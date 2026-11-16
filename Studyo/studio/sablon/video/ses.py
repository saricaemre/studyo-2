"""{{BASLIK}} — ses tasarımı. Motor: pipeline/sfx.py (efekt kütüphanesi + miks + −14 LUFS).

tasarla(L, fx, beds, c, sents, dur) çağrılır:
  L     efekt kütüphanesi (L.wood_tok(), L.stamp(), L.ney(), L.whoosh(), L.gate() …;
        çizgi film ailesi: L.tik(), L.baloncuk(f0, f1), L.yay(), L.can(midi), L.parilti(), L.gum(), L.tebesir(), L.konfeti())
  fx    efekt kanalı: fx.add(sinyal, zaman_sn, dB, pan)
  beds  ortam kanalı (anlatım altında otomatik kısılır)
  c     işaretler {ad: saniye}: görüntüyle aynı zamanlar
  sents cümleler {id: {start, end, words}}
Dönüş: {"hush": [(başla, bitir), ...]} → bu aralıklarda her şey kısılır (bilinçli sessizlik).
"""


def tasarla(L, fx, beds, c, sents, dur):
    # Örnek: mühür darbesi + ney
    if "seal" in c:
        fx.add(L.stamp(), c["seal"], -7)
        fx.add(L.ney(293.66, 3.2), c["seal"] + 0.05, -15)
    return {"hush": []}
