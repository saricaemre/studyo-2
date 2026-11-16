"""Stüdyo paneli: tarayıcıda açılan yerel kontrol paneli.

Yalnız bu bilgisayardan erişilir (127.0.0.1). Komutları `./st` üzerinden çalıştırır, dosyaları stüdyo klasöründen sunar.
Başlatma: ./st panel   (ya da Youtube/Panel.command dosyasına çift tıkla)
"""
import argparse
import array
import datetime as dt
import hashlib
import json
import math
import mimetypes
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

PANEL = Path(__file__).resolve().parent
sys.path.insert(0, str(PANEL.parent / "pipeline"))
import ortak as O  # noqa: E402
import st  # noqa: E402
import uretim  # noqa: E402
import goruntu  # noqa: E402
import takip as kamera_takibi  # noqa: E402
import veri as canli_veri  # noqa: E402  (do_POST içinde "veri" yerel değişkeni yüklenen baytlardır)
import kisisel  # noqa: E402  (kişisel etki filmi: ./st toplu; veri videos/<id>/toplu/, Claude'a kapalı)
import yapim  # noqa: E402  (yapım filmi, "nasıl yapıldı": ./st yapim)

KOK = O.KANAL.resolve()            # Youtube/
STUDIO = O.ROOT                    # Youtube/studio
PY = str(STUDIO / ".venv" / "bin" / "python")

# Panelden çalıştırılabilen komutlar (beyaz liste)
KOMUTLAR = {
    "lint": ["lint"], "cekim": ["cekim"], "ses": ["ses"], "vurus": ["vurus"], "muzik": ["muzik"],
    "temsili": ["temsili"], "kaba": ["render"], "inceleme": ["inceleme"], "olc": ["olc"],
    "final": ["render", "--final"], "deterministik": ["deterministik"], "yayin": ["yayin"], "elestir": ["elestir"], "gorunus": ["gorunus"],
    "blender-ac": ["blender", "ac"],   # Blender videosu: sahneyi Blender arayüzünde açar (./st blender <id> ac)
}
DUZENLENEBILIR = {"brief.md", "kaynaklar.md", "varliklar.md", "yayin.md", "script.json", "cues.json"}


# ---------------------------------------------------------------- işler (arka plan komutları)
ISDIR = PANEL / "isler"   # her iş: <id>.log (çıktı) + <id>.json (kayıt). Panel kapansa da iş sürer, açılınca geri yüklenir.
BITTI = ("bitti", "hata", "durduruldu")


class Is:
    tur = "komut"

    def __init__(self, ad, cmd, video=None, cwd=None, bitince=None, _meta=None, env_ek=None):
        self.bitince, self.cikti, self.proc = bitince, [], None
        if _meta:  # panel yeniden açıldı: kayıtlı işi geri yükle
            m = _meta
            self.id, self.ad, self.video, self.bas, self.pid = m["id"], m["ad"], m.get("video"), m["bas"], m.get("pid")
            self.cwd, self.cmd = Path(m.get("cwd", STUDIO)), []
            self.durum, self.kod, self.bit = m.get("durum", "çalışıyor"), m.get("kod"), m.get("bit")
        else:
            self.id = uuid.uuid4().hex[:10]
            self.ad, self.cmd, self.video, self.cwd = ad, cmd, video, cwd or STUDIO
            self.durum, self.kod, self.bas, self.bit = "çalışıyor", None, time.time(), None
            ISDIR.mkdir(exist_ok=True)
            with open(ISDIR / f"{self.id}.log", "w") as f:
                # Ayrı oturumda başlar ve çıktısını dosyaya yazar: panel kapanınca iş ölmez.
                self.proc = subprocess.Popen(["/bin/sh", "-c", '"$@"; echo "__CIKIS__ $?"', "sh", *cmd], cwd=self.cwd,
                                             stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True,
                                             env={**os.environ, "FORCE_COLOR": "0", "PYTHONUNBUFFERED": "1", **(env_ek or {})})
            self.pid = self.proc.pid
            self.meta_yaz()
        self.log = ISDIR / f"{self.id}.log"
        if self.durum in BITTI:  # eskiden bitmiş: yalnız günlüğü oku
            self._oku_hepsi()
        else:
            threading.Thread(target=self._izle, daemon=True).start()

    def ek_meta(self):
        return {}

    def meta_yaz(self):
        (ISDIR / f"{self.id}.json").write_text(json.dumps({
            "id": self.id, "ad": self.ad, "video": self.video, "tur": self.tur, "bas": self.bas, "bit": self.bit, "pid": self.pid,
            "cwd": str(self.cwd), "durum": self.durum, "kod": self.kod, **self.ek_meta()}, ensure_ascii=False))

    def satir(self, line):
        return re.sub(r"\x1b\[[0-9;]*m", "", line.rstrip("\n"))

    def _isle(self, ln):
        m = re.match(r"^__CIKIS__ (\d+)\s*$", ln)
        if m:
            self.kod = int(m.group(1))
            return
        out = self.satir(ln)
        if out:
            self.cikti.append(out)

    def _oku_hepsi(self):
        if self.log.exists():
            for ln in self.log.read_text(errors="replace").splitlines():
                self._isle(ln)

    def _canli(self):
        if self.proc:
            return self.proc.poll() is None
        try:
            os.kill(self.pid, 0)
            return True
        except (OSError, TypeError):
            return False

    def _izle(self):
        pos, buf = 0, ""
        while True:
            alive = self._canli()
            try:
                with open(self.log, "r", errors="replace") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
            except FileNotFoundError:
                chunk = ""
            buf += chunk
            *lines, buf = buf.split("\n")
            for ln in lines:
                self._isle(ln)
            if not alive and not chunk:
                if buf:
                    self._isle(buf)
                break
            time.sleep(0.5)
        if self.durum == "çalışıyor":
            self.durum = "bitti" if self.kod == 0 else "hata"
        self.bit = self.bit or time.time()
        self.meta_yaz()
        if self.bitince:
            try:
                self.bitince(self)
            except Exception as e:  # noqa: BLE001
                self.cikti.append(f"(bitiş adımı hatası: {e})")

    def durdur(self):
        if self.durum == "çalışıyor":
            self.durum = "durduruldu"
            try:
                os.killpg(self.pid, signal.SIGTERM)
            except OSError:
                pass
            self.meta_yaz()

    def ozet(self, offset=0):
        return {"id": self.id, "ad": self.ad, "video": self.video, "tur": self.tur, "durum": self.durum, "kod": self.kod,
                "sure": round((self.bit or time.time()) - self.bas, 1), "satirlar": self.cikti[offset:], "toplam": len(self.cikti)}


class ClaudeIs(Is):
    """Claude Code'u arka planda (claude -p) çalıştırır; akış olaylarını okunur satırlara çevirir, oturum kimliğini saklar."""
    tur = "claude"

    def __init__(self, ad, prompt, video, oturum=None, bitince=None, asama=None, _meta=None, secim=None, araclar=None):
        self.oturum, self.sonuc, self.maliyet = (_meta or {}).get("oturum", oturum), None, None
        self.asama = (_meta or {}).get("asama", asama)
        self.kredi = (_meta or {}).get("kredi")  # bu işte harcanan Magnific kredisi (işin başı ve sonundaki bakiye okumalarından)
        cmd = []
        if not _meta:
            # model ve efor aşamaya göre (panel → Claude ayarları); boşsa Claude Code'un varsayılanı
            ayar = {"plan": "plan", "plan_tamamla": "plan_tamamla", "uretim": "uretim", "devam": "uretim", "degisiklik": "degisiklik",
                    "referans": "referans", "analitik": "analitik"}.get(asama or "", "")
            kucuk = ["--model", "haiku"] if asama == "magnific" else []  # yalnız bakiye okuyan iş: küçük model yeter (aşama ayarı değil)
            cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", *(O.claude_bayraklari(ayar, secim) if ayar else kucuk),
                   "--permission-mode", "acceptEdits", "--add-dir", str(KOK), "--settings", KANCA_AYARI, "--allowedTools", *(araclar or CLAUDE_ARACLAR)]
            if oturum:
                cmd += ["--resume", oturum]
        # kanca hangi filmin kredi sınırına yazacağını buradan bilir
        super().__init__(ad, cmd, video, cwd=STUDIO, bitince=bitince, _meta=_meta, env_ek={"STUDYO_VIDEO": video} if video else None)

    def ek_meta(self):
        return {"oturum": self.oturum, "asama": self.asama, "kredi": self.kredi}

    def ozet(self, offset=0):
        return {**super().ozet(offset), "asama": self.asama}

    def satir(self, line):
        line = line.strip()
        if not line:
            return None
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            return line[:300]
        t = d.get("type")
        if t == "system" and d.get("subtype") == "init":
            self.oturum = d.get("session_id") or self.oturum
            m = d.get("model") or ""
            return "Claude başladı" + (f" · {O.CLAUDE_MODELLER.get(m, m)}" if m else "")
        if t == "assistant":
            parts = []
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "text" and c.get("text", "").strip():
                    parts.append("💬 " + c["text"].strip().replace("\n", " ")[:400])
                elif c.get("type") == "tool_use":
                    parts.append("🔧 " + arac_ozet(c.get("name", ""), c.get("input", {})))
            return "\n".join(parts) or None
        if t == "result":
            self.oturum = d.get("session_id") or self.oturum
            self.sonuc = d.get("result")
            self.maliyet = d.get("total_cost_usd")
            dk = (d.get("duration_ms") or 0) / 60000
            return f"{'✓' if d.get('subtype') == 'success' else '✗'} Claude bitirdi · {dk:.1f} dk" + (f" · ~${self.maliyet:.2f}" if self.maliyet else "")
        return None


def arac_ozet(ad, inp):
    if ad == "Bash":
        return "komut: " + str(inp.get("command", ""))[:140]
    if ad in ("Edit", "Write", "Read", "NotebookEdit"):
        p = str(inp.get("file_path", ""))
        return {"Edit": "düzenledi", "Write": "yazdı", "Read": "okudu"}.get(ad, ad) + ": " + p.replace(str(KOK) + "/", "")
    if ad == "WebSearch":
        return "web'de aradı: " + str(inp.get("query", ""))[:120]
    if ad == "WebFetch":
        return "sayfa okudu: " + str(inp.get("url", ""))[:120]
    if ad.startswith("mcp__magnific__"):
        a = ad[len("mcp__magnific__"):]
        ne = {"account_balance": "bakiyeyi okudu", "simulate_cost": "bedeli ölçtü (ücretsiz)", "images_generate": "görsel üretti",
              "video_generate": "video üretti", "creations_wait": "üretimi bekledi", "stock_search": "stokta aradı", "stock_download": "stok indirdi",
              "audio_sfx_generate": "efekt sesi üretti"}.get(a, a)
        return "Magnific: " + ne + (f" · {inp.get('mode') or inp.get('slug')}" if inp.get("mode") or inp.get("slug") else "")
    return ad


# Basit modda Claude'un yetkileri: stüdyo dosyaları, ./st, tip denetimi, kaynak araması
CLAUDE_ARACLAR = ["Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "TodoWrite", "Skill",
                  "Bash(./st:*)", "Bash(.venv/bin/python:*)", "Bash(ffprobe:*)",
                  "mcp__threejsassets",  # 3B model kataloğu ve indirme bağlantısı (kullanıcı bağlantıyı kurduysa; yoksa araç yok, zararsız)
                  # Magnific: sunucunun tamamı değil, yalnız üretim, okuma ve indirme araçları tam adlarıyla (pipeline/uretim.py); hesabı değiştirenler
                  # (paylaşma, silme, takım, marka kiti yazma, Spaces, akışlar), müzik ve TTS yok. Bağlı değilse araç yok, zararsız.
                  *uretim.mcp_araclari()]
# Kredi bekçisi: ücretli Magnific çağrısından önce kanca (./st uret butce'nin izni yoksa çağrı gitmez; müzik ve TTS hiç gitmez)
# Kişisel verinin bekçisi: videos/<id>/toplu/ (kişisel etki filmi) Claude'un dosya, arama, komut ve Magnific araçlarına kapalı (pipeline/kisisel_kanca.py)
KANCA_AYARI = json.dumps({"hooks": {"PreToolUse": [{"matcher": "mcp__magnific__.*", "hooks": [
    {"type": "command", "command": f"'{PY}' -I '{STUDIO / 'pipeline' / 'uretim_kanca.py'}'"}]},
    {"matcher": "Read|Edit|Write|MultiEdit|NotebookEdit|Glob|Grep|Bash|mcp__.*", "hooks": [
        {"type": "command", "command": f"'{PY}' -I '{STUDIO / 'pipeline' / 'kisisel_kanca.py'}'"}]}]}})
# Not: bu makinede bir kanca bash komutlarını rtk'ye yeniden yazıyor (ls, cat, npx …); o yüzden Claude'a gereken her şey ./st üzerinden.
ARAC_KURALI = ("Araç kuralı (arka plan oturumu): Bash'te yalnız ./st, .venv/bin/python ve ffprobe çalışır. Dosya okumak, listelemek, aramak için "
               "Read, Glob, Grep araçlarını kullan; sahne kodu denetimi için ./st tip <id>; dosya taşımak gerekirse Write ile yaz. "
               "HyperFrames videosunda CLI'yi npx ile değil ./st hf <id> <komut> ile çalıştır (lint, check, snapshot, timeline, keyframes, catalog, add, docs); "
               "HyperFrames becerilerini Skill aracıyla yükle. Blender videosunda Blender'ı doğrudan çalıştırma: plakaları ./st çizer "
               "(./st kare, temsili, inceleme, render; elle ./st blender <id> plaka|durum), sahne denetimi ./st tip <id>. "
               "Onay isteyen başka bir komut deneme.\n")


def goruntu_kurali(vid: str | None) -> str:
    """Arka plan Claude'una gerçek görüntü (3b, zanaat §2 B ve D, §9) kuralları: kayıt, türevler, bileşenler, rıza. Magnific'siz de geçerli."""
    v_ = f"{vid or '<id>'}"
    ozet = ""
    if vid and (STUDIO / "videos" / vid / "goruntu" / "goruntu.json").exists():
        G = goruntu.yukle(O.load(vid))["varliklar"]
        ozet = " Bu filmin kaydı: " + "; ".join(f"{x['ad']} ({x['tur']}, {goruntu.KAYNAKLAR.get(x['kaynak'], x['kaynak'])}"
                                                 + (f", kişi var, rıza {x.get('riza')}" + (f", çözüm {x['cozum']}" if x.get("cozum") else "") if x.get("kisi") else "")
                                                 + ")" for x in G) + "."
    stok = ("stok video Magnific'te kredi harcar (ücretsiz lisanslı ~150, premium ~600: stock_search → creditCost; bekçi kuralları geçerli).\n"
            if uretim.magnific_durumu()["kurulu"] else "Magnific bağlı değil: stok yok; gerçek görüntü kullanıcının dosyasından (kendi, arşiv, açık lisans).\n")
    return ("GERÇEK GÖRÜNTÜ (yol B: kendi çekim, kurum arşivi, açık lisanslı CC0, Magnific stok; yol D: gerçek görüntü kodla stilize; zanaat §2, §9):"
            f"{ozet}\n"
            f"- Kullanıcının yüklediği görüntü panelden ./st goruntu ekle ile gelir (videos/{v_}/goruntu/goruntu.json; ./st goruntu liste {v_}). Kendin eklersen: "
            f"./st goruntu ekle {v_} <dosya | stok:<üretim adı>> [--kaynak kendi|arsiv|acik] [--bas SN --son SN]. Gerçek görüntü gerçek kalır: Magnific'e kaynak "
            f"kare olarak verilmez, üzerinde kimse yeniden çizilmez (kural 2); {stok}"
            f"- Türevler bir kez üretilir, dondurulur: ./st maske {v_} <ad> (insan; nesne --kutu x0,y0,x1,y1), ./st derinlik {v_} <ad>, "
            f"./st goruntu kadraj {v_} <ad> --format <F> (her format ayrı; merkezden kırpma yok; ani geçiş uyarısında --bas/--son ile kırp). Bunlar uzun sürer: "
            "Bash'te timeout 600000 ile çalıştır, arka plana atma.\n"
            f"- Remotion: src/lib/goruntu → <Goruntu film=\"{v_}\" ad=… /> (gerçek, kadrajlı), <Stilize mod=isi|yarimton|cizgi|nokta|parcacik|gercek "
            "koru=ozne|arka gizle /> (D), <Derinlik25D sure=… odak={[u,v]} /> (2.5B, durağan görsel ya da video), <Sandvic … /> (anahtar kare sandviçi: ./st sandvic). "
            "HyperFrames'te 2.5B ve stilizasyon yalnız durağan görselde (uc.js goruntuYukle; hf/CLAUDE.md).\n"
            "- Kişi ve rıza kullanıcının işidir: bunun için sorma, bekleme, kapı koyma (kullanıcı kararı, 2026-10-27). Kullanıcı panelde bir çözüm seçtiyse "
            "(Plan → Gerçek görüntü: yüzleri gizle, stilize et, kullanma; ./st goruntu riza … --cozum) ona uy: gizle'de kişi her sahnede <Stilize … gizle /> "
            "ile, stilize'de yalnız <Stilize> ile çizilir (ölçüm denetler). Stokta ya da gerçek görüntüde ekrana etiket (“Temsilîdir” vb.) KENDİLİĞİNDEN koyma.\n"
            "- Kamera takibi (FOOH: gerçek yerde imkânsız nesne; Blender filminde): kullanıcının telefon çekimi gerçek görüntü kaydına girer, sonra "
            f"./st takip {v_} <görüntü adı> [--yukseklik M] (Blender arka planda izler, kamerayı çözer, zemini ve ölçeği kurar, dondurur; ~5–8 dk: timeout "
            "600000). Ortalama çözüm hatası 1 px'in üstündeyse ya da çözümde boşluk varsa çekimi kırp (--bas/--son) ya da kullanıcıya elle iz yolunu "
            f"söyle (panel: Plan → Kamera takibi). Sahne: import takip · takip.kamera() · nesne (kit) · takip.ortam() · takip.zemin() (gölge yakalayıcı, "
            "yalnız Cycles) · en sonda takip.katmanlar(); üst katman <TakipBirlesim> (src/lib/takip). Ekrana etiket ya da uyarı yazısı (ör. “Canlandırmadır”) KENDİLİĞİNDEN koyma: "
            "yalnız kullanıcı isterse (blender/CLAUDE.md → Kamera takibi).\n")


def veri_kurali(vid: str | None) -> str:
    """Arka plan Claude'una canlı veri (4d) kuralları: açık kaynak ve lisans, konum kullanıcının, dondurma, atıf yayın paketinde, rakam elle yazılmaz."""
    v_ = f"{vid or '<id>'}"
    ozet = ""
    if vid and (STUDIO / "videos" / vid / "veri.json").exists():
        vv = O.load(vid)
        x = canli_veri.secili(vv)
        S = canli_veri.sozlesme(vv)
        ozet = (f" Bu filmin kaynağı: {S['kaynak'].get('ad')} · {S['konum'].get('ad')} · lisans {S.get('lisans')}"
                + (f" · seçili görüntü {x['kimlik']} ({x['zaman_yerel']}): " + "; ".join(f"{d['ad']} {d['metin']} {d['birim']}" for d in x["degerler"].values())
                   if x else " · henüz anlık görüntü yok") + ".")
    return ("CANLI VERİ (gerçek ve güncel veriyle yeniden çizilen film: ./st veri, README → Canlı veri, zanaat §11; yalnız film bunu istiyorsa):"
            f"{ozet}\n"
            "- Kaynak açık ve lisansı kurum kampanyasını kapsamalı (kampanya tanıtımdır): hazır met-norway (MET Norway, CC BY 4.0, ticari ve kurum "
            "kullanımı serbest, atıf şart). Open-Meteo'nun ücretsiz katmanı tanıtımda kullanılmaz; başka bir kaynağın lisansı belirsizse durum.md'de sor. "
            "Rakam uydurulmaz: veri yoksa ekranda rakam yok.\n"
            f"- Konum kullanıcının kararıdır: söylemediyse durum.md'de sor (şehir düzeyi; kampın tam yeri hassas olabilir). ./st veri {v_} kur --saglayici "
            f"met-norway --konum \"Ad\" --enlem E --boylam B → ./st veri {v_} cek. Ağ hatasında ya da beklenmeyen veride komut durur (çıkış 2): önceki "
            "görüntüye sessizce düşme, hangi görüntüyle çizildiğini durum.md'de söyle. Çıkış 4: kaynağın önbellek süresi dolmadı, bekle.\n"
            f"- Ekrandaki her rakam seçili görüntüden: Remotion const V = useVeri('{v_}') (src/lib/veri) → V.degerler.<alan>.metin + birim; HyperFrames "
            "ST.veri.degerler.<alan>.metin; Blender ST.veri (yazı üst katmanda). Rakamı elle yazma, yeniden biçimleme; çizimde ağ yok. script.json → "
            "veri_isareti: değerlerin ekranda tam göründüğü işaret (ölçüm o kareyi okur). Atıf yayın paketinde ve kaynaklar.md'de (./st veri yazar); "
            "ekrana atıf satırı (<VeriAtif>, .veri-atif) ya da “tahmin” etiketi KENDİLİĞİNDEN koyma: yalnız kullanıcı isterse. Söylediğin her şey doğru "
            "olsun (tahmini “ölçüldü” diye sunma). Anlatım rakamı söylemez (veri değişince ses değişmez).\n")


def kisisel_kurali(vid: str | None) -> str:
    """Arka plan Claude'una kişisel etki filmi (4c) kuralları. Kişisel veri istemlere hiç girmez: yalnız şablonun alanları (adları ve türleri)."""
    v_ = f"{vid or '<id>'}"
    if not (vid and (STUDIO / "videos" / vid / kisisel.SABLON).exists()):
        return ("KİŞİSEL VERİ: videos/<id>/toplu/ (kişisel etki filminin veri dosyaları ve kişiye özel filmler) kişisel veridir: okuma, arama, "
                "özetleme, durum.md'ye ya da belleğe yazma (kanca engeller). Kişisel film şablonu istenirse README → Kişisel etki filmi.\n")
    S = kisisel.sablon(O.load(vid))
    alanlar = ", ".join(f"{k} ({a['tur']}{', ekranda' if a.get('ekranda') else ''})" for k, a in S["alanlar"].items())
    return ("KİŞİSEL ETKİ FİLMİ (bu film bir şablon: ./st toplu her satıra, her bağışçıya kendi verisiyle film çizer; README → Kişisel etki filmi):"
            f" alanlar {alanlar}.\n"
            f"- Kişisel veri (videos/{v_}/toplu/: veri dosyaları, kişiye özel filmler, önizleme) bu bilgisayarda kalır: okuma, arama, özetleme, "
            "durum.md'ye, belleğe ya da Magnific'e verme (kanca engeller). Toplu üretimi, önizlemeyi, kurum verisi notlarını (isteğe bağlı: kaynak, izin, "
            f"ekranda alanlar, gönderim, saklama) ve silmeyi kullanıcı panelden yapar; sen yalnız ./st toplu {v_} sablon|liste|denetle (ad ve değer içermez).\n"
            f"- Şablonu kurarken: ekrandaki her yazı const K = useKisi('{v_}') (src/lib/kisisel): <KisiYazi kisi={{K}} alan=\"ad\" …/> sığdırılmış "
            "satırlarla (veri_sablonu.json → yazi: Roboto Flex, ≥ 64 px; uzun ad iki satıra kırılır, sonra daralır, sığmazsa o satır atlanır), sayı "
            "K.alanlar.<alan>.sayi + birim; metni elle yazma, yeniden biçimleme. Ekrana TEST plakası ya da etiket KENDİLİĞİNDEN koyma (<KisiTest> yalnız kullanıcı isterse). "
            "kisi_isareti: ekrandaki bütün alanların tam göründüğü işaret (yazı tanıma o kareyi okur). Şablonun ornek satırı TEST'tir; gerçek kişi girmez. "
            "Sabit cümle (\"ulaştı\") kurumun verisinin söylediğini aşmaz (uydurma yok). En uzun değerle kart taşmasın: yerleşim akışta, boşluk payıyla.\n")


