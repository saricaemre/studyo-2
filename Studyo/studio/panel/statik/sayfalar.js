// Stüdyo paneli · Kütüphane, film türleri, öğrenimler, ayarlar, yardım, belge

const KAT_AD = {gorsel: 'Görüntü stilleri', animasyon: 'Hareket', ses: 'Ses'};
const KAT_TEKIL = {gorsel: 'görüntü stili', animasyon: 'hareket tipi', ses: 'ses stili'};
const KAT_KABUL = {gorsel: 'image/*,video/*', animasyon: 'video/*', ses: 'audio/*,video/*'};

// ---------------------------------------------------------------- Kütüphane
const kutSekmeler = (tur) => `<div class="parcali" role="tablist" aria-label="Kütüphane">${[['gorsel', 'Görüntü'], ['animasyon', 'Hareket'], ['ses', 'Ses'], ['model', '3B modeller'], ['gecis', 'Geçişler'], ['referans', 'Referanslar']]
  .map(([k, a]) => `<a role="tab" aria-selected="${k === tur}" href="#/kutuphane/${k}" style="text-decoration:none"><button type="button" tabindex="-1" class="${k === tur ? 'aktif' : ''}">${a}</button></a>`).join('')}</div>`;

SAYFA.kutuphane = async ([tur = 'gorsel']) => {
  if (tur === 'referans') return referansSayfasi();
  if (tur === 'model') return modelSayfasi();
  if (tur === 'gecis') return gecisSayfasi();
  if (!KAT_AD[tur]) tur = 'gorsel';
  const G = await genelYukle(true);
  const K = G.katalog;
  const L = K[tur] || [];
  const parca = kutSekmeler(tur);
  const alt = {gorsel: "Görüntü için esin kartları: her biri üç varyasyonla gelir. Seçersen Claude buradan yola çıkar, karıştırır ve aşar; 'Aynen' dersen üç varyasyon üç yolun görünüşü olur.",
    animasyon: "Hareket için esin kartları: kurallar, kamera, geçiş, tempo. Seçersen Claude buradan yola çıkar; 'Aynen' dersen tarife uyar.",
    ses: `Ses için esin kartları: müzik, efekt ailesi, anlatıcı hızı ve miks. Seçersen Claude buradan yola çıkar; 'Aynen' dersen kartın ayarı kullanılır. Müzik iki kaynaktan gelir: koddan üretim ya da bu Mac'te çalışan ACE-Step${G.aceVar ? '' : ' (kurulu değil)'}.`}[tur];
  const uygun = (e) => (e.uygun?.length ? `<div class="cipler">${e.uygun.slice(0, 3).map((u) => `<span class="cip">${esc(u)}</span>`).join('')}</div>` : '');
  const filmden = (e) => String(e.kaynak || '').startsWith('film:');
  const rozet = (e) => `${e.durum === 'taslak' ? '<span class="cip turuncu">taslak · onayını bekliyor</span>' : ''}${e.kaynak === 'referans' ? '<span class="cip">senin referansın</span>' : ''}${filmden(e) ? `<span class="cip">filmden: ${esc(e.kaynak.slice(5))}</span>` : ''}`;
  const eylem = (e) => (e.kaynak === 'referans' || filmden(e) ? `<div class="dugmeler" style="padding:0 4px">${e.durum === 'taslak' ? `<button type="button" class="btn ana-btn kucuk" data-kat-onay="${e.ad}">Kataloğa ekle</button>` : ''}<button type="button" class="btn cam-btn kucuk" data-kat-sil="${e.ad}">Sil</button></div>` : '');
  const not = (e) => (e.not ? `<details class="aac" style="padding:0 4px"><summary>${ik('sag')}Claude'un notu</summary><div class="durum-md">${md(e.not)}</div></details>` : '');
  let govde;
  if (tur === 'ses') {
    govde = `<div class="ses-liste">${L.map((e) => {
      const o = e.onizleme || {};
      const ana = o.ace ? ['ace', o.ace] : o.kod ? ['kod', o.kod] : null;
      return `<div class="ses-satir">${ana ? calDugme(`${e.ad}:${ana[0]}`, dosyaUrl(ana[1]), `${e.baslik} örneğini dinle`, 'ses-oynat') : '<span class="ses-oynat"></span>'}
        <div><h3>${esc(e.baslik)} ${rozet(e)}</h3><p>${esc(e.ozet)}</p>
          <div class="cipler" style="margin-top:8px">${o.kod ? calDugme(`${e.ad}:kod`, dosyaUrl(o.kod), 'Koddan üretilen örneği dinle', 'kucuk-cal') + '<span class="cip">koddan</span>' : ''}${o.ace ? calDugme(`${e.ad}:ace`, dosyaUrl(o.ace), 'ACE-Step örneğini dinle', 'kucuk-cal') + '<span class="cip">ACE-Step</span>' : ''}${e.detay?.bpm ? `<span class="cip">${e.detay.bpm} BPM</span>` : ''}</div>
          ${not(e)}${eylem(e)}</div>
        <span class="ekolayzer" aria-hidden="true"><i></i><i></i><i></i></span></div>`;
    }).join('')}</div>`;
  } else {
    govde = `<div class="kat-izgara">${L.map((e) => {
      const g = tur === 'gorsel' ? ((e.varyasyonlar || [])[0]?.onizleme || e.onizleme) : null;
      const medyaH = tur === 'gorsel' ? (g ? `<img src="${kucukUrl(g, 400)}" alt="" loading="lazy">` : '')
        : (e.onizleme ? `<video src="${dosyaUrl(e.onizleme)}" ${e.poster ? `poster="${kucukUrl(e.poster, 400)}"` : ''} muted loop autoplay playsinline preload="metadata"></video>` : '');
      return `<article class="kat-kart"><div class="kg">${medyaH}</div><h3>${esc(e.baslik)}</h3>${rozet(e) ? `<div class="cipler" style="padding:0 4px">${rozet(e)}</div>` : ''}<p>${esc(e.ozet)}</p>
        ${tur === 'gorsel' && e.varyasyonlar?.length ? `<p class="ince" style="padding:0 4px">${e.varyasyonlar.map((v) => `${v.harf.toUpperCase()} · ${esc(v.ad)}`).join(' · ')}</p>` : ''}
        ${tur === 'animasyon' && e.detay?.ornek_motor ? `<p class="ince" style="padding:0 4px">Örneği ${MOTOR_AD[e.detay.ornek_motor] || e.detay.ornek_motor} ile çizildi; her motorda uygulanır.</p>` : ''}
        ${uygun(e)}${not(e)}${eylem(e)}</article>`;
    }).join('')}<button type="button" class="kat-kart ekle" data-referans-ekle>${ik('arti')}<b>Kendi referansın</b><span class="ince">Beğendiğin bir ${tur === 'animasyon' ? 'videoyu' : 'görseli ya da videoyu'} yükle; Claude ölçer ve taslak bir ${KAT_TEKIL[tur]} yazar.</span></button></div>`;
  }
  const bekleyen = (K.bekleyen || []).filter((b) => b.tur === tur);
  $('#v-sayfa').innerHTML = `${ustCubuk(KAT_AD[tur], alt, parca)}<div class="icerik" style="gap:18px">
    ${bekleyen.length ? `<div class="uyari-kutu">${ik('claude')}<span><b>Claude seçenek çıkarıyor (referanstan ya da bir filmden):</b> ${bekleyen.map((b) => esc(b.ad)).join(', ')}. Bitince burada taslak olarak görünür.</span></div>` : ''}
    ${govde}
    ${tur === 'ses' ? `<div class="dugmeler"><button type="button" class="btn cam-btn" data-referans-ekle>${ik('arti')}Kendi referansından ses stili</button></div><p class="ayar-not">ACE-Step örnekleri bu bilgisayarda çalışan yapay zekâ müzik modeliyle üretildi; kullanılırsa yayın paketinde belirtilir.</p>` : ''}
  </div>`;
  const S = $('#v-sayfa');
  $$('[data-referans-ekle]', S).forEach((b) => b.addEventListener('click', () => referansLevha(tur)));
  $$('[data-kat-onay]', S).forEach((b) => b.addEventListener('click', async () => {
    try { await api.post('/api/katalog/onay', {tur, ad: b.dataset.katOnay}); bildir('Kataloğa eklendi.'); SAYFA.kutuphane([tur]); } catch (e) { bildir(e.message, 6000); }
  }));
  $$('[data-kat-sil]', S).forEach((b) => b.addEventListener('click', async () => {
    const n = await onaySor(b, {soru: 'Bu seçenek ve önizlemeleri silinsin mi? (Referansın da silinir; film olduğu gibi kalır.)', evet: 'Sil', tehlike: true});
    if (n === null) return;
    try { await api.post('/api/katalog/sil', {tur, ad: b.dataset.katSil}); bildir('Silindi.'); SAYFA.kutuphane([tur]); } catch (e) { bildir(e.message, 6000); }
  }));
};
function referansLevha(tur) {
  levhaAc(`<div class="levha-bas"><div><h2 id="levha-baslik">Kendi referansın</h2><p>Beğendiğin bir ${tur === 'ses' ? 'parçayı' : tur === 'animasyon' ? 'videoyu' : 'görseli ya da videoyu'} yükle; Claude ondan yeni bir ${KAT_TEKIL[tur]} taslağı çıkarsın. Referans kopyalanmaz; ölçülebilir dili (palet, tempo, ses karakteri) alınır. Taslak sen onaylayınca kataloğa girer.</p></div>${kapatDugme}</div>
    <form class="yeni-form" id="ref-form" style="gap:14px">
      <div class="form-izgara"><label class="alan-et" for="ref-ad">Ad <small>küçük harf ve tire, ör. gece-treni</small><input id="ref-ad" placeholder="gece-treni" autofocus></label>
        <label class="alan-et" for="ref-dosya">Dosya<input type="file" id="ref-dosya" accept="${KAT_KABUL[tur]}" style="padding-top:7px"></label></div>
      <label class="alan-et" for="ref-not">Not <small>bu referansın neyini seviyorsun? (isteğe bağlı)</small><textarea id="ref-not" rows="3" placeholder="ör. renkleri ve yavaş kamera hareketi"></textarea></label>
      <div class="levha-alt"><div class="alt-sol"><p>Claude arka planda çalışır; ilerlemesi sağ altta görünür.</p></div><button type="button" class="btn cam-btn buyuk" data-kapat>Vazgeç</button><button type="submit" class="btn ana-btn buyuk">${ik('yukari')}Claude'a gönder</button></div>
    </form>`, 'dar');
  $('#ref-ad').addEventListener('input', (e) => { e.target.value = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'); });
  $('#ref-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const ad = $('#ref-ad').value.trim();
    const f = $('#ref-dosya').files[0];
    if (!/^[a-z][a-z0-9-]{2,30}$/.test(ad)) return bildir('Ad: küçük harf, rakam ve tire (en az 3 harf).');
    if (!f) return bildir('Bir dosya seç.');
    try {
      const r = await api.post(`/api/katalog/referans?tur=${tur}&ad=${encodeURIComponent(ad)}&dosya=${encodeURIComponent(f.name)}&not=${encodeURIComponent($('#ref-not').value.trim())}`, await f.arrayBuffer(), true);
      levhaKapat();
      bildir('Claude referansı inceliyor; bitince taslak burada görünür.', 5000);
      isIzle(r.is, () => SAYFA.kutuphane([tur]));
      SAYFA.kutuphane([tur]);
    } catch (er) { bildir(er.message, 6000); }
  });
}
async function referansSayfasi() {
  const G = await genelYukle(true);
  const parca = kutSekmeler('referans');
  $('#v-sayfa').innerHTML = `${ustCubuk('Referanslar', 'Beğendiğin bir videoyu ver; stüdyo ölçülebilir dilini çıkarsın: renk paleti, kesme temposu, hareket, ses yüksekliği, müzik temposu, konuşma hızı. Referans kopyalanmaz, çıta olarak kullanılır.', parca)}
    <div class="icerik" style="gap:18px">
      <div class="profil-kart cam"><h3>Yeni analiz</h3>
        <div class="form-izgara"><label class="alan-et" for="ref-video">Video dosyası yükle<input type="file" id="ref-video" accept="video/*" style="padding-top:7px"></label>
          <label class="alan-et" for="ref-yol">ya da bilgisayardaki yolu yaz<input id="ref-yol" placeholder="~/Downloads/begendigim.mp4"></label></div>
        <div class="dugmeler"><button type="button" class="btn ana-btn" id="ref-baslat">Analiz et</button><span class="ince">Konuşma varsa Whisper da çalışır; birkaç dakika sürebilir.</span></div></div>
      <div class="ogrenim-liste">${G.referanslar.map((r) => `<details class="ogrenim" data-analiz="${esc(r.analiz || '')}"><summary><span class="no">${ik('goz')}</span><span><span class="kural">${esc(r.ad)}</span><span class="kaynak">${r.analiz ? 'analiz hazır' : 'analiz dosyası yok'}</span></span><span></span></summary>
        <div class="ogrenim-ic"><div class="kare-izgara" style="grid-template-columns:repeat(2,1fr)">${r.palet ? `<button type="button" data-buyut="${dosyaUrl(r.palet)}"><span class="kg" style="aspect-ratio:auto;height:110px"><img src="${kucukUrl(r.palet, 400)}" alt=""></span><small>palet</small></button>` : ''}${r.kareler ? `<button type="button" data-buyut="${dosyaUrl(r.kareler)}"><span class="kg" style="aspect-ratio:auto;height:110px"><img src="${kucukUrl(r.kareler, 400)}" alt=""></span><small>kareler</small></button>` : ''}</div>
          <div class="ref-md"></div><p class="ince">Bu analizden yeni bir stil için Claude'a: <code>referans/${esc(r.ad)}/analiz.md'den yeni bir görünüş çıkar</code></p></div></details>`).join('') || '<div class="bos-durum"><p>Henüz analiz yok.</p></div>'}</div>
    </div>`;
  const S = $('#v-sayfa');
  $$('details[data-analiz]', S).forEach((det) => det.addEventListener('toggle', async () => {
    const m = $('.ref-md', det);
    if (det.open && det.dataset.analiz && !m.dataset.yuklendi) {
      try { const b = await api.get(`/api/belge?yol=${encodeURIComponent(det.dataset.analiz)}`); m.innerHTML = md(b.metin); m.dataset.yuklendi = '1'; } catch (e) { m.textContent = e.message; }
    }
  }));
  $('#ref-baslat').addEventListener('click', async () => {
    const f = $('#ref-video').files[0];
    try {
      const j = f ? await api.post(`/api/referans-yukle?ad=${encodeURIComponent(f.name)}`, await f.arrayBuffer(), true) : await api.post('/api/referans', {yol: $('#ref-yol').value.trim()});
      isIzle(j, () => referansSayfasi());
    } catch (e) { bildir(e.message, 6000); }
  });
}

// 3B modeller: threejsassets.com'un ücretsiz GLB'leri (pipeline/model3b.py). İndirme kullanıcının kendi hesabıyla, tarayıcıda;
// panel yalnız katalog bilgisini gösterir (afiş, ad, bağlantı) ve indirilen dosyayı kütüphaneye alır.
let modelArama = '';
async function modelSayfasi() {
  const K = await api.get('/api/3b');
  const M = K.modeller;
  const sayi = $('#sayi-model');
  if (sayi) sayi.textContent = M.length || '';
  const olcu = (b) => { const k = b.glb?.kutu?.boyut; return k ? k.map((x) => sn(x, x < 10 ? 1 : 0)).join(' × ') + ' m' : ''; };
  const yerelKart = (b) => `<article class="kat-kart"><div class="kg">${b.onizlemeYol ? `<img src="${kucukUrl(b.onizlemeYol, 400)}&v=${b.tarih}" alt="" loading="lazy">`
      : b.poster_url ? `<img src="${esc(b.poster_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ''}</div>
    <h3>${esc(b.name)}</h3>
    <div class="cipler" style="padding:0 4px">${olcu(b) ? `<span class="cip">${olcu(b)}</span>` : ''}<span class="cip">${(b.glb?.ucgen ?? b.triangles ?? 0).toLocaleString('tr-TR')} üçgen</span>${b.glb?.animasyon?.length ? `<span class="cip claude">${b.glb.animasyon.length} animasyon</span>` : ''}${b.filmler.map((f) => `<span class="cip yesil">${esc(f)}</span>`).join('')}</div>
    <p class="ince" style="padding:0 4px"><code>${esc(b.slug)}</code> · Claude'a: “${esc(b.slug)} modelini filme al”</p>
    <div class="dugmeler" style="padding:0 4px"><button type="button" class="btn cam-btn kucuk" data-m-onizle="${esc(b.slug)}">${ik('goz')}${b.onizlemeYol ? 'Yeniden çiz' : 'Stüdyoda çiz'}</button><a class="btn cam-btn kucuk" href="${esc(b.url)}" target="_blank" rel="noopener">${ik('sagok')}Sayfası</a><button type="button" class="btn cam-btn kucuk" data-m-sil="${esc(b.slug)}">Sil</button></div></article>`;
  $('#v-sayfa').innerHTML = `${ustCubuk('3B modeller', 'threejsassets.com\'un ücretsiz düşük poligon modelleri (GLB): yapı, doğa, araç, eşya, iç mekân. Videoda ticari kullanım serbest, atıf gerekmez; model dosyası başkasıyla paylaşılmaz. İndirmek senin ücretsiz hesabınla olur; indirdiğin modeli buraya bırak, Claude filmde kullanır.', kutSekmeler('model'))}
    <div class="icerik" style="gap:28px">
      <label class="profil-kart cam model-birak" id="m-birak" for="m-dosya">${ik('indir')}<span><b>İndirdiğin .glb dosyalarını buraya bırak</b><span class="ince"> ya da tıklayıp seç. Dosya adı değiştirilmemeli (ör. ammo-crate.glb): stüdyo modeli adından tanır.</span></span>
        <input type="file" id="m-dosya" accept=".glb,model/gltf-binary" multiple hidden></label>
      <section><div class="bolum-bas"><h2>Kütüphanen</h2><span>${M.length ? `${M.length} model · bu bilgisayarda` : 'henüz model yok'}</span></div>
        ${M.length ? `<div class="kat-izgara">${M.map(yerelKart).join('')}</div>` : '<p class="ince" style="padding:0 4px">Aşağıda ara, beğendiğinin sayfasını aç, oradan indir (ücretsiz hesap, e-postana gelen bağlantıyla giriş) ve dosyayı yukarı bırak. Ya da Claude\'a “çadır modeli bul ve filme al” de.</p>'}</section>
      <section><div class="bolum-bas"><h2>Katalogda ara</h2><span>ücretsiz modeller · İngilizce sözcükle: tent, crate, tree, truck, house</span></div>
        <input class="girdi" id="m-ara" type="search" placeholder="ör. tent" value="${esc(modelArama)}" style="max-width:420px;margin:0 4px 16px">
        <div id="m-sonuc"></div>
        <p class="ince" style="padding:12px 4px 0">Katalog bilgisi ve afişler: <a href="${esc(K.site)}/assets/free" target="_blank" rel="noopener">threejsassets.com</a>. Panel dosya indirmez; indirme sitenin kendisinde, senin hesabınla.</p></section>
    </div>`;
  const S = $('#v-sayfa');
  const ara = async () => {
    const q = $('#m-ara').value.trim();
    modelArama = q;
    const kutu = $('#m-sonuc');
    if (!q) { kutu.innerHTML = ''; return; }
    kutu.innerHTML = '<p class="ince" style="padding:0 4px">aranıyor…</p>';
    try {
      const r = await api.get(`/api/3b/ara?q=${encodeURIComponent(q)}&n=48`);
      if ($('#m-ara')?.value.trim() !== q) return;
      kutu.innerHTML = r.sonuc.length ? `<div class="kat-izgara">${r.sonuc.map((m) => `<article class="kat-kart"><div class="kg">${m.poster_url ? `<img src="${esc(m.poster_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ''}</div>
          <h3>${esc(m.name)}</h3><div class="cipler" style="padding:0 4px"><span class="cip">${(m.triangles || 0).toLocaleString('tr-TR')} üçgen</span><span class="cip">${Math.max(1, Math.round((m.file_size_bytes || 0) / 1024))} KB</span>${m.category ? `<span class="cip">${esc(m.category)}</span>` : ''}${m.yerel ? '<span class="cip yesil">kütüphanede</span>' : ''}</div>
          <p style="display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden">${esc(m.description || '')}</p>
          <div class="dugmeler" style="padding:0 4px"><a class="btn ${m.yerel ? 'cam-btn' : 'ana-btn'} kucuk" href="${esc(m.url)}" target="_blank" rel="noopener">${ik('sagok')}${m.yerel ? 'Sayfası' : 'Sitede indir'}</a></div></article>`).join('')}</div>`
        : '<p class="ince" style="padding:0 4px">Sonuç yok. Başka bir İngilizce sözcük dene.</p>';
    } catch (e) { kutu.innerHTML = `<p class="ince" style="padding:0 4px">${esc(e.message)}</p>`; }
  };
  let zaman = null;
  $('#m-ara').addEventListener('input', () => { clearTimeout(zaman); zaman = setTimeout(ara, 300); });
  if (modelArama) ara();
  const yukle = async (dosyalar) => {
    for (const f of dosyalar) {
      try {
        const r = await api.post(`/api/3b/ekle?dosya=${encodeURIComponent(f.name)}`, await f.arrayBuffer(), true);
        bildir(`Kütüphaneye alındı: ${r.ad}`);
      } catch (e) { bildir(`${f.name}: ${e.message}`, 7000); }
    }
    modelSayfasi();
  };
  const birak = $('#m-birak');
  $('#m-dosya').addEventListener('change', (e) => yukle([...e.target.files]));
  birak.addEventListener('dragover', (e) => { e.preventDefault(); birak.classList.add('ustunde'); });
  birak.addEventListener('dragleave', () => birak.classList.remove('ustunde'));
  birak.addEventListener('drop', (e) => { e.preventDefault(); birak.classList.remove('ustunde'); yukle([...e.dataTransfer.files]); });
  $$('[data-m-onizle]', S).forEach((b) => b.addEventListener('click', async () => {
    try { isIzle(await api.post('/api/3b/onizle', {slug: b.dataset.mOnizle}), () => modelSayfasi()); } catch (e) { bildir(e.message, 6000); }
  }));
  $$('[data-m-sil]', S).forEach((b) => b.addEventListener('click', async () => {
    const n = await onaySor(b, {soru: 'Model bu bilgisayarın kütüphanesinden silinsin mi? Filmlere kopyalanmış dosyalar yerinde kalır.', evet: 'Sil', tehlike: true});
    if (n === null) return;
    try { await api.post('/api/3b/sil', {slug: b.dataset.mSil}); bildir('Silindi.'); modelSayfasi(); } catch (e) { bildir(e.message, 6000); }
  }));
}

// Geçişler (oturum 6a): gl-transitions kataloğunun gölgelendirici geçişleri, iki nötr kartla önizleme (./st gecis onizle). Salt göz atma:
// geçişi Claude senaryoda seçer ve gerekçesini yazar; kullanıcı “Claude'a söyle” ile değiştirir. Kartın üstüne gelince klip oynar.
let gecisFiltre = {etiket: '', ara: ''};
async function gecisSayfasi() {
  const K = await api.get('/api/gecis');
  const L = K.gecisler;
  const sayac = {};
  L.forEach((g) => g.etiketler.forEach((e) => { sayac[e] = (sayac[e] || 0) + 1; }));
  const one = Object.keys(sayac).filter((e) => sayac[e] >= 5).sort((a, b) => sayac[b] - sayac[a] || a.localeCompare(b, 'tr')).slice(0, 14);
  const sayi = $('#sayi-gecis');
  if (sayi) sayi.textContent = L.length || '';
  $('#v-sayfa').innerHTML = `${ustCubuk('Geçişler', `Sahneler arasında gölgelendiriciyle çizilen ${L.length} geçiş: sayfa çevirme, mürekkep, perde, dalga, yanma… Düz kesim varsayılandır; geçiş anlam taşıdığında kullanılır. Geçişi Claude senaryoda seçer ve gerekçesini yazar; değiştirmek için Claude'a söyle (ör. “ikinci kesimde InkBleed olsun”). Remotion filmlerinde ve karma filmin sahne sınırlarında çalışır.`, kutSekmeler('gecis'))}
    <div class="icerik" style="gap:18px">
      <div class="dugmeler" style="flex-wrap:wrap;gap:8px"><input class="girdi" id="g-ara" type="search" placeholder="ara: page, ink, wipe…" value="${esc(gecisFiltre.ara)}" style="max-width:260px">
        <button type="button" class="btn ${gecisFiltre.etiket ? 'cam-btn' : 'ana-btn'} kucuk" data-g-etiket="">hepsi <span class="ince">${L.length}</span></button>
        ${one.map((e) => `<button type="button" class="btn ${gecisFiltre.etiket === e ? 'ana-btn' : 'cam-btn'} kucuk" data-g-etiket="${esc(e)}">${esc(e)} <span class="ince">${sayac[e]}</span></button>`).join('')}</div>
      ${K.eksik ? `<div class="uyari-kutu">${ik('claude')}<span>${K.eksik} geçişin önizlemesi henüz çizilmedi (./st gecis onizle --hepsi).</span></div>` : ''}
      <div class="kat-izgara" id="g-izgara"></div>
      <p class="ayar-not">Kaynak: ${esc(K.kaynak)} (MIT; her geçişin yazarı ve lisansı kartında). Açıklamalar kataloğun kendisinden (İngilizce). Ek doku isteyen ${Object.keys(K.cikarilan).length} geçiş (${Object.keys(K.cikarilan).map(esc).join(', ')}) stüdyoya alınmadı. Önizleme kartları görünüşten bağımsız gri tonlardır; filmde geçiş kendi sahnelerini birleştirir.</p>
    </div>`;
  const ciz = () => {
    const q = gecisFiltre.ara.toLowerCase();
    const S = L.filter((g) => (!gecisFiltre.etiket || g.etiketler.includes(gecisFiltre.etiket))
      && (!q || g.ad.toLowerCase().includes(q) || g.aciklama.toLowerCase().includes(q) || g.etiketler.some((e) => e.includes(q))));
    $('#g-izgara').innerHTML = S.map((g) => `<article class="kat-kart" data-g-kart>
        <div class="kg">${g.onizleme ? `<video src="${dosyaUrl(g.onizleme)}" ${g.poster ? `poster="${dosyaUrl(g.poster)}" preload="none"` : 'preload="metadata"'} muted loop playsinline></video>` : ''}</div>
        <h3>${esc(g.ad)}</h3>
        <div class="cipler" style="padding:0 4px">${g.etiketler.slice(0, 4).map((e) => `<span class="cip">${esc(e)}</span>`).join('')}</div>
        <p style="display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden" title="${esc(g.aciklama)}">${esc(g.aciklama)}</p>
        <p class="ince" style="padding:0 4px">${g.param ? `Ayar: ${esc(g.param)}` : 'Ayarsız'} · ${esc(g.lisans)} · ${esc(g.yazar)}</p></article>`).join('')
      || '<p class="ince" style="padding:0 4px">Bu süzgeçte geçiş yok.</p>';
    $$('[data-g-kart]', $('#g-izgara')).forEach((k) => {
      const vid = $('video', k);
      if (!vid) return;
      k.addEventListener('mouseenter', () => { vid.play().catch(() => {}); });
      k.addEventListener('mouseleave', () => { vid.pause(); vid.currentTime = 0; });
    });
  };
  ciz();
  let zaman = null;
  $('#g-ara').addEventListener('input', (e) => { clearTimeout(zaman); zaman = setTimeout(() => { gecisFiltre.ara = e.target.value.trim(); ciz(); }, 200); });
  $$('[data-g-etiket]').forEach((b) => b.addEventListener('click', () => { gecisFiltre.etiket = b.dataset.gEtiket; gecisSayfasi(); }));
}

// ---------------------------------------------------------------- Film türleri, seriler, formatlar, markalar
SAYFA.turler = async () => {
  const G = await genelYukle();
  $('#v-sayfa').innerHTML = `${ustCubuk('Film türleri', 'Her tür ölçülebilir çıtalar (süre, kanca, ses yüksekliği) ve bir öneri vuruş iskeleti taşır. Hikâyenin iskeletini film kurabilir. Yeni bir tür, yeni bir profil dosyasıdır.')}
    <div class="icerik" style="gap:28px">
      <div class="profil-izgara">${G.profiller.map((p) => `<article class="profil-kart cam"><h3>${esc(p.ad)}</h3><p>${esc(p.aciklama)}</p>
        <div class="iskelet" title="Öneri iskelet: film kendi yapısını kurabilir">${(p.vuruslar || []).map((v, i) => `${i ? ik('sag') : ''}<span>${esc(v)}</span>`).join('')}<small class="iskelet-not">öneri</small></div>
        <div class="citalar"><div><b>${p.sure[0]}–${p.sure[1]} sn</b><span>süre</span></div><div><b>≤ ${sn(p.kanca_sn, p.kanca_sn % 1 ? 1 : 0)} sn</b><span>kanca</span></div><div><b>${(p.lufs || []).join('…')}</b><span>LUFS</span></div></div>
        <div class="cipler">${(p.formatlar || []).map((f) => `<span class="cip">${fmtEtiket(f)}</span>`).join('')}${p.wpm ? `<span class="cip">${p.wpm[0]}–${p.wpm[1]} kelime/dk</span>` : '<span class="cip">anlatımsız ya da kısa anlatım</span>'}${p.kaynak_zorunlu ? '<span class="cip">kaynak zorunlu</span>' : ''}</div></article>`).join('')}</div>
      <section><div class="bolum-bas"><h2>Seriler</h2><span>Birkaç filmin bilerek paylaştığı görünüş</span></div>
        <div class="profil-izgara">${G.stiller.map((s) => `<article class="profil-kart cam"><h3>${esc(s.ad)}</h3><p>${satirIci(s.ozet)}</p>${s.rehber ? `<div class="dugmeler"><a class="btn cam-btn kucuk" href="#/belge?yol=${encodeURIComponent(s.rehber)}">Rehberi oku</a></div>` : ''}</article>`).join('') || '<p class="ince">Henüz seri yok.</p>'}</div></section>
      <section><div class="bolum-bas"><h2>Formatlar</h2><span>Her format ayrı bir kompozisyondur; merkezden kırpılmaz</span></div>
        <div class="tablo-kap"><table><thead><tr><th>Format</th><th>Ad</th><th>Boyut</th><th>Platform arayüzüne ait kenarlar</th></tr></thead><tbody>
          ${Object.entries(G.formatlar).map(([k, f]) => `<tr><td><b>${fmtEtiket(k)}</b></td><td>${esc(f.ad)}</td><td>${f.w}×${f.h}</td><td>üst %${Math.round(f.guvenli.ust * 100)} · alt %${Math.round(f.guvenli.alt * 100)} · sol %${Math.round(f.guvenli.sol * 100)} · sağ %${Math.round(f.guvenli.sag * 100)}</td></tr>`).join('')}
        </tbody></table></div></section>
      ${(G.markalar || []).length ? `<section><div class="bolum-bas"><h2>Marka kitleri</h2><span>Kurumun resmi logoları, renkleri ve ton kuralları</span></div><div class="cipler">${G.markalar.map((m) => `<span class="cip">${esc(m.baslik)}</span>`).join('')}</div></section>` : ''}
    </div>`;
};

// ---------------------------------------------------------------- Öğrenimler
SAYFA.ogrenimler = async () => {
  const b = await api.get(`/api/belge?yol=${encodeURIComponent('kanal/ogrenimler.md')}`);
  const satirlar = mdTablo(b.metin, /Yeni kural/i).reverse();
  const tabloSonu = b.metin.split('\n').reduce((a, l, i, L) => (/^\|/.test(l) && !/^\|/.test(L[i + 1] || '') ? i : a), -1);
  const kalan = tabloSonu >= 0 ? b.metin.split('\n').slice(tabloSonu + 1).join('\n') : '';
  const k = (r, d) => r[Object.keys(r).find((x) => d.test(x))] || '';
  $('#v-sayfa').innerHTML = `${ustCubuk('Öğrenimler', 'Tekrar edebilecek her hata bir kurala dönüşür.')}
    <div class="icerik" style="gap:18px">
      <div class="ogrenim-ozet cam"><span class="sayi-buyuk">${satirlar.length}</span><div><p>Her satır bir kanıttan doğdu ve sisteme işlendi: bir kural, bir profil, bir ölçüm ya da kod değişikliği.</p><div class="dongu">${['Brief', 'Sistem', 'Film', 'İnceleme', 'Daha iyi sistem'].map((x, i) => `${i ? ik('sagok') : ''}<span>${x}</span>`).join('')}</div></div></div>
      <div class="ogrenim-liste">${satirlar.map((r) => { const du = sadeMetin(k(r, /Durum/)); return `<details class="ogrenim"><summary><span class="no">#${esc(k(r, /^#$/))}</span><span><span class="kural">${esc(sadeMetin(k(r, /Yeni kural/)))}</span><span class="kaynak">${esc(sadeMetin(k(r, /Kaynak/)))} · ${esc(gun(k(r, /Tarih/)))}</span></span><span class="cip ${/işlendi/i.test(du) ? 'yesil' : ''}">${esc(du.length > 18 ? du.slice(0, 16) + '…' : du)}</span></summary>
        <div class="ogrenim-ic"><span><b>Kanıt:</b> ${esc(sadeMetin(k(r, /Kanıt/)))}</span><span><b>İşlendiği yer:</b> <code>${esc(sadeMetin(k(r, /İşlendiği/)))}</code></span></div></details>`; }).join('')}</div>
      ${kalan.trim() ? `<div class="profil-kart cam">${md(kalan)}</div>` : ''}
    </div>`;
};

// ---------------------------------------------------------------- Ayarlar
SAYFA.ayarlar = async () => {
  const G = await genelYukle(true);
  const C = G.claude;
  const modelSec = (a, deger) => {
    const bilinen = deger === '' || C.modeller[deger];
    return `<label class="alan-et"><span class="gizli-et" hidden>Model</span><select data-model="${a}" aria-label="Model">
      <option value="" ${deger === '' ? 'selected' : ''}>Varsayılan (${esc(C.varsayilan.model)})</option>
      ${Object.entries(C.modeller).map(([k, ad]) => `<option value="${k}" ${deger === k ? 'selected' : ''}>${esc(ad)}</option>`).join('')}
      <option value="_diger" ${bilinen ? '' : 'selected'}>Diğer: model adını yaz</option></select>
      <input data-model-diger="${a}" placeholder="ör. claude-opus-5-5" value="${bilinen ? '' : esc(deger)}" ${bilinen ? 'hidden' : ''} aria-label="Model adı"></label>`;
  };
  const eforSec = (a, deger) => `<label class="alan-et"><select data-efor="${a}" aria-label="Efor"><option value="" ${deger === '' ? 'selected' : ''}>Varsayılan (${esc(C.varsayilan.efor)})</option>
    ${Object.entries(C.eforlar).map(([k, ad]) => `<option value="${k}" ${deger === k ? 'selected' : ''}>${esc(ad)} (${k})</option>`).join('')}</select></label>`;
  const M = G.magnific || {};
  const B = M.bakiye;
  const tl = (n) => Number(n || 0).toLocaleString('tr-TR');
  $('#v-sayfa').innerHTML = `${ustCubuk('Ayarlar', 'Claude, Magnific, anlatıcı sesi ve panel.')}
    <div class="icerik" style="gap:28px">
      <section><div class="bolum-bas"><h2>Claude</h2><span>Her aşamanın modeli ve eforu</span></div>
        <div class="ayar-grup">
          <div class="ayar-satir"><div><b>Tümü</b><span>Aşağıdakilerin hepsine aynı seçimi uygular</span></div>${modelSec('_tumu', '')}<div style="display:flex;gap:8px;align-items:center">${eforSec('_tumu', '')}<button type="button" class="btn cam-btn kucuk" id="tumune">Uygula</button></div></div>
          ${Object.entries(C.asamalar).map(([a, ac]) => `<div class="ayar-satir"><div><b>${esc(ac.split(':')[0])}</b><span>${esc(ac.split(':').slice(1).join(':').trim())}</span></div>${modelSec(a, C.ayar[a]?.model || '')}${eforSec(a, C.ayar[a]?.efor || '')}</div>`).join('')}
        </div>
        <div class="dugmeler" style="margin-top:12px"><button type="button" class="btn ana-btn" id="claude-kaydet">Kaydet</button></div>
        <p class="ayar-not" style="margin-top:8px">Değişiklik bundan sonra başlayan işlerde geçerli olur. Yüksek efor ve büyük model daha dikkatli çalışır ama daha uzun sürer ve kullanımından daha çok harcar. Kör eleştirmen her zaman filmi yapan oturumdan ayrı çalışır.</p></section>
      <section><div class="bolum-bas"><h2>Magnific</h2><span>Yapay zekâ ile görsel, video, efekt sesi, 3B ve stok</span></div>
        <div class="profil-kart cam magnific-kart">
          <p><span class="cip ${M.kurulu ? 'yesil' : ''}">${M.kurulu ? 'Bağlı' : 'Bağlı değil'}</span> ${M.kurulu ? `Plan: ${esc((B?.plan || M.plan || 'premium').replace(/^./, (c) => c.toLocaleUpperCase('tr-TR')))}` : ''}</p>
          ${M.kurulu ? `<p class="magnific-bakiye">${B ? `Son bilinen bakiye: <b>${tl(B.kalan)}</b> kredi${B.toplam ? ` / ${tl(B.toplam)}` : ''} <span class="ince">(${esc(gun(B.tarih.slice(0, 10)))} ${esc(B.tarih.slice(11, 16))})</span>` : 'Bakiye henüz okunmadı.'}</p>
            <div class="dugmeler"><button type="button" class="btn cam-btn" id="bakiye-oku" ${G.claudeVar ? '' : 'disabled'}>Bakiyeyi oku</button></div><div id="bakiye-sonuc"></div>`
            : '<p>Bağlı değilken stüdyo her şeyi kendi yollarıyla yapar (çizim, 3B, Blender); yapay zekâ üretimi önerilmez. Bağlamak için Claude Code\'da bir kez Magnific bağlantısı eklenir ve tarayıcıda kendi hesabınla giriş onaylanır (studio/README.md → Magnific).</p>'}
          <label class="alan-et" for="kredi-varsayilan">Yeni filmlerin kredi sınırı<input id="kredi-varsayilan" type="number" inputmode="numeric" min="0" max="240000" step="500" value="${esc(String(G.uretimAyar?.kredi_siniri ?? 20000))}"></label>
          <div class="dugmeler"><button type="button" class="btn ana-btn" id="kredi-varsayilan-kaydet">Kaydet</button></div>
          <p class="ayar-not">Her filmin sınırı yeni film levhasında (Gelişmiş) ve film sayfasında değişir; Claude sınırı aşacaksa durur ve sana sorar. Premium planında yılda 240.000 kredi var, müzik hakkı yok: müzik kodla ya da ACE-Step'le üretilir. Ölçülmüş bedeller: görsel (Nano Banana 2, 2K) 75 · 5 sn video (Kling 2.5, 720p) 140 · 5 sn (Kling 3.0, 1080p) 450 · 4 sn (Veo 3.1, 1080p) 800. Gerçek yararlanıcı, gerçek olay ve gerçek kişi yapay zekâyla üretilmez; gerçekçi insan yalnız ekranda etiketli canlandırmada.</p></div></section>
      <section><div class="bolum-bas"><h2>Anlatıcı sesi</h2><span>Dene, dinle</span></div>
        <div class="profil-kart cam"><label class="alan-et" for="dene-metin">Metin<input id="dene-metin" value="Bir olay, bir harita ve tek bir ders."></label>
          ${G.anlaticiOrnek ? `<div class="kopya-satir" style="align-items:center"><div><b>Magnific · Serkan Yıldırım</b> <span class="ince">doğal erkek ses, yapay zekâ; filmde her cümle bir kez üretilir (~85 karakter 18 kredi)</span><audio src="${dosyaUrl(G.anlaticiOrnek, true)}" controls preload="none" style="width:100%;height:34px"></audio></div></div>` : ''}
          <div class="dugmeler"><button type="button" class="btn cam-btn" data-dene="edge">Yapay sesle (Edge) dene</button><button type="button" class="btn cam-btn" data-dene="opencode" ${G.opencode ? '' : 'disabled title="Önce OpenCode anahtarı"'}>OpenCode ile dene</button></div><div id="dene-sonuc"></div></div></section>
      <section><div class="bolum-bas"><h2>OpenCode anahtarı</h2><span>Deneysel Gemini sesi için</span></div>
        <div class="profil-kart cam"><p>Anahtar yalnız <code>studio/.env</code> dosyasına yazılır, hiçbir yere gönderilmez. <span class="cip ${G.opencode ? 'yesil' : ''}">${G.opencode ? 'Anahtar ayarlı' : 'Anahtar yok'}</span></p>
          <label class="alan-et" for="anahtar">Anahtar<input type="password" id="anahtar" autocomplete="off" placeholder="${G.opencode ? '•••••••• (değiştirmek için yenisini yaz)' : 'OpenCode Console → API key'}"></label>
          <div class="dugmeler"><button type="button" class="btn ana-btn" id="anahtar-kaydet">Kaydet</button>${G.opencode ? '<button type="button" class="btn cam-btn" id="anahtar-sil">Anahtarı sil</button>' : ''}</div></div></section>
      <section><div class="bolum-bas"><h2>Panel</h2><span>Yalnız bu bilgisayarda · http://localhost:4777</span></div>
        <div class="profil-kart cam"><p>Paneli kapatsan da süren işler arka planda devam eder. Yeniden açmak için Youtube klasöründeki <b>Panel.command</b>.</p><div class="dugmeler"><button type="button" class="btn cam-btn" id="panel-kapat">Paneli kapat</button></div></div></section>
    </div>`;
  const S = $('#v-sayfa');
  $$('select[data-model]', S).forEach((s) => s.addEventListener('change', () => { $(`input[data-model-diger="${s.dataset.model}"]`, S).hidden = s.value !== '_diger'; }));
  const oku = (a) => { const s = $(`select[data-model="${a}"]`, S).value; return {model: s === '_diger' ? $(`input[data-model-diger="${a}"]`, S).value.trim() : s, efor: $(`select[data-efor="${a}"]`, S).value}; };
  $('#tumune').addEventListener('click', () => {
    const t = oku('_tumu');
    for (const a of Object.keys(C.asamalar)) {
      const bilinen = t.model === '' || C.modeller[t.model];
      $(`select[data-model="${a}"]`, S).value = bilinen ? t.model : '_diger';
      const i = $(`input[data-model-diger="${a}"]`, S);
      i.value = bilinen ? '' : t.model; i.hidden = !!bilinen;
      $(`select[data-efor="${a}"]`, S).value = t.efor;
    }
    bildir('Tümüne uygulandı; kaydetmeyi unutma.');
  });
  $('#claude-kaydet').addEventListener('click', async () => {
    try { await api.post('/api/claude-ayar', Object.fromEntries(Object.keys(C.asamalar).map((a) => [a, oku(a)]))); bildir('Claude ayarları kaydedildi.'); genelTazele(); } catch (e) { bildir(e.message, 6000); }
  });
  $$('[data-dene]', S).forEach((b) => b.addEventListener('click', async () => {
    const k = b.dataset.dene;
    try {
      const j = await api.post('/api/ses-dene', {kaynak: k, metin: $('#dene-metin').value});
      isIzle(j, (s) => { $('#dene-sonuc').innerHTML = s.durum === 'bitti' ? `<audio src="${dosyaUrl(`studio/out/ses_deneme/${k}.wav`, true)}" controls autoplay style="width:100%"></audio>` : `<div class="hata-kutu">${esc(s.satirlar.slice(-1)[0] || 'hata')}</div>`; });
    } catch (e) { bildir(e.message, 6000); }
  }));
  $('#kredi-varsayilan-kaydet').addEventListener('click', async () => {
    try { await api.post('/api/uretim-ayar', {kredi_siniri: $('#kredi-varsayilan').value}); bildir('Kredi sınırı kaydedildi.'); genelTazele(); } catch (e) { bildir(e.message, 6000); }
  });
  $('#bakiye-oku')?.addEventListener('click', async (e) => {
    const b = e.currentTarget;
    b.disabled = true;
    $('#bakiye-sonuc').innerHTML = '<p class="ince parilti">Kısa bir Claude işi yalnız bakiyeyi okuyor (kredi harcamaz)…</p>';
    try {
      const j = await api.post('/api/magnific/bakiye');
      isIzle(j, (s) => { if (s.durum === 'bitti') SAYFA.ayarlar(); else { $('#bakiye-sonuc').innerHTML = `<div class="hata-kutu">${esc(s.satirlar.slice(-1)[0] || 'Bakiye okunamadı')}</div>`; b.disabled = false; } });
    } catch (er) { bildir(er.message, 6000); b.disabled = false; $('#bakiye-sonuc').innerHTML = ''; }
  });
  $('#anahtar-kaydet').addEventListener('click', async () => {
    const a = $('#anahtar').value.trim();
    if (!a) return bildir('Anahtar boş.');
    try { await api.post('/api/ayar/opencode', {anahtar: a}); bildir('Anahtar kaydedildi.'); SAYFA.ayarlar(); } catch (e) { bildir(e.message, 6000); }
  });
  $('#anahtar-sil')?.addEventListener('click', async () => { await api.post('/api/ayar/opencode', {anahtar: ''}); bildir('Anahtar silindi.'); SAYFA.ayarlar(); });
  $('#panel-kapat').addEventListener('click', async (e) => {
    const n = await onaySor(e.currentTarget, {soru: 'Panel kapatılsın mı? Süren işler arka planda devam eder.', evet: 'Kapat', tehlike: true});
    if (n === null) return;
    try { await api.post('/api/kapat'); } catch (er) { /* kapanırken bağlantı kopabilir */ }
    document.body.innerHTML = '<div style="padding:60px;font-family:-apple-system,system-ui;color:#888"><h1>Panel kapandı</h1><p>Yeniden açmak için Youtube klasöründeki <b>Panel.command</b> dosyasına çift tıkla.</p></div>';
  });
};

// ---------------------------------------------------------------- Yardım ve belge
SAYFA.yardim = async () => {
  $('#v-sayfa').innerHTML = `${ustCubuk('Nasıl çalışır?', 'Bu panel, kod ile film üreten stüdyonun masası. Komut satırı bilmen gerekmez.')}
    <div class="icerik" style="gap:28px">
      <div class="profil-kart cam"><h3>Kısaca</h3><p>Fikrini “Yeni film”e kendi cümlelerinle yazarsın. Claude birbirinden farklı üç yol (üç fikir, her biri kendi kanca karesi ve görünüşüyle) önerir; sen birini seçersin, Claude planı o yolda tamamlar, sen onaylarsın. Claude filmi üretir, kendi filmini ölçer, filmi hiç görmemiş bir eleştirmene gösterir ve en büyük kusurları onarır. Sen filmi izler, onaylarsın; yayınlanacağı yere sen yüklersin.</p>
        <div class="iskelet">${ADIMLAR.map((a, i) => `${i ? ik('sag') : ''}<span>${a.ad}${a.insan ? ' · sen' : ''}</span>`).join('')}</div></div>
      <section><div class="bolum-bas"><h2>Yolun altı adımı</h2><span>Her adım bir kapı; kanıt olmadan kapanmaz</span></div>
        <div class="profil-izgara">${ADIMLAR.map((a) => `<article class="profil-kart cam"><h3>${a.kapi} · ${a.ad}</h3><p>${a.ne}</p><div class="cipler"><span class="cip ${a.insan ? 'turuncu' : ''}">${a.insan ? 'senin onayın' : 'kanıtla kapanır'}</span></div></article>`).join('')}</div></section>
      <section><div class="bolum-bas"><h2>Kim ne yapar?</h2></div><div class="profil-izgara">
        <article class="profil-kart cam"><h3>Sen</h3><p>Fikri ve yönü verirsin. Gerçek dosyaları (logo, kayıt, müzik) yüklersin. Üç yoldan birini seçer, planı ve filmi onaylarsın. Filmi yayınlanacağı yere sen yüklersin.</p></article>
        <article class="profil-kart cam"><h3>Claude</h3><p>Brief'i, kaynakları, senaryoyu ve sahne kodunu yazar; sesi tasarlar; incelemede en büyük kusurları bulur ve onarır. Çalışma alanının altındaki “Claude'a söyle” alanına yazdığın her şey ona gider.</p></article>
        <article class="profil-kart cam"><h3>Panel</h3><p>Sesi üretir, kareleri ve filmi render eder, ölçer, kanıtı gösterir. Uzun işler sağ altta canlı görünür; pencereyi kapatsan da sürer.</p></article></div></section>
      <section><div class="bolum-bas"><h2>Sözlük</h2></div><div class="profil-kart cam">${md(`- **Film türü (profil):** filmin türü ve çıtaları: süre, kanca, tempo, ses yüksekliği. Ör. \`dikey-anlatim\`, \`reklam-kisa\`. Türün vuruş iskeleti yalnız bir öneridir: hikâyenin iskeletini film kendisi kurabilir.
- **Esin ve aynen:** katalog kartları esin kaynağıdır. Kart seçmezsen Claude görünüşü, hareketi ve sesi bu filme özel icat eder; kart seçersen onlardan yola çıkar, karıştırır ve aşar. Kartın birebir uygulanmasını istersen tek kart seçip “Aynen uygula” dersin. “Kendin anlat” ile kendi tarifini ve referansını eklersin; tarif kartlarla çelişirse tarif kazanır.
- **Cesaret:** Sağlam, Cesur ya da Sınırsız. Claude'un ne kadar beklenmedik bir film kuracağını sen seçersin; her filmde ayrıca filmi zorlayan tek bir üretim kuralı olur (ör. tek plan, yalnız gölgeyle).
- **Üç yol:** planda Claude önce bir fikir havuzu çıkarır, sonra yöntem olarak birbirinden farklı üç yol önerir (ör. tek bir pencereden, hava durumu bülteni gibi, bir damlanın yolculuğu). Her yolun kendi kanca karesi, üretim kuralı ve görünüşü vardır; sen seçersin, Claude planı o yolda tamamlar. İstersen “Başka üç yol öner” ya da seçtiğin yolda başka görünüşler istersin.
- **Görünüş:** renk, yazı, doku, ışık. Her filme özeldir; yolun içinde gelir. Birkaç filmin paylaştığı görünüşe **seri** denir.
- **Dört seçim birbirinden bağımsızdır:** motor, görüntü stili, hareket ve ses. Hiçbiri ötekini seçmez; her birleşim olur, Claude seçtiğin birleşimi filme uyarlar. Katalogdaki örnekler yalnız tekniği gösterir, filmin dünyası senin isteğinden gelir.
- **Motor:** kareyi çizen araç; tarz değil. Remotion (React: yazı, veri, harita, arayüz, SVG illüstrasyon), HyperFrames (HTML ve GSAP: karakter, çizgi film, kampanya) ya da Blender (gerçek 3B: ışık, malzeme, kamera; ürün, mimari, soyut, maket, çizgi film boyası; çizimi uzun sürer, yazı ve logo Remotion'la üstüne konur).
- **3B katman:** ayrı bir motor değil; Remotion'un ve HyperFrames'in içinde Three.js ile çizilen üç boyutlu sahne (Blender zaten 3B'dir): gerçek coğrafyalı dünya küresi, ışıkta dönen ürün ya da telefon, derinlikli bilgi grafiği, akan parçacık ve ışık alanları. Blender'dan çok daha hızlıdır (saniyeler) ve yazıyla, veriyle aynı sahnede durur. Kareler bilgisayarın işlemcisiyle çizilir, böylece her çizim bayt bayt aynı çıkar. Stil kataloğunda “Dünya küresi”, “3B ürün / nesne” ve “Parçacık / shader alanı” olarak seçilir.
- **Marka kiti:** bir kurumun resmi logosu, renkleri ve ton kuralları (ör. İHH).
- **Format:** en-boy oranı. 9:16 dikey, 16:9 yatay, 1:1 kare, 4:5 portre. Her format ayrı kurulur, kırpılmaz.
- **Vuruş:** filmin bir adımı (ör. Kanca, Doruk, Kapanış). Anlatımlı filmde bir cümle.
- **İşaret:** bir olayın zamanı; bir kelimeye, müzik vuruşuna ya da saniyeye bağlanır. Görüntü ve ses aynı işaretten zamanlanır.
- **Kontak tabakası:** filmin her vuruşundan bir kareyi tek görselde gösteren inceleme sayfası.
- **Kör eleştiri:** filmi hiç görmemiş bir Claude oturumunun yalnız karelere ve ölçüme bakarak yazdığı eleştiri.
- **Ölçüm:** çıtaların sayıyla denetimi. Kaydırmayı durduran şeylere de bakar: ilk saniyelerde mesaj var mı, ilk karede ses var mı, dikey film döngüye girebilir mi, film önceki filmlere ya da katalog kartlarına fazla benziyor mu. Bunlar uyarıdır, yasak değil. Temiz ölçüm iyi film demek değildir: zanaatı denetler, etkiyi değil.`)}</div></section>
      <section><div class="bolum-bas"><h2>Yapay zekâ, kredi ve etik</h2><span>Magnific yalnız bağlıysa · bağlı değilse panel bu seçenekleri gizler</span></div><div class="profil-izgara">
        <article class="profil-kart cam"><h3>Magnific ve kredi</h3><p>Magnific bağlıysa Claude gerçekçi bir mekân, nesne, doku ya da metafor için görsel ya da kısa klip üretebilir; anlatıcı olarak Magnific'in sesi (Serkan) seçilebilir. Her üretim bir kez indirilir ve dondurulur: film her çizimde aynı dosyayı kullanır. Her filmin bir kredi sınırı var (varsayılan 20 000; Ayarlar'da ve Yeni film → Gelişmiş'te). Sınırı aşacak üretimde Claude durur ve sana sorar; harcanan kredi film sayfasının üstünde görünür. Müzik Magnific'ten üretilmez. Magnific bağlı değilse stüdyo her şeyi kendi yollarıyla yapar.</p></article>
        <article class="profil-kart cam"><h3>Etik çizgi</h3><p>Gerçek bir yararlanıcı, gerçek bir olay ya da belgesel görünümlü acı yapay zekâyla üretilmez; gerçek bir kişinin yapay zekâ kopyası yapılmaz. Gerçekçi bir yapay zekâ insanı yalnız ekranda etiketli bir canlandırmada kullanılır (“Canlandırmadır”, “Yapay zekâ ile üretilmiştir”). Yapay zekâ ürünü olan filmin yayın paketine beyan yazılır.</p></article>
        <article class="profil-kart cam"><h3>Gerçek görüntü</h3><p>Kendi çekimini, kurumun arşivini ya da açık lisanslı bir görüntüyü Plan → Gerçek görüntü'den eklersin. Kişi ve rıza senin kararın: istersen yüzleri gizler, görüntüyü stilize eder ya da hiç kullanmayız; seçersen ölçüm buna uyulduğunu denetler. Gerçek görüntü yapay zekâya verilmez; stilizasyon kodla, kare kare yapılır.</p></article></div></section>
      <section><div class="bolum-bas"><h2>Altyazı ve Blender'ın çizeri</h2><span>Yeni film levhasında, örnekleriyle</span></div><div class="profil-izgara">
        <article class="profil-kart cam"><h3>Niyetli altyazı</h3><p>Altyazı: Niyetli seçilirse yazı sesi gösterir: vurgulu kelime kalınlaşır ve büyür, sesin perdesi yazının genişliğini değiştirir, her konuşmacı kendi renginde. Bütün kelimeler telefonda okunacak büyüklükte kalır. Anlatımlı filmde seçilir; Klasik varsayılandır.</p></article>
        <article class="profil-kart cam"><h3>Cycles ya da EEVEE</h3><p>Motor olarak Blender seçilince çizeri de seçersin. Cycles gerçek ışıkla çizer (ışık geçiren bez, cam, yumuşak gölge) ama uzun sürer: 30 saniyelik film birkaç saat. EEVEE yaklaşık 6 kat hızlıdır; stilize, çizgi film, kil ve düşük poligon sahnelere uyar, bezin içinden dışarı düşen gölgeyi çizemez. Seçmezsen Claude seçer ve nedenini söyler.</p></article></div></section>
      <section><div class="bolum-bas"><h2>Veriyle ve kişiye özel filmler</h2><span>Claude'a söyle ya da fikrine yaz</span></div><div class="profil-izgara">
        <article class="profil-kart cam"><h3>Canlı veri</h3><p>Gerçek ve güncel bir veriyle çizilen film (ör. “bu gece kamplarda sıcaklık”). Kaynak açık ve lisansı kurum kampanyasına izin verir (hazır kaynak: MET Norway hava tahmini; atıf şart). Konumu sen seçersin, şehir düzeyinde. Plan → Canlı veri'de son görüntü, değerler, atıf ve lisans durur; “Veriyi yenile” yeni bir anlık görüntü alır (kaynağın kuralı: aynı yere en çok 10 dakikada bir), listeden “Bununla çiz” ile istediğin görüntüyü seçersin. Ekrandaki rakam elle yazılmaz; ölçüm onu filmin kendisinden okuyarak denetler. Atıf yayın paketine yazılır; ekranda atıf yalnız sen istersen.</p></article>
        <article class="profil-kart cam"><h3>Kişisel etki filmi</h3><p>Onaylanmış bir şablon filmden listedeki her kişiye kendi adı ve verisiyle bir film (ör. bağışçıya: adı, bağışının gittiği yer, etkisi). Teslim → Kişisel filmler: listeyi yükle (CSV ya da JSON), sütunları eşle, ilk satırın önizlemesine bak, başlat. Eksik ya da hatalı satır atlanır ve nedeni yazılır; hiçbir alan uydurulmaz. Her filmin yazıları kendi videosundan okunarak denetlenir. İstersen kurum verisi notlarını (kaynak, izin, ekranda görünecekler, gönderim, saklama) yazarsın; yayın paketine girer. Liste ve filmler bu bilgisayarda kalır: panelin Claude'una, Magnific'e ve pakete gitmez.</p></article></div></section>
      <section><div class="bolum-bas"><h2>Teslimden sonra</h2><span>Teslim adımında</span></div><div class="profil-izgara">
        <article class="profil-kart cam"><h3>Nasıl yapıldı filmi</h3><p>15 saniyelik bir kamera arkası, yalnız filmin kendi kayıtlarından: üç yol ve seçilen, kutularıyla iskelet (Blender'da kil → tel kafes → kamera yolu), inceleme turunda önce ve sonra, yapay zekâ varlığının kaynağı, altı kapı ve onayların. Kaydı olmayan bölüm girmez; henüz onaylamadığın kapı “İnsan onayı bekliyor” yazar. Kredi harcamaz; video cikti/ klasörüne gelir. Panel filmin ilk formatında çizer.</p></article>
        <article class="profil-kart cam"><h3>Yayın sonrası rapor</h3><p>Film yayınlandıktan sonra (ör. 48 saat, 7 gün) platformun verisini yüklersin: CSV, ekran görüntüsü, PDF ya da elle sayılar. Claude izleyicinin koptuğu anları karelere çevirir, ölçüm ve eleştiriyle karşılaştırır, bir rapor yazar. Değişiklik yalnız önerir; uygulamak senin onayınla. Yayından iki gün sonra bir kez hatırlatır.</p></article>
        <article class="profil-kart cam"><h3>Kataloğa ekle</h3><p>Beğendiğin bir filmin dilini (görünüş, hareket ya da ses) ⋯ menüsünden “Bu filmin dilini kataloğa ekle” ile karta çevirebilirsin. Claude taslağı yazar; Kütüphane'de onaylarsan katalogda esin kartı olarak görünür.</p></article></div></section>
      <section><div class="bolum-bas"><h2>Geçişler ve karma film</h2><span>Kütüphane → Geçişler · Senaryo adımı</span></div><div class="profil-izgara">
        <article class="profil-kart cam"><h3>Gölgelendirici geçişleri</h3><p>Sahneler arasında 184 hazır geçiş: sayfa çevirme, mürekkep, su, odak kayması, perde… Kütüphane → Geçişler'de her birinin kısa önizlemesi var (üstüne gelince oynar). Düz kesim varsayılandır; geçişi Claude senaryoda yalnız anlam taşıdığı yerde seçer ve nedenini yazar. Değiştirmek istersen “Claude'a söyle” yeter (ör. “ikinci kesimde InkBleed olsun”). Yazı ve altyazı geçişin üstünde kalır, bükülmez; filmin süresi değişmez.</p></article>
        <article class="profil-kart cam"><h3>Karma film: sahne başına motor</h3><p>Bir filmin her sahnesi içeriğine en uygun araçla çizilebilir: yazı ve veri Remotion'da, çizgi film karakteri HyperFrames'te, gerçek ışıklı nesne Blender'da, formül ve grafik Manim'de; hepsi aynı renk ve yazıyla tek filmde birleşir. Tek araçlı film varsayılandır; Claude karma filmi yalnız içerik gerektiriyorsa önerir ve hangi sahnenin hangi araçla neden çizildiğini Plan'da yazar. Senaryo adımında her vuruşun yanında aracı görünür.</p></article>
        <article class="profil-kart cam"><h3>Manim (isteğe bağlı)</h3><p>Formül ve grafik sahneleri için Manim bu Mac'te kurulu. Matematik dizgisi için LaTeX kurulmadı: istersen kendin kurarsın (yönetici parolası ister); kurulmadan formüller Typst ve normal yazıyla çizilir. Başka bir Mac'e giden kurulumda Manim kendiliğinden kurulmaz.</p></article></div></section>
      <section><div class="bolum-bas"><h2>Gerçek yerde imkânsız nesne (kamera takibi)</h2><span>Blender filminde · Plan → Kamera takibi</span></div><div class="profil-izgara">
        <article class="profil-kart cam"><h3>Ne yapar?</h3><p>Telefonla çektiğin gerçek bir yere bilgisayarla çizilmiş bir nesne yerleşir: yolun ortasında süzülen dev bir kumbara, meydanda kocaman bir ekmek. Blender çekimdeki noktaları izler, kameranın nasıl yürüdüğünü, zemini ve ölçeği bulur. Bu çözüm bir kez dondurulur; nesne her karede aynı yerde durur, gölgesi zemine düşer.</p></article>
        <article class="profil-kart cam"><h3>Nasıl çekmeli?</h3>${TAKIP_REHBER}</article>
        <article class="profil-kart cam"><h3>Neye bakmalı?</h3><p>Çözüm hatası 1 pikselin altında olmalı (yeşil). Önizlemedeki mavi ızgara zemindeki 1 metrelik karelerdir: yürürken yere yapışık kalmalı, kareler yolda gerçekten bir metre görünmeli; görünmüyorsa telefonun yerden yüksekliğini değiştir. “Nesneyle dört kare çiz” ile nesneyi çekimin üstünde gör: kaymamalı, gölgesi zemine oturmalı.</p></article>
        <article class="profil-kart cam"><h3>Otomatik iz yetmezse</h3>${TAKIP_ELLE}</article></div></section>
      <section><div class="bolum-bas"><h2>Belgeler</h2></div><div class="dugmeler">${[['CLAUDE.md', 'Stüdyo kılavuzu'], ['studio/README.md', 'Komutlar'], ['studio/zanaat.md', 'Zanaat kuralları'], ['kanal/ogrenimler.md', 'Öğrenimler (ham)'], ['kanal/youtube.md', 'YouTube yükleme listesi']]
        .map(([y, a]) => `<a class="btn cam-btn" href="#/belge?yol=${encodeURIComponent(y)}">${ik('dosya')}${a}</a>`).join('')}</div></section>
    </div>`;
};
SAYFA.belge = async (p, q) => {
  const yol = q.get('yol') || '';
  const b = await api.get(`/api/belge?yol=${encodeURIComponent(yol)}`);
  $('#v-sayfa').innerHTML = `${ustCubuk(esc(yol.split('/').pop()), esc(yol), '<button type="button" class="btn cam-btn" onclick="history.back()">Geri</button>')}<div class="icerik"><div class="profil-kart cam" style="max-width:860px">${md(b.metin)}</div></div>`;
};
