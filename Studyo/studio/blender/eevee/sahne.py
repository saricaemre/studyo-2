"""EEVEE çizerinin sarmalayıcısı: kitin çalıştırıcısı (kit/calistir.py) bunu sahne diye çalıştırır; asıl sahne ST_SAHNE ortam değişkeninde
(pipeline/blender.py → _calistir). Sıra: çizer EEVEE + sanat varsayılanları → asıl sahne (kendi klasöründe, Cycles'takiyle aynı) →
kit malzemeleri EEVEE'ye uyarlanır (cam, ince bez) → EEVEE kalitesi zorlanır. Ardından çalıştırıcının zorla()'sı çözünürlüğü, PNG'yi ve örnek sayısını sabitler.
"""
import os
import runpy
import sys
from pathlib import Path

import bpy

import eevee

if "ST_SAHNE" not in os.environ:
    raise SystemExit("EEVEE sarmalayıcısı asıl sahneyi bilmiyor (ST_SAHNE): plakaları ./st çizer (pipeline/blender.py)")
asil = Path(os.environ["ST_SAHNE"]).resolve()
K = eevee.kalite()
eevee.varsayilan(bpy.context.scene)
os.chdir(asil.parent)
sys.path.insert(0, str(asil.parent))
runpy.run_path(str(asil), run_name="__sahne__")
eevee.uyarla()
eevee.zorla(bpy.context.scene, K)
