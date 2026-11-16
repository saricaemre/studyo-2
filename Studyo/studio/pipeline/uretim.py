"""Üretim deposu (./st uret): Magnific (MCP) ile üretilen ya da bulunan görsel, video, efekt sesi, 3B model ve stok.

Kullanıcının tek ücretli yapay zekâ kaynağı Magnific'tir (Premium: yılda 240 bin kredi, ticari yapay zekâ lisansı, müzik hakkı yok).
Model bir kez çalışır, sonucu dosya olarak dondurulur: kare t'nin saf fonksiyonu kalır (kural 8), ./st deterministik sha256'yı denetler.

Akış (Claude, her üretim çağrısı için)
  simulate_cost (ücretsiz) → ./st uret butce <id> --tahmin N (sınır aşılıyorsa çıkış 3: DUR, kullanıcıya sor) → üretim aracı →
  creations_wait → HEMEN ./st uret al (Magnific'in dosya bağlantısı ~30 dakikada geçersiz olur)
  al        indirir, sha256 + ffprobe; asıl videos/<id>/uretim/<ad>.<uz>, motorların okuduğu kopya public/<id>/varliklar/uretim/<ad>.<uz>
            (Remotion staticFile, HyperFrames varliklar/, Blender varliklar/ hepsi buradan); uretim.json kaydı, varliklar.md satırı (Kapı 1)
  liste     varlıklar, kullanıldıkları yer, harcanan / sınır
  butce     kalan kredi; tahmin sınırı aşıyorsa çıkış kodu 3. Geçerse tek kullanımlık izin yazar (panel işinde kanca bunu arar)
  sil       yalnız hiçbir sahnede kullanılmayan varlık (harcama kaydı kalır)
  bakiye    account_balance sonucunu kaydeder (işin başında ve sonunda): panel/onbellek/magnific_bakiye.json + uretim.json → denetim
  yukle     yerel bir dosyayı (ör. motorun çizdiği anahtar kare) creations_request_upload'un verdiği PUT bağlantısına yükler

Kredi bekçisi: film başına sınır (videos/<id>/claude.json → kredi_siniri, yoksa panel/uretim_ayarlari.json, varsayılan 20 000).
Panelin arka plan Claude'unda PreToolUse kancası (uretim_kanca.py) ücretli her Magnific çağrısını izne bağlar: butce'nin yazdığı izin yoksa,
eskiyse ya da tahmin kalan krediyi aşıyorsa çağrı hiç gitmez. Müzik ve TTS araçları her durumda kapalı (Premium'da müzik hakkı yok; TTS 3a'da yok).

Etik (CLAUDE.md kural 2, İHH çizgisi): gerçek yararlanıcı, gerçek olay, belgesel görünümlü acı ve gerçek kişinin kopyası üretilmez.
Gerçekçi yapay zekâ insanı yalnız ekranda etiketli canlandırmada: --insan → etiket_gerekli; script.json → etiketler [{vurus, metin, varlik}].
"""
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import ortak as O

AYAR = O.ROOT / "panel" / "uretim_ayarlari.json"
BAKIYE = O.ROOT / "panel" / "onbellek" / "magnific_bakiye.json"
VARSAYILAN = {"kredi_siniri": 20000, "magnific_plan": "premium"}
TURLER = ("gorsel", "video", "ses", "3b", "stok", "anlatim")
TUR_AD = {"gorsel": "görsel", "video": "video", "ses": "efekt sesi", "3b": "3B model", "stok": "stok", "anlatim": "anlatım"}
LISANS_YZ = "Magnific ticari yapay zekâ lisansı"
LISANS_STOK = "Magnific/Freepik stok lisansı"
ETIKETLER = ("Canlandırmadır", "Temsilîdir", "Yapay zekâ ile üretilmiştir")
EN_BUYUK = 1024 * 1024 * 1024
IZIN_OMRU = 20 * 60            # butce'nin izni bu kadar saniye geçerli, tek kullanımlık
UA = {"User-Agent": "studyo-uretim/1.0 (code-rendered video studio; personal use)"}

# Panelin arka plan Claude'una açılan Magnific araçları (sunucu.py CLAUDE_ARACLAR). Hesabı değiştirenler (paylaşma, silme, takım,
# marka kiti yazma, Spaces, akışlar) yok. Kredi harcayanlar URET_ARACLARI'dır: kanca her birini butce iznine bağlar.
URET_ARACLARI = {
    "images_generate", "images_retouch", "images_expand", "images_upscale", "images_relight", "images_remove_background",
    "video_generate", "video_extend", "video_modify", "video_upscale",
    "audio_sfx_generate", "audio_isolate",
    "models3d_generate", "models3d_rig", "models3d_convert",
    "audio_tts",  # yalnız anlatıcısı Magnific olan filmde (script.json → ses.kaynak = magnific; kullanıcının seçimi), kanca denetler
    # 3b: derinlik ve maske (görsel: 5 / 35 / 3 kredi; yerel ./st derinlik ve ./st maske ücretsiz, önce onlar) ve stok (stok video 150–600
    # kredi: bedel simulate_cost'ta yok, stock_search / stock_get → creditCost). Lisanslı stok dosyası da kredi harcar (kanca: license=true)
    "images_depth_map", "images_segment", "video_remove_background", "stock_download",
}
LISANSLI_INDIRME = "creations_register_download"  # license: true ile çağrılırsa stoğu lisanslar (ücretli); değilse okuma
OKUMA_ARACLARI = {
    "account_balance", "simulate_cost", "guides_list", "guides_get", "audio_voices_list", "audio_voices_show", "audio_tts_direction",
    "images_models_list", "images_models_show", "images_models_settings", "images_upscale_modes_list",
    "video_models_list", "video_models_show", "video_modify_models_list", "video_upscale_models_list", "models3d_models_list",
    "stock_search", "stock_get",
    "creations_wait", "creations_get", "creation_status", "creations_register_download", "creations_deliver",
    "creations_upload_image", "creations_request_upload", "creations_finalize_upload",
}
# Premium'da müzik hakkı yok (yol haritası kararı 6); ses kopyalama, ses değiştirme ve dudak senkronu açılmadı.
# TTS (audio_tts) yalnız anlatıcısı Magnific seçilmiş filmde (kanca bakar): anlatıcı sesi kullanıcı kararıdır (kural 3)
YASAK_ARACLAR = {"audio_music_generate", "video_music", "video_speak", "audio_voice_clone", "audio_voice_change", "video_soundfx"}
MCP_ON = "mcp__magnific__"


