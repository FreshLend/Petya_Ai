import discord
import asyncio
import os
import json
import re
import base64
import hashlib
import math
import cmath
import config
from typing import Literal, Optional
from decimal import Decimal, getcontext
from sympy import *
from discord import app_commands
from datetime import datetime

shutdown_flag = False
reboot_flag = False

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

def convert_integral_expression(expr: str) -> str:
    import re
    pattern = r'∫\(([^)]+)\)\s+d([a-zA-Z])'
    match = re.search(pattern, expr)
    if match:
        inner = match.group(1)
        var = match.group(2)
        if ' to ' in inner:
            parts = inner.split(' to ')
            if len(parts) == 2:
                func = parts[0].strip()
                upper = parts[1].strip()
                new_expr = f"integrate({func}, ({var}, 0, {upper}))"
                return expr[:match.start()] + new_expr + expr[match.end():]
    expr = re.sub(r'∫\s*([a-zA-Z0-9\(\)\+\-\*\/\^]+)\s+d([a-zA-Z])', r'integrate(\1, \2)', expr)
    return expr

def convert_limit_expression(expr: str) -> str:
    import re
    expr = expr.replace('lim', 'limit')
    expr = expr.replace('→', ', ')
    expr = expr.replace('->', ', ')
    pattern = r'limit\s*\{\s*([a-zA-Z])\s*->\s*([^}]+)\s*\}\s*(.+)'
    match = re.search(pattern, expr)
    if match:
        var = match.group(1)
        point = match.group(2).strip()
        func = match.group(3).strip()
        return f"limit({func}, {var}, {point})"
    pattern2 = r'limit\s*\(\s*([^,]+)\s*,\s*([a-zA-Z]+)\s*,\s*([^)]+)\s*\)'
    match2 = re.search(pattern2, expr)
    if match2:
        return expr
    pattern3 = r'limit\s*\(\s*([^,]+)\s*,\s*([a-zA-Z]+)\s*->\s*([^)]+)\s*\)'
    match3 = re.search(pattern3, expr)
    if match3:
        func = match3.group(1)
        var = match3.group(2)
        point = match3.group(3)
        return f"limit({func}, {var}, {point})"
    return expr

def convert_greek_symbols(expr: str) -> str:
    greek_symbols = {
        'Γ': 'gamma', 'γ': 'gamma', 'Δ': 'Delta', 'δ': 'delta', 'ε': 'epsilon',
        'ζ': 'zeta', 'η': 'eta', 'θ': 'theta', 'Θ': 'Theta', 'ι': 'iota',
        'κ': 'kappa', 'λ': 'lambda', 'Λ': 'Lambda', 'μ': 'mu', 'ν': 'nu',
        'ξ': 'xi', 'Ξ': 'Xi', 'π': 'pi', 'Π': 'Pi', 'ρ': 'rho', 'σ': 'sigma',
        'Σ': 'Sigma', 'τ': 'tau', 'υ': 'upsilon', 'φ': 'phi', 'Φ': 'Phi',
        'χ': 'chi', 'ψ': 'psi', 'Ψ': 'Psi', 'ω': 'omega', 'Ω': 'Omega',
        '∞': 'oo', '∂': 'diff', '∇': 'nabla', 'ℏ': 'hbar',
        'α': 'alpha', 'β': 'beta'
    }
    for symbol, replacement in greek_symbols.items():
        expr = expr.replace(symbol, replacement)
    return expr

def evaluate_expression(expr: str, var: str = 'x'):
    try:
        x = symbols(var)
        expr_clean = expr.replace('log', 'ln').replace('ln', 'log')
        try:
            expr_sym = sympify(expr_clean, locals={var: x, 'gamma': gamma})
            if expr_sym.free_symbols:
                try:
                    f = lambdify(x, expr_sym, modules='math')
                    return f"f({var}) = {latex(expr_sym)}"
                except:
                    return latex(expr_sym)
            else:
                result_value = float(expr_sym)
                return format_number(result_value)
        except Exception:
            safe_dict = create_safe_dict()
            result = eval(expr_clean, {"__builtins__": {}}, safe_dict)
            if isinstance(result, (int, float, complex)):
                return format_number(result)
            return str(result)
    except Exception as e:
        raise ValueError(f"Не удалось вычислить выражение: {str(e)}")

