import os
import logging
from datetime import datetime, date, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

class DatabaseManager:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
    
    def get_connection(self):
        """Создает соединение с PostgreSQL с повторными попытками"""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import time
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Добавляем параметры для лучшей устойчивости SSL
                conn = psycopg2.connect(
                    self.database_url,
                    sslmode='require',
                    connect_timeout=10,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5
                )
                return conn
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt < max_retries - 1:
                    logging.warning(f"⚠️ Database connection attempt {attempt + 1} failed: {e}")
                    logging.info(f"🔄 Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Экспоненциальная задержка
                else:
                    logging.error(f"❌ Failed to connect to database after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logging.error(f"❌ Unexpected database connection error: {e}")
                raise
    
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
                    email TEXT,
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
                    amount DECIMAL NOT NULL,
                    currency TEXT DEFAULT 'RUB',
                    subscription_type TEXT,
                    product_type TEXT DEFAULT 'subscription',
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    payment_method TEXT DEFAULT 'yookassa',
                    yoomoney_payment_id TEXT,
                    payment_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица для логов действий пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_action_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    action TEXT NOT NULL,
                    action_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Добавляем недостающие колонки если таблица уже существует
            cursor.execute('''
                DO $$ 
                BEGIN
                    -- Добавляем payment_method если нет
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                WHERE table_name='payments' AND column_name='payment_method') THEN
                        ALTER TABLE payments ADD COLUMN payment_method TEXT DEFAULT 'yookassa';
                    END IF;
                    
                    -- Добавляем product_type если нет
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                WHERE table_name='payments' AND column_name='product_type') THEN
                        ALTER TABLE payments ADD COLUMN product_type TEXT DEFAULT 'subscription';
                    END IF;
                    
                    -- Добавляем created_at если нет
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                WHERE table_name='payments' AND column_name='created_at') THEN
                        ALTER TABLE payments ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                    END IF;
                END $$;
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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deck_purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_id TEXT,
                    status TEXT DEFAULT 'completed',
                    amount DECIMAL DEFAULT 999.00
                )
            ''')

            # Таблица для истории просмотров медитаций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_meditations (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    watched_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица для видео ссылок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_links (
                    link_hash TEXT PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    video_url TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    has_subscription BOOLEAN DEFAULT FALSE,
                    access_started_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
            # Обновляем структуру существующей таблицы
            self.update_video_links_table()

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

    def has_purchased_deck(self, user_id: int) -> bool:
        """Проверяет, покупал ли пользователь колоду"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id FROM deck_purchases 
                WHERE user_id = %s AND status = 'completed'
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone() is not None
            
            if result:
                logging.info(f"✅ User {user_id} has already purchased deck")
            else:
                logging.info(f"ℹ️ User {user_id} has not purchased deck yet")
                
            return result
                
        except Exception as e:
            logging.error(f"❌ Error checking deck purchase: {e}")
            return False
        finally:
            conn.close()

    def record_deck_purchase(self, user_id: int, payment_id: str = None) -> bool:
        """Записывает факт покупки колоды"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO deck_purchases (user_id, payment_id)
                VALUES (%s, %s)
            ''', (user_id, payment_id))
            
            conn.commit()
            logging.info(f"✅ Deck purchase recorded for user {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error recording deck purchase: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def add_payment_id_column(self):
        """Добавляет колонку payment_id в таблицу payments"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                ALTER TABLE payments 
                ADD COLUMN IF NOT EXISTS payment_id TEXT
            ''')
            conn.commit()
            logging.info("✅ Added payment_id column to payments table")
        except Exception as e:
            logging.error(f"❌ Error adding payment_id column: {e}")
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
            self.check_user_subscription_expiry(user_id)
            # ✅ ПОЛУЧАЕМ ВСЮ НЕОБХОДИМУЮ ИНФОРМАЦИЮ О ПОЛЬЗОВАТЕЛЕ
            cursor.execute('''
                SELECT last_daily_card_date, daily_cards_limit, is_premium, premium_until 
                FROM users WHERE user_id = %s
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return False, "Пользователь не найден"
            
            last_date, limit, is_premium, premium_until = result
            today = date.today()
            
            # ✅ ПРОВЕРЯЕМ АКТИВНУЮ ПОДПИСКУ
            has_active_subscription = False
            if premium_until:
                if hasattr(premium_until, 'date'):
                    premium_date = premium_until.date()
                elif isinstance(premium_until, str):
                    try:
                        premium_date = datetime.strptime(premium_until[:10], '%Y-%m-%d').date()
                    except:
                        premium_date = today
                else:
                    premium_date = premium_until
                
                has_active_subscription = is_premium and premium_date >= today
            
            logging.info(f"📊 User {user_id}: limit={limit}, is_premium={is_premium}, premium_until={premium_until}, has_active={has_active_subscription}")
            
            if not last_date:
                return True, "Можно взять карту"
            
            if last_date < today:
                return True, "Можно взять карту"
            else:
                # ✅ ДЛЯ ПРЕМИУМ ПОЛЬЗОВАТЕЛЕЙ ПРОВЕРЯЕМ КОЛИЧЕСТВО КАРТ СЕГОДНЯ
                if has_active_subscription and limit > 1:
                    cursor.execute('''
                        SELECT COUNT(*) 
                        FROM user_cards 
                        WHERE user_id = %s AND DATE(drawn_date) = %s
                    ''', (user_id, today))
                    
                    today_cards_count = cursor.fetchone()[0]
                    logging.info(f"📊 Premium user {user_id}: today_cards_count={today_cards_count}, limit={limit}")
                    
                    if today_cards_count < limit:
                        return True, f"Можно взять карту ({today_cards_count + 1}/{limit} сегодня)"
                    else:
                        return False, f"Вы уже получили максимальное количество карт сегодня ({limit})"
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
        """Получает статистику пользователя с проверкой истекшей подписки"""
        try:
            logging.info(f"🔄 Getting stats for user {user_id}")
            
            # СНАЧАЛА проверяем и обновляем истекшую подписку
            self.check_user_subscription_expiry(user_id)
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
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
            conn.close()
            
            if result:
                limit, is_premium, total_cards, reg_date, premium_until = result
                
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
                if premium_until:
                    if isinstance(premium_until, str):
                        subscription_end = premium_until[:10]
                    else:
                        subscription_end = premium_until.strftime("%d.%m.%Y")
                
                logging.info(f"📊 User stats - limit: {limit}, premium: {is_premium}, until: {premium_until}")
                return (limit, is_premium, total_cards, reg_date_formatted, subscription_end)
            else:
                logging.warning(f"User data not found for {user_id}")
                return None
                    
        except Exception as e:
            logging.error(f"❌ Error getting user stats: {e}")
            return None

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

    def get_cards_data(self):
        """Возвращает массив с данными всех карт для переиспользования"""
        return [
                    (1, "1", "https://ibb.co/spkyBGgP", "🔱 **ПОСЛАНИЕ ДНЯ: ПРЕОДОЛЕЙ ПРЕГРАДУ**\n\nДаже сквозь самые крепкие стены можно увидеть бескрайний горизонт. Подобно Одиссею, который долгие годы, глядя на море из заточения, сохранял верность своему пути, вы призваны сосредоточиться на цели, а не на преграде.\n\n**Ваша истинная сила** — в дальновидности. Не позволяйте камню преграды заслонить сияние солнца на воде. Внутренняя свобода начинается с выбора того, что вы видите.\n\n**Жажда пути сильнее любых цепей.**\n\n**Смысл дня:** Вы сами выбираете, что важнее: зона комфорта или свобода."),
                    (2, "2", "https://ibb.co/qTVQtQC", "🔱 **ПОСЛАНИЕ ДНЯ: ВОЗЬМИ ПАУЗУ**\n\nДаже когда море взволновано, мудрая птица знает, что наступит время охоты.\n\n**Ваш день призывает:**не поддавайтесь внешнему хаосу. Стойте на своих камнях, как на скале, которую не может сдвинуть ни один гнев Посейдона. Ваша задача сегодня — не действовать, а быть. Сосредоточьтесь на своей внутренней неподвижности. Только в этой паузе вы сможете увидеть правильный момент для следующего шага.\n\n**Неподвижность — это ваша временная, но абсолютная сила.**\n\n**Смысл дня:** Ваша стойкость сильнее любой волны."),
                    (3, "3", "https://ibb.co/MyxPJXmG", "🔱 **ПОСЛАНИЕ ДНЯ: СОБЛЮДАЙ ПОРЯДОК**\n\nСлишком резкий порыв ветра мог сбить с курса даже корабль Одиссея. Ваш день указывает на потенциал хаоса, который может нарушить ваш покой.\n\n**Ваш день призывает:** оцените границы и последствия. Не всякое резкое движение — это свобода. Иногда это неуправляемая энергия, которая может разрушить то, что вы построили. Вернитесь под защиту своей внутренней крыши.\n\n**Прежде чем взлететь, убедись, что твой полет управляем.**\n\n**Смысл дня:** Порядок и защита ценнее разрушающей силы."),
                    (4, "4", "https://ibb.co/5XF99ZvF", "🔱 **ПОСЛАНИЕ ДНЯ: ВЫЙДИ ИЗ ОЦЕПЕНЕНИЯ**\n\nМедуза Горгона была наказана за свою красоту, и всякий, кто смотрел на неё, обращался в камень.\n\n**Ваш день призывает:** не позволяйте прошлой боли превратить вас в неподвижную статую. Осознайте, какое внутреннее чувство или страх сегодня парализует вашу волю. Вы не обязаны смотреть на проблему прямо — иногда нужен зеркальный щит, чтобы увидеть и обезвредить её. Не дайте боли определить вашу форму.\n\n**Самые страшные раны — те, что мы превращаем в собственное заточение.**\n\n**Смысл дня:** Выйдите из оцепенения и начните движение."),
                    (5, "5", "https://ibb.co/rf5dqnGD", "🔱 **ПОСЛАНИЕ ДНЯ: ОТПУСТИ ПРОШЛОЕ**\n\nВ древних мифах всякий закат — это переправа. Подобно тому, как души переходят реку забвения, вы призваны отпустить то, что уже уходит. Ваш день указывает на сопротивление завершению.\n\n**Ваш день призывает:** прекратите цепляться за уходящий свет. Не бойтесь временной темноты, которая наступает перед новым восходом. Примите эмоциональную волну, но не дайте ей сбить вас с курса. Переход требует мужества и тишины.\n\n**Самая тёмная ночь — перед рассветом.**\n\n**Смысл дня:** Отпустите прошлое, чтобы увидеть новое."),
                    (6, "6", "https://ibb.co/BHpJppcw", "🔱 **ПОСЛАНИЕ ДНЯ: УКРЕПИ ГРАНИЦЫ**\n\nВ легендах, когда Посейдон разгневан, бесполезно спорить с волной. Ваш день указывает на кризис или внешнее давление, которое невозможно преодолеть прямым сопротивлением.\n\n**Ваш день призывает:** прекратите борьбу с тем, что выше ваших сил. Волнорез служит не для нападения, а для защиты. Найдите свою внутреннюю гавань, примите мощь стихии и направьте энергию на укрепление своих границ.\n\n**Самая крепкая защита — та, что умеет встретить удар и остаться на месте.**\n\n**Смысл дня:** Вы не обязаны побеждать каждую битву."),
                    (7, "7", "https://ibb.co/QvHN4ZZ3", "🔱 **ПОСЛАНИЕ ДНЯ: ВЫЙДИ ИЗ ЗОНЫ КОМФОРТА**\n\nДаже самое красивое отражение света на воде — это не сам свет. Ваш день указывает на искушение остаться на берегу, наслаждаясь поверхностным покоем, вместо того чтобы отправиться в путь.\n\n**Ваш день призывает:** остерегайтесь золотого плена комфорта. Не позволяйте иллюзии гармонии остановить ваше развитие. Сделайте шаг в воду, даже если она кажется холодной. Истинная красота и приключение ждут там, где кончается песок.\n\n**Комфорт не развивает. Путь требует движения.**\n\n**Смысл дня:** Ваш настоящий путь лежит за границей берега."),
                    (8, "8", "https://ibb.co/Wp69gcDm", "🔱 **ПОСЛАНИЕ ДНЯ: ПРОЯВИ УЯЗВИМОСТЬ**\n\nСогласно древним морским поверьям, только то, что осмеливается выйти на берег, может стать видимым миру.\n\n**Ваш день призывает:** покажите свое истинное лицо. Не бойтесь уязвимости, как медуза не боится прозрачности. Всякая внутренняя ценность должна быть проявлена, чтобы обрести смысл.\n\n**Сквозь муть, выбери Ясность.**\n\n**Смысл дня:** Ваш дар должен быть проявлен."),
                    (9, "9", "https://ibb.co/MyqV7Yz4", "🔱 **ПОСЛАНИЕ ДНЯ: ВЫРВИСЬ ИЗ ВНУТРЕННЕГО ПЛЕНА**\n\nСамые крепкие стены — те, что мы возводим вокруг себя сами. Ваш день указывает на тяжесть ограничений, мешающих увидеть истинную свободу.\n\n**Ваш день призывает:** осознайте, что самое трудное препятствие — ваша привычка к замкнутому пространству. Не позволяйте внешним преградам сузить ваше внутреннее зрение. Свобода начинается с мысли о шаге за пределы рамок и ограничений.\n\n**Стена перестает быть преградой, когда ты решаешь её обойти.**\n\n**Смысл дня:** Ваш главный ограничитель находится внутри вас."),
                    (10, "10", "https://ibb.co/jkKCdQNL", "🔱 **ПОСЛАНИЕ ДНЯ: НЕ ОТВЛЕКАЙСЯ НА МЕЛОЧИ**\n\nОпасно не само море, а хаос у берега. Мелкая, бурлящая пена грозит поглотить ваше внимание, не давая увидеть истинный, глубокий горизонт.\n\n**Ваш день призывает:** остановите попытки бороться со всей этой пеной одновременно. Всякое внимание, направленное на хаос, умножает его. Найдите твердую скалу среди этого бурления и сделайте паузу, чтобы отделить важное от второстепенного.\n\n**Нельзя победить хаос, борясь с каждой его каплей.**\n\n**Смысл дня:** Выберите главное, отпустив мелкие заботы."),
                    (11, "11", "https://ibb.co/Kx0w554m", "🔱 ПОСЛАНИЕ ДНЯ: НЕ БОЙСЯ ПЕРЕМЕН\n\nНеподвижное облако символизирует застой. Подобно тому, как Нарцисс был пленен отражением, вы можете быть прикованы к одной, неизменной картине своего мира.\n\nВаш день призывает: не позволяйте привычному покою затормозить ваше развитие. Если вы видите одну и ту же форму, вы не живете, а замерли в отражении. Ваш берег слишком пологий, и вы рискуете остаться на месте, наблюдая, как время проходит мимо, не создавая ничего нового.\n\nСтоять на месте — это выбирать небытие.\n\nСмысл дня:Сделайте шаг в глубину."),
                    (12, "12", "https://ibb.co/gZqW9DN7", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СТОЙ НА МЕСТЕ\n\nИдеальный штиль таит в себе опасность: лодка, замершая на чистой воде, не движется к цели. Подобно герою, остановившемуся, чтобы полюбоваться своим отражением, вы рискуете застрять.\n\nВаш день призывает:остерегайтесь парализующей силы совершенства. Слишком долгая пауза в идеальных условиях может стать зоной комфорта, которая не развивает. Не позволяйте красоте момента или страху нарушить гармонию остановить ваше движение. Используйте спокойствие, чтобы начать плыть, а не стоять.\n\nИдеальная гладь воды — ловушка для путешественника.\n\nСмысл дня: Стремление к совершенству мешает началу движения."),
                    (13, "13", "https://ibb.co/MyzYPfWk", "🔱 ПОСЛАНИЕ ДНЯ: ОСВОБОДИСЬ ОТ БРЕМЕНИ\n\nСлишком массивный утес отбрасывает глубокую тень, которая не дает солнечным лучам коснуться воды. Эта тень — символ ваших жестких, старых убеждений, которые мешают новому пробиться в вашу жизнь.\n\nВаш день призывает: осознайте, какие убеждения сегодня заслоняют свет. Всякая чрезмерная твердость ведет к неподвижности и изоляции. Ваши границы стали тяжелым бременем, а не защитой. Оставьте часть своей гордыни, чтобы солнечный свет и перемены могли коснуться вашей внутренней воды.\n\nТяжелый камень не может подняться выше.\n\nСмысл дня: Чрезмерная твердость и гордыня создают внутренний плен."),
                    (14, "14", "https://ibb.co/9m3c6Pdq", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЖДИ ИДЕАЛЬНЫХ УСЛОВИЙ\n\nВзгляд, прикованный к мрачному небу, не дает увидеть горизонта и заставляет забыть о солнце. Сегодня вы рискуете застрять в ожидании самого худшего, не видя, что действие возможно и в темноте.\n\nВаш день призывает: не ждите идеальных условий для начала. Осознайте, что ваше внимание целиком поглощено негативным прогнозом (темными тучами) и борьбой (волнами). Это блокирует способность действовать стратегически. Смените фокус: ваш волнорез служит для того, чтобы вы могли оставаться в безопасности и действовать, даже когда вокруг темно.\n\nТот, кто ждет идеального солнца, теряет время в шторм.\n\nСмысл дня: Не ждите чуда -действуйте."),
                    (15, "15", "https://ibb.co/Pz4NH4hD", "🔱 ПОСЛАНИЕ ДНЯ: ДЕЙСТВУЙ ОДИН\n\nВсякое длительное ожидание, даже идеального момента, рискует превратиться в паралич действия. Цапля, слишком долго стоящая на одном месте, может упустить цель.\n\nВаш день призывает: остерегайтесь ловушки перфекционизма и промедления. Не позволяйте страху совершить ошибку или желанию абсолютной гарантии успеха удержать вас. Длительное одиночество и ожидание могут сузить ваше зрение. Если цель не приближается, значит, вам пора сделать решительный, пусть и несовершенный, шаг.\n\nНельзя поймать рыбу, стоя лишь в ожидании.\n\nСмысл дня:Ожидание отдаляет Вас от цели."),
                    (16, "16", "https://ibb.co/RTdtXSLt", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПОДДАЙСЯ ПАНИКЕ\n\nСамая большая опасность в мутной воде — не сама волна, а невозможность видеть дно или горизонт. Это ощущение тотальной потери контроля, которое может парализовать волю.\n\nВаш день призывает: осознайте, что паника умножает внешний хаос. Не позволяйте себе утонуть в эмоциональной мути. Чем больше вы пытаетесь контролировать этот хаос, тем сильнее он вас затягивает. Сфокусируйтесь на единственной точке ясности, которую вы видите (например, небольшой просвет в тучах), и двигайтесь к ней, игнорируя ближайший ужас.\n\nМутная вода скрывает дно, но подводные камни остаются.\n\nСмысл дня: Ваш главный ограничитель — страх потери контроля."),
                    (17, "17", "https://ibb.co/JR6KKYHC", "🔱 ПОСЛАНИЕ ДНЯ: ВЫЙДИ ИЗ ТИШИНЫ\n\nСлишком долгое созерцание может превратиться в ловушку, подобную той, что погубила Нарцисса. Вы рискуете приковать себя к статичной позиции, глядя на отражение, а не на реальный, меняющийся мир.\n\nВаш день призывает:не позволяйте покою превратиться в паралич воли. Осознайте, что уединение, если оно чрезмерно, превращает берег в тюрьму. Вы можете потерять способность действовать из-за страха нарушить идеальную картину. Встаньте со стула: пора принять участие в той жизни, которую вы созерцаете.\n\nСлишком долгий покой заставляет забыть о движении.\n\nСмысл дня: Время тишины закончилось –начинай движение."),
                    (18, "18", "https://ibb.co/gLQ1SmyK", "🔱 ПОСЛАНИЕ ДНЯ: ОСТЕРЕГАЙСЯ СОВЕРШЕНСТВА\n\nЭта высокая башня уязвима, если вы забываете о принципе «вода камень точит». Вы слишком жестко держитесь за созданный порядок.\n\nВаш день призывает: остерегайтесь жесткости и иллюзии совершенства. Гордость за созданный баланс отвлекает вас от вечного движения жизни. Будьте готовы пожертвовать частью старого порядка, чтобы обрести новую, более гибкую форму.\n\nЧто строится слишком идеально, то боится малейшего движения.\n\nСмысл дня:Стремление к жесткому порядку создает уязвимость."),
                    (19, "19", "https://ibb.co/HpkRCY92", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СУЕТИСЬ\n\nМелкие, бесконечные брызги могут затуманить вам глаза и отвлечь от истинной цели — горизонта. Опасность в том, что вы тратите силы на борьбу с суетой, а не с самой проблемой.\n\nВаш день призывает:не позволяйте мелкой суете поглотить ваше внимание. Осознайте: брызги — это всего лишь последствия большого удара. Не пытайтесь вытереть их по одной. Ваш ограничитель — хаотичная реакция на малозначительные раздражители. Сфокусируйтесь на крупном плане.\n\nНельзя победить хаос, борясь с каждой его каплей.\n\nСмысл дня: Не распыляйте внимания на суету."),
                    (20, "20", "https://ibb.co/F4jnjyrR", "🔱 ПОСЛАНИЕ ДНЯ: ПОБЕДИ ЖАДНОСТЬ\n\nВ мифе Ворона была наказана Аполлоном за свое невоздержание и стала черной. Жадность к чужому ресурсу лишает вас собственной ясности и света.\n\nВаш день призывает:осознайте, что соперничество мешает увидеть новые горизонты. Не позволяйте себе стать «падальщиком», дерущимся за то, что уже найдено. Чрезмерная концентрация на борьбе за чужой кусок сыра отвлекает от поиска собственной, более важной добычи.\n\nТот, кто слишком жаден, в итоге теряет всё.\n\nСмысл дня: Жадность поглощает вашу силу."),
                    (21, "21", "https://ibb.co/wZD01tyS", "🔱 ПОСЛАНИЕ ДНЯ: СМОТРИ ВПЕРЕД\n\nСлишком долгое созерцание мощи крепостных стен может отвлечь вас от движения жизни. Всякая великая история, если ею упиваться, становится клеткой для настоящего.\n\nВаш день призывает: осознайте, что ваш фокус должен быть на море, а не на стене. Не позволяйте величию прошлых достижений или старых убеждений помешать вам действовать сегодня. Рыбак, который смотрит только назад, не увидит новой волны. Ваша задача — быть живым, а не замурованным в истории.\n\nСлишком крепкие стены закрывают горизонт.\n\nСмысл дня: Взгляд в прошлое сковывает волю."),
                    (22, "22", "https://ibb.co/VW1pGxVK", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ОТВЛЕКАЙСЯ НА МЕЛОЧИ\n\nОпасно не само море, а хаос у берега. Мелкая, бурлящая пена грозит поглотить ваше внимание, не давая увидеть истинный, глубокий горизонт.\n\nВаш день призывает:остановите попытки бороться со всей этой пеной одновременно. Всякое внимание, направленное на хаос, умножает его. Найдите твердую скалу среди этого бурления и сделайте паузу, чтобы отделить важное от второстепенного.\n\nНельзя победить хаос, борясь с каждой его каплей.\n\nСмысл дня: Выберите главное, отпустив мелкие заботы."),
                    (23, "23", "https://ibb.co/0yrSNNhk", "🔱 ПОСЛАНИЕ ДНЯ: ПРОВЕРЬ УСТОЙЧИВОСТЬ\n\nВ тихий день легко забыть, что такое настоящие корни. Ваш день указывает на опасность абсолютного покоя — когда нет внешнего движения, вы можете перестать развиваться и чувствовать свой фундамент.\n\nВаш день призывает:используйте это спокойствие для внутренней ревизии. Оцените, не стали ли вы слишком жестким и неподвижным. Задайте себе вопрос: готов ли я к волне, когда она придет? Не позволяйте комфорту стать застоем.\n\nСамые сильные корни растут в глубине, а не на поверхности.\n\nСмысл дня: Комфорт не должен быть застоем."),
                    (24, "24", "https://ibb.co/5WwK8b3r", '🔱 ПОСЛАНИЕ ДНЯ: НЕ ДОВЕРЯЙ ОТРАЖЕНИЮ\n\nВ тихой воде легко обмануться видимостью. Ваш день указывает на иллюзию покоя или опасность слишком быстрого доверия тому, что кажется идеальным.\n\nВаш день призывает: помните, что самая темная глубина скрывается за самым ярким бликом. Не спешите действовать, опираясь на внешнее, "отраженное" впечатление. Замедлитесь и проверьте, что находится под первым впечатлением.\n\nСвет на поверхности не всегда освещает глубину.\n\nСмысл дня: Ищите истину не в отражении, а в глубине.'),
                    (25, "25", "https://ibb.co/hRwL3569", "🔱 ПОСЛАНИЕ ДНЯ: НАРУШЬТЕ ГАРМОНИЮ\n\nСлишком долгое любование собственным отражением или тенью, подобно мифу о Дедале, ищущем идеальную форму, может привести к застою. Штиль всегда предшествует буре.\n\nВаш день призывает: не позволяйте покою отвлечь вас от необходимости движения. Осознайте: идеальная гладь — это временное состояние. Если вы задержитесь в этом самолюбовании, вы рискуете быть разбиты первым же ветром. Отпустите страх нарушить гармонию и сделайте шаг.\n\nИдеальный покой часто предшествует краху.\n\nСмысл дня: Идеальное отражение сковывает волю к действию."),
                    (26, "26", "https://ibb.co/d0GCSBL9", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ТЕРЯЙ БЕРЕГ\n\nНеконтролируемая волна в сочетании с дымкой может легко унести вас далеко от берега. Риск в том, что вы слишком увлечетесь мощью стихии и потеряете из виду реальную цель.\n\nВаш день призывает: не позволяйте эмоциям поглотить ваше внимание. Осознайте: если вы концентрируетесь только на мощи волны, вы теряете направление. Сфокусируйтесь на дымке заката — там неясна цель, но есть направление. Ваша задача — сохранить берег (разум) как ориентир, пока длится шторм.\n\nСлепая сила всегда бьет мимо цели.\n\nСмысл дня: Хаотичная энергия сбивает Вас с пути."),
                    (27, "27", "https://ibb.co/wNhmLGnM", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЖДИ ЧУДА\n\nЧрезмерное ожидание золотого луча может стать ловушкой пассивности. Ограничение в том, что вы отказываетесь действовать, пока не получите идеальное, очевидное чудо свыше.\n\nВаш день призывает: не позволяйте пассивному ожиданию отсрочить действие. Осознайте: вы рискуете провести день, глядя вверх. Идеальная красота и свет — это знак, но не само действие. Спуститесь с небес на землю. Используйте этот свет для начала работы, а не для ее замены.\n\nТот, кто ждет только чуда, теряет время жизни.\n\nСмысл дня: Пассивное ожидание отодвигает мечту."),
                    (28, "28", "https://ibb.co/M59G71Db", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПЕРЕГРУЖАЙСЯ\n\nПарусник, идущий под полными парусами без оглядки, рискует разбиться о шторм. Ограничение — в чрезмерной самоуверенности и желании контролировать скорость.\n\nВаш день призывает: осознайте, что скорость может стать ловушкой. Не позволяйте себе увлечься гонкой и пренебречь внутренним балансом. Чрезмерное давление на паруса приведет к разрыву. Ваша задача — замедлиться и проверить свой курс, чтобы быть готовым к неожиданному изменению ветра.\n\nСлепая скорость всегда ведет к крушению.\n\nСмысл дня:Чрезмерная самоуверенность сбивает с курса."),
                    (29, "29", "https://ibb.co/bMzLVznY", "🔱 ПОСЛАНИЕ ДНЯ: СОХРАНИ РАССУДОК\n\nМистическая сила ночи и огромные волны могут полностью поглотить ваше сознание. Это риск, когда неконтролируемое настроение берет верх над разумом.\n\nВаш день призывает: осознайте, что слепая мощь разрушает. Не позволяйте гипнотической силе волны оторвать вас от берега (реальности). Чрезмерная концентрация на мистике и эмоциях лишает вас якоря. Если вы не контролируете внутренний прилив, он унесет вас в открытое море.\n\nТот, кто слишком увлекается тайной, теряет рассудок.\n\nСмысл дня: Слепое доверие эмоциям ведет к потере себя."),
                    (30, "30", "https://ibb.co/SDByKKvq", "🔱 ПОСЛАНИЕ ДНЯ: ОТПУСТИ ИЗЖИВШЕЕ\n\nКружево облаков, которое не может быть вечным, напоминает: что тонко, то и рвется. Вы держитесь за что-то, что давно изжило себя и готово распасться.\n\nВаш день призывает: осознайте, что потеря уже произошла. Не цепляйтесь за форму, которая стала слишком хрупкой. Чтобы избежать полного разрушения, нужно перестать жить иллюзиями. Смелость в том, чтобы позволить старому исчезнуть.\n\nЧто не рвется сейчас, рванет двойной силой.\n\nСмысл дня:Жизнь в иллюзии разрушает."),
                    (31, "31", "https://ibb.co/C5x9pJwM", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СТАНЬ ТЕНЬЮ\n\nСумерки могут создать иллюзию движения при полной неподвижности. Риск в том, что вы можете застрять на этой границе, потеряв активную волю.\n\nВаш день призывает: не позволяйте двусмысленности парализовать ваш выбор. Осознайте: это время, когда легко стать тенью. Если вы отказываетесь выбрать день или ночь, вы остаетесь невидимым. Вы должны сделать решительный шаг, даже если он кажется неясным.\n\nТот, кто стоит на границе, не принадлежит ничему.\n\nСмысл дня:Двусмысленность момента парализует вашу волю."),
                    (32, "32", "https://ibb.co/4gV4YP8N", "🔱 ПОСЛАНИЕ ДНЯ: ОСВОБОДИСЬ ОТ ПЕЧАЛИ\n\nВ этом пограничном месте легко стать пленником прошлого. Риск в том, что вы слишком долго слушаете свое эхо (печальную песню) и отказываетесь выйти к свету и движению.\n\nВаш день призывает: не позволяйте своему прошлому резонировать бесконечно. Осознайте: эхо — это повторение, а не движение вперед. Если вы долго остаетесь в темноте, вы теряете волю к выходу. Признайте этот голос, но не дайте ему диктовать условия настоящего дня.\n\nГраница — это место для перехода, а не для жизни.\n\nСмысл дня: Привязка к прошлому блокирует Вашу свободу."),
                    (33, "33", "https://ibb.co/Cpfxt33s", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЗАКРЫВАЙСЯ\n\nКамень, который не пускает в себя волну и свет, становится холодным и одиноким. Риск в том, что вы отказываетесь принять изменение или красоту момента.\n\nВаш день призывает: не позволяйте своей твердости стать изоляцией. Осознайте: если вы слишком держитесь за свою неизменность, вы пропустите возможность стать частью этого великого, завершающего цикла. Иногда нужно позволить волне обмыть себя, чтобы обновиться.\n\nТот, кто слишком тверд, не может обновиться.\n\nСмысл дня: Излишняя стабильность сковывает вашу волю."),
                    (34, "34", "https://ibb.co/DHwmL1kH", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПАНИКУЙ\n\nГрозовая туча вызывает чувство тревоги и желание бежать, что приводит к хаотичным, неэффективным действиям. Риск в том, чтобы сосредоточиться на страхе, а не на подготовке.\n\nВаш день призывает: не позволяйте панике забрать оставшееся время. Осознайте: сама туча еще не наступила. Если вы тратите силы на тревогу, вы лишаете себя возможности укрепить свои позиции. Пассивный страх — худший враг. Ваши действия должны быть четкими и логичными, а не эмоциональными.\n\nТот, кто бежит до шторма, устанет во время него.\n\nСмысл дня: Паника лишает вас возможности подготовиться."),
                    (35, "35", "https://ibb.co/4RfNv5nr", "🔱 ПОСЛАНИЕ ДНЯ: НЕ БОЙСЯ ТЕНИ\n\nИдеальная ясность может заставить вас поверить, что в жизни нет невидимых препятствий. Риск в том, что вы слишком доверяете видимости и отказываетесь искать то, что скрыто.\n\nВаш день призывает: осознайте, что прозрачность — временное состояние. Не позволяйте себе игнорировать теневые зоны. Если вы постоянно смотрите только на свет, вы рискуете споткнуться о те камни, которые видны, но игнорируются. Совершенный порядок часто скрывает отсутствие гибкости.\n\nТот, кто верит только видимому, слепнет к скрытому.\n\nСмысл дня: Идеальный порядок сковывает Вашу гибкость."),
                    (36, "36", "https://ibb.co/9k1Xg3PC", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СДАВАЙСЯ\n\nПолное отсутствие света и тучи могут создать иллюзию безнадежности и бесконечности кризиса. Риск в том, что вы сдаетесь из-за ощущения, будто тьма никогда не закончится.\n\nВаш день призывает:не позволяйте отчаянию парализовать ваше движение. Осознайте: тьма — это временное состояние. Если вы останавливаетесь, считая, что нет пути, вы дарите победу хаосу. Продолжайте двигаться, полагаясь на ощущение скалы под ногами, а не на видимость.\n\nТот, кто сдается во тьме, не увидит рассвета.\n\nСмысл дня: Отчаяние в хаосе лишает вас сил."),
                    (37, "37", "https://ibb.co/xtd3X8mT", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПРЯЧЬСЯ В СТЕНАХ\n\nОставаясь слишком долго внутри крепости, вы превращаете защиту в тюрьму. Тень, падающая на море, — это ваше собственное наследие, которое может закрыть вам обзор.\n\nВаш день призывает: не позволяйте своему прошлому сковывать ваше будущее. Осознайте: вы рискуете стать пленником своих старых убеждений или накопленной мудрости. Ваша крепость должна служить базой, а не местом скрытия. Вам нужно выйти и встретиться с волной.\n\nТот, кто живет в тени прошлого, не видит солнца.\n\nСмысл дня: Чрезмерная защита лишает вас развития."),
                    (38, "38", "https://ibb.co/vxHLDy3v", "🔱 ПОСЛАНИЕ ДНЯ: СТАНЬ ЦЕЛОСТНЫМ\n\nРиск в том, что вы пытаетесь выбрать только одну сторону — стать только Цаплей или только Вороном — и игнорируете противоположную. Это ведет к потере полноты картины и внутреннему конфликту.\n\nВаш день призывает:не позволяйте одной силе подавить другую. Осознайте: если вы отвергаете тень (Ворона), вы лишаетесь мудрости. Если вы отвергаете свет (Цаплю), вы теряете чистоту. Попытка навязать доминирование одной стороне приведет к тому, что вся система рухнет.\n\nЦелое сильнее суммы своих половин.\n\nСмысл дня:Игнорирование противоположностей лишает вас силы."),
                    (39, "39", "https://ibb.co/rRdCvCWy", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ОТТАЛКИВАЙ ВОЛНУ\n\nХотя Афродита вышла из пены, вы можете попытаться оттолкнуть саму волну, которая её принесла. Риск в том, что вы слишком увлечетесь идеальной красотой и откажетесь от необходимого контакта с бурлящим настоящим.\n\nВаш день призывает:осознайте, что красота требует взаимодействия со стихией. Осознайте: если вы избегаете этой пены (активного участия), вы остаетесь на сухом берегу, наблюдая, как энергия уходит от вас. Вам нужно не только любоваться результатом, но и позволить себе быть омытым процессом.\n\nТот, кто боится волны, не получит её дар.\n\nСмысл дня:Избегание стихии лишает вас свежей энергии."),
                    (40, "40", "https://ibb.co/jxxfRnV", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЗАСТРЕВАЙ\n\nМесто, где река собралась перед слиянием, может стать застоем. Риск в том, что вы слишком долго колеблетесь на границе, не решаясь отдать свою силу большему потоку.\n\nВаш день призывает:не позволяйте остановке перед финалом стать застоем. Осознайте: если вы не делаете последний шаг, вся накопленная энергия (вода реки) становится мертвой. Сопротивление переходу из одного состояния в другое (из реки в море) блокирует ваше развитие и лишает вас чистоты неба.\n\nСамое опасное место — это остановка перед финишем.\n\nСмысл дня: Колебание на границе лишает вас силы."),
                    (41, "41", "https://ibb.co/rCdVhks", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СТАНЬ ДЛЯ СЕБЯ ТЮРЬМОЙ\n\nБастион, который закрывается от моря, рискует превратить защиту в изоляцию. Риск в том, что ваша стремление к неуязвимости блокирует контакт с миром (морем) и его энергией.\n\nВаш день призывает: не позволяйте твердости стать косностью и одиночеством. Осознайте: стены нужны, чтобы смотреть с них на мир, а не прятаться за ними. Чрезмерная защита приводит к стагнации и потере возможности взаимодействия с жизнью. Вам нужно иногда спускаться, чтобы ощутить волну.\n\nСила, не знающая гибкости, недолговечна.\n\nСмысл дня: Чрезмерная защита лишает вас развития."),
                    (42, "42", "https://ibb.co/21xBVxKB", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЦЕПЛЯЙСЯ ЗА БОЛЬ\n\nРиск в том, что вы, подобно Сизифу, слишком привязаны к своей тяжести (обиде) и отказываетесь ее отпустить, считая этот груз частью своей личности.\n\nВаш день призывает: не позволяйте грузу прошлого определять ваше настоящее. Осознайте: два камня, лежащие на песке, — это выбор. Если вы не сбросите это бремя в море, оно останется на берегу. Это не внешняя сила держит вас; это вы держитесь за боль, которую море готово унести.\n\nТот, кто цепляется за боль, не знает свободы.\n\nСмысл дня:больпрошлоголишает вас легкости."),
                    (43, "43", "https://ibb.co/Rp6DS3Lk", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЗАСТРЯНЬ В МЕЛОЧАХ\n\nРиск в том, что вы можете увлечься изучением мелочей и забудете о большой цели. Мелкие детали и текущие задачи могут стать ловушкой для внимания.\n\nВаш день призывает: не позволяйте скрупулезности отвлечь вас от основного пути. Осознайте: вода в этих углублениях — это остатки большой волны. Если вы долго задержитесь в анализе мелочей, вы упустите динамику и свободу чистого горизонта. Вы должны смотреть на воронки, но стремиться к морю.\n\nТот, кто слишком долго смотрит вниз, забывает о небе.\n\nСмысл дня: Избыточная детализация лишает вас движения."),
                    (44, "44", "https://ibb.co/jZf3n1Kq", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СБИВАЙСЯ С ПУТИ\n\nЧистота горизонта таит в себе соблазн чужого маршрута. Риск в том, что вы путаете свое движение с чужим или пытаетесь угнаться сразу за двумя разными точками назначения.\n\nВаш день призывает: не позволяйте чужому курсу отвлекать вас от собственного направления. Осознайте: если вы фокусируетесь на движении другого, вы теряете свою цель. Определите, что для вас важно, и придерживайтесь выбранного курса.\n\nТот, кто смотрит на чужой парус, сбивается с пути.\n\nСмысл дня:Размытая цель — потерянное время."),
                    (45, "45", "https://ibb.co/zVWNH3Zf", "🔱 ПОСЛАНИЕ ДНЯ: ВЫЙДИ ЗА РАМКУ\n\nРамка жизни, которая дарит покой, может стать темницей для духа. Риск в том, что вы слишком привязаны к безопасности созерцания и отказываетесь выйти за пределы своего защищенного мира.\n\nВаш день призывает:не позволяйте идеальному виду заменить собой живое участие. Осознайте: вы видите чистый горизонт, но не движетесь к нему. Если вы не покинете скамью, вы станете пленником своего идеального, но теоретического опыта.\n\nТот, кто слишком долго сидит, становится частью скамьи.\n\nСмысл дня:Идеальные условия — тюрьма для опыта."),
                    (46, "46", "https://ibb.co/1YLB7vJn", "🔱 ПОСЛАНИЕ ДНЯ: СТАНЬ СМЕЛЕЕ\n\nРиск в том, что, стремясь к безопасному укрытию (каменистый берег), вы становитесь слишком незаметным и теряете свою хищную природу. Чрезмерное слияние с окружением может превратиться в пассивность.\n\nВаш день призывает: не позволяйте инстинкту выживания подавить вашу волю к действию. Осознайте: вы должны быть живым наблюдателем, а не просто камнем. Если вы слишком долго будете прятаться, большая волна может забрать не только обломки, но и вашу энергию. Сохраняйте внутренний огонь.\n\nТот, кто слишком долго прячется, забывает, как охотиться.\n\nСмысл дня: Чрезмерная осторожность — потеря воли."),
                    (47, "47", "https://ibb.co/cKBbc1KN", '🔱 ПОСЛАНИЕ ДНЯ: НЕ ОСТАНАВЛИВАЙСЯ\n\nРиск в том, что вы пытаетесь отделить мутную воду реки от чистого горизонта. Вы можете отказаться принять свое прошлое или свои усилия, считая их "недостаточно чистыми" для "светлой цели".\n\nВаш день призывает: не позволяйте самокритике и чувству незавершенности остановить финальный прорыв. Осознайте: движение — это жизнь. Если вы остановите поток, вода застоится и загниет. Вы должны позволить себе войти в море таким, какой вы есть, со всей своей "мутью" и историей.\n\nПопытка казаться, а не быть блокирует путь.\n\nСмысл дня: Сомнение в себе — остановка движения.'),
                    (48, "48", "https://ibb.co/j9M7YJPd", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПРЕДАВАЙ СЕБЯ\n\nРиск в том, что вы позволяете общему серому фону (тяжесть, печаль, усталость) полностью поглотить вашу волю и ваше видение. Вы можете перестать искать свет, потому что его трудно увидеть.\n\nВаш день призывает:не позволяйте настроению окружающего мира отнять у вас чувство цели. Осознайте: хотя Солнце скрыто, оно есть. Ваша работа важна, но если вы будете смотреть только на тяжелые камни, вы забудете о потенциале дальнего горизонта. Не позволяйте тени сделать вас пассивным.\n\nТот, кто принимает тучи за истину, теряет солнце.\n\nСмысл дня: Пассивность — это плен серого дня."),
                    (49, "49", "https://ibb.co/9HPvGDCH", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ВИТАЙ В ОБЛАКАХ\n\nРиск в том, что вы, летя слишком высоко, забываете о необходимости спуска. Прекрасная траектория в облаках мешает вам увидеть и совершить улов, который нужен для жизни.\n\nВаш день призывает: не позволяйте большому, абстрактному видению оторвать вас от малого, насущного действия. Осознайте: парение — это поиск, но успех — это нырок. Если вы смотрите только на небо, вы пропустите момент для решающего броска и останетесь без добычи.\n\nТот, кто летает в облаках остается без улова.\n\nСмысл дня: Без действия нет добычи (результата)."),
                    (50, "50", "https://ibb.co/vxBVcHKv", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЖДИТЕ ЧУДА\n\nРиск в том, что вы пассивно сидите на скамье, ожидая, пока яркий закат вернется или чудо придет с моря. Вы можете стать зависимым от искусственного света и бояться шагнуть в темноту, которую он не освещает.\n\nВаш день призывает: не позволяйте комфорту и ожиданию лишить вас активного движения. Осознайте: ограда — это граница, а не цель. Если вы слишком долго остаетесь в освещенном, безопасном месте, вы пропускаете глубину и возможности, которые таит в себе наступающая темнота.\n\nТот, кто слишком долго ждет, пропускает ночь.\n\nСмысл дня: Пассивное ожидание — потеря времени."),
                    (51, "51", "https://ibb.co/PZW5yXXv", "🔱 ПОСЛАНИЕ ДНЯ: БУДЬ СОБОЙ\n\nРиск в том, что ваш сильный, яркий свет — это всего лишь внешнее освещение, которое отвлекает от истинной, природной силы скалы. Вы можете стать декорацией, зависящей от чужой энергии.\n\nВаш день призывает: не позволяйте внешнему вниманию заменить собой глубинную работу и истинный покой. Осознайте: скала остается собой, даже если свет погаснет. Чрезмерная фокусировка на демонстративном поведении и внешнем эффекте лишает вас возможности взаимодействовать с природными циклами и другими людьми.\n\nТот, кто живет чужим светом, гаснет первым.\n\nСмысл дня:Внешний эффект — искажает суть."),
                    (52, "52", "https://ibb.co/27vGsM3n", "🔱 ПОСЛАНИЕ ДНЯ: СОХРАНЯЙ ЯСНОСТЬ\n\nБуря мглою небо кроет. Риск в том, что вы теряете свою траекторию, увлеченные силой и скоростью волн. Вместо использования хаоса для движения, вы становитесь его частью, позволяя мутной воде затянуть вас и лишить ясности.\n\nВаш день призывает: не позволяйте энергии момента заглушить ваш внутренний голос и цель. Осознайте: вы должны быть над волнами, а не в них. Чрезмерное погружение в эмоциональный или внешний хаос приведет к тому, что вы потеряете различие между собой и средой.\n\nТот, кто слишком доверяется буре – разбивается о камни.\n\nСмысл дня: Утрата контроля приводит к потере себя."),
                    (53, "53", "https://ibb.co/0pn1WCqD", '🔱 ПОСЛАНИЕ ДНЯ: ВЫХОДИ НА ПОВЕРХНОСТЬ\n\nРиск в том, что вы зацикливаетесь на своем внутреннем мире, считая его единственной реальностью. Это может стать ловушкой, если вы боитесь выбраться из него на большую, движущуюся воду.\n\nВаш день призывает: не позволяйте безопасности и комфорту своего "колодца" отрезать вас от общего течения жизни. Осознайте: вы должны быть живой частью цикла. Если вода в углублении слишком долго остается неизменной, она становится темной и застаивается. Не позволяйте застывшему опыту заменить собой новое движение.\n\nТот, кто слишком долго стоит, становится частью дна.\n\nСмысл дня:Излишняя фиксация на себе — потеря течения жизни.'),
                    (54, "54", "https://ibb.co/LDSvMBBf", "🔱 ПОСЛАНИЕ ДНЯ: БУДЬ ГИБОК\n\nРиск в том, что вы теряете связь с реальностью, фокусируясь лишь на ясности неба и морской пене Вы можете решить, что ваше идеальное видение полностью контролирует мощь моря и его волны.\n\nВаш день призывает: не позволяйте абстрактному планированию оторвать вас от необходимости работать с фактической силой и энергией мира (море). Осознайте: сила моря не знает логики, а ваша воля должна быть гибкой, как волна. Если вы смотрите только на небо, вы никогда не научитесь управлять реальной, непредсказуемой энергией.\n\nТот, кто слишком верит в план, тонет в стихии.\n\nСмысл дня: Пренебрежение силой — путь к краху."),
                    (55, "55", "https://ibb.co/Q3G0fNSs", "🔱 ПОСЛАНИЕ ДНЯ: СБРОСЬ СКОРОСТЬ\n\nЧрезмерная скорость всегда угрожает потерей контроля и сбивает ритм. Подобно тому, как излишняя поспешность пугает коня и бросает всадника, вы рискуете споткнуться, если будете фиксировать внимание только на конечной цели, игнорируя красоту и угрозы текущей тропы.\n\nВаш день призывает: замедлите свой бег. Осознайте: путь, который казался свободным, не терпит суеты. Если вы действуете без внимания к деталям, вы теряете единство с вашей внутренней силой. Притормозите, чтобы восстановить баланс и увидеть, что находится прямо у вас под ногами.\n\nТот, кто спешит, видит цель, но не видит дорогу.\n\nСмысл дня: Поспешность —это ловушка, лишающая контроля."),
                    (56, "56", "https://ibb.co/VcRbR1Cd", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СТОЙ НА МЕСТЕ\n\nПирс был создан для отправления, а не для постоянного пребывания. Риск в том, чтобы остаться пленником комфорта, любуясь морем издалека, но не решаясь войти в него. Пальмовые листья могут стать золотой клеткой.\n\nВаш день призывает: преодолейте мнимую устойчивость берега. Осознайте: идеальная позиция для наблюдения — это худшее место для действия. Если вы слишком долго стоите на пирсе, волны стирают ваш след.\n\nВода не терпит тех, кто смотрит, но не плывет.\n\nСмысл дня: Комфорт берега — главное ограничение для роста."),
                    (57, "57", "https://ibb.co/dwLDSnPx", "🔱 ПОСЛАНИЕ ДНЯ: НЕ УПУСТИ ДЕТАЛИ\n\nРиск в том, что далекие, но прекрасные цели (корабли) заставляют вас игнорировать ближайшую реальность. Вы можете увлечься мечтой, не обращая внимания на мощь волн, которые формируют ваш путь.\n\nВаш день призывает: не позволяйте своему взору быть постоянно прикованным к далекому горизонту. Осознайте: пренебрежение деталями здесь и сейчас (мощью ближайших волн) может привести к потере равновесия. Чтобы достичь цели, нужно научиться управлять стихией, которая находится прямо перед вами.\n\nТот, кто смотрит только вдаль, не видит, что творится под ногами.\n\nСмысл дня: Пренебрежение настоящим — причина потери контроля."),
                    (58, "58", "https://ibb.co/vCMDf7hy", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЗАВИСАЙ\n\nНеподвижность, переходящая в оцепенение, лишает вас возможности реагировать на смену течений. Подобно птице, которая слишком долго стоит в одной точке, вы рискуете оказаться в ловушке самообмана, решив, что пассивность — это стабильность.\n\nВаш день призывает: преодолейте иллюзию покоя. Осознайте: туман не вечен. Если вы отказываетесь двигаться, вы не сможете быстро отреагировать, когда он рассеется. Ваша задача — быть не каменной статуей, а живым, готовым к взлету наблюдателем.\n\nОцепенение в буре так же губительно, как и хаотичный бег.\n\nСмысл дня: Пассивное ожидание — главный ограничитель."),
                    (59, "59", "https://ibb.co/q3RdDSXp", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ИГНОРИРУЙ ЗНАКИ\n\nСамый большой риск — поверить в иллюзию вечного покоя, несмотря на явные знаки надвигающейся опасности. Подобно жителям Трои, игнорировавшим пророчества Кассандры, вы рискуете быть застигнутым врасплох.\n\nВаш день призывает: не позволяйте очарованию глади заставить вас забыть о необходимости действовать. Осознайте: пренебрежение очевидной угрозой и излишняя расслабленность могут привести к краху. Вы должны быть на песке, но готовым в любой момент сорваться с места, а не спать в ожидании бури.\n\nКто не видит тучу над гладью будет поражен молнией Зевса.\n\nСмысл дня: Слепое доверие к покою — застает врасплох."),
                    (60, "60", "https://ibb.co/gLnn3CRY", "🔱 ПОСЛАНИЕ ДНЯ: ВЫБЕРИ ДЕЙСТВИЕ\n\nКрасота и комфорт луга могут стать самой опасной ловушкой. Подобно герою, который слишком долго задерживается в волшебном саду нимфы Калипсо, вы рискуете забыть о своем истинном предназначении, околдованный покоем и статичностью.\n\nВаш день призывает: не позволяйте комфорту настоящего стать причиной стагнации. Осознайте: море манит не для того, чтобы вы любовались им издалека, а для того, чтобы войти в него. Если вы слишком долго остаетесь в одном месте, вы теряете связь с динамикой жизни. Откажитесь от золотой клетки: ваше место не там, где красиво, а там, где есть движение.\n\nКто не рискует, тот не увидит горизонта.\n\nСмысл дня:Чрезмерный комфорт —ограничитель роста."),
                    (61, "61", "https://ibb.co/5gd74TVK", "🔱 ПОСЛАНИЕ ДНЯ: СФОКУСИРУЙСЯ НА ЦЕЛИ\n\nРиск в том, чтобы застрять в поверхностном, принимая игру за реальную работу. Подобно моряку, который тратит все силы на борьбу с мелкой прибрежной волной, не видя дальнего пути, вы рискуете потратить ресурс впустую.\n\nВаш день призывает: не позволяй мелким, игривым проблемам отвлекать тебя от стратегического пути. Осознай: твои цели требуют постоянного, направленного усилия. Если ты растрачиваешь энергию на пустяки, ты не сможешь использовать ее для достижения чего-то по-настоящему важного.\n\nКто играет слишком долго, тот забывает, куда плывет.\n\nСмысл дня: Растрата энергии на второстепенное ограничивает."),
                    (62, "62", "https://ibb.co/j954wv5L", "🔱 ПОСЛАНИЕ ДНЯ: ПРЕОДОЛЕЙ ИНЕРЦИЮ\n\nОтвернутый стул символизирует инерцию или подсознательное бегство от огромной силы, которую предлагает мир. Вы рискуете упустить возможности солнечного дня, застряв в пассивном уединении.\n\nВаш день призывает: не позволяйте инертному, даже частичному, уходу от мира стать вашей зоной комфорта. Осознайте: стул — это временное место, но ваше внимание приковано к тому, что позади, а не к возможностям (пена, волны). Вы, подобно Одиссею, не можете вечно сидеть и смотреть вдаль. Настоящее ограничение — это ваш страх развернуться лицом к жизни.\n\nТот, кто сидит, но не смотрит, не увидит бурю.\n\nСмысл дня: Избегание действия — ограничитель развития."),
                    (63, "63", "https://ibb.co/zjfCk9k", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПОДДАЙСЯ ПРОБЛЕМЕ\n\nРиск в том, чтобы сосредоточить все внимание на неуправляемой стихии, позволяя ей поглотить ваше восприятие, даже если свет уже пробивается. Это ловушка отчаяния и инерции перед лицом надвигающегося напряжения.\n\nВаш день призывает: не позволяйте давлению проблем лишить вас воли к действию. Осознайте: разбушевавшаяся стихия — это временная тень, а не ваша судьба. Вы рискуете упустить момент, когда пробившийся луч требует незамедлительного движения. Слишком долгое пребывание в напряжении заставляет забыть о существовании солнца.\n\nТот, кто смотрит на бурю, не увидит луча.\n\nСмысл дня: Фиксация на проблеме — ограничитель прогресса."),
                    (64, "64", "https://ibb.co/TDCb0tqm", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПОТЕРЯЙ ЦЕЛЬ\n\nРиск в том, чтобы позволить хаосу и мраку поглотить ваше внимание, заставив вас забыть о главном. Вы можете оказаться пленником пены и брызг, теряя из виду корабли — символ вашего намеченного пути.\n\nВаш день призывает: не позволяйте временному хаосу затмить постоянную цель. Осознайте: хмурое небо и пена — это лишь фон. Если вы смотрите только на ближайшую угрозу, вы теряете стратегическое преимущество. Сохраняйте ментальную связь с кораблями, чтобы не утонуть в отчаянии момента.\n\nКто смотрит на пену, тот не видит горизонта.\n\nСмысл дня: Фиксация на хаосе — ограничитель движения к цели."),
                    (65, "65", "https://ibb.co/Wp4QPg5x", "🔱 ПОСЛАНИЕ ДНЯ: ПРЕОДОЛЕЙ ТОСКУ\n\nРиск в том, что неподвижность становится оцепенением, а ожидание — страданием. Подобно Прометею, прикованному к скале, вы рискуете застрять в метаниях, глядя на серое море с тоской, но не решаясь ни уйти, ни действовать.\n\nВаш день призывает: не позволяй пассивному страданию поглотить твою волю. Осознай: серое море — отражение твоей внутренней тоски, а не внешней реальности. Вы рискуете упустить момент возвращения или движения, если будете слишком долго зафиксированы на своем горе. Ваше место не на камне, а в потоке.\n\nСтрадание, которое не ведет к действию, — это плен.\n\nСмысл дня: Фиксация на тоске — главный ограничитель."),
                    (66, "66", "https://ibb.co/0VXYTMY8", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ОГЛЯДЫВАЙСЯ\n\nРиск в том, что ты живешь не в настоящем, а в отражении себя прошлого. Подобно герою, который, очарованный своим отражением, застыл, не решаясь двинуться к морю, ты рискуешь быть захваченным тенью или грузом воспоминаний.\n\nВаш день призывает:осознай, что твоя тень — это уже минувший миг. Не позволяй теням из прошлого определять твое движение вперед. Старые проблемы на пути станут преградой, если ты будешь смотреть назад. Твоя задача — смотреть на море (будущее), а не на песок, который уже пройден.\n\nКто живет в тени — лишается света.\n\nСмысл дня: Фиксация на прошлом — ограничитель свободы."),
                    (67, "67", "https://ibb.co/Y7ghqDBg", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ОГЛЯДЫВАЙСЯ\n\nРиск в том, что утес становится тюрьмой, а его непоколебимость — негибкостью. Подобно руинам, которые, гордо стоя, мешают новым кораблям следовать новым маршрутам, вы рискуете быть привязанным к своей старой, жесткой форме.\n\nВаш день призывает: не позволяй прошлой славе или травмам ограничивать твое настоящее. Осознай: жесткая, неизменная структура блокирует течение жизни. Вы рискуете упустить возможности нового, светлого неба, если будете цепляться за память о минувшей грозе. Смелее выходи из прохода, не оставаясь его частью.\n\nЧто не может течь, то зарастает мхом.\n\nСмысл дня: Чрезмерная привязанность к прошлой форме — ограничитель."),
                    (68, "68", "https://ibb.co/ccpDy9Jc", "🔱 ПОСЛАНИЕ ДНЯ: НЕ БОЙСЯ ТЬМЫ\n\nРиск в том, чтобы застрять в красоте уходящего дня и позволить меланхолии поглотить тебя. Подобно Орфею, который, оглянувшись назад, потерял самое ценное, вы рискуете упустить будущее из-за привязанности к прошлому моменту.\n\nВаш день призывает: не позволяй уходящему свету заслонить себе необходимость готовиться к ночи. Осознай: после самого яркого заката неизбежно наступает темнота. Если ты будешь оплакивать конец дня, ты не сможешь использовать темноту для отдыха и восстановления. Развернись лицом к морю: ночь — это лишь другая фаза пути.\n\nКто слишком долго смотрит на закат, тот боится рассвета.\n\nСмысл дня: Привязанность к прошлому моменту — ограничитель."),
                    (69, "69", "https://ibb.co/nqnw4zNV", "🔱 ПОСЛАНИЕ ДНЯ: ВЫЙДИ К СВЕТУ\n\nЗащищенная пещера может стать самой настоящей тюрьмой, если страх перед ночью и волнами сильнее, чем стремление к целям. Вы рискуете стать пленником своего уединения и бездействия.\n\nВаш день призывает: не позволяй комфорту грота изолировать себя от жизни. Осознай: огни города манят, но они останутся лишь далекой мечтой, если ты не пожертвуешь своей безопасностью. Преодолей страх перед темнотой и хаосом. Твоя задача — выйти из тени и вступить в мир, даже если он не идеален и уже погружен в ночь.\n\nКто не рискует выйти из пещеры, тот не увидит рассвета.\n\nСмысл дня: Избыточная защищенность — ограничитель действия."),
                    (70, "70", "https://ibb.co/6cNW4yLt", "🔱 ПОСЛАНИЕ ДНЯ: БУДЬ БДИТЕЛЬНЫМ\n\nРиск в том, что мягкость рассвета усыпляет бдительность, а снисходительная волна заставляет забыть об истинной силе моря. Вы можете перепутать милость с полной безопасностью.\n\nВаш день призывает: не позволяй нежной дымке заслонить от тебя необходимость бдительности. Осознай: даже самая снисходительная волна напоминает о безграничной мощи, скрытой под ней. Если ты воспримешь легкость как должное, ты не подготовишься к моменту, когда волна накроет тебя.\n\nКто верит в вечную нежность, тот не готов к шторму.\n\nСмысл дня: Излишняя расслабленность блокирует бдительность."),
                    (71, "71", "https://ibb.co/mCMp8MCh", "🔱 ПОСЛАНИЕ ДНЯ: ПЕРЕСТАНЬ БОРОТЬСЯ\n\nРиск в том, чтобы застрять в борьбе и боли столкновения, принимая временное разрушение за окончательный приговор. Вы можете упустить из виду тот факт, что за черной тучей по-прежнему находится голубое небо.\n\nВаш день призывает: не позволяй грохоту волн заглушить твой внутренний голос. Осознай: черная туча, нависающая над небом, — это лишь часть картины, а не вся реальность. Если ты фокусируешься только на борьбе, ты теряешь перспективу и забываешь о своей главной цели.\n\nТот, кто слышит только грохот, забывает о тишине.\n\nСмысл дня: Фиксация на борьбе — уводит от цели."),
                    (72, "72", "https://ibb.co/mM5j8fc", "🔱 ПОСЛАНИЕ ДНЯ: ПРЕОДОЛЕЙ ГРАНИЦУ КОМФОРТА\n\nРиск волнореза не в его наличии, а в нежелании его покинуть. Подобно кораблю, который стоит у причала, любуясь закатом, но не решаясь выйти в открытое море, вы рискуете застрять в созданном вами комфорте.\n\nВаш день призывает: не позволяй идеальным условиям стать причиной бездействия. Осознай: волнорез защищает, но он же и ограничивает. Если ты слишком долго остаешься в штиле, ты теряешь навык навигации в волнах. Твоя задача — использовать эту ясность для выхода за пределы искусственной границы.\n\nКто боится волн, тот не увидит дальних берегов.\n\nСмысл дня: Избыточный контроль и штиль — ограничитель движения."),
                    (73, "73", "https://ibb.co/Rk5x321b", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЗАСТРЕВАЙ В ТОСКЕ\n\nРиск в том, что созерцание переходит в пассивную тоску, а камни становятся оковами. Вы рискуете, подобно Нарциссу, застрять в отражении своей грусти, которое подпитывается серым, спокойным морем.\n\nВаш день призывает: не позволяй грусти превратиться в инерцию. Осознай: спокойное море не требует от тебя бездействия; оно лишь отражает твое настроение. Если ты остаешься на камнях, то чайки возможностей пролетят мимо. Твоя задача — использовать твердую почву под ногами не для ожидания, а для решительного шага вперед.\n\nТот, кто слишком долго ждет, забывает, чего он ждет.\n\nСмысл дня: Пассивная тоска — ведет к замиранию и остановке."),
                    (74, "74", "https://ibb.co/vC7DdySQ", "🔱 ПОСЛАНИЕ ДНЯ: ПЕРЕСТАНЬ ОБОРОНЯТЬСЯ\n\nРиск в том, что безопасность превращается в постоянное напряжение, а крепость — в тюрьму, защищающую от несуществующего врага. Вы рискуете застрять в циклической тревоге волн.\n\nВаш день призывает: не позволяй тревоге определять твою реальность. Осознай: постоянная оборона крепость и требует колоссальных затрат энергии. Если вы слишком долго сфокусированы на невидимом враге, вы забываете о жизни внутри стен. Твоя задача — найти способ отпустить тревогу, даже если волны продолжают биться о стены.\n\nКто постоянно держит оборону, тот забывает, как жить мирно.\n\nСмысл дня: Постоянная тревога — ограничитель свободы."),
                    (75, "75", "https://ibb.co/prhmF9jw", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ТЕРЯЙ СЕБЯ\n\nРиск в том, чтобы быть ослепленным грандиозностью цели и утратить свое личное течение. Вы рискуете потерять уникальную форму, которую несет ваше предназначение, в безликой стихии.\n\nВаш день призывает: сохраняй идентичность в моменте слияния. Осознай: если ты заворожен игривостью моря и лохматыми облаками, ты можешь потерять фокус на процессе, который привел тебя сюда. Твоя задача — не просто раствориться, а принести свою силу и чистоту в этот союз.\n\nКто спешит раствориться, тот не оставляет следа.\n\nСмысл дня: Потеря уникальной формы — уводит от предназначения."),
                    (76, "76", "https://ibb.co/wZt3stT4", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ОСТАНАВЛИВАЙСЯ\n\nРиск этого идеального момента — в его соблазне к пассивности. Вы рискуете стать пленником красоты, завороженные закатом, но забывая, что Луна требует действий.\n\nВаш день призывает: не позволяй совершенству момента стать причиной стагнации. Осознай: если ты останешься в комфорте беседок, ты упустишь то время, когда нужно выйти в море. Твоя задача — не любоваться, а использовать энергию перехода. Слишком долгое пребывание в точке покоя лишит тебя возможности действовать под покровом новой ночи.\n\nТот, кто слишком долго смотрит на небо, забывает о земле.\n\nСмысл дня: Используй энергии Солнца и Луны для движения вперед."),
                    (77, "77", "https://ibb.co/K3Tp8mt", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПОДДАЙСЯ ИЛЛЮЗИИ\n\nСамый большой риск — поверить в искажение, которое создает уходящий день, и позволить причудливой туче заслонить цель. Вы рискуете застрять в эмоциональной ловушке, принимая иллюзию за истинную преграду.\n\nВаш день призывает: не позволяй тревоге и искаженному зрению лишить тебя способности действовать. Осознай: если ты смотришь на тучу, ты не видишь корабля-звезды. Твоя задача — преодолеть ментальный шум, который возникает на закате, и сосредоточить всю волю на цели. Если ты потеряешь корабль, серое море поглотит тебя.\n\nТот, кто верит в тень, забывает о свете.\n\nСмысл дня: Искаженное восприятие — ограничитель ясности."),
                    (78, "78", "https://ibb.co/WWVNzYvw", "🔱 ПОСЛАНИЕ ДНЯ: ДВИГАЙСЯ ПОСТУПАТЕЛЬНО\n\nРиск в том, чтобы быть парализованным грандиозностью цели, которую символизирует гигантский гребень тучи. Вы рискуете тратить всю свою энергию на размышления о масштабе, вместо того чтобы совершать реальное движение.\n\nВаш день призывает: не позволяй воображаемому величию обесценить твои реальные шаги в виде движения волн. Осознай: туча — это не физическая преграда, а ментальное препятствие, созданное страхом перед собственным потенциалом. Если ты не справляешься с малыми гребнями, ты никогда не сможешь реализовать цель.\n\nКто теряется перед грандиозным, тот теряет и реальный шаг.\n\nСмысл дня: Пассивность перед масштабом — ограничитель действия."),
                    (79, "79", "https://ibb.co/0p1tFtGS", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СОПРОТИВЛЯЙСЯ ПОТОКУ\n\nРиск в том, что малейшее колебание или сопротивление разрушит тандем, превратив обоснованный риск в катастрофу. Вы рискуете быть не героем, а жертвой, если попытаетесь навязать стихии свою схему.\n\nВаш день призывает: не позволяй панике или самоуверенности нарушить ваше равновесие. Осознай: огромная волна не прощает ошибок. Если ты теряешь контроль над своим телом или пытаешься бороться с волной, а не быть ею, ты можешь быть поглощен стихией.\n\nЕдинственное сопротивление потоку — это ты сам.\n\nСмысл дня: Потеря равновесия — ведет к краху."),
                    (80, "80", "https://ibb.co/xrh5vGg", "🔱 ПОСЛАНИЕ ДНЯ: ИСПОЛЬЗУЙ ТАЙНУ ДЛЯ ТРАНСФОРМАЦИИ\n\nРиск в том, чтобы стать завороженным мистической красотой и таинственностью, забыв о действии. Вы рискуете застрять перед волшебным зеркалом, любуясь сказочным отражением, но не совершая перехода.\n\nВаш день призывает: не позволяй чарам ночи стать ловушкой. Осознай: величайшая тайна должна быть использована. Если ты выберешь безопасность буйков, ты упустишь встречу с сакральными знаниями. Твоя задача — взять полученное тайное знание и использовать его для глубинных трансформаций. Не будь просто зрителем ночного волшебства.\n\nТот, кто слишком долго слушает сказки, не успевает написать свою.\n\nСмысл дня: Чрезмерное созерцание — ограничитель перевоплощения."),
                    (81, "81", "https://ibb.co/Y4YshT3J", "🔱 ПОСЛАНИЕ ДНЯ: НЕ УПУСТИ ВОЗМОЖНОСТЬ\n\nРиск в том, чтобы сосредоточиться на сероватых отливах и легкой ряби в виде мелких сомнений, вместо того чтобы действовать в соответствии с открывшимся «Окном возможностей». Вы рискуете упустить момент ясности.\n\nВаш день призывает: не позволяй прошлому или мелким препятствиям заслонить великую возможность. Осознай: облака в небе продолжают двигаться и могут вновь закрыть окно возможностей. Если ты слишком долго будешь размышлять о легкой ряби, прорыв исчезнет, и ты вернешься к прежним поискам.\n\nТот, кто медлит, когда небо открыто, остается к темноте.\n\nСмысл дня: Промедление — закрывает доступ к открывшимся возможностям."),
                    (82, "82", "https://ibb.co/yn7dLJRN", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ЗАВИСАЙ\n\nРиск в том, что ты превращаешь добровольное «зависание» в пассивную жертву, теряя баланс и забывая о цели этого действия. Если ты не используешь момент перевернутого взгляда, ты останешься просто силуэтом, лишенным энергии.\n\nВаш день призывает: не позволяй остановке превратиться в оковы. Если ты не совершаешь акт очищения, равновесие превращается в застой. Ты рискуешь стать неподвижной тенью на фоне угасающего огня, не имея сил для следующего шага.\n\nЗависание без цели — это добровольный плен.\n\nСмысл дня: Застой в паузе — ограничитель нового движения."),
                    (83, "83", "https://ibb.co/Hf5TF5J2", "🔱 ПОСЛАНИЕ ДНЯ: НЕ БУДЬ ЖЕРТВОЙ\n\nРиск в том, чтобы позволить огромной серо-черной туче подавить твою волю. Опасность не только в приближении беды, но и в потере веры в возможность маневра.\n\nВаш день призывает: не поддавайся панике и чувству безысходности. Осознай: если ты позволишь мраку тучи стать твоим внутренним состоянием, ты перестанешь видеть узкий просвет надежды и ясности. Беспокойное море превратится в хаос, а ты — в жертву, которая ждет, когда давление сокрушит ее.\n\nТот, кто смотрит на тучу, перестает видеть цель.\n\nСмысл дня: Паника не дает видеть свет возможностей."),
                    (84, "84", "https://ibb.co/Zz9jsQCV", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПОДАВЛЯЙ ИГРУ\n\nРиск в том, чтобы воспринять шаловливую волну как угрозу твоему строгому порядку, оттолкнув зов Внутреннего Ребенка. Вы рискуете отвергнуть чистый дар вдохновения, потому что он кажется несерьезным или неуместным.\n\nВаш день призывает: не позволяй стремлению к идеальному спокойствию заглушить жизненную силу. Осознай: если ты заблокируешь эту игривую часть себя, штиль превратится в безжизненный застой. Твоя задача — не контролировать совершенство, а быть открытым для его легких нарушений, иначе стабильность станет тюрьмой, лишенной вдохновения.\n\nТот, кто боится спонтанности, теряет смысл жизни.\n\nСмысл дня: Подавление игры — ограничитель жизненной силы."),
                    (85, "85", "https://ibb.co/C5dR6cnN", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ОТСТУПАЙ ПЕРЕД ЦЕНОЙ\n\nРиск в том, что ты испугаешься цены, которую требует великая ЛЮБОВЬ. Ты рискуешь не совершить финальное, очищающее усилие и остаться пленником темного, беспокойного моря.\n\nВаш день призывает: не позволяй страху перед полной отдачей остановить тебя. Осознай: если ты не используешь силу волны для своего превращения в пену, ты потеряешь возможность обрести любовь. Ты будешь вечно метаться на поверхности, не решившись на главный акт любви, ведущий к истинной свободе.\n\nТот, кто боится отдать все, не обретет ничего.\n\nмысл дня: Страх перед самоотдачей — отдаляет от возможности любить."),
                    (86, "86", "https://ibb.co/8n5d6bLC", "🔱 ПОСЛАНИЕ ДНЯ: ВЫДЕРЖИВАЙ ПРАВДУ\n\nРиск в том, что столкновение с истиной становится не очищением, а травмой. Ты рискуешь быть ранен этой правдой, когда розовые очки разбиваются стеклами во внутрь.\n\nВаш день призывает: не позволяй шоку от разрушенных иллюзий парализовать тебя. Осознай: если ты будешь фиксироваться только на боли, ты потеряешь из виду просвет неба и путеводную чайку. Твоя задача — не прятаться от истины, но и не дать ей стать саморазрушением, иначе ты упустишь возможность преобразить этот хаос.\n\nТот, кто смотрит на осколки, не видит горизонта.\n\nСмысл дня: Избегание истины погружает в иллюзии и парализует движение."),
                    (87, "87", "https://ibb.co/xqr6QynP", "🔱 ПОСЛАНИЕ ДНЯ: НЕ ПРЯЧЬ СВОЙ СВЕТ\n\nРиск в том, чтобы испугаться своей собственной мощи и яркого света, который ты несешь. Ты рискуешь вернуться в волны, стремясь слиться с фоном, вместо того чтобы принять свою уникальность, рожденную в пене.\n\nВаш день призывает: не позволяй скромности или страху затмить твое сияние. Осознай: если ты не примешь свой внутренний свет, который рвется наружу -огненный закат превратится в просто уходящий день, а ты — в обычную фигуру в волнах. Твоя задача — выйти из пены, показать свой свет миру и не возвращаться в состояние «до» перерождения.\n\nТот, кто боится сиять, остается в тени волн.\n\nСмысл дня: Избегание уникальности — несет в себе риск раствориться в пене."),
                    (88, "88", "https://ibb.co/wZZcDHNF", "🔱 ПОСЛАНИЕ ДНЯ: СОХРАНИ СЕБЯ\n\nРиск в том, чтобы быть поглощенным мраком и хаосом стихии, поддавшись панике и безволию. Ты рискуешь попытаться контролировать то, что не поддается контролю, истощая свою силу.\n\nВаш день призывает: не позволяй страху парализовать волю. Осознай: если ты фокусируешься только на темноте и пене, ты утратишь способность к ясности мысли. Твоя задача — отказаться от безнадежной борьбы с ветряными мельницами, иначе ты утонешь в бесконечном пенном хаосе.\n\nТот, кто пытается контролировать бурю, теряет свою силу.\n\nСмысл дня: Не пытайся контролировать стихию, чтобы сохранить инстинкт выживания."),
                    (89, "1", "https://ibb.co/9kNFQCZr", "🔱 **ПОСЛАНИЕ ДНЯ: СОХРАНИ ФОКУС ВНИМАНИЯ**\n\nМогучие стены, которые когда-то служили защитой, теперь стали фундаментом для вашего развития. Подобно маяку, который видит берег и бурю, но остается непоколебим, вы призваны к ясности.\n\nВаш день призывает:используйте свою внутреннюю стабильность как точку опоры. Сконцентрируйтесь на луче солнца на воде. Только при четком фокусе открываются истинные возможности.\n\n**Стабильность не тормозит, она позволяет видеть дальше.**\n\n**Смысл дня:** Ваша защита — ваша лучшая точка обзора."),
                    (90, "2", "https://ibb.co/qM5FTdLy", "🔱 **ПОСЛАНИЕ ДНЯ: СМОТРИ В СУТЬ**\n\nВ греческих мифах боги часто посылали знаки в обличье птиц. Ваша белая фигура — это символ ясности и чистоты цели на темном фоне. Вокруг может быть шторм, но ваше видение остается кристальным.\n\n**Ваш день призывает:** превратите неблагоприятный фон в преимущество. На темном фоне ваша цель видна лучше всего. Используйте контраст, чтобы четко увидеть свое направление и сделать точный, одиночный шаг.\n\n**Всякое одиночество — это возможность стать самому себе лучшим компасом.**\n\n**Смысл дня:** Ясность взгляда — ваша главная возможность."),
                    (91, "3", "https://ibb.co/VWTgcJFT", "🔱 **ПОСЛАНИЕ ДНЯ: СОВЕРШИ ПРОРЫВ**\n\nВ древности внезапная птица в ясном небе считалась прямым знаком от Зевса.\n\n**Ваш день призывает:** используйте внезапность. Сегодня ваша возможность — это спонтанное движение, которое нарушает привычный порядок. Не прячьтесь под соломенной крышей рутины. Взлетите над установленными границами, как эта птица, чтобы увидеть новые горизонты. Именно в неожиданном шаге скрыт ваш прорыв.\n\n**Свобода не ждет разрешения, она просто взлетает.**\n\n**Смысл дня:** Спонтанность открывает новые пути."),
                    (92, "4", "https://ibb.co/Txmm7Hv4", '🔱 **ПОСЛАНИЕ ДНЯ: ПРИМИ СВОЮ СИЛУ**\n\nДаже Горгона в своей пугающей форме обладала даром: её кровь могла воскрешать или исцелять.\n\n**Ваш день призывает:** посмотрите на свою боль как на источник уникальной силы. Найдите в своем сложном опыте тот необычный дар, который получили только вы. Примите свою "иную" форму. Ваша уникальность, даже если она кажется странной, может стать вашим самым мощным оружием или целительным бальзамом.\n\n**Под самой неприглядной внешностью может скрываться великая сила преображения.**\n\n**Смысл дня:** Ваш прошлый опыт может стать вашим даром.'),
                    (93, "5", "https://ibb.co/TMFJLYb6", "🔱 **ПОСЛАНИЕ ДНЯ: СМОТРИ ВПЕРЕД**\n\nКаждое утро Бог Солнца Аполлон в своей золотой колеснице приносит миру обновление и силу. Включите свой внутренний свет. Источник энергии и ясности находится прямо на линии вашего горизонта.\n\n**Ваш день призывает:** смотрите вперед, не оглядываясь на тени. Обновление — это не дар, а ваше право. Используйте эту мощную энергию, чтобы сжечь сомнения и начать движение по новому, освещенному пути.\n\n**Когда свет сияет, тени исчезают.**\n\n**Смысл дня:** Ваша энергия сегодня безгранична."),
                    (94, "6", "https://ibb.co/tpHpZ7L1", "🔱 **ПОСЛАНИЕ ДНЯ: ТРАНСФОРМИРУЙ ЭНЕРГИЮ**\n\nГерои древности знали: чем сильнее натиск волны, тем четче виден твой собственный берег. Волнорез — это не преграда, а ваша точка роста, которая преобразует энергию хаоса в чистую силу.\n\n**Ваш день призывает:** используйте сегодняшнее давление как катализатор. Вместо того чтобы разрушаться, встретьте кризис с осознанием. Примите грозовые тучи как фон, который делает ваши границы и вашу цель максимально видимыми.\n\n**Свет всегда приходит из-за самой темной тучи.**\n\n**Смысл дня:** Преобразование энергии кризиса — это ваша возможность."),
                    (95, "7", "https://ibb.co/mCb9mtqK", "🔱 **ПОСЛАНИЕ ДНЯ: ДЕЙСТВУЙ УВЕРЕННО**\n\nБог света и гармонии Аполлон посылает вам знак: ваш путь сегодня будет освещен. Золотая дорожка на воде — это не случайность, а прямое указание на то, что вы находитесь в потоке гармонии со своей целью.\n\n**Ваш день призывает:** используйте это состояние благодати для активного движения. Доверьтесь красоте, которую видите, и ступайте по свету. Насладитесь этим моментом, потому что он дарит ресурс и ясность для всех следующих шагов.\n\n**Гармония — это не цель, а идеальный инструмент для движения.**\n\n**Смысл дня:** Ваш путь освещен. Действуйте с уверенностью."),
                    (96, "8", "https://ibb.co/gMdyCVSW", "🔱 **ПОСЛАНИЕ ДНЯ: ДОВЕРЬСЯ ПОТОКУ**\n\nМорские нимфы, Нереиды, всегда знали: чтобы достичь берега, нужно довериться волне. Ваша сила не в борьбе, а в гибкости и принятии своего пути.\n\n**Ваш день призывает:** отпустите контроль и позвольте потоку направить вас. Всякая уязвимость — это лишь готовность к преображению. Примите свою текущую форму и двигайтесь легко.\n\n**Самые глубокие изменения происходят в моменты покоя и принятия.**\n\n**Смысл дня:** Всякий поток ведет меня к моей цели."),
                    (97, "9", "https://ibb.co/F4gvstXF", "🔱 **ПОСЛАНИЕ ДНЯ: СФОКУСИРУЙСЯ НА ЦЕЛИ**\n\nГерои древности знали: истинное мастерство — в создании инструмента из препятствия. Даже решетка может стать инструментом, а не тюрьмой. Каменная стена — это то, что отвлекает от главного.\n\n**Ваш день призывает:** используйте сегодняшние ограничения для самодисциплины и концентрации. Откажитесь от борьбы со стеной. Проявите снайперскую точность и направьте всю свою энергию на единственную цель, которую вы видите в проеме.\n\n**Только точное направление освобождает от необходимости блуждать.**\n\n**Смысл дня:** Ясность цели — ваша главная сила."),
                    (98, "10", "https://ibb.co/0pJ4Tcdq", "🔱 **ПОСЛАНИЕ ДНЯ: СОЗДАВАЙ ИЗ ХАОСА**\n\nСогласно легендам, богиня любви Афродита родилась из морской пены. Хаос, который вы видите, — это не помеха, а созидательная энергия.\n\n**Ваш день призывает:** используйте сегодняшнюю энергию не для борьбы, а для активного созидания. Примите нестабильность как плодородную почву. Превратите хаос в мощный толчок для начала проекта или решительного шага. Ваша красота и сила рождаются в этот момент.\n\n**Самые прекрасные вещи рождаются в самых бурных местах.**\n\n**Смысл дня:** Энергия хаоса — ваш ресурс для творчества."),
                    (99, "11", "https://ibb.co/Pv93KM2T", "🔱 ПОСЛАНИЕ ДНЯ: СЛЕДУЙ ЗА ИНТУИЦИЕЙ\n\nВ греческой мифологии облака — это знаки и послания, которые принимают форму божеств и героев. Ваш путь ясен, и сегодня небо посылает вам подсказку.\n\nВаш день призывает: используйте ясность неба, чтобы прочитать знаки. Поднимите взгляд выше горизонта. Не ищите знаков в бурлении прибоя, ищите их в высоте. Ваше видение сегодня должно быть чистым, как синий небосвод. Сконцентрируйтесь на том, что формируется вверху, и смело действуйте согласно этому предзнаменованию.\n\nЯсность неба — ваш лучший компас.\n\nСмысл дня: Интуиция и знаки ведут Вас к цели."),
                    (100, "12", "https://ibb.co/4RYP2rc0", "🔱 ПОСЛАНИЕ ДНЯ: СМОТРИ В ГЛУБИНУ\n\nКак в мифах, где провидец мог видеть сквозь воду, ваша задача сегодня — проявить абсолютную ясность. Прозрачность поверхности позволяет увидеть глубину.\n\nВаш день призывает: используйте кристальную ясность момента, чтобы увидеть истину. Не бойтесь заглянуть в самый низ, потому что там нет скрытых угроз — только факты. Именно эта чистота видения дает вам непоколебимую уверенность и ресурс для действий. Доверяйте тому, что видите под поверхностью.\n\nЧем прозрачнее взгляд, тем глубже знание.\n\nСмысл дня: Внутренняя ясность — Ваш главный ресурс."),
                    (101, "13", "https://ibb.co/RkfHshYQ", "🔱 ПОСЛАНИЕ ДНЯ: БУДЬ НЕПОКОЛИБИМЫМ\n\nСкалистый утес — символ абсолютной стойкости, который противостоит тысячелетним штормам. В моменты натиска вы призваны быть несокрушимой скалой.\n\nВаш день призывает: используйте свою внутреннюю мощь, чтобы противостоять внешней стихии. Не бойтесь быть твердым. Ваша задача сегодня — не двигаться с места, не поддаваться червяку сомнений и не уступать давлению. Используйте свою непоколебимость как маяк, который сам не двигается, но указывает путь другим.\n\nТолько то, что не гнется, может выдержать натиск.\n\nСмысл дня: Внутренняя стойкость — источник Вашей силы."),
                    (102, "14", "https://ibb.co/v6Scjr9s", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ЭМОЦИЮ\n\nВсякий шторм — это высвобождение огромной, чистой энергии, которую можно использовать. Подобно тому, как волнорез преобразует силу удара в брызги, вы призваны трансформировать внутреннее напряжение в действие.\n\nВаш день призывает: используйте сегодняшнее напряжение как топливо, а не как разрушение. Не бойтесь темного неба и мощных волн. Именно эта энергия, которую вы чувствуете, является ключом к прорыву. Позвольте эмоциям выйти, но не дайте им увлечь вас. Превратите свой внутренний кризис в мощный толчок для решительного шага.\n\nСамые сильные прорывы совершаются в самый сильный шторм.\n\nСмысл дня: Энергия кризиса — ваша движущая сила."),
                    (103, "15", "https://ibb.co/3mQmzZV0", "🔱 ПОСЛАНИЕ ДНЯ: СЛУШАЙ ТИШИНУ\n\nЦапля — символ высшей сосредоточенности и терпения. Подобно герою, который ждет знака, вы призваны использовать свое одиночество и тишину как инструмент для точного действия.\n\nВаш день призывает: используйте паузу перед шагом, чтобы достичь цели. Ваша сила сегодня не в активности, а в абсолютной, снайперской концентрации. Не тратьте энергию на мелкие движения. Всякая добыча приходит к тому, кто умеет ждать без суеты.\n\nТишина — самое громкое предзнаменование успеха.\n\nСмысл дня: Концентрация обеспечивает точность Вашего шага."),
                    (104, "16", "https://ibb.co/G423fK2p", '🔱 ПОСЛАНИЕ ДНЯ: СТАНЬ АДАПТИВНЫМ\n\nМуть и буря — это знак крайних, но временных перемен, которые требуют высшей адаптивности. Подобно Протею, морскому богу, который мог принимать любую форму, вы призваны быть гибким.\n\nВаш день призывает:используйте хаос для проверки своей внутренней силы. Не бойтесь того, что все вокруг кажется "грязным" или неправильным. Эта мутная вода — признак мощного потока, который переносит вас через старые границы. Ваша задача — не бороться с волнами, а двигаться вместе с ними, пока не достигнете чистого горизонта.\n\nСамый сильный не тот, кто стоит, а тот, кто умеет течь.\n\nСмысл дня: Адаптивность — источник Вашей неуязвимости.'),
                    (105, "17", "https://ibb.co/DD8P7Ppn", "🔱 ПОСЛАНИЕ ДНЯ: ОБРЕТИ ТИШИНУ\n\nЭтот стул — ваше место, где в абсолютной тишине открывается бесконечный горизонт. Вы призваны очистить свой внутренний холст, чтобы увидеть картину, освещенную светом Аполлона.\n\nВаш день призывает:используйте уединение, чтобы услышать безмолвный ответ. Не бойтесь этого покоя. Всякий шум рассеивает силу, но тишина собирает ее воедино. Созерцайте бесконечность моря, зная, что ваша задача сегодня — не активно действовать, а обрести совершенную ясность и умиротворение перед началом пути.\n\nГде покой, там и пророчество.\n\nСмысл дня: Внутренняя тишина — источник высшего знания."),
                    (106, "18", "https://ibb.co/ym2hhGDy", "🔱 ПОСЛАНИЕ ДНЯ: ПОЧУВСТВУЙ СВОЮ ОПОРУ\n\nВаша задача — собрать и выстроить свою жизнь по принципу «кирпич к кирпичу». Вы призваны создать устойчивость не силой, а точностью каждого шага.\n\nВаш день призывает: используйте последовательность и точность, чтобы создать устойчивую опору. Ваша сила сегодня — в методе маленьких шагов. Сосредоточьтесь на каждом действии. Камни прошлого служат фундаментом для вашей стабильности и роста.\n\nТолько то, что растет медленно, может выдержать ветер.\n\nСмысл дня: Ваша сила — в последовательности и равновесии."),
                    (107, "19", "https://ibb.co/VYJmyW7h", "🔱 ПОСЛАНИЕ ДНЯ: ЧУВСТВУЙ СИЛУ\n\nБрызги, рожденные ударом волны о скалу, — это чистая, высвобожденная энергия. Это момент прорыва, когда сила стихии становится ощутимой.\n\nВаш день призывает:используйте энергию конфликта для своего обновления. Не бойтесь ощутить этот мощный поток. Именно брызги — знак того, что процесс идет и старые границы ломаются. Примите эту живую, хаотичную энергию и направьте ее на создание чего-то нового.\n\nЖизнь — это всегда брызги, а не гладь.\n\nСмысл дня:Энергия прорыва — Ваш ресурс для действия."),
                    (108, "20", "https://ibb.co/fYTvNBbq", "🔱 ПОСЛАНИЕ ДНЯ: БЕРИ СВОЕ\n\nВорона — символ острого ума, который точно знает, где находится его ресурс. Правило жизни гласит: «у каждой вороны есть свой кусочек сыра».\n\nВаш день призывает: используйте остроту инстинкта, чтобы увидеть и забрать свое. Ваша сила в том, чтобы не ждать, а действовать. В конкурентной среде побеждает тот, кто быстро заявляет о своих правах. Будьте решительны и не бойтесь взять то, что честно заработано.\n\nРесурс достается тому, кто готов за ним нырнуть.\n\nСмысл дня: Ваша решительность — главный инструмент добычи."),
                    (109, "21", "https://ibb.co/9HrSkJyx", "🔱 ПОСЛАНИЕ ДНЯ: ЧЕРПАЙ ИЗ ПРОШЛОГО\n\nДревняя крепость — символ нерушимого наследия. Рыбак, стоящий на фоне тысячелетних стен, знает, что истинное упорство рождается из великой истории.\n\nВаш день призывает: используйте свой прошлый опыт как нерушимую опору. Ваша сила сегодня — в умении ловить рыбу в тех же водах, что и предки. Не бойтесь старых методов и традиций. Стены крепости не сдерживают, они дают устойчивость, чтобы сосредоточиться на добыче здесь и сейчас.\n\nВеликое прошлое дарит нерушимую опору.\n\nСмысл дня: Ваш опыт — фундамент сегодняшней добычи."),
                    (110, "22", "https://ibb.co/TBTZRnWn", "🔱 ПОСЛАНИЕ ДНЯ: СОЗДАВАЙ ИЗ ХАОСА\n\nСогласно легендам, богиня любви Афродита родилась из морской пены. Хаос, который вы видите, — это не помеха, а созидательная энергия.\n\nВаш день призывает: используйте сегодняшнюю энергию не для борьбы, а для активного созидания. Примите нестабильность как плодородную почву. Превратите хаос в мощный толчок для начала проекта или решительного шага. Ваша красота и сила рождаются в этот момент.\n\nСамые прекрасные вещи рождаются в самых бурных местах.\n\nСмысл дня: Энергия хаоса — ваш ресурс для творчества."),
                    (111, "23", "https://ibb.co/1GvHFqfD", "🔱 ПОСЛАНИЕ ДНЯ: УВИДЬ РАВНОВЕСИЕ\n\nВеликие герои, такие как Аполлон, ценили идеальное сочетание сил.\n\nВаш день призывает: найдите баланс между жестким волнорезом (вашим фундаментом) и гибкой пальмой (вашей адаптивностью). Признайте, что вам нужна и твердость (чтобы стоять на своем), и легкость (чтобы не сломаться). Спокойное море — идеальный фон, чтобы настроить это равновесие внутри себя, сделав его абсолютным.\n\nИдеальная сила — это сочетание гибкости и непоколебимости.\n\nСмысл дня:Равновесие — Ваш самый ценный ресурс."),
                    (112, "24", "https://ibb.co/DH4w7Bk6", "🔱 ПОСЛАНИЕ ДНЯ: ЗАГЛЯНИ В ГЛУБИНУ\n\nВ легендах, самые великие тайны скрыты в тишине и темноте. Используйте спокойствие воды как зеркало своей истинной природы. Блик света — это ваш внутренний маяк, освещающий путь к себе.\n\nВаш день призывает: не бойтесь внутренней тишины и темноты. Именно в этой глубине скрыты ваши самые мощные ответы и ресурсы. Сегодняшняя возможность — получить ясное, неискаженное знание о себе и своем пути.\n\nСамый чистый свет рождается в самой темной воде.\n\nСмысл дня: Истина и сила находятся в глубине Вашей души."),
                    (113, "25", "https://ibb.co/WNhPs7Nh", '🔱 ПОСЛАНИЕ ДНЯ: СМОТРИ В ЗЕРКАЛО ДУШИ\n\nТихая, гладкая вода — это идеальное зеркало вашей души. Сегодня вы призваны увидеть себя целиком, включая теневые аспекты, с абсолютной ясностью.\n\nВаш день призывает: используйте идеальный покой для обретения внутренней истины. Ваша сила — в чистом, неискаженном отражении. Вода, как «парное молоко» дарит полное расслабление и позволяет увидеть идеальный баланс жизни. Воспользуйтесь этой "тишиной на душе", чтобы принять себя без осуждения.\n\nИстина рождается из покоя в душе.\n\nСмысл дня: Внутренняя тишина открывает истинное отражение.'),
                    (114, "26", "https://ibb.co/bgWhYXsY", "🔱 ПОСЛАНИЕ ДНЯ: СЛЕДУЙ ЗА СИЛОЙ\n\nМощная волна — это чистая, неотвратимая энергия Посейдона. Вы призваны не бороться с этой силой, а использовать ее для достижения цели, даже если она скрыта в дымке.\n\nВаш день призывает: используйте мощь внутреннего движения для прорыва. Ваша сила — в способности принять хаос и направить его. Не ждите, пока волна утихнет; ловите ее и плывите. Сегодняшняя сила — это ваши эмоции, которые, будучи приняты, станут источником невероятного ресурса.\n\nСамый сильный не борется, а направляет волну.\n\nСмысл дня: Эмоциональная сила — Ваш главный ресурс."),
                    (115, "27", "https://ibb.co/0VQV5Vvs", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ БЛАГОДАТЬ\n\nЭтот луч — луч солнца золотого, символ чистой, ничем не заслуженной благодати Аполлона. Он пробивается сквозь тьму, неся любовь, красоту и надежду именно туда, где это нужнее всего.\n\nВаш день призывает:используйте внезапную, теплую поддержку небес. Ваша сила — в принятии этой нежности и света. Не ищите логики в подарке судьбы; просто используйте этот золотой луч, чтобы осветить свои следующие шаги. Сегодня вселенная дарит вам мощный, чистый ресурс.\n\nСвет приходит туда, где больше всего нужна надежда.\n\nСмысл дня: Примите поддержку от этого дня."),
                    (116, "28", "https://ibb.co/Ng9kMzzd", "🔱 ПОСЛАНИЕ ДНЯ: ДЕЙСТВУЙ СМЕЛО\n\nПарусник — символ непоколебимой веры в свой курс. Подобно Одиссею, вы призваны плыть к своей цели, используя попутный ветер и доверяя выбранному пути.\n\nВаш день призывает: используйте текущие возможности для ускорения движения. Ваша сила — в способности видеть и использовать внешние силы (ветер) для своего прогресса. Смело отходите от берега, где нет роста. Цель достижима только тогда, когда вы полностью отдаете себя движению.\n\nТот, кто не рискует, не видит новых земель.\n\nСмысл дня:Вера в себя — парус с попутным ветром."),
                    (117, "29", "https://ibb.co/chsgHSYx", "🔱 ПОСЛАНИЕ ДНЯ: СЛЕДУЙ ЗА ИНТУИЦИЕЙ\n\nГлубокая ночь и мощная волна подчинены Луне, которая управляет приливами и отливами вашего настроения. Лунная дорожка — это ваш единственный, интуитивный путь сквозь темноту.\n\nВаш день призывает: используйте интуитивное знание, чтобы обуздать свою силу. Ваша сила — в согласии с внутренними приливами. Не отвлекайтесь на бушующую волну; сфокусируйтесь на светящейся линии, которая ведет сквозь тьму. Интуиция сильнее любой стихии.\n\nТолько тот, кто видит свет, может обуздать волну.\n\nСмысл дня: Интуиция — главный ресурс в темноте."),
                    (118, "30", "https://ibb.co/20Lx5YfJ", "🔱 ПОСЛАНИЕ ДНЯ: ЧУВСТВУЙ ТОНКО\n\nКружевные облака — символ нежности и идеальной гармонии. Подобно Нереидам, плетущим тончайшие узоры, вы призваны увидеть красоту в хрупкости и мимолетности момента.\n\nВаш день призывает: используйте высокую чувствительность для создания красоты. Ваша сила — в умении проявлять бережность к себе и миру. Не требуйте от себя жесткости; сегодня побеждает тот, кто действует тонко и мягко. Находите ресурс в красоте, которая скоро исчезнет.\n\nСамая большая сила всегда скрыта в нежности.\n\nСмысл дня:Чувствительность — источник Вашей силы."),
                    (119, "31", "https://ibb.co/LDPy6dVt", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ТАЙНУ\n\nСумерки — это магический час Гермеса, когда старый путь уходит, а новый еще не наступил. Вы призваны действовать, доверяя тайне момента и своей внутренней силе.\n\nВаш день призывает: используйте эту переходную точку для самого глубокого планирования. Ваша сила — в способности видеть в полумраке. Всякая внешняя ясность сегодня будет ложной; истинный ресурс в доверии своей интуиции, которая обостряется на границе дня и ночи.\n\nТолько в сумерках видны звезды.\n\nСмысл дня:Интуиция — главный ресурс движения."),
                    (120, "32", "https://ibb.co/k2VfwNrF", "🔱 ПОСЛАНИЕ ДНЯ: СЛУШАЙ ТАЙНУ\n\nНочь и акустическое эхо позволяют услышать то, что заглушает дневной свет: голос вашей истинной, скрытой сути. Вы призваны найти вход в это темное, невидимое знание.\n\nВаш день призывает: используйте тишину, чтобы найти свой тайный ответ. Ваша сила — в способности погрузиться в эту тьму. Ответ, который вы ищете, скрыт глубоко, в резонансе ваших внутренних стен. Не бойтесь зайти туда, где тихо, чтобы услышать свой единственный, верный путь.\n\nИстинная мудрость приходит в полной тишине.\n\nСмысл дня: Скрытый голос — Ваш надежный компас."),
                    (121, "33", "https://ibb.co/Jwrc8PvP", "🔱 ПОСЛАНИЕ ДНЯ: ПОЧУВСТВУЙ ОПОРУ\n\nНа фоне грандиозного заката, камень перед волнами — это символ вашего неизменного фундамента. Стихия вокруг лишь подчеркивает вашу способность выстоять перед завершением цикла.\n\nВаш день призывает: используйте свою непоколебимую стабильность как якорь. Ваша сила — в осознании собственной прочности. Смотрите на волны и яркий свет с позиции силы, зная, что ваша основа нерушима. Неподвижность позволяет увидеть величие всего цикла, не участвуя в его хаосе.\n\nСамая большая сила в том, чтобы оставаться собой.\n\nСмысл дня: Нерушимость — Ваш главный ресурс в пути."),
                    (122, "34", "https://ibb.co/3mwSy8wM", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ПРЕДУПРЕЖДЕНИЕ\n\nБольшая туча, нависшая над морем, — это явное предупреждение. Вы призваны использовать оставшееся время спокойствия для подготовки и внутренней мобилизации.\n\nВаш день призывает: используйте тревогу как мощный стимул для действия. Ваша сила — в способности видеть надвигающуюся опасность и действовать на опережение. Не закрывайте глаза на грозу. Знание о том, что грядет буря, позволяет вам войти в нее во всеоружии.\n\nБуря, которую видишь издалека, теряет свою силу.\n\nСмысл дня: Бдительность — главный ресурс для защиты."),
                    (123, "35", "https://ibb.co/b5bfH5gk", "🔱 ПОСЛАНИЕ ДНЯ: СМОТРИ В ГЛУБИНУ\n\nПрозрачное море, где видно дно, — это абсолютная ясность истины. Вы призваны смотреть вглубь своих проблем, зная, что все факты (камни) лежат на поверхности.\n\nВаш день призывает: используйте идеальное спокойствие для принятия четких решений. Ваша сила — в чистом видении. Облака, выстроенные в ряд, показывают, что все части вашей жизни сейчас могут быть упорядочены. Действуйте, опираясь на полную картину.\n\nИстинная ясность всегда приносит покой.\n\nСмысл дня: Ясность и истина — Ваш главный ресурс."),
                    (124, "36", "https://ibb.co/HLKrDtHJ", "🔱 ПОСЛАНИЕ ДНЯ: НЕСИ СВОЙ ОГОНЬ\n\nЭто момент, когда внешнего света нет, и спасение зависит только от внутреннего огня. Вы призваны стать своим собственным Прометеем: найти свет, силу и смысл внутри себя, чтобы выстоять в шторме.\n\nВаш день призывает: используйте кризис для обретения абсолютной внутренней силы. Ваша сила — в мужестве принять полную тьму и действовать. Не ищите помощи извне; сейчас вы должны опираться только на свою волю. Шторм проверяет, насколько прочен ваш собственный стержень.\n\nСамый яркий свет — это тот, что несет сам человек.\n\nСмысл дня: Сила воли — Ваш главный ресурс."),
                    (125, "37", "https://ibb.co/zVgkWXDb", "🔱 ПОСЛАНИЕ ДНЯ: ЧЕРПАЙ ИЗ ПРОШЛОГО\n\nДревние стены крепости — это символ накопленной силы, защиты и мудрости прошлых поколений. Вы призваны использовать этот опыт как нерушимую основу для своих действий.\n\nВаш день призывает: используйте свой опыт и границы как точку опоры. Ваша сила — в осознании, что вы стоите на плечах истории. Не бойтесь моря (вызовов); стены (ваши принципы) надежно защищают вас. Границы — это не клетка, а фундамент, с которого вы можете смотреть на горизонт.\n\nСила всегда рождается из древнего корня.\n\nСмысл дня: Опыт — главный ресурс для победы."),
                    (126, "38", "https://ibb.co/G35YqJRN", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ СВОЮ ДВОЙСТВЕННОСТЬ\n\nЦапля и Ворон, стоящие на камнях, — это совершенный баланс света и тени, интуиции и мудрости. Вы призваны объединить свои противоположные качества для достижения целостной силы.\n\nВаш день призывает: используйте свои конфликтующие части для более глубокого видения. Ваша сила — в осознании, что вы не должны быть только белым или только черным. Примите свое двойственное начало. Только когда обе стороны (Цапля и Ворон) сфокусированы, вы можете увидеть корабль (цель) на горизонте.\n\nИстинная мудрость рождается на границе света и тени.\n\nСмысл дня: Ваша задача — принять себя любым."),
                    (127, "39", "https://ibb.co/21KqZx8N", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ОБНОВЛЕНИЕ\n\nЧистое небо и энергия волн у берега — это знак абсолютного очищения. Вы призваны войти в эту свежую волну и позволить ей смыть всё ненужное. Пена — это символ зарождения новой, чистой красоты.\n\nВаш день призывает: используйте энергию обновления для смелого старта. Ваша сила — в ясности видения (небо) и силе движения (волна). Сейчас нет сдерживающих факторов, нет туч и теней. Действуйте легко, как волна, зная, что всё, что вам нужно, уже очищено.\n\nЖизнь, рожденная из пены, не знает тяжести.\n\nСмысл дня: Свобода — главный ресурс для старта."),
                    (128, "40", "https://ibb.co/spsNjd2v", "🔱 ПОСЛАНИЕ ДНЯ: ДОВЕРЯЙ ПОТОКУ\n\nРека, собравшаяся у моря, символизирует кульминацию долгого пути и момент, когда все ваши усилия готовы слиться с бесконечным потоком жизни. Вы призваны принять это слияние как абсолютное завершение и обогащение.\n\nВаш день призывает:используйте ясность момента для объединения внутренних сил. Ваша сила — в способности отпустить контроль и позволить двум разным энергиям (река и море) стать одной. Небо над вами чистое, что дает четкое видение того, какой мощью вы обладаете, когда перестаете бороться с неизбежным.\n\nВсякая река находит свой покой в море.\n\nСмысл дня: Быть в потоке – Ваш главный ресурс."),
                    (129, "41", "https://ibb.co/Q3MgxCXS", "🔱 ПОСЛАНИЕ ДНЯ: БУДЬ НЕПОКОЛЕБИМ\n\nБастион, нерушимый перед морем, — это символ стратегической силы и защиты. Вы призваны укрепить свои границы и принципы, сделав их неприступными для внешних атак.\n\nВаш день призывает: используйте свой интеллект для создания надежного фундамента. Ваша сила — в способности создать надежную, долгосрочную структуру, которая выдержит любую волну. Не спешите вступать в открытый бой; сначала оцените свою позицию и убедитесь в прочности своей защиты.\n\nТолько то, что нерушимо, может выстоять вечность.\n\nСмысл дня:Ваши принципы — главный ресурс для победы."),
                    (130, "42", "https://ibb.co/d0mbdKGp", "🔱 ПОСЛАНИЕ ДНЯ: ОСВОБОДИСЬ ОТ ГРУЗА\n\nДва камня символизируют осязаемое бремя, которое вы несете (груз, обида). Море — это трансформирующая сила, готовая поглотить и переварить вашу тяжесть. Вы призваны добровольно отдать прошлое этому потоку.\n\nВаш день призывает: используйте стихию для окончательного освобождения от старого груза. Ваша сила — в осознании, что у вас есть выбор: продолжать нести камни или сбросить их. Пришло время отпустить то, что давит, и дать морю (жизни) провести обряд очищения.\n\nМоре принимает то, что ты не можешь нести.\n\nСмысл дня: Ваша сила в освобождении от груза прошлого."),
                    (131, "43", "https://ibb.co/SDxQCyC6", "🔱 ПОСЛАНИЕ ДНЯ: СМОТРИ ПОД НОГИ\n\nУглубления с водой — это временные зеркала, созданные волной, где можно увидеть неглубокую, но чистую истину. Вы призваны найти знание не в дальней дали, а прямо под ногами, в мелких деталях.\n\nВаш день призывает: используйте эти «воронки» для поиска скрытых смыслов в обыденном. Ваша сила — в способности остановиться и увидеть, что глубина может быть найдена даже в житейских мелочах. Чистое небо над головой гарантирует, что ваше видение остается объективным, пока вы работаете с текущими задачами.\n\nВеликая мудрость часто прячется в мелочах.\n\nСмысл дня: Внимание к деталям — Ваш главный ресурс."),
                    (132, "44", "https://ibb.co/6JmShfmf", "🔱 ПОСЛАНИЕ ДНЯ: СИЛА В ПАРТНЕРСТВЕ\n\nДве лодки, плывущие под чистым небом, символизируют сотрудничество и поддержку. Ваш путь не одинок, а разные ресурсы могут дополнять друг друга, не мешая.\n\nВаш день призывает: используйте идеальную ясность момента для объединения с нужным союзником. Ваша сила — в осознанном взаимодействии. Сегодня важен не спор о скорости, а гармония движения. Это время для открытости и обмена ресурсами.\n\nНа чистом горизонте все пути ведут к цели.\n\nСмысл дня: Партнерство — Ваш главный ресурс."),
                    (133, "45", "https://ibb.co/vvr8vZXc", "🔱 ПОСЛАНИЕ ДНЯ: СМОТРИ ВДАЛЬ\n\nСкамья, обрамленная аркой, — это идеальное место для остановки и созерцания. Вы призваны принять паузу, чтобы увидеть открытый горизонт, просто наблюдая. Созерцание позволяет вам понять полную картину происходящего.\n\nВаш день призывает: используйте спокойствие и защищенность для получения четкого видения. Ваша сила — в способности наблюдать, не реагируя немедленно. Сначала увидьте всю картину, выберите цель, спланируйте маршрут. Это место, где вы находите ответы через тишину и фокус.\n\nИстинное знание приходит в неподвижности.\n\nСмысл дня: Покой перед действием — ключ к успеху."),
                    (134, "46", "https://ibb.co/6JGGPJZx", "🔱 ПОСЛАНИЕ ДНЯ: БУДЬ ХИТРЕЕ\n\nКошка, устроившаяся между камнями у бушующего моря, — это основа выживания. Вы призваны использовать интуицию и гибкость, чтобы найти свою точку равновесия в самой гуще борьбы.\n\nВаш день призывает:используйте стихию для проверки своей внутренней силы и хитрости. Ваша сила — в способности сливаться с окружением, оставаться незаметным и ждать. Буря не может повредить тому, кто принял свою позицию и не сопротивляется очевидному.\n\nСкрытая сила всегда переживает открытую битву.\n\nСмысл дня: Гибкость в борьбе — закон выживания."),
                    (135, "47", "https://ibb.co/d4LJ0xmS", '🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ СВОЙ ОПЫТ\n\nМутная, но сильная река, впадающая в светящееся море, символизирует неизбежность завершения и перехода. Вы призваны принять свои "мутные" (трудные) этапы как необходимую часть пути, ведущую к большому, светлому результату.\n\nВаш день призывает: используйте энергию завершения, чтобы выйти на новый, освещенный путь. Ваша сила — в осознании, что вы уже преодолели всё самое сложное (река), и теперь ваше движение направлено к свету (горизонт). Слияние — это не потеря, а обогащение моря вашей силой.\n\nСамый темный путь ведет к самому яркому свету.\n\nСмысл дня: Преодоление тьмы — рождение силы.'),
                    (136, "48", "https://ibb.co/zH0cCHjV", "🔱 ПОСЛАНИЕ ДНЯ: НАЙДИ СВОЙ СВЕТ\n\nСерый пейзаж, где Солнце — лишь маленькая, но яркая точка, говорит о том, что истинный свет и смысл находятся внутри. Вы призваны обратить внимание на свою малую, но важную работу среди обломков и туч.\n\nВаш день призывает: используйте мрачную атмосферу как идеальный фон для важного, сосредоточенного труда. Ваша сила — в способности находить ценность в сложном, неуютном окружении (работа на камнях). Не ждите яркого солнца; создавайте свое тепло через действие. Это время для сосредоточения и алхимической работы над собой.\n\nСвет, добытый в тени, становится ярче.\n\nСмысл дня: Внутренний огонь — суть преображения."),
                    (137, "49", "https://ibb.co/7tpcS3Wv", "🔱 ПОСЛАНИЕ ДНЯ: ВОЗВЫСЬСЯ НАД ОБСТОЯТЕЛЬСТВАМИ\n\nСмешанное небо говорит о том, что ясность всегда находится над конфликтом. Вы призваны принять высоту птицы, чтобы увидеть свою траекторию, не отвлекаясь на игру света и тени внизу.\n\nВаш день призывает: используйте свой дух для преодоления сомнений и достижения непоколебимой перспективы. Ваша сила — в способности отделиться от эмоционального шума и хаоса. В то время как море и облака борются, ваше движение должно быть одиноким и точным. Выше туч всегда находится чистое синее небо.\n\nВеликая цель требует движения над облаками.\n\nСмысл дня: Чистый взор — высшая свобода."),
                    (138, "50", "https://ibb.co/3YGgV04R", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИТИ СВЕТ ФОНАРЯ\n\nФонарь на фоне уходящего дня — это ваша текущая, сфокусированная истина. Вы призваны ценить и использовать свой свет (внутренний фокус), который освещает ваш путь, даже когда великий, природный свет (закат) уходит.\n\nВаш день призывает: используйте защищенность момента для сосредоточения на самом важном, что находится в вашей власти. Ваша сила — в способности найти центр и точку опоры в переходный период (между светом и тьмой). Скамьи для отдыха и ограда для защиты говорят о том, что сейчас время активного покоя и подготовки к ночи.\n\nМалый свет, который ты несешь, всегда важнее заката.\n\nСмысл дня: Фокус на себе — гарантия успеха."),
                    (139, "51", "https://ibb.co/v4CVn7qg", "🔱 ПОСЛАНИЕ ДНЯ: ПОКАЖИ СВОЙ ЦВЕТ\n\nСкала, освещенная необычным светом, символизирует необходимость заявить о своей уникальной, внутренней силе. Вы призваны не прятаться, а использовать всю свою мощь и незыблемость, чтобы стать ориентиром в наступающей тьме.\n\nВаш день призывает:используйте свою уверенность и неподвижность, чтобы стать самым ярким объектом в пейзаже. Ваша сила — в осознанном принятии своего масштаба и своей непохожести (синий/фиолетовый свет). Ночь не может поглотить то, что светится изнутри.\n\nТот, кто светится, не боится темноты.\n\nСмысл дня: Внутренняя сила — путь к сиянию."),
                    (140, "52", "https://ibb.co/JwvqYPDC", "🔱 ПОСЛАНИЕ ДНЯ: ДРУЖИ С ХАОСОМ\n\nЧайки, пролетающие над бушующей, мутной водой, символизируют использование хаоса для достижения цели. Вы призваны не избегать стихии, а найти в ней энергию и скорость, необходимую для продвижения.\n\nВаш день призывает: используйте текущее смятение как идеальное время для решительного и смелого действия. Ваша сила — в осознанном риске и ловкости. Только в этой буре можно найти ту добычу, которая недоступна в штиль. Смешение воды с грязью дает маскировку и шанс для внезапного броска.\n\nСильнейшая воля рождается в буре.\n\nСмысл дня: Мутная вода — ключ к добыче."),
                    (141, "53", "https://ibb.co/RpP2Lmb3", "🔱 ПОСЛАНИЕ ДНЯ: ДЕЛАЙ ЗАПАСЫ\n\nУглубления в дне, полные темной воды, символизируют сохранение сути и накопление опыта в циклично меняющейся среде. Вы призваны обратить внимание на те внутренние резервы, которые не зависят от текущего прилива.\n\nВаш день призывает:используйте момент для погружения в глубину и для оценки своих накопленных ресурсов, даже если они кажутся скрытыми. Ваша сила — в способности удерживать влагу и жизнь (воду) в хаосе движения. Эти углубления питают то, что не может выжить в момент отлива. Успех приходит к тому, кто умеет создавать и хранить.\n\nТот, кто хранит в себе колодец, не боится засухи.\n\nСмысл дня: Внутренняя влага — путь к стойкости."),
                    (142, "54", "https://ibb.co/5hn4WXf6", "🔱 ПОСЛАНИЕ ДНЯ: НЕ СТОЙ НА МЕСТЕ\n\nНебо с облаками, волна и решетка — вся сцена находится в динамике. Вы призваны использовать движение облаков и волн как знак того, что никакие преграды и никакие эмоции не вечны.\n\nВаш день призывает: используйте текущие перемены как возможность для продвижения. Ни одна проблема не стоит на месте. Ваша сила — в осознании, что прогресс возможен, даже если он идет за облаками. Научитесь читать знак перемен на небе, чтобы понять, что скоро ваше видение станет чище и шире.\n\nКаждое облако несет в себе дождь или солнце.\n\nСмысл дня:Постоянство — в смене циклов."),
                    (143, "55", "https://ibb.co/MDnBy1HS", "🔱 ПОСЛАНИЕ ДНЯ: ПОЙМАЙ СВОЙ РИТМ\n\nИстинная сила — в единстве с движением. Подобно всаднику, который чувствует дыхание и шаг своего коня, вы призваны к полной синхронизации с вашим окружением и партнерами.\n\nВаш день призывает:доверьтесь ритму вашего пути. Не форсируйте события, но и не замедляйтесь без необходимости. Найдите идеальный темп, в котором ваша энергия и энергия цели совпадают. Ваша цель близка, если вы движетесь в согласии с собой и миром.\n\nСкорость без ритма — это хаос.\n\nСмысл дня: Синхронность с процессом — источник неуязвимости."),
                    (144, "56", "https://ibb.co/p6XzxgFv", "🔱 ПОСЛАНИЕ ДНЯ: ИСПОЛЬЗУЙ ПЕРСПЕКТИВУ\n\nБерег — это не конец пути, а лучшая точка обзора перед погружением в стихию. Подобно путешественнику, который отдыхает под тенью пальмы, чтобы ясно увидеть свой маршрут через море, вы призваны к осознанному переходу.\n\nВаш день призывает: не спешите. Используйте устойчивость набережной и вид с пирса, чтобы оценить весь масштаб предстоящих действий. Ваша сила — в способности видеть границу между покоем и движением и делать выбор, обладая всей информацией.\n\nТот, кто стоит на твердой земле, видит все перспективы.\n\nСмысл дня: Готовность к переходу — источник силы."),
                    (145, "57", "https://ibb.co/dwFFTwsy", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ДИНАМИКУ\n\nВаша сила — в способности использовать непрерывную энергию момента. Подобно волне, которая, не останавливаясь, несет в себе силу и достигает берега, вы призваны к постоянной, но плавной активности.\n\nВаш день призывает: сфокусируйтесь на процессе, а не на результате. Каждое текущее усилие — это часть мощного потока, который приближает вас к далекой цели (кораблям). Не бойтесь текущих трудностей, поскольку они — часть динамики, ведущей вперед.\n\nПуть к горизонту начинается с ближайшей волны.\n\nСмысл дня: Динамичность — источник неизбежного прогресса."),
                    (146, "58", "https://ibb.co/1t5jLjPh", "🔱 ПОСЛАНИЕ ДНЯ: ЖДИ МОМЕНТА\n\nВаша сила — в осознанной паузе и исключительной точности. Подобно цапле, которая стоит неподвижно между двух стихий, невидимая в тумане, но готовая к мгновенному действию, вы призваны к максимальной концентрации.\n\nВаш день призывает: используйте неясность (туман) как вуаль, дающую вам преимущество. Пока другие паникуют, вы, подобно стражу Гермеса, стоите на границе миров, сохраняя спокойствие и ясность. Ваша способность ждать — это не бездействие, а абсолютная готовность к рывку.\n\nКто умеет ждать, тот ловит самую быструю рыбу.\n\nСмысл дня: Умение ждать — источник неуязвимой точности."),
                    (147, "59", "https://ibb.co/G4czHJZG", "🔱 ПОСЛАНИЕ ДНЯ: СИЛА В ЗАТИШЬЕ\n\nИстинный покой — это не отсутствие движения, а абсолютная готовность к нему. Подобно тому, как море замирает, собирая энергию перед мощной грозой, вы призваны использовать момент затишья для внутренней концентрации.\n\nВаш день призывает: используйте эту гладь для последней проверки своих ресурсов и своего «корабля». Вспомните Зевса, который обретал молнию в тишине Олимпа. Ваша сила — в способности создать идеальную ясность (зеркальная гладь) прежде, чем начнется хаос.\n\nЗатишье — это не пауза, это подготовка к победе.\n\nСмысл дня: Затишье — главный ресурс для действия."),
                    (148, "60", "https://ibb.co/yngBvQbz", "🔱 ПОСЛАНИЕ ДНЯ: ЧЕРПАЙ СИЛУ\n\nИстинный ресурс — всегда под ногами. Подобно тому, как нимфы и духи земли черпают жизненную энергию из цветущего луга, вы призваны сфокусироваться на богатстве настоящего момента. Солнце освещает вам путь, но корни должны быть в плодородной почве.\n\nВаш день призывает: используйте свою внутреннюю стабильность как источник неиссякаемой силы. Осознайте: яркое сияние возможностей доступно только тому, кто крепко стоит на земле. Примите свою естественную красоту и изобилие — это фундамент для самого смелого путешествия.\n\nКто крепко стоит на ногах, тот далеко смотрит.\n\nСмысл дня: Внутренняя устойчивость — главный источник изобилия."),
                    (149, "61", "https://ibb.co/RppZ4X80", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ЛЕГКОСТЬ\n\nСамая мощная энергия может быть наполнена радостью. Подобно игривым волнам, которые нежно подталкивают к берегу корабли, вы призваны использовать легкость момента для продвижения вперед. В этом движении нет борьбы, только чистая энергия.\n\nВаш день призывает: не утяжеляй свой путь чрезмерной серьезностью. Осознай, что радость и игра — это эффективный двигатель, позволяющий достичь целей без лишнего напряжения. Твоя сила в адаптивности и умении находить удовольствие в процессе.\n\nЧто играючи дается, то легко и приходит.\n\nСмысл дня: Легкость — источник максимальной эффективности."),
                    (150, "62", "https://ibb.co/C3jY5Sh7", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ПРИГЛАШЕНИЕ\n\nСтул у берега — это не знак бегства, а приглашение к осознанному отдыху перед решающим выбором. Подобно герою, который, оставив свой трон, решает войти в стихию, вы призваны отбросить сомнения и начать действовать.\n\nВаш день призывает:используйте энергию солнечного дня и пенящихся волн как мощный стимул. Вы уже отдохнули, стул ждет следующего. Ваша сила в том, чтобы встать и развернуться лицом к морю. Ваше место — там, где движение, а не там, где статика.\n\nДвижение воды смывает усталость.\n\nСмысл дня: Готовность к действию — главный ресурс."),
                    (151, "63", "https://ibb.co/tgB0y95", "🔱 ПОСЛАНИЕ ДНЯ: СЛЕДУЙ ЗА СВЕТОМ\n\nСамый надежный путь пробивается сквозь самую плотную тьму. Подобно тому, как Аполлон посылает луч света, чтобы указать герою единственное верное место посреди бушующего моря, вы призваны сфокусироваться на прорыве.\n\nВаш день призывает: не позволяйте массе проблем заслонить от вас единственную точку ясности. Осознайте: луч света указывает на вашу ближайшую, самую важную цель. Используйте эту ясность как мощный ресурс. Ваша сила — в умении видеть надежду даже в самой безнадежной ситуации.\n\nСвета всегда достаточно, чтобы увидеть следующий шаг.\n\nСмысл дня:Вера в прорыв — гарантия выхода из тьмы."),
                    (152, "64", "https://ibb.co/4wyCDg4F", "🔱 ПОСЛАНИЕ ДНЯ: ИСПОЛЬЗУЙ СИЛУ\n\nСамая большая мощь — это чистая, неуправляемая энергия. Подобно тому, как вал волны несет в себе силу Посейдона, а брызги очищают воздух, вы призваны использовать всю энергию, которая обрушивается на вас.\n\nВаш день призывает: не уклоняйтесь от столкновения с текущей проблемой. Осознайте: эта сила, кажущаяся разрушительной, может стать вашим трамплином, если вы направите ее. Сосредоточьтесь на том, чтобы оседлать гребень волны. Корабли на горизонте достижимы только через преодоление шторма.\n\nЧто не разбивает тебя, то толкает вперед.\n\nСмысл дня: Энергия рождается в самом сильном сопротивлении."),
                    (153, "65", "https://ibb.co/v6z3w64v", "🔱 ПОСЛАНИЕ ДНЯ: СОХРАНИ ПОЗИЦИЮ\n\nИстинная сила рождается в стратегической паузе. Подобно цапле — посланнику между небом и водой, которая, несмотря на серое море, сохраняет идеальную неподвижность на своем камне, вы призваны черпать силу в терпении. Эта пауза — не стагнация, а стратегическое ожидание.\n\nВаш день призывает: используй силу одиночества для максимальной концентрации. Вспомни вещего Сирина: только ясность взгляда позволяет видеть сквозь серую мглу. Твоя сила — в абсолютной уверенности, что действие придет в нужный момент, если ты остаешься на своем месте.\n\nКто твердо стоит на ногах, тот дождется своей добычи.\n\nСмысл дня: Терпение — источник неуязвимой точности."),
                    (154, "66", "https://ibb.co/bMgmWh65", "🔱 ПОСЛАНИЕ ДНЯ: ДОВЕРЬСЯ ТЕНИ\n\nВаша истинная сила часто скрыта в том, что вы не видите напрямую. Подобно тому, как верный пес сопровождает своего хозяина на границе стихий, вы призваны принять свои скрытые, глубинные инстинкты.\n\nВаш день призывает: не бойся своей Тени. Осознай, что твой внутренний мир и интуиция — твои самые надежные спутники. Камни на песке создают условия для четкого проявления твоей сути. Твоя сила — в единстве с самим собой, с той частью, которую не видно глазом.\n\nЧто невидимо глазу — управляет сильнее всего.\n\nСмысл дня: Интуиция — Ваш неиссякаемый ресурс."),
                    (155, "67", "https://ibb.co/nMHg2Vrn", "🔱 ПОСЛАНИЕ ДНЯ: ЧУВСТВУЙ ОПОРУ\n\nВаша сила — это не то, что вы создаете сейчас, а то, что выдержало все прошлые бури. Подобно древнему утесу, который остался незыблемым, формируя проход сквозь время, вы призваны опираться на свою самую твердую основу.\n\nВаш день призывает: используй уроки прошлых штормов как гарантию своей нынешней прочности. Вспомни Атланта, который, стоя неподвижно, держал небеса. Твоя сила — в твоей незыблемости и способности стать проходом для других, опираясь на свою историю.\n\nЧто не сломилось, то стало вечным.\n\nСмысл дня: Стойкость, закаленная временем — источник ресурса."),
                    (156, "68", "https://ibb.co/CKw65fgY", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ НАГРАДУ\n\nСамая большая сила заключена в моменте завершения. Подобно солнцу, которое, завершая свой путь, окрашивает небеса в самые яркие и мощные цвета, вы призваны увидеть и принять красоту своего труда.\n\nВаш день призывает: остановись, чтобы увидеть и почувствовать славу момента. Осознай: это время не для бега, а для глубокой, эмоциональной оценки. Твоя сила — в умении радоваться своим достижениям и находить в них энергию для нового цикла. Это момент истины и красоты, созданный твоим днем.\n\nКрасота завершения — это награда за путь.\n\nСмысл дня: Способность видеть красоту итогов — источник вдохновения."),
                    (157, "69", "https://ibb.co/vC1TFZRP", "🔱 ПОСЛАНИЕ ДНЯ: ЧЕРПАЙ ИЗ ГЛУБИНЫ\n\nСамая надежная позиция — там, где внешнее буйство не нарушает внутренней ясности. Подобно прорицателю, который наблюдает за миром из грота, вы призваны использовать свое уединение для точного стратегического обзора.\n\nВаш день призывает: не спеши выходить в хаос. Осознай: грот дает тебе защиту и древнюю мудрость скалы, позволяя видеть, как волны разбиваются о камни, не затрагивая тебя. Используй отблески заката для финального озарения. Твоя сила — в твоей способности видеть цели из полной безопасности.\n\nКто видит из глубины, того не сбить с пути.\n\nСмысл дня: Ваша защищенность — источник стратегической ясности."),
                    (158, "70", "https://ibb.co/Q38PdBJF", "🔱 ПОСЛАНИЕ ДНЯ: НАЧНИ С ЛЕГКОСТЬЮ\n\nСамое мощное обновление приходит тихо. Подобно Эос, которая окрашивает небо в нежные персиковые оттенки, даруя мягкое начало, Вселенная предлагает вам начать свой путь без борьбы.\n\nВаш день призывает: используй снисходительность стихии. Осознай: волна, которая несет легкое обещание, а не угрозу, дает тебе шанс вступить в воду без страха. Твоя сила — в мягком, но уверенном шаге. Прими эту нежную энергию рассвета как знак того, что твой путь благословлен.\n\nЧто начато в нежности, то приносит плоды в радости.\n\nСмысл дня: Вера в благосклонность момента — Ваш главный ресурс."),
                    (159, "71", "https://ibb.co/ksy9Fp7T", "🔱 ПОСЛАНИЕ ДНЯ: ИСПОЛЬЗУЙ КОНФЛИКТ\n\nИстинное очищение требует столкновения. Подобно волне, которая, разбиваясь о камни, преобразует свою энергию в чистую, сияющую пену (символ Афродиты), вы призваны использовать конфликты для создания ясности.\n\nВаш день призывает: не уклоняйся от необходимых столкновений. Осознай: напряжение между черной тучей и голубым небом — это динамика жизни, а не приговор. Ваша сила — в способности видеть в разрушении процесс очищения и создания новой, незамутненной сути.\n\nЧто разбивается о камни, то становится чище.\n\nСмысл дня:Ваша сила — в очищении через конфликт."),
                    (160, "72", "https://ibb.co/39Zg7wzD", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ДАР\n\nИстинный покой — это дар, который не нужно создавать. Подобно абсолютному штилю на море вы призваны увидеть, что ваш ресурс и ясность уже существуют.\n\nВаш день призывает: используй этот идеальный, всеобъемлющий штиль для полного погружения в себя. Осознай: розоватый горизонт — это благословение. Твоя сила — в умении видеть и принимать этот природный покой как универсальный ресурс, который не зависит от твоих усилий. Ты можешь действовать из этого центра.\n\nПокой, который не создаешь, всегда глубже того, что строишь.\n\nСмысл дня: Принятие естественного покоя — неисчерпаемый источник энергии."),
                    (161, "73", "https://ibb.co/7JVkWqwG", "🔱 ПОСЛАНИЕ ДНЯ: СОЗЕРЦАЙ НЕПОДВИЖНО\n\nИстинная сила не в действии, а в глубине созерцания. Подобно герою, который, сидя на твердых скалах, использует серую гладь моря для погружения в себя, вы призваны найти ответы в неподвижности.\n\nВаш день призывает:не спеши прерывать момент ожидания. Осознай: спокойное, хоть и грустное море — идеальный фон для внутренней работы. Две чайки — символы твоего духа, который свободен летать и приносить знаки. Твоя сила — в способности оставаться устойчивым на камнях, пока внутренняя ясность не принесет решение.\n\nКто неподвижен, тот видит движение мира.\n\nСмысл дня: Ваша сила в созерцании момента."),
                    (162, "74", "https://ibb.co/Lz4cLFm7", "🔱 ПОСЛАНИЕ ДНЯ: УКРЕПИ ГРАНИЦЫ\n\nВаша самая надежная опора — это вековая, проверенная временем устойчивость. Подобно древней крепости, которая веками стоит против натиска стихий, вы призваны черпать силу в своей незыблемости.\n\nВаш день призывает: используй силу своего рода для укрепления границ. Осознай: серое море, бьющееся о стены крепости, не способно разрушить то, что строилось веками. Ваша сила — в способности сохранять спокойствие и безопасность, даже когда вокруг кипят невидимые битвы.\n\nЧто выстояло века, то не разрушит мгновение.\n\nСмысл дня: Стратегии Вашего рода — выдержали ни один шторм."),
                    (163, "75", "https://ibb.co/kVxZV6cs", "🔱 ПОСЛАНИЕ ДНЯ: СЛЕДУЙ ПОТОКУ\n\nВаша сила в естественной и непрерывной тяге к своему предназначению. Подобно реке, которая, невзирая на преграды, стремится к манящему морю, вы призваны направить всю свою энергию на ясную цель.\n\nВаш день призывает: не сомневайся в своей траектории. Осознай: игривость моря и лохматые облака — это знаки того, что цель несет радость, а не борьбу. Сила твоего предназначения — в энергии этого непрерывного движения. Направляй свой поток, зная, что слияние принесет расширение, а не потерю.\n\nЧто течет по своей воле, то обретает великое.\n\nСмысл дня: Следование своему предназначению — источник вдохновения."),
                    (164, "76", "https://ibb.co/pvRGdsJq", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ПЕРЕХОД\n\nИстинная сила — в единстве всех циклов. Подобно тому, как яркий Гелиос (Солнце) и мудрая Селена (Луна) одновременно благословляют небо, вы призваны соединить завершение с интуитивным новым началом.\n\nВаш день призывает: используй эту двойную энергию для идеального старта. Осознай: комфорт беседок и пальм дал тебе точку покоя. Твоя сила — в способности видеть завершение как идеальную подготовку к следующему этапу. Смело следуй за интуицией, которую шепчет тебе Луна.\n\nЧто не заканчивается, то не может начаться.\n\nСмысл дня: Ваша интуиция благословлена моментом перехода."),
                    (165, "77", "https://ibb.co/HfQNCShm", "🔱 ПОСЛАНИЕ ДНЯ: ЧУВСТВУЙ ПРИЗЫВ\n\nВаша сила в том, чтобы использовать время перехода и энергию заката для финальной проверки своего пути. Подобно герою, который, невзирая на оптические иллюзии вечернего неба, держит в фокусе путеводную цель, вы призваны к максимальной концентрации.\n\nВаш день призывает:не позволяй красоте или страху уходящего дня отвлечь тебя от главного. Осознай: серое море и тревожная волна — это лишь фон, требующий уважения, но не паники. Твоя сила — в дальновидности, которая позволяет отличать игру света от истинной цели в виде точки на морской ряби.\n\nЧто остается видимым сквозь любую дымку, то и есть твой путь.\n\nСмысл дня: Ваша дальновидность — источник движения."),
                    (166, "78", "https://ibb.co/fY14FYfr", "🔱 ПОСЛАНИЕ ДНЯ: СТРОЙ ВЕЛИКОЕ МАЛЫМ\n\nВаша сила в том, что вы способны управлять грандиозными целями через скромные, ежедневные усилия. Подобно тому, как волны на море движутся в гармонии с огромной, воздушной волной на небе, вы призваны синхронизировать свое действие и свой потенциал.\n\nВаш день призывает:не теряй из виду величие своего замысла. Осознай: каждый малый шаг абсолютно необходим для создания той энергии, которая поднимет тебя к небесному потенциалу. Ваша сила — в умении видеть конечную форму даже в начальной стадии движения.\n\nТот, кто уважает малый шаг, дойдет до великой цели.\n\nСмысл дня: Синхронность шага и цели — приводит к результату."),
                    (167, "79", "https://ibb.co/Y7YdQtSR", "🔱 ПОСЛАНИЕ ДНЯ: БУДЬ В ПОТОКЕ\n\nВаша сила — в идеальной синхронизации со стихией. Подобно серферу, который, став единым целым с волной, использует ее мощь для стремительного движения, вы призваны полностью довериться потоку.\n\nВаш день призывает: используй энергию огромного риска не как угрозу, а как катализатор. Осознай: только ваше идеальное равновесие и умение быть в потоке позволяют преобразовать потенциальную гибель в чистый триумф и стремительно достичь цели. Твое тело — это инструмент, а стихия — твой двигатель.\n\nЧто движется с потоком, то неуязвимо для него.\n\nСмысл дня:Доверие потоку делает риск оправданным."),
                    (168, "80", "https://ibb.co/4ZghKHhF", "🔱 ПОСЛАНИЕ ДНЯ: ОТКРОЙ ТАЙНУ\n\nВаша сила — в способности находить тайные знания, когда мир погружен в сон. Подобно герою сказок Шехерезады, вы призваны использовать ночную тишину для получения интуитивных, звездных ответов.\n\nВаш день призывает: используй штиль как магическое зеркало. Осознай: буйки и волнорез не держат тебя, а оберегают, пока ты вступаешь в союз с Луной. Твое тело в покое синхронизировано со звездным потоком, и сейчас ты можешь увидеть отражение истины, недоступное дневному свету.\n\nВсе сакральные откровения скрыты в темноте.\n\nСмысл дня: Штиль лунного света — ключ к тайным знаниям."),
                    (169, "81", "https://ibb.co/v43v25F6", "🔱 ПОСЛАНИЕ ДНЯ: СОВЕРШИ ПЕРЕХОД\n\nВаша сила — в мгновенной ясности, которая открывается среди облаков сомнений. Подобно тому, как небо прорывается «Окном возможностей», вы призваны увидеть, что истинное решение всегда доступно, нужно лишь поднять взгляд.\n\nВаш день призывает: используй эту внезапную, ясную веру как свой главный ресурс. Осознай: сероватые отливы моря, как и прежние тревоги, меркнут перед бирюзовой глубиной и небесным прорывом. Ваше тело должно быть готово принять этот поток ясности и веры, чтобы совершить переход.\n\nЧто открыто перед тобой, то и есть твой истинный путь.\n\nСмысл дня:Ваша вера — ключ к переходу на другой уровень."),
                    (170, "82", "https://ibb.co/sdn4mhZ0", "🔱 ПОСЛАНИЕ ДНЯ: ОСТАНОВИ ДВИЖЕНИЕ\n\nТвоя сила — в искусстве прерванного движения и обретении идеального баланса. Подобно Висельнику, стоящему на краю жизни, ты призван остановить себя для полного очищения.\n\nВаш день призывает: используй эту точку подвешивания, чтобы получить совершенно новый, перевернутый взгляд на свою цель. Только в этом временном равновесии ты сможешь смыть с себя песок прошлого и увидеть, как чистый горизонт обещает обновление.\n\nЧто видно с нового ракурса, то становится твоим ключом.\n\nСмысл дня: Зависание в паузе — источник обновления и ясности."),
                    (171, "83", "https://ibb.co/jkpXB0Yg", "🔱 ПОСЛАНИЕ ДНЯ: ФОКУСИРУЙСЯ НА СВЕТЕ\n\nТвоя сила — в способности сохранять предельную ясность, когда угроза неизбежна. Подобно тому, как из-под тяжелой тучи видна единственная полоска чистого неба, ты призван фокусироваться на единственной, абсолютно чистой цели.\n\nВаш день призывает: используй давление тучи как катализатор. Осознай: беспокойное море под тобой дает энергию для решительного, высокоточного маневра. Именно в этот момент кризиса, когда все второстепенное исчезает, рождается истинная точность. Твое тело должно быть готово к мгновенному, единственно верному действию.\n\nЧто не поглощено тьмой, то и есть твой истинный путь.\n\nСмысл дня: Движение к свету — Ваша единственная опора в кризисе."),
                    (172, "84", "https://ibb.co/dJBzhRhN", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ РАДОСТЬ СПОНТАННОСТИ\n\nТвоя сила — в способности услышать зов Внутреннего Ребенка и позволить себе неожиданную, чистую радость. Подобно озорной волне, которая вносит живое движение в идеальный штиль, ты призван вернуть в свою жизнь элемент спонтанности и игры.\n\nВаш день призывает: используй эту игривую энергию как вдохновение. Осознай: спокойный берег и безоблачное небо — это твоя стабильность, но именно эта волна дает жизненную силу. Твое тело должно синхронизироваться с шаловливым потоком, чтобы найти самый легкий и самый радостный путь.\n\nИскренняя непосредственность — является источником вдохновения.\n\nСмысл дня: Спонтанность Внутреннего Ребенка — неиссякаемый поток энергии."),
                    (173, "85", "https://ibb.co/Lh2h2B13", "🔱 ПОСЛАНИЕ ДНЯ: ЛЮБОВЬ ОСВОБОЖДАЕТ\n\nТвоя сила — в способности совершить решающий акт самоотдачи ради высшей идеи или истинной любви. Подобно Русалочке, отдавшей свою прежнюю форму, ты призван использовать всю мощь своего внутреннего потока для великого жертвоприношения во имя любви.\n\nВаш день призывает: используй мощную энергию волны для финального, преобразующего действия. Осознай: только полностью расставшись со старой формой, ты обретешь свободу и чистоту. Эта жертва ради любви — не конец, а начало нового, свободного существования.\n\nЧто отдано морю во имя любви, то возвращается чистой свободой.\n\nСмысл дня: Самоотдача приводит к способности любить."),
                    (174, "86", "https://ibb.co/9H9jV1tq", "🔱 ПОСЛАНИЕ ДНЯ: ПРИМИ ГОРЬКУЮ ПРАВДУ\n\nТвоя сила — в способности принять самую неудобную истину, которую поднимает на поверхность жизненный шторм. Именно сейчас, когда тайное становится явным, ты осознаешь: лучше горькая правда, чем сладкая ложь.\n\nВаш день призывает: используй это откровение для полного перерождения. Осознай: горькая правда — это фундамент нового строительства, а не конец. Над мутной водой всегда есть просвет чистого неба и чайка, несущая надежду. Твое тело должно быть готово к глубокой, но очищающей работе, чтобы интегрировать эту истину в свою силу.\n\nЧто поднято со дна, то служит для перерождения.\n\nСмысл дня:Горькая правда — источник глубинного роста."),
                    (175, "87", "https://ibb.co/DDvF5nWq", '🔱 ПОСЛАНИЕ ДНЯ: ПЕРОЖДЕНИЕ В ОГНЕ\n\nТвоя сила — в моменте выхода из пены, который завершает цикл и дарует тебе сияние нового "Я". Подобно Афродите, рожденной из пены, ты призван использовать кульминацию огненной энергии заката для проявления своей истинной красоты и силы.\n\nВаш день призывает: используй этот момент выхода, чтобы зарядиться светом. Осознай: волны и пена — это материал для твоего перерождения. Твое тело, освещенное огнем заката, готово принять в себя всю мощь стихий, чтобы выйти на новый берег — сияющим и обновленным.\n\nЧто рождено в огне, то несет в себе вечный свет.\n\nСмысл дня: Ваше перерождение — источник неземной силы и обновления.'),
                    (176, "88", "https://ibb.co/4wNXYS52", "🔱 ПОСЛАНИЕ ДНЯ: ОБРЕТИ СИЛУ ХАОСА\n\nТвоя сила — в моменте, когда ты перестаешь бороться со стихией и решаешь стать ее частью. Перед лицом абсолютного хаоса ты призван отпустить контроль и найти свою истинную, инстинктивную реакцию.\n\nВаш день призывает: используй мощь шторма для своего движения. Осознай: когда все разрушено, ты обретаешь момент обнуления. Перейди от сопротивления к доверию потоку. Твое тело должно научиться двигаться в тандеме с волной, используя ее силу, чтобы выжить и выйти обновленным.\n\nТот, кто доверяет хаосу, обретает инстинктивную свободу.\n\nСмысл дня: Доверься хаосу и обновись в его силе.")
        ]

    def add_missing_cards(self):
        """Добавляет отсутствующие карты в базу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            sample_cards = self.get_cards_data()
            
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

    def update_cards_descriptions(self):
        """Обновляет описания существующих карт в базе данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Используем тот же массив, что и в add_missing_cards
            updated_cards = self.get_cards_data()
            
            updated_count = 0
            for card in updated_cards:
                card_id, card_name, image_url, description_text = card
                
                cursor.execute('''
                    UPDATE cards 
                    SET card_name = %s, image_url = %s, description_text = %s
                    WHERE card_id = %s
                ''', (card_name, image_url, description_text, card_id))
                
                if cursor.rowcount > 0:
                    updated_count += 1
            
            conn.commit()
            logging.info(f"✅ Обновлено описаний {updated_count} карт")
            return updated_count
            
        except Exception as e:
            logging.error(f"❌ Error updating cards descriptions: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def force_update_all_cards(self):
        """Принудительно обновляет ВСЕ карты (INSERT или UPDATE)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            all_cards = self.get_cards_data()
            
            updated_count = 0
            for card in all_cards:
                card_id, card_name, image_url, description_text = card
                
                cursor.execute('''
                    INSERT INTO cards (card_id, card_name, image_url, description_text)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (card_id) 
                    DO UPDATE SET 
                        card_name = EXCLUDED.card_name,
                        image_url = EXCLUDED.image_url,
                        description_text = EXCLUDED.description_text
                    RETURNING card_id
                ''', card)
                
                if cursor.fetchone():
                    updated_count += 1
            
            conn.commit()
            logging.info(f"✅ Принудительно обновлено {updated_count} карт")
            return updated_count
            
        except Exception as e:
            logging.error(f"❌ Error force updating cards: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
 
    def get_last_user_card_description(self, user_id: int):
        """Получает описание последней карты пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT c.description_text 
                FROM user_cards uc
                JOIN cards c ON uc.card_id = c.card_id
                WHERE uc.user_id = %s
                ORDER BY uc.drawn_date DESC
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                description = result[0]
                return description
            else:
                return "❌ Не удалось найти описание последней карты. Сначала получите карту дня!"
                
        except Exception as e:
            logging.error(f"❌ Error getting last user card: {e}")
            return "❌ Ошибка при получении описания карты"
        finally:
            conn.close()
    
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

    def create_subscription(self, user_id: int, subscription_type: str, duration_days: int):
        """Создает подписку для пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            from datetime import datetime, timedelta
            from config import DAILY_CARD_LIMIT_PREMIUM, DAILY_CARD_LIMIT_FREE
            
            # Устанавливаем время окончания подписки на КОНЕЦ дня
            end_date = datetime.now() + timedelta(days=duration_days)
            # Устанавливаем на 23:59:59 последнего дня
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
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
            
            # ✅ ОБНОВЛЯЕМ ПОЛЬЗОВАТЕЛЯ КОРРЕКТНО
            cursor.execute('''
                UPDATE users 
                SET is_premium = TRUE, 
                    premium_until = %s, 
                    daily_cards_limit = %s
                WHERE user_id = %s
            ''', (end_date, DAILY_CARD_LIMIT_PREMIUM, user_id))
            
            conn.commit()
            
            logging.info(f"✅ Subscription created for user {user_id}: {subscription_type}, until {end_date}")
            return True
            
        except Exception as e:
            conn.rollback()
            logging.error(f"❌ Error creating subscription: {e}")
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
                if hasattr(premium_until, 'date'):
                    premium_date = premium_until.date()
                elif isinstance(premium_until, str):
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
                # Для бесплатных: проверяем общее количество посланий (максимум 3 за всё время)
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM user_messages 
                    WHERE user_id = %s
                ''', (user_id,))
                
                total_messages_count = cursor.fetchone()[0]
                logging.info(f"📊 Free user {user_id}: total_messages_count={total_messages_count}")
                
                if total_messages_count >= 3:
                    return False, "Вы использовали все бесплатные послания. Оформите подписку для неограниченного доступа!"
                else:
                    remaining = 3 - total_messages_count
                    return True, f"Можно взять послание ({remaining} из 3 бесплатных осталось)"
                        
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
                # Для бесплатных: общее количество посланий
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM user_messages 
                    WHERE user_id = %s
                ''', (user_id,))
                
                total_messages_count = cursor.fetchone()[0]
                limit = 3
                remaining = max(0, limit - total_messages_count)
                can_take = total_messages_count < limit
                
                return {
                    'has_subscription': False,
                    'total_count': total_messages_count,
                    'limit': limit,
                    'remaining': remaining,
                    'can_take': can_take
                }
                
        except Exception as e:
            logging.error(f"❌ Error getting message stats: {e}")
            return None
        finally:
            conn.close()

    def reset_user_messages(self, user_id: int):
        """Сбрасывает историю посланий пользователя за сегодня"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            today = date.today()
            
            # Удаляем послания за сегодня
            cursor.execute('''
                DELETE FROM user_messages 
                WHERE user_id = %s AND DATE(drawn_date) = %s
            ''', (user_id, today))
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            return deleted_count
            
        except Exception as e:
            logging.error(f"❌ Error resetting user messages: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def reset_all_messages_today(self):
        """Сбрасывает все послания за сегодня (для администратора)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            today = date.today()
            
            # Удаляем все послания за сегодня
            cursor.execute('''
                DELETE FROM user_messages 
                WHERE DATE(drawn_date) = %s
            ''', (today,))
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            return deleted_count
            
        except Exception as e:
            logging.error(f"❌ Error resetting all messages: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def get_random_restriction_card(self):
        """Получает случайную карту-ограничение (1-88)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT card_id, card_name, image_url, description_text 
                FROM cards 
                WHERE card_id BETWEEN 1 AND 88
                ORDER BY RANDOM() 
                LIMIT 1
            ''')
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"❌ Error getting restriction card: {e}")
            return None
        finally:
            conn.close()

    def get_random_opportunity_card(self):
        """Получает случайную карту-возможность (89-176)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT card_id, card_name, image_url, description_text 
                FROM cards 
                WHERE card_id BETWEEN 89 AND 176
                ORDER BY RANDOM() 
                LIMIT 1
            ''')
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"❌ Error getting opportunity card: {e}")
            return None
        finally:
            conn.close()

    def can_watch_meditation(self, user_id: int) -> tuple:
        """Проверяет, может ли пользователь смотреть медитацию"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Проверяем подписку пользователя
            subscription = self.get_user_subscription(user_id)
            
            if subscription and subscription[1]:
                # Если есть активная подписка - доступ всегда открыт
                subscription_end = subscription[1]
                if hasattr(subscription_end, 'date'):
                    sub_date = subscription_end.date()
                else:
                    sub_date = subscription_end
                
                if sub_date >= date.today():
                    conn.close()
                    return True, "✅ Доступ открыт по подписке"
            
            # Для бесплатных пользователей проверяем, использовали ли они уже бесплатный доступ
            cursor.execute('''
                SELECT id FROM user_meditations 
                WHERE user_id = %s
                LIMIT 1
            ''', (user_id,))
            
            has_watched = cursor.fetchone() is not None
            
            if has_watched:
                conn.close()
                return False, "❌ Вы уже использовали бесплатный доступ к медитации. Оформите подписку для неограниченного доступа!"
            else:
                conn.close()
                return True, "✅ Можно смотреть медитацию (бесплатный доступ)"
                
        except Exception as e:
            logging.error(f"❌ Error checking meditation access: {e}")
            conn.close()
            return False, "❌ Ошибка при проверке доступа к медитации"
        finally:
            conn.close()

    def record_meditation_watch(self, user_id: int) -> bool:
        """Записывает факт просмотра медитации (для бесплатных пользователей)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Создаем таблицу для истории просмотров медитаций, если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_meditations (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    watched_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Проверяем, есть ли уже запись
            cursor.execute('SELECT id FROM user_meditations WHERE user_id = %s', (user_id,))
            if cursor.fetchone():
                return True  # Уже есть запись
                
            # Записываем просмотр
            cursor.execute('''
                INSERT INTO user_meditations (user_id) 
                VALUES (%s)
            ''', (user_id,))
            
            conn.commit()
            logging.info(f"✅ Meditation watch recorded for user {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error recording meditation watch: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def cleanup_expired_video_links(self):
        """Очищает просроченные видео ссылки"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM video_links WHERE expires_at < NOW()')
            deleted_count = cursor.rowcount
            conn.commit()
            logging.info(f"✅ Cleaned up {deleted_count} expired video links")
            return deleted_count
        except Exception as e:
            logging.error(f"❌ Error cleaning up video links: {e}")
            return 0
        finally:
            conn.close()

    def save_video_link(self, link_hash: str, user_id: int, video_url: str, 
                   expires_at: datetime, platform: str, has_subscription: bool) -> bool:
        """Сохраняет информацию о видео ссылке в базу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Сначала обновляем структуру таблицы
            self.update_video_links_table()
            
            # Сохраняем ссылку
            cursor.execute('''
                INSERT INTO video_links (link_hash, user_id, video_url, platform, has_subscription, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (link_hash) 
                DO UPDATE SET 
                    video_url = EXCLUDED.video_url,
                    platform = EXCLUDED.platform,
                    has_subscription = EXCLUDED.has_subscription,
                    expires_at = EXCLUDED.expires_at
            ''', (link_hash, user_id, video_url, platform, has_subscription, expires_at))
            
            conn.commit()
            logging.info(f"✅ Video link saved for user {user_id}, platform: {platform}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error saving video link: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def start_video_access(self, link_hash: str) -> bool:
        """Устанавливает время начала доступа для бесплатных пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Устанавливаем время начала и время окончания (1 час)
            access_started = datetime.now()
            expires_at = access_started + timedelta(hours=1)
            
            cursor.execute('''
                UPDATE video_links 
                SET access_started_at = %s, expires_at = %s
                WHERE link_hash = %s AND access_started_at IS NULL
            ''', (access_started, expires_at, link_hash))
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logging.info(f"✅ Video access started for link {link_hash}, expires at {expires_at}")
            else:
                logging.warning(f"⚠️ Video access already started for link {link_hash}")
                
            return success
            
        except Exception as e:
            logging.error(f"❌ Error starting video access: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_video_link(self, link_hash: str):
        """Получает информацию о видео ссылке из базы"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT user_id, video_url, platform, has_subscription, access_started_at, expires_at 
                FROM video_links 
                WHERE link_hash = %s
            ''', (link_hash,))
            
            result = cursor.fetchone()
            if result:
                user_id, video_url, platform, has_subscription, access_started_at, expires_at = result
                
                # Проверяем срок действия
                if expires_at and datetime.now() > expires_at:
                    # Удаляем просроченную ссылку
                    cursor.execute('DELETE FROM video_links WHERE link_hash = %s', (link_hash,))
                    conn.commit()
                    return None
                    
                return {
                    'user_id': user_id, 
                    'video_url': video_url, 
                    'platform': platform,
                    'has_subscription': has_subscription,
                    'access_started_at': access_started_at,
                    'expires_at': expires_at
                }
            return None
            
        except Exception as e:
            logging.error(f"❌ Error getting video link: {e}")
            return None
        finally:
            conn.close()

    def update_video_links_table(self):
        """Обновляет структуру таблицы video_links"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Сначала делаем колонку expires_at nullable
            cursor.execute('''
                ALTER TABLE video_links 
                ALTER COLUMN expires_at DROP NOT NULL
            ''')
            
            # Добавляем все необходимые колонки если их нет
            cursor.execute('''
                ALTER TABLE video_links 
                ADD COLUMN IF NOT EXISTS video_url TEXT,
                ADD COLUMN IF NOT EXISTS platform TEXT,
                ADD COLUMN IF NOT EXISTS has_subscription BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS access_started_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS base_hash TEXT
            ''')
            
            # Если есть старая колонка yandex_link, делаем ее nullable
            cursor.execute('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'video_links' AND column_name = 'yandex_link'
            ''')
            
            has_yandex_column = cursor.fetchone() is not None
            
            if has_yandex_column:
                cursor.execute('''
                    ALTER TABLE video_links ALTER COLUMN yandex_link DROP NOT NULL
                ''')
                logging.info("✅ Made yandex_link column nullable")
                
                # Переносим данные из yandex_link в video_url если нужно
                cursor.execute('''
                    UPDATE video_links 
                    SET video_url = yandex_link 
                    WHERE video_url IS NULL AND yandex_link IS NOT NULL
                ''')
                logging.info("✅ Migrated data from yandex_link to video_url")
            
            conn.commit()
            logging.info("✅ Video links table updated successfully")
            
        except Exception as e:
            logging.error(f"❌ Error updating video links table: {e}")
            conn.rollback()
        finally:
            conn.close()

    def create_meditation_access(self, user_id: int, base_hash: str) -> bool:
        """Создает запись о доступе к медитации с общим временем"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Создаем таблицу для управления доступом если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS meditation_access (
                    base_hash TEXT PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    access_started_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создаем запись о доступе (время еще не установлено)
            cursor.execute('''
                INSERT INTO meditation_access (base_hash, user_id)
                VALUES (%s, %s)
                ON CONFLICT (base_hash) DO NOTHING
            ''', (base_hash, user_id))
            
            conn.commit()
            logging.info(f"✅ Meditation access created for user {user_id}, base_hash: {base_hash}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error creating meditation access: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def start_meditation_access(self, user_id: int) -> bool:
        """Запускает отсчет времени доступа к медитации для бесплатных пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Устанавливаем время начала и время окончания (24 часа)
            access_started = datetime.now()
            expires_at = access_started + timedelta(hours=24)
            
            # Обновляем все активные ссылки пользователя
            cursor.execute('''
                UPDATE video_links 
                SET access_started_at = %s, expires_at = %s
                WHERE user_id = %s AND has_subscription = FALSE
            ''', (access_started, expires_at, user_id))
            
            conn.commit()
            updated_count = cursor.rowcount
            
            if updated_count > 0:
                logging.info(f"✅ Meditation access started for user {user_id}, expires at {expires_at}")
                return True
            else:
                logging.warning(f"⚠️ No video links found for user {user_id}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error starting meditation access: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_meditation_access_info(self, user_id: int):
        """Получает информацию о доступе к медитации"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Проверяем подписку
            subscription = self.get_user_subscription(user_id)
            has_active_subscription = False
            subscription_end = None
            
            if subscription and subscription[1]:
                subscription_end = subscription[1]
                if hasattr(subscription_end, 'date'):
                    has_active_subscription = subscription_end.date() >= date.today()
            
            # Для подписчиков возвращаем информацию о подписке
            if has_active_subscription:
                return {
                    'has_subscription': True,
                    'expires_at': subscription_end,
                    'access_started_at': None
                }
            
            # Для бесплатных пользователей ищем активную ссылку
            cursor.execute('''
                SELECT access_started_at, expires_at 
                FROM video_links 
                WHERE user_id = %s AND has_subscription = FALSE 
                AND expires_at > NOW()
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                access_started_at, expires_at = result
                return {
                    'has_subscription': False,
                    'expires_at': expires_at,
                    'access_started_at': access_started_at
                }
            else:
                # Проверяем, использовал ли пользователь бесплатный доступ
                cursor.execute('SELECT id FROM user_meditations WHERE user_id = %s', (user_id,))
                has_used_free = cursor.fetchone() is not None
                
                return {
                    'has_subscription': False,
                    'expires_at': None,
                    'access_started_at': None,
                    'has_used_free': has_used_free
                }
                
        except Exception as e:
            logging.error(f"❌ Error getting meditation access info: {e}")
            return None
        finally:
            conn.close()

    def start_all_user_video_access(self, user_id: int) -> bool:
        """Запускает отсчет времени для ВСЕХ видео ссылок пользователя одновременно"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Устанавливаем время начала и время окончания (24 часа) для всех ссылок пользователя
            access_started = datetime.now()
            expires_at = access_started + timedelta(hours=24)  # Изменено с 1 часа на 24 часа
            
            cursor.execute('''
                UPDATE video_links 
                SET access_started_at = %s, expires_at = %s
                WHERE user_id = %s AND access_started_at IS NULL AND has_subscription = FALSE
            ''', (access_started, expires_at, user_id))
            
            conn.commit()
            updated_count = cursor.rowcount
            logging.info(f"✅ Started video access for {updated_count} user {user_id} links, expires at {expires_at}")
            
            return updated_count > 0
            
        except Exception as e:
            logging.error(f"❌ Error starting all user video access: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def save_paypal_payment(self, user_id: int, subscription_type: str, amount: float, payment_id: str = None, product_type: str = "subscription"):
        """Сохраняет информацию о PayPal платеже в базу"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Для платежей за колоду subscription_type должен быть NULL
            sub_type = subscription_type if product_type == "subscription" else None
            
            cursor.execute('''
                INSERT INTO payments (user_id, amount, subscription_type, product_type, status, payment_method, payment_id, currency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                user_id,
                amount,
                sub_type,  # Будет NULL для колоды
                product_type,
                'pending',
                'paypal',
                payment_id or f"paypal_{user_id}_{int(datetime.now().timestamp())}",
                'ILS'
            ))
            
            conn.commit()
            logging.info(f"✅ PayPal payment saved to database for user {user_id}, product_type: {product_type}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error saving PayPal payment to DB: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def create_manual_subscription(self, user_id: int, subscription_type: str, duration_days: int):
        """Создает подписку для пользователя вручную (для администратора)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            from datetime import datetime, timedelta
            from config import DAILY_CARD_LIMIT_PREMIUM
            
            # Проверяем существование пользователя
            cursor.execute('SELECT user_id FROM users WHERE user_id = %s', (user_id,))
            if not cursor.fetchone():
                return False, "Пользователь не найден"
            
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
            
            # Обновляем лимит карт для премиум пользователей
            cursor.execute('''
                UPDATE users 
                SET is_premium = TRUE, 
                    premium_until = %s, 
                    daily_cards_limit = %s
                WHERE user_id = %s
            ''', (end_date, DAILY_CARD_LIMIT_PREMIUM, user_id))
            
            # Записываем ручной платеж в историю
            cursor.execute('''
                INSERT INTO payments (user_id, amount, subscription_type, status, payment_method, payment_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                user_id,
                0,  # Бесплатно
                subscription_type,
                'success',
                'manual',
                f"manual_{user_id}_{int(datetime.now().timestamp())}"
            ))
            
            conn.commit()
            
            logging.info(f"✅ Manual subscription created for user {user_id}: {subscription_type}, duration: {duration_days} days")
            return True, f"Подписка успешно активирована до {end_date.strftime('%d.%m.%Y')}"
            
        except Exception as e:
            conn.rollback()
            logging.error(f"❌ Error creating manual subscription: {e}")
            return False, f"Ошибка: {str(e)}"
        finally:
            conn.close()

    def get_user_info(self, user_id: int):
        """Получает информацию о пользователе"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT u.user_id, u.username, u.first_name, u.is_premium, u.premium_until,
                    COUNT(uc.id) as total_cards,
                    u.registered_date
                FROM users u
                LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                WHERE u.user_id = %s
                GROUP BY u.user_id, u.username, u.first_name, u.is_premium, u.premium_until, u.registered_date
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                user_id, username, first_name, is_premium, premium_until, total_cards, registered_date = result
                return {
                    'user_id': user_id,
                    'username': username,
                    'first_name': first_name,
                    'is_premium': is_premium,
                    'premium_until': premium_until,
                    'total_cards': total_cards,
                    'registered_date': registered_date
                }
            return None
            
        except Exception as e:
            logging.error(f"❌ Error getting user info: {e}")
            return None
        finally:
            conn.close()

    def update_payments_table_structure(self):
        """Обновляет структуру таблицы payments для поддержки NULL в subscription_type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Делаем subscription_type nullable
            cursor.execute('''
                ALTER TABLE payments 
                ALTER COLUMN subscription_type DROP NOT NULL
            ''')
            
            # Добавляем product_type если нет
            cursor.execute('''
                ALTER TABLE payments 
                ADD COLUMN IF NOT EXISTS product_type TEXT DEFAULT 'subscription'
            ''')
            
            conn.commit()
            logging.info("✅ Payments table structure updated: subscription_type now nullable")
            
        except Exception as e:
            logging.error(f"❌ Error updating payments table structure: {e}")
            conn.rollback()
        finally:
            conn.close()

    def check_and_update_expired_subscriptions(self):
        """Проверяет и обновляет истекшие подписки"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            from config import DAILY_CARD_LIMIT_FREE
            
            # Находим пользователей с истекшей подпиской
            cursor.execute('''
                UPDATE users 
                SET is_premium = FALSE, 
                    daily_cards_limit = %s,
                    premium_until = NULL
                WHERE is_premium = TRUE 
                AND premium_until < CURRENT_TIMESTAMP
            ''', (DAILY_CARD_LIMIT_FREE,))
            
            updated_count = cursor.rowcount
            
            # Также деактивируем подписки в таблице subscriptions
            cursor.execute('''
                UPDATE subscriptions 
                SET is_active = FALSE 
                WHERE is_active = TRUE 
                AND end_date < CURRENT_TIMESTAMP
            ''')
            
            deactivated_count = cursor.rowcount
            
            conn.commit()
            
            if updated_count > 0:
                logging.info(f"✅ Updated {updated_count} expired subscriptions in users table")
                logging.info(f"✅ Deactivated {deactivated_count} expired subscriptions")
            
            return updated_count
            
        except Exception as e:
            logging.error(f"❌ Error checking expired subscriptions: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def check_user_subscription_expiry(self, user_id: int):
        """Проверяет и обновляет истекшую подписку для конкретного пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            from config import DAILY_CARD_LIMIT_FREE
            
            cursor.execute('''
                SELECT is_premium, premium_until 
                FROM users 
                WHERE user_id = %s
            ''', (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                is_premium, premium_until = result
                
                if is_premium and premium_until:
                    from datetime import datetime
                    
                    # Проверяем, истекла ли подписка
                    if isinstance(premium_until, str):
                        try:
                            expiry_date = datetime.strptime(premium_until[:19], '%Y-%m-%d %H:%M:%S')
                        except:
                            expiry_date = datetime.strptime(premium_until[:10], '%Y-%m-%d')
                    else:
                        expiry_date = premium_until
                    
                    if expiry_date < datetime.now():
                        # Подписка истекла - обновляем
                        cursor.execute('''
                            UPDATE users 
                            SET is_premium = FALSE, 
                                daily_cards_limit = %s,
                                premium_until = NULL
                            WHERE user_id = %s
                        ''', (DAILY_CARD_LIMIT_FREE, user_id))
                        
                        # Деактивируем подписку в таблице subscriptions
                        cursor.execute('''
                            UPDATE subscriptions 
                            SET is_active = FALSE 
                            WHERE user_id = %s 
                            AND is_active = TRUE
                        ''', (user_id,))
                        
                        conn.commit()
                        logging.info(f"✅ Subscription expired for user {user_id}, updated to free")
                        return True
            
            conn.close()
            return False
            
        except Exception as e:
            logging.error(f"❌ Error checking user subscription expiry: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def safe_db_operation(self, operation_func, *args, **kwargs):
        """Безопасно выполняет операцию с базой данных с повторными попытками"""
        import time
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return operation_func(*args, **kwargs)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if "SSL" in str(e) or "connection" in str(e).lower():
                    if attempt < max_retries - 1:
                        logging.warning(f"⚠️ Database SSL error on attempt {attempt + 1}: {e}")
                        time.sleep(1)
                        continue
                raise
            except Exception as e:
                raise
        
        raise Exception("Database operation failed after retries")

    def update_user_email(user_id: int, email: str):
        """Обновляет email пользователя в базе данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users 
                SET email = %s 
                WHERE user_id = %s
            ''', (email, user_id))
            
            conn.commit()
            logger.info(f"✅ Email updated for user {user_id}: {email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating user email: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

# Глобальный экземпляр для использования в других файлах
db = DatabaseManager()