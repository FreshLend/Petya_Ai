import json
import os
import config
from typing import Dict, Any

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