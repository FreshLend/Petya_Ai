import asyncio
import json
import math
import os
import random
import discord
import config
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from discord import app_commands
from discord.ui import Button, Modal, Select, TextInput, View

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
        chips = 0
        chips += money.get("copper_coin", 0) // 1000
        chips += money.get("silver_coin", 0) // 100
        chips += money.get("gold_coin", 0)
        chips += money.get("platinum_coin", 0) * 100
        return chips
    
    @staticmethod
    def chips_to_money(chips: int) -> Dict[str, int]:
        money = {
            "platinum_coin": 0,
            "gold_coin": 0,
            "silver_coin": 0,
            "copper_coin": 0
        }
        
        if chips >= 100:
            money["platinum_coin"] = chips // 100
            chips %= 100
        
        money["gold_coin"] = chips
        chips = 0
        
        if money["gold_coin"] == 0 and chips == 0:
            pass
        
        return money
    
    @staticmethod
    def can_buy_chips(money: Dict[str, int], amount: int) -> bool:
        total_copper_needed = amount * 1000
        
        total_copper_available = (
            money.get("copper_coin", 0) +
            money.get("silver_coin", 0) * 100 +
            money.get("gold_coin", 0) * 1000 +
            money.get("platinum_coin", 0) * 100000
        )
        
        return total_copper_available >= total_copper_needed
    
    @staticmethod
    def deduct_money_for_chips(money: Dict[str, int], amount: int) -> Dict[str, int]:
        copper_needed = amount * 1000
        
        new_money = money.copy()
        
        if new_money.get("copper_coin", 0) >= copper_needed:
            new_money["copper_coin"] -= copper_needed
            return new_money
        
        copper_needed -= new_money.get("copper_coin", 0)
        new_money["copper_coin"] = 0
        
        silver_needed = math.ceil(copper_needed / 100)
        if new_money.get("silver_coin", 0) >= silver_needed:
            new_money["silver_coin"] -= silver_needed
            copper_needed -= silver_needed * 100
            if copper_needed < 0:
                new_money["copper_coin"] += abs(copper_needed)
            return new_money
        
        copper_needed -= new_money.get("silver_coin", 0) * 100
        new_money["silver_coin"] = 0
        
        gold_needed = math.ceil(copper_needed / 1000)
        if new_money.get("gold_coin", 0) >= gold_needed:
            new_money["gold_coin"] -= gold_needed
            copper_needed -= gold_needed * 1000
            if copper_needed < 0:
                silver_change = abs(copper_needed) // 100
                copper_change = abs(copper_needed) % 100
                new_money["silver_coin"] += silver_change
                new_money["copper_coin"] += copper_change
            return new_money
        
        copper_needed -= new_money.get("gold_coin", 0) * 1000
        new_money["gold_coin"] = 0
        
        platinum_needed = math.ceil(copper_needed / 100000)
        new_money["platinum_coin"] -= platinum_needed
        copper_needed -= platinum_needed * 100000
        
        if copper_needed < 0:
            change = abs(copper_needed)
            gold_change = change // 1000
            change %= 1000
            silver_change = change // 100
            copper_change = change % 100
            
            new_money["gold_coin"] += gold_change
            new_money["silver_coin"] += silver_change
            new_money["copper_coin"] += copper_change
        
        return new_money

class SlotsGame:
    def __init__(self, settings: Dict):
        self.settings = settings
        self.symbols = list(settings["slots"]["symbols"].keys())
        self.weights = [settings["slots"]["symbols"][s]["weight"] for s in self.symbols]
        self.payouts = {s: settings["slots"]["symbols"][s]["payout"] for s in self.symbols}
        self.jackpot_combination = settings["slots"]["jackpot_combination"]
        self.jackpot_payout = settings["slots"]["jackpot_payout"]
    
    def spin(self) -> tuple:
        result = random.choices(self.symbols, weights=self.weights, k=3)
        
        if result == self.jackpot_combination:
            return result, self.jackpot_payout
        
        if result[0] == result[1] == result[2]:
            return result, self.payouts[result[0]]
        
        if result[0] == result[1] or result[0] == result[2] or result[1] == result[2]:
            for symbol in result:
                if result.count(symbol) == 2:
                    return result, self.payouts[symbol] // 2
        
        return result, 0

class ThimblesGame:
    def __init__(self, settings: Dict):
        self.settings = settings
        self.win_multiplier = settings["thimbles"]["win_multiplier"]
    
    def play(self, player_choice: int) -> tuple:
        ball_position = random.randint(1, 3)
        return player_choice == ball_position, ball_position

class BlackjackGame:
    def __init__(self, settings: Dict):
        self.settings = settings
        self.deck = self.create_deck()
        self.shuffle_deck()
    
    def create_deck(self) -> List[str]:
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠', '♥', '♦', '♣']
        deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
        return deck * 4
    
    def shuffle_deck(self):
        random.shuffle(self.deck)
    
    def draw_card(self) -> str:
        if len(self.deck) < 10:
            self.deck = self.create_deck()
            self.shuffle_deck()
        return self.deck.pop()
    
    def card_value(self, card: str) -> int:
        rank = card[:-1]
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11
        else:
            return int(rank)
    
    def calculate_hand_value(self, hand: List[str]) -> int:
        value = 0
        aces = 0
        
        for card in hand:
            card_val = self.card_value(card)
            if card_val == 11:
                aces += 1
            value += card_val
        
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def dealer_turn(self, dealer_hand: List[str]) -> List[str]:
        while self.calculate_hand_value(dealer_hand) < self.settings["blackjack"]["dealer_stop"]:
            dealer_hand.append(self.draw_card())
        return dealer_hand

def add_item_to_inventory(user_id: str, item_template: dict, quantity: int = 1):
    inventory = load_inventory()
    if user_id not in inventory:
        inventory[user_id] = {}
    user_inv = inventory[user_id]
    
    def normalize_for_match(data):
        if isinstance(data, dict):
            return json.dumps(data, sort_keys=True)
        return data
    
    match_fields = (
        item_template.get('type'),
        item_template.get('sub_type'),
        item_template.get('tool_level'),
        item_template.get('name'),
        item_template.get('description'),
        normalize_for_match(item_template.get('price', {})),
        normalize_for_match(item_template.get('effects', {})),
        item_template.get('duration'),
        normalize_for_match(item_template.get('requirements', {})),
        item_template.get('sold'),
        item_template.get('use'),
        item_template.get('delete'),
        item_template.get('unpack'),
        normalize_for_match(item_template.get('details', {}))
    )
    
    for existing_id, existing_item in user_inv.items():
        existing_match = (
            existing_item.get('type'),
            existing_item.get('sub_type'),
            existing_item.get('tool_level'),
            existing_item.get('name'),
            existing_item.get('description'),
            normalize_for_match(existing_item.get('price', {})),
            normalize_for_match(existing_item.get('effects', {})),
            existing_item.get('duration'),
            normalize_for_match(existing_item.get('requirements', {})),
            existing_item.get('sold'),
            existing_item.get('use'),
            existing_item.get('delete'),
            existing_item.get('unpack'),
            normalize_for_match(existing_item.get('details', {}))
        )
        if match_fields == existing_match:
            existing_item['quantity'] = existing_item.get('quantity', 1) + quantity
            save_inventory(inventory)
            return existing_id
    
    new_id = f"{item_template.get('name', 'item')}_{int(datetime.now().timestamp())}_{random.randint(1000,9999)}"
    new_item = item_template.copy()
    new_item['quantity'] = quantity
    new_item['obtained_at'] = datetime.now().isoformat()
    inventory[user_id][new_id] = new_item
    save_inventory(inventory)
    return new_id

def remove_item_from_inventory(user_id: str, item_id: str, quantity: int) -> bool:
    inventory = load_inventory()
    if user_id not in inventory or item_id not in inventory[user_id]:
        return False
    item = inventory[user_id][item_id]
    current_qty = item.get('quantity', 1)
    if quantity >= current_qty:
        del inventory[user_id][item_id]
    else:
        item['quantity'] = current_qty - quantity
    save_inventory(inventory)
    return True

class RepairButton(Button):
    def __init__(self, detector_id: str):
        super().__init__(
            label="Починить",
            style=discord.ButtonStyle.red,
            emoji="🛠️"
        )
        self.detector_id = detector_id
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        inventory = load_inventory()
        user_id = str(interaction.user.id)
        profiles = load_profiles()
        
        if user_id not in inventory or self.detector_id not in inventory[user_id]:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Ошибка",
                    description="Металлоискатель не найден!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        detector = inventory[user_id][self.detector_id]
        repair_cost = self.calculate_repair_cost(detector)
        
        if not self.has_enough_money(profiles[user_id]['money'], repair_cost):
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Недостаточно денег",
                    description=f"Для починки нужно: {self.format_cost(repair_cost)}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        self.deduct_money(profiles[user_id]['money'], repair_cost)
        
        detector['details']['durability'] = detector.get('max_durability', 1000)
        
        save_profiles(profiles)
        save_inventory(inventory)
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ Металлоискатель починен",
                description=f"Ваш {detector['name']} полностью восстановлен!\n\nПотрачено: {self.format_cost(repair_cost)}",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
    
    def calculate_repair_cost(self, detector):
        base_price = detector.get('price', {})
        repair_cost = {}
        
        for currency, amount in base_price.items():
            repair_cost[currency] = max(1, int(amount * 0.2))
        
        return repair_cost
    
    def has_enough_money(self, user_money, cost):
        return all(user_money.get(currency, 0) >= amount for currency, amount in cost.items())
    
    def deduct_money(self, user_money, cost):
        for currency, amount in cost.items():
            if user_money.get(currency, 0) >= amount:
                user_money[currency] -= amount
                return
        
        currency_order = ['platinum_coin', 'gold_coin', 'silver_coin', 'copper_coin']
        
        for i, currency in enumerate(currency_order):
            if currency in cost:
                needed = cost[currency]
                available = user_money.get(currency, 0)
                
                if available < needed:
                    if i > 0:
                        higher_currency = currency_order[i-1]
                        exchange_rate = 100 if higher_currency == 'gold_coin' else 10
                        
                        needed_higher = (needed - available + exchange_rate - 1) // exchange_rate
                        
                        if user_money.get(higher_currency, 0) >= needed_higher:
                            user_money[higher_currency] -= needed_higher
                            user_money[currency] += needed_higher * exchange_rate - (needed - available)
                        else:
                            continue
                
                user_money[currency] -= needed
    
    def format_cost(self, cost):
        return " ".join(f"{config.CURRENCY_EMOJIS.get(currency, '')} {amount}" 
                      for currency, amount in cost.items())

