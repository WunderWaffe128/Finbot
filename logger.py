# logger.py
from datetime import datetime


def log_conversion(user_name, user_last_name, amount, result, currency_from="BYN", currency_to="USD"):
    """Логирование конвертации в файл"""
    try:
        current_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        last_name = user_last_name if user_last_name else ""

        log_message = (f"Время: [{current_time}] Пользователь: {user_name} {last_name}, "
                       f"{amount:.2f} {currency_from} -> {result:.2f} {currency_to}\n")

        with open('bot.log.txt', 'a', encoding='utf-8') as file:
            file.write(log_message)

    except Exception as e:
        print(f"❌ Ошибка записи в файл: {e}")


def log_to_console(user, user_name, user_last_name, amount, result, currency_from="BYN", currency_to="USD"):
    """Логирование в консоль"""
    current_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    print(f"Время: [{current_time}] Пользователь: {user.id}, {user_name} {user_last_name}, "
          f"{amount:.2f} {currency_from} -> {result:.2f} {currency_to}")