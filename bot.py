import logging
import os
import time
import requests
import threading
from flask import Flask, request, jsonify
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import BOT_TOKEN
import handlers
from database import db
from yookassa_payment import payment_processor  
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем Flask приложение
app = Flask(__name__)

@app.route('/')
def home():
    return "🌊 Metaphor Bot is running!"

@app.route('/health')
def health_check():
    return "✅ Bot is alive!", 200

@app.route('/payment_callback', methods=['POST'])
def payment_callback():
    """Обрабатывает уведомления от ЮKassa"""
    try:
        # Получаем JSON данные
        event_json = request.get_json()
        logger.info(f"📨 Received YooKassa webhook: {event_json}")
        
        if not event_json:
            logger.error("❌ Empty webhook data received")
            return jsonify({"status": "error", "message": "No data received"}), 400
        
        # Проверяем тип события
        event_type = event_json.get('type')
        if event_type == 'notification':
            # Обрабатываем уведомление о платеже
            return handle_payment_notification(event_json)
        elif event_type == 'payment.waiting_for_capture':
            # Платеж ожидает подтверждения
            logger.info("⏳ Payment waiting for capture")
            return jsonify({"status": "success"}), 200
        else:
            logger.warning(f"⚠️ Unknown event type: {event_type}")
            return jsonify({"status": "success"}), 200
            
    except Exception as e:
        logger.error(f"❌ Error in payment callback: {e}")
        return jsonify({"status": "error"}), 500

def handle_payment_notification(event_data):
    """Обрабатывает уведомление о платеже"""
    try:
        payment_object = event_data.get('object', {})
        payment_status = payment_object.get('status')
        payment_id = payment_object.get('id')
        metadata = payment_object.get('metadata', {})
        amount_value = payment_object.get('amount', {}).get('value')
        
        logger.info(f"🔔 Payment notification: status={payment_status}, payment_id={payment_id}, amount={amount_value}")
        
        user_id = metadata.get('user_id')
        
        # ✅ ЕСЛИ user_id НЕТ, ИЩЕМ ПОЛЬЗОВАТЕЛЯ ПО РАЗНЫМ СПОСОБАМ
        if not user_id:
            user_id = find_user_by_payment_data(payment_object)
        
        if user_id:
            subscription_type = determine_subscription_type(amount_value)
            
            if payment_status == 'succeeded':
                user_id = int(user_id)
                logger.info(f"✅ Payment succeeded for user {user_id}, type: {subscription_type}")
                
                success = activate_subscription_from_webhook(user_id, subscription_type, payment_id, payment_id)
                
                if success:
                    logger.info(f"🎉 Subscription activated for user {user_id}")
                    
                    import asyncio
                    asyncio.create_task(send_payment_success_notification(user_id, subscription_type, amount_value))
                    
                return jsonify({"status": "success"}), 200
                
            elif payment_status in ['canceled', 'failed']:
                logger.info(f"❌ Payment failed for user {user_id}")
                return jsonify({"status": "success"}), 200
            else:
                logger.info(f"⏳ Payment still processing for user {user_id}: {payment_status}")
                return jsonify({"status": "success"}), 200
        else:
            # ✅ СОХРАНЯЕМ ДЛЯ РУЧНОЙ ОБРАБОТКИ И ЛОГИРУЕМ
            logger.warning(f"⚠️ Cannot identify user for payment {payment_id}")
            save_unknown_payment_for_review(payment_object)
            return jsonify({"status": "success"}), 200
            
    except Exception as e:
        logger.error(f"❌ Error handling payment notification: {e}")
        return jsonify({"status": "error"}), 500

def find_user_by_payment_data(payment_object):
    """Ищет пользователя по различным данным из платежа"""
    try:
        metadata = payment_object.get('metadata', {})
        amount_value = payment_object.get('amount', {}).get('value')
        
        # ✅ СПОСОБ 1: По email
        customer_email = metadata.get('custEmail')
        if customer_email:
            user_id = find_user_by_email(customer_email)
            if user_id:
                logger.info(f"✅ Found user {user_id} by email: {customer_email}")
                return user_id
        
        # ✅ СПОСОБ 2: По номеру телефона (если есть в metadata)
        customer_phone = metadata.get('phone') or metadata.get('custPhone')
        if customer_phone:
            user_id = find_user_by_phone(customer_phone)
            if user_id:
                logger.info(f"✅ Found user {user_id} by phone: {customer_phone}")
                return user_id
        
        # ✅ СПОСОБ 3: По последним активным пользователям (если сумма совпадает)
        # Ищем пользователей, которые недавно нажимали на кнопки подписки
        user_id = find_recent_subscription_user(amount_value)
        if user_id:
            logger.info(f"✅ Found recent subscription user {user_id} by amount: {amount_value}")
            return user_id
            
        return None
        
    except Exception as e:
        logger.error(f"❌ Error finding user by payment data: {e}")
        return None