def magnific_kurali(vid: str | None) -> str:
    """Arka plan Claude'una Magnific kuralları: bağlıysa bekçi, etik ve dondurma; değilse üretim yolunu önermeme (Magnific bağlı olmayan kurulum)."""
    if not uretim.magnific_durumu()["kurulu"]:
        return ("MAGNIFIC bu bilgisayarda bağlı değil: yapay zekâ ile görsel ya da video üretimini (zanaat §2 yol C) önerme ve kullanma; filmi yerel "
                "yollarla kur (F, M, A, E, 3B katmanı; gerçek görüntü B ve D kullanıcının dosyasıyla yerelde çalışır). Gerçekçi görüntü şartsa "
                "durum.md'de söyle ve en iyi yerel yolu öner.\n")
    s = uretim.sinir(vid) if vid else uretim.ayarlar()["kredi_siniri"]
    h = 0
    if vid and (STUDIO / "videos" / vid / "script.json").exists():
        h = uretim.harcanan(uretim.yukle(O.load(vid)))
    return (f"MAGNIFIC (kullanıcının tek ücretli yapay zekâ kaynağı, araçlar mcp__magnific__*; kurallar zanaat.md §9):\n"
            "- Ne zaman: gerçekçi mekân, nesne, doku, metafor ya da etiketli canlandırma kodla ve 3B'yle iyi kurulamıyorsa (zanaat §2 yol C: plaka). "
            "\"Neden yapay zekâ?\" sorusunun cevabı brief'in Yönetmenlik bölümüne yazılır. Yazı plakaya gömülmez, kodla çizilir; modelin sesi kullanılmaz.\n"
            "- Etik (pazarlıksız): gerçek yararlanıcı, gerçek olay, belgesel görünümlü acı ve gerçek kişinin kopyası üretilmez. Gerçekçi insan yalnız "
            "ekranda etiketli canlandırmada: ./st uret al … --insan; Remotion <Etiket> (src/lib/Etiket.tsx), HyperFrames <div class=\"etiket\">; "
            "script.json → etiketler [{\"vurus\", \"metin\", \"varlik\"}].\n"
            f"- Kredi bekçisi: bu filmin sınırı {s} kredi (harcanan {h}). Her üretim çağrısından önce simulate_cost (ücretsiz), sonra "
            f"./st uret butce {vid or '<id>'} --tahmin <kredi> --arac <araç>. Çıkış 3 = sınır aşılıyor: DUR, üretme; durum.md'de ne için kaç kredi gerektiğini "
            "yazıp kullanıcıya sor (sınırı yalnız o yükseltir). İzinsiz ücretli çağrıyı kanca durdurur.\n"
            "- Önce ucuz modelde dene (görsel Nano Banana 2 1K/2K 75; video Kling 2.5 720p 5 sn 140, Hailuo 2.3 Fast 768p 6 sn 150), yalnız seçilen çekimi "
            "pahalı modelde üret (Kling 3.0 1080p 5 sn 450, Veo 3.1 1080p 4 sn 800). Kamera ve ışık plakalar arasında sürekli.\n"
            f"- Her üretimden HEMEN sonra (dosya bağlantısı ~30 dk geçerli): creations_wait → görselde creations_register_download'un originals[] dosyası "
            f"varsa o → ./st uret al {vid or '<id>'} <ad> --url <bağlantı> --tur gorsel|video|ses|3b|stok --model <m> --arac <araç> --istem \"…\" --kredi <n> "
            "(aynı çağrının ikinci varlığında --kredi 0). Magnific'in dosya sunucusu yavaş olabilir (7 MB ~1,5 dk): ./st uret al'ı Bash'te timeout 600000 ile "
            "çalıştır, arka plana atma, bitmesini bekle. Yeniden üretimde eski varlık kalır, yenisi yeni adla gelir. Stok: stock_search (creditCost = bedel; "
            "simulate_cost stoğu bilmez) → ./st uret butce --tahmin <creditCost> --arac stock_download → stock_download (videoda max_bytes) → ./st uret al … --tur stok → "
            "./st goruntu ekle <id> stok:<ad>. Yerel kare yüklemek: creations_request_upload → ./st uret yukle <dosya> --put <bağlantı> → creations_finalize_upload. "
            "Anahtar kare sandviçi: ./st sandvic <id> <ad> --bas SN --sure S adımları yazar (ilk ve son kare motordan; karede gerçek kişi olmamalı).\n"
            f"- Bu işte üretim yapacaksan ilk üretimden önce ve işin sonunda account_balance oku: ./st uret bakiye {vid or '<id>'} --kalan <credits.available> "
            "--an bas|son.\n"
            "- Müzik Magnific'ten üretilmez (Premium'da müzik hakkı yok): müzik ./st muzik. Anlatıcı sesi yalnız kullanıcı seçtiyse Magnific'ten "
            f"(script.json → ses.kaynak = magnific): ./st uret anlatim {vid or '<id>'} eksik parçaları metin ve anahtarıyla listeler; her parça için "
            "simulate_cost → ./st uret butce → audio_tts {text: metin AYNEN, model, voiceId, source: catalog} → creations_wait → ./st uret al "
            f"{vid or '<id>'} anlatim_<anahtar> --tur anlatim … ; sonra ./st ses. Metin değişmedikçe parça yeniden üretilmez; değişen parçanın eskisi "
            "./st uret sil ile temizlenir. Yayın paketi beyanı ./st yayin ile uretim.json'dan dolar.\n")


ISLER: dict[str, Is] = {}


def is_baslat(ad, args, video=None):
    j = Is(ad, [str(STUDIO / "st"), *args], video)
    ISLER[j.id] = j
    return j


# ---------------------------------------------------------------- veri
_TR = str.maketrans("çğıöşüâîûÇĞİÖŞÜ", "cgiosuaiucgiosu")


def slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", t.translate(_TR).lower()).strip("_")



def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(KOK))


def insanca(e: str) -> str:
    """Komut satırı dilindeki eksikleri panelde okunur hale getirir."""
    e = re.sub(r"insan onayı yok \(\./st kapi <id> \d\)", "Senin onayın bekleniyor", e)
    e = re.sub(r"^\./st temsili <id> \(eksik: (.*)\)$", r"Temsilî kareler henüz üretilmedi (\1)", e)
    e = re.sub(r"^\./st inceleme <id> \(eksik: (.*)\)$", r"Kontak tabakası ve ölçüm henüz yok (\1)", e)
    e = re.sub(r"\s*\(\./st render <id> --final\)", "", e)
    e = re.sub(r"\s*\(\./st (ses|lint)\)", "", e)
    e = re.sub(r"^yol seçilmedi: .*$", "Üç yoldan birini seç: kartlardaki “Bu yolu seç” düğmesi", e)
    return e


def kapilar(v):
    res, g = st.gate_eval(v)
    out, blocked = [], False
    yol = v.yol_modu  # planda üç yol: brief'in Yönetmenlik bölümü yol seçilince yazılır
    for n, (ad, insan) in st.GATES.items():
        ok, eksik = res[n]
        if yol and n == 1:
            eksik = ["Brief'in yönetmenlik bölümü seçtiğin yolda yazılacak" if e.startswith("brief.md'de doldurulmamış") else e for e in eksik]
        durum = "tamam" if ok else ("bekliyor" if blocked else "sirada")
        out.append({"n": n, "ad": ad, "insan": insan, "durum": durum, "eksik": [insanca(e) for e in eksik],
                    "onay": g.get(str(n), {}).get("onay"), "not": g.get(str(n), {}).get("not", "")})
        if not ok and not blocked:
            blocked = True
    return out


def poster(v):
    for f in v.formatlar:
        vs = st.final_versions(v, f)
        if vs:
            p = vs[-1].with_name(vs[-1].stem + "_poster.png")
            if p.exists():
                return rel(p)
    t = v.dir / "inceleme" / "temsili"
    for f in v.formatlar:
        kd = t / st.review_names(v, f)[1]
        if kd.exists():
            fs = sorted(kd.glob("f*.png"))
            if fs:
                return rel(fs[min(1, len(fs) - 1)])
    return None


def video_ozet(vid):
    v = O.load(vid)
    k = kapilar(v)
    return {"id": vid, "baslik": v.script.get("title", vid), "profil": v.profil["ad"], "stil": v.gorunus_etiketi,
            "formatlar": v.formatlar, "anlatim": v.anlatim, "sure": v.duration, "arsiv": v.script.get("arsiv"),
            "kapilar": [{"n": x["n"], "durum": x["durum"]} for x in k],
            "sirada": next((x for x in k if x["durum"] == "sirada"), None), "poster": poster(v), "raporZamani": analitik_ozet(v)["raporZamani"]}


def olcum_oku(p: Path):
    return O.jload(p) if p.exists() else None


def yol_konseptleri(v, S) -> dict:
    if not uretim.var_mi(v):
        return {}
    U = {x["ad"]: x for x in uretim.yukle(v)["varliklar"]}
    out = {}
    for k, o in S.items():
        x = U.get(((o.get("yol") or {}) if isinstance(o.get("yol"), dict) else {}).get("konsept") or "")
        if x and (v.dir / x["dosya"]).exists():
            out[k] = rel(v.dir / x["dosya"])
    return out


def gorunus_paneli(v):
    """Görünüş: mod, seçenekler, seçim ve deneme tabakaları (panelde seçim için)."""
    if v.gorunus_modu != "video":
        return {"mod": "seri", "etiket": v.gorunus_etiketi}
    G = v.gorunus_json() or {}
    S = G.get("secenekler") or {}
    gd = v.dir / "inceleme" / "gorunus"
    kf = {f: {k: rel(p) for k in sorted(S) for p in sorted((gd / f"{k}-{f}").glob("f*.png"), key=lambda x: x.stat().st_mtime)[-1:]} for f in v.formatlar} if gd.exists() else {}
    fk = v.dir / "fikirler.md"
    return {"mod": "video", "etiket": v.gorunus_etiketi, "secim": G.get("secim"),
            "secenekler": [{"harf": k, "ad": o.get("ad", ""), "fikir": o.get("fikir", ""), "renk": o.get("renk", {}), "yazi": o.get("yazi", {}),
                            **({"yol": o["yol"]} if isinstance(o.get("yol"), dict) else {})} for k, o in sorted(S.items())],
            "kareler": {k: rel(gd / f"{k}-{f}" / p.name) for f in v.formatlar[:1] for k in sorted(S)
                        for p in sorted((gd / f"{k}-{f}").glob("f*.png"))[:1]} if gd.exists() else {},
            "karelerFmt": kf,  # her format için seçeneklerin kanca karesi (yol kartlarında format sekmesi)
            "konseptler": yol_konseptleri(v, S),  # Magnific konsept karesi (yol.konsept → üretim deposundaki varlık); kanca karesi kodla kalır
            "yolModu": bool(G.get("yol_modu")),  # planda üç yol (2a): seçenekler ayrı fikirlerdir
            "fikirler": fk.read_text() if fk.exists() else None,
            "tabakalar": {f: rel(gd / f"gorunusler-{f}.png") for f in v.formatlar if (gd / f"gorunusler-{f}.png").exists()},
            "rapor": rel(gd / "gorunus.md") if (gd / "gorunus.md").exists() else None}


def yapim_ozeti(v) -> dict:
    """Teslim → Nasıl yapıldı filmi: yapim.ozet + sürmekte olan işin son adımı ("[3/8] kılavuz …")."""
    Y = yapim.ozet(v)
    j = next((j for j in ISLER.values() if j.video == v.id and j.durum == "çalışıyor" and j.ad.startswith("Nasıl yapıldı")), None)
    if j:
        adim = next((m for m in (re.match(r"^\[(\d+)/(\d+)\] (.*)$", ln) for ln in reversed(j.cikti)) if m), None)
        Y["suren"] = {"id": j.id, "adim": int(adim.group(1)) if adim else 0, "toplam": int(adim.group(2)) if adim else 0,
                      "metin": adim.group(3) if adim else "başlıyor", "gecen": round(time.time() - j.bas)}
    return Y


def video_detay(vid):
    v = O.load(vid)
    d = video_ozet(vid)
    d["gorunus"] = gorunus_paneli(v)
    d["kapilar"] = kapilar(v)
    d["profilDetay"] = v.profil
    d["yapi"] = v.vuruslar            # geçerli vuruş iskeleti: script.json → yapi ya da profilin önerisi
    d["yapiKaynak"] = "film" if v.yapi else "profil"
    d["ses"] = v.ses
    d["dosyalar"] = {n: (v.dir / n).read_text() if (v.dir / n).exists() else None for n in sorted(DUZENLENEBILIR)}
    d["script"] = v.script
    d["cueHata"] = v.cue_error
    d["isaretler"] = sorted(([k, round(t, 3)] for k, t in v.cues.items()), key=lambda x: x[1])
    d["zaman"] = [{"id": s["id"], "adim": s["step"], "bas": s["start"], "bit": s["end"],
                   "metin": " ".join(w["text"] for w in s["words"]) or v.text_of(s["id"])} for s in (v.timeline or {}).get("sentences", [])]
    d["bpm"] = (v.timeline or {}).get("bpm")
    import plaka
    if plaka.var_mi(v):  # karma film (6b): sahneler ve vuruş başına motor (Senaryo adımındaki rozet)
        SS = [S for S in plaka.sahneler(v) if not S["hata"]]
        d["karma"] = [{"ad": S["ad"], "motor": S["motor"], "cizer": S.get("cizer"), "saydam": bool(S.get("saydam")),
                       "bas": round(S["bas_f"] / v.fps, 3), "son": round(S["son_f"] / v.fps, 3)} for S in SS]
        d["sahneMotor"] = {}
        for s in (v.timeline or {}).get("sentences", []):
            a, b = round(s["start"] * v.fps), round(s["end"] * v.fps)
            d["sahneMotor"][s["id"]] = [{"motor": x["motor"], "ad": x["ad"]} for x in SS if x["bas_f"] < b and a < x["son_f"]] or [{"motor": "remotion", "ad": None}]
    d["lint"] = [{"durum": a, "mesaj": b} for a, b in st.lint_rows(v)]
    ses = {}
    for n in ("mix.wav", "narration.wav", v.ses.get("muzik") or "muzik.wav"):
        if (v.pub / n).exists():
            ses[n] = rel(v.pub / n)
    if list(v.dir.glob("kayit.*")):
        ses["kayit"] = rel(next(v.dir.glob("kayit.*")))
    d["sesDosyalari"] = ses
    # inceleme sürümleri
    ince = []
    root = v.dir / "inceleme"
    for rd in sorted((p for p in root.glob("v*") if p.is_dir() and re.fullmatch(r"v\d+", p.name)), key=lambda p: int(p.name[1:])) if root.exists() else []:
        item = {"ad": rd.name, "kontak": {}, "olcum": olcum_oku(rd / "olcum.json"),
                "inceleme": (rd / "inceleme.md").read_text() if (rd / "inceleme.md").exists() else None,
                "elestiri": (rd / "elestiri.md").read_text() if (rd / "elestiri.md").exists() else None, "teslim": []}
        for f in v.formatlar:
            kp = rd / st.review_names(v, f)[0]
            if kp.exists():
                item["kontak"][f] = rel(kp)
        for td in sorted(rd.glob("teslim_v*")):
            item["teslim"].append({"ad": td.name, "olcum": olcum_oku(td / "olcum.json")})
        ince.append(item)
    d["incelemeler"] = ince
    tem = {}
    for f in v.formatlar:
        tp = root / "temsili" / st.review_names(v, f)[2]
        if tp.exists():
            tem[f] = rel(tp)
    d["temsili"] = tem
    # teslim dosyaları
    teslim = []
    for f in v.formatlar:
        for p in st.final_versions(v, f):
            pp = p.with_name(p.stem + "_poster.png")
            teslim.append({"format": f, "dosya": rel(p), "ad": p.name, "poster": rel(pp) if pp.exists() else None,
                           "mb": round(p.stat().st_size / 1e6, 1)})
    d["teslim"] = teslim
    kaba = {}
    for f in v.formatlar:
        rp = st.rough_path(v, f)
        if rp.exists():
            kaba[f] = rel(rp)
    d["kaba"] = kaba
    d["uretim"] = uretim.ozet(v)  # Magnific üretim deposu: varlıklar, harcanan / sınır
    d["goruntu"] = goruntu.ozet(v)  # gerçek görüntü (3b): kendi çekim, arşiv, açık lisans, stok; rıza, türevler
    d["takip"] = kamera_takibi.ozet(v)  # kamera takibi (4a, FOOH): çekimler, çözümler (hata, kare başına hata, önizlemeler); Blender filminde
    if d["takip"]:
        d["takip"]["suren"] = next((j.ad for j in ISLER.values() if j.video == vid and j.durum == "çalışıyor" and j.ad.startswith("Kamera takibi")), None)
    d["veri"] = canli_veri.ozet(v)  # canlı veri (4d): kaynak, lisans, anlık görüntüler, seçili görüntü ve yaşı (veri.json yoksa None)
    d["kisisel"] = kisisel.ozet(v)  # kişisel etki filmi (4c): şablon alanları, kararlar, veri dosyaları (yalnız ad), önizleme, çalışmalar (kimlikle)
    if d["kisisel"]:  # sürmekte olan toplu iş: düğmeler kilitli, ilerleme iş kartında
        d["kisisel"]["suren"] = next((j.ad for j in ISLER.values() if j.video == vid and j.durum == "çalışıyor" and j.ad.startswith("Kişisel film")), None)
    d["yapim"] = yapim_ozeti(v)  # yapım filmi (4e): hangi bölümler girer (önizleme görselleriyle), son çıktı ve ölçümü, sürmekte olan iş
    A = uretim.anlatim_durumu(v)  # anlatıcı Magnific ise: kaç parça hazır
    d["anlatim"] = {"magnific": A["magnific"], "parca": len(A["parcalar"]), "eksik": len(A["eksik"]),
                    "karakter": sum(len(p["metin"]) for p in A["eksik"]), "ses_adi": A["ayar"].get("ses_adi")} if A["magnific"] else None
    var = v.pub / "varliklar"
    d["varliklar"] = sorted(p.name for p in var.iterdir() if p.is_file() and not p.name.startswith(".")) if var.exists() else []
    d["varlikDurum"] = O.varlik_durumu(v)
    d["claude"] = claude_talimati(v, d["kapilar"])
    # yeni panelin çalışma alanı: zaman çizelgesi, kareler, format bilgisi, basit mod durumu
    d["cizelge"] = zaman_cizelgesi(v)
    d["kareler"] = {f: kare_listesi(v, f) for f in v.formatlar}
    d["formatBilgi"] = {f: O.FORMATLAR.get(f) for f in v.formatlar}
    d["motor"] = v.motor
    d["altyazi"] = v.altyazi["tur"]
    if v.motor == "blender":
        d["plaka"] = plaka_durumu(v)
    d["basit"] = basit_detay(vid)
    d["analitik"] = analitik_ozet(v, ayrinti=True)
    d["katalogaHazir"] = kataloga_hazir(v)
    return d


def plaka_durumu(v):
    """Blender videosu: süren plaka çizimi (out/_plaka/<id>/durum.json), boş bellek ve her (format, kalite) için hazır plaka sayısı."""
    import blender
    dj = blender.ONBELLEK / v.id / "durum.json"
    try:
        cizim = json.loads(dj.read_text()) if dj.exists() else None
    except (OSError, json.JSONDecodeError):
        cizim = None
    gb = blender.bos_bellek_gb()
    out = {"cizim": cizim, "bellek_gb": round(gb, 1), "bellek_az": 0 <= gb < 3.5, "surum": blender.surum(v), "cizer": blender.cizer(v), "kumeler": {}}
    for f in v.formatlar:
        for k in blender.KALITE:
            try:
                kume = blender.parmak_izi(v, f, k)[0]
            except SystemExit:
                continue
            d = blender.ONBELLEK / v.id / kume
            hazir = len(list(d.glob("p*.png"))) if d.exists() else 0
            out["kumeler"].setdefault(f, {})[k] = {"hazir": hazir, "toplam": v.nframes,
                                                   "tahmin_sn": round(blender.tahmini_sure(v, k, max(0, v.nframes - hazir)))}
    return out


def zaman_cizelgesi(v):
    """Ses üretiminden çıkan zamanlar: cümleler (kelime kelime), müzik vuruşları, ölçü başları."""
    tl = v.timeline or {}
    yuvarla = lambda xs: [round(x, 3) for x in xs]  # noqa: E731
    return {"sure": v.duration, "fps": v.fps, "bpm": tl.get("bpm"), "vuruslar": yuvarla(tl.get("beats", [])), "olculer": yuvarla(tl.get("downbeats", [])),
            "cumleler": [{"id": s["id"], "adim": s.get("step"), "bas": s.get("start"), "bit": s.get("end"),
                          "kelimeler": [[w["text"], round(w["start"], 3), round(w["end"], 3)] for w in s.get("words", [])]}
                         for s in tl.get("sentences", [])]}


def kare_listesi(v, fmt):
    """Vuruş kareleri (en son incelemenin, yoksa temsilî kareler): [{t, yol}]. Zaman çizelgesinin görüntü şeridi bunlardan kurulur."""
    root = v.dir / "inceleme"
    if not root.exists():
        return []
    ad = st.review_names(v, fmt)[1]
    surumler = sorted((p for p in root.glob("v*") if p.is_dir() and re.fullmatch(r"v\d+", p.name)), key=lambda p: int(p.name[1:]), reverse=True)
    for d in [*(s / ad for s in surumler), root / "temsili" / ad]:
        kareler = []
        for p in sorted(d.glob("f*.png")) if d.exists() else []:
            m = re.fullmatch(r"f(\d+)", p.stem)
            if m:
                kareler.append({"t": round(int(m.group(1)) / v.fps, 3), "yol": rel(p)})
        if kareler:
            return kareler
    return []


ONBELLEK = PANEL / "onbellek"   # küçük resimler ve ses dalgaları (silinebilir; yeniden üretilir)


