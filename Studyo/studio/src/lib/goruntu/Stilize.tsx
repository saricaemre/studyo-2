// D yolu (3b): gerçek görüntü kodla stilize edilir; hareket gerçek kalır, yüz yeniden yaratılmaz (yapay zekâya girmez, kural 2).
// Modlar: isi (ısı görüntüsü), yarimton, cizgi (mürekkep), nokta (nokta matrisi), parcacik (görüntü noktalara döner, uzak arka plan dağılır),
// gercek (görüntü olduğu gibi; gizle ile: rıza yokken yüzü mozaikle gizlenmiş gerçek görüntü).
// koru "ozne": öznenin kendisi gerçek, çevresi stilize · "arka": tersi · gizle: özne mozaikle gizlenir (rıza yoksa yüz tanınmaz).
// Maske (./st maske) ve derinlik (./st derinlik) varsa kullanılır; kadraj yolu (./st goruntu kadraj) pencereyi verir. Yazılımla çizilir.
import React, {useLayoutEffect, useMemo} from 'react';
import {staticFile, useVideoConfig} from 'remotion';
import type * as THREE from 'three';
import {useFormat} from '../format';
import {Sahne3B, useZaman} from '../uc/Sahne3B';
import {type Koru, type StilModu, goruntuParcaciklari, parcacikAyarla, stilizeAyarla, stilizeMalzemesi, tamEkran} from '../uc/goruntu';
import {type GoruntuKaydi, kaynakKaresi, pencereAl, useGoruntuKaydi, videoKaresiAdresi} from './bilgi';
import {useKareDokusu} from './doku';

/** Modların varsayılan üç rengi: [zemin/soğuk, mürekkep/orta, vurgu/sıcak]. Görünüşün renklerini vermek daha iyidir. */
export const STIL_RENKLERI: Record<StilModu, [string, string, string]> = {
  isi: ['#0b0630', '#d92f6b', '#ffe27a'],
  yarimton: ['#f3ede2', '#15110e', '#7a6c5c'],
  cizgi: ['#f3ede2', '#17120e', '#8c7f70'],
  nokta: ['#07080c', '#000000', '#ffffff'],
  parcacik: ['#05060a', '#000000', '#ffffff'],
  gercek: ['#000000', '#000000', '#000000'],
};

export type StilizeProps = {
  film: string;
  ad: string;
  mod: StilModu;
  renkler?: [string, string, string];
  /** Etkinin gücü (1 = varsayılan). */
  guc?: number;
  /** Izgara / nokta / çizgi kalınlığı (piksel, 1080 kısa kenara göre). */
  boyut?: number;
  koru?: Koru;
  gizle?: boolean;
  /** Mozaik bloğu (piksel, 1080 kısa kenara göre). */
  blok?: number;
  /** Isı ve nokta modunda derinliğin payı (0 = yalnız parlaklık, 1 = yalnız derinlik). */
  derinlikPayi?: number;
  /** Parçacık modunda yatay nokta sayısı. */
  sutun?: number;
  baslangic?: number;
  hiz?: number;
};

const Ic: React.FC<StilizeProps & {k: GoruntuKaydi}> = ({film, ad, k, mod, renkler, guc = 1, boyut = 18, koru = 'yok', gizle = false, blok = 30,
  derinlikPayi = 0.35, sutun = 150, baslangic = 0, hiz = 1}) => {
  const {t, kare, fps} = useZaman();
  const {width, height} = useVideoConfig();
  const {key, unit} = useFormat();
  if ((koru !== 'yok' || gizle) && !k.maske) throw new Error(`${ad}: koru/gizle için maske gerekli → ./st maske ${film} ${ad}`);
  const i = kaynakKaresi(k, kare, fps, baslangic, hiz);
  const pencere = pencereAl(k, key, i, width, height, film, ad);
  const adres = (yol?: string) => (!yol ? null : k.tur === 'video' ? videoKaresiAdresi(staticFile(`${film}/${yol}`), i, fps) : staticFile(`${film}/${yol}`));
  const renk = useKareDokusu(adres(k.dosya));
  const der = useKareDokusu(adres(k.derinlik));
  const msk = useKareDokusu(adres(k.maske));
  const gmsk = useKareDokusu(gizle ? adres(k.maske_genis) : null);  // yüz gizleme: zamanda ve uzayda genişletilmiş maske
  const R = renkler ?? STIL_RENKLERI[mod];
  const nesne = useMemo(() => (mod === 'parcacik' ? goruntuParcaciklari(sutun, width, height, 3) : tamEkran(stilizeMalzemesi())),
    [mod, sutun, width, height]);
  useLayoutEffect(() => () => {
    nesne.geometry.dispose();
    (nesne.material as THREE.Material).dispose();
  }, [nesne]);
  useLayoutEffect(() => {
    if (mod === 'parcacik') {
      parcacikAyarla(nesne as THREE.Points, {renk, derinlik: der, maske: msk, pencere, t, boyut: boyut * unit * 0.45, guc});
    } else {
      stilizeAyarla((nesne as THREE.Mesh).material as THREE.ShaderMaterial, {renk, derinlik: der, maske: msk, pencere, w: width, h: height, t, mod,
        renkler: R, guc, boyut: boyut * unit, koru, gizle, gizleMaske: gmsk, blok: blok * unit, derinlikPayi});
    }
  });
  return <primitive object={nesne} />;
};

const Kayitli: React.FC<StilizeProps> = (p) => {
  const k = useGoruntuKaydi(p.film, p.ad);
  return k ? <Ic {...p} k={k} /> : null;
};

export const Stilize: React.FC<StilizeProps> = (p) => (
  <Sahne3B arka={(p.renkler ?? STIL_RENKLERI[p.mod])[0]} ortam={null} tonlama="yok">
    <Kayitli {...p} />
  </Sahne3B>
);
