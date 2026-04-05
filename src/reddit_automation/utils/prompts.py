from __future__ import annotations

from pathlib import Path

from reddit_automation.utils.paths import PROJECT_ROOT


class PromptError(RuntimeError):
    pass


def load_prompt(relative_path: str) -> str:
    prompt_path = PROJECT_ROOT / relative_path
    if not prompt_path.exists():
        raise PromptError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def load_prompt_bundle(config: dict) -> dict[str, str]:
    prompt_config = config.get("prompts", {})
    return {
        key: load_prompt(value)
        for key, value in prompt_config.items()
        if key.endswith("_file") and isinstance(value, str)
    }
