"""Ölçüm: videonun profilindeki (profiller/<ad>.json) çıtaları senaryo, zaman çizelgesi, miks ve render üzerinden ölçer.

Her satır bir kanıttır: değer + çıta + durum. "Bence iyi oldu" yerine "kanca 4,49 sn, çıta 3 sn".
Durumlar: ✅ geçti · ❌ kaldı · ⚠️ şüpheli / insan bakmalı · 👁 yalnız göz kontrolü
"""
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

import benzerlik
import ortak as O

OK, FAIL, WARN, EYE = "✅", "❌", "⚠️", "👁"

GOZ_GENEL = [
    "Kanca: ilk 2 sn'de izleyiciyi tutan gerçek bir görüntü var",
    "Metin telefon boyutunda okunuyor (kontak küçük resminde okunabiliyor mu?)",
    "Tip, renk ve öğeler sahneler arasında tutarlı",
    "Geçişlerde yarım kalmış ya da çirkin ara kare yok (şeritler)",
    "Her hareketten sonra nereye bakılacağı belli",
    "Son kare poster olacak kadar güçlü",
]


def _row(ad, deger, cita, durum, kanit=""):
    return {"ad": ad, "deger": deger, "cita": cita, "durum": durum, "kanit": kanit}


def _rng(r):
    return f"{r[0]:g}–{r[1]:g}"


# Anlatımsız filmde mesajı taşıyan ilk yazı olayı: işaret adı (k_yazi, baslik, m_cta …) ya da kanca vuruşunun olayında tırnaklı yazı
YAZI_ISARETI = re.compile(r"(?:^|_)(?:yazi|baslik|metin|mesaj|slogan|cta|soru|cumle|altyazi|title|text)(?:_|\d|$)")
TIRNAK = re.compile(r"['‘’\"“”«][^'‘’\"“”«»]{2,}['‘’\"“”»]")


def _mesaj_satiri(v: O.Video, S, P):
    """İlk saniyelerde mesaj (anlatımsız; anlatımlıda ilk cümle sonu zaten ölçülür): ana mesajı taşıyan olay en geç kanca_mesaj_sn'de
    (varsayılan 3 sn; TikTok: en çok tıklanan reklamların %63'ü ana mesajı ilk 3 sn'de veriyor, yol-haritasi/arastirma.md §3).
    Taşıyıcı: script.json → mesaj_isareti > ilk yazı olayı > kanca olayı (yazısız filmde mesajı ana nesne taşır). Sezgisel: ⚠️, ❌ değil."""
    cita = float(P.get("kanca_mesaj_sn", 3.0))
    ad = v.script.get("mesaj_isareti")
    if ad:
        if ad not in v.cues:
            return _row("İlk saniyelerde mesaj (anlatımsız)", f"işaret yok: {ad}", f"≤ {cita:g} sn", WARN, "script.json → mesaj_isareti bir işaret adı olmalı (cues.json)")
        t, neden = v.cues[ad], "script.json → mesaj_isareti"
    else:
        yazi = sorted((t, k) for k, t in v.cues.items() if not k.startswith("poster") and YAZI_ISARETI.search(k))
        kc = v.keyword_cue(S[0]["id"])
        if kc and TIRNAK.search(str(v.script_sentence(S[0]["id"]).get("shot", {}).get("olay") or "")):
            yazi = sorted(yazi + [(kc[1], kc[0])])  # kanca olayı ekrana yazı getiriyor
        if yazi:
            (t, ad), neden = yazi[0], "ilk yazı olayı"
        elif kc:
            (ad, t), neden = kc, "yazısız film: kanca olayı (ana nesne)"
        else:
            return None
    done = t + 0.25
    return _row("İlk saniyelerde mesaj (anlatımsız, sezgisel)", f"{done:.2f} sn", f"≤ {cita:g} sn (olay + giriş)", OK if done <= cita else WARN,
                f"{ad} @ {O.tc(t)} · {neden}" + ("; bilerek geç geliyorsa ya da mesajı başka bir olay taşıyorsa script.json → mesaj_isareti" if done > cita else ""))


def altyazi_bandi(fmt: str) -> tuple[str, str]:
    """Ortak altyazı bandı (components/Captions.tsx; profiller/formatlar.json → altyazi) bu formatta güvenli alanın içinde mi → (durum, mesaj)."""
    F = O.FORMATLAR[fmt]
    w, h, A, G = F["w"], F["h"], F["altyazi"], F["guvenli"]
    yan = A["yan"] * (1 if w > h else min(w, h) / 1080)  # Captions.tsx ile aynı hesap: bant [yan, w − yan] × [ust, ust + yukseklik]
    tas = {"solda": G["sol"] * w - yan, "sağda": G["sag"] * w - yan, "üstte": (G["ust"] - A["ust"]) * h, "altta": (A["ust"] + A["yukseklik"] + G["alt"] - 1) * h}
    kotu = {k: x for k, x in tas.items() if x > 0.5}
    return (WARN if kotu else OK, f"[{fmt}] altyazı bandı " + (", ".join(f"{k} {x:.0f} px" for k, x in kotu.items())
            + " güvenli alanın dışına taşabilir (uzun satırda platform düğmelerinin altına girer). Ortak ayar (profiller/formatlar.json → altyazi):"
            " değiştirmek bütün filmlerin karelerini değiştirir, kullanıcıya sor; tek film için kısa satır ya da küçük punto (stil.punto)"
            if kotu else "güvenli alanın içinde"))


