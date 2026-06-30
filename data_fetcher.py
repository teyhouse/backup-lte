from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class LteData:
    pass_name: str
    pass_type: int
    pass_stage: int
    session_state: int
    total_bytes: int
    total_bytes_str: str
    used_bytes: int
    used_bytes_str: str
    used_percent: float
    remaining_seconds: int
    used_at: datetime
    next_update_seconds: int
    validity_period_weeks: int
    subscriptions: list[str]

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
}


def _parse_ms_timestamp(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _parse_data(raw: dict) -> LteData:
    return LteData(
        pass_name=raw["passName"],
        pass_type=raw["passType"],
        pass_stage=raw["passStage"],
        session_state=raw["sessionState"],
        total_bytes=raw["initialVolume"],
        total_bytes_str=raw["initialVolumeStr"],
        used_bytes=raw["usedVolume"],
        used_bytes_str=raw["usedVolumeStr"],
        used_percent=raw["usedPercentage"],
        remaining_seconds=raw["remainingSeconds"],
        used_at=_parse_ms_timestamp(raw["usedAt"]),
        next_update_seconds=raw["nextUpdate"],
        validity_period_weeks=raw["validityPeriod"],
        subscriptions=raw["subscriptions"],
    )


async def get_lte_data() -> LteData:
    from config import API_URL, MOCK_MODE

    if MOCK_MODE or not API_URL:
        return _parse_data(MOCK_DATA)

    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as resp:
            resp.raise_for_status()
            raw = await resp.json()
            return _parse_data(raw)
