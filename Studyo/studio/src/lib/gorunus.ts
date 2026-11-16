import {createContext, useContext, type CSSProperties} from 'react';
import {getInputProps} from 'remotion';
import {BitisAyar} from '../components/Bitis';
import {CaptionStyle} from '../components/Captions';
import {fontYukle} from './fontlar';

/**
 * Görünüş: bir videonun renk, yazı, doku, ışık ve hareket karakteri. Veri olarak durur (JSON):
 *   videoya özel  → videos/<id>/gorunus.json   (planda 3 seçenek: a, b, c; seçimi kullanıcı yapar)
 *   seri          → stiller/<ad>/gorunus.json  (birden çok videonun bilerek paylaştığı görünüş)
 * Kurallar: zanaat.md §1c. Python tarafı aynı dosyaları okur (ortak.py: kontrast, çeşitlilik).
 */
export type YaziRolu = {
  aile: string; // src/lib/fontlar.ts'teki aile adı, ör. "Bebas Neue"
  agirlik: number;
  italik?: boolean;
  /** harf aralığı (em), ör. -0.04 */
  aralik?: number;
  buyukHarf?: boolean;
};

export type Secenek = {
  ad: string;
  /** Bu görünüşün tek cümlelik fikri: filmin görsel kuralına nasıl hizmet ediyor. */
  fikir: string;
  renk: {arka: string; murekkep: string; vurgu: string; ikincil?: string; soluk?: string; kagit?: string};
  yazi: {baslik: YaziRolu; govde: YaziRolu; aksan?: YaziRolu};
  /** Sözel kararlar: sahne kodu bunlara uyar, eleştirmen bunlarla karşılaştırır. */
  doku?: string;
  isik?: string;
  hareket?: string;
  bitis?: BitisAyar;
  yasak?: string[];
  yol?: Yol;
};

/**
 * Yol (planda üç yol, 2a): seçenek aynı kanca karesinin bir görünüşü değil, ayrı bir fikirdir. Sahne kodu seçeneğin harfine göre
 * dallanır (useSecenek()); plan tamamlanınca seçilmeyen dallar silinir.
 */
export type Yol = {
  ad: string;
  tek_cumle: string;
  yontem: string;
  kural: string;
  kanca: string;
  olaganustu_an: string;
  insan_yolu: string;
  neden_akilda_kalir: string;
  risk: string;
  uretim: string;
  kredi_tahmini?: number;
};

export type GorunusDosyasi = {secim: string | null; secenekler: Record<string, Secenek>; deneme_kare?: number | string | null; yol_modu?: boolean};

/** Sahne kodunun kullandığı çözülmüş stil. Eski stil paketlerinin STIL nesnesiyle aynı alanları taşır (arka, murekkep, vurgu, yazi, altyazi). */
export type Stil = {
  ad: string;
  /** Görünüş dosyasındaki seçeneğin harfi (a, b, c); seri ve nötr görünüşte yok. Yol modunda sahne buna göre dallanır: useSecenek(). */
  harf?: string;
  arka: string;
  murekkep: string;
  vurgu: string;
  ikincil: string;
  soluk: string;
  kagit: string;
  /** CSS font-family değerleri */
  yazi: {baslik: string; govde: string; aksan: string};
  /** ağırlık, aralık, büyük harf: yazı stilini kurmak için `yaziStili(STIL, 'baslik')` */
  rol: {baslik: YaziRolu; govde: YaziRolu; aksan: YaziRolu};
  altyazi: CaptionStyle;
  altyaziTema: 'dark' | 'light';
  bitis: BitisAyar;
  doku: string;
  isik: string;
  hareket: string;
};