def create_safe_dict():
    return {
        'abs': abs, 'round': round, 'min': min, 'max': max, 'pow': pow,
        'sum': sum, 'int': int, 'float': float, 'complex': complex,
        'bool': bool, 'len': len, 'str': str, 'pi': math.pi, 'e': math.e,
        'tau': math.tau, 'inf': float('inf'), 'nan': float('nan'),
        'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
        'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
        'atan2': math.atan2, 'sinh': math.sinh, 'cosh': math.cosh,
        'tanh': math.tanh, 'asinh': math.asinh, 'acosh': math.acosh,
        'atanh': math.atanh, 'log': math.log, 'log10': math.log10,
        'log2': math.log2, 'log1p': math.log1p, 'exp': math.exp,
        'expm1': math.expm1, 'sqrt': math.sqrt,
        'cbrt': lambda x: x ** (1/3) if x >= 0 else -((-x) ** (1/3)),
        'factorial': math.factorial, 'gamma': math.gamma, 'lgamma': math.lgamma,
        'erf': math.erf, 'erfc': math.erfc, 'gcd': math.gcd,
        'lcm': lambda a, b: abs(a*b) // math.gcd(a,b) if a and b else 0,
        'degrees': math.degrees, 'radians': math.radians, 'ceil': math.ceil,
        'floor': math.floor, 'trunc': math.trunc, 'fmod': math.fmod,
        'fabs': math.fabs, 'copysign': math.copysign, 'fsum': math.fsum,
        'isclose': math.isclose, 'isfinite': math.isfinite, 'isinf': math.isinf,
        'isnan': math.isnan, 'mean': lambda *args: sum(args)/len(args) if args else 0,
        'median': lambda *args: sorted(args)[len(args)//2] if args else 0,
        'i': 1j, 'j': 1j,
        'integrate': lambda func, var, a, b: integrate_expression_numeric(str(func), str(var), float(a), float(b)),
        'limit': lambda func, var, point: calculate_limit_numeric(str(func), str(var), float(point)),
        'oo': float('inf'), 'gamma': gamma,
    }

def simplify_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        simplified = simplify(expr_sym)
        return latex(simplified)
    except Exception as e:
        raise ValueError(f"Не удалось упростить выражение: {str(e)}")

def solve_equation(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        solutions = solve(expr_sym, var_symbol)
        return [latex(sol) for sol in solutions]
    except Exception as e:
        raise ValueError(f"Не удалось решить уравнение: {str(e)}")

def expand_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        expanded = expand(expr_sym)
        return latex(expanded)
    except Exception as e:
        raise ValueError(f"Не удалось разложить выражение: {str(e)}")

def factor_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        factored = factor(expr_sym)
        return latex(factored)
    except Exception as e:
        raise ValueError(f"Не удалось факторизовать выражение: {str(e)}")

def differentiate_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        derivative = diff(expr_sym, var_symbol)
        return latex(derivative)
    except Exception as e:
        raise ValueError(f"Не удалось найти производную: {str(e)}")

def integrate_expression(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        integral = integrate(expr_sym, var_symbol)
        return latex(integral)
    except Exception as e:
        raise ValueError(f"Не удалось найти интеграл: {str(e)}")

def calculate_limit(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        lim = limit(expr_sym, var_symbol, 0)
        return latex(lim)
    except Exception as e:
        raise ValueError(f"Не удалось вычислить предел: {str(e)}")

def series_expansion(expr: str, var: str):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        series_exp = series(expr_sym, var_symbol, 0, 5)
        return latex(series_exp.removeO())
    except Exception as e:
        raise ValueError(f"Не удалось разложить в ряд: {str(e)}")

def evaluate_complex(expr: str):
    try:
        expr = expr.replace('i', 'j').replace('I', 'j')
        safe_dict = {'j': 1j, 'pi': math.pi, 'e': math.e, 'gamma': gamma}
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        if not isinstance(result, complex):
            result = complex(result)
        real = result.real
        imag = result.imag
        if abs(imag) < 1e-12:
            return f"{format_number(real)}"
        elif abs(real) < 1e-12:
            return f"{format_number(imag)}i"
        else:
            sign = '+' if imag >= 0 else '-'
            return f"{format_number(real)} {sign} {format_number(abs(imag))}i"
    except Exception as e:
        raise ValueError(f"Не удалось вычислить комплексное выражение: {str(e)}")

def integrate_expression_numeric(expr: str, var: str, a: float, b: float):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        integral = integrate(expr_sym, (var_symbol, a, b))
        if integral.is_number:
            return float(integral)
        return latex(integral)
    except Exception as e:
        raise ValueError(f"Не удалось вычислить интеграл: {str(e)}")

def calculate_limit_numeric(expr: str, var: str, point: float):
    try:
        var_symbol = symbols(var)
        expr_sym = sympify(expr, locals={var: var_symbol, 'gamma': gamma})
        lim = limit(expr_sym, var_symbol, point)
        if lim.is_number:
            return float(lim)
        return latex(lim)
    except Exception as e:
        raise ValueError(f"Не удалось вычислить предел: {str(e)}")

def format_number(num):
    if isinstance(num, complex):
        return format_complex(num)
    if isinstance(num, (int, Decimal)):
        return str(num)
    if abs(num) > 1e12 or (abs(num) < 1e-6 and abs(num) > 0):
        return f"{num:.10e}".replace('e+', 'e').replace('e-', 'e-').replace('e0', '')
    if hasattr(num, 'is_integer') and num.is_integer():
        return str(int(num))
    formatted = f"{num:.15f}".rstrip('0').rstrip('.')
    if len(formatted) > 15:
        return f"{num:.10g}"
    return formatted

def format_complex(c):
    real = c.real
    imag = c.imag
    if abs(imag) < 1e-12:
        return format_number(real)
    elif abs(real) < 1e-12:
        return f"{format_number(imag)}i"
    else:
        sign = '+' if imag >= 0 else '-'
        return f"{format_number(real)} {sign} {format_number(abs(imag))}i"

def create_calculation_embed(expr, result, steps, precision):
    embed = discord.Embed(
        title="🧮 Математический калькулятор",
        description=f"**Выражение:**\n```\n{expr}\n```",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📊 Результат",
        value=f"```\n{result}\n```",
        inline=False
    )
    if steps:
        steps_text = generate_calculation_steps(expr)
        if steps_text:
            embed.add_field(
                name="🔍 Шаги решения",
                value=steps_text,
                inline=False
            )
    if precision:
        embed.set_footer(text=f"Точность: {precision} знаков")
    return embed

def create_simplify_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Упрощение выражения",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📝 Исходное выражение",
        value=f"```\n{expr}\n```",
        inline=False
    )
    embed.add_field(
        name="✅ Упрощенное выражение",
        value=f"```\n{result}\n```",
        inline=False
    )
    return embed

def create_solve_embed(expr, solutions, var, steps):
    embed = discord.Embed(
        title="🧮 Решение уравнения",
        color=discord.Color.orange()
    )
    embed.add_field(
        name="📝 Уравнение",
        value=f"```\n{expr} = 0\n```",
        inline=False
    )
    if solutions:
        solutions_text = "\n".join([f"**{var} =** `{sol}`" for sol in solutions])
        embed.add_field(
            name=f"🎯 Решения ({len(solutions)})",
            value=solutions_text,
            inline=False
        )
    else:
        embed.add_field(
            name="❌ Решений нет",
            value="Уравнение не имеет действительных решений",
            inline=False
        )
    return embed

def create_expand_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Разложение выражения",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="📝 Исходное выражение",
        value=f"```\n{expr}\n```",
        inline=False
    )
    embed.add_field(
        name="🔍 Разложенное выражение",
        value=f"```\n{result}\n```",
        inline=False
    )
    return embed

def create_factor_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Факторизация выражения",
        color=discord.Color.dark_green()
    )
    embed.add_field(
        name="📝 Исходное выражение",
        value=f"```\n{expr}\n```",
        inline=False
    )
    embed.add_field(
        name="🎯 Факторизованное выражение",
        value=f"```\n{result}\n```",
        inline=False
    )
    return embed

def create_differentiate_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Дифференцирование",
        color=discord.Color.dark_blue()
    )
    embed.add_field(
        name="📝 Функция",
        value=f"```\nf({var}) = {expr}\n```",
        inline=False
    )
    embed.add_field(
        name="📈 Производная",
        value=f"```\nf'({var}) = {result}\n```",
        inline=False
    )
    return embed

def create_integrate_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Интегрирование",
        color=discord.Color.dark_purple()
    )
    embed.add_field(
        name="📝 Функция",
        value=f"```\n∫ {expr} d{var}\n```",
        inline=False
    )
    embed.add_field(
        name="📊 Интеграл",
        value=f"```\n{result} + C\n```",
        inline=False
    )
    return embed

