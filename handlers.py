from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import db 
from config import ADMIN_IDS
import logging
import keyboard
import csv
import io

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
        first_name=user.first_name or "",  # Если first_name None
        last_name=user.last_name or ""  # Если last_name None
    )
    
    # Создаем приветственное сообщение с учетом доступных данных
    if user.first_name:
        greeting = f"{user.first_name}, приветствую!"
    else:
        greeting = f"@{user.username}, приветствую!"
    
    welcome_text = f"""
{greeting}

Меня зовут Светлана Скромова. Я практикующий эмоционально-образный терапевт и автор уникальной колоды метафорических карт "Настроение как море".


    """
    
    photo_url = "https://ibb.co/279SfcJ4" 
    
    try:
        # Отправляем фото с текстом
        await update.message.reply_photo(
            photo=photo_url,
            caption=welcome_text,
            parse_mode='Markdown'
        )
        logging.info(f"✅ Photo sent successfully for user {user.id}")
    except Exception as e:
        # Если фото не загружается, отправляем только текст
        logging.error(f"Error sending photo: {e}")
        logging.error(f"Photo URL: {photo_url}")
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def daily_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /daily с новой структурой"""
    user = update.effective_user
    
    can_take, reason = db.can_take_daily_card(user.id)
    
    if not can_take:
        await update.message.reply_text(f"❌ {reason}")
        return
    
    # Сохраняем в контексте, что пользователь начал процесс
    context.user_data['daily_in_progress'] = True
    
    intro_text = """
🌊 Настройка на волну дня

Прежде, чем сделать выбор карты, создайте для себя пространство тишины и спокойствия 🦋

💎 Сделайте несколько глубоких вдохов, закройте глаза и направьте внимание внутрь: какой вопрос или задача сейчас для вас наиболее актуальна?

💎 Сформулируйте свой вопрос к карте.

💡 Подсказка: Пусть вопрос будет открытым, например:
• «Какой ресурс поможет мне сегодня?»
• «В чём мне стоит проявить осторожность?»
• «Что важно увидеть мне сегодня?»

Нажмите кнопку ниже, чтобы получить свою карту дня!
"""
    
    await update.message.reply_text(
        intro_text,
        reply_markup=keyboard.get_daily_intro_keyboard(),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_data = context.user_data
    
    if query.data == "get_daily_card":
        # Пользователь нажал "Карта дня" - показываем карту
        await show_daily_card(query, context)
        
    elif query.data == "get_daily_message":
        # Пользователь нажал "Послание дня" - показываем послание
        await show_daily_message(query, context)
        
    elif query.data == "flip_card":
        # Старая функциональность (если нужно сохранить)
        await handle_flip_card(query, context)

async def show_daily_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает карту дня с вопросами для размышления"""
    user = query.from_user
    
    # Получаем случайную карту
    card = db.get_random_card()
    if not card:
        await query.message.reply_text("⚠️ Ошибка при получении карты.")
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту в контексте
    context.user_data['last_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url
    }
    
    # Записываем карту пользователю
    db.record_user_card(user.id, card_id)
    
    card_text = f"""🎴 Карта дня: {card_name}

👁 Посмотрите на карту, не торопитесь. Позвольте образу говорить с вами.

Опирайтесь на вопросы, которые помогут вам заглянуть внутрь себя и извлечь максимум смысла. Запишите ответы в свой блокнот для большего осознания ⤵️

🔹 Состояние: Какое состояние или чувство рождается внутри вас, когда вы смотрите на эту карту? Что вы чувствуете телом?

🔹 Первый Отклик: Какое слово или эмоция пришли к вам первыми? (Доверьтесь этой первой искре!)

🔹 Путеводная Звезда: Как символика карты (цвета, объекты) может стать ключом к решению вашего вопроса? О чём именно этот образ хочет вам сказать?

🔹 Шаг вперед: Какой самый первый, самый легкий шаг вы можете предпринять сегодня, вдохновившись этой картой?

Помните: В работе с метафорическими картами нет «правильных» ответов. Важен Ваш уникальный, личный смысл, рождающийся в момент встречи с образом."""
    
    try:
        await query.message.reply_photo(
            photo=image_url,
            caption=card_text,
            reply_markup=keyboard.get_card_reflection_keyboard(),  # Кнопка "Послание дня"
            parse_mode='Markdown'
        )
        await query.edit_message_reply_markup(reply_markup=None)  # Убираем кнопку из предыдущего сообщения
        
    except Exception as e:
        logging.error(f"Error sending card image: {e}")
        await query.message.reply_text(
            card_text,
            reply_markup=keyboard.get_card_reflection_keyboard(),
            parse_mode='Markdown'
        )
        await query.edit_message_reply_markup(reply_markup=None)

