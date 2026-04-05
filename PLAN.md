# Reddit Content Automation Project Plan

## Goal
Build a fully automated daily content pipeline that:
- finds funny Reddit threads people are laughing at
- rewrites them into original commentary
- produces ~5-minute podcast-style YouTube videos
- uses 2 AI hosts reacting to 3–5 Reddit threads
- can later be repurposed into Shorts/TikTok-style outputs

## Product Direction Chosen
- V1 format: YouTube audio/podcast-style video
- Show style: two-host banter/reaction format
- Content format: thread summary + best comments + host reactions
- Automation level: fully automated daily pipeline
- Content usage rule: heavily rewrite/summarize into original commentary

## Editorial / Format Decisions
- Daily episode
- Target runtime: 5 minutes
- Typical structure:
  1. 10–15 second cold open / hook
  2. Story 1 reaction
  3. Story 2 reaction
  4. Story 3 reaction
  5. Outro / callback / tomorrow tease
- Use 3 primary selected threads per episode
- Keep 2 backups
- For each selected thread:
  - summarize the thread
  - include best comments
  - have both hosts react
- Long threads are allowed, but must be compressed hard to only the key beats

## Host Format
- Host 1: same witty male lead every episode
- Host 2: grounded by default, adaptive when useful depending on segment
- Goal is a recurring “show” feel, not plain narration

## Sourcing Rules
### Source pool
- Use 5–8 curated subreddits initially
- Fetch from hot + top
- Primary lookback window: last 48 hours
- Fallback pool: best from last 7 days

### Initial subreddit pack
- AskReddit
- AmItheAsshole
- tifu
- facepalm
- MaliciousCompliance
- pettyrevenge
- antiwork
- greentext

### Candidate bundle per post
Each candidate should include:
- post/thread text
- top 5 comments
- metadata:
  - subreddit
  - title
  - body
  - url
  - author
  - created_utc
  - upvotes
  - comment_count

### Candidate volume
- Gather about 40 candidates per day before final scoring/selection

## Hard Filtering Rules
Apply hard filters before storing candidates in the DB.
Rejected items should not enter the main DB.

Reject content that is:
- politics
- culture-war bait
- tragedy-heavy
- abuse-heavy
- death-heavy
- sexual / NSFW-heavy
- low-context junk
- too confusing to rewrite cleanly
- funny only because of shock value
- too dependent on missing context
- near-duplicate of another selected story theme that day

Pipeline order:
fetch -> hard filter -> store survivors -> score -> select

## Scoring Logic
### Key principle
Reaction potential matters most.
Laugh factor is second most important.
Reddit metrics support scoring but do not drive it.

### Scoring dimensions
Score each surviving candidate on 1–10 for:
- reaction_potential
- laugh_factor
- story_payoff
- clarity_after_rewrite
- comment_bonus

### Default weights
These must be configurable, not hardcoded:
- reaction_potential: 0.40
- laugh_factor: 0.25
- story_payoff: 0.15
- clarity_after_rewrite: 0.10
- comment_bonus: 0.10

### Default thresholds
Also configurable:
- min_reaction_potential: 8
- min_laugh_factor: 7
- min_overall_score: 7.2

### Selection rules
- Score all stored candidates
- Drop anything with keep=false
- Prefer candidates with strong reaction potential and laugh factor
- Final episode should include humor variety; do not choose 3 highly similar threads
- Keep top 3 + 2 backups

## Configurability Rule
Anything likely to be tuned in future should live in config or prompt files, not code.

Configurable items include:
- scoring weights
- thresholds
- system prompts
- user prompt templates
- host personas
- subreddit allowlist
- filter rules
- lookback windows
- candidate counts
- comments per candidate
- episode length targets
- fallback behavior
- render settings
- publish settings
- alert settings

Design rule:
- Code handles workflow
- Config controls taste

