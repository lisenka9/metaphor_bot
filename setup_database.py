# setup_database.py
import sqlite3
import os
from config import DATABASE_PATH, IMAGES_DIR

def setup_database():
    """Полная настройка базы данных: создание таблиц и наполнение картами"""
    
    # Создаем папки если их нет
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    # Подключаемся к базе
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("🔄 Создаем таблицы в базе данных...")
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            daily_cards_limit INTEGER DEFAULT 1,
            last_daily_card_date DATE,
            is_premium BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Таблица карт
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY,
            card_name TEXT NOT NULL,
            image_path TEXT NOT NULL,
            description_text TEXT NOT NULL
        )
    ''')
    
    # Таблица истории выданных карт
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card_id INTEGER,
            drawn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (card_id) REFERENCES cards (card_id)
        )
    ''')
    
    print("✅ Таблицы созданы успешно!")
    print("🔄 Добавляем карты в базу...")
    
    # Данные карт
    cards_data = [
        (1, "1", "images/1.jpg", "Описание карты 1"),
        (2, "2", "images/2.jpg", "Описание карты 2"),
        (3, "3", "images/3.jpg", "Описание карты 3"),
        (4, "4", "images/4.jpg", "Описание карты 4"),
        (5, "5", "images/5.jpg", "Описание карты 5")
    ]
    
    for card in cards_data:
        cursor.execute('''
            INSERT OR REPLACE INTO cards 
            (card_id, card_name, image_path, description_text)
            VALUES (?, ?, ?, ?)
        ''', card)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Добавлено {len(cards_data)} карт в базу данных")
    print("🎉 База данных готова к работе!")

if __name__ == '__main__':
    setup_database()
