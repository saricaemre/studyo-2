"""Niyetli altyazının yazı tipi ölçü tablosu: değişken yazı tipinde (Roboto Flex) karakter genişlikleri, ağırlık × genişlik ızgarasında.

pipeline/niyet.py satırları bu tabloyla böler (iki motorda aynı satırlar, ölçüm de aynı tablodan); kelime_genisligi burada, bağımlılıksız.
Tablo yalnız yazı tipi dosyası değişince bir kez üretilir; çıktı public/fontlar/roboto-flex/olcu.json pakete girer. fontTools çalışma
zamanında gerekmez, yalnız üretirken:

  python3 -m venv /tmp/ft && /tmp/ft/bin/pip install fonttools brotli
  /tmp/ft/bin/python pipeline/yazi_olcu.py            # tabloyu yazar, ızgara dışı noktalarda ara değer hatasını basar

Ölçüler yazı tipi biriminde (upm); çekirdek aralığı (kerning) yok sayılır: tarayıcı çiftleri yaklaştırır, tablo genişliği biraz fazla
tahmin eder (güvenli yön).
"""
import json
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIZIN = ROOT / "public" / "fontlar" / "roboto-flex"
OLCU = DIZIN / "olcu.json"
DOSYALAR = ["roboto-flex-latin.woff2", "roboto-flex-latin-ext.woff2"]
OPSZ = 32       # sabit optik boyut: altyazı 64–100 px'te okunaklı aralık; genişlik boyutla değişmesin diye otomatik optik boyut kapalı
WGHT = list(range(300, 1001, 100))
WDTH = list(range(70, 131, 5))
KARAKTERLER = ("".join(chr(c) for c in range(32, 127)) + "ÇçĞğİıÖöŞşÜüÂâÎîÛûÊêÉéÈèÀàÄäËëÏïÑñÁáÍíÓóÚú"
               + "…’‘“”—–·«»€₺°×")


@lru_cache(maxsize=1)
def tablo() -> dict:
    return json.loads(OLCU.read_text())


def kelime_genisligi(metin: str, wght: float, wdth: float, T: dict | None = None) -> float:
    """Kelimenin genişliği, em. Izgara arası ikili doğrusal ara değer; tabloda olmayan karakter "n" genişliğinde sayılır."""
    T = T or tablo()
    W, D, G = T["wght"], T["wdth"], T["genislik"]
    wght = min(max(wght, W[0]), W[-1])
    wdth = min(max(wdth, D[0]), D[-1])
    i = min(bisect_right(W, wght) - 1, len(W) - 2)
    j = min(bisect_right(D, wdth) - 1, len(D) - 2)
    a = (wght - W[i]) / (W[i + 1] - W[i])
    b = (wdth - D[j]) / (D[j + 1] - D[j])
    n = len(D)
    toplam = 0.0
    for c in metin:
        g = G.get(c) or G["n"]
        v00, v01, v10, v11 = g[i * n + j], g[i * n + j + 1], g[(i + 1) * n + j], g[(i + 1) * n + j + 1]
        toplam += (1 - a) * ((1 - b) * v00 + b * v01) + a * ((1 - b) * v10 + b * v11)
    return toplam / T["upm"]


def main():
    from fontTools.ttLib import TTFont
    fontlar = [TTFont(DIZIN / d) for d in DOSYALAR]
    upm = fontlar[0]["head"].unitsPerEm
    sahip = {}
    for f in fontlar:
        for kod, ad in f.getBestCmap().items():
            sahip.setdefault(kod, (f, ad))
    eksik = [c for c in KARAKTERLER if ord(c) not in sahip]
    if eksik:
        raise SystemExit(f"Yazı tipinde olmayan karakterler: {''.join(eksik)}")

    def olc(c, w, d):
        f, ad = sahip[ord(c)]
        return f.getGlyphSet(location={"opsz": OPSZ, "wght": w, "wdth": d, "GRAD": 0})[ad].width

    tablo_ = {c: [round(olc(c, w, d)) for w in WGHT for d in WDTH] for c in KARAKTERLER}
    out = {"aile": "Roboto Flex", "lisans": "OFL-1.1", "upm": upm, "opsz": OPSZ, "wght": WGHT, "wdth": WDTH, "genislik": tablo_}
    OLCU.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(tablo_)} karakter × {len(WGHT)}×{len(WDTH)} → {OLCU}")
    en = 0.0  # ara değer hatası: ızgara dışı noktalarda tam ölçü ile tablo
    for kelime in ("fısıldıyorum.", "Dede!", "Kardan", "ŞİMDİ", "yağıyor", "Söz", "uyuyor.", "İĞNE"):
        for w, d in ((437, 93), (812, 77), (655, 118), (333, 101), (888, 84)):
            tam = sum(olc(c, w, d) for c in kelime)
            en = max(en, abs(kelime_genisligi(kelime, w, d, out) * upm - tam) / tam)
    print(f"en büyük ara değer hatası: %{en * 100:.2f}")


if __name__ == "__main__":
    main()
