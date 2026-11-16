"""Katalog teknik örneği · "Maket / minyatür dünya" hareketinin Blender'daki yapımı (kil-maket görünüşüyle) ve Kil maket görüntü stilinin önizlemesi.
Hareket tipi Blender'a ve kile bağlı değildir: malzemeyi filmin görüntü stili, motoru filmin seçimi belirler; bu sahne kopyalanmaz.

Masa üstü küçük bir kil maket: yuvarlak kil zemin, kâğıt tepeler, bir ev, ağaçlar, iki kil figür. Kamera 3 sn'de birkaç santim yaklaşır;
1,0 sn'de evin penceresi yanar (tek sıcak ışık), çevre ısınır, figürler sevinçle zıplar. Renkler görünüşün adlı renklerinden (kil-maket
varyasyonları: gok_ust, gok_alt, dunya, ana_isik, dolgu, zemin, kagit_arka, kagit_on, ev, cati, agac, govde, figur1, figur2, ten, sicak, sicak_isik).
Örnekte cues.json yok: olay saatleri sabit (gerçek videoda kit.isaret ile işaretlerden gelir). Ölçek metre: ev 6 cm.
"""
import math

import bmesh
import bpy

import kit
from kit import ST, anahtar, renk4

B = {"ana_guc": 2.2, "dolgu_guc": 0.25, "dunya_guc": 1.0, "gok_guc": 1.0, "pozlama": 0.0, "bakis": "AgX - Medium High Contrast", **((ST.gorunus or {}).get("blender") or {})}
PENCERE, ZIPLA = 1.0, 1.3        # pencere yanar, figürler zıplar (örnek: sabit saatler)
sc = bpy.context.scene
sc.view_settings.exposure = B["pozlama"]
sc.view_settings.look = B["bakis"]

# ---------------------------------------------------------------- dünya ve ışık
kit.dunya("dunya", B["dunya_guc"])
kit.gunes("ana_isik", "ana_isik", B["ana_guc"], (math.radians(50), 0, math.radians(35)), aci=8)
kit.gunes("dolgu", "dolgu", B["dolgu_guc"], (math.radians(70), 0, math.radians(-120)), aci=40)

# ---------------------------------------------------------------- gök ve kâğıt tepeler (dörtgen şerit)
GOK = bpy.data.materials.new("gok")
GOK.use_nodes = True
g = GOK.node_tree
g.nodes.clear()
tc, sep, rp = g.nodes.new("ShaderNodeTexCoord"), g.nodes.new("ShaderNodeSeparateXYZ"), g.nodes.new("ShaderNodeValToRGB")
g.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
rp.color_ramp.elements[0].color = renk4("gok_alt")
rp.color_ramp.elements[1].color = renk4("gok_ust")
rp.color_ramp.elements[1].position = 0.8
g.links.new(sep.outputs["Y"], rp.inputs["Fac"])
em, out = g.nodes.new("ShaderNodeEmission"), g.nodes.new("ShaderNodeOutputMaterial")
em.inputs["Strength"].default_value = B["gok_guc"]
g.links.new(rp.outputs["Color"], em.inputs["Color"])
g.links.new(em.outputs["Emission"], out.inputs["Surface"])
gok = kit.duzlem("gok", 1, (0, 0.9, 0.3), GOK)
gok.scale = (2.0, 1, 1.0)
gok.rotation_euler = (math.radians(90), 0, 0)
gok.visible_diffuse = gok.visible_glossy = gok.visible_transmission = False   # gök yalnız görünür: parlak gök maketi pusla aydınlatmasın

for ad, y, taban, tepe, malz, faz in (("kagit_arka", 0.55, 0.0, 0.16, "kagit_arka", 0.7), ("kagit_on", 0.38, -0.01, 0.10, "kagit_on", 2.3)):
    xs = [-0.9 + i * 0.02 for i in range(91)]
    sirt = [(x, y, taban + tepe * (0.6 + 0.25 * math.sin(x * 4.1 + faz) + 0.15 * math.sin(x * 9.7 + faz * 2))) for x in xs]
    me = kit.serit(ad, sirt, [(x, y, -0.03) for x, _, _ in sirt], kit.kagit(ad, malz, isik=0.15))
    kit.nesne(ad, me).modifiers.new("karton", "SOLIDIFY").thickness = 0.004

# ---------------------------------------------------------------- kil zemin
ZEMIN = kit.kil("zemin", "zemin", puruzluluk=0.7, ssd=0.15)
zemin = kit.silindir("zemin", 0.30, 0.03, (0, 0.05, -0.015), ZEMIN, kenar=96)
kit.puruz(zemin, 2)
kit.kaydir(zemin, "tumsek", kit.doku("tumsek", olcek=0.05, derinlik=2), 0.004)

