"""Generate the Easy/->Rey YouTube Downloader logo.

Renders a maroon, calligraphic capital 'R' (its forward leg ends in a swirl)
with a quill feather behind the back (straight) leg, then exports:
  - logo.png   (512x512, transparent)   used inside the app + README
  - icon.ico   (multi-size)             used as the app/exe icon

Run:  python make_logo.py
Only needs Pillow. Kept in the repo so the branding is reproducible.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = r"C:\Windows\Fonts"
CANVAS = 512

MAROON = (148, 8, 22)      # main letter colour (maroon red)
MAROON_DK = (96, 2, 10)    # feather / shadow
MAROON_INK = (70, 0, 6)    # feather spine & barbs


def load_font(px):
    candidates = [
        "segoescb.ttf",   # Segoe Script Bold  (calligraphic R w/ swash tail)
        "segoesc.ttf",    # Segoe Script
        "LHANDW.TTF",     # Lucida Handwriting
        "segoeprb.ttf",   # Segoe Print Bold
        "Gabriola.ttf",
    ]
    for name in candidates:
        path = os.path.join(FONTS_DIR, name)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, px)
            except Exception:
                continue
    return ImageFont.load_default()


def glyph_metrics(font, text="R"):
    probe = Image.new("RGBA", (8, 8))
    d = ImageDraw.Draw(probe)
    bbox = d.textbbox((0, 0), text, font=font)
    w = font.getlength(text)
    return bbox, int(math.ceil(w))


def render_letter(px, text="R"):
    """Render the bare letter, return (img, bbox)."""
    font = load_font(px)
    # first probe real metrics
    bb, _w = glyph_metrics(font, text)
    img = Image.new("RGBA", (px * 2, px * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((0, 0), text, font=font, fill=MAROON + (255,))
    # re-measure from the actual painted pixels
    mask = img.split()[3]
    bbox = mask.getbbox()
    return img, bbox


def fit_letter(target_left=150, target_top=88, max_right=474, max_bottom=424):
    """Pick a font px so the painted glyph fits the allowed box."""
    lo, hi = 10, 700
    img = bbox = None
    while lo <= hi:
        mid = (lo + hi) // 2
        img, bbox = render_letter(mid)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_right - target_left and h <= max_bottom - target_top:
            img, bbox = render_letter(mid)  # keep this as best so far by re-render at same px
            lo = mid + 1
        else:
            hi = mid - 1
    # final crisp render at chosen px
    px = hi
    img, bbox = render_letter(px)
    return img, bbox


def draw_swirl(draw, start, thickness, max_r=34, coils=1.15, taper=True):
    """A curling calligraphic tail sprouting from `start`, drawn as a spiral."""
    x0, y0 = start
    n = 220
    pts = []
    ang_start = math.radians(-70)   # initial direction of travel
    for i in range(n + 1):
        t = i / n
        # radius grows linearly while angle winds around -> an open coil
        r = max_r * t
        ang = ang_start + t * coils * 2 * math.pi
        px = x0 + r * math.cos(ang)
        py = y0 + r * math.sin(ang)
        pts.append((px, py))
    # stroke as short thick round segments, tapering towards the tip
    for i in range(len(pts) - 1):
        u = i / len(pts)
        w = max(3, int(thickness * (1 - 0.75 * u)))
        a, b = pts[i], pts[i + 1]
        if w >= 3:
            draw.line([a, b], fill=MAROON + (255,), width=w, joint="curve")
            rr = w / 2
            draw.ellipse([a[0] - rr, a[1] - rr, a[0] + rr, a[1] + rr],
                         fill=MAROON + (255,))
            draw.ellipse([b[0] - rr, b[1] - rr, b[0] + rr, b[1] + rr],
                         fill=MAROON + (255,))


def stroke(draw, pts, width):
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=MAROON + (255,), width=width,
                  joint="curve")
        rr = width / 2
        for p in (pts[i], pts[i + 1]):
            draw.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr],
                         fill=MAROON + (255,))


def quadratic(p0, p1, p2, t):
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
    return x, y


def draw_feather(img, gx, gy, glyph_h):
    """A quill feather tucked behind the back (left) of the R's straight stem."""
    d = ImageDraw.Draw(img)
    # tip upper-left, base curling behind the stem
    tip = (gx - 138, gy - 22)
    ctrl = (gx - 60, gy + glyph_h * 0.20)
    base = (gx + 40, gy + glyph_h * 0.34)
    n = 26
    center = [quadratic(tip, ctrl, base, t) for t in (i / n for i in range(n + 1))]

    # build a tapered ribbon around the centre-line
    pts = []
    half = []
    for i, p in enumerate(center):
        t = i / n
        w = 15 * (1 - 0.45 * t)
        half.append(w)
    for i in range(n + 1):
        p0 = center[max(0, i - 1)]
        p1 = center[min(n, i + 1)]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = half[i]
        pts.append((p1[0] + nx * w, p1[1] + ny * w))
    for i in range(n, -1, -1):
        p0 = center[max(0, i - 1)]
        p1 = center[min(n, i + 1)]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = half[i]
        pts.append((p1[0] - nx * w, p1[1] - ny * w))
    d.polygon(pts, fill=MAROON_DK + (255,))

    # spine
    spine = [quadratic(tip, ctrl, base, t) for t in (i / n for i in range(n + 1))]
    for i in range(n):
        a, b = spine[i], spine[i + 1]
        w = max(2, int(4.5 * (1 - 0.5 * (i / n))))
        d.line([a, b], fill=MAROON_INK + (255,), width=w, joint="curve")

    # barbs (short lines off the spine on the left/up side)
    for i in range(2, n - 1, 2):
        t = i / n
        p = quadratic(tip, ctrl, base, t)
        d1 = quadratic(tip, ctrl, base, min(1.0, t + 0.06))
        dx, dy = d1[0] - p[0], d1[1] - p[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        a = (p[0] + nx * 14, p[1] + ny * 14)
        b = (p[0] + nx * 8, p[1] + ny * 8)
        d.line([a, b], fill=MAROON_INK + (255,), width=2)


def main():
    img, bbox = fit_letter()
    lx, ty, rx, by = bbox
    w = rx - lx
    h = by - ty

    # final canvas
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.alpha_composite(img, dest=(150 - lx, 88 - ty))
    mask = canvas.split()[3].getbbox()
    gx, gy, grx, gby = mask

    # feather must be drawn before/behind? it is outside letter but overlapping
    # stem only slightly; we paint it after but it sits outside the ink so fine.
    draw_feather(canvas, gx, gy, gby - gy)

    # swirl tail: sprout from the lowest-rightmost painted pixel of the glyph
    pix = canvas.load()
    best = None
    for y in range(gby, gy, -1):
        for x in range(grx, gx, -1):
            if pix[x, y][3] > 128:
                best = (x, y)
                break
        if best:
            break
    if best is None:
        best = (grx, gby)
    draw_swirl(ImageDraw.Draw(canvas), best, thickness=34)

    canvas.save(os.path.join(HERE, "logo.png"))

    # multi-size icon
    icon = canvas
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128),
             (256, 256)]
    icon.save(os.path.join(HERE, "icon.ico"), format="ICO",
              sizes=sizes)

    # preview sheet: logo on dark + light backgrounds for a quick look
    prev = Image.new("RGB", (CANVAS * 2 + 8, CANVAS + 8), (18, 18, 18))
    prev.paste((240, 240, 240), (CANVAS + 8, 0, CANVAS * 2 + 8, CANVAS))
    prev.paste(canvas, (4, 4), canvas)
    prev.paste(canvas, (CANVAS + 8 + 4, 4), canvas)
    prev.save(os.path.join(HERE, "logo_preview.png"))

    print("letter bbox:", (lx, ty, rx, by), "size", w, "x", h)
    print("final ink bbox:", mask)
    print("saved logo.png, icon.ico, logo_preview.png")


if __name__ == "__main__":
    main()
