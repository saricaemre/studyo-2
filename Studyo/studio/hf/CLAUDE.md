# HyperFrames motoru: stüdyoda HTML ile film

Bu klasördeki her alt klasör (`hf/<id>/`) bir HyperFrames projesidir (HeyGen, Apache-2.0): sahne HTML + CSS + SVG + GSAP ile yazılır, kareyi ve videoyu HyperFrames çizer. Stüdyonun kapıları, görünüşü, sesi, ölçümü ve kör eleştirisi aynen geçerlidir (`../../CLAUDE.md`, `../zanaat.md`). Motor `videos/<id>/script.json → "motor": "hyperframes"` ile seçilir; köprü `../pipeline/hf.py`.

## Önce beceriler
Sahne yazmadan önce Skill aracıyla `hyperframes` becerisini yükle. Sahne yazarken `hyperframes-core` (kurallar), `hyperframes-animation` ve `hyperframes-keyframes` (hareket), `hyperframes-creative` (sanat yönetimi) gelir. Beceriler `npx hyperframes …` der: **stüdyoda bunun yerine `./st hf <id> <komut>`** çalıştır (önce görünüş, işaretler ve ses eşitlenir). Örnekler: `./st hf <id> lint`, `./st hf <id> check`, `./st hf <id> snapshot --at 1.2,4.5`, `./st hf <id> timeline --json`, `./st hf <id> keyframes`, `./st hf <id> catalog --query "…"`, `./st hf <id> docs gsap`. Önizleme sunucusu (`preview`) arka plan oturumunda açılmaz.

## Stüdyonun yazdığı bloklar (elle değiştirme)
`index.html` içinde iki blok ve iki süre `./st` tarafından her komutta yeniden yazılır:
- `<style id="st-gorunus">`: seçili görünüşün renkleri `--arka --murekkep --vurgu --ikincil --soluk --kagit` (+ görünüşte adı olan ek renkler), yazı değişkenleri `--yazi-baslik` (+ `-agirlik`, `-aralik`), sınıflar `.yazi-baslik .yazi-govde .yazi-aksan` ve yerel `@font-face`. Marka kiti varsa `--marka-<ad>` (ör. `--marka-yesil-koyu`). Görünüşü değiştirmek için `videos/<id>/gorunus.json`'ı değiştir.
- **Planda üç yol** (`gorunus.json → yol_modu`): her seçenek ayrı bir fikirdir ve kanca karesi seçeneğin harfine göre dallanır: `ST.secenek` (`"a"`, `"b"`, `"c"`) ya da CSS'te `html[data-secenek="b"] .yol-a { display: none }`. Görünüş denemesi her seçeneği kendi kopyasında (`_gorunus/<harf>-<format>/`) bu değerlerle çizer. Alan ve nitelik yalnız yollu filmlerde vardır (öteki filmlerin `index.html`'i değişmez). Plan seçilen yolda tamamlanınca seçilmeyen dallar silinir.
- `<script id="st-veri">`: `window.ST = {format, w, h, fps, sure, isaretler, vuruslar, kelimeler, beats, guvenli, altyazi}` (+ yollu filmde `secenek`, niyetli altyazıda `niyet`, canlı veri filminde `veri`, kişisel film şablonunda `kisi`).
- Kök `<div data-composition-id>`'nin ve `<audio id="st-ses">`'in `data-duration`'ı: stüdyonun zaman çizelgesi (`./st ses`).

