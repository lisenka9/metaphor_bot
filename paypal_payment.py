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
        """Создает платеж в PayPal"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None, None
            
            payment_id = str(uuid.uuid4())
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
                "PayPal-Request-Id": payment_id
            }
            
            payload = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": subscription_type,
                        "description": description,
                        "amount": {
                            "currency_code": "ILS",
                            "value": f"{amount:.2f}"
                        },
                        "custom_id": str(user_id)
                    }
                ],
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                            "brand_name": "Metaphor Cards Sea Bot",
                            "locale": "ru-RU",
                            "landing_page": "LOGIN",
                            "user_action": "PAY_NOW",
                            "return_url": f"https://t.me/MetaphorCardsSeaBot?start=paypal_success_{payment_id}",
                            "cancel_url": f"https://t.me/MetaphorCardsSeaBot?start=paypal_cancel"
                        }
                    }
                }
            }
            
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                order_data = response.json()
                
                # Сохраняем информацию о платеже
                self.pending_payments[payment_id] = {
                    'user_id': user_id,
                    'subscription_type': subscription_type,
                    'paypal_order_id': order_data['id'],
                    'status': order_data['status'],
                    'created_at': datetime.now(),
                    'amount': amount
                }
                
                # Запускаем автоматический мониторинг
                self.start_payment_monitoring(payment_id)
                
                # Находим ссылку для подтверждения
                for link in order_data.get('links', []):
                    if link.get('rel') == 'payer-action':
                        return link['href'], payment_id
                
                # Если нет payer-action, используем approve
                for link in order_data.get('links', []):
                    if link.get('rel') == 'approve':
                        return link['href'], payment_id
                        
                return None, None
            else:
                logging.error(f"❌ PayPal API error: {response.status_code} - {response.text}")
                return None, None
                
        except Exception as e:
            logging.error(f"❌ Error creating PayPal payment: {e}")
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
        
# Глобальный экземпляр
paypal_processor = PayPalPayment()