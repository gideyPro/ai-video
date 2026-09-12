#!/usr/bin/env python3
"""AI script generator for the video engine. Modular AI provider support."""

import json
import os
import subprocess
import sys

PROMPT_TEMPLATE = """You are a professional YouTube video script writer. Given a topic, create a structured video scene plan.

Topic: {topic}
Target Duration: {duration} seconds
Resolution: {width}x{height}

Create a JSON scene plan following this exact schema. Output ONLY valid JSON, no explanation:

{{
  "video": {{
    "title": "Video Title",
    "width": {width},
    "height": {height},
    "fps": 30
  }},
  "scenes": [
    {{
      "id": "intro",
      "template": "title",
      "duration": 4,
      "data": {{
        "title": "Video Title",
        "subtitle": "An interesting exploration"
      }},
      "animation_in": "fadeIn",
      "animation_out": "fadeOut",
      "anim_in_duration": 0.5,
      "anim_out_duration": 0.5
    }}
  ]
}}

Available templates:
- title: Title screen with title and optional subtitle
- comparison: Side-by-side comparison with left/right data
- image_text: Image with text overlay, layout "left" or "right"
- statistics: Animated bar chart with items array [{{label, value, max, unit, color}}]
- fact: Single fact with number and text
- side_by_side: Two content panels
- ranking: Ranked list with items array [{{name, detail}}]
- conclusion: Final screen with title and text
- chapter_title: Chapter/section divider with number and title
- timeline: Timeline with events array [{{year, description}}]

Available animations: fadeIn, fadeOut, slideInLeft, slideInRight, slideUp, slideDown, zoomIn, zoomOut, scale, none

Create a script with:
1. title scene (intro)
2. 3-6 content scenes using various templates
3. statistics or ranking scene if applicable
4. conclusion scene

For comparison topics, use the comparison template.
For educational topics, use fact, statistics, chapter_title templates.
For list topics, use ranking template.

Each scene should have animation_in and animation_out set to appropriate animations.
Set anim_in_duration and anim_out_duration to 0.5 each.
Duration should be 4-8 seconds per scene.
Target total duration close to {duration} seconds.

Output ONLY the JSON object, nothing else."""


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.json")
    config_path = os.path.abspath(config_path)
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {}


def generate_with_ollama(prompt, model="llama3.2"):
    """Generate using local Ollama instance."""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/generate", "-d",
             json.dumps({"model": model, "prompt": prompt, "stream": False})],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            response = json.loads(result.stdout)
            return response.get("response", "")
    except Exception as e:
        print(f"Ollama error: {e}", file=sys.stderr)
    return None


def generate_with_openai_compat(prompt, api_key, base_url, model):
    """Generate using OpenAI-compatible API."""
    try:
        import urllib.request
        url = f"{base_url.rstrip('/')}/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        })
        req = urllib.request.Request(url, data=payload.encode(), headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        })
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
    return None


