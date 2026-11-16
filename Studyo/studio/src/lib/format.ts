import {useVideoConfig} from 'remotion';
import formatlar from '../../profiller/formatlar.json';

export type FormatKey = '9x16' | '16x9' | '1x1' | '4x5';
export type FormatSpec = {
  w: number;
  h: number;
  ad: string;
  guvenli: {ust: number; alt: number; sol: number; sag: number};
  altyazi: {ust: number; yukseklik: number; yan: number; punto: number};
};

export const FORMATLAR = formatlar as unknown as Record<FormatKey, FormatSpec>;

export const formatOf = (w: number, h: number): FormatKey => {
  const hit = (Object.keys(FORMATLAR) as FormatKey[]).find((k) => FORMATLAR[k].w === w && FORMATLAR[k].h === h);
  if (!hit) throw new Error(`Tanımsız format ${w}×${h} (profiller/formatlar.json)`);
  return hit;
};

/** Kompozisyonun formatı + güvenli alan (piksel). Aynı hikâye her formatta ayrı yerleşim kurar. */
export const useFormat = () => {
  const {width, height} = useVideoConfig();
  const key = formatOf(width, height);
  const f = FORMATLAR[key];
  const safe = {
    left: f.guvenli.sol * width,
    right: width - f.guvenli.sag * width,
    top: f.guvenli.ust * height,
    bottom: height - f.guvenli.alt * height,
  };
  return {key, w: width, h: height, f, safe, dikey: height > width, unit: Math.min(width, height) / 1080};
};
