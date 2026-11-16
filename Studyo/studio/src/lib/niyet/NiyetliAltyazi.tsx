import React from 'react';
import {AbsoluteFill} from 'remotion';
import {degiskenFontYukle} from '../fontlar';
import {useFormat} from '../format';
import {type NiyetVeri, altyaziHali} from './cekirdek';
import {gecisPlakasi} from '../gecis/plaka';

/**
 * Niyetli altyazı (Remotion): kelimenin şiddeti ağırlığına ve boyutuna, perdesi genişliğine bağlı; konuşmacıya göre renk.
 * Veri timeline.json → niyet (./st ses ya da ./st niyet <id>); script.json → "altyazi": "niyetli". Sayfa ve satırlar formatın
 * güvenli alanında önceden kurulu; yazı ≥ 64 px, satır plakası kontrastı korur. Ortak Captions'ın yerine, Bitis'in dışında kullan:
 *   <NiyetliAltyazi t={t} veri={timeline.niyet} />
 * HyperFrames karşılığı: niyetliAltyazi(kok) (assets/lib/niyet/niyet.js; hf/CLAUDE.md → Niyetli altyazı).
 */
export const NiyetliAltyazi: React.FC<{t: number; veri?: NiyetVeri | null}> = ({t, veri}) => {
  const {key, h} = useFormat();
  if (gecisPlakasi()) return null; // geçiş plakasında altyazı yok: asıl çizimde geçişin üstünde
  // veri yoksa (./st ses henüz çalışmadı) sahne altyazısız çizilir; ölçüm ve ./st tip bunu söyler
  if (!veri) return null;
  const aile = degiskenFontYukle(veri.yazi.aile as 'Roboto Flex');
  const A = altyaziHali(veri, key, t);
  if (!A) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{
        position: 'absolute', left: A.merkez - A.kutu.w / 2, width: A.kutu.w, bottom: h - A.kutu.alt,  // sayfa karenin ekseninde, güvenli alanda (niyet.py)
        display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: A.opaklik, transform: `translateY(${A.kayma}px)`,
      }}>
        {A.satirlar.map((s, n) => (
          <div key={n} lang="tr" style={{
            fontFamily: `'${aile}', sans-serif`, fontSize: s.boyut, lineHeight: 1.12, whiteSpace: 'pre', width: 'max-content',
            padding: `${A.pad[1]}em ${A.pad[0]}em`, background: A.zemin, borderRadius: '0.16em',
            marginTop: n ? `${A.satirAra}em` : 0, fontKerning: 'normal', fontOpticalSizing: 'none',
          }}>
            {s.kelimeler.map((k, j) => (
              <React.Fragment key={j}>
                <span style={{display: 'inline-block', fontSize: k.boyut, fontVariationSettings: k.ayar, color: k.renk, transform: `translateY(${k.kalkis}px)`}}>
                  {k.metin}
                </span>
                {k.bosluk ? <span style={{fontSize: k.boslukBoyut, fontVariationSettings: k.bosluk}}> </span> : null}
              </React.Fragment>
            ))}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
