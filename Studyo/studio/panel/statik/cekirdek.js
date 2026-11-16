// Stüdyo paneli · çekirdek: yardımcılar, API, simgeler, levhalar, arka plan işleri, yönlendirme (derlemesiz)
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const surum = () => Date.now().toString(36);
const dosyaUrl = (rel, taze = false) => `/dosya?yol=${encodeURIComponent(rel)}${taze ? '&v=' + surum() : ''}`;
const kucukUrl = (rel, w = 360) => `/kucuk?yol=${encodeURIComponent(rel)}&w=${w}`;

const api = {
  async get(u) {
    const r = await fetch(u);
    const j = await r.json();
    if (!r.ok) throw new Error(j.hata || r.statusText);
    return j;
  },
  async post(u, body, ham = false) {
    const r = await fetch(u, {method: 'POST', body: ham ? body : JSON.stringify(body ?? {}), headers: ham ? {} : {'Content-Type': 'application/json'}});
    const j = await r.json();
    if (!r.ok) throw new Error(j.hata || r.statusText);
    return j;
  },
};

// ---------------------------------------------------------------- simgeler (SF Symbols havasında, çizgi)
const IK = {
  film: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7.5 4v16M16.5 4v16M3 9.5h4.5M3 14.5h4.5M16.5 9.5H21M16.5 14.5H21"/>',
  saat: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  arsiv: '<rect x="3" y="4" width="18" height="5" rx="1.5"/><path d="M5 9v9a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9M10 13h4"/>',
  gorsel: '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="9" cy="10" r="1.8"/><path d="M21 15.5l-4.5-4.5L8 19.5"/>',
  hareket: '<path d="M4 18L14 8"/><path d="M15.5 3.5v3M20.5 8.5h-3M18.6 5.4l-2 2"/><path d="M9 4.5l.6 1.7 1.7.6-1.7.6L9 9.1l-.6-1.7-1.7-.6 1.7-.6z"/>',
  ses: '<path d="M4 10v4M8 7v10M12 4v16M16 8v8M20 11v2"/>',
  profil: '<rect x="4" y="9" width="16" height="11" rx="2.5"/><path d="M6.5 6h11M9 3.5h6"/>',
  kitap: '<path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v14.5H6.5A1.5 1.5 0 0 0 5 19z"/><path d="M5 19a1.5 1.5 0 0 0 1.5 1.5H19V17.5"/>',
  claude: '<path d="M12 3.5l1.7 5 5 1.7-5 1.7-1.7 5-1.7-5-5-1.7 5-1.7z"/><path d="M18.5 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/>',
  arti: '<path d="M12 5.5v13M5.5 12h13"/>',
  eksi: '<path d="M5.5 12h13"/>',
  oynat: '<path class="d" d="M8 5.2v13.6c0 .6.7 1 1.2.6l10.4-6.8c.5-.3.5-1 0-1.3L9.2 4.6C8.7 4.3 8 4.6 8 5.2z"/>',
  dur: '<rect class="d" x="6.5" y="5" width="4" height="14" rx="1.2"/><rect class="d" x="13.5" y="5" width="4" height="14" rx="1.2"/>',
  geri: '<path d="M18 6.5v11l-8-5.5z"/><path d="M7 6.5v11"/>',
  ileri: '<path d="M6 6.5v11l8-5.5z"/><path d="M17 6.5v11"/>',
  sol: '<path d="M14.5 5.5L8 12l6.5 6.5"/>',
  sag: '<path d="M9.5 5.5L16 12l-6.5 6.5"/>',
  tik: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  kisi: '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c1.2-3.5 4-5 7-5s5.8 1.5 7 5"/>',
  unlem: '<path d="M12 7v6.5M12 17v.3"/>',
  kenar: '<rect x="3" y="4.5" width="18" height="15" rx="3"/><path d="M9 4.5v15"/>',
  paylas: '<path d="M12 14.5V3.5M7.5 7.5L12 3l4.5 4.5"/><path d="M6 11H5.5a1.5 1.5 0 0 0-1.5 1.5v6A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5v-6a1.5 1.5 0 0 0-1.5-1.5H18"/>',
  telefon: '<rect x="7" y="3" width="10" height="18" rx="2.5"/>',
  tv: '<rect x="3" y="5.5" width="18" height="11" rx="2"/><path d="M9 20h6"/>',
  kare: '<rect x="5" y="5" width="14" height="14" rx="2.5"/>',
  portre: '<rect x="6" y="4" width="12" height="15" rx="2.5"/>',
  katman: '<rect x="6.5" y="3" width="11" height="18" rx="2.5"/><path d="M6.5 7.5h11M6.5 15.5h11M14.5 7.5v8"/>',
  atac: '<path d="M20 11.5l-8 8a5 5 0 0 1-7-7L13.2 4.3a3.3 3.3 0 0 1 4.7 4.7l-8.1 8.1a1.7 1.7 0 0 1-2.4-2.4l7.4-7.4"/>',
  yukari: '<path d="M12 19V5.5M6.5 11L12 5.5l5.5 5.5"/>',
  kapat: '<path d="M7 7l10 10M17 7L7 17"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  goz: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
  sagok: '<path d="M5 12h13M13 7l5 5-5 5"/>',
  soru: '<circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.5a2.5 2.5 0 0 1 4.8.8c0 1.7-2.4 2.1-2.4 3.7M12 16.8v.2"/>',
  nokta3: '<circle class="d" cx="6" cy="12" r="1.6"/><circle class="d" cx="12" cy="12" r="1.6"/><circle class="d" cx="18" cy="12" r="1.6"/>',
  indir: '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>',
  kopya: '<rect x="8" y="8" width="12" height="12" rx="2.5"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  kalem: '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  yenile: '<path d="M4.5 12a7.5 7.5 0 0 1 13-5.1L19.5 9M19.5 4v5h-5"/><path d="M19.5 12a7.5 7.5 0 0 1-13 5.1L4.5 15M4.5 20v-5h5"/>',
  dosya: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
};
const ik = (ad, cls = '') => {
  const p = IK[ad] || '';
  const dolu = p.includes('class="d"');
  return `<svg class="ik ${dolu ? 'dolu' : ''} ${cls}" viewBox="0 0 24 24" aria-hidden="true">${p.replace(/ class="d"/g, '')}</svg>`;
};
const simgele = (kok = document) => $$('[data-ik]', kok).forEach((el) => { el.outerHTML = ik(el.dataset.ik); });
const FORMAT_IK = {'9x16': 'telefon', '16x9': 'tv', '1x1': 'kare', '4x5': 'portre'};
const FORMAT_AD = {'9x16': 'Dikey', '16x9': 'Yatay', '1x1': 'Kare', '4x5': 'Portre'};
const fmtOran = (f) => { const [a, b] = String(f || '9x16').split('x').map(Number); return a / b || 9 / 16; };
const fmtEtiket = (f) => String(f).replace('x', ':');

