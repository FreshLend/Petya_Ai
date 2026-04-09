from discord import app_commands
from discord.ext import tasks, commands
from functools import lru_cache
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import discord
import time
import traceback
import config
import json
import asyncio
import os
import random
import signal
import sys

# ==================== СИСТЕМА ПЛАГИНОВ ====================

class PluginMetadata:
    def __init__(self, data: dict):
        self.id = data.get('id', 'unknown')
        self.name = data.get('name', 'Unknown Plugin')
        self.description = data.get('description', 'No description')
        self.author = data.get('author', 'Unknown')
        self.version = data.get('version', '1.0.0')
        self.dependencies = data.get('dependencies', [])
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'author': self.author,
            'version': self.version,
            'dependencies': self.dependencies
        }

class Plugin:
    def __init__(self, metadata: PluginMetadata, directory: str, loaded: bool = False):
        self.metadata = metadata
        self.directory = directory
        self.loaded = loaded
        self.commands = []
        self.tasks = []
        self.hooks = []
    
    def __str__(self):
        return f"Plugin({self.metadata.id}, v{self.metadata.version}, loaded: {self.loaded})"

class DependencyResolver:
    @staticmethod
    def parse_dependency(dep: str) -> Tuple[str, str, str]:
        import re
        
        pattern = r'^([a-zA-Z0-9_-]+)([<>=!~]*)(.*)$'
        match = re.match(pattern, dep)
        
        if not match:
            return dep, '', ''
        
        plugin_id = match.group(1)
        operator = match.group(2)
        version = match.group(3)
        
        return plugin_id, operator, version
    
    @staticmethod
    def version_match(required_version: str, operator: str, actual_version: str) -> bool:
        if not operator:
            return True
        
        from packaging import version
        
        try:
            req_ver = version.parse(required_version)
            act_ver = version.parse(actual_version)
        except:
            return False
        
        if operator == '==':
            return act_ver == req_ver
        elif operator == '>=':
            return act_ver >= req_ver
        elif operator == '<=':
            return act_ver <= req_ver
        elif operator == '>':
            return act_ver > req_ver
        elif operator == '<':
            return act_ver < req_ver
        elif operator == '!=':
            return act_ver != req_ver
        elif operator == '~=':
            return act_ver >= req_ver and act_ver < version.parse(str(req_ver.major + 1) + ".0.0")
        
        return False
    
    @staticmethod
    def check_dependencies(plugin: Plugin, available_plugins: Dict[str, Plugin]) -> Tuple[bool, List[str]]:
        missing_deps = []
        
        for dep in plugin.metadata.dependencies:
            plugin_id, operator, required_version = DependencyResolver.parse_dependency(dep)
            
            if plugin_id not in available_plugins:
                missing_deps.append(f"{dep} (не найден)")
                continue
            
            dep_plugin = available_plugins[plugin_id]
            
            if operator and required_version:
                if not DependencyResolver.version_match(required_version, operator, dep_plugin.metadata.version):
                    missing_deps.append(f"{dep} (требуется {operator}{required_version}, найдено {dep_plugin.metadata.version})")
            
            if not dep_plugin.loaded:
                missing_deps.append(f"{plugin_id} (не загружен)")
        
        return len(missing_deps) == 0, missing_deps

