import hashlib
import secrets
import requests
import os
from datetime import datetime, timedelta
import logging

# secure_video.py - обновим класс SecureVideoSystem

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
            
            # Для бесплатных пользователей НЕ устанавливаем время сразу
            # Время установится только при первом открытии ссылки
            if not has_subscription:
                # Проверяем, есть ли уже активный доступ
                access_info = self.db.get_meditation_access_info(user_id)
                if access_info and access_info.get('expires_at'):
                    expires_at = access_info['expires_at']
                else:
                    # Пока не устанавливаем время - будет установлено при первом открытии
                    expires_at = None
            
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
            
            logging.info(f"✅ Generated secure {platform} link for user {user_id}, has_subscription: {has_subscription}")
            
            # Возвращаем ссылку на наш защищенный плеер
            secure_url = f"{self.base_url}/secure-video/{link_hash}"
            return secure_url
            
        except Exception as e:
            logging.error(f"❌ Error generating secure link: {e}")
            return None

    def activate_meditation_access(self, user_id: int) -> bool:
        """Активирует доступ к медитации для бесплатных пользователей"""
        try:
            # Записываем факт просмотра
            self.db.record_meditation_watch(user_id)
            
            # Запускаем отсчет времени
            return self.db.start_meditation_access(user_id)
            
        except Exception as e:
            logging.error(f"❌ Error activating meditation access: {e}")
            return False