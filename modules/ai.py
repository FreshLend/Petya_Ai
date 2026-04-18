import asyncio
import json
import os
import threading
import time
import traceback
import discord
import torch
import config
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Literal
from discord import app_commands
from langdetect import detect
from llama_cpp import Llama
from openai import OpenAI
from tqdm import tqdm
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

shutdown_flag = False
reboot_flag = False
SHUTDOWN_TIME = 30

class NLLBTranslator:
    def __init__(self):
        with open(config.LANGUAGES, 'r', encoding='utf-8') as f:
            lang_data = json.load(f)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self.language_mapping = lang_data["language_mapping"]
        self.language_names = lang_data["language_names"]
        self.reverse_language_mapping = {v: k for k, v in self.language_mapping.items()}
        self.lock = threading.Lock()
        self.thread = None

    def get_language_choices(self):
        return [
            (f"{self.language_names[code]} ({code})", code)
            for code in sorted(self.language_mapping.keys())
        ]

    async def load_model(self):
        if self.model is None:
            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._load_model_sync)
                self.thread.start()
                print("Запущена фоновая загрузка NLLB модели...")

    def _load_model_sync(self):
        with self.lock:
            if self.model is None:
                model_name = "facebook/nllb-200-distilled-1.3B"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)
                print("NLLB модель загружена")

    async def translate_text(self, text: str, to_lang: str, from_lang: str = None, user_locale: str = None) -> str:
        if not text.strip():
            return ""
        await self.load_model()
        if self.thread and self.thread.is_alive():
            await asyncio.get_event_loop().run_in_executor(None, self.thread.join)
        if from_lang is None:
            try:
                detected_lang = detect(text)
                src_lang = self.language_mapping.get(detected_lang, 'eng_Latn')
            except:
                src_lang = 'eng_Latn'
        else:
            src_lang = self.language_mapping.get(from_lang, 'eng_Latn')
        tgt_lang = self.language_mapping.get(to_lang, 'eng_Latn')
        with self.lock:
            self.tokenizer.src_lang = src_lang
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_lang)
            translated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_new_tokens=4096
            )
            return self.tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

    def unload(self):
        with self.lock:
            if self.model is not None:
                del self.model
                self.model = None
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None
            print("NLLB модель выгружена")

