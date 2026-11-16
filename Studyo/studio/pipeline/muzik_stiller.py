"""Kodla müzik: ses stillerinin ön ayarları (katalog/ses/*.json → muzik.kod.stil).

Her ön ayar `muzik.build` ile aynı sözleşmeyi verir: (stereo dizi, ızgara). Izgara gerçek vuruşları ve bölüm başlarını
taşır; kurgu müzik seçilmeden vuruşa kesilebilir. Hepsi tohumludur: aynı ayar her zaman aynı dosyayı verir.
Kalite "geçici müzik" düzeyindedir; asıl müzik için ACE-Step kaynağı ya da lisanslı parça kullanılır.
"""
import numpy as np

import muzik as M

SR = M.SR


def _rng(stil):
    """Ön ayara özel tohum (Python'un hash'i süreçten sürece değişir, kullanılmaz)."""
    return np.random.default_rng(sum((i + 1) * ord(c) for i, c in enumerate(stil)))


def _yapi(yapi, per):
    secs, b = [], 0
    for item in yapi.split(","):
        name, bars = item.split(":")
        secs.append((name, b, int(bars) * 4))
        b += int(bars) * 4
    return secs, b


def _bitir(bus, dur, per, total, secs, bpm):
    st = np.stack([bus.L, bus.R], 1)[: int(dur * SR)]
    st = st / (np.abs(st).max() + 1e-9) * 0.89
    grid = {"bpm": bpm, "beats": [round(i * per, 4) for i in range(total + 1)],
            "downbeats": [round(i * per, 4) for i in range(0, total + 1, 4)],
            "bolumler": [{"ad": n, "ilk_vurus": b0, "vurus_sayisi": nb, "bas": round(b0 * per, 4)} for n, b0, nb in secs],
            "sure": round(dur, 3)}
    return st, grid


# ---------------------------------------------------------------- enstrümanlar
def piyano(f, d, r):
    t = M.T(d)
    y = np.zeros(len(t))
    for n in range(1, 9):
        fn = f * n * np.sqrt(1 + 0.0004 * n * n)
        y += (1 / n ** 1.3) * np.sin(2 * np.pi * fn * t) * np.exp(-t / (1.6 / (1 + 0.45 * n)))
    y += 0.05 * M.flt(r.standard_normal(len(t)), "band", [1500, 6000]) * np.exp(-t / 0.006)
    return y * np.clip((d - t) / 0.08, 0, 1)


def epiyano(f, d):
    t = M.T(d)
    I = 2.2 * np.exp(-t / 0.35)
    y = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * t)) * np.exp(-t / 1.1)
    return y * (1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)) * np.clip((d - t) / 0.06, 0, 1)


def marimba(f, d=0.5):
    t = M.T(d)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.05)) * np.exp(-t / 0.22)


def yayli(freqs, d, r, atak=0.6):
    y = sum(M.saw(f * (1 + 0.003 * np.sin(2 * np.pi * 5.2 * M.T(d))), d, (-0.004, 0.0, 0.005)) for f in freqs) / len(freqs)
    y = M.flt(y, "low", 2200)
    t = M.T(d)
    return y * np.clip(t / atak, 0, 1) * np.clip((d - t) / 0.5, 0, 1)


def drone(f, d):
    t = M.T(d)
    y = sum(M.saw(f * k, d, (-0.003, 0.002)) for k in (1, 1.5, 2)) / 3
    y = M.flt(y, "low", 380) + 0.6 * np.sin(2 * np.pi * f / 2 * t)
    return y * (0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)) * np.clip(t / 2.0, 0, 1) * np.clip((d - t) / 1.5, 0, 1)


def nabiz(f=48):
    t = M.T(0.5)
    return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.12)


def taiko(r):
    t = M.T(0.9)
    y = np.sin(2 * np.pi * np.cumsum(60 + 70 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.35)
    y += 0.5 * M.flt(r.standard_normal(len(t)), "low", 500) * np.exp(-t / 0.06)
    return y / np.abs(y).max()


def metal(f, r, d=1.6):
    t = M.T(d)
    y = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t / (0.9 / k ** 0.5)) for k in (1, 2.76, 5.4, 8.93)) / 4
    return y + 0.1 * M.flt(r.standard_normal(len(t)), "high", 4000) * np.exp(-t / 0.01)


