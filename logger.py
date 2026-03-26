import logging

# Настройка логирования — ТОЛЬКО В КОНСОЛЬ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # ✅ только вывод в консоль
    ]
)

logger = logging.getLogger(__name__)