// Gerçek görüntü (zanaat §2 yol B): kendi çekim, kurum arşivi, stok ya da plaka; formatın kadraj yoluyla kırpılır (özne güvenli alanda,
// merkezden kırpma yok). Video Remotion'un OffthreadVideo'suyla (kare kare, deterministik), sessiz: ses işaret listesinden (kural 9).
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useFormat} from '../format';
import {kaynakKaresi, pencereAl, useGoruntuKaydi} from './bilgi';

/** Renk düzeltmesi (CSS süzgeci): 1 = değişmez. sicaklik −1 (soğuk) … 1 (sıcak). */
export type RenkAyari = {parlaklik?: number; kontrast?: number; doygunluk?: number; sicaklik?: number};

export const renkSuzgeci = (r?: RenkAyari) => {
  if (!r) return undefined;
  const s = r.sicaklik ?? 0;
  return [`brightness(${r.parlaklik ?? 1})`, `contrast(${r.kontrast ?? 1})`, `saturate(${r.doygunluk ?? 1})`,
    s > 0 ? `sepia(${(0.35 * s).toFixed(3)}) hue-rotate(${(-8 * s).toFixed(2)}deg)` : s < 0 ? `hue-rotate(${(-12 * s).toFixed(2)}deg) saturate(${(1 + 0.15 * s).toFixed(3)})` : '']
    .filter(Boolean).join(' ');
};

export type GoruntuProps = {
  /** Filmin kimliği (public/<film>/). */
  film: string;
  /** ./st goruntu ekle'nin verdiği ad. */
  ad: string;
  /** Klipte başlangıç (sn) ve hız (0,5 = yarı hız; kare çoğaltılır, ara kare uydurulmaz). */
  baslangic?: number;
  hiz?: number;
  renk?: RenkAyari;
  /** Kadraj penceresinin içinde ek yakınlaşma (1 = yok); pencere merkezinde. Hareket için karede değiştir. */
  olcek?: number;
  style?: React.CSSProperties;
};

export const Goruntu: React.FC<GoruntuProps> = ({film, ad, baslangic = 0, hiz = 1, renk, olcek = 1, style}) => {
  const k = useGoruntuKaydi(film, ad);
  const kare = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const {key} = useFormat();
  if (!k) return null;
  const [x, y, w, h] = pencereAl(k, key, kaynakKaresi(k, kare, fps, baslangic, hiz), width, height, film, ad);
  const s = (width / (w * k.en)) * olcek;
  const cx = (x + w / 2) * k.en * s, cy = (y + h / 2) * k.boy * s;          // pencerenin merkezi karenin merkezine
  const src = staticFile(`${film}/${k.dosya}`);
  const kutu: React.CSSProperties = {position: 'absolute', left: width / 2 - cx, top: height / 2 - cy, width: k.en * s, height: k.boy * s,
    filter: renkSuzgeci(renk)};
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...style}}>
      <div style={kutu}>
        {k.tur === 'video'
          ? <OffthreadVideo src={src} muted trimBefore={Math.round(baslangic * fps) || undefined} playbackRate={hiz} style={{width: '100%', height: '100%'}} />
          : <Img src={src} style={{width: '100%', height: '100%'}} />}
      </div>
    </AbsoluteFill>
  );
};
