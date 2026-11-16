# YouTube — kurulum, yükleme, ritim, geri besleme

> **Yalnız YouTube'a çıkan işler için.** Stüdyo tek bir kanala bağlı değildir: İHH ve başka markaların bütün videoları burada üretilir ve her işin nereye çıkacağı brief'te ve yayın paketinde (`yayin.md → Nereye`) yazar.
> Bu dosya bir videonun YouTube kanalına nasıl çıkacağını ve kanaldan dönen verinin sisteme nasıl geri gireceğini tanımlar. §0 ve §4 tarih-harita denemesi için yazılmış bir kanal taslağıdır; yön kararı değildir.
> **Yükleme ve yayın her zaman insan tarafından yapılır.** Stüdyo yalnız paketi hazırlar (`./st yayin <id>`).

---

## 0. Kanal kimliği (bir kere, insan kararı, yön netleşince)

| Karar | Durum | Not |
|---|---|---|
| Kanalın yönü (içerik konsepti) | **açık** | Stüdyo her yönü üretebilir. Konseptler `konseptler/` altında: ilk deneme `tarih-harita` |
| Kanal adı + @kullanıcı adı | yön seçilince | Ad YouTube'da ve sosyal ağlarda müsait mi diye kontrol et |
| Profil resmi + kapak (banner) | ad seçilince | Seçilen stil paketiyle koddan üretilir (örnek: `HaritaMasasi-Avatar` / `-Banner`) |
| Anlatıcı sesi | kısmen | Varsayılan TTS hızı +8% (121 kelime/dk). Alternatifler: kendi kaydın (`kayit`), OpenCode (deneysel) |

