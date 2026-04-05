"""Unit tests for config validation."""

import pytest

from reddit_automation.utils.config import validate_config, ConfigError


class TestValidateConfigProjectSection:
    """Tests for the project section validation."""

    def test_valid_config_passes(self):
        config = _make_minimal()
        result = validate_config(config)
        assert result is None  # validation returns nothing on success

    def test_missing_project_section(self):
        config = {"sources": {"subreddits": ["AskReddit"]}}
        with pytest.raises(ConfigError, match="project"):
            validate_config(config)

    def test_missing_episode_target_minutes(self):
        config = _make_minimal()
        del config["project"]["episode_target_minutes"]
        with pytest.raises(ConfigError, match="episode_target_minutes"):
            validate_config(config)

    def test_non_numeric_episode_target_minutes(self):
        config = _make_minimal()
        config["project"]["episode_target_minutes"] = "five"
        with pytest.raises(ConfigError, match="episode_target_minutes"):
            validate_config(config)

    def test_negative_episode_target_minutes(self):
        config = _make_minimal()
        config["project"]["episode_target_minutes"] = -1
        with pytest.raises(ConfigError, match="episode_target_minutes"):
            validate_config(config)


class TestValidateConfigSourcesSection:
    """Tests for the sources section validation."""

    def test_missing_sources_section(self):
        config = _make_minimal()
        del config["sources"]
        with pytest.raises(ConfigError, match="sources"):
            validate_config(config)

    def test_missing_subreddits(self):
        config = _make_minimal()
        config["sources"] = {}
        with pytest.raises(ConfigError, match="subreddits"):
            validate_config(config)

    def test_empty_subreddits_list(self):
        config = _make_minimal()
        config["sources"]["subreddits"] = []
        with pytest.raises(ConfigError, match="subreddits"):
            validate_config(config)

    def test_subreddits_not_a_list(self):
        config = _make_minimal()
        config["sources"]["subreddits"] = "AskReddit"
        with pytest.raises(ConfigError, match="subreddits"):
            validate_config(config)


class TestValidateConfigScoringSection:
    """Tests for the scoring section validation."""

    def test_missing_scoring_section(self):
        config = _make_minimal()
        del config["scoring"]
        with pytest.raises(ConfigError, match="scoring"):
            validate_config(config)

    def test_missing_weights(self):
        config = _make_minimal()
        config["scoring"] = {}
        with pytest.raises(ConfigError, match="weights"):
            validate_config(config)

    def test_weights_dont_sum_to_one(self):
        config = _make_minimal()
        config["scoring"]["weights"] = {"reaction_potential": 0.9}
        with pytest.raises(ConfigError, match="weights.*sum"):
            validate_config(config)

    def test_weights_with_negative_values(self):
        config = _make_minimal()
        config["scoring"]["weights"] = {"reaction_potential": -0.5, "laugh_factor": 1.5}
        with pytest.raises(ConfigError, match="weights.*negative"):
            validate_config(config)

    def test_weights_sum_exactly_one_passes(self):
        config = _make_minimal()
        config["scoring"]["weights"] = {"reaction_potential": 0.5, "laugh_factor": 0.5}
        validate_config(config)

    def test_weights_sum_within_tolerance(self):
        config = _make_minimal()
        # Floating point tolerance: 1.0001 should pass
        config["scoring"]["weights"] = {"a": 0.3333, "b": 0.3333, "c": 0.3334}
        validate_config(config)


class TestValidateConfigHostsSection:
    """Tests for the hosts section validation."""

    def test_missing_hosts_section(self):
        config = _make_minimal()
        del config["hosts"]
        with pytest.raises(ConfigError, match="hosts"):
            validate_config(config)

    def test_missing_required_host(self):
        config = _make_minimal()
        config["hosts"] = {}
        with pytest.raises(ConfigError, match="host_1"):
            validate_config(config)

    def test_host_missing_voice_id(self):
        config = _make_minimal()
        del config["hosts"]["host_1"]["voice_id"]
        with pytest.raises(ConfigError, match="voice_id"):
            validate_config(config)


class TestValidateConfigRenderSection:
    """Tests for the render section validation."""

    def test_missing_render_section(self):
        config = _make_minimal()
        del config["render"]
        with pytest.raises(ConfigError, match="render"):
            validate_config(config)

    def test_invalid_resolution_format(self):
        config = _make_minimal()
        config["render"]["resolution"] = "bad-format"
        with pytest.raises(ConfigError, match="resolution"):
            validate_config(config)

    def test_valid_resolution_passes(self):
        config = _make_minimal()
        config["render"]["resolution"] = "2560x1440"
        validate_config(config)


class TestValidateConfigApplyDefaults:
    """Tests that validate_config applies defaults for optional sections."""

    def test_missing_retry_gets_defaults(self):
        config = _make_minimal()
        validate_config(config)
        assert "retry" in config
        assert config["retry"]["max_retries"] == 3

    def test_missing_alerts_gets_defaults(self):
        config = _make_minimal()
        validate_config(config)
        assert "alerts" in config
        assert config["alerts"]["telegram_on_failure"] is False

    def test_existing_retry_not_overwritten(self):
        config = _make_minimal()
        config["retry"] = {"max_retries": 5}
        validate_config(config)
        assert config["retry"]["max_retries"] == 5


def _make_minimal():
    """Create a minimal valid config for testing."""
    return {
        "project": {"episode_target_minutes": 5},
        "sources": {"subreddits": ["AskReddit"]},
        "scoring": {"weights": {"reaction_potential": 0.5, "laugh_factor": 0.5}},
        "hosts": {
            "host_1": {"name": "Host 1", "voice_id": "voice-1"},
            "host_2": {"name": "Host 2", "voice_id": "voice-2"},
        },
        "render": {"resolution": "1920x1080"},
    }
