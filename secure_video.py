import hashlib
import secrets
import requests
import os
from datetime import datetime, timedelta
import logging

class SecureVideoSystem:
    def __init__(self, base_url, db):
        self.base_url = base_url
        self.db = db
        self.yandex_token = os.environ.get('YANDEX_DISK_TOKEN')
        self.meditation_path = "/meditation.MOV"
    
    def get_yandex_download_link(self) -> str:
        """Получает прямую ссылку на видео"""
        try:
            if not self.yandex_token:
                logging.error("❌ Yandex token not set")
                return None
                
            # Получаем информацию о файле
            response = requests.get(
                'https://cloud-api.yandex.net/v1/disk/resources',
                params={
                    'path': self.meditation_path,
                    'fields': 'public_url,file'
                },
                headers={'Authorization': f'OAuth {self.yandex_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                file_info = response.json()
                
                # Если файл публичный, используем публичную ссылку
                if file_info.get('public_url'):
                    public_url = file_info['public_url']
                    # Преобразуем в embed ссылку
                    return public_url.replace('/d/', '/embed/')
                
                # Если файл не публичный, получаем временную ссылку для скачивания
                download_response = requests.post(
                    'https://cloud-api.yandex.net/v1/disk/resources/download',
                    params={'path': self.meditation_path},
                    headers={'Authorization': f'OAuth {self.yandex_token}'},
                    timeout=10
                )
                
                if download_response.status_code == 200:
                    download_data = download_response.json()
                    return download_data['href']
                else:
                    logging.error(f"Download link error: {download_response.status_code}")
                    return None
                    
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
        expires_at = datetime.now() + timedelta(hours=1)  # По умолчанию 1 час
        
        if subscription and subscription[1]:
            subscription_end = subscription[1]
            if hasattr(subscription_end, 'date'):
                sub_date = subscription_end.date()
            else:
                sub_date = subscription_end
            
            if sub_date >= datetime.now().date():
                expires_at = datetime.combine(sub_date, datetime.max.time())
        
        # Генерируем уникальный хеш
        unique_string = f"{user_id}_{secrets.token_hex(8)}_{datetime.now().timestamp()}"
        link_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:20]
        
        # Получаем свежую ссылку на Яндекс Диск
        yandex_link = self.get_yandex_download_link()
        if not yandex_link:
            logging.error("❌ Failed to get Yandex download link")
            return None
        
        # Сохраняем в базу данных
        success = self.db.save_video_link(link_hash, user_id, yandex_link, expires_at)
        if not success:
            logging.error("❌ Failed to save video link to database")
            return None
        
        logging.info(f"✅ Generated secure link for user {user_id}, expires: {expires_at}")
        
        # Возвращаем ссылку на наш прокси
        return f"{self.base_url}/protected-video/{link_hash}"
    
    def validate_link(self, link_hash: str) -> tuple:
        """Проверяет валидность ссылки через базу данных"""
        link_data = self.db.get_video_link(link_hash)
        if not link_data:
            return False, None
        
        return True, link_data['yandex_link']

    def init_video_system(db):
        """Инициализирует систему видео (для обратной совместимости)"""
        try:
            from config import BASE_URL
            video_system = SecureVideoSystem(BASE_URL, db)
            logger.info("✅ Video system initialized")
            return video_system
        except Exception as e:
            logger.error(f"❌ Error initializing video system: {e}")
            return None

    