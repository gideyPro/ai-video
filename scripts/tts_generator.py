#!/usr/bin/env python3
import json
import sys
import os
import asyncio
import tempfile
import subprocess


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

async def generate_tts(text, output_file, voice="am"):
    from gtts import gTTS
    tts = gTTS(text, lang='am')
    tts.save(output_file)


def get_duration(audio_file):
    if not os.path.exists(audio_file): return 0
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file]
    try:
        return float(subprocess.check_output(cmd).decode().strip())
    except:
        return 0

def pad_and_concat(audio_files, target_durations, output_file):
    list_file = os.path.join(os.path.dirname(output_file), "concat.txt")
    with open(list_file, "w") as f:
        for audio, dur in zip(audio_files, target_durations):
            if audio and os.path.exists(audio):
                f.write(f"file '{audio}'\n")
            else:
                # generate silence
                silent = os.path.join(os.path.dirname(output_file), f"silence_{dur}.mp3")
                if not os.path.exists(silent):
                    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(dur), silent], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                f.write(f"file '{silent}'\n")
                
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
    updated_scenes = False
    
    audio_files = []
    target_durations = []

    for i, scene in enumerate(scenes):
        extracted = extract_text_from_scene(scene)
        scene_text = "... ".join(extracted)
        
        # ADD EXTRACTION FOR NEW TEMPLATES
        template = scene.get("template", "")
        if template == "quote":
            scene_text = scene.get("data", {}).get("text", "") + " ... " + scene.get("data", {}).get("author", "")
        elif template == "news_flash":
            scene_text = scene.get("data", {}).get("headline", "") + " ... " + scene.get("data", {}).get("subtext", "")
        elif template == "split_three":
            scene_text = scene.get("data", {}).get("title", "") + " ... " + ", ".join(scene.get("data", {}).get("items", []))
        elif template == "map_marker":
            scene_text = "Location: " + scene.get("data", {}).get("label", "")
        elif template == "code_snippet":
            scene_text = "Code snippet: " + scene.get("data", {}).get("title", "")

        target_duration_s = scene.get("duration", 5)

        if scene_text:
            tmp_mp3 = os.path.join(tmpdir, f"scene_{i}.mp3")
            await generate_tts(scene_text, tmp_mp3, voice)

            audio_duration_s = get_duration(tmp_mp3)

            if audio_duration_s + 0.5 > target_duration_s:
                target_duration_s = round(audio_duration_s + 0.5, 1)
                scene["duration"] = target_duration_s
                updated_scenes = True

            padded_mp3 = os.path.join(tmpdir, f"scene_{i}_padded.mp3")
            subprocess.run(["ffmpeg", "-y", "-i", tmp_mp3, "-af", f"apad,atrim=0:{target_duration_s}", padded_mp3], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            audio_files.append(padded_mp3)
            target_durations.append(target_duration_s)
        else:
            audio_files.append(None)
            target_durations.append(target_duration_s)

    if updated_scenes:
        print("Audio was longer than some scenes. Updating scene durations in JSON...")
        with open(scene_file, "w") as f:
            json.dump(data, f, indent=2)

    pad_and_concat(audio_files, target_durations, output_file)
    print(f"Saved perfectly timed audio to {output_file}")

    import shutil
    shutil.rmtree(tmpdir)

if __name__ == '__main__':
    asyncio.run(main())
