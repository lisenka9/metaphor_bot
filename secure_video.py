# secure_video.py
import hashlib
import secrets
import requests
import os
from datetime import datetime, timedelta
import logging

class SecureVideoSystem:
    def __init__(self, base_url, db):
        self.base_url = base_url  # URL вашего бота на Render
        self.db = db
        self.active_links = {}
        self.yandex_token = os.environ.get('YANDEX_DISK_TOKEN')
        self.meditation_path = "/meditation.MOV"  # Путь к видео на Яндекс Диске
    
    def get_yandex_download_link(self) -> str:
        """Получает временную ссылку для скачивания с Яндекс Диска"""
        try:
            response = requests.get(
                'https://cloud-api.yandex.net/v1/disk/resources/download',
                params={'path': self.meditation_path},
                headers={'Authorization': f'OAuth {self.yandex_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()['href']
            else:
                logging.error(f"Yandex Disk error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting Yandex link: {e}")
            return None
    
    def generate_secure_link(self, user_id: int) -> str:
        """Генерирует защищенную ссылку через прокси"""
        # Определяем срок действия
        subscription = self.db.get_user_subscription(user_id)
        has_active_subscription = False
        expires_at = datetime.now() + timedelta(hours=1)  # По умолчанию 1 час
        
        if subscription and subscription[1]:
            subscription_end = subscription[1]
            if hasattr(subscription_end, 'date'):
                sub_date = subscription_end.date()
            else:
                sub_date = subscription_end
            
            has_active_subscription = sub_date >= datetime.now().date()
            
            if has_active_subscription:
                expires_at = datetime.combine(sub_date, datetime.max.time())
        
        # Генерируем уникальный хеш
        unique_string = f"{user_id}_{secrets.token_hex(8)}_{datetime.now().timestamp()}"
        link_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:20]
        
        # Получаем свежую ссылку на Яндекс Диск
        yandex_link = self.get_yandex_download_link()
        if not yandex_link:
            logging.error("❌ Failed to get Yandex download link")
            return None
        
        # Сохраняем данные ссылки
        self.active_links[link_hash] = {
            'user_id': user_id,
            'expires_at': expires_at,
            'yandex_link': yandex_link,  # Временная ссылка Яндекс Диска
            'created_at': datetime.now(),
            'is_premium': has_active_subscription
        }
        
        logging.info(f"✅ Generated secure link for user {user_id}, expires: {expires_at}")
        
        # Возвращаем ссылку на наш прокси
        return f"{self.base_url}/protected-video/{link_hash}"
    
    def validate_link(self, link_hash: str) -> tuple:
        """Проверяет валидность ссылки и возвращает Яндекс ссылку"""
        if link_hash not in self.active_links:
            return False, None
        
        link_data = self.active_links[link_hash]
        
        # Проверяем срок действия
        if datetime.now() > link_data['expires_at']:
            del self.active_links[link_hash]
            return False, None
        
        return True, link_data['yandex_link']
    
    def cleanup_expired_links(self):
        """Очищает просроченные ссылки (можно вызывать периодически)"""
        current_time = datetime.now()
        expired_hashes = [
            hash for hash, data in self.active_links.items()
            if current_time > data['expires_at']
        ]
        
        for hash in expired_hashes:
            del self.active_links[hash]

# Глобальный экземпляр
video_system = None

def init_video_system(db):
    """Инициализирует систему защищенного видео"""
    global video_system
    try:
        from config import BASE_URL
        video_system = SecureVideoSystem(BASE_URL, db)
        logging.info("✅ Secure video system initialized successfully")
        return video_system
    except Exception as e:
        logging.error(f"❌ Error initializing video system: {e}")
        video_system = None
        return None

def get_video_system():
    """Возвращает глобальный экземпляр video_system"""
    global video_system
    return video_system