def guvenli_denetimi(v: O.Video) -> list[tuple[str, str]]:
    """Yazı güvenli alanda (statik): bileşenler yazı kutularını kare başına raporlamadığı için kod ve format tanımı denetlenir.
    1) Ortak altyazı bandı (components/Captions.tsx; profiller/formatlar.json → altyazi) her formatta güvenli alanın içinde mi
       (yalnız anlatımlı ve altyazısı olan filmde). 2) Sahne kodu güvenli alanı okuyor mu: Remotion ve Blender üst katmanında
       useFormat().safe ya da guvenli; HyperFrames'te ST.guvenli. Okumuyorsa yazılar elle yerleştirilmiştir: kontak tabakasındaki
       kesik çizgili kutuya göz bakar. → [(durum, mesaj)]"""
    out = []
    if v.motor == "hyperframes":
        d = O.ROOT / "hf" / v.id
        kod = "\n".join(re.sub(r"<script id=\"st-veri\">.*?</script>", "", f.read_text(), flags=re.S)
                        for f in [d / "index.html", *(d / "compositions").rglob("*.html")] if f.exists())
        altyazi = "ST.altyazi" in kod
        okur = bool(re.search(r"ST\.guvenli|--guvenli", kod))
        ipucu = "ST.guvenli"
    else:
        kod = "\n".join(f.read_text() for f in v.kod_dizini.rglob("*.ts*")) if v.kod_dizini.exists() else ""
        altyazi = "<Captions" in kod
        okur = bool(re.search(r"\bsafe\b|guvenli", kod))
        ipucu = "useFormat().safe"
    if not kod:
        return out
    if altyazi and v.anlatim:
        for fmt in v.formatlar:
            out.append(altyazi_bandi(fmt))
    out.append((OK, f"sahne kodu güvenli alanı okuyor ({ipucu})") if okur else
               (WARN, f"sahne kodu güvenli alanı okumuyor ({ipucu} yok): yazılar elle yerleştirilmiş; kontak tabakasındaki kesik çizgili kutuya bak"))
    return out


