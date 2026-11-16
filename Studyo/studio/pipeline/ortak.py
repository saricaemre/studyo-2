"""Stüdyo araçlarının ortak parçaları: yollar, video tanımını okuma, işaret hesabı, ölçüm yardımcıları."""
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent          # studio/
KANAL = ROOT.parent                                    # Youtube/
FPS = 24  # eski videoların kare hızı; videonun kendi hızı Video.fps (script.json → fps)
PROFIL_DIR = ROOT / "profiller"
FORMATLAR = json.loads((PROFIL_DIR / "formatlar.json").read_text())
FORMATLAR.pop("_doc", None)
VARSAYILAN_PROFIL = "dikey-anlatim"
# 3B katman (Three.js): kullanan Remotion kompozisyonu yazılımla (ANGLE + SwiftShader) çizilir. Ekran kartı (angle) her işlemin ilk
# karesini farklı çiziyor; swangle 7/7 bayt bayt aynı, video ve tek kare yolu da aynı (denemeler/threejs_3b/OKU.md). Öteki videolar bayraksız.
UC_GL = "swangle"
UC_BEKLEME_MS = 120000  # ilk 3B kare (gölgelendirici derleme, yansıma ortamı, gölge) yazılımla, yükte ve paralel sekmede 30 sn'yi aşabiliyor


def gl_bayraklari(gl: str | None) -> list[str]:
    """npx remotion render/still bayrakları: 3B katmanlı kompozisyonda yazılım GL + uzun bekleme; değilse hiçbiri (eski videolar aynı)."""
    return [f"--gl={gl}", f"--timeout={UC_BEKLEME_MS}"] if gl else []
UC_IZ = re.compile(r"""from\s+['"](?:[./]*lib/uc(?:/[\w.]+)?|[./]*lib/goruntu(?:/(?:index|Derinlik25D|Stilize|doku))?|@remotion/three|"""
                   r"""@react-three/fiber|three(?:/[^'"]*)?)['"]""")  # gerçek görüntü kitinin 2.5B ve stilizasyonu da 3B katmanda (src/lib/goruntu)
# Gölgelendirici geçişleri (oturum 6a, src/lib/gecis): <GlGecis> / <Kesim> WebGL'le çizer. Geçişli kompozisyon BAYRAKSIZ çizilir: başsız Chrome'da
# WebGL zaten SwiftShader (ANGLE Vulkan SwiftShader; bayraksız ve swangle aynı çizici), DOM yazısı yazılımla. swangle DOM yazısını da GPU yolundan
# çiziyor: deneme_gecis 16x9'da 240 px'lik başlığın 4–8 pikseli çizim sırasına bağlı 1/255 oynadı; bayraksız 6/6 kare iki sırada aynı.
GECIS_IZ = re.compile(r"""from\s+['"][./]*lib/gecis(?:/(?:index|GlGecis|Kesim|kutuphane))?['"]""")

# Vuruş renkleri: profildeki sıraya göre (kontak tabakası ve zaman çizelgesi için)
_PALET = [(166, 58, 43), (201, 164, 92), (46, 74, 125), (196, 98, 45), (92, 112, 70), (110, 70, 120), (60, 130, 140), (150, 90, 60)]


def profil(ad: str) -> dict:
    p = PROFIL_DIR / f"{ad}.json"
    if not p.exists():
        mevcut = ", ".join(sorted(x.stem for x in PROFIL_DIR.glob("*.json") if x.stem != "formatlar"))
        raise SystemExit(f"Profil yok: {ad} (mevcut: {mevcut})")
    return json.loads(p.read_text())


def norm_word(s: str) -> str:
    return re.sub(r"[.,…!?;:]", "", s)


def jload(p: Path):
    return json.loads(Path(p).read_text())


