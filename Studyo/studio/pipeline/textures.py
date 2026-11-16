"""Kâğıt, ahşap, toprak ve gren dokularını prosedürel üretir -> public/textures/"""
import numpy as np
from pathlib import Path
from PIL import Image, ImageFilter
from scipy.ndimage import zoom, gaussian_filter

OUT = Path(__file__).resolve().parent.parent / "public" / "textures"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(1453)


def noise(h, w, cell):
    gh, gw = h // cell + 3, w // cell + 3
    g = rng.random((gh, gw))
    z = zoom(g, cell, order=3)
    return z[:h, :w]


def fractal(h, w, base, octaves=5, persistence=0.5):
    out = np.zeros((h, w)); amp = 1.0; tot = 0
    cell = base
    for _ in range(octaves):
        out += amp * noise(h, w, max(2, int(cell)))
        tot += amp; amp *= persistence; cell /= 2
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-9)


def save(arr, name, mode="RGB", q=None):
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode)
    if q:
        img.save(OUT / name, quality=q)
    else:
        img.save(OUT / name, optimize=True)
    print("ok", name, img.size)


# --- Parşömen (harita kâğıdı) 1320x1520 birim -> 1980x2280 px
H, W = 2280, 1980
base = np.array([233, 216, 178], float)
lo = fractal(H, W, 420, 4)
mid = fractal(H, W, 90, 4)
fib = gaussian_filter(rng.standard_normal((H, W)), (0.6, 6))
img = np.ones((H, W, 3)) * base
shade = 1 + (lo - 0.5) * 0.10 + (mid - 0.5) * 0.05 + fib * 0.025
img *= shade[..., None]
# lekeler
st = fractal(H, W, 300, 4)
stain = gaussian_filter(np.clip((st - 0.66) / 0.14, 0, 1) ** 1.5, 6)
img *= (1 - stain[..., None] * np.array([0.025, 0.045, 0.075]))
# benekler
sp = rng.random((H, W)) > 0.9993
sp = gaussian_filter(sp.astype(float), 1.2)
img *= (1 - 0.6 * np.clip(sp * 6, 0, 1))[..., None]
# yanık / yırtık kenar
yy, xx = np.mgrid[0:H, 0:W]
d = np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy]).astype(float)
edge_n = fractal(H, W, 60, 4)
d_eff = d - edge_n * 55 - 10
burn = np.clip(1 - d_eff / 110, 0, 1) ** 1.6
img *= (1 - 0.42 * burn)[..., None]
img[..., 2] *= (1 - 0.15 * burn)
alpha = np.clip(d_eff / 3, 0, 1) * 255
rgba = np.dstack([img, alpha])
save(rgba, "parchment.png", "RGBA")

# --- Ceviz masa 1600x2600
H, W = 2600, 1600
yy, xx = np.mgrid[0:H, 0:W].astype(float)
warp = fractal(H, W, 260, 4) * 60 + fractal(H, W, 40, 3) * 8
board = 300
y_in = (yy % board)
rings = np.sin((yy + warp * 1.8) * 0.05 + fractal(H, W, 120, 3) * 4) * 0.5 + 0.5
pores = gaussian_filter(rng.standard_normal((H, W)), (0.6, 22))
rings = 0.6 * rings + 0.4 * (gaussian_filter(rng.standard_normal((H, W)), (1.2, 40)) * 2 + 0.5).clip(0, 1)
var = fractal(H, W, 500, 3)
t = 0.55 * rings + 0.25 * var + 0.12 * (pores * 0.5 + 0.5)
dark = np.array([46, 27, 15], float); light = np.array([104, 66, 38], float)
img = dark + (light - dark) * t[..., None]
seam = np.exp(-((y_in - 0) ** 2) / 6) + np.exp(-((y_in - board) ** 2) / 6)
img *= (1 - 0.55 * seam)[..., None]
img *= (1 - 0.18 * np.clip((y_in - board * 0.8) / (board * 0.2), 0, 1))[..., None]
save(img, "wood.jpg", q=88)

# --- Toprak (kalas sahnesi) 1080x1920
H, W = 1920, 1080
lo = fractal(H, W, 300, 5); hi = fractal(H, W, 12, 3)
img = np.array([44, 30, 19], float) * (0.75 + 0.45 * lo[..., None]) * (0.9 + 0.2 * hi[..., None])
peb = gaussian_filter((rng.random((H, W)) > 0.9985).astype(float), 2.2)
img += (np.clip(peb * 10, 0, 1) * 40)[..., None]
save(img, "earth.jpg", q=86)

# --- Gren 512x512 (gri, tekrarlanabilir)
g = rng.standard_normal((512, 512)) * 38 + 128
save(np.dstack([g, g, g]), "grain.png")
