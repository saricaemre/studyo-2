"""Kamera takibi (FOOH: gerçek sokakta imkânsız nesne): dondurulmuş kamera çözümünden sahnenin kamerası, gölge yakalayıcı zemin ve
Remotion'un gerçek görüntüyle birleştireceği katmanlar. Kurallar: ../CLAUDE.md → Kamera takibi · çözüm: ./st takip (pipeline/takip.py, coz.py).

Kitin dışında (eevee/, yapim/ gibi): kit bütün Blender filmlerinin parmak izindedir. Bu klasör yalnız takip filminin parmak izine girer
(pipeline/blender.py → kaynaklar), çözümün sha256'sı ST.takip ile veriye. Sahne kodu:

  import takip
  kam = takip.kamera()                     çözümün kamerası: her kareye anahtar (konum + dönüş), odak, sensör; ölçek metre, Z yukarı,
                                           Y yürüyüş yönü, başlangıç ilk karede kameranın ayağı (zemin z = 0)
  takip.zemin(boyut=30, yansima=0)         gölge yakalayıcı zemin (Cycles; EEVEE'de yok: ../CLAUDE.md → Kamera takibi). yansima 0–1: ıslak yol
  takip.ortam(guc=1)                       dünya ışığı çekimin kendi renklerinden (gök ve zemin ortalaması, çözümde): nesne ortama oturur
  takip.onunde(kare, mesafe)               o karede kameranın önünde, zeminde bir nokta (nesnenin yeri için)
  takip.katmanlar()                        saydam film + gölge geçişi + kompozitör (sahnenin SONUNDA çağır)

Katmanlar (her plaka kümesinde, Blender kare numarasıyla: f + 1): pNNNNN.png ana plaka = Blender'ın kendi birleştirmesi (çekim × gölge
+ yansıma + nesne; önizleme ve deterministiklik), nNNNNN.png nesne (RGBA, düz alfa), gNNNNN.png gölge çarpanı (≤ 1, sRGB), yNNNNN.png
yansıma ve sekme ışığı (çekim × gölge çarpanının 1'i aşan kısmı; toplanır). Remotion: src/lib/takip (<TakipBirlesim>).
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

import kit
from kit import ST

KOK = Path(__file__).resolve().parents[2]     # studio/
_C = {}


def bilgi() -> dict:
    t = getattr(ST, "takip", None) if "takip" in ST._d else None
    if not t:
        raise SystemExit("Bu filmde kamera takibi yok (ST.takip): önce ./st takip <id> <görüntü>")
    return t


def cozum() -> dict:
    """Dondurulmuş çözüm (videos/<id>/takip/<ad>/cozum.json); sha256 veriyle aynı olmalı (çözüm değişince plakalar yeni kümeye çizilir)."""
    if "c" not in _C:
        t = bilgi()
        p = KOK / t["cozum"]
        b = p.read_bytes()
        if hashlib.sha256(b).hexdigest() != t["sha256"]:
            raise SystemExit(f"çözüm dosyası değişmiş: {p} (sha256 kayıttakiyle aynı değil; ./st takip yeniden dondurur)")
        _C["c"] = json.loads(b)
    return _C["c"]


def _matris(i: int) -> Matrix:
    K = cozum()["kareler"]
    m = K[max(0, min(len(K) - 1, i))]["m"]
    return Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])


def kamera(yakin=0.05, uzak=500.0):
    """Çözümün kamerası. Film karesi f (Remotion) = çözümün f. karesi = Blender'da f + 1. Çözümden uzun filmde son kare tutulur."""
    c = cozum()
    if abs(ST.w / ST.h - c["klip"]["en"] / c["klip"]["boy"]) > 0.01:
        raise SystemExit(f"çekim {c['klip']['en']}×{c['klip']['boy']}, format {ST.format} ({ST.w}×{ST.h}): oranlar aynı olmalı "
                         "(merkezden kırpma yok; bu format için ayrı çekim)")
    M = c["mercek"]
    k = bpy.data.cameras.new("takip_kamera")
    k.sensor_fit = "HORIZONTAL"         # çözümün odağı görüntünün genişliğine göre (sensör 36 mm = görüntü genişliği)
    k.sensor_width = M["sensor_mm"]
    k.lens = M["odak_mm"]
    k.clip_start, k.clip_end = yakin, uzak
    buyuk = max(c["klip"]["en"], c["klip"]["boy"])
    k.shift_x = (M["merkez_px"][0] - c["klip"]["en"] / 2) / buyuk
    k.shift_y = -(M["merkez_px"][1] - c["klip"]["boy"] / 2) / buyuk
    o = kit.nesne("takip_kamera", k)
    o.rotation_mode = "QUATERNION"
    onceki = None
    for f in range(ST.nkare):
        mw = _matris(f)
        loc, q, _ = mw.decompose()
        if onceki is not None and onceki.dot(q) < 0:   # dördey işareti sürekli: ara karede (hareket bulanıklığı) kamera dönmesin
            q.negate()
        onceki = q
        o.location, o.rotation_quaternion = loc, q
        o.keyframe_insert("location", frame=f + 1)
        o.keyframe_insert("rotation_quaternion", frame=f + 1)
    for fc in kit.fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    bpy.context.scene.camera = o
    return o


