# Yöntem kütüphanesi

> **Şablon değil düşünme aracı; aynı yöntemi art arda iki filmde kullanma.** Bir yöntem filmin nasıl düşündüğüdür (mekanizma), görünüşü değil. Planda üç yol yöntemde ayrışır: renk, yazı ve doku değişse de aynı yöntemi paylaşan iki yol aynı fikirdir.
> **Nasıl kullanılır:** plan turunda isteği oku, aşağıdaki yöntemlerle ve kışkırtma araçlarıyla 12–20 ham fikir üret (`videos/<id>/fikirler.md`), puanla, üç yol seç: biri en güçlü sağlam fikir, biri yanal, biri joker. Kampanya örnekleri `kampanyalar/indeks.md`'de (mekanizma, neden işe yaradı, alınacak tek şey); kodla yapılmış viral videoların zanaati `promptlar/indeks.md`'de.
> **Kaynak:** `../yol-haritasi/arastirma.md` §2 (2026-10-25 araştırması; bağlantılar orada doğrulandı). "Bildirilen" sayılar ajans ya da platformun kendi beyanıdır.
> **Pazarlıksızlar aynen geçerli:** uydurma yok (iddia ve rakam kaynaklı), yazı okunur, kare deterministik. STK işlerinde: gerçek yararlanıcı, gerçek olay ya da "belgesel" acı üretilmez; insanlar onurlu, özneli ve rızalı gösterilir (`kanal/ogrenimler.md`, İHH çizgisi).

## Yöntemler

