"""Geçici müzik üreteci: lisans derdi olmayan, tohumlu, prosedürel bir parça (taslak ve deneme filmleri için).

Final için lisanslı ya da özgün bir parça kullanılır. Bu üretecin değeri, kurgu daha müzik seçilmeden vuruşa kesilebilsin
diye doğru bir ızgara vermesidir. Gerçek ızgarayı da yazar: vurus.py'nin doğruluğu buna karşı ölçülür.

Kullanım: .venv/bin/python -I pipeline/muzik.py <çıktı.wav> --bpm 104 --yapi "giris:1,yukselis:2,ana:4,kapanis:1" [--ton A] [--stil S]
Ses stilleri (--stil): pipeline/muzik_stiller.py ON_AYARLAR; varsayılan "elektronik" (bu dosyadaki build).
Çıktı: <çıktı.wav> (48 kHz stereo) + <çıktı>_izgara.json (gerçek BPM, vuruş, ölçü başı, bölüm başları)
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(104)
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def T(d):
    return np.arange(int(d * SR)) / SR


def flt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x)


def kick():
    t = T(0.42)
    f = 46 + 95 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.16) + 0.4 * flt(rng.standard_normal(len(t)), "low", 1800) * np.exp(-t / 0.004)
    return y / np.abs(y).max()


def clap():
    t = T(0.3)
    n = flt(rng.standard_normal(len(t)), "band", [900, 6500])
    env = np.zeros(len(t))
    for k, a in enumerate([1.0, 0.8, 0.9]):
        i = int(k * 0.011 * SR)
        env[i:] += a * np.exp(-(t[: len(t) - i]) / (0.012 if k < 2 else 0.09))
    y = n * env + 0.3 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04)
    return y / np.abs(y).max()


def hat(open_=False):
    t = T(0.25 if open_ else 0.06)
    y = flt(rng.standard_normal(len(t)), "high", 7000) * np.exp(-t / (0.08 if open_ else 0.015))
    return y / np.abs(y).max()


def saw(f, d, detune=(0.0,)):
    t = T(d)
    y = np.zeros(len(t))
    for dt in detune:
        ph = (t * f * (1 + dt) + rng.random()) % 1.0
        y += 2 * ph - 1
    return y / len(detune)


def pad(freqs, d):
    y = sum(saw(f, d, (-0.006, 0.0, 0.007)) for f in freqs) / len(freqs)
    y = flt(y, "low", 1600)
    t = T(d)
    env = np.clip(t / 0.35, 0, 1) * np.clip((d - t) / 0.4, 0, 1)
    return y * env


def bass(f, d):
    t = T(d)
    y = np.sin(2 * np.pi * f * t) + 0.35 * flt(saw(f, d), "low", 700)
    return y * np.exp(-t / 0.22) * np.clip((d - t) / 0.02, 0, 1)


def riser(d):
    t = T(d)
    n = rng.standard_normal(len(t))
    out = np.zeros(len(t))
    seg = int(0.05 * SR)
    for i in range(0, len(t), seg):
        fc = 400 + 7000 * (i / len(t)) ** 2
        out[i:i + seg] = flt(n[i:i + seg], "band", [fc * 0.7, min(fc * 1.4, 20000)], 1)
    return out * (t / d) ** 2


def impact(d=2.5):
    t = T(d)
    y = np.sin(2 * np.pi * (38 + 40 * np.exp(-t / 0.08)) * t) * np.exp(-t / 0.7)
    y += 0.5 * flt(rng.standard_normal(len(t)), "low", 900) * np.exp(-t / 0.35)
    return y / np.abs(y).max()


class Bus:
    def __init__(self, n):
        self.L = np.zeros(n)
        self.R = np.zeros(n)

    def add(self, sig, t, db=0.0, pan=0.0):
        g = 10 ** (db / 20)
        i = int(round(t * SR))
        if i >= len(self.L):
            return
        j = min(len(self.L), i + len(sig))
        s = sig[: j - i] * g
        self.L[i:j] += s * np.sqrt((1 - pan) / 2) * np.sqrt(2)
        self.R[i:j] += s * np.sqrt((1 + pan) / 2) * np.sqrt(2)


def build(bpm, yapi, ton="A", tail=2.0):
    per = 60.0 / bpm
    root = 45 + NOTE[ton]                      # A2 = 45
    prog = [0, -4, 3, -2]                      # i – VI – III – VII (doğal minör)
    minor = [0, 3, 7]
    major = [0, 4, 7]
    secs, b = [], 0
    for item in yapi.split(","):
        name, bars = item.split(":")
        secs.append((name, b, int(bars) * 4))
        b += int(bars) * 4
    total_beats = b
    dur = total_beats * per + tail
    bus = Bus(int(dur * SR) + SR)
    drop_start = []
    for name, b0, nb in secs:
        t0 = b0 * per
        if name != "giris":
            drop_start.append(t0)
        for k in range(nb // 4):                # akorlar: her ölçü bir akor
            bar = (b0 // 4) + k
            deg = prog[bar % 4]
            q = minor if deg in (0,) else major
            freqs = [hz(root + 12 + deg + i) for i in q] + [hz(root + 24 + deg + q[1])]
            bus.add(pad(freqs, 4 * per + 0.3), t0 + k * 4 * per, -17 if name in ("giris", "kapanis") else -21, 0.0)
            if name in ("ana", "yukselis"):
                for e in range(8):
                    if name == "yukselis" and e % 2:
                        continue
                    bus.add(bass(hz(root + deg), per / 2 * 0.95), t0 + k * 4 * per + e * per / 2, -13)
        for i in range(nb):
            tb = t0 + i * per
            if name in ("yukselis", "ana"):
                bus.add(kick(), tb, -6)
            if name == "ana" and i % 4 in (1, 3):
                bus.add(clap(), tb, -12, 0.1)
            if name in ("giris", "ana", "yukselis"):
                bus.add(hat(), tb + per / 2, -21 if name == "giris" else -18, 0.3)
                if name == "ana":
                    bus.add(hat(), tb, -25, -0.3)
            if name == "kapanis" and i == 0:
                bus.add(kick(), tb, -5)
        if name == "giris":
            bus.add(kick(), t0, -6)            # kanca vuruşu
    for name, b0, nb in secs[1:]:
        t0 = b0 * per
        r = min(2.0, 4 * per)
        bus.add(riser(r), t0 - r, -20)
        bus.add(impact(), t0, -10)
    # yan zincir hissi: vuruşlarda pad/bas hafifçe nefes alır
    duck = np.ones(len(bus.L))
    for i in range(total_beats):
        a = int(i * per * SR)
        L = int(per * SR)
        if a < len(duck):
            seg = 1 - 0.35 * np.exp(-np.arange(min(L, len(duck) - a)) / (0.09 * SR))
            duck[a:a + len(seg)] *= seg
    L, R = bus.L * duck, bus.R * duck
    st = np.stack([L, R], 1)[: int(dur * SR)]
    st = st / (np.abs(st).max() + 1e-9) * 0.89
    grid = {"bpm": bpm, "beats": [round(i * per, 4) for i in range(total_beats + 1)],
            "downbeats": [round(i * per, 4) for i in range(0, total_beats + 1, 4)],
            "bolumler": [{"ad": n, "ilk_vurus": b0, "vurus_sayisi": nb, "bas": round(b0 * per, 4)} for n, b0, nb in secs],
            "sure": round(dur, 3)}
    return st, grid


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--bpm", type=float, default=104)
    ap.add_argument("--yapi", default="giris:1,yukselis:2,ana:4,kapanis:1")
    ap.add_argument("--ton", default="A")
    ap.add_argument("--kuyruk", type=float, default=2.0)
    ap.add_argument("--stil", default="elektronik", help="ses stili ön ayarı (pipeline/muzik_stiller.py ON_AYARLAR)")
    a = ap.parse_args()
    if a.stil == "elektronik":
        st, grid = build(a.bpm, a.yapi, a.ton, a.kuyruk)
    else:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import muzik_stiller
        if a.stil not in muzik_stiller.ON_AYARLAR:
            raise SystemExit(f"Ön ayar yok: {a.stil} (var: {', '.join(muzik_stiller.ON_AYARLAR)})")
        st, grid = muzik_stiller.ON_AYARLAR[a.stil](a.bpm, a.yapi, a.ton, a.kuyruk)
        grid["stil"] = a.stil
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s16le", str(out)],
                   input=st.astype("<f4").tobytes(), check=True)
    out.with_name(out.stem + "_izgara.json").write_text(json.dumps(grid, ensure_ascii=False, indent=1))
    print(f"{out.name}: {grid['sure']:.2f} sn · {a.bpm:g} BPM · {len(grid['beats']) - 1} vuruş · bölümler: " +
          ", ".join(f"{b['ad']}@{b['bas']:.2f}" for b in grid["bolumler"]))
