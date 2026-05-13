import re
import pandas as pd
import numpy as np
from datetime import datetime
import os


def extract_gn_segments(content: str) -> list:
    """
    提取所有从#GN_开始到下一个#GN_之前的内容（最后一段到文本末尾）
    :param content: 待解析的文本/二进制转字符串内容
    :return: 分段结果列表，每个元素是一段#GN_开头的内容
    """
    # 正则匹配：#GN_开头，非贪婪匹配到下一个#GN_或文本结束
    pattern = r'#GN_(.+?)\r\n'
    # 匹配所有结果，re.DOTALL让.匹配换行符
    segments = re.findall(pattern, content, re.DOTALL)
    # 补回#GN_前缀（因为正则里分组去掉了）
    result = [f"#GN_{seg}" for seg in segments]
    return result


# ------------------- 示例用法 -------------------
if __name__ == "__main__":
    # 1. 读取通达信板块文件（二进制转字符串，编码用gbk/gb2312适配中文）
    file_path = r'D:\zd_zyb\T0002\hq_cache\infoharbor_block.dat'  # 替换为你的实际路径
    try:
        with open(file_path, "rb") as f:
            # 二进制文件转字符串（通达信板块文件多为gbk编码）
            content = f.read().decode("gbk", errors="ignore")  # ignore忽略无法解码的字符
    except FileNotFoundError:
        print(f"文件未找到：{file_path}")
        content = ""



    # 3. 提取分段结果
    gn_segments = extract_gn_segments(content)

    # 4. 正则模式定义
    pattern2 = r'#GN_(.+?),'  # 提取所属概念
    pattern3 = r'\d+#\d{6}'  # 提取代码格式

    # 5. 存储所有代码与所属概念的映射关系
    stock_gn_pairs = []  # 存储 (stock_code, block_gn) 对

    for seg in gn_segments:
        # 提取所属概念
        match_gn = re.findall(pattern2, seg, re.DOTALL)
        if not match_gn:
            continue
        block_gn = match_gn[0]

        # 提取代码
        blocks_codes = re.findall(pattern3, seg, re.DOTALL)
        for code in blocks_codes:
            stock_code = code[-6:]  # 提取后6位作为代码并转换为字符串类型
            stock_gn_pairs.append((stock_code, block_gn))

    # 6. 转换为DataFrame
    df = pd.DataFrame(stock_gn_pairs, columns=['代码', '概念'])

    # 7. 输出表格（控制台预览）
    # print("提取的代码与所属概念对应表：")
    # print(df)
    # print(f"\n共提取到 {len(df)} 条记录")



    try:
        df.to_excel( r'D:\数据分析\所属概念.xlsx', index=False, engine='openpyxl')

    except Exception as e:
        print(f"保存文件时出错: {e}")
    else:
        print(f"\n数据已保存为Excel文件")





def merge_stock_data(input_file_path, output_file_path=None):

    # 1. 读取Excel文件
    # print(f"正在读取文件: {input_file_path}")
    try:
        df = pd.read_excel(input_file_path)
        # print(f"成功读取数据，原始数据形状: {df.shape}")
        # print(f"数据列名: {df.columns.tolist()}")
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        raise

    # 检查必要的列是否存在
    required_columns = ['代码', '概念']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"文件中缺少必要的列: {col}，请检查文件格式")

    # 2. 按代码分组，收集每个股票的所有概念
    # print("正在按代码分组并合并概念...")
    # 按代码分组，将概念收集成列表
    grouped = df.groupby('代码')['概念'].apply(list).reset_index()

    print(f"所有股票数量： {len(grouped)}")

    # 3. 确定需要的最大列数（最大板块数量）
    max_sectors = grouped['概念'].apply(len).max()
    print(f"单个股票最多所属板块数量: {max_sectors}")

    # 4. 将概念列表展开为多列
    # print("正在展开概念为多列...")
    # 创建新的DataFrame，包含代码和多个板块列
    result_data = {'代码': grouped['代码']}

    # 为每个板块位置创建一列
    for i in range(max_sectors):
        # 对于每个股票，获取第i个概念，如果不存在则为空字符串
        result_data[f'概念_{i + 1}'] = grouped['概念'].apply(lambda x: x[i] if i < len(x) else '')

    # 创建结果DataFrame
    result_df = pd.DataFrame(result_data)

    # 5. 调整列名，第一列是代码，第二列开始是概念
    # 重命名列，使第二列开始为"概念"、"概念_2"、"概念_3"...
    new_columns = ['代码', '概念']
    if max_sectors > 1:
        new_columns.extend([f'概念_{i}' for i in range(2, max_sectors + 1)])

    result_df.columns = new_columns

    # print(f"数据处理完成，处理后数据形状: {result_df.shape}")

    # 6. 保存文件
    if output_file_path is None:
        # 自动生成输出文件名，包含当前时间戳
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_dir = os.path.dirname(input_file_path)
        input_filename = os.path.basename(input_file_path).split('.')[0]
        output_file_path = os.path.join(input_dir, f"{input_filename}_合并后_{current_time}.xlsx")

    try:
        result_df.to_excel(output_file_path, index=False, engine='openpyxl')
        print(f"文件已成功保存到: {output_file_path}")
    except Exception as e:
        print(f"保存文件失败: {str(e)}")
        raise

    return result_df


def main():
    """
    主函数，演示如何使用
    """
    # 示例用法
    # 请根据实际情况修改输入文件路径
    input_file = r'D:\数据分析\概念2.xlsx'  # 输入Excel文件路径
    output_file = r'D:\数据分析\概念3.xlsx'  # 输出Excel文件路径

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"输入文件不存在: {input_file}")
        return

    # 执行数据合并
    try:
        processed_df = merge_stock_data(input_file, output_file)

        # 显示处理结果的前几行
        # print("\n处理结果预览（前10行）:")
        # print(processed_df.head(10))

        # 显示统计信息
        # print(f"\n数据统计:")
        # print(f"- 原始数据行数: {pd.read_excel(input_file).shape[0]}")
        # print(f"- 处理后数据行数: {processed_df.shape[0]}")
        # print(f"- 总列数: {processed_df.shape[1]}")
        # print(f"- 最多板块数量: {processed_df.shape[1] - 1}")

    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()