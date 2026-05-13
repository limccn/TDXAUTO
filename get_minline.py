# -*- coding: utf-8 -*-
import time
import pandas as pd
from datetime import datetime, timedelta
from mootdx import quotes
import threading
import os
import sys


# 实时数据采集器：交易时段每分钟采集，非交易时段采集一次即退出
class get_data:
    output_dir: str = r'data'
    def __init__(self, code):
        self.symbol = code
        self.client = quotes.Quotes.factory(market='std')
        self.running = False
        self.minute_klines = []  # 分钟K线列表

        self.lock = threading.Lock()
        self.data_dir = 'data'
        os.makedirs(self.data_dir, exist_ok=True)

        # 用于计算分钟内增量
        self.last_cumulative_volume = 0
        self.last_cumulative_amount = 0

    def is_trading_time(self):
        """判断当前是否为交易时间"""
        now = datetime.now()
        # 周末不交易
        if now.weekday() > 4:
            return False

        current_time = now.time()
        morning_start = datetime.strptime('09:30:00', '%H:%M:%S').time()
        morning_end = datetime.strptime('11:30:00', '%H:%M:%S').time()
        afternoon_start = datetime.strptime('13:00:00', '%H:%M:%S').time()
        afternoon_end = datetime.strptime('15:00:00', '%H:%M:%S').time()

        in_morning = morning_start <= current_time <= morning_end
        in_afternoon = afternoon_start <= current_time <= afternoon_end
        return in_morning or in_afternoon

    def get_real_time_data(self):
        try:
            quote = self.client.quotes(symbol=self.symbol)
            if quote is not None and not quote.empty:
                price = float(quote.iloc[0]['price'])
                volume = int(quote.iloc[0]['vol'])  # 累计成交量
                amount = float(quote.iloc[0]['amount'])  # 累计成交额
                return {
                    'datetime': datetime.now(),
                    'price': price,
                    'volume': volume,
                    'amount': amount
                }
        except Exception as e:
            print(f"获取实时数据失败: {e}")
        return None

    def collect_data_and_save(self, data, is_trading):
        """通用处理函数：处理并保存数据"""
        if not data:
            return

        dt_str = data['datetime'].strftime('%Y-%m-%d %H:%M:%S')

        if is_trading:
            # 交易时段：计算增量，生成K线
            vol_delta = data['volume'] - self.last_cumulative_volume
            amt_delta = data['amount'] - self.last_cumulative_amount

            # 异常处理：如果累计值变小（结算），直接使用当前值
            if vol_delta < 0 or amt_delta < 0:
                vol_delta = data['volume']
                amt_delta = data['amount']

            # 更新累计值
            self.last_cumulative_volume = data['volume']
            self.last_cumulative_amount = data['amount']

            kline = {
                'datetime': data['datetime'],
                'open': data['price'],
                'high': data['price'],
                'low': data['price'],
                'close': data['price'],
                'volume': vol_delta,
                'amount': amt_delta
            }

            with self.lock:
                self.minute_klines.append(kline)

            print(f"[交易时段 {dt_str}] 价格: {data['price']:.2f}, 本分钟成交量: {vol_delta}")
        else:
            # 非交易时段：仅记录快照
            print(f"[非交易时段 {dt_str}] 快照采集 - 价格: {data['price']:.2f}, 累计成交量: {data['volume']}")

        # 每次采集后都保存，防止数据丢失
        self.save_minute_klines()

    def save_minute_klines(self):
        with self.lock:
            if self.minute_klines:
                df = pd.DataFrame(self.minute_klines)
                df['datetime'] = pd.to_datetime(df['datetime'])
                output_path = os.path.join(self.data_dir, f'{self.symbol}_minline.csv')
                df.to_csv(output_path, index=False, date_format='%Y-%m-%d %H:%M:%S')
            else:
                # 如果只有非交易时段的快照没有K线数据，可能不需要保存csv，或者创建一个空文件/快照文件
                # 这里根据需求，如果分钟K线为空，就不写入csv文件
                pass

    def run(self):
        print(f"程序启动，股票代码: {self.symbol}")
        self.running = True

        # 初始化累计量
        self.last_cumulative_volume = 0
        self.last_cumulative_amount = 0

        while self.running:
            now = datetime.now()

            # --- 1. 检查是否为交易时段 ---
            if not self.is_trading_time():
                # === 非交易时段逻辑：采集一次并退出 ===
                print(f"\n当前时间 {now.strftime('%H:%M:%S')} 为非交易时段。")
                print("执行最后一次采集后程序将退出...")

                data = self.get_real_time_data()
                if data:
                    self.collect_data_and_save(data, is_trading=False)

                # 退出程序
                print("程序结束。")
                self.running = False
                break

            # --- 2. 交易时段逻辑 ---

            # 计算距离下一分钟 00 秒的等待时间
            current_second = now.second
            # 目标是下一分钟的 00:00
            # 如果现在是 10:00:00 -> wait 60s (也就是下一分钟) 或者 立即采集?
            # 需求：采集是在每分钟的00秒。
            # 为了避免重复，如果刚过00秒，我们等待下一个00秒。
            wait_seconds = 60 - current_second

            print(f"当前 {now.strftime('%H:%M:%S')}，等待 {wait_seconds} 秒至下一分钟采集...")
            time.sleep(wait_seconds)

            # 再次检查状态，防止在sleep期间被停止
            if not self.running: break

            # --- 执行采集 ---
            # 此时理论上应该接近 00 秒
            data = self.get_real_time_data()
            if data:
                self.collect_data_and_save(data, is_trading=True)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取数据为空")

    def start(self):
        try:
            self.run()
        except KeyboardInterrupt:
            print("\n收到中断信号")
        finally:
            print("正在保存数据并退出...")
            self.save_minute_klines()




if __name__ == "__main__":
    collector = get_data(code='600519')
    print(collector)
    # collector.start()
