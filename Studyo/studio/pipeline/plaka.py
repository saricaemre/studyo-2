"""Karma film (oturum 6b): sahne başına motor. Remotion birleştirir; HyperFrames ve Blender sahneleri plaka (PNG dizisi) olarak gelir.

Sözleşme: script.json → "motor": "remotion" + "sahneler":
  [{"ad": "kahraman", "motor": "hyperframes", "bas": "<işaret>", "son": "<işaret>"},
   {"ad": "kumbara", "motor": "blender", "cizer": "eevee", "bas": "<işaret>", "son": "<işaret>", "saydam": false}]
Pencereler işarete bağlı (kural 9); listede olmayan zaman Remotion'da çizilir. Sahnenin kodu:
  hf/<id>/sahneler/<ad>/index.html (sıradan bir HyperFrames projesi; pipeline/hf.py aynen)
  blender/<id>/sahneler/<ad>/sahne.py (kitle; pipeline/blender.py'nin çalıştırıcısı aynen)
Yerel zaman: sahnenin ST'si kendi çizim aralığının başından sayar (0 = ilk plaka). İşaretler, vuruşlar, kelimeler kaydırılır, ST.sure aralığın
uzunluğu; ST.sahne = {ad, bas, son, film_bas, kare0}: sahnenin kendi penceresi (yerel saniye) ve filmdeki başlangıç. Çizim aralığı pencereden
geniş olabilir: sınırdaki gölgelendirici kesiminin (6a, <Kesim>) penceresi kadar (giden sahne N/2 kare uzar, gelen N/2 kare erken başlar).
Plakalar filmin kare hızında, her format için ayrı (merkezden kırpma yok); kare numaraları filmin genel numaralarıdır:
  out/_plaka/<id>/<sahne>/<format>-<kalite>-<parmak izi>/pNNNNN.png  → Remotion'a public/<id>/plaka bağlantısıyla (Blender filmleri gibi).
Parmak izi: motor sürümü + sahne klasörü + stüdyonun verisi (yerel ST, görünüş, marka, varlıklar) + kalite (+ Blender'da kit, EEVEE, saydam).
Sahnenin kodu değişince yalnız o sahnenin plakaları yeniden çizilir. HyperFrames plakaları SwiftShader'la (bayt bayt), kalitesi tek ("tam");
Blender'ınki taslak/tam ve toleranslı (blender.TOLERANS). Saydam sahne yalnız Blender'da (HyperFrames snapshot saydam arka plan vermiyor):
blender/karma/sahne.py sarmalayıcısı film_transparent + RGBA PNG.
Üst katman Remotion'da (src/<id>/Video.tsx: <Plaka>, <Kesim>, altyazı, logo, Bitis, ses); kontak, ölçüm, eleştiri, kapılar son MP4'e bakar.
"""
import fcntl
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

import ortak as O

MOTORLAR = ("hyperframes", "blender", "manim")
ONBELLEK = O.ROOT / "out" / "_plaka"
KARMA = O.ROOT / "blender" / "karma"     # saydam Blender sahnesinin sarmalayıcısı (yalnız saydam sahnenin parmak izinde)
TUT = 3                                   # (sahne, format, kalite) başına saklanan en yeni küme
AD = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
_ATLA = {"_fmt", "_gorunus", "renders", "snapshots", "node_modules", "__pycache__", ".hyperframes", "media"}


def var_mi(v) -> bool:
    """Karma film: Remotion birleştirici + script.json → sahneler (boş değil). Öteki filmlerde hiçbir şey değişmez."""
    return v.motor == "remotion" and isinstance(v.script.get("sahneler"), list) and bool(v.script["sahneler"])


def kok(v, S: dict) -> Path:
    """Sahnenin kod klasörü."""
    return O.ROOT / {"hyperframes": "hf", "blender": "blender", "manim": "manim"}.get(S.get("motor"), "?") / v.id / "sahneler" / str(S.get("ad"))


def _kn(sn: float, fps: int) -> int:
    import gecis
    return gecis.kare_no(sn, fps)


def pencereler(v) -> dict[str, tuple]:
    """{sahne: (motor, bas_f, son_f, saydam)}: yalnız işaretlerden (kesimlere bakmaz; pipeline/gecis.py doğrudan kesimi bununla bulur)."""
    if not var_mi(v):
        return {}
    out = {}
    for S in v.script.get("sahneler") or []:
        if isinstance(S, dict) and S.get("motor") in MOTORLAR and all(isinstance(S.get(a), str) and S[a] in v.cues for a in ("bas", "son")):
            out[str(S.get("ad"))] = (S["motor"], _kn(v.cues[S["bas"]], v.fps), _kn(v.cues[S["son"]], v.fps), bool(S.get("saydam")))
    return out


