import React from 'react';
import {fontYukle} from './fontlar';
import {useFormat} from './format';
import {gecisPlakasi} from './gecis/plaka';

/**
 * Yapay zekâ etiketi (zanaat §9, CLAUDE.md kural 2): gerçekçi yapay zekâ insanı yalnız ekranda etiketli canlandırmada kullanılır.
 * Etiket gerektiren üretim varlığının (videos/<id>/uretim/uretim.json → etiket_gerekli) göründüğü her vuruşta bulunur ve
 * script.json → etiketler [{vurus, metin, varlik}] ile işaretlenir; ölçüm ("Yapay zekâ etiketi") ikisini karşılaştırır.
 * Okunur: 1080 kısa kenarda 64 px, koyu zemin üstünde beyaz (her arka planda ≥ 4,5:1), formatın güvenli alanında, durağan
 * (beyan okunmak içindir: hareket etmez, belirip kaybolmaz; vuruşun ilk karesinden sonuna kadar).
 */
export const ETIKET_METINLERI = ['Canlandırmadır', 'Temsilîdir', 'Yapay zekâ ile üretilmiştir'] as const;
export type EtiketKonumu = 'ust-sol' | 'ust-sag' | 'alt-sol' | 'alt-sag';

const VARSAYILAN_FONT = fontYukle('Inter', [600]);

export const Etiket: React.FC<{metin?: string; konum?: EtiketKonumu; font?: string}> = ({
  metin = 'Yapay zekâ ile üretilmiştir',
  konum = 'ust-sol',
  font = VARSAYILAN_FONT,
}) => {
  const {safe, unit, w, h} = useFormat();
  if (gecisPlakasi()) return null; // geçiş plakasında etiket yok: asıl çizimde geçişin üstünde, durağan
  const pay = 24 * unit;
  return (
    <div
      style={{
        position: 'absolute',
        ...(konum.startsWith('ust') ? {top: safe.top + pay} : {bottom: h - safe.bottom + pay}),
        ...(konum.endsWith('sol') ? {left: safe.left + pay} : {right: w - safe.right + pay}),
        maxWidth: safe.right - safe.left - 2 * pay,
        padding: `${14 * unit}px ${26 * unit}px`,
        borderRadius: 18 * unit,
        background: 'rgba(12,12,14,0.78)',
        color: '#FFFFFF',
        fontFamily: font,
        fontWeight: 600,
        fontSize: 64 * unit,
        lineHeight: 1.12,
        letterSpacing: 0,
      }}
    >
      {metin}
    </div>
  );
};
