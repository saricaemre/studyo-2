// Anahtar kare sandviçi (3b, zanaat §9): motor bir kareyi çizer, Magnific o kareden motorun sonraki karesine giden hareketi üretir
// (video_generate, ilk ve son kare), motor devralır. ./st sandvic <film> <ad> --bas SN kareleri çizer ve adımları yazar; klip
// ./st uret al … --uyum ile filmin kare hızında dondurulur. bas: klibin ilk karesine denk gelen film karesi, kare: gösterilen kare sayısı
// (klibin son karesi motorun devraldığı kareyle aynı olduğundan gösterilmez).
import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, staticFile} from 'remotion';

export const Sandvic: React.FC<{film: string; ad: string; bas: number; kare: number; uzanti?: string; dosya?: string; style?: React.CSSProperties}> = ({film,
  ad, bas, kare, uzanti = 'mp4', dosya, style}) => (
  <Sequence from={bas} durationInFrames={kare} layout="none">
    <AbsoluteFill>
      {/* dosya: üretim deposu dışından bir klip (public/<film>/'e göre; ör. yerel sınama klibi) */}
      <OffthreadVideo src={staticFile(`${film}/${dosya ?? `varliklar/uretim/${ad}.${uzanti}`}`)} muted style={{width: '100%', height: '100%', objectFit: 'cover', ...style}} />
    </AbsoluteFill>
  </Sequence>
);
