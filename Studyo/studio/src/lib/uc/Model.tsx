// Remotion: GLB modeli <Sahne3B> içinde. Yüklenene kadar kare bekletilir (delayRender); yüklendiği karede tuval yeniden çizilir
// (çizim yalnız kare değişince olur: frameloop "never"). Dosya: ./st 3b kullan <id> <slug> → staticFile('<id>/varliklar/3b/<slug>.glb').
import {useThree} from '@react-three/fiber';
import React, {useEffect, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {staticFile, useCurrentFrame, useDelayRender, useVideoConfig} from 'remotion';
import type * as THREE from 'three';
import {type GLTF, type HazirlaAyar, animasyonKur, animasyonSur, glbHazir, glbYukle, modelHazirla} from './glb';

/** Çözücüler public/uc/ altında (./st 3b kullan koyar; three'nin kendi kopyası, CDN yok). */
export const COZUCU = {draco: staticFile('uc/draco') + '/', basis: staticFile('uc/basis') + '/'};

/** GLB'yi yükler; yüklenene kadar Remotion kareyi bekletir, yüklenince tuvali bir kez yeniden çizer. <Sahne3B> içinde kullan. */
export const useModel = (src: string): GLTF | null => {
  const {gl, advance} = useThree();
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  const kare = useCurrentFrame();
  const {fps} = useVideoConfig();
  const [, yenile] = useState(0);
  const g = glbHazir(src);
  const tutamac = useRef<number | null>(null);
  // Bekletme yerleşimde alınır (atılan bir çizim tutamak bırakmaz); <ThreeCanvas>'ın kendi bekletmesi bırakılmadan önce.
  useLayoutEffect(() => {
    if (glbHazir(src)) return;
    tutamac.current = delayRender(`3B model: ${src}`, {timeoutInMilliseconds: 120000});
    let iptal = false;
    glbYukle(src, {cozucu: COZUCU, renderer: gl}).then(() => !iptal && yenile((n) => n + 1), (e) => cancelRender(e));
    return () => {
      iptal = true;
      if (tutamac.current !== null) continueRender(tutamac.current);
      tutamac.current = null;
    };
  }, [src, gl, delayRender, continueRender, cancelRender]);
  // Yüklendiği karede çiz, sonra bekletmeyi bırak. Pasif etki: bileşenlerin poz/konum yazan useLayoutEffect'lerinden sonra çalışır.
  useEffect(() => {
    if (g && tutamac.current !== null) {
      advance((kare / fps) * 1000);  // R3F saatinin damgası; kit bu saati kullanmaz (zaman useZaman'dan)
      continueRender(tutamac.current);
      tutamac.current = null;
    }
  }, [g, advance, continueRender, kare, fps]);
  return g;
};

/** yukseklik, boyut, yerlesim, golge, malzeme ve renkler kurulumdur (değişince model yeniden kopyalanır): sabit tut; canlandırmak için position,
 *  rotation, scale (her karede serbest). */
export type ModelProps = HazirlaAyar & {
  /** staticFile('<id>/varliklar/3b/<slug>.glb') */
  src: string;
  /** GLB'deki animasyonun adı ya da sırası (./st 3b incele <slug> listeler). */
  animasyon?: string | number;
  /** Animasyon zamanı (sn): useZaman().t ya da ondan türetilmiş (geciktirilmiş, yavaşlatılmış) bir değer. */
  t?: number;
  hiz?: number;
  dongu?: boolean;
  position?: THREE.Vector3Tuple;
  rotation?: THREE.Vector3Tuple;
  scale?: number | THREE.Vector3Tuple;
  visible?: boolean;
};

/** GLB modeli: bir kez yüklenir, ölçülür, yerleştirilir (varsayılan: tabanın ortası orijinde). Konum/dönüş/ölçek t'den hesaplanır. */
export const Model = ({src, animasyon, t = 0, hiz = 1, dongu = true, yukseklik, boyut, yerlesim, golge, malzeme, renkler, ...grup}: ModelProps) => {
  const g = useModel(src);
  const kok = useMemo(() => (g ? modelHazirla(g, {yukseklik, boyut, yerlesim, golge, malzeme, renkler}) : null),
    // malzeme ve renkler her çizimde yeni bir işlev/dizi olabilir: kopya yalnız model ve ölçü değişince yeniden kurulur
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [g, yukseklik, boyut, yerlesim, golge]);
  const an = useMemo(() => (kok && g && animasyon !== undefined ? animasyonKur(kok, g.animations) : null), [kok, g, animasyon !== undefined]);
  useLayoutEffect(() => {
    if (an && animasyon !== undefined) animasyonSur(an, {klip: animasyon, t, hiz, dongu});
  });
  useLayoutEffect(() => () => {
    an?.mixer.stopAllAction();
  }, [an]);
  return kok ? <primitive object={kok} {...grup} /> : null;
};
