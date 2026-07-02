import discord
import aiohttp
import asyncio
import random
from typing import Optional, Tuple

plugin_id = "spam_filter"

CLASSIFIER_URL = "http://localhost:8000/v1/chat/completions"
TIMEOUT = 3

GITHUB_LINK = "https://github.com/FreshLend/spam_classifier"

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

    log_preview = content[:100] + ('...' if len(content) > 100 else '')
    print(f"🔍 Плагин получил сообщение от {message.author}: {log_preview!r} (длина: {len(content)})")

    is_spam, error = await classify_text(content)
    
    if error is not None:
        try:
            await message.reply(
                f"⚠️ **Классификатор спама недоступен!**\n"
                f"Скачай и запусти сервер с GitHub: {GITHUB_LINK}\n"
                f"Ошибка: {error}",
                mention_author=False
            )
        except:
            pass
        print(f"⚠️ Ошибка классификатора: {error}")
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