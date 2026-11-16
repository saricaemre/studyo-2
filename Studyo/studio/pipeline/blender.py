"""Blender motoru: script.json → "motor": "blender" olan videolar.

Sahne blender/<id>/sahne.py'de Python ile yazılır (stüdyonun kiti: blender/kit/, kurallar blender/CLAUDE.md). Film iki katmandır:
  1. Plaka: Blender (Cycles) her kareyi PNG olarak çizer. Plakalar önbellektedir: out/_plaka/<id>/<format>-<kalite>-<parmak izi>/pNNNNN.png.
     Parmak izi = Blender sürümü + kit + sahne klasörü + stüdyonun verisi (format, işaretler, görünüş, marka, tohum) + kalite.
     Bunlar değişmedikçe hiçbir kare yeniden çizilmez. Eksik kareler en çok 30'luk ayrı Blender işleriyle çizilir
     (tek işlemde uzun çizim bellekte büyüyüp takasa düşüyordu: kil kamp denemesi, denemeler/blender_kil_cadir/OKU.md).
  2. Üst katman: Remotion (src/<id>/Video.tsx) plakayı <BlenderPlaka> ile kareye koyar, son rötuşu (Bitis), yazıyı, logoyu,
     altyazıyı ve sesi ekler. Kontak, ölçüm, kör eleştiri, kapılar ve yayın paketi öteki motorlarla aynıdır (MP4 ve kareler).
Plakalar Remotion'a public/<id>/plaka → out/_plaka/<id> bağlantısıyla gider: bağlantı paketlemede kopyalanmaz
(ölçüm: blender/CLAUDE.md → "Plakalar Remotion'a nasıl gider"; öğrenimler #49–#50).
Cycles bu Mac'te bayt bayt deterministik değil (gürültü giderici açıkken ≤ 1/255): plakalar bir kez çizilip dondurulur;
./st deterministik üst katmanı katı (bayt bayt), Blender'ın yeniden çizimini toleransla ölçer.
Çizer (script.json → blender.cizer): cycles (varsayılan) ya da eevee (rasterleştirici, çok daha hızlı; blender/eevee/, blender/CLAUDE.md → Çizer).
EEVEE'nin kodu ve kalitesi yalnız EEVEE filminin parmak izine girer: cizer alanı olmayan filmlerin küme adları ve plakaları değişmez.
"""
import fcntl
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

SURUM = "5.2.2"  # sabit (LTS): aynı kaynak her zaman aynı plakayı versin. Yükseltmeden önce Blender videolarında plaka karşılaştırması.
BLENDER = os.environ.get("STUDYO_BLENDER", "/opt/homebrew/bin/blender")
KOK = O.ROOT / "blender"
KIT = KOK / "kit"
CALISTIR = KIT / "calistir.py"
EEVEE = KOK / "eevee"   # EEVEE çizeri: sahne sarmalayıcısı + ayarlar (yalnız cizer: eevee filminin parmak izinde)
TAKIP = KOK / "takip"   # kamera takibi: sahnenin modülü (yalnız takip filminin parmak izinde; çözücü coz.py plakaya girmez)
CIZERLER = ("cycles", "eevee")
SABLON = O.ROOT / "sablon" / "blender"
ONBELLEK = O.ROOT / "out" / "_plaka"
PARCA = 30          # bir Blender işinde en çok bu kadar kare
TUT = 4             # (format, kalite) başına saklanan en yeni plaka kümesi
KALITE = {
    # görünüş denemesi, kare, inceleme, kaba kurgu, deterministiklik: yarım çözünürlük, az örnek
    "taslak": {"olcek": 50, "ornek": 16, "esik": 0.03, "gurultu": True},
    # temsilî kareler, teslim ve poster
    "tam": {"olcek": 100, "ornek": 48, "esik": 0.015, "gurultu": True},
}
KALITE_EEVEE = {
    # ornek: TAA örneği (alan derinliği, hareket bulanıklığı ve yumuşak gölge bunlarla birikir); golge: gölge haritası çözünürlüğü;
    # isin: ekran uzayı ışın izleme çözünürlük böleni (1 tam, 2 yarım); bulaniklik: hareket bulanıklığı adımı; golge_isin/adim: yumuşak gölge
    # Süre örnek sayısıyla doğrusal (kil kamp tam: 64 örnek 7,2 sn, 32 örnek 3,9 sn, 24 örnek 3,0 sn); 24 örnek 128 örnekli kareden gözle
    # ayırt edilmiyor (ortalama fark 1,0/255). Yarım ışın izleme hızlandırmıyor, gölge ışını 1'e inince fark büyüyor (denemeler/blender_eevee/OKU.md).
    "taslak": {"olcek": 50, "ornek": 16, "golge": 0.5, "isin": 2, "bulaniklik": 1, "golge_isin": 1, "golge_adim": 6},
    "tam": {"olcek": 100, "ornek": 24, "golge": 1.0, "isin": 1, "bulaniklik": 1, "golge_isin": 2, "golge_adim": 8},
}
# Cycles yeniden çizim (oturum 5, 2026-10-27): 1/255'lik sayısal gürültü sayılmaz (esik), > 1/255 farklı piksel ≤ %0,01, en büyük ≤ 8/255 (EEVEE ile aynı).
# Ölçüm (denemeler/blender_eevee/OKU.md): Cycles taslak ayrı işlemde en büyük 4/255, > 1/255 en çok %0,0068 (eski ölçü "1/255 dahil ≤ %0,1, ≤ 2/255"
# bunu yanlış ❌ sayıyordu); tam 1/255, > 1/255 yok. Tohumsuz rastgelelik ya da gerçek değişiklik binlerce pikseli 1/255'ten fazla oynatır. Yalnız ölçüm: parmak izine girmez.
TOLERANS = {"en_buyuk": 8, "oran": 0.0001, "esik": 1}
# EEVEE (ısınmadan sonra; denemeler/blender_eevee/OKU.md): 1/255'lik sayısal gürültü piksellerin %1,1'ine kadar yayılıyor, ondan büyük fark
# en çok %0,0006'da (en büyük 4/255). Tolerans: 1/255 sayılmaz (esik), > 1/255 farklı piksel ≤ %0,01, en büyük ≤ 8/255. Isınmasız ilk çizim
# (17–29/255, > 1/255 %0,35) ya da tohumsuz rastgelelik bunu geçer.
TOLERANS_EEVEE = {"en_buyuk": 8, "oran": 0.0001, "esik": 1}
# Panelin ve ilerleme satırının ilk tahmini (ilk plaka çıkınca gerçek hızla düzelir): sn/kare (M4, 16 GB, kil kamp) + iş başına açılış
# (2026-10-26: Cycles taslak 2,9–3,9, tam 22 sessizken / 30 ekran kartı paylaşılırken; EEVEE taslak 0,63, tam 3–4,5; açılış = Blender + kurulum
# + EEVEE'de ısınma karesi)
SURE = {("cycles", "taslak"): 3.3, ("cycles", "tam"): 24.0, ("eevee", "taslak"): 0.65, ("eevee", "tam"): 4.0}
ACILIS = {"cycles": 4.0, "eevee": 7.0}
DISARIDA = {"__pycache__", ".DS_Store"}


