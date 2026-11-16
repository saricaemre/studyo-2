"""./st paket: stüdyoyu başka bir Apple Silicon Mac'e göndermek için kurulum zip'i üretir.

Zip içinde Studyo-kurulum/ klasörü: Kur.command (kurulum + güncelleme), OKUBENI.txt, beceriler/ (HyperFrames becerileri;
panelin arka plan oturumu onları kendisi indiremez) ve Studyo/ (stüdyo). Studyo/ yalnız stüdyonun kendisini taşır: kod, panel,
profiller, katalog, şablonlar, seriler, Blender kiti ve araçları (STUDYO_KLASORLER), zanaat ve öğrenimler, istenen örnek videolar (--ornek, varsayılan ihh_sofra) ve istenen
marka kitleri (--marka, varsayılan yok). Gizli ayarlar (.env), kişisel veri (videos/<id>/toplu/: kişisel etki filminin veri dosyaları
ve kişiye özel çıktıları; KVKK), 3B model kütüphanesi (kutuphane/3b; lisans paylaşıma izin vermez),
öteki videolar, istekler, ara çıktılar, node_modules, .venv ve
ACE-Step pakete girmez; Kur.command bunları hedef makinede kurar. Aynı zip güncelleme de yapar (Kur.command kullanıcının
videolarına, markalarına ve ayarlarına dokunmaz).

--depo <sahip/ad>: aynı klasör ağacı zip yerine özel bir GitHub deposuna gider (depo_gonder). Depoya ayrıca Guncelle.command
(son sürümü çekip Kur.command'ı çalıştırır), README.md (GitHub sayfasındaki ilk kurulum) ve depo.txt girer; Kur.command depo.txt'i
görünce karşı makinede GitHub'a giriş yaptırır, depoyu ~/Studyo/.depo'ya klonlar ve masaüstüne "Stüdyoyu Güncelle" koyar.
"""
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path

import ortak as O

BECERILER = ["hyperframes", "hyperframes-animation", "hyperframes-audio", "hyperframes-cli", "hyperframes-core", "hyperframes-creative",
             "hyperframes-keyframes", "hyperframes-registry", "hyperframes-studio", "general-video", "media-use", "motion-graphics"]
HER_ZAMAN = {"__pycache__", ".DS_Store", ".hyperframes", ".thumbnails", ".waveform-cache", "node_modules"}
STUDIO_DOSYALAR = ["st", "package.json", "package-lock.json", "tsconfig.json", "requirements.txt", "requirements-manim.txt", ".env.ornek",
                   "zanaat.md", "hf/CLAUDE.md", "blender/CLAUDE.md", "manim/CLAUDE.md"]
# Stüdyonun kendi klasörleri, filmlerin klasörleriyle aynı üst klasörde (public/<id>/, blender/<id>/): pakete girer ve her güncellemede
# yenilenir. Tek liste: paket bunu Kur.command'ın yanına yenile.txt olarak yazar; Kur.command güncellemede üst klasörü (filmleri)
# korur, yalnız bu klasörleri yeniler. Değer: kopyalanmayan alt adlar.
STUDYO_KLASORLER = {
    "public/textures": (),          # dokular
    "public/uc": ("_onizleme",),    # GLB çözücüleri (three'nin kendi dosyaları); modeller ve önizlemeleri değil
    "public/fontlar": (),           # değişken yazı aileleri (niyetli altyazı, kişisel film: Roboto Flex, OFL)
    "blender/kit": (),              # Blender sahne kiti
    "blender/eevee": (),            # EEVEE çizeri
    "blender/yapim": (),            # yapım filminin geçişleri (kil, tel kafes, kamera yolu)
    "blender/takip": (),            # kamera takibi: çözücü ve sahne modülü
    "blender/karma": (),            # karma filmin saydam Blender sahnesi sarmalayıcısı (6b)
    "manim/kit": (),                # Manim sahne kiti (6c; Manim'in kendisi isteğe bağlı: requirements-manim.txt)
}


def _yoksay(*ek):
    """shutil.copytree için: her zaman atılanlar + verilen adlar/kalıplar + bozuk bağlantılar."""
    def f(dizin, adlar):
        d = Path(dizin)
        return {a for a in adlar if a in HER_ZAMAN or a in ek or any(a.startswith(k[:-1]) for k in ek if k.endswith("*"))
                or (d / a).is_symlink()}
    return f


