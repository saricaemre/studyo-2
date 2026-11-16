# Stil paketi: Temel (v1.2 · 2026-10-22)

> **Artık bir seri görünüşü** (2026-10-22, öğrenimler #27): yeni videolar görünüşü kendileri seçer; bu görünüş yalnız `--seri temel` ile bilerek paylaşılır. Değerler: `gorunus.json` (yeni videolar) ve `src/stiller/temel/tokens.ts` (eski videolar); ikisi aynı tutulur.
> Nötr, editoryal bir başlangıç paketi: tipografi + diyagram + veri. Tanıtım, açıklayıcı ve ürün filmleri için.
> Kod: `studio/src/stiller/temel/` (`tokens.ts`: `STIL`, `TEMEL_ALTYAZI` · `parcalar.tsx`: Reveal, panel, DrawPath, sayac, Etiket).
> İlk kullanım: `studyo_tanitim` (inceleme v1 → v2). **Değişiklik kuralı:** yalnız `kanal/ogrenimler.md`'de kanıtı olan bir bulguyla.

## 1. Palet
| Token | Hex | Kullanım |
|---|---|---|
| kâğıt | `#F2EFE8` | zemin (sıcak kırık beyaz) |
| mürekkep | `#141414` | başlık ve gövde |
| turuncu | `#D9480F` | **tek vurgu**: göz önce buraya gider. Bir karede en fazla bir turuncu odak. Kâğıtta 3,7:1: yalnız büyük ve kalın yazıda (başlık, aksan, altyazı vurgusu) ve şekilde. v1.1'e kadar `#FF5A1F` (2,7:1, öğrenimler #24) |
| mavi | `#2F5BFF` | ikincil (veri karşılaştırması), seyrek |
| soluk | `#8C877C` | etiket, ikincil metin, geri çekilen başlık |
| çizgi | `#D9D4C8` | ızgara, çubuk zemini |

## 2. Tipografi
| Rol | Font · ağırlık | Boyut (1080 kısa kenar) | Not |
|---|---|---|---|
| Başlık | Inter 800 | 104–168 px · harf aralığı −%4,5 | sıkı, sola hizalı |
| Aksan | Instrument Serif italik | başlığın ×1,1'i | tek kelime ya da kısa öbek; turuncu |
| Gövde / etiket | Inter 600 | ≥ 28 px | bölüm etiketi "02 · SORUN" büyük harf, aralık %18. Küçük yazı turuncu olmaz (4,5:1 gerekir) |
| Sayılar | Inter 800, `tabular-nums` | başlık boyu | Türkçe ondalık virgülü |
| Altyazı | `TEMEL_ALTYAZI` (Inter 600) | format varsayılanı | vurgu turuncu |

## 3. Kompozisyon
- **Sola hizalı ızgara.** 16:9'da 12, 9:16'da 6 sütun. Izgara çizgileri `çizgi` renginde, %55 görünür: yapıyı hissettirir, öne çıkmaz.
- **Göz önce nereye gider:** sol üstte başlık, sonra tek turuncu öğe.
- **Formatlar ayrı kompozisyondur:** 16:9'da mekânsal yerleşim (kartlar yan yana, zincir yatay). 9:16'da daha az öğe ve dikey hiyerarşi (deste, dikey zincir, tek odak). 9:16'da bir öğe gelince öncekiler küçülerek yer açar.
- **Güvenli alan:** formatın `guvenli` payları. Bölüm etiketi güvenli alanın sol üst köşesindedir.

## 4. Tempo
- Müzik varsa her olay bir vuruşa bağlanır (`["vurus", n]`). Bölüm değişimi vuruşta **sert kesmedir**.
- Anlamlı değişimler arası ≤ profilin `olay_bosluk_sn` değeri. Son vuruşta bir imza olayı olur (inceleme v1, kusur 3).
- **İlk kare asla boş kâğıt değildir:** kancanın görüntüsü 0. karede yerindedir; vuruşta yalnız "punch" alır (inceleme v1, kusur 1).

## 5. Hareket kuralları (nesne sınıfına göre)
| Sınıf | Davranış | Eğri · süre | Kod |
|---|---|---|---|
| Kelime | maskeden yukarı kayar, taşma yok, sonra sabit | easeOutCubic · 0,22 sn | `Reveal` |
| Panel / kart | kontrollü yerleşme: −40 px'ten iner, 0,96 → 1 ölçek | easeOutCubic · 0,38 sn | `panel()` |
| Çizgi / ok | kendini çizer | easeInOutCubic · 0,14–0,6 sn | `DrawPath` |
| Sayaç | eskiden yeniye akar, eski değer üstü çizili solda kalır | easeInOutCubic · 0,5 sn | `sayac()` |
| Kamera | bölüm boyunca %1,5 yaklaşma, neredeyse görünmez | doğrusal | `StudyoTanitim` |
| Hiyerarşi devri | yeni başlık gelince eskisi küçülür ve soluklaşır | easeInOutCubic · 0,3 sn | Kapanış |

**Kural:** Yaylanma yok. Bu pakette taşma (overshoot) kullanılmaz, kesinlik hissi buradan gelir.
**Kural:** Üst üste binen öğeler saydamlaşarak sönmez. Arkadaki öğe içinden görünür ("hayalet" kare). Bunun yerine zemin rengi bir örtü kullanılır (inceleme v1, kusur 2).

### 5b. Sayılar (v1.1 · öğrenimler #22, `../../zanaat.md` §3–4)
Yeni sahne kodu bu değerlerle yazılır; yukarıdaki tablo `studyo_tanitim`'in kaydıdır, değerleri bununla çelişmez. Kod: `src/lib/anim.ts`.
| Ne | Değer | Kod |
|---|---|---|
| Biçim yerleşmesi (kart, kutu, panel) | kritik sönümlü yay, %99'a 0,35 sn, taşma yok | `yay(t − t0, 0.35)` |
| Kamera | yay 0,6 sn ya da ortak eğri 1,5–3 sn; içeri girip hemen çıkma yok | `yay(…, 0.6)` · `GECIS` |
| Hedefi değişen değer | her değişime bir yay, toplanır | `yaylar` |
| Biçim dönüşümü (bir öğe ötekine dönüşür) | ortak eğri, 0,8 sn; içerik ikinci yarıda değişir | `GECIS` |
| Vuruşa bağlı hareket | vuruştan 0,05 sn önce başlar | `ONDEN` |
| Ardışık öğeler | 2–4 kare arayla (24 fps'de 0,08–0,17 sn) | — |
| Okuma | yazı `okuma(metin)` dolmadan süs hareketine başlamaz, ekrandan gitmez | `okuma` |
| Bekleme | nefes %1,2 · kapanış kartında %6 | `nefes` |
| Geçiş | öğe bir sonrakine dönüşür; sert kesme yalnız bölüm değişiminde, vuruşta. Siyah ekran yalnız gerekçeyle (`shot.gecis`) | — |

## 6. Doku
Gren (`grain.png`): multiply, %6, kare başına tohumlu kayma.
Son rötuş (`gorunus.json → bitis`; seri videolarında açık): hareket bulanıklığı, köşe kararması, parlak kenarda yumuşak ışık taşması, siyahlar hafif kaldırılmış. Kâğıt zeminde ışık taşması zayıf kalır; asıl etki koyu sahnelerde görülür.

## 7. Ses dokusu
Müzik omurgadır (−3 dB, anlatım yoksa). Efektler kuru ve kısadır (`wood_tok` 900–3000 Hz, `quill`, `whoosh`), müziğin altında kalır (−17…−29 dB) ve aynı vuruş işaretlerine kilitlidir.

## 8. Yasaklar
- Ortada büyük yazı, arkasında gradyan (yalnız "kaçınılan klişe" olarak gösterilebilir)
- Fade-in ile gelen metin. Metin maskeden kayar
- Birden fazla turuncu odak
- Logo kartıyla bitiş. Final bir cümle ve imza satırıdır
- Ölçülmemiş rakam, render edilmemiş "kanıt" görüntüsü
- Konunun düz simgeleri: insan simgesi ızgarası, saat simgesi, çöp adam (saba_bir_sey_olmaz_3 · öğrenimler #22). Ortak liste: `../../zanaat.md` §8
