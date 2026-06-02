# rate_cache.py
# Кэш курсов валют — обновляется 8 раз в сутки по расписанию.
# Все модули читают из кэша. Лишних запросов к банкам — ноль.

import json
import os
from datetime import datetime

CACHE_FILE = "rates_cache.json"


def _load_raw() -> dict:
    """Читает сырой кэш с диска."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(city: str, data: dict):
    """Сохраняет свежие данные для города в кэш."""
    raw = _load_raw()
    raw[city] = {
        "data": data,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


def get_cache(city: str) -> dict | None:
    """
    Возвращает закэшированные данные для города.
    Возвращает None только если кэша вообще нет (первый старт).
    """
    raw = _load_raw()
    entry = raw.get(city)
    if not entry:
        return None
    return entry  # {"data": {...}, "updated_at": "..."}


def get_cache_age_minutes(city: str) -> float:
    """Сколько минут прошло с последнего обновления кэша для города."""
    raw = _load_raw()
    entry = raw.get(city)
    if not entry:
        return 9999.0
    try:
        updated = datetime.strptime(entry["updated_at"], "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - updated
        return delta.total_seconds() / 60
    except Exception:
        return 9999.0
