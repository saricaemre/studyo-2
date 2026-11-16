/**
 * Görünüşlerin kullanabildiği yazı tipleri (Google Fonts). Hepsinde Türkçe karakter alt kümesi (latin-ext) var;
 * ğ ş ı İ glifleri ./st gorunus deneme karesinde gözle doğrulanır.
 * Görünüş dosyasında yazı tipi aile adıyla anılır ("Bebas Neue"); tür, üç seçeneğin birbirinden farklı olmasını denetlemek içindir.
 * Yeni yazı tipi: aşağıya bir import + FONTLAR'a bir satır. Yalnız kullanılan görünüşlerin yazı tipleri yüklenir.
 */
import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';
import * as Inter from '@remotion/google-fonts/Inter';
import * as InstrumentSans from '@remotion/google-fonts/InstrumentSans';
import * as Manrope from '@remotion/google-fonts/Manrope';
import * as WorkSans from '@remotion/google-fonts/WorkSans';
import * as SpaceGrotesk from '@remotion/google-fonts/SpaceGrotesk';
import * as BricolageGrotesque from '@remotion/google-fonts/BricolageGrotesque';
import * as Syne from '@remotion/google-fonts/Syne';
import * as Unbounded from '@remotion/google-fonts/Unbounded';
import * as Sora from '@remotion/google-fonts/Sora';
import * as Rubik from '@remotion/google-fonts/Rubik';
import * as Archivo from '@remotion/google-fonts/Archivo';
import * as ArchivoNarrow from '@remotion/google-fonts/ArchivoNarrow';
import * as ArchivoBlack from '@remotion/google-fonts/ArchivoBlack';
import * as BarlowCondensed from '@remotion/google-fonts/BarlowCondensed';
import * as Oswald from '@remotion/google-fonts/Oswald';
import * as BebasNeue from '@remotion/google-fonts/BebasNeue';
import * as Anton from '@remotion/google-fonts/Anton';
import * as InstrumentSerif from '@remotion/google-fonts/InstrumentSerif';
import * as PlayfairDisplay from '@remotion/google-fonts/PlayfairDisplay';
import * as DMSerifDisplay from '@remotion/google-fonts/DMSerifDisplay';
import * as Fraunces from '@remotion/google-fonts/Fraunces';
import * as Newsreader from '@remotion/google-fonts/Newsreader';
import * as EBGaramond from '@remotion/google-fonts/EBGaramond';
import * as CormorantGaramond from '@remotion/google-fonts/CormorantGaramond';
import * as Lora from '@remotion/google-fonts/Lora';
import * as LibreBaskerville from '@remotion/google-fonts/LibreBaskerville';
import * as JetBrainsMono from '@remotion/google-fonts/JetBrainsMono';
import * as IBMPlexMono from '@remotion/google-fonts/IBMPlexMono';
import * as SpaceMono from '@remotion/google-fonts/SpaceMono';
import * as DMMono from '@remotion/google-fonts/DMMono';
import * as RobotoSlab from '@remotion/google-fonts/RobotoSlab';
import * as ZillaSlab from '@remotion/google-fonts/ZillaSlab';
import * as Caveat from '@remotion/google-fonts/Caveat';
import * as Fredoka from '@remotion/google-fonts/Fredoka';
import * as Baloo2 from '@remotion/google-fonts/Baloo2';
import * as Nunito from '@remotion/google-fonts/Nunito';
import * as Quicksand from '@remotion/google-fonts/Quicksand';
import * as Grandstander from '@remotion/google-fonts/Grandstander';
import * as DynaPuff from '@remotion/google-fonts/DynaPuff';
import * as LilitaOne from '@remotion/google-fonts/LilitaOne';
import * as PatrickHand from '@remotion/google-fonts/PatrickHand';
import * as Kalam from '@remotion/google-fonts/Kalam';
import * as Pangolin from '@remotion/google-fonts/Pangolin';