def onunde(kare: int = 0, mesafe: float = 4.0) -> Vector:
    """f. karede kameranın baktığı yönde, yatayda `mesafe` metre ötede zemindeki nokta (z = 0)."""
    mw = _matris(kare)
    bak = -(mw.to_3x3() @ Vector((0, 0, 1)))
    bak.z = 0
    bak.normalize()
    p = mw.translation + bak * mesafe
    return Vector((p.x, p.y, 0.0))


def zemin(boyut=30.0, yansima=0.0, sekme=0.4, merkez=None):
    """Gölge yakalayıcı zemin (z = 0): yalnız gölgeyi ve nesnenin zemine yansıyan ışığını tutar, kendisi görünmez (Cycles).
    yansima: 0 mat (asfalt, toprak) … 1 ayna gibi ıslak zemin. sekme: nesneden zemine sıçrayan ışığın ve yansımanın şiddeti (y katmanı;
    0 yok, 1 Cycles'ın hesapladığı kadar: renkli nesnenin altında güçlü bir renk lekesi; bulutlu günde 0,3–0,5). EEVEE'de gölge yakalayıcı yok."""
    _C["sekme"] = float(sekme)
    if bpy.context.scene.render.engine != "CYCLES":
        raise SystemExit("Gölge yakalayıcı yalnız Cycles'ta: EEVEE'de zemin gri bir düzlem olarak çizilir (ölçüm: blender/CLAUDE.md → Kamera "
                         "takibi). Takip filmini Cycles ile çiz (./st blender <id> cizer cycles) ya da takip.zemin'i çağırma.")
    c = merkez or onunde(0, boyut / 3)
    bpy.ops.mesh.primitive_plane_add(size=boyut, location=(c[0], c[1], 0.0))
    z = bpy.context.active_object
    z.name = "takip_zemin"
    m = bpy.data.materials.new("takip_zemin")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*_ortalama("zemin"), 1)
    b.inputs["Roughness"].default_value = 1.0 - 0.85 * yansima
    b.inputs["Specular IOR Level"].default_value = 0.5 * yansima
    z.data.materials.append(m)
    z.is_shadow_catcher = True
    return z


def _ortalama(ad):
    r = (cozum().get("renk") or {}).get(ad)
    return kit.renk(r) if r else (0.18, 0.18, 0.18)


