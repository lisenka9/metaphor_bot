import logging
import os
import time
import json
import requests
import threading
from flask import Flask, request, jsonify, redirect, Response, stream_with_context
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import BOT_TOKEN, PAYPAL_WEBHOOK_ID, SUBSCRIPTION_DURATIONS
import handlers
from database import db
from yookassa_payment import payment_processor  
import logging

import multiprocessing
import signal
import sys
from datetime import datetime, timedelta
from telegram import Update


import signal
import sys
import asyncio
from threading import Event

import signal
import sys
import asyncio
import multiprocessing
import time
from threading import Event
from telegram import Bot

class GracefulShutdown:
    def __init__(self):
        self.shutdown_event = threading.Event()
        
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"🛑 Received shutdown signal {signum}. Starting graceful shutdown...")
        self.shutdown_event.set()
        
        # Уведомляем администраторов
        self.notify_admins_about_shutdown(signum)
    
    def notify_admins_about_shutdown(self, signum):
        """Уведомляет администраторов о shutdown"""
        try:
            from telegram import Bot
            from config import BOT_TOKEN, ADMIN_IDS
            
            bot = Bot(token=BOT_TOKEN)
            message = f"🛑 Bot received shutdown signal {signum} at {datetime.now()}"
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(chat_id=admin_id, text=message)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Could not send shutdown notification: {e}")

# Глобальный экземпляр
shutdown_manager = GracefulShutdown()
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем Flask приложение
app = Flask(__name__)

@app.route('/')
def home():
    return "🌊 Metaphor Bot is running!"

@app.route('/health')
def health_check():
    return "✅ Bot is alive!", 200

@app.route('/payment_callback', methods=['POST'])
def payment_callback():
    """Обрабатывает уведомления от ЮKassa"""
    try:
        # Получаем JSON данные
        event_json = request.get_json()
        logger.info(f"📨 Received YooKassa webhook: {event_json}")

        if not event_json:
            logger.error("❌ Empty webhook data received")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Проверяем тип события
        event_type = event_json.get('type')
        if event_type == 'notification':
            # Обрабатываем уведомление о платеже
            return handle_payment_notification(event_json)
        elif event_type == 'payment.waiting_for_capture':
            # Платеж ожидает подтверждения
            logger.info("⏳ Payment waiting for capture")
            return jsonify({"status": "success"}), 200
        else:
            logger.warning(f"⚠️ Unknown event type: {event_type}")
            return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"❌ Error in payment callback: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/secure-video/<link_hash>')
def secure_video_player(link_hash):
    """Безопасный видео-плеер с ограниченным доступом"""
    try:
        logging.info(f"🔧 Secure video requested for hash: {link_hash}")
        link_data = db.get_video_link(link_hash)
        
        if not link_data:
            logging.error(f"❌ Link not found: {link_hash}")
            return """
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Ссылка недействительна</h2>
                    <p>Вернитесь в бота для получения новой ссылки.</p>
                    <a href="https://t.me/MetaphorCardsSeaBot">Вернуться в бота</a>
                </body>
            </html>
            """, 404
        
        user_id = link_data['user_id']
        platform = link_data['platform']
        has_subscription = link_data['has_subscription']
        
        # Для бесплатных пользователей активируем доступ при первом открытии
        if not has_subscription:
            try:
                # Создаем video_system напрямую
                from secure_video import SecureVideoSystem
                from config import BASE_URL
                video_system = SecureVideoSystem(BASE_URL, db)
                if video_system:
                    video_system.activate_meditation_access(user_id)
            except Exception as e:
                logging.error(f"❌ Error activating meditation access: {e}")
        
        # Проверяем срок действия
        if link_data['expires_at'] and datetime.now() > link_data['expires_at']:
            logging.info(f"❌ Link expired: {link_hash}")
            db.cleanup_expired_video_links()
            return """
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Срок действия ссылки истёк</h2>
                    <p>Получите новую ссылку в боте.</p>
                    <a href="https://t.me/MetaphorCardsSeaBot">Вернуться в бота</a>
                </body>
            </html>
            """, 403
        
        video_url = link_data['video_url']
        
        # Для YouTube используем оригинальный подход со сдвигом
        # Для RUTUBE используем обычное отображение с усиленным скрытием элементов
        is_youtube = platform == "youtube"
        
        if is_youtube:
            iframe_style = "position: absolute; top: -60px; left: 0; width: 100%; height: calc(100% + 120px); border: none;"
        else:
            iframe_style = "position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Медитация «Дары Моря»</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{
                    background: white;
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    max-width: 800px;
                    width: 90%;
                    text-align: center;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 20px;
                }}
                .video-wrapper {{
                    position: relative;
                    width: 100%;
                    margin: 20px 0;
                    overflow: hidden;
                    border-radius: 10px;
                    background: #000;
                }}
                .video-container {{
                    position: relative;
                    width: 100%;
                    height: 0;
                    padding-bottom: 56.25%;
                    background: #000;
                    overflow: hidden;
                }}
                .video-mask {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: 100;
                    background: linear-gradient(to bottom, rgba(0,0,0,0.9) 0%, transparent 80px, transparent calc(100% - 80px), rgba(0,0,0,0.9) 100%);
                }}
                .btn {{
                    background: #667eea;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: bold;
                    margin: 10px;
                    display: inline-block;
                }}
                .platform-badge {{
                    background: #667eea;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 14px;
                    margin-bottom: 15px;
                    display: inline-block;
                }}
                
                /* Стили для скрытия элементов RUTUBE */
                .rutube-overlay {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: 50;
                    pointer-events: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🐚 Медитация «Дары Моря»</h1>
                <div class="platform-badge">{platform.upper()}</div>
                
                <div class="video-wrapper">
                    <div class="video-container">
                        <iframe src="{video_url}" 
                            style="{iframe_style}"
                            frameborder="0" 
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                            allowfullscreen
                            id="video-player">
                        </iframe>
                        <div class="video-mask"></div>
                        <div class="rutube-overlay"></div>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <a href="https://t.me/MetaphorCardsSeaBot" class="btn">Вернуться в бота</a>
                </div>
            </div>
            
            <script>
            // Скрываем элементы YouTube
            function hideYouTubeElements() {{
                const style = document.createElement('style');
                style.textContent = `
                    .ytp-chrome-top,
                    .ytp-title-link,
                    .ytp-title-channel,
                    .ytp-share-button,
                    .ytp-copylink-button,
                    .ytp-show-cards-title,
                    .ytp-pause-overlay,
                    .ytp-youtube-button,     
                    .ytp-button.ytp-youtube-button {{  
                        display: none !important;
                        opacity: 0 !important;
                        visibility: hidden !important;
                    }}
                    .ytp-watermark {{
                        display: none !important;
                        opacity: 0 !important;
                        visibility: hidden !important;
                    }}
                    
                    .ytp-chrome-top {{
                        height: 0 !important;
                        min-height: 0 !important;
                        padding: 0 !important;
                    }}
                `;
                document.head.appendChild(style);
            }}
            
            // Усиленное скрытие элементов RUTUBE
            function hideRutubeElements() {{
                // Добавляем стили для полного скрытия
                const style = document.createElement('style');
                style.textContent = `
                    /* Скрываем ВСЕ возможные элементы RUTUBE */
                    [class*="control"],
                    [class*="panel"],
                    [class*="button"],
                    [class*="logo"],
                    [class*="watermark"],
                    [class*="header"],
                    [class*="footer"],
                    [class*="toolbar"],
                    [class*="menu"],
                    [id*="control"],
                    [id*="panel"],
                    [id*="button"],
                    [id*="logo"],
                    .video-controls,
                    .player-controls,
                    .controls-panel,
                    .top-panel,
                    .bottom-panel,
                    .rutube-player__controls,
                    .video-controls__panel,
                    .logo,
                    .rutube-logo,
                    .player-logo,
                    .watermark {{
                        display: none !important;
                        opacity: 0 !important;
                        visibility: hidden !important;
                        pointer-events: none !important;
                    }}
                    
                    /* Скрываем overlay элементы */
                    .video-page__control-panel,
                    .video-controls,
                    .video-page__header,
                    .video-page__footer {{
                        display: none !important;
                    }}
                    
                    /* Делаем iframe на весь экран */
                    body, html {{
                        margin: 0 !important;
                        padding: 0 !important;
                        overflow: hidden !important;
                    }}
                    
                    .video-container, .video-wrapper {{
                        border: none !important;
                        outline: none !important;
                    }}
                `;
                document.head.appendChild(style);
                
                // Агрессивное скрытие через JavaScript
                function aggressivelyHideRutube() {{
                    // Скрываем все элементы с определенными классами/ID
                    const selectors = [
                        '[class*="control"]', '[class*="panel"]', '[class*="button"]',
                        '[class*="logo"]', '[class*="watermark"]', '[class*="header"]',
                        '[class*="footer"]', '[class*="toolbar"]', '[class*="menu"]',
                        '[id*="control"]', '[id*="panel"]', '[id*="button"]', '[id*="logo"]',
                        '.video-controls', '.player-controls', '.controls-panel',
                        '.top-panel', '.bottom-panel', '.rutube-player__controls',
                        '.video-controls__panel', '.logo', '.rutube-logo', '.player-logo',
                        '.watermark', '.video-page__control-panel', '.video-page__header',
                        '.video-page__footer'
                    ];
                    
                    selectors.forEach(selector => {{
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {{
                            if (el) {{
                                el.style.display = 'none';
                                el.style.opacity = '0';
                                el.style.visibility = 'hidden';
                                el.style.pointerEvents = 'none';
                                el.remove(); // Полностью удаляем элемент
                            }}
                        }});
                    }});
                    
                    // Скрываем элементы внутри iframe
                    const iframe = document.getElementById('video-player');
                    if (iframe && iframe.contentDocument) {{
                        selectors.forEach(selector => {{
                            const elements = iframe.contentDocument.querySelectorAll(selector);
                            elements.forEach(el => {{
                                if (el) {{
                                    el.style.display = 'none';
                                    el.style.opacity = '0';
                                    el.style.visibility = 'hidden';
                                    el.style.pointerEvents = 'none';
                                }}
                            }});
                        }});
                    }}
                }}
                
                // Запускаем агрессивное скрытие несколько раз
                aggressivelyHideRutube();
                setTimeout(aggressivelyHideRutube, 1000);
                setTimeout(aggressivelyHideRutube, 3000);
                setInterval(aggressivelyHideRutube, 5000);
            }}
            
            // Определяем платформу и применяем скрипт
            function initVideoPlayer() {{
                const iframe = document.getElementById('video-player');
                if (!iframe) return;
                
                const iframeSrc = iframe.src;
                
                if (iframeSrc.includes('youtube')) {{
                    setTimeout(hideYouTubeElements, 2000);
                    setInterval(hideYouTubeElements, 5000);
                }} else if (iframeSrc.includes('rutube')) {{
                    setTimeout(hideRutubeElements, 1000);
                    setInterval(hideRutubeElements, 3000);
                }}
            }}
            
            // Запускаем при загрузке
            document.getElementById('video-player').addEventListener('load', initVideoPlayer);
            setTimeout(initVideoPlayer, 1000);
            
            // Скрываем при любом взаимодействии
            document.addEventListener('click', initVideoPlayer);
            document.addEventListener('mousemove', initVideoPlayer);
            document.addEventListener('touchstart', initVideoPlayer);
            </script>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        logging.error(f"❌ Error in secure video: {e}")
        return "❌ Ошибка загрузки видео", 500

