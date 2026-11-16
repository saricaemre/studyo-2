"""Yapım filmi ("nasıl yapıldı", ./st yapim) için Blender geçişleri: kitin çalıştırıcısı (kit/calistir.py) bunu sahne diye çalıştırır,
asıl sahne ST_SAHNE ortam değişkeninde (pipeline/blender.py → yapim_plakalari). Kitin ve filmin dışında durur: bir filmin taslak ve tam
plakalarının parmak izine girmez, yalnız yapım kümelerinin (<format>-yapim_<kip>-<özet>) parmak izine girer.

Kipler (ST_YAPIM_KIP):
  kil  sahnenin bütün nesneleri tek bir kil renginde (Workbench: stüdyo ışığı, oyuk gölgesi, gölge). Işık ve malzemeden önceki hâl.
  tel  tel kafes: sahnenin geometrisi çizgi olarak (Workbench, wireframe).
  ust  kamera yolu: sahne kuşbakışı (yükseltilmiş açı), filmin kamerasının bütün film boyunca izlediği yol bir çizgi, o karedeki kamera
       küçük bir piramit. Yol ve piramit filmin kamerasından kare kare örneklenir (kamera anahtar karelidir: t'nin saf fonksiyonu).
Sıra: (EEVEE filminde EEVEE varsayılanları: yalnız EEVEE'de çalışan çağrılar sahneyi durdurmasın) → asıl sahne → Workbench + kip ayarları.
Ardından çalıştırıcının zorla()'sı çözünürlüğü ve PNG'yi sabitler (Workbench'e dokunmaz). Zaman yalnız karelerden; rastgelelik yok.
"""
import math
import os
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

import kit

if "ST_SAHNE" not in os.environ or "ST_YAPIM_KIP" not in os.environ:
    raise SystemExit("Yapım sarmalayıcısı asıl sahneyi ya da kipi bilmiyor (ST_SAHNE, ST_YAPIM_KIP): plakaları ./st yapim çizer")
asil = Path(os.environ["ST_SAHNE"]).resolve()
KIP = os.environ["ST_YAPIM_KIP"]
if KIP not in ("kil", "tel", "ust"):
    raise SystemExit(f"Yapım kipi yok: {KIP} (kil | tel | ust)")

KIL = (0.62, 0.60, 0.57)        # kil grisi (doğrusal)
ZEMIN = (0.045, 0.047, 0.055)   # arka plan (doğrusal; koyu antrasit)
VURGU = (1.0, 0.36, 0.08)       # kamera yolu ve piramit (turuncu; doğrusal)

if os.environ.get("ST_CIZER") == "eevee":   # yalnız EEVEE'de çalışan sahne çağrıları (eevee.hucre) dursun diye önce EEVEE
    import eevee
    eevee.varsayilan(bpy.context.scene)
os.chdir(asil.parent)
sys.path.insert(0, str(asil.parent))
runpy.run_path(str(asil), run_name="__sahne__")

sc = bpy.context.scene
kam = sc.camera
if kam is None:
    raise SystemExit("Sahnede kamera yok")


def _kamera_yolu():
    """Filmin kamerasının her karedeki dünya matrisi (kısıtlar ve anahtar kareler dahil)."""
    yol = []
    for f in range(kit.ST.nkare):
        sc.frame_set(f + 1)
        yol.append(kam.matrix_world.copy())
    sc.frame_set(1)
    return yol


def _gorunen_kutu():
    """Görünür ağların dünya uzayındaki köşeleri (değerlendirilmiş) → (en küçük, en büyük)."""
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for o in sc.objects:
        if o.type != "MESH" or not o.visible_get():
            continue
        oe = o.evaluated_get(dg)
        for c in oe.bound_box:
            p = oe.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, p))
            hi = Vector(map(max, hi, p))
    return lo, hi


def _yol_cizgisi(noktalar, kalinlik, renk=VURGU, ad="yapim_kamera_yolu", ilerle=False):
    """Kameranın yolu: kalın eğri. ilerle: çizgi kendini çizer (o karede kameranın geldiği yere kadar; bevel_factor_end her kareye anahtar)."""
    cu = bpy.data.curves.new(ad, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = kalinlik
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(noktalar) - 1)
    for p, n in zip(sp.points, noktalar):
        p.co = (n.x, n.y, n.z, 1.0)
    if ilerle:
        cu.bevel_factor_mapping_end = "SPLINE"
        son = max(1, len(noktalar) - 1)
        for f in range(len(noktalar)):
            cu.bevel_factor_end = max(0.002, f / son)
            cu.keyframe_insert("bevel_factor_end", frame=f + 1)
    o = bpy.data.objects.new(ad, cu)
    sc.collection.objects.link(o)
    o.color = (*renk, 1.0)
    return o


