"""3B model kütüphanesi (./st 3b): threejsassets.com'un ücretsiz GLB modelleri → yerel kütüphane → film.

Kaynak ve lisans (threejsassets.com/license, v1, 2026-07-08): ücretsiz modeller video dahil ticari işte kullanılır, değiştirilir, atıf
gerekmez. Dosyanın kendisi paylaşılmaz, aynalanmaz, toplu indirilmez: kütüphane yalnız bu bilgisayarındır, modeller film başına,
gerektiği kadar indirilir; `./st paket` modelleri taşımaz (karşı taraf kendi ücretsiz hesabıyla indirir).

Akış
  ara      herkese açık katalog (anahtarsız API, /api/v1/catalog; 24 saat önbellek out/_3b/katalog.json) → ad, açıklama, kategori, paket
  al       indirme üç yoldan biriyle, hepsi kullanıcının kendi hesabıyla:
             --url   threejsassets MCP bağlantısının verdiği kısa ömürlü doğrudan bağlantı (Claude: get_asset_download_link)
             TJA_API_KEY (studio/.env; API anahtarı yalnız satın alma yapmış hesaplarda açılır)
             yoksa: sayfa bağlantısı verilir, kullanıcı tarayıcıda indirir → ekle
  ekle     tarayıcıyla indirilen .glb'yi kütüphaneye alır (panel: Kütüphane → 3B modeller'e bırak)
  incele   GLB'nin içi: uzantılar (Draco, KTX2, Meshopt), boyut ve taban (metre), ağ, malzeme, köşe rengi, animasyonlar
  kullan   modeli filme kopyalar (public/<id>/varliklar/3b/<slug>.glb) ve varliklar.md'ye lisanslı varlık olarak yazar
  onizle   modeli stüdyonun kendi 3B katmanında (Remotion, swangle) çizer → kutuphane/3b/threejsassets/<slug>.png

Çözücüler (Draco, KTX2/Basis) three'nin kendi kopyasından yerelde sunulur: Remotion public/uc/, HyperFrames assets/lib/three/addons/libs/.
"""
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import ortak as O

KAYNAK = "threejsassets"
SITE = "https://threejsassets.com"
API = SITE + "/api/v1"
KUTUPHANE = O.ROOT / "kutuphane" / "3b" / KAYNAK
KATALOG = O.ROOT / "out" / "_3b" / "katalog.json"
KATALOG_OMRU = 24 * 3600
LISANS = ("threejsassets Free Commercial License v1: videoda ticari kullanım serbest, atıf gerekmez; "
          "model dosyası paylaşılmaz, yeniden dağıtılmaz")
UA = {"User-Agent": "studyo-3b/1.0 (code-rendered video studio; personal use)"}  # HTTP başlığı latin-1: Türkçe harf yok
EN_BUYUK = 60 * 1024 * 1024  # ücretsiz katalogda en büyük dosya ~3,8 MB
THREE_LIBS = O.ROOT / "node_modules" / "three" / "examples" / "jsm" / "libs"
COZUCU = {"draco": ["draco_wasm_wrapper.js", "draco_decoder.wasm"], "basis": ["basis_transcoder.js", "basis_transcoder.wasm"]}


# ---------------------------------------------------------------- ağ
def _anahtar() -> str | None:
    """TJA_API_KEY: ortamdan ya da studio/.env'den. Değer hiçbir yere yazdırılmaz."""
    if os.environ.get("TJA_API_KEY"):
        return os.environ["TJA_API_KEY"]
    p = O.ROOT / ".env"
    if p.exists():
        for ln in p.read_text().splitlines():
            m = re.match(r"\s*TJA_API_KEY\s*=\s*(.*)", ln)
            if m and m.group(1).strip().strip('"').strip("'"):
                return m.group(1).strip().strip('"').strip("'")
    return None


def _istek(url: str, anahtar: str | None = None, deneme=4) -> bytes:
    h = dict(UA)
    if anahtar:
        h["Authorization"] = f"Bearer {anahtar}"
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
                veri = r.read(EN_BUYUK + 1)
                if len(veri) > EN_BUYUK:
                    raise SystemExit(f"dosya beklenenden büyük (> {EN_BUYUK // 2**20} MB): {url}")
                return veri
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < deneme - 1:  # hız sınırı: dakikada 120 (katalog); indirme daha sıkı
                time.sleep(float(e.headers.get("Retry-After") or e.headers.get("x-ratelimit-reset") or 10))
                continue
            try:
                hata = json.loads(e.read()).get("error", {})
            except Exception:
                hata = {}
            raise SystemExit(f"threejsassets {e.code} {hata.get('code', '')}: {hata.get('message', e.reason)}"
                             + (f" (istek {hata['request_id']})" if hata.get("request_id") else ""))
        except urllib.error.URLError as e:
            if i < deneme - 1:
                time.sleep(2 * (i + 1))
                continue
            raise SystemExit(f"threejsassets'e ulaşılamadı: {e.reason}")
    raise SystemExit("threejsassets: hız sınırı aşıldı, biraz sonra yeniden dene")


