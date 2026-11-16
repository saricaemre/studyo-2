"""Yerel modeller (./st derinlik, ./st maske): gerçek görüntünün derinlik haritası ve alfa maskesi. Bir kez üretilir, dondurulur (sha256).

Kare t'nin saf fonksiyonu kalır (kural 8): model çizimde değil, burada bir kez çalışır; motor yalnız dondurulmuş dosyayı okur.
Lisans: yalnız Apache 2.0 ve MIT ağırlıklar (yol haritası 3b). Ölçümler (M4, 16 GB, 2026-10-26) studio/README.md → Gerçek görüntü.

Derinlik  Depth Anything V2 Small (Apache 2.0, transformers; ilk kullanımda ~100 MB Hugging Face önbelleğine). Kısa kenar 518 piksel,
          MPS'te ~0,18 sn/kare. Çıktı göreli derinliktir: beyaz = yakın, siyah = uzak. Videoda kareler arası titremeyi azaltmak için her kare
          bir öncekine ölçek + kaymayla hizalanır, sonra yumuşatılır; bütün klip tek aralıkla 16 bite yayılır.
          Depth Anything 3 Small/Base da Apache 2.0, ama resmî paketi xformers ve numpy<2 istiyor (kurulmuyor); Apple Depth Pro'nun ağırlık
          lisansı (apple-amlr) yalnız araştırma için: kullanılmaz.
Maske     insan (varsayılan): HyperFrames remove-background (u2net_human_seg, CoreML; yeni bağımlılık yok, ~0,22 sn/kare). Yalnız insanı tanır.
          nesne (--kutu x0,y0,x1,y1, 0–1): SAM 2.1 tiny (Apache 2.0, transformers + torchvision; ilk kullanımda ~160 MB), videoda ilk karedeki
          kutudan bütün kareye yayılır, ~1,5 sn/kare. BiRefNet (MIT) Hugging Face'ten uzak kod çalıştırmak istiyor: kullanılmadı.
Dosyalar  asıl (dondurulmuş, videos/<id>/goruntu/<ad>/): görselde 16 bit PNG (derinlik) / 8 bit PNG (maske), videoda kayıpsız FFV1 MKV.
          motor kopyası (public/<id>/varliklar/goruntu/): görselde PNG, videoda 8 bit gri H.264 (Remotion useOffthreadVideoTexture okur).
Bellek    16 GB'ta aynı anda tek ağır yerel iş: out/_kilit/yerel_model.lock (ikinci iş sırada bekler).
"""
import contextlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

import ortak as O

DERINLIK_MODELI = "depth-anything/Depth-Anything-V2-Small-hf"
SAM_MODELI = "facebook/sam2.1-hiera-tiny"
KISA = 518                       # Depth Anything'in eğitim çözünürlüğü (kısa kenar, 14'ün katı)
SAM_KISA = 540                   # SAM'e verilen karelerin kısa kenarı (bellek: 16 GB); maske asıl boyuta büyütülür
HF_SURUM = "0.9.17"              # hf.py ile aynı sabit sürüm
KILIT = O.ROOT / "out" / "_kilit" / "yerel_model.lock"
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


@contextlib.contextmanager
def kilit(ne: str):
    """Aynı anda tek ağır yerel model (16 GB: derinlik, SAM, ACE-Step, Blender birlikte takasa düşer). İkinci iş sırada bekler."""
    import fcntl
    KILIT.parent.mkdir(parents=True, exist_ok=True)
    with open(KILIT, "w") as k:
        try:
            fcntl.flock(k, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"→ başka bir yerel model işi sürüyor; {ne} sırada bekliyor…", flush=True)
            fcntl.flock(k, fcntl.LOCK_EX)
        yield


def cihaz() -> str:
    import torch
    return "mps" if torch.backends.mps.is_available() else "cpu"


def _sure(bas: float, n: int) -> dict:
    s = time.time() - bas
    return {"saniye": round(s, 2), "kare": n, "kare_basina": round(s / max(1, n), 3)}


