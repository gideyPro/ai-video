#!/usr/bin/env python3
"""Animation functions for the video renderer engine."""

import math


def ease_in_out(t):
    """Smooth ease in-out curve."""
    return t * t * (3 - 2 * t)


def ease_out(t):
    """Ease out curve."""
    return 1 - (1 - t) ** 3


def ease_in(t):
    """Ease in curve."""
    return t ** 3


def clamp(val, min_val=0.0, max_val=1.0):
    return max(min_val, min(max_val, val))


def interpolate(start, end, t):
    return start + (end - start) * clamp(t)


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def animate_fade_in(progress):
    return ease_in_out(clamp(progress))


def animate_fade_out(progress):
    return 1.0 - ease_in_out(clamp(progress))


def animate_slide_in_left(progress, offset=200):
    t = ease_out(clamp(progress))
    x = interpolate(-offset, 0, t)
    alpha = clamp(progress * 3)
    return x, alpha


def animate_slide_in_right(progress, offset=200):
    t = ease_out(clamp(progress))
    x = interpolate(offset, 0, t)
    alpha = clamp(progress * 3)
    return x, alpha


def animate_slide_up(progress, offset=150):
    t = ease_out(clamp(progress))
    y = interpolate(offset, 0, t)
    alpha = clamp(progress * 3)
    return y, alpha


def animate_slide_down(progress, offset=150):
    t = ease_out(clamp(progress))
    y = interpolate(-offset, 0, t)
    alpha = clamp(progress * 3)
    return y, alpha


def animate_zoom_in(progress):
    t = ease_out(clamp(progress))
    scale = interpolate(0.5, 1.0, t)
    alpha = clamp(progress * 3)
    return scale, alpha


def animate_zoom_out(progress):
    t = ease_out(clamp(progress))
    scale = interpolate(1.5, 1.0, t)
    alpha = clamp(progress * 3)
    return scale, alpha


def animate_scale(progress, from_scale=0.8, to_scale=1.0):
    t = ease_in_out(clamp(progress))
    scale = interpolate(from_scale, to_scale, t)
    alpha = clamp(progress * 2)
    return scale, alpha


def animate_reveal(progress, direction="left"):
    t = ease_out(clamp(progress))
    clip = interpolate(0, 100, t)
    return clip


def animate_count_up(progress, target_value):
    t = ease_out(clamp(progress))
    return int(target_value * t)


def animate_typewriter(progress, text):
    t = clamp(progress)
    chars = int(len(text) * t)
    return text[:chars]


def animate_bounce(progress):
    t = clamp(progress)
    if t < 0.6:
        scale_t = t / 0.6
        return 1.0 + 0.15 * math.sin(scale_t * math.pi)
    else:
        return 1.0


ANIMATION_REGISTRY = {
    "fadeIn": animate_fade_in,
    "fadeOut": animate_fade_out,
    "slideInLeft": animate_slide_in_left,
    "slideInRight": animate_slide_in_right,
    "slideUp": animate_slide_up,
    "slideDown": animate_slide_down,
    "zoomIn": animate_zoom_in,
    "zoomOut": animate_zoom_out,
    "scale": animate_scale,
    "reveal": animate_reveal,
    "countUp": animate_count_up,
    "typewriter": animate_typewriter,
    "bounce": animate_bounce,
}


def get_animation(name):
    return ANIMATION_REGISTRY.get(name, animate_fade_in)
