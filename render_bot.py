import os
import logging
import asyncio
import threading
import time
from flask import Flask

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "🌊 Metaphor Bot is running!"

@app.route('/health')
def health_check():
    return "✅ Bot is alive!", 200

def run_flask():
    """Запускает Flask сервер"""
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def run_bot_async():
    """Запускает бота асинхронно"""
    try:
        from bot import run_bot_with_restart
        await run_bot_with_restart()
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")

def run_bot():
    """Запускает бота в asyncio event loop"""
    try:
        asyncio.run(run_bot_async())
    except Exception as e:
        logger.error(f"❌ Bot event loop crashed: {e}")

if __name__ == '__main__':
    logger.info("🚀 Starting application on Render...")
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Даем Flask время на запуск
    time.sleep(5)
    
    # Запускаем бота в основном потоке
    run_bot()