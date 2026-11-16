"""st — stüdyo komut satırı. Bir videoyu kapı kapı yürütür ve her kapıda kanıt bırakır.

Video
  ./st yeni <id> "Başlık" [--profil P] [--seri S] [--formatlar 16x9,9x16] [--motor remotion|hyperframes|blender] [--marka M] [--dil tr|en]
            [--gorsel G1,G2] [--animasyon A] [--ses S] [--esin gorsel,animasyon,ses] [--muzik-kaynagi kod|ace] [--cesaret saglam|cesur|sinirsiz]
            [--altyazi klasik|niyetli] [--cizer cycles|eevee]
                                                    iskelet: brief, görünüş, senaryo (profilin vuruşlarıyla: öneri iskelet; film kendi
                                                    yapısını script.json → yapi ile kurabilir), işaretler, ses tasarımı, sahne kodu, her format için kompozisyon.
                                                    Motor (araç; tarz seçmez): remotion (src/<id>/Video.tsx, React) ya da hyperframes
                                                    (hf/<id>/index.html, HTML + SVG + GSAP) ya da blender (blender/<id>/sahne.py, Cycles
                                                    plakaları + Remotion üst katmanı: gerçek ışık, malzeme ve kamera; her tarz). Blender'da
                                                    --cizer eevee: Cycles yerine EEVEE (çok daha hızlı; stilize, çizgi film, düz renk). --marka markalar/<ad>/.
                                                    --seri yoksa görünüş videoya özeldir (3 seçenek, seçim kullanıcının).
                                                    Katalog seçimleri (./st katalog) birbirinden ve motordan bağımsızdır; tür başına 0–3 kart.
                                                    Kart yok = filme özel icat. Esin (birden çok kart ya da --esin'deki tür) = başlangıç noktası:
                                                    script.json → esin, görüntüde gorunus.json → esin_stilleri (üç seçeneği Claude yazar).
                                                    Aynen (tek kart, --esin'de yok): --gorsel stilin 3 varyasyonunu görünüş seçeneklerine koyar,
                                                    --animasyon hareket tarifini, --ses müzik/efekt/anlatıcı ayarını işler (script.json → katalog)
  ./st gorunus <id> [--format F] [--hepsi]   görünüş denemesi: gorunus.json'daki seçenekleri doğrular, birbirleriyle ve önceki videolarla
                                   karşılaştırır, kanca karesini her biriyle çizer → inceleme/gorunus/. Yol modunda (gorunus.json → yol_modu)
                                   her seçenek bir yoldur: yol bloğu denetlenir (zorunlu alanlar, üç yolun yöntemi farklı), sahne kodu seçenek
                                   harfine göre dallanır; yol seçildiyse yalnız seçilen yol yeniden çizilir ve önceki karesiyle karşılaştırılır
  ./st gorunus <id> sec <harf>     görünüşü ya da yolu seç (kullanıcı kararı)
  ./st seri <id> <ad>              videonun seçilmiş görünüşünü paylaşılan bir seri yapar → stiller/<ad>/ (sonraki videolar --seri <ad>)
  ./st katalog [gorsel|animasyon|ses] [--ad A] [--yeniden]   stil kataloğu: doğrular, önizlemeleri üretir → katalog/onizleme/, katalog/indeks.json
  ./st katalog motor [--yeniden]   yeni film levhasındaki motor önizlemesi (katalog/motor/<motor>/sahne.py → katalog/onizleme/motor/)
  ./st katalog altyazi [--yeniden] yeni film levhasındaki altyazı önizlemesi (klasik ve niyetli; aynı diyalog → katalog/onizleme/altyazi/)
  ./st katalog cizer [--yeniden]   yeni film levhasındaki Blender çizeri önizlemesi (aynı kare Cycles ve EEVEE → katalog/onizleme/cizer/)
  ./st durum [<id>]                kapı durumu + eksik kanıt + sıradaki adım
  ./st kapi <id> <1-6> "not"       insan onayı kaydet (kapı 1, 2, 6)
  ./st lint <id>                   senaryo + çekim listesi denetimi (profil çıtalarıyla)
  ./st cekim <id>                  çekim listesini (cekim-listesi.md) üret

Ses
  ./st ses <id>                    (müzik varsa vuruş ızgarası) → anlatım + kelime zamanları → ses tasarımı + miks
  ./st muzik <id> [--kaynak kod|ace] [--stil S] [--bpm N] [--yapi …] [--ton A]   müzik: ses.muzik_tarifi (filme özel) > ses stili
                                   (kod ya da ACE-Step) > geçici prosedürel
  ./st vurus <id>                  müzikten vuruş ızgarası (BPM, vuruşlar, ölçü başları)
  ./st zaman <id>                  kelime zamanlarını Whisper ile çapraz kontrol
  ./st ses-dene <kaynak> ["metin"]  ses kaynağını dene: edge | opencode (Magnific anlatıcısı: ./st uret anlatim)
  ./st niyet <id>                  niyetli altyazı (script.json → "altyazi": "niyetli"): anlatımdan kelime başına şiddet ve perde →
                                   değişken yazı tipinin ağırlığı, genişliği, boyutu; sayfa ve satırlar her format için → timeline.json → niyet
                                   (./st ses kendiliğinden çalıştırır; pipeline/niyet.py)

Görüntü ve inceleme ([--format F] verilmezse videonun bütün formatları)
  ./st kare <id> 3.2s 77 ...       tek tek kare render (saniye ya da kare no; Blender: [--kalite taslak|tam])
  ./st temsili <id>                kapı 3: her vuruştan bir temsilî kare
  ./st render <id> [--final]       kaba kurgu (varsayılan) ya da final teslim
  ./st inceleme <id>               kapı 4: kontak tabakası + ölçüm + inceleme şablonu (yeni sürüm klasörü)
  ./st olc <id>                    yalnız ölçüm (son inceleme klasörüne)
  ./st elestir <id>                kör eleştiri: filmi hiç görmemiş bir Claude oturumu yalnız kareleri ve ölçümü görür → inceleme/vN/elestiri.md
  ./st deterministik <id>          atlanabilirlik testi: aynı kareler iki farklı sırada → bayt bayt aynı mı?
  ./st yayin <id>                  yayın paketi taslağı
  ./st yapim <id> [--format F] [--cikti <dosya|klasör>] [--plan] [--onizle]   yapım filmi ("nasıl yapıldı", 15 sn): filmin kendi
                                   kayıtlarından (yollar ve seçilen, kılavuz kipi, Blender'ın kil / tel kafes / kamera yolu geçişleri,
                                   inceleme turları, yapay zekâ kaynağı, kapılar) → ../cikti/<id>_yapim.mp4 + ölçüm (pipeline/yapim.py);
                                   ./st deterministik <id> --yapim

Stüdyo
  ./st panel                       kontrol panelini tarayıcıda aç (http://localhost:4777)
  ./st referans <video> [ad]       referans videoyu ölç (palet, tempo, kesme, ses) → referans/<ad>/analiz.md
  ./st profiller                   profilleri ve formatları listele
  ./st paket [--ornek ihh_sofra|yok] [--marka M] [--hedef ~/Desktop]   stüdyoyu başka bir Apple Silicon Mac'e göndermek için
  ./st paket --depo [sahip/ad] [--ornek …] [--marka …]   aynı paket zip yerine özel GitHub deposuna (karşı taraf oradan günceller)
  ./st paket --acik [--ornek ihh_sofra|yok] [--marka ihh]   herkese açık depo (MIT; üçüncü taraf içerik yok): out/_acik/studyo, yalnız yerel commit
                                   kurulum zip'i (Kur.command kurar ve günceller; .env, öteki videolar ve ara çıktılar girmez)
  ./st regresyon kaydet|karsilastir [--video V]   kural 11: eski filmlerin kareleri bayt bayt aynı mı? Değişiklikten ÖNCE kaydet
                                   (regresyon.json fikstürleri + arşivde olmayan filmlerin lint'i → out/_regresyon/), sonra karşılaştır
  ./st tip [<id>]                  sahne kodu denetimi: TypeScript (Remotion), hyperframes check (HyperFrames) ya da
                                   sahne taraması + kuru kurulum + üst katman TypeScript'i (Blender)
  ./st gecis liste [--etiket E]     gölgelendirici geçişleri (gl-transitions 3.0.0, MIT; 184): ad, etiketler, lisans, parametreler
  ./st gecis onizle <ad …>|--hepsi [--yeniden]   iki nötr kartla 1,5 sn'lik önizleme → katalog/onizleme/gecis/ (panel → Kütüphane → Geçişler)
  ./st gecis <id> durum|esitle|plaka [--format F]   filmin kesimleri (script.json → shot.gecis): pencereler, geçiş plakaları
                                   (out/_gecis/<id>/; ./st kare, temsili, inceleme, render kendiliğinden üretir), public/<id>/gecis.json
  ./st plaka <id> durum|ciz [sahne] [--format F] [--kalite taslak|tam]   karma film (script.json → sahneler: sahne başına motor; Remotion
                                   birleştirir): sahnelerin pencereleri ve plakaları (out/_plaka/<id>/<sahne>/; ./st kare, inceleme, render kendiliğinden çizer)
  ./st plaka <id> yeni <ad> --motor hyperframes|blender|manim --bas <işaret> --son <işaret> [--cizer eevee] [--saydam]
                                   sahnenin iskeleti (hf|blender|manim/<id>/sahneler/<ad>/) + script.json → sahneler satırı
  ./st hf <id> --sahne <ad> <komut …> · ./st blender <id> --sahne <ad> durum|plaka|ac   karma filmin sahnesi kendi motorunda (yerel zaman)
  ./st manim <id> --sahne <ad> durum|ciz|onizle [--format F]   karma filmin Manim sahnesi (formül, grafik, şema; Cairo; bütün plakalar bir kez)
  ./st hf <id> <komut …>           HyperFrames CLI'yi videonun klasöründe çalıştırır (lint, check, snapshot, timeline, keyframes,
                                   inspect, catalog, add, docs, audio …); önce görünüş, işaretler ve ses eşitlenir
  ./st blender <id> durum|plaka|ac|temizle|cizer   Blender videosu: plaka önbelleği (durum), plakaları çiz (plaka [--format F]
                                   [--kalite taslak|tam] [--kareler 0,30]), sahneyi Blender arayüzünde aç (ac), eski kümeleri sil,
                                   çizeri değiştir (cizer cycles|eevee; kullanıcı kararı: görüntü değişir, plakalar yeniden çizilir)

3B model kütüphanesi (threejsassets.com ücretsiz GLB'leri; ticari kullanım serbest, atıf yok, dosya paylaşılmaz; pipeline/model3b.py)
  ./st 3b ara <sözcük …> [--kategori K] [--hepsi] [--n 20]   katalogda ara (ad, açıklama, paket; varsayılan yalnız ücretsiz)
  ./st 3b al <slug> [--url <bağlantı>]   kütüphaneye indir: MCP'nin doğrudan bağlantısı (--url) ya da studio/.env TJA_API_KEY;
                                   ikisi de yoksa tarayıcı tarifi (indir → ekle)
  ./st 3b ekle <dosya.glb> [--slug S]   tarayıcıyla indirilen modeli kütüphaneye al (panel: Kütüphane → 3B modeller)
  ./st 3b liste                    kütüphanedeki modeller ve kullanıldıkları filmler
  ./st 3b incele <slug|dosya.glb>  boyut ve taban (metre), üçgen, malzeme, köşe rengi, animasyonlar, gereken çözücü
  ./st 3b kullan <id> <slug …>     filme al: public/<id>/varliklar/3b/<slug>.glb + varliklar.md satırı + çözücüler
  ./st 3b onizle <slug> [--yeniden]   modeli stüdyonun 3B katmanında çiz → kutuphane/3b/threejsassets/<slug>.png

Üretim deposu (Magnific: görsel, video, efekt sesi, 3B, stok; bir kez üretilir, dondurulur; pipeline/uretim.py)
  ./st uret al <id> <ad> --url <bağlantı> --tur gorsel|video|ses|3b|stok --model <m> --arac <araç> --istem "…" --kredi <n>
            [--parametre '<json>'] [--kaynak-kare <dosya>] [--insan] [--etiket] [--uyum] [--ses-kalsin]
                                   üretimden HEMEN sonra (bağlantı ~30 dk): indir, sha256 + ffprobe → videos/<id>/uretim/<ad>.<uz> (asıl) +
                                   public/<id>/varliklar/uretim/ (üç motor buradan okur) + uretim.json + varliklar.md ✅. Videoda modelin
                                   sesi çıkarılır (--ses-kalsin hariç); --uyum kare hızını filme bir kez çevirir. --insan: gerçekçi insan
                                   canlandırması → ekranda etiket zorunlu (--etiket: insan yokken de etiket)
  ./st uret liste <id>             varlıklar, kullanıldıkları yer, harcanan / sınır
  ./st uret butce <id> [--tahmin N] [--arac A]   kalan kredi; tahmin sınırı aşıyorsa çıkış kodu 3 (DUR, kullanıcıya sor),
                                   geçerse tek kullanımlık izin (panel işinde kanca bunsuz ücretli çağrıyı durdurur)
  ./st uret sil <id> <ad>          kullanılmayan varlığı sil (harcama kaydı kalır)
  ./st uret bakiye [<id>] --kalan N [--an bas|son|okuma]   account_balance sonucunu kaydet (panel: son bilinen bakiye)
  ./st uret anlatim <id>           anlatıcısı Magnific olan filmde (ses.kaynak = magnific) eksik anlatım parçaları: metin, anahtar ve
                                   komutlar (audio_tts → ./st uret al <id> anlatim_<anahtar> --tur anlatim); sonra ./st ses
  ./st uret yukle <dosya> --put <bağlantı>   yerel kareyi Magnific'e yükle (creations_request_upload → yukle → finalize)
  ./st uret beyan <id>             yayin.md'deki yapay zekâ beyanını uretim.json'dan yenile

Canlı veri (gerçek ve güncel veriyle yeniden çizilen film; açık kaynak, atıf zorunlu; pipeline/veri.py)
  ./st veri saglayicilar           hazır kaynaklar ve lisansları (met-norway: CC BY 4.0, kurum kampanyasında kullanılabilir; open-meteo: ücretsiz
                                   katmanı yalnız ticari olmayan kullanım, kampanyada kullanılmaz)
  ./st veri <id> kur --saglayici S --konum "Ad" --enlem E --boylam B [--saat-dilimi Europe/Istanbul] [--tazelik SA] [--kullanim kurum|ticari_olmayan]
                                   videos/<id>/veri.json (kaynak sözleşmesi: URL, alanlar, birim, konum, atıf, lisans); konum kullanıcının kararı,
                                   şehir düzeyine yuvarlanır
  ./st veri <id> cek [--ciz]       anlık görüntü: tek istek → videos/<id>/veri/<kimlik>/ (ham yanıt bayt bayt + kayıt: zaman damgası, URL, sha256,
                                   değerler); atıf kaynaklar.md (✅) ve yayin.md'ye; yeni görüntü seçili olur. Ağ hatasında ya da beklenmeyen
                                   veride DURUR (çıkış 2; önceki görüntüye sessizce düşmez); kaynağın önbellek süresi dolmadıysa istek yok (çıkış 4).
                                   --ciz: kanıt karesini (script.json → veri_isareti) her format için çizer
  ./st veri <id> sec <kimlik|son> [--ciz]   çizilecek görüntüyü seç · ./st veri <id> liste · ./st veri <id> kare (kanıt kareleri)
  ./st veri <id> denetle           sözleşme, dondurma, sahne kodu (veriyi okuyor mu, ağ var mı), kanıt karelerinde ekrandaki yazı (macOS Vision)

Gerçek görüntü (zanaat §2 yol B ve D; kendi çekim, kurum arşivi, stok; pipeline/goruntu.py, pipeline/derinlik.py)
  ./st goruntu ekle <id> <dosya | stok:<ad> | uretim:<ad>> [--ad A] [--kaynak kendi|arsiv|acik] [--kisi | --kisi-yok] [--riza evet|hayir|bilinmiyor]
            [--bas SN] [--son SN] [--not "…"] [--dokum-yok]
                                   kopyalar, ffprobe ile ölçer, ara formata çevirir (film kare hızı, sabit, yüksek bit oranı), konuşma varsa
                                   kelime zamanlı döküm (mlx-whisper), sahne kesmeleri (scdet), kontak tabakası → videos/<id>/goruntu/<ad>/;
                                   motorun kopyası public/<id>/varliklar/goruntu/ + varliklar.md. Kişi belirtilmezse insan modeliyle tahmin edilir;
                                   kişi tahmini ve rıza bilgisi kayda girer (kapı değil; kullanıcı isterse yüz gizleme ya da stilize seçer)
  ./st goruntu riza <id> <ad> [--riza evet|hayir|bilinmiyor] [--cozum stilize|gizle|kullanma|yok] [--kisi | --kisi-yok]   kullanıcının kararı
  ./st goruntu kadraj <id> <ad> --format F [--yakinlik 0.2–1] [--hedef govde|bas] [--yumusak SN] [--ozne en_buyuk|hepsi]
                                   özne takibi (ana öznenin ağırlık merkezi ya da başı): yumuşak kırpma yolu, özne formatın güvenli alanında
                                   (merkezden kırpma yok) → kadraj_<F>.json; Remotion <Goruntu kadraj> okur
  ./st goruntu liste <id>          kayıt, rıza, türevler, kullanıldığı yer (public/<id>/goruntu/bilgi.json'ı yeniler)
  ./st goruntu sil <id> <ad>       kullanılmayan görüntüyü ve türevlerini sil
  ./st derinlik <id> <ad>          derinlik haritası (Depth Anything V2 Small, yerel): görselde 16 bit PNG, videoda kare dizisi (FFV1) → dondurulur
  ./st maske <id> <ad> [--kutu x0,y0,x1,y1] [--kutu-kare N]   alfa maskesi: insan (HyperFrames remove-background) ya da nesne (--kutu,
                                   0–1; SAM 2.1, videoda kutudan bütün kareye) → dondurulur
  ./st sandvic <id> <ad> --bas SN [--sure 5] [--format F]   anahtar kare sandviçi: motorun bas karesini ve klipten sonraki ilk karesini PNG
                                   çizer (videos/<id>/uretim/_anahtar/<ad>/), Magnific'e ilk ve son kare olarak verilecek adımları yazar

Kamera takibi (FOOH: gerçek sokakta imkânsız nesne; Blender + Remotion; pipeline/takip.py, blender/takip/)
  ./st takip <id> <görüntü | dosya> [--ad A] [--bas SN] [--son SN] [--yukseklik M] [--odak MM] [--hedef PX] [--elle iz|cozum]
            [--kaynak kendi|arsiv|acik] [--not "…"] [--kisi | --kisi-yok] [--riza …]
                                   Blender arka planda özellik bulur, izler, kamerayı çözer (odak, mercek bozulması), zemini ve ölçeği
                                   kurar (kamera yüksekliği --yukseklik, varsayılan 1,5 m); çözüm hatasını raporlar; çözümü dondurur →
                                   videos/<id>/takip/<ad>/ (cozum.json + sha256, iz.blend, onizleme.png, hata.png). Dosya verilirse önce
                                   gerçek görüntü hattından eklenir (ara format, kişi tahmini, rıza). --elle iz: iz.blend'deki (elle
                                   düzeltilmiş) izlerle yeniden çöz · --elle cozum: Blender'da elle yapılan çözümü aynen al (zemin + ölçek)
  ./st takip <id> liste | denetle | sec <ad> | ac <ad> | onizle [<ad>] | olcek <ad> <m> | nesne [<ad>]
                                   çözümler · dondurma, kabul (hata ≤ 1 px) ve kayma (gölgenin altındaki zemin izleri) · çizilecek çözümü seç ·
                                   iz.blend'i Blender'da aç (elle iz) · önizlemeyi (izler + 1 m'lik zemin ızgarası) yeniden çiz · kamera
                                   yüksekliğini değiştir (çözüm aynen, yalnız ölçek; saniyeler) · nesnenin çekim üstündeki önizlemesi (filmin
                                   dört karesi → videos/<id>/takip/<ad>/nesne/)
"""
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys

import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak as O  # noqa: E402

PY = str(O.ROOT / ".venv" / "bin" / "python")
CIKTI = O.KANAL / "cikti"
SABLON = O.ROOT / "sablon"
YENI_FPS = 30  # yeni videoların kare hızı (profil "fps" ile değiştirebilir); eski videolar script.json'da fps yoksa 24

GATES = {
    1: ("Brief + gerçekler (kaynak/varlık)", True),
    2: ("Senaryo + çekim listesi", True),
    3: ("Temsilî kareler", False),
    4: ("Kaba kurgu + kontak + ölçüm", False),
    5: ("En büyük 3 kusur onarıldı", False),
    6: ("Ses, formatlar, teslim + yayın paketi", True),
}


def run(cmd, **kw):
    print("→", " ".join(str(c)[:160] for c in cmd))
    return subprocess.run([str(c) for c in cmd], cwd=O.ROOT, check=True, **kw)


def today():
    return dt.date.today().isoformat()


