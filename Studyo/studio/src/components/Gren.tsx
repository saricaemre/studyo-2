import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {rand} from '../lib/anim';

const TILE = 512;

/**
 * Gren dokusu, kare başına tohumlu kayma ile. CSS background yerine <Img> döşemeleri kullanır: Remotion <Img>'in
 * yüklenmesini bekler, CSS arka plan görselini beklemez. Eski hâlinde doku bazı karelerde yüklenmeden yakalanıyordu
 * (./st deterministik ara sıra farklı kare buldu; kanal/ogrenimler.md #15).
 * Döşeme konumları CSS `background-position: ox oy` + tekrarın birebir karşılığıdır.
 */
export const Gren: React.FC<{frame: number; blend: React.CSSProperties['mixBlendMode']; opacity: number}> = ({frame, blend, opacity}) => {
  const {width, height} = useVideoConfig();
  const ox = Math.floor(rand(frame) * TILE);
  const oy = Math.floor(rand(frame + 3) * TILE);
  const tiles: [number, number][] = [];
  for (let y = oy - TILE; y < height; y += TILE) for (let x = ox - TILE; x < width; x += TILE) tiles.push([x, y]);
  return (
    <AbsoluteFill style={{mixBlendMode: blend, opacity, overflow: 'hidden'}}>
      {tiles.map(([x, y]) => (
        <Img key={`${x},${y}`} src={staticFile('textures/grain.png')} style={{position: 'absolute', left: x, top: y, width: TILE, height: TILE}} />
      ))}
    </AbsoluteFill>
  );
};
