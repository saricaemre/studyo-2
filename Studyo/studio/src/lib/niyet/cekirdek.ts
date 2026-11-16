/**
 * Niyetli altyazının çekirdeği (iki motorda ortak; Remotion NiyetliAltyazi.tsx, HyperFrames hf.ts → assets/lib/niyet/niyet.js).
 * Veri pipeline/niyet.py'den (timeline.json → niyet): kelimenin şiddeti ağırlığa ve boyuta, perdesi genişliğe ve hafif yükselmeye
 * bağlı; konuşmacı rengi; sayfa ve satırlar her format için önceden kurulu (tarayıcı satır bölmez). Burada yalnız t anındaki hâl
 * hesaplanır: saf fonksiyon, saat ya da rastgelelik yok (kural 8).
 */

export type NiyetKelime = {
  i: number; metin: string; bas: number; son: number; k: string;
  s: number; p: number; wght: number; wdth: number; boyut: number; kay: number;
};
export type NiyetSatir = {kelimeler: number[]; genislik: number; boyut: number};
export type NiyetSayfa = {bas: number; son: number; olcek: number; merkez: number; satirlar: NiyetSatir[]; yukseklik: number};
export type NiyetYerlesim = {kutu: {x: number; w: number; alt: number; ust: number; unit: number}; sayfalar: NiyetSayfa[]};
export type NiyetKonusmaci = {ad: string; renk: string; renk_once: string};
export type NiyetVeri = {
  surum: number;
  yazi: {aile: string; opsz: number};
  zemin: string; alfa: number; pad: [number, number]; satir_ara: number;
  konusmacilar: Record<string, NiyetKonusmaci>;
  kelimeler: NiyetKelime[];
  formatlar: Record<string, NiyetYerlesim>;
};

export type KelimeHal = {metin: string; renk: string; boyut: number; ayar: string; kalkis: number; bosluk: string | null; boslukBoyut: number};
export type SatirHal = {boyut: number; kelimeler: KelimeHal[]};
export type AltyaziHal = {
  kutu: NiyetYerlesim['kutu']; merkez: number; opaklik: number; kayma: number;
  zemin: string; pad: [number, number]; satirAra: number; aile: string; satirlar: SatirHal[];
};

const kis = (x: number) => Math.min(1, Math.max(0, x));
const cikis = (x: number) => 1 - (1 - x) ** 3;

const rgb = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
export const karistir = (a: string, b: string, k: number) => {
  const A = rgb(a), B = rgb(b);
  return `rgb(${A.map((x, i) => Math.round(x * (1 - k) + B[i] * k)).join(', ')})`;
};
export const saydam = (h: string, alfa: number) => `rgba(${rgb(h).join(', ')}, ${alfa})`;

export const ayar = (wght: number, wdth: number, opsz: number) => `'wght' ${wght}, 'wdth' ${wdth}, 'opsz' ${opsz}, 'GRAD' 0`;

export const GIRIS = 0.14;   // sayfa girişi, sn
export const RENK = 0.08;    // kelimenin söylenince rengine geçişi, sn
export const SICRA = 0.24;   // söylenen kelimenin sıçraması, sn (yüksekliği şiddetle)

/** t anındaki sayfa. Sayfalar zamanda sıralı ve örtüşmez (niyet.py). */
export const sayfaBul = (Y: NiyetYerlesim, t: number): number => {
  for (let n = 0; n < Y.sayfalar.length; n++) if (t >= Y.sayfalar[n].bas && t < Y.sayfalar[n].son) return n;
  return -1;
};

/** t anında çizilecek altyazı; boşsa null. fmt: '9x16' | '16x9' | … */
export const altyaziHali = (N: NiyetVeri, fmt: string, t: number): AltyaziHal | null => {
  const Y = N.formatlar[fmt];
  if (!Y) return null;
  const n = sayfaBul(Y, t);
  if (n < 0) return null;
  const S = Y.sayfalar[n];
  const u = Y.kutu.unit * S.olcek;
  const g = cikis(kis((t - S.bas) / GIRIS));
  const sonraki = Y.sayfalar[n + 1];
  const bosaCikar = !sonraki || sonraki.bas > S.son + 0.05;  // ardından sayfa geliyorsa kesme; boşluğa çıkıyorsa kısa sönüş
  const sonus = bosaCikar ? kis((S.son - t) / 0.08) : 1;
  const satirlar = S.satirlar.map((s) => ({
    boyut: s.boyut,
    kelimeler: s.kelimeler.map((i, j) => {
      const K = N.kelimeler[i];
      const R = N.konusmacilar[K.k];
      const a = kis((t - K.bas) / RENK);
      const q = kis((t - K.bas) / SICRA);
      const boyut = K.boyut * u;
      const sonra = j + 1 < s.kelimeler.length ? N.kelimeler[s.kelimeler[j + 1]] : null;
      return {
        metin: K.metin,
        renk: karistir(R.renk_once, R.renk, a),
        boyut,
        ayar: ayar(K.wght, K.wdth, N.yazi.opsz),
        // perde: tiz kelime biraz yukarıda (kay < 0); söylenince şiddetiyle orantılı küçük bir sıçrama
        kalkis: (K.kay - (t >= K.bas ? Math.sin(Math.PI * q) * (0.03 + 0.07 * K.s) : 0)) * boyut,
        bosluk: sonra ? ayar(sonra.wght, sonra.wdth, N.yazi.opsz) : null,
        boslukBoyut: sonra ? sonra.boyut * u : 0,
      };
    }),
  }));
  return {
    kutu: Y.kutu, merkez: S.merkez, opaklik: g * sonus, kayma: (1 - g) * 0.18 * Math.max(...S.satirlar.map((s) => s.boyut)),
    zemin: saydam(N.zemin, N.alfa), pad: N.pad, satirAra: N.satir_ara, aile: N.yazi.aile, satirlar,
  };
};
