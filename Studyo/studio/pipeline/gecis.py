"""Gölgelendirici geçişleri (oturum 6a): gl-transitions 3.0.0 (MIT) kütüphanesi, kesimler ve geçiş plakaları.

Kütüphane: node_modules/gl-transitions (sabit 3.0.0) → src/lib/gecis/gecisler.json (`./st gecis uret`; ek doku isteyen iki geçiş,
DisplacementMap ve LumaWipe, çıkarılır). Remotion `<GlGecis>` iki görüntüyü gölgelendiriciyle birleştirir (src/lib/gecis/GlGecis.tsx).

Kesim (script.json → shot.gecis yapılandırılmış biçim):
  "gecis": {"gl": "BookFlip", "kare": 18, "param": {…}, "kesim": "<işaret>", "egri": "yumusak|dogrusal", "neden": "…"}
  Vuruşun geçişi o vuruştan SONRAKİ vuruşa geçiştir (çekim listesindeki "Geçiş (sonrakine ne taşınır)" sütunuyla aynı anlam).
  `kesim` yoksa kesim sonraki vuruşun başlangıcıdır (timeline.json; anlatımsız filmde `bas` çapası). Serbest metin `gecis` (eski filmler) aynen kalır.
Zaman: geçiş kesimin ortasında durur, pencere [kesim − N/2, kesim + N/2) (kare). Giden sahne N/2 kare uzar, gelen N/2 kare erken başlar;
filmin süresi ve işaret zamanları değişmez (bindirip kısaltmak yok). İlerleme yalnız kareden: yumusak((f − bas + 1) / (N + 1)) (Kesim.tsx).

Geçiş plakası (DOM sahneleri): film kodu kesimi `<Kesim ad gecis a b />` ile işaretler. Çizimden önce `hazirla` penceredeki her istenen kareyi
iki kez çizer: girdi `gecisPlakasi: {kesim, taraf}` ile yalnız o taraf, tam kare, üst katmansız (Bitis, altyazı, etiket, `<UstKatman>`).
Plakalar out/_gecis/<id>/<format>-<parmak izi>/<kesim>/<a|b>/pNNNNN.png; Remotion'a public/<id>/gecis bağlantısıyla gelir (Blender plakaları gibi).
Parmak izi: filmin kodu (src/<kod>/) ve ortak kitaplıklar (src/lib, components, stiller), filmin verisi (script, işaretler, görünüş, zaman çizelgesi, varlıklar), format, GL ayarı, girdi. Kesimlerin
tanımı ve varsayılan kümeler public/<id>/gecis.json'da (film içe aktarır; `./st` yazar). Kesim başına 2 × N kare: ucuz, her değişiklikte yeniden.
"""
import hashlib
import json
import math
import os
import shutil
import tempfile
import time
from pathlib import Path

import ortak as O

SURUM = "3.0.0"   # sabit (package.json devDependencies); yükseltmek = geçişlerin çizimi değişebilir, kullanıcı kararı
GLT = O.ROOT / "node_modules" / "gl-transitions"
KUTUPHANE = O.ROOT / "src" / "lib" / "gecis" / "gecisler.json"
ONBELLEK = O.ROOT / "out" / "_gecis"
ONIZLEME = O.ROOT / "katalog" / "onizleme" / "gecis"
TUT = 3                  # format başına saklanan en yeni plaka kümesi
EGRILER = ("yumusak", "dogrusal")
_kutuphane = None