## Recommended MVP Tech Stack
- Python for orchestration
- PRAW for Reddit ingestion
- LLM for scoring + outlining + scripting
- ElevenLabs for 2-host TTS
- ffmpeg for stitching/rendering
- templated slides first (not full AI-generated visuals)
- SQLite for storage/tracking
- YouTube Data API for upload
- cron/scheduled runner for daily automation
- Telegram alerts for success/failure

## Rendering Direction
Start simple:
- title card
- per-story background slide
- comment card slides
- captions
- optional music bed

Avoid fully AI-generated visuals in v1.
Templated slides should come first.

## Suggested Project Structure
```text
reddit-content-automation/
- README.md
- config/
  - config.yaml
  - subreddits.yaml
  - hosts.yaml
  - scoring.yaml
- prompts/
  - scoring_system.txt
  - scoring_user.txt
  - outline_system.txt
  - script_system.txt
  - title_system.txt
  - description_system.txt
- data/
  - app.db
  - cache/
  - runs/
  - exports/
- assets/
  - music/
  - fonts/
  - templates/
  - branding/
- output/
  - scripts/
  - audio/
  - video/
  - thumbnails/
  - logs/
- src/
  - main.py
  - pipeline/
    - fetch.py
    - filter.py
    - score.py
    - select.py
    - outline.py
    - script.py
    - voice.py
    - visuals.py
    - render.py
    - publish.py
    - notify.py
  - clients/
    - reddit_client.py
    - llm_client.py
    - tts_client.py
    - youtube_client.py
  - models/
    - candidate.py
    - episode.py
    - score.py
  - storage/
    - db.py
    - candidates.py
    - episodes.py
    - runs.py
  - utils/
    - config.py
    - logging.py
    - text.py
    - ffmpeg.py
  - schemas/
    - episode_plan.schema.json
    - scoring_result.schema.json
- scripts/
  - run_daily.sh
  - backfill_candidates.py
  - test_render.py
- tests/
  - test_filter.py
  - test_score.py
  - test_select.py
  - test_script.py
  - test_pipeline.py
```

## Initial Config Shape
Use a human-editable YAML config system.
Prompts should live in separate files, referenced by config.

Recommended top-level config sections:
- project
- sources
- filters
- comments
- scoring
- hosts
- prompts
- scripting
- render
- publishing
- alerts

## Config Skeleton
```yaml
project:
  episode_target_minutes: 5
  primary_lookback_hours: 48
  fallback_lookback_days: 7
  candidate_target: 40
  final_pick_count: 3
  backup_pick_count: 2

sources:
  subreddits:
    - AskReddit
    - AmItheAsshole
    - tifu
    - facepalm
    - MaliciousCompliance
    - pettyrevenge
    - antiwork
    - greentext
  fetch_modes:
    - hot
    - top

filters:
  exclude_categories:
    - politics
    - culture_war
    - tragedy
    - abuse
    - death
    - nsfw
  exclude_low_context: true
  dedupe_similar_posts: true

comments:
  top_n_per_candidate: 5

scoring:
  weights:
    reaction_potential: 0.40
    laugh_factor: 0.25
    story_payoff: 0.15
    clarity_after_rewrite: 0.10
    comment_bonus: 0.10
  thresholds:
    min_reaction_potential: 8
    min_laugh_factor: 7
    min_overall_score: 7.2

hosts:
  host_1:
    name: "Host 1"
    role: "main"
    persona: "Witty, humorous male lead. Sharp, funny, consistently entertaining."
    voice_id: "VOICE_ID_1"
  host_2:
    name: "Host 2"
    role: "adaptive"
    default_persona: "Grounded, reactive, natural setup-and-response energy."
    adaptive_mode: true
    voice_id: "VOICE_ID_2"

prompts:
  scoring_system_file: "prompts/scoring_system.txt"
  scoring_user_template_file: "prompts/scoring_user.txt"
  outline_system_file: "prompts/outline_system.txt"
  script_system_file: "prompts/script_system.txt"
  title_generation_system_file: "prompts/title_system.txt"
  description_generation_system_file: "prompts/description_system.txt"

scripting:
  target_segments: 3
  allow_range_segments: [3, 5]
  cold_open_seconds: 15
  outro_seconds: 40
  max_direct_quote_words: 12
  rewrite_aggressively: true

render:
  captions_enabled: true
  music_bed_enabled: true
  slide_style: "minimal"
  aspect_ratio: "16:9"

publishing:
  youtube_auto_publish: true
  generate_thumbnail_prompt: true

alerts:
  telegram_on_success: true
  telegram_on_failure: true
```