class SearchButton(Button):
    def __init__(self, location_id: str):
        super().__init__(
            label="Поиск",
            style=discord.ButtonStyle.green,
            emoji="🔍"
        )
        self.location_id = location_id
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        treasure_data = load_treasure_data()
        location = treasure_data.get(self.location_id, {})
        user_id = str(interaction.user.id)
        
        full_inventory = load_inventory()
        user_inventory = full_inventory.get(user_id, {})
        
        profiles = load_profiles()
        profile = profiles.get(user_id, {})
        
        required_level = location.get('required_level', 1)
        if profile.get("level", 1) < required_level:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Недостаточный уровень",
                    description=f"Требуется уровень {required_level} (у вас {profile.get('level', 1)})",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        detector_required = location.get('detector_required', False)
        detector_level = location.get('detector_level')
        best_detector = None
        best_detector_id = None
        
        if detector_required:
            for item_id, item in user_inventory.items():
                if item.get('sub_type') == 'metal_detector':
                    if detector_level is None or item.get('tool_level', 0) >= detector_level:
                        if best_detector is None or item.get('tool_level', 0) > best_detector.get('tool_level', 0):
                            best_detector = item
                            best_detector_id = item_id
            
            if not best_detector:
                embed = discord.Embed(
                    title="❌ Требуется металлоискатель",
                    description=f"Для этой локации {'требуется металлоискатель' + (f' {detector_level} уровня' if detector_level else '')}",
                    color=discord.Color.red()
                )
                if detector_level:
                    embed.set_footer(text="Мысли: Мне кажется лучше обновить металлоискатель")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if best_detector.get('details', {}).get('durability', 1) <= 0:
                view = View(timeout=120)
                view.add_item(RepairButton(best_detector_id))
                
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="💥 Металлоискатель сломан",
                        description="Ваш металлоискатель полностью вышел из строя и требует починки!",
                        color=discord.Color.red()
                    ),
                    view=view,
                    ephemeral=True
                )
                return
        
        base_chance = location.get('base_chance', 0.1)
        
        if best_detector:
            detector_level_value = best_detector.get('tool_level', 1)
            level_multiplier = 1 + (detector_level_value - 1) * 0.3
            base_chance *= level_multiplier
            
            durability = best_detector.get('details', {}).get('durability', 1000)
            max_durability = best_detector.get('max_durability', 1000)
            durability_percent = durability / max_durability
            durability_bonus = -0.5 + (durability_percent * 0.9)
            base_chance *= (1 + durability_bonus)
        
        event_type = random.choices(
            ["positive", "negative", "neutral"],
            weights=[
                config.TREASURE_EVENT_CHANCES.get("positive", 0.20),
                config.TREASURE_EVENT_CHANCES.get("negative", 0.10),
                config.TREASURE_EVENT_CHANCES.get("neutral", 0.7)
            ]
        )[0]
        
        event = random.choice(location.get('events', {}).get(event_type, []))
        event_text = event.get("text", "")
        
        if "chance_multiplier" in event:
            base_chance *= event["chance_multiplier"]
        
        base_chance = max(0.05, min(0.95, base_chance))
        
        durability_change = 0
        if best_detector:
            if "durability_bonus" in event:
                bonus = int(best_detector.get('max_durability', 1000) * event["durability_bonus"])
                durability_change += bonus
                
            if "durability_penalty" in event:
                penalty = int(best_detector.get('max_durability', 1000) * event["durability_penalty"])
                durability_change -= penalty
        
        if random.random() > base_chance:
            if best_detector:
                durability_loss = random.randint(5, 15)
                new_durability = max(0, best_detector['details'].get('durability', 1000) - durability_loss + durability_change)
                best_detector['details']['durability'] = new_durability
                full_inventory[user_id] = user_inventory
                save_inventory(full_inventory)
                
                embed = discord.Embed(
                    title="🔍 Поиск не удался",
                    description=f"{event_text}\n\nВы ничего не нашли.",
                    color=discord.Color.orange()
                )
                
                if best_detector:
                    embed.add_field(
                        name="Состояние металлоискателя",
                        value=f"🔧 {best_detector['details'].get('durability', 0)}/{best_detector.get('max_durability', 1000)}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        possible_items = location.get('possible_items', [])
        selected_item = random.choices(
            possible_items,
            weights=[item.get('chance', 1) for item in possible_items]
        )[0]
        
        item_template = {
            "type": selected_item.get('type', 'item'),
            "name": selected_item.get('name', 'Предмет'),
            "description": selected_item.get('description', ''),
            "price": selected_item.get('price', 0),
            "effects": selected_item.get('effects', {}),
            "sold": selected_item.get('sold', True),
            "use": selected_item.get('use', False),
            "delete": selected_item.get('delete', True),
            "unpack": selected_item.get('unpack', False),
            "requirements": selected_item.get('requirements', {}),
            "duration": selected_item.get('duration', 'infinity')
        }
        
        quantity = selected_item.get('quantity', 1)
        add_item_to_inventory(user_id, item_template, quantity)
        
        broken_text = ""
        if best_detector:
            durability_loss = random.randint(10, 25)
            new_durability = max(0, best_detector['details'].get('durability', 1000) - durability_loss + durability_change)
            best_detector['details']['durability'] = new_durability
            
            if new_durability <= 0:
                broken_text = "\n\n💥 Ваш металлоискатель сломался!"
            
            full_inventory[user_id] = user_inventory
            save_inventory(full_inventory)
        
        embed = discord.Embed(
            title=f"🎉 Найдено: {selected_item.get('name', 'Предмет')}",
            description=f"{event_text}\n\n{selected_item.get('description', '')}{broken_text}",
            color=discord.Color.green() if event_type == "positive" else 
                 discord.Color.red() if event_type == "negative" else 
                 discord.Color.blue()
        )
        
        if best_detector:
            embed.add_field(
                name="Состояние металлоискателя",
                value=f"🔧 {best_detector['details'].get('durability', 0)}/{best_detector.get('max_durability', 1000)}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class LocationSelector(Select):
    def __init__(self, locations: dict, current_location: str):
        options = []
        for loc_id, loc_data in locations.items():
            options.append(discord.SelectOption(
                label=loc_data['name'],
                description=f"Ур. {loc_data.get('required_level', 1)}",
                value=loc_id,
                default=(loc_id == current_location)
            ))
        
        super().__init__(
            placeholder="Выберите локацию для поиска...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.locations = locations
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        treasure_data = load_treasure_data()
        location = treasure_data.get(self.values[0], {})
        
        embed = discord.Embed(
            title=f"🔍 {location.get('name', 'Локация')} (Ур. {location.get('required_level', 1)}+)",
            description=location.get('description', 'Описание отсутствует'),
            color=discord.Color.blue()
        )
        
        requirements = []
        if location.get('detector_required', False):
            req = "🔹 Металлоискатель"
            if 'detector_level' in location:
                req += f" (ур. {location['detector_level']}+)"
            requirements.append(req)
        
        if requirements:
            embed.add_field(name="Требования", value="\n".join(requirements), inline=False)
        
        possible_items = location.get('possible_items', [])
        if possible_items:
            items_text = []
            for item in possible_items[:5]:
                chance = item.get('chance', 1)
                items_text.append(f"▫ {item['name']} (шанс: {chance*100:.1f}%)")
            
            if len(possible_items) > 5:
                items_text.append(f"... и еще {len(possible_items)-5} предметов")
            
            embed.add_field(name="Возможные находки", value="\n".join(items_text), inline=False)
        
        view = View(timeout=120)
        view.add_item(SearchButton(self.values[0]))
        view.add_item(LocationSelector(self.locations, self.values[0]))
        
        await interaction.edit_original_response(embed=embed, view=view)

class BuyItemModal(Modal, title='Покупка предмета'):
    def __init__(self, item_id, item_name, max_quantity, price_info):
        super().__init__()
        self.item_id = item_id
        self.item_name = item_name
        self.max_quantity = max_quantity
        self.price_info = price_info
        
        self.quantity = TextInput(
            label=f'Количество {item_name}',
            placeholder=f'Введите количество (макс. {max_quantity})',
            default='1',
            max_length=len(str(max_quantity))
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity.value)
            if quantity < 1:
                await interaction.response.send_message(
                    "❌ Количество должно быть положительным числом!",
                    ephemeral=True)
                return
            quantity = min(quantity, self.max_quantity)
        except ValueError:
            await interaction.response.send_message(
                "❌ Пожалуйста, введите корректное число!",
                ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await buy_item(interaction, self.item_id, quantity, self.price_info)

class BuyItemButton(Button):
    def __init__(self, item_id, item_name, max_quantity, price_info):
        super().__init__(
            label=f"Купить {item_name}", 
            style=discord.ButtonStyle.success,
            emoji="🛒")
        self.item_id = item_id
        self.item_name = item_name
        self.max_quantity = max_quantity
        self.price_info = price_info
    
    async def callback(self, interaction: discord.Interaction):
        modal = BuyItemModal(self.item_id, self.item_name, self.max_quantity, self.price_info)
        await interaction.response.send_modal(modal)

class ItemManageModal(Modal):
    def __init__(self, item_id, item_name, action, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_id = item_id
        self.item_name = item_name
        self.action = action
        self.quantity = TextInput(
            label='Количество', 
            placeholder='Введите количество', 
            default='1')
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity.value)
            if quantity < 1:
                await interaction.response.send_message(
                    "❌ Количество должно быть положительным числом!",
                    ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Пожалуйста, введите корректное число!",
                ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await manage_item(interaction, self.item_id, self.action, quantity)

class ShopView(View):
    def __init__(self, black_store=False, has_pass=False):
        super().__init__(timeout=180)
        self.black_store = black_store
        self.has_pass = has_pass
        
        if not black_store and not has_pass:
            self.add_item(BuyPassButton())

class BuyPassButton(Button):
    def __init__(self):
        super().__init__(
            label="Купить пропуск", 
            style=discord.ButtonStyle.primary,
            emoji="🎫")
    
    async def callback(self, interaction: discord.Interaction):
        await buy_pass(interaction)

class InventoryItemButton(Button):
    def __init__(self, item_id, item_name):
        super().__init__(
            label=item_name[:25], 
            style=discord.ButtonStyle.primary,
            emoji="📦")
        self.item_id = item_id
        self.item_name = item_name
    
    async def callback(self, interaction: discord.Interaction):
        await show_item_details(interaction, self.item_id)

class InventoryView(View):
    def __init__(self, item_id, item_name, item_type, item_data):
        super().__init__(timeout=120)
        if item_type == "bundle" and item_data.get("unpack", True):
            self.add_item(UnpackBundleButton(item_id, item_name))
        if item_data.get("use", True):
            self.add_item(UseItemButton(item_id, item_name))
        if item_data.get("sold", True):
            self.add_item(SellItemButton(item_id, item_name))
        if item_data.get("delete", True):
            self.add_item(DeleteItemButton(item_id, item_name))

class UnpackBundleButton(Button):
    def __init__(self, item_id, item_name):
        super().__init__(
            label="Распаковать", 
            style=discord.ButtonStyle.success,
            emoji="🎁")
        self.item_id = item_id
        self.item_name = item_name
    
    async def callback(self, interaction: discord.Interaction):
        modal = ItemManageModal(
            self.item_id, 
            self.item_name, 
            "unpack", 
            title=f"Распаковать {self.item_name}"
        )
        await interaction.response.send_modal(modal)

class UseItemButton(Button):
    def __init__(self, item_id, item_name):
        super().__init__(
            label="Применить", 
            style=discord.ButtonStyle.success,
            emoji="⚡")
        self.item_id = item_id
        self.item_name = item_name
    
    async def callback(self, interaction: discord.Interaction):
        modal = ItemManageModal(
            self.item_id, 
            self.item_name, 
            "use", 
            title=f"Применить {self.item_name}"
        )
        await interaction.response.send_modal(modal)

class SellItemButton(Button):
    def __init__(self, item_id, item_name):
        super().__init__(
            label="Продать", 
            style=discord.ButtonStyle.secondary,
            emoji="💰")
        self.item_id = item_id
        self.item_name = item_name
    
    async def callback(self, interaction: discord.Interaction):
        modal = ItemManageModal(
            self.item_id, 
            self.item_name, 
            "sell", 
            title=f"Продать {self.item_name}"
        )
        await interaction.response.send_modal(modal)

class DeleteItemButton(Button):
    def __init__(self, item_id, item_name):
        super().__init__(
            label="Удалить", 
            style=discord.ButtonStyle.danger,
            emoji="🗑️")
        self.item_id = item_id
        self.item_name = item_name
    
    async def callback(self, interaction: discord.Interaction):
        modal = ItemManageModal(
            self.item_id, 
            self.item_name, 
            "delete", 
            title=f"Удалить {self.item_name}"
        )
        await interaction.response.send_modal(modal)

class CategorySelect(Select):
    def __init__(self, categories, black_store=False):
        options = [
            discord.SelectOption(
                label=cat_name,
                description=category.get("description", "Нет описания"),
                emoji=category.get("emoji", "📦")
            )
            for cat_name, category in categories.items()
            if category.get("type") == ("black_market" if black_store else "regular")
        ]
        
        super().__init__(
            placeholder="Выберите категорию",
            min_values=1,
            max_values=1,
            options=options
        )
        self.black_store = black_store
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        shop_data = load_shop()
        selected_category = self.values[0]
        category_data = shop_data["categories"].get(selected_category)
        
        if not category_data:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Ошибка",
                    description="Категория не найдена!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📦 {selected_category}",
            description=category_data.get("description", "Нет описания"),
            color=discord.Color.dark_purple() if self.black_store else discord.Color.blue()
        ).set_thumbnail(url=interaction.user.display_avatar.url)
        
        view = CategoryItemsView(selected_category, self.black_store)
        
        items_list = []
        for item_id, item in category_data.get("items", {}).items():
            name = item.get("name", "Без названия")
            description = item.get("description", "Нет описания")
            required_level = item.get("requirements", {}).get("level", 0)
            price = item.get("price", 0)
            discount = item.get("discount", 0)
            
            if isinstance(price, dict):
                final_price = {curr: int(amt * (1 - discount / 100)) 
                              for curr, amt in price.items()}
            else:
                final_price = int(price * (1 - discount / 100))
            
            quantity = item.get("quantity", "∞")
            max_quantity = 99
            
            if quantity != "∞":
                try:
                    quantity = int(quantity)
                    max_quantity = min(99, quantity)
                except (ValueError, TypeError):
                    quantity = 0
                    max_quantity = 0
            
            price_text = format_price(price)
            final_price_text = format_price(final_price)

            if discount > 0:
                price_display = f"~~{price_text}~~ → {final_price_text} (скидка {discount}%)"
            else:
                price_display = f"{price_text}"
            
            item_text = (
                f"`{item_id}` - **{name}**\n"
                f"**Цена:** {price_display}\n"
                f"**Описание:** {description}\n"
                f"**Требуемый уровень:** {required_level}\n"
                f"**В наличии:** {'∞' if quantity == '∞' else quantity}\n"
            )
            
            items_list.append(item_text)
            
            if max_quantity > 0:
                view.add_item(BuyItemButton(
                    item_id, name, max_quantity, final_price))
        
        if items_list:
            embed.description += "\n\n**Доступные предметы:**"
            for item_text in items_list:
                embed.add_field(
                    name="\u200b",
                    value=item_text,
                    inline=False
                )
        else:
            embed.description += "\n\nВ этой категории пока нет предметов."
        
        view.add_item(BackToCategoriesButton(self.black_store))

        await interaction.edit_original_response(embed=embed, view=view)

class CategoryItemsView(View):
    def __init__(self, category_name, black_store=False):
        super().__init__(timeout=180)
        self.category_name = category_name
        self.black_store = black_store

class BackToCategoriesButton(Button):
    def __init__(self, black_store=False):
        super().__init__(
            label="Назад к категориям",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️"
        )
        self.black_store = black_store
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await show_shop_categories(interaction, self.black_store, interaction.message)

async def show_shop_categories(interaction: discord.Interaction, black_store=False, message=None):
    shop_data = load_shop()
    categories = shop_data.get("categories", {})
    
    embed = discord.Embed(
        title="🔮 Категории чёрного рынка" if black_store else "🏪 Категории магазина",
        description="Выберите категорию для просмотра товаров",
        color=discord.Color.dark_purple() if black_store else discord.Color.blue()
    ).set_thumbnail(url=interaction.user.display_avatar.url)
    
    view = View(timeout=180)
    view.add_item(CategorySelect(categories, black_store))
    
    profiles = load_profiles()
    user_id = str(interaction.user.id)
    inventory = load_inventory().get(user_id, {})
    has_pass = any(item.get("type") == "black_market_pass" for item in inventory.values())
    
    if not black_store and profiles.get(user_id, {}).get("level", 1) >= 15 and not has_pass:
        view.add_item(BuyPassButton())
    
    if message:
        await message.edit(embed=embed, view=view)
    else:
        await interaction.followup.send(embed=embed, view=view)

async def manage_item(interaction: discord.Interaction, item_id: str, action: str, quantity: int):
    inventory = load_inventory()
    user_id = str(interaction.user.id)
    profiles = load_profiles()
    
    if user_id not in inventory or item_id not in inventory[user_id]:
        await interaction.followup.send("❌ Предмет не найден в инвентаре!", ephemeral=True)
        return
    
    item = inventory[user_id][item_id]
    available_quantity = item.get("quantity", 1)
    
    if quantity > available_quantity:
        await interaction.followup.send(f"❌ У вас только {available_quantity} шт. этого предмета!", ephemeral=True)
        return
    
    if action == "use":
        if item.get("requirements", {}).get("level", 0) > profiles[user_id].get("level", 0):
            await interaction.followup.send(
                f"❌ Для использования требуется {item['requirements']['level']} уровень!",
                ephemeral=True)
            return
            
        effects = item.get("effects", {})
        profile = profiles[user_id]
        now = datetime.now()
        
        if "active_effects" not in profile:
            profile["active_effects"] = {}
        
        messages = []
        effect_applied = False
        
        for effect_type, effect_value in effects.items():
            if effect_type == "energy_restore":
                restored = effect_value * quantity
                max_energy = profile.get("max_energy", 100)
                profile["energy"] = min(max_energy, profile.get("energy", max_energy) + restored)
                messages.append(f"⚡ Восстановлено {restored} энергии")
                effect_applied = True
            
            elif effect_type == "max_energy":
                bonus = effect_value * quantity
                profile["max_energy"] = profile.get("max_energy", 100) + bonus
                profile["energy"] = min(profile["max_energy"], profile.get("energy", profile["max_energy"]))
                messages.append(f"🔋 Макс. энергия увеличена на {bonus}")
                effect_applied = True
            
            elif effect_type in ["exp_multiplier", "money_multiplier"]:
                current_effect = profile["active_effects"].get(effect_type)
                
                try:
                    duration = int(item.get("duration", 3600))
                except (TypeError, ValueError):
                    duration = 3600
                
                if current_effect:
                    expires_at = datetime.fromisoformat(current_effect["expires"])
                    new_expires = expires_at + timedelta(seconds=duration)
                    current_effect["expires"] = new_expires.isoformat()
                    messages.append(f"⏳ Эффект {effect_type} продлён до {new_expires.strftime('%H:%M:%S')}")
                else:
                    expires_at = (now + timedelta(seconds=duration)).isoformat()
                    profile["active_effects"][effect_type] = {
                        "value": effect_value,
                        "expires": expires_at
                    }
                    human_duration = str(timedelta(seconds=duration))
                    messages.append(f"✨ Новый эффект: {effect_type} x{effect_value} на {human_duration}")
                effect_applied = True
        
        if not effect_applied:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Не удалось применить предмет",
                    description="Этот предмет не имеет эффектов или они уже активны",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        if not remove_item_from_inventory(user_id, item_id, quantity):
            await interaction.followup.send("❌ Ошибка при удалении предмета", ephemeral=True)
            return
        
        save_profiles(profiles)
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ Предмет применен",
                description=f"Вы успешно применили {quantity} шт. {item['name']}!\n\n" + "\n".join(messages),
                color=discord.Color.green()
            ),
            ephemeral=True)
    
    elif action == "sell":
        if item.get("sold", True) is False:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Нельзя продать",
                    description="Этот предмет нельзя продать!",
                    color=discord.Color.red()
                ),
                ephemeral=True)
            return
        
        if item.get("type") == "black_market_pass":
            sell_price = 0
        else:
            sell_price = item.get("price", 0)

        if isinstance(sell_price, dict):
            total_price = {curr: int(amt * quantity) for curr, amt in sell_price.items()}
        else:
            total_price = int(sell_price * quantity)
        
        if user_id not in profiles:
            profiles[user_id] = {"money": {}}
        
        if isinstance(total_price, dict):
            for currency, amount in total_price.items():
                profiles[user_id]["money"][currency] = profiles[user_id]["money"].get(currency, 0) + amount
        else:
            profiles[user_id]["money"]["gold_coin"] = profiles[user_id]["money"].get("gold_coin", 0) + total_price
        
        if not remove_item_from_inventory(user_id, item_id, quantity):
            await interaction.followup.send("❌ Ошибка при удалении предмета", ephemeral=True)
            return
        
        save_profiles(profiles)
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="💰 Предмет продан",
                description=f"Вы продали {quantity} шт. {item['name']} за {format_price(total_price)}!",
                color=discord.Color.green()
            ),
            ephemeral=True)
    
    elif action == "delete":
        if not remove_item_from_inventory(user_id, item_id, quantity):
            await interaction.followup.send("❌ Ошибка при удалении предмета", ephemeral=True)
            return
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="🗑️ Предмет удален",
                description=f"Вы удалили {quantity} шт. {item['name']}!",
                color=discord.Color.green()
            ),
            ephemeral=True)
    
    elif action == "unpack" and item.get("type") == "bundle":
        shop_data = load_shop()
        bundle_contents = None
        
        for category in shop_data.get("categories", {}).values():
            for shop_item_id, shop_item in category.get("items", {}).items():
                if shop_item_id in item_id:
                    if "contains" in shop_item:
                        bundle_contents = shop_item["contains"]
                        break
            if bundle_contents:
                break
        
        if not bundle_contents:
            await interaction.followup.send("❌ Не удалось найти содержимое этого набора!", ephemeral=True)
            return
        
        added_items = []
        for content_id, content_quantity in bundle_contents.items():
            content_item = None
            
            for category in shop_data.get("categories", {}).values():
                if content_id in category.get("items", {}):
                    content_item = category["items"][content_id]
                    break
            
            if not content_item:
                continue
            
            total_quantity = content_quantity * quantity
            content_template = {
                "type": content_item.get("type", "item"),
                "name": content_item["name"],
                "description": content_item.get("description", ""),
                "price": content_item.get("price", 0),
                "effects": content_item.get("effects", {}),
                "duration": content_item.get("duration", "infinity"),
                "requirements": content_item.get("requirements", {}),
                "sold": content_item.get("sold", True),
                "use": content_item.get("use", True),
                "delete": content_item.get("delete", True),
                "unpack": content_item.get("unpack", True)
            }
            
            add_item_to_inventory(user_id, content_template, total_quantity)
            added_items.append(f"{content_item['name']} x{total_quantity}")
        
        if not added_items:
            await interaction.followup.send("❌ Набор пуст или его содержимое не найдено!", ephemeral=True)
            return
        
        if not remove_item_from_inventory(user_id, item_id, quantity):
            await interaction.followup.send("❌ Ошибка при удалении набора", ephemeral=True)
            return
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="🎁 Набор распакован",
                description=f"Вы распаковали {quantity} шт. {item['name']} и получили:\n" + 
                          "\n".join(f"• {item}" for item in added_items),
                color=discord.Color.green()
            ),
            ephemeral=True)