# ---------------------------------------------------------------- kütüphane
def uret() -> dict:
    """node_modules/gl-transitions/gl-transitions.json → src/lib/gecis/gecisler.json (ek doku isteyenler çıkarılır)."""
    kaynak = GLT / "gl-transitions.json"
    pk = GLT / "package.json"
    if not kaynak.exists():
        raise SystemExit(f"gl-transitions yok: {GLT} (npm install; package.json → devDependencies gl-transitions {SURUM})")
    surum = O.jload(pk)["version"]
    if surum != SURUM:
        raise SystemExit(f"gl-transitions {surum} kurulu, stüdyo {SURUM} istiyor (sabit sürüm: geçişlerin çizimi sürüme bağlı)")
    L = O.jload(kaynak)
    cikan = {x["name"]: f"ek doku ister: {', '.join(x['textures'])}" for x in L if x.get("textures")}
    gecisler = [{"name": x["name"], "author": x.get("author", ""), "license": x.get("license", ""), "description": x.get("description", ""),
                 "tags": x.get("tags") or [], "params": x.get("params") or {}, "glsl": x["glsl"]}
                for x in sorted(L, key=lambda x: x["name"]) if x["name"] not in cikan]
    lisanslar = {}
    for g in gecisler:
        lisanslar[g["license"]] = lisanslar.get(g["license"], 0) + 1
    veri = {"_doc": "./st gecis uret üretir (pipeline/gecis.py); elle değiştirme. Kaynak: gl-transitions npm paketi, sabit sürüm. "
                    "Her geçişin yazarı ve lisansı kendi satırında; paketin MIT lisansı LISANS-gl-transitions.txt.",
            "kaynak": f"gl-transitions {surum}", "lisans": "MIT (Copyright (c) 2017-present gl-transitions contributors); geçiş başına: license alanı",
            "lisanslar": lisanslar, "cikarilan": cikan, "gecisler": gecisler}
    KUTUPHANE.parent.mkdir(parents=True, exist_ok=True)
    KUTUPHANE.write_text(json.dumps(veri, ensure_ascii=False, indent=0) + "\n")
    shutil.copy2(GLT / "LICENSE", KUTUPHANE.parent / "LISANS-gl-transitions.txt")
    global _kutuphane
    _kutuphane = None
    return veri


def kutuphane() -> dict[str, dict]:
    """{ad: geçiş} (src/lib/gecis/gecisler.json)."""
    global _kutuphane
    if _kutuphane is None:
        if not KUTUPHANE.exists():
            raise SystemExit("src/lib/gecis/gecisler.json yok: ./st gecis uret")
        _kutuphane = {g["name"]: g for g in O.jload(KUTUPHANE)["gecisler"]}
    return _kutuphane


def cikarilan() -> dict:
    return O.jload(KUTUPHANE).get("cikarilan", {}) if KUTUPHANE.exists() else {}


def param_ozeti(g: dict) -> str:
    """"direction vec2 = [1, -1] · smoothness float = 0.5" (liste ve panel için)."""
    def deg(x):
        return json.dumps(x).replace(" ", "") if isinstance(x, list) else ("true" if x is True else "false" if x is False else f"{x:g}"
                                                                           if isinstance(x, (int, float)) else str(x))
    return " · ".join(f"{a} {p['type']}" + (f" = {deg(p['default'])}" if "default" in p else "") for a, p in g["params"].items()) or "parametresiz"


# ---------------------------------------------------------------- kesimler
def _gecis_alani(s: dict):
    g = (s.get("shot") or {}).get("gecis")
    return g if isinstance(g, dict) else None


def var_mi(v) -> bool:
    """Filmde yapılandırılmış geçiş (shot.gecis nesne) var mı. Yoksa hiçbir şey değişmez (eski filmler, serbest metin geçişler)."""
    return any(_gecis_alani(s) for s in v.script.get("sentences", []))


def kare_no(sn: float, fps: int) -> int:
    """Saniye → kare: yarım yukarı (Python round'un "çifte yuvarla"sı 64,5 → 64 verir; kesim karesi tek yerde hesaplanır, gecis.json taşır)."""
    return int(math.floor(sn * fps + 0.5))


