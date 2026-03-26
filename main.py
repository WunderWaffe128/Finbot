import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers import start, handle_number

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальная переменная для приложения
app = None


class WebhookHandler(BaseHTTPRequestHandler):
    """Обрабатывает вебхуки от Telegram и healthcheck запросы"""

    def do_POST(self):
        """Telegram отправляет сюда обновления"""
        if self.path == '/webhook':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                update_data = json.loads(post_data)

                # Создаем объект Update и добавляем в очередь
                update = Update.de_json(update_data, app.bot)
                app.update_queue.put_nowait(update)

                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
                logger.debug("Webhook received")
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        """Healthcheck для Render и UptimeRobot"""
        if self.path == '/healthcheck' or self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def do_HEAD(self):
        """Поддержка HEAD для UptimeRobot"""
        if self.path == '/healthcheck' or self.path == '/':
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Отключаем стандартное логирование HTTP сервера"""
        pass


def main():
    global app

    logger.info("🚀 Запускаю бота на вебхуках...")

    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).updater(None).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    # Получаем URL сервера
    port = int(os.getenv('PORT', 10000))
    render_url = os.getenv('RENDER_EXTERNAL_URL', f'https://finbot-j90j.onrender.com')
    webhook_url = f"{render_url}/webhook"

    logger.info(f"Устанавливаю вебхук: {webhook_url}")

    # Устанавливаем вебхук
    app.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

    logger.info(f"✅ Вебхук установлен! Бот готов принимать сообщения")

    # Запускаем HTTP сервер
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    logger.info(f"🌐 HTTP сервер запущен на порту {port}")

    # Запускаем асинхронную обработку
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run_app():
        async with app:
            await app.start()
            logger.info("✅ Бот полностью запущен и ожидает сообщения!")
            await server.serve_forever()

    try:
        loop.run_until_complete(run_app())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        loop.close()


if __name__ == "__main__":
    main()