async def buy_pass(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    profiles = load_profiles()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Ошибка",
                description="У вас нет профиля!",
                color=discord.Color.red()
            ),
            ephemeral=True)
        return
    
    profile = profiles[user_id]
    if profile.get("level", 1) < 15:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Недостаточный уровень",
                description="Вам нужно достичь 15 уровня!",
                color=discord.Color.red()
            ),
            ephemeral=True)
        return
    
    insufficient_currencies = []
    for currency, amount in config.BLACK_MARKET_PASS.items():
        if profile["money"].get(currency, 0) < amount:
            insufficient_currencies.append(
                f"{amount} {config.CURRENCY_EMOJIS.get(currency, currency)}")
    
    if insufficient_currencies:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Недостаточно средств",
                description=f"Не хватает: {', '.join(insufficient_currencies)}",
                color=discord.Color.red()
            ),
            ephemeral=True)
        return
    
    inventory = load_inventory()
    if user_id not in inventory:
        inventory[user_id] = {}
    
    for item in inventory[user_id].values():
        if item.get("type") == "black_market_pass":
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Ошибка",
                    description="У вас уже есть пропуск!",
                    color=discord.Color.red()
                ),
                ephemeral=True)
            return
    
    for currency, amount in config.BLACK_MARKET_PASS.items():
        profile["money"][currency] = profile["money"].get(currency, 0) - amount
    
    item_template = {
        "type": "black_market_pass",
        "name": "Пропуск на чёрный рынок",
        "description": "Даёт доступ к чёрному рынку",
        "price": 0,
        "sold": False,
        "delete": False,
        "use": False,
        "requirements": {
            "level": 15
        }
    }
    add_item_to_inventory(user_id, item_template, 1)
    
    save_profiles(profiles)
    
    await interaction.followup.send(
        embed=discord.Embed(
            title="✅ Успешно",
            description=f"Вы купили пропуск на чёрный рынок за {format_price(config.BLACK_MARKET_PASS)}!",
            color=discord.Color.green()
        ),
        ephemeral=True)

async def restore_energy():
    while True:
        await asyncio.sleep(config.ENERGY_RESTORE_INTERVAL)
        profiles = load_profiles()
        updated = False
        
        for user_id, profile in profiles.items():
            max_energy = profile.get("max_energy", 100)
            
            if "energy" not in profile:
                profile["energy"] = max_energy
                updated = True

            if profile["energy"] < max_energy:
                restore_amount = min(
                    config.ENERGY_RESTORE,
                    max_energy - profile["energy"]
                )
                profile["energy"] += restore_amount
                profile["last_energy_update"] = datetime.now().isoformat()
                updated = True
        
        if updated:
            save_profiles(profiles)