@dataclass
class Video:
    id: str
    dir: Path
    pub: Path
    script: dict
    timeline: dict | None
    cuefile: dict | None
    cues: dict = field(default_factory=dict)
    cue_error: str = ""

    # ---- tanım
    @property
    def profil(self) -> dict:
        return profil(self.script.get("profil", VARSAYILAN_PROFIL))

    @property
    def formatlar(self) -> list[str]:
        return self.script.get("formatlar") or self.profil["formatlar"]

    @property
    def anlatim(self) -> bool:
        return self.ses.get("kaynak", "edge") != "yok"

    @property
    def ses(self) -> dict:
        """Ses ayarı. Eski videolarda voice/rate/pitch üst düzeydeydi."""
        d = dict(self.script.get("ses", {}))
        for k in ("voice", "rate", "pitch"):
            if k in self.script and k not in d:
                d[k] = self.script[k]
        d.setdefault("kaynak", "edge")
        return d

    @property
    def altyazi(self) -> dict:
        """Altyazı türü: script.json → altyazi ("niyetli" ya da {"tur": "niyetli", "zemin", "alfa"}); yoksa klasik (components/Captions.tsx)."""
        a = self.script.get("altyazi") or {}
        return {"tur": a} if isinstance(a, str) else {"tur": "klasik", **a} if "tur" not in a else dict(a)

    @property
    def niyetli(self) -> bool:
        """Niyetli altyazı (pipeline/niyet.py): kelimenin şiddeti ve perdesi değişken yazı tipinin ağırlığına, genişliğine ve boyutuna bağlı."""
        return self.anlatim and self.altyazi["tur"] == "niyetli"

    @property
    def motor(self) -> str:
        """Render motoru: "remotion" (src/<id>/, React), "hyperframes" (hf/<id>/index.html, HTML + GSAP; pipeline/hf.py) ya da
        "blender" (blender/<id>/sahne.py plakaları + src/<id>/ üst katmanı; pipeline/blender.py)."""
        return self.script.get("motor", "remotion")

    @property
    def comp(self) -> str:
        return self.script.get("comp") or "".join(p.capitalize() for p in self.id.split("_"))

    def comp_for(self, fmt: str) -> str:
        """Tek formatlı videoda kompozisyon adı yalın, çok formatlıda -<format> ekli."""
        return self.comp if len(self.formatlar) == 1 else f"{self.comp}-{fmt}"

    def suffix(self, fmt: str) -> str:
        return "" if len(self.formatlar) == 1 else f"_{fmt}"

    @property
    def cover(self) -> str | None:
        return self.script.get("cover")

    @property
    def duration(self) -> float:
        return self.timeline["duration"] if self.timeline else 0.0

    @property
    def fps(self) -> int:
        """Kare hızı: script.json → fps (yeni videolar 30), yoksa eski videoların 24'ü."""
        return int(self.script.get("fps", FPS))

    @property
    def kod_dizini(self) -> Path:
        """Remotion sahne kodu (Blender'da üst katman): src/<kod>/ (script.json → kod, yoksa id)."""
        return ROOT / "src" / self.script.get("kod", self.id)

    @property
    def uc(self) -> bool:
        """3B katman kullanıyor mu: Remotion'da src/<kod>/ lib/uc'u (ya da three'yi) içe aktarır; HyperFrames'te sahne yerel three kopyasını yükler."""
        if self.motor == "hyperframes":
            d = ROOT / "hf" / self.id
            return any("assets/lib/three/" in f.read_text() or "assets/lib/uc/" in f.read_text()
                       for f in [d / "index.html", *(d / "compositions").rglob("*.html")] if f.exists())
        return self.kod_dizini.exists() and any(UC_IZ.search(f.read_text()) for f in self.kod_dizini.rglob("*.ts*"))

    @property
    def gecisli(self) -> bool:
        """Gölgelendirici geçişi kullanıyor mu: src/<kod>/ lib/gecis'i (GlGecis, Kesim) içe aktarır (oturum 6a)."""
        return self.motor != "hyperframes" and self.kod_dizini.exists() and any(GECIS_IZ.search(f.read_text()) for f in self.kod_dizini.rglob("*.ts*"))

    @property
    def gl(self) -> str | None:
        """Remotion'un GL ayarı: 3B katmanlı kompozisyonda UC_GL, yoksa None (bayraksız: eski videoların kareleri değişmez; gölgelendirici geçişli
        kompozisyon da bayraksız: WebGL'i başsız Chrome'da zaten SwiftShader, yukarıda GECIS_IZ notu)."""
        return UC_GL if self.motor != "hyperframes" and self.uc else None

    @property
    def gorunus_modu(self) -> str:
        """"video" (videoya özel, videos/<id>/gorunus.json) · "seri:<ad>" (stiller/<ad>/gorunus.json) · "paket:<stil>" (eski videolar, tokens.ts)."""
        g = self.script.get("gorunus")
        return g if g else f"paket:{self.script.get('stil', 'temel')}"

    @property
    def gorunus_dosyasi(self) -> Path | None:
        m = self.gorunus_modu
        if m == "video":
            return self.dir / "gorunus.json"
        if m.startswith("seri:"):
            return ROOT / "stiller" / m[5:] / "gorunus.json"
        return None

    def gorunus_json(self) -> dict | None:
        f = self.gorunus_dosyasi
        return jload(f) if f and f.exists() else None

    @property
    def gorunus_secimi(self) -> dict | None:
        """Seçilmiş görünüş seçeneği (Secenek, src/lib/gorunus.ts) ya da None (eski paket ya da henüz seçilmedi)."""
        G = self.gorunus_json() or {}
        k = G.get("secim")
        return (G.get("secenekler") or {}).get(k) if k else None

    @property
    def yol_modu(self) -> bool:
        """Planda üç yol (2a): gorunus.json → yol_modu. Seçenekler aynı kanca karesinin üç görünüşü değil, üç ayrı fikirdir (her biri kendi sahnesiyle)."""
        return self.gorunus_modu == "video" and bool((self.gorunus_json() or {}).get("yol_modu"))

    @property
    def yollu(self) -> bool:
        """Seçenekler yol bloğu taşıyor mu (yol modu ya da "bu yolda başka görünüş"): sahne kodu seçenek harfine göre dallanabilir."""
        if self.gorunus_modu != "video":
            return False
        G = self.gorunus_json() or {}
        return bool(G.get("yol_modu")) or any(isinstance(o, dict) and o.get("yol") for o in (G.get("secenekler") or {}).values())

    def secenek_harfi(self, anahtar: str | None = None) -> str | None:
        """Çizilen seçeneğin harfi: istenen (deneme karesi) > seçim > ilk seçenek."""
        G = self.gorunus_json() or {}
        S = G.get("secenekler") or {}
        return anahtar or G.get("secim") or (sorted(S)[0] if S else None)

    @property
    def gorunus_etiketi(self) -> str:
        m = self.gorunus_modu
        if m == "video":
            o = self.gorunus_secimi
            return "videoya özel" + (f" · {o['ad']}" if o else " · seçilmedi")
        return ("seri " if m.startswith("seri:") else "stil ") + m.split(":", 1)[1]

    @property
    def seri_anahtari(self) -> str | None:
        """Aynı görünüşü bilerek paylaşan videoların ortak anahtarı (eski paket = o paketin serisi)."""
        m = self.gorunus_modu
        return self.script.get("seri") if m == "video" else m.split(":", 1)[1]  # seriye çevrilen ilk video da o seridendir

    @property
    def bitis(self) -> dict:
        """Son rötuş: görünüşün bitis'i + script.json → bitis (videoya özel düzeltme). Eski videolarda yalnız script.json; boşsa kapalı."""
        o = self.gorunus_secimi
        return {**((o or {}).get("bitis") or {}), **(self.script.get("bitis") or {})}

    @property
    def nframes(self) -> int:
        return int(np.ceil(self.duration * self.fps))

    @property
    def beats(self) -> list[float]:
        return (self.timeline or {}).get("beats", [])

    @property
    def yapi(self) -> list[str] | None:
        """Filmin kendi vuruş iskeleti (script.json → yapi; sırayla, 1–12 benzersiz ad) ya da None (profilin önerisi geçerli)."""
        y = self.script.get("yapi")
        return [str(x) for x in y] if isinstance(y, list) and y else None

    @property
    def vuruslar(self) -> list[str]:
        """Geçerli vuruş iskeleti: filmin yapısı varsa o, yoksa profilin önerisi. Lint, ölçüm, kontak ve panel buradan okur."""
        return self.yapi or self.profil["vuruslar"]

    def step_rgb(self, step: str):
        vs = self.vuruslar
        return _PALET[vs.index(step) % len(_PALET)] if step in vs else (120, 110, 100)

    # ---- vuruşlar (anlatımlı videoda cümleler, anlatımsızda bölümler)
    def sentence(self, sid):
        return next(s for s in self.timeline["sentences"] if s["id"] == sid)

    def script_sentence(self, sid):
        return next(s for s in self.script["sentences"] if s["id"] == sid)

    def text_of(self, sid):
        s = self.script_sentence(sid)
        if "parts" in s:
            return " ".join(p["text"] for p in s["parts"])
        return s.get("shot", {}).get("olay", "")

    def keyword_cue(self, sid):
        """Vuruşun olay işareti: (ad, saniye) ya da None.
        Anlatımlı: shot.anahtar kelimesine bağlı işaret. Anlatımsız ya da açıkça verilmişse: shot.isaret."""
        if not self.cuefile:
            return None
        shot = self.script_sentence(sid).get("shot", {})
        if shot.get("isaret"):
            n = shot["isaret"]
            return (n, self.cues[n]) if n in self.cues else None
        kw = shot.get("anahtar")
        for name, anchor in self.cuefile["cues"].items():
            if anchor[0] == sid and kw and norm_word(str(anchor[1])).lower() == norm_word(kw).lower():
                return name, self.cues[name]
        return None


