import React, {useMemo} from 'react';
import {AbsoluteFill, getInputProps, useCurrentFrame, useVideoConfig} from 'remotion';
import {GlGecis} from '../lib/gecis';

/**
 * Geçiş önizlemesi (./st gecis onizle → katalog/onizleme/gecis/<ad>.mp4; panel → Kütüphane → Geçişler): 1,5 sn, iki NÖTR kart
 * (görünüşten bağımsız gri tonlar; ızgara, biçim ve harf geçişin bükmesini gösterir). 0–5. kare A, 6–38 geçiş, 39–44 B.
 * Kartlar tuvalde kod ile çizilir (dosya yok); --props '{"ad": "<geçiş>"}'.
 */
const kart = (w: number, h: number, tur: 'a' | 'b'): HTMLCanvasElement => {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const x = c.getContext('2d');
  if (!x) throw new Error('2B tuval yok');
  const [zemin, cizgi, bicim, harf] = tur === 'a' ? ['#383838', '#4a4a4a', '#9c9c9c', '#ececec'] : ['#d2d2d2', '#bdbdbd', '#6a6a6a', '#262626'];
  x.fillStyle = zemin;
  x.fillRect(0, 0, w, h);
  x.strokeStyle = cizgi;
  x.lineWidth = Math.max(1, w / 180);
  const adim = w / 8;
  for (let i = 1; i < 8; i++) {
    x.beginPath();
    x.moveTo(i * adim, 0);
    x.lineTo(i * adim, h);
    x.moveTo(0, i * adim);
    x.lineTo(w, i * adim);
    x.stroke();
  }
  x.fillStyle = bicim;
  if (tur === 'a') {
    x.beginPath();
    x.arc(w * 0.5, h * 0.5, w * 0.3, 0, Math.PI * 2);
    x.fill();
  } else {
    x.save();
    x.translate(w * 0.5, h * 0.5);
    x.rotate(Math.PI / 4);
    x.fillRect(-w * 0.24, -w * 0.24, w * 0.48, w * 0.48);
    x.restore();
  }
  x.fillStyle = harf;
  x.font = `700 ${Math.round(h * 0.42)}px sans-serif`;
  x.textAlign = 'center';
  x.textBaseline = 'middle';
  x.fillText(tur === 'a' ? 'A' : 'B', w * 0.5, h * 0.53);
  return c;
};

export const GecisOnizleme: React.FC = () => {
  const ad = (getInputProps() as {ad?: string}).ad ?? 'Fade';
  const f = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const [A, B] = useMemo(() => [kart(width, height, 'a'), kart(width, height, 'b')], [width, height]);
  const x = Math.max(0, Math.min(1, (f - 5) / 34));
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <GlGecis ad={ad} from={A} to={B} ilerleme={x * x * (3 - 2 * x)} />
    </AbsoluteFill>
  );
};
