import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {degiskenFontYukle} from '../lib/fontlar';

/**
 * Yapım filmi ("nasıl yapıldı", ./st yapim; pipeline/yapim.py): 15 sn, girdi `kurgu` (out/_yapim/<id>/kurgu.json). Her bölüm filmin kendi
 * kayıtlarından gelir: üç yol / görünüş ve seçilen, kılavuz kipinde kareler (yerleşim kutuları, güvenli alan, hareket yolu), Blender'ın kil,
 * tel kafes ve kamera yolu geçişleri, inceleme turunda önce/sonra, yapay zekâ varlığının kaynağı, altı kapı, film. Görseller
 * public/_yapim → out/_yapim bağlantısından (dondurulmuş JPEG). Yazı Roboto Flex, ≥ 64 px (1080 kısa kenarda), plakanın üstünde, formatın
 * güvenli alanında. Kare t'nin saf fonksiyonudur: saat, rastgelelik, CSS geçişi yok (kural 8).
 */
type Yazi = {metin: string; rol: 'baslik' | 'ust' | 'alt' | 'not'; bas: number; bit: number};
type Iz = {kimlik: number; tur: string; noktalar: ([number, number] | null)[]};
type Kapi = {n: number; ad: string; insan: boolean; onay: string | null; tarih: string | null; durum: 'insan' | 'kanit' | 'bekliyor'};
type Bolum = {
  tur: 'acilis' | 'yollar' | 'kilavuz' | 'blender' | 'elestiri' | 'uretim' | 'kapilar' | 'kapanis';
  bas: number;
  kare: number;
  yazilar?: Yazi[];
  arka?: string;
  iskelet?: string;   // açılış: filmin karesinin iskeleti (kılavuz ya da kil); film o anın kendisi
  secenekler?: {harf: string; ad: string; kare: string}[];
  secim?: string | null;
  kart?: [number, number];   // kartın ekrandaki boyutu (px); görsel Python'da tam bu boyuta küçültülmüş gelir
  film?: string[] | string;
  kilavuz?: string[];
  izler?: Iz[];
  adim?: number;
  gecisler?: {kil: string[]; tel: string[]; ust: string[]; son: string[]};
  once?: string;
  sonra?: string;
  etiket1?: string;
  etiket2?: string;
  varlik?: string;
  varlik_boyut?: [number, number];   // ekrandaki boyutu (px); görsel Python'da bu boyutta
  kapilar?: Kapi[];
  kareler?: string[];
  konum?: 'ust' | 'alt';   // yazıların yeri: filmin kendi yazısının olmadığı yarı (pipeline/yapim.py → kılavuz verisi)
};
export type Kurgu = {
  video: string; format: string; w: number; h: number; fps: number; kare: number;
  guvenli: {ust: number; alt: number; sol: number; sag: number}; vurgu: string; baslik: string; bolumler: Bolum[];
};

export const ZEMIN = '#0E1014';
export const YAZI = '#F4F1EA';
export const PLAKA = '#15171C';                 // opak: arkadaki filmin yazısı sızmaz; yazı ≥ 13:1 (pipeline/yapim.py → olc)
const GECIS = 8;                              // bölüm geçişi (kare): yeni bölüm alttan açılır, eskisi altında durur

type Cevre = {W: number; H: number; u: number; S: {x0: number; y0: number; x1: number; y1: number}; dikey: boolean; aile: string; vurgu: string};

const kolay = (f: number, a: number, b: number) => interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.2, 0.7, 0.2, 1)});
const kaynak = (p?: string) => (p ? staticFile(p) : '');
const sira = (liste: string[] | undefined, f: number, adim = 2) => (liste && liste.length ? liste[Math.min(liste.length - 1, Math.max(0, Math.floor(f / adim)))] : undefined);

const Tam: React.FC<{src?: string; style?: React.CSSProperties}> = ({src, style}) =>
  src ? <Img src={kaynak(src)} style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', objectFit: 'cover', ...style}} /> : null;