**Görsel ölçüler** (YouTube yardım sayfalarına göre; yüklemeden önce Studio'da kontrol et):
- Profil resmi: 800×800, daire içinde gösterilir
- Banner: 2560×1440. Yazı ve logo ortadaki ~1546×423 güvenli alanda kalmalı (TV'de tamamı, telefonda yalnız orta şerit görünür)
- Video filigranı: 150×150 (isteğe bağlı)

## 1. Kanal ayarları (bir kere)
- [ ] Kanal dili Türkçe, ülke Türkiye
- [ ] **Varsayılan yükleme ayarları:** kategori *Eğitim*, video dili Türkçe, açıklama şablonu (§3), etiketler: tarih, harita, shorts
- [ ] **Kitle:** YouTube her kanala "çocuklara özel mi?" diye sorar ve bu bir yasal beyandır. Hedef kitle yön seçilince belli olur. Genel izleyici içinse *çocuklara özel değil*. Kararı sen ver
- [ ] **Değiştirilmiş veya yapay içerik beyanı:** YouTube gerçekçi görünen, gerçek sanılabilecek yapay içerik için beyan istiyor. Stilize animasyon, tipografi ve sentetik anlatıcı sesi genelde bu kapsama girmez. Ama yükleme ekranındaki güncel tanımı her seferinde oku. Gerçek bir kişinin sesini ya da yüzünü taklit edersek beyan zorunludur (stil rehberi bunu zaten yasaklıyor)
- [ ] Oynatma listeleri: her seri ya da format için bir liste
- [ ] Kanal fragmanı: kanalın vaadini en iyi gösteren video

## 2. Yükleme listesi (her video, Kapı 6'dan sonra)
1. `./st durum <id>`: bütün kapılar ✅ olmalı
2. Dosya: `cikti/<id>[_format]_vN.mp4`. 9:16 ve ≤ 3 dk → Shorts; 16:9 → normal video. Aynı hikâyenin iki formatı ayrı yüklenir
3. Başlık, açıklama ve sabit yorum: `videos/<id>/yayin.md`
4. **Kapak:** 16:9 videoda özel kapak yüklenir (poster karesi ya da ayrı kapak kompozisyonu). Shorts'ta özel kapak 2026 ortasından beri yalnız YPP kanallarına ve masaüstüne açık; yeni kanalda videodan kare seçilir. Bu yüzden **poster karesi videonun içinde olmalı** (`cues.json → poster`)
5. Oynatma listesine ekle, seriyi açıklamada belirt
6. Yayın sonrası 10 dk: sabit yorumu yaz, otomatik Türkçe altyazıyı kontrol et
7. Konseptin konu havuzunda (varsa) durumu ✅ yap

## 3. Açıklama şablonu
```
[1–2 cümle: olay + ders]

Kaynaklar:
1. ...
2. ...

Seri: [seri adı] ([n]/[toplam])
#tarih #shorts #[konu]
```
`./st yayin <id>` bu şablonu kaynaklar.md'deki kaynakçayla doldurur.

## 4. Yayın ritmi (yön seçilince kesinleşir)
- **Sabit gün ve saatte yayın.** Ritim, üretim kapasitesine göre seçilir. Örneğin Shorts'ta haftada 3, uzun videoda haftada 1
- **Tampon:** Yayın başlamadan önce en az 3–4 video Kapı 6'dan geçmiş olmalı. Böylece bir haftalık aksama ritmi bozmaz
- Üretim seri seri yapılır: aynı stil paketi ve bileşenler serinin bütün videolarında tekrar kullanılır

## 5. Geri besleme (BRIEF → SİSTEM → FİLM → İNCELEME → DAHA İYİ SİSTEM)
Rapor akışı platformdan bağımsızdır (YouTube, Instagram, TikTok, web): her video için yayından **48 saat** ve **7 gün** sonra platformun raporu panelde filmin **Teslim** adımına, **"Yayın sonrası rapor"** bölümüne eklenir: CSV (izlenme eğrisi), ekran görüntüsü ya da PDF; ya da kısa alanlar (platform, tarih, yayınlanan dosya, izlenme, ortalama izlenme %, izlendi / kaydırıldı %, paylaşım, gönderim). Yayın tarihi girilirse panel 2 gün sonra **bir kez** hatırlatır. Dosyalar `videos/<id>/analitik/<tarih>/`'e gider; Claude raporu okur, izleyicinin koptuğu anları saniyeden kareye çevirip çizer (`./st kare … --cikti …/kareler`), filmin ölçümü ve kör eleştirisiyle karşılaştırır, `rapor.md` yazar (ne oldu, koptukları anlar, hipotez, sistem değişikliği önerisi) ve `ogrenimler.md` → Analitik kayıtları'na bir satır ekler. Öneri kullanıcı onaylamadan işlenmez (CLAUDE.md kural 7). "TEST" diye işaretli rapor tabloya yazılmaz.

YouTube'da kaynak YouTube Studio → Analytics; ölçülecekler:

| Metrik | Ne söyler | Bizim karşılığımız |
|---|---|---|
| **İzlendi / kaydırıldı** (Shorts) · **ilk 30 sn tutma** (uzun video) | Kanca çalıştı mı? | Profilin kanca çıtası |
| **Ortalama izlenme yüzdesi** | Shorts'ta %100'ü geçmesi tekrar izleme demektir | Döngü / final |
| **İzlenme süresi grafiğindeki düşüşler** | Hangi saniyede kaçıyorlar? | O saniyenin kontak hücresine bak → kusur adayı |
| Abone kazanımı / video | Kanalın vaadi işliyor mu? | Seri ve konsept |
| Yorumlar | Soru açtı mı, yanlış anlaşılma var mı? | Mesaj + doğruluk |

**Kural:** Bir metrik iki videoda aynı yönde sapıyorsa bu bir **hipotez** olur. Hipotez bir sistem değişikliğine dönüşür (profil, stil paketi, konsept kuralları, şablon ya da kod) ve `ogrenimler.md`'ye işlenir. Tek videoya bakarak kural değiştirilmez.

## 6. Para kazanma (bilgi)
YouTube İş Ortağı Programı'nın eşikleri ülkeye ve programa göre değişiyor. Bilinen ana koşul 1.000 abone + son 12 ayda 4.000 saat izlenme ya da son 90 günde 10 milyon geçerli Shorts görüntülemesi. Güncel eşiği Studio → *Para kazanma* sekmesinden kontrol et. Özel Shorts kapağı da YPP ile açılıyor.
