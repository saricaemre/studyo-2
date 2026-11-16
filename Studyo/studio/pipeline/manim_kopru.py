"""Manim motoru (oturum 6c): karma filmin formül, grafik ve şema sahneleri (Manim Community, MIT; Cairo çizeri, OpenGL yok).

Sahne manim/<id>/sahneler/<ad>/sahne.py'de (kit: manim/kit/, kurallar manim/CLAUDE.md), sınıf adı `Sahne`. 6b'nin plaka düzenine bir motor:
pipeline/plaka.py bu modülün sürücüsünü (Surucu) çağırır; plakalar out/_plaka/<id>/<ad>/<format>-tam-<parmak izi>/pNNNNN.png.
- Manim rastgele kareye erişemez: bir küme eksikse sahnenin BÜTÜN plakaları bir kez çizilir (Cairo, PNG dizisi) ve parmak iziyle dondurulur.
  Kare sayısı çizim aralığıyla aynı olmalı (kit.sona_kadar); değilse iş durur ve nedenini söyler.
- Parmak izi: Manim sürümü (sabit) + kit + sahne klasörü + yerel ST (format, işaretler, görünüş, yazı tipi dosyalarının sha256'sı) + saydam.
- Yazı tipleri: görünüşün aileleri (src/lib/fontlar.ts; @remotion/google-fonts) woff2 olarak indirilir (latin + latin-ext: Türkçe), fontTools ile
  TTF'ye çevrilip birleştirilir (out/_manim_fontlar/), kit Pango'ya kaydeder (manimpango.register_font).
- İsteğe bağlı kurulum: Manim yoksa Manim sahneli film açıklayıcı bir hatayla durur ve kurulum satırını söyler (Kur.command zorla kurmaz).
LaTeX (MathTex) kurulu değil (BasicTeX yönetici parolası ister: kullanıcının kararı); formül Text/Unicode ya da Typst (MathTypst, pip) ile.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import ortak as O

SURUM = "0.22.1"   # sabit: aynı kaynak aynı plakayı versin; yükseltmeden önce Manim sahnelerinde plaka karşılaştırması
PY = str(O.ROOT / ".venv" / "bin" / "python")
KIT = O.ROOT / "manim" / "kit"
FONT_ON = O.ROOT / "out" / "_manim_fontlar"
KURULUM = "uv pip install --python .venv/bin/python -r requirements-manim.txt (önce: brew install cairo pango)"
YASAK = [
    (re.compile(r"(?<![\w.])random\.(random|uniform|randint|randrange|choice|choices|shuffle|gauss|sample|seed)\("), "tohumsuz random: kit.rastgele(n)"),
    (re.compile(r"\bnp\.random\.(?!default_rng\(\s*\d)|\bnumpy\.random\.(?!default_rng\(\s*\d)"), "tohumsuz numpy.random"),
    (re.compile(r"\b(time\.time|time\.perf_counter|time\.monotonic|datetime\.|os\.urandom|uuid\.)"), "saat ya da sistem rastgeleliği"),
    (re.compile(r"\brandom\.Random\(\s*\)"), "tohumsuz random.Random()"),
    (re.compile(r"\bself\.(play|wait)\("), "self.play / self.wait yerine kit.oyna / kit.bekle (kare sayısı tam; işaret karesi kayar)"),
    (re.compile(r"\b(MathTex|Tex|SingleStringMathTex)\("), "LaTeX kurulu değil (kullanıcının kararı): Text, MathTypst ya da Unicode formül"),
    (re.compile(r"renderer\s*=\s*['\"]opengl|OpenGL"), "OpenGL çizeri yok (Cairo: deterministik)"),
]
_surum = None


def kurulu():
    """True ya da kurulum satırı (Manim isteğe bağlı; sürüm sabit)."""
    global _surum
    if _surum is None:
        r = subprocess.run([PY, "-c", "import manim, fontTools, brotli; print(manim.__version__)"], capture_output=True, text=True)
        _surum = r.stdout.strip() if r.returncode == 0 else ""
    if not _surum:
        return f"Manim kurulu değil (isteğe bağlı motor): {KURULUM}"
    if _surum != SURUM:
        return f"Manim {_surum} kurulu, stüdyo {SURUM} istiyor (sürüm değişince plakalar değişir: önce karşılaştır, sonra bilerek yükselt)"
    return True


def _statik(yol: Path, agirlik: int, aile_st: str):
    """woff2 → statik TTF: değişken yazı tipi istenen ağırlıkta örneklenir (fontTools.merge değişken yazı tipini birleştiremiyor), aile adı
    ağırlığa özel ve tekil olur ("Inter ST500"): Pango/CoreText ağırlığı ad üzerinden değil aile adından bulur, PostScript adları çakışmaz."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    f = TTFont(str(yol))
    f.flavor = None
    if "fvar" in f:
        eksen = {a.axisTag: a for a in f["fvar"].axes}
        konum = {t: a.defaultValue for t, a in eksen.items()}
        if "wght" in eksen:
            konum["wght"] = max(eksen["wght"].minValue, min(eksen["wght"].maxValue, agirlik))
        f = instancer.instantiateVariableFont(f, konum)
    f["OS/2"].usWeightClass = 400
    ps = re.sub(r"[^A-Za-z0-9-]", "", aile_st.replace(" ", "-"))
    for kayit in f["name"].names:
        if kayit.nameID in (1, 16):
            kayit.string = aile_st
        elif kayit.nameID in (2, 17):
            kayit.string = "Regular"
        elif kayit.nameID == 4:
            kayit.string = f"{aile_st} Regular"
        elif kayit.nameID == 6:
            kayit.string = f"{ps}-Regular"
    return f


