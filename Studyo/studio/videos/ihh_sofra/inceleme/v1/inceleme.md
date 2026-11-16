# İnceleme — ihh_sofra · v1 · 2026-10-22

> **Eleştirmen kuralı:** Ne yapmak istediğini anlatma. Yalnız render edilmiş karelere (`kontak.png`, `kareler/`) ve ölçüme (`olcum.md`) bak.
> En büyük 3 kusuru bul. Her birine zaman damgası, kanıt ve **yerel** düzeltme yaz. Yalnız o bölümleri onar, etkilenen kareleri yeniden render et (`./st kare`).
> Yeni kanıt yoksa yeni deneme de yok. İlk MP4 bir prototiptir, onay değil.
> **Kör eleştiri:** `./st elestir <id>` → `elestiri.md` (filmi hiç görmemiş bir oturum). Onun P0/P1 maddeleri önceliklidir; katılmadığın maddeyi aşağıda gerekçesiyle yaz.

## Puan kartı (1–5)
| Boyut | Puan | Kanıt (kare / zaman) |
|---|---|---|
| Kanca: ilk 2 sn gerçek bir kanca mı? | 3 | f00000 arayüz ağırlıklı; kalp ancak 1,55 sn'de doğuyor (elestiri.md #3) |
| Okunurluk: telefon boyutunda okunuyor mu, güvenli alanda mı? | 2 | 9x16 f00512: doruk cümlesi üst kenarda kesik, arayüz bandında (P0; orijinal sofra dikey sürümünde de aynı) |
| Süreklilik: renk, yazı ve karakterler sahneler arasında tutarlı mı? | 5 | Tek çizim dili, aynı göz/yanak/gülüş; eleştirmen güçlü yan saydı |
| Hareket: her hareketten sonra nereye bakılacağı belli mi? | 4 | Kalp her sahnede yön veriyor; 5,3–7,5 sn uçuşta kahraman küçük (≈130 px) |
| Ses senkronu: efekt ve görüntü aynı karede mi? | 3 | Efektler olaylara oturuyor; olaylar müzik vuruşuna değil (13/38 işaret ≤ 2 kare) |
| Mesaj: tek cümle anlaşılıyor mu? | 5 | Kör eleştirmenin "anladığım mesaj"ı amaçlananla aynı |
| Doğruluk: ekrandaki her şey kaynaklı mı? | 5 | Rakam ve iddia yok; logo ve adres kurumun |
| Poster: son kare kapak olacak kadar güçlü mü? | 5 | 16x9 f00659 temiz kart; 9x16'da üst bölgeye bakılmalı |

## En büyük 3 kusur
### 1. Dikeyde doruk cümlesi kesik ve platform arayüzünün altında (P0)
- **Zaman:** 00:17.07 · f00512 · 9x16 (10,9–17,7 sn boyunca)
- **Kanıt:** `kareler-9x16/f00512.png` ve `cikti/ihh_sofra_9x16_v1.mp4` 17,07 sn: "…and fills their table with joy!" y≈0–55 px, harflerin üstü kırpık; lamba ipleri yazının içinden geçiyor. Orijinal `IHH/sofra/renders/…-9x16.mp4` aynı kareyi taşıyor (karşılaştırıldı): içe aktarmadan değil, filmin kendisinden.
- **Yerel düzeltme:** `hf/ihh_sofra/index.html` → `html[data-format="9x16"] #s3` ve `.cap` kuralları: altyazıyı güvenli alana (ST.guvenli.ust = %10 → y ≥ 200) indir, krem plaka ekle; 9x16'da lamba iplerini yazının arkasında bitir; sofrayı ~300 px yukarı al.
- **Durum:** açık (filmin yerleşimi değişir: kullanıcı onayı bekliyor)

### 2. Yolculuğun ortası boş: 2,2 sn yeni olay yok, kahraman küçük (P1)
- **Zaman:** 00:05.30–00:07.50 · f00159 → f00225 · bütün formatlar
- **Kanıt:** `olcum.md` "En uzun olaysız aralık 2,20 sn (çıta 1,6)"; elestiri.md #2 (kalp ≈130 px, gökyüzü yalnız gradyan kayması).
- **Yerel düzeltme:** 5,3–7,5 sn arasına iki olay: kalp bir bulutun içinden geçsin (bulut dağılır + süzülme sesi), balonun yanında kanat çırpıp el sallasın; kamera kalbe ×1,6 yaklaşsın. Yeni işaretler `cues.json`'a (y_bulut, y_balon).
- **Durum:** açık

### 3. Kanca bir bağış arayüzüyle açılıyor; kahraman 1,55 sn'de doğuyor (P1)
- **Zaman:** 00:00.00–00:01.55 · f00000, f00046 · bütün formatlar
- **Kanıt:** elestiri.md #3; `kontak-16x9.png` ilk hücre: telefon arayüzü (One-time/Monthly, Secure donation) karenin odağı.
- **Yerel düzeltme:** başparmak 0. karede düğmenin üstünde başlasın (thumb tween 0,7 → 0,1 sn), dokunuş 0,5 sn'de, kalp 0,7 sn'de doğsun; ilk karede One-time/Monthly ve "Secure donation" gizli, dokunuştan sonra gelsin.
- **Durum:** açık

## Ölçümde kalanlar (kusur listesine girmedi, kararı kullanıcının)
- **Vuruş uyumu ❌:** olaylar 120 BPM ızgarasından çoğunlukla 0,1–0,2 sn önce düşüyor. Ya olaylar en yakın vuruşa kaydırılır ya da müzik 0,2 sn erken başlatılır (zanaat §6).
- **Deterministiklik:** kareler iki sırada çizilince 11,0 sn'de 367, 14,67 sn'de 14 piksel ayrışıyor (ileri yönde çizilen MP4'te etkisi yok). HyperFrames lint aynı yerleri `gsap_repeated_fromto_without_baseline` / `overlapping_gsap_tweens` diye uyarıyor (kol ve kanat tween'leri): başlangıç pozuna `tl.set` taban konursa düzelir.

## Onarım kanıtı
| Kusur | Önce | Sonra |
|---|---|---|
| 1 | [önce karesi] | [sonra karesi] |

## Hâlâ insan gözü gerekenler
- [madde]
