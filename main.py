import asyncio
import sys
import os
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot_config import BOT_TOKEN
from handlers import start, handle_number
from scheduler import setup_scheduler
from api_client import refresh_all_cities_cache
from rate_cache import get_cache_age_minutes

# Фикс для Python 3.14
if sys.version_info >= (3, 14):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

async def health_check(request):
    return web.Response(text="OK")

async def post_init(application: Application):
    print("🌐 Проверяю кэш курсов...")
    age = get_cache_age_minutes("minsk")
    if age > 180:
        print(f"📡 Кэш устарел ({age:.0f} мин). Прогреваю...")
        refresh_all_cities_cache()
    else:
        print(f"✅ Кэш актуален (обновлён {age:.0f} мин назад).")
    setup_scheduler(application)
    print("✅ Планировщик запущен!")

async def main():
    # HTTP сервер для Render
    app_web = web.Application()
    app_web.router.add_get('/', health_check)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ HTTP сервер запущен на порту {port}")
    
    # Бот
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
