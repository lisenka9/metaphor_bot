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
        self.youtube_url = "https://www.youtube.com/embed/qBqIO-_OsgA?autoplay=1&rel=0&modestbranding=1&showinfo=0&controls=0&disablekb=1&fs=0&iv_load_policy=3&playsinline=1&cc_load_policy=0&color=white&hl=ru&enablejsapi=1&widgetid=1"
        self.rutube_url = "https://rutube.ru/video/private/af23160e9d682ffcb8c9819e69fedd48/?p=1p2eMSt-NHUeMHLo32SLcQ"
        logging.info("🔧 Video system initialized with YouTube and RUTUBE links")
    
    def generate_secure_link(self, user_id: int, platform: str = "youtube", base_hash: str = None) -> str:
        """Генерирует защищенную ссылку с общим идентификатором доступа"""
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
            
            # Используем общий base_hash или создаем новый
            if not base_hash:
                base_hash = hashlib.sha256(f"{user_id}_{secrets.token_hex(8)}".encode()).hexdigest()[:16]
            
            # Создаем уникальный хеш для каждой платформы, но с общим base_hash
            unique_string = f"{base_hash}_{platform}_{user_id}"
            link_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:20]
            
            # Выбираем платформу
            video_url = self.youtube_url if platform == "youtube" else self.rutube_url
            
            # Сохраняем в базу данных с информацией о платформе и общем идентификаторе
            success = self.db.save_video_link(
                link_hash, 
                user_id, 
                video_url, 
                expires_at,
                platform,
                has_subscription,
                base_hash  # Передаем общий идентификатор
            )
            
            if not success:
                logging.error("❌ Failed to save video link to database")
                return None
            
            logging.info(f"✅ Generated secure {platform} link for user {user_id}, base_hash: {base_hash}")
            
            # Возвращаем ссылку на наш защищенный плеер
            secure_url = f"{self.base_url}/secure-video/{link_hash}"
            return secure_url
        
        except Exception as e:
            logging.error(f"❌ Error generating secure link: {e}")
            return None

    def validate_link(self, link_hash: str) -> tuple:
        """Проверяет валидность ссылки и устанавливает время начала для бесплатных пользователей"""
        link_data = self.db.get_video_link(link_hash)
        if not link_data:
            return False, None
        
        # Если у пользователя нет подписки и время еще не установлено, устанавливаем его
        if not link_data['has_subscription'] and not link_data['access_started_at']:
            success = self.db.start_video_access(link_hash)
            if not success:
                return False, None
        
        return True, link_data

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