#!/usr/bin/env python3
"""Regenerate the Trance theme's wallpapers.

Every image is built procedurally from the theme palette in ../colors.toml, so
the backgrounds can never drift out of sync with the rest of the theme. Nothing
is downloaded and there are no binary source assets to keep around.

    ./generate-backgrounds.py                  # write into ../backgrounds
    ./generate-backgrounds.py --out /tmp/试     # write somewhere else first
    ./generate-backgrounds.py --only 1 6       # regenerate just these

Requires: python3 (stdlib only) and ImageMagick 7 (`magick`) with librsvg.

Notes on two non-obvious choices, both of which fix artefacts that were
visible on screen:

  * Smooth dark gradients contour badly once quantised to 8 bit, so `render()`
    dithers each channel by +/-0.7 LSB as it writes. This is why the aurora sky
    is banding-free despite being an almost-flat gradient.
  * A light film grain is added at JPEG time for the same reason. Keep the
    attenuation low: grain is incompressible, and at 0.4+ these files balloon
    from ~600 KB to several MB for no visible gain.
"""

import argparse
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

W, H = 2560, 1440
ASPECT = W / H

# --- palette (mirrors ../colors.toml) ---------------------------------------
AZr, VIr, MIr = (0x38, 0xD6, 0xFF), (0xA9, 0x7B, 0xFF), (0x4E, 0xF0, 0xC2)
BASE, DEEP, INDIGO = (0x07, 0x0A, 0x16), (0x0B, 0x0F, 0x1E), (0x1A, 0x23, 0x40)
AZ, VI, MI = "#38d6ff", "#a97bff", "#4ef0c2"

HORIZON = 0.80          # shared by the aurora sky, its ridgelines and the stars
GRAIN = "0.12"          # +noise attenuation at JPEG time
QUALITY = "92"


# --- small helpers -----------------------------------------------------------
def clamp(x):
    return 0 if x < 0 else (255 if x > 255 else int(x))


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def add(c, k, m):
    return (c[0] + k[0] * m, c[1] + k[1] * m, c[2] + k[2] * m)


def hexc(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in c)


def sm(t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return t * t * (3 - 2 * t)


def pulse(t, w):
    f = t - math.floor(t)
    d = f if f < 1 - f else 1 - f
    return math.exp(-(d / w) ** 2)


def magick(*args):
    subprocess.run(["magick", *[str(a) for a in args]], check=True)


def render(path, w, h, fn):
    """Rasterise fn(u, v) -> rgb into a PPM, dithering to defeat 8-bit banding."""
    px = bytearray(w * h * 3)
    uni = random.Random(99).uniform
    i = 0
    for y in range(h):
        v = y / (h - 1)
        for x in range(w):
            r, g, b = fn(x / (w - 1), v)
            px[i] = clamp(r + uni(-0.7, 0.7))
            px[i + 1] = clamp(g + uni(-0.7, 0.7))
            px[i + 2] = clamp(b + uni(-0.7, 0.7))
            i += 3
    with open(path, "wb") as f:
        f.write(b"P6\n%d %d\n255\n" % (w, h) + bytes(px))


def svg(path, body, defs=""):
    with open(path, "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
                f"<defs>{defs}</defs>{body}</svg>")


def upscale(src, dst):
    magick(src, "-filter", "Lanczos", "-resize", f"{W}x{H}!", dst)


def rasterise(src, dst):
    magick("-background", "none", src, "-resize", f"{W}x{H}!", dst)


def to_jpeg(src, dst):
    magick(src, "-attenuate", GRAIN, "+noise", "Gaussian",
           "-quality", QUALITY, "-sampling-factor", "4:4:4", "-strip", dst)


# --- pixel layers ------------------------------------------------------------
AURORA_CURTAINS = [   # y0, amp, freq, phase, colour, intensity, width
    (0.30, 0.075, 3.1, 0.4, AZr, 0.40, 0.105),
    (0.40, 0.100, 2.2, 2.3, VIr, 0.30, 0.130),
    (0.24, 0.055, 4.7, 4.1, MIr, 0.17, 0.070),
    (0.50, 0.065, 1.6, 5.2, AZr, 0.22, 0.160),
]


def aurora_sky(u, v):
    c = lerp(BASE, DEEP, sm(v * 1.05))
    for y0, amp, freq, ph, col, inten, wid in AURORA_CURTAINS:
        yc = y0 + amp * math.sin(u * freq * 6.283 + ph) + amp * 0.4 * math.sin(u * freq * 2.7 + ph * 1.7)
        d = v - yc
        band = math.exp(-(d * d) / (2 * wid * wid))
        # vertical filaments: this is what makes it read as curtains, not cloud
        fil = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(u * 150.0 + ph * 7.0)) \
                           * (0.6 + 0.4 * math.sin(u * 37.0 + ph * 2.0))
        env = 0.45 + 0.55 * math.exp(-((u - 0.5) ** 2) / (2 * 0.42 ** 2))
        hang = 1.0 if d < 0 else math.exp(-(d / (wid * 1.7)) ** 2)
        c = add(c, col, inten * band * fil * env * hang)
    c = add(c, INDIGO, 0.24 * math.exp(-((v - 0.62) ** 2) / (2 * 0.20 ** 2)))
    if v > HORIZON - 0.02:     # ground catches some light, so it isn't dead black
        c = add(c, AZr, 0.085 * math.exp(-((v - HORIZON) / 0.13) ** 2))
        c = add(c, INDIGO, 0.30 * math.exp(-((v - HORIZON) / 0.16) ** 2))
    return c