def sahneler(v) -> list[dict]:
    """script.json → sahneler, kareleriyle: bas_f, son_f (pencere), r0, r1 (çizim aralığı: komşu kesim pencereleri dahil). hata: lint söyler."""
    import gecis
    K = gecis.tanim_json(v) if gecis.var_mi(v) else {}
    out = []
    for i, S in enumerate(v.script.get("sahneler") or []):
        S = dict(S) if isinstance(S, dict) else {"ad": f"#{i + 1}", "_bozuk": True}
        S.setdefault("ad", f"#{i + 1}")
        S["kok"] = kok(v, S)
        hata = None
        if S.get("_bozuk"):
            hata = "nesne değil"
        elif S.get("motor") not in MOTORLAR:
            hata = f"motor {S.get('motor')!r} ({' | '.join(MOTORLAR)})"
        else:
            for a in ("bas", "son"):
                x = S.get(a)
                if not isinstance(x, str) or x not in v.cues:
                    hata = f"{a} işareti yok: {x!r} (cues.json; pencereler işarete bağlıdır)" + (f" · {v.cue_error}" if v.cue_error else "")
        if not hata:
            S["bas_f"], S["son_f"] = _kn(v.cues[S["bas"]], v.fps), _kn(v.cues[S["son"]], v.fps)
            r0, r1 = S["bas_f"], S["son_f"]
            for k in K.values():   # sınırdaki kesimin penceresi: giden sahne N/2 kare uzar, gelen N/2 kare erken başlar
                if k["bas"] <= S["bas_f"] < k["son"] or k["kesim"] == S["bas_f"]:
                    r0 = min(r0, k["bas"])
                if k["bas"] < S["son_f"] <= k["son"] or k["kesim"] == S["son_f"]:
                    r1 = max(r1, k["son"])
            S["r0"], S["r1"] = max(0, r0), min(v.nframes or r1, r1)
        S["hata"] = hata
        out.append(S)
    return out


def sorunlar(v) -> list[tuple[str, str]]:
    """./st lint: ad tekil, motor tanımlı ve kurulu, işaretler var, pencere filmin içinde, aynı katmanda çakışma yok, sahnenin kodu var."""
    if not var_mi(v):
        if v.script.get("sahneler") and v.motor != "remotion":
            return [("❌", f"script.json → sahneler yalnız Remotion birleştiricili filmde (motor {v.motor}; karma film: motor remotion)")]
        return []
    out, adlar, opak = [], set(), []
    for S in sahneler(v):
        b = f"sahne {S['ad']}"
        if not AD.match(str(S["ad"])):
            out.append(("❌", f"{b}: ad küçük harf, rakam ve alt çizgi (2–31 karakter)"))
        if S["ad"] in adlar:
            out.append(("❌", f"{b}: ad tekil olmalı"))
        adlar.add(S["ad"])
        if S["hata"]:
            out.append(("❌", f"{b}: {S['hata']}"))
            continue
        if S["son_f"] <= S["bas_f"]:
            out.append(("❌", f"{b}: son işareti bastan önce ya da aynı (f{S['bas_f']} → f{S['son_f']})"))
            continue
        if S["bas_f"] < 0 or (v.nframes and S["son_f"] > v.nframes):
            out.append(("❌", f"{b}: pencere film dışında (f{S['bas_f']}–f{S['son_f'] - 1}, film {v.nframes} kare)"))
        m = S["motor"]
        if m == "hyperframes" and S.get("saydam"):
            out.append(("❌", f"{b}: saydam sahne yalnız Blender'da (HyperFrames snapshot saydam arka plan vermiyor; sahneyi opak çiz)"))
        if m == "blender" and S.get("cizer") not in (None, "cycles", "eevee"):
            out.append(("❌", f"{b}: cizer cycles | eevee (verilen {S.get('cizer')})"))
        dosya = {"hyperframes": "index.html", "blender": "sahne.py", "manim": "sahne.py"}[m]
        if not (S["kok"] / dosya).exists():
            out.append(("❌", f"{b}: kod yok: {(S['kok'] / dosya).relative_to(O.ROOT)} (./st plaka {v.id} yeni {S['ad']} --motor {m})"))
        kurulu = motor_kurulu(m)
        if kurulu is not True:
            out.append(("❌", f"{b}: {kurulu}"))
        if not S.get("saydam"):
            for a, (x, y) in opak:
                if S["bas_f"] < y and x < S["son_f"]:
                    out.append(("❌", f"{b}: {a} sahnesiyle aynı katmanda çakışıyor (f{S['bas_f']}–f{S['son_f'] - 1} ↔ f{x}–f{y - 1}); üst üste çizilecekse biri saydam olmalı"))
            opak.append((S["ad"], (S["bas_f"], S["son_f"])))
    return out


