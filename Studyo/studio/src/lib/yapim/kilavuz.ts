// Kılavuz kipi (yapım filmi, ./st yapim): filmin karesindeki yerleşim kutularını DOM'dan ölçer ve çizer. İki motorda ortak:
// Remotion src/lib/yapim/KilavuzKok.tsx (girdi `yapim` verilince), HyperFrames src/lib/yapim/hf.ts (pipeline/hf.py → kılavuz varyantı).
// Saf DOM: saat, rastgelelik, çizim döngüsü yok; aynı DOM aynı kutuları ve aynı SVG'yi verir (kural 8).
// Kipler: "kilavuz" kutuları, güvenli alanı ve üçte bir çizgilerini filmin üstüne çizer; "veri" kareyi siyaha boyar ve kutuları piksellere
// yazar (her değer 24 bit, bir piksel): pipeline/yapim.py bunları okuyup hareket yolunu (kamera yolu) ve en küçük yazıyı çıkarır.

export type KutuTur = 'yazi' | 'gorsel' | 'video' | 'cizim' | 'uc';
export type Kutu = {x: number; y: number; w: number; h: number; tur: KutuTur; boyut: number; opak: number; kimlik: number; metin: string};
export type Guvenli = {ust: number; alt: number; sol: number; sag: number};

const TURLER: KutuTur[] = ['yazi', 'gorsel', 'video', 'cizim', 'uc'];

const ozet24 = (s: string): number => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) & 0xffffff;
};

type Dikdortgen = {left: number; top: number; right: number; bottom: number};

const birlesim = (rs: Dikdortgen[]): Dikdortgen | null => {
  const g = rs.filter((r) => r.right - r.left > 0 && r.bottom - r.top > 0);
  if (!g.length) return null;
  return {left: Math.min(...g.map((r) => r.left)), top: Math.min(...g.map((r) => r.top)), right: Math.max(...g.map((r) => r.right)),
    bottom: Math.max(...g.map((r) => r.bottom))};
};

/** Kökün altındaki görünür yazı, görsel, video, çizim (en dış svg) ve 3B tuvalinin kutuları (bileşim pikseli; kökün sol üstüne göre).
 *  Görünmeyenler (saydamlık < 0,05, gizli, sıfır boyut, kare dışı, taşmayı kesen atanın dışında) ve kareyi kaplayan zeminler atlanır.
 *  Hareket bulanıklığının kopyaları (Bitis) aynı öğenin üst üste kutuları olarak gelir: aynı içerik ve yakın konum tek kutu olur. */