def _kopya(src: Path, dst: Path, *ek):
    if src.is_dir():
        shutil.copytree(src, dst, ignore=_yoksay(*ek))
    elif src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def root_temizle(metin: str, cikar_dizin: set[str], cikar_id: set[str]) -> str:
    """src/Root.tsx: pakete girmeyen Remotion videolarının import ve kompozisyon kayıtlarını çıkarır."""
    adlar, out = set(), []
    for ln in metin.splitlines(keepends=True):
        m = re.match(r"\s*import (.+?) from '(.+?)';", ln)
        if m and (any(m.group(2).startswith(f"./{d}/") for d in cikar_dizin) or any(f"/public/{i}/" in m.group(2) for i in cikar_id)):
            adlar |= set(re.findall(r"[A-Za-z_]\w*", m.group(1)))
            continue
        out.append(ln)
    s = "".join(out)
    bul = lambda blok: any(re.search(rf"\b{re.escape(a)}\b", blok) for a in adlar)
    return re.sub(r"[ \t]*<(?:Composition|Still)\b.*?/>[ \t]*\n", lambda m: "" if bul(m.group(0)) else m.group(0), s, flags=re.S)


def root_birlestir(paketteki: str, kurulu: str) -> str:
    """Güncellemede src/Root.tsx (Kur.command korur: karşı tarafın film kayıtları): `@st:kompozisyon` işaretinin altı (stüdyonun
    kendi kompozisyonları: katalog önizlemeleri, yapım filmi …) paketteki hâliyle yenilenir, onların kurulu dosyada olmayan
    importları `// @st:import`'un üstüne eklenir. İşaretin üstü (filmler) aynen kalır."""
    IS, IM = "{/* @st:kompozisyon */}", "// @st:import"
    if not all(IS in x and IM in x and "</>" in x for x in (paketteki, kurulu)):
        return kurulu
    blok = paketteki[paketteki.index(IS) + len(IS):paketteki.rindex("</>")]
    s = kurulu[:kurulu.index(IS) + len(IS)] + blok + kurulu[kurulu.rindex("</>"):]
    ad = lambda m: set(re.findall(r"[A-Za-z_]\w*", m.group(1).replace(" as ", " ")))  # noqa: E731
    imp = re.compile(r"\s*import (.+?) from '(.+?)';")
    var = set().union(*[ad(m) for ln in s.splitlines() if (m := imp.match(ln))])
    kullanilan = set(re.findall(r"[A-Za-z_]\w*", blok))
    eksik = [ln for ln in paketteki.splitlines() if (m := imp.match(ln)) and ad(m) & kullanilan and not ad(m) & var]
    return s.replace(IM, "\n".join(eksik + [IM]), 1) if eksik else s


def claude_md_temizle(metin: str, ornekler: list[str], markalar: list[str]) -> str:
    """Kök CLAUDE.md: "Mevcut durum" yeni kurulum için yeniden yazılır; pakete girmeyen marka ve konseptlere atıf kalmaz."""
    bas = metin.split("## Mevcut durum")[0]
    if "ihh" not in markalar:
        bas = bas.replace("(hazır: `ihh`)", "(yeni kit: `studio/sablon/marka/` şablonunu `studio/markalar/<ad>/` olarak kopyala)")
    bas = re.sub(r"- `konseptler/`: içerik konseptleri\..*\n", "- `konseptler/`: içerik konseptleri (boş başlar)\n", bas)
    satir = [f"## Mevcut durum ({dt.date.today().isoformat()}, yeni kurulum)",
             "- Stüdyo paketten kuruldu (`./st paket`). Kanalın yönü ve adı açık: kullanıcı karar verir."]
    if "ihh_sofra" in ornekler:
        satir.append("- Örnek video `ihh_sofra` (reklam-kisa · hyperframes · 16x9 + 9x16 + 1x1 · İngilizce): stüdyo dışında HyperFrames'te yapılmış "
                     "illüstrasyonlu kampanya filmi, stüdyoya alındı (`ice_aktarim`). Kör eleştiri ve en büyük 3 kusur `inceleme/v1/`'de; "
                     "F yolunun (stilize illüstrasyon dünyası) ve HyperFrames motorunun nasıl kullanıldığını gösterir.")
    for o in ornekler:
        if o != "ihh_sofra":
            satir.append(f"- Örnek video `{o}`.")
    satir += ["- Gerçek görüntü (zanaat §2 yol B ve D: kendi çekim, kurum arşivi, açık lisans) yerelde çalışır; yapay zekâ plakaları (yol C), "
              "stok ve Magnific anlatıcısı yalnız Magnific bağlıysa (bağlı değilse panel bu seçenekleri gizler).",
              "- ACE-Step müzik modeli isteğe bağlı: `bash Kur.command --ace` (kurulum zip'inden) ya da `araclar/ACE-Step-1.5` yoksa müzik kodla üretilir."]
    return bas + "\n".join(satir) + "\n"