def motor_kurulu(m: str):
    """True ya da kurulum satırı (Blender: sabit sürüm; Manim: isteğe bağlı, .venv'de; HyperFrames: npx önbelleği, ilk çizimde iner)."""
    if m == "blender":
        import blender
        if not Path(blender.BLENDER).exists():
            return f"Blender yok ({blender.BLENDER}): brew install --cask blender (sürüm {blender.SURUM})"
        return True
    if m == "manim":
        import manim_kopru
        return manim_kopru.kurulu()
    return True


# ---------------------------------------------------------------- yerel zaman
def yerel(v, S: dict):
    """Sahnenin kendi Video'su: kimlik <id>/sahneler/<ad> (motorun kod klasörü), yerel zaman (0 = çizim aralığının başı), filmin görünüşü, verisi,
    markası ve varlıkları. pipeline/hf.py ve pipeline/blender.py bunu sıradan bir film gibi çizer."""
    import copy
    t0 = S["r0"] / v.fps
    n = S["r1"] - S["r0"]
    tl = copy.deepcopy(v.timeline or {"sentences": []})
    for s in tl.get("sentences", []):
        s["start"], s["end"] = s["start"] - t0, s["end"] - t0
        for w in s.get("words", []):
            w["start"], w["end"] = w["start"] - t0, w["end"] - t0
    if tl.get("beats"):
        tl["beats"] = [b - t0 for b in tl["beats"]]
    tl["duration"] = (n - 0.25) / v.fps   # ceil(süre · fps) = n (tam bölünmede yuvarlama bir kare eklemesin)
    sc = {k: x for k, x in v.script.items() if k not in ("altyazi", "hyperframes", "blender", "comp", "kod", "sahneler")}
    sc.update({"motor": S["motor"], "formatlar": v.formatlar,
               "_sahne": {"ad": S["ad"], "bas": round((S["bas_f"] - S["r0"]) / v.fps, 4), "son": round((S["son_f"] - S["r0"]) / v.fps, 4),
                          "film_bas": round(t0, 4), "kare0": S["r0"]}})
    if S["motor"] == "hyperframes":
        import hf
        sc["hyperframes"] = S.get("surum") or hf.SURUM
    elif S["motor"] == "blender":
        import blender
        sc["blender"] = {"surum": S.get("surum") or blender.SURUM, **({"cizer": S["cizer"]} if S.get("cizer") not in (None, "cycles") else {}),
                         **({"tohum": S["tohum"]} if "tohum" in S else {})}
    # Kimlik: HyperFrames'te sahnenin proje klasörü (hf.klasor = hf/<kimlik>); Blender'da filmin kimliği (kit.varlik public/<id>/varliklar'ı
    # ST.id'den bulur; sahnenin yolu çalıştırıcıya açıkça verilir)
    P = O.Video(v.id if S["motor"] == "blender" else f"{v.id}/sahneler/{S['ad']}", v.dir, v.pub, sc, tl, v.cuefile)
    P.cues = {k: t - t0 for k, t in v.cues.items()}
    return P


def _dosyalar(d: Path, haric=()) -> list[Path]:
    out = []
    if not d.exists():
        return out
    for dp, dn, fn in os.walk(d, followlinks=False):
        rel = Path(dp).relative_to(d)
        dn[:] = sorted(x for x in dn if x not in _ATLA and not x.startswith(".") and str(rel / x) not in haric)
        for f in sorted(fn):
            p = Path(dp) / f
            if f.startswith(".") or p.is_symlink() or p.suffix in (".pyc", ".blend1") or str(p.relative_to(d)) in haric:
                continue
            out.append(p)
    return out


def _ozet(h, p: Path):
    st = p.stat()
    h.update(str(p.relative_to(O.ROOT)).encode() + b"\0")
    h.update(f"{st.st_size}:{st.st_mtime_ns}".encode() if st.st_size > 8 * 2 ** 20 else p.read_bytes())
    h.update(b"\0")


def _varliklar(v) -> list[Path]:
    vd = v.pub / "varliklar"
    return sorted(x for x in vd.rglob("*") if x.is_file() and x.name != ".DS_Store") if vd.exists() else []


