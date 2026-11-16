"""Kamera takibi (./st takip): Blender arka planda (bpy) özellik bulur, izler, kamerayı çözer; zemini ve ölçeği kurar; çözümü dondurulacak
JSON olarak yazar. Stüdyo (pipeline/takip.py) çalıştırır; elle çağırmaya gerek yok:

  blender -b --factory-startup --python-exit-code 1 --python blender/takip/coz.py -- \
      --video videos/<id>/goruntu/<ad>/ara.mp4 --cikti videos/<id>/takip/<ad>/ --ayar '{"yukseklik": 1.5}' [--blend iz.blend]

Yöntem (ölçüm: ../../../yol-haritasi/4-sansasyon-araclari.md → 4a; zanaat §10):
  1. Özellik bulma her `aralik` karede (FAST), yakın tekrarlar silinir; her yeni iz ileri ve geri izlenir (affine, anahtar kareye göre eşleşme,
     korelasyon ≥ 0,85). Kısa izler silinir.
  2. Aykırı iz süzgeci: ardışık kare çiftlerinde temel matris RANSAC'ı (Sampson ≤ 2 px); çiftlerin çoğunda aykırı kalan iz silinir
     (yaprak, gölge kenarı, önden geçen direğin kenarı: kayan izler). Tohumlu: aynı video aynı çözümü verir.
  3. Anahtar kare çifti: ortak izi yeterli çiftlerden homografiden sapması (paralaks) en büyük olan.
  4. Odak: sabit odakla çözüm, kaba tarama + altın oran araması (libmv'nin odak inceltmesi yanlış başlangıçta ıraksıyor). Kullanıcı ya da
     videonun üst verisi odağı verdiyse arama onun çevresinde.
  5. Temizlik: her izin her karesindeki yeniden izdüşüm hatası ölçülür; büyük hatalı işaretler susturulur, susturulmuş izler silinir; her karede
     en az `kapsam` iz kalır. Çözüm hedefin altına inene dek tekrarlanır. Sonra odak + mercek bozulması (k1, k2) inceltilir, hata azalmazsa geri alınır.
  6. Zemin: üç boyutlu noktalara RANSAC ile düzlem (normali kameranın yukarısına yakın, kameranın altında); dünya Z = zemin normali,
     Y = yürüyüş yönü, başlangıç = ilk karede kameranın ayağı. Ölçek: kameranın zeminden ortalama yüksekliği `yukseklik` metre (varsayılan 1,5).
Çıktı: cozum.json (her kare için kamera matrisi, odak, bozulma, kare başına hata, zemin, ölçek, noktalar) + iz.blend (izler ve çözüm:
elle düzeltmek için Blender'da açılır; ./st takip <id> <ad> ac). iz.blend son klasörüne yazılır (--blend-cikti): içindeki çekimin yolu
göreli; dosya başka klasöre taşınırsa çekim bulunamaz ve Blender klibi 256×256 sanar (odak milimetresi bozulur).
Elle iz: --blend verilirse izleme yapılmaz; kayıttaki izler ve (varsa) çözüm kullanılır, yalnız 4–6 yapılır (--elle: çözüm aynen alınır).
"""
import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True)
ap.add_argument("--cikti", required=True)
ap.add_argument("--ayar", default="{}")
ap.add_argument("--blend", default="")
ap.add_argument("--blend-cikti", default="")   # iz.blend nereye: çekimin göreli yolu bu klasöre göre yazılır (taşınırsa kayar)
ap.add_argument("--elle", action="store_true")
A = ap.parse_args(argv)
P = {"desen": 21, "arama": 101, "model": "Affine", "eslesme": "KEYFRAME", "kor": 0.85, "esik": 0.1, "mesafe": 40, "aralik": 10,
     "en_kisa": 12, "epipolar_px": 2.0, "epipolar_oran": 0.3, "hedef": 1.0, "kapsam": 12, "odak": None, "odak_aralik": [18.0, 120.0],
     "yukseklik": 1.5, "bas": 0, "son": 0, "tohum": 7, "bozulma": True, **json.loads(A.ayar)}
