// Stüdyo paneli · Çalışma alanı: ortada film, altta zaman çizelgesi, sağda yolun adımına göre denetçi

const W = {id: null, d: null, asama: null, fmt: null, zoom: 1, pps: 20, sure: 0, aktifV: -1, aktifK: -1, acikV: null, secKusur: null, platform: false,
  dalga: null, tik: null, plakaTik: null, vurus: [], kelime: [], isaret: [], kusurlar: [], sessizlik: [], kaynak: null};
const video = $('#film');
const kareImg = $('#kare-yerine');
const RENK_SIRA = ['s0', 's1', 's2', 's3', 's4', 's5', 's6', 's7'];

// ---------------------------------------------------------------- açılış
async function filmAc(id, asama, {yenile = false} = {}) {
  const G = await genelYukle(W.id !== id);
  if (!G.videolar.some((v) => v.id === id)) return istekSayfasi(id);  // henüz klasörü olmayan istek
  const d = await api.get(`/api/video/${id}`);
  const yeni = W.id !== id;
  const t0 = yeni ? 0 : video.currentTime;
  W.id = id; W.d = d;
  if (yeni) { Object.assign(W, {fmt: null, zoom: 1, acikV: null, secKusur: null, dalga: null, kaynak: null, yolGoster: null, yolFmt: null}); sonKareYol = null; video.removeAttribute('src'); video.load(); }
  W.asama = ADIMLAR.some((a) => a.k === asama) ? asama : (yeni || !W.asama ? varsayilanAsama(d) : W.asama);
  gorunumGoster('v-film');
  ortam('tuval');
  hazirla();
  $('#arac-baslik').textContent = d.baslik;
  $('#arac-alt').textContent = [d.profil, MOTOR_AD[d.motor] || 'Remotion', W.sure ? `${sn(W.sure)} sn` : null, d.stil, d.altyazi === 'niyetli' ? 'Niyetli altyazı' : null,
    d.uretim?.var ? `Kredi ${kredi(d.uretim.harcanan)} / ${kredi(d.uretim.sinir)}` : null].filter(Boolean).join(' · ');
  formatSecCiz(); yolCiz(); menuCiz(); denetciCiz({kaydirma: !yeni && yenile}); kaynakAyarla(t0); zamanCiz(); oynatmaGuncelle(video.currentTime || t0, true);
  history.replaceState(null, '', `#/film/${id}/${W.asama}`);
  ayrilinca = () => { video.pause(); clearTimeout(W.tik); clearTimeout(W.plakaTik); ortam(null); };
  if (yeni || !W.dalga) dalgaYukle();
  claudeIzle();
  if (d.plaka?.cizim) plakaIzle();
}
function varsayilanAsama(d) {
  const k = d.kapilar.find((x) => x.durum !== 'tamam');
  return k ? ADIMLAR[k.n - 1].k : 'teslim';
}
const sonInceleme = (d) => d.incelemeler[d.incelemeler.length - 1];
/** Geçerli vuruş iskeleti: filmin kendi yapısı (script.json → yapi) ya da profilin önerisi. */
const vurusIskeleti = (d = W.d) => d.yapi || d.profilDetay.vuruslar || [];
const metinOf = (s) => (s ? ((s.parts || []).map((p) => p.text).join(' ') || s.shot?.olay || '') : '');
function adimRenk(adim) {
  const i = vurusIskeleti().indexOf(adim);
  return `var(--${RENK_SIRA[(i < 0 ? 7 : i) % RENK_SIRA.length]})`;
}
function hazirla() {
  const d = W.d;
  W.fps = d.cizelge.fps || 30;
  W.sure = d.cizelge.sure || d.sure || 0;
  const sc = Object.fromEntries((d.script.sentences || []).map((s) => [s.id, s]));
  const cl = d.cizelge.cumleler || [];
  W.vurus = cl.map((c, i) => ({id: c.id, i, adim: c.adim, bas: i ? c.bas : 0, son: i < cl.length - 1 ? cl[i + 1].bas : W.sure, kelimeler: c.kelimeler || [],
    shot: sc[c.id]?.shot || {}, metin: (c.kelimeler || []).length ? c.kelimeler.map((w) => w[0]).join(' ') : metinOf(sc[c.id]), renk: adimRenk(c.adim)}));
  if (!W.vurus.length) W.vurus = (d.script.sentences || []).map((s, i) => ({id: s.id, i, adim: s.step, bas: null, son: null, kelimeler: [], shot: s.shot || {}, metin: metinOf(s), renk: adimRenk(s.step)}));
  W.kelime = [];
  W.vurus.forEach((v) => v.kelimeler.forEach((w) => W.kelime.push({m: w[0], b: w[1], s: w[2], v: v.i, n: W.kelime.length})));
  W.isaret = (d.isaretler || []).map(([ad, t]) => ({ad, t}));
  const son = sonInceleme(d);
  W.kusurlar = kusurlariAyikla(son?.inceleme || '');
  W.sessizlik = (son?.olcum || []).filter((r) => /sessizlik/i.test(r.ad) && /\d\d:\d\d\.\d+\s*[–-]\s*\d\d:\d\d\.\d+/.test(r.kanit || ''))
    .map((r) => { const m = r.kanit.match(/(\d\d:\d\d\.\d+)\s*[–-]\s*(\d\d:\d\d\.\d+)/); return {bas: zamanOku(m[1]), son: zamanOku(m[2])}; });
  const fm = d.formatlar;
  if (!W.fmt || !fm.includes(W.fmt)) W.fmt = fm.find((f) => medya(f)) || fm[0];
}
const zamanOku = (s) => { const m = String(s).match(/(\d+):(\d+(?:[.,]\d+)?)/); return m ? +m[1] * 60 + parseFloat(m[2].replace(',', '.')) : null; };
/** inceleme.md → en büyük 3 kusur: başlık, zaman, kanıt, düzeltme, durum, kare no. */
function kusurlariAyikla(text) {
  const out = [];
  const bloklar = String(text).split(/\n(?=###\s+\d+\.)/).filter((b) => /^###\s+\d+\./.test(b.trim()));
  for (const b of bloklar) {
    const bas = b.match(/^###\s+(\d+)\.\s*(.+)/m);
    const alan = (ad) => (b.match(new RegExp(`\\*\\*${ad}[^*]*:\\*\\*\\s*(.+)`, 'i')) || [])[1]?.trim() || '';
    const z = alan('Zaman');
    const zs = [...z.matchAll(/(\d\d):(\d\d[.,]\d+)/g)].map((m) => +m[1] * 60 + parseFloat(m[2].replace(',', '.')));
    const kare = (z.match(/f(\d{3,6})/) || [])[1];
    out.push({n: +bas[1], baslik: sadeMetin(bas[2]), zaman: z, t: zs[0] ?? null, bitis: zs[1] ?? (zs[0] != null ? zs[0] + 1.2 : null), kare: kare ? +kare : null,
      kanit: sadeMetin(alan('Kanıt')), duzeltme: sadeMetin(alan('Yerel düzeltme')), durum: sadeMetin(alan('Durum'))});
  }
  return out.slice(0, 6);
}

// ---------------------------------------------------------------- yol ve araç çubuğu
function adimDurum(k) {
  if (k.durum === 'tamam') return 'tamam';
  if (k.durum !== 'sirada') return 'bekliyor';
  if (claudeCalisiyor()) return 'claude';
  return k.eksik.length && k.eksik.every((e) => e.startsWith('Senin onayın')) ? 'sende' : (k.insan ? 'sende' : 'acik');
}
const claudeCalisiyor = () => W.d?.basit?.claude?.durum === 'çalışıyor';
function yolCiz() {
  $('#yol').innerHTML = ADIMLAR.map((a, i) => {
    const k = W.d.kapilar[i];
    const d = adimDurum(k);
    const ic = d === 'tamam' ? ik('tik') : d === 'claude' ? ik('claude') : d === 'sende' ? ik('unlem') : '';
    return `${i ? '<span class="yol-ayrac" aria-hidden="true"></span>' : ''}<button class="yol-adim ${d === 'sende' ? 'sende' : d} ${W.asama === a.k ? 'aktif' : ''}" data-asama="${a.k}" aria-current="${W.asama === a.k ? 'step' : 'false'}" title="Kapı ${a.kapi} · ${esc(k.ad)}${a.insan ? ' · senin onayın' : ''}">
      <span class="yol-ikon">${ic}</span><span class="yol-ad">${a.ad}</span>${a.insan ? ik('kisi', 'yol-insan') : ''}</button>`;
  }).join('');
}
function medya(f) {
  const fin = W.d.teslim.filter((t) => t.format === f);
  if (fin.length) return {tur: 'final', yol: fin[fin.length - 1].dosya, poster: fin[fin.length - 1].poster, ad: fin[fin.length - 1].ad};
  if (W.d.kaba[f]) return {tur: 'kaba', yol: W.d.kaba[f]};
  return null;
}
function formatSecCiz() {
  const fm = W.d.formatlar;
  $('#format-sec').innerHTML = fm.map((f) => `<button type="button" role="tab" aria-selected="${f === W.fmt}" class="${f === W.fmt ? 'aktif' : ''}" data-fmt="${f}" title="${FORMAT_AD[f] || f}${medya(f) ? '' : ' · henüz video yok'}">${ik(FORMAT_IK[f] || 'kare')}${fmtEtiket(f)}</button>`).join('');
}
function menuCiz() {
  const d = W.d;
  $('#arac-menu').innerHTML = `
    <button type="button" data-menu-eylem="hizli">${ik('goz')}Hızlı önizleme</button>
    ${d.motor === 'blender' ? `<button type="button" data-menu-eylem="blender-ac">${ik('oynat')}Sahneyi Blender'da aç</button>`
    : d.motor !== 'hyperframes' ? `<button type="button" data-menu-eylem="remotion">${ik('oynat')}Canlı önizleme (Remotion Studio)</button>` : ''}
    <button type="button" data-menu-eylem="deterministik">${ik('yenile')}Kararlılık testi</button>
    <button type="button" data-menu-eylem="kataloga" ${d.katalogaHazir && GENEL?.claudeVar ? '' : 'disabled title="Filmin dili belli olunca: Kapı 1 kapanınca ya da ilk kareler çizilince"'}>${ik('arti')}Bu filmin dilini kataloğa ekle</button>
    <hr>
    <button type="button" data-menu-eylem="claude-metin">${ik('kopya')}Claude Code'a yapıştırılacak metni kopyala</button>
    <button type="button" data-menu-eylem="klasor">${ik('dosya')}Klasör yolunu kopyala</button>`;
}

// ---------------------------------------------------------------- oynatıcı
function kaynakAyarla(t0 = 0) {
  const f = W.fmt;
  const m = medya(f);
  const fb = W.d.formatBilgi[f] || {};
  W.oran = fb.w && fb.h ? fb.w / fb.h : fmtOran(f);
  $('#v-film').style.setProperty('--oran', W.oran);
  cerceveSigdir();
  const mix = W.d.sesDosyalari['mix.wav'];
  const src = m ? m.yol : mix || null;
  const anahtar = `${f}|${src}`;
  if (W.kaynak !== anahtar) {
    W.kaynak = anahtar;
    video.pause();
    if (src) { video.src = dosyaUrl(src); video.currentTime = Math.min(t0, W.sure || t0); } else { video.removeAttribute('src'); video.load(); }
    video.poster = m?.poster ? kucukUrl(m.poster, 900) : '';
  }
  const videoVar = !!m;
  kareImg.hidden = videoVar;
  const not = $('#cerceve-not');
  not.hidden = videoVar;
  const yo = !(W.d.kareler[f] || []).length ? yolOnizleme() : null;  // planda üç yol: kare yokken sahnede gösterilen yolun kanca karesi
  if (!videoVar) not.textContent = mix ? 'Henüz video yok: son incelemenin kareleri sesle birlikte oynar.' : (W.d.kareler[f] || []).length ? 'Henüz video ve ses yok: zaman çizelgesinde kareleri gezebilirsin.'
    : yo ? `${yo.harf.toUpperCase()} · ${yo.ad}: yolun kanca karesi. Başka bir yolun karesi için kartındaki görsele dokun.` : 'Henüz görüntü yok. Kareler ve ses üretildikçe burada görünür.';
  // platform arayüzünün kapladığı alan (formatlar.json → guvenli)
  const g = fb.guvenli || {};
  const P = $('#platform');
  const yuz = (x) => `${(x || 0) * 100}%`;
  Object.assign($('.p-ust', P).style, {height: yuz(g.ust), display: g.ust ? '' : 'none'});
  Object.assign($('.p-alt', P).style, {height: yuz(g.alt), display: g.alt ? '' : 'none'});
  Object.assign($('.p-sag', P).style, {width: yuz(g.sag), top: yuz(g.ust), bottom: yuz(g.alt), display: g.sag ? '' : 'none'});
  Object.assign($('.p-sol', P).style, {width: yuz(g.sol), top: yuz(g.ust), bottom: yuz(g.alt), left: 0, display: g.sol ? '' : 'none'});
  $('#platform-dugme').hidden = !(g.ust || g.alt || g.sag || g.sol);
}
function cerceveSigdir() {
  const s = $('.sahne');
  const c = $('#cerceve');
  if (!s || !W.oran) return;
  const w = Math.min(s.clientWidth, s.clientHeight * W.oran);
  c.style.width = `${Math.floor(w)}px`;
  c.style.height = `${Math.floor(w / W.oran)}px`;
}
new ResizeObserver(() => cerceveSigdir()).observe($('.sahne'));
function kareBul(t) {
  const L = W.d.kareler[W.fmt] || [];
  let en = null;
  for (const k of L) { if (k.t <= t + 0.02) en = k; else break; }
  return en || L[0] || null;
}
let sonKareYol = null;
function kareGoster(t) {
  if (kareImg.hidden) return;
  const k = kareBul(t);
  const yol = k ? k.yol : yolOnizleme()?.yol;
  if (yol && yol !== sonKareYol) { sonKareYol = yol; kareImg.src = kucukUrl(yol, 720); }
}
/** Yol modunda kare yokken sahnede gösterilen yol: kartta dokunulan > seçilen > ilk. */
function yolOnizleme() {
  const g = W.d?.gorunus;
  const S = g?.yolModu ? (g.secenekler || []).filter((s) => s.yol) : [];
  if (!S.length) return null;
  const s = S.find((x) => x.harf === W.yolGoster) || S.find((x) => x.harf === g.secim) || S[0];
  return {harf: s.harf, ad: s.yol.ad || s.ad, yol: yolKaresi(g, s.harf, W.fmt)};
}
const tuval = $('#ortam-tuval');
const tctx = tuval.getContext('2d');
function ortamCiz() {
  try {
    if (!kareImg.hidden && kareImg.complete && kareImg.naturalWidth) tctx.drawImage(kareImg, 0, 0, 36, 64);
    else if (video.readyState >= 2 && video.videoWidth) tctx.drawImage(video, 0, 0, 36, 64);
  } catch (e) { /* çizilemezse ışık eski karede kalır */ }
}
kareImg.addEventListener('load', ortamCiz);
let kareSay = 0;
function dongu() {
  oynatmaGuncelle(video.currentTime);
  if (++kareSay % 4 === 0) ortamCiz();
  if (!video.paused) requestAnimationFrame(dongu);
}
video.addEventListener('play', () => { $('#cerceve').classList.add('oynuyor'); $('#oynat').innerHTML = ik('dur'); $('#oynat').setAttribute('aria-label', 'Duraklat'); requestAnimationFrame(dongu); });
video.addEventListener('pause', () => { $('#cerceve').classList.remove('oynuyor'); $('#oynat').innerHTML = ik('oynat'); $('#oynat').setAttribute('aria-label', 'Oynat'); });
video.addEventListener('seeked', () => { oynatmaGuncelle(video.currentTime); ortamCiz(); });
video.addEventListener('timeupdate', () => { if (!video.paused && document.hidden) oynatmaGuncelle(video.currentTime); });  // arka planda rAF durur
video.addEventListener('loadeddata', () => { ortamCiz(); if (!W.sure && video.duration) { W.sure = video.duration; zamanCiz(); } });
function git(t) {
  t = Math.max(0, Math.min((W.sure || video.duration || 0) - 0.02, t));
  if (video.getAttribute('src')) video.currentTime = t;
  W.serbestT = t;
  oynatmaGuncelle(t);
}
const simdikiT = () => (video.getAttribute('src') ? video.currentTime : W.serbestT || 0);
const oynatDurdur = () => {
  if (!video.getAttribute('src')) { bildir('Oynatılacak video ya da ses yok.'); return; }
  video.paused ? video.play().catch(() => bildir('Video oynatılamadı.')) : video.pause();
};
$('#oynat').addEventListener('click', oynatDurdur);
$('#cerceve').addEventListener('click', oynatDurdur);
$('#cerceve').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); oynatDurdur(); } });
function vurusAtla(yon) {
  const V = W.vurus.filter((v) => v.bas != null);
  if (!V.length) return;
  const t = simdikiT();
  const ai = Math.max(0, V.findIndex((v) => v.i === W.aktifV));
  const i = yon < 0 ? (t - V[ai].bas > 0.6 ? ai : Math.max(0, ai - 1)) : Math.min(V.length - 1, ai + 1);
  git(V[i].bas + 0.01);
}
$('#onceki').addEventListener('click', () => vurusAtla(-1));
$('#sonraki').addEventListener('click', () => vurusAtla(1));
$('#platform-dugme').addEventListener('click', (e) => { W.platform = !W.platform; $('#platform').classList.toggle('acik', W.platform); e.currentTarget.classList.toggle('secili', W.platform); e.currentTarget.setAttribute('aria-pressed', W.platform); });
$('#kenar-dugme').addEventListener('click', () => {
  if (window.matchMedia('(max-width:900px)').matches) { $('#app').classList.toggle('yan-acik'); return; }
  KENAR_ACIK = !KENAR_ACIK; $('#app').classList.toggle('odak', !KENAR_ACIK);
});
$('#z-yakin').addEventListener('click', () => { W.zoom = Math.min(8, W.zoom + 1); zamanCiz(); oynatmaGuncelle(simdikiT(), true); const k = $('#seritler'); k.scrollLeft = simdikiT() * W.pps - k.clientWidth / 2; });
$('#z-uzak').addEventListener('click', () => { W.zoom = Math.max(1, W.zoom - 1); zamanCiz(); oynatmaGuncelle(simdikiT(), true); });

// ---------------------------------------------------------------- zaman çizelgesi
function anahtarZamani(v) {
  const ana = trKucuk(v.shot.anahtar || '');
  if (ana) { const w = v.kelimeler.find((x) => trKucuk(x[0]).startsWith(ana)); if (w) return w[1]; }
  if (v.shot.isaret) { const c = W.isaret.find((x) => x.ad === v.shot.isaret); if (c) return c.t; }
  return null;
}
function vurusKaresi(v) {
  const L = (W.d.kareler[W.fmt] || []).filter((k) => v.bas != null && k.t >= v.bas - 0.01 && k.t < v.son);
  if (!L.length) return kareBul(v.bas ?? 0);
  const hedef = anahtarZamani(v) ?? (v.bas + v.son) / 2;
  return L.reduce((a, b) => (Math.abs(b.t - hedef) < Math.abs(a.t - hedef) ? b : a));
}
function zamanCiz() {
  const kap = $('#seritler');
  const ic = $('#seritler-ic');
  const gen = kap.clientWidth;
  const P = vurusIskeleti();
  $('#lejant').innerHTML = P.map((ad, i) => `<span style="--renk:var(--${RENK_SIRA[i % 8]})"><i></i>${esc(ad)}</span>`).join('');
  if (!W.sure) {
    ic.style.width = '100%';
    ic.innerHTML = `<div class="zaman-bos" style="height:200px">Zaman çizelgesi ses üretilince kurulur: vuruşların, kelimelerin ve işaretlerin zamanı oradan gelir.${W.d.kapilar[2].durum !== 'bekliyor' ? '<br>Kareler adımında “Ses üret ve miksle”.' : ''}</div>`;
    return;
  }
  if (!gen) return;
  W.pps = ((gen - 16) / W.sure) * W.zoom;
  const Wd = W.sure * W.pps + 8;
  const x = (t) => (t * W.pps).toFixed(1);
  const adim = W.pps > 70 ? 1 : W.pps > 30 ? 2 : W.pps > 14 ? 5 : 10;
  let cetvel = '';
  for (let t = 0; t <= W.sure; t += 0.5) {
    const tam = Math.abs(t - Math.round(t)) < 0.01;
    if (!tam && W.pps < 40) continue;
    const et = tam && Math.round(t) % adim === 0;
    cetvel += `<i class="ct ${et ? 'b' : ''}" style="left:${x(t)}px"></i>${et ? `<span class="cs" style="left:${x(t)}px">${Math.round(t)}</span>` : ''}`;
  }
  cetvel += W.kusurlar.filter((k) => k.t != null).map((k) => `<span class="kusur-bayrak" data-kusur="${k.n}" style="left:${x(k.t)}px" title="Kusur ${k.n}: ${esc(k.baslik)}">${k.n}</span>`).join('');
  const V = W.vurus.filter((v) => v.bas != null);
  const gen_ = (v) => Math.max(2, (v.son - v.bas) * W.pps - 2).toFixed(1);
  const klipler = V.map((v) => `<div class="klip" data-klip="${v.i}" style="left:${x(v.bas)}px;width:${gen_(v)}px;--renk:${v.renk}">${esc(v.adim)}<span>${esc(v.id)}</span></div>`).join('');
  const seritKare = V.map((v) => { const k = vurusKaresi(v); return `<div class="film-seridi" style="left:${x(v.bas)}px;width:${gen_(v)}px">${k ? `<img src="${kucukUrl(k.yol, 200)}" alt="" loading="lazy">` : ''}</div>`; }).join('');
  const yazili = W.pps >= 64;
  const kelimeler = W.kelime.length ? W.kelime.map((k) => `<span class="kelime ${yazili ? 'yazili' : ''}" data-kel="${k.n}" style="left:${x(k.b)}px;width:${Math.max(3, (k.s - k.b) * W.pps - 1.5).toFixed(1)}px" title="${esc(k.m)}">${yazili ? esc(k.m) : ''}</span>`).join('')
    : `<span class="ince" style="position:absolute;left:4px;top:0;font-size:10.5px">${W.d.anlatim ? 'kelime zamanları ses üretilince gelir' : 'anlatımsız film'}</span>`;
  const isaretler = W.isaret.map((c, i) => `<i class="isaret" data-is="${i}" style="left:${x(c.t)}px" title="${esc(c.ad)} · ${tc(c.t).slice(3)}"></i>`).join('');
  const olcu = (W.d.cizelge.olculer || []).filter((t) => t <= W.sure).map((t) => `<i class="vurus-cizgi" style="left:${x(t)}px"></i>`).join('');
  const sessiz = W.sessizlik.map((s) => `<span class="sessizlik" style="left:${x(s.bas)}px;width:${((s.son - s.bas) * W.pps).toFixed(1)}px" title="Bilinçli sessizlik · ${sn(s.son - s.bas)} sn"><span>${W.pps > 40 ? 'sessizlik' : ''}</span></span>`).join('');
  const kusurAlan = W.kusurlar.filter((k) => k.t != null).map((k) => `<i class="kusur-alan" style="left:${x(k.t)}px;width:${(Math.max(0.3, k.bitis - k.t) * W.pps).toFixed(1)}px"></i>`).join('');
  ic.style.width = `${Wd}px`;
  ic.innerHTML = `
    <div class="serit cetvel h-cetvel">${cetvel}</div>
    <div class="serit h-vurus">${klipler}</div>
    <div class="serit h-goruntu">${seritKare}</div>
    <div class="serit h-anlatim">${kelimeler}</div>
    <div class="serit h-isaret">${isaretler}</div>
    <div class="serit ses-serit h-ses">${olcu}${sessiz}<canvas id="dalga-taban"></canvas><div class="ses-calan" id="ses-calan"><canvas id="dalga-calan"></canvas></div></div>
    ${kusurAlan}
    <div class="oynatma" id="oynatma"></div>`;
  dalgaCiz();
  $('#z-oran').textContent = W.zoom === 1 ? 'Sığdır' : `${W.zoom}×`;
  W.aktifV = -1; W.aktifK = -2;
  $('#zaman').classList.toggle('rotus-modu', W.asama === 'rotus');
}
async function dalgaYukle() {
  const id = W.id;
  try { const r = await api.get(`/api/video/${id}/dalga`); if (W.id === id) { W.dalga = r; dalgaCiz(); } } catch (e) { /* ses yoksa şerit boş kalır */ }
}
function dalgaCiz() {
  const P = W.dalga?.tepe || [];
  const taban = $('#dalga-taban');
  if (!taban || !P.length) return;
  const Wd = W.sure * W.pps + 8;
  const ciz = (c, tok) => {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const H = 38;
    c.width = Math.round(Wd * dpr); c.height = H * dpr;
    c.style.width = `${Wd}px`; c.style.height = `${H}px`;
    const ctx = c.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue(`--${tok}`).trim() || '#888';
    const sure = W.dalga.sure || W.sure;
    for (let px = 0; px < Wd - 8; px += 3) {
      const t = px / W.pps;
      const p = P[Math.min(P.length - 1, Math.floor((t / sure) * P.length))] || 0;
      const h = Math.max(1.5, Math.pow(p, 0.8) * (H - 6));
      ctx.fillRect(px, (H - h) / 2, 2, h);
    }
  };
  ciz(taban, 'yazi-3');
  ciz($('#dalga-calan'), 'vurgu');
}
function oynatmaGuncelle(t, zorla) {
  const ph = $('#oynatma');
  if (ph) ph.style.left = `${(t * W.pps).toFixed(1)}px`;
  const sc = $('#ses-calan');
  if (sc) sc.style.width = `${(t * W.pps).toFixed(1)}px`;
  $('#zk').innerHTML = `${tc(t)} <span>/ ${tc(W.sure)}</span>`;
  kareGoster(t);
  let vi = -1;
  for (const v of W.vurus) if (v.bas != null && t >= v.bas) vi = v.i;
  if (vi !== W.aktifV || zorla) {
    W.aktifV = vi;
    $$('.klip').forEach((k) => k.classList.toggle('simdi', +k.dataset.klip === vi));
    const v = W.vurus[vi];
    $('#vurus-cip').innerHTML = v ? `<i style="--renk:${v.renk}"></i>${esc(v.adim)} · ${esc(v.id)}` : '<i></i>—';
    if (W.asama === 'senaryo') senaryoVurgula();
    if (W.asama === 'kareler') kareVurgula();
    yerTutucu();
  }
  let ki = -1;
  for (let i = 0; i < W.kelime.length; i++) { if (t >= W.kelime[i].b - 0.02) ki = i; else break; }
  if (ki >= 0 && t > W.kelime[ki].s + 0.25) ki = -1 - ki;
  if (ki !== W.aktifK || zorla) {
    W.aktifK = ki;
    $$('.kelime.su').forEach((k) => k.classList.remove('su'));
    if (ki >= 0) $(`.kelime[data-kel="${ki}"]`)?.classList.add('su');
    if (W.asama === 'senaryo') kelimeVurgula(ki);
  }
  $$('.isaret').forEach((el) => { const c = W.isaret[+el.dataset.is]; el.classList.toggle('su', t >= c.t && t < c.t + 0.35); });
  if (W.zoom > 1 && !video.paused) {
    const kap = $('#seritler');
    const px = t * W.pps;
    if (px < kap.scrollLeft + 20 || px > kap.scrollLeft + kap.clientWidth - 60) kap.scrollLeft = px - 80;
  }
}
(() => {
  const ic = $('#seritler-ic');
  let surukle = false;
  const tAl = (e) => (e.clientX - ic.getBoundingClientRect().left) / W.pps;
  ic.addEventListener('pointerdown', (e) => {
    if (!W.sure || e.target.closest('[data-kusur]')) return;
    surukle = true; ic.setPointerCapture(e.pointerId); git(tAl(e));
  });
  ic.addEventListener('pointermove', (e) => { if (surukle) git(tAl(e)); });
  ic.addEventListener('pointerup', () => { surukle = false; });
  ic.addEventListener('pointercancel', () => { surukle = false; });
})();
new ResizeObserver(() => { if (!$('#v-film').hidden && W.d) { zamanCiz(); oynatmaGuncelle(simdikiT(), true); } }).observe($('#seritler'));

// ---------------------------------------------------------------- denetçi
const ONERI = {
  plan: ['Kancayı daha sert yap', 'Üç yeni görünüş öner'],
  senaryo: ['Bu vuruşu kısalt', 'Ders cümlesine iki alternatif yaz'],
  kareler: ['Bu kareyi yeniden çiz', 'Alt üçte biri boş kalmasın'],
  kurgu: ['Uyarıları gider', 'Donuk aralığı canlandır'],
  rotus: ['Açık kusurları onar', 'Birinci kusuru onar'],
  teslim: ['Başlık için iki alternatif daha yaz', 'Sabit yorumu kısalt'],
};
const ONERI_YOL = ['Başka üç yol öner', 'Seçtiğim yolda başka görünüşler', 'Kancayı daha sert yap'];
const BASKA_YOLLAR = 'Bu üç yol olmadı: yöntem olarak öncekilerden ve birbirinden farklı üç yeni yol öner. ';
function denetciCiz({kaydirma = false} = {}) {
  const i = ADIMLAR.findIndex((a) => a.k === W.asama);
  const a = ADIMLAR[i];
  const k = W.d.kapilar[i];
  const dd = adimDurum(k);
  const cip = dd === 'tamam' ? `<span class="cip yesil">${ik('tik')}${a.insan && k.onay ? `Onayladın · ${gun(k.onay)}` : 'Tamam'}</span>`
    : dd === 'claude' ? '<span class="cip claude">Claude çalışıyor</span>' : dd === 'sende' ? `<span class="cip turuncu">${a.insan ? 'Onayın bekleniyor' : 'Sırada'}</span>`
      : dd === 'acik' ? '<span class="cip">Sırada</span>' : '<span class="cip">Önceki adımı bekliyor</span>';
  const yd = W.asama === 'plan' ? yolDurumu() : null;  // planda üç yol: başlık kararın kendisi
  const bas = yd === 'secim' ? {ad: 'Üç yol · seçim senin', ne: 'Claude bu film için birbirinden farklı üç fikir önerdi. Kanca karelerine bak, birini seç; Claude planı o yolda tamamlar.'}
    : yd ? {ad: a.ad, ne: 'Seçtiğin yol, brief, gerçekler ve görünüş: filmin ne söylediği ve neyin uydurulamayacağı.'} : a;
  $('#den-bas').innerHTML = `<div class="den-ust"><span>Kapı ${a.kapi}</span><span aria-hidden="true">·</span><span>${a.insan ? 'Sen onaylarsın' : 'Kanıt kapatır'}</span><span style="margin-left:auto">${cip}</span></div><h2>${bas.ad}</h2><p>${bas.ne}</p>`;
  const G = {plan: govdePlan, senaryo: govdeSenaryo, kareler: govdeKareler, kurgu: govdeKurgu, rotus: govdeRotus, teslim: govdeTeslim}[W.asama];
  const ust = claudeCalisiyor() ? claudeKartHtml(W.d.basit.claude) : '';
  const altBilgi = `<details class="aac"><summary>${ik('sag')}Claude Code'da kendin çalışıyorsan</summary><div class="kopya-satir" style="padding:0"><div class="ince">${esc(W.d.claude)}</div><button class="ikon-btn" type="button" data-kopyala="${esc(W.d.claude)}" aria-label="Metni kopyala">${ik('kopya')}</button></div></details>`;
  const g = $('#den-govde');
  const st = g.scrollTop;
  g.innerHTML = ust + G() + altBilgi;
  simgele(g);
  if (kaydirma) g.scrollTop = st; else g.scrollTop = 0;
  $('#oneriler').innerHTML = (W.asama === 'plan' && yd ? ONERI_YOL : ONERI[W.asama]).map((o) => `<button type="button" class="oneri">${esc(o)}</button>`).join('');
  const kilit = claudeCalisiyor() || !GENEL?.claudeVar;
  $('#claude-metin').disabled = kilit;
  $('#claude-form .gonder').disabled = kilit;
  $('#zaman').classList.toggle('rotus-modu', W.asama === 'rotus');
  denetciBagla(g);
  if (W.asama === 'senaryo') senaryoVurgula(true);
  if (W.asama === 'kareler') kareVurgula();
  yerTutucu();
}
function yerTutucu() {
  const inp = $('#claude-metin');
  if (claudeCalisiyor()) { inp.placeholder = 'Claude çalışıyor; bitince yeni istek yazabilirsin.'; return; }
  if (!GENEL?.claudeVar) { inp.placeholder = 'Claude Code bu bilgisayarda bulunamadı.'; return; }
  const v = W.vurus[W.aktifV];
  inp.placeholder = ['senaryo', 'kareler'].includes(W.asama) && v ? `${v.id} · ${v.adim} vuruşu için Claude'a söyle…` : `${ADIMLAR.find((a) => a.k === W.asama).ad} için Claude'a ne söyleyeyim?`;
}

// ---- kapı kutusu: eksikler, komutlar, onay
const KOMUT = {
  1: [['gorunus', 'Görünüş denemesini yeniden çiz']],
  2: [['lint', 'Denetle'], ['cekim', 'Çekim listesini güncelle']],
  3: [['ses', 'Ses üret ve miksle'], ['temsili', 'Temsilî kareleri üret', 1]],
  4: [['inceleme', 'İncele: kontak + ölçüm', 1], ['elestir', 'Kör eleştiri']],
  5: [['inceleme', 'Yeniden incele', 1], ['elestir', 'Kör eleştiri']],
  6: [['kaba', 'Kaba kurgu'], ['final', 'Final render', 1], ['yayin', 'Yayın paketi taslağı']],
};
function kapiKutu(n) {
  const d = W.d;
  const k = d.kapilar[n - 1];
  const a = ADIMLAR[n - 1];
  const calisan = claudeCalisiyor();
  const eksik = k.eksik.filter((e) => !e.startsWith('Senin onayın'));
  const komutlar = KOMUT[n].filter(([c]) => c !== 'gorunus' || d.gorunus?.mod === 'video')
    .map(([c, ad, ana]) => [c, c === 'gorunus' && d.gorunus?.yolModu ? 'Kanca karelerini yeniden çiz' : ad, ana])
    .map(([c, ad, ana]) => `<button type="button" class="btn ${ana && k.durum === 'sirada' && eksik.length ? 'ana-btn' : 'cam-btn'} kucuk" data-komut="${c}" ${calisan ? 'disabled title="Claude çalışırken komut çalıştırılmaz"' : ''}>${esc(ad)}</button>`).join('');
  if (k.durum === 'tamam') {
    return `<div class="kapi-kutu tamam"><h4>${ik('tik')}Kapı ${n} kapalı${k.onay ? ` · ${a.insan ? 'onayladın' : 'not düşüldü'} ${gun(k.onay)}` : ''}</h4>${k.not ? `<p class="ince">${esc(k.not)}</p>` : ''}<div class="dugmeler">${komutlar}</div>${n >= 3 ? plakaKutu() : ''}</div>`;
  }
  const onayBekliyor = k.eksik.some((e) => e.startsWith('Senin onayın'));
  const engel = k.durum === 'bekliyor' ? d.kapilar.find((x) => x.durum === 'sirada') : null;
  const gorunusYok = d.gorunus?.mod === 'video' && !d.gorunus.secim;
  const yolEksik = !!d.gorunus?.yolModu && yolDurumu(d) !== 'tamam';  // yol modu: plan seçilen yolda tamamlanmadan (senaryo denetimi temiz) onaylanmaz
  const planOnayi = (n === 1 || n === 2) && ['plan_onay', 'yol_secim'].includes(d.basit?.durum) && GENEL?.claudeVar;
  let onay = '';
  if (planOnayi && yolDurumu(d) !== 'secim') onay = `<button type="button" class="btn ana-btn" data-plan-onay ${gorunusYok || yolEksik || calisan ? 'disabled' : ''}>Planı onayla, üretime geç</button>${gorunusYok ? `<span class="ince">${d.gorunus.yolModu ? 'Önce üç yoldan birini seç.' : 'Önce görünüşlerden birini seç.'}</span>` : yolEksik ? '<span class="ince">Plan seçtiğin yolda tamamlanınca (senaryo denetimi temiz) onaylanır.</span>' : ''}`;
  if (a.insan && onayBekliyor) onay += `<button type="button" class="btn ${planOnayi ? 'cam-btn' : 'ana-btn'}" data-kapi-onay="${n}" ${eksik.length || calisan ? 'disabled title="Önce diğer eksikler tamamlanmalı"' : ''}>${planOnayi ? `Yalnız Kapı ${n}'i onayla` : n === 6 ? 'Videoyu onayla' : `Kapı ${n}'i onayla`}</button>`;
  const devam = !a.insan && k.durum === 'sirada' && !calisan && GENEL?.claudeVar ? '<button type="button" class="btn cam-btn kucuk" data-claude-devam>Claude devam etsin</button>' : '';
  const sinif = k.durum === 'sirada' ? (a.insan ? 'sende' : '') : '';
  return `<div class="kapi-kutu ${sinif}">
    <h4>${k.durum === 'bekliyor' ? ik('saat') : a.insan ? ik('kisi') : ik('unlem')}${k.durum === 'bekliyor' ? `Önce Kapı ${engel?.n ?? n - 1} kapanmalı` : a.insan ? 'Senin adımın' : 'Sıradaki iş'}</h4>
    ${eksik.length ? `<ul>${eksik.map((e) => `<li>${esc(e)}</li>`).join('')}</ul>` : onayBekliyor ? '<p class="ince">Eksik yok; yalnız senin onayın bekleniyor.</p>' : ''}
    ${onay ? `<div class="dugmeler">${onay}</div>` : ''}
    ${komutlar || devam ? `<div class="dugmeler">${komutlar}${devam}</div>` : ''}
    ${n >= 3 ? plakaKutu() : ''}
  </div>`;
}

// ---- Blender: plaka çizimi (ilerleme, hazır plakalar, bellek uyarısı)
const kalanMetni = (s) => (s < 90 ? `${Math.max(1, Math.round(s))} sn` : s < 5400 ? `${Math.round(s / 60)} dk` : `${sn(s / 3600)} saat`);
const CIZER_AD = {cycles: 'Cycles', eevee: 'EEVEE'};
function plakaIc(p) {
  const c = p.cizim;
  const k = (p.kumeler || {})[W.fmt || W.d.formatlar[0]] || {};
  const cz = CIZER_AD[c?.cizer || p.cizer] || 'Cycles';
  // eksik plakaların tahmini (çizerin tipik hızıyla; çizim başlayınca gerçek hızla düzelir)
  const say = (x) => `${x?.hazir ?? 0}/${x?.toplam ?? 0}${x && x.hazir < x.toplam && x.tahmin_sn ? ` (eksikler ~${kalanMetni(x.tahmin_sn)})` : ''}`;
  const ust = c
    ? `<div class="plaka-ust"><b>${ik('saat')}Blender çiziyor · ${cz} · plaka ${c.yapilan}/${c.toplam}</b><span>kalan ~${kalanMetni(c.kalan_sn || 0)}</span></div>
       <div class="plaka-cubuk" role="progressbar" aria-valuemin="0" aria-valuemax="${c.toplam}" aria-valuenow="${c.yapilan}"><i style="width:${Math.round(100 * c.yapilan / Math.max(1, c.toplam))}%"></i></div>`
    : `<div class="plaka-ust"><b>Blender kareleri · ${cz}</b><span>taslak ${say(k.taslak)} · teslim kalitesi ${say(k.tam)}</span></div>`;
  const bellek = p.bellek_az
    ? `<p class="plaka-uyari">${ik('unlem')}<span>Boş bellek az (${sn(p.bellek_gb)} GB). Çizim yavaşlayabilir; büyük uygulamaları kapatmak hızlandırır.</span></p>` : '';
  return ust + bellek;
}
function plakaKutu() {
  const p = W.d.plaka;
  return p ? `<div class="plaka-kutu" id="plaka-kutu">${plakaIc(p)}</div>` : '';
}
// Çizim sürerken ve bir komuttan hemen sonra (sahne kurulup ilk kare çıkana dek ~40 sn) plaka durumunu yoklar.
function plakaIzle(deneme = 0) {
  clearTimeout(W.plakaTik);
  const id = W.id;
  W.plakaTik = setTimeout(async () => {
    if ($('#v-film').hidden || W.id !== id || !W.d?.plaka) return;
    try {
      const p = await api.get(`/api/video/${id}/plaka`);
      W.d.plaka = p;
      const el = $('#plaka-kutu');
      if (el) el.innerHTML = plakaIc(p);
      if (p.cizim || deneme < 20) plakaIzle(p.cizim ? 0 : deneme + 1);
    } catch (e) { if (deneme < 20) plakaIzle(deneme + 1); }
  }, 2000);
}

// ---- Plan
const yuklenenFont = new Set();
function fontYukle(aile) {
  if (!aile || yuklenenFont.has(aile)) return;
  yuklenenFont.add(aile);
  const l = document.createElement('link');
  l.rel = 'stylesheet';
  l.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(aile).replace(/%20/g, '+')}:wght@400;500;600;700&display=swap`;
  document.head.appendChild(l);
}
function briefAlanlari(brief) {
  const ist = ['Kime', 'Amaç', 'Kanca fikri', 'Görsel kural', 'Ana nesne', 'İnsan / drama yolu', 'İnsan / karakter yolu', 'Ret ölçütü'];
  const out = [];
  for (const l of String(brief).split('\n')) {
    const m = l.match(/^\s*-\s*\*\*([^*]+?):\*\*\s*(.+)$/);
    if (!m) continue;
    const et = m[1].replace(/\s*\(.*\)\s*$/, '').trim();
    if (ist.some((x) => et.startsWith(x))) out.push([et, sadeMetin(m[2])]);
  }
  return out;
}
function govdePlan() {
  const d = W.d;
  const g = d.gorunus;
  const sec = g?.mod === 'video' ? (g.secenekler || []).find((s) => s.harf === g.secim) : null;
  const brief = d.dosyalar['brief.md'] || '';
  const tek = d.script.learningGoal || '';
  const aile = sec?.yazi?.baslik?.aile;
  fontYukle(aile);
  const r = sec?.renk || {};
  const tekKart = tek ? `<div class="blok"><h3>İzleyicinin aklında kalacak tek cümle</h3><div class="tek-cumle" style="${sec ? `background:${esc(r.kagit || r.arka || '')};color:${esc(r.murekkep || '')};` : 'background:var(--dolgu-2);color:var(--yazi);'}${aile ? `font-family:'${esc(aile)}',Georgia,serif;font-weight:${sec.yazi.baslik.agirlik || 700}` : 'font-family:var(--font-b)'}">${esc(tek)}${sec ? `<small>Seçtiğin görünüşle yazıldı: ${esc(sec.ad)}</small>` : ''}</div></div>` : '';
  // yol modunda Yönetmenlik ve kanca satırları seçilen yoldan gelir: henüz köşeli parantezliyse gösterilmez
  const alanlar = briefAlanlari(brief).filter(([, v]) => !(g?.yolModu && /^\[[^\]]*\]$/.test(v.trim())));
  const uydurma = (brief.match(/\*\*Asla uydurulmayacaklar:\*\*\s*(.+)/) || [])[1];
  const gorunus = !g ? '' : g.yolModu ? yolBolumu(d) : g.mod !== 'video' ? `<div class="blok"><h3>Görünüş</h3><p class="ince">${esc(g.etiket)}: paylaşılan seri; bu seriyi kullanan bütün videolar aynı görünür.</p></div>`
    : !(g.secenekler || []).length ? '<div class="blok"><h3>Görünüş · seçim senin</h3><p class="ince">Görünüş seçenekleri henüz yazılmadı: Claude bu film için birbirinden farklı üç görünüş önerecek.</p></div>'
      : `<div class="blok"><h3>Görünüş · seçim senin</h3>
      <div class="gorunus-uclu">${g.secenekler.map((s) => `<button type="button" class="${g.secim === s.harf ? 'secili' : ''}" data-gorunus-ac aria-label="${s.harf.toUpperCase()} · ${esc(s.ad)}">${g.kareler?.[s.harf] ? `<img src="${kucukUrl(g.kareler[s.harf], 240)}" alt="">` : ''}<span class="harf">${s.harf.toUpperCase()}</span>${g.secim === s.harf ? `<span class="tik-rozet">${ik('tik')}</span>` : ''}</button>`).join('')}</div>
      ${g.secim ? '' : '<p class="ince">Henüz seçilmedi: plan, görünüş seçilmeden onaylanamaz.</p>'}
      <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-gorunus-ac>Üç görünüşü karşılaştır</button>${Object.values(g.tabakalar || {})[0] ? `<button type="button" class="btn cam-btn kucuk" data-buyut="${dosyaUrl(Object.values(g.tabakalar)[0], true)}">Deneme tabakasını aç</button>` : ''}</div></div>`;
  const iddialar = mdTablo(d.dosyalar['kaynaklar.md'], /İddia/i);
  const kol = (r, d_) => Object.keys(r).find((x) => d_.test(x));
  const ik_ = (s) => (s.includes('✅') ? ik('tik', 'yesil') : s.includes('❌') ? ik('kapat', 'kirmizi') : ik('unlem', 'turuncu'));
  const gercek = d.dosyalar['kaynaklar.md'] == null ? `<div class="blok"><h3>Gerçekler</h3><p class="ince">${d.profilDetay.kaynak_zorunlu ? 'kaynaklar.md henüz yok.' : 'Bu film türü kaynak istemiyor.'}</p></div>`
    : `<div class="blok"><h3>Gerçekler · ${iddialar.filter((r) => (r[kol(r, /Durum/i)] || '').includes('✅')).length}/${iddialar.length} iddia doğrulandı</h3>
      ${iddialar.length ? `<div class="grup">${iddialar.map((r) => { const kay = (r[kol(r, /Kaynak/i)] || '').match(/\d+/g) || []; return `<div class="iddia">${ik_(r[kol(r, /Durum/i)] || '')}<span>${esc(sadeMetin(r[kol(r, /İddia/i)] || ''))}</span><em>${kay.length} kaynak</em></div>`; }).join('')}</div>` : '<p class="ince">İddia tablosu boş.</p>'}
      ${uydurma ? `<div class="uydurma-yok">${ik('unlem')}<span><b>Uydurulmayacaklar:</b> ${esc(sadeMetin(uydurma))}</span></div>` : ''}
      <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-duzenle="kaynaklar.md">${ik('kalem')}Kaynakları düzenle</button></div></div>`;
  const vd = d.varlikDurum || {};
  const varlik = `<div class="blok"><h3>Varlıklar · gerçek dosyalar</h3>
    <p class="ince">Logo, ekran görüntüsü, ürün görseli, kayıt. Eksik bir dosya varsa Claude sahtesini çizmez, sana sorar.</p>
    ${d.varliklar.length ? `<div class="cipler">${d.varliklar.map((x) => `<span class="cip">${esc(x)}</span>`).join('')}</div>` : ''}
    ${(vd.eksik || []).length || (vd.onaysiz || []).length || (vd.listesiz || []).length ? `<div class="uyari-kutu">${ik('unlem')}<span>${(vd.eksik || []).length ? `<b>Eksik:</b> ${vd.eksik.map(esc).join(', ')}<br>` : ''}${(vd.onaysiz || []).length ? `<b>Onaysız:</b> ${vd.onaysiz.map(esc).join(', ')}<br>` : ''}${(vd.listesiz || []).length ? `<b>Listede yok:</b> ${vd.listesiz.map(esc).join(', ')}` : ''}</span></div>` : ''}
    <div class="dugmeler"><label class="btn cam-btn kucuk dosya-sec">${ik('atac')}Dosya yükle<input type="file" multiple data-yukle="varlik"></label>${d.dosyalar['varliklar.md'] != null ? `<button type="button" class="btn cam-btn kucuk" data-duzenle="varliklar.md">${ik('kalem')}Listeyi düzenle</button>` : ''}</div></div>`;
  const ilk = g?.yolModu && !g.secim;  // yol seçimi bekliyor: kararın malzemesi (üç yol) kapı kutusundan da önce
  const kataloga = d.katalogaHazir ? `<div class="blok"><h3>Kataloğa ekle</h3><p class="ince">Bu filmin görüntü, hareket ya da ses dilini başka filmler için bir esin kartı yap. Claude filmden bir taslak çıkarır (filmin dosyalarına dokunmaz); sen Kütüphane'de görür, onaylar ya da silersin.</p>
    <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-kataloga ${GENEL?.claudeVar ? '' : 'disabled'}>${ik('arti')}Bu filmin dilini kataloğa ekle</button></div></div>` : '';
  return `${ilk ? gorunus : ''}${kapiKutu(1)}${tekKart}
    ${alanlar.length ? `<div class="blok"><h3>Film</h3><div class="grup">${alanlar.map(([e, v]) => `<div class="grup-satir"><span class="et">${esc(e)}</span><span class="de">${esc(v)}</span></div>`).join('')}</div></div>` : ''}
    ${ilk ? '' : gorunus}
    <div class="blok"><h3>Brief</h3><details class="aac"><summary>${ik('sag')}Brief'in tamamı</summary><div class="durum-md" style="max-height:none">${md(brief)}</div></details><div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-duzenle="brief.md">${ik('kalem')}Brief'i düzenle</button></div></div>
    ${gercek}${veriBlok(d)}${varlik}${goruntuBlok(d)}${takipBlok(d)}${uretimBlok(d)}${kataloga}`;
}

// ---- Canlı veri (4d): gerçek ve güncel bir kaynaktan dondurulmuş anlık görüntü; film o görüntüyle çizilir, rakam uydurulmaz
function veriBlok(d) {
  const V = d.veri;
  if (!V) return '';
  const secili = (V.anliklar || []).find((a) => a.kimlik === V.secili);
  const deger = (x) => `<div class="veri-deger"><span>${esc(x.ad)}</span><b>${esc(x.metin)}${x.birim ? `<small> ${esc(x.birim)}</small>` : ''}</b>${x.pencere || x.zaman_yerel ? `<em>${esc(x.pencere || x.zaman_yerel)}</em>` : ''}</div>`;
  const lisans = V.ticari ? '<span class="cip yesil">Kurum kampanyasında kullanılabilir</span>'
    : V.kullanim === 'ticari_olmayan' ? '<span class="cip turuncu">Yalnız ticari olmayan iş: kampanyada yayınlanmaz</span>'
      : '<span class="cip kirmizi">Lisans kurum kampanyasını kapsamıyor</span>';
  const kare = (a) => {
    const f = a.kareler?.[W.fmt] || Object.values(a.kareler || {})[0];
    return f ? `<button type="button" class="veri-on" data-buyut="${dosyaUrl(f, true)}" aria-label="${esc(a.zaman_yerel)}: kanıt karesi"><img src="${kucukUrl(f, 240)}" alt="" loading="lazy"></button>`
      : '<span class="veri-on bos" aria-hidden="true">kare yok</span>';
  };
  const anlik = (a) => `<div class="veri-anlik ${a.kimlik === V.secili ? 'secili' : ''}">${kare(a)}<div><b>${esc(a.zaman_yerel)}</b>
    <span>${a.degerler.map((x) => `${esc(x.ad)} ${esc(x.metin)}${x.birim ? ` ${esc(x.birim)}` : ''}`).join(' · ')}</span>
    <span class="ince">sha256 ${esc(a.sha)}${a.guncelleme ? ` · kaynak güncellemesi ${esc(a.guncelleme.replace('T', ' ').replace('Z', ' UTC'))}` : ''}</span>
    ${a.kimlik === V.secili ? '<span class="cip yesil">Film bununla çiziliyor</span>' : `<button type="button" class="btn cam-btn kucuk" data-veri-sec="${esc(a.kimlik)}">Bununla çiz</button>`}</div></div>`;
  const sorun = (V.sorunlar || []).filter((x) => x.durum === '❌' || x.durum === '⚠️');
  const K = V.konum || {};
  return `<div class="blok"><h3>Canlı veri</h3>
    <p class="ince">Film gerçek bir kaynaktan alınmış, dondurulmuş bir anlık görüntüyle çizilir; rakam uydurulmaz. “Veriyi yenile” kaynaktan yeni görüntüyü alır, atfı kaynaklara ve yayın paketine yazar, değerlerin göründüğü kareyi yeniden çizer. İstek başarısız olursa film eski görüntüyle kalır ve bu sana söylenir.</p>
    <div class="grup">
      <div class="grup-satir"><span class="et">Kaynak</span><span class="de">${esc(V.kaynak?.kurum || '')} · ${esc(V.kaynak?.ad || '')}</span></div>
      <div class="grup-satir"><span class="et">Konum</span><span class="de">${esc(K.ad || '')}${K.enlem != null ? ` · ${sn(K.enlem, 2)}, ${sn(K.boylam, 2)}` : ''}${K.duzey ? ` · ${esc(K.duzey)} düzeyi` : ''}</span></div>
      <div class="grup-satir"><span class="et">Verinin türü</span><span class="de">${esc(V.tur || '')}</span></div>
    </div>
    ${secili ? `<div class="veri-son"><div class="veri-ust"><b>${secili.kimlik === V.anliklar[0].kimlik ? 'Son görüntü' : 'Seçili görüntü (daha yenisi var)'}: ${esc(secili.zaman_yerel)}</b><span>${esc(V.yasMetni || '')} önce</span></div>
      <div class="veri-degerler">${secili.degerler.map(deger).join('')}</div></div>`
      : `<div class="uyari-kutu">${ik('unlem')}<span>Henüz anlık görüntü yok: “Veriyi yenile” ile kaynaktan ilk görüntüyü al. Görüntü gelene kadar film çizilmez.</span></div>`}
    <div class="veri-atif-kutu"><div><b>Atıf</b> ${esc(V.atif || '')}</div><div><b>Ekranda</b> ${V.ekranda ? `“${esc(V.atif_kisa || '')}” (senin isteğin)` : 'yok (atıf yayın paketinde)'}</div>
      <div><b>Lisans</b> <a href="${esc(V.lisans_url || '#')}" target="_blank" rel="noopener">${esc(V.lisans || '')}</a> ${lisans}</div></div>
    ${sorun.length ? `<div class="uyari-kutu">${ik('unlem')}<span>${sorun.map((x) => esc(x.mesaj)).join('<br>')}</span></div>` : ''}
    <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-veri-cek ${sorun.some((x) => x.durum === '❌') || V.sonraki ? 'disabled' : ''}>${ik('yenile')}Veriyi yenile</button>
      ${V.sonraki ? `<span class="ince">Kaynağın kuralı: yeni veri en erken şu saatte istenir: ${esc(V.sonraki)}. O zamana kadar film bu görüntüyle çizilir.</span>` : ''}</div>
    ${(V.anliklar || []).length ? `<details class="aac" ${(V.anliklar || []).length > 1 ? 'open' : ''}><summary>${ik('sag')}Anlık görüntüler (${V.anliklar.length}) · hangisiyle çizilsin?</summary>
      <div class="veri-anliklar">${V.anliklar.map(anlik).join('')}</div></details>` : ''}</div>`;
}

// ---- Gerçek görüntü (3b, zanaat §2 yol B ve D): kendi çekim, kurum arşivi, açık lisans, stok. Kişi ve rıza yalnız bilgi; çözüm isteğe bağlı (2026-10-27).
const RIZA_AD = {evet: 'rıza var', hayir: 'rıza yok', bilinmiyor: 'rıza bilinmiyor', stok: 'stok lisansı (model izni)'};
const COZUM_AD = {stilize: 'stilize edilecek', gizle: 'yüzler gizlenecek', kullanma: 'kullanılmayacak'};
function goruntuBlok(d) {
  const g = d.goruntu || {varliklar: []};
  const satir = (x) => {
    const on = x.tur === 'video' ? `<video src="${dosyaUrl(x.dosya)}" muted loop playsinline preload="metadata" aria-label="${esc(x.ad)}"></video>`
      : `<img src="${kucukUrl(x.dosya, 240)}" alt="${esc(x.ad)}" loading="lazy">`;
    const kisi = x.kisi === true ? `<span class="cip">Kişi var · ${esc(RIZA_AD[x.riza] || 'rıza bilinmiyor')}${x.cozum ? ` → ${esc(COZUM_AD[x.cozum])}` : ''}</span>`
      : x.kisi === false ? '<span class="cip">Kişi yok</span>' : '<span class="cip">Kişi var mı bilinmiyor</span>';
    const tur = [x.derinlik ? 'derinlik' : '', x.maske ? `maske (${x.maske === 'insan' ? 'insan' : 'nesne'})` : '',
      ...Object.entries(x.kadraj || {}).map(([f, o]) => `kadraj ${f} %${Math.round((o || 0) * 100)}`)].filter(Boolean);
    const karar = x.kisi === true && !['evet', 'stok'].includes(x.riza) ? `<div class="goruntu-karar"><span>İstersen: yüzleri gizle ya da stilize et (seçmezsen görüntü olduğu gibi kullanılır)</span>
      <div class="dugmeler"><button type="button" class="btn cam-btn kucuk ${x.cozum === 'gizle' ? 'secili' : ''}" data-goruntu-cozum="gizle" data-ad="${esc(x.ad)}">Yüzleri gizle</button>
      <button type="button" class="btn cam-btn kucuk ${x.cozum === 'stilize' ? 'secili' : ''}" data-goruntu-cozum="stilize" data-ad="${esc(x.ad)}">Stilize et</button>
      <button type="button" class="btn cam-btn kucuk ${x.cozum === 'kullanma' ? 'secili' : ''}" data-goruntu-cozum="kullanma" data-ad="${esc(x.ad)}">Kullanma</button>
      <button type="button" class="btn cam-btn kucuk" data-goruntu-riza="evet" data-ad="${esc(x.ad)}">Rıza var</button></div></div>` : '';
    return `<div class="uretim-varlik goruntu-varlik"><button type="button" class="uretim-on" data-buyut="${dosyaUrl(x.kontak || x.dosya, true)}" aria-label="${esc(x.ad)}: kontak tabakası">${on}</button>
      <div><b>${esc(x.ad)}</b><span>${esc(x.kaynak)} · ${x.olcu?.en}×${x.olcu?.boy}${x.olcu?.sure ? ` · ${sn(x.olcu.sure)} sn` : ''}${x.kesme ? ` · ${x.kesme} kesme` : ''}</span>
      ${kisi}
      ${x.dokum ? `<span class="ince">Konuşma: “${esc(x.dokum)}”</span>` : ''}
      ${tur.length ? `<span class="ince">${esc(tur.join(' · '))}</span>` : ''}
      <span class="ince">${(x.kullanildigi || []).length ? 'Sahnede kullanılıyor' : 'Henüz sahnede değil'}</span>${karar}</div></div>`;
  };
  return `<div class="blok"><h3>Gerçek görüntü</h3>
    <p class="ince">Kendi çekimin, kurum arşivi ya da açık lisanslı (CC0) görüntü. Gerçek görüntü gerçek kalır: yapay zekâya girmez, kimse yeniden çizilmez; stilizasyon kodla yapılır. Kişi ve rıza senin kararın: istersen yüzleri gizler ya da görüntüyü stilize ederiz.</p>
    ${g.varliklar.length ? `<div class="uretim-liste">${g.varliklar.map(satir).join('')}</div>` : ''}
    <details class="aac goruntu-ekle"><summary>${ik('sag')}Görüntü ekle</summary>
      <div class="goruntu-form">
        <label class="alan-et">Kaynağı<select id="g-kaynak"><option value="kendi">Kendi çekimim</option><option value="arsiv">Kurum arşivi</option><option value="acik">Açık lisanslı (CC0, kamu malı, CC BY)</option></select></label>
        <label class="alan-et">Görüntüde kişi var mı?<select id="g-kisi"><option value="bilinmiyor">Bilmiyorum (Claude tahmin eder)</option><option value="evet">Evet</option><option value="hayir">Hayır</option></select></label>
        <label class="alan-et">Kişilerin rızası alındı mı?<select id="g-riza"><option value="bilinmiyor">Bilmiyorum</option><option value="evet">Evet</option><option value="hayir">Hayır</option></select></label>
        <label class="alan-et">Not<input id="g-not" type="text" maxlength="300" placeholder="Açık lisansta lisans ve bağlantı; arşivde çekim yeri ve tarihi"></label>
      </div>
      <div class="dugmeler"><label class="btn cam-btn kucuk dosya-sec">${ik('atac')}Video ya da fotoğraf seç<input type="file" accept="video/*,image/*" data-goruntu-dosya></label></div>
    </details></div>`;
}

// ---- Kamera takibi (4a, FOOH): telefon çekimine bilgisayarla çizilmiş bir nesne. Kamera Blender'da çözülür ve dondurulur; nesne gölgesini zemine düşürür.
const TAKIP_REHBER = `<ul class="takip-rehber">
  <li><b>5–10 saniye, tek plan.</b> Yakınlaştırma yapma, koşma, ani dönme.</li>
  <li><b>Yavaş yürü, paralaks olsun:</b> yakındaki şeyler uzaktakilerden hızlı kaysın. Yerinde dönerek çekilen görüntü çözülemez.</li>
  <li><b>Pozlama ve odak kilitli:</b> iPhone'da ekrana basılı tut (“AE/AF KİLİDİ”), Android'de Pro kipi.</li>
  <li><b>HDR video kapalı</b> (iPhone: Ayarlar → Kamera → Video Kaydı → HDR Video), 4K ya da 1080p, 30 kare/sn. Sinematik ve Aksiyon kipi kapalı.</li>
  <li><b>Zeminde dokulu yüzey:</b> asfalt, taş, çim, kum. Parlak, düz, tek renk zemin (cilalı taş, su) izlenemez.</li>
  <li><b>Telefonu yere değil ileri tut:</b> nesnenin geleceği boşluk kadrajda kalsın (kadrajın üst yarısında ufuk ve gök).</li>
  <li><b>Kadrajda tanınabilir kişi olmasın</b> (varsa rıza ya da yüz gizleme gerekir); geçen araç ve kalabalık izi bozar.</li>
  <li><b>Işık:</b> bulutlu gün yumuşak gölge verir; güneşliyse gölgelerin hangi yöne düştüğünü not et (nesnenin ışığı ona uydurulur).</li></ul>`;
const TAKIP_ELLE = `<ol class="takip-rehber">
  <li>“Blender'da aç”a bas: izler ve çözüm Blender'ın Hareket İzleme ekranında açılır.</li>
  <li>Kırmızı (hatalı) izleri sil, zeminde ve sabit nesnelerde (direk, taş, köşe) yeni iz ekle: Ctrl + tıkla, sonra “Track Markers” (Ctrl + T).</li>
  <li>Her karede en az 8 iz olsun; özellikle nesnenin duracağı yerin çevresinde.</li>
  <li>İstersen “Solve Camera” ile kendin çöz. Kaydet (⌘S), Blender'ı kapat.</li>
  <li>Buraya dönüp “Elle izlerle yeniden çöz” (stüdyo senin izlerinle çözer) ya da kendin çözdüysen “Elle çözümü aynen al”.</li></ol>
  <p class="ince">Sınır: hızlı yürüyüş, el sallantısı ve hareket bulanıklığı olan bölümlerde otomatik iz kopar (deneme klibinin 5 sn'lik 7 diliminden 2'si baştan sona çözüldü). Çözülmeyen kareler varsa önce çekimi o bölümden önce bitecek şekilde kırp; olmuyorsa elle iz.</p>`;
const YUKSEKLIKLER = [1.0, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 2.0];
function takipGrafik(h, hedef) {
  if (!h.length) return '';
  const W = 600, H = 90, ust = Math.max(2.5, ...h) * 1.1;
  const x = (i) => (i / Math.max(1, h.length - 1)) * W, y = (e) => H - (Math.max(0, e) / ust) * H;
  return `<svg class="takip-grafik" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Kare başına çözüm hatası">
    <line x1="0" x2="${W}" y1="${y(hedef)}" y2="${y(hedef)}" class="hedef"/><polyline points="${h.map((e, i) => `${x(i)},${y(e)}`).join(' ')}"/></svg>`;
}
function takipBlok(d) {
  const T = d.takip;
  if (!T) return '';
  const suren = T.suren ? `<div class="uyari-kutu">${ik('saat')}<span>Sürüyor: ${esc(T.suren)} (ilerleme sağ altta).</span></div>` : '';
  const kilit = T.suren ? 'disabled' : '';
  const sec = (deger) => `<select data-takip-yuk>${YUKSEKLIKLER.map((m) => `<option value="${m}" ${Math.abs(m - deger) < 0.01 ? 'selected' : ''}>${sn(m, 1)} m</option>`).join('')}</select>`;
  const coz = (x) => {
    const iyi = x.hata_px <= x.hedef_px;
    const nesne = x.nesne.length ? `<div class="takip-nesne">${x.nesne.map((f) => `<button type="button" data-buyut="${dosyaUrl(f, true)}"><img src="${kucukUrl(f, 200)}" alt="" loading="lazy"></button>`).join('')}</div>`
      : '<p class="ince">Nesne henüz çekimin üstünde çizilmedi.</p>';
    return `<div class="takip-cozum ${x.ad === T.secili ? 'secili' : ''}">
      <div class="takip-ust"><b>${esc(x.goruntu)}</b> ${iyi ? `<span class="cip yesil">Çözüm hatası ${sn(x.hata_px, 2)} px · hedef ≤ ${sn(x.hedef_px, 0)} px</span>` : `<span class="cip turuncu">Çözüm hatası ${sn(x.hata_px, 2)} px · hedef ≤ ${sn(x.hedef_px, 0)} px</span>`}
        ${x.dondurulmus ? '<span class="cip">Donduruldu</span>' : '<span class="cip kirmizi">Çözüm dosyası değişmiş</span>'}${x.elle ? '<span class="cip">Elle</span>' : ''}
        ${T.cozumler.length > 1 ? (x.ad === T.secili ? '<span class="cip yesil">Film bununla çiziliyor</span>' : `<button type="button" class="btn cam-btn kucuk" data-takip="sec" data-ad="${esc(x.ad)}" ${kilit}>Bununla çiz</button>`) : ''}</div>
      <button type="button" class="takip-onizleme" data-buyut="${dosyaUrl(x.onizleme_url, true)}" aria-label="İzler ve zemin ızgarası"><img src="${dosyaUrl(x.onizleme_url, true)}" alt="" loading="lazy"></button>
      <p class="ince">Noktalar çekimde izlenen yerler (yeşil: hatası 1 pikselden az). Mavi ızgara zemindeki 1 metrelik kareler: yürürken yere yapışık kalmalı, kareler yolda gerçekten 1 m görünmeli. Görünmüyorsa aşağıdan kamera yüksekliğini değiştir.</p>
      ${takipGrafik(x.kare_hata, x.hedef_px)}
      <p class="ince">Kare başına çözüm hatası (yeşil çizgi: 1 px). En kötü kare ${x.en_kotu ? `${x.en_kotu.kare} (${sn(x.en_kotu.hata, 2)} px)` : '—'}.</p>
      <div class="grup">
        <div class="grup-satir"><span class="et">İz</span><span class="de">${x.iz} nokta · zeminde ${x.zemin_nokta} (sapma ${sn((x.zemin_sapma_m || 0) * 100, 1)} cm)</span></div>
        <div class="grup-satir"><span class="et">Mercek</span><span class="de">odak ${sn(x.odak_mm, 1)} mm (36 mm genişliğe göre) · bozulma k1 ${sn(x.bozulma.k1, 3)}</span></div>
        <div class="grup-satir"><span class="et">Ölçek</span><span class="de">kamera ${sn(x.yukseklik_m, 1)} m yükseklikte · yürünen yol ${sn(x.yol_m, 1)} m · ${x.n} kare</span></div>
      </div>
      <div class="dugmeler takip-olcek"><label class="alan-et">Telefon yerden ne kadar yüksekteydi?${sec(x.yukseklik_m)}</label>
        <button type="button" class="btn cam-btn kucuk" data-takip="olcek" data-ad="${esc(x.ad)}" ${kilit}>Ölçeği uygula</button></div>
      <h4>Nesne çekimin üstünde</h4>${nesne}
      <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-takip="nesne" data-ad="${esc(x.ad)}" ${kilit}>${ik('yenile')}Nesneyle dört kare çiz</button></div>
      <details class="aac"><summary>${ik('sag')}Otomatik iz yetmezse: elle iz</summary>${TAKIP_ELLE}
        <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-takip="ac" data-ad="${esc(x.ad)}">Blender'da aç</button>
          <button type="button" class="btn cam-btn kucuk" data-takip="elle" data-kip="iz" data-ad="${esc(x.ad)}" ${kilit}>Elle izlerle yeniden çöz</button>
          <button type="button" class="btn cam-btn kucuk" data-takip="elle" data-kip="cozum" data-ad="${esc(x.ad)}" ${kilit}>Elle çözümü aynen al</button></div></details></div>`;
  };
  const takipte = new Set(T.cozumler.map((x) => x.goruntu));
  const aday = (a) => `<div class="uretim-varlik goruntu-varlik"><button type="button" class="uretim-on" data-buyut="${dosyaUrl(a.kontak || a.dosya, true)}" aria-label="${esc(a.ad)}: kontak tabakası">
      <video src="${dosyaUrl(a.dosya)}" muted loop playsinline preload="metadata" aria-label="${esc(a.ad)}"></video></button>
    <div><b>${esc(a.ad)}</b><span>${a.en}×${a.boy}${a.sure ? ` · ${sn(a.sure)} sn` : ''}</span>
      <div class="dugmeler takip-olcek"><label class="alan-et">Telefonun yerden yüksekliği${sec(1.5)}</label>
        <button type="button" class="btn ana-btn kucuk" data-takip="coz" data-ad="${esc(a.ad)}" ${kilit || (!T.blender ? 'disabled' : '')}>${takipte.has(a.ad) ? 'Yeniden çöz' : 'Kamerayı çöz'}</button></div>
      <span class="ince">~5–8 dk; bilgisayar bu sırada yavaşlar.</span></div></div>`;
  return `<div class="blok"><h3>Kamera takibi · gerçek yerde imkânsız nesne</h3>
    <p class="ince">Telefonla çektiğin gerçek bir yere bilgisayarla çizilen bir nesne yerleşir (ör. yolun ortasında süzülen dev bir kumbara). Blender çekimdeki noktaları izler; kameranın nasıl yürüdüğünü, zemini ve ölçeği bulur. Çözüm bir kez dondurulur, nesne her karede aynı yerde durur ve gölgesini zemine düşürür.</p>
    ${T.blender ? '' : `<div class="uyari-kutu">${ik('unlem')}<span>Nesne Blender'da çizilir: kamera takibi Blender filminde çalışır.</span></div>`}
    ${T.cizer === 'eevee' ? `<div class="uyari-kutu">${ik('unlem')}<span>Bu film EEVEE ile çiziliyor: gölge yakalayıcı yalnız Cycles'ta var, nesnenin gölgesi zemine düşmez. Gölge gerekiyorsa çizeri Cycles yap.</span></div>` : ''}
    ${suren}${T.cozumler.map(coz).join('')}
    ${T.adaylar.length ? `<h4>Çekimler</h4><div class="uretim-liste">${T.adaylar.map(aday).join('')}</div>` : '<p class="ince">Önce çekimi ekle: Gerçek görüntü → Görüntü ekle.</p>'}
    <details class="aac" ${T.cozumler.length ? '' : 'open'}><summary>${ik('sag')}Nasıl çekmeli?</summary>${TAKIP_REHBER}</details></div>`;
}

// ---- Yapay zekâ üretimleri (Magnific, 3a): film başına kredi sınırı, harcanan, dondurulmuş varlıklar
const kredi = (n) => Number(n || 0).toLocaleString('tr-TR');
/** Magnific anlatıcı parçaları tek satır: kaç parça, kaçı bugünkü senaryoda, toplam kredi. */
function anlatimSatiri(A) {
  if (!A.length) return '';
  const kul = A.filter((x) => (x.kullanildigi || []).length).length;
  return `<div class="uretim-varlik"><span class="uretim-on" aria-hidden="true">${ik('ses')}</span><div><b>Anlatım · ${esc(A[0].model || 'Magnific')}</b>
    <span>${A.length} parça · ${kredi(A.reduce((s, x) => s + (x.kredi || 0), 0))} kredi</span><span class="ince">${kul === A.length ? 'Hepsi bugünkü senaryoda' : `${kul} parça bugünkü senaryoda; ${A.length - kul} eski parça silinebilir`}</span></div></div>`;
}
function uretimBlok(d) {
  const u = d.uretim || {};
  const M = GENEL?.magnific || {};
  if (!u.var && !M.kurulu) return '';  // Magnific bağlı değil ve bu filmde üretim yok (ör. Magnific bağlı olmayan kurulum): blok hiç görünmez
  const oran = u.sinir ? Math.min(1, u.harcanan / u.sinir) : 1;
  const varlik = (x) => {
    const on = x.tur === 'video' ? `<video src="${dosyaUrl(x.dosya)}" muted loop playsinline preload="metadata" aria-label="${esc(x.ad)}"></video>`
      : /\.(png|jpe?g|webp)$/i.test(x.dosya) ? `<img src="${kucukUrl(x.dosya, 240)}" alt="${esc(x.ad)}" loading="lazy">` : `<span class="uretim-tur">${esc(x.tur)}</span>`;
    const yer = (x.kullanildigi || []).map((y) => y.replace(/^src\/[^/]+\//, '').replace(/^hf\/[^/]+\//, '').replace(/^blender\/[^/]+\//, ''));
    return `<div class="uretim-varlik"><button type="button" class="uretim-on" data-buyut="${dosyaUrl(x.dosya, true)}" aria-label="${esc(x.ad)}: büyüt">${on}</button>
      <div><b>${esc(x.ad)}</b><span>${esc(x.model || x.tur)} · ${kredi(x.kredi)} kredi${x.olcu?.en ? ` · ${x.olcu.en}×${x.olcu.boy}` : ''}${x.olcu?.sure ? ` · ${sn(x.olcu.sure)} sn` : ''}</span>
      <span class="ince">${yer.length ? `Kullanıldığı yer: ${esc(yer.join(', '))}` : 'Henüz sahnede değil'}</span>
      ${x.etiket ? '<span class="cip turuncu">Ekranda etiket gerekli</span>' : ''}</div></div>`;
  };
  return `<div class="blok"><h3>Yapay zekâ üretimleri · Magnific</h3>
    <div class="kredi-gosterge ${u.harcanan > u.sinir ? 'asti' : ''}"><div class="kredi-ust"><b>Kredi: ${kredi(u.harcanan)} / ${kredi(u.sinir)}</b><span>kalan ${kredi(u.kalan)}</span></div>
      <div class="kredi-cubuk" role="meter" aria-label="Harcanan kredi" aria-valuemin="0" aria-valuemax="${u.sinir}" aria-valuenow="${u.harcanan}"><i style="width:${(oran * 100).toFixed(1)}%"></i></div></div>
    <p class="ince">${M.kurulu ? 'Claude gerçekçi plakaları (mekân, nesne, metafor, etiketli canlandırma) yalnız bu sınırın içinde üretir; her üretimden önce bedeli ücretsiz ölçer, sınır aşılacaksa durur ve sana sorar. Gerçek yararlanıcı, gerçek olay ve gerçek kişi yapay zekâyla üretilmez.'
      : 'Magnific bu bilgisayarda bağlı değil: yeni üretim yapılamaz; var olan dosyalar filmde kalır.'}</p>
    ${(u.varliklar || []).length ? `<div class="uretim-liste">${u.varliklar.filter((x) => x.tur !== 'anlatim').map(varlik).join('')}${anlatimSatiri(u.varliklar.filter((x) => x.tur === 'anlatim'))}</div>` : ''}
    <div class="kredi-sinir"><label class="alan-et" for="kredi-siniri">Bu filmin kredi sınırı<input id="kredi-siniri" type="number" inputmode="numeric" min="0" max="240000" step="500" value="${u.sinir ?? ''}"></label>
      <button type="button" class="btn cam-btn kucuk" data-kredi-kaydet>Sınırı kaydet</button></div></div>`;
}

// ---- Kataloğa ekle: filmin dili katalogda yeni bir esin kartı olur (taslak; kullanıcı Kütüphane'de onaylar ya da siler)
const KATALOGA = {gorsel: ['Görüntü', 'renk, yazı, doku, ışık'], animasyon: ['Hareket', 'kurallar, kamera, geçiş, tempo'], ses: ['Ses', 'müzik tarifi, efekt ailesi, miks']};
function katalogaAdi(d) {
  const s = slug(String(d.baslik || d.id).replace(/['’]/g, '')).replace(/_/g, '-').replace(/^[^a-z]+/, '').slice(0, 30).replace(/-+$/, '');
  return s.length >= 3 ? s : `film-${slug(d.id).replace(/_/g, '-')}`.slice(0, 30);
}
function katalogaLevha() {
  const d = W.d;
  const g = d.gorunus;
  const sec = g?.mod === 'video' ? (g.secenekler || []).find((s) => s.harf === g.secim) : null;
  const kare = (g?.secim && (g.karelerFmt?.[W.fmt]?.[g.secim] || g.kareler?.[g.secim])) || (d.kareler[W.fmt] || [])[0]?.yol || null;
  const film = [...d.teslim].reverse().find((t) => t.format === W.fmt)?.dosya || d.kaba[W.fmt] || null;
  const mix = d.sesDosyalari?.['mix.wav'];
  const renkler = sec ? Object.values(sec.renk || {}).filter((c) => typeof c === 'string').slice(0, 5) : [];
  const kart = (tur, gorsel, alt) => `<div class="raf-kart"><button type="button" class="raf-sec" role="radio" aria-checked="${tur === 'gorsel'}" data-kataloga-tur="${tur}"><span class="raf-gorsel">${gorsel}</span><span class="raf-ad">${KATALOGA[tur][0]}<small>${alt}</small></span></button></div>`;
  levhaAc(`<div class="levha-bas"><div><h2 id="levha-baslik">Bu filmin dilini kataloğa ekle</h2><p>${esc(d.baslik)} filminin bir dili katalogda yeni bir esin kartı olur. Claude filmi okur ve ölçer, bir taslak çıkarır; filme özgü olanı (metin, logo, karakter) taşımaz ve filmin dosyalarına dokunmaz. Taslak Kütüphane'de senin onayını bekler.</p></div>${kapatDugme}</div>
    <form class="yeni-form" id="kataloga-form" style="gap:16px">
      <div class="kataloga-turler" role="radiogroup" aria-label="Hangi dil">
        ${kart('gorsel', kare ? `<img src="${kucukUrl(kare, 360)}" alt="">` : ik('gorsel'), `${KATALOGA.gorsel[1]}${renkler.length ? `</small><span class="renkler kucuk-renk">${renkler.map((c) => `<span style="background:${esc(c)}"></span>`).join('')}</span><small>` : ''}`)}
        ${kart('animasyon', film ? `<video src="${dosyaUrl(film)}" muted loop autoplay playsinline preload="metadata"></video>` : ik('hareket'), KATALOGA.animasyon[1])}
        ${kart('ses', `${ik('ses')}`, `${KATALOGA.ses[1]}${d.bpm ? ` · ${Math.round(d.bpm)} BPM` : ''}`)}
      </div>
      ${mix ? `<div class="kataloga-dinle">${calDugme(`kataloga:${W.id}`, dosyaUrl(mix), 'Filmin sesini dinle', 'kucuk-cal')}<span class="ince">Filmin sesini dinle (miks)</span></div>` : ''}
      <div class="form-izgara"><label class="alan-et" for="kataloga-ad">Kartın adı <small>küçük harf ve tire</small><input id="kataloga-ad" value="${esc(katalogaAdi(d))}" autocomplete="off"></label>
        <label class="alan-et" for="kataloga-not">Not <small>isteğe bağlı</small><input id="kataloga-not" placeholder="ör. özellikle ışığı ve geçişleri al"></label></div>
      <div class="levha-alt"><div class="alt-sol"><p>Claude arka planda çalışır; ilerlemesi sağ altta görünür. Önizleme çizilince taslak Kütüphane'de görünür.</p></div><button type="button" class="btn cam-btn buyuk" data-kapat>Vazgeç</button><button type="submit" class="btn ana-btn buyuk">${ik('claude')}Taslağı çıkar</button></div>
    </form>`, 'dar');
  const L = $('#levha');
  $$('[data-kataloga-tur]', L).forEach((b) => b.addEventListener('click', () => $$('[data-kataloga-tur]', L).forEach((x) => x.setAttribute('aria-checked', String(x === b)))));
  $$('[data-cal]', L).forEach((b) => b.addEventListener('click', () => sesCal(b.dataset.cal, b.dataset.src)));
  $('#kataloga-ad', L).addEventListener('input', (e) => { e.target.value = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'); });
  $('#kataloga-form', L).addEventListener('submit', async (e) => {
    e.preventDefault();
    const tur = $('[data-kataloga-tur][aria-checked="true"]', L)?.dataset.katalogaTur;
    const ad = $('#kataloga-ad', L).value.trim();
    if (!/^[a-z][a-z0-9-]{2,30}$/.test(ad)) return bildir('Kartın adı: küçük harf, rakam ve tire (en az 3 harf, harfle başlar).');
    try {
      const r = await api.post('/api/katalog/filmden', {id: W.id, tur, ad, not: $('#kataloga-not', L).value.trim()});
      levhaKapat();
      bildir(`Claude bu filmin ${KATALOGA[tur][0].toLocaleLowerCase('tr-TR')} dilini çıkarıyor; taslak Kütüphane → ${KAT_AD[tur]} sayfasında görünecek.`, 6000);
      isIzle(r.is);
    } catch (er) { bildir(er.message, 6000); }
  });
}

// ---- Plan · üç yol (gorunus.json → yol_modu): her seçenek ayrı bir fikirdir, kendi yöntemi, kanca karesi ve görünüşüyle
/** secim: yol bekleniyor · tamamlaniyor: Claude planı seçilen yolda yazıyor · eksik: seçildi ama plan tamamlanmadı · tamam */
function yolDurumu(d = W.d) {
  const g = d.gorunus;
  if (!g?.yolModu) return null;
  if (!g.secim) return 'secim';
  if (claudeCalisiyor() && d.basit?.claude?.asama === 'plan_tamamla') return 'tamamlaniyor';
  return d.kapilar[1].eksik.some((e) => !e.startsWith('Senin onayın')) ? 'eksik' : 'tamam';
}
const yolKilitli = (d = W.d) => !!d.kapilar[1].onay || claudeCalisiyor();  // plan onaylandıysa ya da Claude çalışıyorsa yol panelden değişmez
const yolFmt = (d = W.d) => (d.formatlar.includes(W.yolFmt) ? W.yolFmt : d.formatlar[0]);
const yolKaresi = (g, harf, f) => g.karelerFmt?.[f]?.[harf] || g.kareler?.[harf] || null;
function yolAlanlari(y, hepsi = false) {
  const L = hepsi
    ? [['Kanca', y.kanca], ['Üretim kuralı', y.kural], ['Olağanüstü an', y.olaganustu_an], ['İnsan / karakter', y.insan_yolu], ['Neden akılda kalır', y.neden_akilda_kalir], ['Risk', y.risk], ['Üretim', y.uretim]]
    : [['Üretim kuralı', y.kural], ['Olağanüstü an', y.olaganustu_an], ['İnsan / karakter', y.insan_yolu], ['Üretim', y.uretim]];
  if (y.kredi_tahmini) L.push(['Kredi tahmini', `~${Number(y.kredi_tahmini).toLocaleString('tr-TR')} kredi (Magnific)`]);
  return `<dl class="yol-alan">${L.filter(([, v]) => v).map(([e, v]) => `<div><dt>${e}</dt><dd>${esc(sadeMetin(v))}</dd></div>`).join('')}</dl>`;
}
function yolSecDugme(s, g, d = W.d) {
  const secili = g.secim === s.harf;
  return `<button type="button" class="btn ${secili ? 'cam-btn' : 'ana-btn'}" data-yol-sec="${s.harf}" ${secili || yolKilitli(d) ? 'disabled' : ''}>${secili ? `${ik('tik')}Seçili yol` : 'Bu yolu seç'}</button>`;
}
function yolKart(s, g, {genis = false} = {}) {
  const y = s.yol || {};
  const f = yolFmt();
  const kare = yolKaresi(g, s.harf, f);
  const secili = g.secim === s.harf;
  const konsept = g.konseptler?.[s.harf];  // Magnific konsept karesi: yolun gerçekçi plakalarının vaadi (kanca karesi kodla çizilir)
  return `<article class="yol-kart ${secili ? 'secili' : ''} ${fmtOran(f) > 1 ? 'yatay' : ''} ${genis ? 'genis' : ''}">
    <button type="button" class="yol-kare ${!genis && yolOnizleme()?.harf === s.harf ? 'gosterilen' : ''}" ${!kare ? 'disabled' : genis ? `data-buyut="${dosyaUrl(kare, true)}"` : `data-yol-goster="${s.harf}"`} style="aspect-ratio:${fmtOran(f)}" aria-label="${s.harf.toUpperCase()} yolunun kanca karesini ${genis ? 'büyüt' : 'sahnede göster'}">${kare ? `<img src="${kucukUrl(kare, genis ? 900 : 480)}" alt="${esc(y.ad || s.ad)}: kanca karesi" loading="lazy">` : ''}<span class="harf">${s.harf.toUpperCase()}</span>${secili ? `<span class="tik-rozet">${ik('tik')}</span>` : ''}</button>
    <div class="yol-bas">
      <h4>${esc(y.ad || s.ad)}</h4>
      <p class="yol-tek">${esc(sadeMetin(y.tek_cumle || s.fikir))}</p>
      ${y.yontem ? `<div class="cipler"><span class="cip yontem-cip" title="Yöntem">${esc(y.yontem)}</span></div>` : ''}
    </div>
    ${konsept ? `<button type="button" class="yol-konsept" data-buyut="${dosyaUrl(konsept, true)}" aria-label="${s.harf.toUpperCase()} yolunun konsept karesini büyüt"><img src="${kucukUrl(konsept, genis ? 480 : 240)}" alt="" loading="lazy"><span>Konsept karesi · yapay zekâ (Magnific)</span></button>` : ''}
    ${yolAlanlari(y, genis)}
    ${genis ? `<div class="yol-gorunus"><span class="ince">Görünüş: ${esc(s.ad)}</span><div class="renkler">${Object.values(s.renk || {}).filter((c) => typeof c === 'string').slice(0, 5).map((c) => `<span style="background:${esc(c)}" title="${esc(c)}"></span>`).join('')}</div></div>` : ''}
    <div class="dugmeler">${yolSecDugme(s, g)}</div></article>`;
}
function yolFmtSekme(d = W.d) {
  if (d.formatlar.length < 2) return '';
  const f = yolFmt(d);
  return `<div class="yol-fmt" role="tablist" aria-label="Kanca karesinin formatı">${d.formatlar.map((x) => `<button type="button" role="tab" aria-selected="${x === f}" class="${x === f ? 'aktif' : ''}" data-yol-fmt="${x}">${ik(FORMAT_IK[x] || 'kare')}${fmtEtiket(x)}</button>`).join('')}</div>`;
}
function fikirHavuzu(g) {
  if (!g.fikirler) return '';
  const T = mdTablo(g.fikirler, /Fikir/i);
  if (!T.length) return `<details class="aac"><summary>${ik('sag')}Fikir havuzu</summary><div class="durum-md" style="max-height:none">${md(g.fikirler)}</div></details>`;
  const bas = Object.keys(T[0]);
  const not = (g.fikirler.match(/^>\s*(.+)$/m) || [])[1];
  return `<details class="aac"><summary>${ik('sag')}Fikir havuzu · ${T.length} fikir</summary>
    ${not ? `<p class="ince">${esc(sadeMetin(not))}</p>` : ''}
    <div class="fikir-tablo" role="region" aria-label="Fikir havuzu" tabindex="0"><table><thead><tr>${bas.map((b) => `<th scope="col">${esc(b)}</th>`).join('')}</tr></thead>
    <tbody>${T.map((r) => { const s = /→/.test(r[bas[0]] || ''); return `<tr class="${s ? 'secilen' : ''}">${bas.map((b) => `<td>${esc(sadeMetin(r[b]))}</td>`).join('')}</tr>`; }).join('')}</tbody></table></div>
    <p class="ince">“→ A” işaretli satırlar üç yola dönüşen fikirler. Puanlar 1–5: şaşırtma, netlik, yapılabilirlik, etik.</p></details>`;
}
function yolBolumu(d) {
  const g = d.gorunus;
  const S = (g.secenekler || []).filter((s) => s.yol);
  if (!S.length) return '<div class="blok"><h3>Üç yol · seçim senin</h3><p class="ince">Yollar henüz yazılmadı: Claude bu film için yöntem olarak birbirinden farklı üç fikir önerecek.</p></div>';
  const dur = yolDurumu(d);
  const tabaka = g.tabakalar?.[yolFmt(d)] || Object.values(g.tabakalar || {})[0];
  const secilen = S.find((s) => s.harf === g.secim);
  const not = d.basit?.durumMd;
  const ust = {
    secim: not ? `<details class="aac yol-not" open><summary>${ik('sag')}Claude'un notu ve önerisi</summary><div class="durum-md">${md(not)}</div></details>` : '',
    tamamlaniyor: `<div class="yol-ilerleme" role="status"><b class="parilti">Claude planı bu yolda tamamlıyor</b><span>Brief'in yönetmenlik bölümü, senaryo ve denetim. Bitince Senaryo adımı ve plan onayı açılır.</span></div>`,
    eksik: `<div class="uyari-kutu">${ik('unlem')}<span>Yolu seçtin ama plan bu yolda henüz tamamlanmadı (senaryo denetimi temiz değil).${claudeCalisiyor() ? '' : ' Claude tamamlasın:'}</span></div>${claudeCalisiyor() || !GENEL?.claudeVar ? '' : '<div class="dugmeler"><button type="button" class="btn ana-btn kucuk" data-yol-tamamla>Claude planı bu yolda tamamlasın</button></div>'}`,
    tamam: `<p class="ince">Plan bu yolda yazıldı. Senaryo adımına bak; içine sinerse planı onayla.${d.kapilar[1].onay ? '' : ' Başka bir yola geçersen plan o yolda yeniden kurulur.'}</p>`,
  }[dur];
  const kartlar = dur === 'secim' ? S.map((s) => yolKart(s, g)).join('')
    : `${secilen ? yolKart(secilen, g) : ''}${S.length > 1 ? `<details class="aac"><summary>${ik('sag')}Öteki ${S.length - 1} yol</summary><div class="yol-liste">${S.filter((s) => s !== secilen).map((s) => yolKart(s, g)).join('')}</div></details>` : ''}`;
  return `<div class="blok yol-blok"><h3>${dur === 'secim' ? 'Üç yol' : `Seçilen yol · ${esc(g.secim.toUpperCase())}`}</h3>${dur === 'secim' ? '' : ust}${yolFmtSekme(d)}
    <div class="yol-liste">${kartlar}</div>${dur === 'secim' ? ust : ''}
    <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-yol-ac>Yolları karşılaştır</button>${tabaka ? `<button type="button" class="btn cam-btn kucuk" data-buyut="${dosyaUrl(tabaka, true)}">Deneme tabakasını aç</button>` : ''}${d.kapilar[1].onay ? '' : '<button type="button" class="btn cam-btn kucuk" data-yol-iste>Başka yollar iste</button>'}</div>
    ${fikirHavuzu(g)}</div>`;
}
/** Karşılaştırma levhası: üç yol yan yana, büyük kanca kareleri ve bütün alanlar. */
function yolLevha() {
  const d = W.d;
  const g = d.gorunus;
  const S = (g.secenekler || []).filter((s) => s.yol);
  levhaAc(`<div class="levha-bas"><div><h2 id="levha-baslik">Üç yol</h2><p>Her yol ayrı bir fikir: kendi yöntemi, üretim kuralı, kanca karesi ve görünüşü. Claude üçünü de önerir, önerisini durum notunda gerekçesiyle söyler; seçim senin. Seçince Claude planı o yolda tamamlar.</p></div>${kapatDugme}</div>
    ${yolFmtSekme(d)}<div class="yol-izgara">${S.map((s) => yolKart(s, g, {genis: true})).join('')}</div>`);
  const L = $('#levha');
  $$('[data-yol-sec]', L).forEach((b) => b.addEventListener('click', () => yolSec(b, b.dataset.yolSec)));
  $$('[data-yol-fmt]', L).forEach((b) => b.addEventListener('click', () => { W.yolFmt = b.dataset.yolFmt; yolLevha(); denetciCiz({kaydirma: true}); }));
}
async function yolSec(b, harf) {
  const g = W.d.gorunus;
  const s = (g.secenekler || []).find((x) => x.harf === harf);
  const yeniden = yolDurumu() !== 'secim';
  const not = await onaySor(b, {soru: `${harf.toUpperCase()} · ${esc(s?.yol?.ad || '')}: Claude planı bu yolda tamamlar (brief ve senaryo; birkaç dakika).${yeniden ? ' Önceki yolda yazılan plan bu yolda yeniden kurulur.' : ''}`, evet: 'Bu yolu seç'});
  if (not === null) return;
  try {
    await api.post(`/api/video/${W.id}/gorunus`, {secim: harf});
    bildir('Yol seçildi; Claude planı bu yolda tamamlıyor.');
    levhaKapat();
    genelTazele(); await yenidenYukle();
  } catch (e) { bildir(e.message, 6000); }
}

