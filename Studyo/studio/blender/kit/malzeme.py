"""Malzemeler: elle yoğrulmuş kil, lifli kâğıt (maket), plastik, metal, cam, boya (genel), ışık. Renk görünüşten gelir (kit.renk): ad ('kar'), '#rrggbb' ya da doğrusal (r, g, b).

Kil ve kâğıdın ölçekleri maket içindir (metre): parmak izi kabartısı 0,4 mm, yüzey altı saçılma 2,5 mm. Başka ölçekte bir dünya kurarsan
(ör. 2 m'lik bir oda) kabartı ve saçılma ölçeğini `olcek` ile çarp.
"""
import bpy

from .veri import renk as _renk


def _yeni(ad):
    m = bpy.data.materials.new(ad)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree.nodes, m.node_tree.links


def kil(ad, renk, puruzluluk=0.62, ssd=0.18, parmak=1.0, gecirgen=0.0, isik_renk=None, isik_guc=0.0, cesit=0.08, kadife=0.0, olcek=1.0):
    """Kil: parmak izi kabartısı (ince gerilmiş gürültü + voronoi çukurlar), hafif renk dalgası (kil hiçbir zaman tek ton değildir),
    ince yüzey altı saçılma. gecirgen > 0: ışığı içinden geçirir (çadır bezi gibi; içerideki ateş dışarıdan görünür)."""
    m, N, L = _yeni(ad)
    out = N.new("ShaderNodeOutputMaterial")
    p = N.new("ShaderNodeBsdfPrincipled")
    p.inputs["Roughness"].default_value = puruzluluk
    p.inputs["Subsurface Weight"].default_value = ssd
    p.inputs["Subsurface Radius"].default_value = (1.0, 0.8, 0.6)
    p.inputs["Subsurface Scale"].default_value = 0.0025 * olcek
    if kadife:
        p.inputs["Sheen Weight"].default_value = kadife
    tk = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 60.0 / olcek
    nz.inputs["Detail"].default_value = 3.0
    L.new(tk.outputs["Object"], nz.inputs["Vector"])
    rp = N.new("ShaderNodeValToRGB")
    r, g, b = _renk(renk)
    rp.color_ramp.elements[0].color = (r * (1 - cesit), g * (1 - cesit), b * (1 - cesit), 1)
    rp.color_ramp.elements[1].color = (min(1, r * (1 + cesit * 0.6)), min(1, g * (1 + cesit * 0.6)), min(1, b * (1 + cesit * 0.6)), 1)
    L.new(nz.outputs["Fac"], rp.inputs["Fac"])
    L.new(rp.outputs["Color"], p.inputs["Base Color"])
    bp = None
    if parmak:
        n2 = N.new("ShaderNodeTexNoise")
        n2.inputs["Scale"].default_value = 900.0 / olcek
        n2.inputs["Detail"].default_value = 2.0
        n2.inputs["Distortion"].default_value = 1.5
        L.new(tk.outputs["Object"], n2.inputs["Vector"])
        vr = N.new("ShaderNodeTexVoronoi")
        vr.inputs["Scale"].default_value = 260.0 / olcek
        L.new(tk.outputs["Object"], vr.inputs["Vector"])
        mx = N.new("ShaderNodeMath")
        mx.operation = "MULTIPLY_ADD"
        L.new(vr.outputs["Distance"], mx.inputs[0])
        mx.inputs[1].default_value = 0.6
        L.new(n2.outputs["Fac"], mx.inputs[2])
        n3 = N.new("ShaderNodeTexNoise")
        n3.inputs["Scale"].default_value = 130.0 / olcek
        n3.inputs["Detail"].default_value = 1.0
        L.new(tk.outputs["Object"], n3.inputs["Vector"])
        mx2 = N.new("ShaderNodeMath")
        mx2.operation = "MULTIPLY_ADD"
        L.new(n3.outputs["Fac"], mx2.inputs[0])
        mx2.inputs[1].default_value = 1.6
        L.new(mx.outputs["Value"], mx2.inputs[2])
        bp = N.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.22 * parmak
        bp.inputs["Distance"].default_value = 0.0004 * olcek
        L.new(mx2.outputs["Value"], bp.inputs["Height"])
        L.new(bp.outputs["Normal"], p.inputs["Normal"])
    if isik_renk is not None:
        p.inputs["Emission Color"].default_value = (*_renk(isik_renk), 1)
        p.inputs["Emission Strength"].default_value = isik_guc
    son = p.outputs["BSDF"]
    if gecirgen:
        tr = N.new("ShaderNodeBsdfTranslucent")
        tr.inputs["Color"].default_value = (min(1, r * 1.15), min(1, g * 1.05), b * 0.9, 1)
        if bp:
            L.new(bp.outputs["Normal"], tr.inputs["Normal"])
        ms = N.new("ShaderNodeMixShader")
        ms.inputs["Fac"].default_value = gecirgen
        L.new(p.outputs["BSDF"], ms.inputs[1])
        L.new(tr.outputs["BSDF"], ms.inputs[2])
        son = ms.outputs["Shader"]
    L.new(son, out.inputs["Surface"])
    return m


