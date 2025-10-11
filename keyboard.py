from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_card_keyboard():
    """Клавиатура с одной кнопкой 'Перевернуть карту'"""
    keyboard = [
        [InlineKeyboardButton("🔄 Перевернуть карту", callback_data="flip_card")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_history_keyboard():
    """Клавиатура для истории"""
    keyboard = [
        [InlineKeyboardButton("🖼 Показать с картинками", callback_data="show_history_pics")]
    ]
    return InlineKeyboardMarkup(keyboard)
