"""Nesne ve ağ yardımcıları (ölçek metre, serbest: 7 cm'lik maket çadırı 0.07, 2 m'lik oda 2.0): temel biçimler, pişirilmiş paylaşılan ağlar, dörtgen şeritler."""
import bmesh
import bpy


def _sahne():
    return bpy.context.scene


def nesne(ad, veri=None, koleksiyon=None):
    o = bpy.data.objects.new(ad, veri)
    (koleksiyon or _sahne().collection).objects.link(o)
    return o


def bos(ad, konum=(0, 0, 0), ebeveyn=None):
    """Boş nesne: eklem, hedef, odak noktası."""
    o = nesne(ad)
    o.location = konum
    if ebeveyn:
        o.parent = ebeveyn
    return o


def _son(ad, malz, ebeveyn, yumusak=True):
    o = bpy.context.active_object
    o.name = ad
    if malz:
        o.data.materials.append(malz)
    if yumusak:
        bpy.ops.object.shade_smooth()
    if ebeveyn:
        o.parent = ebeveyn
    return o


def kure(ad, r, konum, malz, olcek=(1, 1, 1), ebeveyn=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=konum, segments=32, ring_count=16)
    o = _son(ad, malz, ebeveyn)
    o.scale = olcek
    return o


def koni(ad, r1, r2, h, konum, malz, ebeveyn=None, yumusatma=2):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, location=konum, vertices=32)
    o = _son(ad, malz, ebeveyn)
    if yumusatma:
        puruz(o, yumusatma)
    return o


def silindir(ad, r, h, konum, malz, ebeveyn=None, kenar=24, yumusak=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=konum, vertices=kenar)
    return _son(ad, malz, ebeveyn, yumusak)


def duzlem(ad, boyut, konum, malz, ebeveyn=None):
    bpy.ops.mesh.primitive_plane_add(size=boyut, location=konum)
    return _son(ad, malz, ebeveyn, yumusak=False)


def doku(ad, tur="CLOUDS", olcek=0.05, derinlik=2):
    """Kaydırma değiştiricisi için yordamsal doku (tohumsuz değil: Blender dokuları konumun saf fonksiyonudur)."""
    t = bpy.data.textures.new(ad, tur)
    if hasattr(t, "noise_scale"):
        t.noise_scale = olcek
    if hasattr(t, "noise_depth"):
        t.noise_depth = derinlik
    return t


def kaydir(o, ad, doku_, guc, koordinat="GLOBAL"):
    m = o.modifiers.new(ad, "DISPLACE")
    m.texture = doku_
    m.strength = guc
    m.texture_coords = koordinat
    return m


def puruz(o, seviye=2):
    """Alt bölümleme (adı denemeden kaldı): kil topağın yumuşak yüzeyi."""
    m = o.modifiers.new("yumusak", "SUBSURF")
    m.levels = m.render_levels = seviye
    return m


def pisir(me, kur):
    """Değiştiricileri bir kez uygular, sonucu paylaşılabilir düz ağ olarak döndürür. Aynı ağı kullanan yüzlerce kopya
    (çadırlar, kar örtüleri, duman topakları) belleği bir kez yer: kil kamp denemesinde 7,3 GB → 2,9 GB.
    kur(o): geçici nesneye değiştiricileri ekleyen işlev."""
    o = nesne("_pisir", me)
    kur(o)
    dg = bpy.context.evaluated_depsgraph_get()
    p = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o)
    for f in p.polygons:
        f.use_smooth = True
    return p


def serit(ad, ust, alt, malz=None):
    """İki nokta dizisi (aynı uzunlukta) arasında dörtgenlerden şerit ağ. Uzun bir n-gen (kâğıt dağ, kıyı, sırt çizgisi)
    yerine bunu kullan: Blender uzun n-geni üçgenlerken içbükey bölgeleri yanlış dolduruyor (kil kamp denemesi)."""
    bm = bmesh.new()
    u = [bm.verts.new(p) for p in ust]
    a = [bm.verts.new(p) for p in alt]
    for i in range(len(u) - 1):
        bm.faces.new((a[i], a[i + 1], u[i + 1], u[i]))
    me = bpy.data.meshes.new(ad)
    bm.to_mesh(me)
    bm.free()
    if malz:
        me.materials.append(malz)
    return me
