# db_manager.py
import os
from bot_config import USERS_FILE


def load_users():
    """Загрузка конфигурации пользователей (ID, город, время рассылки)"""
    if not os.path.exists(USERS_FILE):
        return {}
    users = {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            uid = parts[0]
            city = parts[1] if len(parts) > 1 else "minsk"
            time_pref = parts[2] if len(parts) > 2 else "09:00"
            users[uid] = {"city": city, "time": time_pref}
    return users


def save_user_setting(user_id, city_slug=None, time_pref=None):
    """Гибкое сохранение отдельных параметров пользователя"""
    users = load_users()
    uid_str = str(user_id)

    if uid_str not in users:
        users[uid_str] = {"city": "minsk", "time": "09:00"}

    if city_slug:
        users[uid_str]["city"] = city_slug
    if time_pref:
        users[uid_str]["time"] = time_pref

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        for uid, data in users.items():
            f.write(f"{uid},{data['city']},{data['time']}\n")


def get_user_data(user_id):
    """Получение настроек пользователя (по умолчанию Минск, 09:00)"""
    users = load_users()
    return users.get(str(user_id), {"city": "minsk", "time": "09:00"})