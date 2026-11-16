import {Pt, clamp01, easeInCubic, easeInOutCubic, easeOutCubic, lerp} from './anim';

export type Cam = {x: number; y: number; s: number};
export type CamOp =
  | {type: 'pan'; t: number; dur: number; to: Cam}
  | {type: 'diveIn'; t: number; dur: number; p: Pt; k: number}
  | {type: 'diveOut'; t: number; dur: number; p: Pt; to: Cam; k: number};

/** Kameranın baktığı noktanın ekrandaki yeri (altyazı bandının üstü). */
export const FOCUS: Pt = [540, 720];

export const toScreen = (p: Pt, c: Cam): Pt => [(p[0] - c.x) * c.s + FOCUS[0], (p[1] - c.y) * c.s + FOCUS[1]];

export type Dive = {kind: 'in' | 'out'; raw: number; q: Pt};

/**
 * pan: hedefe yumuşak kayma (ölçek log uzayında).
 * diveIn/diveOut: "haritaya dalış" — nokta ekrandaki yerinde sabit kalır, ölçek k katına büyür/küçülür.
 */
export const camAt = (t: number, initial: Cam, ops: CamOp[]): {cam: Cam; dive: Dive | null} => {
  let cur: Cam = {...initial};
  let dive: Dive | null = null;
  for (const op of ops) {
    if (t < op.t) break;
    const raw = clamp01((t - op.t) / op.dur);
    if (op.type === 'pan') {
      const p = easeInOutCubic(raw);
      cur = {x: lerp(cur.x, op.to.x, p), y: lerp(cur.y, op.to.y, p), s: Math.exp(lerp(Math.log(cur.s), Math.log(op.to.s), p))};
      dive = null;
    } else if (op.type === 'diveIn') {
      const q = toScreen(op.p, cur);
      const s = cur.s * Math.pow(op.k, easeInCubic(raw));
      cur = {x: op.p[0] - (q[0] - FOCUS[0]) / s, y: op.p[1] - (q[1] - FOCUS[1]) / s, s};
      dive = {kind: 'in', raw, q};
    } else {
      const q = toScreen(op.p, op.to);
      const s = op.to.s * Math.pow(op.k, 1 - easeOutCubic(raw));
      cur = {x: op.p[0] - (q[0] - FOCUS[0]) / s, y: op.p[1] - (q[1] - FOCUS[1]) / s, s};
      dive = {kind: 'out', raw, q};
    }
  }
  return {cam: cur, dive};
};
