from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_card_keyboard():
    """Клавиатура для интерактивной карты"""
    keyboard = [
        [InlineKeyboardButton("🔄 Перевернуть карту", callback_data="flip_card")],
        [InlineKeyboardButton("❓ Вопросы для размышления", callback_data="show_questions")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_questions_keyboard():
    """Клавиатура после вопросов"""
    keyboard = [
        [InlineKeyboardButton("🃏 Новая карта", callback_data="new_card")],
        [InlineKeyboardButton("💾 Сохранить мысли", callback_data="save_thoughts")]
    ]
    return InlineKeyboardMarkup(keyboard)