def _fontlar_hazir(aile: str, agirlik: int) -> dict:
    """Ailenin bir ağırlığı: latin + latin-ext woff2 (önbellek: out/_hf_fontlar) → statik, birleşik TTF (out/_manim_fontlar/)
    → {aile (Pango'nun adı), agirlik, dosya, cap, sha}."""
    import hf
    from fontTools.merge import Merger
    from fontTools.ttLib import TTFont
    FONT_ON.mkdir(parents=True, exist_ok=True)
    ad = re.sub(r"[^a-z0-9]+", "-", aile.lower())
    aile_st = f"{aile} ST{agirlik}"
    hedef = FONT_ON / f"{ad}-{agirlik}.ttf"
    if not hedef.exists():
        r = subprocess.run(["node", "pipeline/fontlar.mjs", "--bilgi", aile], cwd=O.ROOT, capture_output=True, text=True, check=True)
        B = json.loads(r.stdout).get(aile)
        if not B:
            raise SystemExit(f"Yazı tipi listede yok: {aile} (src/lib/fontlar.ts)")
        var = sorted(int(w) for w in B["fonts"]["normal"])
        w = agirlik if agirlik in var else min(var, key=lambda x: abs(x - agirlik))
        with tempfile.TemporaryDirectory(prefix="st_manim_font_") as tmp:
            parcalar = []
            for alt in ("latin", "latin-ext"):
                url = B["fonts"]["normal"][str(w)].get(alt)
                if not url:
                    continue
                w2 = Path(tmp) / f"{alt}.woff2"
                hf._indir(url, w2)
                tt = Path(tmp) / f"{alt}.ttf"
                _statik(w2, agirlik, aile_st).save(str(tt))
                parcalar.append(str(tt))
            if not parcalar:
                raise SystemExit(f"{aile} {w}: latin alt kümesi yok")
            birlesik = Merger().merge(parcalar) if len(parcalar) > 1 else TTFont(parcalar[0])
            birlesik.save(str(hedef + "") if isinstance(hedef, str) else str(hedef))
    f = TTFont(str(hedef))
    cap = getattr(f["OS/2"], "sCapHeight", 0) or 0.7 * f["head"].unitsPerEm
    eksik = [c for c in "ÇĞİÖŞÜçğıöşü" if ord(c) not in f.getBestCmap()]
    if eksik:
        raise SystemExit(f"{aile} {agirlik}: Türkçe harf eksik ({''.join(eksik)}); latin-ext alt kümesi birleşmedi")
    return {"aile": aile_st, "css_aile": aile, "agirlik": int(agirlik), "dosya": str(hedef), "cap": round(cap / f["head"].unitsPerEm, 5),
            "sha": hashlib.sha256(hedef.read_bytes()).hexdigest()[:16]}


def fontlar(v) -> dict:
    """Görünüşün rolleri (baslik, govde, aksan) → kitin yazı tipleri."""
    s = v.gorunus_secimi or {}
    Y = s.get("yazi") or {}
    out = {}
    for rol in ("baslik", "govde", "aksan"):
        y = Y.get(rol) or Y.get("govde") or Y.get("baslik")
        if y:
            out[rol] = _fontlar_hazir(y["aile"], int(y["agirlik"]))
    return out


