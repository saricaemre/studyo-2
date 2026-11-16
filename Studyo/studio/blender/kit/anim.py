"""Anahtar kare yardımcıları (Blender 5.x: f-eğrileri eylemin kanal çantasında)."""
from bpy_extras import anim_utils

from .veri import kare


def fcurves(o):
    """Nesnenin (ya da veri bloğunun) f-eğrileri. Blender 5.x'te action.fcurves yok: eylem yuvasının kanal çantasından okunur."""
    a = o.animation_data
    if not a or not a.action:
        return []
    return anim_utils.action_get_channelbag_for_slot(a.action, a.action_slot).fcurves


def anahtar(hedef, yol: str, deger, t: float, indeks: int = -1, ara: str = "BEZIER"):
    """hedef.yol = deger, t saniyesinde anahtar kare (ara: BEZIER, LINEAR, SINE, CONSTANT …).
    hedef bir nesne, ışık, malzeme düğümünün girişi (node.inputs['Strength']) olabilir."""
    if indeks >= 0:
        getattr(hedef, yol)[indeks] = deger
    else:
        setattr(hedef, yol, deger)
    hedef.keyframe_insert(yol, index=indeks, frame=kare(t))
    for fc in fcurves(hedef.id_data):
        for k in fc.keyframe_points:
            if abs(k.co.x - kare(t)) < 1e-6 and fc.data_path.endswith(yol):
                k.interpolation = ara


def yumusat(o, ara: str = "SINE", kolay: str = "EASE_IN_OUT"):
    """Nesnenin bütün anahtarlarını aynı eğriyle yumuşatır (kamera ve hedef için)."""
    for fc in fcurves(o):
        for k in fc.keyframe_points:
            k.interpolation = ara
            k.easing = kolay


def dongu(o, kolay: str | None = "EASE_IN_OUT"):
    """Nesnenin eğrilerini sonsuz tekrarlar (kar yağışı, nefes). Döngü de t'nin saf fonksiyonudur."""
    for fc in fcurves(o):
        fc.modifiers.new("CYCLES")
        if kolay:
            for kp in fc.keyframe_points:
                kp.easing = kolay
