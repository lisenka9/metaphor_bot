from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_card_keyboard():
    """Клавиатура с одной кнопкой 'Перевернуть карту'"""
    keyboard = [
        [InlineKeyboardButton("🔄 Перевернуть карту", callback_data="flip_card")]
    ]
    return InlineKeyboardMarkup(keyboard)