# ---------------------------------------------------------------- katalog (herkese açık, anahtarsız)
ALANLAR = ("slug", "name", "description", "tier", "category", "pack_slug", "triangles", "file_size_bytes", "version", "poster_url", "url")


def katalog(yenile=False) -> list[dict]:
    """Bütün yayımlanmış modellerin bilgisi (dosya değil): 24 saatte bir yenilenir."""
    if not yenile and KATALOG.exists() and time.time() - KATALOG.stat().st_mtime < KATALOG_OMRU:
        return O.jload(KATALOG)["modeller"]
    try:
        kayit, ofset = [], 0
        while True:
            d = json.loads(_istek(f"{API}/catalog/assets?limit=100&offset={ofset}"))
            kayit += [{k: m.get(k) for k in ALANLAR} for m in d["data"]]
            if not d["pagination"]["has_more"]:
                break
            ofset += 100
    except SystemExit:
        if KATALOG.exists():  # çevrimdışı: eski katalog yeter
            print("   (katalog yenilenemedi; önbellekteki kullanılıyor)")
            return O.jload(KATALOG)["modeller"]
        raise
    KATALOG.parent.mkdir(parents=True, exist_ok=True)
    KATALOG.write_text(json.dumps({"kaynak": f"{API}/catalog/assets", "tarih": dt.datetime.now().isoformat(timespec="seconds"),
                                   "modeller": kayit}, ensure_ascii=False))
    return kayit


def kayit(slug: str) -> dict:
    for m in katalog():
        if m["slug"] == slug:
            return m
    try:  # katalog önbelleğinden yeni bir model
        return {k: v for k, v in json.loads(_istek(f"{API}/catalog/assets/{urllib.parse.quote(slug)}"))["data"].items() if k in ALANLAR}
    except SystemExit:
        raise SystemExit(f"katalogda böyle bir model yok: {slug} (./st 3b ara <sözcük>)")


def ara(sorgu: str = "", kategori: str | None = None, hepsi=False, n=20) -> list[dict]:
    """Ad, kısa ad, açıklama, kategori ve paket adında arar; ad eşleşmesi açıklamadan ağır basar. Varsayılan yalnız ücretsizler."""
    sozler = [s for s in re.split(r"[\s,]+", sorgu.lower()) if s]
    sonuc = []
    for m in katalog():
        if not hepsi and m.get("tier") != "free":
            continue
        if kategori and m.get("category") != kategori:
            continue
        ad, aciklama = f"{m['name']} {m['slug']}".lower(), (m.get("description") or "").lower()
        diger = f"{m.get('category') or ''} {m.get('pack_slug') or ''}".lower()
        puan = 0.0
        for s in sozler:
            k = rf"\b{re.escape(s)}(?:e?s)?\b"  # tam sözcük (çoğul eki dahil): "tent" "tenth"e uymaz
            p = 3 * bool(re.search(k, ad)) + 1 * bool(re.search(k, aciklama)) + 1 * (s in diger)
            if not p:
                break
            puan += p
        else:
            sonuc.append((puan, m))
    sonuc.sort(key=lambda x: (-x[0], x[1]["triangles"] or 0))
    return [m for _, m in sonuc[:n]]


# ---------------------------------------------------------------- kütüphane
def glb_yolu(slug: str) -> Path:
    return KUTUPHANE / f"{slug}.glb"


def bilgi(slug: str) -> dict | None:
    p = KUTUPHANE / f"{slug}.json"
    return O.jload(p) if p.exists() else None