def klasor(v) -> Path:
    return KOK / v.id


def surum(v=None) -> str:
    return ((v.script.get("blender") or {}).get("surum") if v else None) or SURUM


_surum_onbellek = {}


def surum_denetle(beklenen: str):
    """Kurulu Blender'ın sürümü sabitle aynı olmalı: başka sürüm aynı sahneden başka plaka çizer."""
    if BLENDER not in _surum_onbellek:
        if not Path(BLENDER).exists():
            raise SystemExit(f"Blender yok: {BLENDER}. Kurulum: brew install --cask blender (sürüm {beklenen}); başka yer: STUDYO_BLENDER=/yol/blender")
        r = subprocess.run([BLENDER, "--version"], capture_output=True, text=True)
        m = re.search(r"Blender (\d+\.\d+\.\d+)", r.stdout)
        _surum_onbellek[BLENDER] = m.group(1) if m else "?"
    kurulu = _surum_onbellek[BLENDER]
    if kurulu != beklenen:
        raise SystemExit(f"Blender sürümü {kurulu}, bu video {beklenen} istiyor (script.json → blender.surum). Sürüm değişince bütün plakalar "
                         "yeniden çizilir ve kareler değişir: önce plaka karşılaştırması yap, sonra sürümü bilerek yükselt.")


def cizer(v) -> str:
    """Çizer: script.json → blender.cizer (yoksa cycles)."""
    c = (v.script.get("blender") or {}).get("cizer") or "cycles"
    if c not in CIZERLER:
        raise SystemExit(f"Çizer yok: {c} (script.json → blender.cizer: {' | '.join(CIZERLER)})")
    return c


def kalite(v, ad: str) -> dict:
    if ad not in KALITE:
        raise SystemExit(f"Kalite yok: {ad} (taslak | tam)")
    temel = KALITE_EEVEE if cizer(v) == "eevee" else KALITE
    return {**temel[ad], **(((v.script.get("blender") or {}).get("kalite") or {}).get(ad) or {})}


def tolerans(v) -> dict:
    return TOLERANS_EEVEE if cizer(v) == "eevee" else TOLERANS


def secenek(v, anahtar=None) -> dict | None:
    G = v.gorunus_json() or {}
    S = G.get("secenekler") or {}
    k = anahtar or G.get("secim") or (sorted(S)[0] if S else None)
    return S.get(k) if k else None


def _marka(v) -> dict | None:
    m = v.script.get("marka")
    p = O.ROOT / "markalar" / str(m) / "marka.json" if m else None
    return O.jload(p) if p and p.exists() else None


def tohum(v) -> int:
    t = (v.script.get("blender") or {}).get("tohum")
    return int(t) if t is not None else int(hashlib.sha1(v.id.encode()).hexdigest()[:6], 16)


# ---------------------------------------------------------------- veri (HyperFrames'teki window.ST karşılığı)
def veri(v, fmt: str, anahtar: str | None = None) -> dict:
    F = O.FORMATLAR[fmt]
    tl = v.timeline or {}
    r3 = lambda x: round(float(x), 3)
    s = secenek(v, anahtar)
    M = _marka(v)
    return {"id": v.id, "format": fmt, "w": F["w"], "h": F["h"], "fps": v.fps, "sure": r3(v.duration or 10), "nkare": v.nframes or int((v.duration or 10) * v.fps),
            "isaretler": {k: r3(t) for k, t in sorted(v.cues.items())},
            "vuruslar": [{"id": x["id"], "step": x["step"], "start": r3(x["start"]), "end": r3(x["end"])} for x in tl.get("sentences", [])],
            "kelimeler": [{"t": w["text"], "s": r3(w["start"]), "e": r3(w["end"]), "v": x["id"]} for x in tl.get("sentences", []) for w in x.get("words", [])],
            "beats": [r3(b) for b in tl.get("beats", [])], "guvenli": F["guvenli"], "altyazi": F["altyazi"],
            "gorunus": s, "renk": dict((s or {}).get("renk") or {}), "marka": (M or {}).get("renk"), "tohum": tohum(v),
            # planda üç yol: sahne seçeneğin harfine göre dallanır (ST.secenek). Yolsuz filmde alan yok: parmak izi ve plakalar değişmez.
            **({"secenek": v.secenek_harfi(anahtar)} if v.yollu else {}),
            # canlı veri: seçili anlık görüntü (ST.veri); parmak izine girer: görüntü değişince yalnız o filmin plakaları yeniden çizilir
            **_veri(v),
            # kamera takibi: seçili dondurulmuş çözüm (ST.takip: yol + sha256); yalnız takip filminde (öteki filmlerin verisi aynı)
            **_takip(v),
            # karma filmin sahnesi (6b, pipeline/plaka.py): yerel pencere (ST.sahne); yalnız sahne verisinde (öteki filmlerin parmak izi aynı)
            **({"sahne": v.script["_sahne"]} if v.script.get("_sahne") else {})}


