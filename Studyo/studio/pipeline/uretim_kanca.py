"""Kredi bekçisinin kancası: panelin arka plan Claude'u (claude -p --settings) her Magnific aracını çağırmadan önce bunu çalıştırır.

Girdi (stdin): Claude Code'un PreToolUse olayı (tool_name, tool_input, tool_use_id). Film: STUDYO_VIDEO ortam değişkeni (sunucu.py verir).
Ücretli araç ./st uret butce'nin yazdığı tek kullanımlık izin olmadan geçmez; müzik ve TTS hiç geçmez (uretim.kanca).
Çıkış 2 = çağrıyı durdur, stderr'deki neden Claude'a gider. Çıkış 0 = geç.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    try:
        d = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    ad = str(d.get("tool_name", ""))
    if not ad.startswith("mcp__magnific__"):
        sys.exit(0)
    import uretim
    ok, neden = uretim.kanca(os.environ.get("STUDYO_VIDEO") or None, ad[len("mcp__magnific__"):], d.get("tool_use_id"), d.get("tool_input") or {})
    if not ok:
        print(neden, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