def mcp_araclari() -> list[str]:
    return sorted(MCP_ON + a for a in URET_ARACLARI | OKUMA_ARACLARI)


# ---------------------------------------------------------------- ayarlar ve durum
def ayarlar() -> dict:
    try:
        return {**VARSAYILAN, **(O.jload(AYAR) if AYAR.exists() else {})}
    except (json.JSONDecodeError, OSError):
        return dict(VARSAYILAN)


def ayar_yaz(d: dict) -> dict:
    yeni = {**ayarlar(), **d}
    AYAR.write_text(json.dumps(yeni, ensure_ascii=False, indent=2) + "\n")
    return yeni


def _claude_kaydi(vid: str) -> dict:
    for p in (O.ROOT / "videos" / vid / "claude.json", O.ROOT / "istekler" / f"{vid}.json"):
        if p.exists():
            try:
                return O.jload(p)
            except json.JSONDecodeError:
                return {}
    return {}


def sinir(vid: str) -> int:
    """Film başına kredi sınırı: panelin film kaydı (claude.json → kredi_siniri) > ayar (uretim_ayarlari.json) > 20 000."""
    k = _claude_kaydi(vid).get("kredi_siniri")
    return int(k) if isinstance(k, (int, float)) and k >= 0 else int(ayarlar()["kredi_siniri"])


def magnific_durumu() -> dict:
    """Magnific bağlantısı kurulu mu (Claude Code yapılandırması; ağ yok, kredi yok) + son bilinen bakiye.
    Magnific bağlı olmayan kurulumda ya da bağlantı kaldırılmışsa kurulu değil: panel üretim yolunu kapalı gösterir, plan turu yerel yollarla kurar."""
    kurulu, kapsam = False, None
    if os.environ.get("STUDYO_MAGNIFIC") == "yok":  # sınama: bağlantı kurulu değilmiş gibi (Magnific bağlı olmayan kurulum); yapılandırmaya dokunmaz
        return {"kurulu": False, "kapsam": None, "bakiye": None, "plan": ayarlar()["magnific_plan"]}
    try:
        cj = json.loads((Path.home() / ".claude.json").read_text())
    except (OSError, json.JSONDecodeError):
        cj = {}
    if "magnific" in (cj.get("mcpServers") or {}):
        kurulu, kapsam = True, "kullanıcı"
    for yol in (O.KANAL, O.ROOT):
        if "magnific" in ((cj.get("projects") or {}).get(str(yol)) or {}).get("mcpServers", {}):
            kurulu, kapsam = True, kapsam or "proje"
        mj = yol / ".mcp.json"
        if mj.exists():
            try:
                if "magnific" in (json.loads(mj.read_text()).get("mcpServers") or {}):
                    kurulu, kapsam = True, kapsam or "proje (.mcp.json)"
            except json.JSONDecodeError:
                pass
    b = O.jload(BAKIYE) if BAKIYE.exists() else None
    return {"kurulu": kurulu, "kapsam": kapsam, "bakiye": b, "plan": ayarlar()["magnific_plan"]}


# ---------------------------------------------------------------- depo
def depo(v) -> Path:
    return v.dir / "uretim"


def yukle(v) -> dict:
    p = depo(v) / "uretim.json"
    U = O.jload(p) if p.exists() else {}
    for k in ("varliklar", "harcama", "denetim", "silinen"):
        U.setdefault(k, [])
    return U


def var_mi(v) -> bool:
    return (depo(v) / "uretim.json").exists()


def kaydet(v, U: dict):
    depo(v).mkdir(parents=True, exist_ok=True)
    s = sinir(v.id)
    h = harcanan(U)
    U["ozet"] = {"harcanan": h, "sinir": s, "kalan": s - h, "varlik": len(U["varliklar"]),
                 "modeller": sorted({x["model"] for x in U["varliklar"] if x.get("model")}), "guncelleme": _simdi()}
    (depo(v) / "uretim.json").write_text(json.dumps(U, ensure_ascii=False, indent=1) + "\n")


def harcanan(U: dict) -> int:
    return int(sum(h.get("kredi") or 0 for h in U.get("harcama", [])))


def _simdi() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- bütçe ve kanca
def butce(v, tahmin: int | None = None, arac: str | None = None) -> dict:
    """Kalan kredi. Tahmin verildiyse ve sınırı aşmıyorsa tek kullanımlık izin yazar (kanca arar). Aşıyorsa izin yazmaz: ok False."""
    U = yukle(v)
    s, h = sinir(v.id), harcanan(U)
    d = {"sinir": s, "harcanan": h, "kalan": s - h, "tahmin": tahmin, "ok": True}
    if tahmin is not None:
        d["ok"] = tahmin <= s - h
        izin = depo(v) / "_izin.json"
        if d["ok"]:
            depo(v).mkdir(parents=True, exist_ok=True)
            izin.write_text(json.dumps({"tahmin": int(tahmin), "arac": arac, "zaman": time.time(), "tarih": _simdi()}, ensure_ascii=False))
        else:
            izin.unlink(missing_ok=True)
    return d


