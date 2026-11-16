#!/bin/bash
# Stüdyo kurulumu ve güncellemesi (Apple Silicon Mac). Çift tıkla; açılmazsa Terminal'de: bash <bu dosyayı sürükle>
# İlk kurulumda her şeyi kurar; sonraki zip'lerde yalnız stüdyonun kodunu yeniler: videolar, markalar ve ayarlar korunur.
# Paket GitHub'dan geldiyse (yanında depo.txt): GitHub'a giriş yaptırır, depoyu $HEDEF/.depo'ya klonlar ve masaüstüne
# "Stüdyoyu Güncelle" koyar (Guncelle.command: son sürümü çeker, sonra bu betiği çalıştırır).
# İsteğe bağlı: bash Kur.command --ace   → ACE-Step müzik modelini de kurar (≈12 GB)
set -eo pipefail

KAYNAK="$(cd "$(dirname "$0")" && pwd)"
HEDEF="${STUDYO_HEDEF:-$HOME/Studyo}"
TEST="${STUDYO_TEST:-}"   # dolu ise (yalnız paket denemesi): Homebrew, Claude, beceriler, ACE, kısayol ve panel atlanır
DEPO="$(tr -d '[:space:]' < "$KAYNAK/depo.txt" 2>/dev/null || true)"   # sahip/ad: güncellemeler bu özel GitHub deposundan
ACE_COMMIT=ca1e85fe9430179831e6bc6be790c332190a3866
export HYPERFRAMES_NO_TELEMETRY=1

adim() { printf "\n\033[1;34m▸ %s\033[0m\n" "$1"; }
not_() { printf "  %s\n" "$1"; }
bitir() { [ -n "$TEST" ] || { printf "\nKapatmak için Enter'a bas."; read -r _; }; exit "${1:-0}"; }
hata() { printf "\n\033[1;31m✗ %s\033[0m\n" "$1"; printf "  Bu pencerenin ekran görüntüsüyle stüdyonun GitHub sayfasında bir issue aç.\n"; bitir 1; }
trap 'hata "Kurulum yarıda kaldı (satır $LINENO)."' ERR

clear 2>/dev/null || true
printf "\033[1mStüdyo kurulumu\033[0m · hedef: %s\n" "$HEDEF"
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || hata "Bu paket Apple Silicon (M1–M4) Mac içindir."
[ -d "$KAYNAK/Studyo/studio" ] || hata "Paket eksik: Kur.command'ın yanında Studyo klasörü olmalı (zip'i tamamen aç)."

# ---------------------------------------------------------------- 1. Homebrew ve araçlar
if [ -z "$TEST" ]; then
  adim "1/7 Homebrew"
  if ! command -v brew >/dev/null 2>&1; then
    if [ ! -x /opt/homebrew/bin/brew ]; then
      not_ "Homebrew kuruluyor (Mac'in paket yöneticisi). Mac şifren istenecek; yazarken ekranda görünmez, bu normal."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    eval "$(/opt/homebrew/bin/brew shellenv)"
    grep -qs 'brew shellenv' "$HOME/.zprofile" || echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
  fi
  not_ "Homebrew hazır."

  adim "2/7 Araçlar: ffmpeg, uv, git, Node.js"
  for p in ffmpeg uv git ${DEPO:+gh}; do brew list "$p" >/dev/null 2>&1 || brew install "$p"; done
  NODE_ANA=$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || true)
  if [ -z "$NODE_ANA" ] || [ "$NODE_ANA" -lt 22 ]; then
    brew list node@24 >/dev/null 2>&1 || brew install node@24
    export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
    grep -qs 'node@24/bin' "$HOME/.zprofile" || echo 'export PATH="/opt/homebrew/opt/node@24/bin:$PATH"' >> "$HOME/.zprofile"
  fi
  not_ "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}') · uv $(uv --version | awk '{print $2}') · Node $(node -v)"
fi

# ---------------------------------------------------------------- 3. Stüdyo dosyaları
adim "3/7 Stüdyo dosyaları → $HEDEF"
if [ ! -d "$HEDEF/studio" ]; then
  mkdir -p "$HEDEF"
  rsync -a "$KAYNAK/Studyo/" "$HEDEF/"
  not_ "İlk kurulum."
else
  not_ "Var olan kurulum güncelleniyor: videoların, markaların, ayarların ve çıktıların korunur."
  KORU="$(mktemp)"
  cat > "$KORU" <<'EOF'