# ---------------------------------------------------------------- ev: kil kutu, üçgen çatı, yanan pencere
EV, CATI = kit.kil("ev", "ev", puruzluluk=0.75), kit.kil("cati", "cati", puruzluluk=0.7)
ev = kit.nesne("ev", None)
ev.location = (0.0, 0.06, 0.0)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.0175))
govde = bpy.context.active_object
govde.name, govde.scale, govde.parent = "ev_govde", (0.06, 0.045, 0.035), ev
govde.data.materials.append(EV)
bv = govde.modifiers.new("kenar", "BEVEL")   # kutu kil topağa dönmesin: yalnız kenarlar yuvarlanır
bv.width, bv.segments = 0.004, 3
bm = bmesh.new()
v = [bm.verts.new(p) for p in ((-0.034, -0.027, 0.034), (0.034, -0.027, 0.034), (0, -0.027, 0.062), (-0.034, 0.027, 0.034), (0.034, 0.027, 0.034), (0, 0.027, 0.062))]
for f in ((0, 1, 2), (3, 5, 4), (0, 2, 5, 3), (1, 4, 5, 2), (0, 3, 4, 1)):
    bm.faces.new([v[i] for i in f])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("cati")
bm.to_mesh(me)
bm.free()
me.materials.append(CATI)
cati = kit.nesne("cati", me)
cati.parent = ev
bv = cati.modifiers.new("kenar", "BEVEL")
bv.width, bv.segments = 0.0015, 2
PEN_M, PEN_E = kit.isik_malz("pencere", "sicak", 0.0)
pen = kit.duzlem("pencere", 1, (0.0, -0.0231, 0.019), PEN_M, ebeveyn=ev)
pen.scale = (0.014, 0.016, 1)
pen.rotation_euler = (math.radians(90), 0, 0)
_, PEN_L = kit.nokta("pencere_isigi", "sicak_isik", 0.0, 0.004, (0.0, -0.03, 0.02), ev)
for t, g_ in ((0.0, 0.0), (PENCERE, 0.0), (PENCERE + 0.4, 1.0), (3.0, 1.0)):
    anahtar(PEN_E.inputs["Strength"], "default_value", 4.0 * g_, t)
    anahtar(PEN_L, "energy", 0.05 * g_, t)

# ---------------------------------------------------------------- ağaçlar: üst üste kil koniler
AGAC, GOVDE = kit.kil("agac", "agac", puruzluluk=0.8), kit.kil("govde", "govde", puruzluluk=0.8)
for i, (x, y, s) in enumerate(((-0.09, 0.10, 1.0), (0.10, 0.12, 0.85), (-0.15, 0.02, 0.7), (0.16, -0.01, 0.6))):
    kit.silindir(f"agac_govde_{i}", 0.004 * s, 0.02 * s, (x, y, 0.01 * s), GOVDE, kenar=12)
    for j in range(3):
        kit.koni(f"agac_{i}_{j}", (0.026 - j * 0.006) * s, 0.0, (0.03 - j * 0.004) * s, (x, y, (0.03 + j * 0.016) * s), AGAC)

# ---------------------------------------------------------------- iki kil figür: pencere yanınca sevinçle zıplar
TEN = kit.kil("ten", "ten", puruzluluk=0.6, ssd=0.3)
for i, (x, y, malz_ad, gec) in enumerate(((-0.035, -0.035, "figur1", 0.0), (0.04, -0.03, "figur2", 0.12))):
    f = kit.bos(f"figur_{i}", (x, y, 0.0))
    kit.koni(f"figur_govde_{i}", 0.008, 0.005, 0.018, (0, 0, 0.009), kit.kil(f"figur_{i}", malz_ad, puruzluluk=0.7), f)
    kit.kure(f"figur_bas_{i}", 0.0055, (0, 0, 0.0235), TEN, ebeveyn=f)
    for t, z in ((0.0, 0.0), (ZIPLA + gec, 0.0), (ZIPLA + gec + 0.18, 0.012), (ZIPLA + gec + 0.36, 0.0), (3.0, 0.0)):
        anahtar(f, "location", z, t, indeks=2)

# ---------------------------------------------------------------- kamera: 3 sn'de birkaç santim yaklaşma, odak evde
odak = kit.bos("odak", (0.0, 0.035, 0.02))
ko, _ = kit.kamera(lens=45, fstop=10, odak=odak)
hedef = kit.bos("hedef", (0.0, 0.05, 0.028))
kit.izle(ko, hedef)
for t, p in ((0.0, (0.045, -0.27, 0.078)), (3.0, (0.02, -0.215, 0.062))):
    for i in range(3):
        anahtar(ko, "location", p[i], t, indeks=i)
kit.yumusat(ko)
