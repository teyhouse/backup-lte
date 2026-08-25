# LTE Bot

[![CI](https://github.com/teyhouse/backup-lte/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/teyhouse/backup-lte/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Discord bot that monitors Telekom LTE data plan usage via `pass.telekom.de`. Posts a daily summary, provides an on-demand `/lte` slash command, and alerts when usage exceeds 90%.

## Setup

```bash
cp .env.example .env
# Fill in BOT_TOKEN, CHANNEL_ID, OWNER_ID, GUILD_ID
```

```bash
uv sync
```

## Run

### Foreground (testing)

```bash
uv run python main.py
```

### Background with systemd (recommended)

Create `/etc/systemd/system/lte-bot.service`:

```ini
[Unit]
Description=LTE usage Discord bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/lte-bot
ExecStart=/home/pi/.local/bin/uv run python main.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable --now lte-bot
journalctl -u lte-bot -f   # follow logs
```

### Background (simple: nohup)

```bash
nohup uv run python main.py > bot.log 2>&1 &
```

Stop with: `kill $(pgrep -f "main.py")`

## How it works

- **`/lte`** — Slash command that fetches the current data plan status and posts a formatted embed. Only the owner (OWNER_ID) can use it.
- **Daily summary** — Posts a full usage embed automatically at 08:00 CET/CEST to the configured channel.
- **Alert check** — Every 5 minutes, checks if usage exceeds the alert threshold (`ALERT_THRESHOLD`, default 90%). Posts a warning once when crossing the threshold and an all-clear when it drops back below.

Data is fetched by scraping the customer-facing HTML page at `pass.telekom.de/home` (no auth required when behind Telekom LTE). Set `MOCK_MODE=true` in `.env` to use embedded test data instead.

> **Note:** This project originally used the JSON usage-data API at `pass.telekom.de/api/service/generic/v1/status`. Telekom is gradually disabling that endpoint for customers, so the bot now parses the HTML page instead.

## Development

```bash
uv sync              # installs runtime + dev dependencies
uv run ruff check .  # lint
uv run ruff format . # format
uv run python -m unittest discover -s tests  # run tests
```