# ---------------------------------------------------------------- kare okuma ve yazma (ffmpeg)
def kareleri_oku(dosya: Path, en: int, boy: int, gri=False):
    """Videonun kareleri (n, boy, en[, 3]) uint8, kaynak çözünürlüğünde (bellek için akış halinde)."""
    kanal = 1 if gri else 3
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(dosya), "-f", "rawvideo", "-pix_fmt", "gray" if gri else "rgb24", "-"],
                         stdout=subprocess.PIPE)
    boyut = en * boy * kanal
    while True:
        b = p.stdout.read(boyut)
        if len(b) < boyut:
            break
        a = np.frombuffer(b, np.uint8)
        yield a.reshape(boy, en) if gri else a.reshape(boy, en, 3)
    p.wait()


def _yazici(cikti: Path, en: int, boy: int, fps: float, pix: str, kodek: list[str]):
    cikti.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix, "-s", f"{en}x{boy}", "-r", f"{fps:g}", "-i", "-",
                             *kodek, "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", str(cikti)], stdin=subprocess.PIPE)


def kayipsiz(cikti: Path, kareler, en: int, boy: int, fps: float, bit16: bool):
    """Asıl: FFV1 (kayıpsız) gri MKV; 16 bit derinlik ya da 8 bit maske."""
    w = _yazici(cikti, en, boy, fps, "gray16le" if bit16 else "gray", ["-c:v", "ffv1", "-level", "3", "-g", "1", "-pix_fmt", "gray16le" if bit16 else "gray"])
    for k in kareler:
        w.stdin.write((k.astype("<u2") if bit16 else k.astype(np.uint8)).tobytes())
    w.stdin.close()
    if w.wait():
        raise SystemExit(f"ffmpeg yazamadı: {cikti.name}")


def motor_videosu(asil: Path, cikti: Path, fps: float):
    """Motor kopyası: asıl gri MKV → 8 bit gri H.264 (yuv420p, çift boyut). Tarayıcı ve Remotion'un kare çıkarıcısı okur."""
    cikti.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(asil), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=bilinear,format=yuv420p",
                        "-r", f"{fps:g}", "-c:v", "libx264", "-preset", "slow", "-crf", "8", "-g", "15", "-bf", "0", "-threads", "1",
                        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-an", str(cikti)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg: " + r.stderr[-500:])


# ---------------------------------------------------------------- derinlik
def _derinlik_kur():
    import torch
    from transformers import AutoModelForDepthEstimation
    c = cihaz()
    m = AutoModelForDepthEstimation.from_pretrained(DERINLIK_MODELI).to(c).eval()
    return m, c, torch


