import React, {useState} from 'react';
import {AbsoluteFill, Img, getInputProps, getRemotionEnvironment, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useFormat} from './format';

/**
 * Blender motoru (script.json → motor: "blender"): Blender'ın çizdiği plaka, yani o karenin PNG'si.
 * Plakaları stüdyo çizer ve önbellekte tutar (pipeline/blender.py): out/_plaka/<id>/<küme>/pNNNNN.png, Remotion'a
 * public/<id>/plaka bağlantısıyla gelir (public/ her paketlemede kopyalanır, bağlantı kopyalanmaz).
 * Küme (format + kalite + parmak izi) çizimde --props {plaka} ile verilir; yoksa public/<id>/plaka.json'daki varsayılan
 * (önce "tam", sonra "taslak"): Remotion Studio önizlemesi için.
 * Plaka hareket bulanıklığını Blender'da taşır: Bitis'in bulanıklığını kapat (bulaniklik: 0), yoksa aynı plaka üst üste örneklenir.
 */
export type PlakaKumeleri = Partial<Record<string, {taslak?: string; tam?: string}>>;

export const plakaKumesi = (varsayilan: PlakaKumeleri | undefined, format: string): string | undefined => {
  const p = getInputProps() as {plaka?: string};
  return p.plaka ?? varsayilan?.[format]?.tam ?? varsayilan?.[format]?.taslak;
};

export const BlenderPlaka: React.FC<{id: string; varsayilan?: PlakaKumeleri; style?: React.CSSProperties}> = ({id, varsayilan, style}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const {key} = useFormat();
  const [yok, setYok] = useState(false);
  const kume = plakaKumesi(varsayilan, key);
  const cizim = getRemotionEnvironment().isRendering;
  // Kare numarası Remotion'unkidir (0 tabanlı): plaka pNNNNN, Blender'da NNNNN + 1. karedir.
  const f = Math.max(0, Math.min(durationInFrames - 1, Math.round(frame)));
  if (!kume || yok) {
    if (cizim) {
      throw new Error(`${id}: ${key} plakası yok. Plakaları stüdyo çizer: ./st kare / temsili / render (pipeline/blender.py).`);
    }
    return (
      <AbsoluteFill style={{background: '#14161c', color: '#9aa0ad', alignItems: 'center', justifyContent: 'center', fontSize: 34, fontFamily: 'sans-serif'}}>
        {`Plaka yok (${key} · f${f}) — ./st blender ${id} plaka`}
      </AbsoluteFill>
    );
  }
  return (
    <Img
      src={staticFile(`${id}/plaka/${kume}/p${String(f).padStart(5, '0')}.png`)}
      style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', ...style}}
      onError={cizim ? undefined : () => setYok(true)}
    />
  );
};