def load(vid: str) -> Video:
    d = ROOT / "videos" / vid
    if not d.exists():
        raise SystemExit(f"Video yok: {d}")
    script = jload(d / "script.json") if (d / "script.json").exists() else {"id": vid, "sentences": []}
    pub = ROOT / "public" / vid
    tl = jload(pub / "timeline.json") if (pub / "timeline.json").exists() else None
    cf = jload(d / "cues.json") if (d / "cues.json").exists() else None
    v = Video(vid, d, pub, script, tl, cf)
    if tl and cf and tl.get("sentences") is not None:
        try:
            v.cues = resolve_cues(tl, cf)
        except SystemExit as e:  # ses/ızgara henüz üretilmediyse işaretler çözülemez; komutlar yine çalışsın
            v.cue_error = str(e)
    return v


def resolve_anchor(tl, cf, k, anchor):
    """Bir işaret çapası → saniye. src/lib/time.ts ile birebir aynı hesap.
    [cümle, kelime, ofset]  kelime başlangıcı − lead + ofset
    ["vurus", n, ofset]      n. vuruş (müzik ızgarası) + ofset
    ["t", saniye, ofset]     mutlak zaman + ofset"""
    kind = anchor[0]
    off = float(anchor[2]) if len(anchor) > 2 else 0.0
    if kind == "t":
        return float(anchor[1]) + off
    if kind == "vurus":
        beats = tl.get("beats", [])
        n = int(anchor[1])
        if n >= len(beats):
            raise SystemExit(f"İşaret {k}: {n}. vuruş yok (ızgarada {len(beats)} vuruş)")
        return beats[n] + off
    s = next((x for x in tl["sentences"] if x["id"] == kind), None)
    if s is None:
        raise SystemExit(f"İşaret {k}: cümle yok {kind}")
    w = next((x for x in s["words"] if norm_word(x["text"]) == norm_word(str(anchor[1]))), None)
    if w is None:
        raise SystemExit(f"İşaret {k}: kelime yok {kind}/{anchor[1]}")
    return w["start"] - cf.get("lead", 0.0) + off


