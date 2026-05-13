# -*- coding: utf-8 -*-
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import (QHeaderView, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTableWidget,
                             QTableWidgetItem, QGroupBox, QComboBox, QDateEdit,
                             QGridLayout, QLabel, QButtonGroup, QAbstractItemView,
                             QMessageBox)
from link_tdx import link_tdx




def yyb_stat(filters=None):
    """
    统计营业部龙虎榜数据，保存到 data/yyb_stat.csv
    新增: 支持按日期和股票范围筛选统计
    """
    input_path = 'data/lhb_detail_b.csv'
    output_path = 'data/yyb_stat.csv'

    if not os.path.exists(input_path):
        print(f"❌ 错误: 未找到文件 {input_path}")
        return

    try:
        print("🔄 正在读取数据...")

        # ===== 修改：添加调试信息 =====
        # 先读取一行查看文件的实际结构
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline().strip()
            print(f"📄 CSV文件第一行: {first_line}")
        # ============================

        detail_columns = [
            '上榜日', '代码', 'flag', '序号', '交易营业部名称',
            '买入金额(亿)', '买入占比', '卖出金额(亿)', '卖出占比', '净额(亿)', '类型'
        ]

        # ===== 修复1：改为 header=0，正确读取表头 =====
        df = pd.read_csv(input_path, encoding='utf-8-sig', header=0)
        # =================================================

        # ===== 新增：打印调试信息 =====
        print(f"📊 读取后的数据形状: {df.shape}")
        print(f"📊 列名: {df.columns.tolist()}")
        print(f"📊 '上榜日'列的数据类型: {df['上榜日'].dtype}")
        print(f"📊 '上榜日'列的前5个值: {df['上榜日'].head()}")
        # ===========================

        # 数据清洗
        df['代码'] = df['代码'].astype(str)
        df['交易营业部名称'] = df['交易营业部名称'].astype(str)
        df['买入金额(亿)'] = pd.to_numeric(df['买入金额(亿)'], errors='coerce').fillna(0)
        df['卖出金额(亿)'] = pd.to_numeric(df['卖出金额(亿)'], errors='coerce').fillna(0)
        df['flag'] = df['flag'].astype(str)

        # 【关键修改1】日期预处理：转换为datetime以便筛选
        # ===== 修复2：去掉严格 format，支持不同日期格式 =====
        df['上榜日'] = pd.to_datetime(df['上榜日'], errors='coerce')
        # =======================================================

        # 打印调试信息
        print(f"📊 日期转换后，NaT 数量: {df['上榜日'].isna().sum()}")
        if df['上榜日'].isna().sum() > 0:
            print(f"⚠️ 以下行的日期转换失败 (前5行):")
            print(df[df['上榜日'].isna()][['代码', '交易营业部名称', '上榜日']].head())

        # 过滤掉无效代码和营业部名称
        df = df[df['交易营业部名称'] != 'nan']
        valid_code_mask = (
                df['代码'].notna() &
                (df['代码'] != 'nan') & (df['代码'] != 'NaN') &
                (df['代码'] != '') & (df['代码'] != '代码')
        )
        df = df[valid_code_mask]

        # ================= 新增：筛选逻辑 =================
        if filters:
            # --- 1. 日期筛选 ---
            date_mode = filters.get('date_mode')

            # ===== 新增：打印调试信息，确认 date_mode 的值 =====
            print(f"🔍 yyb_stat 收到的 date_mode: '{date_mode}'")
            # ============================================

            if date_mode:
                if date_mode in ["当天", "近3日", "近5日", "近10日", "近30日"]:
                    unique_dates = sorted(df['上榜日'].unique(), reverse=True)
                    # 过滤掉 NaT，防止选中无效日期
                    unique_dates = [d for d in unique_dates if pd.notna(d)]

                    target_dates = []
                    if date_mode == "当天":
                        target_dates = [unique_dates[0]] if len(unique_dates) > 0 else []
                    elif date_mode == "近3日":
                        target_dates = unique_dates[:3]
                    elif date_mode == "近5日":
                        target_dates = unique_dates[:5]
                    elif date_mode == "近10日":
                        target_dates = unique_dates[:10]
                    elif date_mode == "近30日":
                        target_dates = unique_dates[:30]

                    if target_dates:
                        df = df[df['上榜日'].isin(target_dates)]

                elif date_mode == "自定义":
                    start_date = pd.to_datetime(filters.get('start_date'))
                    end_date = pd.to_datetime(filters.get('end_date'))
                    df = df[(df['上榜日'] >= start_date) & (df['上榜日'] <= end_date)]

                else:
                    print(f"⚠️ 未知的 date_mode: '{date_mode}'，默认按当天处理")
                    unique_dates = sorted(df['上榜日'].unique(), reverse=True)
                    unique_dates = [d for d in unique_dates if pd.notna(d)]
                    if len(unique_dates) > 0:
                        df = df[df['上榜日'] == unique_dates[0]]
            else:
                print("⚠️ filters 中缺少 date_mode，默认按当天处理")
                unique_dates = sorted(df['上榜日'].unique(), reverse=True)
                unique_dates = [d for d in unique_dates if pd.notna(d)]
                if len(unique_dates) > 0:
                    df = df[df['上榜日'] == unique_dates[0]]
        else:
            print("⚠️ filters 为 None，默认按当天处理")
            unique_dates = sorted(df['上榜日'].unique(), reverse=True)
            unique_dates = [d for d in unique_dates if pd.notna(d)]
            if len(unique_dates) > 0:
                df = df[df['上榜日'] == unique_dates[0]]
        # ================================================

        # ===== 新增：打印过滤后的调试信息 =====
        print(f"📊 过滤无效数据后的数据形状: {df.shape}")
        # ==================================


        def aggregate_stats(group):
            yyb_name = group.name
            latest_date = group['上榜日'].max()
            list_count = group['代码'].nunique()

            # ===== 修改：处理 group 为空或日期全为 NaT 的情况 =====
            if pd.isna(latest_date):
                print(f"⚠️ 营业部 '{yyb_name}' 的所有日期都无效")
                latest_date = pd.NaT
            # ==================================================

            buy_mask = group['flag'] == '买入'
            buy_stock_count = group[buy_mask]['代码'].nunique()
            buy_total_amount = group[buy_mask]['买入金额(亿)'].sum()

            sell_mask = group['flag'] == '卖出'
            sell_stock_count = group[sell_mask]['代码'].nunique()
            sell_total_amount = group[sell_mask]['卖出金额(亿)'].sum()

            stock_list_str = []
            for code in group['代码']:
                stock_list_str.append(code)

            return pd.Series({
                '上榜日': latest_date,
                '交易营业部名称': yyb_name,
                '大类': '',
                '别名': '',
                '上榜次数': list_count,
                '买入个股数': buy_stock_count,
                '卖出个股数': sell_stock_count,
                '买入总金额': round(buy_total_amount, 2),
                '卖出总金额': round(sell_total_amount, 2),
                '个股列表': stock_list_str
            })

        # ================= 新增：营业部范围筛选 =================
        if filters:
            yyb_category = filters.get('yyb_category', '全部')
            yyb_name = filters.get('yyb_name', '').strip()
            yyb_alias = filters.get('yyb_alias', '').strip()  # 获取别名参数

            print(f"🔍 yyb_stat 营业部筛选 - 大类: '{yyb_category}', 名称: '{yyb_name}', 别名: '{yyb_alias}'")

            # 优先级：名称 > 大类 > 别名
            if yyb_name:
                # 如果输入了营业部名称，按名称模糊匹配
                df = df[df['交易营业部名称'].str.contains(yyb_name, na=False)]
                print(f"✅ 按名称筛选: 包含 '{yyb_name}' 的记录，剩余 {len(df)} 条")
            elif yyb_category != "全部":
                # 如果选择了特定大类，需要从 yyb.csv 中映射
                try:
                    path = 'data/yyb.csv'
                    category_map = {}
                    if os.path.exists(path):
                        df_map = pd.read_csv(path, encoding='utf-8-sig')
                        if '交易营业部名称' in df_map.columns and '大类' in df_map.columns:
                            df_map['大类'] = df_map['大类'].fillna('')
                            category_map = dict(zip(df_map['交易营业部名称'], df_map['大类']))

                        target_names = []
                        for name, category in category_map.items():
                            if category == yyb_category:
                                target_names.append(name)

                        if target_names:
                            df = df[df['交易营业部名称'].isin(target_names)]
                            print(
                                f"✅ 按大类 '{yyb_category}' 筛选，包含 {len(target_names)} 个营业部，剩余 {len(df)} 条记录")
                        else:
                            print(f"⚠️ 大类 '{yyb_category}' 下没有对应的营业部")
                            df = df.iloc[0:0]  # 返回空DataFrame
                except Exception as e:
                    print(f"❌ 按大类筛选出错: {e}")


            elif yyb_alias:

                try:

                    path = 'data/yyb.csv'

                    alias_map = {}

                    if os.path.exists(path):

                        df_map = pd.read_csv(path, encoding='utf-8-sig')

                        if '交易营业部名称' in df_map.columns and '别名' in df_map.columns:
                            df_map['别名'] = df_map['别名'].fillna('').astype(str).str.strip()

                            alias_map = dict(zip(df_map['交易营业部名称'], df_map['别名']))

                    # 调试：打印前5个别名

                    print(f"🔍 别名映射示例: {list(alias_map.items())[:5]}")

                    target_names = []

                    for name, alias in alias_map.items():

                        if alias == yyb_alias.strip():  # 👈 增加 strip()

                            target_names.append(name)

                    if target_names:

                        df = df[df['交易营业部名称'].isin(target_names)]

                        print(f"✅ 按别名 '{yyb_alias}' 筛选，匹配 {len(target_names)} 个营业部")

                    else:

                        print(f"⚠️ 别名 '{yyb_alias}' 未匹配任何营业部！可用别名: {sorted(set(alias_map.values()))}")

                        df = df.iloc[0:0]

                except Exception as e:

                    print(f"❌ 按别名筛选出错: {e}")

                    traceback.print_exc()
        # =======================================================

        # =======================================================

        print("📊 正在进行分组统计...")
        result_df = df.groupby('交易营业部名称').apply(aggregate_stats).reset_index(drop=True)
        result_df = result_df[result_df['个股列表'] != '']

        # 保存文件
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        result_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        print(f"✅ 统计完成！文件已保存至: {output_path}")
        print(f"📈 共统计 {len(result_df)} 个营业部")

        return result_df

    except Exception as e:
        print(f"❌ 处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None

class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
# ================= 龙虎榜数据处理类 =================
class DragonTigerDataProcessor:
    """龙虎榜数据处理器"""

    def __init__(self):
        self.current_selected_rows = []  # 当前选中的行数据
        self.total_summary = {}  # 总合计数据

    def calculate_summary_from_list_tb(self, list_tb):
        """
        从list_tb中选中的行计算总合计

        Args:
            list_tb: QTableWidget对象，包含选中的行

        Returns:
            dict: 包含总合计数据的字典
        """
        selected_rows = []
        total_buy = 0.0
        total_sell = 0.0

        # 获取选中行的数据
        selected_items = list_tb.selectedItems()
        if not selected_items:
            print("⚠️ 未选中任何行")
            return None

        # 获取选中行的唯一行号
        selected_rows_indices = list(set(item.row() for item in selected_items))

        for row_idx in selected_rows_indices:
            try:
                # 获取行的关键数据
                stock_code = list_tb.item(row_idx, self._get_col_index(list_tb, '代码')).text()
                stock_name = list_tb.item(row_idx, self._get_col_index(list_tb, '名称')).text()
                list_date = list_tb.item(row_idx, self._get_col_index(list_tb, '上榜日')).text()

                # 获取买入额和卖出额（注意处理可能的数值格式）
                buy_amount_str = list_tb.item(row_idx, self._get_col_index(list_tb, '买入额')).text()
                sell_amount_str = list_tb.item(row_idx, self._get_col_index(list_tb, '卖出额')).text()

                # 转换为数值（处理可能包含逗号或空格的格式）
                buy_amount = self._parse_amount(buy_amount_str)
                sell_amount = self._parse_amount(sell_amount_str)

                # 累计总金额
                total_buy += buy_amount
                total_sell += sell_amount

                # 保存选中行数据
                selected_rows.append({
                    '代码': stock_code,
                    '名称': stock_name,
                    '上榜日': list_date,
                    '买入额': buy_amount,
                    '卖出额': sell_amount
                })

            except Exception as e:
                print(f"❌ 处理第 {row_idx} 行时出错: {e}")
                continue

        # 计算总净额（根据需求：两者相加）
        total_net = total_buy + total_sell

        # 保存总合计数据
        self.total_summary = {
            '总买入金额': total_buy,
            '总卖出金额': total_sell,
            '总净额': total_net
        }
        self.current_selected_rows = selected_rows

        print(f"✅ 计算完成: 买入={total_buy:.2f}, 卖出={total_sell:.2f}, 净额={total_net:.2f}")
        print(f"📊 选中了 {len(selected_rows)} 行数据")

        return self.total_summary

    def populate_detail_tb(self, detail_tb, list_tb):
        """
        填充detail_tb表格

        Args:
            detail_tb: QTableWidget对象，用于显示详情
            list_tb: QTableWidget对象，从中获取选中的行
        """
        # 计算总合计
        summary = self.calculate_summary_from_list_tb(list_tb)
        if summary is None:
            return False

        # 清空detail_tb
        detail_tb.setRowCount(0)

        # 添加列头
        columns = ['上榜日', '代码', '名称', '买入额', '卖出额', '净额']
        detail_tb.setColumnCount(len(columns))
        detail_tb.setHorizontalHeaderLabels(columns)

        # 添加选中行的数据
        for row_data in self.current_selected_rows:
            row_position = detail_tb.rowCount()
            detail_tb.insertRow(row_position)

            # 计算单行净额
            row_net = row_data['买入额'] + row_data['卖出额']

            # 填充单元格
            detail_tb.setItem(row_position, 0, QtWidgets.QTableWidgetItem(row_data['上榜日']))
            detail_tb.setItem(row_position, 1, QtWidgets.QTableWidgetItem(row_data['代码']))
            detail_tb.setItem(row_position, 2, QtWidgets.QTableWidgetItem(row_data['名称']))
            detail_tb.setItem(row_position, 3, QtWidgets.QTableWidgetItem(f"{row_data['买入额']:.2f}"))
            detail_tb.setItem(row_position, 4, QtWidgets.QTableWidgetItem(f"{row_data['卖出额']:.2f}"))
            detail_tb.setItem(row_position, 5, QtWidgets.QTableWidgetItem(f"{row_net:.2f}"))

        # 添加总合计行
        self._add_summary_row(detail_tb, summary)

        # 设置列宽自适应
        detail_tb.resizeColumnsToContents()

        return True

    def _add_summary_row(self, detail_tb, summary):
        """添加总合计行"""
        row_position = detail_tb.rowCount()
        detail_tb.insertRow(row_position)

        # 创建总计行样式
        from PyQt5.QtGui import QColor, QBrush
        from PyQt5.QtCore import Qt

        # 设置总计行的背景色为淡黄色
        for col in range(detail_tb.columnCount()):
            item = QtWidgets.QTableWidgetItem()
            item.setBackground(QBrush(QColor(255, 255, 200)))
            item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

            if col == 0:
                item.setText("★ 总合计")
            elif col == 1:
                item.setText(f"{len(self.current_selected_rows)} 个")
            elif col == 2:
                item.setText("个股")
            elif col == 3:
                item.setText(f"{summary['总买入金额']:.2f}")
            elif col == 4:
                item.setText(f"{summary['总卖出金额']:.2f}")
            elif col == 5:
                item.setText(f"{summary['总净额']:.2f}")

            detail_tb.setItem(row_position, col, item)

        print(f"✅ 已添加总合计行")

    def _get_col_index(self, table, column_name):
        """获取列索引"""
        for col in range(table.columnCount()):
            if table.horizontalHeaderItem(col).text() == column_name:
                return col
        return -1

    def _parse_amount(self, amount_str):
        """解析金额字符串为数值"""
        try:
            # 移除空格和逗号
            cleaned = amount_str.replace(',', '').replace(' ', '').strip()
            # 转换为浮点数
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0


# ================= 新增：支持数值排序的表格项类 =================
class NumericTableWidgetItem(QtWidgets.QTableWidgetItem):
    """
    自定义表格项，支持按数值大小排序
    如果设置了 UserRole 数据，则按数值排序；否则按文本排序
    """

    def __init__(self, text):
        super().__init__(text)

    def __lt__(self, other):
        # 尝试获取我们存储在 UserRole 中的数值
        value_self = self.data(QtCore.Qt.UserRole)
        value_other = other.data(QtCore.Qt.UserRole)

        # 如果两边都有数值，则按数值比较
        if value_self is not None and value_other is not None:
            try:
                return float(value_self) < float(value_other)
            except (ValueError, TypeError):
                pass

        # 如果没有数值（或者是字符串列），则回退到默认的文本比较
        return super().__lt__(other)


# ==============================================================


class MainWindow(object):
    def __init__(self):
        super().__init__()
        """在MainWindow的__init__方法中添加初始化"""

        # 新增：龙虎榜数据处理器
        self.dragon_tiger_processor = DragonTigerDataProcessor()

        # ================= 新增：保存当前状态用于刷新 =================
        self.current_filters = {}  # 保存当前的查询条件
        self.current_detail_info = {}

        try:
            print("🔄 程序启动：正在读取详情数据缓存...")
            # 读取完整数据用于 yyb_st_tb 筛选
            if os.path.exists('data/lhb_detail_b.csv'):
                self.lhb_detail_b_df = pd.read_csv('data/lhb_detail_b.csv', encoding='utf-8-sig', header=0)
                # 简单清洗
                self.lhb_detail_b_df['代码'] = self.lhb_detail_b_df['代码'].astype(str).str.strip()
                self.lhb_detail_b_df['交易营业部名称'] = self.lhb_detail_b_df['交易营业部名称'].astype(str).str.strip()
                print(f"✅ 详情数据缓存已加载，共 {len(self.lhb_detail_b_df)} 行")
            else:
                print("⚠️ 详情数据文件不存在: data/lhb_detail_b.csv")
                self.lhb_detail_b_df = pd.DataFrame()  # 设为空 DataFrame 以防报错
        except Exception as e:
            print(f"❌ 初始化数据加载失败: {e}")
            self.lhb_detail_b_df = pd.DataFrame()  # 设为空 DataFrame 以防报错

        # ================= 新增：读取大类数据 =================
        self.yyb_categories = []
        self.yyb_category_to_names = {}  # 大类 -> 该大类的营业部名称列表
        self.selected_category = "全部"  # 默认选中"全部"

        try:
            category_map, _ = self.get_yyb_maps()
            if category_map:
                # 获取所有唯一的大类
                self.yyb_categories = sorted(set([v for v in category_map.values() if v]))
                print(f"✅ 已读取大类数据: {self.yyb_categories}")

                # 构建大类到营业部名称的映射
                for name, category in category_map.items():
                    if category:  # 只记录非空的大类
                        if category not in self.yyb_category_to_names:
                            self.yyb_category_to_names[category] = []
                        self.yyb_category_to_names[category].append(name)

                print(f"✅ 大类映射构建完成，共 {len(self.yyb_category_to_names)} 个大类")
            else:
                print("⚠️ 未找到大类数据")
        except Exception as e:
            print(f"❌ 读取大类数据失败: {e}")
        # ======================================================
        # ================= 新增：读取所有别名数据 =================
        self.all_aliases = []
        try:
            _, alias_map = self.get_yyb_maps()
            if alias_map:
                # 获取所有唯一的别名
                self.all_aliases = sorted(set([v for v in alias_map.values() if v]))
                print(f"✅ 已读取所有别名数据: {self.all_aliases}")
        except Exception as e:
            print(f"❌ 读取别名数据失败: {e}")
        # ======================================================

    # ================= 新增：营业部名称缩写函数 =================
    def abbreviate_yyb_name(self, yyb_name):
        """
        对营业部名称进行缩写
        规则：证券股份有限公司 -> a, 证券营业部 -> b
        例如：广发证券股份有限公司深圳后海证券营业部 -> 广发a深圳后海b
        """
        if not yyb_name or yyb_name == 'nan':
            return yyb_name

        # 按顺序替换，确保优先替换长的词组
        # 证券股份有限公司 -> a
        yyb_name = yyb_name.replace('证券股份有限公司', 'a')
        yyb_name = yyb_name.replace('证券有限公司', 'b')
        yyb_name = yyb_name.replace('证券有限责任公司', 'c')
        yyb_name = yyb_name.replace('中国国际金融股份有限公司', '中国国际金融d')
        yyb_name = yyb_name.replace('摩根大通证券(中国)有限公司', '摩根大通d')
        # 证券营业部 -> b
        yyb_name = yyb_name.replace('证券营业部', 'f')

        return yyb_name
    # ====================================================

    # ====================================================


    def on_list_tb_selection_changed(self):
        """
        当list_tb选择改变时，自动更新detail_tb
        """
        if hasattr(self, 'detail_tb') and hasattr(self, 'list_tb'):
            try:
                success = self.dragon_tiger_processor.populate_detail_tb(self.detail_tb, self.list_tb)
                if success:
                    print("✅ detail_tb已自动更新")
            except Exception as e:
                print(f"❌ 更新detail_tb时出错: {e}")

    def on_show_summary_clicked(self):
        """
        显示总合计信息（可选：弹窗显示）
        """
        if hasattr(self, 'dragon_tiger_processor'):
            summary = self.dragon_tiger_processor.total_summary
            if summary:
                from PyQt5.QtWidgets import QMessageBox
                msg = f"""总合计信息：
                    ━━━━━━━━━━━━━━━━━
                    总买入金额: {summary['总买入金额']:.2f} 亿
                    总卖出金额: {summary['总卖出金额']:.2f} 亿
                    总净额: {summary['总净额']:.2f} 亿
                    ━━━━━━━━━━━━━━━━━
                    选中个股数: {len(self.dragon_tiger_processor.current_selected_rows)} 个
                        """
                QMessageBox.information(None, "总合计", msg)

    def get_selected_stock_info(self):
        """
        获取选中行的个股详情信息

        Returns:
            list: 包含个股信息的字典列表
        """
        if hasattr(self, 'dragon_tiger_processor'):
            return self.dragon_tiger_processor.current_selected_rows
        return []

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        # 设置初始大小，允许用户调整
        MainWindow.resize(1920, 1080)  # 稍微加宽以显示更多列

        icon = QtGui.QIcon()
        try:
            icon.addPixmap(QtGui.QPixmap("app4.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        except:
            print("未找到app4.ico图标，不影响窗口功能")
        MainWindow.setWindowIcon(icon)

        # ================= 滚动区域设置 =================
        self.scrollArea = QtWidgets.QScrollArea(MainWindow)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")

        self.centralwidget = QtWidgets.QWidget()
        self.centralwidget.setObjectName("centralwidget")

        # 将 centralwidget 放入滚动区域
        self.scrollArea.setWidget(self.centralwidget)
        MainWindow.setCentralWidget(self.scrollArea)

        # ================= 主布局 =================
        main_layout = QVBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- Banner ---
        self.banner = QtWidgets.QLabel(self.centralwidget)
        self.banner.setFixedHeight(50)
        font_banner = QtGui.QFont("SimHei", 18, QtGui.QFont.Bold)
        self.banner.setFont(font_banner)
        self.banner.setStyleSheet(
            "color: white; background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(0, 85, 128), stop:1 rgb(0, 170, 255));")
        self.banner.setAlignment(QtCore.Qt.AlignCenter)
        self.banner.setObjectName("banner")
        main_layout.addWidget(self.banner)

        # ================= 筛选条件区域 =================
        filter_group = QGroupBox("筛选条件")
        filter_group.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid gray; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        filter_layout = QVBoxLayout()
        filter_group.setLayout(filter_layout)

        # --- 1. 股票范围 ---
        stock_layout = QHBoxLayout()
        stock_label = QLabel("股票范围:")
        stock_label.setStyleSheet("font-weight: bold; color: #333;")
        stock_layout.addWidget(stock_label)

        self.stock_btn_group = QButtonGroup()  # 用于互斥或其他逻辑管理

        stock_options = ["全部", "沪A", "科创板", "深A", "创业板", "京A", "可转债"]
        for idx, text in enumerate(stock_options):
            btn = QPushButton(text)
            btn.setCheckable(True)
            if idx == 0: btn.setChecked(True)  # 默认选中全部
            # 样式设置
            btn.setStyleSheet("""
                QPushButton:checked { background-color: rgb(0, 170, 255); color: white; }
                QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px 10px; }
            """)
            setattr(self, f"btn_stock_{idx}", btn)  # 动态命名 self.btn_stock_0 等
            self.stock_btn_group.addButton(btn)
            stock_layout.addWidget(btn)

        # 个股输入框
        stock_layout.addSpacing(20)
        stock_layout.addWidget(QLabel("个股代码/名称:"))
        self.input_stock = QtWidgets.QLineEdit()
        self.input_stock.setPlaceholderText("输入代码或名称")
        self.input_stock.setFixedWidth(100)
        # ===== 修改：设置样式为20号黑体加粗，绿色 =====
        self.input_stock.setStyleSheet("font-size: 20pt; font-weight: bold; color: green;")

        # ===== 修改：限制输入为6位数字 =====
        reg_ex = QRegExp("[0-9]{2,6}")  # 正则表达式匹配6位数字
        validator = QRegExpValidator(reg_ex, self.input_stock)
        self.input_stock.setValidator(validator)

        # ===== 修改：按回车键自动开始查询 =====
        self.input_stock.returnPressed.connect(self.on_query_clicked)
        stock_layout.addWidget(self.input_stock)

        stock_layout.addStretch()
        filter_layout.addLayout(stock_layout)

        # --- 2. 日期范围 ---
        date_layout = QHBoxLayout()
        date_label = QLabel("日期范围:")
        date_label.setStyleSheet("font-weight: bold; color: #333;")
        date_layout.addWidget(date_label)

        # 【新增】创建日期按钮组，实现互斥（单选）效果
        self.date_btn_group = QtWidgets.QButtonGroup(self.centralwidget)

        # 用于存储日期按钮，方便后续获取选中的是哪一个
        self.date_btns = []

        # ================= 修改开始 =================
        # 【修改点1】在选项列表中加入 "自定义"
        date_options = ["当天", "近3日", "近5日", "近10日", "近30日", "自定义"]
        # ===========================================

        for idx, text in enumerate(date_options):
            btn = QPushButton(text)
            btn.setCheckable(True)

            # 【关键】将按钮添加到按钮组中，实现互斥选中
            self.date_btn_group.addButton(btn)

            if idx == 0: btn.setChecked(True)  # 默认选中当天
            btn.setStyleSheet("""
                        QPushButton:checked { background-color: rgb(0, 170, 255); color: white; }
                        QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px 10px; }
                    """)
            setattr(self, f"btn_date_{text}", btn)
            self.date_btns.append(btn)
            date_layout.addWidget(btn)

        # 日期选择器
        date_layout.addSpacing(20)

        # 日期选择器
        self.date_start = QDateEdit(calendarPopup=True)
        self.date_start.setDate(datetime.now().date() - timedelta(days=30))
        self.date_start.setFixedWidth(120)
        date_layout.addWidget(self.date_start)

        date_layout.addWidget(QLabel("至"))
        self.date_end = QDateEdit(calendarPopup=True)
        self.date_end.setDate(datetime.now().date())
        self.date_end.setFixedWidth(120)
        date_layout.addWidget(self.date_end)

        date_layout.addStretch()
        filter_layout.addLayout(date_layout)

        # --- 3. 营业部范围 ---
        yyb_layout = QHBoxLayout()
        yyb_label = QLabel("营业部范围:")
        yyb_label.setStyleSheet("font-weight: bold; color: #333;")
        yyb_layout.addWidget(yyb_label)

        # 下拉框
        # 下拉框
        self.combo_yyb = QComboBox()
        self.combo_yyb.setFixedWidth(120)
        yyb_layout.addWidget(QLabel("快速选择:"))
        yyb_layout.addWidget(self.combo_yyb)

        # ===== 修改：添加"全部"和从CSV读取的大类 =====
        # 设置下拉框选项："全部" + 从CSV读取的大类
        options = ["全部"] + self.yyb_categories
        self.combo_yyb.addItems(options)
        print(f"📋 下拉框选项: {options}")
        # ==========================================
        # ===== 新增：别名筛选 =====
        yyb_layout.addSpacing(10)  # 增加间距
        yyb_layout.addWidget(QLabel("别名筛选:"))
        self.combo_alias = QComboBox()
        self.combo_alias.setFixedWidth(120)
        # 设置下拉框选项："全部" + 从CSV读取的所有别名
        options_alias = ["全部"] + self.all_aliases
        self.combo_alias.addItems(options_alias)
        yyb_layout.addWidget(self.combo_alias)

        # 当前筛选别名显示 (Label)
        # 当前筛选别名显示 (Label)
        yyb_layout.addWidget(QLabel("当前:"))
        self.lbl_selected_alias = ClickableLabel("无")
        self.lbl_selected_alias.setFixedWidth(100)
        self.lbl_selected_alias.setStyleSheet("border: 1px solid #ccc; padding: 2px 5px; background-color: #f0f0f0;")
        self.lbl_selected_alias.setToolTip("点击可清空别名筛选")
        self.lbl_selected_alias.clicked.connect(self.on_alias_label_clicked)
        # ==========================================
        yyb_layout.addWidget(self.lbl_selected_alias)
        # ============================

        yyb_layout.addSpacing(20)

        # 输入框
        yyb_layout.addSpacing(20)
        yyb_layout.addWidget(QLabel("名称:"))
        self.input_yyb_name = QtWidgets.QLineEdit()
        self.input_yyb_name.setPlaceholderText("输入营业部名称")
        self.input_yyb_name.setFixedWidth(200)
        yyb_layout.addWidget(self.input_yyb_name)

        # # 别名
        # yyb_layout.addWidget(QLabel("别名1:"))
        # self.input_yyb_alias1 = QtWidgets.QLineEdit()
        # self.input_yyb_alias1.setFixedWidth(150)
        # yyb_layout.addWidget(self.input_yyb_alias1)
        #
        # yyb_layout.addWidget(QLabel("别名2:"))
        # self.input_yyb_alias2 = QtWidgets.QLineEdit()
        # self.input_yyb_alias2.setFixedWidth(150)
        # yyb_layout.addWidget(self.input_yyb_alias2)

        # 添加按钮
        self.btn_add_alias = QPushButton("添加别名")
        self.btn_add_alias.setStyleSheet("background-color: #FFA500; color: white; border-radius: 3px;")
        yyb_layout.addWidget(self.btn_add_alias)

        self.btn_add_alias = QPushButton("应用别名")
        self.btn_add_alias.setStyleSheet("background-color: #FFA500; color: white; border-radius: 3px;")
        self.btn_add_alias.clicked.connect(self.on_apply_alias_clicked)
        yyb_layout.addWidget(self.btn_add_alias)

        yyb_layout.addStretch()
        filter_layout.addLayout(yyb_layout)

        yyb_layout.addStretch()
        filter_layout.addLayout(yyb_layout)

        # 查询按钮
        # 查询按钮
        query_layout = QHBoxLayout()

        self.btn_query = QPushButton("开始查询")
        self.btn_query.setFixedHeight(35)
        self.btn_query.setStyleSheet("""
            QPushButton {
                background-color: rgb(0, 170, 255);
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: rgb(0, 140, 220); }
            QPushButton:pressed { background-color: rgb(0, 120, 200); }
        """)

        # ================= 新增：更新数据按钮 =================
        self.btn_update_yyb = QtWidgets.QPushButton("更新数据")
        self.btn_update_yyb.setFixedHeight(35)
        self.btn_update_yyb.setStyleSheet("""
                    QPushButton {
                        background-color: rgb(0, 200, 83);
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 4px;
                    }
                    QPushButton:hover { background-color: rgb(0, 180, 70); }
                    QPushButton:pressed { background-color: rgb(0, 160, 60); }
                """)
        # ==
        # ================= 新增：显示总合计按钮 =================
        self.btn_show_summary = QtWidgets.QPushButton("显示总合计")
        self.btn_show_summary.setFixedHeight(35)
        self.btn_show_summary.setStyleSheet("""
            QPushButton {
                background-color: rgb(255, 165, 0); /* 橙色以便区分 */
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius:4px;
            }
            QPushButton:hover { background-color: rgb(230, 145, 0); }
            QPushButton:pressed { background-color: rgb(200, 125, 0); }
        """)
        # ====================================================
        # ================= 新增：统计按钮 =================
        self.btn_statistics = QtWidgets.QPushButton("统计")
        self.btn_statistics.setFixedHeight(35)
        self.btn_statistics.setStyleSheet("""
                    QPushButton {
                        background-color: rgb(156, 39, 176); /* 紫色以便区分 */
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius:4px;
                    }
                    QPushButton:hover { background-color: rgb(142, 36, 170); }
                    QPushButton:pressed { background-color: rgb(123, 31, 162); }
                """)
        # ===================================================

        query_layout.addStretch()
        query_layout.addWidget(self.btn_query)
        query_layout.addSpacing(20)  # 添加一点间距
        query_layout.addWidget(self.btn_update_yyb)  # 添加更新数据按钮
        query_layout.addSpacing(20)
        query_layout.addWidget(self.btn_show_summary)  # 将按钮添加到布局
        query_layout.addSpacing(20)
        query_layout.addWidget(self.btn_statistics)
        query_layout.addStretch()

        filter_layout.addLayout(query_layout)
        main_layout.addWidget(filter_group)

        # ================= 表格区域 =================
        # 使用 2x2 的网格布局
        tables_grid = QGridLayout()
        tables_grid.setSpacing(10)

        # --- 第一排 ---

        # 1. list_tb (龙虎榜列表)
        self.list_tb = QTableWidget()
        # 列数将在加载CSV时动态设置
        self.list_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.list_tb.setObjectName("list_tb")
        # ===== 新增：启用点击列名排序功能 =====
        self.list_tb.setSortingEnabled(True)
        # 设置点击表头时切换排序顺序
        self.list_tb.horizontalHeader().setSectionsClickable(True)
        self.list_tb.horizontalHeader().setSortIndicatorShown(True)  # 显示排序指示器
        # ================================
        # 新增：设置选中行为整行，并设置深色选中背景
        self.list_tb.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.list_tb.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #005580;
                color: white;
            }
        """)
        self.list_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tables_grid.addWidget(QLabel("龙虎榜列表"), 0, 0)
        tables_grid.addWidget(self.list_tb, 1, 0)
        self.list_tb.setMinimumHeight(400)

        # ================= 新增：stat_tb (统计表) =================
        self.stat_tb = QTableWidget()
        self.stat_tb.setColumnCount(8)
        self.stat_tb.setHorizontalHeaderLabels([
            "代码", "名称", "最近上榜日", "上榜次数",
            "龙虎榜净买额", "龙虎榜买入额", "龙虎榜卖出额", "龙虎榜总成交额"
        ])
        self.stat_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.stat_tb.setObjectName("stat_tb")
        self.stat_tb.setSortingEnabled(True)
        self.stat_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 设置选中样式
        self.stat_tb.setStyleSheet("""
                    QTableWidget::item:selected {
                        background-color: #005580;
                        color: white;
                    }
                """)
        # 将 stat_tb 添加到与 list_tb 相同的位置 (1, 0)
        tables_grid.addWidget(self.stat_tb, 1, 0)
        # 初始隐藏 stat_tb
        self.stat_tb.hide()



        # 2. yyb_tb (营业部统计)
        self.yyb_tb = QTableWidget()
        self.yyb_tb.setColumnCount(9)  # 修改列数：增加"大类"列
        # 修改列名
        self.yyb_tb.setHorizontalHeaderLabels([
            "上榜日",
            "交易营业部名称",
            "大类",  # 新增列
            "别名",
            "上榜次数",
            "买入个股数",
            "卖出个股",
            "买入总金额",
            "卖出总金额"
        ])
        # 修改为 Interactive，这样手动设置的列宽才会生效
        self.yyb_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.yyb_tb.setObjectName("yyb_tb")
        self.yyb_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # ===== 新增：启用点击列名排序功能 =====
        self.yyb_tb.setSortingEnabled(True)
        self.yyb_tb.horizontalHeader().setSectionsClickable(True)
        self.yyb_tb.horizontalHeader().setSortIndicatorShown(True)
        # ================================
        tables_grid.addWidget(QLabel("营业部统计"), 0, 1)
        tables_grid.addWidget(self.yyb_tb, 1, 1)
        self.yyb_tb.setMinimumHeight(400)

        # --- 第二排 ---

        # 3. detail_tb (个股详情)
        # 修改：使用 self.lbl_detail_title 以便后续动态更新文本和样式
        self.lbl_detail_title = QLabel("个股详情")
        self.lbl_detail_title.setStyleSheet("font-weight: bold; font-size: 14px;")  # 初始样式
        tables_grid.addWidget(self.lbl_detail_title, 2, 0)

        self.detail_tb = QTableWidget()
        # 列数将在加载详情CSV时动态设置
        # 修改为 Fixed，严格按代码设置的宽度显示，不可拖动
        self.detail_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.detail_tb.setObjectName("detail_tb")
        self.detail_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # ================= 新增：设置 detail_tb 右键菜单 =================
        self.detail_tb.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.detail_tb.customContextMenuRequested.connect(self.show_detail_context_menu)
        # =============================================================

        tables_grid.addWidget(self.detail_tb, 3, 0)
        self.detail_tb.setMinimumHeight(400)

        # 4. yyb_st_tb (营业部持仓)
        self.lbl_yyb_st_title = QLabel("营业部持仓 (近期操作)")
        tables_grid.addWidget(self.lbl_yyb_st_title, 2, 1)

        self.yyb_st_tb = QTableWidget()

        self.yyb_st_tb.setColumnCount(7)
        # 修改列名
        self.yyb_st_tb.setHorizontalHeaderLabels([
            "上榜日",
            "代码",
            "名称",
            "涨跌幅",
            "flag",
            "买入金额(亿)",
            "卖出金额(亿)"
        ])
        self.yyb_st_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.yyb_st_tb.setObjectName("yyb_st_tb")
        self.yyb_st_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tables_grid.addWidget(self.yyb_st_tb, 3, 1)
        self.yyb_st_tb.setMinimumHeight(400)
        # 【修改点2】设置 yyb_tb 选中行为整行，并设置深色选中背景
        self.yyb_tb.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.yyb_st_tb.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #005580;
                color: white;
            }
        """)  # 注

        # 设置行伸展比例，使上下两排高度比例大致为 1:1
        tables_grid.setRowStretch(0, 0)  # Label 不伸展
        tables_grid.setRowStretch(1, 1)  # 第一排表格
        tables_grid.setRowStretch(2, 0)  # Label 不伸展
        tables_grid.setRowStretch(3, 1)  # 第二排表格
        tables_grid.setColumnStretch(0, 1)
        tables_grid.setColumnStretch(1, 1)

        main_layout.addLayout(tables_grid)

        # 底部弹簧，将内容顶上去
        main_layout.addStretch()

        # 菜单栏和状态栏设置
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1720, 23))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # ================= 事件连接 =================
        self.btn_query.clicked.connect(self.on_query_clicked)
        # 新增：连接 "更新数据" 按钮
        self.btn_update_yyb.clicked.connect(self.on_update_yyb_clicked)

        # 新增：连接 "显示总合计" 按钮
        self.btn_show_summary.clicked.connect(self.on_show_summary_clicked)
        self.btn_statistics.clicked.connect(self.on_statistics_clicked)

        # 新增：list_tb 点击事件，用于联动显示 detail_tb
        self.list_tb.itemClicked.connect(self.on_list_tb_clicked)

        self.list_tb.itemSelectionChanged.connect(self.on_list_tb_selection_changed)
        # 【修改点3】连接 yyb_tb 的选择改变事件
        self.yyb_tb.itemSelectionChanged.connect(self.on_yyb_tb_selection_changed)

        # 初始化表格数据 (默认加载"当天"数据)
        self.init_sample_data()
        self.list_tb.cellClicked.connect(self.on_list_tb_cell_clicked)

        # yyb_st_tb 单击事件
        self.yyb_st_tb.cellClicked.connect(self.on_yyb_st_tb_cell_clicked)
        self.stat_tb.cellClicked.connect(self.on_stat_tb_cell_clicked)

        # ================= 新增：连接 detail_tb 双击事件 =================
        self.detail_tb.cellDoubleClicked.connect(self.on_detail_tb_cell_double_clicked)
        # ============================================================

    # ================= 新增：list_tb 单击联动通达信 =================
    def on_list_tb_cell_clicked(self, row, col):
        """
        处理 list_tb 单元格单击事件
        如果点击的是"代码"列，则联动到通达信软件
        注意：此方法与原有的 on_list_tb_clicked (加载详情) 互不冲突
        """
        try:
            # 获取列名
            header_item = self.list_tb.horizontalHeaderItem(col)
            if not header_item:
                return

            header_text = header_item.text()

            # 只有点击代码列才触发联动
            if header_text == "代码":
                # 获取单元格内容
                item = self.list_tb.item(row, col)
                if item:
                    code = item.text().strip()
                    # 补足6位
                    code = code.zfill(6)

                    # 调用通达信联动函数
                    if link_tdx(code):
                        self.centralwidget.window().statusBar().showMessage(
                            f"✅ 已联动通达信: {code}", 3000
                        )
                    else:
                        QtWidgets.QMessageBox.warning(
                            None, "联动失败",
                            f"无法联动通达信，请确保通达信软件已打开。\n股票代码: {code}"
                        )
        except Exception as e:
            print(f"❌ list_tb 单击联动出错: {e}")

    # ================= 新增：yyb_st_tb 单击联动通达信 =================
    def on_yyb_st_tb_cell_clicked(self, row, col):
        """
        处理 yyb_st_tb 单元格单击事件
        如果点击的是"代码"列，则联动到通达信软件
        yyb_st_tb 列顺序: ["上榜日", "代码", "名称", "涨跌幅", "flag", "买入金额(亿)", "卖出金额(亿)"]
        """
        try:
            # 代码列固定在第2列，索引为1
            if col == 1:
                item = self.yyb_st_tb.item(row, col)
                if item:
                    code = item.text().strip()

                    # 确保代码有效
                    if code and code.isdigit():
                        code = code.zfill(6)

                        # 调用通达信联动函数
                        if link_tdx(code):
                            self.centralwidget.window().statusBar().showMessage(
                                f"✅ 已联动通达信: {code}", 3000
                            )
                        else:
                            QtWidgets.QMessageBox.warning(
                                None, "联动失败",
                                f"无法联动通达信，请确保通达信软件已打开。\n股票代码: {code}"
                            )
        except Exception as e:
            print(f"❌ yyb_st_tb 单击联动出错: {e}")

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "龙虎榜分析系统"))
        self.banner.setText(_translate("MainWindow", "龙虎榜分析系统 V2.0 - 全方位追踪主力资金"))

    def on_statistics_clicked(self):
        """ 统计按钮点击事件 """
        try:
            # 从界面控件获取当前的实际筛选条件
            filters = self.get_current_ui_filters()

            # 调用统计方法
            self.list_tb_statistics(filters)

            # 切换显示：隐藏 list_tb，显示 stat_tb
            self.list_tb.hide()
            self.stat_tb.show()

            self.centralwidget.window().statusBar().showMessage(
                f"已加载统计数据，当前筛选: {filters.get('date_mode', '')}", 3000
            )
        except Exception as e:
            print(f"❌ 统计按钮出错: {e}")
            import traceback
            traceback.print_exc()
    # ================= 新增：stat_tb 单击联动通达信 =================
    def on_stat_tb_cell_clicked(self, row, col):
        """
        处理 stat_tb 单元格单击事件
        如果点击的是"代码"列，则联动到通达信软件
        stat_tb 列顺序: ["代码", "名称", "最近上榜日", "上榜次数", ...]
        """
        try:
            # 代码列固定在第1列，索引为0
            if col == 0:
                item = self.stat_tb.item(row, col)
                if item:
                    code = item.text().strip()
                    # 确保代码有效
                    if code and code.isdigit():
                        code = code.zfill(6)
                        # 调用通达信联动函数
                        if link_tdx(code):
                            self.centralwidget.window().statusBar().showMessage(
                                f"✅ 已联动通达信: {code}", 3000
                            )
                        else:
                            QtWidgets.QMessageBox.warning(
                                None, "联动失败", f"无法联动通达信，请确保通达信软件已打开。\n股票代码: {code}"
                            )
        except Exception as e:
            print(f"❌ stat_tb 单击联动出错: {e}")

    def get_current_ui_filters(self):
        """从界面控件获取当前的筛选条件"""
        filters = {}

        # 1. 股票类型筛选
        stock_types = []
        for i in range(self.stock_btn_group.buttons().__len__()):
            btn = self.stock_btn_group.buttons()[i]
            if btn.isChecked():
                # 获取按钮文本
                btn_text = btn.text()
                stock_types.append(btn_text)
        filters['stock_types'] = stock_types if stock_types else ['全部']

        # 2. 个股输入
        filters['stock_input'] = self.input_stock.text().strip()

        # 3. 日期筛选 - 关键修复点！
        date_mode = "当天"  # 默认值
        for btn in self.date_btns:
            if btn.isChecked():
                date_mode = btn.text()
                break
        filters['date_mode'] = date_mode

        # 4. 自定义日期范围
        if date_mode == "自定义":
            filters['start_date'] = self.date_start.date().toString("yyyy-MM-dd")
            filters['end_date'] = self.date_end.date().toString("yyyy-MM-dd")
        else:
            filters['start_date'] = ""
            filters['end_date'] = ""

        # 5. 营业部筛选
        filters['yyb_category'] = self.combo_yyb.currentText()
        filters['yyb_name'] = self.input_yyb_name.text().strip()
        filters['yyb_alias'] = getattr(self, '_current_selected_alias', '')

        print(f"📋 从界面获取的筛选条件: {filters}")
        return filters

    def eventFilter(self, obj, event):
        """
        事件过滤器：用于处理 Label 点击等事件
        """
        # 如果是当前别名 Label 且触发了鼠标左键点击
        if obj == self.lbl_selected_alias and event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                self.on_alias_label_clicked(event)
                return True
        # 其他事件交给父类处理
        return super().eventFilter(obj, event)

    def on_apply_alias_clicked(self):
        current_text = self.combo_alias.currentText()
        if current_text and current_text != "全部":
            self.lbl_selected_alias.setText(current_text)
            self.lbl_selected_alias.setStyleSheet(
                "border: 1px solid #4CAF50; padding: 2px 5px; background-color: #e8f5e9; color: green;")
            self._current_selected_alias = current_text  # 👈 新增
            print(f"✅ 应用别名筛选: {current_text}")
        else:
            self.on_alias_label_clicked(None)

    def on_alias_label_clicked(self, event=None):
        self.lbl_selected_alias.setText("无")
        self.lbl_selected_alias.setStyleSheet("border: 1px solid #ccc; padding: 2px 5px; background-color: #f0f0f0;")
        self._current_selected_alias = ""  # 👈 新增
        print("🗑️ 已清空别名筛选")
    # ================= 修改/新增：大类和别名管理相关方法 =================
    def get_yyb_maps(self):
        """
        从 data/yyb.csv 读取大类和别名，返回 {name: category} 和 {name: alias}
        注意：yyb.csv中存储的是缩写名称
        """
        path = 'data/yyb.csv'
        category_map = {}
        alias_map = {}
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, encoding='utf-8-sig')
                # 确保列名正确
                if '交易营业部名称' in df.columns:
                    if '大类' in df.columns:
                        df['大类'] = df['大类'].fillna('')
                        category_map = dict(zip(df['交易营业部名称'], df['大类']))
                    if '别名' in df.columns:
                        df['别名'] = df['别名'].fillna('')
                        alias_map = dict(zip(df['交易营业部名称'], df['别名']))
            except Exception as e:
                print(f"❌ 读取别名/大类文件出错: {e}")
        return category_map, alias_map

    def update_yyb_data(self, yyb_name, category=None, alias=None):
        """
        统一更新数据数据到 data/yyb.csv (增强异常处理，支持大类和别名)
        如果营业部存在则更新，不存在则追加
        注意：yyb_name 应该是缩写名称
        """
        path = 'data/yyb.csv'
        try:
            df = pd.DataFrame(columns=['交易营业部名称', '大类', '别名'])

            # 1. 读取现有数据
            if os.path.exists(path):
                df = pd.read_csv(path, encoding='utf-8-sig')
                # 容错：确保列存在
                if '交易营业部名称' not in df.columns:
                    df = pd.DataFrame(columns=['交易营业部名称', '大类', '别名'])
                else:
                    if '大类' not in df.columns: df['大类'] = ''
                    if '别名' not in df.columns: df['别名'] = ''
                    df['大类'] = df['大类'].fillna('')
                    df['别名'] = df['别名'].fillna('')

            # 2. 更新或追加
            # 检查是否存在该营业部
            if yyb_name in df['交易营业部名称'].values:
                if category is not None:
                    df.loc[df['交易营业部名称'] == yyb_name, '大类'] = category
                if alias is not None:
                    df.loc[df['交易营业部名称'] == yyb_name, '别名'] = alias
            else:
                # 新增
                new_row = pd.DataFrame({
                    '交易营业部名称': [yyb_name],
                    '大类': [category if category is not None else ''],
                    '别名': [alias if alias is not None else '']
                })
                df = pd.concat([df, new_row], ignore_index=True)

            # 3. 保存
            df.to_csv(path, index=False, encoding='utf-8-sig')
            print(f"✅ 营业部数据已更新: {yyb_name}")
            return True

        except PermissionError:
            print(f"❌ 文件被占用，无法保存: {path}")
            QtWidgets.QMessageBox.critical(None, "错误",
                                           f"无法保存数据！\n文件 {path} 可能正被其他程序（如Excel）打开。\n请关闭该文件后重试。")
            return False
        except Exception as e:
            print(f"❌ 保存数据时发生未知错误: {e}")
            QtWidgets.QMessageBox.critical(None, "错误", f"保存数据失败：\n{str(e)}")
            return False

    def show_detail_context_menu(self, pos):
        """
        显示 detail_tb 的右键菜单 (修改：增加大类操作、常用筛选和查询功能)
        注意：使用缩写名称
        """
        try:
            item = self.detail_tb.itemAt(pos)
            if not item:
                return

            # ================= 新增：初始化所有 Action 变量 =================
            # 避免在某些代码路径下变量未定义导致 UnboundLocalError
            action_set_category = None
            action_del_category = None
            action_add_alias = None
            action_del_alias = None
            action_set_common = None
            action_query = None

            row = item.row()
            # 查找 '交易营业部名称'、'大类'、'别名' 所在的列索引
            name_col_idx = -1
            category_col_idx = -1
            alias_col_idx = -1

            for col in range(self.detail_tb.columnCount()):
                header_text = self.detail_tb.horizontalHeaderItem(col).text()
                if header_text == '交易营业部名称':
                    name_col_idx = col
                elif header_text == '大类':
                    category_col_idx = col
                elif header_text == '别名':
                    alias_col_idx = col

            if name_col_idx == -1 and category_col_idx == -1 and alias_col_idx == -1:
                return

            col_idx = item.column()
            header_text = self.detail_tb.horizontalHeaderItem(col_idx).text()

            # 获取单元格值
            cell_value = item.text().strip()

            # 创建菜单
            menu = QtWidgets.QMenu()

            # ================= 根据点击的列显示不同的菜单 =================
            if header_text == '交易营业部名称':
                # 营业部名称列：显示设置和查询选项
                yyb_name = cell_value
                if not yyb_name:
                    return

                action_set_category = menu.addAction("设置大类")
                action_del_category = menu.addAction("删除大类")
                menu.addSeparator()
                action_add_alias = menu.addAction("设置别名")
                action_del_alias = menu.addAction("删除别名")
                menu.addSeparator()
                # ================= 新增：查询菜单 =================
                action_query = menu.addAction(f"🔍 查询此营业部: {yyb_name}")
                action_query.setData(('name', yyb_name))
                # ==================================================

            elif header_text == '大类':
                # 大类列：显示删除和查询选项
                category_value = cell_value
                if not category_value:
                    return

                action_del_category = menu.addAction("删除大类")
                menu.addSeparator()
                # ================= 新增：查询菜单 =================
                action_query = menu.addAction(f"🔍 查询此大类: {category_value}")
                action_query.setData(('category', category_value))
                # ==================================================

            elif header_text == '别名':
                # 别名列：显示常用筛选、删除和查询选项
                alias_value = cell_value
                if not alias_value:
                    return

                action_set_common = menu.addAction(f"设为常用筛选: {alias_value}")
                action_set_common.setData(alias_value)
                action_del_alias = menu.addAction("删除别名")
                menu.addSeparator()
                # ================= 新增：查询菜单 =================
                action_query = menu.addAction(f"🔍 查询此别名: {alias_value}")
                action_query.setData(('alias', alias_value))
                # ==================================================

            # 显示菜单并获取用户操作
            action = menu.exec_(self.detail_tb.viewport().mapToGlobal(pos))

            # ================= 处理菜单操作 =================
            if action == action_set_category:
                # 只有在营业部名称列点击时才有这个动作
                self.handle_set_category(cell_value)
            elif action == action_del_category:
                if header_text == '交易营业部名称':
                    self.handle_delete_category(cell_value)
                elif header_text == '大类':
                    # 大类列的删除逻辑略有不同，需要知道对应的营业部名称
                    # 这里为了简化，如果点击大类列，可以提示用户去营业部名称列删除
                    # 或者遍历当前行找到营业部名称
                    name_item = self.detail_tb.item(row, name_col_idx)
                    if name_item:
                        self.handle_delete_category(name_item.text())
            elif action == action_add_alias:
                if header_text == '交易营业部名称':
                    self.handle_add_alias(cell_value)
            elif action == action_del_alias:
                if header_text == '交易营业部名称':
                    self.handle_delete_alias(cell_value)
                elif header_text == '别名':
                    # 别名列的删除逻辑
                    name_item = self.detail_tb.item(row, name_col_idx)
                    if name_item:
                        self.handle_delete_alias(name_item.text())
            elif action == action_set_common:
                alias_to_filter = action.data()
                self.on_set_common_filter_from_detail(alias_to_filter)
            # ================= 新增：处理查询点击 =================
            elif hasattr(action, 'data') and isinstance(action.data(), tuple):
                query_type, query_value = action.data()
                self.query_yyb_by_detail_cell(query_type, query_value)
            # ========================================================
        except Exception as e:
            print(f"❌ 右键菜单出错: {e}")
            import traceback
            traceback.print_exc()

    def on_detail_tb_cell_double_clicked(self, row, col):
        """
        处理 detail_tb 单元格双击事件
        如果点击的是"交易营业部名称"、"大类"或"别名"列，则执行查询
        """
        try:
            header_text = self.detail_tb.horizontalHeaderItem(col).text()

            if header_text in ['交易营业部名称', '大类', '别名']:
                item = self.detail_tb.item(row, col)
                if item:
                    cell_value = item.text().strip()
                    if cell_value:
                        # 确定查询类型
                        if header_text == '交易营业部名称':
                            query_type = 'name'
                        elif header_text == '大类':
                            query_type = 'category'
                        elif header_text == '别名':
                            query_type = 'alias'

                        print(f"🖱️ 双击查询: 类型={query_type}, 值={cell_value}")
                        self.query_yyb_by_detail_cell(query_type, cell_value)
        except Exception as e:
            print(f"❌ 双击事件处理出错: {e}")

    def query_yyb_by_detail_cell(self, query_type, query_value):
        """
        根据从 detail_tb 点击的单元格内容，查询营业部统计数据并显示在 yyb_tb 中

        Args:
            query_type: 查询类型 ('name', 'category', 'alias')
            query_value: 查询值
        """
        try:
            # ================= 构建筛选条件 =================
            # 保持当前的日期筛选设置
            current_date_mode = self.current_filters.get('date_mode', '当天')
            current_start = self.current_filters.get('start_date', '')
            current_end = self.current_filters.get('end_date', '')

            filters = {
                'stock_types': ['全部'],
                'stock_input': '',
                'date_mode': current_date_mode,
                'start_date': current_start,
                'end_date': current_end,
                'yyb_category': '',
                'yyb_name': '',
                'yyb_alias': ''
            }

            # 根据查询类型设置对应的筛选条件
            if query_type == 'name':
                filters['yyb_name'] = query_value
                print(f"🔍 按营业部名称查询: {query_value}")
            elif query_type == 'category':
                filters['yyb_category'] = query_value
                print(f"🔍 按大类查询: {query_value}")
            elif query_type == 'alias':
                filters['yyb_alias'] = query_value
                print(f"🔍 按别名查询: {query_value}")
            # =================================================

            # ================= 执行查询 =================
            print(f"📋 传入的筛选条件: {filters}")  # 新增调试

            # 调用 load_yyb_stat_to_table 加载数据到 yyb_tb
            self.load_yyb_stat_to_table(filters)

            # ================= 更新界面状态 =================
            # 可选：更新筛选栏的显示状态
            # 这里不强制更新筛选栏的下拉框，以免干扰用户的当前选择
            # 只在状态栏显示提示
            self.centralwidget.window().statusBar().showMessage(
                f"已查询: {query_value}", 3000
            )
            # =================================================

        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()

    def on_set_common_filter_from_detail(self, alias_text):
        try:
            if not alias_text or not isinstance(alias_text, str):
                return
            alias_clean = alias_text.strip()
            if not alias_clean:
                return

            self.lbl_selected_alias.setText(alias_clean)
            self.lbl_selected_alias.setStyleSheet(
                "border: 1px solid #4CAF50; padding: 2px 5px; background-color: #e8f5e9; color: green;")
            self._current_selected_alias = alias_clean
            print(f"✅ 已设为常用筛选: {alias_clean}")

            # 可选：自动查询
            # self.on_query_clicked()
        except Exception as e:
            print(f"❌ 设置常用筛选失败: {e}")
            QMessageBox.warning(None, "警告", f"设置常用筛选失败:\n{str(e)}")
    def handle_set_category(self, yyb_name):
        """设置大类"""
        try:
            category_map, alias_map = self.get_yyb_maps()
            current_category = category_map.get(yyb_name, "")

            category, ok = QtWidgets.QInputDialog.getText(
                None,
                "设置大类",
                f"请输入 '{yyb_name}' 的大类:",
                QtWidgets.QLineEdit.Normal,
                current_category
            )

            if ok:
                success = self.update_yyb_data(yyb_name, category=category, alias=None)
                if success:
                    self.refresh_all_tables()
        except Exception as e:
            print(f"❌ 设置大类流程出错: {e}")
            QtWidgets.QMessageBox.critical(None, "错误", f"设置大类出错：\n{str(e)}")

    def handle_delete_category(self, yyb_name):
        """删除大类"""
        try:
            reply = QtWidgets.QMessageBox.question(
                None,
                "删除大类",
                f"确定要删除 '{yyb_name}' 的大类吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                success = self.update_yyb_data(yyb_name, category="", alias=None)
                if success:
                    self.refresh_all_tables()
        except Exception as e:
            print(f"❌ 删除大类流程出错: {e}")
            QtWidgets.QMessageBox.critical(None, "错误", f"删除大类出错：\n{str(e)}")

    def handle_add_alias(self, yyb_name):
        """设置别名"""
        try:
            category_map, alias_map = self.get_yyb_maps()
            current_alias = alias_map.get(yyb_name, "")

            alias, ok = QtWidgets.QInputDialog.getText(
                None,
                "设置别名",
                f"请输入 '{yyb_name}' 的别名:",
                QtWidgets.QLineEdit.Normal,
                current_alias
            )

            if ok:
                success = self.update_yyb_data(yyb_name, category=None, alias=alias)
                if success:
                    self.refresh_all_tables()
        except Exception as e:
            print(f"❌ 设置别名流程出错: {e}")
            QtWidgets.QMessageBox.critical(None, "错误", f"设置别名出错：\n{str(e)}")

    def handle_delete_alias(self, yyb_name):
        """删除别名"""
        try:
            reply = QtWidgets.QMessageBox.question(
                None,
                "删除别名",
                f"确定要删除 '{yyb_name}' 的别名吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                success = self.update_yyb_data(yyb_name, category=None, alias="")
                if success:
                    self.refresh_all_tables()
        except Exception as e:
            print(f"❌ 删除别名流程出错: {e}")
            QtWidgets.QMessageBox.critical(None, "错误", f"删除别名出错：\n{str(e)}")

    def refresh_all_tables(self):
        """
        刷新所有表格以显示最新数据 (保持之前的异常处理)
        """
        try:
            # 1. 刷新 detail_tb (如果有当前选中)
            if hasattr(self, 'current_detail_info') and self.current_detail_info:
                info = self.current_detail_info
                # 只有当 code 和 date 都存在时才刷新，避免空数据崩溃
                if info.get('code') and info.get('date'):
                    print("🔄 正在刷新 detail_tb...")
                    self.load_detail_table_from_csv(info['code'], info['date'], info.get('name', ''))

            # 2. 刷新 yyb_tb (如果有当前筛选条件)
            if hasattr(self, 'current_filters') and self.current_filters:
                print("🔄 正在刷新 yyb_tb...")
                self.load_yyb_stat_to_table(self.current_filters)

        except Exception as e:
            print(f"❌ 刷新表格时出错: {e}")
            import traceback
            traceback.print_exc()
            # 即使刷新失败，也不要让程序崩溃，只提示用户
            QtWidgets.QMessageBox.warning(None, "刷新失败", f"更新界面显示时出错：\n{str(e)}\n请检查数据文件是否完整。")

    # ===================================================

    # ================= 新增：yyb_tb 选择改变事件 =================
    def on_yyb_tb_selection_changed(self):
        """
        当 yyb_tb 选择改变时触发：
        1. 更新标题显示日期和名称
        2. 加载对应的持仓数据到 yyb_st_tb
        """
        try:
            # 获取选中的行
            selected_items = self.yyb_tb.selectedItems()
            if not selected_items:
                return

            # 获取当前选中行的索引（取第一个选中的行）
            selected_row = selected_items[0].row()

            # 获取选中行的数据
            # yyb_tb 的列顺序: ["上榜日", "交易营业部名称", "大类", "别名", ...]
            # 注意：大类是新增的第3列(索引2)
            date_item = self.yyb_tb.item(selected_row, 0)  # 上榜日 在第 0 列
            yyb_name_item = self.yyb_tb.item(selected_row, 1)  # 交易营业部名称 在第 1 列

            if date_item and yyb_name_item:
                date_str = date_item.text()
                yyb_name = yyb_name_item.text()

                # 更新标题: "营业部持仓 (近期操作) - 上榜日: xxx, 营业部: xxx"
                self.lbl_yyb_st_title.setText(
                    f"营业部持仓 (近期操作) - 上榜日: {date_str}, 营业部: {yyb_name}"
                )
                # 设置标题颜色为蓝色以突出显示（可选）
                self.lbl_yyb_st_title.setStyleSheet("color: blue; font-weight: bold;")

                # 加载数据
                self.load_yyb_st_data(date_str, yyb_name)

        except Exception as e:
            print(f"❌ yyb_tb 选择改变时出错: {e}")
            import traceback
            traceback.print_exc()

    def load_yyb_st_data(self, date_str, yyb_name):
        """
        根据 上榜日 和 交易营业部名称 从 lhb_detail_b.csv 加载数据填充到 yyb_st_tb
        同时从 lhb_b.csv 中提取名称和涨跌幅
        """
        csv_path = 'data/lhb_detail_b.csv'
        lhb_csv_path = 'data/lhb_b.csv'
        print(f"🔍 筛选条件: 日期='{date_str}'")

        if self.lhb_detail_b_df is None or self.lhb_detail_b_df.empty:
            print("⚠️ lhb_detail_b_df 为空")
            self.yyb_st_tb.setRowCount(0)
            return

        df = self.lhb_detail_b_df.copy()

        # ===== 新增：将数据源的'上榜日'和输入的date_str都转换为datetime进行比较 =====
        try:
            # 将数据源的日期列转换为 datetime
            df['上榜日_dt'] = pd.to_datetime(df['上榜日'])
            # 将输入的日期字符串也转换为 datetime
            target_date = pd.to_datetime(date_str)
            # 进行筛选
            filtered_df = df[df['上榜日_dt'] == target_date]
        except Exception as e:
            print(f"❌ 日期转换或筛选出错: {e}")
            filtered_df = df.iloc[0:0]  # 返回空DataFrame

        if not os.path.exists(csv_path):
            print(f"警告: 未找到详情文件 {csv_path}")
            self.yyb_st_tb.setRowCount(1)
            self.yyb_st_tb.setColumnCount(1)
            self.yyb_st_tb.setHorizontalHeaderLabels(["提示"])
            self.yyb_st_tb.setItem(0, 0, QtWidgets.QTableWidgetItem("未找到详情数据文件"))
            return

        try:
            # 读取详情数据
            df_detail = pd.read_csv(csv_path, encoding='utf-8-sig')

            # ===== 新增：读取 lhb_b.csv 以获取名称和涨跌幅 =====
            df_lhb = None
            if os.path.exists(lhb_csv_path):
                df_lhb = pd.read_csv(lhb_csv_path, encoding='utf-8-sig')
                # 确保代码列是字符串类型
                df_lhb['代码'] = df_lhb['代码'].astype(str).str.strip()
                # 确保日期列是字符串类型，并去除空格
                df_lhb['上榜日'] = df_lhb['上榜日'].astype(str).str.strip()

                print(f"✅ 成功读取 lhb_b.csv，共 {len(df_lhb)} 行数据")
            else:
                print(f"⚠️ 未找到文件: {lhb_csv_path}")
            # ==========================================

            # 数据清洗：转换为字符串以防匹配出错
            df_detail['代码'] = df_detail['代码'].astype(str).str.strip()
            df_detail['上榜日'] = df_detail['上榜日'].astype(str).str.strip()
            df_detail['交易营业部名称'] = df_detail['交易营业部名称'].astype(str).str.strip()

            # ================== 关键修复：处理缩写匹配 ==================
            # 因为 yyb_name 是缩写名（例如 "广发a深圳后海b"），而 csv 中是全名
            # 所以我们需要将 csv 中的全名也转换为缩写，然后进行匹配
            print(f"🔍 使用全名进行匹配: '{yyb_name}'")

            # =======================================================

            # 筛选条件
            # 处理日期格式兼容（CSV中可能是 "20231225" 或 "2023-12-25"）
            mask_date = (df_detail['上榜日'] == date_str) | (df_detail['上榜日'] == date_str.replace('-', ''))

            # 修改：直接匹配全名
            mask_name = (df_detail['交易营业部名称'] == yyb_name)

            df_filtered = df_detail[mask_date & mask_name]

            print(f"🔍 筛选条件: 日期='{date_str}', 营业部(缩写)='{yyb_name}'")
            print(f"📊 筛选结果: 共 {len(df_filtered)} 条记录")

            # 填充表格
            self.yyb_st_tb.setRowCount(len(df_filtered))

            for row_idx in range(len(df_filtered)):
                row_data = df_filtered.iloc[row_idx]

                # 获取代码和日期
                code = str(row_data['代码']).strip()
                detail_date = str(row_data['上榜日']).strip()

                # ===== 修改点1：日期格式转换 20260130 -> 2026-01-30 =====
                if len(detail_date) == 8 and detail_date.isdigit():
                    # 格式：YYYYMMDD
                    formatted_date = f"{detail_date[:4]}-{detail_date[4:6]}-{detail_date[6:8]}"
                elif '-' in detail_date:
                    # 已经有横杠，直接使用
                    formatted_date = detail_date
                else:
                    formatted_date = detail_date
                # ====================================================

                # ===== 修改点2：代码补足6位 =====
                formatted_code = code.zfill(6)
                # =================================

                # ===== 修改点3：从 lhb_b.csv 中提取名称和涨跌幅 =====
                stock_name = ""
                change_percent = ""

                if df_lhb is not None and len(df_lhb) > 0:
                    # 准备匹配用的日期格式
                    dates_to_match = [
                        detail_date,  # 原始日期格式
                        formatted_date,  # 格式化后的日期 YYYY-MM-DD
                        detail_date.replace('-', ''),  # 去除横杠
                        formatted_date.replace('-', '')  # 格式化后去除横杠
                    ]

                    # 构建代码匹配条件（尝试多种代码格式）
                    codes_to_match = [
                        formatted_code,  # 补足6位
                        code,  # 原始代码
                        code.lstrip('0') or '0'  # 去除前导零
                    ]

                    # 在 lhb_b.csv 中查找匹配的行
                    matched_row = None
                    for test_code in codes_to_match:
                        code_match = df_lhb['代码'] == test_code
                        for test_date in dates_to_match:
                            date_match = df_lhb['上榜日'] == test_date
                            matched_rows = df_lhb[code_match & date_match]
                            if not matched_rows.empty:
                                matched_row = matched_rows.iloc[0]
                                print(f"✅ 找到匹配: 代码={test_code}, 日期={test_date}")
                                break
                        if matched_row is not None:
                            break

                    if matched_row is not None:
                        # 获取名称
                        if '名称' in matched_row.index:
                            stock_name = str(matched_row['名称'])
                        else:
                            print(f"⚠️ lhb_b.csv 中没有'名称'列")

                        # 获取涨跌幅
                        if '涨跌幅' in matched_row.index:
                            change_val = matched_row['涨跌幅']
                            if pd.notna(change_val):
                                change_percent = f"{float(change_val):.2f}%"
                        else:
                            print(f"⚠️ lhb_b.csv 中没有'涨跌幅'列")
                    else:
                        print(f"⚠️ 未找到匹配的记录: 代码={formatted_code}, 日期={formatted_date}")
                # =================================================

                # 1. 上榜日（格式化后）
                self.yyb_st_tb.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(formatted_date))

                # 2. 代码（补足6位）
                self.yyb_st_tb.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(formatted_code))

                # 3. 名称（从 lhb_b.csv 提取）
                self.yyb_st_tb.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(stock_name))

                # 4. 涨跌幅（从 lhb_b.csv 提取）
                change_item = QtWidgets.QTableWidgetItem(change_percent)
                # 根据涨跌幅正负设置颜色
                if change_percent:
                    try:
                        change_val = float(change_percent.replace('%', ''))
                        if change_val > 0:
                            change_item.setForeground(QtGui.QColor('red'))
                        elif change_val < 0:
                            change_item.setForeground(QtGui.QColor('green'))
                    except:
                        pass
                self.yyb_st_tb.setItem(row_idx, 3, change_item)

                # 5. flag
                flag_val = str(row_data.get('flag', '')).strip()
                flag_item = QtWidgets.QTableWidgetItem(flag_val)
                if flag_val == '买入':
                    flag_item.setForeground(QtGui.QColor('red'))
                elif flag_val == '卖出':
                    flag_item.setForeground(QtGui.QColor('green'))
                self.yyb_st_tb.setItem(row_idx, 4, flag_item)

                # 6. 买入金额(亿)
                buy_amt = row_data.get('买入金额(亿)', 0)
                self.yyb_st_tb.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(
                    f"{float(buy_amt):.2f}" if pd.notna(buy_amt) else "0.00"))

                # 7. 卖出金额(亿)
                sell_amt = row_data.get('卖出金额(亿)', 0)
                self.yyb_st_tb.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(
                    f"{float(sell_amt):.2f}" if pd.notna(sell_amt) else "0.00"))

            print(f"✅ 已加载营业部持仓数据: {len(df_filtered)} 条")

        except Exception as e:
            print(f"❌ 加载营业部持仓数据出错: {e}")
            import traceback
            traceback.print_exc()

    # ================= 更新数据按钮点击事件 =================
    def on_update_yyb_clicked(self):
        """更新数据按钮点击事件 - 执行 data_update.py 中的 update.run()"""
        try:
            # 显示状态信息
            self.statusbar.showMessage("正在更新数据，请稍候...", 0)  # 0表示永久显示直到被替换
            QtWidgets.QApplication.processEvents()  # 立即刷新UI，显示状态栏消息

            print("🔄 开始执行数据更新...")

            # 导入并执行数据更新
            from data_update import update

            # 创建update实例并执行run方法
            updater = update()
            updater.run()

            # 更新完成后的处理
            print("✅ 数据更新完成！")
            self.statusbar.showMessage("数据更新完成！", 5000)  # 显示5秒后自动消失

            # 可选：更新完成后自动重新加载数据到表格
            # 这里可以添加重新加载数据的逻辑，例如：
            # self.init_sample_data()  # 重新加载初始数据

            # 显示成功提示对话框（可选）
            QtWidgets.QMessageBox.information(
                None,
                "更新完成",
                "所有数据已成功更新！\n\n"
                "• 龙虎榜数据已更新\n"
                "• 基金数据已更新\n"
                "• 营业部数据已更新"
            )

        except ImportError as e:
            error_msg = f"❌ 导入 data_update 模块失败: {e}"
            print(error_msg)
            self.statusbar.showMessage("数据更新失败：模块导入错误", 5000)
            QtWidgets.QMessageBox.critical(None, "错误", f"无法导入数据更新模块:\n{str(e)}")

        except AttributeError as e:
            error_msg = f"❌ update类或run方法不存在: {e}"
            print(error_msg)
            self.statusbar.showMessage("数据更新失败：方法不存在", 5000)
            QtWidgets.QMessageBox.critical(None, "错误", f"数据更新方法不存在:\n{str(e)}")

        except Exception as e:
            error_msg = f"❌ 数据更新过程中发生错误: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.statusbar.showMessage("数据更新失败，请查看控制台日志", 5000)
            QtWidgets.QMessageBox.critical(None, "错误", f"数据更新失败:\n{str(e)}")
    # ================= 更新数据统计表 =================
    def update_yyb_tb_from_detail_csv(self):
        """
        根据 list_tb 中当前显示的股票代码，统计营业部信息并填充到 yyb_tb
        """
        csv_path = 'data/lhb_detail_b.csv'

        # --- 1. 获取 list_tb 中当前显示的所有唯一股票代码 ---
        displayed_stock_codes = set()
        if self.list_tb.rowCount() > 0:
            code_col_idx = -1
            for col in range(self.list_tb.columnCount()):
                if self.list_tb.horizontalHeaderItem(col).text() == "代码":
                    code_col_idx = col
                    break
            if code_col_idx != -1:
                for row in range(self.list_tb.rowCount()):
                    stock_code_item = self.list_tb.item(row, code_col_idx)
                    if stock_code_item:
                        displayed_stock_codes.add(stock_code_item.text())

        # --- 2. 从 lhb_detail_b.csv 读取数据 ---
        try:
            df_detail = pd.read_csv(
                csv_path,
                encoding='utf-8-sig',
                header=0,
                names=[
                    '上榜日', '代码', 'flag', '序号', '交易营业部名称',
                    '买入金额(亿)', '买入占比', '卖出金额(亿)', '卖出占比', '净额(亿)', '类型'
                ]
            )
        except Exception as e:
            print(f"❌ 读取 {csv_path} 失败: {e}")
            return

        # 如果 list_tb 有数据，则进行筛选
        # if displayed_stock_codes:
        #     df_detail = df_detail[df_detail['代码'].isin(displayed_stock_codes)]

        # --- 3. 数据预处理 ---
        # 确保金额列为数值类型，非数值转为0
        df_detail['买入金额(亿)'] = pd.to_numeric(df_detail['买入金额(亿)'], errors='coerce').fillna(0)
        df_detail['卖出金额(亿)'] = pd.to_numeric(df_detail['卖出金额(亿)'], errors='coerce').fillna(0)

        # --- 4. 按营业部分组并聚合计算 ---
        def aggregate_yyb(group):
            # 上榜次数：该营业部涉及的不同股票代码数量
            listed_count = group['代码'].nunique()

            # 买入相关
            buy_group = group[group['flag'] == '买入']
            buy_stock_count = buy_group['代码'].nunique()  # 买入个股数
            total_buy_amount = buy_group['买入金额(亿)'].sum()  # 买入总金额

            # 卖出相关
            sell_group = group[group['flag'] == '卖出']
            sell_stock_count = sell_group['代码'].nunique()  # 卖出个股数 (原需求为"卖出个股")
            total_sell_amount = sell_group['卖出金额(亿)'].sum()  # 卖出总金额

            # 获取最新的上榜日（假设是该营业部最近一次上榜）
            latest_date = group['上榜日'].max()

            return pd.Series({
                '上榜日': latest_date,
                '上榜次数': listed_count,
                '买入个股数': buy_stock_count,
                '卖出个股数': sell_stock_count,  # 注意：这里列名与UI定义一致
                '买入总金额': total_buy_amount,
                '卖出总金额': total_sell_amount
            })

        # 执行分组聚合
        if not df_detail.empty:
            yyb_summary = df_detail.groupby('交易营业部名称').apply(aggregate_yyb).reset_index()
        else:
            yyb_summary = pd.DataFrame()

        # --- 5. 填充 yyb_tb 表格 ---
        self.yyb_tb.setRowCount(0)  # 清空表格

        if yyb_summary.empty:
            print("📊 营业部统计: 无数据可显示")
            return

        # 设置行数
        self.yyb_tb.setRowCount(len(yyb_summary))

        # 定义表格列的顺序和对应的数据源
        # 注意：UI中定义的列是 ["上榜日", "交易营业部名称", "大类", "别名", "上榜次数", "买入个股数", "卖出个股", "买入总金额", "卖出总金额"]
        # 我们这里会按此顺序填充
        column_mapping = [
            ('上榜日', '上榜日'),
            ('交易营业部名称', '交易营业部名称'),
            ('大类', None),  # 暂不处理大类
            ('别名', None),  # 暂不处理别名
            ('上榜次数', '上榜次数'),
            ('买入个股数', '买入个股数'),
            ('买入总金额', '买入总金额'),
            ('卖出个股数', '卖出个股数'),  # UI列名是"卖出个股"，数据源是'卖出个股数'

            ('卖出总金额', '卖出总金额')
        ]

        for row_idx, (_, row_data) in enumerate(yyb_summary.iterrows()):
            for col_idx, (ui_col_name, data_col_name) in enumerate(column_mapping):
                if data_col_name is None:
                    # '大类' 或 '别名' 列
                    cell_value = ""
                else:
                    value = row_data[data_col_name]
                    if '金额' in ui_col_name:
                        # 金额列保留两位小数
                        cell_value = f"{value:.2f}"
                    elif isinstance(value, (int, float)):
                        # 其他数值列（如次数、个数）转为整数字符串
                        cell_value = str(int(value))
                    else:
                        # 日期或字符串
                        cell_value = str(value)

                item = QtWidgets.QTableWidgetItem(cell_value)
                self.yyb_tb.setItem(row_idx, col_idx, item)

        print(f"✅ 成功更新 yyb_tb，共 {len(yyb_summary)} 条记录")

    # ================= 从CSV加载数据（含筛选逻辑）=================
    # ================= 从CSV加载数据（含筛选逻辑）=================
    def load_list_tb_from_csv(self, filters=None):
        """从 data/lhb_b.csv 读取数据，根据筛选条件过滤后填充到 list_tb 表格"""
        csv_path = 'data/lhb_b.csv'

        if not os.path.exists(csv_path):
            print(f"警告: 未找到文件 {csv_path}")
            self.list_tb.setColumnCount(1)
            self.list_tb.setHorizontalHeaderLabels(["状态"])
            self.list_tb.setRowCount(1)
            self.list_tb.setItem(0, 0, QTableWidgetItem("未找到数据文件"))
            return

        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

            # 预处理：确保日期格式正确，代码转为字符串
            df['上榜日'] = pd.to_datetime(df['上榜日'])
            df['代码'] = df['代码'].astype(str)

            # ------------------- 1. 日期筛选 -------------------
            if filters:
                date_mode = filters.get('date_mode', '当天')
                if date_mode in ["当天", "近3日", "近5日", "近10日", "近30日"]:
                    unique_dates = sorted(df['上榜日'].unique(), reverse=True)
                    target_dates = []
                    if date_mode == "当天":
                        target_dates = [unique_dates[0]] if len(unique_dates) > 0 else []
                    elif date_mode == "近3日":
                        target_dates = unique_dates[:3]
                    elif date_mode == "近5日":
                        target_dates = unique_dates[:5]
                    elif date_mode == "近10日":
                        target_dates = unique_dates[:10]
                    elif date_mode == "近30日":
                        target_dates = unique_dates[:30]
                    if target_dates:
                        df = df[df['上榜日'].isin(target_dates)]
                elif date_mode == "自定义":
                    start_date = pd.to_datetime(filters.get('start_date'))
                    end_date = pd.to_datetime(filters.get('end_date'))
                    df = df[(df['上榜日'] >= start_date) & (df['上榜日'] <= end_date)]

            # ------------------- 2. 股票筛选 -------------------
            if filters:
                stock_types = filters.get('stock_types', [])
                stock_input = filters.get('stock_input', "").strip()

                if "全部" not in stock_types and stock_types:
                    masks = []
                    for st in stock_types:
                        if st == "沪A":
                            masks.append(df['代码'].str.startswith('6'))
                        elif st == "科创板":
                            masks.append(df['代码'].str.startswith('688'))
                        elif st == "深A":
                            masks.append(df['代码'].str.startswith('0') | df['代码'].str.startswith('001') |
                                         df['代码'].str.startswith('002') | df['代码'].str.startswith('003'))
                        elif st == "创业板":
                            masks.append(df['代码'].str.startswith('30'))
                        elif st == "京A":
                            masks.append(df['代码'].str.startswith('8') | df['代码'].str.startswith('43') |
                                         df['代码'].str.startswith('92'))
                        elif st == "可转债":
                            masks.append(df['代码'].str.startswith('11') | df['代码'].str.startswith('12') |
                                         df['代码'].str.startswith('13'))
                    if masks:
                        combined_mask = masks[0]
                        for m in masks[1:]:
                            combined_mask |= m
                        df = df[combined_mask]

                if stock_input:
                    df = df[df['代码'].str.contains(stock_input) | df['名称'].str.contains(stock_input)]

            # ===== 列名重命名 =====
            rename_map = {
                '龙虎榜净买额': '净买额',
                '龙虎榜买入额': '买入额',
                '龙虎榜卖出额': '卖出额',
                '龙虎榜成交额': '龙虎额',
                '市场总成交额': '总额',
                '净买额占总成交比': '净买占比',
                '成交额占总成交比': '龙虎占比',
                '流通市值': '流通',
            }
            df = df.rename(columns=rename_map)

            # ===== 删除不需要的列 =====
            for col in ['收盘价', '龙虎额',  '流通',  '上榜原因']:
                if col in df.columns:
                    df = df.drop(columns=[col])

            print(f"✅ 列名已更新: {df.columns.tolist()}")

            # ===== 【修改】移除预先排序，保留原始顺序，让用户自己点击排序 =====
            # sort_columns = [col for col in df.columns if '买入额' in col]
            # if sort_columns:
            #     df = df.sort_values(by=sort_columns[0], ascending=False)
            # =========================================================================

            # ------------------- 填充表格 -------------------
            columns = df.columns.tolist()
            num_columns = len(columns)

            # 临时禁用排序，避免填充时性能问题
            self.list_tb.setSortingEnabled(False)

            self.list_tb.setColumnCount(num_columns)
            self.list_tb.setHorizontalHeaderLabels(columns)
            self.list_tb.setRowCount(len(df))
            self.list_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

            # 定义需要正确排序的数值列
            numeric_columns = ['涨跌幅', '净买额', '买入额', '卖出额', '净买占比', '龙虎占比', '换手率']

            for col_idx, col_name in enumerate(columns):
                # 根据列名设置不同宽度
                if '上榜日' in col_name:
                    self.list_tb.setColumnWidth(col_idx, 75)
                elif '代码' in col_name or '涨跌幅' in col_name or '换手率' in col_name:
                    self.list_tb.setColumnWidth(col_idx, 60)
                elif '名称' in col_name:
                    self.list_tb.setColumnWidth(col_idx, 65)
                elif '解读' in col_name or '上榜原因' in col_name:
                    self.list_tb.setColumnWidth(col_idx, 180)
                else:
                    self.list_tb.setColumnWidth(col_idx, 60)

            for row_idx in range(len(df)):
                for col_idx, col_name in enumerate(columns):
                    value = df.iloc[row_idx][col_name]

                    if pd.isna(value):
                        display_value = ""
                        numeric_value = 0

                        # ===== 【新增】上榜日列特殊处理 =====
                    elif col_name == '上榜日':
                        try:
                            # pandas 的 datetime 对象，直接格式化为 YYYY-MM-DD
                            display_value = value.strftime('%Y-%m-%d')
                        except:
                            # 兼容处理：如果转失败（比如是字符串），截取前10位
                            display_value = str(value).split(' ')[0][:10]
                        numeric_value = 0
                    elif isinstance(value, (int, float)):
                        if col_name == "龙虎占比":
                            display_value = f"{value * 100:.2f}"
                            numeric_value = value * 100
                        elif col_name == "净买占比":
                            display_value = f"{value * 100:.2f}"
                            numeric_value = value * 100
                        else:
                            display_value = f"{value:.2f}"
                            numeric_value = value
                    else:
                        display_value = str(value)
                        numeric_value = 0

                    item = NumericTableWidgetItem(display_value)
                    # ===== 【新增】总额列整列背景设为灰色 =====
                    if col_name == '总额':
                        item.setBackground(QtGui.QColor("#e0e0e0"))  # 浅灰色背景
                    if col_name == '净买额':
                        item.setBackground(QtGui.QColor("#e0e0e0"))  # 浅灰色背景
                    # =============================================

                    # ===== 【关键修改】为数值列设置正确的数值用于排序 =====
                    if col_name in numeric_columns and isinstance(value,  float) and not pd.isna(value):
                        # 存储数值用于排序
                        item.setData(QtCore.Qt.UserRole, numeric_value)
                    # ====================================================
                    # ===== 【新增】解读列特殊处理：买入红色加粗，卖出绿色加粗 =====
                    # if col_name in ['解读'] and display_value:
                    #     # 创建 QLabel 用于显示富文本
                    #     label = QtWidgets.QLabel()
                    #     label.setStyleSheet("background-color: transparent;")
                    #
                    #     # 替换关键词为带样式的HTML
                    #     styled_text = display_value
                    #     styled_text = styled_text.replace('买入',
                    #                                       '<span style="color:red; font-weight:bold;">买入</span>')
                    #     styled_text = styled_text.replace('卖出',
                    #                                       '<span style="color:green; font-weight:bold;">卖出</span>')
                    #
                    #     label.setText(styled_text)
                    #     label.setTextFormat(QtCore.Qt.RichText)
                    #     label.setWordWrap(False)  # 允许换行
                    #
                    #     # 使用 setCellWidget 设置控件，而不是 setItem
                    #     self.list_tb.setCellWidget(row_idx, col_idx, label)
                    #     continue  # 跳过后续的 setItem 操作
                    # ============================================================

                    # 颜色逻辑
                    if isinstance(value, (int, float)) and not pd.isna(value):
                        check_val = value
                        if col_name == "龙虎占比":
                            check_val = value * 100
                        if col_name == "净买占比":
                            check_val = value * 100

                        # 龙虎占比 和 换手率 的颜色逻辑
                        if col_name in ["龙虎占比", "换手率"]:
                            if check_val > 30:
                                item.setForeground(QtGui.QColor("red"))
                            elif check_val >= 20:
                                item.setForeground(QtGui.QColor("magenta"))
                                font = item.font()
                                font.setBold(True)
                                item.setFont(font)
                            elif check_val >= 5:
                                item.setForeground(QtGui.QColor("blue"))
                            else:
                                item.setForeground(QtGui.QColor("black"))
                        elif col_name in ["净买占比"]:
                            if check_val > 20:
                                item.setForeground(QtGui.QColor("red"))
                            elif check_val >= 10:
                                item.setForeground(QtGui.QColor("magenta"))
                                font = item.font()
                                font.setBold(True)
                                item.setFont(font)
                            elif check_val >= 0:
                                item.setForeground(QtGui.QColor("blue"))
                            else:
                                item.setForeground(QtGui.QColor("green"))

                        elif col_name in ["总额"]:
                            if check_val > 20:
                                item.setForeground(QtGui.QColor("red"))
                            elif check_val >= 10:
                                item.setForeground(QtGui.QColor("magenta"))
                                font = item.font()
                                font.setBold(True)
                                item.setFont(font)
                            elif check_val >= 1:
                                item.setForeground(QtGui.QColor("blue"))
                            else:
                                item.setForeground(QtGui.QColor("green"))
                        elif "净买额" in col_name or "涨跌幅" in col_name:
                            if value < 0:
                                item.setForeground(QtGui.QColor("green"))
                            elif value > 0:
                                item.setForeground(QtGui.QColor("red"))

                    self.list_tb.setItem(row_idx, col_idx, item)

            # ===== 重新启用排序 =====
            self.list_tb.setSortingEnabled(True)

            # ===== 默认选中第一行 =====
            if self.list_tb.rowCount() > 0:
                self.list_tb.selectRow(0)
                first_item = self.list_tb.item(0, 0)
                if first_item:
                    self.on_list_tb_clicked(first_item)

            print(f"查询完成: 共加载 {len(df)} 条数据")
            self.centralwidget.window().statusBar().showMessage(f"查询完成: 找到 {len(df)} 条记录", 3000)

        except Exception as e:
            print(f"读取 CSV 文件时出错: {e}")
            import traceback
            traceback.print_exc()
            self.list_tb.setColumnCount(1)
            self.list_tb.setHorizontalHeaderLabels(["错误"])
            self.list_tb.setRowCount(1)
            self.list_tb.setItem(0, 0, QTableWidgetItem(f"读取错误: {str(e)}"))

    # ================= 新增：list_tb_statistics =================
    def list_tb_statistics(self, filters=None):
        """ 统计一段时间段内 lhb.csv 中的数据，显示在 stat_tb 中
        stat_tb的列名：代码，名称，最近上榜日，上榜次数，龙虎榜净买额，龙虎榜买入额，龙虎榜卖出额，龙虎榜总成交额
        """
        csv_path = 'data/lhb_b.csv'
        if not os.path.exists(csv_path):
            print(f"警告: 未找到文件 {csv_path}")
            self.stat_tb.setColumnCount(1)
            self.stat_tb.setHorizontalHeaderLabels(["状态"])
            self.stat_tb.setRowCount(1)
            self.stat_tb.setItem(0, 0, QTableWidgetItem("未找到数据文件"))
            return

        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            # 预处理：确保日期格式正确，代码转为字符串
            df['上榜日'] = pd.to_datetime(df['上榜日'])
            df['代码'] = df['代码'].astype(str)

            # 确保数值列为数值类型
            numeric_cols = ['龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜总成交额']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # 调试：打印原始数据信息
            print(f"原始数据形状: {df.shape}")
            print(f"原始数据日期范围: {df['上榜日'].min()} 到 {df['上榜日'].max()}")

            # ------------------- 1. 日期筛选 -------------------
            if filters:
                date_mode = filters.get('date_mode', '当天')
                print(f"🔍 应用日期筛选模式: {date_mode}")

                if date_mode in ["当天", "近3日", "近5日", "近10日", "近30日"]:
                    # 获取所有唯一的日期并排序（排除NaT）
                    valid_dates = df['上榜日'].dropna().unique()
                    unique_dates = sorted(valid_dates, reverse=True)
                    print(f"📊 数据中唯一日期数量: {len(unique_dates)}")

                    if len(unique_dates) == 0:
                        print("⚠️ 警告: 没有有效的日期数据")
                        df = df.iloc[0:0]  # 返回空DataFrame
                    else:
                        target_dates = []
                        if date_mode == "当天":
                            target_dates = [unique_dates[0]]
                        elif date_mode == "近3日":
                            target_dates = unique_dates[:3]
                        elif date_mode == "近5日":
                            target_dates = unique_dates[:5]
                        elif date_mode == "近10日":
                            target_dates = unique_dates[:10]
                        elif date_mode == "近30日":
                            target_dates = unique_dates[:30]

                        print(f"🎯 目标日期: {[d.strftime('%Y-%m-%d') for d in target_dates]}")
                        df = df[df['上榜日'].isin(target_dates)]

                elif date_mode == "自定义":
                    start_date = pd.to_datetime(filters.get('start_date'))
                    end_date = pd.to_datetime(filters.get('end_date'))
                    print(f"📅 自定义日期范围: {start_date} 到 {end_date}")
                    df = df[(df['上榜日'] >= start_date) & (df['上榜日'] <= end_date)]
            # ------------------- 2. 股票筛选 -------------------
            if filters:
                stock_types = filters.get('stock_types', [])  # 列表
                stock_input = filters.get('stock_input', "").strip()

                # 如果没有选择"全部"，且选择了特定板块，则按代码前缀筛选
                if "全部" not in stock_types and stock_types:
                    masks = []
                    for st in stock_types:
                        if st == "沪A":  # 6开头但非688
                            masks.append((df['代码'].str.startswith('6')))
                        elif st == "科创板":
                            masks.append(df['代码'].str.startswith('688'))
                        elif st == "深A":  # 0或3开头 (3大部分是创业板，这里简单处理为0)
                            masks.append(df['代码'].str.startswith('0') |
                                         df['代码'].str.startswith('001') |
                                         df['代码'].str.startswith('002') |
                                         df['代码'].str.startswith('003'))
                        elif st == "创业板":
                            masks.append(df['代码'].str.startswith('30'))
                        elif st == "京A":  # 北交所 8, 43, 92开头
                            masks.append(df['代码'].str.startswith('8') |
                                         df['代码'].str.startswith('43') |
                                         df['代码'].str.startswith('92'))
                        elif st == "可转债":  # 11, 12, 13开头
                            masks.append(df['代码'].str.startswith('11') |
                                         df['代码'].str.startswith('12') |
                                         df['代码'].str.startswith('13'))

                    if masks:
                        combined_mask = masks[0].copy()
                        for m in masks[1:]:
                            combined_mask |= m
                        df = df[combined_mask]

                # 个股输入框筛选
                if stock_input:
                    df = df[df['代码'].str.contains(stock_input) | df['名称'].str.contains(stock_input)]

            # 调试：打印股票筛选后数据信息
            print(f"股票筛选后数据形状: {df.shape}")

            # 关键修复：移除列名重命名和排序，这些操作不应在统计前进行
            # 直接进行分组统计，保留原始列名

            # ------------------- 3. 分组统计 -------------------
            if not df.empty:
                # 先计算每个代码的上榜次数
                count_df = df.groupby('代码').size().reset_index(name='上榜次数')
                print(f"计算上榜次数完成，前5条: {count_df.head()}")

                # 定义聚合函数
                agg_funcs = {
                    '名称': 'first',  # 取第一个名称
                    '上榜日': 'max',  # 最近上榜日 (日期最大)
                }

                # 处理数值列 - 只对存在的列进行操作
                numeric_cols = ['龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜总成交额']
                for col in numeric_cols:
                    if col in df.columns:
                        agg_funcs[col] = 'sum'

                # 执行聚合
                grouped = df.groupby('代码', as_index=False).agg(agg_funcs)
                grouped = grouped.rename(columns={'上榜日': '最近上榜日'})

                # 合并上榜次数
                grouped = pd.merge(grouped, count_df, on='代码', how='left')

                # 按上榜次数降序排序
                grouped = grouped.sort_values(by='上榜次数', ascending=False)

                # ------------------- 4. 填充表格 -------------------
                columns = ["代码", "名称", "最近上榜日", "上榜次数", "龙虎榜净买额", "龙虎榜买入额", "龙虎榜卖出额",
                           "龙虎榜总成交额"]
                self.stat_tb.setColumnCount(len(columns))
                self.stat_tb.setHorizontalHeaderLabels(columns)

                self.stat_tb.setRowCount(len(grouped))

                for row_idx in range(len(grouped)):
                    row_data = grouped.iloc[row_idx]
                    self.stat_tb.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row_data['代码'])))
                    self.stat_tb.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row_data['名称'])))
                    self.stat_tb.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(row_data['最近上榜日'])))
                    self.stat_tb.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(int(row_data['上榜次数']))))

                    # 数值列 (保留两位小数)
                    for col_name, col_idx in zip(['龙虎榜净买额', '龙虎榜买入额', '龙虎榜卖出额', '龙虎榜总成交额'],
                                                 [4, 5, 6, 7]):
                        val = row_data.get(col_name, 0)
                        self.stat_tb.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(f"{val:.2f}"))

                # 设置固定列宽
                widths = [70, 70, 85, 60, 90, 90, 90, 90]
                for col_idx, width in enumerate(widths):
                    self.stat_tb.setColumnWidth(col_idx, width)

                print(f"✅ 统计完成: 共加载 {len(grouped)} 条统计数据")
                self.centralwidget.window().statusBar().showMessage(f"统计完成: 共 {len(grouped)} 个股票", 3000)
            else:
                self.stat_tb.setRowCount(0)
                print("⚠️ 筛选后无数据")
                self.centralwidget.window().statusBar().showMessage("筛选后无数据", 3000)

        except Exception as e:
            print(f"❌ 统计数据出错: {e}")
            import traceback
            traceback.print_exc()
            # 设置错误显示
            self.stat_tb.setColumnCount(1)
            self.stat_tb.setHorizontalHeaderLabels(["错误"])
            self.stat_tb.setRowCount(1)
            self.stat_tb.setItem(0, 0, QtWidgets.QTableWidgetItem(f"统计出错: {str(e)}"))

    # =======================================================

    def on_list_tb_clicked(self, item):
        """当点击 list_tb 的某一行时触发，加载对应的 detail_tb 数据"""
        row = item.row()

        # 查找"代码"、"名称"、"上榜日"以及金额列所在的列索引
        code_col_idx = -1
        name_col_idx = -1
        date_col_idx = -1
        buy_col_idx = -1
        sell_col_idx = -1
        net_col_idx = -1

        for col in range(self.list_tb.columnCount()):
            header_text = self.list_tb.horizontalHeaderItem(col).text()
            if header_text == "代码":
                code_col_idx = col
            elif header_text == "名称":
                name_col_idx = col
            elif header_text == "上榜日":
                date_col_idx = col
            elif header_text == "买入额":
                buy_col_idx = col
            elif header_text == "卖出额":
                sell_col_idx = col
            elif header_text == "净买额":
                net_col_idx = col

        if code_col_idx != -1 and date_col_idx != -1:
            stock_code = self.list_tb.item(row, code_col_idx).text()

            # 获取股票名称
            stock_name = ""
            if name_col_idx != -1:
                stock_name = self.list_tb.item(row, name_col_idx).text()

            # 从显示的字符串中截取日期部分 (可能是 YYYY-MM-DD HH:MM:SS)
            date_str_full = self.list_tb.item(row, date_col_idx).text()
            date_str = date_str_full.split(' ')[0]

            # ================= 新增：获取龙虎榜金额数据 =================
            buy_amount = ""
            sell_amount = ""
            net_amount = ""

            if buy_col_idx != -1:
                buy_amount = self.list_tb.item(row, buy_col_idx).text()
            if sell_col_idx != -1:
                sell_amount = self.list_tb.item(row, sell_col_idx).text()
            if net_col_idx != -1:
                net_amount = self.list_tb.item(row, net_col_idx).text()
            # =========================================================

            print(f"用户点击了: 代码={stock_code}, 名称={stock_name}, 日期={date_str}")
            print(f"龙虎榜数据: 买入={buy_amount}, 卖出={sell_amount}, 净买={net_amount}")

            # ================= 新增：保存当前详情信息 =================
            self.current_detail_info = {
                'code': stock_code,
                'name': stock_name,
                'date': date_str,
                'buy_amount': buy_amount,
                'sell_amount': sell_amount,
                'net_amount': net_amount
            }
            # =======================================================

            # 调用加载详情表的方法，传入 stock_name 和龙虎榜数据
            self.load_detail_table_from_csv(stock_code, date_str, stock_name, buy_amount, sell_amount, net_amount)
        else:
            print("错误: 无法在表格中找到 '代码'、'名称' 或 '上榜日' 列")

    def load_detail_table_from_csv(self, stock_code, date_str, stock_name="", buy_amount="", sell_amount="",
                                   net_amount=""):
        """根据代码、日期和名称，从 lhb_detail_b.csv 加载数据到 detail_tb (仅显示明细，不显示合计)"""
        csv_path = 'data/lhb_detail_b.csv'

        if not os.path.exists(csv_path):
            print(f"警告: 未找到详情文件 {csv_path}")
            self.detail_tb.setRowCount(1)
            self.detail_tb.setColumnCount(1)
            self.detail_tb.setHorizontalHeaderLabels(["提示"])
            self.detail_tb.setItem(0, 0, QTableWidgetItem("未找到详情数据文件"))
            # 重置标题
            self.lbl_detail_title.setText("个股详情")
            self.lbl_detail_title.setStyleSheet("font-weight: bold; font-size: 14px; color: black;")
            return

        try:
            # ================= 新增：读取别名和大类映射表 =================
            category_map, alias_map = self.get_yyb_maps()
            # ====================================================

            df_detail = pd.read_csv(csv_path, encoding='utf-8-sig')

            # 数据类型转换
            df_detail['代码'] = df_detail['代码'].astype(str)
            df_detail['上榜日'] = df_detail['上榜日'].astype(str)

            # 匹配逻辑
            mask = (df_detail['代码'] == stock_code) & (df_detail['上榜日'] == date_str)
            df_filtered = df_detail[mask]

            # 如果没匹配到，尝试处理 date_str 移除横杠的情况
            if len(df_filtered) == 0 and '-' in date_str:
                formatted_date = date_str.replace('-', '')
                mask = (df_detail['代码'] == stock_code) & (df_detail['上榜日'] == formatted_date)
                df_filtered = df_detail[mask]

            # ================= 更新标题 (新增名称和龙虎榜金额) =================
            formatted_code = stock_code.zfill(6)
            # 构建标题，包含龙虎榜买入额、卖出额、净买额
            title_text = (f"详情 {date_str} 代码{formatted_code} {stock_name}, "
                          f"买入: {buy_amount}亿, 卖出: {sell_amount}亿, 净买额: {net_amount}亿")
            self.lbl_detail_title.setText(title_text)
            # 设置样式：红色，12号字，加粗
            self.lbl_detail_title.setStyleSheet("""
                QLabel {
                    color: red;
                    font-size: 12pt;
                    font-weight: bold;
                }
            """)
            # ==================================================================

            if len(df_filtered) == 0:
                print(f"未找到代码 {stock_code} 在日期 {date_str} 的详情数据")
                self.detail_tb.setRowCount(0)
                return

            # ... 后面的代码保持不变 ...
            # 清洗列名
            df_filtered.columns = df_filtered.columns.str.strip()

            # ================= 新增：排序逻辑 =================
            # 定义 flag 的排序顺序：买入在前 (0)，卖出在后 (1)
            flag_order = {'买入': 0, '卖出': 1}
            # 将 flag 转换为可排序的数值，不存在的设为 2 (最后)
            df_filtered['flag_sort_key'] = df_filtered['flag'].map(flag_order).fillna(2)
            # 将 '序号' 转换为数值
            df_filtered['序号_num'] = pd.to_numeric(df_filtered['序号'], errors='coerce').fillna(0)
            # 按照先 flag 顺序 (升序: 0->买入, 1->卖出)，再序号大小升序排序
            df_filtered = df_filtered.sort_values(by=['flag_sort_key', '序号_num'], ascending=[True, True])
            # 移除临时列
            df_filtered = df_filtered.drop(columns=['flag_sort_key', '序号_num'])
            # ================================================

            # ... 后面的代码（填充表格部分）保持不变 ...

            # ================= 定义列顺序和宽度 (修改：增加大类列) =================
            # 格式：(列名, 宽度)
            column_config = [
                ('flag',60),  # 操作标识
                ('序号', 60),  # 序号
                ('交易营业部名称', 200),  # 营业部名称
                ('大类', 100),  # 营业部大类 (新增)
                ('别名', 100),  # 营业部别名
                ('买入金额(亿)', 90),  # 买入金额
                ('买入占比', 80),  # 买入占比
                ('卖出金额(亿)',90),  # 卖出金额
                ('卖出占比', 80),
                ('净额(亿)', 80),  # 净额
                ('类型', 200)  # 类型
            ]

            # ================= 准备显示列 (修改逻辑：强制包含大类和别名) =================
            display_columns = []
            column_widths = []

            for col_name, col_width in column_config:
                # 如果是 '大类' 或 '别名'，强制添加到显示列表中
                if col_name in ['大类', '别名']:
                    display_columns.append(col_name)
                    column_widths.append(col_width)
                # 其他列检查是否存在于 DataFrame 中
                elif col_name in df_filtered.columns:
                    display_columns.append(col_name)
                    column_widths.append(col_width)

            # 如果没有找到任何指定的列（极少情况），则显示所有列
            if not display_columns:
                columns_to_hide = ["上榜日", "代码"]
                display_columns = [col for col in df_filtered.columns if col not in columns_to_hide]
                column_widths = [100] * len(display_columns)
                print("⚠️ 未找到预定义的列，显示所有可用列")

            self.detail_tb.setColumnCount(len(display_columns))
            self.detail_tb.setHorizontalHeaderLabels(display_columns)

            # ================= 设置每列的宽度 =================
            for col_idx, col_width in enumerate(column_widths):
                self.detail_tb.setColumnWidth(col_idx, col_width)

            # ================= 填充表格 =================
            # 直接设置行数为数据长度
            self.detail_tb.setRowCount(len(df_filtered))

            for row_idx in range(len(df_filtered)):
                # 获取当前行的 flag (买入/卖出)
                flag_val = str(df_filtered.iloc[row_idx].get('flag', '')).strip()
                is_sell_row = (flag_val == "卖出")

                for col_idx, col_name in enumerate(display_columns):
                    val = None

                    # 【关键修改】判断列是否在 CSV 中
                    if col_name == '大类':
                        # ========== 从大类映射表中读取大类 ==========
                        # 需要用缩写名称匹配
                        yyb_full_name = df_filtered.iloc[row_idx].get('交易营业部名称', '')

                        val = category_map.get(yyb_full_name, "")
                        # ========================================
                    elif col_name == '别名':
                        # ========== 从别名映射表中读取别名 ==========
                        # 需要用缩写名称匹配
                        yyb_full_name = df_filtered.iloc[row_idx].get('交易营业部名称', '')

                        val = alias_map.get(yyb_full_name, "")
                        # ========================================
                    elif col_name == '交易营业部名称':
                        # ========== 显示缩写名称 ==========
                        val = df_filtered.iloc[row_idx].get('交易营业部名称', '')
                        # ==================
                    elif col_name in df_filtered.columns:
                        val = df_filtered.iloc[row_idx][col_name]
                    else:
                        val = ""

                    # 数值处理
                    if pd.isna(val):
                        display_val = ""
                    elif isinstance(val, (int, float)):
                        display_val = f"{val:.2f}"
                    else:
                        display_val = str(val)

                    # 创建单元格项
                    item = QTableWidgetItem(display_val)

                    # ================= 样式逻辑 =================

                    # 1. 卖出的所有行背景为灰色
                    if is_sell_row:
                        item.setBackground(QtGui.QColor("#e0e0e0"))

                    # 2. Flag 列颜色：买入红色，卖出绿色
                    if col_name == "flag":
                        if flag_val == "买入":
                            item.setForeground(QtGui.QColor("red"))
                        elif flag_val == "卖出":
                            item.setForeground(QtGui.QColor("green"))

                    # 3. 卖出金额列：所有行的值都加负号
                    if "卖出金额" in col_name and isinstance(val, (int, float)):
                        item.setText(f"{-abs(val):.2f}")

                    # ================= 新增：金额列颜色逻辑 =================
                    # 买入金额列用红色字
                    if col_name == '买入金额(亿)':
                        if isinstance(val, (int, float)) and val != 0:
                            item.setForeground(QtGui.QColor("red"))
                    # 卖出金额列用绿色字
                    elif col_name == '卖出金额(亿)':
                        if isinstance(val, (int, float)) and val != 0:
                            item.setForeground(QtGui.QColor("green"))
                    # ======================================================

                    # 4. 净额整列：正数红色，负数绿色
                    if "净额" in col_name and isinstance(val, (int, float)):
                        if val > 0:
                            item.setForeground(QtGui.QColor("red"))
                        elif val < 0:
                            item.setForeground(QtGui.QColor("green"))

                    self.detail_tb.setItem(row_idx, col_idx, item)

            print(f"成功加载 {len(df_filtered)} 条详情数据 (含强制插入的大类和别名列)")

        except Exception as e:
            print(f"读取详情 CSV 出错: {e}")
            import traceback
            traceback.print_exc()

    def load_yyb_stat_to_table(self, filters=None):
        """
        调用 yyb_stat() 函数获取统计数据，并填充到 self.yyb_tb 表格中
        """
        # 1. 调用外部定义的 yyb_stat 函数，并传入筛选条件
        df = yyb_stat(filters)

        # 2. 检查返回结果是否有效
        if df is None or df.empty:
            print("⚠️ 营业部统计数据为空或获取失败")
            self.yyb_tb.setRowCount(0)
            return

        # ===== 新增：打印调试信息 =====
        print(f"📊 yyb_stat 返回的数据形状: {df.shape}")
        print(f"📊 yyb_stat 返回的列名: {df.columns.tolist()}")
        print(f"📊 '上榜日' 列的数据类型: {df['上榜日'].dtype}")
        print(f"📊 '上榜日' 列的前 3 个值: {df['上榜日'].head(3).tolist()}")
        print(f"📊 '上榜日' 列是否包含 NaT: {df['上榜日'].isna().any()}")
        # =============================
        # 格式：(列名, 宽度)
        column_config = [
            ('上榜日', 100),  # 操作标识
            ('交易营业部名称', 200),  # 序号

            ('大类', 75),  # 营业部大类 (新增)
            ('别名', 75),  # 营业部别名
            ('上榜次数', 80),  # 买入金额
            ('买入个股数', 80),  # 买入占比
            ('买入总金额', 90),
            ('卖出个股数', 80),  # 卖出金额

            ('卖出总金额', 90), # 净额

        ]

        # ================= 新增：读取别名和大类映射表 =================
        category_map, alias_map = self.get_yyb_maps()
        # ====================================================

        # ===== 新增：在填充前按"上榜次数"降序排序 =====
        if '上榜次数' in df.columns:
            df = df.sort_values(by='上榜次数', ascending=False)
            print(f"✅ 已按'上榜次数'降序排序")
        # ===========================================

        # 3. 设置表格行数
        self.yyb_tb.setRowCount(len(df))

        # 4. 遍历 DataFrame 并填充表格
        for row in range(len(df)):


            data = df.iloc[row]

            # ===== 修改点：改进日期处理逻辑 =====
            date_val = data['上榜日']
            date_str = ""  # 默认值

            if pd.isna(date_val):
                # 处理 NaT 的情况
                print(f"⚠️ 第 {row} 行的日期为 NaT")
                date_str = "无效日期"
            elif isinstance(date_val, str):
                # 字符串类型，尝试转换
                try:
                    dt = pd.to_datetime(date_val)
                    date_str = dt.strftime('%Y-%m-%d')
                except Exception as e:
                    print(f"⚠️ 第 {row} 行的日期转换失败: {e}, 原始值: {date_val}")
                    date_str = str(date_val)
            elif hasattr(date_val, 'strftime'):
                # datetime 对象或 Timestamp 对象
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                # 其他类型，直接转为字符串
                date_str = str(date_val)

            # 设置日期单元格
            self.yyb_tb.setItem(row, 0, QtWidgets.QTableWidgetItem(date_str))
            # ==================================

            yyb_full_name = str(data['交易营业部名称'])
            # ========== 显示缩写名称 ==========

            self.yyb_tb.setItem(row, 1, QtWidgets.QTableWidgetItem(yyb_full_name))
            # ==
            # ========== 修改：从映射表填充大类和别名（使用缩写名称匹配）==========
            # 列索引 2: 大类
            category = category_map.get(yyb_full_name, "")
            self.yyb_tb.setItem(row, 2, QtWidgets.QTableWidgetItem(category))

            # 列索引 3: 别名
            alias = alias_map.get(yyb_full_name, "")
            self.yyb_tb.setItem(row, 3, QtWidgets.QTableWidgetItem(alias))
            # =================================================

            count = data['上榜次数']
            self.yyb_tb.setItem(row, 4, QtWidgets.QTableWidgetItem(str(int(count)) if pd.notna(count) else "0"))

            buy_count = data['买入个股数']
            self.yyb_tb.setItem(row, 5, QtWidgets.QTableWidgetItem(str(int(buy_count)) if pd.notna(buy_count) else "0"))

            sell_count = data['卖出个股数']
            self.yyb_tb.setItem(row, 6,
                                QtWidgets.QTableWidgetItem(str(int(sell_count)) if pd.notna(sell_count) else "0"))

            buy_amt = data['买入总金额']
            self.yyb_tb.setItem(row, 7, QtWidgets.QTableWidgetItem(f"{buy_amt:.2f}" if pd.notna(buy_amt) else "0.00"))

            sell_amt = data['卖出总金额']
            self.yyb_tb.setItem(row, 8, QtWidgets.QTableWidgetItem(f"{sell_amt:.2f}" if pd.notna(sell_amt) else "0.00"))



        self.yyb_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

        for col_idx, (col_name, width) in enumerate(column_config):
            self.yyb_tb.setColumnWidth(col_idx, width)
        # =========================

        print(f"✅ 已将 yyb_stat 统计结果填充到 yyb_tb，共 {len(df)} 条记录")

    def init_sample_data(self):
        """初始化数据：默认加载当天数据"""
        default_filters = {
            'stock_types': ['全部'],
            'stock_input': '',
            'date_mode': '当天',
            'start_date': '',
            'end_date': '',
            'yyb_category': '全部',  # 新增
            'yyb_name': '',
            'yyb_alias': '' # 新增
        }
        self.load_list_tb_from_csv(default_filters)
        self.load_yyb_stat_to_table(default_filters)
        # self.load_yyb_stat_to_table()

        # ================= 填充 yyb_tb (营业部统计) =================
        # self.yyb_tb.setRowCount(5)
        # # 设置列数和表头（确保与 setupUi 一致）
        # self.yyb_tb.setColumnCount(8)
        # self.yyb_tb.setHorizontalHeaderLabels([
        #     "上榜日",
        #     "交易营业部名称",
        #     "别名",
        #
        #     "上榜次数",
        #     "买入个股数",
        #     "卖出个股",
        #     "买入总金额",
        #     "卖出总金额"
        # ])
        #
        # for i in range(7):
        #     self.yyb_tb.setItem(i, 0, QTableWidgetItem(f"中信证券股份有限公司上海淮海中路证券营业部{i}"))
        #     self.yyb_tb.setItem(i, 1, QTableWidgetItem(f"2023-12-{10 + i:02d}"))  # 上榜日
        #     self.yyb_tb.setItem(i, 2, QTableWidgetItem(f"{10 - i}"))  # 上榜次数
        #     self.yyb_tb.setItem(i, 3, QTableWidgetItem(f"{5 + i}"))  # 买入个股数
        #     self.yyb_tb.setItem(i, 4, QTableWidgetItem(f"{3 + i}"))  # 卖出个股
        #     self.yyb_tb.setItem(i, 5, QTableWidgetItem(f"{i * 5000}"))  # 买入总金额
        #     self.yyb_tb.setItem(i, 6, QTableWidgetItem(f"{i * 4000}"))  # 卖出总金额
        #     self.yyb_tb.setItem(i, 7, QTableWidgetItem(f"{i * 4000}"))  # 卖出总金额

        # ================= 填充 detail_tb (个股详情) =================
        self.detail_tb.setRowCount(1)
        self.detail_tb.setColumnCount(1)
        self.detail_tb.setItem(0, 0, QTableWidgetItem("请点击上方龙虎榜列表查看详情"))

        # ================= 填充 yyb_st_tb (营业部持仓) =================
        self.yyb_st_tb.setRowCount(5)
        # 设置列数和表头（确保与 setupUi 一致）
        self.yyb_st_tb.setColumnCount(7)
        self.yyb_st_tb.setHorizontalHeaderLabels([
            "上榜日",
            "代码",
            "名称",
            "涨跌幅",
            "flag",
            "买入金额(亿)",
            "卖出金额(亿)"
        ])

        for i in range(6):
            self.yyb_st_tb.setItem(i, 0, QTableWidgetItem(""))  # 上榜日
            self.yyb_st_tb.setItem(i, 1, QTableWidgetItem(f""))  # 代码
            self.yyb_st_tb.setItem(i, 2, QTableWidgetItem(f""))  # 名称
            self.yyb_st_tb.setItem(i, 3, QTableWidgetItem(""))  # flag
            self.yyb_st_tb.setItem(i, 4, QTableWidgetItem(f""))  # 买入金额(亿)
            self.yyb_st_tb.setItem(i, 5, QTableWidgetItem(f""))  # 卖出金额(亿)
            self.yyb_st_tb.setItem(i, 6, QTableWidgetItem(f""))  # 卖出金额(亿)

    # ================= 查询点击事件 =================
    def on_query_clicked(self):
        """处理查询按钮点击，收集筛选条件并重新加载数据"""
        stock_types = [btn.text() for btn in self.stock_btn_group.buttons() if btn.isChecked()]

        # 2. 获取日期模式
        date_mode = "当天"
        for btn in self.date_btns:
            if btn.isChecked():
                date_mode = btn.text()
                break

        # 新增：打印调试信息
        print(f"🔍 on_query_clicked 确定的 date_mode: '{date_mode}'")

        # 3. 获取日期范围（如果是自定义）
        start_date_str = self.date_start.date().toString("yyyy-MM-dd")
        end_date_str = self.date_end.date().toString("yyyy-MM-dd")

        # 4. 获取个股输入
        stock_input = self.input_stock.text()

        # 5. 获取营业部范围
        yyb_category = self.combo_yyb.currentText()  # 新增：获取下拉框选中的大类
        yyb_name = self.input_yyb_name.text()
        # 安全获取当前别名
        if hasattr(self, '_current_selected_alias'):
            current_alias = self._current_selected_alias
        else:
            current_alias = ""
        # ============================

        # 保存当前选择
        self.selected_category = yyb_category

        print(f"🔍 营业部范围 - 大类: '{yyb_category}', 名称: '{yyb_name}'")

        # 构建筛选字典
        filters = {
            'stock_types': stock_types,
            'stock_input': stock_input,
            'date_mode': date_mode,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'yyb_category': yyb_category,  # 新增
            'yyb_name': yyb_name, # 新增
            'yyb_alias': current_alias
        }

        # ================= 新增：保存当前筛选条件 =================
        self.current_filters = filters
        # =======================================================

        # 显示状态
        self.centralwidget.window().statusBar().showMessage("正在查询...", 0)

        # 执行加载
        self.load_list_tb_from_csv(filters)

        # 【新增点】联动查询营业部统计表
        self.load_yyb_stat_to_table(filters)

        self.list_tb.show()
        self.stat_tb.hide()
        # ===== 新增：查询完成后清空个股代码输入框 =====
        self.input_stock.clear()
        try:
            # 读取完整数据用于 yyb_st_tb 筛选
            print("🔄 正在更新内存中的详情数据缓存...")
            self.lhb_detail_b_df = pd.read_csv('data/lhb_detail_b.csv', encoding='utf-8-sig', header=0)
            # 简单的数据清洗，确保日期列正确
            if '上榜日' in self.lhb_detail_b_df.columns:
                self.lhb_detail_b_df['上榜日'] = pd.to_datetime(self.lhb_detail_b_df['上榜日'], errors='coerce')
            print(f"✅ 已更新内存中的详情数据缓存，共 {len(self.lhb_detail_b_df)} 行")
        except Exception as e:
            print(f"❌ 缓存数据加载失败: {e}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    ui = MainWindow()
    ui.setupUi(window)
    window.show()
    sys.exit(app.exec_())
    # yyb_stat()
