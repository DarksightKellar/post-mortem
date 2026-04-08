# Reddit Content Automation

Automated daily pipeline that turns funny Reddit threads into ~5-minute podcast-style YouTube videos with AI hosts.

## What it does

Runs on a schedule to:
1. **Fetch** top posts from curated subreddits
2. **Filter** out politics, NSFW, tragedy, and low-context content
3. **Score** candidates on reaction potential, laugh factor, and story payoff
4. **Select** the best 3 threads (+ 2 backups) per episode
5. **Outline** a structured episode plan
6. **Write** a two-host dialogue script
7. **Generate** TTS audio for both hosts (using free edge-tts)
8. **Render** video with slides and caption support
9. **Publish** to YouTube

Two AI hosts react to each thread in a recurring show format — witty banter, not plain narration.

## Quick Start

### Prerequisites

- Python 3.11+
- `ffmpeg` installed and on PATH (for audio/video rendering)

### Install

Create a virtual environment (required on Debian/Ubuntu — systems with PEP 668 block system-wide pip installs):

```bash
cd reddit-content-automation
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

> Note: If `python3 -m venv` fails, install the missing package first:
> `sudo apt install python3-venv`

### Run the pipeline

```bash
python -m reddit_automation.pipeline.run_daily
```

### Run the dashboard

```bash
python -m reddit_automation.dashboard.server
```

Opens on http://127.0.0.1:8888 — shows stats, run history, config viewer, and cron controls.

### Run tests

```bash
pytest
```

Strict TDD: I/O boundaries (TTS, FFmpeg, YouTube, Reddit) are monkeypatched so no side effects.

## Dependencies

All dependencies are managed via `pyproject.toml`. Install with `pip install -e ".[dev]"`.

**Python packages:** PyYAML, edge-tts, google-api-python-client, google-auth, google-auth-oauthlib, google-auth-httplib2, pytest (dev).

**External binaries:** ffmpeg + ffprobe (system install, not pip-managed).

**API keys (optional, via environment variables):**

| Variable | Purpose |
|----------|---------|
| `FAL_KEY` | Fal.ai API key for AI image generation (visuals) |
| `YOUTUBE_API_KEY` | YouTube Data API key (publishing) |

## Clients

| Client | Status | Implementation |
|--------|--------|----------------|
| Reddit | Stub | Uses test data from config, no praw dependency |
| LLM | Stub | Placeholder client, no HTTP calls |
| TTS | Working | Uses edge-tts (free, no API key) |
| YouTube | Wired | Uses google-api-python-client, needs OAuth2 credentials |
| Fal.ai | Working | Uses raw urllib (no extra pip dep) |

## Current State

| Stage | Status |
|-------|--------|
| Fetch | Stub (uses test data) |
| Filter | Done |
| Score | Stub (LLM client is placeholder) |
| Select | Done |
| Outline | Stub |
| Script | Stub |
| TTS (Voice) | Working (edge-tts) |
| Visuals | Stub |
| Render | Stub (FFmpeg module wired) |
| Publish | Stub (YouTube client wired) |
| Notify | Done |
| Dashboard | Running |
| Pipeline orchestration | Done (run_daily) |

## Architecture

```
reddit-content-automation/
├── src/reddit_automation/
│   ├── pipeline/       # Pipeline stages: fetch, filter, score, select, outline, script, voice, visuals, render, publish, notify
│   ├── clients/        # External service clients: Reddit, LLM, TTS, YouTube, Fal.ai
│   ├── models/         # Data models: candidate, episode, score
│   ├── storage/        # SQLite backing: db, candidates, episodes, runs
│   ├── utils/          # Config, logging, paths, text, ffmpeg, retry
│   └── dashboard/      # HTTP server + HTML UI
├── config/config.yaml  # All tunable config
├── data/               # SQLite DB and schema
├── tests/              # Strict TDD
└── schemas/            # JSON schemas for pipeline data
```

Pipeline order: `fetch -> hard filter -> store -> score -> select -> outline -> script -> voice -> visuals -> render -> publish -> notify`

## Design Rules

- Rejected candidates do not enter the main DB
- Heavily rewrite content — no long verbatim Reddit quotes
- Max 12 direct-quote words per line
- Configurable scoring weights (sum to ~1.0)
- Anything likely tuned in the future goes in YAML or prompt files, not code
