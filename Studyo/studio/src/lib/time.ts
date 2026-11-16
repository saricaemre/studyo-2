export type Word = {i: number; text: string; start: number; end: number};
export type Sentence = {id: string; step: string; start: number; end: number; words: Word[]};
export type Timeline = {id: string; title: string; duration: number; sentences: Sentence[]; bpm?: number; beats?: number[]};
export type Anchor = (string | number)[];
export type CueFile = {lead?: number; cues: Record<string, Anchor>};

const norm = (s: string) => s.replace(/[.,…!?;:]/g, '');

/**
 * cues.json + timeline.json → işaret adı: saniye. pipeline/ortak.py resolve_anchor ile birebir aynı hesap.
 *   [cümle, kelime, ofset]  kelime başlangıcı − lead + ofset
 *   ["vurus", n, ofset]      müzik ızgarasının n. vuruşu + ofset
 *   ["t", saniye, ofset]     mutlak zaman + ofset
 */
export const makeCues = (tl: Timeline, cf: CueFile): Record<string, number> => {
  const out: Record<string, number> = {};
  for (const [k, a] of Object.entries(cf.cues)) {
    const off = a.length > 2 ? Number(a[2]) : 0;
    if (a[0] === 't') {
      out[k] = Number(a[1]) + off;
      continue;
    }
    if (a[0] === 'vurus') {
      const b = (tl.beats ?? [])[Number(a[1])];
      if (b === undefined) throw new Error(`İşaret ${k}: ${a[1]}. vuruş yok`);
      out[k] = b + off;
      continue;
    }
    const s = tl.sentences.find((x) => x.id === a[0]);
    if (!s) throw new Error(`İşaret ${k}: cümle yok ${a[0]}`);
    const w = s.words.find((x) => norm(x.text) === norm(String(a[1])));
    if (!w) throw new Error(`İşaret ${k}: kelime yok ${a[0]}/${a[1]}`);
    out[k] = w.start - (cf.lead ?? 0) + off;
  }
  return out;
};

/** t anında hangi vuruşta (müzik ızgarası) olduğumuz ve vuruş içindeki ilerleme (0..1). */
export const beatAt = (tl: Timeline, t: number) => {
  const b = tl.beats ?? [];
  let i = 0;
  while (i < b.length - 1 && b[i + 1] <= t) i++;
  const per = b.length > 1 ? b[Math.min(i + 1, b.length - 1)] - b[i] : 0.5;
  return {i, u: per > 0 ? Math.max(0, Math.min(1, (t - (b[i] ?? 0)) / per)) : 0};
};