@app.route('/paypal_webhook', methods=['POST'])
def paypal_webhook():
    """Обрабатывает вебхуки от PayPal с ВЕРИФИКАЦИЕЙ"""
    try:
        # Логируем ВСЕ входящие данные
        logging.info("=" * 50)
        logging.info("📨 PAYPAL WEBHOOK RECEIVED")
        logging.info(f"📋 Headers: {dict(request.headers)}")
        logging.info(f"📦 Raw data: {request.get_data(as_text=True)}")
        
        # Пробуем парсить JSON
        event_json = request.get_json()
        if event_json:
            logging.info(f"🔍 Parsed JSON: {event_json}")
        else:
            logging.error("❌ Cannot parse JSON from webhook")
        # Получаем данные вебхука
        event_json = request.get_json()
        
        # ✅ ВКЛЮЧАЕМ ПРОВЕРКУ ПОДПИСИ (важно для безопасности!)
        if not verify_paypal_webhook(request):
            logging.error("❌ Invalid PayPal webhook signature - possible fraud!")
            return jsonify({"status": "error", "message": "Invalid signature"}), 400
        
        logging.info(f"📨 Verified PayPal webhook: {event_json.get('event_type')}")
        
        event_type = event_json.get('event_type')
        resource = event_json.get('resource', {})
        
        # Обрабатываем ТОЛЬКО подтвержденные платежи
        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            return handle_paypal_payment_completed(resource)
        elif event_type == 'CHECKOUT.ORDER.COMPLETED':
            return handle_paypal_order_completed(resource)
        
        # Для других событий просто подтверждаем получение
        logging.info(f"🔧 Unhandled but verified PayPal event: {event_type}")
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"❌ Error in PayPal webhook: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/health-detailed')
def health_detailed():
    """Детальная проверка здоровья для Render"""
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "flask": "running",
            "database": "unknown",
            "telegram_bot": "unknown"
        }
    }
    
    try:
        # Проверка базы данных
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        health_data["components"]["database"] = "healthy"
        conn.close()
    except Exception as e:
        health_data["components"]["database"] = f"unhealthy: {str(e)}"
        health_data["status"] = "degraded"
    
    # Проверка бота (косвенная)
    try:
        # Попытка получить информацию о боте
        import requests
        bot_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(bot_url, timeout=10)
        if response.status_code == 200:
            health_data["components"]["telegram_bot"] = "healthy"
        else:
            health_data["components"]["telegram_bot"] = f"unhealthy: {response.status_code}"
            health_data["status"] = "unhealthy"
    except Exception as e:
        health_data["components"]["telegram_bot"] = f"unhealthy: {str(e)}"
        health_data["status"] = "unhealthy"
    
    return jsonify(health_data), 200 if health_data["status"] == "healthy" else 503

@app.route('/readiness')
def readiness_check():
    """Проверка готовности для Load Balancer"""
    try:
        # Быстрая проверка базы данных
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        return "✅ Ready", 200
    except Exception as e:
        return f"❌ Not Ready: {str(e)}", 503

@app.route('/paypal_deck_webhook', methods=['POST'])
def paypal_deck_webhook():
    """Обрабатывает вебхуки от PayPal для покупки колоды"""
    try:
        # Получаем JSON данные
        event_json = request.get_json()
        logger.info(f"📨 Received PayPal deck webhook: {event_json}")
        
        if not event_json:
            logger.error("❌ Empty webhook data received")
            return jsonify({"status": "error", "message": "No data received"}), 400
        
        # Проверяем тип события
        event_type = event_json.get('event_type')
        resource = event_json.get('resource', {})
        
        logger.info(f"🔧 PayPal deck webhook event: {event_type}")
        
        # Обрабатываем события покупки колоды
        if event_type in ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.COMPLETED']:
            return handle_paypal_deck_payment_completed(resource)
        
        logger.info(f"🔧 Unhandled PayPal deck webhook event: {event_type}")
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in PayPal deck webhook: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/paypal_webhook_test', methods=['GET', 'POST'])
def paypal_webhook_test():
    """Тестовый endpoint для проверки доступности"""
    if request.method == 'GET':
        return "✅ PayPal webhook endpoint is accessible", 200
    else:
        # Симулируем вебхук для тестирования
        test_data = {
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "custom_id": "user_123456",
                "amount": {"value": "35.00"},
                "status": "COMPLETED"
            }
        }
        return jsonify(test_data), 200

def handle_paypal_deck_payment_completed(resource):
    """Обрабатывает завершенный платеж за колоду"""
    try:
        purchase_units = resource.get('purchase_units', [])
        
        if not purchase_units:
            return jsonify({"status": "success"}), 200
            
        purchase_unit = purchase_units[0]
        custom_id = purchase_unit.get('custom_id')
        amount = purchase_unit.get('amount', {}).get('value')
        
        logger.info(f"🔧 PayPal deck payment completed: custom_id={custom_id}, amount={amount}")
        
        # Если amount соответствует цене колоды (80₪)
        if amount == "80.00":
            # Ищем пользователя по custom_id или другим данным
            user_id = find_user_from_paypal_payment(resource)
            
            if user_id:
                # Активируем покупку колоды
                from paypal_payment import paypal_processor
                if paypal_processor.activate_paypal_deck_purchase(user_id):
                    logger.info(f"✅ PayPal deck purchase activated via webhook for user {user_id}")
                    
                    # Обновляем статус платежа в базе
                    update_payment_status_for_deck(user_id, 'success')
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error handling PayPal deck payment completed: {e}")
        return jsonify({"status": "error"}), 500

def update_payment_status_for_deck(user_id: int, status: str):
    """Обновляет статус платежа за колоду"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE payments 
            SET status = %s, product_type = 'deck'
            WHERE user_id = %s 
            AND payment_method = 'paypal'
            AND status = 'pending'
            AND amount = 80.00
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (status, user_id))
        
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        if updated > 0:
            logging.info(f"✅ PayPal deck payment status updated to {status} for user {user_id}")
        else:
            logging.warning(f"⚠️ No pending PayPal deck payment found for user {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Error updating PayPal deck payment status: {e}")

def send_deck_files_async(user_id: int):
    """Асинхронно отправляет файлы колоды пользователю"""
    import threading
    
    def send_files():
        try:
            # Импортируем здесь чтобы избежать циклических импортов
            from telegram import Bot
            from config import BOT_TOKEN
            
            bot = Bot(token=BOT_TOKEN)
            
            # Отправляем файлы
            file_ids = {
                "zip": "BQACAgIAAxkBAAILH2ka8spSoCXJz_jB1wFckPfGYkSXAAKNgQACUSbYSEhUWdaRMfa5NgQ",
                "rar": "BQACAgIAAxkBAAILIWka8yBQZpQQw23Oj4rIGSF_zNYAA5KBAAJRJthIJUVWWMwVvMg2BA",
                "pdf": "BQACAgIAAxkBAAILF2ka8jBpiM0_cTutmYhXeGoZs4PJAAJ1gQACUSbYSAUgICe9H14nNgQ"
            }
            
            success_text = """
✅ *Спасибо за покупку!*

Ваша цифровая колода «Настроение как море» готова к скачиванию.

📦 *Файлы отправляются...*
"""
            
            bot.send_message(chat_id=user_id, text=success_text, parse_mode='Markdown')
            
            # ZIP файл
            bot.send_document(
                chat_id=user_id,
                document=file_ids["zip"],
                filename="Ограничения.zip",
                caption="📦 Архив с картами (ZIP формат)"
            )
            
            # RAR файл
            bot.send_document(
                chat_id=user_id,
                document=file_ids["rar"],
                filename="Возможности.rar",
                caption="📦 Архив с картами (RAR формат)"
            )
            
            # PDF файл
            bot.send_document(
                chat_id=user_id,
                document=file_ids["pdf"],
                filename="Колода_Настроение_как_море_методическое_пособие.pdf",
                caption="📚 Методическое пособие с посланиями"
            )
            
            final_text = """