def kanca(vid: str | None, arac: str, tool_use_id: str | None = None, girdi: dict | None = None) -> tuple[bool, str]:
    """PreToolUse: Magnific aracı çağrılmadan önce. (True, "") geçer; (False, neden) çağrıyı durdurur ve nedeni Claude'a söyler."""
    if arac == LISANSLI_INDIRME and (girdi or {}).get("license"):  # stoğu lisanslamak kredi harcar: üretim gibi izne bağlı
        return _izinli(vid, arac, tool_use_id)
    if arac in YASAK_ARACLAR:
        return False, (f"{arac} kapalı: Magnific Premium'da müzik hakkı yok; ses kopyalama ve dudak senkronu bu stüdyoda açık değil. "
                       "Müziği ./st muzik (kod ya da ACE-Step) üretir; anlatım ./st ses.")
    if arac not in URET_ARACLARI:
        return True, ""
    return _izinli(vid, arac, tool_use_id)


def _izinli(vid: str | None, arac: str, tool_use_id: str | None) -> tuple[bool, str]:
    """Ücretli çağrı: filmin işinde, butce'nin tek kullanımlık ve bu araca verilmiş izniyle; harcama çağrı anında yazılır."""
    if not vid or not (O.ROOT / "videos" / vid / "script.json").exists():
        return False, "Magnific üretimi yalnız bir filmin işinde yapılır (kredi o filmin sınırına yazılır)."
    v = O.load(vid)
    if arac == "audio_tts" and (v.script.get("ses") or {}).get("kaynak") != "magnific":
        return False, ("audio_tts yalnız anlatıcısı Magnific seçilmiş filmde açık (script.json → ses.kaynak = magnific; anlatıcı sesi kullanıcının "
                       "kararıdır). Bu filmin anlatımı ./st ses ile kendi kaynağından gelir.")
    izin_p = depo(v) / "_izin.json"
    if not izin_p.exists():
        return False, (f"Kredi bekçisi: önce simulate_cost ile bedeli ölç (stokta stock_search / stock_get → creditCost), sonra ./st uret butce {vid} "
                       f"--tahmin <kredi> --arac {arac}. "
                       "Sınır aşılıyorsa (çıkış 3) DUR ve durum.md'de kullanıcıya sor.")
    I = O.jload(izin_p)
    izin_p.unlink(missing_ok=True)  # tek kullanımlık
    if time.time() - float(I.get("zaman", 0)) > IZIN_OMRU:
        return False, f"Kredi bekçisi: izin eskimiş (> {IZIN_OMRU // 60} dk). simulate_cost ve ./st uret butce {vid} --tahmin <kredi> yeniden."
    if I.get("arac") and I["arac"] != arac:
        return False, f"Kredi bekçisi: izin {I['arac']} için alındı, çağrılan {arac}. Bu araç için yeniden butce."
    U = yukle(v)
    kalan = sinir(vid) - harcanan(U)
    if int(I["tahmin"]) > kalan:
        return False, f"Kredi bekçisi: tahmin {I['tahmin']} > kalan {kalan}. DUR, durum.md'de kullanıcıya sor."
    U["harcama"].append({"tarih": _simdi(), "arac": arac, "kredi": int(I["tahmin"]), "kaynak": "kanca", "varlik": None, "tool_use_id": tool_use_id})
    kaydet(v, U)
    return True, ""


def bakiye_kaydet(vid: str | None, kalan: int, an: str = "okuma", toplam: int | None = None, plan: str | None = None, is_: str | None = None) -> dict:
    """account_balance sonucu: panelin son bilinen bakiyesi + (film verildiyse) uretim.json → denetim."""
    b = {"kalan": int(kalan), "toplam": toplam, "plan": plan, "tarih": _simdi(), "video": vid}
    BAKIYE.parent.mkdir(parents=True, exist_ok=True)
    BAKIYE.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n")
    if vid:
        v = O.load(vid)
        U = yukle(v)
        U["denetim"].append({"tarih": b["tarih"], "an": an, "kalan": int(kalan), "is": is_})
        kaydet(v, U)
    return b


def is_harcamasi(v, bas: float, bit: float) -> int | None:
    """Bir Claude işinin [bas, bit] aralığındaki bakiye okumalarından harcanan kredi (ilk "bas" − son "son"); okuma yoksa None."""
    if not var_mi(v):
        return None
    D = [d for d in yukle(v)["denetim"] if bas - 5 <= dt.datetime.fromisoformat(d["tarih"]).timestamp() <= bit + 5]
    b = [d["kalan"] for d in D if d["an"] == "bas"]
    s = [d["kalan"] for d in D if d["an"] == "son"]
    return (b[0] - s[-1]) if b and s else None


# ---------------------------------------------------------------- indirme ve ölçüm
PARCA = 8                      # Magnific'in dosya sunucusu bağlantı başına yavaş akıtabiliyor (ölçülen 90–280 KB/sn): parçalı, paralel indir
DURGUN_SN = 30                 # bu kadar saniye veri gelmezse parça kaldığı yerden yeniden istenir
SON_SURE = 15 * 60             # bütün indirme için üst sınır


