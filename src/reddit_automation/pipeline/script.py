def write_episode_script(outline: dict, config: dict) -> dict:
    """Generate final host dialogue from the episode outline."""
    host_1_key = config.get("hosts", {}).get("host_1", {}).get("key", "host_1")
    host_2_key = config.get("hosts", {}).get("host_2", {}).get("key", "host_2")

    episode_script = {
        "title": outline["title_angle"],
        "segments": [
            {
                "position": segment["position"],
                "reddit_post_id": segment["source"]["reddit_post_id"],
                "source_title": segment["source"]["title"],
                "subreddit": segment["source"]["subreddit"],
                "lines": [
                    {
                        "speaker": host_1_key,
                        "text": f"Setup: {segment['source']['title']}",
                    },
                    {
                        "speaker": host_2_key,
                        "text": f"Reaction: {segment['source']['title']}",
                    },
                ],
            }
            for segment in outline.get("segments", [])
        ],
    }

    if "cold_open" in outline:
        hook = outline["cold_open"]["hook"]
        episode_script["cold_open"] = {
            "lines": [
                {
                    "speaker": host_1_key,
                    "text": f"Cold open: {hook}",
                },
                {
                    "speaker": host_2_key,
                    "text": f"Cold open reaction: {hook}",
                },
            ]
        }

    if "outro" in outline:
        episode_script["outro"] = {
            "lines": [
                {
                    "speaker": host_1_key,
                    "text": f"Callback: {outline['outro']['callback']}",
                },
                {
                    "speaker": host_2_key,
                    "text": f"Tease: {outline['outro']['tomorrow_tease']}",
                },
            ]
        }

    return episode_script
