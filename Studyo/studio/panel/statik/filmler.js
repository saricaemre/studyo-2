// Stüdyo paneli · Filmler: vitrin, sıradaki onaylar, galeri, hızlı önizleme, yeni film levhası

const ADIMLAR = [
  {k: 'plan', ad: 'Plan', kapi: 1, insan: true, ne: 'Brief, gerçekler ve görünüş: filmin ne söylediği ve neyin uydurulamayacağı.'},
  {k: 'senaryo', ad: 'Senaryo', kapi: 2, insan: true, ne: 'Her vuruş, neden var olduğuyla birlikte. Oynatırken metin kelime kelime ilerler.'},
  {k: 'kareler', ad: 'Kareler', kapi: 3, ne: 'Ses ve her vuruştan bir temsilî kare: görünüşün tuttuğunu burada görürsün.'},
  {k: 'kurgu', ad: 'Kurgu', kapi: 4, ne: 'Kaba kurgu, kontak tabakası, ölçüm ve kör eleştiri. Ölçüm zanaatı denetler, etkiyi değil.'},
  {k: 'rotus', ad: 'Rötuş', kapi: 5, ne: 'Filmi hiç görmemiş eleştirmenin ve ölçümün bulduğu en büyük üç kusur.'},
  {k: 'teslim', ad: 'Teslim', kapi: 6, insan: true, ne: 'Final video, poster ve yayın paketi. Yüklemeyi sen yaparsın.'},
];

function yolSiniflari(x) {
  if (!x.kapilar) return ADIMLAR.map((a, i) => (CALISAN_DURUM.includes(x.durum) && i === 0 ? 'claude' : ''));
  const calisan = CALISAN_DURUM.includes(x.durum);
  return x.kapilar.map((k) => (k.durum === 'tamam' ? 'tamam' : k.durum === 'sirada' ? (calisan ? 'claude' : [1, 2, 6].includes(k.n) ? 'sende' : 'acik') : ''));
}
const yolMini = (x) => `<div class="yol-mini" aria-label="Filmin yolu">${ADIMLAR.map((a, i) => `<div class="p ${yolSiniflari(x)[i]}"><i></i>${a.ad}</div>`).join('')}</div>`;
const yolNokta = (x) => (x.arsiv ? '' : `<span class="yol-nokta" aria-hidden="true">${yolSiniflari(x).map((d) => `<i class="${d}"></i>`).join('')}</span>`);
const durumNokta = (x) => `<span class="nokta ${BEKLEYEN_DURUM.includes(x.durum) ? 'turuncu' : CALISAN_DURUM.includes(x.durum) ? 'claude' : x.durum === 'hazir' ? 'yesil' : ''}"></span>`;
const filmOran = (x) => fmtOran((x.formatlar || [])[0]);

