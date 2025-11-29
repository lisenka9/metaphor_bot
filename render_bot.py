import os
import logging
import multiprocessing
import time
import threading
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

def run_bot():
    """Запускает бота в отдельном процессе"""
    try:
        # Импортируем здесь, чтобы избежать конфликтов
        from bot import run_bot_with_restart
        import asyncio
        
        # Запускаем бота
        asyncio.run(run_bot_with_restart())
    except Exception as e:
        logger.error(f"❌ Bot process crashed: {e}")

def start_background_processes():
    """Запускает фоновые процессы"""
    try:
        # Запускаем бота в отдельном процессе
        bot_process = multiprocessing.Process(target=run_bot, name="BotProcess")
        bot_process.daemon = True
        bot_process.start()
        logger.info("✅ Bot process started")
        
        # Мониторинг процессов
        while True:
            time.sleep(10)
            if not bot_process.is_alive():
                logger.error("❌ Bot process died, restarting...")
                bot_process = multiprocessing.Process(target=run_bot, name="BotProcess")
                bot_process.daemon = True
                bot_process.start()
                logger.info("✅ Bot process restarted")
                
    except Exception as e:
        logger.error(f"❌ Error in background processes: {e}")

if __name__ == '__main__':
    logger.info("🚀 Starting application on Render...")
    
    # Запускаем фоновые процессы в отдельном потоке
    background_thread = threading.Thread(target=start_background_processes, daemon=True)
    background_thread.start()
    
    # Запускаем Flask в основном процессе (как требует Render)
    run_flask()