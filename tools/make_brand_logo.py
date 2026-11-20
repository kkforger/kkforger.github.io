"""Render the KKForger brand logo purely from code (PIL).

Forged-steel style, deterministic: stone-textured charcoal tile, molten
"KK" monogram with bevel edge, anvil silhouette, hammer with a glowing
striking face, sparks, and a forged-steel "KK FORGER" wordmark baked in.

Outputs (repo root):
  brand_logo.png       512x512 RGBA tile (site root page, favicon)

Usage:
  python tools/make_brand_logo.py
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
APP_FONTS = Path(r"D:\OpenCode\AIO\04_projects\aio_tracker\assets\fonts")
MANROPE = APP_FONTS / "Manrope.ttf"

# ---------------------------------------------------------------- palette --
WHITE = (255, 255, 255)


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


def _fill_shape(shape_mask: Image.Image, stops) -> Image.Image:
    """Fill a shape's bbox with a vertical gradient, clipped to the shape."""
    x0, y0, x1, y1 = shape_mask.getbbox()
    grad = _axis_gradient(y1 - y0, stops).transpose(Image.ROTATE_90).resize((x1 - x0, y1 - y0)).convert("RGBA")
    out = Image.new("RGBA", shape_mask.size, (0, 0, 0, 0))
    out.paste(grad, (x0, y0))
    out.putalpha(shape_mask)
    return out


def _spark_points(cx: float, cy: float, r: float, q: float):
    return [
        (cx, cy - r), (cx + q, cy - q), (cx + r, cy), (cx + q, cy + q),
        (cx, cy + r), (cx - q, cy + q), (cx - r, cy), (cx - q, cy - q),
    ]


def _composite_clipped(img: Image.Image, layer: Image.Image, tile_mask: Image.Image):
    img.alpha_composite(
        Image.composite(layer, Image.new("RGBA", img.size, (0, 0, 0, 0)), tile_mask)
    )


SPARK_STOPS = [(0.0, (255, 214, 120)), (0.45, (245, 158, 11)), (1.0, (249, 115, 22))]


def _draw_spark(img, S, tile_mask, s, cx, cy, r, glow_alpha, blur):
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon(
        _spark_points(cx, cy, r * 1.9, r * 0.24 * 1.9), fill=(245, 158, 11, glow_alpha)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(s(blur)))
    _composite_clipped(img, glow, tile_mask)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(_spark_points(cx, cy, r, r * 0.24), fill=255)
    img.alpha_composite(_fill_shape(mask, SPARK_STOPS))


# ------------------------------------------------------------- textures ----
def _stone_texture(S: int, s, radius: int) -> Image.Image:
    """Deterministic mottled stone speckle, clipped to the tile."""
    rng = random.Random(42)
    tex = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(tex)
    shades = [(16, 18, 26), (26, 30, 42), (44, 50, 66), (10, 12, 18)]
    for _ in range(260):
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        r = rng.uniform(s(2), s(11))
        shade = shades[rng.randrange(4)]
        d.ellipse((x - r, y - r, x + r, y + r), fill=shade + (rng.randint(22, 64),))
    for _ in range(46):
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        r = rng.uniform(s(1), s(3.4))
        warm = rng.random() < 0.65
        col = (249, 115, 22, rng.randint(28, 85)) if warm else (196, 84, 24, rng.randint(18, 55))
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S, S), radius=radius, fill=255)
    tex.putalpha(Image.composite(tex.getchannel("A"), Image.new("L", (S, S), 0), mask))
    return tex


