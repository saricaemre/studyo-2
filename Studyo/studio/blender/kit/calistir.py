"""Blender kitinin çalıştırıcısı: stüdyo (pipeline/blender.py) her Blender işini bununla başlatır; elle çağırmaya gerek yok.

  blender -b --factory-startup --python-exit-code 1 --python blender/kit/calistir.py -- \
      --sahne blender/<id>/sahne.py --veri VERI.json --kalite '{"olcek": 50, "ornek": 16}' --cikti KLASOR --kareler 0,1,2
Kipler: --kareler (plaka çiz) · --kuru (sahneyi kur, çizme; özet yaz) · --ac (Blender arayüzünde aç) · --kaydet x.blend
Kare numaraları Remotion'unkidir (0 tabanlı, t = f / fps); Blender'da f + 1 çizilir (kit.kare). Plaka: KLASOR/pNNNNN.png (8 bit RGB).

Sıra: sahne temizlenir → varsayılan çizim ayarları → sahne.py çalışır (ışık sayısı, sıçrama, hareket bulanıklığı gibi
sanat kararlarını değiştirebilir) → kalite ve çıktı ayarları yeniden zorlanır (çözünürlük, örnek sayısı, gürültü giderici, PNG).
Her plaka geçici adla yazılıp yerine taşınır: yarım kalan iş önbellekte bozuk plaka bırakmaz.
"""
import argparse
import json
import os
import resource
import runpy
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # studio/blender → `import kit`

import bpy  # noqa: E402

import kit  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--sahne", required=True)
ap.add_argument("--veri", required=True)
ap.add_argument("--kalite", default="{}")
ap.add_argument("--cikti", default="")
ap.add_argument("--kareler", default="")
ap.add_argument("--kuru", action="store_true")
ap.add_argument("--ac", action="store_true")
ap.add_argument("--kaydet", default="")
A = ap.parse_args(argv)
K = {"olcek": 100, "ornek": 48, "esik": 0.015, "gurultu": True, "cihaz": "gpu", **json.loads(A.kalite)}


def yaz(etiket, d):
    print(f"ST_{etiket} " + json.dumps(d, ensure_ascii=False), flush=True)


def temizle():
    """Fabrika sahnesindeki küp, ışık, kamera ve bütün veri blokları silinir (arayüz kipinde de çalışır)."""
    for koleksiyon in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves,
                       bpy.data.textures, bpy.data.images, bpy.data.actions, bpy.data.worlds, bpy.data.node_groups):
        for b in list(koleksiyon):
            koleksiyon.remove(b)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def varsayilan(sc):
    """Kil kamp denemesinden gelen sanat varsayılanları; sahne değiştirebilir."""
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 8, 3, 2
    cy.transmission_bounces, cy.transparent_max_bounces = 6, 8
    cy.caustics_reflective = cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.45   # Blender bulanıklığı karenin ortasına göre: ses senkronu kaymaz
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except TypeError:
            pass
    sc.view_settings.exposure = 0.0
    sc.frame_start, sc.frame_end = 1, max(1, kit.ST.nkare)
    sc.render.fps = kit.ST.fps


def zorla(sc):
    """Kalite ve çıktı stüdyonundur: sahne ne yazarsa yazsın burada sabitlenir (parmak izi bunlarla hesaplanır)."""
    sc.render.resolution_x, sc.render.resolution_y = kit.ST.w, kit.ST.h
    sc.render.resolution_percentage = int(K["olcek"])
    sc.render.fps, sc.render.fps_base = kit.ST.fps, 1.0
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"   # 16 bit RGBA'yı PIL okuyamıyor (kil kamp denemesi)
    sc.render.image_settings.compression = 15
    sc.render.use_file_extension = True
    for ad in ("date", "time", "render_time", "frame", "camera", "lens", "scene", "filename", "memory", "hostname", "frame_range", "marker"):
        if hasattr(sc.render, f"use_stamp_{ad}"):
            setattr(sc.render, f"use_stamp_{ad}", False)
    sc.render.use_stamp = False
    if sc.render.engine == "CYCLES":
        pref = bpy.context.preferences.addons["cycles"].preferences
        metal = False
        if K["cihaz"] == "gpu":
            pref.compute_device_type = "METAL"
            pref.get_devices()
            for d in pref.devices:
                d.use = d.type == "METAL"
                metal = metal or d.use
        cy = sc.cycles
        cy.device = "GPU" if metal else "CPU"
        cy.samples = int(K["ornek"])
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = float(K["esik"])
        cy.use_denoising = bool(K["gurultu"])
        cy.denoiser = "OPENIMAGEDENOISE"
        cy.denoising_use_gpu = False      # CPU gürültü giderici: farkı 1/255'e indiriyor (OKU.md ölçümü)
        cy.seed = 7
        cy.use_animated_seed = False
    elif sc.render.engine.startswith("BLENDER_EEVEE"):
        sc.eevee.taa_render_samples = int(K["ornek"])


def main():
    t0 = time.time()
    kit.ST.yukle(json.loads(Path(A.veri).read_text()))
    sahne = Path(A.sahne).resolve()
    sys.path.insert(0, str(sahne.parent))   # sahne klasöründeki yardımcı modüller
    temizle()
    sc = bpy.context.scene
    varsayilan(sc)
    os.chdir(sahne.parent)
    runpy.run_path(str(sahne), run_name="__sahne__")
    sc = bpy.context.scene
    if sc.camera is None:
        raise SystemExit("Sahnede kamera yok: kit.kamera(...) ile kur")
    zorla(sc)
    kurulum = time.time() - t0
    if A.kaydet:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(A.kaydet).resolve()))
    if A.ac:
        sc.frame_set(1)
        for ekran in bpy.data.screens:
            for alan in ekran.areas:
                if alan.type == "VIEW_3D":
                    alan.spaces[0].region_3d.view_perspective = "CAMERA"
        print(f"Sahne açıldı: {sahne} · {kit.ST.format} · {len(bpy.data.objects)} nesne · kurulum {kurulum:.1f} sn")
        return
    bellek = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30   # macOS: bayt
    if A.kuru:
        dg = bpy.context.evaluated_depsgraph_get()
        ucgen = sum(len(o.evaluated_get(dg).data.loop_triangles) for o in sc.objects if o.type == "MESH" and o.visible_get())
        yaz("KURU", {"nesne": len(bpy.data.objects), "isik": len(bpy.data.lights), "malzeme": len(bpy.data.materials), "ucgen": ucgen,
                     "kurulum_sn": round(kurulum, 2), "bellek_gb": round(bellek(), 2), "motor": sc.render.engine, "kamera": sc.camera.name})
        return
    out = Path(A.cikti)
    out.mkdir(parents=True, exist_ok=True)
    kareler = [int(x) for x in A.kareler.split(",") if x != ""]
    yaz("BASLA", {"kare": len(kareler), "kurulum_sn": round(kurulum, 2), "cihaz": sc.cycles.device if sc.render.engine == "CYCLES" else sc.render.engine})
    for f in kareler:
        if not 0 <= f < kit.ST.nkare:
            raise SystemExit(f"Kare {f} aralık dışında (0..{kit.ST.nkare - 1})")
        t = time.time()
        sc.frame_set(f + 1)
        gecici = out / f"_p{f:05d}.png"
        sc.render.filepath = str(gecici)
        bpy.ops.render.render(write_still=True)
        os.replace(gecici, out / f"p{f:05d}.png")
        yaz("KARE", {"f": f, "sn": round(time.time() - t, 2), "bellek_gb": round(bellek(), 2)})


main()
