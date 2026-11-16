"""Canlı veri (./st veri): gerçek ve güncel bir kaynaktan anlık görüntü. Görüntü bir kez çekilir ve dondurulur; film o görüntüyle çizilir.

Sözleşme videos/<id>/veri.json (kaynağı tarif eder; konum kullanıcının kararı):
  kaynak {saglayici, ad, kurum, url, parametreler, sayfa, kosullar} · konum {ad, enlem, boylam, duzey, saat_dilimi}
  alanlar {<ad>: {ad, birim, ondalik, aralik, ekranda, yol | seri + deger + zaman + islem (+ pencere)}}
  atif, atif_kisa, atif_anahtar (ekranda aranacak kurum adı), lisans, lisans_url, ticari (lisans ticari/kurum kullanımına izin veriyor mu),
  kullanim (kurum | ticari_olmayan; kullanıcının beyanı, varsayılan kurum), ekranda (atıf ekranda da olsun mu: yalnız kullanıcı isterse, varsayılan hayır;
  atıf her durumda kaynaklar.md ve yayın paketinde), tur (tahmin | olcum | istatistik),
  tazelik_saat (yalnız bilgi: görüntünün yaşı ölçümde ve panelde yazar, eski görüntü kullanılabilir; kullanıcı kararı, 2026-10-27), dil

./st veri <id> kur|cek|sec|liste|kare|denetle (komut satırı: pipeline/st.py → cmd_veri)
  cek   kaynağa tek istek: ham yanıt bayt bayt videos/<id>/veri/<kimlik>/ham.json, kayıt kayit.json (zaman damgası, tam URL, HTTP başlıkları,
        sha256, hesaplanan değerler, atıf, lisans). Ağ hatasında ya da beklenmeyen veride DURUR: yeni görüntü yazılmaz, önceki görüntüye
        sessizce düşülmez; hangi görüntünün kullanılmaya devam ettiği söylenir. Kaynağın önbellek kuralına uyar (Expires dolmadan yeniden
        istenmez; If-Modified-Since: değişmediyse yeni görüntü yok). Yeni görüntü seçili olur.
  sec   çizilecek görüntüyü seçer (son ya da kimlik): eski bir görüntüyle yeniden çizim, deterministiklik.
Çizim sırasında ağ yok: motorlar yalnız seçili görüntünün çizim verisini okur (cizim()): Remotion'a girdi (props.veri; Studio'da
public/<id>/veri/anlik.json), HyperFrames'e window.ST.veri, Blender'a ST.veri. Görüntü değişince yalnız o filmin kareleri değişir.
Atıf kaynaklar.md'nin iddia tablosuna (V satırları, ✅) ve Kaynakça'ya, yayın paketine (yayin.md → "Veri kaynağı" bloğu) kendiliğinden yazılır.
"""
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import ortak as O

