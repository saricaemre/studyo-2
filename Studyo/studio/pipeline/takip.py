"""Kamera takibi (./st takip; FOOH: gerçek sokakta imkânsız nesne; zanaat §10, blender/CLAUDE.md → Kamera takibi).

Telefonla çekilmiş gerçek bir mekânın kamerası Blender'da çözülür (blender/takip/coz.py: özellik bulma, izleme, aykırı iz süzgeci, odak
araması, temizlik, zemin ve ölçek) ve bir kez dondurulur: plakalar bu dosyadan çizilir, takip her çizimde yeniden yapılmaz.

Kayıt   videos/<id>/takip/takip.json (çözümler, seçili çözüm, sha256) · her çözüm videos/<id>/takip/<ad>/: cozum.json (her kare için
        kamera matrisi, odak, bozulma, kare başına hata, zemin, ölçek, noktalar, çekimin ortalama renkleri), iz.blend (izler ve çözüm:
        elle düzeltmek için), onizleme.png (izler + 1 m'lik zemin ızgarası), hata.png (kare başına çözüm hatası)
Girdi   çekim gerçek görüntü hattından gelir (./st goruntu ekle: ara format, kişi tahmini ve rıza); <ad> o kayıttaki ad
Motor   Blender: ST.takip (pipeline/blender.py → veri; yalnız takip filminde) → blender/takip (kamera, gölge yakalayıcı zemin, katmanlar);
        Remotion: src/lib/takip (<TakipBirlesim>: çekim × gölge + yansıma + nesne)
"""
import datetime as dt
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np

import ortak as O

KOK = O.ROOT / "blender" / "takip"
COZ = KOK / "coz.py"
HEDEF_PX = 1.0                  # kabul: ortalama çözüm hatası ≤ 1 px


def _simdi():
    return dt.datetime.now().isoformat(timespec="seconds")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def depo(v) -> Path:
    return v.dir / "takip"


def yukle(v) -> dict:
    p = depo(v) / "takip.json"
    T = O.jload(p) if p.exists() else {}
    T.setdefault("cozumler", {})
    return T


def kaydet(v, T: dict):
    depo(v).mkdir(parents=True, exist_ok=True)
    (depo(v) / "takip.json").write_text(json.dumps(T, ensure_ascii=False, indent=1) + "\n")


def secili(v) -> dict | None:
    """Seçili çözümün kaydı (yoksa None: film takip filmi değildir; öteki filmlerin verisi ve parmak izi değişmez)."""
    p = depo(v) / "takip.json"
    if not p.exists():
        return None
    T = O.jload(p)
    return (T.get("cozumler") or {}).get(T.get("secili") or "")


def st_verisi(v) -> dict | None:
    """Blender sahnesine giden ST.takip (parmak izine girer: çözüm değişince yalnız bu filmin plakaları yeniden çizilir)."""
    x = secili(v)
    if not x:
        return None
    return {"ad": x["ad"], "goruntu_ad": x["goruntu"], "cozum": x["cozum"], "sha256": x["sha256"], "goruntu": x["motor"], "bas": x["bas"]}


# ---------------------------------------------------------------- çekimin ortalama renkleri (ortam ışığı için)
def _kare(p: Path, i: int, fps: float, olcek: int | None = None) -> np.ndarray:
    vf = f"select=eq(n\\,{i})" + (f",scale={olcek}:-2" if olcek else "")
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vf", vf, "-vsync", "0", "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                       capture_output=True, check=True)
    from io import BytesIO
    from PIL import Image
    return np.asarray(Image.open(BytesIO(r.stdout)).convert("RGB"))


