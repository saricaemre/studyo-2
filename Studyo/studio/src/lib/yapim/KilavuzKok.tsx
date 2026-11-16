import React, {useLayoutEffect, useRef} from 'react';
import {Composition, Still, continueRender, delayRender, getInputProps, useCurrentFrame, useVideoConfig} from 'remotion';
import formatlar from '../../../profiller/formatlar.json';
import {Guvenli, kilavuzSvg, olc, veriSvg} from './kilavuz';

/**
 * Kılavuz kipi (yapım filmi, ./st yapim): girdi `yapim` verilince (`--props '{"yapim": {"kip": "kilavuz"}}'`) src/index.ts kökü bununla
 * sarar: her kompozisyonun filmi aynen çizilir, üstüne yerleşim kutuları, güvenli alan ve üçte bir çizgileri (kip "kilavuz") ya da kutuların
 * veri pikselleri (kip "veri") gelir. Girdi yoksa kök hiç sarılmaz: filmlerin kareleri bayt bayt aynı (kural 11).
 * Filmin kodu değişmez; kutular çizilmiş DOM'dan ölçülür (src/lib/yapim/kilavuz.ts, HyperFrames'te de aynı çekirdek).
 */
export type YapimGirdisi = {kip?: 'kilavuz' | 'veri'};

const FORMATLAR = formatlar as unknown as Record<string, {w: number; h: number; guvenli: Guvenli}>;
const guvenliAlan = (w: number, h: number): Guvenli | null => Object.values(FORMATLAR).find((f) => f && f.w === w && f.h === h)?.guvenli ?? null;

const Katman: React.FC<{film: React.RefObject<HTMLDivElement | null>; kip: 'kilavuz' | 'veri'}> = ({film, kip}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const h = delayRender('Kılavuz: yerleşim kutuları');
    let bitti = false;
    const ciz = () => {
      if (bitti || !film.current || !ref.current) return;
      bitti = true;
      const k = olc(film.current, width, height);
      ref.current.innerHTML = kip === 'veri' ? veriSvg(k, width, height) : kilavuzSvg(k, width, height, guvenliAlan(width, height));
      continueRender(h);
    };
    // Remotion bileşimi önce ekran dışındaki bir kapta (portal, genişlik 0) kurar, çizimden önce görünür kaba taşır: kutular ancak o zaman
    // doğru. Görseller ve yazı tipleri de yerleşimi değiştirir: kap boyutlanınca, hepsi inince ölç.
    let ro: ResizeObserver | null = null;
    const hazir = () => !!film.current && film.current.getBoundingClientRect().width > 0;
    const olcunce = () => {
      const bekleyen = film.current ? Array.from(film.current.querySelectorAll('img')).filter((i) => !i.complete) : [];
      Promise.all([document.fonts.ready, ...bekleyen.map((i) => new Promise((r) => {
        i.addEventListener('load', r, {once: true});
        i.addEventListener('error', r, {once: true});
      }))]).then(ciz);
    };
    if (hazir()) olcunce();
    else if (film.current) {
      ro = new ResizeObserver(() => {
        if (hazir()) {
          ro?.disconnect();
          olcunce();
        }
      });
      ro.observe(film.current);
    }
    return () => {
      ro?.disconnect();
      if (!bitti) {
        bitti = true;
        continueRender(h);
      }
    };
  }, [frame, kip, width, height, film]);
  return <div ref={ref} style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', pointerEvents: 'none'}} />;
};

const sarili = new WeakMap<object, React.FC<Record<string, unknown>>>();
const sar = (C: React.ComponentType<Record<string, unknown>>): React.FC<Record<string, unknown>> => {
  const var_ = sarili.get(C);
  if (var_) return var_;
  const S: React.FC<Record<string, unknown>> = (p) => {
    const film = useRef<HTMLDivElement>(null);
    const kip = ((getInputProps() as {yapim?: YapimGirdisi}).yapim?.kip) ?? 'kilavuz';
    return (
      <div style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%'}}>
        <div ref={film} style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%'}}>
          <C {...p} />
        </div>
        <Katman film={film} kip={kip} />
      </div>
    );
  };
  sarili.set(C, S);
  return S;
};

/** Kökteki her Composition ve Still'in bileşenini kılavuzla sarar (kök yalnız kayıt listesidir: kancasız bir fonksiyon). */
export const kilavuzluKok = (Kok: React.FC): React.FC => {
  const K: React.FC = () => {
    const el = Kok({}) as React.ReactElement<{children?: React.ReactNode}>;
    const cevir = (c: React.ReactNode): React.ReactNode => {
      if (!React.isValidElement(c)) return c;
      const e = c as React.ReactElement<{component?: React.ComponentType<Record<string, unknown>>; children?: React.ReactNode}>;
      if ((e.type === Composition || e.type === Still) && e.props.component) return React.cloneElement(e, {component: sar(e.props.component)});
      if (e.type === React.Fragment) return React.cloneElement(e, {}, React.Children.map(e.props.children, cevir));
      return e;
    };
    return <>{React.Children.map(el.props.children, cevir)}</>;
  };
  return K;
};
