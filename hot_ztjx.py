# -*- coding: utf-8 -*-
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator

from PyQt5.QtWidgets import (QHeaderView, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QSpacerItem, QCheckBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QGroupBox, QComboBox, QDateEdit,
                             QGridLayout, QLabel, QButtonGroup, QAbstractItemView,
                             QMenu, QInputDialog, QMessageBox)
# ===== 新增：matplotlib 导入 =====
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from link_tdx import link_tdx
# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class MainWindow(object):
    def __init__(self):
        super().__init__()
        """在MainWindow的__init__方法中添加初始化"""
        # ================= 新增：保存当前状态用于刷新 =================
        self.current_filters = {}  # 保存当前的查询条件
        self.current_ztjx_data = pd.DataFrame()  # 缓存当前的ztjx数据

    # ===== 新增：通达信联接函数 =====


    # =================================

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        # 设置初始大小
        MainWindow.resize(1920, 1250)

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
        # self.banner = QtWidgets.QLabel(self.centralwidget)
        # self.banner.setFixedHeight(50)
        # font_banner = QtGui.QFont("SimHei", 18, QtGui.QFont.Bold)
        # self.banner.setFont(font_banner)
        # self.banner.setStyleSheet(
        #     "color: white; background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgb(0, 85, 128), stop:1 rgb(0, 170, 255));")
        # self.banner.setAlignment(QtCore.Qt.AlignCenter)
        # self.banner.setObjectName("banner")
        # main_layout.addWidget(self.banner)

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

        self.stock_btn_group = QButtonGroup()

        stock_options = ["全部", "沪A", "科创板", "深A", "创业板", "京A", "可转债"]
        for idx, text in enumerate(stock_options):
            btn = QPushButton(text)
            btn.setCheckable(True)
            if idx == 0: btn.setChecked(True)  # 默认选中全部
            btn.setStyleSheet("""
                QPushButton:checked { background-color: rgb(0, 170, 255); color: white; }
                QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px 10px; }
            """)
            setattr(self, f"btn_stock_{idx}", btn)
            self.stock_btn_group.addButton(btn)
            stock_layout.addWidget(btn)

        # 个股输入框
        stock_layout.addSpacing(20)
        stock_layout.addWidget(QLabel("个股代码/名称:"))
        self.input_stock = QtWidgets.QLineEdit()
        self.input_stock.setPlaceholderText("输入代码或名称")
        self.input_stock.setFixedWidth(100)
        self.input_stock.setStyleSheet("font-size: 14pt; font-weight: bold; color: green;")

        reg_ex = QRegExp("[0-9]{2,6}")
        validator = QRegExpValidator(reg_ex, self.input_stock)
        self.input_stock.setValidator(validator)
        self.input_stock.returnPressed.connect(self.on_query_clicked)
        stock_layout.addWidget(self.input_stock)

        stock_layout.addStretch()
        filter_layout.addLayout(stock_layout)

        # --- 2. 日期范围 ---
        date_layout = QHBoxLayout()
        date_label = QLabel("日期范围:")
        date_label.setStyleSheet("font-weight: bold; color: #333;")
        date_layout.addWidget(date_label)

        self.date_btn_group = QtWidgets.QButtonGroup(self.centralwidget)
        self.date_btns = []

        date_options = ["当天", "近3日", "近5日", "近10日", "近30日", "自定义"]

        for idx, text in enumerate(date_options):
            btn = QPushButton(text)
            btn.setCheckable(True)
            self.date_btn_group.addButton(btn)
            if idx == 0: btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton:checked { background-color: rgb(0, 170, 255); color: white; }
                QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px 10px; }
            """)
            setattr(self, f"btn_date_{text}", btn)
            self.date_btns.append(btn)
            date_layout.addWidget(btn)

        # 日期选择器
        date_layout.addSpacing(20)
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

        query_layout.addStretch()
        query_layout.addWidget(self.btn_query)
        query_layout.addSpacing(20)
        query_layout.addWidget(self.btn_update_yyb)
        query_layout.addStretch()

        filter_layout.addLayout(query_layout)
        main_layout.addWidget(filter_group)

        # ================= 表格区域 =================
        tables_grid = QGridLayout()
        tables_grid.setSpacing(10)

        # 1. list_tb (题材统计表 - 原龙虎榜列表位置)
        self.list_tb = QTableWidget()
        self.list_tb.setColumnCount(4)
        self.list_tb.setHorizontalHeaderLabels(["日期", "大类名", "涨停数量", "题材"])
        self.list_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.list_tb.setObjectName("list_tb")
        self.list_tb.setSortingEnabled(True)
        self.list_tb.horizontalHeader().setSectionsClickable(True)
        self.list_tb.horizontalHeader().setSortIndicatorShown(True)
        self.list_tb.setSelectionBehavior(QAbstractItemView.SelectRows)

        # ===== 新增：开启自动换行 =====
        self.list_tb.setWordWrap(True)  # 允许文本换行
        # ==============================

        self.list_tb.setStyleSheet("""
            QTableWidget {
                font-size: 12pt;
            }
            QTableWidget::item:selected {
                background-color: #005580;
                color: white;
            }
        """)
        self.list_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tables_grid.addWidget(QLabel("题材统计"), 0, 0)
        tables_grid.addWidget(self.list_tb, 1, 0)
        self.list_tb.setMinimumHeight(700)
        self.list_tb.setMinimumWidth(530)

        # 设置列宽
        self.list_tb.setColumnWidth(0, 100)  # 日期
        self.list_tb.setColumnWidth(1, 60)  # 大类名
        self.list_tb.setColumnWidth(2, 40)  # 涨停数量
        self.list_tb.setColumnWidth(3, 340)  # 题材

        # 2. yyb_tb (个股详情表 - 原营业部统计位置)
        self.yyb_tb = QTableWidget()
        self.yyb_tb.setColumnCount(7)
        self.yyb_tb.setHorizontalHeaderLabels([
            "股票名称", "代码", "最新价", "强度", "龙虎榜",  "涨停时间", "解析"
        ])
        self.yyb_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.yyb_tb.setObjectName("yyb_tb")
        self.yyb_tb.setSortingEnabled(True)
        self.yyb_tb.horizontalHeader().setSectionsClickable(True)
        self.yyb_tb.horizontalHeader().setSortIndicatorShown(True)
        self.yyb_tb.setSelectionBehavior(QAbstractItemView.SelectRows)

        # ===== 新增：开启自动换行 =====
        self.yyb_tb.setWordWrap(True)  # 允许文本换行
        # ==============================

        self.yyb_tb.setStyleSheet("""
            QTableWidget {
                font-size: 12pt;
            }
            QTableWidget::item:selected {
                background-color: #005580;
                color: white;
            }
        """)
        self.yyb_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tables_grid.addWidget(QLabel("个股详情"), 0, 1)
        tables_grid.addWidget(self.yyb_tb, 1, 1)
        self.yyb_tb.setMinimumHeight(700)

        # 设置列宽
        self.yyb_tb.setColumnWidth(0, 70)  # 股票名称
        self.yyb_tb.setColumnWidth(1, 90)  # 代码
        self.yyb_tb.setColumnWidth(2, 60)  # 最新价
        self.yyb_tb.setColumnWidth(3, 60)  # 强度
        self.yyb_tb.setColumnWidth(4, 60)  # 龙虎榜（新增）
        self.yyb_tb.setColumnWidth(5, 70)  # 涨停时间
        self.yyb_tb.setColumnWidth(6, 780)  # 解析

        # 设置行伸展比例
        tables_grid.setRowStretch(0, 0)
        tables_grid.setRowStretch(1, 1)
        tables_grid.setColumnStretch(0, 1)
        tables_grid.setColumnStretch(1, 2)

        main_layout.addLayout(tables_grid)

        # ================= 新增：图表区域 =================
        chart_group = QGroupBox("涨停趋势图（近5日大类名统计 - 当天Top10）")
        chart_group.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid gray; border-radius: 5px; margin-top: 10px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        chart_main_layout = QVBoxLayout()
        chart_group.setLayout(chart_main_layout)

        # 创建 matplotlib 图表
        self.figure = Figure(figsize=(16, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.chart_ax = self.figure.add_subplot(111)

        chart_main_layout.addWidget(self.canvas)

        # ===== 新增：底部复选框区域 =====
        self.checkbox_widget = QtWidgets.QWidget()
        self.checkbox_layout = QHBoxLayout(self.checkbox_widget)
        self.checkbox_layout.setContentsMargins(10, 5, 10, 5)
        self.checkbox_layout.setSpacing(15)
        self.checkbox_layout.addStretch()

        chart_main_layout.addWidget(self.checkbox_widget)

        # 存储复选框对象
        self.chart_checkboxes = {}

        main_layout.addWidget(chart_group)
        # ==================================================

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
        self.btn_update_yyb.clicked.connect(self.on_update_data_clicked)
        self.list_tb.itemClicked.connect(self.on_list_tb_clicked)
        self.yyb_tb.cellClicked.connect(self.on_yyb_tb_cell_clicked)

        # 初始化表格数据
        self.init_sample_data()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "涨停解析分析系统"))
        # self.banner.setText(_translate("MainWindow", "涨停解析分析系统 V3.0"))


    def get_current_ui_filters(self):
        """从界面控件获取当前的筛选条件"""
        filters = {}

        # 1. 股票类型筛选
        stock_types = []
        for btn in self.stock_btn_group.buttons():
            if btn.isChecked():
                stock_types.append(btn.text())
        filters['stock_types'] = stock_types if stock_types else ['全部']

        # 2. 个股输入
        filters['stock_input'] = self.input_stock.text().strip()

        # 3. 日期筛选
        date_mode = "当天"
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

        return filters

    def load_data_from_csv(self, filters=None):
        """从 data/ztjx.csv 读取数据并填充表格"""
        csv_path = 'data/ztjx.csv'

        if not os.path.exists(csv_path):
            print(f"警告: 未找到文件 {csv_path}")
            self.list_tb.setRowCount(1)
            self.list_tb.setColumnCount(1)
            self.list_tb.setHorizontalHeaderLabels(["提示"])
            self.list_tb.setItem(0, 0, QTableWidgetItem(f"未找到数据文件: {csv_path}"))
            self.yyb_tb.setRowCount(0)
            return

        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

            # 预处理：确保关键列存在
            required_cols = ['日期', '大类名', '题材', '股票名称', '代码']
            for col in required_cols:
                if col not in df.columns:
                    print(f"❌ 错误: CSV文件缺少必要列 '{col}'")
                    return

            # 转换日期列
            df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
            df['代码'] = df['代码'].astype(str)

            # ------------------- 1. 日期筛选 -------------------
            if filters:
                date_mode = filters.get('date_mode', '当天')

                if date_mode in ["当天", "近3日", "近5日", "近10日", "近30日"]:
                    unique_dates = sorted(df['日期'].dropna().unique(), reverse=True)

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
                        df = df[df['日期'].isin(target_dates)]

                elif date_mode == "自定义":
                    start_date = pd.to_datetime(filters.get('start_date'))
                    end_date = pd.to_datetime(filters.get('end_date'))
                    df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]

            # ------------------- 2. 股票类型筛选 -------------------
            if filters:
                stock_types = filters.get('stock_types', [])
                stock_input = filters.get('stock_input', "").strip()

                if "全部" not in stock_types and stock_types:
                    masks = []
                    for st in stock_types:
                        # ===== 修改：根据新的代码前缀规则筛选 =====
                        if st == "沪A":
                            # 沪A以sh开头，但排除科创板(sh68)
                            masks.append(df['代码'].str.startswith('sh') & ~df['代码'].str.startswith('sh68'))
                        elif st == "科创板":
                            # 科创板以sh68开头
                            masks.append(df['代码'].str.startswith('sh68'))
                        elif st == "深A":
                            # 深A以sz开头，排除创业板(sz3)
                            masks.append(df['代码'].str.startswith('sz') & ~df['代码'].str.startswith('sz3'))
                        elif st == "创业板":
                            # 创业板以sz3开头
                            masks.append(df['代码'].str.startswith('sz3'))
                        elif st == "京A":
                            # 假设京A以bj开头 (根据通用的前缀规则)
                            masks.append(df['代码'].str.startswith('bj'))
                        elif st == "可转债":
                            # 假设可转债以sh11或sz12开头 (根据通用的前缀规则)
                            masks.append(df['代码'].str.startswith('sh11') | df['代码'].str.startswith('sz12') | df[
                                '代码'].str.startswith('sz13'))
                        # ==========================================

                    if masks:
                        combined_mask = masks[0]
                        for m in masks[1:]:
                            combined_mask |= m
                        df = df[combined_mask]

                if stock_input:
                    df = df[df['代码'].str.contains(stock_input) | df['股票名称'].str.contains(stock_input)]

            # 缓存当前筛选后的数据
            self.current_ztjx_data = df.copy()

            # ================= 填充 list_tb (题材统计) =================
            self.populate_list_tb(df)

            # ================= 填充 yyb_tb (个股详情) =================
            self.populate_yyb_tb(df)
            self.update_chart(df)

            print(f"✅ 数据加载完成: 共 {len(df)} 条记录")
            self.statusbar.showMessage(f"数据加载完成: 共 {len(df)} 条记录", 3000)

        except Exception as e:
            print(f"❌ 读取 CSV 文件时出错: {e}")
            import traceback
            traceback.print_exc()

    def populate_list_tb(self, df):
        """填充题材统计表 list_tb"""
        if df.empty:
            self.list_tb.setRowCount(0)
            return

        # 按日期、大类名、题材分组统计涨停数量
        try:
            # 确保分组列存在
            group_cols = ['日期', '大类名', '题材']
            for col in group_cols:
                if col not in df.columns:
                    print(f"⚠️ 缺少列: {col}")
                    self.list_tb.setRowCount(0)
                    return

            grouped = df.groupby(group_cols)['代码'].count().reset_index()
            grouped.columns = ['日期', '大类名', '题材', '涨停数量']

            # 按日期降序、涨停数量降序排序
            grouped = grouped.sort_values(by=['日期', '涨停数量'], ascending=[False, False])

            self.list_tb.setRowCount(len(grouped))

            for row_idx in range(len(grouped)):
                row_data = grouped.iloc[row_idx]

                # 日期格式化
                date_val = row_data['日期']
                if pd.notna(date_val):
                    date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)
                else:
                    date_str = ""

                # 创建单元格
                item_date = QTableWidgetItem(date_str)

                # ===== 修改：大类名列设为红色 =====
                item_category = QTableWidgetItem(str(row_data['大类名']))
                item_category.setForeground(QtGui.QColor("red"))
                # ================================

                item_count = QTableWidgetItem(str(int(row_data['涨停数量'])))
                item_theme = QTableWidgetItem(str(row_data['题材']))

                # ===== 修改：题材列不同行不同颜色 =====
                if row_idx % 2 == 0:
                    item_theme.setForeground(QtGui.QColor("black"))
                else:
                    item_theme.setForeground(QtGui.QColor("darkblue"))
                # ======================================

                # 设置文本对齐方式（可选：左上角对齐更适合多行文本）
                item_theme.setTextAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

                self.list_tb.setItem(row_idx, 0, item_date)
                self.list_tb.setItem(row_idx, 1, item_category)
                self.list_tb.setItem(row_idx, 2, item_count)
                self.list_tb.setItem(row_idx, 3, item_theme)

            # ===== 新增：根据内容调整行高 =====
            self.list_tb.resizeRowsToContents()
            # ==================================

            print(f"✅ 题材统计表填充完成: 共 {len(grouped)} 个题材组")

        except Exception as e:
            print(f"❌ 填充题材统计表出错: {e}")
            import traceback
            traceback.print_exc()

    def populate_yyb_tb(self, df):
        """填充个股详情表 yyb_tb"""
        if df.empty:
            self.yyb_tb.setRowCount(0)
            return

        # ===== 新增：读取龙虎榜数据 =====
        lhb_set = set()
        lhb_path = 'data/lhb_b.csv'
        if os.path.exists(lhb_path):
            try:
                lhb_df = pd.read_csv(lhb_path, encoding='utf-8-sig')
                # 将日期和代码组合成集合，方便快速查找
                for _, row in lhb_df.iterrows():
                    date_str = str(row['上榜日'])
                    code_raw = str(row['代码']).strip()
                    # 补齐到6位，如 "2261" -> "002261"
                    code_num = code_raw.zfill(6)
                    lhb_set.add((date_str, code_num))
            except Exception as e:
                print(f"⚠️ 读取龙虎榜数据出错: {e}")
        # ================================

        # 列映射: CSV列名 -> 显示列名
        # 显示列: 股票名称、代码、最新价、强度、龙虎榜、涨停时间、解析
        col_mapping = {
            '股票名称': '股票名称',
            '代码': '代码',
            '最新价': '最新价',
            '强度': '强度',
            '龙虎榜': '',
            '涨停时间': '涨停时间',
            '解析': '解析'
        }

        self.yyb_tb.setRowCount(len(df))

        for row_idx in range(len(df)):
            row_data = df.iloc[row_idx]

            # ===== 新增：获取当前行的日期和代码用于龙虎榜匹配 =====
            date_val = row_data.get('日期', '')
            if pd.notna(date_val) and hasattr(date_val, 'strftime'):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(date_val)[:10] if pd.notna(date_val) else ''

            code_val = str(row_data.get('代码', ''))
            # 去掉前缀 sh/sz/bj
            code_num = code_val[2:] if len(code_val) > 2 and code_val[:2] in ['sh', 'sz', 'bj'] else code_val
            # ====================================================

            for col_idx, (csv_col, display_col) in enumerate(col_mapping.items()):
                if csv_col in df.columns:
                    val = row_data.get(csv_col, "")

                    if pd.isna(val):
                        display_val = ""
                    elif isinstance(val, float):
                        display_val = f"{val:.2f}"
                    else:
                        display_val = str(val)

                    item = QTableWidgetItem(display_val)
                    item.setTextAlignment(QtCore.Qt.AlignCenter)

                    if csv_col == '代码':
                        code_str = str(val)
                        if code_str.startswith('sh68') or code_str.startswith('sz3'):
                            item.setForeground(QtGui.QColor("red"))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)

                    if csv_col == '涨停时间':
                        time_str = str(val).strip()
                        try:
                            if ' ' in time_str:
                                time_str = time_str.split(' ')[-1]
                            fmt = "%H:%M:%S" if len(time_str) > 5 else "%H:%M"
                            t_obj = datetime.strptime(time_str, fmt)

                            t_10 = datetime.strptime("10:00", "%H:%M")
                            t_11_30 = datetime.strptime("11:30", "%H:%M")
                            t_14_30 = datetime.strptime("14:30", "%H:%M")
                            t_15 = datetime.strptime("15:00", "%H:%M")

                            if t_obj < t_10:
                                item.setForeground(QtGui.QColor("red"))
                            elif t_10 <= t_obj <= t_11_30:
                                item.setForeground(QtGui.QColor("blue"))
                            elif t_14_30 <= t_obj <= t_15:
                                item.setForeground(QtGui.QColor("green"))
                        except ValueError:
                            pass

                    if csv_col == '解析':
                        if row_idx % 2 == 0:
                            item.setForeground(QtGui.QColor("black"))
                        else:
                            item.setForeground(QtGui.QColor("darkblue"))

                    self.yyb_tb.setItem(row_idx, col_idx, item)
                else:
                    self.yyb_tb.setItem(row_idx, col_idx, QTableWidgetItem(""))

            # ===== 新增：填充龙虎榜列（第5列，索引4）=====
            lhb_item = QTableWidgetItem("")
            lhb_item.setTextAlignment(QtCore.Qt.AlignCenter)
            if (date_str, code_num) in lhb_set:
                lhb_item.setText("***")
                lhb_item.setForeground(QtGui.QColor("red"))
                font = lhb_item.font()
                font.setBold(True)
                lhb_item.setFont(font)
            self.yyb_tb.setItem(row_idx, 4, lhb_item)
            # ===========================================

        self.yyb_tb.resizeRowsToContents()
        print(f"✅ 个股详情表填充完成: 共 {len(df)} 条记录")

    def update_chart(self, df):
        """更新折线图：近5日当天涨停数量最多的10个大类趋势"""
        try:
            # 直接从 CSV 文件读取数据
            csv_path = 'data/ztjx.csv'

            if not os.path.exists(csv_path):
                print("⚠️ 未找到数据文件，跳过图表更新")
                return

            # 读取完整数据
            df_full = pd.read_csv(csv_path, encoding='utf-8-sig')
            df_full['日期'] = pd.to_datetime(df_full['日期'], errors='coerce')

            # 获取所有唯一日期（降序）
            all_dates = sorted(df_full['日期'].dropna().unique(), reverse=True)

            if not all_dates:
                print("⚠️ 无有效日期数据")
                return

            # 获取当天日期（最新日期）
            current_date = all_dates[0]

            # 获取近5日的日期
            recent_5_dates = all_dates[:5]

            # ===== 筛选当天涨停数量最多的10个大类 =====
            df_today = df_full[df_full['日期'] == current_date].copy()

            if df_today.empty or '大类名' not in df_today.columns:
                print("⚠️ 当天数据为空或缺少大类名列")
                return

            # 统计当天各大类涨停数量
            today_grouped = df_today.groupby('大类名')['代码'].count().reset_index()
            today_grouped.columns = ['大类名', '涨停数量']

            # 按涨停数量降序排序，取前10
            top10_categories = today_grouped.sort_values('涨停数量', ascending=False).head(10)['大类名'].tolist()

            if not top10_categories:
                print("⚠️ 未找到大类名数据")
                return

            # 缓存数据用于重绘
            self.chart_data = {
                'df_full': df_full,
                'recent_5_dates': recent_5_dates,
                'top10_categories': top10_categories,
                'current_date': current_date
            }

            # ===== 创建/更新复选框 =====
            self._create_checkboxes(top10_categories)

            # ===== 绘制图表 =====
            self._draw_chart()

            print(f"✅ 图表更新完成: 当天Top10大类名")

        except Exception as e:
            print(f"❌ 更新图表出错: {e}")
            import traceback
            traceback.print_exc()

    def _create_checkboxes(self, categories):
        """创建复选框"""
        try:
            # 清除旧的复选框
            for checkbox in self.chart_checkboxes.values():
                checkbox.deleteLater()
            self.chart_checkboxes.clear()

            # 清空布局中的旧控件
            while self.checkbox_layout.count() > 0:
                item = self.checkbox_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 定义颜色列表
            colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6',
                      '#1ABC9C', '#E67E22', '#34495E', '#16A085', '#C0392B']

            # 创建新的复选框
            for idx, category in enumerate(categories):
                color = colors[idx % len(colors)]

                checkbox = QCheckBox(str(category))
                checkbox.setChecked(True)  # 默认选中
                checkbox.setStyleSheet(f"""
                    QCheckBox {{
                        font-size: 12px;
                        font-weight: bold;
                        color: {color};
                    }}
                    QCheckBox::indicator {{
                        width: 12px;
                        height: 12px;
                    }}
                """)

                # 绑定状态变化事件
                checkbox.stateChanged.connect(self._on_checkbox_changed)

                self.chart_checkboxes[category] = checkbox
                self.checkbox_layout.addWidget(checkbox)

            self.checkbox_layout.addStretch()

        except Exception as e:
            print(f"❌ 创建复选框出错: {e}")
            import traceback
            traceback.print_exc()

    def _on_checkbox_changed(self):
        """复选框状态变化时重绘图表"""
        self._draw_chart()

    def _draw_chart(self):
        """绘制图表"""
        try:
            if not hasattr(self, 'chart_data'):
                return

            df_full = self.chart_data['df_full']
            recent_5_dates = self.chart_data['recent_5_dates']
            top10_categories = self.chart_data['top10_categories']

            # 筛选近5日数据
            df_chart = df_full[df_full['日期'].isin(recent_5_dates)].copy()

            # 按日期、大类名分组统计涨停数量
            grouped = df_chart.groupby(['日期', '大类名'])['代码'].count().reset_index()
            grouped.columns = ['日期', '大类名', '涨停数量']

            # 准备绘图数据
            dates_sorted = sorted(recent_5_dates)  # 升序排列用于绘图
            date_labels = [d.strftime('%m-%d') if hasattr(d, 'strftime') else str(d)[:10] for d in dates_sorted]

            # 清空图表
            self.chart_ax.clear()

            # 定义颜色列表
            colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6',
                      '#1ABC9C', '#E67E22', '#34495E', '#16A085', '#C0392B']

            # 为每个大类名绘制折线
            for idx, category in enumerate(top10_categories):
                # 检查复选框状态
                if category in self.chart_checkboxes:
                    if not self.chart_checkboxes[category].isChecked():
                        continue  # 未选中则跳过

                cat_data = grouped[grouped['大类名'] == category]

                # 构建完整的数据点
                count_list = []
                for d in dates_sorted:
                    match = cat_data[cat_data['日期'] == d]
                    if not match.empty:
                        count_list.append(int(match['涨停数量'].values[0]))
                    else:
                        count_list.append(0)

                # 绘制折线
                color = colors[idx % len(colors)]
                self.chart_ax.plot(date_labels, count_list,
                                   marker='o',
                                   linewidth=2.5,
                                   markersize=8,
                                   label=str(category),
                                   color=color)

                # 在数据点上标注数值
                for i, (x, y) in enumerate(zip(date_labels, count_list)):
                    if y > 0:
                        self.chart_ax.annotate(str(y), (x, y),
                                               textcoords="offset points",
                                               xytext=(0, 10),
                                               ha='center',
                                               fontsize=10,
                                               fontweight='bold',
                                               color=color)

            # 设置图表样式
            # self.chart_ax.set_xlabel('日期', fontsize=12, fontweight='bold')
            # self.chart_ax.set_ylabel('涨停数量', fontsize=12, fontweight='bold')
            # self.chart_ax.set_title('近5日大类名涨停数量趋势（当天Top10）', fontsize=14, fontweight='bold', pad=15)
            # self.chart_ax.legend(loc='upper left', fontsize=10, framealpha=0.9, ncol=2)
            self.chart_ax.grid(True, linestyle='--', alpha=0.4)
            self.chart_ax.set_ylim(bottom=0)

            # 设置背景色
            self.chart_ax.set_facecolor('#F8F9FA')
            self.figure.patch.set_facecolor('#FFFFFF')

            # 自动调整布局
            self.figure.tight_layout()

            # 刷新画布
            self.canvas.draw()

        except Exception as e:
            print(f"❌ 绘制图表出错: {e}")
            import traceback
            traceback.print_exc()

    def on_list_tb_clicked(self, item):
        """点击题材统计表，筛选显示对应的个股详情"""
        try:
            row = item.row()

            # 获取选中行的筛选条件
            date_item = self.list_tb.item(row, 0)  # 日期
            category_item = self.list_tb.item(row, 1)  # 大类名
            theme_item = self.list_tb.item(row, 3)  # 题材

            if not all([date_item, category_item, theme_item]):
                return

            selected_date = date_item.text()
            selected_category = category_item.text()
            selected_theme = theme_item.text()

            print(f"🖱️ 点击题材: 日期={selected_date}, 大类={selected_category}, 题材={selected_theme}")

            # 从缓存数据中筛选
            if self.current_ztjx_data.empty:
                return

            df = self.current_ztjx_data.copy()

            # 筛选逻辑
            # 日期匹配 (需要处理日期格式)
            df['日期_str'] = df['日期'].apply(
                lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) and hasattr(x, 'strftime') else str(x))
            df = df[df['日期_str'] == selected_date]

            if selected_category and selected_category != "nan":
                df = df[df['大类名'] == selected_category]

            if selected_theme and selected_theme != "nan":
                df = df[df['题材'] == selected_theme]

            # 更新 yyb_tb
            self.populate_yyb_tb(df)

            self.statusbar.showMessage(f"已筛选: {selected_theme} 共 {len(df)} 只个股", 3000)

        except Exception as e:
            print(f"❌ 点击题材行出错: {e}")
            import traceback
            traceback.print_exc()

    def on_yyb_tb_cell_clicked(self, row, col):
        """点击 yyb_tb 表格单元格事件"""
        try:
            # 只处理代码列（第2列，索引1）
            if col != 1:
                return

            # 获取代码单元格内容
            code_item = self.yyb_tb.item(row, 1)
            if not code_item:
                return

            code_val = code_item.text().strip()

            # 去掉前缀 sh/sz/bj，获取6位代码
            if len(code_val) > 2 and code_val[:2] in ['sh', 'sz', 'bj']:
                code_num = code_val[2:]
            else:
                code_num = code_val

            # 调用通达信联接函数（修改：改为直接调用导入的函数）
            link_tdx(code_num)

            # 获取股票名称用于提示
            name_item = self.yyb_tb.item(row, 0)
            stock_name = name_item.text() if name_item else code_num
            self.statusbar.showMessage(f"已联接通达信: {stock_name} ({code_num})", 3000)

        except Exception as e:
            print(f"❌ 点击代码列出错: {e}")
            import traceback
            traceback.print_exc()

    def init_sample_data(self):
        """初始化数据：默认加载当天数据"""
        default_filters = {
            'stock_types': ['全部'],
            'stock_input': '',
            'date_mode': '当天',
            'start_date': '',
            'end_date': ''
        }
        self.load_data_from_csv(default_filters)

    def on_query_clicked(self):
        """处理查询按钮点击"""
        filters = self.get_current_ui_filters()
        self.current_filters = filters
        self.statusbar.showMessage("正在查询...", 0)
        self.load_data_from_csv(filters)
        self.input_stock.clear()

    def on_update_data_clicked(self):
        """更新数据按钮点击事件"""
        try:
            self.statusbar.showMessage("正在更新数据，请稍候...", 0)
            QtWidgets.QApplication.processEvents()

            print("🔄 开始执行数据更新...")

            # 尝试导入并执行数据更新模块
            try:
                from data_update import update
                updater = update()
                updater.run()
            except ImportError:
                print("⚠️ 未找到 data_update 模块，跳过更新")
            except Exception as e:
                print(f"⚠️ 数据更新出错: {e}")

            print("✅ 数据更新完成！")
            self.statusbar.showMessage("数据更新完成！", 5000)

            # 重新加载数据
            self.load_data_from_csv(self.current_filters)

            QtWidgets.QMessageBox.information(None, "更新完成", "数据已成功更新！")

        except Exception as e:
            print(f"❌ 数据更新过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            self.statusbar.showMessage("数据更新失败", 5000)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    ui = MainWindow()
    ui.setupUi(window)
    window.show()
    sys.exit(app.exec_())