async def show_item_details(interaction: discord.Interaction, item_id: str):
    await interaction.response.defer(ephemeral=True)
    inventory = load_inventory()
    user_id = str(interaction.user.id)
    
    if user_id not in inventory or item_id not in inventory[user_id]:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Ошибка",
                description="Предмет не найден в инвентаре!",
                color=discord.Color.red()
            ),
            ephemeral=True)
        return
    
    item = inventory[user_id][item_id]
    embed = discord.Embed(
        title=f"📦 {item['name']}",
        description=item.get("description", "Нет описания"),
        color=discord.Color.gold()
    ).set_thumbnail(url=interaction.user.display_avatar.url)
    
    info_fields = [
        f"**ID:** `{item_id}`",
        f"**Количество:** {item.get('quantity', 1)}",
        f"**Тип:** {item.get('type', 'предмет')}",
    ]
    
    if item.get("requirements"):
        reqs = []
        if "level" in item["requirements"]:
            reqs.append(f"Уровень: {item['requirements']['level']}+")
        if reqs:
            info_fields.append(f"**Требования:** {', '.join(reqs)}")
    
    restrictions = []
    if item.get("sold", True) is False:
        restrictions.append("❌ Продажа")
    if item.get("use", True) is False:
        restrictions.append("❌ Использование")
    if item.get("delete", True) is False:
        restrictions.append("❌ Удаление")
    if item.get("type") == "bundle" and item.get("unpack", True) is False:
        restrictions.append("❌ Распаковка")
    
    if restrictions:
        embed.add_field(
            name="🔒 Ограничения",
            value="\n".join(restrictions),
            inline=False)
    
    if "effects" in item:
        effects = []
        if "max_energy" in item["effects"]:
            effects.append(f"🔋 +{item['effects']['max_energy']} к максимальной энергии")
        if "exp_multiplier" in item["effects"]:
            effects.append(f"📚 Множитель опыта: x{item['effects']['exp_multiplier']}")
        if "money_multiplier" in item["effects"]:
            effects.append(f"💰 Множитель денег: x{item['effects']['money_multiplier']}")
        if "energy_restore" in item["effects"]:
            effects.append(f"⚡ Восстанавливает {item['effects']['energy_restore']} энергии")
        
        if effects:
            embed.add_field(
                name="🔹 Эффекты",
                value="\n".join(effects),
                inline=False)
    
    if "duration" in item and item["duration"] != "infinity":
        duration = timedelta(seconds=item["duration"])
        embed.add_field(
            name="⏳ Длительность",
            value=f"{duration}",
            inline=False)
    
    embed.set_footer(
        text=f"Получен: {datetime.fromisoformat(item['obtained_at']).strftime('%d.%m.%Y %H:%M')}")
    
    view = InventoryView(item_id, item['name'], item.get("type"), item)
    await interaction.followup.send(embed=embed, view=view)

async def buy_item(interaction: discord.Interaction, item_id: str, quantity: int, price_info):
    try:
        profiles = load_profiles()
        user_id = str(interaction.user.id)
        
        if user_id not in profiles:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Ошибка",
                    description="У вас нет профиля!",
                    color=discord.Color.red()
                ),
                ephemeral=True)
            return
        
        shop_data = load_shop()
        item_found = None
        
        for category in shop_data.get("categories", {}).values():
            if item_id in category.get("items", {}):
                item_found = category["items"][item_id]
                break
        
        if not item_found:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Ошибка",
                    description="Предмет не найден!",
                    color=discord.Color.red()
                ),
                ephemeral=True)
            return
        
        profile = profiles[user_id]
        inventory = load_inventory()
        user_inventory = inventory.get(user_id, {})

        if item_found.get("type") == "tools":
            item_sub_type = item_found.get("sub_type")
            new_tool_level = item_found.get("tool_level", 0)

            tools_to_remove = []
            highest_level = 0
            
            for item_key, item_data in user_inventory.items():
                if (item_data.get("type") == "tools" and 
                    item_data.get("sub_type") == item_sub_type):
                    
                    current_level = item_data.get("tool_level", 0)
                    highest_level = max(highest_level, current_level)

                    if new_tool_level <= current_level:
                        await interaction.followup.send(
                            embed=discord.Embed(
                                title="❌ Ошибка",
                                description=f"У вас уже есть {item_data['name']} (уровень {current_level}). "
                                          f"Вы можете купить только инструмент более высокого уровня (>{highest_level})!",
                                color=discord.Color.red()
                            ),
                            ephemeral=True)
                        return

                    tools_to_remove.append(item_key)

            for item_key in tools_to_remove:
                remove_item_from_inventory(user_id, item_key, user_inventory[item_key].get('quantity', 1))

        item_requirements = item_found.get("requirements", {})
        required_level = item_requirements.get("level", 0)
        user_level = profile.get("level", 0)
        
        if user_level < required_level:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Недостаточный уровень",
                    description=f"Для покупки этого предмета требуется {required_level} уровень (у вас {user_level})!",
                    color=discord.Color.red()
                ),
                ephemeral=True)
            return

        if item_found.get("quantity", "∞") != "∞":
            try:
                available = int(item_found["quantity"])
                if available < quantity:
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="❌ Недостаточно товара",
                            description=f"В наличии только {available} шт.!",
                            color=discord.Color.red()
                        ),
                        ephemeral=True)
                    return
            except (ValueError, TypeError):
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Ошибка",
                        description="Ошибка проверки количества товара!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True)
                return

        insufficient_currencies = []
        
        if isinstance(price_info, dict):
            total_price = {curr: int(amt * quantity) for curr, amt in price_info.items()}
            
            for currency, amount in total_price.items():
                if profile["money"].get(currency, 0) < amount:
                    insufficient_currencies.append(
                        f"{amount} {config.CURRENCY_EMOJIS.get(currency, currency)}")
        else:
            total_price = int(price_info * quantity)
            if profile["money"].get("gold_coin", 0) < total_price:
                insufficient_currencies.append(
                    f"{total_price} {config.CURRENCY_EMOJIS.get('gold_coin')}")
        
        if insufficient_currencies:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Недостаточно средств",
                    description=f"Не хватает: {', '.join(insufficient_currencies)}",
                    color=discord.Color.red()
                ),
                ephemeral=True)
            return

        if isinstance(total_price, dict):
            for currency, amount in total_price.items():
                profile["money"][currency] -= amount
        else:
            profile["money"]["gold_coin"] -= total_price

        if item_found.get("type") == "tools":
            inventory_price = price_info if isinstance(price_info, dict) else price_info
        else:
            if isinstance(price_info, dict):
                inventory_price = {curr: int(amt * 0.5) for curr, amt in price_info.items()}
            else:
                inventory_price = int(price_info * 0.5)
        
        item_template = {
            "type": item_found.get("type", "item"),
            "sub_type": item_found.get("sub_type", ""),
            "tool_level": item_found.get("tool_level", 0),
            "name": item_found["name"],
            "description": item_found.get("description", ""),
            "price": inventory_price,
            "effects": item_found.get("effects", {}),
            "duration": item_found.get("duration", "infinity"),
            "requirements": item_found.get("requirements", {}),
            "sold": item_found.get("sold", True),
            "use": item_found.get("use", True),
            "delete": item_found.get("delete", True),
            "unpack": item_found.get("unpack", True),
            "details": item_found.get("details", {})
        }
        
        add_item_to_inventory(user_id, item_template, quantity)

        if item_found.get("quantity", "∞") != "∞":
            for category in shop_data.get("categories", {}).values():
                if item_id in category.get("items", {}):
                    category["items"][item_id]["quantity"] -= quantity
                    if category["items"][item_id]["quantity"] <= 0:
                        del category["items"][item_id]
                    break
        
        save_profiles(profiles)
        save_shop(shop_data)
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ Успешная покупка",
                description=f"Вы купили {quantity} шт. {item_found['name']} за {format_price(total_price)}!",
                color=discord.Color.green()
            ),
            ephemeral=True)
        
    except Exception as e:
        print(f"Ошибка при покупке предмета: {e}")
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Ошибка",
                description="Произошла ошибка при обработке покупки!",
                color=discord.Color.red()
            ),
            ephemeral=True)