def renkler(ara: Path, bas: int, n: int, fps: float) -> dict:
    """Gök (karenin üst %25'i) ve zemin (alt %35'i) ortalama rengi, beş karede: dünya ışığı bunlardan (blender/takip → ortam)."""
    gok, zem = [], []
    for i in np.linspace(bas, bas + n - 1, 5).round().astype(int):
        a = _kare(ara, int(i), fps, 270).astype(float)
        h = a.shape[0]
        gok.append(a[: h // 4].reshape(-1, 3).mean(0))
        zem.append(a[int(h * 0.65):].reshape(-1, 3).mean(0))
    hx = lambda c: "#" + "".join(f"{int(round(x)):02X}" for x in np.mean(c, 0))   # noqa: E731
    return {"gok": hx(gok), "zemin": hx(zem)}


# ---------------------------------------------------------------- izdüşüm (Blender kamerasıyla aynı model)
def izdusum(c: dict, i: int, P: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Dünya noktaları (N×3) → i. karede görüntü pikseli (x sağa, y aşağı) + önde mi (N)."""
    M = np.array(c["kareler"][i]["m"]).reshape(4, 4)
    R, t = M[:3, :3], M[:3, 3]
    pc = (np.asarray(P, float) - t) @ R
    z = -pc[:, 2]
    onde = z > 0.05
    z = np.where(onde, z, 1.0)
    x, y = pc[:, 0] / z, pc[:, 1] / z
    B = c["mercek"]["bozulma"]
    r2 = x * x + y * y
    d = 1 + B["k1"] * r2 + B["k2"] * r2 ** 2 + B["k3"] * r2 ** 3
    f = c["mercek"]["odak_px"]
    cx, cy = c["mercek"]["merkez_px"]
    # bozulma polinomu yalnız görüntünün içinde (ve biraz dışında) geçerli: çok dıştaki nokta geri katlanır, çizilmez
    sinir = 2.0 * ((c["klip"]["en"] / 2) ** 2 + (c["klip"]["boy"] / 2) ** 2) / f ** 2
    return np.stack([cx + f * x * d, cy - f * y * d], 1), onde & (r2 < sinir)


def _izgara(c: dict, i: int, olc: float, d, renk=(80, 200, 255, 150)):
    """1 m'lik zemin ızgarası (z = 0): dünyaya sabit (tam metrelerde), o karede kameranın 1,5–16 m önünde; kameraya 1 m'den yakın ya da
    arkasında kalan parça çizilmez (ızgara yürürken zemine yapışık kalmalı: kayıyorsa çözüm ya da zemin yanlış)."""
    M = np.array(c["kareler"][i]["m"]).reshape(4, 4)
    cy, cx = float(M[1, 3]), float(M[0, 3])
    ys = np.arange(np.floor(cy + 1.5), cy + 16.01, 1.0)
    xs = np.arange(np.floor(cx - 3), cx + 3.01, 1.0)
    cizgiler = [np.array([[x, y, 0.0] for y in np.linspace(ys[0], ys[-1], 60)]) for x in xs]
    cizgiler += [np.array([[x, y, 0.0] for x in np.linspace(xs[0], xs[-1], 30)]) for y in ys]
    R, t = M[:3, :3], M[:3, 3]
    W, H = c["klip"]["en"] * olc, c["klip"]["boy"] * olc
    for L in cizgiler:
        p, on = izdusum(c, i, L)
        derin = -((L - t) @ R)[:, 2]
        ic = on & (derin > 1.0)
        p = p * olc
        for a, b_, oa, ob in zip(p[:-1], p[1:], ic[:-1], ic[1:]):
            if oa and ob and -W < a[0] < 2 * W and -H < a[1] < 2 * H:
                d.line([tuple(a), tuple(b_)], fill=renk, width=1)


def _yazi(boy=12):
    from PIL import ImageFont
    from kontak import F_REG
    return ImageFont.truetype(F_REG, boy)


def onizleme(v, ad: str, c: dict, ara: Path, hedef: Path, kareler_: list[int] | None = None):
    """Üç karede: izlenen noktalar (renk: yeniden izdüşüm hatası ≤ 1 px yeşil, ≤ 2 px sarı, büyük kırmızı) ve 1 m'lik zemin ızgarası
    (ölçeğin ve zeminin görsel denetimi: kareler yolda 1 m görünmeli, ızgara yürürken zemine yapışık kalmalı)."""
    from PIL import Image, ImageDraw
    n = c["klip"]["n"]
    kareler_ = kareler_ or [0, n // 2, n - 1]
    W, H = c["klip"]["en"], c["klip"]["boy"]
    olc = 360 / W
    pts = c["noktalar"]
    out = []
    for i in kareler_:
        im = Image.fromarray(_kare(ara, c["klip"]["bas"] + i, c["klip"]["fps"])).resize((360, int(round(H * olc))), Image.LANCZOS)
        d = ImageDraw.Draw(im, "RGBA")
        _izgara(c, i, olc, d)
        sec_ = [q for q in pts if str(i) in q["k"]]
        if sec_:
            pr, on = izdusum(c, i, np.array([q["p"] for q in sec_]))
            for q, (u, w), o in zip(sec_, pr, on):
                if not o:
                    continue
                mx, my = q["k"][str(i)]
                h = float(np.hypot(u - mx, w - my))
                renk = (60, 220, 90, 255) if h <= 1 else ((255, 210, 0, 255) if h <= 2 else (255, 60, 60, 255))
                x_, y_ = mx * olc, my * olc
                d.ellipse((x_ - 2.2, y_ - 2.2, x_ + 2.2, y_ + 2.2), outline=renk, width=1)
        d.rectangle((0, 0, 360, 20), fill=(0, 0, 0, 160))
        d.text((6, 3), f"kare {i} · hata {c['kareler'][i]['hata']:.2f} px · {c['kareler'][i]['iz']} iz", fill=(255, 255, 255, 255), font=_yazi())
        out.append(im)
    T = Image.new("RGB", (len(out) * 360 + (len(out) - 1) * 8, out[0].height), (20, 22, 28))
    for k, im in enumerate(out):
        T.paste(im, (k * 368, 0))
    T.save(hedef)


def hata_grafigi(c: dict, hedef: Path):
    """Kare başına çözüm hatası (px): yatay çizgi 1 px (kabul), kırmızı bölge 2 px'in üstü."""
    from PIL import Image, ImageDraw
    K = c["kareler"]
    W, H, pad = 720, 160, 24
    im = Image.new("RGB", (W, H), (20, 22, 28))
    d = ImageDraw.Draw(im)
    tavan = max(2.5, max(k["hata"] for k in K) * 1.1)
    yy = lambda e: H - pad - (H - 2 * pad) * min(e, tavan) / tavan   # noqa: E731
    xx = lambda i: pad + (W - 2 * pad) * i / max(1, len(K) - 1)       # noqa: E731
    d.line([(pad, yy(1.0)), (W - pad, yy(1.0))], fill=(90, 200, 120), width=1)
    d.text((W - pad - 80, yy(1.0) - 16), "1 px (hedef)", fill=(90, 200, 120), font=_yazi())
    d.line([(xx(i), yy(max(0, k["hata"]))) for i, k in enumerate(K)], fill=(240, 240, 240), width=2)
    d.text((pad, 4), f"kare başına çözüm hatası · ortalama {c['hata']['ortalama_px']:.2f} px · en kötü kare {c['hata']['en_kotu_kare']['kare']} "
           f"({c['hata']['en_kotu_kare']['hata']:.2f} px)", fill=(220, 220, 220), font=_yazi())
    im.save(hedef)


# ---------------------------------------------------------------- çözüm
def _blender(args: list[str], etiket: str, blend: Path | None = None) -> list[dict]:
    """coz.py'yi arka planda çalıştırır. blend: elle iz (iz.blend): Blender dosyayla başlatılır (klip filmiyle birlikte okunsun)."""
    import blender
    blender.surum_denetle(blender.SURUM)
    cmd = [blender.BLENDER, "-b", "--factory-startup"] + ([str(blend)] if blend else []) + ["--python-exit-code", "1", "--python", str(COZ), "--"] + args
    satirlar, son = [], []
    p = subprocess.Popen(cmd, cwd=O.ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for ln in p.stdout:
        son = (son + [ln.rstrip()])[-40:]
        if ln.startswith("ST_"):
            e, _, js = ln.partition(" ")
            d = json.loads(js)
            satirlar.append({"e": e[3:], **d})
            if e == "ST_ADIM":
                print(f"   {d['sn']:6.1f} sn · {d['metin']}", flush=True)
            elif e == "ST_IZ":
                print(f"   izleme: kare {d['kare']}/{d['toplam']} · {d['iz']} iz", flush=True)
            elif e == "ST_TEMIZLIK":
                print(f"   temizlik {d['tur'] + 1}: {d['susturulan']} işaret susturuldu, {d['silinen']} iz silindi → hata {d['hata']:.3f} px", flush=True)
    p.wait()
    if p.returncode:
        temiz = [x for x in son if x and not x.startswith(("W0000", "E0000", "Error in evaluating", "No camera", "Unable to reconstruct"))
                 and "ResidualBlock" not in x]
        neden = next((x for x in reversed(temiz) if any(k in x for k in ("çözüm", "zemin", "aralık", "kamera", "Error", "rror"))), temiz[-1] if temiz else "")
        raise SystemExit(f"kamera takibi ({etiket}) başarısız: {neden}")
    return satirlar


def coz(vid: str, kaynak: str, ad: str | None = None, bas: float | None = None, son: float | None = None, yukseklik: float = 1.5,
        odak: float | None = None, hedef: float = HEDEF_PX, elle: str | None = None, ekle_ayar: dict | None = None, olcek_yalniz: bool = False) -> dict:
    """Çekimin kamerasını çözer ve dondurur. kaynak: gerçek görüntü kaydındaki ad (./st goruntu ekle) ya da bir video dosyası
    (önce gerçek görüntü hattından eklenir: ara format, kişi tahmini, rıza). elle: "iz" (iz.blend'deki izlerle yeniden çöz) ya da
    "cozum" (iz.blend'deki elle çözümü aynen al; yalnız zemin ve ölçek). olcek_yalniz: kamera yüksekliği değişti, çözüm aynen (kayıtta elle sayılmaz)."""
    import goruntu as G
    v = O.load(vid)
    if Path(kaynak).suffix and Path(kaynak).expanduser().exists():
        e = ekle_ayar or {}
        x = G.ekle(vid, kaynak, e.get("ad"), e.get("kaynak") or "kendi", e.get("riza"), e.get("kisi"), None, None, e.get("not") or "", True)
        kaynak = x["ad"]
        v = O.load(vid)
    x = G.bul(v, kaynak)
    if x["tur"] != "video":
        raise SystemExit(f"{kaynak} bir görsel: kamera takibi video ister (paralaks veren yürüyüş, 5–10 sn)")
    if x.get("kisi") and not G.riza_tamam(x):
        print(f"⚠️ {kaynak}: görüntüde kişi var, rıza {x.get('riza')}: takip çözülür ama film Kapı 1'de bekler (./st goruntu riza)")
    ara = v.dir / x["ara"]
    fps = x["olcu"].get("fps") or v.fps
    nk = int(x["olcu"]["kare"])
    bas_k = int(round((bas or 0) * v.fps))
    son_k = int(round(son * v.fps)) - 1 if son else nk - 1
    ad = ad or kaynak
    k = depo(v) / ad
    if elle and not (k / "iz.blend").exists():
        raise SystemExit(f"elle çözüm için iz.blend yok: önce otomatik takip (./st takip {vid} {kaynak}) ya da ./st takip {vid} {ad} ac")
    ayar = {"yukseklik": yukseklik, "hedef": hedef, "bas": bas_k, "son": son_k + 1, **({"odak": odak} if odak else {})}
    print(f"→ kamera takibi: {vid} · {kaynak} · kare {bas_k}–{son_k} ({(son_k - bas_k + 1) / v.fps:.1f} sn) · kamera yüksekliği {yukseklik} m"
          + (f" · odak {odak} mm" if odak else " · odak aranacak") + (f" · elle ({elle})" if elle else ""), flush=True)
    t0 = time.time()
    gecici = k / "_yeni"
    gecici.mkdir(parents=True, exist_ok=True)
    args = ["--video", str(ara), "--cikti", str(gecici), "--ayar", json.dumps(ayar), "--blend-cikti", str(k / "_iz_yeni.blend")]
    if elle:
        args += ["--blend", str(k / "iz.blend")] + (["--elle"] if elle == "cozum" else [])
    try:
        _blender(args, kaynak, (k / "iz.blend") if elle else None)
        c = O.jload(gecici / "cozum.json")
        c["renk"] = renkler(ara, bas_k, c["klip"]["n"], fps)
        c["goruntu"] = {"ad": kaynak, "ara": x["ara"], "ara_sha256": _sha(ara), "motor": f"public/{vid}/{x['yayin']}"}
        (gecici / "cozum.json").write_text(json.dumps(c, ensure_ascii=False, separators=(",", ":")) + "\n")
        # yeni çözüm eskisinin yerine; iz.blend aynı klasörde yazıldı (çekimin göreli yolu doğru kalsın), yalnız adı değişir
        os.replace(gecici / "cozum.json", k / "cozum.json")
        if (k / "_iz_yeni.blend").exists():
            os.replace(k / "_iz_yeni.blend", k / "iz.blend")
    finally:
        for f in list(gecici.glob("*")) + list(k.glob("_iz_yeni.blend*")):
            f.unlink()
        gecici.rmdir()
    onizleme(v, ad, c, ara, k / "onizleme.png")
    hata_grafigi(c, k / "hata.png")
    T = yukle(v)
    if olcek_yalniz and ad in T["cozumler"]:
        elle = T["cozumler"][ad].get("elle")
        olcek_yalniz = False
    kayit = {"ad": ad, "goruntu": kaynak, "cozum": str((k / "cozum.json").relative_to(O.ROOT)), "sha256": _sha(k / "cozum.json"),
             "motor": f"public/{vid}/{x['yayin']}", "motor_sha256": _sha(v.pub / x["yayin"]), "bas": bas_k, "n": c["klip"]["n"],
             "hata_px": c["hata"]["ortalama_px"], "hedef_px": hedef, "odak_mm": c["mercek"]["odak_mm"], "bozulma": c["mercek"]["bozulma"],
             "zemin_nokta": c["zemin"]["nokta"], "yukseklik_m": yukseklik, "yol_m": c["olcek"]["yol_m"], "iz": c["iz"]["kullanilan"],
             "elle": None if olcek_yalniz else elle, "tarih": _simdi(), "sure_sn": round(time.time() - t0, 1),
             "onizleme": str((k / "onizleme.png").relative_to(v.dir)), "hata_grafigi": str((k / "hata.png").relative_to(v.dir))}
    T["cozumler"][ad] = kayit
    T["secili"] = T.get("secili") or ad
    kaydet(v, T)
    return {**kayit, "cozum_veri": c}


def sec(vid: str, ad: str) -> dict:
    v = O.load(vid)
    T = yukle(v)
    if ad not in T["cozumler"]:
        raise SystemExit(f"çözüm yok: {ad} (var: {', '.join(T['cozumler']) or 'yok'})")
    T["secili"] = ad
    kaydet(v, T)
    return T["cozumler"][ad]


def ac(vid: str, ad: str):
    """iz.blend'i Blender arayüzünde açar (Motion Tracking): elle iz ekle, kötüleri sil, Solve Camera; kaydet (Ctrl+S), sonra
    ./st takip <id> <ad> --elle iz (izlerle yeniden çöz) ya da --elle cozum (elle çözümü aynen al)."""
    import blender
    v = O.load(vid)
    p = depo(v) / ad / "iz.blend"
    if not p.exists():
        raise SystemExit(f"iz.blend yok: önce ./st takip {vid} <görüntü>")
    blender.surum_denetle(blender.SURUM)
    betik = ("import bpy\n"
             "for w in bpy.context.window_manager.windows:\n"
             "    for a in w.screen.areas:\n"
             "        if a.type in ('VIEW_3D', 'PROPERTIES', 'OUTLINER'):\n"
             "            a.type = 'CLIP_EDITOR'\n"
             "            a.spaces.active.clip = bpy.data.movieclips[0]\n"
             "            break\n")
    yol = depo(v) / ad / "_ac.py"
    yol.write_text(betik)
    subprocess.Popen([blender.BLENDER, str(p), "--python", str(yol)], cwd=O.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    print(f"Blender açılıyor: {p.relative_to(O.ROOT)} (Motion Tracking). Bitince kaydet (⌘S), sonra: ./st takip {vid} {ad} --elle iz "
          f"ya da --elle cozum")


# ---------------------------------------------------------------- denetim (./st tip, ./st deterministik, ölçüm)
def denetle(v) -> list[tuple[bool, str, str]]:
    """Dondurma ve kabul → [(tamam mı, ölçüt, değer)]: çözüm ve çekim sha256'sı kayıttakiyle aynı mı, hata ≤ hedef, zemin, çekim oranı formatla aynı mı."""
    x = secili(v)
    if not x:
        return []
    out = []
    p = O.ROOT / x["cozum"]
    ok = p.exists() and _sha(p) == x["sha256"]
    out.append((ok, "Kamera çözümü dondurulmuş", f"{x['cozum']} · sha256 {'aynı' if ok else 'DEĞİŞMİŞ: ./st takip yeniden çözer'}"))
    m = O.ROOT / x["motor"]
    ok = m.exists() and _sha(m) == x["motor_sha256"]
    out.append((ok, "Takip edilen çekim değişmemiş", x["motor"] + ("" if ok else ": DEĞİŞMİŞ, çözüm bu çekime ait değil")))
    if not p.exists():
        return out
    c = O.jload(p)
    e = c["hata"]["ortalama_px"]
    out.append((e <= x.get("hedef_px", HEDEF_PX), f"Ortalama çözüm hatası ≤ {x.get('hedef_px', HEDEF_PX):g} px",
                f"{e:.2f} px · en kötü kare {c['hata']['en_kotu_kare']['kare']}: {c['hata']['en_kotu_kare']['hata']:.2f} px · {c['iz']['kullanilan']} iz, "
                f"kare başına en az {c['iz']['kare_basina_en_az']}"))
    out.append((c["zemin"]["nokta"] >= 12, "Zemin ve ölçek", f"zeminde {c['zemin']['nokta']} nokta, ortanca sapma {c['zemin']['sapma_m'] * 100:.1f} cm · "
                f"kamera {c['olcek']['kamera_yuksekligi_m']} m yükseklikte, yürünen yol {c['olcek']['yol_m']:.1f} m"))
    for fmt in v.formatlar:
        F = O.FORMATLAR[fmt]
        ayni = abs(F["w"] / F["h"] - c["klip"]["en"] / c["klip"]["boy"]) < 0.01
        out.append((ayni, f"[{fmt}] Çekimin oranı formatla aynı", f"çekim {c['klip']['en']}×{c['klip']['boy']}, format {F['w']}×{F['h']}"
                    + ("" if ayni else ": oran farklı (merkezden kırpma yok; bu format için ayrı çekim)")))
    if v.nframes > c["klip"]["n"]:
        out.append((False, "Film çözümün içinde", f"film {v.nframes} kare, çözüm {c['klip']['n']} kare: çözümün dışındaki karelerde kamera son karede donar"))
    return out


def nesne_kareleri(v, ad: str) -> list[str]:
    """Nesnenin çekim üstündeki önizlemesi (./st takip <id> nesne): filmin kendi kareleri, videos/<id>/takip/<ad>/nesne/."""
    d = depo(v) / ad / "nesne"
    return [str(p.relative_to(v.dir)) for p in sorted(d.glob("f*.png"))] if d.exists() else []


def ozet(v) -> dict | None:
    """Panel için: takip edilebilecek çekimler (gerçek görüntü kaydındaki videolar) ve çözümler (hata, kare başına hata, önizlemeler)."""
    import blender
    import goruntu as G
    T = yukle(v)
    kanal = lambda p: str(p.relative_to(O.KANAL))   # noqa: E731  (panelin /dosya yolu: Youtube/'a göre)
    adaylar = [{"ad": x["ad"], "dosya": kanal(v.pub / x["yayin"]), "kontak": kanal(v.dir / x["kontak"]) if x.get("kontak") else None,
                "sure": (x.get("olcu") or {}).get("sure"),
                "en": (x.get("olcu") or {}).get("en"), "boy": (x.get("olcu") or {}).get("boy"), "kisi": x.get("kisi"), "rizaTamam": G.riza_tamam(x)}
               for x in G.yukle(v)["varliklar"] if x["tur"] == "video"] if G.var_mi(v) else []
    if not T["cozumler"] and not (adaylar and v.motor == "blender"):
        return None
    out = {"secili": T.get("secili"), "cozumler": [], "adaylar": adaylar, "blender": v.motor == "blender",
           "cizer": blender.cizer(v) if v.motor == "blender" else None, "hedef_px": HEDEF_PX}
    for ad, x in T["cozumler"].items():
        p = O.ROOT / x["cozum"]
        c = O.jload(p) if p.exists() else None
        out["cozumler"].append({**x, "kare_hata": [k["hata"] for k in c["kareler"]] if c else [],
                                "kare_iz": [k["iz"] for k in c["kareler"]] if c else [],
                                "zemin_sapma_m": c["zemin"]["sapma_m"] if c else None, "olcek": c["olcek"] if c else None,
                                "en_kotu": c["hata"]["en_kotu_kare"] if c else None, "fps": c["klip"]["fps"] if c else None,
                                "nesne": [kanal(v.dir / f) for f in nesne_kareleri(v, ad)], "onizleme_url": kanal(v.dir / x["onizleme"]),
                                "takipte": True, "dondurulmus": bool(c) and _sha(p) == x["sha256"]})
    return out


# ---------------------------------------------------------------- kayma: nesnenin gölgesinin oturduğu yerde zemin izlerinin hatası
def kayma(v, kume: str | None = None, adim: int = 3) -> dict | None:
    """Nesne kayıyor mu: her karede gölge katmanının (gNNNNN, çarpan < 0,9) kapladığı bölge bulunur, o bölgedeki (40 px payla) ZEMİN
    izlerinin yeniden izdüşüm hatası ölçülür. Bilgisayarın zemini çekimin zeminiyle o noktada çakışıyorsa nesne ve gölgesi yerinde kalır:
    hata büyükse nesne asfaltın üstünde yüzer gibi kayar. Plaka kümesi yoksa None."""
    from PIL import Image
    import blender
    x = secili(v)
    if not x:
        return None
    c = O.jload(O.ROOT / x["cozum"])
    fmt = v.formatlar[0]
    if kume is None:
        P = O.jload(v.pub / "plaka.json") if (v.pub / "plaka.json").exists() else {}
        kume = (P.get(fmt) or {}).get("taslak") or (P.get(fmt) or {}).get("tam")
    d = blender.ONBELLEK / v.id / (kume or "")
    if not kume or not d.exists():
        return None
    W, H = c["klip"]["en"], c["klip"]["boy"]
    zemin = [q for q in c["noktalar"] if q["zemin"]]
    satir, kareler_ = [], []
    for f in range(0, min(v.nframes, c["klip"]["n"]), adim):
        g = d / f"g{f + 1:05d}.png"
        if not g.exists():
            continue
        a = np.asarray(Image.open(g).convert("L"))
        ys, xs = np.where(a < 0.9 * 255)
        if len(xs) < 20:
            continue
        k = W / a.shape[1]
        x0, x1, y0, y1 = xs.min() * k - 40, xs.max() * k + 40, ys.min() * k - 40, ys.max() * k + 40
        sec_ = [q for q in zemin if str(f) in q["k"] and x0 <= q["k"][str(f)][0] <= x1 and y0 <= q["k"][str(f)][1] <= y1]
        if not sec_:
            continue
        pr, on = izdusum(c, f, np.array([q["p"] for q in sec_]))
        h = [float(np.hypot(u - q["k"][str(f)][0], w_ - q["k"][str(f)][1])) for q, (u, w_), o in zip(sec_, pr, on) if o]
        if h:
            satir.append(float(np.mean(h)))
            kareler_.append({"kare": f, "iz": len(h), "hata": round(float(np.mean(h)), 3), "kutu": [round(x0), round(y0), round(x1), round(y1)]})
    if not satir:
        return {"kume": kume, "kare": 0}
    return {"kume": kume, "kare": len(satir), "ortalama_px": round(float(np.mean(satir)), 3), "en_kotu_px": round(float(np.max(satir)), 3),
            "en_kotu_kare": kareler_[int(np.argmax(satir))]["kare"], "kareler": kareler_}
