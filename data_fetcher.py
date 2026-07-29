import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

HTML_URL = "https://pass.telekom.de/home"
USER_AGENT = "Mozilla/5.0 (Linux; Android 15; SM-S938B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36"

MONTH_MAP = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
    "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
}


@dataclass
class LteData:
    pass_name: str
    status_text: str
    total_bytes: int
    total_bytes_str: str
    used_bytes: int
    used_bytes_str: str
    used_percent: float
    valid_until: datetime
    last_update: datetime

    pass_type: int = 0
    pass_stage: int = 0
    session_state: int = 0
    remaining_seconds: int = 0
    next_update_seconds: int = 3600
    subscriptions: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.session_state:
            self.session_state = 0 if self.status_text.lower() in ("aktiv", "active") else 1
        if not self.remaining_seconds and self.valid_until:
            delta = self.valid_until - datetime.now(timezone.utc)
            self.remaining_seconds = max(int(delta.total_seconds()), 0)

    @property
    def remaining_bytes(self) -> int:
        return self.total_bytes - self.used_bytes

    @property
    def remaining_days(self) -> int:
        return self.remaining_seconds // 86400

    @property
    def status(self) -> str:
        return "active" if self.session_state == 0 else "inactive"


MOCK_DATA = {
    "passName": "MagentaMobil Prepaid M",
    "passType": 103,
    "passStage": 1,
    "sessionState": 0,
    "initialVolume": 21474836480,
    "initialVolumeStr": "20 GB",
    "usedVolume": 5368709120,
    "usedVolumeStr": "5 GB",
    "usedPercentage": 25.0,
    "remainingSeconds": 2332800,
    "usedAt": 1782835472000,
    "nextUpdate": 10800,
    "validityPeriod": 4,
    "subscriptions": ["tns", "xtraSpeed"],
    "validUntil": "24. August 2026",
    "statusText": "active",
}


def _parse_ms_timestamp(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _parse_german_float(text: str) -> float:
    return float(text.strip().replace(".", "").replace(",", "."))


def _parse_german_date(text: str) -> datetime:
    m = re.match(r'(\d+)\.\s*(\w+)\s+(\d{4})', text.strip())
    if not m:
        raise ValueError(f"cannot parse German date: {text}")
    day, month_name, year = int(m.group(1)), m.group(2), int(m.group(3))
    month = MONTH_MAP.get(month_name)
    if month is None:
        raise ValueError(f"unknown month: {month_name}")
    return datetime(year, month, day, tzinfo=timezone.utc)


def _parse_last_update_time(text: str) -> datetime:
    m = re.match(r'(\d+)\.(\d+)\.(\d+)\s*um\s*(\d+):(\d+)', text.strip())
    if not m:
        raise ValueError(f"cannot parse last-update time: {text}")
    day, month, year, hour, minute = (
        int(m.group(1)), int(m.group(2)), int(m.group(3)),
        int(m.group(4)), int(m.group(5)),
    )
    year += 2000 if year < 100 else 0
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _gb_to_bytes(gb: float) -> int:
    return int(gb * 1_073_741_824)


def _parse_data(raw: dict) -> LteData:
    return LteData(
        pass_name=raw["passName"],
        status_text=raw.get("statusText", "unknown"),
        total_bytes=raw["initialVolume"],
        total_bytes_str=raw["initialVolumeStr"],
        used_bytes=raw["usedVolume"],
        used_bytes_str=raw["usedVolumeStr"],
        used_percent=raw["usedPercentage"],
        valid_until=_parse_german_date(raw.get("validUntil", "1. Januar 2099")),
        last_update=_parse_ms_timestamp(raw["usedAt"]),
        pass_type=raw.get("passType", 0),
        pass_stage=raw.get("passStage", 0),
        session_state=raw.get("sessionState", 0),
        remaining_seconds=raw.get("remainingSeconds", 0),
        next_update_seconds=raw.get("nextUpdate", 3600),
        subscriptions=raw.get("subscriptions", []),
    )


def _fmt_bytes(b: int) -> str:
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f} GB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"


