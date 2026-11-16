# Stil paketi: {{AD}}

> **Seri görünüşü şablonu.** Tek bir videonun görünüşü `videos/<id>/gorunus.json`'dadır (zanaat.md §1c); bu şablon birkaç videonun bilerek paylaşacağı bir seri içindir (`./st seri <id> <ad>` bunu kendiliğinden üretir).
> Bir stil paketi, modelin boş bıraktığı kararları önceden verir. Yoksa model kendi "güvenli varsayılanlarıyla" doldurur ve bütün videolar aynı demoya benzer.
> Kaynak: [referans/<ad>/analiz.md ya da elle tanım]. Kod: `studio/src/stiller/{{AD}}/tokens.ts` (`STIL` nesnesi: arka, mürekkep, vurgu, fontlar, altyazı).
> **Değişiklik kuralı:** Yalnız `kanal/ogrenimler.md`'de kanıtı olan bir bulguyla değişir.

## 1. Palet (gerçek değerler, "premium" gibi sıfatlar değil)
| Token | Hex | Kullanım |
|---|---|---|
| arka | [#] | [zemin] |
| mürekkep | [#] | [ana yazı] |
| vurgu | [#] | [tek vurgu: göz önce buraya gider] |

## 2. Tipografi
| Rol | Font · ağırlık | Boyut (1080 kısa kenara göre) | Not |
|---|---|---|---|
| Başlık | [font] | [px] | |
| Gövde | [font] | [px] | en küçük bilgi taşıyan yazı ≥ 28 px |
| Altyazı | [font] | format varsayılanı | |

## 3. Kompozisyon
- **Göz önce nereye gider:** [kural]
- **Güvenli alan:** formatın `guvenli` payları (profiller/formatlar.json) · bilgi taşıyan öğe dışarı taşmaz
- **Formatlar arası:** [16:9'da mekânsal bağlam, 9:16'da daha az öğe ve dikey hiyerarşi, 1:1'de sıkı tip]

## 4. Tempo
- Anlamlı değişimler arası ortalama: [sn] · hiçbir aralık profilin `olay_bosluk_sn` değerini geçmez

## 5. Hareket kuralları (nesne sınıfına göre)
| Sınıf | Davranış | Eğri · süre |
|---|---|---|
| Küçük arayüz öğesi | hızlı, en az taşma | [ ] |
| Panel / kart | kontrollü yerleşme | [ ] |
| Kamera | yumuşak, neredeyse görünmez | [ ] |
| Başlık | güçlü giriş, sabit bekleme (okunacak kadar) | [ ] |
Her şey yaylanırsa hiçbir şey kesin görünmez.
Sayılar (`src/lib/anim.ts`): yay oturma süresi [sn] · taşma [yok / %] · ortak dönüşüm eğrisi [`GECIS` ya da başka] · vuruştan önce başlama [0,05 sn] · ardışık öğe arası [kare] · okuma (`okuma(metin)`). Ortak kurallar: `../zanaat.md` §3–4.

## 6. Doku
- [gren / kâğıt / cam / yok]
- Son rötuş (`gorunus.json → bitis`): hareket bulanıklığı [örnek sayısı] · köşe kararması [güç] · ışık taşması [güç] · siyah kaldırma [değer] · ya da "yok" ve neden

## 7. Ses dokusu
- [efekt ailesi, müzik karakteri, ses yüksekliği hedefi profilden]

## 8. Kaçınılacaklar (bu pakete özgü)
- [pakete özel: bu görsel dilin kimliğini bozan şeyler ve neden]
- Genel uyarılar: `zanaat.md` §8 (yasak değil; sebepsiz kullanılınca ucuz durur)

## 9. Kopyalanmayacaklar (referanstan)
Konu, logo, metin, karakter ve ürüne özgü görseller.