def dark_field(u, v):
    """Neutral ground for the flow-field trails."""
    c = lerp(BASE, DEEP, sm(v * 1.1))
    c = add(c, INDIGO, 0.30 * math.exp(-((v - 0.80) ** 2) / (2 * 0.26 ** 2)))
    c = add(c, AZr, 0.06 * math.exp(-((v - 0.85) ** 2) / (2 * 0.14 ** 2)))
    return c


def stage(u, v):
    """Hazy club air with a lit floor for the laser beams to land on."""
    c = lerp(BASE, DEEP, sm(v * 1.05))
    c = add(c, INDIGO, 0.40 * math.exp(-((v - 0.86) ** 2) / (2 * 0.16 ** 2)))
    c = add(c, AZr, 0.13 * math.exp(-((v - 0.93) ** 2) / (2 * 0.085 ** 2))
                     * (0.5 + 0.5 * math.exp(-((u - 0.34) ** 2) / (2 * 0.34 ** 2))))
    c = add(c, VIr, 0.05 * math.exp(-((v - 0.60) ** 2) / (2 * 0.26 ** 2)))
    return c


def tunnel(u, v):
    """Polar depth mapping: rings recede, spokes twist. Held at 55% intensity so
    windows sitting on top of it stay readable."""
    dx, dy = (u - 0.5) * ASPECT, (v - 0.5)
    r = math.hypot(dx, dy) or 1e-4
    ang = math.atan2(dy, dx)
    depth = 0.30 / r
    fog = math.exp(-depth * 0.155)
    ring = pulse(depth * 2.15, 0.115)
    spoke = pulse(ang / 6.283 * 14.0 + depth * 0.34, 0.16)
    b = (ring * 0.80 + spoke * 0.42 + ring * spoke * 0.75) * fog * 0.55
    col = lerp(AZr, VIr, 0.5 + 0.5 * math.sin(ang * 2.0 + depth * 0.42))
    c = lerp(BASE, DEEP, sm(0.30 + r * 0.42))
    c = add(c, col, b * 0.95)
    return add(c, INDIGO, 0.16 * fog)


# --- vector layers -----------------------------------------------------------
def stars_svg(path, n=620, seed=21):
    rnd = random.Random(seed)
    svg(path, "".join(
        f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, H * HORIZON):.0f}" '
        f'r="{rnd.uniform(0.5, 2.0):.2f}" fill="#fff" opacity="{rnd.uniform(0.12, 0.8):.2f}"/>'
        for _ in range(n)))


def ridges_svg(path):
    fills = ["#0e1526", "#0b111f", "#080d18", "#050911"]
    el = []
    for k in range(4):
        base, amp = H * (HORIZON + k * 0.052), 54 - k * 11
        pts = []
        for j in range(260):
            u = j / 259
            y = base - (math.sin(u * 6.283 * 1.3 + k * 2.1) * amp
                        + math.sin(u * 6.283 * 2.9 + k * 1.1) * amp * 0.45
                        + math.sin(u * 6.283 * 5.7 + k * 3.3) * amp * 0.20)
            pts.append(f"{u * W:.0f},{y:.0f}")
        el.append(f'<polygon points="{" ".join(pts)} {W},{H} 0,{H}" fill="{fills[k]}"/>')
        el.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{AZ}" '
                  f'stroke-opacity="{0.34 - k * 0.07:.2f}" stroke-width="1.8"/>')
    svg(path, "".join(el))


