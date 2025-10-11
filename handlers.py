from telegram import Update
from telegram.ext import ContextTypes
from database import db 
from config import ADMIN_IDS
import logging

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Логируем данные пользователя для отладки
    logging.info(f"New user: ID={user.id}, Name={user.first_name}, "
                 f"Username=@{user.username}, LastName={user.last_name}")
    
    # Регистрируем пользователя с обработкой None значений
    db.get_or_create_user(
        user_id=user.id,
        username=user.username or "",  # Если username None - используем пустую строку
        first_name=user.first_name or "Пользователь",  # Если first_name None
        last_name=user.last_name or ""  # Если last_name None
    )
    
    # Создаем приветственное сообщение с учетом доступных данных
    if user.username:
        greeting = f"Привет, @{user.username}! 👋"
    else:
        greeting = f"Привет, {user.first_name}! 👋"
    
    welcome_text = f"""
{greeting}

Я - бот метафорических карт. Каждый день ты можешь получать свою карту дня, которая поможет задуматься о текущей ситуации.

✨ Команды:
/daily - Получить карту дня
/profile - Ваша статистика
/help - Помощь

🎴 Карта дня - это случайная карта из колоды, которая может подсказать, на что обратить внимание сегодня.
    """
    
    await update.message.reply_text(welcome_text)

async def daily_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /daily"""
    user = update.effective_user
    
    # Проверяем, можно ли взять карту
    can_take, reason = db.can_take_daily_card(user.id)
    
    if not can_take:
        await update.message.reply_text(f"❌ {reason}")
        return
    
    # Получаем случайную карту
    card = db.get_random_card()
    if not card:
        await update.message.reply_text("⚠️ Произошла ошибка при получении карты. Попробуйте позже.")
        return
    
    card_id, card_name, image_url, description = card
    
    # Новый формат текста карты
    card_text = f"""✨ Выбор сделан! Карта дня на сегодня - {card_name}. 

👁 Посмотрите на неё несколько секунд и отметьте:
— какое состояние она вызывает?
— какое воспоминание всплыло?
— какое слово или эмоция пришли первыми?
— как символика карты может помочь вам сегодня?

💭 С каким эмоциональным состоянием у вас ассоциируется изображение — радость, грусть, спокойствие, вдохновение или что-то другое?

В работе с метафорическими картами нет «правильных» ответов — важен ваш личный смысл, рождающийся в момент встречи с образом."""
    
    try:
        
        await update.message.reply_photo(
            photo=image_url,  
            caption=card_text,
            parse_mode='Markdown'
        )
        
        # Записываем в историю
        db.record_user_card(user.id, card_id)
        
    except FileNotFoundError:
        # Если картинка не найдена, отправляем только текст
        await update.message.reply_text(
            card_text + "\n\n⚠️ Изображение временно недоступно",
            parse_mode='Markdown'
        )
        db.record_user_card(user.id, card_id)
    except Exception as e:
        logging.error(f"Error sending card: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при отправке карты. Попробуйте позже."
        )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /profile"""
    user = update.effective_user
    
    logging.info(f"🔄 Profile command from user {user.id}")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Проверяем, есть ли пользователь в базе - ИСПРАВЛЕНО для PostgreSQL
        cursor.execute('SELECT * FROM users WHERE user_id = %s', (user.id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await update.message.reply_text("❌ Вы не зарегистрированы. Используйте /start")
            conn.close()
            return
        
        # Получаем количество карт - ИСПРАВЛЕНО для PostgreSQL
        cursor.execute('SELECT COUNT(*) FROM user_cards WHERE user_id = %s', (user.id,))
        total_cards = cursor.fetchone()[0]
        
        # Получаем лимит - ИСПРАВЛЕНО для PostgreSQL
        cursor.execute('SELECT daily_cards_limit FROM users WHERE user_id = %s', (user.id,))
        limit_result = cursor.fetchone()
        limit = limit_result[0] if limit_result else 3
        
        profile_text = f"""
👤 **Ваш профиль**

📊 Всего карт получено: {total_cards}
🎯 Лимит карт в день: {limit}
📅 ID пользователя: {user.id}
        """
        
        await update.message.reply_text(profile_text)
        conn.close()
        
    except Exception as e:
        logging.error(f"❌ Error in profile command: {e}")
        await update.message.reply_text("⚠️ Ошибка при загрузке профиля")

async def reset_my_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс своего лимита карт (для тестирования)"""
    user = update.effective_user
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        # ИСПРАВЛЕНО для PostgreSQL
        cursor.execute('UPDATE users SET last_daily_card_date = NULL WHERE user_id = %s', (user.id,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ Ваш лимит сброшен! Можете снова взять карту дня.")
        
    except Exception as e:
        logging.error(f"❌ Error resetting limit: {e}")
        await update.message.reply_text("❌ Ошибка при сбросе лимита")

async def debug_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Временная команда для отладки базы данных"""
    user = update.effective_user
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Проверяем таблицы в PostgreSQL - ИСПРАВЛЕНО
        cursor.execute('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        ''')
        tables = [table[0] for table in cursor.fetchall()]
        
        # Проверяем пользователя - ИСПРАВЛЕНО для PostgreSQL
        cursor.execute('SELECT * FROM users WHERE user_id = %s', (user.id,))
        user_data = cursor.fetchone()
        
        # Проверяем карты - ИСПРАВЛЕНО для PostgreSQL
        cursor.execute('SELECT COUNT(*) FROM user_cards WHERE user_id = %s', (user.id,))
        user_cards_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cards')
        total_cards_count = cursor.fetchone()[0]
        
        debug_text = f"""
🔍 **Отладочная информация:**

📋 Таблицы в базе: {tables}
👤 Ваши данные: {'✅ Есть' if user_data else '❌ Нет'}
🎴 Ваших карт в истории: {user_cards_count}
🃏 Всего карт в колоде: {total_cards_count}
        """
        
        await update.message.reply_text(debug_text)
        conn.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка отладки: {e}")
