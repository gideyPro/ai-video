#!/usr/bin/env python3
"""Professional template rendering functions for YouTube-quality video output."""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import os
import random

# =================== FONT PATHS ===================

FONTS_DIR = "/data/data/com.termux/files/usr/share/fonts/TTF"
FONT_PATH_REGULAR = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
FONT_PATH_BOLD = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
FONT_PATH_MONO = os.path.join(FONTS_DIR, "DejaVuSansMono.ttf")

# =================== CONFIG INJECTION ===================

_CURRENT_CONFIG = {}

def set_config(cfg):
    global _CURRENT_CONFIG
    _CURRENT_CONFIG = cfg

def get_font(size, bold=False, mono=False):
    global _CURRENT_CONFIG
    fonts = _CURRENT_CONFIG.get("fonts", {})
    font_path = FONT_PATH_REGULAR
    if bold:
        font_path = fonts.get("bold", FONT_PATH_BOLD)
    elif mono:
        font_path = fonts.get("mono", FONT_PATH_MONO)
    else:
        font_path = fonts.get("regular", FONT_PATH_REGULAR)
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        try:
            return ImageFont.truetype(FONT_PATH_REGULAR, size)
        except Exception:
            return ImageFont.load_default()

# =================== FALLBACK COLORS ===================

COLORS = {
    "background": (10, 10, 10),
    "primary": (79, 195, 247),
    "secondary": (255, 112, 67),
    "accent": (102, 187, 106),
    "text": (255, 255, 255),
    "text_dim": (170, 170, 170),
    "card_bg": (26, 26, 46),
}

# =================== COLOR UTILITIES ===================

def parse_color(color_str):
    if not color_str:
        return (255, 255, 255)
    if isinstance(color_str, (list, tuple)):
        return tuple(color_str[:3])
    try:
        color_str = color_str.lstrip("#")
        if len(color_str) == 6:
            return (int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16))
    except Exception:
        pass
    return (255, 255, 255)

def _clamp(v):
    return max(0, min(255, int(v)))

def tint(color, factor=0.3):
    return tuple(_clamp(c + (255 - c) * factor) for c in color[:3])

def shade(color, factor=0.4):
    return tuple(_clamp(c * (1 - factor)) for c in color[:3])

def with_alpha(color, alpha):
    return (color[0], color[1], color[2], _clamp(alpha))

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(_clamp(c1[i] * (1 - t) + c2[i] * t) for i in range(3))

def get_palette(config):
    colors = config.get("colors", {})
    primary = parse_color(colors.get("primary", "#4fc3f7"))
    grad_start = parse_color(colors.get("gradient_start", "#0f0c29"))
    grad_end = parse_color(colors.get("gradient_end", "#302b63"))
    return {
        "primary": primary,
        "primary_light": tint(primary, 0.4),
        "primary_dark": shade(primary, 0.5),
        "primary_muted": shade(primary, 0.3),
        "grad_start": grad_start,
        "grad_end": grad_end,
        "surface": shade(grad_end, 0.3),
        "text": (240, 240, 245),
        "text_secondary": (180, 180, 190),
        "text_dim": (120, 120, 130),
        "shadow": shade(grad_start, 0.7),
    }

# =================== LAYOUT ===================

def _safe(w, h):
    return int(w * 0.0625), int(h * 0.11)

def _scale(value, h, base=1080):
    return max(1, int(value * h / base))

# =================== TEXT UTILITIES ===================

