# scheduler.py
# Планировщик работает в двух режимах:
# 1. Обновление кэша курсов — 8 раз в сутки (06:05, 09:05, 12:05, 15:05, 18:05, 21:05, 00:05, 03:05)
# 2. Рассылка пользователям — каждую минуту проверяем совпадение времени

from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db_manager import load_users
from api_client import get_best_rates_summary, refresh_all_cities_cache
from bot_config import CITIES_MAPPING


# ─────────────────────────────────────────────
# 1. ОБНОВЛЕНИЕ КЭША КУРСОВ
# ─────────────────────────────────────────────

async def job_refresh_cache():
    """Асинхронная обёртка для обновления кэша (APScheduler требует async)."""
    now_str = datetime.now(pytz.timezone("Europe/Minsk")).strftime("%H:%M")
    print(f"🔄 [{now_str}] Запуск планового обновления кэша курсов...")
    updated, failed = refresh_all_cities_cache()
    print(f"   ✅ Обновлено: {updated}")
    if failed:
        print(f"   ⚠️  Ошибки:   {failed}")


# ─────────────────────────────────────────────
# 2. РАССЫЛКА УТРЕННИХ ОТЧЁТОВ
# ─────────────────────────────────────────────

async def check_and_send_notifications(application):
    """Каждую минуту проверяет, у кого совпало время рассылки."""
    users = load_users()
    if not users:
        return

    minsk_tz = pytz.timezone("Europe/Minsk")
    now_minsk = datetime.now(minsk_tz).strftime("%H:%M")
    city_cache = {}

    for user_id, data in users.items():
        city_slug     = data["city"]
        preferred_time = data["time"]

        if preferred_time == "off" or preferred_time != now_minsk:
            continue

        # Берём данные из кэша (не делаем новый HTTP-запрос!)
        if city_slug not in city_cache:
            city_cache[city_slug] = get_best_rates_summary(city_slug)

        rates_data = city_cache[city_slug]
        if not rates_data:
            continue

        city_name_ru = next(
            (k for k, v in CITIES_MAPPING.items() if v == city_slug), "Минск"
        )

        msg = f"☀️ **Утренний отчёт по курсам валют — {city_name_ru}**\n"
        msg += f"🕐 Обновлено: данные банков актуальны\n\n"

        for cur, info in rates_data["best"].items():
            unit = "100 " if cur == "RUB" else "10 " if cur == "CNY" else "1 "
            msg += (
                f"💵 **{unit}{cur}**\n"
                f"🟢 Сдать дороже: `{info['best_buy']:.4f}` BYN"
                f" ({info['best_buy_bank']})\n"
                f"🔴 Купить дешевле: `{info['best_sell']:.4f}` BYN"
                f" ({info['best_sell_bank']})\n\n"
            )

        msg += "💡 _Используй /start → 🔮 Прогноз для анализа тренда_"

        try:
            await application.bot.send_message(
                chat_id=int(user_id), text=msg, parse_mode="Markdown"
            )
        except Exception as err:
            print(f"⚠️ Рассылка пользователю {user_id}: {err}")


# ─────────────────────────────────────────────
# 3. ИНИЦИАЛИЗАЦИЯ
# ─────────────────────────────────────────────

# Времена обновления кэша (час, минута) — Минское время
CACHE_REFRESH_TIMES = [
    (6,  5),
    (9,  5),
    (12, 5),
    (15, 5),
    (18, 5),
    (21, 5),
    (0,  5),
    (3,  5),
]


def setup_scheduler(application):
    """
    Регистрирует все задачи в APScheduler:
    - 8 плановых обновлений кэша
    - Ежеминутная рассылка пользователям
    """
    tz = pytz.timezone("Europe/Minsk")
    scheduler = AsyncIOScheduler(timezone=tz)

    # 8 обновлений кэша по расписанию
    for hour, minute in CACHE_REFRESH_TIMES:
        scheduler.add_job(
            job_refresh_cache,
            trigger="cron",
            hour=hour,
            minute=minute,
            id=f"cache_refresh_{hour:02d}_{minute:02d}",
        )

    # Ежеминутная проверка рассылок
    scheduler.add_job(
        check_and_send_notifications,
        trigger="interval",
        minutes=1,
        args=[application],
        id="notifications",
    )

    scheduler.start()
    print(
        "✅ Планировщик запущен. Кэш будет обновляться в: "
        + ", ".join(f"{h:02d}:{m:02d}" for h, m in CACHE_REFRESH_TIMES)
    )