def measure(v: O.Video, renders: dict | None = None, frames_dir: Path | None = None, teslim: bool = False):
    """renders: {format: mp4}. teslim=True → teslim dosyası denetimleri de yapılır."""
    P = v.profil
    S = v.timeline["sentences"]
    renders = renders or {}
    rows = [_row("Profil", f"{P['ad']} · {', '.join(v.formatlar)}", "", "—", P.get("aciklama", ""))]

    # --- yapı
    d = v.duration
    rows.append(_row("Süre", f"{d:.2f} sn", f"{_rng(P['sure'])} sn", OK if P["sure"][0] <= d <= P["sure"][1] else FAIL))
    s1 = S[0]
    kc1 = v.keyword_cue(s1["id"])
    if v.anlatim or not kc1:
        rows.append(_row("Kanca bitişi (ilk cümle sonu)", f"{s1['end']:.2f} sn", f"≤ {P['kanca_sn']:g} sn",
                         OK if s1["end"] <= P["kanca_sn"] else FAIL, f"{s1['id']}: “{v.text_of(s1['id'])}”"))
    else:  # anlatımsız: kanca görüntüsünün tamamlandığı an (olay işareti + giriş süresi); bölüm sınırı müziğin ölçüsüdür
        done = kc1[1] + 0.25
        rows.append(_row("Kanca tamamlanma (kanca olayı + giriş)", f"{done:.2f} sn", f"≤ {P['kanca_sn']:g} sn",
                         OK if done <= P["kanca_sn"] else FAIL, f"{kc1[0]} @ {O.tc(kc1[1])} · {s1['id']}: “{v.text_of(s1['id'])}”"))
    if not v.anlatim and (r := _mesaj_satiri(v, S, P)):
        rows.append(r)
    steps = [s["step"] for s in S]
    order = v.vuruslar  # filmin yapısı (script.json → yapi) ya da profilin önerisi
    unknown = [x for x in steps if x not in order]
    missing = [x for x in order if x not in steps]
    idx = [order.index(x) for x in steps if x in order]
    ok_order = idx == sorted(idx) and not unknown and not missing
    rows.append(_row("Vuruş iskeleti", " → ".join(dict.fromkeys(steps)), ("film yapısı: " if v.yapi else "") + " → ".join(order), OK if ok_order else FAIL,
                     "; ".join(filter(None, [("eksik: " + ", ".join(missing)) if missing else "",
                                             ("tanımsız: " + ", ".join(unknown)) if unknown else "",
                                             "" if idx == sorted(idx) else "sıra bozuk"]))))

    # --- anlatım
    if v.anlatim and P.get("wpm"):
        nw = [len(s["words"]) for s in S]
        span = S[-1]["end"] - S[0]["start"]
        wpm = sum(nw) / span * 60
        rows.append(_row("Anlatım temposu", f"{wpm:.0f} kelime/dk ({sum(nw)} kelime / {span:.1f} sn)", _rng(P["wpm"]),
                         OK if P["wpm"][0] <= wpm <= P["wpm"][1] else WARN))
        longest = max(S, key=lambda s: len(s["words"]))
        rows.append(_row("Cümle uzunluğu", f"ort {np.mean(nw):.1f} · en uzun {max(nw)} ({longest['id']})",
                         f"ort ≤ {P['cumle_ort']:g} · en uzun ≤ {P['cumle_max']}",
                         OK if np.mean(nw) <= P["cumle_ort"] and max(nw) <= P["cumle_max"] else FAIL))

    # --- her vuruşta bir olay (anlatımlıda anahtar kelimede)
    bad, details = [], []
    for s in S:
        kc = v.keyword_cue(s["id"])
        shot = v.script_sentence(s["id"]).get("shot", {})
        if not kc:
            bad.append(s["id"])
            details.append(f"{s['id']}: “{shot.get('anahtar') or shot.get('isaret') or '—'}” için işaret yok")
            continue
        name, t = kc
        if v.anlatim and shot.get("anahtar") and not shot.get("isaret"):
            w = next(x for x in s["words"] if O.norm_word(x["text"]).lower() == O.norm_word(shot["anahtar"]).lower())
            lead_f = (w["start"] - t) * v.fps
            if not (-0.5 <= lead_f <= P["senkron_kare"] + 0.5):
                bad.append(s["id"])
                details.append(f"{s['id']}: {name} kelimeden {lead_f:+.1f} kare önce")
        elif not (s["start"] - 0.05 <= t <= s["end"] + 0.05):
            bad.append(s["id"])
            details.append(f"{s['id']}: {name} vuruşun dışında ({O.tc(t)})")
    rows.append(_row("Her vuruşta ekranda bir olay", f"{len(S) - len(bad)}/{len(S)} vuruş",
                     f"anahtar kelimeden 0–{P['senkron_kare']} kare önce" if v.anlatim else "vuruşun içinde",
                     OK if not bad else FAIL, "; ".join(details)))

    # --- müzik ızgarası: kesmeler vuruşa oturuyor mu?
    if v.beats:
        B = np.array(v.beats)
        offs = {k: (t - B[np.argmin(np.abs(B - t))]) * v.fps for k, t in v.cues.items()}  # işaretçiler de ızgarada olmalı
        off_grid = {k: f for k, f in offs.items() if abs(f) > P["senkron_kare"] + 0.5}
        bpm = v.timeline.get("bpm")
        rows.append(_row("İşaretler müzik vuruşuna oturuyor",
                         f"{len(offs) - len(off_grid)}/{len(offs)} işaret" + (f" · {bpm:.1f} BPM" if bpm else ""),
                         f"en yakın vuruşa ≤ {P['senkron_kare']} kare", OK if not off_grid else (WARN if v.anlatim else FAIL),
                         ", ".join(f"{k} {f:+.1f}k" for k, f in sorted(off_grid.items(), key=lambda kv: v.cues[kv[0]]))))

    events = {k: t for k, t in v.cues.items() if not k.startswith("poster")}  # poster bir kare işaretçisidir, olay değil
    times = sorted(events.values())
    edges = [0.0] + times + [d]
    gaps = [(b - a, a, b) for a, b in zip(edges[:-1], edges[1:])]
    long_gaps = [g for g in gaps if g[0] > P["olay_bosluk_sn"]]
    worst = max(gaps)
    rows.append(_row("En uzun olaysız aralık (işaretlere göre)", f"{worst[0]:.2f} sn ({O.tc(worst[1])}–{O.tc(worst[2])})",
                     f"≤ {P['olay_bosluk_sn']:g} sn", OK if not long_gaps else FAIL,
                     "; ".join(f"{O.tc(a)}–{O.tc(b)} ({g:.1f} sn)" for g, a, b in long_gaps)))

    # --- katalog: animasyon tipinin tempo hedefi ve ses stili (bilgi; zanaat ve katalog tarifleri)
    kat = v.script.get("katalog") or {}
    if kat.get("animasyon"):
        tp = O.ROOT / "katalog" / "animasyon" / f"{kat['animasyon']}.json"
        if tp.exists():
            lo, hi = O.jload(tp)["tempo"]["olay_aralik_sn"]
            ort = float(np.mean(np.diff(times))) if len(times) > 1 else d
            rows.append(_row(f"Animasyon tipi ({kat['animasyon']}): olaylar arası ortalama", f"{ort:.2f} sn", f"{lo:g}–{hi:g} sn (tarif)",
                             OK if lo * 0.7 <= ort <= hi * 1.3 else WARN))
    if v.ses.get("stil"):
        rows.append(_row("Ses stili", f"{v.ses['stil']} · müzik kaynağı {v.ses.get('muzik_kaynagi', 'kod')}", "", "—"))
    esin = v.script.get("esin") or {}
    if esin:  # esin kartları: başlangıç noktası, tarif değil (ölçüt yok, yalnız bilgi)
        rows.append(_row("Katalog esin kartları", " · ".join(f"{t}: {', '.join(a)}" for t, a in esin.items()), "", "—"))
    if v.script.get("cesaret"):
        rows.append(_row("Cesaret (kullanıcının seçimi)", v.script["cesaret"], "", "—"))

    # --- render üstünde (her format ayrı)
    motions = {}
    for fmt, mp4 in renders.items():
        if not (mp4 and mp4.exists()):
            continue
        F = O.FORMATLAR[fmt]
        fr = O.gray_frames(mp4, *O.motion_size(F["w"], F["h"]), fps=v.fps)
        motion = O.motion_of(fr)
        motions[fmt] = motion
        fl = O.flash_frames(fr, motion)
        if fmt == "9x16" and d <= 60 and not P.get("dongu") and len(fr) > 1:  # kısa dikey: akış tekrarları sayar, kendine dönen film izlenme süresini uzatır
            sim = 1 - np.abs(fr[0] - fr[-1]).mean() / 255
            rows.append(_row(f"[{fmt}] Döngü önerisi (ilk kare ↔ son kare)", f"%{sim * 100:.0f}", "öneri: ≥ %85 ise film kendine döner (Shorts tekrarı sayar)",
                             "—", "" if sim >= 0.85 else "son kare ilk kareye bağlanırsa izleyici fark etmeden yeniden izler"))
        rows.append(_row(f"[{fmt}] Tek karelik sıçrama", f"{len(fl)} kare", "0 (bir kare boyunca beliren ya da kaybolan öğe)", FAIL if fl else OK,
                         ", ".join(f"f{i} ({O.tc(i / v.fps)})" for i in fl[:8])))
        bl = O.blank_runs(fr)
        tot = sum(b - a for a, b, _ in bl) / v.fps
        uzun = max([(b - a) / v.fps for a, b, _ in bl] or [0])
        rows.append(_row(f"[{fmt}] Boş ekran (tek renk)", f"toplam {tot:.2f} sn · en uzun {uzun:.2f} sn",
                         "en uzun ≤ 0,5 sn · toplam ≤ 1 sn; fazlası gerekçesiyle (shot.gecis, zanaat.md §3)", WARN if uzun > 0.5 or tot > 1.0 else OK,
                         "; ".join(f"{O.tc(a / v.fps)} · {(b - a) / v.fps:.2f} sn · gri {g}" for a, b, g in bl if b - a > 1)))
        weak = []
        for name, t in sorted(events.items(), key=lambda kv: kv[1]):
            f = int(round(t * v.fps))
            win = motion[max(1, f - 4): f + 7]
            base = np.median(motion[max(1, f - 36): f + 36]) + 0.05
            if len(win) == 0 or win.max() / base < 1.35:
                weak.append(f"{name}@{O.tc(t)} ({win.max() / base if len(win) else 0:.2f})")
        rows.append(_row(f"[{fmt}] İşaret anında görsel değişim (sezgisel)", f"{len(events) - len(weak)}/{len(events)} işaret",
                         "işaretin −4/+6 karesinde belirgin değişim", OK if not weak else WARN,
                         ("zayıf (tepe/taban): " + ", ".join(weak)) if weak else ""))
        # Sezgisel: ortalama kare farkı ince çizgili/küçük olayları (yeni beliren kontur, küçük yazı) kaçırabilir.
        # İçinde planlı olay olmayan donuk aralık kesin ölü zamandır (❌); olay varsa göz doğrular (⚠️).
        runs = O.still_runs(motion, P["olay_bosluk_sn"], fps=v.fps)
        dead = [(a, b) for a, b in runs if not any(a / v.fps <= t <= b / v.fps for t in events.values())]
        hint = [(a, b, [k for k, t in events.items() if a / v.fps <= t <= b / v.fps]) for a, b in runs if (a, b) not in dead]
        rows.append(_row(f"[{fmt}] Donuk aralık (görüntü kıpırdamıyor, sezgisel)",
                         f"{len(runs)} aralık" + (f", en uzun {max(b - a for a, b in runs) / v.fps:.1f} sn" if runs else ""),
                         f"hiçbir aralık > {P['olay_bosluk_sn']:g} sn değil", FAIL if dead else (WARN if runs else OK),
                         "; ".join([f"{O.tc(a / v.fps)}–{O.tc(b / v.fps)} olaysız" for a, b in dead] +
                                   [f"{O.tc(a / v.fps)}–{O.tc(b / v.fps)} içinde {', '.join(ks)} var ama görünür değişim zayıf: kontakta doğrula" for a, b, ks in hint])))

    # --- stil: yazı rengi ile zemin arasındaki kontrast (WCAG; zanaat.md §4). Palet değişikliği kullanıcı kararıdır: yalnız uyarır.
    R = O.gorunus_renkleri(v)
    zemin = R.get("kagit") or R.get("arka")
    if zemin:
        for k, ad, alt in (("murekkep", "mürekkep", 4.5), ("soluk", "soluk", 4.5), ("vurgu", "vurgu", 3.0)):
            if k in R:
                c = O.kontrast(R[k], zemin)
                not_ = "" if c >= alt else ("yalnız büyük, kalın yazıda (≥ 3:1)" if c >= 3 else "yazıda kullanma: yalnız şekil ve çizgi")
                rows.append(_row(f"Stil kontrastı · {ad} / zemin", f"{c:.1f}:1 ({R[k]} / {zemin})", f"≥ {alt:g}:1",
                                 OK if c >= alt else WARN, not_))
    z = O.gorunus_ozeti(v)
    if z:
        ben = [(w, m) for w, oz in O.diger_gorunusler(v) if len(m := O.benzerlik(z, oz)) >= 2]
        rows.append(_row("Görünüş çeşitliliği (önceki videolarla)", v.gorunus_etiketi, "öteki videolarla en fazla 1 ortak nokta (seri hariç)",
                         WARN if ben else OK, "; ".join(f"{w}: {', '.join(m)}" for w, m in ben)))
    gd = guvenli_denetimi(v)
    if gd:
        rows.append(_row("Yazı güvenli alanda (statik denetim)", f"{sum(d_ == OK for d_, _ in gd)}/{len(gd)} temiz", "yazı platform arayüzünün altında kalmaz (formatlar.json → guvenli)",
                         WARN if any(d_ == WARN for d_, _ in gd) else OK, "; ".join(m for _, m in gd)))
    if v.niyetli:  # niyetli altyazı (pipeline/niyet.py): ölçüm tazeliği, okunurluk, sayfa, güvenli alan, kontrast; yalnız seçili filmde
        import niyet
        rows += [_row(*r) for r in niyet.denetim(v)]
        kod = niyet.kod_kullaniyor(v)
        rows.append(_row("Niyetli altyazı sahnede", "çiziliyor" if kod else "kodda yok", "Remotion <NiyetliAltyazi>, HyperFrames niyetliAltyazi(…)",
                         OK if kod else FAIL, "" if kod else "script.json → altyazi niyetli ama sahne kodu çizmiyor (statik denetim)"))
    bz = benzerlik.satir(v)  # temsilî kareler ↔ katalog önizlemeleri ve öteki filmler (deneme ve arşiv hariç)
    if bz:
        rows.append(_row("Benzerlik (katalog kartları ve önceki filmler)", bz[0], f"≥ {benzerlik.ESIK:g} çok benziyor (seri, marka kiti, filmin kendi kartı beklenen)", bz[1], bz[2]))
    if (yy := benzerlik.yol_yontemi(v)) and (oy := benzerlik.onceki_yontem(v)):
        rows.append(_row("Yöntem tekrarı (önceki yollu filmle)", yy, "art arda iki filmde aynı yöntem yok (referans/yontemler.md)",
                         WARN if oy[1] == yy else OK, f"önceki: {oy[0]} · {oy[1]}"))
    bt = v.bitis
    rows.append(_row("Son rötuş (görünüş + script.json → bitis)",
                     ("bulanıklık " + str(bt.get("bulaniklik", 0)) + " örnek · vinyet " + str(bt.get("vinyet", 0)) + " · ışık " + str(bt.get("isik", 0))
                      + " · gren " + str(bt.get("gren", 0))) if bt else "kapalı", "yeni videolarda açık (zanaat.md §5)", OK if bt else "—"))

    # --- ses
    mix = v.pub / "mix.wav"
    if mix.exists():
        L = O.loudness(mix)
        rows.append(_row("Miks ses yüksekliği", f"{L['I']:.1f} LUFS · tepe {L['TP']:.1f} dBTP",
                         f"{_rng(P['lufs'])} LUFS · ≤ {P['tp']:g} dBTP",
                         OK if P["lufs"][0] <= L["I"] <= P["lufs"][1] and L["TP"] <= P["tp"] else FAIL))
        q0 = O.rms_db(O.audio_mono(mix, 16000), 16000, 0.0, 0.15)  # sesi açık izleyen ilk karede bir şey duymalı
        sessiz = v.script.get("sessiz_acilis")
        rows.append(_row("İlk karede ses (ilk 0,15 sn)", f"{q0:.0f} dBFS" + (" · bilinçli sessiz açılış" if sessiz and q0 <= -45 else ""), "> −45 dBFS",
                         OK if q0 > -45 or sessiz else WARN, f"gerekçe: {sessiz}" if sessiz and q0 <= -45 else
                         ("" if q0 > -45 else "ilk karede ses yok: açılışa bir ses koy ya da bilinçli sessizse script.json → sessiz_acilis: \"gerekçe\"")))
        pre = P.get("sessizlik_once")
        h = next((i for i, s in enumerate(S) if s["step"] == pre), None) if pre else None
        if h:
            a, b = S[h - 1]["end"], S[h]["start"]
            sr = 16000
            x = O.audio_mono(mix, sr)
            q = O.rms_db(x, sr, a + 0.15, b - 0.05)
            speech = O.rms_db(x, sr, S[0]["start"], S[-1]["end"])
            rows.append(_row(f"{pre} öncesi bilinçli sessizlik", f"{b - a:.2f} sn · {q:.0f} dBFS (genel {speech:.0f})",
                             "≥ 0,4 sn ve genelden ≥ 20 dB sessiz", OK if b - a >= 0.4 and speech - q >= 20 else FAIL,
                             f"{O.tc(a)}–{O.tc(b)}"))
    else:
        rows.append(_row("Miks", "mix.wav yok", "./st ses", FAIL))

    # --- teslim dosyaları
    if teslim:
        for fmt, mp4 in renders.items():
            if not (mp4 and mp4.exists()):
                rows.append(_row(f"[{fmt}] Teslim dosyası", "yok", "", FAIL))
                continue
            F = O.FORMATLAR[fmt]
            p = O.probe(mp4)
            vs = next(s for s in p["streams"] if s["codec_type"] == "video")
            aud = [s for s in p["streams"] if s["codec_type"] == "audio"]
            fr = vs["r_frame_rate"].split("/")
            fps = float(fr[0]) / float(fr[1])
            dur = float(p["format"]["duration"])
            okv = vs["width"] == F["w"] and vs["height"] == F["h"] and abs(fps - v.fps) < 0.01 and vs["codec_name"] == "h264" and aud
            rows.append(_row(f"[{fmt}] Teslim dosyası", f"{vs['width']}×{vs['height']} · {fps:.0f} fps · {vs['codec_name']} · "
                             f"{aud[0]['codec_name'] if aud else 'SES YOK'} · {dur:.2f} sn",
                             f"{F['w']}×{F['h']} · {v.fps} · h264 · ses",
                             OK if okv else FAIL))
            L2 = O.loudness(mp4)
            rows.append(_row(f"[{fmt}] Teslim ses yüksekliği", f"{L2['I']:.1f} LUFS · tepe {L2['TP']:.1f} dBTP",
                             f"{_rng(P['lufs'])} · ≤ {P['tp']:g}",
                             OK if P["lufs"][0] <= L2["I"] <= P["lufs"][1] and L2["TP"] <= P["tp"] else FAIL))

    # --- ilk kare: akışta ilk görülen kare boş olmamalı (studyo_tanitim inceleme v1, kusur 1)
    if frames_dir and (frames_dir / "f00000.png").exists():
        g = np.asarray(Image.open(frames_dir / "f00000.png").convert("L").resize((180, 320)), dtype=np.float32)
        ink = float((np.abs(g - np.median(g)) > 40).mean() * 100)
        rows.append(_row("İlk kare boş değil", f"%{ink:.1f} piksel zeminden farklı", "≥ %1 (kancanın görüntüsü 0. karede)",
                         OK if ink >= 1.0 else FAIL, f"{frames_dir.name}/f00000.png"))

    # --- döngü
    if P.get("dongu") and frames_dir:
        fs = sorted(frames_dir.glob("f*.png"))
        if len(fs) >= 2:
            a = np.asarray(Image.open(fs[0]).convert("L").resize((90, 160)), dtype=np.float32)
            b = np.asarray(Image.open(fs[-1]).convert("L").resize((90, 160)), dtype=np.float32)
            sim = 1 - np.abs(a - b).mean() / 255
            rows.append(_row("Döngü (ilk kare ↔ son kare benzerliği)", f"%{sim * 100:.0f}", "≥ %85 ya da final kancaya sözle bağlanır",
                             OK if sim >= 0.85 else WARN, f"{fs[0].name} ↔ {fs[-1].name}"))

    # --- öğreticilik sayımları (sezgisel; yalnız profil isterse)
    if v.anlatim and P.get("isim_max") is not None:
        names, nums = set(), set()
        for s in S:
            for i, w in enumerate(s["words"]):
                t = O.norm_word(w["text"])
                if any(ch.isdigit() for ch in t):
                    nums.add(t)
                elif t[:1].isupper() and (i > 0 or re.search(r"['’]", t)):
                    names.add(re.split(r"['’]", t)[0])
        rows.append(_row("Özel isim / rakam sayısı (sezgisel)",
                         f"isim {len(names)}: {', '.join(sorted(names))} · rakam {len(nums)}: {', '.join(sorted(nums))}",
                         f"yabancı isim ≤ {P['isim_max']} · rakam ≤ {P['sayi_max']}", EYE, "Herkesin bildiği isimler sayılmaz; insan karar verir"))

    # --- doğruluk ve varlıklar
    if P.get("kaynak_zorunlu"):
        kd = O.kaynak_durumu(v)
        if kd:
            ok = kd["ok"] == kd["toplam"] and kd["toplam"] > 0
            rows.append(_row("Kaynak doğrulama (kaynaklar.md)", f"✅ {kd['ok']} · ⚠️ {kd['warn']} · ❌ {kd['bad']} / {kd['toplam']} iddia",
                             "her iddia ≥ 2 kaynak", OK if ok else FAIL))
        else:
            rows.append(_row("Kaynak doğrulama", "kaynaklar.md yok", "her iddia ≥ 2 kaynak", FAIL))
    vd = O.varlik_durumu(v)
    if P.get("varlik_zorunlu") or vd["liste"]:
        sorun = vd["eksik"] + vd["onaysiz"] + vd["listesiz"]
        rows.append(_row("Varlıklar (varliklar.md)",
                         f"{vd['liste']} listeli · eksik {len(vd['eksik'])} · onaysız {len(vd['onaysiz'])} · listede yok {len(vd['listesiz'])}",
                         "kodun kullandığı her dosya listede, mevcut ve ✅", OK if not sorun else FAIL, ", ".join(sorun)))
    rows += uretim_satirlari(v, teslim)
    rows += goruntu_satirlari(v, renders)
    rows += takip_satirlari(v)
    import veri  # canlı veri (veri.json'u olan film): görüntünün yaşı, dondurma, lisans, atıf, ekrandaki rakamlar (yazı tanıma)
    rows += veri.olcum_satirlari(v, renders, teslim, frames_dir.parent if frames_dir else None)
    import kisisel  # kişisel etki filmi (veri_sablonu.json'u olan şablon film): sözleşme, sahne kodu, kararlar, örnek satırın yazıları ekranda
    rows += kisisel.olcum_satirlari(v, renders, teslim, frames_dir.parent if frames_dir else None)

    niyet_goz = ["Niyetli altyazı: bağıran kelime kalın ve büyük, fısıltı ince; tiz kelime dar; renk doğru konuşmacıda"] if v.niyetli else []
    veri_goz = ["Canlı veri: ekranda verinin ne olduğu (tahmin / ölçüm), yeri ve zamanı doğru söyleniyor; rakam abartılmadan sunuluyor"] if veri.var_mi(v) else []
    takip_goz = ["Kamera takibi: nesne çekimin ışığına uyuyor (gölge yönü ve yumuşaklığı, renk, keskinlik, hareket bulanıklığı); yürürken kaymıyor"] if (v.dir / "takip" / "takip.json").exists() else []
    kisi_goz = ["Kişisel film: en uzun ad ve en uzun değerlerle kart taşmıyor, ad okunuyor; TEST verisiyle çizilen film gerçek sanılmıyor"] if kisisel.var_mi(v) else []
    for ad in GOZ_GENEL + P.get("goz", []) + niyet_goz + veri_goz + kisi_goz + takip_goz:
        rows.append(_row(ad, "—", "—", EYE))
    return rows, motions


