// src/lib/fontlar.ts'teki yazı tiplerini listeler (aile adı, tür, ağırlıklar, italik, Türkçe alt küme). ./st gorunus doğrulaması için.
// Kullanım: node pipeline/fontlar.mjs  → stdout JSON
//          node pipeline/fontlar.mjs --bilgi "Fredoka,Baloo Two"  → seçilen ailelerin dosya adresleri (HyperFrames motoru yerel @font-face kurar)
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const src = readFileSync(path.join(ROOT, 'src/lib/fontlar.ts'), 'utf8');
const turler = Object.fromEntries([...src.matchAll(/^\s+(\w+): \{mod: \w+, tur: '([^']+)'\}/gm)].map((m) => [m[1], m[2]]));
const out = {};
for (const [mod, tur] of Object.entries(turler)) {
  const info = require(path.join(ROOT, 'node_modules/@remotion/google-fonts/dist/cjs', mod + '.js')).getInfo();
  const n = info.fonts.normal || {};
  const w0 = Object.keys(n)[0];
  out[info.fontFamily] = {modul: mod, tur, agirliklar: Object.keys(n).map(Number), italik: Boolean(info.fonts.italic),
    turkce: w0 ? Object.keys(n[w0]).includes('latin-ext') : false};
}
const i = process.argv.indexOf('--bilgi');
if (i > 0) {
  const iste = new Set(process.argv[i + 1].split(',').map((x) => x.trim()));
  const bilgi = {};
  for (const [aile, o] of Object.entries(out)) {
    if (!iste.has(aile)) continue;
    const info = require(path.join(ROOT, 'node_modules/@remotion/google-fonts/dist/cjs', o.modul + '.js')).getInfo();
    bilgi[aile] = {fonts: info.fonts, unicodeRanges: info.unicodeRanges};
  }
  console.log(JSON.stringify(bilgi));
} else {
  console.log(JSON.stringify(out));
}