def text_bbox(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def _wrap_text(draw, text, font, max_width):
    if not text:
        return []
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        tw, _ = text_bbox(draw, test, font)
        if tw > max_width and current:
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    return lines

def _draw_text_shadow(draw, pos, text, font, color, shadow_color=None, offset=3):
    if shadow_color is None:
        shadow_color = (0, 0, 0, 120)
    x, y = pos
    draw.text((x + offset, y + offset), text, fill=shadow_color, font=font)
    draw.text((x, y), text, fill=color, font=font)

def _draw_text_block(draw, lines, x, y, font, color, line_spacing, progress=1.0, stagger=0.08):
    for i, line in enumerate(lines):
        line_alpha = _ease_alpha(progress, i * stagger)
        if line_alpha <= 0:
            continue
        c = with_alpha(color[:3], line_alpha)
        sc = (0, 0, 0, max(0, line_alpha // 2))
        _draw_text_shadow(draw, (x, y + i * line_spacing), line, font, c, sc, offset=2)

# =================== EASING ===================

def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3

def ease_out_quart(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 4

def ease_in_out_cubic(t):
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - ((-2 * t + 2) ** 3) / 2

def ease_out_back(t):
    t = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * ((t - 1) ** 3) + c1 * ((t - 1) ** 2)

def ease_out_simple(t):
    return 1 - (1 - min(t, 1)) ** 3

def _ease_alpha(progress, delay=0.0):
    t = max(0.0, min(1.0, (progress - delay) * 2.5))
    return int(ease_out_cubic(t) * 255)

# =================== DRAWING PRIMITIVES ===================

def draw_rounded_rect(draw, xy, radius, fill, outline=None, width=2):
    x0, y0, x1, y1 = [int(v) for v in xy]
    if x1 <= x0 or y1 <= y0:
        return
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    r = max(0, r)
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.pieslice([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=fill)
    draw.pieslice([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=fill)
    if outline:
        draw.arc([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=outline, width=width)
        draw.arc([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=outline, width=width)
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)

def draw_glass_panel(img, draw, xy, radius, fill, outline=None, shadow_alpha=80, blur_radius=12):
    x0, y0, x1, y1 = [int(v) for v in xy]
    w, h = img.size
    if shadow_alpha > 0:
        shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow_layer)
        draw_rounded_rect(s_draw, (x0+4, y0+8, x1+4, y1+8), radius, (0, 0, 0, shadow_alpha))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur_radius))
        img.paste(shadow_layer, (0, 0), shadow_layer)
    if len(fill) == 4 and fill[3] < 255:
        try:
            box = (max(0, x0), max(0, y0), min(w, x1), min(h, y1))
            if box[2] > box[0] and box[3] > box[1]:
                bg_crop = img.crop(box).filter(ImageFilter.GaussianBlur(18))
                mask = Image.new("L", (box[2]-box[0], box[3]-box[1]), 0)
                m_draw = ImageDraw.Draw(mask)
                draw_rounded_rect(m_draw, (0, 0, box[2]-box[0], box[3]-box[1]), radius, 255)
                img.paste(bg_crop, box, mask)
        except Exception:
            pass
    panel_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(panel_layer)
    draw_rounded_rect(p_draw, xy, radius, fill, outline, width=2)
    img.paste(panel_layer, (0, 0), panel_layer)

def draw_accent_line(draw, x, y, length, thickness, color, progress=1.0):
    animated_len = int(length * ease_out_cubic(min(progress * 1.5, 1.0)))
    if animated_len > 0:
        draw.rectangle([x, y, x + animated_len, y + thickness], fill=color)

def draw_bar(draw, x, y, width, height, progress_val, color, bg_color=(35, 35, 45)):
    draw_rounded_rect(draw, (x, y, x + width, y + height), height // 2, bg_color)
    fill_w = max(height, int(width * progress_val))
    if fill_w > 0:
        draw_rounded_rect(draw, (x, y, x + fill_w, y + height), height // 2, color)
        highlight = tint(color, 0.3)
        draw_rounded_rect(draw, (x, y, x + fill_w, y + height // 2), height // 2, with_alpha(highlight, 60))

def load_image_fit(image_path, max_w, max_h, zoom=1.0):
    try:
        img = Image.open(image_path).convert("RGBA")
        img_ratio = img.width / max(1, img.height)
        target_ratio = max_w / max(1, max_h)
        if img_ratio > target_ratio:
            new_h = int(max_h * zoom)
            new_w = int(new_h * img_ratio)
        else:
            new_w = int(max_w * zoom)
            new_h = int(new_w / img_ratio)
        img = img.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)
        canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
        ox = (max_w - img.width) // 2
        oy = (max_h - img.height) // 2
        canvas.paste(img, (ox, oy), img)
        return canvas
    except Exception:
        placeholder = Image.new("RGBA", (max_w, max_h), (30, 30, 35, 255))
        d = ImageDraw.Draw(placeholder)
        f = get_font(24)
        d.text((max_w // 2, max_h // 2), "No Image", fill=(100, 100, 110), font=f, anchor="mm")
        return placeholder

def draw_gradient_text(img, text, position, font, color_start, color_end, alpha=255):
    color_start = parse_color(color_start)
    color_end = parse_color(color_end)
    w, h = img.size
    txt_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    t_draw = ImageDraw.Draw(txt_layer)
    t_draw.text(position, text, fill=(255, 255, 255, 255), font=font)
    bbox = t_draw.textbbox(position, text, font=font)
    tw = max(bbox[2] - bbox[0], 1)
    grad_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grad_layer)
    for x in range(bbox[0], bbox[2]):
        t = (x - bbox[0]) / tw
        r = _clamp(color_start[0] * (1 - t) + color_end[0] * t)
        g = _clamp(color_start[1] * (1 - t) + color_end[1] * t)
        b = _clamp(color_start[2] * (1 - t) + color_end[2] * t)
        g_draw.line([(x, bbox[1]), (x, bbox[3])], fill=(r, g, b, alpha))
    txt_layer.paste(grad_layer, (0, 0), txt_layer)
    img.paste(txt_layer, (0, 0), txt_layer)

# =================== TEMPLATE FUNCTIONS ===================

def render_title(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    title = data.get("title", "Untitled")
    subtitle = data.get("subtitle", "")
    font_title = get_font(_scale(78, h), bold=True)
    font_sub = get_font(_scale(36, h))
    max_title_w = w - sx * 2
    title_lines = _wrap_text(draw, title, font_title, max_title_w)
    line_h = _scale(95, h)
    total_title_h = len(title_lines) * line_h
    sub_h = _scale(50, h) if subtitle else 0
    accent_h = _scale(20, h)
    total_block = total_title_h + accent_h + sub_h
    start_y = (h - total_block) // 2
    title_alpha = _ease_alpha(progress, 0.0)
    sub_alpha = _ease_alpha(progress, 0.15)
    line_alpha = _ease_alpha(progress, 0.1)
    for i, line in enumerate(title_lines):
        tw, _ = text_bbox(draw, line, font_title)
        tx = (w - tw) // 2
        ty = start_y + i * line_h
        draw.text((tx + 3, ty + 4), line, fill=(0, 0, 0, title_alpha // 3), font=font_title)
        draw_gradient_text(img, line, (tx, ty), font_title, pal["primary"], pal["primary_light"], title_alpha)
    accent_y = start_y + total_title_h + _scale(8, h)
    accent_w = min(max_title_w // 2, _scale(400, h))
    draw_accent_line(draw, (w - accent_w) // 2, accent_y, accent_w, _scale(4, h), with_alpha(pal["primary"], line_alpha), progress)
    if subtitle:
        sub_lines = _wrap_text(draw, subtitle, font_sub, max_title_w - _scale(200, h))
        sub_start = accent_y + _scale(20, h)
        for i, line in enumerate(sub_lines):
            sw, _ = text_bbox(draw, line, font_sub)
            _draw_text_shadow(draw, ((w - sw) // 2, sub_start + i * _scale(48, h)), line, font_sub, with_alpha(pal["text_secondary"], sub_alpha), (0, 0, 0, sub_alpha // 3), offset=2)
    return img

def render_comparison(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    font_title = get_font(_scale(46, h), bold=True)
    font_sub = get_font(_scale(28, h))
    font_vs = get_font(_scale(52, h), bold=True)
    mid_x = w // 2
    gap = _scale(30, h)
    panel_w = mid_x - sx - gap
    for idx, side in enumerate(["left", "right"]):
        d = data.get(side, {})
        title = d.get("title", "")
        image = d.get("image", "")
        sub = d.get("subtitle", d.get("text", ""))
        panel_x = sx if side == "left" else mid_x + gap
        delay = 0.0 if side == "left" else 0.12
        panel_progress = ease_out_quart(max(0, min(1, (progress - delay) * 2.0)))
        alpha = _ease_alpha(progress, delay)
        slide_x = int((1 - panel_progress) * (150 if side == "left" else -150))
        px = panel_x + slide_x
        draw_glass_panel(img, draw, (px, sy, px + panel_w, h - sy), _scale(16, h), with_alpha(pal["surface"], int(alpha * 0.75)), outline=with_alpha(pal["primary_dark"], alpha // 3))
        content_y = sy + _scale(30, h)
        if image and os.path.exists(image):
            img_h = h // 2 - sy
            kb_zoom = 1.0 + 0.06 * progress
            img_asset = load_image_fit(image, panel_w - _scale(40, h), img_h, zoom=kb_zoom)
            img.paste(img_asset, (px + _scale(20, h), content_y), img_asset)
            content_y += img_h + _scale(20, h)
        if title:
            tw, _ = text_bbox(draw, title, font_title)
            tx = px + (panel_w - tw) // 2
            _draw_text_shadow(draw, (tx, content_y), title, font_title, with_alpha((255, 255, 255), alpha), offset=2)
            content_y += _scale(55, h)
        if sub:
            sub_lines = _wrap_text(draw, sub, font_sub, panel_w - _scale(60, h))
            for i, line in enumerate(sub_lines[:6]):
                la = _ease_alpha(progress, delay + 0.1 + i * 0.05)
                draw.text((px + _scale(30, h), content_y + i * _scale(38, h)), line, fill=with_alpha(pal["text_secondary"], la), font=font_sub)
    vs_alpha = _ease_alpha(progress, 0.2)
    vs_size = _scale(70, h)
    draw.ellipse([mid_x - vs_size, h // 2 - vs_size, mid_x + vs_size, h // 2 + vs_size], fill=with_alpha(pal["primary_dark"], vs_alpha))
    draw.ellipse([mid_x - vs_size + 4, h // 2 - vs_size + 4, mid_x + vs_size - 4, h // 2 + vs_size - 4], fill=with_alpha(shade(pal["grad_start"], 0.2), vs_alpha))
    vs_text = data.get("vs_text", "VS")
    vtw, _ = text_bbox(draw, vs_text, font_vs)
    draw.text((mid_x - vtw // 2, h // 2 - _scale(22, h)), vs_text, fill=with_alpha(pal["primary_light"], vs_alpha), font=font_vs)
    return img

def render_image_text(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    image = data.get("image", "")
    title = data.get("title", "")
    text = data.get("text", "")
    layout = data.get("layout", "right")
    font_title = get_font(_scale(46, h), bold=True)
    font_text = get_font(_scale(28, h))
    content_w = w // 2 - sx - _scale(20, h)
    if layout == "right":
        text_x, img_x = sx, w // 2 + _scale(20, h)
    else:
        text_x, img_x = w // 2 + _scale(20, h), sx
    if image and os.path.exists(image):
        kb_zoom = 1.0 + 0.06 * progress
        img_asset = load_image_fit(image, content_w, h - sy * 2, zoom=kb_zoom)
        ia = _ease_alpha(progress, 0.0)
        if ia > 0:
            mask = Image.new("L", img_asset.size, ia)
            img.paste(img_asset, (img_x, sy), mask)
    slide_progress = ease_out_quart(max(0, min(1, progress * 1.8)))
    offset = int((1 - slide_progress) * _scale(60, h))
    text_alpha = _ease_alpha(progress, 0.1)
    tx = text_x + (offset if layout == "left" else -offset)
    cy = sy + _scale(20, h)
    if title:
        title_lines = _wrap_text(draw, title, font_title, content_w)
        for i, line in enumerate(title_lines):
            la = _ease_alpha(progress, 0.05 + i * 0.04)
            _draw_text_shadow(draw, (tx, cy), line, font_title, with_alpha((255, 255, 255), la), offset=2)
            cy += _scale(58, h)
        draw_accent_line(draw, tx, cy, _scale(80, h), _scale(3, h), with_alpha(pal["primary"], text_alpha), progress)
        cy += _scale(25, h)
    if text:
        lines = _wrap_text(draw, text, font_text, content_w)
        _draw_text_block(draw, lines, tx, cy, font_text, pal["text_secondary"], _scale(40, h), progress, stagger=0.06)
    return img

def render_statistics(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    items = data.get("items", [])
    title = data.get("title", "Statistics")
    font_title = get_font(_scale(46, h), bold=True)
    font_label = get_font(_scale(28, h))
    font_value = get_font(_scale(36, h), bold=True)
    title_alpha = _ease_alpha(progress, 0.0)
    tw, _ = text_bbox(draw, title, font_title)
    _draw_text_shadow(draw, ((w - tw) // 2, sy), title, font_title, with_alpha((255, 255, 255), title_alpha), offset=2)
    draw_accent_line(draw, (w - tw) // 2, sy + _scale(55, h), tw, _scale(3, h), with_alpha(pal["primary"], title_alpha), progress)
    y_start = sy + _scale(90, h)
    available_h = h - y_start - sy
    item_h = min(_scale(95, h), available_h // max(len(items), 1))
    bar_colors = [pal["primary"], pal["primary_light"], COLORS["accent"], COLORS["secondary"], tint(pal["primary"], 0.2)]
    for i, item in enumerate(items):
        delay = 0.08 + i * 0.1
        item_progress = max(0.0, min(1.0, (progress - delay) * 3.0))
        if item_progress <= 0:
            continue
        alpha = _ease_alpha(progress, delay)
        y = y_start + i * item_h
        label = item.get("label", "")
        value = item.get("value", 0)
        max_val = item.get("max", 100)
        unit = item.get("unit", "")
        c = bar_colors[i % len(bar_colors)]
        draw.text((sx, y + _scale(5, h)), label, fill=with_alpha(pal["text_secondary"], alpha), font=font_label)
        bar_x = sx + _scale(280, h)
        bar_w = w - bar_x - sx - _scale(130, h)
        bar_y = y + _scale(35, h)
        bar_h = _scale(22, h)
        value_ratio = min(1.0, value / max_val) if max_val > 0 else 0
        animated_ratio = value_ratio * ease_out_cubic(item_progress)
        draw_bar(draw, bar_x, bar_y, bar_w, bar_h, animated_ratio, c)
        display_val = int(value * ease_out_cubic(item_progress))
        val_text = f"{display_val}{unit}"
        vtw, _ = text_bbox(draw, val_text, font_value)
        draw.text((w - sx - vtw, y + _scale(2, h)), val_text, fill=with_alpha((255, 255, 255), alpha), font=font_value)
    return img

def render_ranking(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    items = data.get("items", [])
    title = data.get("title", "Ranking")
    font_title = get_font(_scale(46, h), bold=True)
    font_rank = get_font(_scale(38, h), bold=True)
    font_name = get_font(_scale(30, h))
    font_detail = get_font(_scale(24, h))
    ta = _ease_alpha(progress, 0.0)
    tw, _ = text_bbox(draw, title, font_title)
    _draw_text_shadow(draw, ((w - tw) // 2, sy), title, font_title, with_alpha((255, 255, 255), ta), offset=2)
    y_start = sy + _scale(80, h)
    available = h - y_start - sy
    row_h = min(_scale(90, h), available // max(len(items), 1))
    rank_colors = [pal["primary"], pal["primary_light"], COLORS["accent"]] + [pal["text_dim"]] * 20
    for i, item in enumerate(items):
        delay = 0.08 + i * 0.08
        ip = max(0, min(1, (progress - delay) * 2.5))
        if ip <= 0:
            continue
        alpha = _ease_alpha(progress, delay)
        slide_x = int((1 - ease_out_quart(ip)) * _scale(200, h))
        y = y_start + i * row_h
        draw_glass_panel(img, draw, (sx + slide_x, y, w - sx + slide_x, y + row_h - _scale(8, h)), _scale(10, h), with_alpha(pal["surface"], int(alpha * 0.65)))
        rc = rank_colors[min(i, len(rank_colors) - 1)]
        circle_r = _scale(26, h)
        cx_pos = sx + slide_x + _scale(40, h)
        cy_pos = y + row_h // 2
        draw.ellipse([cx_pos - circle_r, cy_pos - circle_r, cx_pos + circle_r, cy_pos + circle_r], fill=with_alpha(rc, alpha))
        rank_text = str(i + 1)
        rtw, _ = text_bbox(draw, rank_text, font_rank)
        draw.text((cx_pos - rtw // 2, cy_pos - _scale(16, h)), rank_text, fill=with_alpha((255, 255, 255), alpha), font=font_rank)
        name = item.get("name", item.get("title", ""))
        draw.text((sx + slide_x + _scale(90, h), y + (row_h - _scale(30, h)) // 2), name, fill=with_alpha((255, 255, 255), alpha), font=font_name)
        detail = item.get("detail", item.get("subtitle", ""))
        if detail:
            dtw, _ = text_bbox(draw, detail, font_detail)
            draw.text((w - sx + slide_x - dtw - _scale(20, h), y + (row_h - _scale(24, h)) // 2), detail, fill=with_alpha(pal["text_dim"], alpha), font=font_detail)
    return img

def render_chapter_title(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    title = data.get("title", "")
    number = data.get("number", "")
    font_title = get_font(_scale(48, h), bold=True)
    center_y = h // 2
    alpha = _ease_alpha(progress, 0.0)
    if number:
        scale = ease_out_cubic(min(progress * 2, 1.0))
        fs = _scale(int(120 * (0.6 + 0.4 * scale)), h)
        fn = get_font(fs, bold=True)
        nw, nh = text_bbox(draw, str(number), fn)
        nx = (w - nw) // 2
        ny = center_y - nh - _scale(30, h)
        draw.text((nx + 3, ny + 4), str(number), fill=(0, 0, 0, alpha // 4), font=fn)
        draw.text((nx, ny), str(number), fill=with_alpha(pal["primary"], alpha), font=fn)
    if title:
        title_lines = _wrap_text(draw, title, font_title, w - _safe(w, h)[0] * 2)
        ty_start = center_y + _scale(15, h) if number else center_y - _scale(25, h)
        for i, line in enumerate(title_lines):
            la = _ease_alpha(progress, 0.1 + i * 0.05)
            tw, _ = text_bbox(draw, line, font_title)
            _draw_text_shadow(draw, ((w - tw) // 2, ty_start + i * _scale(60, h)), line, font_title, with_alpha((255, 255, 255), la), offset=2)
        accent_y = ty_start + len(title_lines) * _scale(60, h) + _scale(15, h)
        draw_accent_line(draw, (w - _scale(250, h)) // 2, accent_y, _scale(250, h), _scale(4, h), with_alpha(pal["primary"], alpha), progress)
    return img

def render_timeline(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    events = data.get("events", [])
    title = data.get("title", "Timeline")
    font_title = get_font(_scale(42, h), bold=True)
    font_year = get_font(_scale(26, h), bold=True)
    font_desc = get_font(_scale(22, h))
    ta = _ease_alpha(progress, 0.0)
    tw, _ = text_bbox(draw, title, font_title)
    _draw_text_shadow(draw, ((w - tw) // 2, sy), title, font_title, with_alpha((255, 255, 255), ta), offset=2)
    if not events:
        return img
    line_y = h // 2
    margin = sx + _scale(40, h)
    line_w = w - margin * 2
    line_prog = ease_out_cubic(min(progress * 2, 1.0))
    current_w = int(line_w * line_prog)
    if current_w > 0:
        draw.rectangle([margin, line_y - 1, margin + current_w, line_y + 2], fill=with_alpha(pal["primary_dark"], ta))
    for i, event in enumerate(events):
        delay = 0.1 + i * 0.12
        ep = max(0, min(1, (progress - delay) * 2.5))
        if ep <= 0:
            continue
        alpha = _ease_alpha(progress, delay)
        n = max(len(events) - 1, 1)
        x = margin + int(line_w * (i / n))
        dot_r = _scale(8, h)
        draw.ellipse([x - dot_r, line_y - dot_r, x + dot_r, line_y + dot_r], fill=with_alpha(pal["primary"], alpha))
        ring_r = dot_r + _scale(4, h)
        draw.ellipse([x - ring_r, line_y - ring_r, x + ring_r, line_y + ring_r], outline=with_alpha(pal["primary_dark"], alpha // 2), width=2)
        above = i % 2 == 0
        year = str(event.get("year", event.get("date", "")))
        desc = event.get("description", event.get("text", ""))
        connector_h = _scale(40, h)
        if above:
            draw.line([(x, line_y - dot_r), (x, line_y - connector_h)], fill=with_alpha(pal["primary_dark"], alpha // 2), width=2)
        else:
            draw.line([(x, line_y + dot_r), (x, line_y + connector_h)], fill=with_alpha(pal["primary_dark"], alpha // 2), width=2)
        card_w = _scale(220, h)
        card_h = _scale(90, h)
        if above:
            card_y = line_y - connector_h - card_h
        else:
            card_y = line_y + connector_h
        card_x = x - card_w // 2
        card_x = max(sx, min(card_x, w - sx - card_w))
        draw_glass_panel(img, draw, (card_x, card_y, card_x + card_w, card_y + card_h), _scale(8, h), with_alpha(pal["surface"], int(alpha * 0.6)), shadow_alpha=40)
        draw.text((card_x + _scale(12, h), card_y + _scale(10, h)), year, fill=with_alpha(pal["primary_light"], alpha), font=font_year)
        desc_lines = _wrap_text(draw, desc, font_desc, card_w - _scale(24, h))
        for j, dl in enumerate(desc_lines[:2]):
            draw.text((card_x + _scale(12, h), card_y + _scale(38, h) + j * _scale(26, h)), dl, fill=with_alpha(pal["text_secondary"], alpha), font=font_desc)
    return img

def render_quote(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    text = data.get("text", "")
    author = data.get("author", "")
    font_quote_mark = get_font(_scale(180, h), bold=True)
    font_text = get_font(_scale(42, h))
    font_author = get_font(_scale(30, h), bold=True)
    max_text_w = w - sx * 2 - _scale(160, h)
    
    panel_alpha = _ease_alpha(progress, 0.05)
    text_lines = _wrap_text(draw, text, font_text, max_text_w)
    line_h = _scale(56, h)
    block_h = len(text_lines) * line_h + _scale(80, h)
    panel_pad = _scale(40, h)
    panel_top = (h - block_h) // 2 - panel_pad
    panel_bot = panel_top + block_h + panel_pad * 2
    panel_left = sx + _scale(60, h)
    panel_right = w - sx - _scale(60, h)

    # 1. Draw glass panel backdrop first (restoring original glassish look: alpha 0.5, no dark outline)
    draw_glass_panel(img, draw, (panel_left, panel_top, panel_right, panel_bot), _scale(16, h), with_alpha(pal["surface"], int(panel_alpha * 0.5)), shadow_alpha=50)
    
    draw = ImageDraw.Draw(img) # Refresh handle

    # 2. Draw single quotation mark on the left on top of the rectangle
    qm_alpha = _ease_alpha(progress, 0.0)
    # Position properly relative to the top-left of the panel
    qx = panel_left - _scale(10, h)
    qy = panel_top - _scale(40, h)
    draw.text((qx, qy), "\u201C", font=font_quote_mark, fill=with_alpha(pal["primary"], int(qm_alpha * 0.6)))

    # 3. Draw quote text
    text_start_y = (h - block_h) // 2
    for i, line in enumerate(text_lines):
        la = _ease_alpha(progress, 0.1 + i * 0.05)
        lw, _ = text_bbox(draw, line, font_text)
        draw.text(((w - lw) // 2, text_start_y + i * line_h), line, fill=with_alpha(pal["text"], la), font=font_text)
        
    # 4. Draw author
    if author:
        author_alpha = _ease_alpha(progress, 0.25)
        aw, _ = text_bbox(draw, author, font_author)
        draw.text(((w - aw) // 2, text_start_y + len(text_lines) * line_h + _scale(25, h)), author, fill=with_alpha(pal["primary"], author_alpha), font=font_author)
        
    return img

def render_news_flash(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    headline = data.get("headline", "BREAKING NEWS")
    subtext = data.get("subtext", "")
    bg_img = data.get("image")
    if bg_img and os.path.exists(bg_img):
        try:
            bimg = load_image_fit(bg_img, w, h, zoom=1.0 + 0.04 * progress)
            img.paste(bimg, (0, 0))
        except Exception:
            pass
    font_head = get_font(_scale(56, h), bold=True)
    font_sub = get_font(_scale(32, h))
    font_tag = get_font(_scale(24, h), bold=True)
    alpha = _ease_alpha(progress, 0.0)
    bar_top = h - _scale(200, h)
    bar_mid = h - _scale(120, h)
    bar_bot = h - _scale(50, h)
    headline_panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hp_draw = ImageDraw.Draw(headline_panel)
    hp_draw.rectangle([0, bar_top, w, bar_mid], fill=(180, 20, 20, int(alpha * 0.92)))
    img.paste(headline_panel, (0, 0), headline_panel)
    ticker_panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tp_draw = ImageDraw.Draw(ticker_panel)
    tp_draw.rectangle([0, bar_mid, w, bar_bot], fill=(245, 245, 245, int(alpha * 0.95)))
    img.paste(ticker_panel, (0, 0), ticker_panel)
    tag_w = _scale(180, h)
    draw.rectangle([0, bar_mid, tag_w, bar_bot], fill=with_alpha((180, 20, 20), alpha))
    draw.text((_scale(15, h), bar_mid + _scale(12, h)), "LIVE", fill=with_alpha((255, 255, 255), alpha), font=font_tag)
    head_lines = _wrap_text(draw, headline.upper(), font_head, w - _scale(200, h))
    for i, hl in enumerate(head_lines[:2]):
        draw.text((_scale(100, h), bar_top + _scale(12, h) + i * _scale(60, h)), hl, fill=with_alpha((255, 255, 255), alpha), font=font_head)
    if subtext:
        ticker_progress = ease_in_out_cubic(progress)
        stw, _ = text_bbox(draw, subtext, font_sub)
        x_offset = int(w - ticker_progress * (w + stw + _scale(200, h)))
        x_offset = max(-stw, x_offset)
        draw.text((tag_w + _scale(20, h) + max(0, x_offset), bar_mid + _scale(14, h)), subtext, fill=with_alpha((30, 30, 30), alpha), font=font_sub)
    return img



def render_dynamic_captions(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    text = data.get("text", "Default Caption")
    
    font_cap = get_font(_scale(90, h), bold=True)
    words = text.split()
    
    current_word_idx = min(len(words) - 1, int(progress * len(words) * 1.2))
    
    total_w = 0
    word_boxes = []
    space_w, _ = text_bbox(draw, " ", font_cap)
    for word in words:
        ww, wh = text_bbox(draw, word, font_cap)
        word_boxes.append((word, ww, wh))
        total_w += ww + space_w
    
    total_w -= space_w
    
    lines = []
    current_line = []
    current_line_w = 0
    max_w = w - sx * 2
    
    for word, ww, wh in word_boxes:
        if current_line_w + ww > max_w and current_line:
            lines.append((current_line, current_line_w - space_w))
            current_line = [(word, ww, wh)]
            current_line_w = ww + space_w
        else:
            current_line.append((word, ww, wh))
            current_line_w += ww + space_w
            
    if current_line:
        lines.append((current_line, current_line_w - space_w))
        
    line_h = _scale(120, h)
    total_h = len(lines) * line_h
    start_y = (h - total_h) // 2
    
    word_count = 0
    for i, (line_words, line_w) in enumerate(lines):
        start_x = (w - line_w) // 2
        curr_x = start_x
        for word, ww, wh in line_words:
            is_active = (word_count == current_word_idx)
            is_past = (word_count < current_word_idx)
            
            y_offset = -_scale(10, h) if is_active else 0
            
            if is_active:
                color = pal.get("primary", (255, 200, 50))
                _draw_text_shadow(draw, (curr_x, start_y + i * line_h + y_offset), word, font_cap, color, (color[0], color[1], color[2], 100), offset=4)
            else:
                color = (255, 255, 255) if is_past else (150, 150, 150)
                _draw_text_shadow(draw, (curr_x, start_y + i * line_h + y_offset), word, font_cap, color, (0,0,0,150), offset=4)
                
            curr_x += ww + space_w
            word_count += 1
            
    return img

def render_social_post(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    sx, sy = _safe(w, h)
    
    username = data.get("username", "@user")
    handle = data.get("handle", "@user")
    content = data.get("text", "")
    likes = data.get("likes", "10.5K")
    
    font_user = get_font(_scale(36, h), bold=True)
    font_handle = get_font(_scale(28, h))
    font_content = get_font(_scale(42, h))
    font_stats = get_font(_scale(26, h))
    
    max_w = _scale(1000, h)
    lines = _wrap_text(draw, content, font_content, max_w - _scale(80, h))
    
    card_h = _scale(160, h) + len(lines) * _scale(55, h) + _scale(80, h)
    card_w = max_w
    
    scale = ease_out_back(min(1.0, progress * 2.0))
    if scale < 0.01:
        return img
        
    scaled_w = int(card_w * scale)
    scaled_h = int(card_h * scale)
    
    cx, cy = w // 2, h // 2
    px = cx - scaled_w // 2
    py = cy - scaled_h // 2
    
    alpha = _ease_alpha(progress, 0.0)
    draw_glass_panel(img, draw, (px, py, px + scaled_w, py + scaled_h), _scale(20, h), 
                     with_alpha(pal["surface"], int(alpha * 0.95)), shadow_alpha=80)
    
    if scale > 0.9:
        draw = ImageDraw.Draw(img)
        av_r = _scale(35, h)
        av_x = px + _scale(40, h)
        av_y = py + _scale(40, h)
        draw.ellipse([av_x, av_y, av_x + av_r*2, av_y + av_r*2], fill=pal["primary_dark"])
        
        draw.text((av_x + av_r*2 + _scale(20, h), av_y), username, font=font_user, fill=with_alpha((255,255,255), alpha))
        draw.text((av_x + av_r*2 + _scale(20, h), av_y + _scale(40, h)), handle, font=font_handle, fill=with_alpha(pal["text_secondary"], alpha))
        
        text_y = av_y + av_r*2 + _scale(40, h)
        for i, line in enumerate(lines):
            draw.text((px + _scale(40, h), text_y + i * _scale(55, h)), line, font=font_content, fill=with_alpha(pal["text"], alpha))
            
        action_y = py + scaled_h - _scale(60, h)
        draw.text((px + _scale(40, h), action_y), f"❤️ {likes} Likes", font=font_stats, fill=with_alpha(pal["text_secondary"], alpha))
        
    return img

def render_search_typing(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    query = data.get("query", "How to automate YouTube videos")
    
    font_search = get_font(_scale(46, h))
    
    bar_w = _scale(1200, h)
    bar_h = _scale(100, h)
    cx, cy = w // 2, h // 2
    
    slide_y = int((1 - ease_out_quart(min(1.0, progress * 2.0))) * _scale(100, h))
    px = cx - bar_w // 2
    py = cy - bar_h // 2 + slide_y
    
    alpha = _ease_alpha(progress, 0.0)
    
    draw_glass_panel(img, draw, (px, py, px + bar_w, py + bar_h), _scale(50, h), 
                     with_alpha((255, 255, 255), int(alpha * 0.9)), shadow_alpha=50)
    
    draw = ImageDraw.Draw(img)
    
    draw.text((px + _scale(30, h), py + _scale(25, h)), "🔍", font=get_font(_scale(35, h)), fill=with_alpha((100,100,100), alpha))
    
    typing_progress = max(0.0, min(1.0, (progress - 0.2) * 2.0))
    char_count = int(typing_progress * len(query))
    typed_text = query[:char_count]
    
    draw.text((px + _scale(90, h), py + _scale(25, h)), typed_text, font=font_search, fill=with_alpha((30,30,30), alpha))
    
    if char_count < len(query):
        cursor_blink = int(progress * 10) % 2 == 0
        if cursor_blink:
            tw, _ = text_bbox(draw, typed_text, font_search)
            draw.line([(px + _scale(95, h) + tw, py + _scale(20, h)), (px + _scale(95, h) + tw, py + bar_h - _scale(20, h))], 
                      fill=with_alpha((50,50,50), alpha), width=3)
                      
    return img

def render_lower_third(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    
    name = data.get("name", "John Doe")
    title = data.get("title", "Expert")
    
    font_name = get_font(_scale(50, h), bold=True)
    font_title = get_font(_scale(30, h))
    
    nw, nh = text_bbox(draw, name, font_name)
    tw, th = text_bbox(draw, title, font_title)
    
    box_w = max(nw, tw) + _scale(80, h)
    box_h = _scale(120, h)
    
    slide_x = int((ease_out_quart(min(1.0, progress * 3.0)) - 1.0) * box_w)
    
    px = _scale(100, h) + slide_x
    py = h - _scale(200, h)
    
    draw.rectangle([px, py, px + box_w, py + box_h], fill=with_alpha(pal["surface"], 220))
    draw.rectangle([px, py, px + _scale(15, h), py + box_h], fill=pal["primary"])
    
    draw.text((px + _scale(40, h), py + _scale(20, h)), name, font=font_name, fill=(255,255,255))
    draw.text((px + _scale(40, h), py + _scale(75, h)), title, font=font_title, fill=pal["primary_light"])
    
    return img

def render_call_to_action(img, draw, data, progress, config):
    w, h = img.size
    pal = get_palette(config)
    
    text = data.get("text", "SUBSCRIBE")
    font_cta = get_font(_scale(60, h), bold=True)
    
    tw, th = text_bbox(draw, text, font_cta)
    btn_w = tw + _scale(120, h)
    btn_h = _scale(120, h)
    
    cx, cy = w // 2, h // 2
    px = cx - btn_w // 2
    py = cy - btn_h // 2
    
    scale = ease_out_back(min(1.0, progress * 2.0))
    if scale < 0.01:
        return img
        
    scaled_w = int(btn_w * scale)
    scaled_h = int(btn_h * scale)
    sx = cx - scaled_w // 2
    sy = cy - scaled_h // 2
    
    draw_rounded_rect(draw, (sx, sy, sx + scaled_w, sy + scaled_h), _scale(60, h), (220, 40, 40))
    
    if scale > 0.9:
        draw.text((cx, cy - _scale(5, h)), text, font=font_cta, fill=(255,255,255), anchor="mm")
        
    return img


RENDERER_REGISTRY = {
    "title": render_title,
    "comparison": render_comparison,
    "image_text": render_image_text,
    "statistics": render_statistics,
    "ranking": render_ranking,
    "chapter_title": render_chapter_title,
    "timeline": render_timeline,
    "quote": render_quote,
    "news_flash": render_news_flash,
    "dynamic_captions": render_dynamic_captions,
    "social_post": render_social_post,
    "search_typing": render_search_typing,
    "lower_third": render_lower_third,
    "call_to_action": render_call_to_action
}

def render_template(template_name, img, draw, data, progress, config):
    renderer = RENDERER_REGISTRY.get(template_name)
    if renderer:
        return renderer(img, draw, data, progress, config)
    return img