def _extract_summation_pass(html: str) -> dict | None:
    m = re.search(
        r'<section\s+class="data-pass-instance"\s+id="summationPass">'
        r'.*?'
        r'<div\s+class="remaining-volume-value">([\d.,]+)\s*</div>'
        r'.*?'
        r'<div\s+class="start-volume">([\d.,]+)</div>'
        r'.*?'
        r'<div\s+class="volume-unit">(\w+)</div>'
        r'.*?'
        r'--to-width:([\d.]+)%',
        html, re.DOTALL,
    )
    if not m:
        return None
    remaining_val, total_val, unit, remaining_pct_str = m.groups()
    remaining_num = _parse_german_float(remaining_val)
    total_num = _parse_german_float(total_val)
    remaining_pct = _parse_german_float(remaining_pct_str)
    used_pct = round(100 - remaining_pct, 1)
    multiplier = 1_073_741_824 if unit.upper() == "GB" else 1_048_576 if unit.upper() == "MB" else 1
    used_bytes = int((total_num - remaining_num) * multiplier)
    return {
        "used_bytes": used_bytes,
        "used_bytes_str": _fmt_bytes(used_bytes),
        "total_bytes": int(total_num * multiplier),
        "total_bytes_str": f"{total_val} {unit}",
        "used_percent": used_pct,
    }


def _extract_pass_name(html: str) -> str | None:
    m = re.search(r'<h1[^>]*>\s*<span>([^<]+)</span>\s*</h1>', html)
    return m.group(1).strip() if m else None


def _extract_status_and_valid_until(html: str) -> tuple[str | None, datetime | None]:
    status = None
    valid_until = None
    for m in re.finditer(
        r'<section\s+class="data-pass-instance[^"]*"[^>]*id="pass-[^"]+"[^>]*>'
        r'([\s\S]*?)'
        r'</section>',
        html,
    ):
        content = m.group(1)
        if status is None:
            rm = re.search(r'<div\s+class="ribbon">\s*<strong>([^<]+)</strong>', content)
            if rm:
                status = rm.group(1).strip()
        if valid_until is None:
            vm = re.search(r'Gültig bis:\s*([^<]+)</div>', content)
            if vm:
                try:
                    valid_until = _parse_german_date(vm.group(1).strip())
                except ValueError:
                    pass
    return status, valid_until


def _extract_last_update(html: str) -> datetime | None:
    m = re.search(r'(\d{2}\.\d{2}\.\d{4})\s*um\s*(\d{2}:\d{2})', html)
    if m:
        return _parse_last_update_time(f"{m.group(1)} um {m.group(2)}")
    return None


def _parse_html(html: str) -> LteData:
    volume = _extract_summation_pass(html)
    if volume is None:
        raise ValueError("could not parse summation pass from HTML")

    status, valid_until = _extract_status_and_valid_until(html)
    last_update = _extract_last_update(html) or datetime.now(timezone.utc)
    pass_name = _extract_pass_name(html) or "Datenvolumen"

    return LteData(
        pass_name=pass_name,
        status_text=status or "unknown",
        total_bytes=volume["total_bytes"],
        total_bytes_str=volume["total_bytes_str"],
        used_bytes=volume["used_bytes"],
        used_bytes_str=volume["used_bytes_str"],
        used_percent=volume["used_percent"],
        valid_until=valid_until or datetime.now(timezone.utc) + timedelta(days=30),
        last_update=last_update,
    )


async def get_lte_data() -> LteData:
    from config import MOCK_MODE

    if MOCK_MODE:
        return _parse_data(MOCK_DATA)

    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(
            HTML_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            html = await resp.text()
            try:
                return _parse_html(html)
            except ValueError:
                logger.warning("Telekom HTML structure changed, falling back to mock", exc_info=True)
                return _parse_data(MOCK_DATA)