# ---------------------------------------------------------------- HyperFrames sürücüsü
class _HF:
    kaliteler = ("tam",)   # SwiftShader, tam çözünürlük; taslak/tam aynı plaka

    @staticmethod
    def kaynaklar(v, S) -> list[Path]:
        return _dosyalar(S["kok"], haric=("assets/ses", "assets/ses/miks.wav"))

    @staticmethod
    def kume(v, S, fmt, kalite) -> tuple[str, object]:
        import hf
        P = yerel(v, S)
        hf.esitle(P)
        h = hashlib.sha256()
        h.update(f"hf-sahne 1\nhyperframes {hf.surum(P)}\n{fmt}\n".encode())
        for p in _HF.kaynaklar(v, S) + _varliklar(v):
            _ozet(h, p)
        h.update(json.dumps(hf.st_veri(P, fmt), sort_keys=True, ensure_ascii=False).encode())
        return f"{fmt}-tam-{h.hexdigest()[:12]}", P

    @staticmethod
    def ciz(v, S, fmt, kalite, kume, P, kareler: list[int], hedef: Path):
        import hf
        with tempfile.TemporaryDirectory(prefix="st_karma_hf_") as tmp:
            files = hf.kareler(P, [f - S["r0"] for f in kareler], Path(tmp), fmt, "asc", None, yazilim=True)
            for f, p in files.items():
                shutil.move(str(p), hedef / f"p{f + S['r0']:05d}.png")

    @staticmethod
    def yeniden(v, S, fmt, kume, P, kareler, hedef_eski: Path) -> list[str]:
        import hf
        with tempfile.TemporaryDirectory(prefix="st_karma_hf_det_") as tmp:
            files = hf.kareler(P, [f - S["r0"] for f in kareler], Path(tmp), fmt, "desc", None, yazilim=True)
            fark = [f + S["r0"] for f, p in files.items() if p.read_bytes() != (hedef_eski / f"p{f + S['r0']:05d}.png").read_bytes()]
        return [f"{'✅' if not fark else '❌'} [{fmt}] sahne {S['ad']} (HyperFrames, SwiftShader): {len(kareler) - len(fark)}/{len(kareler)} plaka ayrı "
                f"işlemde ters sırayla bayt bayt aynı" + (f" · farklı: {fark[:6]}" if fark else "")]

    @staticmethod
    def denetle(v, S) -> int:
        import hf
        P = yerel(v, S)
        print(f"\n[sahne {S['ad']} · HyperFrames {hf.surum(P)}]")
        return hf.denetle(P)

    @staticmethod
    def tara(v, S) -> list[str]:
        bad = re.compile(r"Math\.random|Date\.now|new Date\(|performance\.now|setTimeout|setInterval|requestAnimationFrame|"
                         r"transition\s*:|animation\s*:|@keyframes")
        hits = []
        for p in _HF.kaynaklar(v, S):
            if p.suffix in (".html", ".js", ".css") and "assets/lib" not in str(p):
                for i, ln in enumerate(p.read_text().splitlines(), 1):
                    if bad.search(ln):
                        hits.append(f"{p.relative_to(O.ROOT)}:{i}: {ln.strip()[:90]}")
        return hits


