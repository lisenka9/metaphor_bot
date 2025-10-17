from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_daily_intro_keyboard():
    """Клавиатура для введения в карту дня"""
    keyboard = [
        [InlineKeyboardButton("🎴 Карта дня", callback_data="get_daily_card")],
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

def get_card_questions_keyboard():
    """Клавиатура с кнопкой 'Посмотреть вопросы'"""
    keyboard = [
        [InlineKeyboardButton("👁 Посмотреть вопросы", callback_data="flip_card")],
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

def get_main_menu_keyboard():
    """Клавиатура для главного меню"""
    keyboard = [
        [InlineKeyboardButton("🎴 Карта дня", callback_data="get_daily_card")],
        [InlineKeyboardButton("📊 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📚 История карт", callback_data="history")],
        [InlineKeyboardButton("💫 Консультация", callback_data="consult")]
    ]
    return InlineKeyboardMarkup(keyboard)
