import logging
import uuid
import requests
import time
from datetime import datetime, timedelta
from threading import Thread
from database import db
from config import SUBSCRIPTION_DURATIONS, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

class YooKassaPayment:
    def __init__(self):
        self.base_url = "https://api.yookassa.ru/v3"
        self.pending_payments = {}  # Храним ожидающие платежи
        self.auth = (YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
    
    def create_payment(self, amount: float, description: str, user_id: int, subscription_type: str):
        """Создает платеж в ЮKassa"""
        try:
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
            
            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=headers,
                auth=self.auth,
                timeout=30
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
                
                return payment_data['confirmation']['confirmation_url'], payment_id
            else:
                logging.error(f"❌ YooKassa API error: {response.status_code} - {response.text}")
                return None, None
                
        except Exception as e:
            logging.error(f"❌ Error creating YooKassa payment: {e}")
            return None, None
    
    def check_payment_status(self, payment_id: str):
        """Проверяет статус платежа через API ЮKassa"""
        try:
            # Если payment_id есть в ожидающих - проверяем через API
            if payment_id in self.pending_payments:
                payment_info = self.pending_payments[payment_id]
                yookassa_payment_id = payment_info['yookassa_payment_id']
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                response = requests.get(
                    f"{self.base_url}/payments/{yookassa_payment_id}",
                    headers=headers,
                    auth=self.auth,
                    timeout=30
                )
                
                if response.status_code == 200:
                    payment_data = response.json()
                    status = payment_data['status']
                    
                    # Обновляем статус в локальном хранилище
                    self.pending_payments[payment_id]['status'] = status
                    
                    if status == 'succeeded':
                        return True
                    elif status in ['canceled', 'failed']:
                        return False
                    else:
                        return None  # Платеж еще в процессе
                else:
                    logging.error(f"❌ YooKassa API check error: {response.status_code}")
                    return None
            
            # ✅ ИСПРАВЛЕННАЯ ПРОВЕРКА ПЛАТЕЖЕЙ В БАЗЕ ДАННЫХ
            else:
                # Ищем платеж в базе данных по yoomoney_payment_id
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT status 
                    FROM payments 
                    WHERE yoomoney_payment_id = %s
                    ORDER BY payment_date DESC 
                    LIMIT 1
                ''', (payment_id,))  # ✅ Ищем по yoomoney_payment_id
                
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    status = result[0]
                    if status == 'success':
                        return True
                
                return False
                    
        except Exception as e:
            logging.error(f"❌ Error checking payment status: {e}")
            return None

    def find_user_payment(self, user_id: int):
        """Ищет платежи пользователя в базе данных"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT yoomoney_payment_id, status, subscription_type, payment_date
                FROM payments 
                WHERE user_id = %s 
                ORDER BY payment_date DESC 
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                yoomoney_payment_id, status, subscription_type, payment_date = result
                return {
                    'status': status,
                    'subscription_type': subscription_type,
                    'payment_date': payment_date
                }
            
            return None
            
        except Exception as e:
            logging.error(f"❌ Error finding user payment: {e}")
            return None

    def check_all_pending_payments(self):
        """Автоматически проверяет все ожидающие платежи"""
        completed_payments = []
        
        for payment_id, payment_info in list(self.pending_payments.items()):
            try:
                status = self.check_payment_status(payment_id)
                
                if status is True:
                    # Платеж успешен - активируем подписку
                    if self.activate_subscription(payment_id):
                        logging.info(f"✅ Auto-activated subscription for payment {payment_id}")
                        completed_payments.append(payment_id)
                elif status is False:
                    # Платеж не прошел - удаляем
                    logging.info(f"❌ Payment failed: {payment_id}")
                    completed_payments.append(payment_id)
                    
            except Exception as e:
                logging.error(f"❌ Error checking payment {payment_id}: {e}")
        
        # Удаляем завершенные платежи
        for payment_id in completed_payments:
            if payment_id in self.pending_payments:
                del self.pending_payments[payment_id]

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
            logging.info(f"✅ Subscription activated for user {user_id}, type: {subscription_type}")
            return True
        
        return False
    
    def save_payment_to_db(self, payment_info: dict):
        """Сохраняет информацию о платеже в базу данных"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO payments (user_id, amount, subscription_type, status, yoomoney_payment_id)
                VALUES (%s, %s, %s, %s, %s)
            ''', (
                payment_info['user_id'],
                payment_info['amount'],
                payment_info['subscription_type'],
                'success',
                payment_info['yookassa_payment_id']
            ))
            
            conn.commit()
            conn.close()
            logging.info(f"✅ Payment saved to database for user {payment_info['user_id']}")
            
        except Exception as e:
            logging.error(f"❌ Error saving payment to DB: {e}")
    
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
                            logging.info(f"✅ Payment confirmed and subscription activated: {payment_id}")
                        break
                    elif status is False:
                        # Платеж не прошел
                        logging.info(f"❌ Payment failed: {payment_id}")
                        break
                    # Если status is None - платеж еще в процессе
                    
                except Exception as e:
                    logging.error(f"❌ Error in payment monitoring: {e}")
                
                time.sleep(30)  # Проверяем каждые 30 секунд
                checks += 1
            
            # Если платеж не подтвердился, очищаем
            if payment_id in self.pending_payments:
                logging.warning(f"⚠️ Payment monitoring timeout: {payment_id}")
                del self.pending_payments[payment_id]
        
        thread = Thread(target=monitor)
        thread.daemon = True
        thread.start()

# Глобальный экземпляр
payment_processor = YooKassaPayment()