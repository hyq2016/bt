# K线数据获取
#数字货币回测
# 从Binance币安在线api下载k线，进行回测
import requests
import json
import pandas as pd
import datetime as dt
import os
import ccxt

from datetime import datetime,timedelta
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['SimHei']
plt.rcParams['axes.unicode_minus']=False
plt.rcParams['figure.figsize']=[10, 8]
plt.rcParams['figure.dpi']=200
plt.rcParams['figure.facecolor']='w'
plt.rcParams['figure.edgecolor']='k'


def get_binance_bars(symbol, interval, startTime, endTime):
    filename = 'demo2.json'
    if os.path.exists(filename):
        return pd.read_json(filename)
    url = "https://api.binance.com/api/v3/klines"
    startTime = str(int(startTime.timestamp() * 1000))
    endTime = str(int(endTime.timestamp() * 1000))
    limit = '50'
    exchange = ccxt.binance({
        'proxies': {
            'http': '127.0.0.1:10792',
            'https': '127.0.0.1:10792'
        }
    })
    df = pd.DataFrame(exchange.fetch_ohlcv(symbol, interval))
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
df_list = []
# 数据起点时间
last_datetime = dt.datetime(2021,6,1)
# while True:
#     new_df = get_binance_bars('ETHUSDT', '4h', last_datetime, dt.datetime(2022,7,15)) # 获取k线数据
#     if new_df is None:
#         break
#     df_list.append(new_df)
#     last_datetime = max(new_df.index) + dt.timedelta(0, 5)

new_df = get_binance_bars('ETHUSDT', '4h', last_datetime, dt.datetime(2022,7,15)) # 获取k线数据
df_list.append(new_df)
dataframe=pd.concat(df_list)
dataframe['openinterest']=0
dataframe=dataframe[['open','high','low','close','volume','openinterest']]
# print(dataframe.shape)
# print(dataframe.tail())
# dataframe.head()