def readme_temizle(metin: str, markalar: list[str]) -> str:
    if "ihh" not in markalar:
        metin = re.sub(r"Hazır: `ihh` \(.*?\)\.", "Şablon: `sablon/marka/` (kopyala, kurumun resmi kaynağından doldur).", metin)
    return metin


def agac(ornekler: list[str], markalar: list[str], depo: str | None = None) -> Path:
    """Paketin klasör ağacı (out/_paket/Studyo-kurulum): zip de GitHub deposu da bunu taşır. depo verilirse güncelleme betiği,
    GitHub sayfası ve depo adı da girer."""
    K, S = O.KANAL, O.ROOT
    for o in ornekler:
        if not (S / "videos" / o).exists():
            raise SystemExit(f"Örnek video yok: {o}")
    for m in markalar:
        if not (S / "markalar" / m / "marka.json").exists():
            raise SystemExit(f"Marka kiti yok: {m}")
    tmp = S / "out" / "_paket"
    shutil.rmtree(tmp, ignore_errors=True)
    P = tmp / "Studyo-kurulum"
    T = P / "Studyo"
    TS = T / "studio"

    # kurulum betikleri ve beceriler
    _kopya(S / "sablon" / "paket" / "Kur.command", P / "Kur.command")
    (P / "Kur.command").chmod(0o755)
    _kopya(S / "sablon" / "paket" / "OKUBENI.txt", P / "OKUBENI.txt")
    if depo:
        _kopya(S / "sablon" / "paket" / "Guncelle.command", P / "Guncelle.command")
        (P / "Guncelle.command").chmod(0o755)
        _kopya(S / "sablon" / "paket" / "README-depo.md", P / "README.md")
        (P / "depo.txt").write_text(depo + "\n")
    sk = Path.home() / ".claude" / "skills"
    for b in BECERILER:
        _kopya(sk / b, P / "beceriler" / b)

    # kök
    (T).mkdir(parents=True)
    (T / "CLAUDE.md").write_text(claude_md_temizle((K / "CLAUDE.md").read_text(), ornekler, markalar))
    _kopya(K / "Panel.command", T / "Panel.command")
    for f in ("youtube.md", "ogrenimler.md"):
        _kopya(K / "kanal" / f, T / "kanal" / f)
    _kopya(K / "referans" / "promptlar", T / "referans" / "promptlar")
    _kopya(K / "referans" / "yontemler.md", T / "referans" / "yontemler.md")      # yöntem kütüphanesi (planda üç yol)
    _kopya(K / "referans" / "kampanyalar", T / "referans" / "kampanyalar")
    for d in ("konseptler", "cikti", "araclar"):
        (T / d).mkdir(exist_ok=True)
    for o in ornekler:
        for f in sorted((K / "cikti").glob(f"{o}_*")):
            _kopya(f, T / "cikti" / f.name)

    # stüdyo: kod, panel, profiller, katalog, şablonlar, seriler
    for f in STUDIO_DOSYALAR:
        _kopya(S / f, TS / f)
    (TS / "README.md").write_text(readme_temizle((S / "README.md").read_text(), markalar))
    _kopya(S / "pipeline", TS / "pipeline")
    _kopya(S / "panel", TS / "panel", "isler", "panel.log", "onbellek", "eski", "tasarim")
    for d in ("profiller", "sablon", "stiller"):
        _kopya(S / d, TS / d)
    _kopya(S / "katalog", TS / "katalog", "assets")  # HyperFrames örneklerinin assets/ klasörü önizlemede yeniden kurulur
    for d in ("istekler", "markalar", "out", "videos", "hf", "public", "blender", "manim"):
        (TS / d).mkdir(exist_ok=True)
    for m in markalar:
        _kopya(S / "markalar" / m, TS / "markalar" / m)
    for d, ek in STUDYO_KLASORLER.items():
        _kopya(S / d, TS / d, *ek)
    (P / "yenile.txt").write_text("".join(f"{d}\n" for d in STUDYO_KLASORLER))

    # src: pakete girmeyen Remotion videolarının kaynağı ve kaydı çıkar
    tum = {p.name: O.load(p.name) for p in (S / "videos").iterdir() if (p / "script.json").exists()}
    disari = {vid: v for vid, v in tum.items() if vid not in ornekler and v.motor != "hyperframes"}
    cikar_dizin = {v.script.get("kod") or (vid if (S / "src" / vid).exists() else None) for vid, v in disari.items()} - {None}
    # eski videolarda kaynak klasörü kimlikten farklı olabilir (gemiler_karadan → src/gemiler): Root.tsx'teki importlardan bul
    root = (S / "src" / "Root.tsx").read_text()
    for vid, v in disari.items():
        m = re.search(rf"import \{{{v.comp}\}} from '\./([^/]+)/", root)
        if m:
            cikar_dizin.add(m.group(1))
    _kopya(S / "src", TS / "src")
    for d in cikar_dizin:
        shutil.rmtree(TS / "src" / d, ignore_errors=True)
    (TS / "src" / "Root.tsx").write_text(root_temizle(root, cikar_dizin, set(disari)))

    # örnek videolar
    for o in ornekler:
        # kişisel etki filmi: veri dosyaları ve kişisel çıktılar (toplu/) bu bilgisayarda kalır, pakete girmez (KVKK; README → Kişisel etki filmi)
        _kopya(S / "videos" / o, TS / "videos" / o, "kareler-*", "claude.json", "toplu")
        _kopya(S / "public" / o, TS / "public" / o, "_tts", "3b")  # 3B modeller (threejsassets) paylaşılmaz: karşı taraf kendi hesabıyla indirir
        if (S / "blender" / o).exists():
            _kopya(S / "blender" / o, TS / "blender" / o)
        if (S / "manim" / o).exists():   # karma filmin Manim sahneleri (6c)
            _kopya(S / "manim" / o, TS / "manim" / o)
        if (S / "hf" / o).exists():
            _kopya(S / "hf" / o, TS / "hf" / o, "_fmt", "_gorunus")
            for d in ("assets/ses", "assets/lib"):  # ./st her komutta yeniden kurar (miks ve yerel GSAP)
                shutil.rmtree(TS / "hf" / o / d, ignore_errors=True)
        for f in sorted((S / "out").glob(f"{o}_*_kaba.mp4")) + sorted((S / "out").glob(f"{o}_kaba.mp4")):
            _kopya(f, TS / "out" / f.name)
    (TS / "SURUM.txt").write_text(f"Stüdyo paketi · {dt.datetime.now():%Y-%m-%d %H:%M} · örnekler: {', '.join(ornekler) or '—'} · markalar: {', '.join(markalar) or '—'}\n")

    gizli = [p for p in T.rglob(".env") if p.is_file()]
    if gizli:
        raise SystemExit(f"Gizli ayar pakete girmiş: {gizli}")
    kisisel = [p for p in (TS / "videos").glob("*/toplu")] + [p for p in TS.rglob("_is.json") if "toplu" in p.parts]
    if kisisel:
        raise SystemExit(f"Kişisel veri pakete girmiş (videos/<id>/toplu/ bu bilgisayarda kalır): {[str(p.relative_to(T)) for p in kisisel]}")
    return P


