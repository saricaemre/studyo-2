// Gerçek görüntü gölgelendiricileri (3b, zanaat §2 yol B ve D): saf Three.js, iki motorda ortak (Remotion src/lib/goruntu, HyperFrames uc.js).
// Dokular dışarıdan gelir (bir kez dondurulmuş görsel, video karesi, derinlik ve maske; ./st goruntu, ./st derinlik, ./st maske).
// Zaman yalnız uniform'la (uZaman = t); saat ve rastgelelik yok. Renk dönüşümü yok: doku değeri ekrana birebir (sRGB içinde hesap).
import * as THREE from 'three';

/** Kırpma penceresi (kaynağa göre 0–1; x, y sol üstten): ./st goruntu kadraj yolunun bir karesi. */
export type Pencere = [number, number, number, number];

/** Kaynağın formatı "kaplayan" ortalanmış penceresi (yalnız oranlar eşitken ya da kadraj yokken tek kare görselde). */
export const kaplayanPencere = (en: number, boy: number, w: number, h: number): Pencere => {
  const a = w / h;
  const [cw, ch] = en / boy > a ? [(boy * a) / en, 1] : [1, en / a / boy];
  return [(1 - cw) / 2, (1 - ch) / 2, cw, ch];
};

const ham = (t: THREE.Texture | null) => {
  if (t) {
    t.colorSpace = THREE.NoColorSpace;
    t.minFilter = THREE.LinearFilter;
    t.generateMipmaps = false;
  }
  return t;
};

// ---------------------------------------------------------------- 2.5B: derinlik haritalı düzlem
export type DerinlikAyar = {
  /** Kaynağın en ve boyu (piksel): düzlemin oranı. */
  en: number;
  boy: number;
  /** Uzun kenardaki bölüm sayısı (köşe yoğunluğu); 2.5B'de 320–512 yeter. */
  bolum?: number;
};

/** Görseli derinliğine göre öne/geri iten düzlem (yükseklik 1, genişlik en/boy). Beyaz = yakın: kameraya doğru uGuc/2 kadar gelir.
 *  Derinlik sıçramalarında (özne kenarı) gerilme olur: guc'u küçük tut (0,15–0,35), kamera hareketini ölçülü. */
export const derinlikDuzlemi = (a: DerinlikAyar) => {
  const oran = a.en / a.boy;
  const n = a.bolum ?? 384;
  const geo = new THREE.PlaneGeometry(oran, 1, oran >= 1 ? n : Math.max(8, Math.round(n * oran)), oran >= 1 ? Math.max(8, Math.round(n / oran)) : n);
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uRenk: {value: null}, uDerinlik: {value: null}, uGuc: {value: 0.25},
      uSisRengi: {value: new THREE.Vector3(0.5, 0.55, 0.6)}, uSis: {value: 0}, uIsik: {value: 0}, uKoyu: {value: 0},
    },
    vertexShader: /* glsl */ `
      uniform sampler2D uDerinlik; uniform float uGuc;
      varying vec2 vUv; varying float vD;
      void main() {
        vUv = uv;
        float d = texture2D(uDerinlik, uv).r;
        vD = d;
        vec3 p = position;
        p.z += (d - 0.5) * uGuc;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D uRenk; uniform vec3 uSisRengi; uniform float uSis; uniform float uIsik; uniform float uKoyu;
      varying vec2 vUv; varying float vD;
      void main() {
        vec3 c = texture2D(uRenk, vUv).rgb;
        c *= 1.0 + uIsik * (vD - 0.5);            // yakın biraz aydınlık, uzak biraz koyu (ışık derinliği)
        c = mix(c, uSisRengi, uSis * pow(1.0 - vD, 1.5));   // sis uzakta yoğun
        c *= 1.0 - uKoyu;
        gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
      }`,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  return mesh;
};

export type DerinlikDegerleri = {renk: THREE.Texture | null; derinlik: THREE.Texture | null; guc?: number; sis?: number; sisRengi?: string; isik?: number;
  koyu?: number};

/** Her karede: dokular ve değerler (sisRengi hex, sRGB değeriyle). */
export const derinlikAyarla = (m: THREE.Mesh, d: DerinlikDegerleri) => {
  const u = (m.material as THREE.ShaderMaterial).uniforms;
  u.uRenk.value = ham(d.renk);
  u.uDerinlik.value = ham(d.derinlik);
  u.uGuc.value = d.guc ?? 0.25;
  u.uSis.value = d.sis ?? 0;
  u.uIsik.value = d.isik ?? 0;
  u.uKoyu.value = d.koyu ?? 0;
  if (d.sisRengi) {
    const c = new THREE.Color(d.sisRengi);
    u.uSisRengi.value.set(c.r, c.g, c.b);
  }
};

