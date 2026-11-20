"""Render the KKForger brand logo purely from code (PIL).

Same conventions as the AIO Tracker branding script: every pixel is drawn
deterministically, supersampled 4x and downscaled with LANCZOS. No AI
imagery, no external sources.

Design: "forge" identity for the developer brand.
  - charcoal slate tile (diagonal gradient), distinct from the app's violet
  - white "KK" monogram in Manrope ExtraBold with a metallic sheen
  - amber 4-point forge spark with glow, striking off the monogram's top-right

Outputs (repo root):
  brand_logo.png       512x512 RGBA tile (site root page, favicon)
  brand_wordmark.png   horizontal lockup, transparent (future use)

Usage:
  python tools/make_brand_logo.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
APP_FONTS = Path(r"D:\OpenCode\AIO\04_projects\aio_tracker\assets\fonts")
MANROPE = APP_FONTS / "Manrope.ttf"

# ---------------------------------------------------------------- palette --
SLATE_HI = (30, 38, 54)      # #1E2636 tile gradient top-left
SLATE_LO = (11, 14, 22)      # #0B0E16 tile gradient bottom-right
WHITE = (255, 255, 255)
SHEEN = (199, 210, 254)      # #C7D2FE metallic cool sheen
AMBER = (245, 158, 11)       # #F59E0B forge spark
ORANGE = (249, 115, 22)      # #F97316 molten core
SHADOW_INK = (4, 6, 12)


def _font(path: Path, size: int, variation: str | None = None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size)
    if variation:
        try:
            font.set_variation_by_name(variation)
        except Exception:
            pass  # static font without variations: default weight is fine
    return font


def _lerp_color(c0, c1, t: float):
    return tuple(round(a + (b - a) * t) for a, b in zip(c0, c1))


def _stop_color(stops, t: float):
    if t <= stops[0][0]:
        return stops[0][1]
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            span = p1 - p0
            local = 0.0 if span <= 0 else (t - p0) / span
            return _lerp_color(c0, c1, min(1.0, max(0.0, local)))
    return stops[-1][1]


def _axis_gradient(length: int, stops):
    strip = Image.new("RGB", (length, 1))
    px = strip.load()
    for x in range(length):
        px[x, 0] = _stop_color(stops, x / (length - 1))
    return strip


def diagonal_gradient(size, stops) -> Image.Image:
    w, h = size
    horiz = _axis_gradient(w, stops).resize((w, h))
    vert = _axis_gradient(h, stops).transpose(Image.ROTATE_90).resize((w, h))
    return Image.blend(horiz, vert, 0.5)


def _vertical_gradient_overlay(mask: Image.Image, stops) -> Image.Image:
    """Gradient image clipped to the alpha of `mask` (L mask or RGBA image)."""
    w, h = mask.size
    grad = _axis_gradient(h, stops).transpose(Image.ROTATE_90).resize((w, h)).convert("RGBA")
    alpha = mask.getchannel("A") if mask.mode == "RGBA" else mask
    grad.putalpha(alpha)
    return grad


def _spark_points(cx: float, cy: float, r: float, q: float):
    """4-point sparkle polygon: N/E/S/W tips with concave waist points."""
    return [
        (cx, cy - r), (cx + q, cy - q), (cx + r, cy), (cx + q, cy + q),
        (cx, cy + r), (cx - q, cy + q), (cx - r, cy), (cx - q, cy - q),
    ]


# ------------------------------------------------------------------- icon --
def render_brand_icon(size: int = 512, ss: int = 4, margin: int = 16) -> Image.Image:
    S = size * ss
    k = S / 512.0
    s = lambda v: int(round(v * k))

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # -- charcoal tile -------------------------------------------------
    tile_r = s(110)
    grad = diagonal_gradient((S, S), [(0.0, SLATE_HI), (1.0, SLATE_LO)]).convert("RGBA")
    tile_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tile_mask).rounded_rectangle(
        (s(margin), s(margin), S - s(margin), S - s(margin)), radius=tile_r, fill=255
    )
    grad.putalpha(tile_mask)
    img.alpha_composite(grad)

    # -- faint forge glow behind the monogram (warm ember, very subtle) -
    ember = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ed = ImageDraw.Draw(ember)
    ed.ellipse(
        (s(150), s(150), s(392), s(392)),
        fill=(249, 115, 22, 26),
    )
    ember = ember.filter(ImageFilter.GaussianBlur(s(46)))
    ember.putalpha(
        Image.composite(
            ember.getchannel("A").point(lambda a: int(a * 0.9)),
            Image.new("L", (S, S), 0),
            tile_mask,
        )
    )
    img.alpha_composite(ember)

    # -- "KK" monogram with metallic sheen -----------------------------
    mono = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mono)
    font = _font(MANROPE, s(238), variation="ExtraBold")
    text = "KK"
    bbox = md.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # optical centering (monogram sits a touch high of true center)
    tx = (S - tw) / 2 - bbox[0]
    ty = (S - th) / 2 - bbox[1] + s(6)
    md.text((tx, ty), text, font=font, fill=255)

    # soft drop shadow for depth
    shadow = mono.filter(ImageFilter.GaussianBlur(s(7)))
    shadow_img = Image.new("RGBA", (S, S), SHADOW_INK + (0,))
    shadow_img.putalpha(shadow.point(lambda a: int(a * 0.55)))
    img.alpha_composite(Image.composite(shadow_img, Image.new("RGBA", (S, S), (0, 0, 0, 0)), tile_mask))

    # sheen: white at top fading to cool mist at the bottom
    sheen_stops = [(0.0, WHITE), (0.55, WHITE), (1.0, SHEEN)]
    img.alpha_composite(_vertical_gradient_overlay(mono, sheen_stops))

    # -- amber forge spark, top-right of the monogram -------------------
    scx, scy, sr = s(368), s(138), s(64)
    sq = sr * 0.24

    # glow layer
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.polygon(_spark_points(scx, scy, sr * 1.9, sq * 1.9), fill=(245, 158, 11, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(s(18)))
    img.alpha_composite(Image.composite(glow, Image.new("RGBA", (S, S), (0, 0, 0, 0)), tile_mask))

    # molten core: gradient-filled spark (amber -> orange top to bottom)
    spark_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(spark_mask).polygon(_spark_points(scx, scy, sr, sq), fill=255)
    core_stops = [(0.0, (255, 214, 120)), (0.45, AMBER), (1.0, ORANGE)]
    img.alpha_composite(_vertical_gradient_overlay(spark_mask, core_stops))

    # tiny companion spark, lower-left of the monogram
    scx2, scy2, sr2 = s(136), s(376), s(26)
    glow2 = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow2).polygon(_spark_points(scx2, scy2, sr2 * 1.9, sr2 * 0.24 * 1.9), fill=(245, 158, 11, 70))
    glow2 = glow2.filter(ImageFilter.GaussianBlur(s(8)))
    img.alpha_composite(Image.composite(glow2, Image.new("RGBA", (S, S), (0, 0, 0, 0)), tile_mask))
    mask2 = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask2).polygon(_spark_points(scx2, scy2, sr2, sr2 * 0.24), fill=255)
    img.alpha_composite(_vertical_gradient_overlay(mask2, core_stops))

    # downscale
    return img.resize((size, size), Image.LANCZOS)


# --------------------------------------------------------------- wordmark --
def render_wordmark(height: int = 128, ss: int = 4) -> Image.Image:
    """Horizontal lockup: brand glyph + 'KKForger' + 'APPS' kicker."""
    S = height * ss
    k = S / 128.0
    s = lambda v: int(round(v * k))

    icon = render_brand_icon(size=S, ss=1, margin=12)

    font_main = _font(MANROPE, s(58), variation="ExtraBold")
    font_kick = _font(MANROPE, s(21), variation="Bold")

    probe = Image.new("RGBA", (10, 10))
    pd = ImageDraw.Draw(probe)
    b1 = pd.textbbox((0, 0), "KKForger", font=font_main)
    b2 = pd.textbbox((0, 0), "APPS", font=font_kick)
    tw = int(b1[2] - b1[0]) + s(28) + icon.width + s(36)
    th = S

    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    img.alpha_composite(icon, (0, 0))

    d = ImageDraw.Draw(img)
    # text baseline: vertically centered against the icon
    main_y = (th - (b1[3] - b1[1])) / 2 - b1[1]
    d.text((icon.width + s(28), main_y), "KKForger", font=font_main, fill=WHITE)
    # kicker under the name, right-aligned to the name's end
    kick_x = tw - (b2[2] - b2[0]) - s(2)
    kick_y = main_y + (b1[3] - b1[1]) + s(10)
    d.text((kick_x, kick_y), "APPS", font=font_kick, fill=(148, 163, 184))
    return img


# -------------------------------------------------------------------- main --
if __name__ == "__main__":
    icon = render_brand_icon()
    icon.save(ROOT / "brand_logo.png")
    print("wrote brand_logo.png", icon.size)

    mark = render_wordmark()
    mark.save(ROOT / "brand_wordmark.png")
    print("wrote brand_wordmark.png", mark.size)
