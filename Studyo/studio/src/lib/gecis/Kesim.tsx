import React, {useState} from 'react';
import {AbsoluteFill, getInputProps, getRemotionEnvironment, staticFile, useCurrentFrame} from 'remotion';
import {useFormat} from '../format';
import {Plaka, plakaYolu} from '../Plaka';
import {GlGecis} from './GlGecis';
import type {GecisParamDegeri} from './kutuphane';
import {gecisPlakasi} from './plaka';

/**
 * Kesim: iki sahne arasında gölgelendirici geçişi (oturum 6a). Tanım script.json → shot.gecis'tedir
 * ({"gl": "BookFlip", "kare": 18, "param": {…}, "kesim": "<işaret>", "neden": "…"}; vuruştan sonrakine geçiş), ./st onu
 * public/<id>/gecis.json'a kare olarak yazar (tek hesap: pipeline/gecis.py). Film o dosyayı içe aktarır:
 *   import gecisJson from '../../public/<id>/gecis.json';  const GECIS = gecisJson as GecisVerisi;
 *   <Kesim ad="b1" gecis={GECIS} a={<Sahne1 />} b={<Sahne2 />} />
 * Zaman: pencere [kesim − N/2, kesim + N/2); giden sahne N/2 kare uzar, gelen N/2 kare erken başlar, ikisi de aynı MUTLAK zamanda
 * çizilir (Sequence kaydırması yok). Filmin süresi ve işaretleri değişmez. Pencerenin dışında yalnız a ya da b.
 * DOM sahneleri doğrudan gölgelendiriciye girmez: ./st pencerenin karelerini önce iki kez çizer (geçiş plakası; yalnız bir taraf, üst katmansız)
 * ve asıl çizimde <GlGecis> bu iki PNG'yi birleştirir. Bu yüzden film üst katmanlarını (yazı, logo) <UstKatman> içine koyar; altyazı, etiket ve
 * Bitis'in rötuşu kendiliğinden geçişin üstünde kalır (bükülmez). Zincir: b tarafı başka bir <Kesim> olabilir (A → B → C).
 */
export type KesimTanimi = {ad: string; gl: string; kare: number; param: Record<string, GecisParamDegeri>; egri: 'yumusak' | 'dogrusal';
  kesim: number; bas: number; son: number; vurus?: string; sonraki?: string | null;
  /** Karma film (6b): iki taraf da opak plaka sahnesi ve kesim onların sınırında → plakalar doğrudan gölgelendiriciye girer (geçiş plakası yok). */
  dogrudan?: {a: string; b: string}};
export type GecisVerisi = {id: string; fps: number; kume: Partial<Record<string, string>>; kesimler: Record<string, KesimTanimi>};

/** Penceredeki karenin ilerlemesi: yumusak((f − bas + 1) / (N + 1)); pencerenin ilk karesi 0'dan, son karesi 1'den bir adım uzakta. */
export const gecisIlerleme = (k: KesimTanimi, f: number) => {
  const x = Math.max(0, Math.min(1, (f - k.bas + 1) / (k.kare + 1)));
  return k.egri === 'dogrusal' ? x : x * x * (3 - 2 * x);
};

const plakaAdi = (f: number) => `p${String(f).padStart(5, '0')}.png`;

/** Karma film: kesimin bir tarafındaki <Plaka>'nın o karedeki görüntüsü. Zincirde iç içe <Kesim> açılır (a tarafında iç kesimin b'si görünür). */
const plakaKaynagi = (el: React.ReactNode, taraf: 'a' | 'b', format: string, f: number): string | null => {
  if (!React.isValidElement(el)) return null;
  const p = el.props as Record<string, unknown>;
  if (el.type === Plaka) return plakaYolu(p.veri as Parameters<typeof plakaYolu>[0], p.sahne as string, format, f);
  if (el.type === Kesim) return plakaKaynagi((taraf === 'a' ? p.b : p.a) as React.ReactNode, taraf, format, f);
  return null;
};