def create_limit_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Вычисление предела",
        color=discord.Color.dark_orange()
    )
    embed.add_field(
        name="📝 Выражение",
        value=f"```\nlim({var}→0) {expr}\n```",
        inline=False
    )
    embed.add_field(
        name="🎯 Предел",
        value=f"```\n{result}\n```",
        inline=False
    )
    return embed

def create_series_embed(expr, result, var, steps):
    embed = discord.Embed(
        title="🧮 Разложение в ряд Тейлора",
        color=discord.Color.dark_red()
    )
    embed.add_field(
        name="📝 Функция",
        value=f"```\nf({var}) = {expr}\n```",
        inline=False
    )
    embed.add_field(
        name="📈 Ряд Тейлора (до 5-го члена)",
        value=f"```\n{result} + O({var}⁶)\n```",
        inline=False
    )
    return embed

def create_complex_embed(expr, result, steps):
    embed = discord.Embed(
        title="🧮 Комплексные числа",
        color=discord.Color.teal()
    )
    embed.add_field(
        name="📝 Выражение",
        value=f"```\n{expr}\n```",
        inline=False
    )
    embed.add_field(
        name="🎯 Результат",
        value=f"```\n{result}\n```",
        inline=False
    )
    try:
        expr_fixed = expr.replace('i', 'j').replace('I', 'j')
        safe_dict = {'j': 1j, 'pi': math.pi, 'e': math.e, 'gamma': gamma}
        complex_num = eval(expr_fixed, {"__builtins__": {}}, safe_dict)
        if not isinstance(complex_num, complex):
            complex_num = complex(complex_num)
        magnitude = abs(complex_num)
        phase = math.degrees(cmath.phase(complex_num))
        embed.add_field(
            name="📊 Комплексная форма",
            value=(
                f"**Модуль (r):** `{format_number(magnitude)}`\n"
                f"**Аргумент (φ):** `{format_number(phase)}°`\n"
                f"**Тригонометрическая форма:** `{format_number(magnitude)}·e^(i·{format_number(math.radians(phase))})`"
            ),
            inline=False
        )
    except:
        pass
    return embed

def generate_calculation_steps(expr):
    steps = []
    expr_clean = expr.replace(" ", "")
    steps.append(f"**1. Исходное выражение:** `{expr}`")
    if '(' in expr_clean and ')' in expr_clean:
        steps.append("**2. Вычисление выражений в скобках**")
    if '**' in expr_clean or '^' in expr_clean:
        steps.append("**3. Возведение в степень**")
    if '*' in expr_clean or '/' in expr_clean:
        steps.append("**4. Умножение и деление**")
    if '+' in expr_clean or '-' in expr_clean:
        steps.append("**5. Сложение и вычитание**")
    return "\n".join(steps) if steps else ""

async def shutdown_handler():
    print("\nПолучен сигнал завершения работы...")
    translator.unload()
    await aibot.shutdown()
    await bot.close()

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

