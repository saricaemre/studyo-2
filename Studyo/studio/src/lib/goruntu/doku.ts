// Kare dokusu (<Sahne3B> içinde): görsel ya da video karesi. Yüklenene kadar kare bekletilir; yüklendiği karede tuval bir kez daha çizilir,
// sonra bekletme bırakılır (çizim yalnız kare değişince olur: frameloop "never"; ../uc/Model.tsx ile aynı düzen). Böylece ekran görüntüsü
// her zaman o karenin dokusuyla alınır (useOffthreadVideoTexture doku gelince tuvali yeniden çizmiyor).
import {useThree} from '@react-three/fiber';
import {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {useCurrentFrame, useDelayRender, useVideoConfig} from 'remotion';
import * as THREE from 'three';

export const useKareDokusu = (url: string | null): THREE.Texture | null => {
  const {advance} = useThree();
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  const kare = useCurrentFrame();
  const {fps} = useVideoConfig();
  const [doku, setDoku] = useState<{url: string; t: THREE.Texture} | null>(null);
  const tutamac = useRef<number | null>(null);
  const son = useRef<THREE.Texture | null>(null);
  son.current = doku?.t ?? null;
  const birak = () => {
    if (tutamac.current !== null) continueRender(tutamac.current);
    tutamac.current = null;
  };
  useLayoutEffect(() => {
    if (!url || doku?.url === url) return;
    tutamac.current = delayRender(`kare dokusu: ${url.slice(-80)}`, {timeoutInMilliseconds: 120000});
    let iptal = false;
    new THREE.TextureLoader().loadAsync(url).then((t) => {
      if (iptal) {
        t.dispose();
        return;
      }
      setDoku((eski) => {
        eski?.t.dispose();
        return {url, t};
      });
    }, (e) => cancelRender(e));
    return () => {
      iptal = true;
      birak();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);
  // Yüklendiği commit'te: tüketicinin useLayoutEffect'i dokuyu uniform'a yazdı; şimdi çiz, sonra bırak.
  useEffect(() => {
    if (doku && doku.url === url && tutamac.current !== null) {
      advance((kare / fps) * 1000);
      birak();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doku, url]);
  useEffect(() => () => son.current?.dispose(), []);
  return doku?.t ?? null;
};
