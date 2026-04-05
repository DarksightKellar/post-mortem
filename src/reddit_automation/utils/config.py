from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from reddit_automation.utils.paths import CONFIG_DIR


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


def load_config(path: str | None = None) -> dict[str, Any]:
    config = load_yaml_file(path or DEFAULT_CONFIG_PATH)
    validate_config(config)
    return config


REQUIRED_SECTIONS = ["project", "sources", "scoring", "hosts", "render"]


def validate_config(config: dict[str, Any]) -> None:
    """Validate the configuration dictionary and apply defaults.
    
    Raises ConfigError with a clear message for any missing or invalid values.
    Mutates config in-place to apply defaults for optional sections.
    """
    # Check required top-level sections
    for section in REQUIRED_SECTIONS:
        if section not in config:
            raise ConfigError(f"Missing required config section: '{section}'")

    _validate_project(config["project"])
    _validate_sources(config["sources"])
    _validate_scoring(config["scoring"])
    _validate_hosts(config["hosts"])
    _validate_render(config["render"])

    # Apply defaults for optional sections
    config.setdefault("retry", {"max_retries": 3, "base_delay": 2.0})
    config.setdefault("alerts", {
        "telegram_on_success": False,
        "telegram_on_failure": False,
    })
    config.setdefault("publishing", {
        "youtube_auto_publish": False,
        "generate_thumbnail_prompt": True,
        "default_privacy_status": "private",
        "upload_tags": ["reddit", "reddit stories"],
    })


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
    if subs is None:
        raise ConfigError("Missing required field: sources.subreddits")
    if not isinstance(subs, list):
        raise ConfigError("sources.subreddits must be a list")
    if len(subs) == 0:
        raise ConfigError("sources.subreddits must not be empty")


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
        raise ConfigError(
            f"scoring.weights must sum to ~1.0, got {total:.4f}"
        )


def _validate_hosts(hosts: Any) -> None:
    if not isinstance(hosts, dict):
        raise ConfigError("'hosts' must be a mapping")
    if "host_1" not in hosts:
        raise ConfigError("Missing required host: hosts.host_1")
    for host_key in ("host_1", "host_2"):
        if host_key not in hosts:
            continue  # host_2 is optional
        host = hosts[host_key]
        if not isinstance(host, dict):
            raise ConfigError(f"hosts.{host_key} must be a mapping")
        if "voice_id" not in host:
            raise ConfigError(f"Missing required field: hosts.{host_key}.voice_id")


def _validate_render(render: Any) -> None:
    if not isinstance(render, dict):
        raise ConfigError("'render' must be a mapping")
    resolution = render.get("resolution")
    if resolution is not None:
        if not isinstance(resolution, str) or not re.match(r"^\d+x\d+$", resolution):
            raise ConfigError(
                f"render.resolution must be in WxH format (e.g. '1920x1080'), got '{resolution}'"
            )