export const olc = (kok: Element, W: number, H: number, haric?: Element | null): Kutu[] => {
  const r0 = kok.getBoundingClientRect();
  const k = r0.width > 0 ? W / r0.width : 1;
  const opak = new Map<Element, number>();
  const opaklik = (el: Element | null): number => {
    if (!el || el === kok) return 1;
    const o = opak.get(el);
    if (o !== undefined) return o;
    const v = (parseFloat(getComputedStyle(el).opacity) || 0) * opaklik(el.parentElement);
    opak.set(el, v);
    return v;
  };
  const kirp = (el: Element, r: Dikdortgen): Dikdortgen | null => {
    let s = {...r};
    for (let p = el.parentElement; p && p !== kok; p = p.parentElement) {
      const st = getComputedStyle(p);
      if (st.overflowX !== 'visible' || st.overflowY !== 'visible') {
        const q = p.getBoundingClientRect();
        s = {left: Math.max(s.left, q.left), top: Math.max(s.top, q.top), right: Math.min(s.right, q.right), bottom: Math.min(s.bottom, q.bottom)};
        if (s.right <= s.left || s.bottom <= s.top) return null;
      }
    }
    return s;
  };
  const ham: (Kutu & {anahtar: string})[] = [];
  const hepsi = kok.querySelectorAll('*');
  for (let i = 0; i < hepsi.length; i++) {
    const el = hepsi[i];
    if (haric && (el === haric || haric.contains(el))) continue;
    const ad = el.tagName.toLowerCase();
    const svgIci = !!el.parentElement?.closest('svg');
    let tur: KutuTur | null = null;
    let metin = '';
    let r: Dikdortgen | null = null;
    if (ad === 'img' || ad === 'image') tur = 'gorsel';
    else if (ad === 'video') tur = 'video';
    else if (ad === 'canvas') tur = 'uc';
    else if (ad === 'svg' && !svgIci) tur = 'cizim';
    else if (ad === 'text' && svgIci) {
      metin = (el.textContent || '').trim();
      if (metin) tur = 'yazi';
    } else if (!svgIci && ad !== 'svg' && ad !== 'style' && ad !== 'script') {
      const dugumler = Array.from(el.childNodes).filter((n) => n.nodeType === 3 && (n.textContent || '').trim());
      if (dugumler.length) {
        tur = 'yazi';
        metin = dugumler.map((n) => (n.textContent || '').trim()).join(' ');
        const rg = document.createRange();
        r = birlesim(dugumler.map((n) => {
          rg.selectNodeContents(n);
          const b = rg.getBoundingClientRect();
          return {left: b.left, top: b.top, right: b.right, bottom: b.bottom};
        }));
      }
    }
    if (!tur) continue;
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') continue;
    const op = opaklik(el);
    if (op < 0.05) continue;
    if (!r) {
      const b = el.getBoundingClientRect();
      r = {left: b.left, top: b.top, right: b.right, bottom: b.bottom};
    }
    r = kirp(el, r);
    if (!r) continue;
    const x = (r.left - r0.left) * k;
    const y = (r.top - r0.top) * k;
    const w = (r.right - r.left) * k;
    const h = (r.bottom - r.top) * k;
    if (w < 4 || h < 4 || x + w <= 0 || y + h <= 0 || x >= W || y >= H) continue;
    if (tur !== 'yazi' && w * h > 0.85 * W * H) continue;   // kareyi kaplayan zemin (plaka, arka plan görseli)
    let boyut = 0;
    if (tur === 'yazi') {
      const fs = parseFloat(st.fontSize) || 0;
      const ow = (el as HTMLElement).offsetWidth;
      const olcek = ow > 0 ? el.getBoundingClientRect().width / ow : 1;
      boyut = fs * olcek * k;
    }
    const kaynak = tur === 'yazi' ? metin : el.getAttribute('src') || el.getAttribute('href') || el.id || '';
    ham.push({x, y, w, h, tur, boyut, opak: op, kimlik: 0, metin: metin.slice(0, 80), anahtar: `${tur}|${ad}|${kaynak}`});
  }
  // tekilleştir: aynı içerik, merkezleri yakın → en opak kutu
  const gruplar = new Map<string, (Kutu & {anahtar: string})[]>();
  for (const b of ham) {
    const g = gruplar.get(b.anahtar) || [];
    const cx = b.x + b.w / 2;
    const cy = b.y + b.h / 2;
    const es = g.findIndex((a) => Math.abs(a.x + a.w / 2 - cx) < Math.max(24, a.w * 0.12) && Math.abs(a.y + a.h / 2 - cy) < Math.max(24, a.h * 0.12));
    if (es < 0) g.push(b);
    else if (b.opak > g[es].opak) g[es] = b;
    gruplar.set(b.anahtar, g);
  }
  const out: Kutu[] = [];
  for (const [anahtar, g] of gruplar) {
    g.sort((a, b) => a.y - b.y || a.x - b.x);
    g.forEach((b, n) => out.push({x: b.x, y: b.y, w: b.w, h: b.h, tur: b.tur, boyut: b.boyut, opak: b.opak, metin: b.metin, kimlik: ozet24(`${anahtar}#${n}`)}));
  }
  return out.sort((a, b) => a.y - b.y || a.x - b.x);
};

const RENK: Record<KutuTur, string> = {yazi: '#FFD23F', gorsel: '#56E39F', video: '#56E39F', cizim: '#B69CFF', uc: '#7FD8FF'};
const AD: Record<KutuTur, string> = {yazi: 'yazı', gorsel: 'görsel', video: 'video', cizim: 'çizim', uc: '3B'};
export const YAZI_ESIK = 64;   // okunan yazı ≥ 64 px (1080 kısa kenarda; zanaat §4)