def _takip(v) -> dict:
    import takip
    t = takip.st_verisi(v)
    return {"takip": t} if t else {}


def _veri(v) -> dict:
    import veri
    c = veri.cizim(v) if veri.var_mi(v) else None
    return {"veri": c} if c else {}


def kaynaklar(v) -> list[Path]:
    """Sahnenin kaynak dosyaları (parmak izi ve kaba kurgunun tazeliği için): blender/<id>/ + kit (+ EEVEE filminde eevee/,
    takip filminde blender/takip/__init__.py: sahnenin modülü; çözücü coz.py plakaya girmez, çözümün kendisi sha256'sıyla veride)."""
    out = []
    for d in (klasor(v), KIT) + ((EEVEE,) if cizer(v) == "eevee" else ()):
        if d.exists():
            out += [p for p in sorted(d.rglob("*")) if p.is_file() and not (set(p.relative_to(d).parts) & DISARIDA)
                    and p.suffix not in (".blend1", ".pyc")]
    if _takip(v):
        out.append(TAKIP / "__init__.py")
    return out


def parmak_izi(v, fmt: str, kalite_ad: str, anahtar: str | None = None) -> tuple[str, dict, dict]:
    """(küme adı, veri, kalite). Küme adı: <format>-<kalite>-<özet>; özet sahnenin, kitin, verinin, kalitenin ve Blender sürümünün özetidir."""
    V = veri(v, fmt, anahtar)
    K = kalite(v, kalite_ad)
    h = hashlib.sha256()
    h.update(f"blender {surum(v)}\n".encode())
    if cizer(v) != "cycles":   # Cycles filminin özeti eskisiyle aynı kalır (küme adları ve plakalar değişmez)
        h.update(f"cizer {cizer(v)}\n".encode())
    vd = v.pub / "varliklar"
    for p in kaynaklar(v) + (sorted(x for x in vd.rglob("*") if x.is_file() and x.name != ".DS_Store") if vd.exists() else []):
        h.update(str(p.relative_to(O.ROOT)).encode() + b"\0" + p.read_bytes() + b"\0")
    h.update(json.dumps(V, sort_keys=True, ensure_ascii=False).encode())
    h.update(json.dumps(K, sort_keys=True).encode())
    return f"{fmt}-{kalite_ad}-{h.hexdigest()[:12]}", V, K


# ---------------------------------------------------------------- eşitleme ve plakalar
def esitle(v):
    """Remotion'un plakaları görmesi: public/<id>/plaka → out/_plaka/<id> (göreli bağlantı) + plaka.json (varsayılan kümeler)."""
    if not (klasor(v) / "sahne.py").exists():
        raise SystemExit(f"{v.id}: blender/{v.id}/sahne.py yok (yeni Blender videosu: ./st yeni {v.id} \"Başlık\" --motor blender)")
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
    if not pj.exists():
        pj.write_text("{}\n")


def _varsayilan_yaz(v, fmt, kalite_ad, kume):
    pj = v.pub / "plaka.json"
    P = O.jload(pj) if pj.exists() else {}
    if P.get(fmt, {}).get(kalite_ad) != kume:
        P.setdefault(fmt, {})[kalite_ad] = kume
        pj.write_text(json.dumps(P, indent=1, sort_keys=True) + "\n")


