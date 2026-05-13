import pandas as pd
import akshare as ak

start_date: str = "20241201"
end_date: str = "20280101"


class data_his:

    def stock_list(self):
        """
        实时行情数据与资金流向排名合并
        """
        # 实时行情数据-东财目标地址: https://quote.eastmoney.com/center/gridlist.html#hs_a_board
        # 实时资金流入-东财目标地址: https://data.eastmoney.com/zjlx/detail.html

        # 1. 获取实时行情数据
        try:
            stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
            print("[DEBUG] 获取实时行情数据成功，形状:", stock_zh_a_spot_em_df.shape)
        except Exception as e:
            print(f"[ERROR] 获取实时行情数据失败: {e}")
            return None

        # 2. 获取资金流向排名数据
        try:
            stock_individual_fund_flow_rank_df = ak.stock_individual_fund_flow_rank(indicator="今日")
            print("[DEBUG] 获取资金流向排名数据成功，形状:", stock_individual_fund_flow_rank_df.shape)
        except Exception as e:
            print(f"[ERROR] 获取资金流向排名数据失败: {e}")
            return None

        # 3. 检查数据是否为空
        if stock_zh_a_spot_em_df is None or stock_zh_a_spot_em_df.empty:
            print("[WARNING] 实时行情数据为空")
            return None
        if stock_individual_fund_flow_rank_df is None or stock_individual_fund_flow_rank_df.empty:
            print("[WARNING] 资金流向排名数据为空")
            return None

        # 4. 从资金流向数据中选取所需列，并复制以避免 SettingWithCopyWarning
        # 注意：这里假设原始列名为 '今日主力净流入-净额' 和 '今日主力净流入-净占比'
        # 请根据实际接口返回的列名进行调整
        fund_cols_needed = ['代码', '今日主力净流入-净额', '今日主力净流入-净占比']
        available_fund_cols = [col for col in fund_cols_needed if col in stock_individual_fund_flow_rank_df.columns]
        print(f"[DEBUG] 资金流向数据中找到的列: {available_fund_cols}")

        if not available_fund_cols or len(available_fund_cols) < 3:
             print(f"[WARNING] 资金流向数据中缺少必要的列，仅找到: {available_fund_cols}")
             # 即使列不全，也尝试合并，缺失的列将在结果中为 NaN
             fund_df_to_merge = stock_individual_fund_flow_rank_df[fund_cols_needed[:1]].copy() # 至少保留代码列用于合并
        else:
            fund_df_to_merge = stock_individual_fund_flow_rank_df[available_fund_cols].copy()

        # 5. 确保用于合并的列名一致
        # 实时行情表通常有 '代码' 列，资金流向排名表也应有 '代码' 列，所以直接使用 '代码' 作为合并键
        # 如果实时行情表的列名不同（例如 '证券代码'），则需要先重命名
        # 这里假设都叫 '代码'
        spot_df = stock_zh_a_spot_em_df.copy()

        # 6. 合并数据，以实时行情数据为主（left join）
        # left join 会保留所有行情数据的记录，即使该股票在资金流排名中没有记录
        merged_df = pd.merge(spot_df, fund_df_to_merge, on='代码', how='left')

        # 7. 数据格式化
        # 将资金流数据中的金额列转为亿元，并保留两位小数
        fund_amount_col = '今日主力净流入-净额'
        fund_ratio_col = '今日主力净流入-净占比'

        if fund_amount_col in merged_df.columns:
            merged_df[fund_amount_col] = pd.to_numeric(merged_df[fund_amount_col], errors='coerce')
            merged_df[fund_amount_col] = (merged_df[fund_amount_col] / 100000000).round(2)

        if fund_ratio_col in merged_df.columns:
            merged_df[fund_ratio_col] = pd.to_numeric(merged_df[fund_ratio_col], errors='coerce')
            # 假设净占比已经是小数形式，如 0.0523 代表 5.23%
            # 如果原始是百分比数字（如 5.23），则需要除以 100
            # if merged_df[fund_ratio_col].abs().max() > 1: # 如果最大值大于1，可能是百分比数字
            #     merged_df[fund_ratio_col] = (merged_df[fund_ratio_col] / 100).round(4)
            merged_df[fund_ratio_col] = merged_df[fund_ratio_col].round(4) # 保留4位小数更精确


        print(f"[DEBUG] 合并完成，最终数据形状: {merged_df.shape}")
        # 如果你想看到合并后的部分数据，可以取消下面一行的注释
        # print(merged_df.head())

        # 返回合并后的完整DataFrame
        return merged_df

    def stock_his(self, stock_code: str):
        # 个股数据历史数据
        # 自动判断市场
        if stock_code.startswith(("60", "68")):
            market = "sh"
        else:
            market = "sz"

        # 获取K线历史数据（包含开盘、收盘、最高、最低、成交量、成交额、振幅、换手率）
        try:
            hist_df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )
        except Exception as e:
            print(f"获取K线数据失败: {e}")
            return None



        # 获取资金流数据
        try:
            fund_df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
        except Exception as e:
            print(f"获取资金流数据失败: {e}")
            return None



    def index_sh(self):  # 实时指数，主力净额上证
        try:
            stock_market_fund_flow_df = ak.stock_market_fund_flow()

            if stock_market_fund_flow_df is None or stock_market_fund_flow_df.empty:
                print("未获取到大盘资金流向数据")
                return None

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
            if '深证-收盘价' in stock_market_fund_flow_df.columns:
                rename_mapping['深证-收盘价'] = '深证'
            if '深证-涨跌幅' in stock_market_fund_flow_df.columns:
                rename_mapping['深证-涨跌幅'] = '深证涨幅'
            if '日期' in stock_market_fund_flow_df.columns:
                rename_mapping['日期'] = '日期'

            if rename_mapping:
                stock_market_fund_flow_df.rename(columns=rename_mapping, inplace=True)

            # 将主力净额换算成亿元，保留2位小数
            if '主力净额' in stock_market_fund_flow_df.columns:
                stock_market_fund_flow_df['主力净额'] = (
                        stock_market_fund_flow_df['主力净额'] / 100000000
                ).round(2)

            # 涨跌幅保留2位小数
            if '上证涨跌幅' in stock_market_fund_flow_df.columns:
                stock_market_fund_flow_df['上证涨跌幅'] = stock_market_fund_flow_df['上证涨跌幅'].round(2)
            if '深证涨幅' in stock_market_fund_flow_df.columns:
                stock_market_fund_flow_df['深证涨幅'] = stock_market_fund_flow_df['深证涨幅'].round(2)
            if '净占比' in stock_market_fund_flow_df.columns:
                stock_market_fund_flow_df['净占比'] = stock_market_fund_flow_df['净占比'].round(2)

            # 选择需要的列
            result_df = stock_market_fund_flow_df[[
                '日期', '上证', '上证涨跌幅', '深证', '深证涨幅', '主力净额', '净占比'
            ]].copy()

            return result_df

        except Exception as e:
            print(f"获取大盘资金流向数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    # 在 ak_data.py 中添加
    def index_volume(self):
        """获取上证指数历史成交量"""
        try:
            # 获取上证指数历史行情
            df = ak.stock_zh_index_daily(symbol="sh000001")
            if df is not None and not df.empty:
                df.rename(columns={
                    'date': '日期',
                    'close': '收盘',
                    'volume': '成交量'
                }, inplace=True)
                return df
            return None
        except Exception as e:
            print(f"获取指数成交量失败: {e}")
            return None

    def index_his(self):
        """
        获取大盘历史资金流向数据
        """
        try:
            stock_market_fund_flow_df = ak.stock_market_fund_flow()

            if stock_market_fund_flow_df is None or stock_market_fund_flow_df.empty:
                print("未能获取到大盘历史资金流向数据或数据为空。")
                return None  # ← 添加返回值

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
                stock_market_fund_flow_df['主力净额'] = (
                        pd.to_numeric(stock_market_fund_flow_df['主力净额'], errors='coerce') / 100000000
                ).round(2)

            # 格式化 '净占比' 列
            if '净占比' in stock_market_fund_flow_df.columns:
                stock_market_fund_flow_df['净占比'] = pd.to_numeric(
                    stock_market_fund_flow_df['净占比'], errors='coerce'
                ).round(2)

            # ← 添加返回语句
            return stock_market_fund_flow_df

        except Exception as e:
            print(f"获取大盘历史资金流向数据失败: {e}")
            return None

    def sector(self):#行业板块资金实时https://data.eastmoney.com/bkzj/hy.html
        try:
            stock_sector_fund_flow_rank_df = ak.stock_sector_fund_flow_rank(
                indicator="今日",
                sector_type="行业资金流"
            ).copy()  # 使用 .copy() 避免警告

            # 重命名列
            stock_sector_fund_flow_rank_df.rename(columns={
                '序号': '序号',
                '名称': '名称',
                '今日涨跌幅': '今日涨跌幅',
                '今日主力净流入-净额': '主力净额',
                '今日主力净流入-净占比': '净占比',
                '今日主力净流入最大股': '代表个股'
            }, inplace=True)

            # 选择需要的列
            result_df = stock_sector_fund_flow_rank_df[[
                '序号', '名称', '今日涨跌幅', '主力净额', '净占比', '代表个股'
            ]].copy()

            # 将主力净流入换算成亿元，保留2位小数
            result_df['主力净额'] = (result_df['主力净额'] / 100000000).round(2)

            # 涨跌幅保留2位小数
            result_df['今日涨跌幅'] = result_df['今日涨跌幅'].round(2)

            # 净占比保留2位小数
            result_df['净占比'] = result_df['净占比'].round(2)

            return result_df

        except Exception as e:
            print(f"获取行业资金流向数据失败: {e}")
            return None

    def sector_stock(self, gn_blk="电源设备"):  #板块内实时个股

        try:
            # 行业内的个股资金流入
            stock_sector_fund_flow_summary_df = ak.stock_sector_fund_flow_summary(symbol=gn_blk, indicator="今日")

            if stock_sector_fund_flow_summary_df is None or stock_sector_fund_flow_summary_df.empty:
                print(f"未获取到板块 {symbol} 的数据")
                return None

            # 使用 .copy() 避免警告
            df = stock_sector_fund_flow_summary_df.copy()

            # 重命名列
            df.rename(columns={
                '今日主力净流入-净额': '主力净额',
                '今日主力净流入-净占比': '净占比'
            }, inplace=True)

            # 选择需要的列
            result_df = df[[
                '序号', '代码', '名称', '最新价', '今天涨跌幅', '主力净额', '净占比'
            ]].copy()

            # 将主力净额换算成亿元，保留2位小数
            result_df['主力净额'] = (result_df['主力净额'] / 100000000).round(2)

            # 涨跌幅保留2位小数
            result_df['今天涨跌幅'] = result_df['今天涨跌幅'].round(2)

            # 净占比保留2位小数
            result_df['净占比'] = result_df['净占比'].round(2)

            return result_df

        except Exception as e:
            print(f"获取板块个股资金流向数据失败: {e}")
            return None

    def sector_detail(self):  #具体板块历史
        stock_sector_fund_flow_hist_df = ak.stock_sector_fund_flow_hist(symbol="汽车服务")
        print(stock_sector_fund_flow_hist_df)
    def gn_blk(self):  #板块列表https://quote.eastmoney.com/center/gridlist.html#concept_board
        try:
            # 1. 获取概念板块名称列表
            stock_board_concept_name_em_df = ak.stock_board_concept_name_em().copy()

            # 重命名列以区分板块涨跌幅和领涨股涨跌幅
            stock_board_concept_name_em_df.rename(columns={
                '板块名称': '名称',
                '涨跌幅': '板块涨跌幅',
                '领涨股票-涨跌幅': '领涨涨幅'
            }, inplace=True)

            # 2. 获取概念资金流数据
            stock_sector_fund_flow_rank_df = ak.stock_sector_fund_flow_rank(
                indicator="今日",
                sector_type="概念资金流"
            ).copy()

            # 重命名概念资金流的列
            stock_sector_fund_flow_rank_df.rename(columns={
                '今日主力净流入-净额': '主力净额',
                '今日主力净流入-净占比': '净占比',
                '今日主力净流入最大股': '代表个股'
            }, inplace=True)

            # 选择需要的列
            fund_df = stock_sector_fund_flow_rank_df[['名称', '主力净额', '净占比', '代表个股']].copy()

            # 3. 将两个 DataFrame 以"名称"列进行合并
            merged_df = pd.merge(
                stock_board_concept_name_em_df,
                fund_df,
                on='名称',
                how='left'
            )
            # 4. 选择最终需要的列
            result_df = merged_df[[
                '名称', '板块涨跌幅', '换手率', '上涨家数', '下跌家数',
                '主力净额', '净占比', '代表个股'
            ]].copy()

            # 5. 数据格式化
            # 将主力净额换算成亿元，保留2位小数
            if '主力净额' in result_df.columns:
                result_df['主力净额'] = (result_df['主力净额'] / 100000000).round(2)

            # 板块涨跌幅保留2位小数
            result_df['板块涨跌幅'] = result_df['板块涨跌幅'].round(2)

            # 换手率保留2位小数
            result_df['换手率'] = result_df['换手率'].round(2)

            # 净占比保留2位小数
            if '净占比' in result_df.columns:
                result_df['净占比'] = pd.to_numeric(result_df['净占比'], errors='coerce')
                result_df['净占比'] = result_df['净占比'].round(2)

            return result_df

        except Exception as e:
            print(f"获取概念板块列表失败: {e}")
            return None


    def gn_detail(self):  #具体概念的详情
        stock_board_concept_spot_em_df = ak.stock_board_concept_spot_em(symbol="可燃冰")
        print(stock_board_concept_spot_em_df)

    def gn_stock(self, gn_blk="可燃冰"):  #概念板块的成分股http://quote.eastmoney.com/center/boardlist.html#boards-BK06551
        try:
            df = ak.stock_board_concept_cons_em(symbol=gn_blk)

            if df is None or df.empty:
                print(f"未获取到概念板块 {gn_blk} 的成分股数据")
                return None

            # 使用 .copy() 避免警告
            df = df.copy()

            # 1. 将成交额换算成亿元，保留2位小数
            if '成交额' in df.columns:
                df['成交额'] = (df['成交额'] / 100000000).round(2)

            # 2. 数值列保留2位小数
            # 可能存在的列名列表
            cols_to_round = [
                '最新价', '涨跌幅', '振幅', '最高', '最低', '今开', '昨收',
                '量比', '换手率', '市盈率-动态', '市净率', '市盈率'
            ]
            for col in cols_to_round:
                if col in df.columns:
                    df[col] = df[col].round(2)

            # 3. 重命名列以匹配用户要求
            # 映射关系：'量比' -> '最比'
            # '市盈率-动态' 或 '市盈率' -> '市盈率（动态）'
            rename_map = {
                '量比': '最比'
            }
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

            # 过滤出实际存在的列
            available_cols = [col for col in target_cols if col in df.columns]
            result_df = df[available_cols].copy()

            return result_df

        except Exception as e:
            print(f"获取概念成分股数据失败: {e}")
            return None

    def gn_his(self, gn_blk="可燃冰", start_date="20251201", end_date="20280101"):
        """具体概念板块的历史数据（含资金流）"""
        try:
            # 1. 获取行情数据
            stock_board_concept_hist_em_df = ak.stock_board_concept_hist_em(
                symbol=gn_blk,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            if stock_board_concept_hist_em_df is None or stock_board_concept_hist_em_df.empty:
                print(f"未获取到概念板块 {gn_blk} 的历史行情数据")
                return None

            df_hist = stock_board_concept_hist_em_df.copy()
            # 确保日期是 datetime 类型（通常已经是）
            df_hist['日期'] = pd.to_datetime(df_hist['日期'])

            # 2. 获取资金流历史
            try:
                fund_hist_df = ak.stock_concept_fund_flow_hist(symbol=gn_blk)
            except Exception as e:
                print(f"获取概念资金流历史失败: {e}")
                fund_hist_df = None

            if fund_hist_df is not None and not fund_hist_df.empty:
                # === 关键修复：统一日期格式 ===
                fund_hist_df['日期'] = pd.to_datetime(fund_hist_df['日期'])  # ←←← 这行最重要！

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
                        fund_hist_df['主力净额'] = (
                                    pd.to_numeric(fund_hist_df['主力净额'], errors='coerce') / 1e8).round(2)
                    if '净占比' in fund_hist_df.columns:
                        fund_hist_df['净占比'] = pd.to_numeric(fund_hist_df['净占比'], errors='coerce').round(4)

                    # 合并（现在日期类型一致了！）
                    merged_df = pd.merge(df_hist, fund_hist_df, on='日期', how='left')
                else:
                    print(f"[WARNING] 资金流数据缺少所需列")
                    merged_df = df_hist
            else:
                print(f"[INFO] 无资金流历史数据")
                merged_df = df_hist

            # 格式化成交额
            if '成交额' in merged_df.columns:
                merged_df['成交额'] = (pd.to_numeric(merged_df['成交额'], errors='coerce') / 1e8).round(2)
                merged_df.rename(columns={'成交额': '成交额(亿)'}, inplace=True)

            return merged_df

        except Exception as e:
            print(f"获取概念板块 {gn_blk} 历史数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def gn_fund(self):  # 概念板块资金注入实时
        try:
            # 获取原始数据
            raw_df = ak.stock_sector_fund_flow_rank(
                indicator="今日",
                sector_type="概念资金流"
            )

            # 检查是否获取到数据
            if raw_df is None or raw_df.empty:
                print("未获取到数据，可能为非交易时间或接口暂时无数据")
                return None

            # 复制一份数据进行操作
            df = raw_df.copy()


                # --- 打印实际列名以便调试（如果运行报错，请查看控制台输出的列名） ---
                # print("概念资金流实际列名:", df.columns.tolist())
                # -------------------------------------------------------------

                # 定义列名映射字典：键是可能存在的旧列名，值是我们要的新列名
                # 这里的判断逻辑会尝试匹配最常见的几种列名变体
            rename_map = {}
            final_cols = []

            # 1. 处理 序号
            if '序号' in df.columns:
                rename_map['序号'] = '序号'
                final_cols.append('序号')

            # 2. 处理 名称
            if '名称' in df.columns:
                rename_map['名称'] = '名称'
                final_cols.append('名称')

            # 3. 处理 涨跌幅 (可能叫 '今日涨跌幅' 或 '涨跌幅')
            change_col = None
            if '今日涨跌幅' in df.columns:
                change_col = '今日涨跌幅'
            elif '涨跌幅' in df.columns:
                change_col = '涨跌幅'

            if change_col:
                rename_map[change_col] = '今日涨跌幅'  # 统一重命名为今日涨跌幅
                final_cols.append('今日涨跌幅')

            # 4. 处理 主力净额 (可能叫 '今日主力净流入-净额', '主力净流入-净额', '主力净额' 等)
            # 查找包含"净额"或"净流入"的列
            net_col = None
            for col in df.columns:
                if '净额' in col or '净流入' in col:
                    net_col = col
                    break

            if net_col:
                rename_map[net_col] = '主力净额'
                final_cols.append('主力净额')

            # 5. 处理 净占比
            ratio_col = None
            for col in df.columns:
                if '净占比' in col:
                    ratio_col = col
                    break

            if ratio_col:
                rename_map[ratio_col] = '净占比'
                final_cols.append('净占比')

            # 6. 处理 代表个股 (可能叫 '今日主力净流入最大股', '主力净流入最大股', '领涨股')
            lead_col = None
            for col in df.columns:
                if '最大股' in col or '领涨' in col:
                    lead_col = col
                    break

            if lead_col:
                rename_map[lead_col] = '代表个股'
                final_cols.append('代表个股')

            # 执行重命名
            df.rename(columns=rename_map, inplace=True)

            # 选择最终需要的列（只选择确实存在的列）
            # 我们需要保证列的顺序：序号，名称，今日涨跌幅，主力净额，净占比，代表个股
            target_order = ['序号', '名称', '今日涨跌幅', '主力净额', '净占比', '代表个股']
            available_cols = [col for col in target_order if col in df.columns]

            result_df = df[available_cols].copy()

            # --- 数据格式化 ---

            # 将主力净额换算成亿元，保留2位小数
            if '主力净额' in result_df.columns:
                result_df['主力净额'] = (result_df['主力净额'] / 100000000).round(2)

            # 涨跌幅保留2位小数
            if '今日涨跌幅' in result_df.columns:
                # 先转换为数值类型
                result_df['今日涨跌幅'] = pd.to_numeric(result_df['今日涨跌幅'], errors='coerce')
                result_df['今日涨跌幅'] = result_df['今日涨跌幅'].round(2)

            # 净占比保留2位小数
            if '净占比' in result_df.columns:
                # 先转换为数值类型
                result_df['净占比'] = pd.to_numeric(result_df['净占比'], errors='coerce')
                result_df['净占比'] = result_df['净占比'].round(2)

            return result_df

        except Exception as e:
            # 打印详细的错误信息，帮助调试
            print(f"获取概念板块资金流向数据失败: {e}")
            # 如果出错，尝试打印原始数据的列名，方便排查
            try:
                print("当前接口返回的列名为:",
                      ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流").columns.tolist())
            except:
                pass
            return None

    def lhb(self, start_date: str, end_date: str):
        """
        统计一段时间的龙虎榜，https://data.eastmoney.com/stock/tradedetail.html并整理为目标格式（不含上榜后N日收益）
        """
        try:
            # 统一日期格式为 YYYYMMDD（AkShare 要求）
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")

            df_raw = ak.stock_lhb_detail_em(start_date=start, end_date=end)
            if df_raw is None or df_raw.empty:
                print(f"龙虎榜：{start_date} 至 {end_date} 无数据")
                return None

            # 复制避免警告
            df = df_raw.copy()

            # 重命名映射（根据实际列名调整）
            rename_map = {
                '代码': '代码',
                '名称': '名称',
                '上榜日': '上榜日',
                '收盘价': '收盘价',
                '涨跌幅': '涨跌幅',
                '净买额': '龙虎榜净买额',
                '买入金额': '龙虎榜买入额',
                '卖出金额': '龙虎榜卖出额',
                '成交金额': '龙虎榜成交额',
                '市场总成交': '市场总成交额',
                '换手率': '换手率',
                '流通市值': '流通市值',
                '解读': '解读',  # 如果有
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

            # 计算占比（注意单位：原始为元）
            df['龙虎榜净买额'] = pd.to_numeric((df['龙虎榜净买额'] / 100000000).round(2), errors='coerce')
            df['龙虎榜成交额'] = pd.to_numeric((df['龙虎榜成交额'] / 100000000).round(2), errors='coerce')
            df['市场总成交额'] = pd.to_numeric((df['市场总成交额'] / 100000000).round(2), errors='coerce')
            df['龙虎榜买入额'] = pd.to_numeric((df['龙虎榜买入额'] / 100000000).round(2), errors='coerce')
            df['龙虎榜卖出额'] = pd.to_numeric((df['龙虎榜卖出额'] / 100000000).round(2), errors='coerce')
            df['流通市值'] = pd.to_numeric((df['流通市值'] / 100000000).round(2), errors='coerce')

            df['净买额占总成交比'] = (df['龙虎榜净买额'] / df['市场总成交额']).round(2)
            df['成交额占总成交比'] = (df['龙虎榜成交额'] / df['市场总成交额']).round(2)

            # 数值列保留合适小数
            float_cols = ['收盘价', '涨跌幅', '换手率', '净买额占总成交比', '成交额占总成交比']
            for col in float_cols:
                if col in df.columns:
                    df[col] = df[col].round(2)

            # 转换为亿元显示（可选，按需）
            # df['龙虎榜净买额'] = (df['龙虎榜净买额'] / 1e8).round(2)
            # df['市场总成交额'] = (df['市场总成交额'] / 1e8).round(2)

            # 最终列顺序
            final_cols = [
                '代码', '名称', '上榜日', '解读', '收盘价', '涨跌幅',
                '龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜成交额',
                '市场总成交额', '净买额占总成交比', '成交额占总成交比',
                '换手率', '流通市值', '上榜原因'
            ]

            result = df[final_cols].copy()
            return result

        except Exception as e:
            print(f"获取或处理龙虎榜数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def lhb_stat(self, period: str = "近一月"):
        """
        获取龙虎榜统计（如近一月上榜次数等）https://data.eastmoney.com/stock/stockstatistic.html
        支持 period: '近一月', '近三月', '近六月', '近一年'
        """
        try:
            # 验证 period 合法性
            valid_periods = ["近一月", "近三月", "近六月", "近一年"]
            if period not in valid_periods:
                print(f"警告: period 应为 {valid_periods} 之一，使用默认 '近一月'")
                period = "近一月"

            df_raw = ak.stock_lhb_stock_statistic_em(symbol=period)
            if df_raw is None or df_raw.empty:
                print(f"龙虎榜统计（{period}）无数据")
                return None

            # 复制避免警告
            df = df_raw.copy()

            # 可选：重命名列（根据实际列名调整）
            # 打印原始列名供参考
            # print("原始列名:", df.columns.tolist())

            # 设置 pandas 全局显示选项（也可在主程序中设置）
            pd.set_option('display.max_columns', None)  # 显示所有列
            pd.set_option('display.max_rows', None)  # 显示所有行（谨慎）
            pd.set_option('display.width', None)  # 自动换行
            pd.set_option('display.max_colwidth', 50)  # 每列最大宽度
            pd.set_option('display.unicode.ambiguous_as_wide', True)
            pd.set_option('display.unicode.east_asian_width', True)

            # 打印完整表格
            print(f"\n【龙虎榜统计 - {period}】")
            print("=" * 100)
            print(df.to_string(index=False))  # to_string() 确保不省略
            print("=" * 100)

            return df

        except Exception as e:
            print(f"获取龙虎榜统计数据失败 ({period}): {e}")
            import traceback
            traceback.print_exc()
            return None



    def lhb_hyyyb(self, start_date: str = "20260101", end_date: str = "20260119"):
        """
        获取龙虎榜活跃的营业部（如近一月上榜次数等）
        参数:https://data.eastmoney.com/stock/hyyyb.html
            start_date (str): 起始日期，格式 "YYYYMMDD" 或 "YYYY-MM-DD"
            end_date (str):   结束日期，格式 "YYYYMMDD" 或 "YYYY-MM-DD"
        示例:
            dh.lhb_hyyyb("2025-12-01", "2025-12-31")
        """
        try:
            # 统一转换为 YYYYMMDD 格式
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")

            df_raw = ak.stock_lhb_hyyyb_em(start_date=start, end_date=end)

            if df_raw is None or df_raw.empty:
                print(f"龙虎榜活跃营业部：{start_date} 至 {end_date} 无数据")
                return None

            df = df_raw.copy()

            # === 设置 pandas 显示选项：确保所有列完整显示 ===
            pd.set_option('display.max_columns', None)  # 不隐藏列
            pd.set_option('display.max_rows', None)  # 显示所有行（可酌情限制）
            pd.set_option('display.width', None)  # 自动换行
            pd.set_option('display.max_colwidth', 100)  # 每列最大宽度（避免截断营业部名称）
            pd.set_option('display.unicode.ambiguous_as_wide', True)
            pd.set_option('display.unicode.east_asian_width', True)

            # === 打印标题和数据 ===
            print(f"\n【龙虎榜活跃营业部统计】{start_date} ~ {end_date}")
            print("=" * 120)
            print(df.to_string(index=False))  # 关键：用 to_string() 避免省略
            print("=" * 120)

            return df

        except Exception as e:
            print(f"获取龙虎榜活跃营业部数据失败 ({start_date} ~ {end_date}): {e}")
            import traceback
            traceback.print_exc()
            return None


    def lhb_stock_detail(self, stock_code: str, date: str, flag: str = "买入"):
        """
        个股龙虎榜详情
        目标地址: https://data.eastmoney.com/stock/lhb/600077.html
        参数:
            stock_code (str): 股票代码，如 "600077"
            date (str): 日期，格式 "YYYYMMDD" 或 "YYYY-MM-DD"，必须是交易日且该股当日上榜
            flag (str): "买入" 或 "卖出"

        示例:
            dh.lhb_stock_detail("600077", "2025-12-15", "买入")
        """

        try:
            clean_date = date.replace("-", "")
            if flag not in ["买入", "卖出"]:
                raise ValueError("flag 必须为 '买入' 或 '卖出'")

            df_raw = ak.stock_lhb_stock_detail_em(symbol=stock_code, date=clean_date, flag=flag)
            if df_raw is None or df_raw.empty:
                print(f"个股龙虎榜详情：{stock_code} 在 {date} 无 {flag} 数据")
                return None

            df = df_raw.copy()

            # === 列名模糊匹配 ===
            buy_amt_col = next((col for col in df.columns if '买入金额' in col and '比例' not in col), None)
            buy_ratio_col = next((col for col in df.columns if '买入金额' in col and ('比例' in col or '比' in col)),
                                 None)
            sell_amt_col = next((col for col in df.columns if '卖出金额' in col and '比例' not in col), None)
            sell_ratio_col = next((col for col in df.columns if '卖出金额' in col and ('比例' in col or '比' in col)),
                                  None)

            # 匹配净额列（常见名称）
            net_col = next((col for col in df.columns
                            if any(kw in col for kw in ['净额', '净买', '净卖', '净买入', '净卖出'])), None)

            # === 处理买入金额（亿元）===
            if buy_amt_col:
                df[buy_amt_col] = pd.to_numeric(df[buy_amt_col], errors='coerce')
                df[buy_amt_col] = (df[buy_amt_col] / 1e8).round(2)
                df.rename(columns={buy_amt_col: '买入金额(亿)'}, inplace=True)

            # === 处理买入比例 ===
            if buy_ratio_col:
                s = df[buy_ratio_col].astype(str).str.replace('%', '', regex=False)
                df[buy_ratio_col] = pd.to_numeric(s, errors='coerce')
                if df[buy_ratio_col].max() > 1:  # 是百分比数值（如 5.23 表示 5.23%）
                    df[buy_ratio_col] = (df[buy_ratio_col] / 100).round(2)
                else:
                    df[buy_ratio_col] = df[buy_ratio_col].round(2)
                df.rename(columns={buy_ratio_col: '买入占比'}, inplace=True)

            # === 处理卖出金额（亿元）===
            if sell_amt_col:
                df[sell_amt_col] = pd.to_numeric(df[sell_amt_col], errors='coerce')
                df[sell_amt_col] = (df[sell_amt_col] / 1e8).round(2)
                df.rename(columns={sell_amt_col: '卖出金额(亿)'}, inplace=True)

            # === 处理卖出比例 ===
            if sell_ratio_col:
                s = df[sell_ratio_col].astype(str).str.replace('%', '', regex=False)
                df[sell_ratio_col] = pd.to_numeric(s, errors='coerce')
                if df[sell_ratio_col].max() > 1:
                    df[sell_ratio_col] = (df[sell_ratio_col] / 100).round(2)
                else:
                    df[sell_ratio_col] = df[sell_ratio_col].round(2)
                df.rename(columns={sell_ratio_col: '卖出占比'}, inplace=True)

            # === 处理净额（亿元）===
            if net_col:
                df[net_col] = pd.to_numeric(df[net_col], errors='coerce')
                df[net_col] = (df[net_col] / 1e8).round(2)
                df.rename(columns={net_col: '净额(亿)'}, inplace=True)

            # === 设置 pandas 显示选项 ===
            pd.set_option('display.max_columns', None)
            pd.set_option('display.max_rows', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 120)
            pd.set_option('display.unicode.ambiguous_as_wide', True)
            pd.set_option('display.unicode.east_asian_width', True)

            # === 打印结果 ===
            print(f"\n【个股龙虎榜详情】{stock_code} | 日期: {date} | 方向: {flag}")
            print("=" * 130)
            print(df.to_string(index=False))
            print("=" * 130)

            return df

        except Exception as e:
            print(f"获取或处理个股龙虎榜详情失败 ({stock_code}, {date}, {flag}): {e}")
            import traceback
            traceback.print_exc()
            return None
    def stock_zt(self):
        """
        获取涨停股票列表目标地址: https://quote.eastmoney.com/ztb/detail#type=ztgc
        """
        try:
            # 获取数据 (使用今天的日期)
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df_raw = ak.stock_zt_pool_em(date=today)

            if df_raw is None or df_raw.empty:
                print("未获取到涨停股票数据")
                return None

            df = df_raw.copy()

            # 格式化数值列
            # 金额类转为亿元
            amount_cols = ['成交额', '流通市值', '总市值']
            for col in amount_cols:
                if col in df.columns:
                    df[col] = (pd.to_numeric(df[col], errors='coerce') / 1e8).round(2)

            # 百分比类保留2位小数
            pct_cols = ['涨跌幅', '换手率', '量比', '振幅', '流通市值占比', '年初至今涨跌幅', '5日涨跌幅', '封单资金']
            for col in pct_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

            # 设置显示选项
            self._set_pandas_display_options()
            print(f"\n【涨停股票池 - {today}】")
            print("=" * 150)
            print(df.to_string(index=False))
            print("=" * 150)
            return df

        except Exception as e:
            print(f"获取涨停股票数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def stock_zt_pre(self):
        """
        获取涨停股票列表目标地址: https://quote.eastmoney.com/ztb/detail#type=ztgc
        """
        try:
            # 获取数据 (使用今天的日期)
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df_raw = ak.stock_zt_pool_previous_em(date=today)

            if df_raw is None or df_raw.empty:
                print("未获取到昨日涨停股票数据")
                return None

            df = df_raw.copy()

            # 格式化数值列
            # 金额类转为亿元
            amount_cols = ['成交额', '流通市值', '总市值']
            for col in amount_cols:
                if col in df.columns:
                    df[col] = (pd.to_numeric(df[col], errors='coerce') / 1e8).round(2)

            # 百分比类保留2位小数
            pct_cols = ['涨跌幅', '换手率', '量比', '振幅', 'A股流通市值', '涨速', '昨日涨停统计', '昨日涨停天数',
                        '昨日连板数', '昨日涨停最大值', '昨日涨停最小值', '昨日涨停均价', '昨日涨停涨跌幅',
                        '昨日涨停收盘价', '昨日涨停开盘价', '昨日涨停最高价', '昨日涨停最低价', '昨日涨停成交量',
                        '昨日涨停成交额', '昨日涨停换手率', '昨日涨停量比', '昨日涨停振幅', '昨日涨停流通市值',
                        '昨日涨停总市值', '昨日涨停流通股本', '昨日涨停总股本', '昨日涨停上市天数', '昨日涨停未匹配量',
                        '昨日涨停未匹配额', '昨日涨停未匹配比', '昨日涨停未匹配振幅', '昨日涨停未匹配换手率',
                        '昨日涨停未匹配量比', '昨日涨停未匹配流通市值', '昨日涨停未匹配总市值',
                        '昨日涨停未匹配流通股本', '昨日涨停未匹配总股本', '昨日涨停未匹配上市天数']
            for col in pct_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

            # 设置显示选项
            self._set_pandas_display_options()
            print(f"\n【昨日涨停股票池 - {today}】")
            print("=" * 150)
            print(df.to_string(index=False))
            print("=" * 150)
            return df

        except Exception as e:
            print(f"获取昨日涨停股票数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def stock_dt(self):
        """
        获取跌停列表目标地址: https://quote.eastmoney.com/ztb/detail#type=ztgc
        """
        try:
            # 获取数据 (使用今天的日期)
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df_raw = ak.stock_zt_pool_dtgc_em(date=today)

            if df_raw is None or df_raw.empty:
                print("未获取到跌停股票数据")
                return None

            df = df_raw.copy()

            # 格式化数值列
            # 金额类转为亿元
            amount_cols = ['成交额', '流通市值', '总市值', '封单资金']
            for col in amount_cols:
                if col in df.columns:
                    df[col] = (pd.to_numeric(df[col], errors='coerce') / 1e8).round(2)

            # 百分比类保留2位小数
            pct_cols = ['涨跌幅', '换手率', '量比', '振幅', '流通市值占比', '年初至今涨跌幅', '5日涨跌幅']
            for col in pct_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

            # 设置显示选项
            self._set_pandas_display_options()
            print(f"\n【跌停股票池 - {today}】")
            print("=" * 150)
            print(df.to_string(index=False))
            print("=" * 150)
            return df

        except Exception as e:
            print(f"获取跌停股票数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def stock_zt_not(self):
        """
        获取炸板股票列表目标地址: https://quote.eastmoney.com/ztb/detail#type=ztgc
        """
        try:
            # 获取数据 (使用今天的日期)
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            df_raw = ak.stock_zt_pool_zbgc_em(date=today)

            if df_raw is None or df_raw.empty:
                print("未获取到炸板股票数据")
                return None

            df = df_raw.copy()

            # 格式化数值列
            # 金额类转为亿元
            amount_cols = ['成交额', '流通市值', '总市值']
            for col in amount_cols:
                if col in df.columns:
                    df[col] = (pd.to_numeric(df[col], errors='coerce') / 1e8).round(2)

            # 百分比类保留2位小数
            pct_cols = ['涨跌幅', '换手率', '量比', '振幅', '流通市值占比', '年初至今涨跌幅', '5日涨跌幅', '涨速'
                       ]
            for col in pct_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

            # 设置显示选项
            self._set_pandas_display_options()
            print(f"\n【炸板股票池 - {today}】")
            print("=" * 150)
            print(df.to_string(index=False))
            print("=" * 150)
            return df

        except Exception as e:
            print(f"获取炸板股票数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def stock_tdx_hot(self):
        """
        通达信热股列表，
        """
        pass
    def earn_effect(self):
        # 目标地址: https: // www.legulegu.com / stockdata / market - activity


        stock_market_activity_legu_df = ak.stock_market_activity_legu()
        print(stock_market_activity_legu_df)
    def stock_fund_3d(self):
        # 目标地址: https://data.eastmoney.com/bkzj/hy.html
        # indicator = "今日"已经合并到个股行情中;        choice        {"今日", "3日", "5日", "10日"}
        try:
            df_raw = ak.stock_individual_fund_flow_rank(indicator="3日")

            if df_raw is None or df_raw.empty:
                print("未获取到3日个股资金流数据")
                return None

            df = df_raw.copy()

            # 将主力净流入金额转为亿元，并保留2位小数
            if '今日主力净流入-净额' in df.columns:
                df['今日主力净流入-净额'] = (pd.to_numeric(df['今日主力净流入-净额'], errors='coerce') / 1e8).round(2)
            if '今日主力净流入-净占比' in df.columns:
                df['今日主力净流入-净占比'] = pd.to_numeric(df['今日主力净流入-净占比'], errors='coerce').round(2)

            # 设置显示选项
            self._set_pandas_display_options()
            print(f"\n【3日个股资金流排名】")
            print("=" * 150)
            print(df.to_string(index=False))
            print("=" * 150)
            return df

        except Exception as e:
            print(f"获取3日个股资金流数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def blk_fund_3d(self):
        # 目标地址: http: // data.eastmoney.com / zjlx / detail.html
        # indicator = "今日"已经合并到个股行情中;    indicator="今日"; choice of {"今日", "5日", "10日"}
        #sector_type = "行业资金流";       choice        of        {"行业资金流", "概念资金流", "地域资金流"}
        try:
            df_raw = ak.stock_sector_fund_flow_rank(indicator="3日", sector_type="行业资金流")

            if df_raw is None or df_raw.empty:
                print("未获取到3日行业资金流数据")
                return None

            df = df_raw.copy()

            # 将主力净流入金额转为亿元，并保留2位小数
            if '今日主力净流入-净额' in df.columns:
                df['今日主力净流入-净额'] = (pd.to_numeric(df['今日主力净流入-净额'], errors='coerce') / 1e8).round(2)
            if '今日主力净流入-净占比' in df.columns:
                df['今日主力净流入-净占比'] = pd.to_numeric(df['今日主力净流入-净占比'], errors='coerce').round(2)

            # 设置显示选项
            self._set_pandas_display_options()
            print(f"\n【3日行业资金流排名】")
            print("=" * 150)
            print(df.to_string(index=False))
            print("=" * 150)
            return df

        except Exception as e:
            print(f"获取3日行业资金流数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def stock_now(self, stock_code: str):
        """
        获取单支股票的实时行情（通过东财个股接口，避免全量拉取）
        目标列：最新, 涨幅, 总手, 金额, 换手, 量比, 今开, 最高, 最低, 昨收
        """
        import time
        import random
        from akshare.stock_feature.stock_hist_em import _code_id_map

        try:
            # 获取代码映射（如 '600519' -> '1.600519'）
            code_id_dict = _code_id_map()
            if stock_code not in code_id_dict:
                print(f"❌ 不支持的股票代码: {stock_code}")
                return None

            code_id = code_id_dict[stock_code]

            # 构造东财个股行情 URL
            url = f"https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "invt": "2",
                "fltt": "2",
                "fields": "f58,f107,f169,f170,f152,f177,f111,f110,f116,f117,f113,f114,f115,f118,f119,f120,f121,f122,f123,f124,f125,f126,f127,f128,f129,f130,f131,f132,f133,f134,f135,f136,f137,f138,f139,f141,f142,f144,f145,f146,f147,f148,f149,f150,f151,f153,f154,f155,f156,f157,f158,f159,f160,f161,f162,f163,f164,f165,f166,f167,f168,f171,f172,f173,f174,f175,f176,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f194,f195,f196,f197,f198,f199,f200,f201,f202,f203,f204,f205,f206,f207,f208,f209,f210,f211,f212,f213,f214,f215,f216,f217,f218,f219,f220,f221,f222,f223,f224,f225,f226,f227,f228,f229,f230,f231,f232,f233,f234,f235,f236,f237,f238,f239,f240,f241,f242,f243,f244,f245,f246,f247,f248,f249,f250,f251,f252,f253,f254,f255,f256,f257,f258,f259,f260,f261,f262,f263,f264,f265,f266,f267,f268,f269,f270,f271,f272,f273,f274,f275,f276,f277,f278,f279,f280,f281,f282,f283,f284,f285,f286,f287,f288,f289,f290,f291,f292,f293,f294,f295,f296,f297,f298,f299,f300,f301,f302,f303,f304,f305,f306,f307,f308,f309,f310,f311,f312,f313,f314,f315,f316,f317,f318,f319,f320,f321,f322,f323,f324,f325,f326,f327,f328,f329,f330,f331,f332,f333,f334,f335,f336,f337,f338,f339,f340,f341,f342,f343,f344,f345,f346,f347,f348,f349,f350,f351,f352,f353,f354,f355,f356,f357,f358,f359,f360,f361,f362,f363,f364,f365,f366,f367,f368,f369,f370,f371,f372,f373,f374,f375,f376,f377,f378,f379,f380,f381,f382,f383,f384,f385,f386,f387,f388,f389,f390,f391,f392,f393,f394,f395,f396,f397,f398,f399,f400,f401,f402,f403,f404,f405,f406,f407,f408,f409,f410,f411,f412,f413,f414,f415,f416,f417,f418,f419,f420,f421,f422,f423,f424,f425,f426,f427,f428,f429,f430,f431,f432,f433,f434,f435,f436,f437,f438,f439,f440,f441,f442,f443,f444,f445,f446,f447,f448,f449,f450,f451,f452,f453,f454,f455,f456,f457,f458,f459,f460,f461,f462,f463,f464,f465,f466,f467,f468,f469,f470,f471,f472,f473,f474,f475,f476,f477,f478,f479,f480,f481,f482,f483,f484,f485,f486,f487,f488,f489,f490,f491,f492,f493,f494,f495,f496,f497,f498,f499,f500,f501,f502,f503,f504,f505,f506,f507,f508,f509,f510,f511,f512,f513,f514,f515,f516,f517,f518,f519,f520,f521,f522,f523,f524,f525,f526,f527,f528,f529,f530,f531,f532,f533,f534,f535,f536,f537,f538,f539,f540,f541,f542,f543,f544,f545,f546,f547,f548,f549,f550,f551,f552,f553,f554,f555,f556,f557,f558,f559,f560,f561,f562,f563,f564,f565,f566,f567,f568,f569,f570,f571,f572,f573,f574,f575,f576,f577,f578,f579,f580,f581,f582,f583,f584,f585,f586,f587,f588,f589,f590,f591,f592,f593,f594,f595,f596,f597,f598,f599,f600",
                "secid": code_id,
                "_": int(time.time() * 1000),
            }

            # 添加 headers 模拟浏览器
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"https://quote.eastmoney.com/{stock_code}.html"
            }

            # 重试机制
            for attempt in range(3):
                try:
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    break
                except Exception as e:
                    print(f"第 {attempt + 1} 次尝试失败: {e}")
                    time.sleep(random.uniform(1, 3))
            else:
                print("❌ 所有重试均失败")
                return None

            # 解析数据（字段含义需对照东财文档）
            quote = data["data"]["f58"]  # 最新价
            if quote is None:
                print("❌ 未获取到有效行情数据（可能停牌或非交易时间）")
                return None

            result = pd.DataFrame([{
                '最新': data["data"]["f58"],
                '涨幅': data["data"]["f170"],  # 涨跌幅
                '总手': data["data"]["f177"],  # 成交量（股）
                '金额': data["data"]["f152"],  # 成交额（元）
                '换手': data["data"]["f169"],  # 换手率
                '量比': data["data"]["f171"],  # 量比
                '今开': data["data"]["f59"],  # 今开
                '最高': data["data"]["f60"],  # 最高
                '最低': data["data"]["f61"],  # 最低
                '昨收': data["data"]["f62"],  # 昨收
            }])

            # 数值处理
            float_cols = ['最新', '涨幅', '换手', '量比', '今开', '最高', '最低', '昨收']
            for col in float_cols:
                result[col] = pd.to_numeric(result[col], errors='coerce').round(2)
            result['总手'] = (pd.to_numeric(result['总手'], errors='coerce') / 100).round(0)  # 转为“手”
            result['金额'] = (pd.to_numeric(result['金额'], errors='coerce') / 1e8).round(2)  # 转为“亿元”

            return result

        except Exception as e:
            print(f"获取 {stock_code} 实时行情失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    def _set_pandas_display_options(self):
        """辅助方法：设置pandas全局显示选项"""
        pd.set_option('display.max_columns', None)  # 显示所有列
        pd.set_option('display.max_rows', None)  # 显示所有行
        pd.set_option('display.width', None)  # 自动换行
        pd.set_option('display.max_colwidth', 100)  # 每列最大宽度
        pd.set_option('display.unicode.ambiguous_as_wide', True)
        pd.set_option('display.unicode.east_asian_width', True)

if __name__ == '__main__':
    dh = data_his()
    df_gn_stock = dh.stock_his("300393")

    if df_gn_stock is not None:
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.unicode.ambiguous_as_wide', True)
        pd.set_option('display.unicode.east_asian_width', True)
        # print("概念板块成分股数据:")
        print(df_gn_stock.tail(20))
    else:
        print("数据获取失败")