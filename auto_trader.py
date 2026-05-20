"""
auto_trader.py — Otomatik İşlem Modülü
En iyi sinyallere göre emir gönderir
"""
import logging, time, json, urllib.request, urllib.parse
log = logging.getLogger('AutoTrader')

class AutoTrader:
    def __init__(self, config):
        self.config    = config
        self.paper     = config['paper_mode']
        self.positions = {}  # {symbol: {poz_pct, entry_price, market}}
        self.max_open  = config.get('max_open_trades', 5)
        self.capital   = config.get('capital_per_signal', 200)
        self._exchange = None
        if not self.paper:
            self._init_exchange()

    def _init_exchange(self):
        try:
            import ccxt
            self._exchange = ccxt.bybit({
                'apiKey' : self.config['bybit_key'],
                'secret' : self.config['bybit_secret'],
                'enableRateLimit': True,
            })
            log.info("✅ Bybit bağlantısı OK")
        except Exception as e:
            log.error(f"Bybit bağlantı hatası: {e}")

    def execute_signals(self, signals):
        done = 0
        open_count = len(self.positions)

        for sig in signals:
            if open_count >= self.max_open:
                log.info(f"Max açık işlem ({self.max_open}) doldu, atlanıyor.")
                break

            sym    = sig['symbol']
            price  = sig['price']
            market = sig['market']
            action = sig['action']

            # Sadece AL sinyallerini otomatik işle
            if '🟢' not in action and '🟡' not in action:
                continue

            # Zaten pozisyon var mı?
            if sym in self.positions:
                log.info(f"{sym} zaten açık, atlanıyor.")
                continue

            sv = sig.get('small_scale', {}) or {}
            target_poz = sv.get('sv', {}).get('poz', 30) if sv else 30

            # Sadece kripto otomatik işlem (hisse/forex için manuel)
            if market != 'crypto':
                log.info(f"⚠️ {sym} ({market}): Otomatik işlem sadece kripto. Sinyal loglandı.")
                continue

            success = self._place_crypto_order(sym, price, target_poz)
            if success:
                self.positions[sym] = {
                    'entry_price': price,
                    'target_poz' : target_poz,
                    'market'     : market,
                    'action'     : action,
                    'ts'         : time.time(),
                }
                done += 1
                open_count += 1
                log.info(f"✅ Pozisyon açıldı: {sym} @ ${price:,.4g} | %{target_poz}")

        return done

    def _place_crypto_order(self, symbol, price, poz_pct):
        amount_usd = self.capital * (poz_pct / 100)
        amount_coin = amount_usd / price

        if self.paper:
            log.info(f"📄 [PAPER] BUY {symbol}: ${amount_usd:.2f} ({amount_coin:.6f} coin) @ ${price:,.4g}")
            return True

        try:
            sym_clean = symbol.replace('/', '')
            order = self._exchange.create_market_buy_order(symbol, amount_coin)
            log.info(f"💰 CANLI EMİR: {order['id']} | {symbol} | ${amount_usd:.2f}")
            return True
        except Exception as e:
            log.error(f"Emir hatası {symbol}: {e}")
            return False

    def get_open_positions(self):
        return self.positions

    def close_position(self, symbol, price, reason=''):
        if symbol not in self.positions:
            return False
        pos = self.positions[symbol]
        pnl_pct = (price - pos['entry_price']) / pos['entry_price'] * 100
        log.info(f"🔚 POZİSYON KAPAT: {symbol} | Giriş: ${pos['entry_price']:,.4g} → Çıkış: ${price:,.4g} | PnL: {pnl_pct:+.1f}%")
        del self.positions[symbol]
        return True


# ─────────────────────────────────────────────────────────────────────────────
"""
scanner_notifier.py — Bildirim Sistemi
Telegram + Email
"""