def resolve_cues(tl, cf):
    """cues.json → {işaret: saniye}."""
    return {k: resolve_anchor(tl, cf, k, a) for k, a in cf["cues"].items()}


def tc(sec: float) -> str:
    """Zaman kodu: 00:03.21"""
    m, s = divmod(max(0.0, sec), 60)
    return f"{int(m):02d}:{s:05.2f}"


# ---------------------------------------------------------------- ölçüm yardımcıları
def loudness(path: Path) -> dict:
    """EBU R128: entegre ses yüksekliği (LUFS), gerçek tepe (dBTP), LRA."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    s = r[r.rindex("Summary:"):]
    num = lambda pat: float(re.search(pat, s, re.S).group(1))
    return {"I": num(r"I:\s+(-?[\d.]+) LUFS"), "LRA": num(r"LRA:\s+(-?[\d.]+) LU"),
            "TP": num(r"True peak:.*?Peak:\s+(-?[\d.]+|-inf) dBFS")}


def audio_mono(path: Path, sr=16000) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def rms_db(x: np.ndarray, sr: int, a: float, b: float) -> float:
    seg = x[int(max(0, a) * sr): int(max(a, b) * sr)]
    if len(seg) == 0:
        return -120.0
    return float(20 * np.log10(np.sqrt(np.mean(seg.astype(float) ** 2)) + 1e-9))


def gray_frames(mp4: Path, w=90, h=160, fps=FPS) -> np.ndarray:
    """Videonun küçültülmüş gri kareleri (n, h, w), float32."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"fps={fps},scale={w}:{h},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w).astype(np.float32)


