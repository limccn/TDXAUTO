import pandas as pd
import akshare as ak
import os
from datetime import datetime, time, timedelta
import time as time_module
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional
from mootdx.reader import Reader
import csv
import json



def load_config():
    try:
        with open('setup.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

class update:
    # 手动更新类属性
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.config = load_config()
        self.tdx_path = self.config.get('TDX_PATH', '')
        # 记录每个函数最后获取历史数据的日期
        self.last_fetch_date = {}
        self.last_lhb_fetch_date = None
        self.last_batch_lhb_fetch_date = None

        # 初始化 headers (用于热榜数据获取)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    def get_all_data(self):
        """从桌面读取当天A股数据，去重后追加到CSV文件中"""
        setup_json_path = "setup.json"
        csv_output_path = "data/all_data.csv"
        columns_to_keep = ["代码", "开盘换手Z", "开盘金额", "开盘量比"]

        # ---- 1. 读取 setup.json 获取桌面路径 ----
        with open(setup_json_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        desktop_path = config.get("desktop_path") or config.get("DesktopPath") or config.get("desktop")
        if not desktop_path:
            raise KeyError("未在 setup.json 中找到桌面路径")

        # ---- 2. 用当天日期拼接文件名并读取 ----
        today_str = datetime.now().strftime("%Y%m%d")
        file_name = f"全部Ａ股{today_str}.xls"
        file_path = os.path.join(desktop_path, file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"未找到文件：{file_path}")

        # 自动检测编码
        raw = open(file_path, "rb").read(5000)
        encoding = "gbk" if b"\xb4\xfa\xc2\xeb" in raw else "utf-8"

        df = pd.read_csv(file_path, sep="\t", encoding=encoding, dtype=str)

        # ---- 3. 删除 "#数据来源:通达信" 等无关行 ----
        first_col = df.columns[0]
        df = df[~df[first_col].astype(str).str.contains("数据来源|通达信", na=False)]

        # 检查所需列是否存在
        missing = [col for col in columns_to_keep if col not in df.columns]
        if missing:
            raise KeyError(f"文件中缺少以下列：{missing}")

        df = df[columns_to_keep].copy()
        # ---- 4. 清理代码列：="688618" → 688618 ----
        df["代码"] = df["代码"].astype(str).str.replace(r'^="(.+)"$', r'\1', regex=True)
        # ---- 5. 开盘金额除以10000，保留2位小数 ----
        # df["开盘金额"] = (pd.to_numeric(df["开盘金额"], errors="coerce") / 10000).round(2)

        # ---- 4. 插入日期列 ----
        today_display = datetime.now().strftime("%Y-%m-%d")
        df.insert(0, "日期", today_display)

        # ---- 5. 追加写入CSV（当天数据去重）----
        os.makedirs(os.path.dirname(csv_output_path), exist_ok=True)

        if os.path.exists(csv_output_path):
            old_df = pd.read_csv(csv_output_path, dtype=str)
            df = pd.concat([old_df, df], ignore_index=True)

            # 按 [日期, 代码Z] 去重，keep='last' 保留最新跑出的那条
            df = df.drop_duplicates(subset=["日期", "代码"], keep="last")

        df.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
        print(f"完成！当前共 {len(df)} 条数据，已保存到 {csv_output_path}")

    def extern_user(self):
        """将all_data.csv转换为通达信外部信号格式，保存到extern_user.txt"""
        # ---- 1. 读取 setup.json 获取 TDX_PATH ----
        setup_json_path = "setup.json"
        csv_output_path = "data/all_data.csv"
        with open(setup_json_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        tdx_path = config.get("TDX_PATH")
        if not tdx_path:
            raise KeyError("未在 setup.json 中找到 TDX_PATH")

        # ---- 2. 读取 all_data.csv ----
        if not os.path.exists(csv_output_path):
            raise FileNotFoundError(f"未找到文件：{csv_output_path}")
        df = pd.read_csv(csv_output_path, dtype=str)

        # ---- 3. 计算日期差（从今天往前推）----
        today = pd.Timestamp.now()

        df["日期"] = pd.to_datetime(df["日期"])
        df["日期差"] = (today - df["日期"]).dt.days

        # 只保留最近10天内的数据（0~9天），超过10天的丢弃
        df = df[(df["日期差"] >= 0) & (df["日期差"] <= 9)]
        if df.empty:
            print("没有最近10天内的数据，无需生成文件")
            return

        # ---- 4. 代码补足6位 & 确定市场代码 ----
        def get_market(code):
            code = str(code).zfill(6)
            prefix = code[:2]
            if prefix in ("00", "30"):
                return "0"
            elif prefix in ("60", "68"):
                return "1"
            elif prefix == "92":
                return "2"
            else:
                return "0"

        df["代码"] = df["代码"].astype(str).str.zfill(6)
        df["市场"] = df["代码"].apply(get_market)

        # ---- 5. 生成编码：1100(今天)、1101(昨天)、1102...1109 ----
        df["编码"] = "110" + df["日期差"].astype(str)

        # ---- 6. 拼接每行格式：市场|代码|编码|暂无|开盘金额 ----
        lines = df.apply(
            lambda row: f"{row['市场']}|{row['代码']}|{row['日期'].strftime('%Y%m%d')}|{row['开盘金额']}",

            axis=1
        )
        # lines = df.apply(
        #     lambda row: f"{row['市场']}|{row['代码']}|{row['编码']}|{row['开盘金额']}",
        #
        #     axis=1
        # )
        # ---- 7. 保存到 TDX_PATH/T0002/signals/extern_user.txt ----
        output_dir = os.path.join(tdx_path, "T0002", "signals")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "extern_user.txt")
        with open(output_path, "w", encoding="gbk") as f:
            f.write("\n".join(lines.tolist()) + "\n")

        print(f"完成！共导出 {len(df)} 条信号，已保存到 {output_path}")
    def etf_jz(self):
        """ETF基金净值数据"""
        file = os.path.join(self.tdx_path, 'T0002', 'hq_cache', 'specjjdata.txt')
        # 检查文件是否存在
        if not os.path.exists(file):
            print(f"❌ 未找到文件: {file}")
            return

        # 读取ETF名称映射表
        name_file = os.path.join(self.data_dir, 'etf_name.csv')
        if not os.path.exists(name_file):
            print(f"❌ 未找到ETF名称文件: {name_file}")
            return

        name_df = pd.read_csv(name_file, encoding='utf-8-sig')
        name_dict = dict(zip(name_df['代码'].astype(str), name_df['名称']))

        # 解析specjjdata.txt文件
        data_list = []
        with open(file, 'r', encoding='gbk') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 6:
                    code = parts[0].strip()
                    date_str = parts[3].strip()  # 20260403格式
                    amount = parts[4].strip()  # 份额
                    net_value = parts[5].strip()  # 净值

                    # 过滤无效数据
                    if code and date_str and amount and net_value:
                        try:
                            # 获取名称
                            name = name_dict.get(code, '')
                            # 如果名称为空，跳过该行
                            if not name:
                                continue

                            amount_float = float(amount)
                            net_value_float = float(net_value)

                            # 日期格式转换：强制统一为带前导零的 YYYY-MM-DD
                            if len(date_str) == 8 and date_str.isdigit():
                                date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                            else:
                                # 兜底处理：把各种奇葩格式(如2026-4-7)统统转成标准格式
                                try:
                                    date_formatted = pd.to_datetime(date_str).strftime('%Y-%m-%d')
                                except:
                                    date_formatted = date_str

                            # 计算总市值
                            total_value = round(amount_float * net_value_float / 10000, 2)

                            data_list.append({
                                '日期': date_formatted,
                                '代码': str(code),  # 强制转为字符串
                                '名称': name,
                                '份额': amount_float,
                                '净值': net_value_float,
                                '总市值': total_value
                            })
                        except ValueError:
                            continue

        if not data_list:
            print("❌ 未解析到有效数据（可能名称匹配失败）")
            return

        df_new = pd.DataFrame(data_list)

        # 【新增】新数据自身去重，防止txt文件内部存在多行重复记录
        df_new = df_new.drop_duplicates(subset=['日期', '代码'], keep='last')

        print(f"解析到 {len(df_new)} 条有效数据（已过滤名称为空）")

        # 保存到文件
        output_file = os.path.join(self.data_dir, 'etf_jz.csv')
        if os.path.exists(output_file):
            # 读取现有数据
            df_existing = pd.read_csv(output_file, encoding='utf-8-sig')

            # ================= 核心修复：统一数据类型 =================
            # 1. 统一“代码”列：强制全部转为字符串去空格，解决 159001(int) != '159001'(str) 的问题
            df_existing['代码'] = df_existing['代码'].astype(str).str.strip()
            df_new['代码'] = df_new['代码'].astype(str).str.strip()

            # 2. 统一“日期”列：强制全部转为标准的 YYYY-MM-DD 格式，解决 2026-4-7 != 2026-04-07 的问题
            df_existing['日期'] = pd.to_datetime(df_existing['日期'], errors='coerce').dt.strftime('%Y-%m-%d')
            df_new['日期'] = pd.to_datetime(df_new['日期'], errors='coerce').dt.strftime('%Y-%m-%d')
            # =========================================================

            # 合并数据
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)

            # 基于日期+代码去重，保留最新数据（此时类型一致，去重必定生效）
            df_combined = df_combined.drop_duplicates(subset=['日期', '代码'], keep='last')

            # 按日期降序、代码升序排序
            df_combined = df_combined.sort_values(['日期', '代码'], ascending=[False, True])

            # 保存
            df_combined.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"✅ 已追加保存，共 {len(df_combined)} 条数据")
        else:
            # 首次创建
            df_new = df_new.sort_values(['日期', '代码'], ascending=[False, True])
            df_new.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"✅ 已创建并保存 {len(df_new)} 条数据")

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

        # ================= 新增：热榜数据保存逻辑 =================

    def _save_hot_csv(self, df, csv_file):
        """保存热榜CSV文件，同一天的数据会被覆盖"""
        today_str = df.iloc[0]["日期"]
        if os.path.exists(csv_file):
            try:
                existing_df = pd.read_csv(csv_file, encoding="utf-8-sig")
                existing_df = existing_df[existing_df["日期"] != today_str]
                result_df = pd.concat([existing_df, df], ignore_index=True)
            except:
                result_df = df
        else:
            result_df = df
        result_df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"✅ 热榜数据已保存: {csv_file}")

        # ================= 新增：热榜数据获取函数 =================

    def ths(self):
        """同花顺热榜"""
        print("正在更新：同花顺热榜...")
        url = (
            "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
            "?stock_type=a&type=hour&list_type=normal"
        )
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            stock_list = data.get("data", {}).get("stock_list", [])
            if not stock_list:
                print("未获取到股票列表")
                return

            stock_list = sorted(stock_list, key=lambda x: x.get("order", 999))
            today_str = datetime.now().strftime("%Y-%m-%d")
            new_row = {"日期": today_str}
            for item in stock_list:
                order = item.get("order")
                code = item.get("code")
                if order and 1 <= order <= 50:
                    new_row[f"排名{order}"] = code
            for i in range(1, 51):
                if f"排名{i}" not in new_row:
                    new_row[f"排名{i}"] = ""
            columns_order = ["日期"] + [f"排名{i}" for i in range(1, 51)]
            df = pd.DataFrame([new_row], columns=columns_order)
            csv_file = os.path.join(self.data_dir, "hot_ths.csv")
            self._save_hot_csv(df, csv_file)
        except Exception as e:
            print(f"❌ 同花顺更新失败: {e}")

    def cls(self):
        """财联社热榜"""
        print("正在更新：财联社热榜...")
        url = "https://api3.cls.cn/v1/hot_stock"
        para = {
            'app': 'cailianpress',
            'os': 'android',
            'sv': 835,
            'sign': 'e89e141e1391c13c7d2b99d8c142848c'
        }
        try:
            resp = requests.get(url, headers=self.headers, params=para, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            data_list = data.get("data", [])
            if not data_list:
                print("未获取到股票列表")
                return

            today_str = datetime.now().strftime("%Y-%m-%d")
            new_row = {"日期": today_str}
            for i, item in enumerate(data_list, 1):
                if i > 50:
                    break
                stock_info = item.get("stock", {})
                stock_id = stock_info.get("StockID", "")
                if stock_id:
                    pure_code = stock_id[2:]
                    new_row[f"排名{i}"] = pure_code
            for i in range(1, 51):
                if f"排名{i}" not in new_row:
                    new_row[f"排名{i}"] = ""
            columns_order = ["日期"] + [f"排名{i}" for i in range(1, 51)]
            df = pd.DataFrame([new_row], columns=columns_order)
            csv_file = os.path.join(self.data_dir, "hot_cls.csv")
            self._save_hot_csv(df, csv_file)
        except Exception as e:
            print(f"❌ 财联社更新失败: {e}")

    def tdx(self):
        """通达信热榜"""
        print("正在更新：通达信热榜...")
        url = "https://pul.tdx.com.cn/TQLEX"
        params = {"Entry": "JNLPSE.hotStockList", "RI": ""}
        data = [{"listType": "0", "cycle": "0"}]
        try:
            response = requests.post(url, params=params, json=data, headers=self.headers, timeout=30)
            result = response.json()
            status = result[0]
            if status[0] != 0:
                print(f"接口返回错误: {status}")
                return

            headers_row = result[1]
            data_rows = result[3:]
            print(f"获取到 {len(data_rows)} 条数据")
            df = pd.DataFrame(data_rows, columns=headers_row)
            today_str = datetime.now().strftime("%Y-%m-%d")
            new_row = {"日期": today_str}
            for _, row in df.iterrows():
                ranking = int(row["ranking"])
                sec_code = row["sec_code"]
                if 1 <= ranking <= 50:
                    new_row[f"排名{ranking}"] = sec_code
            for i in range(1, 51):
                if f"排名{i}" not in new_row:
                    new_row[f"排名{i}"] = ""
            columns_order = ["日期"] + [f"排名{i}" for i in range(1, 51)]
            df_new = pd.DataFrame([new_row], columns=columns_order)
            csv_file = os.path.join(self.data_dir, "hot_tdx.csv")
            self._save_hot_csv(df_new, csv_file)
        except Exception as e:
            print(f"❌ 通达信更新失败: {e}")

    def em_old(self):
        """东方财富热榜 (读取本地HTML)"""
        print("正在更新：东方财富热榜...")
        html_file = os.path.join(self.data_dir, "东方财富热榜.html")
        if not os.path.exists(html_file):
            print(f"❌ 未找到文件: {html_file}，请先手动保存网页")
            return

        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, 'html.parser')
            code_spans = soup.find_all('span', class_='code')
            if not code_spans:
                print("未找到股票代码")
                return

            print(f"找到 {len(code_spans)} 个股票代码")
            today_str = datetime.now().strftime("%Y-%m-%d")
            new_row = {"日期": today_str}
            for i, span in enumerate(code_spans, 1):
                if i > 50:
                    break
                code = span.get_text(strip=True)
                new_row[f"排名{i}"] = code
            for i in range(1, 51):
                if f"排名{i}" not in new_row:
                    new_row[f"排名{i}"] = ""
            columns_order = ["日期"] + [f"排名{i}" for i in range(1, 51)]
            df = pd.DataFrame([new_row], columns=columns_order)
            csv_file = os.path.join(self.data_dir, "hot_em.csv")
            self._save_hot_csv(df, csv_file)
        except Exception as e:
            print(f"❌ 东方财富更新失败: {e}")

    def em(self):
        """东方财富热榜 (接口获取)"""
        print("正在更新：东方财富热榜...")
        url = 'https://emappdata.eastmoney.com/stockrank/getAllCurrentList'
        params = {
            'appId': "appId01",
            'globalId': "786e4c21-70dc-435a-93bb-38",
            'marketType': "",
            'pageNo': 1,
            'pageSize': 100
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(url, json=params, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            result_dict = response.json()

            if result_dict.get('status') != 0:
                print(f"接口返回错误: {result_dict.get('message', '未知错误')}")
                return

            stock_list = result_dict.get('data', [])
            if not stock_list:
                print("未获取到股票列表")
                return

            print(f"获取到 {len(stock_list)} 条数据")

            today_str = datetime.now().strftime("%Y-%m-%d")
            new_row = {"日期": today_str}

            for i, item in enumerate(stock_list, 1):
                if i > 50:
                    break

                sc = item.get('sc', '')
                if sc.startswith('SZ') or sc.startswith('SH'):
                    code = sc[2:]  # "SZ002309" -> "002309"
                    code = str(int(code))  # "002309" -> "2309"（去掉前导零）
                else:
                    code = sc

                new_row[f"排名{i}"] = code

            for i in range(1, 51):
                if f"排名{i}" not in new_row:
                    new_row[f"排名{i}"] = ""

            columns_order = ["日期"] + [f"排名{i}" for i in range(1, 51)]
            df = pd.DataFrame([new_row], columns=columns_order)

            csv_file = os.path.join(self.data_dir, "hot_em.csv")
            self._save_hot_csv(df, csv_file)

        except Exception as e:
            print(f"❌ 东方财富更新失败: {e}")

    def start_realtime_fetch(self, run_once=False):
        """
        启动实时数据自动获取
        - 每天首次运行时获取上一个交易日的龙虎榜数据（仅一次）

        :param run_once: 如果为True，执行一次后退出；否则无限循环
        """
        while True:
            try:

                # 获取今天的日期字符串
                today = self._get_today_date_str()
                current_dt = datetime.now()
                date_today = current_dt.strftime("%Y-%m-%d")
                date_three_days_ago = (current_dt - pd.Timedelta(days=3)).strftime("%Y-%m-%d")

                # 每天第一次运行时，获取上一个交易日的龙虎榜数据（仅一次）
                # 注意：data_update.py 中这部分是注释掉的，这里保持原样
                # if self.last_lhb_fetch_date != today:
                #     print("\n【正在获取上一个交易日龙虎榜数据...】")
                #     ...
                #     self.last_lhb_fetch_date = today

                if self.last_batch_lhb_fetch_date != today:
                    print("\n【正在批量下载龙虎榜详情...】")
                    print(f"日期范围: {date_three_days_ago} 至 {date_today}")

                    # 调用 batch_lhb，延时设为 1 秒，避免请求过快
                    self.batch_lhb(start_date=date_three_days_ago, end_date=date_today, delay_seconds=3)

                    # 标记今天已执行过批量下载
                    self.last_batch_lhb_fetch_date = today
                    print(f"✅ 龙虎榜详情批量下载完成")

                # 【新增】如果是单次运行模式，执行完任务后跳出循环
                if run_once:
                    print("单次运行模式：数据获取完成，退出循环")
                    break

                # time_module.sleep(60)
            except KeyboardInterrupt:
                print("\n定时任务已停止")
                break
            except Exception as e:
                print(f"\n定时任务出错: {e}")
                # 【新增】如果是单次运行模式出错，也跳出循环，防止卡死
                if run_once:
                    break

                # time_module.sleep(60)
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

            # 找出新增的营业部（直接比较，因为 lhb_detail_b.csv 中的名称已经是缩写状态）
            new_yyb_full = [name for name in yyb_names if name not in existing_yyb]

            if not new_yyb_full:
                print("营业部数据已是最新！")
                return True

            print(f"➕ 发现 {len(new_yyb_full)} 个新营业部")

            # 3. 构造新增数据
            new_data_list = []
            for name in new_yyb_full:
                new_data_list.append({
                    '交易营业部名称': name,  # 直接使用，不缩写
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
            print(msg)

            print(f"✅ 成功追加 {len(new_yyb_full)} 个新营业部到 {output_file}")

        except Exception as e:
            print(f"❌ 提取营业部数据失败: {e}")
            return False

    # 获取基金数据# 获取基金数据# 获取基金数据# 获取基金数据
    def fund_daily_old(self):
        """获取开放式基金每日净值数据"""


        def extract_fund_data_from_html(file_path):
            # 尝试多种编码
            for encoding in ['utf-8', 'gbk', 'gb2312']:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        soup = BeautifulSoup(f, "html.parser")
                    print(f"✅ 成功以 {encoding} 编码读取: {file_path}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError(f"无法用常见编码读取文件: {file_path}")

            rows = soup.select('tr[rel="tpl"]')  # 选择所有基金数据行
            data = []
            for row in rows:
                try:
                    # 提取基金代码
                    code_td = row.find('td', string=lambda x: x and len(x.strip()) == 6 and x.strip().isdigit())
                    if not code_td:
                        code_elem = row.find('a', {'field': 'code'})
                        code = code_elem.get_text(strip=True) if code_elem else None
                    else:
                        code = code_td.get_text(strip=True)

                    # 提取基金名称
                    name_elem = row.find('a', {'field': 'name'})
                    name = name_elem.get_text(strip=True) if name_elem else None

                    # 提取单位净值（field="net"）
                    net_elem = row.find('td', {'field': 'net'})
                    net = net_elem.get_text(strip=True) if net_elem else None

                    # 提取申购状态（field="sgstat"）
                    stat_elem = row.find('td', {'field': 'sgstat'})
                    stat = stat_elem.get_text(strip=True) if stat_elem else None
                    if stat == "开放" or stat == "限制大额":

                        if code and name and net:
                            data.append({"代码": code, "基金名称": name, "单位净值": net, "申购状态": stat})
                except Exception as e:
                    print(f"解析某行时出错: {e}")
                    continue
            return data

        # 读取两个文件
        lof_data = extract_fund_data_from_html("data\\lof型开放式基金净值查询_基金数据_同花顺金融网.html")

        # 转为 DataFrame 并去重（避免重复基金）
        df = pd.DataFrame(lof_data).drop_duplicates(subset=["代码"]).reset_index(drop=True)

        # 保存到 CSV
        output_path = "data/fund_day.csv"
        df.to_csv(output_path, index=False, encoding="utf_8_sig")  # utf_8_sig 支持 Excel 正确显示中文

        print(f"共提取 {len(df)} 只基金，已保存至 {output_path}")

    def fund_daily(self):
        """获取开放式基金每日净值数据"""
        print("正在更新：开放式基金每日净值...")

        url = 'https://fund.10jqka.com.cn/data/Net/info/LOF_rate_desc_0_0_1_9999_0_0_0_jsonp_g.html'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            item = response.text

            # 1. 去掉 JSONP 包装：g(...) -> {...}
            json_str = re.search(r'\((.*)\)', item).group(1)

            # 2. 解析 JSON
            data_dict = json.loads(json_str)

            # 3. 提取基金列表
            fund_list = data_dict['data']['data']

            # 4. 解析每只基金
            result = []
            for fund_key, fund_info in fund_list.items():
                code = fund_info['code']  # 代码
                name = fund_info['name']  # 基金名称
                net = fund_info['newnet']  # 单位净值
                sgstat = fund_info['sgstat']  # 申购状态

                # 只保存申购状态为"开放"或"限制大额"的基金
                if sgstat == "开放" or sgstat == "限制大额":
                    result.append({
                        "代码": code,
                        "基金名称": name,
                        "单位净值": net,
                        "申购状态": sgstat
                    })

            # 5. 转为 DataFrame 并去重（避免重复基金）
            df = pd.DataFrame(result).drop_duplicates(subset=["代码"]).reset_index(drop=True)

            # 6. 保存到 CSV
            output_path = os.path.join(self.data_dir, "fund_day.csv")
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"✅ 共提取 {len(df)} 只基金，已保存至 {output_path}")

        except Exception as e:
            print(f"❌ 获取基金数据失败: {e}")

    def fetch_etf_or_lof(self, symbol):
        """获取指定类型的基金数据（'ETF基金' 或 'LOF基金'）"""
        try:
            df = ak.fund_etf_category_sina(symbol=symbol)
            print(f"✅ 成功获取 {symbol} 数据，共 {len(df)} 条")
            return df
        except Exception as e:
            print(f"❌ 获取 {symbol} 失败: {e}")
            return pd.DataFrame()

    def fund_etf_and_lof(self):
        """当前最新价同时获取 ETF 和 LOF 数据，并合并保存到同一个文件"""
        # df_etf = self.fetch_etf_or_lof("ETF基金")
        df_lof = self.fetch_etf_or_lof("LOF基金")

        df_lof['代码'] = df_lof['代码'].str.replace(r'^(sh|sz)', '', case=False, regex=True)

        # 保存到同一个文件
        output_path = "data/fund_lof.csv"
        df_lof.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ ETF 和 LOF 数据已合并保存至 {output_path}，共 {len(df_lof)} 条记录")

    def fund_etf(self):
        """当前最新价同时获取 ETF 数据，并保存到文件"""
        df_etf = self.fetch_etf_or_lof("ETF基金")

        if not df_etf.empty:
            df_etf['代码'] = df_etf['代码'].str.replace(r'^(sh|sz)', '', case=False, regex=True)

            # 保存到文件
            output_path = "data/fund_etf.csv"
            df_etf.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"✅ ETF 数据已保存至 {output_path}，共 {len(df_etf)} 条记录")
        else:
            print("❌ ETF 数据获取失败，文件未生成")

    def remove_rows_with_empty_col4(self, input_csv='fund_day.csv', output_csv='fund_day.csv'):

        # 统一使用 os.path.join 拼接路径
        input_path = os.path.join(self.data_dir, input_csv)
        output_path = os.path.join(self.data_dir, output_csv)

        # 读取主文件前检查文件是否存在
        if not os.path.exists(input_path):
            print(f"❌ 错误：找不到文件 {input_path}")
            print("💡 提示：请检查之前的 fund_daily() 是否成功运行。")
            return

        try:
            df = pd.read_csv(input_path)
        except Exception as e:
            print(f"❌ 读取文件 {input_path} 失败: {e}")
            print("💡 提示：文件可能正在被其他程序（如 Excel）占用，或者文件损坏。")
            return

        print(f"原始数据行数: {len(df)}")

        # 获取第3列（索引为2）和"代码"列（索引为0）
        col_data = df.iloc[:, 2]  # 第3列：单位净值
        col_code = df['代码'].astype(str).str.zfill(6)  # 确保"代码"列是6位字符串

        # # ========== 读取 fund_stat.txt 并筛选 "暂停申购" 的代码 ==========
        stat_txt_path = os.path.join(self.data_dir, 'fund_stat.txt')
        paused_codes = []

        if os.path.exists(stat_txt_path):
            try:
                with open(stat_txt_path, 'r', encoding='utf-8-sig') as f:
                    paused_codes = [line.strip() for line in f if line.strip()]
                print(f"🛑️ 从 fund_stat.txt 读取到 {len(paused_codes)} 个暂停申购代码")
            except Exception as e:
                print(f"⚠️ 读取 fund_stat.txt 失败: {e}")
        else:
            print("⚠️ 未找到 fund_stat.txt，仅根据第3列数值筛选")

        # ========== 修改筛选逻辑 ==========

        # 处理数据为字符串
        numeric_col = pd.to_numeric(col_data, errors='coerce')

        # 2. 删除条件 A：数值无效（NaN） 或 数值等于 0
        #    NaN 代表了原数据的空值、空字符串、'--' 等
        #    numeric_col == 0 能够正确识别 0, 0.0, '0', '0.00' 等所有形式的零
        condition_delete_a = numeric_col.isna() | (numeric_col == 0)
        # --- 删除条件 B: 代码在暂停申购列表中 ---
        condition_delete_b = col_code.isin(paused_codes)

        # --- 最终保留逻辑 ---
        # 只有既不满足删除条件 A，也不满足删除条件 B 的行，才被保留
        # 即：净值有效 AND 代码不在暂停列表中
        df_cleaned = df[~condition_delete_a & ~condition_delete_b]

        print(f"清理后数据行数: {len(df_cleaned)}")
        print(f"删除的行数: {len(df) - len(df_cleaned)}")

        # 保存清理后的数据
        df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ 文件已保存至: {output_path}")

    def same_code(self):
        df_etf = pd.read_csv('data\\fund_lof.csv')
        df_day = pd.read_csv('data\\fund_day.csv')

        # 3. 确保两表的“基金代码”列都是字符串（防止 0 开头被截断）
        df_etf['代码'] = df_etf['代码'].astype(str)
        df_day['代码'] = df_day['代码'].astype(str)

        # 4. 找出共同的基金代码
        common_codes = set(df_etf['代码']) & set(df_day['代码'])
        print(f"共有 {len(common_codes)} 只基金在两个文件中同时存在")

        # 5. 筛选交集行
        df_etf_common = df_etf[df_etf['代码'].isin(common_codes)]
        df_day_common = df_day[df_day['代码'].isin(common_codes)]

        # 6. 保存结果（保留原列名）
        df_etf_common.to_csv('data\\fund_lof.csv', index=False, encoding='utf-8-sig')
        df_day_common.to_csv('data\\fund_day.csv', index=False, encoding='utf-8-sig')

        print("✅ 已成功保存带列名的交集数据：")
        print(f"  - fund_lof.csv ({len(df_etf_common)} 行)")
        print(f"  - fund_day.csv ({len(df_day_common)} 行)")

    # ================= 新增：涨停板数据获取相关方法 =================

    def get_limit_up_stocks(self, date_str, max_retries=3):
        """
        获取指定日期的涨停股票代码和名称，带重试机制
        """
        url = "https://flash-api.xuangubao.cn/api/pool/detail"

        params = {
            "pool_name": "limit_up",
            "date": date_str
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        for attempt in range(max_retries):
            try:
                print(f"  尝试 {attempt + 1}/{max_retries}...", end=' ')
                response = requests.get(url, params=params, timeout=30, headers=headers)

                if response.status_code == 200:
                    result = response.json()

                    if result.get('code') == 20000 and result.get('data'):
                        stock_list = result['data']
                        stocks = []

                        for item in stock_list:
                            symbol = item.get('symbol', '')
                            name = item.get('stock_chi_name', '')

                            # 获取6位股票代码
                            code_6 = symbol[:6] if len(symbol) >= 6 else symbol

                            # 过滤掉 ST 股
                            if 'ST' not in name and 'st' not in name:
                                stocks.append({
                                    '日期': date_str,
                                    '代码': code_6,
                                    '名称': name
                                })

                        print(f"成功，找到 {len(stocks)} 只")
                        return stocks
                    else:
                        print("无数据")
                        return []
                else:
                    print(f"状态码: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    continue

            except Exception as e:
                print(f"异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue

        print("失败")
        return []

    def fetch_zt_data(self):
        """获取最近5天的涨停数据并保存到 zt_list.csv"""
        list_path = os.path.join(self.data_dir, 'zt_list.csv')

        # 1. 计算最近5个自然日
        end_date = datetime.now()
        dates_to_fetch = []
        for i in range(5):
            date = end_date - timedelta(days=i)
            dates_to_fetch.append(date.strftime('%Y-%m-%d'))

        dates_to_fetch.reverse()  # 从早到晚

        # 2. 下载并合并新数据
        all_new_stocks = []
        success_count = 0

        for date_str in dates_to_fetch:
            print(f"正在下载 {date_str} 的数据...")
            stocks = self.get_limit_up_stocks(date_str)
            if stocks:
                all_new_stocks.extend(stocks)
                success_count += 1

        if not all_new_stocks:
            print("最近5天没有新数据")
            return

        # 3. 读取现有数据并合并
        df_existing = pd.DataFrame()
        if os.path.exists(list_path):
            df_existing = pd.read_csv(list_path, dtype={'代码': str})
            df_existing['代码'] = df_existing['代码'].astype(str).str.zfill(6)

        df_new = pd.DataFrame(all_new_stocks)
        df_new['代码'] = df_new['代码'].astype(str).str.zfill(6)

        # 合并并去重（基于日期+代码）
        if not df_existing.empty:
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=['日期', '代码'], keep='last')
        else:
            df_combined = df_new

        # 按日期排序
        df_combined = df_combined.sort_values('日期')

        # 4. 保存到 zt_list.csv
        df_combined.to_csv(list_path, index=False, encoding='utf-8-sig')

        print(f"✅ 涨停数据已更新（新增 {len(all_new_stocks)} 条，总共 {len(df_combined)} 条）")

    def get_tdx_path(self):
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

    def update_stock_concepts(self):
        """更新所属概念 (原 update_gn 逻辑)"""
        TDX_PATH = self.get_tdx_path()
        if TDX_PATH is None:
            print("❌ 错误：未找到 TDX_PATH 配置，请检查 setup.json 文件")
            return "未找到通达信路径"

        file_path = os.path.join(TDX_PATH, 'T0002', 'hq_cache', 'infoharbor_block.dat')
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在：{file_path}")
            return "通达信文件不存在"

        try:
            with open(file_path, "rb") as f:
                content = f.read().decode("gbk", errors="ignore")
                gn_segments = re.findall(r'#GN_(.+?)\r\n', content, re.DOTALL)
                gn_segments = [f"#GN_{seg}" for seg in gn_segments]

                pattern2 = r'#GN_(.+?),'
                pattern3 = r'\d+#\d{6}'

                stock_gn_pairs = []

                for seg in gn_segments:
                    match_gn = re.findall(pattern2, seg, re.DOTALL)
                    if not match_gn:
                        continue
                    block_gn = match_gn[0]
                    blocks_codes = re.findall(pattern3, seg, re.DOTALL)
                    for code in blocks_codes:
                        stock_code = code[2:8]
                        stock_gn_pairs.append((stock_code, block_gn))

                # 【修正1】列名改为 '代码'，与后续逻辑保持一致
                df = pd.DataFrame(stock_gn_pairs, columns=['代码', '概念'])

                # 【修正2】groupby 也相应改为 '代码'
                grouped = df.groupby('代码')['概念'].apply(list).reset_index()
                max_sectors = grouped['概念'].apply(len).max()

                # 【修正3】result_data 键名改为 '代码'
                result_data = {'代码': grouped['代码']}
                for i in range(max_sectors):
                    result_data[f'概念{i + 1}'] = grouped['概念'].apply(lambda x: x[i] if i < len(x) else '')

                result_df = pd.DataFrame(result_data)

                # ========== 修改开始：读取 stock_name.csv ==========
                name_file = 'data\\stock_name.csv'
                if not os.path.exists(name_file):
                    print(f"⚠️ 股票名称文件未找到：{name_file}")
                    return "股票名称文件缺失"

                try:
                    name_df = pd.read_csv(name_file, dtype=str)
                except Exception as e:
                    print(f"❌ 读取 {name_file} 失败: {e}")
                    return "读取名称文件失败"
                # ========== 修改结束 ==========

                result_df['代码'] = result_df['代码'].astype(str).str.zfill(6)
                name_df['代码'] = name_df['代码'].astype(str).str.zfill(6)

                name_df = name_df.drop_duplicates(subset=['代码'], keep='first')

                # 合并：假设 stock_name.csv 中有 '名称' 列
                merged_df = result_df.merge(name_df[['代码', '名称']], on='代码', how='left')

                cols = ['代码', '名称'] + [col for col in merged_df.columns if col.startswith('概念')]
                merged_df = merged_df[cols]

                final_df = merged_df
                final_df['代码'] = pd.to_numeric(final_df['代码'], errors='coerce').astype('Int64')

                # 列名重命名 (保持最终输出文件列名为 '代码', '名称')
                final_df = final_df.rename(columns={'代码': '代码', '名称': '名称'})

                # ========== 保存为 stock_gn.csv ==========
                output_file = 'data\\stock_gn.csv'
                final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"✅ 所属概念更新成功: {len(final_df)} 只股票，保存至 {output_file}")
                # ========== 修改结束 ==========
                return f"更新成功 {len(final_df)} 只"

        except Exception as e:
            print(f"❌ 更新所属概念失败: {e}")
            return f"更新失败: {e}"

    def calculate_zt_stat(self):
        """计算涨停板块统计 (原 ensure_stat_data_updated 逻辑)"""
        list_path = os.path.join(self.data_dir, 'zt_list.csv')
        stat_path = os.path.join(self.data_dir, 'zt_stat.csv')

        if not os.path.exists(list_path):
            return

        # 读取 zt_list.csv 获取所有存在涨停的日期
        try:
            df_list = pd.read_csv(list_path, dtype={'代码': str})
            df_list['代码'] = df_list['代码'].astype(str).str.zfill(6)
            dates_in_list = set(df_list['日期'].unique())
        except Exception as e:
            print(f"读取 zt_list.csv 失败: {e}")
            return

        # 读取已存在的统计数据日期
        dates_in_stat = set()
        if os.path.exists(stat_path):
            try:
                df_stat_exist = pd.read_csv(stat_path, dtype={'日期': str})
                dates_in_stat = set(df_stat_exist['日期'].unique())
            except Exception as e:
                print(f"读取 zt_stat.csv 失败（可能为空），将重新生成: {e}")

        # 找出需要计算的新日期
        missing_dates = sorted(list(dates_in_list - dates_in_stat))
        if not missing_dates:
            print("统计数据已是最新，无需重新计算")
            return

        print(f"发现 {len(missing_dates)} 个新日期需要统计: {missing_dates}")

        # 加载概念数据
        # ========== 修改开始：读取 stock_gn.csv ==========
        concepts_file = 'data\\stock_gn.csv'
        df_stocks = pd.DataFrame()
        if os.path.exists(concepts_file):
            try:
                # 使用 read_csv 替代 read_excel
                df_stocks = pd.read_csv(concepts_file, dtype=str)
                df_stocks['代码'] = df_stocks['代码'].astype(str).str.zfill(6)
            except Exception as e:
                print(f"读取概念文件 {concepts_file} 失败: {e}")
        else:
            print(f"⚠️ 概念文件 {concepts_file} 不存在")
            return
        # ========== 修改结束 ==========

        # 加载排除词
        exclude_words = set()
        if os.path.exists("set_key.txt"):
            try:
                with open("set_key.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                    exclude_words = set(word for word in content.split() if word.strip())
            except:
                pass

        # 批量计算缺失日期的统计
        new_stats = []
        for date_str in missing_dates:
            daily_df = df_list[df_list['日期'] == date_str]
            if daily_df.empty:
                continue

            daily_concept_counts = {}
            for _, row in daily_df.iterrows():
                code = row['代码']
                # 查概念
                if not df_stocks.empty:
                    stock_info = df_stocks[df_stocks['代码'] == code]
                    if not stock_info.empty:
                        stock_data = stock_info.iloc[0]
                        for i in range(1, 47):
                            col_name = f'概念{i}'
                            concept = stock_data.get(col_name)
                            if pd.notna(concept) and concept.strip() and concept not in exclude_words:
                                daily_concept_counts[concept] = daily_concept_counts.get(concept, 0) + 1

            # 收集该日的统计结果
            for concept, count in daily_concept_counts.items():
                new_stats.append({
                    '日期': date_str,
                    '板块名称': concept,
                    '概念重复次数': count
                })

        if not new_stats:
            print("未提取到任何新统计数据")
            return

        # 保存到 CSV
        try:
            df_new = pd.DataFrame(new_stats)
            # 确保目录存在
            os.makedirs('data', exist_ok=True)

            if os.path.exists(stat_path):
                # 追加模式，不写表头
                df_new.to_csv(stat_path, mode='a', header=False, index=False, encoding='utf-8-sig')
                print(f"✅ 已追加 {len(new_stats)} 条统计数据到 zt_stat.csv")
            else:
                # 首次写入
                df_new.to_csv(stat_path, mode='w', header=True, index=False, encoding='utf-8-sig')
                print(f"✅ 已新建并保存 {len(new_stats)} 条统计数据到 zt_stat.csv")

        except Exception as e:
            print(f"❌ 保存统计数据失败: {e}")

    # ================= 结束：新增方法 =================
    def stock_day(self,code) -> Optional[pd.DataFrame]:
        tdx_dir: str = self.get_tdx_path()

        # 【新增】增加路径不存在的判断，防止后续报错
        if tdx_dir is None:
            print(f"❌ 错误：未找到通达信路径配置，无法获取股票 {code} 日线数据")
            return None

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
            if 'code' not in df1.columns:
                df1['code'] = code
            # 仅保留需要的列，并确保顺序
            required_cols = ['date', 'code','open', 'high', 'low', 'close', 'volume', 'amount']
            df = df1[required_cols].copy()

            # 转换日期格式（mootdx 的 date 通常是 int 类型，如 20231201）
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

            # 价格字段保留两位小数
            price_cols = ['open', 'high', 'low', 'close']

            df[price_cols] = df[price_cols].round(2)





            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            df['rate'] = 100 * (df['close'] - df['close'].shift(1)) / df['close'].shift(1)
            df['rate'] = df['rate'].round(2)

            # df2 = df[['date','code', 'rate']].copy()


            # # 保存 CSV（自动包含 header）
            # output_path = os.path.join(output_dir, f"blk.csv")
            # df2.to_csv(output_path, index=False, date_format='%Y-%m-%d')
            # print(f"✅ 已成功保存：{output_path}")

            return df

        except Exception as e:
            print(f"❌ 处理股票 {code} 时出错: {e}")
            return None

    def blk_rate(self):
        with open('data\\板块指数.txt', 'r', encoding='gbk') as f:
            lines = f.readlines()

        # 解析文件内容为DataFrame
        data = []
        for line in lines:
            parts = line.strip().split()
            # ✅ 修复1：过滤表头，确保代码是数字（通达信板块指数代码通常以8开头）
            if len(parts) >= 2 and parts[0].isdigit():
                data.append({
                    'code': parts[0],
                    'name': parts[1]
                })

        df_codes = pd.DataFrame(data)
        all_data = []

        # ✅ 修复2：遍历时同时获取 code 和 name
        for index, row in df_codes.iterrows():
            code = row['code']
            name = row['name']

            result = self.stock_day(code)
            if result is not None:
                # 手动添加 name 列
                result['name'] = name
                all_data.append(result[['date', 'code', 'name', 'rate']])
            print(code)

        # 合并所有数据并保存
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)

            # --- 新增代码开始 ---
            # 筛选日期在 2025-1-1 之后的数据
            final_df = final_df[final_df['date'] > pd.to_datetime('2025-01-01')]
            # --- 新增代码结束 ---

            output_path = os.path.join('data', 'blk.csv')
            final_df.to_csv(output_path, index=False, date_format='%Y-%m-%d')
            print(f"✅ 已成功保存所有数据：{output_path}，共 {len(final_df)} 条记录")
            return final_df

        return None

    def ztjx(self):
        import glob

        # ===== 配置文件路径 =====
        html_dir = 'data'  # HTML文件所在目录
        csv_file = 'data/ztjx.csv'  # 输出CSV文件路径

        # ===== 创建目录（如果不存在）=====
        os.makedirs('data', exist_ok=True)

        # ===== 读取现有CSV数据（用于去重）=====
        existing_data = {}  # 用字典存储，key为"日期+代码"，value为数据行

        if os.path.exists(csv_file):
            print("正在读取现有CSV文件...")
            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    header = next(reader)  # 跳过表头
                    for row in reader:
                        if len(row) >= 6:  # 确保有足够列
                            # 用"日期+代码"作为唯一键
                            key = f"{row[0]}_{row[5]}"  # 日期_代码
                            existing_data[key] = row
                print(f"  已读取 {len(existing_data)} 条现有数据")
            except Exception as e:
                print(f"  读取CSV失败: {e}")
                existing_data = {}

        # ===== 准备新数据列表 =====
        new_data = {}  # 本次读取的新数据

        # ===== 获取所有HTML文件 =====
        html_files = glob.glob(os.path.join(html_dir, '韭研公社-*异动.html'))

        if len(html_files) == 0:
            print("⚠️  警告：未找到任何HTML文件！")
            print(f"   请确保HTML文件放在 '{html_dir}' 目录下")
        else:
            print(f"\n找到 {len(html_files)} 个HTML文件")
            print("=" * 80)

            # ===== 遍历每个HTML文件 =====
            for html_file in sorted(html_files):
                filename = os.path.basename(html_file)
                print(f"正在处理: {filename}")

                # 从文件名提取日期
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', html_file)
                date = date_match.group(1) if date_match else ''

                try:
                    html_content = None
                    for encoding in ['utf-8', 'gbk', 'gb2312']:
                        try:
                            with open(html_file, 'r', encoding=encoding) as f:
                                html_content = f.read()
                            break
                        except UnicodeDecodeError:
                            continue

                    if html_content is None:
                        print(f"  ❌ 无法识别文件编码，跳过: {filename}")
                        continue

                    soup = BeautifulSoup(html_content, 'html.parser')

                    # 找到所有板块模块
                    modules = soup.find_all('li', class_='module')

                    file_count = 0

                    for module in modules:
                        # 提取大类名
                        category_div = module.find('div', class_='fs18-bold lf')
                        category = category_div.get_text(strip=True) if category_div else ''

                        # 提取涨停数量
                        number_div = module.find('div', class_='number lf')
                        number = number_div.get_text(strip=True) if number_div else ''

                        # 提取题材
                        theme_div = module.find('div', class_='mtb8 fs16 text-justify')
                        theme = theme_div.get_text(strip=True) if theme_div else ''

                        # 提取股票信息
                        rows = module.find_all('li', class_='row')

                        for row in rows:
                            # 股票名称
                            name_div = row.find('div', class_='shrink fs15-bold')
                            name = name_div.get_text(strip=True) if name_div else ''

                            # 代码
                            code_div = row.find('div', class_='shrink fs12-bold-ash force-wrap')
                            code = code_div.get_text(strip=True) if code_div else ''

                            # 最新价
                            price_div = row.find('div', class_='shrink number')
                            price = price_div.get_text(strip=True) if price_div else ''

                            # 强度
                            strength_div = row.find('div', class_='sort')
                            strength = strength_div.get_text(strip=True) if strength_div else ''

                            # 涨跌幅
                            change_div = row.find('div', class_='shrink cred')
                            change = change_div.get_text(strip=True) if change_div else ''

                            # 涨停时间
                            time_div = row.find('div', class_='shrink fs15')
                            limit_time = time_div.get_text(strip=True) if time_div else ''

                            # 解析
                            analysis_pre = row.find('pre', class_='pre tl hilll')
                            analysis = analysis_pre.get_text(strip=True) if analysis_pre else ''

                            if name:
                                # 构建数据行
                                data_row = [
                                    date, category, number, theme,
                                    name, code, price, strength,
                                    change, limit_time, analysis
                                ]

                                # 用"日期+代码"作为唯一键
                                key = f"{date}_{code}"
                                new_data[key] = data_row
                                file_count += 1

                    print(f"  ✅ 提取了 {file_count} 条数据")

                except Exception as e:
                    print(f"  ❌ 处理失败: {str(e)}")
                    continue

            # ===== 合并数据（新数据覆盖旧数据）=====
            print("\n" + "=" * 80)
            print("正在合并数据...")

            # 统计新增和更新
            add_count = 0
            update_count = 0

            for key, row in new_data.items():
                if key not in existing_data:
                    add_count += 1
                else:
                    update_count += 1
                existing_data[key] = row  # 新数据覆盖旧数据

            # ===== 按日期排序 =====
            all_data = sorted(existing_data.values(), key=lambda x: x[0], reverse=True)

            # ===== 保存到CSV文件 =====
            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['日期', '大类名', '涨停数量', '题材', '股票名称', '代码',
                                 '最新价', '强度', '涨跌幅', '涨停时间', '解析'])
                writer.writerows(all_data)

            print("=" * 80)
            print(f"📊 数据统计:")
            print(f"   - 现有数据: {len(existing_data) - add_count} 条")
            print(f"   - 新增数据: {add_count} 条")
            print(f"   - 更新数据: {update_count} 条")
            print(f"   - 总计数据: {len(all_data)} 条")
            print(f"\n✅ 已保存到: {csv_file}")

    def process_lbtt_data(self, df):
        """
        处理 lbtt 数据：筛选列、重命名、格式转换
        """
        columns_to_keep = ['rqex', 'lbts', 'ZQDM', 'ztyy', 'fde', 'ZQJC', 'ztyy2', 'ztsj', 'kbcs', 'sshy']

        missing_cols = [col for col in columns_to_keep if col not in df.columns]
        if missing_cols:
            print(f"警告：缺少以下列：{missing_cols}")

        existing_cols = [col for col in columns_to_keep if col in df.columns]
        df = df[existing_cols].copy()

        rename_dict = {
            'rqex': '日期', 'lbts': '连板高度', 'ZQDM': '代码',
            'ztyy': '原因1', 'fde': '封单额', 'ZQJC': '股票名称',
            'ztyy2': '原因2', 'ztsj': '时间', 'kbcs': '开板次数', 'sshy': '行业'
        }
        df = df.rename(columns=rename_dict)

        # 日期格式转换
        def convert_date(date_str):
            if pd.isna(date_str) or date_str == '' or date_str == 'None':
                return ''
            try:
                date_str = str(int(float(date_str)))
                dt = datetime.strptime(date_str, '%Y%m%d')
                return f"{dt.year}-{dt.month}-{dt.day}"
            except:
                return str(date_str)

        if '日期' in df.columns:
            df['日期'] = df['日期'].apply(convert_date)

        # 封单额转换（除以1亿）
        if '封单额' in df.columns:
            def convert_fde(value):
                try:
                    if pd.isna(value) or value == '' or value == 'None':
                        return 0.00
                    return round(float(value) / 100000000, 2)
                except:
                    return 0.00

            df['封单额'] = df['封单额'].apply(convert_fde)

        return df

    def process_lbss_data(self, df):
        """
        处理 lbss 数据：筛选列、重命名、格式转换
        """
        columns_to_keep = ['N001', 'N002', 'N003', 'N004', 'N005', 'N006',
                           'N007', 'N008', 'N009', 'N010', 'N011', 'N012', 'N013', 'N014']

        missing_cols = [col for col in columns_to_keep if col not in df.columns]
        if missing_cols:
            print(f"警告：缺少以下列：{missing_cols}")

        existing_cols = [col for col in columns_to_keep if col in df.columns]
        df = df[existing_cols].copy()

        rename_dict = {
            'N001': '日期', 'N002': '上涨', 'N003': '下跌', 'N004': '平盘',
            'N005': '涨停', 'N006': '跌停', 'N007': '今日成交', 'N008': '昨日成交',
            'N009': '最火概念1', 'N010': '最火概念1涨停', 'N011': '最火概念2',
            'N012': '最火概念2涨停', 'N013': '最火概念3', 'N014': '最火概念3涨停'
        }
        df = df.rename(columns=rename_dict)

        # 成交额转换（除以1万亿）
        def convert_volume(value):
            try:
                if pd.isna(value) or value == '' or value == 'None':
                    return 0.00
                return round(float(value) / 1000000000000, 2)
            except:
                return 0.00

        if '今日成交' in df.columns:
            df['今日成交'] = df['今日成交'].apply(convert_volume)
        if '昨日成交' in df.columns:
            df['昨日成交'] = df['昨日成交'].apply(convert_volume)

        return df

    def append_to_csv(self, new_df, output_file, key_columns):
        """
        将新数据追加到已有CSV文件中，根据关键字段去重
        """
        if not os.path.exists('data'):
            os.makedirs('data')

        if os.path.exists(output_file):
            existing_df = pd.read_csv(output_file, encoding='utf-8-sig')
            print(f"读取已有数据：{len(existing_df)} 条")

            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=key_columns, keep='last')
            print(f"合并后数据：{len(combined_df)} 条（新增 {len(new_df)} 条，去重后）")
        else:
            combined_df = new_df
            print(f"新建文件：{len(combined_df)} 条")

        combined_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 数据已保存到 {output_file}\n")

    def stock_down(self, type_param, output_file):
        """
        获取涨停股/市场统计数据并保存
        type_param: 1=涨停股数据, 2=市场统计数据
        """
        url = 'http://hot.icfqs.com:7615/TQLEX'
        params = {"Entry": "CWServ.cfg_fx_lbtt", "RI": ""}

        today = datetime.now()
        end_date = today.strftime('%Y-%m-%d')
        three_days_ago = today - timedelta(days=3)
        start_date = three_days_ago.strftime('%Y-%m-%d')



        data = {"Params": [str(type_param), start_date, end_date]}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, params=params, json=data, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            result_dict = json.loads(response.text)

            if result_dict['ErrorCode'] == 0:
                for result_set in result_dict['ResultSets']:
                    col_names = result_set['ColName']
                    contents = result_set['Content']
                    count = result_set['Count']
                    print(f"{'=' * 60}")
                    print(f"类型 {type_param}：获取到 {count} 条数据")

                    df = pd.DataFrame(contents, columns=col_names)

                    if type_param == 1:
                        df = self.process_lbtt_data(df)
                        self.append_to_csv(df, output_file, key_columns=['日期', '代码'])
                    else:
                        df = self.process_lbss_data(df)
                        self.append_to_csv(df, output_file, key_columns=['日期'])
            else:
                print(f"❌ 错误: {result_dict.get('ErrorInfo', '未知错误')}")
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")

    def run(self):

        print("=" * 60)
        print("【开始获取竞价数据并保存】")

        # self.get_all_data()
        # self.extern_user()
        print("=" * 60)
        print("【开始获取ETF净值】")
        self.etf_jz()
        print("=" * 60)
        print("【开始获取涨停股数据】")

        self.stock_down(type_param=1, output_file='data/lbtt.csv')

        # 获取市场统计数据
        self.stock_down(type_param=2, output_file='data/lbss.csv')
        """主运行函数：整合龙虎榜、基金及涨停数据更新"""


        # 1. 原有逻辑：龙虎榜与基金数据
        self.start_realtime_fetch(run_once=True)

        self.convert_lhb_detail_to_lhb_detail_b()
        self.convert_lhb_to_lhb_b()
        self.extract_and_save_yyb()
        self.fund_daily()
        self.fund_etf_and_lof()
        self.fund_etf()
        self.remove_rows_with_empty_col4(input_csv='fund_day.csv', output_csv='fund_day.csv')
        self.remove_rows_with_empty_col4(input_csv='fund_lof.csv', output_csv='fund_lof.csv')
        self.same_code()

        # 2. 新增逻辑：涨停数据、概念及统计
        print("\n===== 开始更新涨停及概念数据 =====")
        self.update_stock_concepts()  # 更新概念 Excel
        self.fetch_zt_data()  # 获取涨停列表

        self.calculate_zt_stat()  # 计算统计
        print("===== 数据更新流程结束 =====")

        self.blk_rate()# 板块指数r的每天涨幅
        self.ztjx()
        # 4. 【新增】热榜数据更新
        print("\n===== 开始更新热榜数据 =====")
        self.ths()
        self.cls()
        self.tdx()
        self.em()

        print("\n" + "=" * 60)
        print("✅ 所有数据更新流程结束")
        print("=" * 60)

if __name__ == '__main__':
    # 示例1：初始化并单次获取数据
    update().run()
    # update().get_all_data()
    # update().extern_user()