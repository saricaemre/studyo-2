"""Yapım filmi ("nasıl yapıldı", oturum 4e): 15 saniyelik bir film, filmin yapay zekâ değil insan kararıyla yapıldığının kanıtı.

./st yapim <id> [--format F] [--cikti <dosya.mp4|klasör>] [--plan] — malzeme yalnız filmin kendi kayıtlarından gelir (uydurma yok, kural 2):
  · görünüş / yol denemesinin kanca kareleri ve seçilen seçenek (inceleme/gorunus/, gorunus.json), Kapı 1 onayı (kapilar.json)
  · kılavuz kipinde çizilmiş kareler (Remotion girdi `yapim`, HyperFrames kılavuz varyantı: yerleşim kutuları, güvenli alan, yazı puntosu)
    ve kutuların veri pikselleri (hareket yolu, en küçük yazı); Blender'da kil, tel kafes ve kamera yolu geçişleri (blender/yapim/)
  · inceleme turlarında aynı karenin ilk ve son hâli (inceleme/vN/kareler, olcum.json, elestiri.md)
  · yapay zekâ varlıklarının kaynağı (uretim.json: model, araç, kredi; asıl dosya)
  · altı kapının durumu (insan onayının tarihi ya da kanıt) ve teslim edilen film
Her bölüm ancak kaydı varsa girer; yazılan her olgu yapim.json → kanitlar'da kaynak dosyasıyla durur. Kişisel etki filminde yalnız şablonun
TEST örneği (videos/<id>/toplu/ okunmaz). Ses kredisiz: kod müziği (pipeline/muzik.py) + kapanışta filmin kendi miksi, −14 LUFS.
Çıktı varsayılanı ../cikti/<id>_yapim.mp4; çalışma klasörü out/_yapim/<id>/ (malzeme JPEG + sha256, kurgu.json, yapim.json, olcum.md).
Görüntüyü Remotion'un Yapim-<format> kompozisyonu çizer (src/yapim/Yapim.tsx); kare deterministik (./st deterministik <id> --yapim).
"""
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image

import ortak as O

