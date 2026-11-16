"""HyperFrames motoru: script.json → "motor": "hyperframes" olan videolar.

Sahne hf/<id>/index.html'de HTML + CSS + SVG + GSAP ile yazılır; kareleri ve videoyu HyperFrames CLI (HeyGen, Apache-2.0) çizer.
Stüdyo bu klasöre dört şey taşır (`esitle`), ikisi index.html'in içinde işaretli bloklar olarak (elle değiştirilmez):
  <style id="st-gorunus">   görünüşün renk ve yazı değişkenleri (--arka, --vurgu, --yazi-baslik …) + yerel @font-face
  <script id="st-veri">     window.ST = {format, w, h, fps, sure, isaretler, vuruslar, kelimeler, beats, guvenli, altyazi}
  assets/ses/miks.wav       ./st ses'in miksi (yoksa sessiz yer tutucu) · assets/lib/gsap/ (yerel GSAP) · varliklar/ (public/<id>/varliklar)
3B katman (Three.js; sahne assets/lib/three/ ya da assets/lib/uc/ yüklüyorsa): yerel three kopyası + kullandığı eklentiler (assets/lib/three/),
stüdyonun 3B kiti (assets/lib/uc/uc.js, src/lib/uc/hf.ts'ten esbuild ile) ve <script type="importmap" id="st-uc"> bloğu. CDN'den yükleme yok.
Kök öğenin ve <audio id="st-ses">'in süresi stüdyonun zaman çizelgesinden gelir.
Her format ayrı bir kompozisyondur: _fmt/<format>/index.html (boyut, data-format ve ST değişir; öteki dosyalar bağlantıdır).
Sahne kodu formatı html[data-format="9x16"] seçicisiyle ya da ST.format ile okur; merkezden kırpılmaz.
Kontak tabakası, ölçüm, kör eleştiri ve yayın paketi motordan bağımsızdır: MP4'ü ve kareleri okurlar.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request
import wave
from pathlib import Path

import ortak as O

SURUM = "0.9.17"  # sabit: aynı kaynak her zaman aynı kareyi versin. Yükseltmeden önce HF videolarında kare karşılaştırması.
# Yeni filmlerin varsayılanı; her film kendi sürümünü script.json → hyperframes'te tutar (eski filmler 0.8.181'de kalır, kareleri değişmez).
# 0.8.181 → 0.9.17 (2026-11-06, öğrenimler #81): görünüşte yazı tipi tanımlı filmler SwiftShader'da bayt bayt aynı; tanımsız `sans-serif`
# başka yedek yazı tipine düşüyor (uc_*_hf), bir filmde başlığın kenar yumuşatması oynuyor. Bir filmi yükseltmek = kareleri değişebilir.
HF = O.ROOT / "hf"
SABLON = O.ROOT / "sablon" / "hf"
FONT_ON = O.ROOT / "out" / "_hf_fontlar"
GSAP_DIST = O.ROOT / "node_modules" / "gsap" / "dist"
THREE_DIZIN = O.ROOT / "node_modules" / "three"
UC_KAYNAK = O.ROOT / "src" / "lib" / "uc"
NIYET_KAYNAK = O.ROOT / "src" / "lib" / "niyet"
UC_EKLENTI = ["environments/RoomEnvironment.js", "loaders/GLTFLoader.js", "loaders/DRACOLoader.js", "loaders/KTX2Loader.js",
              "utils/SkeletonUtils.js", "libs/meshopt_decoder.module.js"]  # uc.js'in kendi kullandığı eklentiler (GLB yükleyici dahil)
GSAP = ["gsap", "MotionPathPlugin", "CustomEase", "CustomBounce", "CustomWiggle", "DrawSVGPlugin", "MorphSVGPlugin",
        "SplitText", "TextPlugin", "Physics2DPlugin", "EasePack"]
CIKAR = {"index.html", "_fmt", "_gorunus", "renders", "snapshots", "node_modules"}  # varyanta bağlanmayanlar (noktalılar da)
CEVRE = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1"}


def klasor(v) -> Path:
    return HF / v.id


def surum(v) -> str:
    return (v.script.get("hyperframes") if v else None) or SURUM


def cli(v, args, cwd=None, capture=False, check=True):
    """HyperFrames CLI'yi sabit sürümle çalıştırır (npx önbelleği)."""
    print("→ hyperframes " + " ".join(str(a) for a in args)[:200])
    r = subprocess.run(["npx", "--yes", f"hyperframes@{surum(v)}", *map(str, args)], cwd=cwd or (klasor(v) if v else O.ROOT), env=CEVRE,
                       text=True, capture_output=capture)
    if check and r.returncode:
        raise SystemExit(f"hyperframes {args[0]} başarısız (çıkış {r.returncode})" + (f":\n{(r.stdout + r.stderr)[-3000:]}" if capture else ""))
    return r


# ---------------------------------------------------------------- görünüş → CSS
def secenek(v, anahtar=None) -> dict | None:
    G = v.gorunus_json() or {}
    S = G.get("secenekler") or {}
    k = anahtar or G.get("secim") or (sorted(S)[0] if S else None)
    return S.get(k) if k else None