def uret(ornekler: list[str], markalar: list[str], hedef: Path) -> Path:
    P = agac(ornekler, markalar)
    hedef.mkdir(parents=True, exist_ok=True)
    zipp = hedef / f"Studyo-kurulum-{dt.date.today().isoformat()}.zip"
    zipp.unlink(missing_ok=True)
    subprocess.run(["ditto", "-c", "-k", "--norsrc", "--noextattr", "--keepParent", str(P), str(zipp)], check=True)
    shutil.rmtree(P.parent, ignore_errors=True)
    return zipp


# ---------------------------------------------------------------- GitHub deposu (--depo)
DEPO_YEREL = O.ROOT / "out" / "_depo"   # deponun bu bilgisayardaki aynası (yalnız gönderim için; elle düzenlenmez)
GITHUB_SINIR = 95e6                     # GitHub 100 MB'tan büyük dosyayı reddeder
SURUM = "Studyo/studio/SURUM.txt"       # her pakette değişen damga: tek başına değişiklik sayılmaz


def _calis(*komut, sorun: str | None = None) -> subprocess.CompletedProcess:
    r = subprocess.run([str(k) for k in komut], capture_output=True, text=True)
    if sorun and r.returncode:
        raise SystemExit(f"{sorun}: {(r.stderr or r.stdout).strip()}")
    return r


