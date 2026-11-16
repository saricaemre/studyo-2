"""Gerçek görüntü hattı (./st goruntu, ./st derinlik, ./st maske): kendi çekim, kurum arşivi ya da stok; zanaat §2 yol B ve D.

Gerçek görüntü gerçek kalır: yapay zekâya girmez (kural 2), stilizasyon kodla ve kare kare deterministiktir (Remotion Stilize), yüz yeniden
yaratılmaz. Bütün türetilmiş dosyalar (ara format, derinlik, maske, kadraj yolu) bir kez üretilir ve sha256 ile dondurulur (kural 8).

Kayıt   videos/<id>/goruntu/goruntu.json · her varlık videos/<id>/goruntu/<ad>/ (asıl kopya, ara.mp4, kontak.png, dokum.json, derinlik, maske,
        kadraj_<format>.json)
Motor   public/<id>/varliklar/goruntu/<ad>.mp4|png (gerçek dosya: varliklar.md'de listelenir, Kapı 1)
        public/<id>/goruntu/<ad>/derinlik.*, maske.*, public/<id>/goruntu/bilgi.json (türetilmiş: boyut, kare hızı, kadraj yolları; motorlar okur)
Kaynak  kendi (kendi çekim) · arsiv (kurum arşivi) · acik (CC0, kamu malı ya da CC BY; lisans, atıf ve bağlantı --not'ta; telif lisansıdır, görüntüdeki kişinin
        rızası değildir) · stok (./st uret al --tur stok ile dondurulmuş Magnific/Freepik stoğu: stok:<ad>) ·
        uretim (yapay zekâ plakası: uretim:<ad>; derinlik ve 2.5B için)
Etik    kişi ve rıza bilgisi (evet | hayir | bilinmiyor) kayıtta durur ama kapı ya da zorunlu etiket değildir (kullanıcı kararı, 2026-10-27):
        kullanıcı isterse bir çözüm seçer (cozum: stilize | gizle | kullanma), seçtiyse ölçüm kodun ona uyduğunu denetler. Stokta ekran etiketi
        yalnız kullanıcı isterse. Gerçek görüntüdeki kişi Magnific'e kaynak kare olarak verilmez (kural 2; ölçüm denetler).
"""
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

import ortak as O

KAYNAKLAR = {"kendi": "kendi çekim", "arsiv": "kurum arşivi", "acik": "açık lisanslı (CC0, kamu malı ya da CC BY: lisans ve atıf notta)", "stok": "Magnific/Freepik stok",
             "uretim": "Magnific yapay zekâ plakası"}
RIZALAR = ("evet", "hayir", "bilinmiyor", "stok")
COZUMLER = ("stilize", "gizle", "kullanma")
GORSEL_UZ = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".tif", ".tiff")
VIDEO_UZ = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".mts")
AD = re.compile(r"[a-z][a-z0-9_]{1,40}")
EN_UZUN = 3840                  # ara formatın uzun kenarı en çok 4K (dikey kırpma için çözünürlük kalsın)


def _simdi():
    return dt.datetime.now().isoformat(timespec="seconds")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def depo(v) -> Path:
    return v.dir / "goruntu"


def var_mi(v) -> bool:
    return (depo(v) / "goruntu.json").exists()


def yukle(v) -> dict:
    p = depo(v) / "goruntu.json"
    G = O.jload(p) if p.exists() else {}
    G.setdefault("varliklar", [])
    return G


def bul(v, ad: str) -> dict:
    x = next((x for x in yukle(v)["varliklar"] if x["ad"] == ad), None)
    if not x:
        mevcut = ", ".join(y["ad"] for y in yukle(v)["varliklar"]) or "yok"
        raise SystemExit(f"gerçek görüntü kaydında yok: {ad} (mevcut: {mevcut}). Önce ./st goruntu ekle {v.id} <dosya | stok:<ad> | uretim:<ad>>")
    return x


def kaydet(v, G: dict):
    depo(v).mkdir(parents=True, exist_ok=True)
    (depo(v) / "goruntu.json").write_text(json.dumps(G, ensure_ascii=False, indent=1) + "\n")
    bilgi_yaz(v, G)


def _dosyalar(x: dict) -> list[tuple[str, str]]:
    """Varlığın dondurulmuş dosyaları: (kök, göreli yol) — kök "video" (videos/<id>/) ya da "public" (public/<id>/)."""
    out = [("video", x["asil"])] if x.get("asil") else []
    out += [("video", x["ara"])] if x.get("ara") else []
    out += [("public", x["yayin"])] if x.get("yayin") and x.get("kaynak") != "uretim" else []
    for t in ("derinlik", "maske"):
        if x.get(t):
            out += [("video", x[t]["asil"]), ("public", x[t]["motor"])]
    if (x.get("maske") or {}).get("genis"):
        out += [("public", x["maske"]["genis"])]
    for f in (x.get("kadraj") or {}).values():
        out += [("video", f["dosya"])]
    return out


def _kok(v, k: str) -> Path:
    return v.dir if k == "video" else v.pub


def _muhurle(v, x: dict):
    x["sha256"] = {f"{k}:{p}": _sha(_kok(v, k) / p) for k, p in _dosyalar(x)}


def dogrula(v) -> list[tuple[str, bool, str]]:
    """Dondurulmuş gerçek görüntü dosyaları kayıttaki sha256'yla aynı mı? + bilgi.json kayıttan yeniden üretilince aynı mı?"""
    out = []
    G = yukle(v)
    for x in G["varliklar"]:
        for anahtar, sha in (x.get("sha256") or {}).items():
            k, p = anahtar.split(":", 1)
            f = _kok(v, k) / p
            if not f.exists():
                out.append((x["ad"], False, f"yok: {f.relative_to(O.ROOT)}"))
            elif _sha(f) != sha:
                out.append((x["ad"], False, f"değişmiş: {f.relative_to(O.ROOT)}"))
            else:
                out.append((x["ad"], True, str(f.relative_to(O.ROOT))))
    b = v.pub / "goruntu" / "bilgi.json"
    if G["varliklar"]:
        ok = b.exists() and b.read_text() == bilgi_metni(v, G)
        out.append(("bilgi.json", ok, str(b.relative_to(O.ROOT)) if ok else "public/<id>/goruntu/bilgi.json kayıttan farklı: ./st goruntu liste yeniler"))
    return out


