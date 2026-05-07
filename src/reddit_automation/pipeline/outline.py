def _story_text(item: dict) -> str:
    for key in ("summary", "body", "title"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Untitled public thread"


def _source_label(item: dict) -> str:
    community = item.get("source_community")
    source = item.get("source") or ("reddit" if community else "source")
    community = community or source
    if source == "reddit":
        return f"r/{community}"
    if source == "bluesky":
        return f"Bluesky @{community}"
    return f"{source}:{community}"


def _segment_visual_note(item: dict) -> str:
    return f"Scene from {_source_label(item)}: {_story_text(item)}"


def _title_angle(primary_items: list[dict]) -> str:
    first_title = primary_items[0]["title"]
    if len(primary_items) == 1:
        return first_title
    return f"{first_title} + {len(primary_items) - 1} more public-thread blowups"


def _cold_open(item: dict) -> dict:
    story_text = _story_text(item)
    return {
        "hook": story_text,
        "visual_note": _segment_visual_note(item),
    }


def _outro(primary_items: list[dict], backup_items: list[dict]) -> dict:
    first_item = primary_items[0]
    callback = f"That started with {first_item['title']} and somehow got worse once the replies piled on."
    if backup_items:
        tomorrow_tease = f"Next up: {backup_items[0]['title']}"
    else:
        tomorrow_tease = "Next up: more public internet fallout worth dissecting."
    return {
        "callback": callback,
        "tomorrow_tease": tomorrow_tease,
        "visual_note": f"Aftermath in {_source_label(first_item)}: {_story_text(first_item)}",
    }


def _target_segment_count(config: dict) -> int:
    scripting = config.get("scripting", {})
    target_segments = int(scripting.get("target_segments", 1))
    project = config.get("project") or {}
    target_minutes = project.get("episode_target_minutes")
    if target_minutes is None:
        return target_segments

    minutes_per_segment = float(scripting.get("minutes_per_segment", 1.5))
    if minutes_per_segment <= 0:
        return target_segments
    duration_budget = max(1, int(float(target_minutes) // minutes_per_segment))
    return max(1, min(target_segments, duration_budget))


def _source_id(item: dict, source: str) -> str | None:
    if item.get("source_id"):
        return item["source_id"]
    candidate_id = item.get("candidate_id")
    if not candidate_id:
        return None
    candidate_id = str(candidate_id)
    prefix = f"{source}:"
    if candidate_id.startswith(prefix):
        return candidate_id[len(prefix) :]
    return candidate_id


def _selection_item(item: dict, position: int) -> dict:
    community = item.get("source_community")
    source = item.get("source") or ("reddit" if community or item.get("candidate_id") else None)
    return {
        "position": position,
        "candidate_id": item["candidate_id"],
        "source": source,
        "source_id": _source_id(item, source or "source"),
        "source_community": community,
        "title": item["title"],
        "author": item.get("author"),
        "url": item.get("url"),
    }


def build_episode_outline(selected_items: dict, config: dict) -> dict:
    """Generate structured episode plan JSON."""
    target_segments = _target_segment_count(config)
    primary_items = selected_items["primary"][:target_segments]

    outline = {
        "segments": [
            {
                "position": index + 1,
                "source": item,
                "visual_notes": [_segment_visual_note(item)],
            }
            for index, item in enumerate(primary_items)
        ],
        "selection": {
            "primary_items": [_selection_item(item, index + 1) for index, item in enumerate(primary_items)]
        },
    }

    project = config.get("project")
    if project and project.get("episode_date"):
        outline["episode_date"] = project["episode_date"]
        outline["title_angle"] = _title_angle(primary_items)
        outline["cold_open"] = _cold_open(primary_items[0])
        outline["outro"] = _outro(primary_items, selected_items.get("backups", []))

    return outline
