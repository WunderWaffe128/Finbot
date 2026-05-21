# scheduler.py
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db_manager import load_users
from api_client import get_best_rates_summary
from bot_config import CITIES_MAPPING


async def check_and_send_notifications(application):
    """Ежеминутный поиск пользователей, выставивших текущее время"""
    users = load_users()
    if not users:
        return

    minsk_tz = pytz.timezone("Europe/Minsk")
    now_minsk = datetime.now(minsk_tz).strftime("%H:%M")
    city_cache = {}

    for user_id, data in users.items():
        city_slug = data["city"]
        preferred_time = data["time"]

        if preferred_time == now_minsk:
            if city_slug not in city_cache:
                city_cache[city_slug] = get_best_rates_summary(city_slug)

            rates_data = city_cache[city_slug]
            if not rates_data:
                continue

            city_name_ru = next((k for k, v in CITIES_MAPPING.items() if v == city_slug), "Минск")
            msg = f"☀️ **Твой персональный утренний отчет по курсам валют ({city_name_ru}):**\n"
            for cur, info in rates_data["best"].items():
                unit = "100 " if cur == "RUB" else "10 " if cur == "CNY" else "1 "
                msg += (
                    f"\n💵 **{unit}{cur}**\n"
                    f"🟢 Сдать дороже: `{info['best_buy']:.4f}` BYN ({info['best_buy_bank']})\n"
                    f"🔴 Купить дешевле: `{info['best_sell']:.4f}` BYN ({info['best_sell_bank']})\n"
                )
            try:
                await application.bot.send_message(chat_id=int(user_id), text=msg, parse_mode="Markdown")
            except Exception:
                pass


def setup_scheduler(application):
    """Инициализация планировщика с интервалом проверки в 1 минуту"""
    scheduler = AsyncIOScheduler(timezone="Europe/Minsk")
    scheduler.add_job(check_and_send_notifications, "interval", minutes=1, args=[application])
    scheduler.start()