const BOY = {baslik: 112, ust: 84, alt: 72, not: 64};
const AGIRLIK = {baslik: 820, ust: 760, alt: 600, not: 560};

/** Tek yazı plakası: rolüne göre punto (≥ 64 px), girişte kısa bir yükseliş; görünmeden önce de yeri ayrılmıştır. */
const Plaka: React.FC<{c: Cevre; f: number; y: Yazi; orta?: boolean}> = ({c, f, y, orta}) => {
  const {u} = c;
  const p = kolay(f, y.bas, y.bas + 7);
  const gor = f >= y.bas && f < y.bit;
  return (
    <div lang="tr" style={{opacity: gor ? p : 0, transform: `translateY(${(1 - p) * 26 * u}px)`, background: PLAKA, color: YAZI,
      fontFamily: `'${c.aile}', sans-serif`, fontSize: BOY[y.rol] * u, fontVariationSettings: `'wght' ${AGIRLIK[y.rol]}, 'wdth' ${y.rol === 'baslik' ? 92 : 100}`,
      lineHeight: 1.08, padding: `${0.16 * BOY[y.rol] * u}px ${0.3 * BOY[y.rol] * u}px`, borderRadius: 14 * u, textAlign: orta ? 'center' : 'left',
      borderLeft: y.rol === 'not' ? `${8 * u}px solid ${c.vurgu}` : undefined, maxWidth: '100%', textWrap: 'balance', whiteSpace: 'pre-line', flex: 'none'} as React.CSSProperties}>
      {y.metin}
    </div>
  );
};

/** Bölümün yazıları: güvenli alanın altında (başlık ortada, istenirse üstte) bir sütun; sonradan gelen yazı ötekileri kaydırmaz. */
const Yazilar: React.FC<{c: Cevre; f: number; yazilar: Yazi[]; orta?: boolean; ust?: boolean}> = ({c, f, yazilar, orta, ust}) => {
  const {u, S} = c;
  return (
    <div style={{position: 'absolute', left: S.x0 + 48 * u, width: S.x1 - S.x0 - 96 * u, top: S.y0 + 40 * u, bottom: c.H - S.y1 + 48 * u,
      display: 'flex', flexDirection: 'column', justifyContent: orta ? 'center' : ust ? 'flex-start' : 'flex-end', alignItems: orta ? 'center' : 'flex-start',
      gap: 18 * u}}>
      {yazilar.map((y, i) => <Plaka key={i} c={c} f={f} y={y} orta={orta} />)}
    </div>
  );
};

const Acilis: React.FC<{c: Cevre; b: Bolum; f: number}> = ({c, b, f}) => {
  // Kanca: filmin bir anı, sürgü ilk saniyede aynı anın iskeletini açar (kılavuz ya da kil); başlık 0. karede
  const film = typeof b.film === 'string' ? b.film : b.arka;
  const p = b.iskelet ? interpolate(f, [3, b.kare * 0.8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.45, 0, 0.25, 1)}) : 0;
  return (
    <AbsoluteFill style={{background: ZEMIN}}>
      <Silme c={c} p={p} once={<Tam src={film} />} sonra={<Tam src={b.iskelet} />} />
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(14,16,20,0.35), rgba(14,16,20,0) 30%, rgba(14,16,20,0) 70%, rgba(14,16,20,0.35))'}} />
      <Yazilar c={c} f={f} yazilar={b.yazilar || []} orta />
    </AbsoluteFill>
  );
};

