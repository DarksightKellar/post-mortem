from reddit_automation.pipeline.generate_scenes import generate_scene_images
from reddit_automation.utils.ffmpeg import render_video


def render_episode_video(audio_path: str, visual_plan: dict, config: dict) -> str:
    """Render final video asset."""
    output_path = f"{config['project']['render_dir']}/{visual_plan['episode_date']}.mp4"

    # Generate scene images from the visual plan
    scene_images = generate_scene_images(visual_plan, config)

    # Render video with scene images
    render_video(
        audio_path=audio_path,
        visual_plan=visual_plan,
        output_path=output_path,
        config=config,
        scene_images=scene_images if scene_images else None,
    )
    return output_path
