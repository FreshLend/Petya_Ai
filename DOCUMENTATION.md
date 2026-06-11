# Документация системы плагинов и модулей

## Обзор

Система плагинов предоставляет возможность расширять функциональность бота без изменения основного кода.  
Плагины обладают **изоляцией**, поддержкой **зависимостей** и **собственным API**.  
Дополнительно существует система **модулей** (папка `modules/`), которые загружаются как обычный Python‑код и **не** имеют изоляции – они предназначены для встроенных функций бота (AI, экономика, инструменты).

---

## 🧩 Структура плагина

Каждый плагин должен быть расположен в отдельной папке внутри `plugins/`. Минимальная структура:

```
plugins/
└── my_plugin/
    ├── metadata.json      # Метаданные плагина (обязательно)
    └── main.py            # Главный скрипт плагина (обязательно)
```

### metadata.json

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
| `dependencies` | array | ❌ | Список зависимостей (см. формат) |

**Формат зависимостей:**  
`plugin_id` — любая версия  
`plugin_id>=1.0.0` — версия 1.0.0 или выше  
`plugin_id==1.0.0` — точная версия  
`plugin_id~=1.0.0` — совместимая версия (1.x.x)

---

## 🧠 API для разработки плагинов

### Глобальные объекты в `main.py` плагина

| Объект | Описание |
|--------|----------|
| `plugin_id` | ID текущего плагина |
| `plugin_api` | Экземпляр API для взаимодействия с ботом |
| `plugin_hook` | Декоратор для регистрации хуков |
| `plugin_command` | Декоратор для регистрации slash-команд |
| `read_plugin_file` | Функция чтения файла из директории плагина |
| `write_plugin_file` | Функция записи файла |
| `plugin_file_exists` | Проверка существования файла |
| `get_plugin_path` | Получить абсолютный путь внутри плагина |
| `list_plugin_files` | Список файлов в директории |
| `set_shared_data` | Установить общие данные (доступны другим плагинам) |
| `get_shared_data` | Получить общие данные |

### Декораторы

#### @plugin_command
Регистрирует slash-команду.

```python
@plugin_command(name="ping", description="Проверка работоспособности")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")
```

#### @plugin_hook
Регистрирует обработчик событий Discord.

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

Все пути **относительные** относительно директории плагина.

```python
# Чтение файла
content = read_plugin_file("data/config.json")

# Запись файла
write_plugin_file("data/config.json", '{"key": "value"}')

# Проверка существования
if plugin_file_exists("data/config.json"):
    ...

# Получение абсолютного пути
path = get_plugin_path("data/file.txt")

# Список файлов в директории
files = list_plugin_files("data/")
```

### Работа с общими данными (между плагинами)

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

my_periodic_task.start()
```

### Получение бота и конфигурации

```python
bot = plugin_api.get_bot()
config = plugin_api.get_config()
```

---

## 📦 Модули (папка `modules/`)

Модули загружаются **автоматически** при запуске бота из папки `modules/`.  
Каждый модуль — это обычный Python‑скрипт (или папка с `*.py`), который выполняется в глобальном пространстве имён бота.  
Модули **не имеют** изоляции, зависимостей и собственного API — они могут напрямую обращаться к `bot`, `config`, регистрировать команды через `@bot.tree.command()` и т.д.

**Отключение модуля:** добавьте его имя в `DISABLED_MODULES = ["имя_модуля"]` в `config.py`.  
Пример структуры модуля:
```
modules/
└── my_module/
    ├── __init__.py   # (опционально)
    └── main.py
```

---

## 🛠 Управление плагинами (команды бота)

| Команда | Описание |
|---------|----------|
| `/plugins list` | Список всех плагинов |
| `/plugins info <id>` | Информация о плагине |
| `/plugins files <id>` | Список файлов плагина |
| `/plugins load <id>` | Загрузить плагин |
| `/plugins unload <id>` | Выгрузить плагин |
| `/plugins reload <id>` | Перезагрузить плагин |
| `/plugins reload_all` | Перезагрузить все плагины |

> ⚠️ Команды `load`, `unload`, `reload`, `reload_all` доступны только владельцам бота (`config.ALLOWED_ID`).

---

## 📝 Пример полного плагина

**`plugins/example_plugin/metadata.json`**
```json
{
    "id": "example_plugin",
    "name": "Example Plugin",
    "description": "Пример плагина",
    "author": "Bot Developer",
    "version": "1.0.0"
}
```

**`plugins/example_plugin/main.py`**
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
    if plugin_file_exists("temp/"):
        import shutil
        shutil.rmtree(get_plugin_path("temp/"))
        write_plugin_file("temp/.gitkeep", "")

set_shared_data("example_plugin_loaded", True)
print(f"Plugin {plugin_id} loading...")
```

---

## 🔧 Отладка

При загрузке плагинов в консоль выводится детальная информация:

```
📁 Найден плагин: Example Plugin (example_plugin) - ❌ Не загружен
├ 🔍 Проверка зависимостей для example_plugin
├ ✅ Все зависимости удовлетворены
└ ✅ Плагин Example Plugin (example_plugin) успешно загружен
```

---

## ⚠️ Ограничения безопасности

1. Команды плагинов автоматически удаляются при выгрузке.
2. Фоновые задачи отменяются при выгрузке.
3. Хуки удаляются при выгрузке.
4. Доступ к файловой системе ограничен директорией плагина (функции `read_plugin_file`, `write_plugin_file` и др.).

---

## 📌 Примечания

- Плагины загружаются асинхронно с разрешением зависимостей.
- Для отключения плагина добавьте его ID в `config.DISABLED_PLUGINS`.
- При синтаксических ошибках плагин не загрузится, но бот продолжит работу.
- Модули из `modules/` загружаются после плагинов.