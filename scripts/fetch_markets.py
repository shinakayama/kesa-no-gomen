"""Fetch market quotes from the Yahoo Finance chart API and print them as `quotes` entries.

Usage: python3 scripts/fetch_markets.py > /tmp/quotes.json
Covers 日経平均・NYダウ・ドル円・米国債10年・ビットコイン. 日本国債10年、フラット35、変動金利、
API価格は Yahoo に無いので別途調べて quotes に追加する。
"""
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

# symbol, 名前, 単位, 値の小数桁, 前日比の形式
SYMBOLS = [
    ("^N225", "日経平均株価", "円", 2, "abs"),
    ("^DJI", "NYダウ", "ドル", 2, "abs"),
    ("JPY=X", "円相場", "円", 2, "abs"),
    ("^TNX", "米国債10年", "%", 3, "abs"),
    ("BTC-USD", "ビットコイン", "ドル", 0, "pct"),
]


def fetch(symbol: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1d&range=10d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["chart"]["result"][0]


def quote(symbol, name, unit, digits, diff_kind):
    res = fetch(symbol)
    meta = res["meta"]
    offset = timedelta(seconds=meta["gmtoffset"])
    local_date = lambda ts: (datetime.fromtimestamp(ts, timezone.utc) + offset).date()

    price, price_ts = meta["regularMarketPrice"], meta["regularMarketTime"]
    today = local_date(price_ts)
    # chartPreviousClose is the close before the whole range, not yesterday's; derive it from daily bars.
    closes = [(local_date(t), c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"])
              if c is not None]
    prev = [c for d, c in closes if d < today][-1]

    closed = price_ts >= meta["currentTradingPeriod"]["regular"]["end"]
    when = datetime.fromtimestamp(price_ts, JST)
    note = f"（{today.day}日終値）" if closed and symbol not in ("JPY=X", "BTC-USD") \
        else f"（{when.day}日{when.hour}時・日本時間）"

    diff = price - prev
    if diff_kind == "pct":
        diff_text = f"{diff / prev * 100:+.1f}%"
    else:
        diff_text = f"{diff:+,.{digits}f}"
    diff_text = diff_text.replace("+", "＋").replace("-", "−")
    return {
        "name": name,
        "note": note,
        "value": f"{price:,.{digits}f}",
        "unit": unit,
        "diff": diff_text,
        "dir": "up" if diff > 0 else "dn" if diff < 0 else "flat",
        "source": f"Yahoo Finance {symbol}",
    }


def main():
    out = []
    for args in SYMBOLS:
        try:
            out.append(quote(*args))
        except Exception as e:  # one failed symbol must not block the others
            print(f"{args[0]}: {e}", file=sys.stderr)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