class three_moving_average(bt.Strategy):
    params = dict(
        short_period=5,
        median_period=20,
        long_period=60,
        printlog=False)
    def log(self, txt, dt=None,doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()},{txt}')
    def __init__(self):
        self.order = None
        self.close = self.datas[0].close
        self.allbar = self.close.buflen()
        self.s_ma = bt.ind.SMA(period=int(self.p.short_period))
        self.m_ma = bt.ind.SMA(period=int(self.p.median_period))
        self.l_ma = bt.ind.SMA(period=int(self.p.long_period))
        # 捕获做多信号
        # 短期均线在中期均线上方，且中期均取也在长期均线上方，三线多头排列，取值为1；反之，取值为0
        self.signal1 = bt.And(self.m_ma>self.l_ma, self.s_ma>self.m_ma)
        # 做多信号，求上面 self.signal1 的环比增量，可以判断得到第一次同时满足上述条件的时间，第一次满足条件为1，其余条件为0
        self.long_signal = bt.If((self.signal1-self.signal1(-1))>0, 1, 0)
        # 做多平仓信号，短期均线下穿长期均线时，取值为1；反之取值为0
        self.close_long_signal = bt.ind.CrossDown(self.s_ma, self.m_ma)
        # 捕获做空信号和平仓信号，与做多相反
        self.signal2 = bt.And(self.m_ma<self.l_ma, self.s_ma<self.m_ma)
        self.short_signal = bt.If((self.signal2-self.signal2(-1))>0, 1, 0)
        self.close_short_signal = bt.ind.CrossUp(self.s_ma, self.m_ma)

    def next(self):
        #         self.log(self.sell_signal[0],doprint=True)
        #         self.log(type(self.position.size),doprint=True)
        # 如果还有订单在执行中，就不做新的仓位调整
        #         if self.order:
        #             return
        # 如果当前持有多单
        if self.position.size>0:
            #             self.log(self.position.size,doprint=True)
            # 平仓设置,出现平仓信号进行平仓
            if self.close_long_signal ==1 or (self.allbar - 1) <= len(self):
                self.order = self.sell(size=abs(self.position.size))
        # 如果当前持有空单
        elif self.position.size < 0 :
            # 平仓设置，出现平仓信号进行平仓
            if self.close_short_signal ==1 or (self.allbar - 1) <= len(self):
                self.order = self.buy(size=abs(self.position.size))
        else: # 如果没有持仓，等待入场时机
            #入场: 出现做多信号，做多，开四分之一仓位
            if self.long_signal ==1 :
                self.buy_unit = int(self.broker.getvalue()/self.close[0]/4)
                self.order = self.buy(size=self.buy_unit)
            #入场: 出现做空信号，做空，开四分之一仓位
            elif self.short_signal==1:
                self.sell_unit = int(self.broker.getvalue()/self.close[0]/4)
                self.order = self.sell(size=self.sell_unit)

    # 打印订单日志
    def notify_order(self, order):
        order_status = ['Created','Submitted','Accepted','Partial',
                        'Completed','Canceled','Expired','Margin','Rejected']
        # 未被处理的订单
        if order.status in [order.Submitted, order.Accepted]:
            self.log('ref:%.0f, name: %s, Order: %s'% (order.ref,
                                                       order.data._name,
                                                       order_status[order.status]))
            return
        # 已经处理的订单
        if order.status in [order.Partial, order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, status: %s, ref:%.0f, name: %s, Size: %.2f, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order_status[order.status], # 订单状态
                     order.ref, # 订单编号
                     order.data._name, # 股票名称
                     order.executed.size, # 成交量
                     order.executed.price, # 成交价
                     order.executed.value, # 成交额
                     order.executed.comm)) # 佣金
            else: # Sell
                self.log('SELL EXECUTED, status: %s, ref:%.0f, name: %s, Size: %.2f, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order_status[order.status],
                          order.ref,
                          order.data._name,
                          order.executed.size,
                          order.executed.price,
                          order.executed.value,
                          order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected, order.Expired]:
            # 订单未完成
            self.log('ref:%.0f, name: %s, status: %s'% (
                order.ref, order.data._name, order_status[order.status]))

        self.order = None
    def stop(self):
        self.log(f'(组合线：{self.p.short_period},{self.p.median_period},{self.p.long_period}); 期末总资金: {self.broker.getvalue():.2f}', doprint=False)


#编写回测主函数
def main(short_period,median_period,long_period,para_opt=True,startcash=100000,com=0.0005,printlog=False):
    if para_opt==True:
        cerebro = bt.Cerebro()
        cerebro.addstrategy(three_moving_average,short_period=short_period,
                            median_period=median_period,long_period=long_period,printlog=printlog)
        data = bt.feeds.PandasData(dataname=dataframe)
        cerebro.adddata(data)
        #broker设置资金、手续费
        cerebro.broker.setcash(startcash)
        cerebro.broker.setcommission(commission=com)
        cerebro.run(maxcpus=2)
        value = cerebro.broker.getvalue()
        return value
    else:
        cerebro = bt.Cerebro()
        cerebro.addstrategy(three_moving_average,short_period=short_period,
                            median_period=median_period,long_period=long_period,printlog=printlog)
        data = bt.feeds.PandasData(dataname=dataframe)
        cerebro.adddata(data)
        #broker设置资金、手续费
        cerebro.broker.setcash(startcash)
        cerebro.broker.setcommission(commission=com)
        #设置指标观察
        cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
        print('期初总资金: %.2f' % cerebro.broker.getvalue())
        results=cerebro.run(maxcpus=2)
        print('期末总资金: %.2f' % cerebro.broker.getvalue())
        cerebro.plot(iplot=False)
#         result = results[0]
#         pyfolio = result.analyzers.pyfolio # 注意：后面不要调用 .get_analysis() 方法
#         # 或者是 result[0].analyzers.getbyname('pyfolio')
#         returns, positions, transactions, gross_lev = pyfolio.get_pf_items()
#         pf.create_full_tear_sheet(returns)





main(short_period=7,median_period=24,long_period=99,
     para_opt=False,com=0.0005,printlog=False)