def kutuphane() -> list[dict]:
    """İndirilmiş modeller + hangi filmlerde kullanıldıkları."""
    if not KUTUPHANE.exists():
        return []
    kullanim = {}
    for f in (O.ROOT / "public").glob("*/varliklar/3b/*.glb"):
        kullanim.setdefault(f.stem, []).append(f.parts[-4])
    out = []
    for p in sorted(KUTUPHANE.glob("*.json")):
        b = O.jload(p)
        if glb_yolu(b["slug"]).exists():
            b["filmler"] = sorted(kullanim.get(b["slug"], []))
            b["onizleme"] = (KUTUPHANE / f"{b['slug']}.png").exists()
            out.append(b)
    return out


def _glb_dogrula(veri: bytes, kaynak: str):
    if len(veri) < 20 or veri[:4] != b"glTF":
        bas = veri[:200].decode("utf-8", "replace").strip()
        ipucu = " (oturum açma sayfası döndü: bağlantının süresi dolmuş olabilir)" if "<html" in bas.lower() else ""
        raise SystemExit(f"GLB değil: {kaynak}{ipucu}")
    surum, uzunluk = struct.unpack_from("<II", veri, 4)
    if surum != 2 or uzunluk != len(veri):
        raise SystemExit(f"GLB bozuk ya da yarım: {kaynak} (sürüm {surum}, başlık {uzunluk} bayt, dosya {len(veri)} bayt)")


def _kaydet(slug: str, m: dict, veri: bytes, yol: str) -> dict:
    _glb_dogrula(veri, slug)
    KUTUPHANE.mkdir(parents=True, exist_ok=True)
    gecici = glb_yolu(slug).with_suffix(".glb.yarim")
    gecici.write_bytes(veri)
    gecici.replace(glb_yolu(slug))
    b = {**m, "kaynak": KAYNAK, "lisans": LISANS, "indirme": yol, "tarih": dt.date.today().isoformat(),
         "sha256": hashlib.sha256(veri).hexdigest(), "bayt": len(veri), "glb": glb_bilgi(glb_yolu(slug))}
    (KUTUPHANE / f"{slug}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n")
    return b


def al(slug: str, url: str | None = None) -> dict:
    """Kütüphaneye indirir (zaten varsa dokunmaz; yenilemek için önce sil). Yol: --url (MCP), TJA_API_KEY, yoksa tarayıcı tarifi."""
    m = kayit(slug)
    if glb_yolu(slug).exists() and not url:
        print(f"   {slug} zaten kütüphanede")
        return bilgi(slug) or {}
    anahtar = _anahtar()
    if url:
        u = urllib.parse.urlparse(url)
        if u.scheme != "https":
            raise SystemExit("--url https olmalı (threejsassets MCP bağlantısının verdiği doğrudan bağlantı)")
        if not (u.hostname or "").endswith("threejsassets.com"):
            print(f"   not: bağlantı {u.hostname} adresinden (threejsassets.com değil); dosya GLB olarak doğrulanacak")
        return _kaydet(slug, m, _istek(url), "mcp")
    if anahtar:
        return _kaydet(slug, m, _istek(f"{API}/assets/{urllib.parse.quote(slug)}/download", anahtar), "api")
    ucret = "" if m.get("tier") == "free" else " Bu model ücretli (paket gerekir): ücretsiz bir benzerini ara (./st 3b ara)."
    raise SystemExit(
        f"{slug} henüz kütüphanede yok ve indirme yolu açık değil.{ucret}\n"
        f"İndirmek kullanıcının kendi hesabıyla olur (ücretsiz hesap, e-postaya giriş bağlantısı):\n"
        f"  1) Tarayıcıda: {m['url']} → Download → sonra ./st 3b ekle ~/Downloads/{slug}.glb (ya da panel: Kütüphane → 3B modeller'e bırak)\n"
        f"  2) Claude'un threejsassets bağlantısı (MCP, .mcp.json) açıksa: get_asset_download_link → ./st 3b al {slug} --url <bağlantı>\n"
        f"  3) API anahtarı (yalnız satın alma yapmış hesaplarda): studio/.env → TJA_API_KEY=…")


def ekle(dosya: str, slug: str | None = None) -> dict:
    """Tarayıcıyla indirilmiş .glb → kütüphane. Kısa ad dosya adından ("ammo-crate (1).glb" → ammo-crate) ya da --slug."""
    p = Path(dosya).expanduser()
    if not p.exists():
        raise SystemExit(f"dosya yok: {p}")
    if p.suffix.lower() != ".glb":
        raise SystemExit(f"yalnız .glb alınır: {p.name}")
    return _kaydet(*_tani(p, slug), p.read_bytes(), "tarayici")


