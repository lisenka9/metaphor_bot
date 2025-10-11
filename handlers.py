from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import db 
from config import ADMIN_IDS
import logging
import keyboard

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
/history - История ваших карт

🎴 Карта дня - это случайная карта из колоды, которая может подсказать, на что обратить внимание сегодня.
    """
    
    await update.message.reply_text(welcome_text)

async def daily_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /daily с интерактивной картой"""
    user = update.effective_user
    
    can_take, reason = db.can_take_daily_card(user.id)
    
    if not can_take:
        await update.message.reply_text(f"❌ {reason}")
        return
    
    card = db.get_random_card()
    if not card:
        await update.message.reply_text("⚠️ Ошибка при получении карты.")
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту в контексте
    context.user_data['last_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url
    }
    
    card_text = f"""✨ Карта дня: {card_name}

Посмотрите на изображение... 
Какие первые ощущения?"""
    
    try:
        await update.message.reply_photo(
            photo=image_url,  
            caption=card_text,
            reply_markup=keyboard.get_card_keyboard(),  # добавляем кнопку
            parse_mode='Markdown'
        )
        
        db.record_user_card(user.id, card_id)
        
    except Exception as e:
        await update.message.reply_text(
            f"✨ Карта дня: {card_name}**\n\n{card_text}",
            reply_markup=keyboard.get_card_keyboard(),  # добавляем кнопку
            parse_mode='Markdown'
        )
        db.record_user_card(user.id, card_id)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопку 'Перевернуть карту'"""
    query = update.callback_query
    await query.answer()  # важно - подтверждаем нажатие
    
    user_data = context.user_data
    last_card = user_data.get('last_card', {})
    
    if query.data == "flip_card":
        questions_text = f"""🎴 {last_card['card_name']}

👁 Вопросы для размышления:

— Какое состояние вызывает карта?
— Какое воспоминание всплыло?
— Какое слово или эмоция пришли первыми?  
— Как символика карты может помочь вам сегодня?

💭 С каким эмоциональным состоянием у вас ассоциируется изображение?

✨ В работе с метафорическими картами нет «правильных» ответов — важен ваш личный смысл, рождающийся в момент встречи с образом."""
        
        # Убираем кнопку после нажатия
        await query.edit_message_caption(
            caption=questions_text,
            reply_markup=None,  # убираем клавиатуру
            parse_mode='Markdown'
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 Доступные команды:

/daily - Получить карту дня
/profile - Ваша статистика и лимиты
/history - Посмотреть историю всех ваших карт
/help - Эта справка

❓ Как это работает?
- Каждый день вы можете получить одну случайную карту
- Карта выбирается из колоды случайным образом
- Вы можете размышлять над значением карты в контексте вашей жизни

💡 Совет: Не пытайтесь анализировать карту слишком рационально. 
Дайте образу войти в ваше сознание, обратите внимание на первые мысли и чувства.
    """
    
    await update.message.reply_text(help_text)

    
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
📅 Дата регистрации: {reg_date}
    """
    
    await update.message.reply_text(profile_text)

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
🔍 Отладочная информация:

📋 Таблицы в базе: {tables}
👤 Ваши данные: {'✅ Есть' if user_data else '❌ Нет'}
🎴 Ваших карт в истории: {user_cards_count}
🃏 Всего карт в колоде: {total_cards_count}
        """
        
        await update.message.reply_text(debug_text)
        conn.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка отладки: {e}")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает историю карт пользователя"""
    user = update.effective_user
    
    try:
        history = db.get_user_card_history(user.id)
        
        if not history:
            await update.message.reply_text(
                "📝 У вас пока нет истории карт.\n"
                "Используйте /daily чтобы получить первую карту!"
            )
            return
        
        if len(history) > 10:  # Ограничиваем показ для удобства
            history_text = f"📚 **Последние 10 карт из {len(history)}:**\n\n"
            history = history[:10]
        else:
            history_text = f"📚 **Ваши карты ({len(history)}):**\n\n"
        
        for i, (card_name, image_url, description, drawn_date) in enumerate(history, 1):
            # Форматируем дату
            if isinstance(drawn_date, str):
                date_str = drawn_date[:10]
            else:
                date_str = drawn_date.strftime("%d.%m.%Y")
            
            history_text += f"{i}. **{card_name}** - {date_str}\n"
        
        history_text += "\n💫 Каждая карта — это момент вашего пути."
        
        await update.message.reply_text(history_text, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"❌ Error in history command: {e}")
        await update.message.reply_text("⚠️ Ошибка при загрузке истории")


async def detailed_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подробная история с пагинацией"""
    user = update.effective_user
    
    try:
        history = db.get_user_card_history(user.id)
        
        if not history:
            await update.message.reply_text("📝 У вас пока нет истории карт.")
            return
        
        # Показываем по 5 карт за раз
        page = context.args[0] if context.args else "1"
        try:
            page = int(page)
        except:
            page = 1
            
        items_per_page = 5
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        
        total_pages = (len(history) + items_per_page - 1) // items_per_page
        
        history_text = f"📚 **Ваши карты (страница {page}/{total_pages}):**\n\n"
        
        for i, (card_name, image_url, description, drawn_date) in enumerate(history[start_idx:end_idx], start_idx + 1):
            if isinstance(drawn_date, str):
                date_str = drawn_date[:10]
            else:
                date_str = drawn_date.strftime("%d.%m.%Y")
            
            history_text += f"**{card_name}** - {date_str}\n"
        
        if total_pages > 1:
            history_text += f"\nИспользуйте /history {page+1} для следующей страницы"
        
        await update.message.reply_text(history_text, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"❌ Error in detailed history: {e}")
        await update.message.reply_text("⚠️ Ошибка при загрузке истории")
