"""Referans analizi: beğenilen bir videoyu ölçer ve yeni bir stil paketinin taslağını çıkarır.

Makaledeki kural: referans bir kolaj değil, bir stil rehberine dönüşmeli. Model referansı görmezse boşluğu kendi
"güvenli varsayılanlarıyla" doldurur. Bu araç ölçülebilir olanı ölçer (palet, tempo, kesmeler, hareket, ses, konuşma);
tipografi, kompozisyon ve hareket dilini göze bırakır.

Kullanım: .venv/bin/python -I pipeline/referans.py <video> <çıktı klasörü> [--konusma-yok]
Çıktı: analiz.md · kareler.jpg (kontak) · palet.png · olcum.json
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak as O  # noqa: E402

F_REG = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def frames_at(path, times, w):
    out = []
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={w}:-2",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        if raw:
            from io import BytesIO
            out.append((t, Image.open(BytesIO(raw)).convert("RGB")))
    return out


def kmeans(px, k=8, iters=12, seed=7):
    rng = np.random.default_rng(seed)
    c = px[rng.choice(len(px), k, replace=False)].astype(np.float32)
    for _ in range(iters):
        d = ((px[:, None, :] - c[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = px[lab == j]
            if len(m):
                c[j] = m.mean(0)
    share = np.bincount(lab, minlength=k) / len(px)
    order = np.argsort(-share)
    return c[order], share[order]


def hexc(c):
    return "#%02X%02X%02X" % tuple(int(round(x)) for x in c)


def sat(c):
    mx, mn = max(c), min(c)
    return 0 if mx == 0 else (mx - mn) / mx


def main(src, out, konusma=True):
    src, out = Path(src), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pr = O.probe(src)
    vs = next(s for s in pr["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in pr["streams"])
    W, H = vs["width"], vs["height"]
    fr = vs["r_frame_rate"].split("/")
    fps = float(fr[0]) / float(fr[1])
    dur = float(pr["format"]["duration"])
    res = {"dosya": str(src), "boyut": [W, H], "fps": round(fps, 3), "sure": round(dur, 2), "ses": has_audio}

    # --- kontak: kısa videoda 2 kare/sn, uzunda eşit aralıklı 48 kare
    n = min(48, max(8, int(dur * 2)))
    times = [dur * (i + 0.5) / n for i in range(n)]
    tw = 220 if H > W else 320
    frs = frames_at(src, times, tw)
    th = frs[0][1].size[1]
    cols = 8 if H > W else 6
    rows = (len(frs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 26) + 8), (24, 20, 17))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(F_REG, 13)
    for i, (t, im) in enumerate(frs):
        x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 26)
        sheet.paste(im, (x, y))
        d.text((x, y + th + 4), O.tc(t), font=f, fill=(220, 210, 190))
    sheet.save(out / "kareler.jpg", quality=88)

    # --- palet (k-ortalamalar), ayrıca doygun "vurgu" adayları
    px = np.concatenate([np.asarray(im.resize((96, int(96 * im.size[1] / im.size[0])))).reshape(-1, 3) for _, im in frs]).astype(np.float32)
    cent, share = kmeans(px, 8)
    pal = [{"hex": hexc(c), "pay": round(float(s) * 100, 1), "doygunluk": round(float(sat(c)), 2)} for c, s in zip(cent, share)]
    sw = Image.new("RGB", (8 * 120, 150), (255, 255, 255))
    dd = ImageDraw.Draw(sw)
    for i, p in enumerate(pal):
        dd.rectangle([i * 120, 0, i * 120 + 119, 110], fill=p["hex"])
        dd.text((i * 120 + 6, 116), f"{p['hex']} %{p['pay']}", font=ImageFont.truetype(F_REG, 14), fill=(20, 20, 20))
    sw.save(out / "palet.png")
    res["palet"] = pal
    lum = (0.2126 * px[:, 0] + 0.7152 * px[:, 1] + 0.0722 * px[:, 2])
    res["parlaklik"] = {"ortalama": round(float(lum.mean()), 1), "koyu_oran": round(float((lum < 50).mean() * 100), 1),
                        "acik_oran": round(float((lum > 205).mean() * 100), 1)}

    # --- tempo: kesmeler ve anlamlı değişimler
    mw, mh = O.motion_size(W, H)
    m = O.motion_curve(src, mw, mh)
    med = float(np.median(m[1:])) if len(m) > 1 else 0.0
    cut_thr = max(25.0, 6 * med)
    cuts = [i for i in range(1, len(m)) if m[i] > cut_thr and (i < 2 or m[i - 1] <= cut_thr)]
    thr = np.percentile(m[1:], 80) if len(m) > 10 else 1
    peaks, last = [], -999
    for i in range(1, len(m) - 1):
        if m[i] >= thr and m[i] >= m[i - 1] and m[i] >= m[i + 1] and i - last >= O.FPS // 4:
            peaks.append(i)
            last = i
    ct = [c / O.FPS for c in cuts]
    shots = np.diff([0.0] + ct + [dur]) if ct else np.array([dur])
    res["tempo"] = {"kesme_sayisi": len(cuts), "ortalama_plan_sn": round(float(shots.mean()), 2),
                    "kesmeler": [round(t, 2) for t in ct[:200]],
                    "anlamli_degisim_arasi_sn": round(float(np.diff(peaks).mean() / O.FPS), 2) if len(peaks) > 2 else None,
                    "durgun_kare_orani": round(float((m[1:] < O.still_threshold(m)).mean() * 100), 1),
                    "en_uzun_durgun_sn": round(max([(b - a) / O.FPS for a, b in O.still_runs(m, 0)] or [0]), 2)}

    # --- ses
    if has_audio:
        L = O.loudness(src)
        x = O.audio_mono(src, 16000)
        win = 1600
        nwin = len(x) // win
        db = 20 * np.log10(np.sqrt((x[: nwin * win].reshape(nwin, win) ** 2).mean(1)) + 1e-9)
        quiet = db < -45
        sil, s0 = [], None
        for i, q in enumerate(list(quiet) + [False]):
            if q and s0 is None:
                s0 = i
            elif not q and s0 is not None:
                if (i - s0) * 0.1 >= 0.2:
                    sil.append([round(s0 * 0.1, 1), round(i * 0.1, 1)])
                s0 = None
        res["ses_olcum"] = {"LUFS": L["I"], "LRA": L["LRA"], "tepe_dBTP": L["TP"], "sessizlikler": sil[:30]}
        tmp = out / "_ses.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "22050", str(tmp)], check=True)
        import vurus
        b = vurus.analyze(tmp)
        res["muzik"] = {"bpm": b["bpm"], "sabit_tempo": b["sabit_tempo"], "uyum_ms": b["uyum_ms"]}
        if ct and b["beats"]:
            B = np.array(b["beats"])
            off = [abs(t - B[np.argmin(abs(B - t))]) * O.FPS for t in ct]
            res["muzik"]["vurusa_oturan_kesme_orani"] = round(float(np.mean(np.array(off) <= 1.5) * 100), 1)
        tmp.unlink(missing_ok=True)
        if konusma:
            import mlx_whisper
            r = mlx_whisper.transcribe(x, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", word_timestamps=True)
            words = [w for s in r["segments"] for w in s.get("words", [])]
            if len(words) >= 5:
                text = " ".join(w["word"].strip() for w in words)
                sents = [s for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]
                lens = [len(s.split()) for s in sents]
                first_end = next((w["end"] for w in words if re.search(r"[.!?…]$", w["word"].strip())), words[-1]["end"])
                span = words[-1]["end"] - words[0]["start"]
                res["konusma"] = {"dil": r.get("language"), "kelime": len(words), "wpm": round(len(words) / span * 60, 1),
                                  "cumle_ort": round(float(np.mean(lens)), 1), "cumle_max": int(max(lens)),
                                  "ilk_cumle_sonu_sn": round(first_end, 2), "metin": text[:2000]}
    (out / "olcum.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float))

    # --- analiz.md (stil rehberi taslağının ham maddesi)
    T = res["tempo"]
    lines = [f"# Referans analizi — {src.name}", "",
             "> Bu bir **çıta kaynağıdır, şablon değil.** Ölçülebilir olan aşağıda ölçüldü; göz gerektiren bölümler [ ] olarak bırakıldı.",
             "> Sıradaki adım: `studio/sablon/stil-rehberi.md` → `studio/stiller/<ad>/stil-rehberi.md` (bu değerlerle).", "",
             "## Künye", f"- {W}×{H} · {fps:g} fps · {dur:.1f} sn · ses {'var' if has_audio else 'yok'}", "",
             "## Palet (k-ortalamalar, 8 küme; pay = ekran alanı)", "| Renk | Pay | Doygunluk |", "|---|---|---|"]
    lines += [f"| `{p['hex']}` | %{p['pay']} | {p['doygunluk']} |" for p in pal]
    acc = [p for p in pal if p["doygunluk"] > 0.45 and p["pay"] < 12]
    lines += ["", f"- **Vurgu adayları** (doygun, az alan): {', '.join(p['hex'] for p in acc) or 'yok'}",
              f"- **Parlaklık:** ortalama {res['parlaklik']['ortalama']} / 255 · koyu piksel %{res['parlaklik']['koyu_oran']} · açık piksel %{res['parlaklik']['acik_oran']}", "",
              "## Tempo", f"- **Kesme:** {T['kesme_sayisi']} · ortalama plan süresi {T['ortalama_plan_sn']} sn",
              f"- **Anlamlı değişimler arası:** {T['anlamli_degisim_arasi_sn']} sn (görüntü değişim tepeleri)",
              f"- **Durgun kare oranı:** %{T['durgun_kare_orani']} · en uzun durgun aralık {T['en_uzun_durgun_sn']} sn", ""]
    if "ses_olcum" in res:
        S = res["ses_olcum"]
        lines += ["## Ses", f"- **Ses yüksekliği:** {S['LUFS']} LUFS · LRA {S['LRA']} · tepe {S['tepe_dBTP']} dBTP",
                  f"- **Bilinçli sessizlikler (≥ 0,2 sn, < −45 dB):** {', '.join(f'{a}–{b} sn' for a, b in S['sessizlikler']) or 'yok'}",
                  (f"- **Müzik:** {res['muzik']['bpm']} BPM, sabit tempo (uyum {res['muzik']['uyum_ms']} ms)"
                   + (f" · kesmelerin %{res['muzik']['vurusa_oturan_kesme_orani']}'i vuruşa oturuyor" if "vurusa_oturan_kesme_orani" in res["muzik"] else ""))
                  if res["muzik"]["sabit_tempo"] else "- **Müzik:** belirgin sabit bir tempo yok (müziksiz ya da serbest tempolu)", ""]
    if "konusma" in res:
        K = res["konusma"]
        lines += ["## Konuşma", f"- **Dil:** {K['dil']} · {K['kelime']} kelime · **{K['wpm']} kelime/dk**",
                  f"- **Cümle:** ortalama {K['cumle_ort']} kelime · en uzun {K['cumle_max']}",
                  f"- **Kanca (ilk cümle sonu):** {K['ilk_cumle_sonu_sn']} sn", ""]
    lines += ["## Göz (doldur: kareler.jpg'ye bakarak)",
              "- **Tipografi:** [aile, genişlik, ağırlık, ölçek]",
              "- **Kompozisyon:** [göz önce nereye gidiyor]",
              "- **Hareket:** [yapış / süzülme / taşma / kesme / bekleme]",
              "- **Doku:** [gren / kâğıt / cam / yok]",
              "- **Tekrar izleme sebebi:** [döngü / final / yok]", "",
              "## Kopyalanmayacaklar", "Konu, logo, metin, karakter, kalıp cümle ve ürüne özgü görseller. Yalnız ölçülebilir çıtalar alınır.", ""]
    (out / "analiz.md").write_text("\n".join(lines))
    print(f"yazıldı: {out}/analiz.md · kareler.jpg · palet.png · olcum.json")
    print(f"   {W}×{H} · {dur:.1f} sn · palet: {', '.join(p['hex'] for p in pal[:5])} · plan {T['ortalama_plan_sn']} sn · "
          + (f"{res['muzik']['bpm']} BPM · " if "muzik" in res else "") + (f"{res['konusma']['wpm']} kelime/dk" if "konusma" in res else ""))


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(a[0], a[1], konusma="--konusma-yok" not in sys.argv)
