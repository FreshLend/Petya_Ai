# Файл: ai_commands.py
import asyncio
import discord
from discord import app_commands
from typing import List, Dict, Literal
import traceback

class AskModal(discord.ui.Modal, title="Задать вопрос боту"):
    question_input = discord.ui.TextInput(label="Ваш вопрос", style=discord.TextStyle.long, placeholder="Введите ваш вопрос здесь...", required=True, max_length=2000)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await process_question(interaction, self.question_input.value, is_private=True)

async def process_question(interaction: discord.Interaction, question: str, image_attachments: List[discord.Attachment] = None, is_private: bool = True):
    user_model = aibot.get_user_model(interaction.user.id)
    response_text = await aibot.generate_response_async(question, interaction.user.id, save_context=True, ignore_context=False, image_attachments=image_attachments)
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
            embed = discord.Embed(title="Очистка истории диалога", description="Вы действительно хотите очистить историю диалога?\n**Это действие нельзя отменить!**", color=discord.Color.red())
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
            if self.owner_id in user_contexts:
                user_contexts[self.owner_id]["messages"] = []
                try:
                    save_contexts_sync()
                except Exception as e:
                    print(f"[Очистка] Ошибка сохранения: {e}")
            await interaction.response.edit_message(content="✅ История диалога успешно очищена!", embed=None, view=None)
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
        await interaction.followup.send(f"{interaction.user.mention} {response_text}{footer}", view=ClearView(), ephemeral=is_private)
    else:
        await interaction.followup.send(f"{interaction.user.mention} {response_parts[0]}", view=ClearView(), ephemeral=is_private)
        last_message = await interaction.original_response()
        for i, part in enumerate(response_parts[1:], 1):
            if i == len(response_parts) - 1:
                content = f"{part}{footer}"
            else:
                content = f"{part}\n*(продолжение...)*"
            if len(content) > 2000:
                sub_parts = split_message(content, 1990)
                for sub_part in sub_parts:
                    last_message = await last_message.reply(content=sub_part, mention_author=False, ephemeral=is_private)
            else:
                last_message = await last_message.reply(content=content, mention_author=False, ephemeral=is_private)

