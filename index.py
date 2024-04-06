# -*- coding: utf-8 -*-

import os
import sys


# -----------------------------------------------------------------------------

import ccxt  # noqa: E402
import pandas as pd
import datetime as dt
import os

# -----------------------------------------------------------------------------

def format_data(data):
    df = pd.DataFrame(data)
    if (len(df.index) == 0):
        return None
    df = df.iloc[:, 0:6]
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df.open = df.open.astype("float")
    df.high = df.high.astype("float")
    df.low = df.low.astype("float")
    df.close = df.close.astype("float")
    df.volume = df.volume.astype("float")
    df.index = [dt.datetime.fromtimestamp(x / 1000.0) for x in df.datetime]
    return df

def get_binance_bars(symbol, interval, startTime, endTime):
    url = "https://api.binance.com/api/v3/klines"
    startTime = str(int(startTime.timestamp() * 1000))
    endTime = str(int(endTime.timestamp() * 1000))
    limit = '50'
    req_params = {"symbol" : symbol, 'interval' : interval, 'startTime' : startTime, 'endTime' : endTime, 'limit' : limit}
    exchange = ccxt.binance({
        'proxies': {
            'http': '127.0.0.1:10792',
            'https': '127.0.0.1:10792'
        }
    })

    since = exchange.milliseconds() - 86400000 * 300
    allLines = []
    while True:
        print(since)
        tmpLines = exchange.fetch_ohlcv(symbol, interval, since, 100)
        print(tmpLines)
        # print(tmpLines[len(tmpLines) - 1][0])
        # break

        if(len(tmpLines) > 0):
            since = tmpLines[len(tmpLines) - 1][0] + 100
            allLines.append(format_data(tmpLines))
        else:
            break

    dataframe=pd.concat(allLines)
    dataframe.to_json('demo2.json')
    return

    df = pd.DataFrame(exchange.fetch_ohlcv(symbol, interval))
    # df = pd.DataFrame(json.loads(requests.get(url, params = req_params).text))
    if (len(df.index) == 0):
        return None
    df = df.iloc[:, 0:6]
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df.open = df.open.astype("float")
    df.high = df.high.astype("float")
    df.low = df.low.astype("float")
    df.close = df.close.astype("float")
    df.volume = df.volume.astype("float")
    df.index = [dt.datetime.fromtimestamp(x / 1000.0) for x in df.datetime]
    df.to_json('demo.json')
    return df

last_datetime = dt.datetime(2021,6,1)
new_df = get_binance_bars('ETHUSDT', '4h', last_datetime, dt.datetime(2022,7,15)) # 获取k线数据
print(new_df)