// ---------------------------------------------------------------- filmler sayfası
async function filmlerSayfasi(filtre) {
  const G = await genelYukle(true);
  const L = filmListesi(G);
  const liste = L.filter((x) => (filtre === 'arsiv' ? x.arsiv : filtre === 'bekleyen' ? BEKLEYEN_DURUM.includes(x.durum) : !x.arsiv));
  const bekleyen = L.filter((x) => BEKLEYEN_DURUM.includes(x.durum));
  const vitrinFilm = filtre !== 'arsiv' ? bekleyen[0] : null;
  const baslik = {filmler: 'Filmler', bekleyen: 'Seni bekleyenler', arsiv: 'Arşiv'}[filtre];
  const alt = filtre === 'arsiv' ? 'Biten denemeler. Bekleyen işleri yok.'
    : `${L.filter((x) => !x.arsiv).length} film${bekleyen.length ? ` · ${bekleyen.length} tanesi senin kararını bekliyor` : ''}`;
  const sira = filtre !== 'arsiv' ? bekleyen.filter((x) => x !== vitrinFilm) : [];
  $('#v-filmler').innerHTML = `
    ${ustCubuk(baslik, alt, `<button class="besteci cam" data-yeni>${ik('claude')}<span class="yer">Yeni bir film anlat… ne, kime, nerede yayınlanacak?</span><span class="gonder-yuvarlak">${ik('yukari')}</span></button>`)}
    <div class="icerik">
      ${!G.claudeVar ? `<div class="uyari-kutu">${ik('unlem')}<span><b>Claude Code bu bilgisayarda bulunamadı.</b> Panel Claude'a iş gönderemez; filmleri izleyebilir, onaylayabilir ve komutları çalıştırabilirsin.</span></div>` : ''}
      ${vitrinFilm ? vitrinHtml(vitrinFilm) : ''}
      ${sira.length ? `<section aria-labelledby="sira-bas"><div class="bolum-bas"><h2 id="sira-bas">Sırada senin kararın</h2><span>${sira.length} film</span></div>
        <div class="sira">${sira.map(siraKart).join('')}</div></section>` : ''}
      <section aria-labelledby="galeri-bas"><div class="bolum-bas"><h2 id="galeri-bas">${filtre === 'arsiv' ? 'Arşivdeki filmler' : filtre === 'bekleyen' ? 'Bekleyenlerin hepsi' : 'Bütün filmler'}</h2></div>
        ${liste.length ? `<div class="galeri">${liste.map(filmKart).join('')}</div>` : `<div class="bos-durum cam"><h3>${filtre === 'bekleyen' ? 'Seni bekleyen bir şey yok' : 'Burada film yok'}</h3><p>${filtre === 'bekleyen' ? 'Claude bir plan ya da video hazırladığında burada görünür.' : 'Yeni bir film anlatarak başla.'}</p><button class="btn ana-btn" data-yeni>${ik('arti')}Yeni film</button></div>`}
      </section>
    </div>`;
  ortam(vitrinFilm?.poster ? 'img' : null, vitrinFilm?.poster ? kucukUrl(vitrinFilm.poster, 160) : null);
  if (vitrinFilm) vitrinDoldur(vitrinFilm);
  raporHatirlat(L);
}
// Yayın sonrası rapor hatırlatması: yayından 2 gün sonra, rapor yoksa bir kez (bu tarayıcıda gösterildi diye işaretlenir; ısrar etmez)
function raporHatirlat(L) {
  const x = L.find((f) => f.raporZamani && !f.arsiv && !(() => { try { return localStorage.getItem(`rapor-hatirlatma:${f.id}`); } catch { return '1'; } })());
  if (!x) return;
  try { localStorage.setItem(`rapor-hatirlatma:${x.id}`, '1'); } catch { /* yerel kayıt yoksa hatırlatma yine bir kez görünür */ }
  bildir(`“${x.baslik}” yayınlanalı en az iki gün oldu: izlenme raporunu filmin Teslim adımından ekleyebilirsin.`, 7000);
}

function vitrinEylem(x) {
  if (x.durum === 'video_onay') return `<button class="btn ana-btn buyuk" data-hizli="${x.id}">${ik('oynat')}İzle ve onayla</button><a class="btn cam-btn buyuk" href="#/film/${x.id}">Çalışma alanını aç</a>`;
  if (x.durum === 'plan_onay') return `<a class="btn ana-btn buyuk" href="#/film/${x.id}/plan">Planı oku ve onayla</a><button class="btn cam-btn buyuk" data-hizli="${x.id}">Hızlı bak</button>`;
  return `<button class="btn ana-btn buyuk" data-hizli="${x.id}">Devam ettir</button><a class="btn cam-btn buyuk" href="#/film/${x.id}">Çalışma alanını aç</a>`;
}
function vitrinHtml(x) {
  const yatay = filmOran(x) > 1;
  return `<section class="vitrin cam" aria-label="Seni bekleyen film">
    <div class="vitrin-metin">
      <div class="ust-not"><span class="nokta turuncu"></span>${esc(x.durumBaslik)}</div>
      <h2 class="vitrin-baslik">${esc(x.baslik)}</h2>
      <p class="vitrin-tek" id="vitrin-tek"></p>
      <div class="karar-satir">${ik('claude')}<div class="vitrin-durum" id="vitrin-durum">${esc(x.durumAciklama || '')}</div></div>
      <div class="dugmeler">${vitrinEylem(x)}${iptalDugme(x, 'buyuk')}</div>
      ${x.kapilar ? yolMini(x) : ''}
    </div>
    <button class="vitrin-poster ${yatay ? 'yatay' : ''}" data-hizli="${x.id}" aria-label="${esc(x.baslik)} önizlemesi">${x.poster ? `<img src="${kucukUrl(x.poster, 720)}" alt="">` : ''}<span class="oynat-rozet">${ik('oynat')}</span></button>
  </section>`;
}
async function vitrinDoldur(x) {
  try {
    const d = await api.get(`/api/basit/${x.id}`);
    if (d.tekCumle) $('#vitrin-tek') && ($('#vitrin-tek').textContent = d.tekCumle);
    const ilk = String(d.durumMd || '').split(/\n\s*\n|\n(?=\*\*)/).filter((s) => s.trim()).slice(0, 2).join('\n');
    if (ilk && $('#vitrin-durum')) $('#vitrin-durum').innerHTML = satirIci(ilk.replace(/\n/g, ' '));
  } catch (e) { /* vitrin özeti olmadan da çalışır */ }
}
function siraKart(x) {
  const eylem = {video_onay: 'İzle ve onayla', plan_onay: 'Planı oku', yarim: 'Devam ettir'}[x.durum] || 'Aç';
  return `<article class="sira-kart cam">
    <button class="sira-gorsel" data-hizli="${x.id}" aria-label="${esc(x.baslik)} önizlemesi">${x.poster ? `<img src="${kucukUrl(x.poster, 360)}" alt="" style="aspect-ratio:${filmOran(x) > 1 ? '16/9' : '9/16'}">` : ''}</button>
    <div class="sira-govde"><h3>${esc(x.baslik)}</h3><p class="durum-satir">${durumNokta(x)}${esc(x.durumBaslik)}</p>
      <div class="sira-alt">${yolNokta(x)}<span class="dugmeler">${iptalDugme(x, 'kucuk')}${x.durum === 'plan_onay' ? `<a class="btn kucuk cam-btn" href="#/film/${x.id}/plan">${eylem}</a>` : `<button class="btn kucuk cam-btn" data-hizli="${x.id}">${eylem}</button>`}</span></div></div>
  </article>`;
}
/** İptal: klasörü olan film arşive kalkar (geri alınabilir), başlamamış istek silinir. */
const iptalDugme = (x, boy) => `<button class="btn ${boy} sade-btn" type="button" data-iptal="${x.id}" data-klasor="${x.klasor ? 1 : ''}">İptal et</button>`;
async function iptalEt(bt) {
  const id = bt.dataset.iptal;
  const klasor = !!bt.dataset.klasor;
  const not = await onaySor(bt, {soru: klasor ? 'Film listeden kalkar ve Arşiv\'e taşınır. Dosyaları silinmez; Arşiv\'den geri alabilirsin.' : 'Bu istek ve ekli dosyaları silinsin mi? Geri alınamaz.', evet: klasor ? 'İptal et' : 'Sil', tehlike: true});
  if (not === null) return;
  try {
    await api.post(klasor ? `/api/basit/${id}/arsiv` : `/api/basit/${id}/sil`);
    bildir(klasor ? 'Film arşive taşındı.' : 'İstek silindi.');
    genelTazele();
    filmlerSayfasi(mevcutFiltre());
  } catch (er) { bildir(er.message, 6000); }
}
function filmKart(x) {
  const oran = filmOran(x);
  const gorsel = x.poster ? `<img src="${kucukUrl(x.poster, oran > 1 ? 720 : 400)}" alt="" loading="lazy">`
    : `<span class="bekleyen-gorsel" style="position:absolute;inset:0;display:grid"><span>${CALISAN_DURUM.includes(x.durum) ? `<span class="parilti" style="font-weight:600;font-size:14px">${esc(x.durumBaslik)}</span>` : `<span style="font-weight:600;font-size:14px;color:var(--yazi-2)">${x.klasor ? 'Henüz görüntü yok' : 'İstek'}</span>`}</span></span>`;
  return `<button class="film-kart" style="--oran:${oran.toFixed(4)}" data-hizli="${x.id}">
    <span class="film-gorsel">${gorsel}${x.formatlar ? `<span class="format-rozet">${x.formatlar.map(fmtEtiket).join(' · ')}</span>` : ''}</span>
    <span class="film-bilgi"><span class="film-ad">${esc(x.baslik)}</span><span class="film-alt">${durumNokta(x)}<span>${esc(x.durumBaslik)}</span></span></span>
  </button>`;
}

// ---------------------------------------------------------------- hızlı önizleme
let hizliZ = null;
let hizliFmt = null;
async function hizliLevha(id, {yenile = false} = {}) {
  clearTimeout(hizliZ);
  const G = await genelYukle();
  const x = filmListesi(G).find((f) => f.id === id) || {id};
  const d = await api.get(`/api/basit/${id}`);
  const vids = d.videolar || {};
  const fmtler = Object.keys(vids);
  if (!fmtler.includes(hizliFmt)) hizliFmt = fmtler[0];
  const v = vids[hizliFmt];
  const oran = fmtOran(hizliFmt || (x.formatlar || [])[0]);
  const calisiyor = d.claude && d.claude.durum === 'çalışıyor';
  const medya = v ? `<video src="${dosyaUrl(v.dosya)}" ${v.poster ? `poster="${kucukUrl(v.poster, 900)}"` : ''} controls ${yenile ? '' : 'autoplay'} playsinline></video>`
    : x.poster ? `<img src="${kucukUrl(x.poster, 900)}" alt="" style="width:100%;height:100%;object-fit:cover">`
      : `<div class="zaman-bos" style="color:#aaa">${CALISAN_DURUM.includes(d.durum) ? '<span class="parilti" style="font-weight:600">Claude çalışıyor</span>' : 'Henüz görüntü yok'}</div>`;
  const y = d.yayin;
  const govde = `
    <div class="hizli">
      <div><div class="hizli-video ${oran < 1 ? 'dikey' : 'yatay'}" style="aspect-ratio:${oran}">${medya}</div>
        ${fmtler.length > 1 ? `<div class="format-sec" style="margin-top:12px">${fmtler.map((f) => `<button type="button" class="${f === hizliFmt ? 'aktif' : ''}" data-hizli-fmt="${f}">${ik(FORMAT_IK[f] || 'kare')}${fmtEtiket(f)}</button>`).join('')}</div>` : ''}</div>
      <div class="hizli-bilgi">
        <div class="levha-bas" style="margin:0"><div><div class="durum-satir">${durumNokta(d)}${esc(d.durumBaslik)}</div><h2 id="levha-baslik" style="margin-top:8px">${esc(d.baslik)}</h2></div>${kapatDugme}</div>
        ${d.tekCumle ? `<p class="vitrin-tek" style="font-size:15px">${esc(d.tekCumle)}</p>` : ''}
        ${d.profil ? `<div class="cipler"><span class="cip">${esc(d.profil)}</span>${(d.formatlar || []).map((f) => `<span class="cip">${fmtEtiket(f)}</span>`).join('')}${d.sure ? `<span class="cip">${sn(d.sure)} sn</span>` : ''}${d.stil ? `<span class="cip">${esc(d.stil)}</span>` : ''}</div>` : ''}
        ${x.kapilar ? yolMini(x) : ''}
        <p class="ince">${esc(d.durumAciklama || '')}</p>
        ${calisiyor ? claudeKartHtml(d.claude) : ''}
        ${d.durumMd && !calisiyor ? `<div class="durum-md">${md(d.durumMd)}</div>` : ''}
        ${!calisiyor && ['yarim', 'hata'].includes(d.durum) && d.claudeSon ? `<details class="aac"><summary>${ik('sag')}Claude'un son mesajı</summary><div class="durum-md">${md(d.claudeSon)}</div></details>` : ''}
        ${y && ['video_onay', 'hazir'].includes(d.durum) ? `<div class="grup">
          ${y.baslik ? `<div class="kopya-satir"><div><b>Başlık</b>${esc(y.baslik)}</div><button class="ikon-btn" type="button" data-kopyala="${esc(y.baslik)}" aria-label="Başlığı kopyala">${ik('kopya')}</button></div>` : ''}
          ${y.aciklama ? `<div class="kopya-satir"><div><b>Açıklama</b>${esc(y.aciklama.slice(0, 240))}${y.aciklama.length > 240 ? '…' : ''}</div><button class="ikon-btn" type="button" data-kopyala="${esc(y.aciklama)}" aria-label="Açıklamayı kopyala">${ik('kopya')}</button></div>` : ''}</div>` : ''}
        <div class="dugmeler" id="hizli-eylem">${hizliEylemler(d, x)}</div>
        <div id="hizli-degisiklik"></div>
        ${v ? `<p class="ince"><a href="${dosyaUrl(v.dosya)}" download="${esc(v.ad)}">${esc(v.ad)} indir</a>${v.poster ? ` · <a href="${dosyaUrl(v.poster)}" download>poster</a>` : ''}</p>` : ''}
      </div>
    </div>`;
  if (yenile && !$('#perde').hidden) { $('#levha').innerHTML = govde; simgele($('#levha')); }
  else levhaAc(govde, '', () => { clearTimeout(hizliZ); });
  hizliBagla(d);
  if (calisiyor) hizliZ = setTimeout(() => { if (!$('#perde').hidden) hizliLevha(id, {yenile: true}).catch(() => {}); }, 3500);
}
function hizliEylemler(d, x) {
  const b = [];
  const ac = x.klasor || d.profil ? `<a class="btn cam-btn buyuk" href="#/film/${d.id}" data-kapat>Çalışma alanını aç</a>` : '';
  const gorunusYok = d.gorunus && d.gorunus.mod === 'video' && !d.gorunus.secim;
  if (d.durum === 'yol_secim') b.push(`<a class="btn ana-btn buyuk" href="#/film/${d.id}/plan" data-kapat>Üç yola bak, birini seç</a>`);
  if (d.durum === 'plan_onay') b.push(gorunusYok ? `<a class="btn ana-btn buyuk" href="#/film/${d.id}/plan" data-kapat>Önce görünüşü seç</a>` : `<button class="btn ana-btn buyuk" type="button" data-b-onay="plan">Planı onayla, üretime geç</button>`);
  if (d.durum === 'video_onay') b.push('<button class="btn ana-btn buyuk" type="button" data-b-onay="video">Videoyu onayla</button>');
  if (d.durum === 'baslamadi') b.push('<button class="btn ana-btn buyuk" type="button" data-b-eylem="basla">Başlat</button><button class="btn cam-btn buyuk" type="button" data-b-eylem="sil">İsteği sil</button>');
  if (['yarim', 'hata'].includes(d.durum)) b.push('<button class="btn ana-btn buyuk" type="button" data-b-eylem="devam">Devam ettir</button>');
  if (d.durum === 'taslak') b.push(`<a class="btn ana-btn buyuk" href="#/film/${d.id}" data-kapat>İsteğini yaz</a>`);
  if (ac) b.push(ac);
  if (x.arsiv) b.push('<button class="btn cam-btn buyuk" type="button" data-b-arsiv>Arşivden çıkar</button>');
  if (d.profil && !CALISAN_DURUM.includes(d.durum) && d.durum !== 'baslamadi') b.push('<button class="btn cam-btn buyuk" type="button" data-b-degis>Değişiklik iste</button>');
  return b.join('');
}
function hizliBagla(d) {
  const L = $('#levha');
  $$('[data-hizli-fmt]', L).forEach((bt) => bt.addEventListener('click', () => { hizliFmt = bt.dataset.hizliFmt; hizliLevha(d.id, {yenile: true}); }));
  const sonra = async (yol, body, mesaj) => {
    try { await api.post(yol, body); if (mesaj) bildir(mesaj); genelTazele(); await hizliLevha(d.id, {yenile: true}); if (!location.hash.startsWith('#/film/')) filmlerSayfasi(mevcutFiltre()); } catch (e) { bildir(e.message, 6000); }
  };
  $$('[data-b-onay]', L).forEach((bt) => bt.addEventListener('click', async () => {
    const plan = bt.dataset.bOnay === 'plan';
    const not = await onaySor(bt, {soru: plan ? 'Kapı 1 ve 2 senin onayınla kapanır, Claude filmi üretmeye başlar.' : 'Kapı 6 kapanır; film teslim edilmiş sayılır. Yüklemeyi sen yaparsın.', evet: plan ? 'Onayla ve üret' : 'Onayla'});
    if (not === null) return;
    sonra(`/api/basit/${d.id}/onay`, {asama: bt.dataset.bOnay}, plan ? 'Plan onaylandı; Claude üretime başladı.' : 'Video onaylandı.');
  }));
  $$('[data-b-eylem]', L).forEach((bt) => bt.addEventListener('click', async () => {
    const e = bt.dataset.bEylem;
    if (e === 'sil') {
      const not = await onaySor(bt, {soru: 'Bu istek ve ekli dosyaları silinsin mi? Geri alınamaz.', evet: 'Sil', tehlike: true});
      if (not === null) return;
      try { await api.post(`/api/basit/${d.id}/sil`); bildir('İstek silindi.'); levhaKapat(); genelTazele(); filmlerSayfasi(mevcutFiltre()); } catch (er) { bildir(er.message, 6000); }
      return;
    }
    sonra(`/api/basit/${d.id}/${e}`, {}, e === 'basla' ? 'Claude başladı.' : 'Claude kaldığı yerden devam ediyor.');
  }));
  $('[data-b-arsiv]', L)?.addEventListener('click', async () => {
    try { await api.post(`/api/basit/${d.id}/arsiv`, {geri: true}); bildir('Film arşivden çıktı.'); levhaKapat(); genelTazele(); filmlerSayfasi(mevcutFiltre()); } catch (er) { bildir(er.message, 6000); }
  });
  $('[data-b-degis]', L)?.addEventListener('click', (ev) => {
    ev.currentTarget.hidden = true;
    $('#hizli-degisiklik').innerHTML = `<div class="onay-not"><textarea class="girdi" id="degis-metin" rows="3" placeholder="Ne değişsin? Ör: daha kısa olsun, girişte soru sorsun, renkler daha koyu olsun."></textarea><div class="dugmeler"><button class="btn ana-btn" type="button" id="degis-gonder">${ik('yukari')}Claude'a gönder</button></div></div>`;
    $('#degis-metin').focus();
    $('#degis-gonder').addEventListener('click', () => {
      const m = $('#degis-metin').value.trim();
      if (!m) { bildir('Ne değişsin? Kısaca yaz.'); return; }
      sonra(`/api/basit/${d.id}/degisiklik`, {metin: m}, "Claude'a gönderildi.");
    });
  });
  $$('[data-durdur]', L).forEach((bt) => bt.addEventListener('click', async () => {
    const not = await onaySor(bt, {soru: 'Claude durdurulsun mu? Yaptıkları kalır; sonra “Devam ettir” diyebilirsin.', evet: 'Durdur', tehlike: true});
    if (not === null) return;
    sonra(`/api/is/${bt.dataset.durdur}/durdur`, {}, 'Claude durduruldu.');
  }));
}
function claudeKartHtml(j) {
  const s = Math.round((j.sure || 0) / 60);
  return `<div class="claude-kart"><div class="claude-kart-ust">${ik('claude')}<b class="parilti">${esc(j.ad || 'Claude çalışıyor')}</b><span>${s} dk</span></div>
    <div class="gunluk" data-gunluk>${esc((j.satirlar || []).join('\n') || 'Claude başlıyor…')}</div>
    <div class="dugmeler"><button class="btn cam-btn kucuk" type="button" data-durdur="${j.id}">Durdur</button><span class="ince">Sayfayı kapatabilirsin; iş arka planda sürer.</span></div></div>`;
}
const mevcutFiltre = () => (location.hash.match(/^#\/(filmler|bekleyen|arsiv)/) || [0, 'filmler'])[1];

document.addEventListener('click', (e) => {
  const iptal = e.target.closest('[data-iptal]');
  if (iptal) { e.preventDefault(); iptalEt(iptal); return; }
  const b = e.target.closest('[data-hizli]');
  if (b) { e.preventDefault(); hizliLevha(b.dataset.hizli).catch((er) => bildir(er.message, 6000)); }
});
document.addEventListener('is-bitti', () => { if (location.hash.match(/^#\/(filmler|bekleyen|arsiv)|^$|^#\/?$/)) filmlerSayfasi(mevcutFiltre()).catch(() => {}); });

// ---------------------------------------------------------------- yeni film levhası
// Katalog esin kaynağıdır: kart yoksa Claude filme özel icat eder; kartlar "esin" (karıştır, aş) ya da tek kartla "aynen" (tarif).
const RAF = {
  gorsel: {et: 'Görüntü stili', icat: 'Her yola kendi görünüşü', ornek: "80'lerin VHS reklamı gibi, titrek renk, büyük harfli yazı"},
  animasyon: {et: 'Hareket', icat: 'Filme özel hareket dili', ornek: 'Tek plan: kamera hiç kesmeden geri çekilir, her şey tek nefeste olur'},
  ses: {et: 'Ses', icat: 'Filme özel müzik ve ses', ornek: 'Doruğa kadar müzik yok; yalnız tek bir davul ve nefes sesi'},
};
const RAF_EN_COK = 3;
const TARIF_EN_COK = 400;
const ESIN_NOT = {
  gorsel: 'Claude bu kartı başlangıç olarak alır: karıştırır, değiştirir, aşar. Üç yolun görünüşünü filme göre kendisi yazar.',
  animasyon: 'Claude bu tarifi başlangıç olarak alır: karıştırır, değiştirir, aşar. Hareket dilini filme göre kendisi kurar.',
  ses: 'Claude bu kartı başlangıç olarak alır: karıştırır, değiştirir, aşar. Müziği filme göre kendisi tarif eder.',
};
const AYNEN_NOT = {
  gorsel: 'Bu üç varyasyon üç yolun görünüşü olur. Claude filme göre inceltebilir, stilin dışına çıkmaz; seçim yine senin.',
  animasyon: 'Claude bu tarife uyar: kurallar, kamera, geçiş ve tempo.',
  ses: 'Müzik, efektler, anlatıcı ayarı ve miks bu karttan gelir.',
};
const CESARET = {saglam: 'Sağlam', cesur: 'Cesur', sinirsiz: 'Sınırsız'};
const CESARET_NOT = {
  saglam: 'Denenmiş, net bir dil; yine de bir olağanüstü an.',
  cesur: 'En az bir beklenmedik fikir ve bir olağanüstü an.',
  sinirsiz: "İlk saniyede alışkanlığı kıran açılış, en az bir 'imkânsız ama gerçek görünen' an, stüdyonun daha önce yapmadığı bir teknik.",
};
const rafYeni = () => ({kartlar: [], mod: 'esin', tarif: '', acik: false, goster: ''});
const SES_KAPAK = {
  'belgesel-sakin': ['#41607f', '#fff'], 'enerjik-elektronik': ['#6b3fd4', '#fff'], 'gerilim-drone': ['#262c36', '#fff'], 'haber-bulteni': ['#b3261e', '#fff'], 'lofi-sicak': ['#9a5f36', '#fff'],
  'minimal-arayuz': ['#24766f', '#fff'], 'neseli-sicak': ['#f2b705', '#2a1d00'], 'sessizlik-tek-vurus': ['#141416', '#fff'], 'sinematik-yukselis': ['#8a4b14', '#fff'],
};
const SES_YEDEK = ['#3d5a80', '#6d597a', '#355070', '#7f5539', '#2d6a4f', '#5f0f40'];
const EFEKT = {baloncuk: 'baloncuk', can: 'çan', drone: 'drone', gum: 'güm', konfeti: 'konfeti', low_drum: 'derin davul', metal_die: 'metal darbe', paper_rustle: 'kâğıt hışırtısı', paper_slide: 'kâğıt kayması', parilti: 'parıltı', quill: 'tüy kalem', room: 'oda tonu', shimmer: 'ışıltı', stamp: 'mühür', tebesir: 'tebeşir', tik: 'tık', whoosh: 'vınlama', wood_tok: 'tahta tok', yay: 'yay'};
const MUZIK_AD = {kod: 'koddan müzik', ace: 'ACE-Step müziği', yok: 'müziksiz'};
let YS = null;   // yeni film levhasındaki seçimler
const katListe = (tur) => (GENEL?.katalog?.[tur] || []).filter((e) => e.durum !== 'taslak');
const katBul = (tur, ad) => katListe(tur).find((e) => e.ad === ad);
const cubuklar = (ad) => { let h = 7; for (const c of ad) h = (h * 31 + c.charCodeAt(0)) >>> 0; return Array.from({length: 12}, () => { h = (h * 1103515245 + 12345) >>> 0; return 22 + ((h >>> 8) % 78); }); };
const sesKapak = (ad) => SES_KAPAK[ad] || [SES_YEDEK[cubuklar(ad)[0] % SES_YEDEK.length], '#fff'];
const sesOrnek = (e, kay) => (e.onizleme && typeof e.onizleme === 'object' ? e.onizleme[kay] || e.onizleme.ace || e.onizleme.kod : null);

function rafKart(tur, e) {
  const R = YS[tur];
  const secili = e ? R.kartlar.includes(e.ad) : !R.kartlar.length;
  if (!e) return `<div class="raf-kart icat-kart"><button type="button" class="raf-sec" role="checkbox" aria-checked="${secili}" data-raf-sec="${tur}" data-ad=""><span class="raf-gorsel">${ik('claude')}</span><span class="raf-ad">Claude icat etsin<small>${RAF[tur].icat}</small></span></button></div>`;
  let g = '';
  if (tur === 'gorsel') { const o = (e.varyasyonlar || [])[0]?.onizleme || e.onizleme; g = o ? `<img src="${kucukUrl(o, 300)}" alt="" loading="lazy">` : ''; }
  else if (tur === 'animasyon') g = e.onizleme ? `<video src="${dosyaUrl(e.onizleme)}" ${e.poster ? `poster="${kucukUrl(e.poster, 300)}"` : ''} muted loop autoplay playsinline preload="metadata"></video>` : '';
  else { const [bg, fg] = sesKapak(e.ad); g = `<span class="ses-kapak" style="--kapak:${bg};--kapak-yazi:${fg}"><span class="bars">${cubuklar(e.ad).map((h) => `<i style="height:${h}%"></i>`).join('')}</span><span class="bpm">${e.detay?.bpm ? `${e.detay.bpm} BPM` : ''}</span></span>`; }
  const ornek = tur === 'ses' ? sesOrnek(e, 'ace') : null;
  const cal = ornek ? calDugme(`${e.ad}:${ornek.includes('-kod') ? 'kod' : 'ace'}`, dosyaUrl(ornek), `${e.baslik} örneğini dinle`, 'raf-cal') : '';
  return `<div class="raf-kart"><button type="button" class="raf-sec" role="checkbox" aria-checked="${secili}" data-raf-sec="${tur}" data-ad="${e.ad}"><span class="raf-gorsel">${g}</span><span class="raf-ad">${esc(e.baslik)}</span></button>${cal}</div>`;
}
const anlatKart = (tur) => `<div class="raf-kart anlat-kart"><button type="button" class="raf-sec" aria-expanded="${YS[tur].acik}" aria-controls="raf-anlat-${tur}" data-raf-anlat="${tur}"><span class="raf-gorsel">${ik('kalem')}</span><span class="raf-ad">Kendin anlat<small>Tarif ve referans</small></span></button></div>`;
function raf(tur) {
  return `<section class="raf" aria-labelledby="raf-${tur}">
    <div class="raf-bas"><h3 id="raf-${tur}">${RAF[tur].et}</h3><span class="raf-secim" id="raf-ad-${tur}"></span>
      <div class="mod-sec" role="radiogroup" aria-label="${RAF[tur].et}: kartları nasıl kullansın" id="raf-mod-${tur}">
        <label><input type="radio" name="mod-${tur}" value="esin" data-raf-mod="${tur}" checked><span>Esinlen</span></label><label><input type="radio" name="mod-${tur}" value="aynen" data-raf-mod="${tur}"><span>Aynen uygula</span></label></div>
      <button type="button" class="ikon-btn raf-ok" data-raf-kaydir="${tur}" data-yon="-1" aria-label="${RAF[tur].et}: geri kaydır">${ik('sol')}</button><button type="button" class="ikon-btn raf-ok" data-raf-kaydir="${tur}" data-yon="1" aria-label="${RAF[tur].et}: ileri kaydır">${ik('sag')}</button></div>
    <div class="raf-serit" id="raf-serit-${tur}" role="group" aria-labelledby="raf-${tur}">${rafKart(tur, null)}${katListe(tur).map((e) => rafKart(tur, e)).join('')}${anlatKart(tur)}</div>
    <p class="mod-not" id="raf-modnot-${tur}" aria-live="polite"></p>
    <div class="raf-anlat" id="raf-anlat-${tur}" hidden>
      <label class="alan-et" for="tarif-${tur}">${RAF[tur].et}: kendi tarifin <small><span id="tarif-say-${tur}">0</span>/${TARIF_EN_COK}</small></label>
      <textarea class="girdi tarif-alan" id="tarif-${tur}" data-raf-tarif="${tur}" maxlength="${TARIF_EN_COK}" rows="2" placeholder="Örnek: ${esc(RAF[tur].ornek)}"></textarea>
      <div class="ref-satir"><label class="btn cam-btn kucuk ref-ekle" for="ref-${tur}">${ik('atac')}Referans ekle<input type="file" id="ref-${tur}" data-raf-ref="${tur}" accept="image/*,video/*,audio/*" multiple></label>
        <span class="ince">Görsel, video ya da ses. Claude ölçer, dilini alır; kopyalamaz.</span></div>
      <div class="cipler ref-liste" id="ref-liste-${tur}"></div></div>
    <div id="raf-detay-${tur}"></div></section>`;
}
function rafDetay(tur, e, mod) {
  const D = e.detay || {};
  const not = `<p class="detay-not">${ik('claude')}<span>${esc(e.ozet)} ${mod === 'aynen' ? AYNEN_NOT[tur] : ESIN_NOT[tur]}</span></p>`;
  if (tur === 'gorsel') {
    const V = D.varyasyonlar || {};
    return `<div class="varyasyonlar">${(e.varyasyonlar || []).map((x) => { const v = V[x.harf] || {}; return `<figure class="varyasyon"><img src="${kucukUrl(x.onizleme, 400)}" alt="${esc(x.ad)} varyasyonu"><figcaption><b>${x.harf.toUpperCase()} · ${esc(x.ad)}</b>${v.fikir ? `<p>${esc(v.fikir)}</p>` : ''}${v.renk?.length ? `<span class="mini-renk">${v.renk.map((r) => `<i style="background:${esc(r)}" title="${esc(r)}"></i>`).join('')}</span>` : ''}${v.baslik ? `<small>${esc(v.baslik)}${v.govde ? ` · ${esc(v.govde)}` : ''}</small>` : ''}</figcaption></figure>`; }).join('')}</div>
      ${not}`;
  }
  if (tur === 'animasyon') {
    return `<div class="hareket-detay">${e.onizleme ? `<video src="${dosyaUrl(e.onizleme)}" ${e.poster ? `poster="${kucukUrl(e.poster, 400)}"` : ''} muted loop autoplay playsinline></video>` : '<span></span>'}
      <div class="tarif"><p class="ozet">${esc(e.ozet)}</p>${(D.kurallar || []).length ? `<ul>${D.kurallar.slice(0, 2).map((k) => `<li>${esc(k)}</li>`).join('')}</ul>` : ''}
        <p>${D.kamera ? `<b>Kamera:</b> ${esc(D.kamera)}` : ''}${D.gecis ? ` · <b>Geçiş:</b> ${esc(D.gecis)}` : ''}${D.tempo ? ` · <b>Olay aralığı:</b> ${sn(D.tempo[0])}–${sn(D.tempo[1])} sn` : ''}</p>
        <p class="detay-not">${ik('claude')}<span>${mod === 'aynen' ? AYNEN_NOT[tur] : ESIN_NOT[tur]}</span></p>
        <p class="motor-not">${ik('claude')}Önizleme yalnız hareketi gösterir${D.ornek_motor ? ` (${MOTOR_AD[D.ornek_motor] || D.ornek_motor} ile çizildi)` : ''}. Görünüşü görüntü stili, motoru Motor seçimin belirler; bu hareket her motorda uygulanır.</p>
        ${D.uc ? `<p class="motor-not">${ik('unlem')}3B sahne: Remotion'da ve HyperFrames'te Three.js katmanıyla, Blender'da doğrudan çizilir.</p>` : ''}</div></div>`;
  }
  const k = D.kod || {};
  const an = D.anlatim || {};
  const m = D.miks || {};
  const eksi = (x) => String(x).replace('-', '−').replace('Hz', ' Hz');
  const o = e.onizleme || {};
  const aceYok = !GENEL.aceVar;
  return `<p class="detay-ozet">${esc(e.ozet)}</p>
    <div class="kaynaklar2" role="radiogroup" aria-label="Müzik kaynağı">
      <div class="kaynak-kart"><label for="mk-kod"><input type="radio" name="muzik-kaynagi" id="mk-kod" value="kod" ${YS.kaynak === 'kod' ? 'checked' : ''}><b>Koddan üretim</b><span>Anında hazır, geçici kalite</span><small>${k.bpm || D.bpm || ''} BPM${k.ton ? ` · ${esc(k.ton)}` : ''}</small></label>${o.kod ? calDugme(`${e.ad}:kod`, dosyaUrl(o.kod), 'Koddan üretilen örneği dinle') : ''}</div>
      <div class="kaynak-kart"><label for="mk-ace"><input type="radio" name="muzik-kaynagi" id="mk-ace" value="ace" ${YS.kaynak === 'ace' ? 'checked' : ''} ${aceYok ? 'disabled' : ''}><b>ACE-Step</b><span>${aceYok ? 'Bu Mac’te kurulu değil' : 'Bu Mac’te çalışan yapay zekâ · parça başına ~2 dk'}</span>${D.ace ? `<small>“${esc(D.ace)}”</small>` : ''}</label>${o.ace ? calDugme(`${e.ad}:ace`, dosyaUrl(o.ace), 'ACE-Step örneğini dinle') : ''}</div>
    </div>
    <div class="ses-bilgi">
      <div><b>Efektler</b><div class="cipler">${(D.efekt || []).map((x) => `<span class="cip">${esc(EFEKT[x] || x)}</span>`).join('') || '—'}</div></div>
      <div><b>Anlatıcı</b><span>${an.rate ? `hız ${eksi(an.rate)}` : 'varsayılan hız'}${an.pitch ? ` · perde ${eksi(an.pitch)}` : ''}</span></div>
      <div><b>Miks</b><span>${m.muzik_db !== undefined ? `müzik ${eksi(m.muzik_db)} dB` : ''}${m.duck_db ? ` · anlatımda ${eksi(m.duck_db)} dB` : ''}${m.sessizlik ? ` · ${esc(m.sessizlik)}` : ''}</span></div>
    </div>
    <p class="detay-not">${ik('claude')}<span>${mod === 'aynen' ? AYNEN_NOT[tur] : ESIN_NOT[tur]}</span></p>`;
}
function rafGuncelle(tur) {
  const R = YS[tur];
  $$(`[data-raf-sec="${tur}"]`).forEach((b) => b.setAttribute('aria-checked', String(b.dataset.ad ? R.kartlar.includes(b.dataset.ad) : !R.kartlar.length)));
  const secili = R.kartlar.map((a) => katBul(tur, a)).filter(Boolean);
  if (R.mod === 'aynen' && secili.length !== 1) R.mod = 'esin';
  const modK = $(`#raf-mod-${tur}`);   // kart yoksa iki düğme de pasif; "Aynen uygula" yalnız tek kartla
  $$('input', modK).forEach((r) => { r.checked = r.value === R.mod; r.disabled = !secili.length || (r.value === 'aynen' && secili.length > 1); });
  modK.classList.toggle('pasif', !secili.length);
  $(`#raf-modnot-${tur}`).textContent = secili.length > 1 ? 'Aynen uygulama tek kartla olur: birden çok kart Claude için esin kaynağıdır.' : '';
  $(`#raf-ad-${tur}`).innerHTML = secili.length ? `<b>${secili.map((e) => esc(e.baslik)).join(' + ')}</b> · ${R.mod === 'aynen' ? 'aynen' : 'esin'}` : 'Claude icat eder';
  if (!R.kartlar.includes(R.goster)) R.goster = R.kartlar[R.kartlar.length - 1] || '';
  const e = katBul(tur, R.goster);
  const sekmeler = secili.length > 1 ? `<div class="detay-sekmeler" role="tablist" aria-label="${RAF[tur].et}: seçili kartlar">${secili.map((x) => `<button type="button" role="tab" aria-selected="${x.ad === R.goster}" data-raf-goster="${tur}" data-ad="${x.ad}">${esc(x.baslik)}</button>`).join('')}</div>` : '';
  $(`#raf-detay-${tur}`).innerHTML = e ? `<div class="raf-detay">${sekmeler}${rafDetay(tur, e, R.mod)}</div>` : '';
  const ak = $(`[data-raf-anlat="${tur}"]`);
  ak.setAttribute('aria-expanded', String(R.acik));
  $(`#raf-anlat-${tur}`).hidden = !R.acik;
  anlatDurum(tur);
  secimOzet();
}
/** "Kendin anlat" kartı: tarif ya da referans varsa dolu görünür; altındaki referans listesi. */
function anlatDurum(tur) {
  const refler = YS.referanslar.map((r, i) => ({...r, i})).filter((r) => r.tur === tur);
  $(`[data-raf-anlat="${tur}"]`).closest('.raf-kart').classList.toggle('dolu', !!YS[tur].tarif.trim() || refler.length > 0);
  $(`#tarif-say-${tur}`).textContent = YS[tur].tarif.length;
  $(`#ref-liste-${tur}`).innerHTML = refler.map((r) => `<span class="cip ref-cip">${ik('atac')}<span class="ref-ad">${esc(r.dosya.name)}</span><button type="button" class="ref-sil" data-ref-sil="${r.i}" aria-label="${esc(r.dosya.name)} referansını kaldır">${ik('kapat')}</button></span>`).join('');
}
const MOTOR_NOT = {
  hyperframes: 'HTML, SVG ve GSAP: karakter ve çizgi film animasyonunda, kampanyada, video oynatmada güçlü. 3B katman da var.',
  remotion: 'React: yazıda, veride, haritada, arayüzde, SVG illüstrasyonda güçlü. 3B katman da var.',
  blender: 'Gerçek 3B: ışık, malzeme, kamera ve alan derinliği. Ürün, mimari, soyut, maket, çizgi film boyası; her tarz. Çizim süresi çizere bağlı (aşağıda).',
};
function motorNot(onEk = '') {
  const v = $('input[name=motor]:checked')?.value || '';
  const cg = $('#cizer-grup');
  if (cg) {  // Blender'ın çizeri yalnız Blender seçilince; başka motora geçince seçim bırakılır
    cg.hidden = v !== 'blender';
    if (cg.hidden) $('input[name=cizer][value=""]').checked = true;
    cizerNot();
  }
  const o = GENEL?.motorOnizleme?.[v];
  $('#motor-not').innerHTML = (onEk ? `<b>${esc(onEk)}</b> ` : '')
    + esc(MOTOR_NOT[v] || 'Motor bir araçtır, tarz değil: görünüşü görüntü stili, hareketi hareket tipi belirler. Claude filmin ihtiyacına göre seçer ve nedenini söyler.')
    + (o ? `<span class="motor-onizleme"><video src="${dosyaUrl(o.video)}" ${o.poster ? `poster="${kucukUrl(o.poster, 200)}"` : ''} muted loop autoplay playsinline preload="metadata" aria-label="${esc(MOTOR_AD[v])} örneği"></video><small>${v === 'blender' ? 'Örnek: Blender malzeme yelpazesi' : `Örnek: ${esc(MOTOR_AD[v])}`}</small></span>` : '');
}
function secimOzet() {
  const el = $('#secim-ozet');
  if (!el) return;
  const p = [];
  ['gorsel', 'animasyon', 'ses'].forEach((t) => {
    const R = YS[t];
    const adlar = R.kartlar.map((a) => katBul(t, a)?.baslik).filter(Boolean);
    if (adlar.length) p.push(`${adlar.join(' + ')} (${R.mod === 'aynen' ? 'aynen' : 'esin'})${t === 'ses' ? ` · ${MUZIK_AD[YS.kaynak]}` : ''}`);
    const tf = R.tarif.trim();
    if (tf) p.push(`Kendi tarifin: ${tf.length > 40 ? `${tf.slice(0, 40)}…` : tf}`);
  });
  if (!YS.ses.kartlar.length && YS.kaynak !== 'kod') p.push(MUZIK_AD[YS.kaynak].replace(/^./, (c) => c.toLocaleUpperCase('tr-TR')));
  if (YS.referanslar.length) p.push(`${YS.referanslar.length} referans`);
  p.push(`Cesaret: ${CESARET[YS.cesaret]}`);
  const an = $('input[name=anlatim]:checked')?.value;
  if (an) p.push({kayit: 'Kendi sesin', magnific: 'Magnific anlatıcı', yok: 'Anlatımsız'}[an]);
  if ($('input[name=altyazi]:checked')?.value === 'niyetli') p.push('Niyetli altyazı');
  const cz = $('input[name=motor]:checked')?.value === 'blender' && $('input[name=cizer]:checked')?.value;
  if (cz) p.push(`Blender · ${cz === 'eevee' ? 'EEVEE' : 'Cycles'}`);
  const fm = $$('input[name=format]:checked').map((c) => fmtEtiket(c.value));
  if (fm.length) p.unshift(fm.join(' + '));
  el.innerHTML = p.map((x) => `<span class="cip">${esc(x)}</span>`).join('');
}
function cesaretNot() {
  $('#cesaret-not').textContent = CESARET_NOT[YS.cesaret];
  secimOzet();
}
function sesNotlari() {
  const an = $('input[name=anlatim]:checked')?.value || '';
  const ornek = GENEL?.anlaticiOrnek;
  $('#anlatim-not').innerHTML = an === 'magnific'
    ? `Magnific'in doğal erkek sesi (Serkan Yıldırım, yapay zekâ). Her cümle bir kez üretilir, kredi sınırına sayılır (~85 karakter 18 kredi); yayın paketinde belirtilir.${ornek ? `<audio src="${dosyaUrl(ornek, true)}" controls preload="none" style="width:100%;height:32px;margin-top:6px" aria-label="Serkan Yıldırım örneği"></audio>` : ''}`
    : esc({'': "Edge'in ücretsiz yapay sesi. Metni okuyan konuşma sesidir; müzikle ilgisi yok.", kayit: 'Sen okursun, kelime zamanları otomatik çıkar. Kaydını aşağıdan ekle ya da sonra yükle.', yok: 'Anlatıcısız film: görüntü müziğe ve efektlere kesilir.'}[an]);
  $('#muzik-not').textContent = {kod: 'Anında hazır, geçici kalite. Bilgisayar müziği kod ile besteler.', ace: "Bu Mac'te çalışan yapay zekâ müziği: ilk açılış ~5 dk, parça başına ~2 dk. Yayın paketinde belirtilir.", yok: 'Müzik olmaz; anlatım ve efektler kalır.'}[YS.kaynak];
  $$('input[name="muzik-kaynagi"]').forEach((r) => { r.checked = r.value === YS.kaynak; });
  const s = $(`input[name=muzik][value="${YS.kaynak}"]`);
  if (s) s.checked = true;
  secimOzet();
}
// Blender'ın çizeri: aynı karenin Cycles ve EEVEE hâli (./st katalog cizer) + 30 sn'lik filmin teslim süresi (kil kampla ölçüldü)
const sureMetni = (dk) => (dk >= 90 ? `~${sn(Math.round(dk / 6) / 10)} saat` : `~${dk} dk`);
function cizerNot() {
  const el = $('#cizer-not');
  if (!el) return;
  const v = $('input[name=cizer]:checked')?.value || '';
  const O = GENEL?.cizerOnizleme || {};
  const sure = (c) => (O[c] ? `Teslim kare başına ~${sn(O[c].sn_kare)} sn, 30 saniyelik film ${sureMetni(O[c].film30_dk)}` : '');
  if (!el.querySelector('.cizer-onizleme') && (O.cycles || O.eevee)) {  // örnekler bir kez kurulur; seçim değişince yalnız işaret değişir
    el.innerHTML = `<span class="cizer-onizleme">${[['cycles', 1, 'Cycles'], ['eevee', 2, 'EEVEE']].filter(([c]) => O[c]).map(([c, i, ad]) => `<label class="cizer-ornek" for="seg-cizer-${i}" data-cizer="${c}"><img src="${kucukUrl(O[c].gorsel, 200)}" alt="${ad} ile çizilmiş örnek kare" loading="lazy"><small><b>${ad}</b> · ${sureMetni(O[c].film30_dk)}</small></label>`).join('')}</span><span class="cizer-metin"></span>`;
  }
  el.querySelectorAll('.cizer-ornek').forEach((x) => x.classList.toggle('secili', x.dataset.cizer === v));
  const m = el.querySelector('.cizer-metin') || el;
  m.textContent = {
    '': 'Claude filmin görünüşüne göre seçer: gerçek ışık gerekiyorsa Cycles, stilize ya da çizgi film dünyasıysa EEVEE. Örnekler aynı karedir.',
    cycles: `Gerçek ışık: içinden ışık geçen bez, cam, yumuşak dolaylı ışık. ${sure('cycles')}.`,
    eevee: `Hızlı: stilize, çizgi film, düz renk, kil, düşük poligon. ${sure('eevee')}. Kumaşın içinden dışarı düşen gölgeyi ve camın tam gerçekçi kırılmasını yapamaz.`,
  }[v];
  secimOzet();
}
const ALTYAZI_NOT = {
  '': 'Kelime kelime, tek yazı ağırlığı; filmin görünüşüne uyar.',
  niyetli: 'Yazı sesi gösterir: bağıran kelime kalın ve büyük, fısıltı ince, tiz ses dar; her konuşmacı kendi renginde. En az 64 px, güçlü kontrast. Anlatımlı film ister.',
};
function altyaziNot() {
  const el = $('#altyazi-not');
  if (!el) return;
  const yok = $('input[name=anlatim]:checked')?.value === 'yok';
  const niy = $('input[name=altyazi][value=niyetli]');
  niy.disabled = yok;
  if (yok && niy.checked) $('input[name=altyazi][value=""]').checked = true;
  const v = $('input[name=altyazi]:checked')?.value || '';
  const O = GENEL?.altyaziOnizleme || {};
  if (!el.querySelector('.altyazi-onizleme') && (O.klasik || O.niyetli)) {  // örnekler bir kez kurulur; seçim değişince yalnız işaret değişir
    el.innerHTML = `<span class="altyazi-onizleme">${[['', 'klasik', 'Klasik'], ['niyetli', 'niyetli', 'Niyetli']].filter(([, a]) => O[a]).map(([d, a, ad]) => `<label class="altyazi-ornek" for="seg-altyazi-${d ? 1 : 0}" data-altyazi="${d}"><video src="${dosyaUrl(O[a].video)}" ${O[a].poster ? `poster="${kucukUrl(O[a].poster, 200)}"` : ''} muted loop autoplay playsinline preload="metadata" aria-label="${ad} altyazı örneği"></video><small>${ad}</small></label>`).join('')}</span><span class="altyazi-metin"></span>`;
    el.querySelectorAll('.altyazi-ornek video').forEach((vd) => vd.addEventListener('click', () => {  // tıklanan örneğin sesi açılır, öteki kısılır
      el.querySelectorAll('.altyazi-ornek video').forEach((o) => { if (o !== vd) o.muted = true; });
      vd.muted = !vd.muted;
    }));
  }
  el.querySelectorAll('.altyazi-ornek').forEach((x) => x.classList.toggle('secili', x.dataset.altyazi === v));
  const m = el.querySelector('.altyazi-metin') || el;
  m.textContent = (yok ? 'Anlatımsız filmde niyetli altyazı yok: yazı sesi ölçer. ' : '') + ALTYAZI_NOT[v] + (O.niyetli ? ' Örneğe tıklarsan sesi açılır.' : '');
  secimOzet();
}
const seg = (ad, et, ops, notVar = false, ilk = 0) => `<div class="seg-grup"><span class="seg-et" id="seg-${ad}">${et}</span><div class="seg" role="radiogroup" aria-labelledby="seg-${ad}">${ops.map(([v, a, dis], i) => `<label><input type="radio" name="${ad}" value="${esc(v)}" id="seg-${ad}-${i}" ${i === ilk ? 'checked' : ''} ${dis ? 'disabled' : ''}><span>${esc(a)}</span></label>`).join('')}</div>${notVar ? `<span class="seg-not" id="${ad}-not"></span>` : ''}</div>`;

async function yeniLevha(onMetin = '') {
  const G = await genelYukle();
  YS = {gorsel: rafYeni(), animasyon: rafYeni(), ses: rafYeni(), kaynak: 'kod', cesaret: 'cesur', referanslar: []};
  const C = G.claude || {};
  const sec = (id, et, ilk, ops) => `<label class="alan-et" for="${id}">${et}<select id="${id}"><option value="">${esc(ilk)}</option>${ops.map(([v, a]) => `<option value="${esc(v)}">${esc(a)}</option>`).join('')}</select></label>`;
  levhaAc(`
    <div class="levha-bas"><div><h2 id="levha-baslik">Yeni film</h2><p>Fikrini kendi cümlelerinle yaz. Claude türünü, görünüşünü ve senaryosunu önerir. Sen iki kez onaylarsın: önce planı, sonra filmi.</p></div>${kapatDugme}</div>
    <form class="yeni-form" id="yeni-form">
      ${!G.claudeVar ? `<div class="uyari-kutu">${ik('unlem')}<span><b>Claude Code bu bilgisayarda bulunamadı.</b> İstek gönderilemez; aşağıda “Gelişmiş” içinden boş bir video klasörü kurabilirsin.</span></div>` : ''}
      <label for="istek" class="form-et">Ne anlatmak istiyorsun?</label>
      <textarea class="istek-alan" id="istek" autofocus placeholder="Örnek: Kış yardımını anlatan 30 saniyelik dikey bir kampanya filmi. Sıcak, umutlu, çocuklara saygılı; sonunda bağış adresi.">${esc(onMetin)}</textarea>
      <fieldset style="border:0;padding:0;margin:0"><legend class="form-et">Nerede yayınlanacak? <span>Boş bırakırsan Claude karar verir</span></legend>
        <div class="cihazlar">${[['9x16', 'Dikey', 'Reels, Shorts, TikTok, hikâye', 20, 34], ['16x9', 'Yatay', 'YouTube, web, sunum, ekran', 40, 23], ['1x1', 'Kare', 'Akış gönderisi', 30, 30], ['4x5', 'Portre', 'Instagram akışı', 26, 32]]
          .filter(([v]) => G.formatlar[v]).map(([v, a, b, w, h]) => `<label class="cihaz"><input type="checkbox" name="format" value="${v}" id="fmt-${v}"><span class="sekil" style="width:${w}px;height:${h}px"></span><b>${a}</b><span>${b}</span></label>`).join('')}</div></fieldset>
      <div class="raflar"><div class="form-et" style="margin:0">Görüntü, hareket ve ses <span>Boş bırakırsan Claude bu filme özel icat eder. Kartlar esin kaynağıdır; birden çok seçebilirsin.</span></div>
        ${raf('gorsel')}${raf('animasyon')}${raf('ses')}</div>
      <div class="seg-izgara">
        ${seg('cesaret', 'Cesaret', Object.entries(CESARET), true, 1)}
        ${seg('anlatim', 'Anlatıcı · konuşma sesi', [['', 'Yapay ses'], ['kayit', 'Kendi sesim'], ['magnific', 'Magnific · Serkan', !G.magnific?.kurulu], ['yok', 'Anlatımsız']], true)}
        ${seg('altyazi', 'Altyazı', [['', 'Klasik'], ['niyetli', 'Niyetli · sesi gösterir']], true)}
        ${seg('muzik', 'Müzik', [['kod', 'Koddan üretim'], ['ace', 'ACE-Step', !G.aceVar], ['yok', 'Müziksiz']], true)}
        ${seg('motor', 'Motor', [['', 'Claude seçsin'], ['remotion', 'Remotion'], ['hyperframes', 'HyperFrames'], ['blender', 'Blender']], true)}
        <div class="cizer-grup" id="cizer-grup" hidden>${seg('cizer', 'Blender çizeri', [['', 'Claude seçsin'], ['cycles', 'Cycles'], ['eevee', 'EEVEE · hızlı']], true)}</div>
        ${seg('marka', 'Marka', [['', 'Yok'], ...(G.markalar || []).map((m) => [m.ad, m.kisa || m.baslik])])}
        ${seg('dil', 'Dil', [['', 'Claude seçsin'], ['tr', 'Türkçe'], ['en', 'İngilizce']])}
      </div>
      <label class="ek-alan" for="ekler">${ik('atac')}<span id="ek-ad">Logo, görsel, ses kaydı ya da müzik ekle</span><input type="file" id="ekler" multiple></label>
      <details class="aac" id="gelismis"><summary>${ik('sag')}Gelişmiş: film türü, seri, Claude, kredi sınırı, boş video</summary>
        <div class="yeni-form" style="gap:14px">
          <div class="secimler">
            ${sec('s-profil', 'Film türü', 'Claude seçsin', (G.profiller || []).map((p) => [p.ad, p.ad]))}
            ${sec('s-seri', 'Seri (ortak görünüş)', 'Yok: filme özel görünüş', (G.stiller || []).map((s) => [s.ad, s.ad]))}
            ${sec('s-model', 'Claude modeli', `Claude ayarlarındaki`, Object.entries(C.modeller || {}))}
            ${sec('s-efor', 'Efor', 'Claude ayarlarındaki', Object.entries(C.eforlar || {}).map(([k, a]) => [k, `${a} (${k})`]))}
            <label class="alan-et" for="s-kredi">Kredi sınırı <small>Magnific · ${G.magnific?.kurulu ? '<span class="cip yesil kucuk-cip">bağlı</span>' : '<span class="cip kucuk-cip">bağlı değil</span>'}</small><input id="s-kredi" type="number" inputmode="numeric" min="0" max="240000" step="500" value="${esc(String(G.uretimAyar?.kredi_siniri ?? 20000))}"></label>
          </div>
          <p class="ince" style="margin:0">${G.magnific?.kurulu ? 'Claude gerçekçi bir plaka (mekân, nesne, metafor, etiketli canlandırma) üretirse bu filmde en çok bu kadar kredi harcar; aşacaksa durur ve sana sorar.' : 'Magnific bağlı değil: Claude yapay zekâ ile görsel ya da video üretmez, filmi stüdyonun kendi yollarıyla kurar.'}</p>
          <label class="goz-satir" style="padding:0"><input type="checkbox" id="bos-video" ${G.claudeVar ? '' : 'checked'}><span><b>Claude'suz boş video kur.</b> Yalnız klasör ve iskelet kurulur; işi Claude Code'da kendin yönetirsin. Başlık, kimlik ve film türü gerekir.</span></label>
          <div class="form-izgara" id="bos-alanlar" ${G.claudeVar ? 'hidden' : ''}>
            <label class="alan-et" for="b-baslik">Başlık<input id="b-baslik" placeholder="ör. Kahve dünyayı nasıl dolaştı?"></label>
            <label class="alan-et" for="b-kimlik">Kimlik <small>klasör adı: küçük harf, rakam, alt çizgi</small><input id="b-kimlik" placeholder="kahve_dunyayi_dolasti"></label>
          </div>
        </div></details>
      <div class="levha-alt"><div class="alt-sol"><div class="secim-ozet" id="secim-ozet"></div><p>Claude önce bir plan hazırlar. Sen onaylamadan üretime geçilmez; kaynaksız bir iddia ya da eksik bir logo olursa durur ve sana sorar.</p></div>
        <button type="button" class="btn cam-btn buyuk" data-kapat>Vazgeç</button><button type="submit" class="btn ana-btn buyuk" id="yeni-gonder">${ik('yukari')}<span>Claude'a gönder</span></button></div>
    </form>`, 'genis');
  ['gorsel', 'animasyon', 'ses'].forEach(rafGuncelle);
  sesNotlari(); motorNot(); cesaretNot(); altyaziNot();
  const L = $('#levha');
  const bosMod = () => {
    const b = $('#bos-video').checked;
    $('#bos-alanlar').hidden = !b;
    $('#yeni-gonder span').textContent = b ? 'Boş videoyu kur' : "Claude'a gönder";
    if (b) $('#gelismis').open = true;
  };
  bosMod();
  $('#bos-video').addEventListener('change', bosMod);
  let elle = false;
  $('#b-kimlik').addEventListener('input', () => { elle = true; });
  $('#b-baslik').addEventListener('input', (e) => { if (!elle) $('#b-kimlik').value = slug(e.target.value); });
  $('#ekler').addEventListener('change', (e) => { const n = [...e.target.files].map((f) => f.name); $('#ek-ad').textContent = n.length ? n.join(', ') : 'Logo, görsel, ses kaydı ya da müzik ekle'; });
  L.addEventListener('click', (e) => {
    const b = e.target.closest('[data-raf-sec]');
    if (b) {
      const tur = b.dataset.rafSec;
      const ad = b.dataset.ad;
      const R = YS[tur];
      const ekle = ad && !R.kartlar.includes(ad);
      if (!ad) R.kartlar = [];   // "Claude icat etsin": öteki kartlar bırakılır
      else if (!ekle) R.kartlar = R.kartlar.filter((x) => x !== ad);
      else if (R.kartlar.length >= RAF_EN_COK) { bildir(`Bir rafta en çok ${RAF_EN_COK} kart seçilir: önce birini bırak.`); return; }
      else { R.kartlar.push(ad); R.goster = ad; }
      rafGuncelle(tur);
      if (tur === 'ses') {
        const ex = ekle ? katBul('ses', ad) : null;
        const kay = YS.kaynak === 'yok' ? 'ace' : YS.kaynak;
        const src = ex && sesOrnek(ex, kay);
        if (src && calanAnahtar !== `${ex.ad}:${kay}`) sesCal(`${ex.ad}:${kay}`, dosyaUrl(src));
        else if (!ekle && (!ad || calanAnahtar?.startsWith(`${ad}:`))) sesDur();
      }
      return;
    }
    const an = e.target.closest('[data-raf-anlat]');
    if (an) {
      const tur = an.dataset.rafAnlat;
      YS[tur].acik = !YS[tur].acik;
      rafGuncelle(tur);
      if (YS[tur].acik) $(`#tarif-${tur}`).focus();
      return;
    }
    const gs = e.target.closest('[data-raf-goster]');
    if (gs) { YS[gs.dataset.rafGoster].goster = gs.dataset.ad; rafGuncelle(gs.dataset.rafGoster); $(`[data-raf-goster="${gs.dataset.rafGoster}"][data-ad="${gs.dataset.ad}"]`)?.focus(); return; }
    const rs = e.target.closest('[data-ref-sil]');
    if (rs) { const [r] = YS.referanslar.splice(+rs.dataset.refSil, 1); ['gorsel', 'animasyon', 'ses'].forEach(anlatDurum); secimOzet(); bildir(`${r.dosya.name} kaldırıldı.`); return; }
    const k = e.target.closest('[data-raf-kaydir]');
    if (k) { const s = $(`#raf-serit-${k.dataset.rafKaydir}`); s.scrollBy({left: +k.dataset.yon * s.clientWidth * 0.8, behavior: 'smooth'}); }
  });
  L.addEventListener('change', (e) => {
    const t = e.target;
    if (t.name === 'muzik-kaynagi' || t.name === 'muzik') {
      YS.kaynak = t.value; sesNotlari();
      const sg = YS.ses.goster;
      if (calanAnahtar && sg && calanAnahtar.startsWith(`${sg}:`)) {
        const ex = katBul('ses', sg);
        if (t.value === 'yok') sesDur(); else if (ex?.onizleme?.[t.value]) sesCal(`${sg}:${t.value}`, dosyaUrl(ex.onizleme[t.value]));
      }
    }
    if (t.dataset.rafMod) { YS[t.dataset.rafMod].mod = t.value; rafGuncelle(t.dataset.rafMod); }
    if (t.dataset.rafRef) {
      const tur = t.dataset.rafRef;
      for (const f of t.files) YS.referanslar.push({tur, dosya: f});
      t.value = '';
      anlatDurum(tur); secimOzet();
    }
    if (t.name === 'cesaret') { YS.cesaret = t.value; cesaretNot(); }
    if (t.name === 'anlatim' || t.name === 'format' || t.name === 'marka' || t.name === 'dil') sesNotlari();
    if (t.name === 'anlatim' || t.name === 'altyazi') altyaziNot();
    if (t.name === 'motor') motorNot();
    if (t.name === 'cizer') cizerNot();
  });
  L.addEventListener('input', (e) => {
    const tur = e.target.dataset.rafTarif;
    if (tur) { YS[tur].tarif = e.target.value.slice(0, TARIF_EN_COK); anlatDurum(tur); secimOzet(); }
  });
  $('#yeni-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const deger = (n) => $(`input[name=${n}]:checked`)?.value || '';
    const formatlar = $$('input[name=format]:checked').map((c) => c.value);
    const ekler = [...$('#ekler').files];
    const dugme = $('#yeni-gonder');
    const secim = (t) => ({kartlar: [...YS[t].kartlar], mod: YS[t].kartlar.length ? YS[t].mod : 'esin', tarif: YS[t].tarif.trim()});
    const kat = {gorsel: secim('gorsel'), animasyon: secim('animasyon'), ses: secim('ses'), muzik_kaynagi: YS.kaynak !== 'yok' ? YS.kaynak : null};
    const refler = YS.referanslar.map((r) => r.dosya);
    const refYukle = async (id) => {
      for (const f of refler) {
        dugme.querySelector('span').textContent = `Yükleniyor: ${f.name}`;
        await api.post(`/api/basit/${id}/dosya?tur=referans&ad=${encodeURIComponent(f.name)}`, await f.arrayBuffer(), true);
      }
    };
    const ortak = {motor: deger('motor') || null, marka: deger('marka') || null, dil: deger('dil') || null, altyazi: deger('altyazi') || null,
      cizer: deger('motor') === 'blender' ? (deger('cizer') || null) : null};
    dugme.disabled = true;
    try {
      if ($('#bos-video').checked) {
        const id = $('#b-kimlik').value.trim();
        const baslik = $('#b-baslik').value.trim();
        const profil = $('#s-profil').value;
        if (!baslik || !id) throw new Error('Boş video için başlık ve kimlik gerekli.');
        if (!profil) throw new Error('Boş video için film türünü seç (Gelişmiş → Film türü).');
        const an = deger('anlatim');
        if (an === 'magnific') throw new Error('Magnific anlatıcısını Claude üretir: boş videoda Yapay ses ya da Kendi sesim seç.');
        await api.post('/api/yeni', {id, baslik, profil, stil: $('#s-seri').value, formatlar: formatlar.length ? formatlar : (G.profiller.find((p) => p.ad === profil)?.formatlar || []),
          ses: an === 'kayit' ? 'kayit' : an === 'yok' ? 'yok' : 'edge', katalog: kat, cesaret: YS.cesaret, ...ortak, dil: ortak.dil || 'tr'});
        await refYukle(id);
        levhaKapat(); genelTazele(); bildir('Video klasörü kuruldu.');
        location.hash = `#/film/${id}`;
        return;
      }
      const metin = $('#istek').value.trim();
      if (metin.length < 15) { $('#istek').focus(); throw new Error('Biraz daha anlat: ne, kime, nerede yayınlanacak?'); }
      const r = await api.post('/api/basit/yeni', {metin, yayin: 'karar', formatlar, katalog: kat, cesaret: YS.cesaret, claude: {model: $('#s-model').value, efor: $('#s-efor').value}, kredi_siniri: $('#s-kredi').value,
        anlatim: deger('anlatim') || null, muzik: YS.kaynak, bekle: ekler.length + refler.length > 0, ...ortak});
      try {
        for (const f of ekler) {
          dugme.querySelector('span').textContent = `Yükleniyor: ${f.name}`;
          await api.post(`/api/basit/${r.id}/dosya?ad=${encodeURIComponent(f.name)}`, await f.arrayBuffer(), true);
        }
        await refYukle(r.id);
        if (ekler.length || refler.length) await api.post(`/api/basit/${r.id}/basla`);
      } catch (er) { bildir(`Claude başlatılamadı: ${er.message}. Film sayfasındaki “Başlat” ile yeniden dene.`, 8000); }
      levhaKapat(); genelTazele(); bildir("Claude'a gönderildi. Planı hazırlayınca seni bekleyenlerde görünür.", 5000);
      location.hash = `#/film/${r.id}`;
    } catch (er) {
      bildir(er.message, 6000);
      dugme.disabled = false;
      dugme.querySelector('span').textContent = $('#bos-video').checked ? 'Boş videoyu kur' : "Claude'a gönder";
    }
  });
}