def kesimler(v) -> list[dict]:
    """Yapılandırılmış geçişler → [{ad, gl, kare, param, egri, neden, vurus, sonraki, kesim_sn, kesim, bas, son, vurus_bas, sonraki_son, hata}].
    kesim, bas, son: kare (son hariç). Zaman çizelgesi ya da işaret yoksa hata alanı dolu (lint söyler)."""
    S = v.script.get("sentences", [])
    tl = {x["id"]: x for x in (v.timeline or {}).get("sentences", [])}
    out = []
    for i, s in enumerate(S):
        g = _gecis_alani(s)
        if not g:
            continue
        k = {"ad": str(g.get("ad") or s["id"]), "gl": g.get("gl"), "kare": g.get("kare"), "param": g.get("param") or {},
             "egri": g.get("egri") or "yumusak", "neden": g.get("neden") or "", "vurus": s["id"],
             "sonraki": S[i + 1]["id"] if i + 1 < len(S) else None, "isaret": g.get("kesim"), "hata": None}
        if k["sonraki"] is None:
            k["hata"] = "son vuruşta geçiş olmaz (geçiş vuruştan sonrakine geçiştir)"
        elif not tl or s["id"] not in tl or k["sonraki"] not in tl:
            k["hata"] = f"zaman çizelgesi yok (./st ses {v.id})"
        elif k["isaret"] and k["isaret"] not in v.cues:
            k["hata"] = f"kesim işareti yok: {k['isaret']} (cues.json)" + (f"; {v.cue_error}" if v.cue_error else "")
        if not k["hata"]:
            k["kesim_sn"] = round(float(v.cues[k["isaret"]] if k["isaret"] else tl[k["sonraki"]]["start"]), 4)
            k["kesim"] = kare_no(k["kesim_sn"], v.fps)
            n = int(k["kare"]) if isinstance(k["kare"], int) and not isinstance(k["kare"], bool) else 0
            k["bas"] = k["kesim"] - n // 2
            k["son"] = k["bas"] + n
            k["vurus_bas"] = kare_no(tl[s["id"]]["start"], v.fps)
            k["sonraki_son"] = kare_no(tl[k["sonraki"]]["end"], v.fps)
        out.append(k)
    return out


def sorunlar(v) -> list[tuple[str, str]]:
    """./st lint: ad kütüphanede, ek doku gerekmiyor, kare ≥ 2, parametreler tanımlı, pencere komşu iki vuruşun içinde ve filmde,
    pencereler çakışmıyor, kesim adları tekil. Gerekçe yazılmamışsa ⚠️ (zanaat: geçiş anlam taşısın)."""
    if not var_mi(v):
        return []
    try:
        L = kutuphane()
    except SystemExit as e:
        return [("❌", f"geçiş kütüphanesi: {e}")]
    out, adlar, pencereler = [], {}, []
    for k in kesimler(v):
        b = f"{k['vurus']} geçişi"
        if k["gl"] not in L:
            neden = cikarilan().get(k["gl"])
            out.append(("❌", f"{b}: “{k['gl']}” kütüphanede yok" + (f" ({neden}; stüdyoda sağlanmadı)" if neden else
                                                                     " (./st gecis liste; adlar PascalCase, gl-transitions 3.0)")))
        else:
            P = L[k["gl"]]["params"]
            bil = [a for a in k["param"] if a not in P]
            if bil:
                out.append(("❌", f"{b}: {k['gl']} bu parametreleri tanımıyor: {', '.join(bil)} (var: {', '.join(P) or 'yok'})"))
            for a, d in k["param"].items():
                if a in P and isinstance(P[a].get("default"), list) and not (isinstance(d, list) and len(d) == len(P[a]["default"])):
                    out.append(("❌", f"{b}: {a} {P[a]['type']} ister ({len(P[a]['default'])} sayı), verilen {json.dumps(d)}"))
        if not (isinstance(k["kare"], int) and not isinstance(k["kare"], bool) and k["kare"] >= 2):
            out.append(("❌", f"{b}: kare ≥ 2 olmalı (verilen {k['kare']!r}); pencere kesimin ortasında N kare"))
        if k["egri"] not in EGRILER:
            out.append(("❌", f"{b}: egri {' | '.join(EGRILER)} (verilen {k['egri']})"))
        if k["ad"] in adlar:
            out.append(("❌", f"{b}: kesim adı “{k['ad']}” {adlar[k['ad']]} geçişinde de var (gecis.ad tekil olmalı)"))
        adlar.setdefault(k["ad"], k["vurus"])
        if k["hata"]:
            out.append(("❌", f"{b}: {k['hata']}"))
            continue
        if not isinstance(k["kare"], int) or k["kare"] < 2:
            continue
        if k["bas"] < k["vurus_bas"] or k["son"] > k["sonraki_son"]:
            out.append(("❌", f"{b}: pencere f{k['bas']}–f{k['son'] - 1} komşu iki vuruşun dışına taşıyor ({k['vurus']} f{k['vurus_bas']} → "
                              f"{k['sonraki']} f{k['sonraki_son'] - 1}); kareyi azalt ya da kesimi kaydır"))
        if k["bas"] < 0 or (v.nframes and k["son"] > v.nframes):
            out.append(("❌", f"{b}: pencere film dışında (f{k['bas']}–f{k['son'] - 1}, film {v.nframes} kare)"))
        for a, (x, y) in pencereler:
            if k["bas"] < y and x < k["son"]:
                out.append(("❌", f"{b}: penceresi {a} geçişiyle çakışıyor (f{k['bas']}–f{k['son'] - 1} ↔ f{x}–f{y - 1})"))
        pencereler.append((k["vurus"], (k["bas"], k["son"])))
        if not str(k["neden"]).strip():
            out.append(("⚠️", f"{b}: gerekçe yok (gecis.neden): geçiş anlam taşımalı, düz kesim varsayılandır (zanaat §3)"))
    return out


