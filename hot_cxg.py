# -*- coding: utf-8 -*-
import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator, QColor, QBrush, QPen, QPainter
from PyQt5.QtWidgets import (QHeaderView, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QCheckBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QGroupBox, QComboBox, QDateEdit, QGridLayout, QLabel,
                             QButtonGroup, QAbstractItemView, QMenu, QInputDialog, QMessageBox)
# 从 link_tdx.py 引入 link_tdx 函数
from link_tdx import link_tdx, get_tdx_path, add_codes_to_blk


# ================= 自定义表格控件：支持绘制连接线 + 表头高亮 =================
class StockTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connection_points = []  # 存储需要连线的单元格中心坐标
        self.connection_code = ""  # 当前连线的代码
        self.highlighted_columns = []  # 存储当前高亮的列索引

    def paintEvent(self, event):
        # 1. 先执行默认的绘制（画出表格、文字、背景）
        super().paintEvent(event)
        # 2. 如果有连线需求，绘制连接线
        if len(self.connection_points) > 1:
            painter = QPainter(self.viewport())
            # 设置画笔：红色，宽度2，抗锯齿
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.Antialiasing)
            # 绘制路径
            path = QtGui.QPainterPath()
            path.moveTo(self.connection_points[0])
            for point in self.connection_points[1:]:
                path.lineTo(point)
            painter.drawPath(path)

    def draw_connections_for_code(self, code):
        """寻找指定代码的所有单元格，计算中心坐标并触发重绘"""
        self.connection_code = code
        self.connection_points = []
        self.reset_header_highlight()
        points = []
        cols_to_highlight = []
        if code:
            for col in range(self.columnCount()):
                found_in_col = False
                for row in range(self.rowCount()):
                    item = self.item(row, col)
                    if item:
                        # 从单元格获取实际代码进行比较
                        cell_code = item.data(QtCore.Qt.UserRole)
                        if cell_code == code:
                            rect = self.visualRect(self.model().index(row, col))
                            center = rect.center()
                            points.append(center)
                            found_in_col = True
                            break
                if found_in_col:
                    cols_to_highlight.append(col)
            self.highlight_header_columns(cols_to_highlight)
        if len(points) > 1:
            self.connection_points = points
        else:
            self.connection_points = []
        self.viewport().update()

    def highlight_header_columns(self, cols):
        """将指定列的表头设为高亮色"""
        self.highlighted_columns = cols
        highlight_color = QColor(100, 200, 50)  # 浅红色背景
        text_color = QColor(200, 000, 0)  # 深红色文字
        for col in cols:
            item = self.horizontalHeaderItem(col)
            if item:
                item.setBackground(QBrush(highlight_color))
                item.setForeground(QBrush(text_color))

    def reset_header_highlight(self):
        """重置表头背景色"""
        default_color = QColor(255, 255, 255)  # 默认白色背景
        default_text = QColor(0, 0, 0)  # 默认黑色文字
        for col in self.highlighted_columns:
            item = self.horizontalHeaderItem(col)
            if item:
                item.setBackground(QBrush(default_color))
                item.setForeground(QBrush(default_text))
        self.highlighted_columns = []

    def clear_connections(self):
        """清除连线和表头高亮"""
        self.connection_points = []
        self.connection_code = ""
        self.reset_header_highlight()  # 清除连线时同时清除表头高亮
        self.viewport().update()


# =================================================================

