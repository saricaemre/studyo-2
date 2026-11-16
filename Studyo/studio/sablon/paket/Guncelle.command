#!/bin/bash
# Stüdyoyu GitHub'daki son sürüme günceller: depodaki yeni sürümü çeker, sonra Kur.command kurulumu yeniler
# (videoların, markaların, ayarların ve çıktıların korunur). Masaüstündeki "Stüdyoyu Güncelle" bunu çalıştırır.
# Bu klasör deponun yalnız aynasıdır: elle değiştirilen dosya son sürümle değiştirilir.
set -eo pipefail

D="$(cd "$(dirname "$0")" && pwd)"
[ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
DEPO="$(tr -d '[:space:]' < "$D/depo.txt" 2>/dev/null || true)"

dur() {
  printf "\n\033[1;31m✗ %s\033[0m\n  Bu pencerenin ekran görüntüsüyle stüdyonun GitHub sayfasında bir issue aç.\n" "$1"
  [ -n "${STUDYO_TEST:-}" ] || { printf "\nKapatmak için Enter'a bas."; read -r _; }
  exit 1
}

clear 2>/dev/null || true
printf "\033[1mStüdyo güncelleniyor\033[0m · %s\n" "${DEPO:-GitHub}"
if ! git -C "$D" fetch -q origin main; then
  # giriş süresi dolmuş olabilir: bir kez yeniden giriş
  command -v gh >/dev/null 2>&1 && ! gh auth status -h github.com >/dev/null 2>&1 || dur "Yeni sürüm indirilemedi. İnternet bağlantını kontrol et."
  printf "  GitHub'a yeniden giriş gerekiyor: Enter'a bas, tarayıcıda giriş yap ve ekrandaki kodu (panoda) yapıştır.\n"
  gh auth login -h github.com -p https -w -c && gh auth setup-git -h github.com || dur "GitHub'a giriş yapılamadı."
  git -C "$D" fetch -q origin main || dur "Yeni sürüm indirilemedi."
fi
ONCE="$(git -C "$D" rev-parse --short HEAD)"
git -C "$D" reset -q --hard origin/main
SONRA="$(git -C "$D" rev-parse --short HEAD)"
if [ "$ONCE" = "$SONRA" ]; then
  printf "  Yeni sürüm yok (%s); kurulum yine de denetleniyor.\n" "$SONRA"
else
  printf "  Yeni sürüm indi: %s → %s · %s\n" "$ONCE" "$SONRA" "$(git -C "$D" log -1 --format=%s)"
fi
exec bash "$D/Kur.command" "$@"
