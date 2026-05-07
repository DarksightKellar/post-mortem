from pathlib import Path

from reddit_automation.utils.config import load_config


def test_load_config_reads_yaml_mapping_from_explicit_path():
    config_path = Path(__file__).resolve().parents[1] / "config/config.yaml"

    config = load_config(config_path)

    assert config["project"]["episode_target_minutes"] == 5
