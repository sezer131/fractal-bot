"""
market_scanner.py — Tüm Piyasaları Tara
Kripto · ABD Hisse · BIST · Forex
"""
import json, logging, time
import urllib.request, urllib.parse
log = logging.getLogger('MarketScanner')

# ── KRİPTO: Top 200 USDT çifti (Bybit) ──
CRYPTO_SYMBOLS_FALLBACK = [
    'BTC/USDT','ETH/USDT','BNB/USDT','SOL/USDT','XRP/USDT',
    'ADA/USDT','AVAX/USDT','DOT/USDT','MATIC/USDT','LINK/USDT',
    'ATOM/USDT','UNI/USDT','LTC/USDT','BCH/USDT','NEAR/USDT',
    'ICP/USDT','FIL/USDT','ARB/USDT','OP/USDT','APT/USDT',
    'DOGE/USDT','SHIB/USDT','PEPE/USDT','WIF/USDT','BONK/USDT',
    'SUI/USDT','SEI/USDT','TIA/USDT','INJ/USDT','RNDR/USDT',
]

# ── ABD HİSSE: S&P 500 + NASDAQ büyükleri ──
US_STOCKS = [
    'AAPL','MSFT','NVDA','GOOGL','AMZN','META','TSLA','BRK-B',
    'JPM','V','JNJ','UNH','XOM','PG','MA','HD','CVX','MRK',
    'ABBV','PEP','KO','AVGO','COST','WMT','BAC','PFE','DIS',
    'CSCO','INTC','CRM','NFLX','AMD','PYPL','ADBE','QCOM',
    'ORCL','T','VZ','BABA','TSM','SPOT','UBER','LYFT','SNAP',
    'PLTR','COIN','MSTR','HOOD','SOFI','NIO','RIVN','LCID',
]

# ── BIST: BIST 100 hisseleri ──
BIST_STOCKS = [
    'THYAO','GARAN','AKBNK','EREGL','KCHOL','SAHOL','SISE','TUPRS',
    'ASELS','BIMAS','TCELL','TOASO','FROTO','PETKM','YKBNK','TAVHL',
    'ARCLK','ENKAI','EKGYO','VAKBN','HALKB','ISCTR','DOHOL','KOZAL',
    'MGROS','TKFEN','LOGO','PGSUS','ULKER','SODA','ALARK','KRDMD',
    'KONTR','KOZAA','TTKOM','CIMSA','AKCNS','OYAKC','BOLUC','TSKB',
    'ISGYO','SELEC','BRISA','VESBE','KARSN','NETAS','SAFGK','SKBNK',
]

# ── FOREX: Ana çiftler ──
FOREX_PAIRS = [
    'EUR/USD','GBP/USD','USD/JPY','USD/CHF','AUD/USD',
    'USD/CAD','NZD/USD','EUR/GBP','EUR/JPY','GBP/JPY',
    'USD/TRY','EUR/TRY','XAU/USD','XAG/USD','WTI/USD',
]