def _hazirla(rgb: np.ndarray, torch, c):
    """Depth Anything girdisi: kısa kenar 518, iki kenar 14'ün katı, ImageNet normalleştirmesi."""
    from PIL import Image
    h, w = rgb.shape[:2]
    o = KISA / min(h, w)
    yw, yh = max(14, round(w * o / 14) * 14), max(14, round(h * o / 14) * 14)
    x = np.asarray(Image.fromarray(rgb).resize((yw, yh), Image.BICUBIC), np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    return torch.from_numpy(x.transpose(2, 0, 1)[None].copy()).to(c)


def _tahmin(m, rgb, torch, c) -> np.ndarray:
    with torch.no_grad():
        d = m(pixel_values=_hazirla(rgb, torch, c)).predicted_depth[0]
    return d.float().cpu().numpy()


def _hizala(d: np.ndarray, onceki: np.ndarray) -> np.ndarray:
    """Göreli derinliğin ölçeği ve kayması kareden kareye oynar: d'yi öncekine en küçük kareler (a·d + b) ile oturt."""
    x, y = d[::4, ::4].ravel(), onceki[::4, ::4].ravel()
    A = np.stack([x, np.ones_like(x)], 1)
    (a, b), *_ = np.linalg.lstsq(A, y, rcond=None)
    return a * d + b if a > 0 else d


def _yay(D: list[np.ndarray]) -> tuple[list[np.ndarray], tuple[float, float]]:
    """Bütün klip tek aralıkla 0–1'e (%1–%99 dilim): kareler arası parlaklık oynamaz."""
    ornek = np.concatenate([d[::8, ::8].ravel() for d in D])
    a, b = np.percentile(ornek, [1, 99])
    return [np.clip((d - a) / max(1e-6, b - a), 0, 1) for d in D], (float(a), float(b))


def derinlik_gorsel(kaynak: Path, asil: Path, motor: Path) -> dict:
    """Görsel → 16 bit PNG (asıl, model çözünürlüğünde) + motor kopyası (8 bit PNG, hafif yumuşatılmış: 2.5B'de basamak olmasın)."""
    from PIL import Image, ImageFilter
    rgb = np.asarray(Image.open(kaynak).convert("RGB"))
    with kilit("derinlik"):
        bas = time.time()
        m, c, torch = _derinlik_kur()
        yuk = time.time() - bas
        bas = time.time()
        d = _tahmin(m, rgb, torch, c)
        sure = _sure(bas, 1)
    (d01,), aralik = _yay([d])
    asil.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((d01 * 65535).round().astype(np.uint16)).save(asil)
    motor.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((d01 * 255).round().astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(1.2)).save(motor, optimize=False)
    return {"model": DERINLIK_MODELI, "cihaz": c, "en": d.shape[1], "boy": d.shape[0], "aralik": aralik, "yukleme_sn": round(yuk, 1), **sure}


def derinlik_video(kaynak: Path, en: int, boy: int, fps: float, asil: Path, motor: Path, yumusatma: float = 0.35) -> dict:
    """Video → kare kare derinlik, öncekine hizalanmış ve yumuşatılmış (titremesin) → 16 bit FFV1 (asıl) + 8 bit gri H.264 (motor)."""
    with kilit("derinlik"):
        bas = time.time()
        m, c, torch = _derinlik_kur()
        yuk = time.time() - bas
        bas = time.time()
        D, onceki = [], None
        for i, rgb in enumerate(kareleri_oku(kaynak, en, boy)):
            d = _tahmin(m, rgb, torch, c)
            if onceki is not None:
                d = (1 - yumusatma) * _hizala(d, onceki) + yumusatma * onceki
            D.append(d)
            onceki = d
            if i and i % 60 == 0:
                print(f"   derinlik: {i} kare · {(time.time() - bas) / i:.2f} sn/kare", flush=True)
        sure = _sure(bas, len(D))
    if not D:
        raise SystemExit(f"kare okunamadı: {kaynak}")
    D01, aralik = _yay(D)
    h, w = D01[0].shape
    kayipsiz(asil, ((d * 65535).round() for d in D01), w, h, fps, bit16=True)
    motor_videosu(asil, motor, fps)
    return {"model": DERINLIK_MODELI, "cihaz": c, "en": w, "boy": h, "kare": len(D), "aralik": aralik, "yumusatma": yumusatma,
            "yukleme_sn": round(yuk, 1), **sure}


# ---------------------------------------------------------------- maske
def _hf_arka_plan(kaynak: Path, cikti: Path) -> dict:
    """HyperFrames remove-background (u2net_human_seg). Görselde PNG, videoda ProRes 4444 (alfa kolay ayrılır)."""
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1"}
    r = subprocess.run(["npx", "--yes", f"hyperframes@{HF_SURUM}", "remove-background", str(kaynak), "-o", str(cikti), "--json"],
                       cwd=O.ROOT, capture_output=True, text=True, env=env)
    js = next((ln for ln in r.stdout.splitlines()[::-1] if ln.startswith("{")), None)
    if r.returncode or not js or not cikti.exists():
        raise SystemExit("hyperframes remove-background başarısız:\n" + (r.stdout + r.stderr)[-1500:])
    return json.loads(js)


def _alfa_kareleri(mov: Path, en: int, boy: int):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(mov), "-vf", "alphaextract,format=gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(en * boy)
        if len(b) < en * boy:
            break
        yield np.frombuffer(b, np.uint8).reshape(boy, en)
    p.wait()


def _sam_kur(video: bool):
    import torch
    from transformers import Sam2Model, Sam2Processor, Sam2VideoModel, Sam2VideoProcessor
    c = cihaz()
    if video:
        return Sam2VideoModel.from_pretrained(SAM_MODELI).to(c, dtype=torch.float32).eval(), Sam2VideoProcessor.from_pretrained(SAM_MODELI), c, torch
    return Sam2Model.from_pretrained(SAM_MODELI).to(c).eval(), Sam2Processor.from_pretrained(SAM_MODELI), c, torch


def _kucult(rgb: np.ndarray, kisa: int) -> np.ndarray:
    from PIL import Image
    h, w = rgb.shape[:2]
    if min(h, w) <= kisa:
        return rgb
    o = kisa / min(h, w)
    return np.asarray(Image.fromarray(rgb).resize((round(w * o), round(h * o)), Image.BILINEAR))


def _doldur(m: np.ndarray) -> np.ndarray:
    """Nesne maskesinin iç delikleri (kâsenin içi, gölgeli yüzey) doldurulur: özne bütün bir siluettir."""
    from scipy import ndimage
    return ndimage.binary_fill_holes(m > 0).astype(np.uint8) * 255


def _buyut(m: np.ndarray, en: int, boy: int) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.fromarray(m).resize((en, boy), Image.BILINEAR)) if m.shape != (boy, en) else m