def opts(args, *names):
    """Konumsal argümanlar + --ad değer seçenekleri. Bayrak (değersiz) seçenekler True olur."""
    pos, o, i = [], {}, 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            k = a[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--") and k in names:
                o[k] = args[i + 1]
                i += 2
                continue
            o[k] = True
        else:
            pos.append(a)
        i += 1
    return pos, o


def fmts(v, o):
    f = o.get("format")
    if f and f not in v.formatlar:
        raise SystemExit(f"{v.id} bu formatta yok: {f} (formatlar: {', '.join(v.formatlar)})")
    return [f] if f else v.formatlar


# ---------------------------------------------------------------- kapı kayıtları
def gates_file(v):
    return v.dir / "kapilar.json"


def gates_load(v):
    p = gates_file(v)
    return O.jload(p) if p.exists() else {}


def gates_save(v, g):
    gates_file(v).write_text(json.dumps(g, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- render yardımcıları
def render_frames(v, frames, out_dir: Path, fmt=None, order="asc", props=None):
    fmt = fmt or v.formatlar[0]
    props = _veri_props(v, props)
    if v.motor == "hyperframes":
        import hf
        hf.esitle(v)
        if (props or {}).get("kisi"):   # kişisel film: şablonun örneği değilse satırın verisiyle varyant (videos/<id>/toplu/_gecici/, sonra silinir)
            import kisisel
            if props["kisi"] != kisisel.ornek_kisi(v):
                with kisisel.gecici_dizin(v) as g:
                    kok = hf.kisi_varyanti(v, fmt, props["kisi"], g / fmt)
                    return hf.kareler(v, frames, out_dir, fmt, order, None, props.get("yazilim", False), kok=kok)
        return hf.kareler(v, frames, out_dir, fmt, order, (props or {}).get("gorunus"), (props or {}).get("yazilim", False))
    if v.motor == "blender":  # plakalar (önbellek ya da Blender) → üst katman Remotion'da, aşağıdaki yolla
        import blender
        props = blender.hazirla(v, frames, fmt, props)
    import plaka
    if plaka.var_mi(v):  # karma film (6b): istenen karelere düşen sahnelerin motor plakaları (HyperFrames, Blender); sahne dışı kare plaka çizdirmez
        props = plaka.hazirla(v, frames, fmt, props)
    import gecis
    if gecis.var_mi(v):  # gölgelendirici kesimleri (6a): penceredeki karelerin iki tarafının plakası önce (yalnız geçişli filmde)
        props = gecis.hazirla(v, frames, fmt, props)
    spec = {"comp": v.comp_for(fmt), "out": str(out_dir), "frames": sorted(set(int(f) for f in frames)), "order": order, "props": props or {},
            **({"gl": v.gl} if v.gl else {})}  # 3B katman: yazılımla (O.UC_GL); öteki videolar bayraksız
    if "kisi" in (props or {}):  # kişisel film: kişi verisi komut satırına (günlüğe) yazılmaz, iş tanımı geçici dosyada
        import kisisel
        with kisisel.gecici_dosya(v, spec) as yol:
            r = run(["node", "pipeline/kareler.mjs", f"@{yol}"], capture_output=True, text=True)
    else:
        r = run(["node", "pipeline/kareler.mjs", json.dumps(spec)], capture_output=True, text=True)
    res = json.loads(r.stdout.strip().splitlines()[-1])
    print(f"   [{fmt}] {len(res['files'])} kare, {res['seconds']:.1f} sn")
    return {int(k): Path(p) for k, p in res["files"].items()}


def _veri_props(v, props=None):
    """Canlı veri (veri.json'u olan film): seçili anlık görüntünün çizim verisi Remotion'a girdi olur (props.veri; HyperFrames'e ST.veri,
    Blender'a ST.veri köprülerinde). Kişisel film (veri_sablonu.json): şablonun TEST örneği props.kisi (./st toplu her satırın kendisini verir).
    Öteki filmlerin props'u olduğu gibi kalır (kareleri değişmez)."""
    import kisisel
    import veri
    ek = {}
    if veri.var_mi(v):
        veri.esitle(v)
        ek.update(veri.props(v))
    if kisisel.var_mi(v):
        kisisel.esitle(v)
        ek.update(kisisel.props(v))
    if not ek:
        return props
    return {**ek, **(props or {})}


def _props_bayragi(v) -> list[str]:
    """npx remotion render/still: canlı veri ya da kişisel filmde --props (seçili görüntü, şablonun TEST örneği), öteki filmlerde hiçbiri.
    Kişisel filmde props dosyayla (out/_props/<id>.json): kişi verisi komut satırına yazılmaz."""
    p = _veri_props(v) or {}
    if "kisi" in p:
        d = O.ROOT / "out" / "_props"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{v.id}.json").write_text(json.dumps(p, ensure_ascii=False))
        return ["--props", str(d / f"{v.id}.json")]
    return ["--props", json.dumps(p, ensure_ascii=False)] if p else []


def render_jobs(isler):
    """Birden çok (kompozisyon, kareler, props) işini tek paket ve tek tarayıcıyla render eder → [ {kare: yol} ].
    İşte "gl" varsa (3B katman) o iş o GL ayarıyla açılmış ayrı bir tarayıcıda çizilir."""
    r = run(["node", "pipeline/kareler.mjs", json.dumps({"isler": [{**i, "out": str(i["out"])} for i in isler]})], capture_output=True, text=True)
    res = json.loads(r.stdout.strip().splitlines()[-1])
    print(f"   {len(isler)} iş, {res['seconds']:.1f} sn")
    return [{int(k): Path(p) for k, p in j["files"].items()} for j in res["isler"]]


def parse_times(args, fps):
    return [int(round(float(a[:-1]) * fps)) if a.endswith("s") else int(a) for a in args]


def rough_path(v, fmt):
    return O.ROOT / "out" / f"{v.id}{v.suffix(fmt)}_kaba.mp4"


def final_versions(v, fmt):
    pat = re.compile(rf"^{re.escape(v.id + v.suffix(fmt))}_v(\d+)\.mp4$")
    return sorted((p for p in CIKTI.glob(f"{v.id}*_v*.mp4") if pat.match(p.name)), key=lambda p: int(pat.match(p.name).group(1)))


def review_names(v, fmt):
    """Tek formatlı videoda eski adlar (kontak.png, kareler/), çok formatlıda -<format> ekli."""
    sx = "" if len(v.formatlar) == 1 else f"-{fmt}"
    return f"kontak{sx}.png", f"kareler{sx}", f"temsili{sx}.png"


# ---------------------------------------------------------------- yeni video
# Cesaret: kullanıcının seçimi (yeni film levhası). Plan istemine ve brief'e girer; script.json → cesaret.
CESARET = {
    "saglam": ("Sağlam", "Denenmiş, net bir dil; yine de bir olağanüstü an."),
    "cesur": ("Cesur", "En az bir beklenmedik fikir ve bir olağanüstü an."),
    "sinirsiz": ("Sınırsız", "İlk saniyede alışkanlığı kıran açılış, en az bir 'imkânsız ama gerçek görünen' an, stüdyonun daha önce yapmadığı bir teknik."),
}
TUR_AD = {"gorsel": "Görüntü", "animasyon": "Hareket", "ses": "Ses"}


def katalog_normalize(k) -> dict:
    """Panel kaydındaki (istekler/<id>.json, videos/<id>/claude.json) katalog seçimi → {tür: {kartlar, mod, tarif}, muzik_kaynagi}.
    Eski şema ({"gorsel": "ad" | None, …}): tek ad = aynen (eski filmler eski anlamını korur), None = kart yok (filme özel icat)."""
    k = k if isinstance(k, dict) else {}
    out = {}
    for t in TURLER:
        x = k.get(t)
        if isinstance(x, str) and x:
            out[t] = {"kartlar": [x], "mod": "aynen", "tarif": ""}
        elif isinstance(x, dict):
            kartlar = [a for a in (x.get("kartlar") or []) if isinstance(a, str) and a][:3]
            out[t] = {"kartlar": kartlar, "mod": "aynen" if x.get("mod") == "aynen" and len(kartlar) == 1 else "esin",
                      "tarif": str(x.get("tarif") or "").strip()[:400]}
        else:
            out[t] = {"kartlar": [], "mod": "esin", "tarif": ""}
    out["muzik_kaynagi"] = k.get("muzik_kaynagi") if k.get("muzik_kaynagi") in ("kod", "ace") else None
    return out


def _tarif_satiri(meta) -> str:
    """Brief → Görsel → "Kullanıcının tarifi": panel kaydındaki kendi tarifler aynen; kayıt yoksa (komut satırı) Claude doldurur."""
    if meta is None:
        return '[görüntü / hareket / ses için kullanıcının kendi tarifi aynen; yoksa "yok"]'
    K = katalog_normalize(meta.get("katalog"))
    p = [f"{TUR_AD[t]}: «{K[t]['tarif'].replace('[', '(').replace(']', ')')}»" for t in TURLER if K[t]["tarif"]]
    return " · ".join(p) if p else "yok"


def _skeleton(vid, title, prof, seri=None):
    P = O.profil(prof)
    comp = "".join(p.capitalize() for p in vid.split("_"))
    ents = []
    for i, step in enumerate(P["vuruslar"], 1):
        shot = {"plan": "", "giris": "", "cikis": "", "gecis": "", "olay": "", "ses": "", "amac": ""}
        if P.get("anlatim", True):
            e = {"id": f"s{i}", "step": step, "pauseAfter": 0.35, "parts": [{"text": f"[{step} cümlesi]"}], "shot": {"anahtar": "", **shot}}
        else:
            e = {"id": f"b{i}", "step": step, "bas": ["vurus", (i - 1) * 4], "bit": ["vurus", i * 4], "shot": {"isaret": "", **shot}}
        ents.append(e)
    ses = ({"kaynak": "edge", "voice": "tr-TR-EmelNeural", "rate": "+8%", "pitch": "-2Hz"} if P.get("anlatim", True)
           else {"kaynak": "yok", "muzik": "muzik.wav"})
    # görünüş: videoya özel (gorunus.json, 3 seçenek) ya da seri (stiller/<ad>/gorunus.json); bitis burada yalnız videoya özel düzeltmedir
    sc = {"id": vid, "title": title, "profil": prof, "gorunus": f"seri:{seri}" if seri else "video", "comp": comp, "fps": P.get("fps", YENI_FPS),
          "bitis": {}, "kor_elestiri": True, "ses": ses,
          "leadIn": 0.2, "tail": 1.6, "learningGoal": "", "sentences": ents}
    if not P.get("anlatim", True):
        sc["sure"] = ["vurus", len(P["vuruslar"]) * 4, 1.5]
    return sc, comp, P


def _dump_script(sc):
    head = {k: v for k, v in sc.items() if k != "sentences"}
    lines = ["{"] + [f'  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},' for k, v in head.items()] + ['  "sentences": [']
    for i, e in enumerate(sc["sentences"]):
        lines.append("    " + json.dumps(e, ensure_ascii=False) + ("," if i < len(sc["sentences"]) - 1 else ""))
    return "\n".join(lines + ["  ]", "}"]) + "\n"


def cmd_yeni(*args):
    pos, o = opts(args, "profil", "seri", "stil", "formatlar", "istek", "gorsel", "animasyon", "ses", "muzik-kaynagi", "motor", "marka", "dil",
                  "esin", "cesaret", "altyazi", "cizer")
    if len(pos) < 2:
        raise SystemExit('Kullanım: ./st yeni <id> "Başlık" [--profil P] [--seri S] [--formatlar 16x9,9x16]')
    vid, title = pos[0], pos[1]
    prof = o.get("profil", O.VARSAYILAN_PROFIL)
    seri = o.get("seri") or o.get("stil")  # --stil eski adı: artık "bu seriyi paylaş" demektir
    d = O.ROOT / "videos" / vid
    if d.exists():
        raise SystemExit(f"Zaten var: {d}")
    if seri and not (O.ROOT / "stiller" / seri / "gorunus.json").exists():
        raise SystemExit(f"Seri yok: stiller/{seri}/gorunus.json (mevcut: {', '.join(p.name for p in (O.ROOT / 'stiller').iterdir() if (p / 'gorunus.json').exists())})")
    sc, comp, P = _skeleton(vid, title, prof, seri)
    if o.get("formatlar"):
        sel = o["formatlar"].split(",")
        bad = [f for f in sel if f not in O.FORMATLAR]
        if bad:
            raise SystemExit(f"Tanımsız format: {', '.join(bad)} (mevcut: {', '.join(O.FORMATLAR)})")
        sc = {**{k: v for k, v in sc.items() if k != "sentences"}, "formatlar": sel, "sentences": sc["sentences"]}
        P = {**P, "formatlar": sel}
    # Katalog kartları: tür başına 0–3. Kart yok = filme özel icat. Birden çok kart ya da --esin'deki tür = esin (başlangıç noktası,
    # Claude karıştırır ve aşar); tek kart ve --esin'de yok = aynen (bugünkü davranış: tarife uyulur).
    kartlar = {t: [a for a in str(o.get(t) or "").split(",") if a and a != "True"] for t in TURLER}
    for tur, adlar in kartlar.items():
        if len(adlar) > 3 or len(set(adlar)) != len(adlar):
            raise SystemExit(f"--{tur}: en çok 3 farklı kart (verilen: {', '.join(adlar)})")
        for ad in adlar:
            if not (KATALOG / tur / f"{ad}.json").exists():
                raise SystemExit(f"Katalogda yok: {tur}/{ad} (mevcut: {', '.join(_katalog_kayitlar(tur))})")
            if _katalog_kayitlar(tur)[ad].get("durum") == "taslak":
                raise SystemExit(f"{tur}/{ad} henüz taslak: önce panelde onayla")
    esin_t = [t for t in str(o.get("esin") or "").split(",") if t and t != "True"]
    for t in esin_t:
        if t not in TURLER:
            raise SystemExit(f"--esin: tür {t} yok ({', '.join(TURLER)})")
        if not kartlar[t]:
            raise SystemExit(f"--esin {t}: bu türde kart yok (--{t} a,b)")
    mod = {t: "esin" if len(a) > 1 or t in esin_t else "aynen" for t, a in kartlar.items() if a}
    aynen = {t: kartlar[t][0] for t, m in mod.items() if m == "aynen"}
    esin = {t: kartlar[t] for t, m in mod.items() if m == "esin"}
    if kartlar["gorsel"] and seri:
        raise SystemExit("--gorsel ile --seri birlikte olmaz: seri görünüşü zaten seçilmiş bir görünüştür")
    # basit mod: panelin yazdığı istek kaydı (istekler/<id>.json) kullanıcının kendi tarifini ve cesaretini taşır
    ip = (O.ROOT / o["istek"]).resolve() if isinstance(o.get("istek"), str) else None
    meta = O.jload(ip.with_suffix(".json")) if ip and ip.with_suffix(".json").exists() else None
    cesaret = o.get("cesaret") if isinstance(o.get("cesaret"), str) else (meta or {}).get("cesaret")
    if cesaret and cesaret not in CESARET:
        raise SystemExit(f"--cesaret: {', '.join(CESARET)} (verilen: {cesaret})")
    # Motor yalnız açık seçimdir: görüntü stili ve hareket tipi motoru seçmez (eksenler bağımsız; örneğin motoru yalnız bilgi: ornek_motor)
    motor = o.get("motor") or "remotion"
    if motor not in ("remotion", "hyperframes", "blender"):
        raise SystemExit(f"Motor: remotion, hyperframes ya da blender (verilen: {motor})")
    cizer = o.get("cizer") if isinstance(o.get("cizer"), str) else None   # Blender'ın çizeri; yoksa cycles (alan yazılmaz)
    if cizer and (motor != "blender" or cizer not in __import__("blender").CIZERLER):
        raise SystemExit(f"--cizer yalnız Blender'da: cycles ya da eevee (verilen: {cizer}, motor {motor})")
    marka = o.get("marka")
    if marka and not (O.ROOT / "markalar" / marka / "marka.json").exists():
        raise SystemExit(f"Marka kiti yok: markalar/{marka}/marka.json (mevcut: {', '.join(p.name for p in (O.ROOT / 'markalar').iterdir() if (p / 'marka.json').exists())})")
    dil = o.get("dil", "tr")
    altyazi = o.get("altyazi") if isinstance(o.get("altyazi"), str) else "klasik"
    if altyazi not in ("klasik", "niyetli"):
        raise SystemExit(f"--altyazi: klasik ya da niyetli (verilen: {altyazi})")
    ek = {"motor": motor, "dil": dil, **({"hyperframes": __import__("hf").SURUM} if motor == "hyperframes" else {}),
          **({"blender": {"surum": __import__("blender").SURUM, **({"cizer": cizer} if cizer and cizer != "cycles" else {})}} if motor == "blender" else {}),
          **({"marka": marka} if marka else {})}
    sc = {**{k: v for k, v in sc.items() if k != "sentences"}, **ek, "sentences": sc["sentences"]}
    head = {k: v for k, v in sc.items() if k != "sentences"}
    if cesaret:  # eski filmlerde alan yok
        head["cesaret"] = cesaret
    if altyazi == "niyetli":  # yalnız seçilince (klasik: alan yok, components/Captions.tsx)
        head["altyazi"] = "niyetli"
    if aynen:  # bugünkü tek değerli şema: eski okuyucular (olc, üretim istemi) "katalog"u tarif sayar
        head["katalog"] = {t: aynen.get(t) for t in TURLER}
    if esin:
        head["esin"] = esin
    mk = o.get("muzik-kaynagi") if o.get("muzik-kaynagi") in ("kod", "ace") else None
    if kartlar["ses"]:  # aynen: kartın ayarı; esin: ilk kart başlangıç ön ayarıdır (ses.esin bütün kartlar)
        SS = _katalog_kayitlar("ses")[kartlar["ses"][0]]
        ses = dict(head["ses"])
        if ses.get("kaynak") == "edge":
            ses.update({k: SS["anlatim"][k] for k in ("rate", "pitch") if k in SS.get("anlatim", {})})
        ses.update({"stil": kartlar["ses"][0], "muzik_kaynagi": mk or "kod", **({"esin": kartlar["ses"]} if "ses" in esin else {})})
        head["ses"] = ses
    elif mk:  # ses kartı yok: müziği Claude ses.muzik_tarifi ile kurar; kaynak kullanıcının seçimi
        head["ses"] = {**head["ses"], "muzik_kaynagi": mk}
    sc = {**head, "sentences": sc["sentences"]}
    d.mkdir(parents=True)
    etiket = f"seri {seri}" if seri else "videoya özel (gorunus.json)"
    gj = f"../../stiller/{seri}/gorunus.json" if seri else f"../../videos/{vid}/gorunus.json"
    rep = {"{{ID}}": vid, "{{BASLIK}}": title, "{{COMP}}": comp, "{{TARIH}}": today(), "{{PROFIL}}": prof, "{{STIL}}": etiket,
           "{{GORUNUS}}": etiket, "{{GORUNUS_JSON}}": gj,
           "{{FORMATLAR}}": ", ".join(P["formatlar"]), "{{VURUSLAR}}": " → ".join(P["vuruslar"]),
           "{{CESARET}}": f"{CESARET[cesaret][0]} (kullanıcının seçimi): {CESARET[cesaret][1]}" if cesaret
                          else f"Cesur (varsayılan; kullanıcı seçmedi): {CESARET['cesur'][1]}",
           "{{TARIF}}": _tarif_satiri(meta)}
    skip = set()
    if not P.get("kaynak_zorunlu"):
        skip.add("kaynaklar.md")
    if not P.get("varlik_zorunlu") and not marka:
        skip.add("varliklar.md")
    if motor in ("hyperframes", "blender"):
        skip.add("Video.tsx.sablon")
    if seri:
        skip.add("gorunus.json")
    for src in SABLON.glob("video/*"):
        if src.name in skip:
            continue
        txt = src.read_text()
        for k, val in rep.items():
            txt = txt.replace(k, val)
        name = src.name.replace(".sablon", "")
        if name.endswith(".tsx") and altyazi == "niyetli":
            txt = _niyetli_sablon(txt)
        dst = (O.ROOT / "src" / vid / name) if name.endswith(".tsx") else d / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(txt)
    if motor == "blender":  # üst katman (Remotion): plaka + Bitis + yazı; sahne blender/<id>/sahne.py
        txt = (SABLON / "blender" / "Video.tsx.sablon").read_text()
        for k, val in rep.items():
            txt = txt.replace(k, val)
        (O.ROOT / "src" / vid).mkdir(parents=True, exist_ok=True)
        (O.ROOT / "src" / vid / "Video.tsx").write_text(_niyetli_sablon(txt) if altyazi == "niyetli" else txt)
    (d / "script.json").write_text(_dump_script(sc))
    if aynen.get("gorsel"):  # aynen: üç hazır varyasyon görünüş seçenekleri olur (Claude videoya göre inceltebilir, seçim kullanıcının)
        gp = d / "gorunus.json"
        G = json.loads(gp.read_text())
        G["katalog_stili"] = aynen["gorsel"]
        G["secenekler"] = _katalog_kayitlar("gorsel")[aynen["gorsel"]]["varyasyonlar"]
        gp.write_text(json.dumps(G, ensure_ascii=False, indent=2) + "\n")
    elif esin.get("gorsel"):  # esin: kartlar ham malzemedir; üç seçeneği Claude filme göre yazar (ayırt eşiği 3, videoya özel görünüş gibi)
        gp = d / "gorunus.json"
        G = json.loads(gp.read_text())
        G["esin_stilleri"] = esin["gorsel"]
        gp.write_text(json.dumps(G, ensure_ascii=False, indent=2) + "\n")
    pub = O.ROOT / "public" / vid
    (pub / "varliklar").mkdir(parents=True, exist_ok=True)
    if marka:  # resmi logolar videoya kopyalanır ve onaylı varlık olarak listelenir
        M = O.jload(O.ROOT / "markalar" / marka / "marka.json")
        (pub / "varliklar" / "marka").mkdir(exist_ok=True)
        satir = []
        for ad, yol in M.get("logolar", {}).items():
            shutil.copy2(O.ROOT / "markalar" / marka / yol, pub / "varliklar" / "marka" / Path(yol).name)
            satir.append(f"| {M['kisa']} logo ({ad}) | varliklar/marka/{Path(yol).name} | logo | resmi dosya: markalar/{marka}/{yol} | ✅ onaylı (marka kiti) |")
        vp = d / "varliklar.md"
        t = vp.read_text()
        t = re.sub(r"^\| \[ad\].*$", "\n".join(satir), t, count=1, flags=re.M) if re.search(r"^\| \[ad\]", t, re.M) else t.rstrip() + "\n" + "\n".join(satir) + "\n"
        vp.write_text(t)
    # Ses üretilene kadar Remotion paketi bozulmasın diye yer tutucu zaman çizelgesi
    (pub / "timeline.json").write_text(json.dumps({"id": vid, "title": title, "duration": 10, "sentences": []}, ensure_ascii=False))
    if motor == "blender":
        import blender
        blender.yeni(vid, title, P["formatlar"][0])
        blender.esitle(O.load(vid))  # public/<id>/plaka bağlantısı + plaka.json'ı (Video.tsx içe aktarır)
    gates_save(O.load(vid), {str(k): {"ad": n, "onay": None, "not": ""} for k, (n, _) in GATES.items()})
    if ip:  # basit mod: panelin yazdığı istek, ekli dosyalar ve referanslar videoya taşınır
        if ip.exists():
            shutil.move(str(ip), d / "istek.md")
            meta_yol = ip.with_suffix(".json")
            if meta_yol.exists():
                shutil.move(str(meta_yol), d / "claude.json")
            ekler = ip.with_name(ip.stem + "_dosyalar")
            if ekler.exists():
                for f in sorted(ekler.iterdir()):
                    shutil.move(str(f), pub / "varliklar" / f.name)
                    print(f"   ek dosya → public/{vid}/varliklar/{f.name} (varliklar.md'ye ekle)")
                ekler.rmdir()
            refler = ip.with_name(ip.stem + "_referanslar")  # referans: ölçülür, kopyalanmaz (varlık değil)
            if refler.exists():
                (d / "referanslar").mkdir(exist_ok=True)
                for f in sorted(refler.iterdir()):
                    shutil.move(str(f), d / "referanslar" / f.name)
                    print(f"   referans → videos/{vid}/referanslar/{f.name}")
                refler.rmdir()
    if altyazi == "niyetli" and (json.loads((d / "script.json").read_text()).get("ses") or {}).get("kaynak", "yok") == "yok":
        print("Not: niyetli altyazı anlatımdan ölçülür; bu profilin şablonunda anlatım yok. script.json → ses.kaynak "
              "(edge, magnific, kayit) ve cümleleri yaz, sonra ./st ses.")
    if motor == "hyperframes":
        import hf
        hf.yeni(vid, title, P["formatlar"][0], dil, niyetli=altyazi == "niyetli")
        print(f"Oluşturuldu: videos/{vid}/ · hf/{vid}/index.html (HyperFrames {hf.SURUM}) · profil {prof} · görünüş {etiket} · formatlar {', '.join(P['formatlar'])}"
              + (f" · marka {marka}" if marka else ""))
        print("Sıradaki: brief.md → " + ("" if seri else "gorunus.json (3 seçenek) → kanca karesi (hf/<id>/index.html) → ./st gorunus → kullanıcı seçer → ") +
              ("kaynaklar.md → " if P.get("kaynak_zorunlu") else "") + f"./st durum {vid}")
        return
    if motor == "blender":
        print(f"Blender {__import__('blender').SURUM} · çizer {cizer or 'cycles'}: sahne blender/{vid}/sahne.py (kit blender/kit/, kurallar blender/CLAUDE.md) · "
              f"üst katman src/{vid}/Video.tsx")
    root = O.ROOT / "src" / "Root.tsx"
    r = root.read_text()
    imp = f"import {{{comp}}} from './{vid}/Video';\nimport tl_{vid} from '../public/{vid}/timeline.json';\n"
    reg = ""
    for f in P["formatlar"]:
        F = O.FORMATLAR[f]
        cid = comp if len(P["formatlar"]) == 1 else f"{comp}-{f}"
        reg += (f"  <Composition id=\"{cid}\" component={{{comp}}} width={{{F['w']}}} height={{{F['h']}}} fps={{{sc['fps']}}} "
                f"durationInFrames={{Math.ceil(tl_{vid}.duration * {sc['fps']})}} />\n")
    r = r.replace("// @st:import\n", imp + "// @st:import\n").replace("  {/* @st:kompozisyon */}\n", reg + "  {/* @st:kompozisyon */}\n")
    root.write_text(r)
    print(f"Oluşturuldu: videos/{vid}/ · src/{vid}/Video.tsx · profil {prof} · görünüş {etiket} · formatlar {', '.join(P['formatlar'])}")
    print("Sıradaki: brief.md → " + ("" if seri else "gorunus.json (3 seçenek) → kanca karesi → ./st gorunus → kullanıcı seçer → ") +
          ("kaynaklar.md → " if P.get("kaynak_zorunlu") else "") +
          ("varliklar.md → " if P.get("varlik_zorunlu") else "") + f"./st durum {vid}")


def _niyetli_sablon(txt: str) -> str:
    """Remotion şablonunda ortak altyazının (Captions) yerine niyetli altyazı (src/lib/niyet; veri timeline.json → niyet)."""
    txt = txt.replace("import {Captions} from '../components/Captions';", "import {NiyetliAltyazi, NiyetVeri} from '../lib/niyet';")
    txt = re.sub(r"<Captions t=\{t\} [^\n]*/>",
                 "{/* niyetli altyazı: şiddet → ağırlık + boyut, perde → genişlik, konuşmacı → renk (./st niyet) */}\n"
                 "        <NiyetliAltyazi t={t} veri={(TL as {niyet?: NiyetVeri}).niyet} />", txt)
    if "<NiyetliAltyazi" not in txt:
        raise SystemExit("Şablonda <Captions …/> satırı bulunamadı (sablon/*/Video.tsx.sablon)")
    return txt


# ---------------------------------------------------------------- senaryo
def lint_rows(v):
    """Senaryo/çekim listesi denetimi (profil çıtalarıyla) → [(durum, mesaj)]."""
    out = []
    P = v.profil
    S = v.script.get("sentences", [])
    if not S:
        return [("❌", "script.json'da vuruş yok")]
    Y = v.script.get("yapi")
    if Y is not None:  # filmin kendi iskeleti: profilin vuruşları yalnız öneridir (ölçülebilir çıtalar aynen geçerli)
        if not (isinstance(Y, list) and 1 <= len(Y) <= 12 and all(isinstance(x, str) and x.strip() for x in Y) and len(set(Y)) == len(Y)):
            out.append(("❌", "script.json → yapi: sırayla 1–12 benzersiz vuruş adı olmalı (ör. [\"Tek an\", \"Kırılma\", \"Çağrı\"])"))
    V = v.vuruslar
    req = ["plan", "olay", "ses", "giris", "cikis", "amac"] + (["anahtar"] if v.anlatim else ["isaret"])
    for s in S:
        shot = s.get("shot", {})
        miss = [k for k in req if not str(shot.get(k, "")).strip() and not (k == "anahtar" and shot.get("isaret"))]
        if miss:
            out.append(("❌", f"{s['id']}: çekim alanları eksik: {', '.join(miss)}"))
        if not str(shot.get("gecis", "")).strip():
            out.append(("⚠️", f"{s['id']}: geçiş yazılmamış: nasıl çıkar, sonrakine ne taşınır, siyah ya da kesmeyse gerekçesi (zanaat.md §1, §3)"))
        if s.get("step") not in V:
            out.append(("❌", f"{s['id']}: vuruş “{s.get('step')}” " + (f"filmin yapısında yok (script.json → yapi: {' → '.join(V)})" if v.yapi
                                                                       else f"profilde yok ({' → '.join(V)})")))
        if v.anlatim:
            words = " ".join(p["text"] for p in s.get("parts", [])).split()
            if O.PLACEHOLDER.search(" ".join(words)):
                out.append(("❌", f"{s['id']}: metin doldurulmamış"))
            kw = shot.get("anahtar")
            if kw and O.norm_word(kw).lower() not in [O.norm_word(w).lower() for w in words]:
                out.append(("❌", f"{s['id']}: anahtar “{kw}” cümlede yok"))
            if "cumle_max" in P and len(words) > P["cumle_max"]:  # anlatımsız profilde (reklam-kisa, kisa-an) kısa anlatımın çıtası yok
                out.append(("❌", f"{s['id']}: {len(words)} kelime (en fazla {P['cumle_max']})"))
        else:
            if not (s.get("bas") and s.get("bit")):
                out.append(("❌", f"{s['id']}: bas/bit çapası yok"))
    if v.anlatim:
        hook = " ".join(p["text"] for p in S[0].get("parts", [])).split()
        if len(hook) > P.get("kanca_kelime", 99):
            out.append(("⚠️", f"kanca {len(hook)} kelime (≤ {P['kanca_kelime']} önerilir: {P['kanca_sn']:g} sn çıtası)"))
        n = sum(len(" ".join(p["text"] for p in s.get("parts", [])).split()) for s in S)
        if "cumle_ort" in P and n / len(S) > P["cumle_ort"]:
            out.append(("❌", f"ortalama cümle {n / len(S):.1f} kelime (çıta ≤ {P['cumle_ort']:g})"))
        lo, hi = P.get("toplam_kelime", (0, 10 ** 6))
        if not lo <= n <= hi:
            out.append(("⚠️", f"toplam {n} kelime (profil: {lo}–{hi})"))
    steps = [s["step"] for s in S]
    for st in V:
        if st not in steps:
            out.append(("❌", f"vuruş eksik: {st}"))
    if not v.script.get("learningGoal"):
        out.append(("⚠️", "learningGoal (izleyicinin aklında kalacak tek cümle) boş"))
    out += [("⚠️", f"ses.muzik_tarifi: {m}") for m in muzik_tarifi_sorunlari(v.ses.get("muzik_tarifi"))]
    import gecis
    out += gecis.sorunlar(v)  # yapılandırılmış geçiş (shot.gecis nesne): kütüphane, kare, pencere; öteki filmlerde satır yok
    import plaka
    out += plaka.sorunlar(v)  # karma film (script.json → sahneler): işaretler, motor, çakışma, sahne kodu; öteki filmlerde satır yok
    if v.cue_error:
        out.append(("❌", f"işaretler çözülemedi: {v.cue_error} (./st ses)"))
    elif v.cuefile and v.timeline and v.timeline.get("sentences"):
        for s in v.timeline["sentences"]:
            if not v.keyword_cue(s["id"]):
                out.append(("❌", f"{s['id']}: olay işareti yok (cues.json)"))
    return out or [("✅", "senaryo ve çekim listesi denetimden geçti")]


def cmd_lint(vid):
    for d, m in lint_rows(O.load(vid)):
        print(d, m)


def _gecis_metni(g) -> str:
    """Çekim listesinin geçiş hücresi: serbest metin aynen; yapılandırılmış geçiş (6a) "BookFlip · 18 kare · kesim <işaret> · gerekçe"."""
    if not isinstance(g, dict):
        return str(g or "")
    p = ", ".join(f"{k} {json.dumps(x, ensure_ascii=False)}" for k, x in (g.get("param") or {}).items())
    return " · ".join(x for x in (f"**{g.get('gl')}** (gölgelendirici)", f"{g.get('kare')} kare", p, f"kesim {g['kesim']}" if g.get("kesim") else "",
                                  str(g.get("neden") or "")) if x)


def cmd_cekim(vid):
    """Çekim listesi (sözleşme): her vuruşun giriş/çıkış durumu ve var olma sebebi."""
    v = O.load(vid)
    rows = ["| # | Vuruş | Zaman | Metin / olay | Anahtar / işaret | Plan | Giriş durumu → Çıkış durumu | Geçiş (sonrakine ne taşınır) | Görsel olay | Ses | Neden var? |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    import plaka
    karma = plaka.var_mi(v) and v.timeline and v.timeline.get("sentences")
    if karma:  # karma film (6b): vuruşu hangi motorun çizdiği (sahne pencereleri; brief → Yönetmenlik'teki sahne tablosuyla aynı)
        rows = [rows[0][:-1] + " Motor |", rows[1] + "---|"]
        SS = [S for S in plaka.sahneler(v) if not S["hata"]]
    for i, s in enumerate(v.script["sentences"], 1):
        sh = s.get("shot", {})
        tm = ""
        if v.timeline and v.timeline.get("sentences"):
            ts = v.sentence(s["id"])
            tm = f"{O.tc(ts['start'])}–{O.tc(ts['end'])}"
        text = " ".join(p["text"] for p in s["parts"]) if "parts" in s else "—"
        rows.append(f"| {i} | {s['step']} | {tm} | {text} | **{sh.get('anahtar') or sh.get('isaret', '')}** | {sh.get('plan', '')} | "
                    f"{sh.get('giris', '')} → {sh.get('cikis', '')} | {_gecis_metni(sh.get('gecis')) or '—'} | {sh.get('olay', '')} | {sh.get('ses', '')} | {sh.get('amac', '')} |")
        if karma:
            ts = v.sentence(s["id"])
            a, b = round(ts["start"] * v.fps), round(ts["end"] * v.fps)
            m = [f"{S['motor']} ({S['ad']})" for S in SS if S["bas_f"] < b and a < S["son_f"]]
            rows[-1] += f" {' + '.join(m) if m else 'remotion'} |"
    head = [f"# Çekim listesi — {v.script.get('title', vid)}", "",
            f"> Profil: {v.profil['ad']} · formatlar: {', '.join(v.formatlar)} · tek cümle: {v.script.get('learningGoal') or '—'}",
            "> Sözleşme: bir vuruşun neden var olduğu açıklanamıyorsa, o vuruş render'a girmez.", ""]
    (v.dir / "cekim-listesi.md").write_text("\n".join(head + rows) + "\n")
    print(f"yazıldı: videos/{vid}/cekim-listesi.md")


# ---------------------------------------------------------------- ses
def cmd_vurus(vid):
    v = O.load(vid)
    m = v.ses.get("muzik")
    if not m:
        raise SystemExit("script.json → ses.muzik yok (ör. \"muzik.wav\", dosya public/<id>/ altında)")
    run([PY, "-I", "pipeline/vurus.py", v.pub / m, v.pub / "vuruslar.json"])
    truth = v.pub / (Path(m).stem + "_izgara.json")
    if truth.exists():  # prosedürel müzikte gerçek ızgara bilinir: dedektörün doğruluğu ölçülür
        import numpy as np
        g, d = O.jload(truth), O.jload(v.pub / "vuruslar.json")
        G, D = np.array(g["beats"][:-1]), np.array(d["beats"])
        err = np.array([(D[np.argmin(abs(D - t))] - t) * 1000 for t in G])
        print(f"   doğrulama: gerçek {g['bpm']:g} BPM, tespit {d['bpm']} · ort {abs(err).mean():.1f} ms · en kötü {abs(err).max():.1f} ms "
              f"({abs(err).max() / 1000 * v.fps:.2f} kare)")


def _muzik_suresi(v):
    """Müziğin süresi: anlatım varsa zaman çizelgesi + 2 sn kuyruk, yoksa profilin üst sınırı."""
    if v.timeline and v.timeline.get("sentences"):
        return v.duration + 2.0
    return float(v.profil["sure"][1])


def _yapi_sureden(sure, bpm):
    per = 60 / bpm
    olcu = max(4, int(np.ceil(sure / (4 * per))))
    return f"giris:1,yukselis:1,ana:{olcu - 3},kapanis:1"


def muzik_tarifi_sorunlari(t) -> list[str]:
    """script.json → ses.muzik_tarifi şeması: {"kod": {"stil": <muzik_stiller ön ayarı>, "bpm": 96, "ton": "D"},
    "ace": {"caption": "<İngilizce kısa tarif>", "bpm": 96, "ton": "D minor", "tohum": 7}}; ikisinden biri yeter."""
    if t is None:
        return []
    if not isinstance(t, dict) or not (isinstance(t.get("kod"), dict) or isinstance(t.get("ace"), dict)):
        return ['"kod" ya da "ace" alanı olan bir nesne olmalı (README → Müzik tarifi)']
    import muzik_stiller as MS
    out, k, a = [], t.get("kod"), t.get("ace")
    sayi = lambda x, lo, hi: isinstance(x, (int, float)) and not isinstance(x, bool) and lo <= x <= hi  # noqa: E731
    if k is not None:
        if not isinstance(k, dict) or k.get("stil") not in MS.ON_AYARLAR:
            out.append(f"kod.stil ön ayarlardan biri olmalı ({', '.join(MS.ON_AYARLAR)})")
        elif "bpm" in k and not sayi(k["bpm"], 40, 220):
            out.append("kod.bpm 40–220 arası bir sayı olmalı")
        elif "ton" in k and str(k["ton"]) not in MS.M.NOTE:
            out.append(f"kod.ton nota adı olmalı ({', '.join(MS.M.NOTE)})")
    if a is not None:
        if not isinstance(a, dict) or not str(a.get("caption") or "").strip():
            out.append("ace.caption gerekli (İngilizce kısa tarif: tür, çalgılar, duygu)")
        elif "bpm" in a and not sayi(a["bpm"], 40, 220):
            out.append("ace.bpm 40–220 arası bir sayı olmalı")
        elif "tohum" in a and not (isinstance(a["tohum"], int) and not isinstance(a["tohum"], bool)):
            out.append("ace.tohum tam sayı olmalı")
    return out


def cmd_muzik(vid, *args):
    """Müzik. Öncelik: --stil > script.json → ses.muzik_tarifi (filme özel tarif: kod ön ayarı ya da ACE-Step caption'ı) > ses.stil
    (katalog ses stili) > eski geçici müzik (prosedürel elektronik). Kaynak "kod" (prosedürel ön ayar) ya da "ace" (ACE-Step 1.5, yerel
    yapay zekâ; ses.muzik_notu tarifi zenginleştirir, ses.muzik_referans örnek alınacak parça)."""
    _, o = opts(args, "bpm", "yapi", "ton", "kuyruk", "kaynak", "stil")
    v = O.load(vid)
    # tarif (T) kaynak başına önce gelir; katalog ses stili (SS) tarifte o kaynağın alanı yoksa yedektir
    T, stil = (None, o["stil"]) if o.get("stil") else (v.ses.get("muzik_tarifi"), v.ses.get("stil"))
    SS = _katalog_kayitlar("ses").get(stil) if stil else None
    if stil and not SS:
        raise SystemExit(f"Ses stili yok: {stil} (./st katalog)")
    sorun = muzik_tarifi_sorunlari(T)
    if sorun:
        raise SystemExit("ses.muzik_tarifi: " + "; ".join(sorun))
    kaynak = o.get("kaynak") or v.ses.get("muzik_kaynagi") or "kod"
    hedef = v.pub / "muzik.wav"
    if kaynak == "ace":
        a = (T or {}).get("ace") or (SS or {}).get("muzik", {}).get("ace")
        if not a:
            raise SystemExit("ACE-Step için ses.muzik_tarifi.ace ya da ses stili gerekli (script.json → ses; ya da --stil)")
        ref = v.ses.get("muzik_referans")
        is_ = {"cikti": str(hedef), "caption": a["caption"] + (", " + v.ses["muzik_notu"] if v.ses.get("muzik_notu") else ""),
               "bpm": int(float(o.get("bpm") or a.get("bpm") or 100)), "sure": round(min(600.0, max(10.0, _muzik_suresi(v))), 1),
               "ton": o.get("ton") or a.get("ton", ""), "tohum": int(v.ses.get("muzik_tohum", a.get("tohum", 42)))}
        if ref:
            is_["referans"] = str(v.pub / ref)
        ace_uret([is_])
        (v.pub / "muzik_izgara.json").unlink(missing_ok=True)  # gerçek parçanın ızgarası vurus.py ile çıkar
        print(f"ACE-Step müziği: {hedef.relative_to(O.ROOT)} · {is_['sure']} sn · {is_['bpm']} BPM · tohum {is_['tohum']}")
    else:
        cmd = [PY, "-I", "pipeline/muzik.py", hedef]
        k = (T or {}).get("kod") or (SS or {}).get("muzik", {}).get("kod")
        if k:
            bpm = float(o.get("bpm") or k.get("bpm") or 100)
            cmd += ["--stil", k["stil"], "--bpm", str(bpm), "--ton", o.get("ton") or k.get("ton", "A"), "--yapi", o.get("yapi") or _yapi_sureden(_muzik_suresi(v), bpm)]
            if "kuyruk" in o:
                cmd += ["--kuyruk", o["kuyruk"]]
        else:
            if T:
                print("ses.muzik_tarifi'nde kod alanı yok: geçici prosedürel müzik (filme göre ses.muzik_tarifi.kod yaz)")
            for k in ("bpm", "yapi", "ton", "kuyruk"):
                if k in o:
                    cmd += [f"--{k}", o[k]]
        run(cmd)
    if not v.ses.get("muzik"):
        p = v.dir / "script.json"
        sc = json.loads(p.read_text())
        sc.setdefault("ses", {})["muzik"] = "muzik.wav"
        p.write_text(_dump_script(sc))
        print("script.json → ses.muzik = muzik.wav")


def cmd_ses(vid):
    v = O.load(vid)
    if v.ses.get("kaynak") == "magnific":  # Magnific anlatıcısı: parçalar Claude'un MCP üretimiyle dondurulmuş olmalı (pipeline/tts.py)
        import uretim
        A = uretim.anlatim_durumu(v)
        if A["eksik"]:
            raise SystemExit(f"Magnific anlatımı eksik: {len(A['eksik'])}/{len(A['parcalar'])} parça ({sum(len(p['metin']) for p in A['eksik'])} karakter). "
                             f"Claude üretir: ./st uret anlatim {vid} (audio_tts → ./st uret al … --tur anlatim), sonra yeniden ./st ses {vid}. "
                             "Panelden: Claude'a “Anlatımı Magnific sesiyle üret” de.")
    if v.ses.get("muzik"):
        cmd_vurus(vid)
    run([PY, "-I", "pipeline/tts.py", f"videos/{vid}/script.json"])
    if v.niyetli:  # anlatım yeni: kelime başına şiddet ve perde yeniden ölçülür (timeline.json → niyet)
        run([PY, "-I", "pipeline/niyet.py", vid])
    run([PY, "-I", "pipeline/sfx.py", vid])
    cmd_cekim(vid)


def cmd_niyet(vid):
    run([PY, "-I", "pipeline/niyet.py", vid])


def cmd_zaman(vid):
    run([PY, "-I", "pipeline/check_timing.py", vid])


def cmd_ses_dene(kaynak="edge", *metin):
    """Ses kaynağını kısa bir cümleyle dener → out/ses_deneme/<kaynak>.wav"""
    sys.path.insert(0, str(O.ROOT / "pipeline"))
    import asyncio
    import tts
    text = " ".join(metin) or "Bir olay, bir harita ve tek bir ders."
    out = O.ROOT / "out" / "ses_deneme"
    out.mkdir(parents=True, exist_ok=True)
    script = {"id": "_ses_deneme", "title": "deneme", "leadIn": 0.1, "tail": 0.3,
              "ses": {"kaynak": kaynak, "voice": "tr-TR-EmelNeural" if kaynak == "edge" else "Kore", "rate": "+8%", "pitch": "-2Hz"},
              "sentences": [{"id": "s1", "step": "Kanca", "pauseAfter": 0.0, "parts": [{"text": text}]}]}
    y, sents = asyncio.run(tts.synth_parts(script, out))
    wav = out / f"{kaynak}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(tts.SR), "-ac", "1", "-i", "-", str(wav)],
                   input=y.astype("<f4").tobytes(), check=True)
    print(f"✅ {kaynak}: {len(y) / tts.SR:.2f} sn → {wav.relative_to(O.ROOT)}")
    print("   " + " ".join(f"{w['text']}@{w['start']:.2f}" for w in sents[0]["words"]))


# ---------------------------------------------------------------- görüntü
def cmd_kare(vid, *args):
    """Belirli anların kareleri (4.5s saniye, 120 kare numarası) → son inceleme kareleri klasörü; --cikti <klasör>: oraya (ör. izleyici raporunun kareleri)."""
    pos, o = opts(args, "format", "kalite", "cikti")
    v = O.load(vid)
    ek = {"kalite": o["kalite"]} if v.motor == "blender" and o.get("kalite") else None  # Blender: taslak (varsayılan) | tam
    for fmt in fmts(v, o):
        out = v.dir / "inceleme" / review_names(v, fmt)[1]
        if o.get("cikti"):
            out = (Path(o["cikti"]) if Path(o["cikti"]).is_absolute() else O.ROOT / o["cikti"]) / (fmt if len(v.formatlar) > 1 else "")
        files = render_frames(v, parse_times(pos, v.fps), out, fmt, props=ek)
        for f, p in sorted(files.items()):
            print(f"   f{f} ({O.tc(f / v.fps)}) → {p.relative_to(O.ROOT) if p.is_relative_to(O.ROOT) else p}")


def cmd_temsili(vid, *args):
    """Kapı 3: her vuruş türünden bir kare (olay işareti + 3 kare). Hepsini render etmeden önce görünüşü onayla."""
    import kontak as K
    _, o = opts(args, "format")
    v = O.load(vid)
    picks = {}
    for s in v.timeline["sentences"]:
        if s["step"] in picks:
            continue
        kc = v.keyword_cue(s["id"])
        t = kc[1] if kc else (s["start"] + s["end"]) / 2
        picks[s["step"]] = (min(v.nframes - 1, round(t * v.fps) + 3), s["id"])
    out = v.dir / "inceleme" / "temsili"
    ek = {"kalite": "tam"} if v.motor == "blender" else None  # temsilî kareler görünüşü onaylatır: teslim kalitesinde plaka
    for fmt in fmts(v, o):
        _, kdir, tname = review_names(v, fmt)
        files = render_frames(v, [f for f, _ in picks.values()], out / kdir, fmt, props=ek)
        cells = [{"frame": f, "title": st.upper(), "step": st, "sid": sid, "note": ""} for st, (f, sid) in picks.items()]
        K.build(v, files, cells, [], out / tname, f"temsilî kareler · {fmt} · {today()}", fmt=fmt)
        print(f"yazıldı: {(out / tname).relative_to(O.ROOT)}")


def cmd_render(vid, *args):
    _, o = opts(args, "format")
    v = O.load(vid)
    (O.ROOT / "out").mkdir(exist_ok=True)
    if not o.get("final"):
        for fmt in fmts(v, o):
            dst = rough_path(v, fmt)
            if v.motor == "hyperframes":
                import hf
                hf.esitle(v)
                hf.video(v, fmt, dst)
            elif v.motor == "blender":
                import blender
                _gecis_hazir(v, fmt)
                blender.video(v, fmt, dst)
            else:
                ek = _plaka_gecis_hazir(v, fmt, final=False)
                run(["npx", "remotion", "render", "src/index.ts", v.comp_for(fmt), dst, "--codec=h264", "--crf=26", "--scale=0.5", "--log=error",
                     *O.gl_bayraklari(v.gl), *(["--props", json.dumps(ek, ensure_ascii=False)] if ek is not None else _props_bayragi(v))])
            print(f"kaba kurgu [{fmt}]: {dst.relative_to(O.ROOT)}")
        return
    import olc
    CIKTI.mkdir(exist_ok=True)
    renders, n = {}, 0
    for fmt in fmts(v, o):
        vs = final_versions(v, fmt)
        n = int(re.search(r"_v(\d+)\.mp4$", vs[-1].name).group(1)) + 1 if vs else 1
        name = f"{v.id}{v.suffix(fmt)}_v{n}"
        tmp = O.ROOT / "out" / f"{name}.mp4"
        if v.motor == "hyperframes":
            import hf
            hf.esitle(v)
            hf.video(v, fmt, tmp, final=True)
        elif v.motor == "blender":
            import blender
            _gecis_hazir(v, fmt)
            blender.video(v, fmt, tmp, final=True)
        else:
            ek = _plaka_gecis_hazir(v, fmt, final=True)
            run(["npx", "remotion", "render", "src/index.ts", v.comp_for(fmt), tmp, "--codec=h264", "--crf=17", "--audio-bitrate=320k", "--log=error",
                 *O.gl_bayraklari(v.gl), *(["--props", json.dumps(ek, ensure_ascii=False)] if ek is not None else _props_bayragi(v))])
        shutil.copy2(tmp, CIKTI / tmp.name)
        renders[fmt] = CIKTI / tmp.name
        pf = round(v.cues["poster"] * v.fps) if "poster" in v.cues else v.nframes - 1
        files = render_frames(v, [pf], O.ROOT / "out" / "poster" / fmt, fmt, props={"kalite": "tam"} if v.motor == "blender" else None)
        shutil.copy2(files[pf], CIKTI / f"{name}_poster.png")
    if v.cover and v.motor == "remotion":
        run(["npx", "remotion", "still", "src/index.ts", v.cover, CIKTI / f"{v.id}_kapak.png", "--log=error", *O.gl_bayraklari(v.gl), *_props_bayragi(v)])
    rows, _ = olc.measure(v, renders, teslim=True)
    rd = O.latest_review_dir(v) or O.next_review_dir(v)
    olc.write(v, rows, rd / f"teslim_v{n}", f"teslim v{n}")
    for fmt, p in renders.items():
        print(f"teslim [{fmt}]: {p.relative_to(O.KANAL)}")
    print(f"ölçüm: {(rd / f'teslim_v{n}' / 'olcum.md').relative_to(O.ROOT)}")


def _gecis_hazir(v, fmt, props=None):
    """npx remotion render'dan önce: geçişli filmde bütün pencerelerin plakaları (önbellekte yoksa çizilir) ve varsayılan küme (gecis.json)
    → girdi (gecisKume dahil) ya da geçişsiz filmde None."""
    import gecis
    if gecis.var_mi(v):
        return gecis.hazirla(v, [f for fr in gecis.pencere_kareleri(v).values() for f in fr], fmt, props if props is not None else _veri_props(v))
    return None


def _plaka_gecis_hazir(v, fmt, final=False):
    """Kaba kurgu ve teslimden önce: karma filmde bütün sahnelerin plakaları (kaba: taslak, teslim: tam) + geçiş plakaları → npx remotion render'ın
    girdisi; ikisi de yoksa None (öteki filmler eskisi gibi _props_bayragi)."""
    import plaka
    props = None
    if plaka.var_mi(v):
        props = plaka.hazirla(v, plaka.tum_kareler(v), fmt, {**(_veri_props(v) or {}), "kalite": "tam" if final else "taslak"})
    g = _gecis_hazir(v, fmt, props)
    return g if g is not None else props


def _fresh_rough(v, fmt):
    mp4 = rough_path(v, fmt)
    import gecis
    if gecis.var_mi(v):
        gecis.esitle(v)
    if v.motor == "hyperframes":
        import hf
        kod = hf.kaynaklar(v) + [p for p in (v.dir / "gorunus.json",) if p.exists()]
    elif v.motor == "blender":  # sahne + kit + üst katman + görünüş (plakalar parmak iziyle bunlardan türer)
        import blender
        kod = blender.kaynaklar(v) + list((O.ROOT / "src").rglob("*.ts*")) + [p for p in (v.dir / "gorunus.json",) if p.exists()]
    else:
        kod = list((O.ROOT / "src").rglob("*.ts*"))
    deps = kod + [p for p in (v.pub / "mix.wav", v.pub / "timeline.json", v.dir / "cues.json", v.pub / "veri" / "anlik.json") if p.exists()]
    if gecis.var_mi(v):  # kesimlerin tanımı (script.json → shot.gecis): yalnız geçişli filmde
        deps += [p for p in (v.pub / "gecis.json", v.dir / "script.json") if p.exists()]
    import plaka
    if plaka.var_mi(v):  # karma film: sahnelerin kodu ve motor kitleri
        deps += plaka.kaynaklar(v)
    if not mp4.exists() or mp4.stat().st_mtime < max(p.stat().st_mtime for p in deps):
        print(f"kaba kurgu [{fmt}] yok ya da kaynaktan/sesten eski → yeniden render")
        cmd_render(v.id, "--format", fmt)
    return mp4


def cmd_inceleme(vid, *args):
    """Kapı 4: her format için kontak tabakası + ortak ölçüm + inceleme şablonu → inceleme/vN/"""
    import kontak as K
    import olc
    _, o = opts(args, "format")
    v = O.load(vid)
    rd = O.next_review_dir(v)
    label = f"{rd.name} · {today()}"
    renders, frames_dir = {}, None
    for fmt in fmts(v, o):
        mp4 = _fresh_rough(v, fmt)
        renders[fmt] = mp4
        F = O.FORMATLAR[fmt]
        motion = O.motion_curve(mp4, *O.motion_size(F["w"], F["h"]), fps=v.fps)
        cells, strips = K.select(v, motion)
        kname, kdir, _ = review_names(v, fmt)
        files = render_frames(v, K.all_frames(cells, strips), rd / kdir, fmt)
        K.build(v, files, cells, strips, rd / kname, f"{label} · {fmt}", motion=motion, fmt=fmt)
        frames_dir = frames_dir or rd / kdir
    rows, _ = olc.measure(v, renders, frames_dir)
    olc.write(v, rows, rd, label)
    t = (SABLON / "inceleme.md").read_text().replace("{{ID}}", vid).replace("{{SURUM}}", rd.name).replace("{{TARIH}}", today())
    (rd / "inceleme.md").write_text(t)
    print(f"\nkanıt: {rd.relative_to(O.ROOT)}/ → " + ", ".join(review_names(v, f)[0] for f in renders) + " · olcum.md")
    print((rd / "olcum.md").read_text())
    print(f"Sıradaki: kontak tabakalarına ve olcum.md'ye bakarak {rd.relative_to(O.ROOT)}/inceleme.md'yi doldur (en büyük 3 kusur).")


def cmd_olc(vid):
    import olc
    v = O.load(vid)
    rd = O.latest_review_dir(v) or O.next_review_dir(v)
    renders = {f: rough_path(v, f) for f in v.formatlar if rough_path(v, f).exists()}
    kdir = rd / review_names(v, v.formatlar[0])[1]
    rows, _ = olc.measure(v, renders, kdir if kdir.exists() else None)
    olc.write(v, rows, rd, f"{rd.name} · {today()}")
    print((rd / "olcum.md").read_text())


def _kare_farki(a: bytes, b: bytes, v) -> str:
    """İki PNG karşılaştırması (yol seçildikten sonra kanca karesi değişti mi): bayt bayt, değilse en büyük piksel farkı.
    Blender bayt bayt aynı çizmez: çizerin toleransı içindeyse aynı sayılır (1/255 sayılmaz, > 1/255 ≤ %0,01 piksel, en büyük ≤ 8/255; CLAUDE.md kural 8)."""
    if a == b:
        return "✅ değişmedi (bayt bayt aynı)"
    import io
    from PIL import Image
    x, y = (np.asarray(Image.open(io.BytesIO(p)).convert("RGB"), dtype=np.int16) for p in (a, b))
    if x.shape != y.shape:
        return f"⚠️ değişti (boyut {x.shape[1]}×{x.shape[0]} → {y.shape[1]}×{y.shape[0]})"
    d = np.abs(x - y).max(axis=2)
    T = __import__("blender").tolerans(v) if v.motor == "blender" else None
    en, oran = int(d.max()), float((d > (T or {}).get("esik", 0)).mean())
    tolerans = T is not None and en <= T["en_buyuk"] and oran <= T["oran"]
    return (f"{'✅ aynı (Blender toleransında)' if tolerans else '⚠️ değişti'}: en büyük fark {en}/255, "
            f"farklı piksel %{oran * 100:.2f}" + ("" if tolerans else " (seçilmeyen dallar temizlenirken seçilen yolun sahnesi değiştiyse geri al)"))


def cmd_gorunus(vid, *args):
    """Görünüş denemesi (Kapı 1): seçenekleri doğrula, karşılaştır, kanca karesinde çiz. `sec <harf>` seçimi kaydeder."""
    import gorunus as GR
    pos, o = opts(args, "format")
    v = O.load(vid)
    if v.gorunus_modu != "video":
        raise SystemExit(f"{vid} paylaşılan görünüş kullanıyor ({v.gorunus_etiketi}); deneme ve seçim yalnız videoya özel görünüşte.")
    gp = v.dir / "gorunus.json"
    G = O.jload(gp)
    S = G.get("secenekler") or {}
    if pos and pos[0] == "sec":
        k = (pos[1] if len(pos) > 1 else "").lower()
        if k not in S:
            raise SystemExit(f"Seçenek yok: {k or '—'} (var: {', '.join(sorted(S)) or 'hiçbiri'})")
        G["secim"] = k
        gp.write_text(json.dumps(G, ensure_ascii=False, indent=2) + "\n")
        y = S[k].get("yol") if G.get("yol_modu") else None
        print(f"✅ yol seçildi: {k.upper()} · {y.get('ad', '')} (görünüş {S[k].get('ad', '')}). Sıradaki: planı bu yolda tamamla "
              "(brief → Yönetmenlik, senaryo, ./st lint; seçilmeyen yolların kanca dalları temizlenir; panel bunu Claude'a kendiliğinden verir)"
              if isinstance(y, dict) else f"✅ görünüş seçildi: {k.upper()} · {S[k].get('ad', '')}")
        return
    if len(S) < 3:
        raise SystemExit(f"gorunus.json'da {len(S)} seçenek var; birbirinden belirgin farklı 3 seçenek yaz (a, b, c; zanaat.md §1c).")
    F = GR.fontlar()
    D = GR.dogrula(S, F)
    for k, rows in GR.yol_dogrula(S, bool(G.get("yol_modu"))).items():  # yol bloğu (2a): zorunlu alanlar, üç yolun yöntemi farklı
        D[k] += rows
    A = GR.ayirt(S, F, 2 if G.get("katalog_stili") else 3)  # aynı katalog stilinin varyasyonları en az 2 eksende ayrışır
    onc = GR.onceki(v, S)
    bozuk = [k for k, rows in D.items() if any(d == "❌" for d, _ in rows)]
    if bozuk:
        for k in bozuk:
            print(f"❌ {k.upper()}: " + "; ".join(m for d, m in D[k] if d == "❌"))
        raise SystemExit("Bozuk seçenek çizilmez: gorunus.json'u düzelt.")
    # Yol seçildiyse yalnız seçilen yol yeniden çizilir: öteki yolların kareleri önerildikleri anın kaydıdır (seçilmeyen dallar
    # kodda temizlenince yeniden çizilirlerse seçilen yolun sahnesini başka renkte gösterirlerdi). --hepsi: üçünü de çiz.
    secili = G.get("secim") if G.get("yol_modu") and G.get("secim") in S and not o.get("hepsi") else None
    t = G.get("deneme_kare")
    if isinstance(t, str):
        if t not in v.cues:
            raise SystemExit(f"deneme_kare işareti yok: {t}")
        t = v.cues[t]
    frame = min(v.nframes - 1, round((1.0 if t is None else float(t)) * v.fps))
    out = v.dir / "inceleme" / "gorunus"
    tabakalar, notlu = {}, set()
    for fmt in fmts(v, o):
        eski = {k: sorted((out / f"{k}-{fmt}").glob("f*.png"), key=lambda x: x.stat().st_mtime) for k in S}  # en yenisi sonda
        keys = [k for k in sorted(S) if not secili or k == secili or not eski[k]]
        once = eski[secili][-1].read_bytes() if secili and eski[secili] else None
        if v.motor in ("hyperframes", "blender"):  # Blender: her seçenek kendi renkleriyle ayrı plaka kümesi (taslak)
            res = [render_frames(v, [frame], out / f"{k}-{fmt}", fmt, props={"gorunus": k}) for k in keys]
        else:
            res = render_jobs([{"comp": v.comp_for(fmt), "out": out / f"{k}-{fmt}", "frames": [frame], "props": _veri_props(v, {"gorunus": k}),
                                **({"gl": v.gl} if v.gl else {})} for k in keys])
        kareler = {**{k: eski[k][-1] for k in S if k not in keys}, **{k: r[frame] for k, r in zip(keys, res)}}
        if secili:
            print(f"[{fmt}] yol {secili.upper()} seçili: yalnız o yeniden çizildi; öteki yolların kareleri önerildikleri anın kaydı (--hepsi: hepsini çiz)")
            if once is not None:
                print(f"   seçilen yolun kanca karesi: {_kare_farki(once, Path(kareler[secili]).read_bytes(), v)}")
        if G.get("yol_modu"):  # 2b: yolun kanca karesi bir önceki filme ya da katalog kartına çok mu benziyor; yöntemi önceki yollu filmde de mi var
            import benzerlik
            oy = benzerlik.onceki_yontem(v)
            for k in [k for k in sorted(S) if k not in notlu]:
                notlu.add(k)
                E, _ = benzerlik.en_yakin(v, [Path(kareler[k])], n=1)
                if E and E[0]["skor"] >= benzerlik.ESIK and not E[0]["beklenen"]:
                    D[k].append(("⚠️", f"kanca karesi {E[0]['yonelme']} çok benziyor ({E[0]['skor']:.2f})"))
                y = " ".join(O.norm_word(str((S[k].get("yol") or {}).get("yontem") or "")).lower().split())
                if oy and y and y == oy[1]:
                    D[k].append(("⚠️", f"yöntem önceki yollu filmde ({oy[0]}) de kullanıldı: art arda iki filmde aynı yöntem"))
        tp = out / f"gorunusler-{fmt}.png"
        GR.tabaka(v, fmt, kareler, S, D, A, onc, frame, tp)
        tabakalar[fmt] = tp
        print(f"yazıldı: {tp.relative_to(O.ROOT)}")
    (out / "gorunus.md").write_text(GR.rapor_md(v, S, D, A, onc, frame, tabakalar))
    for k in sorted(S):
        notlar = [m for _, m in D[k]] + [f"{vid_} videosuna benziyor ({', '.join(m)})" for vid_, m in onc.get(k, [])]
        y = S[k].get("yol") if isinstance(S[k].get("yol"), dict) and G.get("yol_modu") else None
        print(f"  {k.upper()} · " + (f"yol “{y.get('ad', '')}” ({y.get('yontem', '')}) · görünüş " if y else "") + f"{S[k].get('ad', '')}: "
              + ("; ".join(notlar) if notlar else "temiz"))
    for a in A:
        print(f"  ⚠️ {a}")
    print(f"Seçim kullanıcının: panelde ya da ./st gorunus {vid} sec <harf>. Mevcut seçim: {G.get('secim') or 'yok'}")


def cmd_seri(vid, ad):
    """Videonun seçilmiş görünüşünü paylaşılan bir seri yapar: stiller/<ad>/gorunus.json + stil-rehberi.md."""
    v = O.load(vid)
    o = v.gorunus_secimi
    if v.gorunus_modu != "video" or not o:
        raise SystemExit(f"{vid}: seçilmiş videoya özel görünüş yok ({v.gorunus_etiketi})")
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,30}", ad):
        raise SystemExit("Seri adı küçük harf, rakam ve tire olmalı (ör. gece-yolu)")
    d = O.ROOT / "stiller" / ad
    if d.exists():
        raise SystemExit(f"Zaten var: stiller/{ad}")
    d.mkdir(parents=True)
    (d / "gorunus.json").write_text(json.dumps({"_doc": f"Seri görünüşü: {vid} videosundan ({today()}). Yeni video: ./st yeni <id> --seri {ad}.",
                                                 "secim": ad, "secenekler": {ad: o}}, ensure_ascii=False, indent=2) + "\n")
    R, Y = o["renk"], o["yazi"]
    L = [f"# Seri: {o.get('ad', ad)} ({today()})", "",
         f"> {o.get('fikir', '')} İlk video: `{vid}`. Değer kaynağı: `gorunus.json` (bu dosya özettir).",
         "> **Değişiklik kuralı:** seri görünüşü değişirse onu kullanan bütün videolar değişir; yalnız kullanıcı kararıyla ve `kanal/ogrenimler.md`'de kanıtla.", "",
         "## Palet", "| Rol | Hex |", "|---|---|"] + [f"| {k} | `{h}` |" for k, h in R.items()] + [
         "", "## Yazı", "| Rol | Aile · ağırlık |", "|---|---|"] + [f"| {k} | {y['aile']} {y['agirlik']}{' italik' if y.get('italik') else ''} |" for k, y in Y.items()] + [
         "", "## Doku · ışık · hareket", f"- Doku: {o.get('doku', '—')}", f"- Işık: {o.get('isik', '—')}", f"- Hareket: {o.get('hareket', '—')}",
         "", "## Kaçınılacaklar (bu seriye özgü)"] + [f"- {y}" for y in o.get("yasak", [])] + ["- Genel uyarılar: `../../zanaat.md` §8"]
    (d / "stil-rehberi.md").write_text("\n".join(L) + "\n")
    sp = v.dir / "script.json"
    sc = json.loads(sp.read_text())
    sc["seri"] = ad  # çeşitlilik denetimi bu videoyu serinin öteki videolarıyla karşılaştırmaz
    sp.write_text(_dump_script(sc))
    print(f"✅ seri oluşturuldu: stiller/{ad}/ · yeni videolar: ./st yeni <id> --seri {ad}")


KATALOG = O.ROOT / "katalog"
TURLER = ("gorsel", "animasyon", "ses")


def _katalog_kayitlar(tur):
    return {p.stem: O.jload(p) for p in sorted((KATALOG / tur).glob("*.json"))}


def _katalog_index_ts():
    """src/katalog/gorseller.gen.ts: katalog görüntü stillerinin JSON'larını Remotion paketine bağlar (elle düzenlenmez)."""
    G = _katalog_kayitlar("gorsel")
    ad = lambda k: "g_" + re.sub(r"[^a-z0-9]", "_", k)
    L = ["// ./st katalog üretir: elle düzenleme. Katalog görüntü stilleri (katalog/gorsel/*.json).",
         "import {Secenek} from '../lib/gorunus';"]
    L += [f"import {ad(k)} from '../../katalog/gorsel/{k}.json';" for k in G]
    L += ["", "export type KatalogGorselKaydi = {ad: string; baslik: string; ozet: string; varyasyonlar: Record<string, Secenek>};",
          "export const GORSELLER = {"] + [f"  '{k}': {ad(k)}," for k in G] + ["} as unknown as Record<string, KatalogGorselKaydi>;"]
    f = O.ROOT / "src" / "katalog" / "gorseller.gen.ts"
    yeni = "\n".join(L) + "\n"
    if not f.exists() or f.read_text() != yeni:
        f.write_text(yeni)


def _katalog_gorsel(adlar, yeniden):
    import gorunus as GR
    from PIL import Image, ImageDraw
    import kontak as K
    G = _katalog_kayitlar("gorsel")
    F = GR.fontlar()
    out = KATALOG / "onizleme" / "gorsel"
    out.mkdir(parents=True, exist_ok=True)
    isler, hedef = [], []
    adlar = [a for a in (adlar or G) if a in G]
    for ad in adlar:
        V = G[ad]["varyasyonlar"]
        D = GR.dogrula(V, F)
        bozuk = {k: [m for d, m in r if d == "❌"] for k, r in D.items() if any(d == "❌" for d, _ in r)}
        if bozuk:
            print(f"❌ {ad}: {bozuk}")
            continue
        if G[ad].get("onizleme_motoru") == "blender" and G[ad].get("onizleme_sahne"):  # önizlemesi Blender sahnesiyle çizilen stil (kil-maket)
            import blender
            eksik = {k: out / f"{ad}-{k}.png" for k in sorted(V) if yeniden or not (out / f"{ad}-{k}.png").exists()}
            if eksik:
                blender.katalog_kareler(O.ROOT / G[ad]["onizleme_sahne"], {k: V[k] for k in eksik}, int(G[ad].get("onizleme_kare", 45)), eksik)
            continue
        for k in sorted(V):
            png = out / f"{ad}-{k}.png"
            if yeniden or not png.exists():
                isler.append({"comp": "KatalogGorsel", "out": out / "_kare" / f"{ad}-{k}", "frames": [0], "props": {"stil": ad, "varyasyon": k}})
                hedef.append(png)
    if isler:
        for png, r in zip(hedef, render_jobs(isler)):
            Image.open(r[0]).convert("RGB").resize((540, 540)).save(png)
        shutil.rmtree(out / "_kare", ignore_errors=True)
    for ad in adlar:  # kart görseli: üç varyasyon yan yana
        V = G[ad]["varyasyonlar"]
        kart = Image.new("RGB", (3 * 360 + 4 * 12, 360 + 24 + 40), (24, 22, 20))
        d = ImageDraw.Draw(kart)
        for i, k in enumerate(sorted(V)):
            png = out / f"{ad}-{k}.png"
            if png.exists():
                kart.paste(Image.open(png).resize((360, 360)), (12 + i * 372, 12))
            d.text((12 + i * 372, 380), f"{k.upper()} · {V[k].get('ad', '')}", font=K.font(17, True), fill=(236, 232, 224))
        kart.save(out / f"{ad}.png")
    print(f"görüntü stilleri: {len(adlar)} stil, {len(isler)} yeni kare → {out.relative_to(O.ROOT)}")


def _katalog_indeks():
    """Panelin okuduğu özet: katalog/indeks.json."""
    rel = lambda p: str(p.relative_to(O.KANAL)) if p.exists() else None
    oz = KATALOG / "onizleme"
    I = {}
    for tur in TURLER:
        I[tur] = []
        for ad, d in _katalog_kayitlar(tur).items():
            e = {"ad": ad, "baslik": d.get("baslik", ad), "ozet": d.get("ozet", ""), "uygun": d.get("uygun", []), "kaynak": d.get("kaynak", "katalog"),
                 "durum": d.get("durum", "onayli")}
            if tur == "gorsel":
                e["onizleme"] = rel(oz / "gorsel" / f"{ad}.png")
                e["varyasyonlar"] = [{"harf": k, "ad": v.get("ad", ""), "onizleme": rel(oz / "gorsel" / f"{ad}-{k}.png")} for k, v in sorted(d["varyasyonlar"].items())]
            elif tur == "animasyon":
                e["onizleme"] = rel(oz / "animasyon" / f"{ad}.mp4")
                e["poster"] = rel(oz / "animasyon" / f"{ad}.png")
            else:
                e["onizleme"] = {k: rel(oz / "ses" / f"{ad}-{k}.mp3") for k in ("ace", "kod")}
            I[tur].append(e)
    (KATALOG / "indeks.json").write_text(json.dumps(I, ensure_ascii=False, indent=1) + "\n")


def _katalog_motor(yeniden):
    """Yeni film levhasındaki motor önizlemesi: katalog/motor/<motor>/sahne.py (motorun bir tarza bağlı olmadığını gösteren örnek)
    → katalog/onizleme/motor/<motor>.mp4 + .png (9x16, 270 px). Şimdilik Blender; öteki motorların önizlemesi elle konur."""
    import blender
    from PIL import Image
    out = KATALOG / "onizleme" / "motor"
    for sahne in sorted((KATALOG / "motor").glob("blender/sahne.py")):
        m = sahne.parent.name
        if not yeniden and (out / f"{m}.mp4").exists():
            continue
        tmp = out / "_kare" / m
        tmp.mkdir(parents=True, exist_ok=True)
        kare = {45: tmp / "f00045.png"}
        blender.katalog_demo(sahne.parent, {}, tmp / "tam.mp4", kare, fmt="9x16")  # görünüşsüz: renkler sahnenin yedekleri
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "tam.mp4"), "-vf", "scale=270:480", "-an", "-c:v", "libx264", "-crf", "24",
                        "-pix_fmt", "yuv420p", str(out / f"{m}.mp4")], check=True)
        Image.open(kare[45]).convert("RGB").resize((270, 480)).save(out / f"{m}.png")
        shutil.rmtree(out / "_kare", ignore_errors=True)
        print(f"motor önizlemesi: {(out / f'{m}.mp4').relative_to(O.ROOT)}")


