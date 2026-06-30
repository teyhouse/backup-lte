import os
from datetime import time

from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
GUILD_ID: int = int(os.getenv("GUILD_ID", "0"))
MOCK_MODE: bool = os.getenv("MOCK_MODE", "false").lower() == "true"
API_URL: str = os.getenv("API_URL", "")

BERLIN_TZ = ZoneInfo("Europe/Berlin")
SUMMARY_TIME = time(hour=8, minute=0, tzinfo=BERLIN_TZ)
