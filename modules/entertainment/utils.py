import discord
import random
import json
import os
import config

def load_data():
    with open(config.JOKES_AND_QUOTES, 'r', encoding='utf-8') as f:
        return json.load(f)

interactables = {}

def _load_interactables() -> dict:
    try:
        full_path = os.path.abspath(config.INTERACTABLES)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            data = json.loads(content)
            return data
    except FileNotFoundError:
        print(f"❌ Файл не найден: {full_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return {}
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return {}

interactables = _load_interactables()

async def get_anime_gif(search_query: str):
    try:
        if search_query not in interactables:
            print(f"🔍 Ключ '{search_query}' не найден в interactables.json")
            return None, None
        gifs = interactables[search_query]
        if not gifs:
            print(f"⚠️ Для ключа '{search_query}' нет доступных гифок")
            return None, None
        selected = random.choice(gifs)
        gif_path = selected["path"]
        if not os.path.exists(gif_path):
            print(f"❌ Файл не найден: {gif_path}")
            return None, None
        return gif_path, selected.get("anime", "Неизвестное аниме")
    except Exception as e:
        print(f"🔥 Ошибка в get_anime_gif: {str(e)}")
        return None, None

async def send_gif_embed(interaction: discord.Interaction, gif_path: str, embed: discord.Embed, view: discord.ui.View = None):
    try:
        if not os.path.exists(gif_path):
            raise FileNotFoundError(f"Файл {gif_path} не найден")
        file_size = os.path.getsize(gif_path) / (1024 * 1024)
        if file_size > 8:
            embed.set_footer(text="[Гифка слишком большая] " + (embed.footer.text if embed.footer else ""))
            if view is not None:
                await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed)
            return
        with open(gif_path, 'rb') as f:
            gif_file = discord.File(f, filename=os.path.basename(gif_path))
            embed.set_image(url=f"attachment://{gif_file.filename}")
            if view is not None:
                await interaction.followup.send(file=gif_file, embed=embed, view=view)
            else:
                await interaction.followup.send(file=gif_file, embed=embed)
    except Exception as e:
        print(f"Ошибка при отправке гифки: {e}")
        embed.set_footer(text="[Не удалось загрузить гифку] " + (embed.footer.text if embed.footer else ""))
        if view is not None:
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed)

async def update_interaction_count(user1_id: int, user2_id: int, action: str):
    try:
        with open(config.USER_INTERACTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    for uid in [str(user1_id), str(user2_id)]:
        if uid not in data:
            data[uid] = {}
    for sender, receiver in [(user1_id, user2_id), (user2_id, user1_id)]:
        sender_str = str(sender)
        receiver_str = str(receiver)
        if receiver_str not in data[sender_str]:
            data[sender_str][receiver_str] = {action: 0}
        elif action not in data[sender_str][receiver_str]:
            data[sender_str][receiver_str][action] = 0
        if sender == user1_id:
            data[sender_str][receiver_str][action] += 1
    with open(config.USER_INTERACTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def get_interaction_count(user1_id: int, user2_id: int, action: str) -> int:
    try:
        with open(config.USER_INTERACTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    user1_str = str(user1_id)
    user2_str = str(user2_id)
    if user1_str in data and user2_str in data[user1_str] and action in data[user1_str][user2_str]:
        return data[user1_str][user2_str][action]
    return 0