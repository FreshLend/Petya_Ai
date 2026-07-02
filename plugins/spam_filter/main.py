import discord
import aiohttp
import asyncio
import random
import time
from typing import Optional, Tuple, Dict
from collections import deque

plugin_id = "spam_filter"

CLASSIFIER_URL = "http://localhost:8000/v1/chat/completions"
TIMEOUT = 3

GITHUB_LINK = "https://github.com/FreshLend/spam_classifier"

DUPLICATE_LIMIT = 3
DUPLICATE_WINDOW = 60

user_history: Dict[int, deque] = {}

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

def is_duplicate_spam(user_id: int, text: str) -> bool:
    now = time.time()
    if user_id not in user_history:
        user_history[user_id] = deque(maxlen=DUPLICATE_LIMIT + 1)

    history = user_history[user_id]

    while history and now - history[0][1] > DUPLICATE_WINDOW:
        history.popleft()

    count = sum(1 for msg, ts in history if msg == text)

    history.append((text, now))

    return count >= DUPLICATE_LIMIT

async def classify_text(text: str) -> Tuple[Optional[bool], Optional[str]]:
    payload = {
        "messages": [{"role": "user", "content": text}],
        "temperature": 0.0,
        "max_tokens": 1
    }
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                CLASSIFIER_URL,
                headers=headers,
                json=payload,
                timeout=TIMEOUT
            ) as resp:
                if resp.status != 200:
                    return None, f"Сервер классификатора вернул ошибку {resp.status}"

                data = await resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return None, "Сервер вернул пустой ответ"

                label = choices[0].get("message", {}).get("content", "").strip().lower()
                return label == "spam", None

        except asyncio.TimeoutError:
            return None, "Сервер классификатора не отвечает (таймаут)"
        except aiohttp.ClientConnectorError:
            return None, "Не удалось подключиться к серверу классификатора (сервер не запущен)"
        except aiohttp.ClientError as e:
            return None, f"Ошибка соединения с классификатором: {e}"
        except Exception as e:
            return None, f"Неизвестная ошибка: {e}"

@plugin_hook("on_message")
async def on_message_filter(message: discord.Message) -> bool:
    if message.author.bot:
        return False

    content = message.content.strip()
    if not content or content.startswith(('!', '/')):
        return False

    bot = plugin_api.get_bot()
    is_mentioned = bot.user.mentioned_in(message)
    is_reply_to_bot = (
        message.reference
        and message.reference.resolved
        and isinstance(message.reference.resolved, discord.Message)
        and message.reference.resolved.author == bot.user
    )

    if not (is_mentioned or is_reply_to_bot):
        return False

    if is_duplicate_spam(message.author.id, content):
        try:
            await message.reply(random.choice(DUPLICATE_BLOCK_MESSAGES), mention_author=False)
        except:
            pass
        print(f"🚫 Блокировка (дубликат) от {message.author}: {content[:50]}...")
        return True

    log_preview = content[:100] + ('...' if len(content) > 100 else '')
    print(f"🔍 Плагин получил сообщение от {message.author}: {log_preview!r} (длина: {len(content)})")

    is_spam, error = await classify_text(content)

    if error is not None:
        print(f"⚠️ Ошибка классификатора: {error}\nСкачай и запусти сервер: {GITHUB_LINK}")
        return False

    if is_spam is None:
        return False

    if is_spam:
        reply_text = random.choice(BLOCK_MESSAGES)
        try:
            await message.reply(reply_text, mention_author=False)
        except:
            pass
        print(f"🚫 Блокировка (ИИ) от {message.author}: {content[:50]}...")
        return True

    return False

print("✅ Плагин спам-фильтра загружен")
