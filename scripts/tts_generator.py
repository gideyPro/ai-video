#!/usr/bin/env python3
import json
import sys
import os
import asyncio
import tempfile
import subprocess
from pydub import AudioSegment

try:
    import edge_tts
except ImportError:
    print("edge_tts is required. Install with: pip install edge-tts", file=sys.stderr)
    sys.exit(1)

def extract_text_from_scene(scene):
    texts = []
    template = scene.get("template", "")
    data = scene.get("data", {})

    if template == "title":
        texts.append(data.get("title", ""))
        texts.append(data.get("subtitle", ""))
    elif template == "chapter_title":
        texts.append(data.get("title", ""))
    elif template == "fact":
        texts.append(data.get("text", ""))
    elif template == "conclusion":
        texts.append(data.get("title", ""))
        texts.append(data.get("text", ""))
    elif template == "statistics":
        texts.append(data.get("title", ""))
        for item in data.get("items", []):
            label = item.get("label", "")
            value = item.get("value", "")
            unit = item.get("unit", "")
            texts.append(f"{label} {value} {unit}")
    elif template == "ranking":
        texts.append(data.get("title", ""))
        for i, item in enumerate(data.get("items", [])):
            name = item.get("name", "")
            detail = item.get("detail", "")
            texts.append(f"Number {i + 1}, {name}, {detail}")
    elif template == "side_by_side" or template == "comparison":
        for side in ["left", "right"]:
            s = data.get(side, {})
            texts.append(s.get("title", ""))
            texts.append(s.get("text", ""))
    elif template == "image_text":
        texts.append(data.get("title", ""))
        texts.append(data.get("text", ""))
    elif template == "timeline":
        texts.append(data.get("title", ""))
        for event in data.get("events", []):
            year = event.get("year", event.get("date", ""))
            desc = event.get("description", event.get("text", ""))
            texts.append(f"{year}, {desc}")

    return [t.strip() for t in texts if t and t.strip()]

async def generate_tts(text, output_file, voice="en-US-AriaNeural"):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

async def main():
    if len(sys.argv) < 3:
        print("Usage: python tts_generator.py <scene.json> <output.mp3> [--voice <voice>]", file=sys.stderr)
        sys.exit(1)

    scene_file = sys.argv[1]
    output_file = sys.argv[2]
    voice = "en-US-AriaNeural"

    if len(sys.argv) > 3 and sys.argv[3] == "--voice" and len(sys.argv) > 4:
        voice = sys.argv[4]

    if not os.path.exists(scene_file):
        print(f"File not found: {scene_file}", file=sys.stderr)
        sys.exit(1)

    with open(scene_file) as f:
        data = json.load(f)

    scenes = data.get("scenes", [])

    tmpdir = tempfile.mkdtemp(prefix="video_tts_")
    final_audio = AudioSegment.empty()
    updated_scenes = False

    for i, scene in enumerate(scenes):
        extracted = extract_text_from_scene(scene)
        scene_text = "... ".join(extracted)

        target_duration_s = scene.get("duration", 5)

        if scene_text:
            tmp_mp3 = os.path.join(tmpdir, f"scene_{i}.mp3")
            await generate_tts(scene_text, tmp_mp3, voice)

            # Load with pydub to get exact duration
            audio_segment = AudioSegment.from_mp3(tmp_mp3)
            audio_duration_s = len(audio_segment) / 1000.0

            # If audio is longer than visual scene duration, we must extend visual scene
            # We add a small buffer (0.5s) to let the voice finish naturally
            if audio_duration_s + 0.5 > target_duration_s:
                target_duration_s = round(audio_duration_s + 0.5, 1)
                scene["duration"] = target_duration_s
                updated_scenes = True

            # Pad audio to exact target duration (so visuals and audio match perfectly)
            target_duration_ms = int(target_duration_s * 1000)
            padding_ms = target_duration_ms - len(audio_segment)
            if padding_ms > 0:
                silence = AudioSegment.silent(duration=padding_ms)
                audio_segment = audio_segment + silence

            final_audio += audio_segment
        else:
            # No text, just add silence for the duration
            silence = AudioSegment.silent(duration=int(target_duration_s * 1000))
            final_audio += silence

    if updated_scenes:
        print("Audio was longer than some scenes. Updating scene durations in JSON...")
        with open(scene_file, "w") as f:
            json.dump(data, f, indent=2)

    final_audio.export(output_file, format="mp3")
    print(f"Saved perfectly timed audio to {output_file}")

    # Clean up temporary directory
    import shutil
    shutil.rmtree(tmpdir)

if __name__ == "__main__":
    asyncio.run(main())
