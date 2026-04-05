"""Unit tests for per-scene image generation orchestrator."""

from reddit_automation.pipeline.generate_scenes import (
    build_prompt_for_scene,
    generate_scene_images,
)


def test_build_prompt_for_title_card():
    scene = {"type": "title_card", "text": "Best threads of the week"}
    prompt = build_prompt_for_scene(scene)
    assert "title card" in prompt
    assert "Best threads of the week" in prompt


def test_build_prompt_for_segment_scene():
    scene = {
        "type": "segment",
        "position": 1,
        "text": "Show a confused office worker at their desk",
    }
    prompt = build_prompt_for_scene(scene)
    assert "confused office worker" in prompt


def test_build_prompt_enhances_visual_note_with_style():
    scene = {"type": "cold_open", "text": "Two hosts at microphones"}
    prompt = build_prompt_for_scene(scene, style="cinematic")
    assert "Two hosts at microphones" in prompt
    assert "cinematic" in prompt


def test_generate_scene_images_calls_fal_client_for_each_scene(tmp_path, monkeypatch):
    visual_plan = {
        "episode_date": "2026-04-03",
        "title": "Test episode",
        "scenes": [
            {"type": "title_card", "text": "Title here", "visual_note": "Big bold title"},
            {"type": "segment", "position": 1, "text": "Office scene", "visual_note": "Office visual"},
        ],
    }
    config = {
        "project": {"assets_dir": str(tmp_path / "assets")},
        "render": {"aspect_ratio": "16:9", "resolution": "1920x1080"},
        "fal": {"model": "fal-ai/flux/schnell"},
    }

    generated_paths = [
        str(tmp_path / "assets" / "2026-04-03" / "000_title_card.png"),
        str(tmp_path / "assets" / "2026-04-03" / "001_segment.png"),
    ]

    call_log = []

    class FakeFalClient:
        def __init__(self, api_key=None, config=None):
            pass

        def generate(self, prompt, output_path):
            call_log.append({"prompt": prompt, "output_path": output_path})
            return output_path

    monkeypatch.setattr(
        "reddit_automation.pipeline.generate_scenes.FalClient", FakeFalClient
    )
    monkeypatch.setenv("FAL_KEY", "test-key")

    result = generate_scene_images(visual_plan, config)

    assert result == generated_paths
    assert len(call_log) == 2
    assert call_log[0]["output_path"].endswith("000_title_card.png")
    assert call_log[1]["output_path"].endswith("001_segment.png")


def test_generate_scene_images_skips_scenes_without_text(tmp_path, monkeypatch):
    visual_plan = {
        "episode_date": "2026-04-03",
        "title": "Test episode",
        "scenes": [
            {"type": "title_card", "text": "Title"},
            {"type": "segment", "position": 1, "text": ""},
            {"type": "outro", "text": "Outro visual"},
        ],
    }
    config = {
        "project": {"assets_dir": str(tmp_path / "assets")},
        "render": {"aspect_ratio": "16:9", "resolution": "1920x1080"},
        "fal": {"model": "fal-ai/flux/schnell"},
    }

    call_log = []

    class FakeFalClient:
        def __init__(self, api_key=None, config=None):
            pass

        def generate(self, prompt, output_path):
            call_log.append({"prompt": prompt, "output_path": output_path})
            return output_path

    monkeypatch.setattr(
        "reddit_automation.pipeline.generate_scenes.FalClient", FakeFalClient
    )
    monkeypatch.setenv("FAL_KEY", "test-key")

    result = generate_scene_images(visual_plan, config)

    # Should only generate for non-empty text scenes
    assert len(call_log) == 2
    assert len(result) == 2
    assert "000_title_card" in result[0]
    assert "002_outro" in result[1]


def test_generate_scene_images_creates_assets_directory(tmp_path, monkeypatch):
    visual_plan = {
        "episode_date": "2026-04-03",
        "title": "Test",
        "scenes": [{"type": "title_card", "text": "Hi"}],
    }
    assets_dir = tmp_path / "my_assets"
    config = {
        "project": {"assets_dir": str(assets_dir)},
        "render": {"aspect_ratio": "16:9", "resolution": "1920x1080"},
        "fal": {"model": "fal-ai/flux/schnell"},
    }

    class FakeFalClient:
        def __init__(self, api_key=None, config=None):
            pass

        def generate(self, prompt, output_path):
            return output_path

    monkeypatch.setattr(
        "reddit_automation.pipeline.generate_scenes.FalClient", FakeFalClient
    )
    monkeypatch.setenv("FAL_KEY", "test-key")

    assert not assets_dir.exists()
    generate_scene_images(visual_plan, config)
    assert assets_dir.exists()
