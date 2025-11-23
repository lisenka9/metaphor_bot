import hashlib
import hmac
import time

class SecureVideoSystem:
    def __init__(self, base_url, db):
        self.base_url = base_url
        self.db = db
        self.secret_key = os.environ.get('VIDEO_SECRET_KEY', 'your-secret-key-change-in-production')
    
    def generate_secure_token(self, user_id: int, expires_in: int = 3600) -> str:
        """Генерирует токен для доступа к видео"""
        timestamp = str(int(time.time()) + expires_in)
        data = f"{user_id}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{data}:{signature}"
    
    def verify_token(self, token: str) -> tuple:
        """Проверяет токен и возвращает user_id если валиден"""
        try:
            data, signature = token.rsplit(':', 1)
            user_id, timestamp = data.split(':', 1)
            
            # Проверяем подпись
            expected_signature = hmac.new(
                self.secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None, "Invalid signature"
            
            # Проверяем срок действия
            if int(time.time()) > int(timestamp):
                return None, "Token expired"
            
            return int(user_id), "Valid"
            
        except Exception as e:
            return None, f"Token error: {str(e)}"
    
    def get_video_url(self, user_id: int) -> str:
        """Генерирует защищенную ссылку на видео"""
        token = self.generate_secure_token(user_id)
        return f"{self.base_url}/protected-video/{token}"

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
            
            # Сохраняем в базу данных
            success = self.db.save_video_link(link_hash, user_id, "protected", expires_at)
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