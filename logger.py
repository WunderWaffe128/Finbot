# logger.py
from datetime import datetime
from bot_config import LOG_FILE

def log_conversion(user_name, user_last_name, amount, result, currency_from="BYN", currency_to="USD"):
    try:
        current_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        log_message = (f"Время: [{current_time}] Пользователь: {user_name} {user_last_name}, "
                       f"{amount:.2f} {currency_from} -> {result:.2f} {currency_to}\n")
        with open(LOG_FILE, 'a', encoding='utf-8') as file:
            file.write(log_message)
    except Exception as e:
        print(f"❌ Ошибка записи логов: {e}")

def log_to_console(user, user_name, user_last_name, amount, result, currency_from="BYN", currency_to="USD"):
    current_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    print(f"Время: [{current_time}] Пользователь ID: {user.id}, {user_name} {user_last_name}, "
          f"{amount:.2f} {currency_from} -> {result:.2f} {currency_to}")
