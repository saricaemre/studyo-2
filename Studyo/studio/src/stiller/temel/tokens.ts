import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadSerif} from '@remotion/google-fonts/InstrumentSerif';
import {CaptionStyle} from '../../components/Captions';

export const SANS = loadInter('normal', {weights: ['400', '500', '600', '700', '800'], subsets: ['latin', 'latin-ext']}).fontFamily;
export const SERIF = loadSerif('italic', {weights: ['400'], subsets: ['latin', 'latin-ext']}).fontFamily;

export const KAGIT = '#F2EFE8';
export const MUREKKEP = '#141414';
// v1.2 (2026-10-22, öğrenimler #24): #FF5A1F kâğıtta 2,7:1'di; aynı ton koyulaştırıldı → 3,7:1 (büyük, kalın yazı ve şekil için).
export const TURUNCU = '#D9480F';
export const MAVI = '#2F5BFF';
export const SOLUK = '#8C877C';
export const CIZGI = '#D9D4C8';

export const TEMEL_ALTYAZI: CaptionStyle = {
  font: SANS,
  weight: 600,
  letterSpacing: -0.2,
  lineHeight: 1.2,
  themes: {
    dark: {base: '#FFFFFF', hi: TURUNCU, shadow: '0 2px 12px rgba(0,0,0,0.75)'},
    light: {base: MUREKKEP, hi: TURUNCU, shadow: 'none'},
  },
  plate: '242,239,232',
};

/** Stil paketi arayüzü */
export const STIL = {
  arka: KAGIT,
  murekkep: MUREKKEP,
  vurgu: TURUNCU,
  ikincil: MAVI,
  soluk: SOLUK,
  kagit: KAGIT,
  yazi: {govde: SANS, baslik: SANS, aksan: SERIF},
  altyazi: TEMEL_ALTYAZI,
};