// ---------------------------------------------------------------- biçim
const sn = (x, b = 1) => Number(x || 0).toFixed(b).replace('.', ',');
const MOTOR_AD = {remotion: 'Remotion', hyperframes: 'HyperFrames', blender: 'Blender', manim: 'Manim'};
const tc = (t) => { t = Math.max(0, t || 0); const m = Math.floor(t / 60); const s = t - m * 60; return `${String(m).padStart(2, '0')}:${s.toFixed(2).padStart(5, '0').replace('.', ',')}`; };
const trKucuk = (s) => String(s || '').toLocaleLowerCase('tr-TR').replace(/[.,:;!?“”"'’()…]/g, '');
const TR_HARF = {ç: 'c', ğ: 'g', ı: 'i', ö: 'o', ş: 's', ü: 'u', â: 'a', î: 'i', û: 'u'};
const slug = (s) => String(s).toLocaleLowerCase('tr-TR').replace(/[çğıöşüâîû]/g, (c) => TR_HARF[c]).replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40);
const gun = (iso) => { if (!iso) return ''; const [y, a, g] = String(iso).split('-'); const AY = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']; return `${+g} ${AY[+a - 1] || ''}`; };

let bildirimZ = null;
function bildir(m, ms = 3200) {
  const b = $('#bildirim');
  b.innerHTML = `${ik('claude')}<span>${esc(m)}</span>`;
  b.classList.add('acik');
  clearTimeout(bildirimZ);
  bildirimZ = setTimeout(() => b.classList.remove('acik'), ms);
}
async function kopyala(t) {
  try { await navigator.clipboard.writeText(t); bildir('Kopyalandı.'); } catch { bildir('Kopyalanamadı: metni elle seç.'); }
}

// ---------------------------------------------------------------- markdown (belgelerimizin kullandığı kadarı)
function satirIci(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, a, b) => `<a href="${b.startsWith('http') ? b : '#'}" target="_blank" rel="noopener">${a}</a>`);
}
function md(text) {
  const L = String(text || '').replace(/\r/g, '').split('\n');
  let out = '', i = 0;
  while (i < L.length) {
    const l = L[i];
    if (/^```/.test(l)) {
      let j = i + 1;
      const buf = [];
      while (j < L.length && !/^```/.test(L[j])) buf.push(L[j++]);
      out += `<pre><code>${esc(buf.join('\n'))}</code></pre>`;
      i = j + 1; continue;
    }
    if (/^#{1,4} /.test(l)) { const n = l.match(/^#+/)[0].length; out += `<h${n}>${satirIci(l.slice(n + 1))}</h${n}>`; i++; continue; }
    if (/^---+\s*$/.test(l)) { out += '<hr>'; i++; continue; }
    if (/^\|/.test(l)) {
      const rows = [];
      while (i < L.length && /^\|/.test(L[i])) rows.push(L[i++]);
      const cells = (r) => r.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
      const body = rows.filter((r) => !/^\|[\s\-:|]+\|$/.test(r));
      out += '<div class="tablo-kap"><table><thead><tr>' + cells(body[0]).map((c) => `<th>${satirIci(c)}</th>`).join('') + '</tr></thead><tbody>' +
        body.slice(1).map((r) => '<tr>' + cells(r).map((c) => `<td>${satirIci(c)}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>';
      continue;
    }
    if (/^> ?/.test(l)) {
      const buf = [];
      while (i < L.length && /^> ?/.test(L[i])) buf.push(L[i++].replace(/^> ?/, ''));
      out += `<blockquote>${buf.map((b) => `<p>${satirIci(b)}</p>`).join('')}</blockquote>`;
      continue;
    }
    if (/^\s*([-*]|\d+\.) /.test(l)) {
      const sirali = /^\s*\d+\./.test(l);
      const buf = [];
      while (i < L.length && /^\s*([-*]|\d+\.) /.test(L[i])) buf.push(L[i++].replace(/^\s*([-*]|\d+\.) /, ''));
      out += (sirali ? '<ol>' : '<ul>') + buf.map((b) => `<li>${satirIci(b)}</li>`).join('') + (sirali ? '</ol>' : '</ul>');
      continue;
    }
    if (!l.trim()) { i++; continue; }
    const buf = [];
    while (i < L.length && L[i].trim() && !/^(#{1,4} |\||> ?|```|\s*([-*]|\d+\.) )/.test(L[i])) buf.push(L[i++]);
    out += `<p>${satirIci(buf.join(' '))}</p>`;
  }
  return `<div class="md">${out}</div>`;
}
// markdown tablosunu satırlara çevirir: [{başlık: hücre}]
function mdTablo(text, baslikDeseni) {
  const L = String(text || '').split('\n');
  const i = L.findIndex((l) => /^\|/.test(l) && (!baslikDeseni || baslikDeseni.test(l)));
  if (i < 0) return [];
  const hucre = (r) => r.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
  const bas = hucre(L[i]);
  const out = [];
  for (let j = i + 1; j < L.length && /^\|/.test(L[j]); j++) {
    if (/^\|[\s\-:|]+\|$/.test(L[j])) continue;
    const h = hucre(L[j]);
    out.push(Object.fromEntries(bas.map((b, k) => [b, h[k] ?? ''])));
  }
  return out;
}
const sadeMetin = (s) => String(s || '').replace(/\*\*([^*]+)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1');

// ---------------------------------------------------------------- levha, büyütme, satır içi onay
let oncekiOdak = null;
let levhaKapaninca = null;
function levhaAc(html, cls = '', kapaninca = null) {
  oncekiOdak = document.activeElement;
  levhaKapaninca = kapaninca;
  const l = $('#levha');
  l.className = `levha cam-guclu ${cls}`;
  l.innerHTML = html;
  simgele(l);
  $('#perde').hidden = false;
  setTimeout(() => (l.querySelector('[autofocus]') || l.querySelector('.kapat'))?.focus(), 30);
  return l;
}
function levhaKapat() {
  const p = $('#perde');
  if (p.hidden) return;
  $$('video, audio', p).forEach((m) => m.pause());
  sesDur();
  p.hidden = true;
  $('#levha').innerHTML = '';
  const k = levhaKapaninca;
  levhaKapaninca = null;
  k?.();
  oncekiOdak?.focus?.();
}
const kapatDugme = `<button class="ikon-btn kapat" type="button" data-kapat aria-label="Kapat">${ik('kapat')}</button>`;
function buyut(src) { const b = $('#buyut'); $('img', b).src = src; b.hidden = false; }

/** Düğmenin yerine küçük bir onay kutusu açar; "Evet"e basılırsa notu (ya da '') döner, vazgeçilirse null. */
function onaySor(btn, {soru, evet = 'Evet', not = false, notYer = 'İsteğe bağlı not', tehlike = false} = {}) {
  return new Promise((coz) => {
    const kutu = document.createElement('div');
    kutu.className = 'onay-not';
    kutu.innerHTML = `<p class="ince" style="color:var(--yazi-2)">${soru}</p>${not ? `<textarea class="girdi" rows="2" placeholder="${esc(notYer)}" style="min-height:64px"></textarea>` : ''}
      <div class="dugmeler"><button type="button" class="btn ${tehlike ? 'uyari-btn' : 'ana-btn'}" data-e>${esc(evet)}</button><button type="button" class="btn cam-btn" data-h>Vazgeç</button></div>`;
    btn.hidden = true;
    btn.after(kutu);
    $('textarea', kutu)?.focus();
    const bitir = (v) => { kutu.remove(); btn.hidden = false; coz(v); };
    $('[data-e]', kutu).addEventListener('click', () => bitir($('textarea', kutu)?.value.trim() ?? ''));
    $('[data-h]', kutu).addEventListener('click', () => bitir(null));
  });
}

// ---------------------------------------------------------------- ortak ses çalar (katalog önizlemeleri)
const calar = new Audio();
let calanAnahtar = null;
function calSimgele() { $$('[data-cal]').forEach((b) => { const on = b.dataset.cal === calanAnahtar; b.classList.toggle('caliyor', on); b.closest('.ses-satir')?.classList.toggle('caliyor', on); }); }
function sesCal(anahtar, src) {
  if (calanAnahtar === anahtar) { calar.pause(); calanAnahtar = null; }
  else { calar.src = src; calanAnahtar = anahtar; calar.play().catch(() => { calanAnahtar = null; calSimgele(); bildir('Ses çalınamadı.'); }); }
  calSimgele();
}
function sesDur() { if (calanAnahtar) { calar.pause(); calanAnahtar = null; calSimgele(); } }
calar.addEventListener('ended', () => { calanAnahtar = null; calSimgele(); });
const calDugme = (anahtar, src, etiket, cls = '') => `<button type="button" class="cal ${cls} ${calanAnahtar === anahtar ? 'caliyor' : ''}" data-cal="${anahtar}" data-src="${src}" aria-label="${esc(etiket)}"><span class="i-oynat">${ik('oynat')}</span><span class="i-dur">${ik('dur')}</span></button>`;

// ---------------------------------------------------------------- arka plan işleri (Etkinlik)
const ISLER = new Map();
function isIzle(j, bitince, {offset = 0} = {}) {
  if (!j || !j.id) return;
  if (ISLER.has(j.id)) { if (bitince) ISLER.get(j.id).bitince.push(bitince); return; }
  const el = document.createElement('div');
  el.className = 'is-kart cam-guclu';
  el.innerHTML = `<div class="is-ust"><span class="nokta ${j.tur === 'claude' ? 'claude' : 'turuncu'}"></span><b>${esc(j.ad)}${j.video ? ` · ${esc(j.video)}` : ''}</b><span class="sure">0 sn</span><button class="ikon-btn" type="button" style="width:26px;height:26px" aria-label="Kapat">${ik('kapat')}</button></div><div class="gunluk"></div>`;
  $('#etkinlik').prepend(el);
  const log = $('.gunluk', el);
  const kayit = {offset, el, bitince: bitince ? [bitince] : []};
  ISLER.set(j.id, kayit);
  $('.is-ust', el).addEventListener('click', (e) => {
    if (e.target.closest('button')) { el.remove(); ISLER.delete(j.id); return; }
    el.classList.toggle('kapali');
  });
  const tur = async () => {
    if (!ISLER.has(j.id)) return;
    try {
      const s = await api.get(`/api/is/${j.id}?offset=${kayit.offset}`);
      if (s.satirlar.length) {
        log.textContent = (log.textContent ? log.textContent + '\n' : '') + s.satirlar.join('\n');
        if (log.textContent.length > 20000) log.textContent = log.textContent.slice(-12000);
        log.scrollTop = log.scrollHeight;
        kayit.offset = s.toplam;
      }
      $('.sure', el).textContent = s.sure >= 90 ? `${Math.round(s.sure / 60)} dk` : `${Math.round(s.sure)} sn`;
      if (s.durum === 'çalışıyor') return setTimeout(tur, 900);
      el.classList.add(s.durum === 'bitti' ? 'bitti' : 'hata');
      $('.nokta', el).className = `nokta ${s.durum === 'bitti' ? 'yesil' : ''}`;
      bildir(s.durum === 'bitti' ? `${j.ad} bitti` : `${j.ad} ${s.durum === 'durduruldu' ? 'durduruldu' : 'hata verdi: ayrıntı sağ altta'}`, 3800);
      if (s.durum === 'bitti') { setTimeout(() => el.classList.add('kapali'), 3500); setTimeout(() => { el.remove(); ISLER.delete(j.id); }, 25000); }
      kayit.bitince.forEach((f) => { try { f(s); } catch (e) { console.error(e); } });
      document.dispatchEvent(new CustomEvent('is-bitti', {detail: {...s, id: j.id, video: j.video}}));
      genelTazele();
    } catch (e) { setTimeout(tur, 1800); }
  };
  tur();
  genelTazele();
}
async function komut(vid, k, ekstra = {}, etiket = null, bitince = null) {
  const j = await api.post(`/api/video/${vid}/komut`, {komut: k, ad: etiket || undefined, ...ekstra});
  isIzle(j, bitince);
  return j;
}

// ---------------------------------------------------------------- genel durum, kenar çubuğu
let GENEL = null;
let GENEL_ZAMAN = 0;
async function genelYukle(taze = false) {
  if (!taze && GENEL && Date.now() - GENEL_ZAMAN < 2500) return GENEL;
  GENEL = await api.get('/api/genel');
  GENEL_ZAMAN = Date.now();
  kenarGuncelle(GENEL);
  return GENEL;
}
let tazeZ = null;
function genelTazele() { clearTimeout(tazeZ); tazeZ = setTimeout(() => genelYukle(true).catch(() => {}), 400); }

const BEKLEYEN_DURUM = ['yol_secim', 'plan_onay', 'video_onay', 'yarim'];
const CALISAN_DURUM = ['hazirlaniyor', 'yol_tamamlaniyor', 'uretiliyor'];
/** Kütüphanedeki her film: basit durumu (Claude ile akış) + klasör bilgisi (kapılar, poster, formatlar). */
function filmListesi(G) {
  const vm = Object.fromEntries(G.videolar.map((v) => [v.id, v]));
  const out = G.basit.map((b) => ({...(vm[b.id] || {}), ...b, klasor: !!vm[b.id], baslik: vm[b.id]?.baslik || b.baslik, poster: b.poster || vm[b.id]?.poster}));
  const var_ = new Set(out.map((x) => x.id));
  for (const v of G.videolar) if (!var_.has(v.id)) out.push({...v, klasor: true, durum: v.arsiv ? 'arsiv' : 'detay', durumBaslik: v.arsiv ? 'Arşivde' : (v.sirada ? `Sıradaki: ${v.sirada.ad}` : 'Bütün kapılar kapalı')});
  return out;
}
function kenarGuncelle(G) {
  const L = filmListesi(G);
  const bek = L.filter((x) => BEKLEYEN_DURUM.includes(x.durum)).length;
  $('#sayi-tum').textContent = L.filter((x) => !x.arsiv).length;
  const r = $('#sayi-bekleyen');
  r.textContent = bek;
  r.hidden = !bek;
  $('#sayi-arsiv').textContent = L.filter((x) => x.arsiv).length || '';
  for (const t of ['gorsel', 'animasyon', 'ses']) $(`#sayi-${t}`).textContent = (G.katalog[t] || []).length;
  $('#sayi-model').textContent = G.modelSayisi || '';
  if ($('#sayi-gecis')) $('#sayi-gecis').textContent = G.gecisSayisi || '';
  const calisan = (G.isler || []).filter((j) => j.durum === 'çalışıyor');
  const cl = calisan.filter((j) => j.tur === 'claude');
  $('#claude-durum').innerHTML = `${ik('claude')}<div><b>${!G.claudeVar ? 'Claude Code bulunamadı' : cl.length ? `Claude çalışıyor${cl.length > 1 ? ` · ${cl.length} iş` : ''}` : 'Claude hazır'}</b><span>${calisan.length ? `${calisan.length} iş sürüyor · ${esc(cl[0]?.video || calisan[0].ad)}` : 'Bu Mac\'te · ' + esc(G.claude?.varsayilan?.model || 'varsayılan model')}</span></div>`;
  if (cl.length) $('#claude-durum b').classList.add('parilti');
}

// ---------------------------------------------------------------- ortam ışığı
function ortam(tur, src) {
  const img = $('#ortam-img');
  const tv = $('#ortam-tuval');
  img.classList.toggle('acik', tur === 'img');
  tv.classList.toggle('acik', tur === 'tuval');
  if (tur === 'img' && src && img.dataset.src !== src) { img.dataset.src = src; img.src = src; }
}

// ---------------------------------------------------------------- yönlendirme
const SAYFA = {};          // sayfalar.js doldurur: ad → async (parçalar, sorgu)
let ayrilinca = null;      // açık görünümün temizliği (ör. çalışma alanında video durdur)
let KENAR_ACIK = false;    // çalışma alanında kenar çubuğu açık mı
function gorunumGoster(id) {
  $$('.gorunum').forEach((g) => { g.hidden = g.id !== id; });
  const g = document.getElementById(id);
  g.style.animation = 'none'; void g.offsetWidth; g.style.animation = '';
}
function navIsaretle(ad) { $$('.yan-oge').forEach((a) => a.classList.toggle('aktif', a.dataset.nav === ad)); }
async function yonlendir() {
  let h = location.hash.replace(/^#/, '');
  const eski = h.match(/^\/(v|video)\/([a-z0-9_]+)/);
  if (eski) { location.replace(`#/film/${eski[2]}`); return; }
  if (!h || h === '/') h = '/filmler';
  const [yol, sorgu] = h.split('?');
  const p = yol.split('/').filter(Boolean).map(decodeURIComponent);
  sesDur();
  $('#app').classList.remove('yan-acik');
  if (ayrilinca) { const f = ayrilinca; ayrilinca = null; f(); }
  $('#app').classList.toggle('odak', p[0] === 'film' && !KENAR_ACIK);
  try {
    if (['filmler', 'bekleyen', 'arsiv'].includes(p[0])) {
      navIsaretle(p[0]); gorunumGoster('v-filmler'); await filmlerSayfasi(p[0]);
    } else if (p[0] === 'film' && p[1]) {
      navIsaretle(''); await filmAc(p[1], p[2]);
    } else {
      const ad = SAYFA[p[0]] ? p[0] : null;
      navIsaretle(p[0] === 'kutuphane' ? `kutuphane/${p[1] || 'gorsel'}` : p[0]);
      gorunumGoster('v-sayfa'); ortam(null);
      if (!ad) { $('#v-sayfa').innerHTML = '<div class="icerik"><div class="bos-durum"><h3>Sayfa bulunamadı</h3><a class="btn cam-btn" href="#/filmler">Filmlere dön</a></div></div>'; return; }
      await SAYFA[ad](p.slice(1), new URLSearchParams(sorgu || ''));
    }
  } catch (e) {
    console.error(e);
    gorunumGoster('v-sayfa');
    $('#v-sayfa').innerHTML = `<div class="icerik" style="padding-top:24px"><div class="hata-kutu"><b>Bir sorun çıktı:</b> ${esc(e.message)}</div></div>`;
  }
}
const ustCubuk = (baslik, alt, sag = '') => `<div class="ust-cubuk"><button class="ikon-btn menu-btn" data-menu aria-label="Menüyü aç">${ik('menu')}</button><div><h1 class="buyuk-baslik">${baslik}</h1>${alt ? `<p class="ust-alt">${alt}</p>` : ''}</div><div class="bosluk"></div>${sag}</div>`;

// ---------------------------------------------------------------- ortak olaylar
document.addEventListener('click', (e) => {
  const t = e.target;
  const c = (s) => t.closest(s);
  let b;
  if (c('[data-kapat]') || t === $('#perde')) { levhaKapat(); return; }
  if (t.closest('#buyut')) { $('#buyut').hidden = true; return; }
  if ((b = c('[data-menu]'))) { $('#app').classList.toggle('yan-acik'); return; }
  if ((b = c('[data-yeni]'))) { e.preventDefault(); yeniLevha(); return; }
  if ((b = c('[data-buyut]'))) { e.preventDefault(); buyut(b.dataset.buyut); return; }
  if ((b = c('[data-kopyala]'))) { kopyala(b.dataset.kopyala); return; }
  if ((b = c('[data-cal]'))) { sesCal(b.dataset.cal, b.dataset.src); return; }
  if (!c('.menu-kap')) $$('.menu').forEach((m) => { m.hidden = true; });
});
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if (!$('#buyut').hidden) { $('#buyut').hidden = true; return; }
  if (!$('#perde').hidden) { levhaKapat(); return; }
  $$('.menu').forEach((m) => { m.hidden = true; });
  $('#app').classList.remove('yan-acik');
});
window.addEventListener('hashchange', yonlendir);

async function baslat() {
  simgele();
  try {
    const G = await genelYukle(true);
    // panel kapanıp açıldıysa süren işleri Etkinlik'e geri getir
    for (const j of (G.isler || []).filter((x) => x.durum === 'çalışıyor')) isIzle(j, null, {offset: Math.max(0, (j.toplam || 0) - 6)});
  } catch (e) { bildir(`Panel verisi alınamadı: ${e.message}`, 6000); }
  yonlendir();
}
