# LTE Bot — Architecture

## Overview

A Discord bot that monitors Telekom LTE data plan usage. It runs persistently on a
Raspberry Pi, posts a daily usage summary to a configured channel, provides an
on-demand `/lte` slash command, and alerts when usage exceeds 90%.

---

## Project Structure

```
lte-bot/
├── pyproject.toml          # uv project definition & dependencies
├── main.py                 # Entry point — bot lifecycle
├── config.py               # Centralised config from .env
├── data_fetcher.py         # LteData dataclass, mock data, HTTP fetcher
├── cogs/
│   ├── __init__.py
│   ├── lte_commands.py     # /lte slash command (owner-only)
│   └── scheduler.py        # Daily summary + 5-min alert loops
├── utils/
│   ├── __init__.py
│   └── formatter.py        # Discord embed builders
├── .env                    # Runtime secrets (gitignored)
├── .env.example            # Template for .env
└── architecture.md         # This file
```

---

## Component Breakdown

### 1. `main.py` — Entry Point

Creates a `commands.Bot` subclass (`LteBot`) with default intents and loads both
cogs via `setup_hook` using `load_extension`. This approach keeps `main.py`
minimal — it only knows *which* cogs exist, not *how* they work.

```python
class LteBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.lte_commands")
        await self.load_extension("cogs.scheduler")
```

The bot instance is a module-level singleton, created once and passed to every
cog's `__init__`.

### 2. `config.py` — Configuration

Reads `.env` via `python-dotenv` and exports typed constants consumed by every
other module. Key values:

| Variable | Type | Purpose |
|---|---|---|---|
| `BOT_TOKEN` | `str` | Discord bot login token |
| `CHANNEL_ID` | `int` | Target channel for auto-posts |
| `OWNER_ID` | `int` | Discord user ID allowed to use `/lte` |
| `GUILD_ID` | `int` | Server ID for instant slash command sync |
| `MOCK_MODE` | `bool` | Use mock data (development fallback); defaults to `false` |
| `API_URL` | `str` | Telekom API endpoint (`pass.telekom.de/...`) |
| `SUMMARY_TIME` | `datetime.time` | 08:00 Europe/Berlin (CET/CEST-aware) |

### 3. `data_fetcher.py` — Data Layer

Two responsibilities:

**a) `LteData` dataclass** — Mirrors the flat JSON from `pass.telekom.de`.
The real API returns a flat structure (not nested like the original mock), so
`LteData` stores the raw fields plus computed `@property` helpers:

| Field | Source | Notes |
|---|---|---|
| `pass_name` | `passName` | e.g. "MagentaMobil Prepaid M" |
| `pass_type` | `passType` | Numeric code (103 = prepaid) |
| `pass_stage` | `passStage` | Internal stage counter |
| `session_state` | `sessionState` | 0 = active |
| `total_bytes` / `total_bytes_str` | `initialVolume` / `initialVolumeStr` | e.g. 21474836480 / "20 GB" |
| `used_bytes` / `used_bytes_str` | `usedVolume` / `usedVolumeStr` | e.g. 0 / "0 kB" |
| `used_percent` | `usedPercentage` | 0.0 – 100.0 |
| `remaining_seconds` | `remainingSeconds` | Seconds until plan expiry |
| `used_at` | `usedAt` | Unix ms timestamp → `datetime` |
| `next_update_seconds` | `nextUpdate` | Seconds until next API refresh (usually 10800 = 3h) |
| `validity_period_weeks` | `validityPeriod` | Plan duration in weeks |
| `subscriptions` | `subscriptions` | Array of add-on names |

**Computed `@property` fields:**
- `remaining_bytes = total_bytes - used_bytes`
- `remaining_days = remaining_seconds // 86400`
- `status = "active"` if `session_state == 0` else `"inactive"`

**b) `get_lte_data()` — The single async function** that all consumers call.
It decides the source at runtime:

```python
async def get_lte_data() -> LteData:
    if MOCK_MODE or not API_URL:
        return _parse_data(MOCK_DATA)     # ← hard-coded dict (dev fallback)
    async with aiohttp.ClientSession() as session:
        resp = await session.get(API_URL)  # ← real HTTP call
        return _parse_data(await resp.json())
```

**Real API is the default** (`MOCK_MODE=false`). The `MOCK_DATA` dict is a
development fallback — it mirrors the real API's flat shape. Both code paths
use the same `_parse_data()` function, so switching is transparent.

### 4. `utils/formatter.py` — Embed Builders

Pure functions that take `LteData` and return `discord.Embed` objects. No
Discord client connection is needed to construct embeds, making them easily
testable.

Three embed types:

