from flask import Flask
import psycopg2
import os

app = Flask(__name__)

@app.route('/migrate')
def migrate_data():
    try:
        railway_url = os.environ.get('RAILWAY_DB_URL')
        render_url = os.environ.get('DATABASE_URL')
        
        if not railway_url:
            return "❌ RAILWAY_DB_URL не настроен"
        if not render_url:
            return "❌ DATABASE_URL не настроен"
        
        # Подключаемся к базам
        old_conn = psycopg2.connect(railway_url)
        old_cursor = old_conn.cursor()
        new_conn = psycopg2.connect(render_url)
        new_cursor = new_conn.cursor()
        
        # Мигрируем пользователей
        old_cursor.execute('SELECT * FROM users')
        users = old_cursor.fetchall()
        user_count = len(users)
        
        migrated_users = 0
        for user in users:
            try:
                new_cursor.execute('''
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, registered_date, daily_cards_limit, last_daily_card_date, is_premium)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                ''', user)
                migrated_users += 1
            except Exception as e:
                print(f"⚠️ Ошибка пользователя {user[0]}: {e}")
        
        # Мигрируем историю карт
        old_cursor.execute('SELECT * FROM user_cards')
        user_cards = old_cursor.fetchall()
        card_count = len(user_cards)
        
        migrated_cards = 0
        for card in user_cards:
            try:
                new_cursor.execute('''
                    INSERT INTO user_cards (id, user_id, card_id, drawn_date)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                ''', card)
                migrated_cards += 1
            except Exception as e:
                print(f"⚠️ Ошибка карты {card[0]}: {e}")
        
        new_conn.commit()
        old_conn.close()
        new_conn.close()
        
        return f"""
        ✅ Миграция завершена успешно!<br>
        👤 Пользователей перенесено: {migrated_users}/{user_count}<br>
        🎴 Записей карт перенесено: {migrated_cards}/{card_count}
        """
        
    except Exception as e:
        return f"❌ Ошибка миграции: {str(e)}"

if __name__ == '__main__':
    print("🚀 Сервер миграции запущен на порту 5000")
    app.run(host='0.0.0.0', port=5000)