def _indir(url: str, hedef: Path):
    FONT_ON.mkdir(parents=True, exist_ok=True)
    on = FONT_ON / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".woff2")
    if not on.exists():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            on.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            raise SystemExit(f"Yazı tipi indirilemedi ({url}): {e}. İnternet bağlantısı gerekiyor (bir kez; sonra önbellekte).")
    if not hedef.exists() or hedef.stat().st_size != on.stat().st_size:
        shutil.copy2(on, hedef)


def _fontlar_css(s: dict, fontdir: Path) -> list[str]:
    """Görünüşün yazı tiplerini yerel dosyaya indirir (latin + latin-ext: Türkçe), @font-face kurallarını döndürür."""
    istek = {}
    for rol, y in (s.get("yazi") or {}).items():
        if not y:
            continue
        a = istek.setdefault(y["aile"], [set(), False])
        a[0] |= {int(y["agirlik"])} | ({600} if rol == "govde" else set())  # Remotion tarafıyla aynı: gövdeye kalın da yüklenir
        a[1] = a[1] or bool(y.get("italik"))
    if not istek:
        return []
    r = subprocess.run(["node", "pipeline/fontlar.mjs", "--bilgi", ",".join(istek)], cwd=O.ROOT, capture_output=True, text=True, check=True)
    bilgi = json.loads(r.stdout)
    eksik = sorted(set(istek) - set(bilgi))
    if eksik:
        raise SystemExit(f"Yazı tipi listede yok: {', '.join(eksik)} (src/lib/fontlar.ts; başka bir yazı tipi için index.html'e kendi @font-face'ini yaz)")
    fontdir.mkdir(parents=True, exist_ok=True)
    kurallar = []
    for aile, (ws, ital) in istek.items():
        B = bilgi[aile]
        for stil in ["normal"] + (["italic"] if ital and "italic" in B["fonts"] else []):
            var = sorted(int(w) for w in B["fonts"][stil])
            for w in sorted(ws):
                wg = w if w in var else min(var, key=lambda x: abs(x - w))
                for alt in ("latin", "latin-ext"):
                    url = B["fonts"][stil][str(wg)].get(alt)
                    if not url:
                        continue
                    ad = f"{re.sub(r'[^a-z0-9]+', '-', aile.lower())}-{stil}-{wg}-{alt}.woff2"
                    _indir(url, fontdir / ad)
                    kurallar.append(f'@font-face {{ font-family: "{aile}"; font-style: {stil}; font-weight: {w}; font-display: block; '
                                    f'src: url("assets/fonts/{ad}") format("woff2"); unicode-range: {B["unicodeRanges"][alt]}; }}')
    return kurallar


def _marka(v) -> dict | None:
    m = v.script.get("marka") if v else None
    p = O.ROOT / "markalar" / str(m) / "marka.json" if m else None
    return O.jload(p) if p and p.exists() else None


def gorunus_css(v, s: dict | None, fontdir: Path) -> str:
    """Görünüş seçeneğini CSS değişkenlerine çevirir. Sahne kodu renkleri ve yazıyı yalnız buradan okur: üç seçenek gerçekten farklı çıkar."""
    L = ["/* ./st üretir (videos/<id>/gorunus.json → seçili görünüş). Elle değiştirme: görünüşü gorunus.json'da değiştir. */"]
    deg = []
    if s:
        R = dict(s.get("renk") or {})
        R.setdefault("ikincil", R.get("vurgu"))
        R.setdefault("soluk", R.get("murekkep"))
        R.setdefault("kagit", R.get("arka"))
        deg += [f"--{k}: {c};" for k, c in R.items() if c]
        L += _fontlar_css(s, fontdir)
        for rol in ("baslik", "govde", "aksan"):
            y = (s.get("yazi") or {}).get(rol) or s["yazi"]["baslik"]
            deg += [f'--yazi-{rol}: "{y["aile"]}", sans-serif;', f"--yazi-{rol}-agirlik: {y['agirlik']};", f"--yazi-{rol}-aralik: {y.get('aralik', 0)}em;"]
            L.append(f".yazi-{rol} {{ font-family: var(--yazi-{rol}); font-weight: var(--yazi-{rol}-agirlik); letter-spacing: var(--yazi-{rol}-aralik);"
                     + (" font-style: italic;" if y.get("italik") else "") + (" text-transform: uppercase;" if y.get("buyukHarf") else "") + " }")
    else:  # görünüş henüz yazılmadı: yer tutucu (lint ve önizleme çalışsın)
        deg += ["--arka: #f4efe6;", "--murekkep: #1d1b18;", "--vurgu: #d9480f;", "--ikincil: #2b6cb0;", "--soluk: #6b645c;", "--kagit: #f4efe6;"]
        for rol in ("baslik", "govde", "aksan"):
            deg += [f"--yazi-{rol}: sans-serif;", f"--yazi-{rol}-agirlik: {700 if rol == 'baslik' else 400};", f"--yazi-{rol}-aralik: 0em;"]
    M = _marka(v)
    if M:
        deg += [f"--marka-{k}: {c};" for k, c in (M.get("renk") or {}).items()]
    L.insert(1, ":root { " + " ".join(deg) + " }")
    if v is not None:
        import uretim
        if uretim.var_mi(v):  # yalnız Magnific üretim deposu olan filmde (eski filmlerin index.html'i değişmez)
            L += etiket_css()
        if v.niyetli:  # yalnız niyetli altyazılı filmde (öteki filmlerin index.html'i değişmez)
            L += niyet_css()
        import veri
        if veri.var_mi(v):  # yalnız canlı veri filminde: ekranda atıf plakası
            L += veri_css()
        import kisisel
        if kisisel.var_mi(v):  # yalnız kişisel film şablonunda: verinin yazı tipi (Roboto Flex) ve TEST plakası
            L += kisi_css(v)
    return "\n" + "\n".join(L) + "\n"


