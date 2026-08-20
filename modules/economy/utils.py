import json
import os
from pathlib import Path
from typing import Dict
import config

CURRENCY_ORDER = ["copper_coin", "silver_coin", "gold_coin", "platinum_coin"]
CURRENCY_RATIOS = {"copper_coin": 1, "silver_coin": 100, "gold_coin": 10000, "platinum_coin": 1000000}

def to_copper(amount: int, currency: str) -> int:
    return amount * CURRENCY_RATIOS[currency]

def from_copper(copper: int) -> Dict[str, int]:
    result = {cur: 0 for cur in CURRENCY_ORDER}
    remaining = copper
    for i in range(len(CURRENCY_ORDER) - 1, -1, -1):
        cur = CURRENCY_ORDER[i]
        ratio = CURRENCY_RATIOS[cur]
        if remaining >= ratio:
            result[cur] = remaining // ratio
            remaining %= ratio
    return result

def normalize_money(money: Dict[str, int]) -> Dict[str, int]:
    total_copper = sum(to_copper(money.get(cur, 0), cur) for cur in CURRENCY_ORDER)
    return from_copper(total_copper)

def can_afford(money: Dict[str, int], cost: Dict[str, int]) -> bool:
    total_copper_money = sum(to_copper(money.get(cur, 0), cur) for cur in CURRENCY_ORDER)
    total_copper_cost = sum(to_copper(cost.get(cur, 0), cur) for cur in CURRENCY_ORDER)
    return total_copper_money >= total_copper_cost

def deduct_money(money: Dict[str, int], cost: Dict[str, int]) -> Dict[str, int]:
    total_copper = sum(to_copper(money.get(cur, 0), cur) for cur in CURRENCY_ORDER)
    total_copper -= sum(to_copper(cost.get(cur, 0), cur) for cur in CURRENCY_ORDER)
    return from_copper(total_copper)

def add_money(money: Dict[str, int], gain: Dict[str, int]) -> Dict[str, int]:
    total_copper = sum(to_copper(money.get(cur, 0), cur) for cur in CURRENCY_ORDER)
    total_copper += sum(to_copper(gain.get(cur, 0), cur) for cur in CURRENCY_ORDER)
    return from_copper(total_copper)