def _katalog_altyazi(yeniden):
    """Yeni film levhasındaki altyazı seçiminin önizlemesi: aynı diyalog (katalog/onizleme/altyazi/kaynak/, dondurulmuş Edge anlatımı)
    klasik ve niyetli altyazıyla → katalog/onizleme/altyazi/<tur>.mp4 (9x16'nın altyazı bölgesi, 432 × 200, sesli) + .png (kapak: "Sus, yavaş konuş.").
    Küçük resimde yazı okunsun diye yalnız altyazının oturduğu şerit (y 1000–1500) gösterilir."""
    from PIL import Image
    import niyet
    out = KATALOG / "onizleme" / "altyazi"
    if yeniden:  # sayfa yerleşimi kaynaktaki dondurulmuş kelime ölçümünden yeniden kurulur (ses yeniden ölçülmez)
        yol = out / "kaynak" / "timeline.json"
        tl = json.loads(yol.read_text())
        N = tl["niyet"]
        N["surum"] = niyet.SURUM
        N["formatlar"] = {f: niyet.yerlesim(N["kelimeler"], f, tl["duration"]) for f in N["formatlar"]}
        yol.write_text(json.dumps(tl, ensure_ascii=False, separators=(",", ":")))
    for tur in ("klasik", "niyetli"):
        if not yeniden and (out / f"{tur}.mp4").exists():
            continue
        tmp = out / "_kare" / tur
        tmp.mkdir(parents=True, exist_ok=True)
        run(["npx", "remotion", "render", "src/index.ts", "KatalogAltyazi", tmp / "sessiz.mp4", "--props", json.dumps({"tur": tur}),
             "--codec=h264", "--crf=18", "--log=error"])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "sessiz.mp4"), "-i", str(out / "kaynak" / "ses.m4a"), "-vf", "crop=1080:500:0:1000,scale=432:200",
                        "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart",
                        str(out / f"{tur}.mp4")], check=True)
        r = render_jobs([{"comp": "KatalogAltyazi", "out": tmp, "frames": [87], "props": {"tur": tur}}])[0]
        Image.open(r[87]).convert("RGB").crop((0, 1000, 1080, 1500)).resize((432, 200)).save(out / f"{tur}.png")
        shutil.rmtree(out / "_kare", ignore_errors=True)
        print(f"altyazı önizlemesi: {(out / f'{tur}.mp4').relative_to(O.ROOT)}")


