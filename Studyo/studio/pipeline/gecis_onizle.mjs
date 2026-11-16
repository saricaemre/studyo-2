// Geçiş önizlemeleri (./st gecis onizle; pipeline/gecis.py): GecisOnizleme kompozisyonu her geçiş için 1,5 sn'lik küçük klip.
// Tek paket, tek tarayıcı (yazılım GL: gölgelendirici her makinede aynı çizilir).
//   node pipeline/gecis_onizle.mjs '{"adlar": ["BookFlip", …], "out": "/yol", "gl": "swangle"}'
// Çıktı: <out>/<ad>.mp4; stdout'un son satırı JSON özet {bitti, hata, seconds}.
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, selectComposition} from '@remotion/renderer';
import {mkdirSync, rmSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const spec = JSON.parse(process.argv[2]);
let paket = null;
process.on('exit', () => paket && rmSync(paket, {recursive: true, force: true}));
for (const [sinyal, kod] of [['SIGINT', 130], ['SIGTERM', 143]]) process.on(sinyal, () => process.exit(kod));
const t0 = Date.now();
paket = await bundle({entryPoint: path.join(ROOT, 'src/index.ts'), enableCaching: true, symlinkPublicDir: true});
const browser = await openBrowser('chrome', {chromiumOptions: {gl: spec.gl ?? 'swangle'}});
mkdirSync(spec.out, {recursive: true});
const bitti = [];
const hata = {};
for (const ad of spec.adlar) {
  try {
    const inputProps = {ad};
    const composition = await selectComposition({serveUrl: paket, id: 'GecisOnizleme', inputProps, puppeteerInstance: browser});
    await renderMedia({composition, serveUrl: paket, codec: 'h264', crf: 26, pixelFormat: 'yuv420p', muted: true, inputProps,
      outputLocation: path.join(spec.out, `${ad}.mp4`), puppeteerInstance: browser, overwrite: true, logLevel: 'error'});
    bitti.push(ad);
    process.stderr.write(`   ${bitti.length}/${spec.adlar.length} ${ad}\n`);
  } catch (e) {
    hata[ad] = String(e?.message ?? e).slice(0, 300);
  }
}
await browser.close({silent: true});
console.log(JSON.stringify({bitti, hata, seconds: (Date.now() - t0) / 1000}));
