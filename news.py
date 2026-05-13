import requests
import os
import json
import re
import csv
import time
from datetime import datetime, timedelta
import pandas as pd
from openai import OpenAI  # 替换原 dashscope 导入
from send_wechat import send_wechat
from send_wechat import send_dingtalk


def config():
    try:
        with open('setup.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

# ==============================
def clean_old_files():
    """清理旧数据文件"""
    files_to_delete = [
        'data/news_stat.csv',
        'data/news_top_boards.csv',
        'data/news_top_boards_summary.csv',
        'data/news_total_dedup.csv',
    ]
    print("=" * 50)
    print("【清理旧数据文件】")
    print("=" * 50)
    deleted_count = 0
    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f" ✓ 已删除: {file_path}")
                deleted_count += 1
            else:
                print(f" - 不存在: {file_path}")
        except Exception as e:
            print(f" ✗ 删除失败 {file_path}: {e}")
    print(f"\n共删除 {deleted_count} 个旧文件")
    print("=" * 50 + "\n")


class BlkIndex:
    """板块指数处理类"""

    def process_financial_data(self):
        csv_file = 'data/news_stat.csv'
        txt_file = 'data/板块指数.txt'
        columns = ['代码', '名称', '概念重复次数', '新闻列表', '重磅程度', '板块热度', '昨涨幅', '昨板比率', '连涨天']
        df_result = pd.DataFrame(columns=columns)

        print(f"\n[1] 读取 {txt_file}...")
        if not os.path.exists(txt_file):
            print(f" ⚠️ 文件 {txt_file} 不存在！")
        else:
            try:
                df_sector = pd.read_csv(txt_file, sep='\t', encoding='gbk', dtype={'代码': str})
                print(f" ✓ 成功！读取到 {len(df_sector)} 行数据")
                required_cols = ['涨跌数', '涨停数', '名称', '代码', '涨幅%', '连涨天']
                if all(col in df_sector.columns for col in required_cols):
                    print(f"\n[2] 计算昨板比率...")
                    split_counts = df_sector['涨跌数'].str.split('|', expand=True)
                    df_sector['涨数'] = pd.to_numeric(split_counts[0])
                    df_sector['跌数'] = pd.to_numeric(split_counts[1])
                    denominator = df_sector['涨数'] + df_sector['跌数']
                    df_sector['昨板比率'] = (100 * df_sector['涨停数'] / denominator.replace(0, 1)).round(2)
                    print(f" ✓ 计算完成")

                    df_result['代码'] = df_sector['代码']
                    df_result['名称'] = df_sector['名称']
                    df_result['昨涨幅'] = df_sector['涨幅%']
                    df_result['昨板比率'] = df_sector['昨板比率']
                    df_result['连涨天'] = df_sector['连涨天']
                    df_result['概念重复次数'] = 0
                    df_result['新闻列表'] = ''
                    df_result['重磅程度'] = ''
                    df_result['板块热度'] = 0
                    print(f" ✓ 构建完成，共 {len(df_result)} 行")
            except Exception as e:
                print(f" ✗ 读取失败: {e}")

        # 检查现有 CSV 数据
        if os.path.exists(csv_file):
            try:
                existing_df = pd.read_csv(csv_file, encoding='utf-8-sig')
                if len(existing_df) > 0:
                    print(f" ✓ 发现现有数据 {len(existing_df)} 行")
                    if len(df_result) == 0:
                        df_result = existing_df[columns].copy()
                    else:
                        for col in ['概念重复次数', '新闻列表', '重磅程度', '板块热度']:
                            if col in existing_df.columns:
                                value_map = existing_df.dropna(subset=[col]).set_index('代码')[col].to_dict()
                                df_result[col] = df_result['代码'].map(value_map).fillna(df_result[col])
            except Exception as e:
                print(f" ⚠️ 读取现有数据失败: {e}")

        df_result.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f" ✓ 已保存到: {csv_file}")
        return df_result


