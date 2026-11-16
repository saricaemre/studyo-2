"""Senaryodan anlatım sesi + kelime zaman çizelgesi üretir. Ses kaynağı script.json → "ses".kaynak:

  edge      edge-tts (ücretsiz). Kelime sınırlarını kendisi verir.
  opencode  OpenCode Zen üzerinden Gemini ses çıktısı (deneysel; studio/.env → OPENCODE_API_KEY).
            Kelime zamanları Whisper ile hizalanır.
  kayit     Kendi kaydın: videos/<id>/kayit.(wav|m4a|mp3|aiff). Kelime zamanları Whisper ile hizalanır.
  magnific  Magnific (ElevenLabs) yapay anlatıcı; kullanıcının seçtiği ses (varsayılan Serkan Yıldırım, eleven_v3). Magnific'in genel
            API'sinde TTS yok, ses yalnız MCP'den (Claude) üretilir: her parça bir kez üretilip dondurulur (videos/<id>/uretim/anlatim/
            <anahtar>.mp3, ./st uret anlatim → audio_tts → ./st uret al … --tur anlatim). Eksik parça varsa liste yazılır, durulur.
            Anahtar = metin + ses + model: metin değişmedikçe yeniden üretilmez. Kelime zamanları Whisper ile hizalanır.
  yok       Anlatım yok (müzikli/sessiz film). Vuruşlar script'teki "bas"/"bit" çapalarından kurulur.

Kullanım: .venv/bin/python -I pipeline/tts.py videos/<id>/script.json
Çıktı:   public/<id>/narration.wav (anlatım varsa), public/<id>/timeline.json
"""
import asyncio
import base64
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

SR = 48000
BOUNDARY_LAG = 0.04
ROOT = Path(__file__).resolve().parent.parent
WHISPER = "mlx-community/whisper-large-v3-turbo"


# ---------------------------------------------------------------- ortak
def decode(path, sr=SR):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def trim_bounds(x, thr_db=-45.0, pad=0.02):
    """Baştaki/sondaki sessizliği bulur (saniye)."""
    win = int(0.01 * SR)
    n = len(x) // win
    rms = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(1) + 1e-12)
    loud = np.where(20 * np.log10(rms) > thr_db)[0]
    s = max(0.0, loud[0] * 0.01 - pad)
    e = min(len(x) / SR, (loud[-1] + 1) * 0.01 + pad)
    return s, e


def map_tokens(display, spoken):
    """Ekranda görünen kelimeleri (ör. '1453') okunan kelimelere (bin dört yüz elli üç) eşler."""
    if len(display) == len(spoken):
        return [[i] for i in range(len(spoken))]
    extra = len(spoken) - len(display)
    out, j = [], 0
    for tok in display:
        n = 1 + extra if any(c.isdigit() for c in tok) else 1
        out.append(list(range(j, j + n)))
        j += n
    assert j == len(spoken), (display, [w["text"] for w in spoken])
    return out


def load_env():
    """studio/.env → os.environ (yalnız boş olmayan, henüz ayarlanmamış anahtarlar). Değerler hiçbir yere yazdırılmaz."""
    p = ROOT / ".env"
    if p.exists():
        for ln in p.read_text().splitlines():
            m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$", ln)
            if m and m.group(2) and not os.environ.get(m.group(1)):
                os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


def _norm(s):
    return re.sub(r"[^\wçğıöşüâîû]", "", s.lower().replace("i̇", "i"))