class PluginAPI:
    def __init__(self, bot):
        self.bot = bot
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_dirs = {}
        self.plugin_hooks = {
            'on_ready': [],
            'on_message': [],
            'on_voice_state_update': [],
            'on_member_join': [],
            'on_member_remove': [],
            'on_reaction_add': [],
            'on_reaction_remove': [],
            'before_command': [],
            'after_command': [],
            'custom_events': {}
        }
        self.shared_data = {}
        self.plugin_commands = {}
        self.plugin_tasks = {}

    def get_all_plugins_with_status(self) -> List[Plugin]:
        scanned_plugins = self.scan_plugins()
        
        for plugin in scanned_plugins:
            if plugin.metadata.id in self.plugins:
                self.plugins[plugin.metadata.id].loaded = plugin.loaded
        
        return list(self.plugins.values())
    
    def scan_plugins(self) -> List[Plugin]:
        plugins = []
        plugins_dir = "plugins"
        
        if not os.path.exists(plugins_dir):
            print("⚠️ Директория plugins не найдена")
            return plugins
        
        for plugin_name in os.listdir(plugins_dir):
            plugin_dir = os.path.join(plugins_dir, plugin_name)
            if os.path.isdir(plugin_dir):
                metadata_file = os.path.join(plugin_dir, "metadata.json")
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata_data = json.load(f)
                        metadata = PluginMetadata(metadata_data)
                        
                        existing_plugin = self.plugins.get(metadata.id)
                        if existing_plugin:
                            plugin = existing_plugin
                        else:
                            plugin = Plugin(metadata, plugin_dir, loaded=False)
                        
                        plugins.append(plugin)
                        print(f"📁 Найден плагин: {metadata.name} ({metadata.id}) - {'✅ Загружен' if plugin.loaded else '❌ Не загружен'}")
                    except Exception as e:
                        print(f"❌ Ошибка загрузки метаданных для {plugin_name}: {e}")
                else:
                    print(f"⚠️ Плагин {plugin_name} не имеет metadata.json")
        
        return plugins
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self.plugins.get(plugin_id)
    
    def get_all_plugins(self) -> List[Plugin]:
        return list(self.plugins.values())
    
    def get_loaded_plugins(self) -> List[Plugin]:
        return [p for p in self.plugins.values() if p.loaded]
    
    def register_plugin(self, plugin: Plugin):
        self.plugins[plugin.metadata.id] = plugin
        self.plugin_dirs[plugin.metadata.id] = plugin.directory
        print(f"📦 Зарегистрирован плагин: {plugin.metadata.name} ({plugin.metadata.id})")
    
    def resolve_plugin_path(self, relative_path: str, plugin_id: str = None) -> str:
        if plugin_id is None:
            return relative_path
        
        if plugin_id not in self.plugin_dirs:
            return relative_path
        
        plugin_dir = self.plugin_dirs[plugin_id]
        absolute_path = os.path.normpath(os.path.join(plugin_dir, relative_path))
        
        if not absolute_path.startswith(plugin_dir):
            raise SecurityError(f"Попытка доступа к файлу вне директории плагина: {relative_path}")
        
        return absolute_path
    
    def read_plugin_file(self, relative_path: str, plugin_id: str, encoding: str = "utf-8") -> str:
        absolute_path = self.resolve_plugin_path(relative_path, plugin_id)
        
        try:
            with open(absolute_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            with open(absolute_path, "r", encoding="cp1251") as f:
                return f.read()
    
    def write_plugin_file(self, relative_path: str, content: str, plugin_id: str, encoding: str = "utf-8"):
        absolute_path = self.resolve_plugin_path(relative_path, plugin_id)
        
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        
        with open(absolute_path, "w", encoding=encoding) as f:
            f.write(content)
    
    def plugin_file_exists(self, relative_path: str, plugin_id: str) -> bool:
        absolute_path = self.resolve_plugin_path(relative_path, plugin_id)
        return os.path.exists(absolute_path)
    
    def list_plugin_files(self, relative_path: str = ".", plugin_id: str = None) -> List[str]:
        absolute_path = self.resolve_plugin_path(relative_path, plugin_id)
        return os.listdir(absolute_path)
    
    def register_hook(self, hook_name: str, callback, plugin_id: str):
        if hook_name not in self.plugin_hooks:
            self.plugin_hooks[hook_name] = []
        
        self.plugin_hooks[hook_name].append({
            'callback': callback,
            'plugin_id': plugin_id
        })
        print(f"✅ Зарегистрирован хук '{hook_name}' для плагина '{plugin_id}'")
    
    def unregister_hooks(self, plugin_id: str):
        for hook_name in self.plugin_hooks:
            if hook_name in self.plugin_hooks:
                self.plugin_hooks[hook_name] = [
                    hook for hook in self.plugin_hooks[hook_name] 
                    if hook['plugin_id'] != plugin_id
                ]
    
    def register_command(self, command, plugin_id: str):
        if plugin_id not in self.plugin_commands:
            self.plugin_commands[plugin_id] = []
        
        self.plugin_commands[plugin_id].append(command)
        self.bot.tree.add_command(command)
        print(f"✅ Зарегистрирована команда от плагина '{plugin_id}': {command.name}")
    
    def unregister_commands(self, plugin_id: str):
        if plugin_id in self.plugin_commands:
            for command in self.plugin_commands[plugin_id]:
                self.bot.tree.remove_command(command.name)
            del self.plugin_commands[plugin_id]
    
    def register_task(self, task, plugin_id: str, task_name: str):
        if plugin_id not in self.plugin_tasks:
            self.plugin_tasks[plugin_id] = {}
        
        self.plugin_tasks[plugin_id][task_name] = task
        task.start()
        print(f"✅ Зарегистрирована задача '{task_name}' для плагина '{plugin_id}'")
    
    def unregister_tasks(self, plugin_id: str):
        if plugin_id in self.plugin_tasks:
            for task_name, task in self.plugin_tasks[plugin_id].items():
                task.cancel()
            del self.plugin_tasks[plugin_id]
    
    def set_shared_data(self, key: str, value: Any, plugin_id: str):
        self.shared_data[key] = {
            'value': value,
            'owner': plugin_id
        }
    
    def get_shared_data(self, key: str, default=None):
        return self.shared_data.get(key, {}).get('value', default)
    
    def call_hook(self, hook_name: str, *args, **kwargs):
        if hook_name not in self.plugin_hooks:
            return
        
        for hook in self.plugin_hooks[hook_name]:
            try:
                if asyncio.iscoroutinefunction(hook['callback']):
                    asyncio.create_task(hook['callback'](*args, **kwargs))
                else:
                    hook['callback'](*args, **kwargs)
            except Exception as e:
                print(f"❌ Ошибка в хуке '{hook_name}' плагина '{hook['plugin_id']}': {e}")
    
    def emit_event(self, event_name: str, *args, **kwargs):
        self.call_hook('custom_events', event_name, *args, **kwargs)
    
    def get_bot(self):
        return self.bot
    
    def get_config(self):
        return config

class SecurityError(Exception):
    pass

plugin_api = None

def get_plugin_api():
    return plugin_api

def plugin_hook(hook_name: str):
    def decorator(func):
        import inspect
        frame = inspect.currentframe()
        try:
            while frame:
                if 'plugin_id' in frame.f_globals:
                    plugin_id = frame.f_globals['plugin_id']
                    break
                frame = frame.f_back
            else:
                plugin_id = 'unknown'
        finally:
            del frame
        
        func._plugin_id = plugin_id
        
        api = get_plugin_api()
        if api:
            api.register_hook(hook_name, func, plugin_id)
        return func
    return decorator

def plugin_command(name: str = None, description: str = "Команда плагина", **kwargs):
    def decorator(func):
        import inspect
        frame = inspect.currentframe()
        try:
            while frame:
                if 'plugin_id' in frame.f_globals:
                    plugin_id = frame.f_globals['plugin_id']
                    break
                frame = frame.f_back
            else:
                plugin_id = 'unknown'
        finally:
            del frame
        
        func._plugin_id = plugin_id
        
        command = app_commands.command(
            name=name or func.__name__,
            description=description,
            **kwargs
        )(func)
        
        api = get_plugin_api()
        if api:
            api.register_command(command, plugin_id)
        
        return func
    return decorator

# ==================== МОДИФИЦИРОВАННЫЕ БОТ ЕВЕНТЫ С ХУКАМИ ====================

async def restart_bot():
    python = sys.executable
    os.execl(python, python, *sys.argv)

unix_time = int(time.time())

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    sync_commands=True
)