def find_user_by_email(email: str):
    """Ищет пользователя по email в базе данных"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Ищем в таблице users
        cursor.execute('SELECT user_id FROM users WHERE email = %s LIMIT 1', (email,))
        result = cursor.fetchone()
        
        if not result:
            # Ищем в таблице платежей по историческим данным
            cursor.execute('''
                SELECT user_id FROM payments 
                WHERE customer_email = %s 
                ORDER BY payment_date DESC 
                LIMIT 1
            ''', (email,))
            result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        logger.error(f"❌ Error finding user by email: {e}")
        return None

def find_user_by_phone(phone: str):
    """Ищет пользователя по номеру телефона"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Очищаем номер от лишних символов
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Ищем в пользователях (если есть поле phone)
        cursor.execute('''
            SELECT user_id FROM users 
            WHERE phone = %s OR phone LIKE %s 
            LIMIT 1
        ''', (phone, f'%{clean_phone}%'))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        logger.error(f"❌ Error finding user by phone: {e}")
        return None

def find_recent_subscription_user(amount: str):
    """Ищет недавних пользователей, которые выбирали подписку"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Создаем временную таблицу для хранения действий пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                action_type TEXT,
                action_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ищем пользователей, которые недавно нажимали на кнопки подписки
        cursor.execute('''
            SELECT user_id FROM user_actions 
            WHERE action_type = 'subscription_selection' 
            AND created_at >= NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC 
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        logger.error(f"❌ Error finding recent subscription user: {e}")
        return None

def determine_subscription_type(amount: str):
    """Определяет тип подписки по сумме платежа"""
    subscription_types = {
        "99.00": "month",
        "199.00": "3months", 
        "399.00": "6months",
        "799.00": "year"
    }
    
    return subscription_types.get(amount, "month")

def save_unknown_payment_for_review(payment_object):
    """Сохраняет платеж с неизвестным пользователем для ручной обработки"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unknown_payments (
                id SERIAL PRIMARY KEY,
                payment_id TEXT NOT NULL,
                amount DECIMAL,
                customer_email TEXT,
                customer_phone TEXT,
                payment_data JSONB,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        payment_id = payment_object.get('id')
        amount = payment_object.get('amount', {}).get('value')
        metadata = payment_object.get('metadata', {})
        customer_email = metadata.get('custEmail')
        customer_phone = metadata.get('phone') or metadata.get('custPhone')
        status = payment_object.get('status')
        
        cursor.execute('''
            INSERT INTO unknown_payments 
            (payment_id, amount, customer_email, customer_phone, payment_data, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (payment_id, amount, customer_email, customer_phone, json.dumps(payment_object), status))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Unknown payment saved for review: {payment_id}")
        
        # ✅ УВЕДОМЛЯЕМ АДМИНИСТРАТОРА О НЕИДЕНТИФИЦИРОВАННОМ ПЛАТЕЖЕ
        notify_admin_about_unknown_payment(payment_id, amount, customer_email, customer_phone)
        
    except Exception as e:
        logger.error(f"❌ Error saving unknown payment: {e}")

async def send_payment_success_notification(user_id: int, subscription_type: str, amount: str):
    """Отправляет уведомление пользователю об успешной оплате"""
    try:
        from telegram import Bot
        from config import BOT_TOKEN
        
        bot = Bot(token=BOT_TOKEN)
        
        subscription_names = {
            "month": "1 месяц",
            "3months": "3 месяца", 
            "6months": "6 месяцев",
            "year": "1 год"
        }
        
        message_text = f"""
✅ *Оплата прошла успешно!*

💎 Ваша премиум подписка "{subscription_names.get(subscription_type, '1 месяц')}" активирована.

💰 Сумма: {amount}₽

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Архипелаг ресурсов

Наслаждайтесь полным доступом! 💫
"""
        
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Success notification sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error sending success notification: {e}")

def notify_admin_about_unknown_payment(payment_id: str, amount: str, email: str, phone: str):
    """Уведомляет администратора о неидентифицированном платеже"""
    try:
        from telegram import Bot
        from config import BOT_TOKEN, ADMIN_IDS
        
        if not ADMIN_IDS:
            return
            
        bot = Bot(token=BOT_TOKEN)
        
        message_text = f"""
⚠️ *Неидентифицированный платеж*

💰 Сумма: {amount}₽
📧 Email: {email or 'Не указан'}
📞 Телефон: {phone or 'Не указан'}
🆔 Payment ID: {payment_id}

Требуется ручная обработка.
"""
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"❌ Error notifying admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Error notifying admin: {e}")

def activate_subscription_from_webhook(user_id, subscription_type, yookassa_payment_id, internal_payment_id):
    """Активирует подписку из вебхука"""
    try:
        from database import db
        from config import SUBSCRIPTION_DURATIONS
        
        # Активируем подписку в базе данных
        success = db.create_subscription(
            user_id, 
            subscription_type, 
            SUBSCRIPTION_DURATIONS[subscription_type]
        )
        
        if success:
            # Сохраняем информацию о платеже
            save_payment_to_db(user_id, subscription_type, yookassa_payment_id, internal_payment_id)
            return True
        return False
        
    except Exception as e:
        logger.error(f"❌ Error activating subscription from webhook: {e}")
        return False

def save_payment_to_db(user_id, subscription_type, yookassa_payment_id, internal_payment_id):
    """Сохраняет информацию о платеже в базу данных"""
    try:
        from database import db
        from config import SUBSCRIPTION_PRICES
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payments (user_id, amount, subscription_type, status, yoomoney_payment_id, payment_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            user_id,
            SUBSCRIPTION_PRICES[subscription_type],
            subscription_type,
            'success',
            yookassa_payment_id,
            internal_payment_id
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Payment saved to database for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error saving payment to DB: {e}")

def start_flask():
    """Запускает Flask сервер"""
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def ping_self():
    """Пингует собственный health endpoint"""
    service_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://metaphor-bot.onrender.com')
    
    while True:
        try:
            response = requests.get(f"{service_url}/health", timeout=10)
            logger.info(f"✅ Self-ping successful: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Self-ping failed: {e}")
        
        # Ждем 10 минут (600 секунд)
        time.sleep(600)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def run_bot_with_restart():
    """Запускает бота с автоматическим перезапуском при ошибках"""
    max_retries = 5
    retry_delay = 60  # секунды
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Attempt {attempt + 1} to start bot...")
            
            # Проверяем наличие токена
            if not BOT_TOKEN:
                logger.error("BOT_TOKEN not found in environment variables!")
                return
            
            # Проверяем наличие ключей ЮKassa
            from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
            if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
                logger.warning("⚠️ YooKassa keys not found - payments will not work!")
            else:
                logger.info("✅ YooKassa keys loaded")
            
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
            application.add_handler(CommandHandler("resources", handlers.resources_command))
            application.add_handler(CommandHandler("guide", handlers.guide_command))
            application.add_handler(CommandHandler("buy", handlers.buy_command))
            application.add_handler(CommandHandler("subscribe", handlers.subscribe_command))
            application.add_handler(CommandHandler("message", handlers.show_daily_message))
            application.add_handler(CommandHandler("message_status", handlers.message_status))
            application.add_handler(CommandHandler("debug_messages", handlers.debug_messages))
            application.add_handler(CommandHandler("init_messages", handlers.init_messages))
            application.add_handler(CommandHandler("update_db", handlers.update_database))
            application.add_handler(CommandHandler("mystatus", handlers.check_subscription_status))
            application.add_handler(CommandHandler("fix_limit", handlers.fix_limit))
            application.add_handler(CommandHandler("resetsimple", handlers.reset_simple))
            application.add_handler(CommandHandler("resetmymessages", handlers.reset_my_messages))
            application.add_handler(CommandHandler("resetusermessages", handlers.reset_user_messages_admin))
            application.add_handler(CommandHandler("resetallmessages", handlers.reset_all_messages))
            application.add_handler(CommandHandler("todaymessages", handlers.view_today_messages))
            
            application.add_handler(CallbackQueryHandler(
                handlers.handle_subscription_selection, 
                pattern="^subscribe_"
            ))
            application.add_handler(CallbackQueryHandler(
                handlers.handle_payment_check, 
                pattern="^check_payment_"
            ))
            application.add_handler(CallbackQueryHandler(handlers.button_handler))

            
            application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handlers.handle_random_messages
            ))

            application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handlers.handle_consult_form
            ))
            
            logger.info("🚀 Запуск бота в режиме Polling...")
            application.run_polling(
                poll_interval=3.0,
                timeout=20,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ Bot crashed on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"🔄 Restarting in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  
            else:
                logger.error("💥 Max retries exceeded. Bot stopped.")
                raise

def start_payment_monitoring():
    """Запускает автоматический мониторинг платежей"""
    while True:
        try:
            payment_processor.check_all_pending_payments()
        except Exception as e:
            logging.error(f"❌ Error in payment monitoring: {e}")
        
        # Проверяем каждые 30 секунд
        time.sleep(30)

def main():
    """Основная функция запуска"""
    
    # Запускаем мониторинг платежей в отдельном потоке
    payment_thread = threading.Thread(target=start_payment_monitoring)
    payment_thread.daemon = True
    payment_thread.start()

    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Даем Flask время на запуск
    time.sleep(3)
    
    # Запускаем самопинг в отдельном потоке
    ping_thread = threading.Thread(target=ping_self)
    ping_thread.daemon = True
    ping_thread.start()
    
    # Запускаем бота с автоматическим перезапуском
    run_bot_with_restart()

if __name__ == '__main__':
    main()