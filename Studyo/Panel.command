#!/bin/sh
# Stüdyo panelini açar. Finder'da çift tıkla. Panel arka planda çalışır: bu pencereyi kapatsan da açık kalır.
# Kapatmak için panelde sol alttaki "Paneli kapat".
cd "$(dirname "$0")/studio" || exit 1
# Araçlar (claude, ffmpeg, node) Finder'dan açılışta da bulunsun: kurulumun koyduğu yerler PATH'in sonuna eklenir
export PATH="$PATH:$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/opt/node@24/bin"
URL=http://localhost:4777
if curl -s -m 1 "$URL/api/genel" >/dev/null 2>&1; then
  open "$URL"; echo "Panel zaten açık: $URL"; exit 0
fi
nohup .venv/bin/python -I -u panel/sunucu.py --port 4777 > panel/panel.log 2>&1 &
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 0.5
  curl -s -m 1 "$URL/api/genel" >/dev/null 2>&1 && break
done
open "$URL"
echo "Panel arka planda açık: $URL"
echo "Bu pencereyi kapatabilirsin. Paneli kapatmak için panelde sol alttaki \"Paneli kapat\"."
