import asyncio
import sys

# === ФИКС ДЛЯ PYTHON 3.14 НА RENDER ===
# Принудительно создаём event loop перед запуском бота
if sys.version_info >= (3, 14):
    try:
        # Пытаемся получить текущий loop
        asyncio.get_running_loop()
    except RuntimeError:
        # Если loop не запущен (а это наш случай), создаём новый и устанавливаем его
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
# === КОНЕЦ ФИКСА ===

# Теперь все обычные импорты
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot_config import BOT_TOKEN
from handlers import start, handle_number
from scheduler import setup_scheduler
from api_client import refresh_all_cities_cache
from rate_cache import get_cache_age_minutes

async def post_init(application: Application):
    """
    Запускается при старте бота:
    1. Прогревает кэш (если он пустой или старше 3 часов)
    2. Запускает планировщик
    """
    print("🌐 Проверяю кэш курсов...")
    # Проверяем Минск как индикатор общего состояния кэша
    age = get_cache_age_minutes("minsk")
    if age > 180:  # старше 3 часов — обновляем сразу
        print(f"📡 Кэш устарел ({age:.0f} мин). Прогреваю...")
        refresh_all_cities_cache()
    else:
        print(f"✅ Кэш актуален (обновлён {age:.0f} мин назад).")

    setup_scheduler(application)
    print("✅ Планировщик запущен!")


def main():
    print("🚀 Запуск валютного бота Беларуси...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    print("✅ Бот онлайн.")
    app.run_polling()


if __name__ == "__main__":
    main()
