import React, {useMemo} from 'react';
import {AbsoluteFill} from 'remotion';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {clamp01, easeInOutCubic, easeOutCubic, lerp} from '../../lib/anim';
import {baslikMetni, yaziStili} from '../../lib/gorunus';
import {DunyaKuresi, Isik, Kamera, KureIsareti, Parcaciklar, Sahne3B, ShaderAlani, malzeme, useNesne, useSigdir, yuzunuDondur} from '../../lib/uc';
import type {Ornek} from './ornekler';

/**
 * 3B katman örnekleri (katalog/animasyon/*.json → "uc": true). Three.js, @remotion/three ile; yazı Remotion'da, 3B'nin üstünde.
 * Teknik örnektir: telefon, cam ve kil küre, İstanbul ve renkler yalnız örneğin seçimidir; film kendi nesnesini, malzemesini ve rengini brief'ten ve görünüşten alır.
 * Zaman t'den (useCurrentFrame); hareket bulanıklığı yok (Bitis'in ara kareleri her biri ayrı bir WebGL tuvali açardı).
 */
const p = (t: number, a: number, d: number, e: (x: number) => number = easeInOutCubic) => e(clamp01((t - a) / d));

const karistir = (a: string, b: string, k: number) => '#' + new THREE.Color(a).lerp(new THREE.Color(b), k).getHexString();

// 1 · Dünya küresi: küre Atlantik'ten İstanbul'a döner, kamera yaklaşır, konum işareti nabız atar, ad yazısı gelir
export const DunyaKuresiOrnek: Ornek = ({t, S}) => {
  const doku = useMemo(() => ({deniz: karistir(S.murekkep, '#1d3d6b', 0.55), kara: karistir(S.kagit, '#e9dcc3', 0.4)}), [S.murekkep, S.kagit]);
  const k = p(t, 0.2, 2.1);
  const [x0, y0] = yuzunuDondur(18, -40);
  const [x1, y1] = yuzunuDondur(41.0, 28.98);
  const uzak = useSigdir(1, 30, 1.25);
  const yazi = p(t, 2.0, 0.5, easeOutCubic);
  return (
    <AbsoluteFill style={{background: '#06080d'}}>
      <Sahne3B arka="#06080d">
        <Kamera konum={[0, 0, lerp(uzak, uzak * 0.7, k)]} fov={30} />
        <Isik on="gun" aci={-0.6} />
        <Parcaciklar n={1500} tohum={3} kabuk={[18, 30]} boyut={3} renk="#cfdcff" saydamlik={0.7} suruklenme={0.05} />
        <DunyaKuresi donus={[lerp(x0, x1, k), lerp(y0, y1, k), 0]} doku={doku} atmosfer="#8cc8ff">
          <KureIsareti enlem={41.0} boylam={28.98} renk={S.vurgu} boyut={0.022} nabiz={(Math.max(0, t - 1.6) * 0.9) % 1} />
        </DunyaKuresi>
      </Sahne3B>
      <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 120,
        background: `linear-gradient(to top, rgba(6,8,13,${0.88 * yazi}) 0%, rgba(6,8,13,0) 45%)`}}>
        <div style={{...yaziStili(S, 'baslik'), color: '#ffffff', fontSize: 92, opacity: yazi, transform: `translateY(${(1 - yazi) * 30}px)`}}>
          {baslikMetni(S, 'İstanbul')}
        </div>
        <div style={{...yaziStili(S, 'govde'), color: '#ffffff', opacity: 0.7 * yazi, fontSize: 34, marginTop: 8}}>41,0° K · 28,9° D</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Telefon ekranı: tuvalde çizilmiş basit arayüz (yazısız bloklar, vurgu renginde). */
const ekranDokusu = (vurgu: string, murekkep: string) => {
  const c = document.createElement('canvas');
  c.width = 540;
  c.height = 1080;
  const x = c.getContext('2d', {willReadFrequently: true})!;
  x.fillStyle = '#f6f4f0';
  x.fillRect(0, 0, 540, 1080);
  x.fillStyle = vurgu;
  x.beginPath();
  x.roundRect(36, 120, 468, 300, 28);
  x.fill();
  x.fillStyle = '#ffffff';
  x.globalAlpha = 0.85;
  x.fillRect(72, 330, 220, 26);
  x.globalAlpha = 1;
  x.fillStyle = murekkep;
  for (let i = 0; i < 4; i++) {
    x.globalAlpha = 0.9 - i * 0.18;
    x.beginPath();
    x.roundRect(36, 460 + i * 140, 468, 112, 22);
    x.fill();
  }
  x.globalAlpha = 1;
  const d = new THREE.CanvasTexture(c);
  d.colorSpace = THREE.SRGBColorSpace;
  d.anisotropy = 4;
  return d;
};