def etiket_css() -> list[str]:
    """Yapay zekâ etiketi (<div class="etiket">Canlandırmadır</div>; .alt ve .sag konumları): 64 px, koyu zemin üstünde beyaz,
    formatın güvenli alanında, durağan. Remotion karşılığı src/lib/Etiket.tsx."""
    L = [".etiket { position: absolute; z-index: 50; padding: 14px 26px; border-radius: 18px; background: rgba(12,12,14,0.78); color: #fff;"
         " font-family: var(--yazi-govde), sans-serif; font-weight: 600; font-size: 64px; line-height: 1.12; letter-spacing: 0; }"]
    for f, F in O.FORMATLAR.items():
        g, w, h = F["guvenli"], F["w"], F["h"]
        s = f'html[data-format="{f}"] .etiket'
        L += [f"{s} {{ top: {g['ust'] * h + 24:.0f}px; left: {g['sol'] * w + 24:.0f}px; max-width: {(1 - g['sol'] - g['sag']) * w - 48:.0f}px; }}",
              f"{s}.alt {{ top: auto; bottom: {g['alt'] * h + 24:.0f}px; }}", f"{s}.sag {{ left: auto; right: {g['sag'] * w + 24:.0f}px; }}"]
    return L


def veri_css() -> list[str]:
    """Canlı verinin ekrandaki atfı (<div class="veri-atif"></div>; metni ST.veri.atif_kisa · tur_ad · zaman_yerel; .ust konumu): 40 px,
    koyu zemin üstünde beyaz (≥ 4,5:1), formatın güvenli alanında, durağan. Remotion karşılığı src/lib/veri → <VeriAtif>."""
    L = [".veri-atif { position: absolute; z-index: 50; padding: 10px 22px; border-radius: 14px; background: rgba(12,12,14,0.80); color: #fff;"
         " font-family: var(--yazi-govde), sans-serif; font-weight: 500; font-size: 40px; line-height: 1.2; letter-spacing: 0; }"]
    for f, F in O.FORMATLAR.items():
        g, w, h = F["guvenli"], F["w"], F["h"]
        s = f'html[data-format="{f}"] .veri-atif'
        L += [f"{s} {{ bottom: {g['alt'] * h + 24:.0f}px; left: {g['sol'] * w + 24:.0f}px; max-width: {(1 - g['sol'] - g['sag']) * w - 48:.0f}px; }}",
              f"{s}.ust {{ bottom: auto; top: {g['ust'] * h + 24:.0f}px; }}"]
    return L


def kisi_css(v) -> list[str]:
    """Kişisel etki filmi: Roboto Flex (sığdırılmış yazı; assets/lib/kisisel/kisi.js) ve TEST plakası (<div class="kisi-test">; 40 px, koyu kırmızı
    üstünde beyaz, formatın güvenli alanında, durağan). Remotion karşılığı src/lib/kisisel → <KisiTest>. Niyetli filmde yazı tipi zaten var."""
    L = [] if v.niyetli else niyet_css()
    L.append(".kisi-test { position: absolute; z-index: 60; padding: 8px 20px; border-radius: 12px; background: #8E1B1B; color: #fff;"
             " font-family: var(--yazi-govde), sans-serif; font-weight: 600; font-size: 40px; line-height: 1.2; letter-spacing: 0; }")
    for f, F in O.FORMATLAR.items():
        g, w, h = F["guvenli"], F["w"], F["h"]
        L.append(f'html[data-format="{f}"] .kisi-test {{ top: {g["ust"] * h + 24:.0f}px; left: {g["sol"] * w + 24:.0f}px; }}')
    return L


def niyet_css() -> list[str]:
    """Niyetli altyazının değişken yazı tipi (Roboto Flex, OFL; public/fontlar/roboto-flex → assets/fonts/): ağırlık ve genişlik ekseni
    font-variation-settings ile kelime kelime (assets/lib/niyet/niyet.js). Remotion karşılığı src/lib/fontlar.ts → DEGISKEN."""
    import niyet
    return [f'@font-face {{ font-family: "{niyet.AILE}"; font-style: normal; font-weight: 100 1000; font-stretch: 25% 151%; font-display: block; '
            f'src: url("assets/fonts/{ad}") format("woff2"); unicode-range: {aralik}; }}' for ad, aralik in NIYET_FONTLAR.items()]


NIYET_FONTLAR = {  # src/lib/fontlar.ts → DEGISKEN["Roboto Flex"].dosyalar ile aynı
    "roboto-flex-latin.woff2": "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, "
                               "U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
    "roboto-flex-latin-ext.woff2": "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, "
                                   "U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF",
}


