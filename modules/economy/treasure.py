import json
import random
import discord
import config
from datetime import datetime
from discord.ui import Button, Select, View

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
        
        if not can_afford(profiles[user_id]['money'], repair_cost):
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Недостаточно денег",
                    description=f"Для починки нужно: {self.format_cost(repair_cost)}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        profiles[user_id]['money'] = deduct_money(profiles[user_id]['money'], repair_cost)
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
        
        broken_text = ""
        if best_detector:
            durability_loss = random.randint(10, 25)
            new_durability = max(0, best_detector['details'].get('durability', 1000) - durability_loss + durability_change)
            best_detector['details']['durability'] = new_durability
            
            if new_durability <= 0:
                broken_text = "\n\n💥 Ваш металлоискатель сломался!"
        
        if user_id not in full_inventory:
            full_inventory[user_id] = {}
        user_inventory = full_inventory[user_id]
        
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
        
        found = False
        for existing_id, existing_item in user_inventory.items():
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
                found = True
                break
        
        if not found:
            new_id = f"{item_template.get('name', 'item')}_{int(datetime.now().timestamp())}_{random.randint(1000,9999)}"
            new_item = item_template.copy()
            new_item['quantity'] = quantity
            new_item['obtained_at'] = datetime.now().isoformat()
            full_inventory[user_id][new_id] = new_item
        
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