CIKTI = Path(A.cikti)
CIKTI.mkdir(parents=True, exist_ok=True)
T0 = time.time()
rng = np.random.default_rng(P["tohum"])


def yaz(etiket, d):
    print(f"ST_{etiket} " + json.dumps(d, ensure_ascii=False), flush=True)


def adim(metin):
    yaz("ADIM", {"metin": metin, "sn": round(time.time() - T0, 1)})


# ---------------------------------------------------------------- klip ve klip düzenleyicisi (arka planda da tek pencere var)
if A.blend:
    # Blender dosyayla başlatılır (pipeline/takip.py → _blender): betiğin içinden open_mainfile ile açılan klibin filmi henüz okunmamış
    # oluyor (boyutu 256×256 ve kare hızı 0 sanılıyor; odak milimetresi buna göre yanlış çıkıyordu).
    if Path(bpy.data.filepath or "/").resolve() != Path(A.blend).resolve():
        raise SystemExit("elle iz: Blender iz.blend ile başlatılmalı (blender -b iz.blend --python coz.py …)")
    clip = bpy.data.movieclips[0]
    if tuple(clip.size) != tuple(bpy.data.movieclips.load(str(Path(A.video).resolve()), check_existing=True).size):
        raise SystemExit("elle iz: iz.blend'deki klip takip edilen çekimle aynı boyutta değil")
else:
    clip = bpy.data.movieclips.load(str(Path(A.video).resolve()))
W, H = clip.size
NK = clip.frame_duration
BAS = 1 + int(P["bas"])
SON = min(NK, int(P["son"])) if P["son"] else NK   # ffprobe yuvarlaması kareyi bir fazla sayabiliyor: klibin kendisi esas
if not (1 <= BAS < SON <= NK):
    raise SystemExit(f"aralık geçersiz: kare {BAS - 1}–{SON - 1} (klip {NK} kare)")
N = SON - BAS + 1
sc = bpy.context.scene
sc.frame_start, sc.frame_end = BAS, SON
sc.render.fps = int(round(clip.fps)) or 30
win = bpy.context.window_manager.windows[0]
ekran = win.screen
alan = ekran.areas[0]
alan.type = "CLIP_EDITOR"
sp = alan.spaces.active
sp.clip = clip
bolge = [r for r in alan.regions if r.type == "WINDOW"][0]
OV = dict(window=win, screen=ekran, area=alan, region=bolge, space_data=sp, edit_movieclip=clip)
tr = clip.tracking
s = tr.settings
ob = tr.objects[0]
kam = tr.camera
kam.sensor_width = 36.0
kam.units = "MILLIMETERS"
kam.distortion_model = "POLYNOMIAL"


def git(f):
    sc.frame_set(f)
    sp.clip_user.frame_current = f


def sec(izler):
    S = {t.name for t in izler}
    for t in tr.tracks:
        t.select = t.name in S


def sil(izler):
    if izler:
        sec(izler)
        bpy.ops.clip.delete_track()


def isaretler(t):
    return [m for m in t.markers if not m.mute and BAS <= m.frame <= SON]


def kapsam():
    say = np.zeros(NK + 2, int)
    for t in tr.tracks:
        for m in isaretler(t):
            say[m.frame] += 1
    return say


