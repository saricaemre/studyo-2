// 3B model (GLB): kütüphaneden filme alınan dosyalar (./st 3b kullan → public/<id>/varliklar/3b/<slug>.glb). İki motorda ortak (React'siz).
// Çözücüler yerelden (Draco geometri, KTX2/Basis doku, Meshopt); CDN yok. Animasyon zamanı dışarıdan (t): animasyonSur her karede
// eylemi baştan kurar ve mixer.setTime(t) ile konar; ileri ya da geri atlamada aynı poz çıkar. Saat, çizim döngüsü yok.
import * as THREE from 'three';
import {DRACOLoader} from 'three/examples/jsm/loaders/DRACOLoader.js';
import {type GLTF, GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {KTX2Loader} from 'three/examples/jsm/loaders/KTX2Loader.js';
import {clone as iskeletliKopya} from 'three/examples/jsm/utils/SkeletonUtils.js';

export type {GLTF};

/** Çözücü klasörleri (sonu / ile). Remotion: staticFile('uc/draco'), HyperFrames: assets/lib/three/addons/libs/draco/gltf. */
export type Cozucu = {draco: string; basis: string};
export type YukleAyar = {cozucu: Cozucu; /** KTX2 dokulu modeller için gerekir (biçim desteği çizicinin kendisinden). */ renderer?: THREE.WebGLRenderer};

const yukleyiciler = new Map<string, GLTFLoader>();
const modeller = new Map<string, Promise<GLTF>>();
const hazir = new Map<string, GLTF>();
let meshopt: Promise<unknown> | null = null;
let sira: Promise<unknown> = Promise.resolve();

/** GLB'nin JSON bölümündeki extensionsUsed: hangi çözücünün gerektiğini dosyayı çözmeden söyler. */
const uzantilar = (veri: ArrayBuffer): string[] => {
  const d = new DataView(veri);
  if (d.getUint32(0, true) !== 0x46546c67) return [];
  const uz = d.getUint32(12, true);
  try {
    return JSON.parse(new TextDecoder().decode(new Uint8Array(veri, 20, uz))).extensionsUsed ?? [];
  } catch {
    return [];
  }
};

const yukleyici = (a: YukleAyar) => {
  const anahtar = `${a.cozucu.draco}|${a.cozucu.basis}|${a.renderer ? 'r' : '-'}`;
  let l = yukleyiciler.get(anahtar);
  if (!l) {
    l = new GLTFLoader();
    // Tek işçi: parçalar istendiği sırayla çözülür (paralel işçide bitiş sırası, dolayısıyla malzeme sırası her seferinde değişiyordu).
    l.setDRACOLoader(new DRACOLoader().setDecoderPath(a.cozucu.draco).setDecoderConfig({type: 'wasm'}).setWorkerLimit(1));
    if (a.renderer) l.setKTX2Loader(new KTX2Loader().setTranscoderPath(a.cozucu.basis).setWorkerLimit(1).detectSupport(a.renderer));
    yukleyiciler.set(anahtar, l);
  }
  return l;
};

/** Malzemeleri gezinti sırasıyla yeniden kurar. three opak nesneleri malzeme kimliğine göre sıralar; kimlik, malzemenin yaratıldığı
 *  anla verilir ve yükleyicide bu an doku ve parça çözümünün bitiş sırasına bağlıdır. Yeniden kurulunca çizim sırası (bitişik
 *  yüzlerdeki piksel) her çizimde aynı olur. */
const malzemeleriSirala = (kok: THREE.Object3D) => {
  const yeni = new Map<THREE.Material, THREE.Material>();
  const al = (m: THREE.Material) => {
    if (!yeni.has(m)) {
      yeni.set(m, m.clone());
      m.dispose();
    }
    return yeni.get(m)!;
  };
  kok.traverse((n) => {
    const ag = n as THREE.Mesh;
    if (ag.isMesh) ag.material = Array.isArray(ag.material) ? ag.material.map(al) : al(ag.material);
  });
};

/** GLB'yi indirir ve çözer; aynı adres bir kez yüklenir (sonraki çağrılar aynı sözü döndürür). Yüklemeler sıradadır: biri bitmeden
 *  öteki başlamaz, kimlikler (malzeme, nesne) çağrı sırasıyla verilir. */
export const glbYukle = (url: string, a: YukleAyar): Promise<GLTF> => {
  let s = modeller.get(url);
  if (!s) {
    const l = yukleyici(a);
    const once = sira;
    s = once.then(() => new THREE.FileLoader(l.manager).setResponseType('arraybuffer').loadAsync(url)).then(async (veri) => {
      const ext = uzantilar(veri as ArrayBuffer);
      if (ext.includes('KHR_texture_basisu') && !a.renderer) throw new Error(`${url}: KTX2 dokulu; yüklerken çiziciyi ver ({renderer})`);
      if (ext.some((e) => e.endsWith('_meshopt_compression'))) {
        // Meshopt çözücüsü içe aktarılırken WASM derler: yalnız gereken dosyada yüklenir.
        meshopt ??= import('three/examples/jsm/libs/meshopt_decoder.module.js').then((m) => m.MeshoptDecoder);
        l.setMeshoptDecoder((await meshopt) as Parameters<GLTFLoader['setMeshoptDecoder']>[0]);
      }
      const g = await l.parseAsync(veri as ArrayBuffer, url.slice(0, url.lastIndexOf('/') + 1));
      malzemeleriSirala(g.scene);
      hazir.set(url, g);
      return g;
    });
    sira = s.catch(() => undefined);
    modeller.set(url, s);
  }
  return s;
};

/** Daha önce yüklenmiş model (yoksa null): aynı sayfada ikinci kullanım beklemeden çizilir. */
export const glbHazir = (url: string) => hazir.get(url) ?? null;

export type HazirlaAyar = {
  /** Modeli bu yüksekliğe ölçekle (sahne birimi; modeller metre ölçeğinde gelir, 1 birim = 1 m). */
  yukseklik?: number;
  /** Ya da en büyük boyutu buna ölçekle. İkisi de yoksa ölçek 1 (gerçek boyut). */
  boyut?: number;
  /** "zemin": tabanın ortası (0,0,0)'da (varsayılan; yere oturur) · "merkez": kutunun ortası · "kendi": dosyadaki pivot. */
  yerlesim?: 'zemin' | 'merkez' | 'kendi';
  /** Ağlar gölge atar ve alır (Sahne3B golge + Isik golge de gerekir). */
  golge?: boolean;
  /** Görünüşe uydurmak için malzeme değişimi: her ağın malzemesinin KOPYASI gelir; yeni malzeme döndür ya da yerinde değiştir.
   *  Örnek: (m) => malzeme.kil('#e0a458') tek tonlu maket · (m) => { (m as any).color?.set('#ffd9b0') } köşe rengini tonlar. */
  malzeme?: (m: THREE.Material, ag: THREE.Mesh) => THREE.Material | void;
  /** Parça başına malzeme (köşe rengine göre): renkleAyir. `malzeme`den sonra uygulanır. */
  renkler?: RenkKurali[];
};

// ---------------------------------------------------------------- köşe rengi (COLOR_0) ile parça
// threejsassets'in düşük poligon modelleri tek ortak malzeme + köşe rengi taşır; parça adı yoktur (cam, pirinç, demir aynı ağda).
// Parçayı rengi seçer: ./st 3b onizle paleti (sRGB hex) basar, renkleAyir o renkteki üçgenlere ayrı malzeme verir.

const ucgenRenkleri = (g: THREE.BufferGeometry) => {
  const c = g.getAttribute('color') as THREE.BufferAttribute | undefined;
  if (!c) return null;
  const ix = g.getIndex();
  const n = (ix ? ix.count : g.getAttribute('position').count) / 3;
  const renk = new THREE.Color(), out: number[][] = [];
  for (let i = 0; i < n; i++) {
    let r = 0, gg = 0, b = 0;
    for (let k = 0; k < 3; k++) {
      const v = ix ? ix.getX(i * 3 + k) : i * 3 + k;
      r += c.getX(v) / 3; gg += c.getY(v) / 3; b += c.getZ(v) / 3;
    }
    renk.setRGB(r, gg, b, THREE.LinearSRGBColorSpace).getRGB(renk, THREE.SRGBColorSpace);
    out.push([renk.r * 255, renk.g * 255, renk.b * 255]);
  }
  return out;
};
const uzaklik = (a: number[], b: number[]) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const hex = (c: number[]) => '#' + c.map((x) => Math.round(Math.min(255, Math.max(0, x))).toString(16).padStart(2, '0')).join('');
const rgb = (h: string) => {
  const n = new THREE.Color(h).getHex();  // sRGB
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

/** Köşe rengi paleti: üçgenlerin rengi (sRGB, ekranda görünen) yakınlığa göre kümelenir (tolerans: 0–255 uzaklık), en çok üçgenden
 *  aza. Tonu titretilmiş yüzeyler ("tint-noised planks") bir küme olur. Köşe rengi olmayan modelde boş. */
export const renkPaleti = (kok: THREE.Object3D, tolerans = 24): {renk: string; ucgen: number}[] => {
  const kume: {c: number[]; n: number}[] = [];
  kok.traverse((o) => {
    const ag = o as THREE.Mesh;
    const rs = ag.isMesh ? ucgenRenkleri(ag.geometry) : null;
    for (const c of rs ?? []) {
      const k = kume.find((x) => uzaklik(x.c, c) <= tolerans);
      if (k) {
        k.c = k.c.map((v, i) => (v * k.n + c[i]) / (k.n + 1));
        k.n++;
      } else kume.push({c, n: 1});
    }
  });
  return kume.sort((a, b) => b.n - a.n).map((k) => ({renk: hex(k.c), ucgen: k.n}));
};

/** renk: paletteki sRGB hex (ya da birkaç tanesi) · tolerans: 0–255 uzaklık (varsayılan 24) · malzeme: yeni malzeme ya da özgün
 *  malzemenin kopyasını alıp döndüren işlev (köşe rengi açık kalır; tam renk için köşe rengisiz yeni malzeme ver: malzeme.metal('#…')). */
export type RenkKurali = {renk: string | string[]; tolerans?: number; malzeme: THREE.Material | ((m: THREE.Material) => THREE.Material)};

/** Köşe rengine göre parça malzemesi: her üçgen, rengine en yakın kurala (tolerans içinde) gider; kalanlar özgün malzemede kalır.
 *  Geometri kopyalanır (öteki kopyalar etkilenmez), üçgenler kural sırasıyla gruplanır, malzeme dizisi olur. Ağ başına tek malzemeli
 *  ağlarda çalışır. Örnek (gaz lambası): renkleAyir(kok, [{renk: '#c9d6cf', malzeme: malzeme.isikli('#ffb347', {guc: 2})}]) camı yakar. */
export const renkleAyir = (kok: THREE.Object3D, kurallar: RenkKurali[]) => {
  const K = kurallar.map((k) => ({...k, cs: (Array.isArray(k.renk) ? k.renk : [k.renk]).map(rgb), tol: k.tolerans ?? 24}));
  let ayrilan = 0;
  kok.traverse((o) => {
    const ag = o as THREE.Mesh;
    if (!ag.isMesh || Array.isArray(ag.material)) return;
    const rs = ucgenRenkleri(ag.geometry);
    if (!rs) return;
    const kova: number[][] = [[], ...K.map(() => [])];
    rs.forEach((c, i) => {
      let en = -1, d = Infinity;
      K.forEach((k, j) => k.cs.forEach((h) => {
        const u = uzaklik(c, h);
        if (u <= k.tol && u < d) [en, d] = [j, u];
      }));
      kova[en + 1].push(i);
    });
    if (kova[0].length === rs.length) return;
    const g = ag.geometry.clone();
    const ix = ag.geometry.getIndex();
    const yeni = new Uint32Array(rs.length * 3);
    let p = 0;
    g.clearGroups();
    kova.forEach((ucgenler, m) => {
      if (!ucgenler.length) return;
      g.addGroup(p, ucgenler.length * 3, m);
      for (const i of ucgenler) for (let k = 0; k < 3; k++) yeni[p++] = ix ? ix.getX(i * 3 + k) : i * 3 + k;
    });
    g.setIndex(new THREE.BufferAttribute(yeni, 1));
    const ozgun = ag.material as THREE.Material;
    ag.geometry = g;
    ag.material = [ozgun, ...K.map((k) => (typeof k.malzeme === 'function' ? k.malzeme(ozgun.clone()) : k.malzeme))];
    ayrilan += rs.length - kova[0].length;
  });
  return ayrilan;
};

/** Yüklenen modelin bağımsız bir kopyası, dış grupta: grup serbestçe konur, döner, ölçeklenir; içteki model ölçülüp yerleştirilmiştir.
 *  userData.boyut: ölçekten sonraki boyut (Vector3). Geometri kopyalar arasında paylaşılır; malzeme yalnız `malzeme` verilirse kopyalanır. */
export const modelHazirla = (g: GLTF | THREE.Object3D, a: HazirlaAyar = {}) => {
  const kaynak = 'scene' in g ? g.scene : g;
  const ic = iskeletliKopya(kaynak);
  ic.traverse((n) => {
    const ag = n as THREE.Mesh;
    if (!ag.isMesh) return;
    if (a.golge) ag.castShadow = ag.receiveShadow = true;
    if (a.malzeme) {
      const degis = (m: THREE.Material) => {
        const k = m.clone();
        return a.malzeme!(k, ag) ?? k;
      };
      ag.material = Array.isArray(ag.material) ? ag.material.map(degis) : degis(ag.material);
    }
  });
  if (a.renkler?.length) renkleAyir(ic, a.renkler);
  const kutu = new THREE.Box3().setFromObject(ic, true);
  const boy = kutu.getSize(new THREE.Vector3());
  const s = a.yukseklik ? a.yukseklik / (boy.y || 1) : a.boyut ? a.boyut / (Math.max(boy.x, boy.y, boy.z) || 1) : 1;
  ic.scale.multiplyScalar(s);
  const m = kutu.getCenter(new THREE.Vector3());
  const yer = a.yerlesim ?? 'zemin';
  if (yer !== 'kendi') ic.position.set(-m.x * s, yer === 'zemin' ? -kutu.min.y * s : -m.y * s, -m.z * s);
  const kok = new THREE.Group();
  kok.name = `model:${kaynak.name || 'glb'}`;
  kok.add(ic);
  kok.userData.boyut = boy.multiplyScalar(s);
  return kok;
};

/** Malzemeleri gezer (örneğin kopyalanmış bir modelin rengini karede değiştirmek için). */
export const malzemeleriGez = (kok: THREE.Object3D, f: (m: THREE.Material, ag: THREE.Mesh) => void) =>
  kok.traverse((n) => {
    const ag = n as THREE.Mesh;
    if (ag.isMesh) (Array.isArray(ag.material) ? ag.material : [ag.material]).forEach((m) => f(m, ag));
  });

export type Animasyon = {mixer: THREE.AnimationMixer; klipler: THREE.AnimationClip[]; adlar: string[]};

/** Modelin animasyonları (GLB'de varsa). kok: modelHazirla'nın döndürdüğü grup. */
export const animasyonKur = (kok: THREE.Object3D, klipler: THREE.AnimationClip[]): Animasyon => ({
  mixer: new THREE.AnimationMixer(kok), klipler, adlar: klipler.map((k) => k.name),
});

/** t anındaki poz (saniye). klip: ad, sıra ya da "hepsi" (dışa aktarıcılar çoğu zaman her nesneye ayrı klip yazar; birlikte oynarlar).
 *  dongu false → son pozda kalır. Her çağrıda eylemler baştan kurulur (atlamaya dayanıklı). */
export const animasyonSur = (an: Animasyon, {klip = 0, t, hiz = 1, dongu = true}: {klip?: string | number; t: number; hiz?: number; dongu?: boolean}) => {
  const ks = klip === 'hepsi' ? an.klipler : [typeof klip === 'number' ? an.klipler[klip] : an.klipler.find((x) => x.name === klip)];
  if (!ks.length || ks.some((k) => !k)) throw new Error(`Animasyon yok: ${klip} (var: ${an.adlar.join(', ') || 'hiç'})`);
  an.mixer.stopAllAction();
  for (const k of ks as THREE.AnimationClip[]) {
    const e = an.mixer.clipAction(k).reset();
    e.setLoop(dongu ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
    e.clampWhenFinished = !dongu;
    e.play();
  }
  an.mixer.setTime(Math.max(0, t) * hiz);
};