class NewsProcessor:
    """新闻处理类"""

    def update_board_heat(self, news_file):
        """更新板块热度"""
        try:
            df_stat = pd.read_csv('data/news_stat.csv', encoding='utf-8-sig')
        except Exception as e:
            print(f"读取 news_stat.csv 失败: {e}")
            return

        try:
            df_news = pd.read_csv(news_file)
            df_news['contents'] = df_news['contents'].astype(str)
        except FileNotFoundError:
            print(f"未找到 {news_file}")
            return

        board_names = df_stat['名称'].dropna().astype(str).tolist()
        df_stat['板块热度'] = 0
        total_trigger_count = 0

        print(f"正在匹配 {len(df_news)} 条新闻...")
        for content in df_news['contents']:
            for name in board_names:
                if name in content:
                    df_stat.loc[df_stat['名称'] == name, '板块热度'] += 1
                    total_trigger_count += 1

        df_stat['板块热度'] = df_stat['板块热度'].apply(lambda x: f"{int(x)}/{total_trigger_count}")
        df_stat.to_csv('data/news_stat.csv', index=False, encoding='utf-8-sig')
        print(f" ✓ 板块热度更新完成，总触发 {total_trigger_count} 次")

    def generate_top_board_news_report(self):
        """生成Top10板块新闻明细"""
        print("\n" + "=" * 50)
        print("【生成板块热度Top10新闻明细】")
        print("=" * 50)
        try:
            df_stat = pd.read_csv('data/news_stat.csv', encoding='utf-8-sig')
            df_news = pd.read_csv('data/tdx_news.csv')
            df_news['contents'] = df_news['contents'].astype(str)
        except Exception as e:
            print(f"读取文件失败: {e}")
            return

        def get_heat_value(x):
            try:
                return int(str(x).split('/')[0])
            except:
                return 0

        df_stat['temp_heat'] = df_stat['板块热度'].apply(get_heat_value)
        top_boards = df_stat.sort_values(by='temp_heat', ascending=False).head(10)
        top_board_names = top_boards['名称'].dropna().tolist()

        board_news_map = {name: [] for name in top_board_names}
        for _, row in df_news.iterrows():
            content = row['contents']
            for name in top_board_names:
                if name in content:
                    board_news_map[name].append(content)

        result_rows = []
        for name in top_board_names:
            merged = " ".join(board_news_map[name])
            result_rows.append({"板块名称": name, "合并后的内容": merged})

        df_result = pd.DataFrame(result_rows)
        df_result.to_csv('data/news_top_boards.csv', index=False, encoding='utf-8-sig')
        print(f" ✓ 已保存到 data/news_top_boards.csv")
        return df_result

    def summarize_board_content(self, board_name, news_text):
        config_data = config()  # ✓ 先调用函数获取字典
        if not config_data:
            return "Error: 配置文件读取失败"

        api_key = config_data.get('OPENAI_API_KEY')
        model_name = config_data.get('OPENAI_MODEL')
        base_url = config_data.get('OPENAI_BASE_URL')

        prompt = f"""请分析昨日16:00至今日9:00的财经新闻，针对"{board_name}"板块，筛选出**最具潜在Alpha收益的5条核心驱动事件**。 **筛选标准**： 1. **驱动性**：优先选择政策突变、行业重大利好/利空、头部公司重大动作，忽略一般性日常报道。 2. **独立性**：每条必须是独立的主题，避免同一事件的重复报道。 3. **精炼度**：每条信息必须高密度概括核心事实。 **输出规范** - **格式**：输出为纯文本，共5行。每行对应一条事件，无序号、无项目符号、无任何标题或Markdown格式。 - **内容**：每行严格控制在40个汉字以内，直接陈述核心事实。 - **风格**：使用客观、冷静的交易员语言，无需任何分析或评论语句（如"这意味着"、"预计将"）。 **新闻内容**： {news_text} """

        if not api_key:
                return

        try:
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {'role': 'system', 'content': '你是一名A股市场的资深交易员，擅长从海量信息中捕捉影响股价走势的核心变量。'},
                    {'role': 'user', 'content': f'{prompt}'}
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"错误信息：{e}")

    def generate_board_summary_report(self):
        """生成AI总结报告"""
        print("\n" + "=" * 50)
        print("【大模型提炼板块重点】")
        print("=" * 50)
        try:
            df = pd.read_csv('data/news_top_boards.csv', encoding='utf-8-sig')
        except Exception as e:
            print(f"读取失败: {e}")
            return

        results = []
        for index, row in df.iterrows():
            board_name = row['板块名称']
            content = row['合并后的内容']
            print(f" 正在处理: {board_name}...", end=" ")
            summary = self.summarize_board_content(board_name, content)
            print("完成")
            results.append({"板块名称": board_name, "AI总结": summary})
            import time
            time.sleep(0.5)

        df_summary = pd.DataFrame(results)
        df_summary.to_csv('data/news_top_boards_summary.csv', index=False, encoding='utf-8-sig')
        print(f" ✓ 总结已保存")
        return df_summary

    def update_news_list_with_summary(self):
        """将AI总结更新到新闻列表"""
        try:
            df_summary = pd.read_csv('data/news_top_boards_summary.csv', encoding='utf-8-sig')
            df_stat = pd.read_csv('data/news_stat.csv', encoding='utf-8-sig')
        except Exception as e:
            print(f"读取失败: {e}")
            return

        df_stat['新闻列表'] = df_stat['新闻列表'].fillna('').astype(str)
        summary_map = dict(zip(df_summary['板块名称'], df_summary['AI总结']))

        for index, row in df_stat.iterrows():
            board_name = row['名称']
            if board_name in summary_map:
                df_stat.at[index, '新闻列表'] = summary_map[board_name]

        df_stat.to_csv('data/news_stat.csv', index=False, encoding='utf-8-sig')
        print(f" ✓ AI总结已更新到板块数据")


