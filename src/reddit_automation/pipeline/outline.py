def build_episode_outline(selected_items: dict, config: dict) -> dict:
    """Generate structured episode plan JSON."""
    target_segments = config["scripting"]["target_segments"]
    primary_items = selected_items["primary"][:target_segments]
    first_primary = primary_items[0]

    outline = {
        "segments": [
            {
                "position": index + 1,
                "source": item,
                "visual_notes": [f"Placeholder visual note for {item['reddit_post_id']}"]
            }
            for index, item in enumerate(primary_items)
        ],
        "selection": {
            "primary_items": [
                {
                    "position": index + 1,
                    "reddit_post_id": item["reddit_post_id"],
                    "title": item["title"],
                    "author": item.get("author"),
                    "url": item.get("url"),
                }
                for index, item in enumerate(primary_items)
            ]
        },
    }

    project = config.get("project")
    if project and project.get("episode_date"):
        outline["episode_date"] = project["episode_date"]
        outline["title_angle"] = f"Placeholder: {first_primary['title']}"
        outline["cold_open"] = {
            "hook": f"Placeholder hook for {first_primary['reddit_post_id']}",
            "visual_note": f"Placeholder visual note for {first_primary['reddit_post_id']}",
        }
        outline["outro"] = {
            "callback": f"Placeholder callback for {first_primary['reddit_post_id']}",
            "tomorrow_tease": "Placeholder tease for next episode",
            "visual_note": f"Placeholder outro visual note for {first_primary['reddit_post_id']}",
        }

    return outline