def niyet_veri(N: dict, fmt: str) -> dict:
    """ST.niyet: niyetli altyazının çekirdeğe giden verisi (src/lib/niyet/cekirdek.ts → NiyetVeri), yalnız bu formatın yerleşimiyle."""
    alan = ("i", "metin", "bas", "son", "k", "s", "p", "wght", "wdth", "boyut", "kay")
    return {"surum": N["surum"], "yazi": {"aile": N["yazi"]["aile"], "opsz": N["yazi"]["opsz"]}, "zemin": N["zemin"], "alfa": N["alfa"],
            "pad": N["pad"], "satir_ara": N["satir_ara"],
            "konusmacilar": {k: {"ad": d["ad"], "renk": d["renk"], "renk_once": d["renk_once"]} for k, d in N["konusmacilar"].items()},
            "kelimeler": [{a: k[a] for a in alan} for k in N["kelimeler"]], "formatlar": {fmt: N["formatlar"][fmt]}}


# ---------------------------------------------------------------- veri (format, süre, işaretler)
def st_veri(v, fmt: str, anahtar: str | None = None, kisi: dict | None = None) -> dict:
    F = O.FORMATLAR[fmt]
    tl = v.timeline or {}
    r3 = lambda x: round(float(x), 3)
    vur = [{"id": s["id"], "step": s["step"], "start": r3(s["start"]), "end": r3(s["end"])} for s in tl.get("sentences", [])]
    kel = [{"t": w["text"], "s": r3(w["start"]), "e": r3(w["end"]), "v": s["id"]} for s in tl.get("sentences", []) for w in s.get("words", [])]
    out = {"format": fmt, "w": F["w"], "h": F["h"], "fps": v.fps, "sure": r3(v.duration or 10), "isaretler": {k: r3(t) for k, t in v.cues.items()},
           "vuruslar": vur, "kelimeler": kel, "beats": [r3(b) for b in tl.get("beats", [])], "guvenli": F["guvenli"], "altyazi": F["altyazi"]}
    if v.niyetli and tl.get("niyet") and fmt in tl["niyet"]["formatlar"]:  # niyetli altyazı (assets/lib/niyet/niyet.js); öteki filmlerde alan yok
        out["niyet"] = niyet_veri(tl["niyet"], fmt)
    if v.yollu:  # planda üç yol: kanca karesi seçeneğin harfine göre dallanır (ST.secenek, html[data-secenek]); yolsuz filmlerde alan yok
        out["secenek"] = v.secenek_harfi(anahtar)
    import veri
    c = veri.cizim(v) if veri.var_mi(v) else None
    if c:  # canlı veri: seçili anlık görüntünün çizim verisi (ST.veri); öteki filmlerde alan yok
        out["veri"] = c
    import kisisel
    if kisi or kisisel.var_mi(v):  # kişisel film: şablonun TEST örneği ya da ./st toplu'nun satırı (ST.kisi); öteki filmlerde alan yok
        out["kisi"] = kisi or kisisel.ornek_kisi(v)
    if v.script.get("_sahne"):  # karma filmin sahnesi (6b, pipeline/plaka.py): yerel pencere; öteki filmlerde alan yok
        out["sahne"] = v.script["_sahne"]
    return out


def _secenek_niteligi(v, html: str, anahtar: str | None = None) -> str:
    """Yol modu: <html data-secenek="a"> (CSS ile dallanma: html[data-secenek="b"] .yol-a {display:none}). Yolsuz filmde dokunulmaz."""
    return _etiketi_degistir(html, r"<html[^>]*>", data_secenek=v.secenek_harfi(anahtar)) if v.yollu and v.secenek_harfi(anahtar) else html


def _blok(html: str, etiket: str, kimlik: str, icerik: str) -> str:
    pat = re.compile(rf'(<{etiket}(?:\s[^>]*?)?\sid="{kimlik}"[^>]*>)(.*?)(</{etiket}>)', re.S)  # id ilk nitelik olmayabilir (importmap)
    if not pat.search(html):
        raise SystemExit(f'index.html\'de <{etiket} id="{kimlik}"> bloğu yok (şablon: sablon/hf/index.html)')
    return pat.sub(lambda m: m.group(1) + icerik + m.group(3), html, count=1)


def _nitelik(etiket: str, ad: str, deger) -> str:
    if re.search(rf'\s{ad}="[^"]*"', etiket):
        return re.sub(rf'(\s{ad}=")[^"]*(")', lambda m: f"{m.group(1)}{deger}{m.group(2)}", etiket, count=1)
    return etiket[:-1].rstrip("/").rstrip() + f' {ad}="{deger}">'


def _etiketi_degistir(html: str, pat: str, **nitelikler) -> str:
    m = re.search(pat, html)
    if not m:
        return html
    t = m.group(0)
    for ad, d in nitelikler.items():
        t = _nitelik(t, ad.replace("_", "-"), d)
    return html[:m.start()] + t + html[m.end():]


KOK = r'<div[^>]*\sdata-composition-id="[^"]+"[^>]*>'


