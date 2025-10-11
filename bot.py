import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
import handlers
from database import db
# Добавьте в bot.py перед application.run_polling()
from flask import Flask
from threading import Thread
import psycopg2
import os

# Создаем Flask приложение для миграции
migration_app = Flask('')

@migration_app.route('/migrate')
def migrate_data():
    try:
        # Ваш код миграции здесь
        railway_url = os.environ.get('RAILWAY_DB_URL')
        render_url = os.environ.get('DATABASE_URL')
        
        if not railway_url or not render_url:
            return "❌ Переменные окружения не настроены"
        
        # Подключаемся к базам
        old_conn = psycopg2.connect(railway_url)
        old_cursor = old_conn.cursor()
        new_conn = psycopg2.connect(render_url)
        new_cursor = new_conn.cursor()
        
        # Мигрируем пользователей
        old_cursor.execute('SELECT * FROM users')
        users = old_cursor.fetchall()
        user_count = len(users)
        
        for user in users:
            new_cursor.execute('''
                INSERT INTO users 
                (user_id, username, first_name, last_name, registered_date, daily_cards_limit, last_daily_card_date, is_premium)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            ''', user)
        
        # Мигрируем историю карт
        old_cursor.execute('SELECT * FROM user_cards')
        user_cards = old_cursor.fetchall()
        card_count = len(user_cards)
        
        for card in user_cards:
            new_cursor.execute('''
                INSERT INTO user_cards (id, user_id, card_id, drawn_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            ''', card)
        
        new_conn.commit()
        
        return f"""
        ✅ Миграция завершена успешно!
        👤 Пользователей перенесено: {user_count}
        🎴 Записей карт перенесено: {card_count}
        """
        
    except Exception as e:
        return f"❌ Ошибка миграции: {str(e)}"

def run_migration_server():
    migration_app.run(host='0.0.0.0', port=5000)

# Запускаем сервер миграции в отдельном потоке
migration_thread = Thread(target=run_migration_server)
migration_thread.daemon = True
migration_thread.start()

print("🚀 Сервер миграции запущен на порту 5000")

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
    
    # Обработчик для любых других сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                         handlers.help_command))
    
    # Запускаем бота
    logger.info("Бот запущен на Railway...")
    application.run_polling()

if __name__ == '__main__':
    main()
