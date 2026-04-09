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

async def get_anime_gif(search_query: str) -> Optional[Tuple[str, str]]:
    try:
        interactables = _load_interactables()
        
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
            return await interaction.followup.send(embed=embed, view=view)
        
        with open(gif_path, 'rb') as f:
            gif_file = discord.File(f, filename=os.path.basename(gif_path))
            embed.set_image(url=f"attachment://{gif_file.filename}")
            await interaction.followup.send(file=gif_file, embed=embed, view=view)
            
    except Exception as e:
        print(f"Ошибка при отправке гифки: {e}")
        embed.set_footer(text="[Не удалось загрузить гифку] " + (embed.footer.text if embed.footer else ""))
        await interaction.followup.send(embed=embed, view=view)

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

def load_data():
    with open(config.JOKES_AND_QUOTES, 'r', encoding='utf-8') as f:
        return json.load(f)

@bot.tree.command(name="8ball", description="Магический шар")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def eight_ball(
    interaction: discord.Interaction,
    question: str
):
    await interaction.response.defer()
    
    answers = [
        "Бесспорно", "Предрешено", "Никаких сомнений", "Определённо да",
        "Можешь быть уверен в этом", "Мне кажется — «да»", "Вероятнее всего",
        "Хорошие перспективы", "Знаки говорят — «да»", "Да",
        "Пока не ясно, попробуй снова", "Спроси позже", "Лучше не рассказывать",
        "Сейчас нельзя предсказать", "Сконцентрируйся и спроси опять",
        "Даже не думай", "Мой ответ — «нет»", "По моим данным — «нет»",
        "Перспективы не очень хорошие", "Весьма сомнительно"
    ]
    
    answer = random.choice(answers)
    embed = discord.Embed(
        title="🎱 Магический шар",
        description=f"**Вопрос:** {question}\n**Ответ:** {answer}",
        color=discord.Color.dark_blue()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="interact_hi", description="Отправить приветственное сообщение")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(target="Пользователь, которого нужно поприветствовать")
