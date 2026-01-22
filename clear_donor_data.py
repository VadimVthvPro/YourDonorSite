import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'blood_donor_bot'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'vadamahjkl'),
    'port': os.getenv('DB_PORT', '5432')
}

try:
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    print("Clearing donor data...")
    
    # 1. Удаляем записи из donation_responses
    cursor.execute("TRUNCATE TABLE donation_responses CASCADE;")
    print("Truncated donation_responses.")
    
    # 2. Удаляем пользователей с ролью 'user' (доноры)
    # Сначала удаляем запросы, созданные пользователями, которые сейчас имеют роль 'user'
    cursor.execute("""
        DELETE FROM donation_requests 
        WHERE doctor_id IN (SELECT telegram_id FROM users WHERE role = 'user');
    """)
    print("Deleted donation_requests for user-role doctors.")
    
    # Теперь удаляем самих пользователей
    cursor.execute("DELETE FROM users WHERE role = 'user';")
    print("Deleted users with role 'user'.")
    
    conn.commit()
    print("Donor data cleared successfully.")
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"An error occurred: {e}")