class MainWindow(object):
    def __init__(self):
        super().__init__()
        self.current_filters = {}
        self.current_ztjx_data = pd.DataFrame()
        # 存储统计类型与颜色的映射 { "统计类型名": QColor }
        self.category_colors = {}
        # 存储股票代码与颜色的映射 { "股票代码": QColor }
        self.code_color_map = {}
        # 通达信路径
        self.tdx_path = get_tdx_path()
        # 程序启动时加载配置
        # 注意：原 load_tdx_config 已移除，路径已由上一行获取
        self.load_color_settings()
        self.show_name_mode = True  # 默认显示名称
        self.code_name_map = {}  # 代码到名称的映射
        self.load_name_map()  # 加载名称映射



    # ================= JSON 配置读写 =================
    def load_color_settings(self):
        """从JSON文件读取颜色设置"""
        path = 'data/hot_cxg.json'
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 将字符串转换回QColor对象
                for k, v in data.items():
                    self.category_colors[k] = QColor(v)
                print("✅ 颜色配置已加载")
            except Exception as e:
                print(f"⚠️ 读取颜色配置失败: {e}")

    def save_color_settings(self):
        """将颜色设置保存到JSON文件"""
        path = 'data/hot_cxg.json'
        try:
            os.makedirs('data', exist_ok=True)
            # 将QColor对象转换为十六进制字符串存储
            data = {k: v.name() for k, v in self.category_colors.items()}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print("✅ 颜色配置已保存")
        except Exception as e:
            print(f"❌ 保存颜色配置失败: {e}")

    # ================================================

    def load_name_map(self):
        """加载代码到名称的映射"""
        name_path = 'data/stock_name.csv'
        if os.path.exists(name_path):
            try:
                df = pd.read_csv(name_path, encoding='utf-8-sig')
                for _, row in df.iterrows():
                    code = str(row['代码']).zfill(6)
                    name = str(row['名称'])
                    self.code_name_map[code] = name
                print(f"✅ 已加载 {len(self.code_name_map)} 个股票名称映射")
            except Exception as e:
                print(f"⚠️ 加载名称映射失败: {e}")

    def toggle_display(self):
        """切换显示模式"""
        self.show_name_mode = not self.show_name_mode
        if self.show_name_mode:
            self.btn_toggle_display.setText("显示代码")
        else:
            self.btn_toggle_display.setText("显示名称")
        self.load_stock_tb()

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1920, 1250)
        icon = QtGui.QIcon()
        try:
            icon.addPixmap(QtGui.QPixmap("app4.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        except:
            pass
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

        # ================= 筛选条件区域 =================
        filter_group = QGroupBox("筛选条件")
        filter_group.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid gray; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        filter_layout = QVBoxLayout()
        filter_group.setLayout(filter_layout)

        # --- 1. 股票范围 (日期范围已删除) ---
        stock_layout = QHBoxLayout()
        stock_label = QLabel("股票范围:")
        stock_label.setStyleSheet("font-weight: bold; color: #333;")
        stock_layout.addWidget(stock_label)
        self.stock_btn_group = QButtonGroup()
        stock_options = ["全部", "沪A", "科创板", "深A", "创业板", "京A", "可转债"]
        for idx, text in enumerate(stock_options):
            btn = QPushButton(text)
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.setStyleSheet(
                "QPushButton:checked { background-color: rgb(0, 170, 255); color: white; } QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px 10px; }")
            setattr(self, f"btn_stock_{idx}", btn)
            self.stock_btn_group.addButton(btn)
            stock_layout.addWidget(btn)
        stock_layout.addSpacing(20)
        stock_layout.addWidget(QLabel("个股代码/名称:"))
        self.input_stock = QtWidgets.QLineEdit()
        self.input_stock.setPlaceholderText("输入代码或名称")
        self.input_stock.setFixedWidth(100)
        self.input_stock.setStyleSheet("font-size: 14pt; font-weight: bold; color: green;")
        self.input_stock.setValidator(QRegExpValidator(QRegExp("[0-9]{2,6}"), self.input_stock))
        self.input_stock.returnPressed.connect(self.on_query_clicked)
        stock_layout.addWidget(self.input_stock)
        stock_layout.addStretch()
        filter_layout.addLayout(stock_layout)

        # --- 查询按钮 ---
        query_layout = QHBoxLayout()
        # 先定义所有按钮
        self.btn_toggle_display = QtWidgets.QPushButton("显示代码")
        self.btn_toggle_display.setFixedHeight(35)
        self.btn_toggle_display.setStyleSheet(
            "QPushButton { background-color: rgb(255, 140, 0); color: white; font-size: 14px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: rgb(255, 120, 0); }")
        self.btn_toggle_display.clicked.connect(self.toggle_display)

        self.btn_query = QPushButton("开始查询")
        self.btn_query.setFixedHeight(35)
        self.btn_query.setStyleSheet(
            "QPushButton { background-color: rgb(0, 170, 255); color: white; font-size: 14px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: rgb(0, 140, 220); }")

        self.btn_update_yyb = QtWidgets.QPushButton("更新数据")
        self.btn_update_yyb.setFixedHeight(35)
        self.btn_update_yyb.setStyleSheet(
            "QPushButton { background-color: rgb(0, 200, 83); color: white; font-size: 14px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: rgb(0, 180, 70); }")

        # 然后添加到布局
        query_layout.addStretch()
        query_layout.addWidget(self.btn_toggle_display)
        query_layout.addSpacing(20)
        query_layout.addWidget(self.btn_query)
        query_layout.addSpacing(20)
        query_layout.addWidget(self.btn_update_yyb)
        query_layout.addStretch()
        filter_layout.addLayout(query_layout)




        main_layout.addWidget(filter_group)

        # ================= 新增：表格区域 =================
        tables_container = QtWidgets.QWidget()
        tables_layout = QVBoxLayout(tables_container)
        tables_layout.setSpacing(10)

        # 1. stat_tb (统计表)
        stat_label = QLabel("频次与连板统计 (右键设定颜色或加入板块，点击代码联动通达信并绘制连线)")
        stat_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        tables_layout.addWidget(stat_label)
        self.stat_tb = QTableWidget()
        self.stat_tb.setContextMenuPolicy(Qt.CustomContextMenu)
        self.stat_tb.customContextMenuRequested.connect(self.show_stat_context_menu)
        self.stat_tb.setColumnCount(3)
        self.stat_tb.setHorizontalHeaderLabels(["统计类型", "数量", "股票代码"])
        self.stat_tb.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.stat_tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.stat_tb.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.stat_tb.setFixedHeight(320)
        self.stat_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.stat_tb.setStyleSheet(
            "QTableWidget { font-size: 12pt; } QTableWidget::item:selected { background-color: #005580; color: white; }")
        self.stat_tb.cellClicked.connect(self.on_stat_cell_clicked)
        tables_layout.addWidget(self.stat_tb)

        # 2. stock_tb (股票列表表 - 使用自定义的支持连线的控件)
        # 2. stock_tb (股票列表表 - 使用自定义的支持连线的控件)
        stock_header_layout = QHBoxLayout()
        stock_label = QLabel("股票列表 (最近10日，每列为一个日期)")
        stock_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        stock_header_layout.addWidget(stock_label)
        self.stock_count_label = QLabel("")  # 显示选中股票的出现次数
        self.stock_count_label.setStyleSheet("font-weight: bold; font-size: 20px; color: red;")
        stock_header_layout.addWidget(self.stock_count_label)
        stock_header_layout.addStretch()
        tables_layout.addLayout(stock_header_layout)

        self.stock_tb = StockTableWidget()
        self.stock_tb.setColumnCount(0)
        self.stock_tb.horizontalHeader().setDefaultSectionSize(70)
        self.stock_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.stock_tb.setMinimumHeight(800)
        self.stock_tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.stock_tb.setStyleSheet(
            "QTableWidget { font-size: 12pt; } QTableWidget::item:selected { background-color: #005580; color: white; }")
        self.stock_tb.cellClicked.connect(self.on_stock_cell_clicked)
        # 开启右键菜单支持
        self.stock_tb.setContextMenuPolicy(Qt.CustomContextMenu)
        self.stock_tb.customContextMenuRequested.connect(self.show_stock_context_menu)

        tables_layout.addWidget(self.stock_tb)
        main_layout.addWidget(tables_container)
        main_layout.addStretch()

        # 菜单栏和状态栏
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1720, 23))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.btn_query.clicked.connect(self.on_query_clicked)
        self.btn_update_yyb.clicked.connect(self.on_update_data_clicked)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "创120日新高个股分析"))

    def on_query_clicked(self):
        self.statusbar.showMessage("正在查询...", 0)
        self.load_stock_tb()
        self.statusbar.showMessage("数据加载完成", 3000)

    def on_update_data_clicked(self):
        self.statusbar.showMessage("正在更新数据...", 0)
        QtWidgets.QApplication.processEvents()
        self.get()
        self.load_stock_tb()

        # 更新连续板块
        if hasattr(self, 'stock_stats'):
            consecutive_map = {
                5: '669lx5c.blk',
                4: '669lx4c.blk',
                3: '669lx3c.blk',
                2: '669lx2c.blk'
            }

            for cons_times, blk_file in consecutive_map.items():
                codes = [code for code, stats in self.stock_stats.items()
                         if stats['consecutive'] >= cons_times]
                if codes:
                    blk_path = os.path.join(self.tdx_path, 'T0002', 'blocknew', blk_file)
                    try:
                        os.makedirs(os.path.dirname(blk_path), exist_ok=True)
                        with open(blk_path, 'w', encoding='gbk') as f:
                            f.write('\n'.join([f'1{code}' for code in codes]))
                        print(f"✅ 已保存 {len(codes)} 个股票到 {blk_file}")
                    except Exception as e:
                        print(f"❌ 保存 {blk_file} 失败: {e}")

        self.statusbar.showMessage("数据更新完成", 3000)

    def on_stat_cell_clicked(self, row, col):
        """点击统计表的单元格"""
        item = self.stat_tb.item(row, col)
        if not item:
            return
        code = item.data(QtCore.Qt.UserRole)
        display_text = item.text()
        # 点击的是代码列 (第3列及以后)
        if col >= 2 and code:
            # 1. 联接通达信
            link_tdx(code)
            self.statusbar.showMessage(f"已联接通达信: {display_text}", 3000)
            # 2. 在 stock_tb 中绘制连线
            self.stock_tb.draw_connections_for_code(code)
            # 3. 更新次数显示
            if hasattr(self, 'stock_stats') and code in self.stock_stats:
                count = self.stock_stats[code]['count']
                self.stock_count_label.setText(f" {display_text}   出现 {count} 次")
            else:
                self.stock_count_label.setText("")
        else:
            # 点击的是类型或数量列，清除连线
            self.stock_tb.clear_connections()
            self.stock_count_label.setText("")


    def on_stock_cell_clicked(self, row, col):
        """点击股票列表的单元格"""
        item = self.stock_tb.item(row, col)
        if not item:
            return
        code = item.data(QtCore.Qt.UserRole)
        display_text = item.text()
        if code:
            link_tdx(code)
            self.statusbar.showMessage(f"已联接通达信: {display_text}", 3000)
            self.stock_tb.draw_connections_for_code(code)
            # 更新次数显示
            if hasattr(self, 'stock_stats') and code in self.stock_stats:
                count = self.stock_stats[code]['count']
                self.stock_count_label.setText(f" {display_text}   出现 {count} 次")
            else:
                self.stock_count_label.setText("")

    def show_stat_context_menu(self, pos):
        """右键菜单设定颜色 或 加入板块"""
        items = self.stat_tb.selectedItems()
        codes = set()
        for item in items:
            if item.column() >= 2:  # 只取代码列的内容
                # 从单元格获取实际代码
                code = item.data(QtCore.Qt.UserRole)
                if code:
                    codes.add(code)

        menu = QtWidgets.QMenu(self.stat_tb)

        # 颜色设置功能
        action_red = menu.addAction("设为红色")
        action_purple = menu.addAction("设为紫色")
        action_deeppink = menu.addAction("设为深粉红色")
        action_peru = menu.addAction("设为古铜色")
        action_yellow = menu.addAction("设为黄色")
        action_blue = menu.addAction("设为蓝色")


        action_green = menu.addAction("设为绿色")




        action_clear = menu.addAction("清除颜色")

        # 板块操作功能
        if codes:
            menu.addSeparator()
            action_add_blk = menu.addAction(f"加入板块 ({len(codes)}个)")
            action_clear_add_blk = menu.addAction(f"清空原板块后加入 ({len(codes)}个)")

        action = menu.exec_(self.stat_tb.mapToGlobal(pos))

        # 处理颜色
        color = None
        if action == action_red:
            color = QColor(255, 200, 200)
        elif action == action_green:
            color = QColor(200, 255, 200)
        elif action == action_blue:
            color = QColor(200, 200, 255)
        elif action == action_yellow:
            color = QColor(255, 255, 200)
        elif action == action_peru:
            color = QColor(205, 133, 163)
        elif action == action_deeppink:
            color = QColor(255, 20, 147)

        elif action == action_purple:
            color = QColor(160, 32, 240)
        elif action == action_clear:
            color = None
        else:
            # 处理板块操作
            if codes:
                if action == action_add_blk:
                    add_codes_to_blk(self.tdx_path, codes, clear_before_add=False)
                elif action == action_clear_add_blk:
                    add_codes_to_blk(self.tdx_path, codes, clear_before_add=True)
            return

        # 应用颜色逻辑
        if not items:
            return
        row = items[0].row()
        cat_item = self.stat_tb.item(row, 0)
        if not cat_item:
            return
        category_name = cat_item.text()

        if color:
            self.category_colors[category_name] = color
        else:
            if category_name in self.category_colors:
                del self.category_colors[category_name]

        self.save_color_settings()
        self.update_code_color_map()
        self.apply_colors_to_tables()

    def show_stock_context_menu(self, pos):
        """股票列表表的右键菜单"""
        items = self.stock_tb.selectedItems()
        codes = set()
        for item in items:
            # 从单元格获取实际代码
            code = item.data(QtCore.Qt.UserRole)
            if code:
                codes.add(code)
        if not codes:
            return
        menu = QtWidgets.QMenu(self.stock_tb)
        action_add_blk = menu.addAction(f"加入板块 ({len(codes)}个)")
        action_clear_add_blk = menu.addAction(f"清空原板块后加入 ({len(codes)}个)")
        action = menu.exec_(self.stock_tb.mapToGlobal(pos))
        if action == action_add_blk:
            add_codes_to_blk(self.tdx_path, codes, clear_before_add=False)
        elif action == action_clear_add_blk:
            add_codes_to_blk(self.tdx_path, codes, clear_before_add=True)

    def update_code_color_map(self):
        """根据当前统计类型颜色，构建股票代码到颜色的映射"""
        self.code_color_map.clear()
        for row in range(self.stat_tb.rowCount()):
            cat_item = self.stat_tb.item(row, 0)
            if not cat_item:
                continue
            cat_name = cat_item.text()
            if cat_name in self.category_colors:
                color = self.category_colors[cat_name]
                for col in range(2, self.stat_tb.columnCount()):
                    code_item = self.stat_tb.item(row, col)
                    if code_item:
                        # 从单元格获取实际代码
                        code = code_item.data(QtCore.Qt.UserRole)
                        if code:
                            self.code_color_map[code] = color

    def apply_colors_to_tables(self):
        """应用颜色到两个表格"""
        # 1. stat_tb
        for row in range(self.stat_tb.rowCount()):
            cat_item = self.stat_tb.item(row, 0)
            if not cat_item:
                continue
            cat_name = cat_item.text()
            bg_color = self.category_colors.get(cat_name, QColor(255, 255, 255))
            for col in range(self.stat_tb.columnCount()):
                item = self.stat_tb.item(row, col)
                if item:
                    item.setBackground(QBrush(bg_color))
        # 2. stock_tb
        for row in range(self.stock_tb.rowCount()):
            for col in range(self.stock_tb.columnCount()):
                item = self.stock_tb.item(row, col)
                if item:
                    # 从单元格获取实际代码
                    code = item.data(QtCore.Qt.UserRole)
                    if code and code in self.code_color_map:
                        item.setBackground(QBrush(self.code_color_map[code]))
                    else:
                        item.setBackground(QBrush(QColor(255, 255, 255)))

    def load_stock_tb(self):
        """读取 cxg669.csv，计算统计数据并显示"""
        csv_path = 'data/cxg669.csv'
        if not os.path.exists(csv_path):
            print(f"⚠️ 未找到数据文件: {csv_path}")
            return
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            if df.empty:
                return
            # ===== 1. 筛选最近10个日期 =====
            df = df.copy()
            df['日期_dt'] = pd.to_datetime(df['日期'])
            today = pd.to_datetime(datetime.now().date())
            df['距离'] = (df['日期_dt'] - today).abs()
            df_sorted = df.sort_values('距离', ascending=True).head(10)
            df_recent = df_sorted.sort_values('日期_dt', ascending=True).reset_index(drop=True)
            dates = df_recent['日期'].tolist()
            stock_cols = [col for col in df.columns if col not in ['日期', '日期_dt', '距离']]

            # ===== 2. 重新计算统计数据 =====
            code_indices = {}
            for r_idx, row in df_recent.iterrows():
                for col in stock_cols:
                    val = row[col]
                    if pd.notna(val):
                        try:
                            code = str(int(val)).zfill(6)
                        except:
                            continue
                        if code not in code_indices:
                            code_indices[code] = []
                        code_indices[code].append(r_idx)

            # 存储为实例变量，供其他方法使用
            self.stock_stats = {}
            last_row_idx = len(df_recent) - 1
            for code, indices in code_indices.items():
                total_count = len(indices)
                consecutive = 0
                if last_row_idx in indices:
                    consecutive = 1
                    for i in range(last_row_idx - 1, -1, -1):
                        if i in indices:
                            consecutive += 1
                        else:
                            break
                first_time = False
                if last_row_idx in indices:
                    if (last_row_idx - 1) not in indices:
                        first_time = True
                self.stock_stats[code] = {
                    'count': total_count,
                    'consecutive': consecutive,
                    'first_time': first_time
                }

            # ===== 3. 分类统计 =====
            stats_categories = {
                "10天中出现7次以上": [],
                "10天中出现6次": [],
                "10天中出现5次": [],
                "10天中出现4次": [],
                "连续出现5次以上": [],
                "连续出现4次": [],
                "连续出现3次": [],
                "连续出现2次": []
            }

            for code, stats in self.stock_stats.items():
                cnt = stats['count']
                cons = stats['consecutive']
                # 频率统计
                if cnt >= 7:
                    stats_categories["10天中出现7次以上"].append(code)
                elif cnt == 6:
                    stats_categories["10天中出现6次"].append(code)
                elif cnt == 5:
                    stats_categories["10天中出现5次"].append(code)
                elif cnt == 4:
                    stats_categories["10天中出现4次"].append(code)
                # 连续统计
                if cons >= 5:
                    stats_categories["连续出现5次以上"].append(code)
                elif cons == 4:
                    stats_categories["连续出现4次"].append(code)
                elif cons == 3:
                    stats_categories["连续出现3次"].append(code)
                elif cons == 2:
                    stats_categories["连续出现2次"].append(code)

            # ===== 4. 更新 stat_tb =====
            max_codes = max([len(v) for v in stats_categories.values()]) if stats_categories else 0
            col_count = 2 + max_codes
            self.stat_tb.clear()
            self.stat_tb.setRowCount(len(stats_categories))
            self.stat_tb.setColumnCount(col_count)
            headers = ["统计类型", "数量"] + [f"代码{i + 1}" for i in range(max_codes)]
            self.stat_tb.setHorizontalHeaderLabels(headers)
            self.stat_tb.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.stat_tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            for col in range(2, col_count):
                self.stat_tb.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
                self.stat_tb.setColumnWidth(col, 80)

            for row, (cat_name, codes) in enumerate(stats_categories.items()):
                item_cat = QTableWidgetItem(cat_name)
                item_cat.setTextAlignment(QtCore.Qt.AlignCenter)
                self.stat_tb.setItem(row, 0, item_cat)

                item_cnt = QTableWidgetItem(str(len(codes)))
                item_cnt.setTextAlignment(QtCore.Qt.AlignCenter)
                self.stat_tb.setItem(row, 1, item_cnt)

                for col_idx, code in enumerate(codes):
                    if self.show_name_mode:
                        display_text = self.code_name_map.get(code, code)
                    else:
                        display_text = code
                    item_code = QTableWidgetItem(display_text)
                    item_code.setTextAlignment(QtCore.Qt.AlignCenter)
                    item_code.setForeground(QtGui.QColor("darkblue"))
                    item_code.setData(QtCore.Qt.UserRole, code)
                    self.stat_tb.setItem(row, 2 + col_idx, item_code)

            # ===== 5. 更新 stock_tb =====
            self.stock_tb.clear()
            self.stock_tb.setColumnCount(len(dates))
            self.stock_tb.setRowCount(len(stock_cols))
            self.stock_tb.setHorizontalHeaderLabels(dates)
            self.stock_tb.setVerticalHeaderLabels(stock_cols)
            self.stock_tb.horizontalHeader().setDefaultSectionSize(100)
            self.stock_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

            for col_idx in range(len(dates)):
                row_data = df_recent.iloc[col_idx]
                for row_idx, col_name in enumerate(stock_cols):
                    val = row_data[col_name]
                    if pd.notna(val):
                        try:
                            code_str = str(int(val)).zfill(6)
                        except:
                            code_str = str(val)
                        if self.show_name_mode:
                            display_text = self.code_name_map.get(code_str, code_str)
                        else:
                            display_text = code_str
                        item = QTableWidgetItem(display_text)
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        item.setForeground(QtGui.QColor("darkblue"))
                        item.setData(QtCore.Qt.UserRole, code_str)
                        self.stock_tb.setItem(row_idx, col_idx, item)

            self.update_code_color_map()
            self.apply_colors_to_tables()
            self.stock_tb.clear_connections()
            # 清空次数显示
            self.stock_count_label.setText("")
            print(f"✅ 表格已加载: 最近 {len(dates)} 个日期, 统计分析完成")
        except Exception as e:
            print(f"❌ 加载表格出错: {e}")
            import traceback
            traceback.print_exc()

    def get(self):
        """从指定路径读取 .blk 文件，提取股票代码并保存到 CSV。"""
        # 检查路径是否加载成功
        if not self.tdx_path:
            print("❌ 通达信路径未配置，请检查 setup.json")
            return

        # 使用 self.tdx_path 动态拼接路径
        blk_path = os.path.join(self.tdx_path, 'T0002', 'blocknew', '669WRC120RXG.blk')
        save_path = 'data/cxg669.csv'

        if not os.path.exists(blk_path):
            print(f"❌ 文件未找到: {blk_path}")
            return

        try:
            codes = []
            with open(blk_path, 'r', encoding='gbk') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if len(line) >= 6:
                        code_part = line[-6:]
                        if code_part.isdigit():
                            codes.append(code_part)

            if not codes:
                return

            today_str = datetime.now().strftime('%Y-%m-%d')
            os.makedirs('data', exist_ok=True)

            if os.path.exists(save_path):
                try:
                    df_old = pd.read_csv(save_path, encoding='utf-8-sig')
                except:
                    df_old = pd.DataFrame()
            else:
                df_old = pd.DataFrame()

            new_cols = ['日期'] + [f'股票{i + 1}' for i in range(len(codes))]
            new_row_df = pd.DataFrame([[today_str] + codes], columns=new_cols)

            if not df_old.empty:
                if today_str in df_old['日期'].values:
                    df_old = df_old[df_old['日期'] != today_str]
                df_combined = pd.concat([df_old, new_row_df], ignore_index=True)
            else:
                df_combined = new_row_df

            df_combined.to_csv(save_path, index=False, encoding='utf-8-sig')
            print(f"✅ 数据已保存至: {save_path}")

        except Exception as e:
            print(f"❌ 处理 .blk 文件时出错: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    ui = MainWindow()
    ui.setupUi(window)
    if os.path.exists('data/cxg669.csv'):
        ui.load_stock_tb()
    window.show()
    sys.exit(app.exec_())
