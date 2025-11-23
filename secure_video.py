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
        logging.info(f"🔧 Video system initialized with token: {'✅' if self.yandex_token else '❌'}")
    
    def get_yandex_download_link(self) -> str:
        """Ссылка на приватное YouTube видео"""
        youtube_id = "qBqIO-_OsgA"  
        params = [
            "autoplay=1",           # Автозапуск
            "rel=0",                # Не показывать похожие видео
            "modestbranding=1",     # Минимум логотипов YouTube
            "showinfo=0",           # Скрыть заголовок и информацию о канале
            "controls=1",           # Показать элементы управления (пауза, громкость)
            "disablekb=1",          # Отключить клавиатурные shortcuts
            "fs=1",                 # Разрешить полноэкранный режим
            "iv_load_policy=3",     # Скрыть аннотации
            "playsinline=1"         # Воспроизведение в окне на iOS
        ]
        return f"https://www.youtube.com/embed/{youtube_id}?{'&'.join(params)}"

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
            
            # Возвращаем ссылку на наш защищенный плеер
            secure_url = f"{self.base_url}/secure-video/{link_hash}"
            logging.info(f"🔗 Secure URL: {secure_url}")
            return secure_url
        
        except Exception as e:
            logging.error(f"❌ Error generating secure link: {e}")
            return None
    
    def validate_link(self, link_hash: str) -> tuple:
        """Проверяет валидность ссылки через базу данных"""
        link_data = self.db.get_video_link(link_hash)
        if not link_data:
            return False, None
        
        return True, link_data['yandex_link']

def get_video_system_safe():
    """Безопасно получает video_system"""
    try:
        from config import BASE_URL
        from database import db
        
        video_system = SecureVideoSystem(BASE_URL, db)
        logging.info("✅ Video system created successfully")
        return video_system
    except Exception as e:
        logging.error(f"❌ Error creating video system: {e}")
        return None