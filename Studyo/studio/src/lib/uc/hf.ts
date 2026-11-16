// HyperFrames girişi: pipeline/hf.py bunu esbuild ile assets/lib/uc/uc.js'e paketler (three dışarıda; import map yerel kopyayı gösterir).
// Sahne kodu: import {kur, zamanaBagla, isikKur, malzeme, …} from "./assets/lib/uc/uc.js"  (hf/CLAUDE.md → 3B katman)
import * as THREE from 'three';
import {ortamKur} from './cekirdek';
import {type GLTF, glbYukle} from './glb';
import {type Pencere, kaplayanPencere} from './goruntu';

export * from './cekirdek';
export * from './dunya';
export * from './glb';
export * from './goruntu';

declare global {
  interface Window {
    ST?: {w: number; h: number; format: string};
    __hfThreeTime?: number;
    __hf?: {buildReady?: Record<string, Promise<unknown>>};
  }
}

export type KurAyar = {
  canvas: HTMLCanvasElement;
  w?: number;
  h?: number;
  golge?: boolean;
  /** "oda": stüdyo yansıma ortamı (cam ve metal için); null: yok */
  ortam?: 'oda' | null;
  ortamGucu?: number;
  /** "aces" (Remotion kitiyle aynı) ya da "yok" (renkler hex'e birebir) */
  tonlama?: 'aces' | 'yok';
  /** sahne arka rengi; null: saydam (arkadaki HTML görünür) */
  arka?: string | null;
  fov?: number;
};

/** Çizici + sahne + kamera. Boyut stüdyonun formatından (ST.w × ST.h), piksel oranı 1 (cihazdan bağımsız). */
export const kur = (a: KurAyar) => {
  const w = a.w ?? window.ST?.w ?? 1920, h = a.h ?? window.ST?.h ?? 1080;
  const renderer = new THREE.WebGLRenderer({canvas: a.canvas, antialias: true, alpha: a.arka === null, preserveDrawingBuffer: true});
  renderer.setPixelRatio(1);
  renderer.setSize(w, h, false);
  renderer.toneMapping = a.tonlama === 'yok' ? THREE.NoToneMapping : THREE.ACESFilmicToneMapping;
  if (a.golge) {
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  }
  const sahne = new THREE.Scene();
  if (a.arka) sahne.background = new THREE.Color(a.arka);
  if (a.ortam !== null) ortamKur(renderer, sahne, a.ortamGucu ?? 1);
  const kamera = new THREE.PerspectiveCamera(a.fov ?? 35, w / h, 0.1, 500);
  return {renderer, sahne, kamera, w, h};
};

/** Sahneyi HyperFrames zamanına bağlar: her arayışta (hf-seek) ve açılışta ciz(t) bir kez çağrılır. Çizim döngüsü yok. */
export const zamanaBagla = (ciz: (t: number) => void) => {
  window.addEventListener('hf-seek', (e) => ciz((e as CustomEvent<{time: number}>).detail.time));
  ciz(window.__hfThreeTime || 0);
};

/** Çözücüler: ./st (hf.esitle) three'nin kendi dosyalarını assets/lib/uc/cozucu/'ya koyar; CDN yok. */
export const COZUCU = {draco: './assets/lib/uc/cozucu/draco/', basis: './assets/lib/uc/cozucu/basis/'};
let modelSayac = 0;

/** GLB'yi yükler ("varliklar/3b/<slug>.glb"; ./st 3b kullan koyar). HyperFrames çizime başlamadan önce yüklenmesini bekler
 *  (__hf.buildReady). Modülün başında await ile çağır, sonra modelHazirla; KTX2 dokulu modelde {renderer} ver. */
export const modelYukle = (url: string, a: {renderer?: THREE.WebGLRenderer} = {}): Promise<GLTF> => {
  const s = glbYukle(url, {cozucu: COZUCU, renderer: a.renderer});
  const hf = (window.__hf ??= {});
  (hf.buildReady ??= {})[`uc-model-${++modelSayac}`] = s;
  return s;
};

/** Gerçek görüntü (./st goruntu, ./st derinlik, ./st maske): kaydı (goruntu/bilgi.json) ve durağan görselin dokularını yükler; HyperFrames
 *  ilk çizimi bekler (__hf.buildReady). Modülün başında await ile çağır. 2.5B (derinlikDuzlemi) ve stilizasyon (stilizeMalzemesi,
 *  goruntuParcaciklari) HyperFrames'te durağan görselde; videonun kare kare dokusu Remotion'da (src/lib/goruntu). */
export const goruntuYukle = (ad: string) => {
  const s = (async () => {
    const r = await fetch('goruntu/bilgi.json');
    if (!r.ok) throw new Error('goruntu/bilgi.json yok: ./st goruntu ekle <id> …');
    const B = await r.json();
    const kayit = B[ad];
    if (!kayit) throw new Error(`gerçek görüntü kaydında yok: ${ad}`);
    if (kayit.tur !== 'gorsel') throw new Error(`${ad} video: HyperFrames'te 2.5B ve stilizasyon durağan görselde (video: Remotion src/lib/goruntu)`);
    const yukle = (u?: string) => (u ? new THREE.TextureLoader().loadAsync(u) : Promise.resolve(null));
    const [renk, derinlik, maske, gizleMaske] = await Promise.all([yukle(kayit.dosya), yukle(kayit.derinlik), yukle(kayit.maske), yukle(kayit.maske_genis)]);
    const pencere = (format: string, w: number, h: number): Pencere => kayit.kadraj?.[format]?.kareler?.[0] ?? kaplayanPencere(kayit.en, kayit.boy, w, h);
    return {kayit, renk, derinlik, maske, gizleMaske, pencere};
  })();
  const hf = (window.__hf ??= {});
  (hf.buildReady ??= {})[`uc-goruntu-${ad}`] = s;
  return s;
};