@bot.tree.command(name="bank", description="Управление банком или просмотр баланса")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    action="Действие с банком",
    name="Название банка",
    set_comission="Установить комиссию банка (в %)",
    set_service="Установить обслуживание (в %)",
    new_name="Новое название банка"
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="create", value="create"),
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="rename", value="rename"),
        app_commands.Choice(name="set_comission", value="set_comission"),
        app_commands.Choice(name="set_service", value="set_service"),
        app_commands.Choice(name="info", value="info")
    ]
)
async def bank_command(
    interaction: discord.Interaction,
    action: Optional[app_commands.Choice[str]] = None,
    name: Optional[str] = None,
    set_comission: Optional[float] = None,
    set_service: Optional[float] = None,
    new_name: Optional[str] = None
):
    await interaction.response.defer()
    profiles = load_profiles()
    banks = load_banks()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send("❌ У вас нет профиля!", ephemeral=True)
        return
    
    if action is None:
        current_bank = profiles[user_id].get("bank")
        if not current_bank or current_bank not in banks:
            await interaction.followup.send("❌ У вас нет активного банка!", ephemeral=True)
            return
        
        ensure_client_dict_format(banks, current_bank, user_id)
        
        if user_id not in banks[current_bank]["clients"]:
            banks[current_bank]["clients"][user_id] = create_empty_balance()
        
        client_data = banks[current_bank]["clients"][user_id]
        embed = discord.Embed(
            title=f"Ваш баланс в банке '{current_bank}'",
            color=discord.Color.blue()
        )
        
        money_values = []
        for currency in ["copper_coin", "silver_coin", "gold_coin", "platinum_coin"]:
            emoji = config.CURRENCY_EMOJIS.get(currency, "")
            money_values.append(f"{emoji} `{client_data.get(currency, 0)}`")
        
        embed.description = "\n".join(money_values)
        await interaction.followup.send(embed=embed, ephemeral=False)
        return
    
    action_value = action.value if action else None
    
    if action_value == "create":
        if not name:
            await interaction.followup.send("❌ Укажите название банка!", ephemeral=True)
            return
            
        user_banks = [b for b in banks.values() if b["owner_id"] == user_id]
        if len(user_banks) >= 3:
            await interaction.followup.send("❌ У вас уже максимальное количество банков (3)!", ephemeral=True)
            return
            
        if profiles[user_id]["money"]["gold_coin"] < 10:
            gold_emoji = config.CURRENCY_EMOJIS.get("gold_coin", "")
            await interaction.followup.send(f"❌ Для создания банка нужно 10 {gold_emoji}!", ephemeral=True)
            return
            
        if name in banks:
            await interaction.followup.send("❌ Банк с таким названием уже существует!", ephemeral=True)
            return
            
        banks[name] = {
            "owner_id": user_id,
            "comission": 5.0,
            "service": 2.0,
            "clients": {},
            "created_at": datetime.now().isoformat()
        }
        
        profiles[user_id]["money"]["gold_coin"] -= 10
        save_profiles(profiles)
        save_banks(banks)
        
        await interaction.followup.send(f"✅ Банк '{name}' успешно создан!", ephemeral=True)
    
    elif action_value == "list":
        embed = discord.Embed(title="Список банков", color=discord.Color.blue())
        
        if not banks:
            embed.description = "Пока нет созданных банков"
        else:
            for bank_name, bank_data in banks.items():
                owner = await bot.fetch_user(int(bank_data["owner_id"]))
                embed.add_field(
                    name=f"{bank_name} (Владелец: {owner.display_name})",
                    value=f"Комиссия: {bank_data['comission']}%\nОбслуживание: {bank_data['service']}%\nКлиентов: {len(bank_data['clients'])}",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    elif action_value == "rename":
        if not name or not new_name:
            await interaction.followup.send("❌ Укажите текущее и новое название банка!", ephemeral=True)
            return
            
        if name not in banks:
            await interaction.followup.send("❌ Банк не найден!", ephemeral=True)
            return
            
        if banks[name]["owner_id"] != user_id:
            await interaction.followup.send("❌ Вы не владелец этого банка!", ephemeral=True)
            return
            
        if new_name in banks:
            await interaction.followup.send("❌ Банк с таким названием уже существует!", ephemeral=True)
            return
            
        banks[new_name] = banks.pop(name)
        save_banks(banks)
        
        await interaction.followup.send(f"✅ Банк успешно переименован в '{new_name}'!", ephemeral=True)
    
    elif action_value == "set_comission":
        if not name or set_comission is None:
            await interaction.followup.send("❌ Укажите название банка и размер комиссии!", ephemeral=True)
            return
            
        if name not in banks:
            await interaction.followup.send("❌ Банк не найден!", ephemeral=True)
            return
            
        if banks[name]["owner_id"] != user_id:
            await interaction.followup.send("❌ Вы не владелец этого банка!", ephemeral=True)
            return
            
        if set_comission < 0 or set_comission > 50:
            await interaction.followup.send("❌ Комиссия должна быть от 0% до 50%!", ephemeral=True)
            return
            
        banks[name]["comission"] = set_comission
        save_banks(banks)
        
        await interaction.followup.send(f"✅ Комиссия банка '{name}' установлена на {set_comission}%!", ephemeral=True)
    
    elif action_value == "set_service":
        if not name or set_service is None:
            await interaction.followup.send("❌ Укажите название банка и размер обслуживания!", ephemeral=True)
            return
            
        if name not in banks:
            await interaction.followup.send("❌ Банк не найден!", ephemeral=True)
            return
            
        if banks[name]["owner_id"] != user_id:
            await interaction.followup.send("❌ Вы не владелец этого банка!", ephemeral=True)
            return
            
        if set_service < 0 or set_service > 20:
            await interaction.followup.send("❌ Обслуживание должно быть от 0% до 20%!", ephemeral=True)
            return
            
        banks[name]["service"] = set_service
        save_banks(banks)
        
        await interaction.followup.send(f"✅ Обслуживание банка '{name}' установлено на {set_service}%!", ephemeral=True)
    
    elif action_value == "info":
        if not name:
            current_bank = profiles[user_id].get("bank")
            if not current_bank or current_bank not in banks:
                await interaction.followup.send("❌ Укажите название банка или установите активный банк!", ephemeral=True)
                return
            name = current_bank
            
        if name not in banks:
            await interaction.followup.send("❌ Банк не найден!", ephemeral=True)
            return
            
        bank_data = banks[name]
        owner = await bot.fetch_user(int(bank_data["owner_id"]))

        client_data = bank_data["clients"].get(user_id, create_empty_balance())

        money_values = []
        for currency in ["copper_coin", "silver_coin", "gold_coin", "platinum_coin"]:
            emoji = config.CURRENCY_EMOJIS.get(currency, "")
            money_values.append(f"{emoji} `{client_data.get(currency, 0)}`")
        balance_text = "\n".join(money_values)
        
        embed = discord.Embed(
            title=f"Информация о банке '{name}'",
            color=discord.Color.blue()
        )

        embed.add_field(name="Владелец", value=owner.mention, inline=False)
        embed.add_field(name="Комиссия за перевод", value=f"{bank_data['comission']}%", inline=True)
        embed.add_field(name="Обслуживание", value=f"{bank_data['service']}% в месяц", inline=True)
        embed.add_field(name="Клиентов", value=str(len(bank_data["clients"])), inline=False)
        embed.add_field(name="Дата создания", value=datetime.fromisoformat(bank_data["created_at"]).strftime('%d.%m.%Y %H:%M'), inline=False)
        embed.add_field(name="Ваш баланс", value=balance_text, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    else:
        await interaction.followup.send("❌ Неизвестное действие! Доступные действия: create, list, rename, set_comission, set_service, info", ephemeral=True)

@bot.tree.command(name="deposit", description="Внести деньги на свой банковский счет")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    amount="Количество",
    currency="Тип валюты"
)
@app_commands.choices(
    currency=[
        app_commands.Choice(name="Медные монеты", value="copper_coin"),
        app_commands.Choice(name="Серебряные монеты", value="silver_coin"),
        app_commands.Choice(name="Золотые монеты", value="gold_coin"),
        app_commands.Choice(name="Платиновые монеты", value="platinum_coin")
    ]
)
async def deposit_command(
    interaction: discord.Interaction,
    amount: int,
    currency: app_commands.Choice[str]
):
    await interaction.response.defer(ephemeral=True)
    profiles = load_profiles()
    banks = load_banks()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send("❌ У вас нет профиля!", ephemeral=True)
        return
        
    current_bank = profiles[user_id].get("bank")
    if not current_bank or current_bank not in banks:
        await interaction.followup.send("❌ У вас нет активного банка!", ephemeral=True)
        return
        
    if amount <= 0:
        await interaction.followup.send("❌ Сумма должна быть положительной!", ephemeral=True)
        return
        
    if profiles[user_id]["money"][currency.value] < amount:
        await interaction.followup.send(f"❌ Недостаточно {currency.name.lower()} для депозита!", ephemeral=True)
        return
    
    ensure_client_dict_format(banks, current_bank, user_id)
        
    if user_id not in banks[current_bank]["clients"]:
        banks[current_bank]["clients"][user_id] = {
            "gold_coin": 0,
            "silver_coin": 0,
            "copper_coin": 0,
            "platinum_coin": 0
        }
    
    profiles[user_id]["money"][currency.value] -= amount
    banks[current_bank]["clients"][user_id][currency.value] = banks[current_bank]["clients"][user_id].get(currency.value, 0) + amount
    
    save_profiles(profiles)
    save_banks(banks)
    
    await interaction.followup.send(
        f"✅ Успешно внесено {amount} {currency.name.lower()} в ваш банк '{current_bank}'!",
        ephemeral=True
    )

@bot.tree.command(name="exchange", description="Конвертация валют (курс 100:1)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    amount="Количество валюты для обмена",
    from_currency="Из какой валюты конвертировать",
    to_currency="В какую валюту конвертировать"
)
@app_commands.choices(
    from_currency=[
        app_commands.Choice(name="Медные монеты", value="copper"),
        app_commands.Choice(name="Серебряные монеты", value="silver"),
        app_commands.Choice(name="Золотые монеты", value="gold"),
        app_commands.Choice(name="Платиновые монеты", value="platinum")
    ],
    to_currency=[
        app_commands.Choice(name="Медные монеты", value="copper"),
        app_commands.Choice(name="Серебряные монеты", value="silver"),
        app_commands.Choice(name="Золотые монеты", value="gold"),
        app_commands.Choice(name="Платиновые монеты", value="platinum")
    ]
)
async def exchange_command(
    interaction: discord.Interaction,
    amount: int,
    from_currency: app_commands.Choice[str],
    to_currency: app_commands.Choice[str]
):
    await interaction.response.defer()
    if amount <= 0:
        await interaction.followup.send(
            "❌ Количество для обмена должно быть положительным!",
            ephemeral=True
        )
        return

    profiles = load_profiles()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send(
            "❌ У вас нет профиля! Сначала создайте его командой `/profile create:True`.",
            ephemeral=True
        )
        return

    profile = profiles[user_id]
    money = profile["money"]
    
    currency_map = {
        "copper": "copper_coin",
        "silver": "silver_coin",
        "gold": "gold_coin",
        "platinum": "platinum_coin"
    }
    
    from_curr = currency_map[from_currency.value]
    to_curr = currency_map[to_currency.value]
    
    if money[from_curr] < amount:
        await interaction.followup.send(
            f"❌ У вас недостаточно {from_currency.name.lower()} для обмена!",
            ephemeral=True
        )
        return
    
    currency_order = ["copper", "silver", "gold", "platinum"]
    from_index = currency_order.index(from_currency.value)
    to_index = currency_order.index(to_currency.value)
    
    if from_index < to_index:
        rate = 100 ** (to_index - from_index)
        if amount % rate != 0:
            await interaction.followup.send(
                f"❌ Для обмена в {to_currency.name.lower()} количество {from_currency.name.lower()} должно быть кратно {rate}!",
                ephemeral=True
            )
            return
        result_amount = amount // rate
    elif from_index > to_index:
        rate = 100 ** (from_index - to_index)
        result_amount = amount * rate
    else:
        result_amount = amount
    
    money[from_curr] = int(money[from_curr] - amount)
    money[to_curr] = int(money[to_curr] + result_amount)
    
    save_profiles(profiles)
    
    from_emoji = {
        "copper": "🟤",
        "silver": "⚪",
        "gold": "🟡",
        "platinum": "⚫"
    }[from_currency.value]
    
    to_emoji = {
        "copper": "🟤",
        "silver": "⚪",
        "gold": "🟡",
        "platinum": "⚫"
    }[to_currency.value]
    
    embed = discord.Embed(
        title="✅ Обмен валюты выполнен",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Вы обменяли",
        value=f"{from_emoji} {amount} {from_currency.name.lower()}",
        inline=False
    )
    
    embed.add_field(
        name="Получено",
        value=f"{to_emoji} {result_amount} {to_currency.name.lower()}",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="inventory", description="Просмотр инвентаря")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def inventory_command(interaction: discord.Interaction):
    await interaction.response.defer()
    inventory = load_inventory()
    user_id = str(interaction.user.id)
    
    if user_id not in inventory or not inventory[user_id]:
        await interaction.followup.send(
            embed=discord.Embed(
                title="🎒 Ваш инвентарь",
                description="Ваш инвентарь пуст!",
                color=discord.Color.red()
            ),
            ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎒 Ваш инвентарь",
        description="Нажмите на кнопку предмета для просмотра деталей",
        color=discord.Color.green()
    ).set_thumbnail(url=interaction.user.display_avatar.url)
    
    view = View(timeout=120)
    for item_id, item in inventory[user_id].items():
        short_name = item['name'][:20] + '...' if len(item['name']) > 20 else item['name']
        view.add_item(InventoryItemButton(item_id, short_name))
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="profile", description="Просмотр или создание профиля")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def profile_command(
    interaction: discord.Interaction,
    user: Optional[discord.User] = None,
    create: bool = False
):
    await interaction.response.defer()
    professions = load_professions()
    profiles = load_profiles()

    if create:
        if user:
            await interaction.followup.send(
                "❌ Нельзя использовать `create` с указанием пользователя!",
                ephemeral=True
            )
            return
        
        user_id = str(interaction.user.id)
        if user_id in profiles:
            await interaction.followup.send(
                "❌ У вас уже есть профиль!",
                ephemeral=True
            )
            return

        profiles[user_id] = {
            "group": "пользователь",
            "profession": "Бездомный",
            "energy": 100,
            "max_energy": 100,
            "level": 1,
            "exp": 0,
            "next_level_exp": 100,
            "money": {
                "copper_coin": 0,
                "silver_coin": 0,
                "gold_coin": 0,
                "platinum_coin": 0,
                "freshcoin": 0
            },
            "active_effects": {},
            "created_at": datetime.now().isoformat(),
            "last_work_time": datetime.now().isoformat(),
            "last_energy_update": datetime.now().isoformat()
        }
        save_profiles(profiles)
        await interaction.followup.send("✅ Ваш профиль успешно создан!", ephemeral=True)
        return

    target_user = user or interaction.user
    user_id = str(target_user.id)
    
    if user_id not in profiles:
        if user:
            await interaction.followup.send(
                f"❌ У пользователя {target_user.mention} нет профиля!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ У вас нет профиля! Используйте `/profile create:True` чтобы создать.",
                ephemeral=True
            )
        return
    
    profile = profiles[user_id]

    current_energy = profile.get("energy", 0)
    max_energy = profile.get("max_energy", 100)
    energy_percent = int((current_energy / max_energy) * 100) if max_energy > 0 else 0
    energy_bar = "🔵" * int(energy_percent/10) + "⚫" * (10 - int(energy_percent/10))
    
    exp_percent = int((profile["exp"] / profile["next_level_exp"]) * 100)
    progress_bar = "🟢" * int(exp_percent/10) + "⚫" * (10 - int(exp_percent/10))
    
    level_info = (
        f"⭐ **Ур. {profile['level']}** `{profile['exp']}/{profile['next_level_exp']}`\n"
        f"{progress_bar}\n\n"
        f"⚡ **Энергия** `{current_energy}/{max_energy}`\n"
        f"{energy_bar}"
    )

    embed = discord.Embed(
        title=f"👤 Профиль {target_user.display_name}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)

    group_emoji = {
        "пользователь": "👤",
        "покупатель": "💳",
        "тестер": "🔧",
        "разработчик": "👑"
    }.get(profile["group"], "❓")

    profession_data = professions.get(profile.get("profession", "Уборщик"), professions["Уборщик"])
    profession_emoji = profession_data["emoji"]

    embed.add_field(
        name="**Группа**",
        value=f"{group_emoji} {profile['group'].capitalize()}",
        inline=True
    )

    embed.add_field(
        name="**Профессия**",
        value=f"{profession_emoji} {profile.get('profession', 'Уборщик')}",
        inline=True
    )
    
    embed.add_field(
        name="**Прогресс**",
        value=level_info,
        inline=False
    )

    money_values = []
    for currency in ["copper_coin", "silver_coin", "gold_coin", "platinum_coin"]:
        emoji = config.CURRENCY_EMOJIS.get(currency, "")
        money_values.append(f"{emoji} `{profile['money'].get(currency, 0)}`")
    
    embed.add_field(
        name="**Валюта**",
        value=" ".join(money_values),
        inline=False
    )

    if profile['money'].get('freshcoin', 0) > 0:
        embed.add_field(
            name="**Другая валюта**",
            value=f"{config.CURRENCY_EMOJIS['freshcoin']} FreshCoin: {profile['money'].get('freshcoin', 0)}",
            inline=False
        )

    created_at = datetime.fromisoformat(profile["created_at"])
    embed.set_footer(text=f"Профиль создан: {created_at.strftime('%d.%m.%Y %H:%M')}")

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="set_bank", description="Выбрать банк для обслуживания")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(name="Название банка")
async def set_bank_command(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    profiles = load_profiles()
    banks = load_banks()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send("❌ У вас нет профиля!", ephemeral=True)
        return
        
    if name not in banks:
        await interaction.followup.send("❌ Банк не найден!", ephemeral=True)
        return
    
    current_bank = profiles[user_id].get("bank")
    if current_bank == name:
        await interaction.followup.send(
            f"ℹ️ Вы уже находитесь в банке '{name}'!",
            ephemeral=True
        )
        return
        
    if current_bank and current_bank in banks:
        old_balance = banks[current_bank]["clients"].get(user_id, {})
        banks[current_bank]["clients"].pop(user_id, None)
    else:
        old_balance = {}
    
    banks[name]["clients"][user_id] = old_balance
    profiles[user_id]["bank"] = name
    
    save_profiles(profiles)
    save_banks(banks)
    
    await interaction.followup.send(
        f"✅ Вы успешно выбрали банк '{name}' для обслуживания!",
        ephemeral=True
    )

@bot.tree.command(name="set_group", description="Установить группу пользователя (только для создателей)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    user="Пользователь",
    group="Группа для установки"
)
async def set_group_command(
    interaction: discord.Interaction,
    user: discord.User,
    group: Literal["разработчик", "тестер", "покупатель", "пользователь"]
):
    await interaction.response.defer(ephemeral=True)
    if not hasattr(config, 'ALLOWED_ID') or interaction.user.id not in config.ALLOWED_ID:
        await interaction.followup.send(
            "❌ У вас нет прав для этой команды!",
            ephemeral=True
        )
        return
    
    profiles = load_profiles()
    user_id = str(user.id)
    
    if user_id not in profiles:
        await interaction.followup.send(
            f"❌ У пользователя {user.mention} нет профиля!",
            ephemeral=True
        )
        return

    profiles[user_id]["group"] = group
    save_profiles(profiles)
    
    await interaction.followup.send(
        f"✅ Группа пользователя {user.mention} изменена на `{group}`!",
        ephemeral=True
    )

@bot.tree.command(name="shop", description="Магазин")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def shop_command(interaction: discord.Interaction, black_store: bool = False):
    await interaction.response.defer()
    profiles = load_profiles()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Ошибка",
                description="У вас нет профиля!",
                color=discord.Color.red()
            ),
            ephemeral=True)
        return
    
    profile = profiles[user_id]
    inventory = load_inventory().get(user_id, {})
    has_pass = any(item.get("type") == "black_market_pass" for item in inventory.values())
    
    if black_store and not has_pass:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Доступ запрещен",
                description="У вас нет доступа к черному рынку!",
                color=discord.Color.red()
            ),
            ephemeral=True)
        return
    
    await show_shop_categories(interaction, black_store)

