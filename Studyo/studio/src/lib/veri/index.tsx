import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, getInputProps, staticFile} from 'remotion';
import {fontYukle} from '../fontlar';
import {useFormat} from '../format';
import {gecisPlakasi} from '../gecis/plaka';

/**
 * Canlı veri (./st veri, pipeline/veri.py): gerçek ve güncel bir kaynaktan dondurulmuş anlık görüntü. Kare t'nin saf fonksiyonu kalır:
 * çizim sırasında ağ yok, film yalnız seçili görüntünün çizim verisini okur.
 * - ./st ile çizimde veri Remotion girdisidir (props.veri; render_frames, npx remotion render --props). Görüntü değişince yalnız bu filmin
 *   kareleri değişir.
 * - Remotion Studio'da girdi yoksa seçili görüntünün motor kopyası okunur (public/<film>/veri/anlik.json, ./st veri cek|sec yazar).
 * Ekrandaki sayı her zaman `metin`dir (Python'da biçimlenir: Türkçe ondalık virgül, eksi U+2212); sahne kodu sayıyı yeniden biçimlemez ve
 * değeri elle yazmaz (ölçüm: "Ekrandaki rakamlar dondurulmuş veriyle aynı", yazı tanıma ile).
 */
export type VeriDegeri = {ad: string; deger: number; metin: string; birim: string; zaman_yerel?: string; pencere?: string};
export type AnlikVeri = {
  surum: number;
  film: string;
  kimlik: string;
  sha: string;
  zaman: string;
  zaman_yerel: string;
  tur: 'tahmin' | 'olcum' | 'istatistik';
  tur_ad: string;
  konum: string;
  kaynak: string;
  atif: string;
  atif_kisa: string;
  lisans: string;
  ekranda: boolean;
  degerler: Record<string, VeriDegeri>;
};

const onbellek = new Map<string, AnlikVeri>();

/** Seçili anlık görüntü; Studio'da yüklenene kadar null (render bekletilir). `const V = useVeri('<id>'); if (!V) return null;` */
export const useVeri = (film: string): AnlikVeri | null => {
  const girdi = (getInputProps() as {veri?: AnlikVeri}).veri;
  const hazir = girdi && girdi.film === film ? girdi : onbellek.get(film) ?? null;
  const [veri, setVeri] = useState<AnlikVeri | null>(hazir);
  const [tutamak] = useState(() => (hazir ? null : delayRender(`canlı veri: ${film}/veri/anlik.json`)));
  useEffect(() => {
    if (veri || tutamak === null) return;
    fetch(staticFile(`${film}/veri/anlik.json`))
      .then((r) => {
        if (!r.ok) throw new Error(`Canlı veri yok: public/${film}/veri/anlik.json (./st veri ${film} cek)`);
        return r.json();
      })
      .then((j: AnlikVeri) => {
        onbellek.set(film, j);
        setVeri(j);
        continueRender(tutamak);
      })
      .catch((e) => cancelRender(e));
  }, [film, veri, tutamak]);
  return girdi && girdi.film === film ? girdi : veri;
};

/** Değer + birim ("8 °C"); birim "%" ise boşluksuz. */
export const veriMetni = (d: VeriDegeri, birim = true): string => (birim && d.birim ? `${d.metin}${d.birim === '%' ? '' : ' '}${d.birim}` : d.metin);

const VARSAYILAN_FONT = fontYukle('Inter', [500]);

/**
 * Ekranda atıf (lisans gereği; veri.json → ekranda): iki satır, "Veri: MET Norway · CC BY 4.0" ve "tahmin · 26 Ekim 2026 22:00".
 * Okunur: 1080 kısa kenarda 40 px, koyu zemin üstünde beyaz (≥ 4,5:1), formatın güvenli alanında, durağan (değerin göründüğü her anda).
 * HyperFrames karşılığı: <div class="veri-atif"> (pipeline/hf.py → veri_css).
 */
export const VeriAtif: React.FC<{veri: AnlikVeri; konum?: 'alt' | 'ust'; font?: string; zaman?: boolean}> = ({
  veri,
  konum = 'alt',
  font = VARSAYILAN_FONT,
  zaman = true,
}) => {
  const {safe, unit, h} = useFormat();
  if (gecisPlakasi()) return null; // geçiş plakasında atıf yok: asıl çizimde geçişin üstünde
  const pay = 24 * unit;
  return (
    <div
      style={{
        position: 'absolute',
        ...(konum === 'ust' ? {top: safe.top + pay} : {bottom: h - safe.bottom + pay}),
        left: safe.left + pay,
        maxWidth: safe.right - safe.left - 2 * pay,
        padding: `${10 * unit}px ${22 * unit}px`,
        borderRadius: 14 * unit,
        background: 'rgba(12,12,14,0.80)',
        color: '#FFFFFF',
        fontFamily: font,
        fontWeight: 500,
        fontSize: 40 * unit,
        lineHeight: 1.2,
        letterSpacing: 0,
      }}
    >
      <div>{veri.atif_kisa}</div>
      {zaman && <div>{`${veri.tur_ad} · ${veri.zaman_yerel}`}</div>}
    </div>
  );
};