def _boyut(html: str, fmt: str) -> str:
    F = O.FORMATLAR[fmt]
    html = re.sub(r'(<meta name="viewport" content=")width=\d+,\s*height=\d+', rf'\g<1>width={F["w"]}, height={F["h"]}', html, count=1)
    html = _etiketi_degistir(html, r"<html[^>]*>", data_format=fmt)
    # html/body'ye piksel boyut yazılmışsa (içe aktarılan projeler) o da formata uyar; yoksa kompozisyon eski boyutta kırpılır
    html = re.sub(r"(html,\s*body\s*\{[^}]*?(?<![-\w])width:\s*)\d+px", rf"\g<1>{F['w']}px", html, count=1)
    html = re.sub(r"(html,\s*body\s*\{[^}]*?(?<![-\w])height:\s*)\d+px", rf"\g<1>{F['h']}px", html, count=1)
    return _etiketi_degistir(html, KOK, data_width=F["w"], data_height=F["h"])


def _sure(html: str, sure: float) -> str:
    s = f"{sure:.3f}".rstrip("0").rstrip(".")
    html = _etiketi_degistir(html, KOK, data_duration=s)
    return _etiketi_degistir(html, r'<audio[^>]*\sid="st-ses"[^>]*>', data_duration=s)


def _yaz(p: Path, metin: str):
    if not p.exists() or p.read_text() != metin:
        p.write_text(metin)


# ---------------------------------------------------------------- eşitleme
def _ses(v, d: Path):
    hedef = d / "assets" / "ses" / "miks.wav"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    kaynak = v.pub / "mix.wav"
    if kaynak.exists():
        if not hedef.exists() or hedef.stat().st_size != kaynak.stat().st_size or hedef.stat().st_mtime < kaynak.stat().st_mtime:
            shutil.copy2(kaynak, hedef)
    elif not hedef.exists():  # ./st ses'ten önce: sessiz yer tutucu (lint eksik dosya demesin)
        with wave.open(str(hedef), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(b"\0\0\0\0" * int(48000 * max(1.0, v.duration or 10)))


def _kutuphane(d: Path):
    lib = d / "assets" / "lib" / "gsap"
    lib.mkdir(parents=True, exist_ok=True)
    for ad in GSAP:
        k = GSAP_DIST / f"{ad}.min.js"
        if k.exists() and not (lib / k.name).exists():
            shutil.copy2(k, lib / k.name)


def _kopya(k: Path, h: Path):
    if not h.exists() or h.stat().st_size != k.stat().st_size:
        h.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(k, h)


def uc_kullanir(d: Path) -> bool:
    """Sahne 3B katmanı (yerel three ya da stüdyo kiti) yüklüyor mu."""
    return any("assets/lib/three/" in f.read_text() or "assets/lib/uc/" in f.read_text()
               for f in [d / "index.html", *(d / "compositions").rglob("*.html")] if f.exists())


IMPORTMAP = {"imports": {"three": "./assets/lib/three/three.module.js", "three/addons/": "./assets/lib/three/addons/",
                         "three/examples/jsm/": "./assets/lib/three/addons/"}}


def _uc_kutuphane(d: Path):
    """3B katman: three (sabit sürüm, node_modules'tan), sahnenin içe aktardığı eklentiler (ve onların göreli bağımlılıkları), uc.js."""
    lib = d / "assets" / "lib"
    for ad in ("three.module.js", "three.core.js"):
        _kopya(THREE_DIZIN / "build" / ad, lib / "three" / ad)
    metin = "".join(f.read_text() for f in d.rglob("*") if f.suffix in (".html", ".js", ".mjs") and f.is_file() and "assets/lib" not in str(f)
                    and not any(x.startswith(".") or x in ("_fmt", "_gorunus", "renders", "snapshots", "node_modules") for x in f.relative_to(d).parts))
    bekleyen = set(UC_EKLENTI) | set(re.findall(r"""three/(?:addons|examples/jsm)/([\w/.-]+\.js)""", metin))
    gorulen = set()
    while bekleyen:
        rel = bekleyen.pop()
        if rel in gorulen:
            continue
        k = THREE_DIZIN / "examples" / "jsm" / rel
        if not k.exists():
            raise SystemExit(f"three eklentisi yok: three/addons/{rel} (node_modules/three/examples/jsm/)")
        gorulen.add(rel)
        _kopya(k, lib / "three" / "addons" / rel)
        bekleyen |= {os.path.normpath(str(Path(rel).parent / g)) for g in re.findall(r"""from\s+['"](\.{1,2}/[^'"]+)['"]""", k.read_text())}
    import model3b
    model3b.cozucu_hazirla(lib / "uc" / "cozucu")  # GLB çözücüleri (Draco, KTX2/Basis): uc.js COZUCU yolları
    cikti = lib / "uc" / "uc.js"
    kaynak = list(UC_KAYNAK.glob("*.ts"))
    if not cikti.exists() or cikti.stat().st_mtime < max(f.stat().st_mtime for f in kaynak):
        cikti.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(O.ROOT / "node_modules" / ".bin" / "esbuild"), str(UC_KAYNAK / "hf.ts"), "--bundle", "--format=esm", "--target=es2020",
                        "--external:three", "--external:three/*", "--legal-comments=none", f"--outfile={cikti}", "--log-level=warning"],
                       cwd=O.ROOT, check=True)
    html = (d / "index.html").read_text()
    if 'id="st-uc"' not in html:
        raise SystemExit(f'{d.name}/index.html 3B katman kullanıyor ama <script type="importmap" id="st-uc"></script> bloğu yok '
                         "(<head>'de, ilk modül betiğinden önce; şablon: hf/CLAUDE.md → 3B katman)")


