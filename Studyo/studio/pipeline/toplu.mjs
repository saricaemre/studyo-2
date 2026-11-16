// Kişisel etki filmi: bir şablon filmden her satır için video (./st toplu; pipeline/kisisel.py çağırır, elle çalıştırılmaz).
// Paket ve tarayıcı bir kez açılır; her iş (kimlik × format) kendi girdisiyle (props.kisi) renderMedia ile çizilir.
//
// Kullanım: node pipeline/toplu.mjs @<iş dosyası>   (iş dosyası videos/<id>/toplu/<çalışma>/_is.json; kişi verisi taşır, iş bitince silinir)
//   {"isler": [{"kimlik", "format", "comp", "props", "cikti", "gizli": [maskelenecek değerler]}], "esanli": sekme sayısı | null,
//    "paralel": aynı anda kaç film, "crf": 18, "gl": null}
// Çıktı (stdout): her olay bir JSON satırı; içinde yalnız kimlik ve format (ad ve değer yok). Hata iletilerinde kişinin değerleri maskelenir.
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, selectComposition} from '@remotion/renderer';
import {mkdirSync, readFileSync, rmSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const spec = JSON.parse(readFileSync(process.argv[2].replace(/^@/, ''), 'utf8'));
const yaz = (o) => process.stdout.write(JSON.stringify(o) + '\n');
const maskele = (s, gizli) => (gizli || []).filter((g) => g && String(g).length >= 2).reduce((m, g) => m.split(String(g)).join('‹…›'), String(s));

let paket = null;
process.on('exit', () => paket && rmSync(paket, {recursive: true, force: true}));
for (const [sinyal, kod] of [['SIGINT', 130], ['SIGTERM', 143]]) process.on(sinyal, () => process.exit(kod));

const t0 = Date.now();
paket = await bundle({entryPoint: path.join(ROOT, 'src/index.ts'), enableCaching: true, symlinkPublicDir: true});
yaz({olay: 'paket', sn: (Date.now() - t0) / 1000});
const browser = await openBrowser('chrome', spec.gl ? {chromiumOptions: {gl: spec.gl}} : undefined);
const bekleme = spec.gl ? {timeoutInMilliseconds: 120000} : {};

const isler = [...spec.isler];
let hatali = 0;
const isci = async () => {
  for (let is = isler.shift(); is; is = isler.shift()) {
    const k = {kimlik: is.kimlik, format: is.format};
    yaz({olay: 'basla', ...k});
    const t1 = Date.now();
    try {
      mkdirSync(path.dirname(is.cikti), {recursive: true});
      const composition = await selectComposition({serveUrl: paket, id: is.comp, inputProps: is.props, puppeteerInstance: browser, ...bekleme});
      let son = -1;
      await renderMedia({
        composition, serveUrl: paket, codec: 'h264', crf: spec.crf ?? 18, audioBitrate: '320k', outputLocation: is.cikti, inputProps: is.props,
        puppeteerInstance: browser, overwrite: true, logLevel: 'error', ...(spec.esanli ? {concurrency: spec.esanli} : {}), ...bekleme,
        onProgress: ({progress}) => {
          const o = Math.floor(progress * 10);
          if (o > son) {
            son = o;
            yaz({olay: 'ilerleme', ...k, oran: Math.round(progress * 100) / 100});
          }
        },
      });
      yaz({olay: 'bitti', ...k, sn: (Date.now() - t1) / 1000, kare: composition.durationInFrames, fps: composition.fps});
    } catch (e) {
      hatali += 1;
      yaz({olay: 'hata', ...k, sn: (Date.now() - t1) / 1000, mesaj: maskele(e?.message ?? e, is.gizli).slice(0, 400)});
    }
  }
};
await Promise.all(Array.from({length: Math.max(1, spec.paralel ?? 1)}, isci));
await browser.close({silent: true});
yaz({olay: 'son', sn: (Date.now() - t0) / 1000, hatali});
process.exit(0);
