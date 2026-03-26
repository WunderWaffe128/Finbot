import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers import start, handle_number


# ===== ПРОСТОЙ HEALTHCHECK СЕРВЕР (без Flask) =====
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, format, *args):
        # Отключаем логи healthcheck
        pass


def run_health_server():
    port = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()


# Запускаем healthcheck сервер в фоновом потоке
threading.Thread(target=run_health_server, daemon=True).start()


# ===== КОНЕЦ =====

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