def niyet_kullanir(d: Path) -> bool:
    """Sahne niyetli altyazıyı (assets/lib/niyet/niyet.js) yüklüyor mu."""
    return any("assets/lib/niyet/" in f.read_text() for f in [d / "index.html", *(d / "compositions").rglob("*.html")] if f.exists())


def _niyet_kutuphane(d: Path):
    """Niyetli altyazı: çekirdek (src/lib/niyet/hf.ts → assets/lib/niyet/niyet.js, esbuild) ve değişken yazı tipi (assets/fonts/)."""
    for ad in NIYET_FONTLAR:
        _kopya(O.ROOT / "public" / "fontlar" / "roboto-flex" / ad, d / "assets" / "fonts" / ad)
    cikti = d / "assets" / "lib" / "niyet" / "niyet.js"
    kaynak = list(NIYET_KAYNAK.glob("*.ts"))
    if not cikti.exists() or cikti.stat().st_mtime < max(f.stat().st_mtime for f in kaynak):
        cikti.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(O.ROOT / "node_modules" / ".bin" / "esbuild"), str(NIYET_KAYNAK / "hf.ts"), "--bundle", "--format=esm", "--target=es2020",
                        "--legal-comments=none", f"--outfile={cikti}", "--log-level=warning"], cwd=O.ROOT, check=True)


def _kisi_kutuphane(d: Path):
    """Kişisel film: Roboto Flex (assets/fonts/) ve yardımcı (src/lib/kisisel/hf.js → assets/lib/kisisel/kisi.js, derlemesiz kopya)."""
    for ad in NIYET_FONTLAR:
        _kopya(O.ROOT / "public" / "fontlar" / "roboto-flex" / ad, d / "assets" / "fonts" / ad)
    _kopya(O.ROOT / "src" / "lib" / "kisisel" / "hf.js", d / "assets" / "lib" / "kisisel" / "kisi.js")


def kisi_varyanti(v, fmt: str, kisi: dict, hedef: Path) -> Path:
    """./st toplu'nun bir satırı için kompozisyon: formatın varyantı, ST.kisi bu satırla. Kişi verisi taşır: hedef videos/<id>/toplu/ altında
    (iş bitince silinir); öteki dosyalar hf/<id>/'ye bağlantıdır."""
    d = klasor(v)
    hedef.mkdir(parents=True, exist_ok=True)
    html = _secenek_niteligi(v, _boyut((d / "index.html").read_text(), fmt))
    html = _blok(html, "script", "st-veri", "\nwindow.ST = " + json.dumps(st_veri(v, fmt, kisi=kisi), ensure_ascii=False) + ";\n")
    _yaz(hedef / "index.html", html)
    for p in d.iterdir():
        if p.name in CIKAR or p.name.startswith("."):
            continue
        b = hedef / p.name
        if not b.is_symlink() and not b.exists():
            b.symlink_to(os.path.relpath(p, hedef))
    return hedef


YAPIM_KAYNAK = O.ROOT / "src" / "lib" / "yapim"


def kilavuz_paketi() -> str:
    """Kılavuz kipinin HyperFrames betiği (src/lib/yapim/hf.ts → esbuild, IIFE); out/_yapim/_lib/'de önbellekli."""
    cikti = O.ROOT / "out" / "_yapim" / "_lib" / "kilavuz-hf.js"
    kaynak = list(YAPIM_KAYNAK.glob("*.ts"))
    if not cikti.exists() or cikti.stat().st_mtime < max(f.stat().st_mtime for f in kaynak):
        cikti.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(O.ROOT / "node_modules" / ".bin" / "esbuild"), str(YAPIM_KAYNAK / "hf.ts"), "--bundle", "--format=iife", "--target=es2020",
                        "--legal-comments=none", f"--outfile={cikti}", "--log-level=warning"], cwd=O.ROOT, check=True)
    return cikti.read_text()


def kilavuz_varyanti(v, fmt: str, kip: str, hedef: Path) -> Path:
    """Yapım filmi (./st yapim): formatın kompozisyonu + kılavuz betiği (yerleşim kutuları, güvenli alan; kip "veri": kutuların pikselleri).
    hedef out/_yapim/<id>/ altında; hf/<id>/'ye yazılmaz, öteki dosyalar oraya bağlantıdır."""
    esitle(v)
    d = klasor(v)
    hedef.mkdir(parents=True, exist_ok=True)
    html = (varyant(v, fmt) / "index.html").read_text()
    betik = f'<script id="st-yapim">\nwindow.ST_YAPIM = {json.dumps({"kip": kip})};\n{kilavuz_paketi()}\n</script>\n'
    if "</body>" not in html:
        raise SystemExit(f"{v.id}: index.html'de </body> yok (kılavuz betiği eklenemedi)")
    i = html.rindex("</body>")
    _yaz(hedef / "index.html", html[:i] + betik + html[i:])
    for p in d.iterdir():
        if p.name in CIKAR or p.name.startswith("."):
            continue
        b = hedef / p.name
        if not b.is_symlink() and not b.exists():
            b.symlink_to(os.path.relpath(p, hedef))
    return hedef