// ---- Senaryo
function vurusMetinHtml(v) {
  const ana = trKucuk(v.shot.anahtar || '');
  let isaretli = false;
  if (!v.kelimeler.length) return esc(v.metin);
  return v.kelimeler.map((w) => {
    const n = W.kelime.findIndex((k) => k.v === v.i && k.b === w[1]);
    let m = esc(w[0]);
    if (!isaretli && ana && trKucuk(w[0]).startsWith(ana)) { m = `<mark>${m}</mark>`; isaretli = true; }
    return `<span class="k" data-k="${n}">${m}</span>`;
  }).join(' ');
}
function gecisMetni(g) {
  if (!g || typeof g !== 'object') return g;
  const p = Object.entries(g.param || {}).map(([k, x]) => `${k} ${JSON.stringify(x)}`).join(', ');
  return [`${g.gl} (gölgelendirici geçişi)`, `${g.kare} kare`, p, g.kesim ? `kesim: ${g.kesim}` : '', g.neden || ''].filter(Boolean).join(' · ');
}
function sozlesmeHtml(v) {
  const s = {...v.shot, gecis: gecisMetni(v.shot.gecis)};
  const r = (et, m) => (m ? `<div><b>${et}</b>${esc(m)}</div>` : '');
  return `<div class="sozlesme">${r(W.d.anlatim ? 'Anahtar kelime' : 'Olay işareti', s.anahtar || s.isaret)}${r('Plan', s.plan)}${r('Görsel olay', s.olay)}${r('Giriş', s.giris)}${r('Çıkış', s.cikis)}${r('Geçiş · sonrakine ne taşınır', s.gecis)}${r('Ses', s.ses)}${s.amac ? `<div class="neden"><b>Neden var?</b>${esc(s.amac)}</div>` : ''}</div>`;
}
const DURUM_IK = (s) => (s.includes('❌') ? ik('kapat', 'kirmizi') : s.includes('⚠') ? ik('unlem', 'turuncu') : s.includes('✅') ? ik('tik', 'yesil') : ik('goz'));
/** Karma film (6b): vuruşu hangi motorun çizdiği (sahnelerin pencerelerinden). Tek motorlu filmde rozet yok. */
const motorRozeti = (id) => (W.d.sahneMotor?.[id] || []).map((m) => `<span class="cip${m.motor === 'remotion' ? '' : ' claude'}" title="${m.ad ? `sahne ${esc(m.ad)}` : 'Remotion birleştirici'}">${esc(MOTOR_AD[m.motor] || m.motor)}</span>`).join('');
function govdeSenaryo() {
  const d = W.d;
  const lint = d.lint || [];
  return `${kapiKutu(2)}
    <div class="vurus-liste" id="vurus-liste">${W.vurus.map((v) => `
      <div class="vurus-satir" data-vs="${v.i}" style="--renk:${v.renk}">
        <button type="button" data-vurus="${v.i}" aria-expanded="${W.acikV === v.i}"><span class="adim-et"><i></i>${esc(v.adim)}</span>${motorRozeti(v.id)}<span class="vurus-metin">${vurusMetinHtml(v)}</span><span class="vurus-zaman">${v.bas != null ? tc(v.bas).slice(3) : ''}</span></button>
        ${W.acikV === v.i ? sozlesmeHtml(v) : ''}
      </div>`).join('') || '<p class="ince">Senaryo henüz yazılmadı.</p>'}</div>
    <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-senaryo-duzenle>${ik('kalem')}Senaryoyu düzenle</button></div>
    ${d.karma ? `<div class="blok"><h3>Karma film · sahneler ve motorlar</h3><p class="ince">Her sahne içeriğine en uygun motorla çizilir; Remotion birleştirir. Listede olmayan zaman Remotion'da.</p>
      <div class="grup">${d.karma.map((s) => `<div class="olcum-satir">${ik('katman')}<span><b>${esc(s.ad)}</b> · ${esc(MOTOR_AD[s.motor] || s.motor)}${s.cizer ? ` · ${esc(s.cizer.toUpperCase())}` : ''}${s.saydam ? ' · saydam' : ''}</span><span>${sn(s.bas, 2)}–${sn(s.son, 2)} sn</span></div>`).join('')}</div></div>` : ''}
    <div class="blok"><h3>Denetim</h3>${lint.length ? `<div class="grup">${lint.map((l) => `<div class="olcum-satir">${DURUM_IK(l.durum)}<span>${esc(l.mesaj)}</span><span></span></div>`).join('')}</div>` : '<p class="ince">Denetim çıktısı yok.</p>'}</div>
    <div class="blok"><h3>Olay işaretleri${d.bpm ? ` · müzik ${Math.round(d.bpm)} BPM` : ''}</h3>
      ${d.cueHata ? `<div class="uyari-kutu">${ik('unlem')}<span>${esc(d.cueHata)}</span></div>` : ''}
      <p class="ince">Görüntü ve ses bu tek listeden zamanlanır: bir kelimeye, bir müzik vuruşuna ya da gerekçeli bir saniyeye bağlanır.</p>
      ${W.isaret.length ? `<div class="cipler">${W.isaret.map((c) => `<button type="button" class="cip" data-git="${c.t}">${esc(c.ad)} · ${sn(c.t, 2)}</button>`).join('')}</div>` : '<p class="ince">Henüz çözülmüş işaret yok.</p>'}
      ${d.dosyalar['cues.json'] != null ? `<div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-duzenle="cues.json">${ik('kalem')}cues.json'u düzenle</button></div>` : ''}</div>`;
}
function senaryoVurgula(kaydir) {
  $$('.vurus-satir').forEach((r) => r.classList.toggle('simdi', +r.dataset.vs === W.aktifV));
  if (!video.paused || kaydir) {
    const r = $(`.vurus-satir[data-vs="${W.aktifV}"]`);
    const g = $('#den-govde');
    if (r && g) {
      const ust = g.scrollTop + r.getBoundingClientRect().top - g.getBoundingClientRect().top - 70;
      if (Math.abs(g.scrollTop - ust) > 40) g.scrollTo({top: ust, behavior: video.paused ? 'auto' : 'smooth'});
    }
  }
}
function kelimeVurgula(ki) {
  const gercek = ki >= 0 ? ki : -1 - ki;
  $$('.vurus-metin .k').forEach((el) => {
    const n = +el.dataset.k;
    el.classList.toggle('soylendi', n <= gercek && W.aktifK !== -1);
    el.classList.toggle('su', n === ki);
  });
}

