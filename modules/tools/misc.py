import discord
import asyncio
import config
from discord import app_commands
from datetime import datetime
from typing import Optional

shutdown_flag = False
reboot_flag = False

async def shutdown_handler():
    print("\n🛑 Получен сигнал завершения работы...")
    g = globals()
    
    if 'translator' in g and g['translator'] is not None:
        try:
            g['translator'].unload()
        except Exception as e:
            print(f"⚠️ Ошибка при выгрузке переводчика: {e}")
    
    if 'aibot' in g and g['aibot'] is not None:
        try:
            await g['aibot'].shutdown()
        except Exception as e:
            print(f"⚠️ Ошибка при остановке AiBot: {e}")
    
    if 'bot' in g and g['bot'] is not None:
        try:
            await g['bot'].close()
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии бота: {e}")
    
    await asyncio.sleep(0.5)
    for task in asyncio.all_tasks():
        if not task.done():
            task.cancel()
    await asyncio.gather(*asyncio.all_tasks(), return_exceptions=True)

@bot.tree.command(name="avatar", description="Показать аватар пользователя")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    await interaction.response.defer()
    target_user = user or interaction.user
    user_name = f"{target_user.display_name} ({target_user.name})"
    user_id = target_user.id
    avatar_url = target_user.display_avatar.url
    is_animated = target_user.display_avatar.is_animated()
    avatar_type = "Анимированный" if is_animated else "Статичный"
    embed = discord.Embed(
        title="Информация о аватаре",
        description=(
            f"**Пользователь:** {user_name}\n"
            f"**ID:** {user_id}\n"
            f"**Тип:** {avatar_type}\n"
        ),
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=avatar_url)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="bot_channel", description="Управление каналом для работы бота")
@app_commands.describe(
    action="Выберите действие",
    channel="Укажите канал (необязательно)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Установить канал", value="set_channel"),
    app_commands.Choice(name="Сбросить настройки", value="reset_channel"),
    app_commands.Choice(name="Показать текущий", value="show_channel")
])
async def bot_channel_command(
    interaction: discord.Interaction,
    action: str,
    channel: Optional[discord.TextChannel] = None
):
    await interaction.response.defer(ephemeral=True)
    if not (interaction.user.guild_permissions.administrator or interaction.user.id in config.config.ALLOWED_ID):
        await interaction.followup.send(
            "❌ Эта команда только для администраторов сервера!",
            ephemeral=True
        )
        return
    guild_id = interaction.guild.id
    if action == "set_channel":
        target_channel = channel or interaction.channel
        if guild_id not in server_settings:
            server_settings[guild_id] = {}
        server_settings[guild_id]["allowed_channel"] = target_channel.id
        save_server_settings()
        await interaction.followup.send(
            f"✅ Бот теперь будет работать только в канале {target_channel.mention}",
            ephemeral=True
        )
    elif action == "reset_channel":
        if guild_id in server_settings:
            if "allowed_channel" in server_settings[guild_id]:
                del server_settings[guild_id]["allowed_channel"]
                if not server_settings[guild_id]:
                    del server_settings[guild_id]
                save_server_settings()
        await interaction.followup.send(
            "✅ Ограничения канала сброшены. Бот будет работать во всех доступных каналах.",
            ephemeral=True
        )
    elif action == "show_channel":
        channel_id = server_settings.get(guild_id, {}).get("allowed_channel")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                await interaction.followup.send(
                    f"📌 Текущий канал для бота: {channel.mention}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "⚠️ Настроенный канал не найден. Сбросьте настройки.",
                    ephemeral=True
                )
        else:
            await interaction.followup.send(
                "ℹ️ Бот работает во всех доступных каналах",
                ephemeral=True
            )

