# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import numpy as np
import sys
import os
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QHeaderView, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QCheckBox, QScrollArea, \
    QWidget

# 【新增】导入 data_update 模块
from data_update import update
import json
# 新增：导入matplotlib图表库
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib import rcParams
from link_tdx import link_tdx


# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False



class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1750, 1200)

        icon = QtGui.QIcon()
        try:
            icon.addPixmap(QtGui.QPixmap("app4.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        except:
            print("未找到app4.ico图标，不影响窗口功能")
        MainWindow.setWindowIcon(icon)

        self.scrollArea = QtWidgets.QScrollArea(MainWindow)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")

        self.centralwidget = QtWidgets.QWidget()
        self.centralwidget.setObjectName("centralwidget")

        self.scrollArea.setWidget(self.centralwidget)
        MainWindow.setCentralWidget(self.scrollArea)

        main_layout = QVBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- Banner ---
        self.banner = QtWidgets.QLabel(self.centralwidget)
        self.banner.setFixedHeight(60)
        font = QtGui.QFont()
        font.setFamily("迷你简汉真广标")
        font.setPointSize(20)
        font.setBold(False)
        font.setWeight(50)
        font.setKerning(False)
        self.banner.setFont(font)
        self.banner.setStyleSheet("color: white;\nbackground-color: rgb(0, 170,255);")
        self.banner.setAlignment(QtCore.Qt.AlignCenter)
        self.banner.setObjectName("banner")
        main_layout.addWidget(self.banner)

        # --- Widget (输入框和按钮区域) ---
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setObjectName("widget")

        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")

        # ================= 快速选择按钮 =================
        self.btn_1_week = QtWidgets.QPushButton(self.widget)
        self.btn_1_week.setObjectName("btn_1_week")

        self.btn_2_weeks = QtWidgets.QPushButton(self.widget)
        self.btn_2_weeks.setObjectName("btn_2_weeks")

        self.btn_1_month = QtWidgets.QPushButton(self.widget)
        self.btn_1_month.setObjectName("btn_1_month")

        self.btn_3_months = QtWidgets.QPushButton(self.widget)
        self.btn_3_months.setObjectName("btn_3_months")

        self.horizontalLayout.addWidget(self.btn_1_week)
        self.horizontalLayout.addWidget(self.btn_2_weeks)
        self.horizontalLayout.addWidget(self.btn_1_month)
        self.horizontalLayout.addWidget(self.btn_3_months)

        spacer_quick = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacer_quick)
        # ================= 快速选择按钮结束 =================

        # ================= 日期范围分析相关控件 =================
        self.start_date_label = QtWidgets.QLabel(self.widget)
        font_label = QtGui.QFont()
        font_label.setFamily("SimHei")
        font_label.setPointSize(12)
        self.start_date_label.setFont(font_label)
        self.start_date_label.setObjectName("start_date_label")

        self.start_date_input = QtWidgets.QLineEdit(self.widget)
        self.start_date_input.setText("2025-01-02")
        self.start_date_input.setFixedWidth(100)
        self.start_date_input.setObjectName("start_date_input")

        self.end_date_label = QtWidgets.QLabel(self.widget)
        self.end_date_label.setFont(font_label)
        self.end_date_label.setObjectName("end_date_label")

        self.end_date_input = QtWidgets.QLineEdit(self.widget)
        self.end_date_input.setText("2025-01-02")
        self.end_date_input.setFixedWidth(100)
        self.end_date_input.setObjectName("end_date_input")

        self.analyze_btn = QtWidgets.QPushButton(self.widget)
        self.analyze_btn.setObjectName("analyze_btn")

        # ================= 合并：数据更新按钮（包含更新所属概念） =================
        self.update_data_btn = QtWidgets.QPushButton(self.widget)
        self.update_data_btn.setObjectName("update_data_btn")

        self.horizontalLayout.addWidget(self.start_date_label)
        self.horizontalLayout.addWidget(self.start_date_input)
        self.horizontalLayout.addWidget(self.end_date_label)
        self.horizontalLayout.addWidget(self.end_date_input)
        self.horizontalLayout.addWidget(self.analyze_btn)
        self.horizontalLayout.addWidget(self.update_data_btn)

        separator_line = QtWidgets.QFrame(self.widget)
        separator_line.setFrameShape(QtWidgets.QFrame.VLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.horizontalLayout.addWidget(separator_line)
        # ================= 控件添加结束 =================

        # ================= 更新信息显示区 =================
        self.update_info_label = QtWidgets.QLabel(self.widget)
        self.update_info_label.setObjectName("update_info_label")
        self.update_info_label.setStyleSheet(
            "color: #0066cc; "
            "font-weight: bold; "
            "padding: 5px; "
            "background-color: #e6f2ff; "
            "border-radius: 3px; "
            "border: 1px solid #b3d4fc;"
        )
        self.horizontalLayout.addWidget(self.update_info_label)
        # ================= 信息显示区结束 =================

        main_layout.addWidget(self.widget)

        # ================= 图表和表格的水平布局 =================
        charts_and_tables_widget = QtWidgets.QWidget(self.centralwidget)
        charts_layout = QHBoxLayout(charts_and_tables_widget)
        charts_layout.setSpacing(10)

        # 左侧：板块表格
        self.blk_tb = QtWidgets.QTableWidget(self.centralwidget)
        self.blk_tb.setObjectName("blk_tb")
        self.blk_tb.setColumnCount(3)  # 日期，板块名称，概念重复次数
        self.blk_tb.setRowCount(0)
        self.blk_tb.setMinimumHeight(500)
        self.blk_tb.setMaximumWidth(400)  # 限制表格宽度

        for i in range(3):
            item = QtWidgets.QTableWidgetItem()
            self.blk_tb.setHorizontalHeaderItem(i, item)

        # 中间：图表区
        self.chart_widget = QtWidgets.QWidget()
        chart_layout = QVBoxLayout(self.chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(5)

        # 创建matplotlib图表
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)

        # 【新增】复选框控制区
        self.chk_container = QWidget()
        self.chk_layout = QHBoxLayout(self.chk_container)
        self.chk_layout.setContentsMargins(0, 0, 0, 0)
        self.chk_container.setMaximumHeight(40)  # 限制高度
        chart_layout.addWidget(self.chk_container)

        # 添加布局
        charts_layout.addWidget(self.blk_tb)
        charts_layout.addWidget(self.chart_widget, stretch=1)

        main_layout.addWidget(charts_and_tables_widget)
        # ================= 布局添加结束 =================

        # ================= Top5代码信息显示区 =================
        self.top_stocks_info = QtWidgets.QLabel(self.centralwidget)
        self.top_stocks_info.setObjectName("top_stocks_info")
        self.top_stocks_info.setWordWrap(True)  # 允许文字自动换行
        self.top_stocks_info.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.top_stocks_info.setStyleSheet(
            "background-color: #f5f5f5; "
            "color: #333333; "
            "font-size: 13px; "
            "font-weight: bold; "
            "padding: 8px; "
            "border-radius: 5px; "
            "border: 1px solid #dcdcdc;"
        )
        main_layout.addWidget(self.top_stocks_info)
        # ================= Top5信息显示区结束 =================

        self.stock_tb = QtWidgets.QTableWidget(self.centralwidget)
        self.stock_tb.setObjectName("stock_tb")
        self.stock_tb.setColumnCount(3)  # 默认只显示3列：日期、代码、名称
        self.stock_tb.setRowCount(0)
        self.stock_tb.setMinimumHeight(500)

        for i in range(3):
            item = QtWidgets.QTableWidgetItem()
            self.stock_tb.setHorizontalHeaderItem(i, item)

        self.stock_tb.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)

        main_layout.addWidget(self.stock_tb)

        main_layout.addStretch()

        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1720, 23))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def init_tables(self):
        font = QtGui.QFont()
        font.setPointSize(12)
        self.stock_tb.setFont(font)
        self.blk_tb.setFont(font)

        self.blk_tb.setColumnCount(3)
        self.blk_tb.setHorizontalHeaderLabels(
            ["日期", "板块名称", "概念重复次数"]
        )
        blk_column_widths = [100, 80, 60]
        for col, width in enumerate(blk_column_widths):
            self.blk_tb.setColumnWidth(col, width)
        self.blk_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

        # 默认只设置3列（多日统计模式）
        self.stock_tb.setColumnCount(3)
        self.stock_tb.setHorizontalHeaderLabels(
            ["日期", "代码", "名称"]
        )
        stock_column_widths = [100, 80, 60]
        for col, width in enumerate(stock_column_widths):
            self.stock_tb.setColumnWidth(col, width)
        self.stock_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

    def set_stock_tb_full_columns(self):
        """设置为完整列模式（单日统计）"""
        self.stock_tb.setColumnCount(50)
        headers = ["日期", "代码", "名称"]
        for i in range(1, 47):
            headers.append(f'概念{i}')
        headers.append("其他")
        self.stock_tb.setHorizontalHeaderLabels(headers)

        for col in range(self.stock_tb.columnCount()):
            self.stock_tb.setColumnWidth(col, 75)

        self.stock_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

    def set_stock_tb_simple_columns(self):
        """设置为简单列模式（多日统计）"""
        self.stock_tb.setColumnCount(3)
        self.stock_tb.setHorizontalHeaderLabels(
            ["日期", "代码", "名称"]
        )
        stock_column_widths = [100, 80, 80]
        for col, width in enumerate(stock_column_widths):
            self.stock_tb.setColumnWidth(col, width)
        self.stock_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "涨停板分析"))
        self.banner.setText(_translate("MainWindow", "涨停板分析，反向得出板块热度！"))
        self.btn_1_week.setText(_translate("MainWindow", "近1周"))
        self.btn_2_weeks.setText(_translate("MainWindow", "近2周"))
        self.btn_1_month.setText(_translate("MainWindow", "近1月"))
        self.btn_3_months.setText(_translate("MainWindow", "近3月"))
        self.start_date_label.setText(_translate("MainWindow", "开始日期:"))
        self.end_date_label.setText(_translate("MainWindow", "结束日期:"))
        self.analyze_btn.setText(_translate("MainWindow", "分析涨停"))
        self.update_data_btn.setText(_translate("MainWindow", "数据更新"))
        self.update_info_label.setText(_translate("MainWindow", "⏳ 等待更新..."))
        self.top_stocks_info.setText(_translate("MainWindow", "📊 期间内最活跃代码 Top 5: 暂无数据"))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.init_tables()
        self.df_stocks = None
        self.exclude_words = set()
        self.yes_words = set()
        self.blkfile_path = ""

        # # 实例化 zt_data 类
        # self.zt_data_inst = zt_data()

        # 事件ID用于注销
        self.mpl_cid = None

        self.load_resources()

        # 绑定按钮
        self.analyze_btn.clicked.connect(self.on_analyze_date_clicked)
        self.update_data_btn.clicked.connect(self.on_update_data_clicked)

        # 绑定快速选择按钮
        self.btn_1_week.clicked.connect(lambda: self.set_date_range(days=7))
        self.btn_2_weeks.clicked.connect(lambda: self.set_date_range(days=14))
        self.btn_1_month.clicked.connect(lambda: self.set_date_range(days=30))
        self.btn_3_months.clicked.connect(lambda: self.set_date_range(days=90))

        self.stock_tb.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.stock_tb.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.stock_tb.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.stock_tb.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

        self.stock_tb.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.stock_tb.cellClicked.connect(self.on_stock_cell_clicked)
        self.set_date_range(days=14)

    def set_date_range(self, days):
        """快速选择日期范围并触发分析"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        self.end_date_input.setText(end_date.strftime('%Y-%m-%d'))
        self.start_date_input.setText(start_date.strftime('%Y-%m-%d'))

        # 自动触发分析
        self.on_analyze_date_clicked()

    def on_stock_cell_clicked(self, row, column):
        """点击表格单元格时联接到通达信"""
        # 判断是否点击的是代码列（第1列，索引从0开始）
        if column == 1:
            item = self.stock_tb.item(row, column)
            if item:
                code = item.text().strip()
                if code:
                    link_tdx(code)

    def load_resources(self):
        file_path = 'data/stock_gn.csv'
        if os.path.exists(file_path):
            try:
                self.df_stocks = pd.read_csv(file_path, dtype=str, encoding='utf-8-sig')

                if '代码' in self.df_stocks.columns:
                    self.df_stocks['代码'] = self.df_stocks['代码'].astype(str).str.zfill(6)

                    # 检查概念列是否存在
                    concept_cols = [col for col in self.df_stocks.columns if col.startswith('概念')]
                    print(f"✅ 已加载 stock_gn.csv，包含 {len(self.df_stocks)} 只股票")
                    print(f"✅ 发现 {len(concept_cols)} 个概念列")

                    # 打印前几行示例
                    print(f"✅ 列名: {self.df_stocks.columns.tolist()[:10]}")
                else:
                    print(f"❌ stock_gn.csv 缺少'代码'列")
                    self.df_stocks = pd.DataFrame()

            except Exception as e:
                print(f"❌ 加载stock_gn.csv 失败: {e}")
                import traceback
                traceback.print_exc()
                self.df_stocks = pd.DataFrame()
        else:
            print(f"⚠️ stock_gn.csv 不存在: {file_path}")
            self.df_stocks = pd.DataFrame()

        # 其余代码保持不变
        try:
            if os.path.exists("set_key.txt"):
                with open("set_key.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                    self.exclude_words = set(word for word in content.split() if word.strip())
                    print(f"✅ 加载排除关键词: {len(self.exclude_words)} 个")
        except Exception as e:
            pass

        self.yes_words = set()
        self.blkfile_path = None
        try:
            if os.path.exists("setup.json"):
                with open("setup.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.yes_words = set(word for word in config.get('yesword', '').split() if word.strip())
                    self.blkfile_path = config.get('blkfile', '').strip()
                    print(f"✅ 加载必须包含词: {len(self.yes_words)} 个")
        except Exception as e:
            pass

    def on_update_data_clicked(self):
        """数据更新按钮：执行 data_update 中的 run 函数"""
        try:
            # 更新UI显示
            self.update_info_label.setText("🔄 正在执行全量数据更新，请稍候...")
            QtWidgets.QApplication.processEvents()

            # 【核心修改】调用 data_update 中的 run 方法
            updater = update()
            updater.run()

            # 更新完成后的处理
            self.load_resources()  # 重新加载概念数据到内存
            self.on_analyze_date_clicked()  # 刷新分析显示

            self.update_info_label.setText("✅ 全部数据更新完成")
            QtWidgets.QMessageBox.information(self, "完成", "全部数据更新完成！")

        except Exception as e:
            self.update_info_label.setText(f"❌ 更新失败: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "错误", f"更新失败: {e}")
            import traceback
            traceback.print_exc()

    def on_analyze_date_clicked(self):
        """分析涨停按钮：读取数据并显示，自动补充缺失的统计数据"""
        start_str = self.start_date_input.text().strip()
        end_str = self.end_date_input.text().strip()

        if not start_str or not end_str:
            QtWidgets.QMessageBox.warning(self, "提示", "请输入开始日期和结束日期")
            return

        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d')
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "错误", "日期格式不正确，请使用 YYYY-MM-DD")
            return

        stat_path = 'data/zt_stat.csv'
        list_path = 'data/zt_list.csv'

        if not os.path.exists(list_path):
            QtWidgets.QMessageBox.warning(self, "错误", f"源数据文件不存在 ({list_path})")
            return

        if not os.path.exists(stat_path):
            # 创建空的统计文件
            pd.DataFrame(columns=['日期', '板块名称', '概念重复次数']).to_csv(stat_path, index=False,
                                                                              encoding='utf-8-sig')

        try:
            is_single_day = (start_str == end_str)

            # 1. 读取涨停列表
            df_list = pd.read_csv(list_path, dtype={'代码': str})
            df_list['代码'] = df_list['代码'].astype(str).str.zfill(6)

            # 2. 读取统计数据
            df_stat = pd.read_csv(stat_path, dtype={'日期': str, '概念重复次数': int})

            # 3. 检查哪些日期缺少统计数据
            list_dates = set(df_list['日期'].unique())
            # 修复：检查 '日期' 列是否存在
            if not df_stat.empty and '日期' in df_stat.columns:
                stat_dates = set(df_stat['日期'].unique())
            else:
                stat_dates = set()
            missing_dates = list_dates - stat_dates

            # 4. 如果有缺失日期，自动补充统计
            if missing_dates:
                print(f"⚠️ 发现缺失统计的日期: {missing_dates}，正在自动补充...")
                missing_df = df_list[df_list['日期'].isin(missing_dates)]
                new_stat = self._calculate_stat_from_list(missing_df)
                if not new_stat.empty:
                    df_stat = pd.concat([df_stat, new_stat], ignore_index=True)
                    df_stat.to_csv(stat_path, index=False, encoding='utf-8-sig')
                    print(f"✅ 已补充 {len(missing_dates)} 个日期的统计数据")

            # 5. 筛选日期范围
            mask = (df_stat['日期'] >= start_str) & (df_stat['日期'] <= end_str)
            df_stat_filtered = df_stat.loc[mask]
            df_stat_filtered = df_stat_filtered.sort_values(['日期', '概念重复次数'], ascending=[True, False])

            # 6. 填充 blk_tb
            self.blk_tb.setRowCount(0)
            for _, row in df_stat_filtered.iterrows():
                r = self.blk_tb.rowCount()
                self.blk_tb.insertRow(r)
                self.blk_tb.setItem(r, 0, QtWidgets.QTableWidgetItem(str(row['日期'])))
                self.blk_tb.setItem(r, 1, QtWidgets.QTableWidgetItem(str(row['板块名称'])))
                self.blk_tb.setItem(r, 2, QtWidgets.QTableWidgetItem(str(row['概念重复次数'])))

            # 7. 筛选股票列表
            mask_list = (df_list['日期'] >= start_str) & (df_list['日期'] <= end_str)
            df_list_filtered = df_list.loc[mask_list]

            # 8. 显示Top5代码
            if not df_list_filtered.empty:
                top_5 = df_list_filtered['代码'].value_counts().head(5)
                top_items = []
                for code, count in top_5.items():
                    stock_info = df_list_filtered[df_list_filtered['代码'] == code].iloc[0]
                    name = stock_info['名称']
                    top_items.append(f"{code} {name}({count}次)")
                self.top_stocks_info.setText(f"📊 期间内最活跃代码 Top 5: {' '.join(top_items)}")
            else:
                self.top_stocks_info.setText("📊 期间内最活跃代码 Top 5: 暂无数据")

            # 9. 设置表格列模式
            if is_single_day:
                self.set_stock_tb_full_columns()
            else:
                self.set_stock_tb_simple_columns()

            self.stock_tb.setRowCount(0)
            for _, row in df_list_filtered.iterrows():
                if is_single_day:
                    self._add_stock_row_from_list(row)
                else:
                    self._add_stock_row_simple(row)

            # 10. 绘制图表
            if not is_single_day:
                self.plot_charts(df_stat_filtered, start_str, end_str)
            else:
                self.figure.clear()
                self.canvas.draw()

            QtWidgets.QMessageBox.information(self, "完成",
                                              f"分析完成！\n显示 {len(df_stat_filtered)} 条统计记录\n显示 {len(df_list_filtered)} 只股票")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"读取显示数据失败: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_stat_from_list(self, df_list):
        """从涨停列表计算板块统计数据"""
        if df_list.empty:
            return pd.DataFrame()

        # 加载概念数据
        if self.df_stocks is None or self.df_stocks.empty:
            print("⚠️ 概念数据未加载，无法计算板块统计")
            print("⚠️ 请检查 data/stock_gn.csv 文件是否存在且格式正确")
            return pd.DataFrame()

        results = []

        # 打印调试信息
        print(f"📊 需要统计的日期: {df_list['日期'].unique()}")
        print(f"📊 涨停股票数量: {len(df_list)}")
        print(f"📊 概念库股票数量: {len(self.df_stocks)}")

        for date in df_list['日期'].unique():
            df_day = df_list[df_list['日期'] == date]
            plate_counter = {}
            missing_codes = []

            print(f"📅 处理日期: {date}, 涨停股票数: {len(df_day)}")

            for _, row in df_day.iterrows():
                code = row['代码']
                stock_info = self.df_stocks[self.df_stocks['代码'] == code]

                if stock_info.empty:
                    missing_codes.append(code)
                    continue

                s_data = stock_info.iloc[0]

                # 统计所有概念
                concepts_found = []
                for i in range(1, 47):
                    col_name = f'概念{i}'
                    if col_name not in s_data.index:
                        continue

                    plate = s_data[col_name]

                    # 正确过滤空值
                    if pd.notna(plate):
                        plate_str = str(plate).strip()
                        if plate_str and plate_str.lower() != 'nan':
                            # 排除关键词
                            if plate_str not in self.exclude_words:
                                # 如果设置了必须包含词，则检查
                                if not self.yes_words or any(yw in plate_str for yw in self.yes_words):
                                    plate_counter[plate_str] = plate_counter.get(plate_str, 0) + 1
                                    concepts_found.append(plate_str)

            if missing_codes:
                print(f"  ⚠️ 未找到概念的代码({len(missing_codes)}个): {', '.join(missing_codes[:5])}...")

            print(f"  📊 日期 {date} 统计到 {len(plate_counter)} 个板块")

            # 按重复次数排序
            for plate, count in sorted(plate_counter.items(), key=lambda x: x[1], reverse=True):
                results.append({
                    '日期': date,
                    '板块名称': plate,
                    '概念重复次数': count
                })

        return pd.DataFrame(results)

    def toggle_line(self, label, checked):
        """复选框槽函数：控制折线的显示/隐藏"""
        # 遍历图表中的所有线条
        for line in self.ax.lines:
            # 跳过辅助线（如垂直线）
            if line.get_linestyle() == ':':
                continue
            if line.get_label() == label:
                line.set_visible(checked)
                break

        # 重绘
        self.canvas.draw_idle()

    def on_mouse_move(self, event):
        """鼠标移动事件：显示数据提示"""
        # 检查鼠标是否在坐标轴内
        if event.inaxes != self.ax:
            self.annot.set_visible(False)
            self.vline.set_visible(False)
            self.canvas.draw_idle()
            return

        # 获取鼠标x坐标（浮点数日期）
        x_data = event.xdata

        # 【修改】使用数值型日期数组计算最近的索引，避免 Timestamp - float 的类型错误
        idx = (np.abs(self.unique_dates_num - x_data)).argmin()

        # 获取对应的 Timestamp 对象用于后续显示
        x_date = self.unique_dates[idx]

        # 移动垂直辅助线
        self.vline.set_xdata([x_date, x_date])  # set_xdata 通常也能处理 Timestamp
        self.vline.set_visible(True)

        # 构建显示文本
        text_str = f"日期: {x_date.strftime('%Y-%m-%d')}\n"

        # 获取当前可见的线条数据
        for line in self.ax.lines:
            if line.get_linestyle() == ':': continue  # 跳过辅助线
            if not line.get_visible(): continue  # 跳过隐藏的线条

            label = line.get_label()
            y_data = line.get_ydata()

            # 获取对应索引的y值，如果存在
            if idx < len(y_data):
                val = y_data[idx]
                text_str += f"{label}: {val}\n"

        # 更新注释位置和文本
        self.annot.xy = (x_date, event.ydata)
        self.annot.set_text(text_str)
        self.annot.set_visible(True)

        self.canvas.draw_idle()

    def plot_charts(self, df_stat, start_date, end_date):
        """绘制板块热度折线图"""
        # 【修改】注销旧的事件连接，防止重复触发
        if self.mpl_cid is not None:
            self.canvas.mpl_disconnect(self.mpl_cid)

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        # 优化：只使用数据中存在的日期（交易日）
        df_stat['日期_dt'] = pd.to_datetime(df_stat['日期'])
        self.unique_dates = sorted(df_stat['日期_dt'].unique())
        self.unique_dates_num = mdates.date2num(self.unique_dates)

        if not self.unique_dates:
            self.canvas.draw()
            return

        if not self.unique_dates:
            self.canvas.draw()
            return

        # 选择前10个最热门的板块（总重复次数最多）
        plate_totals = df_stat.groupby('板块名称')['概念重复次数'].sum().sort_values(ascending=False)
        top_plates = plate_totals.head(10).index.tolist()

        if not top_plates:
            self.canvas.draw()
            return

        # 【新增】清空旧复选框
        # 删除 chk_layout 中的所有子控件
        while self.chk_layout.count():
            item = self.chk_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # 为每个板块绘制折线并创建复选框
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        all_max_y = 0

        for idx, plate in enumerate(top_plates):
            plate_data = df_stat[df_stat['板块名称'] == plate].copy()
            # 确保数据按日期排序
            plate_data = plate_data.sort_values('日期_dt')

            x_dates = plate_data['日期_dt'].tolist()
            y_counts = plate_data['概念重复次数'].tolist()

            # 更新最大值
            if y_counts:
                all_max_y = max(all_max_y, max(y_counts))

            color = colors[idx % len(colors)]

            # 绘制折线
            self.ax.plot(x_dates, y_counts, marker='o', linewidth=2, markersize=6,
                         label=plate, color=color)

            # 【新增】创建复选框
            chk = QCheckBox(plate)
            chk.setChecked(True)  # 默认全部选中

            # 设置复选框文字颜色与折线一致
            palette = chk.palette()
            palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(color))
            chk.setPalette(palette)

            # 使用 lambda 捕获参数
            chk.stateChanged.connect(lambda state, p=plate: self.toggle_line(p, state == QtCore.Qt.Checked))

            self.chk_layout.addWidget(chk)

        # 添加弹性空间，把复选框挤到左边
        self.chk_layout.addStretch()

        # 设置图表标题和标签
        self.ax.set_title(f"板块热度趋势图 ({start_date} 至 {end_date})", fontsize=14, fontweight='bold')
        self.ax.set_xlabel('日期', fontsize=12)
        self.ax.set_ylabel('概念重复次数', fontsize=12)

        # 设置X轴为日期格式
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        # 自动调整日期刻度密度
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # 设置Y轴：起点从5开始，上限自动
        self.ax.set_ylim(bottom=5, top=all_max_y + 1)

        # 添加图例（可选，因为已有复选框）
        # self.ax.legend(loc='best', fontsize=9, framealpha=0.9)

        # 添加网格
        self.ax.grid(True, alpha=0.3, linestyle='--')

        # 自动调整布局
        self.figure.tight_layout()

        # 【新增】初始化鼠标悬停的辅助元素
        # 创建垂直辅助线
        self.vline = self.ax.axvline(x=self.unique_dates[0], color='gray', linestyle=':', alpha=0.8)
        self.vline.set_visible(False)

        # 创建文本注释框
        self.annot = self.ax.annotate('', xy=(0, 0), xytext=(20, 20), textcoords='offset points',
                                      bbox=dict(boxstyle='round', fc='w', alpha=0.8),
                                      arrowprops=dict(arrowstyle='->'))
        self.annot.set_visible(False)

        # 【新增】连接鼠标移动事件
        self.mpl_cid = self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        # 刷新画布
        self.canvas.draw()

    def _add_stock_row_simple(self, row_data):
        """简单模式：只添加日期、代码、名称3列，不查询概念库"""
        code = str(row_data['代码']).zfill(6)
        name = str(row_data['名称'])
        date = str(row_data['日期'])

        # 检查重复
        for r in range(self.stock_tb.rowCount()):
            item_code = self.stock_tb.item(r, 1)
            item_date = self.stock_tb.item(r, 0)
            if item_code and item_code.text() == code and item_date and item_date.text() == date:
                return

        current_row = self.stock_tb.rowCount()
        self.stock_tb.insertRow(current_row)

        # 第0列：日期
        date_item = QtWidgets.QTableWidgetItem(date)
        date_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.stock_tb.setItem(current_row, 0, date_item)

        # 第1列：代码
        code_item = QtWidgets.QTableWidgetItem(code)
        code_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.stock_tb.setItem(current_row, 1, code_item)

        # 第2列：名称
        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.stock_tb.setItem(current_row, 2, name_item)

    def _add_stock_row_from_list(self, row_data):
        """完整模式：从 zt_list 的行数据添加股票到表格，包含完整概念列"""
        code = str(row_data['代码']).zfill(6)
        name = str(row_data['名称'])
        date = str(row_data['日期'])

        # 检查重复
        for r in range(self.stock_tb.rowCount()):
            item_code = self.stock_tb.item(r, 1)
            item_date = self.stock_tb.item(r, 0)
            if item_code and item_code.text() == code and item_date and item_date.text() == date:
                return

        current_row = self.stock_tb.rowCount()
        self.stock_tb.insertRow(current_row)

        # 第0列：日期
        date_item = QtWidgets.QTableWidgetItem(date)
        date_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.stock_tb.setItem(current_row, 0, date_item)

        # 第1列：代码
        code_item = QtWidgets.QTableWidgetItem(code)
        code_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.stock_tb.setItem(current_row, 1, code_item)

        # 第2列：名称
        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.stock_tb.setItem(current_row, 2, name_item)

        # 补充概念列（1-46）
        if not self.df_stocks is None and not self.df_stocks.empty:
            stock_info = self.df_stocks[self.df_stocks['代码'] == code]
            if not stock_info.empty:
                s_data = stock_info.iloc[0]
                for i in range(1, 47):
                    col_idx = i + 2
                    col_name = f'概念{i}'
                    val = s_data.get(col_name)
                    if pd.isna(val):
                        val = ""
                    item = QtWidgets.QTableWidgetItem(str(val))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    self.stock_tb.setItem(current_row, col_idx, item)

        # 刷新颜色
        # self._refresh_stock_table_colors()




if __name__ == "__main__":
    import matplotlib.pyplot as plt

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
