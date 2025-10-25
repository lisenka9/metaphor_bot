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
    """Клавиатура для архипелага ресурсов"""
    keyboard = [
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

def get_main_menu_keyboard():
    """Клавиатура для главного меню"""
    keyboard = [
        [InlineKeyboardButton("🎴 Карта дня", callback_data="show_daily_intro")],
        [InlineKeyboardButton("🗺 Архипелаг ресурсов", callback_data="resources")],
        [InlineKeyboardButton("📚 Гайд по Эмоциональному Интеллекту", callback_data="guide")],
        [InlineKeyboardButton("🛒 Купить колоду", callback_data="buy")],
        [InlineKeyboardButton("📊 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📖 История карт", callback_data="history")],
        [InlineKeyboardButton("💫 Консультация", callback_data="consult")]
    ]
    return InlineKeyboardMarkup(keyboard)
