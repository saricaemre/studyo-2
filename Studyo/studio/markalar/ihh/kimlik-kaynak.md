# İHH İnsani Yardım Vakfı: Tasarım Kimliği

**Kaynak:** ihh.org.tr (canlı site, 15 Ekim 2026). Değerler sitenin CSS'inden, hesaplanmış stillerden ve resmi logo SVG'sinden çıkarıldı.
**Hazırlayan:** Emre Sarıca (Claude ile)
**Kural:** İHH için yapılan tüm yeni tasarımlar (reklam, sosyal medya, web, sunum, Figma) bu dosyaya göre yapılır. Bir kampanya özel bir renk veya font gerektiriyorsa bu dosyadaki kampanya renkleri arasından seçilir, yoksa burada not edilip gerekçesi yazılır.

Bu klasördeki dosyalar:

| Dosya | Ne işe yarar |
|---|---|
| `IHH_Marka_Kimligi.md` | Bu belge, ana referans |
| `ihh-tokens.css` | HTML/Playwright ile üretilen tasarımlar için hazır CSS değişkenleri |
| `ihh-logo-yatay-tr.svg` | Resmi yatay Türkçe logo (sitedeki dosyanın birebir kopyası) |
| `ihh-logo-yatay-tr-beyaz.svg` | Koyu zemin ve fotoğraf üstü için tamamen beyaz versiyon |
| `ihh-logo-yatay-tr-tek-renk-yesil.svg` | Tek renk koyu yeşil versiyon (tek renk baskı, küçük boyut) |
| `IHH_Marka_Kimligi_Onizleme.png` | Kimliğin tek sayfalık görsel özeti |

---

## 1. Logo

- **Resmi dosya:** `https://ihh.org.tr/public/display/6/horizontal---turkce.svg` (161×54, oran ~3:1).
- **Yapı:** Solda zeytin dallarıyla çevrili dünya küresi amblemi, sağda "İHH" harfleri, altında "İNSANİ YARDIM VAKFI" yazısı.
- **Logo renkleri:**
  - Koyu yeşil `#026839`: "İHH" harfleri ve zeytin dalları
  - Zeytin altın `#A09744`: küre ve "İNSANİ YARDIM VAKFI" yazısı
- **Sitede yalnızca Türkçe yatay logo yayında.** İngilizce ("IHH Humanitarian Relief Foundation") ve Arapça logo dosyaları sitede bulunamadı. İngilizce reklamlarda Türkçe logo kullanılabilir ya da kurumdan İngilizce logo istenmeli.

**Kullanım kuralları (sektör standardı + sitedeki uygulama):**
- Logo beyaz veya çok açık zeminde orijinal renkleriyle kullanılır (sitede her zaman beyaz header üzerinde).
- Koyu zemin veya fotoğraf üstünde tamamen beyaz versiyon kullanılır. Fotoğraf kalabalıksa logonun altına sade bir alan veya hafif koyu degrade bırakılır.
- Etrafındaki boş alan en az "İHH" harf yüksekliğinin yarısı kadar olmalı.
- Ekranda en küçük genişlik ~120 px (sitede 143–161 px). Bunun altında alt yazı okunmaz, tek renk yeşil versiyon tercih edilir.
- Logonun renkleri değiştirilmez, gerilmez, döndürülmez, gölge veya efekt eklenmez.

---

## 2. Renkler

### 2.1 Kurumsal (logodan)
| Ad | HEX | RGB | Kullanım |
|---|---|---|---|
| İHH Koyu Yeşil | `#026839` | 2, 104, 57 | Logo, kurumsal vurgu, küçük yeşil metin, koyu zeminler |
| İHH Zeytin Altın | `#A09744` | 160, 151, 68 | Logo, ince ayrıntı ve süs öğeleri. Metin rengi olarak kullanılmaz |

### 2.2 Dijital ana renk
| Ad | HEX | Kullanım (sitede) |
|---|---|---|
| Bağış Yeşili | `#1FAD4E` | Ana CTA ("Bağış Yap", "Projeyi Destekle", "Hikayeyi oku"), linkler, ilerleme çubukları, seçili durumlar, para birimi rozetleri |
| Bağış Yeşili odak halkası | `rgba(31,173,78,.3)` | Form odak gölgesi |

