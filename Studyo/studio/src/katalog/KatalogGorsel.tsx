import React from 'react';
import {AbsoluteFill, getInputProps} from 'remotion';
import {Bitis} from '../components/Bitis';
import {NOTR, Secenek, Stil, StilSaglayici, baslikMetni, stilOlustur, yaziStili} from '../lib/gorunus';
import {GORSELLER} from './gorseller.gen';

/**
 * Katalog önizlemesi: bir görüntü stilinin bir varyasyonu, herkes için aynı örnek karede.
 * ./st katalog --props '{"stil": "<ad>", "varyasyon": "a"}' ile çizer. Yazı tipleri yalnız istenen stil çizilirken yüklenir
 * (modül düzeyinde yüklenseydi her videonun render'ı bütün katalog yazı tiplerini beklerdi).
 */
const onbellek: Record<string, Stil> = {};
const stilAl = (ad?: string, v?: string): Stil => {
  const k = `${ad}/${v}`;
  if (!onbellek[k]) {
    const s = ad ? (GORSELLER[ad]?.varyasyonlar[v ?? 'a'] as Secenek | undefined) : undefined;
    onbellek[k] = stilOlustur(s ?? NOTR);
  }
  return onbellek[k];
};

export const KatalogGorselKare: React.FC<{STIL: Stil}> = ({STIL}) => {
  const zemin = STIL.kagit;
  const kartli = zemin.toLowerCase() !== STIL.arka.toLowerCase();
  const B = [0.42, 0.68, 0.55, 0.9];
  return (
    <AbsoluteFill style={{background: STIL.arka}}>
      <div style={{position: 'absolute', inset: kartli ? 70 : 0, background: zemin, boxShadow: kartli ? '0 30px 80px rgba(0,0,0,0.45)' : undefined}}>
        <div style={{position: 'absolute', left: 90, top: 90, right: 90}}>
          <div style={{...yaziStili(STIL, 'aksan'), color: STIL.soluk, fontSize: 34}}>01 · örnek kare</div>
          <div style={{...yaziStili(STIL, 'baslik'), color: STIL.murekkep, fontSize: 112, lineHeight: 0.98, marginTop: 34}}>
            {baslikMetni(STIL, 'Her şey bir ')}<span style={{color: STIL.vurgu}}>{baslikMetni(STIL, 'fikirle')}</span>{baslikMetni(STIL, ' başlar')}
          </div>
          <div style={{width: 170, height: 12, background: STIL.vurgu, marginTop: 40}} />
          <div style={{...yaziStili(STIL, 'govde'), color: STIL.murekkep, fontSize: 40, marginTop: 40, maxWidth: 760, lineHeight: 1.25}}>
            Aynı kare, başka bir görünüş: renk, yazı, doku ve ışık.
          </div>
        </div>
        <div style={{position: 'absolute', left: 90, bottom: 90, display: 'flex', alignItems: 'flex-end', gap: 26}}>
          {B.map((h, i) => (
            <div key={i} style={{width: 64, height: 220 * h, background: i === B.length - 1 ? STIL.vurgu : STIL.soluk, opacity: i === B.length - 1 ? 1 : 0.55}} />
          ))}
          <div style={{marginLeft: 30}}>
            <div style={{...yaziStili(STIL, 'baslik'), color: STIL.murekkep, fontSize: 72, lineHeight: 1, whiteSpace: 'nowrap'}}>2.600.000</div>
            <div style={{...yaziStili(STIL, 'govde'), color: STIL.soluk, fontSize: 28, marginTop: 10}}>kişi · yıllık · örnek veri</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const KatalogGorsel: React.FC = () => {
  const P = getInputProps() as {stil?: string; varyasyon?: string};
  const STIL = stilAl(P.stil, P.varyasyon);
  return (
    <StilSaglayici value={STIL}>
      <AbsoluteFill lang="tr">
        <Bitis ayar={{...STIL.bitis, bulaniklik: 0}}>
          <KatalogGorselKare STIL={STIL} />
        </Bitis>
      </AbsoluteFill>
    </StilSaglayici>
  );
};
