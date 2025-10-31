from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import db 
from config import ADMIN_IDS
import logging
import keyboard
import csv
import io
from datetime import datetime
from payment import payment_processor
from config import SUBSCRIPTION_PRICES, SUBSCRIPTION_NAMES, SUBSCRIPTION_DURATIONS, YOOMONEY_RECEIVER

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
    
    photo_url = "https://ibb.co/0bc2b6M" 
    
    try:
        # Сначала отправляем фото с коротким заголовком
        short_caption = f"{greeting}\n\nМеня зовут Светлана Скромова. Я практикующий эмоционально-образный терапевт и автор уникальной колоды метафорических карт 'Настроение как море'."
        await update.message.reply_photo(
            photo=photo_url,
            caption=short_caption,
            parse_mode='Markdown'
        )
        
        # Затем отправляем полный текст отдельным сообщением
        welcome_text = f"""

🌊 О колоде и миссии бота

Море, как и наша жизнь, многолико: оно может быть ласковым, умиротворяющим, а порой — грозным и разрушительным. Этот образ идеально отражает внутренние состояния человека: от штиля до бури.

Каждая карта колоды пропитана энергией моря и создана для того, чтобы помочь вам:

Увидеть подсказки для решения жизненных ситуаций.

Наполниться ресурсами и энергией, которую несет в себе морская стихия.

Научиться распознавать свои эмоции и быть с ними в контакте.

Колода "Настроение как море" помогает заглянуть в глубину собственного бессознательного, осознать эмоции, встретиться с тем, что подавлено, и открыть новые ресурсы для роста.

✨ В добрый путь!
Я благодарю Вас за доверие и интерес к своему внутреннему миру.

Выбирайте в меню бота то, что для Вас сейчас наиболее актуально!

✨ Команды:
/daily - Получить карту дня
/resources - Архипелаг ресурсов 
/guide - Гайд по Эмоциональному Интеллекту
/buy - Купить колоду
/profile - Ваша статистика
/help - Помощь
/history - История ваших карт
/message - Послание дня
/consult - Запись на консультацию
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        
    except Exception as e:
        # Если фото не загружается, отправляем только текст
        logging.error(f"Error sending photo: {e}")
        full_text = f"""
{greeting}

Меня зовут Светлана Скромова. Я практикующий эмоционально-образный терапевт и автор уникальной колоды метафорических карт "Настроение как море".

🌊 О колоде и миссии бота
Море, как и наша жизнь, многолико: оно может быть ласковым, умиротворяющим, а порой — грозным и разрушительным. Этот образ идеально отражает внутренние состояния человека: от штиля до бури.

Каждая карта колоды пропитана энергией моря и создана для того, чтобы помочь вам:

Увидеть подсказки для решения жизненных ситуаций.

Наполниться ресурсами и энергией, которую несет в себе морская стихия.

Научиться распознавать свои эмоции и быть с ними в контакте.

✨ Команды:
/daily - Получить карту дня
/resources - Архипелаг ресурсов 
/guide - Гайд по Эмоциональному Интеллекту
/buy - Купить колоду
/profile - Ваша статистика
/help - Помощь
/message - Послание дня
/history - История ваших карт
        """
        await update.message.reply_text(full_text, parse_mode='Markdown')

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

💡 Подсказка: Пусть вопрос будет открытым, например:«Какой ресурс поможет мне сегодня?» или «В чём мне стоит проявить осторожность?»

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
    
    # ✅ Защита от множественных нажатий
    user_id = query.from_user.id
    current_time = datetime.now().timestamp()
    
    if 'last_button_click' in context.user_data:
        last_click = context.user_data['last_button_click']
        if current_time - last_click < 3:  # 3 секунды между нажатиями
            logging.info(f"⚡ Fast click protection for user {user_id}")
            return
    
    context.user_data['last_button_click'] = current_time
    
    # ✅ Логируем какая кнопка нажата
    logging.info(f"🔄 Button pressed: {query.data} by user {user_id}")
    
    if query.data == "show_daily_intro":
        await show_daily_intro_from_button(query, context)
        
    elif query.data == "get_daily_card":
        await show_daily_card(query, context)
        
    elif query.data == "get_daily_message":
        await show_daily_message(query, context)
        
    elif query.data == "card_questions":  # ✅ ДОБАВЛЕНО
        await show_card_questions(query, context)
    
    elif query.data == "show_history_pics":
        await show_history_pics_from_button(query, context)
    
    elif query.data == "main_menu":
        await show_main_menu_from_button(query, context)
    
    elif query.data == "profile":
        await show_profile_from_button(query, context)
    
    elif query.data == "history":
        await show_history_from_button(query, context)
    
    elif query.data == "consult":
        await show_consult_from_button(query, context)
    
    elif query.data == "start_consult_form":
        await start_consult_form(query, context)
    
    elif query.data == "resources":
        await show_resources_from_button(query, context)
    
    elif query.data == "guide":
        await show_guide_from_button(query, context)
    
    elif query.data == "buy":
        await show_buy_from_button(query, context)
    
    elif query.data == "subscribe":
        await show_subscribe_from_button(query, context)
    
    elif query.data.startswith("subscribe_"):
        await handle_subscription_selection(query, context)
    
    elif query.data.startswith("check_payment_"):
        await handle_payment_check(query, context)

async def start_consult_form(query, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс заполнения формы консультации"""
    # Убираем кнопку из предыдущего сообщения
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Сохраняем состояние формы
    context.user_data['consult_form'] = {
        'step': 1,
        'user_id': query.from_user.id,
        'username': query.from_user.username or query.from_user.first_name
    }
    
    # Первый вопрос формы
    question_text = """
📝 Запись на консультацию

Пожалуйста, ответьте на вопросы ниже. Это поможет мне лучше понять ваш запрос и подготовиться к нашей встрече.

1. Как я могу к вам обращаться?
"""
    
    await query.message.reply_text(
        question_text,
        parse_mode='Markdown'
    )

