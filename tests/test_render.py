import reddit_automation.pipeline.render as render_module
from reddit_automation.pipeline.render import render_episode_video


def test_render_episode_video_uses_hyperframes_render_backend():
    assert render_module.render_video.__module__ == "reddit_automation.utils.hyperframes"


def test_render_episode_video_does_not_import_fal_scene_generation():
    assert not hasattr(render_module, "generate_scene_images")


def test_render_episode_video_delegates_to_hyperframes_with_audio_visual_plan_and_output_path(monkeypatch):
    audio_path = "/tmp/voice/episode.wav"
    visual_plan = {
        "episode_date": "2026-04-03",
        "title": "Funniest threads today",
        "scenes": [{"type": "title_card", "text": "Funniest threads today"}],
    }
    config = {"project": {"render_dir": "/tmp/rendered"}}
    backend_calls = []

    def stub_render_video(*, audio_path, visual_plan, output_path, config):
        backend_calls.append(
            {
                "audio_path": audio_path,
                "visual_plan": visual_plan,
                "output_path": output_path,
                "config": config,
            }
        )
        return output_path

    monkeypatch.setattr("reddit_automation.pipeline.render.render_video", stub_render_video)

    video_path = render_episode_video(audio_path, visual_plan, config)

    assert backend_calls == [
        {
            "audio_path": "/tmp/voice/episode.wav",
            "visual_plan": visual_plan,
            "output_path": "/tmp/rendered/2026-04-03.mp4",
            "config": config,
        }
    ]
    assert video_path == "/tmp/rendered/2026-04-03.mp4"