def _parca_indir(url: str, bas: int, bit: int | None, ilerleme: list, i: int) -> bytes:
    """[bas, bit] aralığını indirir; durursa ya da bağlantı erken kapanırsa kaldığı yerden yeniden ister (en çok 10 deneme)."""
    buf = bytearray()
    beklenen = None if bit is None else bit - bas + 1
    for deneme in range(10):
        h = dict(UA)
        if bit is not None or bas:
            h["Range"] = f"bytes={bas + len(buf)}-{'' if bit is None else bit}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=DURGUN_SN) as r:
                while True:
                    b = r.read(256 * 1024)
                    if not b:
                        break
                    buf += b
                    ilerleme[i] = len(buf)
                    if len(buf) > EN_BUYUK:
                        raise SystemExit("dosya 1 GB'tan büyük")
            if beklenen is None or len(buf) >= beklenen:
                return bytes(buf)
            continue  # bağlantı erken kapandı: kalanını iste
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404, 410):
                raise SystemExit(f"bağlantı açılmadı ({e.code}): bağlantının süresi dolmuş olabilir. creations_get ile yeni bağlantı al, "
                                 "hemen yeniden ./st uret al")
            if deneme == 9:
                raise SystemExit(f"indirilemedi: HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if deneme == 9:
                raise SystemExit(f"indirilemedi: {getattr(e, 'reason', e)}")
        time.sleep(min(1 + deneme, 5))
    raise SystemExit("indirilemedi")


def _indir(url: str) -> tuple[bytes, str]:
    """Magnific dosya bağlantısı → bayt. Boyut ve aralık desteği küçük bir aralık isteğiyle öğrenilir; büyük dosya 8 paralel parçayla
    indirilir, takılan parça kaldığı yerden yeniden istenir, ilerleme yazılır; sunucu MD5 veriyorsa bütünlük denetlenir."""
    import base64
    import concurrent.futures as cf
    u = urllib.parse.urlparse(url)
    if u.scheme != "https":
        raise SystemExit("--url https olmalı (Magnific'in verdiği dosya bağlantısı)")
    toplam, ctype, md5 = None, "", None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, "Range": "bytes=0-0"}), timeout=DURGUN_SN) as r:
            ctype = r.headers.get("Content-Type", "")
            m = re.search(r"/(\d+)$", r.headers.get("Content-Range", ""))
            toplam = int(m.group(1)) if r.status == 206 and m else None
            for hh in r.headers.get_all("x-goog-hash") or []:
                if hh.startswith("md5="):
                    md5 = base64.b64decode(hh[4:]).hex()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404, 410):
            raise SystemExit(f"bağlantı açılmadı ({e.code}): bağlantının süresi dolmuş olabilir. creations_get ile yeni bağlantı al, hemen yeniden ./st uret al")
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
    if toplam and toplam > EN_BUYUK:
        raise SystemExit("dosya 1 GB'tan büyük")
    n = PARCA if toplam and toplam > 2 * 1024 * 1024 else 1
    sinirlar = [(k * toplam // n, (k + 1) * toplam // n - 1) for k in range(n)] if toplam else [(0, None)]
    ilerleme = [0] * len(sinirlar)
    bas, son_yazi = time.time(), time.time()
    with cf.ThreadPoolExecutor(len(sinirlar)) as ex:
        isler = [ex.submit(_parca_indir, url, a, b, ilerleme, i) for i, (a, b) in enumerate(sinirlar)]
        while not all(f.done() for f in isler):
            time.sleep(0.5)
            if time.time() - bas > SON_SURE:
                raise SystemExit(f"indirme {SON_SURE // 60} dakikada bitmedi: bağlantıyı (creations_get) yenileyip yeniden dene")
            if time.time() - son_yazi > 10:
                son_yazi = time.time()
                print(f"   indiriliyor: {sum(ilerleme) / 1e6:.1f}" + (f" / {toplam / 1e6:.1f}" if toplam else "") + " MB", flush=True)
        veri = b"".join(f.result() for f in isler)
    if toplam and len(veri) != toplam:
        raise SystemExit(f"eksik indirildi: {len(veri)} / {toplam} bayt")
    if md5 and hashlib.md5(veri).hexdigest() != md5:
        raise SystemExit("indirilen dosya bozuk (MD5 sunucununkiyle aynı değil): yeniden dene")
    print(f"   indirildi: {len(veri) / 1e6:.1f} MB · {time.time() - bas:.0f} sn" + (" · MD5 doğrulandı" if md5 else ""), flush=True)
    return veri, ctype


def _uzanti(veri: bytes, ctype: str, url: str) -> str:
    b = veri[:16]
    if b.startswith(b"\x89PNG"):
        return ".png"
    if b.startswith(b"\xff\xd8"):
        return ".jpg"
    if b[:4] == b"RIFF" and veri[8:12] == b"WEBP":
        return ".webp"
    if b[:4] == b"RIFF" and veri[8:12] == b"WAVE":
        return ".wav"
    if veri[4:8] == b"ftyp":
        return ".mov" if veri[8:10] == b"qt" else ".mp4"
    if b.startswith(b"glTF"):
        return ".glb"
    if b.startswith(b"ID3") or b[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3"
    if b.startswith(b"OggS"):
        return ".ogg"
    if b.startswith(b"\x1aE\xdf\xa3"):
        return ".webm"
    if b.startswith(b"PK"):
        return ".zip"
    if b.startswith(b"Kaydara FBX"):
        return ".fbx"
    uz = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if uz in (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".wav", ".mp3", ".glb", ".gltf", ".fbx", ".obj", ".usdz", ".zip", ".svg"):
        return ".jpg" if uz == ".jpeg" else uz
    if "svg" in ctype or veri.lstrip()[:5] in (b"<?xml", b"<svg "):
        return ".svg"
    raise SystemExit(f"dosya türü tanınmadı (Content-Type {ctype or '—'})")


def olcu(p: Path) -> dict:
    """ffprobe: görsel en × boy; video kare hızı, süre, çözünürlük, ses var mı; ses süresi."""
    if p.suffix in (".glb", ".gltf", ".fbx", ".obj", ".usdz", ".zip", ".svg"):
        return {"bayt": p.stat().st_size}
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffprobe okuyamadı: {p.name}")
    J = json.loads(r.stdout)
    vs = next((s for s in J.get("streams", []) if s.get("codec_type") == "video"), None)
    au = next((s for s in J.get("streams", []) if s.get("codec_type") == "audio"), None)
    d = {"bayt": p.stat().st_size}
    if vs:
        d.update(en=vs.get("width"), boy=vs.get("height"))
    hareketli = vs is not None and p.suffix in (".mp4", ".mov", ".webm")
    if hareketli:
        n, _, m = (vs.get("avg_frame_rate") or vs.get("r_frame_rate") or "0/1").partition("/")
        d.update(fps=round(float(n) / float(m or 1), 3) if float(m or 1) else None, sure=round(float(J["format"].get("duration") or 0), 3),
                 codec=vs.get("codec_name"), ses=au is not None, kare=int(vs["nb_frames"]) if str(vs.get("nb_frames", "")).isdigit() else None)
    elif au is not None:
        d.update(sure=round(float(J["format"].get("duration") or 0), 3), ornekleme=int(au.get("sample_rate") or 0), kanal=au.get("channels"))
    return d


def _ffmpeg(*args):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg: " + r.stderr.strip()[-600:])


# ---------------------------------------------------------------- al, liste, sil
AD = re.compile(r"[a-z][a-z0-9_-]{1,40}")


def _varlik_satiri(x: dict) -> str:
    kaynak = (f"stok: Magnific/Freepik {x.get('model') or ''}".strip() if x["tur"] == "stok" else f"üretim: Magnific {x.get('model') or ''}".strip())
    olc_ = x.get("olcu") or {}
    boyut = f"{olc_['en']}×{olc_['boy']}" if olc_.get("en") else ""
    ek = " · ".join(filter(None, [boyut, f"{olc_['sure']:g} sn" if olc_.get("sure") else "", f"{olc_['fps']:g} kare/sn" if olc_.get("fps") else ""]))
    yz = "yapay zekâ" if x.get("yz") else "stok"
    return (f"| {x['ad']} ({yz}: {TUR_AD.get(x['tur'], x['tur'])}) | {x['yayin']} | {TUR_AD.get(x['tur'], x['tur'])} | "
            f"{x['lisans']} · {x.get('arac') or '—'} · {x['tarih'][:10]} · {x.get('kredi', 0)} kredi{' · ' + ek if ek else ''}"
            f"{' · ekranda etiket gerekli' if x.get('etiket_gerekli') else ''} | ✅ onaylı · {kaynak} |")


def _varliklar_md(v, x: dict | None = None, sil_: str | None = None):
    md = v.dir / "varliklar.md"
    if not md.exists():
        md.write_text((O.ROOT / "sablon" / "video" / "varliklar.md").read_text()
                      .replace("{{BASLIK}}", v.script.get("title", v.id)).replace("{{ID}}", v.id))
    satirlar = md.read_text().splitlines()
    if sil_:
        satirlar = [ln for ln in satirlar if not (ln.startswith("|") and f"| {sil_} |" in ln)]
    if x:
        yeni = _varlik_satiri(x)
        satirlar = [ln for ln in satirlar if not (ln.startswith("|") and f"| {x['yayin']} |" in ln)]
        i = next((i for i, ln in enumerate(satirlar) if re.match(r"^\| \[ad\]", ln)), None)
        if i is not None:
            satirlar[i] = yeni
        else:
            satirlar.append(yeni)
    md.write_text("\n".join(satirlar).rstrip() + "\n")


def al(vid: str, ad: str, url: str, tur: str, model: str = "", arac: str = "", istem: str = "", kredi: int = 0, parametre: dict | None = None,
       kaynak_kare: str | None = None, insan: bool = False, etiket: bool = False, uyum: bool = False, ses_kalsin: bool = False) -> dict:
    v = O.load(vid)
    if not AD.fullmatch(ad):
        raise SystemExit(f"ad: küçük harf, rakam, - ve _ (2–41 karakter), harfle başlar: {ad}")
    if tur not in TURLER:
        raise SystemExit(f"--tur: {' | '.join(TURLER)}")
    anahtar = None
    if tur == "anlatim":  # Magnific anlatıcı parçası: ad = anlatim_<anahtar> (./st uret anlatim verir); motor kopyası ve varliklar.md satırı yok
        anahtar = ad[len("anlatim_"):] if ad.startswith("anlatim_") else ""
        if not re.fullmatch(r"[0-9a-f]{16}", anahtar):
            raise SystemExit(f"anlatım parçasının adı anlatim_<anahtar> olmalı (./st uret anlatim {vid} listeler): {ad}")
    U = yukle(v)
    if any(x["ad"] == ad for x in U["varliklar"]):
        raise SystemExit(f"{ad} zaten var. Yeniden üretimde eski varlık kalır, yenisi yeni adla gelir (ör. {ad}_2); kullanılmayan eski: ./st uret sil {vid} {ad}")
    veri, ctype = _indir(url)
    uz = _uzanti(veri, ctype, url)
    D = depo(v)
    D.mkdir(parents=True, exist_ok=True)
    asil = (D / "anlatim" / f"{anahtar}{uz}") if anahtar else (D / f"{ad}{uz}")
    asil.parent.mkdir(parents=True, exist_ok=True)
    asil.write_bytes(veri)
    o = olcu(asil)
    ham, islem, uyari = None, [], []
    if "fps" in o and o.get("fps"):
        sesli = o.get("ses") and not ses_kalsin
        fps_farki = abs(o["fps"] - v.fps) > 0.01
        if fps_farki and not uyum:
            uyari.append(f"klip {o['fps']:g} kare/sn, film {v.fps}: hareket sekebilir. Ya --uyum ile bir kez dönüştür ya da filmi {o['fps']:g} kare/sn kur (zanaat §9)")
        if sesli or (fps_farki and uyum):
            (D / "_ham").mkdir(exist_ok=True)
            ham = D / "_ham" / asil.name
            shutil.move(str(asil), ham)
            if fps_farki and uyum:  # bir kez yeniden kodla, dondur (kare çoğaltma; ara kare uydurmaz)
                asil = asil.with_suffix(".mp4")
                _ffmpeg("-i", str(ham), "-an", "-vf", f"fps={v.fps}", "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
                        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", str(asil))
                islem.append(f"{o['fps']:g}→{v.fps} kare/sn (ffmpeg fps, kare çoğaltma)")
            else:  # yalnız sesi at: yeniden kodlama yok
                _ffmpeg("-i", str(ham), "-an", "-c:v", "copy", "-map_metadata", "-1", "-fflags", "+bitexact", str(asil))
            if sesli:
                islem.append("modelin sesi çıkarıldı (ses işaret listesinden gelir, kural 9)")
            o = {**olcu(asil), "kaynak_olcu": o}
    if anahtar:
        if anahtar not in {p["anahtar"] for p in anlatim_durumu(v)["parcalar"]}:
            uyari.append("bu anahtar bugünkü senaryoda yok (metin, ses ya da model değişmiş olabilir): ./st uret anlatim " + vid)
    else:
        pub = v.pub / "varliklar" / "uretim" / asil.name
        pub.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asil, pub)
    x = {"ad": ad, "dosya": str(asil.relative_to(v.dir)), "yayin": None if anahtar else f"varliklar/uretim/{asil.name}", "sha256": _sha(asil), "tur": tur,
         "model": model, "arac": arac, "istem": istem, "parametreler": parametre or {}, "kredi": int(kredi), "tarih": _simdi(),
         "lisans": LISANS_STOK if tur == "stok" else LISANS_YZ, "yz": tur != "stok", "insan": bool(insan),
         "etiket_gerekli": bool(insan or etiket), "kaynak_kare": kaynak_kare, "olcu": o,
         "ham": {"dosya": str(ham.relative_to(v.dir)), "sha256": _sha(ham)} if ham else None, "islem": islem, "kullanildigi": []}
    U["varliklar"].append(x)
    # kredi: panel işinde kanca harcamayı çağrı anında yazdı (bağlanmamış son kayıt bu varlığındır); kancasız (etkileşimli) oturumda al yazar
    acik = next((h for h in reversed(U["harcama"]) if h.get("kaynak") == "kanca" and not h.get("varlik") and (not arac or h.get("arac") == arac)), None)
    if acik:
        acik["varlik"] = ad
        if kredi and int(kredi) != acik["kredi"]:
            uyari.append(f"kancanın yazdığı tahmin {acik['kredi']}, --kredi {kredi}: harcama tahminle kaldı")
    elif kredi:
        U["harcama"].append({"tarih": x["tarih"], "arac": arac, "kredi": int(kredi), "kaynak": "al", "varlik": ad})
    kaydet(v, U)
    if not anahtar:
        _varliklar_md(v, x)
    x["uyari"] = uyari
    return x


def anlatim_durumu(v) -> dict:
    """Anlatıcısı Magnific olan filmin parçaları ve hangilerinin dondurulmuş klibi eksik (pipeline/tts.py ile aynı anahtar)."""
    import tts
    if (v.script.get("ses") or {}).get("kaynak") != "magnific" or not v.script.get("sentences"):
        return {"magnific": False, "parcalar": [], "eksik": [], "ayar": {}}
    P = tts.magnific_parcalari(v.script)
    return {"magnific": True, "parcalar": P, "eksik": [p for p in P if not tts.magnific_klibi(v.id, p["anahtar"])], "ayar": tts.magnific_ayar(v.script)}


def kullanim(v) -> dict[str, list[str]]:
    """Her üretim varlığının kodda geçtiği dosyalar ve script.json → etiketler'deki vuruşlar."""
    U = yukle(v)
    dosyalar = []
    src = O.ROOT / "src" / v.script.get("kod", v.id)
    if src.exists():
        dosyalar += list(src.rglob("*.ts*"))
    hfd = O.ROOT / "hf" / v.id
    if hfd.exists():
        dosyalar += [p for p in [hfd / "index.html", *(hfd / "compositions").rglob("*.html")] if p.exists()]
    bd = O.ROOT / "blender" / v.id
    if bd.exists():
        dosyalar += list(bd.rglob("*.py"))
    if (v.dir / "ses.py").exists():  # efekt sesleri (--tur ses) ses tasarımında okunur
        dosyalar.append(v.dir / "ses.py")
    metin = {p: p.read_text(errors="replace") for p in dosyalar}
    out = {}
    gkul = {}  # gerçek görüntü kaydı üzerinden kullanım (3b: <Derinlik25D ad="plaka">, <Stilize …>, uretim:<ad> ya da stok:<ad> ile eklenmiş)
    if (v.dir / "goruntu" / "goruntu.json").exists():
        import goruntu
        gk = goruntu.kullanim(v)
        for g in goruntu.yukle(v)["varliklar"]:
            if g.get("uretim") and gk.get(g["ad"]):
                gkul.setdefault(g["uretim"], []).extend(gk[g["ad"]])
    A = {p["anahtar"]: p["cumle"] for p in anlatim_durumu(v)["parcalar"]} if any(x["tur"] == "anlatim" for x in U["varliklar"]) else {}
    for x in U["varliklar"]:
        if x["tur"] == "anlatim":
            k = x["ad"][len("anlatim_"):]
            out[x["ad"]] = [f"anlatım {A[k]}"] if k in A else []
            continue
        dosya = Path(x["yayin"]).name
        yer = [str(p.relative_to(O.ROOT)) for p, t in metin.items() if re.search(r"uretim/" + re.escape(dosya) + r"\b", t)]
        yer += [y for y in gkul.get(x["ad"], []) if y not in yer]
        yer += [f"vuruş {e.get('vurus')}" for e in (v.script.get("etiketler") or []) if e.get("varlik") == x["ad"]]
        out[x["ad"]] = yer
    return out


def sil(vid: str, ad: str) -> dict:
    v = O.load(vid)
    U = yukle(v)
    x = next((x for x in U["varliklar"] if x["ad"] == ad), None)
    if not x:
        raise SystemExit(f"üretim deposunda yok: {ad}")
    yer = [y for y in kullanim(v).get(ad, []) if not y.startswith("vuruş")]
    if yer:
        raise SystemExit(f"{ad} kullanılıyor: {', '.join(yer)}. Önce sahneden çıkar.")
    for p in (v.dir / x["dosya"], *([v.pub / x["yayin"]] if x.get("yayin") else []), *([v.dir / x["ham"]["dosya"]] if x.get("ham") else [])):
        p.unlink(missing_ok=True)
    U["varliklar"] = [y for y in U["varliklar"] if y["ad"] != ad]
    U["silinen"].append({"ad": ad, "model": x.get("model"), "kredi": x.get("kredi"), "tarih": _simdi()})  # harcama kaydı yerinde kalır
    kaydet(v, U)
    if x.get("yayin"):
        _varliklar_md(v, sil_=x["yayin"])
    return x


def yukle_put(dosya: str, url: str) -> int:
    """Yerel dosya → creations_request_upload'un verdiği imzalı PUT bağlantısı (Claude'un Bash'i curl çalıştırmaz)."""
    p = Path(dosya).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"dosya yok: {p}")
    if urllib.parse.urlparse(url).scheme != "https":
        raise SystemExit("--put https olmalı")
    tip = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".mp4": "video/mp4", ".wav": "audio/wav",
           ".mp3": "audio/mpeg"}.get(p.suffix.lower(), "application/octet-stream")
    req = urllib.request.Request(url, data=p.read_bytes(), method="PUT", headers={**UA, "Content-Type": tip})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.status


# ---------------------------------------------------------------- denetim: dondurma, etiket, beyan
def dogrula(v) -> list[tuple[str, bool, str]]:
    """Dondurulmuş girdiler: asıl ve motorun okuduğu kopya kayıttaki sha256'yla aynı mı?"""
    out = []
    for x in yukle(v)["varliklar"]:
        for p in (v.dir / x["dosya"], *([v.pub / x["yayin"]] if x.get("yayin") else [])):
            if not p.exists():
                out.append((x["ad"], False, f"yok: {p.relative_to(O.ROOT)}"))
            elif _sha(p) != x["sha256"]:
                out.append((x["ad"], False, f"değişmiş: {p.relative_to(O.ROOT)} (sha256 kayıttakiyle aynı değil)"))
            else:
                out.append((x["ad"], True, str(p.relative_to(O.ROOT))))
    return out


def etiket_durumu(v) -> dict:
    """Etiket gerektiren (gerçekçi insan canlandırması ya da elle istenmiş) varlık kodda kullanılıyorsa script.json → etiketler'de kaydı olmalı."""
    U = yukle(v)
    kul = kullanim(v)
    E = v.script.get("etiketler") or []
    gerekli = [x["ad"] for x in U["varliklar"] if x.get("etiket_gerekli") and any(not y.startswith("vuruş") for y in kul.get(x["ad"], []))]
    eksik = [a for a in gerekli if not any(e.get("varlik") in (a, None, "") for e in E)]
    kod = " ".join(p.read_text(errors="replace") for p in _kod_dosyalari(v))
    bilesen = bool(re.search(r"<Etiket\b|class=[\"'][^\"']*\betiket\b", kod))
    return {"gerekli": gerekli, "eksik": eksik, "etiketler": E, "bilesen": bilesen}


def _kod_dosyalari(v) -> list[Path]:
    src = O.ROOT / "src" / v.script.get("kod", v.id)
    hfd = O.ROOT / "hf" / v.id
    return ([*src.rglob("*.ts*")] if src.exists() else []) + ([p for p in [hfd / "index.html", *(hfd / "compositions").rglob("*.html")] if p.exists()]
                                                             if hfd.exists() else [])


BEYAN_BAS, BEYAN_SON = "<!-- yz-beyan: ./st yayin uretim.json'dan doldurur; elle değiştirme -->", "<!-- /yz-beyan -->"


def beyan_md(v) -> str:
    """yayin.md → "Yapay zekâ beyanı": uretim.json (Magnific), müzik kaynağı (ACE-Step) ve anlatım kaynağından (sentetik ses)."""
    U = yukle(v) if var_mi(v) else {"varliklar": []}
    kul = kullanim(v) if var_mi(v) else {}
    yz = [x for x in U["varliklar"] if x.get("yz") and x["tur"] != "anlatim"]
    anl = [x for x in U["varliklar"] if x["tur"] == "anlatim" and (kul.get(x["ad"]) or [])]
    stok = [x for x in U["varliklar"] if not x.get("yz")]
    ace = v.ses.get("muzik_kaynagi") == "ace" and v.ses.get("muzik")
    tts = v.anlatim and v.ses.get("kaynak") in ("edge", "opencode")
    L = [BEYAN_BAS, "## Yapay zekâ beyanı"]
    if not (yz or anl or stok or ace or tts):
        L += ["Bu filmde yapay zekâ ile üretilmiş görsel, video, ses ya da müzik yok (üretim deposu boş, müzik ve anlatım yapay zekâsız).", BEYAN_SON]
        return "\n".join(L)
    if yz:
        L.append("**Yapay zekâ ile üretilenler** (Magnific, ticari yapay zekâ lisansı):")
        for x in yz:
            k = kul.get(x["ad"]) or []
            vurus = [y for y in k if y.startswith("vuruş")]  # okuyan için vuruş adları; yoksa sahne kodunun dosyası
            yer = ", ".join(vurus or k) or "henüz sahnede değil"
            L.append(f"- {x['ad']}: {TUR_AD.get(x['tur'], x['tur'])} · {x.get('model') or '—'} · kullanıldığı yer: {yer}"
                     + (" · ekranda etiketli canlandırma" if x.get("etiket_gerekli") else ""))
    if anl:
        ad_ = (v.script.get("ses") or {}).get("ses_adi") or "Magnific sesi"
        if not yz:
            L.append("**Yapay zekâ ile üretilenler** (Magnific, ticari yapay zekâ lisansı):")
        L.append(f"- Anlatım: sentetik ses (Magnific · {anl[0].get('model') or 'ElevenLabs · ' + ad_}) · {len(anl)} parça · bütün film boyunca")
    if ace:
        L.append("- Müzik: ACE-Step 1.5 (bu bilgisayarda çalışan yapay zekâ modeli, MIT lisanslı)")
    if tts:
        L.append(f"- Anlatım: sentetik ses ({'Edge TTS' if v.ses.get('kaynak') == 'edge' else 'OpenCode / Gemini'})")
    if stok:
        L.append("**Stok** (Magnific/Freepik stok lisansı; yapay zekâ değil, lisans koşulları geçerli): " + ", ".join(x["ad"] for x in stok))
    if yz or anl:
        gercekci = any(x["tur"] in ("gorsel", "video") for x in yz)
        L += ["**Yüklerken açılacak beyanlar:**",
              f"- YouTube: \"Değiştirilmiş veya yapay içerik\" → {'Evet (gerçekçi görüntü var)' if gercekci else 'gerçekçi görüntü yoksa Hayır; emin değilsen Evet'}",
              "- Instagram / Facebook (Meta): \"AI info\" / yapay zekâ etiketi açık",
              "- TikTok: yapay zekâ ile üretilmiş içerik etiketi açık",
              "- Google Ads: \"How this ad was made\" (reklamın nasıl yapıldığı) beyanı",
              "**Hatırlatma:** Türkiye Ticari Reklam ve Haksız Ticari Uygulamalar Yönetmeliği (1 Ağustos 2026'dan beri) yapay zekâ içeriğinin açıkça "
              "belirtilmesini ister; gerçek kişinin yanıltıcı yapay zekâ kopyası yasaktır. AB'de yayında Yapay Zekâ Yasası md. 50 (gerçekçi sentetik "
              "içerik etiketlenir). Etiket tek başına hukuka uygunluk sağlamaz; bağış ilanının yönetmelik kapsamı kurumun hukuk birimine sorulur."]
    L.append(BEYAN_SON)
    return "\n".join(L)


def beyan_yaz(v) -> Path | None:
    """yayin.md'deki beyan bloğunu yeniler (dosya varsa); yoksa None."""
    p = v.dir / "yayin.md"
    if not p.exists():
        return None
    t = p.read_text()
    blok = beyan_md(v)
    if BEYAN_BAS in t and BEYAN_SON in t:
        t = t[:t.index(BEYAN_BAS)] + blok + t[t.index(BEYAN_SON) + len(BEYAN_SON):]
    elif "\n## Yapay zekâ beyanı" in t:  # işaretleri silinmiş eski blok: başlığından bir sonraki başlığa kadar yenilenir
        a = t.index("\n## Yapay zekâ beyanı") + 1
        b = t.find("\n## ", a)
        t = t[:a] + blok + ("\n" + t[b:] if b >= 0 else "\n")
    elif "\n## Dosyalar" in t:
        t = t.replace("\n## Dosyalar", "\n" + blok + "\n\n## Dosyalar", 1)
    else:
        t = t.rstrip() + "\n\n" + blok + "\n"
    p.write_text(t)
    return p


def beyan_dolu(v) -> bool | None:
    """yayin.md'de beyan bloğu dolu mu? yayin.md yoksa None."""
    p = v.dir / "yayin.md"
    if not p.exists():
        return None
    t = p.read_text()
    if BEYAN_BAS not in t or BEYAN_SON not in t:
        return False
    blok = t[t.index(BEYAN_BAS):t.index(BEYAN_SON)]
    return "**Yapay zekâ ile üretilenler**" in blok and not O.PLACEHOLDER.search(blok)


# ---------------------------------------------------------------- panel özeti
def ozet(v) -> dict:
    """Panel: film sayfasındaki kredi göstergesi ve üretim listesi."""
    U = yukle(v) if var_mi(v) else {"varliklar": [], "harcama": [], "denetim": []}
    s = sinir(v.id)
    h = harcanan(U)
    kul = kullanim(v) if U["varliklar"] else {}
    return {"var": bool(U["varliklar"] or U["harcama"]), "sinir": s, "harcanan": h, "kalan": s - h,
            "varliklar": [{"ad": x["ad"], "tur": x["tur"], "model": x.get("model"), "kredi": x.get("kredi", 0), "yayin": x["yayin"],
                           "dosya": str((v.dir / x["dosya"]).relative_to(O.KANAL)), "etiket": x.get("etiket_gerekli"), "olcu": x.get("olcu"),
                           "istem": x.get("istem", ""), "kullanildigi": kul.get(x["ad"], []), "tarih": x["tarih"]} for x in U["varliklar"]],
            "denetim": U["denetim"][-6:]}
