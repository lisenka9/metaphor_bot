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
BASE_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://metaphor-bot.onrender.com')

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")

# PayPal настройки
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")

# Ссылки для оплаты
PAYMENT_LINKS = {
    "month": "https://yookassa.ru/my/i/aQY7xxKX30Fj/l",
    "3months": "https://yookassa.ru/my/i/aQY8WAd6bEpS/l", 
    "6months": "https://yookassa.ru/my/i/aQY8oBNxveyr/l",
    "year": "https://yookassa.ru/my/i/aQY86Y-FkTVZ/l"
}

PAYPAL_LINKS = {
    "month": "https://www.paypal.com/ncp/payment/ELCKRCRLM9AV8",
    "3months": "https://www.paypal.com/ncp/payment/MVWBB6P5ER5KE",
    "6months": "https://www.paypal.com/ncp/payment/TLSQ2ZAGXMHNL", 
    "year": "https://www.paypal.com/ncp/payment/PVLQ7RPTY7XKU"
}

# Цены подписок
SUBSCRIPTION_PRICES = {
    "month": 99,
    "3months": 199,  
    "6months": 399,
    "year": 799
}

PAYPAL_PRICES = {
    "month": 5.00,  # ILS
    "3months": 9.00,  
    "6months": 17.00,
    "year": 35.00
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

PAYPAL_DECK_LINK = "https://www.paypal.com/ncp/payment/4F3G4YC6LSKZN"

DECK_PRICE_RUB = 999.00
DECK_PRICE_ILS = 80.00

DECK_PRODUCT_PAYPAL = {
    "price": DECK_PRICE_ILS,
    "name": "Цифровая колода 'Настроение как море'",
    "payment_link": PAYPAL_DECK_LINK,
    "description": "Полная цифровая версия колоды с методическим пособием"
}

print(f"✅ BOT_TOKEN loaded: {BOT_TOKEN[:10]}...") 
