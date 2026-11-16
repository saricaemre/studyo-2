"""Ses motoru: efekt kütüphanesi + miks. Videoya özel tasarım videos/<id>/ses.py içindedir (tasarla()).

Kullanım: .venv/bin/python -I pipeline/sfx.py gemiler_karadan
Çıktı:   public/<id>/mix.wav (48 kHz stereo, -14 LUFS)
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, iirpeak, lfilter, sosfilt, fftconvolve

sys.dont_write_bytecode = True  # videos/<id>/ses.py yüklenirken __pycache__ bırakmasın
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak as O  # noqa: E402

SR = 48000
ROOT = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(1453)


# ---------------------------------------------------------------- yardımcılar
def T(d):
    return np.arange(int(d * SR)) / SR


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="high", fs=SR, output="sos"), x)


def reson(x, f, q):
    b, a = iirpeak(f, q, fs=SR)
    return lfilter(b, a, x)


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def fade(x, a=0.01, r=0.05):
    n = len(x)
    e = np.ones(n)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return x * e


def smooth_rand(d, rate, seed_shift=0):
    """Yavaş değişen rastgele zarf (0..1)."""
    n = int(d * SR)
    k = max(4, int(d * rate) + 4)
    pts = rng.random(k)
    xs = np.linspace(0, n, k)
    return np.interp(np.arange(n), xs, pts)


def brown(n):
    x = np.cumsum(rng.standard_normal(n))
    x = hp(x, 20)
    return norm(x)


def reverb(x, rt=1.6, wet=0.3, seed=0):
    n = int(rt * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-6.9 * t / rt)
    ir = lp(ir, 5000)
    ir[0] = 0
    y = fftconvolve(x, ir)
    y = np.concatenate([y, np.zeros(max(0, len(x) + n - len(y)))])[: len(x) + n]
    y = norm(y, np.max(np.abs(x)) + 1e-9)
    out = np.concatenate([x, np.zeros(n)]) * (1 - wet) + y * wet
    return out


# ---------------------------------------------------------------- efektler
def wood_tok(f=900, d=0.18):
    n = int(d * SR)
    exc = np.zeros(n)
    m = int(0.003 * SR)
    exc[:m] = rng.standard_normal(m) * np.linspace(1, 0, m)
    y = reson(exc, f, 14) + 0.5 * reson(exc, f * 2.27, 12) + 0.7 * reson(exc, f * 0.56, 9)
    y *= np.exp(-T(d) / 0.045)
    y += exc * 0.15
    return norm(fade(y, 0.0005, 0.03))


def plank_thunk():
    f = 160 * rng.uniform(0.85, 1.15)
    n = int(0.45 * SR)
    exc = np.zeros(n)
    m = int(0.006 * SR)
    exc[:m] = rng.standard_normal(m)
    y = reson(exc, f, 6) + 0.6 * reson(exc, f * 2.6, 7) + 0.3 * reson(exc, f * 5.3, 8)
    y *= np.exp(-T(0.45) / 0.11)
    thud = lp(rng.standard_normal(n), 300) * np.exp(-T(0.45) / 0.04)
    return norm(fade(y + 0.8 * norm(thud), 0.0005, 0.1))


def paper_rustle(d=0.6, density=60):
    n = int(d * SR)
    x = bp(rng.standard_normal(n), 1400, 8000) * 0.25
    imp = (rng.random(n) < density / SR) * rng.standard_normal(n)
    crack = bp(np.convolve(imp, np.exp(-np.arange(200) / 30), "same"), 1800, 9000)
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 0.8 * (0.5 + 0.5 * smooth_rand(d, 25))
    return norm((x + norm(crack)) * env)


def whoosh(d=0.7):
    n = int(d * SR)
    w = rng.standard_normal(n)
    u = np.linspace(0, 1, n)
    bands = [(150, 500), (500, 1400), (1400, 4200)]
    weights = [np.clip(1 - np.abs(u - c) * 2.2, 0, 1) for c in (0.75, 0.5, 0.3)]
    y = sum(norm(bp(w, lo, hi)) * wt for (lo, hi), wt in zip(bands, weights))
    env = np.exp(-((u - 0.45) ** 2) / 0.05)
    return norm(y * env)


def quill(d=0.95):
    n = int(d * SR)
    x = bp(rng.standard_normal(n), 2500, 9500)
    t = T(d)
    am = np.abs(np.sin(2 * np.pi * 24 * t + 3 * smooth_rand(d, 8))) ** 2
    am *= 0.6 + 0.4 * smooth_rand(d, 40)
    ticks = bp((rng.random(n) < 30 / SR) * rng.standard_normal(n), 3000, 9000) * 3
    env = fade(np.ones(n), 0.04, 0.12)
    return norm((x * am + ticks) * env)


def stamp():
    d = 0.8
    t = T(d)
    f = 48 + 62 * np.exp(-t / 0.05)
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    knock = lp(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.03)
    slap = hp(rng.standard_normal(len(t)), 2000) * np.exp(-t / 0.008)
    y = norm(thump) + 0.7 * norm(knock) + 0.35 * norm(slap)
    return norm(reverb(fade(y, 0.0005, 0.2), 0.9, 0.18))


def ney(f0=293.66, d=3.0, scoop=-0.03):
    t = T(d)
    vib = 0.0045 * np.sin(2 * np.pi * 5.1 * t) * np.clip((t - 0.35) / 0.6, 0, 1)
    glide = scoop * np.exp(-t / 0.09)
    f = f0 * (1 + vib + glide)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph) + 0.05 * np.sin(4 * ph)
    breath = bp(rng.standard_normal(len(t)), f0 * 3, f0 * 12) * 0.18
    env = np.clip(t / 0.22, 0, 1) * np.clip((d - t) / 1.1, 0, 1) ** 1.3
    y = (tone + breath * (0.6 + 0.4 * env)) * env
    return norm(reverb(y, 2.4, 0.35))


def chain_clink():
    d = 0.16
    t = T(d)
    y = np.zeros(len(t))
    for f, dec, a in zip([2300, 3650, 5150, 7300], [0.07, 0.05, 0.035, 0.025], [1, 0.7, 0.5, 0.3]):
        y += a * np.sin(2 * np.pi * f * rng.uniform(0.9, 1.1) * t + rng.random() * 6) * np.exp(-t / dec)
    tick = hp(rng.standard_normal(len(t)), 4000) * np.exp(-t / 0.002)
    return norm(fade(y + 0.4 * tick, 0.0003, 0.02))


def clank():
    d = 1.0
    t = T(d)
    y = np.zeros(len(t))
    for f, dec, a in zip([520, 1180, 1990, 2870, 4100], [0.5, 0.35, 0.25, 0.18, 0.12], [1, 0.8, 0.6, 0.4, 0.3]):
        y += a * np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-t / dec)
    thud = np.sin(2 * np.pi * 85 * t) * np.exp(-t / 0.08)
    return norm(reverb(fade(y * 0.7 + thud, 0.0005, 0.2), 1.0, 0.2))


def metal_die(d=1.5):
    t = T(d)
    y = np.zeros(len(t))
    for f, a in zip([880, 1320, 1990, 2640], [1, 0.6, 0.4, 0.25]):
        fr = f * (1 - 0.18 * t / d)
        y += a * np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.55)
    y *= 0.75 + 0.25 * np.sin(2 * np.pi * 7 * t)
    return norm(lp(fade(y, 0.005, 0.3), 5000))


def splash():
    d = 0.9
    n = int(d * SR)
    t = T(d)
    w = rng.standard_normal(n)
    y = norm(bp(w, 3000, 9000)) * np.exp(-t / 0.06) + norm(bp(w, 800, 3000)) * np.exp(-t / 0.15) + norm(bp(w, 200, 800)) * np.exp(-t / 0.25)
    for _ in range(6):
        st = rng.uniform(0.05, 0.45)
        bt = T(0.035)
        bf = np.linspace(rng.uniform(450, 700), rng.uniform(1100, 1600), len(bt))
        b = np.sin(2 * np.pi * np.cumsum(bf) / SR) * np.sin(np.pi * bt / 0.035)
        i = int(st * SR)
        y[i : i + len(b)] += 0.35 * b
    y += 0.8 * np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.07)
    return norm(fade(y, 0.002, 0.2))


def pour(d=1.2):
    n = int(d * SR)
    x = bp(rng.standard_normal(n), 300, 1500)
    gurgle = np.clip(lp(rng.standard_normal(n), 22) * 6, 0, None)
    trickle = lp(hp(rng.standard_normal(n), 3000), 6500) * 0.05
    return norm(fade(x * (0.3 + gurgle) + trickle, 0.08, 0.3))


def paper_slide(d=1.0):
    n = int(d * SR)
    x = bp(rng.standard_normal(n), 900, 5000) * (0.5 + 0.5 * smooth_rand(d, 12))
    body = bp(brown(n), 120, 500) * 0.5
    return norm(fade(x + body, 0.05, 0.2))


def creak(d, seed=0):
    """Ahşap gerilme gıcırtısı: kaymalı-yapışmalı darbe dizisi + gövde rezonansları."""
    n = int(d * SR)
    y = np.zeros(n)
    t = 0.0
    while t < d:
        ev = rng.uniform(0.25, 0.8)
        f0 = rng.uniform(55, 120)
        tt = t
        while tt < min(d, t + ev):
            i = int(tt * SR)
            if i < n:
                y[i] += rng.uniform(0.5, 1.0) * np.sin(np.pi * (tt - t) / ev)
            f0 *= rng.uniform(0.985, 1.02)
            tt += 1 / f0 * rng.uniform(0.85, 1.15)
        t += ev + rng.uniform(0.05, 0.4)
    body = reson(y, 310, 6) + 0.7 * reson(y, 640, 7) + 0.4 * reson(y, 1270, 8)
    return norm(lp(body, 4000))


def wind(d):
    n = int(d * SR)
    x = lp(brown(n), 600) * (0.55 + 0.45 * smooth_rand(d, 0.4))
    gust = bp(rng.standard_normal(n), 300, 1100) * smooth_rand(d, 0.25) ** 2 * 0.25
    return norm(x + gust)


def crickets(d):
    n = int(d * SR)
    y = np.zeros(n)
    for f in (4400, 4950):
        t = rng.uniform(0, 0.5)
        while t < d - 0.2:
            for k in range(3):
                pt = T(0.014)
                s = np.sin(2 * np.pi * f * pt) * np.sin(np.pi * pt / 0.014)
                i = int((t + k * 0.032) * SR)
                y[i : i + len(s)] += s
            t += rng.uniform(0.55, 0.95)
    return norm(lp(y, 7000))


def fire(d):
    n = int(d * SR)
    imp = (rng.random(n) < 9 / SR) * rng.uniform(0.2, 1.0, n)
    crack = lp(hp(np.convolve(imp, rng.standard_normal(120) * np.exp(-np.arange(120) / 25), "same"), 1200), 6000)
    rumble = lp(brown(n), 220) * 0.4
    return norm(crack + rumble)


def room(d):
    n = int(d * SR)
    return norm(lp(brown(n) * 0.6 + rng.standard_normal(n) * 0.05, 1200))


def drone(d):
    t = T(d)
    y = np.zeros(len(t))
    for f, a in ((73.42, 1.0), (110.0, 0.55), (146.83, 0.35), (220.0, 0.12)):
        y += a * np.sin(2 * np.pi * f * t + rng.random() * 6) * (0.75 + 0.25 * np.sin(2 * np.pi * rng.uniform(0.05, 0.12) * t))
    return norm(lp(y, 900))


def low_drum():
    d = 0.9
    t = T(d)
    f = 68 + 36 * np.exp(-t / 0.06)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.28)
    y += 0.3 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.08)
    y += 0.4 * lp(rng.standard_normal(len(t)), 500) * np.exp(-t / 0.025)
    return norm(reverb(fade(y, 0.0005, 0.2), 1.4, 0.22))


def shimmer(d=1.6):
    t = T(d)
    y = np.zeros(len(t))
    for f in (1174.7, 1568.0, 2349.3, 2960.0):
        y += np.sin(2 * np.pi * f * t + rng.random() * 6) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(5, 9) * t))
    env = np.clip(t / 0.15, 0, 1) * np.exp(-np.clip(t - 0.3, 0, None) / 0.5)
    return norm(reverb(y * env, 1.8, 0.4))


# ---------------------------------------------------------------- çizgi film ailesi (ihh_sofra'dan): dokunuş, baloncuk, yay, çan, parıltı
def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tik(d=0.03):
    """Ekrana dokunuş: kuru, parlak tık."""
    t = T(d)
    y = bp(rng.standard_normal(len(t)), 2000, 10000) * 0.6 + np.sin(2 * np.pi * 2400 * t)
    return norm(y * np.exp(-t * 260))


def baloncuk(f0=300, f1=900, d=0.18):
    """Pop: frekansı kayan yumuşak ton (doğuş, beliriş, iniş). f0 > f1 ise iner."""
    t = T(d)
    f = f0 * (f1 / f0) ** (t / d)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 0.6)


def yay(d=0.45):
    """Boing: titreyerek yükselen ton (konuşma balonu, zıplama)."""
    t = T(d)
    f = 380 + 140 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4) + 200 * t
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.clip(t / 0.005, 0, 1) * np.exp(-t * 6))


def can(m=88, d=1.2):
    """Glockenspiel çanı (MIDI notası)."""
    t = T(d)
    f = midi(m)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.6) + 0.35 * np.sin(2 * np.pi * f * 2.756 * t) * np.exp(-t * 7)
    y += 0.12 * np.sin(2 * np.pi * f * 5.404 * t) * np.exp(-t * 14)
    return norm(y * np.clip(t / 0.002, 0, 1))


def parilti(m=84, n=10, aralik=0.035, d=1.0):
    """Pentatonik yükselen çan dizisi (sihir, sevinç, başarı)."""
    olcek = [0, 2, 4, 7, 9]
    y = np.zeros(int((n * aralik + d) * SR) + 1)
    for i in range(n):
        s = can(m + 12 * (i // 5) + olcek[i % 5], d)
        k = int(i * aralik * SR)
        y[k:k + len(s)] += s * (0.9 - 0.4 * i / n)
    return norm(y)


def gum(d=0.4):
    """Yumuşak iniş darbesi."""
    t = T(d)
    f = 55 + 160 * np.exp(-t * 25)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8))


def tebesir(d=0.38):
    """Kara tahtaya tebeşirle yazı."""
    t = T(d)
    y = bp(rng.standard_normal(len(t)), 2200, 7000) * (0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 11 * t + 0.6)))
    return norm(y * np.sin(np.pi * t / d) ** 0.5)


def konfeti(d=0.6):
    """Konfeti patlaması: parlak gürültü."""
    t = T(d)
    return norm(bp(rng.standard_normal(len(t)), 1500, 12000) * np.exp(-t * 7))


# ---------------------------------------------------------------- miks
class Bus:
    def __init__(self, dur):
        self.L = np.zeros(int(dur * SR) + SR)
        self.R = np.zeros_like(self.L)

    def add(self, sig, t, db=0.0, pan=0.0):
        g = 10 ** (db / 20)
        i = int(max(0, t) * SR)
        j = min(len(self.L), i + len(sig))
        s = sig[: j - i] * g
        self.L[i:j] += s * np.sqrt((1 - pan) / 2)
        self.R[i:j] += s * np.sqrt((1 + pan) / 2)

    def add_st(self, l, r, t, db=0.0):
        g = 10 ** (db / 20)
        i = int(max(0, t) * SR)
        j = min(len(self.L), i + len(l))
        self.L[i:j] += l[: j - i] * g
        self.R[i:j] += r[: j - i] * g


def gate(n, segs, ramp=0.25):
    """Zaman aralıklarında 1 olan, kenarları yumuşak zarf."""
    e = np.zeros(n)
    for a, b in segs:
        i, j = int(a * SR), int(b * SR)
        e[max(0, i) : min(n, j)] = 1
    k = int(ramp * SR)
    ker = np.ones(k) / k
    return np.convolve(e, ker, "same")


def load_design(vid):
    """videos/<id>/ses.py → tasarla(L, fx, beds, c, sents, dur)."""
    path = ROOT / "videos" / vid / "ses.py"
    if not path.exists():
        raise SystemExit(f"Ses tasarımı yok: {path} (şablon: sablon/video/ses.py)")
    spec = importlib.util.spec_from_file_location(f"ses_{vid}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(vid):
    pub = ROOT / "public" / vid
    tl = json.loads((pub / "timeline.json").read_text())
    cf = json.loads((ROOT / "videos" / vid / "cues.json").read_text())
    script = json.loads((ROOT / "videos" / vid / "script.json").read_text())
    c = O.resolve_cues(tl, cf)
    dur = tl["duration"]
    sents = {s["id"]: s for s in tl["sentences"]}
    ses = script.get("ses", {})

    fx = Bus(dur)
    beds = Bus(dur)
    N = len(fx.L)

    def load(path, ch):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype=np.float32).astype(float).reshape(-1, ch)
        out = np.zeros((N, ch))
        out[: min(N, len(x))] = x[:N]
        return out

    nar_path = pub / "narration.wav"
    narr = norm(load(nar_path, 1)[:, 0], 0.7) if nar_path.exists() else np.zeros(N)

    tasarim = load_design(vid)
    out = tasarim.tasarla(sys.modules[__name__], fx, beds, c, sents, dur) or {}
    hush = 1 - 0.92 * gate(N, out["hush"], 0.12) if out.get("hush") else np.ones(N)

    # Anlatım altında yatak ve müzik kısma (ducking)
    env = np.sqrt(np.convolve(narr ** 2, np.ones(int(0.05 * SR)) / int(0.05 * SR), "same"))
    level = np.clip(env / 0.08, 0, 1)
    smooth = lambda e: np.convolve(e, np.ones(int(0.12 * SR)) / int(0.12 * SR), "same")
    duck = smooth(1 - 0.45 * level)
    duck_m = smooth(1 - 0.6 * level)

    # Müzik yatağı (script.json → ses.muzik): anlatım varsa altında kalır, yoksa filmin omurgasıdır
    music = np.zeros((N, 2))
    if ses.get("muzik"):
        m = load(pub / ses["muzik"], 2)
        m = m / (np.abs(m).max() + 1e-9)
        db = ses.get("muzik_db", -19.0 if nar_path.exists() else -3.0)
        music = m * 10 ** (db / 20)

    L = narr * 0.707 + fx.L * hush + beds.L * duck * hush + music[:, 0] * duck_m * hush
    R = narr * 0.707 + fx.R * hush + beds.R * duck * hush + music[:, 1] * duck_m * hush
    n_out = int(dur * SR)
    st = np.stack([L[:n_out], R[:n_out]], 1)
    fo = min(n_out, int(0.35 * SR))  # sonda kısa kısılma: kesilen yankı tık sesi bırakmasın
    st[n_out - fo:] *= np.linspace(1, 0, fo)[:, None]
    st = st / (np.max(np.abs(st)) + 1e-9) * 0.89
    tmp = pub / "_mix_raw.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", str(tmp)], input=st.astype("<f4").tobytes(), check=True)

    # İki geçişli loudnorm → -14 LUFS, -1.5 dBTP
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    js = json.loads(m[m.rindex("{") : m.rindex("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", af, "-ar", str(SR), "-c:a", "pcm_s16le", str(pub / "mix.wav")], check=True)
    tmp.unlink()
    chk = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pub / "mix.wav"), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = chk[chk.rindex("Summary:"):]
    print("mix.wav yazıldı;", " ".join(l.strip() for l in summary.splitlines() if l.strip().startswith(("I:", "Peak:"))))


if __name__ == "__main__":
    main(sys.argv[1])
