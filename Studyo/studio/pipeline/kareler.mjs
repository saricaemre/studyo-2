// Seçilen kareleri doğrudan render eder. Her kare kendi başına hesaplanır (atlanabilirlik):
// 240. kare, 0–239 oynatılmadan çizilebilmelidir.
//
// Kullanım (genelde st.py çağırır):
//   node pipeline/kareler.mjs '{"comp":"GemilerKaradan","out":"/yol","frames":[0,77],"scale":1,"order":"asc"}'
//   "gl": "swangle" → 3B katman (Three.js) kullanan kompozisyon yazılımla (SwiftShader) çizilir; st.py seçer (O.gl). Verilmezse tarayıcı
//   eskisi gibi bayraksız açılır: öteki videoların kareleri değişmez (kural 11). Ölçüm: denemeler/threejs_3b/OKU.md.
// Çıktı: her kare için <out>/f00077.png; stdout'a JSON özet.
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {mkdirSync, readFileSync, rmSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// Kişi verisi taşıyan iş (./st toplu, kişisel film) tanımı komut satırına değil dosyaya yazılır: '@<yol>' (günlükte ad görünmez).
const spec = JSON.parse(process.argv[2].startsWith('@') ? readFileSync(process.argv[2].slice(1), 'utf8') : process.argv[2]);
const {comp, out, frames, props = {}, scale = 1} = spec;
const order = !frames ? [] : spec.order === 'desc' ? [...frames].sort((a, b) => b - a) : [...frames].sort((a, b) => a - b);

// Paket geçici klasöre yazılır: public/ kopyalanmaz, bağlanır (npx remotion render gibi; 133 MB yerine 34 MB, daha hızlı)
// ve paketi biz açtıysak çıkışta (hata ve panel iptali dahil) silinir. Silinmeyen kopyalar birikiyordu (2026-10-24: 177 paket, 24 GB).
// rmSync bağlantıyı izlemez: public/ ve plakalar yerinde kalır.
let paket = null;
process.on('exit', () => paket && rmSync(paket, {recursive: true, force: true}));
for (const [sinyal, kod] of [['SIGINT', 130], ['SIGTERM', 143]]) process.on(sinyal, () => process.exit(kod));
const serveUrl = spec.serveUrl ?? (paket = await bundle({entryPoint: path.join(ROOT, 'src/index.ts'), enableCaching: true, symlinkPublicDir: true}));
const tarayicilar = new Map();
const tarayici = async (gl) => {
  if (!tarayicilar.has(gl ?? '')) tarayicilar.set(gl ?? '', await openBrowser('chrome', gl ? {chromiumOptions: {gl}} : undefined));
  return tarayicilar.get(gl ?? '');
};
const kapat = () => Promise.all([...tarayicilar.values()].map((b) => b.close({silent: true})));
// 3B katman: ilk kare (gölgelendirici derleme, yansıma ortamı) yazılımla ve yükte 30 sn'yi aşabiliyor → uzun bekleme (ortak.py UC_BEKLEME_MS)
const bekleme = (gl) => (gl ? {timeoutInMilliseconds: 120000} : {});

// Çoklu iş: {"isler": [{"comp", "out", "frames", "props"}, …]} → paket ve tarayıcı bir kez açılır (ör. ./st gorunus: her seçenek × format)
// "esanli": N (isteğe bağlı, ./st yapim) → bir işin kareleri N sayfada aynı anda çizilir; verilmezse eskisi gibi sırayla.
if (spec.isler) {
  const t1 = Date.now();
  const sonuc = [];
  const esanli = Math.max(1, spec.esanli ?? 1);
  for (const is of spec.isler) {
    mkdirSync(is.out, {recursive: true});
    const browser = await tarayici(is.gl ?? spec.gl);
    const c = await selectComposition({serveUrl, id: is.comp, inputProps: is.props ?? {}, puppeteerInstance: browser, ...bekleme(is.gl ?? spec.gl)});
    const dosyalar = {};
    const kareler = [...is.frames].sort((x, y) => x - y);
    const ciz = async (f) => {
      if (f < 0 || f >= c.durationInFrames) throw new Error(`Kare ${f} aralık dışında (0..${c.durationInFrames - 1})`);
      const file = path.join(is.out, `f${String(f).padStart(5, '0')}.png`);
      await renderStill({composition: c, serveUrl, output: file, frame: f, inputProps: is.props ?? {}, scale, puppeteerInstance: browser, overwrite: true,
        ...bekleme(is.gl ?? spec.gl)});
      dosyalar[f] = file;
    };
    if (esanli === 1) {
      for (const f of kareler) await ciz(f);
    } else {
      let sira = 0;
      await Promise.all(Array.from({length: Math.min(esanli, kareler.length)}, async () => {
        while (sira < kareler.length) await ciz(kareler[sira++]);
      }));
    }
    sonuc.push({comp: is.comp, props: is.props ?? {}, files: dosyalar});
  }
  await kapat();
  // Çıktı boruya tam yazılmadan çıkma: 512 bayttan uzun sonuç (ör. 3 yol × 3 format) process.exit ile kesiliyordu.
  await new Promise((bitti) => process.stdout.write(JSON.stringify({isler: sonuc, serveUrl, seconds: (Date.now() - t1) / 1000}) + '\n', bitti));
  process.exit(0);
}

mkdirSync(out, {recursive: true});
const browser = await tarayici(spec.gl);
const composition = await selectComposition({serveUrl, id: comp, inputProps: props, puppeteerInstance: browser, ...bekleme(spec.gl)});

const files = {};
const t0 = Date.now();
for (const f of order) {
  if (f < 0 || f >= composition.durationInFrames) throw new Error(`Kare ${f} aralık dışında (0..${composition.durationInFrames - 1})`);
  const file = path.join(out, `f${String(f).padStart(5, '0')}.png`);
  await renderStill({composition, serveUrl, output: file, frame: f, inputProps: props, scale, puppeteerInstance: browser, overwrite: true, ...bekleme(spec.gl)});
  files[f] = file;
}
await kapat();
console.log(JSON.stringify({comp, fps: composition.fps, width: composition.width, height: composition.height,
  durationInFrames: composition.durationInFrames, serveUrl, files, seconds: (Date.now() - t0) / 1000}));