def veri(P, fmt: str, saydam=False) -> dict:
    """Kitin ST'si (yerel zaman; pipeline/plaka.py → yerel)."""
    F = O.FORMATLAR[fmt]
    tl = P.timeline or {}
    r3 = lambda x: round(float(x), 4)
    s = P.gorunus_secimi or {}
    return {"id": P.id, "format": fmt, "w": F["w"], "h": F["h"], "fps": P.fps, "sure": r3(P.duration), "nkare": P.nframes,
            "isaretler": {k: r3(t) for k, t in sorted(P.cues.items())},
            "vuruslar": [{"id": x["id"], "step": x["step"], "start": r3(x["start"]), "end": r3(x["end"])} for x in tl.get("sentences", [])],
            "beats": [r3(b) for b in tl.get("beats", [])], "guvenli": F["guvenli"], "renk": dict(s.get("renk") or {}), "gorunus": s,
            "sahne": P.script.get("_sahne"), "fontlar": fontlar(P), "tohum": int(hashlib.sha1(P.id.encode()).hexdigest()[:6], 16), "saydam": bool(saydam)}


def _cagir(sahne: Path, V: dict, fmt: str, hedef: Path, kuru=False) -> list[Path]:
    """manim render (Cairo) → hedef/ PNG dizisi; → yazılan kareler (sırayla)."""
    ok = kurulu()
    if ok is not True:
        raise SystemExit(ok)
    with tempfile.NamedTemporaryFile("w", suffix=".json", prefix="st_manim_", delete=False) as f:
        json.dump(V, f, ensure_ascii=False)
        vyol = f.name
    medya = hedef / "_medya"
    shutil.rmtree(medya, ignore_errors=True)
    cmd = [PY, "-m", "manim", "render", str(sahne), "Sahne", "--renderer", "cairo", "--format", "png-sequence", "-r", f"{V['w']},{V['h']}",
           "--fps", str(V["fps"]), "--media_dir", str(medya), "--disable_caching", "--progress_bar", "none", "-v", "WARNING"] + \
          (["-t"] if V["saydam"] else []) + (["--dry_run"] if kuru else [])
    env = {**os.environ, "ST_VERI": vyol, "PYTHONPATH": str(KIT.parent), "PYTHONWARNINGS": "ignore"}
    try:
        r = subprocess.run(cmd, cwd=sahne.parent, env=env, capture_output=True, text=True)
    finally:
        os.unlink(vyol)
    if r.returncode:
        hata = "\n".join(x for x in (r.stdout + r.stderr).splitlines() if x.strip())[-3000:]
        raise SystemExit(f"Manim sahnesi başarısız ({sahne.relative_to(O.ROOT)}, {fmt}):\n{hata}")
    if kuru:
        return []
    pngs = sorted(medya.rglob("*.png"), key=lambda p: int(re.search(r"(\d+)\.png$", p.name).group(1)))
    return pngs