def dalga(vid, n=900):
    """Miksin ses dalgası: n parçanın her biri için tepe (0–1). Ses dosyası değişince yeniden hesaplanır."""
    v = O.load(vid)
    src = next((v.pub / x for x in ("mix.wav", "narration.wav", v.ses.get("muzik") or "muzik.wav") if (v.pub / x).exists()), None)
    if not src:
        return {"tepe": [], "sure": v.duration, "kaynak": None}
    ONBELLEK.mkdir(exist_ok=True)
    c = ONBELLEK / f"dalga_{vid}_{int(src.stat().st_mtime)}.json"
    if c.exists():
        return json.loads(c.read_text())
    for eski in ONBELLEK.glob(f"dalga_{vid}_*.json"):
        eski.unlink()
    hz = 4000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(hz), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    a = array.array("h")
    a.frombytes(raw[: len(raw) // 2 * 2])
    L = len(a)
    tepe = []
    for i in range(n):
        s, e = i * L // n, (i + 1) * L // n
        tepe.append(math.sqrt(sum(x * x for x in a[s:e]) / (e - s)) if e > s else 0.0)
    m = max(tepe) or 1.0
    out = {"tepe": [round(x / m, 3) for x in tepe], "sure": round(L / hz, 3), "kaynak": src.name}
    c.write_text(json.dumps(out))
    return out


def kucuk(yol, w):
    """Küçük JPEG (poster, kare, katalog görseli): 2–3 MB'lık PNG'ler zaman çizelgesinde ve galeride hafif kalsın."""
    p = guvenli_yol(yol)
    if not p.is_file():
        return p
    w = max(48, min(1280, int(w)))
    ONBELLEK.mkdir(exist_ok=True)
    h = hashlib.sha1(f"{p}|{p.stat().st_mtime}|{w}".encode()).hexdigest()[:16]
    c = ONBELLEK / f"k_{h}.jpg"
    if not c.exists():
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-vf", f"scale='min({w},iw)':-2", "-frames:v", "1", "-q:v", "4", str(c)],
                           capture_output=True)
        if r.returncode != 0 or not c.exists():
            return p
    return c


def claude_talimati(v, kap):
    """Sıradaki adım için Claude'a yapıştırılacak hazır metin."""
    sira = next((k for k in kap if k["durum"] == "sirada"), None)
    if not sira:
        return f"{v.id}: bütün kapılar kapalı. Yayın paketini son kez kontrol edip videonun çıkacağı her yer için (yayin.md → Nereye) yükleme adımlarını benimle birlikte geçelim."
    n = sira["n"]
    if n <= 2 and v.yol_modu:  # planda üç yol: önce kullanıcı yolu seçer, sonra plan o yolda tamamlanır
        G = v.gorunus_json() or {}
        if not G.get("secim"):
            return (f"Bu adımda Claude'a iş yok: {v.id} için üç yol hazır. Plan adımında kanca karelerine bak ve birini “Bu yolu seç” ile seç; "
                    f"Claude planı o yolda tamamlar. Claude Code'da kendin çalışıyorsan: ./st gorunus {v.id} sec <harf>, sonra "
                    f"\"{v.id}: <harf> yolunu seçtim, planı bu yolda tamamla\" yaz.")
        if any(not e.startswith("Senin onayın") for e in sira["eksik"]):
            return (f"{v.id}: {G['secim'].upper()} yolunu seçtim. Planı bu yolda tamamla: yol bloğunu brief'in Yönetmenlik bölümüne taşı, "
                    f"senaryoyu yaz (./st lint temiz), seçilmeyen yolların kanca dallarını temizle ve ./st gorunus {v.id} ile seçilen yolun karesinin "
                    "değişmediğine bak. Bitince bana göster, planı panelden onaylayacağım.")
    if all(e.startswith("Senin onayın") for e in sira["eksik"]):
        return (f"Bu adımda Claude'a iş yok: Kapı {n} yalnız senin onayını bekliyor. İlgili sekmeyi oku; içine sinerse "
                f"\"Kapı {n}'i onayla\" düğmesine bas. Bir şey değişsin istiyorsan Claude'a şöyle yaz: \"{v.id}: <ne değişsin>\"")
    eksik = "; ".join(e for e in sira["eksik"] if not e.startswith("Senin onayın"))
    if n == 1:
        return (f"{v.id} videosu için Kapı 1'i hazırla: brief.md'yi benimle konuşarak doldur"
                + (", kaynaklar.md'deki her iddiayı en az 2 güvenilir kaynakla doğrula" if v.profil.get("kaynak_zorunlu") else "")
                + (", varliklar.md'yi gerçek dosyalarla tamamla (eksik olanı bana sor)" if v.profil.get("varlik_zorunlu") else "")
                + f". Eksikler: {eksik}. Bitince bana göster, onayı panelden vereceğim.")
    if n == 2:
        return (f"{v.id} videosunun senaryosunu yaz: filmin geçerli yapısıyla ({' → '.join(v.vuruslar)}"
                + ("; script.json → yapi" if v.yapi else "; profilin önerisi: film başka bir yapı istiyorsa script.json → yapi") + "), her vuruşa çekim sözleşmesi "
                f"(anahtar/işaret, plan, giriş→çıkış, geçiş, olay, ses, amaç). ./st lint temiz olsun. Eksikler: {eksik}. Bitince bana göster.")
    if n == 3:
        kod = {"hyperframes": f"hf/{v.id}/index.html (HyperFrames; önce hyperframes becerisi ve hf/CLAUDE.md)",
               "blender": f"blender/{v.id}/sahne.py (Blender; kurallar blender/CLAUDE.md, kit blender/kit; yazı ve logo src/{v.id}/Video.tsx'te)"}.get(
            v.motor, f"src/{v.script.get('kod', v.id)}/")
        return f"{v.id} için sahne kodunu ({kod}) ve ses tasarımını yaz, sonra ./st ses ve ./st temsili çalıştır. Temsilî kareleri bana göster."
    if n == 4:
        return f"{v.id} için ./st inceleme ve ./st elestir çalıştır; kontak tabakalarına, ölçüme ve kör eleştiriye bakıp en büyük 3 kusuru inceleme.md'ye yaz."
    if n == 5:
        return f"{v.id}: son incelemedeki en büyük 3 kusuru onar (önce etkilenen kareler, sonra ./st inceleme ve ./st elestir). Eksikler: {eksik}."
    return f"{v.id}: final render al (./st render {v.id} --final), yayin.md'yi doldur ve teslim ölçümünü göster. Eksikler: {eksik}."


def genel():
    vids = sorted(p.name for p in (STUDIO / "videos").iterdir() if p.is_dir())
    profiller = []
    for p in sorted(O.PROFIL_DIR.glob("*.json")):
        if p.stem != "formatlar":
            profiller.append(O.jload(p))
    stiller = []
    for p in sorted((STUDIO / "stiller").iterdir()):
        if p.is_dir() and (p / "gorunus.json").exists():  # seri görünüşleri
            sr = p / "stil-rehberi.md"
            ilk = next((ln for ln in sr.read_text().splitlines()[1:] if ln.startswith(">")), "") if sr.exists() else ""
            stiller.append({"ad": p.name, "rehber": rel(sr) if sr.exists() else None, "ozet": ilk.lstrip("> ").strip()})
    refs = []
    rr = KOK / "referans"
    if rr.exists():
        for p in sorted(rr.iterdir()):
            if p.is_dir() and p.name not in ("promptlar", "kampanyalar"):  # analiz değil, ilham kütüphaneleri (indeks.md)
                md = p / "analiz.md" if (p / "analiz.md").exists() else (p / "ANALIZ.md" if (p / "ANALIZ.md").exists() else None)
                refs.append({"ad": p.name, "analiz": rel(md) if md else None,
                             "kareler": rel(p / "kareler.jpg") if (p / "kareler.jpg").exists() else None,
                             "palet": rel(p / "palet.png") if (p / "palet.png").exists() else None})
    envp = STUDIO / ".env"
    opencode = envp.exists() and bool(re.search(r"^OPENCODE_API_KEY=.+", envp.read_text(), re.M))
    return {"videolar": [video_ozet(v) for v in vids], "profiller": profiller, "stiller": stiller, "formatlar": O.FORMATLAR,
            "referanslar": refs, "opencode": opencode, "isler": [j.ozet(10 ** 9) for j in list(ISLER.values())[-20:]],
            "katalog": katalog_ozet(), "aceVar": st.ACE_PY.exists(), "claude": claude_ayar_ozet(), "markalar": marka_ozet(),
            "basit": basit_liste(), "claudeVar": bool(shutil.which("claude")),
            "magnific": uretim.magnific_durumu(), "uretimAyar": uretim.ayarlar(),  # Magnific bağlantısı, son bilinen bakiye, film başına kredi sınırı
            "anlaticiOrnek": rel(KATALOG / "onizleme" / "anlatici" / "magnific-serkan-yildirim.mp3")  # seçilen Magnific anlatıcısının örneği (kredi harcamaz)
            if (KATALOG / "onizleme" / "anlatici" / "magnific-serkan-yildirim.mp3").exists() else None,
            "modelSayisi": len(list((STUDIO / "kutuphane" / "3b" / "threejsassets").glob("*.glb"))),  # 3B model kütüphanesi (./st 3b)
            "gecisSayisi": gecis_sayisi(),  # gölgelendirici geçişleri (6a; src/lib/gecis/gecisler.json)
            # motor seçiminin önizlemesi (yeni film levhası): katalog/onizleme/motor/<motor>.mp4 (+ .png kapak); Blender: ./st katalog motor (malzeme yelpazesi)
            "motorOnizleme": {m: {"video": rel(d / f"{m}.mp4"), "poster": rel(d / f"{m}.png") if (d / f"{m}.png").exists() else None}
                              for d in [KATALOG / "onizleme" / "motor"] for m in ("remotion", "hyperframes", "blender") if (d / f"{m}.mp4").exists()},
            # altyazı seçiminin önizlemesi: aynı diyalog klasik ve niyetli (./st katalog altyazi → katalog/onizleme/altyazi/<tur>.mp4 + .png)
            "altyaziOnizleme": {a: {"video": rel(d / f"{a}.mp4"), "poster": rel(d / f"{a}.png") if (d / f"{a}.png").exists() else None}
                                for d in [KATALOG / "onizleme" / "altyazi"] for a in ("klasik", "niyetli") if (d / f"{a}.mp4").exists()},
            "cizerOnizleme": cizer_onizleme()}


def cizer_onizleme():
    """Blender'ın çizer seçimi (yeni film levhası): aynı karenin Cycles ve EEVEE hâli (./st katalog cizer → katalog/onizleme/cizer/)
    ve 30 sn'lik filmin teslim kalitesinde tahmini çizim süresi (pipeline/blender.py → SURE, kil kampla ölçüldü)."""
    import blender
    d = KATALOG / "onizleme" / "cizer"
    out = {}
    for c in blender.CIZERLER:
        if (d / f"{c}.png").exists():
            out[c] = {"gorsel": rel(d / f"{c}.png"), "sn_kare": blender.SURE[(c, "tam")],
                      "film30_dk": round((blender.SURE[(c, "tam")] * 900 + blender.ACILIS[c] * 30) / 60)}
    return out


def marka_ozet():
    """Panel: marka kitleri (markalar/<ad>/marka.json)."""
    d = STUDIO / "markalar"
    out = []
    for p in sorted(d.glob("*/marka.json")) if d.exists() else []:
        M = json.loads(p.read_text())
        out.append({"ad": p.parent.name, "baslik": M.get("ad", p.parent.name), "kisa": M.get("kisa", p.parent.name)})
    return out


def claude_ayar_ozet():
    """Panel: aşama başına model/efor + seçenekler + Claude Code'un kendi varsayılanı."""
    ev = {}
    f = Path.home() / ".claude" / "settings.json"
    try:
        ev = json.loads(f.read_text()) if f.exists() else {}
    except json.JSONDecodeError:
        pass
    vm = ev.get("model") or ""
    ve = ((ev.get("modelSettings") or {}).get(vm or "claude-opus-5-5") or {}).get("effortLevel") or ev.get("effortLevel") or ""
    return {"ayar": O.claude_ayarlari(), "asamalar": O.CLAUDE_ASAMALAR, "modeller": O.CLAUDE_MODELLER, "eforlar": O.CLAUDE_EFORLAR,
            "varsayilan": {"model": O.CLAUDE_MODELLER.get(vm, vm) or "Claude Code varsayılanı (şu an Opus 5.5)", "efor": O.CLAUDE_EFORLAR.get(ve, ve) or "Claude Code varsayılanı"}}


KATALOG = STUDIO / "katalog"
KAT_TURLER = ("gorsel", "animasyon", "ses")


def katalog_ozet():
    """katalog/indeks.json + taslak durumu (Claude'un referanstan çıkardığı, kullanıcı onayı bekleyen seçenekler)."""
    I = json.loads((KATALOG / "indeks.json").read_text()) if (KATALOG / "indeks.json").exists() else {t: [] for t in KAT_TURLER}
    for tur in KAT_TURLER:
        for e in I.get(tur, []):
            f = KATALOG / tur / f"{e['ad']}.json"
            d = json.loads(f.read_text()) if f.exists() else {}
            e["durum"] = d.get("durum", "onayli")
            rd = KATALOG / "_referanslar" / tur / e["ad"] / "durum.md"
            e["not"] = rd.read_text() if rd.exists() else ""
            e["detay"] = katalog_detay(tur, d)
    # referansı yüklenmiş ama Claude'un henüz kaydını yazmadığı (çalışan) işler
    I["bekleyen"] = []
    rr = KATALOG / "_referanslar"
    if rr.exists():
        for tur in KAT_TURLER:
            for d in sorted((rr / tur).glob("*")) if (rr / tur).exists() else []:
                if d.is_dir() and not (KATALOG / tur / f"{d.name}.json").exists():
                    I["bekleyen"].append({"tur": tur, "ad": d.name})
    return I


def katalog_detay(tur, d):
    """Yeni film levhasındaki rafların önizlemesi için seçeneğin özü (tarifin tamamı katalog/<tür>/<ad>.json'da)."""
    if tur == "gorsel":
        return {"varyasyonlar": {h: {"ad": x.get("ad", ""), "fikir": x.get("fikir", ""), "renk": [c for c in (x.get("renk") or {}).values() if isinstance(c, str)][:5],
                                     "baslik": ((x.get("yazi") or {}).get("baslik") or {}).get("aile", ""), "govde": ((x.get("yazi") or {}).get("govde") or {}).get("aile", "")}
                                 for h, x in sorted((d.get("varyasyonlar") or {}).items())}}
    if tur == "animasyon":
        return {"ornek_motor": d.get("ornek_motor"), "uc": bool(d.get("uc")), "kurallar": (d.get("kurallar") or [])[:3], "kamera": d.get("kamera", ""),
                "gecis": d.get("gecis", ""), "tempo": (d.get("tempo") or {}).get("olay_aralik_sn")}
    m = d.get("muzik") or {}
    return {"kod": m.get("kod"), "ace": (m.get("ace") or {}).get("caption", ""), "bpm": (m.get("kod") or {}).get("bpm") or (m.get("ace") or {}).get("bpm"),
            "efekt": d.get("efekt") or [], "anlatim": d.get("anlatim") or {}, "miks": d.get("miks") or {}}


# Eski claude.json şeması ({"gorsel": "ad" | None, …}) ve yenisi ({"gorsel": {kartlar, mod, tarif}, …}) → yeni şema. Her okuma yolu bundan geçer.
katalog_normalize = st.katalog_normalize
CESARET_METNI = {k: f"{a}: {m}" for k, (a, m) in st.CESARET.items()}


def katalog_dogrula(k):
    """Yeni film levhasının katalog seçimi → (yeni şema, hata | None). Kart katalogda ve onaylı, tür başına en çok 3, mod esin | aynen,
    aynen yalnız tek kartla, tarif en çok 400 karakter. Eski şema (tek ad) de kabul edilir."""
    k = k if isinstance(k, dict) else {}
    for t in KAT_TURLER:
        x = k.get(t)
        if x in (None, ""):
            continue
        if isinstance(x, str):
            x = {"kartlar": [x], "mod": "aynen", "tarif": ""}
        if not isinstance(x, dict) or not isinstance(x.get("kartlar", []), list):
            return None, f"{st.TUR_AD[t]}: seçim şeması bozuk"
        kartlar, mod, tarif = x.get("kartlar") or [], x.get("mod") or "esin", str(x.get("tarif") or "")
        if len(kartlar) > 3 or len(set(kartlar)) != len(kartlar):
            return None, f"{st.TUR_AD[t]}: bir rafta en çok 3 farklı kart"
        for ad in kartlar:
            f = KATALOG / t / f"{ad}.json"
            if not (isinstance(ad, str) and re.fullmatch(r"[a-z][a-z0-9-]{1,40}", ad) and f.exists()):
                return None, f"Katalogda yok: {t}/{ad}"
            if json.loads(f.read_text()).get("durum") == "taslak":
                return None, f"{t}/{ad} henüz taslak: önce Kütüphane'de onayla"
        if mod not in ("esin", "aynen"):
            return None, f"{st.TUR_AD[t]}: mod esin ya da aynen olmalı"
        if mod == "aynen" and len(kartlar) != 1:
            return None, f"{st.TUR_AD[t]}: aynen uygulama tek kartla olur"
        if len(tarif.strip()) > 400:
            return None, f"{st.TUR_AD[t]}: kendi tarifin en çok 400 karakter"
    if k.get("muzik_kaynagi") not in (None, "", "kod", "ace"):
        return None, "Müzik kaynağı: kod ya da ace"
    return katalog_normalize(k), None


def katalog_secimi_metni(k, vid=None, referanslar=None):
    """Basit modda kullanıcının katalog seçimlerini Claude'a anlatır. Tür başına üç dal: kart yok = filme özel icat, esin = başlangıç
    noktası, aynen = tarif. Kullanıcının kendi tarifi her dalda önce gelir ve kartlarla çelişirse kazanır."""
    K = katalog_normalize(k)
    out, bayrak, esin = ["Katalog esin kaynağıdır: varsayılan, bu filme özel icattır; birebir uygulama yalnız kullanıcı \"aynen\" dediyse."], [], []
    for t in KAT_TURLER:
        x, ad = K[t], st.TUR_AD[t]
        if x["tarif"]:
            out.append(f"{ad} için kullanıcının kendi tarifi: «{x['tarif']}». Brief'e aynen yaz; kartlarla çelişirse tarif kazanır.")
        if not x["kartlar"]:
            out.append(f"{ad}: kart yok. Bu film için kendi dilini icat et. Katalog yalnız teknik örnek ve önceki filmlerle çakışmamak için okunur; "
                       "./st yeni'ye bu tür için bayrak verme." + (" Müzik tarifini script.json → ses.muzik_tarifi'ne sen yaz (studio/README.md → Müzik tarifi)."
                                                                   if t == "ses" else ""))
            continue
        bayrak.append(f"--{t} {','.join(x['kartlar'])}")
        if x["mod"] == "aynen":
            out.append(f"{ad}: '{x['kartlar'][0]}' kartını aynen uygula (--{t} {x['kartlar'][0]}); tarifin dışına çıkma (studio/katalog/{t}/{x['kartlar'][0]}.json)."
                       + (" ses.muzik_tarifi yazma: müzik bu kartın tarifinden gelir." if t == "ses" else ""))
        else:
            esin.append(t)
            out.append(f"{ad}: esin kartları {', '.join(x['kartlar'])}. Başlangıç noktasıdır: karıştır, değiştir, aş. Kuralları ipucu, yasak listesi uyarıdır "
                       f"(studio/katalog/{t}/<ad>.json)." + (" İlk kart müziğin başlangıç ön ayarıdır; filme göre ses.muzik_tarifi yazabilirsin." if t == "ses" else ""))
    if esin:
        bayrak.append("--esin " + ",".join(esin))
    if K["muzik_kaynagi"]:
        bayrak.append(f"--muzik-kaynagi {K['muzik_kaynagi']}")
    out.append(f"./st yeni'ye katalog bayrakları: {' '.join(bayrak)}." if bayrak else "./st yeni'ye katalog bayrağı verme.")
    if referanslar:
        out.append(f"Referanslar: videos/{vid}/referanslar/ → {', '.join(referanslar)} (./st yeni istekler/{vid}_referanslar/'dan oraya taşır). "
                   "Video ise ./st referans <dosya> ile ölç, görsel ise Read ile bak, ses ise ./st referans ile ölç (BPM, ses yüksekliği). "
                   "Ölçülebilir dilini al, kopyalama (CLAUDE.md).")
    return " ".join(out)


def secim_metni(k):
    """Basit modda kullanıcının motor, marka ve dil seçimlerini Claude'a anlatır."""
    motor = k.get("motor") or ""
    m = {"remotion": "Kullanıcı motoru seçti: --motor remotion.", "hyperframes": "Kullanıcı motoru seçti: --motor hyperframes.",
         "blender": "Kullanıcı motoru seçti: --motor blender (sahne blender/<id>/sahne.py; önce blender/CLAUDE.md)."}.get(
        motor, "Motoru sen seç (--motor remotion | hyperframes | blender). Motor bir araçtır, tarz değil: görüntü stili ve hareket tipi motoru belirlemez, "
               "her biri her motorda uygulanır (katalog JSON'unda teknik.<motor> notu). Filmin teknik ihtiyacına göre seç: remotion (React, DOM: yazı, veri, "
               "harita, arayüz, SVG illüstrasyon; Three.js 3B katmanı src/lib/uc), hyperframes (HTML, SVG, GSAP: çizgi film ve karakter animasyonu, kampanya, "
               "video oynatma; 3B katmanı assets/lib/uc/uc.js), blender (gerçek 3B: ışık, malzeme, kamera, alan derinliği; her tarz: ürün, mimari, soyut, "
               "maket, düşük poligon, çizgi film boyası; çizimi uzun sürer: teslim kare başına ~20–30 sn). Kullanıcı motor seçmediyse ve seçtiğin motor "
               "katalog seçimlerinin örneğinin motorundan farklıysa bunu durum.md'de bir cümleyle söyle.")
    cz = k.get("cizer")
    if motor == "blender" or not motor:
        m += {"eevee": " Çizer: kullanıcı EEVEE'yi seçti (./st yeni'ye --cizer eevee; script.json → blender.cizer = eevee): hızlı rasterleştirici; "
                       "blender/CLAUDE.md → Çizer'i oku (EEVEE'nin yapamadıkları: içindeki gölgeyi dışarı geçiren bez, ekran dışını gören kırılma ve yansıma, "
                       "çok sıçramalı yumuşak ışık; kil ve kar biraz koyu).",
              "cycles": " Çizer: kullanıcı Cycles'ı seçti (varsayılan; --cizer verme): gerçek ışık, teslim kare başına ~20–30 sn."}.get(
            cz, " Blender seçersen çizeri de sen seç (blender/CLAUDE.md → Çizer): cycles (varsayılan; gerçek ışık: ışık geçiren bez, cam, yumuşak "
                "dolaylı ışık; teslim kare başına ~20–30 sn) ya da --cizer eevee (kil kampta ~6 kat hızlı, teslim ~4 sn/kare; stilize, çizgi film, düz renk, "
                "kil, düşük poligon; içindeki gölgeyi dışarı geçiren bezi, ekran dışını gören kırılmayı yapamaz). Seçimini ve nedenini durum.md'de bir cümleyle söyle.")
    marka = k.get("marka")
    mk = (f" Marka kiti: --marka {marka} (markalar/{marka}/marka.md'yi oku: logo, renk, ton kuralları kurumundur; logolar videoya onaylı varlık olarak gelir)."
          if marka else " Marka kiti seçilmedi; istek bir kurum adıyla ve markalar/ altında kiti olan bir kurumla ilgiliyse --marka <ad> ver ve durum.md'de söyle.")
    dil = k.get("dil")
    dl = f" Video dili: --dil {dil} (ekrandaki bütün yazılar ve anlatım bu dilde)." if dil else " Video dilini isteğe göre seç (--dil tr | en); belirsizse Türkçe."
    an = {"kayit": " Anlatıcı: kullanıcı kendi sesiyle okuyacak (script.json ses.kaynak = kayit; kayıt ekli dosyalarda ya da sonra panelden yüklenir, "
                   "videos/<id>/kayit.*). Senaryoyu onun okuyacağı metin olarak yaz.",
          "yok": " Anlatıcı yok: anlatıcısız film (script.json ses.kaynak = yok); hikâyeyi görüntü, yazı, müzik ve efekt anlatır.",
          "magnific": " Anlatıcı: Magnific yapay sesi, kullanıcının seçimi (Serkan Yıldırım, erkek, doğal; ElevenLabs eleven_v3). script.json → ses = "
                      "{\"kaynak\": \"magnific\", \"voice\": 1039, \"ses_adi\": \"Serkan Yıldırım\", \"model\": \"eleven_v3\"} (müzik alanları kalır). "
                      "Anlatım parçaları üretim turunda ./st uret anlatim ile üretilir (MAGNIFIC kuralları; ~85 karakter 18 kredi): senaryoyu "
                      "sade, konuşur gibi yaz; kredi tahminine anlatımı da kat."}.get(
        k.get("anlatim") or "", " Anlatıcı: kullanıcı varsayılanı bıraktı (yapay ses, edge). Film anlatımlıysa edge sesini kullan; "
                                "istek anlatımsız bir filmle daha güçlü oluyorsa anlatımsız yap ve durum.md'de söyle.")
    mz = {"ace": " Müzik kaynağı: ACE-Step (--muzik-kaynagi ace; ses kartı yoksa ses.muzik_tarifi.ace'yi sen yaz: İngilizce kısa tarif, bpm, ton, tohum).",
          "yok": " Müzik istemiyor: müziksiz film (müzik üretme; ses stili seçildiyse yalnız efekt ve miks ayarlarını kullan)."}.get(k.get("muzik") or "", "")
    ay = (" Altyazı: kullanıcı niyetli altyazıyı seçti (./st yeni'ye --altyazi niyetli ver; script.json → altyazi = niyetli). Yazı sesi gösterir: "
          "kelimenin şiddeti ağırlığına ve boyutuna, perdesi genişliğine bağlı, her konuşmacı kendi renginde (script.json → konusmacilar; "
          "her cümlede konusmaci). Film anlatımlı olmalı; ölçümü ./st ses yapar. Sahne kodunda ortak Captions yerine Remotion <NiyetliAltyazi>, "
          "HyperFrames niyetliAltyazi(…) (şablon hazır kurar; hf/CLAUDE.md → Niyetli altyazı). Sesin inip çıktığı, fısıltının ve bağırışın "
          "olduğu bir senaryo bu seçimi değerli kılar." if k.get("altyazi") == "niyetli" else "")
    return m + mk + dl + an + mz + ay


def plan_istemi(vid):
    k = claude_kayit(vid)
    yayin = k.get("yayin", YAYIN["karar"])
    if k.get("formatlar"):
        yayin = f"kullanıcı formatları seçti: {', '.join(k['formatlar'])} (./st yeni'ye --formatlar {','.join(k['formatlar'])} ver)"
    c = k.get("cesaret") if k.get("cesaret") in st.CESARET else "cesur"
    return P_PLAN.format(id=vid, yayin=yayin, katalog=katalog_secimi_metni(k.get("katalog"), vid, k.get("referanslar")), secim=secim_metni(k),
                         cesaret=CESARET_METNI[c] + ("" if k.get("cesaret") else " (varsayılan)"), cesaret_kod=c, ortak=P_YOL_ORTAK.format(id=vid))


def plan_tamamla_istemi(vid):
    """Yol seçildi: planı o yolda tamamlama istemi (brief → Yönetmenlik, senaryo, lint, seçilmeyen kanca dallarının temizliği)."""
    v = O.load(vid)
    G = v.gorunus_json() or {}
    h = G.get("secim") or ""
    y = ((G.get("secenekler") or {}).get(h) or {}).get("yol") or {}
    return P_PLAN_TAMAMLA.format(id=vid, harf=h.upper(), h=h, yol_ad=y.get("ad", ""), yontem=y.get("yontem", ""),
                                 kaynak=("Profil kaynak istiyor: senaryodaki her iddiayı web'de en az 2 güvenilir kaynakla doğrula ve kaynaklar.md'ye yaz; "
                                         "doğrulayamadığın iddiayı senaryoya koyma." if v.profil.get("kaynak_zorunlu") else
                                         "Profil kaynak istemiyor; yine de rakam ya da iddia kullanırsan kaynaklar.md'ye yaz (uydurma yok)."))


# ---------------------------------------------------------------- basit mod: brief → Claude doldurur → iki onay
ISTEKLER = STUDIO / "istekler"
YAYIN = {"karar": "sen karar ver", "dikey": "dikey (Reels, Shorts, TikTok, hikâye)", "yatay": "yatay (YouTube, web sitesi, sunum, ekran)", "ikisi": "hem dikey hem yatay"}

P_PLAN = """BASİT MOD · PLAN TURU (ÖNCE FİKİR: ÜÇ YOL). Kullanıcı stüdyoyu panelin basit modundan kullanıyor: yalnız aşağıdaki isteği yazdı, gerisini sen dolduracaksın.
Kurallar: ../CLAUDE.md dosyasını oku ve uy. Uydurma yok; kalıcı marka kararı verme.
Video kimliği: {id} (tam olarak bunu kullan). İstek dosyası: istekler/{id}.md. Yayın tercihi: {yayin}. Ekli dosyalar: istekler/{id}_dosyalar/ (varsa).
Stil kataloğu: {katalog}
Motor, marka, dil: {secim}
Cesaret (kullanıcının seçimi): {cesaret}

Kullanıcı yaratıcı, iddialı, akılda kalan işler istiyor. Güvenli ve sönük bir plan başarısızlıktır. Kurallara takılıp isteği küçültme:
zanaat.md bir yasak listesi değil, ipucudur; pazarlıksız olanlar yalnız uydurma yok, yazı okunur, kare deterministik.

Bu tur bir FİKİR turudur: birbirinden YÖNTEM olarak farklı üç yol önerirsin, her biri kendi kanca karesi ve görünüşüyle. Kullanıcı birini seçer;
planı (brief'in Yönetmenlik bölümü, senaryo) o yolda bir sonraki turda tamamlarsın. Bu turda senaryo yazma.

Yapılacaklar:
1. Oku: isteği (ekli dosyalar ve referanslar dahil), studio/zanaat.md'yi (özellikle §1–2), ../referans/yontemler.md'yi (yöntemler, kışkırtma araçları, vesileler),
   ../referans/kampanyalar/indeks.md'den isteğe en yakın 2–3 kampanyayı ve ../referans/promptlar/indeks.md'den 2–3 zanaat örneğini.
   Filmi en iyi hâliyle hayal et: neyi gösterirsen izleyici bunu unutmaz? Cesaret: {cesaret}.
   İnsan, çocuk, mekân, duygu gerekiyorsa yolu zanaat §2'den seç (F stilize illüstrasyon dünyası, M malzeme ve maket dünyası, A, E …): karakterleri ve
   mekânları tek bir yapım diliyle, ayrıntılı ve tam taahhütle kur. Yol, görüntü stili, hareket ve motor dört ayrı karardır: yolu ve görünüşü filmin
   fikrinden, motoru teknik ihtiyaçtan seç; biri ötekini getirmez (illüstrasyon Remotion'da, HyperFrames'te ya da Blender'da çizgi film boyasıyla olur;
   3B ürün Blender'da ya da 3B katmanda olur). Katalogdaki ve önceki filmlerdeki örnekler TEKNİK örnektir: dünyasını, malzemesini, rengini, karakterini kopyalama.
   Gerçekçi mekân, nesne, doku, metafor ya da etiketli canlandırma gerekiyorsa yol C (Magnific plakası, yukarıdaki MAGNIFIC kuralları; bağlı değilse yok)
   kullanılabilir; yapay zekâ ucuz kamera değil, fikrin parçası olmalı. Gerçek kişi, gerçek olay ve gerçek yararlanıcı yapay zekâyla üretilmez: bunlar şartsa
   B (gerçek görüntü) ya da D (gerçek görüntü kodla stilize) yolu; aşağıdaki GERÇEK GÖRÜNTÜ kuralları. Dosya kullanıcıdan gelir: yoksa durum.md'nin İLK satırında
   iste (ne, kaç saniye, hangi açıdan) ve en iyi alternatifi (C etiketli canlandırma, F, A ya da E) de öner.
2. Ortak çerçeve (üç yol için aynı): profil (./st profiller; reklam ve kampanya için reklam-kisa), formatlar ve motor. Üç yol aynı motorda çizilir: fikirleri
   düşünürken üçüne de hizmet eden motoru seç. Profilin vuruş iskeleti bir öneridir; ölçülebilir çıtaları (süre, kanca, olay aralığı, cümle sınırları,
   ses yüksekliği, kaynak) aynen geçerlidir. Görünüş videoya özeldir; kullanıcı açıkça bir seriye bağlanmak istediyse --seri <ad> ver (seriler:
   studio/stiller/*/gorunus.json); o zaman görünüş paylaşılır ve yol kartları kurulamaz: üç yolu fikirler.md ve durum.md'de anlat, önerdiğin yolla planı
   tamamla (brief'in Yönetmenlik bölümü, senaryo, ./st lint temiz) ve durum.md'de söyle.
   ./st yeni {id} "<kısa başlık>" --profil <p> --formatlar <f1,f2> --motor <m> [--marka M] [--dil tr|en] [--gorsel G1,G2 --animasyon A1 --ses S1 --esin gorsel,animasyon --muzik-kaynagi kod|ace] --cesaret {cesaret_kod} --istek istekler/{id}.md
   (istek, ekli dosyalar ve referanslar kendiliğinden videoya taşınır; katalog bayraklarını yukarıdaki "Stil kataloğu" satırından al). Ekli dosya geldiyse varliklar.md'ye ekle.
   Görüntü: kart "aynen" ise üç yolun görünüşü o stilin varyasyonlarıdır (gorunus.json'a hazır gelir): yola göre inceltebilirsin (renk tonu, yazı ağırlığı),
   stilin dışına çıkma; katalog/gorsel/<ad>.json'daki "kurallar" ve "teknik" de geçerlidir. Kart "esin" ise kartlar ham malzemedir (gorunus.json → esin_stilleri):
   üç görünüşü yollara göre sen yaz; karıştır, değiştir, aş. Kart yoksa her yolun görünüşünü o yolun fikrinden icat et.
   Hareket (üç yolda da): kart "aynen" ise katalog/animasyon/<ad>.json'daki "kurallar" (hareket, kamera, tempo, geçiş) uyulacak tariftir; "esin" ise kurallar
   ipucudur, filmin fikri kazanır; kart yoksa hareket dilini (kamera, tempo, geçiş) yolun fikrinden kur. Her durumda seçtiğin motorun "teknik" notu nasıl
   yapılacağını söyler; "gorunus_ipucu" yalnız görüntü kartı yoksa ipucudur; "demo" yalnız teknik örnektir (ornek_motor'da yazılmıştır): dünyasını,
   malzemesini, rengini kopyalama.
   HyperFrames motorunda önce Skill aracıyla "hyperframes" becerisini yükle (sahne yazarken hyperframes-core, hyperframes-animation, hyperframes-creative),
   sonra hf/CLAUDE.md'yi oku: stüdyonun görünüş, işaret ve format köprüsü oradadır. Blender motorunda blender/CLAUDE.md'yi oku (malzeme ailesi
   görüntü stilinden: kil/kâğıt maket yalnız biri): sahne blender/{id}/sahne.py'de kitle (import kit) kurulur, yazı ve logo src/{id}/Video.tsx üst katmanındadır.
3. Fikir havuzu ve üç yol:
{ortak}
4. brief.md'nin ortak bölümlerini doldur: Film (tek cümle, kime, nerede, amaç, süre ve formatlar), Gerçekler, Görsel (kullanıcının kendi tarifi varsa
   "Kullanıcının tarifi" satırında aynen durur; referans, tut, kaçın), Ses, Kabul edilemez. Yönetmenlik bölümü ve Film → "Kanca fikri" satırı seçilen yoldan
   gelir: köşeli parantezlerini bırak (plan o yolda tamamlanınca dolar). Marka kiti varsa marka.md'deki logo, renk ve ton kurallarını brief'e taşı.
   Profil kaynak istiyorsa yolların dayandığı iddiaları şimdiden web'de en az 2 güvenilir kaynakla doğrula ve kaynaklar.md'ye yaz; doğrulayamadığın iddiaya yol kurma.
5. Gerçek bir dosya gerekiyorsa (logo, ürün ekranı) ve elinde yoksa: ona ihtiyaç duymayan bir çözüm seç ya da durum.md'de sor.
   3B sahnede hazır düşük poligon model gerekiyorsa (yapı, ağaç, araç, eşya, iç mekân): ./st 3b ara <İngilizce sözcük> (threejsassets ücretsiz katmanı,
   videoda ticari kullanım serbest, atıf yok). Kütüphanede yoksa indirme kullanıcının hesabıyla olur: threejsassets araçların (mcp__threejsassets) açıksa
   get_asset_download_link → ./st 3b al <slug> --url <bağlantı>; değilse durum.md'de hangi modelleri istediğini sayfa bağlantılarıyla yaz
   (kullanıcı tarayıcıdan indirip panelde Kütüphane → 3B modeller'e bırakır). Sonra ./st 3b kullan {id} <slug>. Farklı paketleri tek görsel dile malzemeyle bağla.
6. DUR. Kapıları kendin onaylama, yol seçme, senaryo yazma, kanca kareleri dışında sahne kodu yazma, video render alma.
7. videos/{id}/durum.md'yi yaz: kullanıcı için sade Türkçe, en fazla 10 satır. Ne yapacağız (tek cümle), süre ve formatlar, üç yolun her biri tek cümleyle
   (harf, ad ve nasıl bir film olacağı), senin önerin ve gerekçesi (seçim onun), varsa soruların. Yollar panelde Plan adımında kart olarak görünür. Teknik terim kullanma.
"""

# Üç yolu kuran ortak adımlar: yeni filmin plan turu (P_PLAN), panelden açılmış mevcut film (P_PLAN_MEVCUT) ve "başka yollar" değişikliği.
P_YOL_ORTAK = """   a. videos/{id}/fikirler.md: 12–20 ham fikir. ../referans/yontemler.md'deki yöntemleri ve kışkırtma araçlarını (ölçek kayması, bilineni tersine çevirme,
      iki ilgisiz dünyayı çarpıştırma, "burada taklit edilemeyen ne?", "ya şöyle olsaydı") isteğe uygula. Biçim: başlık "# Fikir havuzu: <başlık>", altında
      "> " ile başlayan tek satır (istek tek cümleyle · cesaret · puanlar 1–5, yüksek iyi; etik 5 = etik risk yok), sonra tablo:
      | # | Fikir (tek cümle) | Yöntem | Şaşırtma | Netlik | Yapılabilirlik | Etik | Not |
      Seçtiğin üç fikrin # hücresine yolun harfini ekle (ör. "4 → A"). Önceki filmlerin yöntemlerine bak (videos/*/gorunus.json → secenekler.*.yol.yontem):
      aynı yöntemi art arda iki filmde kullanma.
   b. Üç yol seç: A en güçlü sağlam fikir, B yanal (aynı mesaja başka bir yöntemle), C joker (cesaret Sınırsız'sa en uç olanı). Yollar renkte değil
      YÖNTEMDE ayrışır: iki yol aynı yöntemi paylaşamaz. Görünüşleri de zanaat.md §1c'ye göre en az üç eksende ayrışır (zemin açık/koyu, renk ailesi,
      yazı türü, doku ve ışık, hareket karakteri) ve hiçbiri önceki videolara benzemez (marka renkleri hariç). Her yol kendi üretim kuralını,
      insan/karakter yolunu (zanaat §2) ve olağanüstü ânını taşır; film başka bir vuruş yapısı istiyorsa yolun içinde söyle (plan tamamlanınca script.json → yapi).
      Pazarlıksızlar ve İHH çizgisi (gerçek yararlanıcı ve gerçek olay üretilmez) her yolda geçerli.
   c. videos/{id}/gorunus.json: üst düzeye "yol_modu": true. Üç seçenek (a, b, c); her biri görünüş alanları (ad, fikir, renk, yazi, doku, isik, hareket, bitis;
      HyperFrames ve Blender'da sahnenin kullandığı adlı renkler, Blender'da blender alanı) ve bir "yol" bloğu taşır:
      "yol": {{"ad": "<yolun adı, 2–4 sözcük>", "tek_cumle": "<film bu yolda ne söylüyor>", "yontem": "<yontemler.md'deki yöntem>", "kural": "<üretim kuralı>",
              "kanca": "<ilk 2 sn'de ne görülür ve duyulur>", "olaganustu_an": "<...>", "insan_yolu": "<F, M, A, E … ya da yok; neden>",
              "neden_akilda_kalir": "<...>", "risk": "<bu yolun riski ve önlemi>", "uretim": "<tahmini üretim süresi ve motor, ör. ~1 sa (Remotion)>", "kredi_tahmini": 0}}
      kredi_tahmini: yol Magnific plakası kullanacaksa denemeler dahil tahmini toplam kredi (ör. 4 plaka × 75 + 6 klip × 140 + seçilen çekimlerin pahalı
      üretimi), kullanmayacaksa 0; filmin kredi sınırını aşamaz. Plaka kullanan bir yolun neye benzeyeceğini göstermek için (yalnız Magnific bağlıysa,
      bekçi kurallarıyla) bir konsept karesi üretebilirsin: Nano Banana 2 1K (75 kredi) → ./st uret al {id} konsept_<harf> --tur gorsel … → yol bloğuna
      "konsept": "konsept_<harf>". Panel onu kanca karesinin yanında gösterir; kanca karesi yine kodla çizilir. Konsept karesinin vaadi filmde tutulabilir olmalı.
      Görüntü kartı "aynen" ise gorunus.json'a hazır gelen üç varyasyon üç yolun görünüşüdür: her birine bir yol bloğu ekle.
   d. Kanca kareleri: her yolun kanca karesini kodla; sahne seçeneğin harfine göre dallanır. Remotion: src/{id}/Video.tsx'te const yol = useSecenek()
      (../lib/gorunus) ve yol === 'a' / 'b' / 'c' için ayrı sahne bileşeni; renk ve yazı useStil()'den, büyük harf buyuk() ile. HyperFrames: hf/{id}/index.html'de
      ST.secenek ya da html[data-secenek="a"] seçicisi; renk var(--…), yazı .yazi-* sınıfları. Blender: blender/{id}/sahne.py'de ST.secenek, renk kit.renk('<ad>').
      Kanca karesi yolun vaadidir: iyi çizilmiş, ayrıntılı, gerçek bir kare olsun, iskelet değil. Kanca karesi dışında sahne yazma. Sonra ./st tip {id}.
   e. ./st gorunus {id}: yol bloklarını denetler (boş alan ya da aynı yöntem ❌) ve üç yolu kendi kanca kareleriyle çizer. Tabakayı
      (videos/{id}/inceleme/gorunus/gorunusler-*.png) kendin incele; uyarı varsa düzelt ve yeniden çiz. SEÇİM YAPMA: yolu kullanıcı seçer."""

P_PLAN_TAMAMLA = """BASİT MOD · PLANI TAMAMLA. Kullanıcı {id} filminde {harf} yolunu seçti: “{yol_ad}” ({yontem}). Kurallar: ../CLAUDE.md.
Fikir havuzu (videos/{id}/fikirler.md), üç yol (videos/{id}/gorunus.json → secenekler) ve kanca kareleri (videos/{id}/inceleme/gorunus/) hazır.
Şimdi planı yalnız bu yolda tamamla:
1. Seçilen yolun bloğunu (gorunus.json → secenekler.{h}.yol) brief.md'nin Yönetmenlik bölümüne taşı ve filme göre derinleştir: görsel kural, ana nesne,
   insan / karakter yolu (yol.insan_yolu), üretim kuralı (yol.kural), olağanüstü an(lar) (yol.olaganustu_an), benzer örnekler (../referans/yontemler.md,
   ../referans/kampanyalar/indeks.md, ../referans/promptlar/indeks.md: her birinden alınacak tek şey), ret ölçütü. Cesaret satırı aynen kalır.
   Film → Kanca fikri yol.kanca'dan gelir. brief.md'de köşeli parantezli alan kalmasın. Yol Magnific plakası kullanıyorsa Yönetmenlik'e "Neden yapay zekâ?"
   cevabını, hangi plakaların üretileceğini (deneme ucuz modelde, seçilen pahalıda), kare hızı kararını ve etik çizgiyi (zanaat §9) yaz; kredi tahmini sınırı aşmasın.
2. {kaynak} Gerçek bir dosya gerekiyorsa ve elinde yoksa ona ihtiyaç duymayan bir çözüm seç ya da durum.md'de sor.
3. Senaryoyu yaz: script.json (learningGoal; her vuruşa çekim sözleşmesi: anahtar ya da işaret, plan, giriş, çıkış, geçiş, olay, ses, amaç; anlatımsız filmde
   bas/bit çapaları); yol başka bir yapı istiyorsa script.json → yapi (sırayla 1–12 vuruş adı; her vuruşun amacını gerekçelendir); gerekiyorsa cues.json.
   Profilin ölçülebilir çıtaları aynen geçerli. ./st lint {id} temiz olsun (❌ kalmasın).
   Geçiş: düz kesim varsayılandır; gölgelendirici geçişi (gl-transitions; panel → Kütüphane → Geçişler) yalnız anlam taşıdığı kesimde, adı ve gerekçesi
   shot.gecis'te (yapılandırılmış biçim ve kurallar: ../studio/README.md → Gölgelendirici geçişleri, zanaat.md §3). Motor: tek motorlu film varsayılandır;
   bir sahne başka bir motorun güçlü olduğu şeyi taşıyorsa (karakter → HyperFrames, gerçek ışık ve malzeme → Blender, formül ve grafik → Manim; ipucu,
   zanaat.md → Karma film) karma film önerebilirsin: brief'in Yönetmenlik bölümüne sahne tablosu (sahnede ne var → motor → neden, gündelik dille) ve
   script.json → sahneler; kullanıcı Kapı 2'de onaylar.
4. Kanca dalları: sahne kodunda seçilmeyen yolların dallarını sil (Remotion useSecenek, HyperFrames ST.secenek ya da html[data-secenek], Blender ST.secenek);
   kod yalnız seçilen yolu çizsin, dal koşulu kalksın. Seçilen yolun sahnesi DEĞİŞMEMELİ. Seçilen yolun dalı kodda yoksa (önceden temizlendiyse) yol bloğundan
   ve önceki kanca karesinden (videos/{id}/inceleme/gorunus/{h}-<format>/) yeniden yaz. Sonra ./st tip {id} ve ./st gorunus {id}: yalnız seçilen yol yeniden
   çizilir ve önceki karesiyle karşılaştırılır; "değişti" derse farkı bul ve düzelt (Blender'da küçük gürültü farkı normaldir).
5. DUR. Kapıları onaylama, gorunus.json'da seçimi ve yol bloklarını değiştirme, kanca karesi dışında sahne kodu yazma, render alma.
6. videos/{id}/durum.md'yi yeniden yaz: sade Türkçe, en fazla 8 satır. Seçilen yol (tek cümle), filmi zorlayan üretim kuralı, süre ve formatlar,
   senaryonun kısa akışı, olağanüstü an(lar), varsa soruların. Teknik terim kullanma.
"""

P_REFERANS = """KATALOG REFERANSI. Kullanıcı panelden "{tur}" kataloğuna bir referans ekledi: {dosya}. Notu: {not_}
Görevin bu referanstan kataloğa yeni bir seçenek TASLAĞI çıkarmak; adı: {ad}. Kurallar: ../CLAUDE.md (referans kopyalanmaz, ölçülebilir dili alınır; uydurma yok).
- Video ise önce ./st referans {dosya} ref-{ad} ile ölç (palet, kesme temposu, hareket, ses, BPM) ve ../referans/ref-{ad}/ altındaki kareleri Read ile incele. Görsel ise Read ile bak. Ses ise ./st referans ile ölç (BPM, ses yüksekliği).
- gorsel: katalog/gorsel/{ad}.json yaz; şema katalog/gorsel/editoryal-kagit.json ile aynı: üç varyasyon (a, b, c), renkler referanstan, yazı tipleri yalnız src/lib/fontlar.ts listesinden, kontrast kuralları zanaat.md §1c.
- animasyon: katalog/animasyon/{ad}.json yaz; şema katalog/animasyon/kinetik-tipografi.json ile aynı (kurallar, kamera, geçiş, tempo referansın ölçülen kesme temposundan). "demo_tip" alanına mevcut örneklerden en yakınını yaz, "referans" alanına video yolunu.
- ses: katalog/ses/{ad}.json yaz; şema katalog/ses/belgesel-sakin.json ile aynı: muzik.kod.stil mevcut ön ayarlardan en yakını (pipeline/muzik_stiller.py ON_AYARLAR), bpm ölçülen tempo; muzik.ace.caption İngilizce kısa tarif ve "referans": "{dosya}" (ACE-Step bu parçayı örnek alır).
- Her durumda "kaynak": "referans", "durum": "taslak", "referans": "{dosya}" alanlarını koy. Sonra ./st katalog {tur} --ad {ad} çalıştır (doğrulama ve önizleme); hata varsa düzelt.
- Son olarak katalog/_referanslar/{tur}/{ad}/durum.md yaz: kullanıcı için sade Türkçe, en fazla 5 satır: referanstan ne aldın, neyi bilerek almadın, önizlemede neye bakmalı.
Onaylama: taslağı kullanıcı panelden onaylar. Kapı ya da başka video dosyasına dokunma.
"""

# Kataloğa ekle (filmden): katalog stüdyonun icat arşivine döner. Film kullanıcınındır: yalnız okunur.
P_KATALOGA = """KATALOĞA EKLE (FİLMDEN). Kullanıcı panelden {id} filminin {tur_ad} dilini kataloğa eklemek istedi. Yeni seçeneğin adı: {ad}. Notu: {not_}
Görevin bu filmden kataloğa yeni bir seçenek TASLAĞI çıkarmak. Kurallar: ../CLAUDE.md. Katalog esin kaynağıdır: kart filmin ölçülebilir dilini taşır,
filme özgü olanı (metin, logo, marka, karakter, gerçek kişi, olay) taşımaz. Uydurma yok: taslak filmde gerçekten olanı tarif eder.
Film kullanıcınındır: videos/{id}/, src/, hf/, blender/, public/ altındaki HİÇBİR dosyayı değiştirme, kapılarına ve teslimlerine dokunma; yalnız oku ve ölç.
Önce oku: videos/{id}/script.json, gorunus.json (varsa; seçilen görünüş), brief.md (Yönetmenlik), cues.json; filmin temsilî karelerine ve son kontak
tabakasına (videos/{id}/inceleme/) Read ile bak. ./st olc {id} ölçümü yazar; çalıştırma, son inceleme klasöründeki olcum.md'yi oku.
{gorev}
- Kayıtta "ad": "{ad}", "kaynak": "film:{id}", "durum": "taslak" olsun; "uygun" filmin türünden genelleşsin. Sonra ./st katalog {tur} --ad {ad}
  çalıştır (doğrulama ve önizleme); hata varsa yalnız katalog/{tur}/{ad}.json'u düzelt.
- Son olarak katalog/_referanslar/{tur}/{ad}/durum.md yaz: kullanıcı için sade Türkçe, en fazla 5 satır: filmden ne aldın, neyi bilerek almadın
  (filme özgü olan), önizlemede neye bakmalı.
Onaylama: taslağı kullanıcı panelden (Kütüphane) onaylar ya da siler. Başka dosyaya dokunma.
"""
KATALOGA_GOREV = {
    "gorsel": """- katalog/gorsel/{ad}.json yaz; şema katalog/gorsel/editoryal-kagit.json ile aynı. Üç varyasyon (a, b, c): a filmin seçilen görünüşüdür
  (gorunus.json → secenekler.<secim>: renk, yazı, doku, ışık, hareket, bitis; film paylaşılan bir seri ya da stil paketi kullanıyorsa oradan:
  stiller/<ad>/gorunus.json ya da src/stiller/<ad>/tokens.ts). b ve c ondan türer: aynı dil (doku, ışık mantığı, yazı türü), başka bir palet ya da ışık
  (gece/gündüz, açık/koyu zemin). Yazı tipleri yalnız src/lib/fontlar.ts listesinden; kontrast zanaat.md §1c. Marka kitinin renkleri (markalar/)
  varyasyona kurum rengi olarak geçmez: bir varyasyonda kalsa bile adını "kurum rengi" diye koyma.""",
    "animasyon": """- katalog/animasyon/{ad}.json yaz; şema katalog/animasyon/kinetik-tipografi.json ile aynı: kurallar (filmin hareket dili, motordan bağımsız),
  kamera, gecis, tempo.olay_aralik_sn (filmin işaretlerinden: cues.json ve public/{id}/timeline.json; olaylar arası en kısa ve tipik aralık),
  yasak, teknik.<motor> (filmin motorunda nasıl yapıldığı; öteki motorlar için kısa not), gorunus_ipucu. Örnek kod yazma: "demo" ve "demo_tip" koyma,
  "ornek_motor" koyma. "referans": filmin videosu (studio/'ya göre yol: son teslim ../cikti/<ad>_vN.mp4, yoksa out/<ad>_kaba.mp4) ve
  "demo_aralik": [başlangıç sn, bitiş sn] (filmin hareket dilini en iyi gösteren ~3 sn; önizleme bu aralıktan kesilir).""",
    "ses": """- katalog/ses/{ad}.json yaz; şema katalog/ses/belgesel-sakin.json ile aynı: muzik.kod (script.json → ses.muzik_tarifi.kod varsa o; yoksa ses.stil'in
  ön ayarı ya da pipeline/muzik_stiller.py ON_AYARLAR'dan filme en yakını; bpm public/{id}/timeline.json'dan), muzik.ace (caption İngilizce kısa tarif,
  bpm, ton, tohum; muzik_tarifi.ace varsa o), efekt (videos/{id}/ses.py'de kullanılan efekt ailesi), anlatim (ses.kaynak ve hız), miks (ses.py ve
  ölçüm: müzik seviyesi, sessizlikler). ACE-Step önizlemesi uzun sürer (açılış ~5 dk); ./st katalog ses --ad {ad} ikisini de üretir.""",
}

# İzleyici raporu (yayın sonrası): gerçek izleyici verisi döngüye girer. Sistem değişikliği yalnız kullanıcı onayıyla (CLAUDE.md kural 7).
P_ANALITIK = """İZLEYİCİ RAPORU. Kullanıcı {id} filminin yayın sonrası raporunu ekledi: videos/{id}/analitik/{klasor}/ (alanlar.json; dosyalar: {dosyalar}).
Kurallar: ../CLAUDE.md. Uydurma yok: yalnız raporda yazanı oku; okunamayan değeri "okunamadı" yaz.{test}
1. Raporu oku: alanlar.json (platform, tarih, surum = yayınlanan teslim dosyası (../cikti/), izlenme, ortalama izlenme %, izlendi / kaydırıldı %, paylaşım,
   gönderim, not). ./st kare kareleri filmin BUGÜNKÜ kodundan çizer: surum en son teslim değilse ya da teslim yoksa bunu rapor.md'de söyle. CSV'yi Read ile aç ve sütunlarını
   anla (izlenme eğrisi varsa saniye → izleyici oranı); ekran görüntüsünü ya da PDF'i Read ile incele.
2. İzleyicinin koptuğu anları bul: eğride ani düşüşler (yalnız toplamlar varsa: kanca için izlendi / kaydırıldı, döngü için ortalama izlenme %).
   En çok 6 anı kareye çevir ve çiz: ./st kare {id} 4.5s 9.2s … --cikti videos/{id}/analitik/{klasor}/kareler
   (saniyeyi "s" ekiyle yaz; ek yoksa sayı kare numarasıdır; filmin süresi içinde kal; yayınlanan format belliyse --format <format>).
   Çizilen karelere Read ile bak: o saniyede ekranda ne vardı?
3. Filmin son ölçümüne (videos/{id}/inceleme/vN/olcum.md: kanca, ilk saniyelerde mesaj, ilk karede ses, döngü, benzerlik), kör eleştirisine
   (elestiri.md) ve brief'ine bak: rapordaki düşüş ölçümün ya da eleştirinin bir uyarısıyla örtüşüyor mu?
4. videos/{id}/analitik/{klasor}/rapor.md yaz (sade Türkçe, kısa):
   ## Ne oldu (rakamlar raporda yazdığı gibi; hangi dosyadan)
   ## Koptukları anlar (saniye · kare dosyası · ekranda ne vardı)
   ## Hipotez (tek film kural değildir: "bu filmde" diye yaz; kanal/ogrenimler.md → Analitik kayıtları'nda aynı yönde başka bir film varsa söyle)
   ## Sistem değişikliği önerisi (profil, zanaat, ölçüm, katalog ya da kod; HENÜZ İŞLEME: kullanıcı onaylarsa işlenir)
5. {ogrenim}
6. Başka dosyaya dokunma: filmin kodu, kapıları, teslimleri ve stüdyonun kuralları bu turda değişmez.
"""
ANALITIK_OGRENIM = ("../kanal/ogrenimler.md → \"Analitik kayıtları\" tablosuna tek satır ekle: Video · Platform · Tarih · Görüntüleme · İzlendi / kaydırıldı · "
                    "Ort. izlenme % · Paylaşım / gönderim · Hipotez · Sistem değişikliği (\"öneri, onay bekliyor\"). Tablonun başlığını ve öteki satırları değiştirme.")
ANALITIK_TEST = ("Bu rapor TEST olarak işaretli: ../kanal/ogrenimler.md'ye satır EKLEME. rapor.md'nin ilk satırı \"> TEST raporu: öğrenimlere işlenmedi.\" olsun.")
ANALITIK_UZANTI = (".csv", ".tsv", ".txt", ".png", ".jpg", ".jpeg", ".webp", ".pdf")


def kataloga_hazir(v) -> bool:
    """"Bu filmin dilini kataloğa ekle" açık mı: filmin dili belli (Kapı 1 onaylı) ya da filmin çizilmiş bir dili var (temsilî kareler, kaba kurgu
    ya da teslim; Kapı 1'i kayıtlı olmayan içe aktarılmış eski filmler, ör. ihh_sofra)."""
    return (bool(st.gates_load(v).get("1", {}).get("onay")) or any((v.dir / "inceleme" / "temsili").glob("kareler*/f*.png"))
            or any(st.rough_path(v, f).exists() or st.final_versions(v, f) for f in v.formatlar))


def analitik_ozet(v, ayrinti=False):
    """Yayın sonrası raporlar (videos/<id>/analitik/): yayın tarihi (analitik/yayin.json), raporlar (<tarih>/: alanlar.json, dosyalar, rapor.md, kareler/)
    ve tek seferlik hatırlatma: yayından 2 gün sonra, henüz rapor yoksa (panel bir kez gösterir, ısrar etmez)."""
    d = v.dir / "analitik"
    try:
        yt = json.loads((d / "yayin.json").read_text()).get("tarih")
    except (OSError, ValueError):
        yt = None
    klasorler = sorted((p for p in d.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}(-\d+)?", p.name)), key=lambda p: p.name) if d.exists() else []
    try:
        zaman = bool(yt) and not klasorler and dt.date.today() >= dt.date.fromisoformat(yt) + dt.timedelta(days=2)
    except ValueError:
        zaman = False
    out = {"yayinTarihi": yt, "raporZamani": zaman, "raporSayisi": len(klasorler)}
    if ayrinti:
        out["raporlar"] = []
        for k in reversed(klasorler):
            try:
                al = json.loads((k / "alanlar.json").read_text())
            except (OSError, ValueError):
                al = {}
            calisan = next((j for j in ISLER.values() if getattr(j, "analitik", None) == f"{v.id}/{k.name}" and j.durum == "çalışıyor"), None)
            out["raporlar"].append({"klasor": k.name, "alanlar": al, "test": bool(al.get("test")),
                                    "rapor": (k / "rapor.md").read_text() if (k / "rapor.md").exists() else None,
                                    "dosyalar": [{"ad": p.name, "yol": rel(p)} for p in sorted(k.iterdir()) if p.is_file() and p.suffix.lower() in ANALITIK_UZANTI],
                                    "kareler": [rel(p) for p in sorted((k / "kareler").rglob("f*.png"))] if (k / "kareler").exists() else [],
                                    "durum": "hazir" if (k / "rapor.md").exists() else "inceleniyor" if calisan else "bekliyor", "is": calisan.id if calisan else None})
    return out

P_PLAN_MEVCUT = """BASİT MOD · PLAN TURU (mevcut video). Kullanıcı {id} videosunu panelden açtı (./st yeni çalıştı: profil {profil}, görünüş {stil}, formatlar {formatlar}) ve şu isteği yazdı: videos/{id}/istek.md.
Kurallar: ../CLAUDE.md dosyasını oku ve uy. Uydurma yok; kalıcı marka kararı verme. Güvenli ve sönük plan başarısızlıktır.
1. İsteği oku. Profil isteğe uymuyorsa script.json'da değiştir; format değişikliği gerekiyorsa script.json "formatlar" ve src/Root.tsx kaydını birlikte güncelle.
2. studio/zanaat.md'yi (§1–2), ../referans/yontemler.md'yi, ../referans/kampanyalar/indeks.md'den 2–3 kampanyayı ve ../referans/promptlar/indeks.md'den isteğe en yakın
   2–3 örneği oku. İnsan, karakter ya da mekân gerektiren istekte zanaat.md §2'den yol seç (F, M, A, E …). Yol, görünüş, hareket ve motor ayrı kararlardır;
   biri ötekini getirmez, örnekler (katalog, önceki filmler) yalnız tekniktir, dünyaları kopyalanmaz.
   Katalog esin kaynağıdır: script.json "katalog" (aynen kartlar) varsa tarife uy; "esin" varsa kartlar başlangıç noktasıdır (karıştır, değiştir, aş);
   ikisi de yoksa görünüşü, hareketi ve sesi bu filme özel icat et. Hedef cesaret script.json → cesaret (yoksa cesur). Profilin vuruş iskeleti
   bir öneridir; ölçülebilir çıtaları aynen geçerlidir.
3. Görünüş videoya özelse (script.json "gorunus": "video"): önce fikir, üç yol. Bu turda senaryo yazma; kullanıcı yolu seçince plan o yolda tamamlanır.
{ortak}
   brief.md'nin ortak bölümlerini doldur (Film, Gerçekler, Görsel, Ses, Kabul edilemez); Yönetmenlik bölümü ve "Kanca fikri" satırı seçilen yoldan gelir,
   köşeli parantezlerini bırak. Profil kaynak istiyorsa yolların dayandığı iddiaları şimdiden en az 2 güvenilir kaynakla doğrula (kaynaklar.md).
   Görünüş bir seriyse (script.json "gorunus": "seri:<ad>") yol kartları kurulamaz: üç yolu fikirler.md ve durum.md'de anlat, önerdiğin yolla planı tamamla
   (brief'in Yönetmenlik bölümü filmin omurgasıdır: görsel kural, ana nesne, insan/karakter yolu, üretim kuralı, olağanüstü anlar, ret ölçütü;
   senaryo script.json'da, her vuruşa çekim sözleşmesi, ./st lint temiz).
4. Gerçek bir dosya gerekiyorsa ve elinde yoksa: ona ihtiyaç duymayan bir çözüm seç ya da durum.md'de sor.
   3B sahnede hazır düşük poligon model gerekiyorsa: ./st 3b ara <İngilizce sözcük>; indirme kullanıcının hesabıyla (mcp__threejsassets açıksa
   get_asset_download_link → ./st 3b al <slug> --url <bağlantı>; değilse durum.md'de sayfa bağlantılarıyla iste), sonra ./st 3b kullan {id} <slug>.
   HyperFrames videosunda önce hyperframes becerisi ve hf/CLAUDE.md; Blender videosunda blender/CLAUDE.md.
5. DUR. Kapıları kendin onaylama, yol seçme, kanca karesi dışında sahne kodu yazma, video render alma.
6. videos/{id}/durum.md'yi yaz: kullanıcı için sade Türkçe, en fazla 10 satır. Ne yapacağız (tek cümle), süre ve formatlar, üç yolun her biri tek cümleyle ve senin önerin (gerekçesiyle; seçim onun), varsa soruların.
"""

P_URETIM = """BASİT MOD · ÜRETİM TURU. Kullanıcı {id} planını onayladı (Kapı 1 ve 2 kayıtlı). Kurallar: ../CLAUDE.md.
Şimdi uçtan uca üret:
1. Önce studio/zanaat.md §1–6'yı ve brief'teki Yönetmenlik bölümünü oku. Hedef: kullanıcının yıllarca saklayacağı kadar iyi, cesur, ayrıntılı bir film.
   script.json "katalog" (aynen kartlar) varsa tarife uy: animasyon tipinin tarifini (katalog/animasyon/<ad>.json: kurallar + bu motorun teknik notu;
   demo yalnız teknik örnek, dünyası kopyalanmaz) ve görüntü stilinin kurallarını oku. "esin" varsa kartlar ipucudur: brief'in Yönetmenlik bölümü ve
   seçilen görünüş kazanır. Hedef cesaret düzeyi script.json → cesaret (yoksa cesur); brief'teki üretim kuralı bütün sahnelerde geçerlidir.
   Planda üç yol vardıysa seçilen yol (gorunus.json → secim ve o seçeneğin yol bloğu) filmin vaadidir: kanca karesi o yolun karesidir, öteki yollar filme girmez.
   Ses stili ya da ses.muzik_tarifi varsa müziği ./st muzik {id} üretir (öncelik muzik_tarifi; kaynak script.json → ses.muzik_kaynagi; "ace" yavaştır,
   anlatım zamanlaması çıktıktan sonra bir kez çalıştır); efektleri filmin ses diline göre seç (ses stili kartı varsa onun efekt ailesi başlangıçtır).
   Sahne kodu motora göre: script.json "motor" yoksa ya da "remotion"sa src/<kod>/ (görünüşün bileşenleri, src/lib/anim.ts hareket dili, her format ayrı yerleşim,
   son rötuş Bitis); "hyperframes"sa hf/{id}/index.html (Skill: hyperframes, hyperframes-core, hyperframes-animation, hyperframes-creative; kurallar hf/CLAUDE.md;
   zaman ST.isaretler'den, format html[data-format] ile; CLI ./st hf {id} …); "blender"sa blender/{id}/sahne.py (kurallar blender/CLAUDE.md, kit blender/kit:
   zaman kit.isaret, renk kit.renk, rastgelelik tohumlu, her format kendi kadrajı) + yazı/logo src/{id}/Video.tsx üst katmanı; plakaları yalnız ./st çizer
   (taslak ~4 sn/kare, teslim ~20–30 sn/kare: 30 sn'lik film ~5–7 saat; uzunsa durum.md'de söyle). Ses tasarımı videos/{id}/ses.py, işaretler cues.json. Kod yazınca ./st tip {id} temiz olmalı.
   Brief Magnific plakası istiyorsa (yol C): yukarıdaki MAGNIFIC kurallarıyla üret, hemen ./st uret al ile dondur ve sahnede yalnız
   varliklar/uretim/ kopyasını kullan (Remotion <Img> ya da <OffthreadVideo muted>, HyperFrames <img> ya da <video muted>, Blender kit.varlik("uretim/…")).
   Yazı ve logo plakanın üstünde kodla çizilir. Etiket gerektiren varlığın göründüğü her vuruşta ekranda etiket ve script.json → etiketler.
   Brief gerçek görüntü istiyorsa (yol B ya da D): yukarıdaki GERÇEK GÖRÜNTÜ kuralları (maske, derinlik, kadraj her format için; rıza çözümüne uy).
2. ./st ses {id} (anlatıcı Magnific ise önce ./st uret anlatim {id}: eksik parçaları MAGNIFIC kurallarıyla üret), ardından ./st temsili {id};
   temsilî kareleri kendin incele (png'leri oku).
3. ./st inceleme {id}, ardından ./st elestir {id} (filmi hiç görmemiş bir oturumun kör eleştirisi → inceleme/vN/elestiri.md). Kontak tabakalarına, ölçüme ve
   eleştiriye bak; en büyük 3 kusuru inceleme.md'ye yaz (eleştirmenin P0/P1 maddeleri önceliklidir; katılmadığın maddeyi gerekçesiyle yaz), yerel olarak onar,
   "**Durum:** onarıldı" diye işaretle, ./st inceleme ve ./st elestir ile yeniden ölç. Ölçümün kanca ve izleyici satırları (ilk saniyelerde mesaj, ilk karede ses,
   döngü önerisi, yazı güvenli alanda, benzerlik) ⚠️'dir, ❌ değil: bilinçli bir tercihse gerekçesini yaz (script.json → mesaj_isareti / sessiz_acilis, durum.md);
   ortak ayarları (profiller/formatlar.json) değiştirme, kullanıcıya sor. Son ölçümde ❌ kalmayana ve eleştiri "yayınla" diyene kadar sürdür (en fazla 3 tur);
   3 turda "yayınla" çıkmazsa kalan maddeleri durum.md'de kullanıcıya söyle.
4. ./st deterministik {id} geçmeli.
5. ./st render {id} --final; ./st yayin {id}; yayin.md'yi doldur (karar gerektiren alanları en makul tahminle doldur ve durum.md'de belirt).
   Yapay zekâ beyanı bloğunu ./st yayin üretim deposundan doldurur: elle değiştirme; yapay zekâ varlığı varsa durum.md'de hangi platform beyanlarının açılacağını söyle.
6. Kapı 6'yı onaylama. DUR.
7. videos/{id}/durum.md'yi güncelle: sade Türkçe, en fazla 8 satır. Video hazır mı, neyi düzelttin, kullanıcı nereye özellikle bakmalı, yayın başlığı önerin.
"""

P_DEGISIKLIK = """BASİT MOD · DEĞİŞİKLİK. {id} için kullanıcı şunu istiyor:
<istek>
{metin}
</istek>
Kurallar: ../CLAUDE.md. Bulunduğun aşamadan devam et:
- Plan henüz onaylanmadıysa: brief, kaynaklar ve senaryoyu güncelle; lint temiz olsun; DUR.
- Plan onaylandıysa: ilgili yerleri düzelt, etkilenen kareleri yeniden render et, gerekiyorsa yeniden incele, final render ve yayin.md'yi güncelle. Kapı 6'yı onaylama.
- İstek planı değiştiriyorsa (konu, süre, format), kapilar.json'da Kapı 1 ve 2 onaylarını sıfırla ki kullanıcı yeniden onaylasın.
- Yapay zekâ ile üretilmiş bir varlık yeniden üretilecekse (Magnific): bekçi kuralları aynen (simulate_cost → ./st uret butce; çıkış 3 = DUR, sor). Eski varlık kalır,
  yenisi yeni adla gelir (ör. <ad>_2), sahne yenisine geçer; artık kullanılmayan eskiyi ./st uret sil {id} <ad> ile temizle.
- İstek görünüşle ilgiliyse: seçili görünüşü istenen yönde düzelt, ya da yeni seçenekler istendiyse gorunus.json'a yeni üç seçenek yaz, "secim"i null yap,
  ./st gorunus {id} çalıştır ve Kapı 1 onayını sıfırla: seçimi yine kullanıcı yapar.
- Planda üç yol varsa (gorunus.json → "yol_modu": true; yöntemler ../referans/yontemler.md):
  · Başka yollar isteniyorsa: fikirler.md'ye yeni fikirler ekle, öncekilerden ve birbirinden YÖNTEM olarak farklı üç yeni yol yaz (seçenekler, yol blokları,
    kodda kanca dalları: Remotion useSecenek, HyperFrames ST.secenek, Blender ST.secenek), "secim"i null yap, ./st gorunus {id} --hepsi çalıştır,
    kapilar.json'da Kapı 1 ve 2 onaylarını sıfırla. Senaryo yazma: kullanıcı yeni yolu seçince plan o yolda tamamlanır.
  · Bir yolda başka görünüşler isteniyorsa: o yolun bloğunu koru, aynı yol bloğuyla birbirinden belirgin farklı üç yeni GÖRÜNÜŞ yaz (a, b, c; zanaat §1c),
    "yol_modu"nu false, "secim"i null yap; kanca karesi o yolun tek sahnesidir (seçenekler yalnız renk, yazı, doku ve ışıkta ayrışır); ./st gorunus {id} --hepsi;
    Kapı 1 onayını sıfırla. Plan bu yolda henüz tamamlanmadıysa (brief'in Yönetmenlik bölümü boş ya da senaryo yok) aynı turda tamamla: yol bloğunu
    Yönetmenlik'e taşı, senaryoyu yaz, ./st lint temiz.
  · Başka bir yola geçmek isteniyorsa (ör. "C yolu olsun"): gorunus.json → secim'i o harfe çevir, planı o yolda tamamla (brief → Yönetmenlik, senaryo,
    ./st lint temiz; seçilmeyen kanca dalları temizlenir, o yolun dalı kodda yoksa yol bloğundan ve önceki kanca karesinden yeniden yaz; ./st gorunus {id})
    ve Kapı 1 ve 2 onaylarını sıfırla.
Son olarak videos/{id}/durum.md'yi güncelle (sade Türkçe, en fazla 8 satır).
"""

P_DEVAM = """BASİT MOD · DEVAM. {id} için yarım kalan işi kaldığın yerden sürdür. Kurallar: ../CLAUDE.md. ./st durum {id} ile nerede olduğuna bak.
Plan onaylanmadıysa plan turunu bitir ve dur (planda üç yol varsa ve yol seçilmediyse: fikir havuzu, üç yol, kanca kareleri, ./st gorunus, durum.md; senaryo yazma).
Onaylandıysa üretim turunu (sahne, ses, inceleme ve onarım, final render, yayın paketi) bitir; Kapı 6'yı onaylama.
Sonunda videos/{id}/durum.md'yi güncelle (sade Türkçe, en fazla 8 satır).
"""


P_BAKIYE = """MAGNIFIC BAKİYESİ. Yalnız şunu yap: mcp__magnific__account_balance aracını parametresiz çağır; sonra
./st uret bakiye --kalan <credits.available> --toplam <credits.totalPlan> --plan <plan.tier> komutunu çalıştır. Başka hiçbir araç ya da komut kullanma.
Araç yoksa ya da giriş isterse tek cümleyle söyle ve dur.
"""
KREDI_UST = 240000  # Premium planın yıllık kredisi: film sınırı bundan büyük olamaz


def kredi_degeri(x) -> int | None:
    try:
        n = int(str(x).replace(".", "").replace(" ", ""))
    except (TypeError, ValueError):
        return None
    return n if 0 <= n <= KREDI_UST else None


def claude_kayit_yolu(vid):
    d = STUDIO / "videos" / vid
    return (d / "claude.json") if d.exists() else (ISTEKLER / f"{vid}.json")


def claude_kayit(vid):
    for p in (STUDIO / "videos" / vid / "claude.json", ISTEKLER / f"{vid}.json"):
        if p.exists():
            return json.loads(p.read_text())
    return {}


def claude_bitti(j):
    """Claude işi bitince (panel o sırada kapalı olsa bile, açılınca) video kaydını günceller."""
    if not j.video:
        return
    if (STUDIO / "videos" / j.video / "script.json").exists():  # Magnific: bu işte harcanan (işin başı ve sonundaki bakiye okumaları)
        try:
            j.kredi = uretim.is_harcamasi(O.load(j.video), j.bas, j.bit or time.time())
            j.meta_yaz()
        except (SystemExit, ValueError, KeyError):
            pass
    kay = {**claude_kayit(j.video), "oturum": j.oturum, "son_asama": j.asama, "son_durum": j.durum,
           "son_sonuc": (j.sonuc or "")[:2000], "son_bitis": time.strftime("%Y-%m-%d %H:%M"),
           **({"son_kredi": j.kredi} if getattr(j, "kredi", None) is not None else {})}
    claude_kayit_yolu(j.video).write_text(json.dumps(kay, ensure_ascii=False, indent=1))


def claude_baslat(vid, asama, prompt):
    k = claude_kayit(vid)
    ad = {"plan": "Claude plan hazırlıyor", "plan_tamamla": "Claude planı seçtiğin yolda tamamlıyor", "uretim": "Claude videoyu üretiyor",
          "degisiklik": "Claude değişikliği yapıyor", "devam": "Claude devam ediyor"}[asama]
    j = ClaudeIs(ad, ARAC_KURALI + magnific_kurali(vid) + goruntu_kurali(vid) + veri_kurali(vid) + kisisel_kurali(vid) + prompt, vid, oturum=k.get("oturum"), bitince=claude_bitti, asama=asama, secim=k.get("claude"))
    ISLER[j.id] = j
    ISTEKLER.mkdir(exist_ok=True)
    claude_kayit_yolu(vid).write_text(json.dumps({**k, "son_is": j.id, "son_asama": asama, "son_durum": "çalışıyor"}, ensure_ascii=False, indent=1))
    return j


def calisan_claude(vid):
    return next((j for j in reversed(list(ISLER.values())) if j.video == vid and j.tur == "claude" and j.durum == "çalışıyor"), None)


def yayin_ozet(v):
    y = v.dir / "yayin.md"
    if not y.exists():
        return None
    t = y.read_text()
    m = re.search(r"\*\*Seçilen:\*\*\s*(.+)", t)
    a = re.search(r"## Açıklama\n(.*?)\n## ", t, re.S)
    return {"baslik": m.group(1).strip() if m else "", "aciklama": a.group(1).strip() if a else "", "dosya": rel(y)}


DURUM_METNI = {
    "baslamadi": ("Gönderildi ama başlamadı", "Claude bu istek için hiç çalışmadı. “Başlat” ile başlat ya da kopyaysa sil.", 1),
    "taslak": ("Ne anlatmak istediğini yaz", "Kendi cümlelerinle anlat; Claude brief'i ve senaryoyu doldursun.", 1),
    "hazirlaniyor": ("Claude planı hazırlıyor", "Fikirleri çıkarıyor, birbirinden farklı üç yol ve kanca karelerini hazırlıyor. Bitince birini seçeceksin.", 1),
    "yol_secim": ("Üç yoldan birini seç", "Claude bu film için birbirinden farklı üç fikir önerdi. Kanca karelerine bak, birini seç; Claude planı o yolda tamamlar.", 1),
    "yol_tamamlaniyor": ("Claude planı seçtiğin yolda tamamlıyor", "Brief'in yönetmenlik bölümünü ve senaryoyu yazıyor. Bitince okuyup onaylayacaksın.", 1),
    "plan_onay": ("Planı oku ve onayla", "Beğenmediğin bir şey varsa “Değişiklik iste” kutusuna yaz.", 1),
    "uretiliyor": ("Claude videoyu üretiyor", "Sahneler, ses, inceleme ve onarım, final render. Bu biraz sürebilir.", 2),
    "video_onay": ("Videoyu izle ve onayla", "Beğenmediğin bir şey varsa “Değişiklik iste” kutusuna yaz.", 3),
    "hazir": ("Video hazır", "Yayınlayabilirsin. Başlık, açıklama ve nereye çıkacağı aşağıda.", 3),
    "yarim": ("İş yarım kaldı", "Claude bitirmeden durdu. “Devam ettir” ile kaldığı yerden sürer.", 2),
    "hata": ("Bir sorun çıktı", "Claude'un son mesajına bak; “Devam ettir” ile yeniden dene.", 2),
}


def basit_durum(vid):
    kay = claude_kayit(vid)
    calisan = calisan_claude(vid)
    d = STUDIO / "videos" / vid
    if kay.get("son_durum") == "çalışıyor" and not calisan:
        return "yarim"  # panel kapanınca yarıda kalmış bir Claude işi
    if not d.exists():
        if calisan:
            return "hazirlaniyor"
        if not kay.get("son_is"):
            return "baslamadi"
        return "hata" if kay.get("son_durum") in ("hata", "durduruldu", "bitti") else "hazirlaniyor"
    v = O.load(vid)
    g = st.gates_load(v)
    ok = lambda n: bool(g.get(str(n), {}).get("onay"))  # noqa: E731
    plan_ok = ok(1) and ok(2)
    if calisan:
        return "uretiliyor" if plan_ok else ("yol_tamamlaniyor" if calisan.asama == "plan_tamamla" else "hazirlaniyor")
    if not plan_ok:
        if kay.get("son_asama") == "plan_tamamla" and kay.get("son_durum") in ("hata", "durduruldu"):
            return "hata"  # yol seçildi ama plan o yolda tamamlanamadı: "Devam ettir" yeniden dener
        if (d / "durum.md").exists() or kay.get("son_durum") == "bitti":
            return "yol_secim" if v.yol_modu and not (v.gorunus_json() or {}).get("secim") else "plan_onay"
        if kay.get("son_durum") in ("hata", "durduruldu"):
            return "hata"
        bos = O.PLACEHOLDER.search((d / "brief.md").read_text()) if (d / "brief.md").exists() else True
        return "taslak" if bos else "plan_onay"
    if ok(6):
        return "hazir"
    if all(st.final_versions(v, f) for f in v.formatlar) and kay.get("son_durum") in ("bitti", None):
        return "video_onay"
    return "hata" if kay.get("son_durum") == "hata" else "yarim"


def basit_ozet(vid):
    durum = basit_durum(vid)
    baslik, poster_yol = vid, None
    d = STUDIO / "videos" / vid
    if d.exists():
        v = O.load(vid)
        baslik = v.script.get("title", vid)
        poster_yol = poster(v)
    else:
        ip = ISTEKLER / f"{vid}.md"
        if ip.exists():
            baslik = ip.read_text().strip().splitlines()[0][:70]
    t, a, adim = DURUM_METNI[durum]
    return {"id": vid, "baslik": baslik, "durum": durum, "durumBaslik": t, "durumAciklama": a, "adim": adim, "poster": poster_yol}


def basit_liste():
    ids = []
    for p in sorted((STUDIO / "videos").iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        sp = p / "script.json"
        if p.is_dir() and sp.exists() and not json.loads(sp.read_text()).get("arsiv"):
            ids.append(p.name)
    if ISTEKLER.exists():
        for p in sorted(ISTEKLER.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            if p.stem not in ids and not (STUDIO / "videos" / p.stem).exists():
                ids.insert(0, p.stem)
    return [basit_ozet(i) for i in ids]


def basit_detay(vid):
    o = basit_ozet(vid)
    d = STUDIO / "videos" / vid
    kay = claude_kayit(vid)
    j = calisan_claude(vid) or ISLER.get(kay.get("son_is", ""))
    o["claude"] = j.ozet(max(0, len(j.cikti) - 14)) if j else None
    o["claudeSon"] = kay.get("son_sonuc")
    ip = (d / "istek.md") if (d / "istek.md").exists() else (ISTEKLER / f"{vid}.md")
    o["istek"] = ip.read_text() if ip.exists() else ""
    if not d.exists():
        return o
    v = O.load(vid)
    o["durumMd"] = (d / "durum.md").read_text() if (d / "durum.md").exists() else ""
    o["tekCumle"] = v.script.get("learningGoal", "")
    o["profil"], o["stil"], o["formatlar"], o["sure"] = v.profil["ad"], v.gorunus_etiketi, v.formatlar, v.duration
    o["gorunus"] = gorunus_paneli(v)
    o["senaryo"] = [{"adim": s.get("step"), "metin": " ".join(p["text"] for p in s.get("parts", [])) or s.get("shot", {}).get("olay", "")}
                    for s in v.script.get("sentences", [])]
    tem = d / "inceleme" / "temsili"
    o["temsili"] = {f: rel(tem / st.review_names(v, f)[2]) for f in v.formatlar if (tem / st.review_names(v, f)[2]).exists()}
    son = {}
    for f in v.formatlar:
        vs = st.final_versions(v, f)
        if vs:
            pp = vs[-1].with_name(vs[-1].stem + "_poster.png")
            son[f] = {"dosya": rel(vs[-1]), "poster": rel(pp) if pp.exists() else None, "ad": vs[-1].name}
    o["videolar"] = son
    o["yayin"] = yayin_ozet(v)
    return o


def gecis_sayisi() -> int:
    try:
        import gecis
        return len(gecis.kutuphane())
    except SystemExit:
        return 0


def gecis_listesi() -> dict:
    """Kütüphane → Geçişler: gl-transitions kataloğu (gölgelendirici kaynağı olmadan) + önizlemeler (./st gecis onizle). Salt göz atma:
    geçişi Claude senaryoda seçer ve gerekçesini yazar (script.json → shot.gecis); kullanıcı “Claude'a söyle” ile değiştirir."""
    import gecis
    out = []
    for g in gecis.kutuphane().values():
        mp4, jpg = gecis.ONIZLEME / f"{g['name']}.mp4", gecis.ONIZLEME / f"{g['name']}.jpg"
        out.append({"ad": g["name"], "yazar": g["author"], "lisans": g["license"], "aciklama": g["description"], "etiketler": g["tags"],
                    "param": gecis.param_ozeti(g) if g["params"] else "", "onizleme": rel(mp4) if mp4.exists() else None,
                    "poster": rel(jpg) if jpg.exists() else None})
    return {"gecisler": out, "kaynak": f"gl-transitions {gecis.SURUM}", "cikarilan": gecis.cikarilan(),
            "eksik": sum(1 for x in out if not x["onizleme"])}


# ---------------------------------------------------------------- HTTP
def guvenli_yol(yol: str) -> Path:
    p = (KOK / unquote(yol)).resolve()
    if KOK not in p.parents and p != KOK:
        raise PermissionError(yol)
    return p


class H(BaseHTTPRequestHandler):
    server_version = "StudyoPanel/1"

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False, default=float).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _hata(self, msg, code=400):
        self._json({"hata": str(msg)}, code)

    def _govde(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _dosya(self, p: Path, cache=False):
        if not p.exists() or not p.is_file():
            return self._hata("dosya yok", 404)
        size = p.stat().st_size
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        if p.suffix == ".md":
            ctype = "text/plain; charset=utf-8"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                else:
                    start = size - int(m.group(2))
            end = min(end, size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "max-age=60" if cache else "no-store")
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self._dosya(PANEL / "index.html")
            if u.path.startswith("/statik/"):
                return self._dosya(PANEL / "statik" / Path(u.path).name, cache=False)
            if u.path == "/dosya":
                return self._dosya(guvenli_yol(q["yol"]))
            if u.path == "/kucuk":
                return self._dosya(kucuk(q["yol"], q.get("w", 360)), cache=True)
            if u.path == "/api/genel":
                return self._json(genel())
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/dalga", u.path)
            if m:
                return self._json(dalga(m.group(1)))
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/plaka", u.path)   # Blender plaka çizimi: ilerleme göstergesi bunu yoklar
            if m:
                v = O.load(m.group(1))
                return self._json(plaka_durumu(v) if v.motor == "blender" else {})
            if u.path == "/api/basit":
                return self._json({"videolar": basit_liste(), "claudeVar": bool(shutil.which("claude"))})
            m = re.fullmatch(r"/api/basit/([a-z0-9_]+)", u.path)
            if m:
                return self._json(basit_detay(m.group(1)))
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)", u.path)
            if m:
                return self._json(video_detay(m.group(1)))
            m = re.fullmatch(r"/api/is/([a-f0-9]+)", u.path)
            if m:
                j = ISLER.get(m.group(1))
                return self._json(j.ozet(int(q.get("offset", 0)))) if j else self._hata("iş yok", 404)
            if u.path == "/api/3b":  # 3B model kütüphanesi (pipeline/model3b.py): indirilmiş modeller
                import model3b
                return self._json({"modeller": [{**b, "glbYol": rel(model3b.glb_yolu(b["slug"])),
                                                 "onizlemeYol": rel(model3b.KUTUPHANE / f"{b['slug']}.png") if b["onizleme"] else None}
                                                for b in model3b.kutuphane()],
                                   "site": model3b.SITE, "anahtar": bool(model3b._anahtar())})
            if u.path == "/api/3b/ara":  # herkese açık katalog (yalnız bilgi ve afiş; dosya değil)
                import model3b
                yerel = {b["slug"] for b in model3b.kutuphane()}
                return self._json({"sonuc": [{**m, "yerel": m["slug"] in yerel} for m in
                                             model3b.ara(q.get("q", ""), q.get("kategori") or None, q.get("hepsi") == "1", int(q.get("n", 48)))]})
            if u.path == "/api/gecis":  # gölgelendirici geçişleri (6a): katalog + önizlemeler
                return self._json(gecis_listesi())
            if u.path == "/api/belge":
                p = guvenli_yol(q["yol"])
                return self._json({"yol": q["yol"], "metin": p.read_text()})
            return self._hata("bulunamadı", 404)
        except (PermissionError, KeyError) as e:
            return self._hata(f"geçersiz istek: {e}", 400)
        except SystemExit as e:
            return self._hata(str(e), 400)

    def _takip(self, vid: str, alt: str):
        """Kamera takibi düğmeleri. Çekim gerçek görüntü kaydından gelir (Plan → Gerçek görüntü → Görüntü ekle); kamera yüksekliği 1–2,5 m."""
        b = json.loads(self._govde() or b"{}")
        v = O.load(vid)
        if v.motor != "blender":
            return self._hata("Kamera takibi Blender filminde çalışır (nesne Blender'da çizilir).")
        if any(j.video == vid and j.durum == "çalışıyor" and j.ad.startswith("Kamera takibi") for j in ISLER.values()):
            return self._hata("Bu filmde bir kamera takibi işi sürüyor.", 409)
        ad = str(b.get("ad") or b.get("goruntu") or "")
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", ad):
            return self._hata("geçersiz ad")
        try:
            yuk = float(b.get("yukseklik", 1.5))
        except (TypeError, ValueError):
            return self._hata("kamera yüksekliği bir sayı olmalı")
        if not 0.3 <= yuk <= 3.0:
            return self._hata("kamera yüksekliği 0,3–3 m")
        T = kamera_takibi.yukle(v)
        if alt == "coz":
            if ad not in {x["ad"] for x in goruntu.yukle(v)["varliklar"] if x["tur"] == "video"}:
                return self._hata(f"gerçek görüntü kaydında böyle bir video yok: {ad}")
            return self._json(is_baslat("Kamera takibi çözülüyor", ["takip", vid, ad, "--yukseklik", f"{yuk:g}"], vid).ozet())
        if ad not in T["cozumler"]:
            return self._hata(f"çözüm yok: {ad}")
        if alt == "olcek":
            return self._json(is_baslat("Kamera takibi: ölçek", ["takip", vid, "olcek", ad, f"{yuk:g}"], vid).ozet())
        if alt == "nesne":
            return self._json(is_baslat("Kamera takibi: nesne önizlemesi", ["takip", vid, "nesne", ad], vid).ozet())
        if alt == "sec":
            kamera_takibi.sec(vid, ad)
            return self._json({"tamam": True, "takip": kamera_takibi.ozet(O.load(vid))})
        if alt == "ac":   # Blender arayüzü bu bilgisayarda açılır (elle iz)
            try:
                kamera_takibi.ac(vid, ad)
            except SystemExit as e:
                return self._hata(str(e))
            return self._json({"tamam": True})
        kip = b.get("kip")
        if kip not in ("iz", "cozum"):
            return self._hata("kip: iz | cozum")
        x = T["cozumler"][ad]
        return self._json(is_baslat("Kamera takibi: elle " + ("izlerle yeniden çöz" if kip == "iz" else "çözümü al"),
                                    ["takip", vid, x["goruntu"], "--ad", ad, "--elle", kip, "--yukseklik", f"{x['yukseklik_m']:g}"], vid).ozet())

    def _toplu(self, vid, ne, q):
        """Kişisel etki filmi: yükle (bayt → videos/<id>/toplu/veri/<ad>), denetle, esleme (alan → sütun), onizle ve baslat (./st işi), karar
        (kullanıcının kurum verisi kararları), sil. Yanıtlarda ad ve değer yok: sütun adları, sayılar, satır numarası + kimlik + neden."""
        v = O.load(vid)
        if not kisisel.var_mi(v):
            return self._hata("Bu film kişisel film şablonu değil (veri_sablonu.json yok).")
        D = kisisel.dizin(v)
        if ne == "yukle":
            ad = Path(unquote(q.get("ad", ""))).name.replace(" ", "_")
            if not re.fullmatch(r"[\w.\-]+\.(csv|json|tsv|txt)", ad, flags=re.I):
                return self._hata("Veri dosyası .csv ya da .json olmalı (adında yalnız harf, rakam, nokta, tire).")
            govde = self._govde()
            if len(govde) > 50 * 1024 * 1024:
                return self._hata("Veri dosyası 50 MB'tan büyük.")
            (D / "veri").mkdir(parents=True, exist_ok=True)
            (D / "veri" / ad).write_bytes(govde)
            return self._json(self._toplu_ozet(v, ad))
        b = json.loads(self._govde() or b"{}")
        dosya = Path(str(b.get("dosya", ""))).name
        if ne in ("denetle", "esleme", "onizle", "baslat") and not (D / "veri" / dosya).exists():
            return self._hata("Veri dosyası yok: önce yükle.")
        if ne == "denetle":
            return self._json(self._toplu_ozet(v, dosya))
        if ne == "esleme":
            S = kisisel.sablon(v)
            E = {k: str(c) for k, c in (b.get("esleme") or {}).items() if k in S["alanlar"] and c}
            (D / "esleme.json").write_text(json.dumps(E, ensure_ascii=False, indent=1) + "\n")
            return self._json(self._toplu_ozet(v, dosya))
        suren = next((j for j in ISLER.values() if j.video == vid and j.durum == "çalışıyor" and j.ad.startswith("Kişisel film")), None)
        if ne in ("onizle", "baslat") and suren:
            return self._hata(f"Bu filmde bir kişisel film işi sürüyor ({suren.ad}): bitmesini bekle.")
        if ne == "onizle":
            return self._json(is_baslat("Kişisel film önizlemesi", ["toplu", vid, "onizle", "--veri", dosya], vid).ozet())
        if ne == "baslat":
            oz = self._toplu_ozet(v, dosya)
            if oz.get("engel"):
                return self._hata(oz["engel"])
            if not oz["gecerli"]:
                return self._hata("Geçerli satır yok: atlanacak satırların nedenlerine bak.")
            return self._json(is_baslat(f"Kişisel filmler ({oz['gecerli']} kişi)", ["toplu", vid, "--veri", dosya], vid).ozet())
        if ne == "karar":   # kullanıcının kararı: panel düğmesi (Claude yazmaz)
            S = kisisel.sablon(v)
            K = S.setdefault("kurum_verisi", {})
            for k in kisisel.KARAR_ALANLARI:
                if k in b:
                    K[k] = (str(b[k]).strip()[:2000] or None)
            kisisel.dosya(v).write_text(json.dumps(S, ensure_ascii=False, indent=1) + "\n")
            kisisel.yayin_yaz(v)
            return self._json({"tamam": True, "kisisel": kisisel.ozet(v)})
        if ne == "sil":
            h = str(b.get("hedef", ""))
            hedef = D / "veri" / Path(h[5:]).name if h.startswith("veri:") else D / Path(h).name
            if not h or not hedef.exists() or D.resolve() not in hedef.resolve().parents:
                return self._hata("Silinecek şey yok.")
            if hedef.is_dir():
                shutil.rmtree(hedef)
            else:
                hedef.unlink()
            return self._json({"tamam": True, "kisisel": kisisel.ozet(v)})
        return self._hata("bilinmeyen işlem")

    def _toplu_ozet(self, v, dosya):
        """Yüklenen dosyanın doğrulaması: sütun adları, eşleme, geçerli satır sayısı, atlanacaklar (satır no + kimlik + neden), TEST mi, engel."""
        D = kisisel.dizin(v)
        es = O.jload(D / "esleme.json") if (D / "esleme.json").exists() else {}
        try:
            H = kisisel.hazirla(v, D / "veri" / dosya, {k: c for k, c in es.items()} if es else None)
        except SystemExit as e:   # eşlenen sütun bu dosyada yoksa otomatik eşlemeyle yeniden dene
            if es:
                try:
                    H = kisisel.hazirla(v, D / "veri" / dosya)
                except SystemExit as e2:
                    return {"dosya": dosya, "hata": str(e2)}
            else:
                return {"dosya": dosya, "hata": str(e)}
        return {"dosya": dosya, "sutunlar": H["sutunlar"], "esleme": H["esleme"], "eslenmeyen": H["eslenmeyen"], "kullanilmayan": H["kullanilmayan"],
                "satir": len(H["satirlar"]), "gecerli": sum(1 for x in H["satirlar"] if x["kisi"]), "test": H["test"],
                "atlanan": [{"no": x["no"], "kimlik": x["kimlik"], "nedenler": x["nedenler"]} for x in H["satirlar"] if not x["kisi"]],
                "engel": kisisel.onay_engeli(v, H), "sha": H["sha256"][:12]}

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/api/yeni":
                b = json.loads(self._govde() or b"{}")
                vid = b.get("id", "")
                if not re.fullmatch(r"[a-z][a-z0-9_]{2,40}", vid):
                    return self._hata("Kimlik küçük harf, rakam ve alt çizgi olmalı (ör. kahve_tarihi)")
                args = ["yeni", vid, b.get("baslik") or vid, "--profil", b["profil"]] + (["--seri", b["stil"]] if b.get("stil") else [])
                # katalog: yeni şema (levha) ya da eski alanlar ("ses" alanı anlatım kaynağıdır, ses stili "sesStili")
                kat, hata = katalog_dogrula(b["katalog"] if "katalog" in b else {"gorsel": b.get("gorsel"), "animasyon": b.get("animasyon"),
                                                                                  "ses": b.get("sesStili"), "muzik_kaynagi": b.get("muzik_kaynagi")})
                if hata:
                    return self._hata(hata)
                kullan = [t for t in KAT_TURLER if kat[t]["kartlar"] and not (t == "gorsel" and b.get("stil"))]
                for t in kullan:
                    args += [f"--{t}", ",".join(kat[t]["kartlar"])]
                if any(kat[t]["mod"] == "esin" for t in kullan):
                    args += ["--esin", ",".join(t for t in kullan if kat[t]["mod"] == "esin")]
                if kat["muzik_kaynagi"]:
                    args += ["--muzik-kaynagi", kat["muzik_kaynagi"]]
                if b.get("cesaret"):
                    if b["cesaret"] not in st.CESARET:
                        return self._hata("Cesaret: saglam, cesur ya da sinirsiz")
                    args += ["--cesaret", b["cesaret"]]
                if b.get("formatlar"):
                    args += ["--formatlar", ",".join(b["formatlar"])]
                for k in ("motor", "marka", "dil"):
                    if b.get(k):
                        args += [f"--{k}", b[k]]
                if b.get("cizer"):
                    if b.get("motor") != "blender" or b["cizer"] not in ("cycles", "eevee"):
                        return self._hata("Çizer yalnız Blender'da: Cycles ya da EEVEE")
                    args += ["--cizer", b["cizer"]]
                if b.get("altyazi") not in (None, "", "klasik", "niyetli"):
                    return self._hata("Altyazı: klasik ya da niyetli")
                if b.get("altyazi") == "niyetli":
                    if b.get("ses") == "yok":
                        return self._hata("Niyetli altyazı anlatımdan ölçülür: anlatımsız filmde klasik altyazıyı seç.")
                    args += ["--altyazi", "niyetli"]
                r = subprocess.run([str(STUDIO / "st"), *args], cwd=STUDIO, capture_output=True, text=True)
                if r.returncode != 0:
                    return self._hata((r.stderr or r.stdout).strip()[-600:])
                if b.get("ses") and b["ses"] != "edge":
                    p = STUDIO / "videos" / vid / "script.json"
                    sc = json.loads(p.read_text())
                    kalan = {x: y for x, y in sc["ses"].items() if x in ("stil", "muzik_kaynagi", "esin")}  # ses kartı ve müzik kaynağı korunur
                    sc["ses"] = {"kaynak": b["ses"], **({"muzik": "muzik.wav"} if b["ses"] == "yok" else {}), **kalan}
                    p.write_text(st._dump_script(sc))
                if any(kat[t]["tarif"] for t in KAT_TURLER):  # kendi tarif: brief'e aynen (istek kaydı olmadığı için burada)
                    bp = STUDIO / "videos" / vid / "brief.md"
                    bp.write_text(bp.read_text().replace(st._tarif_satiri(None), st._tarif_satiri({"katalog": kat})))
                return self._json({"tamam": True, "id": vid, "cikti": r.stdout})
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/komut", u.path)
            if m:
                vid = m.group(1)
                b = json.loads(self._govde() or b"{}")
                k = b.get("komut")
                if k not in KOMUTLAR:
                    return self._hata("bilinmeyen komut")
                args = [KOMUTLAR[k][0], vid, *KOMUTLAR[k][1:]]
                if k == "muzik":
                    for o in ("bpm", "yapi", "ton", "kaynak"):
                        if b.get(o):
                            args += [f"--{o}", str(b[o])]
                if b.get("format") and k in ("temsili", "kaba", "final", "deterministik"):
                    args += ["--format", b["format"]]
                j = is_baslat(b.get("ad") or k, args, vid)
                return self._json(j.ozet())
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/goruntu", u.path)  # gerçek görüntü yükle: ./st goruntu ekle (kişi ve rıza kullanıcıdan)
            if m:
                vid = m.group(1)
                ad = Path(unquote(q.get("ad", ""))).name
                if not ad or not re.fullmatch(r"[\w.\- ]+", ad) or Path(ad).suffix.lower() not in goruntu.GORSEL_UZ + goruntu.VIDEO_UZ:
                    return self._hata("video (mp4, mov, m4v, webm, mkv) ya da görsel (png, jpg, webp, heic) yükle")
                kaynak, kisi, riza = q.get("kaynak", "kendi"), q.get("kisi", "bilinmiyor"), q.get("riza", "bilinmiyor")
                not_ = unquote(q.get("not", "")).strip()[:300]
                if kaynak not in ("kendi", "arsiv", "acik") or kisi not in ("evet", "hayir", "bilinmiyor") or riza not in goruntu.RIZALAR[:3]:
                    return self._hata("kaynak: kendi | arsiv | acik · kişi ve rıza: evet | hayir | bilinmiyor")
                if kaynak == "acik" and not not_:
                    return self._hata("Açık lisanslı görüntüde lisansı ve bağlantıyı nota yaz (ör. CC0 · https://commons.wikimedia.org/…).")
                gelen = STUDIO / "videos" / vid / "goruntu" / "_gelen"
                gelen.mkdir(parents=True, exist_ok=True)
                hedef = gelen / ad.replace(" ", "_")
                hedef.write_bytes(self._govde())
                args = ["goruntu", "ekle", vid, str(hedef), "--kaynak", kaynak]
                args += {"evet": ["--kisi"], "hayir": ["--kisi-yok"]}.get(kisi, [])
                args += ["--riza", riza] if kisi == "evet" else []
                args += ["--not", not_] if not_ else []
                j = Is("Gerçek görüntü ekleniyor", [str(STUDIO / "st"), *args], vid, bitince=lambda _j, h=hedef: h.unlink(missing_ok=True))
                ISLER[j.id] = j
                return self._json(j.ozet())
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/yapim", u.path)   # Nasıl yapıldı filmi (4e): ./st yapim <id> → ../cikti/<id>_yapim.mp4
            if m:
                vid = m.group(1)
                v = O.load(vid)
                if any(j.video == vid and j.durum == "çalışıyor" and j.ad.startswith("Nasıl yapıldı") for j in ISLER.values()):
                    return self._hata("Bu filmin yapım filmi zaten çiziliyor.", 409)
                fmt = q.get("format") or v.formatlar[0]
                if fmt not in v.formatlar:
                    return self._hata(f"Bu filmde {fmt} formatı yok.", 400)
                if q.get("onizle"):   # görsel önizleme: kılavuz kipinde tek kare (Blender: kil)
                    return self._json(is_baslat("Nasıl yapıldı önizlemesi", ["yapim", vid, "--onizle", "--format", fmt], vid).ozet())
                return self._json(is_baslat("Nasıl yapıldı filmi", ["yapim", vid, "--format", fmt], vid).ozet())
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/toplu/(yukle|denetle|esleme|onizle|baslat|karar|sil)", u.path)
            if m:   # kişisel etki filmi (4c): veri dosyası film klasöründe kalır (videos/<id>/toplu/veri/), panelin Claude'una gönderilmez
                return self._toplu(m.group(1), m.group(2), q)
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/takip/(coz|olcek|nesne|ac|elle|sec)", u.path)
            if m:   # kamera takibi (4a): çöz ve dondur (uzun: iş), ölçek (kamera yüksekliği), nesne önizlemesi, elle iz (Blender'da aç, elle çözümü al)
                return self._takip(m.group(1), m.group(2))
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/veri-cek", u.path)  # Veriyi yenile: ./st veri <id> cek --ciz (yeni görüntü + kanıt kareleri)
            if m:
                vid = m.group(1)
                if not (STUDIO / "videos" / vid / "veri.json").exists():
                    return self._hata("Bu filmde canlı veri yok (veri.json).")
                j = is_baslat("Veri yenileniyor", ["veri", vid, "cek", "--ciz"], vid)
                return self._json(j.ozet())
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/veri-sec", u.path)  # çizilecek anlık görüntü (kullanıcı; kanıt karesi önizlemesiyle)
            if m:
                vid = m.group(1)
                b = json.loads(self._govde() or b"{}")
                k = str(b.get("kimlik", ""))
                if not re.fullmatch(r"\d{8}T\d{6}Z|son", k):
                    return self._hata("görüntü kimliği: 20261026T191313Z biçiminde")
                try:
                    canli_veri.sec(vid, k)
                except SystemExit as e:
                    return self._hata(str(e))
                return self._json({"tamam": True, "veri": canli_veri.ozet(O.load(vid))})
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/goruntu-riza", u.path)  # kullanıcının kararı: rıza ya da çözüm (stilize, gizle, kullanma)
            if m:
                vid = m.group(1)
                b = json.loads(self._govde() or b"{}")
                try:
                    goruntu.riza_ayarla(vid, str(b.get("ad", "")), b.get("riza") or None, b.get("cozum") or None,
                                        {"evet": True, "hayir": False}.get(b.get("kisi")))
                except SystemExit as e:
                    return self._hata(str(e))
                return self._json({"tamam": True, "goruntu": goruntu.ozet(O.load(vid))})
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/kaydet", u.path)
            if m:
                vid = m.group(1)
                b = json.loads(self._govde() or b"{}")
                ad = b.get("dosya")
                d = STUDIO / "videos" / vid
                if ad in DUZENLENEBILIR:
                    hedef = d / ad
                else:
                    mm = re.fullmatch(r"inceleme/(v\d+)/inceleme\.md", ad or "")
                    if not mm:
                        return self._hata("bu dosya panelden düzenlenemez")
                    hedef = d / ad
                metin = b.get("metin", "")
                if hedef.suffix == ".json":
                    obj = json.loads(metin)
                    metin = st._dump_script(obj) if hedef.name == "script.json" else json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
                hedef.write_text(metin)
                return self._json({"tamam": True})
            if u.path == "/api/katalog/filmden":  # "Bu filmin dilini kataloğa ekle": Claude filmden bir taslak çıkarır, kullanıcı Kütüphane'de onaylar
                b = json.loads(self._govde() or b"{}")
                vid, tur, ad = str(b.get("id", "")), b.get("tur"), str(b.get("ad", ""))
                if not re.fullmatch(r"[a-z0-9_]+", vid) or not (STUDIO / "videos" / vid / "script.json").exists():
                    return self._hata("film yok")
                if tur not in KAT_TURLER or not re.fullmatch(r"[a-z][a-z0-9-]{2,30}", ad):
                    return self._hata("tür: görüntü, hareket ya da ses · ad: küçük harf, rakam ve tire (ör. gece-sofrasi)")
                if (KATALOG / tur / f"{ad}.json").exists() or (KATALOG / "_referanslar" / tur / ad).exists():
                    return self._hata(f"Bu adla bir {st.TUR_AD[tur].lower()} seçeneği zaten var ya da hazırlanıyor: {ad}")
                if not shutil.which("claude"):
                    return self._hata("Claude Code bu bilgisayarda bulunamadı.")
                if not kataloga_hazir(O.load(vid)):
                    return self._hata("Filmin dili henüz belli değil: Kapı 1 kapanınca ya da ilk kareler çizilince kataloğa eklenir.")
                not_ = str(b.get("not") or "").strip()[:400]
                hedef = KATALOG / "_referanslar" / tur / ad  # taslağın çalışma klasörü (Kütüphane "hazırlanıyor" diye gösterir)
                hedef.mkdir(parents=True, exist_ok=True)
                (hedef / "kaynak.md").write_text(f"film:{vid}\n{not_}\n")
                prompt = ARAC_KURALI + P_KATALOGA.format(id=vid, tur=tur, tur_ad=st.TUR_AD[tur].lower(), ad=ad, not_=not_ or "—",
                                                         gorev=KATALOGA_GOREV[tur].format(ad=ad, id=vid))
                def bitti(_j, tur=tur, ad=ad):  # taslak yazılamadıysa çalışma klasörü kalkar: aynı adla yeniden denenebilir
                    if not (KATALOG / tur / f"{ad}.json").exists():
                        shutil.rmtree(KATALOG / "_referanslar" / tur / ad, ignore_errors=True)
                j = ClaudeIs(f"Claude {vid} filminin {st.TUR_AD[tur].lower()} dilini kataloğa çıkarıyor: {ad}", prompt, None, bitince=bitti, asama="referans")
                ISLER[j.id] = j
                return self._json({"tamam": True, "is": j.ozet()})
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/yayin-tarihi", u.path)
            if m:  # yayın tarihi: izleyici raporu hatırlatması bundan 2 gün sonra bir kez görünür
                v = O.load(m.group(1))
                t = str(json.loads(self._govde() or b"{}").get("tarih") or "")
                d = v.dir / "analitik"
                if t:
                    dt.date.fromisoformat(t)
                    d.mkdir(exist_ok=True)
                    (d / "yayin.json").write_text(json.dumps({"tarih": t}) + "\n")
                else:
                    (d / "yayin.json").unlink(missing_ok=True)
                return self._json({"tamam": True})
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/analitik(/dosya|/basla)?", u.path)
            if m:  # yayın sonrası rapor: önce alanlar (klasör açılır), sonra dosyalar, sonra Claude inceler
                v = O.load(m.group(1))
                kok = v.dir / "analitik"
                if m.group(2) is None:
                    b = json.loads(self._govde() or b"{}")
                    al = {k: str(b.get(k) or "").strip()[:80] for k in ("platform", "tarih", "surum", "izlenme", "ort_izlenme", "izlendi_kaydirildi", "paylasim", "gonderim")}
                    al["not"] = str(b.get("not") or "").strip()[:600]
                    al["tarih"] = al["tarih"] or dt.date.today().isoformat()
                    dt.date.fromisoformat(al["tarih"])
                    k, n = kok / al["tarih"], 2
                    while k.exists():
                        k, n = kok / f"{al['tarih']}-{n}", n + 1
                    k.mkdir(parents=True)
                    (k / "alanlar.json").write_text(json.dumps(al, ensure_ascii=False, indent=1) + "\n")
                    return self._json({"tamam": True, "klasor": k.name})
                k = kok / Path(str(q.get("klasor", ""))).name
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(-\d+)?", k.name) or not k.is_dir():
                    return self._hata("rapor klasörü yok")
                if m.group(2) == "/dosya":
                    ad = Path(unquote(q.get("ad", ""))).name
                    if not re.fullmatch(r"[\w.\- ()]+", ad) or Path(ad).suffix.lower() not in ANALITIK_UZANTI:
                        return self._hata("Rapor dosyası CSV, ekran görüntüsü (PNG, JPG) ya da PDF olmalı.")
                    (k / ad).write_bytes(self._govde())
                    return self._json({"tamam": True})
                if not shutil.which("claude"):
                    return self._hata("Claude Code bu bilgisayarda bulunamadı.")
                if next((j for j in ISLER.values() if getattr(j, "analitik", None) == f"{v.id}/{k.name}" and j.durum == "çalışıyor"), None):
                    return self._hata("Claude bu raporu zaten inceliyor.")
                al = json.loads((k / "alanlar.json").read_text())
                dosyalar = sorted(p.name for p in k.iterdir() if p.is_file() and p.suffix.lower() in ANALITIK_UZANTI)
                # TEST: dosya adında, alanlarda ya da metin dosyasının başında açıkça "TEST" yazıyorsa öğrenimlere işlenmez
                test = any("TEST" in x for x in dosyalar + [al.get("platform", ""), al.get("not", "")]) or any(
                    b"TEST" in (k / x).read_bytes()[:4096] for x in dosyalar if Path(x).suffix.lower() in (".csv", ".tsv", ".txt"))
                al["test"] = test
                (k / "alanlar.json").write_text(json.dumps(al, ensure_ascii=False, indent=1) + "\n")
                prompt = ARAC_KURALI + P_ANALITIK.format(id=v.id, klasor=k.name, dosyalar=", ".join(dosyalar) or "yok (yalnız alanlar)",
                                                         test=f"\n{ANALITIK_TEST}" if test else "", ogrenim=ANALITIK_TEST if test else ANALITIK_OGRENIM)
                j = ClaudeIs(f"Claude izleyici raporunu inceliyor: {k.name}" + (" (TEST)" if test else ""), prompt, None, asama="analitik")
                j.analitik = f"{v.id}/{k.name}"
                ISLER[j.id] = j
                return self._json({"tamam": True, "is": j.ozet(), "test": test})
            if u.path == "/api/katalog/referans":
                tur, ad = q.get("tur"), q.get("ad", "")
                dosya = Path(unquote(q.get("dosya", ""))).name
                if tur not in KAT_TURLER or not re.fullmatch(r"[a-z][a-z0-9-]{2,30}", ad):
                    return self._hata("tür: gorsel/animasyon/ses · ad: küçük harf, rakam ve tire (ör. gece-treni)")
                if not dosya or not re.fullmatch(r"[\w.\- ]+", dosya):
                    return self._hata("geçersiz dosya adı")
                if (KATALOG / tur / f"{ad}.json").exists():
                    return self._hata(f"Bu adla bir {tur} seçeneği zaten var: {ad}")
                hedef = KATALOG / "_referanslar" / tur / ad
                hedef.mkdir(parents=True, exist_ok=True)
                (hedef / dosya).write_bytes(self._govde())
                (hedef / "not.md").write_text(unquote(q.get("not", "")) + "\n")
                prompt = ARAC_KURALI + P_REFERANS.format(tur=tur, ad=ad, dosya=f"katalog/_referanslar/{tur}/{ad}/{dosya}", not_=unquote(q.get("not", "")) or "—")
                j = ClaudeIs(f"Claude referanstan {tur} seçeneği çıkarıyor: {ad}", prompt, None, asama="referans")
                ISLER[j.id] = j
                return self._json({"tamam": True, "is": j.ozet()})
            if u.path == "/api/3b/ekle":  # tarayıcıyla indirilen .glb → kütüphane (dosya adı modelin kısa adıdır)
                import model3b
                dosya = Path(unquote(q.get("dosya", ""))).name
                if not dosya.lower().endswith(".glb") or not re.fullmatch(r"[\w.\- ()]+", dosya):
                    return self._hata("yalnız .glb dosyası (threejsassets'ten indirdiğin adıyla)")
                gecici = STUDIO / "out" / "_3b" / "yukleme" / dosya
                gecici.parent.mkdir(parents=True, exist_ok=True)
                gecici.write_bytes(self._govde())
                try:
                    b = model3b.ekle(str(gecici), q.get("slug") or None)
                except SystemExit as e:
                    if "karşılığı bulunamadı" in str(e):
                        return self._hata(f"{dosya}: katalogda bu adla bir model yok. Dosyayı threejsassets'ten indirdiğin adıyla bırak "
                                          "(ör. ammo-crate.glb) ya da Claude'a hangi model olduğunu söyle.")
                    raise
                finally:
                    gecici.unlink(missing_ok=True)
                return self._json({"tamam": True, "slug": b["slug"], "ad": b["name"]})
            if u.path == "/api/3b/onizle":
                b = json.loads(self._govde() or b"{}")
                s = str(b.get("slug", ""))
                if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", s):
                    return self._hata("geçersiz model")
                return self._json(is_baslat(f"3B model önizlemesi: {s}", ["3b", "onizle", s, "--yeniden"]).ozet())
            if u.path == "/api/3b/sil":  # yalnız bu bilgisayardaki kütüphane kopyası; filmlere kopyalanmış dosyalar yerinde kalır
                import model3b
                b = json.loads(self._govde() or b"{}")
                s = str(b.get("slug", ""))
                if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", s):
                    return self._hata("geçersiz model")
                for uz in (".glb", ".json", ".png"):
                    (model3b.KUTUPHANE / f"{s}{uz}").unlink(missing_ok=True)
                return self._json({"tamam": True})
            if u.path == "/api/uretim-ayar":  # Ayarlar → Magnific: yeni filmlerin varsayılan kredi sınırı
                b = json.loads(self._govde() or b"{}")
                n = kredi_degeri(b.get("kredi_siniri"))
                if n is None:
                    return self._hata(f"Kredi sınırı 0 ile {KREDI_UST:,} arasında bir tam sayı olmalı.".replace(",", "."))
                return self._json({"tamam": True, "ayar": uretim.ayar_yaz({"kredi_siniri": n})})
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/kredi-siniri", u.path)
            if m:  # filmin kredi sınırı (kullanıcı kararı): claude.json → kredi_siniri
                vid = m.group(1)
                n = kredi_degeri(json.loads(self._govde() or b"{}").get("kredi_siniri"))
                if n is None or not (STUDIO / "videos" / vid / "script.json").exists():
                    return self._hata(f"Kredi sınırı 0 ile {KREDI_UST:,} arasında bir tam sayı olmalı.".replace(",", "."))
                kayit_ = claude_kayit_yolu(vid)
                kayit_.write_text(json.dumps({**claude_kayit(vid), "kredi_siniri": n}, ensure_ascii=False, indent=1))
                return self._json({"tamam": True, "uretim": uretim.ozet(O.load(vid))})
            if u.path == "/api/magnific/bakiye":  # Ayarlar → "Bakiyeyi oku": kısa bir arka plan işi yalnız account_balance okur (kredi harcamaz)
                if not uretim.magnific_durumu()["kurulu"]:
                    return self._hata("Magnific bu bilgisayarda bağlı değil.")
                if not shutil.which("claude"):
                    return self._hata("Claude Code komut satırı (claude) bulunamadı.")
                j = ClaudeIs("Magnific bakiyesi okunuyor", ARAC_KURALI + P_BAKIYE, None, asama="magnific",
                             araclar=["mcp__magnific__account_balance", "Bash(./st:*)"])
                ISLER[j.id] = j
                return self._json(j.ozet())
            if u.path == "/api/claude-ayar":
                b = json.loads(self._govde() or b"{}")
                yeni = {}
                for a in O.CLAUDE_ASAMALAR:
                    x = b.get(a) or {}
                    m, e = str(x.get("model", "")).strip(), str(x.get("efor", "")).strip()
                    if m and not re.fullmatch(r"[A-Za-z0-9._\-\[\]]{2,60}", m):
                        return self._hata(f"Geçersiz model adı: {m}")
                    if e and e not in O.CLAUDE_EFORLAR:
                        return self._hata(f"Geçersiz efor: {e}")
                    yeni[a] = {"model": m, "efor": e}
                O.CLAUDE_AYAR.write_text(json.dumps(yeni, ensure_ascii=False, indent=2) + "\n")
                return self._json({"tamam": True, "ayar": yeni})
            if u.path in ("/api/katalog/onay", "/api/katalog/sil"):
                b = json.loads(self._govde() or b"{}")
                tur, ad = b.get("tur"), b.get("ad", "")
                f = KATALOG / str(tur) / f"{ad}.json"
                if tur not in KAT_TURLER or not re.fullmatch(r"[a-z][a-z0-9-]{2,30}", ad):
                    return self._hata("geçersiz seçenek")
                d = json.loads(f.read_text()) if f.exists() else {}
                if u.path.endswith("onay"):
                    if not f.exists():
                        return self._hata("seçenek yok")
                    d.pop("durum", None)
                    f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
                else:
                    if d.get("kaynak", "referans") != "referans" and not str(d.get("kaynak", "")).startswith("film:"):
                        return self._hata("Hazır katalog seçenekleri silinmez; yalnız referanstan ya da bir filmden eklenenler.")
                    f.unlink(missing_ok=True)
                    for o in (KATALOG / "onizleme" / tur).glob(f"{ad}*"):
                        o.unlink()
                    shutil.rmtree(KATALOG / "_referanslar" / tur / ad, ignore_errors=True)
                subprocess.run([str(STUDIO / "st"), "katalog", "--indeks"], cwd=STUDIO, capture_output=True)
                return self._json({"tamam": True})
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/gorunus", u.path)
            if m:
                vid = m.group(1)
                b = json.loads(self._govde() or b"{}")
                k = str(b.get("secim", ""))
                if not re.fullmatch(r"[a-z]", k):
                    return self._hata("secim: tek harf (a, b, c)")
                vv = O.load(vid)
                yol, onceki = vv.yol_modu, (vv.gorunus_json() or {}).get("secim")
                if yol:  # planda üç yol: seçim planı belirler; Claude çalışırken ya da plan onaylandıktan sonra panelden değişmez
                    if calisan_claude(vid):
                        return self._hata("Claude bu film üzerinde çalışıyor; bitince yolu seç.")
                    if st.gates_load(vv).get("2", {}).get("onay"):
                        return self._hata("Plan onaylandı: başka bir yola geçmek için Claude'a söyle (ör. “C yolu olsun”).")
                r = subprocess.run([str(STUDIO / "st"), "gorunus", vid, "sec", k], cwd=STUDIO, capture_output=True, text=True)
                if r.returncode != 0:
                    return self._hata((r.stderr or r.stdout).strip()[-400:])
                out = {"tamam": True, "cikti": r.stdout}
                if yol and (k != onceki or b.get("tamamla")) and shutil.which("claude"):  # yol seçildi: Claude planı o yolda tamamlar
                    out["is"] = claude_baslat(vid, "plan_tamamla", plan_tamamla_istemi(vid)).ozet()
                return self._json(out)
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/kapi", u.path)
            if m:
                b = json.loads(self._govde() or b"{}")
                r = subprocess.run([str(STUDIO / "st"), "kapi", m.group(1), str(int(b["n"])), b.get("not", "")], cwd=STUDIO,
                                   capture_output=True, text=True)
                return self._json({"tamam": r.returncode == 0, "cikti": r.stdout + r.stderr})
            m = re.fullmatch(r"/api/video/([a-z0-9_]+)/yukle", u.path)
            if m:
                vid = m.group(1)
                ad = Path(unquote(q.get("ad", ""))).name
                tur = q.get("tur")
                if not ad or not re.fullmatch(r"[\w.\- ]+", ad):
                    return self._hata("geçersiz dosya adı")
                veri = self._govde()
                if tur == "varlik":
                    hedef = STUDIO / "public" / vid / "varliklar" / ad
                elif tur == "kayit":
                    ext = Path(ad).suffix.lower()
                    if ext not in (".wav", ".m4a", ".mp3", ".aiff", ".flac"):
                        return self._hata("kayıt wav/m4a/mp3/aiff/flac olmalı")
                    for old in (STUDIO / "videos" / vid).glob("kayit.*"):
                        old.unlink()
                    hedef = STUDIO / "videos" / vid / f"kayit{ext}"
                elif tur == "muzik":
                    hedef = STUDIO / "public" / vid / "muzik.wav"
                    tmp = hedef.with_name("_yuklenen" + Path(ad).suffix)
                    tmp.write_bytes(veri)
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-ar", "48000", str(hedef)], check=True)
                    tmp.unlink()
                    return self._json({"tamam": True, "dosya": rel(hedef)})
                else:
                    return self._hata("tür: varlik | kayit | muzik")
                hedef.parent.mkdir(parents=True, exist_ok=True)
                hedef.write_bytes(veri)
                return self._json({"tamam": True, "dosya": rel(hedef)})
            if u.path == "/api/basit/yeni":
                b = json.loads(self._govde() or b"{}")
                metin = (b.get("metin") or "").strip()
                if len(metin) < 15:
                    return self._hata("Biraz daha anlat: ne anlatmak istiyorsun, kime, nerede yayınlanacak?")
                if not shutil.which("claude"):
                    return self._hata("Claude Code komut satırı (claude) bulunamadı. Detaylı modu kullan ya da Claude Code'u kur.")
                kok = "_".join(slug(metin).split("_")[:4])[:32].strip("_") or "video"
                if not kok[0].isalpha():
                    kok = "v_" + kok
                vid, n = kok, 2
                while (STUDIO / "videos" / vid).exists() or (ISTEKLER / f"{vid}.md").exists():
                    vid, n = f"{kok}_{n}", n + 1
                yayin = YAYIN.get(b.get("yayin", "karar"), YAYIN["karar"])
                kat, hata = katalog_dogrula(b.get("katalog"))
                if hata:
                    return self._hata(hata)
                cesaret = b.get("cesaret") or "cesur"
                if cesaret not in st.CESARET:
                    return self._hata("Cesaret: saglam, cesur ya da sinirsiz")
                cs = {k: str((b.get("claude") or {}).get(k) or "").strip() for k in ("model", "efor")}
                if cs["model"] and not re.fullmatch(r"[A-Za-z0-9._\-\[\]]{2,60}", cs["model"]):
                    return self._hata(f"Geçersiz model adı: {cs['model']}")
                if cs["efor"] and cs["efor"] not in O.CLAUDE_EFORLAR:
                    return self._hata(f"Geçersiz efor: {cs['efor']}")
                sec = {k: (b.get(k) or None) for k in ("motor", "marka", "dil", "anlatim", "muzik", "altyazi", "cizer")}
                if sec["motor"] not in (None, "remotion", "hyperframes", "blender") or (sec["dil"] and sec["dil"] not in ("tr", "en")):
                    return self._hata("Geçersiz motor ya da dil")
                if sec["cizer"] and (sec["motor"] != "blender" or sec["cizer"] not in ("cycles", "eevee")):
                    return self._hata("Çizer yalnız Blender'da: Cycles ya da EEVEE")
                if not sec["cizer"]:
                    del sec["cizer"]  # Claude seçer (Blender seçilirse): istek kaydında alan yok
                if sec["altyazi"] not in (None, "niyetli"):
                    return self._hata("Altyazı: klasik ya da niyetli")
                if sec["altyazi"] == "niyetli" and sec["anlatim"] == "yok":
                    return self._hata("Niyetli altyazı anlatımdan ölçülür: anlatımsız filmde klasik altyazıyı seç.")
                if not sec["altyazi"]:
                    del sec["altyazi"]  # klasik: istek kaydında alan yok
                if sec["anlatim"] not in (None, "kayit", "yok", "magnific") or sec["muzik"] not in (None, "kod", "ace", "yok"):
                    return self._hata("Geçersiz anlatıcı ya da müzik seçimi")
                if sec["anlatim"] == "magnific" and not uretim.magnific_durumu()["kurulu"]:
                    return self._hata("Magnific bu bilgisayarda bağlı değil: anlatıcı için Yapay ses ya da Kendi sesim seç.")
                if sec["marka"] and not (STUDIO / "markalar" / sec["marka"] / "marka.json").exists():
                    return self._hata(f"Marka kiti yok: {sec['marka']}")
                fm = [f for f in (b.get("formatlar") or []) if f in O.FORMATLAR]
                kredi = kredi_degeri(b["kredi_siniri"]) if b.get("kredi_siniri") not in (None, "") else uretim.ayarlar()["kredi_siniri"]
                if kredi is None:
                    return self._hata(f"Kredi sınırı 0 ile {KREDI_UST:,} arasında bir tam sayı olmalı.".replace(",", "."))
                sec["kredi_siniri"] = kredi  # Magnific: film başına kredi sınırı (Gelişmiş); claude.json'a taşınır
                kat["muzik_kaynagi"] = sec["muzik"] if sec["muzik"] in ("kod", "ace") else None  # ses kartı yoksa da: müzik tarifini Claude yazar
                ISTEKLER.mkdir(exist_ok=True)  # doğrulamadan sonra: reddedilen istek dosya bırakmaz
                (ISTEKLER / f"{vid}.md").write_text(metin + "\n")
                (ISTEKLER / f"{vid}.json").write_text(json.dumps({"yayin": yayin, "katalog": kat, "cesaret": cesaret, "claude": cs, **sec,
                                                                  **({"formatlar": fm} if fm else {})}, ensure_ascii=False))
                if b.get("bekle"):  # önce ekli dosyalar yüklenecek, sonra /basla
                    return self._json({"id": vid})
                j = claude_baslat(vid, "plan", plan_istemi(vid))
                return self._json({"id": vid, "is": j.ozet()})
            m = re.fullmatch(r"/api/basit/([a-z0-9_]+)/sil", u.path)
            if m:
                vid = m.group(1)
                if (STUDIO / "videos" / vid).exists() or calisan_claude(vid):
                    return self._hata("Yalnız başlamamış istekler panelden silinebilir.")
                for f in (ISTEKLER / f"{vid}.md", ISTEKLER / f"{vid}.json"):
                    f.unlink(missing_ok=True)
                for ek in (ISTEKLER / f"{vid}_dosyalar", ISTEKLER / f"{vid}_referanslar"):
                    if ek.exists():
                        shutil.rmtree(ek)
                return self._json({"tamam": True})
            m = re.fullmatch(r"/api/basit/([a-z0-9_]+)/arsiv", u.path)
            if m:  # iptal = arşive kaldır (dosyalar kalır, geri alınabilir)
                vid = m.group(1)
                sp = STUDIO / "videos" / vid / "script.json"
                if not sp.exists():
                    return self._hata("Film klasörü yok.")
                if calisan_claude(vid):
                    return self._hata("Claude bu film üzerinde çalışıyor; önce durdur.")
                geri = bool(json.loads(self._govde() or b"{}").get("geri"))
                metin = re.sub(r'\n[ \t]*"arsiv": "(?:[^"\\]|\\.)*",?', "", sp.read_text())  # elle biçimlenmiş dosyayı bozmadan
                if not geri:
                    metin = re.sub(r"^\{\n", '{\n  "arsiv": "panelden iptal edildi · ' + time.strftime("%Y-%m-%d") + '",\n', metin, count=1)
                json.loads(metin)
                sp.write_text(metin)
                return self._json({"tamam": True})
            m = re.fullmatch(r"/api/basit/([a-z0-9_]+)/basla", u.path)
            if m:
                vid = m.group(1)
                if calisan_claude(vid):
                    return self._hata("Claude zaten çalışıyor.")
                j = claude_baslat(vid, "plan", plan_istemi(vid))
                return self._json({"id": vid, "is": j.ozet()})
            m = re.fullmatch(r"/api/basit/([a-z0-9_]+)/(onay|degisiklik|devam|dosya)", u.path)
            if m:
                vid, eylem = m.group(1), m.group(2)
                if eylem == "dosya":
                    ad = Path(unquote(q.get("ad", ""))).name
                    if not ad or not re.fullmatch(r"[\w.\- ]+", ad):
                        return self._hata("geçersiz dosya adı")
                    if q.get("tur") == "referans":  # referans: ölçülür, kopyalanmaz (varlık değil); ./st yeni videoya taşır
                        vd = STUDIO / "videos" / vid
                        hedef = (vd / "referanslar") if vd.exists() else (ISTEKLER / f"{vid}_referanslar")
                        hedef.mkdir(parents=True, exist_ok=True)
                        (hedef / ad).write_bytes(self._govde())
                        kay = claude_kayit(vid)
                        kay["referanslar"] = [*[x for x in kay.get("referanslar") or [] if x != ad], ad]
                        claude_kayit_yolu(vid).write_text(json.dumps(kay, ensure_ascii=False, indent=1))
                        return self._json({"tamam": True})
                    hedef = (STUDIO / "public" / vid / "varliklar") if (STUDIO / "videos" / vid).exists() else (ISTEKLER / f"{vid}_dosyalar")
                    hedef.mkdir(parents=True, exist_ok=True)
                    (hedef / ad).write_bytes(self._govde())
                    return self._json({"tamam": True})
                if calisan_claude(vid):
                    return self._hata("Claude şu an bu video üzerinde çalışıyor; bitmesini bekle ya da durdur.")
                b = json.loads(self._govde() or b"{}")
                if eylem == "onay":
                    asama = b.get("asama")
                    if asama == "plan":
                        vv = O.load(vid)
                        if vv.gorunus_modu == "video" and not vv.gorunus_secimi:
                            return self._hata("Önce üç yoldan birini seç." if vv.yol_modu else "Önce görünüşlerden birini seç (üç deneme karesinin altındaki düğmeler).")
                        if vv.yol_modu and any(d_ == "❌" for d_, _ in st.lint_rows(vv)):
                            return self._hata("Plan bu yolda henüz tamamlanmadı: senaryo denetimi temiz değil. Claude'un bitirmesini bekle ya da “Devam ettir” de.")
                        for n in (1, 2):
                            subprocess.run([str(STUDIO / "st"), "kapi", vid, str(n), "basit mod: plan onayı"], cwd=STUDIO, capture_output=True)
                        v = O.load(vid)
                        if all(st.final_versions(v, f) for f in v.formatlar):
                            return self._json({"tamam": True})  # video zaten üretilmiş: doğrudan video onayına geçer
                        j = claude_baslat(vid, "uretim", P_URETIM.format(id=vid))
                        return self._json({"tamam": True, "is": j.ozet()})
                    if asama == "video":
                        subprocess.run([str(STUDIO / "st"), "kapi", vid, "6", "basit mod: video onayı"], cwd=STUDIO, capture_output=True)
                        return self._json({"tamam": True})
                    return self._hata("asama: plan | video")
                if eylem == "degisiklik":
                    metin = (b.get("metin") or "").strip()
                    if not metin:
                        return self._hata("Ne değişsin? Kısaca yaz.")
                    j = claude_baslat(vid, "degisiklik", P_DEGISIKLIK.format(id=vid, metin=metin))
                    return self._json({"tamam": True, "is": j.ozet()})
                if eylem == "devam" and b.get("istek"):
                    d = STUDIO / "videos" / vid
                    (d / "istek.md").write_text(b["istek"].strip() + "\n")
                    v = O.load(vid)
                    j = claude_baslat(vid, "plan", P_PLAN_MEVCUT.format(id=vid, profil=v.profil["ad"], stil=v.gorunus_etiketi,
                                                                       formatlar=", ".join(v.formatlar), ortak=P_YOL_ORTAK.format(id=vid)))
                    return self._json({"tamam": True, "is": j.ozet()})
                if (STUDIO / "videos" / vid / "script.json").exists():  # yol seçilmiş ama plan o yolda tamamlanmamış: tamamlama turunu yeniden dene
                    vv = O.load(vid)
                    gg = st.gates_load(vv)
                    if (vv.yol_modu and (vv.gorunus_json() or {}).get("secim") and not (gg.get("1", {}).get("onay") and gg.get("2", {}).get("onay"))
                            and any(d_ == "❌" for d_, _ in st.lint_rows(vv))):
                        j = claude_baslat(vid, "plan_tamamla", plan_tamamla_istemi(vid))
                        return self._json({"tamam": True, "is": j.ozet()})
                j = claude_baslat(vid, "devam", P_DEVAM.format(id=vid))
                return self._json({"tamam": True, "is": j.ozet()})
            m = re.fullmatch(r"/api/is/([a-f0-9]+)/durdur", u.path)
            if m:
                j = ISLER.get(m.group(1))
                if not j:
                    return self._hata("iş yok", 404)
                j.durdur()
                return self._json(j.ozet(10 ** 9))
            if u.path == "/api/referans":
                b = json.loads(self._govde() or b"{}")
                yol = Path(b.get("yol", "")).expanduser()
                if not yol.exists():
                    return self._hata(f"dosya bulunamadı: {yol}")
                args = ["referans", str(yol)] + ([b["ad"]] if b.get("ad") else [])
                return self._json(is_baslat("referans analizi", args).ozet())
            if u.path == "/api/referans-yukle":
                ad = Path(unquote(q.get("ad", "video.mp4"))).name
                d = KOK / "referans" / "_yuklenen"
                d.mkdir(parents=True, exist_ok=True)
                p = d / ad
                p.write_bytes(self._govde())
                isim = re.sub(r"[^a-z0-9_]+", "_", Path(ad).stem.lower()).strip("_") or "referans"
                return self._json(is_baslat("referans analizi", ["referans", str(p), isim]).ozet())
            if u.path == "/api/ses-dene":
                b = json.loads(self._govde() or b"{}")
                k = b.get("kaynak", "edge")
                if k not in ("edge", "opencode"):
                    return self._hata("kaynak: edge | opencode")
                return self._json(is_baslat(f"ses denemesi ({k})", ["ses-dene", k] + ([b["metin"]] if b.get("metin") else [])).ozet())
            if u.path == "/api/ayar/opencode":
                b = json.loads(self._govde() or b"{}")
                key = (b.get("anahtar") or "").strip()
                envp = STUDIO / ".env"
                lines = [ln for ln in (envp.read_text().splitlines() if envp.exists() else []) if not ln.startswith("OPENCODE_API_KEY=")]
                if key:
                    lines.append(f"OPENCODE_API_KEY={key}")
                envp.write_text("\n".join(lines) + "\n")
                os.chmod(envp, 0o600)
                return self._json({"tamam": True, "ayarli": bool(key)})
            if u.path == "/api/kapat":
                self._json({"tamam": True, "not": "Panel kapanıyor; süren işler arka planda devam eder."})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return None
            if u.path == "/api/remotion":
                try:
                    import urllib.request
                    urllib.request.urlopen("http://localhost:3000", timeout=1)
                    return self._json({"url": "http://localhost:3000", "durum": "açık"})
                except Exception:  # noqa: BLE001
                    j = Is("Remotion Studio", ["npx", "remotion", "studio", "--port", "3000", "--no-open"])
                    ISLER[j.id] = j
                    return self._json({"url": "http://localhost:3000", "durum": "başlatılıyor", "is": j.ozet()})
            return self._hata("bulunamadı", 404)
        except json.JSONDecodeError as e:
            return self._hata(f"JSON hatası: {e}")
        except SystemExit as e:
            return self._hata(str(e))
        except (PermissionError, KeyError, ValueError, subprocess.CalledProcessError) as e:
            return self._hata(e)


def isleri_yukle():
    """Panel kapandığında süren ya da biten işleri geri yükler (son 60 iş)."""
    if not ISDIR.exists():
        return
    metas = []
    for p in ISDIR.glob("*.json"):
        try:
            metas.append(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    for m in sorted(metas, key=lambda m: m.get("bas", 0))[-60:]:
        try:
            j = ClaudeIs(None, None, None, _meta=m, bitince=claude_bitti) if m.get("tur") == "claude" else Is(None, None, _meta=m)
            ISLER[j.id] = j
        except Exception as e:  # noqa: BLE001
            print(f"iş geri yüklenemedi {m.get('id')}: {e}", flush=True)


def main():
    isleri_yukle()
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=4777)
    ap.add_argument("--ac", action="store_true", help="tarayıcıda aç")
    a = ap.parse_args()
    url = f"http://localhost:{a.port}"
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    except OSError:
        # Port dolu: panel zaten açıksa yalnız tarayıcıyı aç
        try:
            import urllib.request
            urllib.request.urlopen(url + "/api/genel", timeout=2)
            print(f"Panel zaten açık: {url}", flush=True)
            if a.ac:
                webbrowser.open(url)
            return
        except Exception:  # noqa: BLE001
            raise SystemExit(f"{a.port} portu başka bir program tarafından kullanılıyor. Başka port: ./st panel --port 4778")
    print(f"Stüdyo paneli: {url}  (kapatmak için Ctrl+C)", flush=True)
    if a.ac:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