// ---- Kareler (+ ses)
function govdeKareler() {
  const d = W.d;
  const L = d.kareler[W.fmt] || [];
  const secilen = [];
  if (L.length) secilen.push({k: L[0], ad: 'İlk kare', alt: 'döngü başı'});
  for (const v of W.vurus.filter((x) => x.bas != null)) { const k = vurusKaresi(v); if (k) secilen.push({k, ad: `${v.id} · ${v.adim}`, renk: v.renk, v: v.i}); }
  if (L.length > 1) secilen.push({k: L[L.length - 1], ad: 'Son kare', alt: 'poster adayı'});
  const s = d.ses || {};
  const oynat = Object.entries(d.sesDosyalari || {});
  const tem = d.temsili[W.fmt];
  return `${kapiKutu(3)}
    ${secilen.length ? `<div class="kare-izgara" id="kare-izgara">${secilen.map((x) => `<button type="button" data-git="${x.k.t}" data-kv="${x.v ?? ''}" style="--renk:${x.renk || 'transparent'}"><span class="kg"><img src="${kucukUrl(x.k.yol, 240)}" alt="" loading="lazy"></span><small><b>${esc(x.ad)}</b>${tc(x.k.t).slice(3)}${x.alt ? ` · ${x.alt}` : ''}</small></button>`).join('')}</div>` : '<p class="ince">Henüz kare yok: temsilî kareler ya da inceleme üretilince burada görünür.</p>'}
    ${tem ? `<div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-buyut="${dosyaUrl(tem, true)}">Temsilî tabakayı aç (${fmtEtiket(W.fmt)})</button></div>` : ''}
    <details class="aac" ${oynat.length ? '' : 'open'}><summary>${ik('sag')}Ses ve müzik</summary>
      <div class="yeni-form" style="gap:12px" id="ses-form">
        <div class="form-izgara">
          <label class="alan-et" for="ses-kaynak">Anlatıcı<select id="ses-kaynak">${[['edge', 'Yapay ses (Edge, ücretsiz)'], ['kayit', 'Kendi kaydım'], ...(GENEL?.magnific?.kurulu || s.kaynak === 'magnific' ? [['magnific', 'Magnific · Serkan Yıldırım (yapay zekâ, kredi)']] : []), ['opencode', 'OpenCode (deneysel)'], ['yok', 'Anlatım yok']].map(([k, a]) => `<option value="${k}" ${k === s.kaynak ? 'selected' : ''}>${a}</option>`).join('')}</select></label>
          <label class="alan-et" for="ses-voice" data-kaynak-alan="edge">Ses<select id="ses-voice">${['tr-TR-EmelNeural', 'tr-TR-AhmetNeural', 'en-US-AriaNeural', 'en-US-GuyNeural'].map((x) => `<option ${x === s.voice ? 'selected' : ''}>${x}</option>`).join('')}</select></label>
          <label class="alan-et" for="ses-rate" data-kaynak-alan="edge">Hız <small>ör. +8%</small><input id="ses-rate" value="${esc(s.rate || '+0%')}"></label>
          <label class="alan-et" for="ses-muzik">Müzik dosyası <small>public/${esc(d.id)}/ altında</small><input id="ses-muzik" value="${esc(s.muzik || '')}" placeholder="muzik.wav"></label>
          <label class="alan-et" for="ses-muzik-db">Müzik seviyesi (dB) <small>boş: otomatik</small><input id="ses-muzik-db" value="${s.muzik_db ?? ''}"></label>
        </div>
        <p class="ince" data-kaynak-alan="magnific">${d.anlatim ? (d.anlatim.eksik ? `Magnific anlatımı: ${d.anlatim.parca - d.anlatim.eksik}/${d.anlatim.parca} parça hazır. Eksik ${d.anlatim.eksik} parçayı (${d.anlatim.karakter} karakter, yaklaşık ${Math.ceil(d.anlatim.karakter / 85) * 18} kredi) Claude üretim turunda üretir; şimdi istersen Claude'a “Anlatımı Magnific sesiyle üret” de.` : `Magnific anlatımı hazır: ${d.anlatim.parca} parça dondurulmuş.`) : 'Kaydedince Claude anlatımı Magnific sesiyle (Serkan Yıldırım) üretir; her cümle bir kez, kredi sınırına sayılır.'}${GENEL?.anlaticiOrnek ? `<audio src="${dosyaUrl(GENEL.anlaticiOrnek, true)}" controls preload="none" style="width:100%;height:32px;margin-top:6px" aria-label="Serkan Yıldırım örneği"></audio>` : ''}</p>
        <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" id="ses-kaydet">Ses ayarlarını kaydet</button><label class="btn cam-btn kucuk dosya-sec" data-kaynak-alan="kayit">${ik('atac')}Kaydını yükle<input type="file" accept=".wav,.m4a,.mp3,.aiff,.flac" data-yukle="kayit"></label><label class="btn cam-btn kucuk dosya-sec">${ik('atac')}Müzik yükle<input type="file" accept="audio/*" data-yukle="muzik"></label></div>
        <div class="form-izgara"><label class="alan-et" for="muzik-bpm">Geçici müzik temposu (BPM)<input id="muzik-bpm" type="number" value="${Math.round(d.bpm || 104)}"></label><label class="alan-et" for="muzik-yapi">Yapı <small>bölüm:ölçü</small><input id="muzik-yapi" value="giris:1,ana:4,kapanis:1"></label></div>
        <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-komut="muzik">Müzik üret</button><button type="button" class="btn cam-btn kucuk" data-komut="vurus">Vuruş ızgarası çıkar</button></div>
        ${oynat.length ? `<div class="grup">${oynat.map(([n, p]) => `<div class="kopya-satir" style="align-items:center"><div><b>${esc(n)}</b><audio src="${dosyaUrl(p, true)}" controls preload="none" style="width:100%;height:34px"></audio></div></div>`).join('')}</div>` : '<p class="ince">Henüz ses yok.</p>'}
      </div></details>`;
}
function kareVurgula() { $$('#kare-izgara button').forEach((b) => b.classList.toggle('simdi', b.dataset.kv !== '' && +b.dataset.kv === W.aktifV)); }

// ---- Kurgu
const gozAnahtar = () => `goz:${W.id}:${sonInceleme(W.d)?.ad || ''}`;
function gozOku() { try { return JSON.parse(localStorage.getItem(gozAnahtar()) || '{}'); } catch { return {}; } }
function hukumAyikla(el) {
  const t = String(el || '');
  return {karar: sadeMetin((t.match(/\*\*Karar:\*\*\s*(.+)/) || [])[1] || ''), mesaj: sadeMetin((t.match(/\*\*Anladığım mesaj[^*]*:\*\*\s*(.+)/) || [])[1] || ''),
    izlenim: sadeMetin((t.match(/\*\*Genel izlenim:\*\*\s*(.+)/) || [])[1] || '')};
}
/** Kör eleştirinin "Üç soru" bölümü (ilk saniye, gönderir misin, şablon gibi mi; varsa üretim kuralı): [[soru, yanıt]] */
function ucSoru(el) {
  const b = (String(el || '').split(/^## Üç soru\s*$/m)[1] || '').split(/^## /m)[0];
  return [...b.matchAll(/^-\s*\*\*([^*]+?)\*\*\s*(.+)$/gm)].map((m) => [m[1].trim(), sadeMetin(m[2].trim())]);
}
function olcumOzet(rows) {
  const n = (s) => rows.filter((r) => r.durum === s).length;
  return `<div class="olcum-ozet"><div class="kirmizi"><b>${n('❌')}</b><span>hata</span></div><div class="turuncu"><b>${n('⚠️')}</b><span>uyarı</span></div><div class="yesil"><b>${n('✅')}</b><span>geçti</span></div><div><b>${n('👁')}</b><span>senin gözün</span></div></div>`;
}
const olcumSatir = (r) => `<div class="olcum-satir">${DURUM_IK(r.durum)}<span>${esc(r.ad)}${r.cita ? `<span class="cita">Çıta: ${esc(r.cita)}</span>` : ''}</span><span class="deger" title="${esc(r.deger)}">${esc(r.deger.length > 34 ? r.deger.slice(0, 32) + '…' : r.deger)}</span></div>`;
function govdeKurgu() {
  const d = W.d;
  const son = sonInceleme(d);
  if (!son) return `${kapiKutu(4)}<p class="ince">Henüz inceleme yok: “İncele: kontak + ölçüm” kontak tabakasını ve ölçümü üretir.</p>`;
  const O = son.olcum || [];
  const goz = O.filter((r) => r.durum === '👁');
  const gd = gozOku();
  const h = hukumAyikla(son.elestiri);
  return `${kapiKutu(4)}
    <div class="blok"><h3>Ölçüm · ${esc(son.ad)}</h3>${olcumOzet(O)}</div>
    ${O.some((r) => ['❌', '⚠️'].includes(r.durum)) ? `<div class="blok"><h3>Hatalar ve uyarılar</h3><div class="grup">${O.filter((r) => ['❌', '⚠️'].includes(r.durum)).map(olcumSatir).join('')}</div></div>` : ''}
    ${goz.length ? `<div class="blok"><h3>Senin gözün · ölçümün göremedikleri</h3><div class="grup">${goz.map((r, i) => `<label class="goz-satir"><input type="checkbox" id="goz-${i}" data-goz="${i}" ${gd[i] ? 'checked' : ''}><span>${esc(r.ad)}</span></label>`).join('')}</div><p class="ince">Bu liste yalnız bu tarayıcıda işaretlenir; kapıyı etkilemez.</p></div>` : ''}
    <details class="aac"><summary>${ik('sag')}Geçen ${O.filter((r) => r.durum === '✅').length} ölçüm</summary><div class="grup">${O.filter((r) => r.durum === '✅').map(olcumSatir).join('')}</div></details>
    ${Object.keys(son.kontak).length ? `<div class="blok"><h3>Kontak tabakası</h3><div class="kare-izgara" style="grid-template-columns:repeat(${Math.min(3, Object.keys(son.kontak).length)},1fr)">${Object.entries(son.kontak).map(([f, p]) => `<button type="button" data-buyut="${dosyaUrl(p)}"><span class="kg" style="aspect-ratio:auto;height:140px"><img src="${kucukUrl(p, 400)}" alt="" style="object-position:top"></span><small><b>${fmtEtiket(f)}</b>tam boy aç</small></button>`).join('')}</div></div>` : ''}
    ${son.elestiri ? `<div class="blok"><h3>Kör eleştiri</h3><div class="hukum"><div class="hukum-ust"><span class="hukum-ikon">${ik('goz')}</span><div><b>${esc(h.karar || 'Eleştiri')}</b><br><small>Filmi hiç görmemiş bir oturum · yalnız kareleri ve ölçümü gördü</small></div></div>${h.izlenim ? `<q>${esc(h.izlenim)}</q>` : ''}</div>
      ${ucSoru(son.elestiri).length ? `<div class="grup uc-soru">${ucSoru(son.elestiri).map(([q, a]) => `<div class="grup-satir"><span class="et">${esc(q)}</span><span class="de" title="${esc(a)}">${esc(a.split(/(?<=[.!?])\s/)[0].slice(0, 180))}</span></div>`).join('')}</div>` : ''}
      <details class="aac"><summary>${ik('sag')}Eleştirinin tamamı</summary><div class="durum-md" style="max-height:none">${md(son.elestiri)}</div></details></div>` : ''}
    ${d.incelemeler.length > 1 ? `<details class="aac"><summary>${ik('sag')}Önceki incelemeler</summary><div class="grup">${[...d.incelemeler].reverse().slice(1).map((r) => `<div class="kopya-satir"><div><b>${esc(r.ad)}</b>${r.olcum ? `❌ ${r.olcum.filter((x) => x.durum === '❌').length} · ⚠️ ${r.olcum.filter((x) => x.durum === '⚠️').length} · ✅ ${r.olcum.filter((x) => x.durum === '✅').length}` : 'ölçüm yok'}</div>${Object.values(r.kontak)[0] ? `<button type="button" class="btn cam-btn kucuk" data-buyut="${dosyaUrl(Object.values(r.kontak)[0])}">Kontak</button>` : ''}</div>`).join('')}</div></details>` : ''}`;
}

// ---- Rötuş
function govdeRotus() {
  const d = W.d;
  const son = sonInceleme(d);
  const h = hukumAyikla(son?.elestiri);
  const k5 = d.kapilar[4];
  const kart = (k) => {
    const kr = k.kare != null ? (d.kareler[W.fmt] || []).find((x) => Math.round(x.t * W.fps) === k.kare) || kareBul(k.kare / W.fps) : k.t != null ? kareBul(k.t) : null;
    const tamam = /onarıldı|kapandı|tamam/i.test(k.durum);
    return `<button type="button" class="kusur ${W.secKusur === k.n ? 'secili' : ''}" data-kusur="${k.n}"><span class="kg">${kr ? `<img src="${kucukUrl(kr.yol, 160)}" alt="">` : ''}</span>
      <span class="kusur-govde"><span class="kusur-ust"><span class="no">${k.n}</span>${k.t != null ? tc(k.t).slice(3) : esc(k.zaman)}<span class="cip ${tamam ? 'yesil' : 'turuncu'}" style="margin-left:auto">${esc(k.durum || 'açık')}</span></span><h4>${esc(k.baslik)}</h4>${k.kanit ? `<p>${esc(k.kanit)}</p>` : ''}${k.duzeltme ? `<p><b>Düzeltme:</b> ${esc(k.duzeltme)}</p>` : ''}</span></button>`;
  };
  const acik = W.kusurlar.filter((k) => !/onarıldı|kapandı|tamam/i.test(k.durum));
  const karar = k5.durum === 'sirada' && !claudeCalisiyor() && GENEL?.claudeVar && son ? `<div class="karar-kutu"><p><b>Karar senin.</b> ${acik.length ? `${acik.length} kusur açık.` : 'Kusurlar onarılmış görünüyor.'} Claude bir tur daha onarabilir ya da film olduğu gibi teslime geçer: Rötuş kanıtla kapanır, açık kusurlarla teslim etmek senin kararın.</p>
    <div class="dugmeler"><button type="button" class="btn ana-btn" data-rotus="onar">Kusurları Claude onarsın</button><button type="button" class="btn cam-btn" data-asama-git="teslim">Böyle teslim et</button></div></div>` : '';
  return `${kapiKutu(5)}
    ${son?.elestiri ? `<div class="hukum"><div class="hukum-ust"><span class="hukum-ikon">${ik('goz')}</span><div><b>${esc(h.karar || 'Kör eleştiri')}</b><br><small>Kör eleştirmen · ${esc(son.ad)} · yalnız kareleri ve ölçümü gördü</small></div></div>${h.mesaj ? `<q>${esc(h.mesaj)}</q>` : ''}${h.mesaj && d.script.learningGoal ? '<small>Eleştirmenin anladığı mesajı kendi tek cümlenle karşılaştır.</small>' : ''}</div>` : ''}
    <div class="blok"><h3>En büyük kusurlar${son ? ` · ${esc(son.ad)}` : ''}</h3>${W.kusurlar.length ? W.kusurlar.map(kart).join('') : '<p class="ince">İnceleme notunda henüz kusur yazılmamış.</p>'}</div>
    ${son ? `<div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-duzenle="inceleme/${esc(son.ad)}/inceleme.md">${ik('kalem')}İnceleme notunu düzenle</button></div>` : ''}
    ${karar}`;
}

// ---- Teslim
function govdeTeslim() {
  const d = W.d;
  const son = {};
  for (const t of d.teslim) son[t.format] = t;
  const tes = sonInceleme(d)?.teslim || [];
  const tOlc = tes.length ? tes[tes.length - 1].olcum || [] : [];
  const lufs = tOlc.find((r) => /ses yüksekliği/i.test(r.ad));
  const y = d.basit?.yayin;
  const yMd = d.dosyalar['yayin.md'];
  return `${kapiKutu(6)}
    <div class="blok"><h3>Final videolar</h3>${Object.values(son).length ? Object.values(son).map((t) => `<div class="teslim-kart" style="grid-template-columns:${fmtOran(t.format) > 1 ? '120px' : '70px'} 1fr">${t.poster ? `<img src="${kucukUrl(t.poster, 300)}" alt="" style="aspect-ratio:${fmtOran(t.format)}">` : '<span></span>'}<div><b>${FORMAT_AD[t.format] || ''} · ${fmtEtiket(t.format)}</b><span>${esc(t.ad)} · ${sn(t.mb)} MB</span>
      <span class="dugmeler" style="margin-top:6px"><button type="button" class="btn cam-btn kucuk" data-fmt="${t.format}">İzle</button><a class="btn cam-btn kucuk" href="${dosyaUrl(t.dosya)}" download="${esc(t.ad)}">${ik('indir')}İndir</a>${t.poster ? `<a class="btn cam-btn kucuk" href="${dosyaUrl(t.poster)}" download>Poster</a>` : ''}</span></div></div>`).join('') : '<p class="ince">Henüz final render yok.</p>'}</div>
    ${yapimBlok(d)}
    ${kisiselBlok(d)}
    ${tOlc.length ? `<div class="blok"><h3>Teslim ölçümü · ${esc(tes[tes.length - 1].ad)}</h3>${olcumOzet(tOlc)}${lufs ? `<div class="grup">${olcumSatir(lufs)}</div>` : ''}${tOlc.some((r) => r.durum === '❌') ? `<div class="grup">${tOlc.filter((r) => r.durum === '❌').map(olcumSatir).join('')}</div>` : ''}</div>` : ''}
    <div class="blok"><h3>Yayın paketi</h3>${yMd != null ? `${y ? `<div class="grup">${y.baslik ? `<div class="kopya-satir"><div><b>Başlık</b>${esc(y.baslik)}</div><button class="ikon-btn" type="button" data-kopyala="${esc(y.baslik)}" aria-label="Başlığı kopyala">${ik('kopya')}</button></div>` : ''}${y.aciklama ? `<div class="kopya-satir"><div><b>Açıklama</b>${esc(y.aciklama)}</div><button class="ikon-btn" type="button" data-kopyala="${esc(y.aciklama)}" aria-label="Açıklamayı kopyala">${ik('kopya')}</button></div>` : ''}</div>` : ''}
      <details class="aac"><summary>${ik('sag')}Yayın paketinin tamamı</summary><div class="durum-md" style="max-height:none">${md(yMd)}</div></details>
      <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-duzenle="yayin.md">${ik('kalem')}Yayın paketini düzenle</button></div>` : '<p class="ince">Yayın paketi henüz yok: “Yayın paketi taslağı”.</p>'}
      <p class="ince">Yüklemeyi sen yaparsın; nereye çıkacağı yayın paketinde yazar. YouTube'a çıkacaksa <a href="#/belge?yol=kanal/youtube.md">YouTube yükleme listesi</a>.</p></div>
    ${analitikBlok(d)}`;
}

// ---- Nasıl yapıldı filmi (4e): 15 sn'lik yapım filmi, bu filmin kendi kayıtlarından (./st yapim). Kredi harcamaz, kapı onaylamaz.
const YAPIM_RENK = {acilis: '#8B93A1', yollar: '#FF7A2F', kilavuz: '#FFD23F', blender: '#B69CFF', elestiri: '#7FD8FF', uretim: '#56E39F', kapilar: '#F4F1EA', kapanis: '#5B6170'};
const YAPIM_AD = {acilis: 'Başlık', yollar: 'Üç yol', kilavuz: 'Kılavuz', blender: 'Kil · tel kafes', elestiri: 'Önce / sonra', uretim: 'Yapay zekâ', kapilar: 'Kapılar', kapanis: 'Film'};
const YAPIM_EKSIK = {yollar: 'Üç yol ya da görünüş denemesi kaydı yok', elestiri: 'En az iki inceleme turu yok', uretim: 'Yapay zekâ varlığı yok'};
let yapimZamanlayici = null;
function yapimBlok(d) {
  const Y = d.yapim;
  if (!Y) return '';
  if (Y.hata) return `<div class="blok yapim"><h3>Nasıl yapıldı filmi</h3><p class="ince">${esc(Y.hata)}</p></div>`;
  const oran = fmtOran(Y.format);
  const son = Y.son;
  const S = Y.suren;
  clearTimeout(yapimZamanlayici);
  if (S) yapimZamanlayici = setTimeout(() => { if (W.asama === 'teslim' && W.d?.yapim?.suren) yenidenYukle(); }, 3500);
  const toplam = Y.plan.reduce((a, b) => a + b.sn, 0) || 15;
  const serit = `<div class="yapim-serit" role="list" aria-label="Yapım filminin bölümleri">${Y.plan.map((b) => `<div role="listitem" class="yapim-dilim" style="flex:${b.sn} 1 0;--r:${YAPIM_RENK[b.tur] || '#888'}" title="${esc(b.aciklama)}"><span>${esc(YAPIM_AD[b.tur] || b.tur)}</span><small>${sn(b.sn)} sn</small></div>`).join('')}</div>`;
  const kart = (p, etiket) => `<button type="button" class="yapim-on" data-buyut="${dosyaUrl(p, true)}" style="aspect-ratio:${oran}" aria-label="${esc(etiket)}: büyüt"><img src="${kucukUrl(p, 320)}" alt="" loading="lazy"><span>${esc(etiket)}</span></button>`;
  let onizleme = '';
  if (son?.kareler && Object.keys(son.kareler).length) {
    onizleme = Y.plan.filter((b) => son.kareler[b.tur]).map((b) => kart(son.kareler[b.tur], YAPIM_AD[b.tur] || b.tur)).join('');
  } else {
    const parca = [];
    if (Y.kilavuz_onizleme) parca.push(kart(Y.kilavuz_onizleme, Y.motor === 'blender' ? 'Kil' : 'Kılavuz'));
    for (const p of Y.onizleme.yollar || []) parca.push(kart(p, 'Yol'));
    (Y.onizleme.elestiri || []).forEach((p, i) => parca.push(kart(p, i ? 'Son tur' : 'İlk tur')));
    for (const p of Y.onizleme.uretim || []) parca.push(kart(p, 'Yapay zekâ'));
    onizleme = parca.join('');
  }
  const eksik = (Y.eksik || []).length ? `<p class="ince">Kaydı olmadığı için girmeyen: ${Y.eksik.map((k) => esc(YAPIM_EKSIK[k] || k)).join(' · ')}. Yapım filminde yalnız kaydı olan an görünür.</p>` : '';
  const ilerleme = S ? `<div class="yapim-ilerleme" role="status"><div class="yapim-bar"><i style="width:${S.toplam ? Math.round((100 * S.adim) / S.toplam) : 4}%"></i></div>
      <span>${S.toplam ? `Adım ${S.adim}/${S.toplam} · ` : ''}${esc(S.metin)} · ${S.gecen >= 90 ? `${Math.round(S.gecen / 60)} dk` : `${S.gecen} sn`}</span></div>` : '';
  const olc = son?.olcum || [];
  const kotu = olc.filter((r) => r.durum === '❌');
  const video = son ? `<div class="yapim-cikti">${son.dosya ? `<video controls preload="none" playsinline src="${dosyaUrl(son.dosya, true)}"${son.poster ? ` poster="${kucukUrl(son.poster, 540)}"` : ''} style="aspect-ratio:${oran}"></video>` : '<p class="ince">Son çıktı panelin dışında bir klasöre yazıldı.</p>'}
      <div><b>${esc(son.ad)}</b><span class="ince">${esc(son.tarih)} · ${fmtEtiket(son.format)}${son.mb ? ` · ${sn(son.mb)} MB` : ''}${son.sure_sn ? ` · ${Math.max(1, Math.round(son.sure_sn / 60))} dk'da çizildi` : ''}</span>
      ${olc.length ? `<span class="cip ${kotu.length ? 'kirmizi' : 'yesil'}">${kotu.length ? `ölçümde ${kotu.length} sorun` : 'ölçüm temiz'}</span>` : ''}
      ${son.dosya ? `<span class="dugmeler"><a class="btn cam-btn kucuk" href="${dosyaUrl(son.dosya)}" download="${esc(son.ad)}">${ik('indir')}İndir</a></span>` : ''}
      ${kotu.length ? `<div class="grup">${kotu.map(olcumSatir).join('')}</div>` : ''}</div></div>` : '';
  const dk = Math.max(1, Math.round((Y.tahmini_sn || 240) / 60));
  return `<div class="blok yapim"><h3>Nasıl yapıldı filmi</h3>
    <p class="ince">15 saniyelik bir yapım filmi: bu filmin kendi kayıtlarından kurgulanır (üç yol ve seçilen, iskelet, inceleme turları, kapılar ve senin onayların). Kredi harcamaz; ses kod müziği ve filmin kendi miksi.</p>
    ${serit}${onizleme ? `<div class="yapim-onizleme">${onizleme}</div>` : ''}${eksik}${ilerleme}${video}
    <div class="dugmeler"><button type="button" class="btn ${son ? 'cam-btn' : 'ana-btn'}" data-yapim-baslat ${S ? 'disabled' : ''}>${S ? 'Çiziliyor…' : `${son ? 'Yeniden çiz' : 'Nasıl yapıldı filmini çiz'} · ~${dk} dk`}</button>${!son && !Y.kilavuz_onizleme ? `<button type="button" class="btn cam-btn kucuk" data-yapim-onizle ${S ? 'disabled' : ''}>${ik('gorsel')}Önce bir kareye bak</button>` : ''}</div></div>`;
}
async function yapimTikla(t) {
  const b = t.closest('[data-yapim-baslat], [data-yapim-onizle]');
  if (!b) return false;
  b.disabled = true;
  const onizle = b.hasAttribute('data-yapim-onizle');
  try {
    isIzle(await api.post(`/api/video/${W.id}/yapim${onizle ? '?onizle=1' : ''}`, {}), () => yenidenYukle());
    bildir(onizle ? 'Kılavuz karesi çiziliyor…' : 'Yapım filmi çiziliyor: ilerleme bu kutuda ve sağ altta.', 4500);
    setTimeout(yenidenYukle, 1500);
  } catch (er) { bildir(er.message, 6000); b.disabled = false; }
  return true;
}

// ---- Kişisel etki filmi (4c): şablondan her kişiye kendi verisiyle film. Liste bu bilgisayarda kalır (videos/<id>/toplu/), Claude'a gitmez.
// Sunucu yalnız sütun adlarını, sayıları ve satır numarası + kimlik + nedeni döndürür; önizleme bir resimdir (ilk geçerli satırın kanıt karesi).
const KISI = {film: null, dosya: null, oz: null, bekliyor: false};
const kisiYer = (a) => (a.ekranda ? 'ekranda' : a.sahne ? 'sahnede (yazı değil)' : 'filme gitmez');
async function kisiDenetle() {
  if (!KISI.dosya) return;
  KISI.bekliyor = true;
  try { KISI.oz = await api.post(`/api/video/${W.id}/toplu/denetle`, {dosya: KISI.dosya}); } catch (er) { KISI.oz = {dosya: KISI.dosya, hata: er.message}; }
  KISI.bekliyor = false;
  if (W.asama === 'teslim') denetciCiz({kaydirma: true});
}
function kisiselBlok(d) {
  const K = d.kisisel;
  if (!K) return '';
  if (KISI.film !== W.id) Object.assign(KISI, {film: W.id, dosya: null, oz: null});
  const dosyalar = K.dosyalar || [];
  if (!dosyalar.some((f) => f.ad === KISI.dosya)) { KISI.dosya = dosyalar.length ? dosyalar[dosyalar.length - 1].ad : null; KISI.oz = null; }
  const O = KISI.oz && KISI.oz.dosya === KISI.dosya ? KISI.oz : null;
  if (KISI.dosya && !O && !KISI.bekliyor) setTimeout(kisiDenetle, 0);
  const alanlar = K.alanlar.filter((a) => a.tur !== 'kimlik').map((a) => `<span class="cip ${a.ekranda ? 'yesil' : ''}" title="${esc(a.tur)}">${esc(a.ad)} · ${kisiYer(a)}${a.zorunlu ? '' : ' · isteğe bağlı'}</span>`).join('');
  const eksik = K.karar_eksik || [];
  const karar = `<details class="aac"><summary>${ik('sag')}<span>Kurum verisi notları (isteğe bağlı)</span> ${eksik.length ? '' : '<span class="cip yesil">yazılı</span>'}</summary>
      <p class="ince">İstersen yazarsın (Claude yazmaz); yazdıkların yayın paketine KVKK notu olarak girer. Boş bırakabilirsin. Hukuki dayanak ve aydınlatma metni için kurumun hukuk birimine danışabilirsin.</p>
      <div class="kisi-karar">${Object.entries(K.karar_alanlari).map(([k, ad]) => `<label class="alan-et" for="kk-${k}">${esc(ad)}<textarea id="kk-${k}" data-kisi-karar="${k}" rows="2" style="min-height:60px" placeholder="${k === 'ekranda' ? 'ör. yalnız ad ve bağış kalemi' : k === 'saklama' ? 'ör. gönderimden 30 gün sonra silinir' : ''}">${esc(K.kararlar?.[k] || '')}</textarea></label>`).join('')}</div>
      <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-kisi-karar-kaydet>${ik('tik')}Kararları kaydet</button></div></details>`;
  const dosyaSec = dosyalar.length ? `<div class="kisi-dosyalar" role="radiogroup" aria-label="Veri dosyası">${dosyalar.map((f) => `<button type="button" role="radio" aria-checked="${f.ad === KISI.dosya}" class="kisi-dosya ${f.ad === KISI.dosya ? 'secili' : ''}" data-kisi-dosya="${esc(f.ad)}">${ik('dosya')}<span>${esc(f.ad)}</span><small>${Math.max(1, Math.round(f.boyut / 1024))} KB</small></button>`).join('')}</div>` : '';
  let denet = '';
  if (KISI.dosya && !O) denet = '<p class="ince">Liste denetleniyor…</p>';
  else if (O?.hata) denet = `<div class="hata-kutu">${esc(O.hata)}</div>`;
  else if (O) {
    const secenek = (alan) => `<option value="">— eşleme yok —</option>${O.sutunlar.map((c) => `<option value="${esc(c)}" ${O.esleme[alan.anahtar] === c ? 'selected' : ''}>${esc(c)}</option>`).join('')}`;
    const esleme = `<details class="aac" ${O.eslenmeyen.some((k) => K.alanlar.find((a) => a.anahtar === k)?.zorunlu) ? 'open' : ''}><summary>${ik('sag')}<span>Sütun eşleme</span> <span class="cip">${Object.keys(O.esleme).length}/${K.alanlar.length} alan</span></summary>
        <div class="kisi-esleme">${K.alanlar.map((a) => `<label class="alan-et" for="ke-${a.anahtar}">${esc(a.ad)}${a.zorunlu ? '' : ' <small>isteğe bağlı</small>'}<select id="ke-${a.anahtar}" data-kisi-esle="${a.anahtar}">${secenek(a)}</select></label>`).join('')}</div>
        ${O.kullanilmayan.length ? `<p class="ince">Dosyada olup kullanılmayan sütunlar (filme gitmez): ${O.kullanilmayan.map(esc).join(', ')}</p>` : ''}
        <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-kisi-esleme-kaydet>${ik('tik')}Eşlemeyi kaydet</button></div></details>`;
    const at = O.atlanan.length ? `<details class="aac"><summary>${ik('sag')}<span>Atlanacak satırlar</span> <span class="cip turuncu">${O.atlanan.length}</span></summary>
        <div class="grup">${O.atlanan.map((x) => `<div class="grup-satir"><span class="et">satır ${x.no}${x.kimlik ? `<br><small>${esc(x.kimlik)}</small>` : ''}</span><span class="de">${x.nedenler.map(esc).join('<br>')}</span></div>`).join('')}</div>
        <p class="ince">Uydurma yok: eksik ya da geçersiz alanlı satır varsayılan değerle doldurulmaz, film çizilmez. Listeyi düzeltip yeniden yükle.</p></details>` : '';
    denet = `<div class="kisi-sayilar"><span class="cip">${O.satir} satır</span><span class="cip yesil">${O.gecerli} film çizilecek</span>${O.atlanan.length ? `<span class="cip turuncu">${O.atlanan.length} satır atlanacak</span>` : ''}${O.test ? '<span class="cip kirmizi">TEST verisi</span>' : '<span class="cip">kurum verisi</span>'}</div>
      ${O.engel ? `<div class="hata-kutu"><b>Gerçek veriyle çizilemez:</b> ${esc(O.engel)}</div>` : ''}${esleme}${at}`;
  }
  const oz = K.onizleme && K.onizleme.dosya === KISI.dosya ? K.onizleme : null;
  const onz = oz ? `<div class="kisi-onizleme">${Object.entries(oz.kareler).map(([f, p]) => `<button type="button" class="kisi-on ${fmtOran(f) < 1 ? 'dik' : 'yatay'}" data-buyut="${dosyaUrl(p, true)}" style="aspect-ratio:${fmtOran(f)}" aria-label="${fmtEtiket(f)} önizlemesi: büyüt"><img src="${kucukUrl(p, 480)}&v=${encodeURIComponent(oz.zaman)}" alt="satır ${oz.satir} önizlemesi (${fmtEtiket(f)})" loading="lazy"><span>${fmtEtiket(f)}</span></button>`).join('')}</div>
      <p class="ince">Satır ${oz.satir} · ${esc(oz.kimlik)} · filmin kanıt karesi (bütün yazılar ekranda). Büyütmek için dokun.</p>` : '';
  const son = (K.calismalar || [])[0];
  const tahmin = O && son?.film_basina_sn ? ` · ~${Math.max(1, Math.round((O.gecerli * d.formatlar.length * son.film_basina_sn) / 60))} dk` : '';
  const veri = `<div class="kisi-adim"><b>1 · Liste</b>
      ${dosyaSec}
      <div class="dugmeler"><label class="btn cam-btn kucuk dosya-sec">${ik('atac')}Liste yükle (CSV ya da JSON)<input type="file" accept=".csv,.json,.tsv,.txt" data-kisi-yukle></label>${KISI.dosya ? `<button type="button" class="btn cam-btn kucuk" data-kisi-sil="veri:${esc(KISI.dosya)}">Bu listeyi sil</button>` : ''}</div>
      ${denet}</div>`;
  const onizle = KISI.dosya && O && !O.hata ? `<div class="kisi-adim"><b>2 · İlk satırın önizlemesi</b>${onz || '<p class="ince">Listenin ilk geçerli satırıyla filmin bir karesi çizilir; yazıların sığdığını ve doğru olduğunu gözünle gör.</p>'}
      <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-kisi-onizle ${O.gecerli && !K.suren ? '' : 'disabled'}>${ik('gorsel')}${oz ? 'Önizlemeyi yeniden çiz' : 'Önizlemeyi çiz'}</button></div></div>
    <div class="kisi-adim"><b>3 · Filmleri çiz</b><p class="ince">Her kişiye bir film${d.formatlar.length > 1 ? ` (${d.formatlar.map(fmtEtiket).join(' + ')})` : ''}; dosya adları kimlikle. Her filmin yazıları kendi dosyasından yazı tanımayla denetlenir.</p>
      <div class="dugmeler"><button type="button" class="btn ana-btn" data-kisi-baslat ${O.engel || !O.gecerli || K.suren ? 'disabled' : ''}>${K.suren ? 'Çiziliyor…' : `${O.gecerli} kişiye film çiz${tahmin}`}</button></div>
      ${K.suren ? `<p class="ince">${esc(K.suren)} sürüyor: ilerleme sağ altta; biten filmler aşağıda belirir.</p>` : ''}</div>` : '';
  const ocrCip = (x) => (x.durum !== 'tamam' ? '<span class="cip kirmizi">çizilemedi</span>' : x.ocr ? '<span class="cip yesil">yazılar doğrulandı</span>' : '<span class="cip turuncu">göz bakmalı</span>');
  const calisma = (c, i) => `<details class="aac" ${i === 0 ? 'open' : ''}><summary>${ik('sag')}<span>${esc(c.ad)} · ${esc(c.dosya)}</span> ${c.test ? '<span class="cip kirmizi">TEST</span>' : ''}${c.bitti ? '' : ' <span class="cip claude">çiziliyor</span>'}</summary>
      <div class="kisi-sayilar"><span class="cip yesil">${c.uretilen} film</span>${c.atlanan.length ? `<span class="cip turuncu">${c.atlanan.length} satır atlandı</span>` : ''}${c.hatali ? `<span class="cip kirmizi">${c.hatali} hata</span>` : ''}${c.film_basina_sn ? `<span class="cip">film başına ${sn(c.film_basina_sn)} sn</span>` : ''}</div>
      <div class="kisi-cikti">${c.cikti.map((x) => `<div class="kisi-kart">${x.kanit ? `<button type="button" class="kisi-on" data-buyut="${dosyaUrl(x.kanit, true)}" style="aspect-ratio:${fmtOran(x.format)}" aria-label="${esc(x.kimlik)} kanıt karesi: büyüt"><img src="${kucukUrl(x.kanit, 320)}" alt="" loading="lazy"></button>` : '<span></span>'}
        <div><b>${esc(x.kimlik)}</b><span class="ince">${fmtEtiket(x.format)}${x.sn ? ` · ${sn(x.sn)} sn` : ''}</span>${ocrCip(x)}
        ${x.video ? `<span class="dugmeler"><a class="btn cam-btn kucuk" href="${dosyaUrl(x.video)}" target="_blank" rel="noopener">İzle</a><a class="btn cam-btn kucuk" href="${dosyaUrl(x.video)}" download>${ik('indir')}İndir</a></span>` : ''}</div></div>`).join('')}</div>
      ${c.atlanan.length ? `<div class="grup">${c.atlanan.map((x) => `<div class="grup-satir"><span class="et">satır ${x.no}${x.kimlik ? `<br><small>${esc(x.kimlik)}</small>` : ''}</span><span class="de">${x.nedenler.map(esc).join('<br>')}</span></div>`).join('')}</div>` : ''}
      <div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-kisi-sil="${esc(c.ad)}">Bu çalışmanın filmlerini sil</button></div></details>`;
  return `<div class="blok kisisel"><h3>Kişisel filmler</h3>
    <p class="ince">Bu film bir şablon: yüklediğin listedeki her kişiye kendi adı ve verisiyle ayrı bir film çizilir. Liste ve filmler bu bilgisayarda kalır; Claude'a, Magnific'e ve pakete gitmez. Dosya adları kimlikle (ad değil).</p>
    <div class="kisi-alanlar">${alanlar}</div>
    ${karar}${veri}${onizle}
    ${(K.calismalar || []).length ? `<div class="kisi-adim"><b>Çizilen filmler</b>${K.calismalar.map(calisma).join('')}</div>` : ''}</div>`;
}
async function kisiYukle(input) {
  const f = input.files[0];
  if (!f) return;
  bildir(`${f.name} yükleniyor…`);
  try {
    const oz = await api.post(`/api/video/${W.id}/toplu/yukle?ad=${encodeURIComponent(f.name)}`, await f.arrayBuffer(), true);
    Object.assign(KISI, {dosya: oz.dosya, oz});
    bildir(oz.hata ? 'Liste okunamadı: nedeni kutuda.' : `Liste yüklendi: ${oz.gecerli} film çizilecek${oz.atlanan?.length ? `, ${oz.atlanan.length} satır atlanacak` : ''}.`, 5000);
    await yenidenYukle();
  } catch (er) { bildir(er.message, 6500); }
  input.value = '';
}
async function kisiTikla(t) {
  const c = (s) => t.closest(s);
  let b;
  if ((b = c('[data-kisi-dosya]'))) { Object.assign(KISI, {dosya: b.dataset.kisiDosya, oz: null}); denetciCiz({kaydirma: true}); return true; }
  if ((b = c('[data-kisi-esleme-kaydet]'))) {
    const esleme = Object.fromEntries($$('[data-kisi-esle]').map((s) => [s.dataset.kisiEsle, s.value]));
    try { KISI.oz = await api.post(`/api/video/${W.id}/toplu/esleme`, {dosya: KISI.dosya, esleme}); bildir('Eşleme kaydedildi; liste yeniden denetlendi.'); denetciCiz({kaydirma: true}); } catch (er) { bildir(er.message, 6000); }
    return true;
  }
  if ((b = c('[data-kisi-karar-kaydet]'))) {
    const govde = Object.fromEntries($$('[data-kisi-karar]').map((x) => [x.dataset.kisiKarar, x.value]));
    try { await api.post(`/api/video/${W.id}/toplu/karar`, govde); KISI.oz = null; bildir('Kararların kaydedildi (yayın paketine KVKK notu olarak girdi).', 4500); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return true;
  }
  if ((b = c('[data-kisi-onizle]'))) {
    b.disabled = true;
    try { isIzle(await api.post(`/api/video/${W.id}/toplu/onizle`, {dosya: KISI.dosya}), () => yenidenYukle()); } catch (er) { bildir(er.message, 6000); b.disabled = false; }
    return true;
  }
  if ((b = c('[data-kisi-baslat]'))) {
    b.disabled = true;
    try { isIzle(await api.post(`/api/video/${W.id}/toplu/baslat`, {dosya: KISI.dosya}), () => yenidenYukle()); bildir('Filmler çiziliyor: ilerleme sağ altta, bitenler aşağıda listelenir.', 5000); setTimeout(yenidenYukle, 2500); } catch (er) { bildir(er.message, 6500); b.disabled = false; }
    return true;
  }
  if ((b = c('[data-kisi-sil]'))) {
    const veri = b.dataset.kisiSil.startsWith('veri:');
    const ok = await onaySor(b, {soru: veri ? 'Liste dosyası bu bilgisayardan silinsin mi? (Çizilmiş filmler kalır.)' : 'Bu çalışmanın kişisel filmleri, kanıt kareleri ve raporu silinsin mi?', evet: 'Sil', tehlike: true});
    if (ok === null) return true;
    try { await api.post(`/api/video/${W.id}/toplu/sil`, {hedef: b.dataset.kisiSil}); if (veri) Object.assign(KISI, {dosya: null, oz: null}); bildir('Silindi.'); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return true;
  }
  return false;
}

// ---- Yayın sonrası rapor: gerçek izleyici verisi döngüye girer (Claude koptukları anları karelerde bulur; sistem önerisi senin onayınla işlenir)
const PLATFORMLAR = ['YouTube Shorts', 'Instagram Reels', 'TikTok', 'YouTube', 'Instagram gönderisi', 'Facebook', 'X', 'Web sitesi', 'Diğer'];
const bugun = () => { const z = new Date(); return `${z.getFullYear()}-${String(z.getMonth() + 1).padStart(2, '0')}-${String(z.getDate()).padStart(2, '0')}`; };
function analitikBlok(d) {
  const A = d.analitik || {raporlar: []};
  const durum = (r) => (r.durum === 'hazir' ? '<span class="cip yesil">rapor hazır</span>' : r.durum === 'inceleniyor' ? '<span class="cip claude">Claude inceliyor</span>' : '<span class="cip">incelenmedi</span>');
  const rapor = (r) => `<details class="aac" ${r.durum !== 'hazir' ? 'open' : ''}><summary>${ik('sag')}<span>${esc(r.klasor)} · ${esc(r.alanlar.platform || 'platform yok')}</span> ${durum(r)}${r.test ? ' <span class="cip turuncu">TEST</span>' : ''}</summary>
      ${r.rapor ? `<div class="durum-md" style="max-height:none">${md(r.rapor)}</div>` : ''}
      ${r.kareler.length ? `<div class="analitik-kareler">${r.kareler.map((k) => `<button type="button" data-buyut="${dosyaUrl(k)}" aria-label="Kareyi büyüt"><img src="${kucukUrl(k, 200)}" alt=""><small>${esc((k.match(/f(\d+)\.png$/) || [])[1] ? tc(+k.match(/f(\d+)\.png$/)[1] / W.fps).slice(3) : '')}</small></button>`).join('')}</div>` : ''}
      ${r.dosyalar.length ? `<div class="cipler">${r.dosyalar.map((f) => `<a class="cip" href="${dosyaUrl(f.yol)}" target="_blank" rel="noopener">${ik('atac')}${esc(f.ad)}</a>`).join('')}</div>` : ''}
      ${r.durum === 'bekliyor' && GENEL?.claudeVar ? `<div class="dugmeler"><button type="button" class="btn cam-btn kucuk" data-analitik-basla="${esc(r.klasor)}">Claude'a incelet</button></div>` : ''}</details>`;
  const alan = (id, et, ipucu, tip = 'text') => `<label class="alan-et" for="${id}">${et}${ipucu ? ` <small>${ipucu}</small>` : ''}<input id="${id}" type="${tip}" ${tip === 'text' ? 'inputmode="decimal" autocomplete="off"' : ''}></label>`;
  return `<div class="blok" id="analitik-blok"><h3>Yayın sonrası rapor</h3>
    <p class="ince">Film yayınlandıktan sonra platformun raporunu ekle (CSV, ekran görüntüsü ya da PDF; ya da birkaç sayı). Claude izleyicinin koptuğu anları filmin karelerinde bulur, bir hipotez ve sistem önerisi yazar; öneri sen onaylamadan işlenmez.</p>
    ${A.raporZamani ? `<p class="analitik-not">${ik('saat')}<span>Yayından iki gün geçti: ilk rapor için iyi bir zaman. (Bu not bir kez görünür.)</span></p>` : ''}
    <div class="analitik-satir"><label class="alan-et" for="an-yayin">Yayın tarihi <small>hatırlatma bundan 2 gün sonra bir kez</small><input id="an-yayin" type="date" value="${esc(A.yayinTarihi || '')}"></label><button type="button" class="btn cam-btn kucuk" data-yayin-kaydet>Kaydet</button></div>
    ${A.raporlar.map(rapor).join('')}
    <details class="aac" ${A.raporlar.length ? '' : 'open'}><summary>${ik('arti')}Rapor ekle</summary>
      <div class="analitik-form">
        ${d.teslim.length ? '' : `<p class="analitik-not">${ik('unlem')}<span>Bu filmin henüz teslim dosyası yok: Claude düşüş anlarını filmin bugünkü hâlinden çizer, ölçümle karşılaştırma eksik kalabilir.</span></p>`}
        <div class="form-izgara"><label class="alan-et" for="an-platform">Platform<select id="an-platform">${PLATFORMLAR.map((x) => `<option>${x}</option>`).join('')}</select></label>
          <label class="alan-et" for="an-tarih">Rapor tarihi<input id="an-tarih" type="date" value="${bugun()}"></label></div>
        ${d.teslim.length ? `<label class="alan-et" for="an-surum">Yayınlanan dosya<select id="an-surum">${[...d.teslim].reverse().map((t) => `<option value="${esc(t.ad)}">${esc(t.ad)}</option>`).join('')}<option value="">bilmiyorum</option></select></label>` : ''}
        <div class="analitik-alanlar">${alan('an-izlenme', 'İzlenme', '')}${alan('an-ort', 'Ort. izlenme', '%')}${alan('an-izlendi', 'İzlendi / kaydırıldı', '%')}${alan('an-paylasim', 'Paylaşım', '')}${alan('an-gonderim', 'Gönderim', '')}</div>
        <label class="alan-et" for="an-not">Not <small>isteğe bağlı: neyi merak ediyorsun?</small><textarea id="an-not" rows="2"></textarea></label>
        <div class="dugmeler"><label class="btn cam-btn kucuk dosya-sec">${ik('atac')}Dosya seç (CSV, ekran görüntüsü, PDF)<input type="file" multiple id="an-dosya" accept=".csv,.tsv,.txt,.pdf,image/png,image/jpeg,image/webp"></label><span class="ince" id="an-dosya-ad"></span></div>
        <div class="dugmeler"><button type="button" class="btn ana-btn" data-analitik-gonder ${GENEL?.claudeVar ? '' : 'disabled'}>${ik('claude')}Raporu Claude'a incelet</button></div>
      </div></details></div>`;
}
async function analitikGonder(b) {
  const deger = (id) => $(`#${id}`)?.value.trim() || '';
  const al = {platform: deger('an-platform'), tarih: deger('an-tarih'), surum: deger('an-surum'), izlenme: deger('an-izlenme'), ort_izlenme: deger('an-ort'), izlendi_kaydirildi: deger('an-izlendi'),
    paylasim: deger('an-paylasim'), gonderim: deger('an-gonderim'), not: deger('an-not')};
  const dosyalar = [...($('#an-dosya')?.files || [])];
  if (!dosyalar.length && !al.izlenme && !al.ort_izlenme && !al.izlendi_kaydirildi) return bildir('Bir rapor dosyası seç ya da en az bir sayı yaz (izlenme, ortalama izlenme ya da izlendi / kaydırıldı).', 5000);
  b.disabled = true;
  try {
    const r = await api.post(`/api/video/${W.id}/analitik`, al);
    for (const f of dosyalar) await api.post(`/api/video/${W.id}/analitik/dosya?klasor=${encodeURIComponent(r.klasor)}&ad=${encodeURIComponent(f.name)}`, await f.arrayBuffer(), true);
    await analitikBasla(r.klasor);
  } catch (er) { bildir(er.message, 6000); b.disabled = false; }
}
async function analitikBasla(klasor) {
  const j = await api.post(`/api/video/${W.id}/analitik/basla?klasor=${encodeURIComponent(klasor)}`, {});
  isIzle(j.is, () => yenidenYukle().catch(() => {}));
  bildir(j.test ? 'TEST raporu: Claude inceliyor; öğrenimlere işlenmez.' : 'Claude raporu inceliyor; bitince burada görünür.', 5000);
  await yenidenYukle();
}

// ---------------------------------------------------------------- denetçi olayları
function denetciBagla(g) {
  $$('[data-goz]', g).forEach((c) => c.addEventListener('change', () => { const o = gozOku(); o[c.dataset.goz] = c.checked; try { localStorage.setItem(gozAnahtar(), JSON.stringify(o)); } catch { /* yerel kayıt yoksa işaret oturumda kalır */ } }));
  const kaynak = $('#ses-kaynak', g);
  if (kaynak) {
    const goster = () => $$('[data-kaynak-alan]', g).forEach((el) => { el.hidden = el.dataset.kaynakAlan !== kaynak.value; });
    kaynak.addEventListener('change', goster);
    goster();
  }
}
async function yenidenYukle() { await filmAc(W.id, W.asama, {yenile: true}); }
async function kaydet(dosya, metin) {
  await api.post(`/api/video/${W.id}/kaydet`, {dosya, metin});
  bildir(`${dosya.split('/').pop()} kaydedildi.`);
  await yenidenYukle();
}
function duzenleyiciAc(dosya) {
  const d = W.d;
  const ince = dosya.match(/^inceleme\/(v\d+)\/inceleme\.md$/);
  const metin = ince ? (d.incelemeler.find((r) => r.ad === ince[1])?.inceleme || '') : d.dosyalar[dosya] ?? '';
  const mdMi = dosya.endsWith('.md');
  levhaAc(`<div class="levha-bas"><div><h2 id="levha-baslik">${esc(dosya)}</h2><p>${mdMi ? 'Solda yaz, sağda nasıl göründüğüne bak.' : 'JSON biçiminde; kaydedince denetlenir.'}</p></div>${kapatDugme}</div>
    <div class="duzenleyici" style="${mdMi ? '' : 'grid-template-columns:1fr'}"><textarea id="duz-metin" spellcheck="${mdMi}" aria-label="${esc(dosya)}">${esc(metin)}</textarea>${mdMi ? `<div class="onizleme" id="duz-on">${md(metin)}</div>` : ''}</div>
    <div class="levha-alt" style="margin-top:16px"><div class="alt-sol"><p>Kaydettiğinde dosya diske yazılır. Kapılar yeniden hesaplanır.</p></div><button type="button" class="btn cam-btn buyuk" data-kapat>Vazgeç</button><button type="button" class="btn ana-btn buyuk" id="duz-kaydet">Kaydet</button></div>`, 'genis');
  $('#duz-metin').addEventListener('input', (e) => { if (mdMi) $('#duz-on').innerHTML = md(e.target.value); });
  $('#duz-kaydet').addEventListener('click', async () => {
    try { await kaydet(dosya, $('#duz-metin').value); levhaKapat(); } catch (e) { bildir(`Kaydedilemedi: ${e.message}`, 6000); }
  });
}
function senaryoDuzenleyici() {
  const d = W.d;
  const sc = JSON.parse(JSON.stringify(d.script));
  const P = vurusIskeleti(d);
  const anlatimli = d.ses.kaynak !== 'yok';
  const alanlar = [[anlatimli ? 'anahtar' : 'isaret', anlatimli ? 'Anahtar kelime (ekranda olay olur)' : 'Olay işareti (cues.json)'], ['plan', 'Plan'], ['olay', 'Görsel olay'],
    ['giris', 'Giriş durumu'], ['cikis', 'Çıkış durumu'], ['gecis', 'Geçiş (sonrakine ne taşınır)'], ['ses', 'Ses'], ['amac', 'Neden var?']];
  const capa = (a) => (a ? (a[0] === 'vurus' ? a[1] : `t${a[1]}`) : '');
  levhaAc(`<div class="levha-bas"><div><h2 id="levha-baslik">Senaryo</h2><p>Her vuruşun bir görevi vardır: “Neden var?” sorusu cevapsızsa o vuruş filme girmez. Vuruş adları ${d.yapiKaynak === 'film' ? 'filmin kendi yapısından' : 'film türünün önerisinden'} gelir. Kaydettikten sonra “Denetle” profilin çıtalarına bakar.</p></div>${kapatDugme}</div>
    <div class="yeni-form" style="gap:14px"><label class="alan-et" for="sc-tek">İzleyicinin aklında kalacak tek cümle<input id="sc-tek" value="${esc(sc.learningGoal || '')}"></label><div id="sc-vuruslar" class="yeni-form" style="gap:10px"></div></div>
    <div class="levha-alt" style="margin-top:16px"><div class="alt-sol"><p>Metinde farklı okunacak yer: <code>1514 || Bin beş yüz on dört</code>. Her satır ayrı bir parçadır.</p></div><button type="button" class="btn cam-btn buyuk" data-kapat>Vazgeç</button><button type="button" class="btn ana-btn buyuk" id="sc-kaydet">Senaryoyu kaydet</button></div>`, 'genis');
  const ciz = () => {
    $('#sc-vuruslar').innerHTML = sc.sentences.map((s, i) => `<div class="vurus-duz" data-i="${i}">
      <div class="vurus-duz-ust"><span class="no">${i + 1}</span><select data-alan="step" aria-label="Vuruş adımı">${[...P, ...(P.includes(s.step) ? [] : [s.step])].map((v) => `<option ${v === s.step ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>
        ${anlatimli ? `<label class="ince">sonra duraklama <input type="number" step="0.05" data-alan="pauseAfter" value="${s.pauseAfter ?? 0.35}" style="width:76px"> sn</label>`
          : `<label class="ince">başlangıç vuruşu <input data-alan="bas" value="${capa(s.bas)}" style="width:64px"></label><label class="ince">bitiş <input data-alan="bit" value="${capa(s.bit)}" style="width:64px"></label>`}
        <span class="bosluk"></span><button type="button" class="ikon-btn" data-eylem="yukari" aria-label="Yukarı taşı">${ik('yukari')}</button><button type="button" class="ikon-btn" data-eylem="asagi" aria-label="Aşağı taşı" style="transform:rotate(180deg)">${ik('yukari')}</button><button type="button" class="btn cam-btn kucuk" data-eylem="ekle">${ik('arti')}Altına vuruş</button><button type="button" class="btn cam-btn kucuk" data-eylem="sil">Sil</button></div>
      ${anlatimli ? `<label class="alan-et">Metin<textarea data-alan="metin" style="min-height:60px">${esc((s.parts || []).map((p) => (p.say && p.say !== p.text ? `${p.text} || ${p.say}` : p.text)).join('\n'))}</textarea></label>` : ''}
      <div class="sozlesme-duz">${alanlar.map(([k, a]) => `<label class="alan-et">${a}<input data-shot="${k}" value="${esc((s.shot || {})[k] || '')}"></label>`).join('')}</div></div>`).join('');
  };
  const oku = () => {
    sc.learningGoal = $('#sc-tek').value;
    $$('.vurus-duz').forEach((v) => {
      const s = sc.sentences[+v.dataset.i];
      s.step = $('[data-alan=step]', v).value;
      if (anlatimli) {
        s.pauseAfter = parseFloat($('[data-alan=pauseAfter]', v).value) || 0;
        const eski = s.parts || [];
        s.parts = $('[data-alan=metin]', v).value.split('\n').map((x) => x.trim()).filter(Boolean).map((line, k) => {
          const [text, say] = line.split('||').map((x) => x.trim());
          const p = {text};
          if (say) p.say = say;
          if (eski[k]?.pauseAfter !== undefined) p.pauseAfter = eski[k].pauseAfter;
          return p;
        });
      } else {
        const c = (x) => (x.startsWith('t') ? ['t', parseFloat(x.slice(1))] : ['vurus', parseInt(x, 10)]);
        s.bas = c($('[data-alan=bas]', v).value.trim() || '0');
        s.bit = c($('[data-alan=bit]', v).value.trim() || '0');
      }
      s.shot = s.shot || {};
      $$('[data-shot]', v).forEach((inp) => { s.shot[inp.dataset.shot] = inp.value; });
    });
  };
  ciz();
  $('#sc-vuruslar').addEventListener('click', async (e) => {
    const b = e.target.closest('[data-eylem]');
    if (!b) return;
    oku();
    const i = +b.closest('.vurus-duz').dataset.i;
    const L = sc.sentences;
    if (b.dataset.eylem === 'sil') { const not = await onaySor(b, {soru: 'Bu vuruş silinsin mi?', evet: 'Sil', tehlike: true}); if (not === null) return; L.splice(i, 1); }
    if (b.dataset.eylem === 'yukari' && i > 0) [L[i - 1], L[i]] = [L[i], L[i - 1]];
    if (b.dataset.eylem === 'asagi' && i < L.length - 1) [L[i + 1], L[i]] = [L[i], L[i + 1]];
    if (b.dataset.eylem === 'ekle') {
      const ids = new Set(L.map((s) => s.id));
      let n = L.length + 1;
      const on = anlatimli ? 's' : 'b';
      while (ids.has(on + n)) n++;
      L.splice(i + 1, 0, anlatimli ? {id: on + n, step: L[i].step, pauseAfter: 0.35, parts: [{text: ''}], shot: {}} : {id: on + n, step: L[i].step, bas: L[i].bit, bit: L[i].bit, shot: {}});
    }
    ciz();
  });
  $('#sc-kaydet').addEventListener('click', async () => {
    oku();
    try { await kaydet('script.json', JSON.stringify(sc)); levhaKapat(); } catch (e) { bildir(`Kaydedilemedi: ${e.message}`, 6000); }
  });
}
function gorunusLevha() {
  const g = W.d.gorunus;
  g.secenekler.forEach((s) => { fontYukle(s.yazi?.baslik?.aile); fontYukle(s.yazi?.govde?.aile); });
  levhaAc(`<div class="levha-bas"><div><h2 id="levha-baslik">Görünüş</h2><p>Aynı kanca karesi, üç ayrı görünüşte: renk, yazı, doku ve ışık. Claude üçünü de önerir ve gerekçesini söyler; seçim senin. Sonra değiştirebilirsin.</p></div>${kapatDugme}</div>
    <div class="gorunus-izgara">${g.secenekler.map((s) => {
    const r = s.renk || {};
    const y = s.yazi || {};
    return `<article class="gorunus-kart ${g.secim === s.harf ? 'secili' : ''}">
      <div class="kg">${g.kareler?.[s.harf] ? `<img src="${kucukUrl(g.kareler[s.harf], 600)}" alt="${s.harf.toUpperCase()} görünüşünde kanca karesi">` : ''}</div>
      <h3>${s.harf.toUpperCase()} · ${esc(s.ad)}</h3><p>${esc(s.fikir)}</p>
      <div><div class="renkler">${Object.values(r).filter((c) => typeof c === 'string').slice(0, 5).map((c) => `<span style="background:${esc(c)}" data-hex="${esc(c)}" title="${esc(c)}"></span>`).join('')}</div>
      ${y.baslik ? `<div class="yazi-ornek" style="background:${esc(r.kagit || r.arka || '')};color:${esc(r.murekkep || '')};margin-top:26px"><span class="yb" style="font-family:'${esc(y.baslik.aile)}',Georgia,serif;font-weight:${y.baslik.agirlik || 700}">${esc((W.d.baslik || '').slice(0, 40))}</span>${y.govde ? `<span class="yg" style="font-family:'${esc(y.govde.aile)}',Georgia,serif;font-weight:${y.govde.agirlik || 500}">${esc((W.d.script.learningGoal || '').slice(0, 90))}</span>` : ''}<small>Başlık ${esc(y.baslik.aile)}${y.govde ? ` · gövde ${esc(y.govde.aile)}` : ''}</small></div>` : ''}</div>
      <button type="button" class="btn ${g.secim === s.harf ? 'cam-btn' : 'ana-btn'}" data-gorunus-sec="${s.harf}">${g.secim === s.harf ? `${ik('tik')}Seçili` : 'Bunu seç'}</button></article>`;
  }).join('')}</div>`);
  $$('[data-gorunus-sec]', $('#levha')).forEach((b) => b.addEventListener('click', async () => {
    try { await api.post(`/api/video/${W.id}/gorunus`, {secim: b.dataset.gorunusSec}); bildir('Görünüş seçildi.'); await yenidenYukle(); gorunusLevha(); } catch (e) { bildir(e.message, 6000); }
  }));
}
async function goruntuYukle(input) {
  const f = input.files[0];
  const q = new URLSearchParams({ad: f.name, kaynak: $('#g-kaynak').value, kisi: $('#g-kisi').value, riza: $('#g-riza').value, not: $('#g-not').value.trim()});
  bildir(`${f.name} yükleniyor…`);
  try {
    const j = await api.post(`/api/video/${W.id}/goruntu?${q}`, await f.arrayBuffer(), true);
    isIzle(j, () => { bildir('Görüntü eklendi: ölçüldü, kontak tabakası çizildi.'); yenidenYukle(); });
  } catch (er) { bildir(er.message, 6500); }
  input.value = '';
}

async function yukle(input, tur) {
  for (const f of input.files) {
    try { await api.post(`/api/video/${W.id}/yukle?tur=${tur}&ad=${encodeURIComponent(f.name)}`, await f.arrayBuffer(), true); } catch (e) { bildir(e.message, 6000); return; }
  }
  bildir(tur === 'varlik' ? 'Yüklendi. Şimdi varlık listesine ekle ve onayla.' : 'Yüklendi.');
  await yenidenYukle();
}

// Çalışma alanındaki tıklamalar
$('#v-film').addEventListener('click', async (e) => {
  const t = e.target;
  const c = (s) => t.closest(s);
  let b;
  if ((b = c('[data-asama]'))) { W.asama = b.dataset.asama; history.replaceState(null, '', `#/film/${W.id}/${W.asama}`); yolCiz(); denetciCiz(); return; }
  if ((b = c('[data-asama-git]'))) { W.asama = b.dataset.asamaGit; history.replaceState(null, '', `#/film/${W.id}/${W.asama}`); yolCiz(); denetciCiz(); return; }
  if ((b = c('[data-fmt]'))) { W.fmt = b.dataset.fmt; formatSecCiz(); kaynakAyarla(simdikiT()); zamanCiz(); oynatmaGuncelle(simdikiT(), true); if (['kareler', 'rotus'].includes(W.asama)) denetciCiz({kaydirma: true}); return; }
  if ((b = c('#menu-dugme'))) { const m = $('#arac-menu'); m.hidden = !m.hidden; b.setAttribute('aria-expanded', String(!m.hidden)); return; }
  if ((b = c('[data-menu-eylem]'))) {
    $('#arac-menu').hidden = true;
    const k = b.dataset.menuEylem;
    if (k === 'hizli') hizliLevha(W.id);
    if (k === 'claude-metin') kopyala(W.d.claude);
    if (k === 'klasor') kopyala(`studio/videos/${W.id}`);
    if (k === 'kataloga') katalogaLevha();
    if (k === 'deterministik') { komut(W.id, 'deterministik', {}, 'Kararlılık testi', yenidenYukle).catch((er) => bildir(er.message, 6000)); if (W.d.plaka) plakaIzle(); }
    if (k === 'blender-ac') komut(W.id, 'blender-ac', {}, "Sahne Blender'da açılıyor").then(() => bildir('Blender açılıyor: sahne kamera görünümünde kurulur (birkaç saniye). Değişiklikleri Claude\'a söyle; Blender\'da kaydedilen dosya filme girmez.', 6500)).catch((er) => bildir(er.message, 6000));
    if (k === 'remotion') {
      try {
        const r = await api.post('/api/remotion');
        if (r.is) isIzle(r.is);
        bildir(r.durum === 'açık' ? 'Remotion Studio açılıyor.' : 'Remotion Studio başlatılıyor (birkaç saniye)…');
        setTimeout(() => window.open(r.url, '_blank'), r.durum === 'açık' ? 50 : 6000);
      } catch (er) { bildir(er.message, 6000); }
    }
    return;
  }
  if ((b = c('[data-vurus]'))) { const i = +b.dataset.vurus; W.acikV = W.acikV === i ? null : i; if (W.vurus[i].bas != null) git(W.vurus[i].bas + 0.01); denetciCiz({kaydirma: true}); return; }
  if ((b = c('[data-klip]'))) return;
  if ((b = c('[data-git]'))) { git(+b.dataset.git); return; }
  if ((b = c('[data-kusur]'))) {
    const k = W.kusurlar.find((x) => x.n === +b.dataset.kusur);
    if (!k) return;
    W.secKusur = k.n;
    if (W.asama !== 'rotus') { W.asama = 'rotus'; yolCiz(); }
    denetciCiz({kaydirma: W.asama === 'rotus'});
    if (k.t != null) git(k.t + 0.01);
    return;
  }
  if ((b = c('[data-gorunus-ac]'))) { gorunusLevha(); return; }
  if ((b = c('[data-yol-ac]'))) { yolLevha(); return; }
  if ((b = c('[data-yol-sec]'))) { yolSec(b, b.dataset.yolSec); return; }
  if ((b = c('[data-yol-fmt]'))) { W.yolFmt = b.dataset.yolFmt; if (W.d.formatlar.includes(W.yolFmt) && W.fmt !== W.yolFmt) { W.fmt = W.yolFmt; formatSecCiz(); kaynakAyarla(simdikiT()); zamanCiz(); } denetciCiz({kaydirma: true}); return; }
  if ((b = c('[data-yol-goster]'))) { W.yolGoster = b.dataset.yolGoster; sonKareYol = null; kaynakAyarla(simdikiT()); kareGoster(simdikiT()); denetciCiz({kaydirma: true}); return; }
  if ((b = c('[data-yol-iste]'))) { const m = $('#claude-metin'); m.value = BASKA_YOLLAR; m.focus(); m.setSelectionRange(m.value.length, m.value.length); bildir('Hazır metin “Claude’a söyle” alanında: istersen ekle ve gönder.'); return; }
  if ((b = c('[data-yol-tamamla]'))) {
    b.disabled = true;
    try { await api.post(`/api/video/${W.id}/gorunus`, {secim: W.d.gorunus.secim, tamamla: true}); bildir('Claude planı bu yolda tamamlıyor.'); genelTazele(); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); b.disabled = false; }
    return;
  }
  if ((b = c('[data-duzenle]'))) { duzenleyiciAc(b.dataset.duzenle); return; }
  if ((b = c('[data-kataloga]'))) { katalogaLevha(); return; }
  if ((b = c('[data-goruntu-cozum], [data-goruntu-riza]'))) {
    const govde = b.dataset.goruntuCozum ? {ad: b.dataset.ad, cozum: b.dataset.goruntuCozum} : {ad: b.dataset.ad, riza: b.dataset.goruntuRiza};
    try { await api.post(`/api/video/${W.id}/goruntu-riza`, govde); bildir('Kaydedildi: Claude görüntüyü bu karara göre kullanır.'); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-takip]'))) {
    const alt = b.dataset.takip, kutu = b.closest('.takip-cozum, .goruntu-varlik');
    const yuk = Number(kutu?.querySelector('[data-takip-yuk]')?.value || 1.5);
    b.disabled = true;
    try {
      const j = await api.post(`/api/video/${W.id}/takip/${alt}`, {ad: b.dataset.ad, yukseklik: yuk, kip: b.dataset.kip});
      if (j.id) {
        bildir({coz: 'Kamera takibi başladı (~5–8 dk); ilerleme sağ altta.', olcek: 'Ölçek uygulanıyor: ızgara birazdan yeni ölçekle çizilir.', nesne: 'Nesne çekimin üstünde çiziliyor.', elle: 'Elle izlerle çözülüyor.'}[alt] || 'Başladı.', 5000);
        isIzle(j, (s_) => { bildir(s_.durum === 'bitti' ? 'Kamera takibi işi bitti.' : 'Kamera takibi işi başarısız: neden sağ altta.', 6000); yenidenYukle(); });
      } else {
        bildir(alt === 'ac' ? "Blender açılıyor: izleri düzelt, kaydet (⌘S), sonra buraya dön." : 'Kaydedildi.', 6000);
        await yenidenYukle();
      }
    } catch (er) { bildir(er.message, 6000); b.disabled = false; }
    return;
  }
  if (t.closest('[data-yapim-baslat], [data-yapim-onizle]')) { await yapimTikla(t); return; }
  if (t.closest('[data-kisi-dosya], [data-kisi-esleme-kaydet], [data-kisi-karar-kaydet], [data-kisi-onizle], [data-kisi-baslat], [data-kisi-sil]')) { await kisiTikla(t); return; }
  if ((b = c('[data-veri-cek]'))) {
    b.disabled = true;
    try {
      const j = await api.post(`/api/video/${W.id}/veri-cek`, {});
      isIzle(j, (s) => { bildir(s.durum === 'bitti' ? 'Veri yenilendi: film en yeni görüntüyle çizilecek (ayrıntı sağ altta).' : 'Yeni veri alınamadı: film önceki görüntüyle kalıyor (neden sağ altta).', 6000); yenidenYukle(); });
    } catch (er) { bildir(er.message, 6000); b.disabled = false; }
    return;
  }
  if ((b = c('[data-veri-sec]'))) {
    try { await api.post(`/api/video/${W.id}/veri-sec`, {kimlik: b.dataset.veriSec}); bildir('Seçildi: film bu görüntüyle çizilecek (kareleri yeniden çizmek için Kurgu adımı).', 5000); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-kredi-kaydet]'))) {
    try { await api.post(`/api/video/${W.id}/kredi-siniri`, {kredi_siniri: $('#kredi-siniri').value}); bildir('Kredi sınırı kaydedildi.'); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-analitik-gonder]'))) { analitikGonder(b); return; }
  if ((b = c('[data-analitik-basla]'))) { b.disabled = true; analitikBasla(b.dataset.analitikBasla).catch((er) => { bildir(er.message, 6000); b.disabled = false; }); return; }
  if ((b = c('[data-yayin-kaydet]'))) {
    try { await api.post(`/api/video/${W.id}/yayin-tarihi`, {tarih: $('#an-yayin').value}); bildir('Yayın tarihi kaydedildi.'); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-senaryo-duzenle]'))) { senaryoDuzenleyici(); return; }
  if ((b = c('[data-komut]'))) {
    const k = b.dataset.komut;
    const ekstra = k === 'muzik' ? {bpm: $('#muzik-bpm')?.value, yapi: $('#muzik-yapi')?.value} : {};
    b.disabled = true;
    try { await komut(W.id, k, ekstra, b.textContent.trim(), yenidenYukle); if (W.d.plaka) plakaIzle(); } catch (er) { bildir(er.message, 6000); }
    setTimeout(() => { b.disabled = false; }, 1500);
    return;
  }
  if ((b = c('#ses-kaydet'))) {
    const sc = JSON.parse(JSON.stringify(W.d.script));
    const s = W.d.ses;
    const kay = $('#ses-kaynak').value;
    const yeni = {...(sc.ses || {}), kaynak: kay};
    if (kay === 'edge') Object.assign(yeni, {voice: $('#ses-voice').value, rate: $('#ses-rate').value, pitch: s.pitch || '-2Hz'});
    if (kay === 'opencode') Object.assign(yeni, {voice: s.kaynak === 'opencode' ? s.voice : 'Kore', ...(s.model ? {model: s.model} : {})});
    if (kay !== 'edge' && kay !== 'opencode') ['voice', 'rate', 'pitch'].forEach((x) => delete yeni[x]);
    if (kay === 'magnific') Object.assign(yeni, s.kaynak === 'magnific' ? {voice: s.voice, ses_adi: s.ses_adi, model: s.model} : {voice: 1039, ses_adi: 'Serkan Yıldırım', model: 'eleven_v3'});
    if (kay !== 'magnific') ['ses_adi', 'model'].forEach((x) => delete yeni[x]);
    const mz = $('#ses-muzik').value.trim();
    if (mz) yeni.muzik = mz; else delete yeni.muzik;
    const db = $('#ses-muzik-db').value.trim();
    if (db) yeni.muzik_db = parseFloat(db); else delete yeni.muzik_db;
    sc.ses = yeni;
    ['voice', 'rate', 'pitch'].forEach((x) => delete sc[x]);
    try { await kaydet('script.json', JSON.stringify(sc)); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-plan-onay]'))) {
    const not = await onaySor(b, {soru: 'Kapı 1 ve 2 senin onayınla kapanır, Claude filmi üretmeye başlar.', evet: 'Onayla ve üret'});
    if (not === null) return;
    try { await api.post(`/api/basit/${W.id}/onay`, {asama: 'plan'}); bildir('Plan onaylandı; Claude üretime başladı.'); genelTazele(); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-kapi-onay]'))) {
    const n = +b.dataset.kapiOnay;
    const not = await onaySor(b, {soru: n === 6 ? 'Kapı 6 kapanır: film teslim edilmiş sayılır. Yüklemeyi sen yaparsın.' : `Kapı ${n} senin onayınla kapanır.`, evet: 'Onayla', not: true});
    if (not === null) return;
    try { await api.post(`/api/video/${W.id}/kapi`, {n, not: not || (n === 6 ? 'panel: video onayı' : 'panel')}); bildir(`Kapı ${n} onaylandı.`); genelTazele(); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-claude-devam]'))) {
    try { await api.post(`/api/basit/${W.id}/devam`, {}); bildir('Claude kaldığı yerden devam ediyor.'); genelTazele(); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-rotus]'))) {
    const son = sonInceleme(W.d);
    const not = await onaySor(b, {soru: 'Claude son incelemedeki açık kusurları onarır, etkilenen kareleri ve filmi yeniden render eder, yeniden ölçer.', evet: 'Onarsın'});
    if (not === null) return;
    try {
      await api.post(`/api/basit/${W.id}/degisiklik`, {metin: `Son incelemedeki (inceleme/${son?.ad}/inceleme.md) açık kusurları onar: önce etkilenen kareler, sonra ./st inceleme ve ./st elestir ile yeniden ölç; final render ve yayin.md'yi güncelle.`});
      bildir("Claude'a gönderildi."); genelTazele(); await yenidenYukle();
    } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('[data-durdur]'))) {
    const not = await onaySor(b, {soru: 'Claude durdurulsun mu? Yaptıkları kalır; sonra “Claude devam etsin” diyebilirsin.', evet: 'Durdur', tehlike: true});
    if (not === null) return;
    try { await api.post(`/api/is/${b.dataset.durdur}/durdur`); bildir('Claude durduruldu.'); await yenidenYukle(); } catch (er) { bildir(er.message, 6000); }
    return;
  }
  if ((b = c('.oneri'))) { $('#claude-metin').value = b.textContent; $('#claude-metin').focus(); }
});
$('#v-film').addEventListener('change', (e) => {
  const gd = e.target.closest('[data-goruntu-dosya]');
  if (gd && gd.files.length) { goruntuYukle(gd); return; }
  const kd = e.target.closest('[data-kisi-yukle]');
  if (kd && kd.files.length) { kisiYukle(kd); return; }
  const i = e.target.closest('[data-yukle]');
  if (i) yukle(i, i.dataset.yukle);
  if (e.target.id === 'an-dosya') $('#an-dosya-ad').textContent = [...e.target.files].map((f) => f.name).join(', ');
});
$('#claude-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const m = $('#claude-metin').value.trim();
  if (!m) return;
  const v = W.vurus[W.aktifV];
  const baglam = `[${ADIMLAR.find((a) => a.k === W.asama).ad} adımı${['senaryo', 'kareler', 'rotus'].includes(W.asama) && v ? ` · ${v.id} ${v.adim}` : ''} · ${tc(simdikiT())} · ${fmtEtiket(W.fmt)}]`;
  try {
    await api.post(`/api/basit/${W.id}/degisiklik`, {metin: `${baglam} ${m}`});
    $('#kuyruk').innerHTML = `<div>${esc(m)}</div><small>Claude'a gönderildi · ${esc(baglam.slice(1, -1))}</small>`;
    $('#claude-metin').value = '';
    bildir("Claude'a gönderildi.");
    genelTazele(); await yenidenYukle();
  } catch (er) { bildir(er.message, 6000); }
});
document.addEventListener('keydown', (e) => {
  if ($('#v-film').hidden || !$('#perde').hidden) return;
  if (e.target.closest('input, textarea, select, [contenteditable]')) return;
  if (e.key === ' ' && !e.target.closest('button, a')) { e.preventDefault(); oynatDurdur(); }
  if (e.key === 'ArrowRight') { e.preventDefault(); vurusAtla(1); }
  if (e.key === 'ArrowLeft') { e.preventDefault(); vurusAtla(-1); }
});
document.addEventListener('is-bitti', (e) => { if (!$('#v-film').hidden && e.detail.video === W.id) yenidenYukle().catch(() => {}); });

// Claude çalışırken günlüğü canlı tut; bitince alanı tazele
function claudeIzle() {
  clearTimeout(W.tik);
  if (!claudeCalisiyor()) return;
  const id = W.id;
  W.tik = setTimeout(async () => {
    if ($('#v-film').hidden || W.id !== id) return;
    try {
      const b = await api.get(`/api/basit/${id}`);
      if (!(b.claude && b.claude.durum === 'çalışıyor')) { genelTazele(); return yenidenYukle(); }
      W.d.basit = b;
      const g = $('[data-gunluk]', $('#den-govde'));
      if (g) { g.textContent = (b.claude.satirlar || []).join('\n'); g.scrollTop = g.scrollHeight; }
    } catch (e) { /* bir sonraki turda yeniden dener */ }
    claudeIzle();
  }, 3500);
}

// ---------------------------------------------------------------- klasörü olmayan istek (Claude planı hazırlıyor ya da başlamadı)
async function istekSayfasi(id) {
  gorunumGoster('v-sayfa');
  $('#app').classList.remove('odak');
  const d = await api.get(`/api/basit/${id}`);
  const calisiyor = d.claude && d.claude.durum === 'çalışıyor';
  $('#v-sayfa').innerHTML = `${ustCubuk(esc(d.baslik), `${durumNokta(d)} ${esc(d.durumBaslik)}`)}
    <div class="istek-sayfa">
      <p class="ince">${esc(d.durumAciklama)}</p>
      ${calisiyor ? claudeKartHtml(d.claude) : ''}
      ${d.istek ? `<div class="blok"><h3>İsteğin</h3><div class="istek-metni">${esc(d.istek)}</div></div>` : ''}
      ${!calisiyor && d.claudeSon ? `<div class="blok"><h3>Claude'un son mesajı</h3><div class="durum-md">${md(d.claudeSon)}</div></div>` : ''}
      ${!calisiyor && d.claude?.satirlar?.length ? `<details class="aac"><summary>${ik('sag')}Son günlük</summary><div class="gunluk">${esc(d.claude.satirlar.join('\n'))}</div></details>` : ''}
      <div class="dugmeler" id="istek-eylem">${d.durum === 'baslamadi' ? '<button class="btn ana-btn buyuk" type="button" data-i-eylem="basla">Başlat</button><button class="btn cam-btn buyuk" type="button" data-i-eylem="sil">İsteği sil</button>'
    : !calisiyor ? '<button class="btn ana-btn buyuk" type="button" data-i-eylem="devam">Devam ettir</button>' : ''}<a class="btn cam-btn buyuk" href="#/filmler">Filmlere dön</a></div>
    </div>`;
  simgele($('#v-sayfa'));
  const L = $('#v-sayfa');
  $$('[data-i-eylem]', L).forEach((b) => b.addEventListener('click', async () => {
    const e = b.dataset.iEylem;
    if (e === 'sil') {
      const not = await onaySor(b, {soru: 'Bu istek ve ekli dosyaları silinsin mi? Geri alınamaz.', evet: 'Sil', tehlike: true});
      if (not === null) return;
      try { await api.post(`/api/basit/${id}/sil`); bildir('İstek silindi.'); genelTazele(); location.hash = '#/filmler'; } catch (er) { bildir(er.message, 6000); }
      return;
    }
    try { await api.post(`/api/basit/${id}/${e}`, {}); bildir('Claude başladı.'); genelTazele(); istekSayfasi(id); } catch (er) { bildir(er.message, 6000); }
  }));
  $$('[data-durdur]', L).forEach((b) => b.addEventListener('click', async () => {
    const not = await onaySor(b, {soru: 'Claude durdurulsun mu?', evet: 'Durdur', tehlike: true});
    if (not === null) return;
    try { await api.post(`/api/is/${b.dataset.durdur}/durdur`); istekSayfasi(id); } catch (er) { bildir(er.message, 6000); }
  }));
  if (calisiyor) {
    const t = setTimeout(async () => {
      if (!location.hash.startsWith(`#/film/${id}`)) return;
      try { await api.get(`/api/video/${id}`); location.hash = `#/film/${id}`; yonlendir(); } catch { istekSayfasi(id); }
    }, 4000);
    ayrilinca = () => clearTimeout(t);
  }
}
