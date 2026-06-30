from datetime import datetime

import discord

from data_fetcher import LteData


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


def _format_bytes(b: int) -> str:
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f} GB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"


def _format_duration(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds // 86400}d {seconds % 86400 // 3600}h"
    if seconds >= 3600:
        return f"{seconds // 3600}h {seconds % 3600 // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def _dt_short(dt: datetime) -> str:
    return dt.strftime("%b %d, %H:%M UTC")


def build_embed(data: LteData) -> discord.Embed:
    color = _usage_color(data.used_percent)
    bar = _usage_bar(data.used_percent)

    status_emoji = "🟢" if data.status == "active" else "🔴"
    description = (
        f"{status_emoji} {data.status.title()} · "
        f"{data.validity_period_weeks}-week plan"
    )

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
            f"└ {_format_bytes(data.remaining_bytes)} remaining"
        ),
        inline=True,
    )

    embed.add_field(
        name="Time",
        value=(
            f"**{data.remaining_days} days** remaining\n"
            f"└ Next update: {_format_duration(data.next_update_seconds)}"
        ),
        inline=True,
    )

    subs = ", ".join(data.subscriptions) if data.subscriptions else "—"
    embed.add_field(
        name="Subscriptions",
        value=subs,
        inline=True,
    )

    embed.set_footer(
        text=f"Last used: {_dt_short(data.used_at)} · pass.telekom.de"
    )

    return embed


def build_alert_embed(data: LteData) -> discord.Embed:
    remaining = _format_bytes(data.remaining_bytes)
    embed = discord.Embed(
        title="⚠️ Data Usage Alert",
        description=(
            f"Usage has reached **{data.used_percent:.0f}%** — "
            f"only **{remaining}** remaining!"
        ),
        color=0xE74C3C,
    )
    embed.add_field(
        name="Volume",
        value=f"{data.used_bytes_str} / {data.total_bytes_str}",
    )
    embed.add_field(name="Remaining", value=remaining)
    embed.add_field(name="Days left", value=f"{data.remaining_days} days")
    embed.set_footer(
        text=f"Checked: {_dt_short(data.used_at)} · pass.telekom.de"
    )
    return embed


def build_all_clear_embed(percent: float, remaining_gb: int) -> discord.Embed:
    return discord.Embed(
        title="✅ Usage Normalized",
        description=(
            f"Usage is back to **{percent:.0f}%** "
            f"({remaining_gb} GB remaining)."
        ),
        color=0x2ECC71,
    )