@bot.tree.command(name="treasure", description="Поиск сокровищ в различных локациях")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def treasure_command(interaction: discord.Interaction):
    await interaction.response.defer()
    treasure_data = load_treasure_data()
    profiles = load_profiles()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Нет профиля",
                description="У вас нет профиля! Создайте его командой `/profile create:True`",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return
    
    profile = profiles[user_id]
    user_level = profile.get("level", 1)
    
    available_locations = {
        loc_id: loc_data 
        for loc_id, loc_data in treasure_data.items() 
        if loc_data.get('required_level', 1) <= user_level
    }
    
    if not available_locations:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Нет доступных локаций",
                description="У вас недостаточный уровень для доступа к любым локациям!",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return
    
    first_loc_id = next(iter(available_locations))
    location = available_locations[first_loc_id]
    
    embed = discord.Embed(
        title=f"🔍 {location.get('name', 'Локация')} (Ур. {location.get('required_level', 1)}+)",
        description=location.get('description', 'Описание отсутствует'),
        color=discord.Color.blue()
    )
    
    requirements = []
    if location.get('detector_required', False):
        req = "🔹 Металлоискатель"
        if 'detector_level' in location:
            req += f" (ур. {location['detector_level']}+)"
        requirements.append(req)
    
    if requirements:
        embed.add_field(name="Требования", value="\n".join(requirements), inline=False)
    
    possible_items = location.get('possible_items', [])
    if possible_items:
        items_text = []
        for item in possible_items[:5]:
            chance = item.get('chance', 1)
            items_text.append(f"▫ {item['name']} (шанс: {chance*100:.1f}%)")
        
        if len(possible_items) > 5:
            items_text.append(f"... и еще {len(possible_items)-5} предметов")
        
        embed.add_field(name="Возможные находки", value="\n".join(items_text), inline=False)
    
    view = View(timeout=120)
    view.add_item(SearchButton(first_loc_id))
    
    if len(available_locations) > 1:
        view.add_item(LocationSelector(available_locations, first_loc_id))
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="transfer", description="Перевести деньги другому пользователю")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    amount="Количество",
    currency="Тип валюты",
    user="Получатель"
)
@app_commands.choices(
    currency=[
        app_commands.Choice(name="Медные монеты", value="copper_coin"),
        app_commands.Choice(name="Серебряные монеты", value="silver_coin"),
        app_commands.Choice(name="Золотые монеты", value="gold_coin"),
        app_commands.Choice(name="Платиновые монеты", value="platinum_coin")
    ]
)
async def transfer_command(
    interaction: discord.Interaction,
    amount: int,
    currency: app_commands.Choice[str],
    user: discord.User
):
    await interaction.response.defer(ephemeral=True)
    profiles = load_profiles()
    banks = load_banks()
    user_id = str(interaction.user.id)
    target_user_id = str(user.id)
    
    if user_id not in profiles:
        await interaction.followup.send("❌ У вас нет профиля!", ephemeral=True)
        return
        
    if target_user_id not in profiles:
        await interaction.followup.send("❌ У получателя нет профиля!", ephemeral=True)
        return
        
    if amount <= 0:
        await interaction.followup.send("❌ Сумма должна быть положительной!", ephemeral=True)
        return
    
    sender_bank = profiles[user_id].get("bank")
    receiver_bank = profiles[target_user_id].get("bank")
    
    if not sender_bank or sender_bank not in banks:
        await interaction.followup.send("❌ У вас нет активного банка!", ephemeral=True)
        return
        
    if not receiver_bank or receiver_bank not in banks:
        await interaction.followup.send("❌ У получателя нет активного банка!", ephemeral=True)
        return
    
    ensure_client_dict_format(banks, sender_bank, user_id)
    
    if user_id not in banks[sender_bank]["clients"]:
        banks[sender_bank]["clients"][user_id] = create_empty_balance()
    
    sender_balance = banks[sender_bank]["clients"][user_id]
    
    if sender_balance.get(currency.value, 0) < amount:
        await interaction.followup.send(f"❌ Недостаточно {currency.name.lower()} на вашем счету!", ephemeral=True)
        return
    
    is_bank_owner = (banks[sender_bank]["owner_id"] == user_id)
    comission_percent = 0 if is_bank_owner else banks[sender_bank]["comission"]
    comission_amount = amount * comission_percent / 100
    
    main_comission = int(comission_amount)
    fractional_comission = comission_amount - main_comission
    
    fractional_amount = 0
    fractional_currency = None
    
    if fractional_comission > 0:
        if currency.value == "platinum_coin":
            fractional_amount = int(fractional_comission * 100)
            fractional_currency = "gold_coin"
        elif currency.value == "gold_coin":
            fractional_amount = int(fractional_comission * 100)
            fractional_currency = "silver_coin"
        elif currency.value == "silver_coin":
            fractional_amount = int(fractional_comission * 100)
            fractional_currency = "copper_coin"
    
    total_main_comission = main_comission
    total_fractional_comission = 0
    
    if fractional_currency:
        if sender_balance.get(fractional_currency, 0) < fractional_amount:
            total_main_comission += 1
            converted_amount = 100 if fractional_currency != "copper_coin" else 10000
            total_fractional_comission = converted_amount - fractional_amount
        else:
            total_fractional_comission = fractional_amount
    
    total_to_deduct = amount + total_main_comission
    
    if sender_balance.get(currency.value, 0) < total_to_deduct:
        await interaction.followup.send(f"❌ Недостаточно средств с учетом комиссии!", ephemeral=True)
        return
    
    sender_balance[currency.value] -= total_to_deduct
    
    ensure_client_dict_format(banks, receiver_bank, target_user_id)
    
    if target_user_id not in banks[receiver_bank]["clients"]:
        banks[receiver_bank]["clients"][target_user_id] = create_empty_balance()
    
    banks[receiver_bank]["clients"][target_user_id][currency.value] += amount
    
    if comission_percent > 0:
        owner_id = banks[sender_bank]["owner_id"]
        ensure_client_dict_format(banks, sender_bank, owner_id)
        
        if owner_id not in banks[sender_bank]["clients"]:
            banks[sender_bank]["clients"][owner_id] = create_empty_balance()
        
        banks[sender_bank]["clients"][owner_id][currency.value] += main_comission
        
        if fractional_currency and total_fractional_comission > 0:
            if fractional_amount > 0:
                if total_fractional_comission != fractional_amount:
                    change = fractional_amount - total_fractional_comission
                    if fractional_currency == "gold_coin":
                        sender_balance["silver_coin"] = sender_balance.get("silver_coin", 0) + change
                    elif fractional_currency == "silver_coin":
                        sender_balance["copper_coin"] = sender_balance.get("copper_coin", 0) + change
                
                banks[sender_bank]["clients"][owner_id][fractional_currency] = banks[sender_bank]["clients"][owner_id].get(fractional_currency, 0) + total_fractional_comission
    
    save_banks(banks)
    
    if comission_percent > 0:
        comission_msg = []
        if main_comission > 0:
            comission_msg.append(f"{main_comission} {currency.name.lower()}")
        if total_fractional_comission > 0:
            fractional_name = next(c.name for c in transfer_command._params['currency'].choices if c.value == fractional_currency)
            comission_msg.append(f"{total_fractional_comission} {fractional_name.lower()}")
        
        await interaction.followup.send(
            f"✅ Успешно переведено {amount} {currency.name.lower()} пользователю {user.mention}!\n"
            f"Комиссия: {' + '.join(comission_msg)}",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"✅ Успешно переведено {amount} {currency.name.lower()} пользователю {user.mention} (без комиссии)!",
            ephemeral=True
        )

