from __future__ import annotations

import html
import shutil
import subprocess
from pathlib import Path
from typing import Any

POSTMORTEM_DESIGN_MD = """# Postmortem Video Design

## Style Prompt
Dark forensic comedy newsroom: evidence-board structure, tabloid tension, sharp Reddit-story pacing, and clean high-contrast motion graphics.

## Colors
- Canvas: #0B0F14
- Panel: #151B23
- Bone text: #F5E6C8
- Alert coral: #FF4D2E
- Cool slate: #8F9BB3
- Evidence gold: #F2C14E

## Typography
- Headlines: Space Grotesk, 800 weight
- Body: Newsreader, 500 weight
- Labels: Space Grotesk, 700 uppercase

## Motion
Fast evidence-card entrances, forensic wipe transitions, and restrained final fade. No jump cuts between scenes.

## What NOT to Do
- No default blue SaaS palette.
- No generic gray-on-gray cards.
- No Roboto fallback as the visual identity.
- No jump cuts between scenes.
"""


def render_video(*, audio_path: str, visual_plan: dict, output_path: str, config: dict) -> str:
    """Render a Postmortem episode video through a generated HyperFrames project."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    render_config = config.get("render", {})
    hyperframes_config = render_config.get("hyperframes", {})
    fps = int(render_config.get("fps", 30))
    width, height = _parse_resolution(render_config.get("resolution", "1920x1080"))
    quality = hyperframes_config.get("quality", "standard")

    duration_seconds = _probe_audio_duration(audio_path)
    composition_dir = _composition_dir_for(output, hyperframes_config)
    composition_dir.mkdir(parents=True, exist_ok=True)
    audio_asset_path = _copy_audio_asset(audio_path, composition_dir)

    (composition_dir / "DESIGN.md").write_text(POSTMORTEM_DESIGN_MD, encoding="utf-8")
    (composition_dir / "index.html").write_text(
        _build_index_html(
            audio_src=audio_asset_path.name,
            visual_plan=visual_plan,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
        ),
        encoding="utf-8",
    )

    _run_hyperframes_command(["lint", "--strict"], composition_dir)
    if hyperframes_config.get("run_validate", True):
        _run_hyperframes_command(["validate"], composition_dir)
    if hyperframes_config.get("run_inspect", True):
        _run_hyperframes_command(["inspect"], composition_dir)
    _run_hyperframes_command(
        [
            "render",
            "--output",
            str(output),
            "--fps",
            str(fps),
            "--quality",
            str(quality),
            "--strict",
        ],
        composition_dir,
    )

    return str(output)


def _probe_audio_duration(audio_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"ffprobe returned invalid duration: {result.stdout!r}") from exc
    if duration <= 0:
        raise RuntimeError(f"ffprobe returned non-positive duration: {duration}")
    return duration


def _run_hyperframes_command(args: list[str], composition_dir: Path) -> None:
    cmd = ["npx", "hyperframes", *args]
    result = subprocess.run(cmd, cwd=str(composition_dir), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "HyperFrames command failed: "
            f"{' '.join(cmd)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _composition_dir_for(output_path: Path, hyperframes_config: dict[str, Any]) -> Path:
    configured_dir = hyperframes_config.get("work_dir")
    if configured_dir:
        return Path(configured_dir) / output_path.stem
    return output_path.parent / ".hyperframes" / output_path.stem


def _copy_audio_asset(audio_path: str, composition_dir: Path) -> Path:
    source = Path(audio_path)
    suffix = source.suffix or ".audio"
    destination = composition_dir / f"audio{suffix}"
    shutil.copy2(source, destination)
    return destination


def _parse_resolution(resolution: str) -> tuple[int, int]:
    width, height = resolution.lower().split("x", 1)
    return int(width), int(height)


def _format_seconds(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _build_index_html(
    *,
    audio_src: str,
    visual_plan: dict,
    duration_seconds: float,
    width: int,
    height: int,
) -> str:
    scenes = _normalized_scenes(visual_plan)
    scene_count = len(scenes)
    scene_duration = duration_seconds / scene_count
    scene_clip_duration = max(scene_duration - 0.001, scene_duration * 0.99)
    transition_duration = min(0.45, max(0.18, scene_duration * 0.18))

    scene_markup = []
    animation_lines = []
    transition_markup = []

    for index, scene in enumerate(scenes, start=1):
        start = (index - 1) * scene_duration
        scene_type = html.escape(str(scene.get("type", "segment")).replace("_", " ").upper())
        scene_text = html.escape(str(scene.get("text") or scene.get("visual_note") or visual_plan.get("title") or "Postmortem"))
        scene_markup.append(
            f"""
      <section id="scene-{index}" class="scene scene-{index} clip" data-start="{_format_seconds(start)}" data-duration="{_format_seconds(scene_clip_duration)}" data-track-index="0">
        <div class="scene-content">
          <div class="eyebrow">{scene_type}</div>
          <h1>{scene_text}</h1>
          <div class="body-card">Reddit evidence, host reactions, and the part where the story turns.</div>
        </div>
      </section>"""
        )
        animation_start = start + 0.18
        animation_lines.extend(
            [
                f'tl.from("#scene-{index} .eyebrow", {{ autoAlpha: 0, y: 32, duration: 0.42, ease: "power3.out" }}, {_format_seconds(animation_start)});',
                f'tl.from("#scene-{index} h1", {{ autoAlpha: 0, y: 58, scale: 0.98, duration: 0.66, ease: "expo.out" }}, {_format_seconds(animation_start + 0.09)});',
                f'tl.from("#scene-{index} .body-card", {{ autoAlpha: 0, y: 18, duration: 0.5, ease: "power3.out" }}, {_format_seconds(animation_start + 0.25)});',
            ]
        )
        if index < scene_count:
            transition_start = max(start + scene_duration - transition_duration, start)
            transition_markup.append(
                f'<div id="transition-wipe-{index}" class="transition-wipe clip" data-start="{_format_seconds(transition_start)}" data-duration="{_format_seconds(transition_duration)}" data-track-index="10"></div>'
            )
            animation_lines.extend(
                [
                    f'tl.fromTo("#transition-wipe-{index}", {{ x: "-105%" }}, {{ x: "0%", duration: {_format_seconds(transition_duration / 2)}, ease: "power4.in" }}, {_format_seconds(transition_start)});',
                    f'tl.to("#transition-wipe-{index}", {{ x: "105%", duration: {_format_seconds(transition_duration / 2)}, ease: "power4.out" }}, {_format_seconds(transition_start + transition_duration / 2)});',
                ]
            )

    final_fade_start = max(duration_seconds - 0.55, 0)
    animation_lines.append(
        f'tl.to("#scene-{scene_count} .scene-content", {{ autoAlpha: 0, duration: 0.45, ease: "power2.in" }}, {_format_seconds(final_fade_start)});'
    )
    animation_script = "\n    ".join(animation_lines)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(str(visual_plan.get("title", "Postmortem")))}</title>
  <style>
    :root {{
      --pm-canvas: #0B0F14;
      --pm-panel: #151B23;
      --pm-bone: #F5E6C8;
      --pm-coral: #FF4D2E;
      --pm-slate: #8F9BB3;
      --pm-gold: #F2C14E;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: var(--pm-canvas); }}
    #stage {{
      position: relative;
      width: {width}px;
      height: {height}px;
      overflow: hidden;
      color: var(--pm-bone);
      background:
        radial-gradient(circle at 18% 12%, rgba(255, 77, 46, 0.24), transparent 28%),
        radial-gradient(circle at 82% 88%, rgba(242, 193, 78, 0.18), transparent 30%),
        var(--pm-canvas);
      font-family: "Space Grotesk", "Newsreader", sans-serif;
    }}
    #stage::before {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      opacity: 0.18;
      background-image: linear-gradient(rgba(245, 230, 200, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(245, 230, 200, 0.08) 1px, transparent 1px);
      background-size: 56px 56px;
    }}
    .scene {{
      position: absolute;
      inset: 0;
      z-index: 1;
    }}
    .scene-content {{
      width: 100%;
      height: 100%;
      padding: clamp(24px, 5vw, 96px);
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: clamp(10px, 1.8vw, 30px);
    }}
    .eyebrow {{
      width: max-content;
      max-width: 100%;
      padding: 8px 12px;
      border: 2px solid var(--pm-coral);
      color: var(--pm-gold);
      background: rgba(21, 27, 35, 0.88);
      font-size: clamp(14px, 2.2vw, 32px);
      font-weight: 800;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    h1 {{
      max-width: min(22ch, 92%);
      margin: 0;
      color: var(--pm-bone);
      font-family: "Space Grotesk", sans-serif;
      font-size: clamp(28px, 5.7vw, 84px);
      line-height: 0.92;
      letter-spacing: -0.055em;
      text-wrap: balance;
      text-shadow: 0 12px 48px rgba(255, 77, 46, 0.26);
    }}
    .body-card {{
      max-width: min(980px, 84%);
      padding: 12px 16px;
      border-left: 8px solid var(--pm-coral);
      background: rgba(21, 27, 35, 0.9);
      color: var(--pm-slate);
      font-family: "Newsreader", serif;
      font-size: clamp(14px, 2vw, 26px);
      line-height: 1.12;
    }}
    .transition-wipe {{
      position: absolute;
      inset: 0;
      z-index: 30;
      background: linear-gradient(100deg, var(--pm-coral) 0%, var(--pm-gold) 52%, var(--pm-bone) 100%);
      box-shadow: 0 0 80px rgba(255, 77, 46, 0.38);
    }}
  </style>
</head>
<body>
  <div id="stage" data-composition-id="root" data-start="0" data-duration="{_format_seconds(duration_seconds)}" data-width="{width}" data-height="{height}">
{''.join(scene_markup)}
      {''.join(transition_markup)}
      <audio id="episode-audio" data-start="0" data-duration="{_format_seconds(duration_seconds)}" data-track-index="20" src="{html.escape(audio_src)}"></audio>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
    {animation_script}
    window.__timelines["root"] = tl;
  </script>
</body>
</html>
"""


def _normalized_scenes(visual_plan: dict) -> list[dict[str, Any]]:
    scenes = visual_plan.get("scenes") or []
    normalized = [scene for scene in scenes if isinstance(scene, dict)]
    if normalized:
        return normalized
    return [{"type": "title_card", "text": visual_plan.get("title", "Postmortem")}]
