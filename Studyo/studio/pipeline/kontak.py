"""Kontak tabakası: her vuruştan bir kare + hızlı geçişlerin şeritleri + ses/işaret zaman çizelgesi.

Eleştirmen (insan ya da Claude) filmi değil bu tabakayı yargılar: "ne yapmak istedim" değil, "ekranda ne var".
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import ortak as O

F_REG = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
F_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
BG = (24, 20, 17)
FG = (236, 226, 204)
DIM = (150, 138, 118)
RED = (226, 70, 52)
GOLD = (222, 186, 110)

SHEET_W = 1808
THUMB_AREA = 240 * 427  # her formatta küçük resmin alanı aynı: dikeyde 240×427, yatayda 427×240


def font(size, bold=False):
    return ImageFont.truetype(F_BOLD if bold else F_REG, size)


def LANDED(f):
    """İşaretten 3 kare sonrası: olay 'oturmuş' olmalı."""
    return f + 3


def select(v: O.Video, motion=None):
    """Kontak tabakasına girecek kareleri seçer → (vuruş hücreleri, şeritler)."""
    n = v.nframes
    cells = [{"frame": 0, "title": "İLK KARE", "step": v.timeline["sentences"][0]["step"], "sid": None, "note": "kapak adayı · döngü başı"}]
    for s in v.timeline["sentences"]:
        kc = v.keyword_cue(s["id"])
        if kc:
            name, sec = kc
            f = min(n - 1, LANDED(round(sec * v.fps)))
            note = f"işaret {name} +3k"
        else:
            f = round((s["start"] + s["end"]) / 2 * v.fps)
            note = "ANAHTAR İŞARETİ YOK (orta kare)"
        cells.append({"frame": f, "title": f"{s['id']} · {s['step'].upper()}", "step": s["step"], "sid": s["id"], "note": note})
    poster = v.cues.get("poster")
    if poster is not None:
        cells.append({"frame": min(n - 1, round(poster * v.fps)), "title": "POSTER", "step": v.timeline["sentences"][-1]["step"], "sid": None, "note": "işaret: poster"})
    cells.append({"frame": n - 1, "title": "SON KARE", "step": v.timeline["sentences"][-1]["step"], "sid": None, "note": "poster olacak kadar güçlü mü?"})

    strips = []
    for name, dur in (v.cuefile or {}).get("seritler", []):
        a = round(v.cues[name] * v.fps)
        b = a + max(6, round(dur * v.fps))
        fr = sorted({min(n - 1, int(round(a + (b - a) * k / 7))) for k in range(8)})
        strips.append({"name": f"{name} ({dur:.2f} sn)", "frames": fr})
    if motion is not None and len(motion) > 10:
        # Kaba kurgudaki en sert 3 değişim (aralarında ≥ 1 sn)
        m = motion.copy()
        m[:2] = 0
        taken = []
        for i in np.argsort(-m):
            if all(abs(i - j) > v.fps for j in taken) and all(not (s["frames"][0] - 6 <= i <= s["frames"][-1] + 6) for s in strips):
                taken.append(int(i))
            if len(taken) == 3:
                break
        for i in sorted(taken):
            fr = [min(n - 1, max(0, i + d)) for d in (-6, -4, -2, -1, 0, 1, 2, 4)]
            strips.append({"name": f"hareket zirvesi f{i} ({O.tc(i / v.fps)})", "frames": sorted(set(fr))})
    return cells, strips


def all_frames(cells, strips):
    s = {c["frame"] for c in cells}
    for st in strips:
        s.update(st["frames"])
    return sorted(s)


def _safe_overlay(img: Image.Image, fmt: str) -> Image.Image:
    """Formatın platform arayüzü bölgelerini karartır (renk tonunu bozmaz) ve güvenli alanı kesik çizgiyle çizer."""
    G = O.FORMATLAR[fmt]["guvenli"]
    w, h = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = 92
    top, bot = int(h * G["ust"]), int(h * (1 - G["alt"]))
    left, right = int(w * G["sol"]), int(w * (1 - G["sag"]))
    d.rectangle([0, 0, w, top], fill=(0, 0, 0, a))
    d.rectangle([0, bot, w, h], fill=(0, 0, 0, a))
    d.rectangle([right, top, w, bot], fill=(0, 0, 0, a))
    d.rectangle([0, top, left, bot], fill=(0, 0, 0, a))
    for x0, y0, x1, y1 in [(left, top, right, top), (left, bot, right, bot), (right, top, right, bot), (left, top, left, bot)]:
        n = int(max(abs(x1 - x0), abs(y1 - y0)) // 6)
        for k in range(0, n, 2):
            d.line([x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, x0 + (x1 - x0) * (k + 1) / n, y0 + (y1 - y0) * (k + 1) / n],
                   fill=(255, 80, 60, 230), width=1)
    return Image.alpha_composite(img.convert("RGBA"), ov)


def _wrap(d, text, fnt, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _sentence_line(d, xy, v, sid, width, fnt, fnt_b):
    """Cümleyi yazar; anahtar kelime altın renkte ve kalın."""
    kw = O.norm_word(v.script_sentence(sid).get("shot", {}).get("anahtar", "")).lower()
    x0, y = xy
    x = x0
    for w in v.text_of(sid).split():
        is_kw = kw and O.norm_word(w).lower() == kw
        f = fnt_b if is_kw else fnt
        tw = d.textlength(w + " ", font=f)
        if x + tw > x0 + width:
            x = x0
            y += fnt.size + 3
        d.text((x, y), w, font=f, fill=GOLD if is_kw else FG)
        x += tw
    return y + fnt.size + 3


def build(v: O.Video, frames: dict, cells, strips, out_png: Path, label: str, motion=None, guides=True, fmt=None):
    fmt = fmt or v.formatlar[0]
    F = O.FORMATLAR[fmt]
    ar = F["w"] / F["h"]
    PAD = 16
    TW = int(round((THUMB_AREA * ar) ** 0.5))
    TH = int(round(TW / ar))
    COLS = max(1, (SHEET_W - PAD) // (TW + PAD))
    W = max(PAD + COLS * (TW + PAD), 900)
    SW = min(int(TW * 0.62), (W - 2 * PAD) // 8 - 8)
    SH = int(round(SW / ar))
    gap_max = v.profil["olay_bosluk_sn"]
    G = F["guvenli"]
    CELL_H = 26 + TH + 92
    rows = (len(cells) + COLS - 1) // COLS
    strip_h = sum(30 + SH + 24 for _ in strips)
    TL_H = 300
    H = 96 + rows * (CELL_H + PAD) + (40 + strip_h if strips else 0) + 40 + TL_H + PAD
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    f_h1, f_b, f_s, f_xs = font(30, True), font(16, True), font(15), font(12)

    import veri
    dm = veri.damga(v)  # canlı veri: hangi anlık görüntüyle çizildiği (yalnız veri.json'u olan filmde)
    d.text((PAD, 18), f"KONTAK TABAKASI · {v.id} · {label}" + (f" · {dm}" if dm else ""), font=f_h1, fill=FG)
    d.text((PAD, 58), f"{F['ad']} {F['w']}×{F['h']} · {v.duration:.2f} sn · {v.nframes} kare · {v.fps} fps · vuruş karesi = işaret + 3 kare · "
                      f"karartılmış = platform arayüzü (üst %{G['ust'] * 100:g}, alt %{G['alt'] * 100:g}, sol %{G['sol'] * 100:g}, sağ %{G['sag'] * 100:g})",
           font=f_s, fill=DIM)

    def thumb(f, w, h):
        img = Image.open(frames[f]).convert("RGB").resize((w, h), Image.LANCZOS)
        return _safe_overlay(img, fmt).convert("RGB") if guides else img

    y = 96
    for i, c in enumerate(cells):
        col, row = i % COLS, i // COLS
        x = PAD + col * (TW + PAD)
        yy = y + row * (CELL_H + PAD)
        d.rectangle([x, yy, x + TW, yy + 22], fill=v.step_rgb(c["step"]))
        d.text((x + 6, yy + 3), c["title"], font=f_b, fill=(255, 250, 240))
        sheet.paste(thumb(c["frame"], TW, TH), (x, yy + 24))
        ty = yy + 26 + TH + 2
        d.text((x, ty), f"{O.tc(c['frame'] / v.fps)} · f{c['frame']}", font=f_b, fill=FG)
        d.text((x, ty + 19), c["note"], font=f_xs, fill=RED if "YOK" in c["note"] else DIM)
        if c["sid"]:
            _sentence_line(d, (x, ty + 36), v, c["sid"], TW, f_xs, font(12, True))
    y += rows * (CELL_H + PAD)

    if strips:
        d.text((PAD, y + 8), "GEÇİŞ ŞERİTLERİ — ara kareler: yarım kalmış, çirkin geçiş karesi var mı?", font=f_b, fill=FG)
        y += 40
        for st in strips:
            d.text((PAD, y + 4), st["name"], font=f_s, fill=GOLD)
            for j, f in enumerate(st["frames"]):
                x = PAD + j * (SW + 8)
                sheet.paste(thumb(f, SW, SH), (x, y + 28))
                d.text((x, y + 28 + SH + 3), f"f{f} · {O.tc(f / v.fps)}", font=f_xs, fill=DIM)
            y += 30 + SH + 24

    # ---------------------------------------------------------- zaman çizelgesi
    y += 16
    d.text((PAD, y), "ZAMAN ÇİZELGESİ — vuruşlar (renkli) · işaretler" + (" · müzik ızgarası" if v.beats else "") + " · ses dalgası"
           + (" · görsel değişim" if motion is not None else "") + f" · kırmızı = {gap_max:g} sn'den uzun olaysız aralık", font=f_b, fill=FG)
    y += 28
    x0, x1 = PAD + 40, W - PAD
    sx = lambda t: x0 + (x1 - x0) * t / v.duration
    for s in v.timeline["sentences"]:
        d.rectangle([sx(s["start"]), y, sx(s["end"]), y + 26], fill=v.step_rgb(s["step"]))
        d.text((sx(s["start"]) + 3, y + 5), s["id"], font=f_xs, fill=(255, 250, 240))
    downs = set(round(t, 3) for t in (v.timeline.get("downbeats") or []))
    for bt in v.beats:
        if bt <= v.duration:
            d.line([sx(bt), y + 28, sx(bt), y + (40 if round(bt, 3) in downs else 33)], fill=(120, 170, 120))
    for k in range(int(v.duration) + 1):
        d.line([sx(k), y + 28, sx(k), y + 34], fill=DIM)
        if k % 5 == 0:
            d.text((sx(k) - 6, y + 36), f"{k}s", font=f_xs, fill=DIM)
    y += 54
    times = sorted(v.cues.values())
    for a, b in zip([0.0] + times, times + [v.duration]):
        if b - a > gap_max:
            d.rectangle([sx(a), y, sx(b), y + 60], fill=(110, 30, 24))
    for k, (name, t) in enumerate(sorted(v.cues.items(), key=lambda kv: kv[1])):
        d.line([sx(t), y, sx(t), y + 60], fill=GOLD, width=1)
        d.text((sx(t) + 2, y + (k % 4) * 15), name, font=font(10), fill=GOLD)
    y += 66
    mix = v.pub / "mix.wav"
    if mix.exists():
        sr = 4000
        a = O.audio_mono(mix, sr)
        cols = int(x1 - x0)
        env = np.array([np.abs(a[int(i * len(a) / cols): int((i + 1) * len(a) / cols)]).max(initial=0) for i in range(cols)])
        env = env / (env.max() + 1e-9)
        mid = y + 45
        for i, e in enumerate(env):
            d.line([x0 + i, mid - e * 42, x0 + i, mid + e * 42], fill=(120, 150, 190))
        d.text((PAD, mid - 8), "ses", font=f_xs, fill=DIM)
        y += 94
    if motion is not None:
        cols = int(x1 - x0)
        m = np.array([motion[min(len(motion) - 1, int(i * len(motion) / cols))] for i in range(cols)])
        m = m / (np.percentile(m, 99) + 1e-9)
        base = y + 50
        for a, b in O.still_runs(motion, gap_max, fps=v.fps):
            d.rectangle([sx(a / v.fps), base - 50, sx(b / v.fps), base], fill=(110, 30, 24))
        for i, e in enumerate(np.clip(m, 0, 1)):
            d.line([x0 + i, base, x0 + i, base - e * 48], fill=(200, 150, 90))
        d.text((PAD, base - 20), "görüntü", font=f_xs, fill=DIM)
    sheet = sheet.crop((0, 0, W, min(H, y + 70)))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, optimize=True)
    return out_png
