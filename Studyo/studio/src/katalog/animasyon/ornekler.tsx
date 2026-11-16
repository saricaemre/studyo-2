import React from 'react';
import {AbsoluteFill} from 'remotion';
import {GECIS, Pt, YERLES, clamp01, easeInOutSine, kareZamani, lerp, nefes, ptsToPath, rand, smooth, yay, yaylar} from '../../lib/anim';
import {Stil, baslikMetni, yaziStili} from '../../lib/gorunus';

/**
 * Animasyon tiplerinin örnek sahneleri (katalog/animasyon/*.json → "demo"). Her biri 3 sn'lik döngü, 1080×1080, t'nin saf fonksiyonu.
 * Teknik örnektir: hareketin nasıl kurulduğunu gösterir. Filmin dünyası, nesneleri ve metni brief'ten, renk ve yazı görünüşten (S) gelir; örnek kopyalanmaz.
 */
export type Ornek = React.FC<{t: number; S: Stil}>;

const p = (t: number, a: number, d: number, e: (x: number) => number = GECIS) => e(clamp01((t - a) / d));
const FPS = 30;
const acikMi = (h: string) => {
  const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] > 0.5;
};

// 1 · Kinetik tipografi: kelimeler maske çizgisinden tek tek yükselir, sonra satır yeniden dizilir
export const KinetikTipografi: Ornek = ({t, S}) => {
  const kel = ['Bana', 'bir', 'şey', 'olmaz.'];
  const dizil = yay(t - 1.3, 0.45);
  const cik = p(t, 2.55, 0.4, YERLES);
  return (
    <AbsoluteFill style={{background: S.arka, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{position: 'relative', width: 900, height: 600}}>
        {kel.map((k, i) => {
          const gir = p(t, 0.15 + i * 0.12, 0.5, YERLES);
          const x0 = [0, 360, 590, 0][i], y0 = [190, 190, 190, 330][i];
          const x1 = 0, y1 = 40 + i * 140;
          const vurgu = i === 3;
          return (
            <div key={i} style={{position: 'absolute', left: lerp(x0, x1, dizil), top: lerp(y0, y1, dizil), overflow: 'hidden', height: 150}}>
              <div style={{...yaziStili(S, 'baslik'), fontSize: vurgu ? lerp(130, 160, dizil) : 130, lineHeight: 1.1, color: vurgu ? S.vurgu : S.murekkep,
                transform: `translateY(${(1 - gir) * 110 - cik * 110}%)`}}>{baslikMetni(S, k)}</div>
            </div>
          );
        })}
        <div style={{position: 'absolute', left: 0, top: 600 - 10, height: 6, width: 900 * p(t, 1.3, 0.5), background: S.vurgu}} />
      </div>
    </AbsoluteFill>
  );
};

// 2 · Bilgi grafiği: eksen çizilir, sütunlar yaylarla yükselir, sayaç akar, not çizgisi vurguya uzanır
export const BilgiGrafigi: Ornek = ({t, S}) => {
  const V = [0.35, 0.5, 0.42, 0.66, 0.58, 0.95];
  const eksen = p(t, 0, 0.5);
  const sayac = Math.round(2600000 * p(kareZamani(t, FPS), 0.4, 1.4, YERLES)); // sayaç karenin zamanını okur
  const not = p(t, 1.7, 0.5);
  const cik = p(t, 2.6, 0.35);
  return (
    <AbsoluteFill style={{background: S.arka, opacity: 1 - cik}}>
      <div style={{...yaziStili(S, 'aksan'), position: 'absolute', left: 120, top: 110, fontSize: 30, color: S.soluk}}>yıllık · örnek veri</div>
      <div style={{...yaziStili(S, 'baslik'), position: 'absolute', left: 120, top: 160, fontSize: 110, color: S.murekkep, fontVariantNumeric: 'tabular-nums'}}>
        {sayac.toLocaleString('tr-TR')}
      </div>
      <svg width={1080} height={1080} style={{position: 'absolute'}}>
        <line x1={120} y1={900} x2={120 + 840 * eksen} y2={900} stroke={S.murekkep} strokeWidth={4} />
        {V.map((v, i) => {
          const h = 420 * v * yay(t - 0.35 - i * 0.08, 0.4);
          const son = i === V.length - 1;
          return <rect key={i} x={150 + i * 135} y={900 - h} width={90} height={h} fill={son ? S.vurgu : S.soluk} opacity={son ? 1 : 0.6} />;
        })}
        <path d={`M ${855 + 45} ${900 - 420 * 0.95 - 20} L ${900} ${330}`} stroke={S.vurgu} strokeWidth={3} strokeDasharray={`${200 * not} 400`} fill="none" />
      </svg>
      <div style={{...yaziStili(S, 'govde'), position: 'absolute', left: 620, top: 290, fontSize: 32, color: S.murekkep, opacity: not}}>en yüksek değer</div>
    </AbsoluteFill>
  );
};

// 3 · Harita dalışı: kamera logaritmik uzayda bir noktaya dalar, rota çizilir, iğne düşer
const KIYI: Pt[][] = [0, 1, 2].map((k) => {
  const c: Pt = [[300, 380], [720, 640], [480, 820]][k] as Pt;
  const r = [220, 260, 140][k];
  const pts: Pt[] = Array.from({length: 14}, (_, i) => {
    const a = (i / 14) * Math.PI * 2;
    const rr = r * (0.7 + 0.5 * rand(k * 50 + i));
    return [c[0] + Math.cos(a) * rr, c[1] + Math.sin(a) * rr * 0.8];
  });
  return smooth([...pts, pts[0]], 6, 0, k);
});
export const HaritaDalisi: Ornek = ({t, S}) => {
  const hedef: Pt = [700, 600];
  const s = Math.exp(lerp(Math.log(1), Math.log(3.2), p(t, 0.3, 1.6, GECIS)) * (1 - p(t, 2.5, 0.5)));
  const rota = p(t, 1.4, 0.9);
  const igne = yay(t - 2.0, 0.3);
  const kagit = S.kagit;
  return (
    <AbsoluteFill style={{background: S.arka}}>
      <svg width={1080} height={1080}>
        <g transform={`translate(540 540) scale(${s}) translate(${-lerp(540, hedef[0], 1 - 1 / s)} ${-lerp(540, hedef[1], 1 - 1 / s)})`}>
          <rect x={-200} y={-200} width={1480} height={1480} fill={kagit} />
          {KIYI.map((k, i) => <path key={i} d={ptsToPath(k, true)} fill={S.soluk} opacity={0.35} stroke={S.murekkep} strokeWidth={2 / s} />)}
          <path d="M 260 360 C 420 300, 560 520, 700 600" fill="none" stroke={S.vurgu} strokeWidth={6 / s} strokeDasharray={`${560 * rota} 600`} strokeLinecap="round" />
          <circle cx={700} cy={600 - 30 * (1 - igne)} r={14 / s} fill={S.vurgu} opacity={igne} />
        </g>
      </svg>
      <div style={{...yaziStili(S, 'baslik'), position: 'absolute', left: 90, top: 90, fontSize: 64, color: S.murekkep}}>{baslikMetni(S, 'Rota')}</div>
    </AbsoluteFill>
  );
};

// 4 · Kâğıt kesik / kolaj: yırtık kenarlı parçalar "ikilerde" (12 fps) düşer, gölge bırakır, hafif sallanır
const yirtik = (w: number, h: number, seed: number) => {
  const pts: Pt[] = [];
  for (let i = 0; i <= 10; i++) pts.push([(w * i) / 10, (rand(seed + i) - 0.5) * 14]);
  for (let i = 0; i <= 8; i++) pts.push([w + (rand(seed + 20 + i) - 0.5) * 14, (h * i) / 8]);
  for (let i = 10; i >= 0; i--) pts.push([(w * i) / 10, h + (rand(seed + 40 + i) - 0.5) * 14]);
  for (let i = 8; i >= 0; i--) pts.push([(rand(seed + 60 + i) - 0.5) * 14, (h * i) / 8]);
  return ptsToPath(pts, true);
};
export const KagitKolaj: Ornek = ({t, S}) => {
  const tq = Math.floor(t * 12) / 12; // ikilerde: stop-motion hissi
  const P = [
    {x: 160, y: 200, w: 520, h: 360, r: -4, at: 0.1, c: S.kagit === S.arka ? S.soluk : S.kagit},
    {x: 430, y: 430, w: 460, h: 300, r: 3, at: 0.45, c: S.vurgu},
    {x: 240, y: 640, w: 520, h: 200, r: -2, at: 0.8, c: S.murekkep},
  ];
  return (
    <AbsoluteFill style={{background: S.arka}}>
      <svg width={1080} height={1080}>
        {P.map((q, i) => {
          const k = yay(tq - q.at, 0.35);
          const sal = Math.sin(tq * 2.2 + i) * 1.2 * k;
          return (
            <g key={i} transform={`translate(${q.x} ${q.y - (1 - k) * 700}) rotate(${q.r + sal} ${q.w / 2} ${q.h / 2})`}>
              <path d={yirtik(q.w, q.h, i * 100)} fill="rgba(0,0,0,0.28)" transform="translate(12 16)" />
              <path d={yirtik(q.w, q.h, i * 100)} fill={q.c} />
            </g>
          );
        })}
      </svg>
      <div style={{...yaziStili(S, 'aksan'), position: 'absolute', left: 300, top: 690, fontSize: 64, color: S.arka, opacity: tq > 1.3 ? 1 : 0,
        transform: `rotate(-2deg)`}}>kes, yapıştır</div>
    </AbsoluteFill>
  );
};

// 5 · Tek nesne dönüşümü: tek biçim hiç kesilmeden daire → hap → kart → çubuk → daireye döner (yay toplamı)
export const TekNesne: Ornek = ({t, S}) => {
  const A: [number, number][] = [[0.3, 1], [0.9, 2], [1.5, 3], [2.2, 0]];
  const durum = [
    {w: 220, h: 220, r: 110},
    {w: 520, h: 140, r: 70},
    {w: 620, h: 420, r: 28},
    {w: 760, h: 60, r: 8},
  ];
  const al = (k: 'w' | 'h' | 'r') => yaylar(t, durum[0][k], A.map(([a, i]) => [a, durum[i][k]] as [number, number]), 0.42);
  const w = al('w'), h = al('h'), r = al('r');
  const icerik = t > 1.65 && t < 2.15 ? 1 - Math.abs((t - 1.9) / 0.25) : 0;
  return (
    <AbsoluteFill style={{background: S.arka, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{width: w, height: h, borderRadius: r, background: S.vurgu, display: 'flex', alignItems: 'center', justifyContent: 'center',
        transform: `scale(${nefes(t, 0, 3, 0.012)})`}}>
        <div style={{...yaziStili(S, 'baslik'), fontSize: 72, color: S.arka, opacity: clamp01(icerik * 2)}}>{baslikMetni(S, 'tek biçim')}</div>
      </div>
    </AbsoluteFill>
  );
};

// 6 · Arayüz / ürün demosu: imleç gelir, kutuya tıklar (dalga), yazı harf harf yazılır, sonuçlar kayar
export const ArayuzDemo: Ornek = ({t, S}) => {
  const imlec = p(t, 0.1, 0.7);
  const ix = lerp(860, 330, imlec), iy = lerp(900, 330, imlec);
  const tik = clamp01((t - 0.85) / 0.4);
  const metin = 'kahve tarihi';
  const n = Math.floor(metin.length * clamp01((kareZamani(t, FPS) - 1.0) / 0.8)); // yazılan harf karenin zamanını okur
  const sonuc = (i: number) => yay(t - 1.9 - i * 0.1, 0.35);
  const kart = S.kagit === S.arka ? '#FFFFFF' : S.kagit;
  return (
    <AbsoluteFill style={{background: S.arka}}>
      <div style={{position: 'absolute', left: 140, top: 270, width: 800, height: 120, borderRadius: 24, background: kart, border: `3px solid ${t > 0.85 ? S.vurgu : S.soluk}`,
        display: 'flex', alignItems: 'center', paddingLeft: 40, boxSizing: 'border-box'}}>
        <span style={{...yaziStili(S, 'govde'), fontSize: 46, color: S.murekkep}}>{metin.slice(0, n)}</span>
        <span style={{width: 4, height: 56, marginLeft: 4, background: S.vurgu, opacity: n < metin.length || Math.floor(t * 2) % 2 === 0 ? 1 : 0}} />
      </div>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{position: 'absolute', left: 140, top: 440 + i * 130, width: 800, height: 110, borderRadius: 18, background: kart,
          opacity: sonuc(i), transform: `translateY(${(1 - sonuc(i)) * 40}px)`, display: 'flex', alignItems: 'center', paddingLeft: 40, boxSizing: 'border-box'}}>
          <div style={{width: 60, height: 60, borderRadius: 12, background: i === 0 ? S.vurgu : S.soluk, opacity: i === 0 ? 1 : 0.5}} />
          <div style={{...yaziStili(S, 'govde'), fontSize: 36, marginLeft: 30, color: S.murekkep}}>{['Kahvenin yolculuğu', 'Yemen limanları', 'Osmanlı kahvehaneleri'][i]}</div>
        </div>
      ))}
      <div style={{position: 'absolute', left: ix - 60 * tik, top: iy - 60 * tik, width: 120 * tik, height: 120 * tik, borderRadius: '50%',
        border: `4px solid ${S.vurgu}`, opacity: tik > 0 ? 1 - tik : 0}} />
      <svg width={60} height={60} style={{position: 'absolute', left: ix, top: iy}}>
        <path d="M2 2 L2 44 L14 32 L24 54 L32 50 L22 29 L38 29 Z" fill={S.murekkep} stroke={S.arka} strokeWidth={3} />
      </svg>
    </AbsoluteFill>
  );
};

