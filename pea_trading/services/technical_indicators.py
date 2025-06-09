# pea_trading/services/technical_indicators.py

def compute_ichimoku(data, period1=9, period2=26, period3=52):
    """
    data: liste de dictionnaires [{'date': ..., 'high_price': ..., 'low_price': ..., 'close_price': ...}]
    """
    high_prices = [d['high_price'] for d in data]
    low_prices = [d['low_price'] for d in data]
    close_prices = [d['close_price'] for d in data]
    
    def rolling_avg(highs, lows, window):
        return [(max(highs[i-window+1:i+1]) + min(lows[i-window+1:i+1])) / 2 if i >= window-1 else None
                for i in range(len(highs))]

    tenkan = rolling_avg(high_prices, low_prices, period1)
    kijun = rolling_avg(high_prices, low_prices, period2)
    senkou_a = [(tenkan[i] + kijun[i]) / 2 if tenkan[i] and kijun[i] else None for i in range(len(tenkan))]
    senkou_b = rolling_avg(high_prices, low_prices, period3)

    chikou = [close_prices[i+period2] if i + period2 < len(close_prices) else None for i in range(len(close_prices))]

    return {
        'tenkan_sen': tenkan,
        'kijun_sen': kijun,
        'senkou_span_a': senkou_a,
        'senkou_span_b': senkou_b,
        'chikou_span': chikou
    }
