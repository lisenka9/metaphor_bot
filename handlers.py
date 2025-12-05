from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import db 
from config import ADMIN_IDS
import logging
import keyboard
import csv
import io
from datetime import datetime, date
from yookassa_payment import payment_processor
from config import PAYMENT_LINKS, SUBSCRIPTION_PRICES, SUBSCRIPTION_NAMES, PAYPAL_PRICES, PAYPAL_LINKS
import uuid
import json

def get_video_system_safe():
    """Безопасно создает экземпляр video_system"""
    try:
        from secure_video import SecureVideoSystem
        from config import BASE_URL
        from database import db
        
        video_system = SecureVideoSystem(BASE_URL, db)
        logging.info("✅ Video system created successfully")
        return video_system
    except Exception as e:
        logging.error(f"❌ Error creating video system: {e}")
        return None

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
    
    photo_url = "https://ibb.co/dJgLgMCz" 
    
    try:
        # Сначала отправляем фото с коротким заголовком
        short_caption = f"{greeting}\n\nМеня зовут Светлана Скромова. Я практикующий психотерапевт и автор уникальной колоды метафорических карт «Настроение как море»."
        await update.message.reply_photo(
            photo=photo_url,
            caption=short_caption,
            parse_mode='Markdown'
        )
        
        # Затем отправляем полный текст отдельным сообщением
        welcome_text = f"""

Я - бот инструментов самопомощи, основанных на метафоре моря 🧜‍♀️

Каждый день ты будешь получать карту дня и послание дня, которые помогут задуматься о текущей ситуации. 

При помощи специальных упражнений ты проработаешь свои ограничения, прокачаешь эмоциональный интеллект и осознанность, усилишь свои внутренние ресурсы.

🎴 Карта дня - это случайная карта из колоды, которая может подсказать, на что обратить внимание сегодня.

💌Послание дня поможет глубже понять смысл карты.

🗺️Техники самопомощи - это техники, основанные на работе с метафорическими картами.

🎁А еще у меня для тебя подарок: гайд по эмоциональному интеллекту, который ты можешь скачать бесплатно!
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        # Если фото не загружается, отправляем только текст
        logging.error(f"Error sending photo: {e}")
        full_text = f"""
{greeting}

Меня зовут Светлана Скромова. Я практикующий эмоционально-образный терапевт и автор уникальной колоды метафорических карт "Настроение как море".

🌊 О колоде и миссии бота

Море, как и наша жизнь, многолико: оно может быть ласковым, умиротворяющим, а порой — грозным и разрушительным. Этот образ идеально отражает внутренние состояния человека: от штиля до бури.

Каждая карта колоды пропитана энергией моря и создана для того, чтобы помочь вам:

💎Увидеть подсказки для решения жизненных ситуаций.
💎Наполниться ресурсами и энергией, которую несет в себе морская стихия.
💎Научиться распознавать свои эмоции и быть с ними в контакте.
💎Осознать свои ограничения и отпустить их в морскую пучину.

Колода "Настроение как море" помогает заглянуть в глубину собственного бессознательного, осознать эмоции, встретиться с тем, что подавлено, и открыть новые ресурсы для роста.

🦋В добрый путь!
Я благодарю Вас за доверие и интерес к своему внутреннему миру.

Выбирайте в меню бота то, что для Вас сейчас наиболее актуально!
        """
        
        await update.message.reply_text(
            full_text,
            reply_markup=keyboard.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )

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
    logging.info(f"🔧 DEBUG: button_handler called with: {query.data}")
    
    # ✅ Защита от множественных нажатий
    user_id = query.from_user.id
    current_time = datetime.now().timestamp()
    
    if 'last_button_click' in context.user_data:
        last_click = context.user_data['last_button_click']
        if current_time - last_click < 1:  # 1 секунды между нажатиями
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
    
    elif query.data == "messages_command":
        await messages_command(update, context)
        
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
    
    elif query.data.startswith("resource_"):
        await handle_resource_technique(query, context)
        
    elif query.data == "tide_step1_card":
        await handle_tide_step1_card(query, context)
        
    elif query.data == "tide_step1_questions":
        await handle_tide_step1_questions(query, context)
        
    elif query.data == "tide_step2":
        await handle_tide_step2(query, context)
        
    elif query.data == "tide_step2_card":
        await handle_tide_step2_card(query, context)
        
    elif query.data == "tide_step2_questions":
        await handle_tide_step2_questions(query, context)

    elif query.data == "complete_tide_practice":
        await complete_tide_practice(query, context)
    
    elif query.data == "resource_tech2":
        await handle_storm_calm_technique(query, context)
        
    elif query.data == "storm_calm_step1_card":
        await handle_storm_calm_step1_card(query, context)
        
    elif query.data == "storm_calm_step2_lighthouse":
        await handle_storm_calm_step2_lighthouse(query, context)
        
    elif query.data == "storm_calm_complete":
        await handle_storm_calm_complete(query, context)
    
    elif query.data == "three_waves_step1":
        await handle_three_waves_step1(query, context)

    elif query.data == "three_waves_step1_card":
        await handle_three_waves_step1_card(query, context)

    elif query.data == "three_waves_step2":
        await handle_three_waves_step2(query, context)

    elif query.data == "three_waves_step2_card":
        await handle_three_waves_step2_card(query, context)

    elif query.data == "three_waves_step3":
        await handle_three_waves_step3(query, context)

    elif query.data == "three_waves_step3_card":
        await handle_three_waves_step3_card(query, context)
        
    elif query.data == "three_waves_complete":
        await handle_three_waves_complete(query, context)

    elif query.data == "guide":
        await show_guide_from_button(query, context)
    
    elif query.data == "report_problem":
        logging.info(f"📝 Report problem button clicked by user {user_id}")
        await show_report_problem_from_button(query, context)
        
    elif query.data == "start_report_form":
        logging.info(f"📝 Start report form clicked by user {user_id}")
        await start_report_form(query, context)
    
    elif query.data == "buy":
        await show_buy_from_button(query, context)
    
    elif query.data == "buy_deck_russia":
        await handle_buy_deck_russia(query, context)
        
    elif query.data == "buy_deck_international":
        await handle_buy_deck_international(query, context)
        
    elif query.data == "deck_payment_yookassa":
        await handle_buy_deck(query, context)
        
    elif query.data == "deck_payment_paypal":
        await handle_deck_payment_paypal(query, context)
        
    elif query.data.startswith("check_paypal_deck_"):
        await handle_paypal_deck_payment_check(query, context)

    elif query.data == "buy_deck":
        await handle_buy_deck(query, context)

    elif query.data.startswith("check_deck_payment_"):
        await handle_deck_payment_check(query, context)
    
    elif query.data == "meditation":
        await meditation_button_handler(query, context)
    
    elif query.data.startswith("subscribe_"):
        await handle_subscription_selection(update, context)

    elif query.data == "subscribe":
        await show_subscribe_from_button(query, context)

    elif query.data.startswith("payment_"):
        await handle_payment_method_selection(query, context)
        
    elif query.data.startswith("paypal_"):
        await handle_paypal_subscription_selection(update, context)
    
    elif query.data.startswith("check_paypal_"):
        await handle_paypal_payment_check(query, context)
    
    elif query.data.startswith("check_payment_"):
        await handle_payment_check(query, context)

    elif query.data.startswith("find_by_email_"):
        await handle_find_by_email(query, context)

    elif query.data.startswith("find_by_phone_"):
        await handle_find_by_phone(query, context)

    elif query.data.startswith("process_manually_"):
        await handle_process_manually(query, context)

    elif query.data.startswith("ignore_payment_"):
        await handle_ignore_payment(query, context)

    elif query.data.startswith("activate_for_"):
        await handle_activate_for_user(query, context)

    elif query.data.startswith("cancel_process_"):
        await handle_cancel_process(query, context)

    elif query.data == "show_unknown_payments":
        await show_unknown_payments(query, context)

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

💎Увидеть подсказки для решения жизненных ситуаций.

💎Наполниться ресурсами и энергией, которую несет в себе морская стихия.

💎Научиться распознавать свои эмоции и быть с ними в контакте.

💎Осознать свои ограничения и отпустить их в морскую пучину.

Колода "Настроение как море" помогает заглянуть в глубину собственного бессознательного, осознать эмоции, встретиться с тем, что подавлено, и открыть новые ресурсы для роста.

🦋В добрый путь!
Я благодарю Вас за доверие и интерес к своему внутреннему миру.

Выбирайте в меню бота то, что для Вас сейчас наиболее актуально!
"""
    
    # Отправляем новое сообщение с меню, не редактируя предыдущее
    await query.message.reply_text(
        menu_text,
        reply_markup=keyboard.get_main_menu_keyboard(),
        parse_mode='Markdown'
    )

