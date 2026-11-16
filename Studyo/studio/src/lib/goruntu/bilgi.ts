// Gerçek görüntü kaydı (public/<film>/goruntu/bilgi.json; ./st goruntu yazar): dosya, boyut, kare hızı, derinlik, maske, kadraj yolları.
// Bir kez okunur (delayRender), bütün bileşenler paylaşır. Kare dizisi değil: video karesi Remotion'un kare çıkarıcısından (OffthreadVideo yolu).
import {useLayoutEffect, useState} from 'react';
import {staticFile, useDelayRender} from 'remotion';
import {NoReactInternals} from 'remotion/no-react';
import {kaplayanPencere, type Pencere} from '../uc/goruntu';
import type {FormatKey} from '../format';

export type GoruntuKaydi = {
  tur: 'video' | 'gorsel';
  /** public/<film>/'e göre: varliklar/goruntu/<ad>.mp4 (ya da üretim plakası varliklar/uretim/…) */
  dosya: string;
  en: number;
  boy: number;
  fps?: number;
  kare?: number;
  sure?: number;
  kisi?: boolean | null;
  kaynak: string;
  derinlik?: string;
  maske?: string;
  /** yüz gizleme için genişletilmiş maske (zamanda ±4 kare, uzayda %2,5) */
  maske_genis?: string;
  kadraj?: Partial<Record<FormatKey, {pencere: [number, number]; kareler: Pencere[]}>>;
};

const sozler = new Map<string, Promise<Record<string, GoruntuKaydi>>>();
const kayitlar = new Map<string, Record<string, GoruntuKaydi>>();

/** Filmin gerçek görüntü kaydı; okunana kadar kare bekletilir. */
export const useGoruntuKaydi = (film: string, ad: string): GoruntuKaydi | null => {
  const [B, setB] = useState(() => kayitlar.get(film) ?? null);
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  useLayoutEffect(() => {
    if (B) return;
    const h = delayRender(`gerçek görüntü kaydı: ${film}`);
    let s = sozler.get(film);
    if (!s) {
      s = fetch(staticFile(`${film}/goruntu/bilgi.json`)).then((r) => {
        if (!r.ok) throw new Error(`public/${film}/goruntu/bilgi.json yok: önce ./st goruntu ekle ${film} …`);
        return r.json();
      });
      sozler.set(film, s);
    }
    let iptal = false, birakildi = false;
    const birak = () => {
      if (!birakildi) continueRender(h);
      birakildi = true;
    };
    s.then((j) => {
      kayitlar.set(film, j);
      if (!iptal) setB(j);
      birak();
    }, (e) => cancelRender(e));
    return () => {
      iptal = true;
      birak();
    };
  }, [B, film, delayRender, continueRender, cancelRender]);
  if (!B) return null;
  const k = B[ad];
  if (!k) throw new Error(`gerçek görüntü kaydında yok: ${ad} (./st goruntu liste ${film})`);
  return k;
};

/** Kaynağın i. karesi (videoda; görselde 0) ve bu formattaki kırpma penceresi. Kadraj yolu yoksa yalnız oranlar eşitken bütün kare;
 *  değilse hata: merkezden kırpma yok (CLAUDE.md format kuralı) → ./st goruntu kadraj <film> <ad> --format <F>. */
export const pencereAl = (k: GoruntuKaydi, key: FormatKey, i: number, w: number, h: number, film: string, ad: string): Pencere => {
  const yol = k.kadraj?.[key];
  if (yol) return yol.kareler[Math.max(0, Math.min(yol.kareler.length - 1, i))];
  if (Math.abs(k.en / k.boy - w / h) / (w / h) < 0.02) return kaplayanPencere(k.en, k.boy, w, h);
  throw new Error(`${ad}: ${key} için kadraj yolu yok (kaynak ${k.en}×${k.boy}). Merkezden kırpma yok: ./st goruntu kadraj ${film} ${ad} --format ${key}`);
};

/** Kaynak karesinin numarası: film karesi + başlangıç (sn), hız; ara format filmin kare hızındadır. */
export const kaynakKaresi = (k: GoruntuKaydi, kare: number, fps: number, baslangic = 0, hiz = 1) =>
  k.tur === 'video' ? Math.max(0, Math.min((k.kare ?? 1) - 1, Math.round(baslangic * fps + kare * hiz))) : 0;

/** Video karesinin adresi: Remotion'un kare çıkarıcısı (OffthreadVideo ile aynı yol; yalnız çizimde, ./st kare / render). */
export const videoKaresiAdresi = (src: string, i: number, fps: number) =>
  NoReactInternals.getOffthreadVideoSource({src, currentTime: i / fps, transparent: false, toneMapped: true});
