"""
signal_engine.py — Fraktal Sayı Sistemi Sinyal Motoru
Tüm varlıklara 2.6·3.0·3.3·4.2·4.6·5.7·6.0·7.7·8.4·9.2·10.6 uygula
"""
import math, logging
from datetime import datetime
log = logging.getLogger('SignalEngine')

SISTEM = [
    {'d':2.6,  'r':'Sistem Giriş',   'poz':15,  'guven':60, 'yon': 1},
    {'d':3.0,  'r':'Alt Destek',     'poz':25,  'guven':65, 'yon': 1},
    {'d':3.3,  'r':'Pivot',          'poz':35,  'guven':70, 'yon': 1},
    {'d':4.2,  'r':'Basamak',        'poz':50,  'guven':75, 'yon': 1},
    {'d':4.6,  'r':'Ara Onay 1',     'poz':60,  'guven':78, 'yon': 1},
    {'d':5.7,  'r':'Kritik Eşik',    'poz':75,  'guven':80, 'yon': 1},
    {'d':6.0,  'r':'Yeni Başlangıç', 'poz':85,  'guven':82, 'yon': 1},
    {'d':7.7,  'r':'Ara Onay 2',     'poz':90,  'guven':85, 'yon': 1},
    {'d':8.4,  'r':'Tam Onay',       'poz':95,  'guven':88, 'yon': 1},
    {'d':9.2,  'r':'Direnç',         'poz':50,  'guven':70, 'yon':-1},
    {'d':10.6, 'r':'Bant Stop',      'poz':0,   'guven':90, 'yon':-1},
]

