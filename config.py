# config.py
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Явно грузим .env из папки бота (на VPS при запуске из другого каталога иначе не подхватится)
load_dotenv(os.path.join(BASE_DIR, ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Несколько админов через запятую: ADMIN_IDS=123,456,789
_raw_ids = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", ""))
ADMIN_IDS = {int(x.strip()) for x in _raw_ids.split(",") if x.strip()}
ADMIN_ID = next(iter(ADMIN_IDS), 0)  # первый, для совместимости
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Пути
DATABASE_PATH = os.path.join(BASE_DIR, "data", "an26.db")

# Настройки поиска (макс. результатов в быстром поиске)
SEARCH_LIMIT = 50
CACHE_TIME = 3600  # 1 час