class ScannerNotifier:
    def __init__(self, config):
        self.token   = config.get('telegram_token', '')
        self.chat_id = config.get('telegram_chat', '')
        self.enabled = bool(self.token and self.chat_id)
        self._log    = logging.getLogger('Notifier')
        if self.enabled:
            self._log.info(f"📱 Telegram aktif")

    def send(self, msg):
        self._log.info(f"📣 {msg[:100]}")
        if not self.enabled: return
        try:
            url  = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = urllib.parse.urlencode({
                'chat_id'   : self.chat_id,
                'text'      : msg,
                'parse_mode': 'HTML'
            }).encode()
            req = urllib.request.Request(url, data=data)
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            self._log.warning(f"Telegram hata: {e}")

    def send_startup(self, config):
        markets = []
        if config.get('scan_crypto'):    markets.append('₿ Kripto')
        if config.get('scan_us_stocks'): markets.append('🇺🇸 ABD Hisse')
        if config.get('scan_bist'):      markets.append('🇹🇷 BIST')
        if config.get('scan_forex'):     markets.append('💱 Forex')

        msg = (
            f"🤖 <b>Fraktal Scanner Başladı</b>\n"
            f"{'─'*30}\n"
            f"🔍 Piyasalar: {' · '.join(markets)}\n"
            f"⏰ Tarama: Her {config['scan_interval_h']} saat\n"
            f"⭐ Top sinyal: {config['top_signals']}\n"
            f"📊 Min skor: {config['min_score']}/100\n"
            f"{'📄 PAPER MODE' if config['paper_mode'] else '💰 CANLI MOD'}"
        )
        self.send(msg)

    def send_scan_report(self, report, top_signals):
        if not top_signals:
            self.send(f"🔍 Tarama #{report['scan_no']} tamamlandı — Güçlü sinyal bulunamadı.")
            return

        market_emoji = {'crypto':'₿','us_stock':'🇺🇸','bist':'🇹🇷','forex':'💱'}
        msg = f"🔍 <b>Tarama #{report['scan_no']}</b> — {report['timestamp']}\n{'─'*30}\n"

        for m, c in report['stats'].items():
            if m == 'total': continue
            msg += f"{market_emoji.get(m,'📊')} {m.upper()}: {c}\n"

        msg += f"\n<b>⭐ Top {len(top_signals)} Sinyal:</b>\n"

        for i, sig in enumerate(top_signals, 1):
            me = market_emoji.get(sig['market'], '📊')
            sv = sig.get('small_scale', {}) or {}
            sv_name = sv.get('sv', {}).get('r', '—') if sv else '—'
            poz = sv.get('sv', {}).get('poz', 0) if sv else 0
            msg += (
                f"\n{i}. {me} <b>{sig['symbol']}</b>\n"
                f"   💲 ${sig['price']:,.4g} ({sig['chg_pct']:+.1f}%)\n"
                f"   📐 Skor: <b>{sig['score']}/100</b> · {sig['action']}\n"
                f"   📊 {sv_name} → %{poz} pozisyon\n"
            )

        self.send(msg)

    def send_trade_summary(self, positions):
        if not positions:
            return
        msg = f"💼 <b>Açık Pozisyonlar ({len(positions)})</b>\n"
        for sym, pos in positions.items():
            msg += f"  • {sym}: %{pos['target_poz']} @ ${pos['entry_price']:,.4g}\n"
        self.send(msg)


# ─────────────────────────────────────────────────────────────────────────────
"""
schedule_manager.py — Zamanlama Yöneticisi
Kripto: 7/24 · Hisse: sadece borsa saatleri
"""
from datetime import datetime, timezone, timedelta

class ScheduleManager:
    def __init__(self, config):
        self.interval_h  = config.get('scan_interval_h', 4)
        self.scan_crypto = config.get('scan_crypto', True)
        self.scan_stocks = config.get('scan_us_stocks', True) or config.get('scan_bist', True)
        self._last_scan  = None
        self._log        = logging.getLogger('Scheduler')

    def should_scan(self, now):
        """Şu an tarama yapılmalı mı?"""
        if self._last_scan is None:
            return True  # İlk çalışmada hemen tara

        elapsed = (now - self._last_scan).total_seconds()
        if elapsed < self.interval_h * 3600:
            return False

        return True

    def mark_scanned(self, ts):
        self._last_scan = ts

    def seconds_to_next(self, now):
        if self._last_scan is None:
            return 0
        elapsed  = (now - self._last_scan).total_seconds()
        interval = self.interval_h * 3600
        return max(0, interval - elapsed)

    def next_scan_str(self, now):
        secs = self.seconds_to_next(now)
        nxt  = now + timedelta(seconds=secs)
        return nxt.strftime('%H:%M UTC')

    def _is_market_hours(self, now, market):
        """Borsa saati kontrolü (UTC)"""
        hour = now.hour
        weekday = now.weekday()  # 0=Pazartesi
        if weekday >= 5:
            return False  # Hafta sonu
        if market == 'us':
            return 13 <= hour < 21  # NYSE: 09:30-16:00 EST = 13:30-20:00 UTC
        if market == 'bist':
            return 7 <= hour < 15  # BIST: 10:00-18:00 TRT = 07:00-15:00 UTC
        return True  # Kripto/forex her zaman