def load_profiles():
    if not os.path.exists(config.PROFILES_FILE):
        return {}
    with open(config.PROFILES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        for user_id, profile in data.items():
            profile["exp"] = int(profile["exp"])
            profile["next_level_exp"] = int(profile["next_level_exp"])
            for currency in profile["money"].values():
                if isinstance(currency, float):
                    currency = int(currency)
        return data

def save_profiles(profiles):
    with open(config.PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def load_professions():
    path = Path(config.PROFESSIONS)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_models_config():
    if not os.path.exists(config.MODELS_FILE):
        return {}
    with open(config.MODELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_banks():
    if not os.path.exists(config.BANK_DATA_FILE):
        return {}
    with open(config.BANK_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_banks(banks):
    with open(config.BANK_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(banks, f, ensure_ascii=False, indent=2)

def load_shop():
    try:
        with open(config.SHOP_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"categories": {}}

def save_shop(data):
    with open(config.SHOP_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_inventory():
    try:
        with open(config.INVENTORY, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_inventory(data):
    with open(config.INVENTORY, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_treasure_data():
    try:
        with open(config.TREASURE_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def has_metal_detector(inventory: dict, required_level: int = None):
    for item_id, item in inventory.items():
        if item.get('sub_type') == 'metal_detector':
            if required_level is None:
                return True
            if item.get('tool_level', 0) >= required_level:
                return True
    return False

def format_price(price):
    if isinstance(price, dict):
        return " ".join(f"{amount}{config.CURRENCY_EMOJIS.get(currency, '')}" 
                    for currency, amount in price.items())
    return f"{price}{config.CURRENCY_EMOJIS.get('gold_coin', '')}"

def ensure_client_dict_format(banks, bank_name, user_id):
    if user_id in banks[bank_name]["clients"] and isinstance(banks[bank_name]["clients"][user_id], int):
        banks[bank_name]["clients"][user_id] = {
            "gold_coin": 0,
            "silver_coin": 0,
            "copper_coin": 0,
            "platinum_coin": 0
        }

def create_empty_balance():
    return {
        "gold_coin": 0,
        "silver_coin": 0,
        "copper_coin": 0,
        "platinum_coin": 0
    }

def load_casino_settings():
    try:
        with open(config.CASINO_SETTINGS, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        default_settings = {
            "slots": {
                "symbols": {
                    "🍒": {"weight": 40, "payout": 2},
                    "🍋": {"weight": 30, "payout": 3},
                    "🍊": {"weight": 20, "payout": 5},
                    "⭐": {"weight": 7, "payout": 10},
                    "7️⃣": {"weight": 3, "payout": 50}
                },
                "jackpot_combination": ["7️⃣", "7️⃣", "7️⃣"],
                "jackpot_payout": 100
            },
            "thimbles": {
                "win_multiplier": 2
            },
            "blackjack": {
                "min_bet": 10,
                "max_bet": 1000,
                "dealer_stop": 17
            }
        }
        with open("casino_settings.json", "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=2, ensure_ascii=False)
        return default_settings

class ChipConverter:
    @staticmethod
    def money_to_chips(money: Dict[str, int]) -> int:
        total_copper = sum(to_copper(money.get(cur, 0), cur) for cur in CURRENCY_ORDER)
        return total_copper // 1000
    
    @staticmethod
    def chips_to_money(chips: int) -> Dict[str, int]:
        return from_copper(chips * 1000)
    
    @staticmethod
    def can_buy_chips(money: Dict[str, int], amount: int) -> bool:
        total_copper = sum(to_copper(money.get(cur, 0), cur) for cur in CURRENCY_ORDER)
        return total_copper >= amount * 1000
    
    @staticmethod
    def deduct_money_for_chips(money: Dict[str, int], amount: int) -> Dict[str, int]:
        total_copper = sum(to_copper(money.get(cur, 0), cur) for cur in CURRENCY_ORDER)
        total_copper -= amount * 1000
        return from_copper(total_copper)

def get_cash_in_copper(profile: dict) -> int:
    money = profile.get("money", {})
    total = 0
    for cur, amt in money.items():
        if cur in CURRENCY_ORDER:
            total += to_copper(amt, cur)
    return total

def get_bank_in_copper(user_id: str, banks: dict, bank_name: str) -> int:
    if not bank_name or bank_name not in banks:
        return 0
    client = banks[bank_name].get("clients", {}).get(user_id)
    if not client:
        return 0
    if isinstance(client, int):
        return client * 10000
    total = 0
    for cur, amt in client.items():
        if cur in CURRENCY_ORDER:
            total += to_copper(amt, cur)
    return total

def get_inventory_value_in_copper(user_id: str, inventory: dict) -> int:
    user_inv = inventory.get(user_id, {})
    total = 0
    for item in user_inv.values():
        price = item.get("price", 0)
        qty = item.get("quantity", 1)
        if isinstance(price, dict):
            for cur, amt in price.items():
                if cur in CURRENCY_ORDER:
                    total += to_copper(amt, cur) * qty
        else:
            total += to_copper(int(price), "gold_coin") * qty
    return total

def get_casino_value_in_copper(profile: dict) -> int:
    chips = profile.get("casino_chips", 0)
    return chips * 10000

def get_total_wealth(user_id: str, profiles: dict, banks: dict, inventory: dict) -> int:
    profile = profiles.get(user_id, {})
    bank_name = profile.get("bank")
    return (get_cash_in_copper(profile) +
            get_bank_in_copper(user_id, banks, bank_name) +
            get_inventory_value_in_copper(user_id, inventory) +
            get_casino_value_in_copper(profile))

def get_default_profession(professions_data):
    if not professions_data:
        return "Бродяга"
    return list(professions_data.keys())[0]

def get_profession_data(professions_data, profession_name):
    if not professions_data:
        return {}
    if profession_name in professions_data:
        return professions_data[profession_name]
    default = get_default_profession(professions_data)
    return professions_data.get(default, {})