def send_reports_to_wechat():
    """将 news_top_boards_summary.csv 发送到企业微信和钉钉"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    try:
        df_summary = pd.read_csv('data/news_top_boards_summary.csv', encoding='utf-8-sig')
        message_parts = []
        message_parts.append(f"【{today_str}】10大热门概念及新闻(昨16-今9之间)")
        message_parts.append("=" * 40)

        for i, (_, row) in enumerate(df_summary.iterrows(), 1):
            board_name = row.get('板块名称', 'N/A')
            summary = str(row.get('AI总结', ''))
            message_parts.append(f"\n{i}. 【{board_name}】")
            message_parts.append(f" {summary}")

        full_message = "\n".join(message_parts)

        # 如果消息太长，分段发送
        max_length = 4096
        if len(full_message) <= max_length:
            send_wechat(full_message)
            send_dingtalk(full_message)
            print("✓ 报告已发送到企业微信和钉钉")
        else:
            parts = []
            current_part = ""
            for line in message_parts:
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = line
                else:
                    current_part += "\n" + line if current_part else line
            if current_part:
                parts.append(current_part)

            for i, part in enumerate(parts, 1):
                send_wechat(f"[第{i}部分]\n{part}")
                send_dingtalk(f"[第{i}部分]\n{part}")
            print(f"✓ 报告已分{len(parts)}段发送到企业微信和钉钉")
    except Exception as e:
        send_wechat(f"发送失败: {e}")
        send_dingtalk(f"发送失败: {e}")
        print(f"✗ 发送失败: {e}")


def stock_down():
    """获取新闻数据"""
    url = 'https://fk.tdx.com.cn/TQLEX'
    params = {"Entry": "CWServ.tdxi_zxxwsy"}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/json'
    }
    os.makedirs("data", exist_ok=True)

    now = datetime.now()
    target_end = now.replace(hour=9, minute=0, second=0, microsecond=0)
    yesterday_16 = (now - timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0)
    print(f"📅 有效时间范围: {yesterday_16} ~ {target_end}")

    all_news = []
    all_news_raw = []  # 新增：用于保存未过滤的原始新闻

    should_stop = False
    for i in range(1, 500):
        if should_stop:
            break
        # 新增：显示正在获取第几页
        print(f"\n[第{i}页] 正在请求API...", end=" ")
        data = {"Params": ["1", i, "20"]}
        try:
            response = requests.post(url, params=params, json=data, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            result_dict = json.loads(response.text)
            content_list = result_dict['ResultSets'][1]['Content']

            # 新增：显示本页新闻数量
            print(f"获取到 {len(content_list)} 条新闻")

            # 新增：统计本页过滤情况
            page_stats = {
                '保留': 0,
                '跳过_晚于结束': 0,
                '过滤_PDF': 0,
                '过滤_来源': 0,
                '过滤_关键词': 0,
                '过滤_长度': 0
            }

            for content in content_list:
                news_time_str = content[1]
                news_time = datetime.strptime(news_time_str, "%Y-%m-%d %H:%M:%S")

                if news_time < yesterday_16:
                    print(f" ⏹️ 时间早于范围: {news_time_str}，结束获取")
                    should_stop = True
                    break
                elif news_time > target_end:
                    page_stats['跳过_晚于结束'] += 1
                    continue

                # 新增：收集未过滤的原始新闻（仅过滤了时间范围）
                all_news_raw.append({

                    "datetime": content[1],
                    "title": content[0],
                    "writer": content[3],
                    "contents": content[6]
                })

                # 新增：详细过滤日志
                if str(content[4]).lower().endswith('.pdf'):
                    page_stats['过滤_PDF'] += 1
                    continue
                if str(content[3]) in ['证券之星', '智通财经', '同壁财经']:
                    page_stats['过滤_来源'] += 1
                    continue
                news_contents = content[6]
                skip_words = ['.HK', '公告', '营收', '公布', '挂牌', '收盘', '美股', '欧股', '国债']
                if any(word in news_contents for word in skip_words):
                    page_stats['过滤_关键词'] += 1
                    continue
                if len(news_contents) < 80:
                    page_stats['过滤_长度'] += 1
                    continue

                # 清洗内容前缀
                patterns = [
                    r'^格隆汇\d+月\d+日[｜|丨]',
                    r'^财联社\d+月\d+日电，',
                    r'^金吾财讯\s*[｜|丨]\s*',
                    r'^\d+月\d+日，',
                ]
                for pattern in patterns:
                    news_contents = re.sub(pattern, '', news_contents)

                all_news.append({
                    "datetime": content[1],
                    "contents": news_contents
                })
                page_stats['保留'] += 1
                print(f" ✅ {content[1]} - {content[0][:30]}...")

            # 新增：显示本页统计
            print(f" 📊 本页统计: 保留{page_stats['保留']}条", end="")
            filtered = sum([v for k, v in page_stats.items() if k.startswith('过滤')])
            if filtered > 0 or page_stats['跳过_晚于结束'] > 0:
                print(f" | 过滤{filtered}条", end="")
            if page_stats['跳过_晚于结束'] > 0:
                print(f" | 跳过{page_stats['跳过_晚于结束']}条", end="")
            print()

        except requests.exceptions.Timeout:
            print(f"❌ API超时（30秒），跳过本页")
            continue
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            continue

    # 保存未过滤的原始新闻
    raw_csv_file = "data/tdx_news_all.csv"
    with open(raw_csv_file, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [ "datetime", "title","writer", "contents"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_news_raw)

    # 保存过滤后的新闻
    csv_file = "data/tdx_news.csv"
    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["datetime", "contents"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_news)

    print(f"\n{'=' * 70}")
    print(f"🎉 共保存 {len(all_news_raw)} 条原始新闻到 {raw_csv_file}")
    print(f"🎉 共保存 {len(all_news)} 条过滤后新闻到 {csv_file}")
    print(f"{'=' * 70}")

    return csv_file


def new_distill():
    """
    从 data/tdx_news_all.csv 的 title 列中提取代码和重大新闻，保存到 data/news_distill.csv。
    流程顺序：
    第一步：过滤噪音关键词（直接在原标题上判断）
    第二步：处理6位代码、括号及冒号（得到清洗后的文本）
    第三步：匹配分类关键词并打上标签（利好/利空/波动/中性）
    附加：剔除中标金额小于1000万元的行
    """
    # 读取源数据
    df = pd.read_csv('data/tdx_news_all.csv')

    # 正则：以 00/30/60/68 开头的6位数字
    pattern_code = r'(?<!\d)(00\d{4}|30\d{4}|60\d{4}|68\d{4})(?!\d)'

    # ===== 第一步：需要过滤掉的噪音关键词 =====
    exclude_keywords = ['ST','章程', '草案', '制度', '董事', '员工', '限制',
                        '关于', '发行', '募集', '审计', '年度报告','债券',
                        '细则', '规范', '临时', '资料', '规则','异常波动','商业化','意见书','异议',
                        '报告', '摘要', '内容', '闲置', '理财', '往来']

    # ===== 第三步：分类关键词映射表 =====
    keyword_map = {
        '警惕': [ '同比双双增长，应收账款上升', '同比双双增长，公司应收账款体量较大','三费占比上升明显','公司应收账款体量较大','短期债务压力上升'],
        '中性': ['暂未涉及', '不存在任何股权关系', '暂无直接相关的业务应用',
                 '不是公司客户', '目前没有', '不涉及', '没有合作',
                 '目前主要专注'],
        '利好': ['扭亏为盈', '预增', '盈利能力上升', '增长', '亏损收窄', '中标',
                 '量产', '供货', '回购', '增持',
                 '签订', '获得药品注册证书'],
        '利空': ['逾期', '冻结', '处罚', '补缴', '净亏损', '下降','增收不增利',
                 '增收不增利', '预减', '下滑', '减持', '质押',
                 '终止上市', '退市风险警示', '可能被终止上市', '停牌',
                 '监管工作函', '问询函', '终止收购', '终止转让', '终止',
                 '风险提示','公司应收账款体量较大'],
        '波动': ['重大资产重组', '重大资产购买', '发行股份购买资产',
                 '资产置换', '定增'],

    }

    # 正则：提取金额（用于附加过滤）
    pattern_amount = r'金额为([\d\.]+)\s*(万元|亿元)'

    results = []
    for title in df['title'].dropna():
        title_str = str(title)

        # ==========================================
        # 第一步：过滤噪音关键词（在原始标题上直接匹配）
        # ==========================================
        if any(kw in title_str for kw in exclude_keywords):
            continue

        # ==========================================
        # 第二步：处理代码、括号及冒号
        # ==========================================
        # 提取代码
        codes = re.findall(pattern_code, title_str)
        if not codes:
            continue

        # 去除代码
        news = re.sub(pattern_code, '', title_str)
        # 删除第一个 ) 或 ） 及其之前的所有内容
        news = re.sub(r'.*?[)）]', '', news, count=1)
        # 删除中文冒号"："
        news = news.replace('：', '')
        # 清理多余空格及首尾标点
        news = re.sub(r'\s+', ' ', news).strip(' ,，、：:；; \t\n')

        if not news:
            continue

        # ==========================================
        # 第三步：分类关键词匹配与标注
        # ==========================================
        matched_type = None
        for category, keywords in keyword_map.items():
            if any(kw in news for kw in keywords):
                matched_type = category
                break

        if matched_type:
            # ===== 附加过滤：剔除中标金额小于1000万元的行 =====
            amount_match = re.search(pattern_amount, news)
            if amount_match:
                num = float(amount_match.group(1))
                unit = amount_match.group(2)
                # 统一换算为万元进行比较
                actual_amount = num * 10000 if unit == '亿元' else num
                if actual_amount < 1000:
                    continue

            labeled_news = f'【{matched_type}】{news}'
            for code in codes:
                results.append({'代码': code, '相关新闻': labeled_news})

    result_df = pd.DataFrame(results)
    # 最终去重：代码与重大新闻完全一致则视为重复，只保留第一条
    # ==========================================
    result_df.drop_duplicates(subset=['代码', '相关新闻'], keep='first', inplace=True)
    # 去重后重置索引（避免索引断层）
    result_df.reset_index(drop=True, inplace=True)

    # 确保输出目录存在
    os.makedirs('data', exist_ok=True)

    # 带重试的保存
    output_path = 'data/news_distill.csv'
    for attempt in range(5):
        try:
            result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f'提取完成，共 {len(result_df)} 条记录，已保存到 {output_path}')
            return result_df
        except PermissionError:
            print(f'文件被占用，第{attempt + 1}次尝试失败，等待2秒后重试...')
            time.sleep(2)

    print('错误：文件持续被占用，请关闭 Excel 后重新运行！')
    return result_df
if __name__ == '__main__':
    # 1. 清理旧文件
    clean_old_files()
    # 2. 获取新闻
    news_file = stock_down()
    # 3. 处理板块指数
    index_processor = BlkIndex()
    index_processor.process_financial_data()
    # 4. 更新板块热度
    news_processor = NewsProcessor()
    news_processor.update_board_heat(news_file)
    # 5. 生成Top10板块新闻
    news_processor.generate_top_board_news_report()
    # 6. AI总结
    news_processor.generate_board_summary_report()
    # 7. 更新新闻列表
    news_processor.update_news_list_with_summary()
    # 8. 发送报告到微信
    send_reports_to_wechat()
    # 9. 精简个股相关的利好利空新闻
    new_distill()
    print("\n" + "=" * 50)
    print("【全部完成】")
    print("=" * 50)