@bot.tree.command(name="help", description="Показать список команд по категориям")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(category="Выберите категорию команд")
@app_commands.choices(category=[
    app_commands.Choice(name="Искусственный Интеллект", value="ai"),
    app_commands.Choice(name="Развлечения", value="fun"),
    app_commands.Choice(name="Экономика", value="economy"),
    app_commands.Choice(name="Инструменты", value="tools")
])
async def help_command(interaction: discord.Interaction, category: app_commands.Choice[str]):
    await interaction.response.defer()

    commands_by_category = {
        "ai": [
            "• `/query action: (ask, define) question: term: image: is_private:` - Задать вопрос ИИ",
            "• `/parameter action: (get, set, reset) parameter: (system_prompt, context, all) value:` - Управление системным промптом и контекстом",
            "• `/model action: (info, set) model:` - Управление моделями",
            "• `/status action: (history, queue) limit:` - История диалога или состояние очереди",
            "• `/summarize text:` - Суммаризировать текст",
            "• `/translate text: to_language: from_language:` - Перевести текст",
            "• `/char character:` - Сменить персонажа"
        ],
        "fun": [
            "• `/8ball question:` - Магический шар",
            "• `/interact_bang target:` - Выстрелить в пользователя",
            "• `/interact_bye target:` - Попрощаться с пользователем",
            "• `/interact_hi target:` - Поприветствовать пользователя",
            "• `/interact_kiss target: cheeks:` - Поцеловать пользователя",
            "• `/joke` - Случайная шутка",
            "• `/quote` - Случайная цитата",
            "• `/roll max_number:` - Случайное число"
        ],
        "economy": [
            "• `/bank action: (create, list, rename, set_comission, set_service, info) name: set_comission: set_service: new_name:` - Управление банком",
            "• `/deposit amount: currency: (Медные монеты, Серебряные монеты, Золотые монеты, Платиновые монеты)` - Внести депозит",
            "• `/exchange from_currency: (copper_coin, silver_coin, gold_coin, platinum_coin) to_currency: (copper_coin, silver_coin, gold_coin, platinum_coin) amount:` - Конвертация валют",
            "• `/inventory` - Инвентарь",
            "• `/leaderboard top_type: (⭐ Уровень, 💰 Богатство) page:` - Топ игроков",
            "• `/profile create: user:` - Профиль",
            "• `/casino action: (меню, купить, продать, слоты, наперстки, блэкджек) amount: choice:` - Казино",
            "• `/set_bank name:` - Выбрать банк",
            "• `/set_group user: group: (разработчик, тестер, покупатель, пользователь)` - Установить группу",
            "• `/shop black_store:` - Магазин",
            "• `/transfer amount: currency: (Медные, Серебряные, Золотые, Платиновые) user:` - Перевести деньги",
            "• `/treasure` - Поиск сокровищ",
            "• `/withdraw amount: currency: (Медные, Серебряные, Золотые, Платиновые)` - Снять деньги",
            "• `/work profession_list:` - Работа"
        ],
        "tools": [
            "• `/avatar user:` - Аватар пользователя",
            "• `/bot_channel action: (set_channel, reset_channel, show_channel) channel:` - Управление каналом бота",
            "• `/calc expression: precision:` - Математические вычисления",
            "• `/cipher action: (🔒 Зашифровать, 🔓 Расшифровать) cipher_type: (Цезарь, Атбаш, ROT13, Виженер, Base64, Морзе, HEX, Бинарный, XOR, Аффинный, MD5, SHA-1, SHA-256, SHA-512) text: key: shift:` - Шифрование",
            "• `/emoji action: (send, info) emoji: format:` - Работа с эмодзи",
            "• `/emoji_list server_id:` - Список эмодзи сервера",
            "• `/feedback` - Обратная связь",
            "• `/health` - Проверка работоспособности",
            "• `/info short_info:` - Информация о боте",
            "• `/math expression: mode: variable: steps: precision:` - Вычислить выражение",
            "• `/invite` - Пригласить бота",
            "• `/ping` - Проверка задержки",
            "• `/plugins action: (list, info, reload, reload_all, files, load, unload) plugin_id:` - Управление плагинами",
            "• `/reboot` - Перезагрузить бота",
            "• `/say text:` - Сказать от имени бота",
            "• `/servers` - Информация о серверах",
            "• `/shutdown` - Выключить бота",
            "• `/help category:` - Эта команда"
        ]
    }

    category_info = {
        "ai": {"title": "📚 Список команд: Искусственный Интеллект", "desc": "**🤖 Искусственный Интеллект**"},
        "fun": {"title": "📚 Список команд: Развлечения", "desc": "**🎪 Развлечения**"},
        "economy": {"title": "📚 Список команд: Экономика", "desc": "**💰 Экономика**"},
        "tools": {"title": "📚 Список команд: Инструменты", "desc": "**🛠️ Инструменты**"}
    }

    info = category_info[category.value]
    commands = commands_by_category[category.value]

    embed = discord.Embed(title=info["title"], color=0x2b2d31)
    embed.description = info["desc"]

    parts = []
    current = ""
    for cmd in commands:
        if len(current) + len(cmd) + 1 <= 1024:
            current += cmd + "\n"
        else:
            parts.append(current.strip())
            current = cmd + "\n"
    if current:
        parts.append(current.strip())

    if parts:
        embed.add_field(name="Доступные команды:", value=parts[0], inline=False)
        for part in parts[1:]:
            embed.add_field(name="", value=part, inline=False)

    embed.set_footer(text=f"Запрошено: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="info", description="Информация о боте")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(short_info="Коротка информация")
async def info(interaction: discord.Interaction, short_info: bool = False):
    await interaction.response.defer()
    unix_time = int(datetime.now().timestamp())
    if short_info:
        ping = round(bot.latency * 1000)
        embed = discord.Embed(title="Информация", color=discord.Color.blue())
        embed.add_field(name="🕒 Время работы:", value=f"<t:{unix_time}:F> - <t:{unix_time}:R>", inline=False)
        embed.add_field(name="⏱ Задержка:", value=f"{ping}мс", inline=False)
        await interaction.followup.send(embed=embed)
        return
    if not short_info:
        guild_count = len(bot.guilds)
        unique_members = set()
        for guild in bot.guilds:
            for member in guild.members:
                if not member.bot:
                    unique_members.add(member.id)
        human_count = len(unique_members)
        ping = round(bot.latency * 1000)
        embed = discord.Embed(title="💎 Статистика Бота", color=discord.Color.blue())
        embed.add_field(name="👑 — Разработчик:", value="<@1136934279348224042>", inline=False)
        embed.add_field(name="🤖 — Имя бота:", value="<@1137405206288666634>", inline=False)
        embed.add_field(name="📝 — Описание:", value="Petya_Ai - это бот с Искусственным Интеллектом, у него есть развлечения в виде экономической игры и многое другое!", inline=False)
        embed.add_field(name="🖥 Серверов:", value=str(guild_count), inline=False)
        embed.add_field(name="👥 Участников:", value=str(human_count), inline=False)
        embed.add_field(name="🔨 Дата создания:", value="<t:1691321400:F>", inline=False)
        embed.add_field(name="🛠 Версия:", value="2.8.0", inline=False)
        embed.add_field(name="⏱ Задержка:", value=f"{ping}мс", inline=False)
        embed.add_field(name="🕒 Время работы:", value=f"<t:{unix_time}:F> - <t:{unix_time}:R>", inline=False)
        embed.add_field(name="🌐 — Наш сайт:", value="[Нажми сюда!](https://freshlend.github.io)", inline=False)
        embed.add_field(name="🛠 — Исходный код:", value="[Нажми сюда!](https://github.com/FreshLend/Petya_Ai)", inline=False)
        embed.add_field(name="💬 — Связаться со мной:", value="freshlend.studio@gmail.com", inline=False)
        embed.add_field(name="🛡 — Все права защищены", value="FreshLend Studio", inline=False)
        await interaction.followup.send(embed=embed)
        return

@bot.tree.command(name="invite", description="Получить ссылку-приглашения")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def invite(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(
        title="Пригласить бота на сервер",
        description=f"[Нажмите здесь, чтобы добавить бота на сервер](https://discord.com/oauth2/authorize?client_id=1137405206288666634)",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Присоединится на сервер",
        value="[Нажмите здесь, чтобы присоединится на сервер](https://discord.com/invite/95EyHeZmMz)"
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ping", description="Проверить задержку бота")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def ping(interaction: discord.Interaction):
    await interaction.response.defer()
    latency = bot.latency * 1000
    await interaction.followup.send(f'🏓Pong! {int(latency)} мс')

@bot.tree.command(name="plugins", description="Управление плагинами")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    action="Действие",
    plugin_id="ID плагина (не требуется для list и reload_all)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="list", value="list"),
    app_commands.Choice(name="info", value="info"),
    app_commands.Choice(name="reload", value="reload"),
    app_commands.Choice(name="reload_all", value="reload_all"),
    app_commands.Choice(name="files", value="files"),
    app_commands.Choice(name="load", value="load"),
    app_commands.Choice(name="unload", value="unload")
])
async def plugins_command(interaction: discord.Interaction, action: str, plugin_id: str = None):
    await interaction.response.defer(thinking=True)
    protected_actions = ["reload", "reload_all", "load", "unload"]
    if action in protected_actions:
        if interaction.user.id not in config.ALLOWED_ID:
            await interaction.followup.send("❌ У вас недостаточно прав для выполнения этого действия")
            return
    if action == "list":
        plugins = plugin_api.scan_plugins()
        if not plugins:
            await interaction.followup.send("📦 Нет зарегистрированных плагинов")
            return
        loaded_count = sum(1 for p in plugins if p.loaded)
        not_loaded_count = len(plugins) - loaded_count
        embed = discord.Embed(
            title="📦 Список плагинов",
            description=f"Всего: {len(plugins)} | ✅ Загружено: {loaded_count} | ❌ Не загружено: {not_loaded_count}",
            color=discord.Color.blue()
        )
        sorted_plugins = sorted(plugins, key=lambda p: (not p.loaded, p.metadata.name))
        for plugin in sorted_plugins:
            status = "✅ Загружен" if plugin.loaded else "❌ Не загружен"
            dependencies_info = ""
            if plugin.metadata.dependencies:
                deps_ok, missing_deps = DependencyResolver.check_dependencies(plugin, {p.metadata.id: p for p in plugins})
                if not deps_ok:
                    status = "⚠️ Зависимости не удовлетворены"
                    dependencies_info = f"\n❌ Отсутствует: {', '.join(missing_deps)}"
            embed.add_field(
                name=f"{plugin.metadata.name} ({plugin.metadata.id})",
                value=f"Версия: {plugin.metadata.version}\nАвтор: {plugin.metadata.author}\nСтатус: {status}{dependencies_info}",
                inline=False
            )
        await interaction.followup.send(embed=embed)
    elif action == "info":
        if not plugin_id:
            await interaction.followup.send("❌ Для действия 'info' требуется указать plugin_id")
            return
        plugin = plugin_api.get_plugin(plugin_id)
        if not plugin:
            await interaction.followup.send(f"❌ Плагин с ID '{plugin_id}' не найден")
            return
        commands_count = len(plugin_api.plugin_commands.get(plugin_id, []))
        tasks_count = len(plugin_api.plugin_tasks.get(plugin_id, {}))
        hooks_count = 0
        for hook_list in plugin_api.plugin_hooks.values():
            hooks_count += len([h for h in hook_list if h['plugin_id'] == plugin_id])
        embed = discord.Embed(
            title=f"📦 Информация о плагине: {plugin.metadata.name}",
            description=plugin.metadata.description,
            color=discord.Color.green()
        )
        embed.add_field(name="ID", value=plugin.metadata.id, inline=True)
        embed.add_field(name="Версия", value=plugin.metadata.version, inline=True)
        embed.add_field(name="Автор", value=plugin.metadata.author, inline=True)
        embed.add_field(name="Статус", value="✅ Загружен" if plugin.loaded else "❌ Не загружен", inline=True)
        embed.add_field(name="Команды", value=commands_count, inline=True)
        embed.add_field(name="Задачи", value=tasks_count, inline=True)
        embed.add_field(name="Хуки", value=hooks_count, inline=True)
        embed.add_field(name="Зависимости", value=", ".join(plugin.metadata.dependencies) if plugin.metadata.dependencies else "Нет", inline=False)
        embed.add_field(name="Директория", value=plugin.directory, inline=False)
        await interaction.followup.send(embed=embed)
    elif action == "files":
        if not plugin_id:
            await interaction.followup.send("❌ Для действия 'files' требуется указать plugin_id")
            return
        plugin = plugin_api.get_plugin(plugin_id)
        if not plugin:
            await interaction.followup.send(f"❌ Плагин с ID '{plugin_id}' не найден")
            return
        try:
            files = plugin_api.list_plugin_files(".", plugin_id)
            files_list = "\n".join([f"📄 {f}" for f in files if f.endswith('.py')]) + "\n" + \
                        "\n".join([f"📁 {f}" for f in files if not f.endswith('.py')])
            embed = discord.Embed(
                title=f"📂 Файлы плагина: {plugin.metadata.name}",
                description=files_list if files else "Файлы не найдены",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка при получении файлов: {e}")
    elif action == "reload":
        if not plugin_id:
            await interaction.followup.send("❌ Для действия 'reload' требуется указать plugin_id")
            return
        result = await reload_plugin(plugin_id)
        if result:
            await interaction.followup.send(f"✅ Плагин '{plugin_id}' успешно перезагружен")
        else:
            await interaction.followup.send(f"❌ Не удалось перезагрузить плагин '{plugin_id}'")
    elif action == "reload_all":
        await reload_all_plugins()
        await interaction.followup.send("✅ Все плагины перезагружены!")
    elif action == "load":
        if not plugin_id:
            await interaction.followup.send("❌ Для действия 'load' требуется указать plugin_id")
            return
        result = await load_single_plugin(plugin_id)
        if result:
            await interaction.followup.send(f"✅ Плагин '{plugin_id}' успешно загружен")
        else:
            await interaction.followup.send(f"❌ Не удалось загрузить плагин '{plugin_id}'")
    elif action == "unload":
        if not plugin_id:
            await interaction.followup.send("❌ Для действия 'unload' требуется указать plugin_id")
            return
        result = await unload_plugin(plugin_id)
        if result:
            await interaction.followup.send(f"✅ Плагин '{plugin_id}' успешно выгружен")
        else:
            await interaction.followup.send(f"❌ Не удалось выгрузить плагин '{plugin_id}'")
    else:
        await interaction.followup.send(f"❌ Неизвестное действие: {action}")

@bot.tree.command(name="reboot", description="Перезагрузить бота")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def reboot_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id not in config.ALLOWED_ID:
        await interaction.followup.send("У вас нет прав для использования этой команды.", ephemeral=True)
        return
    await interaction.followup.send(f"Бот перезагружается... Ожидайте завершения операций (максимум {config.SHUTDOWN_TIME} секунд).", ephemeral=True)
    if hasattr(config, 'LOG_CHANNEL_ID'):
        log_channel = bot.get_channel(config.LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"Бот перезагружается по команде от **{interaction.user.display_name}**")
    translator.unload()
    await aibot.prepare_for_reboot()
    await asyncio.sleep(config.REBOOT_DELAY)
    await restart_bot()

@bot.tree.command(name="say", description="Отправьте сообщение через меня")
@app_commands.describe(text="Текст сообщения (необязательно)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def say(interaction: discord.Interaction, text: str = None):
    async def send_as_message(content):
        try:
            await interaction.channel.send(content)
            return True
        except discord.Forbidden:
            return False
        except Exception as e:
            print(f"Произошла ошибка: {e}")
            return False
    if text is not None:
        if not await send_as_message(text):
            await interaction.response.send_message(text)
        else:
            await interaction.response.send_message("Сообщение отправлено!", ephemeral=True)
        return
    class SayModal(discord.ui.Modal, title="Отправить сообщение"):
        message = discord.ui.TextInput(
            label="Текст сообщения",
            style=discord.TextStyle.long,
            placeholder="Введите текст, который бот отправит...",
            required=True,
            max_length=2000
        )
        async def on_submit(self, interaction: discord.Interaction):
            if not await send_as_message(self.message.value):
                await interaction.response.send_message(self.message.value)
            else:
                await interaction.response.send_message("Сообщение отправлено!", ephemeral=True)
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            await interaction.response.send_message("Произошла ошибка при обработке вашего запроса.", ephemeral=True)
            print(f"Ошибка в модальном окне: {error}")
    await interaction.response.send_modal(SayModal())

@bot.tree.command(name="servers", description="Показать информацию о серверах бота")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def servers(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        guilds = sorted(bot.guilds, key=lambda g: g.name)
        def get_human_members(guild):
            return len([member for member in guild.members if not member.bot])
        simple_embeds = []
        server_list = []
        for guild in guilds:
            human_count = get_human_members(guild)
            owner_info = f"👑 {guild.owner.display_name}" if guild.owner else f"👑 (ID: {guild.owner_id})"
            server_list.append(f"**{guild.name}** (`{guild.id}`)\n└ Владелец: {owner_info}\n└ 👥 Участников: {human_count} | 🤖 Ботов: {guild.member_count - human_count}")
        current_embed_content = []
        current_length = 0
        for server in server_list:
            server_length = len(server) + 2
            if current_length + server_length > 4000:
                embed = discord.Embed(
                    title=f"📋 Список серверов ({len(simple_embeds) + 1}/{len(simple_embeds) + 2})",
                    description="\n\n".join(current_embed_content),
                    color=discord.Color.blue()
                )
                simple_embeds.append(embed)
                current_embed_content = [server]
                current_length = server_length
            else:
                current_embed_content.append(server)
                current_length += server_length
        if current_embed_content:
            embed = discord.Embed(
                title=f"📋 Список серверов ({len(simple_embeds) + 1}/{len(simple_embeds) + 1})",
                description="\n\n".join(current_embed_content),
                color=discord.Color.blue()
            )
            simple_embeds.append(embed)
        detailed_embeds = []
        guilds_info = []
        for guild in guilds:
            human_count = get_human_members(guild)
            owner_info = f"👑 {guild.owner.display_name}" if guild.owner else f"👑 (ID: {guild.owner_id})"
            guild_info = [
                f"**{guild.name}** (`{guild.id}`)",
                f"└ Владелец: {owner_info}",
                f"└ 👥 Участников: {human_count} | 🤖 Ботов: {guild.member_count - human_count}",
                f"└ 📅 Создан: {guild.created_at.strftime('%d.%m.%Y')}"
            ]
            no_category_text = sorted(
                [ch for ch in guild.channels if ch.category is None and isinstance(ch, discord.TextChannel)],
                key=lambda c: c.position
            )
            no_category_voice = sorted(
                [ch for ch in guild.channels if ch.category is None and isinstance(ch, discord.VoiceChannel)],
                key=lambda c: c.position
            )
            if no_category_text or no_category_voice:
                guild_info.append("└ 📁 Без категории")
                for channel in no_category_text:
                    guild_info.append(f"  ├ 💬 {channel.name}")
                for channel in no_category_voice:
                    guild_info.append(f"  ├ 🔊 {channel.name}")
            for category in sorted(guild.categories, key=lambda c: c.position):
                guild_info.append(f"└ 📁 {category.name}")
                text_channels = sorted(
                    [ch for ch in category.channels if isinstance(ch, discord.TextChannel)],
                    key=lambda c: c.position
                )
                for channel in text_channels:
                    guild_info.append(f"  ├ 💬 {channel.name}")
                voice_channels = sorted(
                    [ch for ch in category.channels if isinstance(ch, discord.VoiceChannel)],
                    key=lambda c: c.position
                )
                for channel in voice_channels:
                    guild_info.append(f"  ├ 🔊 {channel.name}")
            guilds_info.append("\n".join(guild_info))
        all_content = "\n\n".join(guilds_info)
        if len(all_content) <= 4000:
            embed = discord.Embed(
                title="🔍 Детальная структура (1/1)",
                description=f"```\n{all_content}\n```",
                color=discord.Color.green()
            )
            detailed_embeds.append(embed)
        else:
            parts = []
            current_part = ""
            for line in all_content.split("\n"):
                if len(current_part) + len(line) + 1 > 4000:
                    parts.append(current_part)
                    current_part = line
                else:
                    if current_part:
                        current_part += "\n" + line
                    else:
                        current_part = line
            if current_part:
                parts.append(current_part)
            for i, part in enumerate(parts):
                embed = discord.Embed(
                    title=f"🔍 Детальная структура ({i+1}/{len(parts)})",
                    description=f"```\n{part}\n```",
                    color=discord.Color.green()
                )
                detailed_embeds.append(embed)
        class ServerView(discord.ui.View):
            def __init__(self, simple_embeds, detailed_embeds):
                super().__init__(timeout=120)
                self.simple_embeds = simple_embeds
                self.detailed_embeds = detailed_embeds
                self.current_mode = "simple"
                self.simple_page = 0
                self.detailed_page = 0
            def update_buttons(self):
                if self.current_mode == "simple":
                    self.prev_button.disabled = len(self.simple_embeds) <= 1
                    self.next_button.disabled = len(self.simple_embeds) <= 1
                else:
                    self.prev_button.disabled = len(self.detailed_embeds) <= 1
                    self.next_button.disabled = len(self.detailed_embeds) <= 1
            @discord.ui.select(
                placeholder="Выберите режим отображения",
                options=[
                    discord.SelectOption(label="📋 Список серверов", value="simple", description="Краткий список всех серверов"),
                    discord.SelectOption(label="🔍 Детальная структура", value="detailed", description="Подробная структура каналов")
                ]
            )
            async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                self.current_mode = select.values[0]
                if self.current_mode == "simple":
                    embed = self.simple_embeds[self.simple_page]
                else:
                    embed = self.detailed_embeds[self.detailed_page]
                self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)
            @discord.ui.button(label="◀️", style=discord.ButtonStyle.grey, row=1)
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_mode == "simple":
                    self.simple_page = (self.simple_page - 1) % len(self.simple_embeds)
                    embed = self.simple_embeds[self.simple_page]
                else:
                    self.detailed_page = (self.detailed_page - 1) % len(self.detailed_embeds)
                    embed = self.detailed_embeds[self.detailed_page]
                await interaction.response.edit_message(embed=embed, view=self)
            @discord.ui.button(label="▶️", style=discord.ButtonStyle.grey, row=1)
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_mode == "simple":
                    self.simple_page = (self.simple_page + 1) % len(self.simple_embeds)
                    embed = self.simple_embeds[self.simple_page]
                else:
                    self.detailed_page = (self.detailed_page + 1) % len(self.detailed_embeds)
                    embed = self.detailed_embeds[self.detailed_page]
                await interaction.response.edit_message(embed=embed, view=self)
            async def on_timeout(self):
                for item in self.children:
                    item.disabled = True
                try:
                    await self.message.edit(view=self)
                except:
                    pass
        view = ServerView(simple_embeds, detailed_embeds)
        view.update_buttons()
        view.message = await interaction.followup.send(
            embed=simple_embeds[0] if simple_embeds else discord.Embed(description="Нет данных о серверах"),
            view=view
        )
    except Exception as e:
        await interaction.followup.send(f"Произошла ошибка: {str(e)}")

@bot.tree.command(name="shutdown", description="Выключить бота")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def shutdown_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id not in config.ALLOWED_ID:
        await interaction.followup.send("У вас нет прав для использования этой команды.", ephemeral=True)
        return
    await interaction.followup.send(f"Бот выключается... Ожидайте завершения операций (максимум {config.SHUTDOWN_TIME} секунд).", ephemeral=True)
    if hasattr(config, 'LOG_CHANNEL_ID'):
        log_channel = bot.get_channel(config.LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"Бот выключается по команде от **{interaction.user.display_name}**")
    translator.unload()
    await aibot.shutdown()
    await bot.close()