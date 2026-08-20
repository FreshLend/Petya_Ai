import discord
import config
from discord import app_commands
from typing import Literal

@bot.tree.command(name="emoji", description="Работа с кастомными эмодзи")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def emoji_command(
    interaction: discord.Interaction,
    action: Literal["send", "info"],
    emoji: str,
    format: Literal["png", "gif"] = None
):
    await interaction.response.defer()
    try:
        emoji_id = None
        emoji_name = None
        emoji = emoji.strip()
        if emoji.startswith('<:') and emoji.endswith('>'):
            parts = emoji[2:-1].split(':')
            if len(parts) == 2:
                emoji_name, emoji_id = parts
            else:
                emoji_id = emoji.split(':')[-1][:-1]
        elif emoji.startswith(':') and emoji.endswith(':'):
            parts = emoji[1:-1].split(':')
            if len(parts) == 2:
                emoji_name, emoji_id = parts
            else:
                emoji_id = parts[-1]
        elif ':' in emoji:
            emoji_name, emoji_id = emoji.split(':')
        elif emoji.isdigit():
            emoji_id = emoji
        if not emoji_id or not emoji_id.isdigit():
            raise ValueError("Некорректный формат смайлика")
        emoji_id = int(emoji_id)
        if action == "send":
            if not format:
                await interaction.followup.send("Для действия 'send' необходимо указать формат!")
                return
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{format.lower()}"
            embed = discord.Embed(color=discord.Color.blue())
            embed.set_image(url=emoji_url)
            await interaction.followup.send(embed=embed)
        elif action == "info":
            emoji_obj = bot.get_emoji(emoji_id)
            if emoji_obj:
                emoji_type = "анимированный" if emoji_obj.animated else "статический"
                emoji_str = f"<{'a' if emoji_obj.animated else ''}:{emoji_obj.name}:{emoji_obj.id}>"
                embed = discord.Embed(
                    title="Информация о смайлике",
                    description=(
                        f"**Представление:** {emoji_str}\n"
                        f"**Название:** {emoji_obj.name}\n"
                        f"**ID:** {emoji_obj.id}\n"
                        f"**Тип:** {emoji_type}\n"
                        f"**Сервер:** {emoji_obj.guild.name} (ID: {emoji_obj.guild.id})\n"
                        f"**Дата создания:** {emoji_obj.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                        f"**Доступен:** {'Да' if emoji_obj.available else 'Нет'}"
                    ),
                    color=discord.Color.blue()
                )
                if emoji_obj.guild.icon:
                    embed.set_thumbnail(url=emoji_obj.guild.icon.url)
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="Отправить как PNG",
                    custom_id=f"emoji_send_{emoji_id}_png",
                    style=discord.ButtonStyle.primary
                ))
                view.add_item(discord.ui.Button(
                    label="Отправить как GIF",
                    custom_id=f"emoji_send_{emoji_id}_gif",
                    style=discord.ButtonStyle.primary,
                    disabled=not emoji_obj.animated
                ))
                await interaction.followup.send(embed=embed, view=view)
            else:
                embed = discord.Embed(
                    title="Ошибка!",
                    description="Смайлик не найден. Возможно, бот не имеет доступа к серверу, где находится этот смайлик.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Ошибка!",
            description=f"Не удалось обработать смайлик: {str(e)}\n\n"
                    "Правильные форматы ввода:\n"
                    "- ID смайлика (123)\n"
                    "- name:id (emoji:123)\n"
                    "- :name:id: (:emoji:123)\n"
                    "- <:name:id> (<:emoji:123>)",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="emoji_list", description="Показать список смайлов сервера")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.user_install()
async def emoji_list(interaction: discord.Interaction, server_id: str = None):
    await interaction.response.defer()
    try:
        if server_id:
            try:
                guild = bot.get_guild(int(server_id))
                if not guild:
                    raise ValueError
            except:
                return await interaction.followup.send("Сервер с указанным ID не найден или бот не состоит на нем")
        else:
            if not interaction.guild:
                return await interaction.followup.send("Эта команда работает только на серверах")
            guild = interaction.guild
        emojis = sorted(guild.emojis, key=lambda e: e.name)
        if not emojis:
            return await interaction.followup.send("На этом сервере нет кастомных смайлов")
        pages = []
        for i in range(0, len(emojis), 10):
            page_emojis = emojis[i:i+10]
            emoji_list_text = []
            for emoji in page_emojis:
                status = '🟢' if emoji.available else '🔴'
                emoji_str = str(emoji)
                emoji_list_text.append(f"{status} {emoji_str} - `:{emoji.name}:` (ID: {emoji.id})")
            embed = discord.Embed(
                title=f"Смайлы сервера {guild.name} (Всего: {len(emojis)})",
                description="\n".join(emoji_list_text),
                color=discord.Color.blue()
            )
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            pages.append(embed)
        class PaginatorView(discord.ui.View):
            def __init__(self, pages):
                super().__init__(timeout=60)
                self.current_page = 0
                self.pages = pages
                self.update_buttons()
            def update_buttons(self):
                self.prev_btn.disabled = self.current_page == 0
                self.next_btn.disabled = self.current_page == len(self.pages) - 1
                self.page_indicator.label = f"{self.current_page + 1}/{len(self.pages)}"
            @discord.ui.button(label="◀️", style=discord.ButtonStyle.grey)
            async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.current_page = max(0, self.current_page - 1)
                self.update_buttons()
                await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
            @discord.ui.button(label="▶️", style=discord.ButtonStyle.grey)
            async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.current_page = min(len(self.pages) - 1, self.current_page + 1)
                self.update_buttons()
                await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
            @discord.ui.button(style=discord.ButtonStyle.blurple, disabled=True)
            async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
                pass
            async def on_timeout(self):
                for item in self.children:
                    item.disabled = True
                try:
                    await self.message.edit(view=self)
                except:
                    pass
        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0])
        else:
            view = PaginatorView(pages)
            view.message = await interaction.followup.send(embed=pages[0], view=view)
    except Exception as e:
        await interaction.followup.send(f"Произошла ошибка: {str(e)}")