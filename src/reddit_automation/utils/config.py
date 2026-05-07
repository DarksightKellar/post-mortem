from __future__ import annotations

import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from reddit_automation.utils.paths import CONFIG_DIR, DATA_DIR, OUTPUT_DIR


DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"


class ConfigError(RuntimeError):
    pass


def load_yaml_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigError(f"Config file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Expected mapping in YAML file: {file_path}")
    return data


def write_yaml_file(path: str | Path, data: dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    temp_path.replace(file_path)


REQUIRED_SECTIONS = ["project", "sources", "scoring", "hosts", "render"]


def _runtime_defaults() -> dict[str, Any]:
    return {
        "project": {
            "final_pick_count": 3,
            "backup_pick_count": 2,
            "episode_date": date.today().isoformat(),
            "render_dir": str(OUTPUT_DIR / "rendered"),
            "assets_dir": str(OUTPUT_DIR / "assets"),
        },
        "sources": {
            "source_mode": "subreddits",
            "max_posts_per_subreddit_per_mode": 15,
            "bluesky_reply_depth": 6,
        },
        "filters": {
            "exclude_categories": ["politics", "culture_war", "tragedy", "abuse", "death", "nsfw"],
            "exclude_low_context": True,
            "dedupe_similar_posts": True,
        },
        "comments": {
            "top_n_per_candidate": 5,
        },
        "scoring": {
            "weights": {
                "reaction_potential": 0.40,
                "laugh_factor": 0.25,
                "story_payoff": 0.15,
                "clarity_after_rewrite": 0.10,
                "comment_bonus": 0.10,
            },
            "thresholds": {
                "min_reaction_potential": 8,
                "min_laugh_factor": 7,
                "min_overall_score": 7.2,
            },
        },
        "hosts": {
            "host_1": {
                "key": "host_1",
                "name": "Host 1",
                "role": "story_driver",
                "personality": "dry setup narrator",
                "voice_id": "en-US-GuyNeural",
            },
            "host_2": {
                "key": "host_2",
                "name": "Host 2",
                "role": "incredulous_reactor",
                "personality": "sharp skeptical punchline partner",
                "voice_id": "en-US-AnaNeural",
            },
        },
        "scripting": {
            "target_segments": 3,
        },
        "render": {
            "engine": "hyperframes",
            "slide_style": "postmortem_forensic",
            "resolution": "1920x1080",
            "fps": 30,
            "hyperframes": {
                "quality": "standard",
                "run_validate": True,
                "run_inspect": True,
            },
        },
        "publishing": {
            "youtube_auto_publish": False,
            "default_privacy_status": "private",
            "upload_tags": ["reddit", "reddit stories"],
        },
        "alerts": {
            "telegram_on_success": False,
            "telegram_on_failure": False,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
        },
        "retry": {
            "max_retries": 3,
            "base_delay": 2.0,
        },
        "reddit": {
            "client_id": "",
            "client_secret": "",
            "user_agent": "Postmortem/0.1 by u/unknown",
            "max_retries": 3,
            "base_delay_seconds": 2.0,
            "min_seconds_between_requests": 2.0,
            "max_comment_threads_per_run": 10,
        },
        "youtube": {
            "credentials_file": str(DATA_DIR / "youtube_credentials.json"),
            "token_file": str(DATA_DIR / "youtube_credentials.token"),
            "category_id": "22",
            "api_key": "",
        },
        "fal": {
            "model": "fal-ai/flux/schnell",
        },
        "tts": {
            "provider": "edge_tts",
            "comfy_qwen_tts": {
                "base_url": "http://127.0.0.1:8188",
                "model_size": "0.6B",
                "language": "English",
                "device": "auto",
                "precision": "bf16",
                "attention": "auto",
                "max_new_tokens": 768,
                "do_sample": False,
                "timeout_seconds": 900,
                "poll_interval_seconds": 1.0,
                "max_poll_attempts": 900,
                "unload_models": False,
            },
            "elevenlabs": {
                "api_key_env": "ELEVENLABS_API_KEY",
                "model_id": "eleven_multilingual_v2",
                "output_format": "mp3_44100_128",
                "timeout_seconds": 60,
            },
        },
        "output_dir": str(OUTPUT_DIR),
        "reddit_test_data": {
            "submissions": [],
        },
        "cron": "24h",
    }


EDITABLE_TOP_LEVEL_KEYS = set(_runtime_defaults().keys()) | {
    "project",
    "sources",
    "filters",
    "comments",
    "scoring",
    "hosts",
    "scripting",
    "render",
    "publishing",
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def build_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(_runtime_defaults(), config)
    configured_sources = config.get("sources")
    if (
        isinstance(configured_sources, dict)
        and "source_mode" not in configured_sources
        and configured_sources.get("reddit_post_urls")
    ):
        merged["sources"]["source_mode"] = "post_urls"
    return merged


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config = build_runtime_config(load_yaml_file(path or DEFAULT_CONFIG_PATH))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate the configuration dictionary and apply defaults for optional sections.

    Raises ConfigError with a clear message for any missing or invalid values.
    Mutates config in-place to apply defaults for optional sections.
    """
    for section in REQUIRED_SECTIONS:
        if section not in config:
            raise ConfigError(f"Missing required config section: '{section}'")

    _validate_project(config["project"])
    _validate_sources(config["sources"])
    _validate_scoring(config["scoring"])
    _validate_hosts(config["hosts"])
    _validate_render(config["render"])

    config.setdefault("retry", {"max_retries": 3, "base_delay": 2.0})
    config.setdefault(
        "alerts",
        {
            "telegram_on_success": False,
            "telegram_on_failure": False,
        },
    )
    config.setdefault(
        "publishing",
        {
            "youtube_auto_publish": False,
            "generate_thumbnail_prompt": True,
            "default_privacy_status": "private",
            "upload_tags": ["reddit", "reddit stories"],
        },
    )


def _validate_project(project: Any) -> None:
    if not isinstance(project, dict):
        raise ConfigError("'project' must be a mapping")
    if "episode_target_minutes" not in project:
        raise ConfigError("Missing required field: project.episode_target_minutes")
    val = project["episode_target_minutes"]
    if not isinstance(val, (int, float)):
        raise ConfigError(f"project.episode_target_minutes must be numeric, got {type(val).__name__}")
    if val <= 0:
        raise ConfigError("project.episode_target_minutes must be positive")


def _validate_sources(sources: Any) -> None:
    if not isinstance(sources, dict):
        raise ConfigError("'sources' must be a mapping")
    subs = sources.get("subreddits")
    post_urls = sources.get("reddit_post_urls")
    bluesky_post_urls = sources.get("bluesky_post_urls")
    source_mode = sources.get("source_mode")
    allowed_modes = {"post_urls", "subreddits", "bluesky"}
    if subs is None and post_urls is None and bluesky_post_urls is None:
        if source_mode == "bluesky":
            raise ConfigError("sources.source_mode=bluesky requires sources.bluesky_post_urls")
        raise ConfigError("Missing required field: sources.subreddits, sources.reddit_post_urls, or sources.bluesky_post_urls")
    if source_mode is not None and source_mode not in allowed_modes:
        raise ConfigError("sources.source_mode must be 'post_urls', 'subreddits', or 'bluesky'")
    configured_source_count = sum(value is not None for value in (subs, post_urls, bluesky_post_urls))
    if configured_source_count > 1 and source_mode is None:
        raise ConfigError("sources.source_mode is required when multiple source lists are configured")
    if source_mode == "post_urls" and post_urls is None:
        raise ConfigError("sources.source_mode=post_urls requires sources.reddit_post_urls")
    if source_mode == "subreddits" and subs is None:
        raise ConfigError("sources.source_mode=subreddits requires sources.subreddits")
    if source_mode == "bluesky" and bluesky_post_urls is None:
        raise ConfigError("sources.source_mode=bluesky requires sources.bluesky_post_urls")
    if subs is not None:
        if not isinstance(subs, list):
            raise ConfigError("sources.subreddits must be a list")
        if len(subs) == 0:
            raise ConfigError("sources.subreddits must not be empty")
    if post_urls is not None:
        if not isinstance(post_urls, list):
            raise ConfigError("sources.reddit_post_urls must be a list")
        if len(post_urls) == 0:
            raise ConfigError("sources.reddit_post_urls must not be empty")
        if not all(isinstance(url, str) and url.strip() for url in post_urls):
            raise ConfigError("sources.reddit_post_urls must contain non-empty strings")
    if bluesky_post_urls is not None:
        if not isinstance(bluesky_post_urls, list):
            raise ConfigError("sources.bluesky_post_urls must be a list")
        if len(bluesky_post_urls) == 0:
            raise ConfigError("sources.bluesky_post_urls must not be empty")
        if not all(isinstance(url, str) and url.strip() for url in bluesky_post_urls):
            raise ConfigError("sources.bluesky_post_urls must contain non-empty strings")


def _validate_scoring(scoring: Any) -> None:
    if not isinstance(scoring, dict):
        raise ConfigError("'scoring' must be a mapping")
    weights = scoring.get("weights")
    if weights is None:
        raise ConfigError("Missing required field: scoring.weights")
    if not isinstance(weights, dict):
        raise ConfigError("scoring.weights must be a mapping")
    for key, val in weights.items():
        if not isinstance(val, (int, float)):
            raise ConfigError(f"scoring.weights.{key} must be numeric")
        if val < 0:
            raise ConfigError(f"scoring.weights.{key} must not be negative")
    total = sum(float(v) for v in weights.values())
    if abs(total - 1.0) > 0.01:
        raise ConfigError(f"scoring.weights must sum to ~1.0, got {total:.4f}")


def _validate_hosts(hosts: Any) -> None:
    if not isinstance(hosts, dict):
        raise ConfigError("'hosts' must be a mapping")
    if "host_1" not in hosts:
        raise ConfigError("Missing required host: hosts.host_1")
    if "host_2" not in hosts:
        raise ConfigError("Missing required host: hosts.host_2")
    for host_key in ("host_1", "host_2"):
        host = hosts[host_key]
        if not isinstance(host, dict):
            raise ConfigError(f"hosts.{host_key} must be a mapping")
        for field in ("name", "role", "personality", "voice_id"):
            if field not in host:
                raise ConfigError(f"Missing required field: hosts.{host_key}.{field}")
            if not isinstance(host[field], str) or not host[field].strip():
                raise ConfigError(f"hosts.{host_key}.{field} must be a non-empty string")
        if "key" in host and (not isinstance(host["key"], str) or not host["key"].strip()):
            raise ConfigError(f"hosts.{host_key}.key must be a non-empty string")


def _validate_render(render: Any) -> None:
    if not isinstance(render, dict):
        raise ConfigError("'render' must be a mapping")
    resolution = render.get("resolution")
    if resolution is not None:
        if not isinstance(resolution, str) or not re.match(r"^\d+x\d+$", resolution):
            raise ConfigError(
                f"render.resolution must be in WxH format (e.g. '1920x1080'), got '{resolution}'"
            )