class MarketScanner:
    def __init__(self, config):
        self.config = config
        self._cache = {}
        self._cache_ttl = 300  # 5 dk cache

    # ────────────────────────────────────────────────────────
    def scan_all(self):
        """Tüm piyasaları tara, normalize et, birleştir"""
        results = []
        stats = {}

        if self.config.get('scan_crypto'):
            crypto = self._scan_crypto()
            results.extend(crypto)
            stats['crypto'] = len(crypto)
            log.info(f"  ₿ Kripto: {len(crypto)} coin tarandı")

        if self.config.get('scan_us_stocks'):
            us = self._scan_us_stocks()
            results.extend(us)
            stats['us_stocks'] = len(us)
            log.info(f"  📈 ABD Hisse: {len(us)} hisse tarandı")

        if self.config.get('scan_bist'):
            bist = self._scan_bist()
            results.extend(bist)
            stats['bist'] = len(bist)
            log.info(f"  🇹🇷 BIST: {len(bist)} hisse tarandı")

        if self.config.get('scan_forex'):
            forex = self._scan_forex()
            results.extend(forex)
            stats['forex'] = len(forex)
            log.info(f"  💱 Forex: {len(forex)} çift tarandı")

        stats['total'] = len(results)
        return {'data': results, 'stats': stats, 'total': len(results)}

    # ── KRİPTO ──────────────────────────────────────────────
    def _scan_crypto(self):
        results = []
        try:
            # Bybit ticker API (ücretsiz, auth gerektirmez)
            url = 'https://api.bybit.com/v5/market/tickers?category=spot'
            data = self._fetch_json(url)
            tickers = data.get('result', {}).get('list', [])

            # Sadece USDT çiftleri, hacim > $1M
            usdt = [t for t in tickers
                    if t.get('symbol', '').endswith('USDT')
                    and float(t.get('turnover24h', 0)) > 1_000_000]

            # Hacme göre sırala, top 300
            usdt.sort(key=lambda x: float(x.get('turnover24h', 0)), reverse=True)
            usdt = usdt[:300]

            for t in usdt:
                sym   = t['symbol'].replace('USDT', '/USDT')
                price = float(t.get('lastPrice', 0))
                chg   = float(t.get('price24hPcnt', 0)) * 100
                vol   = float(t.get('turnover24h', 0))
                high  = float(t.get('highPrice24h', price))
                low   = float(t.get('lowPrice24h', price))
                if price <= 0: continue
                results.append(self._normalize(sym, price, chg, vol, high, low, 'crypto'))

        except Exception as e:
            log.warning(f"Bybit API hatası: {e} — fallback kullanılıyor")
            # Fallback: Binance
            results = self._scan_crypto_binance()

        return results

    def _scan_crypto_binance(self):
        results = []
        try:
            url  = 'https://api.binance.com/api/v3/ticker/24hr'
            data = self._fetch_json(url)
            usdt = [t for t in data
                    if t.get('symbol','').endswith('USDT')
                    and float(t.get('quoteVolume',0)) > 1_000_000]
            usdt.sort(key=lambda x: float(x.get('quoteVolume',0)), reverse=True)
            for t in usdt[:300]:
                sym   = t['symbol'].replace('USDT', '/USDT')
                price = float(t['lastPrice'])
                chg   = float(t['priceChangePercent'])
                vol   = float(t['quoteVolume'])
                high  = float(t['highPrice'])
                low   = float(t['lowPrice'])
                if price <= 0: continue
                results.append(self._normalize(sym, price, chg, vol, high, low, 'crypto'))
        except Exception as e:
            log.error(f"Binance de hata: {e}")
        return results

    # ── ABD HİSSE ────────────────────────────────────────────
    def _scan_us_stocks(self):
        results = []
        # Yahoo Finance v8 API (ücretsiz)
        chunk_size = 10
        for i in range(0, len(US_STOCKS), chunk_size):
            chunk = US_STOCKS[i:i+chunk_size]
            syms  = ','.join(chunk)
            try:
                url  = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={syms}'
                data = self._fetch_json(url, headers={'User-Agent': 'Mozilla/5.0'})
                quotes = data.get('quoteResponse', {}).get('result', [])
                for q in quotes:
                    price = q.get('regularMarketPrice', 0)
                    if not price: continue
                    chg   = q.get('regularMarketChangePercent', 0)
                    vol   = q.get('regularMarketVolume', 0) * price
                    high  = q.get('regularMarketDayHigh', price)
                    low   = q.get('regularMarketDayLow', price)
                    sym   = q.get('symbol', '')
                    results.append(self._normalize(sym, price, chg, vol, high, low, 'us_stock'))
                time.sleep(0.3)
            except Exception as e:
                log.warning(f"Yahoo Finance hata ({chunk}): {e}")
        return results

    # ── BIST ─────────────────────────────────────────────────
    def _scan_bist(self):
        results = []
        # Yahoo Finance ile BIST (sembol + .IS eki)
        chunk_size = 10
        bist_yahoo = [f"{s}.IS" for s in BIST_STOCKS]
        for i in range(0, len(bist_yahoo), chunk_size):
            chunk = bist_yahoo[i:i+chunk_size]
            syms  = ','.join(chunk)
            try:
                url  = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={syms}'
                data = self._fetch_json(url, headers={'User-Agent': 'Mozilla/5.0'})
                quotes = data.get('quoteResponse', {}).get('result', [])
                for q in quotes:
                    price = q.get('regularMarketPrice', 0)
                    if not price: continue
                    sym   = q.get('symbol', '').replace('.IS', '')
                    chg   = q.get('regularMarketChangePercent', 0)
                    vol   = q.get('regularMarketVolume', 0) * price
                    high  = q.get('regularMarketDayHigh', price)
                    low   = q.get('regularMarketDayLow', price)
                    results.append(self._normalize(sym, price, chg, vol, high, low, 'bist'))
                time.sleep(0.3)
            except Exception as e:
                log.warning(f"BIST hata ({chunk}): {e}")
        return results

    # ── FOREX ────────────────────────────────────────────────
    def _scan_forex(self):
        results = []
        try:
            # ExchangeRate API (ücretsiz tier)
            url  = 'https://open.er-api.com/v6/latest/USD'
            data = self._fetch_json(url)
            rates = data.get('rates', {})

            forex_map = {
                'EUR/USD': 1/rates.get('EUR',1),
                'GBP/USD': 1/rates.get('GBP',1),
                'USD/JPY': rates.get('JPY',1),
                'USD/CHF': rates.get('CHF',1),
                'AUD/USD': 1/rates.get('AUD',1),
                'USD/CAD': rates.get('CAD',1),
                'NZD/USD': 1/rates.get('NZD',1),
                'USD/TRY': rates.get('TRY',1),
                'EUR/TRY': (1/rates.get('EUR',1)) * rates.get('TRY',1),
            }

            # Altın/Gümüş için ayrı API
            try:
                gold_url = 'https://api.metals.live/v1/spot'
                gold_data = self._fetch_json(gold_url)
                for item in gold_data:
                    if item.get('gold'):
                        forex_map['XAU/USD'] = float(item['gold'])
                    if item.get('silver'):
                        forex_map['XAG/USD'] = float(item['silver'])
            except:
                pass

            for pair, price in forex_map.items():
                if price <= 0: continue
                results.append(self._normalize(pair, price, 0, 1_000_000, price*1.01, price*0.99, 'forex'))

        except Exception as e:
            log.warning(f"Forex hata: {e}")
        return results

    # ── YARDIMCI ─────────────────────────────────────────────
    def _normalize(self, symbol, price, chg_pct, volume, high, low, market):
        """Tüm varlıkları aynı formata getir"""
        return {
            'symbol'  : symbol,
            'price'   : float(price),
            'chg_pct' : float(chg_pct),
            'volume'  : float(volume),
            'high_24h': float(high),
            'low_24h' : float(low),
            'market'  : market,
            'ts'      : time.time(),
        }

    def _fetch_json(self, url, headers=None):
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'FractalScanner/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
