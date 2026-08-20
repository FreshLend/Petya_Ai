import discord
from discord import app_commands
import traceback
import json
import os
import config
from typing import Dict, List
import asyncio

class HealthCheck:
    def __init__(self):
        self.results: Dict[str, str] = {}
        self.failed: List[str] = []
    
    async def run_all(self) -> Dict[str, str]:
        self.results = {}
        self.failed = []
        
        await self.test_math()
        await self.test_cipher()
        await self.test_economy_utils()
        await self.test_economy_loaders()
        await self.test_entertainment()
        await self.test_feedback()
        await self.test_context()
        await self.test_core()
        await self.test_commands()
        await self.test_ai()
        await self.test_translator()
        await self.test_characters()
        await self.test_economy_functions()
        await self.test_casino_games()
        await self.test_command_registration()
        
        return self.results
    
    def _get_global(self, name: str):
        return globals().get(name)
    
    async def test_math(self):
        try:
            eval_func = self._get_global('evaluate_expression')
            if eval_func is None:
                self.results['math'] = "❌ Функция evaluate_expression не найдена"
                self.failed.append('math')
                return
            result = eval_func("2+2")
            if str(result).strip() == "4":
                self.results['math'] = "✅ OK"
            else:
                self.results['math'] = f"❌ Ожидалось '4', получено '{result}'"
                self.failed.append('math')
        except Exception as e:
            self.results['math'] = f"❌ Ошибка: {e}"
            self.failed.append('math')
            traceback.print_exc()
    
    async def test_cipher(self):
        try:
            CipherProcessor = self._get_global('CipherProcessor')
            if CipherProcessor is None:
                self.results['cipher'] = "❌ Класс CipherProcessor не найден"
                self.failed.append('cipher')
                return
            cp = CipherProcessor()
            text = "test"
            encrypted = cp.caesar(text, 3, True)
            decrypted = cp.caesar(encrypted, 3, False)
            if decrypted == text:
                self.results['cipher'] = "✅ OK"
            else:
                self.results['cipher'] = f"❌ Ожидалось '{text}', получено '{decrypted}'"
                self.failed.append('cipher')
        except Exception as e:
            self.results['cipher'] = f"❌ Ошибка: {e}"
            self.failed.append('cipher')
            traceback.print_exc()
    
    async def test_economy_utils(self):
        try:
            to_copper_func = self._get_global('to_copper')
            if to_copper_func is None:
                self.results['economy_utils'] = "❌ Функция to_copper не найдена"
                self.failed.append('economy_utils')
                return
            result = to_copper_func(5, "gold_coin")
            if result == 50000:
                self.results['economy_utils'] = "✅ OK"
            else:
                self.results['economy_utils'] = f"❌ Ожидалось 50000, получено {result}"
                self.failed.append('economy_utils')
        except Exception as e:
            self.results['economy_utils'] = f"❌ Ошибка: {e}"
            self.failed.append('economy_utils')
            traceback.print_exc()
    
    async def test_economy_loaders(self):
        loaders = [
            ('load_profiles', 'profiles'),
            ('load_shop', 'shop'),
            ('load_treasure_data', 'treasure'),
            ('load_inventory', 'inventory'),
            ('load_banks', 'banks')
        ]
        for func_name, label in loaders:
            try:
                func = self._get_global(func_name)
                if func is None:
                    self.results[f'economy_loader_{label}'] = f"❌ Функция {func_name} не найдена"
                    self.failed.append(f'economy_loader_{label}')
                    continue
                _ = func()
                self.results[f'economy_loader_{label}'] = "✅ OK"
            except Exception as e:
                self.results[f'economy_loader_{label}'] = f"❌ Ошибка: {e}"
                self.failed.append(f'economy_loader_{label}')
                traceback.print_exc()
    
    async def test_entertainment(self):
        try:
            load_func = self._get_global('_load_interactables')
            if load_func is None:
                self.results['entertainment'] = "❌ Функция _load_interactables не найдена"
                self.failed.append('entertainment')
                return
            data = load_func()
            if isinstance(data, dict):
                self.results['entertainment'] = f"✅ OK (найдено {len(data)} ключей)"
            else:
                self.results['entertainment'] = "❌ Данные не являются словарём"
                self.failed.append('entertainment')
        except Exception as e:
            self.results['entertainment'] = f"❌ Ошибка: {e}"
            self.failed.append('entertainment')
            traceback.print_exc()
    
    async def test_feedback(self):
        try:
            path = config.FEEDBACK_ACTIONS_FILE
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                self.results['feedback'] = "✅ OK (файл создан)"
            else:
                self.results['feedback'] = "✅ OK"
        except Exception as e:
            self.results['feedback'] = f"❌ Ошибка: {e}"
            self.failed.append('feedback')
            traceback.print_exc()
    
    async def test_context(self):
        try:
            load_ctx = self._get_global('load_contexts_sync')
            if load_ctx is None:
                self.results['context'] = "❌ Функция load_contexts_sync не найдена"
                self.failed.append('context')
                return
            data = load_ctx()
            self.results['context'] = f"✅ OK (загружено {len(data)} контекстов)"
        except Exception as e:
            self.results['context'] = f"❌ Ошибка: {e}"
            self.failed.append('context')
            traceback.print_exc()
    
    async def test_core(self):
        try:
            aibot_obj = self._get_global('aibot')
            if aibot_obj is None:
                self.results['core'] = "❌ Объект aibot не найден"
                self.failed.append('core')
                return
            if aibot_obj.models_config:
                self.results['core'] = f"✅ OK (моделей: {len(aibot_obj.models_config)})"
            else:
                self.results['core'] = "⚠️ Нет загруженных моделей"
        except Exception as e:
            self.results['core'] = f"❌ Ошибка: {e}"
            self.failed.append('core')
            traceback.print_exc()
    
    async def test_commands(self):
        try:
            bot_obj = self._get_global('bot')
            if bot_obj is None:
                self.results['commands'] = "❌ Объект bot не найден"
                self.failed.append('commands')
                return
            if hasattr(bot_obj, 'tree'):
                self.results['commands'] = "✅ OK (tree доступен)"
            else:
                self.results['commands'] = "⚠️ tree не найден"
        except Exception as e:
            self.results['commands'] = f"❌ Ошибка: {e}"
            self.failed.append('commands')
            traceback.print_exc()
    
    async def test_ai(self):
        try:
            aibot_obj = self._get_global('aibot')
            if aibot_obj is None:
                self.results['ai'] = "❌ Объект aibot не найден"
                self.failed.append('ai')
                return
            
            if not aibot_obj.models_config:
                self.results['ai'] = "⚠️ Нет моделей – тест пропущен"
                return
            
            user_contexts_dict = self._get_global('user_contexts')
            if user_contexts_dict is None:
                self.results['ai'] = "❌ user_contexts не найден"
                self.failed.append('ai')
                return
            
            old_context = user_contexts_dict.get(0)
            test_prompt_system = "You are a helpful assistant that always responds with exactly the word 'hello' and nothing else."
            user_contexts_dict[0] = {
                "custom_system_prompt": test_prompt_system,
                "messages": []
            }
            
            try:
                response = await aibot_obj.generate_response_async(
                    prompt="What should you say?",
                    user_id=0,
                    save_context=False,
                    ignore_context=True,
                    was_mentioned=False
                )
            except Exception as gen_error:
                self.results['ai'] = f"❌ Ошибка генерации: {gen_error}"
                self.failed.append('ai')
                if old_context is not None:
                    user_contexts_dict[0] = old_context
                else:
                    del user_contexts_dict[0]
                traceback.print_exc()
                return
            
            if not response or not isinstance(response, str):
                self.results['ai'] = "❌ Ответ пустой или не строка"
                self.failed.append('ai')
            elif "hello" in response.lower():
                self.results['ai'] = f"✅ OK (ответ: {response[:50]})"
            else:
                self.results['ai'] = f"⚠️ Ответ не содержит 'hello' (получено: {response[:50]})"
            
            if old_context is not None:
                user_contexts_dict[0] = old_context
            else:
                if 0 in user_contexts_dict:
                    del user_contexts_dict[0]
            
        except Exception as e:
            self.results['ai'] = f"❌ Ошибка в тесте ИИ: {e}"
            self.failed.append('ai')
            traceback.print_exc()
    
    async def test_translator(self):
        try:
            translator_obj = self._get_global('translator')
            if translator_obj is None:
                self.results['translator'] = "❌ Объект translator не найден"
                self.failed.append('translator')
                return
            
            if not hasattr(translator_obj, 'translate_text'):
                self.results['translator'] = "❌ Метод translate_text отсутствует"
                self.failed.append('translator')
                return
            
            TORCH_AVAILABLE = self._get_global('TORCH_AVAILABLE')
            TRANSFORMERS_AVAILABLE = self._get_global('TRANSFORMERS_AVAILABLE')
            if not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE:
                self.results['translator'] = "❌ PyTorch или Transformers не установлены"
                self.failed.append('translator')
                return
            
            if translator_obj.model is None:
                try:
                    await translator_obj.load_model()
                    timeout = 60.0
                    start = asyncio.get_event_loop().time()
                    while translator_obj.model is None and (asyncio.get_event_loop().time() - start) < timeout:
                        await asyncio.sleep(0.5)
                    if translator_obj.model is None:
                        raise TimeoutError("Модель не загрузилась за 60 секунд")
                except asyncio.TimeoutError:
                    self.results['translator'] = "❌ Таймаут загрузки модели переводчика (>60 сек)"
                    self.failed.append('translator')
                    return
                except Exception as e:
                    self.results['translator'] = f"❌ Ошибка загрузки модели: {e}"
                    self.failed.append('translator')
                    traceback.print_exc()
                    return
            
            if translator_obj.model is None:
                self.results['translator'] = "❌ Модель не загрузилась (осталась None)"
                self.failed.append('translator')
                return
            
            try:
                result = await asyncio.wait_for(
                    translator_obj.translate_text("hello", "ru", from_lang="en"),
                    timeout=10.0
                )
                if result and isinstance(result, str) and len(result) > 0:
                    self.results['translator'] = f"✅ OK (перевод: {result[:30]})"
                else:
                    self.results['translator'] = "❌ Пустой ответ от переводчика"
                    self.failed.append('translator')
            except asyncio.TimeoutError:
                self.results['translator'] = "❌ Таймаут при переводе (>10 сек)"
                self.failed.append('translator')
            except Exception as e:
                self.results['translator'] = f"❌ Ошибка перевода: {e}"
                self.failed.append('translator')
                traceback.print_exc()
                
        except Exception as e:
            self.results['translator'] = f"❌ Ошибка в тесте переводчика: {e}"
            self.failed.append('translator')
            traceback.print_exc()
    
    async def test_characters(self):
        try:
            aibot_obj = self._get_global('aibot')
            if aibot_obj is None:
                self.results['characters'] = "❌ Объект aibot не найден"
                self.failed.append('characters')
                return
            if hasattr(aibot_obj, 'characters') and aibot_obj.characters:
                self.results['characters'] = f"✅ OK (загружено {len(aibot_obj.characters)} персонажей)"
            else:
                self.results['characters'] = "⚠️ Персонажи не загружены или пусты"
        except Exception as e:
            self.results['characters'] = f"❌ Ошибка: {e}"
            self.failed.append('characters')
            traceback.print_exc()
    
    async def test_economy_functions(self):
        try:
            can_afford_func = self._get_global('can_afford')
            add_money_func = self._get_global('add_money')
            deduct_money_func = self._get_global('deduct_money')
            if not can_afford_func or not add_money_func or not deduct_money_func:
                self.results['economy_functions'] = "❌ Одна из функций не найдена"
                self.failed.append('economy_functions')
                return
            
            money = {"gold_coin": 10, "silver_coin": 50}
            cost = {"gold_coin": 5, "silver_coin": 20}
            
            if not can_afford_func(money, cost):
                self.results['economy_functions'] = "❌ can_afford вернул False при достаточных средствах"
                self.failed.append('economy_functions')
                return
            
            new_money = deduct_money_func(money, cost)
            if new_money.get("gold_coin", 0) != 5 or new_money.get("silver_coin", 0) != 30:
                self.results['economy_functions'] = f"❌ deduct_money дал неверный результат: {new_money}"
                self.failed.append('economy_functions')
                return
            
            added = add_money_func(new_money, {"gold_coin": 3})
            if added.get("gold_coin", 0) != 8:
                self.results['economy_functions'] = f"❌ add_money дал неверный результат: {added}"
                self.failed.append('economy_functions')
                return
            
            self.results['economy_functions'] = "✅ OK"
        except Exception as e:
            self.results['economy_functions'] = f"❌ Ошибка: {e}"
            self.failed.append('economy_functions')
            traceback.print_exc()
    
    async def test_casino_games(self):
        try:
            SlotsGame = self._get_global('SlotsGame')
            ThimblesGame = self._get_global('ThimblesGame')
            BlackjackGame = self._get_global('BlackjackGame')
            if not SlotsGame or not ThimblesGame or not BlackjackGame:
                self.results['casino'] = "❌ Один из классов игр не найден"
                self.failed.append('casino')
                return
            
            settings = {
                "slots": {
                    "symbols": {
                        "🍒": {"weight": 40, "payout": 2},
                        "7️⃣": {"weight": 3, "payout": 50}
                    },
                    "jackpot_combination": ["7️⃣", "7️⃣", "7️⃣"],
                    "jackpot_payout": 100
                },
                "thimbles": {"win_multiplier": 2},
                "blackjack": {"min_bet": 10, "max_bet": 1000, "dealer_stop": 17}
            }
            
            slots = SlotsGame(settings)
            result, payout = slots.spin()
            if not isinstance(result, list) or len(result) != 3:
                self.results['casino'] = "❌ SlotsGame.spin вернул неверный формат"
                self.failed.append('casino')
                return
            
            thimbles = ThimblesGame(settings)
            won, pos = thimbles.play(1)
            if not isinstance(won, bool) or not (1 <= pos <= 3):
                self.results['casino'] = "❌ ThimblesGame.play вернул неверный формат"
                self.failed.append('casino')
                return
            
            bj = BlackjackGame(settings)
            card = bj.draw_card()
            if not card or not isinstance(card, str):
                self.results['casino'] = "❌ BlackjackGame.draw_card вернул неверный формат"
                self.failed.append('casino')
                return
            
            self.results['casino'] = "✅ OK"
        except Exception as e:
            self.results['casino'] = f"❌ Ошибка в тесте казино: {e}"
            self.failed.append('casino')
            traceback.print_exc()
    
    async def test_command_registration(self):
        try:
            bot_obj = self._get_global('bot')
            if bot_obj is None:
                self.results['commands_registered'] = "❌ Объект bot не найден"
                self.failed.append('commands_registered')
                return
            
            try:
                commands = await bot_obj.tree.fetch_commands()
                if len(commands) > 0:
                    self.results['commands_registered'] = f"✅ OK (зарегистрировано {len(commands)} глобальных команд)"
                else:
                    self.results['commands_registered'] = "⚠️ Нет глобальных команд (возможно, ещё не синхронизированы)"
            except discord.HTTPException as e:
                self.results['commands_registered'] = f"⚠️ Не удалось получить список команд: {e}"
            except Exception as e:
                self.results['commands_registered'] = f"❌ Ошибка при получении команд: {e}"
                self.failed.append('commands_registered')
                traceback.print_exc()
        except Exception as e:
            self.results['commands_registered'] = f"❌ Ошибка в тесте команд: {e}"
            self.failed.append('commands_registered')
            traceback.print_exc()


@bot.tree.command(name="health", description="Проверить работоспособность всех модулей")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def health_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        checker = HealthCheck()
        results = await checker.run_all()
        embed = discord.Embed(title="🧪 Проверка состояния", color=discord.Color.blue())
        for module, status in results.items():
            if "✅" in status or "OK" in status:
                emoji = "✅"
            elif "❌" in status:
                emoji = "❌"
            else:
                emoji = "⚠️"
            clean_status = status.replace("✅", "").replace("❌", "").strip()
            embed.add_field(name=f"{emoji} {module}", value=clean_status, inline=False)
        
        if checker.failed:
            embed.color = discord.Color.red()
            embed.set_footer(text=f"⚠️ Проблемные модули: {', '.join(checker.failed)}")
        else:
            embed.color = discord.Color.green()
            embed.set_footer(text="✅ Все системы работают")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка при выполнении теста: {e}", ephemeral=True)
        traceback.print_exc()