/** 2.5B kamerası: ilerleme p (0..1, yumuşatılmış) ile itme (dolly), kayma (yan/üst) ve dönüş. Görünür alan yolun her anında düzlemin içinde
 *  kalır (kenar görünmez): uzak bölge guc/2 kadar geri itildiğinde de, kayma ve dönüş payıyla. odak: kaynağın hangi noktası kadrajın ortası
 *  (0–1, sol üstten; ör. özne). yakinlik < 1: daha dar görüş (özneye yakın). Merkezden kırpma yerine özneye göre yerleşim. */
export const derinlikKamerasi = (kamera: THREE.PerspectiveCamera, a: {en: number; boy: number; w: number; h: number; p: number; guc?: number; itme?: number;
  kayma?: [number, number]; donus?: number; odak?: [number, number]; yakinlik?: number; fazla?: number; fov?: number}) => {
  const fov = a.fov ?? 30;
  const tan = Math.tan(THREE.MathUtils.degToRad(fov) / 2);
  const oran = a.en / a.boy;
  const V = a.w / a.h;
  const [kx, ky] = a.kayma ?? [0, 0];
  const don = Math.abs(a.donus ?? 0);
  // izin verilen görünür yükseklik: düzlem eksi kayma ve dönüş payı, sonra yakınlık ve güvenlik payı
  const H = (Math.min(1 - Math.abs(ky), (oran - Math.abs(kx) - don * 0.6) / V) * (a.yakinlik ?? 1)) / (a.fazla ?? 1.03);
  const uzak = Math.max(0.05, H / (2 * tan) - (a.guc ?? 0.25) / 2);   // uzak bölge (z = −guc/2) de kadrajı kaplasın
  const z = uzak * (1 - (a.itme ?? 0.1) * a.p);
  // odak: düzlem koordinatında, görünür pencere düzlemin içinde kalacak biçimde sınırlı
  const [u, v] = a.odak ?? [0.5, 0.5];
  const yariH = H / 2, yariW = (H * V) / 2;
  const sinirX = Math.max(0, oran / 2 - yariW - Math.abs(kx) / 2), sinirY = Math.max(0, 0.5 - yariH - Math.abs(ky) / 2);
  const ox = Math.max(-sinirX, Math.min(sinirX, (u - 0.5) * oran)), oy = Math.max(-sinirY, Math.min(sinirY, 0.5 - v));
  const x = ox + kx * (a.p - 0.5), y = oy + ky * (a.p - 0.5);
  const d = (a.donus ?? 0) * (a.p - 0.5);
  kamera.fov = fov;
  kamera.aspect = V;
  kamera.position.set(x + Math.sin(d) * z, y, Math.cos(d) * z);
  kamera.lookAt(ox + (x - ox) * 0.35, oy + (y - oy) * 0.35, 0);       // hedef kameradan az kayar: paralaks
  kamera.updateProjectionMatrix();
};

// ---------------------------------------------------------------- D yolu: stilizasyon (tam ekran)
export const STIL_MODLARI = {isi: 0, yarimton: 1, cizgi: 2, nokta: 3, gercek: 4} as const;
export type StilModu = keyof typeof STIL_MODLARI | 'parcacik';
export type Koru = 'yok' | 'ozne' | 'arka';

const ORTAK_GLSL = /* glsl */ `
  uniform sampler2D uRenk; uniform sampler2D uDerinlik; uniform sampler2D uMaske;
  uniform float uDerinlikVar; uniform float uMaskeVar; uniform vec4 uPencere; uniform vec2 uCoz;
  vec2 kaynakUv(vec2 ekran) {            // ekran uv (sol alt) → kaynak uv (doku; flipY)
    return vec2(uPencere.x + ekran.x * uPencere.z, 1.0 - (uPencere.y + (1.0 - ekran.y) * uPencere.w));
  }
  float parlak(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
  float derin(vec2 s) { return uDerinlikVar > 0.5 ? texture2D(uDerinlik, s).r : 0.5; }
  float maske(vec2 s) { return uMaskeVar > 0.5 ? smoothstep(0.35, 0.65, texture2D(uMaske, s).r) : 0.0; }
`;