def motion_of(fr: np.ndarray) -> np.ndarray:
    d = np.zeros(len(fr), dtype=np.float32)
    d[1:] = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    return d


def motion_curve(mp4: Path, w=90, h=160, fps=FPS) -> np.ndarray:
    """Videodaki kare-kare görsel değişim (0–255 ölçeğinde ortalama mutlak fark). curve[i] = kare i ile i-1 farkı."""
    return motion_of(gray_frames(mp4, w, h, fps))


def flash_frames(fr: np.ndarray, motion: np.ndarray) -> list[int]:
    """Tek karelik sıçrama: kare hem öncekinden hem sonrakinden belirgin farklı, ama önceki ile sonraki birbirine benziyor
    (bir kare boyunca beliren/kaybolan öğe, patlayan kart, yanlış kare). Eski videolarda hiç yok (öğrenimler #23)."""
    if len(fr) < 3:
        return []
    d2 = np.abs(fr[2:] - fr[:-2]).mean(axis=(1, 2))
    thr = still_threshold(motion) + 2.0
    return [i for i in range(1, len(fr) - 1) if min(motion[i], motion[i + 1]) > thr and d2[i - 1] < 0.4 * min(motion[i], motion[i + 1])]


def blank_runs(fr: np.ndarray, min_frames=1):
    """Boş (tek renk) ekran aralıkları [(ilk kare, son kare + 1, gri değer)]: küçültülmüş karede standart sapma < 4."""
    sd = fr.reshape(len(fr), -1).std(axis=1)
    runs, s = [], None
    for i, q in enumerate(list(sd < 4) + [False]):
        if q and s is None:
            s = i
        elif not q and s is not None:
            if i - s >= min_frames:
                runs.append((s, i, int(np.median(fr[s]))))
            s = None
    return runs


def stil_renkleri(stil: str) -> dict:
    """Stil paketinin STIL nesnesindeki renkler (src/stiller/<stil>/tokens.ts) → {anahtar: '#rrggbb'}."""
    p = ROOT / "src" / "stiller" / stil / "tokens.ts"
    if not p.exists():
        return {}
    s = p.read_text()
    consts = dict(re.findall(r"export const (\w+)\s*=\s*'(#[0-9A-Fa-f]{6})'", s))
    m = re.search(r"export const STIL = \{(.*?)\n\};", s, re.S)
    out = {}
    for k, val in re.findall(r"^\s*(\w+):\s*([^,\n]+),", m.group(1) if m else "", re.M):
        val = val.strip()
        if re.fullmatch(r"'#[0-9A-Fa-f]{6}'", val):
            out[k] = val.strip("'")
        elif val in consts:
            out[k] = consts[val]
    return out


