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

print(f"✅ BOT_TOKEN loaded: {BOT_TOKEN[:10]}...") 
