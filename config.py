# Настойки Бота
TOKEN = "ваш_токен_бота" # Токен бота
ALLOWED_ID = [ВАШ_DISCORD_ID] # Доверенные ID
SHUTDOWN_TIME = 5  # Время на завершение работы в секундах
REBOOT_DELAY = 5  # Задержка перед перезапуском в секундах
SERVER_SETTINGS_FILE = "data/server/server_settings.json" # Настройки серверов
USER_SETTINGS_FILE = "data/client/user_settings.json" # Настройки пользователей
USER_INTERACTS_FILE = "data/client/user_interacts.json" # Взаимодействия
JOKES_AND_QUOTES = "data/jokes_and_quotes.json" # Шутки и цитаты
INTERACTABLES = "data/interactables.json" # База гифок для Взаимодействий
# Список отключаемых плагинов и модулей
DISABLED_PLUGINS = [""] # DISABLED_PLUGINS = ["ai_learning_algorithm"]
DISABLED_MODULES = [""] # DISABLED_MODULES = ["entertainment"]

# Настройка FeedBack
FEEDBACK_ACTIONS_FILE = "data/server/feedback_actions.json" # Хранение состояний кнопок обратной связи
FEEDBACK_FORUM_ID = 1384637991091441767 # ID Форума
TAG_PROBLEMA = 1384638708958892032 # ID Тега "проблема"
TAG_OTZYV = 1384638735492059306 # ID Тега "отзыв"
TAG_IDEA = 1384638777049350265 # ID Тега "идея"
TAG_DRUGOE = 1384640464472244284 # ID Тега "другое"

# Настройка искусственного интеллекта
MODELS_FILE = "data/models.json" # Модели
USER_CONTEXT_FILE = "data/client/user_contexts.json" # Контекст
CHARACTER_FILE = "data/characters.json" # Персонажи
TAGS_INSTRUCTION = """
<|USER_ID|> если хочешь явно упомянуть пользователя в тексте
<|REPLY|> если хочешь ответить как reply на сообщение (автоупоминание)
<|REPLY|> и <|USER_ID|> могут быть использованы оба
Если пользователь обратился по имени или упомянул тебя — ты можешь выбрать <|REPLY|> или <|USER_ID|> как считаешь нужным.
"""
MAX_QUEUE_SIZE = 10 # Максимальная очередь для локальных моделей
RANDOM_RESPONCE_CHANCE = 0.02 # 2% Шанс ответа без упоминания бота, примерно каждые 50 сообщений.
LANGUAGES = "data/languages.json" # Языки для перевода NLLB
# Настройки спам фильтра
TIMEOUT = 10
MIN_TEXT_LENGTH = 3
DUPLICATE_LIMIT = 3
DUPLICATE_WINDOW = 60
RATE_LIMIT_WINDOW = 2
RATE_LIMIT_MAX = 3
WORDS_PATTERNS = [
    r'(?i)\b(продолжим|продолжай|продолжение|продолжить)\b',
    
    r'(?i)(напиши|скинь|дай|покажи|объясни|помоги)\s*(код|аллокатор|gpu|vm|memory|cuda|пример|решение|функцию|класс)',

    r'<:[a-zA-Z0-9_]+:[0-9]+>',

    r'<@!?[0-9]+>',

    r'<#[0-9]+>',

    r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+',
]

# Настройка Экономики
XP_MULTIPLIER = 1.3 # Множитель для след.опыта
USER_GROUPS = ["пользователь", "покупатель", "тестер", "разработчик"] # Группы
PROFILES_FILE = "data/client/profiles.json" # Профили пользователей
BANK_DATA_FILE = "data/client/banks.json" # Банки
TREASURE_DATA_FILE = "data/treasure.json" # Поиск сокровищ локации и предметы
CASINO_SETTINGS = "data/casino_settings.json" # Настройка казино
INVENTORY = "data/client/inventory.json" # Инветарь
SHOP_FILE = "data/shop.json" # Магазин
PROFESSIONS = "data/professions.json" # Профессии
BLACK_MARKET_PASS = {"gold_coin": 20} # Цена пропуска на чёрный рынок
ENERGY_RESTORE = 5 # Количество восстановленной энергии
ENERGY_RESTORE_INTERVAL = 5 * 60 # Время восстановления
# Шансы ивентов поиска
TREASURE_EVENT_CHANCES = {
    "positive": 20, # 20% Шанс положительного события
    "negative": 10, # 10% Шанс отрицательного события
    "neutral": 70 # 70% Шанс нейтрального события
}
# Шансы ивентов работы
EVENT_CHANCES = {
    "positive": 20, # 20% Шанс положительного события
    "negative": 15, # 15% Шанс отрицательного события
    "neutral": 65 # 65% Шанс нейтрального события
}
# Эмодзи валют
CURRENCY_EMOJIS = {
    "copper_coin": "<:copper_coin:1387557036912541848>", # Медные монеты
    "silver_coin": "<:silver_coin:1387557073105195138>", # Серебрянные монеты
    "gold_coin": "<:gold_coin:1387557111046602802>", # Золотые монеты
    "platinum_coin": "<:platinum_coin:1387557130848178347>", # Платиновые монеты
    "freshcoin": "<:freshcoin:1387561918633476156>" # Донатная валюта FreshCoin
}