def depo_gonder(ornekler: list[str], markalar: list[str], depo: str) -> tuple[str, bool]:
    """Paketi özel GitHub deposuna gönderir → (adres, yeni sürüm gitti mi). Depo yoksa özel açılır; herkese açıksa durur.
    Yalnız SURUM.txt değiştiyse gönderilmez."""
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", depo):
        raise SystemExit(f"Depo adı sahip/ad olmalı: {depo}")
    r = _calis("gh", "repo", "view", depo, "--json", "visibility,url")
    if r.returncode:
        if "Could not resolve" not in r.stderr:
            raise SystemExit(f"GitHub'a ulaşılamadı (gh auth status): {r.stderr.strip()}")
        _calis("gh", "repo", "create", depo, "--private", "--description", "Stüdyo: kurulum ve güncelleme", sorun="Depo açılamadı")
        r = _calis("gh", "repo", "view", depo, "--json", "visibility,url", sorun="Depo okunamadı")
    bilgi = json.loads(r.stdout)
    if bilgi["visibility"] != "PRIVATE":
        raise SystemExit(f"{depo} herkese açık: stüdyo yalnız özel depoya gönderilir.")

    P = agac(ornekler, markalar, depo)
    buyuk = [p for p in P.rglob("*") if p.is_file() and p.stat().st_size > GITHUB_SINIR]
    if buyuk:
        raise SystemExit(f"GitHub 100 MB'tan büyük dosya almaz: {[str(p.relative_to(P)) for p in buyuk]}")
    D = DEPO_YEREL / depo.replace("/", "__")
    if not (D / ".git").exists():
        shutil.rmtree(D, ignore_errors=True)
        D.parent.mkdir(parents=True, exist_ok=True)
        _calis("gh", "repo", "clone", depo, D, sorun="Depo klonlanamadı")
    else:
        _calis("git", "-C", D, "fetch", "-q", "origin", sorun="Depo çekilemedi")
        if _calis("git", "-C", D, "rev-parse", "-q", "--verify", "origin/main").returncode == 0:
            _calis("git", "-C", D, "reset", "-q", "--hard", "origin/main", sorun="Ayna eşitlenemedi")
    if _calis("git", "-C", D, "rev-parse", "-q", "--verify", "HEAD").returncode:  # boş depo: ilk sürüm main dalına
        _calis("git", "-C", D, "symbolic-ref", "HEAD", "refs/heads/main", sorun="Dal kurulamadı")
    subprocess.run(["rsync", "-a", "--delete", "--exclude=/.git", f"{P}/", f"{D}/"], check=True)
    shutil.rmtree(P.parent, ignore_errors=True)
    (DEPO_YEREL / "depo.txt").write_text(depo + "\n")

    _calis("git", "-C", D, "add", "-A", sorun="git add")
    ilk = _calis("git", "-C", D, "rev-parse", "-q", "--verify", "HEAD").returncode != 0
    if not ilk and _calis("git", "-C", D, "diff", "--cached", "--quiet", "--", ".", f":!{SURUM}").returncode == 0:
        _calis("git", "-C", D, "reset", "-q", "--hard", "HEAD")
        return bilgi["url"], False
    mesaj = f"Stüdyo {dt.datetime.now():%Y-%m-%d %H:%M} · örnekler: {', '.join(ornekler) or '—'} · markalar: {', '.join(markalar) or '—'}"
    _calis("git", "-C", D, "commit", "-q", "-m", mesaj, sorun="git commit")
    _calis("git", "-C", D, "push", "-q", "-u", "origin", "HEAD:main", sorun="Depoya gönderilemedi")
    return bilgi["url"], True