plugin_api = PluginAPI(bot)

avatar_schedule = {
    "spring": {"month": 3, "file": "Petya_Ai-Vesna.png"},
    "summer": {"month": 6, "file": "Petya_Ai-Leto.png"},
    "autumn": {"month": 9, "file": "Petya_Ai-Osen.png"},
    "winter": {"month": 12, "file": "Petya_Ai-Zima.png"}
}

special_events = {
    "halloween": {
        "start": {"month": 10, "day": 1},
        "end": {"month": 11, "day": 1},
        "file": "Petya_Ai-Halloween.png"
    }
}

def get_current_season(month):
    if 3 <= month < 6:
        return "spring"
    elif 6 <= month < 9:
        return "summer"
    elif 9 <= month < 12:
        return "autumn"
    else:
        return "winter"

def is_special_event_active(now):
    for event_name, event_info in special_events.items():
        start_month = event_info["start"]["month"]
        start_day = event_info["start"]["day"]
        end_month = event_info["end"]["month"]
        end_day = event_info["end"]["day"]
        
        if start_month > end_month:
            if (now.month == start_month and now.day >= start_day) or \
               (now.month == end_month and now.day <= end_day) or \
               (now.month > start_month or now.month < end_month):
                return event_name, event_info["file"]
        else:
            if (now.month == start_month and now.day >= start_day) or \
               (now.month == end_month and now.day <= end_day) or \
               (start_month < now.month < end_month):
                return event_name, event_info["file"]
    
    return None, None

