def build_visual_plan(outline: dict, config: dict) -> dict:
    """Create slide/comment-card visual plan for rendering."""
    title = outline["title_angle"]
    scenes = [{"type": "title_card", "text": title}]

    cold_open = outline.get("cold_open", {})
    cold_open_visual_note = cold_open.get("visual_note")
    if cold_open_visual_note:
        scenes.append({"type": "cold_open", "text": cold_open_visual_note})

    segments = outline.get("segments", [])
    for segment in segments:
        visual_notes = segment.get("visual_notes", [])
        if visual_notes:
            scenes.append(
                {
                    "type": "segment",
                    "position": segment["position"],
                    "text": visual_notes[0],
                }
            )

    outro = outline.get("outro", {})
    outro_visual_note = outro.get("visual_note")
    if outro_visual_note:
        scenes.append({"type": "outro", "text": outro_visual_note})

    return {
        "episode_date": outline["episode_date"],
        "title": title,
        "scenes": scenes,
    }