async def handle_consult_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответы формы консультации"""
    user_data = context.user_data.get('consult_form', {})
    
    if not user_data or 'step' not in user_data:
        await handlers.help_command(update, context)
        return
    
    step = user_data['step']
    user_id = user_data['user_id']
    
    # Проверяем, что сообщение от того же пользователя
    if update.effective_user.id != user_id:
        return
    
    user_answer = update.message.text
    
    if step == 1:
        user_data['name'] = user_answer
        user_data['step'] = 2
        question_text = "2. Опишите в нескольких словах проблему/запрос, с которым хотите прийти на консультацию"
        await update.message.reply_text(question_text, parse_mode='Markdown')
        
    elif step == 2:
        user_data['problem'] = user_answer
        user_data['step'] = 3
        question_text = "3. Напишите время с воскресенья по среду, которое подходит для консультации"
        await update.message.reply_text(question_text, parse_mode='Markdown')
        
    elif step == 3:
        user_data['preferred_time'] = user_answer
        user_data['step'] = 4
        question_text = "4. Укажите Ваш Telegram-ник или WhatsApp для связи\n\nВ ближайшие 24 часа я напишу Вам для подтверждения времени консультации."
        await update.message.reply_text(question_text, parse_mode='Markdown')
        
    elif step == 4:
        user_data['contact'] = user_answer
        
        # Получаем московское время
        try:
            import pytz
            moscow_tz = pytz.timezone('Europe/Moscow')
            moscow_time = datetime.now(moscow_tz)
        except:
            # Если pytz не установлен, используем локальное время с пометкой МСК
            moscow_time = datetime.now()
        
        # Формируем итоговое сообщение для отправки психологу
        consult_summary = f"""
📋 *Новая заявка на консультацию*

👤 *От пользователя:* @{update.effective_user.username or 'не указан'}

📝 *Данные формы:*
• *Имя:* {user_data.get('name', 'Не указано')}
• *Проблема/запрос:* {user_data.get('problem', 'Не указано')}
• *Удобное время:* {user_data.get('preferred_time', 'Не указано')}
• *Контакт:* {user_data.get('contact', 'Не указано')}

⏰ *Время заявки:* {moscow_time.strftime('%d.%m.%Y %H:%M')} (мск)
"""
        
        try:
            # Отправляем заявку всем администраторам
            from config import ADMIN_IDS
            sent_to_admins = []
            
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=consult_summary,
                        parse_mode='Markdown'
                    )
                    sent_to_admins.append(admin_id)
                    logging.info(f"✅ Consult form sent to admin {admin_id}")
                except Exception as admin_error:
                    logging.error(f"❌ Error sending to admin {admin_id}: {admin_error}")
            
            if sent_to_admins:
                # Подтверждаем пользователю
                success_text = f"""
✅ *Спасибо! Ваша заявка отправлена!*

В ближайшие 24 часа я свяжусь с вами для подтверждения времени консультации.
"""
                await update.message.reply_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard.get_main_menu_keyboard()
                )
            else:
                raise Exception("Не удалось отправить ни одному администратору")
            
        except Exception as e:
            logging.error(f"❌ Error sending consult form: {e}")
            
            # Формируем сообщение для копирования
            copyable_form = f"""
❌ *Не удалось отправить заявку автоматически*

Пожалуйста, скопируйте эту информацию и отправьте напрямую @Skromova_Svetlana_psy:

*Имя:* {user_data.get('name', 'Не указано')}
*Проблема:* {user_data.get('problem', 'Не указано')}
*Удобное время:* {user_data.get('preferred_time', 'Не указано')}
*Контакт:* {user_data.get('contact', 'Не указано')}
*Мой Telegram:* @{update.effective_user.username or 'не указан'}
*Время заявки:* {moscow_time.strftime('%d.%m.%Y %H:%M')} (мск)
"""
            await update.message.reply_text(
                copyable_form,
                parse_mode='Markdown',
                reply_markup=keyboard.get_main_menu_keyboard()
            )
        
        # Очищаем данные формы
        if 'consult_form' in context.user_data:
            del context.user_data['consult_form']

            

async def admin_consult_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает заявки на консультацию для администратора"""
    user = update.effective_user
    
    # Проверяем, является ли пользователь администратором
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    # Здесь можно добавить логику для просмотра заявок из базы данных
    # если вы решите сохранять их в базу
    
    await update.message.reply_text(
        "📋 Команда для просмотра заявок на консультацию.\n"
        "Заявки автоматически отправляются всем администраторам.",
        parse_mode='Markdown'
    )


async def show_daily_intro_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает интро для карты дня при нажатии кнопки из меню"""
    user = query.from_user
    
    # ✅ Проверяем лимит СРАЗУ при нажатии "Карта дня" в меню
    can_take, reason = db.can_take_daily_card(user.id)
    if not can_take:
        await query.message.reply_text(f"❌ {reason}")
        return
    
    intro_text = """
🌊 Настройка на волну дня

Прежде, чем сделать выбор карты, создайте для себя пространство тишины и спокойствия 🦋

💎 Сделайте несколько глубоких вдохов, закройте глаза и направьте внимание внутрь: какой вопрос или задача сейчас для вас наиболее актуальна?

💎 Сформулируйте свой вопрос к карте.

💡 Подсказка: Пусть вопрос будет открытым, например:«Какой ресурс поможет мне сегодня?» или «В чём мне стоит проявить осторожность?»

