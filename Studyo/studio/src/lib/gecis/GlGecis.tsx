import React, {useLayoutEffect, useRef} from 'react';
import {cancelRender, continueRender, delayRender, getRemotionEnvironment, useVideoConfig} from 'remotion';
import {type GecisParamDegeri, type GecisTanimi, gecisBul} from './kutuphane';

/**
 * İki GÖRÜNTÜYÜ bir gl-transitions gölgelendiricisiyle birleştirir: ilerleme 0'da `from`, 1'de `to` (GL Transition Specification v1).
 * Kaynak: görüntü adresi (staticFile; Blender ya da motor plakası, Magnific plakası, gerçek görüntü karesi, geçiş plakası) ya da tuval.
 * Kare t'nin saf fonksiyonudur: ilerlemeyi çağıran kareden hesaplar (Kesim.tsx → gecisIlerleme); saat, çizim döngüsü yok.
 * Doku yükleme 3B katmanın yolunu izler: delayRender/continueRender (CSS arka planı yok). Gölgelendirici tuval başına bir kez derlenir;
 * karede yalnız dokular ve uniform'lar değişir. Başsız Chrome'da WebGL SwiftShader'dır (bayraksız da swangle'da da; ölçüldü): geçişli kompozisyon
 * bayraksız çizilir, çünkü swangle DOM yazısını da GPU yolundan çiziyor ve büyük yazının kenarı çizim sırasına bağlı 1/255 oynuyor (ortak.py → GECIS_IZ).
 * Çizimde görüntü açılmazsa iş durur; önizlemede (Remotion Studio) `onYok` çağrılır (Kesim düz bindirmeye düşer).
 */
export type GecisKaynagi = string | HTMLImageElement | HTMLCanvasElement | ImageBitmap;

const KOSE = `attribute vec2 _p;
varying vec2 _uv;
void main() {
  gl_Position = vec4(_p, 0.0, 1.0);
  _uv = _p * 0.5 + 0.5;
}`;

const parca = (glsl: string) => `precision highp float;
varying vec2 _uv;
uniform sampler2D from, to;
uniform float progress, ratio;
vec4 getFromColor(vec2 uv) { return texture2D(from, uv); }
vec4 getToColor(vec2 uv) { return texture2D(to, uv); }
${glsl}
void main() { gl_FragColor = transition(_uv); }
`;

type GL = WebGLRenderingContext | WebGL2RenderingContext;
type Durum = {gl: GL; ad: string; program: WebGLProgram; tampon: WebGLBuffer; dokular: [WebGLTexture, WebGLTexture]; yer: Map<string, WebGLUniformLocation | null>};

const derle = (gl: GL, tur: number, kaynak: string, ad: string) => {
  const s = gl.createShader(tur);
  if (!s) throw new Error('WebGL gölgelendirici açılamadı');
  gl.shaderSource(s, kaynak);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(`Geçiş ${ad} derlenmedi: ${gl.getShaderInfoLog(s)}`);
  return s;
};

const kur = (gl: GL, g: GecisTanimi): Durum => {
  const program = gl.createProgram();
  if (!program) throw new Error('WebGL programı açılamadı');
  gl.attachShader(program, derle(gl, gl.VERTEX_SHADER, KOSE, g.name));
  gl.attachShader(program, derle(gl, gl.FRAGMENT_SHADER, parca(g.glsl), g.name));
  gl.bindAttribLocation(program, 0, '_p');
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(`Geçiş ${g.name} bağlanmadı: ${gl.getProgramInfoLog(program)}`);
  const tampon = gl.createBuffer();
  if (!tampon) throw new Error('WebGL tamponu açılamadı');
  gl.bindBuffer(gl.ARRAY_BUFFER, tampon);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW); // tam ekran tek üçgen
  const doku = () => {
    const t = gl.createTexture();
    if (!t) throw new Error('WebGL dokusu açılamadı');
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    return t;
  };
  return {gl, ad: g.name, program, tampon, dokular: [doku(), doku()], yer: new Map()};
};

const yer = (d: Durum, ad: string) => {
  if (!d.yer.has(ad)) d.yer.set(ad, d.gl.getUniformLocation(d.program, ad));
  return d.yer.get(ad) ?? null;
};

/** Parametre: kullanıcının değeri, yoksa kataloğun varsayılanı; hiçbiri boş bırakılmaz (boş uniform 0'dır, çoğu geçişi bozar). */
const parametreler = (d: Durum, g: GecisTanimi, param: Record<string, GecisParamDegeri>) => {
  const {gl} = d;
  for (const [ad, p] of Object.entries(g.params)) {
    const ham = param[ad] ?? p.default ?? 0;
    const v = (Array.isArray(ham) ? ham : [ham]).map((x) => Number(x));
    const l = yer(d, ad);
    if (l === null) continue;
    if (p.type === 'int' || p.type === 'bool' || p.type.startsWith('ivec')) {
      const n = v.map((x) => Math.round(x));
      if (n.length === 1) gl.uniform1i(l, n[0]);
      else if (n.length === 2) gl.uniform2i(l, n[0], n[1]);
      else if (n.length === 3) gl.uniform3i(l, n[0], n[1], n[2]);
      else gl.uniform4i(l, n[0], n[1], n[2], n[3]);
    } else if (v.length === 1) gl.uniform1f(l, v[0]);
    else if (v.length === 2) gl.uniform2f(l, v[0], v[1]);
    else if (v.length === 3) gl.uniform3f(l, v[0], v[1], v[2]);
    else gl.uniform4f(l, v[0], v[1], v[2], v[3]);
  }
};

