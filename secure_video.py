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
        """Получает прямую ссылку на видео с Яндекс.Диска"""
        try:
            logging.info(f"🔍 Yandex token: {'✅ Set' if self.yandex_token else '❌ Not set'}")
            logging.info(f"🔍 Trying to get link for path: {self.meditation_path}")

            if not self.yandex_token:
                logging.error("❌ Yandex token not set")
                return None
                
            # Получаем информацию о файле
            file_info_response = requests.get(
                'https://cloud-api.yandex.net/v1/disk/resources',
                params={
                    'path': self.meditation_path,
                    'fields': 'public_url,file'
                },
                headers={'Authorization': f'OAuth {self.yandex_token}'},
                timeout=10
            )
            
            if file_info_response.status_code == 200:
                file_info = file_info_response.json()
                
                # Если файл публичный, используем прямую ссылку
                if file_info.get('public_url'):
                    public_url = file_info['public_url']
                    logging.info(f"✅ Using public URL: {public_url}")
                    return public_url
                
                # Если файл не публичный, получаем download ссылку
                download_response = requests.get(
                    'https://cloud-api.yandex.net/v1/disk/resources/download',
                    params={'path': self.meditation_path},
                    headers={'Authorization': f'OAuth {self.yandex_token}'},
                    timeout=10
                )
                
                if download_response.status_code == 200:
                    download_data = download_response.json()
                    direct_link = download_data.get('href')
                    
                    if direct_link:
                        logging.info(f"✅ Got direct download link: {direct_link[:50]}...")
                        return direct_link
                    else:
                        logging.error("❌ No href in download response")
                        return None
                else:
                    logging.error(f"❌ Download link error: {download_response.status_code}")
                    return None
            else:
                logging.error(f"❌ File info error: {file_info_response.status_code}")
                return None
                    
        except Exception as e:
            logging.error(f"❌ Error getting Yandex link: {e}")
            return None

    def generate_secure_link(self, user_id: int) -> str:
        """Генерирует защищенную ссылку через прокси"""
        try:
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
        
        except Exception as e:
            logging.error(f"❌ Error generating secure link: {e}")
            return None
    
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
        logging.info("✅ Video system initialized")
        return video_system
    except Exception as e:
        logging.error(f"❌ Error initializing video system: {e}")
        return None