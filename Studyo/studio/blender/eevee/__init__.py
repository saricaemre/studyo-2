"""EEVEE çizeri (script.json → blender.cizer: "eevee"): Cycles'ın yerine rasterleştirici, aynı sahne kodu, aynı kit. Kurallar: ../CLAUDE.md → Çizer.

Cycles filmlerinin parmak izine girmez: bu klasör yalnız EEVEE filminin parmak izinde (pipeline/blender.py → kaynaklar). Kit'e
(blender/kit/) dokunulmadı, çünkü kit bütün Blender filmlerinin parmak izindedir; değişse Cycles plakaları yeniden çizilirdi.

Akış: kitin çalıştırıcısı (kit/calistir.py) sahne yerine sarmalayıcıyı (eevee/sahne.py) çalıştırır. Sarmalayıcı çizeri EEVEE'ye çevirip
sanat varsayılanlarını kurar (varsayilan), asıl sahneyi çalıştırır, kit malzemelerini uyarlar (uyarla), kaliteyi zorlar (zorla).
Çalıştırıcının zorla()'sı ardından çözünürlüğü, PNG'yi ve örnek sayısını (taa_render_samples = ornek) sabitler. Her işin ilk karesi
iki kez çizilir (ısınma; pipeline/blender.py → _calistir).

  varsayilan(sc)    sanat varsayılanları: ekran uzayı ışın izleme (yansıma, kırılma, dolaylı ışık), gölge, süzgeçli alan derinliği;
                    sahne değiştirebilir (ör. sc.eevee.use_raytracing = False)
  uyarla()          kit malzemeleri EEVEE'de Cycles'a en yakın: cam ve sıvıda ışın izlenmiş kırılma, ışık geçiren ince yüzeyde (bez, kâğıt)
                    ince levha kalınlığı. Sahne bir malzemeyi dışarıda bırakır: m["eevee_uyarla"] = False
  zorla(sc, K)      kalite stüdyonundur: gölge çözünürlüğü, ışın izleme çözünürlüğü, hareket bulanıklığı adımı, gölge ışını
  hucre(...)        hücre boyası (toon): ışığı birkaç düz banda böler. Yalnız EEVEE'de çalışır (Shader to RGB); Cycles'ta karşılığı yok
"""
import json
import sys

import bpy

KALITE_ANAHTARLARI = ("ornek", "golge", "isin", "bulaniklik", "golge_isin", "golge_adim")


def kalite() -> dict:
    """Çalıştırıcıya verilen --kalite (stüdyonun kalite ön ayarı: pipeline/blender.py → KALITE_EEVEE)."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    K = json.loads(argv[argv.index("--kalite") + 1]) if "--kalite" in argv else {}
    eksik = [k for k in KALITE_ANAHTARLARI if k not in K]
    if eksik:
        raise SystemExit(f"EEVEE kalite ayarı eksik: {', '.join(eksik)} (pipeline/blender.py → KALITE_EEVEE)")
    return K


def varsayilan(sc):
    """Çizer EEVEE; sanat varsayılanları. Çalıştırıcının varsayilan()'ı (AgX, hareket bulanıklığı, kare aralığı) zaten kuruldu."""
    sc.render.engine = "BLENDER_EEVEE"
    e = sc.eevee
    e.use_shadows = True
    e.use_raytracing = True                   # yansıma, kırılma (cam), dolaylı ışık: ekran uzayında
    e.ray_tracing_method = "SCREEN"
    e.use_fast_gi = True                      # pürüzlü yüzeylerin dolaylı ışığı
    e.fast_gi_method = "GLOBAL_ILLUMINATION"
    e.use_bokeh_jittered = False              # alan derinliği süzgeçle: örnekli (titreşimli) hâli az örnekte yumuşak gölgeyi karıncalandırıyor


def _gecirgen(N) -> tuple[bool, bool]:
    """(kırılan, ince ışık geçiren): Principled'ın iletimi (bağlı ya da > 0), cam ve kırılma düğümü · Translucent BSDF."""
    kirilan = any(n.type in ("BSDF_GLASS", "BSDF_REFRACTION") or (n.type == "BSDF_PRINCIPLED" and (
        n.inputs["Transmission Weight"].is_linked or n.inputs["Transmission Weight"].default_value > 0)) for n in N)
    return kirilan, any(n.type == "BSDF_TRANSLUCENT" for n in N)