Нажмите кнопку ниже, чтобы получить свою карту дня!
"""
    
    # Отправляем новое сообщение с интро, не редактируя предыдущее
    await query.message.reply_text(
        intro_text,
        reply_markup=keyboard.get_daily_intro_keyboard(),
        parse_mode='Markdown'
    )


async def show_main_menu_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню при нажатии кнопки (не редактирует предыдущее сообщение)"""
    menu_text = """
🌊 О колоде и миссии бота

Море, как и наша жизнь, многолико: оно может быть ласковым, умиротворяющим, а порой — грозным и разрушительным. Этот образ идеально отражает внутренние состояния человека: от штиля до бури.

Каждая карта колоды пропитана энергией моря и создана для того, чтобы помочь вам:

Увидеть подсказки для решения жизненных ситуаций.

Наполниться ресурсами и энергией, которую несет в себе морская стихия.

Научиться распознавать свои эмоции и быть с ними в контакте.

Колода "Настроение как море" помогает заглянуть в глубину собственного бессознательного, осознать эмоции, встретиться с тем, что подавлено, и открыть новые ресурсы для роста.

✨ В добрый путь!
Я благодарю Вас за доверие и интерес к своему внутреннему миру.

Выбирайте в меню бота то, что для Вас сейчас наиболее актуально!

✨ Команды:
/daily - Получить карту дня
/resources - Архипелаг ресурсов 
/guide - Гайд по Эмоциональному Интеллекту
/buy - Купить колоду
/profile - Ваша статистика
/help - Помощь
/message - Послание дня
/history - История ваших карт
/consult - Запись на консультацию
"""
    
    # Отправляем новое сообщение с меню, не редактируя предыдущее
    await query.message.reply_text(
        menu_text,
        reply_markup=keyboard.get_main_menu_keyboard(),
        parse_mode='Markdown'
    )

