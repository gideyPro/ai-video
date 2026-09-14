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
import random
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
    if not color_str: return (10, 10, 10)
    if isinstance(color_str, (list, tuple)): return tuple(color_str)
    color_str = color_str.lstrip("#")
    if len(color_str) == 6:
        return (int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16))
    return (10, 10, 10)

def get_broll_frame(video_path, frame_number, target_w, target_h, fps=30):
    timestamp = frame_number / float(fps)
    tmp_path = f"/tmp/broll_frame_{os.getpid()}.jpg"
    cmd = [
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path,
        "-frames:v", "1", "-q:v", "2", tmp_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(tmp_path):
        try:
            img = Image.open(tmp_path).convert("RGB")
            img = img.resize((target_w, target_h), Image.LANCZOS)
            return img.convert("RGBA")
        except Exception:
            pass
    return None

def render_background(img, config, progress=0.0):
    """Render a smooth animated diagonal gradient background with radial vignette."""
    colors = config.get("colors", {})
    draw = ImageDraw.Draw(img)
    w, h = img.size

    bg_start = parse_color(colors.get("gradient_start", "#0f0c29"))
    bg_end = parse_color(colors.get("gradient_end", "#302b63"))

    # Slow diagonal shift for subtle movement (no jarring particles)
    shift = math.sin(progress * math.pi * 0.8) * 0.12

    for y in range(h):
        t = y / h + shift
        t = max(0.0, min(1.0, t))
        r = int(bg_start[0] * (1 - t) + bg_end[0] * t)
        g = int(bg_start[1] * (1 - t) + bg_end[1] * t)
        b = int(bg_start[2] * (1 - t) + bg_end[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Radial vignette — darkens edges organically
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    cx, cy = w // 2, h // 2
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    steps = 20
    for i in range(steps, 0, -1):
        t = i / steps
        alpha = int(0.35 * 255 * (t ** 1.8))
        r = int(max_dist * (1.0 - (steps - i) / steps * 0.25))
        v_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, alpha))
    img.paste(vignette, (0, 0), vignette)

    return img

def apply_transition(img, anim_type, t):
    w, h = img.size
    out_img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    alpha_mask = int(t * 255)
    
    if anim_type in ("slideInLeft", "slideOutRight"):
        offset_x = int((1 - t) * -w)
        out_img.paste(img, (offset_x, 0))
    elif anim_type in ("slideInRight", "slideOutLeft"):
        offset_x = int((1 - t) * w)
        out_img.paste(img, (offset_x, 0))
    elif anim_type in ("slideUp", "slideOutDown"):
        offset_y = int((1 - t) * h)
        out_img.paste(img, (0, offset_y))
    elif anim_type in ("zoomIn", "zoomOut"):
        scale = 0.5 + 0.5 * t
        new_w, new_h = int(w * scale), int(h * scale)
        scaled = img.resize((new_w, new_h), Image.LANCZOS)
        mask = Image.new("L", (new_w, new_h), alpha_mask)
        out_img.paste(scaled, ((w - new_w)//2, (h - new_h)//2), mask)
    else: 
        mask = Image.new("L", (w, h), alpha_mask)
        out_img.paste(img, (0, 0), mask)
        
    return out_img

def render_scene_frame(scene, frame_number, fps, width, height, config):
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

    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    
    bg_video = scene.get("background_video")
    bg_image = scene.get("background_image")
    
    if bg_video and os.path.exists(bg_video):
        broll_img = get_broll_frame(bg_video, frame_number, width, height, fps)
        if broll_img:
            img.paste(broll_img, (0,0))
    elif bg_image and os.path.exists(bg_image):
        try:
            bg_img_obj = Image.open(bg_image).convert("RGBA")
            bg_img_obj = bg_img_obj.resize((width, height), Image.LANCZOS)
            img.paste(bg_img_obj, (0,0))
        except Exception as e:
            print("Failed to load background image:", e)
            img = render_background(img, config, progress)
    else:
        img = render_background(img, config, progress)
        
    draw = ImageDraw.Draw(img)
    import templates
    templates.set_config(config)
    img = render_template(template, img, draw, data, progress, config)

    if in_frames > 0 and frame_number < in_frames:
        t = frame_number / max(in_frames, 1)
        img = apply_transition(img, animation_in, t)
    elif out_frames > 0 and frame_number >= total_frames - out_frames:
        remaining = total_frames - frame_number
        t = remaining / max(out_frames, 1)
        img = apply_transition(img, animation_out, t)

    return img.convert("RGB")

def render_scene_frames(scene, fps, width, height, config, output_dir):
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

def frames_to_video(frame_paths, output_path, fps, audio_path=None, bgm_path=None):
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
    ]

    filters = []
    
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])
        if bgm_path and os.path.exists(bgm_path):
            cmd.extend(["-i", bgm_path])
            filters.append("[1:a]volume=1.0[a1];[2:a]volume=0.2[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[a]")
        else:
            filters.append("[1:a]volume=1.0[a]")
    
    if filters:
        cmd.extend(["-filter_complex", "".join(filters), "-map", "0:v", "-map", "[a]"])
    
    cmd.extend([
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ])

    print(f"Running FFmpeg: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

    if result.returncode != 0:
        print(f"FFmpeg error:\n{result.stderr}")
        return False

    return True

def validate_and_render(scene_data, output_path, project_dir=None, config=None, explicit_audio_path=None):
    video_config = scene_data.get("video", {})
    width = video_config.get("width", 1920)
    height = video_config.get("height", 1080)
    fps = video_config.get("fps", 30)
    scenes = scene_data.get("scenes", [])
    
    tmpdir = tempfile.mkdtemp(prefix="video_render_")
    all_frames = []

    for i, scene in enumerate(scenes):
        frames = render_scene_frames(scene, fps, width, height, config, tmpdir)
        all_frames.extend(frames)

    audio_path = explicit_audio_path if explicit_audio_path and os.path.exists(explicit_audio_path) else None
    if not audio_path:
        for candidate in ["narration.mp3", "audio.mp3"]:
            p = os.path.join(project_dir, candidate) if project_dir else candidate
            if os.path.exists(p):
                audio_path = p; break

    bgm_path = config.get("bgm_path") if config else None
    if bgm_path and not os.path.exists(bgm_path):
        bgm_path = os.path.join(project_dir, bgm_path) if project_dir else None

    return frames_to_video(all_frames, output_path, fps, audio_path, bgm_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene_json")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-c", "--config", default=None)
    parser.add_argument("-a", "--audio", default=None)
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()

    with open(args.scene_json) as f:
        scene_data = json.load(f)

    config = load_config(args.config)
    if "config" in scene_data:
        config.update(scene_data["config"])
    video_config = scene_data.get("video", {})
    width = video_config.get("width", 1920)
    height = video_config.get("height", 1080)
    fps = video_config.get("fps", 30)

    if args.preview_only:
        scene = scene_data.get("scenes", [])[0]
        duration = scene.get("duration", 5)
        frame_img = render_scene_frame(scene, int(duration * fps / 2), fps, width, height, config)
        os.makedirs("output", exist_ok=True)
        frame_img.save("output/preview.png")
        sys.exit(0)

    output_path = args.output
    if output_path is None:
        slug = scene_data.get("video", {}).get("title", "output").lower().replace(" ", "-")
        output_path = os.path.join("output", f"{slug}.mp4")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    project_dir = os.path.dirname(os.path.abspath(args.scene_json))

    success = validate_and_render(scene_data, os.path.abspath(output_path), project_dir, config, explicit_audio_path=args.audio)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