def _varliklar(v, d: Path):
    k = v.pub / "varliklar"
    k.mkdir(parents=True, exist_ok=True)
    b = d / "varliklar"
    if not b.exists() and not b.is_symlink():
        b.symlink_to(os.path.relpath(k, d))
    g = v.pub / "goruntu"  # gerçek görüntünün türevleri (./st goruntu: bilgi.json, derinlik, maske); yalnız varsa (öteki filmler değişmez)
    if g.exists() and not (d / "goruntu").exists() and not (d / "goruntu").is_symlink():
        (d / "goruntu").symlink_to(os.path.relpath(g, d))


def esitle(v):
    """Stüdyodan HyperFrames projesine: görünüş, veri, süre, ses, kitaplık, varlıklar; sonra her formatın varyantı."""
    d = klasor(v)
    if not (d / "index.html").exists():
        raise SystemExit(f"{v.id}: hf/{v.id}/index.html yok (yeni HyperFrames videosu: ./st yeni {v.id} \"Başlık\" --motor hyperframes)")
    _kutuphane(d)
    uc = uc_kullanir(d)
    if uc:
        _uc_kutuphane(d)
    if niyet_kullanir(d):
        _niyet_kutuphane(d)
    import kisisel
    if kisisel.var_mi(v):  # yalnız kişisel film şablonunda (öteki filmlerin klasörü değişmez)
        _kisi_kutuphane(d)
    _ses(v, d)
    _varliklar(v, d)
    html = (d / "index.html").read_text()
    if uc:
        html = _blok(html, "script", "st-uc", "\n" + json.dumps(IMPORTMAP, indent=1) + "\n")
    html = _blok(html, "style", "st-gorunus", gorunus_css(v, secenek(v), d / "assets" / "fonts"))
    html = _blok(html, "script", "st-veri", "\nwindow.ST = " + json.dumps(st_veri(v, v.formatlar[0]), ensure_ascii=False) + ";\n")
    html = _secenek_niteligi(v, _sure(_boyut(html, v.formatlar[0]), v.duration or 10))
    _yaz(d / "index.html", html)
    for fmt in v.formatlar:
        varyant(v, fmt)


def varyant(v, fmt: str, anahtar: str | None = None) -> Path:
    """Bir formatın (ve istenirse başka bir görünüş seçeneğinin) kompozisyonu: index.html'in boyutlu kopyası + öteki dosyalara bağlantı."""
    d = klasor(v)
    hedef = d / "_gorunus" / f"{anahtar}-{fmt}" if anahtar else d / "_fmt" / fmt
    hedef.mkdir(parents=True, exist_ok=True)
    html = _secenek_niteligi(v, _boyut((d / "index.html").read_text(), fmt), anahtar)
    html = _blok(html, "script", "st-veri", "\nwindow.ST = " + json.dumps(st_veri(v, fmt, anahtar), ensure_ascii=False) + ";\n")
    if anahtar:
        html = _blok(html, "style", "st-gorunus", gorunus_css(v, secenek(v, anahtar), d / "assets" / "fonts"))
    _yaz(hedef / "index.html", html)
    for p in d.iterdir():
        if p.name in CIKAR or p.name.startswith("."):
            continue
        b = hedef / p.name
        if not b.is_symlink() and not b.exists():
            b.symlink_to(os.path.relpath(p, hedef))
    return hedef


def kaynaklar(v) -> list[Path]:
    """Kaba kurgunun tazeliği için: yazılan dosyalar (üretilen varyantlar ve önbellekler hariç)."""
    d = klasor(v)
    out = []
    for p in d.rglob("*"):
        rel = p.relative_to(d).parts
        if p.is_file() and not p.is_symlink() and rel[0] not in CIKAR - {"index.html"} and not any(x.startswith(".") for x in rel):
            out.append(p)
    return out


# ---------------------------------------------------------------- kareler ve render
def kareler(v, frames, out_dir: Path, fmt: str, order="asc", anahtar=None, yazilim=False, kok: Path | None = None) -> dict[int, Path]:
    """Kareleri HyperFrames snapshot ile çizer → out_dir/fNNNNN.png (Remotion yolundaki adlarla aynı).
    yazilim=True: tarayıcı GPU'su yerine SwiftShader (HyperFrames'in deterministik kipi). Donanım GPU'su kenar yumuşatmasını
    önceki karelere göre birkaç pikselde farklı yuvarlıyor (1–40/255); ./st deterministik bu yüzden yazılım kipini kullanır."""
    kok = kok or varyant(v, fmt, anahtar)
    fr = sorted({int(f) for f in frames}, reverse=(order == "desc"))
    tmp = out_dir / "_hf"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    zaman = ",".join(f"{f / v.fps:.6f}".rstrip("0").rstrip(".") if f else "0" for f in fr)
    cli(v, ["snapshot", kok, "--at", zaman, "--no-end", "--keep", "-o", tmp, "--describe", "false"] + (["--no-browser-gpu"] if yazilim else []), capture=True)
    files = {}
    for p in tmp.glob("at-*s.png"):
        f = round(float(p.name[3:-5]) * v.fps)
        dst = out_dir / f"f{f:05d}.png"
        shutil.move(str(p), dst)
        files[f] = dst
    shutil.rmtree(tmp, ignore_errors=True)
    eksik = [f for f in fr if f not in files]
    if eksik:
        raise SystemExit(f"HyperFrames şu kareleri çizmedi: {eksik[:10]}")
    print(f"   [{fmt}] {len(files)} kare (HyperFrames)")
    return files