const Yollar: React.FC<{c: Cevre; b: Bolum; f: number}> = ({c, b, f}) => {
  const {u, S} = c;
  const sec = b.secenekler || [];
  const gap = 22 * u;
  const alan = (S.y1 - S.y0) - 400 * u;           // altta üç yazının yeri
  // Kart boyutu pipeline/yapim.py → _kart ile aynı; görsel o boyutta gelir ve ölçeklenmez (tarayıcının küçültme süzgeci çizim sırasına bağlı)
  const [en2, boy] = b.kart || [Math.round((S.x1 - S.x0 - 2 * gap - 24 * u) / 3), Math.round(((S.x1 - S.x0 - 2 * gap - 24 * u) / 3) * c.H / c.W)];
  const vurgu = kolay(f, b.kare * 0.42, b.kare * 0.42 + 10);
  const ayril = b.secim ? kolay(f, b.kare * 0.5, b.kare * 0.78) : 0;   // seçim: seçilen ortaya gelir, ötekiler kenara çekilip söner
  const ust_ust = c.H / c.W > 1.5;   // dikey: büyük kartlar üst üste biner (karenin ortasında; kart görseldir, harfi güvenli alanda kalır)
  const adim = ust_ust ? Math.round(0.29 * c.W) : en2 + gap;
  const sol0 = ust_ust ? Math.round(c.W / 2 - adim - en2 / 2) : Math.round((S.x0 + S.x1) / 2 - (3 * en2 + 2 * gap) / 2);
  const ust0 = S.y0 + (alan - boy) / 2 + 20 * u;
  const si = sec.findIndex((s) => s.harf === b.secim);
  const orta = Math.round(c.W / 2 - en2 / 2);
  return (
    <AbsoluteFill style={{background: ZEMIN}}>
      {sec.map((s, i) => {
        const gir = kolay(f, i * 4, i * 4 + 10);
        const secili = b.secim === s.harf;
        const x0 = sol0 + Math.round(i * adim);
        // konum tam piksel (görsel ölçeklenmez, kaydırma alt piksele düşmez): deterministik
        const x = secili ? Math.round(x0 + (orta - x0) * ayril) : Math.round(x0 + Math.sign(i - si) * 0.22 * c.W * ayril);
        const rozet: React.CSSProperties = ust_ust && i === 2 ? {right: 12 * u} : ust_ust && i === 1 ? {left: en2 / 2 - 36 * u} : {left: 12 * u};
        return (
          <div key={s.harf} style={{position: 'absolute', left: x, top: Math.round(ust0 + (1 - gir) * 60 * u), width: en2, height: boy,
            zIndex: secili && vurgu > 0 ? 3 : i === 1 ? 2 : 1, opacity: gir * (secili || !b.secim ? 1 : (1 - 0.62 * vurgu) * (1 - 0.75 * ayril)),
            borderRadius: 18 * u, overflow: 'hidden', boxShadow: secili ? `0 0 0 ${8 * u * vurgu}px ${c.vurgu}` : 'none'}}>
            <Img src={kaynak(s.kare)} style={{display: 'block', width: en2, height: boy}} />
            <div style={{position: 'absolute', ...rozet, top: 12 * u, background: PLAKA, color: YAZI, fontFamily: `'${c.aile}', sans-serif`,
              fontSize: 72 * u, fontVariationSettings: "'wght' 820", lineHeight: 1, padding: `${10 * u}px ${18 * u}px`, borderRadius: 12 * u}}>{s.harf.toUpperCase()}</div>
          </div>
        );
      })}
      <Yazilar c={c} f={f} yazilar={b.yazilar || []} />
    </AbsoluteFill>
  );
};

/** Kutuların hareket yolu (kılavuzun veri kipinden): her kutunun merkezi, son ~1 sn, uçta nokta. Film pikseli = yapım pikseli (aynı format). */
const Izler: React.FC<{c: Cevre; izler: Iz[]; i: number; opak: number}> = ({c, izler, i, opak}) => (
  <svg width={c.W} height={c.H} style={{position: 'absolute', left: 0, top: 0, opacity: opak}}>
    {izler.map((z) => {
      // iz yalnız kesintisiz parçalarla (null: kopuk), son ~1 sn
      const parca: [number, number][][] = [[]];
      for (const q of z.noktalar.slice(Math.max(0, i - 15), i + 1)) {
        if (q) parca[parca.length - 1].push(q);
        else if (parca[parca.length - 1].length) parca.push([]);
      }
      const son = z.noktalar[i];
      return (
        <g key={z.kimlik}>
          {parca.filter((p) => p.length > 1).map((p, k) => (
            <polyline key={k} points={p.map((q) => `${q[0]},${q[1]}`).join(' ')} fill="none" stroke={c.vurgu} strokeWidth={6 * c.u} strokeLinecap="round" strokeLinejoin="round" />
          ))}
          {son && <circle cx={son[0]} cy={son[1]} r={11 * c.u} fill={c.vurgu} stroke={ZEMIN} strokeWidth={3 * c.u} />}
        </g>
      );
    })}
  </svg>
);