class Surucu:
    kaliteler = ("tam",)   # Cairo, tam çözünürlük; taslak/tam aynı plaka

    @staticmethod
    def kaynaklar(v, S) -> list[Path]:
        import plaka
        return plaka._dosyalar(S["kok"]) + plaka._dosyalar(KIT)

    @staticmethod
    def kume(v, S, fmt, kalite):
        import plaka
        P = plaka.yerel(v, S)
        V = veri(P, fmt, S.get("saydam"))
        h = hashlib.sha256()
        h.update(f"manim {SURUM}\nmanim-sahne 1\n{fmt}\n".encode())
        for p in Surucu.kaynaklar(v, S) + plaka._varliklar(v):
            plaka._ozet(h, p)
        h.update(json.dumps({k: x for k, x in V.items() if k != "fontlar"}, sort_keys=True, ensure_ascii=False).encode())
        h.update(json.dumps({r: (f["aile"], f["agirlik"], f["sha"]) for r, f in V["fontlar"].items()}, sort_keys=True).encode())
        return f"{fmt}-tam-{h.hexdigest()[:12]}", (P, V)

    @staticmethod
    def ciz(v, S, fmt, kalite, kume, PV, kareler, hedef: Path):
        """Manim rastgele kareye erişemez: kümenin bütün plakaları bir kez çizilir (kareler yalnız neyin eksik olduğunu söyler)."""
        P, V = PV
        n = S["r1"] - S["r0"]
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix="st_manim_") as tmp:
            pngs = _cagir(S["kok"] / "sahne.py", V, fmt, Path(tmp))
            if len(pngs) != n:
                raise SystemExit(f"Manim sahnesi {S['ad']} ({fmt}) {len(pngs)} kare yazdı, çizim aralığı {n} kare (f{S['r0']}–f{S['r1'] - 1}): "
                                 "sahne kit.sona_kadar(self) ile bitmeli; animasyonlar kit.oyna / kit.bekle ile tam kare")
            for i, p in enumerate(pngs):
                os.replace(p, hedef / f"p{S['r0'] + i:05d}.png")
        print(f"   Manim {SURUM}: {n} plaka {time.time() - t0:.1f} sn ({(time.time() - t0) / n:.2f} sn/kare)", flush=True)

    @staticmethod
    def yeniden(v, S, fmt, kume, PV, kareler, hedef_eski: Path) -> list[str]:
        """Bütün sahne ayrı bir işlemde yeniden çizilir; bütün plakalar bayt bayt karşılaştırılır (Cairo)."""
        P, V = PV
        with tempfile.TemporaryDirectory(prefix="st_manim_det_") as tmp:
            pngs = _cagir(S["kok"] / "sahne.py", V, fmt, Path(tmp))
            fark = [S["r0"] + i for i, p in enumerate(pngs) if p.read_bytes() != (hedef_eski / f"p{S['r0'] + i:05d}.png").read_bytes()]
            n = len(pngs)
        return [f"{'✅' if not fark else '❌'} [{fmt}] sahne {S['ad']} (Manim {SURUM}, Cairo): {n - len(fark)}/{n} plaka ayrı işlemde bayt bayt aynı"
                + (f" · farklı: {fark[:8]}" if fark else "")]

    @staticmethod
    def denetle(v, S) -> int:
        """./st tip: tarama + kuru çalıştırma (her format; Manim sahneyi kurar, kare yazmaz)."""
        import plaka
        hits = Surucu.tara(v, S)
        print(f"\n[sahne {S['ad']} · Manim {SURUM}]")
        print("✅ sahne kodunda gizli saat / tohumsuz rastgelelik / LaTeX / OpenGL yok, kare sayan kit kullanılıyor" if not hits
              else "❌ sahne kodu:\n  " + "\n  ".join(hits))
        ok = kurulu()
        if ok is not True:
            print(f"❌ {ok}")
            return 1
        for fmt in v.formatlar:
            P = plaka.yerel(v, S)
            with tempfile.TemporaryDirectory(prefix="st_manim_kuru_") as tmp:
                _cagir(S["kok"] / "sahne.py", veri(P, fmt, S.get("saydam")), fmt, Path(tmp), kuru=True)
            print(f"✅ [{fmt}] sahne kuruldu (kuru çalıştırma)")
        return int(bool(hits))

    @staticmethod
    def tara(v, S) -> list[str]:
        import plaka
        hits = []
        for p in plaka._dosyalar(S["kok"]):
            if p.suffix != ".py":
                continue
            for i, ln in enumerate(p.read_text().splitlines(), 1):
                kod = ln.split("#", 1)[0]
                for pat, neden in YASAK:
                    if pat.search(kod):
                        hits.append(f"{p.relative_to(O.ROOT)}:{i}: {neden}: {ln.strip()[:80]}")
        return hits


def yeni(d: Path, v, ad: str):
    d.mkdir(parents=True)
    (d / "sahne.py").write_text(f'''"""{v.script.get("title", v.id)} · {ad}: karma filmin Manim sahnesi. Kit: manim/kit (import kit) · kurallar: manim/CLAUDE.md.

Zaman YEREL (0 = sahnenin çizim aralığının başı); olaylar yalnız işaretlerden (kit.isarete_kadar), animasyon tam kare (kit.oyna),
renk görünüşten (kit.renk), yazı görünüşün yazı tipiyle (kit.yazi, ≥ 64 px). Her format ayrı yerleşim: ST.dikey, ST.guvenli. Sahne
kit.sona_kadar(self) ile biter (kare sayısı = çizim aralığı).
"""
from manim import Axes, Create, Scene, Write

import kit
from kit import ST


class Sahne(Scene):
    def construct(self):
        eksen = Axes(x_range=[0, 4, 1], y_range=[0, 16, 4], x_length=config_genislik(), y_length=4.5,
                     axis_config={{"color": kit.renk("soluk"), "include_tip": False}})
        self.add(eksen)
        egri = eksen.plot(lambda x: 2 ** x, x_range=[0, 4], color=kit.renk("vurgu"))
        kit.isarete_kadar(self, sorted(ST.isaretler, key=ST.isaretler.get)[0])
        kit.oyna(self, Create(egri), kare=30)
        kit.sona_kadar(self)


def config_genislik():
    return 5.0 if ST.dikey else 9.0
''')