def extract_json(text):
    """Extract JSON from text that may contain markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            elif line.startswith("```") and in_block:
                break
            elif in_block:
                json_lines.append(line)
        text = "\n".join(json_lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


def generate_script(topic, duration=60, config=None, output_path=None):
    """Generate a scene plan for a video topic."""
    if config is None:
        config = load_config()

    width = config.get("resolution", {}).get("width", 1920)
    height = config.get("resolution", {}).get("height", 1080)

    prompt = PROMPT_TEMPLATE.format(
        topic=topic, duration=duration, width=width, height=height
    )

    provider = config.get("provider", "ollama")
    model = config.get("model", "llama3.2")
    api_key_env = config.get("api_key_env", "AI_API_KEY")

    print(f"Generating script with {provider}/{model}...")
    print(f"Topic: {topic}")
    print(f"Target duration: {duration}s")

    response_text = None

    if provider == "ollama":
        response_text = generate_with_ollama(prompt, model)
    elif provider in ("openai", "openai_compat"):
        api_key = os.environ.get(api_key_env, "")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        if not api_key:
            print(f"Error: Set {api_key_env} environment variable", file=sys.stderr)
            return None
        response_text = generate_with_openai_compat(prompt, api_key, base_url, model)
    else:
        print(f"Unknown provider: {provider}. Trying Ollama as fallback.", file=sys.stderr)
        response_text = generate_with_ollama(prompt, model)

    if not response_text:
        print("Failed to generate script from AI. Using fallback template.", file=sys.stderr)
        scene_data = generate_fallback_script(topic, duration, config)
    else:
        scene_data = extract_json(response_text)
        if not scene_data:
            print("Failed to parse AI response as JSON. Using fallback.", file=sys.stderr)
            scene_data = generate_fallback_script(topic, duration, config)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(scene_data, f, indent=2)
        print(f"Script saved to: {output_path}")

    return scene_data


def generate_fallback_script(topic, duration=60, config=None):
    """Generate a deterministic fallback script when AI is unavailable."""
    if config is None:
        config = load_config()
    width = config.get("resolution", {}).get("width", 1920)
    height = config.get("resolution", {}).get("height", 1080)

    words = topic.split()
    is_vs = any(w.lower() == "vs" for w in words)
    clean_topic = topic.replace("vs", "versus").strip()

    if is_vs:
        parts = topic.split("vs")
        left_name = parts[0].strip() if len(parts) > 0 else "Option A"
        right_name = parts[1].strip() if len(parts) > 1 else "Option B"
        scenes = [
            {"id": "intro", "template": "title", "duration": 4,
             "data": {"title": clean_topic, "subtitle": "Which is better?"},
             "animation_in": "fadeIn", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "comparison", "template": "comparison", "duration": 6,
             "data": {"left": {"title": left_name}, "right": {"title": right_name}, "vs_text": "VS"},
             "animation_in": "fadeIn", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "ch1", "template": "chapter_title", "duration": 3,
             "data": {"title": "Key Differences", "number": "1"},
             "animation_in": "slideInLeft", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "fact1", "template": "fact", "duration": 5,
             "data": {"number": "01", "text": f"Both {left_name} and {right_name} are remarkable in their own ways"},
             "animation_in": "slideInLeft", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "stats", "template": "statistics", "duration": 6,
             "data": {"title": "Comparison Stats",
                      "items": [
                          {"label": f"{left_name} Power", "value": 85, "max": 100, "unit": "%", "color": "secondary"},
                          {"label": f"{right_name} Power", "value": 90, "max": 100, "unit": "%", "color": "primary"},
                          {"label": f"{left_name} Speed", "value": 80, "max": 100, "unit": "%", "color": "secondary"},
                          {"label": f"{right_name} Speed", "value": 75, "max": 100, "unit": "%", "color": "primary"}
                      ]},
             "animation_in": "fadeIn", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "fact2", "template": "fact", "duration": 5,
             "data": {"number": "02", "text": f"The {left_name} is known for its strength and courage"},
             "animation_in": "slideInRight", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "fact3", "template": "fact", "duration": 5,
             "data": {"number": "03", "text": f"The {right_name} is celebrated for its agility and hunting skills"},
             "animation_in": "slideInLeft", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "ranking", "template": "ranking", "duration": 5,
             "data": {"title": "Overall Ranking",
                      "items": [
                          {"name": right_name, "detail": "90/100"},
                          {"name": left_name, "detail": "88/100"}
                      ]},
             "animation_in": "fadeIn", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "conclusion", "template": "conclusion", "duration": 5,
             "data": {"title": "The Verdict", "text": f"Both are incredible creatures. The winner depends on what you value most.",
                      },
             "animation_in": "fadeIn", "animation_out": "fadeIn", "anim_in_duration": 0.8, "anim_out_duration": 0.5}
        ]
    else:
        scenes = [
            {"id": "intro", "template": "title", "duration": 4,
             "data": {"title": clean_topic.title(), "subtitle": "Everything you need to know"},
             "animation_in": "fadeIn", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "ch1", "template": "chapter_title", "duration": 3,
             "data": {"title": "Introduction", "number": "1"},
             "animation_in": "slideInLeft", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "fact1", "template": "fact", "duration": 5,
             "data": {"number": "01", "text": f"Let's explore the fascinating world of {clean_topic}"},
             "animation_in": "slideInLeft", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "ch2", "template": "chapter_title", "duration": 3,
             "data": {"title": "Key Facts", "number": "2"},
             "animation_in": "slideInRight", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "fact2", "template": "fact", "duration": 5,
             "data": {"number": "02", "text": f"There is so much to discover about {clean_topic}"},
             "animation_in": "slideUp", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "stats", "template": "statistics", "duration": 6,
             "data": {"title": "Key Metrics",
                      "items": [
                          {"label": "Importance", "value": 95, "max": 100, "unit": "%", "color": "primary"},
                          {"label": "Complexity", "value": 78, "max": 100, "unit": "%", "color": "secondary"},
                          {"label": "Interest", "value": 88, "max": 100, "unit": "%", "color": "accent"}
                      ]},
             "animation_in": "fadeIn", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "fact3", "template": "fact", "duration": 5,
             "data": {"number": "03", "text": f"The story of {clean_topic} continues to evolve"},
             "animation_in": "slideInLeft", "animation_out": "fadeOut", "anim_in_duration": 0.5, "anim_out_duration": 0.5},
            {"id": "conclusion", "template": "conclusion", "duration": 5,
             "data": {"title": "Summary", "text": f"That's everything about {clean_topic}!",
                      },
             "animation_in": "fadeIn", "animation_out": "fadeIn", "anim_in_duration": 0.8, "anim_out_duration": 0.5}
        ]

    scene_data = {
        "video": {
            "title": clean_topic.title(),
            "width": width,
            "height": height,
            "fps": 30
        },
        "scenes": scenes
    }

    return scene_data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_generator.py <topic> [--duration 60] [--output scenes.json]")
        sys.exit(1)

    topic = sys.argv[1]
    duration = 60
    output = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--duration" and i + 1 < len(sys.argv):
            duration = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    data = generate_script(topic, duration=duration, output_path=output)
    if data and not output:
        print(json.dumps(data, indent=2))
