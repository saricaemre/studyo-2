"""Dünya, ışık ve kamera."""
import math

import bpy

from .model import nesne
from .veri import ST, renk as _renk


def dunya(renk, guc=1.0):
    """Arka plan ışığı (gökyüzünün kendisi değil: onu bir düzlemle kur)."""
    w = bpy.data.worlds.new("dunya")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*_renk(renk), 1)
    bg.inputs["Strength"].default_value = guc
    return w


def gunes(ad, renk, guc, yon, aci=4.0):
    """Yönlü ışık (ay, dolgu). yon: Euler (radyan). aci: ışık kaynağının açısı (derece): büyük = yumuşak gölge."""
    L = bpy.data.lights.new(ad, "SUN")
    L.color = _renk(renk)
    L.energy = guc
    L.angle = math.radians(aci)
    o = nesne(ad, L)
    o.rotation_euler = yon
    return o, L


def nokta(ad, renk, guc, yaricap, konum=(0, 0, 0), ebeveyn=None):
    """Nokta ışık (soba, kor, fener). Güç maket ölçeğinde küçüktür (W): 0,01–0,1."""
    L = bpy.data.lights.new(ad, "POINT")
    L.color = _renk(renk)
    L.shadow_soft_size = yaricap
    L.energy = guc
    o = nesne(ad, L)
    o.location = konum
    if ebeveyn:
        o.parent = ebeveyn
    return o, L


def kamera(lens=45, fstop=None, odak=None, bicak=7, yakin=0.002, uzak=10.0, sensor=36):
    """Sahnenin kamerası. fstop verilirse alan derinliği açılır (maket hissi: yüksek f, çok yakın kamera); odak: odak nesnesi.
    Sensör uzun kenara uyar (AUTO): dikey formatta yükseklik, yatayda genişlik aynı açıyı görür. Her format ayrı kompozisyondur:
    kadrajı ST.format / ST.dikey ile kur (kamera konumu, lens), merkezden kırpma."""
    k = bpy.data.cameras.new("kamera")
    k.lens = lens
    k.sensor_width = sensor
    k.clip_start = yakin
    k.clip_end = uzak
    if fstop:
        k.dof.use_dof = True
        k.dof.aperture_fstop = fstop
        k.dof.aperture_blades = bicak
        k.dof.aperture_ratio = 1.0
        if odak is not None:
            k.dof.focus_object = odak
    o = nesne("kamera", k)
    bpy.context.scene.camera = o
    return o, k


def izle(kamera_nesnesi, hedef):
    """Kamera hedef nesneye bakar (hedef canlanırsa bakış da canlanır)."""
    iz = kamera_nesnesi.constraints.new("TRACK_TO")
    iz.target = hedef
    iz.track_axis = "TRACK_NEGATIVE_Z"
    iz.up_axis = "UP_Y"
    return iz


def guvenli_alan():
    """Formatın güvenli alanı (oran, kadrajın kenarlarından): {ust, alt, sol, sag}. Remotion'un yazısı buraya oturur;
    sahnenin ana nesnesini platform arayüzünün altında bırakma."""
    return dict(ST.guvenli)


def kontur(kalinlik=1.6, renk="#1A1A1A", yaratik=True):
    """Çizgi film konturu (Freestyle): siluet ve kırışık kenarları çizer. kalinlik: 1080 px yüksekliğe göre piksel (taslak ve tam aynı görünür).
    Sanat kararıdır: sahne açar, çalıştırıcı dokunmaz."""
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "RELATIVE"
    sc.render.line_thickness = kalinlik * 480.0 / 1080.0   # RELATIVE: 480 px yüksekliğe göre
    katman = bpy.context.view_layer
    katman.use_freestyle = True
    ls = katman.freestyle_settings.linesets[0] if katman.freestyle_settings.linesets else katman.freestyle_settings.linesets.new("kontur")
    ls.select_by_visibility = True
    ls.select_by_edge_types = True
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = yaratik
    ls.linestyle.color = _renk(renk)
    ls.linestyle.thickness = 1.0
    return ls