def video(v, fmt: str, hedef: Path, final=False, kok: Path | None = None):
    """Görüntüyü HyperFrames çizer; ses stüdyonundur. HyperFrames'in kendi karıştırıcısı seviyeyi değiştiriyor (−14 → −15,8 LUFS,
    ihh_sofra teslim v1), o yüzden ./st ses'in miksi görüntüye olduğu gibi bindirilir."""
    kok = kok or varyant(v, fmt)
    ham = hedef.with_name(hedef.stem + "_hf.mp4")
    # Teslim SwiftShader ile (deterministik kip): donanım GPU'suyla macOS'ta açılan hızlı yakalama, ölçeği değişen katmanı
    # bir kare düşük çözünürlüklü rasterle çizebiliyor (ihh_kis_yardimi_icin teslim v1, f378 bulanık: "tek karelik sıçrama" ❌)
    cli(v, ["render", kok, "-o", ham, "--fps", v.fps, "--quality", "delivery" if final else "draft", "--quiet"] + (["--no-browser-gpu"] if final else []))
    mix = v.pub / "mix.wav"
    if not mix.exists():
        ham.replace(hedef)
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ham), "-i", str(mix), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k" if final else "160k", "-shortest", str(hedef)], check=True)
    ham.unlink()


def denetle(v) -> int:
    """hyperframes check (lint + çalışma + yerleşim + hareket + kontrast), her format için."""
    esitle(v)
    kotu = 0
    for fmt in v.formatlar:
        print(f"\n[{fmt}]")
        r = cli(v, ["check", varyant(v, fmt)], check=False)
        kotu += r.returncode != 0
    print("✅ HyperFrames denetimi temiz" if not kotu else f"❌ {kotu} formatta bulgu var (yukarıda)")
    return kotu


def yeni(vid: str, baslik: str, fmt: str, dil: str = "tr", niyetli: bool = False):
    """hf/<id>/ iskeleti: şablondan index.html, hyperframes.json, meta.json. niyetli: altyazı katmanı ve niyet.js modülü eklenir."""
    d = HF / vid
    d.mkdir(parents=True, exist_ok=False)
    F = O.FORMATLAR[fmt]
    for src in SABLON.iterdir():
        t = src.read_text()
        for k, val in {"{{ID}}": vid, "{{BASLIK}}": baslik, "{{W}}": str(F["w"]), "{{H}}": str(F["h"]), "{{FORMAT}}": fmt, "{{DIL}}": dil}.items():
            t = t.replace(k, val)
        if niyetli and src.name == "index.html":
            t = t.replace('      <audio id="st-ses"', '      <div id="altyazi"></div>\n      <audio id="st-ses"', 1).replace(
                "  </body>", '    <script type="module">\n      // Niyetli altyazı: şiddet → ağırlık + boyut, perde → genişlik, konuşmacı → renk (ST.niyet; ./st niyet)\n'
                '      import { niyetliAltyazi } from "./assets/lib/niyet/niyet.js";\n      niyetliAltyazi(document.getElementById("altyazi"));\n'
                "    </script>\n  </body>", 1)
        (d / src.name).write_text(t)
    (d / "assets").mkdir(exist_ok=True)


def katalog_demo(dizin: Path, secenek_: dict, mp4: Path, kareler_: dict[int, Path], fps=30, sure=3.0):
    """Katalog animasyon tipinin HyperFrames örneği (katalog/animasyon/hf/<ad>/index.html): görünüş ve veri bloklarını doldurur,
    3 sn'lik döngüyü ve göz kontrolü karelerini çizer."""
    _kutuphane(dizin)
    if uc_kullanir(dizin):
        _uc_kutuphane(dizin)
        _yaz(dizin / "index.html", _blok((dizin / "index.html").read_text(), "script", "st-uc", "\n" + json.dumps(IMPORTMAP, indent=1) + "\n"))
    html = (dizin / "index.html").read_text()
    html = _blok(html, "style", "st-gorunus", gorunus_css(None, secenek_, dizin / "assets" / "fonts"))
    F = O.FORMATLAR["1x1"]
    veri = {"format": "1x1", "w": F["w"], "h": F["h"], "fps": fps, "sure": sure, "isaretler": {}, "vuruslar": [], "kelimeler": [], "beats": [],
            "guvenli": F["guvenli"], "altyazi": F["altyazi"]}
    _yaz(dizin / "index.html", _blok(html, "script", "st-veri", "\nwindow.ST = " + json.dumps(veri, ensure_ascii=False) + ";\n"))
    cli(None, ["render", dizin, "-o", mp4, "--fps", fps, "--quality", "looks", "--quiet"], cwd=dizin)
    tmp = mp4.parent / "_hf_kare"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    zaman = ",".join(f"{f / fps:.6f}".rstrip("0").rstrip(".") for f in kareler_)
    cli(None, ["snapshot", dizin, "--at", zaman, "--no-end", "--keep", "-o", tmp, "--describe", "false"], cwd=dizin, capture=True)
    for p in tmp.glob("at-*s.png"):
        f = round(float(p.name[3:-5]) * fps)
        if f in kareler_:
            shutil.move(str(p), kareler_[f])
    shutil.rmtree(tmp, ignore_errors=True)
