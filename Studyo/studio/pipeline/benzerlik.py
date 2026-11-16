"""Benzerlik: filmin kareleri katalog önizlemelerine ve öteki filmlerin karelerine ne kadar benziyor (yol haritası 2b).

Yöntem (PIL + numpy), her kare için bir imza:
- yapı: algısal karma (pHash, 64 bit): 32×32 gri karenin DCT'sinin sol üst 8×8'i, ortancaya göre bit; iki kare 1 − Hamming / 64.
- ton: CIELAB açıklık (L*) histogramı, 8 bölme (filmin ışık düzeni: gece, gündüz, kâğıt beyazı).
- doygunluk: kroma (C*) histogramı, 5 bölme (soluk, pastel, canlı).
- renk: renk tonu (h°) histogramı, 12 bölme, kromayla ağırlıklı (gri pikseller renk sayılmaz).
İki kare arasında histogramlar kesişir (0–1), yapı pHash benzerliğidir (0,5 = ilgisiz iki kare → 0, 1 → 1):
  kare benzerliği = 0,4 · ton + 0,2 · doygunluk + 0,2 · renk + 0,2 · yapı
İki küme (A: bu film, B: öteki film ya da kart) arasında, iki yönlü: A'nın her karesi için B'deki en benzer kare (ortalama) ile
B'nin her karesi için A'daki en benzer karenin ortalaması. Film ortalaması alınmaz: çok renkli bir filmin ortalama histogramı her şeye
benzer.
ESIK eski filmler üzerinde ayarlandı: iki "İyilik Soğuk Geçirmez" filmi (ihh_kis_yardimi_icin ↔ kil_kamp) eşiğin üstünde,
ilgisiz filmler (ihh_sofra ↔ kil_kamp vb.) altında (yol-haritasi/2b-kanca-ve-izleyici.md → Uygulama notu).
Deneme (deneme_*) ve arşiv filmleri karşılaştırmaya girmez; aynı seri ya da marka kitini paylaşan film, filmin kullandığı ya da
filmden türetilen katalog kartı "beklenen" benzerliktir (⚠️ vermez, not düşülür).
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

import ortak as O

ESIK = 0.45
OK, WARN = "✅", "⚠️"
ONBELLEK = O.ROOT / "out" / "_benzerlik" / "imza.json"
KATALOG = O.ROOT / "katalog"


def _dct(n: int) -> np.ndarray:
    k = np.arange(n)
    M = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n)) * np.sqrt(2 / n)
    M[0] /= np.sqrt(2)
    return M


_D32 = _dct(32)
_BELLEK: dict | None = None


def _lab(rgb: np.ndarray):
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    X = (c @ np.array([0.4124, 0.3576, 0.1805])) / 0.95047
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    Z = (c @ np.array([0.0193, 0.1192, 0.9505])) / 1.08883
    f = lambda t: np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)  # noqa: E731
    return 116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))


def _oran(h: np.ndarray) -> list:
    s = h.sum()
    return (h / s if s > 0 else np.full(len(h), 1 / len(h))).round(5).tolist()


def _imza_hesapla(p: Path) -> dict:
    im = Image.open(p).convert("RGB")
    g = np.asarray(im.convert("L").resize((32, 32), Image.LANCZOS), dtype=np.float64)
    c = (_D32 @ g @ _D32.T)[:8, :8].ravel()
    bits = c > np.median(c[1:])  # doğru akım (c[0]) ortancaya girmez
    L, a, b = _lab(np.asarray(im.resize((96, 96), Image.BILINEAR), dtype=np.float64))
    C, H = np.hypot(a, b), (np.degrees(np.arctan2(b, a)) + 360) % 360
    return {"p": int("".join("1" if b else "0" for b in bits), 2),
            "t": _oran(np.histogram(L, bins=8, range=(0, 100))[0].astype(float)),
            "c": _oran(np.histogram(C, bins=[0, 8, 18, 30, 45, 1000])[0].astype(float)),
            "h": _oran(np.histogram(H, bins=12, range=(0, 360), weights=np.clip((C - 8) / 30, 0, 1))[0])}


def imza(p: Path) -> dict:
    """Karenin imzası (önbellekli: yol + değişme zamanı + boyut)."""
    global _BELLEK
    if _BELLEK is None:
        try:
            _BELLEK = json.loads(ONBELLEK.read_text())
        except (OSError, ValueError):
            _BELLEK = {}
    st = p.stat()
    k = f"{p.resolve()}|{st.st_mtime_ns}|{st.st_size}"
    if k not in _BELLEK:
        _BELLEK[k] = _imza_hesapla(p)
        try:
            ONBELLEK.parent.mkdir(parents=True, exist_ok=True)
            ONBELLEK.write_text(json.dumps(_BELLEK))
        except OSError:
            pass
    return _BELLEK[k]


AGIRLIK = {"ton": 0.4, "doygunluk": 0.2, "renk": 0.2, "yapi": 0.2}
_HIS = {"ton": "t", "doygunluk": "c", "renk": "h"}


def _matris(A: list[dict], B: list[dict]) -> dict:
    """Bileşenlerin kare × kare matrisleri (|A| × |B|)."""
    m = {k: np.minimum(np.array([a[h] for a in A])[:, None, :], np.array([b[h] for b in B])[None, :, :]).sum(axis=2) for k, h in _HIS.items()}
    pa, pb = np.array([a["p"] for a in A], dtype=np.uint64), np.array([b["p"] for b in B], dtype=np.uint64)
    x = pa[:, None] ^ pb[None, :]
    ham = sum(((x >> np.uint64(i)) & np.uint64(1)).astype(np.int64) for i in range(64))
    m["yapi"] = np.clip((1 - ham / 64 - 0.5) / 0.5, 0, None)
    m["skor"] = sum(AGIRLIK[k] * m[k] for k in AGIRLIK)
    return m


def skor(A: list[dict], B: list[dict]) -> dict:
    """A ile B kümelerinin benzerliği, iki yönlü kare kare: {skor, ton, doygunluk, renk, yapi} (hepsi 0–1; bileşenler en benzer
    kare çiftlerinin ortalaması)."""
    m = _matris(A, B)
    ia, ib = m["skor"].argmax(axis=1), m["skor"].argmax(axis=0)
    return {k: float((m[k][np.arange(len(A)), ia].mean() + m[k][ib, np.arange(len(B))].mean()) / 2) for k in ("skor", *AGIRLIK)}


def _esit_aralik(L: list, n: int) -> list:
    return L if len(L) <= n else [L[round(i * (len(L) - 1) / (n - 1))] for i in range(n)]


def film_kareleri(v: O.Video, en_cok: int = 8) -> list[Path]:
    """Filmin temsilî kareleri: inceleme/temsili (her format) > son inceleme kareleri (eşit aralıklı) > seçilen yolun ya da görünüşün kanca karesi."""
    kok = v.dir / "inceleme"
    k = sorted(kok.glob("temsili/kareler*/f*.png"))
    if k:
        return _esit_aralik(k, 3 * en_cok)
    rd = O.latest_review_dir(v)
    if rd:
        k = sorted(rd.glob("kareler*/f*.png"))
        if k:
            return _esit_aralik(k, en_cok)
    sec = (v.gorunus_json() or {}).get("secim") if v.gorunus_modu == "video" else None
    if sec:
        return [max(d.glob("f*.png"), key=lambda p: p.stat().st_mtime) for d in sorted(kok.glob(f"gorunus/{sec}-*")) if list(d.glob("f*.png"))]
    return []


def poster_karesi(v: O.Video) -> Path | None:
    """Filmin bir poster karesi (kör eleştirinin karşılaştırma klasörü için): son teslim posteri > son temsilî kare > son kare."""
    ps = sorted(O.KANAL.glob(f"cikti/{v.id}*_v*_poster.png"), key=lambda p: p.stat().st_mtime)
    if ps:
        return ps[-1]
    k = film_kareleri(v)
    return k[-1] if k else None


def karsilastirilir(w: O.Video) -> bool:
    """Karşılaştırmaya giren film: deneme (deneme_*) ve arşivdeki filmler hariç."""
    return not w.id.startswith("deneme_") and not w.script.get("arsiv")


def oteki_filmler(v: O.Video | None):
    for d in sorted((O.ROOT / "videos").iterdir()):
        if not d.is_dir() or (v is not None and d.name == v.id) or not (d / "script.json").exists():
            continue
        try:
            w = O.load(d.name)
        except SystemExit:
            continue
        if karsilastirilir(w):
            yield w


def kullandigi_kartlar(v: O.Video) -> set[str]:
    """Filmin kullandığı katalog kartları ("gorsel/<ad>", "animasyon/<ad>"): aynen, esin ya da görünüşün katalog stili."""
    out = set()
    kat, esin = v.script.get("katalog") or {}, v.script.get("esin") or {}
    for t in ("gorsel", "animasyon"):
        x = kat.get(t)
        for ad in ([x] if isinstance(x, str) else (x or {}).get("kartlar", []) if isinstance(x, dict) else []):
            out.add(f"{t}/{ad}")
        for ad in esin.get(t) or []:
            out.add(f"{t}/{ad}")
    G = v.gorunus_json() or {}
    for ad in [G.get("katalog_stili")] + list(G.get("esin_stilleri") or []):
        if ad:
            out.add(f"gorsel/{ad}")
    return out


def katalog_kartlari() -> list[dict]:
    """Onaylı katalog kartlarının önizleme kareleri: görüntü stillerinin her varyasyonu ayrı, hareket tiplerinin poster karesi."""
    out = []
    for t, desen in (("gorsel", "{ad}-*.png"), ("animasyon", "{ad}.png")):
        for f in sorted((KATALOG / t).glob("*.json")):
            d = O.jload(f)
            if d.get("durum") == "taslak":
                continue
            for p in sorted((KATALOG / "onizleme" / t).glob(desen.format(ad=f.stem))):
                harf = p.stem[len(f.stem) + 1:] if t == "gorsel" else ""
                if t == "gorsel" and len(harf) != 1:
                    continue
                ad = f"{f.stem}" + (f" {harf.upper()}" if harf else "") + f" {'görüntü' if t == 'gorsel' else 'hareket'} kartı"
                out.append({"anahtar": f"{t}/{f.stem}", "etiket": ad, "yonelme": ad + "na", "kaynak": d.get("kaynak", "katalog"), "kareler": [p]})
    return out


def en_yakin(v: O.Video, kareler: list[Path] | None = None, n: int = 3) -> tuple[list[dict], int]:
    """Bu filmin (ya da verilen karelerin) en yakın n eşleşmesi ve karşılaştırılan küme sayısı.
    Her eşleşme: {etiket, yonelme ("… filmine", "… kartına"), tur, skor, ton, doygunluk, renk, yapi, beklenen (not ya da "")}."""
    A = [imza(p) for p in (kareler if kareler is not None else film_kareleri(v))]
    if not A:
        return [], 0
    kullan = kullandigi_kartlar(v)
    adaylar = []
    for w in oteki_filmler(v):
        k = film_kareleri(w)
        if not k:
            continue
        bek = []
        if v.seri_anahtari and w.seri_anahtari == v.seri_anahtari:
            bek.append(f"aynı seri ({v.seri_anahtari})")
        if v.script.get("marka") and w.script.get("marka") == v.script.get("marka"):
            bek.append(f"aynı marka kiti ({v.script['marka']})")
        adaylar.append({"etiket": f"{w.id} filmi", "yonelme": f"{w.id} filmine", "tur": "film", "kareler": k, "beklenen": ", ".join(bek)})
    for c in katalog_kartlari():
        bek = "filmin kullandığı kart" if c["anahtar"] in kullan else ("bu filmden türetildi" if c["kaynak"] == f"film:{v.id}" else "")
        adaylar.append({"etiket": c["etiket"], "yonelme": c["yonelme"], "tur": "kart", "kareler": c["kareler"], "beklenen": bek})
    for a in adaylar:
        a.update(skor(A, [imza(p) for p in a.pop("kareler")]))
    adaylar.sort(key=lambda a: -a["skor"])
    return adaylar[:n], len(adaylar)


def satir(v: O.Video, kareler: list[Path] | None = None) -> tuple[str, str, str] | None:
    """Ölçüm satırı (değer, durum, kanıt) ya da None (filmin karesi yok). Eşiğin üstünde beklenmeyen eşleşme ⚠️."""
    E, toplam = en_yakin(v, kareler)
    if not E:
        return None
    yaz = lambda a: f"{a['etiket']} {a['skor']:.2f}" + (f" (beklenen: {a['beklenen']})" if a["beklenen"] and a["skor"] >= ESIK else "")  # noqa: E731
    kotu = [a for a in E if a["skor"] >= ESIK and not a["beklenen"]]
    kanit = ("; ".join(f"{a['yonelme']} çok benziyor (ton {a['ton']:.2f}, doygunluk {a['doygunluk']:.2f}, renk {a['renk']:.2f}, yapı {a['yapi']:.2f})"
                       for a in kotu) or f"{toplam} film ve kart karesiyle karşılaştırıldı")
    return " · ".join(yaz(a) for a in E), WARN if kotu else OK, kanit


def yol_yontemi(w: O.Video) -> str | None:
    """Filmin seçilen yolunun yöntemi (planda üç yol), normalleştirilmiş; yoksa None."""
    G = (w.gorunus_json() or {}) if w.gorunus_modu == "video" else {}
    y = ((G.get("secenekler") or {}).get(G.get("secim") or "") or {}).get("yol")
    if not isinstance(y, dict):
        return None
    return " ".join(O.norm_word(str(y.get("yontem") or "")).lower().split()) or None


def onceki_yontem(v: O.Video) -> tuple[str, str] | None:
    """Bu filmden önce yolu seçilen son filmin (id, yöntem): "aynı yöntemi art arda iki filmde kullanma" (referans/yontemler.md)."""
    gp = v.dir / "gorunus.json"
    sinir = gp.stat().st_mtime if gp.exists() else float("inf")
    L = [((w.dir / "gorunus.json").stat().st_mtime, w.id, y) for w in oteki_filmler(v) if (y := yol_yontemi(w)) and (w.dir / "gorunus.json").stat().st_mtime <= sinir]
    return max(L)[1:] if L else None