async def show_daily_message(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает послание дня при нажатии кнопки"""
    user = query.from_user
    
    # Проверяем лимит посланий
    can_take, reason = db.can_take_daily_message(user.id)
    
    if not can_take:
        # Показываем статистику и информацию о лимитах
        stats = db.get_user_message_stats(user.id)
        if stats:
            if stats['has_subscription']:
                limit_text = f"❌ {reason}\n\n📊 Сегодня: {stats['today_count']}/5 посланий"
                reply_markup = keyboard.get_main_menu_keyboard()
            else:
                if stats['can_take']:
                    limit_text = "✅ Можно взять послание (1 раз в неделю)"
                    reply_markup = keyboard.get_main_menu_keyboard()
                else:
                    limit_text = f"❌ {reason}\n\n📅 Следующее послание через {stats['days_until_next']} дней"
                    reply_markup = keyboard.get_message_status_keyboard()
        else:
            limit_text = f"❌ {reason}"
            reply_markup = keyboard.get_main_menu_keyboard()
        
        await query.message.reply_text(
            limit_text,
            reply_markup=reply_markup
        )
        return
    
    # Получаем случайное послание
    message_data = db.get_random_message()
    if not message_data:
        await query.message.reply_text(
            "⚠️ Ошибка при получении послания. Пожалуйста, попробуйте позже.",
            reply_markup=keyboard.get_daily_message_keyboard()
        )
        return
    
    message_id, image_url, message_text = message_data
    
    # Записываем факт получения послания
    success = db.record_user_message(user.id, message_id)
    if not success:
        logging.error(f"❌ Failed to record message for user {user.id}")
    
    message_caption = f'''🦋 Послание Дня

Прочитайте его и почувствуйте, какой отклик оно находит внутри вас:

🔹 Как реагирует ваше тело?
🔹 Какие эмоции поднимаются?
🔹 Что важного это послание несет вам?
🔹 Как это послание поможет вам на вашем жизненном пути?'''
    
    try:
        # Отправляем новое сообщение с посланием
        await query.message.reply_photo(
            photo=image_url,
            caption=message_caption,
            reply_markup=keyboard.get_daily_message_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error sending message image: {e}")
        await query.message.reply_text(
            f"{message_caption}\n\n📝 *Текст послания:* {message_text}",
            reply_markup=keyboard.get_daily_message_keyboard(),
            parse_mode='Markdown'
        )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /profile"""
    user = update.effective_user
    
    stats = db.get_user_stats(user.id)
    
    if not stats:
        await update.message.reply_text("❌ Не удалось загрузить статистику")
        return
    
    limit, is_premium, total_cards, reg_date, subscription_end = stats
    
    # Формируем текст о подписке
    if subscription_end:
        subscription_text = f"✅ Активна до: {subscription_end}"
    else:
        subscription_text = "❌ Нет активной подписки"
    
    profile_text = f"""
👤 Ваш профиль

📊 Всего карт получено: {total_cards}
🎯 Лимит карт в день: {limit}
💎 Подписка: {subscription_text}
📅 Дата регистрации: {reg_date}
    """
    
    await update.message.reply_text(
        profile_text,
        reply_markup=keyboard.get_profile_keyboard(),
        parse_mode='Markdown'
    )

async def show_profile_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает профиль из кнопки меню"""
    user = query.from_user
    
    stats = db.get_user_stats(user.id)
    
    if not stats:
        await query.message.reply_text("❌ Не удалось загрузить статистику")
        return
    
    limit, is_premium, total_cards, reg_date, subscription_end = stats
    
    # Формируем текст о подписке
    if subscription_end:
        subscription_text = f"✅ Активна до: {subscription_end}"
    else:
        subscription_text = "❌ Нет активной подписки"
    
    profile_text = f"""
👤 Ваш профиль

📊 Всего карт получено: {total_cards}
🎯 Лимит карт в день: {limit}
💎 Подписка: {subscription_text}
📅 Дата регистрации: {reg_date}
    """
    
    await query.message.reply_text(
        profile_text,
        reply_markup=keyboard.get_profile_keyboard(),
        parse_mode='Markdown'
    )


async def show_consult_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о консультации из кнопки меню"""
    # URL фото для консультации
    photo_url = "https://ibb.co/SXQR8ryT"  
    
    try:
        # Сначала отправляем фото
        await query.message.reply_photo(
            photo=photo_url,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error sending consult photo: {e}")
        # Если фото не загружается, продолжаем без него
    
    consult_text = """
💫Приветствую! Я Светлана Скромова, и я очень рада, что Вы сделали шаг к записи на консультацию. Если Вы здесь, значит, внутри уже есть готовность к важным переменам и внутренним трансформациям.

Я психотерапевт (магистр психологии, Москва) с более чем 7-летним опытом частной практики. Работаю онлайн с русскоговорящими клиентами по всему миру, создавая безопасное пространство, где мы вместе можем найти причину Ваших сложностей.

Какие вопросы мы можем решить:
🔸 Жизненные кризисы (утрата, развод, переезд)
🔸 Эмоциональное выгорание, депрессия, тревожность, апатия, стресс
🔸 Сложности в отношениях, эмоциональная зависимость, одиночество, страх отвержения/близости
🔸 Самооценка, неуверенность в себе, неумение говорить "нет"
🔸 Психологическое сопровождение в эмиграции (я сама прошла этот путь и знаю, как сложно строить жизнь с нуля)

⚓️ Мои инструменты: мультимодальный подход

🦋Моя работа — это не просто разговоры. Это глубинная и мягкая трансформация, где я использую проверенные и эффективные методы. Подбираю индивидуальные инструменты для каждого клиента.

💵 Стоимость и формат работы
Формат: Индивидуальная видео-консультация (WhatsApp, Telegram, Google Meet, Teams)

Продолжительность: 60 минут

Стоимость: 5500 ₽ (или 250₪). При оплате не из России происходит конвертация вашей валюты в шекели по банковскому курсу.

💎Первая консультация диагностическая (60-90 минут), чтобы мы могли познакомиться и наметить план дальнейшей работы. Я озвучу свое виденье вашей проблемы и инструменты для её решения.

Если Вы чувствуете отклик внутри и готовы к внутренним трансформациям - я буду рада стать Вашим проводником к изменениям 💛
"""
    
    # Отправляем текст консультации с кнопками
    await query.message.reply_text(
        consult_text,
        reply_markup=keyboard.get_consult_keyboard(),
        parse_mode='Markdown'
    )


async def show_daily_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает карту дня с кнопками"""
    user = query.from_user
    
    # ✅ Дополнительная проверка лимита
    can_take, reason = db.can_take_daily_card(user.id)
    if not can_take:
        await query.message.reply_text(f"❌ {reason}")
        return
    
    # ✅ Сразу убираем кнопку и показываем "загрузку"
    await query.edit_message_reply_markup(reply_markup=None)
    loading_message = await query.message.reply_text("🔄 Загружаем вашу карту дня...")
    
    try:
        # Получаем случайную карту
        card = db.get_random_card()
        if not card:
            await loading_message.edit_text("⚠️ Ошибка при получении карты.")
            return
        
        card_id, card_name, image_url, description = card
        
        # Сохраняем карту в контексте для вопросов
        context.user_data['last_card'] = {
            'card_id': card_id,
            'card_name': card_name,
            'image_url': image_url,
            'description': description
        }
        
        # Записываем карту пользователю
        db.record_user_card(user.id, card_id)
        
        
        try:
            # ✅ Удаляем сообщение "загрузка"
            await loading_message.delete()
            
            # ✅ Отправляем карту с кнопками "Вопросы к карте" и "Вернуться в меню"
            await query.message.reply_photo(
                photo=image_url,
                reply_markup=keyboard.get_card_display_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logging.error(f"❌ Error sending card image: {e}")
            await loading_message.edit_text("❌ Ошибка при загрузке изображения")
            # Если картинка не загружается, отправляем текстовое описание
            await query.message.reply_text(
                f"🎴 Карта дня: {card_name}\n\n(изображение временно недоступно)",
                reply_markup=keyboard.get_card_display_keyboard(),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logging.error(f"❌ Error in show_daily_card: {e}")
        await loading_message.edit_text("❌ Произошла ошибка при получении карты")


async def show_card_questions(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает вопросы для размышления над картой и убирает кнопки под картинкой"""
    user_data = context.user_data
    last_card = user_data.get('last_card', {})
    
    if not last_card:
        await query.message.reply_text(
            "❌ Информация о карте не найдена. Пожалуйста, получите новую карту дня.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    card_name = last_card.get('card_name', 'Карта')
    
    questions_text = f"""

👁 Посмотрите на карту, не торопитесь. Позвольте образу говорить с вами.

Опирайтесь на вопросы, которые помогут вам заглянуть внутрь себя и извлечь максимум смысла. Запишите ответы в свой блокнот для большего осознания ⤵️

🔹 *Состояние*: Какое состояние или чувство рождается внутри вас, когда вы смотрите на эту карту? Что вы чувствуете телом?

🔹 *Первый Отклик*: Какое слово или эмоция пришли к вам первыми? (Доверьтесь этой первой искре!)

🔹 *Путеводная Звезда*: Как символика карты (цвета, объекты) может стать ключом к решению вашего вопроса? О чём именно этот образ хочет вам сказать?

🔹 *Шаг вперед*: Какой самый первый, самый легкий шаг вы можете предпринять сегодня, вдохновившись этой картой?

*Помните*: В работе с метафорическими картами нет «правильных» ответов. Важен Ваш уникальный, личный смысл, рождающийся в момент встречи с образом."""
    
    # ✅ УДАЛЯЕМ кнопки под картинкой, редактируя предыдущее сообщение
    try:
        # Если предыдущее сообщение было с фото, убираем кнопки под ним
        if query.message.photo:
            await query.edit_message_reply_markup(reply_markup=None)
        
        # Отправляем новое сообщение с вопросами
        await query.message.reply_text(
            questions_text,
            reply_markup=keyboard.get_card_questions_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error in show_card_questions: {e}")
        # Если не удалось убрать кнопки, все равно отправляем вопросы
        await query.message.reply_text(
            questions_text,
            reply_markup=keyboard.get_card_questions_keyboard(),
            parse_mode='Markdown'
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 Доступные команды:

/daily - Получить карту дня
/resources - Архипелаг ресурсов 
/guide - Гайд по Эмоциональному Интеллекту
/buy - Купить колоду
/profile - Ваша статистика и лимиты
/history - Посмотреть историю всех ваших карт
/consult - Запись на консультацию
/message - Послание дня
/help - Эта справка

❓ Как это работает?
- Каждый день вы можете получить одну случайную карту
- Карта выбирается из колоды случайным образом
- Вы можете размышлять над значением карты в контексте вашей жизни

💡 Совет: Не пытайтесь анализировать карту слишком рационально. 
Дайте образу войти в ваше сознание, обратите внимание на первые мысли и чувства.
    """
    
    await update.message.reply_text(
        help_text,
        reply_markup=keyboard.get_help_keyboard(),
        parse_mode='Markdown'
    )

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
        history = db.get_user_card_history(user.id, limit=88)
        
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

🏆 Топ пользователей:
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


async def consult_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /consult - запись на консультацию"""
    # URL фото для консультации
    photo_url = "https://ibb.co/SXQR8ryT"  
    
    try:
        # Сначала отправляем фото
        await update.message.reply_photo(
            photo=photo_url,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error sending consult photo: {e}")
        # Если фото не загружается, продолжаем без него
    
    consult_text = """
💫Приветствую! Я Светлана Скромова, и я очень рада, что Вы сделали шаг к записи на консультацию. Если Вы здесь, значит, внутри уже есть готовность к важным переменам и внутренним трансформациям.

Я психотерапевт (магистр психологии, Москва) с более чем 7-летним опытом частной практики. Работаю онлайн с русскоговорящими клиентами по всему миру, создавая безопасное пространство, где мы вместе можем найти причину Ваших сложностей.

Какие вопросы мы можем решить:
🔸 Жизненные кризисы (утрата, развод, переезд)
🔸 Эмоциональное выгорание, депрессия, тревожность, апатия, стресс
🔸 Сложности в отношениях, эмоциональная зависимость, одиночество, страх отвержения/близости
🔸 Самооценка, неуверенность в себе, неумение говорить "нет"
🔸 Психологическое сопровождение в эмиграции (я сама прошла этот путь и знаю, как сложно строить жизнь с нуля)

⚓️ Мои инструменты: мультимодальный подход

🦋Моя работа — это не просто разговоры. Это глубинная и мягкая трансформация, где я использую проверенные и эффективные методы. Подбираю индивидуальные инструменты для каждого клиента.

💵 Стоимость и формат работы
Формат: Индивидуальная видео-консультация (WhatsApp, Telegram, Google Meet, Teams)

Продолжительность: 60 минут

Стоимость: 5500 ₽ (или 250₪). При оплате не из России происходит конвертация вашей валюты в шекели по банковскому курсу.

💎Первая консультация диагностическая (60-90 минут), чтобы мы могли познакомиться и наметить план дальнейшей работы. Я озвучу свое виденье вашей проблемы и инструменты для её решения.

Если Вы чувствуете отклик внутри и готовы к внутренним трансформациям - я буду рада стать Вашим проводником к изменениям 💛
"""
    
    # Отправляем текст консультации с кнопками
    await update.message.reply_text(
        consult_text,
        reply_markup=keyboard.get_consult_keyboard(),
        parse_mode='Markdown'
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню бота"""
    menu_text = """
🌊 О колоде и миссии бота

Море, как и наша жизнь, многолико: оно может быть ласковым, умиротворяющим, а порой — грозным и разрушительным. Этот образ идеально отражает внутренние состояния человека: от штиля до бури.

Каждая карта колоды пропитана энергией моря и создана для того, чтобы помочь вам:

Увидеть подсказки для решения жизненных ситуаций.

Наполниться ресурсами и энергией, которую несет в себе морская стихия.

Научиться распознавать свои эмоции и быть с ними в контакте.

Колода "Настроение как море" помогает заглянуть в глубину собственного бессознательного, осознать эмоции, встретиться с тем, что подавлено, и открыть новые ресурсы для роста.

✨ В добрый путь!
Я благодарю Вас за доверие и интерес к своему внутреннему миру.

Выбирайте в меню бота то, что для Вас сейчас наиболее актуально!

✨ Команды:
/daily - Получить карту дня
/resources - Архипелаг ресурсов 
/guide - Гайд по Эмоциональному Интеллекту
/buy - Купить колоду
/profile - Ваша статистика
/help - Помощь
/history - История ваших карт
/message - Послание дня
/consult - Запись на консультацию
"""
    
    # Если это callback query (нажатие кнопки), отправляем НОВОЕ сообщение
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(  # Отправляем новое сообщение, не редактируем
            menu_text,
            reply_markup=keyboard.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
    else:
        # Если это обычная команда, отправляем новое сообщение
        await update.message.reply_text(
            menu_text,
            reply_markup=keyboard.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )



async def show_history_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает историю из кнопки меню"""
    user = query.from_user
    
    try:
        history = db.get_user_card_history(user.id, limit=20)
        
        if not history:
            # Отправляем новое сообщение
            await query.message.reply_text(
                "📝 У вас пока нет истории карт.\n\nИспользуйте /daily чтобы получить первую карту!",
                reply_markup=keyboard.get_history_keyboard(),
                parse_mode='Markdown'
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
        
        history_text += "\n💫 Нажмите кнопку ниже чтобы увидеть картинки карт"
        
        # Отправляем новое сообщение с историей, не редактируя предыдущее
        await query.message.reply_text(
            history_text, 
            reply_markup=keyboard.get_history_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error in history from button: {e}")
        # Отправляем новое сообщение с ошибкой
        await query.message.reply_text(
            "⚠️ Ошибка при загрузке истории",
            reply_markup=keyboard.get_history_keyboard(),
            parse_mode='Markdown'
        )


async def show_history_pics_from_button(query, context: ContextTypes.DEFAULT_TYPE):

    """Показывает историю с картинками и кнопкой возврата"""
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
        
        # Отправляем сообщение с кнопкой "Вернуться в меню"
        await query.message.reply_text(
            "Ваши карты",
            reply_markup=keyboard.get_history_pics_keyboard(),  # Используем клавиатуру только с кнопкой возврата
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error in history album from query: {e}")
        await query.message.reply_text(
            "⚠️ Ошибка при загрузке истории с картинками",
            reply_markup=keyboard.get_history_pics_keyboard(),
            parse_mode='Markdown'
        )

async def resources_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /resources"""
    resources_text = """
🗺️ Архипелаг ресурсов

Извините, мы работаем над этой командой. В скором времени Вы сможете ею воспользоваться!
"""
    
    await update.message.reply_text(
        resources_text,
        reply_markup=keyboard.get_resources_keyboard(),
        parse_mode='Markdown'
    )

async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /guide"""
    try:
        file_id = "BQACAgIAAxkBAAIDwWj8b5ci3sQ1cngkY3N-bue4xshdAAKCfAACi0jhS_Jqr9GIbsvvNgQ"
        
        logging.info(f"🔄 Attempting to send guide with file_id: {file_id}")
        
        guide_text = """
📚 Гайд по Эмоциональному Интеллекту

Отправляю вам полезный гайд по развитию эмоционального интеллекта.
"""
        
        # Пробуем отправить документ
        result = await update.message.reply_document(
            document=file_id,
            filename="ГАЙД_по_развитию_эмоционального_интеллекта.pdf",
            caption=guide_text,
            reply_markup=keyboard.get_guide_keyboard(),
            parse_mode='Markdown'
        )
        
        logging.info(f"✅ Guide sent successfully! Message ID: {result.message_id}")
        
    except Exception as e:
        logging.error(f"❌ Error sending guide PDF: {e}")
        logging.error(f"❌ Error type: {type(e)}")
        logging.error(f"❌ Full traceback:", exc_info=True)
        
        error_text = """
📚 Гайд по Эмоциональному Интеллекту

К сожалению, файл временно недоступен. Пожалуйста, попробуйте позже.

Извините за неудобства!
"""
        await update.message.reply_text(
            error_text,
            reply_markup=keyboard.get_guide_keyboard(),
            parse_mode='Markdown'
        )

async def show_guide_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает гайд из кнопки меню"""
    try:
        file_id = "BQACAgIAAxkBAAIDwWj8b5ci3sQ1cngkY3N-bue4xshdAAKCfAACi0jhS_Jqr9GIbsvvNgQ"
        
        logging.info(f"🔄 Attempting to send guide from button with file_id: {file_id}")
        
        guide_text = """
📚 Гайд по Эмоциональному Интеллекту

Отправляю вам полезный гайд по развитию эмоционального интеллекта.
"""
        
        result = await query.message.reply_document(
            document=file_id,
            filename="ГАЙД_по_развитию_эмоционального_интеллекта.pdf",
            caption=guide_text,
            reply_markup=keyboard.get_guide_keyboard(),
            parse_mode='Markdown'
        )
        
        logging.info(f"✅ Guide from button sent successfully! Message ID: {result.message_id}")
        
    except Exception as e:
        logging.error(f"❌ Error sending guide PDF from button: {e}")
        logging.error(f"❌ Error type: {type(e)}")
        logging.error(f"❌ Full traceback:", exc_info=True)
        
        error_text = """
📚 Гайд по Эмоциональному Интеллекту

К сожалению, файл временно недоступен. Пожалуйста, попробуйте позже.

Извините за неудобства!
"""
        await query.message.reply_text(
            error_text,
            reply_markup=keyboard.get_guide_keyboard(),
            parse_mode='Markdown'
        )

async def show_resources_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ресурсы из кнопки меню"""
    resources_text = """
🗺️ Архипелаг ресурсов

Извините, мы работаем над этой командой. В скором времени Вы сможете ею воспользоваться!
"""
    
    await query.message.reply_text(
        resources_text,
        reply_markup=keyboard.get_resources_keyboard(),
        parse_mode='Markdown'
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /buy"""
    buy_text = """
🛒 Купить колоду

Извините, мы работаем над этой командой. В скором времени Вы сможете ею воспользоваться!
"""
    
    await update.message.reply_text(
        buy_text,
        reply_markup=keyboard.get_buy_keyboard(),
        parse_mode='Markdown'
    )

async def show_buy_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о покупке из кнопки меню"""
    buy_text = """
🛒 Купить колоду

Извините, мы работаем над этой командой. В скором времени Вы сможете ею воспользоваться!
"""
    
    await query.message.reply_text(
        buy_text,
        reply_markup=keyboard.get_buy_keyboard(),
        parse_mode='Markdown'
    )


async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для получения file_id последнего документа"""
    # Проверяем, был ли отправлен документ в этом чате
    user_id = update.effective_user.id
    if 'last_document' in context.chat_data:
        file_id = context.chat_data['last_document']['file_id']
        file_name = context.chat_data['last_document']['file_name']
        
        await update.message.reply_text(
            f"✅ Последний полученный документ:\n"
            f"📎 File ID: `{file_id}`\n"
            f"📄 File name: {file_name}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Документы не найдены.\n\n"
            "Как получить file_id:\n"
            "1. Отправьте PDF файл как 'File'\n"
            "2. Бот автоматически сохранит file_id\n"
            "3. Используйте /getfileid для просмотра"
        )

async def handle_any_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Автоматически обрабатывает любой отправленный документ"""
    if update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name or "Unknown"
        mime_type = update.message.document.mime_type or "Unknown"
        
        # Сохраняем информацию о документе в контексте чата
        context.chat_data['last_document'] = {
            'file_id': file_id,
            'file_name': file_name,
            'mime_type': mime_type
        }
        
        await update.message.reply_text(
            f"📎 Документ получен!\n"
            f"Имя: {file_name}\n"
            f"Тип: {mime_type}\n\n"
            f"✅ File ID сохранен! Используйте /getfileid чтобы посмотреть",
            parse_mode='Markdown'
        )
        
        # Логируем для отладки
        logging.info(f"Document received - File: {file_name}, MIME: {mime_type}, ID: {file_id}")

async def debug_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная информация о сообщении"""
    user_id = update.effective_user.id
    
    debug_info = f"""
🔍 Отладочная информация:

Тип сообщения: {update.message.content_type}
ID пользователя: {user_id}
Текст: {update.message.text or 'Нет текста'}
"""

    if update.message.document:
        document = update.message.document
        debug_info += f"""
📎 Документ:
- File ID: {document.file_id}
- Имя файла: {document.file_name or 'Неизвестно'}
- MIME тип: {document.mime_type or 'Неизвестно'}
- Размер: {document.file_size or 'Неизвестно'}
"""
    
    if 'last_document' in context.chat_data:
        last_doc = context.chat_data['last_document']
        debug_info += f"""
💾 Последний сохраненный документ:
- File ID: {last_doc['file_id']}
- Имя: {last_doc['file_name']}
- Тип: {last_doc['mime_type']}
"""


    await update.message.reply_text(debug_info, parse_mode='Markdown')


async def handle_subscription_selection(query, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа подписки"""
    subscription_type = query.data.replace("subscribe_", "")
    user_id = query.from_user.id
    
    price = SUBSCRIPTION_PRICES[subscription_type]
    duration = SUBSCRIPTION_NAMES[subscription_type]
    
    # Генерируем уникальную метку
    payment_label = payment_processor.generate_payment_label(user_id, subscription_type)
    
    # Сохраняем в контексте
    context.user_data['payment_label'] = payment_label
    context.user_data['subscription_type'] = subscription_type
    
    # Создаем ссылку для оплаты
    payment_url = payment_processor.create_payment_link(
        amount=price,
        label=payment_label,
        receiver=YOOMONEY_RECEIVER,
        targets=f"Подписка {duration} - Metaphor Bot"
    )
    
    payment_text = f"""
💎 Премиум подписка - {duration}

Стоимость: {price}₽

Нажмите кнопку "💳 Оплатить онлайн" для перехода к безопасной оплате.

После оплаты система автоматически активирует вашу подписку в течение 1-2 минут.

Если подписка не активировалась, нажмите "🔄 Проверить оплату".
"""
    
    await query.message.reply_text(
        payment_text,
        reply_markup=keyboard.get_payment_keyboard(subscription_type, payment_url),
        parse_mode='Markdown'
    )
    
    # Запускаем мониторинг платежа
    payment_processor.start_payment_monitoring(payment_label)

async def handle_payment_check(query, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет статус оплаты"""
    subscription_type = query.data.replace("check_payment_", "")
    user_id = query.from_user.id
    
    payment_label = context.user_data.get('payment_label')
    
    if not payment_label:
        await query.message.reply_text(
            "❌ Не найден активный платеж. Пожалуйста, начните процесс заново.",
            reply_markup=keyboard.get_subscription_choice_keyboard()
        )
        return
    
    # Проверяем статус подписки пользователя
    subscription = db.get_user_subscription(user_id)
    
    if subscription:
        # Подписка уже активирована
        success_text = f"""
✅ Подписка активирована!

Ваша премиум подписка успешно активирована.

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Архипелаг ресурсов

Наслаждайтесь полным доступом! 💫
"""
        await query.message.reply_text(
            success_text,
            reply_markup=keyboard.get_payment_success_keyboard(),
            parse_mode='Markdown'
        )
        
        # Очищаем данные о платеже
        if 'payment_label' in context.user_data:
            del context.user_data['payment_label']
            
    else:
        # Подписка еще не активирована
        await query.message.reply_text(
            "⏳ Платеж еще обрабатывается...\n\n"
            "Пожалуйста, подождите 1-2 минуты и проверьте снова.\n"
            "Если прошло больше времени, свяжитесь с @Skromova_Svetlana_psy",
            reply_markup=keyboard.get_payment_keyboard(subscription_type, "")
        )


async def handle_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /payment с deep links"""
    user = update.effective_user
    args = context.args
    
    if args and args[0].startswith('payment_'):
        payment_label = args[0].replace('payment_', '')
        
        # Проверяем статус подписки
        subscription = db.get_user_subscription(user.id)
        
        if subscription:
            success_text = """
✅ Оплата прошла успешно!

Ваша премиум подписка активирована.

✨ Теперь вам доступны все премиум-функции!
"""
            await update.message.reply_text(
                success_text,
                reply_markup=keyboard.get_payment_success_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "⏳ Ваш платеж обрабатывается...",
                reply_markup=keyboard.get_main_menu_keyboard()
            )
    else:
        # Если /payment без параметров, показываем информацию о подписке
        await subscribe_command(update, context)


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /subscribe"""
    subscription_text = """
💎 Премиум подписка

Откройте полный доступ к возможностям бота:

✨ **Что входит:**
• 5 карт дня вместо 1
• Послание дня (ежедневно)
• Доступ к Архипелагу ресурсов

🎯 **Тарифы:**
• 1 месяц - 99₽
• 3 месяца - 199₽
• 6 месяцев - 399₽ 
• 1 год - 799₽ 

Выберите срок подписки:
"""

    
    await update.message.reply_text(
        subscription_text,
        reply_markup=keyboard.get_subscription_keyboard(),
        parse_mode='Markdown'
    )

async def show_subscribe_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подписку из кнопки меню"""
    subscription_text = """
💎 Премиум подписка

Откройте полный доступ к возможностям бота:

✨ **Что входит:**
• 5 карт дня вместо 1
• Послание дня (ежедневно)
• Доступ к Архипелагу ресурсов

🎯 **Тарифы:**
• 1 месяц - 99₽
• 3 месяца - 199₽ 
• 6 месяцев - 399₽ 
• 1 год - 799₽

Выберите срок подписки:
"""

    
    await query.message.reply_text(
        subscription_text,
        reply_markup=keyboard.get_subscription_keyboard(),
        parse_mode='Markdown'
    )

# В handlers.py - обновляем функции для посланий

async def message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /message - Послание дня"""
    user = update.effective_user
    
    # Проверяем лимит посланий
    can_take, reason = db.can_take_daily_message(user.id)
    
    if not can_take:
        # Показываем статистику и информацию о лимитах
        stats = db.get_user_message_stats(user.id)
        if stats:
            if stats['has_subscription']:
                limit_text = f"❌ {reason}\n\n📊 Сегодня: {stats['today_count']}/5 посланий"
            else:
                if stats['can_take']:
                    limit_text = "✅ Можно взять послание (1 раз в неделю)"
                else:
                    limit_text = f"❌ {reason}\n\n📅 Следующее послание через {stats['days_until_next']} дней"
        else:
            limit_text = f"❌ {reason}"
        
        await update.message.reply_text(
            limit_text,
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    # Получаем случайное послание
    message_data = db.get_random_message()
    if not message_data:
        await update.message.reply_text(
            "⚠️ Ошибка при получении послания. Пожалуйста, попробуйте позже.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    message_id, image_url, message_text = message_data
    
    # Записываем факт получения послания
    db.record_user_message(user.id, message_id)
    
    message_caption = f'''🦋 Послание Дня

Прочитайте его и почувствуйте, какой отклик оно находит внутри вас:

🔹 Как реагирует ваше тело?
🔹 Какие эмоции поднимаются?
🔹 Что важного это послание несет вам?
🔹 Как это послание поможет вам на вашем жизненном пути?'''
    
    try:
        # Отправляем послание
        await update.message.reply_photo(
            photo=image_url,
            caption=message_caption,
            reply_markup=keyboard.get_daily_message_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error sending message image: {e}")
        # Если картинка не загружается, отправляем текстовую версию
        await update.message.reply_text(
            f"{message_caption}\n\n📝 *Текст послания:* {message_text}",
            reply_markup=keyboard.get_daily_message_keyboard(),
            parse_mode='Markdown'
        )

async def show_daily_message(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает послание дня при нажатии кнопки"""
    user = query.from_user
    
    # ✅ Сразу убираем кнопку "Послание дня"
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Проверяем лимит посланий
    can_take, reason = db.can_take_daily_message(user.id)
    
    if not can_take:
        # Показываем статистику и информацию о лимитах
        stats = db.get_user_message_stats(user.id)
        if stats:
            if stats['has_subscription']:
                limit_text = f"❌ {reason}\n\n📊 Сегодня: {stats['today_count']}/5 посланий"
            else:
                if stats['can_take']:
                    limit_text = "✅ Можно взять послание (1 раз в неделю)"
                else:
                    limit_text = f"❌ {reason}\n\n📅 Следующее послание через {stats['days_until_next']} дней"
        else:
            limit_text = f"❌ {reason}"
        
        await query.message.reply_text(
            limit_text,
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    # Получаем случайное послание
    message_data = db.get_random_message()
    if not message_data:
        await query.message.reply_text(
            "⚠️ Ошибка при получении послания. Пожалуйста, попробуйте позже.",
            reply_markup=keyboard.get_daily_message_keyboard()
        )
        return
    
    message_id, image_url, message_text = message_data
    
    # Записываем факт получения послания
    db.record_user_message(user.id, message_id)
    
    message_caption = f'''🦋 Послание Дня

Прочитайте его и почувствуйте, какой отклик оно находит внутри вас:

🔹 Как реагирует ваше тело?
🔹 Какие эмоции поднимаются?
🔹 Что важного это послание несет вам?
🔹 Как это послание поможет вам на вашем жизненном пути?'''
    
    try:
        # Отправляем новое сообщение с посланием
        await query.message.reply_photo(
            photo=image_url,
            caption=message_caption,
            reply_markup=keyboard.get_daily_message_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error sending message image: {e}")
        await query.message.reply_text(
            f"{message_caption}\n\n📝 *Текст послания:* {message_text}",
            reply_markup=keyboard.get_daily_message_keyboard(),
            parse_mode='Markdown'
        )

async def message_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус посланий пользователя с кнопками подписки"""
    user = update.effective_user
    
    stats = db.get_user_message_stats(user.id)
    if not stats:
        await update.message.reply_text("❌ Не удалось получить статистику посланий")
        return
    
    if stats['has_subscription']:
        status_text = f"""
📊 Статус ваших посланий (Премиум)

🎯 Лимит: 5 посланий в день
📨 Сегодня получено: {stats['today_count']}/5
🔄 Осталось сегодня: {stats['remaining']}

💫 Используйте кнопку 'Послание дня' в меню чтобы получить послание!
"""
        # Для премиум пользователей - только кнопка "Вернуться в меню"
        reply_markup = keyboard.get_main_menu_keyboard()
    else:
        if stats['can_take']:
            status_text = """
📊 Статус ваших посланий (Бесплатно)

🎯 Лимит: 1 послание в неделю
✅ Сейчас можно получить послание!

💫 Используйте кнопку 'Послание дня' в меню чтобы получить послание!
⚡ Или оформите подписку для доступа к 5 посланиям в день!
"""
            reply_markup = keyboard.get_main_menu_keyboard()
        else:
            status_text = f"""
📊 Статус ваших посланий (Бесплатно)

🎯 Лимит: 1 послание в неделю
⏳ Следующее послание через: {stats['days_until_next']} дней

⚡ Оформите подписку для доступа к 5 посланиям в день!
"""
            # Для бесплатных пользователей, которые не могут взять послание - кнопки "Приобрести подписку" и "Вернуться в меню"
            reply_markup = keyboard.get_message_status_keyboard()

    await update.message.reply_text(
        status_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def debug_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная команда для проверки лимитов посланий"""
    user = update.effective_user
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем информацию о пользователе
        cursor.execute('''
            SELECT user_id, is_premium, premium_until 
            FROM users 
            WHERE user_id = %s
        ''', (user.id,))
        user_data = cursor.fetchone()
        
        # Получаем историю посланий
        cursor.execute('''
            SELECT drawn_date 
            FROM user_messages 
            WHERE user_id = %s 
            ORDER BY drawn_date DESC 
            LIMIT 5
        ''', (user.id,))
        message_history = cursor.fetchall()
        
        # Проверяем лимит
        can_take, reason = db.can_take_daily_message(user.id)
        
        debug_text = f"""
🔍 Отладка лимитов посланий

👤 Пользователь: {user.id}
💎 Премиум: {user_data[1] if user_data else 'N/A'}
📅 Premium until: {user_data[2] if user_data else 'N/A'}
✅ Можно взять: {can_take}
📝 Причина: {reason}

📊 История посланий:
"""
        
        for i, (drawn_date,) in enumerate(message_history, 1):
            debug_text += f"{i}. {drawn_date}\n"
        
        if not message_history:
            debug_text += "Нет истории посланий"
        
        await update.message.reply_text(debug_text)
        conn.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка отладки: {e}")