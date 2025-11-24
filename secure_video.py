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
            # [остальной код без изменений]
            # ... ваш существующий код ...
            
        except Exception as e:
            logging.error(f"❌ Error generating secure link: {e}")
            return None