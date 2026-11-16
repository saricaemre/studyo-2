import React from 'react';
import {clamp01, easeInOutCubic, easeOutBack, lerp} from '../../lib/anim';
import {CORMORANT, INK, LAL, LORA} from './tokens';

/** Kavram kartı: terim + tek satır tanım. Haritanın kenarına iğnelenir. */
export const ConceptCard: React.FC<{t: number; from: number; to: number; term: string; def: string; visible: number}> = ({t, from, to, term, def, visible}) => {
  if (t < from || t > to + 0.5) return null;
  const inP = easeOutBack(clamp01((t - from) / 0.45));
  const outP = easeInOutCubic(clamp01((t - to) / 0.4));
  const x = lerp(-520, 64, inP) - outP * 600;
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: 236,
        width: 470,
        padding: '26px 30px 28px',
        background: 'linear-gradient(160deg, #F6ECD3, #E9D9B4)',
        borderRadius: 6,
        transform: `rotate(${lerp(-7, -2.2, clamp01((t - from) / 0.45))}deg)`,
        boxShadow: '0 18px 40px rgba(0,0,0,0.45), 0 3px 8px rgba(0,0,0,0.3)',
        opacity: visible,
        border: '1px solid rgba(43,33,24,0.35)',
      }}
    >
      <div style={{position: 'absolute', top: -12, left: '50%', width: 26, height: 26, marginLeft: -13, borderRadius: 13, background: LAL, boxShadow: 'inset -4px -4px 0 rgba(0,0,0,0.25), 0 3px 6px rgba(0,0,0,0.4)'}} />
      <div style={{fontFamily: LORA, fontWeight: 700, fontSize: 20, letterSpacing: 5, color: LAL}}>KAVRAM</div>
      <div style={{fontFamily: CORMORANT, fontStyle: 'italic', fontWeight: 700, fontSize: 70, lineHeight: 1.0, color: INK, margin: '6px 0 10px'}}>{term}</div>
      <div style={{fontFamily: LORA, fontWeight: 500, fontSize: 29, lineHeight: 1.3, color: INK}}>{def}</div>
    </div>
  );
};
