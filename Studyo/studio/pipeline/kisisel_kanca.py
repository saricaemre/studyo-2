"""Kişisel verinin bekçisi: panelin arka plan Claude'u (claude -p --settings) dosya, arama, komut ve Magnific araçlarını çağırmadan önce bunu çalıştırır.

Kişisel etki filminin veri dosyaları ve kişiye özel çıktıları videos/<id>/toplu/ altındadır (CLAUDE.md kural 2; README → Kişisel etki filmi).
Claude bu klasörü okumaz, aramaz, değiştirmez, Magnific'e göndermez; işlemeyi yalnız ./st yapar. Kullanıcının kararları (toplu üretimi başlatmak,
önizleme, kurum verisi kararları, silme) panelden verilir: Claude yalnız şablonu, raporların listesini ve doğrulamayı (ad ve değer içermez) görür.
Girdi (stdin): Claude Code'un PreToolUse olayı (tool_name, tool_input, cwd). Çıkış 2 = çağrıyı durdur, stderr'deki neden Claude'a gider. Çıkış 0 = geç.
"""
import json
import re
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent
NEDEN = ("Kişisel veri (videos/<id>/toplu/: kişisel etki filminin veri dosyaları ve kişiye özel filmler) bu bilgisayarda kalır: Claude okumaz, aramaz, "
         "değiştirmez, başka bir servise göndermez. Toplu üretimi, önizlemeyi, kurum verisi kararlarını ve silmeyi kullanıcı panelden yapar "
         "(Teslim → Kişisel filmler). Sen şablonu (veri_sablonu.json) ve ./st toplu <id> sablon|liste|denetle çıktısını (ad ve değer içermez) kullanabilirsin.")
SERBEST = re.compile(r"^\s*\./st\s+toplu\s+[a-z0-9_]+\s+(sablon|liste|denetle)\b")


def korunan() -> list[Path]:
    """İçinde dosya olan toplu/ klasörleri (boşsa korunacak veri yok)."""
    return [d.resolve() for d in (STUDIO / "videos").glob("*/toplu") if d.is_dir() and any(d.iterdir())]


def _yol(p, cwd: Path) -> Path:
    q = Path(str(p)).expanduser()
    return (q if q.is_absolute() else cwd / q).resolve()


def icinde(p: Path, K: list[Path]) -> bool:
    return any(p == d or d in p.parents for d in K)


def kapsar(p: Path, K: list[Path]) -> bool:
    """p, korunan bir klasörün üstü mü (arama oraya da iner)?"""
    return any(p == d or p in d.parents for d in K)


def _metinler(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _metinler(v)
    elif isinstance(x, list):
        for v in x:
            yield from _metinler(v)


def karar(ad: str, girdi: dict, cwd: Path, K: list[Path]) -> str | None:
    """Engel nedeni ya da None (geç)."""
    if not K and ad != "Bash":
        return None
    if ad in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        p = girdi.get("file_path") or girdi.get("notebook_path")
        return NEDEN if p and icinde(_yol(p, cwd), K) else None
    if ad == "Glob":
        p = _yol(girdi.get("path") or cwd, cwd)
        return NEDEN if icinde(p, K) or (kapsar(p, K) and "toplu" in str(girdi.get("pattern", ""))) else None
    if ad == "Grep":
        p = _yol(girdi.get("path") or cwd, cwd)
        if icinde(p, K) or kapsar(p, K):
            return NEDEN + " Bu arama kişisel veri klasörüne de iner: aramayı daha dar bir klasörle yap (ör. src/<id>/, videos/<id>/script.json)."
        return None
    if ad == "Bash":
        c = str(girdi.get("command", ""))
        if re.search(r"\btoplu\b", c) and not SERBEST.match(c):
            return NEDEN
        return None
    if ad.startswith("mcp__"):
        return NEDEN if any(re.search(r"(^|/)toplu/", s) for s in _metinler(girdi)) else None
    return None


def main():
    try:
        d = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    neden = karar(str(d.get("tool_name", "")), d.get("tool_input") or {}, Path(d.get("cwd") or STUDIO), korunan())
    if neden:
        print(neden, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
