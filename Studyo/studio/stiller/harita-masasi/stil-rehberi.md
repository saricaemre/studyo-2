# Stil paketi: Harita Masası (v1.0 · 2026-10-21)

> **Seri görünüşü** (2026-10-22): yeni bir video bu görünüşü yalnız `--seri harita-masasi` ile bilerek paylaşır. Değerler: `gorunus.json` (yeni videolar) ve `src/stiller/harita-masasi/tokens.ts` (eski videolar).
> İlk konseptin (`konseptler/tarih-harita/DUSTUR.md`) görsel dili. Konsept "ne ve neden" sorusunu yanıtlar, bu rehber "tam olarak nasıl" sorusunu.
> Kod: `studio/src/stiller/harita-masasi/` (tokens, Seal, ConceptCard, Marka) · ortak: `studio/src/components/Captions.tsx` (`HARITA_ALTYAZI`), `studio/src/lib/camera.ts`.
> **Değişiklik kuralı:** Bu dosya yalnız `ogrenimler.md`'de kanıtı olan bir bulguyla değişir. "Daha havalı olur" bir kanıt değildir.
> **Modelin boşluğu güvenli varsayılanlarla doldurmaması için:** Burada yazmayan bir görsel karar gerekiyorsa küçük bir deneme karesi üretip sorulur. 900 karelik yanlış render üretilmez.

---

## 1. Palet (gerçek değerler, "premium" gibi sıfatlar değil)

| Token | Hex | Kullanım |
|---|---|---|
| parşömen | `#EFE3C8` | harita kâğıdı · açık altyazı plakası `#F4EAD2` (%90) |
| mürekkep | `#2B2118` | kıyı çizgisi, yazı, kontur |
| lapis | `#2E4A7D` | savunan taraf, deniz tonu (%13), kavram rengi |
| lal | `#A63A2B` | saldıran taraf, mühür, sebep–sonuç okları, "zayıf nokta" vurgusu |
| varak | `#C9A45C` | söylenen kelime (koyu zeminde `#E9C779`, açıkta `#9A5F12`), ders parıltısı |
| ahşap | `#7A5232` | masa |
| gece | `#0A0D18` / `#070912` | sahne planı: gece gökyüzü |
| meşale | `#FFB45C` | sahne ışığı |

**Taraf kuralı:** Bir videoda iki taraf varsa biri lal, öteki lapis olur. Kanal boyunca aynı taraf aynı renkte kalmaz (her seferinde Osmanlı lal değil). Kural şu: **hamleyi yapan lal, karşılayan lapis.** İzleyici "lal = harekete geçen" diye okumayı öğrenir.

## 2. Yazı

| Rol | Font | Boyut @1080 | Not |
|---|---|---|---|
| Altyazı | Lora 600 | 54 px, satır 1,22 | en fazla 2 satır, bant y = 1152–1302 (%60–68) |
| Harita yer adları | Cormorant Garamond 600–700 (italik: su, düz: kara) | 20–44 px | dekordur, bilgi taşımaz |
| Kavram kartı | KAVRAM etiketi Lora 700 20 px (aralık 5) · terim Cormorant italik 700 70 px · tanım Lora 500 29 px | | sol üst, iğneli |
| Mühür | Cormorant 700: yıl 50 px, halka 19 px (aralık 5) | | sağ üst |

- **En küçük bilgi taşıyan yazı:** 1080 genişlikte 28 px. Altındaki yazı dekor sayılır.
- **Okunurluk testi:** Kontak tabakasındaki 240 px küçük resimde okunmuyorsa telefonda da okunmaz.
- Türkçe karakterler (ğ, ş, İ, ı) her fontta `latin-ext` alt kümesiyle yüklenir.

## 3. Kompozisyon

- **Güvenli alan (9:16):** üst %10 (192 px), alt %25 (480 px), sağ %15 (162 px) platform arayüzüne aittir. Bilgi taşıyan hiçbir öğe buraya girmez. Kontak tabakası bu bölgeleri karartarak gösterir.
- **Göz önce nereye gider:** Kamera odağı ekranın üst-ortasıdır (`FOCUS = 540, 720`). Ana aksiyon orada olur, altyazı altta, kavram kartı sol üstte, mühür sağ üstte.
- **Bir kare, bir bakış noktası.** Aynı anda en fazla 1 büyük olay ve 1 küçük hareket olur.
- **Açık zemin = altyazı plakası.** Harita üstündeki altyazı yumuşak kenarlı parşömen plaka üstünde durur (inceleme v1, kusur 2).

## 4. Tempo

