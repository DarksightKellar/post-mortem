from __future__ import annotations

from reddit_automation.pipeline.fetch import fetch_candidates
from reddit_automation.pipeline.filter import filter_candidates
from reddit_automation.pipeline.notify import send_run_notification
from reddit_automation.pipeline.outline import build_episode_outline
from reddit_automation.pipeline.publish import publish_episode
from reddit_automation.pipeline.render import render_episode_video
from reddit_automation.pipeline.score import score_candidates
from reddit_automation.pipeline.script import write_episode_script
from reddit_automation.pipeline.select import select_episode_items
from reddit_automation.pipeline.store import store_candidates
from reddit_automation.pipeline.visuals import build_visual_plan
from reddit_automation.pipeline.voice import generate_episode_audio
from reddit_automation.storage.bootstrap import bootstrap_database
from reddit_automation.storage.runs import RunLogRepository
from reddit_automation.utils.config import load_config
from reddit_automation.utils.retry import retry_with_backoff

DEFAULT_RETRYABLE = (ConnectionError, OSError, TimeoutError)

def run_daily_pipeline(progress_callback=None) -> dict[str, object]:
    config = load_config()
    retry_cfg = config.get("retry", {})
    max_retries = retry_cfg.get("max_retries", 3) if retry_cfg else 3
    base_delay = retry_cfg.get("base_delay", 2.0) if retry_cfg else 2.0

    db = bootstrap_database(config)
    run_logs = RunLogRepository(db)
    stage_name = "fetch"
    outline = None

    def _run_stage(name, fn):
        """Run a single pipeline stage with retry-with-backoff."""
        nonlocal stage_name
        stage_name = name

        if progress_callback:
            progress_callback("running", name, f"Running: {name}")

        def _call():
            return fn()

        result = retry_with_backoff(
            _call,
            max_retries=max_retries,
            base_delay=base_delay,
            retryable_exceptions=DEFAULT_RETRYABLE,
        )

        if progress_callback:
            progress_callback("completed", name, f"Completed: {name}")

        return result

    try:
        raw_candidates = _run_stage("fetch", lambda: fetch_candidates(config))
        filtered_candidates = _run_stage("filter", lambda: filter_candidates(raw_candidates, config))
        _run_stage("store", lambda: store_candidates(filtered_candidates, db))
        scored_candidates = _run_stage("score", lambda: score_candidates(filtered_candidates, config))
        selected_items = _run_stage("select", lambda: select_episode_items(scored_candidates, config))

        if not selected_items.get("primary"):
            run_logs.log(
                run_date="unknown",
                stage="select",
                status="success",
                message="No episode generated",
                payload={"reason": "no_selected_items"},
            )
            send_run_notification("success", "No episode generated: no selected items", config)
            return {
                "status": "no_episode",
                "reason": "no_selected_items",
            }

        outline = _run_stage("outline", lambda: build_episode_outline(selected_items, config))
        script = _run_stage("script", lambda: write_episode_script(outline, config))
        audio_path = _run_stage("voice", lambda: generate_episode_audio(script, config))
        visual_plan = _run_stage("visuals", lambda: build_visual_plan(outline, config))
        video_path = _run_stage("render", lambda: render_episode_video(audio_path, visual_plan, config))
        publish_result = _run_stage("publish", lambda: publish_episode(video_path, {"title": script["title"]}, config))
    except Exception as exc:
        run_logs.log(
            run_date=outline["episode_date"] if outline and "episode_date" in outline else "unknown",
            stage=stage_name,
            status="failure",
            message=str(exc),
            payload={"error_type": exc.__class__.__name__},
        )
        send_run_notification("failure", str(exc), config)
        raise

    run_logs.log(
        run_date=outline["episode_date"],
        stage="publish",
        status="success",
        message="Episode published successfully",
        payload={
            "title": script["title"],
            "video_path": video_path,
            "publish_result": publish_result,
        },
    )
    send_run_notification("success", f"Episode published successfully: {script['title']}", config)
    return {
        "status": "success",
        "run_date": outline["episode_date"],
        "title": script["title"],
        "video_path": video_path,
        "publish_result": publish_result,
    }
