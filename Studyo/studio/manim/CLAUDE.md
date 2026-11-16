# Manim motoru: formül, grafik ve şema sahneleri (karma filmde)

Manim Community (3Blue1Brown'un aracının topluluk sürümü, MIT) stüdyoda **karma filmin bir sahne motorudur** (oturum 6c): matematik, grafik, eksen,
geometri dönüşümü, şema. Tek başına Manim filmi yoktur: film Remotion birleştiricilidir (`script.json → motor: remotion`), Manim sahnesi
`script.json → sahneler`'de bir satırdır ve plaka (PNG dizisi) olarak gelir (`../pipeline/plaka.py`, köprü `../pipeline/manim_kopru.py`).
Kapılar, görünüş, ses, ölçüm ve kör eleştiri aynen geçerlidir (`../../CLAUDE.md`, `../zanaat.md`); kontak ve ölçüm son MP4'e bakar.

## Kurulum (isteğe bağlı)
- Sürüm sabit: **Manim 0.22.1** (`manim_kopru.SURUM`; parmak izine girer). Cairo çizeri; **OpenGL yok** (deterministik değil).
- `uv pip install --python .venv/bin/python -r requirements-manim.txt` (önce `brew install cairo pango`). Kur.command Manim'i kurmaz: kurulu değilse
  Manim sahneli film açıklayıcı bir hatayla durur ve bu satırı söyler (`./st lint`, `./st tip`).
- **LaTeX yok** (kullanıcının kararı, kurulmadı): `MathTex`/`Tex` kullanılmaz (`./st tip` yakalar). Formül `Text`/Unicode (`y = 2ˣ`, `√`, `π`) ya da
  **Typst** (`MathTypst`, `Typst`; pip ile kurulu, yönetici parolası istemez) ile. Dizgi kalitesinde LaTeX istenirse BasicTeX
  (`brew install --cask basictex`, yönetici parolası ister) kullanıcının kendi kurulumudur; sonra kural gevşetilir.

## Sahne
- Yer: `manim/<id>/sahneler/<ad>/sahne.py`, sınıf adı **`Sahne(Scene)`**. İskelet: `./st plaka <id> yeni <ad> --motor manim --bas <işaret> --son <işaret> [--saydam]`.
- Kit: `import kit` (`kit/`): `ST` (format, w, h, fps, sure, nkare, isaretler, vuruslar, beats, guvenli, renk, gorunus, sahne, fontlar, tohum, saydam),
  `renk("vurgu")`, `yazi(metin, rol, px)`, `px(n)`, `kare(t)`, `kare_sayisi(self)`, `oyna(self, *anim, kare=n)`, `bekle(self, n)`,
  `isarete_kadar(self, "ad", ofset)`, `sona_kadar(self)`, `rastgele(n)`.
- **Zaman yerel** (6b): 0 = sahnenin çizim aralığının başı (sınırdaki gölgelendirici kesiminin penceresi dahil); `ST.sahne.bas/son` sahnenin kendi
  penceresi (yerel saniye), `ST.isaretler` kaydırılmış.

## Kurallar
- **Zaman yalnız işaretlerden** (kural 9): `kit.isarete_kadar(self, "formul_yuksel")` sonra `kit.oyna(self, Create(egri), kare=24)`. İşaret karesi,
  animasyonun ilk (alfa 0) karesidir: Remotion'daki `prog(t, işaret, …)` ile aynı (ölçüldü: işaret karesine kadar plakalar bayt bayt aynı, bir
  sonraki karede hareket başlar).
- **Kare sayısı tam**: `self.play`/`self.wait` kullanılmaz (`./st tip` yakalar): Manim'in `run_time`'ı yuvarlamada bir kare kaçırabilir; kit
  `run_time = (n − 0,5)/fps` verir, yazılan kareyi sayar ve sapmayı durdurur. Sahne **`kit.sona_kadar(self)`** ile biter: plaka sayısı çizim aralığıyla
  aynı olmalı, değilse köprü durur ve nedenini söyler.
- **Rastgele kareye erişim yok**: Manim sırayla çizer. Bir küme eksikse sahnenin bütün plakaları bir kez çizilir (`--format png-sequence`) ve
  parmak iziyle dondurulur (Manim sürümü + kit + sahne klasörü + yerel ST + yazı tipi dosyalarının sha256'sı). Hızlıdır (~0,07 sn/kare, 1080×1920).
- **Renk görünüşten** (`kit.renk`), **yazı görünüşün yazı tipiyle** (`kit.yazi`, ≥ 64 px): aynı film tek elden çıkmış gibi durur.
- **Deterministik**: `random`, `time`, `datetime`, tohumsuz `numpy.random` yok (`kit.rastgele`). `./st deterministik` sahneyi ayrı bir işlemde
  baştan çizer ve bütün plakaları bayt bayt karşılaştırır (ölçüm: `../../denemeler/manim/OKU.md`).
- **Her format ayrı yerleşim**: Manim `-r` ile çerçevenin en-boy oranını güncellemiyor; kit çerçeveyi 8 birim yükseklik, formatın oranında genişlik
  kurar (`W = 8 · ST.w / ST.h`). Yerleşimi `ST.dikey` ve `ST.guvenli` ile kur; 9x16'da sağdaki platform düğmeleri (%15) ve alttaki %25 boş.
- **Saydam sahne** (`"saydam": true`): `-t` ile alfa kanallı PNG; Remotion `<Plaka>` altındaki katmanı gösterir.

## Yazı tipleri ve Türkçe
Görünüşün aileleri (`src/lib/fontlar.ts`, @remotion/google-fonts) latin + latin-ext woff2 olarak indirilir (önbellek `out/_hf_fontlar`), fontTools ile
istenen ağırlıkta **statik** örneğe çevrilir (değişken yazı tipi birleştirilemiyor), iki alt küme birleştirilir ve ağırlığa özel tekil aile adıyla
(`"Inter ST500"`) kaydedilir (`out/_manim_fontlar/`, `manimpango.register_font`). Köprü Ç Ğ İ Ö Ş Ü ç ğ ı ö ş ü'nün hepsi yoksa durur.
`kit.yazi(…, px)` boyu tarayıcıdaki gibi ölçer: büyük harf yüksekliği = px · capHeight/em.

## Komutlar
`./st manim <id> --sahne <ad> durum | ciz [--format F] | onizle [--format F]` · `./st plaka <id> durum` · `./st tip <id>` (tarama + kuru çalıştırma) ·
`./st deterministik <id>`. Plakalar `out/_plaka/<id>/<ad>/<format>-tam-<özet>/`. Teknik örnek: `deneme_karma` (arşivde) → `grafik` sahnesi.