@bot.tree.command(name="query", description="Задать вопрос или получить определение")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(action="Действие: ask или define", question="Ваш вопрос (для ask)", term="Термин для определения (для define)", image="Прикрепите изображение (опционально)", is_private="Сделать ответ видимым только вам (по умолчанию True)")
async def query_command(interaction: discord.Interaction, action: Literal["ask", "define"], question: str = None, term: str = None, image: discord.Attachment = None, is_private: bool = True):
    if action == "ask":
        if question is None:
            await interaction.response.send_modal(AskModal())
        else:
            await interaction.response.defer(ephemeral=is_private)
            image_list = [image] if image else []
            await process_question(interaction, question, image_attachments=image_list, is_private=is_private)
    elif action == "define":
        if term is None:
            await interaction.response.send_message("❌ Для /query define необходимо указать term.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=is_private)
        prompt = f"Дай точное и краткое определение термина '{term}'. Если это аббревиатура, расшифруй её."
        definition = await aibot.generate_response_async(prompt, interaction.user.id, save_context=False, ignore_context=True)
        embed = discord.Embed(title=f"Определение: {term}", description=definition, color=discord.Color.dark_gold())
        await interaction.followup.send(embed=embed, ephemeral=is_private)

@bot.tree.command(name="parameter", description="Управление параметрами (get/set/reset)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    action="Действие: get, set или reset",
    parameter="Параметр (system_prompt, context, all)",
    value="Новое значение (только для set)"
)
async def parameter_command(
    interaction: discord.Interaction,
    action: Literal["get", "set", "reset"],
    parameter: Literal["system_prompt", "context", "all"],
    value: str = None
):
    if action == "get":
        await interaction.response.defer(ephemeral=True)
        context = user_contexts.get(interaction.user.id, {})
        custom_prompt = context.get("custom_system_prompt")
        messages = context.get("messages", [])
        
        if parameter == "system_prompt":
            if custom_prompt:
                await interaction.followup.send(f"Ваш системный промпт:\n{custom_prompt[:1900]}{'...' if len(custom_prompt) > 1900 else ''}")
            else:
                await interaction.followup.send("У вас не установлен системный промпт.")
        
        elif parameter == "context":
            if not messages:
                await interaction.followup.send("История диалога пуста.")
                return
            
            history_lines = []
            for msg in messages[-20:]:
                role = "Вы" if msg['role'] == 'user' else "Бот"
                content = msg['content']
                if len(content) > 500:
                    content = content[:497] + "..."
                history_lines.append(f"**{role}:** {content}")
            
            history_text = "\n\n".join(history_lines)
            if len(history_text) > 1900:
                history_text = history_text[:1897] + "..."
            
            embed = discord.Embed(
                title="История диалога (последние сообщения)",
                description=history_text,
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
        
        elif parameter == "all":
            prompt_text = custom_prompt if custom_prompt else "не установлен"
            msg_count = len(messages)
            await interaction.followup.send(f"**Системный промпт:** {prompt_text[:500]}\n**Сообщений в контексте:** {msg_count}")
    
    elif action == "set":
        if parameter != "system_prompt":
            await interaction.response.send_message("❌ Установка возможна только для system_prompt.", ephemeral=True)
            return
        if value is None:
            await interaction.response.send_message("❌ Для /parameter set необходимо указать value.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        
        if interaction.user.id not in user_contexts:
            user_contexts[interaction.user.id] = {"custom_system_prompt": value, "messages": []}
        else:
            user_contexts[interaction.user.id]["custom_system_prompt"] = value
        save_contexts_sync()
        await interaction.followup.send(f"Ваш системный промпт установлен!\nНовый промпт: {value[:100]}{'...' if len(value) > 100 else ''}")
    
    elif action == "reset":
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id not in user_contexts:
            user_contexts[interaction.user.id] = {"custom_system_prompt": None, "messages": []}
        
        if parameter == "system_prompt":
            user_contexts[interaction.user.id]["custom_system_prompt"] = None
            save_contexts_sync()
            await interaction.followup.send("Системный промпт сброшен.")
        
        elif parameter == "context":
            user_contexts[interaction.user.id]["messages"] = []
            save_contexts_sync()
            await interaction.followup.send("Контекст (история диалога) очищен.")
        
        elif parameter == "all":
            user_contexts[interaction.user.id]["custom_system_prompt"] = None
            user_contexts[interaction.user.id]["messages"] = []
            save_contexts_sync()
            await interaction.followup.send("Системный промпт и контекст полностью сброшены.")

@bot.tree.command(name="model", description="Управление моделями (info/set)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(action="Действие: info или set", model="Название модели (только для set)")
async def model_command(interaction: discord.Interaction, action: Literal["info", "set"], model: str = None):
    if action == "info":
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
            await interaction.followup.send(f"Ошибка при получении информации: {str(e)}", ephemeral=True)
    
    elif action == "set":
        if model is None:
            await interaction.response.send_message("❌ Для /model set необходимо указать model.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        
        try:
            profiles = load_profiles()
            user_id_str = str(interaction.user.id)
            if user_id_str not in profiles:
                await interaction.followup.send(
                    "❌ У вас нет профиля! Сначала создайте его через `/profile create:True`.",
                    ephemeral=True
                )
                return
            
            user_group = profiles[user_id_str]["group"]
            available_models = list(aibot.models_config.keys())
            if model not in available_models:
                await interaction.followup.send(f"❌ Модель {model} не найдена! Доступные: {', '.join(available_models)}", ephemeral=True)
                return
            
            model_config = aibot.models_config[model]
            if "required_groups" in model_config:
                if user_group not in model_config["required_groups"]:
                    await interaction.followup.send(f"❌ Модель {model} доступна только для групп: {', '.join(model_config['required_groups'])}!", ephemeral=True)
                    return
            
            if model_config.get("type") == "offline" and not LLAMA_AVAILABLE:
                await interaction.followup.send(f"❌ Локальная модель {model} недоступна: llama-cpp-python не установлена.", ephemeral=True)
                return
            
            aibot.set_user_model(interaction.user.id, model)
            await asyncio.get_event_loop().run_in_executor(aibot.executor, aibot.unload_unused_models)
            await interaction.followup.send(
                f"Модель успешно изменена на {model}!\n"
                f"Тип модели: {model_config['type']}\n"
                f"Параметры:\n"
                f"- Context length: {model_config['context_length']}\n"
                f"- Temperature: {model_config['default_temperature']}\n"
                f"- Max tokens: {model_config['max_tokens']}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"Ошибка при смене модели: {str(e)}", ephemeral=True)

@model_command.autocomplete("model")
async def model_autocomplete(interaction: discord.Interaction, current: str):
    available_models = list(aibot.models_config.keys())
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
    return [app_commands.Choice(name=model, value=model) for model in filtered_models if current.lower() in model.lower()]

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
        embed = discord.Embed(title=f"История диалога (страница {self.current_page + 1}/{len(self.pages)})", description=self.pages[self.current_page], color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="status", description="Информация о статусе (история или очередь)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(action="Действие: history или queue", limit="Количество последних сообщений (для history, по умолчанию 5)")
async def status_command(interaction: discord.Interaction, action: Literal["history", "queue"], limit: int = 5):
    if action == "history":
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
                msg_length = len(msg_text) + 2
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
            embed = discord.Embed(title=f"Последние {len(messages)} сообщений", description=pages[0], color=discord.Color.blue())
            await interaction.followup.send(embed=embed)
        else:
            view = HistoryView(pages, interaction.user.id)
            embed = discord.Embed(title=f"История диалога (страница 1/{len(pages)})", description=pages[0], color=discord.Color.blue())
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    elif action == "queue":
        await interaction.response.defer(ephemeral=True)
        queue_size = len(aibot.generation_queue)
        await interaction.followup.send(f"Текущее состояние очереди:\n- Запросов в очереди: {queue_size}\n- Максимальный размер очереди: {aibot.MAX_QUEUE_SIZE}\n- Активных генераций: {'присутствуют' if aibot.active_generation else 'нет'}", ephemeral=True)

@bot.tree.command(name="summarize", description="Краткое содержание длинного текста")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def summarize(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    prompt = f"Создай краткое содержание следующего текста (2-3 предложения):\n\n{text}"
    summary = await aibot.generate_response_async(prompt, interaction.user.id, save_context=False, ignore_context=True)
    embed = discord.Embed(title="Краткое содержание", description=summary, color=discord.Color.green())
    embed.add_field(name="Исходный текст", value=f"{text[:500]}..." if len(text) > 500 else text, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="translate", description="Перевести текст")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(text="Текст для перевода", to_language="Целевой язык (пример ru, ja)", from_language="Исходный язык (пример ru, ja)")
async def translate_command(interaction: discord.Interaction, text: str, to_language: str, from_language: str = None):
    await interaction.response.defer()
    try:
        translated_text = await translator.translate_text(text=text, to_lang=to_language, from_lang=from_language)
        from_lang_name = translator.language_names.get(from_language, "автоопределение") if from_language else "автоопределение"
        to_lang_name = translator.language_names.get(to_language, to_language)
        embed = discord.Embed(title="🌍 Переводчик", description=f"**Результат перевода:**\n```{translated_text}```", color=discord.Color.blue())
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
async def language_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    choices = []
    for code, name in translator.language_names.items():
        if current.lower() in name.lower() or current.lower() in code.lower():
            choices.append(app_commands.Choice(name=f"{name} ({code})", value=code))
    return choices[:25]

@bot.tree.command(name="char", description="Управление персонажами (список или выбор)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(character="Имя персонажа для выбора (оставьте пустым для списка)")
async def char_command(interaction: discord.Interaction, character: str = None):
    if character is None:
        characters = aibot.characters
        if not characters:
            await interaction.response.send_message("❌ Персонажи не загружены.", ephemeral=True)
            return
        embed = discord.Embed(title="📜 Список персонажей", color=discord.Color.purple())
        for name, data in characters.items():
            desc = data.get("description", "Описание отсутствует.")
            embed.add_field(name=name, value=desc, inline=False)
        current_char = aibot.get_user_character(interaction.user.id)
        embed.set_footer(text=f"Ваш текущий персонаж: {current_char}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        try:
            if character not in aibot.characters:
                available = ", ".join(aibot.characters.keys())
                await interaction.response.send_message(f"❌ Персонаж '{character}' не найден. Доступные: {available}", ephemeral=True)
                return
            aibot.set_user_character(interaction.user.id, character)
            if interaction.user.id in user_contexts:
                user_contexts[interaction.user.id]["messages"] = []
                save_contexts_sync()
            await interaction.response.send_message(f"✅ Персонаж изменён на **{character}**! История диалога очищена.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)