def _paket_fontlari(stil: str) -> dict:
    """Eski stil paketinin (tokens.ts) başlık/gövde yazı aileleri: google-fonts modül adından ("InstrumentSerif" → "Instrument Serif")."""
    p = ROOT / "src" / "stiller" / stil / "tokens.ts"
    if not p.exists():
        return {}
    s = p.read_text()
    yukleyici = {a: re.sub(r"(?<!^)(?=[A-Z])", " ", m) for a, m in re.findall(r"loadFont as (\w+)\}\s*from '@remotion/google-fonts/(\w+)'", s)}
    sabit = {c: yukleyici.get(f) for c, f in re.findall(r"export const (\w+)\s*=\s*(\w+)\(", s)}
    m = re.search(r"yazi:\s*\{([^}]*)\}", s)
    return {k: sabit.get(val.strip()) for k, val in re.findall(r"(\w+):\s*(\w+)", m.group(1))} if m else {}


def secenek_ozeti(o: dict, ad: str = "") -> dict:
    """Görünüş seçeneğinin karşılaştırılabilir özeti."""
    return {"ad": ad or o.get("ad", ""), "renk": dict(o["renk"]), "baslik": o["yazi"]["baslik"]["aile"], "govde": o["yazi"]["govde"]["aile"]}


def gorunus_ozeti(v: "Video") -> dict | None:
    """Videonun etkin görünüşü: renkler + başlık/gövde yazısı. Eski videolarda stil paketinden okunur."""
    o = v.gorunus_secimi
    if o:
        return secenek_ozeti(o, v.gorunus_etiketi)
    if v.gorunus_modu.startswith("paket:"):
        st = v.gorunus_modu[6:]
        R, F = stil_renkleri(st), _paket_fontlari(st)
        if R:
            return {"ad": f"stil {st}", "renk": R, "baslik": F.get("baslik"), "govde": F.get("govde")}
    return None


def gorunus_renkleri(v: "Video") -> dict:
    """Etkin görünüşün renkleri (kontrast ölçümü için)."""
    z = gorunus_ozeti(v)
    return z["renk"] if z else {}


def _lab(h: str):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    X = (0.4124 * c[0] + 0.3576 * c[1] + 0.1805 * c[2]) / 0.95047
    Y = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    Z = (0.0193 * c[0] + 0.1192 * c[1] + 0.9505 * c[2]) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))


def renk_farki(a: str, b: str) -> float:
    """CIE76 ΔE: < 12 aynı renk ailesi gibi okunur."""
    return float(np.linalg.norm(np.subtract(_lab(a), _lab(b))))


def benzerlik(a: dict, b: dict) -> list[str]:
    """İki görünüş özetinin ortak noktaları. İki ya da daha fazlası = izleyici aynı filmi izliyormuş gibi hisseder."""
    m = []
    if renk_farki(a["renk"]["arka"], b["renk"]["arka"]) < 12:
        m.append("zemin rengi")
    if renk_farki(a["renk"]["vurgu"], b["renk"]["vurgu"]) < 20:
        m.append("vurgu rengi")
    if a.get("baslik") and a.get("baslik") == b.get("baslik"):
        m.append(f"başlık yazısı ({a['baslik']})")
    if a.get("govde") and a.get("govde") == b.get("govde"):
        m.append(f"gövde yazısı ({a['govde']})")
    return m


def diger_gorunusler(v: "Video") -> list[tuple[str, dict]]:
    """Karşılaştırma için öteki videoların görünüşleri: arşivdekiler, deneme filmleri (deneme_*) ve aynı seriden olanlar hariç."""
    out = []
    for d in sorted((ROOT / "videos").iterdir()):
        if not d.is_dir() or d.name == v.id or d.name.startswith("deneme_") or not (d / "script.json").exists():
            continue
        w = load(d.name)
        if w.script.get("arsiv") or (v.seri_anahtari and w.seri_anahtari == v.seri_anahtari):
            continue
        z = gorunus_ozeti(w)
        if z:
            out.append((w.id, z))
    return out