FPS = 30
SURE = 15.0
NKARE = int(SURE * FPS)
ADIM = 2                       # klip bölümlerinde her malzeme karesi iki yapım karesi sürer (15 kare/sn, kılavuzun "adım adım" görünüşü)
YAZI_ESIK = 64                 # okunan yazı ≥ 64 px (1080 kısa kenarda; zanaat §4)
KONTRAST_ESIK = 4.5
ONB = O.ROOT / "out" / "_yapim"
CIKTI = O.KANAL / "cikti"
JPEG = 90
TUR_AD = ["yazi", "gorsel", "video", "cizim", "uc"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
SAYI = {1: "biri", 2: "ikisi", 3: "üçü", 4: "dördü", 5: "beşi", 6: "altısı"}
KAPI_KISA = {1: "Plan", 2: "Senaryo", 3: "Kareler", 4: "Kurgu", 5: "Rötuş", 6: "Teslim"}   # panelin yolundaki adlar
# bölümlerin sırası ve süresi (sn); eksik bölümün süresi önce kılavuza/Blender'a, sonra kapanışa gider (toplam her zaman 15 sn)
SURELER = {"acilis": 1.6, "yollar": 2.2, "kilavuz": 3.4, "blender": 4.0, "elestiri": 2.2, "uretim": 2.2, "kapilar": 1.8, "kapanis": 1.6}
ACIKLAMA = {"acilis": "Başlık", "yollar": "Üç yol ya da görünüş ve seçilen", "kilavuz": "Kılavuz: yerleşim kutuları, güvenli alan, yazı puntosu",
            "blender": "Kil, tel kafes, kamera yolu, son hâl", "elestiri": "İnceleme turunda önce ve sonra", "uretim": "Yapay zekâ varlığının kaynağı",
            "kapilar": "Altı kapı ve insan onayları", "kapanis": "Film"}


def dizin(v) -> Path:
    return ONB / v.id


def _bag():
    """public/_yapim → out/_yapim (Remotion staticFile; bağlantı paketlemede kopyalanmaz). Yoksa kurulur."""
    ONB.mkdir(parents=True, exist_ok=True)
    b = O.ROOT / "public" / "_yapim"
    hedef = os.path.relpath(ONB, b.parent)
    if b.is_symlink() and os.readlink(b) != hedef:
        b.unlink()
    if not b.is_symlink():
        if b.exists():
            raise SystemExit(f"{b} bir klasör; yapım malzemesi out/_yapim'de durur, bu bir bağlantı olmalı")
        b.symlink_to(hedef)


def _tarih(s: str | None) -> str | None:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return f"{int(m.group(3))} {AYLAR[int(m.group(2)) - 1]}" if m else None


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _rel(p: Path) -> str:
    p = Path(p)
    return str(p.relative_to(O.ROOT)) if p.is_relative_to(O.ROOT) else str(p)


def baslik(v) -> str:
    t = v.script.get("title") or v.script.get("baslik")
    if not t and (v.dir / "brief.md").exists():
        m = re.search(r"^#\s+(.+)$", (v.dir / "brief.md").read_text(), re.M)
        t = m.group(1) if m else None
    t = re.sub(r"\s+", " ", (t or v.id.replace("_", " "))).strip()
    if len(t) > 48:   # uzun başlık sözcük sınırında kısalır (yazı ≥ 64 px, en çok iki satır)
        t = t[:47].rsplit(" ", 1)[0].rstrip(":,;·-") + "…"
    return re.sub(r"\s+[·—:]\s+", "\n", t)   # ayraçta satır kırılır (ayraç satır sonunda asılı kalmasın)


# ---------------------------------------------------------------- kayıtlar (çizim yok: plan ve panel önizlemesi)
def _gorunus(v, fmt) -> dict | None:
    if v.gorunus_modu != "video":
        return None
    G = v.gorunus_json() or {}
    S = G.get("secenekler") or {}
    gd = v.dir / "inceleme" / "gorunus"
    sec = []
    for k in sorted(S)[:3]:
        o = S[k] or {}
        kare = None
        for f in [fmt] + [x for x in v.formatlar if x != fmt]:
            ks = sorted((gd / f"{k}-{f}").glob("f*.png")) if (gd / f"{k}-{f}").exists() else []
            if ks:
                kare = ks[0]
                break
        yol = o.get("yol") if isinstance(o.get("yol"), dict) else None
        sec.append({"harf": k, "ad": (yol or {}).get("ad") or o.get("ad") or k.upper(), "kare": kare})
    if len(sec) < 2 or not all(s["kare"] for s in sec):
        return None
    return {"mod": "yol" if G.get("yol_modu") else "gorunus", "secenekler": sec, "secim": G.get("secim") if G.get("secim") in S else None,
            "kaynak": [_rel(v.gorunus_dosyasi), _rel(gd)]}


def _kapilar(v) -> list[dict]:
    import st
    try:
        res, g = st.gate_eval(v)
    except Exception:   # ölçülemeyen kapı "bekliyor" sayılır (uydurma yok)
        res, g = {n: (False, []) for n in st.GATES}, st.gates_load(v)
    out = []
    for n, (ad, insan) in st.GATES.items():
        onay = (g.get(str(n)) or {}).get("onay")
        ok = res.get(n, (False, []))[0]
        out.append({"n": n, "ad": KAPI_KISA.get(n, ad), "insan": insan, "onay": onay, "tarih": _tarih(onay),
                    "durum": ("insan" if insan and onay else "kanit" if ok and not insan else "bekliyor")})
    return out


def _turlar(v, fmt) -> list[dict]:
    import st
    root = v.dir / "inceleme"
    out = []
    for rd in sorted((p for p in root.glob("v*") if p.is_dir() and re.fullmatch(r"v\d+", p.name)), key=lambda p: int(p.name[1:])) if root.exists() else []:
        kd = rd / st.review_names(v, fmt)[1]
        om = rd / "olcum.json"
        carpi = sum(1 for r in O.jload(om) if r.get("durum") == "❌") if om.exists() else None
        out.append({"ad": rd.name, "n": int(rd.name[1:]), "kareler": kd if kd.exists() else None, "carpi": carpi,
                    "elestiri": (rd / "elestiri.md").exists(), "karar": st.elestiri_karari(rd) if (rd / "elestiri.md").exists() else None})
    return out


_CIFT: dict = {}   # panel her açılışta sorar: dosyaların zamanı değişmedikçe aynı sonuç


def _elestiri_cifti(v, fmt) -> dict | None:
    """İlk ve son inceleme turunda aynı kare numarasının hâli; en çok değişen kare (görüntü farkı) seçilir. Değişim yoksa None."""
    T = [t for t in _turlar(v, fmt) if t["kareler"]]
    if len(T) < 2:
        return None
    a, b = T[0], T[-1]
    ortak = sorted({p.name for p in a["kareler"].glob("f*.png")} & {p.name for p in b["kareler"].glob("f*.png")})
    anahtar = (v.id, fmt, a["ad"], b["ad"], tuple((n, (a["kareler"] / n).stat().st_mtime, (b["kareler"] / n).stat().st_mtime) for n in ortak))
    if anahtar not in _CIFT:
        _CIFT[anahtar] = _cift_sec(a, b, ortak)
    return _CIFT[anahtar]


def _cift_sec(a, b, ortak) -> dict | None:
    en, sec = 0.0, None
    for ad in ortak:
        x = np.asarray(Image.open(a["kareler"] / ad).convert("L").resize((90, 160)), dtype=np.float32)
        y = np.asarray(Image.open(b["kareler"] / ad).convert("L").resize((90, 160)), dtype=np.float32)
        d = float(np.abs(x - y).mean())
        if d > en:
            en, sec = d, ad
    if not sec or en < 1.5:
        return None
    return {"once": a["kareler"] / sec, "sonra": b["kareler"] / sec, "kare": int(sec[1:6]), "tur1": a, "tur2": b, "fark": round(en, 2),
            "kaynak": [_rel(a["kareler"] / sec), _rel(b["kareler"] / sec)]}


def _uretim(v) -> dict | None:
    import uretim
    if not uretim.var_mi(v):
        return None
    U = uretim.yukle(v)
    xs = [x for x in U.get("varliklar", []) if x.get("tur") in ("gorsel", "video") and (v.dir / x["dosya"]).exists()]
    if not xs:
        return None
    x = sorted(xs, key=lambda x: (x["tur"] != "gorsel", x.get("tarih", "")))[0]
    return {"ad": x["ad"], "tur": x["tur"], "model": x.get("model") or x.get("arac"), "arac": x.get("arac"), "kredi": x.get("kredi", 0),
            "istem": bool(x.get("istem")), "dosya": v.dir / x["dosya"], "toplam_kredi": sum(int(y.get("kredi", 0)) for y in U.get("varliklar", [])),
            "adet": len(U.get("varliklar", [])), "kaynak": [_rel(v.dir / "uretim" / "uretim.json")]}


def plan(v, fmt: str | None = None) -> dict:
    """Hangi bölümler girer (kaydı olanlar), süreleri ve panelin önizlemesi için var olan görseller. Çizim yapmaz."""
    fmt = fmt or v.formatlar[0]
    if fmt not in v.formatlar:
        raise SystemExit(f"{v.id} bu formatta yok: {fmt} (formatlar: {', '.join(v.formatlar)})")
    G = _gorunus(v, fmt)
    E = _elestiri_cifti(v, fmt)
    U = _uretim(v)
    var = {"acilis": True, "yollar": bool(G), "kilavuz": v.motor != "blender", "blender": v.motor == "blender", "elestiri": bool(E),
           "uretim": bool(U), "kapilar": True, "kapanis": True}
    sure = {k: s for k, s in SURELER.items() if var[k]}
    artan = SURE - sum(sure.values())
    ana = "blender" if v.motor == "blender" else "kilavuz"
    for k, en in ((ana, 1.6), ("kapilar", 0.6), ("uretim", 0.4), ("acilis", 0.4), ("elestiri", 0.4), ("yollar", 0.4)):
        if k in sure and artan > 0:
            ek = min(artan, en)
            sure[k] += ek
            artan -= ek
    sure["kapanis"] += artan
    bolumler, bas = [], 0
    for k in SURELER:
        if k not in sure:
            continue
        n = int(round(sure[k] * FPS))
        bolumler.append({"tur": k, "bas": bas, "kare": n, "aciklama": ACIKLAMA[k]})
        bas += n
    bolumler[-1]["kare"] += NKARE - bas   # yuvarlama artığı kapanışa
    onizleme = {}
    if G:
        onizleme["yollar"] = [_rel(s["kare"]) for s in G["secenekler"]]
    if E:
        onizleme["elestiri"] = [_rel(E["once"]), _rel(E["sonra"])]
    if U and U["tur"] == "gorsel":
        onizleme["uretim"] = [_rel(U["dosya"])]
    return {"video": v.id, "format": fmt, "motor": v.motor, "bolumler": bolumler, "eksik": [k for k, x in var.items() if not x and k not in ("kilavuz", "blender")],
            "onizleme": onizleme, "gorunus": G, "elestiri": E, "uretim": U}


# ---------------------------------------------------------------- malzeme
def _jpeg(kaynak: Path, hedef: Path, en: int | None = None, boyut: tuple[int, int] | None = None) -> Path:
    hedef.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(kaynak).convert("RGB")
    if boyut:
        im = im.resize(boyut, Image.LANCZOS)
    elif en and im.width > en:
        im = im.resize((en, round(im.height * en / im.width)), Image.LANCZOS)
    im.save(hedef, "JPEG", quality=JPEG, optimize=False, progressive=False, subsampling=0)
    return hedef


ESANLI = 4   # Remotion: aynı anda çizilen sayfa (kareler.mjs → esanli)


def _kareler_coklu(v, fmt, film_kareleri: list[int], hedef: Path, kipler: list[str | None]) -> dict[str | None, dict[int, Path]]:
    """Filmin kareleri birkaç kipte: None (film), "kilavuz", "veri". PNG → hedef/<kip>/fNNNNN.png. Remotion'da hepsi tek pakette, eşzamanlı."""
    import st
    fr = sorted(set(film_kareleri))
    outs = {}
    for kip in kipler:
        outs[kip] = hedef / (kip or "film")
        shutil.rmtree(outs[kip], ignore_errors=True)
        outs[kip].mkdir(parents=True, exist_ok=True)
    if v.motor == "hyperframes":
        import hf
        hf.esitle(v)
        # kişisel şablonda ST.kisi = TEST örneği (varyantın st-veri bloğu); yazılımla (SwiftShader): deterministik kip
        return {kip: hf.kareler(v, fr, outs[kip], fmt, kok=hf.kilavuz_varyanti(v, fmt, kip, dizin(v) / "hf" / f"{kip}-{fmt}") if kip else None, yazilim=True)
                for kip in kipler}
    def props(kip):
        p = st._veri_props(v, {"yapim": {"kip": kip}} if kip else None) or {}
        if v.motor == "blender":   # üst katman taslak plakalarla (önbellekten ya da çizilerek)
            import blender
            p = blender.hazirla(v, fr, fmt, {**p, "kalite": "taslak"})
        return p
    isler = [{"comp": v.comp_for(fmt), "out": str(outs[kip]), "frames": fr, "props": props(kip), **({"gl": v.gl} if v.gl else {})} for kip in kipler]
    pf = hedef / "_is.json"
    pf.write_text(json.dumps({"isler": isler, "esanli": ESANLI}, ensure_ascii=False))
    t = time.time()
    r = subprocess.run(["node", "pipeline/kareler.mjs", f"@{pf}"], cwd=O.ROOT, capture_output=True, text=True)
    pf.unlink()
    if r.returncode:
        raise SystemExit(f"Remotion kareleri çizilemedi:\n{(r.stdout + r.stderr)[-2500:]}")
    res = json.loads(r.stdout.strip().splitlines()[-1])
    print(f"   [{fmt}] {len(fr)} kare × {len(kipler)} kip, {time.time() - t:.1f} sn", flush=True)
    return {kip: {int(k): Path(p) for k, p in j["files"].items()} for kip, j in zip(kipler, res["isler"])}


def _kareler(v, fmt, film_kareleri: list[int], hedef: Path, kip: str | None) -> dict[int, Path]:
    return _kareler_coklu(v, fmt, film_kareleri, hedef, [kip])[kip]


def _veri_coz(png: Path) -> list[dict] | None:
    a = np.asarray(Image.open(png).convert("RGB"), dtype=np.int64)
    duz = a.reshape(-1, 3)
    deger = lambda i: int((duz[i, 0] << 16) | (duz[i, 1] << 8) | duz[i, 2])
    if deger(0) != 0x53544B:
        return None
    n = deger(1)
    vals = [deger(i) for i in range(n * 7 + 3)]
    if sum(vals[:-1]) % 0x1000000 != vals[-1]:
        return None
    out = []
    for k in range(n):
        x, y, w, h, kim, tb, op = vals[2 + k * 7: 9 + k * 7]
        out.append({"x": x / 4 - 8192, "y": y / 4 - 8192, "w": w / 4, "h": h / 4, "kimlik": kim, "tur": TUR_AD[(tb >> 16) & 0xff] if (tb >> 16) < len(TUR_AD) else "?",
                    "boyut": (tb & 0xffff) / 4, "opak": op / 1000})
    return out


def _izler(veri: list[list[dict]]) -> tuple[list[dict], dict]:
    """Kutuların kareler boyunca merkezleri (hareket yolu) + özet (en küçük yazı, kutu sayısı)."""
    yollar: dict[int, dict] = {}
    yazilar = []
    for i, kutular in enumerate(veri):
        for b in kutular or []:
            y = yollar.setdefault(b["kimlik"], {"kimlik": b["kimlik"], "tur": b["tur"], "noktalar": [None] * len(veri)})
            y["noktalar"][i] = [round(b["x"] + b["w"] / 2, 1), round(b["y"] + b["h"] / 2, 1)]
            if b["tur"] == "yazi" and b["opak"] >= 0.5:
                yazilar.append(b["boyut"])
    izler = []
    for y in yollar.values():
        # sürekli hareket: ardışık iki örnek arası ≤ 70 px (2 kare, ~1000 px/sn); büyük sıçrama aynı görünen başka öğedir → iz kopar
        n = list(y["noktalar"])
        for i in range(len(n) - 1, 0, -1):   # sondan başa: kopukluk yalnız sıçrayan noktayı düşürür (çizim null'da böler)
            if n[i] and n[i - 1] and math.dist(n[i], n[i - 1]) > 70:
                n[i] = None
        y["noktalar"] = n
        p = [q for q in n if q]
        if len(p) < 4:
            continue
        yol = sum(math.dist(a, b) for a, b in zip(n, n[1:]) if a and b)
        if yol >= 30:
            izler.append({**y, "uzunluk": round(yol)})
    izler.sort(key=lambda y: -y["uzunluk"])
    return izler[:8], {"en_kucuk_yazi": round(min(yazilar)) if yazilar else None, "yazi_kutusu": len(yazilar),
                        "kutu": max((len(k or []) for k in veri), default=0)}


def _yazi_konumu(veri: list[list[dict]], F: dict) -> str:
    """Filmin yazıları karenin alt yarısında mı (alan × görünme süresi): öyleyse yapım yazıları üstte durur, yoksa altta."""
    alt = ust = 0.0
    for kutular in veri:
        for b in kutular or []:
            if b["tur"] != "yazi" or b["opak"] < 0.3:
                continue
            a = b["w"] * b["h"]
            if b["y"] + b["h"] / 2 > F["h"] / 2:
                alt += a
            else:
                ust += a
    return "ust" if alt > ust else "alt"


def _pencere(v, sure_film: float) -> float:
    """Kılavuz klibinin filmdeki başlangıcı: kaba kurgu varsa görüntünün en çok değiştiği aralık, yoksa baş."""
    import st
    sure = max(0.0, v.duration - sure_film)
    if sure <= 0:
        return 0.0
    rp = st.rough_path(v, v.formatlar[0])
    if not rp.exists():
        return 0.0
    try:
        m = O.motion_curve(rp, fps=v.fps)
    except Exception:
        return 0.0
    n = max(1, int(sure_film * v.fps))
    toplam = np.convolve(m, np.ones(n), "valid")
    i = int(np.argmax(toplam[: int(sure * v.fps) + 1])) if len(toplam) else 0
    return round(i / v.fps, 3)


def _film_kareleri(v, bas: float, n: int) -> list[int]:
    """Yapımın n malzeme karesi (ADIM'da bir) için filmin kare numaraları: filmin zamanı yapımla aynı hızda akar."""
    return [min(v.nframes - 1, int(round((bas + i * ADIM / FPS) * v.fps))) for i in range(n)]


def _muzik_ve_ses(v, kurgu: dict, d: Path) -> Path:
    """Kod müziği (pipeline/muzik.py, tohumlu, kredisiz) + kapanışta filmin kendi miksi; −14 LUFS, −1,5 dBTP."""
    SR = 48000
    N = int(SURE * SR)
    m = d / "muzik.wav"
    subprocess.run([str(O.ROOT / ".venv" / "bin" / "python"), "-I", str(O.ROOT / "pipeline" / "muzik.py"), str(m), "--bpm", "96",
                    "--yapi", "giris:1,ana:4,kapanis:1", "--ton", "D", "--stil", "minimal", "--kuyruk", "0"], check=True, capture_output=True)

    def yukle(p, bas=0.0, sure=SURE):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", str(p), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype=np.float32).astype(float).reshape(-1, 2)
        out = np.zeros((int(sure * SR), 2))
        out[: min(len(out), len(x))] = x[: len(out)]
        return out

    yatak = yukle(m)
    yatak /= np.abs(yatak).max() + 1e-9
    yatak *= 10 ** (-6 / 20)
    zarf = np.ones(N)
    zarf[: int(0.25 * SR)] = np.linspace(0, 1, int(0.25 * SR))
    K = next(b for b in kurgu["bolumler"] if b["tur"] == "kapanis")
    kb = int(K["bas"] / FPS * SR)
    film = np.zeros((N, 2))
    mix = v.pub / "mix.wav"
    if mix.exists() and K.get("film_bas") is not None:
        x = yukle(mix, K["film_bas"], SURE - K["bas"] / FPS)
        film[kb:kb + len(x)] = x[: N - kb]
        g = int(0.35 * SR)
        rampa = np.clip((np.arange(N) - kb + g) / g, 0, 1)
        zarf *= 1 - 0.75 * rampa                    # kapanışta yatak kısılır, film konuşur
        film *= np.clip((np.arange(N) - kb) / int(0.12 * SR) + 1, 0, 1)[:, None]
    son = int(0.9 * SR)
    st_ = yatak * zarf[:, None] + film
    st_[-son:] *= np.linspace(1, 0, son)[:, None]
    st_ = st_ / (np.abs(st_).max() + 1e-9) * 0.89
    ham = d / "_ses_ham.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", str(ham)], input=st_.astype("<f4").tobytes(), check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(ham), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    js = json.loads(r[r.rindex("{"): r.rindex("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
          f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    ses = d / "ses.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ham), "-af", af, "-ar", str(SR), "-c:a", "pcm_s16le", str(ses)], check=True)
    ham.unlink()
    return ses


# ---------------------------------------------------------------- kurgu
def _kart(F: dict) -> tuple[int, int]:
    """Üç yol kartının ekrandaki boyutu (px): src/yapim/Yapim.tsx → Yollar ile aynı hesap (üç kart yan yana, altta üç yazının yeri)."""
    W, H, g = F["w"], F["h"], F["guvenli"]
    u = min(W, H) / 1080
    sw, sh = W - (g["sol"] + g["sag"]) * W, H - (g["ust"] + g["alt"]) * H
    en = 0.36 * W if H / W > 1.5 else (sw - 2 * 22 * u - 24 * u) / 3   # dikeyde kartlar büyük ve üst üste biner
    boy = min(en * H / W, (sh - 400 * u) * 0.92)
    return round(boy * W / H), round(boy)


def _varlik_boyut(F: dict, iw: int, ih: int) -> tuple[int, int]:
    """Yapay zekâ varlığının ekrandaki boyutu: Yapim.tsx → Uretim'deki alana sığan en büyük boyut (oran korunur)."""
    W, H, g = F["w"], F["h"], F["guvenli"]
    u = min(W, H) / 1080
    sw, sh = W - (g["sol"] + g["sag"]) * W, H - (g["ust"] + g["alt"]) * H
    k = min(sh * (0.5 if H > W else 0.62) / ih, (sw - 96 * u) / iw)
    return round(iw * k), round(ih * k)


def _guvenli(fmt) -> dict:
    return O.FORMATLAR[fmt]["guvenli"]


def _vurgu(v) -> str:
    o = v.gorunus_secimi or {}
    for k in ("vurgu", "accent"):
        h = (o.get("renk") or {}).get(k) if isinstance(o.get("renk"), dict) else None
        h = h or o.get(k)
        if isinstance(h, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", h):
            return h
    return "#FF7A2F"


def _yaz(kurgu: dict) -> list[dict]:
    """Kurgudaki her yazı: (bölüm, metin, kare aralığı). Ölçüm ve yazı tanıma bunları arar."""
    out = []
    for b in kurgu["bolumler"]:
        for y in b.get("yazilar", []):
            out.append({"bolum": b["tur"], "metin": y["metin"], "bas": b["bas"] + y.get("bas", 0), "bit": b["bas"] + y.get("bit", b["kare"])})
    return out


def uret(v, fmt: str | None = None, cikti: Path | None = None, sadece_malzeme=False) -> dict:
    t_bas = time.time()
    _bag()
    P = plan(v, fmt)
    fmt = P["format"]
    d = dizin(v)
    m = d / "m"
    shutil.rmtree(m, ignore_errors=True)
    shutil.rmtree(d / "_ham", ignore_errors=True)
    m.mkdir(parents=True, exist_ok=True)
    ham = d / "_ham"
    F = O.FORMATLAR[fmt]
    kanit, malzeme = [], {}
    adimlar = len(P["bolumler"]) + 3
    adim = [0]

    def ilerle(metin):
        adim[0] += 1
        print(f"[{adim[0]}/{adimlar}] {metin}", flush=True)

    def yol(p: Path) -> str:
        malzeme[_rel(p)] = _sha(p)
        return "_yapim/" + str(p.relative_to(ONB))

    B = {b["tur"]: b for b in P["bolumler"]}
    kurgu = {"surum": 1, "video": v.id, "format": fmt, "w": F["w"], "h": F["h"], "fps": FPS, "kare": NKARE, "guvenli": _guvenli(fmt), "vurgu": _vurgu(v),
             "baslik": baslik(v), "bolumler": []}
    kanit.append({"olgu": f"başlık: {kurgu['baslik']}", "kaynak": _rel(v.dir / "script.json")})

    # kapanış (filmin kendisi) + açılışın arka planı (poster)
    K = B["kapanis"]
    nk = -(-K["kare"] // ADIM)
    poster_t = v.cues.get("poster", v.duration - 0.5) if v.duration else 0
    k_bas = max(0.0, min(v.duration - nk * ADIM / FPS, poster_t - nk * ADIM / FPS * 0.6)) if v.duration else 0.0
    ilerle(f"film kareleri (kapanış, {nk} kare)")
    kf = _film_kareleri(v, k_bas, nk)
    fs = _kareler(v, fmt, kf + [min(v.nframes - 1, round(poster_t * v.fps))], ham, None)
    kapanis_kareleri = [yol(_jpeg(fs[f], m / "kapanis" / f"k{i:03d}.jpg")) for i, f in enumerate(kf)]
    arka = yol(_jpeg(fs[min(v.nframes - 1, round(poster_t * v.fps))], m / "poster.jpg"))
    G = P["gorunus"]
    kapilar = _kapilar(v)
    k1 = next(k for k in kapilar if k["n"] == 1)

    for b in P["bolumler"]:
        t, n = b["tur"], b["kare"]
        x = {"tur": t, "bas": b["bas"], "kare": n}
        if t == "acilis":
            ilerle("açılış")
            x.update(arka=arka, yazilar=[{"metin": kurgu["baslik"], "rol": "baslik", "bas": 0, "bit": n},
                                         {"metin": "Nasıl yapıldı", "rol": "alt", "bas": 8, "bit": n}])
        elif t == "yollar":
            ilerle("üç yol / görünüş")
            kw, kh = _kart(F)   # kart ekrandaki boyutuna Python'da küçültülür: tarayıcı ölçeklerse süzgeci çizim sırasına bağlı (2/255)
            sec = [{"harf": s["harf"], "ad": s["ad"], "kare": yol(_jpeg(s["kare"], m / "yollar" / f"{s['harf']}.jpg", boyut=(kw, kh)))} for s in G["secenekler"]]
            ad = "Üç yol önerildi" if G["mod"] == "yol" else "Üç görünüş denendi"
            ys = [{"metin": ad, "rol": "ust", "bas": 2, "bit": n}]
            if G["secim"]:
                ys.append({"metin": f"Seçilen: {G['secim'].upper()}", "rol": "alt", "bas": int(n * 0.45), "bit": n})
            ys.append({"metin": f"İnsan onayı · {k1['tarih']}" if k1["onay"] else "İnsan onayı bekliyor", "rol": "not", "bas": int(n * 0.62), "bit": n})
            x.update(secenekler=sec, secim=G["secim"], kart=[kw, kh], yazilar=ys)
            kanit.append({"olgu": f"{len(sec)} seçenek, seçilen {G['secim'] or '—'}; Kapı 1 onayı {k1['onay'] or 'yok'}",
                          "kaynak": ", ".join(G["kaynak"] + [_rel(v.dir / "kapilar.json")])})
        elif t == "kilavuz":
            nm = -(-n // ADIM)
            sure_film = nm * ADIM / FPS
            bas = _pencere(v, sure_film)
            fr = _film_kareleri(v, bas, nm)
            ilerle(f"kılavuz kipinde kareler ({nm} kare × film, kılavuz, veri; filmde {O.tc(bas)}–{O.tc(bas + sure_film)})")
            K3 = _kareler_coklu(v, fmt, fr, ham, [None, "kilavuz", "veri"])
            ff, fk, fv = K3[None], K3["kilavuz"], K3["veri"]
            veri = [_veri_coz(fv[f]) for f in fr]
            if any(q is None for q in veri):
                raise SystemExit("kılavuz verisi okunamadı (veri kipinin pikselleri bozuk): src/lib/yapim/kilavuz.ts → veriSvg")
            izler, oz = _izler(veri)
            kurgu["konum"] = _yazi_konumu(veri, F)
            film = [yol(_jpeg(ff[f], m / "kilavuz" / f"f{i:03d}.jpg")) for i, f in enumerate(fr)]
            kil = [yol(_jpeg(fk[f], m / "kilavuz" / f"k{i:03d}.jpg")) for i, f in enumerate(fr)]
            ek = oz["en_kucuk_yazi"]
            ys = [{"metin": "Önce iskelet", "rol": "ust", "bas": 2, "bit": int(n * 0.58)},
                  {"metin": f"En küçük yazı {ek} piksel" if ek else "Her kutu ölçüldü", "rol": "alt", "bas": 10, "bit": int(n * 0.58)},
                  {"metin": "Sonra film", "rol": "ust", "bas": int(n * 0.62), "bit": n}]
            if izler:
                ys.insert(2, {"metin": "Hareket yolu", "rol": "not", "bas": int(n * 0.3), "bit": int(n * 0.58)})
            x.update(film=film, kilavuz=kil, izler=izler, adim=ADIM, film_bas=bas, yazilar=ys, ozet=oz)
            kanit.append({"olgu": f"kılavuz: {oz['yazi_kutusu']} yazı kutusu, en küçük yazı {ek} px, {len(izler)} hareket yolu; filmde {O.tc(bas)}",
                          "kaynak": "kılavuz kipinde çizim (src/lib/yapim/kilavuz.ts)"})
        elif t == "blender":
            import blender as BL
            nm = -(-n // ADIM)
            bas = _pencere(v, nm * ADIM / FPS)
            fr = _film_kareleri(v, bas, nm)
            ilerle(f"Blender: kil, tel kafes, kamera yolu ({nm} kare) + son hâl")
            # kamera yolu evresi (bölümün 3. çeyreği) bütün filmi hızlandırılmış gezer: kamera yolun başından sonuna gider, çizgi kendini çizer
            q = n / 4
            fr_ust = [round(min(1.0, max(0.0, (i * ADIM - 2 * q) / q)) * (v.nframes - 1)) for i in range(nm)]
            gec, kareler_ = {}, {}
            for kip in BL.YAPIM_KIPLERI:
                kf_ = fr_ust if kip == "ust" else fr
                kume, ps = BL.yapim_plakalari(v, kf_, fmt, kip)
                gec[kip] = [yol(_jpeg(ps[f], m / "blender" / f"{kip}{i:03d}.jpg")) for i, f in enumerate(kf_)]
                kareler_[kip] = kf_
                kanit.append({"olgu": f"Blender geçişi «{kip}»: {len(set(kf_))} plaka", "kaynak": f"out/_plaka/{v.id}/{kume}"})
            ff = _kareler(v, fmt, fr, ham, None)
            gec["son"] = [yol(_jpeg(ff[f], m / "blender" / f"son{i:03d}.jpg")) for i, f in enumerate(fr)]
            q = n // 4
            ys = [{"metin": "Kil", "rol": "ust", "bas": 2, "bit": q}, {"metin": "Tel kafes", "rol": "ust", "bas": q, "bit": 2 * q},
                  {"metin": "Kamera yolu", "rol": "ust", "bas": 2 * q, "bit": 3 * q}, {"metin": "Işık ve malzeme", "rol": "ust", "bas": 3 * q, "bit": n}]
            x.update(gecisler=gec, adim=ADIM, film_bas=bas, film_kareleri=kareler_, yazilar=ys)
        elif t == "elestiri":
            ilerle("inceleme turları: önce ve sonra")
            E = P["elestiri"]
            t1, t2 = E["tur1"], E["tur2"]
            ad = "Kör eleştiri" if t1["elestiri"] or t2["elestiri"] else "İnceleme"
            ys = [{"metin": f"{ad} turu {t1['n']} → {t2['n']}", "rol": "ust", "bas": 2, "bit": n}]
            if t1["carpi"] is not None and t2["carpi"] is not None and t1["carpi"] > t2["carpi"]:
                ys.append({"metin": f"Ölçümde hata {t1['carpi']} → {t2['carpi']}", "rol": "alt", "bas": int(n * 0.4), "bit": n})
            else:
                ys.append({"metin": "Aynı an, iki tur", "rol": "alt", "bas": int(n * 0.4), "bit": n})
            x.update(once=yol(_jpeg(E["once"], m / "elestiri" / "once.jpg", 1080)), sonra=yol(_jpeg(E["sonra"], m / "elestiri" / "sonra.jpg", 1080)),
                     etiket1=f"{t1['n']}. tur", etiket2=f"{t2['n']}. tur", yazilar=ys)
            kanit.append({"olgu": f"{t1['ad']} → {t2['ad']}, kare {E['kare']} (fark {E['fark']}/255); ❌ {t1['carpi']} → {t2['carpi']}",
                          "kaynak": ", ".join(E["kaynak"])})
        elif t == "uretim":
            ilerle("yapay zekâ varlığının kaynağı")
            U = P["uretim"]
            if U["tur"] == "video":
                kaynak = ham / "uretim_ilk.png"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(U["dosya"]), "-frames:v", "1", str(kaynak)], check=True)
            else:
                kaynak = U["dosya"]
            ys = [{"metin": "Yapay zekâ ile üretildi", "rol": "ust", "bas": 2, "bit": n},
                  {"metin": f"{U['model']} · {U['kredi']} kredi", "rol": "alt", "bas": int(n * 0.25), "bit": n}]
            if U["istem"]:
                ys.append({"metin": "İstemi kayıtlı", "rol": "not", "bas": int(n * 0.45), "bit": n})
            vb = _varlik_boyut(F, *Image.open(kaynak).size)   # ekrandaki boyutuna Python'da (tarayıcı ölçeklemesin)
            x.update(varlik=yol(_jpeg(kaynak, m / "uretim" / "varlik.jpg", boyut=vb)), varlik_boyut=list(vb), film=arka, yazilar=ys)
            kanit.append({"olgu": f"yapay zekâ varlığı {U['ad']}: {U['model']}, {U['kredi']} kredi, istem {'kayıtlı' if U['istem'] else 'yok'}",
                          "kaynak": ", ".join(U["kaynak"])})
        elif t == "kapilar":
            ilerle("kapılar")
            insan = sum(1 for k in kapilar if k["insan"])
            x.update(kapilar=kapilar, yazilar=[{"metin": f"Altı kapıdan {SAYI.get(insan, insan)} insanın", "rol": "ust", "bas": 2, "bit": n}])
            kanit.append({"olgu": "kapılar: " + ", ".join(f"{k['n']} {k['durum']}{' ' + k['onay'] if k['onay'] else ''}" for k in kapilar),
                          "kaynak": _rel(v.dir / "kapilar.json") + " + ./st durum"})
        elif t == "kapanis":
            x.update(kareler=kapanis_kareleri, adim=ADIM, film_bas=k_bas,
                     yazilar=[{"metin": "Son kapı insanın", "rol": "ust", "bas": max(2, n - 54), "bit": n}])
        kurgu["bolumler"].append(x)

    ana = next((x for x in kurgu["bolumler"] if x["tur"] in ("kilavuz", "blender")), None)
    if ana:   # açılış: filmin bir anı ve aynı anın iskeleti; sürgü ilk saniyede iskeleti açar (kanca)
        A = next(x for x in kurgu["bolumler"] if x["tur"] == "acilis")
        A["film"], A["iskelet"] = (ana["film"][0], ana["kilavuz"][0]) if ana["tur"] == "kilavuz" else (ana["gecisler"]["son"][0], ana["gecisler"]["kil"][0])
    for x in kurgu["bolumler"]:   # filmin kendi yazısının olmadığı yarı (kılavuz verisinden; yoksa alt)
        if x["tur"] in ("kilavuz", "elestiri", "kapanis"):
            x["konum"] = kurgu.get("konum", "alt")
    ilerle("ses: kod müziği + filmin miksi")
    ses = _muzik_ve_ses(v, kurgu, d)
    kurgu["yazilar"] = _yaz(kurgu)
    (d / "kurgu.json").write_text(json.dumps(kurgu, ensure_ascii=False, indent=1) + "\n")
    shutil.rmtree(ham, ignore_errors=True)
    kayit = {"video": v.id, "format": fmt, "motor": v.motor, "tarih": time.strftime("%Y-%m-%d %H:%M"), "bolumler": [b["tur"] for b in P["bolumler"]],
             "eksik": P["eksik"], "kanitlar": kanit, "malzeme": malzeme, "ses": {"dosya": _rel(ses), "sha256": _sha(ses)}}
    if sadece_malzeme:
        (d / "yapim.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n")
        return kayit
    ilerle("Remotion: Yapim-" + fmt)
    sessiz = d / "_sessiz.mp4"
    props = d / "props.json"
    props.write_text(json.dumps({"kurgu": kurgu}, ensure_ascii=False))
    subprocess.run(["npx", "remotion", "render", "src/index.ts", f"Yapim-{fmt}", str(sessiz), "--props", str(props), "--codec=h264", "--crf=18",
                    "--log=error"], cwd=O.ROOT, check=True)
    mp4 = d / f"{v.id}_yapim.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(sessiz), "-i", str(ses), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "256k", "-shortest", str(mp4)], check=True)
    sessiz.unlink()
    ilerle("ölçüm")
    import veri as V
    rows = olc(v, kurgu, mp4)
    kayit["olcum"] = rows
    kayit["sure_sn"] = round(time.time() - t_bas, 1)
    hedef = _hedef(v, cikti)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mp4, hedef)
    poster = hedef.with_name(hedef.stem + "_poster.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(B['acilis']['kare'] - 1) / FPS:.3f}", "-i", str(mp4), "-frames:v", "1", "-q:v", "3", str(poster)],
                   check=True)
    kayit["cikti"] = str(hedef)
    kayit["poster"] = str(poster)
    bd = d / "bolum"   # panel: her bölümün ortasından bir kare
    shutil.rmtree(bd, ignore_errors=True)
    bd.mkdir()
    for b in kurgu["bolumler"]:
        f = b["bas"] + int(b["kare"] * {"kilavuz": 0.3, "elestiri": 0.75, "yollar": 0.75}.get(b["tur"], 0.5))
        V.mp4_karesi(mp4, f, bd / f"{b['tur']}.png")
        if (bd / f"{b['tur']}.png").exists():
            _jpeg(bd / f"{b['tur']}.png", bd / f"{b['tur']}.jpg", 540)
            (bd / f"{b['tur']}.png").unlink()
    kayit["bolum_kareleri"] = {b["tur"]: _rel(bd / f"{b['tur']}.jpg") for b in kurgu["bolumler"] if (bd / f"{b['tur']}.jpg").exists()}
    (d / "yapim.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n")
    _olcum_md(v, kayit, d / "olcum.md")
    if hedef.parent != CIKTI:
        shutil.copy2(d / "olcum.md", hedef.with_name(hedef.stem + "_olcum.md"))
    return kayit


def _hedef(v, cikti) -> Path:
    if not cikti:
        return CIKTI / f"{v.id}_yapim.mp4"
    c = Path(cikti)
    c = c if c.is_absolute() else Path.cwd() / c
    return c if c.suffix == ".mp4" else c / f"{v.id}_yapim.mp4"


# ---------------------------------------------------------------- ölçüm
def _kontrast(a: str, b: str) -> float:
    return O.kontrast(a, b)


def olc(v, kurgu: dict, mp4: Path) -> list[dict]:
    """Yapım filminin ölçümü: süre, yazılar (punto ve güvenli alan kılavuzun kendisiyle; kontrast; yazı tanıma filmin MP4'ünden), ilk kare,
    tek karelik sıçrama, boş ekran, ses yüksekliği, malzemenin dondurulması, kişisel veri."""
    import veri as V
    rows = []
    ok = lambda d, ad, deger, hedef, kanit="": rows.append({"durum": d, "ad": ad, "deger": deger, "hedef": hedef, "kanit": kanit})
    pr = O.probe(mp4)
    sure = float(pr["format"]["duration"])
    vs = next(s for s in pr["streams"] if s["codec_type"] == "video")
    nk = int(vs.get("nb_frames") or 0)
    ok("✅" if abs(sure - SURE) <= 0.1 and (not nk or nk == NKARE) else "❌", "Süre", f"{sure:.2f} sn · {nk} kare", f"{SURE:.0f} sn · {NKARE} kare")
    # yazılar: Yapim kompozisyonunun kendisi kılavuzun veri kipinde (DOM'dan): punto ve güvenli alan
    Y = kurgu["yazilar"]
    kareler = sorted({min(NKARE - 1, (y["bas"] + y["bit"]) // 2 + 4) for y in Y})
    d = dizin(v) / "_olcum"
    shutil.rmtree(d, ignore_errors=True)
    props = {"kurgu": kurgu, "yapim": {"kip": "veri"}}
    pf = dizin(v) / "_olcum_props.json"
    pf.write_text(json.dumps({"comp": f"Yapim-{kurgu['format']}", "out": str(d), "frames": kareler, "props": props}, ensure_ascii=False))
    r = subprocess.run(["node", "pipeline/kareler.mjs", f"@{pf}"], cwd=O.ROOT, capture_output=True, text=True)
    pf.unlink()
    if r.returncode:
        ok("❌", "Yazılar ölçülemedi", "", "", r.stderr[-400:])
        return rows
    W, H, g = kurgu["w"], kurgu["h"], kurgu["guvenli"]
    sx0, sy0, sx1, sy1 = g["sol"] * W, g["ust"] * H, W - g["sag"] * W, H - g["alt"] * H
    kucuk, disari, gorulen = [], [], 0
    for f in kareler:
        kut = _veri_coz(d / f"f{f:05d}.png") or []
        for b in kut:
            if b["tur"] != "yazi" or b["opak"] < 0.5:
                continue
            gorulen += 1
            if b["boyut"] < YAZI_ESIK - 0.5:
                kucuk.append(f"f{f} {b['boyut']:.0f} px")
            if b["x"] < sx0 - 1 or b["y"] < sy0 - 1 or b["x"] + b["w"] > sx1 + 1 or b["y"] + b["h"] > sy1 + 1:
                disari.append(f"f{f} ({b['x']:.0f},{b['y']:.0f} {b['w']:.0f}×{b['h']:.0f})")
    ok("✅" if gorulen and not kucuk else "❌", f"Yazı ≥ {YAZI_ESIK} px", f"{gorulen} yazı kutusu" + (f" · küçük: {', '.join(kucuk[:4])}" if kucuk else ""),
       f"≥ {YAZI_ESIK} px (1080 kısa kenarda)", "Yapim kompozisyonu kılavuzun veri kipinde (DOM)")
    ok("✅" if not disari else "❌", "Yazı güvenli alanda", "hepsi içeride" if not disari else ", ".join(disari[:4]), "formatın güvenli alanı")
    k = min(_kontrast("#F4F1EA", p) for p in ("#0E1014", "#15171C"))   # yazı ve plaka (Yapim.tsx → YAZI, PLAKA: opak), zemin
    ok("✅" if k >= KONTRAST_ESIK else "❌", "Yazı kontrastı", f"{k:.1f}:1", f"≥ {KONTRAST_ESIK}:1")
    # yazı tanıma (MP4'ten)
    kd = dizin(v) / "_ocr"
    shutil.rmtree(kd, ignore_errors=True)
    kd.mkdir(parents=True)
    pngs = {}
    for y in Y:
        f = min(NKARE - 1, y["bit"] - 3)
        if f not in pngs:
            pngs[f] = V.mp4_karesi(mp4, f, kd / f"f{f:05d}.png")
    o = V.ocr([p for p in pngs.values() if p])
    if o is None:
        ok("👁", "Yazılar ekranda okunuyor", "yazı tanıma yok (Xcode komut satırı araçları)", "göz")
    else:
        bulunmayan = []
        for y in Y:
            p = pngs[min(NKARE - 1, y["bit"] - 3)]
            metinler = o.get(str(p), [])
            if not V.ekranda_bul(metinler, y["metin"].replace("…", ""), False) and not _gevsek(metinler, y["metin"]):
                bulunmayan.append(f"«{y['metin']}» (f{min(NKARE - 1, y['bit'] - 3)})")
        ok("✅" if not bulunmayan else "⚠️", "Yazılar ekranda okunuyor", f"{len(Y) - len(bulunmayan)}/{len(Y)}" + (f" · okunamayan: {', '.join(bulunmayan[:3])}" if bulunmayan else ""),
           "her yazı filmin MP4'ünden okunur (macOS Vision)")
    shutil.rmtree(kd, ignore_errors=True)
    # görüntü: ilk kare, tek karelik sıçrama, boş ekran
    fr = O.gray_frames(mp4, 90, int(90 * H / W) // 2 * 2, fps=FPS)
    hareket = O.motion_of(fr)
    bos = O.blank_runs(fr, 3)
    ilk_bos = bool(bos and bos[0][0] == 0)
    ok("❌" if ilk_bos else "✅", "İlk kare boş değil", "boş" if ilk_bos else "dolu", "kanca 0. karede")
    fl = O.flash_frames(fr, hareket)
    ok("✅" if not fl else "❌", "Tek karelik sıçrama", "yok" if not fl else ", ".join(f"f{i}" for i in fl[:6]), "yok")
    uzun = [(a, b) for a, b, _ in bos if b - a >= FPS * 0.5]
    ok("✅" if not uzun else "⚠️", "Boş ekran", "yok" if not uzun else ", ".join(f"{O.tc(a / FPS)}–{O.tc(b / FPS)}" for a, b in uzun), "< 0,5 sn")
    L = O.loudness(mp4)
    ok("✅" if abs(L["I"] + 14) <= 1.0 and L["TP"] <= -1.0 else "❌", "Ses yüksekliği", f"{L['I']:.1f} LUFS · {L['TP']:.1f} dBTP", "−14 ± 1 LUFS, ≤ −1 dBTP")
    # kanıt: malzeme dondurulmuş, kişisel veri yok
    km = json.loads((dizin(v) / "kurgu.json").read_text()) if (dizin(v) / "kurgu.json").exists() else kurgu
    yollar = re.findall(r'"(_yapim/[^"]+)"', json.dumps(km, ensure_ascii=False))
    eksik = [p for p in yollar if not (ONB / p[len("_yapim/"):]).exists()]
    ok("✅" if not eksik else "❌", "Malzeme dondurulmuş", f"{len(set(yollar))} dosya, sha256 yapim.json'da" + (f" · eksik {len(eksik)}" if eksik else ""),
       "her görsel out/_yapim/<id>/m/'de")
    kisisel = any("/toplu/" in p for p in yollar) or "/toplu/" in json.dumps(km, ensure_ascii=False)
    ok("❌" if kisisel else "✅", "Kişisel veri yok", "toplu/'dan malzeme var" if kisisel else "toplu/ okunmadı" + (" (şablonun TEST örneği)" if _kisisel(v) else ""),
       "kişisel etki filminde yalnız şablon ve TEST")
    return rows


def _gevsek(metinler: list[str], aranan: str) -> bool:
    """Yazı tanıma büyük harfin işaretini, orta noktayı ya da oku kaçırabiliyor: harf ve rakamlar sırayla geçiyor mu."""
    import unicodedata
    sade = lambda s: re.sub(r"[^0-9a-z]", "", unicodedata.normalize("NFKD", s.replace("İ", "i").replace("ı", "i").lower()).encode("ascii", "ignore").decode())
    t = sade(" ".join(metinler))
    a = sade(aranan)
    return bool(a) and a in t


def _kisisel(v) -> bool:
    import kisisel
    return kisisel.var_mi(v)


def _olcum_md(v, kayit: dict, hedef: Path):
    L = [f"# Yapım filmi ölçümü · {v.id} · {kayit['format']} · {kayit['tarih']}", "",
         f"Bölümler: {', '.join(kayit['bolumler'])}" + (f" · kaydı olmayan: {', '.join(kayit['eksik'])}" if kayit["eksik"] else ""),
         f"Üretim süresi: {kayit.get('sure_sn', '—')} sn · çıktı: {kayit.get('cikti', '—')}", "",
         "| Durum | Ölçüt | Değer | Hedef |", "|---|---|---|---|"]
    L += [f"| {r['durum']} | {r['ad']} | {r['deger']} | {r['hedef']} |" for r in kayit.get("olcum", [])]
    L += ["", "## Ekrandaki her olgunun kaynağı", ""] + [f"- {k['olgu']} — `{k['kaynak']}`" for k in kayit["kanitlar"]]
    hedef.write_text("\n".join(L) + "\n")


# ---------------------------------------------------------------- panel ve deterministiklik
def ozet(v) -> dict:
    """Panel (Teslim → Nasıl yapıldı filmi): plan (bölümler, önizleme görselleri), son çıktı, ölçüm özeti."""
    try:
        P = plan(v)
    except SystemExit as e:
        return {"hata": str(e)}
    kj = dizin(v) / "yapim.json"
    K = O.jload(kj) if kj.exists() else None
    son = None
    if K and K.get("cikti") and Path(K["cikti"]).exists():
        c = Path(K["cikti"])
        son = {"dosya": str(c.resolve().relative_to(O.KANAL)) if c.resolve().is_relative_to(O.KANAL) else None, "ad": c.name,
               "poster": str(Path(K["poster"]).resolve().relative_to(O.KANAL)) if K.get("poster") and Path(K["poster"]).resolve().is_relative_to(O.KANAL) else None,
               "tarih": K["tarih"], "mb": round(c.stat().st_size / 1e6, 1), "sure_sn": K.get("sure_sn"), "format": K["format"],
               "olcum": K.get("olcum", []), "bolumler": K.get("bolumler", []),
               "kareler": {k: str((O.ROOT / p).resolve().relative_to(O.KANAL)) for k, p in (K.get("bolum_kareleri") or {}).items() if (O.ROOT / p).exists()}}
    oz = dizin(v) / f"onizleme-{P['format']}.jpg"
    return {"plan": [{"tur": b["tur"], "aciklama": b["aciklama"], "sn": round(b["kare"] / FPS, 1)} for b in P["bolumler"]], "eksik": P["eksik"],
            "onizleme": {k: [str((O.ROOT / p).resolve().relative_to(O.KANAL)) for p in ps] for k, ps in P["onizleme"].items()},
            "format": P["format"], "son": son, "tahmini_sn": tahmini_sure(v),
            "kilavuz_onizleme": str(oz.resolve().relative_to(O.KANAL)) if oz.exists() else None, "motor": v.motor}


def onizle(v, fmt: str | None = None) -> Path:
    """Panelin görsel önizlemesi: kılavuz kipinde tek kare (Remotion, HyperFrames; poster anı) ya da Blender'da kil geçişinin karesi."""
    fmt = fmt or v.formatlar[0]
    _bag()
    d = dizin(v)
    hedef = d / f"onizleme-{fmt}.jpg"
    f = min(max(0, v.nframes - 1), round(v.cues.get("poster", v.duration * 0.6) * v.fps)) if v.duration else 0
    with __import__("tempfile").TemporaryDirectory(prefix="st_yapim_on_") as tmp:
        if v.motor == "blender":
            import blender as BL
            _, ps = BL.yapim_plakalari(v, [f], fmt, "kil")
            kaynak = ps[f]
        else:
            kaynak = _kareler(v, fmt, [f], Path(tmp), "kilavuz")[f]
        _jpeg(kaynak, hedef, 720)
    return hedef


def tahmini_sure(v) -> int:
    """Üretim süresinin tahmini (sn): bu film daha önce çizildiyse o süre; yoksa motora göre (M4'te ölçüldü, 2026-10-27: HyperFrames ~1 dk,
    Blender kil kamp ~3,5 dk, Remotion sahnenin ağırlığına göre 2–5 dk)."""
    kj = dizin(v) / "yapim.json"
    if kj.exists() and O.jload(kj).get("sure_sn"):
        return int(O.jload(kj)["sure_sn"])
    klip = -(-int((SURELER["kilavuz"] + 1.6) * FPS) // ADIM) + -(-int(SURELER["kapanis"] * FPS) // ADIM)
    taban = 45
    if v.motor == "hyperframes":
        return int(taban + klip * 3 * 0.15)
    if v.motor == "blender":
        return int(taban + klip * 3 * 0.4 + klip * 1.2)
    return int(taban + klip * 3 * (0.8 if v.gl else 0.5))


def deterministik(v) -> list[str]:
    """./st deterministik <id> --yapim: (1) malzeme sha256'ları yapim.json'la aynı, (2) Yapim kompozisyonunun kareleri iki sırada bayt bayt aynı,
    (3) kılavuz kipinin iki karesi (film ve veri) yeniden çizilince dondurulmuş malzemeyle aynı (JPEG baytı / veri), (4) Blender geçişi toleransla."""
    d = dizin(v)
    if not (d / "yapim.json").exists() or not (d / "kurgu.json").exists():
        return [f"⏸ yapım filmi yok: ./st yapim {v.id}"]
    K = O.jload(d / "yapim.json")
    kurgu = O.jload(d / "kurgu.json")
    satir = []
    bozuk = [p for p, h in K["malzeme"].items() if not (O.ROOT / p).exists() or _sha(O.ROOT / p) != h]
    satir.append(f"{'✅' if not bozuk else '❌'} malzeme dondurulmuş: {len(K['malzeme']) - len(bozuk)}/{len(K['malzeme'])} sha256 aynı"
                 + (f" · değişen: {', '.join(bozuk[:3])}" if bozuk else ""))
    # her bölümün ortası + giriş ve geçiş kareleri (ölçek ve saydamlık canlanırken Chrome'un katman kararları sıraya duyarlı olabilir)
    kar = sorted({0, NKARE - 1, *[b["bas"] + b["kare"] // 2 for b in kurgu["bolumler"]],
                  *[min(NKARE - 1, b["bas"] + k) for b in kurgu["bolumler"] for k in (2, 5, 9, 14)]})
    props = {"kurgu": kurgu}
    with __import__("tempfile").TemporaryDirectory(prefix="st_yapim_det_") as tmp:
        sonuc = []
        for sira in ("asc", "desc"):
            pf = Path(tmp) / f"{sira}.json"
            pf.write_text(json.dumps({"comp": f"Yapim-{kurgu['format']}", "out": str(Path(tmp) / sira), "frames": kar, "order": sira, "props": props},
                                     ensure_ascii=False))
            subprocess.run(["node", "pipeline/kareler.mjs", f"@{pf}"], cwd=O.ROOT, check=True, capture_output=True)
            sonuc.append({f: (Path(tmp) / sira / f"f{f:05d}.png").read_bytes() for f in kar})
        ayni = sum(sonuc[0][f] == sonuc[1][f] for f in kar)
        satir.append(f"{'✅' if ayni == len(kar) else '❌'} Yapim-{kurgu['format']}: {ayni}/{len(kar)} kare iki sırada bayt bayt aynı")
        # kılavuz: filmin iki karesi yeniden (dondurulmuşla aynı mı)
        b = next((x for x in kurgu["bolumler"] if x["tur"] == "kilavuz"), None)
        if b:
            fr = _film_kareleri(v, b["film_bas"], len(b["film"]))
            sec = [0, len(fr) // 2]
            ff = _kareler(v, kurgu["format"], [fr[i] for i in sec], Path(tmp) / "k", "kilavuz")
            esit = 0
            for i in sec:
                yeni = _jpeg(ff[fr[i]], Path(tmp) / f"k{i}.jpg")
                esit += yeni.read_bytes() == (ONB / b["kilavuz"][i][len("_yapim/"):]).read_bytes()
            satir.append(f"{'✅' if esit == len(sec) else '❌'} kılavuz kipi: {esit}/{len(sec)} kare yeniden çizimde dondurulmuş malzemeyle bayt bayt aynı")
        bb = next((x for x in kurgu["bolumler"] if x["tur"] == "blender"), None)
        if bb:
            import blender as BL
            for kip in BL.YAPIM_KIPLERI:
                fr = sorted(set(bb.get("film_kareleri", {}).get(kip) or _film_kareleri(v, bb["film_bas"], len(bb["gecisler"]["kil"]))))
                satir += BL.yapim_yeniden_ciz(v, kurgu["format"], kip, [fr[0], fr[len(fr) // 2], fr[-1]])
    return satir
