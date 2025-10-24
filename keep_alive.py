import requests
import time
import os
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def ping_server():
    """Пингует сервер каждые 14 минут"""
    service_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://metaphor-bot.onrender.com')
    
    while True:
        try:
            response = requests.get(f"{service_url}/health", timeout=10)
            logger.info(f"✅ Ping successful: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Ping failed: {e}")
        
        # Ждем 14 минут (840 секунд)
        time.sleep(840)

if __name__ == '__main__':
    logger.info("🚀 Starting keep-alive service...")
    ping_server()
