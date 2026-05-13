# -*- coding: utf-8 -*-
import sys
import os
import re
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QHeaderView, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem

from link_tdx import link_tdx, get_tdx_path
import json


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        # 设置初始大小，允许用户调整
        MainWindow.resize(1720, 1350)

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
        # ================= 修改结束 =================

        # ================= 布局管理重构 =================
        # 创建主垂直布局，管理所有控件的垂直堆叠
        main_layout = QVBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # 边距
        main_layout.setSpacing(10)  # 控件间距
        # ================= 修改结束 =================

        # --- Banner ---
        self.banner = QtWidgets.QLabel(self.centralwidget)
        # 移除 setGeometry，改用固定高度
        self.banner.setFixedHeight(60)
        font = QtGui.QFont()
        font.setFamily("迷你简汉真广标")
        font.setPointSize(20)
        font.setBold(False)
        font.setWeight(50)
        font.setKerning(False)
        self.banner.setFont(font)
        self.banner.setStyleSheet("color: white;\nbackground-color: rgb(0, 170, 255);")
        self.banner.setAlignment(QtCore.Qt.AlignCenter)
        self.banner.setObjectName("banner")
        # 将 Banner 加入主布局
        main_layout.addWidget(self.banner)

        # --- Widget (输入框和按钮区域) ---
        self.widget = QtWidgets.QWidget(self.centralwidget)
        # 移除 setGeometry
        self.widget.setObjectName("widget")

        # Widget 内部的水平布局
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")

        # 输入框控件
        self.input_stock_lable = QtWidgets.QLabel(self.widget)
        font_label = QtGui.QFont()
        font_label.setFamily("SimHei")
        font_label.setPointSize(14)
        font_label.setBold(True)
        self.input_stock_lable.setFont(font_label)
        self.input_stock_lable.setStyleSheet("color: green;")
        self.input_stock_lable.setObjectName("input_stock_lable")

        self.input_stock = QtWidgets.QLineEdit(self.widget)
        self.input_stock.setInputMask("")
        self.input_stock.setText("")
        self.input_stock.setObjectName("input_stock")
        font_input = QtGui.QFont()
        font_input.setFamily("SimHei")
        font_input.setPointSize(14)
        self.input_stock.setFont(font_input)
        self.input_stock.setStyleSheet("color: blue;")
        self.input_stock.setFixedHeight(30)

        # 计算宽度
        font_calc = QtGui.QFont("Arial", 14)
        font_metrics = QtGui.QFontMetrics(font_calc)
        char_width = font_metrics.width("000000")
        self.input_stock.setFixedWidth(char_width)

        self.start_input = QtWidgets.QLineEdit(self.widget)
        self.start_input.setInputMask("")
        self.start_input.setText("1")
        self.start_input.setObjectName("start_input")
        font_input = QtGui.QFont()
        font_input.setFamily("SimHei")
        font_input.setPointSize(14)
        self.start_input.setFont(font_input)
        self.start_input.setStyleSheet("color: blue;")
        self.start_input.setFixedHeight(30)

        font_calc = QtGui.QFont("Arial", 20, QtGui.QFont.Bold)
        font_metrics = QtGui.QFontMetrics(font_calc)
        digit_width = font_metrics.width("000")
        self.start_input.setMinimumWidth(digit_width)
        self.start_input.setFixedWidth(digit_width)

        self.label_4 = QtWidgets.QLabel(self.widget)
        font = QtGui.QFont()
        font.setFamily("阿里巴巴普惠体 M")
        font.setPointSize(12)
        self.label_4.setFont(font)
        self.label_4.setObjectName("label_4")

        self.end_input = QtWidgets.QLineEdit(self.widget)
        self.end_input.setInputMask("")
        self.end_input.setText("")
        self.end_input.setObjectName("end_input")
        font_input = QtGui.QFont()
        font_input.setFamily("SimHei")
        font_input.setPointSize(14)
        self.end_input.setFont(font_input)
        self.end_input.setStyleSheet("color: blue;")
        self.end_input.setFixedHeight(30)

        self.end_input.setMinimumWidth(digit_width)
        self.end_input.setFixedWidth(digit_width)

        # 左侧布局：输入代码标签 + 输入框
        left_layout = QtWidgets.QHBoxLayout()
        left_layout.setSpacing(5)
        left_layout.addWidget(self.input_stock_lable)
        left_layout.addWidget(self.input_stock)

        # 右侧布局：起始行 + 到 + 结束行
        right_layout = QtWidgets.QHBoxLayout()
        right_layout.setSpacing(5)
        right_layout.addWidget(self.start_input)
        right_layout.addWidget(self.label_4)
        right_layout.addWidget(self.end_input)

        self.horizontalLayout.addLayout(left_layout)

        # 添加间距
        spacer_big = QtWidgets.QSpacerItem(100, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacer_big)

        self.horizontalLayout.addLayout(right_layout)

        # 按钮
        self.statics = QtWidgets.QPushButton(self.widget)
        font = QtGui.QFont()
        font.setFamily("阿里巴巴普惠体 M")
        font.setPointSize(12)
        self.statics.setFont(font)
        self.statics.setStyleSheet("color: red;")
        self.statics.setObjectName("statics")
        self.horizontalLayout.addWidget(self.statics)

        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)

        self.add_auto = QtWidgets.QPushButton(self.widget)
        font = QtGui.QFont()
        font.setFamily("阿里巴巴普惠体 M")
        font.setPointSize(12)
        self.add_auto.setFont(font)
        self.add_auto.setStyleSheet("color: green;")
        self.add_auto.setObjectName("add_auto")
        self.horizontalLayout.addWidget(self.add_auto)

        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)

        self.stop_auto = QtWidgets.QPushButton(self.widget)
        font = QtGui.QFont()
        font.setFamily("阿里巴巴普惠体 M")
        font.setPointSize(12)
        self.stop_auto.setFont(font)
        self.stop_auto.setObjectName("stop_auto")
        self.horizontalLayout.addWidget(self.stop_auto)

        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem2)

        self.update_gn = QtWidgets.QPushButton(self.widget)
        font = QtGui.QFont()
        font.setFamily("阿里巴巴普惠体 M")
        font.setPointSize(12)
        self.update_gn.setFont(font)
        self.update_gn.setObjectName("update_gn")
        self.horizontalLayout.addWidget(self.update_gn)

        self.update_gn_list = QtWidgets.QLabel(self.widget)
        self.update_gn_list.setObjectName("update_gn_list")
        self.horizontalLayout.addWidget(self.update_gn_list)

        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem3)

        self.update_news = QtWidgets.QPushButton(self.widget)
        font = QtGui.QFont()
        font.setFamily("阿里巴巴普惠体 M")
        font.setPointSize(12)
        self.update_news.setFont(font)
        self.update_news.setObjectName("update_news")
        self.horizontalLayout.addWidget(self.update_news)

        self.update_news_list = QtWidgets.QLabel(self.widget)
        self.update_news_list.setObjectName("update_news_list")
        self.horizontalLayout.addWidget(self.update_news_list)

        # 将 Widget 加入主布局
        main_layout.addWidget(self.widget)

        # --- 板块表格 ---
        self.blk_tb = QtWidgets.QTableWidget(self.centralwidget)
        self.blk_tb.setObjectName("blk_tb")
        self.blk_tb.setColumnCount(9)
        self.blk_tb.setRowCount(0)
        # 设置最小高度，避免太小
        self.blk_tb.setMinimumHeight(500)

        for i in range(10):
            item = QtWidgets.QTableWidgetItem()
            self.blk_tb.setHorizontalHeaderItem(i, item)

        # 将板块表格加入主布局
        main_layout.addWidget(self.blk_tb)

        # --- 股票表格 ---
        self.stock_tb = QtWidgets.QTableWidget(self.centralwidget)
        self.stock_tb.setObjectName("stock_tb")
        self.stock_tb.setColumnCount(53)
        self.stock_tb.setRowCount(0)
        # 设置最小高度，给予足够的展示空间
        self.stock_tb.setMinimumHeight(700)

        for i in range(53):
            item = QtWidgets.QTableWidgetItem()
            self.stock_tb.setHorizontalHeaderItem(i, item)

        self.stock_tb.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)

        # 将股票表格加入主布局
        main_layout.addWidget(self.stock_tb)

        # 添加一个弹簧，将所有内容推到顶部，避免底部被拉伸得太奇怪
        main_layout.addStretch()

        # 菜单栏和状态栏设置保持不变
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

        # 板块表格
        self.blk_tb.setColumnCount(9)
        self.blk_tb.setHorizontalHeaderLabels(
            ["板块代码", "板块名称", "概念重复次数", "新闻列表", "重磅程序", "板块热度", "昨涨幅", "昨板比率", "连涨天"]
        )
        blk_column_widths = [80, 100, 120, 450, 100, 100, 100, 100, 100]
        for col, width in enumerate(blk_column_widths):
            self.blk_tb.setColumnWidth(col, width)
        self.blk_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

        # 股票表格
        self.stock_tb.setColumnCount(50)
        headers = ["时间", "代码", "名称"]
        for i in range(1, 47):
            headers.append(f"概念{i}")
        headers.append("其他")
        self.stock_tb.setHorizontalHeaderLabels(headers)

        # 设置列宽（由于总宽度很大，配合QScrollArea会出现横向滚动条，这是正常的）
        for col in range(self.stock_tb.columnCount()):
            self.stock_tb.setColumnWidth(col, 75)

        self.stock_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "概念热度分析"))
        self.banner.setText(_translate("MainWindow", "概念热度分析，短线套利助手！"))
        self.input_stock_lable.setText(_translate("MainWindow", "输入代码"))
        self.input_stock.setPlaceholderText(_translate("MainWindow", "股票代码"))
        self.start_input.setPlaceholderText(_translate("MainWindow", "行"))
        self.label_4.setText(_translate("MainWindow", "到"))
        self.end_input.setPlaceholderText(_translate("MainWindow", "行"))
        self.statics.setText(_translate("MainWindow", "统计"))
        self.add_auto.setText(_translate("MainWindow", "自动添加"))
        self.stop_auto.setText(_translate("MainWindow", "停止自动"))
        self.update_gn.setText(_translate("MainWindow", "更新所属概念"))
        self.update_gn_list.setText(_translate("MainWindow", ""))
        self.update_news.setText(_translate("MainWindow", "更新新闻"))
        self.update_news_list.setText(_translate("MainWindow", "打印更新信息"))


