# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Несколько админов через запятую: ADMIN_IDS=123,456,789
_raw_ids = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", ""))
ADMIN_IDS = {int(x.strip()) for x in _raw_ids.split(",") if x.strip()}
ADMIN_ID = next(iter(ADMIN_IDS), 0)  # первый, для совместимости
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "an26.db")

# Настройки поиска (макс. результатов в быстром поиске)
SEARCH_LIMIT = 50
CACHE_TIME = 3600  # 1 час
