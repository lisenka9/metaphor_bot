import os

# Токен бота из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")
# ID администратора
ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "").split(",") if id.strip()]

# Лимиты карт
DAILY_CARD_LIMIT_FREE = 1
DAILY_CARD_LIMIT_PREMIUM = 5

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")

# Ссылки для оплаты
PAYMENT_LINKS = {
    "month": "https://yookassa.ru/my/i/aQY7xxKX30Fj/l",
    "3months": "https://yookassa.ru/my/i/aQY8WAd6bEpS/l", 
    "6months": "https://yookassa.ru/my/i/aQY8oBNxveyr/l",
    "year": "https://yookassa.ru/my/i/aQY86Y-FkTVZ/l"
}

# Цены подписок
SUBSCRIPTION_PRICES = {
    "month": 99,
    "3months": 199,  
    "6months": 399,
    "year": 799
}

SUBSCRIPTION_DURATIONS = {
    "month": 30,
    "3months": 90, 
    "6months": 180,
    "year": 365
}

SUBSCRIPTION_NAMES = {
    "month": "1 месяц",
    "3months": "3 месяца", 
    "6months": "6 месяцев",
    "year": "1 год"
}

DECK_PRODUCT = {
    "price": 999.00,
    "name": "Цифровая колода 'Настроение как море'",
    "payment_link": "https://yookassa.ru/my/i/aRn2fkgcOd2v/l",
    "description": "Полная цифровая версия колоды с методическим пособием"
}

print(f"✅ BOT_TOKEN loaded: {BOT_TOKEN[:10]}...") 
