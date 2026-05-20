# 🔍 FRAKTAL SCANNER — Evrensel Piyasa Tarama Sistemi

Her 4 saatte tüm piyasaları tara → Fraktal skoru hesapla → Telegram'a gönder → Otomatik işlem

---

## ⚡ 5 DAKİKADA KURULUM

```bash
# 1. Kur
pip install -r requirements.txt

# 2. Ayarla
cp .env.example .env
nano .env   # (sadece TELEGRAM_TOKEN ve TELEGRAM_CHAT doldur, gerisi opsiyonel)

# 3. Çalıştır
python3 scanner_main.py
```

---

## 📊 NE YAPTIĞI

```
Her 4 saatte:

₿  Kripto   → Bybit/Binance'ten top 300 coin
🇺🇸 ABD Hisse → S&P500 + NASDAQ (Yahoo Finance)
🇹🇷 BIST      → BIST100 hisseleri (Yahoo Finance)
💱 Forex     → Ana çiftler + Altın/Gümüş
        ↓
Fraktal Sayı Sistemi uygula (2.6·3.0·3.3·4.2·4.6·5.7·6.0·7.7·8.4·9.2·10.6)
        ↓
Her varlığa 0-100 arası skor ver
        ↓
Top 5 sinyali Telegram'a gönder
        ↓
AUTO_TRADE=true ise → En iyi kripto sinyaline otomatik emir
```

---

## 📱 TELEGRAM ÖRNEK MESAJI

```
🔍 Tarama #12 — 2026-05-18 08:00 UTC
──────────────────────────────────
₿ CRYPTO: 287 tarandı
🇺🇸 US_STOCK: 52 tarandı
🇹🇷 BIST: 48 tarandı
💱 FOREX: 9 tarandı

⭐ Top 5 Sinyal:

1. ₿ BTC/USDT
   💲 $113,060 (+2.3%)
   📐 Skor: 87/100 · 🟢 GÜÇLÜ AL
   📊 Yeni Başlangıç (+6.0) → %85 pozisyon

2. 🇺🇸 NVDA
   💲 $875.40 (+1.8%)
   📐 Skor: 81/100 · 🟡 AL
   📊 Ara Onay 1 (+4.6) → %60 pozisyon

3. 🇹🇷 THYAO
   💲 ₺312.50 (+3.1%)
   📐 Skor: 76/100 · 🟡 AL
   📊 Kritik Eşik (+5.7) → %75 pozisyon
...
```

---

## 🎯 FRAKTAL SKORU NASIL HESAPLANIR?

| Kriter | Max Puan |
|---|---|
| Seviye gücü (hangi delta'da) | 35 |
| Bant içi konum (%40-80 optimal) | 20 |
| Sonraki seviyeye yakınlık | 20 |
| İşlem hacmi | 15 |
| Fiyat değişimi | 10 |
| **Toplam** | **100** |

- **80-100**: 🟢 Güçlü Al
- **70-79**: 🟡 Al
- **60-69**: 🟠 İzle
- **<60**: ⏸ Sinyal yok

---

## ⚙️ AYARLAR

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SCAN_INTERVAL_H` | 4 | Tarama sıklığı |
| `TOP_SIGNALS` | 5 | Kaç sinyal gönderilsin |
| `MIN_SCORE` | 70 | Minimum skor eşiği |
| `AUTO_TRADE` | false | Otomatik işlem |
| `PAPER_MODE` | true | Simülasyon modu |
| `CAPITAL_PER_SIGNAL` | $200 | İşlem başına sermaye |
| `MAX_OPEN_TRADES` | 5 | Max açık pozisyon |

---

## ☁️ RAILWAY'DE OTOMATIK ÇALIŞTIRMA

1. GitHub'a yükle
2. railway.app → Deploy
3. Variables → .env içeriğini ekle
4. 7/24 otomatik çalışır

---

## ⚠️ ÖNEMLİ NOTLAR

- **ABD + BIST hisseleri**: Sinyal gönderir ama otomatik işlem yapmaz (borsa saati kısıtı, farklı broker gerekir)
- **Kripto**: Tam otomatik (Bybit API)
- **Forex**: Sadece sinyal (otomatik değil)
- `MIN_SCORE=70` ile başla, deneyim kazandıkça artır
- Her zaman `PAPER_MODE=true` ile test et
