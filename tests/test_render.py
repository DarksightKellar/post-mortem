from reddit_automation.pipeline.render import render_episode_video


def test_render_episode_video_delegates_to_render_backend_with_audio_visual_plan_and_output_path(monkeypatch):
    audio_path = "/tmp/voice/episode.wav"
    visual_plan = {
        "episode_date": "2026-04-03",
        "title": "Placeholder: Funniest threads today",
        "scenes": [
            {"type": "title_card", "text": "Placeholder: Funniest threads today"}
        ],
    }
    config = {
        "project": {
            "render_dir": "/tmp/rendered"
        }
    }

    def stub_generate_scene_images(visual_plan, config):
        return []

    backend_calls = []

    def stub_render_video(*, audio_path, visual_plan, output_path, config, scene_images=None):
        backend_calls.append({
            "audio_path": audio_path,
            "visual_plan": visual_plan,
            "output_path": output_path,
        })
        return output_path

    monkeypatch.setattr(
        "reddit_automation.pipeline.render.generate_scene_images",
        stub_generate_scene_images,
    )
    monkeypatch.setattr(
        "reddit_automation.pipeline.render.render_video",
        stub_render_video,
    )

    video_path = render_episode_video(audio_path, visual_plan, config)

    assert backend_calls == [
        {
            "audio_path": "/tmp/voice/episode.wav",
            "visual_plan": {
                "episode_date": "2026-04-03",
                "title": "Placeholder: Funniest threads today",
                "scenes": [
                    {"type": "title_card", "text": "Placeholder: Funniest threads today"}
                ],
            },
            "output_path": "/tmp/rendered/2026-04-03.mp4",
        }
    ]
    assert video_path == "/tmp/rendered/2026-04-03.mp4"
