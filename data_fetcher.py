import contextlib
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import aiohttp

from config import MOCK_MODE
from utils.humanize import format_bytes

logger = logging.getLogger(__name__)

HTML_URL = "https://pass.telekom.de/home"

_CHROME_MAJORS = [133, 134, 135, 136, 137, 138, 139, 140]
_ANDROID_VERSIONS = ["13", "14", "15"]
_ANDROID_DEVICES = ["SM-S928B", "SM-S938B", "SM-A556B", "Pixel 8", "Pixel 9 Pro"]
_IOS_VERSIONS = ["17.5", "17.6", "18.0", "18.1"]
_IPHONE_DEVICES = [
    "iPhone 15",
    "iPhone 15 Pro Max",
    "iPhone 16",
    "iPhone 16 Pro",
]


def _build_browser_profile() -> dict:
    if random.random() < 0.2:
        ios = random.choice(_IOS_VERSIONS)
        device = random.choice(_IPHONE_DEVICES)
        major = ios.split(".")[0]
        ua = (
            f"Mozilla/5.0 (iPhone; CPU iPhone OS {ios.replace('.', '_')} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{major}.0 Mobile/15E148 "
            f"Safari/604.1"
        )
        return {"ua": ua, "chrome_major": None, "platform": "ios"}
    chrome_major = random.choice(_CHROME_MAJORS)
    android = random.choice(_ANDROID_VERSIONS)
    device = random.choice(_ANDROID_DEVICES)
    ua = (
        f"Mozilla/5.0 (Linux; Android {android}; {device}) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{chrome_major}.0.0.0 Mobile Safari/537.36"
    )
    return {"ua": ua, "chrome_major": chrome_major, "platform": "android"}


_ACCEPT_LANGUAGES = [
    "de-DE,de;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "de-DE,de-AT;q=0.9,de;q=0.8,en-US;q=0.6,en;q=0.5",
    "de-DE,en-US;q=0.8,en;q=0.7",
]
_ACCEPT_HTML = [
    (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    ("text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"),
]


def _build_headers(profile: dict) -> dict[str, str]:
    headers = {
        "User-Agent": profile["ua"],
        "Accept": random.choice(_ACCEPT_HTML),
        "Accept-Language": random.choice(_ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    if random.random() < 0.4:
        headers["DNT"] = "1"
    if profile["platform"] == "android":
        major = profile["chrome_major"]
        headers.update(
            {
                "Sec-CH-UA": f'"Chromium";v="{major}", "Google Chrome";v="{major}"',
                "Sec-CH-UA-Mobile": "?1",
                "Sec-CH-UA-Platform": '"Android"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            }
        )
    return headers


MONTH_MAP = {
    "Januar": 1,
    "Februar": 2,
    "März": 3,
    "April": 4,
    "Mai": 5,
    "Juni": 6,
    "Juli": 7,
    "August": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Dezember": 12,
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
            delta = self.valid_until - datetime.now(UTC)
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
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def _parse_german_float(text: str) -> float:
    return float(text.strip().replace(".", "").replace(",", "."))


def _parse_german_date(text: str) -> datetime:
    m = re.match(r"(\d+)\.\s*(\w+)\s+(\d{4})", text.strip())
    if not m:
        raise ValueError(f"cannot parse German date: {text}")
    day, month_name, year = int(m.group(1)), m.group(2), int(m.group(3))
    month = MONTH_MAP.get(month_name)
    if month is None:
        raise ValueError(f"unknown month: {month_name}")
    return datetime(year, month, day, tzinfo=UTC)


def _parse_last_update_time(text: str) -> datetime:
    m = re.match(r"(\d+)\.(\d+)\.(\d+)\s*um\s*(\d+):(\d+)", text.strip())
    if not m:
        raise ValueError(f"cannot parse last-update time: {text}")
    day, month, year, hour, minute = (
        int(m.group(1)),
        int(m.group(2)),
        int(m.group(3)),
        int(m.group(4)),
        int(m.group(5)),
    )
    year += 2000 if year < 100 else 0
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


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


def _extract_summation_pass(html: str) -> dict | None:
    m = re.search(
        r'<section\s+class="data-pass-instance"\s+id="summationPass">'
        r".*?"
        r'<div\s+class="remaining-volume-value">([\d.,]+)\s*</div>'
        r".*?"
        r'<div\s+class="start-volume">([\d.,]+)</div>'
        r".*?"
        r'<div\s+class="volume-unit">(\w+)</div>'
        r".*?"
        r"--to-width:([\d.]+)%",
        html,
        re.DOTALL,
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
        "used_bytes_str": format_bytes(used_bytes),
        "total_bytes": int(total_num * multiplier),
        "total_bytes_str": f"{total_val} {unit}",
        "used_percent": used_pct,
    }


def _extract_pass_name(html: str) -> str | None:
    m = re.search(r"<h1[^>]*>\s*<span>([^<]+)</span>\s*</h1>", html)
    return m.group(1).strip() if m else None


def _extract_status_and_valid_until(html: str) -> tuple[str | None, datetime | None]:
    status = None
    valid_until = None
    for m in re.finditer(
        r'<section\s+class="data-pass-instance[^"]*"[^>]*id="pass-[^"]+"[^>]*>'
        r"([\s\S]*?)"
        r"</section>",
        html,
    ):
        content = m.group(1)
        if status is None:
            rm = re.search(r'<div\s+class="ribbon">\s*<strong>([^<]+)</strong>', content)
            if rm:
                status = rm.group(1).strip()
        if valid_until is None:
            vm = re.search(r"Gültig bis:\s*([^<]+)</div>", content)
            if vm:
                with contextlib.suppress(ValueError):
                    valid_until = _parse_german_date(vm.group(1).strip())
    return status, valid_until


def _extract_last_update(html: str) -> datetime | None:
    m = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*um\s*(\d{2}:\d{2})", html)
    if m:
        return _parse_last_update_time(f"{m.group(1)} um {m.group(2)}")
    return None


def _parse_html(html: str) -> LteData:
    volume = _extract_summation_pass(html)
    if volume is None:
        raise ValueError("could not parse summation pass from HTML")

    status, valid_until = _extract_status_and_valid_until(html)
    last_update = _extract_last_update(html) or datetime.now(UTC)
    pass_name = _extract_pass_name(html) or "Datenvolumen"

    return LteData(
        pass_name=pass_name,
        status_text=status or "unknown",
        total_bytes=volume["total_bytes"],
        total_bytes_str=volume["total_bytes_str"],
        used_bytes=volume["used_bytes"],
        used_bytes_str=volume["used_bytes_str"],
        used_percent=volume["used_percent"],
        valid_until=valid_until or datetime.now(UTC) + timedelta(days=30),
        last_update=last_update,
    )


async def get_lte_data() -> LteData:
    if MOCK_MODE:
        return _parse_data(MOCK_DATA)

    profile = _build_browser_profile()
    async with (
        aiohttp.ClientSession() as session,
        session.get(
            HTML_URL,
            headers=_build_headers(profile),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp,
    ):
        resp.raise_for_status()
        html = await resp.text()
        return _parse_html(html)
