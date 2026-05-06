# Postmortem Production Gap Backlog

This file records the ten production gaps found in the audit.

Important distinction:
- A mechanically runnable pipeline is not the same thing as a production-ready pipeline.
- Placeholder creative output, dishonest fallback reporting, and fragile runtime edges all count as production blockers.

## Original audit order

This file now preserves the original audit order instead of my later execution reorder.
That reorder was my mistake.

1. [x] Outline generation is explicit placeholder fabrication, not production editorial logic.
   - Fixed in `src/reddit_automation/pipeline/outline.py`
   - Covered by `tests/test_outline.py`

2. [x] Script generation is canned skeleton output, not production writing.
   - Fixed in `src/reddit_automation/pipeline/script.py`
   - Covered by `tests/test_script.py`, `tests/test_integration_script_voice.py`, `tests/test_integration_full_media_pipeline.py`

3. [ ] Visual planning is just a thin wrapper around placeholder notes, not a production visual plan.
   - Evidence: `src/reddit_automation/pipeline/visuals.py`

4. [ ] Fallback visuals degrade to a black-screen video instead of a usable render fallback.
   - Evidence: `src/reddit_automation/utils/ffmpeg.py`

5. [ ] Render fallback metadata is not wired honestly from the real render path to pipeline/dashboard state.
   - Evidence: `src/reddit_automation/pipeline/render.py`, `src/reddit_automation/pipeline/run_daily.py`, `src/reddit_automation/dashboard/server.py`

6. [x] Voice stage fails on a clean run because `output_dir` is not created before stitching audio.
   - Fixed in `src/reddit_automation/pipeline/voice.py`
   - Covered by `tests/test_voice.py::test_generate_episode_audio_creates_output_dir_before_stitching`

7. [x] Public Reddit JSON fetching is not production-hardened against live runtime failures and rate limits.
   - Fixed by adding a no-key pasted-URL ingestion path and keeping authenticated Reddit OAuth/Data API for bulk subreddit fetch in `src/reddit_automation/clients/reddit_client.py`
   - Added 429 retry/backoff, request pacing, comment thread budgeting, and a clear manual fallback error for blocked pasted URLs
   - Covered by `tests/test_reddit_client.py`, `tests/test_validate_config.py`
   - Operator setup is now optional: `sources.reddit_post_urls` works without OAuth; bulk subreddit fetch still requires `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and `REDDIT_USER_AGENT`

8. [x] Notification failures can incorrectly fail or mask pipeline runs.
   - Fixed in `src/reddit_automation/pipeline/notify.py`, `src/reddit_automation/pipeline/run_daily.py`
   - Covered by `tests/test_notify.py`, `tests/test_run_daily.py`

9. [ ] First-run YouTube auto-publish is not headless-safe because OAuth bootstrap still requires an interactive consent flow.
   - Evidence: `src/reddit_automation/clients/youtube_client.py`

10. [ ] Tests overstate readiness by normalizing placeholder output and mocked fallbacks as acceptable production behavior.
   - Evidence: `tests/test_outline.py`, `tests/test_script.py`, `tests/test_visuals.py`, `tests/test_render.py`, `tests/test_run_daily.py`
