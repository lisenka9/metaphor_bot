import sqlite3
import os
from config import DATABASE_PATH, IMAGES_DIR

def check_images():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT card_id, card_name, image_path FROM cards')
    cards = cursor.fetchall()
    
    print("🔍 Проверка карт в базе данных:")
    for card_id, card_name, image_path in cards:
        exists = os.path.exists(image_path)
        status = "✅ ЕСТЬ" if exists else "❌ НЕТ"
        print(f"Карта {card_id} ('{card_name}'): {image_path} - {status}")
    
    conn.close()

if __name__ == '__main__':
    check_images()