def uretim_satirlari(v: O.Video, teslim: bool = False) -> list[dict]:
    """Magnific üretim deposu (videos/<id>/uretim/uretim.json) olan filmde: kredi, dondurma, ekranda etiket, yayın beyanı, kare hızı.
    Deposu olmayan (eski) filmlere satır eklenmez."""
    import uretim
    if not uretim.var_mi(v):
        return []
    U = uretim.yukle(v)
    if not U["varliklar"] and not U["harcama"]:
        return []
    rows = []
    s, h = uretim.sinir(v.id), uretim.harcanan(U)
    modeller = sorted({x["model"] for x in U["varliklar"] if x.get("model")})
    rows.append(_row("Yapay zekâ üretimleri (Magnific)", f"{len(U['varliklar'])} varlık · {', '.join(modeller) or '—'} · harcanan {h} / sınır {s} kredi",
                     "harcanan ≤ filmin kredi sınırı (sınırı kullanıcı değiştirir)", OK if h <= s else FAIL))
    dg = uretim.dogrula(v)
    bozuk = [m for _, ok, m in dg if not ok]
    rows.append(_row("Üretim varlıkları dondurulmuş (sha256)", f"{len(dg) - len(bozuk)}/{len(dg)} dosya aynı", "hepsi kayıttakiyle aynı (kural 8)",
                     OK if not bozuk else FAIL, ", ".join(bozuk)))
    E = uretim.etiket_durumu(v)
    if not E["gerekli"]:
        rows.append(_row("Yapay zekâ etiketi (ekranda)", "etiket gerektiren varlık sahnede değil", "gerçekçi insan canlandırması kullanılan her vuruşta etiket", OK))
    else:
        durum = FAIL if E["eksik"] else (WARN if not E["bilesen"] else OK)
        rows.append(_row("Yapay zekâ etiketi (ekranda)", f"{len(E['gerekli']) - len(E['eksik'])}/{len(E['gerekli'])} varlığın etiket kaydı · "
                         f"{len(E['etiketler'])} etiket (script.json → etiketler)", "gerçekçi insan canlandırması kullanılan her vuruşta etiket",
                         durum, (("etiket kaydı yok: " + ", ".join(E["eksik"])) if E["eksik"] else
                                 ("" if E["bilesen"] else "kodda <Etiket> ya da .etiket bulunamadı (statik denetim)"))))
    if any(x.get("yz") for x in U["varliklar"]):
        bd = uretim.beyan_dolu(v)
        rows.append(_row("Yapay zekâ beyanı (yayin.md)", {True: "dolu", False: "boş", None: "yayin.md yok"}[bd],
                         "yapay zekâ varlığı varsa yayın paketinde beyan (./st yayin doldurur)",
                         OK if bd else (FAIL if bd is False or teslim else WARN), "" if bd else "./st yayin " + v.id))
    kul = uretim.kullanim(v)
    sek = [f"{x['ad']} {x['olcu']['fps']:g}" for x in U["varliklar"] if (x.get("olcu") or {}).get("fps") and abs(x["olcu"]["fps"] - v.fps) > 0.01
           and any(not y.startswith("vuruş") for y in kul.get(x["ad"], []))]
    if any((x.get("olcu") or {}).get("fps") for x in U["varliklar"]):
        rows.append(_row("Üretim klipleri kare hızı", ", ".join(sek) + f" kare/sn ↔ film {v.fps}" if sek else f"film hızında ({v.fps} kare/sn)",
                         "klip filmle aynı hızda (--uyum) ya da film klibin hızında (zanaat §9)", WARN if sek else OK))
    return rows