@bot.tree.command(name="calc", description="Выполнить математические вычисления")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    expression="Математическое выражение для вычисления",
    precision="Точность вычислений (количество знаков после запятой)"
)
async def calc(interaction: discord.Interaction, expression: str, precision: int = 6):
    await interaction.response.defer()
    class SmartCalculator:
        def __init__(self):
            self.constants = {
                'pi': math.pi, 'π': math.pi, 'e': math.e, 'tau': math.tau,
                'τ': math.tau, 'inf': float('inf'), '∞': float('inf'),
                'phi': 1.618033988749895, 'φ': 1.618033988749895,
            }
            self.functions = {
                'sqrt': lambda x: math.sqrt(x), '√': lambda x: math.sqrt(x),
                'sin': lambda x: math.sin(x), 'cos': lambda x: math.cos(x),
                'tan': lambda x: math.tan(x), 'tg': lambda x: math.tan(x),
                'ctg': lambda x: 1 / math.tan(x) if math.tan(x) != 0 else float('inf'),
                'asin': lambda x: math.asin(x), 'acos': lambda x: math.acos(x),
                'atan': lambda x: math.atan(x), 'arcsin': lambda x: math.asin(x),
                'arccos': lambda x: math.acos(x), 'arctan': lambda x: math.atan(x),
                'ln': lambda x: math.log(x), 'log': lambda x: math.log10(x),
                'log2': lambda x: math.log2(x), 'exp': lambda x: math.exp(x),
                'abs': lambda x: abs(x), 'floor': lambda x: math.floor(x),
                'ceil': lambda x: math.ceil(x), 'round': lambda x: round(x),
                'factorial': lambda x: math.factorial(int(x)) if x >= 0 and x == int(x) else float('nan'),
                '!': lambda x: math.factorial(int(x)) if x >= 0 and x == int(x) else float('nan'),
                'rad': lambda x: math.radians(x), 'deg': lambda x: math.degrees(x),
                'sinh': lambda x: math.sinh(x), 'cosh': lambda x: math.cosh(x),
                'tanh': lambda x: math.tanh(x),
            }
            self.operators = {
                '+': (1, lambda a, b: a + b), '-': (1, lambda a, b: a - b),
                '*': (2, lambda a, b: a * b), '×': (2, lambda a, b: a * b),
                '/': (2, lambda a, b: a / b if b != 0 else float('inf')),
                '÷': (2, lambda a, b: a / b if b != 0 else float('inf')),
                '//': (2, lambda a, b: a // b if b != 0 else float('inf')),
                '%': (2, lambda a, b: a % b if b != 0 else float('inf')),
                '^': (3, lambda a, b: a ** b), '**': (3, lambda a, b: a ** b),
            }
        def preprocess_expression(self, expr: str) -> str:
            expr = expr.lower().replace(' ', '')
            expr = expr.replace('pi', 'π').replace('tau', 'τ').replace('phi', 'φ')
            expr = expr.replace('×', '*').replace('÷', '/').replace('√', 'sqrt')
            expr = re.sub(r'(\d)(\()', r'\1*\2', expr)
            expr = re.sub(r'(\d)([a-zφπτ√])', r'\1*\2', expr)
            expr = re.sub(r'\)\(', ')*(', expr)
            expr = re.sub(r'([πτφ])(\d)', r'\1*\2', expr)
            expr = re.sub(r'([πτφ])(\()', r'\1*\2', expr)
            expr = re.sub(r'\(-', '(0-', expr)
            expr = re.sub(r',-', ',0-', expr)
            expr = re.sub(r'(\d)e([+-]?\d+)', r'\1e\2', expr)
            if expr.startswith('-'):
                expr = '0' + expr
            return expr
        def tokenize(self, expr: str) -> list:
            tokens = []
            i = 0
            while i < len(expr):
                char = expr[i]
                if char.isspace():
                    i += 1
                    continue
                if char.isdigit() or char == '.':
                    num = ''
                    while i < len(expr) and (expr[i].isdigit() or expr[i] == '.' or expr[i] == 'e' or expr[i] == 'E'):
                        num += expr[i]
                        i += 1
                        if (expr[i-1] == 'e' or expr[i-1] == 'E') and i < len(expr) and expr[i] in '+-':
                            num += expr[i]
                            i += 1
                    tokens.append(('number', float(num)))
                    continue
                if char.isalpha() or char in 'πτφ√':
                    name = ''
                    while i < len(expr) and (expr[i].isalpha() or expr[i] in 'πτφ√'):
                        name += expr[i]
                        i += 1
                    if name in self.constants:
                        tokens.append(('number', self.constants[name]))
                    elif name in self.functions:
                        tokens.append(('function', name))
                    else:
                        raise ValueError(f"Неизвестная функция или константа: {name}")
                    continue
                if char in '+-*/^%':
                    if i + 1 < len(expr) and expr[i:i+2] in ['**', '//']:
                        tokens.append(('operator', expr[i:i+2]))
                        i += 2
                    else:
                        tokens.append(('operator', char))
                        i += 1
                    continue
                if char in '(),':
                    tokens.append(('paren', char))
                    i += 1
                    continue
                raise ValueError(f"Неизвестный символ: {char}")
            return tokens
        def shunting_yard(self, tokens: list) -> list:
            output = []
            stack = []
            for token_type, token_value in tokens:
                if token_type == 'number':
                    output.append(token_value)
                elif token_type == 'function':
                    stack.append(('function', token_value))
                elif token_type == 'operator':
                    while (stack and stack[-1][0] == 'operator' and
                           self.operators[stack[-1][1]][0] >= self.operators[token_value][0]):
                        output.append(stack.pop()[1])
                    stack.append(('operator', token_value))
                elif token_type == 'paren' and token_value == '(':
                    stack.append(('paren', '('))
                elif token_type == 'paren' and token_value == ')':
                    while stack and stack[-1] != ('paren', '('):
                        output.append(stack.pop()[1])
                    if not stack:
                        raise ValueError("Несбалансированные скобки")
                    stack.pop()
                    if stack and stack[-1][0] == 'function':
                        output.append(stack.pop()[1])
            while stack:
                if stack[-1][0] == 'paren':
                    raise ValueError("Несбалансированные скобки")
                output.append(stack.pop()[1])
            return output
        def evaluate_rpn(self, rpn: list) -> float:
            stack = []
            for token in rpn:
                if isinstance(token, float):
                    stack.append(token)
                elif token in self.operators:
                    if len(stack) < 2:
                        raise ValueError("Недостаточно операндов для оператора")
                    b = stack.pop()
                    a = stack.pop()
                    result = self.operators[token][1](a, b)
                    stack.append(result)
                elif token in self.functions:
                    if len(stack) < 1:
                        raise ValueError("Недостаточно операндов для функции")
                    x = stack.pop()
                    result = self.functions[token](x)
                    stack.append(result)
            if len(stack) != 1:
                raise ValueError("Некорректное выражение")
            return stack[0]
        def calculate(self, expr: str) -> float:
            try:
                processed_expr = self.preprocess_expression(expr)
                tokens = self.tokenize(processed_expr)
                rpn = self.shunting_yard(tokens)
                result = self.evaluate_rpn(rpn)
                return result
            except Exception as e:
                raise ValueError(f"Ошибка вычисления: {str(e)}")
    try:
        calculator = SmartCalculator()
        result = calculator.calculate(expression)
        if math.isnan(result):
            formatted_result = "Неопределено"
        elif math.isinf(result):
            formatted_result = "∞" if result > 0 else "-∞"
        else:
            if isinstance(result, (int, float)) and result == int(result):
                formatted_result = str(int(result))
            else:
                if abs(result) < 1e-10:
                    formatted_result = "0"
                elif abs(result) < 1e-6 or abs(result) > 1e10:
                    formatted_result = f"{result:.{precision}e}"
                else:
                    formatted_result = f"{result:.{precision}f}".rstrip('0').rstrip('.')
        embed = discord.Embed(title="🧮 Калькулятор", color=discord.Color.green())
        embed.add_field(name="📝 Выражение", value=f"```{expression}```", inline=False)
        embed.add_field(name="📊 Результат", value=f"```{formatted_result}```", inline=False)
        help_text = "**Доступные функции:** sin, cos, tan, sqrt, log, ln, abs, factorial и др.\n"
        help_text += "**Константы:** π, e, τ, φ, ∞\n"
        help_text += f"**Точность:** {precision} знаков"
        embed.add_field(name="ℹ️ Справка", value=help_text, inline=False)
        await interaction.followup.send(embed=embed)
    except ZeroDivisionError:
        await interaction.followup.send("❌ **Ошибка:** Деление на ноль!", ephemeral=True)
    except ValueError as e:
        await interaction.followup.send(f"❌ **Ошибка вычисления:** {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ **Неизвестная ошибка:** {str(e)}", ephemeral=True)

@bot.tree.command(name="cipher", description="Шифрование и расшифровка текста")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    action="Действие: шифровать или расшифровать",
    cipher_type="Тип шифра",
    text="Текст для обработки",
    key="Ключ (если требуется)",
    shift="Сдвиг для шифра Цезаря"
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="🔒 Зашифровать", value="encrypt"),
        app_commands.Choice(name="🔓 Расшифровать", value="decrypt")
    ],
    cipher_type=[
        app_commands.Choice(name="🔁 Цезарь", value="caesar"),
        app_commands.Choice(name="🔁 Атбаш", value="atbash"),
        app_commands.Choice(name="🔁 ROT13", value="rot13"),
        app_commands.Choice(name="🔁 Виженер", value="vigenere"),
        app_commands.Choice(name="🔁 Base64", value="base64"),
        app_commands.Choice(name="🔁 Морзе", value="morse"),
        app_commands.Choice(name="🔁 HEX", value="hex"),
        app_commands.Choice(name="🔁 Бинарный", value="binary"),
        app_commands.Choice(name="🔁 XOR", value="xor"),
        app_commands.Choice(name="🔁 Аффинный", value="affine"),
        app_commands.Choice(name="🚫 MD5", value="md5"),
        app_commands.Choice(name="🚫 SHA-1", value="sha1"),
        app_commands.Choice(name="🚫 SHA-256", value="sha256"),
        app_commands.Choice(name="🚫 SHA-512", value="sha512"),
    ]
)
async def cipher(
    interaction: discord.Interaction,
    action: str,
    cipher_type: str,
    text: str,
    key: str = None,
    shift: int = 3
):
    await interaction.response.defer()
    class CipherProcessor:
        def __init__(self):
            self.morse_dict = {
                'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 'G': '--.',
                'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.',
                'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-', 'U': '..-',
                'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--', 'Z': '--..',
                '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-', '5': '.....',
                '6': '-....', '7': '--...', '8': '---..', '9': '----.',
                'А': '.-', 'Б': '-...', 'В': '.--', 'Г': '--.', 'Д': '-..', 'Е': '.', 'Ё': '.',
                'Ж': '...-', 'З': '--..', 'И': '..', 'Й': '.---', 'К': '-.-', 'Л': '.-..', 'М': '--',
                'Н': '-.', 'О': '---', 'П': '.--.', 'Р': '.-.', 'С': '...', 'Т': '-', 'У': '..-',
                'Ф': '..-.', 'Х': '....', 'Ц': '-.-.', 'Ч': '---.', 'Ш': '----', 'Щ': '--.-',
                'Ъ': '.--.-.', 'Ы': '-.--', 'Ь': '-..-', 'Э': '..-..', 'Ю': '..--', 'Я': '.-.-',
                ' ': '/'
            }
            self.reverse_morse = {v: k for k, v in self.morse_dict.items()}
            self.russian_upper = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
            self.russian_lower = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
            self.english_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            self.english_lower = "abcdefghijklmnopqrstuvwxyz"
        def _is_russian(self, char: str) -> bool:
            return 'А' <= char <= 'я' or char in 'Ёё'
        def caesar(self, text: str, shift: int, encrypt: bool = True) -> str:
            result = []
            shift_amount = shift if encrypt else -shift
            for char in text:
                if char.isalpha():
                    if self._is_russian(char):
                        if char.isupper():
                            alphabet = self.russian_upper
                        else:
                            alphabet = self.russian_lower
                        idx = (alphabet.index(char) + shift_amount) % len(alphabet)
                        result.append(alphabet[idx])
                    else:
                        if char.isupper():
                            result.append(chr((ord(char) - 65 + shift_amount) % 26 + 65))
                        else:
                            result.append(chr((ord(char) - 97 + shift_amount) % 26 + 97))
                else:
                    result.append(char)
            return ''.join(result)
        def atbash(self, text: str) -> str:
            result = []
            for char in text:
                if char.isalpha():
                    if self._is_russian(char):
                        if char.isupper():
                            alphabet = self.russian_upper
                            idx = alphabet.index(char)
                            result.append(alphabet[len(alphabet) - 1 - idx])
                        else:
                            alphabet = self.russian_lower
                            idx = alphabet.index(char)
                            result.append(alphabet[len(alphabet) - 1 - idx])
                    else:
                        if char.isupper():
                            result.append(chr(155 - ord(char)))
                        else:
                            result.append(chr(219 - ord(char)))
                else:
                    result.append(char)
            return ''.join(result)
        def rot13(self, text: str) -> str:
            result = []
            for char in text:
                if char.isalpha():
                    if self._is_russian(char):
                        if char.isupper():
                            alphabet = self.russian_upper
                        else:
                            alphabet = self.russian_lower
                        idx = (alphabet.index(char) + 16) % len(alphabet)
                        result.append(alphabet[idx])
                    else:
                        if char.isupper():
                            result.append(chr((ord(char) - 65 + 13) % 26 + 65))
                        else:
                            result.append(chr((ord(char) - 97 + 13) % 26 + 97))
                else:
                    result.append(char)
            return ''.join(result)
        def vigenere(self, text: str, key: str, encrypt: bool = True) -> str:
            result = []
            key_index = 0
            for char in text:
                if char.isalpha():
                    key_char = key[key_index % len(key)]
                    if self._is_russian(char):
                        if char.isupper():
                            alphabet = self.russian_upper
                        else:
                            alphabet = self.russian_lower
                        if self._is_russian(key_char):
                            key_alphabet = self.russian_upper if key_char.isupper() else self.russian_lower
                        else:
                            key_alphabet = self.english_upper if key_char.isupper() else self.english_lower
                        char_idx = alphabet.index(char)
                        key_idx = key_alphabet.index(key_char) if key_char in key_alphabet else 0
                        new_idx = (char_idx + key_idx) % len(alphabet) if encrypt else (char_idx - key_idx) % len(alphabet)
                        result.append(alphabet[new_idx])
                    else:
                        shift = ord(key_char.upper()) - 65
                        if not encrypt:
                            shift = -shift
                        if char.isupper():
                            result.append(chr((ord(char) - 65 + shift) % 26 + 65))
                        else:
                            result.append(chr((ord(char) - 97 + shift) % 26 + 97))
                    key_index += 1
                else:
                    result.append(char)
            return ''.join(result)
        def base64_encode(self, text: str) -> str:
            return base64.b64encode(text.encode('utf-8')).decode('utf-8')
        def base64_decode(self, text: str) -> str:
            try:
                return base64.b64decode(text.encode('utf-8')).decode('utf-8')
            except:
                return "❌ Ошибка декодирования Base64"
        def morse_encode(self, text: str) -> str:
            text = text.upper()
            result = []
            for char in text:
                result.append(self.morse_dict.get(char, '?'))
            return ' '.join(result)
        def morse_decode(self, text: str) -> str:
            words = text.split(' / ')
            result = []
            for word in words:
                chars = word.split()
                decoded_word = ''.join(self.reverse_morse.get(char, '?') for char in chars)
                result.append(decoded_word)
            return ' '.join(result)
        def hex_encode(self, text: str) -> str:
            return text.encode('utf-8').hex()
        def hex_decode(self, text: str) -> str:
            try:
                return bytes.fromhex(text).decode('utf-8')
            except:
                return "❌ Ошибка декодирования HEX"
        def binary_encode(self, text: str) -> str:
            return ' '.join(format(ord(c), '08b') for c in text)
        def binary_decode(self, text: str) -> str:
            try:
                binary_values = text.split()
                return ''.join(chr(int(b, 2)) for b in binary_values)
            except:
                return "❌ Ошибка декодирования бинарного кода"
        def xor_cipher(self, text: str, key: str) -> str:
            result = []
            for i, char in enumerate(text):
                result.append(chr(ord(char) ^ ord(key[i % len(key)])))
            return base64.b64encode(''.join(result).encode('utf-8')).decode('utf-8')
        def xor_decipher(self, text: str, key: str) -> str:
            try:
                decoded = base64.b64decode(text.encode('utf-8')).decode('utf-8')
                result = []
                for i, char in enumerate(decoded):
                    result.append(chr(ord(char) ^ ord(key[i % len(key)])))
                return ''.join(result)
            except:
                return "❌ Ошибка декодирования XOR"
        def affine_encrypt(self, text: str, a: int = 5, b: int = 8) -> str:
            result = []
            for char in text:
                if char.isalpha():
                    if self._is_russian(char):
                        alphabet_size = 33
                        if char.isupper():
                            base = ord('А')
                        else:
                            base = ord('а')
                        x = ord(char) - base
                        result.append(chr(((a * x + b) % alphabet_size) + base))
                    else:
                        alphabet_size = 26
                        if char.isupper():
                            base = ord('A')
                        else:
                            base = ord('a')
                        x = ord(char) - base
                        result.append(chr(((a * x + b) % alphabet_size) + base))
                else:
                    result.append(char)
            return ''.join(result)
        def affine_decrypt(self, text: str, a: int = 5, b: int = 8) -> str:
            result = []
            for char in text:
                if char.isalpha():
                    if self._is_russian(char):
                        alphabet_size = 33
                        if char.isupper():
                            base = ord('А')
                        else:
                            base = ord('а')
                        a_inv = 0
                        for i in range(alphabet_size):
                            if (a * i) % alphabet_size == 1:
                                a_inv = i
                                break
                        y = ord(char) - base
                        result.append(chr(((a_inv * (y - b)) % alphabet_size) + base))
                    else:
                        alphabet_size = 26
                        if char.isupper():
                            base = ord('A')
                        else:
                            base = ord('a')
                        a_inv = 0
                        for i in range(alphabet_size):
                            if (a * i) % alphabet_size == 1:
                                a_inv = i
                                break
                        y = ord(char) - base
                        result.append(chr(((a_inv * (y - b)) % alphabet_size) + base))
                else:
                    result.append(char)
            return ''.join(result)
        def md5_hash(self, text: str) -> str:
            return hashlib.md5(text.encode('utf-8')).hexdigest()
        def sha1_hash(self, text: str) -> str:
            return hashlib.sha1(text.encode('utf-8')).hexdigest()
        def sha256_hash(self, text: str) -> str:
            return hashlib.sha256(text.encode('utf-8')).hexdigest()
        def sha512_hash(self, text: str) -> str:
            return hashlib.sha512(text.encode('utf-8')).hexdigest()
    processor = CipherProcessor()
    try:
        result = ""
        cipher_name = ""
        if cipher_type == "caesar":
            cipher_name = "Цезарь"
            if action == "encrypt":
                result = processor.caesar(text, shift, True)
            else:
                result = processor.caesar(text, shift, False)
        elif cipher_type == "atbash":
            cipher_name = "Атбаш"
            result = processor.atbash(text)
        elif cipher_type == "rot13":
            cipher_name = "ROT13"
            result = processor.rot13(text)
        elif cipher_type == "vigenere":
            cipher_name = "Виженер"
            if not key:
                await interaction.followup.send("❌ Для шифра Виженера требуется ключ!", ephemeral=True)
                return
            if action == "encrypt":
                result = processor.vigenere(text, key, True)
            else:
                result = processor.vigenere(text, key, False)
        elif cipher_type == "base64":
            cipher_name = "Base64"
            if action == "encrypt":
                result = processor.base64_encode(text)
            else:
                result = processor.base64_decode(text)
        elif cipher_type == "morse":
            cipher_name = "Морзе"
            if action == "encrypt":
                result = processor.morse_encode(text)
            else:
                result = processor.morse_decode(text)
        elif cipher_type == "hex":
            cipher_name = "HEX"
            if action == "encrypt":
                result = processor.hex_encode(text)
            else:
                result = processor.hex_decode(text)
        elif cipher_type == "binary":
            cipher_name = "Бинарный"
            if action == "encrypt":
                result = processor.binary_encode(text)
            else:
                result = processor.binary_decode(text)
        elif cipher_type == "xor":
            cipher_name = "XOR"
            if not key:
                await interaction.followup.send("❌ Для XOR шифра требуется ключ!", ephemeral=True)
                return
            if action == "encrypt":
                result = processor.xor_cipher(text, key)
            else:
                result = processor.xor_decipher(text, key)
        elif cipher_type == "affine":
            cipher_name = "Аффинный"
            if action == "encrypt":
                result = processor.affine_encrypt(text)
            else:
                result = processor.affine_decrypt(text)
        elif cipher_type == "md5":
            cipher_name = "MD5"
            result = processor.md5_hash(text)
        elif cipher_type == "sha1":
            cipher_name = "SHA-1"
            result = processor.sha1_hash(text)
        elif cipher_type == "sha256":
            cipher_name = "SHA-256"
            result = processor.sha256_hash(text)
        elif cipher_type == "sha512":
            cipher_name = "SHA-512"
            result = processor.sha512_hash(text)
        action_emoji = "🔒" if action == "encrypt" else "🔓"
        action_text = "Зашифровано" if action == "encrypt" else "Расшифровано"
        embed = discord.Embed(title=f"{action_emoji} {cipher_name} - {action_text}", color=discord.Color.blue())
        embed.add_field(name="📥 Исходный текст", value=f"```{text}```", inline=False)
        display_result = result[:1000] + "..." if len(result) > 1000 else result
        embed.add_field(name="📤 Результат", value=f"```{display_result}```", inline=False)
        if key:
            embed.add_field(name="🔑 Ключ", value=f"`{key}`", inline=True)
        if cipher_type == "caesar":
            embed.add_field(name="📏 Сдвиг", value=f"`{shift}`", inline=True)
        if cipher_type in ["md5", "sha1", "sha256", "sha512"]:
            embed.add_field(name="⚠️ Внимание", value="Это хэш-функция - результат не может быть расшифрован!", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Произошла ошибка при обработке: {str(e)}", ephemeral=True)

@bot.tree.command(name="connect", description="Подключить бота к голосовому каналу")
async def connect(interaction: discord.Interaction, disconnect: bool = False):
    await interaction.response.defer()
    if disconnect:
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.followup.send("Отключился от голосового канала!")
        else:
            await interaction.followup.send("Бот не подключен к голосовому каналу!")
    else:
        if interaction.user.voice:
            await interaction.user.voice.channel.connect()
            await interaction.followup.send("Подключился к голосовому каналу!")
        else:
            await interaction.followup.send("Вы не находитесь в голосовом канале!")

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

@bot.tree.command(name="feedback", description="Отправить отзыв, сообщить о проблеме или предложить идею")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def feedback(interaction: discord.Interaction):
    await interaction.response.send_modal(FeedbackModal())

@bot.tree.command(name="help", description="Показать список команд по категориям")
@app_commands.describe(category="Выберите категорию команд")
@app_commands.choices(category=[
    app_commands.Choice(name="Искусственный Интеллект", value="ai"),
    app_commands.Choice(name="Развлечения", value="fun"),
    app_commands.Choice(name="Экономика", value="economy"),
    app_commands.Choice(name="Инструменты", value="tools")
])
async def help_command(interaction: discord.Interaction, category: app_commands.Choice[str]):
    await interaction.response.defer()
    if category.value == "ai":
        embed1 = discord.Embed(title="📚 Список команд: Искусственный Интеллект", color=0x2b2d31)
        embed1.description = "**🤖 Искусственный Интеллект**"
        embed1.add_field(
            name="Доступные команды:",
            value=(
                "• `/ask question:` - Задать вопрос ИИ\n"
                "• `/define term:` - Определить термин\n"
                "• `/get parameter: (system_prompt)` - Получить параметр\n"
                "• `/history limit:` - История запросов\n"
                "• `/model_info` - Информация о модели\n"
                "• `/queue_info` - Информация об очереди"
            ),
            inline=False
        )
        embed2 = discord.Embed(color=0x2b2d31)
        embed2.add_field(
            name="",
            value=(
                "• `/reset parameter: (context, system_prompt, all)` - Сбросить параметры\n"
                "• `/set parameter: (system_prompt) value:` - Установить параметр\n"
                "• `/set_model model:` - Выбрать модель\n"
                "• `/summarize text:` - Суммаризировать текст\n"
                "• `/translate text: to_language: from_language:` - Перевести текст"
            ),
            inline=False
        )
        embed2.set_footer(text=f"Запрошено: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.followup.send(embeds=[embed1, embed2])
    elif category.value == "fun":
        embed = discord.Embed(title="📚 Список команд: Развлечения", color=0x2b2d31)
        embed.description = "**🎪 Развлечения**"
        embed.add_field(
            name="Доступные команды:",
            value=(
                "• `/8ball question:` - Магический шар\n"
                "• `/interact_bang target:` - Выстрелить в пользователя\n"
                "• `/interact_bye target:` - Отправить прощальное сообщение\n"
                "• `/interact_hi target:` - Отправить приветственное сообщение\n"
                "• `/interact_kiss target: cheeks:` - Поцеловать пользователя\n"
                "• `/joke` - Случайная шутка\n"
                "• `/quote` - Случайная цитата\n"
                "• `/roll max_number:` - Случайное число"
            ),
            inline=False
        )
        embed.set_footer(text=f"Запрошено: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.followup.send(embed=embed)
    elif category.value == "economy":
        embed1 = discord.Embed(title="📚 Список команд: Экономика", color=0x2b2d31)
        embed1.description = "**💰 Экономика**"
        embed1.add_field(
            name="Доступные команды:",
            value=(
                "• `/bank action: (create, list, rename, set_comission, set_service, info) name: set_comission: set_service: new_name:` - Управление банком\n"
                "• `/deposit amount: currency: (Медные монеты, Серебряные монеты, Золотые монеты, Платиновые монеты)` - Внести депозит\n"
                "• `/exchange amount: from_currency: (copper, silver, gold, platinum) to_currency: (copper, silver, gold, platinum)` - Обмен валюты\n"
                "• `/inventory` - Инвентарь\n"
                "• `/profile create: user:` - Профиль\n"
                "• `/casino action: amount: choice:` - Казино с различными играми"
            ),
            inline=False
        )
        embed2 = discord.Embed(color=0x2b2d31)
        embed2.add_field(
            name="",
            value=(
                "• `/set_bank name:` - Установить банк\n"
                "• `/shop black_store:` - Магазин\n"
                "• `/transfer amount: currency: (Медные монеты, Серебряные монеты, Золотые монеты, Платиновые монеты) user:` - Перевести деньги\n"
                "• `/treasure` - Поиск сокровищ\n"
                "• `/withdraw amount: currency: (Медные монеты, Серебряные монеты, Золотые монеты, Платиновые монеты)` - Снять деньги\n"
                "• `/work profession_list:` - Работа"
            ),
            inline=False
        )
        embed2.set_footer(text=f"Запрошено: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.followup.send(embeds=[embed1, embed2])
    elif category.value == "tools":
        embed1 = discord.Embed(title="📚 Список команд: Инструменты", color=0x2b2d31)
        embed1.description = "**🛠️ Инструменты**"
        embed1.add_field(
            name="Доступные команды:",
            value=(
                "• `/avatar user:` - Аватар пользователя\n"
                "• `/bot_channel action: (set_channel, reset_channel, show_channel) channel:` - Управление каналом бота\n"
                "• `/connect disconnect:` - Подключиться к голосовому каналу\n"
                "• `/calc expression: precision:` - Выполнить математические вычисления\n"
                "• `/cipher action: (🔒 Зашифровать, 🔓 Расшифровать) cipher_type: (🔁 Цезарь, 🔁 Атбаш, 🔁 ROT13, 🔁 Виженер, 🔁 Base64, 🔁 Морзе, 🔁 HEX, 🔁 Бинарный, 🔁 XOR, 🔁 Аффинный, 🚫 MD5, 🚫 SHA-1, 🚫 SHA-256, 🚫 SHA-512) text: key: shift:` - Шифрование и расшифровка текста\n"
                "• `/emoji action: (send, info) emoji: format:` - Работа с эмодзи\n"
                "• `/emoji_list server_id:` - Список эмодзи сервера\n"
                "• `/feedback` - Обратная связь\n"
                "• `/info short_info:` - Информация о боте"
                "• `/math expression: mode: variable: steps: precision:` - Вычислить математическое выражение"
            ),
            inline=False
        )
        embed2 = discord.Embed(color=0x2b2d31)
        embed2.add_field(
            name="",
            value=(
                "• `/invite` - Пригласить бота\n"
                "• `/ping` - Проверка задержки\n"
                "• `/plugins action: (list, info, reload, reload_all, files, load, unload) plugin_id:` - Управление плагинами\n"
                "• `/reboot` - Перезагрузить бота\n"
                "• `/say text:` - Сказать от имени бота\n"
                "• `/servers content:` - Информация о серверах\n"
                "• `/set_group user: group: (разработчик, тестер, покупатель, пользователь)` - Установить группу\n"
                "• `/shutdown` - Выключить бота\n"
                "• `/help category:` - Эта команда"
            ),
            inline=False
        )
        embed2.set_footer(text=f"Запрошено: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.followup.send(embeds=[embed1, embed2])

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
        member_count = sum(guild.member_count for guild in bot.guilds)
        bot_count = sum(len([m for m in guild.members if m.bot]) for guild in bot.guilds)
        human_count = member_count - bot_count
        ping = round(bot.latency * 1000)
        embed = discord.Embed(title="💎 Статистика Бота", color=discord.Color.blue())
        embed.add_field(name="👑 — Разработчик:", value="<@1136934279348224042>", inline=False)
        embed.add_field(name="🤖 — Имя бота:", value="<@1137405206288666634>", inline=False)
        embed.add_field(name="📝 — Описание:", value="Petya_Ai - это бот с Искусственным Интеллектом, у него есть развлечения в виде экономической игры и многое другое!", inline=False)
        embed.add_field(name="🖥 Серверов:", value=str(guild_count), inline=False)
        embed.add_field(name="👥 Участников:", value=str(human_count), inline=False)
        embed.add_field(name="🔨 Дата создания:", value="<t:1691321400:F>", inline=False)
        embed.add_field(name="🛠 Версия:", value="2.6.1", inline=False)
        embed.add_field(name="<:petya_ai:1387518848961482842> Модель:", value="Petya_Ai-IM2\n**Бета версия:** Petya_Ai-IM2.5", inline=False)
        embed.add_field(name="⏱ Задержка:", value=f"{ping}мс", inline=False)
        embed.add_field(name="🕒 Время работы:", value=f"<t:{unix_time}:F> - <t:{unix_time}:R>", inline=False)
        embed.add_field(name="🌐 — Наш сайт:", value="[Нажми сюда!](https://freshlend.github.io)", inline=False)
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

@bot.tree.command(name="math", description="Вычислить математическое выражение")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    expression="Математическое выражение для вычисления (без f(x)=)",
    mode="Режим вычисления",
    variable="Переменная (для дифференцирования/интегрирования)",
    steps="Показать шаги решения",
    precision="Точность вычислений (количество знаков)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="вычислить", value="calculate"),
    app_commands.Choice(name="упростить", value="simplify"),
    app_commands.Choice(name="решить уравнение", value="solve"),
    app_commands.Choice(name="разложить", value="expand"),
    app_commands.Choice(name="факторизовать", value="factor"),
    app_commands.Choice(name="дифференцировать", value="diff"),
    app_commands.Choice(name="проинтегрировать", value="integrate"),
    app_commands.Choice(name="предел", value="limit"),
    app_commands.Choice(name="ряд", value="series"),
    app_commands.Choice(name="комплексные числа", value="complex")
])
async def math_command(
    interaction: discord.Interaction,
    expression: str,
    mode: str = "calculate",
    variable: Optional[str] = "x",
    steps: bool = False,
    precision: Optional[int] = 10
):
    await interaction.response.defer()
    try:
        expression_clean = expression.strip()
        if not expression_clean:
            raise ValueError("Пустое выражение")
        if expression_clean.startswith("f(x) = "):
            expression_clean = expression_clean[7:].strip()
        elif expression_clean.startswith("f(x)="):
            expression_clean = expression_clean[5:].strip()
        elif expression_clean.startswith("y = "):
            expression_clean = expression_clean[4:].strip()
        elif expression_clean.startswith("y="):
            expression_clean = expression_clean[2:].strip()
        expression_clean = expression_clean.replace('^', '**')
        expression_clean = expression_clean.replace('÷', '/')
        expression_clean = expression_clean.replace('×', '*')
        expression_clean = convert_integral_expression(expression_clean)
        expression_clean = convert_limit_expression(expression_clean)
        expression_clean = convert_greek_symbols(expression_clean)
        if precision and 1 <= precision <= 100:
            getcontext().prec = precision
        if mode == "calculate":
            result = evaluate_expression(expression_clean, variable)
            embed = create_calculation_embed(expression, result, steps, precision)
        elif mode == "simplify":
            result = simplify_expression(expression_clean, variable)
            embed = create_simplify_embed(expression, result, variable, steps)
        elif mode == "solve":
            solutions = solve_equation(expression_clean, variable)
            embed = create_solve_embed(expression, solutions, variable, steps)
        elif mode == "expand":
            result = expand_expression(expression_clean, variable)
            embed = create_expand_embed(expression, result, variable, steps)
        elif mode == "factor":
            result = factor_expression(expression_clean, variable)
            embed = create_factor_embed(expression, result, variable, steps)
        elif mode == "diff":
            result = differentiate_expression(expression_clean, variable)
            embed = create_differentiate_embed(expression, result, variable, steps)
        elif mode == "integrate":
            result = integrate_expression(expression_clean, variable)
            embed = create_integrate_embed(expression, result, variable, steps)
        elif mode == "limit":
            result = calculate_limit(expression_clean, variable)
            embed = create_limit_embed(expression, result, variable, steps)
        elif mode == "series":
            result = series_expansion(expression_clean, variable)
            embed = create_series_embed(expression, result, variable, steps)
        elif mode == "complex":
            result = evaluate_complex(expression_clean)
            embed = create_complex_embed(expression, result, steps)
        else:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Неизвестный режим вычисления",
                color=discord.Color.red()
            )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Ошибка вычисления",
            description=f"**Выражение:** `{expression}`\n\n**Ошибка:** {str(e)}",
            color=discord.Color.red()
        )
        error_embed.add_field(
            name="💡 Правильный формат",
            value=(
                "Для интегралов используйте: `integrate(tan(t**3), (t, 0, x))`\n"
                "Для пределов используйте: `limit(gamma(x+h)/gamma(x)**(1/h), h, 0)`\n"
                "Или просто введите: `exp(sin(x**2)) * log(1 + cos(3*x))`"
            ),
            inline=False
        )
        await interaction.followup.send(embed=error_embed)

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