### 1. Tek üretim kuralı
- **Neden işe yarar:** kural özgünlüğü zorlar ve kendisi haber olur: izleyici "bunu nasıl yaptılar?" diye sorar.
- **Örnek:** Hyundai "Night Fishing", yalnız arabanın kendi kameralarıyla çekildi ([Hyundai](https://www.hyundai.com/worldwide/en/newsroom/detail/0000000966)); Apple TV logosu gerçek camla çekildi ([AppleInsider](https://appleinsider.com/articles/25/11/06/forget-liquid-glass-apple-tvs-new-logo-was-shot-with-actual-glass)).
- **Stüdyoda:** brief → Yönetmenlik → Üretim kuralı; her sahne buna uyar, kör eleştirmen sorar. Kodla doğal kurallar: tek renk + siyah, yalnız gölge, yalnız telefon ekranı, yalnız tipografi, tek nesne, hiç yüz yok, gerçek ölçekte tek maket.
- **Hangi filme:** her filme; özellikle bütçesi ve süresi kısa işlerde kural filmi taşır.
- **STK etiği:** kural acıyı estetize etmemeli (ör. "yalnız yıkıntı" kuralı acı pornosuna kayar).

### 2. Tek plan, bitmeyen kamera
- **Neden işe yarar:** kesme yoksa çıkış kapısı yok; izleyici bir sonraki ânı bekler.
- **Örnek:** "Adolescence" tek planla çekildi ([PetaPixel](https://petapixel.com/2025/03/22/this-is-how-netflix-shot-adolescence-in-just-one-take/)); Paul Trillo "The Hardest Part" ([No Film School](https://nofilmschool.com/ai-music-video)).
- **Stüdyoda:** kamera yolu t'nin saf fonksiyonu (Remotion'da sürekli dönüşüm, HyperFrames'te GSAP, Blender'da anahtar kareli kamera); `script.json → yapi` kesmesiz yapıya izin verir (ör. ["Tek plan"]).
- **Hangi filme:** dönüşüm hikâyeleri (bir nesnenin yolculuğu), mekân turu, kısa an.
- **STK etiği:** sorun yok; uzun tek planda tempo ölçülür (olay aralığı çıtası).

### 3. Gerçek dünyada imkânsız nesne (FOOH)
- **Neden işe yarar:** "Gerçekten oldu mu?" sorusu paylaştırır.
- **Örnek:** Maybelline ve Jacquemus'un şehirdeki dev nesneleri ([shots](https://shots.net/news/view/cgi-marketing-the-strange-new-world-of-viral-surrealism)).
- **Stüdyoda:** bugün maket ölçeğinde (Blender M yolu) ya da stilize dünyada; gerçek arka plan + kamera takibi 3b oturumunun işi. Açıkça hayal olmalı.
- **Hangi filme:** ürün, marka, duyuru, kampanya açılışı.
- **STK etiği:** gerçek bir afet ya da yardım sahnesi "imkânsız nesne" ile süslenmez; hayal olduğu ilk bakışta anlaşılmalı.

### 4. Ritüel ya da format ele geçirme
- **Neden işe yarar:** tanıdık bir kalıp (hava durumu, kutu açılışı, geri sayım, maç anlatımı) güveni hazır getirir; ters köşe onu kırar.
- **Örnek:** BM Kadın Türkiye #SheSaidNo (Ogilvy İstanbul 2022; bildirilen 3,2 M erişim) ([UN Women](https://eca.unwomen.org/en/stories/feature-story/2022/12/turkiye-says-no-to-intimate-partner-violence-with-shesaidno-campaign)); Budweiser "One Second Ads" ([Campaign ME](https://campaignme.com/all-the-grand-prix-winners-at-cannes-lions-2025/)).
- **Stüdyoda:** kodla birebir taklit edilebilen formatlar: hava durumu haritası, iftar sayacı, borsa bandı, sohbet ekranı, navigasyon, bildirim, fatura. Aşağıdaki vesile takvimiyle birleşir.
- **Hangi filme:** mevsimlik kampanya, sosyal medya, duyuru.
- **STK etiği:** başka kurumun ya da gerçek bir markanın arayüzü taklit edilmez (impersonation); format genel olmalı.

### 5. Tek, dar bakış açısı
- **Neden işe yarar:** az göstererek yakınlık kurar; izleyici boşluğu kendisi doldurur.
- **Örnek:** DEC "The Locker": deprem yıl dönümünde bir doktorun dolabından ([Marketing Beat](https://www.marketing-beat.co.uk/2024/02/06/dec-dont-panic-earthquake-ad/)).
- **Stüdyoda:** kamera hiç çıkmaz: dolap, telefon ekranı, pencere, çadır kapısı, mektup zarfı, bağış kutusunun içi. Kodla en kolay kurulan güçlü yöntemlerden.
- **Hangi filme:** duygusal kampanya, tanıklık, yıl dönümü.
- **STK etiği:** bakış açısı yararlanıcıyı nesneleştirmemeli; kimin gözünden baktığımızı bilerek seç.

### 6. Vereni göstermek
- **Neden işe yarar:** yardım alan kişiyi veren, karar veren, üreten biri olarak göstermek onur ve sürpriz taşır.
- **Örnek:** UNHCR Ramazan 2026 ([Campaign ME](https://campaignme.com/unhcr-ramadan-campaign-shows-loss-does-not-stop-giving/)); Shelter "World of Our Own" ([The Drum](https://www.thedrum.com/news/2024/11/04/father-and-daughter-create-imaginary-world-escape-harsh-realities-shelter-ad)).
- **Stüdyoda:** brief sorusu: "Yararlanıcı ne yapıyor, ne veriyor, neye karar veriyor?" F ya da M dünyasında karakterin eylemi filmi taşır.
- **Hangi filme:** bağış, yetim, mülteci, kış, Ramazan kampanyaları.
- **STK etiği:** en güvenli yöntemlerden; yine de gerçek kişi canlandırılırsa etiket ve rıza.

### 7. Gerçek tanıklık, stilize resim
- **Neden işe yarar:** ses gerçek, kimlik korunur; izleyici hem inanır hem dinler.
- **Örnek:** "Flee" ([It's Nice That](https://www.itsnicethat.com/news/oscar-nominations-2022-animation-film-090222)).
- **Stüdyoda:** gerçek ses kaydı (`ses.kaynak = kayit`, Whisper hizalar) + F/M dünyası + ekranda "canlandırma" etiketi.
- **Hangi filme:** saha hikâyesi, belgesel, tanıklık.
- **STK etiği:** kaydın rızası yazılı olmalı (varliklar.md); ses kurgulanırken anlam değiştirilmez.

### 8. Anlam yüklü nesnenin dönüşümü
- **Neden işe yarar:** tek bir nesne bütün hikâyeyi taşır ve akılda kalır.
- **Örnek:** Caritas "Vehicle of Hope" (papalık arabasından seyyar kliniğe) ([CAFOD](https://cafod.org.uk/news/media/press-releases/vehicle-of-hope-popemobile-mobile-clinic-for-gaza-s-children)); Careem "Seeds for Gaza" ([Campaign ME](https://campaignme.com/these-are-campaign-middle-easts-work-picks-for-february-2026/)).
- **Stüdyoda:** brief → Ana nesne. Kültürel yüklü nesneler: iftar sofrası, kurban ipi, kışlık mont, okul çantası, su bidonu, anahtar. Nesne sahneden sahneye dönüşür (zanaat §1).
- **Hangi filme:** her tür; özellikle kısa reklam.
- **STK etiği:** dini ve kültürel nesneler saygıyla; nesne alay ya da şok aracı olmaz.

### 9. Veriyi elle tutulur kılmak, saatle
- **Neden işe yarar:** soyut sayı nesneye ve zamana dönüşünce hissedilir.
- **Örnek:** Utrecht 2024: 14.000 çift ayakkabı, her 10 dakikada bir yeni çift ([Al Jazeera](https://www.aljazeera.com/video/newsfeed/2024/3/19/thousands-of-shoes-laid-out-as-memorial-to-children-killed-in-gaza)).
- **Stüdyoda:** kaynaklı birim başına bir nesne, gerçek hızında (Remotion ve 3B katmanında binlerce nesne kolay); sayı kaynaklar.md'de ≥ 2 kaynakla.
- **Hangi filme:** veri hikâyesi, yıl dönümü, rapor tanıtımı.
- **STK etiği:** rakam doğrulanmadan film yapılmaz (kural 2); sayı insanı silmemeli.

### 10. Kişisel veri hikâyesi, katılım
- **Neden işe yarar:** insan kendini paylaşır; film her izleyiciye ayrı olur.
- **Örnek:** Spotify Wrapped 2025 (bildirilen 300 M+ kullanıcı) ([Rive](https://rive.app/blog/spotify-used-rive-for-spotify-wrapped-2025)); Uber Eats kendi reklamını kur ([Marketing Dive](https://www.marketingdive.com/news/uber-eats-lets-fans-build-their-own-super-bowl-ad-with-in-app-integration/811208)).
- **Stüdyoda:** Remotion'un asıl gücü: aynı kompozisyon farklı verilerle (bağışçıya kendi yılının filmi). Veri gerçek ve izinli olmalı.
- **Hangi filme:** bağışçıya teşekkür, yıl sonu, gönüllü filmi.
- **STK etiği:** kişisel veri izinsiz kullanılmaz; örnek veri "örnek" diye işaretlenir.

### 11. Görünür zanaat
- **Neden işe yarar:** "slop" çağında insan kararının kanıtı değerli (2025'te yılın kelimesi "slop" seçildi, [ABC7](https://abc7news.com/post/merriam-websters-2025-word-year-is-slop/18288780/)).
- **Örnek:** De'Longhi el yapımı minyatür kafeler ([Famous Campaigns](https://www.famouscampaigns.com/2026/04/delonghi-turns-its-coffee-machines-into-tiny-cafes-in-new-global-push/)); "Flow" Blender'da küçük bir ekiple ([Blender](https://www.blender.org/?p=93732)).
- **Stüdyoda:** maket dünyası (M), elle çizilmiş hissi veren çizgi, "nasıl yapıldı" kurgusu; stil filtrede değil varlıklarda.
- **Hangi filme:** marka hikâyesi, kurum tanıtımı, uzun ömürlü film.
- **STK etiği:** sorun yok.

### 12. Fikrin kanıtı olarak yapay zekâ
- **Neden işe yarar:** yapay zekâ ucuz kamera değil, fikrin parçasıysa tartışma değil merak yaratır.
- **Örnek:** Heinz "A.I. Ketchup" ([Muse](https://musebyclios.com/advertising/asked-to-draw-ketchup-even-a-i-chose-heinz/)); Kalshi ([eWeek](https://www.eweek.com/news/ai-ad-kalshi-nba-finals/)).
- **Stüdyoda:** Magnific hattı (3a) gelince; o zamana kadar yalnız fikir. Brief'te "neden yapay zekâ?" sorusunun cevabı olmalı.
- **Hangi filme:** teknoloji, ürün, deneysel iş.
- **STK etiği:** İHH çizgisi: gerçek yararlanıcı, gerçek olay, "belgesel" acı yapay zekâyla üretilmez; gerçekçi yapay zekâ yalnız etiketli canlandırma, metafor, mekân ve nesne.

## Kışkırtma araçları (fikir havuzunu genişletmek için)
- **Ölçek kayması:** dev olanı küçült, küçük olanı dev yap (bir damla su şehir kadar; bir kamp masa üstünde).
- **Bilineni tersine çevir:** veren alır, alan verir; sondan başa; yardımın gözünden değil yardım edilenin gözünden.
- **İki ilgisiz dünyayı çarpıştır (bisosiyasyon):** hava durumu × iftar, maç anlatımı × kış yardımı, kargo takibi × kurban.
- **"Burada taklit edilemeyen ne?":** yalnız bu kurumun, bu konunun, bu anın sahip olduğu şey.
- **Oblique Strategies tarzı tek kart:** "Hatayı onur olarak gör", "Yalnız bir parçasını göster", "Ne kadar az şey yeter?".
- **"Ya şöyle olsaydı":** ya kış bir karakter olsaydı; ya sofra konuşabilseydi; ya bağış düğmesi bir yolculuğa çıksaydı.
- **Üç yol:** güvenli (en güçlü sağlam fikir), yanal (başka bir yöntemle aynı mesaj), joker (cesaret "Sınırsız"sa daha uç). Yollar renkte değil **mekanizmada** ayrışır. Yapay zekâ çeşitlilik içindir, seçim insanındır.

## Ritüeller ve vesileler (format ele geçirme ve zamanlama için)
Sabit tarihli günler BM ve uluslararası kurumların ilan ettiği günlerdir. Hicrî takvime bağlı vesileler her yıl yaklaşık 11 gün öne kayar: **tarih yazılacaksa Diyanet takviminden, okul tarihleri MEB'in o yılki takviminden doğrulanır** (kural 2).

| Vesile | Ne zaman | Format fikri |
|---|---|---|
| Ramazan ve iftar | hicrî takvim (her yıl ~11 gün öne kayar; doğrula) | iftar sayacı, sofra, sahur alarmı, ezan vakti tablosu |
| Kurban Bayramı | hicrî takvim (doğrula) | kargo takibi, vekâlet makbuzu, paylaşılan sofra |
| Kış | Aralık–Şubat | hava durumu bülteni, termometre, soba, kışlık mont |
| Okul dönemi | Eylül (MEB takvimi; doğrula) | okul çantası, ders zili, yoklama listesi |
| 6 Şubat depremleri yıl dönümü | 6 Şubat (2023 Kahramanmaraş merkezli depremler) | saat, dolap, anahtar; "o sabah" |
| Dünya Kadınlar Günü | 8 Mart | |
| Dünya Su Günü | 22 Mart | damla, kuyu, bidon, sayaç |
| Dünya Mülteciler Günü | 20 Haziran | anahtar, harita, yol |
| Dünya İnsani Yardım Günü | 19 Ağustos | gönüllünün bir günü |
| Uluslararası Hayırseverlik Günü | 5 Eylül | |
| Dünya Gıda Günü | 16 Ekim | sofra, tabak, ekmek |
| Dünya Çocuk Hakları Günü | 20 Kasım | oyuncak, okul, çizim |
| Uluslararası Gönüllüler Günü | 5 Aralık | |
