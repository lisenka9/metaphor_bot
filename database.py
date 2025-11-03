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
            
            # Таблица подписок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    subscription_type TEXT NOT NULL,
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    payment_id TEXT
                )
            ''')
            
            # Таблица платежей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    amount INTEGER NOT NULL,
                    currency TEXT DEFAULT 'RUB',
                    subscription_type TEXT NOT NULL,
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    yoomoney_payment_id TEXT
                )
            ''')
            
            # Таблица для посланий (если ещё нет)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_messages (
                    message_id INTEGER PRIMARY KEY,
                    image_url TEXT NOT NULL,
                    message_text TEXT NOT NULL
                )
            ''')
            
            # Таблица для истории посланий пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_messages (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    message_id INTEGER REFERENCES daily_messages(message_id),
                    drawn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Обновляем таблицу пользователей
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS premium_until TIMESTAMP
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
        """Получает статистику пользователя включая подписку"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            logging.info(f"🔄 Getting stats for user {user_id}")
            
            # Получаем основные данные пользователя
            cursor.execute('''
                SELECT 
                    u.daily_cards_limit, 
                    u.is_premium, 
                    COUNT(uc.id) as total_cards,
                    u.registered_date,
                    u.premium_until
                FROM users u
                LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                WHERE u.user_id = %s
                GROUP BY u.user_id, u.daily_cards_limit, u.is_premium, u.registered_date, u.premium_until
            ''', (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                limit, is_premium, total_cards, reg_date, premium_until = result
                
                # Получаем информацию о подписке
                subscription_info = self.get_user_subscription(user_id)
                
                # Форматируем даты
                if reg_date:
                    if isinstance(reg_date, str):
                        reg_date_formatted = reg_date[:10]
                    else:
                        reg_date_formatted = reg_date.strftime("%d.%m.%Y")
                else:
                    reg_date_formatted = "Неизвестно"
                
                # Форматируем дату окончания подписки
                subscription_end = None
                if subscription_info:
                    subscription_type, end_date = subscription_info
                    if end_date:
                        if isinstance(end_date, str):
                            subscription_end = end_date[:10]
                        else:
                            subscription_end = end_date.strftime("%d.%m.%Y")
                elif premium_until:
                    if isinstance(premium_until, str):
                        subscription_end = premium_until[:10]
                    else:
                        subscription_end = premium_until.strftime("%d.%m.%Y")
                
                logging.info(f"📊 User stats - limit: {limit}, cards: {total_cards}, premium: {is_premium}")
                return (limit, is_premium, total_cards, reg_date_formatted, subscription_end)
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
                (88, "88", "https://ibb.co/wZZcDHNF", "Карта 88"),


                (89, "1", "https://ibb.co/9kNFQCZr", "Карта 1"),
                (90, "2", "https://ibb.co/qM5FTdLy", "Карта 2"),
                (91, "3", "https://ibb.co/VWTgcJFT", "Карта 3"),
                (92, "4", "https://ibb.co/Txmm7Hv4", "Карта 4"),
                (93, "5", "https://ibb.co/TMFJLYb6", "Карта 5"),
                (94, "6", "https://ibb.co/tpHpZ7L1", "Карта 6"),
                (95, "7", "https://ibb.co/mCb9mtqK", "Карта 7"),
                (96, "8", "https://ibb.co/gMdyCVSW", "Карта 8"),
                (97, "9", "https://ibb.co/F4gvstXF", "Карта 9"),
                (98, "10", "https://ibb.co/0pJ4Tcdq", "Карта 10"),
                (99, "11", "https://ibb.co/Pv93KM2T", "Карта 11"),
                (100, "12", "https://ibb.co/4RYP2rc0", "Карта 12"),
                (101, "13", "https://ibb.co/RkfHshYQ", "Карта 13"),
                (102, "14", "https://ibb.co/v6Scjr9s", "Карта 14"),
                (103, "15", "https://ibb.co/3mQmzZV0", "Карта 15"),
                (104, "16", "https://ibb.co/G423fK2p", "Карта 16"),
                (105, "17", "https://ibb.co/DD8P7Ppn", "Карта 17"),
                (106, "18", "https://ibb.co/ym2hhGDy", "Карта 18"),
                (107, "19", "https://ibb.co/VYJmyW7h", "Карта 19"),
                (108, "20", "https://ibb.co/fYTvNBbq", "Карта 20"),
                (109, "21", "https://ibb.co/9HrSkJyx", "Карта 21"),
                (110, "22", "https://ibb.co/TBTZRnWn", "Карта 22"),
                (111, "23", "https://ibb.co/1GvHFqfD", "Карта 23"),
                (112, "24", "https://ibb.co/DH4w7Bk6", "Карта 24"),
                (113, "25", "https://ibb.co/WNhPs7Nh", "Карта 25"),
                (114, "26", "https://ibb.co/bgWhYXsY", "Карта 26"),
                (115, "27", "https://ibb.co/0VQV5Vvs", "Карта 27"),
                (116, "28", "https://ibb.co/Ng9kMzzd", "Карта 28"),
                (117, "29", "https://ibb.co/chsgHSYx", "Карта 29"),
                (118, "30", "https://ibb.co/20Lx5YfJ", "Карта 30"),
                (119, "31", "https://ibb.co/LDPy6dVt", "Карта 31"),
                (120, "32", "https://ibb.co/k2VfwNrF", "Карта 32"),
                (121, "33", "https://ibb.co/Jwrc8PvP", "Карта 33"),
                (122, "34", "https://ibb.co/3mwSy8wM", "Карта 34"),
                (123, "35", "https://ibb.co/b5bfH5gk", "Карта 35"),
                (124, "36", "https://ibb.co/HLKrDtHJ", "Карта 36"),
                (125, "37", "https://ibb.co/zVgkWXDb", "Карта 37"),
                (126, "38", "https://ibb.co/G35YqJRN", "Карта 38"),
                (127, "39", "https://ibb.co/21KqZx8N", "Карта 39"),
                (128, "40", "https://ibb.co/spsNjd2v", "Карта 40"),
                (129, "41", "https://ibb.co/Q3MgxCXS", "Карта 41"),
                (130, "42", "https://ibb.co/d0mbdKGp", "Карта 42"),
                (131, "43", "https://ibb.co/SDxQCyC6", "Карта 43"),
                (132, "44", "https://ibb.co/6JmShfmf", "Карта 44"),
                (133, "45", "https://ibb.co/vvr8vZXc", "Карта 45"),
                (134, "46", "https://ibb.co/6JGGPJZx", "Карта 46"),
                (135, "47", "https://ibb.co/d4LJ0xmS", "Карта 47"),
                (136, "48", "https://ibb.co/zH0cCHjV", "Карта 48"),
                (137, "49", "https://ibb.co/7tpcS3Wv", "Карта 49"),
                (138, "50", "https://ibb.co/3YGgV04R", "Карта 50"),
                (139, "51", "https://ibb.co/v4CVn7qg", "Карта 51"),
                (140, "52", "https://ibb.co/JwvqYPDC", "Карта 52"),
                (141, "53", "https://ibb.co/RpP2Lmb3", "Карта 53"),
                (142, "54", "https://ibb.co/5hn4WXf6", "Карта 54"),
                (143, "55", "https://ibb.co/MDnBy1HS", "Карта 55"),
                (144, "56", "https://ibb.co/p6XzxgFv", "Карта 56"),
                (145, "57", "https://ibb.co/dwFFTwsy", "Карта 57"),
                (146, "58", "https://ibb.co/1t5jLjPh", "Карта 58"),
                (147, "59", "https://ibb.co/G4czHJZG", "Карта 59"),
                (148, "60", "https://ibb.co/yngBvQbz", "Карта 60"),
                (149, "61", "https://ibb.co/RppZ4X80", "Карта 61"),
                (150, "62", "https://ibb.co/C3jY5Sh7", "Карта 62"),
                (151, "63", "https://ibb.co/tgB0y95", "Карта 63"),
                (152, "64", "https://ibb.co/4wyCDg4F", "Карта 64"),
                (153, "65", "https://ibb.co/v6z3w64v", "Карта 65"),
                (154, "66", "https://ibb.co/bMgmWh65", "Карта 66"),
                (155, "67", "https://ibb.co/nMHg2Vrn", "Карта 67"),
                (156, "68", "https://ibb.co/CKw65fgY", "Карта 68"),
                (157, "69", "https://ibb.co/vC1TFZRP", "Карта 69"),
                (158, "70", "https://ibb.co/Q38PdBJF", "Карта 70"),
                (159, "71", "https://ibb.co/ksy9Fp7T", "Карта 71"),
                (160, "72", "https://ibb.co/39Zg7wzD", "Карта 72"),
                (161, "73", "https://ibb.co/7JVkWqwG", "Карта 73"),
                (162, "74", "https://ibb.co/Lz4cLFm7", "Карта 74"),
                (163, "75", "https://ibb.co/kVxZV6cs", "Карта 75"),
                (164, "76", "https://ibb.co/pvRGdsJq", "Карта 76"),
                (165, "77", "https://ibb.co/HfQNCShm", "Карта 77"),
                (166, "78", "https://ibb.co/fY14FYfr", "Карта 78"),
                (167, "79", "https://ibb.co/Y7YdQtSR", "Карта 79"),
                (168, "80", "https://ibb.co/4ZghKHhF", "Карта 80"),
                (169, "81", "https://ibb.co/v43v25F6", "Карта 81"),
                (170, "82", "https://ibb.co/sdn4mhZ0", "Карта 82"),
                (171, "83", "https://ibb.co/jkpXB0Yg", "Карта 83"),
                (172, "84", "https://ibb.co/dJBzhRhN", "Карта 84"),
                (173, "85", "https://ibb.co/Lh2h2B13", "Карта 85"),
                (174, "86", "https://ibb.co/9H9jV1tq", "Карта 86"),
                (175, "87", "https://ibb.co/DDvF5nWq", "Карта 87"),
                (176, "88", "https://ibb.co/4wNXYS52", "Карта 88")

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

    
    def _populate_daily_messages(self, cursor):
        """Добавляет послания дня в базу"""
        daily_messages = [
            (1, "https://ibb.co/wZd8BTHM", "Послание 1"),
            (2, "https://ibb.co/PGWbXCyP", "Послание 2")
            
        ]
        for message_id, image_url, message_text in daily_messages:
            cursor.execute('''
                INSERT INTO daily_messages (message_id, image_url, message_text)
                VALUES (%s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
            ''', (message_id, image_url, message_text))
        
        logging.info(f"✅ Added {len(daily_messages)} sample messages to database")

    def get_user_subscription(self, user_id: int):
        """Получает активную подписку пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT subscription_type, end_date 
                FROM subscriptions 
                WHERE user_id = %s AND is_active = TRUE AND end_date > CURRENT_TIMESTAMP
                ORDER BY end_date DESC 
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            
            # Также проверяем поле premium_until в users
            if not result:
                cursor.execute('''
                    SELECT premium_until 
                    FROM users 
                    WHERE user_id = %s AND premium_until > CURRENT_TIMESTAMP
                ''', (user_id,))
                
                premium_result = cursor.fetchone()
                if premium_result:
                    return ("premium", premium_result[0])
            
            return result
        except Exception as e:
            logging.error(f"Error getting user subscription: {e}")
            return None
        finally:
            conn.close()

    # Убедитесь, что есть метод create_subscription
def create_subscription(self, user_id: int, subscription_type: str, duration_days: int):
        """Создает подписку для пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            from datetime import datetime, timedelta
            
            end_date = datetime.now() + timedelta(days=duration_days)
            
            # Деактивируем старые подписки
            cursor.execute('''
                UPDATE subscriptions 
                SET is_active = FALSE 
                WHERE user_id = %s
            ''', (user_id,))
            
            # Создаем новую подписку
            cursor.execute('''
                INSERT INTO subscriptions (user_id, subscription_type, end_date)
                VALUES (%s, %s, %s)
            ''', (user_id, subscription_type, end_date))
            
            # Обновляем пользователя
            cursor.execute('''
                UPDATE users 
                SET is_premium = TRUE, premium_until = %s, daily_cards_limit = 5
                WHERE user_id = %s
            ''', (end_date, user_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logging.error(f"Error creating subscription: {e}")
            return False
        finally:
            conn.close()

    def can_take_daily_message(self, user_id: int) -> tuple: 
        """Проверяет, может ли пользователь взять послание дня"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Получаем информацию о пользователе и подписке
            cursor.execute('''
                SELECT u.is_premium, u.premium_until
                FROM users u 
                WHERE u.user_id = %s
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return False, "Пользователь не найден"
            
            is_premium, premium_until = result
            today = date.today()
            
            # Проверяем активную подписку
            has_active_subscription = False
            if premium_until:
                # Преобразуем premium_until в date для сравнения
                if hasattr(premium_until, 'date'):
                    premium_date = premium_until.date()
                elif isinstance(premium_until, str):
                    # Если это строка, парсим её
                    try:
                        premium_date = datetime.strptime(premium_until[:10], '%Y-%m-%d').date()
                    except:
                        premium_date = today
                else:
                    premium_date = premium_until
                
                has_active_subscription = is_premium and premium_date >= today
            
            logging.info(f"📊 User {user_id}: is_premium={is_premium}, premium_until={premium_until}, has_active_subscription={has_active_subscription}")
            
            if has_active_subscription:
                # Для премиум: проверяем лимит 5 раз в день
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM user_messages 
                    WHERE user_id = %s AND DATE(drawn_date) = %s
                ''', (user_id, today))
                
                today_messages_count = cursor.fetchone()[0]
                logging.info(f"📊 Premium user {user_id}: today_messages_count={today_messages_count}")
                
                if today_messages_count >= 5:
                    return False, "Вы уже получили максимальное количество посланий сегодня (5)"
                else:
                    return True, f"Можно взять послание ({today_messages_count + 1}/5 сегодня)"
            else:
                # Для бесплатных: проверяем 1 раз в неделю
                cursor.execute('''
                    SELECT MAX(drawn_date) 
                    FROM user_messages 
                    WHERE user_id = %s
                ''', (user_id,))
                
                last_message_result = cursor.fetchone()
                if not last_message_result or not last_message_result[0]:
                    logging.info(f"📊 Free user {user_id}: no previous messages, can take")
                    return True, "Можно взять послание"
                
                last_message_date = last_message_result[0]
                
                # Преобразуем дату в объект date
                if hasattr(last_message_date, 'date'):
                    last_message_date_only = last_message_date.date()
                elif isinstance(last_message_date, str):
                    # Если это строка, парсим её
                    try:
                        last_message_date_only = datetime.strptime(last_message_date[:10], '%Y-%m-%d').date()
                    except:
                        last_message_date_only = today
                else:
                    last_message_date_only = last_message_date
                
                days_since_last_message = (today - last_message_date_only).days
                logging.info(f"📊 Free user {user_id}: last_message={last_message_date_only}, days_since={days_since_last_message}")
                
                if days_since_last_message >= 7:
                    return True, "Можно взять послание"
                else:
                    days_left = 7 - days_since_last_message
                    return False, f"Следующее бесплатное послание будет доступно через {days_left} дней"
                    
        except Exception as e:
            logging.error(f"❌ Error checking daily message: {e}")
            return False, "Ошибка базы данных"
        finally:
            conn.close()

    def record_user_message(self, user_id: int, message_id: int) -> bool:
        """Записывает выданное послание пользователю"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Создаем таблицу для истории посланий, если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_messages (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    message_id INTEGER REFERENCES daily_messages(message_id),
                    drawn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Проверяем, есть ли послания в таблице daily_messages
            cursor.execute('SELECT COUNT(*) FROM daily_messages WHERE message_id = %s', (message_id,))
            message_exists = cursor.fetchone()[0] > 0
            
            if not message_exists:
                logging.error(f"❌ Message ID {message_id} not found in daily_messages")
                # Если послания нет, создаем его
                cursor.execute('''
                    INSERT INTO daily_messages (message_id, image_url, message_text)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING
                ''', (message_id, "https://example.com/default.jpg", "Тестовое послание"))
                logging.info(f"✅ Created default message with ID {message_id}")
            
            # Записываем в историю
            cursor.execute('''
                INSERT INTO user_messages (user_id, message_id) 
                VALUES (%s, %s)
            ''', (user_id, message_id))
            
            conn.commit()
            logging.info(f"✅ Successfully recorded message {message_id} for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"❌ Error recording user message: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    # Исправляем метод get_random_message
    def get_random_message(self):
        """Получает случайное послание дня"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Создаем таблицу для посланий, если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_messages (
                    message_id SERIAL PRIMARY KEY,
                    image_url TEXT NOT NULL,
                    message_text TEXT NOT NULL
                )
            ''')
            
            # Проверяем, есть ли послания, если нет - добавляем тестовые
            cursor.execute('SELECT COUNT(*) FROM daily_messages')
            count = cursor.fetchone()[0]
            
            if count == 0:
                logging.info("🔄 No messages found, populating sample messages")
                self._populate_daily_messages(cursor)
                conn.commit()
            
            cursor.execute('''
                SELECT message_id, image_url, message_text 
                FROM daily_messages 
                ORDER BY RANDOM() 
                LIMIT 1
            ''')
            result = cursor.fetchone()
            
            if result:
                logging.info(f"✅ Retrieved random message: ID {result[0]}")
                return result
            else:
                logging.error("❌ No messages available even after population")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error getting random message: {e}")
            return None
        finally:
            conn.close()

    def get_user_message_stats(self, user_id: int):
        """Получает статистику посланий пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Получаем информацию о подписке
            cursor.execute('''
                SELECT is_premium, premium_until 
                FROM users 
                WHERE user_id = %s
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return None
                
            is_premium, premium_until = user_data
            today = date.today()
            has_active_subscription = is_premium and premium_until and premium_until.date() >= today
            
            # Получаем статистику посланий
            if has_active_subscription:
                # Для премиум: сегодняшние послания
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM user_messages 
                    WHERE user_id = %s AND DATE(drawn_date) = %s
                ''', (user_id, today))
                today_count = cursor.fetchone()[0]
                limit = 5
                remaining = max(0, limit - today_count)
                return {
                    'has_subscription': True,
                    'today_count': today_count,
                    'limit': limit,
                    'remaining': remaining
                }
            else:
                # Для бесплатных: последнее послание
                cursor.execute('''
                    SELECT MAX(drawn_date) 
                    FROM user_messages 
                    WHERE user_id = %s
                ''', (user_id,))
                
                last_message_date = cursor.fetchone()[0]
                if not last_message_date:
                    return {
                        'has_subscription': False,
                        'last_message_date': None,
                        'can_take': True
                    }
                
                last_date = last_message_date.date() if hasattr(last_message_date, 'date') else last_message_date
                days_since_last = (today - last_date).days
                can_take = days_since_last >= 7
                days_until_next = max(0, 7 - days_since_last) if not can_take else 0
                
                return {
                    'has_subscription': False,
                    'last_message_date': last_date,
                    'can_take': can_take,
                    'days_until_next': days_until_next
                }
                
        except Exception as e:
            logging.error(f"❌ Error getting message stats: {e}")
            return None
        finally:
            conn.close()
# Глобальный экземпляр для использования в других файлах
db = DatabaseManager()
