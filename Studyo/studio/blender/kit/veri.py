"""Stüdyonun sahneye verdiği veri (HyperFrames'teki window.ST karşılığı) ve zaman, renk, tohum yardımcıları.

Veriyi stüdyo yazar (pipeline/blender.py → veri()); sahne yalnız okur:
  ST.format, ST.w, ST.h, ST.fps, ST.sure, ST.nkare      format ve süre (nkare = Remotion'un kare sayısı)
  ST.isaretler {ad: saniye}                             cues.json'dan (kural 9: olay saatleri yalnız buradan)
  ST.vuruslar [{id, step, start, end}] · ST.kelimeler · ST.beats (müzik ızgarası)
  ST.guvenli, ST.altyazi                                formatın güvenli alanı (oran): yazı Remotion'da, ama kadraj buna göre kurulur
  ST.gorunus (seçili görünüş seçeneği) · ST.renk {ad: '#rrggbb'} · ST.marka (marka kiti renkleri ya da None)
  ST.tohum                                              videonun tohumu (script.json → blender.tohum)
"""
import random
from pathlib import Path

SURUM_ALANLARI = ("id", "format", "w", "h", "fps", "sure", "nkare", "isaretler", "vuruslar", "kelimeler", "beats", "guvenli", "altyazi",
                  "gorunus", "renk", "marka", "tohum")


class _Veri:
    def __init__(self):
        self._d = {}

    def yukle(self, d: dict):
        eksik = [k for k in SURUM_ALANLARI if k not in d]
        if eksik:
            raise SystemExit(f"Sahne verisinde eksik alan: {', '.join(eksik)} (pipeline/blender.py → veri)")
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

    @property
    def oran(self) -> float:
        return self._d["w"] / self._d["h"]


ST = _Veri()


def kare(t: float) -> float:
    """saniye → Blender karesi. Blender 1'den sayar: Remotion'un f. karesi (t = f / fps) Blender'da f + 1'dir."""
    return 1 + t * ST.fps


def saniye(f: float) -> float:
    """Blender karesi → saniye."""
    return (f - 1) / ST.fps


def isaret(ad: str, ofset: float = 0.0) -> float:
    """cues.json'daki işaretin saniyesi (+ ofset). Sahne olay saatlerini yalnız buradan alır (CLAUDE.md kural 9)."""
    if ad not in ST.isaretler:
        raise SystemExit(f"İşaret yok: {ad} (cues.json'daki işaretler: {', '.join(sorted(ST.isaretler)) or 'hiçbiri'})")
    return ST.isaretler[ad] + ofset


def _dogrusal(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def renk(x, parlaklik: float = 1.0, yedek: str | None = None) -> tuple:
    """Görünüşün rengi → Blender'ın doğrusal RGB'si. x: görünüşteki renk adı ('kar', 'vurgu' …), '#rrggbb' ya da hazır (r, g, b).
    Malzemelerin rengi görünüşten gelir: üç görünüş gerçekten farklı çıksın diye sahneye sabit renk serpiştirilmez.
    yedek: görünüş henüz yazılmadıysa kullanılacak '#rrggbb' (yalnız iskelette; seçeneklere eklenince kaldır)."""
    if isinstance(x, (tuple, list)):
        return tuple(float(c) * parlaklik for c in x[:3])
    h = x
    if not str(x).startswith("#"):
        R = ST.renk or {}
        if x not in R and not yedek:
            raise SystemExit(f"Görünüşte renk yok: '{x}' (gorunus.json → seçeneğin renk alanına ekle; var: {', '.join(sorted(R))})")
        h = R.get(x, yedek)
    return tuple(_dogrusal(int(h[i:i + 2], 16) / 255) * parlaklik for i in (1, 3, 5))


def renk4(x, parlaklik: float = 1.0) -> tuple:
    return (*renk(x, parlaklik), 1.0)


def rastgele(n: int = 0) -> random.Random:
    """Videonun tohumundan türeyen üreteç. Tohumsuz random.random() / numpy.random yasaktır (./st tip tarar): her kare t'nin saf fonksiyonu."""
    return random.Random(ST.tohum * 7919 + n)


def varlik(ad: str) -> Path:
    """Videonun gerçek dosyası (public/<id>/varliklar/<ad>): doku, görsel, ses dışı model. Her biri videos/<id>/varliklar.md'de
    kaynağı ve onayıyla listelenir; eksikse iş durur (CLAUDE.md kural 2: inandırıcı bir sahtesi üretilmez)."""
    p = Path(__file__).resolve().parents[2] / "public" / ST.id / "varliklar" / ad
    if not p.exists():
        raise SystemExit(f"Varlık yok: {p} (videos/{ST.id}/varliklar.md'ye ekle, dosyayı public/{ST.id}/varliklar/'a koy)")
    return p
