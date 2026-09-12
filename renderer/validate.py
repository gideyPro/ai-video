#!/usr/bin/env python3
"""Scene JSON validation for the video renderer engine."""

import json
import os
import sys

VALID_TEMPLATES = [
    "title", "comparison", "image_text", "statistics",
    "fact", "side_by_side", "ranking", "conclusion",
    "transition", "chapter_title", "timeline"
]

VALID_ANIMATIONS = [
    "fadeIn", "fadeOut", "slideInLeft", "slideInRight",
    "slideUp", "slideDown", "zoomIn", "zoomOut",
    "scale", "reveal", "countUp", "typewriter", "bounce",
    "none"
]

VALID_TRANSITIONS = [
    "fade", "slide_left", "slide_right", "slide_up",
    "slide_down", "zoom", "none", "dissolve", "wipe"
]


def validate_scene_json(data, project_dir=None):
    """Validate scene JSON structure. Returns (is_valid, errors)."""
    errors = []
    warnings = []

    if not isinstance(data, dict):
        return False, ["Root must be a JSON object"]

    if "video" not in data:
        errors.append("Missing 'video' object")
    else:
        v = data["video"]
        if "title" not in v:
            errors.append("video.title is required")
        if "width" not in v or "height" not in v:
            errors.append("video.width and video.height are required")
        elif v.get("width", 0) < 100 or v.get("height", 0) < 100:
            errors.append("video dimensions too small")
        if "fps" in v and v["fps"] not in (24, 25, 30, 60):
            warnings.append(f"Non-standard FPS: {v.get('fps')}")

    if "scenes" not in data:
        errors.append("Missing 'scenes' array")
    elif not isinstance(data["scenes"], list) or len(data["scenes"]) == 0:
        errors.append("'scenes' must be a non-empty array")
    else:
        scene_ids = set()
        for i, scene in enumerate(data["scenes"]):
            prefix = f"scenes[{i}]"
            if "id" not in scene:
                errors.append(f"{prefix}: missing 'id'")
            else:
                sid = scene["id"]
                if sid in scene_ids:
                    errors.append(f"{prefix}: duplicate scene id '{sid}'")
                scene_ids.add(sid)

            if "template" not in scene:
                errors.append(f"{prefix}: missing 'template'")
            elif scene["template"] not in VALID_TEMPLATES:
                errors.append(f"{prefix}: invalid template '{scene['template']}'. Valid: {VALID_TEMPLATES}")

            if "duration" not in scene:
                errors.append(f"{prefix}: missing 'duration'")
            elif not isinstance(scene["duration"], (int, float)) or scene["duration"] <= 0:
                errors.append(f"{prefix}: duration must be positive number")

            if "data" not in scene:
                errors.append(f"{prefix}: missing 'data' object")
            else:
                d = scene["data"]
                t = scene.get("template")
                _validate_template_data(prefix, t, d, errors, warnings, project_dir)

            if "animation_in" in scene and scene["animation_in"] not in VALID_ANIMATIONS:
                errors.append(f"{prefix}: invalid animation_in '{scene['animation_in']}'")
            if "animation_out" in scene and scene["animation_out"] not in VALID_ANIMATIONS:
                errors.append(f"{prefix}: invalid animation_out '{scene['animation_out']}'")
            if "transition" in scene and scene["transition"] not in VALID_TRANSITIONS:
                errors.append(f"{prefix}: invalid transition '{scene['transition']}'")

    is_valid = len(errors) == 0
    return is_valid, errors


def _validate_template_data(prefix, template, data, errors, warnings, project_dir=None):
    if template == "title":
        if "title" not in data:
            errors.append(f"{prefix} (title): missing 'title'")
    elif template == "comparison":
        if "left" not in data or "right" not in data:
            errors.append(f"{prefix} (comparison): needs 'left' and 'right'")
        else:
            for side in ["left", "right"]:
                s = data[side]
                if "title" not in s:
                    errors.append(f"{prefix} (comparison.{side}): missing 'title'")
                if "image" in s and project_dir:
                    img_path = os.path.join(project_dir, s["image"])
                    if not os.path.exists(img_path):
                        warnings.append(f"{prefix}: image not found: {s['image']}")
    elif template == "image_text":
        if "image" not in data:
            errors.append(f"{prefix} (image_text): missing 'image'")
        if "text" not in data and "title" not in data:
            errors.append(f"{prefix} (image_text): needs 'title' or 'text'")
    elif template == "statistics":
        if "items" not in data or not isinstance(data["items"], list):
            errors.append(f"{prefix} (statistics): missing 'items' array")
        else:
            for j, item in enumerate(data["items"]):
                if "label" not in item:
                    errors.append(f"{prefix} (statistics.items[{j}]): missing 'label'")
                if "value" not in item:
                    errors.append(f"{prefix} (statistics.items[{j}]): missing 'value'")
    elif template == "fact":
        if "text" not in data:
            errors.append(f"{prefix} (fact): missing 'text'")
    elif template == "side_by_side":
        if "left" not in data or "right" not in data:
            errors.append(f"{prefix} (side_by_side): needs 'left' and 'right'")
    elif template == "ranking":
        if "items" not in data or not isinstance(data["items"], list):
            errors.append(f"{prefix} (ranking): missing 'items' array")
    elif template == "conclusion":
        if "title" not in data and "text" not in data:
            errors.append(f"{prefix} (conclusion): needs 'title' or 'text'")
    elif template == "chapter_title":
        if "title" not in data:
            errors.append(f"{prefix} (chapter_title): missing 'title'")
    elif template == "timeline":
        if "events" not in data or not isinstance(data["events"], list):
            errors.append(f"{prefix} (timeline): missing 'events' array")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <scene.json>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    is_valid, errors = validate_scene_json(data)
    if is_valid:
        print("Scene JSON is valid.")
    else:
        print("Scene JSON has errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