def goruntu_satirlari(v: O.Video, renders: dict | None = None) -> list[dict]:
    """Gerçek görüntü (videos/<id>/goruntu/goruntu.json) ve anahtar kare sandviçi olan filmde: dondurma, kullanıcının seçtiği kişi çözümüne uyum
    (rıza kapı değildir: kullanıcı kararı, 2026-10-27), gerçek kişinin yapay zekâya girmemesi, kadraj (özne güvenli alanda), sandviç geçişinde
    sıçrama. Kaydı olmayan (eski) filmlere satır eklenmez."""
    import goruntu
    rows = []
    if goruntu.var_mi(v) and goruntu.yukle(v)["varliklar"]:
        G = goruntu.yukle(v)
        dg = goruntu.dogrula(v)
        bozuk = [m for _, ok, m in dg if not ok]
        rows.append(_row("Gerçek görüntü dondurulmuş (sha256)", f"{len(dg) - len(bozuk)}/{len(dg)} dosya aynı", "ara format, derinlik, maske, kadraj "
                         "kayıttakiyle aynı (kural 8)", OK if not bozuk else FAIL, ", ".join(bozuk)))
        E = goruntu.etik_durumu(v)
        cozumlu = [x["ad"] for x in G["varliklar"] if x.get("kisi") and x.get("cozum") and x["ad"] in E["kullanilan"]]
        if cozumlu:  # yalnız kullanıcı bir çözüm seçtiyse (yüzleri gizle, stilize, kullanma): kod ona uyuyor mu
            rows.append(_row("Kişi: seçtiğin çözüm uygulanıyor", ", ".join(cozumlu), "kullanıcının seçtiği çözüm (gizle, stilize, kullanma) kodda uygulanıyor",
                             FAIL if E["riza"] else OK, "; ".join(E["riza"])))
        rows.append(_row("Gerçek kişi yapay zekâya girmedi", "temiz" if not E["yz"] else ", ".join(E["yz"]),
                         "gerçek görüntüdeki kişi Magnific'e kaynak kare olarak verilmez (kural 2; yüz yeniden yaratılmaz)", FAIL if E["yz"] else OK))
        stil = goruntu.stil_kullanimi(v)
        for x in G["varliklar"]:  # kadraj yalnız kadraj yolunu okuyan bileşenlerde (Goruntu, Stilize); Sandvic ve Derinlik25D kendi yerleşimini kurar
            if x["tur"] != "video" or x["ad"] not in E["kullanilan"] or not any(b.split(":")[0] in ("Goruntu", "Stilize") for b in stil.get(x["ad"], ())):
                continue
            for fmt in v.formatlar:
                F = O.FORMATLAR[fmt]
                k = (x.get("kadraj") or {}).get(fmt)
                ayni = abs(x["olcu"]["en"] / x["olcu"]["boy"] - F["w"] / F["h"]) / (F["w"] / F["h"]) < 0.02
                if k:
                    rows.append(_row(f"[{fmt}] Kadraj: {x['ad']}", f"özne güvenli alanda %{k['guvenli_oran'] * 100:.0f} kare · {k['kirpma']}",
                                     "≥ %95 (merkezden kırpma yok)", OK if k["guvenli_oran"] >= 0.95 else WARN))
                elif not ayni:
                    rows.append(_row(f"[{fmt}] Kadraj: {x['ad']}", "kadraj yolu yok", "her formatta özne takibi (./st goruntu kadraj)", FAIL,
                                     f"./st goruntu kadraj {v.id} {x['ad']} --format {fmt}"))
    # anahtar kare sandviçi: geçişlerde tek karelik sıçrama yok
    for sj in sorted((v.dir / "uretim" / "_anahtar").glob("*/sandvic.json")) if (v.dir / "uretim" / "_anahtar").exists() else []:
        S = O.jload(sj)
        mp4 = (renders or {}).get(S["format"])
        if not (mp4 and Path(mp4).exists()):
            continue
        F = O.FORMATLAR[S["format"]]
        fr = O.gray_frames(Path(mp4), *O.motion_size(F["w"], F["h"]), fps=v.fps)
        mo = O.motion_of(fr)
        a, b = S["bas_kare"], S["son_kare"]
        fl = [i for i in O.flash_frames(fr, mo) if a - 3 <= i <= b + 3]
        komsu = float(np.median(mo[max(1, a - 30):b + 30])) + 0.05
        ek = f"giriş f{a} fark {mo[a]:.1f} · çıkış f{b} fark {mo[b]:.1f} (çevre ortancası {komsu:.1f})" if b < len(mo) else ""
        rows.append(_row(f"[{S['format']}] Sandviç geçişi: {S['ad']}", f"{len(fl)} tek karelik sıçrama · {ek}", "0 sıçrama (motor → klip → motor)",
                         FAIL if fl else OK, ", ".join(f"f{i}" for i in fl)))
    return rows


