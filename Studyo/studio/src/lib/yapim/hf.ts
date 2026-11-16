// Kılavuz kipinin HyperFrames karşılığı (yapım filmi, ./st yapim): pipeline/hf.py → kilavuz_varyanti bunu esbuild ile paketleyip
// filmin formatının bir kopyasına (out/_yapim/<id>/hf/…, hf/<id>/'ye dokunulmaz) satır içi koyar. Çekirdek Remotion'la ortak (kilavuz.ts).
// Her arayışta (hf-seek) sahne t anına kurulduktan sonra kutular ölçülüp çizilir; çizim döngüsü, saat yok (kural 8).
import {type Guvenli, kilavuzSvg, olc, veriSvg} from './kilavuz';

type Pencere = {
  ST?: {w: number; h: number; guvenli?: Guvenli};
  ST_YAPIM?: {kip?: 'kilavuz' | 'veri'};
  __hf?: {buildReady?: Record<string, Promise<unknown>>};
};

const W = window as unknown as Pencere;
const kok = document.querySelector('[data-composition-id]') as HTMLElement | null;
if (!kok) throw new Error('Kılavuz: data-composition-id taşıyan kök yok');
const katman = document.createElement('div');
katman.id = 'st-yapim-katman';
Object.assign(katman.style, {position: 'absolute', left: '0', top: '0', width: '100%', height: '100%', pointerEvents: 'none', zIndex: '2147483647'});
kok.appendChild(katman);
const kip = W.ST_YAPIM?.kip ?? 'kilavuz';

const ciz = () => {
  const w = W.ST?.w ?? kok.clientWidth;
  const h = W.ST?.h ?? kok.clientHeight;
  const k = olc(kok, w, h, katman);
  katman.innerHTML = kip === 'veri' ? veriSvg(k, w, h) : kilavuzSvg(k, w, h, W.ST?.guvenli ?? null);
};

// hf-seek'in öteki dinleyicileri (altyazı, 3B, sahne) bu olayda kurulur: ölçüm onlardan sonra, aynı görevin sonunda
window.addEventListener('hf-seek', () => queueMicrotask(ciz));
const hf = (W.__hf ??= {});
(hf.buildReady ??= {})['yapim-kilavuz'] = document.fonts.ready.then(ciz);