# ---------------------------------------------------------------- ölçüm (ffprobe)
def olcu(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffprobe okuyamadı: {p.name}")
    J = json.loads(r.stdout)
    vs = next((s for s in J.get("streams", []) if s.get("codec_type") == "video"), None)
    au = next((s for s in J.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not vs:
        raise SystemExit(f"{p.name}: görüntü akışı yok")
    d = {"en": int(vs["width"]), "boy": int(vs["height"]), "codec": vs.get("codec_name"), "bayt": p.stat().st_size}
    don = next((int(sd.get("rotation", 0)) for sd in vs.get("side_data_list", []) if "rotation" in sd), int((vs.get("tags") or {}).get("rotate", 0)))
    if abs(don) in (90, 270):  # telefon: ffmpeg çevirirken döndürür
        d["en"], d["boy"] = d["boy"], d["en"]
        d["dondurme"] = don
    if p.suffix.lower() in VIDEO_UZ:
        n, _, m = (vs.get("avg_frame_rate") or vs.get("r_frame_rate") or "0/1").partition("/")
        d.update(fps=round(float(n) / float(m or 1), 3) if float(m or 1) else None, sure=round(float(J["format"].get("duration") or 0), 3),
                 ses=au is not None, renk=vs.get("color_transfer"), pix=vs.get("pix_fmt"),
                 vfr=vs.get("r_frame_rate") != vs.get("avg_frame_rate"))
        d["hdr"] = d["renk"] in ("arib-std-b67", "smpte2084")
    return d


def _ffmpeg(*args):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg: " + r.stderr.strip()[-800:])


def _ara(kaynak: Path, cikti: Path, fps: int, o: dict, bas: float | None, son: float | None) -> list[str]:
    """Ara format: filmin kare hızında, sabit kare hızıyla (VFR telefon çekimi dahil), yüksek bit oranı, uzun kenar ≤ 4K, çift boyut, yuv420p.
    Kare çoğaltma/atlama (ffmpeg fps); ara kare uydurulmaz. Ses (varsa) AAC 48 kHz olarak kalır: filmde kullanılırsa işaret listesinden (kural 9)."""
    notlar = []
    olc = min(1.0, EN_UZUN / max(o["en"], o["boy"]))
    w, h = int(o["en"] * olc) // 2 * 2, int(o["boy"] * olc) // 2 * 2
    vf = [f"fps={fps}", f"scale={w}:{h}:flags=lanczos", "format=yuv420p"]
    if o.get("hdr"):
        notlar.append("HDR (telefon) görüntü: bu ffmpeg'de ton eşleme yok, renkler soluk ya da aşırı doygun görünebilir; mümkünse telefonda "
                      "HDR video kapalı çek (Ayarlar → Kamera → Video Kaydı → HDR Video)")
    if o.get("vfr"):
        notlar.append(f"değişken kare hızı (telefon) sabit {fps} kare/sn'ye çevrildi")
    if abs((o.get("fps") or fps) - fps) > 0.01:
        notlar.append(f"{o.get('fps'):g} → {fps} kare/sn (kare çoğaltma/atlama, ara kare yok)")
    if olc < 1:
        notlar.append(f"{o['en']}×{o['boy']} → {w}×{h}")
    kes = ([*(["-ss", f"{bas:g}"] if bas else []), *(["-to", f"{son:g}"] if son else [])])
    ses = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"] if o.get("ses") else ["-an"]
    _ffmpeg(*kes, "-i", kaynak, "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-g", str(fps), "-bf", "0", *ses, "-movflags", "+faststart", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", cikti)
    return notlar


def kesmeler(p: Path, esik: float = 10.0) -> list[dict]:
    """Sahne kesmeleri (ffmpeg scdet): [{t, skor}]."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(p), "-vf", f"scdet=threshold={esik:g}", "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [{"t": round(float(m.group(2)), 3), "skor": round(float(m.group(1)), 1)}
            for m in re.finditer(r"lavfi\.scd\.score:\s*([\d.]+),\s*lavfi\.scd\.time:\s*([\d.]+)", r.stderr)]


def dokum(p: Path) -> dict | None:
    """Konuşma varsa kelime zamanlı döküm (mlx-whisper, stüdyonun anlatım hizalamasıyla aynı model). Dil kendiliğinden bulunur."""
    import derinlik as D
    import tts
    x = O.audio_mono(p, 16000)
    if len(x) < 16000 * 0.5 or O.rms_db(x, 16000, 0, len(x) / 16000) < -50:
        return None
    import mlx_whisper
    with D.kilit("döküm"):
        r = mlx_whisper.transcribe(x, path_or_hf_repo=tts.WHISPER, word_timestamps=True)
    seg = [s for s in r.get("segments", []) if s.get("no_speech_prob", 0) < 0.6 and re.search(r"\w{2,}", s.get("text", ""))]
    if not seg or sum(len(s.get("words", [])) for s in seg) < 2:  # rüzgâr, uğultu: Whisper tek "." ya da tek kelime uydurabiliyor
        return None
    return {"dil": r.get("language"), "metin": " ".join(s["text"].strip() for s in seg),
            "kelimeler": [{"text": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)} for s in seg for w in s.get("words", [])]}


def kontak(p: Path, o: dict, kes: list[dict], cikti: Path, n: int = 12):
    """Küçük kontak tabakası: eşit aralıklı kareler, kesme sonrası ilk kareler kırmızı çerçeveli."""
    from PIL import Image, ImageDraw
    import kontak as K
    sure = o.get("sure") or 0
    T = sorted({round(sure * (i + 0.5) / n, 2) for i in range(n)} | {round(k["t"] + 0.05, 2) for k in kes[:6]})
    kw = 300 if o["en"] >= o["boy"] else 180
    kh = round(kw * o["boy"] / o["en"])
    sut = 6 if o["en"] >= o["boy"] else 8
    sat = -(-len(T) // sut)
    img = Image.new("RGB", (sut * (kw + 10) + 10, sat * (kh + 34) + 50), K.BG)
    d = ImageDraw.Draw(img)
    d.text((10, 12), f"{p.parent.name} · {o['en']}×{o['boy']} · {sure:g} sn · {len(kes)} kesme", fill=K.FG, font=K.font(18, True))
    kesik = {round(k["t"] + 0.05, 2) for k in kes}
    for i, t in enumerate(T):
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:g}", "-i", str(p), "-frames:v", "1", "-vf", f"scale={kw}:{kh}", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], capture_output=True)
        if len(r.stdout) < kw * kh * 3:
            continue
        x, y = 10 + (i % sut) * (kw + 10), 44 + (i // sut) * (kh + 34)
        img.paste(Image.frombytes("RGB", (kw, kh), r.stdout[:kw * kh * 3]), (x, y))
        if t in kesik:
            d.rectangle([x - 3, y - 3, x + kw + 2, y + kh + 2], outline=K.RED, width=3)
        d.text((x, y + kh + 6), O.tc(t) + ("  kesme" if t in kesik else ""), fill=K.RED if t in kesik else K.DIM, font=K.font(14))
    img.save(cikti)


def kisi_tara(p: Path, o: dict) -> dict:
    """Görüntüde insan var mı (tahmin): üç kare yan yana → HyperFrames remove-background (insan modeli). Karar kullanıcınındır (rıza)."""
    from PIL import Image
    import derinlik as D
    tmp = p.parent / "_kisi_tara"
    tmp.mkdir(exist_ok=True)
    try:
        if o.get("sure"):
            kareler = []
            for i, t in enumerate((0.15, 0.5, 0.85)):
                f = tmp / f"{i}.png"
                _ffmpeg("-ss", f"{(o['sure'] or 0) * t:.2f}", "-i", p, "-frames:v", "1", "-vf", "scale=-2:640", f)
                kareler.append(Image.open(f).convert("RGB"))
            m = Image.new("RGB", (sum(k.width for k in kareler), 640))
            x = 0
            for k in kareler:
                m.paste(k, (x, 0))
                x += k.width
        else:
            m = Image.open(p).convert("RGB")
            m.thumbnail((1080, 1080))
        m.save(tmp / "montaj.png")
        D._hf_arka_plan(tmp / "montaj.png", tmp / "maske.png")
        a = np.asarray(Image.open(tmp / "maske.png").convert("RGBA"))[..., 3]
        alan = float((a > 127).mean())
        # temkinli: küçük ya da arkadan görünen insanı model kısmen bulur; belirsiz alan "kişi var" sayılır (rıza sorusu açılır)
        return {"kisi_tahmini": alan > 0.0003, "alan": round(alan, 4), "belirsiz": 0.0003 < alan < 0.003}
    except SystemExit as e:
        return {"kisi_tahmini": None, "hata": str(e)[:200]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- ekle
def _varlik_satiri(x: dict) -> str:
    o = x["olcu"]
    ek = " · ".join(filter(None, [f"{o['en']}×{o['boy']}", f"{o['sure']:g} sn" if o.get("sure") else "", x["tarih"][:10]]))
    riza = "" if not x.get("kisi") else f" · kişi var, rıza: {x.get('riza') or 'bilinmiyor'}" + (f" → {x['cozum']}" if x.get("cozum") else "")
    durum = "✅ onaylı" if riza_tamam(x) else "⏳ rıza bekliyor (kişi var: rıza ya da çözüm: stilize / gizle)"
    lisans = {"kendi": "kendi çekim (kullanıcı)", "arsiv": "kurum arşivi (kullanıcı)", "acik": "açık lisans (bağlantı nota)",
              "stok": "Magnific/Freepik stok lisansı"}.get(x["kaynak"], x["kaynak"])
    return (f"| {x['ad']} (gerçek görüntü: {KAYNAKLAR.get(x['kaynak'], x['kaynak'])}) | {x['yayin']} | {'video' if x['tur'] == 'video' else 'görsel'} | "
            f"{lisans} · {ek}{riza}{' · not: ' + x['not'] if x.get('not') else ''} | {durum} · gerçek görüntü: {KAYNAKLAR.get(x['kaynak'])} |")


def _varliklar_md(v, x: dict | None = None, sil_: str | None = None):
    md = v.dir / "varliklar.md"
    if not md.exists():
        md.write_text((O.ROOT / "sablon" / "video" / "varliklar.md").read_text().replace("{{BASLIK}}", v.script.get("title", v.id)).replace("{{ID}}", v.id))
    satirlar = md.read_text().splitlines()
    hedef = sil_ or (x or {}).get("yayin")
    satirlar = [ln for ln in satirlar if not (ln.startswith("|") and f"| {hedef} |" in ln)]
    if x:
        i = next((i for i, ln in enumerate(satirlar) if re.match(r"^\| \[ad\]", ln)), None)
        if i is not None:
            satirlar[i] = _varlik_satiri(x)
        else:
            satirlar.append(_varlik_satiri(x))
    md.write_text("\n".join(satirlar).rstrip() + "\n")


def riza_tamam(x: dict) -> bool:
    """Rıza bir kapı değildir (kullanıcı kararı, 2026-10-27): kişili görüntü de onaylı varlıktır; kişi, rıza ve çözüm yalnız bilgi ve seçenek."""
    return True


def ekle(vid: str, kaynak: str, ad: str | None = None, nereden: str = "kendi", riza: str | None = None, kisi: bool | None = None,
         bas: float | None = None, son: float | None = None, not_: str = "", dokum_yap: bool = True) -> dict:
    v = O.load(vid)
    G = yukle(v)
    uretim_kaydi = None
    if kaynak.startswith(("stok:", "uretim:")):
        import uretim
        tur_, _, uad = kaynak.partition(":")
        uretim_kaydi = next((y for y in uretim.yukle(v)["varliklar"] if y["ad"] == uad), None) if uretim.var_mi(v) else None
        if not uretim_kaydi:
            raise SystemExit(f"üretim deposunda yok: {uad} (stok önce ./st uret al {vid} {uad} --tur stok … ile dondurulur)")
        if tur_ == "stok" and uretim_kaydi["tur"] != "stok":
            raise SystemExit(f"{uad} stok değil ({uretim_kaydi['tur']}): uretim:{uad} ile ekle")
        src = v.dir / uretim_kaydi["dosya"]
        nereden = "stok" if uretim_kaydi["tur"] == "stok" else "uretim"
        ad = ad or uad
    else:
        src = Path(kaynak).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"dosya yok: {src}")
        if nereden not in ("kendi", "arsiv", "acik"):
            raise SystemExit("--kaynak: kendi | arsiv | acik (stok ve yapay zekâ plakası için stok:<ad> / uretim:<ad>)")
        if nereden == "acik" and not not_:
            raise SystemExit("açık lisanslı görüntüde --not \"<lisans> · <bağlantı>\" zorunlu (ör. CC0 · https://commons.wikimedia.org/…)")
        ad = ad or re.sub(r"[^a-z0-9_]+", "_", src.stem.lower().translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))).strip("_")[:40]
        if not ad[:1].isalpha():
            ad = "g_" + ad
    if not AD.fullmatch(ad):
        raise SystemExit(f"ad: küçük harf, rakam ve _ (2–41 karakter), harfle başlar: {ad}")
    if any(x["ad"] == ad for x in G["varliklar"]):
        raise SystemExit(f"{ad} zaten var: başka bir ad ver (--ad) ya da önce ./st goruntu sil {vid} {ad}")
    if riza and riza not in RIZALAR:
        raise SystemExit(f"--riza: {' | '.join(RIZALAR[:3])}")
    uz = src.suffix.lower()
    if uz not in GORSEL_UZ + VIDEO_UZ:
        raise SystemExit(f"desteklenmeyen dosya türü: {uz} (video: {', '.join(VIDEO_UZ)}; görsel: {', '.join(GORSEL_UZ)})")
    tur = "video" if uz in VIDEO_UZ else "gorsel"
    k = depo(v) / ad
    k.mkdir(parents=True, exist_ok=True)
    bas_t = time.time()
    x = {"ad": ad, "tur": tur, "kaynak": nereden, "tarih": _simdi(), "not": not_, "uretim": uretim_kaydi["ad"] if uretim_kaydi else None,
         "kaynak_dosya": None if uretim_kaydi else src.name}
    if uretim_kaydi:  # dondurulmuş üretim/stok dosyası yerinde kalır (uretim.json sha256'sı), kopyalanmaz
        x["asil"] = uretim_kaydi["dosya"]
    else:
        asil = k / f"asil{'.jpg' if uz == '.jpeg' else uz}"
        shutil.copy2(src, asil)
        x["asil"] = str(asil.relative_to(v.dir))
    asil_yol = v.dir / x["asil"]
    o = olcu(asil_yol)
    x["olcu_kaynak"] = o
    notlar = []
    if tur == "video":
        ara = k / "ara.mp4"
        notlar = _ara(asil_yol, ara, v.fps, o, bas, son)
        x["ara"] = str(ara.relative_to(v.dir))
        x["kesim"] = {"bas": bas, "son": son} if bas or son else None
        oa = olcu(ara)
        oa["kare"] = int(round(oa["sure"] * v.fps))
        x["olcu"] = oa
        x["kesmeler"] = kesmeler(ara)
        kontak(ara, oa, x["kesmeler"], k / "kontak.png")
        x["kontak"] = str((k / "kontak.png").relative_to(v.dir))
        if dokum_yap and oa.get("ses"):
            dk = dokum(ara)
            if dk:
                (k / "dokum.json").write_text(json.dumps(dk, ensure_ascii=False, indent=1) + "\n")
                x["dokum"] = {"dosya": str((k / "dokum.json").relative_to(v.dir)), "dil": dk["dil"], "kelime": len(dk["kelimeler"]), "ozet": dk["metin"][:160]}
        pub_ad = f"{ad}.mp4"
        kopya = ara
    else:
        from PIL import Image
        im = Image.open(asil_yol)
        x["olcu"] = {"en": im.width, "boy": im.height, "bayt": asil_yol.stat().st_size}
        if uretim_kaydi:
            x["yayin"] = uretim_kaydi["yayin"]
        pub_ad = f"{ad}{uz if uz in ('.png', '.jpg') else '.png'}"
        kopya = asil_yol if uz in (".png", ".jpg") else None
        if kopya is None:
            kopya = k / "asil.png"
            im.convert("RGB").save(kopya)
    if not x.get("yayin"):
        pub = v.pub / "varliklar" / "goruntu" / pub_ad
        pub.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(kopya, pub)
        x["yayin"] = str(pub.relative_to(v.pub))
    # kişi ve rıza (kural 2, İHH çizgisi): kullanıcı söylemediyse insan modeliyle tahmin; tahmin karar değildir
    if nereden == "uretim" and kisi is None:  # yapay zekâ plakası: insan canlandırması mı, üretim kaydı söyler (--insan)
        kisi = bool(uretim_kaydi.get("insan"))
    if kisi is None:
        tara = kisi_tara(v.dir / (x.get("ara") or x["asil"]), x["olcu"])
        x["kisi_tarama"] = tara
        kisi = tara.get("kisi_tahmini")
    x["kisi"] = bool(kisi) if kisi is not None else None
    x["riza"] = riza or ("stok" if nereden == "stok" and x["kisi"] else ("bilinmiyor" if x["kisi"] else None))
    x["cozum"] = None
    x["etiket_gerekli"] = False  # stokta ekran etiketi yalnız kullanıcı isterse (2026-10-27)
    x["islem"] = notlar
    x["sure_sn"] = round(time.time() - bas_t, 1)
    _muhurle(v, x)
    G["varliklar"].append(x)
    kaydet(v, G)
    if nereden != "uretim":
        _varliklar_md(v, x)
    return x


def riza_ayarla(vid: str, ad: str, riza: str | None = None, cozum: str | None = None, kisi: bool | None = None) -> dict:
    v = O.load(vid)
    G = yukle(v)
    x = next((y for y in G["varliklar"] if y["ad"] == ad), None) or bul(v, ad)
    if kisi is not None:
        x["kisi"] = kisi
    if riza:
        if riza not in RIZALAR:
            raise SystemExit(f"--riza: {' | '.join(RIZALAR[:3])}")
        x["riza"] = riza
    if cozum:
        if cozum not in COZUMLER + ("yok",):
            raise SystemExit(f"--cozum: {' | '.join(COZUMLER)} (kaldırmak için yok)")
        x["cozum"] = None if cozum == "yok" else cozum
    x["riza_tarih"] = _simdi()
    kaydet(v, G)
    if x["kaynak"] != "uretim":
        _varliklar_md(v, x)
    return x


def sil(vid: str, ad: str) -> dict:
    v = O.load(vid)
    G = yukle(v)
    x = bul(v, ad)
    yer = [y for y in kullanim(v).get(ad, [])]
    if yer:
        raise SystemExit(f"{ad} kullanılıyor: {', '.join(yer)}. Önce sahneden çıkar.")
    shutil.rmtree(depo(v) / ad, ignore_errors=True)
    shutil.rmtree(v.pub / "goruntu" / ad, ignore_errors=True)
    if x["kaynak"] != "uretim":
        (v.pub / x["yayin"]).unlink(missing_ok=True)
        _varliklar_md(v, sil_=x["yayin"])
    G["varliklar"] = [y for y in G["varliklar"] if y["ad"] != ad]
    kaydet(v, G)
    return x


# ---------------------------------------------------------------- türevler: derinlik, maske, kadraj
def derinlik(vid: str, ad: str, yumusatma: float = 0.35) -> dict:
    import derinlik as D
    v = O.load(vid)
    G = yukle(v)
    bul(v, ad)
    x = next(y for y in G["varliklar"] if y["ad"] == ad)
    k = depo(v) / ad
    pk = v.pub / "goruntu" / ad
    if x["tur"] == "video":
        o = x["olcu"]
        b = D.derinlik_video(v.dir / x["ara"], o["en"], o["boy"], v.fps, k / "derinlik.mkv", pk / "derinlik.mp4", yumusatma)
        x["derinlik"] = {"asil": str((k / "derinlik.mkv").relative_to(v.dir)), "motor": str((pk / "derinlik.mp4").relative_to(v.pub)), **b}
    else:
        b = D.derinlik_gorsel(v.dir / x["asil"], k / "derinlik.png", pk / "derinlik.png")
        x["derinlik"] = {"asil": str((k / "derinlik.png").relative_to(v.dir)), "motor": str((pk / "derinlik.png").relative_to(v.pub)), **b}
    x["derinlik"]["tarih"] = _simdi()
    _muhurle(v, x)
    kaydet(v, G)
    return x


def maske(vid: str, ad: str, kutu: list[float] | None = None, kutu_kare: int = 0) -> dict:
    import derinlik as D
    v = O.load(vid)
    G = yukle(v)
    bul(v, ad)
    x = next(y for y in G["varliklar"] if y["ad"] == ad)
    if kutu is not None and (len(kutu) != 4 or not all(0 <= a <= 1 for a in kutu) or kutu[0] >= kutu[2] or kutu[1] >= kutu[3]):
        raise SystemExit("--kutu x0,y0,x1,y1: 0–1 arası, karenin sol üstüne göre (ör. 0.3,0.2,0.7,0.9)")
    k = depo(v) / ad
    pk = v.pub / "goruntu" / ad
    o = x["olcu"]
    if x["tur"] == "video":
        b = D.maske_video(v.dir / x["ara"], o["en"], o["boy"], v.fps, k / "maske.mkv", pk / "maske.mp4", kutu, kutu_kare)
        x["maske"] = {"asil": str((k / "maske.mkv").relative_to(v.dir)), "motor": str((pk / "maske.mp4").relative_to(v.pub)), **b}
    else:
        b = D.maske_gorsel(v.dir / x["asil"], k / "maske.png", pk / "maske.png", kutu)
        x["maske"] = {"asil": str((k / "maske.png").relative_to(v.dir)), "motor": str((pk / "maske.png").relative_to(v.pub)), **b}
    x["maske"]["genis"] = str((pk / f"maske_genis.{'mp4' if x['tur'] == 'video' else 'png'}").relative_to(v.pub))
    x["maske"]["tarih"] = _simdi()
    if b.get("zayif_kare"):
        z = b["zayif_kare"]
        print(f"   ⚠️ maske {len(z)} karede komşularına göre ani düşüyor (model kişiyi kaçırmış olabilir): " + ", ".join(f"f{i}" for i in z[:8])
              + f" · yüz gizleme genişletilmiş maskeyi kullanır (±{D.GIZLE_KARE} kare); kontak tabakasında göz denetle")
    if b.get("bos_kare"):
        print(f"   ⚠️ {b['bos_kare']}/{b['kare']} karede maske boş (özne yok ya da model tanımadı): kadraj o karelerde son konumu tutar")
    if b["alan"] < 0.002:
        print("   ⚠️ maske neredeyse boş: insan modeli yalnız insanı tanır; nesne için --kutu x0,y0,x1,y1 ver")
    _muhurle(v, x)
    kaydet(v, G)
    return x


def _yumusat(a: np.ndarray, sigma: float) -> np.ndarray:
    """Gauss ile iki yönlü yumuşatma (çevrimdışı: geleceği de görür), kenarlarda yansıma."""
    if sigma <= 0 or len(a) < 3:
        return a
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(a, (r, r), mode="reflect" if len(a) > r else "edge")
    return np.convolve(p, k, mode="valid")


def kadraj(vid: str, ad: str, fmt: str, yakinlik: float = 1.0, hedef: str = "govde", yumusak: float = 0.8, ozne: str = "en_buyuk") -> dict:
    """Özneyi (maskenin ağırlık merkezi; hedef "bas": maskenin üst kısmı) formatın güvenli alanının ortasında tutan yumuşak kırpma yolu.
    ozne "en_buyuk": maskede birden çok kişi/nesne varsa ana özne (en büyük ve bir önceki kareye yakın); "hepsi": bütün maskenin merkezi.
    Kırpma penceresi formatın en-boy oranında, kaynağın içinde (büyütme yok, kenar dolgusu yok); merkezden kırpma değil (CLAUDE.md format kuralı)."""
    import derinlik as D
    v = O.load(vid)
    G = yukle(v)
    bul(v, ad)
    x = next(y for y in G["varliklar"] if y["ad"] == ad)
    if fmt not in O.FORMATLAR:
        raise SystemExit(f"format: {', '.join(O.FORMATLAR)}")
    if not x.get("maske"):
        raise SystemExit(f"önce maske: ./st maske {vid} {ad} (insan: varsayılan; nesne: --kutu x0,y0,x1,y1)")
    if not 0.2 <= yakinlik <= 1.0:
        raise SystemExit("--yakinlik 0.2–1.0 (1 = kaynağın içine sığan en büyük pencere)")
    F = O.FORMATLAR[fmt]
    g = F["guvenli"]
    o = x["olcu"]
    W, H = o["en"], o["boy"]
    a = F["w"] / F["h"]
    cw, ch = (H * a, H) if W / H > a else (W, W / a)
    cw, ch = cw * yakinlik, ch * yakinlik
    from scipy import ndimage
    olcek = 4
    P, kutu, onceki = [], [], None
    for m in D.maske_dizisi(v.dir / x["maske"]["asil"], W, H, olcek):
        b = m > 127
        if ozne == "en_buyuk" and b.any():  # birden çok kişi/nesne: ana özne (büyük ve bir önceki konuma yakın olan)
            et, n_ = ndimage.label(b)
            alan = ndimage.sum(b, et, range(1, n_ + 1))
            adaylar = [i + 1 for i, a_ in enumerate(alan) if a_ >= 0.1 * alan.max()]
            if onceki is not None and len(adaylar) > 1:  # aynı kişiyi tut: alan × yakınlık (önden geçen biri takibi çalmasın)
                mer = ndimage.center_of_mass(b, et, adaylar)
                puan = [alan[i - 1] * np.exp(-np.hypot(c[1] * olcek - onceki[0], c[0] * olcek - onceki[1]) / (0.12 * W)) for i, c in zip(adaylar, mer)]
                sec = adaylar[int(np.argmax(puan))]
            else:
                sec = int(np.argmax(alan)) + 1
            m = np.where(et == sec, m, 0)
        ys, xs = np.nonzero(m > 127)
        if len(xs) < 4:
            P.append(None)
            kutu.append(None)
            continue
        w8 = m[ys, xs].astype(np.float64)
        cx, cy = float((xs * w8).sum() / w8.sum()) * olcek, float((ys * w8).sum() / w8.sum()) * olcek
        y0, y1 = float(np.percentile(ys, 2)) * olcek, float(np.percentile(ys, 98)) * olcek
        x0, x1 = float(np.percentile(xs, 2)) * olcek, float(np.percentile(xs, 98)) * olcek
        if hedef == "bas":
            cy = y0 + 0.12 * (y1 - y0)
        P.append((cx, cy))
        kutu.append((x0, y0, x1, y1))
        onceki = (cx, cy)
    n = len(P)
    if x["tur"] == "video":
        n = max(n, o.get("kare") or n)
    gecerli = [i for i, p in enumerate(P) if p]
    if not gecerli:
        raise SystemExit("maskenin hiçbir karesinde özne yok: kadraj kurulamaz")
    son = P[gecerli[0]]
    for i in range(len(P)):  # boş karede son konum (baştakiler ilk geçerliyle)
        P[i] = P[i] or son
        son = P[i]
    P += [P[-1]] * (n - len(P))
    kutu += [None] * (n - len(kutu))
    # öznenin karedeki hedef yeri: güvenli alanın ortası (yatayda), gövdede dikey orta, başta üst üçte bir
    tx = (g["sol"] + 1 - g["sag"]) / 2
    ty = (g["ust"] + 1 - g["alt"]) / 2 if hedef == "govde" else g["ust"] + 0.3 * (1 - g["ust"] - g["alt"])
    X = np.clip(np.array([p[0] - tx * cw for p in P]), 0, W - cw)
    Y = np.clip(np.array([p[1] - ty * ch for p in P]), 0, H - ch)
    sig = yumusak * v.fps / 2
    X = np.clip(_yumusat(X, sig), 0, W - cw)
    Y = np.clip(_yumusat(Y, sig), 0, H - ch)
    # kısıt: yumuşak yol özneyi güvenli alanın dışına düşürüyorsa en küçük düzeltme, sonra hafif yumuşatma (birkaç tur)
    px, py = np.array([p[0] for p in P]), np.array([p[1] for p in P])
    xlo, xhi = px - (1 - g["sag"]) * cw, px - g["sol"] * cw
    ylo, yhi = py - (1 - g["alt"]) * ch, py - g["ust"] * ch
    for _ in range(4):
        X = np.clip(np.clip(X, xlo, xhi), 0, W - cw)
        Y = np.clip(np.clip(Y, ylo, yhi), 0, H - ch)
        X = np.clip(_yumusat(X, sig / 3), 0, W - cw)
        Y = np.clip(_yumusat(Y, sig / 3), 0, H - ch)
    X = np.clip(np.clip(X, xlo + 0.01 * cw, xhi - 0.01 * cw), 0, W - cw)
    Y = np.clip(np.clip(Y, ylo + 0.01 * ch, yhi - 0.01 * ch), 0, H - ch)
    # ölçüm: öznenin noktası güvenli alanda mı, gövdesi pencerede mi
    ic, gov = 0, []
    for i, p in enumerate(P):
        ux, uy = (p[0] - X[i]) / cw, (p[1] - Y[i]) / ch
        ic += g["sol"] <= ux <= 1 - g["sag"] and g["ust"] <= uy <= 1 - g["alt"]
        if kutu[i]:
            x0, y0, x1, y1 = kutu[i]
            ix = max(0.0, min(x1, X[i] + cw) - max(x0, X[i]))
            iy = max(0.0, min(y1, Y[i] + ch) - max(y0, Y[i]))
            gov.append(ix * iy / max(1.0, (x1 - x0) * (y1 - y0)))
    hiz = np.hypot(np.diff(X), np.diff(Y)) if n > 1 else np.zeros(1)
    sicrama = [int(i) + 1 for i in np.nonzero(hiz > 0.15 * cw)[0]]  # özne değişti ya da kadrajdan çıktı: kadraj bir karede kayar
    olcum = {"guvenli_oran": round(ic / n, 4), "govde_icinde": round(float(np.mean(gov)) if gov else 1.0, 4),
             "en_hizli_px_kare": round(float(hiz.max()), 2), "sicrama": sicrama[:20], "kirpma": "özne takibi" if n > 1 else "özneye göre sabit"}
    K = {"format": fmt, "kaynak": {"en": W, "boy": H}, "fps": v.fps, "hedef": hedef, "ozne": ozne, "yakinlik": yakinlik, "yumusak": yumusak,
         "pencere": [round(cw / W, 5), round(ch / H, 5)], "olcum": olcum,
         "kareler": [[round(X[i] / W, 5), round(Y[i] / H, 5), round(cw / W, 5), round(ch / H, 5)] for i in range(n)]}
    f = depo(v) / ad / f"kadraj_{fmt}.json"
    f.write_text(json.dumps(K, ensure_ascii=False) + "\n")
    x.setdefault("kadraj", {})[fmt] = {"dosya": str(f.relative_to(v.dir)), "hedef": hedef, "ozne": ozne, "yakinlik": yakinlik, "yumusak": yumusak, **olcum,
                                        "tarih": _simdi()}
    _muhurle(v, x)
    kaydet(v, G)
    return x["kadraj"][fmt]


# ---------------------------------------------------------------- motorların okuduğu özet (public/<id>/goruntu/bilgi.json)
def bilgi_metni(v, G: dict | None = None) -> str:
    G = G or yukle(v)
    B = {}
    for x in G["varliklar"]:
        o = x["olcu"]
        b = {"tur": x["tur"], "dosya": x["yayin"], "en": o["en"], "boy": o["boy"], "kisi": x.get("kisi"), "kaynak": x["kaynak"]}
        if x["tur"] == "video":
            b.update(fps=v.fps, kare=o.get("kare"), sure=o.get("sure"))
        for t in ("derinlik", "maske"):
            if x.get(t):
                b[t] = x[t]["motor"]
        if (x.get("maske") or {}).get("genis"):
            b["maske_genis"] = x["maske"]["genis"]
        if x.get("kadraj"):
            b["kadraj"] = {}
            for fmt, k in sorted(x["kadraj"].items()):
                K = O.jload(v.dir / k["dosya"])
                b["kadraj"][fmt] = {"pencere": K["pencere"], "kareler": K["kareler"]}
        B[x["ad"]] = b
    return json.dumps(B, ensure_ascii=False, separators=(",", ":")) + "\n"


def bilgi_yaz(v, G: dict | None = None):
    p = v.pub / "goruntu" / "bilgi.json"
    t = bilgi_metni(v, G)
    if not (G or yukle(v))["varliklar"]:
        p.unlink(missing_ok=True)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists() or p.read_text() != t:
        p.write_text(t)


# ---------------------------------------------------------------- kullanım ve etik denetimi
def _kod(v) -> dict[Path, str]:
    import uretim
    return {p: p.read_text(errors="replace") for p in uretim._kod_dosyalari(v)}


GORUNTU_ETIKETI = re.compile(r"<(Goruntu|Derinlik25D|Stilize)\b([^>]*?)\bad=(?:\{\s*)?([\"'`]?)([\w]+)\3(?:\s*\})?([^>]*)>", re.S)
SABIT = re.compile(r"\bconst\s+([A-Za-z_]\w*)\s*=\s*['\"`]([a-z][a-z0-9_]*)['\"`]")


def _ad_coz(t: str, ad: str, tirnak: str) -> str:
    """ad={KLIP} → aynı dosyadaki const KLIP = 'kar_firtinasi'."""
    return ad if tirnak else dict(SABIT.findall(t)).get(ad, ad)


def kullanim(v) -> dict[str, list[str]]:
    """Her gerçek görüntünün kodda geçtiği dosyalar: Remotion'da adı bir dize olarak (ad="…", ad={'…'} ya da const X = '…'),
    HyperFrames'te varliklar/goruntu/<ad>… ya da goruntu/<ad>/…"""
    V = yukle(v)["varliklar"]
    out = {x["ad"]: [] for x in V}
    for p, t in _kod(v).items():
        for x in V:
            ad = x["ad"]
            if re.search(r"[\"'`]" + ad + r"[\"'`]", t) or Path(x["yayin"]).name in t or f"goruntu/{ad}/" in t:
                out[ad].append(str(p.relative_to(O.ROOT)))
    return out


def stil_kullanimi(v) -> dict[str, set[str]]:
    """Remotion'da her görüntünün hangi bileşenle çizildiği ve Stilize'de gizle ayarı: {ad: {"Goruntu", "Stilize:gizle", …}}."""
    out: dict[str, set[str]] = {}
    for _, t in _kod(v).items():
        for m in GORUNTU_ETIKETI.finditer(t):
            bilesen, ad, nit = m.group(1), _ad_coz(t, m.group(4), m.group(3)), m.group(2) + m.group(5)
            if bilesen == "Stilize":  # gizle: özne mozaikli; mod="gercek" gizlemesiz: görüntü olduğu gibi (gerçek sayılır)
                bilesen += (":gizle" if re.search(r"\bgizle\b(?!\s*=\s*\{\s*false)", nit)
                            else ":gercek" if re.search(r"\bmod=[\"'{]+gercek", nit) else "")
            out.setdefault(ad, set()).add(bilesen)
    return out


def etik_durumu(v) -> dict:
    """Rıza, stok etiketi ve "gerçek kişi yapay zekâya girmez" denetimi (ölçüm satırları)."""
    import uretim
    G = yukle(v)
    kul = kullanim(v)
    stil = stil_kullanimi(v)
    riza_sorun, etiket_eksik, yz_sorun = [], [], []  # etiket_eksik: stokta zorunlu etiket kalktı (2026-10-27); anahtar geriye uyum için boş
    for x in G["varliklar"]:
        if not kul.get(x["ad"]):
            continue
        if x.get("kisi") and x.get("riza") not in ("evet", "stok"):
            c = x.get("cozum")
            b = stil.get(x["ad"], set())
            if c == "kullanma":  # yalnız kullanıcının seçtiği çözüm denetlenir; çözüm seçilmediyse sorun yok
                riza_sorun.append(f"{x['ad']}: kullanıcı 'kullanma' dedi ama kodda geçiyor")
            elif c == "gizle" and (b - {"Stilize:gizle"}):
                riza_sorun.append(f"{x['ad']}: çözüm 'gizle' ama {', '.join(sorted(b - {'Stilize:gizle'}))} ile yüz açık çiziliyor")
            elif c == "stilize" and b & {"Goruntu", "Derinlik25D", "Stilize:gercek"}:
                riza_sorun.append(f"{x['ad']}: çözüm 'stilize' ama <Goruntu>/<Derinlik25D>/<Stilize mod=\"gercek\"> ile gerçek hâliyle çiziliyor")
    if uretim.var_mi(v):
        kisili = [x for x in G["varliklar"] if x.get("kisi") and x["kaynak"] != "uretim"]
        for y in uretim.yukle(v)["varliklar"]:
            kk = str(y.get("kaynak_kare") or "") + " " + json.dumps(y.get("parametreler") or {}, ensure_ascii=False)
            for x in kisili:
                if f"goruntu/{x['ad']}" in kk or Path(x["yayin"]).name in kk:
                    yz_sorun.append(f"{y['ad']} ← {x['ad']}")
    return {"riza": riza_sorun, "etiket_eksik": etiket_eksik, "yz": yz_sorun, "kullanilan": [a for a, k in kul.items() if k]}


def ozet(v) -> dict:
    """Panel: film sayfasındaki "Gerçek görüntü" bloğu."""
    G = yukle(v) if var_mi(v) else {"varliklar": []}
    kul = kullanim(v) if G["varliklar"] else {}
    return {"var": bool(G["varliklar"]), "varliklar": [
        {"ad": x["ad"], "tur": x["tur"], "kaynak": KAYNAKLAR.get(x["kaynak"], x["kaynak"]), "yayin": x["yayin"],
         "dosya": str((v.pub / x["yayin"]).relative_to(O.KANAL)),
         "kontak": str((v.dir / x["kontak"]).relative_to(O.KANAL)) if x.get("kontak") else None,
         "olcu": {k: x["olcu"].get(k) for k in ("en", "boy", "sure", "kare")}, "kisi": x.get("kisi"), "riza": x.get("riza"), "cozum": x.get("cozum"),
         "rizaTamam": riza_tamam(x), "etiket": x.get("etiket_gerekli"), "dokum": (x.get("dokum") or {}).get("ozet"),
         "kesme": len(x.get("kesmeler") or []), "derinlik": bool(x.get("derinlik")), "maske": (x.get("maske") or {}).get("yontem"),
         "kadraj": {f: k.get("guvenli_oran") for f, k in (x.get("kadraj") or {}).items()}, "kullanildigi": kul.get(x["ad"], []), "tarih": x["tarih"]}
        for x in G["varliklar"]]}
