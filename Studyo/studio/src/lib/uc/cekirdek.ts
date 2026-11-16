// 3B katmanın çekirdeği: saf Three.js (React'siz). Remotion kiti (src/lib/uc/*.tsx) ve HyperFrames (assets/lib/uc/uc.js, esbuild ile
// bu dosyadan paketlenir) aynı ışığı, malzemeyi ve üreteci kullanır.
// Zaman yalnız dışarıdan gelir (t, saniye): saat, çizim döngüsü, tohumsuz rastgelelik yok. Rastgelelik tohumla (rand).
import * as THREE from 'three';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';

export type V3 = [number, number, number];

/** Gölgelendirici rengi: hex'in sRGB bileşenleri. Ham ShaderMaterial renk dönüşümü yapmaz; böylece ekranda tam hex çıkar. */
export const srgb = (hex: string) => new THREE.Color(hex).convertLinearToSRGB();

/** Deterministik sözde rastgele (0..1); src/lib/anim.ts'deki rand ile aynı. */
export const rand = (seed: number) => {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

// ---------------------------------------------------------------- kamera
/** Yarıçapı r olan bir nesnenin kadraja sığdığı uzaklık. Dikey formatta yatay görüş açısı dar olduğu için uzaklık büyür. */
export const sigdirUzaklik = (r: number, fovDerece: number, enBoy: number, pay = 1.15) => {
  const dikey = THREE.MathUtils.degToRad(fovDerece) / 2;
  const yatay = Math.atan(Math.tan(dikey) * enBoy);
  return (r * pay) / Math.sin(Math.min(dikey, yatay));
};

/** Kamerayı t'nin fonksiyonu olarak yerleştirir (konum, hedef, görüş açısı). */
export const kameraKoy = (kamera: THREE.PerspectiveCamera, konum: V3, hedef: V3 = [0, 0, 0], fov?: number) => {
  kamera.position.set(...konum);
  if (fov !== undefined) kamera.fov = fov;
  kamera.lookAt(...hedef);
  kamera.updateProjectionMatrix();
};

// ---------------------------------------------------------------- ışık
export type IsikAdi = 'studyo' | 'gun' | 'aksam' | 'gece' | 'yumusak';
type Yonlu = {renk: string; guc: number; yon: V3};
type IsikTanim = {anahtar?: Yonlu; dolgu: {gok: string; yer: string; guc: number}; kontur?: Yonlu};

/** Işık ön ayarları. Dolgu (yarımküre ışığı) her ön ayarda var: tek yönlü ışıkta nesnenin arka yüzü simsiyah kalır. */
export const ISIKLAR: Record<IsikAdi, IsikTanim> = {
  studyo: {anahtar: {renk: '#fff4e6', guc: 2.6, yon: [-4, 6, 5]}, dolgu: {gok: '#dfe8ff', yer: '#3a3028', guc: 0.9}, kontur: {renk: '#cfe0ff', guc: 1.4, yon: [3, 3, -6]}},
  gun: {anahtar: {renk: '#fff1d6', guc: 3.0, yon: [4, 9, 3]}, dolgu: {gok: '#9cc8ff', yer: '#6b5a40', guc: 1.2}},
  aksam: {anahtar: {renk: '#ffb37a', guc: 2.4, yon: [-7, 2.2, 3]}, dolgu: {gok: '#5a6ea8', yer: '#2a1a14', guc: 0.7}, kontur: {renk: '#7fa6ff', guc: 1.0, yon: [5, 3, -5]}},
  gece: {anahtar: {renk: '#9fb8ff', guc: 1.2, yon: [3, 6, -2]}, dolgu: {gok: '#1c2a4a', yer: '#0a0a10', guc: 0.5}, kontur: {renk: '#ffb070', guc: 0.8, yon: [-4, 1, 5]}},
  yumusak: {dolgu: {gok: '#ffffff', yer: '#d8d0c4', guc: 2.2}},
};

export type IsikAyar = {golge?: boolean; golgeAlani?: number; golgeCozunurluk?: number};

/** Ön ayarın ışıklarını bir grupta kurar. Güç ve yön her karede isikAyarla ile değişir (oranlar sabit kalır). */
export const isikKur = (on: IsikAdi, a: IsikAyar = {}) => {
  const T = ISIKLAR[on];
  if (!T) throw new Error(`Işık ön ayarı yok: ${on} (${Object.keys(ISIKLAR).join(', ')})`);
  const g = new THREE.Group();
  g.name = `isik-${on}`;
  const dolgu = new THREE.HemisphereLight(T.dolgu.gok, T.dolgu.yer, T.dolgu.guc);
  dolgu.name = 'dolgu';
  g.add(dolgu);
  for (const ad of ['anahtar', 'kontur'] as const) {
    const y = T[ad];
    if (!y) continue;
    const l = new THREE.DirectionalLight(y.renk, y.guc);
    l.name = ad;
    l.position.set(...y.yon);
    if (ad === 'anahtar' && a.golge) {
      const s = a.golgeAlani ?? 6;
      l.castShadow = true;
      l.shadow.mapSize.set(a.golgeCozunurluk ?? 2048, a.golgeCozunurluk ?? 2048);
      Object.assign(l.shadow.camera, {left: -s, right: s, top: s, bottom: -s, near: 0.1, far: 60});
      l.shadow.bias = -0.0004;
      l.shadow.normalBias = 0.02;
    }
    g.add(l);
  }
  g.userData.tanim = T;
  return g;
};

/** yogunluk: bütün ışıklar aynı oranla (anahtar/dolgu oranı korunur). aci: anahtar ve kontur Y ekseninde döner (radyan). */
export const isikAyarla = (g: THREE.Group, yogunluk = 1, aci = 0) => {
  const T = g.userData.tanim as IsikTanim;
  for (const l of g.children) {
    if (l instanceof THREE.HemisphereLight) l.intensity = T.dolgu.guc * yogunluk;
    if (l instanceof THREE.DirectionalLight) {
      const y = T[l.name as 'anahtar' | 'kontur']!;
      l.intensity = y.guc * yogunluk;
      const c = Math.cos(aci), s = Math.sin(aci);
      l.position.set(y.yon[0] * c + y.yon[2] * s, y.yon[1], -y.yon[0] * s + y.yon[2] * c);
    }
  }
};

/** Yansıma ortamı (stüdyo odası, PMREM). Cam ve metal onsuz siyah görünür. */
export const ortamKur = (renderer: THREE.WebGLRenderer, sahne: THREE.Scene, guc = 1) => {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const oda = new RoomEnvironment();
  const doku = pmrem.fromScene(oda, 0.04).texture;
  oda.traverse((o) => (o as THREE.Mesh).geometry?.dispose?.());
  pmrem.dispose();
  sahne.environment = doku;
  sahne.environmentIntensity = guc;
  return doku;
};

// ---------------------------------------------------------------- malzeme
type MalzemeAyar = {puruz?: number; guc?: number; kalinlik?: number; ic?: string};

/** Malzeme ailesi. Hepsi PBR; tek ton yüzey yerine ışık ve ortamla canlanır. */
export const malzeme = {
  /** Kil / maket: mat, sıcak, yumuşak gölgeli. */
  kil: (renk: string, a: MalzemeAyar = {}) => new THREE.MeshStandardMaterial({color: renk, roughness: a.puruz ?? 0.85, metalness: 0}),
  /** Düz mat boya. */
  mat: (renk: string) => new THREE.MeshStandardMaterial({color: renk, roughness: 1, metalness: 0}),
  /** Parlak plastik / ürün kabuğu: vernik katmanlı. */
  plastik: (renk: string, a: MalzemeAyar = {}) =>
    new THREE.MeshPhysicalMaterial({color: renk, roughness: a.puruz ?? 0.32, metalness: 0, clearcoat: 0.7, clearcoatRoughness: 0.12}),
  /** Metal: ortam ister (Sahne3B ortam="oda", varsayılan). */
  metal: (renk: string, a: MalzemeAyar = {}) => new THREE.MeshStandardMaterial({color: renk, roughness: a.puruz ?? 0.28, metalness: 1}),
  /** Cam benzeri: ışık geçirir, arkasını kırar. Pahalıdır (sahneyi bir kez daha çizer); sahnede bir iki tane. */
  cam: (renk = '#ffffff', a: MalzemeAyar = {}) =>
    new THREE.MeshPhysicalMaterial({color: renk, roughness: a.puruz ?? 0.05, metalness: 0, transmission: 1, ior: 1.45, thickness: a.kalinlik ?? 0.6,
      attenuationColor: new THREE.Color(a.ic ?? renk), attenuationDistance: 2.5}),
  /** Kendinden ışıklı (ekran, kor, tabela). guc 1–3. */
  isikli: (renk: string, a: MalzemeAyar = {}) => new THREE.MeshStandardMaterial({color: '#000000', emissive: renk, emissiveIntensity: a.guc ?? 1.5}),
};

/** Kenarda parlayan atmosfer kabuğu (küre için, BackSide). */
export const atmosferMalzemesi = (renk = '#6fc3ff', guc = 1.4) =>
  new THREE.ShaderMaterial({
    transparent: true,
    side: THREE.BackSide,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    uniforms: {uRenk: {value: srgb(renk)}, uGuc: {value: guc}},
    vertexShader: `varying vec3 vN; varying vec3 vV;
      void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    // kosinüs pow'a girmeden önce [0,1]'e kıstırılır (negatif taban GLSL'de tanımsız)
    fragmentShader: `uniform vec3 uRenk; uniform float uGuc; varying vec3 vN; varying vec3 vV;
      void main(){ float r = pow(clamp(1.0 - abs(dot(vN, vV)), 0.0, 1.0), 2.4); gl_FragColor = vec4(uRenk * r * uGuc, r); }`,
  });

// ---------------------------------------------------------------- parçacık
/** n nokta, tohumlu: küre kabuğunda (rIc..rDis) ya da kutuda (kutu: [gx, gy, gz]). aTohum özniteliği her noktanın kendi evresidir. */
export const noktaBulutu = (n: number, tohum = 1, yer: {kabuk?: [number, number]; kutu?: V3} = {kabuk: [8, 16]}) => {
  const p = new Float32Array(n * 3), s = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const a = rand(tohum * 9973 + i * 3 + 1), b = rand(tohum * 9973 + i * 3 + 2), c = rand(tohum * 9973 + i * 3 + 3);
    if (yer.kutu) {
      p.set([(a - 0.5) * yer.kutu[0], (b - 0.5) * yer.kutu[1], (c - 0.5) * yer.kutu[2]], i * 3);
    } else {
      const [r0, r1] = yer.kabuk ?? [8, 16];
      const u = a * Math.PI * 2, v = Math.acos(2 * b - 1), r = r0 + c * (r1 - r0);
      p.set([r * Math.sin(v) * Math.cos(u), r * Math.cos(v), r * Math.sin(v) * Math.sin(u)], i * 3);
    }
    s[i] = rand(tohum * 7919 + i);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(p, 3));
  g.setAttribute('aTohum', new THREE.BufferAttribute(s, 1));
  return g;
};

export type ParcacikAyar = {renk?: string; boyut?: number; saydamlik?: number; suruklenme?: number; parlak?: boolean};

/** Nokta malzemesi: konum ve kırpışma gölgelendiricide uZaman'dan hesaplanır (kare t'nin saf fonksiyonu). */
export const parcacikMalzemesi = (a: ParcacikAyar = {}) =>
  new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: a.parlak === false ? THREE.NormalBlending : THREE.AdditiveBlending,
    uniforms: {uZaman: {value: 0}, uRenk: {value: srgb(a.renk ?? '#cfe4ff')}, uBoyut: {value: a.boyut ?? 6},
      uSaydam: {value: a.saydamlik ?? 0.9}, uSurukle: {value: a.suruklenme ?? 0.4}, uYukseklik: {value: 1080}},
    vertexShader: `attribute float aTohum; uniform float uZaman, uBoyut, uSurukle, uYukseklik; varying float vK;
      void main(){
        float e = aTohum * 6.2831;
        vec3 p = position + uSurukle * vec3(sin(uZaman * 0.31 + e), cos(uZaman * 0.23 + e * 1.7), sin(uZaman * 0.19 + e * 2.3));
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vK = 0.65 + 0.35 * sin(uZaman * (1.2 + aTohum) + e * 3.0);
        gl_PointSize = uBoyut * (uYukseklik / 1080.0) * (10.0 / max(0.1, -mv.z)) * (0.6 + 0.8 * aTohum);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `uniform vec3 uRenk; uniform float uSaydam; varying float vK;
      void main(){ float d = length(gl_PointCoord - 0.5); float a = smoothstep(0.5, 0.05, d); gl_FragColor = vec4(uRenk, a * uSaydam * vK); }`,
  });

// ---------------------------------------------------------------- gölgelendirici alanı (tam ekran arka plan)
const GURULTU = `
float h21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float gn(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(h21(i), h21(i + vec2(1, 0)), u.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), u.x), u.y); }
float fbm(vec2 p){ float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++){ s += a * gn(p); p = p * 2.03 + 17.1; a *= 0.5; } return s; }
`;

/** Hazır alanlar. Hepsi uZaman (sn), uCoz (piksel), uRenk1..3, uTohum okur. */
export const ALANLAR = {
  /** Akan bulut / mürekkep: alan bükmeli fbm, üç renk arasında. */
  akis: `${GURULTU}
    void main(){ vec2 uv = gl_FragCoord.xy / uCoz.y; float t = uZaman * 0.12;
      vec2 q = vec2(fbm(uv * 2.2 + uTohum + t), fbm(uv * 2.2 + 5.2 - t));
      float n = fbm(uv * 2.0 + 2.5 * q + vec2(t * 0.7, -t * 0.4));
      vec3 c = mix(uRenk1, uRenk2, smoothstep(0.25, 0.7, n)); c = mix(c, uRenk3, smoothstep(0.62, 0.9, n * q.x * 1.6));
      gl_FragColor = vec4(c, 1.0); }`,
  /** Yavaş dalga bantları (topografya çizgisi gibi). */
  dalga: `${GURULTU}
    void main(){ vec2 uv = gl_FragCoord.xy / uCoz.y; float n = fbm(uv * 1.6 + uTohum + vec2(uZaman * 0.05, 0.0));
      float b = fract(n * 9.0 - uZaman * 0.25); float c = smoothstep(0.0, 0.06, b) * smoothstep(0.16, 0.08, b);
      vec3 col = mix(uRenk1, uRenk2, n); col = mix(col, uRenk3, c * 0.85); gl_FragColor = vec4(col, 1.0); }`,
  /** Merkezden yayılan ışık halkaları (nabız, sinyal). */
  halka: `${GURULTU}
    void main(){ vec2 uv = (gl_FragCoord.xy - 0.5 * uCoz) / uCoz.y; float r = length(uv);
      float w = fract(r * 3.2 - uZaman * 0.35); float halka = smoothstep(0.0, 0.03, w) * smoothstep(0.12, 0.04, w) * exp(-r * 1.6);
      vec3 col = mix(uRenk1, uRenk2, smoothstep(0.9, 0.0, r) * 0.6 + 0.15 * fbm(uv * 3.0 + uTohum));
      col += uRenk3 * halka * 1.2; gl_FragColor = vec4(col, 1.0); }`,
};
export type AlanAdi = keyof typeof ALANLAR;

/** Tam ekran gölgelendirici dörtgeni: sahnenin en arkasında, kameradan bağımsız. frag: hazır ad ya da kendi GLSL main()'in. */
export const shaderAlani = (frag: AlanAdi | string = 'akis', renkler: [string, string, string] = ['#0b1020', '#23407a', '#ff7a45'], tohum = 0) => {
  const kod = (ALANLAR as Record<string, string>)[frag] ?? frag;
  const m = new THREE.ShaderMaterial({
    depthWrite: false,
    depthTest: false,
    uniforms: {uZaman: {value: 0}, uCoz: {value: new THREE.Vector2(1080, 1920)}, uTohum: {value: tohum},
      uRenk1: {value: srgb(renkler[0])}, uRenk2: {value: srgb(renkler[1])}, uRenk3: {value: srgb(renkler[2])}},
    vertexShader: `void main(){ gl_Position = vec4(position.xy, 0.999, 1.0); }`,
    fragmentShader: `uniform float uZaman, uTohum; uniform vec2 uCoz; uniform vec3 uRenk1, uRenk2, uRenk3;\n${kod}`,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), m);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1000;
  return mesh;
};
