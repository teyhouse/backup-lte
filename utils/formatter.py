from datetime import datetime

import discord

from data_fetcher import LteData
from utils.humanize import format_bytes


def _usage_bar(percent: float, length: int = 12) -> str:
    filled = round(percent / 100 * length)
    empty = length - filled
    return "█" * filled + "░" * empty


def _usage_color(percent: float) -> int:
    if percent >= 90:
        return 0xE74C3C
    if percent >= 80:
        return 0xF1C40F
    return 0x2ECC71


def _dt_short(dt: datetime) -> str:
    return dt.strftime("%b %d, %H:%M UTC")


def _dt_date(dt: datetime) -> str:
    return dt.strftime("%b %d, %Y")


def build_embed(data: LteData) -> discord.Embed:
    color = _usage_color(data.used_percent)
    bar = _usage_bar(data.used_percent)

    status_emoji = "🟢" if data.status == "active" else "🔴"
    valid_str = _dt_date(data.valid_until) if data.valid_until else "—"
    description = f"{status_emoji} {data.status_text} · Valid until {valid_str}"

    embed = discord.Embed(
        title=f"📶 {data.pass_name}",
        description=description,
        color=color,
    )

    embed.add_field(
        name="Usage",
        value=f"`{bar}` **{data.used_percent:.0f}%**",
        inline=False,
    )

    embed.add_field(
        name="Volume",
        value=(
            f"**{data.used_bytes_str}** / {data.total_bytes_str} used\n"
            f"└ {format_bytes(data.remaining_bytes)} remaining"
        ),
        inline=True,
    )

    embed.add_field(
        name="Time",
        value=(f"**{data.remaining_days} days** remaining\n└ Valid until: {valid_str}"),
        inline=True,
    )

    embed.set_footer(text=f"Last update: {_dt_short(data.last_update)} · pass.telekom.de")

    return embed


def build_alert_embed(data: LteData) -> discord.Embed:
    remaining = format_bytes(data.remaining_bytes)
    embed = discord.Embed(
        title="⚠️ Data Usage Alert",
        description=(
            f"Usage has reached **{data.used_percent:.0f}%** — only **{remaining}** remaining!"
        ),
        color=0xE74C3C,
    )
    embed.add_field(
        name="Volume",
        value=f"{data.used_bytes_str} / {data.total_bytes_str}",
    )
    embed.add_field(name="Remaining", value=remaining)
    embed.add_field(name="Days left", value=f"{data.remaining_days} days")
    embed.set_footer(text=f"Checked: {_dt_short(data.last_update)} · pass.telekom.de")
    return embed


def build_all_clear_embed(percent: float, remaining_bytes: int) -> discord.Embed:
    return discord.Embed(
        title="✅ Usage Normalized",
        description=(
            f"Usage is back to **{percent:.0f}%** ({format_bytes(remaining_bytes)} remaining)."
        ),
        color=0x2ECC71,
    )
