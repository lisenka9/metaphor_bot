import logging
import uuid
import requests
import time
from urllib.parse import urlencode
from threading import Thread
from database import db
from config import SUBSCRIPTION_DURATIONS

class YooMoneyPayment:
    def __init__(self):
        self.base_url = "https://yoomoney.ru/quickpay/confirm.xml"
        self.api_url = "https://yoomoney.ru/api"
        self.pending_payments = {}  # Храним ожидающие платежи
    
    def create_payment_link(self, amount: float, label: str, receiver: str, payment_type: str = "AC", targets: str = "Оплата подписки"):
        """Создает прямую ссылку для оплаты"""
        
        bot_username = "MetaphorCardsSeaBot"  
        
        params = {
            'receiver': receiver,
            'quickpay-form': 'button',
            'targets': targets,
            'sum': amount,
            'paymentType': payment_type,
            'label': label,
            'successURL': f'https://t.me/{bot_username}?start=payment_{label}'
        }
        
        payment_url = f"{self.base_url}?{urlencode(params)}"
        return payment_url
    
    def generate_payment_label(self, user_id: int, subscription_type: str):
        """Генерирует уникальную метку для платежа"""
        unique_id = str(uuid.uuid4())[:8]
        label = f"sub_{user_id}_{subscription_type}_{unique_id}"
        
        # Сохраняем информацию о платеже
        self.pending_payments[label] = {
            'user_id': user_id,
            'subscription_type': subscription_type,
            'timestamp': time.time(),
            'checked': False
        }
        
        return label
    
    def check_payment_status(self, label: str):
        """Проверяет статус платежа (упрощенная версия)"""
        try:
            # В реальной реализации здесь будет запрос к API ЮMoney
            # Для демо считаем, что платеж прошел если метка существует
            
            if label in self.pending_payments:
                payment_info = self.pending_payments[label]
                
                # Имитируем проверку платежа
                # В реальности здесь будет запрос к API ЮMoney
                time.sleep(2)  # Имитация задержки проверки
                
                # Для демо - считаем что платеж всегда успешен
                return True
                
            return False
        except Exception as e:
            logging.error(f"Error checking payment: {e}")
            return False
    
    def activate_subscription(self, label: str):
        """Активирует подписку после успешной оплаты"""
        if label not in self.pending_payments:
            return False
            
        payment_info = self.pending_payments[label]
        user_id = payment_info['user_id']
        subscription_type = payment_info['subscription_type']
        
        # Активируем подписку в базе данных
        success = db.create_subscription(
            user_id, 
            subscription_type, 
            SUBSCRIPTION_DURATIONS[subscription_type]
        )
        
        if success:
            # Удаляем из ожидающих платежей
            del self.pending_payments[label]
            logging.info(f"Subscription activated for user {user_id}")
            return True
        
        return False
    
    def start_payment_monitoring(self, label: str, max_checks: int = 30):
        """Запускает мониторинг платежа в отдельном потоке"""
        def monitor():
            checks = 0
            while checks < max_checks:
                if self.check_payment_status(label):
                    if self.activate_subscription(label):
                        logging.info(f"Payment confirmed and subscription activated: {label}")
                    break
                
                time.sleep(10)  # Проверяем каждые 10 секунд
                checks += 1
            
            # Если платеж не подтвердился, очищаем
            if label in self.pending_payments:
                del self.pending_payments[label]
        
        thread = Thread(target=monitor)
        thread.daemon = True
        thread.start()

# Глобальный экземпляр
payment_processor = YooMoneyPayment()