# ---------------------------------------------------------------- Claude ayarları (panel → "Claude ayarları")
CLAUDE_AYAR = ROOT / "panel" / "claude_ayarlari.json"
CLAUDE_ASAMALAR = {
    "plan": "Plan: fikir havuzu, üç yol ve kanca kareleri",
    "plan_tamamla": "Planı tamamlama: seçtiğin yolda brief ve senaryo (boşsa plan ayarı)",
    "uretim": "Üretim: sahne kodu, ses, inceleme ve onarım, teslim",
    "degisiklik": "Değişiklik: senin istediğin düzeltmeler",
    "elestiri": "Kör eleştiri: filmi hiç görmemiş eleştirmen",
    "referans": "Katalog: yüklediğin referanstan ya da bir filmin dilinden seçenek çıkarma",
    "analitik": "İzleyici raporu: yayın sonrası rapordan hipotez ve öneri (boşsa değişiklik ayarı)",
}
CLAUDE_YEDEK = {"plan_tamamla": "plan", "analitik": "degisiklik"}  # ayarı boşsa bu aşamanın ayarı kullanılır
CLAUDE_MODELLER = {"claude-fable-5-1": "Fable 5.1", "claude-opus-5-5": "Opus 5.5", "claude-sonnet-5-5": "Sonnet 5.5", "claude-haiku-5-5": "Haiku 5.5"}
CLAUDE_EFORLAR = {"low": "düşük", "medium": "orta", "high": "yüksek", "xhigh": "çok yüksek", "max": "en yüksek"}


def claude_ayarlari() -> dict:
    d = jload(CLAUDE_AYAR) if CLAUDE_AYAR.exists() else {}
    return {a: {"model": (d.get(a) or {}).get("model", ""), "efor": (d.get(a) or {}).get("efor", "")} for a in CLAUDE_ASAMALAR}


def claude_bayraklari(asama: str, video: dict | None = None) -> list[str]:
    """Model ve efor bayrakları. Öncelik: videoya özel seçim (istek formunda) > aşama ayarı (Claude ayarları) > Claude Code varsayılanı."""
    A = claude_ayarlari()
    a = dict(A.get(asama, {}))
    for k in ("model", "efor"):
        if not a.get(k) and asama in CLAUDE_YEDEK:  # ayarı boş aşama yedeğinin ayarını kullanır (plan_tamamla → plan)
            a[k] = (A.get(CLAUDE_YEDEK[asama]) or {}).get(k, "")
    for k in ("model", "efor"):
        if (video or {}).get(k):
            a[k] = video[k]
    out = []
    if re.fullmatch(r"[A-Za-z0-9._\-\[\]]{2,60}", a.get("model") or ""):
        out += ["--model", a["model"]]
    if a.get("efor") in CLAUDE_EFORLAR:
        out += ["--effort", a["efor"]]
    return out