def ortam(guc=1.0):
    """Dünya ışığı: yukarıdan gökün, aşağıdan zeminin ortalama rengi (çekimden ölçüldü, çözümde). Kamera görmez (film saydam)."""
    w = bpy.data.worlds.new("takip_ortam")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    koor = nt.nodes.new("ShaderNodeTexCoord")
    ayir = nt.nodes.new("ShaderNodeSeparateXYZ")
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(koor.outputs["Generated"], ayir.inputs[0])
    nt.links.new(ayir.outputs["Z"], rampa.inputs["Fac"])
    rampa.color_ramp.elements[0].position, rampa.color_ramp.elements[1].position = 0.45, 0.6
    rampa.color_ramp.elements[0].color = (*_ortalama("zemin"), 1)
    rampa.color_ramp.elements[1].color = (*_ortalama("gok"), 1)
    nt.links.new(rampa.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = guc
    return w


def _cikti() -> str | None:
    """Çalıştırıcının --cikti klasörü (katman dosyaları plakanın yanına yazılır); kuru kurulumda ve arayüzde yok."""
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return a[a.index("--cikti") + 1] if "--cikti" in a else None


def katmanlar():
    """Sahnenin sonunda: saydam film, gölge geçişi, Standard görünüm (çekimin renkleri olduğu gibi kalsın) ve kompozitör.
    Ana plaka (pNNNNN) = çekim × gölge + yansıma + nesne (Blender'ın birleştirmesi: önizleme); katmanlar n/g/y Remotion içindir."""
    sc = bpy.context.scene
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    vl = bpy.context.view_layer
    cycles = sc.render.engine == "CYCLES"
    if cycles:
        vl.cycles.use_pass_shadow_catcher = True
    c = cozum()
    t = bilgi()
    klip = bpy.data.movieclips.load(str(KOK / t["goruntu"]))
    klip.frame_start = 1 - int(t.get("bas", 0))       # Blender'ın f + 1. karesi = çekimin bas + f. karesi
    kc = klip.tracking.camera
    kc.sensor_width, kc.focal_length = 36.0, c["mercek"]["odak_mm"]
    B = c["mercek"]["bozulma"]
    kc.distortion_model = "POLYNOMIAL"
    kc.k1, kc.k2, kc.k3 = B["k1"], B["k2"], B["k3"]
    bozuk = any(abs(B[k]) > 1e-6 for k in ("k1", "k2", "k3"))
    ng = bpy.data.node_groups.new("takip_kompozit", "CompositorNodeTree")
    sc.compositing_node_group = ng
    N = ng.nodes
    L = ng.links.new
    rl = N.new("CompositorNodeRLayers")
    nesne_ = rl.outputs["Image"]
    golge = rl.outputs["Shadow Catcher"] if cycles else None
    if bozuk:   # çözüm mercek bozulması bulduysa CG aynı bozulmayla çarpıtılır (çekim olduğu gibi kalır)
        d1 = N.new("CompositorNodeMovieDistortion")
        d1.clip = klip
        d1.inputs["Type"].default_value = "Distort"
        L(nesne_, d1.inputs["Image"])
        nesne_ = d1.outputs["Image"]
        if golge is not None:
            d2 = N.new("CompositorNodeMovieDistortion")
            d2.clip = klip
            d2.inputs["Type"].default_value = "Distort"
            L(golge, d2.inputs["Image"])
            golge = d2.outputs["Image"]
    # çekim: render boyutuna (taslakta yarım)
    mc = N.new("CompositorNodeMovieClip")
    mc.clip = klip
    olc = N.new("CompositorNodeScale")
    olc.inputs["Type"].default_value = "Render Size"
    L(mc.outputs["Image"], olc.inputs["Image"])
    cekim = olc.outputs["Image"]
    # gölge çarpanı ≤ 1 (çarpılır) ve 1'i aşan kısım × çekim (yansıma, sekme ışığı; toplanır)
    def karistir(tur, a, b):
        m = N.new("ShaderNodeMix")      # Mix düğümünde aynı adlı soketler türlere göre yinelenir: renk girişleri 6 ve 7, çıkışı 2
        m.data_type, m.blend_type = "RGBA", tur
        m.inputs[0].default_value = 1.0
        for i, x in ((6, a), (7, b)):
            if isinstance(x, tuple):
                m.inputs[i].default_value = x
            else:
                L(x, m.inputs[i])
        return m.outputs[2]
    if golge is not None:
        g = karistir("DARKEN", golge, (1.0, 1.0, 1.0, 1.0))
        k = _C.get("sekme", 0.4)
        y = karistir("MULTIPLY", karistir("MULTIPLY", karistir("SUBTRACT", golge, g), (k, k, k, 1.0)), cekim)
        zemin_ = karistir("ADD", karistir("MULTIPLY", cekim, g), y)
    else:
        g = y = None
        zemin_ = cekim
    ust = N.new("CompositorNodeAlphaOver")
    L(zemin_, ust.inputs["Background"])
    L(nesne_, ust.inputs["Foreground"])
    cik = ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    go = N.new("NodeGroupOutput")
    L(ust.outputs["Image"], go.inputs[0])
    d = _cikti()
    if d:
        fo = N.new("CompositorNodeOutputFile")
        fo.directory = d
        fo.file_name = ""
        fo.format.media_type = "IMAGE"
        fo.format.file_format = "PNG"
        fo.format.color_depth = "8"
        fo.format.compression = 15
        fo.format.color_mode = "RGBA"
        for ad, soket, mod in (("n", nesne_, "RGBA"), ("g", g, "RGB"), ("y", y, "RGB")):
            if soket is None:
                continue
            it = fo.file_output_items.new("RGBA", ad + "#####")
            it.override_node_format = True
            it.format.media_type = "IMAGE"
            it.format.file_format = "PNG"
            it.format.color_depth = "8"
            it.format.compression = 15
            it.format.color_mode = mod
            L(soket, fo.inputs[ad + "#####"])
    return ng
