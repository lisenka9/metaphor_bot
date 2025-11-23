import logging
import os
import time
import json
import requests
import threading
from flask import Flask, request, jsonify, redirect, Response, stream_with_context
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import BOT_TOKEN
import handlers
from database import db
from yookassa_payment import payment_processor  
import logging

import multiprocessing
import signal
import sys
from datetime import datetime, timedelta

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


@app.route('/protected-video/<link_hash>')
def serve_protected_video(link_hash):
    """HTML страница с видео-плеером"""
    try:
        # Используем базу данных для проверки ссылки
        link_data = db.get_video_link(link_hash)
        
        if not link_data:
            return """
            <html>
                <head><title>Ссылка недействительна</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Ссылка недействительна</h2>
                    <p>Возможные причины:</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>Ссылка устарела (действует 1 час для бесплатных пользователей)</li>
                        <li>Ссылка уже была использована</li>
                        <li>Ошибка в ссылке</li>
                    </ul>
                    <p>Вернитесь в бота для получения новой ссылки.</p>
                    <a href="https://t.me/MetaphorCardsSeaBot" style="color: blue;">Вернуться в бота</a>
                </body>
            </html>
            """, 404
        
        yandex_link = link_data['yandex_link']
        
        if not yandex_link:
            return """
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2>⚠️ Ошибка сервера</h2>
                    <p>Не удалось получить видео.</p>
                    <a href="https://t.me/MetaphorCardsSeaBot">Вернуться в бота</a>
                </body>
            </html>
            """, 500
        
        # Улучшенный HTML с несколькими вариантами видео-плеера
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
                .video-container {{
                    position: relative;
                    width: 100%;
                    height: 0;
                    padding-bottom: 56.25%; /* 16:9 aspect ratio */
                    margin: 20px 0;
                }}
                .video-container iframe,
                .video-container video {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    border-radius: 10px;
                    border: none;
                }}
                .info {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                    text-align: left;
                }}
                .warning {{
                    color: #856404;
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 10px 0;
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
                    transition: background 0.3s;
                }}
                .btn:hover {{
                    background: #764ba2;
                }}
                .loading {{
                    color: #666;
                    font-style: italic;
                }}
                .fallback {{
                    margin-top: 20px;
                    padding: 15px;
                    background: #e9ecef;
                    border-radius: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🧘‍♀️ Медитация «Дары Моря»</h1>
                
                <div class="info">
                    <p><strong>⏰ Время доступа:</strong> {link_data['expires_at'].strftime('%d.%m.%Y %H:%M')}</p>
                    <p><strong>👤 Пользователь:</strong> {link_data['user_id']}</p>
                </div>
                
                <div class="warning">
                    ⚠️ <strong>Внимание:</strong> Это персональная ссылка. Не передавайте её другим.
                </div>
                
                <div class="video-container">
                    <!-- Основной вариант - iframe для прямых ссылок -->
                    <iframe src="{yandex_link}" 
                            frameborder="0" 
                            allow="autoplay; encrypted-media; fullscreen" 
                            allowfullscreen
                            id="videoPlayer">
                    </iframe>
                </div>
                
                <!-- Альтернативный вариант через тег video -->
                <div style="display: none;" id="fallbackVideo">
                    <div class="video-container">
                        <video controls autoplay style="width: 100%;">
                            <source src="{yandex_link}" type="video/mp4">
                            Ваш браузер не поддерживает видео тег.
                        </video>
                    </div>
                </div>
                
                <div class="fallback" id="directLink" style="display: none;">
                    <p>Если видео не загружается, попробуйте открыть ссылку напрямую:</p>
                    <a href="{yandex_link}" target="_blank" class="btn">📺 Открыть видео напрямую</a>
                </div>
                
                <p class="loading" id="loadingText">Загрузка видео...</p>
                
                <div style="margin-top: 20px;">
                    <a href="https://t.me/MetaphorCardsSeaBot" class="btn">Вернуться в бота</a>
                </div>
            </div>

            <script>
                // Проверяем загрузку видео
                setTimeout(function() {{
                    const videoPlayer = document.getElementById('videoPlayer');
                    const fallbackVideo = document.getElementById('fallbackVideo');
                    const directLink = document.getElementById('directLink');
                    const loadingText = document.getElementById('loadingText');
                    
                    // Показываем альтернативные варианты через 5 секунд
                    setTimeout(function() {{
                        loadingText.innerHTML = 'Если видео не загрузилось, используйте альтернативные варианты ниже:';
                        fallbackVideo.style.display = 'block';
                        directLink.style.display = 'block';
                    }}, 5000);
                    
                }}, 1000);
            </script>
        </body>
        </html>
        """
        
        logger.info(f"✅ Serving video page for user {link_data['user_id']}")
        return html_content
        
    except Exception as e:
        logging.error(f"Error in video proxy: {e}")
        return """
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>⚠️ Ошибка сервера</h2>
                <p>Попробуйте получить новую ссылку в боте.</p>
                <a href="https://t.me/MetaphorCardsSeaBot" class="btn">Вернуться в бота</a>
            </body>
        </html>
        """, 500

@app.route('/direct-video/<link_hash>')
def direct_video(link_hash):
    """Прямая загрузка видео (редирект на Яндекс.Диск)"""
    try:
        link_data = db.get_video_link(link_hash)
        
        if not link_data:
            return "❌ Ссылка недействительна", 404
        
        yandex_link = link_data['yandex_link']
        
        if not yandex_link:
            return "❌ Ошибка получения видео", 500
        
        # Делаем редирект на прямую ссылку Яндекс.Диска
        logger.info(f"🔗 Redirecting to Yandex video: {yandex_link}")
        return redirect(yandex_link)
        
    except Exception as e:
        logger.error(f"❌ Error in direct video: {e}")
        return "❌ Ошибка сервера", 500

@app.route('/video-stream/<link_hash>')
def video_stream(link_hash):
    """Потоковая передача видео с проверкой доступа"""
    try:
        # Проверяем доступ по ссылке
        link_data = db.get_video_link(link_hash)
        
        if not link_data:
            return "❌ Ссылка недействительна", 404
        
        # Проверяем срок действия
        if datetime.now() > link_data['expires_at']:
            # Удаляем просроченную ссылку
            db.cleanup_expired_video_links()
            return "❌ Срок действия ссылки истёк", 403
        
        yandex_link = link_data['yandex_link']
        
        if not yandex_link:
            return "❌ Ошибка получения видео", 500
        
        # Создаем потоковую передачу видео
        def generate():
            try:
                # Загружаем видео с Яндекс.Диска частями
                headers = {
                    'Range': request.headers.get('Range', 'bytes=0-'),
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(
                    yandex_link, 
                    headers=headers, 
                    stream=True, 
                    timeout=30
                )
                
                # Передаем видео частями
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
                        
            except Exception as e:
                logging.error(f"❌ Error streaming video: {e}")
        
        # Устанавливаем правильные заголовки для видео
        headers = {
            'Content-Type': 'video/mp4',
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            # Запрещаем кэширование и скачивание
            'Content-Disposition': 'inline',
            'X-Content-Type-Options': 'nosniff'
        }
        
        return Response(
            stream_with_context(generate()),
            status=206,  # Partial Content для поддержки seek
            headers=headers,
            direct_passthrough=True
        )
        
    except Exception as e:
        logging.error(f"❌ Error in video stream: {e}")
        return "❌ Ошибка загрузки видео", 500

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
        
        yandex_link = link_data['yandex_link']
        logging.info(f"✅ Serving video for user {link_data['user_id']}: {yandex_link[:100]}...")
        
        # Простой HTML с iframe для начала
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
                .video-container {{
                    position: relative;
                    width: 100%;
                    height: 0;
                    padding-bottom: 56.25%;
                    margin: 20px 0;
                    background: #000;
                    border-radius: 10px;
                    overflow: hidden;
                }}
                iframe {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    border: none;
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
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🧘‍♀️ Медитация «Дары Моря»</h1>
                
                <div class="info">
                    <p><strong>⏰ Доступно до:</strong> {link_data['expires_at'].strftime('%d.%m.%Y %H:%M')}</p>
                    <p><strong>👤 Пользователь:</strong> {link_data['user_id']}</p>
                </div>
                
                <div class="video-container">
                    <!-- Основной вариант - тег video для прямого воспроизведения -->
                    <video controls autoplay style="width: 100%; height: 100%;" preload="metadata">
                        <source src="{{ yandex_link }}" type="video/mp4">
                        Ваш браузер не поддерживает видео тег.
                    </video>
                </div>

<!-- Запасной вариант через iframe -->
<div style="margin-top: 20px;">
    <a href="{{ yandex_link }}" target="_blank" class="btn">📺 Открыть видео в новом окне</a>
</div>
                
                <div style="margin-top: 20px;">
                    <a href="https://t.me/MetaphorCardsSeaBot" class="btn">Вернуться в бота</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        logging.error(f"❌ Error in secure video: {e}")
        return "❌ Ошибка загрузки видео", 500

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
    logger.error(f"Exception while handling an update: {context.error}")

def run_bot_with_restart():
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
            application.run_polling(
                poll_interval=3.0,
                timeout=20,
                drop_pending_updates=True
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
            payment_processor.check_all_pending_payments()
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

        # Даем Flask время на запуск
        time.sleep(5)
        
        # Запускаем самопинг в отдельном потоке
        ping_thread = threading.Thread(target=ping_self)
        ping_thread.daemon = True
        ping_thread.start()
        
        # ✅ ПЕРИОДИЧЕСКАЯ ОЧИСТКА ССЫЛОК
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
        
        # Запускаем бота с автоматическим перезапуском
        run_bot_with_restart()
    except Exception as e:
        logger.error(f"❌ Bot process crashed: {e}")
        sys.exit(1)

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info("🛑 Received shutdown signal...")
    sys.exit(0)

def main():
    """Основная функция запуска"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Starting bot and Flask in separate processes...")
    
    # Создаем процессы
    flask_process = multiprocessing.Process(target=run_flask_process, name="FlaskProcess")
    bot_process = multiprocessing.Process(target=run_bot_process, name="BotProcess")
    
    # Запускаем процессы
    flask_process.start()
    logger.info("✅ Flask process started")
    
    bot_process.start() 
    logger.info("✅ Bot process started")
    
    # Мониторим процессы и перезапускаем при падении
    while True:
        time.sleep(10)
        
        # Проверяем статус процессов
        if not flask_process.is_alive():
            logger.error("❌ Flask process died, restarting...")
            flask_process = multiprocessing.Process(target=run_flask_process, name="FlaskProcess")
            flask_process.start()
            logger.info("✅ Flask process restarted")
            
        if not bot_process.is_alive():
            logger.error("❌ Bot process died, restarting...")
            bot_process = multiprocessing.Process(target=run_bot_process, name="BotProcess")
            bot_process.start()
            logger.info("✅ Bot process restarted")
        
        # Если оба процесса умерли, выходим
        if not flask_process.is_alive() and not bot_process.is_alive():
            logger.error("💥 Both processes died, exiting...")
            break            
if __name__ == '__main__':
    main()