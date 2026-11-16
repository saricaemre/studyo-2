"""Stüdyonun Blender kiti: sahne kodu (blender/<id>/sahne.py) bunu `import kit` ile kullanır. Kurallar: ../CLAUDE.md.

  ST, kare, saniye, isaret, renk, renk4,              veri.py   (stüdyonun verdiği format, işaretler, görünüş; zaman, renk, tohum,
  rastgele, varlik                                               videonun gerçek dosyaları)
  anahtar, fcurves, yumusat, dongu                     anim.py   (anahtar kare; Blender 5.x kanal çantası)
  nesne, bos, kure, koni, silindir, duzlem, doku,      model.py  (nesneler, ölçek serbest; pisir = paylaşılan ağ; serit = dörtgen şerit)
  kaydir, puruz, pisir, serit
  kil, kagit, plastik, metal, cam, boya, isik_malz     malzeme.py (malzeme ailesini görüntü stili seçer: kil/kâğıt maket yalnız biri)
  dunya, gunes, nokta, kamera, izle, guvenli_alan,     sahne.py   (kontur: çizgi film konturu, Freestyle)
  kontur
Çizim ayarları (motor, örnek sayısı, renk yönetimi, çözünürlük, çıktı) sahnenin değil çalıştırıcının işidir: calistir.py.
"""
from .anim import anahtar, dongu, fcurves, yumusat
from .malzeme import boya, cam, isik_malz, kagit, kil, metal, plastik
from .model import bos, doku, duzlem, kaydir, koni, kure, nesne, pisir, puruz, serit, silindir
from .sahne import dunya, guvenli_alan, gunes, izle, kamera, kontur, nokta
from .veri import ST, isaret, kare, rastgele, renk, renk4, saniye, varlik

__all__ = ["ST", "anahtar", "bos", "boya", "cam", "dongu", "doku", "dunya", "duzlem", "fcurves", "guvenli_alan", "gunes", "isaret", "isik_malz",
           "izle", "kagit", "kamera", "kare", "kaydir", "kil", "koni", "kontur", "kure", "metal", "nesne", "nokta", "pisir", "plastik", "puruz",
           "rastgele", "renk", "renk4", "saniye", "serit", "silindir", "varlik", "yumusat"]
