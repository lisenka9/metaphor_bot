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
    """Показывает историю карт пользователя (текстовый вариант)"""
    user = update.effective_user
    
    try:
        history = db.get_user_card_history(user.id, limit=20)
        
        if not history:
            await update.message.reply_text(
                "📝 У вас пока нет истории карт.\n"
                "Используйте /daily чтобы получить первую карту!"
            )
            return
        
        if len(history) > 5:
            history_text = f"📚 Последние 5 карт из {len(history)}:\n\n"
            history = history[:5]
        else:
            history_text = f"📚 Ваши карты ({len(history)}):\n\n"
        
        for i, (card_id, card_name, image_url, description, drawn_date) in enumerate(history, 1):
            if isinstance(drawn_date, str):
                date_str = drawn_date[:10]
            else:
                date_str = drawn_date.strftime("%d.%m.%Y")
            
            history_text += f"{i}. {card_name} - {date_str}\n"
        
        # Добавляем кнопку для просмотра с картинками
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("🖼 Показать с картинками", callback_data="show_history_pics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        history_text += "\n💫 Нажмите кнопку ниже чтобы увидеть картинки карт"
        
        await update.message.reply_text(
            history_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logging.error(f"❌ Error in history command: {e}")
        await update.message.reply_text("⚠️ Ошибка при загрузке истории")


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальная команда истории"""
    if context.args and context.args[0].lower() == "pics":
        await history_album(update, context)
    else:
        await history(update, context)

async def history_album(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """История в виде альбома (несколько картинок в одном сообщении)"""
    user = update.effective_user
    
    try:
        history = db.get_user_card_history(user.id, limit=5)  # Ограничиваем для альбома
        
        if not history:
            await update.message.reply_text(
                "📝 У вас пока нет истории карт.\n"
                "Используйте /daily чтобы получить первую карту!"
            )
            return
        
        from telegram import InputMediaPhoto
        
        # Создаем медиагруппу
        media_group = []
        
        for i, (card_id, card_name, image_url, description, drawn_date) in enumerate(history, 1):
            if isinstance(drawn_date, str):
                date_str = drawn_date[:10]
            else:
                date_str = drawn_date.strftime("%d.%m.%Y")
            
            caption = f"#{i} {card_name} - {date_str}"
            
            media_group.append(
                InputMediaPhoto(
                    media=image_url,
                    caption=caption
                )
            )
        
        # Отправляем альбом
        await update.message.reply_media_group(media=media_group)
        
        # Отправляем дополнительное текстовое сообщение
        stats = db.get_user_stats(user.id)
        total_cards = stats[2] if stats else 0
        await update.message.reply_text(
            f"🎴 Всего карт получено: {total_cards}\n"
            f"💫 Используйте /daily для новой карты"
        )
        
    except Exception as e:
        logging.error(f"❌ Error in history album: {e}")
        # В случае ошибки пробуем простой метод
        await simple_history_with_images(update, context)

async def simple_history_with_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Простая история с картинками (по одной)"""
    user = update.effective_user
    
    try:
        history = db.get_user_card_history(user.id, limit=5)
        
        if not history:
            await update.message.reply_text(
                "📝 У вас пока нет истории карт.\n"
                "Используйте /daily чтобы получить первую карту!"
            )
            return
        
        # Сначала отправляем текстовое сообщение
        history_text = f"📚 **Ваши последние {len(history)} карт:**\n\n"
        
        for i, (card_id, card_name, image_url, description, drawn_date) in enumerate(history, 1):
            if isinstance(drawn_date, str):
                date_str = drawn_date[:10]
            else:
                date_str = drawn_date.strftime("%d.%m.%Y")
            
            history_text += f"{i}. **{card_name}** - {date_str}\n"
        
        await update.message.reply_text(history_text, parse_mode='Markdown')
        
        # Затем отправляем картинки по одной
        for i, (card_id, card_name, image_url, description, drawn_date) in enumerate(history, 1):
            if isinstance(drawn_date, str):
                date_str = drawn_date[:10]
            else:
                date_str = drawn_date.strftime("%d.%m.%Y")
            
            caption = f"#{i} **{card_name}** - {date_str}"
            
            try:
                await update.message.reply_photo(
                    photo=image_url,
                    caption=caption,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Error sending history image {i}: {e}")
                # Если картинка не загружается, отправляем текстовое описание
                await update.message.reply_text(
                    f"#{i} **{card_name}** - {date_str}\n(изображение недоступно)"
                )
        
    except Exception as e:
        logging.error(f"❌ Error in simple history: {e}")
        await update.message.reply_text("⚠️ Ошибка при загрузке истории")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
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
    
    elif query.data == "show_history_pics":
        # Показываем историю с картинками
        user = query.from_user
        await query.edit_message_reply_markup(reply_markup=None)  # убираем кнопку
        await history_album_from_query(query, context)

async def history_album_from_query(query, context: ContextTypes.DEFAULT_TYPE):
    """История с картинками для callback query"""
    user = query.from_user
    
    try:
        history = db.get_user_card_history(user.id, limit=5)
        
        if not history:
            await query.message.reply_text("📝 У вас пока нет истории карт.")
            return
        
        from telegram import InputMediaPhoto
        
        # Создаем медиагруппу
        media_group = []
        
        for i, (card_id, card_name, image_url, description, drawn_date) in enumerate(history, 1):
            if isinstance(drawn_date, str):
                date_str = drawn_date[:10]
            else:
                date_str = drawn_date.strftime("%d.%m.%Y")
            
            caption = f"#{i} {card_name} - {date_str}"
            
            media_group.append(
                InputMediaPhoto(
                    media=image_url,
                    caption=caption
                )
            )
        
        # Отправляем альбом
        await query.message.reply_media_group(media=media_group)
        
        # Статистика
        stats = db.get_user_stats(user.id)
        total_cards = stats[2] if stats else 0
        await query.message.reply_text(
            f"🎴 Всего карт получено: {total_cards}\n"
        )
        
    except Exception as e:
        logging.error(f"❌ Error in history album from query: {e}")
        await query.message.reply_text("⚠️ Ошибка при загрузке истории с картинками")
