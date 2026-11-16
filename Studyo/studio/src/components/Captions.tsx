import React from 'react';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {clamp01} from '../lib/anim';
import {useFormat} from '../lib/format';
import {Sentence} from '../lib/time';
import {gecisPlakasi} from '../lib/gecis/plaka';

export type CaptionTheme = 'dark' | 'light';
export type CaptionStyle = {
  font: string;
  weight: number;
  letterSpacing: number;
  lineHeight: number;
  themes: Record<CaptionTheme, {base: string; hi: string; shadow: string}>;
  /** Açık zemin plakasının rengi "r,g,b" */
  plate: string;
  /** Format varsayılanının yerine punto (1080 kısa kenara göre) */
  punto?: number;
};

const INTER = loadInter('normal', {weights: ['500', '600', '700'], subsets: ['latin', 'latin-ext']}).fontFamily;

/** Stilden bağımsız varsayılan: Inter, sarı vurgu. Stil paketleri kendi CaptionStyle'ını verir. */
export const ALTYAZI_NOTR: CaptionStyle = {
  font: INTER,
  weight: 600,
  letterSpacing: 0,
  lineHeight: 1.2,
  themes: {
    dark: {base: '#FFFFFF', hi: '#FFD400', shadow: '0 2px 12px rgba(0,0,0,0.8), 0 0 2px rgba(0,0,0,0.9)'},
    light: {base: '#111111', hi: '#C2410C', shadow: '0 0 10px rgba(255,255,255,0.9)'},
  },
  plate: '255,255,255',
};

/**
 * Kelime kelime altyazı. Cümlenin tamamı önceden yerleşir (kayma yok); kelime söylendiği an belirir ve vurgu rengine döner.
 * Bant konumu ve punto formattan gelir (profiller/formatlar.json → altyazi).
 * plate (0–1): açık zeminde yumuşak kenarlı plaka. Arka plandaki yazılarla çakışmayı önler.
 */
export const Captions: React.FC<{t: number; sentences: Sentence[]; theme: CaptionTheme; plate?: number; stil?: CaptionStyle}> = ({
  t,
  sentences,
  theme,
  plate = theme === 'light' ? 1 : 0,
  stil = ALTYAZI_NOTR,
}) => {
  const {f, w, h, unit} = useFormat();
  if (gecisPlakasi()) return null; // geçiş plakasında altyazı yok: asıl çizimde geçişin üstünde
  const idx = sentences.findIndex((s, i) => {
    const next = sentences[i + 1];
    const from = s.start - 0.08;
    const to = Math.min(next ? next.start - 0.1 : Infinity, s.end + 0.55);
    return t >= from && t < to;
  });
  if (idx < 0) return null;
  const s = sentences[idx];
  if (!s.words.length) return null;
  const next = sentences[idx + 1];
  const to = Math.min(next ? next.start - 0.1 : Infinity, s.end + 0.55);
  const pageOpacity = clamp01((to - t) / 0.16);
  const th = stil.themes[theme];
  const side = Math.round(f.altyazi.yan * (w > h ? 1 : unit));

  return (
    <div
      style={{
        position: 'absolute',
        left: side,
        right: side,
        top: Math.round(f.altyazi.ust * h),
        height: Math.round(f.altyazi.yukseklik * h),
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: pageOpacity,
      }}
    >
      <div
        style={{
          fontFamily: stil.font,
          fontWeight: stil.weight,
          fontSize: Math.round((stil.punto ?? f.altyazi.punto) * unit),
          lineHeight: stil.lineHeight,
          textAlign: 'center',
          textWrap: 'balance' as React.CSSProperties['textWrap'],
          letterSpacing: stil.letterSpacing,
          padding: '8px 22px',
          borderRadius: 10,
          background: `rgba(${stil.plate},${0.9 * plate})`,
          boxShadow: `0 0 26px 20px rgba(${stil.plate},${0.9 * plate})`,
        }}
      >
        {s.words.map((wd, i) => {
          const appear = clamp01((t - (wd.start - 0.06)) / 0.12);
          const hiIn = clamp01((t - (wd.start - 0.06)) / 0.08);
          const hiOut = clamp01((t - (wd.end + 0.05)) / 0.18);
          const hi = hiIn * (1 - hiOut);
          return (
            <span
              key={i}
              style={{
                opacity: appear,
                color: hi > 0.5 ? th.hi : th.base,
                textShadow: th.shadow,
                display: 'inline-block',
                transform: `translateY(${(1 - appear) * 10}px)`,
                marginRight: i < s.words.length - 1 ? '0.26em' : 0,
              }}
            >
              {wd.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};
