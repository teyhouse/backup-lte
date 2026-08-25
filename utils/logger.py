import json
import logging
import logging.handlers
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "t": datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%dT%H:%M:%S"),
            "l": record.levelname,
            "n": record.name,
            "m": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


_HUMAN_FMT = logging.Formatter(
    "[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup_logging(level: int = logging.INFO, json_path: str = "bot.log") -> None:
    root = logging.getLogger()
    root.setLevel(level)

    fh = logging.handlers.RotatingFileHandler(
        json_path, maxBytes=10_485_760, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(level)
    fh.setFormatter(JsonFormatter())
    root.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(_HUMAN_FMT)
    root.addHandler(sh)

    logging.getLogger("discord").setLevel(level)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"lte_bot.{name}")
