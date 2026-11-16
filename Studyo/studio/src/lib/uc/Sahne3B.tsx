// Remotion 3B katmanı: <Sahne3B> içinde R3F (three) nesneleri. Zaman yalnız useCurrentFrame'den (useZaman);
// R3F useFrame, Three.js saati ve tarayıcının çizim döngüsü (rAF, setAnimationLoop) yasak (./st tip yakalar).
// 3B kullanan kompozisyon yazılımla (SwiftShader, gl "swangle") çizilir: st.py bunu src/<kod>/ içinde lib/uc görünce kendisi seçer.
import {useThree} from '@react-three/fiber';
import {ThreeCanvas} from '@remotion/three';
import React, {useLayoutEffect, useMemo} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import * as THREE from 'three';
import {type FormatKey, useFormat} from '../format';
import {type AlanAdi, type IsikAdi, type ParcacikAyar, type V3, isikAyarla, isikKur, kameraKoy, noktaBulutu, ortamKur,
  parcacikMalzemesi, shaderAlani, sigdirUzaklik} from './cekirdek';

/** Sahnenin zamanı: t (sn) ve kare. Kitin bütün hareketi bundan türer. */
export const useZaman = () => {
  const kare = useCurrentFrame();
  const {fps} = useVideoConfig();
  return {t: kare / fps, kare, fps};
};

/** Bileşen ömrü boyunca tek nesne; söküldüğünde GPU belleği bırakılır. */
export const useNesne = <T extends {dispose?: () => void}>(yap: () => T, bag: React.DependencyList = []) => {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const n = useMemo(yap, bag);
  useLayoutEffect(() => () => n.dispose?.(), [n]);
  return n;
};

const Ortam = ({guc}: {guc: number}) => {
  const {gl, scene} = useThree();
  useLayoutEffect(() => {
    const d = ortamKur(gl, scene, guc);
    return () => {
      scene.environment = null;
      d.dispose();
    };
  }, [gl, scene, guc]);
  return null;
};

export type Sahne3BProps = {
  children: React.ReactNode;
  /** Yumuşak gölge haritası (ışıkta golge, nesnede castShadow / receiveShadow da gerekir). */
  golge?: boolean;
  /** "oda": stüdyo yansıma ortamı (cam ve metal için, varsayılan); null: yok. */
  ortam?: 'oda' | null;
  ortamGucu?: number;
  /** Arka renk; null: saydam (arkadaki Remotion katmanı görünür). */
  arka?: string | null;
  /** "aces" sinematik tonlama (varsayılan) ya da "yok" (renkler hex'e birebir; düz illüstrasyon için). */
  tonlama?: 'aces' | 'yok';
  style?: React.CSSProperties;
};

/** Kompozisyonun tamamını kaplayan 3B tuval. Piksel oranı 1, kenar yumuşatma açık. */
export const Sahne3B = ({children, golge = false, ortam = 'oda', ortamGucu = 1, arka = null, tonlama = 'aces', style}: Sahne3BProps) => {
  const {width, height} = useVideoConfig();
  return (
    <ThreeCanvas width={width} height={height} dpr={1} shadows={golge ? 'soft' : false} flat={tonlama === 'yok'} style={style}
      gl={{antialias: true, alpha: arka === null, preserveDrawingBuffer: true}} camera={{fov: 35, near: 0.1, far: 500}}>
      {arka ? <color attach="background" args={[arka]} /> : null}
      {ortam ? <Ortam guc={ortamGucu} /> : null}
      {children}
    </ThreeCanvas>
  );
};

/** Format başına değer: tek sayı ya da {"9x16": 42, "16x9": 30} (verilmeyen format → ilk değer). */
export const formatDegeri = <T,>(d: T | Partial<Record<FormatKey, T>>, key: FormatKey): T => {
  if (d === null || typeof d !== 'object' || Array.isArray(d)) return d as T;
  const r = d as Partial<Record<FormatKey, T>>;
  return (r[key] ?? Object.values(r)[0]) as T;
};

/** Kamera: konum, hedef ve görüş açısı t'den hesaplanıp her karede yazılır. fov formata göre verilebilir. */
export const Kamera = ({konum, hedef = [0, 0, 0], fov = 35}: {konum: V3; hedef?: V3; fov?: number | Partial<Record<FormatKey, number>>}) => {
  const {camera} = useThree();
  const {key} = useFormat();
  const f = formatDegeri(fov, key);
  useLayoutEffect(() => {
    kameraKoy(camera as THREE.PerspectiveCamera, konum, hedef, f);
  });
  return null;
};

/** Yarıçapı r olan nesnenin bu formatta kadraja sığdığı kamera uzaklığı (dikeyde daha uzak). */
export const useSigdir = (r: number, fov: number | Partial<Record<FormatKey, number>> = 35, pay = 1.15) => {
  const {key, w, h} = useFormat();
  return sigdirUzaklik(r, formatDegeri(fov, key), w / h, pay);
};

/** Işık ön ayarı: studyo · gun · aksam · gece · yumusak. yogunluk ve aci (radyan) karede değişebilir; oranlar sabit. */
export const Isik = ({on = 'studyo', yogunluk = 1, aci = 0, golge = false, golgeAlani = 6}: {on?: IsikAdi; yogunluk?: number; aci?: number;
  golge?: boolean; golgeAlani?: number}) => {
  const g = useMemo(() => isikKur(on, {golge, golgeAlani}), [on, golge, golgeAlani]);
  useLayoutEffect(() => {
    isikAyarla(g, yogunluk, aci);
  });
  return <primitive object={g} />;
};

/** Tohumlu nokta bulutu (yıldız, toz, kar, kıvılcım). Sürüklenme ve kırpışma gölgelendiricide t'den. */
export const Parcaciklar = ({n = 2000, tohum = 1, kabuk, kutu, ...a}: {n?: number; tohum?: number; kabuk?: [number, number]; kutu?: V3} & ParcacikAyar) => {
  const {t} = useZaman();
  const {height} = useVideoConfig();
  const geo = useNesne(() => noktaBulutu(n, tohum, kutu ? {kutu} : {kabuk: kabuk ?? [8, 16]}), [n, tohum, kutu?.join(), kabuk?.join()]);
  const m = useNesne(() => parcacikMalzemesi(a), [a.renk, a.boyut, a.saydamlik, a.suruklenme, a.parlak]);
  useLayoutEffect(() => {
    m.uniforms.uZaman.value = t;
    m.uniforms.uYukseklik.value = height;
  });
  return <points geometry={geo} material={m} />;
};

/** Tam ekran gölgelendirici arka planı: hazır (akis · dalga · halka) ya da kendi GLSL main()'in. */
export const ShaderAlani = ({frag = 'akis', renkler, tohum = 0, hiz = 1}: {frag?: AlanAdi | string; renkler?: [string, string, string]; tohum?: number;
  hiz?: number}) => {
  const {t} = useZaman();
  const {width, height} = useVideoConfig();
  const mesh = useMemo(() => shaderAlani(frag, renkler, tohum), [frag, renkler?.join(), tohum]);
  useLayoutEffect(() => () => {
    mesh.geometry.dispose();
    (mesh.material as THREE.Material).dispose();
  }, [mesh]);
  useLayoutEffect(() => {
    const u = (mesh.material as THREE.ShaderMaterial).uniforms;
    u.uZaman.value = t * hiz;
    u.uCoz.value.set(width, height);
  });
  return <primitive object={mesh} />;
};
