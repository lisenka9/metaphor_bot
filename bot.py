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
        
        # Проверяем срок действия
        if datetime.now() > link_data['expires_at']:
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
        platform = link_data['platform']
        expires_time = link_data['expires_at'].strftime('%d.%m.%Y %H:%M')
        
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
                .info {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                    text-align: left;
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
                
                <div class="info">
                    <p><strong>⏰ Доступно до:</strong> {expires_time}</p>
                </div>
                
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
    """Обрабатывает вебхуки от PayPal"""
    try:
        # Получаем данные вебхука
        event_json = request.get_json()
        logging.info(f"📨 Received PayPal webhook: {event_json}")
        
        # Проверяем подлинность вебхука
        if not verify_paypal_webhook(request):
            logging.error("❌ Invalid PayPal webhook signature")
            return jsonify({"status": "error"}), 400
        
        event_type = event_json.get('event_type')
        resource = event_json.get('resource', {})
        
        logging.info(f"🔧 PayPal webhook event: {event_type}")
        
        # Обрабатываем разные типы событий
        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            return handle_paypal_payment_completed(resource)
        elif event_type == 'CHECKOUT.ORDER.COMPLETED':
            return handle_paypal_order_completed(resource)
        elif event_type == 'PAYMENT.CAPTURE.DENIED':
            return handle_paypal_payment_denied(resource)
        elif event_type == 'PAYMENT.CAPTURE.REFUNDED':
            return handle_paypal_payment_refunded(resource)
        elif event_type == 'PAYMENT.CAPTURE.REVERSED':
            return handle_paypal_payment_reversed(resource)
        
        # Логируем необработанные события для отладки
        logging.info(f"🔧 Unhandled PayPal webhook event: {event_type}")
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"❌ Error in PayPal webhook: {e}")
        return jsonify({"status": "error"}), 500

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
        webhook_id = PAYPAL_WEBHOOK_ID
        
        # Получаем access token
        access_token = paypal_processor.get_access_token()
        if not access_token:
            return False
        
        # Проверяем вебхук через PayPal API
        webhook_event = request.get_data(as_text=True)
        
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
            "webhook_event": webhook_event
        }
        
        response = requests.post(verification_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('verification_status') == 'SUCCESS'
        
        return False
        
    except Exception as e:
        logging.error(f"❌ Error verifying PayPal webhook: {e}")
        return False

def handle_paypal_order_completed(resource):
    """Обрабатывает завершенный заказ PayPal"""
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
        
        # Способ 2: Активируем по custom_id (user_id)
        if custom_id and amount:
            user_id = int(custom_id)
            
            # Определяем тип подписки по сумме
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
            
            # Определяем тип подписки по сумме
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

def determine_subscription_type_from_paypal(amount):
    """Определяет тип подписки по сумме PayPal"""
    paypal_prices = {
        "5.00": "month",
        "9.00": "3months", 
        "17.00": "6months",
        "35.00": "year"
    }
    return paypal_prices.get(str(amount))

def send_subscription_notification(user_id, subscription_type, amount):
    """Отправляет уведомление пользователю об активации подписки"""
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

💎 Ваша премиум подписка "{subscription_names.get(subscription_type, '1 месяц')}" активирована.

💰 Сумма: {amount}₪
📅 Действует до: {end_date_str}

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Архипелаг ресурсов
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

def handle_payment_notification(event_data):
    """Обрабатывает уведомление о платеже"""
    try:
        payment_object = event_data.get('object', {})
        payment_status = payment_object.get('status')
        payment_id = payment_object.get('id')
        metadata = payment_object.get('metadata', {})
        amount_value = payment_object.get('amount', {}).get('value')
        
        logger.info(f"🔔 Payment notification: status={payment_status}, payment_id={payment_id}, amount={amount_value}")
        
        user_id = metadata.get('user_id')
        product_type = metadata.get('product_type', 'subscription')  # По умолчанию подписка
        
        # ✅ ЕСЛИ user_id НЕТ, ИЩЕМ ПОЛЬЗОВАТЕЛЯ ПО РАЗНЫМ СПОСОБАМ
        if not user_id:
            user_id = find_user_by_payment_data(payment_object)
        
        if user_id and payment_status == 'succeeded':
            user_id = int(user_id)
            
            if product_type == 'deck':
                # ✅ ОБРАБОТКА ПОКУПКИ КОЛОДЫ
                logger.info(f"✅ Deck purchase succeeded for user {user_id}")
                
                # Записываем покупку в базу
                success = db.record_deck_purchase(user_id, payment_id)
                
                if success:
                    logger.info(f"🎉 Deck purchase recorded for user {user_id}")
                    
                    # Запускаем отправку файлов в отдельном потоке
                    import threading
                    
                    def send_deck_files_async():
                        """Отправляет файлы колоды асинхронно"""
                        try:
                            # Импортируем здесь чтобы избежать циклических импортов
                            from telegram import Bot
                            from config import BOT_TOKEN
                            
                            # Используем синхронный Bot (без Application)
                            bot = Bot(token=BOT_TOKEN)
                            
                            # Отправляем сообщение об успехе
                            success_text = """
                    ✅ *Оплата прошла успешно!*

                    Ваша цифровая колода «Настроение как море» готова к скачиванию.

                    📦 *Файлы отправляются...*
                    """
                            bot.send_message(
                                chat_id=user_id,
                                text=success_text,
                                parse_mode='Markdown'
                            )
                            
                            # Отправляем файлы
                            file_ids = {
                                "zip": "BQACAgIAAxkBAAILH2ka8spSoCXJz_jB1wFckPfGYkSXAAKNgQACUSbYSEhUWdaRMfa5NgQ",
                                "rar": "BQACAgIAAxkBAAILIWka8yBQZpQQw23Oj4rIGSF_zNYAA5KBAAJRJthIJUVWWMwVvMg2BA", 
                                "pdf": "BQACAgIAAxkBAAILF2ka8jBpiM0_cTutmYhXeGoZs4PJAAJ1gQACUSbYSAUgICe9H14nNgQ"
                            }
                            
                            try:
                                # ZIP файл
                                bot.send_document(
                                    chat_id=user_id,
                                    document=file_ids["zip"],
                                    filename="Ограничения.zip",
                                    caption="📦 Архив с картами (ZIP формат)"
                                )
                            except Exception as e:
                                logger.error(f"❌ Error sending ZIP: {e}")
                            
                            try:
                                # RAR файл
                                bot.send_document(
                                    chat_id=user_id,
                                    document=file_ids["rar"],
                                    filename="Возможности.rar", 
                                    caption="📦 Архив с картами (RAR формат)"
                                )
                            except Exception as e:
                                logger.error(f"❌ Error sending RAR: {e}")
                            
                            try:
                                # PDF файл
                                bot.send_document(
                                    chat_id=user_id,
                                    document=file_ids["pdf"],
                                    filename="Колода_Настроение_как_море_методическое_пособие.pdf",
                                    caption="📚 Методическое пособие с посланиями"
                                )
                            except Exception as e:
                                logger.error(f"❌ Error sending PDF: {e}")
                            
                            # Финальное сообщение
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
                            logger.error(f"❌ Error in send_deck_files_async: {e}")
                    
                    # Запускаем в отдельном потоке
                    thread = threading.Thread(target=send_deck_files_async)
                    thread.daemon = True
                    thread.start()
                    
                return jsonify({"status": "success"}), 200
                
            else:
                # ✅ ОБРАБОТКА ПОДПИСКИ (старый код)
                subscription_type = determine_subscription_type(amount_value)
                logger.info(f"✅ Payment succeeded for user {user_id}, type: {subscription_type}")
                
                success = activate_subscription_from_webhook(user_id, subscription_type, payment_id, payment_id)
                
                if success:
                    logger.info(f"🎉 Subscription activated for user {user_id}")
                    
                    import threading
                    
                    def send_subscription_notification_async():
                        """Отправляет уведомление о подписке асинхронно"""
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

💰 Сумма: {amount_value}₽

✨ Теперь вам доступны:
• 5 карт дня вместо 1
• Ежедневное послание дня  
• Архипелаг ресурсов

Наслаждайтесь полным доступом! 💫
"""
                            
                            bot.send_message(
                                chat_id=user_id,
                                text=message_text,
                                parse_mode='Markdown'
                            )
                            logger.info(f"✅ Success notification sent to user {user_id}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error sending subscription notification: {e}")
                    
                    thread = threading.Thread(target=send_subscription_notification_async)
                    thread.daemon = True
                    thread.start()
                    
                return jsonify({"status": "success"}), 200
                
        elif payment_status in ['canceled', 'failed']:
            logger.info(f"❌ Payment failed for user {user_id}")
            return jsonify({"status": "success"}), 200
        else:
            logger.info(f"⏳ Payment still processing for user {user_id}: {payment_status}")
            return jsonify({"status": "success"}), 200
            
    except Exception as e:
        logger.error(f"❌ Error handling payment notification: {e}")
        return jsonify({"status": "error"}), 500

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
            # Ищем в таблице платежей по историческим данным
            cursor.execute('''
                SELECT user_id FROM payments 
                WHERE customer_email = %s 
                ORDER BY payment_date DESC 
                LIMIT 1
            ''', (email,))
            result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        logger.error(f"❌ Error finding user by email: {e}")
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
    """Уведомляет администратора о неидентифицированном платеже"""
    try:
        from telegram import Bot
        from config import BOT_TOKEN, ADMIN_IDS
        
        if not ADMIN_IDS:
            return
            
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

async def run_bot_with_restart():
    """Запускает бота с автоматическим перезапуском при ошибках"""
    max_retries = 5
    retry_delay = 60  # секунды
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Attempt {attempt + 1} to start bot...")
            
            # Проверяем наличие токена
            if not BOT_TOKEN:
                logger.error("BOT_TOKEN not found in environment variables!")
                return
            
            # Проверяем наличие ключей ЮKassa
            from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
            if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
                logger.warning("⚠️ YooKassa keys not found - payments will not work!")
            else:
                logger.info("✅ YooKassa keys loaded")
            
            # Инициализируем базу данных
            logger.info("Инициализация базы данных...")
            db.init_database()
            db.update_existing_users_limits()
            
            try:
                cleaned_count = db.cleanup_expired_video_links()
                logger.info(f"✅ Cleaned up {cleaned_count} expired video links")
            except Exception as e:
                logger.error(f"❌ Error cleaning video links: {e}")
            
            if not db.check_cards_exist():
                logger.warning("В базе данных нет карт!")
            
            # Создаем приложение
            application = Application.builder().token(BOT_TOKEN).build()
            
            application.add_error_handler(error_handler)
            
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
            
            logger.info("🚀 Запуск бота в режиме Polling...")
            
            # ЗАПУСКАЕМ POLLING АСИНХРОННО
            await application.run_polling(
                poll_interval=3.0,
                timeout=20,
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query'],
                bootstrap_retries=0,
                close_loop=False
            )
            
        except Exception as e:
            logger.error(f"❌ Bot crashed on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"🔄 Restarting in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  
            else:
                logger.error("💥 Max retries exceeded. Bot stopped.")
                raise

def start_payment_monitoring():
    """Запускает автоматический мониторинг платежей"""
    while True:
        try:
            # Мониторинг ЮKassa платежей
            payment_processor.check_all_pending_payments()
            
            # Мониторинг PayPal платежей
            try:
                from paypal_payment import paypal_processor
                activated_count = paypal_processor.check_paypal_static_payments()
                if activated_count > 0:
                    logging.info(f"✅ PayPal monitor: activated {activated_count} subscriptions")
            except Exception as e:
                logging.error(f"❌ Error in PayPal payment monitoring: {e}")
            
        except Exception as e:
            logging.error(f"❌ Error in payment monitoring: {e}")
        
        # Проверяем каждые 30 секунд
        time.sleep(30)

def run_flask_process():
    """Запускает Flask в отдельном процессе"""
    try:
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"🚀 Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Flask process crashed: {e}")
        sys.exit(1)

def run_bot_process():
    """Запускает бота в отдельном процессе"""
    try:
        # Запускаем мониторинг платежей в отдельном потоке
        payment_thread = threading.Thread(target=start_payment_monitoring)
        payment_thread.daemon = True
        payment_thread.start()

        # Запускаем самопинг в отдельном потоке
        ping_thread = threading.Thread(target=ping_self)
        ping_thread.daemon = True
        ping_thread.start()
        
        # Периодическая очистка ссылок
        def cleanup_video_links():
            while True:
                try:
                    time.sleep(3600)  # Каждый час
                    cleaned_count = db.cleanup_expired_video_links()
                    if cleaned_count > 0:
                        logger.info(f"✅ Periodically cleaned {cleaned_count} expired video links")
                except Exception as e:
                    logger.error(f"❌ Error in periodic video links cleanup: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_video_links)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        # Запускаем бота в asyncio event loop
        asyncio.run(run_bot_with_restart())
        
    except Exception as e:
        logger.error(f"❌ Bot process crashed: {e}")
        sys.exit(1)

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info("🛑 Received shutdown signal. Stopping bot gracefully...")

def main():
    """Основная функция запуска"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Starting bot and Flask in separate threads...")
    
    # Создаем потоки вместо процессов
    flask_thread = threading.Thread(target=run_flask_process, name="FlaskThread")
    bot_thread = threading.Thread(target=run_bot_process, name="BotThread")
    
    # Делаем потоки демонами (завершатся при завершении main)
    flask_thread.daemon = True
    bot_thread.daemon = True
    
    # Запускаем потоки
    flask_thread.start()
    logger.info("✅ Flask thread started")
    
    time.sleep(3)  # Даем Flask время на запуск перед ботом
    
    bot_thread.start()
    logger.info("✅ Bot thread started")
    
    # Мониторим потоки и перезапускаем при падении
    while True:
        time.sleep(10)
        
        # Проверяем статус потоков
        if not flask_thread.is_alive():
            logger.error("❌ Flask thread died, restarting...")
            flask_thread = threading.Thread(target=run_flask_process, name="FlaskThread")
            flask_thread.daemon = True
            flask_thread.start()
            logger.info("✅ Flask thread restarted")
            
        if not bot_thread.is_alive():
            logger.error("❌ Bot thread died, restarting...")
            bot_thread = threading.Thread(target=run_bot_process, name="BotThread")
            bot_thread.daemon = True
            bot_thread.start()
            logger.info("✅ Bot thread restarted")

if __name__ == '__main__':
    main()