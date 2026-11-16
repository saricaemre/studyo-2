import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, getInputProps, staticFile} from 'remotion';
import {degiskenFontYukle, fontYukle} from '../fontlar';
import {useFormat} from '../format';
import {gecisPlakasi} from '../gecis/plaka';

/**
 * Kişisel etki filmi (./st toplu, pipeline/kisisel.py): bir şablon filmden her satıra (her bağışçıya) kendi verisiyle film.
 * Kare t'nin ve kişi verisinin saf fonksiyonudur; çizimde ağ yok.
 * - ./st ile çizimde veri Remotion girdisidir (props.kisi): şablonun kendi kareleri (inceleme, temsilî, teslim) TEST örneğiyle,
 *   ./st toplu her satırın verisiyle. Ekrandaki her yazı `metin`dir (Python'da biçimlenir: Türkçe büyük harf, binlik nokta); sahne kodu
 *   yeniden biçimlemez, değer elle yazmaz.
 * - Ad ve uzun yazılar Python'da sığdırılır (yerlesim: satırlar, boyut, genişlik ekseni): tarayıcı satır bölmez, en küçük 64 px.
 * - Remotion Studio'da girdi yoksa şablonun TEST örneği okunur (public/<film>/kisisel/ornek.json; kişisel veri değil).
 * Canlı veriden (src/lib/veri, props.veri) ayrıdır: ikisi aynı filmde birlikte olabilir. HyperFrames karşılığı ./hf.js (window.Kisi).
 */
export type KisiAlan = {ad: string; tur: 'ad' | 'metin' | 'secim' | 'sayi' | 'para' | 'tarih'; deger: string | number; metin: string; sayi?: string; birim?: string};
export type KisiYerlesim = {
  satirlar: string[];
  boyut: number;
  wght: number;
  wdth: number;
  opsz: number;
  satir_yuksekligi: number;
  genislik: number;
  yukseklik: number;
  hiza: 'sol' | 'orta';
};
export type Kisi = {
  surum: number;
  film: string;
  kimlik: string;
  test: boolean;
  dil: string;
  alanlar: Record<string, KisiAlan>;
  yerlesim: Record<string, Record<string, KisiYerlesim>>;
};

const onbellek = new Map<string, Kisi>();

/** Kişi verisi; Studio'da şablonun TEST örneği yüklenene kadar null (render bekletilir). `const K = useKisi('<id>'); if (!K) return null;` */
export const useKisi = (film: string): Kisi | null => {
  const girdi = (getInputProps() as {kisi?: Kisi}).kisi;
  const hazir = girdi && girdi.film === film ? girdi : onbellek.get(film) ?? null;
  const [kisi, setKisi] = useState<Kisi | null>(hazir);
  const [tutamak] = useState(() => (hazir ? null : delayRender(`kişisel film: ${film}/kisisel/ornek.json`)));
  useEffect(() => {
    if (kisi || tutamak === null) return;
    fetch(staticFile(`${film}/kisisel/ornek.json`))
      .then((r) => {
        if (!r.ok) throw new Error(`Şablon örneği yok: public/${film}/kisisel/ornek.json (./st toplu ${film} sablon)`);
        return r.json();
      })
      .then((j: Kisi) => {
        onbellek.set(film, j);
        setKisi(j);
        continueRender(tutamak);
      })
      .catch((e) => cancelRender(e));
  }, [film, kisi, tutamak]);
  return girdi && girdi.film === film ? girdi : kisi;
};

/** Roboto Flex (verinin yazısı): font-variation-settings ölçü tablosuyla aynı eksenlerde (opsz 32). Sabit boyutlu sayı ve birim için de. */
export const degiskenYazi = (boyut: number, wght: number, wdth = 100, satirYuksekligi = 1.1, opsz = 32): React.CSSProperties => ({
  fontFamily: `'${degiskenFontYukle('Roboto Flex')}', sans-serif`,
  fontSize: boyut,
  lineHeight: satirYuksekligi,
  fontVariationSettings: `'wght' ${wght}, 'wdth' ${wdth}, 'opsz' ${opsz}, 'GRAD' 0`,
  letterSpacing: 0,
});

/** Sığdırılmış yazının biçimi (Python'un yerleşimi: boyut, ağırlık, genişlik ekseni, satır yüksekliği, hiza). */
export const kisiYaziStili = (Y: KisiYerlesim): React.CSSProperties => ({
  ...degiskenYazi(Y.boyut, Y.wght, Y.wdth, Y.satir_yuksekligi, Y.opsz),
  whiteSpace: 'pre',
  textAlign: Y.hiza === 'orta' ? 'center' : 'left',
});

/**
 * Bir alanın sığdırılmış yazısı (ad, kalem, bölge …): Python'un kurduğu satırlar, boyut ve genişlik ekseni bu formatta. Kutunun genişliği
 * şablonun genişliğidir (yerlesim.genislik); satırlar tarayıcıda bölünmez. `satir(i)` satır başına stil (giriş hareketi) verir.
 */
export const KisiYazi: React.FC<{kisi: Kisi; alan: string; renk: string; style?: React.CSSProperties; satir?: (i: number) => React.CSSProperties}> = ({
  kisi,
  alan,
  renk,
  style,
  satir,
}) => {
  const {key} = useFormat();
  const Y = kisi.yerlesim[alan]?.[key];
  if (!Y) throw new Error(`Kişisel film: ${alan} alanının ${key} yerleşimi yok (veri_sablonu.json → yazi.${alan})`);
  return (
    <div style={{width: Y.genislik, color: renk, ...kisiYaziStili(Y), ...style}}>
      {Y.satirlar.map((s, i) => (
        <div key={i} style={{...satir?.(i)}}>
          {s}
        </div>
      ))}
    </div>
  );
};

/** Sayı + birim ("1.250 aile"); sayı her zaman Python'un metni. */
export const kisiSayisi = (a: KisiAlan): string => (a.birim ? `${a.sayi ?? a.metin} ${a.birim}` : a.metin);

const PLAKA_FONT = fontYukle('Inter', [600]);

/**
 * TEST plakası: TEST satırının (sahte veri) filmi gerçek sanılmasın diye her karede, güvenli alanın üstünde. Gerçek veride çizilmez.
 * Okunur: 1080 kısa kenarda 40 px, koyu kırmızı zemin üstünde beyaz (≥ 4,5:1). Ölçüm yazı tanımayla "TEST"i arar.
 */
export const KisiTest: React.FC<{kisi: Kisi; konum?: 'ust' | 'alt'}> = ({kisi, konum = 'ust'}) => {
  const {safe, unit, h} = useFormat();
  if (!kisi.test || gecisPlakasi()) return null;
  const pay = 24 * unit;
  return (
    <div
      style={{
        position: 'absolute',
        ...(konum === 'ust' ? {top: safe.top + pay} : {bottom: h - safe.bottom + pay}),
        left: safe.left + pay,
        padding: `${8 * unit}px ${20 * unit}px`,
        borderRadius: 12 * unit,
        background: '#8E1B1B',
        color: '#FFFFFF',
        fontFamily: PLAKA_FONT,
        fontWeight: 600,
        fontSize: 40 * unit,
        lineHeight: 1.2,
        letterSpacing: 0,
      }}
    >
      TEST · gerçek kişi değil
    </div>
  );
};
