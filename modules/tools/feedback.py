import discord
import json
import os
import config
from discord import app_commands
from datetime import datetime

PERSISTENT_FEEDBACK_VIEWS = {}
user_feedback_counts = {}

class PersistentFeedbackView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Persistent", style=discord.ButtonStyle.grey, custom_id="persistent_feedback")
    async def persistent_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = PERSISTENT_FEEDBACK_VIEWS.get(interaction.message.id)
        if data:
            view = FeedbackActionView(
                data['thread_id'],
                data['user_id'],
                data['feedback_type'],
                interaction.message.id,
                data.get('current_state', 'initial'),
                data.get('user_message', '')
            )
            await view.handle_response(interaction, "persistent_restored")

class FeedbackActionView(discord.ui.View):
    def __init__(self, thread_id: int, user_id: int, feedback_type: str, message_id: int = None, current_state: str = 'initial', user_message: str = ''):
        super().__init__(timeout=None)
        self.thread_id = thread_id
        self.user_id = user_id
        self.feedback_type = feedback_type.lower()
        self.message_id = message_id
        self.current_state = current_state
        self.user_message = user_message

        if message_id:
            PERSISTENT_FEEDBACK_VIEWS[message_id] = {
                'thread_id': thread_id,
                'user_id': user_id,
                'feedback_type': feedback_type,
                'message_id': message_id,
                'current_state': current_state,
                'user_message': user_message
            }
            self.save_persistent_state()

        if current_state == 'responded':
            self.add_reply_buttons()
        else:
            self.add_buttons_based_on_type()

    def add_buttons_based_on_type(self):
        self.clear_items()

        if "проблема" in self.feedback_type:
            self.add_item(self.SolvedButton())
            self.add_item(self.NotFoundButton())
        elif "идея" in self.feedback_type:
            self.add_item(self.AcceptButton())
            self.add_item(self.RejectButton())
        elif "отзыв" in self.feedback_type:
            self.add_item(self.ThanksButton())
            self.add_item(self.SorryButton())
        else:
            self.add_item(self.AcceptButton())
            self.add_item(self.RejectButton())

        self.add_item(self.ChangeDecisionButton())

    def add_reply_buttons(self):
        self.clear_items()
        self.add_item(self.ReplyButton())
        self.add_item(self.CloseButton())
        self.add_item(self.ChangeDecisionButton())

    def save_persistent_state(self):
        if not os.path.exists(config.FEEDBACK_ACTIONS_FILE):
            os.makedirs(os.path.dirname(config.FEEDBACK_ACTIONS_FILE), exist_ok=True)

        with open(config.FEEDBACK_ACTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(PERSISTENT_FEEDBACK_VIEWS, f, ensure_ascii=False, indent=2)

    @classmethod
    async def load_persistent_views(cls, bot):
        if os.path.exists(config.FEEDBACK_ACTIONS_FILE):
            with open(config.FEEDBACK_ACTIONS_FILE, 'r', encoding='utf-8') as f:
                views_data = json.load(f)

                for message_id_str, data in views_data.items():
                    message_id = int(message_id_str)
                    PERSISTENT_FEEDBACK_VIEWS[message_id] = data

                    view = cls(
                        thread_id=data['thread_id'],
                        user_id=data['user_id'],
                        feedback_type=data['feedback_type'],
                        message_id=data['message_id'],
                        current_state=data.get('current_state', 'initial'),
                        user_message=data.get('user_message', '')
                    )

                    bot.add_view(view, message_id=message_id)

    class SolvedButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.success,
                label="Решено",
                custom_id="feedback_solved_button"
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            await view.handle_response(interaction, "solved")

    class NotFoundButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.danger,
                label="Не обнаружено",
                custom_id="feedback_notfound_button"
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            await view.handle_response(interaction, "not_found")

    class AcceptButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.success,
                label="Принять",
                custom_id="feedback_accept_button"
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            await view.handle_response(interaction, "accept")

    class RejectButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.danger,
                label="Отклонить",
                custom_id="feedback_reject_button"
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            await view.handle_response(interaction, "reject")

    class ThanksButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.success,
                label="Спасибо",
                custom_id="feedback_thanks_button"
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            await view.handle_response(interaction, "thanks")

    class SorryButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                label="Жаль",
                custom_id="feedback_sorry_button"
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            await view.handle_response(interaction, "sorry")

    class ChangeDecisionButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                label="Изменить решение",
                custom_id="feedback_change_decision",
                row=1
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            view.current_state = 'initial'
            view.add_buttons_based_on_type()

            if view.message_id in PERSISTENT_FEEDBACK_VIEWS:
                PERSISTENT_FEEDBACK_VIEWS[view.message_id]['current_state'] = 'initial'
                view.save_persistent_state()

            embed = discord.Embed(
                description="🔄 **Решение сброшено. Выберите новое действие:**",
                color=discord.Color.blue()
            )

            await interaction.message.edit(embed=embed, view=view)
            await interaction.response.send_message("✅ Вы можете изменить решение", ephemeral=True)

    class ReplyButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.primary,
                label="Ответить",
                custom_id="feedback_reply_button",
                emoji="📝"
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            modal = FeedbackReplyModal(view.feedback_type, view.thread_id, view.user_id)
            await interaction.response.send_modal(modal)

    class CloseButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                style=discord.ButtonStyle.danger,
                label="Закрыть",
                custom_id="feedback_close_button",
                emoji="❌"
            )

        async def callback(self, interaction: discord.Interaction):
            view = self.view

            action_to_text = {
                "accept": "✅ Принято",
                "reject": "❌ Отклонено",
                "solved": "✅ Решено",
                "not_found": "⚠️ Не обнаружено",
                "thanks": "❤️ Благодарность отправлена",
                "sorry": "😔 Сожаления отправлены"
            }

            decision_text = "❓ Решение не указано"
            if interaction.message.embeds:
                embed = interaction.message.embeds[0]
                if embed.description:
                    import re
                    decision_match = re.search(r'(✅|❌|⚠️|❤️|😔|🔄)[^\n]*', embed.description)
                    if decision_match:
                        decision_text = decision_match.group(0).strip()

            embed = discord.Embed(
                description=f"🔒 **Обращение закрыто. Дальнейшие ответы невозможны.**\n\n**Принятое решение:** {decision_text}",
                color=discord.Color.dark_gray()
            )

            if view.message_id in PERSISTENT_FEEDBACK_VIEWS:
                del PERSISTENT_FEEDBACK_VIEWS[view.message_id]
                view.save_persistent_state()

            await interaction.message.edit(embed=embed, view=None)
            await interaction.response.send_message("✅ Обращение закрыто", ephemeral=True)

    def truncate_text(self, text: str, max_length: int = 892) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    async def handle_response(self, interaction: discord.Interaction, action: str):
        action_texts = {
            "accept": "✅ Запрос был принят",
            "reject": "❌ Запрос был отклонен",
            "solved": "✅ Проблема отмечена как решенная",
            "not_found": "⚠️ Проблема не обнаружена",
            "thanks": "❤️ Отзыв был принят",
            "sorry": "😔 Отзыв учтен",
            "persistent_restored": "🔄 Обращение восстановлено после перезагрузки"
        }

        result_text = action_texts.get(action, "🔄 Запрос обработан")
        moderator = interaction.user.display_name

        embed = discord.Embed(
            description=f"**{result_text}**\n"
                    f"Модератор: {moderator}\n"
                    f"Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            color=discord.Color.green() if action in ["accept", "solved", "thanks"] else
                discord.Color.red() if action in ["reject", "not_found"] else
                discord.Color.orange()
        )

        if self.feedback_type != "отзыв" and action not in ["persistent_restored"] and self.user_message:
            user_text = self.truncate_text(self.user_message, 892)

            embed.add_field(
                name="📝 Текст обращения:",
                value=user_text,
                inline=False
            )

        try:
            if self.feedback_type in ["проблема", "идея", "другое"] and action not in ["persistent_restored"]:
                self.current_state = 'responded'
                self.add_reply_buttons()

                if self.message_id in PERSISTENT_FEEDBACK_VIEWS:
                    PERSISTENT_FEEDBACK_VIEWS[self.message_id]['current_state'] = 'responded'
                    self.save_persistent_state()

                await interaction.message.edit(
                    content=f"🔹 Обращение рассмотрено: **{self.feedback_type.capitalize()}**",
                    embed=embed,
                    view=self
                )
            else:
                await interaction.message.edit(
                    content=f"🔹 Обращение рассмотрено: **{self.feedback_type.capitalize()}**",
                    embed=embed,
                    view=self
                )
        except discord.HTTPException as e:
            print(f"Ошибка при редактировании сообщения: {e}")
            if "fields" in str(e).lower():
                embed.remove_field(0)
                await interaction.message.edit(
                    content=f"🔹 Обращение рассмотрено: **{self.feedback_type.capitalize()}**",
                    embed=embed,
                    view=self
                )

        try:
            user = await interaction.client.fetch_user(self.user_id)
            if not user:
                raise discord.NotFound("User not found")

            messages = {
                "идея": {
                    "accept": "🎉 Ваша идея была одобрена, возможно её реализуют! Спасибо за ваш вклад!",
                    "reject": "😕 К сожалению, ваша идея была отклонена. Но мы ценим ваше участие!"
                },
                "проблема": {
                    "solved": "✅ Ваша проблема была отмечена как решенная. Спасибо за сообщение!",
                    "not_found": "🔍 Мы проверили вашу проблему, но не обнаружили никаких неполадок."
                },
                "отзыв": {
                    "thanks": "❤️ Спасибо за ваш отзыв! Мы очень ценим это!",
                    "sorry": "🙏 Спасибо за ваш отзыв. Нам жаль, что у вас остались такие впечатления."
                },
                "другое": {
                    "accept": "🔹 Ваше обращение было принято.",
                    "reject": "🔹 Ваше обращение было рассмотрено, но отклонено."
                }
            }

            if action != "persistent_restored":
                msg_template = messages.get(self.feedback_type, messages["другое"])
                message = msg_template.get(action, "🔹 Ваше обращение было рассмотрено.")

                if self.feedback_type != "отзыв" and self.user_message:
                    try:
                        user_embed = discord.Embed(
                            title=f"📢 Ответ на ваше обращение ({self.feedback_type})",
                            description=message,
                            color=discord.Color.blue() if action in ["accept", "solved", "thanks"] else discord.Color.orange(),
                            timestamp=datetime.now()
                        )

                        user_text = self.truncate_text(self.user_message, 1024)
                        user_embed.add_field(
                            name="📝 Ваше обращение:",
                            value=user_text,
                            inline=False
                        )

                        user_embed.set_footer(text=f"Модератор: {interaction.user.display_name}")

                        await user.send(embed=user_embed)
                    except discord.HTTPException as e:
                        print(f"Ошибка при отправке embed пользователю: {e}")
                        short_message = self.truncate_text(self.user_message, 500)
                        await user.send(f"{message}\n\n**Ваше обращение:** {short_message}")
                else:
                    await user.send(message)

            self.save_action({
                "thread_id": self.thread_id,
                "user_id": self.user_id,
                "feedback_type": self.feedback_type,
                "action": action,
                "processed_by": interaction.user.id,
                "processed_at": datetime.now().isoformat(),
                "message_id": self.message_id,
                "current_state": self.current_state,
                "user_message": self.user_message
            })

            await interaction.response.send_message(
                f"✅ Ответ отправлен пользователю {user.mention}",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Не удалось отправить сообщение пользователю (возможно, закрыты ЛС)",
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Пользователь не найден",
                ephemeral=True
            )
        except Exception as e:
            print(f"Ошибка при обработке feedback: {e}")
            await interaction.response.send_message(
                "❌ Произошла ошибка при обработке",
                ephemeral=True
            )

    def save_action(self, action_data):
        actions = self.load_actions()
        key = str(self.message_id) if self.message_id else str(self.thread_id)
        actions[key] = action_data
        with open(config.FEEDBACK_ACTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(actions, f, ensure_ascii=False, indent=2)

    def load_actions(self):
        if os.path.exists(config.FEEDBACK_ACTIONS_FILE):
            with open(config.FEEDBACK_ACTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

class FeedbackReplyModal(discord.ui.Modal, title="Ответ на обращение"):
    def __init__(self, feedback_type: str, thread_id: int, user_id: int):
        super().__init__()
        self.feedback_type = feedback_type
        self.thread_id = thread_id
        self.user_id = user_id

    reply_message = discord.ui.TextInput(
        label="Ваш ответ",
        style=discord.TextStyle.long,
        placeholder="Напишите ваш ответ пользователю...",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            thread = await interaction.client.fetch_channel(self.thread_id)
            if not thread:
                await interaction.followup.send("❌ Тред не найден", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"📝 Ответ модератора ({self.feedback_type})",
                description=self.reply_message.value,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Модератор: {interaction.user.display_name}")

            await thread.send(embed=embed)

            try:
                user = await interaction.client.fetch_user(self.user_id)
                if user:
                    user_embed = discord.Embed(
                        title=f"📢 Ответ на ваше обращение ({self.feedback_type})",
                        description=self.reply_message.value,
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    user_embed.set_footer(text=f"Модератор: {interaction.user.display_name}")
                    await user.send(embed=user_embed)
            except discord.Forbidden:
                print(f"Не удалось отправить сообщение пользователю {self.user_id}")

            await interaction.followup.send("✅ Ответ успешно отправлен", ephemeral=True)

        except Exception as e:
            print(f"Ошибка при отправке ответа: {e}")
            await interaction.followup.send("❌ Произошла ошибка при отправке ответа", ephemeral=True)

class FeedbackModal(discord.ui.Modal, title="Оставить отзыв/проблему/идею"):
    feedback_type = discord.ui.TextInput(
        label="Тип обращения",
        placeholder="проблема/отзыв/идея (можно несколько через запятую)",
        required=True,
        max_length=100
    )

    message = discord.ui.TextInput(
        label="Ваше сообщение",
        style=discord.TextStyle.long,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            user_id = interaction.user.id
            current_week = datetime.now().isocalendar()[1]

            if user_id in user_feedback_counts:
                if user_feedback_counts[user_id]['week'] == current_week and user_feedback_counts[user_id]['count'] >= 10:
                    await interaction.followup.send(
                        "❌ Лимит: 10 feedback'ов в неделю",
                        ephemeral=True
                    )
                    return

            if user_id not in user_feedback_counts or user_feedback_counts[user_id]['week'] != current_week:
                user_feedback_counts[user_id] = {'week': current_week, 'count': 0}
            user_feedback_counts[user_id]['count'] += 1

            tags = []
            feedback_types = [ft.strip().lower() for ft in self.feedback_type.value.split(',')]
            primary_type = "другое"

            if any(t in feedback_types for t in ['проблема', 'проблемы']):
                tags.append(config.TAG_PROBLEMA)
                primary_type = "проблема"
            if any(t in feedback_types for t in ['отзыв', 'отзывы']):
                tags.append(config.TAG_OTZYV)
                primary_type = "отзыв"
            if any(t in feedback_types for t in ['идея', 'идеи']):
                tags.append(config.TAG_IDEA)
                primary_type = "идея"

            if not tags:
                tags.append(config.TAG_DRUGOE)

            source = f"Сервер: {interaction.guild.name}" if interaction.guild else "ЛС"

            embed = discord.Embed(
                title="📢 Новое обращение",
                description=self.message.value,
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.set_author(
                name=f"{interaction.user.display_name} (ID: {interaction.user.id})",
                icon_url=interaction.user.display_avatar.url
            )
            embed.add_field(name="🔹 Тип", value=self.feedback_type.value, inline=True)
            embed.add_field(name="📌 Источник", value=source, inline=True)
            embed.set_footer(text="Обращение получено")

            forum_channel = await interaction.client.fetch_channel(config.FEEDBACK_FORUM_ID)

            if not isinstance(forum_channel, discord.ForumChannel):
                raise ValueError("Указанный канал не является форумом")

            thread_name = f"{interaction.user.display_name} | {primary_type.capitalize()}"
            thread_message = await forum_channel.create_thread(
                name=thread_name[:100],
                embed=embed,
                applied_tags=[discord.Object(id=tag) for tag in tags]
            )

            response_messages = {
                "проблема": "🔹 Проблема ожидает рассмотрения:",
                "идея": "🔹 Идея ожидает рассмотрения:",
                "отзыв": "🔹 Отзыв был получен:",
                "другое": "🔹 Обращение было получено:"
            }
            response_message = response_messages.get(primary_type, response_messages["другое"])

            feedback_message = await thread_message.thread.send(response_message)

            view = FeedbackActionView(
                thread_message.thread.id,
                interaction.user.id,
                primary_type,
                feedback_message.id,
                user_message=self.message.value
            )

            await feedback_message.edit(view=view)

            await interaction.followup.send(
                "✅ Ваше обращение успешно отправлено!",
                ephemeral=True
            )
        except Exception as e:
            print(f"Ошибка при отправке feedback: {e}")
            await interaction.followup.send(
                "❌ Произошла ошибка при отправке. Пожалуйста, попробуйте позже.",
                ephemeral=True
            )

@bot.tree.command(name="feedback", description="Отправить отзыв, сообщить о проблеме или предложить идею")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def feedback(interaction: discord.Interaction):
    await interaction.response.send_modal(FeedbackModal())