SURUM = 1
UA = "studyo-veri/1.0 (kod ile render edilen video studyosu)"
ZAMAN_ASIMI = 20               # saniye
EN_BUYUK = 8 * 1024 * 1024     # bir yanıt en çok 8 MB (anlık görüntü küçük bir JSON'dur)
TAZELIK_SAAT = 12
EN_AZ_ARALIK = 10 * 60         # aynı adrese stüdyo genelinde en az 10 dk aralık: kaynak bazen süresi geçmiş Expires veriyor (MET Norway, önbelleğinden)
OCR_KAYNAK = Path(__file__).resolve().parent / "ocr.swift"
OCR_BIN = O.ROOT / "out" / "_araclar" / "ocr"
AYLAR = {"tr": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
         "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
TURLER = {"tahmin": {"tr": "tahmin", "en": "forecast"}, "olcum": {"tr": "ölçüm", "en": "observation"},
          "istatistik": {"tr": "istatistik", "en": "statistics"}}
KULLANIMLAR = ("kurum", "ticari_olmayan")
ISLEMLER = ("en_dusuk", "en_yuksek", "ortalama", "toplam", "ilk", "son", "en_yakin")
ISLEM_AD = {"en_dusuk": "en düşük", "en_yuksek": "en yüksek", "ortalama": "ortalama", "toplam": "toplam", "ilk": "ilk", "son": "son",
            "en_yakin": "görüntü anına en yakın saat"}
# Kodda ağ: çizim sırasında ağ yok (kural 8). Scene kodunda bunlar ❌ (kitin kendi dosyaları taranmaz).
AG = re.compile(r"\bfetch\s*\(|XMLHttpRequest|new\s+WebSocket|EventSource|\baxios\b|\burllib\b|\brequests\.(get|post)|http\.client|\bsocket\.")


class VeriHatasi(Exception):
    """Beklenmeyen veri ya da ağ hatası: yeni görüntü yazılmaz (./st veri çıkış kodu 2)."""
    kod = 2


class VeriBekle(VeriHatasi):
    """Kaynağın önbellek kuralı (Expires dolmadı): istek gönderilmedi (çıkış kodu 4)."""
    kod = 4


# ---------------------------------------------------------------- sağlayıcılar (./st veri kur hazır tarifleri)
# Lisans araştırması (2026-10-26; yol-haritasi/4-sansasyon-araclari.md → 4d): kurum kampanyası tanıtım sayılır.
SAGLAYICILAR = {
    "met-norway": {
        "ad": "MET Norway Locationforecast 2.0 (compact)",
        "kurum": "Norveç Meteoroloji Enstitüsü (MET Norway)",
        "url": "https://api.met.no/weatherapi/locationforecast/2.0/compact",
        "parametreler": lambda K: {"lat": K["enlem"], "lon": K["boylam"]},
        "sayfa": "https://api.met.no/weatherapi/locationforecast/2.0/documentation",
        "kosullar": "https://api.met.no/doc/TermsOfService",
        "lisans": "CC BY 4.0 (ayrıca NLOD 2.0)",
        "lisans_url": "https://creativecommons.org/licenses/by/4.0/deed.tr",
        "ticari": True,
        "ekranda": False,  # ekranda atıf yalnız kullanıcı isterse (2026-10-27); atıf yayın paketinde ve kaynaklar.md'de
        "atif_anahtar": "MET Norway",
        "atif": {"tr": "MET Norway (Norveç Meteoroloji Enstitüsü) verisine dayanır; değerler bu veriden hesaplanmıştır. Lisans: CC BY 4.0",
                 "en": "Based on data from MET Norway (The Norwegian Meteorological Institute); values calculated from this data. Licence: CC BY 4.0"},
        "atif_kisa": {"tr": "Veri: MET Norway · CC BY 4.0", "en": "Data: MET Norway · CC BY 4.0"},
        "tur": "tahmin",
        "kimlik": True,   # kurallar: tanımlayıcı User-Agent (kurum adı + iletişim), Expires dolmadan yeniden istenmez, koordinat ≤ 4 ondalık
        "alanlar": {
            # seri bir model çalışmasının ilk saatinden başlar (görüntüden bir saat önce olabilir): "şu an" görüntü anına en yakın saattir
            "simdi": {"ad": "Şu an", "seri": "properties.timeseries", "deger": "data.instant.details.air_temperature", "zaman": "time",
                      "islem": "en_yakin", "birim": "°C", "ondalik": 0, "aralik": [-70, 60]},
            "gece_en_dusuk": {"ad": "Bu gece en düşük", "seri": "properties.timeseries", "deger": "data.instant.details.air_temperature",
                              "zaman": "time", "islem": "en_dusuk", "pencere": {"tur": "gece", "bas": 21, "son": 6},
                              "birim": "°C", "ondalik": 0, "aralik": [-70, 60]},
        },
        "guncelleme_yolu": "properties.meta.updated_at",
        "not": "Ücretsiz, anahtarsız; CC BY 4.0 ticari kullanıma izin verir (atıf şart). Kurallar: tanımlayıcı User-Agent, Expires dolmadan "
               "yeniden istek yok, koordinat ≤ 4 ondalık, ≤ 20 istek/sn.",
    },
    "open-meteo": {
        "ad": "Open-Meteo Forecast API (ücretsiz katman)",
        "kurum": "Open-Meteo",
        "url": "https://api.open-meteo.com/v1/forecast",
        "parametreler": lambda K: {"latitude": K["enlem"], "longitude": K["boylam"], "current": "temperature_2m",
                                   "hourly": "temperature_2m", "forecast_days": 2, "timezone": "GMT", "timeformat": "unixtime"},
        "sayfa": "https://open-meteo.com/en/docs",
        "kosullar": "https://open-meteo.com/en/terms",
        "lisans": "CC BY 4.0 (veri) · ücretsiz API yalnız ticari olmayan kullanım",
        "lisans_url": "https://open-meteo.com/en/licence",
        "ticari": False,
        "ekranda": False,  # ekranda atıf yalnız kullanıcı isterse (2026-10-27); atıf yayın paketinde ve kaynaklar.md'de
        "atif_anahtar": "Open-Meteo",
        "atif": {"tr": "Hava verisi: Open-Meteo.com (https://open-meteo.com/), CC BY 4.0; değerler bu veriden hesaplanmıştır",
                 "en": "Weather data by Open-Meteo.com (https://open-meteo.com/), CC BY 4.0; values calculated from this data"},
        "atif_kisa": {"tr": "Hava verisi: Open-Meteo.com · CC BY 4.0", "en": "Weather data by Open-Meteo.com · CC BY 4.0"},
        "tur": "tahmin",
        "kimlik": False,
        "alanlar": {
            "simdi": {"ad": "Şu an", "yol": "current.temperature_2m", "zaman_yolu": "current.time", "birim": "°C", "ondalik": 0, "aralik": [-70, 60]},
            "gece_en_dusuk": {"ad": "Bu gece en düşük", "seri": "hourly", "deger": "temperature_2m", "zaman": "time", "islem": "en_dusuk",
                              "sutunlu": True, "pencere": {"tur": "gece", "bas": 21, "son": 6}, "birim": "°C", "ondalik": 0, "aralik": [-70, 60]},
        },
        "not": "Ücretsiz API ticari olmayan kullanım içindir; koşullar 'promotional activities' (tanıtım) kullanımını ticari sayar ve abonelik "
               "ister. Kurum kampanyası tanıtımdır: bu kaynak kurum filminde kullanılmaz (kullanıcının tek ücretli kaynağı Magnific).",
    },
}


# ---------------------------------------------------------------- dosyalar
def dosya(v) -> Path:
    return v.dir / "veri.json"


def var_mi(v) -> bool:
    return dosya(v).exists()


def depo(v) -> Path:
    return v.dir / "veri"


def motor_kopyasi(v) -> Path:
    return v.pub / "veri" / "anlik.json"


def sozlesme(v) -> dict:
    try:
        return O.jload(dosya(v))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{dosya(v).relative_to(O.ROOT)} bozuk JSON: {e}") from None


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _simdi() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _iso(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dil(v, S: dict | None = None) -> str:
    return (S or {}).get("dil") or ("en" if v.script.get("dil") == "en" else "tr")


def _ondalik_sayisi(x) -> int:
    s = repr(float(x))
    return len(s.split(".")[1].rstrip("0")) if "." in s and "e" not in s else 0


# ---------------------------------------------------------------- sözleşmenin denetimi
def sorunlar(S: dict) -> list[tuple[str, str]]:
    """veri.json denetimi → [(❌|⚠️, mesaj)]. ❌ varsa çekilmez."""
    out = []
    K = S.get("kaynak") or {}
    url = str(K.get("url") or "")
    if not url.startswith("https://"):
        out.append(("❌", "kaynak.url https:// ile başlamalı (açık bir uç nokta)"))
    for a in ("atif", "atif_kisa", "lisans", "lisans_url"):
        if not str(S.get(a) or "").strip():
            out.append(("❌", f"{a} boş: atıf ve lisans olmadan veri kullanılmaz"))
    if not isinstance(S.get("ticari"), bool):
        out.append(("❌", "ticari: true/false (lisans kurum ve ticari kullanıma izin veriyor mu?) yazılmalı"))
    if S.get("kullanim", "kurum") not in KULLANIMLAR:
        out.append(("❌", f"kullanim: {' | '.join(KULLANIMLAR)}"))
    if S.get("tur") not in TURLER:
        out.append(("❌", f"tur: {' | '.join(TURLER)} (ekranda verinin ne olduğu doğru söylenir)"))
    k = S.get("konum") or {}
    if not str(k.get("ad") or "").strip():
        out.append(("❌", "konum.ad boş (konum kullanıcının kararı)"))
    try:
        ZoneInfo(k.get("saat_dilimi") or "Europe/Istanbul")
    except Exception:  # noqa: BLE001
        out.append(("❌", f"konum.saat_dilimi tanınmıyor: {k.get('saat_dilimi')}"))
    for a in ("enlem", "boylam"):
        if a in k:
            if not isinstance(k[a], (int, float)):
                out.append(("❌", f"konum.{a} sayı olmalı"))
            elif _ondalik_sayisi(k[a]) > 4:
                out.append(("❌", f"konum.{a} en çok 4 ondalık (kaynağın kuralı; ~10 m)"))
            elif _ondalik_sayisi(k[a]) > 2:
                out.append(("⚠️", f"konum.{a} şehir düzeyinden hassas ({k[a]}): kampın ya da kişinin tam yeri hassas olabilir, kullanıcı kararı"))
    A = S.get("alanlar") or {}
    if not A:
        out.append(("❌", "alanlar boş"))
    for ad, x in A.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,40}", ad):
            out.append(("❌", f"alan adı {ad}: küçük harf, rakam, alt çizgi"))
        if "birim" not in x:
            out.append(("❌", f"{ad}: birim yazılmalı (birimsizse \"\")"))
        if "yol" not in x and not all(k_ in x for k_ in ("seri", "deger", "islem")):
            out.append(("❌", f"{ad}: yol ya da seri + deger + islem"))
        if x.get("islem") and x["islem"] not in ISLEMLER:
            out.append(("❌", f"{ad}: islem {' | '.join(ISLEMLER)}"))
        p = x.get("pencere")
        if p and (p.get("tur") != "gece" or not (0 <= int(p.get("bas", -1)) <= 23 and 0 <= int(p.get("son", -1)) <= 23)):
            out.append(("❌", f"{ad}: pencere {{tur: gece, bas: 0–23, son: 0–23}}"))
        if p and "zaman" not in x:
            out.append(("❌", f"{ad}: pencereli alan zaman yolu ister"))
        if not isinstance(x.get("ondalik", 0), int) or not 0 <= x.get("ondalik", 0) <= 3:
            out.append(("❌", f"{ad}: ondalik 0–3"))
        r = x.get("aralik")
        if r is not None and not (isinstance(r, list) and len(r) == 2 and all(isinstance(y, (int, float)) for y in r) and r[0] < r[1]):
            out.append(("❌", f"{ad}: aralik [en az, en çok]"))
    if not S.get("ticari") and S.get("kullanim", "kurum") == "kurum":
        out.append(("❌", "lisans kurum ve ticari kullanımı kapsamıyor (ticari: false): kurum kampanyasında bu kaynak kullanılmaz. "
                          "Yalnız ticari olmayan bir iş için kullanıcı kullanim: ticari_olmayan yazar"))
    return out


# ---------------------------------------------------------------- kur (hazır tarif → veri.json)
def kur(vid: str, saglayici: str, konum: str, enlem: float, boylam: float, saat_dilimi: str = "Europe/Istanbul",
        tazelik: float | None = None, kullanim: str = "kurum", ustune: bool = False) -> dict:
    v = O.load(vid)
    if saglayici not in SAGLAYICILAR:
        raise SystemExit(f"Sağlayıcı yok: {saglayici} (hazır: {', '.join(SAGLAYICILAR)}; başka bir açık kaynak için veri.json'u elle yaz)")
    if var_mi(v) and not ustune:
        raise SystemExit(f"{dosya(v).relative_to(O.ROOT)} zaten var (değiştirmek için --ustune; konum kullanıcının kararı)")
    P = SAGLAYICILAR[saglayici]
    dil = _dil(v)
    yuv = lambda x: round(float(x), 2)  # noqa: E731  şehir düzeyi (~1 km): kampın tam yeri hassas olabilir
    if _ondalik_sayisi(enlem) > 2 or _ondalik_sayisi(boylam) > 2:
        print(f"not: koordinat şehir düzeyine yuvarlandı ({enlem}, {boylam} → {yuv(enlem)}, {yuv(boylam)}); daha hassası kullanıcı kararıdır (veri.json'da elle)")
    K = {"ad": konum, "enlem": yuv(enlem), "boylam": yuv(boylam), "duzey": "şehir", "saat_dilimi": saat_dilimi}
    S = {"surum": SURUM,
         "kaynak": {"saglayici": saglayici, "ad": P["ad"], "kurum": P["kurum"], "url": P["url"], "parametreler": P["parametreler"](K),
                    "sayfa": P["sayfa"], "kosullar": P["kosullar"]},
         "konum": K, "alanlar": json.loads(json.dumps(P["alanlar"])),
         "atif": P["atif"][dil], "atif_kisa": P["atif_kisa"][dil], "atif_anahtar": P["atif_anahtar"],
         "lisans": P["lisans"], "lisans_url": P["lisans_url"], "ticari": P["ticari"], "kullanim": kullanim, "ekranda": P["ekranda"],
         "tur": P["tur"], "tazelik_saat": tazelik or TAZELIK_SAAT, "dil": dil,
         **({"guncelleme_yolu": P["guncelleme_yolu"]} if P.get("guncelleme_yolu") else {}), "not": P["not"]}
    if dil == "en":
        for x in S["alanlar"].values():
            x["ad"] = {"Şu an": "Now", "Bu gece en düşük": "Tonight's low"}.get(x["ad"], x["ad"])
    dosya(v).write_text(json.dumps(S, ensure_ascii=False, indent=2) + "\n")
    for d, m in sorunlar(S):
        print(f"{d} {m}")
    return S


# ---------------------------------------------------------------- değerler (ham yanıt → sayılar; saf fonksiyon)
_PARCA = re.compile(r"([^.\[\]]+)|\[(-?\d+)\]")


def _yol(d, yol: str):
    """'a.b[0].c' → değer; yoksa VeriHatasi."""
    cur = d
    for ad, sira in _PARCA.findall(yol):
        try:
            cur = cur[int(sira)] if sira else cur[ad]
        except (KeyError, IndexError, TypeError):
            raise VeriHatasi(f"beklenmeyen veri: '{yol}' yanıtta yok ({ad or '[' + sira + ']'} bulunamadı)") from None
    return cur


def _zaman(x) -> dt.datetime:
    """ISO 8601 ('…Z', '+03:00' ya da saat dilimsiz → UTC) ya da Unix zamanı → UTC."""
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return dt.datetime.fromtimestamp(x, dt.timezone.utc)
    if isinstance(x, str):
        try:
            t = dt.datetime.fromisoformat(x.replace("Z", "+00:00"))
            return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            pass
    raise VeriHatasi(f"beklenmeyen veri: zaman okunamadı ({x!r})")


def _sayi(x, ad: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise VeriHatasi(f"beklenmeyen veri: {ad} sayı değil ({x!r})")
    return float(x)


def metin(deger: float, ondalik: int = 0, dil: str = "tr") -> str:
    """Ekranda yazılan sayı: yarım yukarı yuvarlama, Türkçede ondalık virgül, eksi işareti U+2212; '−0' yazılmaz."""
    q = Decimal(str(deger)).quantize(Decimal(1).scaleb(-ondalik), rounding=ROUND_HALF_UP)
    if q == 0:
        q = abs(q)
    s = f"{abs(q):.{ondalik}f}"
    if dil == "tr":
        s = s.replace(".", ",")
    return ("−" if q < 0 else "") + s


def yerel_metin(t: dt.datetime, tz: str, dil: str = "tr", yil: bool = False) -> str:
    y = t.astimezone(ZoneInfo(tz))
    ay = AYLAR["en" if dil == "en" else "tr"][y.month - 1]
    return f"{y.day} {ay}{f' {y.year}' if yil else ''} {y:%H:%M}"


def _pencere(p: dict, T: dt.datetime, tz: str) -> tuple[dt.datetime, dt.datetime]:
    """'Bu gece' (yerel saatle bas → son, ör. 21:00 → 06:00), görüntünün zamanına göre: gündüz alınırsa bu akşamın gecesi,
    gece alınırsa (bas'tan sonra ya da son'dan önce) içinde olunan gecenin kalanı."""
    Z = ZoneInfo(tz)
    y = T.astimezone(Z)
    gun = lambda d, h: dt.datetime(d.year, d.month, d.day, h, tzinfo=Z)  # noqa: E731
    bas, son = int(p["bas"]), int(p["son"])
    saat = y.replace(minute=0, second=0, microsecond=0)
    if y.hour < son:                      # gece yarısından sonra: gecenin kalanı
        return saat, gun(y, son)
    if y.hour >= bas:                     # gece başladı: şimdiden sabaha
        return saat, gun(y + dt.timedelta(days=1), son)
    return gun(y, bas), gun(y + dt.timedelta(days=1), son)


def hesapla(S: dict, ham: dict, T: dt.datetime, dil: str = "tr") -> dict:
    """Ham yanıttan alan değerleri (saf fonksiyon: aynı ham + aynı sözleşme + aynı zaman → aynı değerler; ./st deterministik yeniden hesaplar)."""
    tz = (S.get("konum") or {}).get("saat_dilimi") or "Europe/Istanbul"
    out = {}
    for ad, x in S["alanlar"].items():
        od = int(x.get("ondalik", 0))
        d = {"ad": x.get("ad", ad), "birim": x.get("birim", ""), "ekranda": x.get("ekranda", True) is not False}
        if "yol" in x:
            deger = _sayi(_yol(ham, x["yol"]), ad)
            if x.get("zaman_yolu"):
                z = _zaman(_yol(ham, x["zaman_yolu"]))
                d.update(zaman=_iso(z), zaman_yerel=yerel_metin(z, tz, dil))
        else:
            seri = _yol(ham, x["seri"])
            if x.get("sutunlu"):  # {"time": [...], "temperature_2m": [...]} (Open-Meteo)
                zs, ds = _yol(seri, x["zaman"]), _yol(seri, x["deger"])
                if not (isinstance(zs, list) and isinstance(ds, list) and len(zs) == len(ds)):
                    raise VeriHatasi(f"beklenmeyen veri: {ad} sütunları eşit uzunlukta liste değil")
                ogeler = list(zip(zs, ds))
            else:
                if not isinstance(seri, list):
                    raise VeriHatasi(f"beklenmeyen veri: {x['seri']} liste değil")
                ogeler = [(_yol(o, x["zaman"]) if x.get("zaman") else None, _yol(o, x["deger"])) for o in seri]
            if x.get("pencere"):
                a, b = _pencere(x["pencere"], T, tz)
                ogeler = [(z, val) for z, val in ogeler if a <= _zaman(z) <= b]
                d["pencere"] = f"{yerel_metin(a, tz, dil)} – {yerel_metin(b, tz, dil)}"
            if not ogeler:
                raise VeriHatasi(f"beklenmeyen veri: {ad} için pencerede değer yok")
            sayilar = [(_zaman(z) if z is not None else None, _sayi(val, ad)) for z, val in ogeler]
            islem = x["islem"]
            if islem in ("en_dusuk", "en_yuksek"):
                z, deger = (min if islem == "en_dusuk" else max)(sayilar, key=lambda zv: zv[1])  # eşitlikte ilk saat
            elif islem in ("ilk", "son"):
                z, deger = sayilar[0 if islem == "ilk" else -1]
            elif islem == "en_yakin":
                if any(z_ is None for z_, _ in sayilar):
                    raise VeriHatasi(f"beklenmeyen veri: {ad} için zaman yok (en_yakin zaman ister)")
                z, deger = min(sayilar, key=lambda zv: abs((zv[0] - T).total_seconds()))  # eşitlikte önceki saat
            else:
                z, deger = None, sum(s for _, s in sayilar) / (len(sayilar) if islem == "ortalama" else 1)
            if z is not None:
                d.update(zaman=_iso(z), zaman_yerel=yerel_metin(z, tz, dil))
            d.update(islem=islem, n=len(sayilar))
        r = x.get("aralik")
        if r and not r[0] <= deger <= r[1]:
            raise VeriHatasi(f"beklenmeyen veri: {ad} = {deger:g} {x.get('birim', '')} beklenen aralığın dışında ({r[0]:g}–{r[1]:g})")
        d.update(deger=round(deger, 6), metin=metin(deger, od, dil))
        out[ad] = d
    return out


# ---------------------------------------------------------------- istek
def _iletisim() -> str:
    """Kaynağın istediği iletişim bilgisi (MET Norway: kurumun web sitesi ya da kurumsal e-posta): ortamdan ya da studio/.env →
    STUDYO_VERI_ILETISIM. Yoksa boş (uygulama adı yine gönderilir); stüdyo kendiliğinden kimsenin e-postasını yazmaz."""
    if os.environ.get("STUDYO_VERI_ILETISIM"):
        return os.environ["STUDYO_VERI_ILETISIM"].strip()
    p = O.ROOT / ".env"
    if p.exists():
        for ln in p.read_text().splitlines():
            if ln.startswith("STUDYO_VERI_ILETISIM="):
                return ln.split("=", 1)[1].strip().strip('"')
    return ""


def tam_url(S: dict) -> str:
    K = S["kaynak"]
    q = urllib.parse.urlencode(sorted((K.get("parametreler") or {}).items()))
    return K["url"] + ("?" + q if q else "")


def _istek(url: str, ims: str | None) -> tuple[int, dict, bytes]:
    ua = UA + (f" {_iletisim()}" if _iletisim() else "")
    h = {"User-Agent": ua, "Accept": "application/json", "Accept-Encoding": "gzip"}
    if ims:
        h["If-Modified-Since"] = ims
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=ZAMAN_ASIMI) as r:
            govde = r.read(EN_BUYUK + 1)
            durum, bas = r.status, {k.lower(): val for k, val in r.headers.items()}
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return 304, {k.lower(): val for k, val in e.headers.items()}, b""
        ek = {403: " (kaynak isteği reddetti: tanımlayıcı User-Agent ya da koordinat hassasiyeti; studio/.env → STUDYO_VERI_ILETISIM)",
              429: " (çok sık istek: kaynağın sınırı; bir süre bekle)"}.get(e.code, "")
        raise VeriHatasi(f"ağ hatası: HTTP {e.code} {e.reason}{ek}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise VeriHatasi(f"ağ hatası: {getattr(e, 'reason', e)}") from None
    if len(govde) > EN_BUYUK:
        raise VeriHatasi(f"beklenmeyen veri: yanıt {EN_BUYUK // 1024 // 1024} MB'tan büyük")
    if bas.get("content-encoding") == "gzip":
        govde = gzip.decompress(govde)
    return durum, bas, govde


# ---------------------------------------------------------------- anlık görüntüler
def anliklar(v) -> list[dict]:
    d = depo(v)
    out = []
    for k in sorted(d.glob("*/kayit.json")) if d.exists() else []:
        try:
            out.append(O.jload(k))
        except json.JSONDecodeError:
            continue
    return out


def _secim_dosyasi(v) -> Path:
    return depo(v) / "secim.json"


def secim(v) -> str | None:
    """Çizilen görüntünün kimliği: secim.json (./st veri sec) ya da en yeni görüntü."""
    A = anliklar(v)
    if not A:
        return None
    f = _secim_dosyasi(v)
    k = O.jload(f).get("secili") if f.exists() else None
    return k if k and any(x["kimlik"] == k for x in A) else A[-1]["kimlik"]


def secili(v) -> dict | None:
    k = secim(v)
    return next((x for x in anliklar(v) if x["kimlik"] == k), None) if k else None


def cizim(v) -> dict | None:
    """Motorlara giden çizim verisi (seçili görüntüden; saf: yalnız dondurulmuş kayıttan, şimdiki zamana bakmaz)."""
    if not var_mi(v):
        return None
    x = secili(v)
    if not x:
        return None
    dil = x.get("dil", "tr")
    return {"surum": SURUM, "film": v.id, "kimlik": x["kimlik"], "sha": x["ham"]["sha256"][:8], "zaman": x["zaman"], "zaman_yerel": x["zaman_yerel"],
            "tur": x["tur"], "tur_ad": TURLER[x["tur"]][dil], "konum": x["konum"]["ad"], "kaynak": x["kaynak"]["kurum"],
            "atif": x["atif"], "atif_kisa": x["atif_kisa"], "lisans": x["lisans"], "ekranda": x["ekranda"],
            "degerler": {k: {a: d[a] for a in ("ad", "deger", "metin", "birim", "zaman_yerel", "pencere") if a in d} for k, d in x["degerler"].items()}}


def props(v) -> dict:
    """Remotion girdisi: {"veri": çizim verisi} yalnız canlı veri filminde; öteki filmlerin props'u değişmez."""
    c = cizim(v) if var_mi(v) else None
    return {"veri": c} if c else {}


def damga(v) -> str | None:
    """Kontak tabakası ve plaka durumu için kısa damga: 'veri 20261026T190046Z · 26 Ekim 22:00'."""
    x = secili(v) if var_mi(v) else None
    return f"veri {x['kimlik']} · {x['zaman_yerel']}" if x else None


def esitle(v):
    """Motor kopyası (public/<id>/veri/anlik.json) seçili görüntüyle aynı; kaynaklar.md ve yayin.md atıfı güncel."""
    c = cizim(v)
    p = motor_kopyasi(v)
    if c:
        p.parent.mkdir(parents=True, exist_ok=True)
        t = json.dumps(c, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
        if not p.exists() or p.read_text() != t:
            p.write_text(t)
    elif p.exists():
        p.unlink()
    kaynaklar_yaz(v)
    yayin_yaz(v)


def cek(vid: str) -> dict:
    """Kaynağa tek istek → yeni anlık görüntü (dondurulur, seçili olur). Hata: VeriHatasi (yeni görüntü yok; önceki seçili kalır)."""
    v = O.load(vid)
    if not var_mi(v):
        raise SystemExit(f"{vid}: veri.json yok (./st veri {vid} kur --saglayici met-norway --konum … --enlem … --boylam …)")
    S = sozlesme(v)
    kotu = [m for d, m in sorunlar(S) if d == "❌"]
    if kotu:
        raise SystemExit("veri.json çekilmeye hazır değil:\n- " + "\n- ".join(kotu))
    onceki = secili(v)
    durum_metni = (f"Film önceki görüntüyle çizilmeye devam eder: {onceki['kimlik']} ({onceki['zaman_yerel']})." if onceki
                   else "Bu filmin henüz anlık görüntüsü yok: veri gelene kadar film çizilmez.")
    url = tam_url(S)
    ayni = [x for x in anliklar(v) if x["istek"]["url"] == url]
    son = ayni[-1] if ayni else None
    simdi = _simdi()
    if son and _taze(son, simdi):
        exp = _yeniden_istek(son)
        if exp:
            tz = S["konum"].get("saat_dilimi") or "Europe/Istanbul"
            raise VeriBekle(f"Kaynağın önbellek kuralı: yeni veri en erken {yerel_metin(exp, tz, _dil(v, S))} (yerel) istenir "
                            f"(son görüntü {son['kimlik']}, Expires {son['istek']['basliklar'].get('expires', '—')}; aynı adrese en az "
                            f"{EN_AZ_ARALIK // 60} dk aralık). İstek gönderilmedi, yeni görüntü yazılmadı. {durum_metni}")
    ortak = _ortak_onbellek(url, simdi, v.id)
    if ortak:  # aynı adresi başka bir film az önce çekti ve süresi dolmadı: kaynağa yeniden gidilmez, aynı yanıt bu filme kopyalanır
        return _kopyala(v, S, ortak)
    try:
        kod, bas, govde = _istek(url, (son or {}).get("istek", {}).get("basliklar", {}).get("last-modified"))
    except VeriHatasi as e:
        raise VeriHatasi(f"{e} — yeni görüntü yazılmadı. {durum_metni}") from None
    if kod == 304:
        return {"yeni": False, "neden": "kaynakta veri değişmedi (HTTP 304: Last-Modified aynı)", "secili": onceki and onceki["kimlik"]}
    if kod != 200:
        raise VeriHatasi(f"beklenmeyen yanıt: HTTP {kod} — yeni görüntü yazılmadı. {durum_metni}")
    kimlik = simdi.strftime("%Y%m%dT%H%M%SZ")
    try:
        ham = json.loads(govde)
        dil = _dil(v, S)
        degerler = hesapla(S, ham, simdi, dil)
        guncelleme = _yol(ham, S["guncelleme_yolu"]) if S.get("guncelleme_yolu") else None
    except (json.JSONDecodeError, UnicodeDecodeError, VeriHatasi) as e:
        hd = depo(v) / "_hatali"
        hd.mkdir(parents=True, exist_ok=True)
        (hd / f"{kimlik}.ham").write_bytes(govde)  # incelemek için; kullanılmaz
        neden = e if isinstance(e, VeriHatasi) else f"beklenmeyen veri: JSON değil ({e})"
        raise VeriHatasi(f"{neden} — yanıt {(hd / f'{kimlik}.ham').relative_to(O.ROOT)} (kullanılmaz); yeni görüntü yazılmadı. {durum_metni}") from None
    tz = S["konum"].get("saat_dilimi") or "Europe/Istanbul"
    d = depo(v) / kimlik
    if d.exists():
        raise SystemExit(f"aynı saniyede ikinci çekim: {d.relative_to(O.ROOT)} zaten var")
    d.mkdir(parents=True)
    (d / "ham.json").write_bytes(govde)
    K = {"surum": SURUM, "kimlik": kimlik, "zaman": _iso(simdi), "zaman_yerel": yerel_metin(simdi, tz, dil, yil=True), "saat_dilimi": tz, "dil": dil,
         "istek": {"url": url, "durum": kod, "basliklar": {k: bas[k] for k in ("date", "last-modified", "expires", "content-type") if k in bas},
                   "user_agent": UA + (" + iletişim" if _iletisim() else "")},
         "ham": {"dosya": "ham.json", "sha256": _sha(govde), "bayt": len(govde)},
         "kaynak": {**{k: S["kaynak"].get(k) for k in ("saglayici", "ad", "kurum", "sayfa", "kosullar")}, **({"guncelleme": guncelleme} if guncelleme else {})},
         "konum": S["konum"], "tur": S["tur"], "atif": S["atif"], "atif_kisa": S["atif_kisa"], "atif_anahtar": S.get("atif_anahtar", ""),
         "lisans": S["lisans"], "lisans_url": S["lisans_url"], "ticari": S["ticari"], "kullanim": S.get("kullanim", "kurum"),
         "ekranda": S.get("ekranda", True), "degerler": degerler,
         "sozlesme_sha256": _sha(json.dumps(S, sort_keys=True, ensure_ascii=False).encode())}
    (d / "kayit.json").write_text(json.dumps(K, ensure_ascii=False, indent=1) + "\n")
    _secim_dosyasi(v).write_text(json.dumps({"secili": kimlik}) + "\n")
    esitle(v)
    return {"yeni": True, "kimlik": kimlik, "kayit": K, "onceki": onceki and onceki["kimlik"]}


def _expires(x: dict) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(x["istek"]["basliklar"]["expires"], "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=dt.timezone.utc)
    except (KeyError, ValueError):
        return None


def _taze(x: dict, simdi: dt.datetime) -> bool:
    """Bu görüntüden sonra aynı adrese yeniden istek gönderilmemeli mi? Expires dolmadıysa ya da görüntü EN_AZ_ARALIK'tan yeniyse."""
    e = _expires(x)
    return bool(e and simdi < e) or (simdi - _zaman(x["zaman"])).total_seconds() < EN_AZ_ARALIK


def _yeniden_istek(x: dict) -> dt.datetime:
    """En erken yeni istek: Expires ile görüntü + EN_AZ_ARALIK'tan geç olanı."""
    return max(filter(None, [_expires(x), _zaman(x["zaman"]) + dt.timedelta(seconds=EN_AZ_ARALIK)]))


def _ortak_onbellek(url: str, simdi: dt.datetime, film: str) -> tuple[str, dict] | None:
    """Stüdyonun ortak önbelleği: aynı adresin süresi dolmamış en yeni görüntüsü başka bir filmde var mı? (kaynağın kuralı: yanıtı önbellekle,
    Expires'tan önce yeniden isteme). Kendi filminin görüntüsü sayılmaz (onu Expires denetimi zaten durdurur)."""
    adaylar = []
    for k in (O.ROOT / "videos").glob("*/veri/*/kayit.json"):
        if k.parts[-4] == film:
            continue
        try:
            x = O.jload(k)
        except json.JSONDecodeError:
            continue
        if x.get("istek", {}).get("url") == url and _taze(x, simdi) and (k.parent / "ham.json").exists():
            adaylar.append((x["kimlik"], k.parts[-4], x))
    return max(adaylar)[1:] if adaylar else None


def _kopyala(v, S: dict, ortak: tuple[str, dict]) -> dict:
    film, x = ortak
    kaynak = O.ROOT / "videos" / film / "veri" / x["kimlik"]
    govde = (kaynak / "ham.json").read_bytes()
    if _sha(govde) != x["ham"]["sha256"]:
        raise VeriHatasi(f"ortak önbellek bozuk: {film}/{x['kimlik']} sha256 tutmuyor; yeni görüntü yazılmadı")
    d = depo(v) / x["kimlik"]
    if d.exists():
        raise VeriBekle(f"bu filmde {x['kimlik']} zaten var ve kaynağın önbellek süresi dolmadı: istek gönderilmedi")
    dil = _dil(v, S)
    degerler = hesapla(S, json.loads(govde), _zaman(x["zaman"]), dil)  # bu filmin sözleşmesiyle, görüntünün kendi zamanında
    d.mkdir(parents=True)
    (d / "ham.json").write_bytes(govde)
    tz = S["konum"].get("saat_dilimi") or "Europe/Istanbul"
    K = {**x, "dil": dil, "saat_dilimi": tz, "zaman_yerel": yerel_metin(_zaman(x["zaman"]), tz, dil, yil=True), "konum": S["konum"], "tur": S["tur"], "atif": S["atif"], "atif_kisa": S["atif_kisa"], "atif_anahtar": S.get("atif_anahtar", ""),
         "lisans": S["lisans"], "lisans_url": S["lisans_url"], "ticari": S["ticari"], "kullanim": S.get("kullanim", "kurum"),
         "ekranda": S.get("ekranda", True), "degerler": degerler, "paylasilan": f"{film}/{x['kimlik']}",
         "sozlesme_sha256": _sha(json.dumps(S, sort_keys=True, ensure_ascii=False).encode())}
    (d / "kayit.json").write_text(json.dumps(K, ensure_ascii=False, indent=1) + "\n")
    onceki = secili(v)
    _secim_dosyasi(v).write_text(json.dumps({"secili": x["kimlik"]}) + "\n")
    esitle(v)
    return {"yeni": True, "kimlik": x["kimlik"], "kayit": K, "onceki": onceki and onceki["kimlik"], "paylasilan": film}


def sec(vid: str, kimlik: str) -> dict:
    v = O.load(vid)
    A = anliklar(v)
    if not A:
        raise SystemExit(f"{vid}: anlık görüntü yok (./st veri {vid} cek)")
    hedef = A[-1] if kimlik == "son" else next((x for x in A if x["kimlik"] == kimlik), None)
    if not hedef:
        raise SystemExit(f"görüntü yok: {kimlik} (var olanlar: {', '.join(x['kimlik'] for x in A)})")
    _secim_dosyasi(v).write_text(json.dumps({"secili": hedef["kimlik"]}) + "\n")
    esitle(v)
    return hedef


def dogrula(v) -> list[tuple[str, bool, str]]:
    """Dondurma: her görüntünün ham yanıtı kayıttaki sha256 ile aynı; seçili görüntünün değerleri ham yanıttan yeniden hesapta birebir aynı
    (sözleşme değişmediyse); motor kopyası seçili görüntüyle aynı."""
    out = []
    for x in anliklar(v):
        p = depo(v) / x["kimlik"] / "ham.json"
        ok = p.exists() and _sha(p.read_bytes()) == x["ham"]["sha256"]
        out.append((f"görüntü {x['kimlik']}", ok, "" if ok else "ham yanıt kayıttaki sha256 ile aynı değil (dosya değişmiş ya da yok)"))
    x = secili(v)
    if x:
        p = depo(v) / x["kimlik"] / "ham.json"
        if p.exists():
            S = sozlesme(v)
            ayni_soz = _sha(json.dumps(S, sort_keys=True, ensure_ascii=False).encode()) == x.get("sozlesme_sha256")
            try:
                yeni = hesapla(S, json.loads(p.read_bytes()), _zaman(x["zaman"]), x.get("dil", "tr"))
                esit = yeni == x["degerler"]
            except VeriHatasi as e:
                yeni, esit = None, False
                out.append(("yeniden hesap", False, str(e)))
            if yeni is not None:
                out.append(("yeniden hesap", esit or not ayni_soz,
                            "" if esit else ("veri.json görüntüden sonra değişti: değerler yeni sözleşmeyle farklı (yeniden çek)" if not ayni_soz
                                             else "ham yanıttan yeniden hesaplanan değerler kayıttakinden farklı")))
        c = cizim(v)
        m = motor_kopyasi(v)
        kop = m.exists() and json.loads(m.read_text()) == c
        out.append(("motor kopyası", kop, "" if kop else f"{m.relative_to(O.ROOT)} seçili görüntüyle aynı değil (./st veri {v.id} sec son)"))
    return out


# ---------------------------------------------------------------- atıf: kaynaklar.md ve yayin.md
_V_SATIR = re.compile(r"^\|\s*V\d+\s*\|")
_V_KAYNAK = re.compile(r"^V\d+\.\s")
_YER_TUTUCU_SATIR = "| 1 | s1 | [iddia] | [durum] | [no] | [not] |"
_YER_TUTUCU_KAYNAK = "1. [Yazar, başlık, yayın/yıl, URL: neyi destekliyor]"
KAYNAK_SABLONU = """# Kaynaklar — {baslik}

> Kural: her iddia ≥ 2 güvenilir, bağımsız kaynak. Durum: ✅ doğrulandı · ⚠️ kısmen / düzeltme önerisi · ❌ desteklenmiyor
> Canlı veri satırları (V) `./st veri` tarafından dondurulmuş anlık görüntüden yazılır: ekrandaki her rakamın kaynağı o görüntünün kendisidir.

## İddia tablosu
| # | Cümle | İddia | Durum | Kaynaklar (no) | Not / önerilen ifade |
|---|---|---|---|---|---|

## Kaynakça

## Azınlık görüşleri / rivayetler
- yok

## Önerilen metin düzeltmeleri
- yok
"""


def _iddia_satirlari(v, x: dict) -> tuple[list[str], list[str]]:
    S = sozlesme(v)
    satir, kaynak = [], []
    i = 0
    for ad, d in x["degerler"].items():
        if not d.get("ekranda", True):
            continue
        i += 1
        a = (S.get("alanlar") or {}).get(ad, {})
        nerede = a.get("vurus") or "ekran"
        ne = f"{x['konum']['ad']}: {d['ad']} {d['metin']}{(' ' + d['birim']) if d['birim'] else ''} ({TURLER[x['tur']]['tr']}"
        ne += f"; {d['pencere']}" if d.get("pencere") else (f"; {d['zaman_yerel']}" if d.get("zaman_yerel") else "")
        ne += ")"
        satir.append(f"| V{i} | {nerede} | {ne} | ✅ | V{i} | canlı veri: dondurulmuş görüntü {x['kimlik']} · sha256 {x['ham']['sha256'][:12]} · "
                     f"{x['zaman_yerel']} · ekrandaki değer bu görüntüden hesaplanır (tek kaynak: verinin kendisi) |")
        kaynak.append(f"V{i}. {x['kaynak']['kurum']}, {x['kaynak']['ad']}, {x['istek']['url']} (alındı {x['zaman_yerel']}, {x['kimlik']}); "
                      f"lisans {x['lisans']} {x['lisans_url']}; atıf: {x['atif']}: {d['ad']} değerini destekler.")
    return satir, kaynak


def kaynaklar_yaz(v):
    """kaynaklar.md: iddia tablosundaki V satırları ve Kaynakça'daki V kaynakları seçili görüntüden yeniden yazılır (✅); şablonun boş
    yer tutucu satırı kaldırılır; gerisi (elle yazılmış iddialar) olduğu gibi kalır. Görüntü yoksa V satırları silinir."""
    x = secili(v) if var_mi(v) else None
    p = v.dir / "kaynaklar.md"
    if not p.exists():
        if not x:
            return
        p.write_text(KAYNAK_SABLONU.format(baslik=v.script.get("title", v.id)))
    satir, kaynak = _iddia_satirlari(v, x) if x else ([], [])
    L = p.read_text().splitlines()
    L = [ln for ln in L if not _V_SATIR.match(ln) and not _V_KAYNAK.match(ln)
         and not (x and ln.strip() in (_YER_TUTUCU_SATIR, _YER_TUTUCU_KAYNAK))]
    # tabloya: başlık ayırıcısından (|---|) hemen sonra
    ayr = next((i for i, ln in enumerate(L) if ln.startswith("|") and set(ln) <= set("|-: ")), None)
    if ayr is None and satir:
        bas = next((i for i, ln in enumerate(L) if ln.startswith("## İddia")), len(L) - 1)
        L[bas + 1:bas + 1] = ["| # | Cümle | İddia | Durum | Kaynaklar (no) | Not / önerilen ifade |", "|---|---|---|---|---|---|"]
        ayr = bas + 2
    if satir:
        L[ayr + 1:ayr + 1] = satir
    if kaynak:
        kb = next((i for i, ln in enumerate(L) if ln.startswith("## Kaynakça")), None)
        if kb is None:
            L += ["", "## Kaynakça"]
            kb = len(L) - 1
        L[kb + 1:kb + 1] = kaynak
    t = "\n".join(L).rstrip() + "\n"
    if t != p.read_text():
        p.write_text(t)


VERI_BAS = "<!-- st:veri (./st veri yazar; elle değiştirme) -->"
VERI_SON = "<!-- /st:veri -->"


def yayin_md(v) -> str:
    x = secili(v)
    if not x:
        return f"{VERI_BAS}\n## Veri kaynağı\n[anlık görüntü yok: ./st veri {v.id} cek]\n{VERI_SON}"
    L = [VERI_BAS, "## Veri kaynağı (canlı veri, atıf zorunlu)",
         f"- **Açıklamaya girecek atıf:** {x['atif']}",
         f"- **Kaynak:** {x['kaynak']['kurum']} · {x['kaynak']['ad']} · {x['kaynak'].get('sayfa') or x['istek']['url']}",
         f"- **Lisans:** {x['lisans']} · {x['lisans_url']}" + (" · ticari ve kurum kullanımı serbest" if x["ticari"] else
                                                                " · yalnız ticari olmayan kullanım (kurum kampanyasında yayınlanmaz)"),
         f"- **Anlık görüntü:** {x['kimlik']} · {x['zaman_yerel']} ({x['saat_dilimi']}) · sha256 {x['ham']['sha256'][:12]} · "
         f"{TURLER[x['tur']]['tr']}" + (f" · kaynak güncellemesi {x['kaynak']['guncelleme']}" if x["kaynak"].get("guncelleme") else ""),
         "- **Ekrandaki değerler:** " + "; ".join(f"{d['ad']} {d['metin']}{(' ' + d['birim']) if d['birim'] else ''}"
                                                   for d in x["degerler"].values() if d.get("ekranda", True)) + f" ({x['konum']['ad']})",
         "- **Ekranda atıf:** " + ("var (kullanıcının isteği; filmde " + f"“{x['atif_kisa']}”)" if x["ekranda"] else "yok (atıf bu açıklamada ve kaynaklar.md'de)"),
         "- Veri yeniden çekilirse film yeni görüntüyle yeniden çizilir; yayından önce bu satırların filmle aynı görüntüyü gösterdiğine bak.",
         VERI_SON]
    return "\n".join(L)


def yayin_yaz(v) -> Path | None:
    """yayin.md'deki veri bloğunu yeniler (dosya varsa); blok yoksa Beyanlar'dan (yoksa Dosyalar'dan) önce eklenir."""
    p = v.dir / "yayin.md"
    if not p.exists() or not var_mi(v):
        return None
    t = p.read_text()
    blok = yayin_md(v)
    if VERI_BAS in t and VERI_SON in t:
        t2 = t[:t.index(VERI_BAS)] + blok + t[t.index(VERI_SON) + len(VERI_SON):]
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


def yayin_durumu(v) -> bool | None:
    """yayin.md'de veri bloğu seçili görüntüyle dolu mu? yayin.md yoksa None."""
    p = v.dir / "yayin.md"
    if not p.exists():
        return None
    t = p.read_text()
    x = secili(v)
    return bool(x) and VERI_BAS in t and VERI_SON in t and x["kimlik"] in t[t.index(VERI_BAS):t.index(VERI_SON)] and x["atif"] in t


# ---------------------------------------------------------------- ekranda ne yazıyor (OCR: macOS Vision)
def ocr_hazir() -> Path | None:
    """pipeline/ocr.swift → out/_araclar/ocr (swiftc; Xcode komut satırı araçları). Derlenemezse None (ölçüm göz satırına düşer)."""
    if OCR_BIN.exists() and OCR_BIN.stat().st_mtime >= OCR_KAYNAK.stat().st_mtime:
        return OCR_BIN
    if not shutil.which("swiftc"):
        return None
    OCR_BIN.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["swiftc", "-O", str(OCR_KAYNAK), "-o", str(OCR_BIN)], capture_output=True, text=True)
    return OCR_BIN if r.returncode == 0 and OCR_BIN.exists() else None


def ocr(pngs: list[Path]) -> dict[str, list[str]] | None:
    b = ocr_hazir()
    if not b or not pngs:
        return None
    r = subprocess.run([str(b), *map(str, pngs)], capture_output=True, text=True)
    out = {}
    for ln in r.stdout.splitlines():
        try:
            j = json.loads(ln)
        except json.JSONDecodeError:
            continue
        out[j["dosya"]] = [s["metin"] for s in j.get("satirlar", [])]
    return out


def _norm(s: str) -> str:
    s = s.replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", s.replace("−", "-").replace("–", "-").replace("—", "-").replace("º", "°"))


def ekranda_bul(metinler: list[str], aranan: str, sayi: bool) -> bool:
    t = _norm(" ".join(metinler))
    a = _norm(aranan)
    if sayi:
        return re.search(rf"(?<![\d.,\-]){re.escape(a)}(?![\d])(?!,\d)", t) is not None
    return a in t


def kanit_karesi(v) -> int | None:
    """Değerlerin ekranda tam göründüğü kare: script.json → veri_isareti (işaret adı), yoksa poster işareti."""
    ad = v.script.get("veri_isareti") or ("poster" if "poster" in v.cues else None)
    if ad and ad in v.cues:
        return min(max(0, v.nframes - 1), round(v.cues[ad] * v.fps))
    return None


def mp4_karesi(mp4: Path, kare: int, hedef: Path) -> Path | None:
    hedef.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", f"select=eq(n\\,{kare})", "-vsync", "0", "-frames:v", "1", str(hedef)],
                       capture_output=True)
    return hedef if r.returncode == 0 and hedef.exists() else None


def ekran_denetimi(v, png: Path) -> dict:
    """Bir karede: ekranda olması gereken her değerin metni ve (kullanıcı ekranda atıf istediyse) atıf okunuyor mu? Verinin türü bilgi olarak."""
    x = secili(v)
    o = ocr([png])
    if o is None:
        return {"ocr": False}
    m = o.get(str(png), [])
    dil = x.get("dil", "tr")
    eksik = [f"{d['ad']} {d['metin']}" for d in x["degerler"].values() if d.get("ekranda", True) and not ekranda_bul(m, d["metin"], True)]
    atif = (not x["ekranda"]) or ekranda_bul(m, x.get("atif_anahtar") or x["kaynak"]["kurum"], False)
    tur = ekranda_bul(m, TURLER[x["tur"]][dil], False)
    return {"ocr": True, "okunan": m, "eksik": eksik, "atif": atif, "tur": tur}


# ---------------------------------------------------------------- sahne kodu
def kod_dosyalari(v) -> list[Path]:
    """Filmin kendi sahne kodu (kit ve kütüphane dosyaları hariç): Remotion src/<kod>/, HyperFrames hf/<id>/ HTML, Blender blender/<id>/ + üst katman."""
    out = []
    if v.motor in ("remotion", "blender") and v.kod_dizini.exists():
        out += sorted(v.kod_dizini.rglob("*.ts*"))
    if v.motor == "hyperframes":
        d = O.ROOT / "hf" / v.id
        out += [p for p in [d / "index.html", *sorted((d / "compositions").rglob("*.html"))] if p.exists()]
    if v.motor == "blender":
        d = O.ROOT / "blender" / v.id
        out += sorted(d.glob("*.py")) if d.exists() else []
    return out


def _yorumsuz(t: str, suffix: str) -> str:
    if suffix == ".py":
        return re.sub(r"#.*", "", t)
    t = re.sub(r"/\*.*?\*/|<!--.*?-->", "", t, flags=re.S)
    return re.sub(r"(?<![:\"'])//.*", "", t)


def kod_denetimi(v) -> list[tuple[str, str]]:
    """[(durum, mesaj)]: kod veriyi okuyor mu (useVeri / ST.veri), çizimde ağ var mı, seçili görüntünün değeri elle yazılmış mı."""
    D = kod_dosyalari(v)
    if not D:
        return [("⚠️", "sahne kodu yok")]
    metin_ = {p: _yorumsuz(p.read_text(), p.suffix) for p in D}
    out = []
    okur = [p for p, t in metin_.items() if re.search(r"\buseVeri\s*\(|\bST\.veri\b|\bST\[\s*['\"]veri['\"]\s*\]|props\.veri\b", t)]
    out.append(("✅", "kod veriyi seçili görüntüden okuyor: " + ", ".join(p.name for p in okur)) if okur else
               ("❌", "kod veriyi okumuyor: Remotion useVeri(film) (src/lib/veri), HyperFrames ST.veri, Blender ST.veri"))
    ag = [f"{p.name}: {m.group(0)}" for p, t in metin_.items() for m in [AG.search(t)] if m]
    S = sozlesme(v)
    host = urllib.parse.urlparse(str((S.get("kaynak") or {}).get("url", ""))).netloc
    ag += [f"{p.name}: {host}" for p, t in metin_.items() if host and host in t]
    out.append(("❌", "çizim sırasında ağ yok (kural 8): " + "; ".join(ag)) if ag else ("✅", "sahne kodunda ağ çağrısı yok"))
    x = secili(v)
    elle = []
    for d in (x or {}).get("degerler", {}).values():
        b = re.escape(d["birim"]) if d["birim"] else "°"
        pat = re.compile(rf"""['"`>]\s*{re.escape(d['metin'])}\s*(?:{b}|°)""")
        elle += [f"{p.name}: {d['metin']} {d['birim']}" for p, t in metin_.items() if pat.search(t)]
    if elle:
        out.append(("⚠️", "seçili görüntünün değeri kodda elle yazılmış olabilir (görüntü değişince ekran değişmez): " + "; ".join(sorted(set(elle)))))
    return out


# ---------------------------------------------------------------- ölçüm satırları (yalnız veri.json'u olan filmde)
def _yas(x) -> float:
    return (_simdi() - _zaman(x["zaman"])).total_seconds() / 3600


def yas_metni(saat: float) -> str:
    if saat < 1:
        return f"{max(0, round(saat * 60))} dk"
    if saat < 48:
        return f"{int(saat)} sa {round((saat % 1) * 60)} dk"
    return f"{saat / 24:.1f} gün"


def olcum_satirlari(v, renders: dict | None = None, teslim: bool = False, cikti: Path | None = None) -> list[dict]:
    row = lambda ad, deger, cita, durum, kanit="": {"ad": ad, "deger": deger, "cita": cita, "durum": durum, "kanit": kanit}  # noqa: E731
    if not var_mi(v):
        return []
    S = sozlesme(v)
    rows = []
    kotu = [f"{d} {m}" for d, m in sorunlar(S)]
    x = secili(v)
    if not x:
        return [row("Canlı veri: anlık görüntü", "yok", "dondurulmuş bir görüntü (./st veri cek)", "❌", "; ".join(kotu))]
    dg = dogrula(v)
    bozuk = [f"{a}: {m}" for a, ok, m in dg if not ok]
    rows.append(row("Canlı veri: anlık görüntü", f"{x['kimlik']} · {x['zaman_yerel']} · {x['kaynak']['kurum']} · {x['konum']['ad']} · sha256 {x['ham']['sha256'][:8]}"
                    f" · {len(anliklar(v))} görüntü kayıtlı", "dondurulmuş (sha256), değerler ham yanıttan yeniden hesapta aynı, motor kopyası seçiliyle aynı",
                    "✅" if not bozuk else "❌", "; ".join(bozuk)))
    yas, taze = _yas(x), float(S.get("tazelik_saat") or TAZELIK_SAAT)
    rows.append(row("Canlı veri: görüntünün yaşı", yas_metni(yas), "bilgi (eski görüntü de kullanılabilir; yenisi: Veriyi yenile)", "—",
                    "" if yas <= taze else f"yenisi istenirse: ./st veri {v.id} cek"))
    if x["ticari"]:
        lis = ("✅", f"{x['lisans']} · ticari ve kurum kullanımı serbest")
    elif x.get("kullanim") == "ticari_olmayan":
        lis = ("⚠️", f"{x['lisans']} · yalnız ticari olmayan kullanım (kullanıcının beyanı): kurum kampanyasında yayınlanmaz")
    else:
        lis = ("❌", f"{x['lisans']} · lisans kurum ve ticari kullanımı kapsamıyor")
    rows.append(row("Canlı veri: lisans ve kullanım", lis[1], "lisans filmin kullanımını kapsıyor (kurum kampanyası = tanıtım)", lis[0],
                    "; ".join(m for m in kotu if "lisans" in m)))
    kd = (v.dir / "kaynaklar.md").read_text() if (v.dir / "kaynaklar.md").exists() else ""
    satir, _ = _iddia_satirlari(v, x)
    ok_k = bool(satir) and all(s in kd for s in satir)
    rows.append(row("Canlı veri: atıf kaynaklar.md'de", f"{len(satir)} değer · V satırları ✅" if ok_k else "eksik ya da başka görüntüden",
                    "ekrandaki her değer kaynaklar.md'de seçili görüntüyle (./st veri yazar)", "✅" if ok_k else "❌",
                    "" if ok_k else f"./st veri {v.id} sec {x['kimlik']} (kaynaklar.md'yi yeniden yazar)"))
    yd = yayin_durumu(v)
    rows.append(row("Canlı veri: atıf yayın paketinde (yayin.md)", {True: "dolu, seçili görüntüyle", False: "eksik ya da başka görüntüden", None: "yayin.md yok"}[yd],
                    "yayın açıklamasında atıf ve lisans (./st yayin yazar)", "✅" if yd else ("❌" if yd is False or teslim else "⚠️"),
                    "" if yd else f"./st yayin {v.id}"))
    kod = kod_denetimi(v)
    kd_durum = "❌" if any(d == "❌" for d, _ in kod) else ("⚠️" if any(d == "⚠️" for d, _ in kod) else "✅")
    rows.append(row("Canlı veri: sahne kodu", "; ".join(m for d, m in kod if d != "✅") or "veri seçili görüntüden, çizimde ağ yok",
                    "kod değeri seçili görüntüden okur, çizimde ağ yok, değer elle yazılmaz", kd_durum))
    # ekranda: kanıt karesi (script.json → veri_isareti) filmin dosyasından okunur
    kare = kanit_karesi(v)
    anlik = motor_kopyasi(v)
    for fmt, mp4 in (renders or {}).items():
        mp4 = Path(mp4)
        ad = f"[{fmt}] Ekrandaki rakamlar dondurulmuş veriyle aynı"
        if not mp4.exists():
            continue
        if kare is None:
            rows.append(row(ad, "kanıt karesi yok", "script.json → veri_isareti: değerlerin ekranda tam göründüğü işaret", "⚠️"))
            continue
        if anlik.exists() and mp4.stat().st_mtime < anlik.stat().st_mtime:
            rows.append(row(ad, f"film seçili görüntüden ({x['kimlik']}) önce çizilmiş", "film seçili görüntüyle çizilir", "❌",
                            "yeniden çiz: ./st inceleme (kaba kurgu) ya da ./st render --final"))
            continue
        hedef = (cikti or O.ROOT / "out" / "_veri" / v.id) / f"kanit-{fmt}-f{kare:05d}.png"
        png = mp4_karesi(mp4, kare, hedef)
        E = ekran_denetimi(v, png) if png else {"ocr": False}
        if not E["ocr"]:
            rows.append(row(ad, f"f{kare} ({O.tc(kare / v.fps)}) · yazı tanıma yok", "değerler ekranda", "👁",
                            str(png.relative_to(O.ROOT)) if png else ""))
            continue
        degerler = "; ".join(f"{d['ad']} {d['metin']}" for d in x["degerler"].values() if d.get("ekranda", True))
        sorun = E["eksik"] + ([] if E["atif"] else ["atıf okunmadı (ekranda atıf istenmişti)"])
        durum = "❌" if sorun else "✅"
        rows.append(row(ad, f"f{kare} ({O.tc(kare / v.fps)}) · görüntü {x['kimlik']}: {degerler}",
                        "her değerin metni ekranda dondurulmuş görüntüyle aynı (ekranda atıf yalnız istendiyse aranır)",
                        durum, ("eksik: " + ", ".join(sorun) + " · " if sorun else "") + "okunan: " + " / ".join(E["okunan"])[:400]
                        + f" · {png.relative_to(O.ROOT)}"))
    return rows


# ---------------------------------------------------------------- panel
def sonraki_istek(v) -> str | None:
    """Kaynağın önbellek kuralına göre bu filmin en erken yeni istek saati (yerel; süresi dolduysa None)."""
    S = sozlesme(v)
    url = tam_url(S)
    ayni = [x for x in anliklar(v) if x["istek"]["url"] == url]
    if not ayni or not _taze(ayni[-1], _simdi()):
        return None
    return yerel_metin(_yeniden_istek(ayni[-1]), S["konum"].get("saat_dilimi") or "Europe/Istanbul", _dil(v, S))


def ozet(v) -> dict | None:
    if not var_mi(v):
        return None
    S = sozlesme(v)
    x = secili(v)
    A = anliklar(v)
    yas = _yas(x) if x else None

    def kisa(a):
        kd = depo(v) / a["kimlik"] / "kareler"   # ./st veri kare: kanıt karesi her format için <format>.png
        kareler = {p.stem: str(p.relative_to(O.KANAL)) for p in sorted(kd.glob("*.png"))} if kd.exists() else {}
        return {"kimlik": a["kimlik"], "zaman_yerel": a["zaman_yerel"], "sha": a["ham"]["sha256"][:8],
                "degerler": [{"ad": d["ad"], "metin": d["metin"], "birim": d["birim"], "pencere": d.get("pencere"), "zaman_yerel": d.get("zaman_yerel")}
                             for d in a["degerler"].values()], "kareler": kareler, "guncelleme": a["kaynak"].get("guncelleme")}
    return {"kaynak": {k: (S.get("kaynak") or {}).get(k) for k in ("saglayici", "ad", "kurum", "sayfa", "kosullar")},
            "konum": S.get("konum"), "atif": S.get("atif"), "atif_kisa": S.get("atif_kisa"), "lisans": S.get("lisans"), "lisans_url": S.get("lisans_url"),
            "ticari": S.get("ticari"), "kullanim": S.get("kullanim", "kurum"), "ekranda": S.get("ekranda", True), "tur": TURLER.get(S.get("tur"), {}).get("tr"),
            "sorunlar": [{"durum": d, "mesaj": m} for d, m in sorunlar(S)], "tazelik": S.get("tazelik_saat") or TAZELIK_SAAT,
            "secili": x and x["kimlik"], "yas": yas, "yasMetni": yas_metni(yas) if yas is not None else None, "sonraki": sonraki_istek(v),
            "anliklar": [kisa(a) for a in reversed(A)], "kanit": v.script.get("veri_isareti")}