async def show_daily_message(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает послание дня (описание последней карты) при нажатии кнопки"""
    user = query.from_user
    
    # ✅ СРАЗУ УБИРАЕМ КНОПКИ ПРИ НАЖАТИИ
    await query.edit_message_reply_markup(reply_markup=None)
    
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
                    limit_text = f"✅ Можно взять послание ({stats['remaining']} из 3 бесплатных осталось)"
                    reply_markup = keyboard.get_main_menu_keyboard()
                else:
                    limit_text = f"❌ {reason}\n\n💎 Оформите подписку для неограниченного доступа к посланиям!"
                    reply_markup = keyboard.get_message_status_keyboard()
        else:
            limit_text = f"❌ {reason}"
            reply_markup = keyboard.get_main_menu_keyboard()
        
        await query.message.reply_text(
            limit_text,
            reply_markup=reply_markup
        )
        return
    
    # ✅ ПОЛУЧАЕМ ОПИСАНИЕ ПОСЛЕДНЕЙ КАРТЫ ПОЛЬЗОВАТЕЛЯ
    card_description = db.get_last_user_card_description(user.id)
    
    if not card_description:
        await query.message.reply_text(
            "❌ Сначала получите карту дня, чтобы увидеть её послание!",
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    # ✅ ЗАПИСЫВАЕМ ФАКТ ПОЛУЧЕНИЯ ПОСЛАНИЯ
    # Используем ID последней карты как message_id
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT card_id FROM user_cards 
        WHERE user_id = %s 
        ORDER BY drawn_date DESC 
        LIMIT 1
    ''', (user.id,))
    last_card_result = cursor.fetchone()
    conn.close()
    
    if last_card_result:
        last_card_id = last_card_result[0]
        success = db.record_user_message(user.id, last_card_id)
        if not success:
            logging.error(f"❌ Failed to record message for user {user.id}")
    
    # ✅ ОТПРАВЛЯЕМ ТОЛЬКО ТЕКСТ ОПИСАНИЯ БЕЗ КАРТИНКИ И С КНОПКОЙ "ВЕРНУТЬСЯ В МЕНЮ"
    await query.message.reply_text(
        card_description,
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
    
    subscription = db.get_user_subscription(user.id)
    has_resources_access = subscription and subscription[1] and subscription[1].date() >= date.today()

    # Формируем текст о подписке
    if subscription_end:
        subscription_text = f"✅ Активна до: {subscription_end}"
    else:
        subscription_text = "❌ Нет активной подписки"
    
    profile_text = f"""
👤 Ваш профиль

📊 Всего карт получено: {total_cards}
💎 Подписка: {subscription_text}
🎯 Лимит карт в день: {limit}
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
    
    subscription = db.get_user_subscription(user.id)
    has_resources_access = subscription and subscription[1] and subscription[1].date() >= date.today()
    
    # Формируем текст о подписке
    if subscription_end:
        subscription_text = f"✅ Активна до: {subscription_end}"
    else:
        subscription_text = "❌ Нет активной подписки"
    
    profile_text = f"""
👤 Ваш профиль

📊 Всего карт получено: {total_cards}
💎 Подписка: {subscription_text}
🎯 Лимит карт в день: {limit}
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
    """Показывает карту дня с текстом ограничения/возможности в одном сообщении"""
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
        
        # ✅ Определяем тип карты (Ограничение или Возможность)
        card_type = "Ограничение" if 1 <= card_id <= 88 else "Возможность"
        
        # ✅ Определяем текст в зависимости от типа карты
        if card_type == "Ограничение":
            card_text = """
⚡️ ОГРАНИЧЕНИЕ ДНЯ ⚡️

Сегодняшняя карта дня указывает на Ограничение.

Этот образ может символизировать потенциальную преграду, внутренний блок или ситуацию, требующую внимания. ⚠️

❓ Посмотрите на карту и ответьте на вопрос: Как вы можете встретиться с этим ограничением? Что поможет его преодолеть или принять?

➡️ Помните: в ограничении скрыт урок этого дня. 🧭
"""
        else:  # Возможность
            card_text = """
✨ ВОЗМОЖНОСТЬ ДНЯ ✨

Сегодняшний день несет для вас Новый Потенциал! 🌊

Обратите внимание на изображение на карту — он указывает на ресурс или новые возможности в вашей жизни. 🧭

❓ Посмотрите на карту и ответьте на вопрос: Что вы можете сделать или использовать сегодня, чтобы максимально раскрыть возможности этого дня? 

➡️ Помните: это ваша главная точка роста! 🌱
"""
        
        try:
            # ✅ Удаляем сообщение "загрузка"
            await loading_message.delete()
            
            # ✅ Отправляем карту с текстом и кнопками в одном сообщении
            caption = f"{card_text}"
            
            await query.message.reply_photo(
                photo=image_url,
                caption=caption,
                reply_markup=keyboard.get_card_display_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logging.error(f"❌ Error sending card image: {e}")
            await loading_message.edit_text("❌ Ошибка при загрузке изображения")
            
            # Если картинка не загрузжается, отправляем только текст
            await query.message.reply_text(
                f"{card_text}\n\n🎴 Карта дня: **{card_type}**\n\n(изображение временно недоступно)",
                reply_markup=keyboard.get_card_display_keyboard(),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logging.error(f"❌ Error in show_daily_card: {e}")
        await loading_message.edit_text("❌ Произошла ошибка при получении карты")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 Доступные команды:

/daily - Получить карту дня
/messages - Послание дня
/resources - Техники самопомощи
/guide - Гайд по Эмоциональному Интеллекту
/buy - Купить цифровую колоду 
/profile - Ваша статистика и лимиты
/history - Посмотреть историю всех ваших карт
/consult - Запись на консультацию
/subscribe - Приобрести подписку
/meditation - Медитация "Дары Моря"
/report - Сообщить о проблеме
/help - Эта справка
    """
    
    await update.message.reply_text(
        help_text,
        reply_markup=keyboard.get_help_keyboard(),
        parse_mode='Markdown'
    )

async def reset_my_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает лимиты карт для администратора (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        from datetime import date
        import logging
        
        logging.info(f"🔄 Resetme command by admin {user.id}")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # ✅ ПРОВЕРЯЕМ СТРУКТУРУ ТАБЛИЦЫ
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user_cards' 
            AND table_schema = 'public'
        """)
        columns = cursor.fetchall()
        logging.info(f"📋 user_cards columns: {columns}")
        
        # ✅ ПОЛНОСТЬЮ СБРАСЫВАЕМ ИСТОРИЮ КАРТ ЗА СЕГОДНЯ
        today = date.today()
        logging.info(f"📅 Today date: {today}")
        
        cursor.execute('''
            SELECT COUNT(*) FROM user_cards 
            WHERE user_id = %s AND DATE(drawn_date) = %s
        ''', (user.id, today))
        
        cards_before = cursor.fetchone()[0]
        logging.info(f"📊 Cards before reset: {cards_before}")
        
        cursor.execute('''
            DELETE FROM user_cards 
            WHERE user_id = %s AND DATE(drawn_date) = %s
        ''', (user.id, today))
        
        deleted_cards = cursor.rowcount
        logging.info(f"🗑️ Deleted cards: {deleted_cards}")
        
        # ✅ СБРАСЫВАЕМ ДАТУ ПОСЛЕДНЕЙ КАРТЫ
        cursor.execute('''
            UPDATE users 
            SET last_daily_card_date = NULL 
            WHERE user_id = %s
        ''', (user.id,))
        
        updated_users = cursor.rowcount
        logging.info(f"👤 Updated users: {updated_users}")
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ Ваши лимиты полностью сброшены!\n"
            f"🗑️ Удалено карт за сегодня: {deleted_cards}\n"
            f"🎯 Теперь вы можете получить до 5 карт (премиум лимит)"
        )
        
    except Exception as e:
        logging.error(f"❌ Error resetting limit: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка при сбросе лимита: {str(e)}")

async def reset_simple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Простая версия сброса лимитов"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # ✅ ПРОСТО СБРАСЫВАЕМ ДАТУ БЕЗ УДАЛЕНИЯ КАРТ
        cursor.execute('''
            UPDATE users 
            SET last_daily_card_date = NULL 
            WHERE user_id = %s
        ''', (user.id,))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ Дата последней карты сброшена!")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

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

💎Увидеть подсказки для решения жизненных ситуаций.

💎Наполниться ресурсами и энергией, которую несет в себе морская стихия.

💎Научиться распознавать свои эмоции и быть с ними в контакте.

💎Осознать свои ограничения и отпустить их в морскую пучину.

Колода "Настроение как море" помогает заглянуть в глубину собственного бессознательного, осознать эмоции, встретиться с тем, что подавлено, и открыть новые ресурсы для роста.

🦋В добрый путь!
Я благодарю Вас за доверие и интерес к своему внутреннему миру.

Выбирайте в меню бота то, что для Вас сейчас наиболее актуально!
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

async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /guide"""
    try:
        file_id = "BQACAgIAAxkBAAIPyWksJ2oB7zWcPGDuD4Y10SFMGxW4AAIRiAACi_RhSZpuTPvDNakwNgQ"
        
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
        file_id = "BQACAgIAAxkBAAIPyWksJ2oB7zWcPGDuD4Y10SFMGxW4AAIRiAACi_RhSZpuTPvDNakwNgQ"
        
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

async def show_buy_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о покупке из кнопки меню"""
    buy_text = """
🛒 Купить цифровую колоду 

Извините, мы работаем над этой командой. В скором времени Вы сможете ею воспользоваться!
"""
    
    await query.message.reply_text(
        buy_text,
        reply_markup=keyboard.get_buy_keyboard(),
        parse_mode='Markdown'
    )


async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для получения file_id последнего документа"""
    user_id = update.effective_user.id
    
    # Добавим отладочную информацию
    logging.info(f"🔍 get_file_id called by user {user_id}")
    logging.info(f"🔍 chat_data keys: {list(context.chat_data.keys())}")
    
    if 'last_document' in context.chat_data:
        file_info = context.chat_data['last_document']
        file_id = file_info['file_id']
        file_name = file_info['file_name']
        
        await update.message.reply_text(
            f"✅ Последний полученный документ:\n"
            f"📎 File ID: {file_id}\n"
            f"📄 File name: {file_name}",
            parse_mode=None  # Без Markdown
        )
        
        # Также покажем в логах
        logging.info(f"✅ Found file: {file_name}, ID: {file_id}")
    else:
        await update.message.reply_text(
            "❌ Документы не найдены в контексте.\n\n"
            "Как получить file_id:\n"
            "1. Отправьте PDF файл как 'File'\n"
            "2. Бот автоматически сохранит file_id\n"
            "3. Используйте /getfileid для просмотра",
            parse_mode=None
        )
        logging.warning("❌ No documents found in chat_data")

async def handle_any_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Автоматически обрабатывает любой отправленный документ"""
    try:
        if update.message and update.message.document:
            file_id = update.message.document.file_id
            file_name = update.message.document.file_name or "Unknown"
            mime_type = update.message.document.mime_type or "Unknown"
            file_size = update.message.document.file_size or 0
            
            # Экранируем имя файла для Markdown
            safe_file_name = file_name.replace('_', '\\_').replace('-', '\\-').replace('.', '\\.')
            
            # Сохраняем в контексте чата (последний файл)
            context.chat_data['last_document'] = {
                'file_id': file_id,
                'file_name': file_name,
                'mime_type': mime_type,
                'file_size': file_size
            }
            
            # Сохраняем в bot_data (все файлы)
            if 'saved_files' not in context.bot_data:
                context.bot_data['saved_files'] = []
            
            # Добавляем файл если его еще нет
            if not any(f['file_id'] == file_id for f in context.bot_data['saved_files']):
                context.bot_data['saved_files'].append({
                    'file_id': file_id,
                    'file_name': file_name,
                    'mime_type': mime_type,
                    'file_size': file_size,
                    'uploaded_at': datetime.now().isoformat()
                })
            
            logging.info(f"📎 DOCUMENT RECEIVED - File: {file_name}, Size: {file_size}, MIME: {mime_type}, ID: {file_id}")
            
            # Отправляем сообщение БЕЗ Markdown разметки
            await update.message.reply_text(
                f"📎 Документ получен!\n"
                f"📄 Имя: {file_name}\n"
                f"📊 Размер: {file_size} байт\n"
                f"🔧 Тип: {mime_type}\n"
                f"🆔 ID: {file_id}\n\n"
                f"✅ File ID сохранен!\n"
                f"Используйте:\n"
                f"• /getfileid - последний файл\n"
                f"• /getallfiles - все файлы"
                # Убрали parse_mode='Markdown'
            )
            
        else:
            logging.warning("❌ Document message but no document found")
            
    except Exception as e:
        logging.error(f"❌ Error in handle_any_document: {e}")
        # Отправляем простой текст без разметки
        await update.message.reply_text("❌ Ошибка при обработке документа")

async def get_all_file_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все сохраненные file_id"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    # Отладочная информация
    logging.info(f"🔍 get_all_file_ids called by admin {user.id}")
    logging.info(f"🔍 bot_data keys: {list(context.bot_data.keys())}")
    
    if 'saved_files' not in context.bot_data:
        context.bot_data['saved_files'] = []
    
    if not context.bot_data['saved_files']:
        await update.message.reply_text("📭 Нет сохраненных файлов в bot_data.")
        logging.warning("❌ No saved_files in bot_data")
        return
    
    message = "📋 Сохраненные файлы:\n\n"
    for i, file_info in enumerate(context.bot_data['saved_files'], 1):
        message += f"{i}. {file_info['file_id']}\n"
        message += f"   📄 {file_info['file_name']}\n"
        message += f"   🔧 {file_info['mime_type']}\n"
        message += f"   📊 {file_info.get('file_size', 'N/A')} байт\n\n"
    
    await update.message.reply_text(message, parse_mode=None)
    logging.info(f"✅ Sent {len(context.bot_data['saved_files'])} file IDs to admin")

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

✨ Что входит:
• 5 карт дня вместо 1
• Послание дня (ежедневно)
• Доступ к 3 техникам самопомощи «Техники самопомощи»
• Медитация «Дары моря»

🎯 Тарифы:
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
    """Показывает выбор платежной системы"""
    subscription_text = """
💎 Премиум подписка

Выберите способ оплаты:

🇷🇺 *Оплата из России* (рубли)
🌍 *Оплата из любой точки мира* (шекели)

Обе системы обеспечивают безопасную оплату и мгновенную активацию подписки.
"""
    
    await query.message.reply_text(
        subscription_text,
        reply_markup=keyboard.get_payment_method_keyboard(),
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

🎯 Лимит: 3 послания за всё время
❌ Использовано: {stats['total_count']}/3

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
            SELECT um.drawn_date, dm.message_text 
            FROM user_messages um
            LEFT JOIN daily_messages dm ON um.message_id = dm.message_id
            WHERE um.user_id = %s 
            ORDER BY um.drawn_date DESC 
            LIMIT 5
        ''', (user.id,))
        message_history = cursor.fetchall()
        
        # Проверяем количество посланий в базе
        cursor.execute('SELECT COUNT(*) FROM daily_messages')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM user_messages WHERE user_id = %s', (user.id,))
        user_messages_count = cursor.fetchone()[0]
        
        # Проверяем лимит
        can_take, reason = db.can_take_daily_message(user.id)
        
        debug_text = f"""
🔍 Отладка лимитов посланий

👤 Пользователь: {user.id}
💎 Премиум: {user_data[1] if user_data else 'N/A'}
📅 Premium until: {user_data[2] if user_data else 'N/A'}
✅ Можно взять: {can_take}
📝 Причина: {reason}

📊 Статистика:
• Всего посланий в базе: {total_messages}
• Ваших посланий в истории: {user_messages_count}

📋 История ваших посланий:
"""
        
        for i, (drawn_date, message_text) in enumerate(message_history, 1):
            date_str = drawn_date.strftime("%Y-%m-%d %H:%M") if hasattr(drawn_date, 'strftime') else str(drawn_date)
            debug_text += f"{i}. {date_str} - {message_text[:30]}...\n"
        
        if not message_history:
            debug_text += "Нет истории посланий"
        
        await update.message.reply_text(debug_text)
        conn.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка отладки: {e}")

async def init_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительно создает тестовые послания в базе"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Создаем таблицу
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_messages (
                message_id SERIAL PRIMARY KEY,
                image_url TEXT NOT NULL,
                message_text TEXT NOT NULL
            )
        ''')
        
        # Очищаем таблицу
        cursor.execute('DELETE FROM daily_messages')
        
        # Добавляем тестовые послания
        daily_messages = [
            (1, "https://ibb.co/wZd8BTHM", "Послание 1"),
            (2, "https://ibb.co/PGWbXCyP", "Послание 2")
        ]
        
        for message_id, image_url, message_text in daily_messages:
            cursor.execute('''
                INSERT INTO daily_messages (message_id, image_url, message_text)
                VALUES (%s, %s, %s)
            ''', (message_id, image_url, message_text))
        
        conn.commit()
        
        await update.message.reply_text(f"✅ Создано {len(daily_messages)} тестовых посланий в базе данных")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def reset_message_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс лимита посланий дня (для администратора)"""
    user = update.effective_user
    
    # Проверяем, является ли пользователь администратором
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем аргументы команды (если указан конкретный пользователь)
        target_user_id = user.id  # по умолчанию сбрасываем себе
        
        if context.args:
            try:
                target_user_id = int(context.args[0])
                logging.info(f"🔄 Admin {user.id} resetting message limit for user {target_user_id}")
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID пользователя")
                return
        
        # Удаляем историю посланий пользователя
        cursor.execute('DELETE FROM user_messages WHERE user_id = %s', (target_user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if target_user_id == user.id:
            await update.message.reply_text(f"✅ Ваш лимит посланий сброшен! Удалено {deleted_count} записей.")
        else:
            await update.message.reply_text(f"✅ Лимит посланий пользователя {target_user_id} сброшен! Удалено {deleted_count} записей.")
        
    except Exception as e:
        logging.error(f"❌ Error resetting message limit: {e}")
        await update.message.reply_text("❌ Ошибка при сбросе лимита посланий")

async def handle_subscription_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа подписки"""
    query = update.callback_query
    await query.answer()
    
    try:
        subscription_type = query.data.replace("subscribe_", "")
        user_id = query.from_user.id
        
        logging.info(f"🔄 Subscription selected: {subscription_type} by user {user_id}")
        
        # ✅ ЛОГИРУЕМ ДЕЙСТВИЕ ПОЛЬЗОВАТЕЛЯ В БАЗУ ДАННЫХ
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Создаем таблицу если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_action_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    action TEXT,
                    action_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO user_action_logs (user_id, action, action_data)
                VALUES (%s, %s, %s)
            ''', (user_id, 'subscription_selected', subscription_type))
            
            conn.commit()
            conn.close()
            logging.info(f"✅ User action logged for {user_id}")
        except Exception as log_error:
            logging.error(f"❌ Error logging user action: {log_error}")
        
        if subscription_type not in SUBSCRIPTION_PRICES:
            await query.message.reply_text(
                "❌ Ошибка: выбран неверный тип подписки.",
                reply_markup=keyboard.get_main_menu_keyboard()
            )
            return
        
        price = SUBSCRIPTION_PRICES[subscription_type]
        duration = SUBSCRIPTION_NAMES[subscription_type]
        
        # ИСПОЛЬЗУЕМ СТАТИЧЕСКИЕ ССЫЛКИ (как раньше)
        payment_url = PAYMENT_LINKS.get(subscription_type)
        
        if not payment_url:
            await query.message.reply_text(
                "❌ Ошибка: ссылка для оплаты не найдена. Свяжитесь с администратором.",
                reply_markup=keyboard.get_main_menu_keyboard()
            )
            return
        
        # Генерируем простой payment_id
        payment_id = f"{subscription_type}_{user_id}_{int(datetime.now().timestamp())}"
        
        # Сохраняем в контексте
        context.user_data['payment_id'] = payment_id
        context.user_data['subscription_type'] = subscription_type
        
        payment_text = f"""
💎 Премиум подписка - {duration}

Стоимость: {price}₽

Нажмите кнопку "💳 Оплатить онлайн" для перехода к оплате.

После успешной оплаты подписка активируется автоматически в течение 1-2 минут.

Если подписка не активировалась, нажмите "🔄 Проверить оплату".
"""
        
        await query.message.reply_text(
            payment_text,
            reply_markup=keyboard.get_payment_keyboard(subscription_type, payment_url, payment_id),
            parse_mode='Markdown'
        )
        
        logging.info(f"✅ Payment message sent for user {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Error in handle_subscription_selection: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка при создании платежа. Попробуйте позже.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )

def save_user_action(user_id: int, action_type: str, action_data: dict):
    """Сохраняет действие пользователя для идентификации"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Создаем таблицу если не существует
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                action_type TEXT,
                action_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            INSERT INTO user_actions (user_id, action_type, action_data)
            VALUES (%s, %s, %s)
        ''', (user_id, action_type, json.dumps(action_data)))
        
        conn.commit()
        conn.close()
        logging.info(f"✅ User action saved: {action_type} for user {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Error saving user action: {e}")

async def handle_payment_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет статус оплаты"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    payment_id = context.user_data.get('payment_id')
    subscription_type = context.user_data.get('subscription_type')
    
    # ✅ СНАЧАЛА ПРОВЕРЯЕМ БАЗУ ДАННЫХ
    payment_info = payment_processor.find_user_payment(user_id)
    if payment_info and payment_info['status'] == 'success':
        # Подписка уже активирована
        success_text = f"""
✅ Подписка активирована!

Ваша премиум подписка успешно активирована {payment_info['payment_date'].strftime('%d.%m.%Y в %H:%M')}.

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Техники самопомощи

Наслаждайтесь полным доступом! 💫
"""
        await query.message.reply_text(
            success_text,
            reply_markup=keyboard.get_payment_success_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if not payment_id:
        await query.message.reply_text(
            "❌ Не найден активный платеж. Пожалуйста, начните процесс заново.",
            reply_markup=keyboard.get_subscription_choice_keyboard()
        )
        return
    
    # Проверяем статус платежа через API
    payment_status = payment_processor.check_payment_status(payment_id)
    
    if payment_status is True:
        # Платеж подтвержден, активируем подписку
        if payment_processor.activate_subscription(payment_id):
            success_text = f"""
✅ Оплата подтверждена!

Ваша премиум подписка активирована.

✨ Теперь вам доступны все премиум-функции!
"""
            await query.message.reply_text(
                success_text,
                reply_markup=keyboard.get_payment_success_keyboard(),
                parse_mode='Markdown'
            )
            
            # Очищаем данные о платеже
            if 'payment_id' in context.user_data:
                del context.user_data['payment_id']
        else:
            await query.message.reply_text(
                "❌ Ошибка при активации подписки. Свяжитесь с администратором.",
                reply_markup=keyboard.get_main_menu_keyboard()
            )
            
    elif payment_status is False:
        await query.message.reply_text(
            "❌ Платеж не прошел или был отменен. Попробуйте оплатить снова.",
            reply_markup=keyboard.get_subscription_choice_keyboard()
        )
    else:
        # Платеж еще обрабатывается
        await query.message.reply_text(
            "⏳ Платеж еще обрабатывается...\n\n"
            "Пожалуйста, подождите 1-2 минуты и проверьте снова.",
            reply_markup=keyboard.get_payment_check_keyboard(subscription_type, payment_id)
        )

async def handle_start_with_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает deep link после успешной оплаты подписки"""
    user = update.effective_user
    args = context.args
    
    if not args:
        return
        
    # Обработка успешной оплаты через ЮKassa
    if args[0] == 'payment_success':
        # Проверяем, есть ли у пользователя активная подписка
        subscription = db.get_user_subscription(user.id)
        
        if subscription:
            subscription_type, end_date = subscription
            
            # Форматируем дату окончания подписки
            if hasattr(end_date, 'strftime'):
                end_date_str = end_date.strftime('%d.%m.%Y')
            else:
                end_date_str = str(end_date)[:10]
            
            success_text = f"""
✅ Оплата прошла успешно!

Ваша премиум подписка активирована.

📅 Действует до: {end_date_str}

✨ Теперь вам доступны все премиум-функции:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Техники самопомощи
• Медитация «Дары Моря»

Наслаждайтесь полным доступом! 💫
"""
            await update.message.reply_text(
                success_text,
                reply_markup=keyboard.get_payment_success_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "⏳ Ваш платеж обрабатывается...\n\n"
                "Подписка будет активирована в течение 1-2 минут.\n\n"
                "Если прошло больше времени:\n"
                "• Используйте команду /subscribe для проверки статуса\n"
                "• Или нажмите кнопку '🔄 Проверить оплату' в предыдущем сообщении",
                reply_markup=keyboard.get_main_menu_keyboard()
            )
    
    # Обработка успешной оплаты через PayPal
    elif args[0].startswith('paypal_success_'):
        payment_id = args[0].replace('paypal_success_', '')
        
        # Проверяем статус подписки
        subscription = db.get_user_subscription(user.id)
        
        if subscription:
            subscription_type, end_date = subscription
            
            # Форматируем дату окончания подписки
            if hasattr(end_date, 'strftime'):
                end_date_str = end_date.strftime('%d.%m.%Y')
            else:
                end_date_str = str(end_date)[:10]
            
            success_text = f"""
✅ Оплата прошла успешно!

Ваша премиум подписка активирована.

📅 Действует до: {end_date_str}

✨ Теперь вам доступны все премиум-функции:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Техники самопомощи
• Медитация «Дары Моря»

Наслаждайтесь полным доступом! 💫
"""
            await update.message.reply_text(
                success_text,
                reply_markup=keyboard.get_payment_success_keyboard(),
                parse_mode='Markdown'
            )
        else:
            # Проверяем статус PayPal платежа напрямую
            try:
                from paypal_payment import paypal_processor
                payment_status = paypal_processor.check_payment_status(payment_id)
                
                if payment_status is True:
                    # Активируем подписку
                    if paypal_processor.activate_subscription(payment_id):
                        subscription = db.get_user_subscription(user.id)
                        if subscription:
                            subscription_type, end_date = subscription
                            
                            if hasattr(end_date, 'strftime'):
                                end_date_str = end_date.strftime('%d.%m.%Y')
                            else:
                                end_date_str = str(end_date)[:10]
                            
                            success_text = f"""
✅ Оплата подтверждена!

Ваша премиум подписка активирована.

📅 Действует до: {end_date_str}

✨ Теперь вам доступны все премиум-функции!
"""
                            await update.message.reply_text(
                                success_text,
                                reply_markup=keyboard.get_payment_success_keyboard(),
                                parse_mode='Markdown'
                            )
                            return
                
                await update.message.reply_text(
                    "⏳ Ваш платеж обрабатывается...\n\n"
                    "Подписка будет активирована в течение 1-2 минут.\n\n"
                    "Если прошло больше времени:\n"
                    "• Используйте команду /subscribe для проверки статуса\n"
                    "• Или нажмите кнопку '🔄 Проверить оплату' в предыдущем сообщении",
                    reply_markup=keyboard.get_main_menu_keyboard()
                )
                
            except Exception as e:
                logging.error(f"❌ Error checking PayPal payment: {e}")
                await update.message.reply_text(
                    "⏳ Ваш платеж обрабатывается...\n\n"
                    "Если подписка не активировалась в течение 5 минут, "
                    "пожалуйста, свяжитесь с поддержкой.",
                    reply_markup=keyboard.get_main_menu_keyboard()
                )
    
    # Обработка отмены оплаты через PayPal
    elif args[0] == 'paypal_cancel':
        await update.message.reply_text(
            "❌ Оплата была отменена.\n\n"
            "Вы можете попробовать снова или выбрать другой способ оплаты.",
            reply_markup=keyboard.get_payment_method_keyboard()
        )
    
    # Обработка успешной оплаты колоды (оставляем для полноты, но это отдельная функция)
    elif args[0] == 'deck_purchase_success':
        # Проверяем, есть ли у пользователя покупка колоды
        if db.has_purchased_deck(user.id):
            await send_deck_files(update, context, user.id)
        else:
            await update.message.reply_text(
                "⏳ Ваш платеж за колоду обрабатывается...\n\n"
                "Файлы будут отправлены в течение 1-2 минут.\n\n"
                "Если прошло больше времени:\n"
                "• Используйте команду /buy для проверки статуса\n"
                "• Или нажмите кнопку '🔄 Проверить оплату' в предыдущем сообщении",
                reply_markup=keyboard.get_buy_keyboard()
            )

async def update_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет структуру базы данных"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        # Добавляем недостающие колонки
        db.add_payment_id_column()
        await update.message.reply_text("✅ База данных обновлена! Добавлена колонка payment_id")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def check_subscription_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущий статус подписки и лимиты"""
    user = update.effective_user
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.daily_cards_limit, u.is_premium, u.premium_until,
                   COUNT(uc.id) as today_cards,
                   (SELECT COUNT(*) FROM user_cards WHERE user_id = %s AND DATE(drawn_date) = CURRENT_DATE) as today_count
            FROM users u
            LEFT JOIN user_cards uc ON u.user_id = uc.user_id AND DATE(uc.drawn_date) = CURRENT_DATE
            WHERE u.user_id = %s
            GROUP BY u.user_id, u.daily_cards_limit, u.is_premium, u.premium_until
        ''', (user.id, user.id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            limit, is_premium, premium_until, today_cards, today_count = result
            
            status_text = f"""
📊 Статус вашей подписки:

🎯 Лимит карт в день: {limit}
💎 Премиум статус: {'✅ Активен' if is_premium else '❌ Неактивен'}
📅 Подписка до: {premium_until.strftime('%d.%m.%Y') if premium_until else 'Неактивна'}
📨 Карт получено сегодня: {today_count or 0}/{limit}

"""
            
            if is_premium and limit == 1:
                status_text += "\n⚠️ *Внимание:* У вас премиум подписка, но лимит карт не обновлен!\nИспользуйте /fix_limit для исправления."
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Не удалось получить информацию о подписке")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def fix_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Исправляет лимит карт для премиум пользователей"""
    user = update.effective_user
    
    try:
        from config import DAILY_CARD_LIMIT_PREMIUM
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Проверяем, есть ли активная подписка
        cursor.execute('''
            SELECT is_premium, premium_until 
            FROM users 
            WHERE user_id = %s AND is_premium = TRUE AND premium_until >= CURRENT_DATE
        ''', (user.id,))
        
        result = cursor.fetchone()
        
        if result:
            # Обновляем лимит
            cursor.execute('''
                UPDATE users 
                SET daily_cards_limit = %s 
                WHERE user_id = %s
            ''', (DAILY_CARD_LIMIT_PREMIUM, user.id))
            
            conn.commit()
            await update.message.reply_text(f"✅ Лимит карт обновлен! Теперь вам доступно {DAILY_CARD_LIMIT_PREMIUM} карт в день.")
        else:
            await update.message.reply_text("❌ У вас нет активной премиум подписки")
            
        conn.close()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def handle_random_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ВСЕ текстовые сообщения (не команды)"""
    if update.message and update.message.text:
        user_message = update.message.text.strip()
        
        # Игнорируем ТОЛЬКО команды
        if user_message.startswith('/'):
            return
        
        # ✅ Проверяем, не находится ли пользователь в процессе заполнения формы консультации
        if 'consult_form' in context.user_data:
            await handle_consult_form(update, context)
            return
            
        # ✅ Проверяем, не находится ли пользователь в процессе заполнения формы проблемы
        if 'report_form' in context.user_data:
            await handle_report_form(update, context)
            return

         # ✅ Проверяем, не находится ли администратор в процессе ручной обработки платежа
        if 'manual_payment_processing' in context.user_data:
            await handle_manual_user_id_input(update, context)
            return

        logging.info(f"🔄 Random message from user {update.effective_user.id}: '{user_message}'")
        
        help_text = """
🌊 О колоде и миссии бота

Море, как и наша жизнь, многолико: оно может быть ласковым, умиротворяющим, а порой — грозным и разрушительным. Этот образ идеально отражает внутренние состояния человека: от штиля до бури.

Каждая карта колоды пропитана энергией моря и создана для того, чтобы помочь вам:

💎Увидеть подсказки для решения жизненных ситуаций.

💎Наполниться ресурсами и энергией, которую несет в себе морская стихия.

💎Научиться распознавать свои эмоции и быть с ними в контакте.

💎Осознать свои ограничения и отпустить их в морскую пучину.

Колода "Настроение как море" помогает заглянуть в глубину собственного бессознательного, осознать эмоции, встретиться с тем, что подавлено, и открыть новые ресурсы для роста.

🦋В добрый путь!
Я благодарю Вас за доверие и интерес к своему внутреннему миру.

Выбирайте в меню бота то, что для Вас сейчас наиболее актуально!

Выберите нужную команду из меню ниже 👇
"""
        
        await update.message.reply_text(
            help_text,
            reply_markup=keyboard.get_main_menu_keyboard(),
            parse_mode='Markdown'
        )

async def reset_my_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает послания дня для администратора (только для админов)"""
    user = update.effective_user
    
    # ✅ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        # Сбрасываем послания текущего пользователя
        deleted_count = db.reset_user_messages(user.id)
        
        await update.message.reply_text(
            f"✅ Ваши послания дня сброшены!\n"
            f"🗑️ Удалено посланий за сегодня: {deleted_count}\n"
            f"🦋 Теперь вы можете получить новое послание дня"
        )
        
    except Exception as e:
        logging.error(f"❌ Error resetting messages: {e}")
        await update.message.reply_text(f"❌ Ошибка при сбросе посланий: {str(e)}")

async def reset_user_messages_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает послания дня для указанного пользователя (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    # ✅ ПРОВЕРКА АРГУМЕНТОВ
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите ID пользователя\n"
            "Пример: /resetusermessages 123456789"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        # Сбрасываем послания указанного пользователя
        deleted_count = db.reset_user_messages(target_user_id)
        
        await update.message.reply_text(
            f"✅ Послания пользователя {target_user_id} сброшены!\n"
            f"🗑️ Удалено посланий за сегодня: {deleted_count}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя")
    except Exception as e:
        logging.error(f"❌ Error resetting user messages: {e}")
        await update.message.reply_text(f"❌ Ошибка при сбросе посланий: {str(e)}")

async def reset_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает ВСЕ послания за сегодня (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        # ✅ ПОДТВЕРЖДЕНИЕ ОПАСНОЙ ОПЕРАЦИИ
        if context.args and context.args[0] == 'confirm':
            # Сбрасываем ВСЕ послания за сегодня
            deleted_count = db.reset_all_messages_today()
            
            await update.message.reply_text(
                f"⚠️ *ВСЕ послания за сегодня сброшены!*\n"
                f"🗑️ Удалено посланий: {deleted_count}\n"
                f"📅 Дата: {date.today().strftime('%d.%m.%Y')}",
                parse_mode='Markdown'
            )
        else:
            # Запрос подтверждения
            await update.message.reply_text(
                "⚠️ *ВНИМАНИЕ: Опасная операция!*\n\n"
                "Эта команда сбросит ВСЕ послания дня для ВСЕХ пользователей за сегодня.\n\n"
                "Для подтверждения введите:\n"
                "`/resetallmessages confirm`",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logging.error(f"❌ Error resetting all messages: {e}")
        await update.message.reply_text(f"❌ Ошибка при сбросе всех посланий: {str(e)}")

async def view_today_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает послания, полученные пользователем сегодня (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    target_user_id = user.id  # по умолчанию смотрим свои послания
    
    if context.args:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя")
            return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # ✅ ПОЛУЧАЕМ СЕГОДНЯШНИЕ ПОСЛАНИЯ ПОЛЬЗОВАТЕЛЯ
        today = date.today()
        cursor.execute('''
            SELECT um.drawn_date, dm.message_text
            FROM user_messages um
            LEFT JOIN daily_messages dm ON um.message_id = dm.message_id
            WHERE um.user_id = %s AND DATE(um.drawn_date) = %s
            ORDER BY um.drawn_date
        ''', (target_user_id, today))
        
        today_messages = cursor.fetchall()
        
        # ✅ ПОЛУЧАЕМ ИНФОРМАЦИЮ О ПОЛЬЗОВАТЕЛЕ
        cursor.execute('''
            SELECT username, first_name, is_premium
            FROM users 
            WHERE user_id = %s
        ''', (target_user_id,))
        
        user_info = cursor.fetchone()
        conn.close()
        
        if not user_info:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        username, first_name, is_premium = user_info
        user_display = f"@{username}" if username else first_name or f"ID {target_user_id}"
        
        messages_text = f"""
📊 Послания пользователя {user_display} за сегодня:

💎 Премиум: {'✅ Да' if is_premium else '❌ Нет'}
📅 Дата: {today.strftime('%d.%m.%Y')}

"""
        
        if today_messages:
            messages_text += f"📋 Получено посланий: {len(today_messages)}\n\n"
            for i, (drawn_date, message_text) in enumerate(today_messages, 1):
                time_str = drawn_date.strftime('%H:%M') if hasattr(drawn_date, 'strftime') else drawn_date[11:16]
                messages_text += f"{i}. {time_str}"
                if message_text:
                    messages_text += f" - {message_text[:30]}..."
                messages_text += "\n"
        else:
            messages_text += "✅ Сегодня еще не получено ни одного послания"
        
        await update.message.reply_text(messages_text, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"❌ Error viewing today messages: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def update_cards_descriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет описания карт в базе данных (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        # Принудительно добавляем карты с новыми описаниями
        added_count = db.add_missing_cards()
        
        await update.message.reply_text(
            f"✅ Описания карт обновлены!\n"
            f"🃏 Добавлено/обновлено карт: {added_count}"
        )
        
    except Exception as e:
        logging.error(f"❌ Error updating cards: {e}")
        await update.message.reply_text(f"❌ Ошибка при обновлении карт: {str(e)}")


async def resources_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /resources - Архипелаг ресурсов"""
    user = update.effective_user
    subscription = db.get_user_subscription(user.id)
    has_active_subscription = subscription and subscription[1] and subscription[1].date() >= date.today()
    
    if not has_active_subscription:
        await update.message.reply_text(
            "❌ *Техники самопомощи доступен только пользователям с премиум подпиской!*\n\n"
            "Используйте /subscribe чтобы оформить подписку и получить доступ ко всем ресурсам!",
            reply_markup=keyboard.get_message_status_keyboard(),
            parse_mode='Markdown'
        )
        return
    resources_text = """
🗺️ Техники самопомощи

Выберите технику, которой хотите воспользоваться:
"""
    
    await update.message.reply_text(
        resources_text,
        reply_markup=keyboard.get_resources_keyboard(),
        parse_mode='Markdown'
    )

async def show_resources_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает Архипелаг ресурсов из кнопки меню"""
    logging.info(f"🔧 DEBUG: show_resources_from_button started for user {query.from_user.id}")
    
    try:
        user = query.from_user
        
        # ✅ ПРОВЕРЯЕМ ПОДПИСКУ ПОЛЬЗОВАТЕЛЯ
        subscription = db.get_user_subscription(user.id)
        logging.info(f"🔧 DEBUG: Subscription data: {subscription}")
        
        has_active_subscription = False
        if subscription and subscription[1]:
            subscription_end = subscription[1]
            if hasattr(subscription_end, 'date'):
                subscription_date = subscription_end.date()
            elif isinstance(subscription_end, str):
                try:
                    subscription_date = datetime.strptime(subscription_end[:10], '%Y-%m-%d').date()
                except:
                    subscription_date = date.today()
            else:
                subscription_date = subscription_end
            
            has_active_subscription = subscription_date >= date.today()
        
        logging.info(f"🔧 DEBUG: Has active subscription: {has_active_subscription}")
        
        if not has_active_subscription:
            await query.message.reply_text(
                "❌ *Техники самопомощи доступен только пользователям с премиум подпиской!*\n\n"
                "Используйте кнопку ниже чтобы оформить подписку и получить доступ ко всем ресурсам!",
                reply_markup=keyboard.get_message_status_keyboard(),
                parse_mode='Markdown'
            )
            return
        
        resources_text = """
🗺️ Техники самопомощи

Выберите технику, которой хотите воспользоваться:
"""
        
        await query.message.reply_text(
            resources_text,
            reply_markup=keyboard.get_resources_keyboard(),
            parse_mode='Markdown'
        )
        logging.info(f"🔧 DEBUG: Resources menu sent to user {user.id}")
        
    except Exception as e:
        logging.error(f"❌ Error in show_resources_from_button: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка при загрузке ресурсов. Попробуйте позже.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )

async def handle_resource_technique(query, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор техники в Архипелаге ресурсов"""
    technique = query.data
    
    if technique == "resource_tide":
        await show_tide_technique(query, context)
    elif technique == "resource_tech2":
        await handle_storm_calm_technique(query, context)  
    elif technique == "resource_tech3" :
        await handle_three_waves_technique(query, context)

async def show_tide_technique(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает технику Морской Прилив"""
    tide_text = """
🌊 *Волна Новых Возможностей*

💡 *Цель Техники*
Эта техника подходит для работы с ограничениями, которые мешают впустить в жизнь новое. Техника поможет осознать, от чего нужно освободиться, и что ресурсное впустить в свою жизнь.

⚓️ *Шаг 1: Освобождение от Ограничений (Что пора отпустить?)*

📝 Мысленно задайте вопрос картам:

*«Что мне пора отпустить в моей жизни, что стало ненужным грузом и сдерживает мое развитие?»*
"""
    
    await query.message.reply_text(
        tide_text,
        reply_markup=keyboard.get_tide_step1_keyboard(),
        parse_mode='Markdown'
    )

async def handle_tide_step1_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор карты-ограничения в Шаге 1"""
    await query.edit_message_reply_markup(reply_markup=None)
    # Получаем случайную карту-ограничение
    card = db.get_random_restriction_card()
    
    if not card:
        await query.message.reply_text(
            "❌ Ошибка при получении карты. Попробуйте позже.",
            reply_markup=keyboard.get_tide_step1_keyboard()
        )
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту в контексте для вопросов
    context.user_data['tide_step1_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url,
        'description': description
    }
    
    try:
        # Отправляем карту-ограничение
        await query.message.reply_photo(
            photo=image_url,
            caption=f"🎴 *Карта-ограничение*",
            reply_markup=keyboard.get_tide_step1_reflection_keyboard(),
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"❌ Error sending restriction card: {e}")
        await query.message.reply_text(
            f"🎴 *Карта-ограничение*\n\n(изображение временно недоступно)",
            reply_markup=keyboard.get_tide_step1_reflection_keyboard(),
            parse_mode='Markdown'
        )

async def handle_tide_step1_questions(query, context: ContextTypes.DEFAULT_TYPE):
    await query.edit_message_reply_markup(reply_markup=None)
    """Показывает вопросы для саморефлексии Шага 1"""
    questions_text = """
❓ *Вопросы для Саморефлексии*

• Что первым привлекло ваше внимание на карте?

• Какое чувство вызывает у вас это изображение? Что оно символизирует?

• Как то что изображено на карте мешает вам или ограничивает?

• К какой сфере жизни, человеку или ситуации относится это ограничение, которое вы видите на карте?

• Что не дает отпустить это ограничение?

• Как изменится ваша жизнь, если этого ограничения не будет?

• Какой первый шаг к освобождению вы можете сделать прямо сейчас?

• Дайте название этому ограничению и отпустите его?
"""
    
    await query.message.reply_text(
        questions_text,
        reply_markup=keyboard.get_tide_step1_questions_keyboard(),
        parse_mode='Markdown'
    )

async def handle_tide_step2(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает Шаг 2 техники Морской Прилив"""
    await query.edit_message_reply_markup(reply_markup=None)
    step2_text = """
☀️ *Шаг 2: Поиск новых Возможностей и Ресурсов (Что я принимаю?)*

Теперь, когда вы осознали и отпустили свое ограничение, пора подумать о том, что ресурсное и вдохновляющее вы можете впустить в освободившееся пространство.

📝 Мысленно задайте вопрос картам:

*«Какой ресурс, новую возможность или силу я могу впустить в свою жизнь, освободившись от старого груза?»*
"""
    
    await query.message.reply_text(
        step2_text,
        reply_markup=keyboard.get_tide_step2_keyboard(),
        parse_mode='Markdown'
    )

async def handle_tide_step2_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор карты-возможности в Шаге 2"""
    await query.edit_message_reply_markup(reply_markup=None)
    # Получаем случайную карту-возможность
    card = db.get_random_opportunity_card()
    
    if not card:
        await query.message.reply_text(
            "❌ Ошибка при получении карты. Попробуйте позже.",
            reply_markup=keyboard.get_tide_step2_keyboard()
        )
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту в контексте для вопросов
    context.user_data['tide_step2_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url,
        'description': description
    }
    
    try:
        # Отправляем карту-возможность
        await query.message.reply_photo(
            photo=image_url,
            caption=f"🎴 *Карта-возможность*",
            reply_markup=keyboard.get_tide_step2_reflection_keyboard(),
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"❌ Error sending opportunity card: {e}")
        await query.message.reply_text(
            f"🎴 *Карта-возможность*\n\n(изображение временно недоступно)",
            reply_markup=keyboard.get_tide_step2_reflection_keyboard(),
            parse_mode='Markdown'
        )

async def handle_tide_step2_questions(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает вопросы для саморефлексии Шага 2"""
    await query.edit_message_reply_markup(reply_markup=None)
    questions_text = """
❓ *Вопросы для Саморефлексии*

• Что первым привлекло ваше внимание на карте?

• Какое чувство вызывает у вас это изображение? Что оно символизирует?

• Как то что изображено на карте может наполнить вас ресурсами и открыть новые возможности?

• Что на этой карте кажется вам самым ресурсным?

• Какое конкретное действие, связанное с образом на карте, вы готовы начать делать, чтобы впустить этот ресурс в свою жизнь?

• Что новое и ресурсное вы принимаете и впускаете в свою жизнь, начиная с этого момента?
"""
    
    await query.message.reply_text(
        questions_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌅 Завершить практику", callback_data="complete_tide_practice")]
        ]),
        parse_mode='Markdown'
    )

async def complete_tide_practice(query, context: ContextTypes.DEFAULT_TYPE):
    """Завершает практику Морской Прилив"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    completion_text = """
Спасибо, что прикоснулись к своим внутренним ограничениям и увидели свои возможности ✨

Умение отпускать ненужное освобождает место для нового ☀️

🌊 В море можно отпустить всю свою боль и тяжесть и почувствовать освобождение.

💫 Вернуться к этой технике можно в любой момент, когда захочется лучше понять себя.
"""
    
    await query.message.reply_text(
        completion_text,
        reply_markup=keyboard.get_tide_completion_keyboard(),
        parse_mode='Markdown'
    )

async def force_update_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительно обновляет ВСЕ карты (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        # Принудительно обновляем все карты
        updated_count = db.force_update_all_cards()
        
        await update.message.reply_text(
            f"✅ Все карты принудительно обновлены!\n"
            f"🃏 Обновлено карт: {updated_count}/176"
        )
        
    except Exception as e:
        logging.error(f"❌ Error force updating cards: {e}")
        await update.message.reply_text(f"❌ Ошибка при обновлении карт: {str(e)}")


async def handle_storm_calm_technique(query, context: ContextTypes.DEFAULT_TYPE):
    """Начинает технику Шторм и Штиль внутри тебя"""
    technique_text = """
*Шторм и Штиль внутри тебя*

💡 *Цель Техники*
Мягко исследовать текущее эмоциональное состояние (без оценки «хорошо/плохо»), осознать его динамику и найти внутренний ресурс, который помогает оставаться в согласии с самим собой.

🌊
Иногда в душе бушует шторм, иногда — тихий штиль.
Эта техника поможет почувствовать свой внутренний ритм — не изменить состояние, а услышать, о чём оно.

Сделайте вдох и позвольте себе просто быть.

Нажмите кнопку ниже, чтобы вытянуть карту, отражающую ваше текущее состояние.
"""
    
    await query.message.reply_text(
        technique_text,
        reply_markup=keyboard.get_storm_calm_step1_keyboard(),
        parse_mode='Markdown'
    )

async def handle_storm_calm_step1_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает карту состояния для техники Шторм и Штиль"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Получаем случайную карту из всего диапазона (1-176)
    card = db.get_random_card()
    
    if not card:
        await query.message.reply_text(
            "❌ Ошибка при получении карты. Попробуйте позже.",
            reply_markup=keyboard.get_storm_calm_step1_keyboard()
        )
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту состояния в контексте
    context.user_data['storm_calm_state_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url,
        'description': description
    }
    
    try:
        # Отправляем карту состояния
        await query.message.reply_photo(
            photo=image_url,
            caption="🎴 *Это карта твоего сегодняшнего моря.*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"❌ Error sending state card: {e}")
        await query.message.reply_text(
            "🎴 *Это карта твоего сегодняшнего моря.*\n\n(изображение временно недоступно)",
            parse_mode='Markdown'
        )
    
    # Отправляем вопросы для рефлексии
    reflection_text = """
*Посмотри на неё без анализа — просто наблюдай.*

💬*Задай себе вопрос:*

▪️Что это море говорит о моём состоянии сейчас?
▪️Есть ли в нём движение, или наоборот — остановка?
▪️Какое это состояние по энергии: разрушает, сохраняет, замедляет, зовёт к покою?
▪️Что это состояние хочет мне сказать?
"""
    
    await query.message.reply_text(
        reflection_text,
        reply_markup=keyboard.get_storm_calm_step2_keyboard(),
        parse_mode='Markdown'
    )

async def handle_storm_calm_step2_lighthouse(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает карту-маяк (ресурс)"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Получаем случайную карту-возможность (89-176)
    card = db.get_random_opportunity_card()
    
    if not card:
        await query.message.reply_text(
            "❌ Ошибка при получении карты-маяка. Попробуйте позже.",
            reply_markup=keyboard.get_storm_calm_step2_keyboard()
        )
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту-маяк в контексте
    context.user_data['storm_calm_lighthouse_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url,
        'description': description
    }
    
    try:
        # Отправляем карту-маяк
        await query.message.reply_photo(
            photo=image_url,
            caption="🕯 *Это твой внутренний Маяк — то, что помогает тебе быть в согласии с собой.*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"❌ Error sending lighthouse card: {e}")
        await query.message.reply_text(
            "🕯 *Это твой внутренний Маяк — то, что помогает тебе быть в согласии с собой.*\n\n(изображение временно недоступно)",
            parse_mode='Markdown'
        )
    
    # Отправляем вопросы для рефлексии по маяку
    lighthouse_text = """
🔎*Подумай:*

▪️Какой внутренний ресурс поможет мне быть в согласии со своим любым состоянием? 
▪️Что в этом образе похоже на поддержку, надежду или смысл?
▪️Какой импульс я чувствую, глядя на эту карту?
▪️Что я могу сделать сегодня, чтобы быть в согласии со своим любым состоянием?
"""
    
    await query.message.reply_text(
        lighthouse_text,
        reply_markup=keyboard.get_storm_calm_step3_keyboard(),
        parse_mode='Markdown'
    )

async def handle_storm_calm_complete(query, context: ContextTypes.DEFAULT_TYPE):
    """Завершает технику Шторм и Штиль"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    completion_text = """
Спасибо, что прикоснулись к своему морю 🌊

Иногда ритм жизни похож на волну — то прибой, то отлив.

Важно не бороться с морем, а учиться слышать его дыхание.

💫 Вернуться к этой технике можно в любой момент, когда захочется лучше понять себя.
"""
    
    await query.message.reply_text(
        completion_text,
        reply_markup=keyboard.get_storm_calm_completion_keyboard(),
        parse_mode='Markdown'
    )       

async def handle_three_waves_technique(query, context: ContextTypes.DEFAULT_TYPE):
    """Начинает технику Три Волны Осознанности"""
    technique_text = """
*«Три Волны Осознанности»*

Иногда эмоции приходят волнами.
Первая — поднимает то, что мы чувствуем.
Вторая — показывает, почему это возникло.
А третья — помогает найти способ быть с этим по-новому.

Давай попробуем вместе пройти через три волны осознанности.
"""
    
    await query.message.reply_text(
        technique_text,
        reply_markup=keyboard.get_three_waves_intro_keyboard(),
        parse_mode='Markdown'
    )

async def handle_three_waves_step1(query, context: ContextTypes.DEFAULT_TYPE):
    """Первая волна - что я чувствую"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    step1_text = """
*🌊 Первая Волна — «Что я чувствую?»*

Мысленно задай вопрос:
*«Что я чувствую прямо сейчас?»*

Пусть первая карта покажет твою эмоцию, то, что поднимается на поверхности твоего внутреннего моря.
"""
    
    await query.message.reply_text(
        step1_text,
        reply_markup=keyboard.get_three_waves_step1_keyboard(),
        parse_mode='Markdown'
    )

async def handle_three_waves_step1_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает карту для первой волны"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Получаем случайную карту-возможность (89-176)
    card = db.get_random_opportunity_card()
    
    if not card:
        await query.message.reply_text(
            "❌ Ошибка при получении карты. Попробуйте позже.",
            reply_markup=keyboard.get_three_waves_step1_keyboard()
        )
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту в контексте
    context.user_data['three_waves_step1_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url,
        'description': description
    }
    
    try:
        # Отправляем карту
        await query.message.reply_photo(
            photo=image_url,
            caption="🎴 *Первая Волна — Что я чувствую?*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"❌ Error sending step1 card: {e}")
        await query.message.reply_text(
            "🎴 *Первая Волна — Что я чувствую?*\n\n(изображение временно недоступно)",
            parse_mode='Markdown'
        )
    
    # Отправляем вопросы для рефлексии
    reflection_text = """
*Посмотри на изображение.*

•Что первым делом привлекло твое внимание?
•Какое это чувство — мягкое, тревожное, холодное, тёплое?
•Если бы это море могло говорить, что бы оно сказало о тебе?
"""
    
    await query.message.reply_text(
        reflection_text,
        reply_markup=keyboard.get_three_waves_step2_keyboard(),
        parse_mode='Markdown'
    )

async def handle_three_waves_step2(query, context: ContextTypes.DEFAULT_TYPE):
    """Вторая волна - почему я это чувствую"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    step2_text = """
*🌊 Вторая Волна — «Почему я это чувствую?»*

Теперь заглянем глубже.
Мысленно спроси:
*«Почему это чувство пришло ко мне?»*

Пусть вторая карта покажет глубинную причину твоего состояния.
"""
    
    await query.message.reply_text(
        step2_text,
        reply_markup=keyboard.get_three_waves_step2_card_keyboard(),
        parse_mode='Markdown'
    )

async def handle_three_waves_step2_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает карту для второй волны"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Получаем случайную карту-ограничение (1-88)
    card = db.get_random_restriction_card()
    
    if not card:
        await query.message.reply_text(
            "❌ Ошибка при получении карты. Попробуйте позже.",
            reply_markup=keyboard.get_three_waves_step2_card_keyboard()
        )
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту в контексте
    context.user_data['three_waves_step2_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url,
        'description': description
    }
    
    try:
        # Отправляем карту
        await query.message.reply_photo(
            photo=image_url,
            caption="🎴 *Вторая Волна — Почему я это чувствую?*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"❌ Error sending step2 card: {e}")
        await query.message.reply_text(
            "🎴 *Вторая Волна — Почему я это чувствую?*\n\n(изображение временно недоступно)",
            parse_mode='Markdown'
        )
    
    # Отправляем вопросы для рефлексии
    reflection_text = """
•Что в этом образе похоже на твою жизнь сейчас?
•Есть ли под этой эмоцией что-то ещё — боль, усталость, ожидание, страх?
•Что это чувство хочет тебе сказать?
"""
    
    await query.message.reply_text(
        reflection_text,
        reply_markup=keyboard.get_three_waves_step3_keyboard(),
        parse_mode='Markdown'
    )

async def handle_three_waves_step3(query, context: ContextTypes.DEFAULT_TYPE):
    """Третья волна - как я могу с этим быть"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    step3_text = """
*🌊 Третья Волна — «Как я могу с этим быть?»*

И теперь — последняя волна.
Мысленно спроси:
*«Как я могу быть с этой эмоцией так, чтобы она помогала, а не мешала?»*

Пусть третья карта подскажет, как превратить внутренний шторм в осознанное движение.
"""
    
    await query.message.reply_text(
        step3_text,
        reply_markup=keyboard.get_three_waves_step3_card_keyboard(),
        parse_mode='Markdown'
    )

async def handle_three_waves_step3_card(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает карту для третьей волны"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Получаем случайную карту-возможность (89-176)
    card = db.get_random_opportunity_card()
    
    if not card:
        await query.message.reply_text(
            "❌ Ошибка при получении карты. Попробуйте позже.",
            reply_markup=keyboard.get_three_waves_step3_card_keyboard()
        )
        return
    
    card_id, card_name, image_url, description = card
    
    # Сохраняем карту в контексте
    context.user_data['three_waves_step3_card'] = {
        'card_id': card_id,
        'card_name': card_name,
        'image_url': image_url,
        'description': description
    }
    
    try:
        # Отправляем карту
        await query.message.reply_photo(
            photo=image_url,
            caption="🎴 *Третья Волна — Как я могу с этим быть?*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"❌ Error sending step3 card: {e}")
        await query.message.reply_text(
            "🎴 *Третья Волна — Как я могу с этим быть?*\n\n(изображение временно недоступно)",
            parse_mode='Markdown'
        )
    
    # Отправляем вопросы для рефлексии
    reflection_text = """
•Что в этом образе напоминает принятие или спокойствие?
•Как ты можешь поддержать себя сейчас?
•Какое действие или внутреннее движение поможет тебе сохранить равновесие?
"""
    
    await query.message.reply_text(
        reflection_text,
        reply_markup=keyboard.get_three_waves_completion_keyboard(),
        parse_mode='Markdown'
    )

async def handle_three_waves_complete(query, context: ContextTypes.DEFAULT_TYPE):
    """Завершает технику Три Волны Осознанности"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    completion_text = """
🪞Эти три волны — как зеркало твоей души.

Они показывают, как ты чувствуешь, почему это происходит и куда направить энергию💫

Сделай глубокий вдох и поблагодари своё внутреннее море за честность.

✨Вернуться к этой технике можно в любой момент, когда захочется лучше понять себя.
"""
    
    await query.message.reply_text(
        completion_text,
        reply_markup=keyboard.get_three_waves_final_keyboard(),
        parse_mode='Markdown'
    )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /buy"""
    user = update.effective_user
    
    # Проверяем, покупал ли пользователь уже колоду
    if db.has_purchased_deck(user.id):
        # Если уже покупал - сразу отправляем файлы
        await send_deck_files(update, context, user.id)
        return

    buy_text = """
🛒 *Купить цифровую колоду*

Вы можете приобрести полную цифровую версию колоды метафорических карт «Настроение как море»:

✨ *Что входит в комплект:*
• 88 карт без рамки (Возможности)
• 88 карт с рамкой (Ограничения)  
• Методическое пособие с посланиями ко всем картам

💎 *Формат файлов:* PDF, ZIP, RAR
📦 *Мгновенная доставка:* файлы придут сразу после оплаты
💰 *Стоимость:* 999₽

*Нажмите кнопку "Купить колоду" чтобы получить колоду:*
"""
    
    await update.message.reply_text(
        buy_text,
        reply_markup=keyboard.get_buy_keyboard(),
        parse_mode='Markdown'
    )

async def show_buy_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о покупке из кнопки меню"""
    user = query.from_user
    
    # Проверяем, покупал ли пользователь уже колоду
    if db.has_purchased_deck(user.id):
        # Если уже покупал - сразу отправляем файлы
        await send_deck_files_to_query(query, context, user.id)
        return

    buy_text = """
🛒 *Купить цифровую колоду*

Вы можете приобрести полную цифровую версию колоды метафорических карт «Настроение как море»:

✨ *Что входит в комплект:*
• 88 карт без рамки (Возможности)
• 88 карт с рамкой (Ограничения) 
• Методическое пособие с посланиями ко всем картам

💎 *Формат файлов:* PDF, ZIP, RAR
📦 *Мгновенная доставка:* файлы придут сразу после оплаты
💰 *Стоимость:* 999₽

"""
    
    await query.message.reply_text(
        buy_text,
        reply_markup=keyboard.get_buy_keyboard(),
        parse_mode='Markdown'
    )

async def handle_buy_deck(query, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает покупку колоды"""
    user = query.from_user
    
    # Проверяем, покупал ли пользователь уже колоду
    if db.has_purchased_deck(user.id):
        # Если уже покупал - сразу отправляем файлы
        await send_deck_files_to_query(query, context, user.id)
        return
    
    # Создаем платеж
    payment_url, payment_id = payment_processor.create_deck_payment(user.id)
    
    if not payment_url:
        await query.message.reply_text(
            "❌ Ошибка при создании платежа. Попробуйте позже.",
            reply_markup=keyboard.get_buy_keyboard()
        )
        return
    
    # Сохраняем в контексте
    context.user_data['deck_payment_id'] = payment_id
    
    payment_text = """
💎 *Цифровая колода «Настроение как море»*

Стоимость: 999₽

Нажмите кнопку "💳 Оплатить онлайн" для перехода к оплате.

После успешной оплаты файлы колоды будут отправлены автоматически в течение 1-2 минут.

Если файлы не пришли, нажмите "🔄 Проверить оплату".
"""
    
    await query.message.reply_text(
        payment_text,
        reply_markup=keyboard.get_deck_payment_keyboard(payment_url, payment_id),
        parse_mode='Markdown'
    )

async def handle_deck_payment_check(query, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет статус оплаты колоды"""
    user = query.from_user
    
    # Проверяем, не покупал ли пользователь уже колоду
    if db.has_purchased_deck(user.id):
        await send_deck_files_to_query(query, context, user.id)
        return
    
    payment_id = context.user_data.get('deck_payment_id')
    
    if not payment_id:
        await query.message.reply_text(
            "❌ Не найден активный платеж. Пожалуйста, начните процесс заново.",
            reply_markup=keyboard.get_buy_keyboard()
        )
        return
    
    # Проверяем статус платежа
    payment_status = payment_processor.check_payment_status(payment_id)
    
    if payment_status is True:
        # Платеж подтвержден, активируем покупку
        if payment_processor.activate_deck_purchase(payment_id):
            await send_deck_files_to_query(query, context, user.id)
            
            # Очищаем данные о платеже
            if 'deck_payment_id' in context.user_data:
                del context.user_data['deck_payment_id']
        else:
            await query.message.reply_text(
                "❌ Ошибка при активации покупки. Свяжитесь с администратором.",
                reply_markup=keyboard.get_buy_keyboard()
            )
            
    elif payment_status is False:
        await query.message.reply_text(
            "❌ Платеж не прошел или был отменен. Попробуйте оплатить снова.",
            reply_markup=keyboard.get_buy_keyboard()
        )
    else:
        # Платеж еще обрабатывается
        await query.message.reply_text(
            "⏳ Платеж еще обрабатывается...\n\n"
            "Пожалуйста, подождите 1-2 минуты и проверьте снова.",
            reply_markup=keyboard.get_deck_payment_check_keyboard(payment_id)
        )

async def send_deck_files_to_query(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Отправляет файлы колоды в ответ на query"""
    await query.edit_message_reply_markup(reply_markup=None)
    
    try:
        # Отправляем сообщение об успехе
        success_text = """
✅ *Спасибо за покупку!*

Ваша цифровая колода «Настроение как море» готова к скачиванию.

📦 *Файлы отправляются...*
"""
        await query.message.reply_text(success_text, parse_mode='Markdown')
        
        # Отправляем файлы
        file_ids = {
            "zip": "BQACAgIAAxkBAAILH2ka8spSoCXJz_jB1wFckPfGYkSXAAKNgQACUSbYSEhUWdaRMfa5NgQ",
            "rar": "BQACAgIAAxkBAAILIWka8yBQZpQQw23Oj4rIGSF_zNYAA5KBAAJRJthIJUVWWMwVvMg2BA",
            "pdf": "BQACAgIAAxkBAAILF2ka8jBpiM0_cTutmYhXeGoZs4PJAAJ1gQACUSbYSAUgICe9H14nNgQ"
        }
        
        try:
            # ZIP файл
            await query.message.reply_document(
                document=file_ids["zip"],
                filename="Ограничения.zip",
                caption="📦 Архив с картами (ZIP формат)"
            )
        except Exception as e:
            logger.error(f"❌ Error sending ZIP: {e}")
        
        try:
            # RAR файл
            await query.message.reply_document(
                document=file_ids["rar"],
                filename="Возможности.rar",
                caption="📦 Архив с картами (RAR формат)"
            )
        except Exception as e:
            logger.error(f"❌ Error sending RAR: {e}")
        
        try:
            # PDF файл
            await query.message.reply_document(
                document=file_ids["pdf"],
                filename="Колода_Настроение_как_море_методическое_пособие.pdf",
                caption="📚 Методическое пособие с посланиями"
            )
        except Exception as e:
            logger.error(f"❌ Error sending PDF: {e}")
        
        # Финальное сообщение
        final_text = """
🎉 *Поздравляем с приобретением колоды!*

Теперь у вас есть полный доступ ко всем картам и методическим материалам.

💫 Приятного использования!
"""
        await query.message.reply_text(
            final_text,
            reply_markup=keyboard.get_after_purchase_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Error sending deck files: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка при отправке файлов. Пожалуйста, свяжитесь с администратором."
        )

async def send_deck_files(update, context: ContextTypes.DEFAULT_TYPE, user_id: int, message=None):
    """Отправляет файлы колоды пользователю"""
    try:
        if message is None and update:
            message = update.message
        success_text = """
✅ *Спасибо за покупку!*

Ваша цифровая колода «Настроение как море» готова к скачиванию.

📦 *В комплекте:*
• Архив с картами-ограничениями (ZIP)
• Архив с картами-возможностями (RAR) 
• Методическое пособие (PDF)

*Файлы отправляются...*
"""
        
        await query.message.reply_text(
            success_text,
            parse_mode='Markdown'
        )
        
        # Здесь будут file_id ваших реальных файлов
        # Пока используем заглушки - замените на реальные file_id
        
        try:
            # Попытка отправить ZIP файл
            # Замените file_id на реальный ID вашего ZIP файла
            await query.message.reply_document(
                document="BQACAgIAAxkBAAILH2ka8spSoCXJz_jB1wFckPfGYkSXAAKNgQACUSbYSEhUWdaRMfa5NgQ",  
                filename="Ограничения.zip",
                caption="📦 Архив с картами (ZIP формат)"
            )
        except Exception as e:
            logging.error(f"❌ Error sending ZIP: {e}")
            await query.message.reply_text(
                "❌ Файл ZIP временно недоступен. Мы уже работаем над исправлением!"
            )
        
        try:
            # Попытка отправить RAR файл  
            # Замените file_id на реальный ID вашего RAR файла
            await query.message.reply_document(
                document="BQACAgIAAxkBAAILIWka8yBQZpQQw23Oj4rIGSF_zNYAA5KBAAJRJthIJUVWWMwVvMg2BA",  
                filename="Возможности.rar",
                caption="📦 Архив с картами (RAR формат)"
            )
        except Exception as e:
            logging.error(f"❌ Error sending RAR: {e}")
            await query.message.reply_text(
                "❌ Файл RAR временно недоступен. Мы уже работаем над исправлением!"
            )
        
        try:
            # Попытка отправить PDF файл
            # Замените file_id на реальный ID вашего PDF файла
            await query.message.reply_document(
                document="BQACAgIAAxkBAAILF2ka8jBpiM0_cTutmYhXeGoZs4PJAAJ1gQACUSbYSAUgICe9H14nNgQ",  
                filename="Колода_Настроение_как_море_методическое_пособие.pdf",
                caption="📚 Методическое пособие с посланиями"
            )
        except Exception as e:
            logging.error(f"❌ Error sending PDF: {e}")
            await query.message.reply_text(
                "❌ PDF файл временно недоступен. Мы уже работаем над исправлением!"
            )
        
        # Финальное сообщение
        final_text = """
🎉 *Поздравляем с приобретением колоды!*

Теперь у вас есть полный доступ ко всем картам и методическим материалам.

✨ Приятного использования!
"""
        
        if message:
            await message.reply_text(
                final_text,
                reply_markup=keyboard.get_after_purchase_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                final_text,
                reply_markup=keyboard.get_after_purchase_keyboard(),
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logging.error(f"❌ Error sending deck files: {e}")
        error_msg = "❌ Произошла ошибка при отправке файлов. Пожалуйста, свяжитесь с администратором."
        
        if message:
            await message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def handle_start_with_deck_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает deep link после успешной оплаты колоды"""
    user = update.effective_user
    args = context.args
    
    if args and args[0] == 'deck_purchase_success':
        # Проверяем, есть ли у пользователя покупка колоды
        if db.has_purchased_deck(user.id):
            await send_deck_files(update, context, user.id)
        else:
            await update.message.reply_text(
                "⏳ Ваш платеж обрабатывается...\n\n"
                "Файлы будут отправлены в течение 1-2 минут. "
                "Если прошло больше времени, используйте команду /buy для проверки статуса.",
                reply_markup=keyboard.get_buy_keyboard()
            )

async def upload_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для загрузки файлов и получения file_id"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    instruction_text = """
📤 *Как получить file_id файлов:*

1. Отправьте ZIP файл как документ
2. Отправьте RAR файл как документ  
3. Отправьте PDF файл как документ
4. Используйте /getfileids чтобы посмотреть file_id

Бот автоматически сохранит file_id всех отправленных документов.
"""
    
    await update.message.reply_text(instruction_text, parse_mode='Markdown')

async def messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /messages - информация о посланиях дня"""
    # Определяем, откуда пришел запрос - из команды или из кнопки
    if update.callback_query:
        # Если это callback query (нажатие кнопки)
        query = update.callback_query
        message = query.message
        await query.answer()  # Подтверждаем нажатие кнопки
    else:
        # Если это обычная команда
        message = update.message
    
    user = update.effective_user
    
    # Получаем статистику пользователя для персонализации
    stats = db.get_user_message_stats(user.id)
    
    if stats:
        if stats['has_subscription']:
            # Для премиум пользователей
            message_text = f"""
💫 *О посланиях дня*

✨ *Для вас как для премиум-пользователя:*
• 🎯 До 5 посланий в день
• 📊 Сегодня использовано: {stats['today_count']}/5
• 🆓 Доступно всегда после получения карты дня

💡 *Как это работает:*
1. Сначала получите карту дня (/daily)
2. Затем нажмите кнопку «🦋 Послание дня»
3. Получите глубокое толкование вашей карты
"""
        else:
            # Для бесплатных пользователей
            if stats['can_take']:
                status_text = "✅ *Сейчас доступно* - можно получить послание!"
                remaining_text = f"🆓 Осталось бесплатных посланий: {stats['remaining']}/3"
            else:
                status_text = "⏳ *Бесплатные послания использованы*"
                remaining_text = "💎 Оформите подписку для неограниченного доступа!"
            
            message_text = f"""
💫 *О посланиях дня*

{status_text}
{remaining_text}

📅 *Базовый режим:* 3 послания за всё время
💎 *Премиум режим:* 5 посланий в день  

💡 *Как получить послание:*
1. Используйте /daily для карты дня
2. Нажмите «🦋 Послание дня»
3. Получите послание для вашего дня

✨ *Хотите больше?* Оформите подписку для полного доступа!
"""
    else:
        # Общая информация для новых пользователей
        message_text = """
💫 *О посланиях дня*

📚 *Что такое послание дня?*
Это глубокое толкование вашей карты дня, которое помогает:
• Понять скрытые смыслы образа
• Увидеть подсказки для текущей ситуации
• Найти ресурсы для развития

🎯 *Доступность:*
• 🆓 *Бесплатно:* 3 послания за всё время
• 💎 *С подпиской:* 5 посланий в день

💡 *Как работает:*
1. Сначала получите карту дня (/daily)
2. Затем нажмите «🦋 Послание дня»
3. Получите послание для вашего дня

✨ Послание дня — это ключ к пониманию вашего внутреннего состояния и подсказкам Вселенной!
"""
    
    await message.reply_text(
        message_text,
        reply_markup=keyboard.get_messages_info_keyboard(stats['has_subscription'] if stats else False),
        parse_mode='Markdown'
    )

def get_video_system():
    """Создает экземпляр video_system при каждом вызове"""
    try:
        from secure_video import SecureVideoSystem
        from config import BASE_URL
        from database import db
        return SecureVideoSystem(BASE_URL, db)
    except Exception as e:
        logging.error(f"❌ Error creating video system: {e}")
        return None

async def meditation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /meditation"""
    user = update.effective_user
    logging.info(f"🔧 Meditation command called by user {user.id}")
    
    # Проверяем доступ ДО создания видео системы
    can_watch, reason = db.can_watch_meditation(user.id)
    
    if not can_watch:
        await update.message.reply_text(
            f"❌ {reason}",
            reply_markup=keyboard.get_meditation_limited_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # Создаем video_system при каждом вызове
    video_system = get_video_system_safe()
    
    if not video_system:
        logging.error(f"❌ Video system is None for user {user.id}")
        await update.message.reply_text(
            "❌ Система видео временно недоступна. Попробуйте позже.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    # Получаем информацию о подписке
    subscription = db.get_user_subscription(user.id)
    has_active_subscription = False
    
    if subscription and subscription[1]:
        sub_end = subscription[1]
        if hasattr(sub_end, 'date'):
            has_active_subscription = sub_end.date() >= datetime.now().date()
    
    # Генерируем отдельные ссылки для YouTube и RUTUBE
    youtube_link = video_system.generate_secure_link(user.id, "youtube")
    rutube_link = video_system.generate_secure_link(user.id, "rutube")
    
    if not youtube_link or not rutube_link:
        await update.message.reply_text(
            "❌ Ошибка при подготовке медитации. Попробуйте позже.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    meditation_text = """
🐚 *Медитация «Дары Моря»*

Погрузитесь в умиротворяющую атмосферу морской медитации, которая поможет вам найти внутренний покой и гармонию.

✨ *Доступные платформы:*
• YouTube 
• RUTUBE 
"""
    
    if not has_active_subscription:
        meditation_text += "\n⚠️ *Бесплатный доступ:* предоставляется только 1 раз на 24 часа"
    
    logging.info(f"✅ Sending meditation links to user {user.id}")
    await update.message.reply_text(
        meditation_text,
        parse_mode='Markdown',
        reply_markup=keyboard.get_meditation_platforms_keyboard(youtube_link, rutube_link),
        disable_web_page_preview=True
    )

async def meditation_button_handler(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки медитации из меню"""
    user = query.from_user
    await query.answer()
    
    # Проверяем доступ ДО создания видео системы
    can_watch, reason = db.can_watch_meditation(user.id)
    
    if not can_watch:
        await query.message.reply_text(
            f"❌ {reason}",
            reply_markup=keyboard.get_meditation_limited_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    video_system = get_video_system_safe()
    
    if not video_system:
        await query.message.reply_text(
            "❌ Система видео временно недоступна. Попробуйте позже.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    # Показываем "загрузка"
    loading_msg = await query.message.reply_text("🔄 Подготавливаем вашу медитацию...")
    
    # Получаем информацию о подписке
    subscription = db.get_user_subscription(user.id)
    has_active_subscription = False
    
    if subscription and subscription[1]:
        sub_end = subscription[1]
        if hasattr(sub_end, 'date'):
            has_active_subscription = sub_end.date() >= datetime.now().date()
    
    # Генерируем отдельные ссылки для YouTube и RUTUBE
    youtube_link = video_system.generate_secure_link(user.id, "youtube")
    rutube_link = video_system.generate_secure_link(user.id, "rutube")
    
    if not youtube_link or not rutube_link:
        await loading_msg.edit_text(
            "❌ Ошибка при подготовке медитации. Попробуйте позже.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )
        return
    
    meditation_text = """
🐚 *Медитация «Дары Моря»*

Погрузитесь в умиротворяющую атмосферу морской медитации, которая поможет вам найти внутренний покой и гармонию.

✨ *Доступные платформы:*
• YouTube 
• RUTUBE 
"""
    
    if not has_active_subscription:
        meditation_text += "\n⚠️ *Бесплатный доступ:* предоставляется только 1 раз на 24 часа"
    
    await loading_msg.edit_text(
        meditation_text,
        parse_mode='Markdown',
        reply_markup=keyboard.get_meditation_platforms_keyboard(youtube_link, rutube_link),
        disable_web_page_preview=True
    )

async def fix_video_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Исправляет таблицу video_links (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Делаем expires_at nullable
        cursor.execute('''
            ALTER TABLE video_links 
            ALTER COLUMN expires_at DROP NOT NULL
        ''')
        
        # Обновляем существующие записи, где expires_at NULL
        cursor.execute('''
            UPDATE video_links 
            SET expires_at = NOW() + INTERVAL '1 year'
            WHERE expires_at IS NULL AND has_subscription = TRUE
        ''')
        
        cursor.execute('''
            UPDATE video_links 
            SET expires_at = NOW() + INTERVAL '24 hours'
            WHERE expires_at IS NULL AND has_subscription = FALSE
        ''')
        
        conn.commit()
        await update.message.reply_text("✅ Таблица video_links исправлена! Колонка expires_at теперь nullable.")
        
    except Exception as e:
        logging.error(f"❌ Error fixing video table: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def update_video_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет таблицу video_links (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        db.update_video_links_table()
        await update.message.reply_text("✅ Таблица video_links обновлена!")
        
    except Exception as e:
        logging.error(f"❌ Error updating video table: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def fix_video_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительно обновляет таблицу video_links (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        db.update_video_links_table()
        await update.message.reply_text("✅ Таблица video_links обновлена! Колонка base_hash добавлена.")
        
    except Exception as e:
        logging.error(f"❌ Error updating video table: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def recreate_video_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Полностью пересоздает таблицу video_links (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Создаем новую таблицу с правильной структурой
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_links_new (
                link_hash TEXT PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                video_url TEXT NOT NULL,
                platform TEXT NOT NULL,
                has_subscription BOOLEAN DEFAULT FALSE,
                access_started_at TIMESTAMP,
                expires_at TIMESTAMP,
                base_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Копируем данные из старой таблицы если она существует
        cursor.execute('''
            INSERT INTO video_links_new (link_hash, user_id, video_url, platform, has_subscription, expires_at, created_at)
            SELECT 
                link_hash, 
                user_id,
                COALESCE(video_url, yandex_link) as video_url,
                COALESCE(platform, 'youtube') as platform,
                COALESCE(has_subscription, FALSE) as has_subscription,
                expires_at,
                created_at
            FROM video_links 
            WHERE link_hash NOT IN (SELECT link_hash FROM video_links_new)
        ''')
        
        # Переименовываем таблицы
        cursor.execute('DROP TABLE IF EXISTS video_links_old')
        cursor.execute('ALTER TABLE IF EXISTS video_links RENAME TO video_links_old')
        cursor.execute('ALTER TABLE video_links_new RENAME TO video_links')
        
        conn.commit()
        await update.message.reply_text("✅ Таблица video_links полностью пересоздана с новой структурой!")
        
    except Exception as e:
        logging.error(f"❌ Error recreating video table: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def report_problem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /report - сообщить о проблеме"""
    report_text = """
🆘 Сообщить о проблеме

Нашли ошибку в работе бота? Есть вопросы или предложения по улучшению? 

Напишите нам о проблеме, и мы обязательно её исправим!

Нажмите кнопку ниже чтобы начать описание проблемы:
"""
    
    await update.message.reply_text(
        report_text,
        reply_markup=keyboard.get_report_problem_keyboard(),
        parse_mode='Markdown'
    )

async def show_report_problem_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о сообщении проблемы из кнопки меню"""
    query = update.callback_query
    logging.info(f"🔧 show_report_problem_from_button called for user {query.from_user.id}")
    
    report_text = """
🆘 Сообщить о проблеме

Нашли ошибку в работе бота? Есть вопросы или предложения по улучшению? 

Напишите нам о проблеме, и мы обязательно её исправим!

Нажмите кнопку ниже чтобы начать описание проблемы:
"""
    
    try:
        await query.message.reply_text(
            report_text,
            reply_markup=keyboard.get_report_problem_keyboard(),
            parse_mode='Markdown'
        )
        logging.info(f"✅ Report problem message sent to user {query.from_user.id}")
    except Exception as e:
        logging.error(f"❌ Error in show_report_problem_from_button: {e}")

async def start_report_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс заполнения формы проблемы"""
    query = update.callback_query
    logging.info(f"🔧 start_report_form called for user {query.from_user.id}")
    
    try:
        # Убираем кнопку из предыдущего сообщения
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Сохраняем состояние формы
        context.user_data['report_form'] = {
            'step': 1,
            'user_id': query.from_user.id,
            'username': query.from_user.username or query.from_user.first_name
        }
        
        # Первый вопрос формы
        question_text = """
📝 Сообщение о проблеме

Пожалуйста, опишите проблему, с которой вы столкнулись, или ваше предложение по улучшению бота.

1. Опишите проблему или предложение максимально подробно:
"""
        
        await query.message.reply_text(
            question_text,
            parse_mode='Markdown'
        )
        logging.info(f"✅ Report form started for user {query.from_user.id}")
        
    except Exception as e:
        logging.error(f"❌ Error in start_report_form: {e}")


async def handle_report_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответы формы проблемы"""
    user_data = context.user_data.get('report_form', {})
    
    if not user_data or 'step' not in user_data:
        # Если нет активной формы, показываем помощь
        await help_command(update, context)
        return
    
    step = user_data['step']
    user_id = user_data['user_id']
    
    # Проверяем, что сообщение от того же пользователя
    if update.effective_user.id != user_id:
        return
    
    user_answer = update.message.text
    
    if step == 1:
        user_data['problem_description'] = user_answer
        user_data['step'] = 2
        question_text = """
2. Укажите, как мы можем с вами связаться для уточнений (Telegram, email или оставьте "не нужно"):
"""
        await update.message.reply_text(question_text, parse_mode='Markdown')
        
    elif step == 2:
        user_data['contact'] = user_answer
        
        # Получаем московское время
        try:
            import pytz
            moscow_tz = pytz.timezone('Europe/Moscow')
            moscow_time = datetime.now(moscow_tz)
        except:
            moscow_time = datetime.now()
        
        # Формируем итоговое сообщение для отправки администраторам
        report_summary = f"""
🆘 *Новое сообщение о проблеме*

👤 *От пользователя:* @{update.effective_user.username or 'не указан'}
🆔 *User ID:* {user_id}

📝 *Описание проблемы:*
{user_data.get('problem_description', 'Не указано')}

📞 *Контакт для связи:* {user_data.get('contact', 'Не указано')}

⏰ *Время сообщения:* {moscow_time.strftime('%d.%m.%Y %H:%M')} (мск)
"""
        
        try:
            # Отправляем сообщение всем администраторам
            from config import ADMIN_IDS
            sent_to_admins = []
            
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=report_summary,
                        parse_mode='Markdown'
                    )
                    sent_to_admins.append(admin_id)
                    logging.info(f"✅ Report sent to admin {admin_id}")
                except Exception as admin_error:
                    logging.error(f"❌ Error sending to admin {admin_id}: {admin_error}")
            
            if sent_to_admins:
                # Подтверждаем пользователю
                success_text = """
✅ *Спасибо! Ваше сообщение отправлено!*

Мы рассмотрим вашу проблему в ближайшее время и постараемся её исправить.

"""
                await update.message.reply_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard.get_main_menu_keyboard()
                )
            else:
                raise Exception("Не удалось отправить ни одному администратору")
            
        except Exception as e:
            logging.error(f"❌ Error sending report: {e}")
            
        
            await update.message.reply_text(
                copyable_report,
                parse_mode='Markdown',
                reply_markup=keyboard.get_main_menu_keyboard()
            )
        
        # Очищаем данные формы
        if 'report_form' in context.user_data:
            del context.user_data['report_form']

async def admin_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает сообщения о проблемах для администратора"""
    user = update.effective_user
    
    # Проверяем, является ли пользователь администратором
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    # Здесь можно добавить логику для просмотра отчетов из базы данных
    # если вы решите сохранять их в базу
    
    await update.message.reply_text(
        "📋 Команда для просмотра сообщений о проблемах.\n"
        "Сообщения автоматически отправляются всем администраторам.",
        parse_mode='Markdown'
    )

async def debug_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная команда для проверки кнопок"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🆘 Сообщить о проблеме", callback_data="report_problem")],
        [InlineKeyboardButton("📝 Написать о проблеме", callback_data="start_report_form")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 Отладочные кнопки:",
        reply_markup=reply_markup
    )

async def debug_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная команда для проверки кнопок сообщения о проблеме"""
    user = update.effective_user
    logging.info(f"🔧 DEBUG: debug_report called by user {user.id}")
    
    # Простая тестовая клавиатура
    keyboard = [
        [InlineKeyboardButton("🆘 Тест: Сообщить о проблеме", callback_data="report_problem")],
        [InlineKeyboardButton("📝 Тест: Написать о проблеме", callback_data="start_report_form")],
        [InlineKeyboardButton("✅ Тест: Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 **ТЕСТ КНОПОК СООБЩЕНИЯ О ПРОБЛЕМЕ**\n\nНажмите любую кнопку:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def test_report_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для проверки кнопок сообщения о проблеме"""
    logging.info(f"🔧 TEST: test_report_buttons called by user {update.effective_user.id}")
    
    # Тестовая клавиатура
    keyboard = [
        [InlineKeyboardButton("🆘 Тест: Сообщить о проблеме", callback_data="report_problem")],
        [InlineKeyboardButton("📝 Тест: Написать о проблеме", callback_data="start_report_form")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 **ТЕСТ КНОПОК**\n\nНажмите кнопки для проверки:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_payment_method_selection(query, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор платежной системы"""
    await query.answer()
    
    payment_method = query.data.replace("payment_", "")
    
    if payment_method == "yookassa":
        # Показываем выбор подписки для ЮKassa (оригинальный способ)
        await show_subscription_choice_original(query, context)
    elif payment_method == "paypal":
        # Показываем выбор подписки для PayPal
        await show_paypal_subscription_choice(query, context)

async def show_subscription_choice_original(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает выбор подписки (оригинальный способ)"""
    subscription_text = """
💎 Премиум подписка

Откройте полный доступ к возможностям бота:

✨ Что входит:
• 5 карт дня вместо 1
• Послание дня (ежедневно)
• Доступ к Техникам самопомощи
• Медитация «Дары моря»

🎯 Тарифы:
• 1 месяц - 99₽
• 3 месяца - 199₽ 
• 6 месяцев - 399₽
• 1 год - 799₽

Выберите срок подписки:
"""
    
    await query.message.reply_text(
        subscription_text,
        reply_markup=keyboard.get_subscription_keyboard(),  # Оригинальная клавиатура
        parse_mode='Markdown'
    )


async def show_yookassa_subscription_choice(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает выбор подписки для ЮKassa"""
    subscription_text = """
💎 Премиум подписка (ЮKassa)

Откройте полный доступ к возможностям бота:

✨ Что входит:
• 5 карт дня вместо 1
• Послание дня (ежедневно)
• Доступ к Техникам самопомощи
• Медитация «Дары моря»

🎯 Тарифы (в рублях):
• 1 месяц - 99₽
• 3 месяца - 199₽ 
• 6 месяцев - 399₽
• 1 год - 799₽

Выберите срок подписки:
"""
    
    # Отправляем новое сообщение с выбором тарифов
    await query.message.reply_text(
        subscription_text,
        reply_markup=keyboard.get_yookassa_subscription_keyboard(),
        parse_mode='Markdown'
    )

async def show_paypal_subscription_choice(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает выбор подписки для PayPal"""
    subscription_text = """
💎 Премиум подписка

Откройте полный доступ к возможностям бота:

✨ Что входит:
• 5 карт дня вместо 1
• Послание дня (ежедневно)
• Доступ к Техникам самопомощи
• Медитация «Дары моря»

🎯 Тарифы (в израильских шекелях):
• 1 месяц - 5.00₪
• 3 месяца - 9.00₪ 
• 6 месяцев - 17.00₪
• 1 год - 35.00₪

Выберите срок подписки:
"""
    
    await query.message.reply_text(
        subscription_text,
        reply_markup=keyboard.get_paypal_subscription_keyboard(),
        parse_mode='Markdown'
    )

async def handle_paypal_subscription_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор типа подписки PayPal"""
    query = update.callback_query
    await query.answer()
    
    try:
        subscription_type = query.data.replace("paypal_", "")
        user_id = query.from_user.id
        
        logging.info(f"🔄 PayPal subscription selected: {subscription_type} by user {user_id}")
        
        # Проверяем, что тип подписки существует в PayPal ценах
        if subscription_type not in PAYPAL_PRICES:
            await query.message.reply_text(
                "❌ Ошибка: выбран неверный тип подписки.",
                reply_markup=keyboard.get_main_menu_keyboard()
            )
            return
        
        price = PAYPAL_PRICES[subscription_type]
        duration = SUBSCRIPTION_NAMES[subscription_type]
        
        # ИСПОЛЬЗУЕМ СТАТИЧЕСКИЕ ССЫЛКИ PAYPAL (не ЮKassa!)
        payment_url = PAYPAL_LINKS.get(subscription_type)
        
        if not payment_url:
            await query.message.reply_text(
                "❌ Ошибка: ссылка для оплаты PayPal не найдена. Свяжитесь с администратором.",
                reply_markup=keyboard.get_main_menu_keyboard()
            )
            return
        
        # Генерируем простой payment_id для PayPal
        payment_id = f"paypal_{subscription_type}_{user_id}_{int(datetime.now().timestamp())}"
        db.save_paypal_payment(user_id, subscription_type, price, payment_id)
        
        # Сохраняем в контексте
        context.user_data['paypal_payment_id'] = payment_id
        context.user_data['subscription_type'] = subscription_type
        
        payment_text = f"""
💎 Премиум подписка - {duration} (PayPal)

Стоимость: {price}₪

Нажмите кнопку "💳 Оплатить" для перехода к оплате.

После успешной оплаты подписка активируется автоматически в течение 1-2 минут.

Если подписка не активировалась, нажмите "🔄 Проверить оплату".
"""
        
        await query.message.reply_text(
            payment_text,
            reply_markup=keyboard.get_paypal_payment_keyboard(subscription_type, payment_url, payment_id),
            parse_mode='Markdown'
        )
        
        logging.info(f"✅ PayPal payment message sent for user {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Error in handle_paypal_subscription_selection: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка при создании платежа. Попробуйте позже.",
            reply_markup=keyboard.get_main_menu_keyboard()
        )

async def handle_paypal_payment_check(query, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет статус оплаты PayPal"""
    await query.answer()
    
    user_id = query.from_user.id
    payment_id = context.user_data.get('paypal_payment_id')
    subscription_type = context.user_data.get('subscription_type')
    
    if not payment_id:
        await query.message.reply_text(
            "❌ Не найден активный платеж PayPal. Пожалуйста, начните процесс заново.",
            reply_markup=keyboard.get_paypal_subscription_keyboard()
        )
        return
    
    # Сначала проверяем базу данных - возможно подписка уже активирована
    subscription = db.get_user_subscription(user_id)
    if subscription:
        await handle_successful_payment(query, subscription)
        return
    
    # Для статических ссылок PayPal просто сообщаем, что проверка в процессе
    if payment_id.startswith('paypal_'):
        await query.message.reply_text(
            "⏳ Платеж обрабатывается...\n\n"
            "✅ Автоматическая проверка активна - подписка активируется сама при успешной оплате.\n"
            "Обычно это занимает 1-5 минут.\n\n"
            "Вы можете закрыть это окно и вернуться позже.",
            reply_markup=keyboard.get_paypal_check_keyboard(subscription_type, payment_id)
        )
    else:
        await query.message.reply_text(
            "❌ Неизвестный тип платежа.",
            reply_markup=keyboard.get_paypal_subscription_keyboard()
        )

async def handle_successful_payment(query, subscription):
    """Обрабатывает успешную оплату"""
    subscription_type, end_date = subscription
    
    if hasattr(end_date, 'strftime'):
        end_date_str = end_date.strftime('%d.%m.%Y')
    else:
        end_date_str = str(end_date)[:10]
    
    success_text = f"""
✅ Оплата подтверждена!

Ваша премиум подписка активирована.

💎 Тип подписки: {SUBSCRIPTION_NAMES.get(subscription_type, subscription_type)}
📅 Действует до: {end_date_str}

✨ Теперь вам доступны все премиум-функции!
"""
    
    await query.message.reply_text(
        success_text,
        reply_markup=keyboard.get_payment_success_keyboard(),
        parse_mode='Markdown'
    )

async def update_payments_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет таблицу payments (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Добавляем недостающие колонки
        cursor.execute('''
            DO $$ 
            BEGIN
                -- Добавляем payment_method если нет
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='payments' AND column_name='payment_method') THEN
                    ALTER TABLE payments ADD COLUMN payment_method TEXT DEFAULT 'yookassa';
                END IF;
                
                -- Добавляем product_type если нет
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='payments' AND column_name='product_type') THEN
                    ALTER TABLE payments ADD COLUMN product_type TEXT DEFAULT 'subscription';
                END IF;
                
                -- Добавляем created_at если нет
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='payments' AND column_name='created_at') THEN
                    ALTER TABLE payments ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                END IF;
            END $$;
        ''')
        
        conn.commit()
        await update.message.reply_text("✅ Таблица payments обновлена! Добавлены колонки payment_method, product_type, created_at")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def manual_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручное включение подписки для пользователя (только для администратора)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    # Проверяем аргументы команды
    if not context.args or len(context.args) < 2:
        help_text = """
📋 *Использование команды:*
`/subscribe_user <user_id> <тип_подписки> [дней]`

*Типы подписок:*
• `month` - 1 месяц (30 дней)
• `3months` - 3 месяца (90 дней) 
• `6months` - 6 месяцев (180 дней)
• `year` - 1 год (365 дней)

*Примеры:*
`/subscribe_user 123456789 month` - подписка на 1 месяц
`/subscribe_user 123456789 year 400` - подписка на 400 дней
`/subscribe_user 123456789 custom 15` - подписка на 15 дней
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(context.args[0])
        subscription_type = context.args[1].lower()
        
        # Определяем длительность подписки
        subscription_durations = {
            'month': 30,
            '3months': 90,
            '6months': 180, 
            'year': 365
        }
        
        if subscription_type in subscription_durations:
            duration_days = subscription_durations[subscription_type]
            subscription_name = {
                'month': '1 месяц',
                '3months': '3 месяца',
                '6months': '6 месяцев', 
                'year': '1 год'
            }.get(subscription_type, subscription_type)
        elif subscription_type == 'custom' and len(context.args) >= 3:
            duration_days = int(context.args[2])
            subscription_name = f"{duration_days} дней"
        else:
            # Если указана кастомная длительность
            duration_days = int(context.args[2]) if len(context.args) >= 3 else 30
            subscription_name = f"{duration_days} дней"
        
        # Получаем информацию о пользователе
        user_info = db.get_user_info(target_user_id)
        if not user_info:
            await update.message.reply_text(f"❌ Пользователь с ID {target_user_id} не найден")
            return
        
        # Активируем подписку
        success, message = db.create_manual_subscription(target_user_id, subscription_type, duration_days)
        
        if success:
            # Формируем сообщение об успехе
            user_display = f"@{user_info['username']}" if user_info['username'] else user_info['first_name'] or f"ID {target_user_id}"
            
            success_text = f"""
✅ *Подписка успешно активирована!*

👤 *Пользователь:* {user_display}
🆔 *ID:* {target_user_id}
💎 *Тип подписки:* {subscription_name}
📅 *Длительность:* {duration_days} дней
📊 *Карт в истории:* {user_info['total_cards']}
📅 *Регистрация:* {user_info['registered_date'].strftime('%d.%m.%Y') if user_info['registered_date'] else 'Неизвестно'}

{message}
"""
            await update.message.reply_text(success_text, parse_mode='Markdown')
            
            # Пытаемся отправить уведомление пользователю
            try:
                from telegram import Bot
                from config import BOT_TOKEN
                
                bot = Bot(token=BOT_TOKEN)
                
                user_notification = f"""
🎉 *Вам активирована премиум подписка!*

💎 *Тип подписки:* {subscription_name}
📅 *Действует до:* {(datetime.now() + timedelta(days=duration_days)).strftime('%d.%m.%Y')}

✨ *Теперь вам доступны:*
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Техники самопомощи
• Медитация «Дары Моря»

Наслаждайтесь полным доступом! 💫
"""
                await bot.send_message(
                    chat_id=target_user_id,
                    text=user_notification,
                    parse_mode='Markdown'
                )
                logging.info(f"✅ Notification sent to user {target_user_id}")
                
            except Exception as notify_error:
                logging.error(f"❌ Error sending notification to user {target_user_id}: {notify_error}")
                await update.message.reply_text(f"⚠️ Подписка активирована, но не удалось отправить уведомление пользователю: {notify_error}")
                
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя или количества дней")
    except Exception as e:
        logging.error(f"❌ Error in manual_subscription: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о пользователе (только для администратора)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID пользователя\nПример: `/user_info 123456789`", parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(context.args[0])
        user_info = db.get_user_info(target_user_id)
        
        if not user_info:
            await update.message.reply_text(f"❌ Пользователь с ID {target_user_id} не найден")
            return
        
        # Получаем информацию о подписке
        subscription = db.get_user_subscription(target_user_id)
        
        # Форматируем информацию
        user_display = f"@{user_info['username']}" if user_info['username'] else user_info['first_name'] or f"ID {target_user_id}"
        premium_status = "✅ Активна" if user_info['is_premium'] else "❌ Неактивна"
        
        subscription_info = "❌ Нет активной подписки"
        if subscription:
            sub_type, end_date = subscription
            if hasattr(end_date, 'strftime'):
                end_date_str = end_date.strftime('%d.%m.%Y')
            else:
                end_date_str = str(end_date)[:10]
            
            subscription_info = f"✅ {sub_type} (до {end_date_str})"
        
        info_text = f"""
👤 *Информация о пользователе*

*Имя:* {user_display}
*ID:* {target_user_id}
*Премиум статус:* {premium_status}
*Подписка:* {subscription_info}
*Карт в истории:* {user_info['total_cards']}
*Лимит карт:* {user_info.get('daily_cards_limit', 1)}/день
*Дата регистрации:* {user_info['registered_date'].strftime('%d.%m.%Y') if user_info['registered_date'] else 'Неизвестно'}
"""
        await update.message.reply_text(info_text, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя")
    except Exception as e:
        logging.error(f"❌ Error in user_info: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

async def show_buy_from_button(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о покупке из кнопки меню"""
    user = query.from_user
    
    # Проверяем, покупал ли пользователь уже колоду
    if db.has_purchased_deck(user.id):
        # Если уже покупал - сразу отправляем файлы
        await send_deck_files_to_query(query, context, user.id)
        return

    buy_text = """
🛒 Купить цифровую колоду

Вы можете приобрести полную цифровую версию колоды метафорических карт «Настроение как море»:

✨ Что входит в комплект:
• 88 карт без рамки (Возможности)
• 88 карт с рамкой (Ограничения) 
• Методическое пособие с посланиями ко всем картам

💎 Формат файлов: PDF, ZIP, RAR
📦 Мгновенная доставка: файлы придут сразу после оплаты

Выберите способ оплаты:

🇷🇺 Оплата из России (999₽)
🌍 Оплата из любой точки мира (80₪)

Обе системы обеспечивают безопасную оплату и мгновенную доставку.
"""
    
    await query.message.reply_text(
        buy_text,
        reply_markup=keyboard.get_buy_deck_keyboard(),
        parse_mode='Markdown'
    )

async def handle_buy_deck_russia(query, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор оплаты из России"""
    await handle_buy_deck(query, context)

async def handle_deck_payment_paypal(query, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает оплату колоды через PayPal (объединенная версия)"""
    user = query.from_user
    
    # Проверяем, покупал ли пользователь уже колоду
    if db.has_purchased_deck(user.id):
        await send_deck_files_to_query(query, context, user.id)
        return
    
    from config import PAYPAL_DECK_LINK, DECK_PRICE_ILS
    
    # Генерируем payment_id для отслеживания
    payment_id = f"paypal_deck_{user.id}_{int(datetime.now().timestamp())}"
    
    # Сохраняем информацию о платеже в базу ДО оплаты с product_type='deck'
    try:
        from paypal_payment import paypal_processor
        paypal_processor.save_paypal_payment(
            user_id=user.id,
            amount=DECK_PRICE_ILS,
            payment_id=payment_id,
            product_type='deck'
        )
        
        logging.info(f"✅ PayPal deck payment record created for user {user.id}")
        
    except Exception as e:
        logging.error(f"❌ Error creating PayPal deck payment record: {e}")
    
    # Сохраняем в контексте БОЛЕЕ НАДЕЖНО
    if 'paypal_deck_payments' not in context.user_data:
        context.user_data['paypal_deck_payments'] = {}
    
    context.user_data['paypal_deck_payments'][user.id] = payment_id
    context.user_data['last_paypal_deck_payment'] = payment_id
    context.user_data['paypal_deck_payment_id'] = payment_id  # для обратной совместимости
    
    # Также сохраняем в bot_data для глобального доступа
    if 'paypal_deck_payments' not in context.bot_data:
        context.bot_data['paypal_deck_payments'] = {}
    context.bot_data['paypal_deck_payments'][user.id] = payment_id
    
    payment_text = f"""
🛒 Цифровая колода «Настроение как море»

💎 Стоимость: {DECK_PRICE_ILS}₪

✨ Что входит:
• 88 карт без рамки (Возможности)
• 88 карт с рамкой (Ограничения) 
• Методическое пособие с посланиями

Нажмите кнопку "💳 Оплатить" для перехода к оплате через PayPal.

После успешной оплаты файлы колоды будут отправлены автоматически в течение 1-2 минут.

Если файлы не пришли, нажмите "🔄 Проверить оплату".

💡 *ID платежа:* `{payment_id}`
"""
    
    await query.message.reply_text(
        payment_text,
        reply_markup=keyboard.get_paypal_deck_payment_keyboard(PAYPAL_DECK_LINK, payment_id),
        parse_mode='Markdown'
    )

async def handle_buy_deck_international(query, context: ContextTypes.DEFAULT_TYPE):
    """Перенаправляет на обработку оплаты через PayPal"""
    await handle_deck_payment_paypal(query, context)

async def handle_paypal_deck_payment_check(query, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет статус оплаты колоды через PayPal"""
    user = query.from_user
    
    # СНАЧАЛА проверяем, не купил ли пользователь уже колоду
    if db.has_purchased_deck(user.id):
        await send_deck_files_to_query(query, context, user.id)
        return
    
    payment_id = None
    if query.data.startswith('check_paypal_deck_'):
        payment_id = query.data.replace('check_paypal_deck_', '')
    
    # 🔄 АВТОМАТИЧЕСКАЯ АКТИВАЦИЯ ДЛЯ ТЕСТИРОВАНИЯ
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, amount FROM payments 
            WHERE (payment_id = %s OR user_id = %s) 
            AND product_type = 'deck'
            AND amount = 80.00
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (payment_id, user.id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            status, amount = result
            if amount == 80.00:  # Сумма совпадает с ценой колоды
                logging.info(f"💰 Amount matches deck price (80₪), activating purchase for user {user.id}")
                
                # Активируем покупку
                from paypal_payment import paypal_processor
                if paypal_processor.activate_paypal_deck_purchase(user.id):
                    # Обновляем статус платежа (с обработкой ошибки)
                    try:
                        paypal_processor.update_payment_status(payment_id, 'success')
                    except Exception as e:
                        logging.error(f"❌ Error updating payment status: {e}")
                        # Продолжаем, даже если не удалось обновить статус
                    
                    await send_deck_files_to_query(query, context, user.id)
                    return
                else:
                    await query.message.reply_text(
                        "❌ Ошибка активации покупки. Свяжитесь с поддержкой.",
                        reply_markup=keyboard.get_buy_deck_keyboard()
                    )
                    return
        
        # Если автоматическая активация не сработала, показываем стандартное сообщение
        await query.message.reply_text(
            "⏳ Платеж обрабатывается PayPal...\n\n"
            "✅ *Если вы уже оплатили:*\n"
            "• Файлы отправятся автоматически\n"  
            "• Обычно это занимает 1-5 минут\n"
            "• Вы можете закрыть это окно\n\n"
            "🔄 *Статус:* ожидание подтверждения от PayPal\n"
            "❌ *Если оплата не прошла:* попробуйте снова",
            reply_markup=keyboard.get_paypal_deck_check_keyboard(payment_id),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"❌ Error checking PayPal deck payment: {e}")
        await query.message.reply_text(
            "❌ Ошибка при проверке платежа.",
            reply_markup=keyboard.get_buy_deck_keyboard()
        )

async def update_payments_structure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет структуру таблицы payments (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        db.update_payments_table_structure()
        await update.message.reply_text("✅ Структура таблицы payments обновлена! subscription_type теперь nullable.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def view_my_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает активные платежи пользователя"""
    user = update.effective_user
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT payment_id, product_type, status, amount, currency, created_at 
            FROM payments 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (user.id,))
        
        payments = cursor.fetchall()
        conn.close()
        
        if not payments:
            await update.message.reply_text("📭 У вас нет активных платежей.")
            return
        
        message = "💳 *Ваши последние платежи:*\n\n"
        
        for payment in payments:
            payment_id, product_type, status, amount, currency, created_at = payment
            
            status_emoji = "✅" if status == 'success' else "⏳" if status == 'pending' else "❌"
            product_name = "Колода" if product_type == 'deck' else "Подписка"
            
            message += f"{status_emoji} *{product_name}*\n"
            message += f"💰 {amount} {currency}\n"
            message += f"🆔 `{payment_id}`\n"
            message += f"📅 {created_at.strftime('%d.%m.%Y %H:%M')}\n"
            message += f"📊 Статус: {status}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"❌ Error viewing payments: {e}")
        await update.message.reply_text("❌ Ошибка при получении информации о платежах.")

async def update_database_structure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет структуру базы данных (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Добавляем колонку email если её нет
        cursor.execute('''
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='email') THEN
                    ALTER TABLE users ADD COLUMN email TEXT;
                END IF;
            END $$;
        ''')
        
        # Добавляем колонку customer_email в payments если её нет
        cursor.execute('''
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='payments' AND column_name='customer_email') THEN
                    ALTER TABLE payments ADD COLUMN customer_email TEXT;
                END IF;
            END $$;
        ''')
        
        conn.commit()
        await update.message.reply_text("✅ Структура базы данных обновлена! Добавлены колонки email и customer_email")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        
async def add_phone_column(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет колонку phone в таблицу users (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='phone') THEN
                    ALTER TABLE users ADD COLUMN phone TEXT;
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='payments' AND column_name='customer_phone') THEN
                    ALTER TABLE payments ADD COLUMN customer_phone TEXT;
                END IF;
            END $$;
        ''')
        
        conn.commit()
        await update.message.reply_text("✅ Добавлены колонки phone и customer_phone")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def fix_expired_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручное обновление истекших подписок"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        expired_count = db.check_and_update_expired_subscriptions()
        
        if expired_count > 0:
            await update.message.reply_text(f"✅ Обновлено {expired_count} истекших подписок")
        else:
            await update.message.reply_text("✅ Нет истекших подписок для обновления")
            
    except Exception as e:
        logging.error(f"❌ Error fixing expired subscriptions: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def fix_user_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительное обновление подписки пользователя"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    if not context.args:
        target_user_id = user.id
    else:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный формат user_id")
            return
    
    try:
        # Проверяем и обновляем подписку
        updated = db.check_user_subscription_expiry(target_user_id)
        
        if updated:
            await update.message.reply_text(f"✅ Подписка пользователя {target_user_id} обновлена (истекшая)")
        else:
            # Показываем текущий статус
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT is_premium, premium_until, daily_cards_limit 
                FROM users 
                WHERE user_id = %s
            ''', (target_user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                is_premium, premium_until, limit = result
                await update.message.reply_text(
                    f"📊 Статус пользователя {target_user_id}:\n"
                    f"💎 Premium: {is_premium}\n"
                    f"📅 Until: {premium_until}\n"
                    f"🎯 Limit: {limit}\n\n"
                    f"ℹ️ Подписка еще активна или не найдена"
                )
            else:
                await update.message.reply_text(f"❌ Пользователь {target_user_id} не найден")
            
    except Exception as e:
        logging.error(f"❌ Error fixing user subscription: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def add_missing_columns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет недостающие колонки в таблицы (только для админов)"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Добавляем ВСЕ недостающие колонки
        cursor.execute('''
            DO $$ 
            BEGIN
                -- В таблице users
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='email') THEN
                    ALTER TABLE users ADD COLUMN email TEXT;
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='phone') THEN
                    ALTER TABLE users ADD COLUMN phone TEXT;
                END IF;
                
                -- В таблице payments
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='payments' AND column_name='customer_email') THEN
                    ALTER TABLE payments ADD COLUMN customer_email TEXT;
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='payments' AND column_name='customer_phone') THEN
                    ALTER TABLE payments ADD COLUMN customer_phone TEXT;
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='payments' AND column_name='custom_id') THEN
                    ALTER TABLE payments ADD COLUMN custom_id TEXT;
                END IF;
            END $$;
        ''')
        
        conn.commit()
        await update.message.reply_text("✅ Добавлены все недостающие колонки в базу!")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def process_unknown_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неидентифицированных платежей (только для админа)"""
    user = update.effective_user
    
    if user.id != 891422895:  # Только вы
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем необработанные платежи
        cursor.execute('''
            SELECT id, payment_id, amount, customer_email, customer_phone, payment_data, payment_date
            FROM unknown_payments 
            WHERE processed = FALSE
            ORDER BY payment_date DESC
            LIMIT 10
        ''')
        
        payments = cursor.fetchall()
        
        if not payments:
            await update.message.reply_text("✅ Нет необработанных платежей")
            return
        
        message = "🔄 *Необработанные платежи:*\n\n"
        
        for i, (record_id, payment_id, amount, email, phone, payment_data_json, payment_date) in enumerate(payments, 1):
            message += f"{i}. *ID:* {payment_id}\n"
            message += f"   💰 {amount}₽ | 📧 {email or 'нет'} | 📞 {phone or 'нет'}\n"
            message += f"   📅 {payment_date.strftime('%d.%m.%Y %H:%M')}\n"
            
            # Кнопки для быстрой обработки
            keyboard = []
            
            if email:
                keyboard.append([
                    InlineKeyboardButton(f"🔍 Найти по email", 
                                        callback_data=f"find_by_email_{record_id}")
                ])
            
            if phone:
                keyboard.append([
                    InlineKeyboardButton(f"📞 Найти по телефону", 
                                        callback_data=f"find_by_phone_{record_id}")
                ])
            
            keyboard.append([
                InlineKeyboardButton("✅ Обработать вручную", 
                                    callback_data=f"process_manually_{record_id}"),
                InlineKeyboardButton("❌ Игнорировать", 
                                    callback_data=f"ignore_payment_{record_id}")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            message = ""  # Сбрасываем для следующего платежа
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error processing unknown payments: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_find_by_email(query, context: ContextTypes.DEFAULT_TYPE):
    """Ищет пользователя по email для обработки платежа"""
    await query.answer()
    record_id = query.data.replace("find_by_email_", "")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем информацию о платеже
        cursor.execute('''
            SELECT customer_email FROM unknown_payments WHERE id = %s
        ''', (record_id,))
        
        result = cursor.fetchone()
        if not result or not result[0]:
            await query.message.reply_text("❌ Email не найден в записи")
            return
        
        email = result[0]
        
        # Ищем пользователя по email
        cursor.execute('''
            SELECT user_id, username, first_name, last_name 
            FROM users 
            WHERE email = %s OR username LIKE %s
            LIMIT 5
        ''', (email, f"%{email}%"))
        
        users = cursor.fetchall()
        
        if users:
            message = f"🔍 *Найдены пользователи по email {email}:*\n\n"
            for i, (user_id, username, first_name, last_name) in enumerate(users, 1):
                username_display = f"@{username}" if username else f"{first_name} {last_name}".strip()
                message += f"{i}. {username_display} (ID: {user_id})\n"
            
            keyboard = [
                [InlineKeyboardButton(f"✅ Активировать подписку для {users[0][0]}", 
                                     callback_data=f"activate_for_{users[0][0]}_{record_id}")]
            ]
            
            if len(users) > 1:
                for i, (user_id, _, _, _) in enumerate(users[1:], 2):
                    keyboard.append([
                        InlineKeyboardButton(f"Выбрать {i}: ID {user_id}", 
                                           callback_data=f"select_user_{user_id}_{record_id}")
                    ])
            
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_process_{record_id}")])
            
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.message.reply_text(
                f"❌ Пользователи с email {email} не найдены",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Поиск вручную", callback_data=f"manual_search_{record_id}")]
                ])
            )
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error finding by email: {e}")
        await query.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_find_by_phone(query, context: ContextTypes.DEFAULT_TYPE):
    """Ищет пользователя по телефону для обработки платежа"""
    await query.answer()
    record_id = query.data.replace("find_by_phone_", "")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем информацию о платеже
        cursor.execute('''
            SELECT customer_phone FROM unknown_payments WHERE id = %s
        ''', (record_id,))
        
        result = cursor.fetchone()
        if not result or not result[0]:
            await query.message.reply_text("❌ Телефон не найден в записи")
            return
        
        phone = result[0]
        
        # Очищаем номер от лишних символов
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Ищем пользователя по телефону
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, phone
            FROM users 
            WHERE phone LIKE %s OR phone LIKE %s
            LIMIT 5
        ''', (f"%{clean_phone}%", f"%{phone}%"))
        
        users = cursor.fetchall()
        
        if users:
            message = f"🔍 *Найдены пользователи по телефону {phone}:*\n\n"
            for i, (user_id, username, first_name, last_name, user_phone) in enumerate(users, 1):
                username_display = f"@{username}" if username else f"{first_name} {last_name}".strip()
                message += f"{i}. {username_display} (ID: {user_id}, тел: {user_phone})\n"
            
            keyboard = [
                [InlineKeyboardButton(f"✅ Активировать подписку для {users[0][0]}", 
                                     callback_data=f"activate_for_{users[0][0]}_{record_id}")]
            ]
            
            if len(users) > 1:
                for i, (user_id, _, _, _, _) in enumerate(users[1:], 2):
                    keyboard.append([
                        InlineKeyboardButton(f"Выбрать {i}: ID {user_id}", 
                                           callback_data=f"select_user_{user_id}_{record_id}")
                    ])
            
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_process_{record_id}")])
            
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.message.reply_text(
                f"❌ Пользователи с телефоном {phone} не найдены",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Поиск вручную", callback_data=f"manual_search_{record_id}")]
                ])
            )
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error finding by phone: {e}")
        await query.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_process_manually(query, context: ContextTypes.DEFAULT_TYPE):
    """Начинает ручную обработку платежа"""
    await query.answer()
    record_id = query.data.replace("process_manually_", "")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем информацию о платеже
        cursor.execute('''
            SELECT payment_id, amount, customer_email, customer_phone, payment_date
            FROM unknown_payments WHERE id = %s
        ''', (record_id,))
        
        result = cursor.fetchone()
        if not result:
            await query.message.reply_text("❌ Запись не найдена")
            return
        
        payment_id, amount, email, phone, payment_date = result
        
        message = f"""
📋 *Ручная обработка платежа*

🆔 ID платежа: `{payment_id}`
💰 Сумма: {amount}₽
📧 Email: {email or 'не указан'}
📞 Телефон: {phone or 'не указан'}
📅 Дата: {payment_date.strftime('%d.%m.%Y %H:%M')}

Введите ID пользователя для активации подписки:
(или нажмите кнопки для поиска)
"""
        
        keyboard = []
        if email:
            keyboard.append([InlineKeyboardButton(f"🔍 Поиск по email", callback_data=f"find_by_email_{record_id}")])
        if phone:
            keyboard.append([InlineKeyboardButton(f"📞 Поиск по телефону", callback_data=f"find_by_phone_{record_id}")])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_process_{record_id}")])
        
        # Сохраняем состояние ручной обработки
        context.user_data['manual_payment_processing'] = {
            'record_id': record_id,
            'payment_id': payment_id,
            'amount': amount
        }
        
        await query.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error starting manual processing: {e}")
        await query.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_ignore_payment(query, context: ContextTypes.DEFAULT_TYPE):
    """Помечает платеж как игнорируемый"""
    await query.answer()
    record_id = query.data.replace("ignore_payment_", "")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE unknown_payments 
            SET processed = TRUE, status = 'ignored'
            WHERE id = %s
        ''', (record_id,))
        
        conn.commit()
        
        await query.message.reply_text(
            f"✅ Платеж {record_id} помечен как игнорируемый",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Показать другие платежи", callback_data="show_unknown_payments")]
            ])
        )
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error ignoring payment: {e}")
        await query.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_manual_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ручной ввод ID пользователя"""
    if 'manual_payment_processing' not in context.user_data:
        return
    
    try:
        user_input = update.message.text.strip()
        
        if not user_input.isdigit():
            await update.message.reply_text("❌ Введите числовой ID пользователя")
            return
        
        user_id = int(user_input)
        processing_data = context.user_data['manual_payment_processing']
        record_id = processing_data['record_id']
        amount = float(processing_data['amount'])
        
        # Проверяем существование пользователя
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE user_id = %s', (user_id,))
        
        if not cursor.fetchone():
            await update.message.reply_text(f"❌ Пользователь с ID {user_id} не найден")
            return
        
        # Определяем тип подписки по сумме
        subscription_type = determine_subscription_type_from_amount(amount)
        
        if not subscription_type:
            await update.message.reply_text(
                f"❌ Не могу определить тип подписки для суммы {amount}₽\n"
                f"Используйте: /subscribe_user {user_id} month"
            )
            return
        
        # Активируем подписку
        success, message = db.create_manual_subscription(user_id, subscription_type, 30)
        
        if success:
            # Помечаем платеж как обработанный
            cursor.execute('''
                UPDATE unknown_payments 
                SET processed = TRUE, status = 'manual_processed', processed_by = %s
                WHERE id = %s
            ''', (update.effective_user.id, record_id))
            
            conn.commit()
            conn.close()
            
            # Очищаем состояние
            del context.user_data['manual_payment_processing']
            
            await update.message.reply_text(
                f"✅ Подписка успешно активирована для пользователя {user_id}\n\n"
                f"💎 Тип: {subscription_type}\n"
                f"💰 Сумма: {amount}₽\n"
                f"🆔 Запись: {record_id}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Другие платежи", callback_data="show_unknown_payments")]
                ])
            )
        else:
            await update.message.reply_text(f"❌ Ошибка: {message}")
            
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID")
    except Exception as e:
        logger.error(f"❌ Error processing manual input: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_activate_for_user(query, context: ContextTypes.DEFAULT_TYPE):
    """Активирует подписку для выбранного пользователя"""
    await query.answer()
    data_parts = query.data.replace("activate_for_", "").split("_")
    
    if len(data_parts) < 2:
        await query.message.reply_text("❌ Неверный формат данных")
        return
    
    user_id = int(data_parts[0])
    record_id = data_parts[1]
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем информацию о платеже
        cursor.execute('''
            SELECT amount FROM unknown_payments WHERE id = %s
        ''', (record_id,))
        
        result = cursor.fetchone()
        if not result:
            await query.message.reply_text("❌ Запись о платеже не найдена")
            return
        
        amount = float(result[0])
        
        # Определяем тип подписки
        subscription_type = determine_subscription_type_from_amount(amount)
        
        if not subscription_type:
            await query.message.reply_text(
                f"❌ Не могу определить тип подписки для суммы {amount}₽\n"
                f"Используйте: /subscribe_user {user_id} month"
            )
            return
        
        # Активируем подписку
        success, message = db.create_manual_subscription(user_id, subscription_type, 30)
        
        if success:
            # Помечаем платеж как обработанный
            cursor.execute('''
                UPDATE unknown_payments 
                SET processed = TRUE, status = 'auto_processed', processed_by = %s
                WHERE id = %s
            ''', (query.from_user.id, record_id))
            
            conn.commit()
            
            await query.message.reply_text(
                f"✅ Подписка успешно активирована!\n\n"
                f"👤 Пользователь: {user_id}\n"
                f"💎 Тип: {subscription_type}\n"
                f"💰 Сумма: {amount}₽\n\n"
                f"Подписка действует 30 дней с момента активации.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Другие платежи", callback_data="show_unknown_payments")]
                ])
            )
        else:
            await query.message.reply_text(f"❌ Ошибка: {message}")
            
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error activating subscription: {e}")
        await query.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_cancel_process(query, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет текущий процесс обработки"""
    await query.answer()
    record_id = query.data.replace("cancel_process_", "")
    
    if 'manual_payment_processing' in context.user_data:
        del context.user_data['manual_payment_processing']
    
    await query.message.reply_text(
        "❌ Обработка отменена",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Вернуться к списку", callback_data="show_unknown_payments")]
        ])
    )

async def show_unknown_payments(query, context: ContextTypes.DEFAULT_TYPE):
    """Показывает необработанные платежи (через callback)"""
    await query.answer()
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Создаем таблицу если её нет
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unknown_payments (
                id SERIAL PRIMARY KEY,
                payment_id TEXT NOT NULL,
                amount DECIMAL,
                customer_email TEXT,
                customer_phone TEXT,
                payment_data JSONB,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                processed BOOLEAN DEFAULT FALSE,
                processed_by BIGINT,
                processed_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            SELECT id, payment_id, amount, customer_email, customer_phone, payment_date
            FROM unknown_payments 
            WHERE processed = FALSE
            ORDER BY payment_date DESC
            LIMIT 10
        ''')
        
        payments = cursor.fetchall()
        conn.close()
        
        if not payments:
            await query.message.reply_text("✅ Нет необработанных платежей")
            return
        
        message = "🔄 *Необработанные платежи:*\n\n"
        
        for i, (record_id, payment_id, amount, email, phone, payment_date) in enumerate(payments, 1):
            message += f"{i}. *ID:* `{payment_id}`\n"
            message += f"   💰 {amount}₽ | 📧 {email or 'нет'} | 📞 {phone or 'нет'}\n"
            message += f"   📅 {payment_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            
            # Кнопки для каждой записи
            keyboard = []
            
            if email:
                keyboard.append([
                    InlineKeyboardButton(f"🔍 Поиск по email", 
                                        callback_data=f"find_by_email_{record_id}")
                ])
            
            if phone:
                keyboard.append([
                    InlineKeyboardButton(f"📞 Поиск по телефону", 
                                        callback_data=f"find_by_phone_{record_id}")
                ])
            
            keyboard.append([
                InlineKeyboardButton("✅ Обработать вручную", 
                                    callback_data=f"process_manually_{record_id}"),
                InlineKeyboardButton("❌ Игнорировать", 
                                    callback_data=f"ignore_payment_{record_id}")
            ])
            
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            message = ""  # Сбрасываем для следующего платежа
        
    except Exception as e:
        logger.error(f"❌ Error showing unknown payments: {e}")
        await query.message.reply_text(f"❌ Ошибка: {str(e)}")

def determine_subscription_type_from_amount(amount: float):
    """Определяет тип подписки по сумме платежа"""
    subscription_types = {
        99.00: "month",
        199.00: "3months", 
        399.00: "6months",
        799.00: "year"
    }
    
    # Проверяем точное совпадение и округленные значения
    if amount in subscription_types:
        return subscription_types[amount]
    
    # Проверяем округление (иногда могут быть копейки)
    for price, sub_type in subscription_types.items():
        if abs(amount - price) < 0.1:  # Разница менее 10 копеек
            return sub_type
    
    return None

