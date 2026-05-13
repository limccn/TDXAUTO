# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import sys
import os
import pandas as pd
import json
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QSpacerItem, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, \
    QCheckBox, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from data_update import update
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import rcParams
from link_tdx import link_tdx

rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

# ==================== 通达信联接功能 ====================


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1750, 1350)
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
        # self.btn_1_month.clicked = True



        spacer_quick = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacer_quick)

        # ================= 日期范围分析相关控件 =================
        self.start_date_label = QtWidgets.QLabel(self.widget)
        font_label = QtGui.QFont()
        font_label.setFamily("SimHei")
        font_label.setPointSize(12)
        self.start_date_label.setFont(font_label)
        self.start_date_label.setObjectName("start_date_label")
        self.start_date_input = QtWidgets.QLineEdit(self.widget)

        today = datetime.now()
        self.start_date_input.setText((today - timedelta(days=30)).strftime('%Y-%m-%d'))


        self.start_date_input.setFixedWidth(100)
        self.start_date_input.setObjectName("start_date_input")
        self.end_date_label = QtWidgets.QLabel(self.widget)
        self.end_date_label.setFont(font_label)
        self.end_date_label.setObjectName("end_date_label")
        self.end_date_input = QtWidgets.QLineEdit(self.widget)
        self.end_date_input.setText(today.strftime('%Y-%m-%d'))
        self.end_date_input.setFixedWidth(100)
        self.end_date_input.setObjectName("end_date_input")
        self.analyze_btn = QtWidgets.QPushButton(self.widget)
        self.analyze_btn.setObjectName("analyze_btn")




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

        # ================= 更新信息显示区 =================
        self.update_info_label = QtWidgets.QLabel(self.widget)
        self.update_info_label.setObjectName("update_info_label")
        self.update_info_label.setStyleSheet(
            "color: #0066cc; font-weight: bold; padding: 5px; "
            "background-color: #e6f2ff; border-radius: 3px; border: 1px solid #b3d4fc;"
        )
        self.horizontalLayout.addWidget(self.update_info_label)

        main_layout.addWidget(self.widget)

        # ================= 勾选区域 =================
        self.checkbox_widget = QtWidgets.QWidget()
        checkbox_layout = QHBoxLayout(self.checkbox_widget)
        checkbox_layout.setContentsMargins(5, 5, 5, 5)
        checkbox_layout.setSpacing(15)

        checkbox_label = QtWidgets.QLabel("显示指标：")
        checkbox_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        checkbox_layout.addWidget(checkbox_label)

        self.cb_emotion = QCheckBox("情绪高度")
        self.cb_emotion.setChecked(True)
        self.cb_emotion.setStyleSheet("font-size: 11px; color: #FF6B6B;")
        checkbox_layout.addWidget(self.cb_emotion)

        self.cb_up_rate = QCheckBox("上涨率")
        self.cb_up_rate.setStyleSheet("font-size: 11px; color: purple;")
        checkbox_layout.addWidget(self.cb_up_rate)

        self.cb_down_rate = QCheckBox("下跌率")
        self.cb_down_rate.setStyleSheet("font-size: 11px; color: #4876FF;")
        checkbox_layout.addWidget(self.cb_down_rate)

        self.cb_zt_count = QCheckBox("涨停数")
        self.cb_zt_count.setStyleSheet("font-size: 11px; color: #FF00FF;")
        checkbox_layout.addWidget(self.cb_zt_count)

        self.cb_dt_count = QCheckBox("跌停数")
        self.cb_dt_count.setStyleSheet("font-size: 11px; color: #00AA00;")
        checkbox_layout.addWidget(self.cb_dt_count)

        self.cb_volume_change = QCheckBox("成交增幅")
        self.cb_volume_change.setStyleSheet("font-size: 11px; color: #FF8C00;")
        checkbox_layout.addWidget(self.cb_volume_change)

        self.cb_hot_concept = QCheckBox("最火概念")
        self.cb_hot_concept.setStyleSheet("font-size: 11px; color: #9932CC;")
        checkbox_layout.addWidget(self.cb_hot_concept)

        self.current_concept_label = QtWidgets.QLabel("当前概念: 无")
        self.current_concept_label.setStyleSheet("font-size: 11px; color: #9932CC; font-weight: bold;")
        checkbox_layout.addWidget(self.current_concept_label)

        checkbox_layout.addStretch()

        self.checkbox_widget.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        main_layout.addWidget(self.checkbox_widget)

        # ================= 图表区域 =================
        self.chart_widget = QtWidgets.QWidget()
        chart_layout = QVBoxLayout(self.chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(5)

        self.figure = Figure(figsize=(12, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)

        self.chart_widget.setMinimumHeight(600)
        main_layout.addWidget(self.chart_widget, stretch=3)

        # ================= 表格区域 =================
        self.tables_widget = QtWidgets.QWidget()
        tables_h_layout = QHBoxLayout(self.tables_widget)
        tables_h_layout.setContentsMargins(0, 0, 0, 0)
        tables_h_layout.setSpacing(10)

        # === 左侧区域 ===
        self.left_tables_widget = QtWidgets.QWidget()
        left_v_layout = QVBoxLayout(self.left_tables_widget)
        left_v_layout.setContentsMargins(0, 0, 0, 0)
        left_v_layout.setSpacing(5)

        self.date_display_label = QtWidgets.QLabel("加载中...")
        date_font = QtGui.QFont()
        date_font.setFamily("SimHei")
        date_font.setPointSize(20)
        date_font.setBold(True)
        self.date_display_label.setFont(date_font)
        self.date_display_label.setStyleSheet("color: #FF0000; padding: 5px;")
        self.date_display_label.setAlignment(QtCore.Qt.AlignCenter)
        left_v_layout.addWidget(self.date_display_label)

        self.index_label = QtWidgets.QLabel("📈 大盘统计")
        self.index_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #333;")
        left_v_layout.addWidget(self.index_label)

        self.index_st = QTableWidget()
        self.index_st.setColumnCount(7)
        self.index_st.setHorizontalHeaderLabels(['上涨', '下跌', '平盘', '涨停', '跌停', '今日成交', '昨日成交'])
        self.index_st.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_font = QtGui.QFont()
        table_font.setFamily("SimHei")
        table_font.setPointSize(12)
        self.index_st.setFont(table_font)
        self.index_st.horizontalHeader().setFont(table_font)
        left_v_layout.addWidget(self.index_st)

        self.gn_label = QtWidgets.QLabel("🔥 热门概念前3")
        self.gn_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #333;")
        left_v_layout.addWidget(self.gn_label)

        self.gn_tb = QTableWidget()
        self.gn_tb.setColumnCount(6)
        self.gn_tb.setHorizontalHeaderLabels(['最火概念1', '涨停数', '最火概念2', '涨停数', '最火概念3', '涨停数'])
        self.gn_tb.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.gn_tb.setFont(table_font)
        self.gn_tb.horizontalHeader().setFont(table_font)
        left_v_layout.addWidget(self.gn_tb)

        self.left_tables_widget.setFixedWidth(600)
        tables_h_layout.addWidget(self.left_tables_widget, stretch=1)

        # === 右侧区域 ===
        self.right_tables_widget = QtWidgets.QWidget()
        right_v_layout = QVBoxLayout(self.right_tables_widget)
        right_v_layout.setContentsMargins(0, 0, 0, 0)
        right_v_layout.setSpacing(5)

        self.stock_label = QtWidgets.QLabel("🎯 连板梯队")
        self.stock_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #333;")
        right_v_layout.addWidget(self.stock_label)

        self.stock_st = QTableWidget()
        self.stock_st.setColumnCount(4)
        self.stock_st.setHorizontalHeaderLabels(['连板高度', '代码', '股票名称', '解析'])

        # 设置列宽
        header = self.stock_st.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.stock_st.setColumnWidth(0, 100)
        self.stock_st.setColumnWidth(1, 100)
        self.stock_st.setColumnWidth(2, 100)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.stock_st.setFont(table_font)
        self.stock_st.horizontalHeader().setFont(table_font)
        right_v_layout.addWidget(self.stock_st)

        tables_h_layout.addWidget(self.right_tables_widget, stretch=1)

        self.tables_widget.setMinimumHeight(300)
        main_layout.addWidget(self.tables_widget, stretch=4)

        # ================= Top5信息显示区 =================
        self.top_stocks_info = QtWidgets.QLabel(self.centralwidget)
        self.top_stocks_info.setObjectName("top_stocks_info")
        self.top_stocks_info.setWordWrap(True)
        self.top_stocks_info.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.top_stocks_info.setStyleSheet(
            "background-color: #f5f5f5; color: #333333; font-size: 13px; "
            "font-weight: bold; padding: 8px; border-radius: 5px; border: 1px solid #dcdcdc;"
        )
        main_layout.addWidget(self.top_stocks_info)

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

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "市场情绪分析"))
        self.banner.setText(_translate("MainWindow", "市场情绪、连板高度"))
        self.btn_1_week.setText(_translate("MainWindow", "近1周"))
        self.btn_2_weeks.setText(_translate("MainWindow", "近2周"))
        self.btn_1_month.setText(_translate("MainWindow", "近1月"))
        self.btn_3_months.setText(_translate("MainWindow", "近3月"))
        self.start_date_label.setText(_translate("MainWindow", "开始日期:"))
        self.end_date_label.setText(_translate("MainWindow", "结束日期:"))
        self.analyze_btn.setText(_translate("MainWindow", "分析连板高度"))
        self.update_data_btn.setText(_translate("MainWindow", "数据更新"))
        self.update_info_label.setText(_translate("MainWindow", "⏳ 等待更新..."))
        self.top_stocks_info.setText(_translate("MainWindow", "📊 期间内最活跃代码 Top 5: 暂无数据"))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.settings_file = os.path.join(os.path.dirname(__file__), 'hot_lbtt.json')

        # 定义所有勾选框及其默认值
        self.checkbox_defaults = {
            'cb_emotion': True,  # 情绪高度默认勾选
            'cb_up_rate': False,
            'cb_down_rate': False,
            'cb_zt_count': False,
            'cb_dt_count': False,
            'cb_volume_change': False,
            'cb_hot_concept': False
        }

        # 从 JSON 文件加载设置
        self.load_settings()

        self.df_stocks = None
        self.current_dates = []
        self.current_stats = {}
        self.selected_concept = None
        self.df_lbss_all = None

        # 绑定按钮
        self.analyze_btn.clicked.connect(self.on_analyze_date_clicked)
        self.analyze_btn.animateClick()



        self.update_data_btn.clicked.connect(self.on_update_data_clicked)
        self.btn_1_week.clicked.connect(lambda: self.set_date_range(days=7))
        self.btn_2_weeks.clicked.connect(lambda: self.set_date_range(days=14))
        self.btn_1_month.clicked.connect(lambda: self.set_date_range(days=30))
        self.btn_3_months.clicked.connect(lambda: self.set_date_range(days=90))

        # 绑定图表双击事件
        self.canvas.mpl_connect('button_press_event', self.on_chart_double_click)

        # 【新增】绑定表格单元格点击事件
        self.stock_st.cellClicked.connect(self.on_stock_cell_clicked)

        # 绑定复选框
        self.cb_emotion.stateChanged.connect(self.on_checkbox_changed)
        self.cb_up_rate.stateChanged.connect(self.on_checkbox_changed)
        self.cb_down_rate.stateChanged.connect(self.on_checkbox_changed)
        self.cb_zt_count.stateChanged.connect(self.on_checkbox_changed)
        self.cb_dt_count.stateChanged.connect(self.on_checkbox_changed)
        self.cb_volume_change.stateChanged.connect(self.on_checkbox_changed)
        self.cb_hot_concept.stateChanged.connect(self.on_checkbox_changed)






    def load_settings(self):
        """从 JSON 文件加载勾选框设置"""

        # 尝试读取配置文件
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)

                # 应用保存的设置到各个勾选框
                checkbox_map = {
                    'cb_emotion': self.cb_emotion,
                    'cb_up_rate': self.cb_up_rate,
                    'cb_down_rate': self.cb_down_rate,
                    'cb_zt_count': self.cb_zt_count,
                    'cb_dt_count': self.cb_dt_count,
                    'cb_volume_change': self.cb_volume_change,
                    'cb_hot_concept': self.cb_hot_concept
                }

                for name, checkbox in checkbox_map.items():
                    # 如果文件中有该设置，则使用；否则使用默认值
                    value = saved_settings.get(name, self.checkbox_defaults.get(name, False))
                    checkbox.setChecked(value)

                print(f"✅ 已加载配置文件: {self.settings_file}")
                return
            except Exception as e:
                print(f"⚠️ 读取配置文件失败: {e}，将使用默认设置")

        # 如果文件不存在或读取失败，使用默认值
        checkbox_map = {
            'cb_emotion': self.cb_emotion,
            'cb_up_rate': self.cb_up_rate,
            'cb_down_rate': self.cb_down_rate,
            'cb_zt_count': self.cb_zt_count,
            'cb_dt_count': self.cb_dt_count,
            'cb_volume_change': self.cb_volume_change,
            'cb_hot_concept': self.cb_hot_concept
        }

        for name, checkbox in checkbox_map.items():
            checkbox.setChecked(self.checkbox_defaults.get(name, False))

    def on_stock_cell_clicked(self, row, column):
        """【新增】表格单元格点击事件：点击代码列联接通达信"""
        if column == 1:  # 代码列（索引为1）
            code_item = self.stock_st.item(row, column)
            if code_item:
                code = code_item.text().strip()
                if code:
                    link_tdx(code)

    def on_checkbox_changed(self):
        """勾选状态改变时保存设置"""
        # 收集当前所有勾选框的状态
        settings_data = {
            'cb_emotion': self.cb_emotion.isChecked(),
            'cb_up_rate': self.cb_up_rate.isChecked(),
            'cb_down_rate': self.cb_down_rate.isChecked(),
            'cb_zt_count': self.cb_zt_count.isChecked(),
            'cb_dt_count': self.cb_dt_count.isChecked(),
            'cb_volume_change': self.cb_volume_change.isChecked(),
            'cb_hot_concept': self.cb_hot_concept.isChecked()
        }

        # 保存到 JSON 文件
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=4)
            print(f"💾 设置已保存")
        except Exception as e:
            print(f"❌ 保存设置失败: {e}")

        # 重绘图表
        self.redraw_chart()

    def redraw_chart(self):
        if hasattr(self, 'last_chart_data') and self.last_chart_data:
            self.draw_chart_with_data(**self.last_chart_data)

    def set_date_range(self, days):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        self.end_date_input.setText(end_date.strftime('%Y-%m-%d'))
        self.start_date_input.setText(start_date.strftime('%Y-%m-%d'))
        self.on_analyze_date_clicked()

    def on_analyze_date_clicked(self):
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

        self.plot_lianban_height(start_str, end_str)

    def on_update_data_clicked(self):
        try:
            self.update_info_label.setText("🔄 正在执行全量数据更新，请稍候...")
            QtWidgets.QApplication.processEvents()
            updater = update()
            updater.run()
            self.update_info_label.setText("✅ 全部数据更新完成")
            QtWidgets.QMessageBox.information(self, "完成", "全部数据更新完成！")
        except Exception as e:
            self.update_info_label.setText(f"❌ 更新失败: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "错误", f"更新失败: {e}")

    def on_chart_double_click(self, event):
        if event.inaxes is None:
            return

        if event.dblclick:
            x_click = event.xdata
            if x_click is None:
                return

            x_idx = int(round(x_click))
            if 0 <= x_idx < len(self.current_dates):
                clicked_date = self.current_dates[x_idx]
                date_str = clicked_date.strftime('%Y-%m-%d')

                self.date_display_label.setText(date_str)

                if x_idx in self.current_stats:
                    stats = self.current_stats[x_idx]
                    hot1 = stats.get('hot1', '')
                    if hot1:
                        self.selected_concept = hot1
                        self.current_concept_label.setText(f"当前概念: {hot1}")

                self.redraw_chart()
                self.load_tables_for_date(date_str)

    def load_tables_for_date(self, date_str):
        """加载指定日期的数据到表格"""
        # 加载解析数据
        ztjx_path = 'data/ztjx.csv'
        ztjx_map = {}
        if os.path.exists(ztjx_path):
            try:
                df_ztjx = pd.read_csv(ztjx_path, encoding='utf-8-sig')
                df_ztjx['代码'] = df_ztjx['代码'].astype(str)
                ztjx_map = dict(zip(df_ztjx['代码'], df_ztjx['解析'].fillna('')))
            except Exception as e:
                print(f"❌ 加载ztjx.csv失败: {e}")

        # 加载 stock_st
        lbtt_path = 'data/lbtt.csv'
        if os.path.exists(lbtt_path):
            try:
                df_lbtt = pd.read_csv(lbtt_path, encoding='utf-8-sig')
                df_lbtt['日期'] = pd.to_datetime(df_lbtt['日期'])
                target_date = pd.to_datetime(date_str)

                df_stock = df_lbtt[
                    (df_lbtt['日期'] == target_date) &
                    (df_lbtt['连板高度'] > 1)
                    ].copy()
                df_stock = df_stock.drop_duplicates(subset=['代码', '连板高度'])
                df_stock = df_stock.sort_values('连板高度', ascending=False)

                self.stock_st.setRowCount(0)
                analysis_col_width = self.stock_st.width() - 300

                for _, row in df_stock.iterrows():
                    r = self.stock_st.rowCount()
                    self.stock_st.insertRow(r)

                    # 填充前3列
                    for col_idx, col_name in enumerate(['连板高度', '代码', '股票名称']):
                        val = row[col_name]
                        if col_name == '代码':
                            val = str(val).zfill(6)
                        item = QTableWidgetItem(str(val))
                        item.setTextAlignment(Qt.AlignCenter)
                        self.stock_st.setItem(r, col_idx, item)

                    # 填充解析列
                    code_val = str(row['代码']).zfill(6)
                    prefix = 'sh' if code_val.startswith('6') else 'sz'
                    if not code_val.startswith(('0', '3', '6')):
                        prefix = ''
                    full_code = prefix + code_val

                    analysis_text = ztjx_map.get(full_code, '')

                    item_ana = QTableWidgetItem(analysis_text)
                    item_ana.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.stock_st.setItem(r, 3, item_ana)

                    # 计算行高
                    if analysis_text:
                        font_metrics = self.stock_st.fontMetrics()
                        chars_per_line = max(analysis_col_width // font_metrics.horizontalAdvance('字'), 10)
                        text_lines = (len(analysis_text) + chars_per_line - 1) // chars_per_line
                        row_height = max(text_lines * 22 + 10, 30)
                        self.stock_st.setRowHeight(r, row_height)
                    else:
                        self.stock_st.setRowHeight(r, 30)

                    # 【新增】设置隔行变色
                    if r % 2 == 0:
                        bg_color = QColor(240, 248, 255)  # 浅蓝色
                    else:
                        bg_color = QColor(255, 255, 255)  # 白色

                    for col in range(4):
                        item = self.stock_st.item(r, col)
                        if item:
                            item.setBackground(QBrush(bg_color))

            except Exception as e:
                print(f"❌ 加载连板股票失败: {e}")

        # 加载 index_st 和 gn_tb
        lbss_path = 'data/lbss.csv'
        if os.path.exists(lbss_path):
            try:
                df_lbss = pd.read_csv(lbss_path, encoding='utf-8-sig')
                df_lbss['日期'] = pd.to_datetime(df_lbss['日期'])
                target_date = pd.to_datetime(date_str)
                df_stat = df_lbss[df_lbss['日期'] == target_date]

                if not df_stat.empty:
                    row = df_stat.iloc[0]

                    self.index_st.setRowCount(0)
                    self.index_st.insertRow(0)
                    for col_idx, col_name in enumerate(
                            ['上涨', '下跌', '平盘', '涨停', '跌停', '今日成交', '昨日成交']):
                        item = QTableWidgetItem(str(row.get(col_name, '')))
                        item.setTextAlignment(Qt.AlignCenter)
                        self.index_st.setItem(0, col_idx, item)

                    self.gn_tb.setRowCount(0)
                    self.gn_tb.insertRow(0)
                    gn_columns = [
                        ('最火概念1', 0), ('最火概念1涨停', 1),
                        ('最火概念2', 2), ('最火概念2涨停', 3),
                        ('最火概念3', 4), ('最火概念3涨停', 5)
                    ]
                    for col_name, col_idx in gn_columns:
                        item = QTableWidgetItem(str(row.get(col_name, '')))
                        item.setTextAlignment(Qt.AlignCenter)
                        self.gn_tb.setItem(0, col_idx, item)
            except Exception as e:
                print(f"❌ 加载市场统计失败: {e}")

    def plot_lianban_height(self, start_date, end_date):
        lbtt_path = 'data/lbtt.csv'
        lbss_path = 'data/lbss.csv'

        if not os.path.exists(lbtt_path):
            print(f"⚠️ 连板数据文件不存在: {lbtt_path}")
            self.figure.clear()
            self.canvas.draw()
            return

        try:
            df = pd.read_csv(lbtt_path, encoding='utf-8-sig')
            df['日期'] = pd.to_datetime(df['日期'])

            df_lbss = pd.DataFrame()
            if os.path.exists(lbss_path):
                df_lbss = pd.read_csv(lbss_path, encoding='utf-8-sig')
                df_lbss['日期'] = pd.to_datetime(df_lbss['日期'])
                self.df_lbss_all = df_lbss

            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            mask = (df['日期'] >= start_dt) & (df['日期'] <= end_dt)
            df_filtered = df.loc[mask].copy()

            if df_filtered.empty:
                self.figure.clear()
                self.canvas.draw()
                return

            daily_stats = []
            self.current_stats = {}

            for date, group in df_filtered.groupby('日期'):
                group_sorted = group.sort_values('连板高度', ascending=False)

                if len(group_sorted) > 0:
                    max_val = int(group_sorted.iloc[0]['连板高度'])
                    max_stocks = group_sorted[group_sorted['连板高度'] == max_val]
                    max_stock_list = [{'代码': str(r['代码']).zfill(6), '股票名称': str(r['股票名称'])}
                                      for _, r in max_stocks.iterrows()]

                    second_stocks = group_sorted[group_sorted['连板高度'] < max_val]
                    second_val = int(second_stocks.iloc[0]['连板高度']) if len(second_stocks) > 0 else 0

                    daily_stats.append({
                        '日期': date,
                        '最大值': max_val,
                        '次大值': second_val,
                        '最大值股票': max_stock_list
                    })

            if not daily_stats:
                self.figure.clear()
                self.canvas.draw()
                return

            df_stats = pd.DataFrame(daily_stats)
            df_stats = df_stats.sort_values('日期').reset_index(drop=True)

            self.current_dates = df_stats['日期'].tolist()

            up_rates, down_rates, zt_counts, dt_counts, hot_concepts, volume_changes = [], [], [], [], [], []

            for idx, date in enumerate(self.current_dates):
                stat_row = df_lbss[df_lbss['日期'] == date]
                if not stat_row.empty:
                    row = stat_row.iloc[0]
                    up = int(row.get('上涨', 0) or 0)
                    down = int(row.get('下跌', 0) or 0)
                    flat = int(row.get('平盘', 0) or 0)
                    total = up + down + flat

                    up_rate = (up / total * 100) if total > 0 else 0
                    down_rate = (down / total * 100) if total > 0 else 0

                    up_rates.append(up_rate)
                    down_rates.append(down_rate)
                    zt_counts.append(int(row.get('涨停', 0) or 0))
                    dt_counts.append(int(row.get('跌停', 0) or 0))
                    hot_concepts.append((str(row.get('最火概念1', '')), str(row.get('最火概念2', '')),
                                         str(row.get('最火概念3', ''))))

                    today_vol = float(row.get('今日成交', 0) or 0)
                    yesterday_vol = float(row.get('昨日成交', 0) or 0)
                    volume_change = 100 * (today_vol - yesterday_vol) / yesterday_vol if yesterday_vol > 0 else 0
                    volume_changes.append(volume_change)

                    self.current_stats[idx] = {
                        'up_rate': f"{up_rate:.1f}%",
                        'down_rate': f"{down_rate:.1f}%",
                        'zt_count': str(zt_counts[-1]),
                        'dt_count': str(dt_counts[-1]),
                        'volume_change': f"{volume_change:.1f}%",
                        'hot1': str(row.get('最火概念1', '')),
                        'hot2': str(row.get('最火概念2', '')),
                        'hot3': str(row.get('最火概念3', '')),
                    }
                else:
                    up_rates.append(0)
                    down_rates.append(0)
                    zt_counts.append(0)
                    dt_counts.append(0)
                    hot_concepts.append(('', '', ''))
                    volume_changes.append(0)

            self.last_chart_data = {
                'dates': self.current_dates,
                'max_vals': df_stats['最大值'].tolist(),
                'second_vals': df_stats['次大值'].tolist(),
                'max_stock_lists': df_stats['最大值股票'].tolist(),
                'up_rates': up_rates,
                'down_rates': down_rates,
                'zt_counts': zt_counts,
                'dt_counts': dt_counts,
                'volume_changes': volume_changes,
                'hot_concepts': hot_concepts,
                'start_date': start_date,
                'end_date': end_date
            }

            self.draw_chart_with_data(**self.last_chart_data)

            if len(self.current_dates) > 0:
                latest_date = self.current_dates[-1]
                latest_idx = len(self.current_dates) - 1
                date_str = latest_date.strftime('%Y-%m-%d')

                self.date_display_label.setText(date_str)

                if latest_idx in self.current_stats:
                    hot1 = self.current_stats[latest_idx].get('hot1', '')
                    if hot1:
                        self.selected_concept = hot1
                        self.current_concept_label.setText(f"当前概念: {hot1}")

                self.load_tables_for_date(date_str)

        except Exception as e:
            print(f"❌ 绘制图表失败: {e}")
            import traceback
            traceback.print_exc()

    def draw_chart_with_data(self, dates, max_vals, second_vals, max_stock_lists,
                             up_rates, down_rates, zt_counts, dt_counts,
                             volume_changes, hot_concepts, start_date, end_date):
        self.figure.clear()

        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        x_positions = range(len(dates))

        if self.cb_emotion.isChecked():
            ax1.plot(x_positions, max_vals, marker='o', linewidth=2, markersize=8,
                     label='最大连板高度', color='#FF6B6B', linestyle='-')
            ax1.plot(x_positions, second_vals, marker='s', linewidth=2, markersize=8,
                     label='次高度', color='#4ECDC4', linestyle='--')

            for i, (x, max_val, second_val, stock_list) in enumerate(
                    zip(x_positions, max_vals, second_vals, max_stock_lists)):
                stock_texts = [f"{s['代码']}\n{s['股票名称']}" for s in stock_list]
                label_text = f'{max_val}\n' + '\n'.join(stock_texts)
                offset_y = 15 + len(stock_list) * 5

                ax1.annotate(label_text, xy=(x, max_val), xytext=(0, offset_y),
                             textcoords='offset points', ha='center', va='bottom',
                             fontsize=9, color='#FF6B6B', fontweight='bold',
                             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor='#FF6B6B'))

                ax1.annotate(f'{second_val}', xy=(x, second_val), xytext=(0, -15),
                             textcoords='offset points', ha='center', va='top',
                             fontsize=12, color='#4ECDC4', fontweight='bold')

            y_max = max(max_vals) if max_vals else 10
            ax1.set_ylim(bottom=2, top=y_max + 1)
            ax1.set_ylabel('连板高度', fontsize=12, color='#FF6B6B')
            ax1.tick_params(axis='y', labelcolor='#FF6B6B')

        legend_items = []

        if self.cb_up_rate.isChecked():
            ax2.plot(x_positions, up_rates, marker='*', linewidth=1.5, markersize=6,
                     label='上涨率(%)', color='purple', linestyle='-')
            legend_items.append(('上涨率(%)', 'purple'))

        if self.cb_down_rate.isChecked():
            ax2.plot(x_positions, down_rates, marker='v', linewidth=1.5, markersize=6,
                     label='下跌率(%)', color='#4876FF', linestyle='-.')
            legend_items.append(('下跌率(%)', '#4876FF'))

        if self.cb_zt_count.isChecked():
            ax2.plot(x_positions, zt_counts, marker='D', linewidth=1.5, markersize=5,
                     label='涨停数', color='#FF00FF', linestyle='-')
            legend_items.append(('涨停数', '#FF00FF'))

        if self.cb_dt_count.isChecked():
            ax2.plot(x_positions, dt_counts, marker='x', linewidth=1.5, markersize=6,
                     label='跌停数', color='#00AA00', linestyle=':')
            legend_items.append(('跌停数', '#00AA00'))

        if self.cb_volume_change.isChecked():
            ax2.plot(x_positions, volume_changes, marker='p', linewidth=1.5, markersize=7,
                     label='成交增幅(%)', color='#FF8C00', linestyle='-')
            legend_items.append(('成交增幅(%)', '#FF8C00'))

        concept_counts = None
        if self.cb_hot_concept.isChecked() and self.selected_concept:
            concept_counts = self.get_concept_counts(self.selected_concept, dates)
            if concept_counts:
                ax2.plot(x_positions, concept_counts, marker='*', linewidth=2, markersize=10,
                         label=f'【{self.selected_concept}】涨停数', color='#9932CC', linestyle='-')
                legend_items.append((f'【{self.selected_concept}】涨停数', '#9932CC'))

        if legend_items:
            values_to_compare = [0]
            if self.cb_up_rate.isChecked() and up_rates:
                values_to_compare.append(max(up_rates))
            if self.cb_down_rate.isChecked() and down_rates:
                values_to_compare.append(max(down_rates))
            if self.cb_zt_count.isChecked() and zt_counts:
                values_to_compare.append(max(zt_counts))
            if self.cb_dt_count.isChecked() and dt_counts:
                values_to_compare.append(max(dt_counts))
            if self.cb_volume_change.isChecked() and volume_changes:
                values_to_compare.append(max(volume_changes))
            if concept_counts:
                values_to_compare.append(max(concept_counts))

            max_val_right = max(values_to_compare)

            min_val_right = 0
            if self.cb_volume_change.isChecked() and volume_changes:
                min_val_right = min(min(volume_changes), 0)

            ax2.set_ylim(bottom=min_val_right - 10, top=max(max_val_right * 1.2, 60))
            ax2.set_ylabel('上涨率(%)/下跌率(%)/数量/成交增幅(%)', fontsize=10, color='#666666')
            ax2.tick_params(axis='y', labelcolor='#666666')

        date_labels = [d.strftime('%m-%d') for d in dates]
        ax1.set_xticks(list(x_positions))
        ax1.set_xticklabels(date_labels, rotation=45, ha='right')

        ax1.set_title(f'情绪高度 ({start_date} 至 {end_date})', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--')

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        if lines1 or lines2:
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8, ncol=2)

        self.figure.tight_layout()
        self.canvas.draw()

    def get_concept_counts(self, concept_name, dates):
        if self.df_lbss_all is None or not concept_name:
            return None

        counts = []
        for date in dates:
            stat_row = self.df_lbss_all[self.df_lbss_all['日期'] == date]
            if not stat_row.empty:
                row = stat_row.iloc[0]
                if row.get('最火概念1', '') == concept_name:
                    counts.append(int(row.get('最火概念1涨停', 0) or 0))
                elif row.get('最火概念2', '') == concept_name:
                    counts.append(int(row.get('最火概念2涨停', 0) or 0))
                elif row.get('最火概念3', '') == concept_name:
                    counts.append(int(row.get('最火概念3涨停', 0) or 0))
                else:
                    counts.append(0)
            else:
                counts.append(0)

        return counts


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
