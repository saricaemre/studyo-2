// Kamera takibi (FOOH): gerçek çekim + Blender'ın gölge, yansıma ve nesne katmanları (zanaat §10, blender/CLAUDE.md → Kamera takibi).
// Kamera ./st takip ile çözülür ve dondurulur; plakaları stüdyo çizer (pipeline/blender.py). Bir plaka kümesinde (Blender kare numarasıyla, f + 1):
//   gNNNNN.png gölge çarpanı (≤ 1, çarpılır) · yNNNNN.png yansıma ve sekme ışığı (çekim × gölge çarpanının 1'i aşan kısmı, toplanır) ·
//   nNNNNN.png nesne (RGBA). pNNNNN.png Blender'ın kendi birleştirmesidir (önizleme, deterministiklik); burada kullanılmaz.
// Sıra: çekim → gölge → yansıma → (children: nesnenin ARKASINDA kalacak yazı ya da görsel) → nesne.
import React, {useState} from 'react';
import {AbsoluteFill, Img, getRemotionEnvironment, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useFormat} from '../format';
import {plakaKumesi, type PlakaKumeleri} from '../BlenderPlaka';
import {Goruntu, type RenkAyari} from '../goruntu/Goruntu';

/** videos/<id>/takip/takip.json (./st takip yazar): seçili çözüm, çekimin adı ve başlangıç karesi. */
export type TakipKaydi = {secili?: string | null; cozumler: Record<string, {goruntu: string; bas: number; n: number}>};

const katman = (id: string, kume: string, harf: 'n' | 'g' | 'y', f: number) =>
  staticFile(`${id}/plaka/${kume}/${harf}${String(f + 1).padStart(5, '0')}.png`);

export const TakipBirlesim: React.FC<{
  id: string;
  takip: TakipKaydi;
  varsayilan?: PlakaKumeleri;
  /** çekimin renk düzeltmesi (CSS süzgeci; nesne katmanına uygulanmaz: nesnenin ışığı Blender'da çekimin ortalama renginden) */
  renk?: RenkAyari;
  children?: React.ReactNode;
}> = ({id, takip, varsayilan, renk, children}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const {key} = useFormat();
  const [yok, setYok] = useState(false);
  const x = takip.cozumler[takip.secili ?? ''];
  if (!x) throw new Error(`${id}: kamera takibi yok (videos/${id}/takip/takip.json): ./st takip ${id} <görüntü>`);
  const kume = plakaKumesi(varsayilan, key);
  const cizim = getRemotionEnvironment().isRendering;
  const f = Math.max(0, Math.min(durationInFrames - 1, Math.round(frame)));
  const tam: React.CSSProperties = {position: 'absolute', left: 0, top: 0, width: '100%', height: '100%'};
  const hata = cizim ? undefined : () => setYok(true);
  return (
    <AbsoluteFill>
      <Goruntu film={id} ad={x.goruntu} baslangic={x.bas / fps} renk={renk} />
      {kume && !yok ? (
        <>
          <Img src={katman(id, kume, 'g', f)} style={{...tam, mixBlendMode: 'multiply'}} onError={hata} />
          <Img src={katman(id, kume, 'y', f)} style={{...tam, mixBlendMode: 'plus-lighter'}} onError={hata} />
          {children}
          <Img src={katman(id, kume, 'n', f)} style={tam} onError={hata} />
        </>
      ) : cizim ? (
        (() => {
          throw new Error(`${id}: ${key} plakası yok. Plakaları stüdyo çizer: ./st kare / temsili / render (pipeline/blender.py).`);
        })()
      ) : (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 34, fontFamily: 'sans-serif'}}>
          {`Plaka yok (${key} · f${f}) — ./st blender ${id} plaka`}
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
