import os
import pandas as pd
import threading
from datetime import datetime, time as dt_time
import numpy as np
output_dir = r"data"
file_write_lock = threading.Lock()


class emo_doctor:
    def __init__(self):

        self.today_str = datetime.now().strftime("%Y%m%d")
        self.data_dir = "data"
        self.encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']
        self.indicators = {}
        self.emo_columns = [
            '时间', '连板数', '涨停数量',
            # '昨涨停平均收益', '昨涨停上涨比率', '昨涨停下跌比率',
            # '连板晋级率',
            '跌停数量', '炸板数量', '炸板率',

            'M上涨率', 'M下跌率', 'M平盘率', '非一字涨停', '非一字跌停', 'ST涨停', 'ST跌停', '活跃度'
        ]
        emo_file_path = os.path.join(self.data_dir, "emo_data.csv")
        if os.path.exists(emo_file_path):
            try:
                # 读取历史数据
                self.emo_data_df = pd.read_csv(emo_file_path, encoding='utf-8-sig')
                print(f"  ✅ 成功加载历史情绪数据: {len(self.emo_data_df)} 条记录")

                # ========== 添加时间格式统一化处理 ==========
                if '时间' in self.emo_data_df.columns:
                    print("  🔵 统一时间格式...")
                    # 方法：使用 mixed 格式解析时间，然后统一输出格式
                    self.emo_data_df['时间'] = self.emo_data_df['时间'].apply(
                        lambda x: pd.to_datetime(x, format='mixed', errors='coerce').strftime('%Y-%m-%d %H:%M:%S')
                        if pd.notna(x) else x
                    )
                    print("  ✅ 时间格式统一完成")
                # ========== 修改结束 ==========

            except Exception as e:
                print(f"  ⚠️ 读取历史情绪数据失败 ({e})，将创建新数据表")
                self.emo_data_df = pd.DataFrame(columns=self.emo_columns)
        else:
            self.emo_data_df = pd.DataFrame(columns=self.emo_columns)
            print(f"  ℹ️ 未找到历史情绪数据文件，将创建新文件")

    def _align_to_trading_period(self, dt_obj=None):
        """
        将时间对齐到交易时段
        - 9:30-11:30 的任何时间 → 归到当前交易时段的实际时间（对齐到分钟）
        - 11:30-13:00 的任何时间 → 归到 11:30:00
        - 13:00-15:00 的任何时间 → 归到当前交易时段的实际时间（对齐到分钟）
        - 15:00后到次日9:30 → 归到 15:00:00
        """
        if dt_obj is None:
            dt_obj = datetime.now()

        # 先对齐到分钟
        dt_obj = dt_obj.replace(second=0, microsecond=0)
        now_time = dt_obj.time()

        # 定义关键时间点
        t_9_30 = dt_time(9, 30)
        t_11_30 = dt_time(11, 31)
        t_13_00 = dt_time(13, 0)
        t_15_00 = dt_time(15, 1)

        # 判断时间区间并处理
        if now_time < t_9_30:
            dt_obj = dt_obj - pd.Timedelta(days=1)
            dt_obj = dt_obj.replace(hour=15, minute=0)
        elif t_9_30 <= now_time <= t_11_30:
            pass
        elif t_11_30 < now_time < t_13_00:
            dt_obj = dt_obj.replace(hour=11, minute=30)
        elif t_13_00 <= now_time <= t_15_00:
            pass
        else:  # now_time > t_15_00
            dt_obj = dt_obj.replace(hour=15, minute=0)

        return dt_obj.strftime('%Y-%m-%d %H:%M:%S')


    def _normalize_minute(self, time_val):
        """将时间戳归一化到分钟的00秒"""
        if pd.isna(time_val):
            return time_val
        try:
            dt_obj = pd.to_datetime(time_val)
            dt_obj = dt_obj.replace(second=0, microsecond=0)
            return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return time_val

    def _read_csv_with_encoding(self, filepath, file_desc="文件"):
        """尝试多种编码读取CSV文件"""
        if not os.path.exists(filepath):
            print(f"  ⚠️ {file_desc} 不存在: {filepath}")
            return None

        for enc in self.encodings:
            try:
                df = pd.read_csv(filepath, encoding=enc)
                print(f"  ✅ 成功读取{file_desc} (编码: {enc}): {df.shape[0]} 条记录")
                return df
            except Exception as e:
                continue

        print(f"  ❌ 无法使用任何编码读取{file_desc}: {filepath}")
        return None

    def cal_rate(self):
        """计算股票涨幅（简化版，列名已统一）"""
        close_now = 'data//今日价.csv'
        close_pre = 'data//昨日价.txt'

        print("  🔵 读取今日价.csv...")
        try:
            stocks_df = pd.read_csv(close_now)
            print(f"  ✅ 成功读取当前股票数据: {stocks_df.shape[0]} 条记录")
        except FileNotFoundError:
            print(f"❌ 错误: 找不到文件 {close_now}")
            return None
        except Exception as e:
            print(f"❌ 读取当前股票数据失败: {e}")
            return None

        print("  🔵 读取昨日价.txt...")
        try:
            prev_df = None
            for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                try:
                    prev_df = pd.read_csv(close_pre, sep='\t', encoding=enc)
                    print(f"✅ 成功读取上一交易日数据 (编码: {enc}): {prev_df.shape[0]} 条记录")
                    break
                except:
                    try:
                        prev_df = pd.read_csv(close_pre, encoding=enc)
                        print(f"✅ 成功读取上一交易日数据 (CSV格式, 编码: {enc}): {prev_df.shape[0]} 条记录")
                        break
                    except:
                        continue

            if prev_df is None:
                raise Exception("无法使用任何编码格式读取文件")
        except FileNotFoundError:
            print(f"❌ 错误: 找不到文件 {close_pre}")
            return None
        except Exception as e:
            print(f"❌ 读取上一交易日数据失败: {e}")
            return None

        print("  🔵 数据验证...")
        # 列名已统一，检查关键列是否存在
        required_cols = ['Close', 'stock_code']

        missing_stocks = [col for col in required_cols if col not in stocks_df.columns]
        missing_prev = [col for col in required_cols if col not in prev_df.columns]

        if missing_stocks:
            print(f"❌ 错误: 今日价.csv缺少必要列: {missing_stocks}")
            return None
        if missing_prev:
            print(f"❌ 错误: 昨日价.txt缺少必要列: {missing_prev}")
            return None

        print("  🔵 数据清洗...")
        # 统一代码格式：去除后缀并补齐6位
        stocks_df['代码_统一'] = stocks_df['stock_code'].apply(
            lambda x: str(x).split('.')[0].zfill(6) if pd.notna(x) else None
        )
        prev_df['代码_统一'] = prev_df['stock_code'].apply(
            lambda x: str(x).split('.')[0].zfill(6) if pd.notna(x) else None
        )

        # 转换为数值类型
        stocks_df['Close'] = pd.to_numeric(stocks_df['Close'], errors='coerce')
        prev_df['Close'] = pd.to_numeric(prev_df['Close'], errors='coerce')

        print("  🔵 合并数据...")
        # 使用stock_code或代码_统一进行匹配
        merged_df = pd.merge(
            stocks_df,
            prev_df[['代码_统一', 'Close']],
            on='代码_统一',
            how='left',
            suffixes=('', '_prev')
        )

        # 重命名列，使语义更清晰
        merged_df = merged_df.rename(columns={
            'Close': '今日收盘价',
            'Close_prev': '昨日收盘价'
        })

        print(f"📊 合并后数据: {merged_df.shape[0]} 条记录")
        matched_count = merged_df['昨日收盘价'].notna().sum()
        print(f"   成功匹配: {matched_count} 条")
        print(f"   未匹配: {merged_df['昨日收盘价'].isna().sum()} 条")

        # 数据完整性检查
        total_stocks = len(merged_df)
        match_ratio = matched_count / total_stocks if total_stocks > 0 else 0

        if match_ratio < 0.9:
            print(f"  ⚠️ 警告: 昨日价.txt 数据不完整！匹配率仅 {match_ratio:.2%}")
            print(f"     这将导致大量股票无法计算涨幅，影响情绪指标准确性。")

        print("  🔵 计算涨幅（向量化）...")
        import time as time_module
        t_start = time_module.time()

        # 向量化计算涨幅
        # 处理昨日收盘价为0或NaN的情况
        merged_df['涨幅'] = np.where(
            (merged_df['昨日收盘价'] > 0) & (merged_df['昨日收盘价'].notna()),
            100 * (merged_df['今日收盘价'] - merged_df['昨日收盘价']) / merged_df['昨日收盘价'],
            np.nan
        )

        # 处理无穷大值
        merged_df['涨幅'] = np.where(
            np.isinf(merged_df['涨幅']),
            np.nan,
            merged_df['涨幅']
        )

        merged_df['涨幅'] = merged_df['涨幅'].round(2)

        # 未匹配到的股票涨幅设为0（根据需求可改为np.nan）
        merged_df['涨幅'] = merged_df['涨幅'].fillna(0)

        t_end = time_module.time()
        print(f"  ✅ 涨幅计算完成，耗时 {t_end - t_start:.2f} 秒")

        print("  🔵 构造result_df...")
        result_data = {
            '股票代码': merged_df['stock_code'],
            '代码': merged_df['代码_统一'],
            '今日收盘价': merged_df['今日收盘价'],
            '昨日收盘价': merged_df['昨日收盘价'],
            '涨幅': merged_df['涨幅']
        }

        if 'timestamp' in merged_df.columns:
            print("  🔵 处理时间列...")
            t_start = time_module.time()
            result_data['时间'] = merged_df['timestamp']
            result_df = pd.DataFrame(result_data)

            # 归一化时间列
            try:
                temp_times = pd.to_datetime(result_df['时间'], errors='coerce')
                mask = temp_times.notna()
                if mask.any():
                    temp_times.loc[mask] = temp_times.loc[mask].apply(lambda x: x.replace(second=0, microsecond=0))
                    result_df['时间'] = temp_times.dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print(f"  ⚠️ 时间批量转换失败，使用逐行处理: {e}")
                result_df['时间'] = result_df['时间'].apply(self._normalize_minute)

            t_end = time_module.time()
            print(f"  ✅ 时间列处理完成，耗时 {t_end - t_start:.2f} 秒")
        else:
            print("  ⚠️ 未找到timestamp列")
            result_df = pd.DataFrame(result_data)

        print(f"{'=' * 80}\n")
        return result_df

    def cal_emo_indicators(self):
        """计算市场情绪指标"""
        temp_time_data = {}

        def update_temp_data(time_point, data_dict):
            if time_point not in temp_time_data:
                temp_time_data[time_point] = {}
            temp_time_data[time_point].update(data_dict)

        # print("  ⏳ 开始加载全市场行情数据...")
        # rate_df = self.cal_rate()
        # if rate_df is not None and not rate_df.empty:
        #     print(f"  ✅ 全市场数据加载完成，共 {len(rate_df)} 条")
        # else:
        #     print("  ⚠️ 全市场数据为空，部分统计将不可用")

        # ========================================
        # 第1-5项（跳过详细注释，保持原逻辑）
        # ========================================
        print(" 第一项：处理涨停数据 🔵 处理zt.csv...")
        zt_file = os.path.join(self.data_dir, f"zt.csv")
        try:
            if os.path.exists(zt_file):
                df_zt = None
                for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                    try:
                        df_zt = pd.read_csv(zt_file, encoding=enc)
                        break
                    except:
                        continue

                if df_zt is not None and not df_zt.empty:
                    df_zt['连板数'] = pd.to_numeric(df_zt['连板数'], errors='coerce')
                    df_zt['时间'] = df_zt['时间'].apply(self._normalize_minute)

                    time_stats = df_zt.groupby('时间').agg({
                        '代码': 'count',
                        '连板数': 'max'
                    }).reset_index()
                    time_stats.columns = ['时间', '涨停数量', '连板数']

                    for idx, row in time_stats.iterrows():
                        time_point = row['时间']
                        update_temp_data(time_point, {
                            '连板数': int(row['连板数']),
                            '涨停数量': int(row['涨停数量'])
                        })

                    if not time_stats.empty:
                        latest = time_stats.iloc[-1]
                        self.indicators['连板数'] = int(latest['连板数'])
                        self.indicators['涨停数量'] = int(latest['涨停数量'])
                    else:
                        self.indicators['连板数'] = 0
                        self.indicators['涨停数量'] = 0
                else:
                    self.indicators['连板数'] = 0
                    self.indicators['涨停数量'] = 0
        except Exception as e:
            print(f"  ❌ 第1项失败: {e}")
            self.indicators['连板数'] = 0
            self.indicators['涨停数量'] = 0

        print("第二项：处理跌停数据  🔵 处理dt.csv...")
        try:
            csv_path = os.path.join(self.data_dir, 'dt.csv')
            if os.path.exists(csv_path):
                df_dt = None
                for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                    try:
                        df_dt = pd.read_csv(csv_path, encoding=enc)
                        break
                    except:
                        continue

                if df_dt is not None and not df_dt.empty:
                    df_dt['时间'] = df_dt['时间'].apply(self._normalize_minute)
                    time_stats = df_dt.groupby('时间').agg({
                        '代码': 'count'
                    }).reset_index()
                    time_stats.columns = ['时间', '跌停数量']

                    for idx, row in time_stats.iterrows():
                        time_point = row['时间']
                        update_temp_data(time_point, {'跌停数量': int(row['跌停数量'])})

                    if not time_stats.empty:
                        self.indicators['跌停数量'] = int(time_stats.iloc[-1]['跌停数量'])
                    else:
                        self.indicators['跌停数量'] = 0
                else:
                    self.indicators['跌停数量'] = 0
        except Exception as e:
            print(f"  ❌ 第2项失败: {e}")
            self.indicators['跌停数量'] = 0

        # print(" 第三项：处理昨日涨停数据 🔵 处理zt_pre.csv...")
        # try:
        #     csv_path = os.path.join(self.data_dir, 'zt_pre.csv')
        #     if os.path.exists(csv_path):
        #         df = None
        #         for enc in self.encodings:
        #             try:
        #                 df = pd.read_csv(csv_path, encoding=enc)
        #                 break
        #             except:
        #                 continue
        #
        #         if df is not None and not df.empty and '时间' in df.columns and '涨跌幅' in df.columns:
        #             df['时间'] = df['时间'].apply(self._normalize_minute)
        #             time_stats = df.groupby('时间').agg(
        #                 昨涨停平均收益=('涨跌幅', 'mean'),
        #                 昨涨停上涨家数=('涨跌幅', lambda x: (x > 0).sum()),
        #                 昨涨停下跌家数=('涨跌幅', lambda x: (x < 0).sum()),
        #                 昨涨停跌停家数=('涨跌幅', lambda x: (x <= -9.9).sum())
        #             ).reset_index()
        #
        #             time_stats['昨涨停平均收益'] = time_stats['昨涨停平均收益'].round(2)
        #             time_stats['昨涨停上涨比率'] = time_stats.apply(
        #                 lambda row: round(
        #                     (row['昨涨停上涨家数'] / row[['昨涨停上涨家数', '昨涨停下跌家数']].sum()) * 100, 2)
        #                 if (row['昨涨停上涨家数'] + row['昨涨停下跌家数']) > 0 else 0,
        #                 axis=1
        #             )
        #             time_stats['昨涨停下跌比率'] = time_stats.apply(
        #                 lambda row: round(
        #                     (row['昨涨停下跌家数'] / row[['昨涨停上涨家数', '昨涨停下跌家数']].sum()) * 100, 2)
        #                 if (row['昨涨停上涨家数'] + row['昨涨停下跌家数']) > 0 else 0,
        #                 axis=1
        #             )
        #
        #             for idx, row in time_stats.iterrows():
        #                 time_point = row['时间']
        #                 update_temp_data(time_point, {
        #                     '昨涨停平均收益': round(row['昨涨停平均收益'], 2),
        #                     '昨涨停上涨比率': round(row['昨涨停上涨比率'], 2),
        #                     '昨涨停下跌比率': round(row['昨涨停下跌比率'], 2),
        #                     '昨涨停上涨家数': int(row['昨涨停上涨家数']),
        #                     '昨涨停下跌家数': int(row['昨涨停下跌家数']),
        #                     '昨涨停跌停家数': int(row['昨涨停跌停家数'])
        #                 })
        #
        #             if not time_stats.empty:
        #                 latest = time_stats.iloc[-1]
        #                 self.indicators['昨涨停平均收益'] = round(latest['昨涨停平均收益'], 2)
        #                 self.indicators['昨涨停上涨家数'] = int(latest['昨涨停上涨家数'])
        #                 self.indicators['昨涨停下跌家数'] = int(latest['昨涨停下跌家数'])
        #                 self.indicators['昨涨停跌停家数'] = int(latest['昨涨停跌停家数'])
        #             else:
        #                 self.indicators['昨涨停平均收益'] = 0
        #                 self.indicators['昨涨停上涨家数'] = 0
        #                 self.indicators['昨涨停下跌家数'] = 0
        #                 self.indicators['昨涨停跌停家数'] = 0
        #         else:
        #             self.indicators['昨涨停平均收益'] = 0
        #             self.indicators['昨涨停上涨家数'] = 0
        #             self.indicators['昨涨停下跌家数'] = 0
        #             self.indicators['昨涨停跌停家数'] = 0
        # except Exception as e:
        #     print(f"  ❌ 第3项失败: {e}")
        #     self.indicators['昨涨停平均收益'] = 0
        #     self.indicators['昨涨停上涨家数'] = 0
        #     self.indicators['昨涨停下跌家数'] = 0
        #     self.indicators['昨涨停跌停家数'] = 0
        #
        # print(" 第四项：处理连板晋级数据从昨天涨停股中发现 🔵 处理连板晋级率...")
        # try:
        #     curr_csv_path = os.path.join(self.data_dir, 'zt.csv')
        #     pre_csv_path = os.path.join(self.data_dir, 'zt_pre.csv')
        #
        #     df_today = None
        #     df_yesterday = None
        #
        #     if os.path.exists(curr_csv_path):
        #         for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
        #             try:
        #                 df_today = pd.read_csv(curr_csv_path, encoding=enc)
        #                 break
        #             except:
        #                 continue
        #
        #     if os.path.exists(pre_csv_path):
        #         for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
        #             try:
        #                 df_yesterday = pd.read_csv(pre_csv_path, encoding=enc)
        #                 break
        #             except:
        #                 continue
        #
        #     if df_yesterday is not None and not df_yesterday.empty:
        #         yesterday_stocks = set()
        #         if '代码' in df_yesterday.columns:
        #             yesterday_stocks = set(df_yesterday['代码'].dropna().astype(str).str.zfill(6).unique())
        #         yesterday_count = len(yesterday_stocks)
        #
        #         if df_today is not None and not df_today.empty and '代码' in df_today.columns and '时间' in df_today.columns:
        #             df_today['时间'] = df_today['时间'].apply(self._normalize_minute)
        #             time_stats_list = []
        #             time_points = df_today['时间'].unique()
        #
        #             for t in time_points:
        #                 curr_stocks = set(
        #                     df_today[df_today['时间'] == t]['代码'].dropna().astype(str).str.zfill(6).unique())
        #                 advanced_count = len(yesterday_stocks & curr_stocks)
        #                 rate = round((advanced_count / yesterday_count) * 100, 2) if yesterday_count > 0 else 0
        #                 time_stats_list.append({'时间': t, '连板晋级率': rate})
        #
        #             df_stats = pd.DataFrame(time_stats_list)
        #             df_stats = df_stats.sort_values('时间')
        #
        #             for idx, row in df_stats.iterrows():
        #                 time_point = row['时间']
        #                 update_temp_data(time_point, {'连板晋级率': float(row['连板晋级率'])})
        #
        #             if not df_stats.empty:
        #                 self.indicators['连板晋级率'] = float(df_stats.iloc[-1]['连板晋级率'])
        #             else:
        #                 self.indicators['连板晋级率'] = 0
        #         else:
        #             self.indicators['连板晋级率'] = 0
        #     else:
        #         self.indicators['连板晋级率'] = 0
        # except Exception as e:
        #     print(f"  ❌ 第4项失败: {e}")
        #     self.indicators['连板晋级率'] = 0

        print(" 第五项：处理炸板数据 🔵 处理炸板数据...")
        try:
            not_csv_path = os.path.join(self.data_dir, 'zt_not.csv')
            zt_csv_path = os.path.join(self.data_dir, 'zt.csv')

            if os.path.exists(not_csv_path) and os.path.exists(zt_csv_path):
                df_not = None
                for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                    try:
                        df_not = pd.read_csv(not_csv_path, encoding=enc)
                        break
                    except:
                        continue

                df_zt = None
                for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                    try:
                        df_zt = pd.read_csv(zt_csv_path, encoding=enc)
                        break
                    except:
                        continue

                if df_not is not None and df_zt is not None and not df_not.empty and not df_zt.empty and '时间' in df_not.columns and '时间' in df_zt.columns:
                    df_not['时间'] = df_not['时间'].apply(self._normalize_minute)
                    df_zt['时间'] = df_zt['时间'].apply(self._normalize_minute)

                    df_not_stats = df_not.groupby('时间').size().reset_index(name='炸板数量')
                    df_zt_stats = df_zt.groupby('时间').size().reset_index(name='涨停数量')

                    df_merged = pd.merge(df_not_stats, df_zt_stats, on='时间', how='outer')
                    df_merged = df_merged.fillna(0)

                    df_merged['炸板率'] = df_merged.apply(
                        lambda row: round((row['炸板数量'] / (row['涨停数量'] + row['炸板数量'])) * 100, 2)
                        if (row['涨停数量'] + row['炸板数量']) > 0 else 0,
                        axis=1
                    )
                    df_merged = df_merged.sort_values('时间')

                    for idx, row in df_merged.iterrows():
                        time_point = row['时间']
                        update_temp_data(time_point, {
                            '炸板数量': int(row['炸板数量']),
                            '炸板率': round(row['炸板率'], 2)
                        })

                    if not df_merged.empty:
                        latest = df_merged.iloc[-1]
                        self.indicators['炸板数量'] = int(latest['炸板数量'])
                        self.indicators['炸板率'] = round(latest['炸板率'], 2)
                    else:
                        self.indicators['炸板数量'] = 0
                        self.indicators['炸板率'] = 0
                else:
                    self.indicators['炸板数量'] = 0
                    self.indicators['炸板率'] = 0
            else:
                self.indicators['炸板数量'] = 0
                self.indicators['炸板率'] = 0
        except Exception as e:
            print(f"  ❌ 第5项失败: {e}")
            self.indicators['炸板数量'] = 0
            self.indicators['炸板率'] = 0





        print(" 第九项：处理赚钱效率据  🔵 处理earn.csv...")
        try:
            # 修正文件路径为 earn.csv
            csv_path = os.path.join(self.data_dir, 'earn.csv')
            if os.path.exists(csv_path):
                df_earn = None
                for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                    try:
                        df_earn = pd.read_csv(csv_path, encoding=enc)
                        print(f"  ✅ 成功读取earn.csv (编码: {enc}): {df_earn.shape[0]} 条记录")
                        break
                    except:
                        continue

                if df_earn is not None and not df_earn.empty:
                    # 1. 归一化时间列（统一到分钟00秒）
                    df_earn['时间'] = df_earn['时间'].apply(self._normalize_minute)

                    # 2. 数据类型转换：将需要计算和保存的列转为数值型
                    cols_to_numeric = ['上涨', '下跌', '平盘', '非一字涨停', '非一字跌停', 'st涨停', 'st跌停', '活跃度']
                    for col in cols_to_numeric:
                        if col in df_earn.columns:
                            df_earn[col] = pd.to_numeric(df_earn[col], errors='coerce')

                    # 3. 计算总数 (上涨+下跌+平盘)，用于计算比率
                    if '上涨' in df_earn.columns and '下跌' in df_earn.columns and '平盘' in df_earn.columns:
                        df_earn['总数'] = df_earn['上涨'] + df_earn['下跌'] + df_earn['平盘']

                        # 定义计算函数，处理分母为0的情况
                        def calc_rate(val, total):
                            return round(100 * val / total, 2) if total > 0 else 0.0

                        # 计算各项比率
                        df_earn['M上涨率'] = df_earn.apply(lambda row: calc_rate(row['上涨'], row['总数']), axis=1)
                        # 提示中“平均”推测为“下跌”的笔误，此处使用'下跌'
                        df_earn['M下跌率'] = df_earn.apply(lambda row: calc_rate(row['下跌'], row['总数']), axis=1)
                        df_earn['M平盘率'] = df_earn.apply(lambda row: calc_rate(row['平盘'], row['总数']), axis=1)
                    else:
                        print("  ⚠️ earn.csv 缺少必要的统计列(上涨/下跌/平盘)，比率将设为0")
                        df_earn['M上涨率'] = 0.0
                        df_earn['M下跌率'] = 0.0
                        df_earn['M平盘率'] = 0.0

                    # 4. 遍历行，更新临时数据 temp_time_data
                    for idx, row in df_earn.iterrows():
                        time_point = row['时间']
                        update_temp_data(time_point, {
                            'M上涨率': float(row['M上涨率']),
                            'M下跌率': float(row['M下跌率']),
                            'M平盘率': float(row['M平盘率']),
                            '非一字涨停': int(row.get('非一字涨停', 0)),
                            '非一字跌停': int(row.get('非一字跌停', 0)),
                            'ST涨停': int(row.get('st涨停', 0)),  # CSV是小写st，这里转为大写ST以匹配列名
                            'ST跌停': int(row.get('st跌停', 0)),
                            '活跃度': float(row.get('活跃度', 0.0))
                        })

                    # 5. 更新 self.indicators (取最新的一条记录)
                    if not df_earn.empty:
                        latest = df_earn.iloc[-1]
                        self.indicators['M上涨率'] = float(latest['M上涨率'])
                        self.indicators['M下跌率'] = float(latest['M下跌率'])
                        self.indicators['M平盘率'] = float(latest['M平盘率'])
                        self.indicators['非一字涨停'] = int(latest.get('非一字涨停', 0))
                        self.indicators['非一字跌停'] = int(latest.get('非一字跌停', 0))
                        self.indicators['ST涨停'] = int(latest.get('st涨停', 0))
                        self.indicators['ST跌停'] = int(latest.get('st跌停', 0))
                        self.indicators['活跃度'] = float(latest.get('活跃度', 0.0))
                    else:
                        # 初始化默认值
                        self.indicators['M上涨率'] = 0.0
                        self.indicators['M下跌率'] = 0.0
                        self.indicators['M平盘率'] = 0.0
                        self.indicators['非一字涨停'] = 0
                        self.indicators['非一字跌停'] = 0
                        self.indicators['ST涨停'] = 0
                        self.indicators['ST跌停'] = 0
                        self.indicators['活跃度'] = 0.0
                else:
                    self.indicators['M上涨率'] = 0.0
                    self.indicators['M下跌率'] = 0.0
                    self.indicators['M平盘率'] = 0.0
                    self.indicators['非一字涨停'] = 0
                    self.indicators['非一字跌停'] = 0
                    self.indicators['ST涨停'] = 0
                    self.indicators['ST跌停'] = 0
                    self.indicators['活跃度'] = 0.0
            else:
                print(f"  ⚠️ 赚钱效率文件不存在: {csv_path}")
                self.indicators['M上涨率'] = 0.0
                self.indicators['M下跌率'] = 0.0
                self.indicators['M平盘率'] = 0.0
                self.indicators['非一字涨停'] = 0
                self.indicators['非一字跌停'] = 0
                self.indicators['ST涨停'] = 0
                self.indicators['ST跌停'] = 0
                self.indicators['活跃度'] = 0.0

        except Exception as e:
            print(f"  ❌ 第9项失败: {e}")
            import traceback
            traceback.print_exc()
            self.indicators['M上涨率'] = 0.0
            self.indicators['M下跌率'] = 0.0
            self.indicators['M平盘率'] = 0.0
            self.indicators['非一字涨停'] = 0
            self.indicators['非一字跌停'] = 0
            self.indicators['ST涨停'] = 0
            self.indicators['ST跌停'] = 0
            self.indicators['活跃度'] = 0.0

        print(" 第十步： 🔵 合并数据到emo_data_df...")
        # 第十步： 🔵 合并数据到emo_data_df...
        if temp_time_data:
            temp_df = pd.DataFrame.from_dict(temp_time_data, orient='index')
            temp_df.reset_index(inplace=True)
            temp_df.rename(columns={'index': '时间'}, inplace=True)

            if self.emo_data_df is None or self.emo_data_df.empty:
                self.emo_data_df = temp_df.copy()
            else:
                # 【修复方案】使用 concat 进行纵向追加，而不是 merge
                # concat 不会改变列名，只会追加行
                self.emo_data_df = pd.concat([self.emo_data_df, temp_df], ignore_index=True)

            # 去重逻辑保持不变：以“时间”为准，保留最新的一条数据（实现“更新”的效果）
            self.emo_data_df = self.emo_data_df.sort_values('时间').reset_index(drop=True)
            self.emo_data_df = self.emo_data_df.drop_duplicates(subset=['时间'], keep='last')

            print(f"  ✅ 已合并，共 {len(self.emo_data_df)} 个时间点")
        else:
            print(f"  ⚠️ 没有收集到任何时间点数据")

        print("  🔵 添加当前时间数据...")
        # try:
        #     current_time = datetime.now().replace(second=0, microsecond=0)
        #     current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        #
        #     new_row_data = {'时间': current_time_str}
        #
        #     for col in self.emo_data_df.columns:
        #         if col == '时间':
        #             continue
        #         elif col == '昨龙虎榜平均收益':
        #             new_row_data[col] = self.indicators.get('昨龙虎榜平均涨幅', 0)
        #         elif col in self.indicators:
        #             new_row_data[col] = self.indicators[col]
        #         else:
        #             new_row_data[col] = 0
        #
        #     new_row_df = pd.DataFrame([new_row_data])
        #     print("  🔵 执行concat...")
        #     self.emo_data_df = pd.concat([self.emo_data_df, new_row_df], ignore_index=True)
        #     print("  ✅ concat完成")
        #
        # except Exception as e:
        #     print(f"  ❌ 更新emo_data_df失败: {e}")
        #     import traceback
        #     traceback.print_exc()

        return self.indicators

    def _init_stock_distribution(self):
        """初始化全体股票行情统计的默认值"""
        self.indicators['涨幅大于7的数量'] = 0
        self.indicators['涨幅5-7的数量'] = 0
        self.indicators['涨幅3-5的数量'] = 0
        self.indicators['涨幅0-3的数量'] = 0
        self.indicators['跌幅小于-7的数量'] = 0
        self.indicators['跌幅0--3的数量'] = 0
        self.indicators['跌幅-3--5的数量'] = 0
        self.indicators['跌幅-5--7的数量'] = 0

    def save_emo_data(self, filename=None, force_collect=False, max_cycles=None):
        import time
        from datetime import datetime, time as dt_time

        if filename is None:
            filename = f"data\\emo_data.csv"

        morning_start = dt_time(9, 30)
        morning_end = dt_time(11, 30)
        afternoon_start = dt_time(13, 0)
        afternoon_end = dt_time(15, 0)

        def is_trading_time():
            now = datetime.now().time()
            return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

        def is_before_market_close():
            now = datetime.now().time()
            return now <= afternoon_end

        print("=" * 80)
        print(f"保存文件: {filename}")
        print(f"强制采集: {'是' if force_collect else '否'}")
        print(f"最大次数: {max_cycles if max_cycles else '无限制'}")

        current_time = datetime.now()
        print(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if not force_collect and not is_trading_time():
            print(f"⚠️ 当前不在交易时间段内！")
            if current_time.time() < morning_start:
                wait_until = datetime.combine(current_time.date(), morning_start)
                print(f"   距离开盘还有 {(wait_until - current_time).seconds // 60} 分钟")
            elif morning_end < current_time.time() < afternoon_start:
                print(f"   午间休息时段")
            elif current_time.time() > afternoon_end:
                print(f"   已过收盘时间")
            print("=" * 80)
            print("提示: 如需测试采集功能，请使用 force_collect=True")
        print("=" * 80)

        cycle_count = 0

        try:
            while is_before_market_close() or force_collect:
                try:
                    current_time = datetime.now()
                    now_time = current_time.time()

                    if is_trading_time() or force_collect:
                        if force_collect and cycle_count >= 1:
                            print(f"\n🏁 强制采集模式，采集1次后结束")
                            break

                        cycle_count += 1
                        print(f"\n{'=' * 80}")
                        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 第 {cycle_count} 次采集")
                        print(f"{'=' * 80}")

                        print("📊 开始计算指标...")
                        indicators = self.cal_emo_indicators()

                        if not indicators:
                            print("  ⚠️ 指标计算结果为空字典！")
                        else:
                            print(f"  ✅ 指标计算成功，共 {len(indicators)} 个指标")

                        if not self.emo_data_df.empty:
                            self.emo_data_df = self.emo_data_df.sort_values('时间').reset_index(drop=True)
                            try:
                                self.emo_data_df.to_csv(filename, index=False, encoding='utf-8-sig')
                                print(f"  ✅ 已保存完整数据表 (共 {len(self.emo_data_df)} 行)")
                                if len(self.emo_data_df) > 1:
                                    print(
                                        f"     时间范围: {self.emo_data_df['时间'].iloc[0]} ~ {self.emo_data_df['时间'].iloc[-1]}")
                            except Exception as e:
                                print(f"  ❌ 保存文件失败: {e}")

                        if max_cycles and cycle_count >= max_cycles:
                            break

                        if force_collect:
                            break

                    else:
                        if now_time < morning_start:
                            wait_until = datetime.combine(current_time.date(), morning_start)
                            wait_minutes = (wait_until - current_time).total_seconds() / 60
                            if wait_minutes > 0 and wait_minutes <= 120:
                                print(f"\n⏰ 等待开盘，距离9:30还有 {int(wait_minutes)} 分钟...")
                        elif morning_end < now_time < afternoon_start:
                            wait_until = datetime.combine(current_time.date(), afternoon_start)
                            wait_minutes = (wait_until - current_time).total_seconds() / 60
                            if wait_minutes > 0 and wait_minutes <= 120:
                                print(f"\n☕ 午间休息，距离13:00还有 {int(wait_minutes)} 分钟...")
                        elif now_time > afternoon_end:
                            print(f"\n🏁 已过收盘时间15:00，停止采集")
                            break

                    if not force_collect:
                        time.sleep(120)
                    else:
                        break

                except KeyboardInterrupt:
                    print("\n\n⚠️ 用户手动中断采集")
                    break
                except Exception as e:
                    print(f"\n❌ 采集过程中出错: {e}")
                    import traceback
                    traceback.print_exc()
                    if not force_collect:
                        time.sleep(120)
                    else:
                        break

        except Exception as e:
            print(f"\n❌ 主循环出错: {e}")
            import traceback
            traceback.print_exc()

        if not self.emo_data_df.empty:
            self.emo_data_df = self.emo_data_df.sort_values('时间').reset_index(drop=True)
            self.emo_data_df = self.emo_data_df.drop_duplicates(subset=['时间'])
            try:
                self.emo_data_df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"\n🎉 已将完整数据表覆盖保存至: {filename}")
                print(f"   包含历史时间点及当前数据，共 {len(self.emo_data_df)} 行")
            except Exception as e:
                print(f"\n❌ 保存完整数据表失败: {e}")
        else:
            print(f"\n⚠️ 警告: self.emo_data_df 为空，未保存历史数据")

        print("\n" + "=" * 80)
        print("采集结束汇总")
        print("=" * 80)

        if not self.emo_data_df.empty:
            return self.emo_data_df
        else:
            return pd.DataFrame()


# 使用示例
if __name__ == "__main__":
    doctor = emo_doctor()
    print("\n[Step 2] 正在保存结果并计算得分...")
    doctor.save_emo_data(force_collect=True)