def tik(r):
    t = M.T(0.03)
    return M.flt(r.standard_normal(len(t)), "high", 3500) * np.exp(-t / 0.004)


def plak(d, r):
    n = len(M.T(d))
    y = M.flt(r.standard_normal(n), "band", [300, 5000]) * 0.03
    imp = np.zeros(n)
    idx = r.integers(0, n, int(d * 18))
    imp[idx] = r.uniform(-1, 1, len(idx))
    return y + M.flt(imp, "high", 1200) * 0.6


def bakir(freqs, d=0.35):
    t = M.T(d)
    y = sum(M.saw(f, d, (-0.004, 0.004)) for f in freqs) / len(freqs)
    return M.flt(y, "band", [300, 2500]) * np.exp(-t / 0.12)


def tozlu_kick(r):
    return M.flt(M.kick(), "low", 2500) * 0.9


def tozlu_trampet(r):
    t = M.T(0.25)
    y = M.flt(r.standard_normal(len(t)), "band", [1200, 5000]) * np.exp(-t / 0.07) + 0.4 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)
    return M.flt(y / np.abs(y).max(), "low", 5000)


# ---------------------------------------------------------------- ön ayarlar
MINOR, MAJOR, MAJ7, MIN7 = [0, 3, 7], [0, 4, 7], [0, 4, 7, 11], [0, 3, 7, 10]


def _akorlar(root, prog, kalite):
    return [[M.hz(root + 12 + d + i) for i in kalite(d)] for d in prog]


