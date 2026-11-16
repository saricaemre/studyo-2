// Niyetli altyazının HyperFrames karşılığı: pipeline/hf.py bunu esbuild ile assets/lib/niyet/niyet.js'e paketler.
// Sahne kodu: import {niyetliAltyazi} from "./assets/lib/niyet/niyet.js"; niyetliAltyazi(document.getElementById("altyazi"));
// Veri window.ST.niyet (yalnız niyetli filmde; formatın yerleşimi dahil), yazı tipi st-gorunus'taki @font-face (assets/fonts/).
// Her arayışta (hf-seek) ve açılışta t anındaki hâl yeniden kurulur: çizim döngüsü, saat, CSS geçişi yok (kural 8).
import {type NiyetVeri, altyaziHali} from './cekirdek';

export * from './cekirdek';

type Pencere = {
  ST?: {w: number; h: number; format: string; niyet?: NiyetVeri};
  __hfThreeTime?: number;
  __hf?: {buildReady?: Record<string, Promise<unknown>>};
};

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** Altyazıyı kok öğesine (sahnenin en üst katmanı, tam kare) bağlar. HyperFrames ilk çizimi yazı tipi inene kadar bekler. */
export const niyetliAltyazi = (kok: HTMLElement | null, veri?: NiyetVeri) => {
  const W = window as unknown as Pencere;
  const N = veri ?? W.ST?.niyet;
  if (!kok) throw new Error('niyetliAltyazi: kök öğe yok (ör. <div id="altyazi"></div>)');
  // veri yoksa (./st ses henüz çalışmadı) sahne altyazısız çizilir; ölçüm ve ./st tip bunu söyler
  if (!N) return;
  const fmt = W.ST?.format ?? '16x9';
  const h = W.ST?.h ?? 1080;
  const hf = (W.__hf ??= {});
  (hf.buildReady ??= {})['niyet-yazi'] = Promise.all(['ığşİ', 'ÇÖÜ'].map((m) => document.fonts.load(`400 64px '${N.yazi.aile}'`, m)));
  Object.assign(kok.style, {position: 'absolute', inset: '0', pointerEvents: 'none'});
  const ciz = (t: number) => {
    const A = altyaziHali(N, fmt, t);
    if (!A) {
      kok.innerHTML = '';
      return;
    }
    const satirlar = A.satirlar.map((s, n) => `<div lang="tr" style="font-family:'${A.aile}',sans-serif;font-size:${s.boyut}px;line-height:1.12;white-space:pre;`
      + `width:max-content;padding:${A.pad[1]}em ${A.pad[0]}em;background:${A.zemin};border-radius:0.16em;margin-top:${n ? A.satirAra : 0}em;`
      + `font-kerning:normal;font-optical-sizing:none">`
      + s.kelimeler.map((k) => `<span style="display:inline-block;font-size:${k.boyut}px;font-variation-settings:${k.ayar};color:${k.renk};`
        + `transform:translateY(${k.kalkis}px)">${esc(k.metin)}</span>`
        + (k.bosluk ? `<span style="font-size:${k.boslukBoyut}px;font-variation-settings:${k.bosluk}"> </span>` : '')).join('')
      + '</div>').join('');
    kok.innerHTML = `<div style="position:absolute;left:${A.merkez - A.kutu.w / 2}px;width:${A.kutu.w}px;bottom:${h - A.kutu.alt}px;display:flex;`
      + `flex-direction:column;align-items:center;opacity:${A.opaklik};transform:translateY(${A.kayma}px)">${satirlar}</div>`;
  };
  window.addEventListener('hf-seek', (e) => ciz((e as CustomEvent<{time: number}>).detail.time));
  ciz(W.__hfThreeTime || 0);
};
