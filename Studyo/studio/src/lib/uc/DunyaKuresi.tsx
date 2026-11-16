// Dünya küresi: gerçek coğrafya dokusu (dunya.ts) + atmosfer kabuğu + konum işaretleri.
// Ülke vurgusu ve sınır çizgisi kullanıcı kararıdır (siyasi); hangi ülkenin vurgulandığı brief'te yazar.
import React, {useLayoutEffect} from 'react';
import * as THREE from 'three';
import {atmosferMalzemesi, malzeme, type V3} from './cekirdek';
import {type DunyaAyar, dunyaDokusu, enlemBoylam} from './dunya';
import {useNesne} from './Sahne3B';

export type DunyaKuresiProps = {
  yaricap?: number;
  /** Doku ayarı (deniz, kara, vurgu, sinir, izgara). Her karede değişmez: sabit tut (useMemo ya da sabit nesne). */
  doku?: DunyaAyar;
  /** Euler XYZ (radyan). yuzunuDondur(enlem, boylam) bir konumu kameraya çevirir. */
  donus?: V3;
  /** Atmosfer rengi; null: yok. */
  atmosfer?: string | null;
  atmosferGucu?: number;
  puruz?: number;
  golge?: boolean;
  /** Küreyle birlikte dönen nesneler (KureIsareti). */
  children?: React.ReactNode;
};

export const DunyaKuresi = ({yaricap = 1, doku, donus = [0, 0, 0], atmosfer = '#7cc4ff', atmosferGucu = 1.4, puruz = 0.8, golge = false,
  children}: DunyaKuresiProps) => {
  const harita = useNesne(() => dunyaDokusu(doku), [JSON.stringify(doku ?? {})]);
  const m = useNesne(() => new THREE.MeshStandardMaterial({map: harita, roughness: puruz, metalness: 0}), [harita, puruz]);
  const atm = useNesne(() => atmosferMalzemesi(atmosfer ?? '#000000', atmosferGucu), [atmosfer, atmosferGucu]);
  return (
    <group>
      <group rotation={donus}>
        <mesh material={m} castShadow={golge} receiveShadow={golge}>
          <sphereGeometry args={[yaricap, 128, 96]} />
        </mesh>
        {children}
      </group>
      {atmosfer ? (
        <mesh material={atm} scale={1.1}>
          <sphereGeometry args={[yaricap, 64, 48]} />
        </mesh>
      ) : null}
    </group>
  );
};

/** Küre yüzeyinde bir konum: tepe noktası + yayılan halka. nabiz 0..1 (t'den hesapla). DunyaKuresi'nin çocuğu olarak kullan. */
export const KureIsareti = ({enlem, boylam, yaricap = 1, renk = '#ff6a3d', boyut = 0.035, nabiz = 0}: {enlem: number; boylam: number;
  yaricap?: number; renk?: string; boyut?: number; nabiz?: number}) => {
  const p = enlemBoylam(enlem, boylam, yaricap);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), p.clone().normalize());
  const nokta = useNesne(() => malzeme.isikli(renk, {guc: 2.2}), [renk]);
  const halka = useNesne(() => new THREE.MeshBasicMaterial({color: renk, transparent: true, depthWrite: false, side: THREE.DoubleSide}), [renk]);
  useLayoutEffect(() => {
    halka.opacity = 0.85 * (1 - nabiz);
  });
  return (
    <group position={p} quaternion={q}>
      <mesh material={nokta} position={[0, 0, boyut * 0.5]}>
        <sphereGeometry args={[boyut, 24, 16]} />
      </mesh>
      <mesh material={halka} position={[0, 0, 0.002]} scale={1 + nabiz * 4}>
        <ringGeometry args={[boyut * 1.2, boyut * 1.6, 48]} />
      </mesh>
    </group>
  );
};
