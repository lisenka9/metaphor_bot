import os

# Токен бота из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")
# ID администратора
ADMIN_IDS = [891422895]

# Лимиты карт
DAILY_CARD_LIMIT_FREE = 1
DAILY_CARD_LIMIT_PREMIUM = 5

print(f"✅ BOT_TOKEN loaded: {BOT_TOKEN[:10]}...") 