## Script / Planning Schema Direction
### Structured episode plan before final script
The planner should first output a structured episode plan, then a separate final dialogue script.

Suggested episode plan shape:
```yaml
episode_plan:
  episode_date: "2026-04-02"
  title_angle: "Absurd Reddit stories that gave the hosts the most to react to"
  cold_open:
    hook: "Short opening hook text"
    visual_note: "Fast montage / teaser"

  segments:
    - segment_order: 1
      reddit_post_id: "abc123"
      subreddit: "AskReddit"
      source_title: "Original Reddit title"
      setup_summary: "Compressed explanation of the thread"
      key_beats:
        - "Beat 1"
        - "Beat 2"
        - "Beat 3"
      selected_comments:
        - comment_id: "c1"
          reason: "Adds punchline"
        - comment_id: "c2"
          reason: "Good reaction bait"
      host_angle: "Why these hosts will be funny on this topic"
      host_2_mode: "grounded"
      visual_notes:
        - "Intro card"
        - "Comment card"
      estimated_seconds: 80

  outro:
    callback: "Closing line / payoff"
    tomorrow_tease: "Optional tease"
    visual_note: "End card"
```

### Final dialogue script shape
```yaml
episode_script:
  title: "..."
  lines:
    - speaker: "HOST_1"
      text: "..."
      scene_hint: "cold_open"
    - speaker: "HOST_2"
      text: "..."
      scene_hint: "cold_open"
    - speaker: "HOST_1"
      text: "..."
      scene_hint: "segment_1"
```

## Prompt Design Notes
Prompts should be editable without code changes.
Use separate prompt files instead of embedding large prompt text directly in YAML.

Important prompt rules:
- no long verbatim Reddit reading
- rewrite aggressively
- preserve only essential beats
- optimize for reaction moments
- Host 1 stays consistent every episode
- Host 2 can switch mode per segment
- comments are supporting material, not the whole segment

## Database Direction
Rejected candidates should not be stored in the main DB.
No `nsfw_flag` field is needed in the main candidates table.

Recommended MVP tables/entities:

### subreddit_sources
- id
- name
- enabled

### reddit_candidates
- reddit_post_id
- subreddit
- title
- body
- url
- author
- created_utc
- score
- comment_count
- raw_json
- fetched_at

### candidate_comments
- id
- reddit_post_id
- comment_id
- body
- score
- author
- created_utc

### candidate_scores
- reddit_post_id
- reaction_potential
- laugh_factor
- story_payoff
- clarity_after_rewrite
- comment_bonus
- keep
- reject_reason
- overall_score
- one_line_summary
- host_angle
- notes
- scored_at

### episodes
- id
- episode_date
- status
- title
- description
- script_path
- audio_path
- video_path
- youtube_video_id
- published_at

### episode_items
- episode_id
- reddit_post_id
- segment_order
- used_comments_json
- role_in_episode

### host_profiles
- id
- host_name
- voice_id
- persona_prompt
- active

### run_logs
- id
- run_date
- stage
- status
- message
- payload_json
- created_at

## Recommended Build Order
1. config loader + config files
2. fetch/filter/store
3. scoring
4. selection
5. episode outline schema
6. script generation
7. TTS
8. render
9. YouTube upload
10. scheduler + alerts

## Immediate Next Step
Design the actual config files and JSON schemas for the project.