def _katalog_cizer(yeniden):
    """Yeni film levhasındaki Blender çizeri önizlemesi: motor önizlemesinin sahnesi (malzeme yelpazesi), aynı kare Cycles ve EEVEE ile,
    teslim kalitesinde → katalog/onizleme/cizer/<çizer>.png (540×960) + olcum.json (bu sahnede sn/kare; panelin süre tahmini kil kamp ölçümünden)."""
    import blender
    from PIL import Image
    out = KATALOG / "onizleme" / "cizer"
    if not yeniden and all((out / f"{c}.png").exists() for c in blender.CIZERLER):
        return
    out.mkdir(parents=True, exist_ok=True)
    tmp = {c: out / f"_{c}.png" for c in blender.CIZERLER}
    sn = blender.katalog_cizer(KATALOG / "motor" / "blender" / "sahne.py", tmp)
    for c, p in tmp.items():
        Image.open(p).convert("RGB").resize((540, 960), Image.LANCZOS).save(out / f"{c}.png")
        p.unlink()
    (out / "olcum.json").write_text(json.dumps({"sahne": "katalog/motor/blender/sahne.py", "kare": 45, "kalite": "tam", "sn_kare": sn,
                                                "tarih": today()}, ensure_ascii=False, indent=1) + "\n")
    print(f"çizer önizlemesi: {out.relative_to(O.ROOT)} · " + " · ".join(f"{c} {x} sn/kare" for c, x in sn.items()))


def cmd_katalog(*args):
    """Stil kataloğu: görüntü stilleri, animasyon tipleri, ses stilleri. Doğrular, eksik önizlemeleri üretir, indeksi yazar."""
    pos, o = opts(args, "ad")
    turler = [t for t in pos if t in TURLER] or ([] if {"motor", "altyazi", "cizer"} & set(pos) else list(TURLER))
    adlar = o["ad"].split(",") if o.get("ad") else None
    _katalog_index_ts()
    if o.get("indeks"):  # yalnız indeks (panel: onay/silme sonrası)
        _katalog_indeks()
        return
    for tur in turler:
        bilinmeyen = [a for a in adlar or [] if a not in _katalog_kayitlar(tur)]
        if bilinmeyen and len(turler) == 1:
            raise SystemExit(f"Katalogda yok: {tur}/{', '.join(bilinmeyen)}")
    if "gorsel" in turler:
        _katalog_gorsel(adlar, o.get("yeniden"))
    if "animasyon" in turler:
        _katalog_animasyon(adlar, o.get("yeniden"))
    if "ses" in turler:
        _katalog_ses(adlar, o.get("yeniden"))
    if "altyazi" in pos:  # yalnız açıkça istenince: ./st katalog altyazi [--yeniden]
        _katalog_altyazi(o.get("yeniden"))
    if "motor" in pos:  # yalnız açıkça istenince: ./st katalog motor [--yeniden]
        _katalog_motor(o.get("yeniden"))
    if "cizer" in pos:  # yalnız açıkça istenince: ./st katalog cizer [--yeniden]
        _katalog_cizer(o.get("yeniden"))
    _katalog_indeks()
    print(f"indeks: {(KATALOG / 'indeks.json').relative_to(O.ROOT)}")


def _katalog_animasyon(adlar, yeniden):
    """Her animasyon tipi: 3 sn döngü (540 px mp4) + poster karesi + üç anlık kare (göz kontrolü için)."""
    from PIL import Image
    A = _katalog_kayitlar("animasyon")
    out = KATALOG / "onizleme" / "animasyon"
    out.mkdir(parents=True, exist_ok=True)
    adlar = [a for a in (adlar or A) if a in A]
    demolar = {a for a, d in A.items() if d.get("kaynak", "katalog") == "katalog" and d.get("ornek_motor") not in ("hyperframes", "blender")}  # ornekler.tsx'te örneği olanlar
    yap = [ad for ad in adlar if yeniden or not (out / f"{ad}.mp4").exists()]
    # referanstan ya da filmden gelen tip: en yakın örnek (demo_tip) ve örnek kod (demo) yoksa kendi videosundan 3 sn (demo_aralik: [bas, son] sn)
    for ad in [a for a in yap if (A[a].get("demo_tip") not in demolar and a not in demolar and A[a].get("ornek_motor") not in ("hyperframes", "blender"))
               or (A[a].get("referans") and not A[a].get("demo") and not A[a].get("demo_tip"))]:
        ref = O.ROOT / A[ad]["referans"] if A[ad].get("referans") else None
        if ref and ref.exists():
            bas, son = A[ad].get("demo_aralik") or [1, 4]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{bas:g}", "-t", f"{son - bas:g}", "-i", str(ref), "-vf",
                            "scale=540:540:force_original_aspect_ratio=increase,crop=540:540", "-an", "-c:v", "libx264", "-crf", "24", str(out / f"{ad}.mp4")], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(bas + son) / 2 if A[ad].get('demo_aralik') else 2:g}", "-i", str(ref), "-frames:v", "1", "-vf",
                            "scale=540:540:force_original_aspect_ratio=increase,crop=540:540", str(out / f"{ad}.png")], check=True)
        yap.remove(ad)
    for ad in [a for a in yap if A[a].get("ornek_motor") == "hyperframes"]:  # HyperFrames örneği: katalog/animasyon/hf/<ad>/index.html
        import hf
        stil, harf = A[ad].get("demo_gorunus") or ["duz-illustrasyon", "a"]
        kareler = {f: out / "_kare" / ad / f"f{f:05d}.png" for f in (22, 45, 68)}
        kareler[22].parent.mkdir(parents=True, exist_ok=True)
        mp4 = out / "_kare" / ad / "tam.mp4"
        hf.katalog_demo(O.ROOT / Path(A[ad]["demo"]).parent, _katalog_kayitlar("gorsel")[stil]["varyasyonlar"][harf], mp4, kareler)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", "scale=540:540", "-an", "-c:v", "libx264", "-crf", "24",
                        "-pix_fmt", "yuv420p", str(out / f"{ad}.mp4")], check=True)
        Image.open(kareler[45]).convert("RGB").resize((540, 540)).save(out / f"{ad}.png")
        serit = Image.new("RGB", (3 * 360, 360))
        for i, f in enumerate((22, 45, 68)):
            serit.paste(Image.open(kareler[f]).convert("RGB").resize((360, 360)), (i * 360, 0))
        serit.save(out / f"{ad}-serit.png")
        shutil.rmtree(out / "_kare" / ad, ignore_errors=True)
        yap.remove(ad)
    for ad in [a for a in yap if A[a].get("ornek_motor") == "blender"]:  # Blender örneği: katalog/animasyon/blender/<ad>/sahne.py (taslak plakalar)
        import blender
        stil, harf = A[ad].get("demo_gorunus") or ["duz-illustrasyon", "a"]
        kareler = {f: out / "_kare" / ad / f"f{f:05d}.png" for f in (22, 45, 68)}
        kareler[22].parent.mkdir(parents=True, exist_ok=True)
        mp4 = out / "_kare" / ad / "tam.mp4"
        blender.katalog_demo(O.ROOT / Path(A[ad]["demo"]).parent, _katalog_kayitlar("gorsel")[stil]["varyasyonlar"][harf], mp4, kareler)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", "scale=540:540", "-an", "-c:v", "libx264", "-crf", "24",
                        "-pix_fmt", "yuv420p", str(out / f"{ad}.mp4")], check=True)
        Image.open(kareler[45]).convert("RGB").resize((540, 540)).save(out / f"{ad}.png")
        serit = Image.new("RGB", (3 * 360, 360))
        for i, f in enumerate((22, 45, 68)):
            serit.paste(Image.open(kareler[f]).convert("RGB").resize((360, 360)), (i * 360, 0))
        serit.save(out / f"{ad}-serit.png")
        shutil.rmtree(out / "_kare" / ad, ignore_errors=True)
        yap.remove(ad)
    tip = lambda ad: ad if ad in demolar else A[ad]["demo_tip"]
    if yap:
        res = render_jobs([{"comp": "KatalogAnimasyon", "out": out / "_kare" / ad, "frames": [22, 45, 68], "props": {"tip": tip(ad)},
                            **({"gl": O.UC_GL} if A[ad].get("uc") else {})} for ad in yap])  # "uc": 3B katman, yazılımla
        for ad, r in zip(yap, res):
            Image.open(r[45]).convert("RGB").resize((540, 540)).save(out / f"{ad}.png")
            serit = Image.new("RGB", (3 * 360, 360))
            for i, f in enumerate((22, 45, 68)):
                serit.paste(Image.open(r[f]).convert("RGB").resize((360, 360)), (i * 360, 0))
            serit.save(out / f"{ad}-serit.png")
        shutil.rmtree(out / "_kare", ignore_errors=True)
    for ad in yap:
        run(["npx", "remotion", "render", "src/index.ts", "KatalogAnimasyon", out / f"{ad}.mp4", "--props", json.dumps({"tip": tip(ad)}),
             "--scale=0.5", "--codec=h264", "--crf=24", "--log=error", *O.gl_bayraklari(O.UC_GL if A[ad].get("uc") else None)])
    print(f"animasyon tipleri: {len(adlar)} tip, {len(yap)} yeni önizleme → {out.relative_to(O.ROOT)}")


ACE_DIZIN = O.KANAL / "araclar" / "ACE-Step-1.5"
ACE_PY = ACE_DIZIN / ".venv" / "bin" / "python"


