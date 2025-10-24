import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import BOT_TOKEN
import handlers
from database import db
import threading
import requests
import time
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health_check():
    return "OK", 200

def keep_alive():
    """Пинг самого себя каждые 10 минут"""
    while True:
        try:
            # URL вашего сервиса Render
            url = "https://metaphor-bot-zdpb.onrender.com"
            requests.get(url, timeout=10)
            print(f"🔄 Self-ping at {time.strftime('%H:%M:%S')}")
        except:
            print("❌ Ping failed")
        time.sleep(600)  # 10 минут

# Запускаем в отдельном потоке при старте
def start_keep_alive():
    thread = threading.Thread(target=keep_alive)
    thread.daemon = True
    thread.start()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    # Запускаем самопинг
    start_keep_alive()

    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    # Инициализируем базу данных
    logger.info("Инициализация базы данных...")
    db.init_database()
    db.update_existing_users_limits()
    
    if not db.check_cards_exist():
        logger.warning("В базе данных нет карт!")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_error_handler(error_handler)
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("daily", handlers.daily_card))
    application.add_handler(CommandHandler("profile", handlers.profile))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("resetme", handlers.reset_my_limit))
    application.add_handler(CommandHandler("debug", handlers.debug_db))
    application.add_handler(CommandHandler("history", handlers.history_command))
    application.add_handler(CommandHandler("stats", handlers.admin_stats))
    application.add_handler(CommandHandler("users", handlers.admin_users))
    application.add_handler(CommandHandler("export", handlers.export_data))
    application.add_handler(CommandHandler("addcards", handlers.add_cards))
    application.add_handler(CommandHandler("consult", handlers.consult_command))
    application.add_handler(CommandHandler("consult_requests", handlers.admin_consult_requests))
    application.add_handler(CallbackQueryHandler(handlers.button_handler))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                     handlers.handle_consult_form))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                         handlers.help_command))
    
    # Webhook режим для Render
    RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    
    if RENDER_EXTERNAL_HOSTNAME:
        logger.info("Запуск в режиме Webhook...")
         
        port = int(os.environ.get("PORT", 10000))
        webhook_url = f'https://{RENDER_EXTERNAL_HOSTNAME}/{BOT_TOKEN}'
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url
        )
    else:
        logger.info("Запуск в режиме Polling...")
        application.run_polling()

if __name__ == '__main__':
    main()
