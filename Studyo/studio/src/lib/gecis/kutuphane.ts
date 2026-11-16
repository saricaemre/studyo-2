import veri from './gecisler.json';

/**
 * Gölgelendirici geçiş kütüphanesi: gl-transitions 3.0.0 (MIT; Copyright (c) 2017-present gl-transitions contributors,
 * LISANS-gl-transitions.txt). gecisler.json `./st gecis uret` ile node_modules/gl-transitions'tan üretilir; ek doku isteyen
 * iki geçiş (DisplacementMap, LumaWipe) çıkarılmıştır. Her geçişin yazarı ve lisansı kendi satırında (184 geçiş: 182 MIT, 1 BSD 3, 1 BSD 2).
 * Göz atmak: ./st gecis liste · panel → Kütüphane → Geçişler (önizlemeli).
 */
export type GecisParamTuru = 'float' | 'int' | 'bool' | 'vec2' | 'vec3' | 'vec4' | 'ivec2' | 'ivec3' | 'ivec4';
export type GecisParamDegeri = number | boolean | number[];
export type GecisParam = {type: GecisParamTuru; default?: GecisParamDegeri; min?: number; max?: number; step?: number; color?: boolean; description?: string};
export type GecisTanimi = {name: string; author: string; license: string; description: string; tags: string[]; params: Record<string, GecisParam>; glsl: string};

const L = (veri as unknown as {gecisler: GecisTanimi[]}).gecisler;
export const GECISLER: Record<string, GecisTanimi> = Object.fromEntries(L.map((g) => [g.name, g]));
export const GECIS_ADLARI = L.map((g) => g.name);

export const gecisBul = (ad: string): GecisTanimi => {
  const g = GECISLER[ad];
  if (!g) throw new Error(`Geçiş yok: ${ad} (src/lib/gecis/gecisler.json; ./st gecis liste)`);
  return g;
};
