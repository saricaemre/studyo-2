"""ACE-Step 1.5 ile yerel müzik üretimi (ses stilleri → kaynak "ace").

ACE-Step'in kendi ortamıyla çalışır (stüdyonun .venv'iyle değil):
  araclar/ACE-Step-1.5/.venv/bin/python pipeline/ace_muzik.py '<iş listesi JSON>'
İş: {"cikti": "/yol/muzik.wav", "caption": "...", "bpm": 90, "sure": 30, "tohum": 42, "ton": "A minor", "referans": "/yol/ref.wav"?}
Modeller bir kez yüklenir, bütün işler sırayla üretilir. Sabit tohum = aynı ayar aynı parçayı verir (önbellek st.py'de).
Ayar (16 GB Apple Silicon): 2B turbo DiT + 0.6B dil modeli (MLX), README'deki öneriyle aynı. Lisans: MIT; çıktıların özgünlüğü
ve yapay zekâ kullanımının belirtilmesi ACE-Step'in sorumlu kullanım notuna göre kullanıcının işidir (yayin.md'ye yazılır).
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

ACE = Path(os.environ.get("ACE_STEP_DIZIN", Path(__file__).resolve().parents[2] / "araclar" / "ACE-Step-1.5"))
sys.path.insert(0, str(ACE))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("ACESTEP_LM_BACKEND", "mlx")


def main():
    isler = json.loads(sys.argv[1])
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music
    from acestep.llm_inference import LLMHandler

    t0 = time.time()
    dit = AceStepHandler()
    msg, ok = dit.initialize_service(project_root=str(ACE), config_path="acestep-v15-turbo", device="auto", offload_to_cpu=False)
    if not ok:
        raise SystemExit(f"ACE-Step DiT başlatılamadı: {msg}")
    llm = LLMHandler()
    msg, ok = llm.initialize(checkpoint_dir=str(ACE / "checkpoints"), lm_model_path="acestep-5Hz-lm-0.6B", backend="mlx",
                             device="auto", offload_to_cpu=False, dtype=None)
    if not ok:
        raise SystemExit(f"ACE-Step dil modeli başlatılamadı: {msg}")
    print(f"ACE-Step hazır: {time.time() - t0:.1f} sn", flush=True)
    tmp = ACE / "output" / "studyo"
    sonuc = []
    for i, j in enumerate(isler):
        t1 = time.time()
        p = GenerationParams(task_type="text2music", caption=j["caption"][:512], lyrics="[Instrumental]", instrumental=True,
                             bpm=j.get("bpm"), keyscale=j.get("ton", ""), timesignature="4", duration=float(j["sure"]),
                             seed=int(j.get("tohum", 42)), inference_steps=8, shift=3.0, thinking=True,
                             reference_audio=j.get("referans"))
        c = GenerationConfig(batch_size=1, audio_format="wav", use_random_seed=False, seeds=[int(j.get("tohum", 42))])
        r = generate_music(dit, llm, p, c, save_dir=str(tmp))
        if not r.success or not r.audios:
            raise SystemExit(f"ACE-Step üretemedi ({j['cikti']}): {r.error}")
        hedef = Path(j["cikti"])
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(r.audios[0]["path"], hedef)
        sonuc.append({"cikti": str(hedef), "sn": round(time.time() - t1, 1), "tohum": r.audios[0].get("params", {}).get("seed")})
        print(f"[{i + 1}/{len(isler)}] {hedef.name}: {sonuc[-1]['sn']} sn", flush=True)
    print(json.dumps({"isler": sonuc}))


if __name__ == "__main__":
    main()
