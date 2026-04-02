import os
import threading
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.config import BOT_TOKEN
from src.handlers import start, handle_number

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== HEALTHCHECK СЕРВЕР =====
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/healthcheck' or self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def do_HEAD(self):
        if self.path == '/healthcheck' or self.path == '/':
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # отключаем логи


def run_health_server():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()


# Запускаем healthcheck в фоне
threading.Thread(target=run_health_server, daemon=True).start()


# =================================

def main():
    logger.info(f"🚀 Запускаю бота версия: beta2.{datetime.now()}")


    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    logger.info("✅ Бот запущен! Ожидаю сообщения...")

    # Запускаем polling
    app.run_polling()


if __name__ == "__main__":
    main()