export type FontTuru = 'grotesk' | 'karakterli grotesk' | 'dar' | 'serif başlık' | 'serif metin' | 'mono' | 'slab' | 'el yazısı' | 'yuvarlak';
type Bilgi = {fontFamily: string; fonts: Record<string, Record<string, unknown>>};
type Modul = {getInfo: () => Bilgi; loadFont: (stil?: never, secenek?: never) => {fontFamily: string}};

const MODULLER: Record<string, {mod: unknown; tur: FontTuru}> = {
  Inter: {mod: Inter, tur: 'grotesk'},
  InstrumentSans: {mod: InstrumentSans, tur: 'grotesk'},
  Manrope: {mod: Manrope, tur: 'grotesk'},
  WorkSans: {mod: WorkSans, tur: 'grotesk'},
  SpaceGrotesk: {mod: SpaceGrotesk, tur: 'karakterli grotesk'},
  BricolageGrotesque: {mod: BricolageGrotesque, tur: 'karakterli grotesk'},
  Syne: {mod: Syne, tur: 'karakterli grotesk'},
  Unbounded: {mod: Unbounded, tur: 'karakterli grotesk'},
  Sora: {mod: Sora, tur: 'karakterli grotesk'},
  Rubik: {mod: Rubik, tur: 'karakterli grotesk'},
  Archivo: {mod: Archivo, tur: 'dar'},
  ArchivoNarrow: {mod: ArchivoNarrow, tur: 'dar'},
  ArchivoBlack: {mod: ArchivoBlack, tur: 'dar'},
  BarlowCondensed: {mod: BarlowCondensed, tur: 'dar'},
  Oswald: {mod: Oswald, tur: 'dar'},
  BebasNeue: {mod: BebasNeue, tur: 'dar'},
  Anton: {mod: Anton, tur: 'dar'},
  InstrumentSerif: {mod: InstrumentSerif, tur: 'serif başlık'},
  PlayfairDisplay: {mod: PlayfairDisplay, tur: 'serif başlık'},
  DMSerifDisplay: {mod: DMSerifDisplay, tur: 'serif başlık'},
  Fraunces: {mod: Fraunces, tur: 'serif başlık'},
  Newsreader: {mod: Newsreader, tur: 'serif metin'},
  EBGaramond: {mod: EBGaramond, tur: 'serif metin'},
  CormorantGaramond: {mod: CormorantGaramond, tur: 'serif metin'},
  Lora: {mod: Lora, tur: 'serif metin'},
  LibreBaskerville: {mod: LibreBaskerville, tur: 'serif metin'},
  JetBrainsMono: {mod: JetBrainsMono, tur: 'mono'},
  IBMPlexMono: {mod: IBMPlexMono, tur: 'mono'},
  SpaceMono: {mod: SpaceMono, tur: 'mono'},
  DMMono: {mod: DMMono, tur: 'mono'},
  RobotoSlab: {mod: RobotoSlab, tur: 'slab'},
  ZillaSlab: {mod: ZillaSlab, tur: 'slab'},
  Caveat: {mod: Caveat, tur: 'el yazısı'},
  Fredoka: {mod: Fredoka, tur: 'yuvarlak'},
  Baloo2: {mod: Baloo2, tur: 'yuvarlak'},
  Nunito: {mod: Nunito, tur: 'yuvarlak'},
  Quicksand: {mod: Quicksand, tur: 'yuvarlak'},
  Grandstander: {mod: Grandstander, tur: 'yuvarlak'},
  DynaPuff: {mod: DynaPuff, tur: 'yuvarlak'},
  LilitaOne: {mod: LilitaOne, tur: 'yuvarlak'},
  PatrickHand: {mod: PatrickHand, tur: 'el yazısı'},
  Kalam: {mod: Kalam, tur: 'el yazısı'},
  Pangolin: {mod: Pangolin, tur: 'el yazısı'},
};

/** Aile adı ("Bebas Neue") → modül ve tür. */
export const FONTLAR: Record<string, {mod: Modul; tur: FontTuru}> = Object.fromEntries(
  Object.values(MODULLER).map(({mod, tur}) => [(mod as Modul).getInfo().fontFamily, {mod: mod as Modul, tur}]),
);

