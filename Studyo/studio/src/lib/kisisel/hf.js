// Kişisel etki filmi, HyperFrames karşılığı (src/lib/kisisel/index.tsx ile aynı kurallar). pipeline/hf.py bu dosyayı
// hf/<id>/assets/lib/kisisel/kisi.js olarak kopyalar (derleme yok; düz betik: GSAP zaman çizelgesi aynı betikte kurulur).
// Veri window.ST.kisi: şablonun TEST örneği ya da ./st toplu'nun satırı. Ekrandaki her yazı ST.kisi'den; ad ve uzun yazılar Python'da
// sığdırılmış satırlarla (tarayıcı bölmez, en küçük 64 px).
//   <script src="assets/lib/kisisel/kisi.js"></script>
//   const satirlar = Kisi.yazi(document.getElementById("ad"), "ad");   // her satır bir <div class="kisi-satir">: GSAP ile sırayla gelebilir
//   Kisi.test(document.getElementById("root"));                         // TEST satırında plaka (her karede, güvenli alanın üstünde)
// Yazı tipi (Roboto Flex) st-gorunus'taki @font-face'ten; HyperFrames ilk çizimi yazı tipi inene kadar bekler (__hf.buildReady).
(function () {
  const W = window;
  const hf = (W.__hf = W.__hf || {});
  (hf.buildReady = hf.buildReady || {})['kisi-yazi'] = Promise.all(['ığşİ', 'ÇÖÜĞ'].map((m) => document.fonts.load("800 64px 'Roboto Flex'", m)));

  /** Roboto Flex'in biçimi (ölçü tablosuyla aynı eksenler, opsz 32). */
  const degiskenYazi = (el, boyut, wght, wdth = 100, satirYuksekligi = 1.1, opsz = 32) => {
    Object.assign(el.style, {fontFamily: "'Roboto Flex', sans-serif", fontSize: `${boyut}px`, lineHeight: String(satirYuksekligi),
      fontVariationSettings: `'wght' ${wght}, 'wdth' ${wdth}, 'opsz' ${opsz}, 'GRAD' 0`, letterSpacing: '0'});
    return el;
  };

  /** Alanın sığdırılmış yazısını el'e çizer (bu formatın satırları); satır öğelerini döndürür. */
  const yazi = (el, alan, renk) => {
    const K = W.ST && W.ST.kisi;
    const Y = K && K.yerlesim && K.yerlesim[alan] && K.yerlesim[alan][W.ST.format];
    if (!Y) throw new Error(`Kisi.yazi: ${alan} alanının ${W.ST && W.ST.format} yerleşimi yok (veri_sablonu.json → yazi.${alan})`);
    degiskenYazi(el, Y.boyut, Y.wght, Y.wdth, Y.satir_yuksekligi, Y.opsz);
    Object.assign(el.style, {whiteSpace: 'pre', width: `${Y.genislik}px`, textAlign: Y.hiza === 'orta' ? 'center' : 'left'});
    if (renk) el.style.color = renk;
    el.replaceChildren(...Y.satirlar.map((s) => {
      const d = document.createElement('div');
      d.className = 'kisi-satir';
      d.textContent = s;
      return d;
    }));
    return [...el.children];
  };

  /** Sayı + birim ("1.250 aile"); sayı her zaman Python'un metni. */
  const sayisi = (a) => (a.birim ? `${a.sayi || a.metin} ${a.birim}` : a.metin);

  /** TEST satırında plaka (sınıf .kisi-test: ./st yazar, st-gorunus; 40 px, koyu kırmızı üstünde beyaz, güvenli alanda). Gerçek veride yok. */
  const test = (kok) => {
    if (!(W.ST && W.ST.kisi && W.ST.kisi.test) || !kok) return null;
    const d = document.createElement('div');
    d.className = 'kisi-test';
    d.textContent = 'TEST · gerçek kişi değil';
    kok.appendChild(d);
    return d;
  };

  W.Kisi = {yazi, degiskenYazi, sayisi, test};
})();