🎉 *Поздравляем с приобретением колоды!*

Теперь у вас есть полный доступ ко всем картам и методическим материалам.

💫 Приятного использования!
"""
            
            bot.send_message(
                chat_id=user_id,
                text=final_text,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Deck files sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending deck files to user {user_id}: {e}")
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=send_files)
    thread.daemon = True
    thread.start()

def handle_paypal_payment_completed(resource):
    """Обрабатывает подтвержденный платеж PayPal (captured)"""
    try:
        custom_id = resource.get('custom_id')
        amount = resource.get('amount', {}).get('value')
        currency = resource.get('amount', {}).get('currency_code', 'ILS')
        
        logging.info(f"🔧 PayPal payment captured: custom_id={custom_id}, amount={amount} {currency}")
        
        # Проверяем, что платеж действительно подтвержден
        status = resource.get('status')
        if status != 'COMPLETED':
            logging.warning(f"⚠️ PayPal payment not completed: status={status}")
            return jsonify({"status": "success"}), 200
        
        # Определяем тип продукта
        product_type = "subscription"
        if amount == "80.00" and currency == "ILS":
            product_type = "deck"
        
        # Ищем пользователя
        user_id = None
        if custom_id and custom_id.startswith('user_'):
            user_id = int(custom_id.replace('user_', ''))
        
        if not user_id:
            # Пробуем найти по другим данным
            payer = resource.get('payer', {})
            email = payer.get('email_address')
            if email:
                user_id = find_user_by_email(email)
        
        if user_id and amount:
            # Определяем тип продукта по сумме
            if amount == "80.00" and currency == "ILS":  # Колода
                from paypal_payment import paypal_processor
                if paypal_processor.activate_paypal_deck_purchase(user_id):
                    logging.info(f"✅ PayPal deck purchase activated via webhook for user {user_id}")
                    
                    # Отправляем уведомление администратору
                    send_admin_notification_successful(user_id, amount, currency, "deck", 
                                                      resource.get('id', 'unknown'), 
                                                      payer.get('email_address', 'не указан'), "PayPal")
                    
                    # Отправляем файлы пользователю (асинхронно)
                    send_deck_files_async(user_id)
            else:
                # Это подписка
                subscription_type = determine_subscription_type_from_paypal(amount)
                
                if subscription_type:
                    # ✅ Активируем подписку ТОЛЬКО при подтвержденном платеже
                    success = db.create_subscription(
                        user_id, 
                        subscription_type, 
                        SUBSCRIPTION_DURATIONS[subscription_type]
                    )
                    
                    if success:
                        logging.info(f"✅ PayPal subscription activated via webhook for user {user_id}")
                        
                        # Обновляем статус платежа в базе
                        update_paypal_payment_status_in_db(user_id, amount, 'success')
                        
                        # Отправляем уведомление пользователю
                        send_paypal_subscription_notification(user_id, subscription_type, amount)
                        
                        # Отправляем уведомление администратору
                        send_admin_notification_successful(user_id, amount, currency, "subscription", 
                                                          resource.get('id', 'unknown'), 
                                                          payer.get('email_address', 'не указан'), "PayPal")
        
        # ✅ ВСЕГДА отправляем уведомление администратору о PayPal платеже
        payer_email = resource.get('payer', {}).get('email_address', 'не указан')
        payment_id = resource.get('id', 'unknown')
        
        admin_notification = f"""
🔄 PAYPAL ПЛАТЕЖ ПОЛУЧЕН

📦 Продукт: {product_type}
💰 Сумма: {amount} {currency}
👤 User ID: {user_id or 'не найден'}
📧 Email: {payer_email}
🆔 Payment ID: {payment_id}
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

{'✅ Автоматически обработан' if user_id else '⚠️ Требуется ручная обработка'}
"""
        
        # Отправляем уведомление через requests
        try:
            import requests
            from config import BOT_TOKEN
            
            telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": 891422895,
                "text": admin_notification,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(telegram_url, json=payload, timeout=10)
            if response.status_code == 200:
                logging.info(f"✅ PayPal admin notification sent")
        except Exception as e:
            logging.error(f"❌ Error sending PayPal admin notification: {e}")
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"❌ Error handling PayPal payment captured: {e}")
        return jsonify({"status": "error"}), 500

def handle_paypal_order_completed(resource):
    """Обрабатывает завершенный заказ PayPal - ДОПОЛНЕННАЯ ВЕРСИЯ"""
    try:
        order_id = resource.get('id')
        purchase_units = resource.get('purchase_units', [])
        
        if not purchase_units:
            return jsonify({"status": "success"}), 200
            
        purchase_unit = purchase_units[0]
        custom_id = purchase_unit.get('custom_id')
        amount = purchase_unit.get('amount', {}).get('value')
        
        logging.info(f"🔧 PayPal order completed: order_id={order_id}, custom_id={custom_id}, amount={amount}")
        
        # Способ 1: Пытаемся найти в pending payments
        from paypal_payment import paypal_processor
        payment_id, payment_info = paypal_processor.find_payment_by_order_id(order_id)
        
        if payment_info:
            # Активируем через существующий механизм
            if paypal_processor.activate_subscription(payment_id):
                logging.info(f"✅ PayPal subscription activated via pending payment for user {payment_info['user_id']}")
                return jsonify({"status": "success"}), 200
        
        # Способ 2: Активируем по custom_id (user_id) и amount
        if custom_id and amount:
            user_id = int(custom_id)
            
            # Проверяем тип продукта по сумме
            if amount == "80.00":  # Колода
                # Активируем покупку колоды
                if paypal_processor.activate_paypal_deck_purchase(user_id):
                    logging.info(f"✅ PayPal deck purchase activated via order completed for user {user_id}")
                    # Отправляем файлы асинхронно
                    send_deck_files_async(user_id)
            else:
                # Это подписка
                subscription_type = determine_subscription_type_from_paypal(amount)
                
                if subscription_type:
                    # Активируем подписку
                    success = db.create_subscription(
                        user_id, 
                        subscription_type, 
                        SUBSCRIPTION_DURATIONS[subscription_type]
                    )
                    
                    if success:
                        logging.info(f"✅ PayPal subscription activated via custom_id for user {user_id}")
                        
                        # Отправляем уведомление пользователю
                        send_subscription_notification(user_id, subscription_type, amount)
                        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"❌ Error handling PayPal order completed: {e}")
        return jsonify({"status": "error"}), 500

def update_paypal_payment_status_in_db(user_id: int, amount: str, status: str):
    """Обновляет статус PayPal платежа в базе данных"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Ищем самый свежий pending платеж с соответствующей суммой
        cursor.execute('''
            UPDATE payments 
            SET status = %s 
            WHERE user_id = %s 
            AND payment_method = 'paypal'
            AND status = 'pending'
            AND amount = %s
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (status, user_id, float(amount)))
        
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        if updated > 0:
            logging.info(f"✅ PayPal payment status updated to {status} for user {user_id}, amount {amount}")
        else:
            logging.warning(f"⚠️ No pending PayPal payment found for user {user_id}, amount {amount}")
        
    except Exception as e:
        logging.error(f"❌ Error updating PayPal payment status in DB: {e}")

def find_user_from_paypal_payment(resource):
    """Ищет пользователя по данным из платежа PayPal"""
    try:
        purchase_units = resource.get('purchase_units', [])
        if not purchase_units:
            return None
            
        purchase_unit = purchase_units[0]
        custom_id = purchase_unit.get('custom_id')
        
        # Если в custom_id указан user_id
        if custom_id and custom_id.startswith('user_'):
            user_id = int(custom_id.replace('user_', ''))
            return user_id
        
        # Ищем по email плательщика
        payer = resource.get('payer', {})
        email = payer.get('email_address')
        
        if email:
            # Ищем пользователя по email в базе
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE email = %s LIMIT 1', (email,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error finding user from PayPal payment: {e}")
        return None

def determine_subscription_type_from_paypal(amount: str):
    """Определяет тип подписки по сумме PayPal"""
    paypal_prices = {
        "5.00": "month",
        "9.00": "3months", 
        "17.00": "6months",
        "35.00": "year"
    }
    return paypal_prices.get(str(amount))

def update_paypal_payment_status(user_id: int, status: str):
    """Обновляет статус PayPal платежа в базе"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE payments 
            SET status = %s 
            WHERE user_id = %s 
            AND payment_method = 'paypal'
            AND status = 'pending'
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (status, user_id))
        
        conn.commit()
        conn.close()
        logging.info(f"✅ PayPal payment status updated to {status} for user {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Error updating PayPal payment status: {e}")

def verify_paypal_webhook(request):
    """Проверяет подлинность вебхука PayPal"""
    try:
        from paypal_payment import paypal_processor
        
        # Получаем заголовки верификации
        auth_algo = request.headers.get('PAYPAL-AUTH-ALGO')
        cert_url = request.headers.get('PAYPAL-CERT-URL')
        transmission_id = request.headers.get('PAYPAL-TRANSMISSION-ID')
        transmission_sig = request.headers.get('PAYPAL-TRANSMISSION-SIG')
        transmission_time = request.headers.get('PAYPAL-TRANSMISSION-TIME')
        webhook_id = PAYPAL_WEBHOOK_ID  # из config.py
        
        # Проверяем наличие всех необходимых заголовков
        if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time, webhook_id]):
            logging.error("❌ Missing PayPal webhook verification headers")
            return False
        
        # Получаем access token для PayPal API
        access_token = paypal_processor.get_access_token()
        if not access_token:
            logging.error("❌ Could not get PayPal access token")
            return False
        
        # Тело вебхука как строка
        webhook_event = request.get_data(as_text=True)
        
        # URL для верификации
        verification_url = f"{paypal_processor.base_url}/v1/notifications/verify-webhook-signature"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        payload = {
            "auth_algo": auth_algo,
            "cert_url": cert_url,
            "transmission_id": transmission_id,
            "transmission_sig": transmission_sig,
            "transmission_time": transmission_time,
            "webhook_id": webhook_id,
            "webhook_event": json.loads(webhook_event)  # Преобразуем обратно в JSON
        }
        
        response = requests.post(verification_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            verification_status = result.get('verification_status')
            
            if verification_status == 'SUCCESS':
                logging.info("✅ PayPal webhook signature verified successfully")
                return True
            else:
                logging.error(f"❌ PayPal webhook verification failed: {verification_status}")
                return False
        
        logging.error(f"❌ PayPal verification API error: {response.status_code}")
        return False
        
    except Exception as e:
        logging.error(f"❌ Error verifying PayPal webhook: {e}")
        return False

def update_payment_status(self, payment_id: str, status: str):
    """Обновляет статус платежа в базе данных"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE payments 
            SET status = %s 
            WHERE payment_id = %s
        ''', (status, payment_id))
        
        conn.commit()
        conn.close()
        logging.info(f"✅ Payment status updated to {status} for {payment_id}")
        
    except Exception as e:
        logging.error(f"❌ Error updating payment status: {e}")

