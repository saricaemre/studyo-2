// ./st katalog üretir: elle düzenleme. Katalog görüntü stilleri (katalog/gorsel/*.json).
import {Secenek} from '../lib/gorunus';
import g_arsiv_belgesel from '../../katalog/gorsel/arsiv-belgesel.json';
import g_duz_illustrasyon from '../../katalog/gorsel/duz-illustrasyon.json';
import g_editoryal_kagit from '../../katalog/gorsel/editoryal-kagit.json';
import g_gece_sinematik from '../../katalog/gorsel/gece-sinematik.json';
import g_harita_masasi from '../../katalog/gorsel/harita-masasi.json';
import g_isvicre_izgara from '../../katalog/gorsel/isvicre-izgara.json';
import g_kil_maket from '../../katalog/gorsel/kil-maket.json';
import g_neseli_sofra from '../../katalog/gorsel/neseli-sofra.json';
import g_pastel_illustrasyon from '../../katalog/gorsel/pastel-illustrasyon.json';
import g_pop_kolaj from '../../katalog/gorsel/pop-kolaj.json';
import g_poster_brutalist from '../../katalog/gorsel/poster-brutalist.json';
import g_tutanak_belge from '../../katalog/gorsel/tutanak-belge.json';
import g_veri_gazeteciligi from '../../katalog/gorsel/veri-gazeteciligi.json';

export type KatalogGorselKaydi = {ad: string; baslik: string; ozet: string; varyasyonlar: Record<string, Secenek>};
export const GORSELLER = {
  'arsiv-belgesel': g_arsiv_belgesel,
  'duz-illustrasyon': g_duz_illustrasyon,
  'editoryal-kagit': g_editoryal_kagit,
  'gece-sinematik': g_gece_sinematik,
  'harita-masasi': g_harita_masasi,
  'isvicre-izgara': g_isvicre_izgara,
  'kil-maket': g_kil_maket,
  'neseli-sofra': g_neseli_sofra,
  'pastel-illustrasyon': g_pastel_illustrasyon,
  'pop-kolaj': g_pop_kolaj,
  'poster-brutalist': g_poster_brutalist,
  'tutanak-belge': g_tutanak_belge,
  'veri-gazeteciligi': g_veri_gazeteciligi,
} as unknown as Record<string, KatalogGorselKaydi>;