// 7 · Kendini çizen çizim: tek çizgi ampulü çizer, dolgu gelir, el yazısı not altını çizer
export const Cizim: Ornek = ({t, S}) => {
  const d = 'M540 250 C 400 250, 330 360, 360 470 C 380 540, 450 580, 460 660 L 620 660 C 630 580, 700 540, 720 470 C 750 360, 680 250, 540 250 Z';
  const ciz = p(t, 0.1, 1.3, easeInOutSine);
  const dolgu = p(t, 1.3, 0.5);
  const alt = p(t, 1.9, 0.5);
  return (
    <AbsoluteFill style={{background: S.arka}}>
      <svg width={1080} height={1080}>
        <path d={d} fill={S.vurgu} opacity={0.85 * dolgu} />
        <path d={d} fill="none" stroke={S.murekkep} strokeWidth={10} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${1500 * ciz} 1600`} opacity={ciz > 0 ? 1 : 0} />
        {[0, 1, 2].map((i) => (
          <line key={i} x1={470} x2={610} y1={700 + i * 34} y2={700 + i * 34} stroke={S.murekkep} strokeWidth={10} strokeLinecap="round"
            strokeDasharray={`${140 * p(t, 1.0 + i * 0.12, 0.3)} 200`} opacity={p(t, 1.0 + i * 0.12, 0.3) > 0 ? 1 : 0} />
        ))}
        <path d="M330 900 C 450 880, 650 890, 760 870" fill="none" stroke={S.vurgu} strokeWidth={8} strokeLinecap="round" strokeDasharray={`${450 * alt} 500`} opacity={alt > 0 ? 1 : 0} />
      </svg>
      <div style={{...yaziStili(S, 'aksan'), position: 'absolute', left: 340, top: 800, fontSize: 70, color: S.murekkep, opacity: alt}}>bir fikir</div>
    </AbsoluteFill>
  );
};

// 8 · Sonsuz yakınlaşma: iç içe çerçeveler; logaritmik ölçek kusursuz döngü yapar (3 sn = bir kat)
export const SonsuzYakinlasma: Ornek = ({t, S}) => {
  const K = 3;
  const u = (t / 3) % 1;
  const ad = ['dünya', 'ülke', 'şehir', 'sokak', 'ev', 'oda', 'masa'];
  const katlar = [-2, -1, 0, 1, 2, 3, 4];
  return (
    <AbsoluteFill style={{background: S.arka, overflow: 'hidden'}}>
      {katlar.map((k) => {
        const s = Math.pow(K, u - k + 1);
        if (s < 0.04 || s > 12) return null;
        const boy = 1000 * s;
        const etiket = clamp01((s - 0.25) / 0.2) * clamp01((2.4 - s) / 0.6);
        const dolu = ((k % 2) + 2) % 2 === 0;
        return (
          <div key={k} style={{position: 'absolute', left: 540 - boy / 2, top: 540 - boy / 2, width: boy, height: boy, boxSizing: 'border-box',
            border: `${Math.max(1.5, 10 * s)}px solid ${dolu ? S.murekkep : S.vurgu}`, background: dolu ? S.arka : S.soluk + '22'}}>
            <div style={{...yaziStili(S, 'baslik'), position: 'absolute', left: 30 * s, top: 22 * s, fontSize: 70 * s, color: dolu ? S.murekkep : S.vurgu,
              whiteSpace: 'nowrap', opacity: etiket}}>{baslikMetni(S, ad[((k + 2) % ad.length + ad.length) % ad.length])}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// 9 · Silüet / gölge tiyatrosu: arkadan ışık, katmanlı silüetler (insansız), ışık süpürür, kuş silüeti geçer
export const SiluetGolge: Ornek = ({t, S}) => {
  const isik = 540 + Math.sin((t / 3) * Math.PI * 2) * 160;
  const kus = -200 + ((t / 3) % 1) * 1500;
  const dag = (y: number, seed: number) => {
    const pts: Pt[] = [[0, 1080]];
    for (let i = 0; i <= 12; i++) pts.push([i * 90, y - rand(seed + i) * 160]);
    pts.push([1080, 1080]);
    return ptsToPath(smooth(pts, 4, 0, seed), true);
  };
  const koyu = acikMi(S.arka) ? S.murekkep : S.arka;
  const isikRengi = acikMi(S.arka) ? S.arka : S.murekkep;
  return (
    <AbsoluteFill style={{background: koyu}}>
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(circle at ${isik}px 470px, ${isikRengi} 0%, ${isikRengi} 12%, ${S.vurgu}66 30%, transparent 62%)`}} />
      <svg width={1080} height={1080} style={{position: 'absolute'}}>
        <path d={dag(760, 10)} fill={koyu} opacity={0.55} transform={`translate(${Math.sin(t) * 6} 0)`} />
        <path d={dag(880, 30)} fill={koyu} opacity={0.8} transform={`translate(${Math.sin(t) * 14} 0)`} />
        <path d={dag(980, 50)} fill={koyu} />
        <path d={`M ${kus} 300 q 30 ${-20 + Math.sin(t * 12) * 18} 60 0 q 30 ${-20 + Math.sin(t * 12) * 18} 60 0`} stroke={koyu} strokeWidth={8} fill="none" />
      </svg>
    </AbsoluteFill>
  );
};