def flow_svg(path, n=2600, seed=11):
    """Particles integrated through a slowly-varying angle field."""
    rnd = random.Random(seed)

    def field(x, y):
        return (math.sin(x * 0.00115 + 0.7) * 1.35
                + math.cos(y * 0.00170 - 0.4) * 1.25
                + math.sin((x * 0.6 + y) * 0.00080 + 2.1) * 0.95)

    tr = []
    for _ in range(n):
        x, y = rnd.uniform(-240, W + 240), rnd.uniform(-200, H + 200)
        t = min(1, max(0, (x / W * 0.55 + y / H * 0.55) + rnd.uniform(-0.16, 0.16)))
        col = hexc(lerp(AZr, VIr, t))
        pts = []
        for _ in range(rnd.randint(100, 240)):
            pts.append("%.0f,%.0f" % (x, y))
            a = field(x, y)
            x += math.cos(a) * 7.0
            y += math.sin(a) * 7.0
            if x < -300 or x > W + 300 or y < -260 or y > H + 260:
                break
        if len(pts) < 14:
            continue
        tr.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" '
                  f'stroke-opacity="{rnd.uniform(0.10, 0.34):.3f}" '
                  f'stroke-width="{rnd.uniform(0.9, 2.6):.1f}" stroke-linecap="round"/>')
    svg(path, "".join(tr))


def waveform_svg(path, n=46, seed=5):
    """Stacked traces; each row's fill occludes the rows behind it."""
    rnd = random.Random(seed)
    layers = []
    for i in range(n):
        t = i / (n - 1)
        ybase = H * 0.15 + t * H * 0.74
        comps = [(rnd.uniform(0, 6.283), rnd.uniform(1.4, 6.5), rnd.uniform(0.3, 1.0))
                 for _ in range(6)]
        pts = []
        for j in range(460):
            u = j / 459
            env = math.exp(-((u - 0.5) ** 2) / (2 * 0.17 ** 2)) \
                + 0.34 * math.exp(-((u - 0.5) ** 2) / (2 * 0.40 ** 2))
            amp = env * (0.32 + 0.68 * math.exp(-((t - 0.52) ** 2) / (2 * 0.26 ** 2)))
            val = sum(math.sin(u * fr * 6.283 + p) * w for p, fr, w in comps) / 3.0
            val += math.sin(u * 88.0 + i * 1.7) * 0.13
            pts.append("%.0f,%.0f" % (u * W, ybase - val * amp * 168))
        col = hexc(lerp(VIr, AZr, t))
        layers.append(f'<polygon points="{" ".join(pts)} {W},{H + 8} 0,{H + 8}" fill="#070a16"/>')
        layers.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" '
                      f'stroke-opacity="0.92" stroke-width="2.0"/>')
    svg(path, "".join(layers))