def maske_gorsel(kaynak: Path, asil: Path, motor: Path, kutu: list[float] | None) -> dict:
    from PIL import Image
    rgb = np.asarray(Image.open(kaynak).convert("RGB"))
    boy, en = rgb.shape[:2]
    with kilit("maske"):
        bas = time.time()
        if kutu is None:
            tmp = asil.with_name("_hf_maske.png")
            bilgi = _hf_arka_plan(kaynak, tmp)
            a = np.asarray(Image.open(tmp).convert("RGBA"))[..., 3]
            tmp.unlink(missing_ok=True)
            yontem = {"yontem": "insan", "model": "u2net_human_seg (HyperFrames remove-background)", "saglayici": bilgi.get("provider")}
        else:
            m, p, c, torch = _sam_kur(False)
            k = _kucult(rgb, SAM_KISA)
            kh, kw = k.shape[:2]
            g = p(images=k, input_boxes=[[[kutu[0] * kw, kutu[1] * kh, kutu[2] * kw, kutu[3] * kh]]], return_tensors="pt").to(c)
            with torch.no_grad():
                o = m(**g, multimask_output=False)
            mm = p.post_process_masks(o.pred_masks.cpu(), g["original_sizes"].cpu())[0][0, 0].numpy()
            a = _buyut(_doldur(mm), en, boy)
            yontem = {"yontem": "nesne", "model": SAM_MODELI, "kutu": kutu, "cihaz": c}
        sure = _sure(bas, 1)
    asil.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a.astype(np.uint8), "L").save(asil)
    motor.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(asil, motor)
    Image.fromarray(gizleme_maskesi([a.astype(np.uint8)])[0], "L").save(motor.with_name("maske_genis.png"))
    return {**yontem, "en": en, "boy": boy, "alan": round(float((a > 127).mean()), 4), **sure}


