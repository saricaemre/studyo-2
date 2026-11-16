"""Kişisel etki filmi (./st toplu): onaylanmış bir şablon filmden her satıra (her bağışçıya) kendi verisiyle film. Spotify Wrapped mekanizması.

Şablon sözleşmesi videos/<id>/veri_sablonu.json (4d'nin canlı veri sözleşmesi veri.json'dan ayrı; ad karışmasın diye sahnede "kişi"):
  alanlar {<alan>: {ad, tur (kimlik | ad | metin | secim | sayi | para | tarih), zorunlu, ekranda (yazı ekranda: yazı tanımayla denetlenir),
           sahne (yazı değil, sahnenin seçimi: ör. kalemin çizimi), bicim (buyuk | olduğu gibi), en_uzun, secenekler, ondalik, aralik, birim,
           para_birimi, esanlam (sütun adı eşlemesi)}}
  kimlik (çıktı adı olan alan) · yazi {<alan>: {aile, wght, wdth [en dar, normal], boyut [en küçük, en büyük] (1080 kısa kenarda px), satir,
  satir_yuksekligi, hiza (sol | orta), pay}} · kisi_isareti (bütün ekrandaki alanların tam göründüğü işaret: kanıt karesi) · ornek (TEST satırı:
  şablon filmin kendi kareleri, Studio, inceleme) · kurum_verisi (kullanıcının kararları: kaynak, izin, ekranda alanlar, saklama; Claude yazmaz)

Kişisel veri bu bilgisayarda kalır (CLAUDE.md kural 2): veri dosyası ve kişisel çıktılar yalnız videos/<id>/toplu/ altında; işlemeyi yalnız ./st yapar.
Günlüklerde, raporlarda ve hata iletilerinde kimlik ve satır numarası görünür, ad ve değer görünmez. Panelin Claude'u bu klasörü okuyamaz
(pipeline/kisisel_kanca.py), ./st paket almaz (pipeline/paket.py). Sahneye yalnız ekranda ya da sahnede kullanılan alanlar gider (en aza indirme).
Uydurma yok: eksik ya da geçersiz alanlı satır atlanır, nedeni (alan + neden, değer değil) raporlanır; varsayılan değerle doldurulmaz.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

import ortak as O
from yazi_olcu import kelime_genisligi, tablo

SURUM = 1
SABLON = "veri_sablonu.json"
TURLER = ("kimlik", "ad", "metin", "secim", "sayi", "para", "tarih")
SAYI_TURLERI = ("sayi", "para")
TEST = "TEST"                     # bir satır TEST sayılır: "test" sütununda tam olarak TEST yazıyorsa (sahte veri; ekranda plaka yalnız kullanıcı isterse)
EN_KUCUK_PX = 64                  # okunan yazı ≥ 64 px (1080 kısa kenarda; zanaat §4)
KONTRAST = 4.5
MARJ = 0.03                       # ölçü tablosu çekirdek aralığını yok sayar (geniş tahmin); üstüne %3 pay
KIMLIK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
AD_HARF = re.compile(r"^[^\W\d_]+(?:[ \-'’.]+[^\W\d_]+)*\.?$")   # harfle başlar, harfle (ya da kısaltma noktasıyla) biter; arada boşluk, kısa çizgi, kesme, nokta
METIN_IZIN = re.compile(r"^[\w .,;:!?'’\"“”()\-–/&+%№#°]*$")
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
KARAR_ALANLARI = {"kaynak": "Verinin kaynağı (hangi sistem, hangi liste)", "izin": "İzin: açık rıza ya da aydınlatma metni ve hukuki dayanak",
                  "ekranda": "Ekranda görünecek alanlar", "gonderim": "Filmler kime ve nasıl gönderilecek (yalnız kişinin kendisine)",
                  "saklama": "Veri dosyası ve kişisel filmler ne zaman silinecek"}


class AlanHatasi(Exception):
    """Bir alan geçersiz: ileti alanın adı ve nedeni, değer değil (günlükte ad ve değer görünmez)."""


# ---------------------------------------------------------------- dosyalar
def dosya(v) -> Path:
    return v.dir / SABLON


def var_mi(v) -> bool:
    return dosya(v).exists()


def sablon(v) -> dict:
    return O.jload(dosya(v))


def dizin(v) -> Path:
    """Kişisel verinin tek yeri: videos/<id>/toplu/ (veri/: yüklenen dosyalar; <çalışma>/: çıktılar ve rapor; onizleme/). Pakete girmez."""
    return v.dir / "toplu"


def ornek_kopyasi(v) -> Path:
    """Remotion Studio için şablonun TEST örneği (kişisel veri değil): public/<id>/kisisel/ornek.json."""
    return v.pub / "kisisel" / "ornek.json"


# ---------------------------------------------------------------- biçim
def buyuk(s: str) -> str:
    """Türkçe büyük harf (src/lib/gorunus.ts → buyuk ile aynı): i → İ, ı → I."""
    return s.replace("i", "İ").upper()


def _tr_norm(s: str) -> str:
    return re.sub(r"[\s_\-./]+", " ", s.replace("İ", "i").replace("I", "ı").lower()).strip()


def sayi_metni(d: Decimal, ondalik: int = 0, dil: str = "tr") -> str:
    """Ekranda yazılan sayı: binlik ayırıcı (tr '.', en ','), ondalık (tr ',', en '.'), eksi U+2212."""
    q = d.quantize(Decimal(1).scaleb(-ondalik), rounding=ROUND_HALF_UP)
    tam, _, kes = f"{abs(q):.{ondalik}f}".partition(".")
    grup = re.sub(r"(?<=\d)(?=(\d{3})+$)", "." if dil == "tr" else ",", tam)
    s = grup + ((("," if dil == "tr" else ".") + kes) if kes else "")
    return ("−" if q < 0 else "") + s


def sayi_oku(x, ondalik: int) -> Decimal:
    """Sayı: 1250 · 1.250 (tr binlik) · 1250,5 (tr ondalık) · 1.250,50. Belirsiz ya da fazla ondalıklı değer reddedilir (yuvarlanmaz)."""
    if isinstance(x, bool):
        raise AlanHatasi("sayı değil")
    if isinstance(x, (int, float)):
        d = Decimal(str(x))
    else:
        s = str(x).strip().replace(" ", "").replace(" ", "").replace("−", "-")
        if not s:
            raise AlanHatasi("boş")
        if not re.fullmatch(r"-?[\d.,]+", s):
            raise AlanHatasi("sayı değil")
        if "," in s and "." in s:
            if s.rfind(",") < s.rfind("."):
                raise AlanHatasi("sayı biçimi belirsiz (Türkçe: 1.250,50)")
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            if s.count(",") > 1:
                raise AlanHatasi("sayı biçimi belirsiz")
            s = s.replace(",", ".")
        elif "." in s:
            if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):  # Türkçe binlik görünümü: 1.250 · 12.500.000
                if s.count(".") == 1 and ondalik > 0:
                    raise AlanHatasi("sayı biçimi belirsiz (1.250: bin iki yüz elli mi, bir virgül yirmi beş mi?)")
                s = s.replace(".", "")
            elif s.count(".") > 1:
                raise AlanHatasi("sayı biçimi belirsiz")
            # tek nokta ve 3'ten farklı basamak: ondalık nokta (sistem dökümü: 1250.50)
        try:
            d = Decimal(s)
        except InvalidOperation:
            raise AlanHatasi("sayı değil") from None
    if not d.is_finite():
        raise AlanHatasi("sayı değil")
    if -d.as_tuple().exponent > ondalik and d != d.quantize(Decimal(1).scaleb(-ondalik)):
        raise AlanHatasi(f"ondalık basamak fazla (şablon en çok {ondalik}; değer yuvarlanmaz)")
    return d


def tarih_oku(x) -> dt.date:
    s = str(x).strip()
    for kalip in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, kalip).date()
        except ValueError:
            continue
    raise AlanHatasi("tarih değil (2026-03-12 ya da 12.03.2026)")


def tarih_metni(d: dt.date, dil: str = "tr") -> str:
    return f"{d.day} {AYLAR[d.month - 1]} {d.year}" if dil == "tr" else d.strftime("%-d %B %Y")


def _bosluk(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def alan_degeri(A: dict, ham, dil: str = "tr") -> dict:
    """Bir alanın ham değeri → {"deger", "metin"} (metin: ekranda yazılan, Python'da bir kez biçimlenir). Geçersizse AlanHatasi (değersiz neden)."""
    tur = A["tur"]
    bos = ham is None or (isinstance(ham, str) and not ham.strip())
    if bos:
        raise AlanHatasi("boş")
    if tur == "kimlik":
        s = str(ham).strip()
        if not KIMLIK.fullmatch(s):
            raise AlanHatasi("kimlik yalnız harf, rakam, - ve _ (en çok 40; ad değil)")
        return {"deger": s, "metin": s}
    if tur in ("ad", "metin"):
        s = _bosluk(str(ham))
        if len(s) > int(A.get("en_uzun") or (48 if tur == "ad" else 40)):
            raise AlanHatasi(f"çok uzun ({len(s)} > {A.get('en_uzun') or (48 if tur == 'ad' else 40)} karakter)")
        if tur == "ad" and (len(s) < 2 or not AD_HARF.fullmatch(s)):
            raise AlanHatasi("ad yalnız harf, boşluk, kısa çizgi, kesme ve nokta içerir")
        if tur == "metin" and not METIN_IZIN.fullmatch(s):
            raise AlanHatasi("izin verilmeyen karakter")
        return {"deger": s, "metin": buyuk(s) if A.get("bicim") == "buyuk" else s}
    if tur == "secim":
        S = A.get("secenekler") or {}
        s = _bosluk(str(ham))
        anahtar = next((k for k, m in S.items() if _tr_norm(s) in (_tr_norm(k), _tr_norm(m))), None)
        if anahtar is None:
            raise AlanHatasi("şablonun listesinde yok")
        m = S[anahtar]
        return {"deger": anahtar, "metin": buyuk(m) if A.get("bicim") == "buyuk" else m}
    if tur in SAYI_TURLERI:
        ond = int(A.get("ondalik", 2 if tur == "para" else 0))
        d = sayi_oku(ham, ond)
        lo, hi = A.get("aralik") or [None, None]
        if (lo is not None and d < Decimal(str(lo))) or (hi is not None and d > Decimal(str(hi))):
            raise AlanHatasi(f"aralık dışında ({lo}–{hi})")
        m = sayi_metni(d, ond, dil)
        if tur == "para":
            m = f"{m} {A.get('para_birimi', 'TL')}"
        return {"deger": float(d), "metin": m, "sayi": sayi_metni(d, ond, dil)}
    if tur == "tarih":
        d = tarih_oku(ham)
        return {"deger": d.isoformat(), "metin": tarih_metni(d, dil)}
    raise AlanHatasi(f"bilinmeyen tür {tur}")


# ---------------------------------------------------------------- sözleşme
def sablon_sorunlari(S: dict, v=None) -> list[tuple[str, str]]:
    out = []
    A = S.get("alanlar") or {}
    if not A:
        return [("❌", "alanlar yok")]
    for k, a in A.items():
        if a.get("tur") not in TURLER:
            out.append(("❌", f"{k}: tür {a.get('tur')} ({', '.join(TURLER)})"))
        if a.get("tur") == "secim" and not a.get("secenekler"):
            out.append(("❌", f"{k}: seçim alanının secenekler listesi yok"))
        if a.get("ekranda") and a.get("tur") == "kimlik":
            out.append(("❌", f"{k}: kimlik ekranda gösterilmez"))
    kim = S.get("kimlik")
    if not kim or (A.get(kim) or {}).get("tur") != "kimlik" or not A[kim].get("zorunlu"):
        out.append(("❌", "kimlik: çıktı adını veren zorunlu bir kimlik alanı olmalı (kişinin adı dosya adına girmez)"))
    for k, Y in (S.get("yazi") or {}).items():
        if k not in A:
            out.append(("❌", f"yazi.{k}: böyle bir alan yok"))
            continue
        if Y.get("aile", "Roboto Flex") != tablo()["aile"]:
            out.append(("❌", f"yazi.{k}: sığdırma için ölçü tablosu yalnız {tablo()['aile']} (public/fontlar/roboto-flex/olcu.json)"))
        if (Y.get("wdth") or [75])[0] < tablo()["wdth"][0] or (Y.get("wdth") or [75, 100])[-1] > tablo()["wdth"][-1]:
            out.append(("❌", f"yazi.{k}: genişlik ekseni ölçü tablosunun içinde olmalı ({tablo()['wdth'][0]}–{tablo()['wdth'][-1]}; dışında tahmin dar kalır, yazı taşar)"))
        if (Y.get("boyut") or [EN_KUCUK_PX])[0] < EN_KUCUK_PX:
            out.append(("❌", f"yazi.{k}: en küçük boyut ≥ {EN_KUCUK_PX} px"))
        if Y.get("renk") and Y.get("zemin") and O.kontrast(Y["renk"], Y["zemin"]) < KONTRAST:
            out.append(("❌", f"yazi.{k}: kontrast {O.kontrast(Y['renk'], Y['zemin']):.1f}:1 < {KONTRAST}:1"))
    for k, a in A.items():
        if a.get("ekranda") and a.get("tur") in ("ad", "metin") and k not in (S.get("yazi") or {}) and not a.get("en_uzun"):
            out.append(("⚠️", f"{k}: ekrandaki yazının sığdırması yok (yazi.{k}) ve en_uzun yok: uzun değer taşabilir"))
    if not S.get("kisi_isareti"):
        out.append(("❌", "kisi_isareti: ekrandaki bütün alanların tam göründüğü işaret yok (kanıt karesi)"))
    elif v is not None and v.cues and S["kisi_isareti"] not in v.cues:
        out.append(("❌", f"kisi_isareti: işaret yok ({S['kisi_isareti']}; cues.json)"))
    orn = S.get("ornek")
    if not orn:
        out.append(("❌", "ornek: şablonun TEST satırı yok (şablon filmin kareleri onunla çizilir)"))
    elif str(orn.get("test", "")).strip() != TEST:
        out.append(("❌", "ornek: TEST satırı olmalı (\"test\": \"TEST\"); şablona gerçek kişi girmez"))
    return out


def iskelet(v) -> dict:
    """./st toplu <id> kur: en küçük şablon (kimlik + ad, adın sığdırması güvenli alana göre, TEST örneği). Alanları film ekler."""
    return {"surum": SURUM, "kimlik": "kimlik",
            "alanlar": {"kimlik": {"ad": "Kimlik", "tur": "kimlik", "zorunlu": True, "esanlam": ["id", "no", "bağışçı no", "kod"]},
                        "ad": {"ad": "Ad soyad", "tur": "ad", "zorunlu": True, "ekranda": True, "bicim": "buyuk", "en_uzun": 48,
                               "esanlam": ["adı soyadı", "ad soyad", "isim", "bağışçı"]}},
            "yazi": {"ad": {"aile": "Roboto Flex", "wght": 800, "wdth": [70, 100], "boyut": [64, 120], "satir": 2, "satir_yuksekligi": 1.2,
                            "hiza": "sol", "pay": 72}},
            "kisi_isareti": "poster" if "poster" in v.cues else None,
            "ornek": {"kimlik": "TEST-000", "ad": "Örnek Kişi", "test": TEST},
            "kurum_verisi": {k: None for k in KARAR_ALANLARI}}


def ekrandaki_alanlar(S: dict) -> list[str]:
    return [k for k, a in S["alanlar"].items() if a.get("ekranda")]


def karar_eksikleri(S: dict) -> list[str]:
    """Kullanıcının kararları (veri_sablonu.json → kurum_verisi): gerçek veriyle toplu üretimden önce dolu olmalı. Claude yazmaz."""
    K = S.get("kurum_verisi") or {}
    return [ad for k, ad in KARAR_ALANLARI.items() if not K.get(k)]


# ---------------------------------------------------------------- ad sığdırma (yazı ölçü tablosu: iki motor aynı satırları çizer)
def kutu(Y: dict, fmt: str) -> float:
    """Yazının sığacağı genişlik (px): güvenli alan (hiza sol) ya da karenin eksenine simetrik güvenli alan (hiza orta), iki yandan pay."""
    F = O.FORMATLAR[fmt]
    w, u = F["w"], min(F["w"], F["h"]) / 1080
    sol, sag = F["guvenli"]["sol"] * w, w - F["guvenli"]["sag"] * w
    pay = float(Y.get("pay", 64)) * u
    if Y.get("genislik"):
        return float(Y["genislik"][fmt] if isinstance(Y["genislik"], dict) else Y["genislik"]) * u
    if Y.get("hiza", "sol") == "orta":
        return 2 * min(w / 2 - sol, sag - w / 2) - 2 * pay
    return (sag - sol) - 2 * pay


def _parcalar(metin: str) -> list[str]:
    """Satır kırma noktaları: boşluk (yutulur) ve kısa çizgiden sonra (çizgi satır sonunda kalır). Parça sonundaki boşluk ayırıcıdır."""
    out = []
    for kelime in metin.split(" "):
        p = re.split(r"(?<=-)", kelime)
        out += [x for x in p if x]
        out[-1] = out[-1] + " "
    out[-1] = out[-1].rstrip()
    return out


def _satirlar(P: list[str], n: int) -> list[list[str]]:
    """P parçasını n ardışık satıra bölmenin bütün yolları (n ≤ 3, parça sayısı küçük)."""
    if n == 1:
        return [["".join(P).rstrip()]]
    out = []
    for i in range(1, len(P)):
        for kalan in _satirlar(P[i:], n - 1):
            out.append(["".join(P[:i]).rstrip(), *kalan])
    return out


def ad_yerlesimi(metin: str, Y: dict, fmt: str) -> dict:
    """Adı (ya da uzun bir yazıyı) kutuya sığdırır: önce normal genişlikte en büyük boyut; tek satır yetmezse dengeli iki (en çok `satir`)
    satır; boyut en küçüğün altına inecekse yazı daralır (wdth); yine sığmazsa AlanHatasi. Satırları tarayıcı bölmez: sahne bu satırları çizer."""
    F = O.FORMATLAR[fmt]
    u = min(F["w"], F["h"]) / 1080
    W = kutu(Y, fmt)
    wght = float(Y.get("wght", 800))
    dar, normal = (Y.get("wdth") or [75, 100])
    lo, hi = [b * u for b in (Y.get("boyut") or [EN_KUCUK_PX, 160])]
    lo = max(lo, EN_KUCUK_PX * u)
    en_cok = int(Y.get("satir", 2))
    tek_esik = float(Y.get("tek_satir_en_az", 0.72)) * hi     # tek satır bu boyuttan küçük kalırsa iki satır denenir
    P = _parcalar(metin)

    def boyut(satirlar, wdth):
        em = max(kelime_genisligi(s, wght, wdth) for s in satirlar) * (1 + MARJ)
        return min(hi, W / em) if em > 0 else hi

    adaylar = []
    for n in range(1, min(en_cok, len(P)) + 1):
        # en büyük boyut; eşitse (ikisi de en büyükte) en dengeli satırlar
        en_iyi = max(_satirlar(P, n), key=lambda s: (boyut(s, normal), -max(kelime_genisligi(x, wght, normal) for x in s)))
        adaylar.append((n, en_iyi))
    secim = None
    for n, s in adaylar:             # en az satırla, büyüklüğü yeten ilk yerleşim; yoksa en büyük boyutlu
        b = boyut(s, normal)
        if b >= (max(lo, tek_esik) if n < len(adaylar) else lo):
            secim = (n, s, normal, b)
            break
    if secim is None:
        n, s = max(adaylar, key=lambda a: boyut(a[1], normal))
        secim = (n, s, normal, boyut(s, normal))
    n, s, wdth, b = secim
    while b < lo and wdth > dar:     # en küçüğün altında: daralt (5'er), boyutu koru
        wdth = max(dar, wdth - 5)
        b = boyut(s, wdth)
    if b < lo - 1e-6:
        en_uzun = max(len(x) for x in s)
        raise AlanHatasi(f"{round(lo / u)} px'te en çok {en_cok} satıra sığmıyor (en uzun satır {en_uzun} harf)")
    b = float(int(b))                # tam piksel: iki motor aynı
    lh = float(Y.get("satir_yuksekligi", 1.18))
    return {"satirlar": s, "boyut": b, "wght": wght, "wdth": float(wdth), "opsz": tablo()["opsz"], "satir_yuksekligi": lh,
            "genislik": round(W, 1), "yukseklik": round(b * lh * len(s), 1), "hiza": Y.get("hiza", "sol"),
            "tahmini_genislik": round(max(kelime_genisligi(x, wght, wdth) for x in s) * b, 1)}


# ---------------------------------------------------------------- veri dosyası
def _cozumle(b: bytes) -> tuple[str, str]:
    for kod in ("utf-8-sig", "cp1254"):
        try:
            return b.decode(kod), kod
        except UnicodeDecodeError:
            continue
    raise SystemExit("veri dosyası okunamadı: UTF-8 ya da Windows-1254 (Türkçe) olmalı")


def oku(yol: Path) -> tuple[list[str], list[dict]]:
    """CSV (virgül, noktalı virgül ya da sekme; UTF-8 ya da Windows-1254) ya da JSON (satır listesi ya da {"satirlar": [...]}) → (sütunlar, satırlar)."""
    yol = Path(yol)
    if not yol.exists():
        raise SystemExit(f"veri dosyası yok: {yol.name}")
    b = yol.read_bytes()
    if yol.suffix.lower() == ".json":
        try:
            j = json.loads(b.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise SystemExit(f"JSON okunamadı ({type(e).__name__}, satır {getattr(e, 'lineno', '?')})") from None
        S = j.get("satirlar") if isinstance(j, dict) else j
        if not isinstance(S, list) or not all(isinstance(x, dict) for x in S):
            raise SystemExit("JSON: satır listesi ya da {\"satirlar\": [...]} olmalı (her satır bir nesne)")
        sut = []
        for x in S:
            sut += [k for k in x if k not in sut]
        return sut, [{k: x.get(k) for k in sut} for x in S]
    if yol.suffix.lower() not in (".csv", ".tsv", ".txt"):
        raise SystemExit("veri dosyası .csv ya da .json olmalı")
    t, _ = _cozumle(b)
    ilk = t.splitlines()[0] if t.strip() else ""
    ayr = max([";", ",", "\t"], key=ilk.count)
    r = list(csv.reader(io.StringIO(t), delimiter=ayr))
    r = [x for x in r if any(c.strip() for c in x)]
    if not r:
        raise SystemExit("veri dosyası boş")
    sut = [c.strip() for c in r[0]]
    if len(set(sut)) != len(sut) or any(not c for c in sut):
        raise SystemExit("CSV: sütun adları boş ya da tekrar ediyor (ilk satır başlık olmalı)")
    return sut, [{c: (x[i] if i < len(x) else None) for i, c in enumerate(sut)} for x in r[1:]]


def otomatik_esleme(S: dict, sutunlar: list[str]) -> dict:
    """Şablon alanı → sütun: sütun adı alanın anahtarına, adına ya da eş anlamlılarına (esanlam) benziyorsa. Bulunamayan alan eşlenmez."""
    N = {_tr_norm(c): c for c in sutunlar}
    out = {}
    for k, a in S["alanlar"].items():
        for aday in [k, a.get("ad", ""), *(a.get("esanlam") or [])]:
            if _tr_norm(aday) in N:
                out[k] = N[_tr_norm(aday)]
                break
    return out


def test_sutunu(sutunlar: list[str]) -> str | None:
    return next((c for c in sutunlar if c.strip().lower() == "test"), None)


def satir_hazirla(S: dict, ham: dict, esleme: dict, formatlar: list[str], dil: str = "tr") -> tuple[dict | None, list[str], dict]:
    """Bir satır → (sahneye giden kişi verisi | None, nedenler [alan: neden], tam değerler). Nedenlerde değer yok."""
    nedenler, D = [], {}
    for k, A in S["alanlar"].items():
        sutun = esleme.get(k)
        hamv = ham.get(sutun) if sutun else None
        if hamv is None or (isinstance(hamv, str) and not hamv.strip()):
            if A.get("zorunlu"):
                nedenler.append(f"{A.get('ad', k)}: {'eşlenmedi' if not sutun else 'boş'}")
            continue
        try:
            D[k] = alan_degeri(A, hamv, dil)
        except AlanHatasi as e:
            nedenler.append(f"{A.get('ad', k)}: {e}")
    kim = S["kimlik"]
    if kim in D and "ad" in [a["tur"] for a in S["alanlar"].values()]:   # çıktı adına kişinin adı girmesin
        adlar = [D[k]["deger"] for k, a in S["alanlar"].items() if a["tur"] == "ad" and k in D]
        parca = {_tr_norm(p) for x in adlar for p in re.split(r"[\s\-'’.]+", x) if len(p) >= 3}
        if any(p and p.replace(" ", "") in _tr_norm(D[kim]["deger"]).replace(" ", "") for p in parca):
            nedenler.append(f"{S['alanlar'][kim].get('ad', kim)}: kişinin adını içeriyor (dosya adına ad girmez)")
    yerlesim = {}
    for k, Y in (S.get("yazi") or {}).items():
        if k not in D:
            continue
        try:
            yerlesim[k] = {f: ad_yerlesimi(D[k]["metin"], Y, f) for f in formatlar}
        except AlanHatasi as e:
            nedenler.append(f"{S['alanlar'][k].get('ad', k)}: {e}")
    test = str(ham.get(test_sutunu(list(ham)) or "", "") or "").strip() == TEST
    if nedenler:
        return None, nedenler, D
    giden = {k: {a: D[k][a] for a in ("deger", "metin", "sayi") if a in D[k]} | {"ad": S["alanlar"][k].get("ad", k), "tur": S["alanlar"][k]["tur"],
             **({"birim": S["alanlar"][k]["birim"]} if S["alanlar"][k].get("birim") else {})}
             for k in D if S["alanlar"][k].get("ekranda") or S["alanlar"][k].get("sahne")}
    kisi = {"surum": SURUM, "kimlik": D[kim]["deger"], "test": test, "dil": dil, "alanlar": giden, "yerlesim": yerlesim}
    return kisi, [], D


def hazirla(v, yol: Path, esleme: dict | None = None, satirlar: list[str] | None = None) -> dict:
    """Veri dosyasının bütün satırları: geçerli olanların kişi verisi, atlananların nedeni. Kimlik tekrarı: tekrar eden bütün satırlar atlanır."""
    S = sablon(v)
    sut, ham = oku(yol)
    E = {**otomatik_esleme(S, sut), **(esleme or {})}
    bilinmeyen = [k for k in (esleme or {}) if k not in S["alanlar"]]
    yok = [c for c in E.values() if c not in sut]
    if bilinmeyen or yok:
        raise SystemExit("eşleme: " + "; ".join([f"şablonda alan yok: {k}" for k in bilinmeyen] + [f"dosyada sütun yok: {c}" for c in yok]))
    dil = v.script.get("dil", "tr")
    out = []
    for i, h in enumerate(ham, 1):
        kisi, ned, D = satir_hazirla(S, h, E, v.formatlar, dil)
        kim = (D.get(S["kimlik"]) or {}).get("deger")
        out.append({"no": i, "kimlik": kim, "kisi": kisi, "nedenler": ned, "test": str(h.get(test_sutunu(sut) or "", "") or "").strip() == TEST})
    sayac = {}
    for x in out:
        if x["kimlik"]:
            sayac[x["kimlik"]] = sayac.get(x["kimlik"], 0) + 1
    for x in out:
        if x["kimlik"] and sayac[x["kimlik"]] > 1:
            x["nedenler"].append(f"kimlik {sayac[x['kimlik']]} satırda tekrar ediyor")
            x["kisi"] = None
    if satirlar:
        out = [x for x in out if x["kimlik"] in satirlar]
    return {"sutunlar": sut, "esleme": E, "eslenmeyen": [k for k, a in S["alanlar"].items() if k not in E],
            "kullanilmayan": [c for c in sut if c not in E.values() and c != test_sutunu(sut)],
            "test": bool(out) and all(x["test"] for x in out), "satirlar": out,
            "sha256": hashlib.sha256(Path(yol).read_bytes()).hexdigest(), "dosya": Path(yol).name}


def ornek_kisi(v) -> dict | None:
    """Şablonun TEST örneği (videos/<id>/veri_sablonu.json → ornek): şablon filmin kendi kareleri, Studio, inceleme bununla çizilir."""
    if not var_mi(v):
        return None
    S = sablon(v)
    if not S.get("ornek"):
        return None
    E = {k: k for k in S["alanlar"]}
    kisi, ned, _ = satir_hazirla(S, {**S["ornek"], "test": S["ornek"].get("test")}, E, v.formatlar, v.script.get("dil", "tr"))
    if ned:
        raise SystemExit(f"{v.id}: veri_sablonu.json → ornek geçersiz: " + "; ".join(ned))
    return {**kisi, "film": v.id}


def props(v) -> dict:
    """Remotion girdisi: {"kisi": şablonun TEST örneği} yalnız kişisel filmde; öteki filmlerin props'u değişmez."""
    k = ornek_kisi(v)
    return {"kisi": k} if k else {}


def esitle(v):
    """Studio için örnek kopyası (public/<id>/kisisel/ornek.json; TEST satırı, kişisel veri değil)."""
    k = ornek_kisi(v)
    p = ornek_kopyasi(v)
    if k:
        p.parent.mkdir(parents=True, exist_ok=True)
        t = json.dumps(k, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
        if not p.exists() or p.read_text() != t:
            p.write_text(t)
    elif p.exists():
        p.unlink()


# ---------------------------------------------------------------- ekranda ne yazıyor (yazı tanıma: 4d'nin aracı)
def _katla(s: str) -> str:
    """Harf işaretleri olmadan (yalnız ⚠️ için: yazı tanıma bazen büyük harfin noktasını, iki noktasını kaçırıyor; gerçek bir yanlışı da gizleyebilir)."""
    import veri
    return veri._norm(s).translate(str.maketrans("öüşçğıâîûê", "ouscgiaiue"))


def _parcalar_png(png: Path, hedef: Path) -> list[Path]:
    """Kareyi yarı yarıya bindirmeli yatay bantlara böler (yatay karede iki sütun × bant): yazı tanıma küçük alanda harf işaretlerini daha iyi
    okuyor, okuma kırpıma bağlı (tam karede "Örnekköy" → "Ornekköy", bir bantta doğru; 4c). Bant ≈ 320 px (1080 kısa kenarda): her satır en az
    bir bantta bütün kalır."""
    from PIL import Image
    im = Image.open(png)
    W, H = im.size
    xs = [(0.0, 0.6), (0.4, 1.0)] if W > H else [(0.0, 1.0)]
    hedef.mkdir(parents=True, exist_ok=True)
    out = []
    for s, (oran, kayma) in enumerate(((0.3, 0.0), (0.3, 0.25), (0.22, 0.0), (0.22, 0.25))):   # iki bant boyu × iki kayma: okuma kırpıma bağlı
        bh = max(1, round(min(W, H) * oran))
        for i, (x0, x1) in enumerate(xs):
            y, j = round(bh * kayma), 0
            while y < H - bh // 2:
                q = hedef / f"{png.stem}-s{s}p{i}{j:02d}.png"
                im.crop((round(x0 * W), y, round(x1 * W), min(H, y + bh))).save(q)
                out.append(q)
                y, j = y + bh // 2, j + 1
    return out


def ekran_denetimi(kisi: dict, png: Path, fmt: str) -> dict:
    """Kanıt karesinde: ekrandaki her alan (ad satır satır, sayı tek başına) okunuyor mu (TEST plakası aranmaz: 2026-10-27)? Önce tam kare, okunmayan
    alan varsa bindirmeli parçalar. Harf işaretleri dışında okunan alan ⚠️ (göz), hiç okunmayan ❌. Okunan yazı döndürülür, rapora yazılmaz (kişisel)."""
    import shutil

    import veri
    o = veri.ocr([png])
    if o is None:
        return {"ocr": False, "durum": "👁"}
    m = list(o.get(str(png), []))

    def denetle(m):
        s = {}
        for k, A in kisi["alanlar"].items():
            Y = (kisi.get("yerlesim") or {}).get(k, {}).get(fmt)
            if Y:
                s[k] = all(veri.ekranda_bul(m, x, False) for x in Y["satirlar"])
            elif A["tur"] in SAYI_TURLERI:
                s[k] = veri.ekranda_bul(m, A["sayi"], True)
            elif A["tur"] != "kimlik" and "metin" in A:
                s[k] = veri.ekranda_bul(m, A["metin"], False)
        return s
    sonuc = denetle(m)
    test_ok = True  # TEST plakası zorunlu değil (kullanıcı kararı, 2026-10-27)
    if not all(sonuc.values()):
        gecici = png.parent / f"_ocr-{png.stem}"
        try:
            P = _parcalar_png(png, gecici)
            op = veri.ocr(P) or {}
            m += [x for q in P for x in op.get(str(q), [])]
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
        sonuc = denetle(m)
    katli = _katla(" ".join(m))
    isaret = [k for k, ok in sonuc.items() if not ok and all(_katla(x) in katli for x in (
        (kisi.get("yerlesim") or {}).get(k, {}).get(fmt, {}).get("satirlar") or [kisi["alanlar"][k].get("sayi") or kisi["alanlar"][k]["metin"]]))]
    durum = "✅" if all(sonuc.values()) and test_ok else ("⚠️" if test_ok and set(k for k, ok in sonuc.items() if not ok) <= set(isaret) else "❌")
    return {"ocr": True, "alanlar": sonuc, "isaret": isaret, "test": test_ok, "durum": durum, "okunan": m}


def ekrandakiler(S: dict, kisi: dict) -> list[str]:
    """Denetlenen alanlar: şablonda ekranda olanlar (sahne alanları yazı değildir)."""
    return [k for k in ekrandaki_alanlar(S) if k in kisi["alanlar"]]


# ---------------------------------------------------------------- sahne kodu
def kod_denetimi(v) -> list[tuple[str, str]]:
    """Kod kişi verisini useKisi'den okuyor mu, şablonun örnek değeri elle yazılmış mı, çizimde ağ var mı. (TEST plakası zorunlu değil: 2026-10-27.)"""
    import veri
    D = veri.kod_dosyalari(v)
    if not D:
        return [("⚠️", "sahne kodu yok")]
    # HyperFrames: ./st'nin yazdığı veri bloğu (st-veri: ST.kisi = şablonun örneği) sahne kodu değildir
    T = {p: veri._yorumsuz(re.sub(r'<script id="st-veri">.*?</script>', "", p.read_text(), flags=re.S), p.suffix) for p in D}
    out = []
    okur = [p.name for p, t in T.items() if re.search(r"\buseKisi\s*\(|\bST\.kisi\b", t)]
    out.append(("✅", "kişi verisi useKisi() / ST.kisi'den: " + ", ".join(okur)) if okur else ("❌", "kod kişi verisini okumuyor: Remotion useKisi('<id>') (src/lib/kisisel)"))
    ag = [f"{p.name}: {m.group(0)}" for p, t in T.items() for m in [veri.AG.search(t)] if m]
    out.append(("❌", "çizimde ağ yok: " + "; ".join(ag)) if ag else ("✅", "sahne kodunda ağ çağrısı yok"))
    S = sablon(v)
    elle = []
    for k in ekrandaki_alanlar(S):
        val = (S.get("ornek") or {}).get(k)
        if isinstance(val, str) and len(val) >= 4:
            for cand in {val, buyuk(val)}:
                elle += [f"{p.name}: {k}" for p, t in T.items() if cand in t]
    if elle:
        out.append(("⚠️", "şablonun örnek değeri kodda elle yazılmış olabilir (her kişide aynı kalır): " + "; ".join(sorted(set(elle)))))
    return out


# ---------------------------------------------------------------- çalışmalar (videos/<id>/toplu/<çalışma>/)
def calismalar(v) -> list[Path]:
    d = dizin(v)
    return sorted([p for p in d.iterdir() if p.is_dir() and (p / "rapor.json").exists()], key=lambda p: p.name) if d.exists() else []


def veri_dosyalari(v) -> list[Path]:
    d = dizin(v) / "veri"
    return sorted([p for p in d.iterdir() if p.suffix.lower() in (".csv", ".json", ".tsv", ".txt")], key=lambda p: p.name) if d.exists() else []


def ocr_metni(E: dict) -> str:
    """Yazı tanıma sonucu tek satır (alan adlarıyla; değer yok)."""
    if not E.get("ocr"):
        return "👁 yazı tanıma yok (göz)"
    if E["durum"] == "✅":
        return "✅ yazılar ekranda: " + ", ".join(E["alanlar"])
    eksik = [k for k, ok in E["alanlar"].items() if not ok and k not in E.get("isaret", [])] + ([] if E["test"] else ["TEST plakası"])
    return ("❌ okunmadı: " + ", ".join(eksik) if eksik else "") + (" · " if eksik and E.get("isaret") else "") + \
        ("⚠️ harf işaretleri okunmadı (göz): " + ", ".join(E["isaret"]) if E.get("isaret") else "")


def rapor_md(R: dict) -> str:
    """İnsan okur: kimlik ve satır numarası, ad ve değer yok."""
    L = [f"# Toplu üretim · {R['film']} · {R['calisma']}", "",
         f"- Veri: `{R['dosya']}` · sha256 {R['sha256'][:12]} · {R['satir_sayisi']} satır · {'TEST verisi' if R['test'] else 'kurum verisi'}",
         f"- Şablon: veri_sablonu.json · ekranda: {', '.join(R['ekranda'])} · formatlar: {', '.join(R['formatlar'])}",
         f"- Sonuç: {R['uretilen']} film üretildi · {len(R['atlanan'])} satır atlandı · {R.get('hatali', 0)} çizim hatası",
         f"- Süre: " + (f"paket {R.get('paket_sn', 0):.1f} sn · " if R.get("motor") != "hyperframes" else "")
         + f"toplam {R.get('toplam_sn', 0):.1f} sn · film başına ortalama {R.get('film_basina_sn') or 0:.1f} sn · etkin (toplam ÷ film) {R.get('etkin_sn') or 0:.1f} sn · "
         + ("HyperFrames, SwiftShader, filmler sırayla" if R.get("motor") == "hyperframes" else
            f"Remotion, eşzamanlı çizim {R.get('esanli', '?')} sekme × {R.get('paralel', 1)} film"), ""]
    if R["cikti"]:
        L += ["| Kimlik | Format | Süre (sn) | Kare | sn/kare | Yazılar ekranda | Dosya |", "|---|---|---|---|---|---|---|"]
        for c in R["cikti"]:
            durum = ocr_metni(c.get("ocr") or {})
            L.append(f"| {c['kimlik']} | {c['format']} | {c.get('sn', 0):.1f} | {c.get('kare', '')} | {c.get('sn_kare', 0):.3f} | {durum if c['durum'] != 'hata' else '❌ çizilemedi'} | "
                     f"{c.get('dosya', '—')} |")
        L.append("")
    if R["atlanan"]:
        L += ["## Atlanan satırlar (uydurma yok: varsayılan değerle doldurulmadı)", ""]
        L += [f"- satır {x['no']}{' · ' + x['kimlik'] if x.get('kimlik') else ''}: " + "; ".join(x["nedenler"]) for x in R["atlanan"]]
        L.append("")
    if R.get("eslenmeyen"):
        L.append(f"- Eşlenmeyen şablon alanları: {', '.join(R['eslenmeyen'])}")
    if R.get("kullanilmayan"):
        L.append(f"- Dosyada olup kullanılmayan sütunlar (sahneye gitmedi): {', '.join(R['kullanilmayan'])}")
    return "\n".join(L) + "\n"


def ozet(v) -> dict | None:
    """Panel: şablon, kullanıcının kararları, yüklenen veri dosyaları, önizleme ve çalışmalar (ad ve değer yok; dosyalar yalnız yol)."""
    if not var_mi(v):
        return None
    S = sablon(v)
    rel = lambda p: str(Path(p).relative_to(O.KANAL))  # noqa: E731
    onz = dizin(v) / "onizleme"
    oj = O.jload(onz / "onizleme.json") if (onz / "onizleme.json").exists() else None
    cal = []
    for c in reversed(calismalar(v)):
        R = O.jload(c / "rapor.json")
        cal.append({"ad": c.name, "dosya": R["dosya"], "test": R["test"], "uretilen": R["uretilen"], "atlanan": R["atlanan"], "hatali": R.get("hatali", 0),
                    "film_basina_sn": R.get("film_basina_sn"), "toplam_sn": R.get("toplam_sn"), "bitti": R.get("bitti", False),
                    "cikti": [{**{k: x.get(k) for k in ("kimlik", "format", "sn", "durum")}, "ocr": (x.get("ocr") or {}).get("tamam"),
                               "video": rel(c / x["dosya"]) if x.get("dosya") else None, "kanit": rel(c / x["kanit"]) if x.get("kanit") else None}
                              for x in R["cikti"]]})
    return {"alanlar": [{"anahtar": k, "ad": a.get("ad", k), "tur": a["tur"], "zorunlu": bool(a.get("zorunlu")), "ekranda": bool(a.get("ekranda")),
                         "sahne": bool(a.get("sahne")), "secenekler": list((a.get("secenekler") or {}).values()) or None}
                        for k, a in S["alanlar"].items()],
            "kimlik": S["kimlik"], "sorunlar": [{"durum": d, "mesaj": m} for d, m in sablon_sorunlari(S, v)],
            "kararlar": S.get("kurum_verisi") or {}, "karar_alanlari": KARAR_ALANLARI, "karar_eksik": karar_eksikleri(S),
            "onay6": bool((O.jload(v.dir / "kapilar.json") if (v.dir / "kapilar.json").exists() else {}).get("6")),
            "dosyalar": [{"ad": p.name, "boyut": p.stat().st_size} for p in veri_dosyalari(v)],
            "esleme": O.jload(dizin(v) / "esleme.json") if (dizin(v) / "esleme.json").exists() else {},
            "onizleme": {**oj, "kareler": {f: rel(onz / p) for f, p in oj.get("kareler", {}).items()}} if oj else None,
            "calismalar": cal}


class gecici_dosya:
    """Kişi verisi taşıyan iş tanımı için geçici dosya (videos/<id>/toplu/_gecici/; iş bitince silinir): komut satırına ve günlüğe ad girmez."""

    def __init__(self, v, icerik):
        self.yol = dizin(v) / "_gecici" / f"is-{os.getpid()}-{id(icerik):x}.json"
        self.icerik = icerik

    def __enter__(self) -> Path:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        self.yol.write_text(json.dumps(self.icerik, ensure_ascii=False))
        return self.yol

    def __exit__(self, *a):
        self.yol.unlink(missing_ok=True)
        try:
            self.yol.parent.rmdir()
        except OSError:
            pass


# ---------------------------------------------------------------- toplu üretim (./st toplu <id> --veri <dosya>)
def kanit_karesi(v) -> int:
    S = sablon(v)
    return min(max(0, v.nframes - 1), round(v.cues[S["kisi_isareti"]] * v.fps))


def onay_engeli(v, H: dict) -> str | None:
    """Gerçek listeye ek kapı yok (kullanıcı kararı, 2026-10-27): listeyi kullanıcı panelden yükleyip başlatır; Kapı 6 onayı ve kurum verisi
    notları isteğe bağlıdır. Panelin Claude'u listeyi zaten göremez ve çizemez (kanca). Çağıranlar için duruyor: her zaman None."""
    return None


def calisma_adi() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def _yaz_rapor(d: Path, R: dict):
    (d / "rapor.json").write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n")
    (d / "rapor.md").write_text(rapor_md(R))


def toplu(v, yol: Path, taban: dict, esleme: dict | None = None, formatlar: list[str] | None = None, satirlar: list[str] | None = None,
          paralel: int = 1, esanli: int | None = None, crf: int = 18) -> dict:
    """Her geçerli satır × format için film; kanıt karesi filmin dosyasından çıkarılır ve yazı tanımayla okunur. Rapor ve çıktılar
    videos/<id>/toplu/<çalışma>/ altında (adlar kimlikle). Günlüğe yalnız kimlik ve satır numarası yazılır."""
    import subprocess
    import time

    import veri
    S = sablon(v)
    kotu = [m for d, m in sablon_sorunlari(S, v) if d == "❌"]
    if kotu:
        raise SystemExit("şablon (veri_sablonu.json): " + "; ".join(kotu))
    if not (v.pub / "timeline.json").exists():
        raise SystemExit(f"şablon filmin zaman çizelgesi yok: önce ./st ses {v.id}")
    H = hazirla(v, yol, esleme, satirlar)
    engel = onay_engeli(v, H)
    if engel:
        raise SystemExit(engel)
    formatlar = formatlar or v.formatlar
    ad = calisma_adi()
    d = dizin(v) / ad
    d.mkdir(parents=True, exist_ok=False)
    gecerli = [x for x in H["satirlar"] if x["kisi"]]
    atlanan = [{"no": x["no"], "kimlik": x["kimlik"], "nedenler": x["nedenler"]} for x in H["satirlar"] if not x["kisi"]]
    R = {"surum": SURUM, "film": v.id, "calisma": ad, "dosya": H["dosya"], "sha256": H["sha256"], "test": H["test"], "satir_sayisi": len(H["satirlar"]),
         "formatlar": formatlar, "ekranda": ekrandaki_alanlar(S), "esleme": H["esleme"], "eslenmeyen": H["eslenmeyen"], "kullanilmayan": H["kullanilmayan"],
         "atlanan": atlanan, "cikti": [], "uretilen": 0, "hatali": 0, "paralel": paralel, "esanli": esanli or "Remotion varsayılanı (çekirdeklerin yarısı)",
         "bitti": False, "toplam_is": len(gecerli) * len(formatlar), "baslangic": dt.datetime.now().isoformat(timespec="seconds")}
    _yaz_rapor(d, R)
    print(f"toplu üretim {v.id} · çalışma {ad} · {H['dosya']} · {len(H['satirlar'])} satır: {len(gecerli)} geçerli, {len(atlanan)} atlandı"
          f" · {'TEST verisi' if H['test'] else 'kurum verisi'} · formatlar {', '.join(formatlar)}")
    for x in atlanan:
        print(f"  atlandı: satır {x['no']}{' · ' + x['kimlik'] if x['kimlik'] else ''}: " + "; ".join(x["nedenler"]))
    if not gecerli:
        R.update(bitti=True, toplam_sn=0.0)
        _yaz_rapor(d, R)
        return R
    tek = len(v.formatlar) == 1
    isler = []
    for x in gecerli:
        kisi = {**x["kisi"], "film": v.id}
        gizli = sorted({str(a.get(k)) for a in x["kisi"]["alanlar"].values() for k in ("deger", "metin") if a.get(k) is not None}
                       | {s for Y in x["kisi"]["yerlesim"].values() for y in Y.values() for s in y["satirlar"]}, key=len, reverse=True)
        for f in formatlar:
            ad_ = f"{x['kimlik']}{'' if tek else '_' + f}.mp4"
            isler.append({"kimlik": x["kimlik"], "format": f, "comp": v.comp_for(f), "props": {**taban, "kisi": kisi}, "cikti": str(d / ad_), "gizli": gizli})
    kisiler = {x["kimlik"]: x["kisi"] for x in gecerli}
    kare = kanit_karesi(v)
    (d / "kanit").mkdir(exist_ok=True)
    R["motor"] = v.motor

    def sonuc(kimlik, f, sn, kare_sayisi=None, hata=None):
        """Bir filmin sonucu: kanıt karesi filmin dosyasından, yazı tanıma; rapora yalnız kimlik, alan adı ve evet/hayır."""
        ad_ = Path(next(i["cikti"] for i in isler if i["kimlik"] == kimlik and i["format"] == f)).name
        c = {"kimlik": kimlik, "format": f, "sn": round(sn, 2), "durum": "hata" if hata is not None else "tamam"}
        if hata is None:
            c.update(dosya=ad_, kare=kare_sayisi, sn_kare=round(sn / max(1, kare_sayisi), 4), mb=round((d / ad_).stat().st_size / 1e6, 2))
            png = veri.mp4_karesi(d / ad_, kare, d / "kanit" / f"{Path(ad_).stem}.png")
            E = ekran_denetimi(kisiler[kimlik], png, f) if png else {"ocr": False, "durum": "👁"}
            E.pop("okunan", None)   # okunan yazı kişiseldir: rapora girmez
            E["tamam"] = E.get("durum") == "✅"
            c.update(kanit=str(png.relative_to(d)) if png else None, ocr=E)
            R["uretilen"] += 1
            print(f"  ✓ {kimlik} [{f}] {sn:.1f} sn ({c['sn_kare']:.3f} sn/kare) · {ocr_metni(E)}")
        else:
            c["hata"] = hata
            R["hatali"] += 1
            print(f"  ✗ {kimlik} [{f}] çizilemedi: {hata[:200]}")
        R["cikti"].append(c)
        _yaz_rapor(d, R)

    def maskele(s: str) -> str:
        for i in isler:   # hata iletisinde kişinin değerleri görünmesin
            for g in i["gizli"]:
                s = s.replace(g, "‹…›") if len(g) >= 2 else s
        return s

    t0 = time.time()
    if v.motor == "hyperframes":   # HyperFrames: satır başına varyant (ST.kisi), SwiftShader ile teslim kalitesi; sırayla (HyperFrames kendi içinde paralel)
        import hf
        hf.esitle(v)
        for i in isler:
            print(f"  çiziliyor: {i['kimlik']} [{i['format']}]")
            t1 = time.time()
            try:
                with gecici_dizin(v) as g:
                    kok = hf.kisi_varyanti(v, i["format"], i["props"]["kisi"], g / i["format"])
                    hf.video(v, i["format"], Path(i["cikti"]), final=True, kok=kok)
                sonuc(i["kimlik"], i["format"], time.time() - t1, v.nframes)
            except (subprocess.CalledProcessError, SystemExit, OSError) as e:
                sonuc(i["kimlik"], i["format"], time.time() - t1, hata=maskele(str(e))[-400:])
        R["paket_sn"] = 0.0
    else:   # Remotion: paket ve tarayıcı bir kez (pipeline/toplu.mjs), her film renderMedia
        is_dosyasi = d / "_is.json"
        is_dosyasi.write_text(json.dumps({"isler": isler, "esanli": esanli, "paralel": paralel, "crf": crf, "gl": v.gl}, ensure_ascii=False))
        try:
            p = subprocess.Popen(["node", "pipeline/toplu.mjs", f"@{is_dosyasi}"], cwd=O.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for ln in p.stdout:
                try:
                    e = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                o = e.get("olay")
                if o == "paket":
                    R["paket_sn"] = round(e["sn"], 1)
                    print(f"  paket hazır: {e['sn']:.1f} sn")
                elif o == "ilerleme" and e["oran"] == 0.5:
                    print(f"  {e['kimlik']} [{e['format']}] %50")
                elif o == "basla":
                    print(f"  çiziliyor: {e['kimlik']} [{e['format']}]")
                elif o == "bitti":
                    sonuc(e["kimlik"], e["format"], e["sn"], e["kare"])
                elif o == "hata":
                    sonuc(e["kimlik"], e["format"], e["sn"], hata=e.get("mesaj", ""))
            p.wait()
            if p.returncode != 0:
                print(f"  toplu çizim durdu (çıkış {p.returncode}): {maskele(p.stderr.read()).strip()[-600:]}")
                R["hatali"] += len(isler) - len(R["cikti"])
        finally:
            is_dosyasi.unlink(missing_ok=True)
    R["toplam_sn"] = round(time.time() - t0, 1)
    tamam = [c for c in R["cikti"] if c["durum"] == "tamam"]
    R["film_basina_sn"] = round(sum(c["sn"] for c in tamam) / len(tamam), 2) if tamam else None   # bir filmin çizim + kodlama süresi
    R["etkin_sn"] = round(R["toplam_sn"] / len(tamam), 2) if tamam else None                        # paket dahil toplam ÷ film (paralelde kısalır)
    R["bitti"] = True
    R["bitis"] = dt.datetime.now().isoformat(timespec="seconds")
    _yaz_rapor(d, R)
    return R


# ---------------------------------------------------------------- ölçüm satırları (yalnız veri_sablonu.json'u olan şablon filmde)
def olcum_satirlari(v, renders: dict | None = None, teslim: bool = False, cikti: Path | None = None) -> list[dict]:
    """Şablon filmin kendi ölçümü (TEST örneğiyle): sözleşme, sahne kodu, kullanıcının kararları ve her format için örnek satırın yazıları
    filmin dosyasında (kanıt karesi, yazı tanıma). Toplu üretimin her filmi ayrıca kendi raporunda denetlenir (toplu/<çalışma>/rapor.md)."""
    import veri
    row = lambda ad, deger, cita, durum, kanit="": {"ad": ad, "deger": deger, "cita": cita, "durum": durum, "kanit": kanit}  # noqa: E731
    if not var_mi(v):
        return []
    S = sablon(v)
    rows = []
    sor = sablon_sorunlari(S, v)
    rows.append(row("Kişisel film: şablon (veri_sablonu.json)", f"{len(S['alanlar'])} alan · ekranda: {', '.join(ekrandaki_alanlar(S))}",
                    "alan türleri, kimlik, sığdırma (≥ 64 px, ölçü tablosunun içinde), kontrast ≥ 4,5:1, kanıt işareti, TEST örneği",
                    "❌" if any(d == "❌" for d, _ in sor) else ("⚠️" if sor else "✅"), "; ".join(m for _, m in sor)))
    kod = kod_denetimi(v)
    rows.append(row("Kişisel film: sahne kodu", "; ".join(m for d, m in kod if d != "✅") or "kişi verisi useKisi / ST.kisi'den, çizimde ağ yok",
                    "yazı kişi verisinden (elle değil), çizimde ağ yok",
                    "❌" if any(d == "❌" for d, _ in kod) else ("⚠️" if any(d == "⚠️" for d, _ in kod) else "✅")))
    eksik = karar_eksikleri(S)
    rows.append(row("Kişisel film: kurum verisi notları", "yazılı" if not eksik else f"yazılmamış: {', '.join(eksik)}",
                    "isteğe bağlı (kaynak, izin, ekranda alanlar, gönderim, saklama); yazılırsa yayın paketine girer", "—"))
    yp = v.dir / "yayin.md"
    yd = (KVKK_BAS in yp.read_text() and KVKK_SON in yp.read_text()) if yp.exists() else None
    rows.append(row("Kişisel film: KVKK notu yayın paketinde (yayin.md)", {True: "var", False: "yok", None: "yayin.md yok"}[yd],
                    "bilgi: ./st yayin kurum verisi notlarından yazar", "—", "" if yd else f"./st yayin {v.id}"))
    kisi = ornek_kisi(v)
    kare = kanit_karesi(v) if S.get("kisi_isareti") in v.cues else None
    for fmt, mp4 in (renders or {}).items():
        mp4 = Path(mp4)
        ad = f"[{fmt}] Kişisel film: örnek satırın yazıları ekranda"
        if not mp4.exists() or kare is None or not kisi:
            continue
        png = veri.mp4_karesi(mp4, kare, (cikti or O.ROOT / "out" / "_kisisel" / v.id) / f"kisi-{fmt}-f{kare:05d}.png")
        E = ekran_denetimi(kisi, png, fmt) if png else {"ocr": False, "durum": "👁"}
        E.pop("okunan", None)
        rows.append(row(ad, f"f{kare} ({O.tc(kare / v.fps)}) · {kisi['kimlik']} · {ocr_metni(E)}",
                        "ekrandaki her alanın metni (ad satır satır) filmin dosyasında okunuyor (yazı tanıma)",
                        E["durum"], str(png.relative_to(O.ROOT)) if png and png.is_relative_to(O.ROOT) else ""))
    return rows


# ---------------------------------------------------------------- yayın paketi (yayin.md → "Kişisel veri" bloğu; ./st yayin yazar)
KVKK_BAS = "<!-- st:kisisel (./st yayin yazar; kararlar veri_sablonu.json → kurum_verisi, kullanıcının) -->"
KVKK_SON = "<!-- /st:kisisel -->"


def yayin_md(v) -> str:
    S = sablon(v)
    K = S.get("kurum_verisi") or {}
    bos = "belirtilmedi"  # köşeli parantezli yer tutucu değil: Kapı 6'yı bekletmesin (notlar isteğe bağlı, 2026-10-27)
    ekranda = ", ".join(S["alanlar"][k].get("ad", k) for k in ekrandaki_alanlar(S))
    L = [KVKK_BAS, "## Kişisel veri ve rıza (kişisel etki filmi; KVKK)",
         "- **Bu film kişiye özeldir.** Her kişinin filmi yalnız kendisine gönderilir; herkese açık yayınlanmaz, başka kişinin verisiyle paylaşılmaz.",
         f"- **Verinin kaynağı:** {K.get('kaynak') or bos}",
         f"- **İzin (açık rıza ya da aydınlatma metni, hukuki dayanak):** {K.get('izin') or bos}",
         f"- **Ekranda görünen alanlar:** {K.get('ekranda') or bos} (şablonda ekranda: {ekranda}; öteki alanlar filme hiç gitmez)",
         f"- **Gönderim:** {K.get('gonderim') or bos}",
         f"- **Saklama ve silme:** {K.get('saklama') or bos} (`./st toplu {v.id} sil <çalışma>` · `sil veri:<dosya>`)",
         "- **İşleme:** veri yalnız bu bilgisayarda işlendi (`./st toplu`); yapay zekâ servisine (Claude, Magnific) ya da başka bir sunucuya gönderilmedi. "
         "Dosya adları kimlikle; raporlarda ve günlüklerde ad ve değer yok.",
         "- Bu blok hukuki görüş değildir: aydınlatma metni, açık rıza ve saklama süresi kurumun hukuk birimiyle netleşir.",
         KVKK_SON]
    return "\n".join(L)


def yayin_yaz(v) -> Path | None:
    """yayin.md'deki kişisel veri bloğunu yeniler (dosya varsa); yoksa Beyanlar'dan (yoksa Dosyalar'dan) önce ekler."""
    p = v.dir / "yayin.md"
    if not p.exists() or not var_mi(v):
        return None
    t = p.read_text()
    blok = yayin_md(v)
    if KVKK_BAS in t and KVKK_SON in t:
        t2 = t[:t.index(KVKK_BAS)] + blok + t[t.index(KVKK_SON) + len(KVKK_SON):]
    else:
        for baslik in ("\n## Beyanlar", "\n## Dosyalar"):
            if baslik in t:
                t2 = t.replace(baslik, "\n" + blok + "\n" + baslik, 1)
                break
        else:
            t2 = t.rstrip() + "\n\n" + blok + "\n"
    if t2 != t:
        p.write_text(t2)
    return p


class gecici_dizin:
    """Kişi verisi taşıyan geçici klasör (videos/<id>/toplu/_gecici/<pid>/; HyperFrames'in satır varyantı): iş bitince silinir."""

    def __init__(self, v):
        self.yol = dizin(v) / "_gecici" / f"d-{os.getpid()}-{id(self):x}"

    def __enter__(self) -> Path:
        self.yol.mkdir(parents=True, exist_ok=True)
        return self.yol

    def __exit__(self, *a):
        import shutil
        shutil.rmtree(self.yol, ignore_errors=True)
        try:
            self.yol.parent.rmdir()
        except OSError:
            pass
