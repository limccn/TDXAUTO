# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import numpy as np
import sys
import os
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QHeaderView, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QCheckBox, QScrollArea, \
    QWidget
import json
from data_update import update

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib import rcParams

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

        # --- Widget ---
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setObjectName("widget")

        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")

        # 快速选择按钮
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

        # 日期范围控件
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

        self.update_info_label = QtWidgets.QLabel(self.widget)
        self.update_info_label.setObjectName("update_info_label")
        self.update_info_label.setStyleSheet(
            "color: #0066cc; font-weight: bold; padding: 5px; "
            "background-color: #e6f2ff; border-radius: 3px; border: 1px solid #b3d4fc;"
        )
        self.horizontalLayout.addWidget(self.update_info_label)

        main_layout.addWidget(self.widget)

        # 图表区
        self.chart_widget = QtWidgets.QWidget()
        chart_layout = QVBoxLayout(self.chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(5)

        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)

        self.chk_container = QWidget()
        self.chk_layout = QHBoxLayout(self.chk_container)
        self.chk_layout.setContentsMargins(0, 0, 0, 0)
        self.chk_container.setMaximumHeight(40)
        chart_layout.addWidget(self.chk_container)

        main_layout.addWidget(self.chart_widget, stretch=1)

        # Top5信息区
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
        MainWindow.setWindowTitle(_translate("MainWindow", "板块涨幅分析"))
        self.banner.setText(_translate("MainWindow", "板块涨幅分析，反向得出板块热度！"))
        self.btn_1_week.setText(_translate("MainWindow", "近1周"))
        self.btn_2_weeks.setText(_translate("MainWindow", "近2周"))
        self.btn_1_month.setText(_translate("MainWindow", "近1月"))
        self.btn_3_months.setText(_translate("MainWindow", "近3月"))
        self.start_date_label.setText(_translate("MainWindow", "开始日期:"))
        self.end_date_label.setText(_translate("MainWindow", "结束日期:"))
        self.analyze_btn.setText(_translate("MainWindow", "分析涨幅"))
        self.update_data_btn.setText(_translate("MainWindow", "数据更新"))
        self.update_info_label.setText(_translate("MainWindow", "⏳ 等待更新..."))
        self.top_stocks_info.setText(_translate("MainWindow", "📊 期间内最活跃代码 Top 5: 暂无数据"))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.blkfile_path = ""
        self.mpl_cid = None

        self.analyze_btn.clicked.connect(self.on_analyze_date_clicked)
        self.update_data_btn.clicked.connect(self.on_update_data_clicked)

        self.btn_1_week.clicked.connect(lambda: self.set_date_range(days=7))
        self.btn_2_weeks.clicked.connect(lambda: self.set_date_range(days=14))
        self.btn_1_month.clicked.connect(lambda: self.set_date_range(days=30))
        self.btn_3_months.clicked.connect(lambda: self.set_date_range(days=90))
        self.set_date_range(days=14)

    def set_date_range(self, days):
        """快速选择日期范围并触发分析"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        self.end_date_input.setText(end_date.strftime('%Y-%m-%d'))
        self.start_date_input.setText(start_date.strftime('%Y-%m-%d'))

        self.on_analyze_date_clicked()

    def load_resources(self):
        file_path = 'data/stock_gn.csv'
        if os.path.exists(file_path):
            try:
                self.df_stocks = pd.read_csv(file_path, dtype=str, encoding='utf-8-sig')
                if '代码' in self.df_stocks.columns:
                    self.df_stocks['代码'] = self.df_stocks['代码'].astype(str).str.zfill(6)
                print("✅ 已加载 data/stock_gn.csv 到内存")
            except Exception as e:
                print(f"❌ 加载 data/stock_gn.csv 失败: {e}")
                self.df_stocks = pd.DataFrame()
        else:
            print(f"⚠️ data/stock_gn.csv 不存在")
            self.df_stocks = pd.DataFrame()

        try:
            if os.path.exists("set_key.txt"):
                with open("set_key.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                    self.exclude_words = set(word for word in content.split() if word.strip())
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
        except Exception as e:
            pass

    def on_update_data_clicked(self):
        """数据更新按钮：执行 data_update 中的 run 函数"""
        try:
            self.update_info_label.setText("🔄 正在执行全量数据更新，请稍候...")
            QtWidgets.QApplication.processEvents()

            updater = update()
            updater.run()

            self.load_resources()
            self.on_analyze_date_clicked()

            self.update_info_label.setText("✅ 全部数据更新完成")
            QtWidgets.QMessageBox.information(self, "完成", "全部数据更新完成！")

        except Exception as e:
            self.update_info_label.setText(f"❌ 更新失败: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "错误", f"更新失败: {e}")
            import traceback
            traceback.print_exc()

    def on_analyze_date_clicked(self):
        """分析涨停按钮：读取数据并绘制板块涨跌幅图表"""
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

        blk_path = 'data/blk.csv'
        if not os.path.exists(blk_path):
            QtWidgets.QMessageBox.warning(self, "提示", f"板块数据文件不存在 ({blk_path})，请先点击'数据更新'按钮")
            return

        try:
            df_blk = pd.read_csv(blk_path, dtype={'date': str, 'code': str, 'name': str, 'rate': float})
            df_blk['date'] = pd.to_datetime(df_blk['date'])

            mask = (df_blk['date'] >= start_str) & (df_blk['date'] <= end_str)
            df_blk_filtered = df_blk.loc[mask].copy()

            if df_blk_filtered.empty:
                QtWidgets.QMessageBox.warning(self, "提示", f"在选定日期范围内没有板块数据")
                return

            self.plot_blk_charts(df_blk_filtered, start_str, end_str)

            self.top_stocks_info.setText(f"📊 日期范围: {start_str} 至 {end_str}，共 {len(df_blk_filtered)} 条板块数据")

            QtWidgets.QMessageBox.information(self, "完成", f"分析完成！\n显示 {len(df_blk_filtered)} 条板块数据")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"读取显示数据失败: {e}")
            import traceback
            traceback.print_exc()

    def toggle_line(self, label, checked):
        """复选框槽函数：控制折线的显示/隐藏"""
        for line in self.ax.lines:
            if line.get_linestyle() == ':':
                continue
            if line.get_label() == label:
                line.set_visible(checked)
                break

        self.canvas.draw_idle()

    def on_mouse_move(self, event):
        """鼠标移动事件：显示数据提示"""
        if event.inaxes != self.ax:
            self.annot.set_visible(False)
            self.vline.set_visible(False)
            self.canvas.draw_idle()
            return

        x_data = event.xdata

        idx = (np.abs(self.unique_dates_num - x_data)).argmin()

        x_date = self.unique_dates[idx]

        self.vline.set_xdata([x_date, x_date])
        self.vline.set_visible(True)

        text_str = f"日期: {x_date.strftime('%Y-%m-%d')}\n"

        for line in self.ax.lines:
            if line.get_linestyle() == ':': continue
            if not line.get_visible(): continue

            label = line.get_label()
            y_data = line.get_ydata()

            if idx < len(y_data):
                val = y_data[idx]
                text_str += f"{label}: {val}%\n"

        self.annot.xy = (x_date, event.ydata)
        self.annot.set_text(text_str)
        self.annot.set_visible(True)

        self.canvas.draw_idle()

    def plot_blk_charts(self, df_blk, start_date, end_date):
        """绘制板块涨跌幅折线图"""
        if self.mpl_cid is not None:
            self.canvas.mpl_disconnect(self.mpl_cid)

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        self.unique_dates = sorted(df_blk['date'].unique())
        self.unique_dates_num = mdates.date2num(self.unique_dates)

        if not self.unique_dates:
            self.canvas.draw()
            return

        unique_names = df_blk['name'].unique()

        if len(unique_names) == 0:
            self.canvas.draw()
            return

        while self.chk_layout.count():
            item = self.chk_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        # ========== 【修改】筛选最近日期涨幅最大的10个概念 ==========
        # 1. 获取最近的日期
        latest_date = df_blk['date'].max()

        # 2. 筛选最近日期的数据
        latest_data = df_blk[df_blk['date'] == latest_date]

        # 3. 按涨幅降序排序，取前10个名称
        # 如果涨幅数据有 NaN，先填充为 0 或丢弃
        latest_data = latest_data.dropna(subset=['rate'])
        top_names_data = latest_data.sort_values(by='rate', ascending=False).head(10)
        top_names = top_names_data['name'].tolist()

        # 如果不足10个，则全部显示
        if not top_names:
            QtWidgets.QMessageBox.warning(self, "提示", "最近日期无有效涨幅数据")
            return

        print(f"📈 筛选逻辑: 最近日期 {latest_date.strftime('%Y-%m-%d')} 涨幅最大 Top 10")
        print(f"🏷️ 选定板块: {top_names}")

        # ========== 【关键修改】动态计算Y轴范围 ==========
        all_rates = df_blk[df_blk['name'].isin(top_names)]['rate']
        min_rate = all_rates.min()
        max_rate = all_rates.max()

        # 添加10%边距，确保数据点不贴边
        margin = abs(max_rate - min_rate) * 0.1
        y_min = min_rate - margin
        y_max = max_rate + margin

        # 确保最小范围
        if abs(y_max - y_min) < 5:
            center = (y_max + y_min) / 2
            y_min = center - 5
            y_max = center + 5

        print(f"📊 数据范围: {min_rate:.2f}% 到 {max_rate:.2f}%")
        print(f"📐 Y轴范围: {y_min:.2f} 到 {y_max:.2f}")

        for idx, name in enumerate(top_names):
            name_data = df_blk[df_blk['name'] == name].copy()
            name_data = name_data.sort_values('date')

            x_dates = name_data['date'].tolist()
            y_rates = name_data['rate'].tolist()

            color = colors[idx % len(colors)]

            self.ax.plot(x_dates, y_rates, marker='o', linewidth=2, markersize=4,
                         label=name, color=color)

            chk = QCheckBox(name)
            chk.setChecked(True)

            palette = chk.palette()
            palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(color))
            chk.setPalette(palette)

            chk.stateChanged.connect(lambda state, n=name: self.toggle_line(n, state == QtCore.Qt.Checked))

            self.chk_layout.addWidget(chk)

        self.chk_layout.addStretch()

        self.ax.set_title(f"板块涨跌幅趋势图 ({start_date} 至 {end_date})", fontsize=14, fontweight='bold')
        self.ax.set_xlabel('日期', fontsize=12)
        self.ax.set_ylabel('涨跌幅 (%)', fontsize=12)

        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        import matplotlib.pyplot as plt
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        # ========== 【保留】Y轴范围设置为 1-6 ==========
        self.ax.set_ylim(y_min, y_max)

        self.ax.grid(True, alpha=0.3, linestyle='--')

        # 添加零线
        self.ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)

        self.figure.tight_layout()

        self.vline = self.ax.axvline(x=self.unique_dates[0], color='gray', linestyle=':', alpha=0.8)
        self.vline.set_visible(False)

        self.annot = self.ax.annotate('', xy=(0, 0), xytext=(20, 20), textcoords='offset points',
                                      bbox=dict(boxstyle='round', fc='w', alpha=0.8),
                                      arrowprops=dict(arrowstyle='->'))
        self.annot.set_visible(False)

        self.mpl_cid = self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        self.canvas.draw()

if __name__ == "__main__":
    import matplotlib.pyplot as plt

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
