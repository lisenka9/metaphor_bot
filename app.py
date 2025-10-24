from flask import Flask
import os
import requests
import time
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Metaphor Bot</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .status { color: green; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>🌊 Metaphor Bot</h1>
            <p>Status: <span class="status">✅ Running</span></p>
            <p>This is the web interface for the Metaphor Cards Telegram Bot.</p>
            <p>The bot is running as a separate worker process.</p>
        </body>
    </html>
    """

@app.route('/health')
def health_check():
    return "OK", 200

def keep_alive():
    """Пинг самого себя каждые 5 минут"""
    while True:
        try:
            url = "https://metaphor-bot.onrender.com/health"
            response = requests.get(url, timeout=10)
            print(f"✅ Health check: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
        time.sleep(300)  # 5 минут

if __name__ == '__main__':
    # Запускаем самопинг в отдельном потоке
    thread = threading.Thread(target=keep_alive)
    thread.daemon = True
    thread.start()
    
    # Запускаем Flask
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