## Kurallar
- **Zaman yalnız işaretlerden.** `ST.isaretler.<ad>` (saniye; `cues.json`'dan), `ST.vuruslar`, `ST.kelimeler` (anlatımlıda kelime zamanları). Elle saniye yazma (CLAUDE.md kural 9); sahne içi küçük ara zamanlar (stagger, 0,3 sn'lik yay) serbest.
- **Renk ve yazı yalnız değişkenlerden.** `fill="var(--vurgu)"`, `color: var(--murekkep)`, `class="yazi-baslik"`. İllüstrasyonun ara tonları (ten, gölge, gökyüzü) görünüşün `renk` alanına adıyla eklenir; sahneye rastgele hex serpiştirilmez ki üç yolun (ya da görünüşün) renkleri gerçekten farklı çıksın. Logo gibi resmi varlıklar kendi renginde kalır.
- **Her format ayrı kompozisyon.** `index.html` videonun ilk formatında yazılır; öteki formatlar `_fmt/<format>/` altında üretilir (boyut ve `data-format` değişir). Yerleşimi `html[data-format="9x16"] …` seçicileriyle ya da `ST.format` ile kur; merkezden kırpma. Güvenli alanlar `ST.guvenli`'de: yazıyı onunla yerleştir (`./st tip` ve ölçüm "Yazı güvenli alanda" satırı sahne kodunun `ST.guvenli`'yi okuyup okumadığına bakar; okumuyorsa ⚠️ ve kontak tabakasındaki karartılmış bölgelere göz bakar).
- **Deterministik.** Tek bir duraklatılmış GSAP zaman çizelgesi `window.__timelines["main"]`. `Math.random`, `Date`, `setTimeout`, CSS `transition`/`animation` yok; rastgelelik tohumlu (mulberry32 gibi). `./st deterministik <id>` geçmeli (SwiftShader ile çizer; donanım GPU'su kenar yumuşatmasını sıraya göre değiştirir). Teslim (`./st render --final`) de SwiftShader ile çizilir: donanım GPU'suyla hızlı yakalama ölçeği değişen katmanı ara sıra bir kare bulanık çiziyor. `mix-blend-mode` taşıyan katmanı saydamlığı canlanan bir grubun içine koyma: grup tam 1'e ulaştığı karede karışım yalıtımı kalkar ve tek karelik sıçrama olur (ogrenimler #43). Film sonuna kadar süren tween'leri `ST.sure`'un ötesinde bitir (tam sonda biten tween geri sarınca durum bırakıyor); yüzlerce öğeye `immediateRender:false` fromTo ile tekrar eden parıltı yerine tek bir öğe (süzülen ışık, maske) kullan (ogrenimler #39). Bir yazı öğesinde **saydamlık ve konum (y, ölçek) aynı tween'de** canlanırsa yazının kenar yumuşatması çizim sırasına bağlı 1/255 ayrışıyor (bitmiş tween'den sonraki bütün karelerde; `force3D: false` ve `will-change` çözmedi): dönüşümü kapsayıcıya, saydamlığı içteki öğelere ver (ogrenimler #74).
- **İlk kare boş değil.** Kanca 0. karede görünür: girişi ölçekle ya da konumla yap, saydamlığı 0'dan başlatma.
- **Dosyalar.** GSAP ve eklentileri yerelde: `assets/lib/gsap/` (gsap, MotionPathPlugin, CustomEase, CustomBounce, CustomWiggle, DrawSVGPlugin, MorphSVGPlugin, SplitText, TextPlugin, Physics2DPlugin, EasePack); `<script src="assets/lib/gsap/…min.js">`. Videonun gerçek dosyaları `varliklar/` (public/<id>/varliklar'a bağlantı; marka logoları `varliklar/marka/`); her biri `videos/<id>/varliklar.md`'de. Ses `assets/ses/miks.wav` (stüdyonun miksi; elle koyma).
- **Yapay zekâ plakaları (Magnific, `zanaat.md` §9).** `./st uret al` dosyayı `varliklar/uretim/<ad>.<uz>`'a koyar: `<img src="varliklar/uretim/…">`, klipte `<video src="varliklar/uretim/…" muted>` (medya kuralları hyperframes-core; modelin sesi zaten çıkarılmıştır). Yazı plakaya gömülmez. Etiket gerektiren varlığın göründüğü sahnede `<div class="etiket">Canlandırmadır</div>` (`.alt`, `.sag` konumları; 64 px, güvenli alanda, durağan); sınıf yalnız üretim deposu olan filmin `st-gorunus` bloğuna girer. Kayıt `script.json → etiketler`.
- **Bölme serbest.** Uzun filmde sahneleri `compositions/<ad>.html` alt kompozisyonlarına ayırabilirsin (hyperframes-core: sub-compositions); `window.ST` hepsinde okunur.

## 3B katman (Three.js)
Küre, ürün, parçacık ya da gölgelendirici alanı için sahneye bir `<canvas>` koy ve stüdyonun kitini kullan (Remotion'daki `src/lib/uc` ile aynı ışık, malzeme ve üreteç; esbuild ile `assets/lib/uc/uc.js`'e paketlenir). Sahne `assets/lib/uc/` ya da `assets/lib/three/` yüklediğinde `./st` three 0.181.2'yi ve içe aktarılan eklentileri (`three/addons/…`) yerel kopyalar, `uc.js`'i üretir ve import map'i yazar. CDN'den yükleme yok (`./st tip` yakalar). Örnek film: `uc_deneme_hf/`.
```html
<head> … <script type="importmap" id="st-uc"></script> (./st yazar; ilk modül betiğinden önce) … </head>
<canvas id="uc" data-layout-allow-overflow></canvas>
<script type="module">
  import * as THREE from "three";
  import { kur, zamanaBagla, isikKur, isikAyarla, malzeme, dunyaDokusu, kameraKoy } from "./assets/lib/uc/uc.js";
  const { renderer, sahne, kamera } = kur({ canvas: document.getElementById("uc"), golge: true });  // boyut ST.w × ST.h, piksel oranı 1
  const isik = isikKur("studyo", { golge: true }); sahne.add(isik);
  // … nesneler kurulumda bir kez
  zamanaBagla((t) => { kameraKoy(kamera, [0, 1, 6]); isikAyarla(isik, 1, t * 0.1); renderer.render(sahne, kamera); });
</script>
```
- **Zaman yalnız HyperFrames'ten:** `zamanaBagla(ciz)` her arayışta (`hf-seek`) ve açılışta `ciz(t)`'yi bir kez çağırır. `requestAnimationFrame`, `setAnimationLoop`, `THREE.Clock`/`Timer` yok; parçacık ve gölgelendirici zamanı `uniforms.uZaman.value = t`. Yazı GSAP zaman çizelgesinde kalır.
- **Kurulum bir kez, çizim t'nin fonksiyonu:** doku, ağ, gölgelendirici kurulumda; `ciz` yalnız konum, açı ve değer yazar. Ağır kurulum (büyük ağ) için `window.__hf.buildReady["ad"] = söz` (hyperframes-animation → three).
- **Gerçek coğrafya:** `dunyaDokusu({deniz, kara})` Natural Earth kıyı çizgisini çizer; `sinir`, `vurgu: {"Turkey": "#…"}` ve `izgara` siyasi/marka tercihidir, kullanıcı kararı. Konum `enlemBoylam(enlem, boylam, r)`, küreyi bir yere çevirmek `yuzunuDondur(enlem, boylam)`.
- **Renk** görünüşten: `getComputedStyle(document.documentElement).getPropertyValue("--vurgu").trim()`; tam ekran 3B tuval `data-layout-allow-overflow` taşır (bilinçli taşma).
- **Hazır GLB modeller** (`./st 3b`, threejsassets ücretsiz katmanı; ayrıntı `../README.md` → 3B model kütüphanesi): `./st 3b ara tent` → `./st 3b kullan <id> <slug>` (dosya `varliklar/3b/<slug>.glb`, `varliklar.md` satırı yazılır). Modülün başında, `zamanaBagla`'dan önce `await` ile yükle; HyperFrames ilk çizimi bekler (`__hf.buildReady`):
  ```js
  const g = await modelYukle("varliklar/3b/<slug>.glb", { renderer });          // Draco/KTX2 çözücüleri yerelde (assets/lib/uc/cozucu/)
  const kok = modelHazirla(g, { yukseklik: 1.2, golge: true });  sahne.add(kok); // tabanın ortası orijinde; malzeme: (m) => malzeme.kil("#…")
  const an = animasyonKur(kok, g.animations);                                     // çizimde: animasyonSur(an, { klip: "hepsi", t })
  ```
  Yolu `"varliklar/…"` diye yaz (`./` olmadan): `./st durum` varlıkları koddaki bu yazımdan tanır. Farklı paketlerden gelen modeller tek bir görsel dile `malzeme` ile bağlanır. Parça başına malzeme köşe rengiyle: düşük poligon modellerde tek malzeme + köşe rengi var, parça adı yok; `./st 3b onizle <slug>` paleti basar, `modelHazirla(g, { renkler: [{ renk: ["#99a898", "#c7d2c6"], malzeme: malzeme.isikli("#ffb04a") }] })` o renkteki üçgenlere ayrı malzeme verir. Deneme filmleri `uc_model_deneme_hf/` (stüdyonun modeli: Draco, animasyon) ve `uc_model_gercek_hf/` (gerçek threejsassets modeli, parça malzemesi).
- `./st deterministik` SwiftShader ile çizer (ölçüm: 7/7 bayt bayt aynı, ~0,3 sn/kare; `denemeler/threejs_3b/OKU.md`).

## Gerçek görüntü (yol B ve D, `../zanaat.md` §10)
Gerçek görüntü `./st goruntu ekle` ile kaydedilir; motorun dosyası `varliklar/goruntu/<ad>.mp4|png` (ya da plaka `varliklar/uretim/…`), türevleri `goruntu/<ad>/derinlik.*`, `maske.*` ve kayıt `goruntu/bilgi.json` (`./st` `goruntu/` bağlantısını kurar).
- **Video:** `<video src="varliklar/goruntu/<ad>.mp4" muted>` (medya kuralları hyperframes-core). Özne takipli kadraj (`./st goruntu kadraj`) için hazır HyperFrames yardımcısı yok: kare kare kırpma Remotion'da (`<Goruntu>`); HyperFrames'te oranı formatla aynı görüntü ya da `goruntu/bilgi.json → kadraj.<format>.kareler`'e göre elle yerleşim (merkezden kırpma yok). Rıza ölçümü HyperFrames'te kullanım bileşenini ayırt etmez: çözüme uyumu kontak tabakasında göz denetler.
- **2.5B ve stilizasyon yalnız durağan görselde** (videonun kare kare dokusu Remotion'da, `src/lib/goruntu`): kitin `goruntuYukle` dokuları ilk çizimden önce yükler.
  ```js
  import { kur, zamanaBagla, goruntuYukle, derinlikDuzlemi, derinlikAyarla, derinlikKamerasi, stilizeMalzemesi, stilizeAyarla, tamEkran } from "./assets/lib/uc/uc.js";
  const { renderer, sahne, kamera, w, h } = kur({ canvas, ortam: null, tonlama: "yok", arka: "#0E1014", fov: 30 });
  const g = await goruntuYukle("<ad>");                       // { kayit, renk, derinlik, maske, pencere(format, w, h) }
  const duz = derinlikDuzlemi({ en: g.kayit.en, boy: g.kayit.boy }), stil = tamEkran(stilizeMalzemesi());
  zamanaBagla((t) => { derinlikAyarla(duz, { renk: g.renk, derinlik: g.derinlik, guc: 0.3 });
    derinlikKamerasi(kamera, { en: g.kayit.en, boy: g.kayit.boy, w, h, p: t / ST.sure, guc: 0.3, itme: 0.16, odak: [0.5, 0.55] });
    stilizeAyarla(stil.material, { renk: g.renk, maske: g.maske, pencere: g.pencere(ST.format, w, h), w, h, t, mod: "yarimton", renkler: [...], koru: "ozne" });
    renderer.render(sahne, kamera); });
  ```
  Deneme filmi `deneme_gercek_hf/` (arşivde): 2.5B sonra yarım ton, deterministik 9/9.
- **Kişi:** kullanıcı bir çözüm seçtiyse (gizle: mozaik, `stilizeAyarla(..., { gizle: true })`; stilize) görüntü yalnız onunla çizilir. Rıza kapı değildir (kullanıcı kararı, 2026-10-27).

## Niyetli altyazı (`script.json → altyazi: niyetli`, `../README.md` → Niyetli altyazı)
Yazı sesi gösterir: kelimenin şiddeti ağırlığına ve boyutuna, perdesi genişliğine bağlı, her konuşmacı kendi renginde. Veri `./st ses` (ya da `./st niyet <id>`) ile `timeline.json → niyet`'e yazılır; `./st` onu `window.ST.niyet`'e (yalnız o formatın sayfaları), Roboto Flex'in `@font-face`'ini `st-gorunus` bloğuna (`assets/fonts/roboto-flex-*.woff2`) ve paketi `assets/lib/niyet/niyet.js`'e koyar. Alanlar ve dosyalar yalnız niyetli filmde vardır.
```html
<div id="altyazi"></div>   <!-- kökün içinde, sahnelerden sonra (en üst katman); ./st yeni --altyazi niyetli kendisi koyar -->
<script type="module">
  import { niyetliAltyazi } from "./assets/lib/niyet/niyet.js";
  niyetliAltyazi(document.getElementById("altyazi"));
</script>
```
- **Zaman yalnız HyperFrames'ten:** her arayışta (`hf-seek`) ve açılışta t anının hâli yeniden kurulur (Remotion'daki `<NiyetliAltyazi>` ile aynı çekirdek, `src/lib/niyet/cekirdek.ts`). GSAP zaman çizelgesine eklenmez; yazı tipi inene kadar HyperFrames çizime başlamaz (`__hf.buildReady["niyet-yazi"]`).
- **Satırları tarayıcı bölmez:** sayfalar ve satırlar `pipeline/niyet.py`'de yazı tipinin ölçü tablosuyla kurulur; iki motor aynı satırı çizer. Alanı güvenli alan verir; sahnede altyazının bölgesini (dikeyde alttan ~%25–35) boş bırak.
- Ortak altyazı bandının ölçüleri (`ST.altyazi`) niyetli filmde kullanılmaz. Deneme filmi `deneme_niyet_hf/` (arşivde): kar gecesi, iki konuşmacı, deterministik 12/12.

## Canlı veri (`videos/<id>/veri.json`, `../README.md` → Canlı veri, `../zanaat.md` §11)
Film gerçek bir kaynaktan dondurulmuş anlık görüntüyle çizilir (`./st veri <id> cek`); `./st` seçili görüntünün çizim verisini `window.ST.veri`'ye yazar: `{kimlik, zaman_yerel, tur_ad, konum, kaynak, atif, atif_kisa, lisans, ekranda, degerler: {<alan>: {ad, deger, metin, birim, pencere, zaman_yerel}}}`. Çizim sırasında ağ yok; görüntü değişince `index.html`'in veri bloğu ve yalnız bu filmin kareleri değişir.
```html
<div id="atif" class="veri-atif"><div class="a1"></div><div class="a2"></div></div>  <!-- yalnız kullanıcı ekranda atıf isterse; sınıfı ./st yazar: 40 px, koyu plaka -->
<script>
  const V = ST.veri, G = V.degerler.gece_en_dusuk;
  document.querySelector("#deger .metin").textContent = G.metin;           // ekrandaki sayı her zaman metin (Python'da biçimlenir); elle yazma, yeniden yuvarlama
  document.querySelector("#atif .a1").textContent = V.atif_kisa;          // ekranda atıf (kullanıcı istediyse); atıf her durumda yayın paketinde
  document.querySelector("#atif .a2").textContent = `${V.tur_ad} · ${V.zaman_yerel}`;
  const oran = (G.deger + 10) / 40;                                       // görsel ölçü değerin kendisinden (kurulumda bir kez); hareket GSAP'ta
</script>
```
- Değerler kurulumda bir kez yazılır, zaman GSAP zaman çizelgesindedir. `script.json → veri_isareti`: değerlerin ve atfın tam göründüğü işaret (ölçüm bu kareyi filmin dosyasından okur). Deneme filmi `deneme_veri_hf/` (arşivde): MET Norway, Ankara, termometre.

## Kişisel etki filmi (`videos/<id>/veri_sablonu.json`, `../README.md` → Kişisel etki filmi, `../zanaat.md` §12)
Şablon film her kişiye kendi verisiyle çizilir (`./st toplu <id> --veri <liste>`). `./st` `window.ST.kisi`'ye şablonun TEST örneğini (filmin kendi kareleri, inceleme, teslim) ya da toplu üretimde satırın verisini yazar: `{kimlik, test, alanlar: {<alan>: {ad, tur, deger, metin, sayi, birim}}, yerlesim: {<alan>: {<format>: {satirlar, boyut, wght, wdth, opsz, satir_yuksekligi, genislik, hiza}}}}`. Yalnız ekranda ya da sahnede kullanılan alanlar gelir. Yardımcı `assets/lib/kisisel/kisi.js` (`./st` kopyalar, düz betik), Roboto Flex'in `@font-face`'i ve `.kisi-test` sınıfı `st-gorunus`'ta; hepsi yalnız şablon filmde.
```html
<script src="assets/lib/kisisel/kisi.js"></script>          <!-- gsap'tan sonra, sahne betiğinden önce -->
<div id="ad"></div>
<script>
  const K = ST.kisi, A = K.alanlar;
  const satirlar = Kisi.yazi(document.getElementById("ad"), "ad", "var(--murekkep)");   // Python'un satırları (tarayıcı bölmez), ≥ 64 px
  Kisi.degiskenYazi(document.querySelector("#etki .sayi"), 110, 860).textContent = A.etki.sayi;   // sayı her zaman Python'un metni
  // Kisi.test(document.getElementById("root"));             // TEST satırında plaka: yalnız kullanıcı isterse
  // maskeli yükseliş: .kisi-satir { overflow: hidden } > span { display: inline-block }; yalnız dönüşüm, saydamlık yok
  const ic = satirlar.map((d) => { const s = document.createElement("span"); s.textContent = d.textContent; d.replaceChildren(s); return s; });
  ic.forEach((s, i) => tl.fromTo(s, { yPercent: 105 }, { yPercent: 0, duration: 0.45 }, I.k_ad + i * 0.12));
</script>
```
- Değerler kurulumda bir kez yazılır, zaman GSAP zaman çizelgesindedir; alanın değerini elle yazma (`./st tip` şablonun örnek değerini kodda arar). Satırın içi maskeyle yükselecekse dönüşüm iç öğede, saydamlık başka öğede (ogrenimler #74). Yerleşim akışta (flex): en uzun ad ve iki satırlık değer kartı taşırmasın.
- `veri_sablonu.json → kisi_isareti`: ekrandaki bütün alanların tam göründüğü işaret (yazı tanıma her filmin bu karesini okur). Toplu üretimde her satırın kompozisyonu `videos/<id>/toplu/_gecici/` altında bir varyanttır (kişi verisi `hf/<id>/`'ye yazılmaz; iş bitince silinir), teslim kalitesinde SwiftShader ile, filmler sırayla. Deneme filmi `deneme_kisisel_hf/` (arşivde): 3 TEST satırı, film başına ~9,7 sn.

## Kılavuz kipi (yapım filmi, `./st yapim`; `../README.md` → Yapım filmi)
Yapım filminin "önce iskelet" bölümü için `./st` formatın kompozisyonunu bir kopyaya alır (`out/_yapim/<id>/hf/<kip>-<format>/`; `hf/<id>/`'ye yazılmaz, öteki dosyalar oraya bağlantı) ve `</body>`'den önce satır içi bir betik ekler (`src/lib/yapim/hf.ts` → esbuild; çekirdek Remotion'la ortak `src/lib/yapim/kilavuz.ts`). Betik her `hf-seek`'te, öteki dinleyiciler (altyazı, 3B, sahne) sahneyi t anına kurduktan sonra (mikro görev) kökün altındaki yazı, görsel, video, en dış svg ve tuval kutularını ölçer ve kökün en üstüne çizer: yazının puntosu (64 px'in altı kırmızı), güvenli alan (`ST.guvenli`), üçte bir çizgileri. Kip `veri` kareyi siyaha boyar, kutuları piksellere yazar (hareket yolu ve en küçük yazı). Sahne kodunda bir şey gerekmez; yalnız yazı DOM'da yazı olmalı (tuvale ya da görsele gömülmüş yazıyı kılavuz göremez). Kareler SwiftShader ile çizilir.

## Gölgelendirici geçişleri (6a): HyperShader ölçüldü, alınmadı
HyperFrames'in kendi gölgelendirici geçiş paketi `@hyperframes/shader-transitions` (HyperShader, 0.9.17, html2canvas gömülü) 2026-11-06'da 0.9.17 filminde
yerel kopyayla ölçüldü (`deneme_gecis_hf`, arşivde; ölçüm `../../denemeler/hypershader/OKU.md`):
- CLI **`render`**'da çalışıyor ve **deterministik** (iki ayrı `render --no-browser-gpu` MP4'ü bayt bayt aynı); motor "page-side compositing" ile yakalıyor,
  `var(--…)` renkleri dokuda doğru (html2canvas yalnız tarayıcı önizlemesinde devreye giriyor).
- Stüdyonun tek kare yolu **`snapshot`**'ta geçiş **hiç çizilmiyor** (GPU'da da SwiftShader'da da pencerede gelen sahne düz görünüyor): `./st kare`, `temsili`,
  `inceleme`'nin kontak kareleri, `deterministik` ve `regresyon` yanlış kare verirdi.
- `hyperframes lint` yerel paketi 3 hatayla reddediyor (`Date.now()`, `performance.now()`, `requestAnimationFrame`): `./st tip` düşer.
- gl-transitions GLSL'i verilemiyor: paket yalnız kendi 14 gölgelendiricisini kabul ediyor (tablo kapalı).

**Karar:** HyperFrames filminde gölgelendirici geçişi yok; geçişler CSS ile (maske, kırpma, ölçek, saydamlık; `hyperframes-animation` → transitions).
Gölgelendirici geçişi gereken HyperFrames sahnesi **karma filmde** (aşağıda) plaka olarak çizilir ve geçişini Remotion `<Kesim>`/`<GlGecis>`
(gl-transitions, 184 geçiş) yapar. Sürüm bu iş için değiştirilmedi. `snapshot` page-side compositing'i desteklediğinde ölçüm tekrarlanır.

## Karma filmin sahnesi (6b; `../pipeline/plaka.py`, `../README.md` → Karma film)
Karma filmde (Remotion birleştirici, `script.json → sahneler`) bir HyperFrames sahnesi `hf/<id>/sahneler/<ad>/index.html`'dir: **sıradan bir HyperFrames
projesi**, bu dosyadaki bütün kurallar aynen (bloklar, GSAP zaman çizelgesi, deterministiklik, formatlar). Farkı zaman: `ST` **yerel**dir (0 = sahnenin
çizim aralığının başı; işaretler, vuruşlar, kelimeler kaydırılmış; `ST.sure` aralığın uzunluğu; `ST.sahne = {ad, bas, son, film_bas, kare0}`). Çizim aralığı
sahnenin penceresinden sınırdaki gölgelendirici kesiminin yarısı kadar geniştir: kesimden önce gelen ilk kareler de bakılabilir olsun.
- İskelet `./st plaka <id> yeni <ad> --motor hyperframes --bas <işaret> --son <işaret>`; CLI `./st hf <id> --sahne <ad> lint|check|snapshot …`.
- Plakalar SwiftShader'la (bayt bayt), istenen kareler için (`snapshot` rastgele kareye erişir), tek kalite; yazı ve logo genelde Remotion üst katmanında.
- Saydam HyperFrames sahnesi yok (`snapshot` saydam arka plan vermiyor): sahne opak çizilir.

## Akış
`./st yeni <id> "Başlık" --motor hyperframes [--marka ihh] [--dil en] [--altyazi niyetli]` → görünüş üç seçenek + kanca karesi → `./st gorunus <id>` → (kullanıcı seçer) → sahneler → `./st tip <id>` (hyperframes check, her format) → `./st ses` → `./st temsili` → `./st inceleme` → `./st elestir` → onarım → `./st render <id> --final`. Teknik örnek film: `ihh_sofra/` (köprünün ve GSAP zaman çizelgesinin nasıl kurulduğu; çizgi film dünyası onun seçimidir, HyperFrames'in değil: tarzı görüntü stili seçer, motor seçmez).