const s1 = (n: number) => Math.round(n * 10) / 10;
const kacis = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** Kılavuz çizimi (SVG metni): güvenli alanın dışı karartılmış ve kesik çizgili sınırı, üçte bir çizgileri, her kutunun köşe işaretli
 *  çerçevesi ve küçük etiketi (yazıda punto; 64 px'in altındaki yazı kırmızı). u = kısa kenar / 1080. */
export const kilavuzSvg = (kutular: Kutu[], W: number, H: number, g?: Guvenli | null): string => {
  const u = Math.min(W, H) / 1080;
  const p: string[] = [];
  const font = `font-family="Helvetica Neue, Helvetica, Arial, sans-serif" font-weight="600"`;
  if (g) {
    const sx = g.sol * W;
    const sy = g.ust * H;
    const sw = W - (g.sol + g.sag) * W;
    const sh = H - (g.ust + g.alt) * H;
    p.push(`<path d="M0 0H${W}V${H}H0Z M${s1(sx)} ${s1(sy)}V${s1(sy + sh)}H${s1(sx + sw)}V${s1(sy)}Z" fill="rgba(8,10,14,0.42)" fill-rule="evenodd"/>`);
    p.push(`<rect x="${s1(sx)}" y="${s1(sy)}" width="${s1(sw)}" height="${s1(sh)}" fill="none" stroke="#7FE3FF" stroke-width="${s1(3 * u)}" stroke-dasharray="${s1(18 * u)} ${s1(12 * u)}"/>`);
  }
  for (const f of [1 / 3, 2 / 3]) {
    p.push(`<line x1="${s1(W * f)}" y1="0" x2="${s1(W * f)}" y2="${H}" stroke="rgba(255,255,255,0.28)" stroke-width="${s1(1.5 * u)}"/>`);
    p.push(`<line x1="0" y1="${s1(H * f)}" x2="${W}" y2="${s1(H * f)}" stroke="rgba(255,255,255,0.28)" stroke-width="${s1(1.5 * u)}"/>`);
  }
  const fs = 26 * u;
  // etiket yeri: kutunun üstü, altı, sağ üstü, içi; başka bir kutunun ya da etiketin üstüne düşmeyen ilk yer
  const dolu: Dikdortgen[] = kutular.map((b) => ({left: b.x, top: b.y, right: b.x + b.w, bottom: b.y + b.h}));
  const kesisir = (a: Dikdortgen, b: Dikdortgen) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  const yer = (b: Kutu, ew: number, eh: number): [number, number] => {
    const adaylar: [number, number][] = [[b.x, b.y - eh], [b.x, b.y + b.h], [b.x + b.w - ew, b.y - eh], [b.x + b.w + 4 * u, b.y], [b.x, b.y]];
    for (const [x, y] of adaylar) {
      const r = {left: x, top: y, right: x + ew, bottom: y + eh};
      if (y < 0 || y + eh > H || x < 0 || x + ew > W) continue;
      if (!dolu.some((d) => kesisir(r, d) && !(d.left === b.x && d.top === b.y && d.right === b.x + b.w && d.bottom === b.y + b.h))) {
        dolu.push(r);
        return [x, y];
      }
    }
    return [Math.max(0, Math.min(W - ew, b.x)), Math.max(0, b.y - eh)];
  };
  for (const b of kutular) {
    const kucuk = b.tur === 'yazi' && b.boyut < YAZI_ESIK - 0.5;
    const renk = kucuk ? '#FF5A4E' : RENK[b.tur];
    const c = Math.min(22 * u, b.w / 3, b.h / 3);
    p.push(`<rect x="${s1(b.x)}" y="${s1(b.y)}" width="${s1(b.w)}" height="${s1(b.h)}" fill="${renk}" fill-opacity="0.08" stroke="${renk}" stroke-width="${s1(2.5 * u)}"${b.tur === 'yazi' ? '' : ` stroke-dasharray="${s1(10 * u)} ${s1(7 * u)}"`}/>`);
    const kose = [[b.x, b.y, 1, 1], [b.x + b.w, b.y, -1, 1], [b.x, b.y + b.h, 1, -1], [b.x + b.w, b.y + b.h, -1, -1]]
      .map(([x, y, dx, dy]) => `M${s1(x + dx * c)} ${s1(y)}H${s1(x)}V${s1(y + dy * c)}`).join(' ');
    p.push(`<path d="${kose}" fill="none" stroke="${renk}" stroke-width="${s1(6 * u)}"/>`);
    const etiket = b.tur === 'yazi' ? `${Math.round(b.boyut)} px` : AD[b.tur];
    const ew = (etiket.length * 0.6 + 1.0) * fs;
    const [ex, ey] = yer(b, ew, fs * 1.35);
    p.push(`<rect x="${s1(ex)}" y="${s1(ey)}" width="${s1(ew)}" height="${s1(fs * 1.35)}" fill="${renk}"/>`);
    p.push(`<text x="${s1(ex + fs * 0.5)}" y="${s1(ey + fs * 1.0)}" font-size="${s1(fs)}" ${font} fill="#111316">${kacis(etiket)}</text>`);
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="position:absolute;left:0;top:0">${p.join('')}</svg>`;
};

/** Veri kipi: kare siyah, kutular piksellere (satır satır, soldan sağa): STK imzası, sayı, her kutu için 7 değer
 *  [(x+8192)·4, (y+8192)·4, w·4, h·4, kimlik, tür<<16 | boyut·4, opaklık·1000], sonda toplamın 24 bitlik kalanı. Okuyan: pipeline/yapim.py. */
export const veriDegerleri = (kutular: Kutu[]): number[] => {
  const v: number[] = [0x53544b, kutular.length];
  const sinir = (n: number) => Math.max(0, Math.min(0xffffff, Math.round(n)));
  for (const b of kutular) {
    v.push(sinir((b.x + 8192) * 4), sinir((b.y + 8192) * 4), sinir(b.w * 4), sinir(b.h * 4), b.kimlik & 0xffffff,
      ((TURLER.indexOf(b.tur) & 0xff) << 16) | Math.min(0xffff, Math.round(b.boyut * 4)), sinir(b.opak * 1000));
  }
  v.push(v.reduce((a, b) => (a + b) % 0x1000000, 0));
  return v;
};

export const veriSvg = (kutular: Kutu[], W: number, H: number): string => {
  const v = veriDegerleri(kutular);
  const p = v.map((n, i) => `<rect x="${i % W}" y="${Math.floor(i / W)}" width="1" height="1" fill="rgb(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255})"/>`);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" shape-rendering="crispEdges" `
    + `style="position:absolute;left:0;top:0"><rect width="${W}" height="${H}" fill="#000"/>${p.join('')}</svg>`;
};
