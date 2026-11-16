import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Captions} from '../components/Captions';
import {type NiyetVeri, NiyetliAltyazi} from '../lib/niyet';
import {Sentence} from '../lib/time';
import kaynak from '../../katalog/onizleme/altyazi/kaynak/timeline.json';

/**
 * Yeni film levhasındaki altyazı seçiminin önizlemesi (./st katalog altyazi → katalog/onizleme/altyazi/<tur>.mp4).
 * Aynı iki kişilik diyalog (kaynak: deneme_niyet'in Edge anlatımı, dondurulmuş) bir kez ortak altyazıyla, bir kez niyetli altyazıyla.
 * Ses sonradan eklenir (kaynak/ses.m4a); sahne bilerek boş: yalnız altyazı karşılaştırılır.
 */
const K = kaynak as unknown as {sentences: Sentence[]; niyet: NiyetVeri};

export const KatalogAltyazi: React.FC<{tur: 'klasik' | 'niyetli'}> = ({tur}) => {
  const {fps} = useVideoConfig();
  const t = useCurrentFrame() / fps;
  return (
    <AbsoluteFill style={{background: 'linear-gradient(180deg, #0B1324 0%, #16223D 100%)'}}>
      {tur === 'niyetli' ? <NiyetliAltyazi t={t} veri={K.niyet} /> : <Captions t={t} sentences={K.sentences} theme="dark" />}
    </AbsoluteFill>
  );
};