def kontrast(a: str, b: str) -> float:
    """WCAG kontrast oranı (1–21)."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


STILL_PAY = 0.4  # gürültü tabanının bu kadar üstündeki kare farkı "kıpırdıyor" sayılır (90×160 gri, 0–255)


def still_threshold(motion: np.ndarray) -> float:
    """Videonun kendi gürültü tabanına göre eşik. Sabit eşik encode'a bağlıydı: finalde korunan gren
    ortalama farkı hiç düşürmüyor, kaba kurguda düşürüyordu (ogrenimler #13). Taban = farkların %10'luk dilimi."""
    m = np.asarray(motion)[1:]
    return float(np.percentile(m, 10)) + STILL_PAY if len(m) else STILL_PAY


def still_runs(motion: np.ndarray, min_sec: float, fps=FPS):
    """Görüntünün donuk kaldığı aralıklar [(başlangıç karesi, bitiş karesi)], min_sec'ten uzun olanlar."""
    moving = np.asarray(motion) >= still_threshold(motion)
    runs, s = [], None
    for i in range(1, len(motion) + 1):
        quiet = i < len(motion) and not moving[i]
        if quiet and s is None:
            s = i
        elif not quiet and s is not None:
            if (i - s) / fps > min_sec:
                runs.append((s, i))
            s = None
    return runs


def probe(mp4: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(mp4)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


PLACEHOLDER = re.compile(r"\[[^\]\n]{2,}\](?!\()")  # [doldurulacak alan]; markdown bağlantıları hariç


def kaynak_durumu(v: Video) -> dict | None:
    """kaynaklar.md iddia tablosundaki durumları sayar (yalnız tablo satırları)."""
    k = v.dir / "kaynaklar.md"
    if not k.exists():
        return None
    rows = [ln for ln in k.read_text().splitlines() if ln.startswith("|") and not set(ln) <= set("|-: ")][1:]
    return {"ok": sum("✅" in r for r in rows), "warn": sum("⚠️" in r for r in rows), "bad": sum("❌" in r for r in rows),
            "bos": sum(bool(PLACEHOLDER.search(r)) for r in rows), "toplam": len(rows)}


def varlik_durumu(v: Video) -> dict:
    """varliklar.md ↔ public/<id>/varliklar/ ↔ koddaki staticFile('<id>/varliklar/...') başvuruları.
    Eksik varlık bir engeldir: inandırıcı bir sahtesi çizilmez (CLAUDE.md kural 2)."""
    md = v.dir / "varliklar.md"
    listed, onay = {}, {}
    if md.exists():
        rows = [ln for ln in md.read_text().splitlines() if ln.startswith("|") and not set(ln) <= set("|-: ")][1:]
        for r in rows:
            cells = [c.strip().strip("`") for c in r.strip("|").split("|")]
            if len(cells) >= 2 and cells[1] and not PLACEHOLDER.search(r):
                listed[cells[1]] = r
                onay[cells[1]] = "✅" in r
    vdir = v.pub / "varliklar"
    present = {str(p.relative_to(v.pub)) for p in vdir.rglob("*") if p.is_file() and not p.name.startswith(".")} if vdir.exists() else set()
    refs = set()
    src = ROOT / "src" / v.script.get("kod", v.id)
    if src.exists():
        for f in src.rglob("*.ts*"):
            for m in re.finditer(r"staticFile\(\s*['\"`]([^'\"`$]+)['\"`]", f.read_text()):
                if m.group(1).startswith(f"{v.id}/varliklar/"):
                    refs.add(m.group(1)[len(v.id) + 1:])
    hfd = ROOT / "hf" / v.id
    if v.motor == "hyperframes" and hfd.exists():  # HTML'de varliklar/<dosya> (hf/<id>/varliklar → public/<id>/varliklar)
        for f in [hfd / "index.html", *(hfd / "compositions").rglob("*.html")]:
            if f.exists():
                refs |= {"varliklar/" + m.group(1) for m in re.finditer(r"""["'(]varliklar/([^"')?#\s]+)""", f.read_text())}
    bd = ROOT / "blender" / v.id
    if v.motor == "blender" and bd.exists():  # sahne kodunda varliklar/<dosya> (doku, görsel, model)
        for f in bd.rglob("*.py"):
            t = f.read_text()
            refs |= {"varliklar/" + m.group(1) for m in re.finditer(r"""["']varliklar/([^"'?#\s]+)""", t)}
            refs |= {"varliklar/" + m.group(1) for m in re.finditer(r"""\bvarlik\(\s*["']([^"']+)["']""", t)}  # kit.varlik("ad")
    need = set(listed) | refs
    return {"liste": len(listed),
            "eksik": sorted(x for x in need if not (v.pub / x).exists()),
            "onaysiz": sorted(x for x in listed if not onay[x]),
            "listesiz": sorted(x for x in (present | refs) if x not in listed)}


def motion_size(w: int, h: int):
    """Hareket eğrisi için küçültme boyutu: ~14 400 piksel, en-boy korunur (90×160 dikeyde)."""
    k = (14400 / (w * h)) ** 0.5
    return int(round(w * k / 2) * 2), int(round(h * k / 2) * 2)


def latest_review_dir(v: Video) -> Path | None:
    d = v.dir / "inceleme"
    if not d.exists():
        return None
    vs = sorted((p for p in d.iterdir() if p.is_dir() and re.fullmatch(r"v\d+", p.name)), key=lambda p: int(p.name[1:]))
    return vs[-1] if vs else None


def next_review_dir(v: Video) -> Path:
    last = latest_review_dir(v)
    n = int(last.name[1:]) + 1 if last else 1
    return v.dir / "inceleme" / f"v{n}"
