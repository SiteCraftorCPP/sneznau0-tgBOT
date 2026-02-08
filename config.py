# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "an26.db")

# Настройки поиска (макс. результатов в быстром поиске)
SEARCH_LIMIT = 50
CACHE_TIME = 3600  # 1 час