def _vignette(S: int, s, radius: int) -> Image.Image:
    """Soft darkening toward the tile edges."""
    vig = Image.new("L", (S, S), 0)
    ImageDraw.Draw(vig).rounded_rectangle(
        (s(28), s(28), S - s(28), S - s(28)), radius=max(1, radius - s(28)),
        outline=255, width=s(64),
    )
    vig = vig.filter(ImageFilter.GaussianBlur(s(46)))
    dark = Image.new("RGBA", (S, S), (5, 7, 12, 0))
    dark.putalpha(vig.point(lambda a: min(255, a * 220 // 255)))
    return dark


# ------------------------------------------------------------------- icon --
ANVIL = [
    (96, 318), (140, 300), (372, 300), (372, 330), (344, 338), (330, 356),
    (352, 372), (352, 392), (166, 392), (166, 372), (188, 356), (176, 338),
    (140, 330),
]


def render_brand_icon(size: int = 512, ss: int = 4, margin: int = 0) -> Image.Image:
    S = size * ss
    k = S / 512.0
    s = lambda v: int(round(v * k))

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # -- charcoal tile -------------------------------------------------
    tile_r = s(110)
    grad = diagonal_gradient((S, S), [(0.0, (34, 40, 56)), (1.0, (13, 16, 26))]).convert("RGBA")
    tile_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tile_mask).rounded_rectangle((0, 0, S, S), radius=tile_r, fill=255)
    grad.putalpha(tile_mask)
    img.alpha_composite(grad)

    # -- stone texture + vignette ---------------------------------------
    img.alpha_composite(_stone_texture(S, s, tile_r))
    img.alpha_composite(_vignette(S, s, tile_r))

    # -- ember glow behind the monogram ---------------------------------
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for rad, a in [(s(190), 70), (s(120), 90)]:
        gd.ellipse((s(256) - rad, s(265) - rad, s(256) + rad, s(265) + rad), fill=(240, 100, 20, a))
    glow = glow.filter(ImageFilter.GaussianBlur(s(40)))
    _composite_clipped(img, glow, tile_mask)

    # -- anvil behind the letters ---------------------------------------
    anvil_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(anvil_mask).polygon([(s(x), s(y)) for x, y in ANVIL], fill=255)
    img.alpha_composite(_fill_shape(anvil_mask, [(0.0, (60, 66, 84)), (1.0, (12, 14, 20))]))

    # -- "KK" monogram: bevel edge + fire gradient ----------------------
    font = _font(MANROPE, s(198), variation="ExtraBold")
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    bbox = probe.textbbox((0, 0), "KK", font=font)
    tw = bbox[2] - bbox[0]
    tx = (S - tw) / 2 - bbox[0]
    ty = s(148) - bbox[1]

    mono = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mono).text((tx, ty), "KK", font=font, fill=255)

    # drop shadow
    shadow = mono.filter(ImageFilter.GaussianBlur(s(6)))
    sh = Image.new("RGBA", (S, S), (6, 8, 14, 0))
    sh.putalpha(shadow.point(lambda a: a * 3 // 4))
    _composite_clipped(img, sh, tile_mask)

    # bevel ring: dilated text in dark steel
    bevel = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bevel)
    off = s(5)
    for dx, dy in [(off, 0), (0, off), (off, off), (-off, 0), (0, -off), (-off, -off), (off, -off), (-off, off)]:
        bdraw.text((tx + dx, ty + dy), "KK", font=font, fill=(24, 27, 38, 255))
    _composite_clipped(img, bevel, tile_mask)

    # fire gradient: molten bright at the bottom, dark steel at the top
    img.alpha_composite(_fill_shape(mono, [
        (0.0, (255, 205, 110)),
        (0.35, (242, 122, 28)),
        (0.62, (176, 56, 18)),
        (1.0, (84, 32, 14)),
    ]))

    # molten core hotspot brightening the middle of the letters
    core = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(core).ellipse((s(150), s(210), s(362), s(300)), fill=(255, 190, 90, 120))
    core = core.filter(ImageFilter.GaussianBlur(s(30)))
    _composite_clipped(img, Image.composite(core, Image.new("RGBA", (S, S), (0, 0, 0, 0)), mono), tile_mask)

    # -- hammer, top-right, rotated -------------------------------------
    hammer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hammer)
    hd.rounded_rectangle((s(96), s(84), s(330), s(108)), radius=s(12), fill=(52, 42, 32, 255))
    hd.rounded_rectangle((s(96), s(84), s(330), s(94)), radius=s(4), fill=(80, 66, 48, 255))
    hd.rounded_rectangle((s(306), s(22), s(404), s(170)), radius=s(18), fill=(40, 44, 58, 255))
    hd.rounded_rectangle((s(306), s(146), s(404), s(170)), radius=s(18), fill=(255, 150, 46, 255))
    hglow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hglow).ellipse((s(280), s(110), s(440), s(240)), fill=(255, 140, 40, 90))
    hglow = hglow.filter(ImageFilter.GaussianBlur(s(26)))
    hammer.alpha_composite(hglow)
    hammer = hammer.rotate(-32, expand=True, resample=Image.BICUBIC)
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hl.alpha_composite(hammer, ((S - hammer.width) // 2 + s(150), -s(10)))
    _composite_clipped(img, hl, tile_mask)

    # -- sparks ----------------------------------------------------------
    rng = random.Random(7)
    for _ in range(14):
        x = rng.uniform(s(90), s(430))
        y = rng.uniform(s(60), s(330))
        r = rng.uniform(s(1.5), s(4))
        dot = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(dot).ellipse((x - r, y - r, x + r, y + r), fill=(255, 190, 90, rng.randint(90, 200)))
        _composite_clipped(img, dot, tile_mask)
    _draw_spark(img, S, tile_mask, s, s(120), s(160), s(16), 130, 10)
    _draw_spark(img, S, tile_mask, s, s(410), s(230), s(13), 110, 9)

    # -- "KK FORGER" wordmark, forged steel ------------------------------
    font_t = _font(MANROPE, s(60), variation="ExtraBold")
    tb = probe.textbbox((0, 0), "KK FORGER", font=font_t)
    ttx = (S - (tb[2] - tb[0])) / 2 - tb[0]
    tty = s(412) - tb[1]

    tsh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(tsh).text((ttx + s(4), tty + s(5)), "KK FORGER", font=font_t, fill=(8, 9, 14, 230))
    _composite_clipped(img, tsh, tile_mask)

    tout = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    td = ImageDraw.Draw(tout)
    o = s(3)
    for dx, dy in [(o, 0), (0, o), (o, o), (-o, 0), (0, -o), (-o, -o), (o, -o), (-o, o)]:
        td.text((ttx + dx, tty + dy), "KK FORGER", font=font_t, fill=(16, 18, 26, 255))
    _composite_clipped(img, tout, tile_mask)

    tmask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tmask).text((ttx, tty), "KK FORGER", font=font_t, fill=255)
    img.alpha_composite(_fill_shape(tmask, [
        (0.0, (208, 216, 232)),
        (0.55, (140, 148, 168)),
        (1.0, (72, 80, 100)),
    ]))

    # downscale
    return img.resize((size, size), Image.LANCZOS)


# -------------------------------------------------------------------- main --
if __name__ == "__main__":
    icon = render_brand_icon()
    icon.save(ROOT / "brand_logo.png")
    print("wrote brand_logo.png", icon.size)

    # dark-background preview for inspection
    bg = Image.new("RGBA", icon.size, (9, 11, 16, 255))
    bg.alpha_composite(icon)
    bg.convert("RGB").save(ROOT / "brand_logo_preview.png")
    print("wrote brand_logo_preview.png")
