# migrate_data.py
import psycopg2
import os
import sys

def migrate_data():
    # Подключение к старой базе (Railway)
    try:
        old_conn = psycopg2.connect(os.environ.get('RAILWAY_DB_URL'))
        old_cursor = old_conn.cursor()
        print("✅ Подключились к Railway базе")
    except Exception as e:
        print(f"❌ Ошибка подключения к Railway: {e}")
        return

    # Подключение к новой базе (Render)
    try:
        new_conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        new_cursor = new_conn.cursor()
        print("✅ Подключились к Render базе")
    except Exception as e:
        print(f"❌ Ошибка подключения к Render: {e}")
        return

    try:
        # Мигрируем пользователей
        old_cursor.execute('SELECT * FROM users')
        users = old_cursor.fetchall()
        print(f"📊 Найдено пользователей: {len(users)}")

        for user in users:
            new_cursor.execute('''
                INSERT INTO users 
                (user_id, username, first_name, last_name, registered_date, daily_cards_limit, last_daily_card_date, is_premium)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            ''', user)

        # Мигрируем историю карт
        old_cursor.execute('SELECT * FROM user_cards')
        user_cards = old_cursor.fetchall()
        print(f"🎴 Найдено записей карт: {len(user_cards)}")

        for card in user_cards:
            new_cursor.execute('''
                INSERT INTO user_cards (id, user_id, card_id, drawn_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            ''', card)

        new_conn.commit()
        print("✅ Миграция данных завершена успешно!")

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        new_conn.rollback()
    finally:
        old_conn.close()
        new_conn.close()

if __name__ == '__main__':
    migrate_data()
