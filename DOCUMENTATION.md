# Документация системы плагинов

## Обзор

Система плагинов предоставляет возможность расширять функциональность бота без изменения основного кода.

## Структура плагина

Каждый плагин должен быть расположен в отдельной папке внутри директории `plugins/`. Минимальная структура:

```
plugins/
└── my_plugin/
    ├── metadata.json      # Метаданные плагина (обязательно)
    └── main.py            # Главный скрипт плагина (обязательно)
```

### metadata.json

Файл с описанием плагина:

```json
{
    "id": "my_plugin",
    "name": "Мой Плагин",
    "description": "Описание функциональности",
    "author": "Ваше имя",
    "version": "1.0.0",
    "dependencies": ["other_plugin>=1.0.0"]
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `id` | string | ✅ | Уникальный идентификатор плагина |
| `name` | string | ✅ | Отображаемое имя |
| `description` | string | ❌ | Описание функциональности |
| `author` | string | ❌ | Автор плагина |
| `version` | string | ❌ | Версия (semver) |
| `dependencies` | array | ❌ | Список зависимостей |

### Формат зависимостей

```
plugin_id           # любая версия
plugin_id>=1.0.0    # версия 1.0.0 или выше
plugin_id==1.0.0    # точная версия
plugin_id~=1.0.0    # совместимая версия (1.x.x)
```

## API для разработки плагинов

### Глобальные объекты в main.py

| Объект | Описание |
|--------|----------|
| `plugin_id` | ID текущего плагина |
| `plugin_api` | Экземпляр API для взаимодействия с ботом |
| `plugin_hook` | Декоратор для регистрации хуков |
| `plugin_command` | Декоратор для регистрации slash-команд |

### Декораторы

#### @plugin_command

Регистрирует slash-команду.

```python
@plugin_command(name="ping", description="Проверка работоспособности")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")
```

**Параметры:**
- `name` (str) - имя команды (по умолчанию имя функции)
- `description` (str) - описание команды

#### @plugin_hook

Регистрирует обработчик событий.

```python
@plugin_hook("on_ready")
async def on_plugin_ready():
    print(f"Плагин {plugin_id} загружен!")

@plugin_hook("on_message")
async def on_plugin_message(message: discord.Message):
    if "hello" in message.content.lower():
        await message.channel.send("Hello from plugin!")
```

**Доступные хуки:**

| Хук | Параметры | Описание |
|-----|-----------|----------|
| `on_ready` | - | Бот готов к работе |
| `on_message` | `message` | Новое сообщение |
| `on_voice_state_update` | `member, before, after` | Изменение голосового статуса |
| `on_member_join` | `member` | Новый участник |
| `on_member_remove` | `member` | Участник покинул сервер |
| `on_reaction_add` | `reaction, user` | Добавлена реакция |
| `on_reaction_remove` | `reaction, user` | Удалена реакция |
| `before_command` | `interaction` | Перед выполнением команды |
| `after_command` | `interaction` | После выполнения команды |

### Функции для работы с файлами

Все пути относительные относительно директории плагина.

```python
# Чтение файла
content = read_plugin_file("data/config.json")

# Запись файла
write_plugin_file("data/config.json", '{"key": "value"}')

# Проверка существования
if plugin_file_exists("data/config.json"):
    # ...

# Получение абсолютного пути
path = get_plugin_path("data/file.txt")

# Список файлов в директории
files = list_plugin_files("data/")
```

### Работа с общими данными

Обмен данными между плагинами.

```python
# Установить общие данные
set_shared_data("my_key", {"value": 123})

# Получить общие данные
data = get_shared_data("my_key", default={})
```

### Фоновые задачи

Используйте `tasks.loop` из `discord.ext`:

```python
from discord.ext import tasks

@tasks.loop(minutes=5)
async def my_periodic_task():
    print("Task running...")

# Запуск задачи
my_periodic_task.start()
```

### Получение бота и конфигурации

```python
bot = plugin_api.get_bot()
config = plugin_api.get_config()

# Пример использования
guild = bot.get_guild(config.MAIN_GUILD_ID)
```

## Управление плагинами (команды бота)

| Команда | Описание |
|---------|----------|
| `/plugins list` | Список всех плагинов |
| `/plugins info <id>` | Информация о плагине |
| `/plugins files <id>` | Список файлов плагина |
| `/plugins load <id>` | Загрузить плагин |
| `/plugins unload <id>` | Выгрузить плагин |
| `/plugins reload <id>` | Перезагрузить плагин |
| `/plugins reload_all` | Перезагрузить все плагины |

## Пример полного плагина

**plugins/example_plugin/metadata.json**
```json
{
    "id": "example_plugin",
    "name": "Example Plugin",
    "description": "Пример плагина",
    "author": "Bot Developer",
    "version": "1.0.0"
}
```

**plugins/example_plugin/main.py**
```python
import discord
from discord.ext import tasks

@plugin_hook("on_ready")
async def on_ready():
    print(f"✅ Example plugin {plugin_id} is ready!")
    start_cleanup_task.start()

@plugin_command(name="echo", description="Повторяет сообщение")
async def echo_command(
    interaction: discord.Interaction, 
    message: str
):
    await interaction.response.send_message(f"🔊 {message}")

@tasks.loop(hours=24)
async def start_cleanup_task():
    # Очистка временных файлов каждые 24 часа
    if plugin_file_exists("temp/"):
        import shutil
        shutil.rmtree(get_plugin_path("temp/"))
        write_plugin_file("temp/.gitkeep", "")

# Инициализация при загрузке плагина
set_shared_data("example_plugin_loaded", True)
print(f"Plugin {plugin_id} loading...")
```

## Отладка

При загрузке плагинов в консоль выводится детальная информация:

```
📁 Найден плагин: Example Plugin (example_plugin) - ❌ Не загружен
├ 🔍 Проверка зависимостей для example_plugin
├ ✅ Все зависимости удовлетворены
└ ✅ Плагин Example Plugin (example_plugin) успешно загружен
```

## Ограничения безопасности

1. Команды плагинов автоматически удаляются при выгрузке
2. Фоновые задачи отменяются при выгрузке
3. Хуки удаляются при выгрузке

## Примечания

- Плагины загружаются асинхронно с разрешением зависимостей
- Для отключения плагина добавьте его ID в `config.DISABLED_PLUGINS`
- При синтаксических ошибках плагин не загрузится, но бот продолжит работу