#!/usr/bin/env python3
"""Template rendering functions for the video renderer engine."""

from PIL import Image, ImageDraw, ImageFont
import math
import os


FONTS_DIR = "/data/data/com.termux/files/usr/share/fonts/TTF"
FONT_PATH_REGULAR = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
FONT_PATH_BOLD = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
FONT_PATH_MONO = os.path.join(FONTS_DIR, "DejaVuSansMono.ttf")

COLORS = {
    "background": (10, 10, 10),
    "primary": (79, 195, 247),
    "secondary": (255, 112, 67),
    "accent": (102, 187, 106),
    "text": (255, 255, 255),
    "text_dim": (170, 170, 170),
    "card_bg": (26, 26, 46),
    "gradient_start": (15, 12, 41),
    "gradient_end": (48, 43, 99),
}


def get_font(size, bold=False, mono=False):
    try:
        if mono:
            return ImageFont.truetype(FONT_PATH_MONO, size)
        if bold:
            return ImageFont.truetype(FONT_PATH_BOLD, size)
        return ImageFont.truetype(FONT_PATH_REGULAR, size)
    except Exception:
        return ImageFont.load_default()


def text_bbox(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_gradient_bg(img, color_start, color_end):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / h
        r = int(color_start[0] * (1 - t) + color_end[0] * t)
        g = int(color_start[1] * (1 - t) + color_end[1] * t)
        b = int(color_start[2] * (1 - t) + color_end[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def draw_rounded_rect(draw, xy, radius, fill, outline=None):
    x0, y0, x1, y1 = xy
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.pieslice([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=fill)
    draw.pieslice([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=fill)
    if outline:
        draw.arc([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=outline, width=2)
        draw.arc([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=outline, width=2)
        draw.arc([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=outline, width=2)
        draw.arc([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=outline, width=2)
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=2)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=2)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=2)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=2)


def draw_bar(draw, x, y, width, height, progress, color, bg_color=(40, 40, 40)):
    draw_rounded_rect(draw, (x, y, x + width, y + height), height // 2, bg_color)
    fill_w = max(height, int(width * progress))
    if fill_w > 0:
        draw_rounded_rect(draw, (x, y, x + fill_w, y + height), height // 2, color)


def load_image_fit(image_path, max_w, max_h):
    try:
        img = Image.open(image_path).convert("RGBA")
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
        ox = (max_w - img.width) // 2
        oy = (max_h - img.height) // 2
        canvas.paste(img, (ox, oy), img)
        return canvas
    except Exception:
        placeholder = Image.new("RGBA", (max_w, max_h), (40, 40, 40, 255))
        d = ImageDraw.Draw(placeholder)
        f = get_font(24)
        tw, th = text_bbox(d, "No Image", f)
        d.text(((max_w - tw) // 2, (max_h - th) // 2), "No Image", fill=(150, 150, 150), font=f)
        return placeholder


# =================== TEMPLATE FUNCTIONS ===================

def render_title(img, draw, data, progress, config):
    title = data.get("title", "Untitled")
    subtitle = data.get("subtitle", "")
    alpha = progress

    font_title = get_font(96, bold=True)
    font_sub = get_font(42)
    tw, th = text_bbox(draw, title, font_title)
    sw, sh = text_bbox(draw, subtitle, font_sub) if subtitle else (0, 0)

    cx, cy = img.width // 2, img.height // 2
    tx = int(cx - tw / 2)
    ty = int(cy - th / 2 - (sh + 20) if subtitle else cy - th / 2)
    a = int(alpha * 255)
    draw.text((tx, ty), title, fill=(255, 255, 255, a), font=font_title)

    if subtitle:
        sa = int(min(alpha * 3, 1.0) * 255)
        draw.text((cx - sw // 2, ty + th + 30), subtitle, fill=(79, 195, 247, sa), font=font_sub)

    line_w = int(tw * ease_out_simple(min(alpha * 1.5, 1.0)))
    if line_w > 0:
        ly = ty + th + 15 if not subtitle else ty - 15
        draw.rectangle([cx - line_w // 2, ly, cx + line_w // 2, ly + 4], fill=(79, 195, 247, a))
    return img


def ease_out_simple(t):
    return 1 - (1 - min(t, 1)) ** 3


def render_comparison(img, draw, data, progress, config):
    left = data.get("left", {})
    right = data.get("right", {})
    vs_text = data.get("vs_text", "VS")

    font_title = get_font(56, bold=True)
    font_vs = get_font(80, bold=True)
    font_sub = get_font(32)

    mid_x = img.width // 2
    split_margin = 40

    for side, x_start, anim_dir in [("left", split_margin, -1), ("right", mid_x + split_margin, 1)]:
        d = data.get(side, {})
        title = d.get("title", "")
        image = d.get("image", "")
        color = config.get("colors", {}).get(side, (255, 255, 255))

        panel_w = mid_x - split_margin * 2
        panel_x = x_start

        panel_progress = max(0, min(1, progress * 2 - (0.0 if side == "left" else 0.2)))
        offset_x = int(anim_dir * 200 * ease_out_simple(panel_progress))
        panel_alpha = int(min(panel_progress * 3, 1.0) * 255)

        draw_rounded_rect(draw, (panel_x + offset_x, 60, panel_x + panel_w + offset_x, img.height - 60),
                          20, (26, 26, 46, panel_alpha), outline=(color[0], color[1], color[2], min(panel_alpha, 100)))

        if image:
            img_asset = load_image_fit(image, panel_w - 40, img.height // 2)
            img.paste(img_asset, (panel_x + offset_x + 20, 100), img_asset)

        ty = img.height // 2 + 60
        tw, _ = text_bbox(draw, title, font_title)
        tx = panel_x + offset_x + (panel_w - tw) // 2
        draw.text((tx, ty), title, fill=(255, 255, 255, panel_alpha), font=font_title)

        if "subtitle" in d:
            stw, _ = text_bbox(draw, d["subtitle"], font_sub)
            stx = panel_x + offset_x + (panel_w - stw) // 2
            draw.text((stx, ty + 70), d["subtitle"], fill=(color[0], color[1], color[2], min(panel_alpha, 200)), font=font_sub)

    vs_progress = max(0, min(1, progress * 2 - 0.4))
    vs_alpha = int(min(vs_progress * 3, 1.0) * 255)
    vs_scale = 0.5 + 0.5 * ease_out_simple(vs_progress)
    vs_font_size = int(80 * vs_scale)
    vs_font = get_font(vs_font_size, bold=True)
    vtw, vth = text_bbox(draw, vs_text, vs_font)
    vsx = mid_x - vtw // 2
    vsy = img.height // 2 - vth // 2
    draw.text((vsx, vsy), vs_text, fill=(255, 112, 67, vs_alpha), font=vs_font)

    circle_r = int(vs_font_size * 0.8)
    draw.ellipse([mid_x - circle_r, img.height // 2 - circle_r,
                  mid_x + circle_r, img.height // 2 + circle_r],
                 outline=(255, 112, 67, min(vs_alpha, 150)), width=3)
    return img


def render_image_text(img, draw, data, progress, config):
    image = data.get("image", "")
    title = data.get("title", "")
    text = data.get("text", "")
    layout = data.get("layout", "right")

    font_title = get_font(52, bold=True)
    font_text = get_font(30)

    content_w = img.width // 2 - 80
    text_x = 80 if layout == "left" else img.width // 2 + 40
    img_x = 80 if layout == "right" else img.width // 2 + 40

    if image:
        img_asset = load_image_fit(image, content_w, img.height - 160)
        img.paste(img_asset, (img_x, 80), img_asset)

    slide_progress = ease_out_simple(progress)
    offset = int((1 - slide_progress) * 100)
    text_alpha = int(min(progress * 3, 1.0) * 255)

    if layout == "left":
        tx = text_x - offset
    else:
        tx = text_x + offset

    if title:
        draw.text((tx, 120), title, fill=(255, 255, 255, text_alpha), font=font_title)

    if text:
        ty = 200 if title else 120
        words = text.split()
        lines = []
        current = ""
        for w in words:
            test = (current + " " + w).strip()
            tw, _ = text_bbox(draw, test, font_text)
            if tw > content_w:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)
        for i, line in enumerate(lines[:12]):
            line_alpha = int(min(progress * 3 - i * 0.1, 1.0) * 255)
            line_alpha = max(0, min(255, line_alpha))
            draw.text((tx, ty + i * 42), line, fill=(200, 200, 200, line_alpha), font=font_text)

    return img


def render_statistics(img, draw, data, progress, config):
    items = data.get("items", [])
    title = data.get("title", "Statistics")

    font_title = get_font(52, bold=True)
    font_label = get_font(32)
    font_value = get_font(44, bold=True)

    tw, th = text_bbox(draw, title, font_title)
    draw.text(((img.width - tw) // 2, 60), title, fill=(255, 255, 255, int(progress * 255)), font=font_title)

    bar_color = tuple(config.get("colors", {}).get("primary", (79, 195, 247)))
    y_start = 160
    item_h = min(100, (img.height - 200) // max(len(items), 1))

    for i, item in enumerate(items):
        item_progress = max(0, min(1, progress * len(items) - i) / 1.5)
        if item_progress <= 0:
            continue

        label = item.get("label", "")
        value = item.get("value", 0)
        max_val = item.get("max", 100)
        unit = item.get("unit", "")
        color_name = item.get("color")
        c = COLORS.get(color_name, bar_color) if color_name else bar_color

        y = y_start + i * item_h
        alpha = int(min(item_progress * 3, 1.0) * 255)

        draw.text((100, y + 10), label, fill=(200, 200, 200, alpha), font=font_label)

        bar_x = 400
        bar_w = img.width - 600
        bar_y = y + 55
        bar_h = 28

        value_ratio = min(1.0, value / max_val) if max_val > 0 else 0
        animated_ratio = value_ratio * ease_out_simple(item_progress)
        val_text = f"{int(value * ease_out_simple(item_progress))}{unit}"
        draw.text((img.width - 150, y + 10), val_text, fill=(255, 255, 255, alpha), font=font_value)

        draw_bar(draw, bar_x, bar_y, bar_w, bar_h, animated_ratio, c)

    return img


def render_fact(img, draw, data, progress, config):
    text = data.get("text", "")
    number = data.get("number", "")
    icon = data.get("icon", "")
    color_name = data.get("color", "primary")
    color = COLORS.get(color_name, COLORS["primary"])

    font_number = get_font(120, bold=True)
    font_text = get_font(40)
    font_icon = get_font(60)

    alpha = int(progress * 255)

    if number:
        nw, nh = text_bbox(draw, str(number), font_number)
        draw.text(((img.width - nw) // 2, img.height // 2 - nh - 80),
                  str(number), fill=(color[0], color[1], color[2], alpha), font=font_number)

    if icon:
        iw, ih = text_bbox(draw, icon, font_icon)
        draw.text(((img.width - iw) // 2, img.height // 2 - 20),
                  icon, fill=(255, 255, 255, alpha), font=font_icon)

    lines = _wrap_text(draw, text, font_text, img.width - 200)
    total_h = len(lines) * 50
    start_y = img.height // 2 + 60 if not number else img.height // 2 + 40

    for i, line in enumerate(lines):
        line_progress = max(0, min(1, progress * len(lines) - i) / 1.5)
        line_alpha = int(min(line_progress * 3, 1.0) * 255)
        lw, _ = text_bbox(draw, line, font_text)
        draw.text(((img.width - lw) // 2, start_y + i * 50), line,
                  fill=(255, 255, 255, line_alpha), font=font_text)

    return img


def render_side_by_side(img, draw, data, progress, config):
    left = data.get("left", {})
    right = data.get("right", {})

    mid_x = img.width // 2
    margin = 30

    for side, x_start in [("left", margin), ("right", mid_x + margin)]:
        d = data.get(side, {})
        title = d.get("title", "")
        text = d.get("text", "")
        image = d.get("image", "")

        panel_w = mid_x - margin * 2
        panel_progress = max(0, min(1, progress * 2 - (0.0 if side == "left" else 0.2)))
        panel_alpha = int(min(panel_progress * 3, 1.0) * 255)

        draw_rounded_rect(draw, (x_start, 40, x_start + panel_w, img.height - 40),
                          16, (26, 26, 46, panel_alpha))

        if image:
            img_asset = load_image_fit(image, panel_w - 20, 300)
            img.paste(img_asset, (x_start + 10, 60), img_asset)

        font_title = get_font(36, bold=True)
        font_text = get_font(26)

        ty_start = 80 if image else 60
        if image:
            ty_start = 380

        if title:
            tw, _ = text_bbox(draw, title, font_title)
            draw.text((x_start + (panel_w - tw) // 2, ty_start), title,
                      fill=(255, 255, 255, panel_alpha), font=font_title)

        if text:
            lines = _wrap_text(draw, text, font_text, panel_w - 40)
            for i, line in enumerate(lines):
                lalpha = int(min(panel_progress * 3 - i * 0.1, 1.0) * 255)
                lalpha = max(0, min(255, lalpha))
                draw.text((x_start + 20, ty_start + 50 + i * 36), line,
                          fill=(200, 200, 200, lalpha), font=font_text)

    return img


def render_ranking(img, draw, data, progress, config):
    items = data.get("items", [])
    title = data.get("title", "Ranking")

    font_title = get_font(52, bold=True)
    font_rank = get_font(48, bold=True)
    font_name = get_font(36)
    font_detail = get_font(28)

    tw, th = text_bbox(draw, title, font_title)
    draw.text(((img.width - tw) // 2, 40), title, fill=(255, 255, 255, int(progress * 255)), font=font_title)

    row_h = min(100, (img.height - 160) // max(len(items), 1))
    colors = [COLORS["secondary"], COLORS["primary"], COLORS["accent"]] + [COLORS["text_dim"]] * 20

    for i, item in enumerate(items):
        item_progress = max(0, min(1, progress * len(items) - i) / 1.5)
        if item_progress <= 0:
            continue

        y = 130 + i * row_h
        alpha = int(min(item_progress * 3, 1.0) * 255)
        slide_x = int((1 - ease_out_simple(item_progress)) * 300)

        rank_color = colors[i] if i < len(colors) else COLORS["text_dim"]

        draw_rounded_rect(draw, (60 + slide_x, y, img.width - 60 + slide_x, y + row_h - 8),
                          12, (26, 26, 46, alpha))

        draw.text((80 + slide_x, y + (row_h - 48) // 2), f"#{i + 1}",
                  fill=(rank_color[0], rank_color[1], rank_color[2], alpha), font=font_rank)

        name = item.get("name", item.get("title", ""))
        draw.text((170 + slide_x, y + (row_h - 36) // 2), name,
                  fill=(255, 255, 255, alpha), font=font_name)

        detail = item.get("detail", item.get("subtitle", ""))
        if detail:
            draw.text((img.width - 400 + slide_x, y + (row_h - 28) // 2 + 4), detail,
                      fill=(170, 170, 170, alpha), font=font_detail)

    return img


def render_conclusion(img, draw, data, progress, config):
    title = data.get("title", "Conclusion")
    text = data.get("text", "")

    font_title = get_font(72, bold=True)
    font_text = get_font(36)

    alpha = int(progress * 255)

    tw, th = text_bbox(draw, title, font_title)
    ty = img.height // 2 - 100 if text else img.height // 2 - th // 2
    draw.text(((img.width - tw) // 2, ty), title, fill=(255, 255, 255, alpha), font=font_title)

    if text:
        lines = _wrap_text(draw, text, font_text, img.width - 300)
        start_y = ty + th + 40
        for i, line in enumerate(lines):
            line_progress = max(0, min(1, progress * len(lines) - i) / 2)
            line_alpha = int(min(line_progress * 3, 1.0) * 255)
            lw, _ = text_bbox(draw, line, font_text)
            draw.text(((img.width - lw) // 2, start_y + i * 48), line,
                      fill=(200, 200, 200, line_alpha), font=font_text)

    return img


def render_chapter_title(img, draw, data, progress, config):
    title = data.get("title", "")
    number = data.get("number", "")
    color_name = data.get("color", "primary")
    color = COLORS.get(color_name, COLORS["primary"])

    font_num = get_font(140, bold=True)
    font_title = get_font(56, bold=True)

    alpha = int(progress * 255)

    if number:
        nw, nh = text_bbox(draw, str(number), font_num)
        draw.text(((img.width - nw) // 2, img.height // 2 - nh - 40),
                  str(number), fill=(color[0], color[1], color[2], alpha), font=font_num)

    if title:
        tw, th = text_bbox(draw, title, font_title)
        ty = img.height // 2 + 20 if number else img.height // 2 - th // 2
        draw.text(((img.width - tw) // 2, ty), title, fill=(255, 255, 255, alpha), font=font_title)

    line_w = int(tw * ease_out_simple(min(progress * 1.5, 1.0))) if title else 0
    if line_w > 0:
        lx = (img.width - line_w) // 2
        ly = img.height // 2 + 90 if number else img.height // 2 + th + 20
        draw.rectangle([lx, ly, lx + line_w, ly + 4], fill=(color[0], color[1], color[2], alpha))

    return img


def render_timeline(img, draw, data, progress, config):
    events = data.get("events", [])
    title = data.get("title", "Timeline")

    font_title = get_font(48, bold=True)
    font_year = get_font(28, bold=True)
    font_desc = get_font(26)

    tw, _ = text_bbox(draw, title, font_title)
    draw.text(((img.width - tw) // 2, 40), title, fill=(255, 255, 255, int(progress * 255)), font=font_title)

    if not events:
        return img

    line_y = img.height // 2
    margin = 120
    line_w = img.width - margin * 2

    line_progress = ease_out_simple(min(progress * 2, 1.0))
    current_w = int(line_w * line_progress)
    if current_w > 0:
        draw.rectangle([margin, line_y, margin + current_w, line_y + 4], fill=COLORS["primary"])

    for i, event in enumerate(events):
        event_progress = max(0, min(1, progress * len(events) - i) / 1.5)
        if event_progress <= 0:
            continue

        alpha = int(min(event_progress * 3, 1.0) * 255)
        x = margin + int(line_w * (i / max(len(events) - 1, 1)))

        draw.ellipse([x - 8, line_y - 8, x + 8, line_y + 8], fill=(255, 112, 67, alpha))

        above = i % 2 == 0
        year = str(event.get("year", event.get("date", "")))
        desc = event.get("description", event.get("text", ""))

        yw, yh = text_bbox(draw, year, font_year)
        dw, _ = text_bbox(draw, desc, font_desc)

        if above:
            draw.text((x - yw // 2, line_y - 50 - yh), year, fill=(255, 255, 255, alpha), font=font_year)
            draw.text((x - dw // 2, line_y - 50 - yh - 36), desc, fill=(170, 170, 170, alpha), font=font_desc)
        else:
            draw.text((x - yw // 2, line_y + 25), year, fill=(255, 255, 255, alpha), font=font_year)
            draw.text((x - dw // 2, line_y + 25 + yh + 8), desc, fill=(170, 170, 170, alpha), font=font_desc)

    return img


def _wrap_text(draw, text, font, max_width):
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


RENDERER_REGISTRY = {
    "title": render_title,
    "comparison": render_comparison,
    "image_text": render_image_text,
    "statistics": render_statistics,
    "fact": render_fact,
    "side_by_side": render_side_by_side,
    "ranking": render_ranking,
    "conclusion": render_conclusion,
    "chapter_title": render_chapter_title,
    "timeline": render_timeline,
}


def render_template(template_name, img, draw, data, progress, config):
    renderer = RENDERER_REGISTRY.get(template_name)
    if renderer:
        return renderer(img, draw, data, progress, config)
    return img
