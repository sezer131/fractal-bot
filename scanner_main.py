#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   FRAKTAL SCANNER — EVRENSEl PİYASA TARAMA SİSTEMİ                         ║
║   Kripto · ABD Hisse · BIST · Forex                                         ║
║   Her 4 saatte otomatik tara → Sinyal + Otomatik İşlem                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

KURULUM:
  pip install -r requirements.txt

ÇALIŞTIRMA:
  python3 scanner_main.py
"""

import os, sys, time, json, logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from market_scanner   import MarketScanner
from signal_engine    import SignalEngine
from auto_trader      import AutoTrader
from scanner_notifier import ScannerNotifier
from schedule_manager import ScheduleManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(levelname)s │ %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scanner.log', encoding='utf-8')
    ]
)
log = logging.getLogger('Scanner')
load_dotenv()

# ── CONFIG ──
CONFIG = {
    # BORSA API
    'bybit_key'      : os.getenv('BYBIT_KEY', ''),
    'bybit_secret'   : os.getenv('BYBIT_SECRET', ''),
    'binance_key'    : os.getenv('BINANCE_KEY', ''),
    'binance_secret' : os.getenv('BINANCE_SECRET', ''),

    # ANTHROPIC
    'anthropic_key'  : os.getenv('ANTHROPIC_API_KEY', ''),

    # BİLDİRİM
    'telegram_token' : os.getenv('TELEGRAM_TOKEN', ''),
    'telegram_chat'  : os.getenv('TELEGRAM_CHAT', ''),
    'email_to'       : os.getenv('EMAIL_TO', ''),

    # TARAMA
    'paper_mode'     : os.getenv('PAPER_MODE', 'true').lower() == 'true',
    'scan_interval_h': int(os.getenv('SCAN_INTERVAL_H', '4')),
    'top_signals'    : int(os.getenv('TOP_SIGNALS', '5')),
    'min_score'      : float(os.getenv('MIN_SCORE', '70')),  # min fraktal skoru

    # PİYASA SEÇİMİ
    'scan_crypto'    : os.getenv('SCAN_CRYPTO',  'true').lower() == 'true',
    'scan_us_stocks' : os.getenv('SCAN_US',      'true').lower() == 'true',
    'scan_bist'      : os.getenv('SCAN_BIST',    'true').lower() == 'true',
    'scan_forex'     : os.getenv('SCAN_FOREX',   'true').lower() == 'true',

    # OTOM. İŞLEM
    'auto_trade'     : os.getenv('AUTO_TRADE',   'false').lower() == 'true',
    'capital_per_signal': float(os.getenv('CAPITAL_PER_SIGNAL', '200')),
    'max_open_trades': int(os.getenv('MAX_OPEN_TRADES', '5')),
    'dd_limit_pct'   : float(os.getenv('DD_LIMIT_PCT', '5')),
}

def main():
    log.info("=" * 70)
    log.info("  FRAKTAL SCANNER BAŞLIYOR")
    log.info(f"  Tarama Aralığı : Her {CONFIG['scan_interval_h']} saat")
    log.info(f"  Piyasalar      : "
             f"{'Kripto ' if CONFIG['scan_crypto'] else ''}"
             f"{'ABD ' if CONFIG['scan_us_stocks'] else ''}"
             f"{'BIST ' if CONFIG['scan_bist'] else ''}"
             f"{'Forex ' if CONFIG['scan_forex'] else ''}")
    log.info(f"  Mod            : {'📄 PAPER' if CONFIG['paper_mode'] else '💰 CANLI'}")
    log.info(f"  Otomatik İşlem : {'✅ AÇIK' if CONFIG['auto_trade'] else '❌ KAPALI'}")
    log.info("=" * 70)

    scanner  = MarketScanner(CONFIG)
    engine   = SignalEngine(CONFIG)
    trader   = AutoTrader(CONFIG)
    notifier = ScannerNotifier(CONFIG)
    schedule = ScheduleManager(CONFIG)

    notifier.send_startup(CONFIG)

    scan_count = 0
    while True:
        try:
            now = datetime.now(timezone.utc)

            if not schedule.should_scan(now):
                wait = schedule.seconds_to_next(now)
                log.info(f"⏰ Sonraki tarama: {schedule.next_scan_str(now)} ({wait//60:.0f} dk)")
                time.sleep(min(wait, 300))
                continue

            scan_count += 1
            log.info(f"\n{'═'*70}")
            log.info(f"  🔍 TARAMA #{scan_count} — {now.strftime('%Y-%m-%d %H:%M UTC')}")
            log.info(f"{'═'*70}")

            # ── 1. TÜM PİYASALARı TARA ──
            all_assets = scanner.scan_all()
            log.info(f"📊 Toplam taranan: {all_assets['total']} varlık")

            # ── 2. FRAKTAL SKORU HESAPLA ──
            scored = engine.score_all(all_assets['data'])
            log.info(f"📐 Fraktal skoru hesaplandı: {len(scored)} varlık")

            # ── 3. EN İYİ SİNYALLERİ SEÇ ──
            top = engine.get_top_signals(scored, CONFIG['top_signals'], CONFIG['min_score'])
            log.info(f"⭐ Min skor {CONFIG['min_score']}+ olan: {len(top)} sinyal")

            # ── 4. RAPOR OLUŞTUR ──
            report = engine.build_report(top, all_assets['stats'], scan_count, now)
            log.info("\n" + report['text_summary'])

            # ── 5. BİLDİRİM GÖNDER ──
            notifier.send_scan_report(report, top)

            # ── 6. OTOMATIK İŞLEM ──
            if CONFIG['auto_trade'] and top:
                trades_done = trader.execute_signals(top)
                log.info(f"🤖 Otomatik işlem: {trades_done} emir")
                if trades_done:
                    notifier.send_trade_summary(trader.get_open_positions())

            schedule.mark_scanned(now)
            log.info(f"✅ Tarama #{scan_count} tamamlandı")

        except KeyboardInterrupt:
            log.info("\n🛑 Scanner durduruldu.")
            notifier.send("🛑 Fraktal Scanner durduruldu.")
            break
        except Exception as e:
            log.error(f"❌ Hata: {e}", exc_info=True)
            notifier.send(f"❌ Scanner hatası: {str(e)[:150]}")
            time.sleep(60)

if __name__ == '__main__':
    main()
