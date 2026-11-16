import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {rand} from '../../lib/anim';
import {CORMORANT, INK, LAL, LAPIS, LORA, PARSOMEN, VARAK} from './tokens';

export type MarkaProps = {ad: string; slogan: string; monogram: string};
export const MARKA_VARSAYILAN: MarkaProps = {ad: 'Harita Masası', slogan: 'Bir olay · bir harita · bir ders', monogram: 'HM'};

/** Kanalın imzası olan mühür, statik hali. Halka metni = kanal adı. */
const MuhurIsareti: React.FC<{r: number; ring: string; center: string}> = ({r, ring, center}) => {
  const rim = Array.from({length: 72}, (_, i) => {
    const a = (i / 72) * Math.PI * 2;
    const rr = 100 + (rand(i * 2.7) - 0.5) * 7;
    return `${Math.cos(a) * rr},${Math.sin(a) * rr}`;
  }).join(' ');
  return (
    <svg width={r * 2.6} height={r * 2.6} viewBox="-130 -130 260 260" style={{overflow: 'visible'}}>
      <defs>
        <path id="markaRing" d="M0,0 m-74,0 a74,74 0 1,1 148,0 a74,74 0 1,1 -148,0" />
      </defs>
      <g transform="rotate(-9)">
        <ellipse cx={6} cy={10} rx={104} ry={102} fill="rgba(20,8,0,0.35)" />
        <polygon points={rim} fill={LAL} />
        <circle r={88} fill="none" stroke={PARSOMEN} strokeWidth={3} opacity={0.9} />
        <circle r={58} fill="none" stroke={PARSOMEN} strokeWidth={2} opacity={0.75} />
        <text fontFamily={CORMORANT} fontWeight={700} fontSize={17} letterSpacing={4} fill={PARSOMEN}>
          <textPath href="#markaRing" startOffset="0">{ring}</textPath>
        </text>
        <text y={center.length > 2 ? 14 : 19} textAnchor="middle" fontFamily={CORMORANT} fontStyle="italic" fontWeight={700} fontSize={center.length > 2 ? 40 : 56} fill={PARSOMEN}>
          {center}
        </text>
      </g>
    </svg>
  );
};

const Kerteler: React.FC<{w: number; h: number; cx: number; cy: number; op: number}> = ({w, h, cx, cy, op}) => (
  <svg width={w} height={h} style={{position: 'absolute', left: 0, top: 0}}>
    {Array.from({length: 32}).map((_, i) => {
      const a = (i * Math.PI) / 16;
      const col = i % 4 === 0 ? INK : i % 2 === 0 ? LAPIS : LAL;
      return <line key={i} x1={cx} y1={cy} x2={cx + Math.cos(a) * 4000} y2={cy + Math.sin(a) * 4000} stroke={col} strokeWidth={i % 4 === 0 ? 1.6 : 1} opacity={op} />;
    })}
  </svg>
);

/** Profil resmi 800×800 (daire içinde gösterilir: önemli her şey ortadaki dairede). */
export const KanalAvatar: React.FC<MarkaProps> = ({ad, monogram}) => (
  <AbsoluteFill style={{background: PARSOMEN}}>
    <Img src={staticFile('textures/parchment.png')} style={{position: 'absolute', left: -160, top: -160, width: 1120, height: 1120, objectFit: 'cover'}} />
    <Kerteler w={800} h={800} cx={400} cy={400} op={0.22} />
    <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 50%, rgba(0,0,0,0) 45%, rgba(60,30,10,0.35) 72%)'}} />
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <MuhurIsareti r={230} ring={`${ad.toLocaleUpperCase('tr-TR')} · ${ad.toLocaleUpperCase('tr-TR')} · `} center={monogram} />
    </AbsoluteFill>
  </AbsoluteFill>
);

/** Kanal kapağı 2560×1440. Yazı ortadaki 1546×423 güvenli alanda (telefonda yalnız orası görünür). */
export const KanalBanner: React.FC<MarkaProps> = ({ad, slogan, monogram}) => (
  <AbsoluteFill style={{background: '#1a1009'}}>
    <Img src={staticFile('textures/wood.jpg')} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover'}} />
    <div style={{position: 'absolute', left: 300, right: 300, top: 330, bottom: 330, boxShadow: '0 40px 90px 10px rgba(0,0,0,0.6)'}}>
      <Img src={staticFile('textures/parchment.png')} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover'}} />
      <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
        <Kerteler w={1960} h={780} cx={1660} cy={390} op={0.2} />
      </div>
    </div>
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 60, width: 1546, height: 423, justifyContent: 'center'}}>
        <MuhurIsareti r={120} ring={`${ad.toLocaleUpperCase('tr-TR')} · `} center={monogram} />
        <div>
          <div style={{fontFamily: CORMORANT, fontStyle: 'italic', fontWeight: 700, fontSize: 150, lineHeight: 1, color: INK}}>{ad}</div>
          <div style={{fontFamily: LORA, fontWeight: 600, fontSize: 46, letterSpacing: 6, color: LAL, marginTop: 18}}>{slogan.toLocaleUpperCase('tr-TR')}</div>
          <div style={{height: 3, width: 420, background: VARAK, marginTop: 22}} />
        </div>
      </div>
    </AbsoluteFill>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse 80% 70% at 50% 50%, rgba(0,0,0,0) 55%, rgba(10,5,0,0.55) 100%)'}} />
  </AbsoluteFill>
);
