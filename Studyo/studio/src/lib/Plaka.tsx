import React, {useState} from 'react';
import {AbsoluteFill, Img, getInputProps, getRemotionEnvironment, staticFile, useCurrentFrame} from 'remotion';
import {useFormat} from './format';

/**
 * Karma filmin plaka sahnesi (oturum 6b, pipeline/plaka.py): HyperFrames, Blender (ya da Manim) sahnesinin o karedeki PNG'si.
 * Plakaları stüdyo çizer ve önbellekte tutar: out/_plaka/<id>/<sahne>/<küme>/pNNNNN.png (NNNNN filmin genel kare numarası),
 * Remotion'a public/<id>/plaka bağlantısıyla gelir. Küme çizimde --props {plaka: {sahne: küme}} ile verilir; yoksa
 * public/<id>/plaka.json'daki varsayılan (önce "tam", sonra "taslak"): Remotion Studio önizlemesi için.
 *   import plakaJson from '../../public/<id>/plaka.json';  const PLAKA = plakaJson as PlakaVerisi;
 *   <Plaka veri={PLAKA} sahne="kahraman" />
 * Saydam sahnenin (Blender, "saydam": true) PNG'si alfa taşır: altındaki Remotion katmanı görünür. Plaka yalnız sahnenin çizim aralığında
 * vardır (plaka.json → sahneler.<ad>.r0–r1); film kodu sahneyi o aralıkta gösterir (<Kesim> ya da pencere karesiyle).
 * BlenderPlaka'nın (tek motorlu Blender filmi) eşi; ona dokunulmadı.
 */
export type PlakaVerisi = {
  id: string;
  kume: Partial<Record<string, Partial<Record<string, {taslak?: string; tam?: string}>>>>;
  sahneler: Record<string, {motor: string; bas: number; son: number; r0: number; r1: number; saydam: boolean}>;
};

export const plakaKumesiSahne = (veri: PlakaVerisi, sahne: string, format: string): string | undefined => {
  const p = getInputProps() as {plaka?: Record<string, string> | string};
  const girdi = p.plaka && typeof p.plaka === 'object' ? p.plaka[sahne] : undefined;
  return girdi ?? veri.kume?.[sahne]?.[format]?.tam ?? veri.kume?.[sahne]?.[format]?.taslak;
};

/** Sahnenin f karesindeki plakasının adresi (çizim aralığına sıkıştırılmış) ya da küme yoksa null. */
export const plakaYolu = (veri: PlakaVerisi, sahne: string, format: string, frame: number): string | null => {
  const S = veri.sahneler[sahne];
  const kume = plakaKumesiSahne(veri, sahne, format);
  if (!S || !kume) return null;
  const f = Math.max(S.r0, Math.min(S.r1 - 1, Math.round(frame)));
  return staticFile(`${veri.id}/plaka/${sahne}/${kume}/p${String(f).padStart(5, '0')}.png`);
};

export const Plaka: React.FC<{veri: PlakaVerisi; sahne: string; style?: React.CSSProperties}> = ({veri, sahne, style}) => {
  const frame = useCurrentFrame();
  const {key} = useFormat();
  const [yok, setYok] = useState(false);
  const S = veri.sahneler[sahne];
  if (!S) throw new Error(`Plaka sahnesi yok: ${sahne} (script.json → sahneler; ./st plaka ${veri.id} durum)`);
  const yol = plakaYolu(veri, sahne, key, frame);
  const cizim = getRemotionEnvironment().isRendering;
  if (!yol || yok) {
    if (cizim) throw new Error(`${veri.id}: sahne ${sahne} (${key}) plakası yok. Plakaları stüdyo çizer: ./st kare / temsili / render (pipeline/plaka.py).`);
    return (
      <AbsoluteFill style={{background: S.saydam ? 'transparent' : '#14161c', color: '#9aa0ad', alignItems: 'center', justifyContent: 'center',
        fontSize: 34, fontFamily: 'sans-serif'}}>
        {`Plaka yok (${sahne} · ${S.motor} · ${key} · f${Math.round(frame)}) — ./st plaka ${veri.id} ciz ${sahne}`}
      </AbsoluteFill>
    );
  }
  return <Img src={yol} style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', ...style}} onError={cizim ? undefined : () => setYok(true)} />;
};
