import asyncio
import discord
import config
from datetime import datetime
from typing import Optional, Literal
from discord import app_commands
from discord.ui import Button, View

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
        current_profession = profile.get("profession", get_default_profession(professions))
        prof_data = get_profession_data(professions, current_profession)
        energy_cost = prof_data.get("energy_cost", 10)
        
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
            current_min = professions.get(current_profession, {}).get("min_level", 0)
            if professions[prof]["min_level"] > current_min:
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
        
        new_energy_cost = get_profession_data(professions, profile.get("profession", get_default_profession(professions))).get("energy_cost", 10)
        if profile["energy"] >= new_energy_cost:
            new_button = WorkButton(user_id)
            new_view = View(timeout=120)
            new_view.add_item(new_button)
            await interaction.edit_original_response(embed=embed, view=new_view)
        else:
            await interaction.edit_original_response(embed=embed, view=None)

@bot.tree.command(name="leaderboard", description="Топ игроков по уровню или богатству")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    top_type="Тип лидерборда",
    page="Страница"
)
@app_commands.choices(top_type=[
    app_commands.Choice(name="⭐ Уровень", value="level"),
    app_commands.Choice(name="💰 Богатство", value="wealth")
])
async def leaderboard(
    interaction: discord.Interaction,
    top_type: app_commands.Choice[str],
    page: Optional[int] = 1
):
    await interaction.response.defer()

    profiles = load_profiles()
    banks = load_banks()
    inventory = load_inventory()

    user_ids = list(profiles.keys())
    if not user_ids:
        await interaction.followup.send("Нет зарегистрированных пользователей.")
        return

    copper_emoji = config.CURRENCY_EMOJIS.get("copper_coin", "🪙")
    ranking = []

    if top_type.value == "level":
        for uid in user_ids:
            level = profiles[uid].get("level", 1)
            ranking.append((uid, level))
        title = "⭐ Уровень"
        value_format = lambda v: f"Ур. {v}"
        ranking.sort(key=lambda x: x[1], reverse=True)

    elif top_type.value == "wealth":
        for uid in user_ids:
            total = get_total_wealth(uid, profiles, banks, inventory)
            ranking.append((uid, total))
        title = f"💰 Богатство"
        ranking.sort(key=lambda x: x[1], reverse=True)

    else:
        await interaction.followup.send("Неизвестный тип лидерборда.")
        return

    per_page = 10
    total_pages = (len(ranking) + per_page - 1) // per_page
    if total_pages == 0:
        await interaction.followup.send("Нет данных для отображения.")
        return

    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    top_users = ranking[start:end]

    embed = discord.Embed(title=f"🏆 Лидерборд: {title}", color=discord.Color.gold())

    lines = []
    for idx, (uid, value) in enumerate(top_users, start=start + 1):
        try:
            user = await bot.fetch_user(int(uid))
            name = user.display_name if user else f"Неизвестный#{uid}"
        except:
            name = f"Неизвестный#{uid}"

        if top_type.value == "level":
            lines.append(f"**{idx}. {name}** — {value_format(value)}")
        else:
            profile = profiles.get(uid, {})
            cash = get_cash_in_copper(profile)
            bank_name = profile.get("bank")
            bank_val = get_bank_in_copper(uid, banks, bank_name) if bank_name else 0
            inv_val = get_inventory_value_in_copper(uid, inventory)
            casino_val = get_casino_value_in_copper(profile)

            lines.append(
                f"**{idx}. {name}** — **{value:,}** {copper_emoji}\n"
                f"└ Наличные: {cash:,} | Банк: {bank_val:,} | Инвентарь: {inv_val:,} | Казино: {casino_val:,}"
            )
    embed.description = "\n".join(lines)
    embed.set_footer(text=f"Страница {page} из {total_pages}")

    view = None
    if total_pages > 1:
        view = discord.ui.View(timeout=60)
        async def prev_callback(interaction: discord.Interaction):
            await leaderboard(interaction, top_type, page - 1)
        async def next_callback(interaction: discord.Interaction):
            await leaderboard(interaction, top_type, page + 1)
        prev_btn = discord.ui.Button(label="◀️", style=discord.ButtonStyle.secondary)
        next_btn = discord.ui.Button(label="▶️", style=discord.ButtonStyle.secondary)
        prev_btn.callback = prev_callback
        next_btn.callback = next_callback
        view.add_item(prev_btn)
        view.add_item(next_btn)

    if view is None:
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(embed=embed, view=view)

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
        for currency in CURRENCY_ORDER:
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
        for currency in CURRENCY_ORDER:
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
    
    cost = {currency.value: amount}
    if not can_afford(profiles[user_id]["money"], cost):
        await interaction.followup.send(f"❌ Недостаточно {currency.name.lower()} для депозита!", ephemeral=True)
        return
    
    ensure_client_dict_format(banks, current_bank, user_id)
        
    if user_id not in banks[current_bank]["clients"]:
        banks[current_bank]["clients"][user_id] = create_empty_balance()
    
    profiles[user_id]["money"] = deduct_money(profiles[user_id]["money"], cost)
    banks[current_bank]["clients"][user_id][currency.value] = banks[current_bank]["clients"][user_id].get(currency.value, 0) + amount
    
    save_profiles(profiles)
    save_banks(banks)
    
    await interaction.followup.send(
        f"✅ Успешно внесено {amount} {currency.name.lower()} в ваш банк '{current_bank}'!",
        ephemeral=True
    )

