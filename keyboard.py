from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_card_keyboard():
    """Клавиатура с одной кнопкой 'Перевернуть карту'"""
    keyboard = [
        [InlineKeyboardButton("Посмотреть вопросы", callback_data="flip_card")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_history_keyboard():
    """Клавиатура для истории"""
    keyboard = [
        [InlineKeyboardButton("🖼 Показать с картинками", callback_data="show_history_pics")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_daily_intro_keyboard():
    """Клавиатура для введения в карту дня"""
    keyboard = [
        [InlineKeyboardButton("🎴 Карта дня", callback_data="get_daily_card")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_card_reflection_keyboard():
    """Клавиатура после показа карты"""
    keyboard = [
        [InlineKeyboardButton("🦋 Послание дня", callback_data="get_daily_message")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_card_keyboard():
    """Клавиатура с одной кнопкой 'Перевернуть карту'"""
    keyboard = [
        [InlineKeyboardButton("🔄 Перевернуть карту", callback_data="flip_card")]
    ]
    return InlineKeyboardMarkup(keyboard)