@bot.tree.command(name="withdraw", description="Снять деньги со своего банковского счета")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    amount="Количество",
    currency="Тип валюты"
)
@app_commands.choices(
    currency=[
        app_commands.Choice(name="Медные монеты", value="copper_coin"),
        app_commands.Choice(name="Серебряные монеты", value="silver_coin"),
        app_commands.Choice(name="Золотые монеты", value="gold_coin"),
        app_commands.Choice(name="Платиновые монеты", value="platinum_coin")
    ]
)
async def withdraw_command(
    interaction: discord.Interaction,
    amount: int,
    currency: app_commands.Choice[str]
):
    await interaction.response.defer(ephemeral=True)
    profiles = load_profiles()
    banks = load_banks()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send("❌ У вас нет профиля!", ephemeral=True)
        return
        
    current_bank = profiles[user_id].get("bank")
    if not current_bank or current_bank not in banks:
        await interaction.followup.send("❌ У вас нет активного банка!", ephemeral=True)
        return
        
    if amount <= 0:
        await interaction.followup.send("❌ Сумма должна быть положительной!", ephemeral=True)
        return
    
    ensure_client_dict_format(banks, current_bank, user_id)
        
    if user_id not in banks[current_bank]["clients"]:
        banks[current_bank]["clients"][user_id] = {
            "gold_coin": 0,
            "silver_coin": 0,
            "copper_coin": 0,
            "platinum_coin": 0
        }
    
    if banks[current_bank]["clients"][user_id].get(currency.value, 0) < amount:
        await interaction.followup.send(f"❌ Недостаточно {currency.name.lower()} на вашем счету!", ephemeral=True)
        return
        
    banks[current_bank]["clients"][user_id][currency.value] -= amount
    profiles[user_id]["money"][currency.value] += amount
    
    if banks[current_bank]["clients"][user_id][currency.value] == 0:
        del banks[current_bank]["clients"][user_id][currency.value]
    
    save_profiles(profiles)
    save_banks(banks)
    
    await interaction.followup.send(
        f"✅ Успешно снято {amount} {currency.name.lower()} из вашего банка '{current_bank}'!",
        ephemeral=True
    )

