import React, {useLayoutEffect, useMemo, useRef, useState} from 'react';
import {AbsoluteFill, staticFile, useDelayRender} from 'remotion';
import * as THREE from 'three';
import {Isik, Kamera, Sahne3B, modelHazirla, renkPaleti, sigdirUzaklik, useModel, useNesne} from '../lib/uc';

/**
 * Kütüphanedeki bir GLB modelin stüdyonun kendi 3B katmanında görünüşü (./st 3b onizle <slug> → kutuphane/3b/threejsassets/<slug>.png).
 * Nötr stüdyo ışığı, yere düşen gölge, dörtte üç açı; model en büyük boyutu 2 birim olacak biçimde ölçeklenir. Film değil, kontrol karesi.
 * Altta köşe rengi paleti (sRGB hex, üçgen payı): parça seçimi renkle yapılır (renkleAyir; modelde parça adı yok).
 */
type Props = {src: string; arka?: string};
type Palet = {renk: string; ucgen: number}[];

const Model = ({src, paletVer}: {src: string; paletVer: (p: Palet) => void}) => {
  const g = useModel(staticFile(src));
  const kok = useMemo(() => (g ? modelHazirla(g, {boyut: 2, golge: true}) : null), [g]);
  useLayoutEffect(() => {
    if (g) paletVer(renkPaleti(g.scene));
  }, [g, paletVer]);
  const zemin = useNesne(() => new THREE.ShadowMaterial({opacity: 0.22}), []);
  const b: THREE.Vector3 = kok?.userData.boyut ?? new THREE.Vector3(2, 2, 2);
  const uzak = sigdirUzaklik(b.length() / 2, 30, 1, 1.12);
  const yon = new THREE.Vector3(0.62, 0.42, 1).normalize().multiplyScalar(uzak);
  return (
    <>
      <Kamera konum={[yon.x, b.y / 2 + yon.y, yon.z]} hedef={[0, b.y / 2, 0]} fov={30} />
      <Isik on="studyo" golge golgeAlani={6} />
      {kok ? <primitive object={kok} /> : null}
      <mesh material={zemin} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[30, 30]} />
      </mesh>
    </>
  );
};

const PaletSeridi = ({palet}: {palet: Palet}) => {
  const top = palet.reduce((s, p) => s + p.ucgen, 0) || 1;
  return (
    <div style={{position: 'absolute', left: 24, right: 24, bottom: 20, display: 'flex', flexWrap: 'wrap', gap: '8px 18px',
      fontFamily: 'Helvetica, Arial, sans-serif', fontSize: 19, color: '#4a4540'}}>
      {palet.slice(0, 12).map((p) => (
        <div key={p.renk} style={{display: 'flex', alignItems: 'center', gap: 7}}>
          <div style={{width: 26, height: 26, borderRadius: 5, background: p.renk, boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.18)'}} />
          {p.renk} · %{Math.round((100 * p.ucgen) / top)}
        </div>
      ))}
    </div>
  );
};

export const ModelOnizleme: React.FC<Props> = ({src, arka = '#e9e5df'}) => {
  const [palet, setPalet] = useState<Palet | null>(null);
  const {delayRender, continueRender} = useDelayRender();
  const bekle = useRef<number | null>(null);
  // Palet tuvalin içinde (model yüklenince) hesaplanır; kare palet şeridi yazılana kadar bekler.
  useLayoutEffect(() => {
    bekle.current = delayRender('model paleti', {timeoutInMilliseconds: 120000});
    return () => {
      if (bekle.current !== null) continueRender(bekle.current);
    };
  }, [delayRender, continueRender]);
  useLayoutEffect(() => {
    if (palet && bekle.current !== null) {
      continueRender(bekle.current);
      bekle.current = null;
    }
  }, [palet, continueRender]);
  return (
    <AbsoluteFill style={{background: arka}}>
      <Sahne3B golge arka={arka}>
        <Model src={src} paletVer={setPalet} />
      </Sahne3B>
      {palet?.length ? <PaletSeridi palet={palet} /> : null}
    </AbsoluteFill>
  );
};
