"""Stüdyonun Manim kiti (oturum 6c): karma filmin Manim sahnesi (manim/<id>/sahneler/<ad>/sahne.py) bunu `import kit` ile kullanır.
Kurallar: ../CLAUDE.md. Sahneyi stüdyo çizer (pipeline/manim_kopru.py, Manim Community 0.22.1, Cairo çizeri; OpenGL yok).

  ST                         stüdyonun verisi (YEREL zaman: 0 = sahnenin çizim aralığının başı; pipeline/plaka.py):
                             format, w, h, fps, sure, nkare, isaretler, vuruslar, beats, guvenli, renk, gorunus, sahne, fontlar, tohum
  renk(ad)                   görünüşün rengi (ManimColor): sahneye sabit renk serpiştirilmez
  yazi(metin, rol, px)       görünüşün yazı tipiyle Text (Pango; woff2 → TTF, Türkçe harfler dahil); px: CSS'teki gibi yazı boyu (≥ 64)
  px(n), birim()             piksel ↔ Manim birimi (yerleşim formata göre: ST.dikey, ST.guvenli; merkezden kırpma yok)
  kare(t), kare_sayisi(s)    saniye → kare (yarım yukarı) · şimdiye dek yazılan kare
  oyna(s, *anim, kare=n)     animasyon tam n kare (Manim'in run_time'ı yuvarlama yüzünden bir kare kaçırabilir: kit sayar ve denetler)
  bekle(s, n) · isarete_kadar(s, "ad") · sona_kadar(s)   zaman yalnız işaretlerden (kural 9); sahne sona_kadar ile biter (kare sayısı = pencere)
  rastgele(n)                tohumlu üreteç (random, time, datetime, tohumsuz numpy yok: ./st tip tarar)
"""
import json
import math
import os
import random
from pathlib import Path

import manimpango
from manim import Text, config
from manim.utils.color import ManimColor


class _Veri:
    def __init__(self):
        self._d = {}

    def yukle(self, d: dict):
        self._d = dict(d)

    def __getattr__(self, k):
        if k.startswith("_"):
            raise AttributeError(k)
        try:
            return self._d[k]
        except KeyError:
            raise AttributeError(f"ST.{k} yok (alanlar: {', '.join(sorted(self._d))})") from None

    @property
    def dikey(self) -> bool:
        return self._d["h"] > self._d["w"]


ST = _Veri()
if "ST_VERI" not in os.environ:
    raise SystemExit("Manim sahnesinin verisi yok (ST_VERI): plakaları ./st çizer (pipeline/manim_kopru.py)")
ST.yukle(json.loads(Path(os.environ["ST_VERI"]).read_text()))

# Çözünürlük ve kare hızı komut satırından (-r, --fps). Manim -r ile çerçevenin en-boy oranını güncellemiyor (14,22 × 8 birim kalıyor;
# dikey formatta görüntü yassılırdı): çerçeve yüksekliği 8 birim, genişliği formatın oranında. Arka plan görünüşten (saydam sahnede -t).
config.frame_height = 8.0
config.frame_width = 8.0 * ST.w / ST.h
if not ST.saydam:
    config.background_color = ManimColor((ST.renk or {}).get("arka", "#000000"))
for _rol, _f in (ST.fontlar or {}).items():
    manimpango.register_font(_f["dosya"])

def renk(ad: str, yedek: str | None = None) -> ManimColor:
    """Görünüşün rengi (gorunus.json → seçeneğin renk alanı) ya da '#rrggbb'."""
    if str(ad).startswith("#"):
        return ManimColor(ad)
    R = ST.renk or {}
    if ad not in R and not yedek:
        raise SystemExit(f"Görünüşte renk yok: '{ad}' (var: {', '.join(sorted(R))})")
    return ManimColor(R.get(ad, yedek))


def birim() -> float:
    """Bir pikselin Manim birimi (çerçeve yüksekliği config.frame_height birim = ST.h piksel)."""
    return config.frame_height / config.pixel_height


def px(n: float) -> float:
    return n * birim()