@bot.tree.command(name="exchange", description="Конвертация валют (курс 100:1) из исходной в целевую")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    from_currency="Из какой валюты конвертируем",
    to_currency="В какую валюту конвертируем",
    amount="Количество целевой валюты, которое хотим получить"
)
@app_commands.choices(
    from_currency=[
        app_commands.Choice(name="Медные монеты", value="copper_coin"),
        app_commands.Choice(name="Серебряные монеты", value="silver_coin"),
        app_commands.Choice(name="Золотые монеты", value="gold_coin"),
        app_commands.Choice(name="Платиновые монеты", value="platinum_coin")
    ],
    to_currency=[
        app_commands.Choice(name="Медные монеты", value="copper_coin"),
        app_commands.Choice(name="Серебряные монеты", value="silver_coin"),
        app_commands.Choice(name="Золотые монеты", value="gold_coin"),
        app_commands.Choice(name="Платиновые монеты", value="platinum_coin")
    ]
)
async def exchange_command(
    interaction: discord.Interaction,
    from_currency: app_commands.Choice[str],
    to_currency: app_commands.Choice[str],
    amount: int
):
    await interaction.response.defer()
    profiles = load_profiles()
    user_id = str(interaction.user.id)
    
    if user_id not in profiles:
        await interaction.followup.send("❌ У вас нет профиля!", ephemeral=True)
        return
    
    if from_currency.value == to_currency.value:
        await interaction.followup.send("❌ Нельзя конвертировать валюту саму в себя!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.followup.send("❌ Количество должно быть положительным числом!", ephemeral=True)
        return
    
    profile = profiles[user_id]
    from_curr = from_currency.value
    to_curr = to_currency.value
    
    cost_copper = amount * CURRENCY_RATIOS[to_curr]
    
    current_copper = sum(to_copper(profile["money"].get(cur, 0), cur) for cur in CURRENCY_ORDER)
    
    if current_copper < cost_copper:
        needed_short = cost_copper - current_copper
        await interaction.followup.send(
            embed=discord.Embed(
                title="❌ Недостаточно средств",
                description=f"Вам не хватает **{needed_short}** медных монет (в эквиваленте) для получения {amount} {to_currency.name}.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return
    
    new_copper = current_copper - cost_copper
    new_money = from_copper(new_copper)
    new_money[to_curr] = new_money.get(to_curr, 0) + amount
    
    profile["money"] = new_money
    save_profiles(profiles)
    
    from_emoji = config.CURRENCY_EMOJIS.get(from_curr, "")
    to_emoji = config.CURRENCY_EMOJIS.get(to_curr, "")
    
    embed = discord.Embed(
        title="✅ Обмен валюты выполнен",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Списано (в эквиваленте)",
        value=f"{cost_copper} медных монет",
        inline=False
    )
    embed.add_field(
        name="Получено",
        value=f"{to_emoji} {amount} {to_currency.name}",
        inline=False
    )
    embed.set_footer(text="Остаток средств автоматически нормализован по курсу 100:1")
    
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

        default_profession = get_default_profession(professions)
        profiles[user_id] = {
            "group": "пользователь",
            "profession": default_profession,
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
    prof_name = profile.get("profession", get_default_profession(professions))
    profession_data = get_profession_data(professions, prof_name)
    profession_emoji = profession_data.get("emoji", "❓")

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

    embed.add_field(
        name="**Группа**",
        value=f"{group_emoji} {profile['group'].capitalize()}",
        inline=True
    )

    embed.add_field(
        name="**Профессия**",
        value=f"{profession_emoji} {prof_name}",
        inline=True
    )
    
    embed.add_field(
        name="**Прогресс**",
        value=level_info,
        inline=False
    )

    money_values = []
    for currency in CURRENCY_ORDER:
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
    
    currency_names = {
        "copper_coin": "медные монеты",
        "silver_coin": "серебряные монеты",
        "gold_coin": "золотые монеты",
        "platinum_coin": "платиновые монеты"
    }
    
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
    
    for coin_key in currency_names.keys():
        if coin_key not in banks[sender_bank]["clients"][user_id]:
            banks[sender_bank]["clients"][user_id][coin_key] = 0
    
    sender_balance = banks[sender_bank]["clients"][user_id]
    
    if sender_balance.get(currency.value, 0) < amount:
        await interaction.followup.send(f"❌ Недостаточно {currency_names[currency.value]} на вашем счету!", ephemeral=True)
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
    
    if fractional_currency and total_fractional_comission == fractional_amount and fractional_amount > 0:
        if sender_balance.get(fractional_currency, 0) >= fractional_amount:
            sender_balance[fractional_currency] -= fractional_amount
        else:
            await interaction.followup.send(f"❌ Ошибка при списании дробной комиссии!", ephemeral=True)
            return
    
    ensure_client_dict_format(banks, receiver_bank, target_user_id)
    if target_user_id not in banks[receiver_bank]["clients"]:
        banks[receiver_bank]["clients"][target_user_id] = create_empty_balance()
    
    for coin_key in currency_names.keys():
        if coin_key not in banks[receiver_bank]["clients"][target_user_id]:
            banks[receiver_bank]["clients"][target_user_id][coin_key] = 0
    
    banks[receiver_bank]["clients"][target_user_id][currency.value] += amount
    
    if comission_percent > 0:
        owner_id = banks[sender_bank]["owner_id"]
        ensure_client_dict_format(banks, sender_bank, owner_id)
        
        if owner_id not in banks[sender_bank]["clients"]:
            banks[sender_bank]["clients"][owner_id] = create_empty_balance()
        
        for coin_key in currency_names.keys():
            if coin_key not in banks[sender_bank]["clients"][owner_id]:
                banks[sender_bank]["clients"][owner_id][coin_key] = 0
        
        banks[sender_bank]["clients"][owner_id][currency.value] += main_comission
        
        if fractional_currency and total_fractional_comission > 0:
            if total_fractional_comission != fractional_amount:
                change = fractional_amount - total_fractional_comission
                if change > 0:
                    if fractional_currency == "gold_coin":
                        sender_balance["silver_coin"] = sender_balance.get("silver_coin", 0) + change
                    elif fractional_currency == "silver_coin":
                        sender_balance["copper_coin"] = sender_balance.get("copper_coin", 0) + change
            else:
                banks[sender_bank]["clients"][owner_id][fractional_currency] = banks[sender_bank]["clients"][owner_id].get(fractional_currency, 0) + total_fractional_comission
    
    save_banks(banks)
    
    if comission_percent > 0:
        comission_msg = []
        if main_comission > 0:
            comission_msg.append(f"{main_comission} {currency_names[currency.value]}")
        if total_fractional_comission > 0 and fractional_currency:
            comission_msg.append(f"{total_fractional_comission} {currency_names[fractional_currency]}")
        
        await interaction.followup.send(
            f"✅ Успешно переведено {amount} {currency_names[currency.value]} пользователю {user.mention}!\n"
            f"Комиссия: {' + '.join(comission_msg)}",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"✅ Успешно переведено {amount} {currency_names[currency.value]} пользователю {user.mention} (без комиссии)!",
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
        banks[current_bank]["clients"][user_id] = create_empty_balance()
    
    if banks[current_bank]["clients"][user_id].get(currency.value, 0) < amount:
        await interaction.followup.send(f"❌ Недостаточно {currency.name.lower()} на вашем счету!", ephemeral=True)
        return
        
    banks[current_bank]["clients"][user_id][currency.value] -= amount
    profiles[user_id]["money"][currency.value] = profiles[user_id]["money"].get(currency.value, 0) + amount
    
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
    professions = load_professions()
    current_prof = profile.get("profession", get_default_profession(professions))
    prof_data = get_profession_data(professions, current_prof)
    energy_cost = prof_data.get("energy_cost", 10)
    
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
        description=f"Нажмите кнопку, чтобы работать как **{current_prof}**\nЭнергии достаточно: {profile.get('energy', max_energy)}/{max_energy}",
        color=discord.Color.blue()
    )
    
    await interaction.followup.send(embed=embed, view=view)

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