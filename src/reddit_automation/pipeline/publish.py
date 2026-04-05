from reddit_automation.clients.youtube_client import YouTubeClient


def publish_episode(video_path: str, metadata: dict, config: dict) -> dict:
    """Upload the final video and return publish metadata."""
    client = YouTubeClient(config)
    return client.upload(video_path, metadata)