def to_md(v: O.Video, rows, label: str) -> str:
    n_fail = sum(r["durum"] == FAIL for r in rows)
    n_warn = sum(r["durum"] == WARN for r in rows)
    out = [f"# Ölçüm — {v.id} · {label}", "",
           f"**Özet:** {n_fail} ❌ · {n_warn} ⚠️ · {sum(r['durum'] == OK for r in rows)} ✅ · {sum(r['durum'] == EYE for r in rows)} 👁 (göz kontrolü)", "",
           "| Ölçüt | Değer | Çıta | Durum | Kanıt |", "|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['ad']} | {r['deger']} | {r['cita']} | {r['durum']} | {r['kanit'].replace('|', '/')} |")
    return "\n".join(out) + "\n"


def write(v: O.Video, rows, out_dir: Path, label: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "olcum.md").write_text(to_md(v, rows, label))
    (out_dir / "olcum.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    return out_dir / "olcum.md"


def takip_satirlari(v: O.Video) -> list[dict]:
    """Kamera takibi (videos/<id>/takip/takip.json) olan filmde: dondurma, çözüm hatası, zemin, format, kayma (gölgenin oturduğu yerde zemin
    izleri). Ekrana etiket ya da uyarı yazısı yalnız kullanıcı isterse konur: ölçüm onu aramaz. Takibi olmayan filme satır eklenmez."""
    import takip
    S = takip.denetle(v)
    if not S:
        return []
    rows = []
    for ok, ad, deger in S:
        rows.append(_row("Kamera takibi: " + ad[0].lower() + ad[1:] if not ad.startswith("[") else "Kamera takibi " + ad, deger,
                         "dondurulmuş, ortalama hata ≤ 1 px, zemin ve ölçek bulundu, çekim formatla aynı oranda", OK if ok else FAIL))
    K = takip.kayma(v)
    if K and K.get("kare"):
        rows.append(_row("Kamera takibi: nesne kaymıyor (gölgenin altındaki zemin izleri)", f"{K['kare']} karede ortalama {K['ortalama_px']:.2f} px · en kötü "
                         f"kare {K['en_kotu_kare']}: {K['en_kotu_px']:.2f} px", "≤ 1,5 px (bilgisayarın zemini çekimin zemininde)",
                         OK if K["en_kotu_px"] <= 1.5 else (WARN if K["en_kotu_px"] <= 3 else FAIL), f"küme {K['kume']}"))
    elif K is not None:
        rows.append(_row("Kamera takibi: nesne kaymıyor (gölgenin altındaki zemin izleri)", "gölge katmanında gölge yok ya da altında zemin izi yok", "—", EYE))
    return rows