# ---------------------------------------------------------------- 1. izleme
def izle():
    s.default_pattern_size, s.default_search_size = P["desen"], P["arama"]
    s.default_motion_model, s.default_pattern_match = P["model"], P["eslesme"]
    s.default_correlation_min, s.default_margin = P["kor"], 12
    s.use_default_brute = s.use_default_normalization = True
    for f0 in range(BAS, SON + 1, P["aralik"]):
        git(f0)
        once = {t.name for t in tr.tracks}
        bpy.ops.clip.detect_features(placement="FRAME", margin=20, threshold=P["esik"], min_distance=P["mesafe"])
        yeni = [t for t in tr.tracks if t.name not in once]
        eski = [m.co for t in tr.tracks if t.name in once for m in [t.markers.find_frame(f0)] if m and not m.mute]
        if eski and yeni:
            E = np.array([(c[0] * W, c[1] * H) for c in eski])
            yakin = [t for t in yeni if np.min(((E - (t.markers.find_frame(f0).co[0] * W, t.markers.find_frame(f0).co[1] * H)) ** 2).sum(1))
                     < (0.6 * P["mesafe"]) ** 2]
            sil(yakin)
            yeni = [t for t in tr.tracks if t.name not in once]
        if not yeni:
            continue
        sec(yeni)
        bpy.ops.clip.track_markers(backwards=False, sequence=True)
        git(f0)
        sec(yeni)
        bpy.ops.clip.track_markers(backwards=True, sequence=True)
        yaz("IZ", {"kare": f0 - BAS, "toplam": N, "iz": len(tr.tracks)})
    kisa = [t for t in tr.tracks if len(isaretler(t)) < P["en_kisa"]]
    sil(kisa)


# ---------------------------------------------------------------- 2. aykırı iz süzgeci (temel matris RANSAC'ı)
def noktalar():
    return {t.name: {m.frame: (m.co[0] * W, m.co[1] * H) for m in isaretler(t)} for t in tr.tracks}


def _normalle(p):
    c = p.mean(0)
    d = np.sqrt(((p - c) ** 2).sum(1)).mean()
    k = math.sqrt(2) / max(d, 1e-9)
    T = np.array([[k, 0, -k * c[0]], [0, k, -k * c[1]], [0, 0, 1]])
    return np.c_[p, np.ones(len(p))] @ T.T, T


def _temel(a, b):
    na, Ta = _normalle(a)
    nb, Tb = _normalle(b)
    M = np.stack([nb[:, 0] * na[:, 0], nb[:, 0] * na[:, 1], nb[:, 0], nb[:, 1] * na[:, 0], nb[:, 1] * na[:, 1], nb[:, 1], na[:, 0], na[:, 1],
                  np.ones(len(a))], 1)
    F = np.linalg.svd(M)[2][-1].reshape(3, 3)
    U, S, Vt = np.linalg.svd(F)
    S[2] = 0
    return Tb.T @ (U @ np.diag(S) @ Vt) @ Ta


def _sampson(F, a, b):
    xa, xb = np.c_[a, np.ones(len(a))], np.c_[b, np.ones(len(b))]
    Fa, Fb = xa @ F.T, xb @ F
    return np.sqrt(np.sum(xb * Fa, 1) ** 2 / np.maximum(Fa[:, 0] ** 2 + Fa[:, 1] ** 2 + Fb[:, 0] ** 2 + Fb[:, 1] ** 2, 1e-12))


def _ransac(a, b, esik, n=400):
    en = None
    for _ in range(n):
        i = rng.choice(len(a), 8, replace=False)
        try:
            ic = _sampson(_temel(a[i], b[i]), a, b) < esik
        except np.linalg.LinAlgError:
            continue
        if en is None or ic.sum() > en.sum():
            en = ic
    if en is not None and en.sum() >= 8:
        en = _sampson(_temel(a[en], b[en]), a, b) < esik
    return en