const Silme: React.FC<{c: Cevre; p: number; once: React.ReactNode; sonra: React.ReactNode; yon?: 'sag' | 'sol'}> = ({c, p, once, sonra, yon = 'sag'}) => {
  const x = yon === 'sag' ? p * c.W : (1 - p) * c.W;
  return (
    <AbsoluteFill>
      {once}
      <AbsoluteFill style={{clipPath: yon === 'sag' ? `inset(0 ${c.W - x}px 0 0)` : `inset(0 0 0 ${x}px)`}}>{sonra}</AbsoluteFill>
      {p > 0 && p < 1 && <div style={{position: 'absolute', left: x - 4 * c.u, top: 0, width: 8 * c.u, height: c.H, background: c.vurgu}} />}
    </AbsoluteFill>
  );
};

const Kilavuz: React.FC<{c: Cevre; b: Bolum; f: number}> = ({c, b, f}) => {
  const adim = b.adim || 2;
  const i = Math.floor(f / adim);
  const film = Array.isArray(b.film) ? b.film : [];
  const p = kolay(f, b.kare * 0.55, b.kare * 0.64);
  return (
    <AbsoluteFill style={{background: ZEMIN}}>
      <Silme c={c} p={p}
        once={<><Tam src={sira(b.kilavuz, f, adim)} /><Izler c={c} izler={b.izler || []} i={i} opak={1 - p} /></>}
        sonra={<Tam src={sira(film, f, adim)} />} />
      <Yazilar c={c} f={f} yazilar={b.yazilar || []} ust={b.konum === 'ust'} />
    </AbsoluteFill>
  );
};

const Blender: React.FC<{c: Cevre; b: Bolum; f: number}> = ({c, b, f}) => {
  const adim = b.adim || 2;
  const g = b.gecisler || {kil: [], tel: [], ust: [], son: []};
  const q = b.kare / 4;
  const asama = [g.kil, g.tel, g.ust, g.son];
  const k = Math.min(3, Math.floor(f / q));
  const p = k > 0 ? kolay(f, k * q, k * q + 9) : 1;
  return (
    <AbsoluteFill style={{background: ZEMIN}}>
      <Silme c={c} p={p} once={<Tam src={sira(asama[Math.max(0, k - 1)], f, adim)} />} sonra={<Tam src={sira(asama[k], f, adim)} />} />
      <Yazilar c={c} f={f} yazilar={b.yazilar || []} ust />
    </AbsoluteFill>
  );
};

const Elestiri: React.FC<{c: Cevre; b: Bolum; f: number}> = ({c, b, f}) => {
  const {u, S} = c;
  const p = interpolate(f, [b.kare * 0.18, b.kare * 0.55], [0, 0.5], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.3, 0, 0.2, 1)});
  const etiket = (metin: string, sag: boolean) => (
    <div style={{position: 'absolute', top: b.konum === 'ust' ? (S.y0 + S.y1) / 2 - 40 * u : S.y0 + 40 * u,
      [sag ? 'right' : 'left']: (sag ? c.W - S.x1 : S.x0) + 40 * u, background: PLAKA, color: YAZI,
      fontFamily: `'${c.aile}', sans-serif`, fontSize: 64 * u, fontVariationSettings: "'wght' 700", padding: `${10 * u}px ${20 * u}px`, borderRadius: 12 * u,
      opacity: kolay(f, sag ? b.kare * 0.4 : 4, sag ? b.kare * 0.4 + 8 : 12)}}>{metin}</div>
  );
  return (
    <AbsoluteFill style={{background: ZEMIN}}>
      <Silme c={c} p={p} yon="sol" once={<Tam src={b.once} />} sonra={<Tam src={b.sonra} />} />
      {p >= 0.5 && <div style={{position: 'absolute', left: c.W / 2 - 4 * u, top: 0, width: 8 * u, height: c.H, background: c.vurgu}} />}
      {etiket(b.etiket1 || '', false)}
      {etiket(b.etiket2 || '', true)}
      <Yazilar c={c} f={f} yazilar={b.yazilar || []} ust={b.konum === 'ust'} />
    </AbsoluteFill>
  );
};

