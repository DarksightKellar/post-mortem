"""Orchestrate per-scene image generation for episode visuals."""

import os
import pathlib

from reddit_automation.utils.fal_client import FalClient


def build_prompt_for_scene(scene: dict, style: str = "minimal") -> str:
    """Build a fal.ai prompt from a scene's visual note text.
    
    Enhances the raw visual note with aspect ratio and style hints
    to generate consistent, video-ready images.
    """
    text = scene.get("text", "")
    scene_type = scene.get("type", "segment")
    
    base = text.strip()
    if not base:
        return None
    
    # Build a rich prompt that works well with FLUX
    prompt_parts = [base]
    
    if scene_type == "title_card":
        prompt_parts.insert(0, "A title card / cover image:")
    elif scene_type == "cold_open":
        prompt_parts.insert(0, "A scene showing:")
    elif scene_type == "segment":
        prompt_parts.insert(0, "An illustration depicting:")
    elif scene_type == "outro":
        prompt_parts.insert(0, "An outro / closing card showing:")
    
    if style and style != "minimal":
        prompt_parts.append(f"Style: {style}")
    
    prompt_parts.append("High quality, clean composition, 16:9 aspect ratio")
    
    return " ".join(prompt_parts)


def generate_scene_images(visual_plan: dict, config: dict) -> list:
    """Generate images for each scene in the visual plan.
    
    Creates the assets directory, builds prompts from scene text,
    and generates images via fal.ai.
    
    Returns a list of generated image paths in scene order.
    """
    assets_dir = pathlib.Path(config["project"]["assets_dir"])
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    resolution = config.get("render", {}).get("resolution", "1920x1080")
    style = config.get("render", {}).get("slide_style", "minimal")
    
    # Use the date as a subdirectory for this episode's assets
    episode_date = visual_plan.get("episode_date", "unknown")
    episode_assets = assets_dir / episode_date
    episode_assets.mkdir(parents=True, exist_ok=True)
    
    client = FalClient(config=config)
    scenes = visual_plan.get("scenes", [])
    generated = []
    
    for i, scene in enumerate(scenes):
        text = scene.get("text", "")
        if not text or not text.strip():
            continue
        
        prompt = build_prompt_for_scene(scene, style)
        if not prompt:
            continue
        
        scene_type = scene.get("type", "segment")
        position = scene.get("position", i)
        filename = f"{i:03d}_{scene_type}.png"
        output_path = str(episode_assets / filename)
        
        client.generate(prompt, output_path)
        generated.append(output_path)
    
    return generated
