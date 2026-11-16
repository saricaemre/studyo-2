import {Easing} from 'remotion';

/** Eski videoların kare hızı. Yeni videolar kare hızını script.json → fps'ten alır; sahne kodu useVideoConfig().fps kullanır. */
export const FPS = 24;

export type Pt = [number, number];

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
export const lerpPt = (a: Pt, b: Pt, p: number): Pt => [lerp(a[0], b[0], p), lerp(a[1], b[1], p)];

export const easeInOutCubic = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
export const easeOutCubic = (x: number) => 1 - Math.pow(1 - x, 3);
export const easeInCubic = (x: number) => x * x * x;
export const easeInOutSine = (x: number) => -(Math.cos(Math.PI * x) - 1) / 2;
export const easeOutBack = (x: number) => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
};

/** start anından itibaren dur saniyede 0→1 (easing'li). */
export const prog = (t: number, start: number, dur: number, ease: (x: number) => number = easeInOutCubic) =>
  ease(clamp01((t - start) / dur));

/** start'ta yükselip hold sonra sönen nabız (0→1→0). */
export const pulse = (t: number, start: number, rise: number, hold: number, fall: number) => {
  if (t < start) return 0;
  if (t < start + rise) return easeOutCubic((t - start) / rise);
  if (t < start + rise + hold) return 1;
  return 1 - easeInOutCubic(clamp01((t - start - rise - hold) / fall));
};

/** Deterministik sözde rastgele (0..1). */
export const rand = (seed: number) => {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** Yumuşak titreşim (alev, dalga vb.). */
export const wobble = (t: number, seed: number) =>
  Math.sin(t * 7.3 + seed) * 0.5 + Math.sin(t * 13.1 + seed * 2.1) * 0.3 + Math.sin(t * 23.7 + seed * 3.7) * 0.2;

export const ptsToPath = (pts: Pt[], closed = false) =>
  'M' + pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('L') + (closed ? 'Z' : '');

/** Catmull-Rom ile yumuşatıp hafif el çizimi titremesi ekler. */
export const smooth = (pts: Pt[], segs = 6, jitter = 0, seed = 1): Pt[] => {
  const out: Pt[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    for (let j = 0; j < segs; j++) {
      const t = j / segs;
      const t2 = t * t;
      const t3 = t2 * t;
      const x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3);
      const y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3);
      const k = out.length;
      out.push([x + (rand(seed * 1000 + k) - 0.5) * jitter, y + (rand(seed * 2000 + k) - 0.5) * jitter]);
    }
  }
  out.push(pts[pts.length - 1]);
  return out;
};

/** Örneklenmiş çoklu çizgi üzerinde uzunluk ve kesir → nokta/açı. */
export const polyline = (pts: Pt[]) => {
  const cum = [0];
  for (let i = 1; i < pts.length; i++) {
    cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  }
  const length = cum[cum.length - 1];
  const at = (f: number): {p: Pt; angle: number} => {
    const d = clamp01(f) * length;
    let i = 1;
    while (i < cum.length - 1 && cum[i] < d) i++;
    const seg = cum[i] - cum[i - 1] || 1;
    const u = (d - cum[i - 1]) / seg;
    const a = pts[i - 1];
    const b = pts[i];
    return {p: lerpPt(a, b, u), angle: (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI};
  };
  return {length, at};
};

export const pointInPoly = (p: Pt, poly: Pt[]) => {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};

// ---------------------------------------------------------------- hareket dili (zanaat.md §3–4)
// Hepsi t'nin saf fonksiyonu: önceki kareden durum taşımaz, her kare tek başına hesaplanır.

/** Ortak dönüşüm eğrisi: bir filmdeki bütün biçim dönüşümleri ve kamera bu eğriye biner (cubic-bezier .45,0,.15,1). */
export const GECIS = Easing.bezier(0.45, 0, 0.15, 1);
/** Yerleşme eğrisi: hızlı gelir, yumuşak oturur, taşmaz (cubic-bezier .16,1,.3,1). */
export const YERLES = Easing.bezier(0.16, 1, 0.3, 1);
/** Vuruşa bağlı hareket vuruştan bu kadar önce başlar ki vuruşa otursun (sn). */
export const ONDEN = 0.05;

/**
 * Kritik sönümlü yay: dt ≤ 0 → 0, sonra 1'e taşmadan oturur. `oturma`: %99'a varış süresi (sn).
 * Kapalı form 1 − (1 + w·dt)·e^(−w·dt), w = 6,64 / oturma. Biçim için ≈0,35 sn, kamera için ≈0,6 sn.
 */
export const yay = (dt: number, oturma = 0.35) => {
  if (dt <= 0) return 0;
  const w = 6.64 / oturma;
  return 1 - (1 + w * dt) * Math.exp(-w * dt);
};

/**
 * Hafif taşan yay (sönüm oranı z < 1). z = 0,78 ≈ %2 taşma. Yalnız stil paketi taşmaya izin veriyorsa.
 * `oturma` yaklaşık %98'e varış süresidir (4 / (z·w)).
 */
export const yayTasan = (dt: number, oturma = 0.45, z = 0.78) => {
  if (dt <= 0) return 0;
  const w = 4 / (z * oturma);
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * dt) * (Math.cos(wd * dt) + (z / Math.sqrt(1 - z * z)) * Math.sin(wd * dt));
};

/**
 * Hedefi birkaç kez değişen değer: her değişim için bir yay toplanır, değer yine t'nin saf fonksiyonu kalır.
 * adimlar: [başlama anı (sn), yeni hedef][] (zamana göre sıralı). Ör. yaylar(t, 0, [[1.2, 300], [2.4, 120]])
 */
export const yaylar = (t: number, bas: number, adimlar: [number, number][], oturma = 0.35, egri: (dt: number, o: number) => number = yay) => {
  let v = bas;
  let onceki = bas;
  for (const [t0, hedef] of adimlar) {
    v += (hedef - onceki) * egri(t - t0, oturma);
    onceki = hedef;
  }
  return v;
};

/**
 * Beklemede nefes: [bas, bit] aralığında ölçek 1 → 1 + miktar (yumuşak, tek yönlü). Ölü kare bırakmaz.
 * Yakın planda ≈0,012; kapanış kartında ≈0,06 (öğrenimler #18).
 */
export const nefes = (t: number, bas: number, bit: number, miktar = 0.012) =>
  1 + miktar * easeInOutSine(clamp01((t - bas) / Math.max(1e-6, bit - bas)));

/**
 * Okuma süresi (sn): yazı bu kadar okunur kalmadan süs hareketine başlamaz ve ekrandan gitmez.
 * Altyazıda yaygın sınır ≈17 karakter/sn + 0,4 sn tanıma; en az 0,6 sn.
 */
export const okuma = (metin: string) => Math.max(0.6, 0.4 + metin.replace(/\s+/g, ' ').trim().length / 17);

/**
 * Karenin zamanı: hareket bulanıklığı bir kareyi kesirli ara zamanlarda çizer; sayaç, yazılan metin, saat gibi
 * "değeri okunan" şeyler ara zamanı değil karenin zamanını okumalı, yoksa rakamlar üst üste biner (zanaat.md §5).
 * 180° obtüratörde ara zamanlar ±0,25 kare içinde kalır, yuvarlama hepsini aynı kareye bağlar.
 */
export const kareZamani = (t: number, fps: number) => Math.round(t * fps) / fps;