def tanim_json(v) -> dict:
    """public/<id>/gecis.json'ın kesim tanımları (Kesim.tsx okur): {ad: {ad, gl, kare, param, egri, kesim, bas, son}}.
    Karma filmde (6b) kesim iki opak plaka sahnesinin tam sınırındaysa "dogrudan": {a, b}: motorların plakaları doğrudan gölgelendiriciye
    girer, geçiş plakası çizilmez (ikinci çizim yok)."""
    import plaka
    P = plaka.pencereler(v)
    out = {}
    for k in kesimler(v):
        if k["hata"] or not (isinstance(k["kare"], int) and not isinstance(k["kare"], bool) and k["kare"] >= 2):
            continue
        d = {"ad": k["ad"], "gl": k["gl"], "kare": k["kare"], "param": k["param"], "egri": k["egri"], "kesim": k["kesim"],
             "bas": k["bas"], "son": k["son"], "vurus": k["vurus"], "sonraki": k["sonraki"]}
        a = next((ad for ad, (m, b, s, sy) in P.items() if s == k["kesim"] and not sy), None)
        b = next((ad for ad, (m, b_, s, sy) in P.items() if b_ == k["kesim"] and not sy), None)
        if a and b:
            d["dogrudan"] = {"a": a, "b": b}
        out[k["ad"]] = d
    return out