def _tani(p: Path, slug: str | None) -> tuple[str, dict]:
    """Dosya adından katalog kaydı: "ammo-crate (1).glb", "Ammo Crate.glb", "ammo_crate.glb" → ammo-crate."""
    if slug:
        return slug, kayit(slug)
    kok = re.sub(r"\s*\(\d+\)$", "", p.stem).strip()
    aday = re.sub(r"[^a-z0-9]+", "-", kok.lower()).strip("-")
    for m in katalog():
        if m["slug"] == aday or m["name"].lower() == kok.lower():
            return m["slug"], m
    raise SystemExit(f"{p.name}: katalogda karşılığı bulunamadı. Dosyayı sitedeki adıyla bırak ya da kısa adını ver: "
                     f"./st 3b ekle {p} --slug <slug> (./st 3b ara {kok})")


# ---------------------------------------------------------------- GLB'nin içi (çözmeden: JSON bölümü + erişimci sınırları)
def _carp(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _matris(n: dict):
    if "matrix" in n:
        m = n["matrix"]  # sütun öncelikli
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    x, y, z, w = n.get("rotation", [0, 0, 0, 1])
    sx, sy, sz = n.get("scale", [1, 1, 1])
    tx, ty, tz = n.get("translation", [0, 0, 0])
    R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[R[0][0] * sx, R[0][1] * sy, R[0][2] * sz, tx], [R[1][0] * sx, R[1][1] * sy, R[1][2] * sz, ty],
            [R[2][0] * sx, R[2][1] * sy, R[2][2] * sz, tz], [0, 0, 0, 1]]


def glb_bilgi(yol: Path) -> dict:
    """Uzantılar, dünya koordinatında sınır kutusu (metre; +Y yukarı), üçgen, ağ, malzeme, köşe rengi, doku, animasyon, iskelet."""
    veri = Path(yol).read_bytes()
    _glb_dogrula(veri, str(yol))
    uz = struct.unpack_from("<I", veri, 12)[0]
    G = json.loads(veri[20:20 + uz])
    acc = G.get("accessors", [])
    ucgen, renkli, ag_say = 0, False, 0
    lo, hi = [math.inf] * 3, [-math.inf] * 3

    def gez(i, M):
        nonlocal ucgen, renkli, ag_say
        n = G["nodes"][i]
        W = _carp(M, _matris(n))
        if "mesh" in n:
            ag_say += 1
            for p in G["meshes"][n["mesh"]]["primitives"]:
                a = p.get("attributes", {})
                renkli = renkli or "COLOR_0" in a
                if p.get("mode", 4) == 4:
                    ucgen += (acc[p["indices"]]["count"] if "indices" in p else acc[a["POSITION"]]["count"]) // 3
                P = acc[a["POSITION"]] if "POSITION" in a else {}
                if "min" in P and "max" in P:
                    for k in range(8):
                        c = [(P["max"] if k >> j & 1 else P["min"])[j] for j in range(3)]
                        w = [sum(W[r][j] * c[j] for j in range(3)) + W[r][3] for r in range(3)]
                        for j in range(3):
                            lo[j], hi[j] = min(lo[j], w[j]), max(hi[j], w[j])
        for c in n.get("children", []):
            gez(c, W)

    birim = [[float(i == j) for j in range(4)] for i in range(4)]
    for i in G.get("scenes", [{}])[G.get("scene", 0)].get("nodes", range(len(G.get("nodes", [])))):
        gez(i, birim)
    anim = []
    for a in G.get("animations", []):
        sure = max((acc[s["input"]].get("max", [0])[0] for s in a.get("samplers", [])), default=0)
        anim.append({"ad": a.get("name", f"#{len(anim)}"), "sure": round(sure, 3)})
    kutu = None
    if lo[0] != math.inf:
        kutu = {"min": [round(v, 3) for v in lo], "max": [round(v, 3) for v in hi], "boyut": [round(hi[j] - lo[j], 3) for j in range(3)],
                "merkez": [round((hi[j] + lo[j]) / 2, 3) for j in range(3)]}
    return {"uzantilar": G.get("extensionsUsed", []), "zorunlu": G.get("extensionsRequired", []), "ucgen": ucgen, "ag": ag_say,
            "dugum": len(G.get("nodes", [])), "malzeme": [m.get("name", "") for m in G.get("materials", [])], "kose_rengi": renkli,
            "doku": len(G.get("images", [])), "iskelet": len(G.get("skins", [])), "animasyon": anim, "kutu": kutu}


