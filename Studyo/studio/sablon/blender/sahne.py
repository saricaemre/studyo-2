"""{{BASLIK}}: Blender sahnesi. Kit: blender/kit/ (import kit) · kurallar: blender/CLAUDE.md · ilk format: {{FORMAT}}.

Bu dosya yalnız sahneyi KURAR. Çizim ayarlarını (Cycles, örnek sayısı, çözünürlük, renk yönetimi) ve kareleri stüdyo yönetir:
./st kare / temsili / inceleme / render plakaları önbellekten verir, eksikleri 30 karelik ayrı Blender işleriyle çizer.
Kurallar kısaca: olay saatleri yalnız işaretlerden (kit.isaret('ad')), renk yalnız görünüşten (kit.renk('ad')), rastgelelik yalnız
tohumlu (kit.rastgele(n)), bütün hareket anahtar kare (saat, kare işleyicisi, pişirilmemiş fizik yok). Yazı ve logo burada değil,
Remotion üst katmanında (src/{{ID}}/Video.tsx). Her format ayrı kompozisyon: kadrajı ST.format / ST.dikey ile kur.
"""
import math

import kit
from kit import ST

# ---------------------------------------------------------------- olay saatleri (cues.json; iskelette işaret yoksa ilk saniye)
ZIPLA = min(ST.isaretler.values(), default=1.0)

# ---------------------------------------------------------------- malzemeler (renkler görünüşten; yedekler yalnız iskelet için)
# Malzeme ailesini filmin görüntü stili seçer (blender/CLAUDE.md → Malzeme ailesi): kit.kil / kit.kagit (maket), kit.plastik / kit.metal /
# kit.cam (ürün, nesne), kit.boya(duz=…) + kit.kontur (çizgi film boyası), kit.isik_malz (ışık). İskelet nötrdür: filmin dünyasıyla değiştir.
ZEMIN = kit.boya("zemin", kit.renk("arka", yedek="#E9E1D3"))
TOP = kit.plastik("top", kit.renk("vurgu", yedek="#D9480F"))

# ---------------------------------------------------------------- dünya ve ışık
kit.dunya(kit.renk("soluk", yedek="#3A3F4A"), 0.5)
kit.gunes("anahtar_isik", "#FFF1DC", 3.0, (math.radians(48), 0, math.radians(35)), aci=10)

# ---------------------------------------------------------------- iskelet: zemin ve zıplayan top (ölçek metre, serbest: burada top 6 cm)
kit.duzlem("zemin", 2.0, (0, 0, 0), ZEMIN)
top = kit.kure("top", 0.03, (0, 0, 0.03), TOP)
for t, z in ((0.0, 0.03), (ZIPLA, 0.03), (ZIPLA + 0.25, 0.10), (ZIPLA + 0.5, 0.03)):
    kit.anahtar(top, "location", z, t, indeks=2)

# ---------------------------------------------------------------- kamera: formatın kadrajı (dikeyde daha yakın ve yüksek)
odak = kit.bos("odak", (0, 0, 0.04))
kam, _ = kit.kamera(lens=50, fstop=6, odak=odak)
kam.location = (0, -0.42, 0.16) if ST.dikey else (0, -0.38, 0.10)
kit.izle(kam, odak)
