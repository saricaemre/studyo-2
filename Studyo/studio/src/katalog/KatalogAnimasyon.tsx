import React from 'react';
import {AbsoluteFill, getInputProps, useCurrentFrame, useVideoConfig} from 'remotion';
import {Bitis} from '../components/Bitis';
import {Secenek, Stil, StilSaglayici, stilOlustur} from '../lib/gorunus';
import {ORNEKLER} from './animasyon/ornekler';
import {UC_ORNEKLER} from './animasyon/uc';
import {GORSELLER} from './gorseller.gen';

/**
 * Katalog önizlemesi: bir animasyon tipinin 3 sn'lik döngüsü (--props '{"tip": "<ad>"}').
 * Hareketi görünüşten ayırmak için hepsi aynı nötr görünüşle çizilir (isviçre ızgarası A); hareket bulanıklığı açık.
 */
let NOTR_STIL: Stil | null = null;
const notr = () => (NOTR_STIL ??= stilOlustur(GORSELLER['isvicre-izgara'].varyasyonlar.a as Secenek));

export const KatalogAnimasyon: React.FC = () => {
  const tip = (getInputProps() as {tip?: string}).tip ?? 'kinetik-tipografi';
  const Ornek = ORNEKLER[tip] ?? UC_ORNEKLER[tip];
  if (!Ornek) throw new Error(`Animasyon tipi yok: ${tip} (var: ${[...Object.keys(ORNEKLER), ...Object.keys(UC_ORNEKLER)].join(', ')})`);
  const S = notr();
  if (UC_ORNEKLER[tip]) {  // 3B katman: hareket bulanıklığı yok (her ara kare ayrı bir WebGL tuvali açardı)
    return (
      <StilSaglayici value={S}>
        <AbsoluteFill lang="tr">
          <OrnekSahne tip={tip} />
        </AbsoluteFill>
      </StilSaglayici>
    );
  }
  return (
    <StilSaglayici value={S}>
      <AbsoluteFill lang="tr">
        <Bitis ayar={{bulaniklik: 8, aci: 180}}>
          <OrnekSahne tip={tip} />
        </Bitis>
      </AbsoluteFill>
    </StilSaglayici>
  );
};

/** Hareket bulanıklığı ara zamanlarda çizebilsin diye t burada, kesirli kareden hesaplanır. */
const OrnekSahne: React.FC<{tip: string}> = ({tip}) => {
  const {fps} = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const Ornek = ORNEKLER[tip] ?? UC_ORNEKLER[tip];
  return <Ornek t={t} S={notr()} />;
};