def cozucu_gerekir(b: dict) -> list[str]:
    u = set(b.get("uzantilar", []))
    return ([] if "KHR_draco_mesh_compression" not in u else ["Draco"]) + ([] if "KHR_texture_basisu" not in u else ["KTX2"]) \
        + ([] if not u & {"EXT_meshopt_compression", "KHR_meshopt_compression"} else ["Meshopt"])


# ---------------------------------------------------------------- filme alma
def cozucu_hazirla(hedef: Path | None = None) -> Path:
    """Draco ve KTX2/Basis çözücülerini three'nin kendi kopyasından (sürüm sabit) yerel klasöre koyar. CDN yok."""
    hedef = hedef or O.ROOT / "public" / "uc"
    for ad, dosyalar in COZUCU.items():
        kaynak = THREE_LIBS / ("draco/gltf" if ad == "draco" else "basis")
        for f in dosyalar:
            k, h = kaynak / f, hedef / ad / f
            if not h.exists() or h.stat().st_size != k.stat().st_size:
                h.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(k, h)
    return hedef


def varlik_satiri(b: dict) -> str:
    g = b.get("glb") or {}
    boy = "×".join(f"{x:g}" for x in (g.get("kutu") or {}).get("boyut", [])) or "?"
    return (f"| {b['name']} (3B model) | varliklar/3b/{b['slug']}.glb | 3b model | {b['url']} · {LISANS} · "
            f"{g.get('ucgen', b.get('triangles'))} üçgen · {boy} m · indirildi {b.get('tarih', '')} | ✅ lisanslı (threejsassets ücretsiz) |")


def kullan(vid: str, sluglar: list[str]) -> list[dict]:
    v = O.load(vid)
    eksik = [s for s in sluglar if not glb_yolu(s).exists()]
    if eksik:
        raise SystemExit(f"kütüphanede yok: {', '.join(eksik)} → önce ./st 3b al <slug> (ya da tarayıcıdan indir → ./st 3b ekle)")
    d = v.pub / "varliklar" / "3b"
    d.mkdir(parents=True, exist_ok=True)
    md = v.dir / "varliklar.md"
    if not md.exists():  # profil varlık listesi istemese de lisanslı model kaynağıyla yazılır (kural 2)
        md.write_text((O.ROOT / "sablon" / "video" / "varliklar.md").read_text()
                      .replace("{{BASLIK}}", v.script.get("title", v.id)).replace("{{ID}}", v.id))
    metin = md.read_text()
    out = []
    for s in sluglar:
        shutil.copy2(glb_yolu(s), d / f"{s}.glb")
        b = bilgi(s) or {}
        if f"varliklar/3b/{s}.glb" not in metin:
            satir = varlik_satiri(b)
            metin = (re.sub(r"^\| \[ad\].*$", satir, metin, count=1, flags=re.M) if re.search(r"^\| \[ad\]", metin, re.M)
                     else metin.rstrip() + "\n" + satir + "\n")
        out.append(b)
    md.write_text(metin)
    cozucu_hazirla()
    return out


def kullanim_ornegi(v, b: dict) -> str:
    s, g = b["slug"], b.get("glb") or {}
    anim = g.get("animasyon") or []
    klip = "hepsi" if len(anim) > 1 else (anim[0]["ad"] if anim else "")  # dışa aktarıcılar çoğu zaman her nesneye ayrı klip yazar
    if v.motor == "hyperframes":
        a = _js_ad(s)
        return (f'const {a} = await modelYukle("varliklar/3b/{s}.glb", {{renderer}});   // hf/{v.id}/index.html, zamanaBagla\'dan önce\n'
                f'   const {a}Kok = modelHazirla({a}, {{yukseklik: 1, golge: true}}); sahne.add({a}Kok);'
                + (f'\n   const {a}An = animasyonKur({a}Kok, {a}.animations);   // çizimde: animasyonSur({a}An, {{klip: "{klip}", t}})' if anim else ""))
    return (f"<Model src={{staticFile('{v.id}/varliklar/3b/{s}.glb')}} yukseklik={{1}} golge"
            + (f' animasyon="{klip}" t={{t}}' if anim else "") + " />   // src/" + v.script.get("kod", v.id) + "/ (lib/uc)")


def _js_ad(slug: str) -> str:
    p = re.split(r"[^a-zA-Z0-9]+", slug)
    return (p[0] + "".join(x[:1].upper() + x[1:] for x in p[1:])) if p and p[0] else "model"
