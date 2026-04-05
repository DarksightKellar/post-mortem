# Reddit Content Automation

Zero-touch pipeline: fetch Reddit threads → score → two-host script → TTS → AI visuals → render → publish to YouTube.

## Quick Start

```bash
# Install dependencies
cd ~/projects/reddit-content-automation
uv sync  # or: pip install -e .

# Bootstrap the database
python scripts/bootstrap_db.py

# Dry run (no network, no publish)
python scripts/run_pipeline.py

# Run the full pipeline
python scripts/run_pipeline.py

# Start the dashboard
python -m reddit_automation.dashboard.server
```

## Architecture

```
Reddit ──▶ Fetch ──▶ Filter ──▶ Score (LLM) ──▶ Select ──▶ Outline ──▶ Script
  │                                                                 │
  └──────────────────────────────────────────────────────┐          │
                                                         ▼          ▼
Publish ◀─────────────────────── Render ◀────── Audio (TTS)  +  Visuals (fal.ai)
  │                                      ║                     ║
YouTube                                ffmpeg              image gen
Telegram                                  ║                     ║
                                      └─── stitched ──────────┘
```

## Pipeline Steps

| Step | Module | What it does |
|------|--------|-------------|
| **fetch** | `pipeline/fetch.py` | Pulls threads from 5–8 curated subreddits (48h lookback) |
| **filter** | `pipeline/filter.py` | Removes NSFW, politics, tragedy, culture-war, low-signal |
| **store** | `pipeline/store.py` | Persists candidates + comments to SQLite |
| **score** | `pipeline/score.py` | LLM scores on reaction potential (40%), laugh factor (25%), etc. |
| **select** | `pipeline/select.py` | Picks top 3–5 primary threads + backups |
| **outline** | `pipeline/outline.py` | Structures cold open, segments, outro with visual notes |
| **script** | `pipeline/script.py` | Writes two-host dialogue comedy commentary |
| **voice** | `pipeline/voice.py` | Generates per-line TTS clips via edge-tts, stitches with ffmpeg |
| **visuals** | `pipeline/visuals.py` + `generate_scenes.py` | Builds scene plan, generates images via fal.ai |
| **render** | `pipeline/render.py` | Slideshow render — each image timed equally across audio duration |
| **publish** | `pipeline/publish.py` | Uploads to YouTube, notifies via Telegram |
| **notify** | `pipeline/notify.py` | Telegram Bot API alerts (success/failure) |

## Configuration

All tuneable settings in `config/config.yaml`:

```yaml
project:
  episode_target_minutes: 5
  primary_lookback_hours: 48
  fallback_lookback_days: 7

sources:
  subreddits:
    - AskReddit
    - AmItheAsshole
    - tifu
    - facepalm
    - MaliciousCompliance

scoring:
  weights:
    reaction_potential: 0.40
    laugh_factor: 0.25
    story_payoff: 0.15
    clarity_after_rewrite: 0.10
    comment_bonus: 0.10

publishing:
  youtube_auto_publish: true
  default_privacy_status: private  # change to 'public' when ready

alerts:
  telegram_on_success: true
  telegram_on_failure: true
```

## Credentials

| Key | Where | Purpose |
|-----|-------|---------|
| `REDDIT_CLIENT_ID` | Env or config | Reddit API access |
| `REDDIT_CLIENT_SECRET` | Env or config | Reddit API access |
| `FAL_KEY` | Env var | AI image generation (fal.ai) |
| LLM API key | Config | Scoring + script generation |
| YouTube OAuth2 `client_secret.json` | `~/.hermes/youtube_credentials.json` | Upload to YouTube |
| `TELEGRAM_BOT_TOKEN` | Config | Success/failure notifications |
| `TELEGRAM_CHAT_ID` | Config | Where to send notifications |

## Dashboard

```bash
python -m reddit_automation.dashboard.server
```

Built-in web UI at `http://127.0.0.1:8888`:
- 📊 Stats cards (total runs, success rate, 7-day count)
- 📋 Recent runs table with status badges
- ⏯ Cron toggle / Run Now buttons
- ⚙️ Config viewer and live updates
- Auto-refreshes every 30s

## Cron Scheduling

Daily pipeline run at 9 AM (configurable):
```bash
# Pause/resume via cronjob tool
hermes "pause the reddit cron"
hermes "resume the cron"
hermes "run the cron now"
```

## Error Recovery

Every pipeline stage retries on transient errors (ConnectionError, OSError, TimeoutError):
- **3 retries** with exponential backoff (2s, 4s, 8s)
- Configurable via `config.yaml`:
  ```yaml
  retry:
    max_retries: 5
    base_delay: 3.0
  ```
- Non-retryable errors (ValueError, KeyError) fail fast
- All failures logged to SQLite + Telegram notification

## Testing

```bash
# Full suite — 131 tests
uv run python -m pytest tests/ -q

# By category
uv run python -m pytest tests/test_run_daily.py -q          # Pipeline orchestration
uv run python -m pytest tests/test_integration_*.py -q      # Integration tests
uv run python -m pytest tests/test_youtube_client.py -q     # YouTube API
uv run python -m pytest tests/test_dashboard_server.py -q    # Dashboard
```

## Project Structure

```
src/reddit_automation/
├── clients/              # External API clients
│   ├── llm_client.py    # OpenAI/compatible LLM
│   ├── reddit_client.py # PRAW Reddit wrapper
│   ├── tts_client.py    # edge-tts integration
│   └── youtube_client.py # YouTube Data API v3 (OAuth2)
├── dashboard/           # Web dashboard
│   ├── server.py        # HTTP server + JSON API
│   └── template.html    # Responsive dark-mode UI
├── models/              # Data models
│   ├── candidate.py     # Reddit candidate schema
│   ├── episode.py       # Episode planning model
│   └── score.py         # Scoring result schema
├── pipeline/            # Pipeline stages
│   ├── fetch.py         # Reddit thread fetching
│   ├── filter.py        # Content filtering
│   ├── score.py         # LLM scoring engine
│   ├── script.py        # Two-host dialogue generation
│   ├── voice.py         # TTS + audio stitching
│   ├── generate_scenes.py # fal.ai image generation
│   ├── render.py        # Video rendering orchestration
│   ├── run_daily.py     # Daily pipeline entry point
│   └── publish.py       # YouTube + Telegram publish
├── storage/             # Persistence layer
│   ├── db.py            # SQLite abstraction
│   ├── candidates.py    # Candidate/comment tables
│   ├── episodes.py      # Episode records
│   └── runs.py          # Run log with FTS5 search
└── utils/               # Shared utilities
    ├── config.py        # YAML loader + validation
    ├── fal_client.py    # fal.ai REST client
    ├── ffmpeg.py        # ffmpeg subprocess wrappers
    ├── retry.py         # Retry-with-backoff
    └── text.py          # Text processing helpers
```

## Status

✅ 131 tests passing  
✅ End-to-end integration tests  
✅ Config validation (fail-fast)  
✅ Error recovery with retries  
✅ Dashboard with live monitoring  
✅ Cron scheduling (daily at 9 AM)  

🔄 YouTube OAuth2 setup pending — just add credentials and it'll work.

## License

Private project — do not distribute.
