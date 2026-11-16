import React from 'react';
import {clamp01, easeInOutCubic, easeOutCubic, lerp, rand} from '../../lib/anim';
import {CORMORANT, LAL, PARSOMEN} from './tokens';

const RIM = Array.from({length: 64}, (_, i) => {
  const a = (i / 64) * Math.PI * 2;
  const r = 100 + (rand(i * 2.7) - 0.5) * 7;
  return `${Math.cos(a) * r},${Math.sin(a) * r}`;
}).join(' ');

/** Yıl mührü: basılır (darbe), sonra köşeye küçülür. Kanalın imzası. */
export const Seal: React.FC<{t: number; at: number; year: string; ring: string; visible: number}> = ({t, at, year, ring, visible}) => {
  if (t < at - 0.05) return null;
  const hit = clamp01((t - at) / 0.16);
  const scale = lerp(1.9, 1, easeOutCubic(hit));
  const settle = easeInOutCubic(clamp01((t - at - 1.5) / 0.6));
  const cx = lerp(700, 830, settle);
  const cy = lerp(330, 268, settle);
  const s = scale * lerp(1, 0.62, settle);
  const splat = clamp01((t - at - 0.1) / 0.3);
  return (
    <svg width={1080} height={1920} style={{position: 'absolute', left: 0, top: 0, opacity: clamp01(hit * 4) * visible}}>
      <defs>
        <path id="sealRing" d="M0,0 m-74,0 a74,74 0 1,1 148,0 a74,74 0 1,1 -148,0" />
      </defs>
      <g transform={`translate(${cx},${cy}) rotate(-9) scale(${s})`}>
        {Array.from({length: 7}).map((_, i) => {
          const a = rand(i * 5.1) * Math.PI * 2;
          const d = 112 + rand(i * 3.3) * 30 * splat;
          return <circle key={i} cx={Math.cos(a) * d} cy={Math.sin(a) * d} r={2 + rand(i) * 4} fill={LAL} opacity={0.8 * splat} />;
        })}
        <polygon points={RIM} fill={LAL} opacity={0.93} />
        <circle r={88} fill="none" stroke={PARSOMEN} strokeWidth={3} opacity={0.85} />
        <circle r={58} fill="none" stroke={PARSOMEN} strokeWidth={2} opacity={0.7} />
        <text fontFamily={CORMORANT} fontWeight={700} fontSize={19} letterSpacing={5} fill={PARSOMEN} opacity={0.95}>
          <textPath href="#sealRing" startOffset="0">{ring}</textPath>
        </text>
        <text y={17} textAnchor="middle" fontFamily={CORMORANT} fontWeight={700} fontSize={50} fill={PARSOMEN}>
          {year}
        </text>
      </g>
    </svg>
  );
};
