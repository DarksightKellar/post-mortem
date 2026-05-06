import re
import subprocess
from pathlib import Path

from reddit_automation.utils.hyperframes import _build_index_html, render_video


def test_render_video_builds_hyperframes_composition_and_runs_quality_gates(monkeypatch, tmp_path):
    audio_path = tmp_path / "episode audio.mp3"
    audio_path.write_bytes(b"fake audio")
    output_path = tmp_path / "rendered" / "episode.mp4"
    visual_plan = {
        "episode_date": "2026-04-03",
        "title": "Airport C4 <chaos> & Reddit fallout",
        "scenes": [
            {"type": "title_card", "text": "Airport C4 <chaos> & Reddit fallout"},
            {"type": "segment", "text": "TSA asks what is in the lunchbox."},
        ],
    }
    config = {
        "render": {
            "resolution": "1080x1920",
            "fps": 24,
            "hyperframes": {
                "quality": "draft",
                "run_validate": True,
                "run_inspect": True,
            },
        }
    }
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "cwd": kwargs.get("cwd")})
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="12.5\n", stderr="")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = render_video(
        audio_path=str(audio_path),
        visual_plan=visual_plan,
        output_path=str(output_path),
        config=config,
    )

    composition_dir = output_path.parent / ".hyperframes" / output_path.stem
    html = (composition_dir / "index.html").read_text(encoding="utf-8")
    design_md = (composition_dir / "DESIGN.md").read_text(encoding="utf-8")

    assert result == str(output_path)
    assert 'data-composition-id="root"' in html
    assert 'data-duration="12.5"' in html
    assert 'data-width="1080"' in html
    assert 'data-height="1920"' in html
    assert "Airport C4 &lt;chaos&gt; &amp; Reddit fallout" in html
    assert "TSA asks what is in the lunchbox." in html
    assert 'class="scene scene-1 clip"' in html
    assert 'class="scene scene-2 clip"' in html
    assert 'class="transition-wipe clip"' in html
    assert f'src="{audio_path.as_uri()}"' not in html
    assert 'src="audio.mp3"' in html
    assert (composition_dir / "audio.mp3").read_bytes() == b"fake audio"
    assert "Postmortem" in design_md
    assert "#333" not in html
    assert "#3b82f6" not in html
    assert "Roboto" not in html

    assert [call["cmd"][:3] for call in calls] == [
        ["ffprobe", "-v", "error"],
        ["npx", "hyperframes", "lint"],
        ["npx", "hyperframes", "validate"],
        ["npx", "hyperframes", "inspect"],
        ["npx", "hyperframes", "render"],
    ]
    assert calls[-1]["cwd"] == str(composition_dir)
    assert "--output" in calls[-1]["cmd"]
    assert str(output_path) in calls[-1]["cmd"]
    assert calls[-1]["cmd"][calls[-1]["cmd"].index("--fps") + 1] == "24"
    assert calls[-1]["cmd"][calls[-1]["cmd"].index("--quality") + 1] == "draft"


def test_render_video_avoids_fractional_scene_clip_overlaps_for_hyperframes_lint():
    html = _build_index_html(
        audio_src="audio.wav",
        visual_plan={
            "title": "Fractional timing smoke",
            "scenes": [
                {"type": "title_card", "text": "One"},
                {"type": "segment", "text": "Two"},
                {"type": "payoff", "text": "Three"},
            ],
        },
        duration_seconds=3.2,
        width=1280,
        height=720,
    )

    scene_timings = [
        (float(start), float(duration))
        for start, duration in re.findall(
            r'class="scene scene-\d+ clip" data-start="([^"]+)" data-duration="([^"]+)"',
            html,
        )
    ]

    assert len(scene_timings) == 3
    for index in range(len(scene_timings) - 1):
        current_start, duration = scene_timings[index]
        next_start, _ = scene_timings[index + 1]
        assert current_start + duration <= next_start


def test_render_video_uses_bounded_typography_for_generated_long_scene_text():
    html = _build_index_html(
        audio_src="audio.wav",
        visual_plan={
            "title": "Long generated scene smoke",
            "scenes": [
                {
                    "type": "segment",
                    "text": "HyperFrames builds HTML, validates it, inspects layout, then renders MP4.",
                },
            ],
        },
        duration_seconds=3.2,
        width=1280,
        height=720,
    )

    assert "max-width: min(22ch, 92%);" in html
    assert "font-size: clamp(28px, 5.7vw, 84px);" in html
    assert "font-size: clamp(14px, 2vw, 26px);" in html


def test_render_video_uses_responsive_spacing_for_low_resolution_compositions(monkeypatch, tmp_path):
    audio_path = tmp_path / "episode.wav"
    audio_path.write_bytes(b"fake audio")
    output_path = tmp_path / "rendered" / "small.mp4"
    visual_plan = {
        "title": "Small frame smoke",
        "scenes": [
            {"type": "title_card", "text": "Small frame smoke"},
            {"type": "segment", "text": "Render path verified"},
        ],
    }

    def fake_run(cmd, **kwargs):
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="1.2\n", stderr="")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    render_video(
        audio_path=str(audio_path),
        visual_plan=visual_plan,
        output_path=str(output_path),
        config={"render": {"resolution": "640x360", "fps": 24, "hyperframes": {"quality": "draft"}}},
    )

    html = (output_path.parent / ".hyperframes" / output_path.stem / "index.html").read_text(encoding="utf-8")

    assert "padding: clamp(24px, 5vw, 96px);" in html
    assert "gap: clamp(10px, 1.8vw, 30px);" in html
    assert "font-size: clamp(28px, 5.7vw, 84px);" in html
    assert "font-size: clamp(14px, 2vw, 26px);" in html
    assert '.body-card", { autoAlpha: 0, x: -' not in html