const Uretim: React.FC<{c: Cevre; b: Bolum; f: number}> = ({c, b, f}) => {
  const {u, S} = c;
  const gir = kolay(f, 0, 14);
  const alanH = (S.y1 - S.y0) * (c.dikey ? 0.5 : 0.62);
  return (
    <AbsoluteFill style={{background: ZEMIN}}>
      <Tam src={typeof b.film === 'string' ? b.film : undefined} style={{opacity: 0.28, transform: `scale(${1.04 - 0.04 * kolay(f, 0, b.kare)})`}} />
      <div style={{position: 'absolute', left: S.x0 + 48 * u, right: c.W - S.x1 + 48 * u, top: Math.round(S.y0 + 70 * u + (1 - gir) * 80 * u), height: alanH,
        opacity: gir, display: 'flex', justifyContent: c.dikey ? 'center' : 'flex-start'}}>
        <Img src={kaynak(b.varlik)} style={b.varlik_boyut ? {width: b.varlik_boyut[0], height: b.varlik_boyut[1], borderRadius: 18 * u, boxShadow: `0 0 0 ${6 * u}px ${c.vurgu}`}
          : {height: '100%', maxWidth: '100%', objectFit: 'contain', borderRadius: 18 * u, boxShadow: `0 0 0 ${6 * u}px ${c.vurgu}`}} />
      </div>
      <Yazilar c={c} f={f} yazilar={b.yazilar || []} />
    </AbsoluteFill>
  );
};

const Kapilar: React.FC<{c: Cevre; b: Bolum; f: number}> = ({c, b, f}) => {
  const {u, S} = c;
  const K = b.kapilar || [];
  const sutun = c.dikey && c.H / c.W > 1.5 ? 1 : 2;
  const durum = (k: Kapi) => (k.durum === 'insan' ? `insan onayı · ${k.tarih}` : k.durum === 'kanit' ? 'ölçümle geçti' : k.insan ? 'insan onayı bekliyor' : 'ölçüm bekliyor');
  const insanlar = K.filter((k) => k.insan).map((k) => k.n);
  const t0 = 6 + K.length * 4 + 6;   // satırlar geldikten sonra insan kapıları sırayla öne çıkar
  return (
    <AbsoluteFill style={{background: ZEMIN}}>
      <div style={{position: 'absolute', left: S.x0 + 48 * u, right: c.W - S.x1 + 48 * u, top: S.y0 + 28 * u, bottom: c.H - S.y1 + 28 * u,
        display: 'flex', flexDirection: 'column', gap: 24 * u}}>
      {(b.yazilar || []).map((y, i) => <Plaka key={i} c={c} f={f} y={y} />)}
      <div style={{display: 'grid', gridTemplateColumns: `repeat(${sutun}, 1fr)`, gap: `${10 * u}px ${28 * u}px`, alignContent: 'start'}}>
        {K.map((k, i) => {
          const gir = kolay(f, 6 + i * 4, 16 + i * 4);
          const j = insanlar.indexOf(k.n);
          const one = j < 0 ? 0 : Math.max(0, 1 - Math.abs(f - (t0 + j * 9 + 6)) / 7) + (f > t0 + insanlar.length * 9 + 4 ? 0.6 : 0);
          const renk = k.insan ? c.vurgu : k.durum === 'kanit' ? '#56E39F' : '#6B7280';   // insan kapıları her zaman vurgu renginde
          const bos = k.insan && k.durum !== 'insan';   // insan kapısı bekliyor: halka (dolu değil)
          return (
            <div key={k.n} style={{display: 'flex', gap: 22 * u, alignItems: 'center', opacity: gir, transform: `translateX(${Math.round((1 - gir) * 40 * u + Math.min(1, one) * 14 * u)}px)`,
              background: one > 0 ? `color-mix(in srgb, ${c.vurgu} ${Math.round(Math.min(1, one) * 26)}%, rgba(255,255,255,0.05))` : 'rgba(255,255,255,0.05)', borderRadius: 16 * u, padding: `${8 * u}px ${18 * u}px`, borderLeft: `${10 * u}px solid ${renk}`}}>
              <div style={{flex: 'none', width: 88 * u, height: 88 * u, borderRadius: '50%', background: bos ? 'transparent' : renk, color: bos ? renk : ZEMIN,
                boxShadow: bos ? `inset 0 0 0 ${6 * u}px ${renk}` : 'none', display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontFamily: `'${c.aile}', sans-serif`, fontSize: 64 * u, fontVariationSettings: "'wght' 860"}}>{k.n}</div>
              <div lang="tr" style={{color: YAZI, fontFamily: `'${c.aile}', sans-serif`, lineHeight: 1.0}}>
                <div style={{fontSize: 64 * u, fontVariationSettings: "'wght' 720, 'wdth' 88"}}>{k.ad}</div>
                <div style={{fontSize: 64 * u, fontVariationSettings: "'wght' 480, 'wdth' 88", opacity: 0.86}}>{durum(k)}</div>
              </div>
            </div>
          );
        })}
      </div>
      </div>
    </AbsoluteFill>
  );
};

