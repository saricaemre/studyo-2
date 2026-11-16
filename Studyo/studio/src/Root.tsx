import {Composition, Still} from 'remotion';
import {FPS} from './lib/anim';
import {KanalAvatar, KanalBanner, MARKA_VARSAYILAN} from './stiller/harita-masasi/Marka';
import {KatalogGorsel} from './katalog/KatalogGorsel';
import {KatalogAnimasyon} from './katalog/KatalogAnimasyon';
import {ModelOnizleme} from './katalog/ModelOnizleme';
import {KatalogAltyazi} from './katalog/KatalogAltyazi';
import {GecisOnizleme} from './katalog/GecisOnizleme';
import altyaziKaynak from '../katalog/onizleme/altyazi/kaynak/timeline.json';
import {Yapim} from './yapim/Yapim';
// @st:import

// Yeni videolar `./st yeni` ile aşağıdaki işaretlerin üstüne otomatik eklenir.
export const RemotionRoot = () => (
  <>
  {/* @st:kompozisyon */}
  {/* Stil kataloğu önizlemeleri (./st katalog) */}
  <Still id="KatalogGorsel" component={KatalogGorsel} width={1080} height={1080} />
  <Composition id="KatalogAnimasyon" component={KatalogAnimasyon} width={1080} height={1080} fps={30} durationInFrames={90} />
  <Still id="ModelOnizleme" component={ModelOnizleme} width={1080} height={1080} defaultProps={{src: ''}} />
  {/* Gölgelendirici geçiş önizlemesi (./st gecis onizle): iki nötr kart, 1,5 sn; --props '{"ad": "BookFlip"}' */}
  <Composition id="GecisOnizleme" component={GecisOnizleme} width={360} height={360} fps={30} durationInFrames={45} />
  <Composition id="KatalogAltyazi" component={KatalogAltyazi} width={1080} height={1920} fps={30} durationInFrames={Math.ceil(altyaziKaynak.duration * 30)} defaultProps={{tur: 'niyetli' as const}} />
  {/* Yapım filmi ("nasıl yapıldı", ./st yapim): 15 sn, girdi kurgu (out/_yapim/<id>/kurgu.json) */}
  <Composition id="Yapim-9x16" component={Yapim} width={1080} height={1920} fps={30} durationInFrames={450} defaultProps={{}} />
  <Composition id="Yapim-16x9" component={Yapim} width={1920} height={1080} fps={30} durationInFrames={450} defaultProps={{}} />
  <Composition id="Yapim-1x1" component={Yapim} width={1080} height={1080} fps={30} durationInFrames={450} defaultProps={{}} />
  <Composition id="Yapim-4x5" component={Yapim} width={1080} height={1350} fps={30} durationInFrames={450} defaultProps={{}} />
  {/* Harita Masası stil paketinin kanal kimliği taslakları (ad karar verilmedi): --props='{"ad":"...","monogram":".."}' */}
  <Still id="HaritaMasasi-Avatar" component={KanalAvatar} width={800} height={800} defaultProps={MARKA_VARSAYILAN} />
  <Still id="HaritaMasasi-Banner" component={KanalBanner} width={2560} height={1440} defaultProps={MARKA_VARSAYILAN} />
  </>
);