// 10 · Izgara montaj: 3×3 hücre vuruşla dolar, vurgu hücresi yer değiştirir (ortak dönüşüm eğrisi)
export const IzgaraMontaj: Ornek = ({t, S}) => {
  const hucre = 300, bosluk = 20, x0 = (1080 - 3 * hucre - 2 * bosluk) / 2;
  const vurguYer = [4, 0, 8, 4];
  const adim = Math.min(3, Math.floor(t / 0.75));
  const gecis = p(t, adim * 0.75, 0.55);
  const a = vurguYer[adim], b = vurguYer[Math.min(3, adim + 1)];
  const xy = (i: number) => [x0 + (i % 3) * (hucre + bosluk), x0 + Math.floor(i / 3) * (hucre + bosluk)];
  const [ax, ay] = xy(a), [bx, by] = xy(b);
  return (
    <AbsoluteFill style={{background: S.arka}}>
      {Array.from({length: 9}, (_, i) => {
        const [x, y] = xy(i);
        const k = yay(t - 0.05 - i * 0.05, 0.3);
        return <div key={i} style={{position: 'absolute', left: x, top: y, width: hucre, height: hucre, background: S.soluk, opacity: 0.25 * k, transform: `scale(${lerp(0.9, 1, k)})`}} />;
      })}
      <div style={{position: 'absolute', left: lerp(ax, bx, gecis), top: lerp(ay, by, gecis), width: hucre, height: hucre, background: S.vurgu,
        display: 'flex', alignItems: 'flex-end', padding: 24, boxSizing: 'border-box'}}>
        <div style={{...yaziStili(S, 'baslik'), fontSize: 54, color: S.arka}}>{['01', '02', '03', '04'][adim]}</div>
      </div>
      <div style={{...yaziStili(S, 'govde'), position: 'absolute', left: x0, top: 40, fontSize: 30, color: S.murekkep}}>modüler düzen · vuruşla değişir</div>
    </AbsoluteFill>
  );
};

export const ORNEKLER: Record<string, Ornek> = {
  'kinetik-tipografi': KinetikTipografi,
  'bilgi-grafigi': BilgiGrafigi,
  'harita-dalisi': HaritaDalisi,
  'kagit-kolaj': KagitKolaj,
  'tek-nesne': TekNesne,
  'arayuz-demo': ArayuzDemo,
  cizim: Cizim,
  'sonsuz-yakinlasma': SonsuzYakinlasma,
  'siluet-golge': SiluetGolge,
  'izgara-montaj': IzgaraMontaj,
};
