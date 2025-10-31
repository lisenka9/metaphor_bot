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

# Настройки ЮMoney
YOOMONEY_CLIENT_ID = os.environ.get("YOOMONEY_CLIENT_ID", "")
YOOMONEY_REDIRECT_URI = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "") + "/payment_callback"
YOOMONEY_SCOPE = "payment-p2p"
YOOMONEY_SECRET = os.environ.get("YOOMONEY_SECRET", "")

# Реквизиты
YOOMONEY_RECEIVER = os.environ.get("YOOMONEY_RECEIVER")

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

print(f"✅ BOT_TOKEN loaded: {BOT_TOKEN[:10]}...") 