def belgesel_sakin(bpm, yapi, ton, tail):
    r = _rng("belgesel")
    per = 60 / bpm
    secs, total = _yapi(yapi, per)
    dur = total * per + tail
    bus = M.Bus(int(dur * SR) + SR)
    root = 45 + M.NOTE[ton]
    akor = _akorlar(root, [0, -4, 3, -2], lambda d: MINOR if d == 0 else MAJOR)
    for name, b0, nb in secs:
        for k in range(nb // 4):
            bar = b0 // 4 + k
            t0 = (b0 + k * 4) * per
            ch = akor[bar % 4]
            if name != "giris":
                bus.add(yayli(ch, 4 * per + 0.6, r, 1.2), t0, -20)
            for e in range(8 if name == "ana" else 4):
                if r.random() < (0.25 if name == "kapanis" else 0.15):
                    continue
                f = ch[e % len(ch)] * (2 if e % 3 == 2 else 1)
                bus.add(piyano(f, 2.5, r), t0 + e * per * (0.5 if name == "ana" else 1), -14, -0.3 + 0.2 * (e % 4))
    return _bitir(bus, dur, per, total, secs, bpm)


def gerilim_drone(bpm, yapi, ton, tail):
    r = _rng("gerilim")
    per = 60 / bpm
    secs, total = _yapi(yapi, per)
    dur = total * per + tail
    bus = M.Bus(int(dur * SR) + SR)
    root = 33 + M.NOTE[ton]
    bus.add(drone(M.hz(root + 12), dur), 0, -10)
    for name, b0, nb in secs:
        for i in range(nb):
            tb = (b0 + i) * per
            if name in ("yukselis", "ana") and i % 4 in (0, 1):  # kalp atışı: iki atım
                bus.add(nabiz(), tb + (0 if i % 4 == 0 else -per * 0.6), -8 if i % 4 == 0 else -12)
            if name == "ana" and i % 8 == 4:
                bus.add(M.flt(metal(M.hz(root + 24 + 6), r), "low", 2500), tb, -24, 0.5 * (1 if i % 16 else -1))
    for name, b0, nb in secs[1:]:
        t0 = b0 * per
        bus.add(M.flt(M.riser(min(2.5, 4 * per)), "low", 1800), t0 - min(2.5, 4 * per), -24)
        bus.add(M.impact(), t0, -9)
    return _bitir(bus, dur, per, total, secs, bpm)


def lofi_sicak(bpm, yapi, ton, tail):
    r = _rng("lofi")
    per = 60 / bpm
    secs, total = _yapi(yapi, per)
    dur = total * per + tail
    bus = M.Bus(int(dur * SR) + SR)
    root = 45 + M.NOTE[ton]
    akor = _akorlar(root, [0, 5, 3, -2], lambda d: MIN7 if d in (0, 5) else MAJ7)
    sw = per / 2 * 0.16  # salınım (swing)
    for name, b0, nb in secs:
        for k in range(nb // 4):
            bar = b0 // 4 + k
            t0 = (b0 + k * 4) * per
            for j, f in enumerate(akor[bar % 4]):
                bus.add(epiyano(f, 4 * per), t0 + j * 0.012, -17)
            if name != "giris":
                bus.add(M.bass(M.hz(root - 12 + [0, 5, 3, -2][bar % 4] + 12), 2 * per), t0, -15)
        for i in range(nb):
            tb = (b0 + i) * per
            if name in ("ana", "yukselis"):
                if i % 4 in (0, 2):
                    bus.add(tozlu_kick(r), tb, -9)
                if i % 4 in (1, 3):
                    bus.add(tozlu_trampet(r), tb, -15, 0.1)
            if name != "kapanis":
                bus.add(M.hat(), tb, -27, 0.3)
                bus.add(M.hat(), tb + per / 2 + sw, -30, 0.3)
    bus.add(plak(dur, r), 0, -24)
    L, R = M.flt(bus.L, "low", 7000), M.flt(bus.R, "low", 7000)
    bus.L, bus.R = L, R
    return _bitir(bus, dur, per, total, secs, bpm)


def minimal_arayuz(bpm, yapi, ton, tail):
    r = _rng("minimal")
    per = 60 / bpm
    secs, total = _yapi(yapi, per)
    dur = total * per + tail
    bus = M.Bus(int(dur * SR) + SR)
    root = 57 + M.NOTE[ton]
    penta = [0, 2, 4, 7, 9, 12]
    desen = [0, 2, 4, 2, 5, 4, 3, 1]
    for name, b0, nb in secs:
        for i in range(nb * 2):
            tb = (b0 * 2 + i) * per / 2
            if name == "giris" and i % 2:
                continue
            if r.random() < 0.18:
                continue
            bus.add(marimba(M.hz(root + penta[desen[i % 8]])), tb, -15, -0.4 + 0.8 * ((i * 3) % 5) / 4)
            if name in ("ana", "yukselis"):
                bus.add(tik(r), tb + per / 4, -26, 0.5)
        for k in range(nb // 4):
            t0 = (b0 + k * 4) * per
            if name != "giris":
                bus.add(nabiz(55), t0, -12)
            bus.add(M.pad([M.hz(root - 12), M.hz(root - 5), M.hz(root + 4)], 4 * per + 0.3), t0, -26)
    return _bitir(bus, dur, per, total, secs, bpm)


def sinematik_yukselis(bpm, yapi, ton, tail):
    r = _rng("sinematik")
    per = 60 / bpm
    secs, total = _yapi(yapi, per)
    dur = total * per + tail
    bus = M.Bus(int(dur * SR) + SR)
    root = 45 + M.NOTE[ton]
    akor = _akorlar(root, [0, -4, -2, -5], lambda d: MINOR if d == 0 else MAJOR)
    for si, (name, b0, nb) in enumerate(secs):
        for k in range(nb // 4):
            bar = b0 // 4 + k
            t0 = (b0 + k * 4) * per
            ch = akor[bar % 4]
            bus.add(yayli(ch + [ch[0] * 2], 4 * per + 0.4, r, 0.3), t0, -16)
            for e in range(8):  # ostinato
                if name != "giris":
                    bus.add(M.flt(M.saw(ch[0] / 2, per / 2 * 0.9), "low", 900) * np.exp(-M.T(per / 2 * 0.9) / 0.2), t0 + e * per / 2, -18)
            if name == "ana":
                bus.add(bakir([f * 2 for f in ch]), t0, -13)
        for i in range(nb):
            tb = (b0 + i) * per
            yog = {"giris": 4, "yukselis": 2, "ana": 1, "kapanis": 8}.get(name, 4)
            if i % yog == 0:
                bus.add(taiko(r), tb, -8 if name == "ana" else -11, -0.2 + 0.4 * (i % 2))
    for name, b0, nb in secs[1:]:
        t0 = b0 * per
        bus.add(M.riser(min(3.0, 4 * per)), t0 - min(3.0, 4 * per), -16)
        bus.add(M.impact(3.0), t0, -6)
    return _bitir(bus, dur, per, total, secs, bpm)


def haber_bulteni(bpm, yapi, ton, tail):
    r = _rng("haber")
    per = 60 / bpm
    secs, total = _yapi(yapi, per)
    dur = total * per + tail
    bus = M.Bus(int(dur * SR) + SR)
    root = 45 + M.NOTE[ton]
    akor = _akorlar(root, [0, 0, -4, -2], lambda d: MINOR if d == 0 else MAJOR)
    for name, b0, nb in secs:
        for i in range(nb * 4):
            tb = (b0 * 4 + i) * per / 4
            if name != "kapanis":
                bus.add(tik(r), tb, -22 if i % 4 == 0 else -28, 0.4 if i % 2 else -0.4)
        for i in range(nb):
            tb = (b0 + i) * per
            bar = (b0 + i) // 4
            if i % 4 == 0:
                bus.add(taiko(r), tb, -10)
                bus.add(M.bass(M.hz(root - 12 + [0, 0, -4, -2][bar % 4] + 12), per * 1.5), tb, -12)
            if name in ("ana", "yukselis") and i % 2 == 1:
                bus.add(bakir(akor[bar % 4]), tb + per / 2, -14)
    for name, b0, nb in secs[1:]:
        bus.add(M.impact(1.5), b0 * per, -14)
    return _bitir(bus, dur, per, total, secs, bpm)


def sessizlik_tek_vurus(bpm, yapi, ton, tail):
    r = _rng("sessiz")
    per = 60 / bpm
    secs, total = _yapi(yapi, per)
    dur = total * per + tail
    bus = M.Bus(int(dur * SR) + SR)
    bus.add(M.flt(r.standard_normal(int(dur * SR)), "low", 300) * 0.02, 0, -6)  # oda tonu
    ana = next((b0 for n, b0, _ in secs if n == "ana"), secs[len(secs) // 2][1])
    bus.add(M.impact(3.0), ana * per, -3)
    bus.add(nabiz(40), ana * per, -6)
    return _bitir(bus, dur, per, total, secs, bpm)


def neseli_sicak(bpm, yapi, ton, tail):
    """Neşeli, sıcak çizgi film müziği (ihh_sofra'dan): ukulele benzeri tel vuruşu, glockenspiel melodisi, yaylı bas, çalkalak ve el çırpma."""
    r = _rng("neseli")
    per = 60 / bpm
    secs, total = _yapi(yapi, per)
    dur = total * per + tail
    bus = M.Bus(int(dur * SR) + SR)
    root = 48 + M.NOTE[ton]
    prog = [0, 7, 9, 5]  # I V vi IV
    kalite = lambda d: [0, 3, 7, 12] if d == 9 else [0, 4, 7, 12]
    olcek = [0, 2, 4, 7, 9]  # majör pentatonik: dört akorun hepsine oturur
    vurus = [(0, 1.0, 1), (1, 0.7, 1), (1.5, 0.5, -1), (2.5, 0.55, -1), (3, 0.8, 1), (3.5, 0.5, -1)]  # (vuruş, şiddet, yön)
    motif = [sorted(r.choice(np.arange(0, 4, 0.5), int(r.integers(3, 6)), replace=False)) for _ in range(2)]
    motif = [[(z, olcek[int(r.integers(0, 5))] + (12 if r.random() < 0.2 else 0)) for z in m] for m in motif]
    for name, b0, nb in secs:
        for k in range(nb // 4):
            bar = b0 // 4 + k
            t0 = (b0 + k * 4) * per
            d = prog[bar % 4]
            notalar = [M.hz(root + d + i) for i in kalite(d)]
            for beat, vel, yon in vurus:
                if (name == "giris" and beat not in (0, 3)) or (name == "kapanis" and beat > 0):
                    continue
                for j, f in enumerate(notalar if yon > 0 else notalar[::-1]):
                    bus.add(tel(f, 1.4, 1.2 if yon > 0 else 0.8), t0 + beat * per + j * 0.011,
                            -17 + 20 * np.log10(vel) - (3 if name == "giris" else 0), -0.25 + j * 0.15)
            if name in ("yukselis", "ana"):
                for beat in (0, 2, 2.75):
                    bus.add(M.bass(M.hz(root - 12 + d), 1.6 * per), t0 + beat * per, -13 if beat != 2.75 else -17)
            if name != "kapanis":
                for z, m in motif[bar % 2]:
                    bus.add(can(M.hz(root + 24 + m), 1.6), t0 + z * per, -16 - (4 if name == "giris" else 0), 0.2)
                    bus.add(can(M.hz(root + 36 + m), 0.8), t0 + z * per + 0.003, -28, -0.3)
            else:
                for j, f in enumerate([M.hz(root + i) for i in (-12, 0, 4, 7, 12, 16)]):
                    bus.add(tel(f, 2.0, 1.4), t0 + j * 0.012, -15, -0.3 + j * 0.12)
        for i in range(nb * 2):  # sekizlikler
            tb = (b0 + i / 2) * per
            if name in ("yukselis", "ana"):
                bus.add(calkalak(r), tb, -20 if i % 2 else -24, 0.4)
            if name == "ana":
                if i % 4 == 0:
                    bus.add(M.kick(), tb, -9)
                if i % 4 == 2:
                    bus.add(M.clap(), tb, -15, -0.1)
            elif name == "yukselis" and i % 4 == 2:
                bus.add(parmak(r), tb, -16, -0.2)
    return _bitir(bus, dur, per, total, secs, bpm)


def tel(f, d=1.2, parlak=1.0):
    """Ukulele / naylon tel: parlak, çabuk sönen harmonikler."""
    t = M.T(d)
    y = np.zeros(len(t))
    for k in range(1, 9):
        y += (1 / k ** 1.3) * np.sin(2 * np.pi * k * f * t * (1 + 0.0007 * k)) * np.exp(-t * (2.5 + 2.6 * k / parlak))
    return y * np.clip(t / 0.003, 0, 1) * 0.5


def can(f, d=1.6):
    """Glockenspiel: temel + iki uyumsuz kısmi (2,756 ve 5,404)."""
    t = M.T(d)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.6) + 0.35 * np.sin(2 * np.pi * f * 2.756 * t) * np.exp(-t * 7)
    y += 0.12 * np.sin(2 * np.pi * f * 5.404 * t) * np.exp(-t * 14)
    return y * np.clip(t / 0.002, 0, 1) * 0.45


def calkalak(r):
    t = M.T(0.09)
    return M.flt(r.standard_normal(len(t)), "high", 6000) * np.sin(np.pi * np.clip(t / 0.09, 0, 1)) ** 2 * 0.5


def parmak(r):
    t = M.T(0.06)
    return M.flt(r.standard_normal(len(t)), "band", [2500, 9000]) * np.exp(-t * 90)


ON_AYARLAR = {
    "elektronik": lambda bpm, yapi, ton, tail: M.build(bpm, yapi, ton, tail),
    "piyano-pad": belgesel_sakin,
    "drone-nabiz": gerilim_drone,
    "lofi": lofi_sicak,
    "minimal": minimal_arayuz,
    "yukselis": sinematik_yukselis,
    "bulten": haber_bulteni,
    "sessiz": sessizlik_tek_vurus,
    "neseli": neseli_sicak,
}
