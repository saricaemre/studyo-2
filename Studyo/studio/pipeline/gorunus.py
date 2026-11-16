"""Görünüş denetimi ve deneme tabakası (./st gorunus).

Videoya özel görünüşün seçeneklerini (videos/<id>/gorunus.json) doğrular: yazı tipi listede mi, ağırlık var mı, renkler geçerli mi,
yazı/zemin kontrastı yeterli mi. Seçenekleri birbirleriyle (gerçekten farklı mı) ve önceki videolarla (aynı filmi mi izletiyor)
karşılaştırır. Kanca karesinin her seçenekle çizilmiş hâlini yan yana bir tabakaya koyar. Seçim kullanıcınındır (zanaat.md §1c).
"""
import datetime as dt
import json
import re
import subprocess
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageDraw

import kontak as K
import ortak as O

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
ROLLER = ("baslik", "govde", "aksan")
ROL_AD = {"baslik": "Başlık", "govde": "Gövde", "aksan": "Aksan"}
# Küçük harfleri de büyük harf olarak çizen yazı tipleri: "bir" → "BIR" olur (doğrusu BİR). Metin buyuk() ile yazılmalı.
YALNIZ_BUYUK = {"Bebas Neue"}


def fontlar() -> dict:
    r = subprocess.run(["node", "pipeline/fontlar.mjs"], cwd=O.ROOT, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def acik(h: str) -> bool:
    return O.kontrast(h, "#000000") > O.kontrast(h, "#FFFFFF")


def dogrula(S: dict, F: dict) -> dict:
    """Her seçenek için [(durum, mesaj)]. ❌ render'ı bozar ya da okunmaz; ⚠️ göz ister."""
    out = {}
    for k, o in S.items():
        rows = []
        R = o.get("renk", {})
        for alan in ("arka", "murekkep", "vurgu"):
            if alan not in R:
                rows.append(("❌", f"renk.{alan} yok"))
        for alan, h in R.items():
            if not HEX.match(str(h)):
                rows.append(("❌", f"renk.{alan} geçersiz: {h} (#rrggbb)"))
        Y = o.get("yazi", {})
        for rol in ROLLER:
            y = Y.get(rol)
            if not y:
                if rol != "aksan":
                    rows.append(("❌", f"yazi.{rol} yok"))
                continue
            f = F.get(y.get("aile"))
            if not f:
                rows.append(("❌", f"{ROL_AD[rol]}: “{y.get('aile')}” yazı tipi listesinde yok (src/lib/fontlar.ts)"))
                continue
            if y.get("agirlik") not in f["agirliklar"]:
                rows.append(("⚠️", f"{ROL_AD[rol]}: {y['aile']} {y.get('agirlik')} yok, en yakını kullanılır (var: {', '.join(map(str, f['agirliklar']))})"))
            if y.get("aile") in YALNIZ_BUYUK:
                rows.append(("⚠️", f"{ROL_AD[rol]}: {y['aile']} yalnız büyük harf çizer; metni buyuk() ile yaz (i → İ), yoksa “bir” BIR olur"))
            if y.get("italik") and not f["italik"]:
                rows.append(("⚠️", f"{ROL_AD[rol]}: {y['aile']} italik değil, düz kullanılır"))
        if not any(d == "❌" for d, _ in rows):
            z = R.get("kagit") or R["arka"]
            for alan, cita, sert in (("murekkep", 4.5, 3.0), ("vurgu", 3.0, 0), ("soluk", 3.0, 0)):
                if alan in R:
                    c = O.kontrast(R[alan], z)
                    if c < cita:
                        rows.append(("❌" if c < sert else "⚠️", f"{alan} / zemin {c:.1f}:1 (≥ {cita:g}:1 gerekir)"))
        out[k] = rows
    return out


# Yol bloğu (2a: planda üç yol). kredi_tahmini isteğe bağlı (Magnific, 3a).
YOL_ALANLARI = {"ad": "ad", "tek_cumle": "tek cümle", "yontem": "yöntem", "kural": "üretim kuralı", "kanca": "kanca (ilk 2 sn)",
                "olaganustu_an": "olağanüstü an", "insan_yolu": "insan / karakter yolu", "neden_akilda_kalir": "neden akılda kalır",
                "risk": "risk", "uretim": "üretim süresi"}


def yol_dogrula(S: dict, yol_modu: bool) -> dict:
    """Yol blokları: zorunlu alanlar dolu mu; yol modunda her seçenek bir yol mu ve üç yolun yöntemi farklı mı → {k: [(durum, mesaj)]}."""
    out = {k: [] for k in S}
    yontem = {}
    for k, o in S.items():
        y = o.get("yol")
        if not isinstance(y, dict):
            if yol_modu:
                out[k].append(("❌", "yol bloğu yok (yol modunda her seçenek bir yoldur: gorunus.json → secenekler.<harf>.yol)"))
            continue
        bos = [ad for alan, ad in YOL_ALANLARI.items() if not str(y.get(alan) or "").strip()]
        if bos:
            out[k].append(("❌", f"yol alanları boş: {', '.join(bos)}"))
        if y.get("kredi_tahmini") is not None and not isinstance(y.get("kredi_tahmini"), (int, float)):
            out[k].append(("⚠️", "yol.kredi_tahmini sayı olmalı (kredi yoksa 0)"))
        if str(y.get("yontem") or "").strip():
            yontem.setdefault(" ".join(O.norm_word(str(y["yontem"])).lower().split()), []).append(k)
    if yol_modu:  # üç yol yöntemde ayrışır (renkte değil); "bu yolda başka görünüş"te üç seçenek aynı yolu paylaşır
        for ks in yontem.values():
            if len(ks) > 1:
                for k in ks:
                    out[k].append(("❌", f"yöntem {', '.join(x.upper() for x in ks)} yollarında aynı: “{S[k]['yol']['yontem']}” (üç yol yöntemde ayrışır)"))
    return out


def ayirt(S: dict, F: dict, en_az: int = 3) -> list[str]:
    """Seçenek çiftleri en az `en_az` eksende ayrışmalı (serbest seçenek 3; aynı katalog stilinin varyasyonları 2); ayrışmayanlar için uyarı."""
    uyari = []
    for a, b in combinations(sorted(S), 2):
        A, B = S[a], S[b]
        try:
            fark = []
            if acik(A["renk"]["arka"]) != acik(B["renk"]["arka"]):
                fark.append("zemin açık/koyu")
            if O.renk_farki(A["renk"]["arka"], B["renk"]["arka"]) >= 12:
                fark.append("zemin rengi")
            if O.renk_farki(A["renk"]["vurgu"], B["renk"]["vurgu"]) >= 20:
                fark.append("vurgu rengi")
            ta, tb = (F.get(x["yazi"]["baslik"]["aile"], {}).get("tur") for x in (A, B))
            if ta != tb:
                fark.append("başlık yazı türü")
            if A["yazi"]["govde"]["aile"] != B["yazi"]["govde"]["aile"]:
                fark.append("gövde yazısı")
        except (KeyError, TypeError):
            continue
        if len(fark) < en_az:
            uyari.append(f"{a.upper()} ile {b.upper()} yeterince farklı değil: " + (f"yalnız {', '.join(fark)} ayrışıyor" if fark else "hiçbir eksende ayrışmıyor")
                         + f" (en az {en_az} eksen: zemin açık/koyu, zemin rengi, vurgu rengi, başlık yazı türü, gövde yazısı)")
    return uyari


def onceki(v: O.Video, S: dict) -> dict:
    """Her seçenek için iki ya da daha fazla ortak noktası olan önceki videolar: {k: [(id, [ortaklar])]}."""
    D = O.diger_gorunusler(v)
    out = {}
    for k, o in S.items():
        try:
            z = O.secenek_ozeti(o)
        except (KeyError, TypeError):
            continue
        out[k] = [(vid, m) for vid, w in D if len(m := O.benzerlik(z, w)) >= 2]
    return out


def _sar(d, text, fnt, width):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= width:
            cur = t
        else:
            out.append(cur)
            cur = w
    return out + ([cur] if cur else [])


def tabaka(v: O.Video, fmt: str, kareler: dict, S: dict, D: dict, A: list, onc: dict, frame: int, out_png: Path):
    """Kanca karesinin her seçenekle hâli yan yana + palet, yazı, kontrast ve benzerlik notları. Yol modunda her sütun bir yoldur:
    yol adı, yöntem ve tek cümle üstte, görünüş altta."""
    Fm = O.FORMATLAR[fmt]
    tw = 400 if Fm["h"] > Fm["w"] else 600
    th = round(tw * Fm["h"] / Fm["w"])
    keys = sorted(S)
    yollu = any(isinstance(S[k].get("yol"), dict) for k in keys)
    yol_modu = bool((v.gorunus_json() or {}).get("yol_modu"))
    PAD, GAP, NOT_H = 28, 28, 330 + (250 if yollu else 0)
    W = PAD * 2 + len(keys) * tw + (len(keys) - 1) * GAP
    H = 120 + th + NOT_H + (34 * len(A)) + PAD
    BG, FG, DIM, UY = (24, 22, 20), (236, 232, 224), (150, 144, 134), (232, 140, 60)
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_t, f_b, f_r, f_s = K.font(30, True), K.font(24, True), K.font(18), K.font(16)
    d.text((PAD, 24), f"{'YOL' if yol_modu else 'GÖRÜNÜŞ'} DENEMESİ · {v.id} · {fmt} · kare f{frame} ({O.tc(frame / v.fps)}) · {dt.date.today().isoformat()}",
           font=f_t, fill=FG)
    d.text((PAD, 66), ("Üç yol: her biri kendi fikri, yöntemi, kanca karesi ve görünüşüyle. Seçim senin: panelde “Bu yolu seç”." if yol_modu else
                       "Aynı kanca karesi, üç görünüş. Seçim senin: panelde “Bunu seç” ya da ./st gorunus <id> sec <harf>."), font=f_r, fill=DIM)
    y0 = 108
    for i, k in enumerate(keys):
        x = PAD + i * (tw + GAP)
        o = S[k]
        Y_ = o.get("yol") if isinstance(o.get("yol"), dict) else None
        if k in kareler:
            im.paste(Image.open(kareler[k]).convert("RGB").resize((tw, th)), (x, y0))
        y = y0 + th + 14
        if Y_ and yol_modu:  # yol: ad, yöntem, tek cümle; görünüş ikinci sırada
            d.text((x, y), f"{k.upper()} · {Y_.get('ad', '')}", font=f_b, fill=FG)
            y += 34
            d.text((x, y), f"Yöntem: {Y_.get('yontem', '')}", font=f_r, fill=UY)
            y += 26
            for ln in _sar(d, Y_.get("tek_cumle", ""), f_r, tw)[:4]:
                d.text((x, y), ln, font=f_r, fill=FG)
                y += 23
            for et, alan in (("Kural", "kural"), ("Olağanüstü an", "olaganustu_an")):
                for ln in _sar(d, f"{et}: {Y_.get(alan, '')}", f_s, tw)[:3]:
                    d.text((x, y), ln, font=f_s, fill=DIM)
                    y += 20
            y += 8
            d.text((x, y), f"Görünüş: {o.get('ad', '')}", font=f_r, fill=FG)
            y += 26
        else:
            d.text((x, y), f"{k.upper()} · {o.get('ad', '')}", font=f_b, fill=FG)
            y += 34
            if Y_:  # bu yolda başka görünüş: üç seçenek aynı yolu paylaşır
                d.text((x, y), f"Yol: {Y_.get('ad', '')} · {Y_.get('yontem', '')}", font=f_r, fill=UY)
                y += 26
        for ln in _sar(d, o.get("fikir", ""), f_r, tw)[:4 if not (Y_ and yol_modu) else 2]:
            d.text((x, y), ln, font=f_r, fill=DIM)
            y += 23
        y += 8
        R = o.get("renk", {})
        sx = x
        renkler = [R[a] for a in ("arka", "kagit", "murekkep", "vurgu", "ikincil", "soluk")
                   if R.get(a) and HEX.match(R[a]) and not (a == "kagit" and R[a].lower() == R.get("arka", "").lower())]
        sg = min(70, (tw - 10 * (len(renkler) - 1)) // max(1, len(renkler)))  # sütuna sığsın (yanındakine taşmasın)
        for h in renkler:
            d.rectangle([sx, y, sx + sg, y + 30], fill=h, outline=(90, 86, 80))
            d.text((sx, y + 34), h.upper(), font=K.font(13 if sg >= 62 else 11), fill=DIM)
            sx += sg + 10
        y += 58
        Y = o.get("yazi", {})
        for rol in ROLLER:
            r = Y.get(rol)
            if r:
                d.text((x, y), f"{ROL_AD[rol]}: {r.get('aile')} {r.get('agirlik')}{' italik' if r.get('italik') else ''}", font=f_r, fill=FG)
                y += 23
        y += 6
        for durum, m in D.get(k, []):
            for ln in _sar(d, ("SORUN: " if durum == "❌" else "DİKKAT: ") + m, f_s, tw)[:2]:
                d.text((x, y), ln, font=f_s, fill=(235, 90, 70) if durum == "❌" else UY)
                y += 20
        for vid, m in onc.get(k, []):
            for ln in _sar(d, f"{vid} videosuna benziyor: {', '.join(m)}", f_s, tw)[:2]:
                d.text((x, y), ln, font=f_s, fill=UY)
                y += 20
    y = y0 + th + NOT_H
    for a in A:
        d.text((PAD, y), "DİKKAT: " + a, font=f_r, fill=UY)
        y += 34
    out_png.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_png)


def rapor_md(v: O.Video, S: dict, D: dict, A: list, onc: dict, frame: int, tabakalar: dict) -> str:
    yol_modu = bool((v.gorunus_json() or {}).get("yol_modu"))
    L = [f"# {'Yol' if yol_modu else 'Görünüş'} denemesi — {v.id} · {dt.date.today().isoformat()}", "",
         (f"> Üç yolun kanca karesi (f{frame}, {O.tc(frame / v.fps)}) her biri kendi sahnesi ve görünüşüyle çizildi. **Seçim kullanıcının** (panel → “Bu yolu seç”)."
          if yol_modu else
          f"> Kanca karesi f{frame} ({O.tc(frame / v.fps)}) üç görünüşle çizildi. **Seçim kullanıcının** (panel ya da `./st gorunus {v.id} sec <harf>`)."),
         "> Ölçüt: zanaat.md §1c. Benzerlik: zemin rengi, vurgu rengi, başlık ve gövde yazısından ikisi ya da fazlası ortaksa uyarılır.", ""]
    L += [f"![{fmt}]({Path(p).name})" for fmt, p in tabakalar.items()] + [""]
    L += ["| | Görünüş | Fikir | Zemin / mürekkep / vurgu | Başlık · gövde | Denetim | Önceki videolara benzerlik |", "|---|---|---|---|---|---|---|"]
    for k in sorted(S):
        o = S[k]
        R, Y = o.get("renk", {}), o.get("yazi", {})
        den = "; ".join(f"{d} {m}" for d, m in D.get(k, [])) or "✅"
        ben = "; ".join(f"⚠️ {vid}: {', '.join(m)}" for vid, m in onc.get(k, [])) or "✅ belirgin benzerlik yok"
        L.append(f"| **{k.upper()}** | {o.get('ad', '')} | {o.get('fikir', '')} | `{R.get('arka')}` / `{R.get('murekkep')}` / `{R.get('vurgu')}` | "
                 f"{Y.get('baslik', {}).get('aile')} {Y.get('baslik', {}).get('agirlik')} · {Y.get('govde', {}).get('aile')} {Y.get('govde', {}).get('agirlik')} | {den} | {ben} |")
    if A:
        L += ["", "## Seçenekler arası"] + [f"- ⚠️ {a}" for a in A]
    yollar = {k: S[k]["yol"] for k in sorted(S) if isinstance(S[k].get("yol"), dict)}
    if yollar:
        hucre = lambda s: str(s if s is not None else "").replace("|", "/").replace("\n", " ")  # noqa: E731
        L += ["", "## Yollar" + (" (planda üç yol; seçim kullanıcının)" if (v.gorunus_json() or {}).get("yol_modu") else " (aynı yol, başka görünüşler)"), "",
              "| | " + " | ".join(a[0].upper() + a[1:] for a in YOL_ALANLARI.values()) + " | Kredi |", "|---|" + "---|" * (len(YOL_ALANLARI) + 1)]
        for k, y in yollar.items():
            L.append(f"| **{k.upper()}** | " + " | ".join(hucre(y.get(alan)) for alan in YOL_ALANLARI) + f" | {hucre(y.get('kredi_tahmini', '—'))} |")
    return "\n".join(L) + "\n"
