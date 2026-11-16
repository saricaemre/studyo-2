# Üçüncü taraf bileşenler ve lisanslar

Stüdyonun kendi kodu MIT lisanslıdır (`LICENSE`). Aşağıdakiler başkalarınındır ve kendi lisanslarıyla gelir.

## Depoda bulunanlar

| Bileşen | Nerede | Lisans |
|---|---|---|
| gl-transitions 3.0.0 (184 gölgelendirici geçişi) | `Studyo/studio/src/lib/gecis/gecisler.json` | MIT (182), BSD 2 ve 3 Clause (birer tane); paket metni `src/lib/gecis/LISANS-gl-transitions.txt`, her geçişin yazarı ve lisansı kendi satırında |
| Roboto Flex yazı ailesi | `Studyo/studio/public/fontlar/roboto-flex/` | SIL Open Font License 1.1 (`OFL.txt`) |
| Draco çözücüsü (Google) | `Studyo/studio/public/uc/draco/` | Apache-2.0 (three.js örnekleriyle dağıtılan sürüm) |
| Basis Universal dönüştürücüsü (Binomial) | `Studyo/studio/public/uc/basis/` | Apache-2.0 (three.js örnekleriyle dağıtılan sürüm) |

Dokular (`public/textures/`) ve katalog önizlemeleri (`katalog/onizleme/`) stüdyonun kendi kodundan üretilmiştir (`pipeline/textures.py`, `./st katalog`).

## Kurulumda indirilenler (depoda yok)

Bunlar `Kur.command` ile kendi kaynaklarından iner; kullanırken kendi lisanslarına uyman gerekir.

- **Remotion** (`remotion`, `@remotion/*`): açık kaynak değil, *kaynağı açık* lisans. Bireyler ve küçük şirketler ücretsiz kullanır; belli büyüklüğün üstündeki kâr amaçlı kuruluşlar şirket lisansı almak zorundadır. Ayrıntı: <https://www.remotion.dev/license>. Stüdyoyu bir kurumda kullanacaksan önce bunu kontrol et.
- **GSAP** (HyperFrames filmlerinde): GreenSock'un ücretsiz standart lisansı, <https://gsap.com/standard-license>.
- **HyperFrames** (HeyGen) ve HyperFrames becerileri (`npx skills add heygen-com/hyperframes`): Apache-2.0.
- **three.js**, **React**, **@react-three/fiber**, **topojson-client**: MIT · **world-atlas** (Natural Earth verisi): ISC, veri kamu malı.
- **Blender** (isteğe bağlı): GPL. Stüdyonun Blender betikleri (`bpy` kullanan `studio/blender/`) Blender içinde çalışır.
- **Manim Community** (isteğe bağlı): MIT · **ACE-Step 1.5** (isteğe bağlı müzik modeli): MIT; ürettiği müzik yapay zekâ üretimidir.
- **Whisper / mlx-whisper**: MIT · **edge-tts**: LGPL-3.0 · **transformers**: Apache-2.0 · **Depth Anything V2 Small**: Apache-2.0 · **SAM 2.1**: Apache-2.0.
- **MET Norway** hava verisi (canlı veri): CC BY 4.0, atıf şart.
- **threejsassets.com** modelleri: depoda yok ve paylaşılmaz; her kullanıcı kendi hesabıyla indirir.
- **Magnific** (isteğe bağlı, ücretli): kendi hesabınla bağlanır; ürettiklerin Magnific'in koşullarına tabidir.
