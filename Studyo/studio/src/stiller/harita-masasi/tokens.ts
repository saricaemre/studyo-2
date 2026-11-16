import {loadFont as loadLora} from '@remotion/google-fonts/Lora';
import {loadFont as loadCormorant} from '@remotion/google-fonts/CormorantGaramond';

export const LORA = loadLora('normal', {weights: ['500', '600', '700'], subsets: ['latin', 'latin-ext']}).fontFamily;
export const CORMORANT = loadCormorant('normal', {weights: ['600', '700'], subsets: ['latin', 'latin-ext']}).fontFamily;
loadCormorant('italic', {weights: ['500', '600', '700'], subsets: ['latin', 'latin-ext']});

export const INK = '#2B2118';
export const LAL = '#A63A2B';
export const LAPIS = '#2E4A7D';
export const VARAK = '#C9A45C';
export const PARSOMEN = '#EFE3C8';
export const WOOD = '#7A5232';

/** Harita Masası altyazı stili: Lora, söylenen kelime varak renginde, açık zeminde parşömen plaka. */
export const HARITA_ALTYAZI = {
  font: LORA,
  weight: 600,
  letterSpacing: 0.2,
  lineHeight: 1.22,
  themes: {
    dark: {base: '#F6EEDB', hi: '#E9C779', shadow: '0 3px 14px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.9)'},
    light: {base: '#2A1F16', hi: '#9A5F12', shadow: '0 0 14px rgba(246,236,212,1), 0 0 6px rgba(246,236,212,1), 0 0 2px rgba(246,236,212,1)'},
  },
  plate: '244,234,210',
};

/** Stil paketi arayüzü (her paket aynı alanları verir; şablon Video.tsx bunu kullanır). */
export const STIL = {
  arka: '#1a1009',
  murekkep: INK,
  vurgu: LAL,
  ikincil: LAPIS,
  soluk: '#8A7A62',
  kagit: PARSOMEN,
  yazi: {govde: LORA, baslik: CORMORANT, aksan: CORMORANT},
  altyazi: HARITA_ALTYAZI,
};
