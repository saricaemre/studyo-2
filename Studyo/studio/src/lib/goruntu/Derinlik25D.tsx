// 2.5B (3b): durağan görsel ya da video derinliğiyle düzleme döner; kamera itme, kayma ve dönüşle gezinir, paralaks gerçek derinlikten.
// Derinlik ./st derinlik ile bir kez çıkarılır ve dondurulur. Yazılımla (swangle) çizilir: bayt bayt aynı (./st deterministik).
import {useThree} from '@react-three/fiber';
import React, {useLayoutEffect, useMemo} from 'react';
import {staticFile, useVideoConfig} from 'remotion';
import type * as THREE from 'three';
import {clamp01, easeInOutCubic} from '../anim';
import {Sahne3B, useZaman} from '../uc/Sahne3B';
import {derinlikAyarla, derinlikDuzlemi, derinlikKamerasi} from '../uc/goruntu';
import {type GoruntuKaydi, kaynakKaresi, useGoruntuKaydi, videoKaresiAdresi} from './bilgi';
import {useKareDokusu} from './doku';

export type Derinlik25DProps = {
  film: string;
  ad: string;
  /** Kamera yolunun süresi (sn): ilerleme t / sure, yumuşatılmış. */
  sure: number;
  /** Derinliğin gücü (düzlem birimi; 0,15–0,35): büyüdükçe paralaks artar, özne kenarında gerilme de. */
  guc?: number;
  /** Kameranın yaklaşma payı (0–0,4). */
  itme?: number;
  /** Kameranın yol boyunca yan ve üst kayması (düzlem birimi, ör. [0.08, 0]). */
  kayma?: [number, number];
  /** Yol boyunca yörünge açısı (radyan, ör. 0.12). */
  donus?: number;
  /** Kadrajın ortasına gelen kaynak noktası (0–1, sol üstten; ör. öznenin yeri) ve görüşü daraltma (1 = en geniş). Formata göre ver
   *  (useFormat().key): yatayda dikey bir görselin bandı özneye göre seçilir, merkezden kırpılmaz. */
  odak?: [number, number];
  yakinlik?: number;
  /** Uzakta sis (renk hex, güç 0–1) ve derinlik ışığı (yakın aydınlık, 0–0,6). */
  sis?: {renk: string; guc: number};
  isik?: number;
  /** Sahneyi karartma (0–1; geçiş için karede değiştir). */
  koyu?: number;
  fov?: number;
  arka?: string;
  /** Videoda başlangıç (sn) ve hız. */
  baslangic?: number;
  hiz?: number;
};

const Duzlem: React.FC<Derinlik25DProps & {k: GoruntuKaydi}> = ({film, ad, k, sure, guc = 0.25, itme = 0.12, kayma = [0.06, 0], donus = 0, odak, yakinlik,
  sis, isik = 0.25, koyu = 0, fov = 30, baslangic = 0, hiz = 1}) => {
  const {t, kare, fps} = useZaman();
  const {width, height} = useVideoConfig();
  const {camera} = useThree();
  if (!k.derinlik) throw new Error(`${ad}: derinlik yok → ./st derinlik ${film} ${ad}`);
  const i = kaynakKaresi(k, kare, fps, baslangic, hiz);
  const adres = (yol: string) => (k.tur === 'video' ? videoKaresiAdresi(staticFile(`${film}/${yol}`), i, fps) : staticFile(`${film}/${yol}`));
  const renk = useKareDokusu(adres(k.dosya));
  const der = useKareDokusu(adres(k.derinlik));
  const mesh = useMemo(() => derinlikDuzlemi({en: k.en, boy: k.boy}), [k.en, k.boy]);
  useLayoutEffect(() => () => {
    mesh.geometry.dispose();
    (mesh.material as THREE.Material).dispose();
  }, [mesh]);
  useLayoutEffect(() => {
    derinlikAyarla(mesh, {renk, derinlik: der, guc, sis: sis?.guc ?? 0, sisRengi: sis?.renk, isik, koyu});
    derinlikKamerasi(camera as THREE.PerspectiveCamera, {en: k.en, boy: k.boy, w: width, h: height, p: easeInOutCubic(clamp01(t / sure)), guc, itme, kayma,
      donus, odak, yakinlik, fov});
  });
  return <primitive object={mesh} />;
};

const Kayitli: React.FC<Derinlik25DProps> = (p) => {
  const k = useGoruntuKaydi(p.film, p.ad);
  return k ? <Duzlem {...p} k={k} /> : null;
};

export const Derinlik25D: React.FC<Derinlik25DProps> = (p) => (
  <Sahne3B arka={p.arka ?? '#000000'} ortam={null} tonlama="yok">
    <Kayitli {...p} />
  </Sahne3B>
);