def esitle(v):
    """public/<id>/gecis.json (kesim tanımları + format başına varsayılan küme) ve public/<id>/gecis → out/_gecis/<id> bağlantısı.
    Yalnız yapılandırılmış geçişi olan filmde; öteki filmlerde hiçbir dosya yazılmaz."""
    if not var_mi(v):
        return
    d = ONBELLEK / v.id
    d.mkdir(parents=True, exist_ok=True)
    v.pub.mkdir(parents=True, exist_ok=True)
    b = v.pub / "gecis"
    hedef = os.path.relpath(d, v.pub)
    if b.is_symlink() and os.readlink(b) != hedef:
        b.unlink()
    if not b.is_symlink():
        if b.exists():
            raise SystemExit(f"{b} bir klasör; geçiş plakaları out/_gecis'te durur, bu bir bağlantı olmalı")
        b.symlink_to(hedef)
    gj = v.pub / "gecis.json"
    eski = O.jload(gj) if gj.exists() else {}
    yeni = {"_doc": "./st yazar (pipeline/gecis.py): script.json → shot.gecis. Elle değiştirme.", "id": v.id, "fps": v.fps,
            "kume": eski.get("kume") or {}, "kesimler": tanim_json(v)}
    metin = json.dumps(yeni, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if not gj.exists() or gj.read_text() != metin:
        gj.write_text(metin)


def _varsayilan_yaz(v, fmt, kume):
    gj = v.pub / "gecis.json"
    G = O.jload(gj)
    if G.get("kume", {}).get(fmt) != kume:
        G.setdefault("kume", {})[fmt] = kume
        gj.write_text(json.dumps(G, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def pencere_kareleri(v, frames=None) -> dict[str, list[int]]:
    """{kesim adı: [pencereye düşen kareler]} (frames verilmezse pencerenin bütün kareleri)."""
    out = {}
    for ad, k in tanim_json(v).items():
        if k.get("dogrudan"):   # iki plaka sahnesi arasında: geçiş plakası gerekmez
            continue
        fr = range(k["bas"], k["son"]) if frames is None else sorted({int(f) for f in frames if k["bas"] <= int(f) < k["son"]})
        if fr:
            out[ad] = list(fr)
    return out


# ---------------------------------------------------------------- parmak izi ve plakalar
_KOD_UZANTI = {".ts", ".tsx", ".js", ".mjs", ".json", ".css"}
KOD_ORTAK = ("lib", "components", "stiller", "index.ts")   # src/ altında her filmin kullanabildiği kod (parmak izine girer)
_SES_UZANTI = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
_ATLA = {"gecis", "plaka", "_plaka", "node_modules", "__pycache__"}


def _dosyalar(kok: Path):
    """kok altındaki dosyalar (bağlantı izlenmez; plaka ve geçiş bağlantıları, ses, gizli dosyalar hariç)."""
    for dp, dn, fn in os.walk(kok, followlinks=False):
        dn[:] = sorted(x for x in dn if x not in _ATLA and not x.startswith("."))
        for f in sorted(fn):
            p = Path(dp) / f
            if f.startswith(".") or p.is_symlink() or p.suffix.lower() in _SES_UZANTI or p.name in ("gecis.json", "plaka.json"):
                continue
            yield p


def _ozet_ekle(h, p: Path):
    st = p.stat()
    h.update(str(p.relative_to(O.ROOT)).encode() + b"\0")
    if st.st_size > 8 * 2 ** 20:   # büyük varlık (gerçek görüntü videosu): boyut + değişme zamanı (içerik özeti saniyeler sürer)
        h.update(f"{st.st_size}:{st.st_mtime_ns}".encode())
    else:
        h.update(p.read_bytes())
    h.update(b"\0")


def _girdi(props: dict | None) -> dict:
    """Parmak izine giren girdi: stüdyonun kendi çizim anahtarları (küme, plaka kipi, yazılım) hariç."""
    return {k: x for k, x in (props or {}).items() if k not in ("gecisKume", "gecisPlakasi", "yazilim", "kalite")}


def parmak_izi(v, fmt: str, props: dict | None = None) -> str:
    """Küme adı <format>-<özet>. Özet: plaka sürümü, format, GL ayarı, kod (src/<kod>/ + src/lib, components, stiller, index.ts), filmin verisi (script, işaretler, görünüş, seri,
    marka, formatlar, package.json, public/<id>/ sessiz ve plakasız), kesim tanımları ve girdi (görünüş anahtarı, canlı veri)."""
    h = hashlib.sha256()
    h.update(f"gecis-plaka 1\n{fmt}\n{v.gl}\n".encode())
    # kod: filmin kendi klasörü + ortak kitaplıklar (öteki filmlerin kodu ve Root.tsx'e eklenen kayıtlar plakayı değiştirmez)
    for kok in (v.kod_dizini, *(O.ROOT / "src" / d for d in KOD_ORTAK)):
        for p in (_dosyalar(kok) if kok.is_dir() else [kok] if kok.exists() else []):
            if p.suffix in _KOD_UZANTI:
                _ozet_ekle(h, p)
    ek = [O.ROOT / "package.json", O.PROFIL_DIR / "formatlar.json", v.dir / "script.json", v.dir / "cues.json", v.dir / "gorunus.json"]
    if v.gorunus_dosyasi:
        ek.append(v.gorunus_dosyasi)
    if v.script.get("marka"):
        ek.append(O.ROOT / "markalar" / str(v.script["marka"]) / "marka.json")
    for p in ek:
        if p.exists():
            _ozet_ekle(h, p)
    if v.pub.exists():
        for p in _dosyalar(v.pub):
            _ozet_ekle(h, p)
    h.update(json.dumps(tanim_json(v), sort_keys=True).encode())
    h.update(json.dumps(_girdi(props), sort_keys=True, ensure_ascii=False).encode())
    return f"{fmt}-{h.hexdigest()[:12]}"


def _temizle(v, fmt: str, korunan: str):
    d = ONBELLEK / v.id
    kumeler = sorted((p for p in d.iterdir() if p.is_dir() and p.name.rsplit("-", 1)[0] == fmt), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in kumeler[TUT:]:
        if p.name != korunan:
            shutil.rmtree(p, ignore_errors=True)


def plaka_yolu(v, kume: str, kesim: str, taraf: str, f: int) -> Path:
    return ONBELLEK / v.id / kume / kesim / taraf / f"p{f:05d}.png"


def _ciz(v, fmt: str, isler: list[tuple[str, str, list[int]]], props: dict | None, hedef_kok: Path, sira="asc") -> float:
    """Plaka işleri [(kesim, taraf, kareler)] → hedef_kok/<kesim>/<taraf>/pNNNNN.png. Tek paket, tek tarayıcı (pipeline/kareler.mjs)."""
    import st
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="st_gecis_") as tmp:
        jobs = [{"comp": v.comp_for(fmt), "out": Path(tmp) / k / t, "frames": sorted(fr, reverse=sira == "desc"),
                 "props": {**_girdi(props), "gecisPlakasi": {"kesim": k, "taraf": t}}, **({"gl": v.gl} if v.gl else {})} for k, t, fr in isler]
        sonuc = st.render_jobs(jobs)
        for (k, t, fr), files in zip(isler, sonuc):
            d = hedef_kok / k / t
            d.mkdir(parents=True, exist_ok=True)
            for f, p in files.items():
                shutil.move(str(p), d / f"p{f:05d}.png")
    return time.time() - t0


def hazirla(v, frames, fmt: str, props: dict | None = None) -> dict | None:
    """render_frames için: istenen karelerden pencereye düşenlerin iki tarafının plakası (önbellekte yoksa çizilir) → props + gecisKume.
    Kişisel filmde kişi verisi plaka önbelleğine yazılmaz: kesimli kişisel film desteklenmez (durur)."""
    esitle(v)
    istek = pencere_kareleri(v, frames)
    kume = parmak_izi(v, fmt, props)
    if "kisi" in (props or {}):
        import kisisel
        if istek and props["kisi"] != kisisel.ornek_kisi(v):
            raise SystemExit("Kişisel filmde gölgelendirici kesimi (<Kesim>) yok: kişi verisi geçiş plakası önbelleğine yazılmaz. "
                             "Geçişi kişi verisi olmayan sahneler arasında <GlGecis> ile doğrudan görüntülerle kur.")
    if istek:
        d = ONBELLEK / v.id / kume
        eksik = [(k, t, [f for f in fr if not plaka_yolu(v, kume, k, t, f).exists()]) for k, fr in istek.items() for t in ("a", "b")]
        eksik = [(k, t, fr) for k, t, fr in eksik if fr]
        if eksik:
            n = sum(len(fr) for *_, fr in eksik)
            print(f"→ geçiş plakaları: {n} kare çizilecek [{fmt} · küme {kume}] " + ", ".join(f"{k}/{t} {len(fr)}" for k, t, fr in eksik), flush=True)
            d.mkdir(parents=True, exist_ok=True)
            (d / "bilgi.json").write_text(json.dumps({"video": v.id, "format": fmt, "olusturma": time.strftime("%Y-%m-%d %H:%M"), "gl": v.gl,
                                                       "kesimler": tanim_json(v), "girdi": sorted(_girdi(props))}, ensure_ascii=False, indent=1) + "\n")
            sure = _ciz(v, fmt, eksik, props, d)
            print(f"   geçiş plakaları {n} kare {sure:.1f} sn", flush=True)
        _temizle(v, fmt, kume)
    if not any(k in (props or {}) for k in ("gorunus",)):
        _varsayilan_yaz(v, fmt, kume)
    return {**(props or {}), "gecisKume": kume}


def cizim_girdisi(v, fmt: str, props: dict | None = None, kalite: str = "taslak") -> dict:
    """Çizimdeki girdinin aynısı (parmak izi için): karma filmde motor plakalarının kümeleri de girdidir (plaka.hazirla ekler)."""
    import plaka
    p = dict(props or {})
    if plaka.var_mi(v):
        p["plaka"] = {S["ad"]: plaka.kume(v, S, fmt, kalite)[0] for S in plaka.sahneler(v) if not S["hata"]}
    return p


def yeniden_ciz(v, fmt: str, frames, props: dict | None = None) -> list[str]:
    """Deterministiklik: önbellekteki plakalardan pencereye düşenler ayrı bir çizimde TERS sırayla yeniden çizilir, bayt bayt karşılaştırılır."""
    kume = parmak_izi(v, fmt, props)
    istek = {k: [f for f in fr if plaka_yolu(v, kume, k, "a", f).exists() and plaka_yolu(v, kume, k, "b", f).exists()]
             for k, fr in pencere_kareleri(v, frames).items()}
    istek = {k: fr for k, fr in istek.items() if fr}
    if not istek:
        return [f"⏸ [{fmt}] pencereye düşen önbellekli geçiş plakası yok"]
    satir = []
    with tempfile.TemporaryDirectory(prefix="st_gecis_det_") as tmp:
        _ciz(v, fmt, [(k, t, fr) for k, fr in istek.items() for t in ("b", "a")], props, Path(tmp), "desc")
        for k, fr in istek.items():
            fark = [f"{t}{f}" for f in fr for t in ("a", "b")
                    if (Path(tmp) / k / t / f"p{f:05d}.png").read_bytes() != plaka_yolu(v, kume, k, t, f).read_bytes()]
            satir.append(f"{'✅' if not fark else '❌'} [{fmt}] kesim {k}: {2 * len(fr) - len(fark)}/{2 * len(fr)} geçiş plakası ayrı çizimde ters sırayla "
                         f"bayt bayt aynı" + (f" · farklı: {', '.join(fark[:8])}" if fark else ""))
    return satir


# ---------------------------------------------------------------- denetim ve durum
def kod_denetimi(v) -> list[tuple[str, str]]:
    """./st tip: her kesim için kodda <Kesim ad="…"> var mı; kesim kullanan kod lib/gecis'i içe aktarıyor mu (GL bayraksız: WebGL SwiftShader)."""
    if not var_mi(v) or v.motor == "hyperframes":
        return []
    import re
    kod = "\n".join(p.read_text() for p in sorted(v.kod_dizini.rglob("*.ts*"))) if v.kod_dizini.exists() else ""
    out = []
    for ad in tanim_json(v):
        if not re.search(rf"""<Kesim\b[^>]*?\bad=\{{?\s*['"]{re.escape(ad)}['"]""", kod, re.S):
            out.append(("❌", f"kesim {ad}: kodda <Kesim ad=\"{ad}\" …> yok (script.json → shot.gecis; src/lib/gecis)"))
    if not out:
        out.append(("✅", f"{len(tanim_json(v))} kesim kodda <Kesim> ile işaretli"))
    if not v.gecisli:
        out.append(("❌", "kod src/lib/gecis'i içe aktarmıyor (<Kesim>, <GlGecis>)"))
    else:
        out.append(("✅", f"gölgelendirici başsız Chrome'un WebGL'inde (SwiftShader){'; 3B katman: swangle' if v.gl else ', DOM yazılımla (bayraksız)'}"))
    return out


def durum(v):
    esitle(v)
    print(f"■ {v.id} · gölgelendirici geçişleri (gl-transitions {SURUM}) · {v.fps} fps · "
          f"{'GL swangle (3B katman)' if v.gl else 'GL bayraksız (başsız Chrome: WebGL SwiftShader, DOM yazılımla)'}")
    for d_, m in sorunlar(v):
        print(f"  {d_} {m}")
    T = tanim_json(v)
    for ad, k in T.items():
        print(f"  {ad}: {k['vurus']} → {k['sonraki']} · {k['gl']} · {k['kare']} kare · kesim f{k['kesim']} ({O.tc(k['kesim'] / v.fps)}) · "
              f"pencere f{k['bas']}–f{k['son'] - 1}" + (f" · {json.dumps(k['param'], ensure_ascii=False)}" if k["param"] else ""))
    G = O.jload(v.pub / "gecis.json") if (v.pub / "gecis.json").exists() else {}
    for fmt in v.formatlar:
        kume = parmak_izi(v, fmt, cizim_girdisi(v, fmt, _veri_props(v)))   # karma filmde motor plakalarının kümeleri de girdidir
        n = sum(1 for ad, fr in pencere_kareleri(v).items() for f in fr for t in ("a", "b") if plaka_yolu(v, kume, ad, t, f).exists())
        top = 2 * sum(len(fr) for fr in pencere_kareleri(v).values())
        print(f"  [{fmt}] güncel küme {kume}: {n}/{top} plaka" + (" ✅" if n == top else "") +
              (f" · varsayılan {G.get('kume', {}).get(fmt)}" if G.get("kume", {}).get(fmt) not in (None, kume) else ""))


def _veri_props(v):
    import st
    return st._veri_props(v)


# ---------------------------------------------------------------- önizleme (Kütüphane → Geçişler)
def onizle(adlar: list[str] | None, yeniden=False) -> list[str]:
    """Her geçiş için iki nötr kartla (gri tonlar, görünüşten bağımsız) 1,5 sn'lik küçük klip + afiş → katalog/onizleme/gecis/<ad>.mp4, .jpg."""
    import subprocess
    L = kutuphane()
    adlar = sorted(L) if adlar is None else adlar
    yok = [a for a in adlar if a not in L]
    if yok:
        raise SystemExit(f"Geçiş yok: {', '.join(yok)} (./st gecis liste)")
    ONIZLEME.mkdir(parents=True, exist_ok=True)
    is_ = [a for a in adlar if yeniden or not (ONIZLEME / f"{a}.mp4").exists() or not (ONIZLEME / f"{a}.jpg").exists()]
    if not is_:
        print(f"önizlemeler hazır ({len(adlar)}): {ONIZLEME.relative_to(O.ROOT)}/")
        return adlar
    print(f"→ {len(is_)} geçiş önizlemesi çiziliyor (yazılım GL; {O.UC_GL})", flush=True)
    r = subprocess.run(["node", "pipeline/gecis_onizle.mjs", json.dumps({"adlar": is_, "out": str(ONIZLEME), "gl": O.UC_GL})], cwd=O.ROOT,
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"önizleme başarısız:\n{(r.stdout + r.stderr)[-3000:]}")
    oz = json.loads(r.stdout.strip().splitlines()[-1])
    for a in oz["bitti"]:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ONIZLEME / f"{a}.mp4"), "-vf", "select=eq(n\\,22)", "-frames:v", "1", "-q:v", "4",
                        str(ONIZLEME / f"{a}.jpg")], check=True)
    print(f"✅ {len(oz['bitti'])} önizleme {oz['seconds']:.0f} sn · {ONIZLEME.relative_to(O.ROOT)}/" + (f" · hata: {oz['hata']}" if oz.get("hata") else ""))
    if oz.get("hata"):
        raise SystemExit(1)
    return adlar
