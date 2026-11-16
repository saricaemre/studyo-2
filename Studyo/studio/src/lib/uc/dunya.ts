// Dünya küresi dokusu: gerçek coğrafya (Natural Earth 1:50m, kamu malı; world-atlas 2.0.2, ISC). Kıta uydurulmaz.
// Eşdikdörtgen tuval → CanvasTexture. Tuval CPU'da çizilir (willReadFrequently): çizim sırası ve ekran kartından bağımsız.
// Sınır çizgisi ve ülke vurgusu siyasi bir tercihtir: varsayılan kapalı; açmak kullanıcı kararıdır (CLAUDE.md kural 3).
import * as THREE from 'three';
import {feature, mesh} from 'topojson-client';
import type {GeometryCollection, Topology} from 'topojson-specification';
import veri from 'world-atlas/countries-50m.json';

const TOPO = veri as unknown as Topology<{countries: GeometryCollection<{name: string}>; land: GeometryCollection}>;

export type DunyaAyar = {
  deniz?: string;
  kara?: string;
  /** Ülke sınırı rengi; null: çizilmez (varsayılan). */
  sinir?: string | null;
  sinirKalinlik?: number;
  /** Ülke → renk. Anahtar İngilizce ad ("Turkey", "Palestine") ya da ISO 3166-1 sayısal kod ("792"). Bulunamayan ad hata verir. */
  vurgu?: Record<string, string>;
  /** Enlem/boylam ızgarası rengi (15°); null: yok. */
  izgara?: string | null;
  /** Doku genişliği (yükseklik yarısı). 4096: küre ekranı doldurduğunda bile keskin. */
  genislik?: number;
};

type Halka = number[][];

/** Halkaları eşdikdörtgen yola çevirir; 180. meridyeni geçen halkalar açılır (boylam sürekli), sonra üç kez (−W, 0, +W) çizilir. */
const yol = (ctx: CanvasRenderingContext2D, halkalar: Halka[], W: number, H: number, kapat: boolean) => {
  ctx.beginPath();
  for (const h of halkalar) {
    let onceki: number | null = null, kay = 0;
    h.forEach(([lon, lat], i) => {
      if (onceki !== null) {
        const d = lon - onceki;
        if (d > 180) kay -= 360;
        else if (d < -180) kay += 360;
      }
      onceki = lon;
      const x = ((lon + kay + 180) / 360) * W, y = ((90 - lat) / 180) * H;
      if (i) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
    });
    if (kapat) ctx.closePath();
  }
};

const ucKez = (ctx: CanvasRenderingContext2D, W: number, ciz: () => void) => {
  for (const dx of [-W, 0, W]) {
    ctx.save();
    ctx.translate(dx, 0);
    ciz();
    ctx.restore();
  }
};

const halkalar = (g: GeoJSON.Geometry | null): Halka[][] =>
  !g ? [] : g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];

/** Ülkenin topojson kaydı (ad ya da ISO sayısal kod). */
export const ulke = (anahtar: string) => {
  const g = TOPO.objects.countries.geometries.find((x) => x.id === anahtar || (x.properties as {name?: string} | undefined)?.name === anahtar);
  if (!g) throw new Error(`Ülke bulunamadı: "${anahtar}" (world-atlas countries-50m: İngilizce ad ya da ISO sayısal kod)`);
  return g;
};

export const dunyaTuvali = (a: DunyaAyar = {}) => {
  const W = a.genislik ?? 4096, H = W / 2;
  const tuval = document.createElement('canvas');
  tuval.width = W;
  tuval.height = H;
  const ctx = tuval.getContext('2d', {willReadFrequently: true})!;
  ctx.fillStyle = a.deniz ?? '#1d3d6b';
  ctx.fillRect(0, 0, W, H);
  const kara = feature(TOPO, TOPO.objects.land) as unknown as GeoJSON.FeatureCollection;
  ctx.fillStyle = a.kara ?? '#e9dcc3';
  const karaH = kara.features.flatMap((f) => halkalar(f.geometry)).flat();
  ucKez(ctx, W, () => {
    yol(ctx, karaH, W, H, true);
    ctx.fill('evenodd');
  });
  for (const [anahtar, renk] of Object.entries(a.vurgu ?? {})) {
    const f = feature(TOPO, ulke(anahtar)) as unknown as GeoJSON.Feature;
    ctx.fillStyle = renk;
    const h = halkalar(f.geometry).flat();
    ucKez(ctx, W, () => {
      yol(ctx, h, W, H, true);
      ctx.fill('evenodd');
    });
  }
  if (a.sinir) {
    const m = mesh(TOPO, TOPO.objects.countries, (x, y) => x !== y) as unknown as GeoJSON.MultiLineString;
    ctx.strokeStyle = a.sinir;
    ctx.lineWidth = (a.sinirKalinlik ?? 1.2) * (W / 4096);
    ctx.lineJoin = 'round';
    ucKez(ctx, W, () => {
      yol(ctx, m.coordinates, W, H, false);
      ctx.stroke();
    });
  }
  if (a.izgara) {
    ctx.strokeStyle = a.izgara;
    ctx.lineWidth = W / 4096;
    ctx.beginPath();
    for (let lon = -180; lon <= 180; lon += 15) {
      ctx.moveTo(((lon + 180) / 360) * W, 0);
      ctx.lineTo(((lon + 180) / 360) * W, H);
    }
    for (let lat = -75; lat <= 75; lat += 15) {
      ctx.moveTo(0, ((90 - lat) / 180) * H);
      ctx.lineTo(W, ((90 - lat) / 180) * H);
    }
    ctx.stroke();
  }
  return tuval;
};

export const dunyaDokusu = (a: DunyaAyar = {}) => {
  const t = new THREE.CanvasTexture(dunyaTuvali(a));
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
};

/** Enlem/boylam → küre yüzeyinde nokta (THREE.SphereGeometry'nin doku yerleşimiyle aynı). */
export const enlemBoylam = (enlem: number, boylam: number, r = 1) => {
  const phi = THREE.MathUtils.degToRad(boylam + 180), theta = THREE.MathUtils.degToRad(90 - enlem);
  return new THREE.Vector3(-r * Math.cos(phi) * Math.sin(theta), r * Math.cos(theta), r * Math.sin(phi) * Math.sin(theta));
};

/** Kürenin (Euler XYZ) dönüşü: verilen enlem/boylam kameraya (+z) bakar. İki konum arasında yumuşak geçiş için açıları ara değerle. */
export const yuzunuDondur = (enlem: number, boylam: number): [number, number, number] => [
  THREE.MathUtils.degToRad(enlem),
  -THREE.MathUtils.degToRad(boylam + 90),
  0,
];
