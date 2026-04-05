from reddit_automation.pipeline import publish as publish_module


def test_publish_episode_delegates_to_youtube_client_upload_and_returns_result(monkeypatch):
    config = {"youtube": {"channel_id": "channel-123"}}
    video_path = "/tmp/renders/episode.mp4"
    metadata = {"title": "Episode Title"}
    upload_result = {"video_id": "abc123", "url": "https://youtube.com/watch?v=abc123"}
    calls = []

    class FakeYouTubeClient:
        def __init__(self, received_config):
            assert received_config is config
            calls.append(("YouTubeClient", received_config))

        def upload(self, received_video_path, received_metadata):
            assert received_video_path == video_path
            assert received_metadata is metadata
            calls.append(("upload", received_video_path, received_metadata))
            return upload_result

    monkeypatch.setattr(publish_module, "YouTubeClient", FakeYouTubeClient)

    result = publish_module.publish_episode(video_path, metadata, config)

    assert result is upload_result
    assert calls == [
        ("YouTubeClient", config),
        ("upload", video_path, metadata),
    ]
