import React from 'react';
import {clamp01, easeInOutCubic, easeOutCubic, lerp} from '../../lib/anim';
import {SANS, SOLUK} from './tokens';

/** Hareket kuralları (stiller/temel/stil-rehberi.md §5) */
export const HIZ = {kelime: 0.22, panel: 0.38, cizgi: 0.32, sayac: 0.5};

export const p = (t: number, at: number, dur: number, ease = easeOutCubic) => ease(clamp01((t - at) / dur));

/** Kelime: maskeden yukarı kayarak girer (taşma yok), sonra sabit kalır. */
export const Reveal: React.FC<{t: number; at: number; children: React.ReactNode; style?: React.CSSProperties}> = ({t, at, children, style}) => {
  const k = p(t, at, HIZ.kelime);
  return (
    <span style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'top', paddingBottom: '0.12em', marginBottom: '-0.12em', ...style}}>
      <span style={{display: 'inline-block', transform: `translateY(${(1 - k) * 110}%)`}}>{children}</span>
    </span>
  );
};

/** Panel: kontrollü yerleşme (küçük ölçek + yukarıdan iniş, taşma yok). */
export const panel = (t: number, at: number, dy = 40) => {
  const k = p(t, at, HIZ.panel);
  return {opacity: clamp01(k * 3), transform: `translateY(${(1 - k) * -dy}px) scale(${lerp(0.96, 1, k)})`};
};

/** Kendini çizen çizgi (SVG yolu boyunca). */
export const DrawPath: React.FC<{t: number; at: number; d: string; len: number; color: string; width: number; dur?: number; cap?: 'round' | 'butt'}> = ({
  t, at, d, len, color, width, dur = HIZ.cizgi, cap = 'round',
}) => {
  const k = p(t, at, dur, easeInOutCubic);
  if (k <= 0) return null;
  return <path d={d} fill="none" stroke={color} strokeWidth={width} strokeLinecap={cap} strokeDasharray={`${len * k} ${len}`} />;
};

/** Sayaç: a'dan b'ye, Türkçe ondalık virgülüyle. */
export const sayac = (t: number, at: number, a: number, b: number, digits = 2) => {
  const k = p(t, at, HIZ.sayac, easeInOutCubic);
  return lerp(a, b, k).toFixed(digits).replace('.', ',');
};

/** Bölüm etiketi: "02 · SORUN" (sol üst, güvenli alanda). */
export const Etiket: React.FC<{no: number; ad: string; x: number; y: number; size: number}> = ({no, ad, x, y, size}) => (
  <div style={{position: 'absolute', left: x, top: y, fontFamily: SANS, fontWeight: 600, fontSize: size, letterSpacing: size * 0.18, color: SOLUK}}>
    {String(no).padStart(2, '0')} · {ad.toLocaleUpperCase('tr-TR')}
  </div>
);
