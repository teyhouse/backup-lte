import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
GUILD_ID: int = int(os.getenv("GUILD_ID", "0"))
MOCK_MODE: bool = os.getenv("MOCK_MODE", "false").lower() == "true"
ALERT_THRESHOLD: float = float(os.getenv("ALERT_THRESHOLD", "90"))
LOG_LEVEL: int = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())

BERLIN_TZ = ZoneInfo("Europe/Berlin")
SUMMARY_TIME = time(hour=8, minute=0, tzinfo=BERLIN_TZ)
