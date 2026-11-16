import React from 'react';
import {AbsoluteFill, Freeze, useCurrentFrame, useVideoConfig} from 'remotion';
import {Gren} from './Gren';
import {gecisPlakasi} from '../lib/gecis/plaka';

/**
 * Son rötuş ayarı: görünüşün bitis alanı (gorunus.json) + videoya özel düzeltme (script.json → bitis).
 * Boş nesne = kapalı: eski videolar bu bileşeni kullanmaz, kareleri değişmez. Kurallar: zanaat.md §5.
 */
export type BitisAyar = {
  /** Hareket bulanıklığı örnek sayısı (0–1 kapalı; 6–8 önerilir, render süresi bu katsayıyla artar). */
  bulaniklik?: number;
  /** Obtüratör açısı (derece): 180 = kare süresinin yarısı boyunca bulanıklık. */
  aci?: number;
  /** Parlak kenarlarda yumuşak ışık taşması gücü (0 kapalı, 0,15–0,35). Açık zeminli stilde 0 kalır: zemin de parlar. */
  isik?: number;
  /** Işık taşmasının başladığı parlaklık (0–1). */
  isik_esik?: number;
  /** Işık taşmasının yarıçapı (px, 1080 kısa kenara göre). */
  isik_yaricap?: number;
  /** Köşe kararması (0 kapalı, 0,1–0,35). */
  vinyet?: number;
  /** Siyahların kaldırılacağı renk (ör. '#1A1714'): hiçbir piksel bundan koyu olmaz. Boşsa kapalı. */
  siyah?: string;
  /** Gren saydamlığı (0 kapalı) ve karışım kipi. */
  gren?: number;
  gren_karisim?: React.CSSProperties['mixBlendMode'];
};

/**
 * Hareket bulanıklığı: kare, kare süresinin `aci/360`'ına yayılmış `ornek` ara zamanın ortalamasıdır.
 * Ara zamanlar karenin ortasına göre simetriktir (ses senkronu kaymaz) ve [0, son kare] aralığına sıkıştırılır.
 * Duran öğeler bütün örneklerde aynı olduğu için keskin kalır. Sahne kodu t'yi useCurrentFrame()'den hesaplamalıdır
 * (ara zamanlarda kare numarası kesirlidir); gren ve altyazı bu bileşenin dışında çizilir.
 */
export const HareketBulanikligi: React.FC<{ornek: number; aci?: number; children: React.ReactNode}> = ({ornek, aci = 180, children}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  if (ornek <= 1) return <>{children}</>;
  const pay = aci / 360;
  return (
    <AbsoluteFill style={{isolation: 'isolate'}}>
      {Array.from({length: ornek}, (_, i) => {
        const f = Math.max(0, Math.min(durationInFrames - 1, frame + ((i + 0.5) / ornek - 0.5) * pay));
        return (
          <AbsoluteFill key={i} style={{opacity: 1 / (i + 1)}}>
            <Freeze frame={f}>{children}</Freeze>
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

/** Sahneyi son rötuştan geçirir: bulanıklık → ışık taşması → köşe kararması → siyah kaldırma → gren. */
export const Bitis: React.FC<{ayar?: BitisAyar; children: React.ReactNode}> = ({ayar = {}, children}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  // geçiş plakası (src/lib/gecis): rötuş plakada yok, asıl çizimde geçişin üstünde bir kez
  if (gecisPlakasi()) return <AbsoluteFill>{children}</AbsoluteFill>;
  const k = Math.min(width, height) / 1080;
  const isik = ayar.isik ?? 0;
  const esik = ayar.isik_esik ?? 0.72;
  const egim = 1 / Math.max(0.01, 1 - esik);
  const sahne = <HareketBulanikligi ornek={ayar.bulaniklik ?? 0} aci={ayar.aci}>{children}</HareketBulanikligi>;
  return (
    <AbsoluteFill>
      {isik > 0 && (
        <svg width={0} height={0} style={{position: 'absolute'}}>
          <filter id="bitis-isik" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
            {/* yalnız eşiğin üstündeki parlaklık kalır */}
            <feComponentTransfer in="SourceGraphic" result="parlak">
              <feFuncR type="linear" slope={egim} intercept={-egim * esik} />
              <feFuncG type="linear" slope={egim} intercept={-egim * esik} />
              <feFuncB type="linear" slope={egim} intercept={-egim * esik} />
            </feComponentTransfer>
            <feGaussianBlur in="parlak" stdDeviation={(ayar.isik_yaricap ?? 14) * k} result="hale" />
            {/* film ışık taşması sıcaktır: kırmızı korunur, mavi azalır */}
            <feColorMatrix in="hale" type="matrix" values="1 0 0 0 0  0 0.72 0 0 0  0 0 0.45 0 0  0 0 0 1 0" result="sicak" />
            <feComposite in="SourceGraphic" in2="sicak" operator="arithmetic" k1={0} k2={1} k3={isik} k4={0} />
          </filter>
        </svg>
      )}
      <AbsoluteFill style={isik > 0 ? {filter: 'url(#bitis-isik)'} : undefined}>{sahne}</AbsoluteFill>
      {(ayar.vinyet ?? 0) > 0 && (
        <AbsoluteFill style={{background: `radial-gradient(ellipse farthest-corner at 50% 50%, rgba(0,0,0,0) 45%, rgba(0,0,0,${ayar.vinyet}) 100%)`}} />
      )}
      {ayar.siyah && <AbsoluteFill style={{background: ayar.siyah, mixBlendMode: 'lighten'}} />}
      {(ayar.gren ?? 0) > 0 && <Gren frame={Math.round(frame)} blend={ayar.gren_karisim ?? 'multiply'} opacity={ayar.gren ?? 0} />}
    </AbsoluteFill>
  );
};