- Her 2–3 sn'de bir anlamlı değişim olur, **hiçbir aralık 3 sn'yi geçmez.** İşaret düzeyinde ve render düzeyinde ölçülür (`./st olc`).
- **"Olay" sayılan:** 1080 genişlikte en az ~60 px'lik bir alanda görünür değişim. 12 px'lik bir piyonun kayması olay sayılmaz (inceleme v1, kusur 3).
- Plan değişimi (masa ↔ sahne) yalnız cümle başında yapılır.
- Kanca **≤ 6 kelime** olur. Mevcut TTS hızında 9 kelime 4,5 sn sürdü (inceleme v1, kusur 1).

## 5. Hareket kuralları (nesne sınıfına göre)

| Sınıf | Davranış | Eğri · süre | Kod |
|---|---|---|---|
| **Piyon** | konur: hafif taşar, sonra sabit kalır | easeOutBack · 0,28 sn | `DefToken`, `ShipToken` |
| **Piyon yolculuğu** | yol boyunca kayar, ortada hafifçe kalkar (ölçek ×1,2) | easeInOutSine · cümleye yayılır | `fleetState` |
| **Mürekkep oku** | kendini çizer, ucu en son gelir | easeInOutSine · 0,45–0,95 sn | yol, `splitArrows` |
| **Mühür** | darbe (ölçek 1,9→1, 0,16 sn) + kısa sarsıntı, 1,5 sn sonra köşeye yerleşir | easeOutCubic | `Seal` |
| **Kavram kartı** | iğnelenir: soldan kayar, −7°→−2° döner | easeOutBack · 0,45 sn | `ConceptCard` |
| **Kamera (masa)** | neredeyse görünmez. Ölçek log uzayında değişir. **Hiç tamamen durmaz:** iki hamle arasında yavaş sürüklenme | easeInOutCubic · 0,8–1,1 sn | `camera.ts` pan |
| **Haritaya dalış** (imza) | nokta ekranda sabit kalır, ölçek ×4–4,5. Sahne daire maskesiyle açılır | 0,6–0,95 sn | `camera.ts` diveIn/diveOut |
| **Altyazı kelimesi** | söylendiği an belirir, 10 px yükselir, varak renge döner | 0,12 sn | `Captions` |
| **Sahne canlılığı** | rüzgâr, meşale, yıldız: tohumlu titreşim | sürekli | `wobble`, `rand(seed)` |

**Kural:** Her şey yaylanırsa hiçbir şey kesin görünmez. Taşma (overshoot) yalnız piyonda ve kavram kartında kullanılır. Kamera, ok ve altyazı taşmaz.

**Kontrol sorusu:** Her hareketten sonra izleyici nereye bakacağını biliyor mu? Bilmiyorsa o hareket mesajla yarışan bir süstür.

## 6. Doku

Kâğıt (`parchment.png`), ahşap (`wood.jpg`), toprak (`earth.jpg`), gren (`grain.png`: overlay %9, kare başına tohumlu kayma), mum ışığı ve vinyet. Dokular `pipeline/textures.py` ile prosedürel üretilir (tohum 1453).

## 7. Ses dokusu

- **Masa:** kâğıt hışırtısı, piyon toku, kalem cızırtısı, mühür darbesi, oda tonu.
- **Sahne:** ortam sesi (rüzgâr, cırcır, deniz, meşale).
- **Motif:** ney (ya da dönemin çalgısı), anlatımın altında kalır.
- **Bilinçli sessizlik:** Hamle'den hemen önce ≥ 0,4 sn, konuşmadan ≥ 20 dB sessiz.
- **Miks:** −14 LUFS, −1,5 dBTP. Ortam sesi anlatım altında otomatik kısılır (ducking).
- **Test:** Gözünü kapat ve dinle. Görüntü olmadan sesin bir şekli yoksa ses tasarımı bitmemiştir.

## 8. Yasaklar (modelin "güvenli varsayılanları")

- Ortada büyük yazı, arkasında gradyan
- Her şeyin fade-in ile gelmesi. Giriş biçimi nesne sınıfından gelir (§5)
- Sonda logo kartı ya da "abone ol" ekranı. Final ilk kareye döner
- Stok fotoğraf, gerçekçi yapay zekâ yüzü, gerçek bir kişinin taklidi
- Emoji, neon, glitch ve "havalı olsun diye" parçacık efekti
- Dönemine uymayan kıyı çizgisi ya da yer adı
- Tartışmalı bir sayıyı kesin gibi gösteren yazı
- Tanıdık bir "epik" kütüphane müziği

## 9. Referans (çıta, şablon değil)

`referans/became_muhabbet_kusu/ANALIZ.md` (Youtube/ köküne göre) yalnız ölçülebilir çıtalar için kullanılır: kanca süresi, senkron, tempo, döngü ve ses yüksekliği. **Kopyalanmaz:** konu, karakter, kalıp cümle, altyazı görünümü ve marka damgası.
