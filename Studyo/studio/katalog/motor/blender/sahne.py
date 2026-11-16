"""Motor önizlemesi · Blender (yeni film levhasındaki "Motor" seçimi): Blender'ın bir tarza bağlı olmadığını gösteren stüdyo sahnesi.

Döner tablada beş malzeme ailesi yan yana: krom (metal), cam, vernikli plastik, mat boya, kil. Kamera 3 sn'de yavaşça yaklaşır,
anahtar ışık üstlerinden geçer. Renkler görünüşün adlı renklerinden (arka, murekkep, vurgu, ikincil, soluk). Gerçek videonun örneği değildir;
malzeme ailesini filmin görüntü stili seçer (blender/CLAUDE.md → Malzeme ailesi). Ölçek metre: nesneler 10–20 cm.
Üretim: ./st katalog motor --yeniden (9x16, taslak, 90 kare → katalog/onizleme/motor/blender.mp4 + .png).
"""
import math

import bpy

import kit
from kit import ST

sc = bpy.context.scene
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = 0.0

# ---------------------------------------------------------------- dünya, ışık
kit.dunya(kit.renk("soluk", yedek="#5E6670"), 0.55)
anahtar, A = kit.gunes("anahtar", "#FFF4E6", 3.2, (math.radians(55), 0, math.radians(-30)), aci=14)
kit.gunes("kontur_isik", "#CFE0FF", 1.6, (math.radians(70), 0, math.radians(160)), aci=6)

# ---------------------------------------------------------------- stüdyo zemini (kavisli fon yerine geniş disk + uzak fon)
fon = kit.boya("fon", kit.renk("arka", yedek="#ECEAE6"), puruz=1.0)
kit.silindir("tabla", 0.42, 0.03, (0, 0, -0.015), kit.boya("tabla", kit.renk("arka", yedek="#ECEAE6"), puruz=0.7), kenar=96)
kit.duzlem("zemin", 6.0, (0, 0, -0.03), fon)
arka = kit.duzlem("arka_fon", 6.0, (0, 1.6, 1.0), fon)
arka.rotation_euler = (math.radians(90), 0, 0)

# ---------------------------------------------------------------- beş malzeme ailesi (tabla döner)
tabla = kit.bos("donen", (0, 0, 0))
kit.kure("krom", 0.075, (-0.20, 0.05, 0.075), kit.metal("krom", "#D7DADF", puruz=0.08), ebeveyn=tabla)
kit.kure("cam", 0.08, (0.02, -0.16, 0.08), kit.cam("cam", "#FFFFFF", puruz=0.01), ebeveyn=tabla)
kit.silindir("plastik", 0.07, 0.19, (0.21, 0.04, 0.095), kit.plastik("plastik", kit.renk("vurgu", yedek="#E4572E"), puruz=0.28), ebeveyn=tabla, kenar=64)
kit.koni("boya", 0.08, 0.0, 0.17, (0.0, 0.2, 0.085), kit.boya("boya", kit.renk("ikincil", yedek="#2F5D8A")), ebeveyn=tabla)
kit.kure("kil", 0.055, (-0.06, -0.02, 0.055), kit.kil("kil", kit.renk("murekkep", yedek="#C98B5B"), olcek=1.0), ebeveyn=tabla)
kit.anahtar(tabla, "rotation_euler", 0.0, 0.0, indeks=2)
kit.anahtar(tabla, "rotation_euler", math.radians(40), ST.sure, indeks=2)
kit.yumusat(tabla, "LINEAR")

# ---------------------------------------------------------------- ışık geçişi ve kamera (formatın kadrajı)
kit.anahtar(anahtar, "rotation_euler", math.radians(-55), 0.0, indeks=2)
kit.anahtar(anahtar, "rotation_euler", math.radians(-5), ST.sure, indeks=2)
odak = kit.bos("odak", (0, 0, 0.1))
kam, _ = kit.kamera(lens=50, fstop=4.0, odak=odak, yakin=0.01, uzak=20.0)
uzak = 1.05 if ST.dikey else 0.85
for t, k in ((0.0, 1.0), (ST.sure, 0.88)):
    kit.anahtar(kam, "location", (0, -uzak * k, 0.3 * k), t)
kit.yumusat(kam, "SINE")
kit.izle(kam, odak)