def bos_bellek_gb() -> float:
    """Boş + geri alınabilir bellek (GB). Çizimden önce bakılır: Cycles + büyük sahne ~3 GB ister."""
    try:
        s = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
        sayfa = int(re.search(r"page size of (\d+)", s).group(1))
        n = sum(int(re.search(rf"{k}:\s+(\d+)", s).group(1)) for k in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable"))
        return n * sayfa / 2 ** 30
    except Exception:
        return -1.0


def _bellek_uyar():
    gb = bos_bellek_gb()
    if 0 <= gb < 3.5:
        print(f"⚠️  Boş bellek az: {gb:.1f} GB. Blender çizimi takasa düşüp çok yavaşlayabilir. Büyük uygulamaları (ör. Unreal Editor) "
              "kapatmak hızlandırır; stüdyo hiçbir uygulamayı kendisi kapatmaz.", flush=True)
    return gb


def _calistir(sahne: Path, V: dict, K: dict, ek: list, etiket: str, ilerleme=None, beklenen: str = SURUM, cizer_: str = "cycles",
              ortam: dict | None = None) -> dict:
    """Blender'ı (arka planda) kitin çalıştırıcısıyla başlatır. ST_ satırlarını okur; hata olursa son çıktıyı gösterir.
    EEVEE: çalıştırıcı sahne yerine sarmalayıcıyı (eevee/sahne.py) çalıştırır, asıl sahne ST_SAHNE'de; her işin ilk karesi iki kez çizilir.
    ortam: ek ortam değişkenleri (yapım sarmalayıcısı: ST_SAHNE, ST_YAPIM_KIP)."""
    surum_denetle(beklenen)
    env, isinma = ({**os.environ, **ortam} if ortam else None), False
    if cizer_ == "eevee":
        env = {**os.environ, **(ortam or {}), "ST_SAHNE": str(sahne)}   # karma filmin saydam sahnesi: ST_KARMA_SAHNE de geçer
        sahne = EEVEE / "sahne.py"
        # Isınma: EEVEE bir işlemin İLK çizimini gölge haritaları dolmadan çiziyor (kil kampta çadırda 29/255, piksellerin %4'ü;
        # ikinci çizimden sonra aynı işlemde ≤ 1/255). İlk kare bir kez boşa çizilir, plakası ikinci çizimle yazılır (denemeler/blender_eevee/OKU.md).
        if "--kareler" in ek and ek[ek.index("--kareler") + 1]:
            i = ek.index("--kareler") + 1
            ek, isinma = ek[:i] + [ek[i].split(",")[0] + "," + ek[i]] + ek[i + 1:], True
    with tempfile.NamedTemporaryFile("w", suffix=".json", prefix="st_veri_", delete=False) as f:
        json.dump(V, f, ensure_ascii=False)
        vyol = f.name
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", str(CALISTIR), "--",
           "--sahne", str(sahne), "--veri", vyol, "--kalite", json.dumps(K)] + ek
    son, ozet = [], {"kareler": []}
    try:
        p = subprocess.Popen(cmd, cwd=O.ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        for ln in p.stdout:
            son = (son + [ln.rstrip()])[-60:]
            if ln.startswith("ST_"):
                e, _, js = ln.partition(" ")
                d = json.loads(js)
                if e == "ST_KARE":
                    if isinma:   # ısınma çizimi: sayılmaz, plakası ikinci çizimle değişti
                        isinma = False
                        ozet["isinma_sn"] = d["sn"]
                        continue
                    ozet["kareler"].append(d)
                    if ilerleme:
                        ilerleme(d)
                else:
                    ozet[e[3:].lower()] = d
        p.wait()
    finally:
        os.unlink(vyol)
    if p.returncode:
        hata = "\n".join(x for x in son if x and not x.startswith("Fra:"))[-3000:]
        raise SystemExit(f"Blender {etiket} başarısız (çıkış {p.returncode}):\n{hata}")
    return ozet


def plakalar(v, frames, fmt: str, kalite_ad: str = "taslak", anahtar: str | None = None) -> tuple[str, dict[int, Path]]:
    """İstenen karelerin plakaları (önbellekten ya da çizilerek) → (küme adı, {kare: yol}).
    anahtar: görünüş seçeneği (görünüş denemesi); yoksa seçili görünüş ve plaka.json'daki varsayılan güncellenir."""
    esitle(v)
    kume, V, K = parmak_izi(v, fmt, kalite_ad, anahtar)
    cz = cizer(v)
    d = ONBELLEK / v.id / kume
    d.mkdir(parents=True, exist_ok=True)
    n = V["nkare"]
    fr = sorted({min(n - 1, max(0, int(f))) for f in frames})
    eksik = [f for f in fr if not (d / f"p{f:05d}.png").exists()]
    if eksik:
        bilgi = d / "bilgi.json"
        if not bilgi.exists():
            bilgi.write_text(json.dumps({"video": v.id, "format": fmt, "kalite": kalite_ad, "kalite_ayar": K, "blender": surum(v), "cizer": cz,
                                         "gorunus": anahtar or (v.gorunus_json() or {}).get("secim"), "olusturma": time.strftime("%Y-%m-%d %H:%M"),
                                         "kaynaklar": [str(p.relative_to(O.ROOT)) for p in kaynaklar(v)]}, ensure_ascii=False, indent=1) + "\n")
        kilit_yolu = ONBELLEK / ".kilit"
        with open(kilit_yolu, "w") as kilit:
            try:
                fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:   # 16 GB'ta iki Cycles işi birlikte takasa düşer: ikinci iş sırada bekler
                print("→ Blender başka bir çizimde; sıra bekleniyor…", flush=True)
                fcntl.flock(kilit, fcntl.LOCK_EX)
            eksik = [f for f in eksik if not (d / f"p{f:05d}.png").exists()]  # beklerken çizilmiş olabilir
            gb = _bellek_uyar()
            t0, yapilan = time.time(), [0]
            tahmin = tahmini_sure(v, kalite_ad, len(eksik))
            print(f"→ Blender {surum(v)} · {cz}: {len(eksik)} plaka çizilecek [{fmt} · {kalite_ad} · {K['olcek']}% · {K['ornek']} örnek] · küme {kume}"
                  f" · önbellekte {len(fr) - len(eksik)} · boş bellek {gb:.1f} GB · tahmini ~{tahmin / 60:.1f} dk", flush=True)

            def durum_yaz(kalan):
                (ONBELLEK / v.id / "durum.json").write_text(json.dumps({"kume": kume, "cizer": cz, "yapilan": yapilan[0], "toplam": len(eksik),
                                                                        "kalan_sn": round(kalan), "zaman": time.strftime("%H:%M:%S")}) + "\n")

            def ilerleme(k):
                yapilan[0] += 1
                gecen = time.time() - t0
                kalan = gecen / yapilan[0] * (len(eksik) - yapilan[0])
                print(f"   plaka {yapilan[0]}/{len(eksik)} · f{k['f']} {k['sn']:.1f} sn · kalan ~{kalan / 60:.1f} dk", flush=True)
                durum_yaz(kalan)

            durum_yaz(tahmin)   # ilk plaka çıkana dek (sahne kurulumu, EEVEE'de gölgelendirici derlemesi) çizerin tipik hızıyla

            try:
                for i in range(0, len(eksik), PARCA):
                    parca = eksik[i:i + PARCA]
                    oz = _calistir(klasor(v) / "sahne.py", V, K, ["--cikti", str(d), "--kareler", ",".join(map(str, parca))],
                                   f"plaka ({fmt}, {kalite_ad})", ilerleme, surum(v), cz)
                    b = oz.get("basla", {})
                    print(f"   iş {i // PARCA + 1}/{-(-len(eksik) // PARCA)}: kurulum {b.get('kurulum_sn', 0):.1f} sn · {b.get('cihaz', '')} · "
                          f"bellek tepe {max([k['bellek_gb'] for k in oz['kareler']] or [0]):.1f} GB", flush=True)
            finally:
                (ONBELLEK / v.id / "durum.json").unlink(missing_ok=True)
            if eksik:
                sure = time.time() - t0
                print(f"   {len(eksik)} plaka {sure / 60:.1f} dk ({sure / len(eksik):.1f} sn/kare, kurulum dahil)", flush=True)
        _temizle(v, kume)
    if anahtar is None:
        _varsayilan_yaz(v, fmt, kalite_ad, kume)
    return kume, {f: d / f"p{f:05d}.png" for f in fr}


# ---------------------------------------------------------------- yapım filmi geçişleri (./st yapim; blender/yapim/)
YAPIM = KOK / "yapim"
YAPIM_KIPLERI = ("kil", "tel", "ust")
YAPIM_KALITE = {"olcek": 50, "aa": 16, "ornek": 16}   # yarım çözünürlük (taslak plakalarla yan yana); ornek: tel kafesin EEVEE örneği
SURE_YAPIM = 0.5                          # sn/kare, ilk tahmin (Workbench; ölçülünce düzelir)


def yapim_kume(v, fmt: str, kip: str) -> tuple[str, dict, dict]:
    """Yapım geçişinin küme adı: <format>-yapim_<kip>-<özet>. Özet filmin taslak/tam parmak izinin girdileri (sahne, kit, varlıklar, veri;
    EEVEE filminde eevee/) + blender/yapim/ + kip. Bu küme filmin taslak ve tam kümelerine dokunmaz: adları ve parmak izleri değişmez,
    temizlik (en yeni 4) grup başına (<format>-yapim_<kip>) ayrı yürür."""
    if kip not in YAPIM_KIPLERI:
        raise SystemExit(f"Yapım kipi yok: {kip} ({' | '.join(YAPIM_KIPLERI)})")
    V = veri(v, fmt)
    K = {**YAPIM_KALITE, "kip": kip}
    h = hashlib.sha256()
    h.update(f"blender {surum(v)}\nyapim {kip}\ncizer {cizer(v)}\n".encode())
    vd = v.pub / "varliklar"
    yk = [p for p in sorted(YAPIM.rglob("*")) if p.is_file() and not (set(p.relative_to(YAPIM).parts) & DISARIDA) and p.suffix != ".pyc"]
    for p in kaynaklar(v) + yk + (sorted(x for x in vd.rglob("*") if x.is_file() and x.name != ".DS_Store") if vd.exists() else []):
        h.update(str(p.relative_to(O.ROOT)).encode() + b"\0" + p.read_bytes() + b"\0")
    h.update(json.dumps(V, sort_keys=True, ensure_ascii=False).encode())
    h.update(json.dumps(K, sort_keys=True).encode())
    return f"{fmt}-yapim_{kip}-{h.hexdigest()[:12]}", V, K


def yapim_plakalari(v, frames, fmt: str, kip: str) -> tuple[str, dict[int, Path]]:
    """Yapım filmi için Blender geçişi (kil, tel kafes, kamera yolu): istenen karelerin plakaları önbellekten ya da Workbench ile çizilerek
    → (küme adı, {kare: yol}). Filmin plaka.json'ına (Remotion'un varsayılan kümeleri) yazılmaz."""
    esitle(v)
    kume, V, K = yapim_kume(v, fmt, kip)
    d = ONBELLEK / v.id / kume
    d.mkdir(parents=True, exist_ok=True)
    n = V["nkare"]
    fr = sorted({min(n - 1, max(0, int(f))) for f in frames})
    eksik = [f for f in fr if not (d / f"p{f:05d}.png").exists()]
    if eksik:
        bilgi = d / "bilgi.json"
        if not bilgi.exists():
            bilgi.write_text(json.dumps({"video": v.id, "format": fmt, "yapim": kip, "kalite_ayar": K, "blender": surum(v), "cizer": "workbench",
                                         "olusturma": time.strftime("%Y-%m-%d %H:%M"),
                                         "kaynaklar": [str(p.relative_to(O.ROOT)) for p in kaynaklar(v)]}, ensure_ascii=False, indent=1) + "\n")
        with open(ONBELLEK / ".kilit", "w") as kilit:
            try:
                fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("→ Blender başka bir çizimde; sıra bekleniyor…", flush=True)
                fcntl.flock(kilit, fcntl.LOCK_EX)
            eksik = [f for f in eksik if not (d / f"p{f:05d}.png").exists()]
            _bellek_uyar()
            t0, yapilan = time.time(), [0]
            print(f"→ Blender {surum(v)} · Workbench · yapım geçişi «{kip}»: {len(eksik)} plaka [{fmt} · {K['olcek']}%] · küme {kume}", flush=True)

            def ilerleme(k):
                yapilan[0] += 1
                if yapilan[0] % 10 == 0 or yapilan[0] == len(eksik):
                    print(f"   {kip} {yapilan[0]}/{len(eksik)} · f{k['f']} {k['sn']:.2f} sn", flush=True)

            ortam = {"ST_SAHNE": str(klasor(v) / "sahne.py"), "ST_YAPIM_KIP": kip, "ST_CIZER": cizer(v)}
            for i in range(0, len(eksik), PARCA):
                parca = eksik[i:i + PARCA]
                _calistir(YAPIM / "sahne.py", V, K, ["--cikti", str(d), "--kareler", ",".join(map(str, parca))],
                          f"yapım geçişi ({kip}, {fmt})", ilerleme, surum(v), "cycles", ortam)
            sure = time.time() - t0
            print(f"   {len(eksik)} plaka {sure:.0f} sn ({sure / len(eksik):.2f} sn/kare, kurulum dahil)", flush=True)
        _temizle(v, kume)
    return kume, {f: d / f"p{f:05d}.png" for f in fr}


def yapim_yeniden_ciz(v, fmt: str, kip: str, kareler_: list[int]) -> list[str]:
    """Yapım geçişinin deterministikliği: önbellekteki plakalar ayrı bir Blender işleminde yeniden çizilir (Workbench toleransı: Cycles'ınki)."""
    import numpy as np
    from PIL import Image
    kume, V, K = yapim_kume(v, fmt, kip)
    d = ONBELLEK / v.id / kume
    sec = [f for f in kareler_ if (d / f"p{f:05d}.png").exists()]
    if not sec:
        return [f"⏸ [{fmt}] yapım geçişi «{kip}» önbellekte yok"]
    satir = []
    with tempfile.TemporaryDirectory(prefix="st_yapim_") as tmp:
        _calistir(YAPIM / "sahne.py", V, K, ["--cikti", tmp, "--kareler", ",".join(map(str, sec))], f"yapım yeniden çizim ({kip})", beklenen=surum(v),
                  ortam={"ST_SAHNE": str(klasor(v) / "sahne.py"), "ST_YAPIM_KIP": kip, "ST_CIZER": cizer(v)})
        for f in sec:
            a = np.asarray(Image.open(d / f"p{f:05d}.png").convert("RGB")).astype(np.int16)
            b = np.asarray(Image.open(Path(tmp) / f"p{f:05d}.png").convert("RGB")).astype(np.int16)
            fark = np.abs(a - b).max(-1)
            eb, oran = int(fark.max()), float((fark > TOLERANS["esik"]).mean())
            ok = eb <= TOLERANS["en_buyuk"] and oran <= TOLERANS["oran"]
            satir.append(f"{'✅' if ok else '❌'} [{fmt}] yapım «{kip}» f{f} ayrı işlemde yeniden çizildi: en büyük fark {eb}/255, farklı piksel "
                         f"(> {TOLERANS['esik']}/255) %{oran * 100:.4f} (tolerans ≤ {TOLERANS['en_buyuk']}/255, ≤ %{TOLERANS['oran'] * 100:g})")
    return satir


def tahmini_sure(v, kalite_ad: str, n: int) -> float:
    """n plakanın tahmini çizim süresi (sn): çizerin tipik hızı × n + iş başına açılış (SURE, ACILIS; M4'te kil kampla ölçüldü)."""
    cz = cizer(v)
    return SURE[(cz, kalite_ad)] * n + ACILIS[cz] * -(-n // PARCA)


def _temizle(v, korunan: str):
    """Her (format, kalite) için en yeni TUT kümeyi saklar; eskiler (kod değişince bayatlayan plakalar) silinir."""
    d = ONBELLEK / v.id
    on = korunan.rsplit("-", 1)[0]
    kumeler = sorted((p for p in d.iterdir() if p.is_dir() and p.name.rsplit("-", 1)[0] == on), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in kumeler[TUT:]:
        if p.name != korunan:
            shutil.rmtree(p, ignore_errors=True)


def hazirla(v, frames, fmt: str, props: dict | None) -> dict:
    """render_frames için: plakaları hazırlar, Remotion'a verilecek props'u döndürür ({plaka: küme} + görünüş)."""
    props = dict(props or {})
    kalite_ad = props.pop("kalite", "taslak")
    kume, _ = plakalar(v, frames, fmt, kalite_ad, props.get("gorunus"))
    return {**props, "plaka": kume}


def video(v, fmt: str, hedef: Path, final=False):
    """Bütün plakalar (kaba kurgu: taslak; teslim: tam) → Remotion üst katmanı (Bitis, yazı, ses) → MP4."""
    kume, _ = plakalar(v, range(v.nframes), fmt, "tam" if final else "taslak")
    ayar = ["--codec=h264", "--crf=17", "--audio-bitrate=320k"] if final else ["--codec=h264", "--crf=26", "--scale=0.5"]
    cmd = ["npx", "remotion", "render", "src/index.ts", v.comp_for(fmt), str(hedef), *ayar, "--props", json.dumps({"plaka": kume, **_veri(v)}, ensure_ascii=False),
           "--log=error"]  # canlı veri filminde üst katmana seçili görüntü (props.veri); öteki filmlerin props'u aynı
    print("→", " ".join(cmd)[:200], flush=True)
    subprocess.run(cmd, cwd=O.ROOT, check=True)


# ---------------------------------------------------------------- denetim
YASAK = [
    (re.compile(r"(?<![\w.])random\.(random|uniform|randint|randrange|choice|choices|shuffle|gauss|sample|normalvariate|seed)\("),
     "tohumsuz random (modül düzeyi): kit.rastgele(n) ya da random.Random(tohum) kullan"),
    (re.compile(r"\bnp\.random\.(?!default_rng\(\s*\d)|\bnumpy\.random\.(?!default_rng\(\s*\d)"), "tohumsuz numpy.random: np.random.default_rng(tohum)"),
    (re.compile(r"\b(time\.time|time\.perf_counter|time\.monotonic|datetime\.|os\.urandom|uuid\.)"), "saat ya da sistem rastgeleliği: kare t'nin saf fonksiyonu olmalı"),
    (re.compile(r"\brandom\.Random\(\s*\)"), "tohumsuz random.Random()"),
    (re.compile(r"\bframe_change_(pre|post)\b|\bapp\.handlers\b"), "kare işleyicisi (handler): anahtar kare ya da sürücü kullan; işleyici sırayla çalışır"),
]
FIZIK = re.compile(r"\b(rigidbody|rigid_body|RIGID_BODY|CLOTH|SOFT_BODY|FLUID|DYNAMIC_PAINT|particle_system|PARTICLE_SYSTEM|point_cache)\b")
PISIRME = re.compile(r"\bbake\b|ptcache\.bake|pisir_fizik")


def tara(v) -> list[str]:
    """Sahne kodunda tohumsuz rastgelelik, saat, kare işleyicisi ve pişirilmemiş fizik (ayrı işlemlerde aynı kareyi vermez)."""
    hits = []
    for p in kaynaklar(v):
        if p.suffix != ".py" or KIT in p.parents or TAKIP in p.parents:   # stüdyonun kodu (kit, takip modülü) taranmaz; sahne taranır
            continue
        metin = p.read_text()
        for i, ln in enumerate(metin.splitlines(), 1):
            kod = ln.split("#", 1)[0]
            for pat, neden in YASAK:
                if pat.search(kod):
                    hits.append(f"{p.relative_to(O.ROOT)}:{i}: {neden}: {ln.strip()[:80]}")
        if FIZIK.search(metin) and not PISIRME.search(metin):
            hits.append(f"{p.relative_to(O.ROOT)}: fizik benzetimi var ama pişirme yok: 30 karelik her iş benzetimi baştan kurar; "
                        "önce pişir (point_cache bake) ya da hareketi anahtar kareye çevir")
    return hits


def denetle(v) -> int:
    """./st tip: sahne kodu taraması + her format için kuru kurulum (Blender sahneyi kurar, çizmez) + üst katmanın TypeScript'i."""
    esitle(v)
    kotu = 0
    hits = tara(v)
    print("✅ sahne kodunda gizli saat / tohumsuz rastgelelik / pişirilmemiş fizik yok" if not hits else "❌ sahne kodu:\n  " + "\n  ".join(hits))
    kotu += bool(hits)
    for fmt in v.formatlar:
        _, V, K = parmak_izi(v, fmt, "taslak")
        oz = _calistir(klasor(v) / "sahne.py", V, K, ["--kuru"], f"kuru kurulum ({fmt})", beklenen=surum(v), cizer_=cizer(v))
        k = oz.get("kuru", {})
        print(f"✅ [{fmt}] sahne kuruldu: {k.get('nesne')} nesne · {k.get('isik')} ışık · {k.get('ucgen', 0):,} üçgen · kurulum {k.get('kurulum_sn')} sn · "
              f"bellek {k.get('bellek_gb')} GB · {k.get('motor')}".replace(",", "."))
    r = subprocess.run(["npx", "tsc", "--noEmit", "-p", "."], cwd=O.ROOT, capture_output=True, text=True)
    print("✅ üst katman (TypeScript) temiz" if r.returncode == 0 else (r.stdout + r.stderr)[-3000:])
    kotu += r.returncode != 0
    return kotu


def yeniden_ciz(v, fmt: str, sayi: int = 2) -> list[str]:
    """Deterministiklik (Blender tarafı): önbellekteki plakalardan birkaçı ayrı bir işlemde yeniden çizilir ve karşılaştırılır.
    Önce tam kalitedeki güncel küme (temsilî kareler) denenir, yoksa taslak. Tolerans: çizerin (TOLERANS, TOLERANS_EEVEE). → satırlar (✅/❌ ...)."""
    import numpy as np
    from PIL import Image
    satir = []
    for kalite_ad in ("tam", "taslak"):
        kume, V, K = parmak_izi(v, fmt, kalite_ad)
        d = ONBELLEK / v.id / kume
        var = sorted(int(p.stem[1:]) for p in d.glob("p*.png")) if d.exists() else []
        if var:
            break
    else:
        return [f"⏸ [{fmt}] önbellekte güncel plaka yok: önce ./st kare / ./st inceleme"]
    sec = sorted({var[len(var) // 2], var[-1], var[0]})[:sayi] if len(var) > 1 else var
    with tempfile.TemporaryDirectory(prefix="st_plaka_") as tmp:
        t0 = time.time()
        _calistir(klasor(v) / "sahne.py", V, K, ["--cikti", tmp, "--kareler", ",".join(map(str, sec))], f"yeniden çizim ({fmt})", beklenen=surum(v),
                  cizer_=cizer(v))
        T = tolerans(v)
        for f in sec:
            a = np.asarray(Image.open(d / f"p{f:05d}.png").convert("RGB")).astype(np.int16)
            b = np.asarray(Image.open(Path(tmp) / f"p{f:05d}.png").convert("RGB")).astype(np.int16)
            fark = np.abs(a - b).max(-1)
            esik = T.get("esik", 0)   # EEVEE: 1/255'lik sayısal gürültü sayılmaz
            eb, oran = int(fark.max()), float((fark > esik).mean())
            ok = eb <= T["en_buyuk"] and oran <= T["oran"]
            satir.append(f"{'✅' if ok else '❌'} [{fmt}] f{f} ({kalite_ad} · {cizer(v)}) ayrı işlemde yeniden çizildi: en büyük fark {eb}/255, "
                         f"farklı piksel{f' (> {esik}/255)' if esik else ''} %{oran * 100:.4f} (tolerans ≤ {T['en_buyuk']}/255, ≤ %{T['oran'] * 100:g})")
            # kamera takibi: Remotion'un birleştirdiği katmanlar (nesne RGBA, gölge, yansıma; Blender kare numarasıyla f + 1) aynı tolerans
            for harf, ad in (("n", "nesne"), ("g", "gölge"), ("y", "yansıma")):
                ka, kb = d / f"{harf}{f + 1:05d}.png", Path(tmp) / f"{harf}{f + 1:05d}.png"
                if not (ka.exists() and kb.exists()):
                    continue
                a = np.asarray(Image.open(ka).convert("RGBA")).astype(np.int16)
                b = np.asarray(Image.open(kb).convert("RGBA")).astype(np.int16)
                fark = np.abs(a - b).max(-1)
                eb, oran = int(fark.max()), float((fark > esik).mean())
                ok = eb <= T["en_buyuk"] and oran <= T["oran"]
                satir.append(f"{'✅' if ok else '❌'} [{fmt}] f{f} {ad} katmanı ({harf}{f + 1:05d}): en büyük fark {eb}/255, farklı piksel %{oran * 100:.4f}")
        satir.append(f"   yeniden çizim {time.time() - t0:.0f} sn · küme {kume}")
    return satir


# ---------------------------------------------------------------- iskelet, arayüz, durum
def yeni(vid: str, baslik: str, fmt: str):
    """blender/<id>/sahne.py iskeleti (sablon/blender/sahne.py)."""
    d = KOK / vid
    d.mkdir(parents=True, exist_ok=False)
    t = (SABLON / "sahne.py").read_text().replace("{{ID}}", vid).replace("{{BASLIK}}", baslik).replace("{{FORMAT}}", fmt)
    (d / "sahne.py").write_text(t)


def ac(v, fmt: str | None = None):
    """Sahneyi Blender arayüzünde açar (seçili görünüş, ilk format): ışığı, kadrajı elle incelemek için. Kaydedilen .blend stüdyonun değildir:
    değişiklik sahne.py'ye yazılır."""
    esitle(v)
    fmt = fmt or v.formatlar[0]
    surum_denetle(surum(v))
    V = veri(v, fmt)
    yol = ONBELLEK / v.id / f"veri-{fmt}.json"
    yol.write_text(json.dumps(V, ensure_ascii=False))
    sahne, env = klasor(v) / "sahne.py", None
    if cizer(v) == "eevee":   # EEVEE filmi arayüzde de EEVEE ayarlarıyla açılır (sarmalayıcı, _calistir'deki gibi)
        sahne, env = EEVEE / "sahne.py", {**os.environ, "ST_SAHNE": str(sahne)}
    cmd = [BLENDER, "--factory-startup", "--python", str(CALISTIR), "--", "--sahne", str(sahne), "--veri", str(yol),
           "--kalite", json.dumps(kalite(v, "taslak")), "--ac"]
    subprocess.Popen(cmd, cwd=O.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, env=env)
    print(f"Blender açılıyor: {v.id} · {fmt} · {cizer(v)} · görünüş {(v.gorunus_json() or {}).get('secim') or '—'} (kamera görünümü; çizim için F12)")


def durum(v):
    esitle(v)
    import veri
    dm = veri.damga(v)
    print(f"■ {v.id} · Blender {surum(v)} · çizer {cizer(v)} · {BLENDER} · boş bellek {bos_bellek_gb():.1f} GB · {v.nframes} kare" + (f" · {dm}" if dm else ""))
    for fmt in v.formatlar:
        for kalite_ad in KALITE:
            kume, _, K = parmak_izi(v, fmt, kalite_ad)
            d = ONBELLEK / v.id / kume
            n = len(list(d.glob("p*.png"))) if d.exists() else 0
            eksik = v.nframes - n
            print(f"  [{fmt} · {kalite_ad}] güncel küme {kume}: {n}/{v.nframes} plaka" + (" ✅" if n >= v.nframes else
                  f" · eksikler ~{tahmini_sure(v, kalite_ad, eksik) / 60:.0f} dk"))
    kumeler = [p for p in (ONBELLEK / v.id).iterdir() if p.is_dir()]
    boyut = sum(f.stat().st_size for p in kumeler for f in p.glob("*.png"))
    print(f"  önbellek: {len(kumeler)} küme · {boyut / 2 ** 20:.0f} MB (out/_plaka/{v.id}; eskiler kendiliğinden silinir, en yeni {TUT} tutulur)")
    dj = ONBELLEK / v.id / "durum.json"
    if dj.exists():
        print(f"  çizim sürüyor: {dj.read_text().strip()}")


# ---------------------------------------------------------------- katalog
def _katalog_veri(ad: str, secenek_: dict, fps: int, sure: float, fmt: str = "1x1") -> dict:
    F = O.FORMATLAR[fmt]
    return {"id": ad, "format": fmt, "w": F["w"], "h": F["h"], "fps": fps, "sure": sure, "nkare": int(round(sure * fps)), "isaretler": {},
            "vuruslar": [], "kelimeler": [], "beats": [], "guvenli": F["guvenli"], "altyazi": F["altyazi"], "gorunus": secenek_,
            "renk": dict(secenek_.get("renk") or {}), "marka": None, "tohum": 1}


def katalog_demo(dizin: Path, secenek_: dict, mp4: Path, kareler_: dict[int, Path], fps=30, sure=3.0, fmt="1x1"):
    """Katalog örneği Blender'da (animasyon tipinin tekniği katalog/animasyon/blender/<ad>/sahne.py, motor önizlemesi katalog/motor/blender/sahne.py):
    3 sn, taslak kalite. Plakalar Blender'dan, video ffmpeg ile (üst katman yok: örnek yalnız hareketi, ışığı ve malzemeyi gösterir)."""
    V = _katalog_veri(dizin.name, secenek_, fps, sure, fmt)
    n = V["nkare"]
    tmp = mp4.parent / "_blender_kare"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for i in range(0, n, PARCA):
        _calistir(dizin / "sahne.py", V, KALITE["taslak"], ["--cikti", str(tmp), "--kareler", ",".join(map(str, range(i, min(n, i + PARCA))))],
                  f"katalog örneği ({dizin.name})")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(tmp / "p%05d.png"), "-c:v", "libx264", "-crf", "18",
                    "-pix_fmt", "yuv420p", str(mp4)], check=True)
    for f, hedef in kareler_.items():
        shutil.copy2(tmp / f"p{min(n - 1, f):05d}.png", hedef)
    shutil.rmtree(tmp, ignore_errors=True)


def katalog_kareler(sahne: Path, secenekler: dict[str, dict], kare: int, hedefler: dict[str, Path], fps=30, sure=3.0):
    """Katalog görüntü stilinin önizlemesi: aynı maket sahnesinin tek karesi her varyasyonun renk ve ışığıyla (taslak, 1x1 → 540 px)."""
    for k, sec in secenekler.items():
        with tempfile.TemporaryDirectory(prefix="st_katalog_") as tmp:
            _calistir(sahne, _katalog_veri(sahne.parent.name, sec, fps, sure), KALITE["taslak"], ["--cikti", tmp, "--kareler", str(kare)],
                      f"görüntü stili önizlemesi ({sahne.parent.name} · {k})")
            shutil.copy2(Path(tmp) / f"p{kare:05d}.png", hedefler[k])


def katalog_cizer(sahne: Path, hedefler: dict[str, Path], kare=45, fps=30, sure=3.0) -> dict[str, float]:
    """Çizer seçiminin önizlemesi (yeni film levhası): aynı sahnenin aynı karesi her çizerle, teslim kalitesinde (9x16). → {çizer: sn/kare}"""
    V = _katalog_veri(sahne.parent.name, {}, fps, sure, "9x16")
    sn = {}
    for c, hedef in hedefler.items():
        K = (KALITE_EEVEE if c == "eevee" else KALITE)["tam"]
        with tempfile.TemporaryDirectory(prefix="st_cizer_") as tmp:
            oz = _calistir(sahne, V, K, ["--cikti", tmp, "--kareler", str(kare)], f"çizer önizlemesi ({c})", cizer_=c)
            shutil.copy2(Path(tmp) / f"p{kare:05d}.png", hedef)
        sn[c] = oz["kareler"][0]["sn"]
    return sn
