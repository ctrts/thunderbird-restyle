# Trance wallpaper generator

`generate-backgrounds.py` rebuilds every wallpaper in `../backgrounds` from
scratch. There are no binary source assets — each image is drawn procedurally
from the palette in `../colors.toml`, so the backgrounds cannot drift out of
sync with the rest of the theme.

```sh
./generate-backgrounds.py              # rebuild all seven (~60s)
./generate-backgrounds.py --only 1 6   # rebuild just these
./generate-backgrounds.py --out /tmp/x # preview somewhere else first
omarchy theme set trance               # restage into the live theme
```

Requires ImageMagick 7 (`magick`) built with librsvg. Python needs no packages.

| # | file | what it is |
|---|------|-----------|
| 1 | `1-aurora.jpg` | aurora curtains over a starfield and ridgelines |
| 2 | `2-flow.jpg` | 2600 particles traced through a noise field |
| 3 | `3-tunnel.jpg` | polar depth mapping — receding rings, twisting spokes |
| 4 | `4-waveform.jpg` | 46 stacked traces, front rows occluding the back |
| 5 | `5-lasers.jpg` | off-centre beam rig over a lit haze floor |
| 6 | `6-aurora-waves.jpg` | aurora with spectrum waves as the landscape |
| 7 | `7-aurora-ridge-waves.jpg` | aurora with ridgelines, waves along the bottom |

## Things worth knowing before you tweak

**Banding.** Smooth dark gradients contour badly at 8 bit. Two defences: the
pixel renderer dithers each channel by ±0.7 LSB as it writes, and a light film
grain is added at JPEG time. Both matter — remove either and the aurora sky
develops visible contour rings.

**Grain vs file size.** Grain is incompressible. `GRAIN = "0.12"` yields ~600 KB
per image; at 0.4 the same images run to several megabytes with no visible
improvement. Raise it only if you see banding.

**Output size.** 2560x1440, deliberately larger than a 1080p panel — downscaling
is free quality. Change `W, H` if you want native output for a bigger display.

**Deterministic.** Every random source is explicitly seeded, so a rebuild
reproduces the same images (bar the film grain, which ImageMagick seeds itself).
Change a `seed=` argument to roll a different variation of that wallpaper.

**Composition.** Layers are combined with `Screen` where they emit light (glows,
beams, trails) and `Over` where they occlude (ridgelines, waveform fills).
Bloom is a blurred copy of a layer screened underneath the sharp original.