def uyarla():
    """Asıl sahneden sonra: kit malzemeleri (kit.cam, kit.kil(gecirgen=…)) EEVEE'nin varsayılanında Cycles'tan çok ayrışıyor.
    Ölçüm (denemeler/blender_eevee/OKU.md): kit.cam ışın izlenmiş kırılma olmadan opak koyu gri; ince bez küre kalınlığıyla koyu.
    Malzeme verisinin ayarıdır (düğüm ağacına dokunmaz); Cycles bunları okumaz."""
    for m in bpy.data.materials:
        if not (m.use_nodes and m.node_tree) or m.get("eevee_uyarla", True) is False:
            continue
        kirilan, ince = _gecirgen(m.node_tree.nodes)
        if kirilan:
            m.use_raytrace_refraction = True
        if ince and not kirilan:
            m.thickness_mode = "SLAB"


def zorla(sc, K):
    """Kalite ve kararlılık stüdyonundur: sahne ne yazarsa yazsın burada sabitlenir (parmak izi bunlarla hesaplanır)."""
    if sc.render.engine != "BLENDER_EEVEE":
        raise SystemExit("Sahne çizeri değiştirdi: EEVEE filminde sc.render.engine'e dokunma (script.json → blender.cizer)")
    e = sc.eevee
    e.taa_render_samples = int(K["ornek"])
    e.shadow_resolution_scale = float(K["golge"])
    e.shadow_ray_count = int(K["golge_isin"])
    e.shadow_step_count = int(K["golge_adim"])
    e.ray_tracing_options.resolution_scale = str(int(K["isin"]))
    e.motion_blur_steps = int(K["bulaniklik"])


def hucre(ad, renk, bant=3, golge=0.35, isik_payi=0.0):
    """Hücre boyası (toon, çizgi film): yüzeyin aldığı ışık bant sayısı kadar düz tona bölünür; en koyu bant renk × golge.
    renk: görünüşteki ad, '#rrggbb' ya da doğrusal (r, g, b) (kit.renk gibi). isik_payi 0..1: ışıktan bağımsız düz renk payı.
    Yalnız EEVEE (Shader to RGB); kit.kontur (Freestyle) ve görünüşte "bakis": "Standard" ile birlikte kullanılır."""
    if bpy.context.scene.render.engine != "BLENDER_EEVEE":
        raise SystemExit("eevee.hucre yalnız EEVEE filminde (script.json → blender.cizer: \"eevee\")")
    if bant < 2:
        raise SystemExit("eevee.hucre: bant ≥ 2")
    from kit import renk as _renk
    c = _renk(renk)
    ton = lambda i: (*(x * (golge + (1 - golge) * i / (bant - 1)) for x in c), 1)  # noqa: E731
    m = bpy.data.materials.new(ad)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.clear()
    d = N.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = N.new("ShaderNodeShaderToRGB")
    L.new(d.outputs["BSDF"], s2r.inputs["Shader"])
    bw = N.new("ShaderNodeRGBToBW")
    L.new(s2r.outputs["Color"], bw.inputs["Color"])
    rp = N.new("ShaderNodeValToRGB")
    rp.color_ramp.interpolation = "CONSTANT"
    el = rp.color_ramp.elements
    el[0].color = ton(0)
    el[1].position, el[1].color = 1 / bant, ton(1)
    for i in range(2, bant):   # yeni eleman sona eklenir: önceki başvurular kaymaz
        el.new(i / bant).color = ton(i)
    L.new(bw.outputs["Val"], rp.inputs["Fac"])
    em = N.new("ShaderNodeEmission")
    L.new(rp.outputs["Color"], em.inputs["Color"])
    out = N.new("ShaderNodeOutputMaterial")
    son = em.outputs["Emission"]
    if isik_payi > 0:
        sabit = N.new("ShaderNodeEmission")
        sabit.inputs["Color"].default_value = (*c, 1)
        k = N.new("ShaderNodeMixShader")
        k.inputs["Fac"].default_value = isik_payi
        L.new(son, k.inputs[1])
        L.new(sabit.outputs["Emission"], k.inputs[2])
        son = k.outputs["Shader"]
    L.new(son, out.inputs["Surface"])
    return m
