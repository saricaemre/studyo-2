"""Joy of Orphan's Table — ses tasarımı. Müzik (muzik.wav) ve efekt (efekt.wav) sofra projesinde sentezlendi (tools/synth_audio.py, telifsiz);
efektler zaten sahne zamanlarına oturtulmuş tek bir parça. Kaynaktaki oran korunur: efekt müziğin tepesinden +3,8 dB."""
import subprocess

import numpy as np


def tasarla(L, fx, beds, c, sents, dur):
    yol = L.ROOT / "public" / "ihh_sofra" / "efekt.wav"
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(yol), "-f", "f32le", "-ac", "2", "-ar", str(L.SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(ham, dtype=np.float32).astype(float).reshape(-1, 2)
    x = x / (np.abs(x).max() + 1e-9)
    fx.add_st(x[:, 0], x[:, 1], 0.0, 0.8)
    return {"hush": []}
