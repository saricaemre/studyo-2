"""Niyetli altyazı (Caption with Intention yaklaşımı): anlatımın kelime başına şiddeti ve perdesi değişken yazı tipine bağlanır.

  şiddet → ağırlık (wght) ve boyut      (bağıran kelime kalın ve büyük, fısıltı ince ve küçük; en küçük boyut 64 px)
  perde  → genişlik (wdth) ve hafif yükselme (tiz kelime dar ve biraz yukarıda, pes kelime geniş)
  konuşmacı → renk                      (script.json → konusmacilar; kontrast zeminin en kötü durumunda ≥ 4,5:1)

Ölçüm anlatım dosyasından (public/<id>/narration.wav; kelime zamanları ./st ses'in hizalaması): şiddet K-ağırlıklı (BS.1770 süzgeci)
etkin enerji, perde YIN (numpy; 60–500 Hz). Şiddet bütün film üzerinden (konuşmacılar arası fark da görünsün), perde konuşmacı
başına (çocuğun sesi hep tizdir; tonlamayı gösteren, kimliği renk) ortanca ve MAD ile ölçeklenir. Sayfa ve satırlar her format için
burada kurulur (yazı tipi ölçü tablosu public/fontlar/roboto-flex/olcu.json): iki motor aynı satırları çizer, ölçüm aynı veriden denetler.

Seçim: script.json → "altyazi": "niyetli" (ya da {"tur": "niyetli", "zemin": "#0F1014", "alfa": 0.84}). Çıktı timeline.json → niyet
(./st ses kendiliğinden çalıştırır; ./st niyet <id> yeniden kurar). Eski filmlerin timeline.json'ına dokunulmaz.
Kullanım: .venv/bin/python -I pipeline/niyet.py <id>
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import ortak as O  # noqa: E402
from yazi_olcu import OLCU, kelime_genisligi, tablo  # noqa: E402

SURUM = 4
AILE = "Roboto Flex"
SR = 48000

# eşleme (boyut 1080 px kısa kenar için; bileşen unit ile çarpar)
WGHT = (360, 900)          # fısıltı → bağırış
BOYUT = (66.0, 96.0)       # px; okunurluk alt sınırı 64 px (sayfa küçültmesi de bunun altına inmez)
EN_KUCUK = 64.0
WDTH = (112.0, 82.0)       # pes → tiz
KAY = 0.05                 # perdeyle yükselme, em (± yarısı)
SAYFA_KELIME = 7
SATIR = 2
ESIK_ETKIN = 4.5           # söylenen kelime: WCAG AAA (büyük yazı) / AA (normal)
ESIK_ONCE = 4.5            # henüz söylenmemiş kelime de AA (normal yazı): 3:1 telefonda soluk okundu (kör eleştiri, deneme_niyet v2)
PALET = ["#FFE08A", "#8FD3FF", "#FF9DB5", "#A8F0B0", "#D7B8FF"]
ZEMIN, ALFA = "#0F1014", 0.84
PAD_X, PAD_Y = 0.28, 0.10  # satır plakasının iç boşluğu, em (satırın en büyük boyutu)
SATIR_ARA = 0.06           # satırlar arası, em
KENAR, ALT_BOSLUK = 54.0, 36.0  # güvenli alanın içinde kenar boşluğu, px (unit = 1)


# ---------------------------------------------------------------- ses ölçümü
def oku(yol: Path, sr: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(yol), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def k_agirlik(x: np.ndarray) -> np.ndarray:
    """ITU-R BS.1770 K-ağırlığı (48 kHz katsayıları): raf süzgeci + yüksek geçiren."""
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    return lfilter(b2, a2, lfilter(b1, a1, x))


def siddet(xk: np.ndarray, bas: float, son: float) -> float:
    """Kelimenin etkin şiddeti, LUFS benzeri dB: 20 ms pencerelerin en yüksek %70'i (kelime sınırındaki sessizlik sayılmaz)."""
    a, b = int(bas * SR), max(int(son * SR), int(bas * SR) + int(0.04 * SR))
    seg = xk[a:b]
    win = int(0.02 * SR)
    n = max(1, len(seg) // win)
    e = (seg[: n * win].reshape(n, -1) ** 2).mean(1) if len(seg) >= win else np.array([(seg ** 2).mean() if len(seg) else 0.0])
    e = np.sort(e)[::-1][: max(1, int(np.ceil(len(e) * 0.7)))]
    return float(-0.691 + 10 * np.log10(e.mean() + 1e-12))


def perde(x16: np.ndarray, sr: int = 16000, fmin: float = 60.0, fmax: float = 500.0, esik: float = 0.15):
    """YIN temel frekans (de Cheveigné & Kawahara 2002), 10 ms adım, 40 ms pencere → (zamanlar, Hz; ötümsüzde nan)."""
    W, adim = int(0.04 * sr), int(0.01 * sr)
    tmin, tmax = int(sr / fmax), int(sr / fmin)
    L = W + tmax
    if len(x16) < L:
        return np.array([]), np.array([])
    n = 1 + (len(x16) - L) // adim
    idx = np.arange(L)[None, :] + adim * np.arange(n)[:, None]
    F = x16[idx]
    nfft = 1 << int(np.ceil(np.log2(L + W)))
    r = np.fft.irfft(np.fft.rfft(F, nfft) * np.conj(np.fft.rfft(F[:, :W], nfft)), nfft)[:, : tmax + 1]
    cs = np.concatenate([np.zeros((n, 1)), np.cumsum(F ** 2, axis=1)], axis=1)
    tau = np.arange(tmax + 1)
    d = cs[:, [W]] - cs[:, [0]] + cs[:, tau + W] - cs[:, tau] - 2 * r
    d[:, 0] = 0
    cm = np.ones_like(d)
    toplam = np.cumsum(d[:, 1:], axis=1)
    cm[:, 1:] = d[:, 1:] * tau[1:] / np.maximum(toplam, 1e-12)
    rms_db = 10 * np.log10((F[:, :W] ** 2).mean(1) + 1e-12)
    f0 = np.full(n, np.nan)
    for k in range(n):
        if rms_db[k] < -45:
            continue
        c = cm[k]
        alt = np.where(c[tmin: tmax] < esik)[0]
        if not len(alt):
            continue
        t = tmin + alt[0]
        while t + 1 < tmax and c[t + 1] < c[t]:
            t += 1
        if 1 <= t < tmax:  # parabolik ara değer
            y0, y1, y2 = c[t - 1], c[t], c[t + 1]
            den = y0 - 2 * y1 + y2
            t = t + (0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0)
        f0[k] = sr / t
    zaman = (np.arange(n) * adim + W / 2) / sr
    return zaman, f0


def _yari_ton(hz: float) -> float:
    return 12 * np.log2(hz / 55.0)


# ---------------------------------------------------------------- renk
def _rgb(h):
    return np.array([int(h[i: i + 2], 16) for i in (1, 3, 5)], dtype=float)


def _hex(c):
    return "#" + "".join(f"{int(round(min(255, max(0, v)))):02X}" for v in c)


def karistir(a: str, b: str, k: float) -> str:
    return _hex(_rgb(a) * (1 - k) + _rgb(b) * k)


def zeminler(zemin: str, alfa: float) -> list[str]:
    """Saydam plakanın en kötü iki durumu: altında siyah ya da beyaz görüntü."""
    return [karistir("#000000", zemin, alfa), karistir("#FFFFFF", zemin, alfa)]


def renk_guvence(renk: str, Z: list[str], esik: float) -> str:
    """Renk iki zeminde de eşiği geçene kadar beyaza yaklaştırılır (ton korunur)."""
    for _ in range(40):
        if min(O.kontrast(renk, z) for z in Z) >= esik:
            return renk
        renk = karistir(renk, "#FFFFFF", 0.08)
    return renk


def konusmacilar(v) -> dict:
    """{anahtar: {ad, renk, renk_once, kontrast, kontrast_once}}: script.json → konusmacilar; yoksa tek anlatıcı."""
    A = v.altyazi
    Z = zeminler(A.get("zemin", ZEMIN), float(A.get("alfa", ALFA)))
    tanim = v.script.get("konusmacilar") or {"anlatici": {"ad": "Anlatıcı"}}
    out = {}
    for n, (k, d) in enumerate(tanim.items()):
        istenen = d.get("renk") or PALET[n % len(PALET)]
        renk = renk_guvence(istenen, Z, ESIK_ETKIN)
        once, kk = renk, 0.0
        for kk in np.arange(0.62, -0.01, -0.04):  # söylenmemiş kelime: plakaya doğru soluk, eşiğin üstünde
            once = karistir(renk, A.get("zemin", ZEMIN), float(kk))
            if min(O.kontrast(once, z) for z in Z) >= ESIK_ONCE:
                break
        out[k] = {"ad": d.get("ad", k), "renk": renk, "istenen": istenen, "renk_once": once,
                  "kontrast": round(min(O.kontrast(renk, z) for z in Z), 2),
                  "kontrast_once": round(min(O.kontrast(once, z) for z in Z), 2)}
    return out


# ---------------------------------------------------------------- yerleşim
def kutu(fmt: str) -> dict:
    """Yazı alanı (px): güvenli alanın içinde, kenar boşluğuyla; satırlar alttan yukarı. Ortak altyazı bandından (formatlar.json →
    altyazi) bağımsız: 9x16'da bant sağda güvenli alana taşabiliyor (2b), niyetli altyazı alanını doğrudan güvenli alandan kurar."""
    F = O.FORMATLAR[fmt]
    w, h, G = F["w"], F["h"], F["guvenli"]
    u = min(w, h) / 1080
    x0, x1 = G["sol"] * w + KENAR * u, w - G["sag"] * w - KENAR * u
    return {"x": round(x0, 1), "w": round(x1 - x0, 1), "alt": round(h * (1 - G["alt"]) - ALT_BOSLUK * u, 1),
            "ust": round(h * G["ust"] + KENAR * u, 1), "unit": u}


def _gen(K, i, u):
    k = K[i]
    return kelime_genisligi(k["metin"], k["wght"], k["wdth"]) * k["boyut"] * u


def _bosluk(K, i, u):
    k = K[i]
    return kelime_genisligi(" ", k["wght"], k["wdth"]) * k["boyut"] * u


def _satir_gen(K, kel, u, olcek=1.0):
    return olcek * (sum(_gen(K, i, u) for i in kel) + sum(_bosluk(K, i, u) for i in kel[1:]))


def satirla(K, kel, genislik, u, olcek=1.0):
    """Açgözlü satırlama, sonra iki satırı dengele (üst satır alttakinden kısa kalmasın diye en uzun satırı kısalt)."""
    satirlar, cur = [], []
    for i in kel:
        if cur and _satir_gen(K, cur + [i], u, olcek) > genislik:
            satirlar.append(cur)
            cur = []
        cur.append(i)
    if cur:
        satirlar.append(cur)
    if len(satirlar) == 2:
        a, b = satirlar
        while len(a) > 1:
            a2, b2 = a[:-1], [a[-1]] + b
            if max(_satir_gen(K, a2, u, olcek), _satir_gen(K, b2, u, olcek)) < max(_satir_gen(K, a, u, olcek), _satir_gen(K, b, u, olcek)) \
                    and _satir_gen(K, b2, u, olcek) <= genislik:
                a, b = a2, b2
            else:
                break
        satirlar = [a, b]
    return satirlar


SON_NOKTA = re.compile(r"[.!?…]['’\"”»)]*$")


def yerlesim(K: list[dict], fmt: str, sure: float) -> dict:
    """Format için sayfalar: cümle (konuşmacı) ve cümle içi nokta sayfayı böler; sayfa ≤ 7 kelime, ≤ 2 satır.
    Tek kelime alana sığmazsa sayfa küçültülür (en küçük boyut 64 px'in altına inmez; inemezse ölçüm ❌ verir)."""
    B = kutu(fmt)
    u, cx = B["unit"], O.FORMATLAR[fmt]["w"] / 2
    # satır genişliği karenin eksenine göre simetrik alandan (plaka boşluğu dahil): 9x16'da güvenli alan sağda dar; geniş sayfa
    # eksenden kayınca öteki sayfalarla hizası bozuluyordu (kör eleştiri, deneme_niyet v3). Her sayfa karenin ekseninde kalır.
    gen = 2 * min(cx - B["x"], B["x"] + B["w"] - cx) - 2 * PAD_X * BOYUT[1] * u
    gruplar, cur = [], []
    for i, k in enumerate(K):
        if cur and (k["cumle"] != K[cur[-1]]["cumle"] or SON_NOKTA.search(K[cur[-1]]["metin"]) or k["bas"] - K[cur[-1]]["son"] > 0.6):
            gruplar.append(cur)
            cur = []
        cur.append(i)
    if cur:
        gruplar.append(cur)
    sayfalar = []
    for g in gruplar:
        cur = []
        for i in g:
            dene = cur + [i]
            if cur and (len(dene) > SAYFA_KELIME or len(satirla(K, dene, gen, u)) > SATIR):
                sayfalar.append(cur)
                cur = []
            cur.append(i)
        if cur:
            sayfalar.append(cur)
    out = []
    for n, kel in enumerate(sayfalar):
        en_kucuk = min(K[i]["boyut"] for i in kel)
        olcek = 1.0
        en_uzun = max(_satir_gen(K, [i], u) for i in kel)
        if en_uzun > gen:
            olcek = max(gen / en_uzun, EN_KUCUK / en_kucuk)
        satirlar = satirla(K, kel, gen, u, olcek)
        bas = max(0.0, K[kel[0]]["bas"] - 0.10)
        son = K[kel[-1]]["son"] + 0.6
        if n + 1 < len(sayfalar):
            son = min(son, max(0.0, K[sayfalar[n + 1][0]]["bas"] - 0.10))
        son = min(max(son, K[kel[-1]]["son"]), sure)
        S = []
        for s in satirlar:
            ust = max(K[i]["boyut"] for i in s) * u * olcek
            S.append({"kelimeler": s, "genislik": round(_satir_gen(K, s, u, olcek), 1), "boyut": round(ust, 1)})
        yuk = sum(s["boyut"] * (1.12 + 2 * PAD_Y) for s in S) + SATIR_ARA * sum(s["boyut"] for s in S[1:])
        # yatay merkez: karenin ekseni (satır genişliği bunu sağlar); kayma yalnız güvenlik için
        pg = max(s["genislik"] + 2 * PAD_X * s["boyut"] for s in S)
        lo, hi = B["x"] + pg / 2, B["x"] + B["w"] - pg / 2
        merkez = min(max(cx, lo), hi) if lo <= hi else B["x"] + B["w"] / 2
        out.append({"bas": round(bas, 3), "son": round(son, 3), "olcek": round(olcek, 4), "merkez": round(merkez, 1), "satirlar": S,
                    "yukseklik": round(yuk, 1)})
    return {"kutu": B, "sayfalar": out}


# ---------------------------------------------------------------- bütün
def anlatim_dosyasi(v) -> Path:
    return v.pub / "narration.wav"


def anahtar(v) -> str:
    """Ölçüm tazeliği: anlatım dosyası + kelime zamanları + altyazı ayarı + konuşmacılar + ölçü tablosu + sürüm."""
    h = hashlib.sha256()
    h.update(anlatim_dosyasi(v).read_bytes() if anlatim_dosyasi(v).exists() else b"")
    kel = [[w["text"], w["start"], w["end"]] for s in (v.timeline or {}).get("sentences", []) for w in s["words"]]
    cumle = {s["id"]: s.get("konusmaci") for s in v.script.get("sentences", [])}
    h.update(json.dumps([SURUM, kel, v.altyazi, v.script.get("konusmacilar"), cumle, v.formatlar], ensure_ascii=False, sort_keys=True).encode())
    h.update(OLCU.read_bytes())
    return h.hexdigest()[:16]


def _olcek(dizi, taban):
    """Ortanca ve MAD (×1,4826, tabanlı) → 0–1 (ortanca 0,5; ±2 sapma uçlar)."""
    a = np.asarray(dizi, float)
    med = float(np.median(a))
    mad = max(float(np.median(np.abs(a - med))) * 1.4826, taban)
    return np.clip(0.5 + (a - med) / (4 * mad), 0, 1), med, mad


def hesapla(v) -> dict:
    if not v.anlatim:
        raise SystemExit(f"{v.id}: anlatımsız filmde niyetli altyazı yok (script.json → ses.kaynak)")
    yol = anlatim_dosyasi(v)
    if not yol.exists() or not v.timeline:
        raise SystemExit(f"{v.id}: anlatım dosyası ya da timeline.json yok: önce ./st ses {v.id}")
    x = oku(yol, SR)
    xk = k_agirlik(x)
    from scipy.signal import resample_poly
    zaman, f0 = perde(resample_poly(x, 1, 3))
    cumle_k = {s["id"]: s.get("konusmaci") for s in v.script.get("sentences", [])}
    KS = konusmacilar(v)
    varsayilan = next(iter(KS))
    K = []
    for s in v.timeline["sentences"]:
        k = cumle_k.get(s["id"]) or varsayilan
        if k not in KS:
            raise SystemExit(f"{v.id}: {s['id']} cümlesinin konuşmacısı tanımsız: {k} (script.json → konusmacilar)")
        for w in s["words"]:
            sec = (zaman >= w["start"]) & (zaman <= w["end"]) & ~np.isnan(f0)
            hz = float(np.median(f0[sec])) if sec.sum() >= 2 else None
            K.append({"i": w["i"], "metin": w["text"], "bas": w["start"], "son": w["end"], "k": k, "cumle": s["id"],
                      "db": round(siddet(xk, w["start"], w["end"]), 2), "hz": round(hz, 1) if hz else None})
    if not K:
        raise SystemExit(f"{v.id}: zaman çizelgesinde kelime yok")
    s_, s_med, s_mad = _olcek([k["db"] for k in K], 2.5)
    for k, s in zip(K, s_):
        k["s"] = round(float(s), 3)
    perde_ozet = {}
    for kk in KS:
        idx = [n for n, k in enumerate(K) if k["k"] == kk]
        if not idx:
            continue
        st = [_yari_ton(K[n]["hz"]) for n in idx if K[n]["hz"]]
        if not st:  # ötümsüz: perde nötr
            for n in idx:
                K[n]["p"] = 0.5
            continue
        p, med, mad = _olcek(st, 1.5)
        it = iter(p)
        for n in idx:
            K[n]["p"] = round(float(next(it)), 3) if K[n]["hz"] else 0.5
        perde_ozet[kk] = {"ortanca_hz": round(55 * 2 ** (med / 12), 1), "sapma_yt": round(mad, 2)}
    for k in K:
        s, p = k["s"], k["p"]
        k["wght"] = round(WGHT[0] + s * (WGHT[1] - WGHT[0]))
        k["boyut"] = round(BOYUT[0] + s * (BOYUT[1] - BOYUT[0]), 1)
        k["wdth"] = round(WDTH[0] + p * (WDTH[1] - WDTH[0]), 1)
        k["kay"] = round(-(p - 0.5) * KAY * 2, 3)
    A = v.altyazi
    return {
        "surum": SURUM, "anahtar": anahtar(v), "kaynak": str(yol.relative_to(O.ROOT)),
        "yazi": {"aile": AILE, "opsz": tablo()["opsz"], "dosyalar": ["fontlar/roboto-flex/roboto-flex-latin.woff2", "fontlar/roboto-flex/roboto-flex-latin-ext.woff2"]},
        "zemin": A.get("zemin", ZEMIN), "alfa": float(A.get("alfa", ALFA)), "pad": [PAD_X, PAD_Y], "satir_ara": SATIR_ARA,
        "olcum": {"siddet_ortanca_db": round(s_med, 2), "siddet_sapma_db": round(s_mad, 2), "perde": perde_ozet},
        "konusmacilar": KS, "kelimeler": K,
        "formatlar": {fmt: yerlesim(K, fmt, v.duration) for fmt in v.formatlar},
    }


def yaz(v, N: dict):
    yol = v.pub / "timeline.json"
    tl = json.loads(yol.read_text())
    tl["niyet"] = N
    yol.write_text(json.dumps(tl, ensure_ascii=False, indent=1))


def tazelik(v) -> tuple[bool, str]:
    N = (v.timeline or {}).get("niyet")
    if not N:
        return False, "ölçülmemiş: ./st niyet " + v.id
    if N.get("anahtar") != anahtar(v):
        return False, "eski: anlatım, kelime zamanları ya da altyazı ayarı değişmiş (./st niyet " + v.id + ")"
    return True, f"anahtar {N['anahtar']}"


# ---------------------------------------------------------------- ölçüm satırları (olc.py)
def denetim(v) -> list[tuple[str, str, str, str, str]]:
    """Niyetli filmin altyazı denetimi → [(ad, değer, çıta, durum, kanıt)]. Yalnız niyetli filmde çağrılır."""
    OK, FAIL, WARN = "✅", "❌", "⚠️"
    out = []
    taze, neden = tazelik(v)
    out.append(("Niyetli altyazı ölçümü", "taze" if taze else "eski", "anlatımla aynı", OK if taze else FAIL, neden))
    N = (v.timeline or {}).get("niyet")
    if not N:
        return out
    K = N["kelimeler"]
    # okunurluk: en küçük çizilen boyut (sayfa küçültmesi dahil)
    en_kucuk, yer = 1e9, ""
    for fmt, Y in N["formatlar"].items():
        u = Y["kutu"]["unit"]
        for sy in Y["sayfalar"]:
            for s in sy["satirlar"]:
                for i in s["kelimeler"]:
                    b = K[i]["boyut"] * u * sy["olcek"]
                    if b < en_kucuk:
                        en_kucuk, yer = b, f"[{fmt}] “{K[i]['metin']}” @ {O.tc(K[i]['bas'])}"
    out.append(("Niyetli altyazı: en küçük yazı", f"{en_kucuk:.1f} px", f"≥ {EN_KUCUK:g} px", OK if en_kucuk >= EN_KUCUK - 0.05 else FAIL, yer))
    # sayfa: ≤ 7 kelime, ≤ 2 satır, satır alana sığıyor, plaka güvenli alanda
    kotu, en_cok_k, en_cok_s = [], 0, 0
    for fmt, Y in N["formatlar"].items():
        B, F = Y["kutu"], O.FORMATLAR[fmt]
        w, h, G = F["w"], F["h"], F["guvenli"]
        for sy in Y["sayfalar"]:
            nk = sum(len(s["kelimeler"]) for s in sy["satirlar"])
            en_cok_k, en_cok_s = max(en_cok_k, nk), max(en_cok_s, len(sy["satirlar"]))
            orta = sy["merkez"]
            for s in sy["satirlar"]:
                yari = s["genislik"] / 2 + PAD_X * s["boyut"]
                if orta - yari < G["sol"] * w - 0.5 or orta + yari > w * (1 - G["sag"]) + 0.5:
                    kotu.append(f"[{fmt}] “{' '.join(K[i]['metin'] for i in s['kelimeler'])}” {s['genislik']:.0f} px")
            if B["alt"] - sy["yukseklik"] < h * G["ust"] or B["alt"] > h * (1 - G["alt"]):
                kotu.append(f"[{fmt}] sayfa @ {O.tc(sy['bas'])} dikeyde")
    out.append(("Niyetli altyazı: sayfa", f"en çok {en_cok_k} kelime · {en_cok_s} satır", f"≤ {SAYFA_KELIME} kelime · ≤ {SATIR} satır",
                OK if en_cok_k <= SAYFA_KELIME and en_cok_s <= SATIR else FAIL, ""))
    out.append(("Niyetli altyazı güvenli alanda", "taşma yok" if not kotu else f"{len(kotu)} taşma", "satır plakası güvenli alanın içinde",
                OK if not kotu else FAIL, "; ".join(kotu[:4]) or "yazı tipi ölçü tablosuyla (çekirdek aralığı yok sayılır: tahmin geniş)"))
    # kontrast
    Z = zeminler(N["zemin"], N["alfa"])
    ks = N["konusmacilar"]
    etkin = min(min(O.kontrast(k["renk"], z) for z in Z) for k in ks.values())
    once = min(min(O.kontrast(k["renk_once"], z) for z in Z) for k in ks.values())
    out.append(("Niyetli altyazı kontrastı", f"söylenen {etkin:.1f}:1 · sıradaki {once:.1f}:1",
                f"≥ {ESIK_ETKIN:g}:1 · ≥ {ESIK_ONCE:g}:1 (plakanın altı siyah ya da beyaz)",
                OK if etkin >= ESIK_ETKIN and once >= ESIK_ONCE else FAIL,
                ", ".join(f"{k['ad']} {k['renk']}" + (f" (istenen {k['istenen']}, kontrast için açıldı)" if k["istenen"].upper() != k["renk"].upper() else "")
                          for k in ks.values())))
    if len(ks) > 1:
        anahtarlar = list(ks)
        fark = min(O.renk_farki(ks[a]["renk"], ks[b]["renk"]) for n, a in enumerate(anahtarlar) for b in anahtarlar[n + 1:])
        out.append(("Niyetli altyazı: konuşmacı renkleri ayrışıyor", f"ΔE {fark:.0f}", "≥ 20", OK if fark >= 20 else WARN,
                    "yakın renkler konuşmacıyı karıştırır: script.json → konusmacilar.<k>.renk" if fark < 20 else ""))
    # ölçüm ayrışıyor mu (her kelime aynı görünüyorsa niyet görünmez)
    s_ = [k["s"] for k in K]
    p_ = [k["p"] for k in K]
    yayilim = (max(s_) - min(s_), max(p_) - min(p_))
    out.append(("Niyetli altyazı: ses ayrışması", f"şiddet {yayilim[0]:.2f} · perde {yayilim[1]:.2f} (0–1)", "≥ 0,3 (biri)",
                OK if max(yayilim) >= 0.3 else WARN,
                f"şiddet ortancası {N['olcum']['siddet_ortanca_db']:g} dB ± {N['olcum']['siddet_sapma_db']:g}"
                + "".join(f" · {ks[k]['ad']} perde {o['ortanca_hz']:g} Hz ± {o['sapma_yt']:g} yt" for k, o in N["olcum"]["perde"].items())
                + ("" if max(yayilim) >= 0.3 else ": anlatım tekdüze, altyazı da tekdüze görünür")))
    return out


def kod_kullaniyor(v) -> bool:
    """Sahne kodu niyetli altyazıyı çiziyor mu (Remotion <NiyetliAltyazi, HyperFrames niyetliAltyazi(...))."""
    if v.motor == "hyperframes":
        d = O.ROOT / "hf" / v.id
        return any("niyetliAltyazi(" in f.read_text() for f in [d / "index.html", *(d / "compositions").rglob("*.html")] if f.exists())
    return v.kod_dizini.exists() and any("<NiyetliAltyazi" in f.read_text() for f in v.kod_dizini.rglob("*.ts*"))


def main(vid: str):
    v = O.load(vid)
    if not v.niyetli:
        raise SystemExit(f"{vid}: niyetli altyazı seçili değil (script.json → \"altyazi\": \"niyetli\"; anlatımlı film)")
    N = hesapla(v)
    yaz(v, N)
    K = N["kelimeler"]
    print(f"niyetli altyazı: {len(K)} kelime · {len(N['konusmacilar'])} konuşmacı · anahtar {N['anahtar']}")
    for k in K:
        print(f"  {O.tc(k['bas'])} {N['konusmacilar'][k['k']]['ad'][:8]:8s} {k['metin'][:16]:16s} {k['db']:7.1f} dB "
              f"{(str(k['hz']) + ' Hz') if k['hz'] else '   —   ':>9s}  s {k['s']:.2f} p {k['p']:.2f} → wght {k['wght']} wdth {k['wdth']:g} {k['boyut']:g} px")
    for fmt, Y in N["formatlar"].items():
        print(f"  [{fmt}] {len(Y['sayfalar'])} sayfa: " + " | ".join(" / ".join(" ".join(K[i]["metin"] for i in s["kelimeler"]) for s in sy["satirlar"])
                                                              for sy in Y["sayfalar"]))


if __name__ == "__main__":
    main(sys.argv[1])