async def show_daily_message(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает послание дня"""
    user = query.from_user
    
    # Получаем случайное послание
    message_data = db.get_random_message()
    if not message_data:
        await query.message.reply_text("⚠️ Ошибка при получении послания.")
        return
    
    message_id, image_url, message_text = message_data
    
    message_caption = f"""🦋 Послание Дня

Прочитайте его и почувствуйте, какой отклик оно находит внутри вас:

🔹 Как реагирует ваше тело?
🔹 Какие эмоции поднимаются?
🔹 Что важного это послание несет вам?
🔹 Как это послание поможет вам на вашем жизненном пути?"""
    
    try:
        await query.message.reply_photo(
            photo=image_url,
            caption=message_caption,
            parse_mode='Markdown'
        )
        await query.edit_message_reply_markup(reply_markup=None)  # Убираем кнопку
        
    except Exception as e:
        logging.error(f"Error sending message image: {e}")
        await query.message.reply_text(
            message_caption,
            parse_mode='Markdown'
        )
        await query.edit_message_reply_markup(reply_markup=None)

async def handle_flip_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик переворота карты (старая функциональность)"""
    user_data = context.user_data
    last_card = user_data.get('last_card', {})
    
    questions_text = f"""🎴 {last_card['card_name']}

👁 Вопросы для размышления:

— Какое состояние вызывает карта?
— Какое воспоминание всплыло?
— Какое слово или эмоция пришли первыми?  
— Как символика карты может помочь вам сегодня?

💭 С каким эмоциональным состоянием у вас ассоциируется изображение?

✨ В работе с метафорическими картами нет «правильных» ответов — важен ваш личный смысл, рождающийся в момент встречи с образом."""
    
    await query.edit_message_caption(
        caption=questions_text,
        reply_markup=None,
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
        
        
    except Exception as e:
        logging.error(f"❌ Error in history album from query: {e}")
        await query.message.reply_text("⚠️ Ошибка при загрузке истории с картинками")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика для администратора"""
    user = update.effective_user
    
    # Проверяем, является ли пользователь администратором
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM user_cards')
        total_cards_issued = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cards')
        total_cards_in_deck = cursor.fetchone()[0]
        
        # Активные пользователи (брали карты за последние 7 дней)
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) 
            FROM user_cards 
            WHERE drawn_date >= CURRENT_DATE - INTERVAL '7 days'
        ''')
        active_users = cursor.fetchone()[0]
        
        # Новые пользователи за последние 7 дней
        cursor.execute('''
            SELECT COUNT(*) 
            FROM users 
            WHERE registered_date >= CURRENT_DATE - INTERVAL '7 days'
        ''')
        new_users = cursor.fetchone()[0]
        
        # Топ пользователей по количеству карт
        cursor.execute('''
            SELECT u.user_id, u.first_name, u.username, COUNT(uc.id) as card_count
            FROM users u
            JOIN user_cards uc ON u.user_id = uc.user_id
            GROUP BY u.user_id, u.first_name, u.username
            ORDER BY card_count DESC
            LIMIT 10
        ''')
        top_users = cursor.fetchall()
        
        stats_text = f"""
📊 Статистика бота

👥 Пользователи:
• Всего пользователей: {total_users}
• Активных (7 дней): {active_users}
• Новых (7 дней): {new_users}

🎴 Карты:
• Всего карт в колоде: {total_cards_in_deck}
• Всего выдано карт: {total_cards_issued}

🏆 **Топ пользователей:**
"""
        
        for i, (user_id, first_name, username, card_count) in enumerate(top_users, 1):
            username_display = f"@{username}" if username else first_name
            stats_text += f"{i}. {username_display} - {card_count} карт\n"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
        conn.close()
        
    except Exception as e:
        logging.error(f"❌ Error getting admin stats: {e}")
        await update.message.reply_text("❌ Ошибка при получении статистики")


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список всех пользователей"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем всех пользователей с количеством карт
        cursor.execute('''
            SELECT u.user_id, u.username, u.first_name, u.registered_date, 
                   COUNT(uc.id) as card_count,
                   MAX(uc.drawn_date) as last_activity
            FROM users u
            LEFT JOIN user_cards uc ON u.user_id = uc.user_id
            GROUP BY u.user_id, u.username, u.first_name, u.registered_date
            ORDER BY u.registered_date DESC
        ''')
        
        users = cursor.fetchall()
        
        if not users:
            await update.message.reply_text("📝 Пользователей пока нет")
            return
        
        users_text = f"👥 **Все пользователи ({len(users)}):**\n\n"
        
        for i, (user_id, username, first_name, reg_date, card_count, last_activity) in enumerate(users[:20], 1):
            username_display = f"@{username}" if username else first_name
            reg_date_str = reg_date.strftime("%d.%m.%Y") if reg_date else "неизвестно"
            last_activity_str = last_activity.strftime("%d.%m.%Y") if last_activity else "нет активности"
            
            users_text += f"{i}. {username_display}\n"
            users_text += f"   ID: {user_id}\n"
            users_text += f"   Карт: {card_count}\n"
            users_text += f"   Регистрация: {reg_date_str}\n"
            users_text += f"   Последняя активность: {last_activity_str}\n\n"
        
        if len(users) > 20:
            users_text += f"\n... и еще {len(users) - 20} пользователей"
        
        await update.message.reply_text(users_text, parse_mode='Markdown')
        
        conn.close()
        
    except Exception as e:
        logging.error(f"❌ Error getting users list: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка пользователей")


async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт данных в CSV"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Экспорт пользователей
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, registered_date
            FROM users 
            ORDER BY registered_date
        ''')
        users_data = cursor.fetchall()
        
        # Создаем CSV в памяти
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow(['User ID', 'Username', 'First Name', 'Last Name', 'Registered Date'])
        
        # Данные
        for row in users_data:
            writer.writerow(row)
        
        # Отправляем файл
        output.seek(0)
        await update.message.reply_document(
            document=io.BytesIO(output.getvalue().encode()),
            filename="users_export.csv",
            caption="📊 Экспорт пользователей"
        )
        
        conn.close()
        
    except Exception as e:
        logging.error(f"❌ Error exporting data: {e}")
        await update.message.reply_text("❌ Ошибка при экспорте данных")

async def add_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет недостающие карты в базу"""
    user = update.effective_user
    
    # Проверяем, является ли пользователь администратором
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        added_count = db.add_missing_cards()
        await update.message.reply_text(f"✅ Добавлено {added_count} новых карт в колоду")
        
    except Exception as e:
        logging.error(f"❌ Error in add_cards: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении карт")