# 在 class Ui_MainWindow 之后，新增一个逻辑类
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.init_tables()
        # ================= 初始化内存缓存变量 =================
        self.df_stocks = None
        self.df_news_stat = None
        self.exclude_words = set()
        self.yes_words = set()
        self.blkfile_path = ""
        self.row_number_counter = 0

        # 首次启动时加载所有资源到内存
        self.load_resources()
        global WM_STOCK_MSG
        # WM_STOCK_MSG = user32.RegisterWindowMessageA(b"Stock")
        # if WM_STOCK_MSG == 0:
        #     print("⚠️ 注册 'Stock' 消息失败")
        # else:
        #     print(f"✅ 已注册 'Stock' 消息，ID: {WM_STOCK_MSG}")

        # 绑定按钮事件
        self.update_gn.clicked.connect(self.on_update_gn_clicked)

        # 限制 input_stock：6位数字（允许前导零）
        self.input_stock.setMaxLength(6)
        self.input_stock.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(r'^\d{0,6}$')))

        # 限制 start_input 和 end_input：只能输入正整数（行号）
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        self.start_input.setValidator(int_validator)
        self.end_input.setValidator(int_validator)

        # ================= 绑定回车事件 =================
        self.input_stock.returnPressed.connect(self.on_stock_code_enter)

        # ================= 表格滚动设置 =================
        self.stock_tb.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.stock_tb.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.stock_tb.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.stock_tb.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

        # ==============================================================

        self.stock_tb.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.stock_tb.installEventFilter(self)
        self.statics.clicked.connect(lambda: self.on_manual_add(silent=False))

        # ================= 自动添加初始化 =================
        self.is_auto_running = True
        self.last_line_index = 0

        self.auto_timer = QtCore.QTimer(self)
        self.auto_timer.timeout.connect(self.run_auto_scan)

        self.add_auto.clicked.connect(self.toggle_auto_add)
        self.stop_auto.clicked.connect(self.stop_auto_add)

        self.add_auto.setText("自动中")
        self.auto_timer.start(5000)

        # 连接单元格点击事件
        self.stock_tb.cellClicked.connect(self.on_stock_cell_clicked)

    def on_stock_cell_clicked(self, row, column):
        if column != 1:
            return
        item = self.stock_tb.item(row, column)
        if not item:
            return
        code = item.text().strip()
        if not code.isdigit() or len(code) != 6:
            return

        # 直接调用导入的 link_tdx 函数
        link_tdx(code)

    def load_resources(self):
        """加载所有配置文件和数据到内存，提高处理速度"""
        file_path = 'data/stock_gn.csv'
        if os.path.exists(file_path):
            try:
                self.df_stocks = pd.read_csv(file_path, dtype=str, encoding='utf-8-sig')
                if '代码' in self.df_stocks.columns:
                    self.df_stocks['代码'] = self.df_stocks['代码'].astype(str).str.zfill(6)
                print("✅ 已加载 stock_gn.csv 到内存")
            except Exception as e:
                print(f"❌ 加载 stock_gn.csv 失败: {e}")
                self.df_stocks = pd.DataFrame()
        else:
            print(f"⚠️ data/stock_gn.csv 不存在")
            self.df_stocks = pd.DataFrame()

        file_path = 'data/news_stat.csv'
        if os.path.exists(file_path):
            try:
                self.df_news_stat = pd.read_csv(file_path, dtype=str)
                print(f"✅ 已加载 news_stat.csv 到内存，共 {len(self.df_news_stat)} 条记录")
            except Exception as e:
                print(f"❌ 加载 news_stat.csv 失败: {e}")
                self.df_news_stat = pd.DataFrame()
        else:
            print(f"⚠️ news_stat.csv 不存在")
            self.df_news_stat = pd.DataFrame()

        try:
            if os.path.exists("set_key.txt"):
                with open("set_key.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                    self.exclude_words = set(word for word in content.split() if word.strip())
                    print(f"✅ 已加载排除词 ({len(self.exclude_words)} 个)")
        except Exception as e:
            print(f"❌ 读取 set_key.txt 失败: {e}")

        self.yes_words = set()
        self.blkfile_path = None
        try:
            if os.path.exists("setup.json"):
                with open("setup.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.yes_words = set(word for word in config.get('yesword', '').split() if word.strip())
                    self.blkfile_path = config.get('blkfile', '').strip()
                print(f"✅ 已加载配置: 强调词({len(self.yes_words)}个), 扫描路径: {self.blkfile_path}")
        except Exception as e:
            print(f"❌ 读取 setup.json 失败: {e}")

    def toggle_auto_add(self):
        """切换自动添加的 启动/暂停 状态"""
        if self.is_auto_running:
            self.auto_timer.stop()
            self.add_auto.setText("自动添加")
            self.is_auto_running = False
        else:
            self.add_auto.setText("自动中")
            self.auto_timer.start(5000)
            self.is_auto_running = True

    def stop_auto_add(self):
        """强制停止自动添加"""
        if self.is_auto_running:
            self.auto_timer.stop()
            self.add_auto.setText("自动添加")
            self.is_auto_running = False

    def get_blkfile_path(self):

        setup_file = "setup.json"
        if os.path.exists(setup_file):
            try:
                with open(setup_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('blkfile', '').strip()
            except Exception as e:
                print(f"读取 setup.json 中的 blkfile 失败: {e}")
        return None

    def run_auto_scan(self):
        print(f"[DEBUG] run_auto_scan called. Current last_line_index: {self.last_line_index}")
        if not self.blkfile_path or not os.path.exists(self.blkfile_path):
            print("[DEBUG] blkfile path is invalid or does not exist.")
            return
        try:
            with open(self.blkfile_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"[DEBUG] Error reading scan file: {e}")
            return

        total_lines = len(lines)
        print(f"[DEBUG] Total lines in file now: {total_lines}")

        if total_lines < self.last_line_index:
            print("[DEBUG] File seems to have shrunk, resetting index.")
            self.last_line_index = 0

        if self.last_line_index >= total_lines:
            print(
                "[DEBUG] No new lines to process. last_line_index ({self.last_line_index}) >= total_lines ({total_lines}).")
            return

        new_lines = lines[self.last_line_index:total_lines]
        print(f"[DEBUG] Processing {len(new_lines)} new lines starting from index {self.last_line_index}")

        for line_num, line in enumerate(new_lines):
            content = line.strip()
            print(f"[DEBUG] Processing new line {self.last_line_index + line_num}: '{content}'")
            if len(content) >= 6:
                code_str = content[-6:]
                print(f"[DEBUG] Extracted code: '{code_str}'")
                if code_str.isdigit():
                    print(f"[DEBUG] Attempting to add code: {code_str}")
                    self._add_stock_by_code(code_str)
                else:
                    print(f"[DEBUG] Extracted code '{code_str}' is not all digits, skipping.")
            else:
                print(f"[DEBUG] Line '{content}' is too short (< 6 chars), skipping.")

    def _add_stock_by_code(self, input_code):
        """内部方法：通过代码添加股票，不处理 UI 输入框交互"""
        if not input_code:
            return

        input_code = str(input_code).zfill(6)

        code_exists = False
        for r in range(self.stock_tb.rowCount()):
            item = self.stock_tb.item(r, 1)
            if item and item.text() == input_code:
                code_exists = True
                break

        if code_exists:
            return

        if self.df_stocks is None or self.df_stocks.empty:
            return
        try:
            matched_rows = self.df_stocks[self.df_stocks['代码'] == input_code]

            if matched_rows.empty:
                return

            row_data = matched_rows.iloc[0]

            current_row = self.stock_tb.rowCount()
            self.stock_tb.insertRow(current_row)

            current_time = QtCore.QDateTime.currentDateTime().toString("hh:mm:ss")
            time_item = QtWidgets.QTableWidgetItem(current_time)
            time_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.stock_tb.setItem(current_row, 0, time_item)

            code_item = QtWidgets.QTableWidgetItem(str(row_data.get('代码', '')))
            code_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.stock_tb.setItem(current_row, 1, code_item)

            name_item = QtWidgets.QTableWidgetItem(str(row_data.get('名称', '')))
            name_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.stock_tb.setItem(current_row, 2, name_item)

            for i in range(1, 47):
                col_idx = i + 2
                col_name = f'概念{i}'

                val = row_data.get(col_name)
                if pd.isna(val):
                    val = ""

                item = QtWidgets.QTableWidgetItem(str(val))
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.stock_tb.setItem(current_row, col_idx, item)

            self.stock_tb.sortItems(0, QtCore.Qt.AscendingOrder)
            self.stock_tb.scrollToBottom()
            self._refresh_stock_table_colors()
            self.on_manual_add(silent=True)

        except Exception as e:
            print(f"自动添加股票 {input_code} 失败: {str(e)}")

    def sort_stock_tb_by_index_desc(self):
        """将stock_tb按行索引号倒序排列（最新行在顶部）"""
        row_count = self.stock_tb.rowCount()
        if row_count <= 1:
            return

        rows_data = []
        for row in range(row_count):
            row_data = []
            for col in range(self.stock_tb.columnCount()):
                item = self.stock_tb.takeItem(row, col)
                row_data.append(item)
            rows_data.append(row_data)

        self.stock_tb.setRowCount(0)
        for row_data in reversed(rows_data):
            row = self.stock_tb.rowCount()
            self.stock_tb.insertRow(row)
            for col, item in enumerate(row_data):
                self.stock_tb.setItem(row, col, item)

        self.stock_tb.scrollToTop()

    def eventFilter(self, obj, event):
        """事件过滤器：监听 stock_tb 中的键盘按下事件"""
        if obj == self.stock_tb and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Delete:
                self.delete_selected_rows()
                return True
        return super().eventFilter(obj, event)

    def delete_selected_rows(self):
        """删除 stock_tb 中选中的行"""
        selected_indexes = self.stock_tb.selectionModel().selectedRows()
        if not selected_indexes:
            return

        rows_to_delete = sorted(set(index.row() for index in selected_indexes), reverse=True)

        for row in rows_to_delete:
            self.stock_tb.removeRow(row)

        self._refresh_stock_table_colors()
        self.on_manual_add(silent=True)

    def on_manual_add(self, silent=False):
        """统计：统计指定行范围内的概念重复次数，并填充到 blk_tb"""
        start_text = self.start_input.text().strip()
        end_text = self.end_input.text().strip()

        total_rows = self.stock_tb.rowCount()
        if total_rows == 0:
            self.blk_tb.setRowCount(0)
            if not silent:
                QtWidgets.QMessageBox.warning(self, "提示", "表格为空，无法统计")
            return

        if silent:
            start_row = 1
            end_row = total_rows
        else:
            start_row = 1
            end_row = total_rows
            if start_text or end_text:
                try:
                    start_row = int(start_text) if start_text else 1
                    end_row = int(end_text) if end_text else total_rows
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, "错误", "行号必须是数字")
                    return

        if start_row < 1 or end_row > total_rows:
            if not silent:
                QtWidgets.QMessageBox.warning(self, "错误", f"行号超出范围 (1 - {total_rows})")
            return
        if start_row > end_row:
            if not silent:
                QtWidgets.QMessageBox.warning(self, "错误", "开始行不能大于结束行")
            return

        exclude_words = set()
        try:
            if os.path.exists("set_key.txt"):
                with open("set_key.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                    exclude_words = set(word for word in content.split() if word.strip())
        except Exception as e:
            print(f"读取 set_key.txt 失败: {e}")

        concept_counts = {}

        for r in range(start_row - 1, end_row):
            for c in range(3, 53):
                item = self.stock_tb.item(r, c)
                if item:
                    concept = item.text().strip()
                    if concept and concept not in exclude_words:
                        concept_counts[concept] = concept_counts.get(concept, 0) + 1

        if not concept_counts:
            if not silent:
                QtWidgets.QMessageBox.information(self, "提示", "在指定范围内未找到任何概念")
            self.blk_tb.setRowCount(0)
            return

        sorted_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)
        filtered_concepts = [(concept, count) for concept, count in sorted_concepts if count > 1]

        if not filtered_concepts:
            if not silent:
                QtWidgets.QMessageBox.information(self, "提示", "在指定范围内未找到重复的概念（所有概念仅出现一次）")
            self.blk_tb.setRowCount(0)
            return

        has_news_data = (self.df_news_stat is not None and
                         not self.df_news_stat.empty and
                         '名称' in self.df_news_stat.columns and
                         '板块热度' in self.df_news_stat.columns)

        self.blk_tb.setRowCount(0)
        self.blk_tb.setRowCount(len(filtered_concepts))

        for r, (concept, count) in enumerate(filtered_concepts):
            name_item = QtWidgets.QTableWidgetItem(concept)
            name_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.blk_tb.setItem(r, 1, name_item)

            count_item = QtWidgets.QTableWidgetItem(str(count))
            count_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.blk_tb.setItem(r, 2, count_item)

            if has_news_data:
                matched_row = self.df_news_stat[self.df_news_stat['名称'] == concept]
                if not matched_row.empty:
                    row_data = matched_row.iloc[0]

                    news_val = row_data.get('新闻列表', '')
                    news_item = QtWidgets.QTableWidgetItem(str(news_val))
                    self.blk_tb.setItem(r, 3, news_item)

                    if news_val:
                        font = self.blk_tb.font()
                        font_metrics = QtGui.QFontMetrics(font)
                        col_width = self.blk_tb.columnWidth(3)
                        text_rect = font_metrics.boundingRect(
                            0, 0, col_width, 10000, QtCore.Qt.TextWordWrap, str(news_val)
                        )
                        self.blk_tb.setRowHeight(r, text_rect.height() + 10)

                    zh_val = row_data.get('重磅程度', '')
                    self.blk_tb.setItem(r, 4, QtWidgets.QTableWidgetItem(str(zh_val)))

                    hot_val = row_data.get('板块热度', '')
                    self.blk_tb.setItem(r, 5, QtWidgets.QTableWidgetItem(str(hot_val)))

                    rise_val = row_data.get('昨涨幅', '')
                    self.blk_tb.setItem(r, 6, QtWidgets.QTableWidgetItem(str(rise_val)))

                    rate_val = row_data.get('昨板比率', '')
                    self.blk_tb.setItem(r, 7, QtWidgets.QTableWidgetItem(str(rate_val)))

                    days_val = row_data.get('连涨天', '')
                    self.blk_tb.setItem(r, 8, QtWidgets.QTableWidgetItem(str(days_val)))
                else:
                    for c in [3, 4, 5, 6, 7, 8]:
                        self.blk_tb.setItem(r, c, QtWidgets.QTableWidgetItem(""))
            else:
                for c in [3, 4, 5, 6, 7, 8]:
                    self.blk_tb.setItem(r, c, QtWidgets.QTableWidgetItem(""))

    def on_update_gn_clicked(self):
        updater = update_gn()
        message = updater.update()
        self.update_gn_list.setText(message)
        print(message)
        self.load_resources()

    def on_stock_code_enter(self):
        """回车键触发：追加行到表格，并清空输入框"""
        input_code = self.input_stock.text().strip()
        if not input_code:
            return
        input_code = input_code.zfill(6)
        code_exists = False
        for r in range(self.stock_tb.rowCount()):
            item = self.stock_tb.item(r, 1)
            if item and item.text() == input_code:
                code_exists = True
                break
        if code_exists:
            print(f"错误：代码 {input_code} 已存在于表格中，已自动略过")
            self.input_stock.selectAll()
            self.input_stock.setFocus()
            return
        file_path = 'data/stock_gn.csv'
        if not os.path.exists(file_path):
            QtWidgets.QMessageBox.warning(self, "错误", f"文件不存在：{file_path}")
            return
        try:
            df = pd.read_csv(file_path, dtype=str, encoding='utf-8-sig')
            if '代码' in df.columns:
                df['代码'] = df['代码'].astype(str).str.zfill(6)
            else:
                QtWidgets.QMessageBox.warning(self, "错误", "文件中未找到 '代码' 列")
                return
            matched_rows = df[df['代码'] == input_code]
            if matched_rows.empty:
                print(f"未找到代码: {input_code}")
                self.input_stock.selectAll()
                return
            row_data = matched_rows.iloc[0]
            current_row = self.stock_tb.rowCount()
            self.stock_tb.insertRow(current_row)
            current_time = QtCore.QDateTime.currentDateTime().toString("hh:mm:ss")
            time_item = QtWidgets.QTableWidgetItem(current_time)
            time_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.stock_tb.setItem(current_row, 0, time_item)
            code_item = QtWidgets.QTableWidgetItem(str(row_data.get('代码', '')))
            code_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.stock_tb.setItem(current_row, 1, code_item)
            name_item = QtWidgets.QTableWidgetItem(str(row_data.get('名称', '')))
            name_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.stock_tb.setItem(current_row, 2, name_item)
            for i in range(1, 51):
                col_idx = i + 2
                col_name = f'概念{i}'
                val = row_data.get(col_name)
                if pd.isna(val):
                    val = ""
                item = QtWidgets.QTableWidgetItem(str(val))
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.stock_tb.setItem(current_row, col_idx, item)
            self.input_stock.clear()
            self.input_stock.setFocus()
            self.stock_tb.sortItems(0, QtCore.Qt.AscendingOrder)
            self.stock_tb.scrollToBottom()
            self._refresh_stock_table_colors()
            self.on_manual_add(silent=True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "错误", f"读取文件失败: {str(e)}")

    def _refresh_stock_table_colors(self):
        """根据规则刷新 stock_tb 的背景颜色"""
        exclude_words = set()
        try:
            if os.path.exists("set_key.txt"):
                with open("set_key.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                    exclude_words = set(word for word in content.split() if word.strip())
        except Exception as e:
            print(f"读取 set_key.txt 失败: {e}")

        emphasize_words = set()
        try:
            if os.path.exists("setup.json"):
                with open("setup.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    content = config.get('yesword', '')
                    emphasize_words = set(word for word in content.split() if word.strip())
        except Exception as e:
            print(f"读取 setup.json 失败: {e}")

        concept_counts = {}
        for r in range(self.stock_tb.rowCount()):
            for c in range(3, 53):
                item = self.stock_tb.item(r, c)
                if item:
                    concept = item.text().strip()
                    if concept and concept not in exclude_words:
                        concept_counts[concept] = concept_counts.get(concept, 0) + 1

        for r in range(self.stock_tb.rowCount()):
            for c in range(3, 53):
                item = self.stock_tb.item(r, c)
                if item:
                    concept = item.text().strip()
                    if not concept:
                        item.setBackground(QtGui.QColor("white"))
                        continue

                    bg_color = QtGui.QColor("white")

                    if concept in emphasize_words:
                        bg_color = QtGui.QColor("orange")
                    elif concept_counts.get(concept, 0) > 1:
                        bg_color = QtGui.QColor("lightgreen")
                    elif concept in exclude_words:
                        bg_color = QtGui.QColor("lightgray")

                    item.setBackground(bg_color)


class update_gn():
    # 删除了 get_from_setup 静态方法

    def extract_gn_segments(self, content: str) -> list:
        """提取概念板块段落"""
        pattern = r'#GN_(.+?)\r\n'
        segments = re.findall(pattern, content, re.DOTALL)
        return [f"#GN_{seg}" for seg in segments]

    def process_stock_concepts(self, file_path):
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
        gn_segments = self.extract_gn_segments(content)
        pattern2 = r'#GN_(.+?),'  # 提取所属概念
        pattern3 = r'\d+#\d{6}'  # 提取股票代码格式
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
        df = pd.DataFrame(stock_gn_pairs, columns=['代码', '概念'])
        return df

    def merge_stock_data(self, df):
        """合并股票概念数据"""
        grouped = df.groupby('代码')['概念'].apply(list).reset_index()
        print(f"所有股票数量： {len(grouped)}")
        max_sectors = grouped['概念'].apply(len).max()
        print(f"单个股票最多所属板块数量: {max_sectors}")
        result_data = {'代码': grouped['代码']}
        for i in range(max_sectors):
            result_data[f'概念{i + 1}'] = grouped['概念'].apply(lambda x: x[i] if i < len(x) else '')
        result_df = pd.DataFrame(result_data)
        return result_df

    def insert_stock_name(self, df, name_df):
        """插入股票名称，并确保股票代码可正确匹配"""
        df = df.copy()
        name_df = name_df.copy()
        df['代码'] = df['代码'].astype(str).str.zfill(6)
        name_df['代码'] = name_df['代码'].astype(str).str.zfill(6)
        name_df = name_df.drop_duplicates(subset=['代码'], keep='first')
        merged_df = df.merge(name_df[['代码', '名称']], on='代码', how='left')
        cols = ['代码', '名称'] + [col for col in merged_df.columns if col.startswith('概念')]
        merged_df = merged_df[cols]
        return merged_df

    def update(self):
        try:
            TDX_PATH = get_tdx_path()
            if not TDX_PATH:
                return "❌ 错误：未找到 TDX_PATH 配置，请检查 setup.json 文件"
            file_path = os.path.join(TDX_PATH, 'T0002', 'hq_cache', 'infoharbor_block.dat')
            if not os.path.exists(file_path):
                return f"❌ 文件不存在：{file_path}"
            df = self.process_stock_concepts(file_path)
            if df is None or df.empty:
                return "⚠️ 未提取到任何股票概念数据，请检查 infoharbor_block.dat 内容"
            processed_df = self.merge_stock_data(df)
            if processed_df.empty:
                return "⚠️ 合并后的数据为空"
            name_file = 'data/stock_name.csv'
            if not os.path.exists(name_file):
                return f"❌ 股票名称文件未找到：{name_file}"

            # 读取CSV（列名已经是"代码"和"名称"）
            name_df = pd.read_csv(name_file, dtype={'代码': str}, encoding='utf-8-sig')

            final_df = self.insert_stock_name(processed_df, name_df)
            final_df['代码'] = pd.to_numeric(final_df['代码'], errors='coerce').astype('Int64')
            final_df.to_csv('data/stock_gn.csv', index=False, encoding='utf-8-sig')
            return f"✅ 所属概念文件已成功保存！共处理 {len(final_df)} 只股票"
        except Exception as e:
            return f"💥 处理过程中发生错误: {str(e)}"


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
