"""Karma filmin SAYDAM Blender sahnesinin sarmalayıcısı (oturum 6b, pipeline/plaka.py): kitin çalıştırıcısı (kit/calistir.py) bunu sahne diye
çalıştırır; asıl sahne ST_KARMA_SAHNE ortam değişkeninde. Sıra: asıl sahne (kendi klasöründe) → film_transparent → çalıştırıcının zorla()'sı
(çözünürlük, 8 bit PNG) → her çizimden önce RGBA (render_pre; zorla() RGB yazar, kit'e dokunulmadı: kit bütün Blender filmlerinin parmak izinde).
Yalnız `"saydam": true` sahnenin parmak izine girer. EEVEE'de zincir: eevee/sahne.py → bu dosya → asıl sahne.
"""
import os
import runpy
import sys
from pathlib import Path

import bpy

if "ST_KARMA_SAHNE" not in os.environ:
    raise SystemExit("Saydam sahne sarmalayıcısı asıl sahneyi bilmiyor (ST_KARMA_SAHNE): plakaları ./st çizer (pipeline/plaka.py)")
asil = Path(os.environ["ST_KARMA_SAHNE"]).resolve()
os.chdir(asil.parent)
sys.path.insert(0, str(asil.parent))
runpy.run_path(str(asil), run_name="__sahne__")
bpy.context.scene.render.film_transparent = True


def _rgba(sahne, *_):
    sahne.render.image_settings.color_mode = "RGBA"


bpy.app.handlers.render_pre.append(_rgba)