def epipolar():
    D = noktalar()
    kotu = {k: 0 for k in D}
    top = {k: 0 for k in D}
    d = max(4, min(10, N // 10))
    for f in range(BAS, SON - d + 1, max(2, d // 2)):
        g = f + d
        ortak = [k for k in D if f in D[k] and g in D[k]]
        if len(ortak) < 15:
            continue
        ic = _ransac(np.array([D[k][f] for k in ortak]), np.array([D[k][g] for k in ortak]), P["epipolar_px"])
        if ic is None:
            continue
        for k, i in zip(ortak, ic):
            top[k] += 1
            kotu[k] += not i
    # çok aykırı izler silinir; kapsam korunur (az izli karelerde iz kalsın)
    k = kapsam()
    adaylar = sorted((x for x in D if top[x] and kotu[x] / top[x] > P["epipolar_oran"]), key=lambda x: -kotu[x] / top[x])
    silinecek = []
    for x in adaylar:
        fr = list(D[x])
        if all(k[f] - 1 >= P["kapsam"] for f in fr):
            for f in fr:
                k[f] -= 1
            silinecek.append(x)
    sil([t for t in tr.tracks if t.name in set(silinecek)])
    return len(silinecek), len(D)


# ---------------------------------------------------------------- 3. anahtar kareler
def anahtar_sec():
    D = noktalar()
    en = None
    for d in (12, 18, 24, 30, 40, 55):
        if d >= N:
            break
        for f in range(BAS, SON - d + 1, 3):
            g = f + d
            ortak = [k for k in D if f in D[k] and g in D[k]]
            if len(ortak) < 30:
                continue
            a, b = np.array([D[k][f] for k in ortak]), np.array([D[k][g] for k in ortak])
            na, Ta = _normalle(a)
            nb, Tb = _normalle(b)
            M = np.zeros((2 * len(a), 9))
            M[0::2] = np.c_[-na[:, :2], -np.ones(len(a)), np.zeros((len(a), 3)), nb[:, :1] * na[:, :2], nb[:, :1]]
            M[1::2] = np.c_[np.zeros((len(a), 3)), -na[:, :2], -np.ones(len(a)), nb[:, 1:2] * na[:, :2], nb[:, 1:2]]
            Hm = np.linalg.inv(Tb) @ np.linalg.svd(M)[2][-1].reshape(3, 3) @ Ta
            p = np.c_[a, np.ones(len(a))] @ Hm.T
            paralaks = float(np.median(np.sqrt(((p[:, :2] / p[:, 2:3] - b) ** 2).sum(1))))
            puan = paralaks * min(1.0, len(ortak) / 120)
            if en is None or puan > en[0]:
                en = (puan, f, g, len(ortak), paralaks)
    return en


# ---------------------------------------------------------------- 4–5. çözüm, izdüşüm, temizlik
def fpx():
    return kam.focal_length / kam.sensor_width * W


def izdusum_hatalari():
    """{iz: [(kare, hata px)]}: kayıttaki kamera + nokta, Blender'ın kendi modeliyle (polinom bozulma)."""
    rec = ob.reconstruction
    C = {c.frame: np.array(c.matrix) for c in rec.cameras}
    f = fpx()
    cx, cy = kam.principal_point_pixels
    k1, k2, k3 = kam.k1, kam.k2, kam.k3
    out = {}
    for t in tr.tracks:
        if not t.has_bundle:
            continue
        P3 = np.array([*t.bundle, 1.0])
        h = []
        for m in isaretler(t):
            M = C.get(m.frame)
            if M is None:
                continue
            pc = np.linalg.inv(M) @ P3
            if pc[2] >= -1e-9:
                h.append((m.frame, 1e6))
                continue
            x, y = pc[0] / -pc[2], pc[1] / -pc[2]
            r2 = x * x + y * y
            d = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 ** 3
            u, v = f * x * d + cx, f * y * d + cy
            h.append((m.frame, float(math.hypot(u - m.co[0] * W, v - m.co[1] * H))))
        out[t.name] = h
    return out


def coz(odak=None, incelt=""):
    if odak is not None:
        kam.focal_length = odak
        kam.k1 = kam.k2 = kam.k3 = 0.0
    s.refine_intrinsics_focal_length = "f" in incelt
    s.refine_intrinsics_radial_distortion = "k" in incelt
    s.refine_intrinsics_principal_point = False
    s.refine_intrinsics_tangential_distortion = False
    bpy.ops.clip.solve_camera()
    rec = ob.reconstruction
    if not rec.is_valid:
        raise RuntimeError("çözüm geçersiz")
    return rec.average_error


def odak_ara(tablo):
    lo, hi = P["odak_aralik"]
    if P["odak"]:
        lo, hi = P["odak"] * 0.8, P["odak"] * 1.25
    izgara = list(np.geomspace(lo, hi, 7))
    for f in izgara:
        try:
            tablo.append((coz(f), float(f)))
        except RuntimeError:
            tablo.append((1e9, float(f)))
    e, f = min(tablo)
    i = izgara.index(f)
    a, b = izgara[max(0, i - 1)], izgara[min(len(izgara) - 1, i + 1)]
    for _ in range(7):
        m1, m2 = a + (b - a) * 0.382, a + (b - a) * 0.618
        try:
            e1, e2 = coz(m1), coz(m2)
        except RuntimeError:
            break
        tablo += [(e1, m1), (e2, m2)]
        if e1 < e2:
            b = m2
        else:
            a = m1
    e, f = min(tablo)
    coz(f)
    return f


def temizle(tur_sayisi=12):
    gecmis = []
    for tur in range(tur_sayisi):
        e = ob.reconstruction.average_error
        if e <= P["hedef"] * 0.6:
            break
        H_ = izdusum_hatalari()
        hepsi = [h for v in H_.values() for _, h in v if h < 1e5]
        med = statistics.median(hepsi) if hepsi else 1.0
        esik = max(P["hedef"] * 1.5, 3.0 * med)
        k = kapsam()
        sustur = []
        for ad, v in sorted(H_.items(), key=lambda x: -max([h for _, h in x[1]] or [0])):
            for f, h in sorted(v, key=lambda x: -x[1]):
                if h > esik and k[f] - 1 >= P["kapsam"]:
                    k[f] -= 1
                    sustur.append((ad, f))
        demetsiz = [t for t in tr.tracks if not t.has_bundle]
        if not sustur and not demetsiz:
            break
        for ad, f in sustur:
            m = tr.tracks[ad].markers.find_frame(f)
            if m:
                m.mute = True
        sil(demetsiz + [t for t in tr.tracks if len(isaretler(t)) < P["en_kisa"] // 2])
        try:
            e2 = coz(None)
        except RuntimeError:
            break
        gecmis.append({"tur": tur, "susturulan": len(sustur), "silinen": len(demetsiz), "esik_px": round(esik, 2), "hata": round(e2, 3), "iz": len(tr.tracks)})
        yaz("TEMIZLIK", gecmis[-1])
    return gecmis


# ---------------------------------------------------------------- 6. zemin ve ölçek
def zemin_bul(Ms, noktalar3):
    """RANSAC düzlem: normali kameranın yukarısına yakın (≤ 40°), bütün kameralar aynı yanda ve üstünde. → (n, d, içler)"""
    Pn = np.array(noktalar3)
    merkez = np.array([M[:3, 3] for M in Ms])
    yukari = np.mean([M[:3, 1] for M in Ms], 0)
    yukari /= np.linalg.norm(yukari)
    olcek = float(np.median(np.linalg.norm(Pn - merkez.mean(0), axis=1)))
    esik = 0.012 * olcek
    en = None
    for _ in range(2000):
        i = rng.choice(len(Pn), 3, replace=False)
        n = np.cross(Pn[i[1]] - Pn[i[0]], Pn[i[2]] - Pn[i[0]])
        if np.linalg.norm(n) < 1e-12:
            continue
        n /= np.linalg.norm(n)
        if n @ yukari < 0:
            n = -n
        if n @ yukari < math.cos(math.radians(40)):
            continue
        d = -n @ Pn[i[0]]
        yuk = merkez @ n + d
        if (yuk <= 0).any():
            continue
        ic = np.abs(Pn @ n + d) < esik
        if en is None or ic.sum() > en[2].sum():
            en = (n, d, ic)
    if en is None or en[2].sum() < 8:
        raise SystemExit("zemin bulunamadı: kameranın altında yeterli nokta yok (zeminde dokulu yüzey gerekir; elle: ./st takip <id> <ad> ac)")
    n, d, ic = en
    Q = Pn[ic]
    c = Q.mean(0)
    n = np.linalg.svd(Q - c)[2][-1]
    if n @ yukari < 0:
        n = -n
    d = -n @ c
    ic = np.abs(Pn @ n + d) < esik
    return n, float(d), ic, esik


def hizala(Ms, n, d, yukseklik):
    """Dünya: Z = zemin normali, Y = yürüyüş yönü, başlangıç = ilk karede kameranın ayağı; ölçek: ortalama kamera yüksekliği = yukseklik."""
    merkez = np.array([M[:3, 3] for M in Ms])
    yuk = merkez @ n + d
    s_ = yukseklik / float(np.mean(yuk))
    O_ = merkez[0] - yuk[0] * n
    ileri = merkez[-1] - merkez[0]
    ileri -= (ileri @ n) * n
    if np.linalg.norm(ileri) < 1e-3 * np.mean(yuk):   # yürüyüş yoksa (sabit, dönen kamera) ilk bakış yönü
        ileri = -Ms[0][:3, 2] - ((-Ms[0][:3, 2]) @ n) * n
    y = ileri / np.linalg.norm(ileri)
    x = np.cross(y, n)
    R = np.stack([x, y, n])    # satırlar: dünya eksenleri
    def nokta(p):
        return s_ * (R @ (np.asarray(p) - O_))
    def kamera(M):
        Y = np.eye(4)
        Y[:3, :3] = R @ M[:3, :3]
        Y[:3, 3] = nokta(M[:3, 3])
        return Y
    return s_, nokta, kamera


# ---------------------------------------------------------------- akış
def main():
    adim("klip açıldı")
    yaz("KLIP", {"en": W, "boy": H, "kare": NK, "bas": BAS - 1, "son": SON - 1, "fps": clip.fps})
    with bpy.context.temp_override(**OV):
        if not A.blend:
            izle()
            adim(f"izleme bitti: {len(tr.tracks)} iz")
            silinen, top = epipolar()
            adim(f"aykırı iz süzgeci: {silinen}/{top} iz silindi")
        tablo = []
        if A.elle and ob.reconstruction.is_valid:
            odak = kam.focal_length
            adim("elle çözüm aynen alındı")
        else:
            an = anahtar_sec()
            s.use_keyframe_selection = not an
            if an:
                ob.keyframe_a, ob.keyframe_b = an[1], an[2]
            adim(f"anahtar kareler {ob.keyframe_a - BAS}–{ob.keyframe_b - BAS}")
            odak = odak_ara(tablo)
            adim(f"odak {odak:.1f} mm · hata {ob.reconstruction.average_error:.3f} px")
            temizlik = temizle()
            # odak + mercek bozulması inceltmesi: hata belirgin azalmazsa (≥ %5) geri alınır
            e0 = ob.reconstruction.average_error
            once = (kam.focal_length, kam.k1, kam.k2)
            if P["bozulma"]:
                try:
                    e1 = coz(None, "fk")
                except RuntimeError:
                    e1 = 1e9
                if not (e1 < 0.95 * e0 and abs(kam.focal_length / once[0] - 1) < 0.3 and abs(kam.k1) < 0.5):
                    kam.focal_length, kam.k1, kam.k2 = once
                    kam.k3 = 0.0
                    coz(None)
            temizlik += temizle(4)
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(A.blend_cikti or CIKTI / "iz.blend").resolve()))
    rec = ob.reconstruction
    if not rec.is_valid:
        raise SystemExit("kamera çözülemedi: yeterli iz yok (paralaks veren yavaş yürüyüş ve dokulu zemin gerekir; elle: ./st takip <id> <ad> ac)")
    Cs = {c.frame: (np.array(c.matrix), c.average_error) for c in rec.cameras}
    eksik = [f for f in range(BAS, SON + 1) if f not in Cs]
    # kısa boşluklar (≤ 3 kare) komşu kameralardan doldurulur; uzunsa durulur
    for f in eksik:
        once_ = max([g for g in Cs if g < f], default=None)
        sonra_ = min([g for g in Cs if g > f], default=None)
        if once_ is None or sonra_ is None or sonra_ - once_ > 4:
            raise SystemExit(f"çözümde boşluk: kare {f - BAS} (komşu çözülmüş kare yok ya da boşluk > 3 kare): bu bölümü kırp (--bas/--son) ya da elle iz ekle")
        u = (f - once_) / (sonra_ - once_)
        Ma, Mb = Cs[once_][0], Cs[sonra_][0]
        qa, qb = Matrix(Ma[:3, :3].tolist()).to_quaternion(), Matrix(Mb[:3, :3].tolist()).to_quaternion()
        M = np.eye(4)
        M[:3, :3] = np.array(qa.slerp(qb, u).to_matrix())
        M[:3, 3] = Ma[:3, 3] * (1 - u) + Mb[:3, 3] * u
        Cs[f] = (M, -1.0)
    Ms = [Cs[f][0] for f in range(BAS, SON + 1)]
    izler = [t for t in tr.tracks if t.has_bundle]
    H_ = izdusum_hatalari()
    n, d, ic, esik = zemin_bul(Ms, [np.array(t.bundle) for t in izler])
    s_, nokta, kamera = hizala(Ms, n, d, P["yukseklik"])
    hepsi = [h for v in H_.values() for _, h in v]
    kareler = []
    for i, f in enumerate(range(BAS, SON + 1)):
        Y = kamera(Ms[i])
        kareler.append({"m": [round(float(x), 6) for x in Y.flatten()], "hata": round(float(Cs[f][1]), 3), "iz": int(sum(1 for t in izler for m in isaretler(t) if m.frame == f))})
    yuk = [float(np.asarray(Ms[i][:3, 3]) @ n + d) * s_ for i in range(N)]
    pts = []
    for t, z in zip(izler, ic):
        p = nokta(np.array(t.bundle))
        pts.append({"p": [round(float(x), 4) for x in p], "hata": round(t.average_error, 3), "zemin": bool(z),
                    "k": {str(m.frame - BAS): [round(m.co[0] * W, 1), round((1 - m.co[1]) * H, 1)] for m in isaretler(t)}})
    sonuc = {
        "surum": 1,
        "klip": {"en": W, "boy": H, "kare": NK, "fps": clip.fps or sc.render.fps, "bas": BAS - 1, "son": SON - 1, "n": N},
        "mercek": {"odak_mm": round(kam.focal_length, 4), "sensor_mm": 36.0, "odak_px": round(fpx(), 3),
                   "merkez_px": [round(kam.principal_point_pixels[0], 3), round(H - kam.principal_point_pixels[1], 3)],
                   "bozulma": {"model": "polinom", "k1": round(kam.k1, 6), "k2": round(kam.k2, 6), "k3": round(kam.k3, 6)}},
        "hata": {"ortalama_px": round(rec.average_error, 4), "ortanca_px": round(statistics.median(hepsi), 4) if hepsi else None,
                 "en_kotu_kare": max(({"kare": i, "hata": k["hata"]} for i, k in enumerate(kareler)), key=lambda x: x["hata"]),
                 "hedef_px": P["hedef"]},
        "iz": {"kullanilan": len(izler), "isaret": len(hepsi), "anahtar": [ob.keyframe_a - BAS, ob.keyframe_b - BAS],
               "kare_basina_en_az": int(min(k["iz"] for k in kareler))},
        "zemin": {"nokta": int(ic.sum()), "esik_m": round(esik * s_, 4),
                  "sapma_m": round(float(np.median(np.abs(np.array([t.bundle for t in izler])[ic] @ n + d))) * s_, 4)},
        "olcek": {"kamera_yuksekligi_m": P["yukseklik"], "yukseklik_min_m": round(min(yuk), 3), "yukseklik_max_m": round(max(yuk), 3),
                  "yol_m": round(float(np.linalg.norm(kamera(Ms[-1])[:3, 3] - kamera(Ms[0])[:3, 3])), 3)},
        "odak_aramasi": [{"odak_mm": round(f, 2), "hata": round(e, 3)} for e, f in sorted(tablo, key=lambda x: x[1]) if e < 1e8],
        "kareler": kareler,
        "noktalar": pts,
        "ayar": P,
        "elle": bool(A.blend),
        "sure_sn": round(time.time() - T0, 1),
    }
    (CIKTI / "cozum.json").write_text(json.dumps(sonuc, ensure_ascii=False, separators=(",", ":")) + "\n")
    yaz("SONUC", {k: sonuc[k] for k in ("mercek", "hata", "iz", "zemin", "olcek", "sure_sn")})


main()