def kagit(ad, renk, isik=0.0, lif=1.0, olcek=1.0):
    """Kâğıt/karton: lifli kabartı, mat yüzey. isik > 0: hafif öz ışık (karanlıkta kesilmiş kâğıdın silueti okunsun)."""
    m, N, L = _yeni(ad)
    out = N.new("ShaderNodeOutputMaterial")
    p = N.new("ShaderNodeBsdfPrincipled")
    c = _renk(renk)
    p.inputs["Base Color"].default_value = (*c, 1)
    p.inputs["Roughness"].default_value = 0.92
    tk = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 6.0)
    L.new(tk.outputs["Object"], mp.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 140.0 / olcek
    nz.inputs["Detail"].default_value = 6.0
    L.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.12 * lif
    bp.inputs["Distance"].default_value = 0.001 * olcek
    L.new(nz.outputs["Fac"], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], p.inputs["Normal"])
    if isik:
        p.inputs["Emission Color"].default_value = (*c, 1)
        p.inputs["Emission Strength"].default_value = isik
    L.new(p.outputs["BSDF"], out.inputs["Surface"])
    return m


def isik_malz(ad, renk, guc):
    """Yalnız ışık yayan malzeme (kor, ay, yıldız, soba ağzı). Döndürür: (malzeme, Emission düğümü) — güç anahtar kareyle canlanır:
    kit.anahtar(dugum.inputs['Strength'], 'default_value', 7.0, t)."""
    m, N, L = _yeni(ad)
    e = N.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*_renk(renk), 1)
    e.inputs["Strength"].default_value = guc
    o = N.new("ShaderNodeOutputMaterial")
    L.new(e.outputs["Emission"], o.inputs["Surface"])
    return m, e


# ---------------------------------------------------------------- genel malzemeler (maket dışı dünyalar: ürün, mimari, soyut, çizgi film)
# Malzeme ailesini görüntü stili belirler (zanaat.md §1c, blender/CLAUDE.md → Malzeme ailesi); kil ve kâğıt yalnız biri.
def _principled(ad, renk, **girdi):
    m, N, L = _yeni(ad)
    out = N.new("ShaderNodeOutputMaterial")
    p = N.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*_renk(renk), 1)
    for k, d in girdi.items():
        p.inputs[k].default_value = d
    L.new(p.outputs["BSDF"], out.inputs["Surface"])
    return m, p


def plastik(ad, renk, puruz=0.32, vernik=0.6):
    """Ürün kabuğu, oyuncak, boyalı yüzey: dielektrik, vernik katmanlı (vernik 0 = mat plastik)."""
    m, _ = _principled(ad, renk, **{"Roughness": puruz, "Metallic": 0.0, "Coat Weight": vernik, "Coat Roughness": 0.08})
    return m


def metal(ad, renk, puruz=0.25):
    """Metal (krom, alüminyum, pirinç, bakır): rengi yansımanın rengidir; dünya ışığı ya da ortam olmadan siyah görünür."""
    m, _ = _principled(ad, renk, **{"Roughness": puruz, "Metallic": 1.0})
    return m


def cam(ad, renk="#FFFFFF", puruz=0.02, ior=1.45):
    """Cam, sıvı, buz: ışık geçirir ve arkasını kırar. Pahalıdır (ışın sıçraması); sahnede birkaç tane."""
    m, _ = _principled(ad, renk, **{"Roughness": puruz, "Metallic": 0.0, "IOR": ior, "Transmission Weight": 1.0})
    return m


def boya(ad, renk, duz=0.0, puruz=0.9):
    """Mat boya. duz 0..1: ışıktan bağımsız düz renk payı (1 = gölgesiz, hex'e yakın; çizgi film / düz illüstrasyon dünyası için
    kit.kontur ve görünüşte "bakis": "Standard" ile birlikte)."""
    m, N, L = _yeni(ad)
    out = N.new("ShaderNodeOutputMaterial")
    c = (*_renk(renk), 1)
    p = N.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = c
    p.inputs["Roughness"].default_value = puruz
    p.inputs["Specular IOR Level"].default_value = 0.2
    if duz <= 0:
        L.new(p.outputs["BSDF"], out.inputs["Surface"])
        return m
    e = N.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = c
    e.inputs["Strength"].default_value = 1.0
    k = N.new("ShaderNodeMixShader")
    k.inputs["Fac"].default_value = duz
    L.new(p.outputs["BSDF"], k.inputs[1])
    L.new(e.outputs["Emission"], k.inputs[2])
    L.new(k.outputs["Shader"], out.inputs["Surface"])
    return m
