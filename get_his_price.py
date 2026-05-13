# -*- coding: utf-8 -*-
import os
from typing import Optional
from mootdx.reader import Reader
import pandas as pd
import mootdx
import json
#从通达信日线数据中获取历史日线
class get_data:
    @staticmethod
    def load_config():
        try:
            with open('setup.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    config = load_config()
    if not config:
        raise SystemExit("⚠️ 未找到或无法读取 setup.json")
    TDX_PATH = config.get('TDX_PATH')

    def stock_day(self,code) -> Optional[pd.DataFrame]:
        tdx_dir: str = self.TDX_PATH
        output_dir: str = r'data'
        try:
            os.makedirs(output_dir, exist_ok=True)

            reader = Reader.factory(market='std', tdxdir=tdx_dir)
            df1 = reader.daily(symbol=code)

            if df1 is None or df1.empty:
                print(f"警告：股票 {code} 无日线数据")
                return None

            # 关键修复：重置索引，将 date 从 index 转为普通列
            df1 = df1.reset_index()

            # 确保列名正确（mootdx 返回的日期列名可能是 'date' 或 'datetime'，一般是 'date'）
            if 'date' not in df1.columns:
                # 兜底：如果索引重置后列名不是 'date'，尝试其他可能
                possible_date_cols = [col for col in df1.columns if 'date' in str(col).lower()]
                if possible_date_cols:
                    df1.rename(columns={possible_date_cols[0]: 'date'}, inplace=True)
                else:
                    raise ValueError("无法找到日期列")

            # 仅保留需要的列，并确保顺序
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
            df = df1[required_cols].copy()

            # 转换日期格式（mootdx 的 date 通常是 int 类型，如 20231201）
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

            # 价格字段保留两位小数
            price_cols = ['open', 'high', 'low', 'close']
            df[price_cols] = df[price_cols].round(2)

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            # 保存 CSV（自动包含 header）
            output_path = os.path.join(output_dir, f"{code}_day.csv")
            df.to_csv(output_path, index=False, date_format='%Y-%m-%d')
            print(f"✅ 已成功保存：{output_path}")

            return df

        except Exception as e:
            print(f"❌ 处理股票 {code} 时出错: {e}")
            return None

    def stock_fzline(self, code) -> Optional[pd.DataFrame]:
        tdx_dir: str = self.TDX_PATH
        output_dir: str = r'data'
        try:
            os.makedirs(output_dir, exist_ok=True)

            reader = Reader.factory(market='std', tdxdir=tdx_dir)
            df1 = reader.fzline(symbol=code)

            if df1 is None or df1.empty:
                print(f"警告：股票 {code} 无日线数据")
                return None

            # 关键修复：重置索引，将 date 从 index 转为普通列
            df1 = df1.reset_index()

            # 确保列名正确（mootdx 返回的日期列名可能是 'date' 或 'datetime'，一般是 'date'）
            if 'date' not in df1.columns:
                # 兜底：如果索引重置后列名不是 'date'，尝试其他可能
                possible_date_cols = [col for col in df1.columns if 'date' in str(col).lower()]
                if possible_date_cols:
                    df1.rename(columns={possible_date_cols[0]: 'date'}, inplace=True)
                else:
                    raise ValueError("无法找到日期列")

            # 仅保留需要的列，并确保顺序
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
            df = df1[required_cols].copy()

            # 转换日期格式（mootdx 的 date 通常是 int 类型，如 20231201）
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d %H%M%S')

            # 价格字段保留两位小数
            price_cols = ['open', 'high', 'low', 'close']
            df[price_cols] = df[price_cols].round(2)

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            # 保存 CSV（自动包含 header）
            output_path = os.path.join(output_dir, f"{code}_fzline.csv")
            df.to_csv(output_path, index=False, date_format='%Y%m%d %H%M%S')
            print(f"✅ 已成功保存：{output_path}")

            return df

        except Exception as e:
            print(f"❌ 处理股票 {code} 时出错: {e}")
            return None

    def stock_minline(self, code) -> Optional[pd.DataFrame]:
        tdx_dir: str = self.TDX_PATH
        output_dir: str = r'data'
        try:
            os.makedirs(output_dir, exist_ok=True)

            reader = Reader.factory(market='std', tdxdir=tdx_dir)
            df1 = reader.minute(symbol=code)

            if df1 is None or df1.empty:
                print(f"警告：股票 {code} 无日线数据")
                return None

            # 关键修复：重置索引，将 date 从 index 转为普通列
            df1 = df1.reset_index()

            # 确保列名正确（mootdx 返回的日期列名可能是 'date' 或 'datetime'，一般是 'date'）
            if 'date' not in df1.columns:
                # 兜底：如果索引重置后列名不是 'date'，尝试其他可能
                possible_date_cols = [col for col in df1.columns if 'date' in str(col).lower()]
                if possible_date_cols:
                    df1.rename(columns={possible_date_cols[0]: 'date'}, inplace=True)
                else:
                    raise ValueError("无法找到日期列")

            # 仅保留需要的列，并确保顺序
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
            df = df1[required_cols].copy()

            # 转换日期格式（mootdx 的 date 通常是 int 类型，如 20231201）
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d %H%M%S')

            # 价格字段保留两位小数
            price_cols = ['open', 'high', 'low', 'close']
            df[price_cols] = df[price_cols].round(2)

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            # 保存 CSV（自动包含 header）
            output_path = os.path.join(output_dir, f"{code}_minline.csv")
            df.to_csv(output_path, index=False, date_format='%Y%m%d %H%M%S')
            print(f"✅ 已成功保存：{output_path}")

            return df

        except Exception as e:
            print(f"❌ 处理股票 {code} 时出错: {e}")
            return None

    def block(self, code):
        tdx_dir: str = self.TDX_PATH
        # 确保 TDX_PATH 不为空
        if not tdx_dir:
            print("错误：未获取到通达信路径，请检查 setup.txt")
            return None

        # 初始化时传入路径
        df = mootdx.reader.StdReader(tdxdir=tdx_dir)
        symbol = code
        df = df.block(symbol=symbol, group=False)


if __name__ == "__main__":
    # df = get_data().stock_fzline(code = '301360')
    # df = df.sort_index(ascending=False)
    # close_price = df["close"].iloc[0]
    # print(f"最新收盘价: {close_price}")
    # print(df)
    # df = get_data().stock_day(code='880716')
    # df = df.sort_index(ascending=False)
    # close_price = df["close"].iloc[0]
    # print(f"最新收盘价: {close_price}")
    df = get_data().stock_day(code='515080')
    print(df)
    # df = get_data().block(code='515080')
    # print(df)



