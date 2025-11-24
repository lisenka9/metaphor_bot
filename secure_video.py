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
        
        # YouTube с оригинальными настройками
        self.youtube_url = "https://www.youtube.com/embed/qBqIO-_OsgA?autoplay=1&rel=0&modestbranding=1&showinfo=0&controls=0&disablekb=1&fs=0&iv_load_policy=3&playsinline=1&cc_load_policy=0&color=white&hl=ru&enablejsapi=1&widgetid=1"
        
        # RUTUBE - используем embed ссылку с минимальными параметрами
        self.rutube_url = "https://rutube.ru/play/embed/af23160e9d682ffcb8c9819e69fedd48"
        
        logging.info("🔧 Video system initialized")
    
    def generate_secure_link(self, user_id: int, platform: str = "youtube") -> str:
        """Генерирует защищенную ссылку"""
        try:
            # Определяем тип доступа
            subscription = self.db.get_user_subscription(user_id)
            has_subscription = False
            expires_at = None
            
            if subscription and subscription[1]:
                subscription_end = subscription[1]
                if hasattr(subscription_end, 'date'):
                    sub_date = subscription_end.date()
                else:
                    sub_date = subscription_end
                
                if sub_date >= datetime.now().date():
                    has_subscription = True
                    expires_at = datetime.combine(sub_date, datetime.max.time())
            
            # Генерируем уникальный хеш
            unique_string = f"{user_id}_{platform}_{secrets.token_hex(8)}_{datetime.now().timestamp()}"
            link_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:20]
            
            # Выбираем платформу
            video_url = self.youtube_url if platform == "youtube" else self.rutube_url
            
            # Сохраняем в базу данных
            success = self.db.save_video_link(
                link_hash, 
                user_id, 
                video_url, 
                expires_at,
                platform,
                has_subscription
            )
            
            if not success:
                logging.error("❌ Failed to save video link to database")
                return None
            
            logging.info(f"✅ Generated secure {platform} link for user {user_id}")
            
            # Возвращаем ссылку на наш защищенный плеер
            secure_url = f"{self.base_url}/secure-video/{link_hash}"
            return secure_url
            
        except Exception as e:
            logging.error(f"❌ Error generating secure link: {e}")
            return None

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