- **`build_embed()`** — Full summary. Includes a text-based progress bar
  (`████░░░░░░`), color-coded by usage (green <80%, yellow 80-90%, red >90%),
  and fields for volume (using API's `usedBytesStr` / `totalBytesStr`), time
  remaining, next-update countdown (formatted from seconds), and the list of
  active subscriptions. The phone number mask, cost, and account fields were
  removed because the real Telekom API does not expose that data.

- **`build_alert_embed()`** — Red warning sent when usage crosses 90%.
  Shows the exact percentage and human-readable remaining volume.

- **`build_all_clear_embed()`** — Green notification sent when usage drops back
  below 90% after having been in alert state.

### 5. `cogs/lte_commands.py` — Slash Command Cog

Registers a single global slash command: `/lte`.

**Authorization:** Checks `interaction.user.id` against `OWNER_ID`. Rejects
unauthorised users with an ephemeral "not authorized" message (only they see
it). Returns immediately without revealing data.

**Flow:** defer → fetch data → build embed → followup.

### 6. `cogs/scheduler.py` — Task Loops Cog

Manages two background `tasks.loop` instances that run for the bot's lifetime:

#### Daily Summary (`08:00 CET/CEST`)
- Triggered by `tasks.loop(time=SUMMARY_TIME)`, where `SUMMARY_TIME` is a
  timezone-aware `datetime.time` using `Europe/Berlin`. Discord.py handles the
  scheduling; the loop fires once per day at the specified wall-clock time.
- Fetches data, builds a full embed, posts to `CHANNEL_ID`.
- Uses `before_loop` to wait for the bot to be ready before the first run.

#### Alert Check (every 5 minutes)
- Triggered by `tasks.loop(minutes=5)`.
- Fetches data, checks `used_percent >= 90`.
- **State machine** via `_was_alerted` flag:
  - `was_alerted=False` → now ≥90% → send alert embed, set `_was_alerted=True`
  - `was_alerted=True` → now <90% → send all-clear embed, reset flag
  - Otherwise → do nothing (no repeated spam)

Both loops share a `_channel()` helper that tries `get_channel` first (fast,
cached), then falls back to `fetch_channel` (API call). This handles the case
where the bot starts before the cache is populated.

---

## Data Flow

```
┌──────────┐   get_lte_data()   ┌──────────────┐
│  Cog /   │ ──────────────────→│ data_fetcher │
│ Command  │                    │              │
│          │←── LteData ────────│  MOCK_DATA   │
│          │                    │  or HTTP GET │
│          │                    └──────┬───────┘
│          │                           │
│          │   build_embed(data)       │
│          │──────────────────────┐    │
│          │                      ▼    │
│          │              ┌────────────┴───┐
│          │              │  formatter.py  │
│          │              │                │
│          │              │  discord.Embed │
│          │              └────────┬───────┘
│          │                       │
│          │   channel.send()      │
│          │───────────────────────▼
│          │              Discord API
└──────────┘
```

1. A trigger occurs: slash command, daily timer, or 5-minute timer.
2. `get_lte_data()` is called — returns an `LteData` dataclass.
3. The appropriate embed builder formats it into a `discord.Embed`.
4. The embed is sent to the configured channel via the Discord API.

---

## Cogs Architecture (discord.py)

Cogs are discord.py's module system. Each cog is a class inheriting from
`commands.Cog` that groups related commands, events, and tasks. They are loaded
via `load_extension()` which calls the module's `setup()` function.

**Why cogs were chosen:**

- **Modularity** — Each feature lives in its own file. Adding a new command
  means creating a new cog file and adding one `load_extension` line, not
  touching existing code.
- **Lifecycle hooks** — `cog_unload()` is called automatically when a cog is
  unloaded, allowing clean shutdown of task loops.
- **Namespace isolation** — Each cog has its own `self.bot` reference and its
  own private state. There are no global variables shared between features.
- **Toggleable** — Commenting out a `load_extension` line disables an entire
  feature without side effects.
- **Convention** — This is how the discord.py ecosystem is designed. Following
  the framework's patterns makes the code predictable.

**Extension protocol:** Every cog file must expose an async `setup(bot)` function
that calls `bot.add_cog()`. This is what `load_extension` looks for.

---

## Task Loop Lifecycle

1. When `Scheduler.__init__()` runs, it calls `.start()` on both loops.
2. Each loop's `before_loop` coroutine runs once before the first iteration —
   it awaits `bot.wait_until_ready()` to ensure the bot is connected to Discord.
3. The daily loop uses `time=` (absolute wall-clock time, timezone-aware).
4. The alert loop uses `minutes=` (fixed interval from last completion).
5. When the bot shuts down or the cog is unloaded, `cog_unload()` calls
   `.stop()` on both loops.

---

## Permission Model

| Action | Who can trigger | Check |
|---|---|---|
| `/lte` command | Only `OWNER_ID` | `interaction.user.id == OWNER_ID` |
| Daily summary | Nobody (auto) | — |
| Alert | Nobody (auto) | — |

Unauthorised `/lte` users receive an ephemeral "not authorized" message.

---

## Dependencies (managed via `uv`)

All packages are declared in `pyproject.toml` and installed into a local
`.venv` by `uv sync`:

| Package | Purpose |
|---|---|
| `discord-py` | Discord API client, command framework, task loops |
| `python-dotenv` | Load `.env` into `os.environ` |
| `aiohttp` | Async HTTP client for the real Telekom API call |

---

## Mock Data (Development Fallback)

Current state: `MOCK_MODE=false` in `.env`. The bot fetches live data from
`pass.telekom.de` by default.

To use mock data instead (e.g. for testing without a network connection):

1. Set `MOCK_MODE=true` in `.env`.
2. Restart the bot.

The embedded `MOCK_DATA` dict mirrors the real API's flat structure and is
parsed by the same `_parse_data()` function.

## Future API Changes

If the real API endpoint changes or requires authentication, only
`get_lte_data()` in `data_fetcher.py` needs to be updated — no other file is
affected. The `_parse_data()` function is the single adapter between the raw
JSON and the rest of the codebase.