### 2.3 Kampanya renkleri (her kampanyanın kendi rengi var)
| Kampanya | HEX | Sitedeki yeri |
|---|---|---|
| Zekat | `#E84545` | "Zekat Bağışla" butonu ve kart çerçevesi |
| Filistin / Gazze, acil yardım | `#E23131` | "Şimdi Bağış Yap" butonu, Filistin kartı |
| **Yetim** | `#22ABE6` | "Sponsor Ol" butonu, yetim kartı, tutar seçimleri |

### 2.4 Yardımcı renkler (ikon ve kategori etiketleri)
| HEX | Sitedeki yeri |
|---|---|
| `#0C8ADF` | "BAĞIŞ YAPIN" başlığı ve ikonu |
| `#E2B513` | "BİLGİ EDİNİN" başlığı ve ikonu |
| `#7FBF40` | "HIZLI ULAŞ" başlığı ve ikonu |

### 2.5 Nötrler
| HEX | Kullanım |
|---|---|
| `#000000` | Ana başlıklar |
| `#333333` | Kart başlıkları, gövde metni |
| `#3F3F41` | Kategori etiketi metni |
| `#4C4C4C` | Üst menü, footer başlıkları |
| `#666666` | İkincil metin, footer |
| `#999999` | Pasif buton ("Sepete Ekle" seçim yokken) |
| `#CCCCCC` | Ayırıcılar |
| `#E4E4E4` | Kart kenarlığı, ilerleme çubuğu zemini, header alt çizgisi |
| `#F2F2F7` | Üst bilgi şeridi zemini |
| `#F8F8F8` | Bölüm zemini (hikayeler, projeler) |
| `#FFFFFF` | Sayfa ve kart zemini |

### 2.6 Kontrast (erişilebilirlik)
| Renk | Beyaz metinle | Not |
|---|---|---|
| `#026839` | 6.9:1 | Her boyutta güvenli |
| `#E23131` | 4.45:1 | Kalın 18 px ve üstü güvenli |
| `#E84545` | 3.9:1 | Sadece büyük, kalın metin |
| `#1FAD4E` | 2.9:1 | Sitede böyle kullanılıyor ama zayıf. Reklamda buton metnini **kalın ve büyük** tut |
| `#22ABE6` | 2.6:1 | Zayıf. Yetim CTA'sında metni büyük ve kalın tut, ya da metni `#000`/`#333` yap (8:1) |
| `#E2B513`, `#7FBF40` | ~2:1 | Beyaz metin kullanılmaz, sadece ikon veya koyu metinle |

---

## 3. Tipografi

| Rol | Font | Not |
|---|---|---|
| Ana font (Latin) | **Proxima Soft** (Adobe Fonts, kit `ftc2odz`) | Ağırlıklar: 300, 400, 500, 600, 700. Yuvarlak uçlu, sıcak, geometrik |
| Arapça | **Tajawal** (Google Fonts) | 300, 400, 500, 700 |
| Ücretsiz yedek | **Nunito** (Google Fonts) | Proxima Soft yoksa en yakın görünüm. Claude'un ürettiği görsellerde bu kullanılır |
| Yığın | `proxima-soft, Tajawal, Nunito, Arial, sans-serif` | |