class SignalEngine:
    def __init__(self, config):
        self.config = config

    # ── ÖLÇEK ──
    def _scale(self, price):
        if price < 0.001: return 0.0001
        if price < 0.01:  return 0.001
        if price < 0.1:   return 0.01
        if price < 1:     return 0.1
        if price < 10:    return 1
        if price < 100:   return 10
        if price < 1000:  return 100
        if price < 10000: return 1000
        if price < 100000:return 10000
        return 100000

    def _large_scale(self, price):
        return self._scale(price) * 10

    # ── BANT ──
    def _band(self, price, scale):
        bw  = 10.6 * scale
        idx = math.floor(price / bw)
        return {'baz': idx*bw, 'bitis': (idx+1)*bw, 'idx': idx, 'bw': bw}

    def _seviyeler(self, baz, scale):
        return [{'fiyat': baz + s['d']*scale, **s} for s in SISTEM]

    def _aktif(self, price, sevs):
        a = -1
        for i in range(len(sevs)-1, -1, -1):
            if price >= sevs[i]['fiyat']:
                a = i; break
        return a

    # ── FRAKTAL SKORU ──
    def _fractal_score(self, asset):
        """
        Skor 0-100 arasında:
        - Seviye gücü         (0-35 puan)
        - Bant içi konum      (0-20 puan)
        - Yakın seviye mesafesi (0-20 puan)
        - Hacim               (0-15 puan)
        - Fiyat değişimi      (0-10 puan)
        """
        price  = asset['price']
        chg    = asset['chg_pct']
        vol    = asset['volume']
        high   = asset['high_24h']
        low    = asset['low_24h']

        score   = 0
        signals = []
        action  = 'BEKLE'
        best_s  = None
        best_ls = None

        for get_scale in [self._scale, self._large_scale]:
            sc   = get_scale(price)
            band = self._band(price, sc)
            sevs = self._seviyeler(band['baz'], sc)
            ak   = self._aktif(price, sevs)

            if ak < 0: continue
            sv = sevs[ak]

            # Bant içi ilerleme
            progress = (price - band['baz']) / band['bw'] * 100

            # Seviye gücü (hangi seviyede olduğumuza göre)
            sev_score = sv['guven'] * 0.35  # max 31 puan

            # Bant içi konum (optimal: %40-80 arası)
            if 40 <= progress <= 80:
                pos_score = 20
            elif 20 <= progress <= 90:
                pos_score = 12
            else:
                pos_score = 5

            # Sonraki seviyeye mesafe (yakınsa daha iyi sinyal)
            if ak < len(sevs)-1:
                next_sv = sevs[ak+1]
                dist_pct = (next_sv['fiyat'] - price) / price * 100
                if dist_pct < 1:   prox_score = 20
                elif dist_pct < 3: prox_score = 15
                elif dist_pct < 5: prox_score = 10
                else:              prox_score = 5
            else:
                prox_score = 0

            total_s = sev_score + pos_score + prox_score

            # Yön
            if sv['yon'] == 1 and get_scale == self._scale:
                best_s = {'scale': 'küçük', 'sc': sc, 'sv': sv, 'band': band, 'progress': progress, 'sub_score': total_s}
            elif sv['yon'] == 1 and get_scale == self._large_scale:
                best_ls = {'scale': 'büyük', 'sc': sc, 'sv': sv, 'band': band, 'progress': progress, 'sub_score': total_s}

            score += total_s

        # Hacim skoru (normalize 0-15)
        if vol > 1_000_000_000:  vol_score = 15
        elif vol > 100_000_000:  vol_score = 12
        elif vol > 10_000_000:   vol_score = 8
        elif vol > 1_000_000:    vol_score = 5
        else:                    vol_score = 0
        score += vol_score

        # Fiyat değişimi skoru (pozitif değişim tercih edilir)
        if 1 <= chg <= 5:    chg_score = 10
        elif 5 < chg <= 10:  chg_score = 7
        elif 0 <= chg < 1:   chg_score = 5
        elif chg > 10:       chg_score = 3  # aşırı yükselmiş, dikkat
        else:                 chg_score = 2  # negatif
        score += chg_score

        # Normalize 0-100
        score = min(score / 1.2, 100)

        # Aksiyon belirle
        if best_s and score >= 70:
            sv = best_s['sv']
            if sv['d'] >= 8.4:      action = '🟢 GÜÇLÜ AL'
            elif sv['d'] >= 5.7:    action = '🟡 AL'
            elif sv['d'] >= 2.6:    action = '🟠 KÜÇÜK AL'
        elif best_s and best_s['sv']['yon'] == -1:
            action = '🔴 SAT/KISALT'

        return {
            'score'   : round(score, 1),
            'action'  : action,
            'small_scale': best_s,
            'large_scale': best_ls,
            'vol_score'  : vol_score,
            'chg_score'  : chg_score,
        }

    # ── TÜM VARLIKLAR ──
    def score_all(self, assets):
        scored = []
        for asset in assets:
            try:
                result = self._fractal_score(asset)
                scored.append({**asset, **result})
            except Exception as e:
                pass  # hatalıyı atla
        return scored

    # ── EN İYİ SİNYALLER ──
    def get_top_signals(self, scored, top_n=5, min_score=70):
        filtered = [s for s in scored if s['score'] >= min_score]
        filtered.sort(key=lambda x: x['score'], reverse=True)

        # Market başına en fazla top_n//2 sinyal
        market_count = {}
        result = []
        for s in filtered:
            m = s['market']
            if market_count.get(m, 0) < max(1, top_n // 4):
                result.append(s)
                market_count[m] = market_count.get(m, 0) + 1
            if len(result) >= top_n:
                break

        # Kalan slotları doldur
        if len(result) < top_n:
            for s in filtered:
                if s not in result:
                    result.append(s)
                if len(result) >= top_n:
                    break

        return result[:top_n]

    # ── RAPOR ──
    def build_report(self, top_signals, stats, scan_no, ts):
        now_str = ts.strftime('%Y-%m-%d %H:%M UTC')
        market_emoji = {'crypto':'₿','us_stock':'🇺🇸','bist':'🇹🇷','forex':'💱'}

        # Text raporu (Telegram için)
        lines = [
            f"🔍 FRAKTAL SCANNER #{scan_no} — {now_str}",
            f"{'─'*38}",
        ]

        # Piyasa özeti
        for market, count in stats.items():
            if market == 'total': continue
            lines.append(f"{market_emoji.get(market,'📊')} {market.upper()}: {count} tarındı")

        lines.append(f"\n⭐ TOP {len(top_signals)} SİNYAL:")
        lines.append(f"{'─'*38}")

        for i, sig in enumerate(top_signals, 1):
            m   = market_emoji.get(sig['market'], '📊')
            sv  = sig.get('small_scale', {}) or {}
            sv_name = sv.get('sv', {}).get('r', '—') if sv else '—'
            sv_d    = sv.get('sv', {}).get('d', '—') if sv else '—'
            lines += [
                f"\n{i}. {m} {sig['symbol']}",
                f"   💲 ${sig['price']:,.4g}  ({sig['chg_pct']:+.1f}%)",
                f"   📐 Skor: {sig['score']}/100  {sig['action']}",
                f"   📊 Seviye: {sv_name} (+{sv_d})",
                f"   💰 Önerilen Poz: %{sv.get('sv',{}).get('poz',0) if sv else 0}",
            ]

        text = '\n'.join(lines)

        # Detaylı dict rapor
        return {
            'text_summary': text,
            'scan_no'     : scan_no,
            'timestamp'   : now_str,
            'stats'       : stats,
            'top_signals' : top_signals,
            'signal_count': len(top_signals),
        }
