import os
import logging
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor

class DatabaseManager:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
    
    def get_connection(self):
        """Создает соединение с PostgreSQL"""
        return psycopg2.connect(self.database_url, sslmode='require')
    
    def init_database(self):
        """Инициализация таблиц в базе данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
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
                    image_url TEXT NOT NULL,
                    description_text TEXT NOT NULL
                )
            ''')
            
            # Таблица истории выданных карт
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_cards (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    card_id INTEGER REFERENCES cards(card_id),
                    drawn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Индекс для быстрого поиска
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_date 
                ON user_cards(user_id, drawn_date)
            ''')
            
            # Проверяем, есть ли карты, если нет - добавляем тестовые
            cursor.execute('SELECT COUNT(*) FROM cards')
            if cursor.fetchone()[0] == 0:
                self._populate_sample_cards(cursor)
            
            conn.commit()
            logging.info("Database tables initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _populate_sample_cards(self, cursor):
        """Добавляет тестовые карты в базу"""
        sample_cards = [
            (1, "Карта 1", "https://via.placeholder.com/300x400/FF6B6B/white?text=Карта+1", "Первая карта"),
            (2, "Карта 2", "https://via.placeholder.com/300x400/4ECDC4/white?text=Карта+2", "Вторая карта"),
            (3, "Карта 3", "https://via.placeholder.com/300x400/45B7D1/white?text=Карта+3", "Третья карта"),
            (4, "Карта 4", "https://via.placeholder.com/300x400/96CEB4/white?text=Карта+4", "Четвертая карта"),
            (5, "Карта 5", "https://via.placeholder.com/300x400/F7DC6F/white?text=Карта+5", "Пятая карта")
        ]
        
        for card in sample_cards:
            cursor.execute('''
                INSERT INTO cards (card_id, card_name, image_url, description_text)
                VALUES (%s, %s, %s, %s)
            ''', card)
        
        logging.info("Added sample cards to database")
    
    def get_or_create_user(self, user_id: int, username: str, 
                          first_name: str, last_name: str) -> bool:
        """Создает или получает пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Обрабатываем возможные None значения
            username = username or ""
            first_name = first_name or "Пользователь"
            last_name = last_name or ""
            
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id, username, first_name, last_name))
            
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error creating user: {e}")
            return False
        finally:
            conn.close()

    # Остальные методы остаются аналогичными, но с синтаксисом PostgreSQL
    def can_take_daily_card(self, user_id: int) -> tuple:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT last_daily_card_date, daily_cards_limit 
                FROM users WHERE user_id = %s
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return False, "Пользователь не найден"
            
            last_date_str, limit = result
            today = date.today()
            
            if not last_date_str:
                return True, "Можно взять карту"
            
            last_date = last_date_str.date() if isinstance(last_date_str, datetime) else last_date_str
            if last_date < today:
                return True, "Можно взять карту"
            else:
                return False, "Вы уже брали карту сегодня"
                
        except Exception as e:
            logging.error(f"Error checking daily card: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    def get_random_card(self):
        """Получает случайную карту из колоды"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT card_id, card_name, image_url, description_text 
                FROM cards 
                ORDER BY RANDOM() 
                LIMIT 1
            ''')
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"Error getting random card: {e}")
            return None
        finally:
            conn.close()

    def record_user_card(self, user_id: int, card_id: int) -> bool:
        """Записывает выданную карту пользователю"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            today = date.today()
            
            # Обновляем дату последней карты
            cursor.execute('''
                UPDATE users 
                SET last_daily_card_date = %s 
                WHERE user_id = %s
            ''', (today, user_id))
            
            # Записываем в историю
            cursor.execute('''
                INSERT INTO user_cards (user_id, card_id) 
                VALUES (%s, %s)
            ''', (user_id, card_id))
            
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error recording user card: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_user_stats(self, user_id: int):
        """Получает статистику пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT u.daily_cards_limit, u.is_premium, 
                       COUNT(uc.id), u.registered_date
                FROM users u
                LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                WHERE u.user_id = %s
                GROUP BY u.user_id, u.daily_cards_limit, u.is_premium, u.registered_date
            ''', (user_id,))
            
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"Error getting user stats: {e}")
            return None
        finally:
            conn.close()

    def check_cards_exist(self) -> bool:
        """Проверяет, есть ли карты в базе данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM cards')
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            logging.error(f"Error checking cards: {e}")
            return False
        finally:
            conn.close()

# Глобальный экземпляр для использования в других файлах
db = DatabaseManager()