def _piramit(boy):
    """Kameranın küçük modeli: tepe kameranın yerinde, taban bakış yönünde (-Z), formatın en-boy oranında."""
    import bmesh
    en = boy * 0.62 * (kit.ST.w / max(kit.ST.w, kit.ST.h)) * 1.6
    yuk = boy * 0.62 * (kit.ST.h / max(kit.ST.w, kit.ST.h)) * 1.6
    bm = bmesh.new()
    tepe = bm.verts.new((0, 0, 0))
    kose = [bm.verts.new((sx * en / 2, sy * yuk / 2, -boy)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i in range(4):
        bm.faces.new((tepe, kose[i], kose[(i + 1) % 4]))
    bm.faces.new(list(reversed(kose)))
    me = bpy.data.meshes.new("yapim_kamera")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("yapim_kamera", me)
    sc.collection.objects.link(o)
    o.color = (*VURGU, 1.0)
    return o


def _ust_kurulum():
    """Kuşbakışı kamera: filmin kamerasının yolu ve baktığı yer kadrajda, yukarıdan ~55° eğik; yolun üstünde kalan (kadrajı kapatan) nesneler
    yakın kırpma düzlemiyle kesilir. Yol çizgisi ve piramit OBJECT renginde (turuncu), sahnenin geri kalanı kil."""
    yol = _kamera_yolu()
    noktalar = [m.translation.copy() for m in yol]
    # kameranın baktığı yer: odak uzaklığı (alan derinliği açıksa) ya da yol boyunun iki katı
    ilk = yol[0]
    odak = kam.data.dof.focus_distance if kam.data.dof.use_dof and kam.data.dof.focus_distance > 0 else 0.0
    if kam.data.dof.use_dof and kam.data.dof.focus_object is not None:
        odak = (kam.data.dof.focus_object.matrix_world.translation - ilk.translation).length
    yol_boy = max((max(p[i] for p in noktalar) - min(p[i] for p in noktalar)) for i in range(3))
    bak = []
    for m in yol[:: max(1, len(yol) // 12)]:
        ileri = (m.to_3x3() @ Vector((0, 0, -1))).normalized()
        bak.append(m.translation + ileri * (odak or max(yol_boy * 2, 0.05)))
    tum = noktalar + [n + (b - n) * 0.45 for b, n in zip(bak, noktalar[:: max(1, len(yol) // 12)])]   # bakılan yere doğru yarı yol: yol büyük görünsün
    lo = Vector((min(p.x for p in tum), min(p.y for p in tum), min(p.z for p in tum)))
    hi = Vector((max(p.x for p in tum), max(p.y for p in tum), max(p.z for p in tum)))
    merkez = (lo + hi) / 2
    olcu = max((hi - lo).length, 0.02)
    import json as _j
    print("ST_YAPIMUST " + _j.dumps({"yol_boy": yol_boy, "odak": odak, "olcu": olcu, "lo": list(lo), "hi": list(hi), "yol0": list(noktalar[0]), "yolN": list(noktalar[-1])}), flush=True)
    # yol, bakış yönünün arkasından ve yukarıdan görünsün: filmin ilk bakış yönünün tersinden 55° yükselerek
    ileri = (ilk.to_3x3() @ Vector((0, 0, -1)))
    yatay = Vector((ileri.x, ileri.y, 0))
    yatay = yatay.normalized() if yatay.length > 1e-6 else Vector((0, 1, 0))
    yon = (-yatay * math.cos(math.radians(55)) + Vector((0, 0, 1)) * math.sin(math.radians(55))).normalized()
    yon = (Matrix.Rotation(math.radians(-28), 3, "Z") @ yon).normalized()   # biraz yandan: yol derinlikte üst üste binmesin
    cd = bpy.data.cameras.new("yapim_ust")
    cd.lens = 35
    cd.sensor_fit = "AUTO"
    o = bpy.data.objects.new("yapim_ust", cd)
    sc.collection.objects.link(o)
    uzak = olcu * 0.48 / math.tan(cd.angle / 2)   # cd.angle: uzun kenarın açısı
    if kit.ST.h > kit.ST.w:   # dikey kadrajda kısa kenar (yatay) dardır
        uzak *= kit.ST.h / kit.ST.w * 0.75
    o.location = merkez + yon * uzak
    o.rotation_euler = (merkez - o.location).to_track_quat("-Z", "Y").to_euler()
    cd.clip_start = max(uzak * 0.35, 1e-4)
    cd.clip_end = uzak * 40
    sc.camera = o
    kalin = olcu * 0.012
    _yol_cizgisi(noktalar, kalin * 0.45, (0.34, 0.25, 0.2), "yapim_kamera_yolu_tum")   # bütün yol, soluk ve ince
    _yol_cizgisi(noktalar, kalin, ilerle=True)                                         # gelinen yer, turuncu ve kalın
    p = _piramit(olcu * 0.12)
    for f, m in enumerate(yol):   # piramit her karede filmin kamerasının yerinde ve yönünde (anahtar kare: t'nin saf fonksiyonu)
        p.matrix_world = m
        p.keyframe_insert("location", frame=f + 1)
        p.keyframe_insert("rotation_euler", frame=f + 1)
    for fc in kit.fcurves(p):
        for k in fc.keyframe_points:
            k.interpolation = "CONSTANT"
    kam.hide_render = True


# ---------------------------------------------------------------- Workbench
sc.render.engine = "BLENDER_WORKBENCH"
sc.render.use_motion_blur = False
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
try:
    sc.view_settings.look = "None"
except TypeError:
    pass
sc.view_settings.exposure = 0.0
sc.view_settings.gamma = 1.0
sc.display.render_aa = "16"
if sc.world is None:
    sc.world = bpy.data.worlds.new("yapim")
sc.world.color = ZEMIN
sh = sc.display.shading
sh.light = "STUDIO"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.cavity_ridge_factor, sh.cavity_valley_factor = 1.0, 1.2
sh.curvature_ridge_factor, sh.curvature_valley_factor = 1.0, 1.0
sh.show_shadows = True
sh.shadow_intensity = 0.45
sh.show_specular_highlight = False
sh.show_object_outline = False
sh.single_color = KIL
for o in sc.objects:
    if o.type in ("MESH", "CURVE", "SURFACE", "META", "FONT"):
        o.color = (*KIL, 1.0)
sc.display.light_direction = (0.35, -0.45, 0.82)
sc.display.shadow_shift = 0.05

if KIP == "kil":
    sh.type = "SOLID"
    sh.color_type = "SINGLE"
elif KIP == "tel":
    # Workbench'in son çiziminde tel kafes yok (yalnız görüntü alanının katmanı): EEVEE + bütün sahneye tek malzeme (görüntü katmanı
    # malzeme üstüne yazması): Wireframe düğümü kenarları piksel kalınlığında açık mavi, yüzleri koyu çizer (arkadaki çizgiler gizli kalır).
    sc.render.engine = "BLENDER_EEVEE"
    m = bpy.data.materials.new("yapim_tel")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tel = nt.nodes.new("ShaderNodeWireframe")
    tel.use_pixel_size = True
    tel.inputs["Size"].default_value = 1.0
    cizgi = nt.nodes.new("ShaderNodeEmission")
    cizgi.inputs["Color"].default_value = (0.62, 0.78, 1.0, 1.0)
    dolgu = nt.nodes.new("ShaderNodeEmission")
    dolgu.inputs["Color"].default_value = (0.012, 0.016, 0.026, 1.0)
    karis = nt.nodes.new("ShaderNodeMixShader")
    cikis = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tel.outputs["Fac"], karis.inputs["Fac"])
    nt.links.new(dolgu.outputs["Emission"], karis.inputs[1])
    nt.links.new(cizgi.outputs["Emission"], karis.inputs[2])
    nt.links.new(karis.outputs["Shader"], cikis.inputs["Surface"])
    bpy.context.view_layer.material_override = m
    dunya = bpy.data.worlds.new("yapim_tel")
    dunya.use_nodes = False
    dunya.color = ZEMIN
    sc.world = dunya
    for o in sc.objects:
        if o.type == "LIGHT":
            o.hide_render = True
else:
    sh.type = "SOLID"
    sh.color_type = "OBJECT"
    _ust_kurulum()