def _speech_chunks(x, sr, gap=0.8, thr_db=-50.0):
    """Örnek aralıkları [(a, b)]: ≥ gap sn sessizliklerin ortasından bölünmüş konuşma parçaları."""
    win = int(0.01 * sr)
    n = len(x) // win
    if n == 0:
        return [(0, len(x))]
    db = 20 * np.log10(np.sqrt((x[: n * win].astype(np.float64).reshape(n, win) ** 2).mean(1)) + 1e-9)
    cuts, i = [], 0
    while i < n:
        if db[i] < thr_db:
            j = i
            while j < n and db[j] < thr_db:
                j += 1
            if j - i >= gap * 100 and i > 0 and j < n:
                cuts.append(((i + j) // 2) * win)
            i = j
        else:
            i += 1
    edges = [0] + cuts + [len(x)]
    return list(zip(edges[:-1], edges[1:]))


def align(tokens, x, sr=SR, offset=0.0):
    """Whisper kelime zamanlarını konuşulan token listesine hizalar → [{text,start,end}] (offset eklenmiş).
    Eşleşmeyen tokenlar komşuları arasında karakter uzunluğuna göre paylaştırılır."""
    import mlx_whisper
    x16 = x if sr == 16000 else np.interp(np.arange(0, len(x) * 16000 // sr) * sr / 16000, np.arange(len(x)), x).astype(np.float32)
    # Whisper, uzun sessizlikten önceki/sonraki kısa konuşmayı atlıyor (kesilerek kurulan kayıtta ilk 4 kelime ve "Her yıl"
    # kayboldu). Kayıt ≥ 0,8 sn sessizliklerden parçalara bölünür, her parça ayrı yazıya dökülür. Tek parçada davranış aynı.
    ww = []
    for a, b in _speech_chunks(x16, 16000):
        r = mlx_whisper.transcribe(x16[a:b], path_or_hf_repo=WHISPER, language="tr", word_timestamps=True,
                                   initial_prompt=" ".join(tokens)[:400])
        ww += [{**w, "start": w["start"] + a / 16000, "end": w["end"] + a / 16000} for s in r["segments"] for w in s.get("words", [])]
    a = [_norm(t) for t in tokens]
    b = [_norm(w["word"]) for w in ww]
    times = [None] * len(tokens)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            w = ww[blk.b + k]
            times[blk.a + k] = (w["start"], w["end"])
    # eşleşmeyenleri doldur
    total = len(x) / sr
    i = 0
    while i < len(tokens):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tokens) and times[j] is None:
            j += 1
        t0 = times[i - 1][1] if i > 0 else (ww[0]["start"] if ww else 0.0)
        t1 = times[j][0] if j < len(tokens) else (ww[-1]["end"] if ww else total)
        lens = [max(1, len(tokens[k])) for k in range(i, j)]
        acc = t0
        for k, L in zip(range(i, j), lens):
            d = (t1 - t0) * L / sum(lens)
            times[k] = (acc, acc + d)
            acc += d
        i = j
    # Whisper, duraklamadan sonra gelen kelimenin başlangıcını sessizliğe taşır: başlangıç sessizdeyse
    # sesin gerçekten başladığı 10 ms'lik pencereye kaydır (kayıt testinde "Haliç" −370 ms → düzeldi).
    # Arama kelimenin sonuna kadar sürer: kesilerek kurulan kayıtta uzun sessizlik sonrası "Her" 0,77 sn erken başlıyordu.
    win = int(0.01 * sr)
    nwin = len(x) // win
    db = 20 * np.log10(np.sqrt((x[: nwin * win].reshape(nwin, win).astype(np.float64) ** 2).mean(1)) + 1e-9)
    for i, (st, en) in enumerate(times):
        k = int(st / 0.01)
        if 0 <= k < nwin and db[k] < -42:
            for j in range(k, min(nwin, int(en / 0.01))):
                if db[j] > -38:
                    times[i] = (j * 0.01, max(en, j * 0.01 + 0.05))
                    break
    matched = sum(1 for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks() for _ in range(blk.size))
    return [{"text": t, "start": s + offset, "end": e + offset} for t, (s, e) in zip(tokens, times)], matched


# ---------------------------------------------------------------- kaynaklar
async def edge_synth(text, cfg, mp3_path):
    import edge_tts
    ek = {"volume": cfg["volume"]} if cfg.get("volume") else {}  # yalnız verilince (eski filmlerin klipleri ve önbelleği değişmez)
    comm = edge_tts.Communicate(text, cfg["voice"], rate=cfg.get("rate", "+0%"), pitch=cfg.get("pitch", "+0Hz"), boundary="WordBoundary", **ek)
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"text": chunk["text"], "start": chunk["offset"] / 1e7,
                              "end": (chunk["offset"] + chunk["duration"]) / 1e7})
    return words


OPENCODE_URL = "https://opencode.ai/inference/google/v1beta/models/{model}:generateContent"


def opencode_synth(text, cfg, wav_path):
    """Gemini'den ses çıktısı ister (responseModalities=AUDIO). Zen bu modu desteklemiyorsa açık bir hata verir."""
    load_env()
    key = os.environ.get("OPENCODE_API_KEY")
    if not key:
        raise SystemExit("OPENCODE_API_KEY yok: studio/.env.ornek → studio/.env olarak kopyala ve anahtarı yaz.")
    model = cfg.get("model", "gemini-3.8-flash")
    style = cfg.get("talimat", "Sakin, sıcak ve net bir belgesel anlatıcısı gibi, doğal Türkçe tonlamayla oku:")
    body = {"contents": [{"role": "user", "parts": [{"text": f"{style}\n{text}"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": cfg.get("voice", "Kore")}}}}}
    req = urllib.request.Request(OPENCODE_URL.format(model=model), data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")[:600]
        raise SystemExit(f"OpenCode ses isteği reddedildi ({e.code}): {msg}")
    parts = [p for c in res.get("candidates", []) for p in c.get("content", {}).get("parts", []) if "inlineData" in p]
    if not parts:
        raise SystemExit(f"OpenCode yanıtında ses yok (model {model} ses çıktısı vermiyor olabilir): {json.dumps(res)[:400]}")
    mime = parts[0]["inlineData"].get("mimeType", "")
    pcm = base64.b64decode(parts[0]["inlineData"]["data"])
    rate = int(re.search(r"rate=(\d+)", mime).group(1)) if "rate=" in mime else 24000
    if "L16" in mime or "pcm" in mime:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "-", str(wav_path)], input=pcm, check=True)
    else:
        Path(wav_path).with_suffix(".bin").write_bytes(pcm)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(Path(wav_path).with_suffix(".bin")), str(wav_path)], check=True)


MAGNIFIC_SES = {"voice": 1039, "ses_adi": "Serkan Yıldırım", "model": "eleven_v3"}  # kullanıcının seçimi (2026-10-26): erkek, doğal


def magnific_ayar(script) -> dict:
    """script.json → ses (kaynak magnific): ses kimliği, adı, model ve isteğe bağlı ElevenLabs ayarları."""
    s = script.get("ses") or {}
    v = s.get("voice")
    return {"voice": int(v) if str(v or "").isdigit() else MAGNIFIC_SES["voice"],
            "ses_adi": s.get("ses_adi") or (MAGNIFIC_SES["ses_adi"] if not str(v or "").isdigit() else ""),
            "model": s.get("model") or MAGNIFIC_SES["model"], **{k: s[k] for k in ("speed", "stability") if k in s}}


def magnific_anahtar(say, ayar) -> str:
    """Parçanın kimliği: okunacak metin + ses + model (+ hız, kararlılık). Metin değişmedikçe aynı klip kullanılır."""
    return hashlib.sha1(json.dumps(["magnific", say, {k: ayar.get(k) for k in ("voice", "model", "speed", "stability")}],
                                   ensure_ascii=False).encode()).hexdigest()[:16]


def magnific_parcalari(script) -> list[dict]:
    """Anlatımın Magnific parçaları: [{anahtar, metin, cumle}] (sıra senaryodaki gibi)."""
    ayar = magnific_ayar(script)
    return [{"anahtar": magnific_anahtar(say, ayar), "metin": say, "cumle": sent["id"]}
            for sent in script["sentences"] for _, _, say in sentence_tokens(sent)]


def magnific_klibi(vid, anahtar) -> Path | None:
    d = ROOT / "videos" / vid / "uretim" / "anlatim"
    return next((p for p in sorted(d.glob(f"{anahtar}.*")) if p.suffix in (".mp3", ".wav", ".m4a", ".ogg")), None) if d.exists() else None


# ---------------------------------------------------------------- yollar
def parca_ayari(cfg, script, sent, part):
    """Konuşmacının ve parçanın ses ayarı (edge, opencode): script.json → konusmacilar.<k>.ses (voice, rate, pitch, volume), sonra
    parts[].ses. Diyalogda iki ses, fısıltı ya da bağırış için. Yoksa filmin ayarı (eski filmler aynen)."""
    if cfg.get("kaynak", "edge") not in ("edge", "opencode"):
        return cfg
    ek = {**(((script.get("konusmacilar") or {}).get(sent.get("konusmaci")) or {}).get("ses") or {}), **(part.get("ses") or {})}
    return {**cfg, **ek} if ek else cfg


def sentence_tokens(sent):
    """Cümlenin parçaları: (ekranda görünen tokenlar, okunacak metin). Senaryo yazılmadan önce (plan turu) parça yok."""
    for part in sent.get("parts", []):
        yield part, part["text"].split(), part.get("say", part["text"]).replace("…", "")


async def synth_parts(script, out_dir):
    """edge / opencode: parça parça sentez, klipleri sessizliklerle birleştirir."""
    cfg = dict(script.get("ses", {}))
    for k in ("voice", "rate", "pitch"):
        cfg.setdefault(k, script.get(k))
    kind = cfg.get("kaynak", "edge")
    if kind == "opencode":
        cfg.setdefault("voice", "Kore")
    if kind == "magnific":  # üst düzey "voice" (Edge adı) karışmasın: ses kimliği yalnız ses bloğundan
        cfg.update(magnific_ayar(script))
        eksik = [p for p in magnific_parcalari(script) if not magnific_klibi(script["id"], p["anahtar"])]
        if eksik:
            yol = ROOT / "videos" / script["id"] / "uretim" / "anlatim_eksik.json"
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_text(json.dumps({**{k: cfg[k] for k in ("voice", "ses_adi", "model")}, "parcalar": eksik}, ensure_ascii=False, indent=1))
            raise SystemExit(f"Magnific anlatımı eksik: {len(eksik)}/{len(magnific_parcalari(script))} parça "
                             f"({sum(len(p['metin']) for p in eksik)} karakter). Claude üretir: ./st uret anlatim {script['id']} "
                             "(audio_tts → ./st uret al … --tur anlatim), sonra yeniden ./st ses.")
    tmp = out_dir / "_tts"
    tmp.mkdir(parents=True, exist_ok=True)
    audio = [np.zeros(int(script["leadIn"] * SR), dtype=np.float32)]
    t = script["leadIn"]
    sentences, k, report, cached = [], 0, [], 0
    for sent in script["sentences"]:
        s_words, s_start = [], t
        parts = sent["parts"]
        for p_i, (part, display, say) in enumerate(sentence_tokens(sent)):
            # Önbellek: aynı metin + aynı ses ayarı → aynı klip (tekrarlanabilir ses, ücretli kaynakta tasarruf)
            c = parca_ayari(cfg, script, sent, part)
            key = hashlib.sha1(json.dumps([kind, say, {k: c.get(k) for k in ("voice", "rate", "pitch", "model", "talimat")}
                                           | ({"volume": c["volume"]} if c.get("volume") else {})],
                                          ensure_ascii=False).encode()).hexdigest()[:16]
            clip_path = tmp / f"{key}.{'mp3' if kind == 'edge' else 'wav'}"
            meta = tmp / f"{key}.json"
            if kind == "magnific":  # dondurulmuş klip; hizalama klibin özetiyle önbellekte
                clip_path = magnific_klibi(script["id"], magnific_anahtar(say, cfg))
                meta = tmp / f"m_{hashlib.sha256(clip_path.read_bytes()).hexdigest()[:16]}.json"
            if clip_path.exists() and meta.exists():
                spoken = json.loads(meta.read_text())
                x = decode(clip_path)
                a, b = trim_bounds(x)
                cached += 1
            elif kind == "edge":
                spoken = await edge_synth(say, c, clip_path)
                x = decode(clip_path)
                a, b = trim_bounds(x)
            else:  # opencode üretir; magnific klibi zaten dondurulmuş (Claude MCP'den üretti)
                if kind == "opencode":
                    opencode_synth(say, c, clip_path)
                x = decode(clip_path)
                a, b = trim_bounds(x)
                spoken, matched = align(say.split(), x[int(a * SR): int(b * SR)], SR, offset=a)
                report.append((sent["id"], matched, len(say.split())))
            meta.write_text(json.dumps(spoken, ensure_ascii=False))
            lag = BOUNDARY_LAG if kind == "edge" else 0.0
            clip = x[int(a * SR): int(b * SR)]
            for tok, idx in zip(display, map_tokens(display, spoken)):
                # Edge sınırları ~40 ms erken geliyor (Whisper ile ölçüldü); klibin ilk kelimesi
                # gerçek ses başlangıcından önce olamaz.
                start = max(t + spoken[idx[0]]["start"] - a + lag, t + 0.02)
                s_words.append({"i": k, "text": tok, "start": round(start, 3),
                                "end": round(t + spoken[idx[-1]]["end"] - a + lag, 3)})
                k += 1
            audio.append(clip)
            t += len(clip) / SR
            last = p_i == len(parts) - 1
            gap = sent["pauseAfter"] if last else part.get("pauseAfter", 0.25)
            s_end = t
            audio.append(np.zeros(int(gap * SR), dtype=np.float32))
            t += gap
        sentences.append({"id": sent["id"], "step": sent["step"], "start": round(s_start, 3),
                          "end": round(s_end, 3), "words": s_words})
    audio.append(np.zeros(int(script["tail"] * SR), dtype=np.float32))
    for sid, m, n in report:
        print(f"   hizalama {sid}: {m}/{n} kelime Whisper ile eşleşti")
    if cached:
        print(f"   önbellekten {cached} klip")
    return np.concatenate(audio), sentences


def from_recording(script, vid):
    """kayit: tek dosya kayıt → Whisper hizalaması → cümle ve kelime zamanları."""
    rec = next((p for ext in ("wav", "m4a", "mp3", "aiff", "flac") for p in [ROOT / "videos" / vid / f"kayit.{ext}"] if p.exists()), None)
    if rec is None:
        raise SystemExit(f"Kayıt yok: videos/{vid}/kayit.wav (m4a/mp3/aiff/flac da olur)")
    x = decode(rec)
    a, b = trim_bounds(x, thr_db=-50.0, pad=0.05)
    x = x[int(a * SR): int(b * SR)]
    lead = script["leadIn"]
    toks, owners = [], []
    for si, sent in enumerate(script["sentences"]):
        for pi, (part, display, say) in enumerate(sentence_tokens(sent)):
            for w in say.split():
                toks.append(w)
                owners.append((si, pi))
    spoken, matched = align(toks, x, SR, offset=lead)
    print(f"   hizalama: {matched}/{len(toks)} kelime Whisper ile eşleşti")
    sentences, k, j = [], 0, 0
    for si, sent in enumerate(script["sentences"]):
        s_words = []
        for pi, (part, display, say) in enumerate(sentence_tokens(sent)):
            n = len(say.split())
            sp = spoken[j: j + n]
            j += n
            for tok, idx in zip(display, map_tokens(display, sp)):
                s_words.append({"i": k, "text": tok, "start": round(sp[idx[0]]["start"], 3), "end": round(sp[idx[-1]]["end"], 3)})
                k += 1
        sentences.append({"id": sent["id"], "step": sent["step"], "start": s_words[0]["start"], "end": s_words[-1]["end"], "words": s_words})
    y = np.concatenate([np.zeros(int(lead * SR), np.float32), x, np.zeros(int(script["tail"] * SR), np.float32)])
    return y, sentences


def sections(script, vid):
    """yok: anlatımsız film. Vuruşlar "bas"/"bit" çapalarından (müzik ızgarası ya da saniye) kurulur."""
    pub = ROOT / "public" / vid
    beats = json.loads((pub / "vuruslar.json").read_text())["beats"] if (pub / "vuruslar.json").exists() else []

    def at(anchor):
        kind, val = anchor[0], anchor[1]
        off = float(anchor[2]) if len(anchor) > 2 else 0.0
        if kind == "vurus":
            if val >= len(beats):
                raise SystemExit(f"{val}. vuruş yok (ızgarada {len(beats)}). Önce ./st vurus")
            return beats[val] + off
        return float(val) + off

    out = []
    for s in script["sentences"]:
        out.append({"id": s["id"], "step": s["step"], "start": round(at(s["bas"]), 3), "end": round(at(s["bit"]), 3), "words": []})
    dur = at(script["sure"]) if "sure" in script else out[-1]["end"] + script.get("tail", 0.5)
    return out, dur


def main(script_path):
    script = json.loads(Path(script_path).read_text())
    vid = script["id"]
    out_dir = ROOT / "public" / vid
    out_dir.mkdir(parents=True, exist_ok=True)
    kind = script.get("ses", {}).get("kaynak", "edge")
    if kind == "yok":
        sentences, duration = sections(script, vid)
        y = None
    elif kind == "kayit":
        y, sentences = from_recording(script, vid)
    elif kind in ("edge", "opencode", "magnific"):
        y, sentences = asyncio.run(synth_parts(script, out_dir))
    else:
        raise SystemExit(f"Bilinmeyen ses kaynağı: {kind} (edge, opencode, magnific, kayit, yok)")
    if y is not None:
        duration = len(y) / SR
        pcm = (np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        str(out_dir / "narration.wav")], input=pcm, check=True)
    elif (out_dir / "narration.wav").exists():
        (out_dir / "narration.wav").unlink()
    timeline = {"id": vid, "title": script["title"], "duration": round(duration, 3), "sentences": sentences}
    vf = out_dir / "vuruslar.json"
    if vf.exists():
        g = json.loads(vf.read_text())
        timeline.update({"bpm": g["bpm"], "beats": g["beats"], "downbeats": g.get("downbeats", [])})
    (out_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1))
    print(f"süre {duration:.2f} sn · kaynak {kind}")
    for s in sentences:
        print(f"[{s['start']:6.2f}-{s['end']:6.2f}] {s['step']:8s} " +
              (" ".join(f"{w['text']}@{w['start']:.2f}" for w in s["words"]) or s["id"]))


if __name__ == "__main__":
    main(sys.argv[1])
