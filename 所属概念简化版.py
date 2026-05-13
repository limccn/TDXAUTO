
import re
import pandas as pd
import os


def get_from_setup():
    setup_file = "setup.txt"
    if os.path.exists(setup_file):
        with open(setup_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("TDX_PATH"):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    return None


TDX_PATH = get_from_setup()

def get_from_setup():
    setup_file = "setup.txt"
    if os.path.exists(setup_file):
        with open(setup_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATA_gn"):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    return None
DATA_gn = get_from_setup()
def extract_gn_segments(content: str) -> list:
    """提取概念板块段落"""
    pattern = r'#GN_(.+?)\r\n'
    segments = re.findall(pattern, content, re.DOTALL)
    return [f"#GN_{seg}" for seg in segments]


def process_stock_concepts(file_path):
    """处理通达信概念板块文件并保存为Excel"""
    try:
        with open(file_path, "rb") as f:
            content = f.read().decode("gbk", errors="ignore")
    except FileNotFoundError:
        print(f"文件未找到：{file_path}")
        return None
    except Exception as e:
        print(f"读取文件时发生错误: {str(e)}")
        return None

    gn_segments = extract_gn_segments(content)
    pattern2 = r'#GN_(.+?),'  # 提取所属概念
    pattern3 = r'\d+#\d{6}'   # 提取股票代码格式

    stock_gn_pairs = []
    for seg in gn_segments:
        match_gn = re.findall(pattern2, seg, re.DOTALL)
        if not match_gn:
            continue
        block_gn = match_gn[0]
        blocks_codes = re.findall(pattern3, seg, re.DOTALL)
        for code in blocks_codes:
            stock_code = code[2:8]  # 如 '000576'
            stock_gn_pairs.append((stock_code, block_gn))

    df = pd.DataFrame(stock_gn_pairs, columns=['股票代码', '概念'])
    return df


def merge_stock_data(df):
    """合并股票概念数据"""
    grouped = df.groupby('股票代码')['概念'].apply(list).reset_index()
    print(f"所有股票数量： {len(grouped)}")

    max_sectors = grouped['概念'].apply(len).max()
    print(f"单个股票最多所属板块数量: {max_sectors}")

    result_data = {'股票代码': grouped['股票代码']}
    for i in range(max_sectors):
        result_data[f'概念{i + 1}'] = grouped['概念'].apply(lambda x: x[i] if i < len(x) else '')

    result_df = pd.DataFrame(result_data)
    return result_df


def insert_stock_name(df, name_df):
    """插入股票简称，并确保股票代码可正确匹配"""
    df = df.copy()
    name_df = name_df.copy()

    # 统一转换为6位字符串用于匹配
    df['股票代码'] = df['股票代码'].astype(str).str.zfill(6)
    name_df['股票代码'] = name_df['股票代码'].astype(str).str.zfill(6)

    # 去重防止一对多
    name_df = name_df.drop_duplicates(subset=['股票代码'], keep='first')

    # 合并简称
    merged_df = df.merge(name_df[['股票代码', '股票简称']], on='股票代码', how='left')

    # 排列列顺序
    cols = ['股票代码', '股票简称'] + [col for col in merged_df.columns if col.startswith('概念')]
    merged_df = merged_df[cols]

    return merged_df


def main():
    if TDX_PATH is None:
        print("错误：未找到TDX_PATH配置，请检查setup.txt文件")
        return
    
    file_path = rf'{TDX_PATH}\T0002\hq_cache\infoharbor_block.dat'
    df = process_stock_concepts(file_path)
    if df is not None:
        try:
            processed_df = merge_stock_data(df)

            name_file = rf'{DATA_gn}\所属概念1.xlsx'
            name_df = pd.read_excel(name_file, dtype={'股票代码': str})

            final_df = insert_stock_name(processed_df, name_df)

            # 将股票代码从字符串转为整型（去除前导零，如 '000576' → 576）
            final_df['股票代码'] = pd.to_numeric(final_df['股票代码'], errors='coerce').astype('Int64')  # 使用 nullable int

            # 重命名列并保存到 Excel
            final_df = final_df.rename(columns={'股票代码': '代码', '股票简称': '简称'})
            final_df.to_excel(rf'{DATA_gn}\所属概念.xlsx', index=False, engine='openpyxl')
            print(f"文件已成功保存")
        except FileNotFoundError:
            print(f"股票名称文件未找到：{name_file}")
        except Exception as e:
            print(f"处理过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()


