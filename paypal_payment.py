# paypal_payment.py
import logging
import uuid
import requests
import time
from datetime import datetime, timedelta
from threading import Thread
from database import db
from config import SUBSCRIPTION_DURATIONS, PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_PRICES

class PayPalPayment:
    def __init__(self):
        self.base_url = "https://api-m.paypal.com"  # Для продакшена
        # Для тестов используйте: "https://api-m.sandbox.paypal.com"
        self.access_token = None
        self.token_expires = None
        self.pending_payments = {}
        
    def get_access_token(self):
        """Получает access token для PayPal API"""
        try:
            # Если токен еще действителен, используем его
            if self.access_token and self.token_expires and datetime.now() < self.token_expires:
                return self.access_token
                
            auth = (PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "grant_type": "client_credentials"
            }
            
            response = requests.post(
                f"{self.base_url}/v1/oauth2/token",
                headers=headers,
                data=data,
                auth=auth,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                # Токен действителен 8 часов, устанавливаем время истечения на 7 часов
                self.token_expires = datetime.now() + timedelta(hours=7)
                logging.info("✅ PayPal access token получен")
                return self.access_token
            else:
                logging.error(f"❌ PayPal auth error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error getting PayPal access token: {e}")
            return None
    
    def create_payment(self, amount: float, description: str, user_id: int, subscription_type: str):
        """Создает платеж в ЮKassa"""
        try:
            # Проверяем наличие ключей ЮKassa
            if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
                logging.error("❌ YooKassa keys not configured")
                return None, None
                
            payment_id = str(uuid.uuid4())
            
            payload = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "payment_method_data": {
                    "type": "bank_card"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/MetaphorCardsSeaBot?start=payment_success"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": int(user_id),  
                    "subscription_type": subscription_type,
                    "payment_id": payment_id
                }
            }
            
            headers = {
                "Idempotence-Key": str(uuid.uuid4()),
                "Content-Type": "application/json"
            }
            
            logging.info(f"🔧 Creating YooKassa payment: amount={amount}, user_id={user_id}")
            
            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=headers,
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 200:
                payment_data = response.json()
                
                # Сохраняем информацию о платеже
                self.pending_payments[payment_id] = {
                    'user_id': user_id,
                    'subscription_type': subscription_type,
                    'yookassa_payment_id': payment_data['id'],
                    'status': payment_data['status'],
                    'created_at': datetime.now(),
                    'amount': amount
                }
                
                # Запускаем мониторинг
                self.start_payment_monitoring(payment_id)
                
                return payment_data['confirmation']['confirmation_url'], payment_id
            else:
                logging.error(f"❌ YooKassa API error: {response.status_code} - {response.text}")
                return None, None
                
        except Exception as e:
            logging.error(f"❌ Error creating YooKassa payment: {e}")
            return None, None
    
    def check_payment_status(self, payment_id: str):
        """Проверяет статус платежа через PayPal API"""
        try:
            if payment_id not in self.pending_payments:
                return False
                
            payment_info = self.pending_payments[payment_id]
            order_id = payment_info['paypal_order_id']
            access_token = self.get_access_token()
            
            if not access_token:
                return None
                
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(
                f"{self.base_url}/v2/checkout/orders/{order_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                order_data = response.json()
                status = order_data['status']
                
                # Обновляем статус в локальном хранилище
                self.pending_payments[payment_id]['status'] = status
                
                if status == 'COMPLETED':
                    return True
                elif status in ['CANCELLED', 'VOIDED', 'FAILED']:
                    return False
                else:
                    return None  # Платеж еще в процессе
            else:
                logging.error(f"❌ PayPal API check error: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error checking PayPal payment status: {e}")
            return None
    
    def capture_payment(self, order_id: str):
        """Подтверждает платеж (capture)"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
                
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
                json={},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logging.info(f"✅ PayPal payment captured: {order_id}")
                return True
            else:
                logging.error(f"❌ PayPal capture error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error capturing PayPal payment: {e}")
            return False
    
    def activate_subscription(self, payment_id: str):
        """Активирует подписку после успешной оплаты"""
        if payment_id not in self.pending_payments:
            return False
            
        payment_info = self.pending_payments[payment_id]
        user_id = payment_info['user_id']
        subscription_type = payment_info['subscription_type']
        
        # Активируем подписку в базе данных
        success = db.create_subscription(
            user_id, 
            subscription_type, 
            SUBSCRIPTION_DURATIONS[subscription_type]
        )
        
        if success:
            # Сохраняем информацию о платеже в базу
            self.save_payment_to_db(payment_info)
            
            # Удаляем из ожидающих платежей
            del self.pending_payments[payment_id]
            logging.info(f"✅ PayPal subscription activated for user {user_id}, type: {subscription_type}")
            return True
        
        return False
    
    def save_payment_to_db(self, payment_info: dict):
        """Сохраняет информацию о платеже в базу данных"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO payments (user_id, amount, subscription_type, status, payment_method, payment_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                payment_info['user_id'],
                payment_info['amount'],
                payment_info['subscription_type'],
                'success',
                'paypal',
                payment_info['paypal_order_id']
            ))
            
            conn.commit()
            conn.close()
            logging.info(f"✅ PayPal payment saved to database for user {payment_info['user_id']}")
            
        except Exception as e:
            logging.error(f"❌ Error saving PayPal payment to DB: {e}")
    
    def check_all_pending_payments(self):
        """Автоматически проверяет все ожидающие платежи"""
        completed_payments = []
        
        for payment_id, payment_info in list(self.pending_payments.items()):
            try:
                status = self.check_payment_status(payment_id)
                
                if status is True:
                    # Платеж успешен - активируем подписку
                    if self.activate_subscription(payment_id):
                        logging.info(f"✅ Auto-activated PayPal subscription for payment {payment_id}")
                        completed_payments.append(payment_id)
                elif status is False:
                    # Платеж не прошел - удаляем
                    logging.info(f"❌ PayPal payment failed: {payment_id}")
                    completed_payments.append(payment_id)
                    
            except Exception as e:
                logging.error(f"❌ Error checking PayPal payment {payment_id}: {e}")
        
        # Удаляем завершенные платежи
        for payment_id in completed_payments:
            if payment_id in self.pending_payments:
                del self.pending_payments[payment_id]

    def start_payment_monitoring(self, payment_id: str, max_checks: int = 60):
        """Запускает мониторинг платежа в отдельном потоке"""
        def monitor():
            checks = 0
            while checks < max_checks:
                try:
                    status = self.check_payment_status(payment_id)
                    
                    if status is True:
                        # Платеж успешен
                        if self.activate_subscription(payment_id):
                            logging.info(f"✅ PayPal payment confirmed and subscription activated: {payment_id}")
                        break
                    elif status is False:
                        # Платеж не прошел
                        logging.info(f"❌ PayPal payment failed: {payment_id}")
                        break
                    # Если status is None - платеж еще в процессе
                    
                except Exception as e:
                    logging.error(f"❌ Error in PayPal payment monitoring: {e}")
                
                time.sleep(30)  # Проверяем каждые 30 секунд
                checks += 1
            
            # Если платеж не подтвердился, очищаем
            if payment_id in self.pending_payments:
                logging.warning(f"⚠️ PayPal payment monitoring timeout: {payment_id}")
                del self.pending_payments[payment_id]
        
        thread = Thread(target=monitor)
        thread.daemon = True
        thread.start()

    def check_all_pending_payments(self):
        """Автоматически проверяет все ожидающие платежи"""
        completed_payments = []
        
        for payment_id, payment_info in list(self.pending_payments.items()):
            try:
                # Пропускаем платежи младше 2 минут (дают время на оплату)
                if datetime.now() - payment_info['created_at'] < timedelta(minutes=2):
                    continue
                    
                status = self.check_payment_status(payment_id)
                
                if status is True:
                    # Платеж успешен - активируем подписку
                    if self.activate_subscription(payment_id):
                        logging.info(f"✅ Auto-activated PayPal subscription for payment {payment_id}")
                        completed_payments.append(payment_id)
                elif status is False:
                    # Платеж не прошел - удаляем
                    logging.info(f"❌ PayPal payment failed: {payment_id}")
                    completed_payments.append(payment_id)
                    
            except Exception as e:
                logging.error(f"❌ Error checking PayPal payment {payment_id}: {e}")
        
        # Удаляем завершенные платежи
        for payment_id in completed_payments:
            if payment_id in self.pending_payments:
                del self.pending_payments[payment_id]

    def find_payment_by_order_id(self, order_id: str):
        """Находит платеж по order_id PayPal"""
        for payment_id, payment_info in self.pending_payments.items():
            if payment_info.get('paypal_order_id') == order_id:
                return payment_id, payment_info
        return None, None

    def activate_subscription_by_order_id(self, order_id: str):
        """Активирует подписку по order_id PayPal"""
        payment_id, payment_info = self.find_payment_by_order_id(order_id)
        if payment_id and payment_info:
            return self.activate_subscription(payment_id)
        return False

    def check_paypal_static_payments(self):
        """Проверяет статические PayPal платежи по базе данных"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Сначала обновляем структуру таблицы если нужно
            cursor.execute('''
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                WHERE table_name='payments' AND column_name='payment_method') THEN
                        ALTER TABLE payments ADD COLUMN payment_method TEXT DEFAULT 'yookassa';
                    END IF;
                END $$;
            ''')
            
            # Ищем платежи в базе данных по таблице payments
            cursor.execute('''
                SELECT p.user_id, p.subscription_type, p.payment_date, p.status 
                FROM payments p 
                WHERE p.payment_method = 'paypal' 
                AND p.status = 'success'
                AND p.payment_date >= NOW() - INTERVAL '10 minutes'
                AND NOT EXISTS (
                    SELECT 1 FROM subscriptions s 
                    WHERE s.user_id = p.user_id 
                    AND s.is_active = true 
                    AND s.end_date > NOW()
                )
            ''')
            
            new_payments = cursor.fetchall()
            conn.close()
            
            activated_count = 0
            for user_id, subscription_type, payment_date, status in new_payments:
                # Активируем подписку
                if self.activate_paypal_subscription(user_id, subscription_type):
                    activated_count += 1
                    logging.info(f"✅ Activated subscription from PayPal payment for user {user_id}")
            
            if activated_count > 0:
                logging.info(f"✅ Activated {activated_count} PayPal subscriptions")
                
            return activated_count
            
        except Exception as e:
            logging.error(f"❌ Error checking PayPal static payments: {e}")
            return 0

    def activate_paypal_subscription(self, user_id: int, subscription_type: str):
        """Активирует подписку для PayPal платежа"""
        try:
            if subscription_type not in SUBSCRIPTION_DURATIONS:
                return False
                
            # Активируем подписку в базе данных
            success = db.create_subscription(
                user_id, 
                subscription_type, 
                SUBSCRIPTION_DURATIONS[subscription_type]
            )
            
            if success:
                logging.info(f"✅ PayPal subscription activated for user {user_id}, type: {subscription_type}")
                
                # Отправляем уведомление пользователю
                self.send_paypal_success_notification(user_id, subscription_type)
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"❌ Error activating PayPal subscription: {e}")
            return False

    def send_paypal_success_notification(self, user_id: int, subscription_type: str):
        """Отправляет уведомление об успешной оплате PayPal"""
        try:
            from telegram import Bot
            from config import BOT_TOKEN
            
            bot = Bot(token=BOT_TOKEN)
            
            subscription_names = {
                "month": "1 месяц",
                "3months": "3 месяца", 
                "6months": "6 месяцев",
                "year": "1 год"
            }
            
            # Получаем информацию о подписке для даты окончания
            subscription = db.get_user_subscription(user_id)
            end_date_str = ""
            if subscription and subscription[1]:
                end_date = subscription[1]
                if hasattr(end_date, 'strftime'):
                    end_date_str = end_date.strftime('%d.%m.%Y')
                else:
                    end_date_str = str(end_date)[:10]
            
            message_text = f"""
    ✅ *Оплата подтверждена!*

    💎 Ваша премиум подписка "{subscription_names.get(subscription_type, '1 год')}" активирована.

    📅 Действует до: {end_date_str}

    ✨ Теперь вам доступны:
    • 5 карт дня вместо 1
    • Ежедневное послание дня  
    • Архипелаг ресурсов
    • Медитация «Дары Моря»

    Наслаждайтесь полным доступом! 💫
    """
            
            bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode='Markdown'
            )
            logging.info(f"✅ PayPal success notification sent to user {user_id}")
            
        except Exception as e:
            logging.error(f"❌ Error sending PayPal success notification: {e}")

    def start_paypal_monitoring(self):
        """Запускает автоматический мониторинг PayPal платежей"""
        def monitor():
            while True:
                try:
                    # Проверяем статические платежи каждые 30 секунд
                    activated_count = self.check_paypal_static_payments()
                    if activated_count > 0:
                        logging.info(f"✅ PayPal monitor: activated {activated_count} subscriptions")
                    
                    # Проверяем pending платежи через API
                    self.check_all_pending_payments()
                    
                except Exception as e:
                    logging.error(f"❌ Error in PayPal monitoring: {e}")
                
                time.sleep(30)  # Проверяем каждые 30 секунд
        
        thread = Thread(target=monitor)
        thread.daemon = True
        thread.start()

    def check_paypal_deck_payments(self):
        """Проверяет PayPal платежи за колоду по базе данных"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Ищем платежи за колоду в базе данных
            cursor.execute('''
                SELECT p.user_id, p.payment_date, p.status 
                FROM payments p 
                WHERE p.product_type = 'deck'
                AND p.payment_method = 'paypal'
                AND p.status = 'success'
                AND p.payment_date >= NOW() - INTERVAL '10 minutes'
                AND NOT EXISTS (
                    SELECT 1 FROM deck_purchases dp 
                    WHERE dp.user_id = p.user_id 
                    AND dp.status = 'completed'
                )
            ''')
            
            new_payments = cursor.fetchall()
            conn.close()
            
            activated_count = 0
            for user_id, payment_date, status in new_payments:
                # Активируем покупку колоды
                if self.activate_paypal_deck_purchase(user_id):
                    activated_count += 1
                    logging.info(f"✅ Activated deck purchase from PayPal payment for user {user_id}")
            
            if activated_count > 0:
                logging.info(f"✅ Activated {activated_count} PayPal deck purchases")
                
            return activated_count
            
        except Exception as e:
            logging.error(f"❌ Error checking PayPal deck payments: {e}")
            return 0

    def activate_paypal_deck_purchase(self, user_id: int):
        """Активирует покупку колоды для PayPal платежа"""
        try:
            # Записываем покупку в базу
            success = db.record_deck_purchase(user_id, f"paypal_{user_id}")
            
            if success:
                logging.info(f"✅ PayPal deck purchase activated for user {user_id}")
                
                # Отправляем уведомление пользователю
                self.send_paypal_deck_success_notification(user_id)
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"❌ Error activating PayPal deck purchase: {e}")
            return False

    def send_paypal_deck_success_notification(self, user_id: int):
        """Отправляет уведомление об успешной покупке колоды через PayPal"""
        try:
            from telegram import Bot
            from config import BOT_TOKEN
            
            bot = Bot(token=BOT_TOKEN)
            
            message_text = """
    ✅ *Оплата подтверждена!*

    Ваша цифровая колода «Настроение как море» успешно приобретена.

    📦 *Файлы отправляются...*
    """
            
            bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode='Markdown'
            )
            logging.info(f"✅ PayPal deck success notification sent to user {user_id}")
            
        except Exception as e:
            logging.error(f"❌ Error sending PayPal deck success notification: {e}")

# Глобальный экземпляр
paypal_processor = PayPalPayment()