def ace_uret(isler):
    """ACE-Step 1.5 ile müzik üretir (modeller bir kez yüklenir). İş: {cikti, caption, bpm, sure, ton, tohum, referans?}.
    Aynı ayar önbellekten gelir: araclar/ACE-Step-1.5/output/onbellek/<özet>.wav."""
    if not ACE_PY.exists():
        raise SystemExit("ACE-Step kurulu değil (araclar/ACE-Step-1.5). Kurulum: README → Ses stilleri.")
    onb = ACE_DIZIN / "output" / "onbellek"
    onb.mkdir(parents=True, exist_ok=True)
    yap = []
    for j in isler:
        anahtar = hashlib.sha1(json.dumps({k: j.get(k) for k in ("caption", "bpm", "sure", "ton", "tohum", "referans")}, sort_keys=True).encode()).hexdigest()[:16]
        j["_onb"] = onb / f"{anahtar}.wav"
        if not j["_onb"].exists():
            yap.append({**{k: v for k, v in j.items() if not k.startswith("_")}, "cikti": str(j["_onb"])})
    if yap:
        import fcntl
        # Aynı anda tek ACE-Step: 16 GB bellekte iki model birlikte sistemi diske taşır (öğrenimler #29). İkinci iş sırada bekler.
        with open(onb.parent / ".kilit", "w") as kilit:
            try:
                fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("→ ACE-Step başka bir iş için çalışıyor; sıra bekleniyor…", flush=True)
                fcntl.flock(kilit, fcntl.LOCK_EX)
            yap = [j for j in yap if not Path(j["cikti"]).exists()]  # beklerken üretilmiş olabilir
            if yap:
                print(f"→ ACE-Step: {len(yap)} parça üretiliyor (açılış ~5 dk, parça başına ~2 dk; önbellekte {len(isler) - len(yap)}). "
                      "Bellek için öteki uygulamaları kapatmak hızlandırır.", flush=True)
                r = subprocess.run([str(ACE_PY), str(O.ROOT / "pipeline" / "ace_muzik.py"), json.dumps(yap)], cwd=O.ROOT, capture_output=True, text=True)
                if r.returncode:
                    raise SystemExit("ACE-Step hatası:\n" + (r.stderr or r.stdout)[-1500:])
    for j in isler:
        Path(j["cikti"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(j["_onb"], j["cikti"])


def _mp3(wav, mp3, sure=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(wav)]
    if sure:
        cmd += ["-t", str(sure), "-af", f"afade=t=out:st={sure - 1.5}:d=1.5"]
    subprocess.run(cmd + ["-c:a", "libmp3lame", "-b:a", "160k", str(mp3)], check=True)


def _katalog_ses(adlar, yeniden):
    """Her ses stili için iki önizleme: kod (anında) ve ACE-Step (yavaş, önbellekli). 15 sn."""
    Sx = _katalog_kayitlar("ses")
    out = KATALOG / "onizleme" / "ses"
    out.mkdir(parents=True, exist_ok=True)
    tmp = O.ROOT / "out" / "_katalog_ses"
    tmp.mkdir(parents=True, exist_ok=True)
    ace = []
    adlar = [a for a in (adlar or Sx) if a in Sx]
    for ad in adlar:
        m = Sx[ad]["muzik"]
        k = m["kod"]
        if yeniden or not (out / f"{ad}-kod.mp3").exists():
            per = 60 / k["bpm"]
            olcu = max(4, int(np.ceil(16 / (4 * per))))
            yapi = f"giris:1,yukselis:1,ana:{max(1, olcu - 3)},kapanis:1"
            run([PY, "-I", "pipeline/muzik.py", tmp / f"{ad}.wav", "--stil", k["stil"], "--bpm", str(k["bpm"]), "--ton", k.get("ton", "A"), "--yapi", yapi])
            _mp3(tmp / f"{ad}.wav", out / f"{ad}-kod.mp3", 15)
        if yeniden or not (out / f"{ad}-ace.mp3").exists():
            a = m["ace"]
            ace.append({"ad": ad, "cikti": str(tmp / f"{ad}-ace.wav"), "caption": a["caption"], "bpm": a.get("bpm"), "sure": 15,
                        "ton": a.get("ton", ""), "tohum": a.get("tohum", 42), **({"referans": str(O.ROOT / a["referans"])} if a.get("referans") else {})})
    if ace:
        if ACE_PY.exists():
            ace_uret(ace)
            for j in ace:
                _mp3(j["cikti"], out / f"{j['ad']}-ace.mp3", 15)
        else:
            print("ACE-Step kurulu değil: ACE önizlemeleri atlandı")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"ses stilleri: {len(adlar)} stil, {len(ace)} ACE parçası → {out.relative_to(O.ROOT)}")


ELESTIRI_ISTEM = """Sen bu filmi hiç görmemiş, sert ve deneyimli bir hareket tasarımı yönetmenisin. Bir stüdyo kodla render ettiği kısa bir filmi sana gösteriyor.
Sana filmin ne anlatmak istediği SÖYLENMEYECEK; yalnız gördüğünü yargıla. Bu klasör dışındaki hiçbir dosyayı okuma, arama yapma.

Bu klasörde:
- kontak-<format>.png: her format için kontak tabakası. Üstte her vuruştan bir kare, ortada geçiş şeritleri (ara kareler), altta zaman çizelgesi
  (ses dalgası, görüntü değişim eğrisi; kırmızı bant = uzun donuk aralık). Önce bunları oku.
- kareler-<format>/fNNNNN.png: tam çözünürlüklü kareler. NNNNN kare numarası, zaman = NNNNN / {fps} sn. Kanıt için ilgili kareleri aç.
- olcum.md: otomatik ölçüm (süre, kanca, tempo, donuk aralık, tek karelik sıçrama, boş ekran, kontrast, ses yüksekliği). Ölçüm zanaatı denetler, etkiyi değil.
- olcutler.md: stüdyonun zanaat rehberi. Yasak listesi DEĞİL, ipucu: §1 (görsel kural, ana nesne, dünya kurma), §2 (karakter çizimi: tam taahhüt ve tutarlılık), §3–4 (hareket ve yazı), §8 (sebepsiz kullanılınca ucuz duran varsayılanlar).
  Bir şeyi yalnız olcutler.md'de geçtiği için kusur sayma: konfeti, zıplayan hareket, gradyan gökyüzü, çizilmiş karakter filmin dünyasına hizmet ediyor ve iyi yapılmışsa güçtür.
- karsilastirma/: stüdyonun katalog kartlarının önizlemeleri (kart-*.png) ve stüdyonun öteki filmlerinden birer poster karesi (film-*.png).
  Bu filmle ilgileri söylenmiyor; yalnız "şablon gibi mi, daha önce görülmüş bir şeye mi benziyor" sorusu için bak.

Film: {sure:.1f} sn · {fps} kare/sn · formatlar: {formatlar}.{beklenti}

Şunlara bak: ilk iki saniye gerçek bir kanca mı; telefon boyutunda her yazı okunuyor mu; her hareketten sonra nereye bakılacağı belli mi;
sahneler tek bir görsel fikirle ya da tek bir dünyayla mı bağlı yoksa dağınık mı; geçişler nesneden mi doğuyor yoksa kesme ve siyah ekranla mı;
karakter ve nesneler aynı çizim diliyle mi yapılmış, oranları tutarlı, ifadeleri canlı mı; ucuz, şablon ya da "yapay zekâ işi" görünen bir şey var mı;
duraklatılan her an tek başına bir resim olarak ayakta duruyor mu; son kare kapak olacak kadar güçlü mü.
Ve en önemlisi: bu film cesur ve akılda kalıcı mı, yoksa kusursuz ama sıkıcı mı? Güvenli, sönük, "hiçbir şey olmuyor" hissi de bir kusurdur (P1).
Üç soruyu da yanıtla: ilk saniye, akışta kaydırmayı durdurur mu, neden? Bu filmi birine gönderir misin, neden? Şablon gibi mi, daha önce görülmüş
bir şeye mi benziyor (karsilastirma/ klasörüne ve bildiğin işlere göre)? Belirgin bir benzerlik ucuzluk belirtisidir: kusurlara da yaz.
Övgüyle başlama. Kararını yalnız kanıta dayandır; her kusur için dosya adı ve kare numarası ver.

Yanıtın SADECE şu Markdown olsun (Türkçe, sade):

**Karar:** yayınla | bir tur daha
**Anladığım mesaj (tek cümle):** <film sana ne söyledi; anlamadıysan "anlaşılmıyor" yaz>
**Genel izlenim:** <en fazla iki cümle>

## Üç soru
- **İlk saniye kaydırmayı durdurur mu?** <evet | hayır, neden; ilk karelerden kanıtla>
- **Bu filmi birine gönderir misin?** <evet | hayır, kime ve neden>
- **Şablon gibi mi, daha önce görülmüş bir şeye mi benziyor?** <hayır | evet: karsilastirma/ klasöründeki hangi dosyaya ya da bildiğin hangi işe, neden>{kural_sorusu}

## Kusurlar (en büyükten küçüğe, en fazla 6)
### 1. <kısa başlık>
- **Önem:** P0 (yayını engeller) | P1 (belirgin ucuzluk) | P2 (rötuş)
- **Zaman:** <00:00.00 · f00000 · format>
- **Kanıt:** <dosya ve ne görülüyor>
- **Neden kötü:** <tek cümle>
- **Yerel düzeltme önerisi:** <somut: ne, nerede, hangi yönde>

## Sebepsiz ya da özensiz kullanılmış varsayılanlar
- <olcutler.md §8'den yalnız filme hizmet etmeyenler, nedeniyle; yoksa "görülmedi">

## Daha cesur olabileceği yer (en fazla 2)
- <filmi daha akılda kalıcı yapacak somut bir fikir; yoksa "yok">

## Güçlü yanlar (en fazla 3)
- <madde>

Karar kuralı: P0 varsa ya da birden fazla P1 varsa "bir tur daha"; yoksa "yayınla".{karar_eki}
"""


def _uretim_kurali(v) -> str | None:
    """Filmin tek üretim kuralı (brief → Yönetmenlik; yoksa seçilen yolun kuralı), gerekçesi olmadan: eleştirmene beklenti olarak verilir."""
    b = v.dir / "brief.md"
    m = re.search(r"\*\*Üretim kuralı[^*]*:\*\*\s*(.+)", b.read_text()) if b.exists() else None
    k = m.group(1).strip() if m else ""
    if not k or k.startswith("["):
        G = v.gorunus_json() or {}
        k = str((((G.get("secenekler") or {}).get(G.get("secim") or "") or {}).get("yol") or {}).get("kural") or "").strip()
    k = re.split(r"\s+[·—]\s+", k)[0].strip().strip("*") if k else ""
    return k if k and not O.PLACEHOLDER.search(k) else None


def _elestiri_beklentisi(v) -> dict:
    """Kör eleştirmene verilen beklentiler (amaç değil): kullanıcının seçtiği cesaret ve filmin tek üretim kuralı → istem alanları."""
    c, kural = v.script.get("cesaret"), _uretim_kurali(v)
    b = ""
    if c in CESARET:
        b += f"\nBu stüdyo bu film için {CESARET[c][0].lower()} cesaret istedi: {CESARET[c][1]} Kararını bu beklentiye göre de ver."
    if kural:
        b += f"\nStüdyo bu filme tek bir üretim kuralı koydu: «{kural}». Karelerde bu kurala uyulmuş mu, bak."
    return {"beklenti": b,
            "kural_sorusu": "\n- **Üretim kuralına uyulmuş mu?** <evet | hayır: hangi karede bozuluyor; filmi dağıtıyorsa P1, tek karede kaçmışsa P2>" if kural else "",
            "karar_eki": "\nCesaret sınırsız istendiyse ve filmde olağanüstü (akılda kalan, imkânsız ama gerçek görünen) bir an yoksa bu bir P1'dir." if c == "sinirsiz" else ""}


def cmd_elestir(vid, *args):
    """Kör eleştiri (CLAUDE.md kural 4'ün uygulaması): filmi yapan oturum kendi filmini puanlamaz. Proje dışındaki geçici bir klasöre
    yalnız kontak tabakaları, kareler, ölçüm, genel zanaat ölçütleri ve karşılaştırma kareleri (katalog kartları, öteki filmlerin posterleri;
    adları gizli) kopyalanır; yeni bir Claude oturumu orada, amacı bilmeden yargılar. Beklenti olarak yalnız kullanıcının seçtiği cesaret ve
    filmin tek üretim kuralı verilir. --cikti <dosya>: eleştiriyi inceleme klasörü yerine oraya yaz (deneme; Kapı 5 kanıtı sayılmaz)."""
    import tempfile
    import benzerlik
    _, o = opts(args, "cikti")
    v = O.load(vid)
    rd = O.latest_review_dir(v)
    if not rd or not (rd / "olcum.md").exists():
        raise SystemExit(f"Önce ./st inceleme {vid}")
    tmp = Path(tempfile.mkdtemp(prefix="st_elestiri_"))
    for fmt in v.formatlar:
        kname, kdir, _ = review_names(v, fmt)
        if (rd / kname).exists():
            shutil.copy2(rd / kname, tmp / f"kontak-{fmt}.png")
        if (rd / kdir).exists():
            shutil.copytree(rd / kdir, tmp / f"kareler-{fmt}")
    shutil.copy2(rd / "olcum.md", tmp / "olcum.md")
    shutil.copy2(O.ROOT / "zanaat.md", tmp / "olcutler.md")
    kd = tmp / "karsilastirma"  # katalog önizlemeleri + öteki filmlerin birer poster karesi (film adları gizli: amaç sızmasın)
    kd.mkdir()
    oz = O.ROOT / "katalog" / "onizleme"
    for t, ad in (("gorsel", "goruntu"), ("animasyon", "hareket")):
        for f in sorted((O.ROOT / "katalog" / t).glob("*.json")):
            src = oz / t / f"{f.stem}.png"
            if src.exists() and O.jload(f).get("durum") != "taslak":
                shutil.copy2(src, kd / f"kart-{ad}-{f.stem}.png")
    filmler = []
    for w in benzerlik.oteki_filmler(v):
        pk = benzerlik.poster_karesi(w)
        if pk:
            filmler.append(w.id)
            shutil.copy2(pk, kd / f"film-{len(filmler):02d}.png")
    istem = ELESTIRI_ISTEM.format(fps=v.fps, sure=v.duration, formatlar=", ".join(v.formatlar), **_elestiri_beklentisi(v))
    print(f"→ kör eleştiri: {rd.relative_to(O.ROOT)} (geçici klasör {tmp}; brief, senaryo ve kod verilmez)")
    bayrak = O.claude_bayraklari("elestiri")
    if bayrak:
        print(f"   eleştirmen: {' '.join(bayrak)} (panel → Claude ayarları)")
    r = subprocess.run(["claude", "-p", istem, "--output-format", "text", *bayrak, "--allowedTools", "Read", "Glob",
                        "--disallowedTools", "Bash", "Edit", "Write", "WebFetch", "WebSearch", f"Read(/{O.KANAL}/**)", f"Glob(/{O.KANAL}/**)"],
                       cwd=tmp, capture_output=True, text=True, timeout=1800)
    shutil.rmtree(tmp, ignore_errors=True)
    out = r.stdout.strip()
    if r.returncode or "**Karar:**" not in out:
        raise SystemExit(f"Eleştiri alınamadı (çıkış {r.returncode}):\n{(r.stderr or out)[-2000:]}")
    bk = _elestiri_beklentisi(v)
    head = (f"# Kör eleştiri — {vid} · {rd.name} · {today()}\n\n"
            f"> Filmi hiç görmemiş bir Claude oturumu yalnız kontak tabakalarını, kareleri, ölçümü, `zanaat.md`'yi ve karşılaştırma klasörünü "
            f"(katalog kartları; öteki filmlerin posterleri adsız: {', '.join(f'film-{i + 1:02d} = {x}' for i, x in enumerate(filmler)) or 'yok'}) gördü; "
            f"brief, senaryo ve kod verilmedi.\n"
            f"> Beklenti olarak verilen: {bk['beklenti'].strip().replace(chr(10), ' ') or 'yok (cesaret ve üretim kuralı yazılmamış)'}\n"
            f"> Filmin amaçlanan tek cümlesi (karşılaştırma için, eleştirmene gösterilmedi): {v.script.get('learningGoal') or '—'}\n\n")
    hedef = Path(o["cikti"]).expanduser().resolve() if o.get("cikti") else rd / "elestiri.md"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(head + out + "\n")
    print(f"yazıldı: {hedef.relative_to(O.ROOT) if O.ROOT in hedef.parents else hedef}")
    for ln in out.splitlines():
        if ln.startswith("**Karar:**") or ln.startswith("**Anladığım mesaj"):
            print("  " + ln)
    print(f"  Amaçlanan: {v.script.get('learningGoal') or '—'}")


def elestiri_karari(rd: Path | None):
    """Son inceleme klasöründeki kör eleştirinin kararı: 'yayınla' / 'bir tur daha' / None (yok)."""
    f = rd / "elestiri.md" if rd else None
    if not f or not f.exists():
        return None
    m = re.search(r"\*\*Karar:\*\*\s*([^\n]+)", f.read_text())
    return m.group(1).strip().lower() if m else "okunamadı"


def cmd_deterministik(vid, *args):
    """Atlanabilirlik: kareler önce artan, sonra azalan sırada render edilir; bayt bayt aynı olmalı.
    Ayrıca kaynakta gizli saat / tohumsuz rastgelelik arar."""
    _, o = opts(args, "format", "veri", "satir")
    v = O.load(vid)
    if o.get("yapim"):   # yapım filmi (./st yapim): malzeme sha256, Yapim kompozisyonu iki sırada, kılavuz kipinin yeniden çizimi, Blender geçişi
        import yapim
        satir = yapim.deterministik(v)
        print("\n".join(satir))
        if any(s_.startswith("❌") for s_ in satir):
            raise SystemExit(1)
        return
    n = v.nframes
    frames = sorted({0, 1, n // 7, n // 3, n // 2, (2 * n) // 3, n - 2, n - 1} | {round(t * v.fps) for t in list(v.cues.values())[::4]})
    import gecis
    import plaka
    if plaka.var_mi(v):  # karma film: her sahnenin ilk, orta ve son karesi de (motor plakası + üst katman)
        frames = sorted(set(frames) | {f for S in plaka.sahneler(v) if not S["hata"] for f in (S["bas_f"], (S["bas_f"] + S["son_f"]) // 2, S["son_f"] - 1)})
    if gecis.var_mi(v):  # gölgelendirici kesimleri: her pencerenin ilk, kesim ve son karesi de (plakalar + GL birleşimi)
        frames = sorted(set(frames) | {f for k in gecis.tanim_json(v).values() for f in (k["bas"], k["kesim"], k["son"] - 1)})
    base = O.ROOT / "out" / "_deterministik"
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    # HyperFrames: SwiftShader (deterministik kip); donanım GPU'su kenar yumuşatmasını sıraya göre birkaç pikselde değiştiriyor (ogrenimler #39)
    # 3B katmanlı Remotion kompozisyonu render_frames'te kendiliğinden yazılımla (v.gl = swangle) çizilir
    ek = {"yazilim": True} if v.motor == "hyperframes" else None
    import kisisel
    if o.get("veri"):   # kişisel film: bir veri satırının kareleri (yoksa şablonun TEST örneği); kareler kişiseldir, iş sonunda silinir
        if not kisisel.var_mi(v):
            raise SystemExit(f"{vid}: kişisel film şablonu yok (veri_sablonu.json)")
        yol = next((p for p in (Path(o["veri"]), O.ROOT / o["veri"], kisisel.dizin(v) / "veri" / o["veri"]) if p.exists()), None)
        if not yol:
            raise SystemExit(f"veri dosyası yok: {Path(o['veri']).name}")
        es = O.jload(kisisel.dizin(v) / "esleme.json") if (kisisel.dizin(v) / "esleme.json").exists() else {}
        Hs = kisisel.hazirla(v, yol, es, [o["satir"]] if isinstance(o.get("satir"), str) else None)
        x = next((x for x in Hs["satirlar"] if x["kisi"]), None)
        if not x:
            raise SystemExit("geçerli satır yok (./st toplu " + vid + " denetle)")
        ek = {**(ek or {}), "kisi": {**x["kisi"], "film": v.id}}
        print(f"kişisel film: satır {x['no']} · {x['kimlik']} ({'TEST' if Hs['test'] else 'kurum verisi'})")
    if v.gl:
        print(f"3B katman: kareler {v.gl} (yazılım, SwiftShader) ile çiziliyor")
    # Blender: Cycles bu Mac'te bayt bayt aynı çizmiyor (≤ 1/255; denemeler/blender_kil_cadir/OKU.md). Plakalar dondurulur:
    # (1) plaka üstü birleştirme (Remotion) katı, (2) Blender'ın ayrı işlemde yeniden çizimi toleransla ölçülür.
    kotu = 0
    for fmt in fmts(v, o):
        a = render_frames(v, frames, base / fmt / "a", fmt, "asc", ek)
        b = render_frames(v, frames, base / fmt / "b", fmt, "desc", ek)
        diff = [f for f in frames if h(a[f]) != h(b[f])]
        kotu += bool(diff)
        print(f"{'✅' if not diff else '❌'} [{fmt}] {len(frames) - len(diff)}/{len(frames)} kare iki sırada da birebir aynı"
              + (" (plaka üstü birleştirme)" if v.motor == "blender" else "") + (f" · farklı: {diff}" if diff else ""))
        if v.motor == "blender":
            import blender
            satir = blender.yeniden_ciz(v, fmt)
            kotu += any(x.startswith("❌") for x in satir)
            print("\n".join(satir))
        if plaka.var_mi(v):  # karma film: her sahnenin plakaları ayrı işlemde (HyperFrames bayt bayt, Blender toleranslı)
            satir = plaka.yeniden_ciz(v, fmt)
            kotu += any(x.startswith("❌") for x in satir)
            print("\n".join(satir))
        if gecis.var_mi(v):  # geçiş plakaları ayrı bir çizimde ters sırayla: bayt bayt (sıra bağımlılığı yok)
            satir = gecis.yeniden_ciz(v, fmt, frames, gecis.cizim_girdisi(v, fmt, _veri_props(v, ek)))
            kotu += any(x.startswith("❌") for x in satir)
            print("\n".join(satir))
    bad = re.compile(r"Math\.random|Date\.now|new Date\(|performance\.now|setTimeout|setInterval|requestAnimationFrame|"
                     r"transition\s*:|animation\s*:|@keyframes|"
                     r"backgroundImage\s*:\s*[`'\"]?url\(")  # CSS arka plan görselini Remotion beklemez (ogrenimler #15): <Img> kullan
    hits = []
    if v.motor == "hyperframes":  # HTML'de CSS animasyonu ve gizli saat; GSAP zaman çizelgesi serbest
        import hf
        bad = re.compile(r"Math\.random|Date\.now|new Date\(|performance\.now|setTimeout|setInterval|requestAnimationFrame|"
                         r"transition\s*:|animation\s*:|@keyframes")
        dosyalar = [p for p in hf.kaynaklar(v) if p.suffix in (".html", ".js", ".css") and "assets/lib" not in str(p)]
        if hf.niyet_kullanir(hf.klasor(v)):  # paketlenen niyet.js'in kaynağı (src/lib/niyet) da taranır
            dosyalar += list((O.ROOT / "src" / "lib" / "niyet").glob("*.ts"))
    else:
        dosyalar = list((O.ROOT / "src").rglob("*.ts*"))
    if v.motor == "blender":  # sahne kodu: tohumsuz rastgelelik, saat, kare işleyicisi, pişirilmemiş fizik
        import blender
        hits += blender.tara(v)
    if plaka.var_mi(v):  # karma film: her sahnede kendi motorunun taraması
        hits += plaka.tara(v)
    hits += uc_denetle(v)  # 3B katman: useFrame, setAnimationLoop, Three.js saati, CDN
    for p in dosyalar:
        for i, ln in enumerate(p.read_text().splitlines(), 1):
            if bad.search(ln):
                hits.append(f"{p.relative_to(O.ROOT)}:{i}: {ln.strip()[:90]}")
    print(("✅ kaynakta gizli saat / tohumsuz rastgelelik / CSS animasyonu / beklenmeyen CSS görseli yok" if not hits else "❌ şüpheli satırlar:\n  " + "\n  ".join(hits)))
    shutil.rmtree(base, ignore_errors=True)
    if v.niyetli:  # niyetli altyazının ölçümü de deterministik: anlatımdan yeniden hesap kayıttakiyle birebir aynı olmalı
        import niyet
        taze, neden = niyet.tazelik(v)
        ayni = taze and niyet.hesapla(v) == v.timeline.get("niyet")
        print(f"✅ niyetli altyazı ölçümü yeniden hesapta birebir aynı ({neden})" if ayni else
              f"❌ niyetli altyazı ölçümü kayıttakinden farklı ya da eski ({neden}): ./st niyet {v.id}")
    import uretim
    if uretim.var_mi(v):  # Magnific üretimleri dondurulmuş girdidir: asıl ve motorun okuduğu kopya kayıttaki sha256'yla aynı olmalı
        dg = uretim.dogrula(v)
        bozuk = [f"{a}: {m}" for a, ok, m in dg if not ok]
        print(f"✅ üretim varlıkları dondurulmuş: {len(dg)}/{len(dg)} dosya sha256 kayıttakiyle aynı" if not bozuk
              else "❌ üretim varlığı değişmiş ya da eksik (dondurulmuş girdi; yeniden üretim yeni adla gelir):\n  " + "\n  ".join(bozuk))
        if bozuk:
            raise SystemExit(1)
    import goruntu
    if goruntu.var_mi(v):  # gerçek görüntü türevleri (ara format, derinlik, maske, kadraj, bilgi.json) dondurulmuş girdidir
        dg = goruntu.dogrula(v)
        bozuk = [f"{a}: {m}" for a, ok, m in dg if not ok]
        print(f"✅ gerçek görüntü dondurulmuş: {len(dg)}/{len(dg)} dosya sha256 kayıttakiyle aynı" if not bozuk
              else "❌ gerçek görüntü dosyası değişmiş ya da eksik:\n  " + "\n  ".join(bozuk))
        if bozuk:
            raise SystemExit(1)
    if kisisel.var_mi(v):  # kişisel film: şablon geçerli, sahne kodu kişi verisini useKisi'den okur, TEST plakası var, çizimde ağ yok
        kotu_s = [m for d_, m in kisisel.sablon_sorunlari(kisisel.sablon(v), v) if d_ == "❌"]
        kod = [m for d_, m in kisisel.kod_denetimi(v) if d_ == "❌"]
        print("✅ kişisel film: şablon geçerli, kişi verisi useKisi'den, TEST plakası var, çizimde ağ yok" if not (kotu_s or kod)
              else "❌ kişisel film: " + "; ".join(kotu_s + kod))
        if kotu_s or kod:
            raise SystemExit(1)
    import veri
    if veri.var_mi(v):  # canlı veri: anlık görüntü dondurulmuş girdidir; değerler ham yanıttan yeniden hesapta aynı; çizimde ağ yok
        dg = veri.dogrula(v)
        bozuk = [f"{a}: {m}" for a, ok, m in dg if not ok]
        kod = [m for d_, m in veri.kod_denetimi(v) if d_ == "❌"]
        x = veri.secili(v)
        print(f"✅ canlı veri dondurulmuş: görüntü {x['kimlik']} ({x['zaman_yerel']}), {len(dg)}/{len(dg)} denetim (sha256, yeniden hesap, motor kopyası)"
              if x and not bozuk else "❌ canlı veri: " + ("anlık görüntü yok" if not x else "\n  " + "\n  ".join(bozuk)))
        if kod:
            print("❌ canlı veri sahne kodu: " + "; ".join(kod))
        if bozuk or kod or not x:
            raise SystemExit(1)
    import takip
    if takip.secili(v):  # kamera takibi: çözüm ve takip edilen çekim dondurulmuş girdidir (plakalar bu çözümden çizilir)
        S = takip.denetle(v)
        bozuk = [f"{ad}: {d_}" for ok, ad, d_ in S[:2] if not ok]
        print(f"✅ kamera takibi dondurulmuş: {S[0][2]} · çekim {S[1][2]}" if not bozuk else "❌ kamera takibi: " + "; ".join(bozuk))
        if bozuk:
            raise SystemExit(1)
    if (v.motor == "blender" or gecis.var_mi(v) or plaka.var_mi(v)) and (kotu or hits):
        raise SystemExit(1)


def cmd_yayin(vid):
    import kisisel
    import uretim
    import veri
    v = O.load(vid)
    p = v.dir / "yayin.md"
    if p.exists():
        yenilenen = []
        if uretim.var_mi(v):  # yapay zekâ beyanı bloğu uretim.json'dan her seferinde yenilenir; gerisi elle doldurulmuş kalır
            uretim.beyan_yaz(v)
            yenilenen.append("yapay zekâ beyanı")
        if veri.var_mi(v):  # canlı verinin atıf bloğu seçili anlık görüntüden
            veri.yayin_yaz(v)
            yenilenen.append("veri kaynağı")
        if kisisel.var_mi(v):  # kişisel etki filmi: KVKK ve rıza bloğu (kullanıcının kararlarından)
            kisisel.yayin_yaz(v)
            yenilenen.append("kişisel veri")
        print(f"zaten var: {p.relative_to(O.ROOT)} " + (f"(yalnız {' ve '.join(yenilenen)} yenilendi)" if yenilenen else "(üzerine yazmıyorum)"))
        return
    src = []
    k = v.dir / "kaynaklar.md"
    if k.exists():
        sec = k.read_text().split("## Kaynakça")
        if len(sec) > 1:
            body = sec[1].split("\n## ")[0]
            src = [ln.strip() for ln in body.splitlines() if re.match(r"\s*\d+\.", ln)]
    kay = "\n".join(src) if src else ("[kaynaklar.md Kaynakça bölümü boş: önce Kapı 1]" if v.profil.get("kaynak_zorunlu") else "(bu profilde kaynak zorunlu değil)")
    t = (SABLON / "yayin.md").read_text()
    t = (t.replace("{{BASLIK}}", v.script.get("title", vid)).replace("{{ID}}", vid)
          .replace("{{HEDEF}}", v.script.get("learningGoal", "")).replace("{{KAYNAKLAR}}", kay)
          .replace("{{SURE}}", f"{v.duration:.0f}").replace("{{FORMATLAR}}", ", ".join(v.formatlar))
          .replace("{{YZ_BEYAN}}", uretim.beyan_md(v)))
    p.write_text(t)
    if veri.var_mi(v):
        veri.yayin_yaz(v)
    if kisisel.var_mi(v):
        kisisel.yayin_yaz(v)
    print(f"yazıldı: {p.relative_to(O.ROOT)}")


# ---------------------------------------------------------------- canlı veri (4d; pipeline/veri.py)
def _veri_kareleri(v, x: dict) -> list[str]:
    """Seçili görüntüyle kanıt karesi (script.json → veri_isareti) her format için → videos/<id>/veri/<kimlik>/kareler/<format>.png."""
    import veri
    f = veri.kanit_karesi(v)
    if f is None:
        print("not: script.json → veri_isareti yok (değerlerin ekranda tam göründüğü işaret): kanıt karesi çizilmedi")
        return []
    out = []
    hedef = veri.depo(v) / x["kimlik"] / "kareler"
    hedef.mkdir(parents=True, exist_ok=True)
    for fmt in v.formatlar:
        try:
            # HyperFrames yazılımla (SwiftShader): donanım GPU'su kenar yumuşatmasını çizimden çizime 1/255 oynatıyor (öğrenimler #39);
            # kanıt karesi o görüntünün kaydıdır, aynı görüntüye dönülünce bayt bayt aynı çıkmalı
            files = render_frames(v, [f], O.ROOT / "out" / "_veri" / v.id / "_ciz" / fmt, fmt, props={"yazilim": True} if v.motor == "hyperframes" else None)
        except (subprocess.CalledProcessError, SystemExit, KeyError) as e:  # veri alındı ve seçili; kare sahne hatası yüzünden çizilemedi
            print(f"⚠️ [{fmt}] kanıt karesi çizilemedi (sahne kodu hatası: {str(e)[:160]}); görüntü {x['kimlik']} alındı ve seçili. "
                  f"Sahne düzelince: ./st veri {v.id} kare")
            continue
        shutil.copy2(files[f], hedef / f"{fmt}.png")
        out.append(str((hedef / f"{fmt}.png").relative_to(O.ROOT)))
    return out


def cmd_veri(*args):
    """Canlı veri: ./st veri <id> kur|cek|sec|liste|kare|denetle · ./st veri saglayicilar"""
    import veri
    if not args or args[0] in ("saglayicilar", "-h", "--help"):
        for ad, P in veri.SAGLAYICILAR.items():
            print(f"{ad}: {P['ad']} · {P['kurum']}\n  lisans {P['lisans']} · {'ticari ve kurum kullanımı serbest' if P['ticari'] else 'kurum kampanyasında KULLANILMAZ'}"
                  f"\n  {P['not']}\n  koşullar {P['kosullar']}")
        print("\nKullanım: ./st veri <id> kur --saglayici met-norway --konum \"Ankara\" --enlem 39.92 --boylam 32.85 · cek [--ciz] · sec <kimlik|son> [--ciz] · "
              "liste · kare · denetle")
        return
    if len(args) < 2:
        raise SystemExit("Kullanım: ./st veri <id> kur|cek|sec|liste|kare|denetle")
    vid, alt, *rest = args
    pos, o = opts(rest, "saglayici", "konum", "enlem", "boylam", "saat-dilimi", "tazelik", "kullanim")
    try:
        if alt == "kur":
            for k in ("saglayici", "konum", "enlem", "boylam"):
                if not isinstance(o.get(k), str):
                    raise SystemExit(f"--{k} gerekli (konum kullanıcının kararı; denemede şehir düzeyinde nötr bir yer)")
            S = veri.kur(vid, o["saglayici"], o["konum"], float(o["enlem"]), float(o["boylam"]), o.get("saat-dilimi") or "Europe/Istanbul",
                         float(o["tazelik"]) if isinstance(o.get("tazelik"), str) else None, o.get("kullanim") or "kurum", bool(o.get("ustune")))
            print(f"yazıldı: videos/{vid}/veri.json · {S['kaynak']['ad']} · {S['konum']['ad']} ({S['konum']['enlem']}, {S['konum']['boylam']}) · lisans {S['lisans']}")
            return
        v = O.load(vid)
        if alt == "cek":
            r = veri.cek(vid)
            v = O.load(vid)
            if not r["yeni"]:
                print(f"yeni görüntü yok: {r['neden']}. Film {r['secili'] or '—'} ile çizilir.")
                return
            x = r["kayit"]
            print(f"✅ anlık görüntü {x['kimlik']} · {x['zaman_yerel']} · {x['istek']['url']}\n   sha256 {x['ham']['sha256']} · {x['ham']['bayt']} bayt"
                  + (f" · kaynak güncellemesi {x['kaynak']['guncelleme']}" if x["kaynak"].get("guncelleme") else ""))
            for d in x["degerler"].values():
                print(f"   {d['ad']}: {d['metin']} {d['birim']}" + (f" ({d['pencere']}, {d.get('zaman_yerel', '')})" if d.get("pencere") else
                                                                    (f" ({d['zaman_yerel']})" if d.get("zaman_yerel") else "")))
            if r.get("paylasilan"):
                print(f"   kaynağa istek gönderilmedi: aynı adresin süresi dolmamış görüntüsü {r['paylasilan']} filminde (ortak önbellek); aynı yanıt kopyalandı")
            print(f"   atıf: {x['atif']} → kaynaklar.md (V satırları ✅)" + (", yayin.md" if (v.dir / "yayin.md").exists() else ""))
            print(f"   önceki görüntü: {r['onceki'] or '—'} · film artık {x['kimlik']} ile çizilir (görüntü değişti: kaba kurgu ve kareler yeniden çizilmeli)")
            if o.get("ciz"):
                for k in _veri_kareleri(v, x):
                    print(f"   kanıt karesi: {k}")
            return
        if alt == "sec":
            if not pos:
                raise SystemExit("Kullanım: ./st veri <id> sec <kimlik|son>")
            x = veri.sec(vid, pos[0])
            print(f"seçili: {x['kimlik']} · {x['zaman_yerel']} · " + "; ".join(f"{d['ad']} {d['metin']} {d['birim']}" for d in x["degerler"].values()))
            if o.get("ciz"):
                for k in _veri_kareleri(O.load(vid), x):
                    print(f"   kanıt karesi: {k}")
            return
        if alt == "liste":
            sk = veri.secim(v)
            for x in veri.anliklar(v):
                print(f"{'→' if x['kimlik'] == sk else ' '} {x['kimlik']} · {x['zaman_yerel']} · sha256 {x['ham']['sha256'][:12]} · "
                      + "; ".join(f"{d['ad']} {d['metin']} {d['birim']}" for d in x["degerler"].values()))
            if not veri.anliklar(v):
                print(f"anlık görüntü yok: ./st veri {vid} cek")
            return
        if alt == "kare":
            x = veri.secili(v)
            if not x:
                raise SystemExit(f"anlık görüntü yok: ./st veri {vid} cek")
            for k in _veri_kareleri(v, x):
                print(f"kanıt karesi ({x['kimlik']}): {k}")
            return
        if alt == "denetle":
            S = veri.sozlesme(v)
            sat = veri.sorunlar(S) + [("✅" if ok else "❌", f"{a}{(': ' + m) if m else ''}") for a, ok, m in veri.dogrula(v)] + veri.kod_denetimi(v)
            for d_, m in sat:
                print(f"{d_} {m}")
            x = veri.secili(v)
            kd = veri.depo(v) / x["kimlik"] / "kareler" if x else None
            for png in sorted(kd.glob("*.png")) if kd and kd.exists() else []:
                E = veri.ekran_denetimi(v, png)
                if E["ocr"]:
                    sor = E["eksik"] + ([] if E["atif"] else ["atıf"])
                    print(f"{'❌' if sor else '✅'} [{png.stem}] ekranda: {' / '.join(E['okunan'])}" + (f" · eksik: {', '.join(sor)}" if sor else ""))
            if any(d_ == "❌" for d_, _ in sat):
                raise SystemExit(1)
            return
        raise SystemExit(f"Bilinmeyen alt komut: {alt} (kur, cek, sec, liste, kare, denetle)")
    except veri.VeriHatasi as e:
        print(f"❌ {e}", file=sys.stderr)
        raise SystemExit(e.kod) from None


def cmd_toplu(vid=None, *args):
    """Kişisel etki filmi: şablon filmden (veri_sablonu.json) her satıra kendi verisiyle film. Ayrıntı: README → Kişisel etki filmi.
    Kişisel veri bu bilgisayarda kalır; günlükte kimlik ve satır numarası görünür, ad ve değer görünmez."""
    import kisisel
    if not vid:
        raise SystemExit("Kullanım: ./st toplu <id> --veri <dosya.csv|json> [--esleme alan=Sütun,…] [--format F] [--satir K1,K2] [--paralel N] [--esanli N]\n"
                         "          ./st toplu <id> kur · sablon · denetle|onizle --veri <dosya> [--satir K] · liste · karar <alan> \"metin\" · sil <çalışma|veri:<dosya>>")
    alt = args[0] if args and not args[0].startswith("--") else None
    pos, o = opts(args[1:] if alt else args, "veri", "esleme", "format", "satir", "paralel", "esanli", "crf")
    v = O.load(vid)
    if alt == "kur":   # şablon iskeleti: kimlik + ad (sığdırmalı) + TEST örneği; alanları film yazar (README → Kişisel etki filmi)
        if kisisel.var_mi(v):
            raise SystemExit(f"zaten var: videos/{vid}/{kisisel.SABLON}")
        kisisel.dosya(v).write_text(json.dumps(kisisel.iskelet(v), ensure_ascii=False, indent=1) + "\n")
        print(f"yazıldı: videos/{vid}/{kisisel.SABLON} (alanları, yazi ve kisi_isareti'ni filme göre düzenle; sahne: useKisi('{vid}'))")
        return
    if not kisisel.var_mi(v):
        raise SystemExit(f"{vid}: kişisel film şablonu yok (videos/{vid}/veri_sablonu.json; ./st toplu {vid} kur; README → Kişisel etki filmi)")
    S = kisisel.sablon(v)
    D = kisisel.dizin(v)

    def veri_yolu():
        if not isinstance(o.get("veri"), str):
            raise SystemExit("--veri <dosya.csv|json> gerekli (panelden yüklenen dosyalar videos/<id>/toplu/veri/ altında)")
        p = Path(o["veri"])
        for aday in (p, O.ROOT / p, D / "veri" / p):
            if aday.exists():
                return aday.resolve()
        raise SystemExit(f"veri dosyası yok: {p.name}")

    def esleme():
        E = O.jload(D / "esleme.json") if (D / "esleme.json").exists() else {}
        for parca in str(o.get("esleme") or "").split(","):
            if "=" in parca:
                k, c = parca.split("=", 1)
                E[k.strip()] = c.strip()
        return E

    satirlar = [s for s in str(o.get("satir") or "").split(",") if s and s != "True"] or None
    if alt == "sablon":
        for d_, m in kisisel.sablon_sorunlari(S, v) or [("✅", "şablon geçerli")]:
            print(f"{d_} {m}")
        for k, a in S["alanlar"].items():
            yer = "ekranda" if a.get("ekranda") else ("sahnede" if a.get("sahne") else "sahneye gitmez")
            print(f"  {k:10} {a['tur']:7} {'zorunlu' if a.get('zorunlu') else 'isteğe bağlı':12} {yer:14} · {a.get('ad', k)}"
                  + (f" · seçenekler: {', '.join(a['secenekler'].values())}" if a.get("secenekler") else ""))
        eksik = kisisel.karar_eksikleri(S)
        print("kurum verisi kararları (kullanıcının): " + ("tamam" if not eksik else "eksik: " + "; ".join(eksik)))
        kisisel.esitle(v)
        return
    if alt == "karar":   # kullanıcının kararı (kaynak, izin, ekranda, gonderim, saklama); Claude yazmaz
        if len(pos) < 1 or pos[0] not in kisisel.KARAR_ALANLARI:
            raise SystemExit(f"./st toplu {vid} karar <{'|'.join(kisisel.KARAR_ALANLARI)}> \"metin\"")
        S.setdefault("kurum_verisi", {})[pos[0]] = " ".join(pos[1:]).strip() or None
        kisisel.dosya(v).write_text(json.dumps(S, ensure_ascii=False, indent=1) + "\n")
        print(f"kaydedildi: kurum_verisi.{pos[0]}")
        return
    if alt == "liste":
        for c in kisisel.calismalar(v):
            R = O.jload(c / "rapor.json")
            print(f"{c.name} · {R['dosya']} · {'TEST' if R['test'] else 'kurum verisi'} · {R['uretilen']} film · {len(R['atlanan'])} atlandı · "
                  f"{R.get('hatali', 0)} hata · film başına {R.get('film_basina_sn') or 0:.1f} sn" + ("" if R.get("bitti") else " · sürüyor"))
        for p in kisisel.veri_dosyalari(v):
            print(f"veri: {p.name} ({p.stat().st_size} bayt)")
        return
    if alt == "sil":   # kişisel çıktıları ya da veri dosyasını siler (kullanıcının kararı: saklama süresi)
        if not pos:
            raise SystemExit(f"./st toplu {vid} sil <çalışma|veri:<dosya>|onizleme>")
        hedef = D / "veri" / pos[0][5:] if pos[0].startswith("veri:") else D / pos[0]
        if not hedef.exists() or D.resolve() not in hedef.resolve().parents:
            raise SystemExit(f"yok: {pos[0]}")
        if hedef.is_dir():
            shutil.rmtree(hedef)
        else:
            hedef.unlink()
        print(f"silindi: toplu/{hedef.relative_to(D)}")
        return
    if alt == "denetle":
        H = kisisel.hazirla(v, veri_yolu(), esleme(), satirlar)
        g = [x for x in H["satirlar"] if x["kisi"]]
        print(f"{H['dosya']} · {len(H['satirlar'])} satır · {len(g)} geçerli · {'TEST verisi' if H['test'] else 'kurum verisi'}")
        print("eşleme: " + ", ".join(f"{k} ← {c}" for k, c in H["esleme"].items()) + (f" · eşlenmeyen alan: {', '.join(H['eslenmeyen'])}" if H["eslenmeyen"] else "")
              + (f" · kullanılmayan sütun: {', '.join(H['kullanilmayan'])}" if H["kullanilmayan"] else ""))
        for x in H["satirlar"]:
            print(f"  satır {x['no']}{' · ' + x['kimlik'] if x['kimlik'] else ''}: " + ("geçerli" if x["kisi"] else "atlanacak: " + "; ".join(x["nedenler"])))
        engel = kisisel.onay_engeli(v, H)
        if engel:
            print("⛔ " + engel)
        return
    if alt == "onizle":   # ilk geçerli satırın (ya da --satir) kanıt karesi her format için: panelin görsel önizlemesi
        H = kisisel.hazirla(v, veri_yolu(), esleme(), satirlar)
        x = next((x for x in H["satirlar"] if x["kisi"]), None)
        if not x:
            raise SystemExit(f"geçerli satır yok: ./st toplu {vid} denetle --veri …")
        hedef = D / "onizleme"
        shutil.rmtree(hedef, ignore_errors=True)
        kare = kisisel.kanit_karesi(v)
        kareler = {}
        for fmt in fmts(v, o):
            files = render_frames(v, [kare], hedef / "_ciz" / fmt, fmt, props={"kisi": {**x["kisi"], "film": v.id}})
            files[kare].replace(hedef / f"{fmt}.png")
            kareler[fmt] = f"{fmt}.png"
        shutil.rmtree(hedef / "_ciz", ignore_errors=True)
        (hedef / "onizleme.json").write_text(json.dumps({"kimlik": x["kimlik"], "satir": x["no"], "dosya": H["dosya"], "sha256": H["sha256"], "kare": kare,
                                                        "kareler": kareler, "gecerli": sum(1 for y in H["satirlar"] if y["kisi"]),
                                                        "atlanan": sum(1 for y in H["satirlar"] if not y["kisi"]), "test": H["test"],
                                                        "engel": kisisel.onay_engeli(v, H), "zaman": dt.datetime.now().isoformat(timespec="seconds")},
                                                       ensure_ascii=False, indent=1))
        print(f"önizleme: satır {x['no']} · {x['kimlik']} → toplu/onizleme/ ({', '.join(kareler)})")
        return
    if alt:
        raise SystemExit(f"bilinmeyen alt komut: {alt}")
    taban = {k: x for k, x in (_veri_props(v) or {}).items() if k != "kisi"}   # canlı veri de varsa seçili görüntü
    R = kisisel.toplu(v, veri_yolu(), taban, esleme(), fmts(v, o) if o.get("format") else None, satirlar,
                      int(o.get("paralel") or 1), int(o["esanli"]) if o.get("esanli") else None, int(o.get("crf") or 18))
    print(f"\nrapor: {(kisisel.dizin(v) / R['calisma'] / 'rapor.md').relative_to(O.ROOT)}")
    print(f"sonuç: {R['uretilen']} film · {len(R['atlanan'])} satır atlandı · {R.get('hatali', 0)} çizim hatası"
          + (f" · film başına {R['film_basina_sn']:.1f} sn (etkin {R['etkin_sn']:.1f} sn) · paket {R.get('paket_sn', 0):.1f} sn · toplam {R['toplam_sn']:.1f} sn"
             if R.get("film_basina_sn") else ""))
    kotu = [c for c in R["cikti"] if c["durum"] != "tamam" or (c.get("ocr") or {}).get("durum") == "❌"]
    goz = [c for c in R["cikti"] if c["durum"] == "tamam" and (c.get("ocr") or {}).get("durum") in ("⚠️", "👁")]
    if goz:
        print("⚠️ göz bakmalı (yazı tanıma tam doğrulayamadı): " + ", ".join(f"{c['kimlik']} [{c['format']}]" for c in goz))
    if kotu:
        print("❌ yazısı ekranda okunmayan ya da çizilemeyen: " + ", ".join(f"{c['kimlik']} [{c['format']}]" for c in kotu))
        raise SystemExit(1)


# ---------------------------------------------------------------- stüdyo
def cmd_yapim(vid, *args):
    """Yapım filmi ("nasıl yapıldı", 15 sn): filmin kendi kayıtlarından (yollar ve seçilen, kılavuz kipi, Blender geçişleri, inceleme turları,
    yapay zekâ kaynağı, kapılar) → ../cikti/<id>_yapim.mp4 (pipeline/yapim.py). --plan: yalnız hangi bölümlerin gireceği; --onizle: kılavuz
    kipinde tek kare (panelin önizlemesi)."""
    import yapim
    _, o = opts(args, "format", "cikti")
    v = O.load(vid)
    if o.get("onizle"):   # panelin görsel önizlemesi: kılavuz kipinde tek kare (Blender: kil geçişi)
        print(f"önizleme: {yapim.onizle(v, o.get('format')).relative_to(O.ROOT)}")
        return
    if o.get("plan"):
        P = yapim.plan(v, o.get("format"))
        for b in P["bolumler"]:
            print(f"  {b['tur']:<9} {b['kare'] / yapim.FPS:4.1f} sn  {b['aciklama']}")
        if P["eksik"]:
            print(f"  kaydı olmayan (girmez): {', '.join(P['eksik'])}")
        print(f"  tahmini süre ~{yapim.tahmini_sure(v) // 60} dk {yapim.tahmini_sure(v) % 60} sn")
        return
    K = yapim.uret(v, o.get("format"), o.get("cikti"))
    print((yapim.dizin(v) / "olcum.md").read_text())
    print(f"yapım filmi: {K['cikti']} · {K['sure_sn']} sn")
    if any(r["durum"] == "❌" for r in K["olcum"]):
        raise SystemExit(1)


def cmd_referans(path, ad=None):
    src = Path(path).expanduser().resolve()
    ad = ad or re.sub(r"[^a-z0-9_]+", "_", src.stem.lower()).strip("_")
    run([PY, "-I", "pipeline/referans.py", src, O.KANAL / "referans" / ad])


def cmd_panel(*args):
    """Tarayıcıda açılan kontrol paneli (yalnız bu bilgisayar)."""
    _, o = opts(args, "port")
    cmd = [PY, "-I", str(O.ROOT / "panel" / "sunucu.py"), "--port", str(o.get("port", 4777))]
    if not o.get("acma"):
        cmd.append("--ac")
    subprocess.run(cmd, cwd=O.ROOT)


# 3B katman (Three.js): kare t'nin saf fonksiyonu olmalı (kural 8). Çizim döngüsü, saat ve CDN'den yükleme iki motorda da aranır.
UC_YASAK = re.compile(r"\buseFrame\s*\(|setAnimationLoop|requestAnimationFrame|\bnew\s+(?:THREE\.)?(?:Clock|Timer)\s*\(|getElapsedTime|"
                      r"\.getDelta\s*\(|\bstate\.clock\b|import\s*\{[^}]*\bCanvas\b[^}]*\}\s*from\s*['\"]@react-three/fiber['\"]|"
                      r"(?:cdn\.jsdelivr\.net|unpkg\.com|esm\.sh|cdnjs\.cloudflare\.com|skypack\.dev)[^'\"]*three")


def _uc_dosyalari(v=None) -> list[Path]:
    """3B taramasının dosyaları: HyperFrames'te yazılan HTML/JS (yerel kitaplıklar hariç); Remotion'da videonun kodu + kit (video yoksa src/)."""
    if v is not None and v.motor == "hyperframes":
        import hf
        return [p for p in hf.kaynaklar(v) if p.suffix in (".html", ".js", ".mjs") and "assets/lib" not in str(p)]
    kok = [v.kod_dizini, O.ROOT / "src" / "lib" / "uc"] if v is not None else [O.ROOT / "src"]
    return [p for k in kok if k.exists() for p in sorted(k.rglob("*.ts*"))]


def uc_denetle(v=None) -> list[str]:
    """3B katman bulguları: yasak kalıplar (yorum satırları hariç) ve HyperFrames'te zamana bağlanmamış sahne."""
    bulgu = []
    for p in _uc_dosyalari(v):
        for i, ln in enumerate(p.read_text().splitlines(), 1):
            if UC_YASAK.search(ln) and not ln.lstrip().startswith(("//", "*", "/*")):
                bulgu.append(f"{p.relative_to(O.ROOT)}:{i}: {ln.strip()[:100]}")
    if v is not None and v.motor == "hyperframes" and v.uc:
        metin = "".join(p.read_text() for p in _uc_dosyalari(v))
        if "zamanaBagla(" not in metin and "hf-seek" not in metin:
            bulgu.append(f"hf/{v.id}: 3B sahne HyperFrames zamanına bağlı değil (uc.js → zamanaBagla(ciz) ya da 'hf-seek' dinleyicisi)")
    return bulgu


def cmd_tip(vid=None):
    """Sahne kodu denetimi: Remotion'da TypeScript, HyperFrames videosunda hyperframes check (her format), Blender'da sahne taraması.
    3B katman (Three.js) her motorda ayrıca taranır: çizim döngüsü, saat, CDN (uc_denetle)."""
    import olc
    v = O.load(vid) if vid else None
    # yazı güvenli alanda (statik; uyarır, tip denetimini düşürmez): ortak altyazı bandı ve sahne kodunun güvenli alanı okuması
    for d, m in (olc.guvenli_denetimi(v) if v is not None else [olc.altyazi_bandi(f) for f in O.FORMATLAR]):
        print(f"{d} yazı güvenli alanda: {m}")
    uc = uc_denetle(v)
    niyet_kotu = False
    if v is not None and v.niyetli:  # niyetli altyazı: veri taze, sahne kodu bileşeni çiziyor, ortak Captions yok
        import niyet
        taze, neden = niyet.tazelik(v)
        kod = niyet.kod_kullaniyor(v)
        print(f"{'✅' if taze else '❌'} niyetli altyazı verisi: {neden}")
        print("✅ sahne kodu niyetli altyazıyı çiziyor" if kod else
              "❌ niyetli altyazı seçili ama sahne kodu çizmiyor: Remotion <NiyetliAltyazi t={t} veri={TL.niyet} />, "
              "HyperFrames niyetliAltyazi(kok) (assets/lib/niyet/niyet.js; hf/CLAUDE.md → Niyetli altyazı)")
        niyet_kotu = not (taze and kod)
    if uc:
        print("❌ 3B katman: çizim döngüsü, saat ya da CDN'den yükleme (kare t'nin saf fonksiyonu olmalı; kit src/lib/uc, hf/CLAUDE.md → 3B katman):\n  "
              + "\n  ".join(uc))
    elif v is None or v.uc:
        print("✅ 3B katman taraması temiz")
    if v is not None and v.uc and v.motor != "hyperframes":  # hareket bulanıklığı her örnekte ayrı bir WebGL tuvali açar
        b = {**((v.gorunus_secimi or {}).get("bitis") or {}), **(v.script.get("bitis") or {})}
        if (b.get("bulaniklik") or 0) > 1:
            print(f"⚠️ 3B katman + hareket bulanıklığı ({b['bulaniklik']} örnek): Sahne3B her örnekte yeniden çizilir (çizim süresi ×{b['bulaniklik']}). "
                  "Gerekmiyorsa script.json → bitis.bulaniklik: 0 ya da Sahne3B'yi Bitis'in dışına al.")
    veri_kotu = False
    if v is not None:
        import veri
        if veri.var_mi(v):  # canlı veri: sözleşme, seçili görüntü dondurulmuş, kod veriyi seçili görüntüden okur, çizimde ağ yok
            S = veri.sozlesme(v)
            sat = [(d_, f"veri.json: {m}") for d_, m in veri.sorunlar(S)]
            x = veri.secili(v)
            sat.append(("✅", f"anlık görüntü {x['kimlik']} ({x['zaman_yerel']})") if x else ("❌", f"anlık görüntü yok: ./st veri {v.id} cek"))
            sat += [(d_, f"dondurma {a}: {m}") for a, ok, m in veri.dogrula(v) if not ok for d_ in ("❌",)]
            sat += veri.kod_denetimi(v)
            for d_, m in sat:
                print(f"{d_} canlı veri: {m}")
            veri_kotu = any(d_ == "❌" for d_, _ in sat)
        import kisisel
        if kisisel.var_mi(v):  # kişisel film: şablon sözleşmesi, sahne kodu kişi verisini useKisi'den okur, çizimde ağ yok (kurum verisi notları isteğe bağlı)
            S = kisisel.sablon(v)
            sat = [(d_, f"veri_sablonu.json: {m}") for d_, m in kisisel.sablon_sorunlari(S, v)] or [("✅", "veri_sablonu.json geçerli")]
            sat += kisisel.kod_denetimi(v)
            for d_, m in sat:
                print(f"{d_} kişisel film: {m}")
            veri_kotu = veri_kotu or any(d_ == "❌" for d_, _ in sat)
    if v is not None:
        import takip
        if takip.secili(v):  # kamera takibi: çözüm dondurulmuş, hata ≤ hedef, zemin, çekim formatla aynı oranda; sahne katmanları kuruyor mu
            sat = [("✅" if ok else "❌", f"{ad}: {d_}") for ok, ad, d_ in takip.denetle(v)]
            if v.motor == "blender":
                kod = (O.ROOT / "blender" / v.id / "sahne.py").read_text() if (O.ROOT / "blender" / v.id / "sahne.py").exists() else ""
                ust = "\n".join(p.read_text() for p in v.kod_dizini.rglob("*.tsx")) if v.kod_dizini.exists() else ""
                sat.append(("✅", "sahne takip kamerasını ve katmanları kuruyor (takip.kamera, takip.katmanlar)") if "takip.kamera(" in kod and
                           "takip.katmanlar(" in kod else ("❌", "sahne takip.kamera() ve takip.katmanlar() çağırmıyor (blender/CLAUDE.md → Kamera takibi)"))
                sat.append(("✅", "üst katman çekimle birleştiriyor (<TakipBirlesim>)") if "<TakipBirlesim" in ust else
                           ("⚠️", "üst katmanda <TakipBirlesim> yok: plaka çekimsiz çizilir (src/lib/takip)"))
            for d_, m in sat:
                print(f"{d_} kamera takibi: {m}")
            veri_kotu = veri_kotu or any(d_ == "❌" for d_, _ in sat)
    if v is not None:
        import gecis
        if gecis.var_mi(v):  # gölgelendirici kesimleri (6a): tanım temiz, kodda <Kesim ad>, kod lib/gecis'i içe aktarıyor
            gecis.esitle(v)
            sat = [(d_, m) for d_, m in gecis.sorunlar(v) if d_ == "❌"] + gecis.kod_denetimi(v)
            for d_, m in sat:
                print(f"{d_} geçiş: {m}")
            veri_kotu = veri_kotu or any(d_ == "❌" for d_, _ in sat)
    if v is not None:
        import plaka
        if plaka.var_mi(v):  # karma film (6b): her sahne kendi motorunun denetimiyle (HyperFrames check, Blender tarama + kuru kurulum)
            plaka.esitle(v)
            sat = plaka.sorunlar(v)
            for d_, m in sat:
                print(f"{d_} karma: {m}")
            veri_kotu = veri_kotu or any(d_ == "❌" for d_, _ in sat) or bool(plaka.denetle(v))
    if v is not None and v.motor == "hyperframes":
        import hf
        if hf.denetle(v) or uc or niyet_kotu or veri_kotu:
            raise SystemExit(1)
        return
    if v is not None and v.motor == "blender":
        import blender
        if blender.denetle(v) or uc or niyet_kotu or veri_kotu:
            raise SystemExit(1)
        return
    r = subprocess.run(["npx", "tsc", "--noEmit", "-p", "."], cwd=O.ROOT, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    print("✅ tip denetimi temiz" if r.returncode == 0 else out[-4000:])
    if r.returncode or uc or niyet_kotu or veri_kotu:
        raise SystemExit(1)


def cmd_gecis(*args):
    """Gölgelendirici geçişleri (6a; gl-transitions 3.0.0): liste · onizle · uret · <id> durum|esitle|plaka (pipeline/gecis.py)."""
    import gecis
    pos, o = opts(args, "etiket", "format")
    alt = pos[0] if pos else "liste"
    if alt == "liste":
        L = gecis.kutuphane()
        et = str(o["etiket"]).lower() if isinstance(o.get("etiket"), str) else None
        satir = [g for g in L.values() if not et or et in [x.lower() for x in g["tags"]]]
        for g in satir:
            print(f"{g['name']:<26} {', '.join(g['tags']):<34} {g['license']:<13} {gecis.param_ozeti(g)}")
        etiketler = sorted({x for g in L.values() for x in g["tags"]})
        print(f"\n{len(satir)} geçiş" + (f" (etiket {et})" if et else f" · etiketler: {', '.join(etiketler)}") +
              f" · gl-transitions {gecis.SURUM}; çıkarılan: " + ", ".join(f"{a} ({n})" for a, n in gecis.cikarilan().items()))
        return
    if alt == "onizle":
        gecis.onizle(None if o.get("hepsi") else pos[1:] or None, yeniden=bool(o.get("yeniden")))
        return
    if alt == "uret":
        V = gecis.uret()
        print(f"✅ {len(V['gecisler'])} geçiş → {gecis.KUTUPHANE.relative_to(O.ROOT)} ({V['kaynak']}; lisanslar {V['lisanslar']}; "
              f"çıkarılan {', '.join(V['cikarilan'])})")
        return
    v = O.load(alt)
    if not gecis.var_mi(v):
        raise SystemExit(f"{v.id}: yapılandırılmış geçiş yok (script.json → shot.gecis = {{\"gl\": \"BookFlip\", \"kare\": 18, …}})")
    islem = pos[1] if len(pos) > 1 else "durum"
    if islem == "durum":
        gecis.durum(v)
    elif islem == "esitle":
        gecis.esitle(v)
        print(f"✅ public/{v.id}/gecis.json · {len(gecis.tanim_json(v))} kesim")
    elif islem == "plaka":
        for fmt in fmts(v, o):
            _gecis_hazir(v, fmt)
        gecis.durum(v)
    else:
        raise SystemExit("Kullanım: ./st gecis liste [--etiket E] | onizle <ad …>|--hepsi [--yeniden] | uret | <id> durum|esitle|plaka [--format F]")


def cmd_plaka(vid=None, *args):
    """Karma film (6b): sahne başına motor. durum [sahne] · ciz [sahne] [--format F] [--kalite taslak|tam] [--kareler 0,3.2s] · yeni <ad> --motor M
    --bas <işaret> --son <işaret> [--cizer eevee] [--saydam] (pipeline/plaka.py)."""
    import plaka
    if not vid:
        raise SystemExit("Kullanım: ./st plaka <id> durum|ciz|yeni …")
    pos, o = opts(args, "format", "kalite", "kareler", "motor", "bas", "son", "cizer")
    v = O.load(vid)
    alt = pos[0] if pos else "durum"
    if alt == "yeni":
        if len(pos) < 2 or not all(isinstance(o.get(k), str) for k in ("motor", "bas", "son")):
            raise SystemExit(f"Kullanım: ./st plaka {vid} yeni <ad> --motor hyperframes|blender|manim --bas <işaret> --son <işaret> [--cizer eevee] [--saydam]")
        plaka.yeni(v, pos[1], o["motor"], o["bas"], o["son"], o.get("cizer") if isinstance(o.get("cizer"), str) else None, bool(o.get("saydam")))
        return
    if not plaka.var_mi(v):
        raise SystemExit(f"{vid}: karma film değil (script.json → sahneler; motor remotion)")
    ad = pos[1] if len(pos) > 1 else None
    if alt == "durum":
        plaka.durum(v, ad)
    elif alt == "ciz":
        S = [S for S in plaka.sahneler(v) if not ad or S["ad"] == ad]
        if not S:
            raise SystemExit(f"Sahne yok: {ad}")
        for fmt in fmts(v, o):
            for x in S:
                kareler = parse_times(o["kareler"].split(","), v.fps) if o.get("kareler") else range(x["r0"], x["r1"])
                plaka.hazirla(v, [f for f in kareler if x["r0"] <= f < x["r1"]], fmt, {"kalite": o.get("kalite", "taslak")}, yalniz=x["ad"])
        plaka.durum(v, ad)
    else:
        raise SystemExit("Kullanım: ./st plaka <id> durum [sahne] | ciz [sahne] [--format F] [--kalite taslak|tam] [--kareler …] | yeni <ad> …")


def cmd_manim(vid=None, *args):
    """Karma filmin Manim sahnesi (6c): ./st manim <id> --sahne <ad> durum | ciz [--format F] | onizle [--format F] (pipeline/manim_kopru.py)."""
    import manim_kopru
    import plaka
    if not vid or "--sahne" not in args:
        raise SystemExit("Kullanım: ./st manim <id> --sahne <ad> durum | ciz [--format F] | onizle [--format F]")
    v = O.load(vid)
    S, P, kalan = _karma_sahnesi(v, args, "manim")
    pos, o = opts(kalan, "format")
    alt = pos[0] if pos else "durum"
    ok = manim_kopru.kurulu()
    if alt == "durum":
        print(f"Manim: {'kurulu ' + manim_kopru.SURUM if ok is True else ok}")
        plaka.durum(v, S["ad"])
    elif alt in ("ciz", "onizle"):
        for fmt in fmts(v, o):
            props = plaka.hazirla(v, range(S["r0"], S["r1"]), fmt, {}, yalniz=S["ad"])
            if alt == "onizle":
                d = plaka.ONBELLEK / v.id / S["ad"] / props["plaka"][S["ad"]]
                mp4 = plaka.ONBELLEK / v.id / S["ad"] / f"onizleme-{fmt}.mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(v.fps), "-start_number", str(S["r0"]), "-i", str(d / "p%05d.png"),
                                "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(mp4)], check=True)
                print(f"önizleme [{fmt}]: {mp4.relative_to(O.ROOT)}")
        plaka.durum(v, S["ad"])
    else:
        raise SystemExit("Kullanım: ./st manim <id> --sahne <ad> durum | ciz | onizle [--format F]")


def _karma_sahnesi(v, args, motor):
    """./st hf|blender <id> --sahne <ad> …: karma filmin sahnesi (yerel zamanlı Video) + kalan argümanlar."""
    import plaka
    args = list(args)
    i = args.index("--sahne")
    ad = args[i + 1] if i + 1 < len(args) else ""
    del args[i:i + 2]
    S = next((S for S in plaka.sahneler(v) if S["ad"] == ad), None)
    if S is None or S.get("motor") != motor:
        raise SystemExit(f"{v.id}: {motor} sahnesi yok: {ad} (./st plaka {v.id} durum)")
    if S["hata"]:
        raise SystemExit(f"sahne {ad}: {S['hata']}")
    return S, plaka.yerel(v, S), args


def cmd_hf(vid, *args):
    """HyperFrames CLI'yi videonun klasöründe çalıştırır (önce eşitleme). Örnek: ./st hf <id> lint · ./st hf <id> snapshot --at 1,4.5
    Karma filmin sahnesi: ./st hf <id> --sahne <ad> lint|check|snapshot … (sahnenin projesinde, yerel zamanla)."""
    import hf
    v = O.load(vid)
    if "--sahne" in args:
        _, P, args = _karma_sahnesi(v, args, "hyperframes")
        hf.esitle(P)
        if not args:
            raise SystemExit("Kullanım: ./st hf <id> --sahne <ad> <komut …>")
        r = hf.cli(P, list(args), check=False)
        if r.returncode:
            raise SystemExit(r.returncode)
        return
    if v.motor != "hyperframes":
        raise SystemExit(f"{vid} Remotion motorunda (script.json → motor)")
    hf.esitle(v)
    if not args:
        raise SystemExit("Kullanım: ./st hf <id> <komut …> (lint, check, snapshot, timeline, keyframes, inspect, catalog, add, docs, audio …)")
    r = hf.cli(v, list(args), check=False)
    if r.returncode:
        raise SystemExit(r.returncode)


def cmd_blender(vid, *args):
    """Blender videosunun plakaları ve sahnesi. durum: önbellek · plaka: çiz [--format F] [--kalite taslak|tam] [--kareler 0,30]
    (yoksa bütün kareler) · ac: sahneyi Blender arayüzünde aç [--format F] · temizle: güncel olmayan plaka kümelerini sil ·
    cizer cycles|eevee: çizeri değiştir (kullanıcı kararı: görüntü değişir, plakalar yeni kümelere çizilir)."""
    import blender
    v = O.load(vid)
    if "--sahne" in args:  # karma filmin Blender sahnesi (6b): durum · plaka [--format F] [--kalite K] · ac [--format F]
        import plaka
        S, P, kalan = _karma_sahnesi(v, args, "blender")
        pos, o = opts(kalan, "format", "kalite", "kareler")
        alt = pos[0] if pos else "durum"
        if alt == "durum":
            plaka.durum(v, S["ad"])
        elif alt == "plaka":
            for fmt in fmts(v, o):
                kareler = parse_times(o["kareler"].split(","), v.fps) if o.get("kareler") else range(S["r0"], S["r1"])
                plaka.hazirla(v, [f for f in kareler if S["r0"] <= f < S["r1"]], fmt, {"kalite": o.get("kalite", "taslak")}, yalniz=S["ad"])
            plaka.durum(v, S["ad"])
        elif alt == "ac":
            fmt = o.get("format") or v.formatlar[0]
            blender.surum_denetle(blender.surum(P))
            yol = plaka.ONBELLEK / v.id / f"veri-{S['ad']}-{fmt}.json"
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_text(json.dumps(blender.veri(P, fmt), ensure_ascii=False))
            sahne, ortam = S["kok"] / "sahne.py", None
            if blender.cizer(P) == "eevee":
                sahne, ortam = blender.EEVEE / "sahne.py", {**__import__("os").environ, "ST_SAHNE": str(sahne)}
            subprocess.Popen([blender.BLENDER, "--factory-startup", "--python", str(blender.CALISTIR), "--", "--sahne", str(sahne), "--veri", str(yol),
                              "--kalite", json.dumps(blender.kalite(P, "taslak")), "--ac"], cwd=O.ROOT, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True, env=ortam)
            print(f"Blender açılıyor: {v.id} · sahne {S['ad']} · {fmt} · {blender.cizer(P)} (yerel zaman; kamera görünümü)")
        else:
            raise SystemExit(f"Kullanım: ./st blender {vid} --sahne <ad> durum | plaka [--format F] [--kalite taslak|tam] | ac [--format F]")
        return
    pos, o = opts(args, "format", "kalite", "kareler")
    if v.motor != "blender":
        raise SystemExit(f"{vid} {v.motor} motorunda (script.json → motor)")
    alt = pos[0] if pos else "durum"
    if alt == "durum":
        blender.durum(v)
    elif alt == "plaka":
        kareler = parse_times(o["kareler"].split(","), v.fps) if o.get("kareler") else range(v.nframes)
        for fmt in fmts(v, o):
            kume, files = blender.plakalar(v, kareler, fmt, o.get("kalite", "taslak"))
            print(f"✅ [{fmt}] {len(files)} plaka hazır · out/_plaka/{vid}/{kume}/")
    elif alt == "ac":
        blender.ac(v, o.get("format"))
    elif alt == "cizer":
        yeni = pos[1] if len(pos) > 1 else ""
        if yeni not in blender.CIZERLER:
            raise SystemExit(f"Kullanım: ./st blender {vid} cizer {' | '.join(blender.CIZERLER)} (şimdiki: {blender.cizer(v)})")
        sc = json.loads((v.dir / "script.json").read_text())
        b = sc.setdefault("blender", {})
        if yeni == "cycles":
            b.pop("cizer", None)   # varsayılan: alan yazılmaz (eski filmlerle aynı parmak izi)
        else:
            b["cizer"] = yeni
        (v.dir / "script.json").write_text(json.dumps(sc, ensure_ascii=False, indent=2) + "\n")
        v = O.load(vid)
        print(f"çizer: {blender.cizer(v)} · plakalar yeni kümelere çizilir (eski kümeler önbellekte kalır, ./st blender {vid} temizle)")
        blender.durum(v)
    elif alt == "temizle":
        guncel = {blender.parmak_izi(v, f, k)[0] for f in v.formatlar for k in blender.KALITE}
        guncel |= {blender.yapim_kume(v, f, k)[0] for f in v.formatlar for k in blender.YAPIM_KIPLERI}   # yapım filminin güncel geçişleri
        silinen = [p for p in (blender.ONBELLEK / vid).iterdir() if p.is_dir() and p.name not in guncel]
        for p in silinen:
            shutil.rmtree(p)
        print(f"silinen plaka kümesi: {len(silinen)} (güncel kümeler korundu)")
    else:
        raise SystemExit("Kullanım: ./st blender <id> durum | plaka [--format F] [--kalite taslak|tam] [--kareler 0,30] | ac [--format F] | temizle"
                         " | cizer cycles|eevee")


def cmd_3b(*args):
    """3B model kütüphanesi: ara · al · ekle · liste · incele · kullan · onizle · katalog (pipeline/model3b.py)."""
    import model3b as M
    pos, o = opts(args, "kategori", "n", "url", "slug")
    alt, pos = (pos[0], pos[1:]) if pos else ("liste", [])
    kb = lambda b: f"{(b or 0) / 1024:.0f} KB"
    if alt == "ara":
        yerel = {b["slug"] for b in M.kutuphane()}
        sonuc = M.ara(" ".join(pos), o.get("kategori"), bool(o.get("hepsi")), int(o.get("n", 20)))
        for m in sonuc:
            print(f"{m['slug']:<34} {m['name'][:30]:<30} {m['triangles'] or 0:>7} üçgen {kb(m['file_size_bytes']):>7}  {m['category'] or '':<9} "
                  f"{m['pack_slug'] or ''}{'  ·ücretli' if m['tier'] != 'free' else ''}{'  ✓ kütüphanede' if m['slug'] in yerel else ''}")
            print(f"{'':<36}{(m['description'] or '')[:150]}")
        print(f"{len(sonuc)} sonuç" + ("" if sonuc else " (İngilizce sözcük dene: tent, crate, tree, car …)") + f" · katalog: {M.SITE}/assets/free")
    elif alt == "katalog":
        print(f"{len(M.katalog(yenile=True))} model (katalog yenilendi → {M.KATALOG.relative_to(O.ROOT)})")
    elif alt == "al":
        if not pos:
            raise SystemExit("Kullanım: ./st 3b al <slug> [--url <bağlantı>]")
        b = M.al(pos[0], o.get("url") if isinstance(o.get("url"), str) else None)
        if b:
            print(f"✅ {b['slug']} → {M.glb_yolu(b['slug']).relative_to(O.ROOT)} · {kb(b['bayt'])} · {b['indirme']}")
    elif alt == "ekle":
        if not pos:
            raise SystemExit("Kullanım: ./st 3b ekle <dosya.glb> [--slug S]")
        b = M.ekle(pos[0], o.get("slug") if isinstance(o.get("slug"), str) else None)
        print(f"✅ {b['slug']} → {M.glb_yolu(b['slug']).relative_to(O.ROOT)} · {kb(b['bayt'])}")
    elif alt == "liste":
        L = M.kutuphane()
        for b in L:
            k = (b.get("glb") or {}).get("kutu") or {}
            print(f"{b['slug']:<34} {b['name'][:30]:<30} {'×'.join(f'{x:g}' for x in k.get('boyut', [])) + ' m':<20} "
                  f"{', '.join(b['filmler']) or '—'}")
        print(f"{len(L)} model · {M.KUTUPHANE.relative_to(O.ROOT)}" if L else
              f"Kütüphane boş. Ara: ./st 3b ara <sözcük> · indir: ./st 3b al <slug> · tarayıcıdan: ./st 3b ekle <dosya.glb>")
    elif alt == "incele":
        if not pos:
            raise SystemExit("Kullanım: ./st 3b incele <slug|dosya.glb>")
        yol = Path(pos[0]).expanduser() if pos[0].endswith(".glb") else M.glb_yolu(pos[0])
        if not yol.exists():
            raise SystemExit(f"yok: {yol} (önce ./st 3b al {pos[0]})")
        g = M.glb_bilgi(yol)
        k = g["kutu"] or {}
        print(f"{yol.name} · {kb(yol.stat().st_size)}")
        print(f"  boyut (x × y × z): {' × '.join(f'{x:g}' for x in k.get('boyut', []))} m · taban y = {k.get('min', [0, 0])[1]:g} · "
              f"orta {k.get('merkez')}  (+Y yukarı, +Z ön; <Model> varsayılan olarak tabanın ortasını orijine koyar)")
        print(f"  {g['ucgen']} üçgen · {g['ag']} ağ · {g['dugum']} düğüm · malzeme: {', '.join(g['malzeme']) or '—'}")
        doku = f" · {g['doku']} doku" if g["doku"] else ""
        print(f"  renk: {'köşe rengi (COLOR_0)' if g['kose_rengi'] else '—'}{doku} · iskelet {g['iskelet']} · "
              f"çözücü: {', '.join(M.cozucu_gerekir(g)) or 'gerekmez'} · uzantılar: {', '.join(g['uzantilar']) or '—'}")
        print("  animasyon: " + (", ".join(f"{a['ad']} ({a['sure']:g} sn)" for a in g["animasyon"]) or "yok"))
    elif alt == "kullan":
        if len(pos) < 2:
            raise SystemExit("Kullanım: ./st 3b kullan <id> <slug> [<slug> …]")
        v = O.load(pos[0])
        for b in M.kullan(pos[0], pos[1:]):
            print(f"✅ {b['slug']} → public/{v.id}/varliklar/3b/{b['slug']}.glb · varliklar.md ✅")
            print("   " + M.kullanim_ornegi(v, b))
    elif alt == "onizle":
        if not pos:
            raise SystemExit("Kullanım: ./st 3b onizle <slug> [--yeniden]")
        s = pos[0]
        hedef = M.KUTUPHANE / f"{s}.png"
        if hedef.exists() and not o.get("yeniden"):
            print(f"önizleme var: {hedef.relative_to(O.ROOT)} (--yeniden)")
            return
        if not M.glb_yolu(s).exists():
            raise SystemExit(f"kütüphanede yok: {s} (./st 3b al {s})")
        M.cozucu_hazirla()
        gecici = O.ROOT / "public" / "uc" / "_onizleme" / f"{s}.glb"
        gecici.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(M.glb_yolu(s), gecici)
        try:
            dosya = render_jobs([{"comp": "ModelOnizleme", "out": O.ROOT / "out" / "_3b" / s, "frames": [0], "props": {"src": f"uc/_onizleme/{s}.glb"},
                                  "gl": O.UC_GL}])[0][0]
        finally:
            gecici.unlink(missing_ok=True)
        shutil.move(str(dosya), hedef)
        shutil.rmtree(O.ROOT / "out" / "_3b" / s, ignore_errors=True)
        print(f"✅ önizleme: {hedef.relative_to(O.ROOT)}")
    else:
        raise SystemExit("Kullanım: ./st 3b ara | al | ekle | liste | incele | kullan | onizle | katalog  (./st yardim)")


def _uretim_ornegi(v, x: dict) -> str:
    f = x["yayin"]
    if v.motor == "hyperframes":
        return (f'<video src="{f}" muted playsinline …>   // hf/{v.id}/index.html (medya kuralları: hyperframes-core)' if x["tur"] == "video"
                else f'<img src="{f}" alt="">   // hf/{v.id}/index.html')
    if v.motor == "blender":
        return f'kit.varlik("{f[len("varliklar/"):]}")   // blender/{v.id}/sahne.py (doku ya da arka plan)'
    if x["tur"] == "video":
        return f"<OffthreadVideo src={{staticFile('{v.id}/{f}')}} muted style={{{{width: '100%', height: '100%', objectFit: 'cover'}}}} />   // <Sequence> içinde"
    if x["tur"] in ("gorsel", "stok") and Path(f).suffix in (".png", ".jpg", ".webp", ".svg"):
        return f"<Img src={{staticFile('{v.id}/{f}')}} style={{{{width: '100%', height: '100%', objectFit: 'cover'}}}} />"
    if x["tur"] == "anlatim":
        return f"./st ses {v.id} (bütün parçalar hazırsa anlatım birleştirilir, kelime zamanları Whisper ile hizalanır)"
    if x["tur"] == "ses":
        return f"ses.py → efekt olarak '{f}' (işarete bağlı; kural 9)"
    return f"staticFile('{v.id}/{f}')"


def cmd_uret(*args):
    """Üretim deposu (pipeline/uretim.py): Magnific'le üretilen ya da bulunan varlıklar, kredi bekçisi, bakiye."""
    import uretim as U
    pos, o = opts(args, "url", "tur", "model", "arac", "istem", "kredi", "parametre", "kaynak-kare", "tahmin", "kalan", "an", "toplam", "plan", "put", "is")
    alt, pos = (pos[0], pos[1:]) if pos else ("", [])
    s = lambda k: o.get(k) if isinstance(o.get(k), str) else None  # noqa: E731
    if alt == "al":
        if len(pos) < 2 or not s("url") or not s("tur"):
            raise SystemExit("Kullanım: ./st uret al <id> <ad> --url <bağlantı> --tur gorsel|video|ses|3b|stok|anlatim --model <m> --arac <araç> --istem \"…\" "
                             "--kredi <n> [--parametre '<json>'] [--kaynak-kare <dosya>] [--insan] [--etiket] [--uyum] [--ses-kalsin]")
        try:
            par = json.loads(s("parametre")) if s("parametre") else {}
        except json.JSONDecodeError as e:
            raise SystemExit(f"--parametre geçerli JSON değil: {e}")
        x = U.al(pos[0], pos[1], s("url"), s("tur"), s("model") or "", s("arac") or "", s("istem") or "", int(float(s("kredi") or 0)), par,
                 s("kaynak-kare"), bool(o.get("insan")), bool(o.get("etiket")), bool(o.get("uyum")), bool(o.get("ses-kalsin")))
        v = O.load(pos[0])
        ol = x["olcu"]
        boyut = f"{ol['en']}×{ol['boy']}" if ol.get("en") else f"{ol['bayt'] / 1e6:.1f} MB"
        print(f"✅ {x['ad']} → videos/{v.id}/{x['dosya']}" + (f" · public/{v.id}/{x['yayin']}" if x.get("yayin") else "") + f" · {boyut}"
              + (f" · {ol['sure']:g} sn" if ol.get("sure") else "") + (f" · {ol['fps']:g} kare/sn" if ol.get("fps") else "")
              + f" · sha256 {x['sha256'][:12]}… · {x['kredi']} kredi")
        for i in x["islem"]:
            print(f"   işlem: {i}")
        for u in x["uyari"]:
            print(f"   ⚠️ {u}")
        if x["etiket_gerekli"]:
            print(f"   etiket gerekli: kullanıldığı her vuruşta ekranda etiket (Remotion <Etiket>, HyperFrames .etiket) + script.json → etiketler "
                  f"[{{\"vurus\": …, \"metin\": \"Canlandırmadır\", \"varlik\": \"{x['ad']}\"}}]")
        print(("   varliklar.md ✅" if x.get("yayin") else "   uretim.json ✅ (anlatım parçası: motora kopyalanmaz, varliklar.md'ye girmez)")
              + " · kullanım: " + _uretim_ornegi(v, x))
        b = U.butce(v)
        print(f"   kredi: harcanan {b['harcanan']} / sınır {b['sinir']} · kalan {b['kalan']}")
    elif alt == "liste":
        if not pos:
            raise SystemExit("Kullanım: ./st uret liste <id>")
        v = O.load(pos[0])
        D = U.yukle(v)
        kul = U.kullanim(v)
        for x in D["varliklar"]:
            ol = x.get("olcu") or {}
            print(f"{x['ad']:<22} {U.TUR_AD.get(x['tur'], x['tur']):<10} {(x.get('model') or '—')[:26]:<26} {x.get('kredi', 0):>6} kredi  "
                  f"{(str(ol['en']) + '×' + str(ol['boy'])) if ol.get('en') else '':<10} {'etiket ' if x.get('etiket_gerekli') else ''}"
                  f"→ {', '.join(kul.get(x['ad']) or []) or 'kullanılmıyor'}")
        b = U.butce(v)
        print(f"{len(D['varliklar'])} varlık · harcanan {b['harcanan']} / sınır {b['sinir']} kredi · kalan {b['kalan']}"
              + (f" · {len(D['silinen'])} silinmiş" if D["silinen"] else ""))
        if D["denetim"]:
            d = D["denetim"][-1]
            print(f"son bakiye okuması: {d['kalan']} kredi ({d['an']}, {d['tarih'][:16].replace('T', ' ')})")
    elif alt == "butce":
        if not pos:
            raise SystemExit("Kullanım: ./st uret butce <id> [--tahmin N] [--arac <araç>]")
        v = O.load(pos[0])
        t = int(float(s("tahmin"))) if s("tahmin") else None
        b = U.butce(v, t, s("arac"))
        print(f"kredi sınırı {b['sinir']} · harcanan {b['harcanan']} · kalan {b['kalan']}" + (f" · tahmin {t}" if t is not None else ""))
        if not b["ok"]:
            print(f"❌ sınır aşılıyor: kullanıcıya sor (tahmin {t} > kalan {b['kalan']}). Üretme; durum.md'de ne için kaç kredi gerektiğini yaz. "
                  "Sınırı yalnız kullanıcı yükseltir (panel: film sayfası → Yapay zekâ üretimleri).")
            raise SystemExit(3)
        if t is not None:
            print(f"✅ izin: bir üretim çağrısı{' (' + s('arac') + ')' if s('arac') else ''}, {U.IZIN_OMRU // 60} dk geçerli")
    elif alt == "sil":
        if len(pos) < 2:
            raise SystemExit("Kullanım: ./st uret sil <id> <ad>")
        x = U.sil(pos[0], pos[1])
        print(f"✅ silindi: {x['ad']} ({x.get('yayin') or x['dosya']}); harcama kaydı yerinde kalır")
    elif alt == "bakiye":
        if not s("kalan"):
            raise SystemExit("Kullanım: ./st uret bakiye [<id>] --kalan <credits.available> [--an bas|son|okuma] [--toplam N] [--plan P]")
        an = s("an") or "okuma"
        if an not in ("bas", "son", "okuma"):
            raise SystemExit("--an: bas | son | okuma")
        b = U.bakiye_kaydet(pos[0] if pos else None, int(float(s("kalan"))), an, int(float(s("toplam"))) if s("toplam") else None, s("plan"), s("is"))
        print(f"✅ bakiye {b['kalan']} kredi kaydedildi ({an}{', ' + pos[0] if pos else ''})")
    elif alt == "anlatim":
        if not pos:
            raise SystemExit("Kullanım: ./st uret anlatim <id>")
        v = O.load(pos[0])
        A = U.anlatim_durumu(v)
        if not A["magnific"]:
            raise SystemExit(f"{v.id}: anlatıcı Magnific değil (script.json → ses.kaynak = {v.ses.get('kaynak')}). Anlatıcı sesi kullanıcının kararıdır.")
        a = A["ayar"]
        print(f"Anlatıcı: Magnific · {a.get('ses_adi') or 'ses'} (voiceId {a['voice']}, model {a['model']}) · {len(A['parcalar'])} parça, "
              f"eksik {len(A['eksik'])} ({sum(len(p['metin']) for p in A['eksik'])} karakter)")
        if not A["eksik"]:
            print(f"✅ bütün parçalar dondurulmuş: ./st ses {v.id}")
            return
        print("Her parça için (metni AYNEN kullan; anahtar metinden hesaplanır):\n"
              f"  simulate_cost {{tool: audio_tts, arguments: {{text, model: {a['model']}, voiceId: {a['voice']}, source: catalog}}}} → "
              f"./st uret butce {v.id} --tahmin <kredi> --arac audio_tts → audio_tts (aynı argümanlar) → creations_wait →\n"
              f"  ./st uret al {v.id} anlatim_<anahtar> --url <bağlantı> --tur anlatim --model \"ElevenLabs {a['model']} · {a.get('ses_adi') or a['voice']}\" "
              "--arac audio_tts --istem \"<metin>\" --kredi <n>")
        for p in A["eksik"]:
            print(f"  anlatim_{p['anahtar']}  [{p['cumle']}]  {p['metin']}")
        print(f"Bitince: ./st ses {v.id}")
    elif alt == "yukle":
        if not pos or not s("put"):
            raise SystemExit("Kullanım: ./st uret yukle <dosya> --put <creations_request_upload bağlantısı>")
        print(f"✅ yüklendi (HTTP {U.yukle_put(pos[0], s('put'))}): sonra creations_finalize_upload")
    elif alt == "beyan":
        if not pos:
            raise SystemExit("Kullanım: ./st uret beyan <id>")
        v = O.load(pos[0])
        p = U.beyan_yaz(v)
        print(U.beyan_md(v))
        print(f"\n→ {p.relative_to(O.ROOT)} güncellendi" if p else "\n(yayin.md yok: ./st yayin bu bloğu yazar)")
    else:
        raise SystemExit("Kullanım: ./st uret al | liste | butce | sil | bakiye | anlatim | yukle | beyan  (./st yardim)")


def _goruntu_satiri(v, x: dict) -> str:
    import goruntu
    o = x["olcu"]
    tur = f"{o['en']}×{o['boy']}" + (f" · {o['sure']:g} sn · {o.get('kare')} kare" if x["tur"] == "video" else "")
    kisi = {True: f"kişi var · rıza {x.get('riza')}" + (f" → {x['cozum']}" if x.get("cozum") else ""), False: "kişi yok", None: "kişi bilinmiyor"}[x.get("kisi")]
    tur_ = " · ".join(filter(None, ["derinlik" if x.get("derinlik") else "", f"maske ({x['maske']['yontem']})" if x.get("maske") else "",
                                    ("kadraj " + ", ".join(f"{f} %{k['guvenli_oran'] * 100:.0f}" for f, k in x["kadraj"].items())) if x.get("kadraj") else ""]))
    return f"{x['ad']:<18} {x['tur']:<6} {goruntu.KAYNAKLAR.get(x['kaynak'], x['kaynak'])} · {tur} · {kisi}" + (f" · {tur_}" if tur_ else "")


def cmd_goruntu(*args):
    """Gerçek görüntü hattı (pipeline/goruntu.py): ekle, rıza, kadraj, liste, sil."""
    import goruntu as G
    pos, o = opts(args, "ad", "kaynak", "riza", "cozum", "bas", "son", "not", "format", "yakinlik", "hedef", "yumusak", "ozne")
    alt, pos = (pos[0], pos[1:]) if pos else ("", [])
    s = lambda k: o.get(k) if isinstance(o.get(k), str) else None  # noqa: E731
    f = lambda k: float(s(k)) if s(k) else None  # noqa: E731
    kisi = True if o.get("kisi") else (False if o.get("kisi-yok") else None)
    if alt == "ekle":
        if len(pos) < 2:
            raise SystemExit("Kullanım: ./st goruntu ekle <id> <dosya | stok:<ad> | uretim:<ad>> [--ad A] [--kaynak kendi|arsiv|acik] [--kisi | --kisi-yok] "
                             "[--riza evet|hayir|bilinmiyor] [--bas SN] [--son SN] [--not \"…\"] [--dokum-yok]")
        x = G.ekle(pos[0], pos[1], s("ad"), s("kaynak") or "kendi", s("riza"), kisi, f("bas"), f("son"), s("not") or "", not o.get("dokum-yok"))
        v = O.load(pos[0])
        print(f"✅ {_goruntu_satiri(v, x)}")
        print(f"   asıl videos/{v.id}/{x['asil']}" + (f" · ara videos/{v.id}/{x['ara']}" if x.get("ara") else "") + f" · motor public/{v.id}/{x['yayin']}"
              + f" · {x['sure_sn']} sn")
        for n in x.get("islem") or []:
            print(f"   işlem: {n}")
        if x["tur"] == "video":
            print(f"   kesmeler: {len(x['kesmeler'])}" + (" (" + ", ".join(f"{k['t']:g} sn" for k in x["kesmeler"][:8]) + ")" if x["kesmeler"] else "")
                  + f" · kontak videos/{v.id}/{x['kontak']}")
            print(f"   döküm: {x['dokum']['dil']} · {x['dokum']['kelime']} kelime · “{x['dokum']['ozet']}”" if x.get("dokum") else "   döküm: konuşma yok")
        if x.get("kisi_tarama"):
            k = x["kisi_tarama"]
            print(f"   kişi taraması (insan modeli, tahmin): {('kişi olabilir (belirsiz: kişi var sayıldı)' if k.get('belirsiz') else 'kişi var') if k.get('kisi_tahmini') else ('kişi yok' if k.get('kisi_tahmini') is False else 'okunamadı')}"
                  + (f" · alan %{k['alan'] * 100:.1f}" if k.get("alan") is not None else "") + " → doğru değilse: ./st goruntu riza " + v.id + " " + x["ad"] + " --kisi | --kisi-yok")
        if x.get("kisi"):  # bilgi: rıza kapı değildir (kullanıcı kararı, 2026-10-27); kullanıcı isterse bir çözüm seçer
            print(f"   kişi var (rıza: {x.get('riza') or 'bilinmiyor'}) · kullanıcı isterse: ./st goruntu riza {v.id} {x['ad']} --cozum gizle|stilize|kullanma")
        print(f"   sıradaki: ./st maske {v.id} {x['ad']} · ./st derinlik {v.id} {x['ad']} · ./st goruntu kadraj {v.id} {x['ad']} --format <F> · "
              f"Remotion <Goruntu film=\"{v.id}\" ad=\"{x['ad']}\" /> (src/lib/goruntu)")
    elif alt == "riza":
        if len(pos) < 2:
            raise SystemExit("Kullanım: ./st goruntu riza <id> <ad> [--riza evet|hayir|bilinmiyor] [--cozum stilize|gizle|kullanma|yok] [--kisi | --kisi-yok]")
        x = G.riza_ayarla(pos[0], pos[1], s("riza"), s("cozum"), kisi)
        print(f"✅ {x['ad']}: " + ("kişi yok" if not x.get("kisi") else f"kişi var · rıza {x['riza']}" + (f" · çözüm {x['cozum']}" if x.get("cozum") else ""))
              + " · varliklar.md ✅")
    elif alt == "kadraj":
        if len(pos) < 2 or not s("format"):
            raise SystemExit("Kullanım: ./st goruntu kadraj <id> <ad> --format F [--yakinlik 0.2–1] [--hedef govde|bas] [--yumusak SN] [--ozne en_buyuk|hepsi]")
        hedef = s("hedef") or "govde"
        if hedef not in ("govde", "bas"):
            raise SystemExit("--hedef govde | bas")
        if (s("ozne") or "en_buyuk") not in ("en_buyuk", "hepsi"):
            raise SystemExit("--ozne en_buyuk | hepsi")
        k = G.kadraj(pos[0], pos[1], s("format"), f("yakinlik") or 1.0, hedef, f("yumusak") if f("yumusak") is not None else 0.8, s("ozne") or "en_buyuk")
        d = "✅" if k["guvenli_oran"] >= 0.95 else "⚠️"
        print(f"{d} kadraj {s('format')}: özne güvenli alanda %{k['guvenli_oran'] * 100:.1f} kare · gövdenin pencere içindeki payı "
              f"%{k['govde_icinde'] * 100:.0f} · {k['kirpma']} · en hızlı kayma {k['en_hizli_px_kare']} px/kare → videos/{pos[0]}/{k['dosya']}")
        if k["guvenli_oran"] < 0.95:
            print("   özne kenara kaçıyor: --yakinlik'i büyüt (pencere genişler), --yumusak'ı küçült (daha sıkı takip) ya da --hedef değiştir")
        if k.get("sicrama"):
            print(f"   ⚠️ ani geçiş (özne değişti ya da kadrajdan çıktı; kadraj bir karede kayıyor): " + ", ".join(f"f{i}" for i in k["sicrama"][:6])
                  + " → o anı kesmeyle kullan ya da görüntüyü --bas/--son ile kırp")
    elif alt == "liste":
        if not pos:
            raise SystemExit("Kullanım: ./st goruntu liste <id>")
        v = O.load(pos[0])
        D = G.yukle(v)
        G.bilgi_yaz(v, D)
        kul = G.kullanim(v)
        for x in D["varliklar"]:
            print(_goruntu_satiri(v, x) + f" → {', '.join(kul.get(x['ad']) or []) or 'kullanılmıyor'}")
        e = G.etik_durumu(v)
        for m in e["riza"] + [f"etiket kaydı yok: {a}" for a in e["etiket_eksik"]] + [f"gerçek görüntü yapay zekâya girmiş: {a}" for a in e["yz"]]:
            print(f"❌ {m}")
        print(f"{len(D['varliklar'])} görüntü")
    elif alt == "sil":
        if len(pos) < 2:
            raise SystemExit("Kullanım: ./st goruntu sil <id> <ad>")
        x = G.sil(pos[0], pos[1])
        print(f"✅ silindi: {x['ad']} (türevleriyle)")
    else:
        raise SystemExit("Kullanım: ./st goruntu ekle | riza | kadraj | liste | sil  (./st yardim)")


def _takip_satiri(x: dict) -> str:
    d = "✅" if x["hata_px"] <= x.get("hedef_px", 1.0) else "⚠️"
    return (f"{d} {x['ad']} · çekim {x['goruntu']} · {x['n']} kare (bas {x['bas']}) · ortalama hata {x['hata_px']:.2f} px · odak {x['odak_mm']:.1f} mm · "
            f"k1 {x['bozulma']['k1']:+.3f} · {x['iz']} iz · zemin {x['zemin_nokta']} nokta · kamera {x['yukseklik_m']} m · yol {x['yol_m']:.1f} m"
            + (f" · elle ({x['elle']})" if x.get("elle") else "") + f" · {x['tarih'][:16]}")


def cmd_takip(vid=None, *args):
    """Kamera takibi (pipeline/takip.py): çöz ve dondur, liste, denetle, sec, ac (elle iz), onizle."""
    import takip as TK
    if not vid:
        raise SystemExit("Kullanım: ./st takip <id> <görüntü | dosya> [--yukseklik M] … | liste | denetle | sec <ad> | ac <ad> | onizle [<ad>] (./st yardim)")
    pos, o = opts(args, "ad", "bas", "son", "yukseklik", "odak", "hedef", "elle", "kaynak", "not", "riza")
    s = lambda k: o.get(k) if isinstance(o.get(k), str) else None  # noqa: E731
    f = lambda k: float(s(k)) if s(k) else None  # noqa: E731
    alt = pos[0] if pos else "liste"
    v = O.load(vid)
    if alt == "liste":
        T = TK.yukle(v)
        for x in T["cozumler"].values():
            print(("▶ " if x["ad"] == T.get("secili") else "  ") + _takip_satiri(x))
        print(f"{len(T['cozumler'])} çözüm" + (f" · seçili: {T['secili']}" if T.get("secili") else ""))
    elif alt == "denetle":
        S = TK.denetle(v)
        if not S:
            raise SystemExit(f"{vid}: kamera takibi yok (./st takip {vid} <görüntü>)")
        for ok, ad, deger in S:
            print(f"{'✅' if ok else '❌'} {ad}: {deger}")
        K = TK.kayma(v)
        if K and K.get("kare"):
            print(f"{'✅' if K['en_kotu_px'] <= 1.5 else '⚠️'} Nesne kaymıyor (gölgenin altındaki zemin izleri): {K['kare']} karede ortalama "
                  f"{K['ortalama_px']:.2f} px, en kötü kare {K['en_kotu_kare']}: {K['en_kotu_px']:.2f} px (küme {K['kume']})")
        raise SystemExit(0 if all(ok for ok, _, _ in S) else 1)
    elif alt == "sec":
        if len(pos) < 2:
            raise SystemExit(f"Kullanım: ./st takip {vid} sec <ad>")
        print("seçili: " + _takip_satiri(TK.sec(vid, pos[1])))
    elif alt == "ac":
        if len(pos) < 2:
            raise SystemExit(f"Kullanım: ./st takip {vid} ac <ad>")
        TK.ac(vid, pos[1])
    elif alt == "olcek":
        if len(pos) < 3:
            raise SystemExit(f"Kullanım: ./st takip {vid} olcek <ad> <kamera yüksekliği m>")
        x = TK.yukle(v)["cozumler"].get(pos[1])
        if not x:
            raise SystemExit(f"çözüm yok: {pos[1]}")
        x = TK.coz(vid, x["goruntu"], pos[1], x["bas"] / v.fps, (x["bas"] + x["n"]) / v.fps, float(pos[2]), None, x.get("hedef_px", TK.HEDEF_PX),
                   "cozum", olcek_yalniz=True)
        x.pop("cozum_veri")
        print(_takip_satiri(x))
        print(f"   ölçek değişti (kamera {pos[2]} m): ızgarayı önizlemede gör: videos/{vid}/{x['onizleme']}; plakalar yeni kümeye çizilir")
    elif alt == "nesne":
        T = TK.yukle(v)
        ad = pos[1] if len(pos) > 1 else T.get("secili")
        x = T["cozumler"].get(ad or "")
        if not x:
            raise SystemExit(f"çözüm yok: {ad}")
        n = min(v.nframes, x["n"])
        hedef = v.dir / "takip" / ad / "nesne"
        for f in hedef.glob("f*.png"):
            f.unlink()
        cmd_kare(vid, "0", str(n // 3), str(2 * n // 3), str(n - 1), "--cikti", str(hedef))
    elif alt == "onizle":
        T = TK.yukle(v)
        ad = pos[1] if len(pos) > 1 else T.get("secili")
        x = T["cozumler"].get(ad or "")
        if not x:
            raise SystemExit(f"çözüm yok: {ad}")
        import goruntu as G
        c = O.jload(O.ROOT / x["cozum"])
        TK.onizleme(v, ad, c, v.dir / G.bul(v, x["goruntu"])["ara"], v.dir / x["onizleme"])
        TK.hata_grafigi(c, v.dir / x["hata_grafigi"])
        print(f"✅ videos/{vid}/{x['onizleme']} · videos/{vid}/{x['hata_grafigi']}")
    else:
        if s("elle") and s("elle") not in ("iz", "cozum"):
            raise SystemExit("--elle iz | cozum")
        kisi = True if o.get("kisi") else (False if o.get("kisi-yok") else None)
        x = TK.coz(vid, alt, s("ad"), f("bas"), f("son"), f("yukseklik") or 1.5, f("odak"), f("hedef") or TK.HEDEF_PX, s("elle"),
                   {"ad": s("ad"), "kaynak": s("kaynak"), "not": s("not"), "riza": s("riza"), "kisi": kisi})
        c = x.pop("cozum_veri")
        print(_takip_satiri(x))
        print(f"   en kötü kare {c['hata']['en_kotu_kare']['kare']} ({c['hata']['en_kotu_kare']['hata']:.2f} px) · ortanca {c['hata']['ortanca_px']:.2f} px · "
              f"anahtar kareler {c['iz']['anahtar'][0]}–{c['iz']['anahtar'][1]} · kare başına en az {c['iz']['kare_basina_en_az']} iz · {x['sure_sn']} sn")
        print(f"   dondu: {x['cozum']} (sha256 {x['sha256'][:12]}…) · önizleme videos/{vid}/{x['onizleme']} · hata grafiği videos/{vid}/{x['hata_grafigi']}")
        if x["hata_px"] > x["hedef_px"]:
            print(f"   ⚠️ hata hedefin üstünde: çekimi kırp (--bas/--son: hata grafiğinde kötü bölüm), kamera yüksekliğini değil çekimi düzelt; "
                  f"olmazsa elle iz: ./st takip {vid} ac {x['ad']} (Blender'da iz ekle/sil, Solve), sonra ./st takip {vid} {x['goruntu']} --ad {x['ad']} --elle iz")
        print(f"   sahnede: import takip · takip.kamera() · takip.zemin() · takip.ortam() · takip.katmanlar(); üst katman <TakipBirlesim> (src/lib/takip)")


def cmd_derinlik(vid=None, ad=None, *args):
    """Derinlik haritası (pipeline/derinlik.py): bir kez üretilir, dondurulur."""
    import goruntu as G
    if not vid or not ad:
        raise SystemExit("Kullanım: ./st derinlik <id> <ad> [--yumusatma 0–0.9]")
    _, o = opts(args, "yumusatma")
    x = G.derinlik(vid, ad, float(o["yumusatma"]) if isinstance(o.get("yumusatma"), str) else 0.35)
    d = x["derinlik"]
    print(f"✅ derinlik {ad}: {d['en']}×{d['boy']}" + (f" · {d['kare']} kare" if d.get("kare") else "") + f" · {d['cihaz']} · {d['kare_basina']} sn/kare "
          f"(model yükleme {d['yukleme_sn']} sn) → videos/{vid}/{d['asil']} (asıl, 16 bit) · public/{vid}/{d['motor']} (motor)")


def cmd_maske(vid=None, ad=None, *args):
    """Alfa maskesi (pipeline/derinlik.py): insan (HyperFrames remove-background) ya da nesne (--kutu, SAM 2.1)."""
    import goruntu as G
    if not vid or not ad:
        raise SystemExit("Kullanım: ./st maske <id> <ad> [--kutu x0,y0,x1,y1] [--kutu-kare N]")
    _, o = opts(args, "kutu", "kutu-kare")
    kutu = [float(a) for a in o["kutu"].split(",")] if isinstance(o.get("kutu"), str) else None
    x = G.maske(vid, ad, kutu, int(o["kutu-kare"]) if isinstance(o.get("kutu-kare"), str) else 0)
    m = x["maske"]
    print(f"✅ maske {ad} ({m['yontem']}: {m['model']}): ortalama alan %{m['alan'] * 100:.1f}" + (f" · {m['kare']} kare" if m.get("kare") else "")
          + f" · {m['kare_basina']} sn/kare → videos/{vid}/{m['asil']} · public/{vid}/{m['motor']}")


def cmd_sandvic(vid=None, ad=None, *args):
    """Anahtar kare sandviçi: motor ilk ve son kareyi çizer, aradaki hareketi Magnific üretir, motor devralır (zanaat §9)."""
    if not vid or not ad:
        raise SystemExit("Kullanım: ./st sandvic <id> <ad> --bas SN [--sure 5] [--format F]")
    _, o = opts(args, "bas", "sure", "format")
    v = O.load(vid)
    if not isinstance(o.get("bas"), str):
        raise SystemExit("--bas: klibin başladığı an (saniye; motorun o karesi klibin ilk karesi olur)")
    sure = float(o["sure"]) if isinstance(o.get("sure"), str) else 5.0
    fmt = fmts(v, o)[0]
    b = round(float(o["bas"]) * v.fps)
    n = round(sure * v.fps) - 1          # klibin son karesi motorun "son" karesine denk; o kare motordan çizilir, klipten atılır
    s_ = b + n
    if s_ >= v.nframes:
        raise SystemExit(f"son kare ({s_}) filmin dışında ({v.nframes} kare)")
    d = v.dir / "uretim" / "_anahtar" / ad
    files = render_frames(v, [b, s_], d / "_ciz", fmt)
    bas_p, son_p = d / f"{fmt}_bas.png", d / f"{fmt}_son.png"
    shutil.move(str(files[b]), bas_p)
    shutil.move(str(files[s_]), son_p)
    shutil.rmtree(d / "_ciz", ignore_errors=True)
    (d / "sandvic.json").write_text(json.dumps({"ad": ad, "format": fmt, "fps": v.fps, "bas_kare": b, "son_kare": s_, "gosterilen_kare": n, "sure": sure,
                                                "bas": {"dosya": str(bas_p.relative_to(v.dir)), "sha256": hashlib.sha256(bas_p.read_bytes()).hexdigest()},
                                                "son": {"dosya": str(son_p.relative_to(v.dir)), "sha256": hashlib.sha256(son_p.read_bytes()).hexdigest()},
                                                "tarih": dt.datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False, indent=1) + "\n")
    oran = {"9x16": "9:16", "16x9": "16:9", "1x1": "1:1"}.get(fmt, "9:16")
    print(f"✅ anahtar kareler [{fmt}]: bas f{b} ({O.tc(b / v.fps)}) → videos/{vid}/{bas_p.relative_to(v.dir)} · son f{s_} ({O.tc(s_ / v.fps)}) → "
          f"videos/{vid}/{son_p.relative_to(v.dir)}")
    print("⚠️ Etik: anahtar karelerde gerçek bir kişi (gerçek görüntüden) varsa Magnific'e verme: model o kişiyi yeniden üretir (kural 2). Karelere bak.")
    print(f"""Adımlar (her ücretli çağrıdan önce bekçi):
  1. Her kare için: creations_request_upload (görsel) → ./st uret yukle <png> --put <bağlantı> → creations_finalize_upload → kreasyonun görsel bağlantısı
  2. simulate_cost {{tool: video_generate, arguments: {{slug, prompt, duration: {sure:g}, aspectRatio: "{oran}", resolution,
       keyframes: {{start: {{type: "image", url: <bas>}}, end: {{type: "image", url: <son>}}}}}}}}
     ilk ve son kareyi birlikte alanlar: kling-25 (yalnız 1080p), kling-30, minimax-video-3_0-max-turbo, bytedance-seedance-* (video_models_list → keyframes)
  3. ./st uret butce {vid} --tahmin <kredi> --arac video_generate → video_generate (aynı argümanlar) → creations_wait
  4. ./st uret al {vid} {ad} --url <bağlantı> --tur video --uyum --model <m> --arac video_generate --istem "…" --kredi <n> --kaynak-kare "{bas_p.relative_to(v.dir)},{son_p.relative_to(v.dir)}"
  5. Sahnede: <Sequence from={{{b}}} durationInFrames={{{n}}}> klip (ilk karesi motorun f{b}'i) </Sequence>; motor f{s_}'den devam eder
     (Remotion: src/lib/goruntu → <Sandvic film="{vid}" ad="{ad}" bas={{{b}}} kare={{{n}}} />). Ölçüm geçişte tek karelik sıçramayı denetler.""")


def cmd_paket(*args):
    """Kurulum zip'i (pipeline/paket.py): örnek videolar ve marka kitleri seçilir, gerisi stüdyonun kendisi."""
    import paket
    _, o = opts(args, "ornek", "marka", "hedef", "depo", "acik")
    if "acik" in o:  # herkese açık depo: yalnız yerelde hazırlanır ve commit edilir; GitHub'a gönderim kullanıcının işi (kural 10)
        orn = o.get("ornek", "ihh_sofra")
        H = paket.acik_agac([] if orn in ("yok", True) else [x for x in orn.split(",") if x],
                            [x for x in str(o.get("marka") or "").split(",") if x and x != "True"])
        yeni = paket.acik_commit(H)
        n = sum(1 for p in H.rglob("*") if p.is_file() and ".git" not in p.parts)
        print(f"✅ açık kaynak depo: {H} · {n} dosya · " + ("yeni commit" if yeni else "değişiklik yok"))
        print("   Göndermek için: gh repo create <ad> --public --source " + str(H) + " --push  (ya da var olan açık depoya git push)")
        return
    orn = o.get("ornek", "ihh_sofra")
    ornekler = [] if orn in ("yok", True) else [x for x in orn.split(",") if x]
    markalar = [x for x in str(o.get("marka") or "").split(",") if x and x != "True"]
    if "depo" in o:  # zip yerine özel GitHub deposu; adsız --depo son kullanılan depoya gider
        son = paket.DEPO_YEREL / "depo.txt"
        depo = o["depo"] if o["depo"] is not True else (son.read_text().strip() if son.exists() else None)
        if not depo:
            raise SystemExit("Depo adı ver: ./st paket --depo <sahip/ad>")
        url, gitti = paket.depo_gonder(ornekler, markalar, depo)
        print(f"✅ depo: {url} (özel) · " + ("yeni sürüm gönderildi" if gitti else "değişiklik yok, gönderilmedi")
              + f" · örnekler: {', '.join(ornekler) or '—'} · markalar: {', '.join(markalar) or '—'}")
        print("   Karşı tarafta ilk sefer: GitHub sayfasında Code → Download ZIP → Kur.command (README). Sonra masaüstündeki \"Stüdyoyu Güncelle\".")
        return
    hedef = Path(o["hedef"]).expanduser() if o.get("hedef") else Path.home() / "Desktop"
    zipp = paket.uret(ornekler, markalar, hedef)
    print(f"✅ paket: {zipp} · {zipp.stat().st_size / 1e6:.0f} MB · örnekler: {', '.join(ornekler) or '—'} · markalar: {', '.join(markalar) or '—'}")
    print("   Karşı tarafta: zip'i aç → Kur.command (OKUBENI.txt). Aynı zip sonraki seferlerde güncelleme yapar.")


# ---------------------------------------------------------------- regresyon (kural 11)
REGRESYON = O.ROOT / "out" / "_regresyon"


def _regresyon_kareleri(v, n):
    """Eşit aralıklı n kare, ilk ve son dahil."""
    N = v.nframes
    return sorted({int(round(i * (N - 1) / max(1, n - 1))) for i in range(n)})


def _regresyon_ciz(fikstur, kok: Path, kareler=None):
    """Fikstürlerin karelerini her zamanki render yoluyla çizer → ({video: {format: {kare: sha256}}}, {video: atlanma nedeni}).
    Remotion fikstürleri tek pakette (render_jobs), HyperFrames yazılımla (SwiftShader), Blender yalnız plakalar önbellekteyse."""
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    sonuc, atla, isler = {}, {}, []
    for F in fikstur:
        vid = F["video"]
        if not (O.ROOT / "videos" / vid).exists():
            atla[vid] = "video yok"
            continue
        v = O.load(vid)
        istek = {fmt: (kareler or {}).get(vid, {}).get(fmt) or _regresyon_kareleri(v, F["kare"]) for fmt in v.formatlar}
        if kareler is not None:
            istek = {fmt: fr for fmt, fr in istek.items() if fmt in kareler.get(vid, {})}
        import plaka
        if plaka.var_mi(v) and F.get("onbellek"):  # karma film: Blender sahnelerinin taslak plakaları önbellekte değilse atlanır (çizim uzun)
            eksik = []
            for fmt, fr in istek.items():
                for S in plaka.sahneler(v):
                    if S["hata"] or S["motor"] != "blender":
                        continue
                    k, _ = plaka.kume(v, S, fmt, "taslak")
                    if not all((plaka.ONBELLEK / vid / S["ad"] / k / f"p{f:05d}.png").exists() for f in fr if S["r0"] <= f < S["r1"]):
                        eksik.append(f"{S['ad']}/{fmt}")
            if eksik:
                atla[vid] = f"Blender sahnesinin taslak plakaları önbellekte değil ({', '.join(eksik)}): ./st plaka {vid} ciz"
                continue
        if v.motor == "blender" and F.get("onbellek"):
            import blender
            eksik = [fmt for fmt, fr in istek.items()
                     if not all((blender.ONBELLEK / vid / blender.parmak_izi(v, fmt, "taslak")[0] / f"p{f:05d}.png").exists() for f in fr)]
            if eksik:
                atla[vid] = f"taslak plakalar önbellekte değil ({', '.join(eksik)}): ./st blender {vid} plaka"
                continue
        for fmt, fr in istek.items():
            out = kok / vid / fmt
            shutil.rmtree(out, ignore_errors=True)
            import gecis
            if v.motor == "remotion" and not plaka.var_mi(v) and not gecis.var_mi(v):
                isler.append((vid, fmt, {"comp": v.comp_for(fmt), "out": out, "frames": fr, "props": {}, **({"gl": v.gl} if v.gl else {})}))
            else:
                files = render_frames(v, fr, out, fmt, props={"yazilim": True} if v.motor == "hyperframes" else None)
                sonuc.setdefault(vid, {})[fmt] = {str(f): h(p) for f, p in sorted(files.items())}
    if isler:
        for (vid, fmt, _), files in zip(isler, render_jobs([j for *_, j in isler])):
            sonuc.setdefault(vid, {})[fmt] = {str(f): h(p) for f, p in sorted(files.items())}
    return sonuc, atla


def _regresyon_disinda(v) -> bool:
    """Lint ve ölçüm karşılaştırmasına girmeyen film: arşivde ve fikstür değil. Fikstür filmleri arşivde de olsa girer:
    kullanıcının arşiv kararı regresyonun kapsamını daraltmaz (2026-10-27: beş film arşive alınınca karşılaştırma 8 → 4 filme düşmüştü)."""
    if not v.script.get("arsiv"):
        return False
    fik = O.ROOT / "regresyon.json"
    return not (fik.exists() and v.id in {F["video"] for F in O.jload(fik)["fikstur"]})


def _regresyon_lint():
    """Arşivde olmayan her filmin ve fikstür filmlerinin ./st lint sonucu: {video: [[durum, mesaj], …]}."""
    out = {}
    for d in sorted((O.ROOT / "videos").iterdir()):
        if not d.is_dir() or not (d / "script.json").exists():
            continue
        try:
            v = O.load(d.name)
            if _regresyon_disinda(v):
                continue
            out[d.name] = [list(r) for r in lint_rows(v)]
        except SystemExit as e:
            out[d.name] = [["hata", str(e)]]
    return out


def _regresyon_olcum():
    """Arşivde olmayan her filmin ve fikstür filmlerinin ölçüm kararları (./st olc gibi, dosya yazmadan; var olan kaba kurgu ve son
    inceleme kareleriyle): {video: [[ölçüt, durum], …]}. Değer karşılaştırılmaz, karar karşılaştırılır."""
    import olc
    out = {}
    for d in sorted((O.ROOT / "videos").iterdir()):
        if not d.is_dir() or not (d / "script.json").exists():
            continue
        try:
            v = O.load(d.name)
            if _regresyon_disinda(v):
                continue
            rd = O.latest_review_dir(v)
            kdir = rd / review_names(v, v.formatlar[0])[1] if rd else None
            rows, _ = olc.measure(v, {f: rough_path(v, f) for f in v.formatlar if rough_path(v, f).exists()}, kdir if kdir and kdir.exists() else None)
            out[d.name] = [[r["ad"], r["durum"]] for r in rows]
        except (SystemExit, Exception) as e:  # noqa: BLE001 (yarım filmler ölçülemez: hata da bir karardır, değişmemeli)
            out[d.name] = [["hata", type(e).__name__]]
    return out


def _olcum_farki(eski, simdi):
    """Ölçüm kararlarının farkı → (kötü, yeni). Eski bir satırın kararı değişirse ya da satır kaybolursa kötü;
    eski filmde beliren yeni satır ❌ değilse beklenen farktır (yeni ölçüm eski kararı değiştirmez, yalnız ekler)."""
    E, S = {}, {}
    for a, d in eski:
        E.setdefault(a, []).append(d)
    for a, d in simdi:
        S.setdefault(a, []).append(d)
    kotu = [f"{a}: kayboldu" if a not in S else f"{a}: {' '.join(E[a])} → {' '.join(S[a])}" for a in E if S.get(a) != E[a]]
    yeni = [(a, d) for a in S if a not in E for d in S[a]]
    kotu += [f"{a}: yeni satır {d}" for a, d in yeni if d == "❌"]
    return kotu, [(a, d) for a, d in yeni if d != "❌"]


def _piksel_farki(a: Path, b: Path) -> str:
    from PIL import Image
    if not (a.exists() and b.exists()):
        return "kare dosyası yok"
    x, y = (np.asarray(Image.open(p).convert("RGBA"), dtype=np.int16) for p in (a, b))
    if x.shape != y.shape:
        return f"boyut farklı {x.shape[:2]} ↔ {y.shape[:2]}"
    d = np.abs(x - y).max(axis=2)
    return f"en büyük fark {int(d.max())}/255 · farklı piksel %{100 * (d > 0).mean():.3f}"


def cmd_regresyon(alt=None, *args):
    """Kural 11: yeniden yapılanmadan ÖNCE `kaydet` (out/_regresyon/temel/ + temel.json: kare özetleri ve lint), SONRA `karsilastir`
    (aynı kareler yeniden çizilir, bayt bayt ve lint satır satır karşılaştırılır; fark varsa çıkış kodu 1). Fikstürler: regresyon.json."""
    if alt not in ("kaydet", "karsilastir"):
        raise SystemExit("Kullanım: ./st regresyon kaydet | karsilastir [--video V]   (fikstürler: regresyon.json)")
    _, o = opts(args, "video")
    if not (O.ROOT / "regresyon.json").exists():
        raise SystemExit("regresyon.json yok: fikstür listesi geliştirme aracıdır, ./st paket ile gelmez")
    fikstur = O.jload(O.ROOT / "regresyon.json")["fikstur"]
    if o.get("video"):
        fikstur = [F for F in fikstur if F["video"] in str(o["video"]).split(",")]
        if not fikstur:
            raise SystemExit(f"regresyon.json'da yok: {o['video']}")
    tj = REGRESYON / "temel.json"
    if alt == "kaydet":
        REGRESYON.mkdir(parents=True, exist_ok=True)
        eski = O.jload(tj) if tj.exists() and o.get("video") else {"kareler": {}, "atlanan": {}}
        sonuc, atla = _regresyon_ciz(fikstur, REGRESYON / "temel")
        kareler = {**{k: x for k, x in eski["kareler"].items() if k not in atla}, **sonuc}
        kayit = {"tarih": dt.datetime.now().isoformat(timespec="seconds"), "kareler": kareler,
                 "atlanan": {**{k: x for k, x in eski.get("atlanan", {}).items() if k not in sonuc}, **atla}, "lint": _regresyon_lint(),
                 "olcum": _regresyon_olcum()}
        tj.write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n")
        for vid, fm in kareler.items():
            print(f"  {vid:<26} " + " · ".join(f"{fmt} {len(hs)} kare" for fmt, hs in fm.items()))
        for vid, neden in kayit["atlanan"].items():
            print(f"  ⚠️ {vid}: atlandı ({neden})")
        print(f"✅ temel kaydedildi: {sum(len(hs) for fm in kareler.values() for hs in fm.values())} kare, {len(kayit['lint'])} filmin lint sonucu, "
              f"{len(kayit['olcum'])} filmin ölçüm kararları → {tj.relative_to(O.ROOT)}")
        return
    if not tj.exists():
        raise SystemExit("Temel yok: önce (değişiklikten önce) ./st regresyon kaydet")
    T = O.jload(tj)
    hedef = {vid: {fmt: [int(f) for f in hs] for fmt, hs in fm.items()} for vid, fm in T["kareler"].items()}
    fikstur = [F for F in fikstur if F["video"] in hedef]
    sonuc, atla = _regresyon_ciz(fikstur, REGRESYON / "simdi", hedef)
    print(f"\nTemel: {T['tarih']}\n\n| Fikstür | Format | Kareler | Durum |\n|---|---|---|---|")
    kotu = 0
    for vid in sorted(hedef):
        if o.get("video") and vid not in {F["video"] for F in fikstur}:
            continue
        for fmt, hs in T["kareler"][vid].items():
            yeni = sonuc.get(vid, {}).get(fmt)
            if yeni is None:
                kotu += 1
                print(f"| {vid} | {fmt} | — | ❌ çizilemedi ({atla.get(vid, 'bilinmiyor')}) |")
                continue
            farkli = [f for f in hs if yeni.get(f) != hs[f]]
            kotu += bool(farkli)
            ayrinti = "; ".join(f"f{f}: {_piksel_farki(REGRESYON / 'temel' / vid / fmt / f'f{int(f):05d}.png', REGRESYON / 'simdi' / vid / fmt / f'f{int(f):05d}.png')}"
                                for f in farkli[:3])
            print(f"| {vid} | {fmt} | {len(hs) - len(farkli)}/{len(hs)} bayt bayt aynı | {'✅' if not farkli else '❌ ' + ayrinti} |")
    lt, ls = T.get("lint", {}), _regresyon_lint()
    print("\n| Film | Lint | Durum |\n|---|---|---|")
    for vid in sorted(set(lt) | set(ls)):
        if o.get("video"):
            break
        if vid not in ls:
            print(f"| {vid} | — | ⚠️ artık yok ya da arşivde (temelde vardı) |")
        elif vid not in lt:
            print(f"| {vid} | {len(ls[vid])} satır | — yeni film (temelde yok) |")
        elif lt[vid] != ls[vid]:
            kotu += 1
            gitti = [m for d, m in lt[vid] if [d, m] not in ls[vid]]
            geldi = [m for d, m in ls[vid] if [d, m] not in lt[vid]]
            print(f"| {vid} | {len(ls[vid])} satır | ❌ değişti · giden: {'; '.join(gitti)[:200] or '—'} · gelen: {'; '.join(geldi)[:200] or '—'} |")
        else:
            print(f"| {vid} | {len(ls[vid])} satır | ✅ aynı |")
    if not o.get("video"):  # ölçüm kararları: eski satırlar aynı kalmalı; yeni satırlar (❌ değilse) beklenen fark
        ot = T.get("olcum")
        print("\n| Film | Ölçüm | Durum |\n|---|---|---|")
        if ot is None:
            print("| — | — | — temelde ölçüm yok (./st regresyon kaydet ekler) |")
        else:
            os_ = _regresyon_olcum()
            for vid in sorted(set(ot) | set(os_)):
                if vid not in os_:
                    print(f"| {vid} | — | ⚠️ artık yok ya da arşivde (temelde vardı) |")
                elif vid not in ot:
                    print(f"| {vid} | {len(os_[vid])} satır | — yeni film (temelde yok) |")
                else:
                    k, yeni = _olcum_farki(ot[vid], os_[vid])
                    kotu += bool(k)
                    bek = f" · beklenen fark, {len(yeni)} yeni satır: " + "; ".join(f"{a} {d}" for a, d in yeni) if yeni else ""
                    print(f"| {vid} | {len(os_[vid])} satır | " + (f"❌ karar değişti: {'; '.join(k)[:300]}" if k else "✅ eski kararlar aynı")
                          + bek[:400] + " |")
    if kotu:
        print(f"\n❌ regresyon: {kotu} fark (kareler: out/_regresyon/temel ↔ out/_regresyon/simdi)")
        raise SystemExit(1)
    shutil.rmtree(REGRESYON / "simdi", ignore_errors=True)
    print("\n✅ regresyon temiz: bütün fikstür kareleri bayt bayt aynı" + ("" if o.get("video") else ", lint sonuçları ve eski ölçüm kararları aynı"))


def cmd_profiller():
    print("Profiller (profiller/<ad>.json):")
    for p in sorted(O.PROFIL_DIR.glob("*.json")):
        if p.stem == "formatlar":
            continue
        P = O.jload(p)
        print(f"  {P['ad']:16s} {', '.join(P['formatlar']):18s} {'anlatımlı' if P.get('anlatim', True) else 'anlatımsız':10s} "
              f"{P['sure'][0]:g}–{P['sure'][1]:g} sn · {' → '.join(P['vuruslar'])}")
        print(f"  {'':16s} {P.get('aciklama', '')}")
    print("\nFormatlar:")
    for k, F in O.FORMATLAR.items():
        print(f"  {k:6s} {F['w']}×{F['h']}  {F['ad']}")
    print("\nGörünüş: her videoya özel (videos/<id>/gorunus.json). Seriler (bilerek paylaşılan, stiller/<ad>/):",
          ", ".join(p.name for p in sorted((O.ROOT / "stiller").iterdir()) if (p / "gorunus.json").exists()))


# ---------------------------------------------------------------- kapılar
def gate_eval(v):
    """Her kapı için (durum, kanıt/eksik) döndürür. Kapılar sıralıdır: biri kapanmadan sonrakine geçilmez."""
    g = gates_load(v)
    P = v.profil
    res = {}
    approved = lambda n: bool(g.get(str(n), {}).get("onay"))
    # 1 — brief + gerçekler
    brief = v.dir / "brief.md"
    miss = []
    if not brief.exists():
        miss.append("brief.md yok")
    elif O.PLACEHOLDER.search(brief.read_text()):
        miss.append("brief.md'de doldurulmamış [alan] var")
    if P.get("kaynak_zorunlu"):
        kd = O.kaynak_durumu(v)
        if not kd or kd["toplam"] == 0 or kd["bos"]:
            miss.append("kaynaklar.md yok ya da iddia tablosu boş")
        elif kd["ok"] < kd["toplam"]:
            miss.append(f"kaynaklar.md: {kd['toplam'] - kd['ok']} iddia ≥ 2 kaynakla doğrulanmadı (⚠️ {kd['warn']} · ❌ {kd['bad']})")
    vd = O.varlik_durumu(v)
    if P.get("varlik_zorunlu") or vd["liste"]:
        sorun = vd["eksik"] + vd["onaysiz"] + vd["listesiz"]
        if sorun:
            miss.append("varliklar.md: eksik/onaysız/listesiz → " + ", ".join(sorun))
    import veri
    if veri.var_mi(v):  # canlı veri: kaynak açık ve lisansı kullanımı kapsıyor; ekrandaki rakamların dondurulmuş bir görüntüsü var
        miss += [f"veri.json: {m}" for d_, m in veri.sorunlar(veri.sozlesme(v)) if d_ == "❌"]
        if not veri.secili(v):
            miss.append(f"canlı veri: anlık görüntü yok (./st veri {v.id} cek)")
    if v.gorunus_modu == "video":
        G = v.gorunus_json() or {}
        S = G.get("secenekler") or {}
        if v.script.get("ice_aktarim"):  # stüdyo dışında yapılmış film: görünüş orada seçildi, burada kayıtlı olması yeter
            if G.get("secim") not in S:
                miss.append("içe aktarılan filmin görünüşü gorunus.json'da kayıtlı değil")
        elif len(S) < 3:
            miss.append(f"gorunus.json: {len(S)}/3 " + ("yol" if G.get("yol_modu") else "görünüş seçeneği"))
        elif not all((v.dir / "inceleme" / "gorunus" / f"gorunusler-{f}.png").exists() for f in v.formatlar):
            miss.append(("yolların kanca kareleri" if G.get("yol_modu") else "görünüş deneme kareleri") + " yok (./st gorunus <id>)")
        elif G.get("secim") not in S:
            miss.append("yol seçilmedi: seçim kullanıcının (panelde “Bu yolu seç” ya da ./st gorunus <id> sec <harf>)" if G.get("yol_modu") else
                        "görünüş seçilmedi: seçim kullanıcının (panel ya da ./st gorunus <id> sec <harf>)")
    if not approved(1):
        miss.append("insan onayı yok (./st kapi <id> 1)")
    res[1] = (not miss, miss)
    # 2 — senaryo
    miss = [m for d, m in lint_rows(v) if d == "❌"]
    if not approved(2):
        miss.append("insan onayı yok (./st kapi <id> 2)")
    res[2] = (not miss, miss)
    # 3 — temsilî kareler (her format)
    tdir = v.dir / "inceleme" / "temsili"
    lack = [f for f in v.formatlar if not (tdir / review_names(v, f)[2]).exists()]
    res[3] = (not lack, [f"./st temsili <id> (eksik: {', '.join(lack)})"] if lack else [])
    # 4 — kaba kurgu + kontak + ölçüm (her format)
    last = O.latest_review_dir(v)
    lack = [f for f in v.formatlar if not rough_path(v, f).exists() or not last or not (last / review_names(v, f)[0]).exists()]
    ok4 = not lack and last and (last / "olcum.md").exists()
    res[4] = (bool(ok4), [] if ok4 else [f"./st inceleme <id> (eksik: {', '.join(lack) or 'ölçüm'})"])
    # 5 — üç kusur onarıldı + son ölçümde ❌ yok
    repaired, fails = 0, None
    if last:
        for rdir in sorted((v.dir / "inceleme").glob("v*")):
            f = rdir / "inceleme.md"
            if f.exists():
                repaired = max(repaired, len(re.findall(r"\*\*Durum:\*\*\s*onarıldı", f.read_text(), re.I)))
        om = last / "olcum.json"
        if om.exists():
            fails = [r["ad"] for r in O.jload(om) if r["durum"] == "❌"]
    miss = []
    if repaired < 3:
        miss.append(f"inceleme.md'de onarılmış kusur {repaired}/3")
    if fails is None:
        miss.append("ölçüm yok")
    elif fails:
        miss.append("son ölçümde ❌: " + ", ".join(fails))
    if v.script.get("kor_elestiri") and last and elestiri_karari(last) is None:
        miss.append(f"son incelemede kör eleştiri yok (./st elestir <id> → {last.name}/elestiri.md)")
    res[5] = (not miss, miss)
    # 6 — teslim (her format) + yayın paketi
    miss = []
    lack = [f for f in v.formatlar if not final_versions(v, f)]
    if lack:
        miss.append(f"final render yok: {', '.join(lack)} (./st render <id> --final)")
    import plaka
    if plaka.var_mi(v) and not lack:  # karma film: her sahnenin her formatta tam plakası (teslim çizimi üretir)
        miss += plaka.teslim_eksik(v)
    y = v.dir / "yayin.md"
    if not y.exists() or O.PLACEHOLDER.search(y.read_text()):
        miss.append("yayin.md yok ya da doldurulmamış [alan] var")
    if not approved(6):
        miss.append("insan onayı yok (./st kapi <id> 6)")
    res[6] = (not miss, miss)
    return res, g


def cmd_durum(vid=None):
    vids = [vid] if vid else sorted(p.name for p in (O.ROOT / "videos").iterdir() if p.is_dir())
    for vid in vids:
        v = O.load(vid)
        if v.script.get("arsiv") and len(vids) > 1:
            continue  # arşivdeki deneme: yalnız adıyla sorulursa gösterilir
        res, g = gate_eval(v)
        print(f"\n■ {vid} — {v.script.get('title', '')} · {v.profil['ad']} · {', '.join(v.formatlar)} · {v.gorunus_etiketi}")
        blocked, nxt = False, None
        for n, (name, human) in GATES.items():
            ok, miss = res[n]
            mark = "✅" if ok else ("⏸" if blocked else "⏳")
            onay = g.get(str(n), {}).get("onay")
            print(f"  {mark} Kapı {n} · {name}{' (insan)' if human else ''}" + (f" — onay {onay}" if onay else "")
                  + (" (kanıt hazır, önceki kapı bekliyor)" if ok and blocked else ""))
            if not ok and not blocked:
                for m in miss:
                    print(f"       · {m}")
                nxt = nxt or (n, miss)
                blocked = True
        k = elestiri_karari(O.latest_review_dir(v))
        if k:
            print(f"  Kör eleştiri ({O.latest_review_dir(v).name}): {k}" + ("" if k.startswith("yayınla") else " · kusur listesi elestiri.md'de; Kapı 6'da insan karar verir"))
        print(f"  → Sıradaki: Kapı {nxt[0]} — {nxt[1][0]}" if nxt else "  → Tüm kapılar kapandı. Yayına hazır.")


def cmd_kapi(vid, n, *note):
    v = O.load(vid)
    n = int(n)
    name, human = GATES[n]
    g = gates_load(v)
    g.setdefault(str(n), {"ad": name})
    g[str(n)].update({"ad": name, "onay": today(), "not": " ".join(note)})
    gates_save(v, g)
    print(f"Kapı {n} ({name}) onaylandı: {today()}" + ("" if human else " (bu kapı kanıtla kapanır; onay yalnız not olarak kaydedildi)"))


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help", "yardim"):
        print(__doc__)
        return
    cmds = {"yeni": cmd_yeni, "durum": cmd_durum, "kapi": cmd_kapi, "lint": cmd_lint, "cekim": cmd_cekim, "ses": cmd_ses,
            "muzik": cmd_muzik, "vurus": cmd_vurus, "zaman": cmd_zaman, "ses-dene": cmd_ses_dene, "kare": cmd_kare,
            "temsili": cmd_temsili, "render": cmd_render, "inceleme": cmd_inceleme, "olc": cmd_olc,
            "deterministik": cmd_deterministik, "elestir": cmd_elestir, "gorunus": cmd_gorunus, "seri": cmd_seri, "katalog": cmd_katalog, "yayin": cmd_yayin, "referans": cmd_referans, "profiller": cmd_profiller,
            "panel": cmd_panel, "tip": cmd_tip, "hf": cmd_hf, "blender": cmd_blender, "paket": cmd_paket, "3b": cmd_3b, "regresyon": cmd_regresyon,
            "uret": cmd_uret, "veri": cmd_veri, "toplu": cmd_toplu, "niyet": cmd_niyet, "goruntu": cmd_goruntu, "derinlik": cmd_derinlik, "maske": cmd_maske, "sandvic": cmd_sandvic,
            "yapim": cmd_yapim, "takip": cmd_takip, "gecis": cmd_gecis, "plaka": cmd_plaka, "manim": cmd_manim}
    if a[0] not in cmds:
        raise SystemExit(f"Bilinmeyen komut: {a[0]}\n{__doc__}")
    cmds[a[0]](*a[1:])


if __name__ == "__main__":
    main()
