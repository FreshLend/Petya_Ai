import json
import random
import discord
import config
from datetime import datetime
from discord.ui import Button, Modal, Select, TextInput, View

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
        shop_data = load_shop()
        categories = shop_data.get("categories", {})

        embed = discord.Embed(
            title="🔮 Категории чёрного рынка" if self.black_store else "🏪 Категории магазина",
            description="Выберите категорию для просмотра товаров",
            color=discord.Color.dark_purple() if self.black_store else discord.Color.blue()
        ).set_thumbnail(url=interaction.user.display_avatar.url)

        view = View(timeout=180)
        view.add_item(CategorySelect(categories, self.black_store))

        profiles = load_profiles()
        user_id = str(interaction.user.id)
        inventory = load_inventory().get(user_id, {})
        has_pass = any(item.get("type") == "black_market_pass" for item in inventory.values())

        if not self.black_store and profiles.get(user_id, {}).get("level", 1) >= 15 and not has_pass:
            view.add_item(BuyPassButton())

        await interaction.response.edit_message(embed=embed, view=view)

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
            profiles[user_id]["money"] = add_money(profiles[user_id]["money"], total_price)
        else:
            profiles[user_id]["money"] = add_money(profiles[user_id]["money"], {"gold_coin": total_price})
        
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
        bundle_contents = item.get("contains")
        if not bundle_contents:
            shop_data = load_shop()
            for cat in shop_data.get("categories", {}).values():
                for shop_id, shop_item in cat.get("items", {}).items():
                    if shop_item.get("name") == item["name"] and "contains" in shop_item:
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
    
    if not can_afford(profile["money"], config.BLACK_MARKET_PASS):
        insufficient_currencies = []
        for currency, amount in config.BLACK_MARKET_PASS.items():
            if profile["money"].get(currency, 0) < amount:
                insufficient_currencies.append(
                    f"{amount} {config.CURRENCY_EMOJIS.get(currency, currency)}")
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
    
    profile["money"] = deduct_money(profile["money"], config.BLACK_MARKET_PASS)
    
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

        if isinstance(price_info, dict):
            total_price = {curr: int(amt * quantity) for curr, amt in price_info.items()}
        else:
            total_price = {"gold_coin": int(price_info * quantity)}
        
        if not can_afford(profile["money"], total_price):
            insufficient_currencies = []
            for currency, amount in total_price.items():
                if profile["money"].get(currency, 0) < amount:
                    insufficient_currencies.append(
                        f"{amount} {config.CURRENCY_EMOJIS.get(currency, currency)}")
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Недостаточно средств",
                    description=f"Не хватает: {', '.join(insufficient_currencies)}",
                    color=discord.Color.red()
                ),
                ephemeral=True)
            return

        profile["money"] = deduct_money(profile["money"], total_price)

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