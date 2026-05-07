"""Unit tests for config validation."""

import pytest

from reddit_automation.utils.config import build_runtime_config, validate_config, ConfigError


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


    def test_reddit_post_urls_can_replace_subreddits_for_manual_url_ingestion(self):
        config = _make_minimal()
        config["sources"] = {"reddit_post_urls": ["https://www.reddit.com/r/AskReddit/comments/abc123/funniest_thing/"]}

        validate_config(config)

    def test_configuring_both_post_urls_and_subreddits_requires_explicit_source_mode(self):
        config = _make_minimal()
        config["sources"] = {
            "reddit_post_urls": ["https://www.reddit.com/r/AskReddit/comments/abc123/funniest_thing/"],
            "subreddits": ["AskReddit"],
        }

        with pytest.raises(ConfigError, match="source_mode"):
            validate_config(config)

    def test_explicit_post_url_source_mode_allows_subreddits_to_stay_as_dormant_defaults(self):
        config = _make_minimal()
        config["sources"] = {
            "source_mode": "post_urls",
            "reddit_post_urls": ["https://www.reddit.com/r/AskReddit/comments/abc123/funniest_thing/"],
            "subreddits": ["AskReddit"],
        }

        validate_config(config)

    def test_bluesky_source_mode_can_replace_reddit_sources(self):
        config = _make_minimal()
        config["sources"] = {
            "source_mode": "bluesky",
            "bluesky_post_urls": ["https://bsky.app/profile/alice.example/post/3kabc"],
        }

        validate_config(config)

    def test_bluesky_source_mode_requires_bluesky_post_urls(self):
        config = _make_minimal()
        config["sources"] = {"source_mode": "bluesky"}

        with pytest.raises(ConfigError, match="bluesky_post_urls"):
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

    def test_host_missing_dialogue_profile_fields(self):
        config = _make_minimal()
        del config["hosts"]["host_2"]["role"]

        with pytest.raises(ConfigError, match="hosts.host_2.role"):
            validate_config(config)

    def test_missing_second_host_fails_for_two_host_pipeline(self):
        config = _make_minimal()
        del config["hosts"]["host_2"]

        with pytest.raises(ConfigError, match="host_2"):
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

    def test_runtime_config_includes_authenticated_reddit_fetch_defaults(self):
        config = build_runtime_config(_make_minimal())

        assert config["reddit"] == {
            "client_id": "",
            "client_secret": "",
            "user_agent": "Postmortem/0.1 by u/unknown",
            "max_retries": 3,
            "base_delay_seconds": 2.0,
            "min_seconds_between_requests": 2.0,
            "max_comment_threads_per_run": 10,
        }

    def test_runtime_config_defaults_to_post_url_mode_when_urls_are_configured(self):
        config = _make_minimal()
        config["scoring"]["weights"] = {
            "reaction_potential": 0.40,
            "laugh_factor": 0.25,
            "story_payoff": 0.15,
            "clarity_after_rewrite": 0.10,
            "comment_bonus": 0.10,
        }
        config["sources"] = {
            "reddit_post_urls": ["https://www.reddit.com/r/AskReddit/comments/abc123/funniest_thing/"],
        }

        runtime_config = build_runtime_config(config)
        validate_config(runtime_config)

        assert runtime_config["sources"]["source_mode"] == "post_urls"

    def test_runtime_config_prefers_post_url_mode_when_urls_and_subreddits_are_configured(self):
        config = _make_minimal()
        config["scoring"]["weights"] = {
            "reaction_potential": 0.40,
            "laugh_factor": 0.25,
            "story_payoff": 0.15,
            "clarity_after_rewrite": 0.10,
            "comment_bonus": 0.10,
        }
        config["sources"] = {
            "reddit_post_urls": ["https://www.reddit.com/r/AskReddit/comments/abc123/funniest_thing/"],
            "subreddits": ["AskReddit"],
        }

        runtime_config = build_runtime_config(config)
        validate_config(runtime_config)

        assert runtime_config["sources"]["source_mode"] == "post_urls"

    def test_runtime_config_defaults_to_edge_tts_with_optional_backend_config(self):
        config = build_runtime_config(_make_minimal())

        assert config["tts"] == {
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
        }


def _make_minimal():
    """Create a minimal valid config for testing."""
    return {
        "project": {"episode_target_minutes": 5},
        "sources": {"subreddits": ["AskReddit"]},
        "scoring": {"weights": {"reaction_potential": 0.5, "laugh_factor": 0.5}},
        "hosts": {
            "host_1": {
                "name": "Host 1",
                "role": "story_driver",
                "personality": "dry setup narrator",
                "voice_id": "voice-1",
            },
            "host_2": {
                "name": "Host 2",
                "role": "incredulous_reactor",
                "personality": "skeptical punchline partner",
                "voice_id": "voice-2",
            },
        },
        "render": {"resolution": "1920x1080"},
    }
