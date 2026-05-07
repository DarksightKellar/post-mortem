# Postmortem

Postmortem turns source threads into podcast-style video episodes.

Current real pipeline:
- ingest URLs from the SQLite source queue, pasted Reddit post URLs, pasted Bluesky post URLs, fixture data, or authenticated bulk Reddit subreddit fetch
- filter and store survivors in SQLite
- score candidates locally with deterministic heuristics
- select episode items
- build placeholder outline/script/visual plan
- generate TTS audio with the configured TTS provider
- render video with HyperFrames HTML compositions
- optionally publish to YouTube
- optionally notify via Telegram

## Prerequisites

- Python 3.11+
- Node.js 22+ and `npx`
- HyperFrames CLI (`npx hyperframes doctor` should pass)
- ffmpeg + ffprobe on PATH

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If `python3 -m venv` fails on Debian/Ubuntu:

```bash
sudo apt install python3-venv
```

## Run the pipeline

Canonical entrypoint:

```bash
python -m postmortem
```

Notes:
- By default, `publishing.youtube_auto_publish` is `false`, so the pipeline can succeed locally without YouTube auth.
- No-key queue mode uses `sources.source_mode: queue` and reads pending URLs from the SQLite `source_queue` inbox; no-key Reddit URL mode can still use `sources.reddit_post_urls`; fixture-backed runs can still use `reddit_test_data.submissions` without network access.
- Bulk subreddit Reddit fetch still requires OAuth credentials.
- Render uses HyperFrames. The pipeline writes a deterministic HTML composition under `render_dir/.hyperframes/<episode>/`, runs `hyperframes lint`, `validate`, `inspect`, then renders the final MP4.

## Run the dashboard

```bash
python -m postmortem.dashboard.server
```

Dashboard:
- URL: http://127.0.0.1:8888
- shows run history and progress
- lets you edit user-provided config values
- lets you trigger runs and pause/resume cron

## Tests

```bash
pytest
```

## Required / optional setup

### Source queue inbox

For the reusable no-key operator flow, set `sources.source_mode: queue` and enqueue URLs:

```bash
python -m postmortem.sources enqueue https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i
python -m postmortem.sources list
```

The queue records each URL as:

- `pending` before fetch
- `processing` while claimed by a run
- `done` with the produced `candidate_id`
- `failed` with an error message and incremented attempt count

Duplicate URLs are ignored without resetting completed work.

### No-key Reddit URL mode

For the MVP path, paste specific Reddit thread URLs into config:

```yaml
sources:
  reddit_post_urls:
    - https://www.reddit.com/r/AskReddit/comments/abc123/funniest_thing/
```

When `sources.reddit_post_urls` is present and non-empty, it takes priority over `sources.subreddits` and does **not** require OAuth credentials. The pipeline makes one small public thread request per pasted URL.

If Reddit still blocks that URL request, the pipeline fails with a clear manual fallback message: paste the post title, body, and useful comments into `reddit_test_data.submissions`.

### Bulk subreddit fetch

Bulk subreddit fetch requires OAuth/Data API credentials.

Create credentials:
1. Go to https://www.reddit.com/prefs/apps
2. Click **create app** or **create another app**.
3. Choose **script** for local automation.
4. Use any name, e.g. `Postmortem Local Fetch`.
5. Set redirect URI to `http://localhost:8080` even though this app uses client credentials.
6. After creation:
   - client ID is the short string under the app name
   - client secret is labeled `secret`

Then export credentials before running live fetch:

```bash
export REDDIT_CLIENT_ID="your_reddit_app_client_id"
export REDDIT_CLIENT_SECRET="your_reddit_app_client_secret"
export REDDIT_USER_AGENT="Postmortem/0.1 by u/your_reddit_username"
```

Or copy `.env.example` to `.env` and source it manually:

```bash
cp .env.example .env
# edit .env, then:
set -a
source .env
set +a
```

Never commit real Reddit secrets. `.env` is ignored by git.

Optional services:
- HyperFrames video rendering
  - install/check: `npx hyperframes doctor`
  - config: `render.engine: hyperframes`
  - generated composition source: `<render_dir>/.hyperframes/<episode>/index.html`
- QwenTTS via ComfyUI
  - install/run ComfyUI separately
  - install custom node: https://github.com/1038lab/ComfyUI-QwenTTS
  - verify ComfyUI is reachable at `tts.comfy_qwen_tts.base_url`
  - set `tts.provider: comfy_qwen_tts`
  - use host `qwen_voice_id` values such as `Ryan` and `Serena`
- YouTube publishing
  - set `publishing.youtube_auto_publish: true`
  - provide OAuth client secrets file and token path in dashboard/config
- Telegram notifications
  - provide `alerts.telegram_bot_token`
  - provide `alerts.telegram_chat_id`

## Current implementation truth

Working now:
- source queue inbox with pending/processing/done/failed state for Reddit and Bluesky URLs
- no-key pasted Reddit URL ingestion, pasted Bluesky URL ingestion, authenticated bulk Reddit fetch, fixture override, 429 retry/backoff, pacing, and comment request budgeting
- filter
- SQLite storage
- local scoring
- selection
- configured TTS voice generation
- HyperFrames HTML composition render
- dashboard config editing

Still placeholder / basic:
- visual planning

## License

MIT. See `LICENSE`.