export const Kesim: React.FC<{ad: string; gecis: GecisVerisi; a: React.ReactNode; b: React.ReactNode}> = ({ad, gecis, a, b}) => {
  const frame = useCurrentFrame();
  const {key, unit} = useFormat();
  const [yok, setYok] = useState(false);
  const K = gecis.kesimler[ad];
  if (!K) throw new Error(`Kesim ${ad}: ${gecis.id}/gecis.json'da yok (script.json → shot.gecis; ./st gecis ${gecis.id} durum)`);
  const P = gecisPlakasi();
  if (P) {
    // Plaka çizimi: bu kesimse yalnız istenen taraf; başka bir kesimse (pencereler çakışmaz) düz kesim
    if (P.kesim === ad) return <AbsoluteFill>{P.taraf === 'a' ? a : b}</AbsoluteFill>;
    return <AbsoluteFill>{frame < K.kesim ? a : b}</AbsoluteFill>;
  }
  if (frame < K.bas) return <AbsoluteFill>{a}</AbsoluteFill>;
  if (frame >= K.son) return <AbsoluteFill>{b}</AbsoluteFill>;
  const p = gecisIlerleme(K, frame);
  const kume = (getInputProps() as {gecisKume?: string}).gecisKume ?? gecis.kume?.[key];
  const cizim = getRemotionEnvironment().isRendering;
  if (K.dogrudan) {
    // iki plaka sahnesi arasında: motorların plakaları doğrudan (ikinci çizim yok)
    const ya = plakaKaynagi(a, 'a', key, Math.max(K.bas, Math.min(K.son - 1, Math.round(frame))));
    const yb = plakaKaynagi(b, 'b', key, Math.max(K.bas, Math.min(K.son - 1, Math.round(frame))));
    if (!ya || !yb) {
      if (cizim) throw new Error(`Kesim ${ad}: iki tarafı da plaka sahnesi (${K.dogrudan.a} → ${K.dogrudan.b}) ama a ve b <Plaka veri sahne> değil ya da küme yok.`);
      return <AbsoluteFill>{p < 0.5 ? a : b}</AbsoluteFill>;
    }
    return <GlGecis ad={K.gl} from={ya} to={yb} ilerleme={p} param={K.param} onYok={cizim ? undefined : () => setYok(true)} />;
  }
  if (!kume || yok) {
    if (cizim) throw new Error(`${gecis.id}: ${key} geçiş plakası yok (kesim ${ad}). Plakaları stüdyo çizer: ./st kare / temsili / render (pipeline/gecis.py).`);
    // Remotion Studio önizlemesi: düz bindirme + not
    return (
      <AbsoluteFill>
        <AbsoluteFill>{a}</AbsoluteFill>
        <AbsoluteFill style={{opacity: p}}>{b}</AbsoluteFill>
        <div style={{position: 'absolute', left: 24 * unit, bottom: 24 * unit, padding: `${6 * unit}px ${14 * unit}px`, borderRadius: 10 * unit,
          background: 'rgba(0,0,0,0.6)', color: '#fff', fontSize: 26 * unit, fontFamily: 'sans-serif'}}>
          {`${K.gl} önizlemesi: düz bindirme (geçiş plakası yok; ./st kare ile çizilir)`}
        </div>
      </AbsoluteFill>
    );
  }
  // Hareket bulanıklığının ara zamanları: en yakın plaka, ilerleme kesirli kareden (pencerenin içinde kalır)
  const f = Math.max(K.bas, Math.min(K.son - 1, Math.round(frame)));
  const yol = (taraf: 'a' | 'b') => staticFile(`${gecis.id}/gecis/${kume}/${ad}/${taraf}/${plakaAdi(f)}`);
  return <GlGecis ad={K.gl} from={yol('a')} to={yol('b')} ilerleme={p} param={K.param} onYok={cizim ? undefined : () => setYok(true)} />;
};