# ---------------------------------------------------------------- açık kaynak sürüm (--acik)
ACIK_YEREL = O.ROOT / "out" / "_acik"   # herkese açık deponun yerel hâli (git, tek commit; gönderim kullanıcının onayıyla)
# açık sürüme girmeyenler (P'ye göre): üçüncü tarafın içeriği, taslak katalog kartı, Magnific sesiyle üretilmiş örnek
ACIK_CIKAR = ["beceriler",                                    # HyperFrames becerileri: Kur.command resmi kaynağından kurar
              "Studyo/referans/promptlar",                    # başkalarının istemleri (yazarlarının adıyla)
              "Studyo/studio/katalog/_referanslar",           # kullanıcı referansları (taslak kartın kaynağı)
              "Studyo/studio/katalog/onizleme/anlatici",      # Magnific/ElevenLabs anlatıcı örneği
              "Studyo/studio/katalog/gorsel/neseli-sofra.json",  # onay bekleyen taslak kart
              "Studyo/studio/sablon/acik"]                    # açık sürümün kendi şablonu ve temizlik listesi
ACIK_TASLAK_KARTLAR = ["neseli-sofra"]
ACIK_TEMIZLE = O.ROOT / "sablon" / "acik" / "temizle.json"  # metin değişiklikleri ve aranacak kişisel atıflar (açık sürüme girmez)


def acik_agac(ornekler: list[str] | None = None, markalar: list[str] | None = None) -> Path:
    """Herkese açık GitHub deposunun ağacı (ACIK_YEREL/studyo): örnek film ve marka kiti yok, üçüncü taraf içerik yok,
    LICENSE (MIT), README, UCUNCU_TARAF.md, .gitignore. Gizli ayar ve kişisel veri taraması agac()'takiyle aynı + kişi adları."""
    ornekler, markalar = ornekler or [], markalar or []
    P = agac(ornekler, markalar)
    for c in ACIK_CIKAR:
        p = P / c
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    K = P / "Studyo" / "studio" / "katalog"
    for ad in ACIK_TASLAK_KARTLAR:
        for f in (K / "onizleme" / "gorsel").glob(f"{ad}*"):
            f.unlink()
    ind = K / "indeks.json"
    if ind.exists():
        d = json.loads(ind.read_text())
        d["gorsel"] = [k for k in d.get("gorsel", []) if k.get("ad") not in ACIK_TASLAK_KARTLAR]
        ind.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    A = O.ROOT / "sablon" / "acik"
    _kopya(A / "promptlar-indeks.md", P / "Studyo" / "referans" / "promptlar" / "indeks.md")
    for f in ("README.md", "LICENSE", "UCUNCU_TARAF.md", ".gitignore"):
        _kopya(A / f, P / f)
    # Mevcut durum: açık sürüm için
    cm = P / "Studyo" / "CLAUDE.md"
    bas = cm.read_text().split("## Mevcut durum")[0]
    cm.write_text(bas + "## Mevcut durum (açık kaynak sürüm)\n"
                  "- Stüdyo açık kaynak depodan kuruldu" + (f" (marka kiti: {', '.join(markalar)})" if markalar else ": marka kiti yok") + "; film arşivi yok. Kanalın ya da işin yönü ve adı açık: kullanıcı karar verir.\n"
                  + ("- Örnek film `ihh_sofra` (reklam-kisa · hyperframes · 16x9 + 9x16 + 1x1 · İngilizce): illüstrasyonlu İHH kampanya filmi; kör eleştiri ve "
                     "en büyük 3 kusur `inceleme/v1/`'de. F yolunun (stilize illüstrasyon dünyası) ve HyperFrames motorunun nasıl kullanıldığını gösterir.\n"
                     if "ihh_sofra" in ornekler else "")
                  + "".join(f"- Örnek film `{o}`.\n" for o in ornekler if o != "ihh_sofra") +
                  "- Gerçek görüntü (yol B ve D) yerelde çalışır; yapay zekâ plakaları (yol C), stok ve Magnific anlatıcısı yalnız kullanıcı kendi Magnific hesabını "
                  "bağlarsa (bağlı değilse panel bu seçenekleri gizler).\n"
                  "- ACE-Step müzik modeli isteğe bağlı (`bash Kur.command --ace`); yoksa müzik kodla üretilir.\n"
                  "- `referans/promptlar/` boş gelir; `kanal/ogrenimler.md` ve `referans/` geliştirme sırasındaki filmlere (`yol-haritasi/`, deneme filmleri) atıf yapar, "
                  "o klasörler depoda yok.\n")
    tz = json.loads(ACIK_TEMIZLE.read_text())
    degistir = [(re.compile(k), y) for k, y in tz["degistir"]]
    for f in P.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".txt", ".py", ".js", ".json", ".command", ".tsx", ".ts", ".html", ".css"):
            t = f.read_text(errors="ignore")
            y = t
            for kalip, yerine in degistir:
                y = kalip.sub(yerine, y)
            if y != t:
                f.write_text(y)
    kalan = [str(f.relative_to(P)) for f in P.rglob("*") if f.is_file() and f.name != "LICENSE"   # LICENSE: telif sahibi bilerek
             and f.suffix not in (".png", ".jpg", ".mp4", ".mp3", ".wasm", ".woff2")
             and re.search(tz["yasak"], f.read_text(errors="ignore"), re.I)]
    if kalan:
        raise SystemExit(f"Kişisel atıf açık sürüme girmiş: {kalan}")
    H = ACIK_YEREL / "studyo"
    eski_git = H / ".git"
    if eski_git.exists():  # var olan yerel deponun geçmişi korunur, içerik yenilenir
        subprocess.run(["rsync", "-a", "--delete", "--exclude=/.git", f"{P}/", f"{H}/"], check=True)
    else:
        shutil.rmtree(H, ignore_errors=True)
        H.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(P), str(H))
    shutil.rmtree(P.parent, ignore_errors=True)
    buyuk = [str(p.relative_to(H)) for p in H.rglob("*") if p.is_file() and ".git" not in p.parts and p.stat().st_size > GITHUB_SINIR]
    if buyuk:
        raise SystemExit(f"GitHub 100 MB'tan büyük dosya almaz: {buyuk}")
    return H