type Kaynak = HTMLImageElement | HTMLCanvasElement | ImageBitmap;

const yukle = (k: GecisKaynagi): Promise<Kaynak> => {
  if (typeof k !== 'string') return Promise.resolve(k);
  const img = new Image();
  img.src = k;
  return img.decode().then(() => img, () => {
    throw new Error(`Geçiş görüntüsü açılmadı: ${k}`);
  });
};

const ciz = (d: Durum, g: GecisTanimi, A: Kaynak, B: Kaynak, ilerleme: number, param: Record<string, GecisParamDegeri>) => {
  const {gl} = d;
  gl.useProgram(d.program);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true); // uv (0, 0) görüntünün sol altı (gl-transitions sözleşmesi)
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE); // PNG'nin baytları olduğu gibi (gAMA/iCCP dönüşümü yok)
  [A, B].forEach((src, i) => {
    gl.activeTexture(gl.TEXTURE0 + i);
    gl.bindTexture(gl.TEXTURE_2D, d.dokular[i]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src);
    gl.uniform1i(yer(d, i === 0 ? 'from' : 'to'), i);
  });
  gl.bindBuffer(gl.ARRAY_BUFFER, d.tampon);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.uniform1f(yer(d, 'progress'), Math.max(0, Math.min(1, ilerleme)));
  gl.uniform1f(yer(d, 'ratio'), gl.drawingBufferWidth / gl.drawingBufferHeight);
  parametreler(d, g, param);
  gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  gl.finish();
};

export const GlGecis: React.FC<{
  /** gl-transitions adı (PascalCase): BookFlip, DirectionalWipe, InkBleed … */
  ad: string;
  from: GecisKaynagi;
  to: GecisKaynagi;
  /** 0 → from, 1 → to; çağıran kareden hesaplar. */
  ilerleme: number;
  param?: Record<string, GecisParamDegeri>;
  style?: React.CSSProperties;
  /** Önizlemede görüntü açılmazsa (plaka henüz çizilmedi): çağıran düz bindirmeye düşer. Çizimde verilmez: iş durur. */
  onYok?: () => void;
}> = ({ad, from, to, ilerleme, param = {}, style, onYok}) => {
  const {width, height} = useVideoConfig();
  const tuval = useRef<HTMLCanvasElement>(null);
  const durum = useRef<Durum | null>(null);
  const g = gecisBul(ad);
  const paramAnahtar = JSON.stringify(param);

  useLayoutEffect(() => {
    const c = tuval.current;
    if (!c) return;
    const h = delayRender(`GlGecis ${ad}`);
    let bitti = false;
    let iptal = false;
    const bitir = () => {
      if (!bitti) {
        bitti = true;
        continueRender(h);
      }
    };
    Promise.all([yukle(from), yukle(to)])
      .then(([A, B]) => {
        if (iptal) return bitir();
        let d = durum.current;
        if (!d || d.ad !== ad) {
          const gl = (c.getContext('webgl2', {alpha: true, premultipliedAlpha: false, antialias: false, depth: false, stencil: false,
            preserveDrawingBuffer: true}) ?? c.getContext('webgl', {alpha: true, premultipliedAlpha: false, antialias: false, depth: false,
            stencil: false, preserveDrawingBuffer: true})) as GL | null;
          if (!gl) throw new Error('WebGL yok: gölgelendirici geçişi çizilemedi');
          d = kur(gl, g);
          durum.current = d;
        }
        ciz(d, g, A, B, ilerleme, JSON.parse(paramAnahtar) as Record<string, GecisParamDegeri>);
        bitir();
      })
      .catch((e: unknown) => {
        if (getRemotionEnvironment().isRendering || !onYok) {
          cancelRender(e instanceof Error ? e : new Error(String(e)));
        } else {
          onYok();
        }
        bitir();
      });
    return () => {
      iptal = true;
      bitir();
    };
  }, [ad, g, from, to, ilerleme, paramAnahtar, onYok]);

  // Söküldüğünde GPU belleği ve bağlam bırakılır (uzun çizimde bağlam sınırına takılmasın)
  useLayoutEffect(() => () => {
    const d = durum.current;
    if (!d) return;
    d.gl.deleteTexture(d.dokular[0]);
    d.gl.deleteTexture(d.dokular[1]);
    d.gl.deleteBuffer(d.tampon);
    d.gl.deleteProgram(d.program);
    d.gl.getExtension('WEBGL_lose_context')?.loseContext();
    durum.current = null;
  }, []);

  return <canvas ref={tuval} width={width} height={height} style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', ...style}} />;
};
