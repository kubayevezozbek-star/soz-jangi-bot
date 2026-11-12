import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "9056051300:AAHr9MglvV6lhk_JrR86_CSvr-TwjhWdOq8").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "1438313297"))
ADMIN_IDS = [ADMIN_ID]

PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()

DB_PATH = BASE_DIR / "data" / "soz_jangi.db"
WORDS_FILE = BASE_DIR / "data" / "words.json"

BOT_USERNAME = "soz_jangi_bot"
