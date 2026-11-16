import React from 'react';
import {getInputProps} from 'remotion';

/**
 * Geçiş plakası kipi (oturum 6a, pipeline/gecis.py): ./st bir kesimin penceresindeki kareleri iki kez çizer, girdi
 * `gecisPlakasi: {kesim, taraf}` ile. O çizimde yalnız kesimin o tarafı görünür; üst katmanlar (altyazı, logo, etiket, Bitis'in
 * rötuşu) çizilmez: onlar asıl çizimde geçişin ÜSTÜNDE gelir, gölgelendiriciyle bükülmez.
 * Bu dosya bilerek hafiftir (gölgelendirici kütüphanesini yüklemez): ortak bileşenler (Bitis, Captions, Etiket …) buradan okur.
 */
export type GecisPlakasi = {kesim: string; taraf: 'a' | 'b'};

export const gecisPlakasi = (): GecisPlakasi | null => (getInputProps() as {gecisPlakasi?: GecisPlakasi}).gecisPlakasi ?? null;

/** Filmin kendi üst katmanı (yazı, logo, marka kartı): geçiş plakasında çizilmez, asıl çizimde geçişin üstünde kalır. */
export const UstKatman: React.FC<{children: React.ReactNode}> = ({children}) => (gecisPlakasi() ? null : <>{children}</>);
