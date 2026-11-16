"""Vuruş ızgarası: müzikten tempo (BPM), vuruş ve ölçü başı zamanlarını çıkarır.

Kesmeler ve görsel olaylar bu ızgaraya bağlanır (cues.json → ["vurus", n, ofset]).
Yöntem: spektral akı başlangıç zarfı → otokorelasyonla tempo → dinamik programlamayla vuruş takibi (Ellis 2007)
→ alçak frekans enerjisine göre ölçü başı.

Kullanım: .venv/bin/python -I pipeline/vurus.py <ses dosyası> [çıktı.json]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 22050
HOP = 256
NFFT = 1024


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def spectrogram(x):
    n = 1 + (len(x) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    frames = x[idx] * np.hanning(NFFT)[None, :]
    return np.abs(np.fft.rfft(frames, axis=1))


def onset_envelope(S, lo_bin=0, hi_bin=None):
    L = np.log1p(100 * S[:, lo_bin:hi_bin])
    flux = np.maximum(0, np.diff(L, axis=0)).sum(1)
    flux = np.concatenate([[0], flux])
    k = max(1, int(SR / HOP))  # ~1 sn hareketli ortalama çıkar
    flux = flux - np.convolve(flux, np.ones(k) / k, "same")
    flux = np.maximum(flux, 0)
    return flux / (flux.std() + 1e-9)


def tempo(env, lo=60, hi=200):
    fps = SR / HOP
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    lags = np.arange(int(fps * 60 / hi), int(fps * 60 / lo) + 1)
    bpm = 60 * fps / lags
    prior = np.exp(-0.5 * (np.log2(bpm / 120) / 1.0) ** 2)
    score = ac[lags] * prior
    i = int(np.argmax(score))
    # parabolik inceltme
    if 0 < i < len(lags) - 1:
        a, b, c = score[i - 1], score[i], score[i + 1]
        d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    else:
        d = 0.0
    lag = lags[i] + d
    return 60 * fps / lag, lag


def track(env, period, tight=100.0):
    n = len(env)
    score = env.copy()
    back = -np.ones(n, dtype=int)
    lo, hi = int(round(period / 2)), int(round(period * 2))
    for t in range(n):
        a, b = max(0, t - hi), t - lo
        if b <= a:
            continue
        prev = np.arange(a, b)
        cost = score[prev] - tight * np.log((t - prev) / period) ** 2
        j = int(np.argmax(cost))
        score[t] = env[t] + cost[j]
        back[t] = prev[j]
    last = int(np.argmax(score[-int(period):])) + n - int(period)
    beats = [last]
    while back[beats[-1]] >= 0:
        beats.append(int(back[beats[-1]]))
    return np.array(beats[::-1])


def steady_grid(times, per, dur):
    """Sabit tempolu müzik için tespitlere düz bir ızgara oturtur (aykırıları atar), parçanın başına ve sonuna uzatır.
    Dönüş: (ızgara, uyum_ms) ya da tempo değişkense (None, uyum_ms)."""
    ref = times[len(times) // 2]
    k = np.round((times - ref) / per)
    mask = np.ones(len(times), bool)
    a, p = ref, per
    for _ in range(4):
        A = np.vstack([np.ones(mask.sum()), k[mask]]).T
        (a, p), *_ = np.linalg.lstsq(A, times[mask], rcond=None)
        res = times - (a + p * k)
        mask = np.abs(res) < 0.25 * p
    fit_ms = float(np.median(np.abs(res[mask])) * 1000)
    if fit_ms > 25 or mask.mean() < 0.6:
        return None, fit_ms, p
    k0 = int(np.ceil((-0.02 - a) / p))
    k1 = int(np.floor((dur - 0.05 - a) / p))
    return a + p * np.arange(k0, k1 + 1), fit_ms, p


def downbeat_phase(S, times):
    """Ölçü başı: akor/doku değişimi en çok hangi vuruş fazında oluyor? (4/4 varsayımı)
    Vuruş aralıklarının ortalama log tayflarını karşılaştırır (100–2000 Hz: armoni bölgesi)."""
    fr = np.clip(np.round((np.asarray(times) * SR - NFFT / 2) / HOP).astype(int), 0, len(S) - 1)
    lo, hi = int(100 * NFFT / SR), int(2000 * NFFT / SR)
    L = np.log1p(100 * S[:, lo:hi])
    M = np.array([L[a:max(a + 1, b)].mean(0) for a, b in zip(fr[:-1], fr[1:])])
    if len(M) < 8:
        return 0
    nov = np.concatenate([[0], np.abs(np.diff(M, axis=0)).sum(1)])
    return int(np.argmax([nov[k::4].sum() for k in range(4)]))


def analyze(path):
    x = decode(path)
    dur = len(x) / SR
    S = spectrogram(x)
    low = onset_envelope(S, 0, int(200 * NFFT / SR) + 1)
    env = onset_envelope(S) + low          # bas davul ağırlığı: ara vuruştaki zillere kilitlenmesin
    env = env / (env.std() + 1e-9)
    bpm, lag = tempo(env)
    b = track(env, lag)
    times = (b * HOP + NFFT / 2) / SR       # çerçeve başı değil, pencere merkezi
    grid, fit_ms, p = steady_grid(times, 60 / bpm, dur)
    steady = grid is not None
    if steady:
        times, bpm = np.clip(grid, 0, None), 60 / p
    phase = downbeat_phase(S, times)
    return {"kaynak": str(path), "bpm": round(float(bpm), 2), "sabit_tempo": steady, "uyum_ms": round(fit_ms, 1),
            "beats": [round(float(t), 4) for t in times], "downbeats": [round(float(t), 4) for t in times[phase::4]],
            "olcu_basi_ilk_vurus": phase}


if __name__ == "__main__":
    res = analyze(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if out:
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"{res['bpm']:.2f} BPM · {len(res['beats'])} vuruş · ilk vuruş {res['beats'][0]:.3f} sn · ölçü başı {res['olcu_basi_ilk_vurus']}. vuruş · "
          + (f"sabit tempo ızgarası (uyum {res['uyum_ms']} ms)" if res["sabit_tempo"] else f"değişken tempo, tespitler olduğu gibi (uyum {res['uyum_ms']} ms)"))