# ---------------------------------------------------------------- Blender sürücüsü
class _BL:
    kaliteler = ("taslak", "tam")

    @staticmethod
    def kaynaklar(v, S) -> list[Path]:
        import blender
        P_cizer = S.get("cizer") or "cycles"
        out = _dosyalar(S["kok"])
        for d in (blender.KIT,) + ((blender.EEVEE,) if P_cizer == "eevee" else ()) + ((KARMA,) if S.get("saydam") else ()):
            out += _dosyalar(d)
        return out

    @staticmethod
    def kume(v, S, fmt, kalite) -> tuple[str, object]:
        import blender
        P = yerel(v, S)
        V = blender.veri(P, fmt)
        K = {**blender.kalite(P, kalite), **({"alfa": True} if S.get("saydam") else {})}
        h = hashlib.sha256()
        h.update(f"blender {blender.surum(P)}\nkarma-sahne 1\n".encode())
        if blender.cizer(P) != "cycles":
            h.update(f"cizer {blender.cizer(P)}\n".encode())
        for p in _BL.kaynaklar(v, S) + _varliklar(v):
            _ozet(h, p)
        h.update(json.dumps(V, sort_keys=True, ensure_ascii=False).encode())
        h.update(json.dumps(K, sort_keys=True).encode())
        return f"{fmt}-{kalite}-{h.hexdigest()[:12]}", (P, V, K)

    @staticmethod
    def _cagri(v, S, P):
        """(sahne, ortam): saydam sahnede sarmalayıcı (film_transparent + RGBA), asıl sahne ST_KARMA_SAHNE'de."""
        asil = S["kok"] / "sahne.py"
        if S.get("saydam"):
            return KARMA / "sahne.py", {"ST_KARMA_SAHNE": str(asil)}
        return asil, None

    @staticmethod
    def ciz(v, S, fmt, kalite, kume, PVK, kareler: list[int], hedef: Path):
        import blender
        P, V, K = PVK
        sahne, ortam = _BL._cagri(v, S, P)
        with open(ONBELLEK / ".kilit", "w") as kilit:
            try:
                fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("→ Blender başka bir çizimde; sıra bekleniyor…", flush=True)
                fcntl.flock(kilit, fcntl.LOCK_EX)
            kareler = [f for f in kareler if not (hedef / f"p{f:05d}.png").exists()]
            blender._bellek_uyar()
            t0, yapilan = time.time(), [0]

            def ilerleme(k):
                yapilan[0] += 1
                if yapilan[0] % 10 == 0 or yapilan[0] == len(kareler):
                    print(f"   sahne {S['ad']} {yapilan[0]}/{len(kareler)} · f{k['f'] + S['r0']} {k['sn']:.1f} sn", flush=True)

            with tempfile.TemporaryDirectory(prefix="st_karma_bl_") as tmp:
                for i in range(0, len(kareler), blender.PARCA):
                    parca = kareler[i:i + blender.PARCA]
                    blender._calistir(sahne, V, K, ["--cikti", tmp, "--kareler", ",".join(str(f - S["r0"]) for f in parca)],
                                      f"sahne {S['ad']} ({fmt}, {kalite})", ilerleme, blender.surum(P), blender.cizer(P), ortam)
                    for f in parca:
                        os.replace(Path(tmp) / f"p{f - S['r0']:05d}.png", hedef / f"p{f:05d}.png")
            if kareler:
                sure = time.time() - t0
                print(f"   sahne {S['ad']}: {len(kareler)} plaka {sure:.0f} sn ({sure / len(kareler):.2f} sn/kare, kurulum dahil)", flush=True)

    @staticmethod
    def yeniden(v, S, fmt, kume, PVK, kareler, hedef_eski: Path) -> list[str]:
        import numpy as np
        from PIL import Image
        import blender
        P, V, K = PVK
        sahne, ortam = _BL._cagri(v, S, P)
        T = blender.TOLERANS_EEVEE if blender.cizer(P) == "eevee" else blender.TOLERANS
        satir = []
        with tempfile.TemporaryDirectory(prefix="st_karma_bl_det_") as tmp:
            blender._calistir(sahne, V, K, ["--cikti", tmp, "--kareler", ",".join(str(f - S["r0"]) for f in kareler)], f"yeniden çizim ({S['ad']})",
                              beklenen=blender.surum(P), cizer_=blender.cizer(P), ortam=ortam)
            for f in kareler:
                a = np.asarray(Image.open(hedef_eski / f"p{f:05d}.png").convert("RGBA")).astype(np.int16)
                b = np.asarray(Image.open(Path(tmp) / f"p{f - S['r0']:05d}.png").convert("RGBA")).astype(np.int16)
                fark = np.abs(a - b).max(-1)
                eb, oran = int(fark.max()), float((fark > T["esik"]).mean())
                ok = eb <= T["en_buyuk"] and oran <= T["oran"]
                satir.append(f"{'✅' if ok else '❌'} [{fmt}] sahne {S['ad']} f{f} ({blender.cizer(P)}) ayrı işlemde yeniden çizildi: en büyük fark {eb}/255, "
                             f"farklı piksel (> {T['esik']}/255) %{oran * 100:.4f} (tolerans ≤ {T['en_buyuk']}/255, ≤ %{T['oran'] * 100:g})")
        return satir

    @staticmethod
    def denetle(v, S) -> int:
        import blender
        kotu = 0
        hits = _BL.tara(v, S)
        print(f"\n[sahne {S['ad']} · Blender {blender.SURUM} · {S.get('cizer') or 'cycles'}]")
        print("✅ sahne kodunda gizli saat / tohumsuz rastgelelik / pişirilmemiş fizik yok" if not hits else "❌ sahne kodu:\n  " + "\n  ".join(hits))
        kotu += bool(hits)
        for fmt in v.formatlar:
            _, (P, V, K) = _BL.kume(v, S, fmt, "taslak")
            sahne, ortam = _BL._cagri(v, S, P)
            oz = blender._calistir(sahne, V, K, ["--kuru"], f"kuru kurulum ({S['ad']}, {fmt})", beklenen=blender.surum(P), cizer_=blender.cizer(P),
                                   ortam=ortam)
            k = oz.get("kuru", {})
            print(f"✅ [{fmt}] sahne kuruldu: {k.get('nesne')} nesne · {k.get('isik')} ışık · {k.get('ucgen', 0):,} üçgen · kurulum {k.get('kurulum_sn')} sn · "
                  f"{k.get('motor')}".replace(",", "."))
        return kotu

    @staticmethod
    def tara(v, S) -> list[str]:
        import blender
        hits = []
        for p in _dosyalar(S["kok"]):
            if p.suffix != ".py":
                continue
            metin = p.read_text()
            for i, ln in enumerate(metin.splitlines(), 1):
                kod = ln.split("#", 1)[0]
                for pat, neden in blender.YASAK:
                    if pat.search(kod):
                        hits.append(f"{p.relative_to(O.ROOT)}:{i}: {neden}: {ln.strip()[:80]}")
            if blender.FIZIK.search(metin) and not blender.PISIRME.search(metin):
                hits.append(f"{p.relative_to(O.ROOT)}: fizik benzetimi var ama pişirme yok")
        return hits


