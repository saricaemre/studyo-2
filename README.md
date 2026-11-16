# Stüdyo

Kodla video üreten, kapılı bir film stüdyosu. Fikrini panele kendi cümlelerinle yazarsın; Claude birbirinden farklı üç yol önerir, sen birini seçersin, Claude filmi kurar, render eder, kendi karelerini ölçer ve en büyük kusurlarını onarır. Her önemli kararı (yol, senaryo, teslim) sen onaylarsın.

Stüdyo tarzdan bağımsızdır: kampanya ve bağış filmi, reklam, tanıtım, sosyal medya içeriği, eğitim, veri hikâyesi, belgesel, YouTube videosu. Belgelerde örnek kurum olarak İHH geçer; stüdyo bir kuruma ya da markaya bağlı değildir.

**İlke:** model işi önerir, sistem neyin yayınlanacağına karar verir. Brief yön verir, render kontrol verir, kontak tabakası kanıt verir.

## Neler yapar

- **Üç motor, tek akış:** Remotion (yazı, veri, harita, arayüz, SVG), HyperFrames (karakter, çizgi film, kampanya; HTML + GSAP), Blender (gerçek ışık, malzeme, kil ve kâğıt maket; Cycles ya da EEVEE). Karma filmde her sahne kendi motoruyla çizilir, Remotion birleştirir; formül ve grafik için Manim.
- **Her format ayrı kompozisyon:** 9x16, 16x9, 1x1, 4x5; merkezden kırpma yok.
- **Altı kapı:** brief ve kaynaklar → senaryo → temsilî kareler → kaba kurgu, kontak tabakası ve ölçüm → en büyük üç kusurun onarımı → teslim ve yayın paketi.
- **Kör eleştiri:** filmi hiç görmemiş bir Claude oturumu yalnız kareleri ve ölçümü görüp eleştirir.
- **Deterministik kare:** her kare zamanın saf fonksiyonudur; aynı film her seferinde aynı çıkar (`./st deterministik`).
- **Ses:** ücretsiz TTS (Edge), kendi kaydın (Whisper ile hizalanır), kodla üretilen müzik ya da yerelde çalışan ACE-Step; isteğe bağlı Magnific anlatıcısı.
- **Gerçek görüntü:** kendi çekimin ya da açık lisanslı görüntü; derinlik, maske, özne takipli kadraj, kodla stilizasyon.
- **Ek araçlar:** gölgelendirici geçişleri (gl-transitions), 3B katman (Three.js: dünya küresi, ürün, parçacık), canlı veri (MET Norway), kişiye özel etki filmi, "nasıl yapıldı" filmi, kamera takibi (gerçek çekime Blender nesnesi).
- **Stil kataloğu:** 12 görüntü stili, 15 animasyon tipi, 9 ses stili; hepsi önizlemeli ve hepsi yalnız esin. Varsayılan, filme özel icattır.

## Gerekenler

- Apple Silicon Mac (M1 ve sonrası), macOS 14 ya da üstü, en az 8 GB boş disk
- Kendi [Claude](https://claude.ai) hesabın (Pro ya da Max): panel filmleri Claude Code'a ürettirir
- İsteğe bağlı: [Blender](https://www.blender.org) 5.2 (3B filmler), Manim (`requirements-manim.txt`), ACE-Step (+12 GB, yapay zekâ müziği), Magnific hesabı (yapay zekâ görseli ve anlatıcı)

## Kurulum

1. Bu sayfada **Code → Download ZIP**, zip'i aç (ya da `git clone`).
2. `Kur.command`'a çift tıkla. macOS açmazsa Terminal'de `bash ` yaz, dosyayı pencereye sürükle, Enter.
3. Betik Homebrew, ffmpeg, Node.js, Python ortamı, render tarayıcıları, Claude Code ve HyperFrames becerilerini kurar; stüdyo `~/Studyo`'ya gelir. ACE-Step için: `bash Kur.command --ace`.
4. Panel açılır: <http://localhost:4777>. Sonra masaüstündeki **Stüdyo Paneli** kısayolundan.

Güncellemek için yeni sürümü indirip `Kur.command`'ı yeniden çalıştır: yalnız stüdyonun kodu yenilenir, filmlerin, markaların ve ayarların korunur.

Ayrıntılı kullanım `OKUBENI.txt`'te; bütün komutlar `Studyo/studio/README.md`'de; Claude'un çalışma kılavuzu `Studyo/CLAUDE.md`; zanaat kuralları `Studyo/studio/zanaat.md`.

## İlk film

Panelde **Yeni film** → fikrini yaz ("30 saniyelik, dikey, kış yardımı için bağış çağrısı" gibi) → **Claude'a gönder**. Claude üç yol önerir; birini seç, planı onayla, gerisini izle. Komut satırından çalışmak istersen: `cd ~/Studyo/studio && ./st yeni <id> "<Başlık>" --profil reklam-kisa`.

## Klasörler

- `Studyo/studio/`: stüdyo (kod `pipeline/`, Remotion `src/`, panel `panel/`, profiller, katalog, şablonlar, Blender ve Manim kitleri)
- `Studyo/kanal/ogrenimler.md`: bütün filmlerden çıkan öğrenimler (stüdyo bunlarla kendini düzeltir)
- `Studyo/referans/`: yöntem kütüphanesi ve kampanya örnekleri (planlarken okunur)
- `Kur.command`: kurulum ve güncelleme

## Lisans

Stüdyonun kodu [MIT](LICENSE). Bağımlılıklar kendi lisanslarıyla gelir; özellikle **Remotion belli büyüklüğün üstündeki şirketler için ücretli şirket lisansı ister**. Ayrıntı: [UCUNCU_TARAF.md](UCUNCU_TARAF.md).

Stüdyoyla ürettiğin filmler senindir. Gerçek kişi, gerçek olay ve gerçek yararlanıcı yapay zekâ ile üretilmez; yapay zekâ varlığı olan filmin yayın paketinde beyan vardır (`Studyo/CLAUDE.md` → Pazarlıksız kurallar).