/**
 * Yazı tipini yükler, CSS aile adını döndürür. Yazı tipinde olmayan ağırlıklar atlanır (yoksa en yakını);
 * italik yoksa düz kullanılır. Modül düzeyinde çağrılmalı (Remotion yazı tipini render başlamadan bekler).
 */
export const fontYukle = (aile: string, agirliklar: number[], italik = false): string => {
  const f = FONTLAR[aile];
  if (!f) throw new Error(`Yazı tipi listede yok: ${aile} (src/lib/fontlar.ts). Mevcut: ${Object.keys(FONTLAR).join(', ')}`);
  const info = f.mod.getInfo();
  const stil = italik && info.fonts.italic ? 'italic' : 'normal';
  const var_ = Object.keys(info.fonts[stil]).map(Number);
  let w = [...new Set(agirliklar)].filter((x) => var_.includes(x));
  if (!w.length) w = [var_.reduce((a, b) => (Math.abs(b - agirliklar[0]) < Math.abs(a - agirliklar[0]) ? b : a))];
  const yukle = f.mod.loadFont as unknown as (s: string, o: {weights: string[]; subsets: string[]}) => {fontFamily: string};
  return yukle(stil, {weights: w.map(String), subsets: ['latin', 'latin-ext']}).fontFamily;
};

/**
 * Değişken yazı tipleri: yerel dosya (public/fontlar/<ad>/, lisans dosyası yanında), Google Fonts modülü değil.
 * Niyetli altyazı (src/lib/niyet) kullanır: ağırlık ve genişlik kelime kelime değişir (font-variation-settings).
 * Roboto Flex (Font Bureau, OFL 1.1): ağırlık 100–1000 ve genişlik 25–151 ile Google Fonts'taki değişken grotesklerin en geniş iki
 * ekseni; optik boyut ve derece (GRAD) da var; ekran için çizilmiş, açık iç boşluklu, 64 px'te okunaklı; Türkçe glifleri tam
 * (ı latin'de, ğ ş İ latin-ext'te). @remotion/google-fonts'ta modülü yok: dosyalar Google Fonts'tan bir kez indirildi.
 * Satır bölme için karakter genişlikleri public/fontlar/roboto-flex/olcu.json'da (pipeline/yazi_olcu.py).
 */
export const DEGISKEN = {
  'Roboto Flex': {
    tur: 'grotesk' as FontTuru,
    lisans: 'OFL-1.1',
    eksenler: {wght: [100, 1000], wdth: [25, 151], opsz: [8, 144], GRAD: [-200, 150]},
    dosyalar: [
      {yol: 'fontlar/roboto-flex/roboto-flex-latin.woff2',
        aralik: 'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD'},
      {yol: 'fontlar/roboto-flex/roboto-flex-latin-ext.woff2',
        aralik: 'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF'},
    ],
  },
} as const;
export type DegiskenAile = keyof typeof DEGISKEN;

const yuklenen = new Set<string>();

/**
 * Değişken yazı tipini yükler (bir kez), CSS aile adını döndürür. Bileşenin içinden çağrılabilir: ilk çağrı Remotion'u yazı tipi
 * inene kadar bekletir (delayRender); kullanmayan filmler hiç yüklemez.
 */
export const degiskenFontYukle = (aile: DegiskenAile): string => {
  if (yuklenen.has(aile) || typeof document === 'undefined') return aile;
  yuklenen.add(aile);
  const D = DEGISKEN[aile];
  const h = delayRender(`Değişken yazı tipi: ${aile}`);
  Promise.all(D.dosyalar.map((d) => {
    const f = new FontFace(aile, `url(${staticFile(d.yol)}) format('woff2')`,
      {weight: `${D.eksenler.wght[0]} ${D.eksenler.wght[1]}`, stretch: `${D.eksenler.wdth[0]}% ${D.eksenler.wdth[1]}%`, unicodeRange: d.aralik, display: 'block'});
    document.fonts.add(f);
    return f.load();
  })).then(() => continueRender(h), (e) => cancelRender(e));
  return aile;
};
