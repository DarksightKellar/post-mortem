def select_episode_items(scored_candidates: list[dict], config: dict) -> dict:
    """Choose primary picks and backups while preserving variety."""
    primary_count = config["project"]["final_pick_count"]
    backup_count = config["project"]["backup_pick_count"]
    kept_candidates = [candidate for candidate in scored_candidates if candidate["keep"]]

    return {
        "primary": kept_candidates[:primary_count],
        "backups": kept_candidates[primary_count:primary_count + backup_count],
    }
