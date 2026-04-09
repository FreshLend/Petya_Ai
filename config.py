# Настойки Бота
TOKEN = "ТВОЙ_ТОКЕН_БОТА" # Токен бота
ALLOWED_ID = [1136934279348224042] # Доверенные ID
SHUTDOWN_TIME = 5  # Время на завершение работы в секундах
REBOOT_DELAY = 5  # Задержка перед перезапуском в секундах
SERVER_SETTINGS_FILE = "data/server/server_settings.json" # Настройки серверов
USER_SETTINGS_FILE = "data/client/user_settings.json" # Настройки пользователей
USER_INTERACTS_FILE = "data/client/user_interacts.json" # Взаимодействия
JOKES_AND_QUOTES = "data/jokes_and_quotes.json" # Шутки и цитаты
INTERACTABLES = "data/interactables.json" # База гифок для Взаимодействий
LANGUAGES = "data/languages.json" # Языки для перевода NLLB
# Список отключаемых плагинов и модулей (без .py)
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
DEFAULT_SYSTEM_PROMPT = "Ты ИИ по имени Петя. Отвечай вежливо и информативно." # Системный Промпт
MAX_QUEUE_SIZE = 10 # Максимальная очередь
RANDOM_RESPONCE_CHANCE = 0.02 # 2% Шанс ответа без упоминания бота, примерно каждые 50 сообщений.
NO_MENTION_CHANCE = 0.7 # 50% Шанс ответа без упоминания пользователя в сообщении
REPLY_PREFERENCE = 0.7 # 70% Шанс использовать reply
# OpenRouter настройки
OPENROUTER_API_KEY = "ТВОЙ_КЛЮЧ_ОТ_OPENROUTER"  # Получите на https://openrouter.ai/keys
SITE_URL = "https://example.com"  # необязательно
SITE_NAME = "Example"  # необязательно

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
# Шансы ивентов
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