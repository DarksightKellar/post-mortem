from reddit_automation.utils.hyperframes import render_video


def render_episode_video(audio_path: str, visual_plan: dict, config: dict) -> str:
    """Render final video asset with the HyperFrames backend."""
    output_path = f"{config['project']['render_dir']}/{visual_plan['episode_date']}.mp4"

    render_video(
        audio_path=audio_path,
        visual_plan=visual_plan,
        output_path=output_path,
        config=config,
    )
    return output_path
