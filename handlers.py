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
    stats = db.get_user_stats(user.id)
    
    if not stats:
        await update.message.reply_text("❌ Не удалось загрузить статистику")
        return
    
    limit, is_premium, total_cards, reg_date = stats
    
    profile_text = f"""
👤 Ваш профиль

📊 Всего карт получено: {total_cards}
🎯 Лимит карт в день: {limit}
💎 Статус: {'Премиум' if is_premium else 'Базовый'}
📅 Дата регистрации: {reg_date[:10]}
    """
    
    await update.message.reply_text(profile_text)
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 Доступные команды:

/daily - Получить карту дня
/profile - Ваша статистика и лимиты
/help - Эта справка

❓ Как это работает?
- Каждый день вы можете получить одну случайную карту
- Карта выбирается из колоды случайным образом
- Вы можете размышлять над значением карты в контексте вашей жизни

💡 Совет: Не пытайтесь анализировать карту слишком рационально. 
Дайте образу войти в ваше сознание, обратите внимание на первые мысли и чувства.
    """
    
    await update.message.reply_text(help_text)

async def reset_my_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс своего лимита карт (для тестирования)"""
    user = update.effective_user
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_daily_card_date = NULL WHERE user_id = ?', (user.id,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ Ваш лимит сброшен! Можете снова взять карту дня.")
        
    except Exception as e:
        logging.error(f"Error resetting limit: {e}")
        await update.message.reply_text("❌ Ошибка при сбросе лимита")