async def enhanced_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Улучшенный обработчик ошибок с обработкой конфликтов"""
    try:
        error = context.error
        
        # Обрабатываем конфликты отдельно
        if isinstance(error, Exception) and "Conflict" in str(error):
            logger.error("💥 CONFLICT: Multiple bot instances detected!")
            logger.info("🔄 Waiting before restart...")
            # Не логируем полный traceback для конфликтов
            return
        
        # Логируем другие ошибки
        logger.error(f"Exception while handling an update: {error}")
        logger.error("Full traceback:", exc_info=error)
        
    except Exception as e:
        logger.error(f"Error in enhanced error handler: {e}")

def start_health_monitoring():
    """Запускает мониторинг здоровья бота"""
    def monitor():
        while True:
            try:
                # Периодическая проверка состояния
                time.sleep(300)  # Каждые 5 минут
                
                # Проверка соединения с Telegram
                import requests
                response = requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
                    timeout=10
                )
                
                if response.status_code != 200:
                    logger.warning("⚠️ Telegram API connectivity issue detected")
                
                # Очистка устаревших данных
                try:
                    db.cleanup_expired_video_links()
                except Exception as e:
                    logger.error(f"❌ Cleanup error: {e}")
                    
            except Exception as e:
                logger.error(f"❌ Health monitor error: {e}")
    
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

def handle_paypal_payment_denied(resource):
    """Обрабатывает отклоненный платеж PayPal"""
    try:
        custom_id = resource.get('custom_id')
        if custom_id:
            user_id = int(custom_id)
            logging.info(f"❌ PayPal payment denied for user {user_id}")
            
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"❌ Error handling PayPal payment denied: {e}")
        return jsonify({"status": "error"}), 500

def handle_paypal_payment_captured(resource):
    """Обрабатывает подтвержденный платеж (captured)"""
    try:
        custom_id = resource.get('custom_id')
        order_id = resource.get('supplementary_data', {}).get('related_ids', {}).get('order_id')
        amount = resource.get('amount', {}).get('value')
        
        logging.info(f"🔧 PayPal payment captured: custom_id={custom_id}, order_id={order_id}, amount={amount}")
        
        if custom_id and amount:
            user_id = int(custom_id)
            
            # Проверяем, это подписка или колода
            if amount == "80.00":  # Стоимость колоды в шекелях
                # Активируем покупку колоды
                from paypal_payment import paypal_processor
                if paypal_processor.activate_paypal_deck_purchase(user_id):
                    logging.info(f"✅ PayPal deck purchase activated via payment captured for user {user_id}")
            else:
                # Это подписка
                subscription_type = determine_subscription_type_from_paypal(amount)
                
                if subscription_type:
                    # Активируем подписку
                    success = db.create_subscription(
                        user_id, 
                        subscription_type, 
                        SUBSCRIPTION_DURATIONS[subscription_type]
                    )
                    
                    if success:
                        logging.info(f"✅ PayPal subscription activated via payment captured for user {user_id}")
                        
                        # Отправляем уведомление пользователю
                        send_subscription_notification(user_id, subscription_type, amount)
                        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"❌ Error handling PayPal payment captured: {e}")
        return jsonify({"status": "error"}), 500

def send_paypal_subscription_notification(user_id: int, subscription_type: str, amount: str):
    """Отправляет уведомление об успешной оплате PayPal"""
    try:
        from telegram import Bot
        from config import BOT_TOKEN
        
        bot = Bot(token=BOT_TOKEN)
        
        subscription_names = {
            "month": "1 месяц",
            "3months": "3 месяца", 
            "6months": "6 месяцев",
            "year": "1 год"
        }
        
        # Получаем информацию о подписке для даты окончания
        subscription = db.get_user_subscription(user_id)
        end_date_str = ""
        if subscription and subscription[1]:
            end_date = subscription[1]
            if hasattr(end_date, 'strftime'):
                end_date_str = end_date.strftime('%d.%m.%Y')
            else:
                end_date_str = str(end_date)[:10]
        
        message_text = f"""
✅ *Оплата подтверждена!*

💎 Ваша премиум подписка "{subscription_names.get(subscription_type, '1 год')}" активирована.

💰 Сумма: {amount}₪
📅 Действует до: {end_date_str}

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Техники самопомощи
• Медитация «Дары Моря»

Наслаждайтесь полным доступом! 💫
"""
        
        bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='Markdown'
        )
        logging.info(f"✅ PayPal subscription notification sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Error sending PayPal subscription notification: {e}")

def find_recent_subscription_user_by_time(payment_time):
    """Ищет пользователя по времени платежа"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Создаем таблицу для логов действий если её нет
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_action_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    action TEXT,
                    action_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        except:
            pass  # Таблица уже существует
        
        # Ищем действия за последние 10 минут до платежа
        time_before_payment = payment_time - timedelta(minutes=10)
        
        cursor.execute('''
            SELECT DISTINCT user_id 
            FROM user_action_logs 
            WHERE action LIKE '%%subscribe%%' 
            AND created_at BETWEEN %s AND %s
            ORDER BY created_at DESC 
            LIMIT 3
        ''', (time_before_payment, payment_time))
        
        results = cursor.fetchall()
        conn.close()
        
        if results:
            # Возвращаем первого пользователя
            return results[0][0]
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error finding user by time: {e}")
        return None