@bot.tree.command(name="work", description="Выйти на работу.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def work_command(interaction: discord.Interaction, profession_list: bool = False):
    if profession_list:
        await interaction.response.defer()
        professions = load_professions()
        embed = discord.Embed(
            title="📊 Доступные профессии",
            color=discord.Color.gold()
        )
        
        for prof, data in professions.items():
            money_info = []
            for currency, amount in data["min_money"].items():
                if amount > 0 or data["max_money"].get(currency, 0) > 0:
                    currency_emoji = config.CURRENCY_EMOJIS.get(currency, "")
                    min_amount = amount
                    max_amount = data["max_money"].get(currency, 0)
                    money_info.append(f"{currency_emoji} {min_amount}-{max_amount}")
            
            embed.add_field(
                name=f"{data['emoji']} {prof} (Ур. {data['min_level']}+)",
                value=(
                    f"**Зарплата:** {' '.join(money_info)}\n"
                    f"**Опыт:** {data['min_exp']}-{data['max_exp']}\n"
                    f"**Расход энергии:** {data['energy_cost']}"
                ),
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        return

    await interaction.response.defer()
    profiles = load_profiles()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Ошибка",
                description="У вас нет профиля! Используйте `/profile create:True` чтобы создать.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return
    
    profile = profiles[user_id]
    max_energy = profile.get("max_energy", 100)
    energy_cost = load_professions().get(profile.get("profession", "Бездомный"), {}).get("energy_cost", 10)
    
    if profile.get("energy", max_energy) < energy_cost:
        embed = discord.Embed(
            title="❌ Недостаточно энергии",
            description=f"У вас {profile.get('energy', max_energy)}/{max_energy} энергии. Нужно {energy_cost}.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    work_button = WorkButton(user_id)
    view = View(timeout=120)
    view.add_item(work_button)
    
    embed = discord.Embed(
        title="💼 Работа",
        description=f"Нажмите кнопку, чтобы работать как **{profile.get('profession', 'Бездомный')}**\nЭнергии достаточно: {profile.get('energy', max_energy)}/{max_energy}",
        color=discord.Color.blue()
    )
    
    await interaction.followup.send(embed=embed, view=view)

class WorkButton(Button):
    def __init__(self, user_id: str):
        super().__init__(label="Работать", style=discord.ButtonStyle.green, emoji="💼")
        self.user_id = user_id
    
    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Это не ваша кнопка!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        profiles = load_profiles()
        user_id = str(interaction.user.id)
        
        if user_id not in profiles:
            await interaction.followup.send("❌ Профиль не найден!", ephemeral=True)
            return
        
        profile = profiles[user_id]
        max_energy = profile.get("max_energy", 100)
        
        if "energy" not in profile:
            profile["energy"] = max_energy
        if "last_energy_update" not in profile:
            profile["last_energy_update"] = datetime.now().isoformat()
        
        professions = load_professions()
        current_profession = profile.get("profession", "Бездомный")
        prof_data = professions.get(current_profession, professions["Бездомный"])
        energy_cost = prof_data["energy_cost"]
        
        if profile.get("energy", max_energy) < energy_cost:
            embed = discord.Embed(
                title="❌ Недостаточно энергии",
                description=f"У вас {profile.get('energy', max_energy)}/{max_energy} энергии. Нужно {energy_cost}.",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=embed, view=None)
            return
        
        profile["energy"] = max(0, profile.get("energy", max_energy) - energy_cost)
        
        work_message = random.choice(prof_data["work_messages"])
        
        event_type = random.choices(
            ["positive", "negative", "neutral"],
            weights=[config.EVENT_CHANCES["positive"], config.EVENT_CHANCES["negative"], config.EVENT_CHANCES["neutral"]]
        )[0]
        
        event = random.choice(prof_data["events"][event_type])
        event_text = event.get("text", "")
        
        energy_change = 0
        if "energy_bonus" in event:
            energy_change += event["energy_bonus"]
        if "energy_penalty" in event:
            energy_change -= event["energy_penalty"]
        
        if energy_change != 0:
            profile["energy"] = max(0, min(max_energy, profile["energy"] + energy_change))
        
        exp_multiplier = 1.0
        money_multiplier = 1.0
        
        if "active_effects" in profile:
            now = datetime.now()
            
            if "exp_multiplier" in profile["active_effects"]:
                expires = datetime.fromisoformat(profile["active_effects"]["exp_multiplier"]["expires"])
                if expires > now:
                    exp_multiplier = profile["active_effects"]["exp_multiplier"]["value"]
                else:
                    del profile["active_effects"]["exp_multiplier"]
            
            if "money_multiplier" in profile["active_effects"]:
                expires = datetime.fromisoformat(profile["active_effects"]["money_multiplier"]["expires"])
                if expires > now:
                    money_multiplier = profile["active_effects"]["money_multiplier"]["value"]
                else:
                    del profile["active_effects"]["money_multiplier"]
            
            if not profile["active_effects"]:
                del profile["active_effects"]
        
        money_earned = {}
        for currency in prof_data["min_money"]:
            min_val = prof_data["min_money"][currency]
            max_val = prof_data["max_money"][currency]
            if max_val > 0:
                base_amount = random.randint(min_val, max_val)
                
                if "money_multiplier" in event:
                    base_amount = int(base_amount * event["money_multiplier"])
                if "money_bonus" in event and currency in event["money_bonus"]:
                    base_amount += event["money_bonus"][currency]
                if "money_penalty" in event and currency in event["money_penalty"]:
                    base_amount = max(0, base_amount - event["money_penalty"][currency])
                
                money_earned[currency] = int(base_amount * money_multiplier)
                profile["money"][currency] = profile["money"].get(currency, 0) + money_earned[currency]
        
        exp_earned = random.randint(prof_data["min_exp"], prof_data["max_exp"])
        if "exp_multiplier" in event:
            exp_earned = int(exp_earned * event["exp_multiplier"])
        exp_earned = int(exp_earned * exp_multiplier)
        profile["exp"] += exp_earned
        
        profile["last_energy_update"] = datetime.now().isoformat()
        
        level_up = False
        while profile["exp"] >= profile["next_level_exp"]:
            profile["exp"] -= profile["next_level_exp"]
            profile["level"] += 1
            profile["next_level_exp"] = int(profile["next_level_exp"] * 1.3)
            level_up = True
        
        available_professions = []
        for prof, data in professions.items():
            if profile["level"] >= data["min_level"]:
                available_professions.append(prof)
        
        new_profession = None
        for prof in reversed(sorted(available_professions, key=lambda x: professions[x]["min_level"])):
            if professions[prof]["min_level"] > professions.get(current_profession, {}).get("min_level", 0):
                new_profession = prof
                profile["profession"] = new_profession
                break
        
        save_profiles(profiles)
        
        money_info = []
        for currency, amount in money_earned.items():
            if amount > 0:
                currency_emoji = config.CURRENCY_EMOJIS.get(currency, "")
                money_info.append(f"{currency_emoji} {amount}")
        
        embed = discord.Embed(
            title=f"💼 Результаты работы",
            color=discord.Color.green() if event_type == "positive" else 
                 discord.Color.red() if event_type == "negative" else 
                 discord.Color.blue()
        )
        
        embed.add_field(
            name="Профессия",
            value=f"{prof_data['emoji']} {current_profession}",
            inline=False
        )
        
        embed.add_field(
            name=work_message,
            value=f"**Событие:** {event_text}",
            inline=False
        )
        
        if money_info:
            embed.add_field(
                name="💰 Заработано",
                value="\n".join(money_info),
                inline=True
            )
        
        embed.add_field(
            name="✨ Опыт",
            value=str(exp_earned),
            inline=True
        )
        
        energy_bar = "🔵" * int(profile["energy"] / (max_energy / 10)) + "⚫" * (10 - int(profile["energy"] / (max_energy / 10)))
        embed.add_field(
            name="⚡ Энергия",
            value=f"{profile['energy']}/{max_energy}\n{energy_bar}",
            inline=False
        )
        
        if exp_multiplier > 1 or money_multiplier > 1:
            bonus_info = []
            if exp_multiplier > 1:
                bonus_info.append(f"Множитель опыта: x{exp_multiplier}")
            if money_multiplier > 1:
                bonus_info.append(f"Множитель денег: x{money_multiplier}")
            embed.add_field(
                name="⚡ Активные бонусы",
                value="\n".join(bonus_info),
                inline=False
            )
        
        if energy_change > 0:
            embed.add_field(name="", value=f"🔋 Получено +{energy_change} энергии", inline=False)
        elif energy_change < 0:
            embed.add_field(name="", value=f"💢 Потеряно {abs(energy_change)} энергии", inline=False)
        
        if level_up:
            embed.set_footer(text="🎉 Поздравляем с повышением уровня!")
        
        if new_profession:
            new_prof_data = professions[new_profession]
            embed.add_field(
                name="🎩 Новая профессия!",
                value=f"Теперь вы **{new_profession}** {new_prof_data['emoji']}\nДоступно с {new_prof_data['min_level']} уровня",
                inline=False
            )
        
        new_energy_cost = load_professions().get(profile.get("profession", "Бездомный"), {}).get("energy_cost", 10)
        if profile["energy"] >= new_energy_cost:
            new_button = WorkButton(user_id)
            new_view = View(timeout=120)
            new_view.add_item(new_button)
            await interaction.edit_original_response(embed=embed, view=new_view)
        else:
            await interaction.edit_original_response(embed=embed, view=None)

@bot.tree.command(name="casino", description="Казино с различными играми")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    action="Выберите действие",
    amount="Количество фишек для покупки/продажи/ставки",
    choice="Выбор для наперстков (1-3)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="меню", value="menu"),
    app_commands.Choice(name="купить", value="buy"),
    app_commands.Choice(name="продать", value="sell"),
    app_commands.Choice(name="слоты", value="slots"),
    app_commands.Choice(name="наперстки", value="thimbles"),
    app_commands.Choice(name="блэкджек", value="blackjack")
])
async def casino_command(
    interaction: discord.Interaction,
    action: str,
    amount: Optional[int] = None,
    choice: Optional[int] = None
):
    await interaction.response.defer()
    
    profiles = load_profiles()
    casino_settings = load_casino_settings()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        embed = discord.Embed(
            title="❌ Ошибка",
            description="У вас нет профиля! Создайте его командой `/profile create:True`",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    profile = profiles[user_id]
    
    if "casino_chips" not in profile:
        profile["casino_chips"] = 0
    
    if action == "menu":
        embed = discord.Embed(
            title="🎰 Казино",
            description=f"Ваш баланс фишек: **{profile['casino_chips']}** 🪙",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🎮 Игры",
            value=(
                "**1. Слоты** 🎰\n"
                "Крутите колесо, собирайте комбинации!\n"
                "Используйте: `/casino action:slots amount:<ставка>`\n\n"
                
                "**2. Наперстки** 🥜\n"
                "Угадайте, под каким наперстком шарик!\n"
                "Используйте: `/casino action:thimbles amount:<ставка> choice:<1-3>`\n\n"
                
                "**3. Блэкджек** ♠️\n"
                "Наберите 21 или больше дилера!\n"
                "Используйте: `/casino action:blackjack amount:<ставка>`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💰 Обмен валюты",
            value=(
                "**Курс обмена:**\n"
                "1 🪙 = 1000 медных\n"
                "1 🪙 = 100 серебряных\n"
                "1 🪙 = 1 золотая\n"
                "100 🪙 = 1 платиновая\n\n"
                "**Купить фишки:** `/casino action:buy amount:<количество>`\n"
                "**Продать фишки:** `/casino action:sell amount:<количество>`"
            ),
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
    
    elif action == "buy":
        if amount is None or amount <= 0:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Укажите положительное количество фишек для покупки!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if not ChipConverter.can_buy_chips(profile["money"], amount):
            embed = discord.Embed(
                title="❌ Недостаточно средств",
                description="У вас недостаточно монет для покупки указанного количества фишек!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        profile["money"] = ChipConverter.deduct_money_for_chips(profile["money"], amount)
        profile["casino_chips"] += amount
        
        save_profiles(profiles)
        
        embed = discord.Embed(
            title="✅ Успешная покупка",
            description=f"Вы купили **{amount}** фишек 🪙\nТеперь у вас **{profile['casino_chips']}** фишек",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    
    elif action == "sell":
        if amount is None or amount <= 0:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Укажите положительное количество фишек для продажи!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if profile["casino_chips"] < amount:
            embed = discord.Embed(
                title="❌ Недостаточно фишек",
                description=f"У вас только {profile['casino_chips']} фишек!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        money_gained = ChipConverter.chips_to_money(amount)
        profile["casino_chips"] -= amount
        
        for currency, value in money_gained.items():
            if value > 0:
                profile["money"][currency] = profile["money"].get(currency, 0) + value
        
        save_profiles(profiles)
        
        money_message = []
        for currency, value in money_gained.items():
            if value > 0:
                emoji = config.CURRENCY_EMOJIS.get(currency, "")
                money_message.append(f"{emoji} {value}")
        
        embed = discord.Embed(
            title="✅ Успешная продажа",
            description=f"Вы продали **{amount}** фишек 🪙\nПолучено: {' '.join(money_message)}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Осталось фишек: {profile['casino_chips']}")
        await interaction.followup.send(embed=embed)
    
    elif action == "slots":
        if amount is None or amount <= 0:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Укажите ставку!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if profile["casino_chips"] < amount:
            embed = discord.Embed(
                title="❌ Недостаточно фишек",
                description=f"У вас только {profile['casino_chips']} фишек!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        profile["casino_chips"] -= amount
        save_profiles(profiles)
        
        slots_game = SlotsGame(casino_settings)
        result, multiplier = slots_game.spin()
        
        winnings = amount * multiplier if multiplier > 0 else 0
        
        if winnings > 0:
            profile["casino_chips"] += winnings
            save_profiles(profiles)
        
        embed = discord.Embed(
            title="🎰 Игровые автоматы",
            description=f"Ставка: **{amount}** фишек 🪙",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Результат",
            value=f"**{result[0]} | {result[1]} | {result[2]}**",
            inline=False
        )
        
        if winnings > 0:
            if result == slots_game.jackpot_combination:
                embed.add_field(
                    name="🎉 ДЖЕКПОТ! 🎉",
                    value=f"Вы выиграли **{winnings}** фишек! (x{multiplier})",
                    inline=False
                )
                embed.color = discord.Color.from_rgb(255, 215, 0)
            
            elif multiplier == 1:
                embed.add_field(
                    name="🎊 Небольшой выигрыш!",
                    value=f"Вы выиграли **{winnings}** фишек! (x{multiplier})",
                    inline=False
                )
                embed.color = discord.Color.gold()
            
            else:
                embed.add_field(
                    name="✅ Выигрыш!",
                    value=f"Вы выиграли **{winnings}** фишек! (x{multiplier})",
                    inline=False
                )
                embed.color = discord.Color.green()
        
        else:
            embed.add_field(
                name="❌ Проигрыш",
                value="Повезет в следующий раз!",
                inline=False
            )
            embed.color = discord.Color.red()
        
        embed.set_footer(text=f"Баланс: {profile['casino_chips']} фишек")
        await interaction.followup.send(embed=embed)
    
    elif action == "thimbles":
        if amount is None or amount <= 0:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Укажите ставку!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if choice is None or choice < 1 or choice > 3:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Укажите выбор от 1 до 3!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if profile["casino_chips"] < amount:
            embed = discord.Embed(
                title="❌ Недостаточно фишек",
                description=f"У вас только {profile['casino_chips']} фишек!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        profile["casino_chips"] -= amount
        save_profiles(profiles)
        
        thimbles_game = ThimblesGame(casino_settings)
        won, ball_position = thimbles_game.play(choice)
        
        if won:
            winnings = amount * thimbles_game.win_multiplier
            profile["casino_chips"] += winnings
            save_profiles(profiles)
        else:
            winnings = 0
        
        embed = discord.Embed(
            title="🥜 Наперстки",
            description=f"Ставка: **{amount}** фишек 🪙\nВаш выбор: **{choice}**",
            color=discord.Color.gold()
        )
        
        thimbles_display = []
        for i in range(1, 4):
            if i == ball_position:
                thimbles_display.append(f"[🥜] Шарик здесь!" if i == choice else "[🥜]")
            else:
                thimbles_display.append(f"[ ] Пусто" if i == choice else "[ ]")
        
        embed.add_field(
            name="Результат",
            value="\n".join(thimbles_display),
            inline=False
        )
        
        if won:
            embed.add_field(
                name="✅ Вы выиграли!",
                value=f"Шарик под наперстком **{ball_position}**!\nВыигрыш: **{winnings}** фишек! (x{thimbles_game.win_multiplier})",
                inline=False
            )
            embed.color = discord.Color.green()
        else:
            embed.add_field(
                name="❌ Вы проиграли",
                value=f"Шарик был под наперстком **{ball_position}**!",
                inline=False
            )
            embed.color = discord.Color.red()
        
        embed.set_footer(text=f"Баланс: {profile['casino_chips']} фишек")
        await interaction.followup.send(embed=embed)
    
    elif action == "blackjack":
        if amount is None or amount <= 0:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Укажите ставку!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        min_bet = casino_settings["blackjack"]["min_bet"]
        max_bet = casino_settings["blackjack"]["max_bet"]
        
        if amount < min_bet:
            embed = discord.Embed(
                title="❌ Ошибка",
                description=f"Минимальная ставка: {min_bet} фишек!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if amount > max_bet:
            embed = discord.Embed(
                title="❌ Ошибка",
                description=f"Максимальная ставка: {max_bet} фишек!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if profile["casino_chips"] < amount:
            embed = discord.Embed(
                title="❌ Недостаточно фишек",
                description=f"У вас только {profile['casino_chips']} фишек!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        profile["casino_chips"] -= amount
        save_profiles(profiles)
        
        bj_game = BlackjackGame(casino_settings)
        
        player_hand = [bj_game.draw_card(), bj_game.draw_card()]
        dealer_hand = [bj_game.draw_card(), bj_game.draw_card()]
        
        player_value = bj_game.calculate_hand_value(player_hand)
        dealer_value = bj_game.calculate_hand_value([dealer_hand[0]])
        
        player_blackjack = player_value == 21
        dealer_blackjack = bj_game.calculate_hand_value(dealer_hand) == 21
        
        class BlackjackView(discord.ui.View):
            def __init__(self, game, player_hand, dealer_hand, bet, user_id):
                super().__init__(timeout=60)
                self.game = game
                self.player_hand = player_hand
                self.dealer_hand = dealer_hand
                self.bet = bet
                self.user_id = user_id
                self.standing = False
            
            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return str(interaction.user.id) == self.user_id
            
            @discord.ui.button(label="Взять карту", style=discord.ButtonStyle.primary, emoji="🃏")
            async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer()
                self.player_hand.append(self.game.draw_card())
                player_value = self.game.calculate_hand_value(self.player_hand)
                
                if player_value > 21:
                    await self.end_game(interaction, "bust")
                else:
                    await self.update_game(interaction, False)
            
            @discord.ui.button(label="Остановиться", style=discord.ButtonStyle.secondary, emoji="✋")
            async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer()
                self.standing = True
                await self.end_game(interaction, "stand")
            
            async def update_game(self, interaction: discord.Interaction, final: bool = False):
                player_value = self.game.calculate_hand_value(self.player_hand)
                dealer_value = self.game.calculate_hand_value([self.dealer_hand[0]]) if not final else self.game.calculate_hand_value(self.dealer_hand)
                
                embed = discord.Embed(
                    title="♠️ Блэкджек",
                    description=f"Ставка: **{self.bet}** фишек 🪙",
                    color=discord.Color.dark_green()
                )
                
                embed.add_field(
                    name="Ваша рука",
                    value=f"{' '.join(self.player_hand)}\n**Сумма: {player_value}**",
                    inline=False
                )
                
                if final:
                    embed.add_field(
                        name="Рука дилера",
                        value=f"{' '.join(self.dealer_hand)}\n**Сумма: {dealer_value}**",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Рука дилера",
                        value=f"{self.dealer_hand[0]} [?]\n**Сумма: {dealer_value}+**",
                        inline=False
                    )
                
                if not final:
                    embed.set_footer(text="Выберите действие:")
                
                await interaction.edit_original_response(embed=embed, view=self if not final else None)
            
            async def end_game(self, interaction: discord.Interaction, reason: str):
                profiles = load_profiles()
                profile = profiles.get(self.user_id)
                
                if reason == "bust":
                    result = "❌ Перебор! Вы проиграли."
                    winnings = 0
                else:
                    self.dealer_hand = self.game.dealer_turn(self.dealer_hand)
                    player_value = self.game.calculate_hand_value(self.player_hand)
                    dealer_value = self.game.calculate_hand_value(self.dealer_hand)
                    
                    if dealer_value > 21:
                        result = "✅ Дилер перебрал! Вы выиграли!"
                        winnings = self.bet * 2
                    elif player_value > dealer_value:
                        result = "✅ Вы выиграли!"
                        winnings = self.bet * 2
                    elif player_value == dealer_value:
                        result = "🤝 Ничья! Ставка возвращена."
                        winnings = self.bet
                    else:
                        result = "❌ Вы проиграли!"
                        winnings = 0
                
                if winnings > 0:
                    profile["casino_chips"] += winnings
                    profiles[self.user_id] = profile
                    save_profiles(profiles)
                
                await self.update_game(interaction, True)
                
                result_embed = discord.Embed(
                    title="Результат игры",
                    description=f"{result}\n\nВыигрыш: **{winnings}** фишек\nБаланс: **{profile['casino_chips']}** фишек",
                    color=discord.Color.green() if winnings > self.bet else discord.Color.red() if winnings == 0 else discord.Color.gold()
                )
                
                await interaction.followup.send(embed=result_embed)
        
        embed = discord.Embed(
            title="♠️ Блэкджек",
            description=f"Ставка: **{amount}** фишек 🪙",
            color=discord.Color.dark_green()
        )
        
        embed.add_field(
            name="Ваша рука",
            value=f"{' '.join(player_hand)}\n**Сумма: {player_value}**",
            inline=False
        )
        
        embed.add_field(
            name="Рука дилера",
            value=f"{dealer_hand[0]} [?]\n**Сумма: {dealer_value}+**",
            inline=False
        )
        
        if player_blackjack and not dealer_blackjack:
            winnings = int(amount * 2.5)
            profile["casino_chips"] += winnings
            save_profiles(profiles)
            
            result_embed = discord.Embed(
                title="🎉 БЛЭКДЖЕК! 🎉",
                description=f"Поздравляем! У вас блэкджек!\n\nВыигрыш: **{winnings}** фишек (3:2)\nБаланс: **{profile['casino_chips']}** фишек",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            await interaction.followup.send(embed=result_embed)
            return
        
        view = BlackjackView(bj_game, player_hand, dealer_hand, amount, user_id)
        await interaction.followup.send(embed=embed, view=view)