def maske_video(kaynak: Path, en: int, boy: int, fps: float, asil: Path, motor: Path, kutu: list[float] | None, kutu_kare: int = 0) -> dict:
    with kilit("maske"):
        bas = time.time()
        if kutu is None:
            tmp = asil.with_name("_hf_maske.mov")
            bilgi = _hf_arka_plan(kaynak, tmp)
            A = list(_alfa_kareleri(tmp, en, boy))
            tmp.unlink(missing_ok=True)
            yontem = {"yontem": "insan", "model": "u2net_human_seg (HyperFrames remove-background)", "saglayici": bilgi.get("provider")}
        else:
            m, p, c, torch = _sam_kur(True)
            K = [_kucult(f, SAM_KISA) for f in kareleri_oku(kaynak, en, boy)]
            kh, kw = K[0].shape[:2]
            ses = p.init_video_session(video=K, inference_device=c, dtype=torch.float32)
            p.add_inputs_to_inference_session(inference_session=ses, frame_idx=kutu_kare, obj_ids=1,
                                              input_boxes=[[[kutu[0] * kw, kutu[1] * kh, kutu[2] * kw, kutu[3] * kh]]])
            M = {}
            with torch.no_grad():
                m(inference_session=ses, frame_idx=kutu_kare)
                for yon in ((False, True) if kutu_kare else (False,)):  # kutu ortadaki bir karedeyse önce ileri, sonra geri
                    for o in m.propagate_in_video_iterator(ses, reverse=yon):
                        mm = p.post_process_masks([o.pred_masks], original_sizes=[[kh, kw]], binarize=True)[0][0, 0].cpu().numpy()
                        M[o.frame_idx] = _doldur(mm)
            A = [_buyut(M.get(i, np.zeros((kh, kw), np.uint8)), en, boy) for i in range(len(K))]
            yontem = {"yontem": "nesne", "model": SAM_MODELI, "kutu": kutu, "kutu_kare": kutu_kare, "cihaz": c}
        sure = _sure(bas, len(A))
    if not A:
        raise SystemExit("maske karesi çıkmadı")
    kayipsiz(asil, A, en, boy, fps, bit16=False)
    motor_videosu(asil, motor, fps)
    genis = asil.with_name("maske_genis.mkv")
    kayipsiz(genis, gizleme_maskesi(A), en, boy, fps, bit16=False)
    motor_videosu(genis, motor.with_name("maske_genis.mp4"), fps)
    genis.unlink(missing_ok=True)  # motor kopyası yeter: asıl maskeden belirlenimli türer
    alan = [float((a[::4, ::4] > 127).mean()) for a in A]
    return {**yontem, "en": en, "boy": boy, "kare": len(A), "alan": round(float(np.mean(alan)), 4), "bos_kare": int(sum(x < 0.001 for x in alan)),
            "zayif_kare": zayif_kareler(alan)[:30], **sure}


GIZLE_KARE = 4          # gizleme maskesi zamanda ±4 kare (model bir iki karede kişiyi kaçırsa da mozaik açık kalmasın)
GIZLE_PAY = 0.025       # ve uzayda kısa kenarın %2,5'i kadar genişler (saç, el, kenar)


def gizleme_maskesi(A: list[np.ndarray]) -> list[np.ndarray]:
    """Yüz gizleme (Stilize gizle) için genişletilmiş maske: zamanda en büyük (±GIZLE_KARE) ve uzayda genişletme. Küçük çözünürlükte hesaplanır."""
    from PIL import Image
    from scipy import ndimage
    boy, en = A[0].shape
    o = 4
    k = np.stack([a[::o, ::o] for a in A])
    r = max(1, round(GIZLE_PAY * min(en, boy) / o))
    k = ndimage.maximum_filter(k, size=(2 * GIZLE_KARE + 1 if len(A) > 1 else 1, 2 * r + 1, 2 * r + 1))
    return [np.asarray(Image.fromarray(x).resize((en, boy), Image.BILINEAR)) for x in k]


def zayif_kareler(alan: list[float]) -> list[int]:
    """Maskenin komşularına göre ani düştüğü kareler (model kişiyi kaçırmış olabilir): ortanca(±8) yarısının altı."""
    a = np.array(alan)
    return [i for i in range(len(a)) if (m := np.median(a[max(0, i - 8):i + 9])) > 0.01 and a[i] < 0.5 * m]


def maske_dizisi(asil: Path, en: int, boy: int, olcek: int = 4):
    """Kadraj için maske kareleri (küçültülmüş): asıl FFV1 ya da PNG."""
    from PIL import Image
    if asil.suffix == ".png":
        a = np.asarray(Image.open(asil).convert("L"))
        yield a[::olcek, ::olcek]
        return
    for a in kareleri_oku(asil, en, boy, gri=True):
        yield a[::olcek, ::olcek]