def get_current_avatar():
    now = datetime.now()
    
    event_name, event_file = is_special_event_active(now)
    if event_name:
        return event_name, event_file
    
    if now.day == 1 and now.hour == 0:
        current_season = get_current_season(now.month)
        season_file = avatar_schedule[current_season]["file"]
        return current_season, season_file
    
    current_season = get_current_season(now.month)
    season_file = avatar_schedule[current_season]["file"]
    return current_season, season_file

@tasks.loop(minutes=1)
async def check_avatar_change():
    now = datetime.now()
    
    if now.hour == 0 and now.minute == 0:
        event_name, filename = get_current_avatar()
        
        try:
            if not os.path.exists(f"data/avatars/{filename}"):
                print(f"Файл data/avatars/{filename} не найден!")
                return
            
            with open(f"data/avatars/{filename}", "rb") as f:
                avatar_bytes = f.read()
            
            await bot.user.edit(avatar=avatar_bytes)
            print(f"✅ Аватар изменен на {filename} ({event_name}) в {now}")
            
        except FileNotFoundError:
            print(f"❌ Файл {filename} не найден в папке 'avatars'")
        except discord.HTTPException as e:
            print(f"❌ Ошибка Discord при смене аватара: {e}")
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")

@tasks.loop(hours=24)
async def daily_avatar_check():
    event_name, filename = get_current_avatar()
    
    try:
        with open(f"data/avatars/{filename}", "rb") as f:
            avatar_bytes = f.read()
        
        current_avatar_hash = hash(bot.user.avatar.url if bot.user.avatar else "")
        new_avatar_hash = hash(avatar_bytes)
        
        if current_avatar_hash != new_avatar_hash:
            await bot.user.edit(avatar=avatar_bytes)
            print(f"🔄 Аватар восстановлен: {filename} ({event_name})")
            
    except Exception as e:
        print(f"Ошибка при ежедневной проверке: {e}")

