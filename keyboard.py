from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_daily_intro_keyboard():
    """Клавиатура для введения в карту дня"""
    keyboard = [
        [InlineKeyboardButton("👀 Посмотреть карту дня", callback_data="get_daily_card")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_card_reflection_keyboard():
    """Клавиатура после показа карты"""
    keyboard = [
        [InlineKeyboardButton("🦋 Послание дня", callback_data="get_daily_message")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_daily_message_keyboard():
    """Клавиатура после послания дня"""
    keyboard = [
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_history_keyboard():
    """Клавиатура для истории"""
    keyboard = [
        [InlineKeyboardButton("🖼 Показать с картинками", callback_data="show_history_pics")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_history_pics_keyboard():
    """Клавиатура после показа картинок истории"""
    keyboard = [
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_consult_keyboard():
    """Клавиатура для консультации"""
    keyboard = [
        [InlineKeyboardButton("📝 Записаться на консультацию и заполнить форму", callback_data="start_consult_form")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_profile_keyboard():
    """Клавиатура для профиля - только кнопка 'Вернуться в меню'"""
    keyboard = [
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_help_keyboard():
    """Клавиатура для помощи - только кнопка 'Вернуться в меню'"""
    keyboard = [
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_resources_keyboard():
    """Клавиатура для Архипелага ресурсов"""
    keyboard = [
        [InlineKeyboardButton("🌊 Волна Новых Возможностей", callback_data="resource_tide")],
        [InlineKeyboardButton("🔄 Техника 2", callback_data="resource_tech2")],
        [InlineKeyboardButton("🌀 Техника 3", callback_data="resource_tech3")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tide_step1_keyboard():
    """Клавиатура для Шага 1 техники Морской Прилив"""
    keyboard = [
        [InlineKeyboardButton("🎴 Выбрать карту-ограничение", callback_data="tide_step1_card")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tide_step1_reflection_keyboard():
    """Клавиатура после выбора карты-ограничения"""
    keyboard = [
        [InlineKeyboardButton("❓ Вопросы для Саморефлексии", callback_data="tide_step1_questions")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tide_step1_questions_keyboard():
    """Клавиатура после вопросов Шага 1"""
    keyboard = [
        [InlineKeyboardButton("➡️ Продолжить", callback_data="tide_step2")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tide_step2_keyboard():
    """Клавиатура для Шага 2 техники Морской Прилив"""
    keyboard = [
        [InlineKeyboardButton("🎴 Выбрать карту-возможность", callback_data="tide_step2_card")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tide_step2_reflection_keyboard():
    """Клавиатура после выбора карты-возможности"""
    keyboard = [
        [InlineKeyboardButton("❓ Вопросы для Саморефлексии", callback_data="tide_step2_questions")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tide_final_keyboard():
    """Финальная клавиатура техники Морской Прилив"""
    keyboard = [
        [InlineKeyboardButton("✅ Завершить практику", callback_data="complete_tide_practice")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_tide_completion_keyboard():
    """Клавиатура после завершения практики Морской Прилив"""
    keyboard = [
        [InlineKeyboardButton("🗺️ Архипелаг ресурсов", callback_data="resources")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_guide_keyboard():
    """Клавиатура для гайда по ЭИ"""
    keyboard = [
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_buy_keyboard():
    """Клавиатура для покупки колоды"""
    keyboard = [
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_subscription_keyboard():
    """Клавиатура для выбора подписки"""
    keyboard = [
        [InlineKeyboardButton("1 месяц - 99₽", callback_data="subscribe_month")],
        [InlineKeyboardButton("3 месяца - 199₽", callback_data="subscribe_3months")],
        [InlineKeyboardButton("6 месяцев - 399₽", callback_data="subscribe_6months")],
        [InlineKeyboardButton("1 год - 799₽", callback_data="subscribe_year")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard():
    """Обновленная клавиатура для главного меню"""
    keyboard = [
        [InlineKeyboardButton("🎴 Карта дня", callback_data="show_daily_intro")],
        [InlineKeyboardButton("🗺️ Архипелаг ресурсов", callback_data="resources")],
        [InlineKeyboardButton("📚 Гайд по Эмоциональному Интеллекту", callback_data="guide")],
        [InlineKeyboardButton("🛒 Купить колоду онлайн", callback_data="buy")],
        [InlineKeyboardButton("💎 Приобрести подписку", callback_data="subscribe")],
        [InlineKeyboardButton("📊 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📖 История карт", callback_data="history")],
        [InlineKeyboardButton("💫 Консультация", callback_data="consult")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_subscription_choice_keyboard():
    """Клавиатура для выбора подписки (альтернативное название)"""
    return get_subscription_keyboard()  # Используем существующую функцию

def get_payment_success_keyboard():
    """Клавиатура после успешной оплаты"""
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_card_display_keyboard(card_type: str = None):
    """Клавиатура после показа карты дня"""
    keyboard = [
        [InlineKeyboardButton("❓ Как исследовать карту дня", callback_data="card_questions")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_card_questions_keyboard():
    """Клавиатура после показа вопросов к карте"""
    keyboard = [
        [InlineKeyboardButton("🦋 Послание дня", callback_data="get_daily_message")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_message_status_keyboard():
    """Клавиатура для статуса посланий (для бесплатных пользователей)"""
    keyboard = [
        [InlineKeyboardButton("💎 Приобрести подписку", callback_data="subscribe")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_payment_keyboard(subscription_type: str, payment_url: str, payment_id: str):
    """Клавиатура для оплаты"""
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить онлайн", url=payment_url)],
        [InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_payment_{payment_id}")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_payment_check_keyboard(subscription_type: str, payment_id: str):
    """Клавиатура для проверки оплаты"""
    keyboard = [
        [InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_payment_{payment_id}")],
        [InlineKeyboardButton("💎 Выбрать другой тариф", callback_data="subscribe")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