def surucu(m: str):
    if m == "hyperframes":
        return _HF
    if m == "blender":
        return _BL
    if m == "manim":
        import manim_kopru
        return manim_kopru.Surucu
    raise SystemExit(f"Motor yok: {m}")


# ---------------------------------------------------------------- önbellek, eşitleme, hazırlık
def esitle(v):
    """public/<id>/plaka → out/_plaka/<id> (göreli bağlantı) ve public/<id>/plaka.json: sahnelerin pencereleri + varsayılan kümeler.
    Film plaka.json'ı içe aktarır (<Plaka veri={PLAKA} sahne="…" />)."""
    if not var_mi(v):
        return
    d = ONBELLEK / v.id
    d.mkdir(parents=True, exist_ok=True)
    v.pub.mkdir(parents=True, exist_ok=True)
    b = v.pub / "plaka"
    hedef = os.path.relpath(d, v.pub)
    if b.is_symlink() and os.readlink(b) != hedef:
        b.unlink()
    if not b.is_symlink():
        if b.exists():
            raise SystemExit(f"{b} bir klasör; plakalar out/_plaka'da durur, bu bir bağlantı olmalı")
        b.symlink_to(hedef)
    pj = v.pub / "plaka.json"
    eski = O.jload(pj) if pj.exists() else {}
    yeni = {"_doc": "./st yazar (pipeline/plaka.py): script.json → sahneler. Elle değiştirme.", "id": v.id,
            "kume": eski.get("kume") or {},
            "sahneler": {S["ad"]: {"motor": S["motor"], "bas": S["bas_f"], "son": S["son_f"], "r0": S["r0"], "r1": S["r1"], "saydam": bool(S.get("saydam"))}
                         for S in sahneler(v) if not S["hata"]}}
    metin = json.dumps(yeni, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if not pj.exists() or pj.read_text() != metin:
        pj.write_text(metin)


def _varsayilan_yaz(v, ad, fmt, kalite, kume):
    pj = v.pub / "plaka.json"
    P = O.jload(pj)
    if P.setdefault("kume", {}).setdefault(ad, {}).setdefault(fmt, {}).get(kalite) != kume:
        P["kume"][ad][fmt][kalite] = kume
        pj.write_text(json.dumps(P, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def _temizle(v, ad, korunan):
    d = ONBELLEK / v.id / ad
    on = korunan.rsplit("-", 1)[0]
    kumeler = sorted((p for p in d.iterdir() if p.is_dir() and p.name.rsplit("-", 1)[0] == on), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in kumeler[TUT:]:
        if p.name != korunan:
            shutil.rmtree(p, ignore_errors=True)


def kume(v, S, fmt, kalite="taslak"):
    D = surucu(S["motor"])
    k = kalite if kalite in D.kaliteler else D.kaliteler[-1]
    return D.kume(v, S, fmt, k)


def hazirla(v, frames, fmt: str, props: dict | None = None, yalniz: str | None = None) -> dict:
    """render_frames için: istenen karelerden sahnelerin çizim aralığına düşenlerin plakaları (önbellekte yoksa motoruyla çizilir)
    → props + plaka: {sahne: küme}. Sahne dışındaki bir kare hiçbir plaka çizdirmez. yalniz: yalnız bu sahnenin plakaları çizilir."""
    esitle(v)
    props = dict(props or {})
    kalite = props.pop("kalite", "taslak")
    istek = sorted({int(f) for f in frames})
    out = {}
    for S in sahneler(v):
        if S["hata"]:
            raise SystemExit(f"{v.id}: sahne {S['ad']}: {S['hata']} (./st lint {v.id})")
        D = surucu(S["motor"])
        kq = kalite if kalite in D.kaliteler else D.kaliteler[-1]
        ad_kume, ek = D.kume(v, S, fmt, kq)
        out[S["ad"]] = ad_kume
        need = [f for f in istek if S["r0"] <= f < S["r1"]] if yalniz in (None, S["ad"]) else []
        d = ONBELLEK / v.id / S["ad"] / ad_kume
        eksik = [f for f in need if not (d / f"p{f:05d}.png").exists()]
        if eksik:
            d.mkdir(parents=True, exist_ok=True)
            if not (d / "bilgi.json").exists():
                (d / "bilgi.json").write_text(json.dumps({"video": v.id, "sahne": S["ad"], "motor": S["motor"], "format": fmt, "kalite": kq,
                                                          "aralik": [S["r0"], S["r1"]], "olusturma": time.strftime("%Y-%m-%d %H:%M"),
                                                          "kaynaklar": [str(p.relative_to(O.ROOT)) for p in D.kaynaklar(v, S)]},
                                                         ensure_ascii=False, indent=1) + "\n")
            print(f"→ sahne {S['ad']} ({S['motor']}): {len(eksik)} plaka çizilecek [{fmt} · {kq} · küme {ad_kume}] · aralık f{S['r0']}–f{S['r1'] - 1}",
                  flush=True)
            t0 = time.time()
            D.ciz(v, S, fmt, kq, ad_kume, ek, eksik, d)
            print(f"   sahne {S['ad']}: {len(eksik)} plaka {time.time() - t0:.1f} sn", flush=True)
            _temizle(v, S["ad"], ad_kume)
        if "gorunus" not in props:
            _varsayilan_yaz(v, S["ad"], fmt, kq, ad_kume)
    return {**props, "plaka": out}


def tum_kareler(v) -> list[int]:
    return sorted({f for S in sahneler(v) if not S["hata"] for f in range(S["r0"], S["r1"])})


def kaynaklar(v) -> list[Path]:
    """Kaba kurgunun tazeliği için: bütün sahnelerin kodu (+ motor kitleri) ve script.json."""
    out = [v.dir / "script.json"]
    for S in sahneler(v):
        if not S["hata"]:
            out += surucu(S["motor"]).kaynaklar(v, S)
    return [p for p in out if p.exists()]


def yeniden_ciz(v, fmt: str, sayi: int = 2) -> list[str]:
    """Deterministiklik (motorların tarafı): her sahnenin önbellekteki birkaç plakası ayrı bir işlemde yeniden çizilip karşılaştırılır
    (HyperFrames bayt bayt, Blender toleranslı). Önce tam kalite, yoksa taslak."""
    satir = []
    for S in sahneler(v):
        if S["hata"]:
            continue
        D = surucu(S["motor"])
        for kq in reversed(D.kaliteler):
            ad_kume, ek = D.kume(v, S, fmt, kq)
            d = ONBELLEK / v.id / S["ad"] / ad_kume
            var = sorted(int(p.stem[1:]) for p in d.glob("p*.png")) if d.exists() else []
            if var:
                break
        else:
            satir.append(f"⏸ [{fmt}] sahne {S['ad']}: önbellekte güncel plaka yok (önce ./st kare / inceleme)")
            continue
        sec = sorted({var[0], var[len(var) // 2], var[-1]})[:max(2, sayi)] if len(var) > 1 else var
        satir += D.yeniden(v, S, fmt, ad_kume, ek, sec, d)
    return satir


def tara(v) -> list[str]:
    """./st deterministik ve tip: her sahnede kendi motorunun taraması (HyperFrames: gizli saat, CSS animasyonu; Blender: saat, tohumsuz rastgelelik,
    kare işleyicisi, pişirilmemiş fizik)."""
    hits = []
    for S in sahneler(v):
        if not S["hata"]:
            hits += surucu(S["motor"]).tara(v, S)
    return hits


def denetle(v) -> int:
    """./st tip: her sahne kendi motorunun denetimiyle (HyperFrames check her format; Blender tarama + kuru kurulum)."""
    kotu = 0
    for S in sahneler(v):
        if S["hata"]:
            print(f"❌ sahne {S['ad']}: {S['hata']}")
            kotu += 1
            continue
        kotu += surucu(S["motor"]).denetle(v, S)
    return kotu


def teslim_eksik(v) -> list[str]:
    """./st durum (Kapı 6 kanıtı): her sahnenin her formatta tam kalitede bütün plakaları önbellekte mi."""
    eksik = []
    for S in sahneler(v):
        if S["hata"]:
            eksik.append(f"sahne {S['ad']}: {S['hata']}")
            continue
        D = surucu(S["motor"])
        for fmt in v.formatlar:
            ad_kume, _ = D.kume(v, S, fmt, D.kaliteler[-1])
            d = ONBELLEK / v.id / S["ad"] / ad_kume
            n = sum(1 for f in range(S["r0"], S["r1"]) if (d / f"p{f:05d}.png").exists())
            if n < S["r1"] - S["r0"]:
                eksik.append(f"sahne {S['ad']} [{fmt}] tam plaka {n}/{S['r1'] - S['r0']} (./st render {v.id} --final çizer)")
    return eksik


def durum(v, ad: str | None = None):
    esitle(v)
    print(f"■ {v.id} · karma film · {len(sahneler(v))} sahne · {v.nframes} kare · {', '.join(v.formatlar)}")
    for d_, m in sorunlar(v):
        print(f"  {d_} {m}")
    for S in sahneler(v):
        if ad and S["ad"] != ad:
            continue
        if S["hata"]:
            print(f"  {S['ad']}: ❌ {S['hata']}")
            continue
        D = surucu(S["motor"])
        bilgi = f" · çizer {S.get('cizer') or 'cycles'}" if S["motor"] == "blender" else ""
        print(f"  {S['ad']} · {S['motor']}{bilgi}{' · saydam' if S.get('saydam') else ''} · pencere f{S['bas_f']}–f{S['son_f'] - 1} "
              f"({O.tc(S['bas_f'] / v.fps)}–{O.tc(S['son_f'] / v.fps)}) · çizim aralığı f{S['r0']}–f{S['r1'] - 1} · kod {S['kok'].relative_to(O.ROOT)}")
        for fmt in v.formatlar:
            for kq in D.kaliteler:
                ad_kume, _ = D.kume(v, S, fmt, kq)
                d = ONBELLEK / v.id / S["ad"] / ad_kume
                n = sum(1 for f in range(S["r0"], S["r1"]) if (d / f"p{f:05d}.png").exists())
                print(f"    [{fmt} · {kq}] {ad_kume}: {n}/{S['r1'] - S['r0']} plaka" + (" ✅" if n == S["r1"] - S["r0"] else ""))


def yeni(v, ad: str, motor: str, bas: str, son: str, cizer: str | None = None, saydam=False):
    """Sahne iskeleti (hf/<id>/sahneler/<ad>/ ya da blender/<id>/sahneler/<ad>/sahne.py) + script.json → sahneler satırı."""
    if not AD.match(ad):
        raise SystemExit("Sahne adı: küçük harf, rakam ve alt çizgi (2–31 karakter)")
    if motor not in MOTORLAR:
        raise SystemExit(f"Motor: {' | '.join(MOTORLAR)}")
    if v.motor != "remotion":
        raise SystemExit(f"Karma film Remotion birleştiricilidir ({v.id} motoru {v.motor})")
    if any(S.get("ad") == ad for S in v.script.get("sahneler") or []):
        raise SystemExit(f"Sahne zaten var: {ad}")
    S = {"ad": ad, "motor": motor, "bas": bas, "son": son, **({"cizer": cizer} if cizer and cizer != "cycles" else {}), **({"saydam": True} if saydam else {})}
    d = kok(v, S)
    if d.exists():
        raise SystemExit(f"Klasör zaten var: {d.relative_to(O.ROOT)}")
    fmt = v.formatlar[0]
    if motor == "hyperframes":
        import hf
        d.mkdir(parents=True)
        F = O.FORMATLAR[fmt]
        for src in hf.SABLON.iterdir():
            t = src.read_text()
            for k, val in {"{{ID}}": f"{v.id} · {ad}", "{{BASLIK}}": f"{v.script.get('title', v.id)} · {ad}", "{{W}}": str(F["w"]), "{{H}}": str(F["h"]),
                           "{{FORMAT}}": fmt, "{{DIL}}": v.script.get("dil", "tr")}.items():
                t = t.replace(k, val)
            (d / src.name).write_text(t)
        (d / "assets").mkdir(exist_ok=True)
    elif motor == "blender":
        import blender
        d.mkdir(parents=True)
        t = (blender.SABLON / "sahne.py").read_text().replace("{{ID}}", f"{v.id}/{ad}").replace("{{BASLIK}}", f"{v.script.get('title', v.id)} · {ad}")
        (d / "sahne.py").write_text(t.replace("{{FORMAT}}", fmt))
    else:
        import manim_kopru
        manim_kopru.yeni(d, v, ad)
    p = v.dir / "script.json"
    sc = json.loads(p.read_text())
    sc.setdefault("sahneler", []).append(S)
    p.write_text(json.dumps(sc, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ sahne {ad} ({motor}) · kod {d.relative_to(O.ROOT)} · script.json → sahneler (bas {bas}, son {son})")
