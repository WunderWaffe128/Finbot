# main.py
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot_config import BOT_TOKEN
from handlers import start, handle_number
from scheduler import setup_scheduler


async def post_init(application: Application):
    """Вызывается автоматически при старте бота для запуска утреннего планировщика"""
    setup_scheduler(application)
    print("✅ Асинхронный планировщик на 09:00 успешно инициализирован!")


def main():
    print("🚀 Запуск модульного валютного бота...")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    print("✅ Бот онлайн и готов обрабатывать запросы.")
    app.run_polling()


if __name__ == "__main__":
    main()
