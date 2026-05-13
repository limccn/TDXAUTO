import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import csv
import akshare as ak
from openai import OpenAI
import glob
import time
import tabulate
import json
from datetime import datetime
from send_wechat import send_wechat, send_dingtalk

today_str = datetime.now().strftime('%Y-%m-%d')

def encode_text(text):
    """保存前：将换行符和双引号替换成特殊标记"""
    if pd.isna(text) or not text:
        return ""
    text = str(text).replace('"', '【引号】')
    text = text.replace('\n', '【换行】')
    return text

def decode_text(text):
    """读取后：将特殊标记还原成换行符和双引号"""
    if pd.isna(text) or not text:
        return ""
    text = str(text).replace('【换行】', '\n')
    text = text.replace('【引号】', '"')
    return text
def convert_to_yi(val):
    """将金额转换为亿单位，保留2位小数，异常值保留原样"""
    if pd.isna(val) or str(val).strip() == '' or str(val).strip() == '--':
        return val
    try:
        num = float(str(val).replace(',', ''))
        return f"{round(num / 10000, 2):.2f}亿"
    except ValueError:
        return val
def index_sh(DATA_DIR,desktop_path, infile, output, output_etf, output_future, output_a50):
    print('正在获取：当前的大盘指数')
    file = os.path.join(desktop_path, infile)
    try:
        df = pd.read_csv(file, sep='\t', encoding='gbk')
        df.columns = df.columns.str.strip()
        df = df[~df.apply(lambda row: '#数据来源:通达信' in row.astype(str).values, axis=1)]

        # 0列代码、1列名称用iloc硬编码，其余列按名称匹配
        df.columns = df.columns.str.strip().str.replace('%', '').str.replace('Z', '').str.replace('（', '(').str.replace(
            '）', ')')
        df_0 = df.iloc[:, [0, 1]].copy()
        df_0.columns = ['代码', '名称']
        other_names = ['涨幅', '总金额']
        df_selected = pd.concat([df_0, df[[c for c in other_names if c in df.columns]].reset_index(drop=True)], axis=1)

        # 关键清洗：去等号、去空格、强制大写
        df_selected['代码'] = df_selected['代码'].astype(str).str.replace('=', '').str.replace('"',
                                                                                               '').str.strip().str.upper()

        # 总金额转换为亿
        if '总金额' in df_selected.columns:
            df_selected['总金额'] = df_selected['总金额'].apply(convert_to_yi)

        # 1. 主要指数 (增加了 000001 和你提供的 999999)
        index_codes = ['000001', '399001', '399006', '000016', '000300', '000688', '999999', '000852']
        df_index = df_selected[df_selected['代码'].isin(index_codes)].copy()
        print(f"✅ 匹配到指数数量: {len(df_index)}")

        # 2. 宽基ETF
        etf_codes = ['510300', '159915', '510500', '510050', '159922', '159919']
        df_etf = df_selected[df_selected['代码'].isin(etf_codes)].copy()
        print(f"✅ 匹配到ETF数量: {len(df_etf)}")

        # 3. 股指期货 (大写匹配)
        future_codes = ['IHL8', 'IFL8', 'ICL8', 'IML8']
        df_future = df_selected[df_selected['代码'].isin(future_codes)].copy()
        print(f"✅ 匹配到股指期货数量: {len(df_future)}")

        # 4. A50 (大写匹配)
        a50_codes = ['CNY0']
        df_a50 = df_selected[df_selected['代码'].isin(a50_codes)].copy()
        print(f"✅ 匹配到A50数量: {len(df_a50)}")

        # === 保存文件 ===
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        # 保存指数
        df_index.to_csv(os.path.join(DATA_DIR, output), index=False, encoding='utf-8-sig')
        # 保存ETF
        df_etf.to_csv(os.path.join(DATA_DIR, output_etf), index=False, encoding='utf-8-sig')
        # 保存股指期货
        df_future.to_csv(os.path.join(DATA_DIR, output_future), index=False, encoding='utf-8-sig')
        # 保存A50
        df_a50.to_csv(os.path.join(DATA_DIR, output_a50), index=False, encoding='utf-8-sig')

        print(f"✅ 文件已保存至 {DATA_DIR}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


def blk(DATA_DIR,desktop_path, infile='竞价-板块指数*.xls', output='open_3gn.csv'):
    print('正在获取：当前的概念板块数据')
    try:
        files = glob.glob(os.path.join(desktop_path, infile))
        all_data = []
        for file in files:
            df = pd.read_csv(file, sep='\t', encoding='gbk')
            df = df[~df.apply(lambda row: '#数据来源:通达信' in row.astype(str).values, axis=1)]
            df.columns = df.columns.str.strip()
            # 0列代码、1列名称用iloc硬编码，其余列按名称匹配
            # 关键清洗
            df.columns = df.columns.str.strip().str.replace('%', '').str.replace('Z', '').str.replace('（',
                                                                                                      '(').str.replace(
                '）', ')')
            # 0列代码、1列名称用iloc硬编码，其余列按名称匹配
            df_0 = df.iloc[:, [0, 1]].copy()
            df_0.columns = ['代码', '名称']
            other_names = ['涨幅', '涨停数', '跌停数', '涨跌数']
            df_selected = pd.concat([df_0, df[[c for c in other_names if c in df.columns]].reset_index(drop=True)],
                                    axis=1)
            all_data.append(df_selected)
        df_combined = pd.concat(all_data, ignore_index=True)
        split_data = df_combined['涨跌数'].str.split('|', expand=True)
        df_combined['上涨数'], df_combined['下跌数'] = split_data[0], split_data[1]
        df_combined.drop(columns=['涨跌数'], inplace=True)
        df_combined.to_csv(os.path.join(DATA_DIR, output), index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")


def gn_distill(DATA_DIR, prefix='open'):
    in_file = os.path.join(DATA_DIR, 'stock_gn.csv')
    distll_gn = os.path.join(DATA_DIR, f'{prefix}_3gn.csv')
    out_file = os.path.join(DATA_DIR, f'{prefix}_gn_distill.csv')
    try:
        # 1. 读取板块数据
        df_gn = pd.read_csv(distll_gn, encoding='utf-8-sig')
        df_gn['涨幅_num'] = pd.to_numeric(
            df_gn['涨幅'].astype(str).str.replace('%', ''), errors='coerce'
        )
        df_gn['涨停_num'] = pd.to_numeric(df_gn['涨停数'], errors='coerce').fillna(0)
        df_gn['跌停_num'] = pd.to_numeric(df_gn['跌停数'], errors='coerce').fillna(0)

        # 2. 领涨风口
        strong_up = df_gn[(df_gn['涨幅_num'] > 1.0) | (df_gn['涨停_num'] >= 2)]
        # 3. 领跌重灾区
        strong_down = df_gn[(df_gn['涨幅_num'] < -1.0) | (df_gn['跌停_num'] >= 2)]
        # 4. 合并白名单
        core_concepts = set(strong_up['名称'].dropna().str.strip()) | \
                        set(strong_down['名称'].dropna().str.strip())
        print(f"✅ [{prefix}] 筛选概念：领涨{len(strong_up)}个 + 领跌{len(strong_down)}个 = 共{len(core_concepts)}个")

        # 5. 读取股票概念文件
        df_stock = pd.read_csv(in_file, encoding='utf-8-sig', dtype={'代码': str})
        concept_cols = df_stock.columns[2:].tolist()

        # 6. 过滤
        for col in concept_cols:
            df_stock[col] = df_stock[col].apply(
                lambda x: x if pd.isna(x) or str(x).strip() in core_concepts else None
            )

        # 7. 左对齐压缩
        def shift_left(row):
            vals = row.dropna().tolist()
            return pd.Series(vals + [None] * (len(row) - len(vals)), index=row.index)
        df_stock[concept_cols] = df_stock[concept_cols].apply(shift_left, axis=1)
        # 7.5 新增：删除压缩后全空的列（大幅减小CSV体积）
        df_stock.dropna(axis=1, how='all', inplace=True)

        # 8. 保存
        df_stock.to_csv(out_file, index=False, encoding='utf-8-sig')
        print(f"✅ [{prefix}] 概念筛选完成 → {out_file}")
    except Exception as e:
        print(f"❌ [{prefix}] 发生错误: {e}")


def target(DATA_DIR, prefix):
    print('正在进行第8项数据：目标股池')
    try:
        df_target = pd.read_csv(os.path.join(DATA_DIR, f'{prefix}_377.csv'), encoding='utf-8-sig', dtype={'代码': str})[['代码']].copy()
        df_gn = pd.read_csv(os.path.join(DATA_DIR, f'{prefix}_gn_distill.csv'), encoding='utf-8-sig', dtype={'代码': str})
        df_stock = pd.read_csv(os.path.join(DATA_DIR, f'{prefix}_4stock.csv'), encoding='utf-8-sig', dtype={'代码': str})
        df_stock['代码'] = df_stock['代码'].str.replace('="', '', regex=False).str.replace('"', '', regex=False)
        concept_cols = [col for col in df_gn.columns if col.startswith('概念')]
        df_gn['概念'] = df_gn[concept_cols].apply(
            lambda row: ','.join([str(v) for v in row if pd.notna(v) and str(v).strip() != '']), axis=1)
        df_result = df_target.merge(df_gn[['代码', '名称', '概念']], on='代码', how='left')
        stock_cols = ['代码', '细分行业', '涨幅', '开盘换手', '开盘金额', '封单额', '量比', '内外比', '3日涨幅',
                      '5日涨幅', '主力净额', '主力净比', '几天几板', '流通市值', '市盈(动)']
        if '相关新闻' in df_stock.columns:
            stock_cols.append('相关新闻')
        df_result = df_result.merge(df_stock[stock_cols], on='代码', how='left')
        df_result.drop_duplicates(subset=['代码'], keep='last').to_csv(os.path.join(DATA_DIR,f'{prefix}_377.csv'), index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")


def target_close(DATA_DIR,output, stock_file):
    print('正在进行第8项数据：目标股池')
    try:
        df_target = pd.read_csv(os.path.join(DATA_DIR, output), encoding='utf-8-sig', dtype={'代码': str})[
            ['代码']].copy()
        df_gn = pd.read_csv(os.path.join(DATA_DIR, 'close_gn_distill.csv'), encoding='utf-8-sig', dtype={'代码': str})
        df_stock = pd.read_csv(os.path.join(DATA_DIR, stock_file), encoding='utf-8-sig', dtype={'代码': str})
        df_stock['代码'] = df_stock['代码'].str.replace('="', '', regex=False).str.replace('"', '', regex=False)
        concept_cols = [col for col in df_gn.columns if col.startswith('概念')]
        df_gn['概念'] = df_gn[concept_cols].apply(
            lambda row: ','.join([str(v) for v in row if pd.notna(v) and str(v).strip() != '']), axis=1)
        df_result = df_target.merge(df_gn[['代码', '名称', '概念']], on='代码', how='left')
        df_result = df_result.merge(df_stock[
                                        ['代码',  '细分行业', '涨幅', '封单额', '量比', '内外比', '3日涨幅', '5日涨幅',
                                   '主力净额', '主力净比', '换手', '总金额', '几天几板', '振幅', '流通市值','市盈(动)']], on='代码', how='left')
        df_result.drop_duplicates(subset=['代码'], keep='last').to_csv(os.path.join(DATA_DIR, output), index=False,
                                                                       encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")


def stock(DATA_DIR, desktop_path, input='竞价-个股数据*.xls', output='open_4stock.csv'):
    try:
        files = glob.glob(os.path.join(desktop_path, input))
        all_data = []
        for file in files:
            df = pd.read_csv(file, sep='\t', encoding='gbk')
            df = df[~df.apply(lambda row: '#数据来源:通达信' in row.astype(str).values, axis=1)]
            df.columns = df.columns.str.strip()
            df.columns = df.columns.str.strip().str.replace('%', '').str.replace('Z', '').str.replace('（', '(').str.replace(
                '）', ')')
            df_0 = df.iloc[:, [0, 1]].copy()
            df_0.columns = ['代码', '名称']
            other_names = ['细分行业', '涨幅', '开盘换手', '开盘金额', '封单额', '量比', '内外比', '3日涨幅', '5日涨幅', '主力净额', '主力净比', '几天几板', '流通市值', '市盈(动)']
            df_selected = pd.concat([df_0, df[[c for c in other_names if c in df.columns]].reset_index(drop=True)], axis=1)
            df_selected = df_selected.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            df_selected['流通市值'] = df_selected['流通市值'].str.strip()
            for col in ['开盘金额', '封单额', '主力净额']:
                if col in df_selected.columns:
                    df_selected[col] = df_selected[col].apply(convert_to_yi)
            df_selected['名称'] = df_selected['名称'].str.replace(
                r'\.(SH|SZ|BJ)$|[\(（](主板|创业板|科创板|北交所)[\)）]$', '', regex=True)
            all_data.append(df_selected)
        df_final = pd.concat(all_data, ignore_index=True)

        # ========== 关键修复：合并新闻前先清洗代码格式 ==========
        df_final['代码'] = df_final['代码'].str.replace('="', '', regex=False).str.replace('"', '', regex=False)

        # ========== 新增：合并本地相关新闻 ==========
        news_file = os.path.join(DATA_DIR, 'news_distill.csv')
        if os.path.exists(news_file):
            try:
                df_news = pd.read_csv(news_file, encoding='utf-8-sig', dtype={'代码': str})
                df_news['代码'] = df_news['代码'].astype(str).str.strip()
                df_news = df_news[df_news['相关新闻'].notna() & (df_news['相关新闻'].str.strip() != '')]
                df_news_grouped = df_news.groupby('代码')['相关新闻'].apply(lambda x: ' | '.join(x)).reset_index()
                df_final = df_final.merge(df_news_grouped, on='代码', how='left')
                df_final['相关新闻'] = df_final['相关新闻'].fillna("")
                matched_count = (df_final['相关新闻'] != "").sum()
                print(f"✅ 成功匹配隔夜新闻：共 {matched_count} 只个股有消息面催化")
            except Exception as e:
                df_final['相关新闻'] = ""
                print(f"⚠️ 匹配新闻失败: {e}")
        else:
            df_final['相关新闻'] = ""

        # ==========================================
        df_final.to_csv(os.path.join(DATA_DIR, output), index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")

def stock_close(DATA_DIR,desktop_path, input, output):
    try:
        files = glob.glob(os.path.join(desktop_path, input))
        all_data = []
        for file in files:
            df = pd.read_csv(file, sep='\t', encoding='gbk')
            df = df[~df.apply(lambda row: '#数据来源:通达信' in row.astype(str).values, axis=1)]
            df.columns = df.columns.str.strip()
            # 关键清洗
            df.columns = df.columns.str.strip().str.replace('%', '').str.replace('Z', '').str.replace('（',
                                                                                                      '(').str.replace(
                '）', ')')
            # 0列代码、1列名称用iloc硬编码，其余列按名称匹配
            df_0 = df.iloc[:, [0, 1]].copy()
            df_0.columns = ['代码', '名称']
            other_names = ['细分行业', '涨幅', '封单额', '量比', '内外比', '3日涨幅', '5日涨幅',
                                   '主力净额', '主力净比', '换手', '总金额', '几天几板', '振幅', '流通市值','市盈(动)']
            df_selected = pd.concat([df_0, df[[c for c in other_names if c in df.columns]].reset_index(drop=True)],
                                    axis=1)
            df_selected = df_selected.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            df_selected['流通市值'] = df_selected['流通市值'].str.strip()
            for col in ['总金额', '封单额', '主力净额']:
                if col in df_selected.columns:
                    df_selected[col] = df_selected[col].apply(convert_to_yi)

            df_selected['名称'] = df_selected['名称'].str.replace(
                r'\.(SH|SZ|BJ)$|[\(（](主板|创业板|科创板|北交所)[\)）]$', '', regex=True)
            all_data.append(df_selected)
        pd.concat(all_data, ignore_index=True).to_csv(os.path.join(DATA_DIR, output), index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")


files_map_open = {
            '4551TDXRG.blk': 'open_50.csv',
            '311zrsb.blk': 'open_1b.csv',
            'eb.blk': 'open_2b.csv',
            'sb.blk': 'open_3b.csv',
            'sb1.blk': 'open_4b.csv',
            'wb.blk': 'open_5b.csv',
            '377dcjl.blk': 'open_377.csv'
        }
files_map_close = {
            '4551TDXRG.blk': 'close_50.csv',
            '311zrsb.blk': 'close_1b.csv',
            'eb.blk': 'close_2b.csv',
            'sb.blk': 'close_3b.csv',
            'sb1.blk': 'close_4b.csv',
            'wb.blk': 'close_5b.csv',
            '377dcjl.blk': 'close_377.csv'
        }
def tdx_hot(DATA_DIR,files_map, config):
    print('正在获取：通达信热股及连板股列表')
    if not config:
        return
    block_dir = os.path.join(config.get('TDX_PATH', ''), 'T0002', 'blocknew')

    try:
        for filename, save_name in files_map.items():
            file_path = os.path.join(block_dir, filename)
            if not os.path.exists(file_path):
                continue
            codes = [line.strip()[-6:] for line in open(file_path, 'r', encoding='gbk', errors='ignore') if line.strip()]
            pd.DataFrame(codes, columns=['代码']).to_csv(os.path.join(DATA_DIR, save_name), index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")

def zt(DATA_DIR,ztfile,dtfile):
    print('正在下载：当前涨停、跌停股的数据')
    today = datetime.now().strftime('%Y%m%d')
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    try:
        zt_df = ak.stock_zt_pool_em(date=today)
        if not zt_df.empty:
            zt_df[['代码']].to_csv(os.path.join(DATA_DIR, ztfile), index=False, encoding='utf-8-sig')
        dt_df = ak.stock_zt_pool_dtgc_em(date=today)
        if not dt_df.empty:
            dt_df[['代码']].to_csv(os.path.join(DATA_DIR, dtfile), index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")


files_list_open = ['open_50.csv', 'open_1b.csv', 'open_2b.csv', 'open_3b.csv', 'open_4b.csv', 'open_5b.csv', 'open_377.csv', 'open_zt.csv', 'open_dt.csv']
files_list_close = ['close_50.csv', 'close_1b.csv', 'close_2b.csv', 'close_3b.csv', 'close_4b.csv', 'close_5b.csv', 'close_377.csv', 'close_zt.csv', 'close_dt.csv']

def zt_pre(DATA_DIR,files_list, stock_file):
    print('正在处理：连板晋级、通达信热股')
    try:
        df_stock = pd.read_csv(os.path.join(DATA_DIR, stock_file), encoding='utf-8-sig', dtype={'代码': str})
        df_stock['代码'] = df_stock['代码'].str.replace('="', '', regex=False).str.replace('"', '', regex=False)
        df_stock = df_stock[
            ['代码', '名称', '细分行业', '涨幅', '开盘换手', '开盘金额', '封单额', '量比', '内外比',
                                   '3日涨幅', '5日涨幅', '主力净额', '主力净比', '几天几板', '流通市值', '市盈(动)', '相关新闻']]
        name_file = os.path.join(DATA_DIR, 'stock_name.csv')
        if os.path.exists(name_file):
            df_name = pd.read_csv(name_file, encoding='utf-8-sig', dtype={'代码': str})[['代码', '名称']].copy()
        else:
            df_name = None
        if df_name is not None:
            df_stock = df_stock.drop(columns=['名称'])
        for file_name in files_list:
            file_path = os.path.join(DATA_DIR, file_name)
            if not os.path.exists(file_path):
                continue
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype={'代码': str})[['代码']].copy()
            if df_name is not None:
                df = df.merge(df_name, on='代码', how='left')
            df.merge(df_stock, on='代码', how='left').drop_duplicates(subset=['代码'], keep='last').to_csv(
                file_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")

def zt_pre_close(DATA_DIR,files_list, stock_file):
    print('正在处理：连板晋级、通达信热股')
    try:
        df_stock = pd.read_csv(os.path.join(DATA_DIR, stock_file), encoding='utf-8-sig', dtype={'代码': str})
        df_stock['代码'] = df_stock['代码'].str.replace('="', '', regex=False).str.replace('"', '', regex=False)
        df_stock = df_stock[
            ['代码', '名称', '细分行业', '涨幅', '封单额', '量比', '内外比', '3日涨幅', '5日涨幅',
                                   '主力净额', '主力净比', '换手', '总金额', '几天几板', '振幅', '流通市值','市盈(动)']]

        name_file = os.path.join(DATA_DIR, 'stock_name.csv')
        if os.path.exists(name_file):
            df_name = pd.read_csv(name_file, encoding='utf-8-sig', dtype={'代码': str})[['代码', '名称']].copy()
        else:
            df_name = None
        if df_name is not None:
            df_stock = df_stock.drop(columns=['名称'])
        for file_name in files_list:
            file_path = os.path.join(DATA_DIR, file_name)
            if not os.path.exists(file_path):
                continue
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype={'代码': str})[['代码']].copy()
            if df_name is not None:
                df = df.merge(df_name, on='代码', how='left')
            df.merge(df_stock, on='代码', how='left').drop_duplicates(subset=['代码'], keep='last').to_csv(
                file_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"发生错误: {e}")




def get_csv_content(DATA_DIR,filename, max_rows=450, sort_by=None, ascending=False):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return f"[文件 {filename} 不存在]"
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        if 'a50' in filename.lower() and '总金额' in df.columns:
            df = df.drop(columns=['总金额'])
        if sort_by and sort_by in df.columns:
            if df[sort_by].dtype == object:
                df[sort_by] = pd.to_numeric(df[sort_by].astype(str).str.replace('%', '').str.replace(',', ''), errors='coerce')
            df = df.sort_values(by=sort_by, ascending=ascending)
        return df.head(max_rows).to_markdown(index=False, floatfmt=".2f")
    except Exception as e:
        return f"[读取 {filename} 失败: {e}]"

def send(result_text, text):
    try:
        max_len = 1500
        if len(result_text) > max_len:
            parts = [result_text[i:i + max_len] for i in range(0, len(result_text), max_len)]
            for i, part in enumerate(parts):
                send_wechat(f"【{today_str}{text}-{i + 1}】\n{part}")
                send_dingtalk(f"【{today_str}{text}-{i + 1}】\n{part}")
        else:
            send_wechat(f"【{today_str}{text}】\n" + result_text)
            send_dingtalk(f"【{today_str}{text}】\n" + result_text)
    except Exception as e:
        print(f"发送失败: {e}")

def saved(DATA_DIR,result_text,output_file, title):
    try:
        file_b_path = os.path.join(DATA_DIR, output_file)
        encoded_text = encode_text(result_text)
        if os.path.exists(file_b_path):
            df_existing = pd.read_csv(file_b_path, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
            df_existing = df_existing[df_existing['日期'] != today_str]
        else:
            df_existing = pd.DataFrame(columns=['日期', title])
        new_row = pd.DataFrame([{'日期': today_str, title: encoded_text}])
        df_final = pd.concat([df_existing, new_row], ignore_index=True)
        df_final.to_csv(file_b_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        print(f"✅ {title}已保存至: {file_b_path}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")

if __name__ == '__main__':
    gn_distill(DATA_DIR = 'data')