async def set_initial_avatar():
    event_name, filename = get_current_avatar()
    try:
        if os.path.exists(f"data/avatars/{filename}"):
            with open(f"data/avatars/{filename}", "rb") as f:
                avatar_bytes = f.read()
            await bot.user.edit(avatar=avatar_bytes)
            print(f"🎯 Установлена начальная аватарка: {filename} ({event_name})")
        else:
            print(f"⚠️ Файл data/avatars/{filename} не найден для начальной установки")
    except Exception as e:
        print(f"❌ Ошибка при установке начальной аватарки: {e}")

@tasks.loop(seconds=900)
async def status_loop():
    while True:
        guild_count = len(bot.guilds)
        member_count = sum(guild.member_count for guild in bot.guilds)
        bot_count = sum(len([m for m in guild.members if m.bot]) for guild in bot.guilds)
        members_count = member_count - bot_count
        
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{guild_count} серверов и {members_count} участников"
        ))
        await asyncio.sleep(300)

        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="/invite"
        ))
        await asyncio.sleep(300)

        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="/help"
        ))
        await asyncio.sleep(300)

@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')
    if not os.path.exists(config.FEEDBACK_ACTIONS_FILE):
        with open(config.FEEDBACK_ACTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    if not status_loop.is_running():
        status_loop.start()
    
    await FeedbackActionView.load_persistent_views(bot)
    bot.add_view(PersistentFeedbackView())

    bot.loop.create_task(restore_energy())
    await update_set_model_command()
    
    await set_initial_avatar()
    
    if not check_avatar_change.is_running():
        check_avatar_change.start()
    
    if not daily_avatar_check.is_running():
        daily_avatar_check.start()
    
    plugin_api.call_hook('on_ready')
    
    await bot.tree.sync()

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or shutdown_flag or reboot_flag:
        return
    
    plugin_api.call_hook('on_message', message)
    
    guild_id = message.guild.id if message.guild else None
    allowed_channel_id = server_settings.get(guild_id, {}).get("allowed_channel")
    
    if allowed_channel_id and message.channel.id != allowed_channel_id:
        return
    
    should_respond = False
    is_mentioned = bot.user.mentioned_in(message)
    
    if is_mentioned or random.random() < config.RANDOM_RESPONCE_CHANCE:
        should_respond = True
        
        clean_content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        if not clean_content or clean_content.startswith('!'):
            return
            
        async with message.channel.typing():
            response = await aibot.generate_response_async(
                clean_content, 
                message.author.id,
                save_context=False,
                ignore_context=True
            )
            
            use_mention = is_mentioned and random.random() >= config.NO_MENTION_CHANCE
            
            if use_mention:
                await message.reply(f"{message.author.mention} {response}")
            else:
                if random.random() < config.REPLY_PREFERENCE:
                    await message.reply(response)
                else:
                    await message.channel.send(response)

@bot.event
async def on_connect():
    print("✅ Подключение к Discord установлено")

@bot.event
async def on_disconnect():
    print("⚠️ Соединение с Discord разорвано")

@bot.event
async def on_resumed():
    print("🔄 Сессия возобновлена")

@bot.event
async def on_voice_state_update(member, before, after):
    plugin_api.call_hook('on_voice_state_update', member, before, after)

@bot.event
async def on_member_join(member):
    plugin_api.call_hook('on_member_join', member)

@bot.event
async def on_member_remove(member):
    plugin_api.call_hook('on_member_remove', member)

@bot.event
async def on_reaction_add(reaction, user):
    plugin_api.call_hook('on_reaction_add', reaction, user)

@bot.event
async def on_reaction_remove(reaction, user):
    plugin_api.call_hook('on_reaction_remove', reaction, user)

# ==================== СИСТЕМА ЗАГРУЗКИ ПЛАГИНОВ И МОДУЛЕЙ ====================

module_cache = {}
load_stats = {'success': 0, 'fail': 0, 'errors': []}

@lru_cache(maxsize=None)
def read_file_cached(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="cp1251") as file:
            return file.read()

class PluginContext:
    def __init__(self, plugin_dir, plugin_id):
        self.plugin_dir = plugin_dir
        self.plugin_id = plugin_id
        self.original_cwd = None
        
    def __enter__(self):
        self.original_cwd = os.getcwd()
        os.chdir(self.plugin_dir)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_cwd:
            os.chdir(self.original_cwd)
        return False

def print_tree_item(level: int, text: str, icon: str = "├"):
    indent = "  " * level
    print(f"{indent}{icon} {text}")

async def load_plugin_async(plugin: Plugin, level: int = 0, available_plugins: Dict[str, Plugin] = None):
    try:
        if plugin.metadata.id in getattr(config, 'DISABLED_PLUGINS', []):
            print_tree_item(level, f"⏭️ Плагин {plugin.metadata.id} отключен в конфиге", "└")
            return False
        
        module_name = f"plugins.{plugin.metadata.id}.main"
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        if plugin.metadata.dependencies:
            print_tree_item(level, f"🔍 Проверка зависимостей для {plugin.metadata.id}", "├")
            deps_ok, missing_deps = DependencyResolver.check_dependencies(plugin, available_plugins)
            
            if not deps_ok:
                print_tree_item(level, f"❌ Неудовлетворенные зависимости:", "├")
                for dep in missing_deps:
                    print_tree_item(level + 1, f"❌ {dep}", "├")
                print_tree_item(level, f"❌ Пропуск загрузки {plugin.metadata.id}", "└")
                return False
            else:
                print_tree_item(level, f"✅ Все зависимости удовлетворены", "├")
        
        main_script = os.path.join(plugin.directory, "main.py")
        if not os.path.exists(main_script):
            print_tree_item(level, f"⚠️ Плагин {plugin.metadata.id} не имеет main.py", "└")
            return False
        
        content = await asyncio.to_thread(read_file_cached, main_script)
        
        original_globals = globals().copy()
        try:
            with PluginContext(plugin.directory, plugin.metadata.id):
                exec_globals = globals().copy()
                
                exec_globals['plugin_id'] = plugin.metadata.id
                
                exec_globals['plugin_api'] = plugin_api
                exec_globals['plugin_hook'] = plugin_hook
                exec_globals['plugin_command'] = plugin_command
                
                exec_globals['read_plugin_file'] = lambda path: plugin_api.read_plugin_file(path, plugin.metadata.id)
                exec_globals['write_plugin_file'] = lambda path, content: plugin_api.write_plugin_file(path, content, plugin.metadata.id)
                exec_globals['plugin_file_exists'] = lambda path: plugin_api.plugin_file_exists(path, plugin.metadata.id)
                exec_globals['get_plugin_path'] = lambda path: plugin_api.resolve_plugin_path(path, plugin.metadata.id)
                exec_globals['list_plugin_files'] = lambda path=".": plugin_api.list_plugin_files(path, plugin.metadata.id)
                
                exec_globals['set_shared_data'] = lambda key, value: plugin_api.set_shared_data(key, value, plugin.metadata.id)
                exec_globals['get_shared_data'] = plugin_api.get_shared_data
                
                exec_globals['discord'] = discord
                exec_globals['app_commands'] = app_commands
                exec_globals['commands'] = commands
                exec_globals['tasks'] = tasks
                exec_globals['datetime'] = datetime
                
                exec(content, exec_globals)
                
            plugin.loaded = True
            plugin_api.register_plugin(plugin)
            load_stats['success'] += 1
            print_tree_item(level, f"✅ Плагин {plugin.metadata.name} ({plugin.metadata.id}) успешно загружен", "└")
            return True
            
        except Exception as e:
            globals().clear()
            globals().update(original_globals)
            raise
            
    except FileNotFoundError:
        error_msg = f"⚠️ Файл main.py не найден для плагина {plugin.metadata.id}"
    except SyntaxError as e:
        error_msg = f"❌ Синтаксическая ошибка в плагине {plugin.metadata.id}: {str(e)}"
    except Exception as e:
        error_msg = f"❌ Ошибка загрузки плагина {plugin.metadata.id}: {str(e)}"
    
    load_stats['fail'] += 1
    load_stats['errors'].append(error_msg)
    print_tree_item(level, error_msg, "└")
    traceback.print_exc()
    return False

async def load_module_async(module_path, level: int = 0):
    try:
        if module_path in module_cache:
            return True

        dir_name, filename = os.path.split(module_path)
        module_name = filename[:-3]
        
        if hasattr(config, 'DISABLED_MODULES') and module_name in config.DISABLED_MODULES:
            print_tree_item(level, f"⏭️ Модуль {module_name} отключен в конфиге", "└")
            return False
            
        content = await asyncio.to_thread(read_file_cached, module_path)

        original_globals = globals().copy()
        try:
            exec(content, globals())
                
            module_cache[module_path] = True
            load_stats['success'] += 1
            print_tree_item(level, f"✅ Модуль {module_path} успешно загружен", "└")
            return True
        except Exception as e:
            globals().clear()
            globals().update(original_globals)
            raise
            
    except FileNotFoundError:
        error_msg = f"⚠️ Файл {module_path} не найден"
    except SyntaxError as e:
        error_msg = f"❌ Синтаксическая ошибка в {module_path}: {str(e)}"
    except Exception as e:
        error_msg = f"❌ Ошибка загрузки {module_path}: {str(e)}"
    
    load_stats['fail'] += 1
    load_stats['errors'].append(error_msg)
    print_tree_item(level, error_msg, "└")
    traceback.print_exc()
    return False

async def load_all_plugins_and_modules():
    print("🚀 Начинаем загрузку системы...")
    
    load_stats['success'] = 0
    load_stats['fail'] = 0
    load_stats['errors'] = []
    
    print_tree_item(0, "📦 PLUGINS", "├")
    plugins = plugin_api.scan_plugins()
    available_plugins = {plugin.metadata.id: plugin for plugin in plugins}
    
    for plugin in plugins:
        if plugin.metadata.id not in plugin_api.plugins:
            plugin_api.register_plugin(plugin)
    
    loaded_plugins = set()
    max_attempts = len(plugins) * 2
    attempts = 0
    
    while len(loaded_plugins) < len(plugins) and attempts < max_attempts:
        attempts += 1
        made_progress = False
        
        for plugin in plugins:
            if plugin.metadata.id in loaded_plugins:
                continue
            
            if plugin.metadata.dependencies:
                deps_ok, _ = DependencyResolver.check_dependencies(plugin, available_plugins)
                if not deps_ok:
                    continue
            
            success = await load_plugin_async(plugin, 1, available_plugins)
            if success:
                loaded_plugins.add(plugin.metadata.id)
                made_progress = True
        
        if not made_progress:
            break
    
    print_tree_item(0, "🔧 MODULES", "├")
    modules_dir = 'modules'
    
    if os.path.exists(modules_dir):
        for filename in os.listdir(modules_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                module_path = os.path.join(modules_dir, filename)
                await load_module_async(module_path, 1)
    
    print_tree_item(0, "📊 СТАТИСТИКА ЗАГРУЗКИ", "└")
    print_tree_item(1, f"✅ Успешно: {load_stats['success']}", "├")
    print_tree_item(1, f"❌ Ошибок: {load_stats['fail']}", "├")
    
    if load_stats['errors']:
        print_tree_item(1, "📋 Ошибки загрузки:", "├")
        for error in load_stats['errors']:
            print_tree_item(2, f"• {error}", "├")
    
    print_tree_item(1, f"📦 Всего плагинов: {len(plugins)}", "├")
    print_tree_item(1, f"✅ Загружено плагинов: {len(loaded_plugins)}", "└")
    print_tree_item(1, f"❌ Не загружено плагинов: {len(plugins) - len(loaded_plugins)}", "└")
    
    print("🎯 Загрузка завершена!")
    
    return load_stats

async def reload_plugin(plugin_id: str) -> bool:
    plugin = plugin_api.get_plugin(plugin_id)
    if not plugin:
        return False
    
    await unload_plugin(plugin_id)
    
    return await load_single_plugin(plugin_id)

async def unload_plugin(plugin_id: str) -> bool:
    plugin = plugin_api.get_plugin(plugin_id)
    if not plugin:
        return False
    
    plugin_api.unregister_commands(plugin_id)
    
    plugin_api.unregister_tasks(plugin_id)
    
    plugin_api.unregister_hooks(plugin_id)
    
    module_name = f"plugins.{plugin_id}.main"
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    keys_to_remove = []
    for key in globals().copy():
        if hasattr(globals()[key], '_plugin_id') and getattr(globals()[key], '_plugin_id') == plugin_id:
            keys_to_remove.append(key)
        elif isinstance(globals()[key], type) and hasattr(globals()[key], '__module__') and plugin_id in getattr(globals()[key], '__module__', ''):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        if key in globals():
            del globals()[key]
    
    if plugin_id in plugin_api.plugins:
        del plugin_api.plugins[plugin_id]
    
    if plugin_id in plugin_api.plugin_dirs:
        del plugin_api.plugin_dirs[plugin_id]
    
    plugin.loaded = False
    
    return True

async def load_single_plugin(plugin_id: str) -> bool:
    plugins = plugin_api.scan_plugins()
    plugin = next((p for p in plugins if p.metadata.id == plugin_id), None)
    
    if not plugin:
        return False
    
    if plugin_id in sys.modules:
        del sys.modules[plugin_id]
    
    module_cache.clear()
    
    available_plugins = {}
    for p in plugin_api.get_all_plugins():
        if p.metadata.id != plugin_id:
            available_plugins[p.metadata.id] = p
    
    result = await load_plugin_async(plugin, 0, available_plugins)
    
    return result

async def reload_plugin(plugin_id: str) -> bool:
    plugin = plugin_api.get_plugin(plugin_id)
    if not plugin:
        return False
    
    print(f"🔄 Перезагрузка плагина {plugin_id}...")
    
    await unload_plugin(plugin_id)
    
    await asyncio.sleep(0.5)
    
    result = await load_single_plugin(plugin_id)
    
    if result:
        print(f"✅ Плагин {plugin_id} перезагружен")
    else:
        print(f"❌ Не удалось перезагрузить {plugin_id}")
    
    return result

async def reload_all_plugins():
    print("🔄 Перезагрузка всех плагинов...")
    
    loaded_plugins = plugin_api.get_loaded_plugins()
    plugin_ids = [p.metadata.id for p in loaded_plugins]
    
    for plugin_id in plugin_ids:
        await unload_plugin(plugin_id)
    
    module_cache.clear()
    
    await asyncio.sleep(0.5)
    
    await load_all_plugins_and_modules()
    
    print("✅ Перезагрузка завершена!")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        if isinstance(original_error, discord.errors.NotFound) and "Unknown interaction" in str(original_error):
            print(f"⚠️ Interaction истек для команды, но команда выполнена")
            return
        
        print(f"❌ Ошибка в команде: {original_error}")
        traceback.print_exc()
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Произошла ошибка при выполнении команды", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Произошла ошибка при выполнении команды", 
                    ephemeral=True
                )
        except:
            pass
    else:
        print(f"❌ Ошибка команды: {error}")

async def main():
    try:
        await load_all_plugins_and_modules()
        
        async with bot:
            await bot.start(config.TOKEN)
            
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал прерывания")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown_handler()))
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown_handler()))
    
    asyncio.run(main())