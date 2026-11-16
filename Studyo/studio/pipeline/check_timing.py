"""timeline.json'daki kelime zamanlarını Whisper ile karşılaştırır."""
import json, sys, mlx_whisper
from pathlib import Path
vid = sys.argv[1]
d = Path('public')/vid
tl = json.loads((d/'timeline.json').read_text())
r = mlx_whisper.transcribe(str(d/'narration.wav'), path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="tr", word_timestamps=True)
ww = [w for s in r['segments'] for w in s['words']]
tw = [w for s in tl['sentences'] for w in s['words']]
diffs = []
for w in tw:
    near = min(ww, key=lambda x: abs(x['start']-w['start']))
    diffs.append(near['start']-w['start'])
    print(f"{w['text']:14s} tts={w['start']:6.2f} whisper={near['start']:6.2f} ({near['word'].strip()}) fark={near['start']-w['start']:+.2f}")
import statistics as st
print("medyan fark:", round(st.median(diffs),3))
