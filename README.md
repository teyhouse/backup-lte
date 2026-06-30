# LTE Bot

Discord bot that monitors Telekom LTE data plan usage via `pass.telekom.de`. Posts a daily summary, provides an on-demand `/lte` slash command, and alerts when usage exceeds 90%.

## Setup

```bash
cp .env.example .env
# Fill in BOT_TOKEN, CHANNEL_ID, OWNER_ID, GUILD_ID
```

## Run

```bash
uv sync
uv run python main.py
```

## How it works

- **`/lte`** — Slash command that fetches the current data plan status and posts a formatted embed. Only the owner (OWNER_ID) can use it.
- **Daily summary** — Posts a full usage embed automatically at 08:00 CET/CEST to the configured channel.
- **Alert check** — Every 5 minutes, checks if usage exceeds 90%. Posts a warning once when crossing the threshold and an all-clear when it drops back below.

Data is fetched via HTTP GET from `pass.telekom.de/api/service/generic/v1/status`. Set `MOCK_MODE=true` in `.env` to use embedded test data instead.

For a detailed breakdown of each component, see `architecture.md`.