const Kapanis: React.FC<{c: Cevre; b: Bolum; f: number}> = ({c, b, f}) => (
  <AbsoluteFill style={{background: ZEMIN}}>
    <Tam src={sira(b.kareler, f, b.adim || 2)} />
    <Yazilar c={c} f={f} yazilar={b.yazilar || []} ust={b.konum === 'ust'} />
  </AbsoluteFill>
);

const BILESEN = {acilis: Acilis, yollar: Yollar, kilavuz: Kilavuz, blender: Blender, elestiri: Elestiri, uretim: Uretim, kapilar: Kapilar, kapanis: Kapanis};

export const Yapim: React.FC<{kurgu?: Kurgu}> = ({kurgu}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const aile = degiskenFontYukle('Roboto Flex');
  if (!kurgu) {
    return (
      <AbsoluteFill style={{background: ZEMIN, color: YAZI, alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif', fontSize: 40}}>
        Yapım filmi: ./st yapim &lt;id&gt; (girdi: kurgu)
      </AbsoluteFill>
    );
  }
  const u = Math.min(width, height) / 1080;
  const g = kurgu.guvenli;
  const c: Cevre = {W: width, H: height, u, dikey: height > width, aile, vurgu: kurgu.vurgu,
    S: {x0: g.sol * width, y0: g.ust * height, x1: width - g.sag * width, y1: height - g.alt * height}};
  const i = Math.max(0, kurgu.bolumler.findIndex((b) => frame >= b.bas && frame < b.bas + b.kare));
  const b = kurgu.bolumler[i];
  const B = BILESEN[b.tur];
  const f = frame - b.bas;
  const once = i > 0 && f < GECIS ? kurgu.bolumler[i - 1] : null;
  const O = once ? BILESEN[once.tur] : null;
  const p = once ? kolay(f, 0, GECIS) : 1;
  // key={frame}: her kare sıfırdan kurulur. Aynı öğe kareden kareye yaşarsa Chrome dönüşümü değişen öğeyi sonradan ayrı katmana alıyor ve
  // ölçeklenen görseli başka süzgeçle çiziyor: kare, çizim sırasına bağlı 2/255 ayrışıyordu (deterministik değil).
  return (
    <AbsoluteFill key={frame} style={{background: ZEMIN}}>
      {once && O && <O c={c} b={once} f={once.kare - 1} />}
      <AbsoluteFill style={once ? {clipPath: `inset(${(1 - p) * 100}% 0 0 0)`} : undefined}>
        <B c={c} b={b} f={f} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
