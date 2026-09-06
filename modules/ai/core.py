import asyncio
import json
import os
import threading
import time
import traceback
import random
import aiohttp
import discord
import config
import requests
import base64
import re
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple
from langdetect import detect
from PIL import Image
from io import BytesIO
from openai import OpenAI

LLAMA_AVAILABLE = False
TORCH_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    Llama = None

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None

try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, AutoModelForSequenceClassification, CLIPModel, CLIPProcessor
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    CLIPModel = None
    CLIPProcessor = None


user_contexts: Dict[int, Dict[str, Any]] = {}
server_settings: Dict[int, Dict[str, int]] = {}

def load_contexts_sync() -> Dict[int, Dict[str, Any]]:
    if not os.path.exists(config.USER_CONTEXT_FILE):
        return {}
    try:
        with open(config.USER_CONTEXT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            contexts = {}
            for user_id, ctx in data.items():
                if not user_id.isdigit():
                    continue
                uid = int(user_id)
                custom_prompt = ctx.get("custom_system_prompt")
                if custom_prompt is None and "system_prompt" in ctx:
                    custom_prompt = ctx["system_prompt"]
                contexts[uid] = {
                    "custom_system_prompt": custom_prompt,
                    "messages": ctx.get("messages", [])
                }
            return contexts
    except Exception as e:
        print(f"Ошибка загрузки контекстов: {e}")
        return {}

def save_contexts_sync():
    try:
        save_data = {
            str(user_id): {
                "custom_system_prompt": data.get("custom_system_prompt"),
                "messages": data["messages"]
            }
            for user_id, data in user_contexts.items()
        }
        with open(config.USER_CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print("Контексты успешно сохранены")
    except Exception as e:
        print(f"Ошибка сохранения контекстов: {e}")

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

def load_profiles():
    if not os.path.exists(config.PROFILES_FILE):
        return {}
    with open(config.PROFILES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

user_contexts = load_contexts_sync()
load_server_settings()

class NLLBTranslator:
    def __init__(self):
        with open(config.LANGUAGES, 'r', encoding='utf-8') as f:
            lang_data = json.load(f)
        if TORCH_AVAILABLE:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = "cpu"
        self.model = None
        self.tokenizer = None
        self.language_mapping = lang_data["language_mapping"]
        self.language_names = lang_data["language_names"]
        self.reverse_language_mapping = {v: k for k, v in self.language_mapping.items()}
        self.lock = threading.Lock()
        self.thread = None

    def get_language_choices(self):
        return [(f"{self.language_names[code]} ({code})", code) for code in sorted(self.language_mapping.keys())]

    async def load_model(self):
        if not (TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE):
            return
        if self.model is None:
            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._load_model_sync)
                self.thread.start()

    def _load_model_sync(self):
        if not (TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE):
            return
        with self.lock:
            if self.model is None:
                model_name = "facebook/nllb-200-distilled-1.3B"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)

    async def translate_text(self, text: str, to_lang: str, from_lang: str = None, user_locale: str = None) -> str:
        if not text.strip():
            return ""
        if not (TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE):
            raise RuntimeError("Переводчик недоступен: не установлены PyTorch или Transformers.")
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
            translated_tokens = self.model.generate(**inputs, forced_bos_token_id=forced_bos_token_id, max_new_tokens=4096)
            return self.tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

    def unload(self):
        with self.lock:
            if self.model is not None:
                del self.model
                self.model = None
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None

class SpamFilter:
    BLOCK_MESSAGES = [
        "⛔ Ой, спам! Попробуй ещё раз, но без этого 🙃",
        "⛔ Спам-детектор говорит: 'Не надо так!' 😅",
        "⛔ Ты думал, я это пропущу? Ха-ха, нет! 🚫",
        "⛔ Это спам, дружок. Иди отсюда! 😏",
        "⛔ Ай-яй-яй, нехорошо спамить! 😠",
        "⛔ Мои фильтры говорят: 'Это спам!' 🧐",
        "⛔ Ты серьёзно? Ну ладно, я блокирую, но запомни этот момент! 😄",
        "⛔ Спам-атака отбита! Попробуй что-то умное 🤓",
        "⛔ Осторожно, спам! Я не дам тебе испортить мой чат ✋",
        "⛔ Не, ну это уже слишком. Блокирую! 🛑",
        "⛔ Ты пытался, но я умнее. Следующий раз думай 🤔",
        "⛔ Спам-детектор: 'Обнаружена опасность!' 🚨",
        "⛔ Ха! Я знал, что ты это напишешь. Блокирую с улыбкой 😉",
        "⛔ Твой спам не пройдёт! Я — Петя, я всё вижу 👀",
        "⛔ Спам? Не-не-не, мне такое не нравится! 😤",
        "⛔ Попытка спама провалилась. Возвращайся с чем-то нормальным 🌟",
        "⛔ Фу, какая гадость! Убирай свой спам отсюда 💩",
        "⛔ Я не ведусь на такое. У тебя есть ещё идеи? 😎",
        "⛔ Спам-фильтр активирован! Твой текст заблокирован 🔒",
        "⛔ Ах, вот ты как! Ну, держи блокировку в ответ 😈",
    ]

    DUPLICATE_BLOCK_MESSAGES = [
        "⛔ Эй, хватит копипастить! Одно и то же надоедает 😴",
        "⛔ Ты что, зациклился? Давай новую тему, а не повторяйся 🔄",
        "⛔ Остановись! Я уже понял, что ты хочешь сказать, не надо столько раз 😄",
        "⛔ Копипаст-детектор сработал! Придумай что-нибудь свежее 💡",
        "⛔ Ты думаешь, если повторить 100 раз, я поверю? Нет уж! 😂",
        "⛔ Ай-яй, опять то же самое! Я тебя запомнил, хватит спамить 🧐",
        "⛔ Слушай, я ценю настойчивость, но это уже перебор. Давай по делу! 💬",
        "⛔ Твоё сообщение — как заевшая пластинка. Смени трек! 🎵",
        "⛔ Бот сказал: 'Не повторяйся, пожалуйста!' И я с ним согласен 🤖",
        "⛔ Кажется, у тебя залип Ctrl+V. Отпусти клавиши и напиши что-то новое ⌨️",
        "⛔ Ой, опять то же самое! Я начинаю думать, что ты бот, а не я 😏",
        "⛔ Хватит дублировать, я уже запомнил твой текст наизусть! 📝",
        "⛔ Твоя настойчивость достойна лучшего применения. Например, написать стих! ✍️",
        "⛔ Если ты пытаешься меня сломать повторами — не выйдет, я слишком умён 😎",
        "⛔ Спам-синдром: повторение одного и того же. Лечится новой идеей! 🧠",
        "⛔ У тебя всё хорошо? Может, переключимся на что-то другое? 🤗",
        "⛔ Я знаю, что ты написал. И в прошлый раз тоже. И в позапрошлый. Хватит! 🙈",
        "⛔ Ты уже третий раз пишешь одно и то же. Я начинаю скучать... 😒",
        "⛔ Если ты не прекратишь, я расскажу анекдот про копипасту! 🐒",
        "⛔ Стоп! Это было уже дважды. Третий раз — блокировка по правилам fair play ⚽",
    ]

    TEXT_MODEL_NAME = "NickupAI/Nickup-Swallow-v2"
    CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
    CLIP_LABELS = ["scam", "phishing", "fake giveaway", "fraud", "normal", "safe"]
    SPAM_INDICES = [0, 1, 2, 3]
    TEXT_SPAM_THRESHOLD = 0.9
    IMAGE_SPAM_THRESHOLD = 0.5

    def __init__(self):
        self.user_history: dict[int, deque] = {}
        self.user_request_timestamps: dict[int, deque] = {}
        self.text_model = None
        self.tokenizer = None
        self.clip_model = None
        self.clip_processor = None
        self.device = None
        self.models_loaded = False
        self._load_models()

    def _load_models(self):
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, AutoModelForSequenceClassification, CLIPModel, CLIPProcessor
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"💡 Загрузка спам-фильтра на устройстве: {self.device}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.TEXT_MODEL_NAME)
            self.text_model = AutoModelForSequenceClassification.from_pretrained(self.TEXT_MODEL_NAME)
            self.text_model.to(self.device)
            self.text_model.eval()
            self.clip_model = CLIPModel.from_pretrained(self.CLIP_MODEL_NAME)
            self.clip_processor = CLIPProcessor.from_pretrained(self.CLIP_MODEL_NAME)
            self.clip_model.to(self.device)
            self.clip_model.eval()
            self.models_loaded = True
            print("✅ Спам-фильтр полностью загружен (локальные модели).")
        except Exception as e:
            print(f"❌ Ошибка загрузки моделей спам-фильтра: {e}")
            self.models_loaded = False
            self.text_model = None
            self.tokenizer = None
            self.clip_model = None
            self.clip_processor = None

    def _is_rate_limited(self, user_id: int) -> bool:
        now = time.time()
        if user_id not in self.user_request_timestamps:
            self.user_request_timestamps[user_id] = deque(maxlen=config.RATE_LIMIT_MAX)
        timestamps = self.user_request_timestamps[user_id]
        while timestamps and now - timestamps[0] > config.RATE_LIMIT_WINDOW:
            timestamps.popleft()
        if len(timestamps) >= config.RATE_LIMIT_MAX:
            return True
        timestamps.append(now)
        return False

    def _is_duplicate_spam(self, user_id: int, text: str) -> bool:
        now = time.time()
        if user_id not in self.user_history:
            self.user_history[user_id] = deque(maxlen=config.DUPLICATE_LIMIT + 1)
        history = self.user_history[user_id]
        while history and now - history[0][1] > config.DUPLICATE_WINDOW:
            history.popleft()
        count = sum(1 for msg, ts in history if msg == text)
        history.append((text, now))
        return count >= config.DUPLICATE_LIMIT

    def _matches_allowed_pattern(self, text: str) -> bool:
        for pattern in config.WORDS_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    def _classify_text_sync(self, text: str) -> str:
        if not self.models_loaded or self.text_model is None:
            return "ham"
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self.text_model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1)
                spam_prob = probs[0][0].item()
                return "spam" if spam_prob > self.TEXT_SPAM_THRESHOLD else "ham"
        except Exception as e:
            print(f"⚠️ Ошибка при классификации текста: {e}")
            return "ham"

    def _classify_image_sync(self, image_bytes: bytes) -> str:
        if not self.models_loaded or self.clip_model is None:
            return "ham"
        try:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            inputs = self.clip_processor(
                text=self.CLIP_LABELS,
                images=image,
                return_tensors="pt",
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                probs = outputs.logits_per_image.softmax(dim=1)[0]
                spam_prob = sum(probs[i].item() for i in self.SPAM_INDICES)
                return "spam" if spam_prob > self.IMAGE_SPAM_THRESHOLD else "ham"
        except Exception as e:
            print(f"⚠️ Ошибка при классификации изображения: {e}")
            return "ham"

    async def check(
        self,
        user_id: int,
        text: str = "",
        image_attachments: Optional[List[discord.Attachment]] = None
    ) -> Tuple[bool, Optional[str]]:
        if text.strip() or image_attachments:
            if self._is_rate_limited(user_id):
                return True, "⏳ Слишком много запросов. Подождите немного."

        clean_text = text.strip()
        if clean_text:
            if self._matches_allowed_pattern(clean_text):
                return False, None

        if text.strip():
            if self._is_duplicate_spam(user_id, text):
                return True, random.choice(self.DUPLICATE_BLOCK_MESSAGES)

        if clean_text:
            loop = asyncio.get_event_loop()
            label = await loop.run_in_executor(None, self._classify_text_sync, clean_text)
            if label == "spam":
                return True, random.choice(self.BLOCK_MESSAGES)

        if image_attachments:
            for att in image_attachments[:1]:
                if att.content_type and att.content_type.startswith("image/"):
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(att.url, timeout=config.TIMEOUT) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    loop = asyncio.get_event_loop()
                                    label = await loop.run_in_executor(None, self._classify_image_sync, image_bytes)
                                    if label == "spam":
                                        return True, random.choice(self.BLOCK_MESSAGES)
                    except Exception as e:
                        print(f"⚠️ Ошибка загрузки/классификации изображения: {e}")
                        continue

        return False, None

class AiBot:
    def __init__(self):
        self.user_settings = self.load_user_settings()
        self.models_config = self.load_models_config()
        self.characters = self.load_characters()
        self.llm_instances = {}
        self.model_locks = {model_name: threading.Lock() for model_name in self.models_config.keys()}
        self.default_model = next(iter(self.models_config.keys())) if self.models_config else None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.generation_queue = deque()
        self.active_generation = False
        self.queue_lock = asyncio.Lock()
        self.MAX_QUEUE_SIZE = config.MAX_QUEUE_SIZE
        self.openai_clients = {}
        self.spam_filter = SpamFilter()
        if not self.default_model:
            print("Не найдено ни одной модели в конфигурации!")
            exit()
        offline_models_exist = any(model["type"] == "offline" for model in self.models_config.values())
        if offline_models_exist and not os.path.exists("data/models"):
            os.makedirs("data/models")
            print(f"Папка 'models' создана. Пожалуйста, поместите туда модели типа .gguf")
        if offline_models_exist and not LLAMA_AVAILABLE:
            print("⚠️ Обнаружены локальные модели, но llama-cpp-python не установлена. Они будут недоступны.")

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

    def load_characters(self):
        if not os.path.exists(config.CHARACTER_FILE):
            default_char = {
                "Assistant": {
                    "name": "Assistant",
                    "description": "Полезный и дружелюбный ассистент.",
                    "system_prompt": "Ты полезный и дружелюбный ассистент."
                }
            }
            os.makedirs(os.path.dirname(config.CHARACTER_FILE), exist_ok=True)
            with open(config.CHARACTER_FILE, "w", encoding="utf-8") as f:
                json.dump(default_char, f, ensure_ascii=False, indent=2)
            return default_char
        try:
            with open(config.CHARACTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки персонажей: {e}")
            return {}

    def get_user_character(self, user_id: int) -> str:
        user_id_str = str(user_id)
        if user_id_str in self.user_settings:
            char = self.user_settings[user_id_str].get("character")
            if char and char in self.characters:
                return char
        if self.characters:
            return next(iter(self.characters.keys()))
        return "Assistant"

    def set_user_character(self, user_id: int, character_name: str):
        if character_name not in self.characters:
            raise ValueError(f"Персонаж {character_name} не найден")
        user_id_str = str(user_id)
        if user_id_str not in self.user_settings:
            self.user_settings[user_id_str] = {}
        self.user_settings[user_id_str]["character"] = character_name
        self.save_user_settings()

    def get_system_prompt(self, user_id: int, was_mentioned: bool = False) -> str:
        context = user_contexts.get(user_id, {})
        custom_prompt = context.get("custom_system_prompt")
        if custom_prompt:
            system_content = custom_prompt
        else:
            character_name = self.get_user_character(user_id)
            character = self.characters.get(character_name)
            if character:
                system_content = character.get("system_prompt", "Ты полезный ассистент.")
            else:
                system_content = "Ты полезный ассистент."
            if was_mentioned:
                system_content += "\n\nПользователь упомянул тебя. Обязательно используйте теги по своему усмотрению."
            else:
                system_content += "\n\nТы начал разговор сам. Можешь использовать теги, но не обязательно."
        system_content += config.TAGS_INSTRUCTION
        return system_content

    def get_user_model(self, user_id: int) -> str:
        user_id_str = str(user_id)
        if user_id_str in self.user_settings:
            return self.user_settings[user_id_str].get("model", self.default_model)
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

    def load_model(self, model_name: str):
        with self.model_locks[model_name]:
            if model_name in self.llm_instances:
                return self.llm_instances[model_name]
            model_config = self.models_config[model_name]
            if self.is_online_model(model_name):
                return None
            if not LLAMA_AVAILABLE:
                raise RuntimeError(f"Невозможно загрузить локальную модель {model_name}: llama-cpp-python не установлена.")
            model_path = model_config["path"]
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Модель {model_path} не найдена")
            print(f"Загрузка модели {model_name}...")
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

    def _extract_text_from_content(self, content):
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'text':
                    texts.append(part.get('text', ''))
            return ' '.join(texts)
        else:
            return str(content)

    def count_tokens(self, messages: List[Dict[str, Any]], user_id: int) -> int:
        model_name = self.get_user_model(user_id)
        if self.is_online_model(model_name):
            return sum(len(self._extract_text_from_content(msg['content']).split()) for msg in messages)
        else:
            llm = self.get_llm_for_user(user_id)
            return sum(len(llm.tokenize(str.encode(self._extract_text_from_content(msg['content'])))) for msg in messages)

    def trim_context(self, messages: List[Dict[str, Any]], user_id: int) -> List[Dict[str, Any]]:
        model_config = self.get_model_config_for_user(user_id)
        while self.count_tokens(messages, user_id) > model_config["context_length"] and len(messages) > 1:
            messages.pop(1)
        return messages

    def _get_openai_client(self, base_url: str, token: str):
        key = (base_url, token)
        if key not in self.openai_clients:
            self.openai_clients[key] = OpenAI(base_url=base_url, api_key=token)
        return self.openai_clients[key]

    def _build_vision_messages(self, messages: List[Dict], image_attachments: List[discord.Attachment]) -> List[Dict]:
        if not image_attachments:
            return messages
        new_messages = messages.copy()
        for i in range(len(new_messages) - 1, -1, -1):
            if new_messages[i]['role'] == 'user':
                user_msg = new_messages[i]
                content_parts = [{"type": "text", "text": user_msg['content']}]
                for att in image_attachments:
                    try:
                        resp = requests.get(att.url, timeout=config.TIMEOUT)
                        if resp.status_code == 200:
                            content_type = att.content_type or 'image/png'
                            b64_data = base64.b64encode(resp.content).decode('utf-8')
                            data_url = f"data:{content_type};base64,{b64_data}"
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": data_url}
                            })
                        else:
                            print(f"⚠️ Не удалось загрузить {att.filename}: статус {resp.status_code}")
                    except Exception as e:
                        print(f"⚠️ Ошибка загрузки {att.filename}: {e}")
                new_messages[i]['content'] = content_parts
                break
        return new_messages

    def _generate_online_response(self, model_name: str, messages: List[Dict[str, Any]], image_attachments: List[discord.Attachment] = None) -> str:
        model_config = self.models_config[model_name]
        base_url = model_config.get("base_url")
        token = model_config.get("token")
        model_link = model_config.get("link", model_name)
        if not base_url or not token:
            raise Exception(f"Для онлайн модели {model_name} не указаны base_url или token в конфигурации")
        client = self._get_openai_client(base_url, token)
        if image_attachments and model_config.get("vision", False):
            messages = self._build_vision_messages(messages, image_attachments)
        try:
            completion = client.chat.completions.create(
                model=model_link,
                messages=messages,
                max_tokens=model_config.get("max_tokens", 1024),
                temperature=model_config.get("default_temperature", 0.7)
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Ошибка API для модели {model_name}: {e}")
            raise

    def _generate_offline_response(self, model_name: str, messages: List[Dict[str, str]]) -> str:
        if not LLAMA_AVAILABLE:
            raise RuntimeError("Локальные модели недоступны: отсутствует llama-cpp-python.")
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
            ignore_context: bool = False,
            was_mentioned: bool = False,
            image_attachments: Optional[List[discord.Attachment]] = None
    ) -> str:
        if shutdown_flag or reboot_flag:
            return "Бот выключается/перезагружается, новые запросы не принимаются."
        is_spam, block_msg = await self.spam_filter.check(user_id, prompt, image_attachments)
        if is_spam:
            print(f"🚫 Спам-фильтр сработал для пользователя {user_id}: {prompt[:50]}...")
            return block_msg
        model_name = self.get_user_model(user_id)
        if self.is_online_model(model_name):
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._generate_response_sync,
                    prompt, user_id, save_context, ignore_context, was_mentioned, image_attachments
                )
                return result
            except Exception as e:
                print(f"Ошибка при онлайн генерации: {e}")
                return "Произошла ошибка при обработке запроса."
        if len(self.generation_queue) >= self.MAX_QUEUE_SIZE:
            return "Извините, очередь запросов переполнена. Пожалуйста, попробуйте позже."
        future = asyncio.get_event_loop().create_future()
        async with self.queue_lock:
            self.generation_queue.append((prompt, user_id, save_context, ignore_context, was_mentioned,
                                          image_attachments, future))
            if not self.active_generation:
                self.active_generation = True
                asyncio.create_task(self.process_queue())
        return await future

    async def process_queue(self):
        while True:
            async with self.queue_lock:
                if not self.generation_queue or shutdown_flag or reboot_flag:
                    self.active_generation = False
                    await asyncio.get_event_loop().run_in_executor(self.executor, self.unload_unused_models)
                    return
                prompt, user_id, save_context, ignore_context, was_mentioned, image_attachments, future = self.generation_queue.popleft()
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    self.executor, self._generate_response_sync, prompt, user_id, save_context, ignore_context, was_mentioned, image_attachments
                )
                if not future.done():
                    future.set_result(result)
            except Exception as e:
                if not future.done():
                    future.set_exception(e)

    def _generate_response_sync(self, prompt: str, user_id: int, save_context: bool = True, ignore_context: bool = False, was_mentioned: bool = False, image_attachments: List[discord.Attachment] = None) -> str:
        try:
            print(f"\nПолучен запрос от пользователя {user_id}: {prompt}")
            if ignore_context:
                system_content = self.get_system_prompt(user_id, was_mentioned)
                full_context = [{"role": "system", "content": system_content}, {"role": "user", "content": prompt}]
            else:
                if save_context:
                    self._add_to_user_context_sync(user_id, "user", prompt)
                context = self._get_user_context_sync(user_id)
                system_content = self.get_system_prompt(user_id, was_mentioned)
                full_context = [{"role": "system", "content": system_content}] + context["messages"]
            model_name = self.get_user_model(user_id)
            print(f"Генерация ответа (модель: {model_name})...")
            if self.is_online_model(model_name):
                answer = self._generate_online_response(model_name, full_context, image_attachments)
            else:
                answer = self._generate_offline_response(model_name, full_context)
            print(f"Сгенерирован ответ: {answer[:200]}...")
            if save_context and not ignore_context:
                self._add_to_user_context_sync(user_id, "assistant", answer)
            return answer
        except Exception as e:
            print(f"\nОшибка генерации: {str(e)}")
            traceback.print_exc()
            return "Произошла ошибка при обработке запроса."

    def _get_user_context_sync(self, user_id: int) -> Dict:
        if user_id not in user_contexts:
            user_contexts[user_id] = {"custom_system_prompt": None, "messages": []}
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
        while self.active_generation and (time.time() - start_time) < config.SHUTDOWN_TIME:
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
        while self.active_generation and (time.time() - start_time) < config.SHUTDOWN_TIME:
            await asyncio.sleep(0.5)
        for model_name in list(self.llm_instances.keys()):
            self.unload_model(model_name)
        save_contexts_sync()
        self.save_user_settings()
        save_server_settings()

    async def check_spam(self, user_id: int, text: str = "",
                         image_attachments: Optional[List[discord.Attachment]] = None) -> Tuple[bool, Optional[str]]:
        return await self.spam_filter.check(user_id, text, image_attachments)

aibot = AiBot()
translator = NLLBTranslator()