// 2 · 3B ürün / nesne: telefon döner tablada yükselir, anahtar ışık üstünden geçer, cam ve kil eşlikçiler; adı altta
export const Urun3BOrnek: Ornek = ({t, S}) => {
  const govdeGeo = useNesne(() => new RoundedBoxGeometry(1.0, 2.04, 0.11, 8, 0.12), []);
  const govde = useNesne(() => malzeme.plastik(S.murekkep, {puruz: 0.28}), [S.murekkep]);
  const ekranDoku = useNesne(() => ekranDokusu(S.vurgu, S.murekkep), [S.vurgu, S.murekkep]);
  const ekran = useNesne(() => new THREE.MeshStandardMaterial({map: ekranDoku, emissive: '#ffffff', emissiveMap: ekranDoku, emissiveIntensity: 0.9,
    roughness: 0.2}), [ekranDoku]);
  const cam = useNesne(() => malzeme.cam('#ffffff', {kalinlik: 0.5}), []);
  const kil = useNesne(() => malzeme.kil(S.vurgu), [S.vurgu]);
  const zemin = useNesne(() => malzeme.kil(karistir(S.arka, '#d9d4cc', 0.35), {puruz: 0.95}), [S.arka]);
  const yuksel = p(t, 0, 1.1, easeOutCubic);
  const don = lerp(-1.25, 0.55, p(t, 0, 3.0));
  const yazi = p(t, 1.6, 0.6, easeOutCubic);
  return (
    <AbsoluteFill style={{background: S.arka}}>
      <Sahne3B arka={karistir(S.arka, '#ece8e2', 0.3)} golge ortamGucu={0.6}>
        <Kamera konum={[0, lerp(1.1, 0.7, p(t, 0, 3)), lerp(6.4, 5.9, p(t, 0, 3))]} hedef={[0, 0.25, 0]} fov={28} />
        <Isik on="studyo" golge golgeAlani={4} aci={lerp(-0.7, 0.5, p(t, 0, 3))} />
        <group position={[0, lerp(-0.6, 0.35, yuksel), 0]} rotation={[lerp(0.5, 0.06, yuksel), don, lerp(-0.2, 0.05, yuksel)]}>
          <mesh geometry={govdeGeo} material={govde} castShadow />
          <mesh material={ekran} position={[0, 0, 0.0565]}>
            <planeGeometry args={[0.9, 1.9]} />
          </mesh>
        </group>
        <mesh material={cam} position={[-0.95, lerp(-0.35, -0.2, Math.sin(t * 2.1) * 0.5 + 0.5), 0.6]} castShadow>
          <sphereGeometry args={[0.38, 64, 48]} />
        </mesh>
        <mesh material={kil} position={[0.95, -0.62 + 0.04 * Math.sin(t * 2.6), 0.3]} castShadow>
          <sphereGeometry args={[0.24, 48, 32]} />
        </mesh>
        <mesh material={zemin} position={[0, -0.88, 0]} receiveShadow>
          <cylinderGeometry args={[2.6, 2.6, 0.12, 96]} />
        </mesh>
      </Sahne3B>
      <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 70}}>
        <div style={{...yaziStili(S, 'baslik'), color: S.murekkep, fontSize: 64, opacity: yazi, transform: `translateY(${(1 - yazi) * 24}px)`}}>
          {baslikMetni(S, 'Cebinizde.')}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// 3 · Parçacık / shader alanı: akan mürekkep alanı + süzülen toz; büyük kelime alanın içinden belirir
export const ParcacikAlaniOrnek: Ornek = ({t, S}) => {
  const renkler = useMemo(() => [S.arka, karistir(S.arka, S.murekkep, 0.3), S.vurgu] as [string, string, string], [S.arka, S.murekkep, S.vurgu]);
  const yazi = p(t, 0.8, 0.9, easeOutCubic);
  return (
    <AbsoluteFill style={{background: S.arka}}>
      <Sahne3B arka={S.arka} ortam={null} tonlama="yok">
        <Kamera konum={[0, 0, lerp(10, 8.5, p(t, 0, 3))]} fov={40} />
        <ShaderAlani frag="akis" renkler={renkler} tohum={4} hiz={2.2} />
        <Parcaciklar n={900} tohum={7} kutu={[12, 12, 6]} boyut={7} renk={S.murekkep} saydamlik={0.55} suruklenme={0.6} parlak={false} />
      </Sahne3B>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{...yaziStili(S, 'baslik'), color: S.murekkep, fontSize: 180, opacity: yazi, letterSpacing: `${lerp(0.25, -0.02, yazi)}em`}}>
          {baslikMetni(S, 'Akış')}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const UC_ORNEKLER: Record<string, Ornek> = {
  'dunya-kuresi': DunyaKuresiOrnek,
  'urun-3b': Urun3BOrnek,
  'parcacik-alani': ParcacikAlaniOrnek,
};
