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
            from config import DAILY_CARD_LIMIT_FREE
            
            # Таблица пользователей - ИСПРАВЛЕНО
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    daily_cards_limit INTEGER DEFAULT {DAILY_CARD_LIMIT_FREE},
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
            
            # Таблица истории выданных карт - ИСПРАВЛЕНО для PostgreSQL
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
            logging.info("✅ Database tables initialized successfully")
            
        except Exception as e:
            logging.error(f"❌ Error initializing database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _populate_sample_cards(self, cursor):
        """Добавляет тестовые карты в базу"""
        sample_cards = [
            (1, "1", "https://ibb.co/spkyBGgP", "Карта 1"),
            (2, "2", "https://ibb.co/qTVQtQC", "Карта 2"),
            (3, "3", "https://ibb.co/MyxPJXmG", "Карта 3"),
            (4, "4", "https://ibb.co/5XF99ZvF", "Карта 4"),
            (5, "5", "https://ibb.co/rf5dqnGD", "Карта 5"),
            (6, "6", "https://ibb.co/BHpJppcw", "Карта 6"),
            (7, "7", "https://ibb.co/QvHN4ZZ3", "Карта 7"),
            (8, "8", "https://ibb.co/Wp69gcDm", "Карта 8"),
            (9, "9", "https://ibb.co/MyqV7Yz4", "Карта 9"),
            (10, "10", "https://ibb.co/jkKCdQNL", "Карта 10"),
            (11, "11", "https://ibb.co/Kx0w554m", "Карта 11"),
            (12, "12", "https://ibb.co/gZqW9DN7", "Карта 12"),
            (13, "13", "https://ibb.co/MyzYPfWk", "Карта 13"),
            (14, "14", "https://ibb.co/9m3c6Pdq", "Карта 14"),
            (15, "15", "https://ibb.co/Pz4NH4hD", "Карта 15"),
            (16, "16", "https://ibb.co/RTdtXSLt", "Карта 16"),
            (17, "17", "https://ibb.co/JR6KKYHC", "Карта 17"),
            (18, "18", "https://ibb.co/gLQ1SmyK", "Карта 18"),
            (19, "19", "https://ibb.co/HpkRCY92", "Карта 19"),
            (20, "20", "https://ibb.co/F4jnjyrR", "Карта 20"),
            (21, "21", "https://ibb.co/wZD01tyS", "Карта 21"),
            (22, "22", "https://ibb.co/VW1pGxVK", "Карта 22"),
            (23, "23", "https://ibb.co/0yrSNNhk", "Карта 23"),
            (24, "24", "https://ibb.co/5WwK8b3r", "Карта 24"),
            (25, "25", "https://ibb.co/hRwL3569", "Карта 25"),
            (26, "26", "https://ibb.co/d0GCSBL9", "Карта 26"),
            (27, "27", "https://ibb.co/wNhmLGnM", "Карта 27"),
            (28, "28", "https://ibb.co/M59G71Db", "Карта 28"),
            (29, "29", "https://ibb.co/bMzLVznY", "Карта 29"),
            (30, "30", "https://ibb.co/SDByKKvq", "Карта 30"),
            (31, "31", "https://ibb.co/C5x9pJwM", "Карта 31"),
            (32, "32", "https://ibb.co/4gV4YP8N", "Карта 32"),
            (33, "33", "https://ibb.co/Cpfxt33s", "Карта 33"),
            (34, "34", "https://ibb.co/DHwmL1kH", "Карта 34"),
            (35, "35", "https://ibb.co/4RfNv5nr", "Карта 35"),
            (36, "36", "https://ibb.co/9k1Xg3PC", "Карта 36"),
            (37, "37", "https://ibb.co/xtd3X8mT", "Карта 37"),
            (38, "38", "https://ibb.co/vxHLDy3v", "Карта 38"),
            (39, "39", "https://ibb.co/rRdCvCWy", "Карта 39"),
            (40, "40", "https://ibb.co/jxxfRnV", "Карта 40"),
            (41, "41", "https://ibb.co/rCdVhks", "Карта 41"),
            (42, "42", "https://ibb.co/21xBVxKB", "Карта 42"),
            (43, "43", "https://ibb.co/Rp6DS3Lk", "Карта 43"),
            (44, "44", "https://ibb.co/jZf3n1Kq", "Карта 44"),
            (45, "45", "https://ibb.co/zVWNH3Zf", "Карта 45"),
            (46, "46", "https://ibb.co/1YLB7vJn", "Карта 46"),
            (47, "47", "https://ibb.co/cKBbc1KN", "Карта 47"),
            (48, "48", "https://ibb.co/j9M7YJPd", "Карта 48"),
            (49, "49", "https://ibb.co/9HPvGDCH", "Карта 49"),
            (50, "50", "https://ibb.co/vxBVcHKv", "Карта 50"),
            (51, "51", "https://ibb.co/PZW5yXXv", "Карта 51"),
            (52, "52", "https://ibb.co/27vGsM3n", "Карта 52"),
            (53, "53", "https://ibb.co/0pn1WCqD", "Карта 53"),
            (54, "54", "https://ibb.co/LDSvMBBf", "Карта 54"),
            (55, "55", "https://ibb.co/Q3G0fNSs", "Карта 55"),
            (56, "56", "https://ibb.co/VcRbR1Cd", "Карта 56"),
            (57, "57", "https://ibb.co/dwLDSnPx", "Карта 57"),
            (58, "58", "https://ibb.co/vCMDf7hy", "Карта 58"),
            (59, "59", "https://ibb.co/q3RdDSXp", "Карта 59"),
            (60, "60", "https://ibb.co/gLnn3CRY", "Карта 60"),
            (61, "61", "https://ibb.co/5gd74TVK", "Карта 61"),
            (62, "62", "https://ibb.co/j954wv5L", "Карта 62"),
            (63, "63", "https://ibb.co/zjfCk9k", "Карта 63"),
            (64, "64", "https://ibb.co/TDCb0tqm", "Карта 64"),
            (65, "65", "https://ibb.co/Wp4QPg5x", "Карта 65"),
            (66, "66", "https://ibb.co/0VXYTMY8", "Карта 66"),
            (67, "67", "https://ibb.co/Y7ghqDBg", "Карта 67"),
            (68, "68", "https://ibb.co/ccpDy9Jc", "Карта 68"),
            (69, "69", "https://ibb.co/nqnw4zNV", "Карта 69"),
            (70, "70", "https://ibb.co/6cNW4yLt", "Карта 70"),
            (71, "71", "https://ibb.co/mCMp8MCh", "Карта 71"),
            (72, "72", "https://ibb.co/mM5j8fc", "Карта 72"),
            (73, "73", "https://ibb.co/Rk5x321b", "Карта 73"),
            (74, "74", "https://ibb.co/vC7DdySQ", "Карта 74"),
            (75, "75", "https://ibb.co/prhmF9jw", "Карта 75"),
            (76, "76", "https://ibb.co/wZt3stT4", "Карта 76"),
            (77, "77", "https://ibb.co/K3Tp8mt", "Карта 77"),
            (78, "78", "https://ibb.co/WWVNzYvw", "Карта 78"),
            (79, "79", "https://ibb.co/0p1tFtGS", "Карта 79"),
            (80, "80", "https://ibb.co/xrh5vGg", "Карта 80"),
            (81, "81", "https://ibb.co/Y4YshT3J", "Карта 81"),
            (82, "82", "https://ibb.co/yn7dLJRN", "Карта 82"),
            (83, "83", "https://ibb.co/Hf5TF5J2", "Карта 83"),
            (84, "84", "https://ibb.co/Zz9jsQCV", "Карта 84"),
            (85, "85", "https://ibb.co/C5dR6cnN", "Карта 85"),
            (86, "86", "https://ibb.co/8n5d6bLC", "Карта 86"),
            (87, "87", "https://ibb.co/xqr6QynP", "Карта 87"),
            (88, "88", "https://ibb.co/wZZcDHNF", "Карта 88")
        ]
        
        for card in sample_cards:
            cursor.execute('''
                INSERT INTO cards (card_id, card_name, image_url, description_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (card_id) DO NOTHING
            ''', card)
        
        logging.info("✅ Added sample cards to database")
    
    def get_or_create_user(self, user_id: int, username: str, 
                          first_name: str, last_name: str) -> bool:
        """Создает или получает пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
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
            logging.error(f"❌ Error creating user: {e}")
            return False
        finally:
            conn.close()

    def can_take_daily_card(self, user_id: int) -> tuple:
        """Проверяет, может ли пользователь взять карту дня"""
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
            
            last_date, limit = result
            today = date.today()
            
            if not last_date:
                return True, "Можно взять карту"
            
            if last_date < today:
                return True, "Можно взять карту"
            else:
                return False, "Вы уже брали карту сегодня"
                
        except Exception as e:
            logging.error(f"❌ Error checking daily card: {e}")
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
            logging.error(f"❌ Error getting random card: {e}")
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
            logging.error(f"❌ Error recording user card: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_user_stats(self, user_id: int):
        """Получает статистику пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            logging.info(f"🔄 Getting stats for user {user_id}")
            
            # Получаем все данные за один запрос
            cursor.execute('''
                SELECT 
                    u.daily_cards_limit, 
                    u.is_premium, 
                    COUNT(uc.id) as total_cards,
                    u.registered_date
                FROM users u
                LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                WHERE u.user_id = %s
                GROUP BY u.user_id, u.daily_cards_limit, u.is_premium, u.registered_date
            ''', (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                limit, is_premium, total_cards, reg_date = result
                
                # Форматируем дату
                if reg_date:
                    if isinstance(reg_date, str):
                        reg_date_formatted = reg_date[:10]
                    else:
                        reg_date_formatted = reg_date.strftime("%d-%m-%Y")
                else:
                    reg_date_formatted = "Неизвестно"
                
                logging.info(f"📊 User stats - limit: {limit}, cards: {total_cards}, reg_date: {reg_date_formatted}")
                return (limit, is_premium, total_cards, reg_date_formatted)
            else:
                logging.warning(f"User data not found for {user_id}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error getting user stats: {e}")
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
            logging.error(f"❌ Error checking cards: {e}")
            return False
        finally:
            conn.close()


    def update_existing_users_limits(self):
        """Обновляет лимиты существующих пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            from config import DAILY_CARD_LIMIT_FREE
            
            cursor.execute('''
                UPDATE users 
                SET daily_cards_limit = %s 
                WHERE is_premium = FALSE
            ''', (DAILY_CARD_LIMIT_FREE,))
            
            conn.commit()
            logging.info(f"✅ Обновлены лимиты пользователей на {DAILY_CARD_LIMIT_FREE}")
            
        except Exception as e:
            logging.error(f"❌ Error updating limits: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_user_card_history(self, user_id: int, limit: int = 10):
        """Получает историю карт пользователя с ограничением"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT c.card_id, c.card_name, c.image_url, c.description_text, uc.drawn_date
                FROM user_cards uc
                JOIN cards c ON uc.card_id = c.card_id
                WHERE uc.user_id = %s
                ORDER BY uc.drawn_date DESC
                LIMIT %s
            ''', (user_id, limit))
            
            history = cursor.fetchall()
            return history
            
        except Exception as e:
            logging.error(f"❌ Error getting card history: {e}")
            return None
        finally:
            conn.close()


    def add_missing_cards(self):
        """Добавляет отсутствующие карты в базу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            sample_cards = [
                (1, "1", "https://ibb.co/spkyBGgP", "Карта 1"),
                (2, "2", "https://ibb.co/qTVQtQC", "Карта 2"),
                (3, "3", "https://ibb.co/MyxPJXmG", "Карта 3"),
                (4, "4", "https://ibb.co/5XF99ZvF", "Карта 4"),
                (5, "5", "https://ibb.co/rf5dqnGD", "Карта 5"),
                (6, "6", "https://ibb.co/BHpJppcw", "Карта 6"),
                (7, "7", "https://ibb.co/QvHN4ZZ3", "Карта 7"),
                (8, "8", "https://ibb.co/Wp69gcDm", "Карта 8"),
                (9, "9", "https://ibb.co/MyqV7Yz4", "Карта 9"),
                (10, "10", "https://ibb.co/jkKCdQNL", "Карта 10"),
                (11, "11", "https://ibb.co/Kx0w554m", "Карта 11"),
                (12, "12", "https://ibb.co/gZqW9DN7", "Карта 12"),
                (13, "13", "https://ibb.co/MyzYPfWk", "Карта 13"),
                (14, "14", "https://ibb.co/9m3c6Pdq", "Карта 14"),
                (15, "15", "https://ibb.co/Pz4NH4hD", "Карта 15"),
                (16, "16", "https://ibb.co/RTdtXSLt", "Карта 16"),
                (17, "17", "https://ibb.co/JR6KKYHC", "Карта 17"),
                (18, "18", "https://ibb.co/gLQ1SmyK", "Карта 18"),
                (19, "19", "https://ibb.co/HpkRCY92", "Карта 19"),
                (20, "20", "https://ibb.co/F4jnjyrR", "Карта 20"),
                (21, "21", "https://ibb.co/wZD01tyS", "Карта 21"),
                (22, "22", "https://ibb.co/VW1pGxVK", "Карта 22"),
                (23, "23", "https://ibb.co/0yrSNNhk", "Карта 23"),
                (24, "24", "https://ibb.co/5WwK8b3r", "Карта 24"),
                (25, "25", "https://ibb.co/hRwL3569", "Карта 25"),
                (26, "26", "https://ibb.co/d0GCSBL9", "Карта 26"),
                (27, "27", "https://ibb.co/wNhmLGnM", "Карта 27"),
                (28, "28", "https://ibb.co/M59G71Db", "Карта 28"),
                (29, "29", "https://ibb.co/bMzLVznY", "Карта 29"),
                (30, "30", "https://ibb.co/SDByKKvq", "Карта 30"),
                (31, "31", "https://ibb.co/C5x9pJwM", "Карта 31"),
                (32, "32", "https://ibb.co/4gV4YP8N", "Карта 32"),
                (33, "33", "https://ibb.co/Cpfxt33s", "Карта 33"),
                (34, "34", "https://ibb.co/DHwmL1kH", "Карта 34"),
                (35, "35", "https://ibb.co/4RfNv5nr", "Карта 35"),
                (36, "36", "https://ibb.co/9k1Xg3PC", "Карта 36"),
                (37, "37", "https://ibb.co/xtd3X8mT", "Карта 37"),
                (38, "38", "https://ibb.co/vxHLDy3v", "Карта 38"),
                (39, "39", "https://ibb.co/rRdCvCWy", "Карта 39"),
                (40, "40", "https://ibb.co/jxxfRnV", "Карта 40"),
                (41, "41", "https://ibb.co/rCdVhks", "Карта 41"),
                (42, "42", "https://ibb.co/21xBVxKB", "Карта 42"),
                (43, "43", "https://ibb.co/Rp6DS3Lk", "Карта 43"),
                (44, "44", "https://ibb.co/jZf3n1Kq", "Карта 44"),
                (45, "45", "https://ibb.co/zVWNH3Zf", "Карта 45"),
                (46, "46", "https://ibb.co/1YLB7vJn", "Карта 46"),
                (47, "47", "https://ibb.co/cKBbc1KN", "Карта 47"),
                (48, "48", "https://ibb.co/j9M7YJPd", "Карта 48"),
                (49, "49", "https://ibb.co/9HPvGDCH", "Карта 49"),
                (50, "50", "https://ibb.co/vxBVcHKv", "Карта 50"),
                (51, "51", "https://ibb.co/PZW5yXXv", "Карта 51"),
                (52, "52", "https://ibb.co/27vGsM3n", "Карта 52"),
                (53, "53", "https://ibb.co/0pn1WCqD", "Карта 53"),
                (54, "54", "https://ibb.co/LDSvMBBf", "Карта 54"),
                (55, "55", "https://ibb.co/Q3G0fNSs", "Карта 55"),
                (56, "56", "https://ibb.co/VcRbR1Cd", "Карта 56"),
                (57, "57", "https://ibb.co/dwLDSnPx", "Карта 57"),
                (58, "58", "https://ibb.co/vCMDf7hy", "Карта 58"),
                (59, "59", "https://ibb.co/q3RdDSXp", "Карта 59"),
                (60, "60", "https://ibb.co/gLnn3CRY", "Карта 60"),
                (61, "61", "https://ibb.co/5gd74TVK", "Карта 61"),
                (62, "62", "https://ibb.co/j954wv5L", "Карта 62"),
                (63, "63", "https://ibb.co/zjfCk9k", "Карта 63"),
                (64, "64", "https://ibb.co/TDCb0tqm", "Карта 64"),
                (65, "65", "https://ibb.co/Wp4QPg5x", "Карта 65"),
                (66, "66", "https://ibb.co/0VXYTMY8", "Карта 66"),
                (67, "67", "https://ibb.co/Y7ghqDBg", "Карта 67"),
                (68, "68", "https://ibb.co/ccpDy9Jc", "Карта 68"),
                (69, "69", "https://ibb.co/nqnw4zNV", "Карта 69"),
                (70, "70", "https://ibb.co/6cNW4yLt", "Карта 70"),
                (71, "71", "https://ibb.co/mCMp8MCh", "Карта 71"),
                (72, "72", "https://ibb.co/mM5j8fc", "Карта 72"),
                (73, "73", "https://ibb.co/Rk5x321b", "Карта 73"),
                (74, "74", "https://ibb.co/vC7DdySQ", "Карта 74"),
                (75, "75", "https://ibb.co/prhmF9jw", "Карта 75"),
                (76, "76", "https://ibb.co/wZt3stT4", "Карта 76"),
                (77, "77", "https://ibb.co/K3Tp8mt", "Карта 77"),
                (78, "78", "https://ibb.co/WWVNzYvw", "Карта 78"),
                (79, "79", "https://ibb.co/0p1tFtGS", "Карта 79"),
                (80, "80", "https://ibb.co/xrh5vGg", "Карта 80"),
                (81, "81", "https://ibb.co/Y4YshT3J", "Карта 81"),
                (82, "82", "https://ibb.co/yn7dLJRN", "Карта 82"),
                (83, "83", "https://ibb.co/Hf5TF5J2", "Карта 83"),
                (84, "84", "https://ibb.co/Zz9jsQCV", "Карта 84"),
                (85, "85", "https://ibb.co/C5dR6cnN", "Карта 85"),
                (86, "86", "https://ibb.co/8n5d6bLC", "Карта 86"),
                (87, "87", "https://ibb.co/xqr6QynP", "Карта 87"),
                (88, "88", "https://ibb.co/wZZcDHNF", "Карта 88")
            ]
            
            added_count = 0
            for card in sample_cards:
                cursor.execute('''
                    INSERT INTO cards (card_id, card_name, image_url, description_text)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (card_id) DO NOTHING
                    RETURNING card_id
                ''', card)
                if cursor.fetchone():
                    added_count += 1
            
            conn.commit()
            logging.info(f"✅ Добавлено {added_count} новых карт")
            return added_count
            
        except Exception as e:
            logging.error(f"❌ Error adding cards: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def get_random_message(self):
        """Получает случайное послание дня"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Таблица для посланий (создаем если нет)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_messages (
                    message_id INTEGER PRIMARY KEY,
                    image_url TEXT NOT NULL,
                    message_text TEXT NOT NULL
                )
            ''')
            
            # Проверяем, есть ли послания, если нет - добавляем
            cursor.execute('SELECT COUNT(*) FROM daily_messages')
            if cursor.fetchone()[0] == 0:
                self._populate_daily_messages(cursor)
            
            cursor.execute('''
                SELECT message_id, image_url, message_text 
                FROM daily_messages 
                ORDER BY RANDOM() 
                LIMIT 1
            ''')
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"❌ Error getting random message: {e}")
            return None
        finally:
            conn.close()

    def _populate_daily_messages(self, cursor):
        """Добавляет послания дня в базу"""
        daily_messages = [
            (1, "https://ibb.co/wZd8BTHM", "Послание 1"),
            (2, "https://ibb.co/PGWbXCyP", "Послание 2"),
            
        ]
        
        for message in daily_messages:
            cursor.execute('''
                INSERT INTO daily_messages (message_id, image_url, message_text)
                VALUES (%s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
            ''', message)
        
        logging.info("✅ Added daily messages to database")

# Глобальный экземпляр для использования в других файлах
db = DatabaseManager()