/** Tam ekran stilizasyon: isi (ısı görüntüsü), yarimton, cizgi (mürekkep), nokta (nokta matrisi), gercek (görüntü olduğu gibi: yalnız gizle
 *  ya da koru ile birlikte anlamlı, ör. rıza yokken yüzü mozaikle gizlenmiş gerçek görüntü). Kamera kullanılmaz (konum NDC'de).
 *  koru: "ozne" öznenin (maske) kendisi gerçek kalır, "arka" arka plan gerçek kalır. gizle: özne mozaikle gizlenir (rıza yoksa yüz). */
export const stilizeMalzemesi = () => new THREE.ShaderMaterial({
  uniforms: {
    uRenk: {value: null}, uDerinlik: {value: null}, uMaske: {value: null}, uDerinlikVar: {value: 0}, uMaskeVar: {value: 0},
    uPencere: {value: new THREE.Vector4(0, 0, 1, 1)}, uCoz: {value: new THREE.Vector2(1080, 1920)}, uZaman: {value: 0}, uMod: {value: 0},
    uR1: {value: new THREE.Vector3()}, uR2: {value: new THREE.Vector3()}, uR3: {value: new THREE.Vector3()},
    uGuc: {value: 1}, uBoyut: {value: 18}, uKoru: {value: 0}, uGizle: {value: 0}, uBlok: {value: 28}, uDerinlikPayi: {value: 0.35},
    uGizleMaske: {value: null}, uGizleVar: {value: 0},
  },
  depthTest: false,
  depthWrite: false,
  vertexShader: /* glsl */ `varying vec2 vEkran; void main() { vEkran = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
  fragmentShader: /* glsl */ `
    ${ORTAK_GLSL}
    uniform float uZaman; uniform int uMod; uniform vec3 uR1; uniform vec3 uR2; uniform vec3 uR3;
    uniform float uGuc; uniform float uBoyut; uniform int uKoru; uniform int uGizle; uniform float uBlok; uniform float uDerinlikPayi;
    uniform sampler2D uGizleMaske; uniform float uGizleVar;
    varying vec2 vEkran;
    // gizleme maskesi: zamanda ve uzayda genişletilmiş (./st maske → maske_genis); yoksa sıkı maske
    float gizleMaske(vec2 s) { return uGizleVar > 0.5 ? smoothstep(0.2, 0.5, texture2D(uGizleMaske, s).r) : maske(s); }
    vec3 uc(float x) { return x < 0.5 ? mix(uR1, uR2, x * 2.0) : mix(uR2, uR3, x * 2.0 - 1.0); }
    vec2 dondur(vec2 v, float a) { return vec2(cos(a) * v.x - sin(a) * v.y, sin(a) * v.x + cos(a) * v.y); }
    vec3 stil(vec2 e) {
      vec2 px = e * uCoz;
      vec2 s = kaynakUv(e);
      vec3 c = texture2D(uRenk, s).rgb;
      float L = parlak(c);
      float D = derin(s);
      if (uMod == 0) {                                   // ısı: parlaklık + derinlik → üç renkli ölçek
        float x = clamp(mix(L, D, uDerinlikPayi) * 1.15 - 0.05, 0.0, 1.0);
        return uc(pow(x, 1.0 / max(0.2, uGuc)));
      }
      if (uMod == 1) {                                   // yarım ton: 45° ızgara, nokta yarıçapı karanlıkla büyür
        vec2 q = dondur(px, 0.7853982) / uBoyut;
        vec2 h = fract(q) - 0.5;
        vec2 mm = dondur((floor(q) + 0.5) * uBoyut, -0.7853982) / uCoz;   // hücre merkezi ekranda
        float Lm = parlak(texture2D(uRenk, kaynakUv(clamp(mm, 0.0, 1.0))).rgb);
        float r = sqrt(clamp(1.0 - Lm, 0.0, 1.0)) * 0.62 * uGuc;
        float d = length(h);
        float k = 1.0 - smoothstep(r - 0.75 / uBoyut, r + 0.75 / uBoyut, d);
        return mix(uR1, uR2, k);
      }
      if (uMod == 2) {                                   // çizgi: parlaklık ve derinlik kenarları (Sobel) mürekkep, ton hafif
        vec2 o = vec2(1.0) / uCoz * max(1.0, uBoyut / 8.0);
        float gx = 0.0, gy = 0.0, dx = 0.0, dy = 0.0;
        for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++) {
          vec2 k2 = kaynakUv(e + vec2(float(i), float(j)) * o);
          float l = parlak(texture2D(uRenk, k2).rgb);
          float dd = derin(k2);
          float wx = float(i) * (j == 0 ? 2.0 : 1.0), wy = float(j) * (i == 0 ? 2.0 : 1.0);
          gx += l * wx; gy += l * wy; dx += dd * wx; dy += dd * wy;
        }
        float kenar = clamp((length(vec2(gx, gy)) * 1.4 + length(vec2(dx, dy)) * 4.0) * uGuc - 0.12, 0.0, 1.0);
        vec3 ton = mix(uR1, uR3, floor((1.0 - L) * 3.0) / 3.0 * 0.35);
        return mix(ton, uR2, kenar);
      }
      if (uMod == 4) return c;                           // gerçek: değişmez
      // nokta matrisi: hücre merkezinin rengi, yakın (derinlik) büyük nokta, koyu zemin
      vec2 hc = (floor(px / uBoyut) + 0.5) * uBoyut;
      vec2 sc = kaynakUv(hc / uCoz);
      vec3 cc = texture2D(uRenk, sc).rgb;
      float r = (0.18 + 0.32 * mix(parlak(cc), derin(sc), uDerinlikPayi)) * uGuc;
      float k = 1.0 - smoothstep(r - 0.04, r + 0.04, length(px / uBoyut - floor(px / uBoyut) - 0.5));
      return mix(uR1, cc * (0.85 + 0.3 * uR3), k);
    }
    void main() {
      vec2 e = vEkran;
      vec2 s = kaynakUv(e);
      vec3 gercek = texture2D(uRenk, s).rgb;
      float m = maske(s);
      vec3 st = stil(e);
      vec3 c = uKoru == 1 ? mix(st, gercek, m) : (uKoru == 2 ? mix(gercek, st, m) : st);
      if (uGizle == 1) {                                 // mozaik: öznenin bölgesi iri bloklara (yüz tanınmaz)
        vec2 b = (floor(e * uCoz / uBlok) + 0.5) * uBlok / uCoz;
        vec2 sb = kaynakUv(b);
        float mb = max(gizleMaske(s), gizleMaske(sb));
        vec3 moz = texture2D(uRenk, sb).rgb;
        c = mix(c, moz, smoothstep(0.05, 0.3, mb));
      }
      gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
    }`,
});

export type StilDegerleri = {renk: THREE.Texture | null; derinlik?: THREE.Texture | null; maske?: THREE.Texture | null; gizleMaske?: THREE.Texture | null;
  pencere: Pencere;
  w: number; h: number; t: number; mod: Exclude<StilModu, 'parcacik'>; renkler: [string, string, string]; guc?: number; boyut?: number; koru?: Koru;
  gizle?: boolean; blok?: number; derinlikPayi?: number};

const rgb = (hex: string, v: THREE.Vector3) => {
  const c = new THREE.Color(hex);
  v.set(c.r, c.g, c.b);
};

/** Her karede: dokular, pencere (kadraj), renkler (hex) ve ayarlar. */
export const stilizeAyarla = (m: THREE.ShaderMaterial, d: StilDegerleri) => {
  const u = m.uniforms;
  u.uRenk.value = ham(d.renk);
  u.uDerinlik.value = ham(d.derinlik ?? null);
  u.uMaske.value = ham(d.maske ?? null);
  u.uDerinlikVar.value = d.derinlik ? 1 : 0;
  u.uMaskeVar.value = d.maske ? 1 : 0;
  u.uGizleMaske.value = ham(d.gizleMaske ?? null);
  u.uGizleVar.value = d.gizleMaske ? 1 : 0;
  u.uPencere.value.set(...d.pencere);
  u.uCoz.value.set(d.w, d.h);
  u.uZaman.value = d.t;
  u.uMod.value = STIL_MODLARI[d.mod];
  rgb(d.renkler[0], u.uR1.value);
  rgb(d.renkler[1], u.uR2.value);
  rgb(d.renkler[2], u.uR3.value);
  u.uGuc.value = d.guc ?? 1;
  u.uBoyut.value = d.boyut ?? 18;
  u.uKoru.value = {yok: 0, ozne: 1, arka: 2}[d.koru ?? 'yok'];
  u.uGizle.value = d.gizle ? 1 : 0;
  u.uBlok.value = d.blok ?? 28;
  u.uDerinlikPayi.value = d.derinlikPayi ?? 0.35;
};

/** Tam ekran dörtgen (stilizasyon için). */
export const tamEkran = (mat: THREE.Material) => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat);
  m.frustumCulled = false;
  return m;
};

// ---------------------------------------------------------------- D yolu: görüntüden parçacık
/** Görüntü ızgarası noktalara döner: renk görüntüden, büyüklük derinlikten (yakın büyük), sürüklenme t ve tohumdan (uzak çok, yakın az).
 *  sutun: yatay nokta sayısı (satır kaynağın oranından). Konum NDC'de: kamera kullanılmaz. */
export const goruntuParcaciklari = (sutun: number, w: number, h: number, tohum = 1) => {
  const satir = Math.max(2, Math.round((sutun * h) / w));
  const n = sutun * satir;
  const uv = new Float32Array(n * 2);
  const rs = new Float32Array(n);
  for (let j = 0, k = 0; j < satir; j++) {
    for (let i = 0; i < sutun; i++, k++) {
      uv[k * 2] = (i + 0.5) / sutun;
      uv[k * 2 + 1] = (j + 0.5) / satir;
      const x = Math.sin((k + 1) * 12.9898 + tohum * 78.233) * 43758.5453;
      rs[k] = x - Math.floor(x);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  geo.setAttribute('aEkran', new THREE.BufferAttribute(uv, 2));
  geo.setAttribute('aRs', new THREE.BufferAttribute(rs, 1));
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uRenk: {value: null}, uDerinlik: {value: null}, uMaske: {value: null}, uDerinlikVar: {value: 0}, uMaskeVar: {value: 0},
      uPencere: {value: new THREE.Vector4(0, 0, 1, 1)}, uCoz: {value: new THREE.Vector2(w, h)}, uZaman: {value: 0}, uBoyut: {value: 6},
      uGuc: {value: 1}, uAralik: {value: w / sutun},
    },
    depthTest: false,
    depthWrite: false,
    vertexShader: /* glsl */ `
      ${ORTAK_GLSL}
      uniform float uZaman; uniform float uBoyut; uniform float uGuc; uniform float uAralik;
      attribute vec2 aEkran; attribute float aRs;
      varying vec3 vR; varying float vA;
      void main() {
        vec2 s = kaynakUv(aEkran);
        vR = texture2D(uRenk, s).rgb;
        float d = derin(s);
        float m = maske(s);
        float uzak = (1.0 - d) * (1.0 - m);              // özne (maske) yerinde durur, uzak arka plan dağılır
        float a = aRs * 6.2831853 + uZaman * (0.35 + aRs * 0.4);
        vec2 kay = vec2(cos(a), sin(a * 1.3)) * uzak * uGuc * uAralik * 2.2;
        kay.y += uzak * uGuc * uAralik * 0.9 * sin(uZaman * 0.6 + aRs * 9.0);
        vec2 p = aEkran * uCoz + kay;
        gl_Position = vec4(p / uCoz * 2.0 - 1.0, 0.0, 1.0);
        gl_PointSize = uBoyut * (0.55 + 0.75 * max(d, m));
        vA = 1.0;
      }`,
    fragmentShader: /* glsl */ `
      varying vec3 vR; varying float vA;
      void main() {
        float r = length(gl_PointCoord - 0.5);
        if (r > 0.5) discard;
        gl_FragColor = vec4(vR, vA * (1.0 - smoothstep(0.38, 0.5, r)));
      }`,
    transparent: true,
  });
  const p = new THREE.Points(geo, mat);
  p.frustumCulled = false;
  return p;
};

export const parcacikAyarla = (p: THREE.Points, d: {renk: THREE.Texture | null; derinlik?: THREE.Texture | null; maske?: THREE.Texture | null;
  pencere: Pencere; t: number; boyut?: number; guc?: number}) => {
  const u = (p.material as THREE.ShaderMaterial).uniforms;
  u.uRenk.value = ham(d.renk);
  u.uDerinlik.value = ham(d.derinlik ?? null);
  u.uMaske.value = ham(d.maske ?? null);
  u.uDerinlikVar.value = d.derinlik ? 1 : 0;
  u.uMaskeVar.value = d.maske ? 1 : 0;
  u.uPencere.value.set(...d.pencere);
  u.uZaman.value = d.t;
  u.uBoyut.value = d.boyut ?? 6;
  u.uGuc.value = d.guc ?? 1;
};
