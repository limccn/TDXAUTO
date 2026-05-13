import pandas as pd
import akshare as ak
import os
from datetime import datetime, time
import time as time_module
import time as tm
import re
import json
start_date: str = "20241201"
end_date: str = "20280101"


class data_his:

    def __init__(self):
        """初始化：创建data目录"""
        self.data_dir = "data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # 记录每个函数最后获取历史数据的日期
        self.last_fetch_date = {}
        # 记录龙虎榜数据最后获取的日期（每天只获取一次）
        self.last_lhb_fetch_date = None
        self.last_batch_lhb_fetch_date = None

    def get_from_setup(self):
        setup_file = "setup.json"
        try:
            with open(setup_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('TDX_PATH')
        except FileNotFoundError:
            print(f"配置文件 {setup_file} 不存在")
            return None
        except json.JSONDecodeError as e:
            print(f"配置文件 {setup_file} 格式错误: {e}")
            return None

    def start_realtime_fetch_with_callback(self, interval_minutes=2, callback=None, stop_check=None):
        """
        启动实时数据自动获取（支持回调函数和停止检查）

        :param interval_minutes: 获取间隔（分钟）
        :param callback: 回调函数，用于发送日志信息
        :param stop_check: 停止检查函数，返回True表示应该停止
        """

        def log(message):
            if callback:
                try:
                    callback(message)
                except Exception as e:
                    print(f"回调失败: {e}")
                    print(message)
            else:
                print(message)

        while True:
            # 检查是否应该停止
            if stop_check and stop_check():
                log("🛑 收到停止信号，退出下载循环")
                break

            try:
                # ========== 修改部分：计算对齐等待时间 ==========
                now = datetime.now()

                # 计算当前时间距离小时开始的秒数 (例如 10:01:30 -> 90秒)
                seconds_into_hour = now.minute * 60 + now.second

                # 设定周期秒数 (2分钟 = 120秒)
                period_seconds = interval_minutes * 60

                # 计算余数，判断是否刚好在对齐时间点
                remainder = seconds_into_hour % period_seconds

                # 如果刚好在对齐点(余数为0)，立即执行；否则计算等待时间
                if remainder == 0:
                    wait_seconds = 0
                else:
                    wait_seconds = period_seconds - remainder

                # 如果需要等待，则先睡眠，直到到达下一个对齐整点
                if wait_seconds > 0:
                    log(f"等待 {wait_seconds} 秒后对齐到整点/2分执行...")

                    # 分段睡眠，每秒检查一次停止信号
                    for _ in range(wait_seconds):
                        if stop_check and stop_check():
                            log("🛑 收到停止信号，退出等待")
                            return
                        time_module.sleep(1)  # 使用 time_module

                    # 睡眠结束后更新时间，用于日志
                    now = datetime.now()
                # ==========================================

                log(f"\n{'=' * 60}")
                log(f"定时获取: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                log(f"{'=' * 60}")

                # 获取今天的日期字符串
                today = self._get_today_date_str()
                current_dt = datetime.now()
                date_today = current_dt.strftime("%Y-%m-%d")
                date_three_days_ago = (current_dt - pd.Timedelta(days=3)).strftime("%Y-%m-%d")

                # # ========== 新增：每天第一次运行时提取通达信热股 ==========
                # if 'extract_tdx_hot' not in self.last_fetch_date or self.last_fetch_date['extract_tdx_hot'] != today:
                #     log("\n【正在提取通达信热股...】")
                #     self.extract_tdx_hot_stocks()

                # 每天第一次运行时，获取上一个交易日的龙虎榜数据（仅一次）
                if self.last_lhb_fetch_date != today:
                    log("\n【正在获取上一个交易日龙虎榜数据...】")

                    # 计算上一个交易日的日期
                    previous_trading_day = (pd.Timestamp.now() - pd.Timedelta(days=1)).strftime("%Y%m%d")
                    self.lhb(previous_trading_day, previous_trading_day)

                    # 标记今天已获取过龙虎榜数据
                    self.last_lhb_fetch_date = today
                    log(f"✅ 龙虎榜数据获取完成（上榜日: {previous_trading_day}）")

                if self.last_batch_lhb_fetch_date != today:
                    log("\n【正在批量下载龙虎榜详情...】")
                    log(f"上榜日范围: {date_three_days_ago} 至 {date_today}")

                    # 调用 batch_lhb，延时设为 1 秒，避免请求过快
                    self.batch_lhb(start_date=date_three_days_ago, end_date=date_today, delay_seconds=1.0)

                    # 标记今天已执行过批量下载
                    self.last_batch_lhb_fetch_date = today
                    log(f"✅ 龙虎榜详情批量下载完成")

                # 在交易时段获取所有实时数据
                if self._is_trading_time():
                    log("\n【正在获取实时数据...】")

                    try:
                        self.stock_zt()
                    except Exception as e:
                        log(f"⚠️ 获取涨停数据失败: {e}")

                    # try:
                    #     self.stock_zt_pre()
                    # except Exception as e:
                    #     log(f"⚠️ 获取昨日涨停数据失败: {e}")

                    try:
                        self.stock_dt()
                    except Exception as e:
                        log(f"⚠️ 获取跌停数据失败: {e}")

                    try:
                        self.stock_zt_not()
                    except Exception as e:
                        log(f"⚠️ 获取炸板数据失败: {e}")

                    # ========== 新增：获取市场涨跌效果数据 ==========
                    try:
                        log("\n【正在获取市场涨跌效果数据...】")
                        self.earn_effect()
                    except Exception as e:
                        log(f"⚠️ 获取市场涨跌效果数据失败: {e}")

                    log("\n【实时数据获取完成】")
                else:
                    log("\n非交易时间，暂不获取实时数据")

                # 移除了原有的固定sleep逻辑，因为下一次循环开始时会自动计算对齐时间

            except KeyboardInterrupt:
                log("\n定时任务已停止")
                break
            except Exception as e:
                log(f"\n定时任务出错: {e}")
                import traceback
                log(traceback.format_exc())

                # 出错后等待更长时间再重试
                try:
                    import time
                    time.sleep(30)
                except:
                    pass

    def extract_tdx_hot_stocks(self, force_fetch=False):
        """从通达信热股文件提取股票列表"""
        # 如果不是强制获取，检查今天是否已执行
        if not force_fetch:
            today = self._get_today_date_str()
            if 'extract_tdx_hot' in self.last_fetch_date and self.last_fetch_date['extract_tdx_hot'] == today:
                print(f"通达信热股今日已提取过，跳过")
                return None

        TDX_PATH = self.get_from_setup()
        if TDX_PATH is None:
            print("❌ 错误：未找到 TDX_PATH 配置，请检查 setup.json 文件")
            return

        file_path = rf'{TDX_PATH}\T0002\hq_cache\infoharbor_block.dat'
        if not os.path.exists(file_path):
            print(f"❌ 错误：文件不存在 {file_path}")
            return

        target_code = "880818"
        stock_list = []

        # 读取整个文件
        try:
            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️ 编码读取失败，尝试 latin1: {e}")
            with open(file_path, 'r', encoding='latin1', errors='ignore') as f:
                lines = f.readlines()

        found_block = False
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # 查找目标板块行
            if line.startswith('#') and f",{target_code}," in line:
                found_block = True
                i += 1  # 从下一行开始读股票
                stock_lines = []

                # 持续读取，直到遇到下一个 # 开头的行或文件结束
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith('#'):
                        break  # 遇到下一个板块，停止
                    if next_line:  # 非空行加入
                        stock_lines.append(next_line)
                    i += 1

                # 合并所有股票行（去除行尾逗号不影响正则）
                full_stock_text = ''.join(stock_lines)
                # 提取所有 0#000000 格式的股票
                stocks = re.findall(r'([012])#(\d{6})', full_stock_text)
                for market, code in stocks:
                    suffix = {'0': '.SZ', '1': '.SH', '2': '.BJ'}[market]
                    stock_list.append(f"{code}{suffix}")
                break  # 找到目标板块后退出

            i += 1

        if not found_block:
            print(f"⚠️ 未找到板块代码 {target_code}")
            all_blocks = []
            for line in lines:
                if line.startswith('#'):
                    parts = line[1:].split(',')
                    if len(parts) >= 3 and parts[2].isdigit() and len(parts[2]) == 6:
                        all_blocks.append(parts[2])
            print("文件中包含的板块代码（前10个）:", list(set(all_blocks[:10])))

        # 写入 task.txt
        with open("data\\tdx_hot.txt", "w", encoding="utf-8") as f:
            for stock in stock_list:
                f.write(stock + '\n')

        # 写入成功后记录上榜日
        if stock_list:
            today = self._get_today_date_str()
            self.last_fetch_date['extract_tdx_hot'] = today

        print(f"✅ 成功提取通达信热股到 tdx_hot.txt，共 {len(stock_list)} 只股票")

    def _is_trading_time(self):
        """判断是否在交易时间：09:30-11:30 和 13:00-15:00"""
        now = datetime.now().time()
        morning_start = time(9, 30)
        morning_end = time(11, 31)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 1)

        return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

    def _align_to_trading_period(self, dt_obj=None):
        """
        将时间对齐到交易时段
        - 9:30-11:30 的任何时间 → 归到当前交易时段的实际时间
        - 11:30-13:00 的任何时间 → 归到 11:30:00
        - 13:00-15:00 的任何时间 → 归到当前交易时段的实际时间
        - 15:00后到次日9:30 → 归到 15:00:00

        :param dt_obj: datetime对象，如果为None则使用当前时间
        :return: 格式化的时间字符串 'YYYY-MM-DD HH:MM:00'
        """
        if dt_obj is None:
            dt_obj = datetime.now()

        # 去除秒和微秒，对齐到分钟
        dt_obj = dt_obj.replace(second=0, microsecond=0)

        now_time = dt_obj.time()

        # 定义关键时间点
        t_9_30 = time(9, 30)
        t_11_30 = time(11, 30)
        t_13_00 = time(13, 0)
        t_15_00 = time(15, 0)

        # 判断时间区间并处理
        if now_time < t_9_30:
            # 早盘之前：归到昨天下午15:00
            dt_obj = dt_obj - pd.Timedelta(days=1)
            dt_obj = dt_obj.replace(hour=15, minute=0)

        elif t_9_30 <= now_time <= t_11_30:
            # 早盘时段：保持当前时间
            pass

        elif t_11_30 < now_time < t_13_00:
            # 午休时段：归到11:30
            dt_obj = dt_obj.replace(hour=11, minute=30)

        elif t_13_00 <= now_time <= t_15_00:
            # 下午时段：保持当前时间
            pass

        else:  # now_time > t_15_00
            # 收盘后：归到15:00
            dt_obj = dt_obj.replace(hour=15, minute=0)

        return dt_obj.strftime('%Y-%m-%d %H:%M:%S')

    def _get_now_time_str(self):
        """获取当前时间字符串：HH:MM:SS"""
        return datetime.now().strftime("%H:%M:%S")

    def _get_today_date_str(self):
        """获取今天的日期字符串，用于文件名：YYYYMMDD"""
        return datetime.now().strftime("%Y%m%d")

    def _format_amount_to_yi(self, amount):
        """将金额转为亿元，保留2位小数"""
        if pd.isna(amount):
            return amount
        try:
            return round(float(amount) / 100000000, 2)
        except:
            return amount

    def _format_to_2_decimal(self, value):
        """保留2位小数"""
        if pd.isna(value):
            return value
        try:
            return round(float(value), 2)
        except:
            return value

    def _save_to_csv(self, df, filename, mode='w'):
        """
        保存到CSV文件
        mode='w': 覆盖写入
        mode='a': 追加写入
        """
        if df is not None and not df.empty:
            filepath = os.path.join(self.data_dir, filename)

            # 处理表头：追加模式下，如果文件不存在或为空，则写入表头
            header = True
            if mode == 'a':
                header = not os.path.exists(filepath) or os.path.getsize(filepath) == 0

            df.to_csv(filepath, mode=mode, header=header, index=False, encoding='utf-8-sig')

            action = "追加保存到" if mode == 'a' else "保存到"
            print(f"数据已{action}: {filepath}")
            return True
        else:
            print(f"数据为空，未保存: {filename}")
            return False

    def start_realtime_fetch(self, interval_minutes=2):
        """
        启动实时数据自动获取
        - 每天首次运行时获取上一个交易日的龙虎榜数据（仅一次）
        - 固定在每小时的第0分、2分、4分...的第00秒自动获取实时数据，其他时间不获取
        """
        while True:
            try:
                # ========== 修改部分：计算对齐等待时间 ==========
                now = datetime.now()

                # 计算当前时间距离小时开始的秒数 (例如 10:01:30 -> 90秒)
                seconds_into_hour = now.minute * 60 + now.second

                # 设定周期秒数 (3分钟 = 180秒)
                period_seconds = interval_minutes * 60

                # 计算余数，判断是否刚好在对齐时间点
                remainder = seconds_into_hour % period_seconds

                # 如果刚好在对齐点(余数为0)，立即执行；否则计算等待时间
                if remainder == 0:
                    wait_seconds = 0
                else:
                    wait_seconds = period_seconds - remainder

                # 如果需要等待，则先睡眠，直到到达下一个对齐整点
                if wait_seconds > 0:
                    print(f"当前时间: {now.strftime('%H:%M:%S')}，等待 {wait_seconds} 秒后对齐到整点/2分执行...")
                    time_module.sleep(wait_seconds)
                    # 睡眠结束后更新时间，用于日志
                    now = datetime.now()
                # ==========================================

                print(f"\n{'=' * 60}")
                print(f"定时获取: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'=' * 60}")

                # 获取今天的日期字符串
                today = self._get_today_date_str()
                current_dt = datetime.now()
                date_today = current_dt.strftime("%Y-%m-%d")
                date_three_days_ago = (current_dt - pd.Timedelta(days=3)).strftime("%Y-%m-%d")

                # ========== 新增：每天第一次运行时提取通达信热股 ==========
                # if 'extract_tdx_hot' not in self.last_fetch_date or self.last_fetch_date['extract_tdx_hot'] != today:
                #     print("\n【正在提取通达信热股...】")
                #     self.extract_tdx_hot_stocks()

                # 每天第一次运行时，获取上一个交易日的龙虎榜数据（仅一次）
                if self.last_lhb_fetch_date != today:
                    print("\n【正在获取上一个交易日龙虎榜数据...】")

                    # 计算上一个交易日的日期
                    previous_trading_day = (pd.Timestamp.now() - pd.Timedelta(days=1)).strftime("%Y%m%d")
                    self.lhb(previous_trading_day, previous_trading_day)

                    # 标记今天已获取过龙虎榜数据
                    self.last_lhb_fetch_date = today
                    print(f"✅ 龙虎榜数据获取完成（日期: {previous_trading_day}）")

                if self.last_batch_lhb_fetch_date != today:
                    print("\n【正在批量下载龙虎榜详情...】")
                    print(f"日期范围: {date_three_days_ago} 至 {date_today}")

                    # 调用 batch_lhb，延时设为 1 秒，避免请求过快
                    self.batch_lhb(start_date=date_three_days_ago, end_date=date_today, delay_seconds=1.0)

                    # 标记今天已执行过批量下载
                    self.last_batch_lhb_fetch_date = today
                    print(f"✅ 龙虎榜详情批量下载完成")

                # 在交易时段获取所有实时数据
                if self._is_trading_time():
                    print("\n【正在获取实时数据...】")

                    # self.stock_fund_today()
                    #
                    # self.gn_fund()
                    self.stock_zt()
                    # self.stock_zt_pre()
                    self.stock_dt()
                    self.stock_zt_not()
                    # ========== 新增：获取市场涨跌效果数据 ==========
                    print("\n【正在获取市场涨跌效果数据...】")
                    self.earn_effect()

                    print("\n【实时数据获取完成】")
                else:
                    print("\n非交易时间，暂不获取实时数据")

                # 移除了原有的固定sleep逻辑，因为下一次循环开始时会自动计算对齐时间

            except KeyboardInterrupt:
                print("\n定时任务已停止")
                break
            except Exception as e:
                print(f"\n定时任务出错: {e}")
                time_module.sleep(60)

    def stock_fund_today(self, force_fetch=False):
        """
        实时资金流入-东财目标地址: https://data.eastmoney.com/zjlx/detail.html
        保存到data/funds_data.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取实时资金流向数据")
                return None

        try:
            stock_individual_fund_flow_rank_df = ak.stock_individual_fund_flow_rank(indicator="今日")
            if stock_individual_fund_flow_rank_df is not None and not stock_individual_fund_flow_rank_df.empty:
                df = stock_individual_fund_flow_rank_df.copy()

                # 处理金额列（转为亿元）
                if '今日主力净流入-净额' in df.columns:
                    df['今日主力净流入-净额'] = df['今日主力净流入-净额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                if '今日主力净流入-净占比' in df.columns:
                    df['今日主力净流入-净占比'] = df['今日主力净流入-净占比'].apply(self._format_to_2_decimal)

                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据（保留原有的覆盖模式，如需追加请修改 mode='a'）
                self._save_to_csv(df, 'funds_data.csv')

                return df
        except Exception as e:
            print(f"获取实时资金流入数据失败: {e}")
        return None

    def gn_fund(self, force_fetch=False):
        """
        获取板块实时资金
        保存到data/blk_fund.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取概念板块资金")
                return None

        try:
            stock_sector_fund_flow_rank_df = ak.stock_sector_fund_flow_rank(
                indicator="今日",
                sector_type="概念资金流"
            )

            if stock_sector_fund_flow_rank_df is not None and not stock_sector_fund_flow_rank_df.empty:
                df = stock_sector_fund_flow_rank_df.copy()

                # 处理金额列
                if '今日主力净流入-净额' in df.columns:
                    df['今日主力净流入-净额'] = df['今日主力净流入-净额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                if '今日主力净流入-净占比' in df.columns:
                    df['今日主力净流入-净占比'] = df['今日主力净流入-净占比'].apply(self._format_to_2_decimal)

                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据（保留原有的覆盖模式，如需追加请修改 mode='a'）
                self._save_to_csv(df, 'blk_fund.csv')

                return df
        except Exception as e:
            print(f"获取概念板块资金失败: {e}")
        return None

    def stock_zt(self, force_fetch=False):
        """
        获取涨停股票列表
        保存到data/zt.csv (追加模式)

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取涨停股票")
                return None

        try:
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df_raw = ak.stock_zt_pool_em(date=today)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # 格式化数值列
                amount_cols = ['成交额', '流通市值', '总市值', '封板资金']
                for col in amount_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_amount_to_yi)

                pct_cols = ['涨跌幅', '换手率', '量比', '振幅', '流通市值占比', '年初至今涨跌幅', '5日涨跌幅']
                for col in pct_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)

                # 添加时间列
                aligned_time = self._align_to_trading_period()
                df['时间'] = aligned_time
                df.insert(0, '时间', df.pop('时间'))

                # 【修改点】使用追加模式保存数据
                self._save_to_csv(df, 'zt.csv', mode='a')

                return df
        except Exception as e:
            print(f"获取涨停股票数据失败: {e}")
        return None

    def stock_zt_pre(self, force_fetch=False):
        """
        获取昨日涨停股票列表
        保存到data/zt_pre.csv (追加模式)

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取昨日涨停股票")
                return None

        try:
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df_raw = ak.stock_zt_pool_previous_em(date=today)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # 格式化数值列
                amount_cols = ['成交额', '流通市值', '总市值']
                for col in amount_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_amount_to_yi)

                pct_cols = ['涨跌幅', '换手率', '量比', '振幅']
                for col in pct_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)

                # 添加时间列
                aligned_time = self._align_to_trading_period()
                df['时间'] = aligned_time
                df.insert(0, '时间', df.pop('时间'))

                # 【修改点】使用追加模式保存数据
                self._save_to_csv(df, 'zt_pre.csv', mode='a')

                return df
        except Exception as e:
            print(f"获取昨日涨停股票数据失败: {e}")
        return None

    def stock_dt(self, force_fetch=False):
        """
        获取跌停列表
        保存到data/dt.csv (追加模式)

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取跌停股票")
                return None

        try:
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df_raw = ak.stock_zt_pool_dtgc_em(date=today)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # 格式化数值列
                amount_cols = ['成交额', '流通市值', '总市值']
                for col in amount_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_amount_to_yi)

                pct_cols = ['涨跌幅', '换手率', '量比', '振幅']
                for col in pct_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)

                # 添加时间列
                aligned_time = self._align_to_trading_period()
                df['时间'] = aligned_time
                df.insert(0, '时间', df.pop('时间'))

                # 【修改点】使用追加模式保存数据
                self._save_to_csv(df, 'dt.csv', mode='a')

                return df
        except Exception as e:
            print(f"获取跌停股票数据失败: {e}")
        return None

    def stock_zt_not(self, force_fetch=False):
        """
        获取炸板股票列表
        保存到data/zt_not.csv (追加模式)

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取炸板股票")
                return None

        try:
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df_raw = ak.stock_zt_pool_zbgc_em(date=today)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # 格式化数值列
                amount_cols = ['成交额', '流通市值', '总市值']
                for col in amount_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_amount_to_yi)

                pct_cols = ['涨跌幅', '换手率', '量比', '振幅']
                for col in pct_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)

                # 添加时间列
                aligned_time = self._align_to_trading_period()
                df['时间'] = aligned_time
                df.insert(0, '时间', df.pop('时间'))

                # 【修改点】使用追加模式保存数据
                self._save_to_csv(df, 'zt_not.csv', mode='a')

                return df
        except Exception as e:
            print(f"获取炸板股票数据失败: {e}")
        return None

    def lhb(self, start_date: str, end_date: str):
        """
        获取龙虎榜数据，只输出代码列
        保存到data/lhb_last.csv
        每天更新覆盖原数据
        """
        # 规范化日期格式
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        filename = f'lhb_last.csv'
        filepath = os.path.join(self.data_dir, filename)

        # 如果文件存在，先删除（强制重新获取）
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"🗑️  已删除旧文件: {filename}")
            except Exception as e:
                print(f"⚠️  删除旧文件失败: {e}")

        try:
            # 从网络获取数据
            df_raw = ak.stock_lhb_detail_em(start_date=start, end_date=end)
            print(f"🌐 从网络获取龙虎榜数据，原始列名: {df_raw.columns.tolist() if df_raw is not None else 'None'}")

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # 尝试查找代码列（支持多种可能的列名）
                code_col = None
                possible_code_cols = ['代码', '名称', '股票代码', '股票名称', 'symbol', 'name']
                for col in possible_code_cols:
                    if col in df.columns:
                        code_col = col
                        print(f"✅ 找到代码列: {code_col}")
                        break

                if code_col is None:
                    print(f"❌ 未找到代码列，原始数据列: {df.columns.tolist()}")
                    return pd.DataFrame(columns=['代码'])

                # 只保留代码列（并重命名为 '代码'）
                result = pd.DataFrame()
                result['代码'] = df[code_col]

                # 保存文件
                self._save_to_csv(result, filename)
                print(f"✅ 龙虎榜数据已保存到: {filename}，共 {len(result)} 只股票")
                return result
            else:
                print(f"❌ 网络数据为空")
                return pd.DataFrame(columns=['代码'])
        except Exception as e:
            print(f"❌ 获取或处理龙虎榜数据失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(columns=['代码'])

    def lhb_list(self, start_date: str, end_date: str):
        """
        统计一段时间的龙虎榜龙
        保存到data/lhb.csv

        修复逻辑：
        1. 无论本地文件是否存在，都根据 start_date 和 end_date 请求网络数据。
        2. 如果本地存在旧数据，读取并合并。
        3. 基于 [上榜日, 代码] 进行去重（保留最新的）。
        4. 保存覆盖，实现"增量更新"的效果。
        """
        # 规范化日期格式
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        filename = f'lhb.csv'
        filepath = os.path.join(self.data_dir, filename)

        # ========== 1. 强制从网络获取新数据 ==========
        print(f"正在从网络获取 {start} 至 {end} 的龙虎榜数据...")
        try:
            df_raw = ak.stock_lhb_detail_em(start_date=start, end_date=end)
        except Exception as e:
            print(f"网络请求失败: {e}")
            # 如果网络完全失败，尝试返回本地现有数据（如果有）
            if os.path.exists(filepath):
                print(f"网络失败，返回本地缓存数据: {filepath}")
                return pd.read_csv(filepath)
            return None

        if df_raw is None or df_raw.empty:
            print(f"该日期范围网络无数据: {start} - {end}")
            # 如果网络无数据，尝试返回本地现有数据（如果有）
            if os.path.exists(filepath):
                return pd.read_csv(filepath)
            return None

        print(f"网络获取成功，新增 {len(df_raw)} 条记录")

        # ========== 2. 处理新数据格式 ==========
        df_new = df_raw.copy()

        # 重命名映射
        rename_map = {
            '上榜日': '上榜日',
            '代码': '代码',
            '名称': '名称',
            '收盘价': '收盘价',
            '涨跌幅': '涨跌幅',
            '净买额': '龙虎榜净买额',
            '买入金额': '龙虎榜买入额',
            '卖出金额': '龙虎榜卖出额',
            '成交金额': '龙虎榜成交额',
            '市场总成交': '市场总成交额',
            '换手率': '换手率',
            '流通市值': '流通市值',
            '解读': '解读',
            '上榜原因': '上榜原因'
        }

        # 过滤存在的列
        existing_cols = {old: new for old, new in rename_map.items() if old in df_new.columns}
        df_new = df_new.rename(columns=existing_cols)

        # 确保目标列存在，缺失则补 NA
        target_cols_basic = [
            '代码', '名称', '上榜日', '解读', '收盘价', '涨跌幅',
            '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜成交额',
            '市场总成交额', '换手率', '流通市值', '上榜原因'
        ]

        for col in target_cols_basic:
            if col not in df_new.columns:
                df_new[col] = pd.NA

        # 计算占比（转为亿元）
        df_new['龙虎榜净买额'] = pd.to_numeric(df_new['龙虎榜净买额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['龙虎榜成交额'] = pd.to_numeric(df_new['龙虎榜成交额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['市场总成交额'] = pd.to_numeric(df_new['市场总成交额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['龙虎榜买入额'] = pd.to_numeric(df_new['龙虎榜买入额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['龙虎榜卖出额'] = pd.to_numeric(df_new['龙虎榜卖出额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['流通市值'] = pd.to_numeric(df_new['流通市值'], errors='coerce').apply(self._format_amount_to_yi)

        df_new['净买额占总成交比'] = (df_new['龙虎榜净买额'] / df_new['市场总成交额']).apply(self._format_to_2_decimal)
        df_new['成交额占总成交比'] = (df_new['龙虎榜成交额'] / df_new['市场总成交额']).apply(self._format_to_2_decimal)

        # 数值列保留2位小数
        float_cols = ['收盘价', '涨跌幅', '换手率']
        for col in float_cols:
            if col in df_new.columns:
                df_new[col] = df_new[col].apply(self._format_to_2_decimal)

        # 最终列顺序
        final_cols = [
            '上榜日', '代码', '名称', '解读', '收盘价', '涨跌幅',
            '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜成交额',
            '市场总成交额', '净买额占总成交比', '成交额占总成交比',
            '换手率', '流通市值', '上榜原因'
        ]

        # 确保新数据只包含需要的列
        df_new = df_new[final_cols].copy()

        # ========== 3. 合并与去重逻辑（核心修复）==========
        df_final = df_new

        if os.path.exists(filepath):
            try:
                df_old = pd.read_csv(filepath, encoding='utf-8-sig')

                if not df_old.empty:
                    # 确保旧数据的列顺序和新数据一致，方便合并
                    # 补齐旧数据缺失的列
                    for col in final_cols:
                        if col not in df_old.columns:
                            df_old[col] = pd.NA
                    df_old = df_old[final_cols].copy()

                    print(f"本地存在旧数据 {len(df_old)} 条，正在合并...")

                    # 合并新旧数据
                    df_merged = pd.concat([df_old, df_new], ignore_index=True)

                    # 去重：基于 '上榜日' 和 '代码'
                    # keep='last' 表示如果有相同的“上榜日+代码”，保留最后出现的（即保留新的网络数据）
                    print(f"合并后共 {len(df_merged)} 条，正在去重...")
                    df_final = df_merged.drop_duplicates(subset=['上榜日', '代码'], keep='last')

                    print(f"去重后最终数据: {len(df_final)} 条")
            except Exception as e:
                print(f"读取本地数据出错: {e}，将只保存新数据")
                df_final = df_new

        # ========== 4. 保存 ==========
        self._save_to_csv(df_final, filename)
        return df_final

    def lhb_stat(self, period: str = "近一月"):
        """
        获取龙虎榜统计（如近一月上榜次数等）
        保存到data/lhb_stat_{period}.csv
        每天只获取一次，检查存在就不再请求
        """
        filename = f'lhb_stat_{period}.csv'

        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            print(f"龙虎榜统计数据已存在: {filename}")
            return pd.read_csv(filepath)

        try:
            valid_periods = ["近一月", "近三月", "近六月", "近一年"]
            if period not in valid_periods:
                print(f"警告: period 应为 {valid_periods} 之一，使用默认 '近一月'")
                period = "近一月"

            df_raw = ak.stock_lhb_stock_statistic_em(symbol=period)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()
                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取龙虎榜统计数据失败 ({period}): {e}")
        return None

    def lhb_hyyyb(self, start_date: str = "20260101", end_date: str = "20260119"):
        """
        获取龙虎榜活跃的营业部
        保存到data/lhb_hyyyb_{start}_{end}.csv
        每天只获取一次，检查存在就不再请求
        """
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        filename = f'lhb_hyyyb_{start}_{end}.csv'

        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            print(f"龙虎榜活跃营业部数据已存在: {filename}")
            return pd.read_csv(filepath)

        try:
            df_raw = ak.stock_lhb_hyyyb_em(start_date=start, end_date=end)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()
                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取龙虎榜活跃营业部数据失败 ({start} ~ {end}): {e}")
        return None

    def lhb_stock_detail(self, stock_code: str, date: str, flag: str = "买入", existing_detail_df=None):
        """
        个股龙虎榜详情
        保存到data/lhb_detail.csv（汇总文件）

        优化点：
        1. 新增参数 existing_detail_df：接收预先加载好的历史数据DataFrame，避免每次都读取文件。
        """
        # ========== 1. 输入参数标准化 ==========
        stock_code = str(stock_code).strip()

        # 处理带市场前缀的情况 (如 "0.000001" -> "000001")
        if '.' in stock_code:
            parts = stock_code.split('.')
            if len(parts) == 2:
                stock_code = parts[-1].zfill(6)
        else:
            stock_code = stock_code.zfill(6)
        # ========== 1. 结束 ==========

        clean_date = date.replace("-", "")
        filename = 'lhb_detail.csv'
        filepath = os.path.join(self.data_dir, filename)

        # ========== 2. 重复检查逻辑（优化核心）==========
        # 优先使用传入的 existing_detail_df（已过滤好的近3天数据）
        # 如果没有传入，则回退到原有的读取全量文件逻辑
        df_to_check = existing_detail_df

        if df_to_check is None:
            if os.path.exists(filepath):
                try:
                    if os.path.getsize(filepath) > 0:
                        df_to_check = pd.read_csv(filepath, encoding='utf-8-sig')
                        # 关键修复：标准化现有数据的格式
                        if '代码' in df_to_check.columns:
                            df_to_check['代码'] = df_to_check['代码'].astype(str).str.zfill(6)
                        if '上榜日' in df_to_check.columns:
                            df_to_check['上榜日'] = df_to_check['上榜日'].astype(str).str.replace("-", "")
                except Exception as e:
                    print(f"⚠️ 检查现有数据时出错: {e}，将重新获取")
                    df_to_check = None

        # 执行查重
        if df_to_check is not None and not df_to_check.empty:
            if '上榜日' in df_to_check.columns and '代码' in df_to_check.columns and 'flag' in df_to_check.columns:
                duplicate_mask = (
                        (df_to_check['上榜日'] == clean_date) &
                        (df_to_check['代码'] == stock_code) &
                        (df_to_check['flag'] == flag)
                )

                if duplicate_mask.any():
                    print(f"数据已经存在，进行下一条的处理: {stock_code} {clean_date} {flag}")
                    return False  # 返回 False 表示跳过
        # ========== 2. 检查结束 ==========

        try:
            if flag not in ["买入", "卖出"]:
                raise ValueError("flag 必须为 '买入' 或 '卖出'")

            df_raw = ak.stock_lhb_stock_detail_em(symbol=stock_code, date=clean_date, flag=flag)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # ========== 在最前面插入三列 ==========
                df.insert(0, '上榜日', clean_date)
                df.insert(1, '代码', stock_code)
                df.insert(2, 'flag', flag)

                # 列名模糊匹配与数据处理（保持原逻辑不变）
                buy_amt_col = next((col for col in df.columns if '买入金额' in col and '比例' not in col), None)
                buy_ratio_col = next(
                    (col for col in df.columns if '买入金额' in col and ('比例' in col or '比' in col)), None)
                sell_amt_col = next((col for col in df.columns if '卖出金额' in col and '比例' not in col), None)
                sell_ratio_col = next(
                    (col for col in df.columns if '卖出金额' in col and ('比例' in col or '比' in col)), None)
                net_col = next((col for col in df.columns if
                                any(kw in col for kw in ['净额', '净买', '净卖', '净买入', '净卖出'])), None)

                if buy_amt_col:
                    df[buy_amt_col] = df[buy_amt_col].apply(self._format_amount_to_yi)
                    df.rename(columns={buy_amt_col: '买入金额(亿)'}, inplace=True)

                if buy_ratio_col:
                    s = df[buy_ratio_col].astype(str).str.replace('%', '', regex=False)
                    df[buy_ratio_col] = pd.to_numeric(s, errors='coerce')
                    if df[buy_ratio_col].max() > 1:
                        df[buy_ratio_col] = (df[buy_ratio_col] / 100).apply(self._format_to_2_decimal)
                    else:
                        df[buy_ratio_col] = df[buy_ratio_col].apply(self._format_to_2_decimal)
                    df.rename(columns={buy_ratio_col: '买入占比'}, inplace=True)

                if sell_amt_col:
                    df[sell_amt_col] = df[sell_amt_col].apply(self._format_amount_to_yi)
                    df.rename(columns={sell_amt_col: '卖出金额(亿)'}, inplace=True)

                if sell_ratio_col:
                    s = df[sell_ratio_col].astype(str).str.replace('%', '', regex=False)
                    df[sell_ratio_col] = pd.to_numeric(s, errors='coerce')
                    if df[sell_ratio_col].max() > 1:
                        df[sell_ratio_col] = (df[sell_ratio_col] / 100).apply(self._format_to_2_decimal)
                    else:
                        df[sell_ratio_col] = df[sell_ratio_col].apply(self._format_to_2_decimal)
                    df.rename(columns={sell_ratio_col: '卖出占比'}, inplace=True)

                if net_col:
                    df[net_col] = df[net_col].apply(self._format_amount_to_yi)
                    df.rename(columns={net_col: '净额(亿)'}, inplace=True)

                # ========== 保存到统一文件 ==========
                if os.path.exists(filepath):
                    existing_df_file = pd.read_csv(filepath, encoding='utf-8-sig')
                    combined_df = pd.concat([existing_df_file, df], ignore_index=True)
                    combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')
                else:
                    self._save_to_csv(df, filename)

                return df
            else:
                print(f"无数据: {stock_code} {clean_date} {flag}")
                return None
        except Exception as e:
            print(f"❌ 获取或处理个股龙虎榜详情失败 ({stock_code}, {date}, flag): {e}")
            import traceback
            traceback.print_exc()
        return None

    def batch_lhb(self, start_date: str, end_date: str, delay_seconds: float = 1.0):
        """
        批量下载龙虎榜详情数据

        优化：
        1. 在循环开始前，一次性读取并过滤 lhb_detail.csv，只保留 start_date 至 end_date 范围内的数据。
        2. 将过滤后的 DataFrame 传递给 lhb_stock_detail，避免重复读取文件和全量查重。
        3. 【核心修复】：过滤 lhb_list 返回的总表数据，只处理指定上榜日范围内的记录，避免处理历史旧数据。
        """
        print(f"【步骤1】正在获取龙虎榜总表: {start_date} 至 {end_date} ...")

        # 1. 先执行 lhb_list 获取总表
        df_list = self.lhb_list(start_date, end_date)

        if df_list is None or df_list.empty:
            print("❌ 龙虎榜总表为空或获取失败，无法继续下载详情")
            return

        # ========== 【新增修复】：过滤总表上榜日范围 ==========
        # 规范化日期字符串用于比较 (YYYYMMDD)
        clean_start_date = start_date.replace("-", "")
        clean_end_date = end_date.replace("-", "")

        # 确保 '上榜日' 列为标准字符串格式 (YYYYMMDD)
        if '上榜日' in df_list.columns:
            original_count = len(df_list)
            df_list['上榜日'] = df_list['上榜日'].astype(str).str.replace("-", "").str.strip()

            # 过滤：只保留在 start_date 和 end_date 之间的数据
            df_list = df_list[
                (df_list['上榜日'] >= clean_start_date) &
                (df_list['上榜日'] <= clean_end_date)
                ].copy()

            filtered_count = len(df_list)
            if original_count != filtered_count:
                print(
                    f"🔍 总表已过滤: 剔除了 {original_count - filtered_count} 条历史旧数据，仅保留 {filtered_count} 条 ({clean_start_date} 至 {clean_end_date})")
        # =================================================

        total_count = len(df_list)
        print(f"✅ 龙虎榜总表获取成功，共 {total_count} 条记录")
        print(f"【步骤2】开始遍历下载个股详情...")

        # ========== 步骤1.5 预加载并过滤历史详情数据 (保持原优化逻辑) ==========
        detail_cache_df = None
        detail_file_path = os.path.join(self.data_dir, 'lhb_detail.csv')

        if os.path.exists(detail_file_path) and os.path.getsize(detail_file_path) > 0:
            print(f"【步骤1.5】正在读取并过滤本地龙虎榜详情数据 ({clean_start_date} 至 {clean_end_date})...")
            try:
                temp_df = pd.read_csv(detail_file_path, encoding='utf-8-sig')

                # 应用与 lhb_stock_detail 中一致的格式化逻辑
                if '代码' in temp_df.columns:
                    temp_df['代码'] = temp_df['代码'].astype(str).str.zfill(6)
                if '上榜日' in temp_df.columns:
                    temp_df['上榜日'] = temp_df['上榜日'].astype(str).str.replace("-", "")

                # 确保上榜日列为字符串进行比较
                temp_df['上榜日'] = temp_df['上榜日'].astype(str)

                # 筛选在上榜日范围内的数据
                detail_cache_df = temp_df[
                    (temp_df['上榜日'] >= clean_start_date) &
                    (temp_df['上榜日'] <= clean_end_date)
                    ].copy()

                print(f"✅ 过滤后缓存数据: {len(detail_cache_df)} 条 (用于本次查重)")

            except Exception as e:
                print(f"⚠️ 读取缓存数据失败: {e}，将每次读取文件查重")
                detail_cache_df = None
        # ==========================================

        skipped_count = 0
        failed_count = 0
        success_count = 0

        # 2. 遍历总表 (此时 df_list 已经只包含指定日期范围的数据)
        for index, row in df_list.iterrows():
            code = row.get('代码')
            raw_date = row.get('上榜日')

            if pd.isna(code) or pd.isna(raw_date):
                skipped_count += 1
                print(f"⏭️  跳过 [{index + 1}/{total_count}] 数据无效")
                continue

            # 代码格式化
            code = str(code).strip()
            if '.' in code:
                parts = code.split('.')
                if len(parts) == 2:
                    code = parts[-1].zfill(6)
            else:
                code = code.zfill(6)

            if not code.isdigit() or len(code) != 6:
                skipped_count += 1
                print(f"⏭️  跳过 [{index + 1}/{total_count}] 股票代码格式错误: {code}")
                continue

            clean_date = str(raw_date).replace("-", "")
            print(f"⏳ 进度 [{index + 1}/{total_count}] 正在处理: {code} ({raw_date})")

            # 3. 先获取买入详情 (传入缓存的 detail_cache_df)
            try:
                result = self.lhb_stock_detail(stock_code=code, date=clean_date, flag="买入",
                                               existing_detail_df=detail_cache_df)

                if result is False:
                    pass  # 已存在，不延时
                else:
                    if result is not None:
                        success_count += 1
                        # 如果获取了新数据，追加到内存缓存中，保证本次循环内查重准确性
                        detail_cache_df = pd.concat([detail_cache_df, result], ignore_index=True)
                    time_module.sleep(delay_seconds)

            except Exception as e:
                failed_count += 1
                print(f"  ❌ {code} 买入详情获取失败: {e}")
                time_module.sleep(delay_seconds)

            # 4. 再获取卖出详情 (传入更新后的 detail_cache_df)
            try:
                result = self.lhb_stock_detail(stock_code=code, date=clean_date, flag="卖出",
                                               existing_detail_df=detail_cache_df)

                if result is False:
                    pass
                else:
                    if result is not None:
                        success_count += 1
                        # 追加到内存缓存
                        detail_cache_df = pd.concat([detail_cache_df, result], ignore_index=True)
                    time_module.sleep(delay_seconds)

            except Exception as e:
                failed_count += 1
                print(f"  ❌ {code} 卖出详情获取失败: {e}")
                time_module.sleep(delay_seconds)

        # 统计信息
        print(f"\n{'=' * 60}")
        print(f"📊 批量下载完成统计:")
        print(f"  总记录数: {total_count}")
        print(f"  跳过数量: {skipped_count}")
        print(f"  失败数量: {failed_count}")
        print(f"  成功获取: {success_count}")
        print(f"{'=' * 60}")
        print(f"✅ 所有龙虎榜详情批量下载完成！")

    def earn_effect(self, force_fetch=False):

        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取市场涨跌效果数据")
                return None

        try:
            # 获取市场活动数据
            stock_market_activity_legu_df = ak.stock_market_activity_legu()

            if stock_market_activity_legu_df is None or stock_market_activity_legu_df.empty:
                print("未获取到市场活动数据")
                return None

            # 打印原始数据结构（用于调试）
            print(f"获取到的市场活动数据列名: {stock_market_activity_legu_df.columns.tolist()}")
            print(f"数据示例:\n{stock_market_activity_legu_df.head()}")
            # ========== 关键修复：将 item-value 格式转换为字典 ==========
            data_dict = {}
            for _, row in stock_market_activity_legu_df.iterrows():
                item_name = row.get('item', '')
                value = row.get('value', 0)
                if item_name and pd.notna(value):
                    # 转换为字符串并去除百分号
                    value_str = str(value).strip()
                    if value_str.endswith('%'):
                        value_str = value_str.rstrip('%')

                    # 转换为数值
                    try:
                        num_value = float(value_str)

                        # 活跃度保留为浮点数（百分比）
                        if item_name == '活跃度':
                            data_dict[item_name] = round(num_value, 2)
                        else:
                            # 其他字段转换为整数
                            data_dict[item_name] = int(num_value)
                    except:
                        data_dict[item_name] = 0

            # 提取基础数据
            current_time = self._align_to_trading_period()

            stats = {
                '时间': current_time,
                '上涨': data_dict.get('上涨', 0),
                '非一字涨停': data_dict.get('真实涨停', 0),
                'st涨停': data_dict.get('st st*涨停', 0),
                '下跌': data_dict.get('下跌', 0),
                '非一字跌停': data_dict.get('真实跌停', 0),
                'st跌停': data_dict.get('st st*跌停', 0),
                '平盘': data_dict.get('平盘', 0),
                '活跃度': data_dict.get('活跃度', 0)
            }

            # 创建DataFrame
            result_df = pd.DataFrame([stats])

            # 确保列顺序正确
            columns_order = [
                '时间', '上涨',
                '下跌', '平盘', '非一字涨停', '非一字跌停', 'st涨停', 'st跌停', '活跃度'
            ]
            result_df = result_df[columns_order]

            # 保存到CSV（追加模式）
            self._save_to_csv(result_df, 'earn.csv', mode='a')

            # 打印结果
            print(f"\n✅ 市场涨跌效果数据:")
            print(result_df.to_string(index=False))

            return result_df

        except Exception as e:
            print(f"获取市场涨跌效果数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None


class update:
    # 类属性
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir

    def __init__(self):
        """初始化：创建data目录"""
        self.data_dir = "data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # 记录每个函数最后获取历史数据的日期
        self.last_fetch_date = {}
        # 记录龙虎榜数据最后获取的日期（每天只获取一次）
        self.last_lhb_fetch_date = None
        self.last_batch_lhb_fetch_date = None


    def _get_now_time_str(self):
        """获取当前时间字符串：HH:MM:SS"""
        return datetime.now().strftime("%H:%M:%S")

    def _get_today_date_str(self):
        """获取今天的日期字符串，用于文件名：YYYYMMDD"""
        return datetime.now().strftime("%Y%m%d")


    def _format_amount_to_yi(self, amount):
        """将金额转为亿元，保留2位小数"""
        if pd.isna(amount):
            return amount
        try:
            return round(float(amount) / 100000000, 2)
        except:
            return amount

    def _format_to_2_decimal(self, value):
        """保留2位小数"""
        if pd.isna(value):
            return value
        try:
            return round(float(value), 2)
        except:
            return value



    def _save_to_csv(self, df, filename, mode='w'):
        """
        保存到CSV文件
        mode='w': 覆盖写入
        mode='a': 追加写入
        """
        if df is not None and not df.empty:
            filepath = os.path.join(self.data_dir, filename)

            # 处理表头：追加模式下，如果文件不存在或为空，则写入表头
            header = True
            if mode == 'a':
                header = not os.path.exists(filepath) or os.path.getsize(filepath) == 0

            df.to_csv(filepath, mode=mode, header=header, index=False, encoding='utf-8-sig')

            action = "追加保存到" if mode == 'a' else "保存到"
            print(f"数据已{action}: {filepath}")
            return True
        else:
            print(f"数据为空，未保存: {filename}")
            return False

    def start_realtime_fetch(self):
        """
        启动实时数据自动获取
        - 每天首次运行时获取上一个交易日的龙虎榜数据（仅一次）
        - 固定在每小时的第0分、2分、4分...的第00秒自动获取实时数据，其他时间不获取
        """
        while True:
            try:

                # 获取今天的日期字符串
                today = self._get_today_date_str()
                current_dt = datetime.now()
                date_today = current_dt.strftime("%Y-%m-%d")
                date_three_days_ago = (current_dt - pd.Timedelta(days=3)).strftime("%Y-%m-%d")


                # # 每天第一次运行时，获取上一个交易日的龙虎榜数据（仅一次）
                # if self.last_lhb_fetch_date != today:
                #     print("\n【正在获取上一个交易日龙虎榜数据...】")
                #
                #     # 计算上一个交易日的日期
                #     previous_trading_day = (pd.Timestamp.now() - pd.Timedelta(days=1)).strftime("%Y%m%d")
                #     self.lhb(previous_trading_day, previous_trading_day)
                #
                #     # 标记今天已获取过龙虎榜数据
                #     self.last_lhb_fetch_date = today
                #     print(f"✅ 龙虎榜数据获取完成（日期: {previous_trading_day}）")

                if self.last_batch_lhb_fetch_date != today:
                    print("\n【正在批量下载龙虎榜详情...】")
                    print(f"日期范围: {date_three_days_ago} 至 {date_today}")

                    # 调用 batch_lhb，延时设为 1 秒，避免请求过快
                    self.batch_lhb(start_date=date_three_days_ago, end_date=date_today, delay_seconds=3)

                    # 标记今天已执行过批量下载
                    self.last_batch_lhb_fetch_date = today
                    print(f"✅ 龙虎榜详情批量下载完成")


            except KeyboardInterrupt:
                print("\n定时任务已停止")
                break
            except Exception as e:
                print(f"\n定时任务出错: {e}")




    def lhb_list(self, start_date: str, end_date: str):

        # 规范化日期格式
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        filename = f'lhb.csv'
        filepath = os.path.join(self.data_dir, filename)

        # ========== 1. 强制从网络获取新数据 ==========
        print(f"正在从网络获取 {start} 至 {end} 的龙虎榜数据...")
        try:
            df_raw = ak.stock_lhb_detail_em(start_date=start, end_date=end)
        except Exception as e:
            print(f"网络请求失败: {e}")
            # 如果网络完全失败，尝试返回本地现有数据（如果有）
            if os.path.exists(filepath):
                print(f"网络失败，返回本地缓存数据: {filepath}")
                return pd.read_csv(filepath)
            return None

        if df_raw is None or df_raw.empty:
            print(f"该日期范围网络无数据: {start} - {end}")
            # 如果网络无数据，尝试返回本地现有数据（如果有）
            if os.path.exists(filepath):
                return pd.read_csv(filepath)
            return None

        print(f"网络获取成功，新增 {len(df_raw)} 条记录")

        # ========== 2. 处理新数据格式 ==========
        df_new = df_raw.copy()

        # 重命名映射
        rename_map = {
            '上榜日': '上榜日',
            '代码': '代码',
            '名称': '名称',
            '收盘价': '收盘价',
            '涨跌幅': '涨跌幅',
            '净买额': '龙虎榜净买额',
            '买入金额': '龙虎榜买入额',
            '卖出金额': '龙虎榜卖出额',
            '成交金额': '龙虎榜成交额',
            '市场总成交': '市场总成交额',
            '换手率': '换手率',
            '流通市值': '流通市值',
            '解读': '解读',
            '上榜原因': '上榜原因'
        }

        # 过滤存在的列
        existing_cols = {old: new for old, new in rename_map.items() if old in df_new.columns}
        df_new = df_new.rename(columns=existing_cols)

        # 确保目标列存在，缺失则补 NA
        target_cols_basic = [
            '代码', '名称', '上榜日', '解读', '收盘价', '涨跌幅',
            '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜成交额',
            '市场总成交额', '换手率', '流通市值', '上榜原因'
        ]

        for col in target_cols_basic:
            if col not in df_new.columns:
                df_new[col] = pd.NA

        # 计算占比（转为亿元）
        df_new['龙虎榜净买额'] = pd.to_numeric(df_new['龙虎榜净买额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['龙虎榜成交额'] = pd.to_numeric(df_new['龙虎榜成交额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['市场总成交额'] = pd.to_numeric(df_new['市场总成交额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['龙虎榜买入额'] = pd.to_numeric(df_new['龙虎榜买入额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['龙虎榜卖出额'] = pd.to_numeric(df_new['龙虎榜卖出额'], errors='coerce').apply(self._format_amount_to_yi)
        df_new['流通市值'] = pd.to_numeric(df_new['流通市值'], errors='coerce').apply(self._format_amount_to_yi)

        df_new['净买额占总成交比'] = (df_new['龙虎榜净买额'] / df_new['市场总成交额']).apply(self._format_to_2_decimal)
        df_new['成交额占总成交比'] = (df_new['龙虎榜成交额'] / df_new['市场总成交额']).apply(self._format_to_2_decimal)

        # 数值列保留2位小数
        float_cols = ['收盘价', '涨跌幅', '换手率']
        for col in float_cols:
            if col in df_new.columns:
                df_new[col] = df_new[col].apply(self._format_to_2_decimal)

        # 最终列顺序
        final_cols = [
            '上榜日', '代码', '名称', '解读', '收盘价', '涨跌幅',
            '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜成交额',
            '市场总成交额', '净买额占总成交比', '成交额占总成交比',
            '换手率', '流通市值', '上榜原因'
        ]

        # 确保新数据只包含需要的列
        df_new = df_new[final_cols].copy()

        # ========== 3. 合并与去重逻辑（核心修复）==========
        df_final = df_new

        if os.path.exists(filepath):
            try:
                df_old = pd.read_csv(filepath, encoding='utf-8-sig')

                if not df_old.empty:
                    # 确保旧数据的列顺序和新数据一致，方便合并
                    # 补齐旧数据缺失的列
                    for col in final_cols:
                        if col not in df_old.columns:
                            df_old[col] = pd.NA
                    df_old = df_old[final_cols].copy()

                    print(f"本地存在旧数据 {len(df_old)} 条，正在合并...")

                    # 合并新旧数据
                    df_merged = pd.concat([df_old, df_new], ignore_index=True)

                    # 去重：基于 '上榜日' 和 '代码'
                    # keep='last' 表示如果有相同的“上榜日+代码”，保留最后出现的（即保留新的网络数据）
                    print(f"合并后共 {len(df_merged)} 条，正在去重...")
                    df_final = df_merged.drop_duplicates(subset=['上榜日', '代码'], keep='last')

                    print(f"去重后最终数据: {len(df_final)} 条")
            except Exception as e:
                print(f"读取本地数据出错: {e}，将只保存新数据")
                df_final = df_new

        # ========== 4. 保存 ==========
        self._save_to_csv(df_final, filename)
        return df_final



    def lhb_stock_detail(self, stock_code: str, date: str, flag: str = "买入", existing_detail_df=None):
        """
        个股龙虎榜详情
        保存到data/lhb_detail.csv（汇总文件）

        优化点：
        1. 新增参数 existing_detail_df：接收预先加载好的历史数据DataFrame，避免每次都读取文件。
        """
        # ========== 1. 输入参数标准化 ==========
        stock_code = str(stock_code).strip()

        # 处理带市场前缀的情况 (如 "0.000001" -> "000001")
        if '.' in stock_code:
            parts = stock_code.split('.')
            if len(parts) == 2:
                stock_code = parts[-1].zfill(6)
        else:
            stock_code = stock_code.zfill(6)
        # ========== 1. 结束 ==========

        clean_date = date.replace("-", "")
        filename = 'lhb_detail.csv'
        filepath = os.path.join(self.data_dir, filename)

        # ========== 2. 重复检查逻辑（优化核心）==========
        # 优先使用传入的 existing_detail_df（已过滤好的近3天数据）
        # 如果没有传入，则回退到原有的读取全量文件逻辑
        df_to_check = existing_detail_df

        if df_to_check is None:
            if os.path.exists(filepath):
                try:
                    if os.path.getsize(filepath) > 0:
                        df_to_check = pd.read_csv(filepath, encoding='utf-8-sig')
                        # 关键修复：标准化现有数据的格式
                        if '代码' in df_to_check.columns:
                            df_to_check['代码'] = df_to_check['代码'].astype(str).str.zfill(6)
                        if '上榜日' in df_to_check.columns:
                            df_to_check['上榜日'] = df_to_check['上榜日'].astype(str).str.replace("-", "")
                except Exception as e:
                    print(f"⚠️ 检查现有数据时出错: {e}，将重新获取")
                    df_to_check = None

        # 执行查重
        if df_to_check is not None and not df_to_check.empty:
            if '上榜日' in df_to_check.columns and '代码' in df_to_check.columns and 'flag' in df_to_check.columns:
                duplicate_mask = (
                        (df_to_check['上榜日'] == clean_date) &
                        (df_to_check['代码'] == stock_code) &
                        (df_to_check['flag'] == flag)
                )

                if duplicate_mask.any():
                    print(f"数据已经存在，进行下一条的处理: {stock_code} {clean_date} {flag}")
                    return False  # 返回 False 表示跳过
        # ========== 2. 检查结束 ==========

        try:
            if flag not in ["买入", "卖出"]:
                raise ValueError("flag 必须为 '买入' 或 '卖出'")

            df_raw = ak.stock_lhb_stock_detail_em(symbol=stock_code, date=clean_date, flag=flag)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # ========== 在最前面插入三列 ==========
                df.insert(0, '上榜日', clean_date)
                df.insert(1, '代码', stock_code)
                df.insert(2, 'flag', flag)

                # 列名模糊匹配与数据处理（保持原逻辑不变）
                buy_amt_col = next((col for col in df.columns if '买入金额' in col and '比例' not in col), None)
                buy_ratio_col = next(
                    (col for col in df.columns if '买入金额' in col and ('比例' in col or '比' in col)), None)
                sell_amt_col = next((col for col in df.columns if '卖出金额' in col and '比例' not in col), None)
                sell_ratio_col = next(
                    (col for col in df.columns if '卖出金额' in col and ('比例' in col or '比' in col)), None)
                net_col = next((col for col in df.columns if
                                any(kw in col for kw in ['净额', '净买', '净卖', '净买入', '净卖出'])), None)

                if buy_amt_col:
                    df[buy_amt_col] = df[buy_amt_col].apply(self._format_amount_to_yi)
                    df.rename(columns={buy_amt_col: '买入金额(亿)'}, inplace=True)

                if buy_ratio_col:
                    s = df[buy_ratio_col].astype(str).str.replace('%', '', regex=False)
                    df[buy_ratio_col] = pd.to_numeric(s, errors='coerce')
                    if df[buy_ratio_col].max() > 1:
                        df[buy_ratio_col] = (df[buy_ratio_col] / 100).apply(self._format_to_2_decimal)
                    else:
                        df[buy_ratio_col] = df[buy_ratio_col].apply(self._format_to_2_decimal)
                    df.rename(columns={buy_ratio_col: '买入占比'}, inplace=True)

                if sell_amt_col:
                    df[sell_amt_col] = df[sell_amt_col].apply(self._format_amount_to_yi)
                    df.rename(columns={sell_amt_col: '卖出金额(亿)'}, inplace=True)

                if sell_ratio_col:
                    s = df[sell_ratio_col].astype(str).str.replace('%', '', regex=False)
                    df[sell_ratio_col] = pd.to_numeric(s, errors='coerce')
                    if df[sell_ratio_col].max() > 1:
                        df[sell_ratio_col] = (df[sell_ratio_col] / 100).apply(self._format_to_2_decimal)
                    else:
                        df[sell_ratio_col] = df[sell_ratio_col].apply(self._format_to_2_decimal)
                    df.rename(columns={sell_ratio_col: '卖出占比'}, inplace=True)

                if net_col:
                    df[net_col] = df[net_col].apply(self._format_amount_to_yi)
                    df.rename(columns={net_col: '净额(亿)'}, inplace=True)

                # ========== 保存到统一文件 ==========
                if os.path.exists(filepath):
                    existing_df_file = pd.read_csv(filepath, encoding='utf-8-sig')
                    combined_df = pd.concat([existing_df_file, df], ignore_index=True)
                    combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')
                else:
                    self._save_to_csv(df, filename)

                return df
            else:
                print(f"无数据: {stock_code} {clean_date} {flag}")
                return None
        except Exception as e:
            print(f"❌ 获取或处理个股龙虎榜详情失败 ({stock_code}, {date}, flag): {e}")
            import traceback
            traceback.print_exc()
        return None

    def batch_lhb(self, start_date: str, end_date: str, delay_seconds: float = 1.0):
        """
        批量下载龙虎榜详情数据

        优化：
        1. 在循环开始前，一次性读取并过滤 lhb_detail.csv，只保留 start_date 至 end_date 范围内的数据。
        2. 将过滤后的 DataFrame 传递给 lhb_stock_detail，避免重复读取文件和全量查重。
        3. 【核心修复】：过滤 lhb_list 返回的总表数据，只处理指定上榜日范围内的记录，避免处理历史旧数据。
        """
        print(f"【步骤1】正在获取龙虎榜总表: {start_date} 至 {end_date} ...")

        # 1. 先执行 lhb_list 获取总表
        df_list = self.lhb_list(start_date, end_date)

        if df_list is None or df_list.empty:
            print("❌ 龙虎榜总表为空或获取失败，无法继续下载详情")
            return

        # ========== 【新增修复】：过滤总表上榜日范围 ==========
        # 规范化日期字符串用于比较 (YYYYMMDD)
        clean_start_date = start_date.replace("-", "")
        clean_end_date = end_date.replace("-", "")

        # 确保 '上榜日' 列为标准字符串格式 (YYYYMMDD)
        if '上榜日' in df_list.columns:
            original_count = len(df_list)
            df_list['上榜日'] = df_list['上榜日'].astype(str).str.replace("-", "").str.strip()

            # 过滤：只保留在 start_date 和 end_date 之间的数据
            df_list = df_list[
                (df_list['上榜日'] >= clean_start_date) &
                (df_list['上榜日'] <= clean_end_date)
                ].copy()

            filtered_count = len(df_list)
            if original_count != filtered_count:
                print(
                    f"🔍 总表已过滤: 剔除了 {original_count - filtered_count} 条历史旧数据，仅保留 {filtered_count} 条 ({clean_start_date} 至 {clean_end_date})")
        # =================================================

        total_count = len(df_list)
        print(f"✅ 龙虎榜总表获取成功，共 {total_count} 条记录")
        print(f"【步骤2】开始遍历下载个股详情...")

        # ========== 步骤1.5 预加载并过滤历史详情数据 (保持原优化逻辑) ==========
        detail_cache_df = None
        detail_file_path = os.path.join(self.data_dir, 'lhb_detail.csv')

        if os.path.exists(detail_file_path) and os.path.getsize(detail_file_path) > 0:
            print(f"【步骤1.5】正在读取并过滤本地龙虎榜详情数据 ({clean_start_date} 至 {clean_end_date})...")
            try:
                temp_df = pd.read_csv(detail_file_path, encoding='utf-8-sig')

                # 应用与 lhb_stock_detail 中一致的格式化逻辑
                if '代码' in temp_df.columns:
                    temp_df['代码'] = temp_df['代码'].astype(str).str.zfill(6)
                if '上榜日' in temp_df.columns:
                    temp_df['上榜日'] = temp_df['上榜日'].astype(str).str.replace("-", "")

                # 确保上榜日列为字符串进行比较
                temp_df['上榜日'] = temp_df['上榜日'].astype(str)

                # 筛选在上榜日范围内的数据
                detail_cache_df = temp_df[
                    (temp_df['上榜日'] >= clean_start_date) &
                    (temp_df['上榜日'] <= clean_end_date)
                    ].copy()

                print(f"✅ 过滤后缓存数据: {len(detail_cache_df)} 条 (用于本次查重)")

            except Exception as e:
                print(f"⚠️ 读取缓存数据失败: {e}，将每次读取文件查重")
                detail_cache_df = None
        # ==========================================

        skipped_count = 0
        failed_count = 0
        success_count = 0

        # 2. 遍历总表 (此时 df_list 已经只包含指定日期范围的数据)
        for index, row in df_list.iterrows():
            code = row.get('代码')
            raw_date = row.get('上榜日')

            if pd.isna(code) or pd.isna(raw_date):
                skipped_count += 1
                print(f"⏭️  跳过 [{index + 1}/{total_count}] 数据无效")
                continue

            # 代码格式化
            code = str(code).strip()
            if '.' in code:
                parts = code.split('.')
                if len(parts) == 2:
                    code = parts[-1].zfill(6)
            else:
                code = code.zfill(6)

            if not code.isdigit() or len(code) != 6:
                skipped_count += 1
                print(f"⏭️  跳过 [{index + 1}/{total_count}] 股票代码格式错误: {code}")
                continue

            clean_date = str(raw_date).replace("-", "")
            print(f"⏳ 进度 [{index + 1}/{total_count}] 正在处理: {code} ({raw_date})")

            # 3. 先获取买入详情 (传入缓存的 detail_cache_df)
            try:
                result = self.lhb_stock_detail(stock_code=code, date=clean_date, flag="买入",
                                               existing_detail_df=detail_cache_df)

                if result is False:
                    pass  # 已存在，不延时
                else:
                    if result is not None:
                        success_count += 1
                        # 如果获取了新数据，追加到内存缓存中，保证本次循环内查重准确性
                        detail_cache_df = pd.concat([detail_cache_df, result], ignore_index=True)
                    time_module.sleep(delay_seconds)

            except Exception as e:
                failed_count += 1
                print(f"  ❌ {code} 买入详情获取失败: {e}")
                time_module.sleep(delay_seconds)

            # 4. 再获取卖出详情 (传入更新后的 detail_cache_df)
            try:
                result = self.lhb_stock_detail(stock_code=code, date=clean_date, flag="卖出",
                                               existing_detail_df=detail_cache_df)

                if result is False:
                    pass
                else:
                    if result is not None:
                        success_count += 1
                        # 追加到内存缓存
                        detail_cache_df = pd.concat([detail_cache_df, result], ignore_index=True)
                    time_module.sleep(delay_seconds)

            except Exception as e:
                failed_count += 1
                print(f"  ❌ {code} 卖出详情获取失败: {e}")
                time_module.sleep(delay_seconds)

        # 统计信息
        print(f"\n{'=' * 60}")
        print(f"📊 批量下载完成统计:")
        print(f"  总记录数: {total_count}")
        print(f"  跳过数量: {skipped_count}")
        print(f"  失败数量: {failed_count}")
        print(f"  成功获取: {success_count}")
        print(f"{'=' * 60}")
        print(f"✅ 所有龙虎榜详情批量下载完成！")



    # ================= 辅助方法：获取文件路径 =================
    def _get_filepath(self, filename):
        """获取文件的绝对路径"""
        return os.path.join(self.data_dir, filename)

    def _save_to_csv(self, df, filename, mode='w'):
        """
        保存到CSV文件
        mode='w': 覆盖写入
        mode='a': 追加写入
        """
        if df is not None and not df.empty:
            filepath = self._get_filepath(filename)

            # 处理表头：追加模式下，如果文件不存在或为空，则写入表头
            header = True
            if mode == 'a':
                header = not os.path.exists(filepath) or os.path.getsize(filepath) == 0

            df.to_csv(filepath, mode=mode, header=header, index=False, encoding='utf-8-sig')

            action = "追加保存到" if mode == 'a' else "保存到"
            print(f"数据已{action}: {filepath}")
            return True
        else:
            print(f"数据为空，未保存: {filename}")
            return False

    # ================= 第二步：转换 lhb_b.csv 格式 =================
    def convert_lhb_to_lhb_b(self):

        input_file = self._get_filepath('lhb.csv')
        output_file = self._get_filepath('lhb_b.csv')

        if not os.path.exists(input_file):
            print(f"❌ 未找到文件: {input_file}")
            return False

        try:
            # 读取 lhb_b.csv
            df = pd.read_csv(input_file, encoding='utf-8-sig')

            # 1. 转换日期格式 (2026-01-30 00:00:00 -> 2026-01-30)
            if '上榜日' in df.columns:
                # 先转为 datetime 以处理各种格式，再转为字符串 YYYY-MM-DD
                # 尝试处理带时间的字符串
                try:
                    # 如果包含空格，说明有时间
                    if df['上榜日'].dtype == 'object':
                        # 去除时间部分
                        df['上榜日'] = df['上榜日'].str.split(' ')[0]
                except:
                    pass

                # 转换为标准日期字符串
                df['上榜日'] = pd.to_datetime(df['上榜日']).dt.strftime('%Y-%m-%d')

            # 2. 代码补足 6位
            if '代码' in df.columns:
                df['代码'] = df['代码'].astype(str).str.zfill(6)

            # 3. 按上榜日降序排序
            df = df.sort_values(by='上榜日', ascending=False)

            # 保存到 lhb_b.csv
            self._save_to_csv(df, 'lhb_b.csv', mode='w')

            print(f"✅ lhb_b.csv 格式转换完成，保存到: {output_file}")

            return df
        except Exception as e:
            print(f"❌ 转换 lhb_b.csv 失败: {e}")
            return None

    # ================= 第三步：转换 lhb_detail_b.csv 格式 =================
    def convert_lhb_detail_to_lhb_detail_b(self):
        input_file = self._get_filepath('lhb_detail.csv')
        output_file = self._get_filepath('lhb_detail_b.csv')
        if not os.path.exists(input_file):
            print(f"❌ 未找到文件: {input_file}")
            return False
        try:
            # 读取源文件（假设有表头）
            df = pd.read_csv(input_file, encoding='utf-8-sig')

            # === 1. 转换 上榜日 格式：20260105 → 2026-01-05 ===
            if '上榜日' in df.columns:
                s = df['上榜日'].astype(str).str.strip()
                mask_8digit = (s.str.len() == 8) & (s.str.isdigit())
                s.loc[mask_8digit] = s.loc[mask_8digit].str[:4] + '-' + s.loc[mask_8digit].str[4:6] + '-' + s.loc[
                    mask_8digit].str[6:8]
                df['上榜日'] = s

            # === 2. 确保代码为 6 位字符串 ===
            if '代码' in df.columns:
                df['代码'] = df['代码'].astype(str).str.zfill(6)

            # === 3. 缩写“交易营业部名称” ===
            def shorten_yyb_name(name):
                if pd.isna(name) or name == '' or str(name).lower() == 'nan':
                    return ''
                s = str(name).strip()
                # 特例优先

                s = s.replace('证券股份有限公司', 'a')
                s = s.replace('证券有限责任公司', 'c')
                s = s.replace('证券有限公司', 'b')
                s = s.replace('证券营业部', 'f')
                return s

            # 在 convert 函数中：
            if '交易营业部名称' in df.columns:
                df['交易营业部名称'] = df['交易营业部名称'].apply(shorten_yyb_name)

            # === 4. 排序并保存 ===
            df = df.sort_values(by='上榜日', ascending=False)
            self._save_to_csv(df, 'lhb_detail_b.csv', mode='w')
            print(f"✅ lhb_detail_b.csv 格式转换完成，保存到: {output_file}")
            return df

        except Exception as e:
            print(f"❌ 转换 lhb_detail_b.csv 失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    # ================= 第四步：提取并保存营业部数据 =================
    def extract_and_save_yyb(self):

        input_file = self._get_filepath('lhb_detail_b.csv')
        output_file = self._get_filepath('yyb.csv')

        if not os.path.exists(input_file):
            print(f"❌ 未找到文件: {input_file}")
            return False

        try:
            print("🔄 正在从 lhb_detail_b.csv 提取营业部数据...")

            # 读取数据
            # 注意：使用正确的列名
            df = pd.read_csv(input_file, encoding='utf-8-sig')

            # 获取交易营业部名称
            if '交易营业部名称' in df.columns:
                df['交易营业部名称'] = df['交易营业部名称'].astype(str).str.strip()

                # 提取并去重营业部名称
                yyb_names = df['交易营业部名称'].dropna().drop_duplicates()
                yyb_names = yyb_names[yyb_names.str.strip() != '']
                yyb_names = yyb_names.str.strip().tolist()

                print(f"📊 从详情数据中提取到 {len(yyb_names)} 个唯一营业部名称")
            else:
                print(f"❌ lhb_detail_b.csv 中未找到 '交易营业部名称' 列！")
                return False

            # 读取现有的 yyb.csv
            existing_yyb = []
            if os.path.exists(output_file):
                try:
                    df_existing = pd.read_csv(output_file, encoding='utf-8-sig')
                    # 检查是否有'交易营业部名称'列
                    if '交易营业部名称' in df_existing.columns:
                        existing_yyb = df_existing['交易营业部名称'].dropna().drop_duplicates().tolist()
                        existing_yyb = [name.strip() for name in existing_yyb if name.strip()]
                        print(f"📂 已有营业部数据库包含 {len(existing_yyb)} 个营业部")
                except Exception as e:
                    print(f"⚠️ 读取现有营业部数据库失败: {e}")

            # 找出新增的营业部
            # 注意：比较时需要用缩写后的名称
            # 1. 对现有数据取缩写
            existing_abbv_names = [self._abbreviate_yyb_name(name) for name in existing_yyb]

            # 2. 对新数据取缩写
            new_yyb_full = [name for name in yyb_names if
                            name not in existing_yyb and
                            self._abbreviate_yyb_name(name) not in existing_abbv_names]

            if not new_yyb_full:
                print("营业部数据已是最新！")
                return True

            print(f"➕ 发现 {len(new_yyb_full)} 个新营业部")

            # 3. 构造新增数据
            # 使用缩写名称
            new_data_list = []
            for name in new_yyb_full:
                abbv_name = self._abbreviate_yyb_name(name)
                new_data_list.append({
                    '交易营业部名称': abbv_name,
                    '大类': '',  # 大类默认为空
                    '别名': ''  # 别名默认为空
                })

            new_data = pd.DataFrame(new_data_list)

            # 4. 追加到 yyb.csv
            # 如果文件不存在，则创建新文件；如果存在，则追加（不包含表头）
            header = not os.path.exists(output_file)
            new_data.to_csv(output_file, mode='a', header=header, index=False, encoding='utf-8-sig')

            # 5. 显示结果
            total_count = len(existing_yyb) + len(new_yyb_full)
            msg = f"""✅ 营业部数据更新成功！

                        ━━━━━━━━━━━━━━━━
                        新增营业部数量: {len(new_yyb_full)}
                        当前总营业部数: {total_count}
                        ━━━━━━━━━━━━━━━━━

                        新增的营业部（前10个）：
                        {chr(10).join(new_yyb_full[:10])}
                        {f'... 还有 {len(new_yyb_full) - 10} 个' if len(new_yyb_full) > 10 else ''}

                        """
            # 注意：这里不能直接用 QMessageBox，因为这不是 UI 类
            print(msg)
            # 如果要在类中使用 QMessageBox，需要传入 parent 参数

            print(f"✅ 成功追加 {len(new_yyb_full)} 个新营业部到 {output_file}")

        except Exception as e:
            print(f"❌ 提取营业部数据失败: {e}")
            return False




if __name__ == '__main__':
    # 示例1：初始化并单次获取数据
    dh = data_his()
    dh.start_realtime_fetch(interval_minutes=2)