async def hello(interaction: discord.Interaction, target: discord.User):
    class HelloButtons(discord.ui.View):
        def __init__(self, original_sender: discord.User, target: discord.User):
            super().__init__(timeout=300)
            self.original_sender = original_sender
            self.target = target
            self.responded = False

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.target.id:
                await interaction.response.send_message(
                    "❌ Это приветствие было отправлено не вам!",
                    ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="Поприветствовать в ответ", style=discord.ButtonStyle.green)
        async def greet_back(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.responded:
                await interaction.response.send_message("❌ Это приветствие уже было обработано!", ephemeral=True)
                return
                
            self.responded = True
            await update_interaction_count(self.original_sender.id, self.target.id, "hello")
            
            gif_path, anime_name = await get_anime_gif("hello")
            responses = [
                f"🌟 **{self.target.display_name}** вежливо приветствует **{self.original_sender.display_name}** в ответ!",
                f"✨ **{self.target.display_name}** радостно машет в ответ **{self.original_sender.display_name}**!",
                f"👋 **{self.target.display_name}** отвечает на приветствие **{self.original_sender.display_name}** с улыбкой!",
                f"💫 **{self.target.display_name}** тепло приветствует **{self.original_sender.display_name}** в ответ!"
            ]

            count = await get_interaction_count(self.original_sender.id, self.target.id, "hello")

            embed = discord.Embed(
                description=f"{random.choice(responses)}\n\n**Всего приветствий между вами:** {count}",
                color=0x00ff00
            )
            
            if gif_path:
                embed.set_footer(text=anime_name)
                await send_gif_embed(interaction, gif_path, embed)
            else:
                await interaction.response.send_message(embed=embed)
                
            for item in self.children:
                item.disabled = True
                
            await self.message.edit(view=self)
            self.stop()

    if target.id == interaction.user.id:
        message = "Ты не можешь поздороваться сам с собой."
        embed = discord.Embed(description=message, color=0xff0000)
        await interaction.response.send_message(embed=embed)
        return

    await interaction.response.defer()
    view = HelloButtons(interaction.user, target)
    gif_path, anime_name = await get_anime_gif("hello")

    greetings = [
        f"👋 **{interaction.user.display_name}** тепло приветствует **{target.display_name}**!",
        f"✨ **{interaction.user.display_name}** посылает лучи добра **{target.display_name}**!",
        f"🌟 **{interaction.user.display_name}** радостно встречает **{target.display_name}**!",
        f"💫 **{interaction.user.display_name}** передаёт тёплые приветствия **{target.display_name}**!",
        f"🌞 **{interaction.user.display_name}** дарит солнечное приветствие **{target.display_name}**!"
    ]

    count = await get_interaction_count(interaction.user.id, target.id, "hello")

    embed = discord.Embed(
        description=f"{random.choice(greetings)}\n\n**Всего приветствий между вами:** {count}",
        color=0x00bfff
    )
    
    if gif_path:
        embed.set_footer(text=anime_name)
        await send_gif_embed(interaction, gif_path, embed, view)
    else:
        await interaction.followup.send(embed=embed, view=view)
    
    view.message = await interaction.original_response()

@bot.tree.command(name="interact_bye", description="Отправить прощальное сообщение")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(target="Пользователь, с которым нужно попрощаться")
async def goodbye(interaction: discord.Interaction, target: discord.User):
    class GoodbyeButtons(discord.ui.View):
        def __init__(self, original_sender: discord.User, target: discord.User):
            super().__init__(timeout=300)
            self.original_sender = original_sender
            self.target = target
            self.responded = False

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.target.id:
                await interaction.response.send_message(
                    "❌ Это прощание было отправлено не вам!",
                    ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="Попрощаться в ответ", style=discord.ButtonStyle.green)
        async def goodbye_back(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.responded:
                await interaction.response.send_message("❌ Это прощание уже было обработано!", ephemeral=True)
                return
                
            self.responded = True
            await update_interaction_count(self.original_sender.id, self.target.id, "goodbye")
            
            gif_path, anime_name = await get_anime_gif("goodbye")
            responses = [
                f"👋 **{self.target.display_name}** прощается с **{self.original_sender.display_name}** в ответ!",
                f"👋 **{self.target.display_name}** машет на прощание **{self.original_sender.display_name}**!",
                f"👋 **{self.target.display_name}** отвечает на прощание **{self.original_sender.display_name}**!",
                f"👋 **{self.target.display_name}** прощается с **{self.original_sender.display_name}** - ещё увидемся!"
            ]

            count = await get_interaction_count(self.original_sender.id, self.target.id, "goodbye")

            embed = discord.Embed(
                description=f"{random.choice(responses)}\n\n**Всего прощаний между вами:** {count}",
                color=0x9932CC
            )
            
            if gif_path:
                embed.set_footer(text=anime_name)
                await send_gif_embed(interaction, gif_path, embed)
            else:
                await interaction.response.send_message(embed=embed)
                
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)
            self.stop()

    if target.id == interaction.user.id:
        message = "Как ты попрощаешься с самим собой?"
        embed = discord.Embed(description=message, color=0xff0000)
        await interaction.response.send_message(embed=embed)
        return

    await interaction.response.defer()
    view = GoodbyeButtons(interaction.user, target)
    gif_path, anime_name = await get_anime_gif("goodbye")

    goodbyes = [
        f"👋 **{interaction.user.display_name}** прощается с **{target.display_name}**! До скорых встреч!",
        f"🌅 **{interaction.user.display_name}** желает **{target.display_name}** отличного дня!",
        f"😊 **{interaction.user.display_name}** прощается с **{target.display_name}**. До новых встреч!"
    ]

    count = await get_interaction_count(interaction.user.id, target.id, "goodbye")

    embed = discord.Embed(
        description=f"{random.choice(goodbyes)}\n\n**Всего прощаний между вами:** {count}",
        color=0x4682B4
    )
    
    if gif_path:
        embed.set_footer(text=anime_name)
        await send_gif_embed(interaction, gif_path, embed, view)
    else:
        await interaction.followup.send(embed=embed, view=view)
    
    view.message = await interaction.original_response()

@bot.tree.command(name="interact_kiss", description="Поцеловать пользователя")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    target="Пользователь, которого нужно поцеловать",
    cheeks="Поцеловать в щёчку (милый поцелуй)"
)
async def kiss(interaction: discord.Interaction, target: discord.User, cheeks: bool = False):
    class KissButtons(discord.ui.View):
        def __init__(self, original_sender: discord.User, target: discord.User, is_cheek_kiss: bool):
            super().__init__(timeout=300)
            self.original_sender = original_sender
            self.target = target
            self.is_cheek_kiss = is_cheek_kiss
            self.responded = False

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.target.id:
                await interaction.response.send_message(
                    "❌ Эти поцелуи не для вас!",
                    ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="Поцеловать в ответ", style=discord.ButtonStyle.green)
        async def kiss_back(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.handle_response(interaction, is_reject=False)

        @discord.ui.button(label="Отказаться", style=discord.ButtonStyle.red)
        async def reject_kiss(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.handle_response(interaction, is_reject=True)

        async def handle_response(self, interaction: discord.Interaction, is_reject: bool):
            if self.responded:
                await interaction.response.send_message("❌ Это взаимодействие уже было обработано!", ephemeral=True)
                return
                
            self.responded = True
            
            if is_reject:
                gif_path, anime_name = await get_anime_gif("reject kiss")
                if self.is_cheek_kiss:
                    responses = [
                        f"😾 **{self.target.mention}** отстраняется от **{self.original_sender.mention}**! 'Нет, спасибо, не сегодня!'",
                        f"🚫 **{self.target.mention}** отвергает милый поцелуй в щёчку от **{self.original_sender.mention}**!",
                        f"❌ **{self.target.mention}** отворачивает щёку от **{self.original_sender.mention}**!",
                        f"😤 **{self.target.mention}**: 'Я не для милых поцелуев!'"
                    ]
                else:
                    responses = [
                        f"😾 **{self.target.mention}** отталкивает **{self.original_sender.mention}**! Кажется, кто-то сегодня не в настроении...",
                        f"🚫 **{self.target.mention}** отвергает поцелуй от **{self.original_sender.mention}**!",
                        f"❌ **{self.target.mention}** отворачивается от **{self.original_sender.mention}**!",
                        f"😤 **{self.target.mention}**: 'Нет уж, спасибо!'"
                    ]
                color = 0xFF0000
                embed = discord.Embed(
                    description=random.choice(responses),
                    color=color
                )
            else:
                action = "cheek_kiss" if self.is_cheek_kiss else "kiss"
                await update_interaction_count(self.original_sender.id, self.target.id, action)
                gif_path, anime_name = await get_anime_gif("cheek kiss" if self.is_cheek_kiss else "kiss")
                if self.is_cheek_kiss:
                    responses = [
                        f"😊 **{self.target.display_name}** нежно целует **{self.original_sender.display_name}** в щёчку в ответ!",
                        f"💞 **{self.target.display_name}** отвечает на поцелуй в щёчку **{self.original_sender.display_name}**!",
                        f"🌸 **{self.target.display_name}** целует **{self.original_sender.display_name}** в щёку, вызывая улыбки вокруг!",
                        f"💝 **{self.target.display_name}** и **{self.original_sender.display_name}** обмениваются милыми поцелуями в щёчку!"
                    ]
                else:
                    responses = [
                        f"💖 **{self.target.display_name}** страстно целует **{self.original_sender.display_name}** в ответ!",
                        f"💘 **{self.target.display_name}** нежно отвечает на поцелуй **{self.original_sender.display_name}**!",
                        f"💞 **{self.target.display_name}** целует **{self.original_sender.display_name}**, вызывая зависть у окружающих!",
                        f"💕 **{self.target.display_name}** и **{self.original_sender.display_name}** обмениваются страстными поцелуями!"
                    ]
                color = 0xFF69B4
                embed = discord.Embed(
                    description=f"{random.choice(responses)}\n\n**Всего {'поцелуев в щёчку' if self.is_cheek_kiss else 'поцелуев'} между вами:** {await get_interaction_count(self.original_sender.id, self.target.id, action)}",
                    color=color
                )
            
            if gif_path:
                embed.set_footer(text=anime_name)
                await send_gif_embed(interaction, gif_path, embed)
            else:
                await interaction.response.send_message(embed=embed)
                
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)
            self.stop()

    if target.id == interaction.user.id:
        message = f"Ты поцелуешь себя {'в щёчку' if cheeks else ''}, {interaction.user.display_name}?"
        embed = discord.Embed(description=message, color=0xff0000)
        await interaction.response.send_message(embed=embed)
        return

    await interaction.response.defer()
    view = KissButtons(interaction.user, target, is_cheek_kiss=cheeks)
    gif_path, anime_name = await get_anime_gif("cheek kiss" if cheeks else "kiss")

    if cheeks:
        kisses = [
            f"😊 **{interaction.user.display_name}** нежно целует **{target.display_name}** в щёчку!",
            f"🌸 **{interaction.user.display_name}** дарит милый поцелуй в щёку **{target.display_name}**!",
            f"💝 **{interaction.user.display_name}** целует **{target.display_name}** в щёку, вызывая улыбки вокруг!",
            f"💞 **{interaction.user.display_name}** и **{target.display_name}** обмениваются милыми поцелуями в щёчку!"
        ]
    else:
        kisses = [
            f"💋 **{interaction.user.display_name}** нежно целует **{target.display_name}**!",
            f"💘 **{interaction.user.display_name}** страстно целует **{target.display_name}**!",
            f"💖 **{interaction.user.display_name}** посылает воздушный поцелуй **{target.display_name}**!",
            f"💞 **{interaction.user.display_name}** и **{target.display_name}** обмениваются поцелуями!",
            f"😘 **{interaction.user.display_name}** целует **{target.display_name}**, вызывая зависть у окружающих!"
        ]

    embed = discord.Embed(
        description=f"{random.choice(kisses)}\n\n**Всего {'поцелуев в щёчку' if cheeks else 'поцелуев'} между вами:** {await get_interaction_count(interaction.user.id, target.id, 'cheek_kiss' if cheeks else 'kiss')}",
        color=0xFF69B4
    )
    
    if gif_path:
        embed.set_footer(text=anime_name)
        await send_gif_embed(interaction, gif_path, embed, view)
    else:
        await interaction.followup.send(embed=embed, view=view)
    
    view.message = await interaction.original_response()

@bot.tree.command(name="interact_bang", description="Выстрелить в пользователя")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(target="Пользователь, в которого нужно выстрелить")
async def bang(interaction: discord.Interaction, target: discord.User):
    class BangButtons(discord.ui.View):
        def __init__(self, original_sender: discord.User, target: discord.User):
            super().__init__(timeout=300)
            self.original_sender = original_sender
            self.target = target
            self.responded = False

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.target.id:
                await interaction.response.send_message(
                    "❌ Эти выстрелы не для вас!",
                    ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="Выстрелить в ответ", style=discord.ButtonStyle.red)
        async def bang_back(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.responded:
                await interaction.response.send_message("❌ Эти выстрелы уже были обработаны!", ephemeral=True)
                return
                
            self.responded = True
            await update_interaction_count(self.original_sender.id, self.target.id, "bang")
            
            gif_path, anime_name = await get_anime_gif("gun fight")
            
            responses = [
                f"🔫 **{self.target.display_name}** отвечает выстрелом **{self.original_sender.display_name}**!",
                f"💥 **{self.target.display_name}** открывает ответный огонь по **{self.original_sender.display_name}**!",
                f"🔥 **{self.target.display_name}** не остаётся в долгу и стреляет в **{self.original_sender.display_name}**!",
                f"⚡ **{self.target.display_name}** и **{self.original_sender.display_name}** устроили перестрелку!"
            ]

            count = await get_interaction_count(self.original_sender.id, self.target.id, "bang")

            embed = discord.Embed(
                description=f"{random.choice(responses)}\n\n**Всего выстрелов между вами:** {count}",
                color=0xFF0000
            )
            
            if gif_path:
                embed.set_footer(text=anime_name)
                await send_gif_embed(interaction, gif_path, embed)
            else:
                await interaction.response.send_message(embed=embed)
                
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)
            self.stop()

    if target.id == interaction.user.id:
        message = "Ты собираешься застрелиться?"
        embed = discord.Embed(description=message, color=0xff0000)
        await interaction.response.send_message(embed=embed)
        return

    await interaction.response.defer()
    view = BangButtons(interaction.user, target)
    gif_path, anime_name = await get_anime_gif("gun fight")

    bangs = [
        f"🔫 **{interaction.user.display_name}** стреляет в **{target.display_name}**!",
        f"💥 **{interaction.user.display_name}** открывает огонь по **{target.display_name}**!",
        f"🔥 **{interaction.user.display_name}** и **{target.display_name}** начинают перестрелку!",
        f"⚡ **{interaction.user.display_name}** неожиданно стреляет в **{target.display_name}**!"
    ]

    count = await get_interaction_count(interaction.user.id, target.id, "bang")

    embed = discord.Embed(
        description=f"{random.choice(bangs)}\n\n**Всего выстрелов между вами:** {count}",
        color=0xFF0000
    )
    
    if gif_path:
        embed.set_footer(text=anime_name)
        await send_gif_embed(interaction, gif_path, embed, view)
    else:
        await interaction.followup.send(embed=embed, view=view)
    
    view.message = await interaction.original_response()

@bot.tree.command(name="joke", description="Случайная шутка")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def joke(interaction: discord.Interaction):
    await interaction.response.defer()
    
    data = load_data()
    joke = random.choice(data["jokes"])
    
    embed = discord.Embed(
        description=f"🎭 *\"{joke}\"*",
        color=discord.Color.dark_blue()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="quote", description="Случайная цитата")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def quote(interaction: discord.Interaction):
    await interaction.response.defer()
    
    data = load_data()
    quote = random.choice(data["quotes"])
    
    embed = discord.Embed(
        description=f"📜 *\"{quote}\"*",
        color=discord.Color.dark_gold()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="roll", description="Случайное число")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def roll(
    interaction: discord.Interaction,
    max_number: int = 100
):
    await interaction.response.defer()
    
    number = random.randint(1, max_number)
    await interaction.followup.send(f"🎲 Выпало число: **{number}** (из {max_number})")