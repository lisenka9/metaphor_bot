import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN
import handlers
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    # Инициализируем базу данных
    logger.info("Инициализация базы данных...")
    db.init_database()
    db.update_existing_users_limits()
    
    # Проверяем, есть ли карты в базе
    if not db.check_cards_exist():
        logger.warning("В базе данных нет карт!")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("daily", handlers.daily_card))
    application.add_handler(CommandHandler("profile", handlers.profile))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("resetme", handlers.reset_my_limit))
    application.add_handler(CommandHandler("debug", handlers.debug_db))
    application.add_handler(CallbackQueryHandler(handlers.button_handler))
    
    # Обработчик для любых других сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                         handlers.help_command))
    
    # Запускаем бота
    logger.info("Бот запущен на Railway...")
    application.run_polling()

if __name__ == '__main__':
    main()