def acik_commit(H: Path) -> bool:
    """Yerel açık depoda commit (gönderim yok). Değişiklik yoksa False."""
    if not (H / ".git").exists():
        _calis("git", "-C", H, "init", "-q", "-b", "main", sorun="git init")
    if _calis("git", "-C", H, "config", "--local", "user.email").returncode:
        # herkese açık geçmişe kişisel e-posta girmez: GitHub'ın gizli (noreply) adresi, depoya özel
        r = _calis("gh", "api", "user", "--jq", '.login + " " + (.id|tostring)')
        if r.returncode:
            raise SystemExit("GitHub hesabı okunamadı (gh auth status): commit kimliği kişisel e-postayla atılmasın diye duruldu.")
        login, uid = r.stdout.split()
        _calis("git", "-C", H, "config", "user.name", login, sorun="git config")
        _calis("git", "-C", H, "config", "user.email", f"{uid}+{login}@users.noreply.github.com", sorun="git config")
    _calis("git", "-C", H, "add", "-A", sorun="git add")
    if _calis("git", "-C", H, "diff", "--cached", "--quiet").returncode == 0:
        return False
    _calis("git", "-C", H, "commit", "-q", "-m", f"Stüdyo açık kaynak sürüm {dt.date.today().isoformat()}", sorun="git commit")
    return True


if __name__ == "__main__":  # Kur.command güncellemede: paketteki Root.tsx'in stüdyo kompozisyonlarını kurulu Root.tsx'e işler
    import sys
    if len(sys.argv) != 4 or sys.argv[1] != "--root-birlestir":
        raise SystemExit("Kullanım: python pipeline/paket.py --root-birlestir <paketteki Root.tsx> <kurulu Root.tsx>")
    pk, ku = Path(sys.argv[2]), Path(sys.argv[3])
    yeni = root_birlestir(pk.read_text(), ku.read_text())
    if yeni != ku.read_text():
        ku.write_text(yeni)
        print("  src/Root.tsx: stüdyonun kompozisyonları paketteki hâliyle yenilendi (film kayıtların aynen).")