/studio/videos/
/studio/hf/*/
/studio/blender/*/
/studio/manim/*/
/studio/public/
/studio/out/
/studio/istekler/
/studio/markalar/
/studio/src/Root.tsx
/studio/panel/claude_ayarlari.json
/studio/panel/uretim_ayarlari.json
/studio/panel/isler/
/studio/.env
/kanal/
/konseptler/
/cikti/
/araclar/
EOF
  rsync -a --exclude-from="$KORU" "$KAYNAK/Studyo/" "$HEDEF/"
  rm -f "$KORU"
  # public/, blender/ ve manim/ korunur (filmlerin klasörleri); stüdyonun oradaki kendi klasörleri (dokular, 3B çözücüleri, yazı tipleri,
  # Blender kiti, EEVEE, yapım, kamera takibi, karma sarmalayıcısı, Manim kiti) yenile.txt'teki listeden ayrıca yenilenir
  # (liste: pipeline/paket.py → STUDYO_KLASORLER). Manim'in kendisi isteğe bağlıdır: requirements-manim.txt (burada kurulmaz).
  while IFS= read -r d; do
    [ -n "$d" ] && [ -d "$KAYNAK/Studyo/studio/$d" ] || continue
    mkdir -p "$HEDEF/studio/$d"
    rsync -a "$KAYNAK/Studyo/studio/$d/" "$HEDEF/studio/$d/"
  done < <(cat "$KAYNAK/yenile.txt" 2>/dev/null || echo public/fontlar)
  GUNCELLEME=1
fi
# gizli ayarlar: .env yoksa boş şablondan (.env.ornek) açılır; var olan .env'e dokunulmaz
if [ ! -f "$HEDEF/studio/.env" ] && [ -f "$HEDEF/studio/.env.ornek" ]; then
  cp "$HEDEF/studio/.env.ornek" "$HEDEF/studio/.env" && chmod 600 "$HEDEF/studio/.env"
  not_ "Gizli ayarlar dosyası açıldı (studio/.env, boş; gerekirse Ayarlar'dan ya da elle doldurulur)."
fi
xattr -dr com.apple.quarantine "$HEDEF" 2>/dev/null || true
chmod +x "$HEDEF/Panel.command" "$HEDEF/studio/st"
cd "$HEDEF/studio"

# ---------------------------------------------------------------- 4. Python ve Node paketleri
adim "4/7 Python ortamı (ilk seferde birkaç dakika)"
[ -x .venv/bin/python ] || uv venv --python 3.12 .venv
uv pip install --quiet --python .venv/bin/python -r requirements.txt
.venv/bin/python -I -c "import numpy, scipy, PIL, edge_tts, mlx_whisper, transformers, torchvision" || hata "Python paketleri yüklenemedi."
# güncellemede src/Root.tsx korunur (filmlerin kaydı); stüdyonun kendi kompozisyonları (katalog, yapım filmi …) paketteki hâline getirilir
[ -z "${GUNCELLEME:-}" ] || .venv/bin/python pipeline/paket.py --root-birlestir "$KAYNAK/Studyo/studio/src/Root.tsx" src/Root.tsx \
  || hata "src/Root.tsx güncellenemedi."
not_ "Python $(.venv/bin/python --version | awk '{print $2}') hazır."

adim "5/7 Node paketleri ve render tarayıcıları (ilk seferde birkaç dakika)"
npm install --no-audit --no-fund --loglevel=error
HF_SURUM=$(grep -m1 '^SURUM' pipeline/hf.py | cut -d'"' -f2)
npx --yes "hyperframes@$HF_SURUM" browser ensure >/dev/null
npx remotion browser ensure >/dev/null 2>&1 || true
not_ "Remotion ve HyperFrames $HF_SURUM hazır."

# ---------------------------------------------------------------- 6. Claude Code ve HyperFrames becerileri
if [ -z "$TEST" ]; then
  adim "6/7 Claude Code"
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v claude >/dev/null 2>&1; then
    not_ "Claude Code kuruluyor (panelin arka planda çalıştırdığı Claude)."
    curl -fsSL https://claude.ai/install.sh | bash
    grep -qs '.local/bin' "$HOME/.zprofile" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zprofile"
  fi
  if [ -d "$KAYNAK/beceriler" ]; then
    mkdir -p "$HOME/.claude/skills"
    rsync -a "$KAYNAK/beceriler/" "$HOME/.claude/skills/"
    not_ "HyperFrames becerileri ~/.claude/skills altına kondu."
  elif [ ! -f "$HOME/.claude/skills/hyperframes/SKILL.md" ]; then
    # açık kaynak sürüm becerileri taşımaz: resmi kaynağından (HeyGen, heygen-com/hyperframes) kurulur
    not_ "HyperFrames becerileri resmi kaynağından kuruluyor (heygen-com/hyperframes)."
    npx --yes skills add heygen-com/hyperframes --all -g -y \
      || not_ "Beceriler kurulamadı; sonra elle: npx skills add heygen-com/hyperframes --all -g"
  fi
  if ! claude -p "yalnız tamam yaz" --max-turns 1 >/dev/null 2>&1; then
    printf "\n  \033[1mClaude'a giriş yapman gerekiyor.\033[0m Birazdan Claude açılacak: kendi Claude hesabınla (Pro ya da Max) giriş yap,\n"
    printf "  giriş bitince \033[1m/exit\033[0m yazıp Enter'a bas; kurulum kaldığı yerden sürer.\n  Hazırsan Enter'a bas."
    read -r _
    claude || true
  fi
  not_ "Claude Code $(claude --version 2>/dev/null | head -1)"
fi

# ---------------------------------------------------------------- GitHub'dan güncelleme (paket GitHub'dan geldiyse)
DEPO_DIZIN=""
if [ -n "$DEPO" ]; then
  adim "Güncelleme bağlantısı: GitHub ($DEPO)"
  if [ -d "$KAYNAK/.git" ]; then DEPO_DIZIN="$KAYNAK"; else DEPO_DIZIN="${STUDYO_DEPO_DIZIN:-$HEDEF/.depo}"; fi
  if [ ! -d "$DEPO_DIZIN/.git" ]; then
    if ! gh auth status -h github.com >/dev/null 2>&1; then
      [ -z "$TEST" ] || { not_ "Deneme: GitHub girişi yok, bağlantı atlandı."; DEPO_DIZIN=""; }
      if [ -z "$TEST" ]; then
        printf "\n  \033[1mGitHub'a giriş yapman gerekiyor\033[0m: stüdyonun güncellemeleri oradan gelir.\n"
        printf "  Ekranda 8 haneli bir kod çıkacak (panoya da kopyalanır). Enter'a basınca tarayıcı açılır: GitHub hesabınla giriş yap,\n"
        printf "  kodu yapıştır ve onayla. Başka bir soru gelirse Enter'a basman yeter.\n"
        gh auth login -h github.com -p https -w -c || hata "GitHub'a giriş yapılamadı."
      fi
    fi
    if [ -n "$DEPO_DIZIN" ]; then
      [ -n "$TEST" ] || gh auth setup-git -h github.com
      rm -rf "$DEPO_DIZIN"
      gh repo clone "$DEPO" "$DEPO_DIZIN" -- -q \
        || hata "Depo indirilemedi ($DEPO). GitHub'daki daveti kabul ettin mi? Kabul edip Kur.command'ı yeniden çalıştır."
    fi
  fi
  [ -z "$DEPO_DIZIN" ] || not_ "Güncellemeler $DEPO deposundan gelir (yerel kopya: $DEPO_DIZIN)."
fi

# ---------------------------------------------------------------- 7. ACE-Step (isteğe bağlı) ve son kontrol
adim "7/7 Son kontrol"
if [ -z "$TEST" ] && [ ! -x "$HEDEF/araclar/ACE-Step-1.5/.venv/bin/python" ]; then
  ACE=""
  if [ "${1:-}" = "--ace" ]; then ACE=e; else
    printf "  ACE-Step müzik modelini de kurayım mı? Yapay zekâyla müzik üretir; ≈12 GB indirir, 20–40 dk sürer.\n"
    printf "  Kurmazsan stüdyo kodla üretilen müzikle çalışır; sonra 'bash Kur.command --ace' ile kurabilirsin. [e/H] "
    read -r ACE
  fi
  if [[ "$ACE" == [eE]* ]]; then
    mkdir -p "$HEDEF/araclar"
    [ -d "$HEDEF/araclar/ACE-Step-1.5/.git" ] || git clone https://github.com/ACE-Step/ACE-Step-1.5.git "$HEDEF/araclar/ACE-Step-1.5"
    git -C "$HEDEF/araclar/ACE-Step-1.5" checkout -q "$ACE_COMMIT"
    (cd "$HEDEF/araclar/ACE-Step-1.5" && uv sync && uv run acestep-download && uv run acestep-download -m acestep-5Hz-lm-0.6B --skip-main)
    ./st katalog ses >/dev/null 2>&1 || true
  fi
fi
./st katalog --indeks
./st tip >/dev/null || hata "Sahne kodu derlenmiyor (./st tip)."
./st durum >/dev/null || hata "./st durum çalışmadı."
not_ "Stüdyo çalışıyor."

if [ -z "$TEST" ]; then
  KISAYOL="$HOME/Desktop/Stüdyo Paneli.command"
  printf '#!/bin/sh\nexec "%s/Panel.command"\n' "$HEDEF" > "$KISAYOL"
  chmod +x "$KISAYOL"
  printf "\n\033[1;32m✓ Kurulum tamam.\033[0m\n  Panel: masaüstündeki \"Stüdyo Paneli\" (ya da %s/Panel.command) → http://localhost:4777\n" "$HEDEF"
  if [ -n "$DEPO_DIZIN" ]; then
    GKISAYOL="$HOME/Desktop/Stüdyoyu Güncelle.command"
    printf '#!/bin/sh\nexec "%s/Guncelle.command"\n' "$DEPO_DIZIN" > "$GKISAYOL"
    chmod +x "$GKISAYOL"
    printf "  Panel şimdi açılıyor. Güncellemek için masaüstündeki \"Stüdyoyu Güncelle\"ye çift tıklaman yeter.\n"
  else
    printf "  Panel şimdi açılıyor. Yeni bir zip gelirse onu açıp yine Kur.command'ı çalıştırman yeter.\n"
  fi
  "$HEDEF/Panel.command" || true
else
  printf "\n✓ Paket denemesi tamam: %s\n" "$HEDEF"
fi
bitir 0