def yazi(metin: str, rol: str = "govde", px_: float = 64, renk_: str | ManimColor = "murekkep", **k) -> Text:
    """Görünüşün yazı tipiyle yazı. px_: CSS'teki font-size gibi (büyük harf yüksekliği = px_ · capHeight/em; tarayıcıyla aynı ölçü).
    Ekranda okunan yazı ≥ 64 px (zanaat.md)."""
    F = (ST.fontlar or {}).get(rol) or (ST.fontlar or {}).get("govde")
    if not F:
        raise SystemExit("Görünüşün yazı tipi yok (ST.fontlar)")
    # aile adı ağırlığa özel ("Inter ST500", pipeline/manim_kopru.py → _statik): Pango'ya ağırlık adla değil aileyle verilir
    ref = Text("H", font=F["aile"], font_size=100)
    olcek = (px_ * F["cap"]) / (ref.height / birim())
    t = Text(metin, font=F["aile"], font_size=100, color=renk(renk_) if isinstance(renk_, str) else renk_, **k)
    return t.scale(olcek)


def kare(t: float) -> int:
    """Yerel saniye → kare (yarım yukarı; pipeline/gecis.py → kare_no ile aynı)."""
    return int(math.floor(t * ST.fps + 0.5))


def kare_sayisi(sahne) -> int:
    """Şimdiye dek yazılan kare (Cairo çizicisinin zamanından)."""
    return int(round(sahne.renderer.time * ST.fps))


def _denetle(sahne, beklenen: int, ne: str):
    k = kare_sayisi(sahne)
    if k < beklenen:   # Manim kısa bıraktıysa (yuvarlama) son kare tekrarlanır
        sahne.wait((beklenen - k + 0.5) / ST.fps, frozen_frame=True)
        k = kare_sayisi(sahne)
    if k != beklenen:
        raise SystemExit(f"{ne}: {k} kare yazıldı, beklenen {beklenen} (kit.oyna / kit.bekle kullan)")


def oyna(sahne, *animasyon, kare: int, **k):
    """Animasyon tam `kare` kare: ilk karesi alfa 0'dır (Remotion'daki prog(t, işaret, …) ile aynı: işaret karesinde hareket başlar)."""
    if kare < 1:
        raise SystemExit("kit.oyna: kare ≥ 1")
    bas = kare_sayisi(sahne)
    sahne.play(*animasyon, run_time=(kare - 0.5) / ST.fps, **k)   # np.arange(0, run_time, 1/fps) → tam `kare` örnek
    _denetle(sahne, bas + kare, "kit.oyna")


def bekle(sahne, kare: int):
    """Tam `kare` kare durgun (güncelleyici varsa sahne güncellenir)."""
    if kare <= 0:
        return
    bas = kare_sayisi(sahne)
    # donmuş olmayan bekleme her kareyi çizer (güncelleyiciler çalışır): np.arange(0, (n − 0,5)/fps, 1/fps) → tam n kare
    sahne.wait((kare - 0.5) / ST.fps, frozen_frame=False)
    _denetle(sahne, bas + kare, "kit.bekle")


def isarete_kadar(sahne, ad: str, ofset: float = 0.0):
    """İşaretin karesine kadar bekler: sonraki oyna() işaretin karesinde başlar (kural 9: zaman işaretten)."""
    if ad not in ST.isaretler:
        raise SystemExit(f"İşaret yok: {ad} (var: {', '.join(sorted(ST.isaretler))})")
    hedef = kare(ST.isaretler[ad] + ofset)
    k = kare_sayisi(sahne)
    if hedef < k:
        raise SystemExit(f"İşaret {ad} (kare {hedef}) geçildi: sahne zaten {k}. karede (önceki animasyonları kısalt)")
    bekle(sahne, hedef - k)


def sona_kadar(sahne):
    """Sahnenin son karesine kadar: plaka sayısı çizim aralığıyla aynı olmalı (ST.nkare)."""
    k = kare_sayisi(sahne)
    if k > ST.nkare:
        raise SystemExit(f"Sahne {k} kare, çizim aralığı {ST.nkare} kare: animasyonlar sığmıyor")
    bekle(sahne, ST.nkare - k)


def rastgele(n: int = 0) -> random.Random:
    return random.Random(int(ST.tohum) * 7919 + n)