const parlaklik = (hex: string) => {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((x) => (x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(',');

/** Görünüş seçeneğinden stil kurar ve yazı tiplerini yükler (modül düzeyinde çağrılmalı). */
export const stilOlustur = (s: Secenek): Stil => {
  const aksan = s.yazi.aksan ?? s.yazi.baslik;
  const baslik = fontYukle(s.yazi.baslik.aile, [s.yazi.baslik.agirlik], s.yazi.baslik.italik);
  const govde = fontYukle(s.yazi.govde.aile, [s.yazi.govde.agirlik, 600]);
  const aks = fontYukle(aksan.aile, [aksan.agirlik], aksan.italik);
  const acik = parlaklik(s.renk.arka) > 0.4;
  const kagit = s.renk.kagit ?? s.renk.arka;
  return {
    ad: s.ad,
    arka: s.renk.arka,
    murekkep: s.renk.murekkep,
    vurgu: s.renk.vurgu,
    ikincil: s.renk.ikincil ?? s.renk.vurgu,
    soluk: s.renk.soluk ?? s.renk.murekkep,
    kagit,
    yazi: {baslik, govde, aksan: aks},
    rol: {baslik: s.yazi.baslik, govde: s.yazi.govde, aksan},
    altyazi: {
      font: govde,
      weight: 600,
      letterSpacing: 0,
      lineHeight: 1.2,
      themes: {
        dark: {base: '#FFFFFF', hi: s.renk.vurgu, shadow: '0 2px 12px rgba(0,0,0,0.75), 0 0 2px rgba(0,0,0,0.9)'},
        light: {base: s.renk.murekkep, hi: s.renk.vurgu, shadow: 'none'},
      },
      plate: rgb(acik ? s.renk.arka : '#FFFFFF'),
    },
    altyaziTema: acik ? 'light' : 'dark',
    bitis: s.bitis ?? {},
    doku: s.doku ?? '',
    isik: s.isik ?? '',
    hareket: s.hareket ?? '',
  };
};

/** Henüz seçenek yazılmamış videoda paketin kırılmaması için nötr görünüş. */
export const NOTR: Secenek = {
  ad: 'nötr (görünüş seçilmedi)',
  fikir: 'Yer tutucu',
  renk: {arka: '#FFFFFF', murekkep: '#111111', vurgu: '#C2410C'},
  yazi: {baslik: {aile: 'Inter', agirlik: 800}, govde: {aile: 'Inter', agirlik: 600}},
};

/** Görünüş dosyasındaki bütün seçenekleri kurar (deneme karelerinde her biri çizilebilsin diye). */
export const stilleriKur = (G: GorunusDosyasi): Record<string, Stil> => {
  const s = Object.entries(G.secenekler ?? {});
  return Object.fromEntries(s.length ? s.map(([k, v]) => [k, {...stilOlustur(v), harf: k}]) : [['_notr', stilOlustur(NOTR)]]);
};

/** Bu render'ın görünüşü: --props '{"gorunus":"b"}' (deneme kareleri) > dosyadaki seçim > ilk seçenek > nötr. */
export const stilSec = (S: Record<string, Stil>, G: GorunusDosyasi): Stil => {
  const istenen = (getInputProps() as {gorunus?: string}).gorunus;
  if (istenen) {
    if (!S[istenen]) throw new Error(`Görünüş yok: ${istenen} (seçenekler: ${Object.keys(S).join(', ')})`);
    return S[istenen];
  }
  return (G.secim && S[G.secim]) || Object.values(S)[0];
};

/**
 * Türkçe büyük harf: "bir" → "BİR" (JavaScript'in varsayılanı "BIR" yapar). Yalnız büyük harfli yazı tiplerinde (Bebas Neue)
 * metni her zaman bununla yaz: yazı tipi küçük "i"yi noktasız "I" çizer. CSS textTransform ancak lang="tr" altında doğru çalışır (şablon verir).
 */
export const buyuk = (metin: string) => metin.toLocaleUpperCase('tr-TR');
/** Küçük harfleri de büyük harf olarak çizen yazı tipleri (pipeline/gorunus.py YALNIZ_BUYUK ile aynı). */
export const YALNIZ_BUYUK = new Set(['Bebas Neue']);
/** Başlık rolünün yazı tipi yalnız büyük harfliyse metni Türkçe büyük harfe çevirir. */
export const baslikMetni = (S: Stil, metin: string) => (YALNIZ_BUYUK.has(S.rol.baslik.aile) || S.rol.baslik.buyukHarf ? buyuk(metin) : metin);

/** Rolün CSS yazı stili: yaziStili(STIL, 'baslik') → {fontFamily, fontWeight, letterSpacing, textTransform, fontStyle} */
export const yaziStili = (S: Stil, rol: 'baslik' | 'govde' | 'aksan'): CSSProperties => {
  const r = S.rol[rol];
  return {
    fontFamily: S.yazi[rol],
    fontWeight: r.agirlik,
    letterSpacing: r.aralik !== undefined ? `${r.aralik}em` : undefined,
    textTransform: r.buyukHarf ? 'uppercase' : undefined,
    fontStyle: r.italik ? 'italic' : undefined,
  };
};

const Ctx = createContext<Stil | null>(null);
export const StilSaglayici = Ctx.Provider;
/** Sahne bileşenlerinde: const STIL = useStil(); */
export const useStil = (): Stil => {
  const s = useContext(Ctx);
  if (!s) throw new Error('useStil(): StilSaglayici dışında');
  return s;
};
/**
 * Yol modunda (gorunus.json → yol_modu) çizilen seçeneğin harfi: --props '{"gorunus":"b"}' (deneme karesi) > seçim > ilk seçenek.
 * Kanca karesi yola göre dallanır: const yol = useSecenek(); {yol === 'a' && <Dolap />}{yol === 'b' && <Pencere />}
 * Plan tamamlanınca seçilmeyen dallar silinir.
 */
export const useSecenek = (): string => useStil().harf ?? '';
