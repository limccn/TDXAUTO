import pandas as pd
import akshare as ak
import os
from datetime import datetime, time
import time as time_module
import time as tm

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

    def _is_trading_time(self):
        """判断是否在交易时间：09:30-11:30 和 13:00-15:00"""
        now = datetime.now().time()
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)

        return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

    def _is_close_to_market_close(self):
        """判断是否接近15点收盘（用于保存日线数据）"""
        now = datetime.now()
        now_time = now.time()
        market_close = time(15, 0)
        # 14:58之后认为接近收盘，或者已经是15点
        market_close_early = time(14, 58)

        return now_time >= market_close_early or now_time >= market_close


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

    def _save_to_csv(self, df, filename):
        """保存到CSV文件"""
        if df is not None and not df.empty:
            filepath = os.path.join(self.data_dir, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"数据已保存到: {filepath}")
            return True
        else:
            print(f"数据为空，未保存: {filename}")
            return False

    def _save_as_daily(self, df, base_filename):
        """保存日线数据（在收盘时调用）"""
        if df is not None and not df.empty:
            today = self._get_today_date_str()
            # 分离文件名和扩展名
            name, ext = os.path.splitext(base_filename)
            # 构造日线文件名：base_name_YYYYMMDD.csv
            daily_filename = f"{name}_{today}{ext}"

            filepath = os.path.join(self.data_dir, daily_filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"日线数据已保存到: {filepath}")
            return True
        else:
            print(f"数据为空，未保存日线: {base_filename}")
            return False

    def _check_file_today_exists(self, filename):
        """检查今天的文件是否已经存在（用于历史数据，每天只获取一次）"""
        today = self._get_today_date_str()
        base_name = os.path.splitext(filename)[0]
        today_filename = f"{base_name}_{today}.csv"
        filepath = os.path.join(self.data_dir, today_filename)
        return os.path.exists(filepath)


    def start_realtime_fetch(self, interval_minutes=3):
        """
        启动实时数据自动获取
        在交易时段每3分钟自动获取实时数据，其他时间不获取
        """
        while True:
            try:
                now = datetime.now()
                print(f"\n{'=' * 60}")
                print(f"定时获取: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'=' * 60}")

                # 在交易时段获取所有实时数据
                if self._is_trading_time():
                    print("\n【正在获取实时数据...】")

                    self.stock_list_today()
                    self.stock_fund_today()
                    self.stock_fund_3day()
                    self.index_sh()
                    self.sector()
                    self.gn_blk()
                    self.gn_fund()
                    self.stock_zt()
                    self.stock_zt_pre()
                    self.stock_dt()
                    self.stock_zt_not()
                    self.blk_fund_3d()

                    print("\n【实时数据获取完成】")
                else:
                    print("\n非交易时间，暂不获取实时数据")

                # 等待下一次获取
                sleep_seconds = interval_minutes * 60
                print(f"\n等待 {interval_minutes} 分钟后再次检查...")
                time_module.sleep(sleep_seconds)

            except KeyboardInterrupt:
                print("\n定时任务已停止")
                break
            except Exception as e:
                print(f"\n定时任务出错: {e}")
                time_module.sleep(60)  # 出错后等待1分钟再继续





    # 实时数据函数（交易时段每3分钟自动获取，其他时间强制请求时获取）

    def stock_list_today(self, force_fetch=False):
        """
        实时行情数据-东财目标地址: https://quote.eastmoney.com/center/gridlist.html#hs_a_board
        保存到data/stocks_data.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取股票实时行情数据")
                return None

        try:
            stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
            if stock_zh_a_spot_em_df is not None and not stock_zh_a_spot_em_df.empty:
                df = stock_zh_a_spot_em_df.copy()

                # 处理金额列（转为亿元）
                amount_cols = ['成交额', '总市值', '流通市值']
                for col in amount_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_amount_to_yi)

                # 小数保留2位
                float_cols = ['最新价', '涨跌幅', '涨跌额', '今开', '最高', '最低', '昨收', '量比', '换手率', '振幅']
                for col in float_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)

                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据
                self._save_to_csv(df, 'stocks_data.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'stocks_data.csv')

                return df
        except Exception as e:
            print(f"获取实时行情数据失败: {e}")
        return None

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

                # 保存分时数据
                self._save_to_csv(df, 'funds_data.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'funds_data.csv')

                return df
        except Exception as e:
            print(f"获取实时资金流入数据失败: {e}")
        return None

    def stock_fund_3day(self, force_fetch=False):
        """
        用于快速查询3天实时资金流入
        保存到data/funds_3day.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取3日资金流向数据")
                return None

        try:
            stock_individual_fund_flow_rank_df = ak.stock_individual_fund_flow_rank(indicator="3日")
            if stock_individual_fund_flow_rank_df is not None and not stock_individual_fund_flow_rank_df.empty:
                df = stock_individual_fund_flow_rank_df.copy()

                # 处理金额列（转为亿元）
                if '3日主力净流入-净额' in df.columns:
                    df['3日主力净流入-净额'] = df['3日主力净流入-净额'].apply(self._format_amount_to_yi)
                elif '今日主力净流入-净额' in df.columns:
                    df['今日主力净流入-净额'] = df['今日主力净流入-净额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                if '3日主力净流入-净占比' in df.columns:
                    df['3日主力净流入-净占比'] = df['3日主力净流入-净占比'].apply(self._format_to_2_decimal)
                elif '今日主力净流入-净占比' in df.columns:
                    df['今日主力净流入-净占比'] = df['今日主力净流入-净占比'].apply(self._format_to_2_decimal)

                self._save_to_csv(df, 'funds_3day.csv')
                return df
        except Exception as e:
            print(f"获取3日资金流入数据失败: {e}")
        return None

    def index_sh(self, force_fetch=False):
        """
        上证深证实时点数
        保存到data/index_sh.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取指数实时数据")
                return None

        try:
            stock_market_fund_flow_df = ak.stock_market_fund_flow()
            if stock_market_fund_flow_df is not None and not stock_market_fund_flow_df.empty:
                df = stock_market_fund_flow_df.copy()

                # 处理金额列（转为亿元）
                if '主力净流入-净额' in df.columns:
                    df['主力净流入-净额'] = df['主力净流入-净额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                if '主力净流入-净占比' in df.columns:
                    df['主力净流入-净占比'] = df['主力净流入-净占比'].apply(self._format_to_2_decimal)

                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据
                self._save_to_csv(df, 'index_sh.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'index_sh.csv')

                return df
        except Exception as e:
            print(f"获取指数实时数据失败: {e}")
        return None

    def sector(self, force_fetch=False):
        """
        行业板块资金实时 https://data.eastmoney.com/bkzj/hy.html
        保存到data/sector_fund.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取行业板块资金数据")
                return None

        try:
            stock_sector_fund_flow_rank_df = ak.stock_sector_fund_flow_rank(
                indicator="今日",
                sector_type="行业资金流"
            )

            if stock_sector_fund_flow_rank_df is not None and not stock_sector_fund_flow_rank_df.empty:
                df = stock_sector_fund_flow_rank_df.copy()

                # 重命名列
                df.rename(columns={
                    '序号': '序号',
                    '名称': '名称',
                    '今日涨跌幅': '今日涨跌幅',
                    '今日主力净流入-净额': '主力净额',
                    '今日主力净流入-净占比': '净占比',
                    '今日主力净流入最大股': '代表个股'
                }, inplace=True)

                # 选择需要的列
                result_df = df[['序号', '名称', '今日涨跌幅', '主力净额', '净占比', '代表个股']].copy()

                # 将主力净流入换算成亿元
                if '主力净额' in result_df.columns:
                    result_df['主力净额'] = result_df['主力净额'].apply(self._format_amount_to_yi)

                # 涨跌幅保留2位小数
                if '今日涨跌幅' in result_df.columns:
                    result_df['今日涨跌幅'] = result_df['今日涨跌幅'].apply(self._format_to_2_decimal)

                # 净占比保留2位小数
                if '净占比' in result_df.columns:
                    result_df['净占比'] = result_df['净占比'].apply(self._format_to_2_decimal)

                self._save_to_csv(result_df, 'sector_fund.csv')
                return result_df
        except Exception as e:
            print(f"获取行业资金流向数据失败: {e}")
        return None

    def sector_stock(self, gn_blk="电源设备", force_fetch=False):
        """
        板块内实时个股
        保存到data/sector_{gn_blk}.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取板块个股数据")
                return None

        try:
            stock_sector_fund_flow_summary_df = ak.stock_sector_fund_flow_summary(symbol=gn_blk, indicator="今日")

            if stock_sector_fund_flow_summary_df is not None and not stock_sector_fund_flow_summary_df.empty:
                df = stock_sector_fund_flow_summary_df.copy()

                # 重命名列
                df.rename(columns={
                    '今日主力净流入-净额': '主力净额',
                    '今日主力净流入-净占比': '净占比'
                }, inplace=True)

                # 选择需要的列
                result_df = df[['序号', '代码', '名称', '最新价', '今天涨跌幅', '主力净额', '净占比']].copy()

                # 将主力净额换算成亿元
                if '主力净额' in result_df.columns:
                    result_df['主力净额'] = result_df['主力净额'].apply(self._format_amount_to_yi)

                # 涨跌幅保留2位小数
                if '今天涨跌幅' in result_df.columns:
                    result_df['今天涨跌幅'] = result_df['今天涨跌幅'].apply(self._format_to_2_decimal)

                # 净占比保留2位小数
                if '净占比' in result_df.columns:
                    result_df['净占比'] = result_df['净占比'].apply(self._format_to_2_decimal)

                filename = f'sector_{gn_blk}.csv'
                self._save_to_csv(result_df, filename)
                return result_df
        except Exception as e:
            print(f"获取板块个股资金流向数据失败: {e}")
        return None

    def gn_blk(self, force_fetch=False):
        """
        实时行情板块列表 https://quote.eastmoney.com/center/gridlist.html#concept_board
        保存到data/blk.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取概念板块列表")
                return None

        try:
            stock_board_concept_name_em_df = ak.stock_board_concept_name_em()

            if stock_board_concept_name_em_df is not None and not stock_board_concept_name_em_df.empty:
                df = stock_board_concept_name_em_df.copy()

                # 处理小数列
                if '涨跌幅' in df.columns:
                    df['涨跌幅'] = df['涨跌幅'].apply(self._format_to_2_decimal)
                if '换手率' in df.columns:
                    df['换手率'] = df['换手率'].apply(self._format_to_2_decimal)


                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据
                self._save_to_csv(df, 'blk.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'blk.csv')

                return df
        except Exception as e:
            print(f"获取概念板块列表失败: {e}")
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

                # 保存分时数据
                self._save_to_csv(df, 'blk_fund.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'blk_fund.csv')

                return df
        except Exception as e:
            print(f"获取概念板块资金失败: {e}")
        return None

    def gn_in_stock_fund(self, symbol="电源设备", force_fetch=False):
        """
        查询板块内的个股的资金
        保存到data/gn_{symbol}_fund.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取板块个股资金")
                return None

        try:
            stock_sector_fund_flow_summary_df = ak.stock_sector_fund_flow_summary(symbol=symbol, indicator="今日")

            if stock_sector_fund_flow_summary_df is not None and not stock_sector_fund_flow_summary_df.empty:
                df = stock_sector_fund_flow_summary_df.copy()

                # 处理金额列
                if '今日主力净流入-净额' in df.columns:
                    df['今日主力净流入-净额'] = df['今日主力净流入-净额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                if '今日主力净流入-净占比' in df.columns:
                    df['今日主力净流入-净占比'] = df['今日主力净流入-净占比'].apply(self._format_to_2_decimal)

                filename = f'gn_{symbol}_fund.csv'
                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取板块个股资金失败: {e}")
        return None

    def gn_detail(self, symbol="可燃冰", force_fetch=False):
        """
        具体概念的实时报价
        保存到data/gn_{symbol}_detail.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取概念板块详情")
                return None

        try:
            stock_board_concept_spot_em_df = ak.stock_board_concept_spot_em(symbol=symbol)

            if stock_board_concept_spot_em_df is not None and not stock_board_concept_spot_em_df.empty:
                df = stock_board_concept_spot_em_df.copy()

                # 处理金额列
                if '成交额' in df.columns:
                    df['成交额'] = df['成交额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                for col in ['最新价', '涨跌幅', '振幅', '最高', '最低', '今开', '昨收', '量比', '换手率']:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)

                filename = f'gn_{symbol}_detail.csv'
                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取概念板块详情失败: {e}")
        return None

    def gn_in_stock(self, gn_blk="可燃冰", force_fetch=False):
        """
        概念板块的成分股
        保存到data/gn_{gn_blk}_stocks.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取概念成分股")
                return None

        try:
            df = ak.stock_board_concept_cons_em(symbol=gn_blk)

            if df is not None and not df.empty:
                df = df.copy()

                # 1. 将成交额换算成亿元
                if '成交额' in df.columns:
                    df['成交额'] = df['成交额'].apply(self._format_amount_to_yi)

                # 2. 数值列保留2位小数
                cols_to_round = [
                    '最新价', '涨跌幅', '振幅', '最高', '最低', '今开', '昨收',
                    '量比', '换手率', '市盈率-动态', '市净率', '市盈率'
                ]
                for col in cols_to_round:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)

                # 3. 重命名列
                rename_map = {'量比': '最比'}
                if '市盈率-动态' in df.columns:
                    rename_map['市盈率-动态'] = '市盈率（动态）'
                elif '市盈率' in df.columns:
                    rename_map['市盈率'] = '市盈率（动态）'

                df.rename(columns=rename_map, inplace=True)

                # 4. 选择并排序列
                target_cols = [
                    '代码', '名称', '最新价', '涨跌幅', '振幅', '成交额',
                    '最高', '最低', '今开', '昨收', '最比', '换手率',
                    '市盈率（动态）', '市净率'
                ]

                available_cols = [col for col in target_cols if col in df.columns]
                result_df = df[available_cols].copy()

                filename = f'gn_{gn_blk}_stocks.csv'
                self._save_to_csv(result_df, filename)
                return result_df
        except Exception as e:
            print(f"获取概念成分股数据失败: {e}")
        return None

    def stock_zt(self, force_fetch=False):
        """
        获取涨停股票列表
        保存到data/zt.csv

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
                amount_cols = ['成交额', '流通市值', '总市值']
                for col in amount_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_amount_to_yi)

                pct_cols = ['涨跌幅', '换手率', '量比', '振幅', '流通市值占比', '年初至今涨跌幅', '5日涨跌幅']
                for col in pct_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)


                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据
                self._save_to_csv(df, 'zt.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'zt.csv')

                return df
        except Exception as e:
            print(f"获取涨停股票数据失败: {e}")
        return None

    def stock_zt_pre(self, force_fetch=False):
        """
        获取昨日涨停股票列表
        保存到data/zt_pre.csv

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

                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据
                self._save_to_csv(df, 'zt_pre.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'zt_pre.csv')

                return df
        except Exception as e:
            print(f"获取昨日涨停股票数据失败: {e}")
        return None

    def stock_dt(self, force_fetch=False):
        """
        获取跌停列表
        保存到data/dt.csv

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

                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据
                self._save_to_csv(df, 'dt.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'dt.csv')

                return df
        except Exception as e:
            print(f"获取跌停股票数据失败: {e}")
        return None

    def stock_zt_not(self, force_fetch=False):
        """
        获取炸板股票列表
        保存到data/zt_not.csv

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

                # ========== 新增：添加时间列 ==========
                current_time = self._get_now_time_str()
                df['时间'] = current_time

                # 保存分时数据
                self._save_to_csv(df, 'zt_not.csv')

                # ========== 新增：接近收盘时保存日线数据 ==========
                if self._is_close_to_market_close():
                    self._save_as_daily(df, 'zt_not.csv')

                return df
        except Exception as e:
            print(f"获取炸板股票数据失败: {e}")
        return None

    def blk_fund_3d(self, force_fetch=False):
        """
        3日行业资金流排名
        保存到data/blk_fund_3d.csv

        在交易时段每3分钟自动获取，其他时间只在force_fetch=True时获取
        """
        if not force_fetch:
            if not self._is_trading_time():
                print("非交易时间，不自动获取3日行业资金流")
                return None

        try:
            df_raw = ak.stock_sector_fund_flow_rank(indicator="3日", sector_type="行业资金流")

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # 将主力净流入金额转为亿元
                if '今日主力净流入-净额' in df.columns:
                    df['今日主力净流入-净额'] = df['今日主力净流入-净额'].apply(self._format_amount_to_yi)
                if '今日主力净流入-净占比' in df.columns:
                    df['今日主力净流入-净占比'] = df['今日主力净流入-净占比'].apply(self._format_to_2_decimal)

                self._save_to_csv(df, 'blk_fund_3d.csv')
                return df
        except Exception as e:
            print(f"获取3日行业资金流数据失败: {e}")
        return None

    # 历史数据函数（请求时才获取，每天只获取一次）

    def st_fund(self, stock_code, market):
        """
        单独个股的历史资金
        保存到data/stock_{stock_code}_fund_{YYYYMMDD}.csv
        每天只获取一次，检查存在就不再请求
        """
        filename = f'stock_{stock_code}_fund_{self._get_today_date_str()}.csv'

        # 检查今天是否已获取
        if self._check_file_today_exists(f'stock_{stock_code}_fund_XXXXXX.csv'):
            print(f"个股资金数据已存在: {filename}")
            filepath = os.path.join(self.data_dir, filename)
            return pd.read_csv(filepath)

        try:
            stock_individual_fund_flow_df = ak.stock_individual_fund_flow(stock=stock_code, market=market)

            if stock_individual_fund_flow_df is not None and not stock_individual_fund_flow_df.empty:
                df = stock_individual_fund_flow_df.copy()

                # 重命名列
                df.rename(columns={
                    '主力净流入-净额': '主力净额',
                    '主力净流入-净占比': '净占比'
                }, inplace=True)

                # 处理金额列（转为亿元）
                if '主力净额' in df.columns:
                    df['主力净额'] = df['主力净额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                if '净占比' in df.columns:
                    df['净占比'] = df['净占比'].apply(self._format_to_2_decimal)

                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取个股历史资金失败: {e}")
        return None

    def st_his(self, stock_code: str):
        """
        个股数据历史数据
        保存到data/stock_{stock_code}_{YYYYMMDD}.csv
        每天只获取一次，检查存在就不再请求
        """
        filename = f'stock_{stock_code}_{self._get_today_date_str()}.csv'

        # 检查今天是否已获取
        if self._check_file_today_exists(f'stock_{stock_code}_XXXXXX.csv'):
            print(f"个股历史数据已存在: {filename}")
            filepath = os.path.join(self.data_dir, filename)
            return pd.read_csv(filepath)

        # 自动判断市场
        if stock_code.startswith(("60", "68")):
            market = "sh"
        else:
            market = "sz"

        try:
            hist_df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )

            if hist_df is not None and not hist_df.empty:
                # 标准化列名
                hist_df.rename(columns={
                    '日期': '日期',
                    '开盘': '开盘',
                    '收盘': '收盘',
                    '最高': '最高',
                    '最低': '最低',
                    '成交量': '成交量',
                    '成交额': '成交额',
                    '振幅': '振幅',
                    '换手率': '换手率'
                }, inplace=True)

                # 计算量比
                hist_df['量比'] = (hist_df['成交量'] / hist_df['成交量'].shift(1)).round(2)

                # 将成交额换算成亿元
                if '成交额' in hist_df.columns:
                    hist_df['成交额'] = hist_df['成交额'].apply(self._format_amount_to_yi)

                # 换手率保留2位小数
                if '换手率' in hist_df.columns:
                    hist_df['换手率'] = hist_df['换手率'].apply(self._format_to_2_decimal)

                # 获取资金流数据
                try:
                    fund_df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
                    if fund_df is not None and not fund_df.empty:
                        fund_df.rename(columns={
                            '主力净流入-净额': '主力净额',
                            '主力净流入-净占比': '净占比'
                        }, inplace=True)

                        fund_df = fund_df[['日期', '主力净额', '净占比']].copy()

                        if '主力净额' in fund_df.columns:
                            fund_df['主力净额'] = fund_df['主力净额'].apply(self._format_amount_to_yi)
                        if '净占比' in fund_df.columns:
                            fund_df['净占比'] = fund_df['净占比'].apply(self._format_to_2_decimal)

                        # 合并数据
                        merged = pd.merge(hist_df, fund_df, on='日期', how='left')

                        # 添加股票代码列
                        merged['股票代码'] = stock_code
                        merged.rename(columns={'成交额': '成交额(亿)'}, inplace=True)

                        self._save_to_csv(merged, filename)
                        return merged
                except Exception as e:
                    print(f"获取个股资金流数据失败: {e}")
                    # 即使资金流失败，也保存K线数据
                    hist_df['股票代码'] = stock_code
                    hist_df.rename(columns={'成交额': '成交额(亿)'}, inplace=True)
                    self._save_to_csv(hist_df, filename)
                    return hist_df
        except Exception as e:
            print(f"获取K线数据失败: {e}")
        return None

    def index_volume(self):
        """
        获取上证指数历史成交量
        保存到data/index_sh_volume_{YYYYMMDD}.csv
        每天只获取一次，检查存在就不再请求
        """
        filename = f'index_sh_volume_{self._get_today_date_str()}.csv'

        # 检查今天是否已获取
        if self._check_file_today_exists('index_sh_volume_XXXXXX.csv'):
            print(f"指数历史数据已存在: {filename}")
            filepath = os.path.join(self.data_dir, filename)
            return pd.read_csv(filepath)

        try:
            df = ak.stock_zh_index_daily(symbol="sh000001")
            if df is not None and not df.empty:
                df.rename(columns={
                    'date': '日期',
                    'close': '收盘',
                    'volume': '成交量'
                }, inplace=True)

                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取指数成交量失败: {e}")
        return None

    def index_his(self):
        """
        获取大盘历史资金流向数据
        保存到data/index_fund_{YYYYMMDD}.csv
        每天只获取一次，检查存在就不再请求
        """
        filename = f'index_fund_{self._get_today_date_str()}.csv'

        # 检查今天是否已获取
        if self._check_file_today_exists('index_fund_XXXXXX.csv'):
            print(f"大盘历史资金流数据已存在: {filename}")
            filepath = os.path.join(self.data_dir, filename)
            return pd.read_csv(filepath)

        try:
            stock_market_fund_flow_df = ak.stock_market_fund_flow()

            if stock_market_fund_flow_df is not None and not stock_market_fund_flow_df.empty:
                # 重命名列
                rename_mapping = {}
                if '主力净流入-净额' in stock_market_fund_flow_df.columns:
                    rename_mapping['主力净流入-净额'] = '主力净额'
                if '主力净流入-净占比' in stock_market_fund_flow_df.columns:
                    rename_mapping['主力净流入-净占比'] = '净占比'
                if '上证-收盘价' in stock_market_fund_flow_df.columns:
                    rename_mapping['上证-收盘价'] = '上证'
                if '上证-涨跌幅' in stock_market_fund_flow_df.columns:
                    rename_mapping['上证-涨跌幅'] = '上证涨跌幅'

                if rename_mapping:
                    stock_market_fund_flow_df.rename(columns=rename_mapping, inplace=True)

                # 格式化 '主力净额' 列（转为亿元）
                if '主力净额' in stock_market_fund_flow_df.columns:
                    stock_market_fund_flow_df['主力净额'] = stock_market_fund_flow_df['主力净额'].apply(
                        self._format_amount_to_yi)

                # 格式化 '净占比' 列
                if '净占比' in stock_market_fund_flow_df.columns:
                    stock_market_fund_flow_df['净占比'] = stock_market_fund_flow_df['净占比'].apply(
                        self._format_to_2_decimal)

                self._save_to_csv(stock_market_fund_flow_df, filename)
                return stock_market_fund_flow_df
        except Exception as e:
            print(f"获取大盘历史资金流向数据失败: {e}")
        return None

    def sector_detail(self, symbol="汽车服务"):
        """
        具体板块历史
        保存到data/sector_{symbol}_{YYYYMMDD}.csv
        每天只获取一次，检查存在就不再请求
        """
        filename = f'sector_{symbol}_{self._get_today_date_str()}.csv'

        # 检查今天是否已获取
        if self._check_file_today_exists(f'sector_{symbol}_XXXXXX.csv'):
            print(f"板块历史数据已存在: {filename}")
            filepath = os.path.join(self.data_dir, filename)
            return pd.read_csv(filepath)

        try:
            stock_sector_fund_flow_hist_df = ak.stock_sector_fund_flow_hist(symbol=symbol)

            if stock_sector_fund_flow_hist_df is not None and not stock_sector_fund_flow_hist_df.empty:
                df = stock_sector_fund_flow_hist_df.copy()

                # 处理金额列（转为亿元）
                if '主力净流入-净额' in df.columns:
                    df['主力净流入-净额'] = df['主力净流入-净额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                if '主力净流入-净占比' in df.columns:
                    df['主力净流入-净占比'] = df['主力净流入-净占比'].apply(self._format_to_2_decimal)

                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取板块历史数据失败: {e}")
        return None

    def gn_fund_his(self, symbol="数据要素"):
        """
        获取概念板块历史资金流
        保存到data/gn_fund_{symbol}_{YYYYMMDD}.csv
        每天只获取一次，检查存在就不再请求
        """
        filename = f'gn_fund_{symbol}_{self._get_today_date_str()}.csv'

        # 检查今天是否已获取
        if self._check_file_today_exists(f'gn_fund_{symbol}_XXXXXX.csv'):
            print(f"概念板块历史资金流数据已存在: {filename}")
            filepath = os.path.join(self.data_dir, filename)
            return pd.read_csv(filepath)

        try:
            stock_concept_fund_flow_hist_df = ak.stock_concept_fund_flow_hist(symbol=symbol)

            if stock_concept_fund_flow_hist_df is not None and not stock_concept_fund_flow_hist_df.empty:
                df = stock_concept_fund_flow_hist_df.copy()

                # 处理金额列（转为亿元）
                if '主力净流入-净额' in df.columns:
                    df['主力净流入-净额'] = df['主力净流入-净额'].apply(self._format_amount_to_yi)

                # 小数保留2位
                if '主力净流入-净占比' in df.columns:
                    df['主力净流入-净占比'] = df['主力净流入-净占比'].apply(self._format_to_2_decimal)

                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取概念板块历史资金流失败: {e}")
        return None

    def gn_his(self, gn_blk="可燃冰", start_date="20251201", end_date="20280101"):
        """
        具体概念板块的历史数据（含资金流）
        保存到data/gn_{gn_blk}_his_{YYYYMMDD}.csv
        每天只获取一次，检查存在就不再请求
        """
        filename = f'gn_{gn_blk}_his_{self._get_today_date_str()}.csv'

        # 检查今天是否已获取
        if self._check_file_today_exists(f'gn_{gn_blk}_his_XXXXXX.csv'):
            print(f"概念板块历史数据已存在: {filename}")
            filepath = os.path.join(self.data_dir, filename)
            return pd.read_csv(filepath)

        try:
            # 获取行情数据
            stock_board_concept_hist_em_df = ak.stock_board_concept_hist_em(
                symbol=gn_blk,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )

            if stock_board_concept_hist_em_df is not None and not stock_board_concept_hist_em_df.empty:
                df_hist = stock_board_concept_hist_em_df.copy()
                df_hist['日期'] = pd.to_datetime(df_hist['日期'])

                # 获取资金流历史
                try:
                    fund_hist_df = ak.stock_concept_fund_flow_hist(symbol=gn_blk)
                    if fund_hist_df is not None and not fund_hist_df.empty:
                        fund_hist_df['日期'] = pd.to_datetime(fund_hist_df['日期'])

                        # 重命名列
                        rename_map = {}
                        if '主力净流入-净额' in fund_hist_df.columns:
                            rename_map['主力净流入-净额'] = '主力净额'
                        if '主力净流入-净占比' in fund_hist_df.columns:
                            rename_map['主力净流入-净占比'] = '净占比'

                        if rename_map:
                            fund_hist_df = fund_hist_df.rename(columns=rename_map)
                            needed_cols = ['日期'] + list(rename_map.values())
                            fund_hist_df = fund_hist_df[needed_cols].copy()

                            # 转换数值
                            if '主力净额' in fund_hist_df.columns:
                                fund_hist_df['主力净额'] = fund_hist_df['主力净额'].apply(self._format_amount_to_yi)
                            if '净占比' in fund_hist_df.columns:
                                fund_hist_df['净占比'] = fund_hist_df['净占比'].apply(self._format_to_2_decimal)

                            # 合并数据
                            merged_df = pd.merge(df_hist, fund_hist_df, on='日期', how='left')
                        else:
                            print(f"[WARNING] 资金流数据缺少所需列")
                            merged_df = df_hist
                    else:
                        print(f"[INFO] 无资金流历史数据")
                        merged_df = df_hist
                except Exception as e:
                    print(f"获取概念资金流历史失败: {e}")
                    merged_df = df_hist

                # 格式化成交额
                if '成交额' in merged_df.columns:
                    merged_df['成交额'] = merged_df['成交额'].apply(self._format_amount_to_yi)
                    merged_df.rename(columns={'成交额': '成交额(亿)'}, inplace=True)

                self._save_to_csv(merged_df, filename)
                return merged_df
        except Exception as e:
            print(f"获取概念板块 {gn_blk} 历史数据失败: {e}")
        return None

    def lhb(self, start_date: str, end_date: str):
        """
        统计一段时间的龙虎榜
        保存到data/lhb_{start_date}_{end_date}.csv
        每天只获取一次（针对相同的日期范围），检查存在就不再请求
        """
        # 规范化日期格式
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        filename = f'lhb_{start}_{end}.csv'

        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            print(f"龙虎榜数据已存在: {filename}")
            return pd.read_csv(filepath)

        try:
            df_raw = ak.stock_lhb_detail_em(start_date=start, end_date=end)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # 重命名映射
                rename_map = {
                    '代码': '代码',
                    '名称': '名称',
                    '日期': '上榜日',
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
                existing_cols = {old: new for old, new in rename_map.items() if old in df.columns}
                df = df.rename(columns=existing_cols)

                # 确保目标列存在，缺失则补 NA
                target_cols_basic = [
                    '代码', '名称', '上榜日', '解读', '收盘价', '涨跌幅',
                    '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜成交额',
                    '市场总成交额', '换手率', '流通市值', '上榜原因'
                ]

                for col in target_cols_basic:
                    if col not in df.columns:
                        df[col] = pd.NA

                # 计算占比（转为亿元）
                df['龙虎榜净买额'] = pd.to_numeric(df['龙虎榜净买额'], errors='coerce').apply(self._format_amount_to_yi)
                df['龙虎榜成交额'] = pd.to_numeric(df['龙虎榜成交额'], errors='coerce').apply(self._format_amount_to_yi)
                df['市场总成交额'] = pd.to_numeric(df['市场总成交额'], errors='coerce').apply(self._format_amount_to_yi)
                df['龙虎榜买入额'] = pd.to_numeric(df['龙虎榜买入额'], errors='coerce').apply(self._format_amount_to_yi)
                df['龙虎榜卖出额'] = pd.to_numeric(df['龙虎榜卖出额'], errors='coerce').apply(self._format_amount_to_yi)
                df['流通市值'] = pd.to_numeric(df['流通市值'], errors='coerce').apply(self._format_amount_to_yi)

                df['净买额占总成交比'] = (df['龙虎榜净买额'] / df['市场总成交额']).apply(self._format_to_2_decimal)
                df['成交额占总成交比'] = (df['龙虎榜成交额'] / df['市场总成交额']).apply(self._format_to_2_decimal)

                # 数值列保留2位小数
                float_cols = ['收盘价', '涨跌幅', '换手率']
                for col in float_cols:
                    if col in df.columns:
                        df[col] = df[col].apply(self._format_to_2_decimal)

                # 最终列顺序
                final_cols = [
                    '代码', '名称', '上榜日', '解读', '收盘价', '涨跌幅',
                    '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜成交额',
                    '市场总成交额', '净买额占总成交比', '成交额占总成交比',
                    '换手率', '流通市值', '上榜原因'
                ]

                result = df[final_cols].copy()
                self._save_to_csv(result, filename)
                return result
        except Exception as e:
            print(f"获取或处理龙虎榜数据失败: {e}")
        return None

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

    def lhb_stock_detail(self, stock_code: str, date: str, flag: str = "买入"):
        """
        个股龙虎榜详情
        保存到data/lhb_{stock_code}_{date}_{flag}.csv
        每天只获取一次，检查存在就不再请求
        """
        clean_date = date.replace("-", "")
        filename = f'lhb_{stock_code}_{clean_date}_{flag}.csv'

        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            print(f"个股龙虎榜详情数据已存在: {filename}")
            return pd.read_csv(filepath)

        try:
            if flag not in ["买入", "卖出"]:
                raise ValueError("flag 必须为 '买入' 或 '卖出'")

            df_raw = ak.stock_lhb_stock_detail_em(symbol=stock_code, date=clean_date, flag=flag)

            if df_raw is not None and not df_raw.empty:
                df = df_raw.copy()

                # 列名模糊匹配
                buy_amt_col = next((col for col in df.columns if '买入金额' in col and '比例' not in col), None)
                buy_ratio_col = next(
                    (col for col in df.columns if '买入金额' in col and ('比例' in col or '比' in col)), None)
                sell_amt_col = next((col for col in df.columns if '卖出金额' in col and '比例' not in col), None)
                sell_ratio_col = next(
                    (col for col in df.columns if '卖出金额' in col and ('比例' in col or '比' in col)), None)
                net_col = next((col for col in df.columns if
                                any(kw in col for kw in ['净额', '净买', '净卖', '净买入', '净卖出'])), None)

                # 处理买入金额（亿元）
                if buy_amt_col:
                    df[buy_amt_col] = df[buy_amt_col].apply(self._format_amount_to_yi)
                    df.rename(columns={buy_amt_col: '买入金额(亿)'}, inplace=True)

                # 处理买入比例
                if buy_ratio_col:
                    s = df[buy_ratio_col].astype(str).str.replace('%', '', regex=False)
                    df[buy_ratio_col] = pd.to_numeric(s, errors='coerce')
                    if df[buy_ratio_col].max() > 1:
                        df[buy_ratio_col] = (df[buy_ratio_col] / 100).apply(self._format_to_2_decimal)
                    else:
                        df[buy_ratio_col] = df[buy_ratio_col].apply(self._format_to_2_decimal)
                    df.rename(columns={buy_ratio_col: '买入占比'}, inplace=True)

                # 处理卖出金额（亿元）
                if sell_amt_col:
                    df[sell_amt_col] = df[sell_amt_col].apply(self._format_amount_to_yi)
                    df.rename(columns={sell_amt_col: '卖出金额(亿)'}, inplace=True)

                # 处理卖出比例
                if sell_ratio_col:
                    s = df[sell_ratio_col].astype(str).str.replace('%', '', regex=False)
                    df[sell_ratio_col] = pd.to_numeric(s, errors='coerce')
                    if df[sell_ratio_col].max() > 1:
                        df[sell_ratio_col] = (df[sell_ratio_col] / 100).apply(self._format_to_2_decimal)
                    else:
                        df[sell_ratio_col] = df[sell_ratio_col].apply(self._format_to_2_decimal)
                    df.rename(columns={sell_ratio_col: '卖出占比'}, inplace=True)

                # 处理净额（亿元）
                if net_col:
                    df[net_col] = df[net_col].apply(self._format_amount_to_yi)
                    df.rename(columns={net_col: '净额(亿)'}, inplace=True)

                self._save_to_csv(df, filename)
                return df
        except Exception as e:
            print(f"获取或处理个股龙虎榜详情失败 ({stock_code}, {date}, {flag}): {e}")
        return None



if __name__ == '__main__':
    # 示例1：初始化并单次获取数据
    dh = data_his()
    # #
    # # # 获取历史数据（每天只获取一次）
    # # print("获取历史数据...")
    # # df_st_his = dh.st_his("600094")
    # # print(df_st_his.head() if df_st_his is not None else "获取失败")
    # df = dh.st_his('300393')
    # print(df)



    # # 获取实时数据（交易时段外需要force_fetch=True）
    # print("\n获取实时数据（强制获取）...")
    # print("第一项：正在获取全市场股票列表")
    # df_stock_list = dh.stock_list_today(force_fetch=True)
    # print(df_stock_list.tail() if df_stock_list is not None else "全市场股票列表获取失败")
    # print("*"*50)
    # tm.sleep(2)
    # print("第二项：正在获取全市场资金流向")
    # df_stock_list = dh.stock_fund_today(force_fetch=True)
    # print(df_stock_list.tail() if df_stock_list is not None else "全市场资金流向获取失败")
    # print("*" * 50)
    # tm.sleep(2)
    # print("第三项：正在获取概念板块")
    # df_stock_list = dh.gn_blk(force_fetch=True)
    # print(df_stock_list.tail() if df_stock_list is not None else "概念板块 获取失败")
    # print("*" * 50)

    print("第四项：正在获取所有的概念板块资金流向")
    df_stock_list = dh.gn_fund(force_fetch=True)
    print(df_stock_list.tail() if df_stock_list is not None else "概念板块资金流向获取失败")
    print("*" * 50)
    # tm.sleep(2)
    # print("第五项：正在获取涨停池")
    # df_stock_list = dh.stock_zt(force_fetch=True)
    # print(df_stock_list.tail() if df_stock_list is not None else "涨停池获取失败")
    # print("*" * 50)
    # tm.sleep(2)
    # print("第六项：正在获取昨日涨停股")
    # df_stock_list = dh.stock_zt_pre(force_fetch=True)
    # print(df_stock_list.tail() if df_stock_list is not None else "昨天涨停股获取失败")
    # print("*" * 50)
    # tm.sleep(2)
    # print("第七项：正在获取跌停股")
    # df_stock_list = dh.stock_dt(force_fetch=True)
    # print(df_stock_list.tail() if df_stock_list is not None else "跌停股获取失败")
    # print("*" * 50)
    # tm.sleep(2)
    #
    # print("第八项：正在获取炸板股")
    # df_stock_list = dh.stock_zt_not(force_fetch=True)
    # print(df_stock_list.tail() if df_stock_list is not None else "炸板股获取失败")
    # tm.sleep(2)
    # print("第九项：正在获取上证实时指数与资金")
    # df_stock_list = dh.index_sh(force_fetch=True)
    # print(df_stock_list.tail() if df_stock_list is not None else "上证实时指数与资金获取失败")




    # 示例2：启动实时数据自动获取（在交易时段自动运行）
    # dh.start_realtime_fetch(interval_minutes=3)
