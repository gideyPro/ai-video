#!/usr/bin/env python3
"""Main video renderer engine. Reads scene JSON and produces frame sequences + MP4."""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from templates import render_template, COLORS, get_font
from validate import validate_scene_json


def load_config(config_path=None):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.json")
    config_path = os.path.abspath(config_path)
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {}


def parse_color(color_str):
    if not color_str:
        return (10, 10, 10)
    if isinstance(color_str, (list, tuple)):
        return tuple(color_str)
    color_str = color_str.lstrip("#")
    if len(color_str) == 6:
        return (int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16))
    return (10, 10, 10)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def render_background(img, config):
    style = config.get("visual_style", "modern_dark")
    colors = config.get("colors", {})
    draw = ImageDraw.Draw(img)
    w, h = img.size

    bg_start = parse_color(colors.get("gradient_start", "#0f0c29"))
    bg_end = parse_color(colors.get("gradient_end", "#302b63"))

    for y in range(h):
        t = y / h
        r = int(bg_start[0] * (1 - t) + bg_end[0] * t)
        g = int(bg_start[1] * (1 - t) + bg_end[1] * t)
        b = int(bg_start[2] * (1 - t) + bg_end[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    return img


def render_scene_frame(scene, frame_number, fps, width, height, config):
    """Render a single frame for a scene."""
    duration = scene.get("duration", 5)
    total_frames = int(duration * fps)
    template = scene.get("template", "title")
    data = scene.get("data", {})

    progress = frame_number / max(total_frames - 1, 1)
    animation_in = scene.get("animation_in", "fadeIn")
    animation_out = scene.get("animation_out", "fadeOut")
    anim_in_duration = scene.get("anim_in_duration", 0.5)
    anim_out_duration = scene.get("anim_out_duration", 0.5)

    in_frames = int(anim_in_duration * fps)
    out_frames = int(anim_out_duration * fps)

    alpha = 1.0
    if in_frames > 0 and frame_number < in_frames:
        alpha = frame_number / max(in_frames, 1)
    elif out_frames > 0 and frame_number >= total_frames - out_frames:
        remaining = total_frames - frame_number
        alpha = remaining / max(out_frames, 1)

    alpha = max(0.0, min(1.0, alpha))

    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    img = render_background(img, config)
    draw = ImageDraw.Draw(img)

    img = render_template(template, img, draw, data, progress, config)

    if alpha < 1.0:
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        black = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        mask = Image.new("L", (width, height), int(alpha * 255))
        img = Image.composite(img, black, mask)

    return img.convert("RGB")


def render_scene_frames(scene, fps, width, height, config, output_dir):
    """Render all frames for a scene, return list of frame file paths."""
    duration = scene.get("duration", 5)
    total_frames = int(duration * fps)
    scene_id = scene.get("id", "unknown")
    scene_dir = os.path.join(output_dir, scene_id)
    os.makedirs(scene_dir, exist_ok=True)

    frame_paths = []
    for f in range(total_frames):
        frame_img = render_scene_frame(scene, f, fps, width, height, config)
        frame_path = os.path.join(scene_dir, f"frame_{f:06d}.png")
        frame_img.save(frame_path)
        frame_paths.append(frame_path)

    return frame_paths


def concat_frame_lists(all_frame_lists):
    result = []
    for fl in all_frame_lists:
        result.extend(fl)
    return result


def frames_to_video(frame_paths, output_path, fps, audio_path=None):
    """Use FFmpeg to convert frame sequence to MP4."""
    if not frame_paths:
        print("No frames to render!")
        return False

    tmpdir = tempfile.mkdtemp()
    list_file = os.path.join(tmpdir, "frames.txt")
    with open(list_file, "w") as f:
        for fp in frame_paths:
            f.write(f"file '{os.path.abspath(fp)}'\n")
            f.write(f"duration {1.0 / fps}\n")
        if frame_paths:
            f.write(f"file '{os.path.abspath(frame_paths[-1])}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-preset", "ultrafast",
        "-crf", "28",
    ]

    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path, "-c:a", "aac", "-b:a", "128k", "-shortest"])

    cmd.append(output_path)

    print(f"Running FFmpeg: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

    if result.returncode != 0:
        print(f"FFmpeg error:\n{result.stderr}")
        return False

    file_size = os.path.getsize(output_path)
    print(f"Video created: {output_path} ({file_size / 1024:.1f} KB)")
    return True


def validate_and_render(scene_data, output_path, project_dir=None, config=None):
    is_valid, errors = validate_scene_json(scene_data, project_dir)
    if not is_valid:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        return False

    if config is None:
        config = load_config()

    video_config = scene_data.get("video", {})
    width = video_config.get("width", 1920)
    height = video_config.get("height", 1080)
    fps = video_config.get("fps", 30)

    scenes = scene_data.get("scenes", [])
    total_duration = sum(s.get("duration", 5) for s in scenes)
    print(f"Rendering {len(scenes)} scenes, {total_duration:.1f}s total, {width}x{height}@{fps}fps")

    tmpdir = tempfile.mkdtemp(prefix="video_render_")
    all_frames = []

    for i, scene in enumerate(scenes):
        print(f"  Scene {i + 1}/{len(scenes)}: {scene.get('id', '?')} ({scene.get('template', '?')}) [{scene.get('duration', 5)}s]")
        frames = render_scene_frames(scene, fps, width, height, config, tmpdir)
        all_frames.extend(frames)

    audio_path = None
    for candidate in ["narration.mp3", "narration.wav", "audio.mp3", "audio.wav"]:
        p = os.path.join(project_dir, candidate) if project_dir else candidate
        if os.path.exists(p):
            audio_path = p
            break

    success = frames_to_video(all_frames, output_path, fps, audio_path)
    return success


def main():
    parser = argparse.ArgumentParser(description="AI Video Renderer")
    parser.add_argument("scene_json", help="Path to scene JSON file")
    parser.add_argument("-o", "--output", default=None, help="Output MP4 path")
    parser.add_argument("-c", "--config", default=None, help="Config file path")
    parser.add_argument("--validate-only", action="store_true", help="Only validate the scene JSON")
    args = parser.parse_args()

    with open(args.scene_json) as f:
        scene_data = json.load(f)

    if args.validate_only:
        is_valid, errors = validate_scene_json(scene_data)
        if is_valid:
            print("Scene JSON is valid.")
        else:
            print("Errors:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        return

    output_path = args.output
    if output_path is None:
        title = scene_data.get("video", {}).get("title", "output")
        slug = title.lower().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        output_path = os.path.join("output", f"{slug}.mp4")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    project_dir = os.path.dirname(os.path.abspath(args.scene_json))
    config = load_config(args.config)

    success = validate_and_render(scene_data, os.path.abspath(output_path), project_dir, config)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