def send_admin_notification_successful(user_id: int, amount: str, currency: str, product_type: str, 
                                      payment_id: str, email: str, payment_system: str):
    """Отправляет уведомление об успешном платеже"""
    try:
        import requests
        from config import BOT_TOKEN
        
        # Определяем название продукта
        product_name = "Подписка" if product_type == "subscription" else "Колода"
        
        # Определяем тип подписки по сумме если это подписка
        subscription_info = ""
        if product_type == "subscription":
            sub_type = determine_subscription_type(amount)
            subscription_names = {
                "month": "1 месяц",
                "3months": "3 месяца", 
                "6months": "6 месяцев",
                "year": "1 год"
            }
            if sub_type in subscription_names:
                subscription_info = f"\n💎 Тип: {subscription_names[sub_type]}"
        
        admin_message = f"""
✅ УСПЕШНЫЙ ПЛАТЕЖ {payment_system.upper()}

🎉 *{product_name} приобретена!*

👤 Пользователь: {user_id}
💰 Сумма: {amount} {currency}
📦 Продукт: {product_name}{subscription_info}
🆔 ID платежа: `{payment_id}`
📧 Email: {email or 'не указан'}
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Платеж обработан автоматически! 🎊
"""
        
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": 891422895,  
            "text": admin_message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(telegram_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Admin notification sent for {product_type} payment {payment_id}")
        else:
            logger.error(f"❌ Failed to send admin notification: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error sending admin notification: {e}")

def send_admin_notification_failed(user_id: int, amount: str, currency: str, product_type: str, 
                                  payment_id: str, reason: str):
    """Отправляет уведомление о неудачном платеже"""
    try:
        import requests
        from config import BOT_TOKEN
        
        product_name = "Подписка" if product_type == "subscription" else "Колода"
        
        admin_message = f"""
❌ НЕУДАЧНЫЙ ПЛАТЕЖ

🚨 *{product_name} не активирована!*

👤 Пользователь: {user_id}
💰 Сумма: {amount} {currency}
📦 Продукт: {product_name}
🆔 ID платежа: `{payment_id}`
📝 Причина: {reason}
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Требуется проверка! ⚠️
"""
        
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": 891422895,  
            "text": admin_message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(telegram_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Admin failure notification sent for payment {payment_id}")
        else:
            logger.error(f"❌ Failed to send failure notification: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error sending failure notification: {e}")

def activate_deck_purchase_from_webhook(user_id: int, payment_id: str, amount: str, currency: str) -> bool:
    """Активирует покупку колоды из вебхука"""
    try:
        from database import db
        
        # Проверяем, является ли это покупкой колоды
        is_deck_purchase = False
        
        if currency == 'RUB' and float(amount) == 999.00:
            is_deck_purchase = True
        elif currency == 'ILS' and float(amount) == 80.00:
            is_deck_purchase = True
        
        if not is_deck_purchase:
            logger.error(f"❌ Amount {amount} {currency} doesn't match deck price")
            return False
        
        # Активируем покупку колоды
        success = db.record_deck_purchase(user_id, payment_id)
        
        if success:
            logger.info(f"✅ Deck purchase activated for user {user_id}")
            
            # Обновляем статус платежа в базе
            update_payment_status_in_db(user_id, payment_id, 'success', 'deck')
            
            return True
        else:
            logger.error(f"❌ Failed to record deck purchase for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error activating deck purchase: {e}")
        return False

def handle_payment_notification(event_data):
    """Обрабатывает уведомление о платеже"""
    try:
        payment_object = event_data.get('object', {})
        payment_status = payment_object.get('status')
        payment_id = payment_object.get('id')
        metadata = payment_object.get('metadata', {})
        amount_value = payment_object.get('amount', {}).get('value')
        currency = payment_object.get('amount', {}).get('currency', 'RUB')

        logger.info(f"🔔 Payment notification: status={payment_status}, payment_id={payment_id}, amount={amount_value}, currency={currency}")
        logger.info(f"🔍 Metadata: {metadata}")

        # Определяем тип продукта
        product_type = "subscription"  # по умолчанию
        if 'product_type' in metadata:
            product_type = metadata['product_type']
        elif float(amount_value) == 999.00 and currency == 'RUB':
            product_type = "deck"  # колода
        elif float(amount_value) == 80.00 and currency == 'ILS':
            product_type = "deck"  # колода PayPal
        elif 'subscription_type' in metadata:
            product_type = "subscription"

        logger.info(f"📦 Product type detected: {product_type}")

        # ✅ СПОСОБ 1: Поиск по user_id в metadata
        user_id = None
        
        # Проверяем разные варианты ключей
        for key in ['user_id', 'userId', 'user', 'userID']:
            if key in metadata:
                user_id = metadata[key]
                logger.info(f"✅ Found user_id in metadata[{key}]: {user_id}")
                break
        
        # Если user_id строка, пытаемся преобразовать
        if user_id and isinstance(user_id, str):
            try:
                user_id = int(user_id)
            except:
                user_id = None
        
        # ✅ СПОСОБ 2: Поиск по email из платежа
        if not user_id:
            # Проверяем разные варианты email в metadata
            email_keys = ['custEmail', 'customer_email', 'email', 'payer_email', 'customerEmail']
            customer_email = None
            
            for key in email_keys:
                if key in metadata and metadata[key]:
                    customer_email = metadata[key]
                    logger.info(f"🔍 Found email in metadata[{key}]: {customer_email}")
                    break
            
            if customer_email:
                logger.info(f"🔍 Searching by email: {customer_email}")
                user_id = find_user_by_email(customer_email)
                if user_id:
                    logger.info(f"✅ Found user {user_id} by email: {customer_email}")
                    
                    # ✅ Обновляем email пользователя в базе если его нет
                    try:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE users 
                            SET email = %s 
                            WHERE user_id = %s AND (email IS NULL OR email = '')
                        ''', (customer_email, user_id))
                        conn.commit()
                        conn.close()
                        logger.info(f"✅ Updated email for user {user_id}: {customer_email}")
                    except Exception as e:
                        logger.error(f"❌ Error updating email: {e}")

        # ✅ СПОСОБ 3: Поиск по номеру телефона
        if not user_id:
            # Проверяем разные варианты телефона
            phone_keys = ['custPhone', 'customer_phone', 'phone', 'payer_phone', 'customerPhone']
            customer_phone = None
            
            for key in phone_keys:
                if key in metadata and metadata[key]:
                    customer_phone = metadata[key]
                    logger.info(f"🔍 Found phone in metadata[{key}]: {customer_phone}")
                    break
            
            if customer_phone:
                logger.info(f"🔍 Searching by phone: {customer_phone}")
                user_id = find_user_by_phone(customer_phone)
                if user_id:
                    logger.info(f"✅ Found user {user_id} by phone: {customer_phone}")

        # ✅ СПОСОБ 4: Поиск по последним действиям (по времени)
        if not user_id:
            logger.info("🔍 Searching by recent actions...")
            payment_time_str = payment_object.get('created_at')
            if payment_time_str:
                try:
                    # Преобразуем время из строки в datetime
                    payment_time = datetime.fromisoformat(payment_time_str.replace('Z', '+00:00'))
                    
                    # Ищем пользователей, которые нажимали на кнопки подписки в последние 10 минут
                    user_id = find_recent_subscription_user_by_time(payment_time)
                    if user_id:
                        logger.info(f"✅ Found user {user_id} by recent action timing")
                except Exception as e:
                    logger.error(f"❌ Error parsing payment time {payment_time_str}: {e}")

        # ✅ СПОСОБ 5: Поиск в таблице pending_payments по payment_id
        if not user_id:
            try:
                from yookassa_payment import payment_processor
                # Проверяем, есть ли этот платеж в ожидающих
                if hasattr(payment_processor, 'pending_payments'):
                    for pid, info in payment_processor.pending_payments.items():
                        if payment_id == info.get('yookassa_payment_id'):
                            user_id = info.get('user_id')
                            product_type = info.get('product_type', product_type)
                            logger.info(f"✅ Found user {user_id} in pending_payments, product: {product_type}")
                            break
            except Exception as e:
                logger.error(f"❌ Error checking pending payments: {e}")

        # ✅ ОБРАБОТКА ПЛАТЕЖА
        if user_id:
            user_id = int(user_id)
            
            if payment_status == 'succeeded':
                logger.info(f"✅ Payment succeeded for user {user_id}, product: {product_type}")
                
                # Обработка в зависимости от типа продукта
                if product_type == "deck":
                    # Обработка покупки колоды
                    success = activate_deck_purchase_from_webhook(user_id, payment_id, amount_value, currency)
                    
                    if success:
                        logger.info(f"🎉 Deck purchase activated for user {user_id}")
                        
                        # Уведомление пользователю отправляется отдельно
                        # Отправляем уведомление администратору
                        send_admin_notification_successful(user_id, amount_value, currency, product_type, 
                                                          payment_id, customer_email, "ЮKassa")
                    else:
                        logger.error(f"❌ Failed to activate deck purchase for user {user_id}")
                        send_admin_notification_failed(user_id, amount_value, currency, product_type, 
                                                      payment_id, "Ошибка активации покупки колоды")
                        
                else:
                    # Обработка подписки
                    subscription_type = determine_subscription_type(amount_value)
                    
                    success = activate_subscription_from_webhook(user_id, subscription_type, payment_id, payment_id)

                    if success:
                        logger.info(f"🎉 Subscription activated for user {user_id}, type: {subscription_type}")

                        # Отправляем уведомление пользователю
                        try:
                            send_subscription_notification_sync(user_id, subscription_type, amount_value)
                        except Exception as e:
                            logger.error(f"❌ Error sending notification to user: {e}")

                        # Отправляем уведомление администратору
                        send_admin_notification_successful(user_id, amount_value, currency, "subscription", 
                                                          payment_id, customer_email, "ЮKassa")

                return jsonify({"status": "success"}), 200

            elif payment_status in ['canceled', 'failed']:
                logger.info(f"❌ Payment failed for user {user_id}")
                # Отправляем уведомление об отмене
                send_admin_notification_failed(user_id, amount_value, currency, product_type, 
                                              payment_id, f"Платеж {payment_status}")
                return jsonify({"status": "success"}), 200
            else:
                logger.info(f"⏳ Payment still processing for user {user_id}: {payment_status}")
                return jsonify({"status": "success"}), 200
        else:
            # ✅ СОХРАНЯЕМ ДЛЯ РУЧНОЙ ОБРАБОТКИ И ЛОГИРУЕМ
            logger.warning(f"⚠️ Cannot identify user for payment {payment_id}")
            logger.warning(f"⚠️ Payment metadata: {metadata}")
            
            customer_email = None
            for key in ['custEmail', 'customer_email', 'email', 'payer_email']:
                if key in metadata:
                    customer_email = metadata[key]
                    break
            
            customer_phone = None
            for key in ['custPhone', 'customer_phone', 'phone', 'payer_phone']:
                if key in metadata:
                    customer_phone = metadata[key]
                    break
            
            save_unknown_payment_for_review(payment_object)
            
            # ✅ ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ АДМИНИСТРАТОРУ О НЕИДЕНТИФИЦИРОВАННОМ ПЛАТЕЖЕ
            notify_admin_about_unknown_payment_sync(payment_id, amount_value, customer_email, customer_phone, 
                                                   product_type, currency)
            
            return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"❌ Error handling payment notification: {e}")
        logger.error(f"❌ Full traceback:", exc_info=True)
        return jsonify({"status": "error"}), 500

def save_successful_payment_to_db(user_id: int, subscription_type: str, yookassa_id: str, amount: str, email: str):
    """Сохраняет информацию об успешном платеже в базу данных"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payments (user_id, amount, subscription_type, status, payment_method, 
                                 yoomoney_payment_id, customer_email, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ''', (
            user_id,
            float(amount),
            subscription_type,
            'success',
            'yookassa',
            yookassa_id,
            email
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Payment saved to database for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error saving payment to DB: {e}")

def notify_admin_about_unknown_payment_sync(payment_id: str, amount: str, email: str, phone: str, 
                                           product_type: str = "unknown", currency: str = "RUB"):
    """Уведомляет администратора о неидентифицированном платеже"""
    try:
        import requests
        from config import BOT_TOKEN
        
        product_name = "Подписка" if product_type == "subscription" else "Колода" if product_type == "deck" else "Неизвестно"
        
        message_text = f"""
⚠️ *НЕИДЕНТИФИЦИРОВАННЫЙ ПЛАТЕЖ*

🚨 Требуется ручная обработка!

📦 *Продукт:* {product_name}
💰 *Сумма:* {amount} {currency}
📧 *Email:* {email or 'Не указан'}
📞 *Телефон:* {phone or 'Не указан'}
🆔 *Payment ID:* `{payment_id}`
⏰ *Время:* {datetime.now().strftime('%d.%m.%Y %H:%M')}

🔍 *Что делать:*
1. Проверить таблицу `unknown_payments`
2. Найти пользователя по email/телефону
3. Использовать команду `/unknown_payments`

*Пользователь не идентифицирован, требуется ручная обработка!*
"""
        
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": 891422895,  
            "text": message_text,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(telegram_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Unknown payment notification sent to admin")
        else:
            logger.error(f"❌ Failed to send notification: {response.status_code}")
        
    except Exception as e:
        logger.error(f"❌ Error notifying admin: {e}")

def send_subscription_notification_sync(user_id: int, subscription_type: str, amount: str):
    """Отправляет уведомление об успешной активации подписки (синхронно)"""
    try:
        from telegram import Bot
        from config import BOT_TOKEN, SUBSCRIPTION_NAMES
        
        bot = Bot(token=BOT_TOKEN)
        
        # Получаем информацию о подписке
        subscription = db.get_user_subscription(user_id)
        end_date_str = ""
        if subscription and subscription[1]:
            end_date = subscription[1]
            if hasattr(end_date, 'strftime'):
                end_date_str = end_date.strftime('%d.%m.%Y')
            else:
                end_date_str = str(end_date)[:10]
        
        message_text = f"""
✅ *Оплата подтверждена!*

💎 Ваша премиум подписка "{SUBSCRIPTION_NAMES.get(subscription_type, '1 месяц')}" активирована.

💰 Сумма: {amount}₽
📅 Действует до: {end_date_str}

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Техники самопомощи
• Медитация «Дары Моря»

Наслаждайтесь полным доступом! 💫
"""
        
        # Синхронный вызов
        bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Subscription notification sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error sending subscription notification: {e}")

def send_subscription_notification(user_id: int, subscription_type: str, amount: str):
    """Отправляет уведомление об успешной активации подписки"""
    try:
        from telegram import Bot
        from config import BOT_TOKEN, SUBSCRIPTION_NAMES
        
        bot = Bot(token=BOT_TOKEN)
        
        # Получаем информацию о подписке
        subscription = db.get_user_subscription(user_id)
        end_date_str = ""
        if subscription and subscription[1]:
            end_date = subscription[1]
            if hasattr(end_date, 'strftime'):
                end_date_str = end_date.strftime('%d.%m.%Y')
            else:
                end_date_str = str(end_date)[:10]
        
        message_text = f"""
✅ *Оплата подтверждена!*

💎 Ваша премиум подписка "{SUBSCRIPTION_NAMES.get(subscription_type, '1 месяц')}" активирована.

💰 Сумма: {amount}₽
📅 Действует до: {end_date_str}

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Техники самопомощи
• Медитация «Дары Моря»

Наслаждайтесь полным доступом! 💫
"""
        
        bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Subscription notification sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error sending subscription notification: {e}")

def save_payment_to_db(user_id, subscription_type, yookassa_payment_id, internal_payment_id):
    """Сохраняет информацию о платеже в базу данных"""
    try:
        from database import db
        from config import SUBSCRIPTION_PRICES

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO payments (user_id, amount, subscription_type, status, yoomoney_payment_id, payment_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            user_id,
            SUBSCRIPTION_PRICES[subscription_type],
            subscription_type,
            'success',
            yookassa_payment_id,
            internal_payment_id
        ))

        conn.commit()
        conn.close()
        logger.info(f"✅ Payment saved to database for user {user_id}")

    except Exception as e:
        logger.error(f"❌ Error saving payment to DB: {e}")
        
def find_user_by_payment_id(yookassa_payment_id: str):
    """Ищет пользователя по payment_id в базе"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id FROM payments 
            WHERE yoomoney_payment_id = %s 
            OR payment_id = %s
            LIMIT 1
        ''', (yookassa_payment_id, yookassa_payment_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        logging.error(f"❌ Error finding user by payment_id: {e}")
        return None

def update_payment_status_in_db(user_id: int, yookassa_id: str, status: str):
    """Обновляет статус платежа в базе"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE payments 
            SET status = %s 
            WHERE user_id = %s 
            AND (yoomoney_payment_id = %s OR payment_id LIKE %s)
            AND status = 'pending'
        ''', (status, user_id, yookassa_id, f"%{yookassa_id}%"))
        
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        if updated > 0:
            logger.info(f"✅ Payment status updated to {status} for user {user_id}")
        else:
            logger.warning(f"⚠️ No pending payment found to update for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error updating payment status in DB: {e}")

def find_user_by_payment_data(payment_object):
    """Ищет пользователя по различным данным из платежа"""
    try:
        metadata = payment_object.get('metadata', {})
        amount_value = payment_object.get('amount', {}).get('value')

        # ✅ СПОСОБ 1: По email
        customer_email = metadata.get('custEmail')
        if customer_email:
            user_id = find_user_by_email(customer_email)
            if user_id:
                logger.info(f"✅ Found user {user_id} by email: {customer_email}")
                return user_id

        # ✅ СПОСОБ 2: По номеру телефона (если есть в metadata)
        customer_phone = metadata.get('phone') or metadata.get('custPhone')
        if customer_phone:
            user_id = find_user_by_phone(customer_phone)
            if user_id:
                logger.info(f"✅ Found user {user_id} by phone: {customer_phone}")
                return user_id

        # ✅ СПОСОБ 3: По последним активным пользователям (если сумма совпадает)
        # Ищем пользователей, которые недавно нажимали на кнопки подписки
        user_id = find_recent_subscription_user(amount_value)
        if user_id:
            logger.info(f"✅ Found recent subscription user {user_id} by amount: {amount_value}")
            return user_id

        return None

    except Exception as e:
        logger.error(f"❌ Error finding user by payment data: {e}")
        return None

def find_user_by_email(email: str):
    """Ищет пользователя по email в базе данных"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Ищем в таблице users
        cursor.execute('SELECT user_id FROM users WHERE email = %s LIMIT 1', (email,))
        result = cursor.fetchone()

        if not result:
            # Ищем похожие email
            cursor.execute('SELECT user_id FROM users WHERE email LIKE %s LIMIT 1', (f"%{email}%",))
            result = cursor.fetchone()

        if not result:
            # Ищем в таблице платежей по историческим данным
            cursor.execute('''
                SELECT user_id FROM payments 
                WHERE customer_email = %s 
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (email,))
            result = cursor.fetchone()

        conn.close()

        if result:
            user_id = result[0]
            logger.info(f"✅ Found user {user_id} by email {email}")
            return user_id
        
        logger.info(f"❌ User not found by email {email}")
        return None

    except Exception as e:
        logger.error(f"❌ Error finding user by email {email}: {e}")
        return None

def find_user_by_phone(phone: str):
    """Ищет пользователя по номеру телефона"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Очищаем номер от лишних символов
        clean_phone = ''.join(filter(str.isdigit, phone))

        # Ищем в пользователях (если есть поле phone)
        cursor.execute('''
            SELECT user_id FROM users 
            WHERE phone = %s OR phone LIKE %s 
            LIMIT 1
        ''', (phone, f'%{clean_phone}%'))

        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        return None

    except Exception as e:
        logger.error(f"❌ Error finding user by phone: {e}")
        return None

def find_recent_subscription_user(amount: str):
    """Ищет недавних пользователей, которые выбирали подписку"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Создаем временную таблицу для хранения действий пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                action_type TEXT,
                action_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Ищем пользователей, которые недавно нажимали на кнопки подписки
        cursor.execute('''
            SELECT user_id FROM user_actions 
            WHERE action_type = 'subscription_selection' 
            AND created_at >= NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC 
            LIMIT 1
        ''')

        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        return None

    except Exception as e:
        logger.error(f"❌ Error finding recent subscription user: {e}")
        return None

def determine_subscription_type(amount: str):
    """Определяет тип подписки по сумме платежа"""
    subscription_types = {
        "99.00": "month",
        "199.00": "3months", 
        "399.00": "6months",
        "799.00": "year"
    }
    if amount == "999.00":
        return None

    return subscription_types.get(amount, "month")

def save_unknown_payment_for_review(payment_object):
    """Сохраняет платеж с неизвестным пользователем для ручной обработки"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unknown_payments (
                id SERIAL PRIMARY KEY,
                payment_id TEXT NOT NULL,
                amount DECIMAL,
                customer_email TEXT,
                customer_phone TEXT,
                payment_data JSONB,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        ''')

        payment_id = payment_object.get('id')
        amount = payment_object.get('amount', {}).get('value')
        metadata = payment_object.get('metadata', {})
        customer_email = metadata.get('custEmail')
        customer_phone = metadata.get('phone') or metadata.get('custPhone')
        status = payment_object.get('status')

        cursor.execute('''
            INSERT INTO unknown_payments 
            (payment_id, amount, customer_email, customer_phone, payment_data, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (payment_id, amount, customer_email, customer_phone, json.dumps(payment_object), status))

        conn.commit()
        conn.close()
        logger.info(f"✅ Unknown payment saved for review: {payment_id}")

        # ✅ УВЕДОМЛЯЕМ АДМИНИСТРАТОРА О НЕИДЕНТИФИЦИРОВАННОМ ПЛАТЕЖЕ
        notify_admin_about_unknown_payment(payment_id, amount, customer_email, customer_phone)

    except Exception as e:
        logger.error(f"❌ Error saving unknown payment: {e}")

async def send_payment_success_notification(user_id: int, subscription_type: str, amount: str):
    """Отправляет уведомление пользователю об успешной оплате"""
    try:
        from telegram import Bot
        from config import BOT_TOKEN

        bot = Bot(token=BOT_TOKEN)

        subscription_names = {
            "month": "1 месяц",
            "3months": "3 месяца", 
            "6months": "6 месяцев",
            "year": "1 год"
        }

        message_text = f"""
✅ *Оплата прошла успешно!*

💎 Ваша премиум подписка "{subscription_names.get(subscription_type, '1 месяц')}" активирована.

💰 Сумма: {amount}₽

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Архипелаг ресурсов

Наслаждайтесь полным доступом! 💫
"""

        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Success notification sent to user {user_id}")

    except Exception as e:
        logger.error(f"❌ Error sending success notification: {e}")

def notify_admin_about_unknown_payment(payment_id: str, amount: str, email: str, phone: str):
    """Уведомляет администратора о неидентифицированном платеже - СИНХРОННАЯ ВЕРСИЯ"""
    try:
        from telegram import Bot
        from config import BOT_TOKEN, ADMIN_IDS

        if not ADMIN_IDS:
            return

        # Используем синхронный Bot
        bot = Bot(token=BOT_TOKEN)

        message_text = f"""
⚠️ *Неидентифицированный платеж*

💰 Сумма: {amount}₽
📧 Email: {email or 'Не указан'}
📞 Телефон: {phone or 'Не указан'}
🆔 Payment ID: {payment_id}

Требуется ручная обработка.
"""

        for admin_id in ADMIN_IDS:
            try:
                # СИНХРОННЫЙ вызов (без await)
                bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"❌ Error notifying admin {admin_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Error notifying admin: {e}")

def activate_subscription_from_webhook(user_id, subscription_type, yookassa_payment_id, internal_payment_id):
    """Активирует подписку из вебхука"""
    try:
        from database import db
        from config import SUBSCRIPTION_DURATIONS

        # Активируем подписку в базе данных
        success = db.create_subscription(
            user_id, 
            subscription_type, 
            SUBSCRIPTION_DURATIONS[subscription_type]
        )

        if success:
            # Сохраняем информацию о платеже
            save_payment_to_db(user_id, subscription_type, yookassa_payment_id, internal_payment_id)
            return True
        return False

    except Exception as e:
        logger.error(f"❌ Error activating subscription from webhook: {e}")
        return False

def save_payment_to_db(user_id, subscription_type, yookassa_payment_id, internal_payment_id):
    """Сохраняет информацию о платеже в базу данных"""
    try:
        from database import db
        from config import SUBSCRIPTION_PRICES
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payments (user_id, amount, subscription_type, status, yoomoney_payment_id, payment_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            user_id,
            SUBSCRIPTION_PRICES[subscription_type],
            subscription_type,
            'success',
            yookassa_payment_id,
            internal_payment_id
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Payment saved to database for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error saving payment to DB: {e}")

def ping_self():
    """Пингует собственный health endpoint"""
    service_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://metaphor-bot.onrender.com')
    
    while True:
        try:
            response = requests.get(f"{service_url}/health", timeout=10)
            logger.info(f"✅ Self-ping successful: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Self-ping failed: {e}")
        
        # Ждем 10 минут (600 секунд)
        time.sleep(600)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    try:
        logger.error(f"Exception while handling an update: {context.error}")
        logger.error("Full traceback:", exc_info=context.error)
    except Exception as e:
        logger.error(f"Error in error handler itself: {e}")

def setup_handlers(application):
    """Настройка всех обработчиков команд"""
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("daily", handlers.daily_card))
    application.add_handler(CommandHandler("profile", handlers.profile))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("resetme", handlers.reset_my_limit))
    application.add_handler(CommandHandler("debug", handlers.debug_db))
    application.add_handler(CommandHandler("history", handlers.history_command))
    application.add_handler(CommandHandler("stats", handlers.admin_stats))
    application.add_handler(CommandHandler("users", handlers.admin_users))
    application.add_handler(CommandHandler("export", handlers.export_data))
    application.add_handler(CommandHandler("addcards", handlers.add_cards))
    application.add_handler(CommandHandler("consult", handlers.consult_command))
    application.add_handler(CommandHandler("consult_requests", handlers.admin_consult_requests))
    application.add_handler(CommandHandler("resources", handlers.resources_command))
    application.add_handler(CommandHandler("guide", handlers.guide_command))
    application.add_handler(CommandHandler("buy", handlers.buy_command))
    application.add_handler(CommandHandler("subscribe", handlers.subscribe_command))
    application.add_handler(CommandHandler("message", handlers.show_daily_message))
    application.add_handler(CommandHandler("messages", handlers.messages_command))
    application.add_handler(CommandHandler("message_status", handlers.message_status))
    application.add_handler(CommandHandler("debug_messages", handlers.debug_messages))
    application.add_handler(CommandHandler("init_messages", handlers.init_messages))
    application.add_handler(CommandHandler("update_db", handlers.update_database))
    application.add_handler(CommandHandler("mystatus", handlers.check_subscription_status))
    application.add_handler(CommandHandler("fix_limit", handlers.fix_limit))
    application.add_handler(CommandHandler("resetsimple", handlers.reset_simple))
    application.add_handler(CommandHandler("resetmymessages", handlers.reset_my_messages))
    application.add_handler(CommandHandler("resetusermessages", handlers.reset_user_messages_admin))
    application.add_handler(CommandHandler("resetallmessages", handlers.reset_all_messages))
    application.add_handler(CommandHandler("todaymessages", handlers.view_today_messages))
    application.add_handler(CommandHandler("updatecards", handlers.update_cards_descriptions))
    application.add_handler(CommandHandler("force_update_cards", handlers.force_update_cards))
    application.add_handler(CommandHandler("getfileid", handlers.get_file_id))
    application.add_handler(CommandHandler("getallfiles", handlers.get_all_file_ids))
    application.add_handler(CommandHandler("meditation", handlers.meditation_command))
    application.add_handler(CommandHandler("update_video_table", handlers.update_video_table))
    application.add_handler(CommandHandler("fix_video_table", handlers.fix_video_table))
    application.add_handler(CommandHandler("recreate_video_table", handlers.recreate_video_table))
    application.add_handler(CommandHandler("report", handlers.report_problem_command))
    application.add_handler(CommandHandler("reports", handlers.admin_reports))
    application.add_handler(CommandHandler("debug_buttons", handlers.debug_buttons))
    application.add_handler(CommandHandler("debug_report", handlers.debug_report))
    application.add_handler(CommandHandler("update_payments", handlers.update_payments_table))
    application.add_handler(CommandHandler("subscribe_user", handlers.manual_subscription))
    application.add_handler(CommandHandler("user_info", handlers.user_info))
    application.add_handler(CommandHandler("fix_video_table", handlers.fix_video_table))
    application.add_handler(CommandHandler("update_payments_structure", handlers.update_payments_structure))
    application.add_handler(CommandHandler("my_payments", handlers.view_my_payments))
    application.add_handler(CommandHandler("update_database_structure", handlers.update_database_structure))
    application.add_handler(CommandHandler("add_phone_column", handlers.add_phone_column))
    application.add_handler(CommandHandler("fix_user_subscription", handlers.fix_user_subscription))
    application.add_handler(CommandHandler("fix_expired_subscriptions", handlers.fix_expired_subscriptions))
    application.add_handler(CommandHandler("add_missing_columns", handlers.add_missing_columns))
    application.add_handler(CommandHandler("unknown_payments", handlers.process_unknown_payments))
    application.add_handler(CommandHandler("test_notifications", handlers.test_notifications))
    application.add_handler(CommandHandler("test_reminder", handlers.test_reminder))


    application.add_handler(CallbackQueryHandler(
        handlers.show_report_problem_from_button, 
        pattern="^report_problem$"
    ))

    application.add_handler(CallbackQueryHandler(
        handlers.start_report_form, 
        pattern="^start_report_form$"
    ))

    application.add_handler(CallbackQueryHandler(
        handlers.handle_subscription_selection, 
        pattern="^subscribe_"
    ))
    application.add_handler(CallbackQueryHandler(
        handlers.handle_payment_check, 
        pattern="^check_payment_"
    ))

    
    application.add_handler(CallbackQueryHandler(handlers.button_handler))

    application.add_handler(CallbackQueryHandler(handlers.meditation_button_handler, pattern="^meditation$"))

    #application.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_any_document))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handlers.handle_random_messages
    ))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handlers.handle_consult_form
    ))

def cleanup_video_links():
    """Периодическая очистка просроченных видео ссылок"""
    while not shutdown_manager.shutdown_event.is_set():
        try:
            time.sleep(3600)  # Каждый час
            if not shutdown_manager.shutdown_event.is_set():
                cleaned_count = db.cleanup_expired_video_links()
                if cleaned_count > 0:
                    logger.info(f"✅ Periodically cleaned {cleaned_count} expired video links")
        except Exception as e:
            logger.error(f"❌ Error in periodic video links cleanup: {e}")

def start_payment_monitoring():
    """Запускает автоматический мониторинг платежей с обработкой ошибок"""
    while not shutdown_manager.shutdown_event.is_set():
        try:
            # Мониторинг ЮKassa платежей
            try:
                payment_processor.check_all_pending_payments()
            except Exception as e:
                logging.error(f"❌ Error in YooKassa payment monitoring: {e}")
            
            # Мониторинг PayPal платежей
            try:
                from paypal_payment import paypal_processor
                # Подписки
                try:
                    activated_subs = paypal_processor.check_paypal_static_payments()
                except Exception as e:
                    logging.error(f"❌ Error in PayPal subscription monitoring: {e}")
                    activated_subs = 0
                    
                # Колоды
                try:
                    activated_decks = paypal_processor.check_paypal_deck_payments()
                except Exception as e:
                    logging.error(f"❌ Error in PayPal deck monitoring: {e}")
                    activated_decks = 0
                
                if activated_subs > 0 or activated_decks > 0:
                    logging.info(f"✅ PayPal monitor: activated {activated_subs} subscriptions, {activated_decks} deck purchases")
                    
            except Exception as e:
                logging.error(f"❌ Error in PayPal payment monitoring: {e}")
            
        except Exception as e:
            logging.error(f"❌ Error in payment monitoring: {e}")
        
        # Проверяем каждые 30 секунд
        for _ in range(30):
            if shutdown_manager.shutdown_event.is_set():
                break
            time.sleep(1)

def run_bot():
    """Запускает бота в основном потоке"""
    max_retries = 3
    retry_delay = 30
    
    for attempt in range(max_retries):
        # Проверяем флаг shutdown перед каждой попыткой
        if shutdown_manager.shutdown_event.is_set():
            logger.info("🛑 Shutdown detected, stopping bot")
            return
            
        try:
            logger.info(f"🔄 Attempt {attempt + 1} to start bot...")
            
            if not BOT_TOKEN:
                logger.error("❌ BOT_TOKEN not found in environment variables!")
                time.sleep(retry_delay)
                continue
            
            # Инициализация базы данных
            logger.info("🔄 Initializing database...")
            db.init_database()
            db.update_existing_users_limits()
            
            # Создаем приложение
            application = Application.builder().token(BOT_TOKEN).build()
            application.add_error_handler(enhanced_error_handler)
            
            # Добавляем обработчики
            setup_handlers(application)
            
            logger.info("🚀 Starting bot polling (SINGLE INSTANCE)...")
            
            # Запускаем polling
            application.run_polling(
                poll_interval=3.0,
                timeout=20,
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query'],
                bootstrap_retries=0,
                close_loop=False
            )
            
            # Если дошли сюда, бот завершился нормально
            logger.info("✅ Bot stopped normally")
            break
            
        except Exception as e:
            error_str = str(e)
            if "Conflict" in error_str:
                logger.error(f"💥 CONFLICT DETECTED on attempt {attempt + 1}: {e}")
                logger.info("🔄 This usually means another instance is running. Waiting...")
            else:
                logger.error(f"❌ Bot crashed on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1 and not shutdown_manager.shutdown_event.is_set():
                current_delay = min(retry_delay * (2 ** attempt), 300)
                logger.info(f"🔄 Restarting in {current_delay} seconds...")
                for _ in range(current_delay):
                    if shutdown_manager.shutdown_event.is_set():
                        return
                    time.sleep(1)
            else:
                logger.error("💥 Max retries exceeded or shutdown requested")
                if not shutdown_manager.shutdown_event.is_set():
                    raise

def run_flask_server():
    """Запускает Flask сервер"""
    try:
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"🚀 Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Flask server crashed: {e}")

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info("🛑 Received shutdown signal. Stopping bot gracefully...")

def monitor_resources():
    """Мониторинг использования ресурсов"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    while not shutdown_manager.shutdown_event.is_set():
        try:
            memory_percent = process.memory_percent()
            cpu_percent = process.cpu_percent()
            
            if memory_percent > 80:
                logger.warning(f"⚠️ High memory usage: {memory_percent:.1f}%")
            if cpu_percent > 90:
                logger.warning(f"⚠️ High CPU usage: {cpu_percent:.1f}%")
                
            time.sleep(60)  # Проверяем каждую минуту
            
        except Exception as e:
            logger.error(f"❌ Resource monitoring error: {e}")
            time.sleep(300)

def check_expired_subscriptions_periodically():
    """Периодически проверяет и обновляет истекшие подписки"""
    while not shutdown_manager.shutdown_event.is_set():
        try:
            # Проверяем каждые 5 минут
            time.sleep(300)
            
            if not shutdown_manager.shutdown_event.is_set():
                expired_count = db.check_and_update_expired_subscriptions()
                if expired_count > 0:
                    logger.info(f"✅ Periodically updated {expired_count} expired subscriptions")
                    
        except Exception as e:
            logger.error(f"❌ Error in expired subscriptions check: {e}")

async def send_reminders():
    """Отправляет напоминания пользователям, которые давно не брали карты (АСИНХРОННАЯ версия)"""
    try:
        bot = Bot(token=BOT_TOKEN)
        conn = db.get_connection()
        cursor = conn.cursor()
        
        week_ago = (datetime.now() - timedelta(days=7)).date()
        
        cursor.execute('''
            SELECT user_id, first_name, username, last_daily_card_date 
            FROM users 
            WHERE (last_daily_card_date IS NULL OR last_daily_card_date < %s)
            AND user_id NOT IN (
                SELECT user_id FROM user_reminders 
                WHERE reminder_date = CURRENT_DATE
            )
        ''', (week_ago,))
        
        users_to_remind = cursor.fetchall()
        
        reminded_count = 0
        
        for user_id, first_name, username, last_date in users_to_remind:
            try:
                user_name = f"@{username}" if username else first_name or "Дорогой пользователь"
                
                if last_date is None:
                    message = f"""
{user_name}, Вы еще не пробовали карты дня! 🎴

Каждый день вы можете получить уникальную карту с подсказкой от Вселенной 🌊

Начните свой день с карты дня — она поможет увидеть новые возможности и ресурсы! 💫

"""
                else:
                    days_passed = (datetime.now().date() - last_date).days
                    message = f"""
{user_name}, Вы давно не брали карту дня! 🎴

Прошло уже {days_passed} дней с вашей последней карты. 
За это время могло многое измениться! 🌊

Карты дня ждут, чтобы подсказать вам:
• Новые возможности
• Скрытые ресурсы  
• Подсказки для важных решений

Вернитесь к практике самопознания! 💫
"""
                
                # АСИНХРОННЫЙ вызов send_message
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
                
                # Записываем факт отправки напоминания
                cursor.execute('''
                    INSERT INTO user_reminders (user_id, reminder_date, reminder_type)
                    VALUES (%s, CURRENT_DATE, 'card_reminder')
                    ON CONFLICT (user_id, reminder_date, reminder_type) DO NOTHING
                ''', (user_id,))
                
                reminded_count += 1
                
                # Небольшая пауза между сообщениями
                await asyncio.sleep(0.1)
                
            except Exception as e:
                # Если не удалось отправить (пользователь заблокировал бота и т.д.)
                logging.error(f"❌ Error sending reminder to user {user_id}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        # Отправляем отчет администратору (асинхронно)
        if reminded_count > 0:
            try:
                report = f"""
📊 Отчет по напоминаниям

✅ Отправлено напоминаний: {reminded_count}
⏰ Время отправки: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Пользователи получили напоминания о картах дня 🎴
"""
                await bot.send_message(
                    chat_id=891422895,  # Ваш ID
                    text=report,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"❌ Error sending reminder report: {e}")
        
        logging.info(f"✅ Sent reminders to {reminded_count} users")
        
    except Exception as e:
        logging.error(f"❌ Error in send_reminders: {e}")

def start_simple_reminders():
    """Простой планировщик напоминаний без внешних зависимостей"""
    import threading
    import time
    from datetime import datetime
    
    def reminder_loop():
        while not shutdown_manager.shutdown_event.is_set():
            try:
                now = datetime.now()
                
                # Проверяем время (10:00 или 18:00)
                if now.hour in [10, 18] and now.minute == 0:
                    logging.info(f"⏰ Time for reminders: {now.hour}:00")
                    
                    # Запускаем асинхронную функцию в отдельном потоке
                    import asyncio
                    
                    def run_async():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(send_reminders())
                            loop.close()
                        except Exception as e:
                            logging.error(f"❌ Error in async reminder: {e}")
                    
                    # Запускаем в отдельном потоке
                    thread = threading.Thread(target=run_async, daemon=True)
                    thread.start()
                    
                    # Ждем час, чтобы не отправлять повторно
                    time.sleep(3600)
                else:
                    # Ждем минуту и проверяем снова
                    time.sleep(60)
                    
            except Exception as e:
                logging.error(f"❌ Error in reminder loop: {e}")
                time.sleep(300)
    
    thread = threading.Thread(target=reminder_loop, daemon=True)
    thread.start()
    logging.info("✅ Simple reminder scheduler started")
    return thread

def main():
    """Основная функция запуска - ТОЛЬКО ОДИН ПРОЦЕСС"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, shutdown_manager.signal_handler)
    signal.signal(signal.SIGTERM, shutdown_manager.signal_handler)
    
    logger.info("🚀 Starting Metaphor Bot (SINGLE INSTANCE)...")
    
    try:
        # Запускаем Flask в отдельном потоке
        flask_thread = threading.Thread(target=run_flask_server, daemon=True)
        flask_thread.start()
        logger.info("✅ Flask server started in thread")
        
        # Даем Flask время на запуск
        time.sleep(3)
        
        # Запускаем мониторинг платежей в отдельном потоке
        payment_thread = threading.Thread(target=start_payment_monitoring, daemon=True)
        payment_thread.start()
        logger.info("✅ Payment monitoring started")
        
        # Запускаем самопинг в отдельном потоке
        ping_thread = threading.Thread(target=ping_self, daemon=True)
        ping_thread.start()
        logger.info("✅ Self-ping started")
        
        # Запускаем очистку видео ссылок в отдельном потоке
        cleanup_thread = threading.Thread(target=cleanup_video_links, daemon=True)
        cleanup_thread.start()
        logger.info("✅ Video links cleanup started")
        
        # Запускаем проверку истекших подписок
        expired_check_thread = threading.Thread(target=check_expired_subscriptions_periodically, daemon=True)
        expired_check_thread.start()
        logger.info("✅ Expired subscriptions checker started")

        # Запускаем планировщик напоминаний
        reminder_thread = start_simple_reminders()
        logger.info("✅ Reminder scheduler started")

        # Запускаем бота в ОСНОВНОМ потоке
        logger.info("✅ Starting bot in main thread...")
        run_bot()
        
    except Exception as e:
        logger.error(f"💥 Error in main: {e}")
    finally:
        logger.info("🛑 Bot application stopped")

if __name__ == '__main__':
    main()