# main.py
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers import start, handle_number


def main():
    """Главная функция для запуска бота"""
    print("🚀 Запускаю бота...")

    # Создание приложения
    app = Application.builder().token(BOT_TOKEN).build()

    # Добавление обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    print("✅ Бот запущен!")

    # Запуск бота
    app.run_polling()


if __name__ == "__main__":
    main()