def beams_svg(path):
    """Off-centre rig; a symmetric apex reads as a retro sunburst, so keep it off-centre."""
    apex = (W * 0.30, -420.0)
    specs = [(-34, .42, AZ), (-27, .26, VI), (-20, .62, AZ), (-13, .34, AZ),
             (-6, .46, VI), (0, .30, AZ), (7, .70, AZ), (14, .32, VI),
             (21, .52, AZ), (28, .28, AZ), (35, .58, VI), (42, .34, AZ),
             (49, .44, AZ), (56, .24, VI), (63, .38, AZ)]
    defs, shapes = [], []
    for i, (deg, op, col) in enumerate(specs):
        a = math.radians(deg)
        dx, dy = math.sin(a), math.cos(a)
        ex, ey = apex[0] + dx * 3000.0, apex[1] + dy * 3000.0
        half, px, py = 20.0, -math.cos(a), math.sin(a)
        pts = "%.0f,%.0f %.0f,%.0f %.0f,%.0f" % (
            apex[0], apex[1], ex + px * half, ey + py * half, ex - px * half, ey - py * half)
        defs.append(f'<linearGradient id="b{i}" gradientUnits="userSpaceOnUse" '
                    f'x1="{apex[0]:.0f}" y1="{apex[1]:.0f}" x2="{ex:.0f}" y2="{ey:.0f}">'
                    f'<stop offset="0.04" stop-color="{col}" stop-opacity="{op:.2f}"/>'
                    f'<stop offset="0.42" stop-color="{col}" stop-opacity="{op * 0.50:.2f}"/>'
                    f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient>')
        shapes.append(f'<polygon points="{pts}" fill="url(#b{i})"/>')
    svg(path, "".join(shapes), "".join(defs))


def waves_svg(path, floor, maxh, nlayers=6, seed=41, samples=760):
    """Layered smooth spectrum curves. Fills fade to fully transparent before the
    floor -- six fills all reaching it stack into a bright horizontal streak."""
    rnd = random.Random(seed)

    def curve(t, comps, envf, envph):
        arch = 0.38 + 0.62 * math.sin(t * math.pi) ** 0.70
        swell = 0.42 + 0.58 * math.sin(t * math.pi * envf + envph)
        v = sum(math.sin(t * fr * 6.283 + ph) * w for fr, ph, w in comps) \
            / sum(w for _, _, w in comps)
        return arch * swell * (0.34 + 0.66 * v)   # wide range -> real peaks and valleys

    defs, body = [], []
    for i in range(nlayers):
        f = i / (nlayers - 1)                     # 0 = back/tallest, 1 = front/shortest
        col = hexc(lerp(VIr, AZr, min(1.0, f * 1.25)) if f < 0.8
                   else lerp(AZr, MIr, (f - 0.8) / 0.2))
        comps = [(rnd.uniform(1.1, 2.6), rnd.uniform(0, 6.283), 1.00),
                 (rnd.uniform(3.2, 6.0), rnd.uniform(0, 6.283), 0.60),
                 (rnd.uniform(6.5, 10.5), rnd.uniform(0, 6.283), 0.30),
                 (rnd.uniform(11.0, 16.0), rnd.uniform(0, 6.283), 0.13)]
        envf, envph = rnd.uniform(2.2, 5.5), rnd.uniform(0, 6.283)
        h_top = maxh * (1.0 - f * 0.62)
        pts = [f"{j / (samples - 1) * W:.1f},"
               f"{floor - (14 + curve(j / (samples - 1), comps, envf, envph) * h_top):.1f}"
               for j in range(samples)]
        defs.append(f'<linearGradient id="wv{i}" gradientUnits="userSpaceOnUse" '
                    f'x1="0" y1="{floor - h_top:.0f}" x2="0" y2="{floor:.0f}">'
                    f'<stop offset="0" stop-color="{col}" stop-opacity="{0.32 - f * 0.10:.2f}"/>'
                    f'<stop offset="0.5" stop-color="{col}" stop-opacity="{0.11 - f * 0.03:.2f}"/>'
                    f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient>')
        body.append(f'<polygon points="{" ".join(pts)} {W},{floor:.0f} 0,{floor:.0f}" '
                    f'fill="url(#wv{i})"/>')
        body.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" '
                    f'stroke-opacity="{0.62 + f * 0.30:.2f}" '
                    f'stroke-width="{2.8 - f * 0.9:.1f}" stroke-linejoin="round"/>')
    svg(path, "".join(body), "".join(defs))


def mirror(src, dst, floor, strength="#4a4a4a", work="."):
    """Mirror a transparent layer about y=floor and fade it out downward."""
    floor = int(floor)
    offset = 2 * floor - H
    raw, fade, alpha = (os.path.join(work, n) for n in ("m-raw.png", "m-fade.png", "m-a.png"))
    magick("-size", f"{W}x{H}", "xc:none", "(", src, "-flip", ")",
           "-geometry", f"+0+{offset}", "-composite", raw)
    magick("(", "-size", f"{W}x{floor}", "xc:black", ")",
           "(", "-size", f"{W}x{H - floor}", f"gradient:{strength}-#000000", ")",
           "-append", fade)
    magick(raw, "-alpha", "extract", fade, "-compose", "Multiply", "-composite", alpha)
    magick(raw, alpha, "-compose", "CopyOpacity", "-composite", dst)


def bloom(src, dst, radius):
    magick(src, "-blur", f"0x{radius}", dst)


# --- the seven wallpapers ----------------------------------------------------
def build(which, work, outdir):
    def step(n):
        print(f"  [{n}/7] {NAMES[n]}", flush=True)

    p = lambda n: os.path.join(work, n)
    out = lambda n: os.path.join(outdir, n)

    need_sky = {1, 6, 7} & which
    need_stars = {1, 6, 7} & which
    need_ridges = {1, 7} & which

    if need_sky:
        render(p("sky.ppm"), 854, 480, aurora_sky)
        upscale(p("sky.ppm"), p("sky.png"))
    if need_stars:
        stars_svg(p("stars.svg")); rasterise(p("stars.svg"), p("stars.png"))
    if need_ridges:
        ridges_svg(p("ridges.svg")); rasterise(p("ridges.svg"), p("ridges.png"))

    if 1 in which:
        step(1)
        magick(p("sky.png"), p("stars.png"), "-compose", "Over", "-composite",
               p("ridges.png"), "-compose", "Over", "-composite", p("1.png"))
        to_jpeg(p("1.png"), out("1-aurora.jpg"))

    if 2 in which:
        step(2)
        render(p("field.ppm"), 640, 360, dark_field)
        upscale(p("field.ppm"), p("field.png"))
        flow_svg(p("flow.svg")); rasterise(p("flow.svg"), p("flow.png"))
        bloom(p("flow.png"), p("flow-glow.png"), 22)
        magick(p("field.png"), p("flow-glow.png"), "-compose", "Screen", "-composite",
               p("flow.png"), "-compose", "Screen", "-composite",
               "-modulate", "88", p("2.png"))
        to_jpeg(p("2.png"), out("2-flow.jpg"))

    if 3 in which:
        step(3)
        render(p("tunnel.ppm"), 1280, 720, tunnel)
        upscale(p("tunnel.ppm"), p("3.png"))
        to_jpeg(p("3.png"), out("3-tunnel.jpg"))

    if 4 in which:
        step(4)
        waveform_svg(p("wave.svg"))
        magick("-background", "#070a16", p("wave.svg"), "-resize", f"{W}x{H}!", p("wave.png"))
        bloom(p("wave.png"), p("wave-glow.png"), 18)
        magick(p("wave.png"), p("wave-glow.png"), "-compose", "Screen", "-composite", p("4.png"))
        to_jpeg(p("4.png"), out("4-waveform.jpg"))

    if 5 in which:
        step(5)
        render(p("stage.ppm"), 854, 480, stage)
        upscale(p("stage.ppm"), p("stage.png"))
        beams_svg(p("beams.svg")); rasterise(p("beams.svg"), p("beams.png"))
        bloom(p("beams.png"), p("beams-glow.png"), 34)
        magick(p("stage.png"), p("beams-glow.png"), "-compose", "Screen", "-composite",
               p("beams.png"), "-compose", "Screen", "-composite", p("5.png"))
        to_jpeg(p("5.png"), out("5-lasers.jpg"))

    if 6 in which:
        step(6)
        floor = H * 0.86     # low, so the mirrored band below isn't dead space
        waves_svg(p("wavesA.svg"), floor, 580, seed=41)
        rasterise(p("wavesA.svg"), p("wavesA.png"))
        mirror(p("wavesA.png"), p("reflA.png"), floor, work=work)
        bloom(p("wavesA.png"), p("wavesA-glow.png"), 28)
        magick(p("sky.png"), p("stars.png"), "-compose", "Over", "-composite",
               p("reflA.png"), "-compose", "Screen", "-composite",
               p("wavesA-glow.png"), "-compose", "Screen", "-composite",
               p("wavesA.png"), "-compose", "Over", "-composite", p("6.png"))
        to_jpeg(p("6.png"), out("6-aurora-waves.jpg"))

    if 7 in which:
        step(7)
        waves_svg(p("wavesB.svg"), H - 4.0, 380, seed=53)
        rasterise(p("wavesB.svg"), p("wavesB.png"))
        bloom(p("wavesB.png"), p("wavesB-glow.png"), 22)
        magick(p("sky.png"), p("stars.png"), "-compose", "Over", "-composite",
               p("ridges.png"), "-compose", "Over", "-composite",
               p("wavesB-glow.png"), "-compose", "Screen", "-composite",
               p("wavesB.png"), "-compose", "Over", "-composite", p("7.png"))
        to_jpeg(p("7.png"), out("7-aurora-ridge-waves.jpg"))


NAMES = {1: "aurora", 2: "flow", 3: "tunnel", 4: "waveform",
         5: "lasers", 6: "aurora-waves", 7: "aurora-ridge-waves"}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(here, os.pardir, "backgrounds"),
                    help="output directory (default: ../backgrounds)")
    ap.add_argument("--only", nargs="+", type=int, choices=sorted(NAMES),
                    help="regenerate only these, e.g. --only 1 6")
    args = ap.parse_args()

    if not shutil.which("magick"):
        sys.exit("error: ImageMagick 7 (`magick`) is not on PATH")

    which = set(args.only) if args.only else set(NAMES)
    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="trance-bg-") as work:
        build(which, work, outdir)
    print(f"\nwrote {len(which)} wallpaper(s) to {outdir}")
    print("apply with:  omarchy theme set trance")


if __name__ == "__main__":
    main()
