# 🤖 Petya_Ai — Умный Discord бот с экономикой

[![Join Discord](https://img.shields.io/badge/Join-Discord-5865F2)](https://discord.com/invite/95EyHeZmMz)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Discord.py](https://img.shields.io/badge/discord.py-2.7%2B-blue)
![License](https://img.shields.io/badge/license-GPLv3-red)

**Petya_Ai** — многофункциональный Discord-бот с открытым исходным кодом.  
Сочетает **гибкую систему плагинов**, **полноценную экономическую RPG**, **модуль искусственного интеллекта** (локальные LLM, OpenAi совместимый), **математический движок** (символьные вычисления, производные, интегралы, пределы), **переводчик NLLB** и множество утилит.

---

## ✨ Основные возможности

### 🤖 Искусственный интеллект
- **Режимы работы**: 
  - Онлайн через OpenAi API совместимость
  - Локально через GGUF-модели (llama-cpp-python)
- Контекстный диалог с рабочей памятью

### 💰 Экономическая система
- Четыре валюты (медные, серебряные, золотые, платиновые монеты) + FreshCoin
- Банковская система с комиссиями
- Магазин и чёрный рынок
- Система уровней и опыта (XP)
- Профессии с работой и случайными событиями
- Инвентарь с предметами (металлоискатели, баффы, наборы)
- Казино (слоты, напёрстки, блэкджек)
- Поиск сокровищ в локациях

### 🔌 Система плагинов
- Полноценная архитектура плагинов с метаданными
- Поддержка зависимостей между плагинами
- Хуки на события Discord (`on_ready`, `on_message` и др.)
- Регистрация slash-команд и фоновых задач
- **📚 [Документация по созданию плагинов](DOCUMENTATION.md)**

### 🛠 Инструменты и утилиты
- **Шифрование**: 12+ шифров (Цезарь, Виженер, XOR, Base64, Морзе, хэши MD5/SHA)
- **Математика**: Калькулятор, символьные вычисления (sympy), работа с комплексными числами
- **Информация о серверах**: детальная структура каналов
- **Автоматическая смена аватара** по сезонам и событиям

### 🎉 Развлечения
- Взаимодействия (приветствия, поцелуи, выстрелы) с гифками из аниме
- Шутки, цитаты, магический шар
- Генерация случайных чисел

---

## 📦 Установка

### Требования
- Python 3.10+
- Discord Bot Token ([получить тут](https://discord.com/developers/applications))

### Быстрая установка (Windows/Linux)

**Windows (run.bat)**:
```batch
run.bat
# Выберите 1 - полная установка
```

**Linux (run.sh)**:
```bash
chmod +x run.sh
./run.sh
# Выберите 1 - полная установка
```

### Ручная установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/FreshLend/Petya_Ai.git
cd Petya_Ai
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте `config.py`:
```python
TOKEN = "ваш_токен_бота"
ALLOWED_ID = [ВАШ_DISCORD_ID]  # для админ-команд
```

5. Настройте модели в `data/models.json`:
```json
{
  "my_online_model": {
    "type": "online",
    "base_url": "https://example.com/api/v1/",
    "token": "sk-or-v1",
    "link": "model/link",
    "vision": true,
    "default_temperature": 0.7,
    "context_length": 16384,
    "max_tokens": 8192
  },
  "my_local_model": {
    "type": "offline",
    "path": "data/models/model.gguf",
    "default_temperature": 0.7,
    "context_length": 2048,
    "max_tokens": 1024,
    "n_gpu_layers": -1
  }
}
```

6. Запустите бота:
```bash
python main.py
```

---

## 🧩 Структура проекта

```
Petya_Ai/
├── main.py                 # Главный файл (система плагинов, события, загрузка)
├── config.py               # Конфигурация (токен, пути, настройки)
├── modules/                # Загружаемые модули (ai, economy, tools, entertainment)
│   ├── ai/                     # ИИ, перевод
│   ├── economy/                # Экономика, банки, магазин
│   ├── tools/                  # Инструменты, шифрование, математика
│   └── entertainment/          # Взаимодействия, шутки, цитаты
├── plugins/                # Плагины (расширения)
├── data/                   # Данные (профили, магазин, контексты)
│   ├── avatars/                # Аватары по сезонам
│   ├── client/                 # Профили, инвентарь, контексты
│   ├── server/                 # Настройки серверов, обратная связь
│   └── ...                     # models.json, shop.json, treasure.json и др.
├── run.bat                 # Запуск на Windows
└── run.sh                  # Запуск на Linux
```

---

## 🎮 Команды бота

### 🤖 Искусственный Интеллект
| Команда | Описание |
|---------|----------|
| `/query ask <question> [image] [is_private]` | Задать вопрос ИИ (можно с картинкой) |
| `/query define <term> [is_private]` | Получить определение термина |
| `/parameter <action> <parameter> [value]` | Управление параметрами: `action` = get/set/reset; `parameter` = system_prompt, context, all |
| `/model <action> [model]` | Информация о модели (`info`) или смена модели (`set`) |
| `/status <action> [limit]` | История диалога (`history`) или состояние очереди (`queue`) |
| `/summarize <text>` | Краткое содержание текста |
| `/translate <text> <to_lang> [from_lang]` | Перевод текста (NLLB) |
| `/char <character>` | Сменить персонажа |

### 🎪 Развлечения
| Команда | Описание |
|---------|----------|
| `/8ball <question>` | Магический шар |
| `/interact_hi [target]` | Поприветствовать (если target не указан – всех) |
| `/interact_bye [target]` | Попрощаться (если target не указан – всех) |
| `/interact_kiss <target> [cheeks]` | Поцеловать (с опцией в щёчку) |
| `/interact_bang <target>` | Выстрелить в пользователя |
| `/joke` | Случайная шутка |
| `/quote` | Случайная цитата |
| `/roll [max_number]` | Случайное число (по умолчанию 100) |

### 💰 Экономика
| Команда | Описание |
|---------|----------|
| `/profile [user] [create]` | Просмотр/создание профиля |
| `/work [profession_list]` | Работать (с опцией показа списка профессий) |
| `/set_group <user> <group>` | Установить группу (разработчик, тестер, покупатель, пользователь) |
| `/exchange <from> <to> <amount>` | Конвертация валют (курс 100:1) |
| `/transfer <amount> <currency> <user>` | Перевести деньги (медные, серебряные, золотые, платиновые) |
| `/bank [action]` | Управление банком (create, list, rename, set_comission, set_service, info) |
| `/deposit <amount> <currency>` | Внести на счёт |
| `/withdraw <amount> <currency>` | Снять со счёта |
| `/set_bank <name>` | Выбрать активный банк |
| `/shop [black_store]` | Магазин / чёрный рынок (если есть пропуск) |
| `/inventory` | Инвентарь |
| `/treasure` | Поиск сокровищ в локациях |
| `/casino <action> [amount] [choice]` | Казино (меню, купить, продать, слоты, наперстки, блэкджек) |
| `/leaderboard <type> [page]` | Топ игроков (уровень / богатство) |

### 🛠 Инструменты
| Команда | Описание |
|---------|----------|
| `/avatar [user]` | Аватар пользователя |
| `/bot_channel <action> [channel]` | Ограничить канал работы бота (set_channel, reset_channel, show_channel) |
| `/calc <expression> [precision]` | Калькулятор (обычные вычисления) |
| `/cipher <action> <cipher_type> <text> [key] [shift]` | Шифрование/дешифрование (Цезарь, Атбаш, ROT13, Виженер, Base64, Морзе, HEX, Бинарный, XOR, Аффинный, хэши MD5/SHA-1/SHA-256/SHA-512) |
| `/emoji <action> <emoji> [format]` | Работа с эмодзи (send, info) |
| `/emoji_list [server_id]` | Список эмодзи сервера |
| `/feedback` | Отправить отзыв / проблему / идею |
| `/health` | Проверить работоспособность всех модулей |
| `/help <category>` | Справка по категориям (ai, fun, economy, tools) |
| `/info [short_info]` | Информация о боте |
| `/invite` | Ссылка-приглашение |
| `/math <expression> [mode] [variable] [steps] [precision]` | Символьные вычисления (упрощение, решение, дифференцирование, интегрирование, пределы, ряды, комплексные числа) |
| `/ping` | Задержка бота |
| `/plugins <action> [plugin_id]` | Управление плагинами (list, info, reload, reload_all, files, load, unload) |
| `/reboot` | Перезагрузить бота |
| `/say [text]` | Отправить сообщение от имени бота (без текста – модальное окно) |
| `/servers` | Информация о серверах бота |
| `/shutdown` | Выключить бота |

---

## 🔧 Управление плагинами

```bash
/plugins list          # Список всех плагинов
/plugins load <id>     # Загрузить плагин
/plugins unload <id>   # Выгрузить плагин
/plugins reload <id>   # Перезагрузить плагин
/plugins reload_all    # Перезагрузить всё
/plugins info <id>     # Информация о плагине
/plugins files <id>    # Список файлов плагина
```

---

## 📞 Контакты

- **Разработчик**: FreshLend Studio (FreshGame)
- **Email**: freshlend.studio@gmail.com
- **Сайт**: [https://freshlend.github.io](https://freshlend.github.io)
- **Discord сервер**: [Присоединиться](https://discord.com/invite/95EyHeZmMz)

---

## ⭐ История версий

**Текущая версия: 2.9.0**
- Система плагинов и модулей
- Искусственный Интеллект
- Экономическая RPG
- Переводчик NLLB-200
- 47 slash-команд

---

## 📜 Лицензия

**GNU General Public License v3.0 [GPLv3](LICENSE)**.  

---

*Разработано с помощью бочек кофе и 3 года без сна для Discord сообщества*