class AiBot:
    def __init__(self):
        self.user_settings = self.load_user_settings()
        self.models_config = self.load_models_config()
        self.llm_instances = {}
        self.model_locks = {model_name: threading.Lock() for model_name in self.models_config.keys()}
        self.default_model = next(iter(self.models_config.keys())) if self.models_config else None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.generation_queue = deque()
        self.active_generation = False
        self.queue_lock = asyncio.Lock()
        self.MAX_QUEUE_SIZE = config.MAX_QUEUE_SIZE
        self.openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.OPENROUTER_API_KEY,
        ) if hasattr(config, 'OPENROUTER_API_KEY') and config.OPENROUTER_API_KEY else None
        if not self.default_model:
            print("Не найдено ни одной модели в конфигурации!")
            exit()
        offline_models_exist = any(model["type"] == "offline" for model in self.models_config.values())
        if offline_models_exist and not os.path.exists("data/models"):
            os.makedirs("data/models")
            print(f"Папка 'models' создана. Пожалуйста, поместите туда модели типа .gguf")

    def load_models_config(self):
        if not os.path.exists(config.MODELS_FILE):
            print(f"Файл конфигурации моделей {config.MODELS_FILE} не найден!")
            return {}
        try:
            with open(config.MODELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации моделей: {e}")
            return {}

    def load_user_settings(self):
        if not os.path.exists(config.USER_SETTINGS_FILE):
            return {}
        try:
            with open(config.USER_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки user_settings.json: {e}")
            return {}

    def save_user_settings(self):
        with open(config.USER_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.user_settings, f, ensure_ascii=False, indent=2)

    def get_user_model(self, user_id: int) -> str:
        user_id_str = str(user_id)
        if user_id_str in self.user_settings:
            return self.user_settings[user_id_str]["model"]
        return self.default_model

    def set_user_model(self, user_id: int, model_name: str):
        if model_name not in self.models_config:
            raise ValueError(f"Модель {model_name} не найдена в конфигурации")
        user_id_str = str(user_id)
        if user_id_str not in self.user_settings:
            self.user_settings[user_id_str] = {}
        self.user_settings[user_id_str]["model"] = model_name
        self.save_user_settings()

    def is_online_model(self, model_name: str) -> bool:
        return self.models_config[model_name].get("type") == "online"

    def load_model(self, model_name: str) -> Llama:
        with self.model_locks[model_name]:
            if model_name in self.llm_instances:
                return self.llm_instances[model_name]
            model_config = self.models_config[model_name]
            if self.is_online_model(model_name):
                self.llm_instances[model_name]
                return None
            model_path = model_config["path"]
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Модель {model_path} не найдена")
            print(f"Загрузка модели {model_name}...")
            print(f"Тип модели: {model_config['type']}")
            print(f"Параметры: context_length={model_config['context_length']}, "
                  f"temperature={model_config['default_temperature']}, "
                  f"n_gpu_layers={model_config['n_gpu_layers']}")
            with tqdm(total=os.path.getsize(model_path), unit='B', unit_scale=True, desc=model_path) as pbar:
                llm = Llama(
                    model_path=model_path,
                    n_ctx=model_config["context_length"],
                    n_gpu_layers=model_config["n_gpu_layers"],
                    seed=-1,
                    verbose=False
                )
                self.llm_instances[model_name] = llm
            print(f"Модель {model_name} успешно загружена!")
            return llm

    def unload_model(self, model_name: str):
        with self.model_locks[model_name]:
            if model_name in self.llm_instances:
                del self.llm_instances[model_name]
                print(f"Модель {model_name} выгружена из памяти")

    def unload_unused_models(self):
        used_models = set(self.get_user_model(uid) for uid in user_contexts.keys())
        all_models = set(self.models_config.keys())
        unused_models = all_models - used_models
        for model_name in unused_models:
            if model_name in self.llm_instances and not self.is_online_model(model_name):
                self.unload_model(model_name)

    def get_llm_for_user(self, user_id: int):
        model_name = self.get_user_model(user_id)
        try:
            llm = self.load_model(model_name)
            if llm is None and not self.is_online_model(model_name):
                raise Exception(f"Оффлайн модель {model_name} не загружена")
            return llm
        except Exception as e:
            print(f"Ошибка загрузки модели {model_name}: {e}")
            if model_name != self.default_model:
                print(f"Попытка использовать модель по умолчанию: {self.default_model}")
                return self.load_model(self.default_model)
            raise

    def get_model_config_for_user(self, user_id: int) -> Dict:
        model_name = self.get_user_model(user_id)
        return self.models_config[model_name]

    def count_tokens(self, messages: List[Dict[str, str]], user_id: int) -> int:
        model_name = self.get_user_model(user_id)
        if self.is_online_model(model_name):
            return sum(len(msg['content'].split()) for msg in messages)
        else:
            llm = self.get_llm_for_user(user_id)
            return sum(len(llm.tokenize(str.encode(msg['content']))) for msg in messages)

    def trim_context(self, messages: List[Dict[str, str]], user_id: int) -> List[Dict[str, str]]:
        model_config = self.get_model_config_for_user(user_id)
        while self.count_tokens(messages, user_id) > model_config["context_length"] and len(messages) > 1:
            messages.pop(1)
        return messages

    def _generate_online_response(self, model_name: str, messages: List[Dict[str, str]]) -> str:
        if not self.openrouter_client:
            raise Exception("OpenRouter client не инициализирован. Проверьте API ключ.")
        model_config = self.models_config[model_name]
        model_link = model_config.get("link", model_name)
        try:
            completion = self.openrouter_client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": getattr(config, 'SITE_URL', 'https://example.com'),
                    "X-Title": getattr(config, 'SITE_NAME', 'My Site'),
                },
                model=model_link,
                messages=messages,
                max_tokens=model_config.get("max_tokens", 1024),
                temperature=model_config.get("default_temperature", 0.7)
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Ошибка OpenRouter API: {e}")
            raise

    def _generate_offline_response(self, model_name: str, messages: List[Dict[str, str]]) -> str:
        model_config = self.models_config[model_name]
        llm = self.load_model(model_name)
        if llm is None:
            raise Exception(f"Оффлайн модель {model_name} не загружена")
        try:
            response = llm.create_chat_completion(
                messages=messages,
                max_tokens=model_config["max_tokens"],
                temperature=model_config["default_temperature"],
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            print(f"Ошибка генерации для модели {model_name}: {e}")
            raise

    async def generate_response_async(
        self,
        prompt: str,
        user_id: int,
        save_context: bool = True,
        ignore_context: bool = False
    ) -> str:
        if shutdown_flag or reboot_flag:
            return "Бот выключается/перезагружается, новые запросы не принимаются."
        if len(self.generation_queue) >= self.MAX_QUEUE_SIZE:
            return "Извините, очередь запросов переполнена. Пожалуйста, попробуйте позже."
        future = asyncio.get_event_loop().create_future()
        async with self.queue_lock:
            self.generation_queue.append((prompt, user_id, save_context, ignore_context, future))
            if not self.active_generation:
                self.active_generation = True
                asyncio.create_task(self.process_queue())
        return await future

    async def process_queue(self):
        while True:
            async with self.queue_lock:
                if not self.generation_queue or shutdown_flag or reboot_flag:
                    self.active_generation = False
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        self.unload_unused_models
                    )
                    return
                prompt, user_id, save_context, ignore_context, future = self.generation_queue.popleft()
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._generate_response_sync,
                    prompt,
                    user_id,
                    save_context,
                    ignore_context
                )
                if not future.done():
                    future.set_result(result)
            except Exception as e:
                if not future.done():
                    future.set_exception(e)

    def _generate_response_sync(
        self,
        prompt: str,
        user_id: int,
        save_context: bool = True,
        ignore_context: bool = False
    ) -> str:
        try:
            print(f"\nПолучен запрос от пользователя {user_id} (save_context={save_context}, ignore_context={ignore_context}): {prompt}")
            if ignore_context:
                full_context = [
                    {"role": "system", "content": config.DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            else:
                if save_context:
                    self._add_to_user_context_sync(user_id, "user", prompt)
                context = self._get_user_context_sync(user_id)
                full_context = [{"role": "system", "content": context["system_prompt"]}] + context["messages"]
            model_name = self.get_user_model(user_id)
            model_config = self.get_model_config_for_user(user_id)
            print(f"Генерация ответа (модель: {model_name}, "
                f"temp={model_config.get('default_temperature', 0.7)}, "
                f"max_tokens={model_config.get('max_tokens', 1024)})...")
            if self.is_online_model(model_name):
                answer = self._generate_online_response(model_name, full_context)
            else:
                answer = self._generate_offline_response(model_name, full_context)
            print(f"Сгенерирован ответ: {answer[:200]}{'...' if len(answer) > 200 else ''}")
            if save_context and not ignore_context:
                self._add_to_user_context_sync(user_id, "assistant", answer)
            return answer
        except Exception as e:
            print(f"\nОшибка генерации: {str(e)}")
            traceback.print_exc()
            return "Произошла ошибка при обработке запроса."

    def _get_user_context_sync(self, user_id: int) -> Dict:
        if user_id not in user_contexts:
            user_contexts[user_id] = {
                "system_prompt": config.DEFAULT_SYSTEM_PROMPT,
                "messages": []
            }
        return user_contexts[user_id]

    def _add_to_user_context_sync(self, user_id: int, role: str, content: str):
        context = self._get_user_context_sync(user_id)
        if role != "system":
            context["messages"].append({"role": role, "content": content})
            context["messages"] = self.trim_context(context["messages"], user_id)
        save_contexts_sync()

    async def shutdown(self):
        global shutdown_flag
        shutdown_flag = True
        start_time = time.time()
        while self.active_generation and (time.time() - start_time) < SHUTDOWN_TIME:
            await asyncio.sleep(0.5)
        for model_name in list(self.llm_instances.keys()):
            self.unload_model(model_name)
        self.executor.shutdown(wait=False)
        save_contexts_sync()
        self.save_user_settings()
        save_server_settings()

    async def prepare_for_reboot(self):
        global reboot_flag
        reboot_flag = True
        start_time = time.time()
        while self.active_generation and (time.time() - start_time) < SHUTDOWN_TIME:
            await asyncio.sleep(0.5)
        for model_name in list(self.llm_instances.keys()):
            self.unload_model(model_name)
        save_contexts_sync()
        self.save_user_settings()
        save_server_settings()

aibot = AiBot()
user_contexts: Dict[int, Dict[str, Any]] = {}
translator = NLLBTranslator()

def load_contexts_sync() -> Dict[int, Dict[str, Any]]:
    if not os.path.exists(config.USER_CONTEXT_FILE):
        return {}
    try:
        with open(config.USER_CONTEXT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                int(user_id): {
                    "system_prompt": str(data[user_id].get("system_prompt", "")),
                    "messages": list(data[user_id].get("messages", []))
                }
                for user_id in data if user_id.isdigit()
            }
    except Exception as e:
        print(f"Ошибка загрузки контекстов: {e}")
        return {}

def save_contexts_sync():
    try:
        save_data = {
            str(user_id): {
                "system_prompt": str(data["system_prompt"]),
                "messages": list(data["messages"])
            }
            for user_id, data in user_contexts.items()
        }
        with open(config.USER_CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print("Контексты успешно сохранены")
    except Exception as e:
        print(f"Ошибка сохранения контекстов: {e}")

user_contexts = load_contexts_sync()
server_settings: Dict[int, Dict[str, int]] = {}

def load_server_settings():
    global server_settings
    if os.path.exists(config.SERVER_SETTINGS_FILE):
        with open(config.SERVER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            server_settings = {int(k): v for k, v in json.load(f).items()}
    else:
        server_settings = {}

def save_server_settings():
    with open(config.SERVER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(server_settings, f, ensure_ascii=False, indent=2)

load_server_settings()

def load_models_list():
    try:
        with open(config.MODELS_FILE, 'r', encoding='utf-8') as f:
            models_config = json.load(f)
            return list(models_config.keys())
    except Exception as e:
        print(f"❌ Ошибка загрузки списка моделей: {e}")
        print("⚠️  Проверьте файл конфигурации моделей!")
        return []

async def update_set_model_command():
    models = load_models_list()
    bot.tree.remove_command("set_model", type=discord.AppCommandType.chat_input)
    @bot.tree.command(name="set_model", description="Установить другую модель")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.user_install()
    async def new_set_model_command(
        interaction: discord.Interaction,
        model: str
    ):
        await interaction.response.defer(ephemeral=True)
        try:
            available_models = load_models_list()
            models_config = aibot.models_config
            if model not in available_models:
                await interaction.followup.send(
                    f"❌ Модель {model} не найдена! Доступные: {', '.join(available_models)}",
                    ephemeral=True
                )
                return
            profiles = load_profiles()
            user_id = str(interaction.user.id)
            if user_id not in profiles:
                await interaction.followup.send(
                    "❌ У вас нет профиля! Сначала создайте его через /profile create:True",
                    ephemeral=True
                )
                return
            user_group = profiles[user_id]["group"]
            model_config = models_config[model]
            if "required_groups" in model_config:
                required_groups = model_config["required_groups"]
                if user_group not in required_groups:
                    await interaction.followup.send(
                        f"❌ Модель {model} доступна только для групп: {', '.join(required_groups)}!",
                        ephemeral=True
                    )
                    return
            old_model = aibot.get_user_model(interaction.user.id)
            aibot.set_user_model(interaction.user.id, model)
            await asyncio.get_event_loop().run_in_executor(
                aibot.executor,
                aibot.unload_unused_models
            )
            await interaction.followup.send(
                f"Модель успешно изменена на {model}!\n"
                f"Тип модели: {model_config['type']}\n"
                f"Параметры модели:\n"
                f"- Context length: {model_config['context_length']}\n"
                f"- Temperature: {model_config['default_temperature']}\n"
                f"- Max tokens: {model_config['max_tokens']}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Ошибка при смене модели: {str(e)}",
                ephemeral=True
            )
    @new_set_model_command.autocomplete("model")
    async def model_autocomplete(interaction: discord.Interaction, current: str):
        available_models = load_models_list()
        profiles = load_profiles()
        user_id = str(interaction.user.id)
        filtered_models = []
        for model in available_models:
            model_config = aibot.models_config[model]
            if "required_groups" in model_config:
                user_group = profiles.get(user_id, {}).get("group", "пользователь")
                if user_group in model_config["required_groups"]:
                    filtered_models.append(model)
            else:
                filtered_models.append(model)
        return [
            app_commands.Choice(name=model, value=model)
            for model in filtered_models
            if current.lower() in model.lower()
        ]
    await bot.tree.sync()

@bot.tree.command(name="ask", description="Задать вопрос боту")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    question="Ваш вопрос"
)
async def ask(
    interaction: discord.Interaction,
    question: str = None
):
    try:
        if question is None:
            await interaction.response.send_modal(AskModal())
        else:
            await interaction.response.defer()
            await process_question(interaction, question)
    except discord.errors.HTTPException as e:
        if "Must be 2000 or fewer in length" in str(e):
            await interaction.followup.send(
                "❌ Ответ слишком длинный и не может быть отправлен даже после разбиения на части.",
                ephemeral=True
            )
        else:
            raise

class AskModal(discord.ui.Modal, title="Задать вопрос боту"):
    question_input = discord.ui.TextInput(
        label="Ваш вопрос",
        style=discord.TextStyle.long,
        placeholder="Введите ваш вопрос здесь...",
        required=True,
        max_length=2000
    )
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await process_question(interaction, self.question_input.value)

async def process_question(interaction: discord.Interaction, question: str):
    user_model = aibot.get_user_model(interaction.user.id)
    response_text = await aibot.generate_response_async(question, interaction.user.id, save_context=True, ignore_context=False)
    
    class ClearView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.owner_id = interaction.user.id
        
        @discord.ui.button(emoji="🗑️", style=discord.ButtonStyle.grey)
        async def clear_button(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
            if btn_interaction.user.id != self.owner_id:
                await btn_interaction.response.send_message("❌ Это не ваша кнопка!", ephemeral=True)
                return
            confirm_view = ConfirmView(self.owner_id)
            embed = discord.Embed(
                title="Очистка истории диалога",
                description="Вы действительно хотите очистить историю диалога?\n**Это действие нельзя отменить!**",
                color=discord.Color.red()
            )
            await btn_interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
    
    class ConfirmView(discord.ui.View):
        def __init__(self, owner_id):
            super().__init__(timeout=30)
            self.owner_id = owner_id
        
        @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("❌ Это не ваша кнопка!", ephemeral=True)
                return
            await interaction.response.edit_message(content="❌ Очистка отменена", embed=None, view=None)
        
        @discord.ui.button(label="Уверен", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("❌ Это не ваша кнопка!", ephemeral=True)
                return
            user_id_str = str(self.owner_id)
            if self.owner_id in user_contexts:
                user_contexts[self.owner_id]["messages"] = []
                try:
                    save_contexts_sync()
                except Exception as e:
                    print(f"[Очистка] Ошибка сохранения: {e}")
            await interaction.response.edit_message(
                content="✅ История диалога успешно очищена!",
                embed=None,
                view=None
            )
    
    def split_message(content: str, limit: int = 1990) -> List[str]:
        if len(content) <= limit:
            return [content]
        
        parts = []
        current_part = ""
        
        lines = content.split('\n')
        
        for line in lines:
            if len(line) > limit:
                words = line.split(' ')
                temp_line = ""
                for word in words:
                    if len(temp_line) + len(word) + 1 <= limit:
                        if temp_line:
                            temp_line += " "
                        temp_line += word
                    else:
                        if temp_line:
                            if current_part:
                                if len(current_part) + len(temp_line) + 1 <= limit:
                                    current_part += "\n" + temp_line
                                else:
                                    if current_part:
                                        parts.append(current_part)
                                    current_part = temp_line
                            else:
                                parts.append(temp_line)
                            temp_line = word
                        else:
                            parts.append(word)
                            temp_line = ""
                if temp_line:
                    if current_part and len(current_part) + len(temp_line) + 1 <= limit:
                        current_part += "\n" + temp_line
                    else:
                        if current_part:
                            parts.append(current_part)
                        current_part = temp_line
            else:
                # Обычная строка
                if current_part and len(current_part) + len(line) + 1 <= limit:
                    current_part += "\n" + line
                else:
                    if current_part:
                        parts.append(current_part)
                    current_part = line
        
        if current_part:
            parts.append(current_part)
        
        return parts
    
    footer = f"\n\nМодель: `{user_model}`"
    max_content_length = 1990 - len(footer)
    
    response_parts = split_message(response_text, max_content_length)
    
    if len(response_parts) == 1:
        await interaction.followup.send(
            f"{interaction.user.mention} {response_text}{footer}",
            view=ClearView()
        )
    else:
        await interaction.followup.send(
            f"{interaction.user.mention} {response_parts[0]}",
            view=ClearView()
        )
        
        last_message = await interaction.original_response()
        
        for i, part in enumerate(response_parts[1:], 1):
            if i == len(response_parts) - 1:
                content = f"{part}{footer}"
            else:
                content = f"{part}\n*(продолжение...)*"
            
            if len(content) > 2000:
                sub_parts = split_message(content, 1990)
                for sub_part in sub_parts:
                    last_message = await last_message.reply(
                        content=sub_part,
                        mention_author=False
                    )
            else:
                last_message = await last_message.reply(
                    content=content,
                    mention_author=False
                )

@bot.tree.command(name="define", description="Определение термина")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def define(
    interaction: discord.Interaction,
    term: str
):
    await interaction.response.defer()
    prompt = f"Дай точное и краткое определение термина '{term}'. Если это аббревиатура, расшифруй её."
    definition = await aibot.generate_response_async(prompt, interaction.user.id, save_context=False, ignore_context=True)
    embed = discord.Embed(
        title=f"Определение: {term}",
        description=definition,
        color=discord.Color.dark_gold()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="get", description="Получить параметры бота")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def get_command(
    interaction: discord.Interaction,
    parameter: Literal["system_prompt"]
):
    await interaction.response.defer(ephemeral=True)
    if parameter == "system_prompt":
        prompt = user_contexts.get(interaction.user.id, {}).get("system_prompt", config.DEFAULT_SYSTEM_PROMPT)
        await interaction.followup.send(
            f"Текущий системный промпт:\n{prompt[:1900]}{'...' if len(prompt) > 1900 else ''}"
        )

class HistoryView(discord.ui.View):
    def __init__(self, pages: List[str], user_id: int):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.user_id = user_id
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша история!", ephemeral=True)
            return
        
        self.current_page = max(0, self.current_page - 1)
        await self.update_message(interaction)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша история!", ephemeral=True)
            return
        
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        await self.update_message(interaction)
    
    async def update_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"История диалога (страница {self.current_page + 1}/{len(self.pages)})",
            description=self.pages[self.current_page],
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="history", description="Показать историю диалога")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def history(
    interaction: discord.Interaction,
    limit: int = 5
):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id not in user_contexts or not user_contexts[interaction.user.id]["messages"]:
        await interaction.followup.send("История диалога пуста.")
        return
    
    messages = user_contexts[interaction.user.id]["messages"][-limit:]
    
    def create_pages(messages_list: List[Dict], max_chars_per_page: int = 4000) -> List[str]:
        pages = []
        current_page = []
        current_length = 0
        
        for msg in messages_list:
            role = 'Вы' if msg['role'] == 'user' else 'Бот'
            content = msg['content']
            if len(content) > 500:
                content = content[:497] + "..."
            
            msg_text = f"**{role}:** {content}"
            msg_length = len(msg_text) + 2  # +2 для разделителя
            
            if current_length + msg_length > max_chars_per_page and current_page:
                pages.append("\n\n".join(current_page))
                current_page = [msg_text]
                current_length = msg_length
            else:
                current_page.append(msg_text)
                current_length += msg_length
        
        if current_page:
            pages.append("\n\n".join(current_page))
        
        return pages if pages else ["История пуста"]
    
    pages = create_pages(messages)
    
    if len(pages) == 1:
        embed = discord.Embed(
            title=f"Последние {len(messages)} сообщений",
            description=pages[0],
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)
    else:
        view = HistoryView(pages, interaction.user.id)
        embed = discord.Embed(
            title=f"История диалога (страница 1/{len(pages)})",
            description=pages[0],
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="model_info", description="Информация о текущей модели")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def model_info_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        model_name = aibot.get_user_model(interaction.user.id)
        model_config = aibot.models_config[model_name]
        loaded = model_name in aibot.llm_instances
        await interaction.followup.send(
            f"Текущая модель: {model_name}\n"
            f"Тип модели: {model_config['type']}\n"
            f"Состояние: {'загружена' if loaded else 'не загружена'}\n"
            f"Параметры:\n"
            f"- Context length: {model_config['context_length']}\n"
            f"- Temperature: {model_config['default_temperature']}\n"
            f"- Max tokens: {model_config['max_tokens']}\n"
            f"- GPU layers: {model_config['n_gpu_layers']}",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"Ошибка при получении информации: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="queue_info", description="Информация об очереди запросов")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def queue_info_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    queue_size = len(aibot.generation_queue)
    await interaction.followup.send(
        f"Текущее состояние очереди:\n"
        f"- Запросов в очереди: {queue_size}\n"
        f"- Максимальный размер очереди: {aibot.MAX_QUEUE_SIZE}\n"
        f"- Активных генераций: {'присутствуют' if aibot.active_generation else 'нет'}",
        ephemeral=True
    )

@bot.tree.command(name="reset", description="Сбросить параметры бота")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def reset_command(
    interaction: discord.Interaction,
    parameter: Literal["context", "system_prompt", "all"]
):
    await interaction.response.defer(ephemeral=True)
    if parameter == "context":
        if interaction.user.id in user_contexts:
            user_contexts[interaction.user.id]["messages"] = []
            save_contexts_sync()
        await interaction.followup.send("История чата сброшена!")
    elif parameter == "system_prompt":
        if interaction.user.id in user_contexts:
            user_contexts[interaction.user.id]["system_prompt"] = config.DEFAULT_SYSTEM_PROMPT
            user_contexts[interaction.user.id]["messages"] = []
            save_contexts_sync()
        await interaction.followup.send(
            f"Системный промпт сброшен до стандартного:\n{config.DEFAULT_SYSTEM_PROMPT[:1900]}{'...' if len(config.DEFAULT_SYSTEM_PROMPT) > 1900 else ''}"
        )
    elif parameter == "all":
        if interaction.user.id in user_contexts:
            del user_contexts[interaction.user.id]
            save_contexts_sync()
        await interaction.followup.send(
            "Все параметры сброшены до стандартных значений!"
        )

@bot.tree.command(name="set", description="Установить параметры бота")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def set_command(
    interaction: discord.Interaction,
    parameter: Literal["system_prompt"],
    value: str
):
    await interaction.response.defer(ephemeral=True)
    if parameter == "system_prompt":
        if interaction.user.id not in user_contexts:
            user_contexts[interaction.user.id] = {
                "system_prompt": value,
                "messages": []
            }
        else:
            user_contexts[interaction.user.id]["system_prompt"] = value
            user_contexts[interaction.user.id]["messages"] = []
        save_contexts_sync()
        await interaction.followup.send(
            f"Системный промпт обновлен!\nНовый промпт: {value[:100]}{'...' if len(value) > 100 else ''}"
        )

@bot.tree.command(name="set_model", description="Установить другую модель")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def set_model_command(
    interaction: discord.Interaction,
    model: str
):
    await interaction.response.defer(ephemeral=True)
    try:
        available_models = load_models_list()
        models_config = aibot.models_config
        if model not in available_models:
            await interaction.followup.send(
                f"❌ Модель {model} не найдена в списке доступных моделей!",
                ephemeral=True
            )
            return
        profiles = load_profiles()
        user_id = str(interaction.user.id)
        if user_id not in profiles:
            await interaction.followup.send(
                "❌ У вас нет профиля! Сначала создайте его через /profile create:True",
                ephemeral=True
            )
            return
        user_group = profiles[user_id]["group"]
        if "required_groups" in models_config[model]:
            required_groups = models_config[model]["required_groups"]
            if user_group not in required_groups:
                await interaction.followup.send(
                    f"❌ Модель {model} доступна только для групп: {', '.join(required_groups)}!",
                    ephemeral=True
                )
                return
        old_model = aibot.get_user_model(interaction.user.id)
        aibot.set_user_model(interaction.user.id, model)
        await asyncio.get_event_loop().run_in_executor(
            aibot.executor,
            aibot.unload_unused_models
        )
        model_config = models_config[model]
        await interaction.followup.send(
            f"Модель успешно изменена на {model}!\n"
            f"Тип модели: {model_config['type']}\n"
            f"Параметры модели:\n"
            f"- Context length: {model_config['context_length']}\n"
            f"- Temperature: {model_config['default_temperature']}\n"
            f"- Max tokens: {model_config['max_tokens']}",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"Ошибка при смене модели: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="summarize", description="Краткое содержание длинного текста")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def summarize(
    interaction: discord.Interaction,
    text: str
):
    await interaction.response.defer()
    prompt = f"Создай краткое содержание следующего текста (1-3 предложения):\n\n{text}"
    summary = await aibot.generate_response_async(prompt, interaction.user.id, save_context=False, ignore_context=True)
    embed = discord.Embed(
        title="Краткое содержание",
        description=summary,
        color=discord.Color.green()
    )
    embed.add_field(name="Исходный текст", value=f"{text[:500]}..." if len(text) > 500 else text, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="translate", description="Перевести текст")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    text="Текст для перевода",
    to_language="Целевой язык (пример ru, ja)",
    from_language="Исходный язык (пример ru, ja)"
)
async def translate_command(
    interaction: discord.Interaction,
    text: str,
    to_language: str,
    from_language: str = None
):
    await interaction.response.defer()
    try:
        translated_text = await translator.translate_text(
            text=text,
            to_lang=to_language,
            from_lang=from_language
        )
        from_lang_name = translator.language_names.get(from_language, "автоопределение") if from_language else "автоопределение"
        to_lang_name = translator.language_names.get(to_language, to_language)
        embed = discord.Embed(
            title="🌍 Переводчик",
            description=f"**Результат перевода:**\n```{translated_text}```",
            color=discord.Color.blue()
        )
        embed.add_field(name="Исходный текст", value=f"```{text[:256]}{'...' if len(text) > 256 else ''}```", inline=False)
        embed.add_field(name="Исходный язык", value=from_lang_name, inline=True)
        embed.add_field(name="Целевой язык", value=to_lang_name, inline=True)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"Ошибка перевода: {e}")
        traceback.print_exc()
        await interaction.followup.send(f"Произошла ошибка при переводе текста: {str(e)}")

@translate_command.autocomplete('from_language')
@translate_command.autocomplete('to_language')
async def language_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    choices = []
    for code, name in translator.language_names.items():
        if current.lower() in name.lower() or current.lower() in code.lower():
            choices.append(app_commands.Choice(
                name=f"{name} ({code})",
                value=code
            ))
    return choices[:25]