- Harf aralığı: tüm metinlerde hafif sıkı, **−0.016em** (18 px'te −0.288 px).
- Serif font kullanılmıyor. Başlıklar için de Proxima Soft kalın.

**Sitedeki ölçek (masaüstü):**
| Öğe | Boyut / ağırlık / satır | Renk |
|---|---|---|
| Hero başlığı | 40 / 400 / 1.0 | `#000` |
| Bölüm başlığı ("Yeni bir hayatla tanışın") | 32 / 700 / 1.375 | `#000` |
| Kart başlığı ("Yetim Sponsorluğu") | 28 / 700 / 1.1 | `#333` |
| Bölüm üst başlığı ("Oradaydık") | 20 / 700 / 1.3 | `#000` |
| Açıklama paragrafı | 20 / 400 / 1.2 | `#333` |
| Gövde | 18 / 400 / 1.1 | `#000` / `#333` |
| Link başlık ("Bir kuyu, bir köyün kaderi") | 18 / 600 | `#1FAD4E` |
| Buton | 16 / 400 | Beyaz |
| Küçük üst başlık ("BAĞIŞ YAPIN") | 15–16 / 400 / BÜYÜK HARF | Yardımcı renk veya `#4C4C4C` |

---

## 4. Arayüz bileşenleri

| Bileşen | Değerler |
|---|---|
| **Ana buton** | Zemin: kampanya rengi veya `#1FAD4E`. Beyaz metin, 16 px. Dolgu `15px 26px` (ikili butonlarda `15px 18px`). Köşe **8 px**. Gölge yok. Solda beyaz kalp ikonu ("Zekat Bağışla" gibi) |
| **Hap (pill) buton** | Köşe **100 px**, dolgu `8px 18px`, 18 px / 500. "Hikayeyi oku" yeşil dolu, "Tümünü Gör" kenarlıklı |
| **Metin buton** | Zeminsiz, siyah veya yeşil metin ("Detaylı Bilgi", "Tüm Haberleri Gör") |
| **Kart** | Beyaz zemin, `1px solid #E4E4E4`, köşe **6 px**, gölge `0 3px 5px rgba(0,0,0,.05)`, iç boşluk 32 px. Üstte fotoğraf, altta ikonlu kategori etiketi, kalın başlık, kısa açıklama, buton |
| **İlerleme çubuğu** | Yükseklik 8 px, köşe 4 px, zemin `#E4E4E4`, dolu kısım `#1FAD4E` |
| **Genel köşe** | 8 px (en sık), 6 px (kart), 4 px (küçük öğe), %50 (yuvarlak ikon) |
| **Yükseltilmiş gölge** | `0 1px 10px rgba(0,0,0,.1), 0 2px 15px rgba(0,0,0,.05)` (açılır menüler) |
| **Konteyner** | 1170 px (içerik), 970 / 770 / 570 px dar sütunlar |
| **Header** | Beyaz, alt çizgi `#E4E4E4`, ortada logo, sağda yeşil "Bağış Yap" |
| **Mobil alt menü** | Ana Sayfa, Bağış Yap (kalp), Sepetim, Oturum Aç. Aktif öğe yeşil |

---

## 5. Görsel dil ve fotoğraf

- **Genel his:** Beyaz, ferah, temiz. Renk, fotoğraftan ve kampanya butonundan geliyor. Arka plan süslemesi yok.
- **Fotoğraf:** Gerçek insanlar, yakın plan, yüzler net, umut ve gülümseme ön planda. Acı veya sefalet sömürüsü yerine onur ve umut. Sitede fotoğraflar kartın üst kısmını tam genişlikte kaplıyor.
- **Kampanya afişleri (hero slider):** Kampanya adı çok kalın, büyük harf, sıkışık bir başlıkla yazılıyor (ör. "ZEKAT"), altına el yazısı (script) bir vurgu kelimesi geliyor (ör. "iyileştirir"). Kampanya rengi (Zekat'ta kırmızı) başlıkta, geri kalan siyah. Bu yazı fontları kampanyaya özel; genel kimlik fontu Proxima Soft.
- **İkonlar:** Çizgi tarzı, yuvarlak uçlu, tek renk. Kategori etiketlerinde kampanya rengiyle küçük ikon + gri metin.

---

## 6. Dil ve ton

- **Kurum adı:** İHH İnsani Yardım Vakfı. İngilizce: IHH Humanitarian Relief Foundation.
- **Tanım (sitenin meta açıklaması):** "Savaş, afet, yoksulluk olan bölgelerle birlikte 123 ülkede din, dil, ırk, millet ve mezhep ayrımı yapmaksızın faaliyet yürütür."
- **CTA'lar kısa ve eylem odaklı:** Bağış Yap, Şimdi Bağış Yap, Zekat Bağışla, Sponsor Ol, Projeyi Destekle, Su Kuyusu Aç, Hikayeyi oku, Detaylı Bilgi.
- **Ton:** Sıcak, doğrudan, "siz" diye hitap eden; bağışçıyı iyiliğin ortağı yapan ("Zekatınızla Burhan iyileşti", "Siz de sponsor olun, bir yetimin hayatına iyilikle dokunun").

---

## 7. Reklam ve sosyal medya tasarım kuralları

Siteden türetilmiş uygulama kuralları. Yeni tasarımlar bunlara göre yapılır:

1. **Zemin:** Beyaz veya `#F8F8F8`. Tam renkli zemin gerekiyorsa koyu yeşil `#026839` ya da kampanya rengi. Fotoğraftan yeni renk türetilmez.
2. **Renk seçimi:** Kampanyanın kendi rengi CTA'da kullanılır (Yetim → `#22ABE6`, Zekat → `#E84545`, Gazze/acil → `#E23131`, genel bağış/su/diğer → `#1FAD4E`). Bir tasarımda en fazla bir kampanya rengi + kurumsal yeşil + nötrler.
3. **Font:** Proxima Soft (yoksa Nunito). Başlık 700, gövde 400, CTA 600–700. Serif yok.
4. **CTA:** Köşe 8 px dikdörtgen veya 100 px hap. Beyaz kalın metin, isteğe bağlı solda kalp ikonu.
5. **Logo:** Her görselde resmi logo dosyası (açık zeminde renkli, koyu/fotoğraf üstünde beyaz). Logo yazıyla yeniden çizilmez.
6. **Fotoğraf:** Gerçek saha fotoğrafı, yüz net, umut odaklı. Köşe yuvarlatılacaksa 6–8 px.
7. **Kart dili:** Bilgi kutuları için beyaz kart + `#E4E4E4` ince kenar + 6 px köşe.
8. **Rakamlar:** Kalın Proxima Soft, kampanya rengi veya `#026839`.

**Yapılmayacaklar:** Serif başlık fontu, fotoğraftan türetilmiş yeni renk paleti (bordo, şeftali vb.), logonun renklerini değiştirmek, açık yeşil/sarı üstünde beyaz metin, yoğun degrade veya parlak efekt.

---

## 8. CSS token'ları

`ihh-tokens.css` dosyasında hazır. Özet:

```css
:root{
  --ihh-green-dark:#026839; --ihh-gold:#A09744;
  --ihh-green:#1FAD4E; --ihh-focus:rgba(31,173,78,.3);
  --ihh-zekat:#E84545; --ihh-emergency:#E23131; --ihh-orphan:#22ABE6;
  --ihh-blue:#0C8ADF; --ihh-yellow:#E2B513; --ihh-lime:#7FBF40;
  --ihh-black:#000; --ihh-ink:#333; --ihh-gray-700:#4C4C4C; --ihh-gray-600:#666;
  --ihh-gray-400:#999; --ihh-gray-300:#CCC; --ihh-line:#E4E4E4;
  --ihh-bg-strip:#F2F2F7; --ihh-bg-soft:#F8F8F8; --ihh-white:#FFF;
  --ihh-font:"proxima-soft","Proxima Soft",Tajawal,Nunito,Arial,sans-serif;
  --ihh-tracking:-0.016em;
  --ihh-radius:8px; --ihh-radius-card:6px; --ihh-radius-pill:100px;
  --ihh-shadow-card:0 3px 5px rgba(0,0,0,.05);
}
```

---

## 9. Açık noktalar

- İngilizce ve Arapça logo dosyaları sitede yok. Kurumsal iletişimden istenmeli.
- Kampanya afişlerindeki kalın başlık ve el yazısı fontlarının adı siteden okunamıyor (görsel içine gömülü). Gerekirse tasarım ekibine sorulmalı.
- Proxima Soft lisanslı bir font (Adobe Fonts). Figma'da kullanmak için Mac'te Adobe Fonts'tan etkinleştirilmeli.
