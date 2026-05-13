# -*- coding: utf-8 -*-
import sys
import os
import re
import json  # 用于保存配置
import pandas as pd
import numpy as np
import time
import io
import threading
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QHeaderView, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QCheckBox, QPushButton, \
    QFrame, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import ak_simple
import emo_simple
import matplotlib

matplotlib.use('Qt5Agg')


# ================= 新增：情绪计算线程类 =================
class EmoCalculationThread(QThread):
    """运行 emo_simple 情绪计算的线程"""

    # 定义信号
    log_signal = pyqtSignal(str)  # 日志输出信号
    finished_signal = pyqtSignal()  # 完成信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.doctor = None

    def run(self):
        """运行情绪计算程序"""
        try:
            # 导入 emo_simple 中的类
            self.log_signal.emit("📦 正在初始化计算实例...")
            self.doctor = emo_simple.emo_doctor()

            self.log_signal.emit("🚀 计算线程已启动，开始实时计算...")

            # 定义交易时间判断 (参考 emo_simple.save_emo_data)
            from datetime import datetime, time as dt_time
            morning_start = dt_time(9, 30)
            morning_end = dt_time(11, 30)
            afternoon_start = dt_time(13, 0)
            afternoon_end = dt_time(15, 0)

            def is_trading_time():
                now = datetime.now().time()
                return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

            def is_before_market_close():
                now = datetime.now().time()
                return now <= afternoon_end

            # 主循环
            while self.running and is_before_market_close():
                try:
                    now = datetime.now()
                    now_time = now.time()

                    if is_trading_time():
                        self.log_signal.emit("⏳ 正在计算市场情绪指标...")

                        # 执行核心计算逻辑
                        # cal_emo_indicators 会读取 csv 文件并计算，更新 self.doctor.emo_data_df
                        self.doctor.cal_emo_indicators()

                        # 保存计算结果到 emo_data.csv
                        if not self.doctor.emo_data_df.empty:
                            self.doctor.emo_data_df = self.doctor.emo_data_df.sort_values('时间')

                            # 确保目录存在
                            import os
                            output_dir = "data"
                            if not os.path.exists(output_dir):
                                os.makedirs(output_dir)

                            filepath = os.path.join(output_dir, "emo_data.csv")
                            self.doctor.emo_data_df.to_csv(filepath, index=False, encoding='utf-8-sig')
                            self.log_signal.emit(f"✅ 计算完成并保存 (共 {len(self.doctor.emo_data_df)} 条)")
                        else:
                            self.log_signal.emit("⚠️ 计算结果为空，未保存")

                    else:
                        self.log_signal.emit("⏸️ 非交易时间，暂停计算")

                    # 响应式睡眠：每2分钟 (120秒) 执行一次
                    # 为了能随时响应停止信号，我们将120秒拆分为120个1秒的睡眠
                    for _ in range(120):
                        if not self.running:
                            self.log_signal.emit("🛑 收到停止信号，退出计算循环")
                            break
                        QThread.sleep(1)  # 这里也可以用 time.sleep(1)

                    if not self.running:
                        break

                except Exception as e:
                    self.log_signal.emit(f"❌ 计算过程出错: {str(e)}")
                    import traceback
                    # 可以选择打印 traceback 到控制台或记录日志
                    # traceback.print_exc()
                    time.sleep(10)  # 出错后等待10秒再重试

            self.log_signal.emit("🏁 已过收盘时间，计算线程结束")
            self.finished_signal.emit()

        except Exception as e:
            self.log_signal.emit(f"❌ 线程初始化异常: {str(e)}")
            self.finished_signal.emit()

    def stop(self):
        """停止线程"""
        self.log_signal.emit("🛑 正在停止计算...")
        self.running = False


# ================= 新增结束 =================

# ================= 新增：数据下载线程类 =================
class DataDownloadThread(QThread):
    """运行 ak_simple 数据下载的线程"""

    # 定义信号
    log_signal = pyqtSignal(str)  # 日志输出信号
    finished_signal = pyqtSignal()  # 完成信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.data_his = None

    def run(self):
        """运行数据下载程序"""
        try:
            # 【修复】删除重复导入，使用全局已导入的 ak_simple
            # 创建 data_his 实例
            self.log_signal.emit("📦 正在创建数据获取实例...")
            self.data_his = ak_simple.data_his()

            # 重定向输出到我们的日志信号
            self.log_signal.emit("🚀 数据下载线程已启动")
            self.log_signal.emit("正在初始化数据下载模块...")

            # 调用 start_realtime_fetch
            self.log_signal.emit("⏳ 准备启动实时数据获取...")
            self.data_his.start_realtime_fetch_with_callback(
                interval_minutes=1,
                callback=self.log_signal.emit,
                stop_check=lambda: not self.running  # 修正：running 为 True 时返回 False（不停止），running 为 False 时返回 True（停止）
            )

        except MemoryError as e:
            self.log_signal.emit(f"❌ 内存错误: {str(e)}")
            self.log_signal.emit("💡 建议：重启程序或增加系统内存")
        except ImportError as e:
            self.log_signal.emit(f"❌ 导入错误: {str(e)}")
        except Exception as e:
            error_msg = f"❌ 错误: {str(e)}"
            self.log_signal.emit(error_msg)
            import traceback
            self.log_signal.emit(traceback.format_exc())
        finally:
            self.log_signal.emit("🛑 数据下载线程已停止")
            self.finished_signal.emit()

    def stop(self):
        """停止线程"""
        self.log_signal.emit("🛑 正在停止线程...")
        self.running = False
        # 不要调用 wait()，可能导致死锁
        # self.wait()  # 注释掉



# ================= 新增结束 =================


class MainWindow(object):
    # ================= 事件处理函数 =================
    def on_group_toggled(self, state, item_checkboxes):
        """组名复选框状态改变时，控制组内所有复选框"""
        # state: 0=Unchecked, 1=PartiallyChecked, 2=Checked

        if state == QtCore.Qt.Checked:
            for cb in item_checkboxes:
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)
        elif state == QtCore.Qt.Unchecked:
            for cb in item_checkboxes:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)

        self.refresh_chart()
        self.save_checkbox_state()  # 保存状态

    def on_item_toggled(self, state, group_checkbox, item_checkboxes):
        """组内复选框状态改变时，更新组名复选框状态（支持三态）"""
        checked_count = 0
        total_count = len(item_checkboxes)

        for cb in item_checkboxes:
            if cb.isChecked():
                checked_count += 1

        group_checkbox.blockSignals(True)

        if checked_count == 0:
            group_checkbox.setCheckState(QtCore.Qt.Unchecked)
        elif checked_count == total_count:
            group_checkbox.setCheckState(QtCore.Qt.Checked)
        else:
            group_checkbox.setCheckState(QtCore.Qt.PartiallyChecked)

        group_checkbox.blockSignals(False)

        self.refresh_chart()
        self.save_checkbox_state()  # 保存状态

    # ================= 新增：全选与反选逻辑 =================
    def on_select_all(self):
        """全选所有筛选项"""
        for group_name, data in self.filter_groups.items():
            # 触发组复选框的选中状态，它会自动选中子项
            data['group_cb'].setChecked(True)

    def on_invert_selection(self):
        """反选所有筛选项"""
        for group_name, data in self.filter_groups.items():
            item_cbs = data['item_cbs']
            group_cb = data['group_cb']

            # 阻止信号以避免每个子项改变时都触发刷新
            for cb in item_cbs:
                cb.blockSignals(True)
                cb.setChecked(not cb.isChecked())
                cb.blockSignals(False)

            # 手动更新父级状态
            checked_count = sum(1 for cb in item_cbs if cb.isChecked())
            total_count = len(item_cbs)

            group_cb.blockSignals(True)
            if checked_count == 0:
                group_cb.setCheckState(QtCore.Qt.Unchecked)
            elif checked_count == total_count:
                group_cb.setCheckState(QtCore.Qt.Checked)
            else:
                group_cb.setCheckState(QtCore.Qt.PartiallyChecked)
            group_cb.blockSignals(False)

        self.refresh_chart()
        self.save_checkbox_state()

    def save_checkbox_state(self):
        """保存复选框状态到文件"""
        data = {}
        for group_name, group_data in self.filter_groups.items():
            items = {}
            for cb in group_data['item_cbs']:
                items[cb.text()] = cb.isChecked()
            data[group_name] = items

        try:
            with open('tdx_emo.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            # print("✅ 筛选配置已保存")
        except Exception as e:
            print(f"⚠️ 保存配置失败: {e}")

    def load_checkbox_state(self):
        """从文件加载复选框状态"""
        if not os.path.exists('tdx_emo.json'):
            return

        try:
            with open('tdx_emo.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            for group_name, group_data in self.filter_groups.items():
                if group_name in data:
                    saved_items = data[group_name]
                    group_cb = group_data['group_cb']
                    item_cbs = group_data['item_cbs']

                    # 阻止信号，避免加载时触发刷新
                    group_cb.blockSignals(True)

                    # 更新子项状态
                    for cb in item_cbs:
                        cb.blockSignals(True)
                        if cb.text() in saved_items:
                            cb.setChecked(saved_items[cb.text()])
                        cb.blockSignals(False)

                    # 计算并设置父级状态
                    checked_count = sum(1 for cb in item_cbs if cb.isChecked())
                    total_count = len(item_cbs)
                    if checked_count == 0:
                        group_cb.setCheckState(QtCore.Qt.Unchecked)
                    elif checked_count == total_count:
                        group_cb.setCheckState(QtCore.Qt.Checked)
                    else:
                        group_cb.setCheckState(QtCore.Qt.PartiallyChecked)

                    group_cb.blockSignals(False)

            # 加载完成后刷新一次图表
            self.refresh_chart()
            # print("✅ 筛选配置已加载")

        except Exception as e:
            print(f"⚠️ 加载配置失败: {e}")

    # ================= 新增结束 =================

    # ================= 图表刷新方法 =================
    def refresh_chart(self):
        """根据当前复选框状态刷新图表"""
        print("🔄 复选框状态改变，刷新图表...")

        selected_filters = []
        for group_name, data in self.filter_groups.items():
            for item_cb in data['item_cbs']:
                if item_cb.isChecked():
                    selected_filters.append(item_cb.text())

        print(f"当前选中指标数量: {len(selected_filters)}")

        self.kline.plot_emo_trend(
            csv_path='data/emo_data.csv',
            ax=self.ax_main,
            selected_filters=selected_filters,
            canvas=self.canvas,
            figure=self.figure  # 传入 figure 对象用于布局调整
        )

    # ================= 新增：数据下载相关方法 =================


    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1720, 1350)

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
        self.banner.setStyleSheet("color: white;\nbackground-color: rgb(0, 170, 255);")
        self.banner.setAlignment(QtCore.Qt.AlignCenter)
        self.banner.setObjectName("banner")
        main_layout.addWidget(self.banner)

        # ================= 工具栏区域 =================
        self.tool_bar_widget = QtWidgets.QWidget(self.centralwidget)
        self.tool_bar_widget.setObjectName("tool_bar_widget")
        tool_bar_layout = QHBoxLayout(self.tool_bar_widget)
        tool_bar_layout.setContentsMargins(0, 0, 0, 0)
        tool_bar_layout.setSpacing(10)





        tool_btn_style = """
            QPushButton {
                background-color: rgb(0, 170, 255);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgb(0, 140, 220);
            }
            QPushButton:pressed {
                background-color: rgb(0, 120, 200);
            }
        """

        # self.btn_auto_plot = QtWidgets.QPushButton("自动画图", self.tool_bar_widget)
        # self.btn_auto_plot.setObjectName("btn_auto_plot")
        # self.btn_auto_plot.setStyleSheet(tool_btn_style)
        # tool_bar_layout.addWidget(self.btn_auto_plot)

        self.btn_auto_run = QtWidgets.QPushButton("自动运行", self.tool_bar_widget)
        self.btn_auto_run.setObjectName("btn_auto_run")
        self.btn_auto_run.setStyleSheet(tool_btn_style)
        tool_bar_layout.addWidget(self.btn_auto_run)

        # 修改：合并为一个状态标签
        tool_bar_layout.addSpacing(20)
        self.lbl_run_status = QtWidgets.QLabel("就绪", self.tool_bar_widget)
        self.lbl_run_status.setObjectName("lbl_run_status")
        self.lbl_run_status.setStyleSheet("color: gray; font-weight: normal;")
        self.lbl_run_status.setFixedWidth(400)  # 加宽以显示更多信息
        tool_bar_layout.addWidget(self.lbl_run_status)




        # 【新增】全选和反选按钮
        tool_bar_layout.addSpacing(20)
        self.btn_select_all = QtWidgets.QPushButton("全选", self.tool_bar_widget)
        self.btn_select_all.setObjectName("btn_select_all")
        self.btn_select_all.setStyleSheet(tool_btn_style)
        tool_bar_layout.addWidget(self.btn_select_all)

        self.btn_invert = QtWidgets.QPushButton("反选", self.tool_bar_widget)
        self.btn_invert.setObjectName("btn_invert")
        self.btn_invert.setStyleSheet(tool_btn_style)
        tool_bar_layout.addWidget(self.btn_invert)



        tool_bar_layout.addSpacing(100)
        self.btn_del_history = QtWidgets.QPushButton("删除历史数据", self.tool_bar_widget)
        self.btn_del_history.setObjectName("btn_del_history")
        self.btn_del_history.setStyleSheet(tool_btn_style)
        tool_bar_layout.addWidget(self.btn_del_history)







        tool_bar_layout.addStretch()
        main_layout.addWidget(self.tool_bar_widget)




        # --- Widget (输入框和按钮区域) ---
        # self.widget = QtWidgets.QWidget(self.centralwidget)
        # self.widget.setObjectName("widget")
        #
        # self.widget_main_layout = QVBoxLayout(self.widget)
        # self.widget_main_layout.setContentsMargins(0, 0, 0, 0)
        # self.widget_main_layout.setSpacing(5)
        #
        # self.input_row_layout = QtWidgets.QHBoxLayout()
        # self.input_row_layout.setContentsMargins(0, 0, 0, 0)
        # self.input_row_layout.setObjectName("input_row_layout")
        #
        # self.input_stock_lable = QtWidgets.QLabel(self.widget)
        # font_label = QtGui.QFont()
        # font_label.setFamily("SimHei")
        # font_label.setPointSize(14)
        # font_label.setBold(True)
        # self.input_stock_lable.setFont(font_label)
        # self.input_stock_lable.setStyleSheet("color: green;")
        # self.input_stock_lable.setObjectName("input_stock_lable")
        #
        # self.input_stock = QtWidgets.QLineEdit(self.widget)
        # self.input_stock.setInputMask("")
        # self.input_stock.setText("")
        # self.input_stock.setObjectName("input_stock")
        # font_input = QtGui.QFont()
        # font_input.setFamily("SimHei")
        # font_input.setPointSize(14)
        # self.input_stock.setFont(font_input)
        # self.input_stock.setStyleSheet("color: blue;")
        # self.input_stock.setFixedHeight(30)
        #
        # self.chk_mainboard = QCheckBox("主板", self.widget)
        # self.chk_mainboard.setObjectName("chk_mainboard")
        # font_chk = QtGui.QFont()
        # font_chk.setFamily("SimHei")
        # font_chk.setPointSize(12)
        # self.chk_mainboard.setFont(font_chk)
        # self.chk_mainboard.setChecked(True)
        #
        # self.chk_st = QCheckBox("ST股", self.widget)
        # self.chk_st.setObjectName("chk_st")
        # self.chk_st.setFont(font_chk)
        #
        # self.chk_bse = QCheckBox("北证", self.widget)
        # self.chk_bse.setObjectName("chk_bse")
        # self.chk_bse.setFont(font_chk)
        #
        # self.btn_confirm = QPushButton("确定", self.widget)
        # self.btn_confirm.setObjectName("btn_confirm")
        # self.btn_confirm.setFixedHeight(30)
        # self.btn_confirm.setFixedWidth(80)
        # self.btn_confirm.setStyleSheet("""
        #     QPushButton {
        #         background-color: rgb(0, 170, 255);
        #         color: white;
        #         font-size: 12px;
        #         font-weight: bold;
        #         border-radius: 4px;
        #     }
        #     QPushButton:hover {
        #         background-color: rgb(0, 140, 220);
        #     }
        #     QPushButton:pressed {
        #         background-color: rgb(0, 120, 200);
        #     }
        # """)
        #
        # self.input_row_layout.addWidget(self.input_stock_lable)
        # self.input_row_layout.addWidget(self.input_stock)
        # self.input_row_layout.addSpacing(20)
        # self.input_row_layout.addWidget(self.chk_mainboard)
        # self.input_row_layout.addWidget(self.chk_st)
        # self.input_row_layout.addWidget(self.chk_bse)
        # self.input_row_layout.addSpacing(10)
        # self.input_row_layout.addWidget(self.btn_confirm)
        # self.input_row_layout.addStretch()
        #
        # self.widget_main_layout.addLayout(self.input_row_layout)

        # ================= 4行多选框筛选区域 =================
        group_style = "QCheckBox { color: green; font: bold 12pt \"SimHei\"; }"
        item_style = "QCheckBox { color: black; font: 11pt \"SimHei\"; }"

        filter_config = [
            {
                "groups": [
                    {"name": "今天涨停表现组",
                     "items": ['连板数', '涨停数量', '跌停数量', '炸板数量', '炸板率']},
                    # {"name": "昨天涨停表现组",
                    #  "items": ['昨涨停平均收益', '昨涨停上涨比率', '昨涨停下跌比率', '连板晋级率']},
                ]
            },
            # {
            #     "groups": [
            #         {"name": "热股表现组",
            #          "items": ['通达信热股上涨率', '通达信热股下跌率', '通达信热股平均涨幅']},
            #         {"name": "昨龙虎榜表现组",
            #          "items": ['昨龙虎榜平均涨幅', '昨龙虎榜上涨比率', '昨龙虎榜下跌比率']},
            #     ]
            # },
            # {
            #     "groups": [
            #         {"name": "全体表现组",
            #          "items": ['上涨大于7比率', '上涨5-7比率', '上涨3-5比率', '上涨0-3比率',
            #                    '下跌0-3比率', '下跌3-5比率', '下跌5-7比率', '下跌大于7比率',
            #                    '全市场平均涨幅', '上涨比例', '下跌比例']},
            #     ]
            # },
            {
                "groups": [
                    {"name": "赚钱效应表现组",
                     "items": ['M上涨率', 'M下跌率', 'M平盘率', '非一字涨停', '非一字跌停',
                               'ST涨停', 'ST跌停', '活跃度']},
                ]
            }
        ]

        self.filter_groups = {}

        for row_data in filter_config:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(15)

            for group_info in row_data["groups"]:
                group_name = group_info["name"]
                items = group_info["items"]

                group_cb = QCheckBox(group_name)
                group_cb.setStyleSheet(group_style)
                group_cb.setChecked(True)
                # 【关键修改】开启三态，允许部分选中
                group_cb.setTristate(True)

                item_checkboxes = []

                row_layout.addWidget(group_cb)

                for item_name in items:
                    item_cb = QCheckBox(item_name)
                    item_cb.setStyleSheet(item_style)
                    item_cb.setChecked(True)
                    row_layout.addWidget(item_cb)
                    item_checkboxes.append(item_cb)

                group_cb.stateChanged.connect(
                    lambda state, cbs=item_checkboxes: self.on_group_toggled(state, cbs)
                )

                for item_cb in item_checkboxes:
                    item_cb.stateChanged.connect(
                        lambda state, g=group_cb, cbs=item_checkboxes: self.on_item_toggled(state, g, cbs)
                    )

                self.filter_groups[group_name] = {
                    "group_cb": group_cb,
                    "item_cbs": item_checkboxes
                }

                separator = QFrame()
                separator.setFrameShape(QFrame.VLine)
                separator.setFrameShadow(QFrame.Sunken)
                row_layout.addWidget(separator)

            if row_layout.count() > 0:
                last_item = row_layout.itemAt(row_layout.count() - 1).widget()
                if isinstance(last_item, QFrame):
                    last_item.deleteLater()

            row_layout.addStretch()
            main_layout.addLayout(row_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # 【新增】加载上次的筛选配置
        self.load_checkbox_state()
        # ================= 新增结束 =================

        # main_layout.addWidget(self.widget)




        # ================= 图表区域 =================
        self.chart_widget = QtWidgets.QWidget(self.centralwidget)
        self.chart_widget.setFixedHeight(800)
        self.chart_widget.setObjectName("chart_widget")
        chart_layout = QVBoxLayout(self.chart_widget)
        chart_layout.setContentsMargins(5, 5, 5, 5)

        self.figure = Figure(figsize=(14, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setObjectName("emotion_chart")

        self.ax_main = self.figure.add_subplot(111)

        from matplotlib import rcParams
        rcParams['font.sans-serif'] = ['SimHei']
        rcParams['axes.unicode_minus'] = False

        chart_layout.addWidget(self.canvas)
        main_layout.addWidget(self.chart_widget)
        # ================= 图表区域结束 =================

        main_layout.addStretch()

        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1720, 23))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.kline = auto_kline()

        # 【新增】初始化下载线程为 None
        self.download_thread = None
        # 【新增】初始化计算线程为 None
        self.calc_thread = None

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # ================= 事件连接 =================
        # ================= 事件连接 =================
        self.btn_auto_run.clicked.connect(self.on_auto_run)  # 修改：使用新的方法名

        self.btn_del_history.clicked.connect(self.on_del)
        # 【新增】连接新按钮
        self.btn_select_all.clicked.connect(self.on_select_all)
        self.btn_invert.clicked.connect(self.on_invert_selection)
        # ================= 连接结束 =================
        QtCore.QTimer.singleShot(10000, self.start_auto_run)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "大盘情绪分析"))
        self.banner.setText(_translate("MainWindow", "大盘情绪分析，把握日内转折点！"))
        # self.input_stock_lable.setText(_translate("MainWindow", "统计范围"))

        self.init_chart()

    def init_chart(self):
        """初始化图表"""
        print("初始化图表...")
        self.refresh_chart()

    # def on_confirm_clicked(self):
    #     # stock_range = self.input_stock.text()
    #     # mainboard = self.chk_mainboard.isChecked()
    #     # st_stock = self.chk_st.isChecked()
    #     # bse = self.chk_bse.isChecked()
    #
    #     # selected_types = []
    #     # if mainboard: selected_types.append("主板")
    #     # if st_stock: selected_types.append("ST股")
    #     # if bse: selected_types.append("北证")
    #     # type_str = "、".join(selected_types) if selected_types else "未选择"
    #
    #     selected_filters = []
    #     for group_name, data in self.filter_groups.items():
    #         for item_cb in data['item_cbs']:
    #             if item_cb.isChecked():
    #                 selected_filters.append(item_cb.text())
    #
    #     print(f"筛选选中项: {selected_filters}")
    #
    #     # 【修复】使用 window() 获取主窗口
    #     main_window = self.centralwidget.window()
    #     main_window.statusBar().showMessage(
    #         f"统计范围: {stock_range} | 类型: {type_str} | 筛选: {len(selected_filters)}项", 3000
    #     )

    # def on_auto_plot(self):
    #     """自动画图"""
    #     print("执行：自动画图")
    #     # 【修复】使用 window() 获取主窗口
    #     main_window = self.centralwidget.window()
    #     main_window.statusBar().showMessage("正在自动画图...", 2000)
    #     self.refresh_chart()

    # ================= 新增：情绪计算相关方法 =================
    # ================= 新增：合并的自动运行控制方法 =================
    def on_auto_run(self):
        """启动/停止自动运行（同时控制下载和计算）"""
        # 判断是否有任何一个线程在运行
        is_running = (self.calc_thread is not None and self.calc_thread.isRunning()) or \
                     (self.download_thread is not None and self.download_thread.isRunning())

        if not is_running:
            # 启动
            self.start_auto_run()
        else:
            # 停止
            self.stop_auto_run()

    def start_auto_run(self):
        """同时启动数据下载和情绪计算"""
        print("🚀 启动自动运行（下载+计算）...")

        # 更新UI状态：按钮变红
        self.btn_auto_run.setText("停止运行")
        self.btn_auto_run.setStyleSheet("""
            QPushButton {
                background-color: rgb(255, 100, 100);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgb(255, 80, 80);
            }
            QPushButton:pressed {
                background-color: rgb(255, 60, 60);
            }
        """)

        # 更新标签状态
        self.lbl_run_status.setText("🚀 正在启动...")
        self.lbl_run_status.setStyleSheet("color: blue; font-weight: bold;")

        # 获取主窗口
        main_window = self.centralwidget.window()
        main_window.statusBar().showMessage("正在启动自动运行...", 2000)

        # === 启动数据下载线程 ===
        self.download_thread = DataDownloadThread()
        self.download_thread.log_signal.connect(self.on_run_log)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()

        # === 启动情绪计算线程 ===
        self.calc_thread = EmoCalculationThread()
        self.calc_thread.log_signal.connect(self.on_run_log)
        self.calc_thread.finished_signal.connect(self.on_calc_finished)
        self.calc_thread.start()

    def stop_auto_run(self):
        """同时停止数据下载和情绪计算"""
        print("🛑 停止自动运行（下载+计算）...")

        # 更新标签状态
        self.lbl_run_status.setText("🛑 正在停止...")
        self.lbl_run_status.setStyleSheet("color: orange; font-weight: bold;")

        # 获取主窗口
        main_window = self.centralwidget.window()
        main_window.statusBar().showMessage("正在停止自动运行...", 2000)

        # 停止下载线程
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()

        # 停止计算线程
        if self.calc_thread and self.calc_thread.isRunning():
            self.calc_thread.stop()

    def on_run_log(self, message):
        """处理运行日志（合并显示下载和计算的日志）"""
        # 更新状态标签
        self.lbl_run_status.setText(message)

        # 根据消息内容设置颜色
        if "❌" in message or "错误" in message or "失败" in message:
            self.lbl_run_status.setStyleSheet("color: red; font-weight: bold;")
        elif "✅" in message or "成功" in message or "完成" in message:
            self.lbl_run_status.setStyleSheet("color: green; font-weight: bold;")
        elif "🚀" in message or "正在" in message or "初始化" in message:
            self.lbl_run_status.setStyleSheet("color: blue; font-weight: bold;")
        elif "⏸️" in message or "暂停" in message:
            self.lbl_run_status.setStyleSheet("color: gray; font-weight: normal;")
        else:
            self.lbl_run_status.setStyleSheet("color: black; font-weight: normal;")

        # 打印到控制台
        print(f"[运行日志] {message}")

        # 如果计算完成并保存，刷新图表
        if "计算完成并保存" in message:
            self.refresh_chart()

    def on_download_finished(self):
        """下载线程结束"""
        print("✅ 数据下载线程已结束")
        self.download_thread = None
        self.check_all_finished()

    def on_calc_finished(self):
        """计算线程结束"""
        print("✅ 情绪计算线程已结束")
        self.calc_thread = None
        self.check_all_finished()

    def check_all_finished(self):
        """检查是否所有线程都已结束"""
        # 只有当两个线程都结束时，才恢复UI
        calc_stopped = self.calc_thread is None or not self.calc_thread.isRunning()
        download_stopped = self.download_thread is None or not self.download_thread.isRunning()

        if calc_stopped and download_stopped:
            print("✅ 所有线程已结束，恢复UI状态")

            # 恢复UI状态
            self.btn_auto_run.setText("自动运行")
            self.btn_auto_run.setStyleSheet("""
                QPushButton {
                    background-color: rgb(0, 170, 255);
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: rgb(0, 140, 220);
                }
                QPushButton:pressed {
                    background-color: rgb(0, 120, 200);
                }
            """)

            self.lbl_run_status.setText("已停止")
            self.lbl_run_status.setStyleSheet("color: gray; font-weight: normal;")

            # 清理线程引用
            self.calc_thread = None
            self.download_thread = None

            # 状态栏提示
            main_window = self.centralwidget.window()
            main_window.statusBar().showMessage("自动运行已停止", 3000)

    # ================= 新增结束 =================

    def on_del(self):
        """删除历史数据文件"""
        import os
        from PyQt5.QtWidgets import QMessageBox
        from PyQt5.QtCore import QProcess

        try:
            # 定义要删除的文件列表
            files_to_delete = [
                'data/tdx_hot.txt',
                'data/今日价.csv'
            ]

            # 检查文件是否存在
            existing_files = []
            for file_path in files_to_delete:
                if os.path.exists(file_path):
                    existing_files.append(file_path)

            if not existing_files:
                QMessageBox.information(
                    None,  # 改为 None，使用默认父窗口
                    "提示",
                    "没有找到需要删除的文件！\n\ntdx_hot.txt\n今日价.csv"
                )
                return

            # 构建确认消息
            file_list_text = '\n'.join([os.path.basename(f) for f in existing_files])
            confirm_msg = QMessageBox()
            confirm_msg.setIcon(QMessageBox.Question)
            confirm_msg.setWindowTitle("确认删除")
            confirm_msg.setText("确定要删除以下历史数据文件吗？")
            confirm_msg.setInformativeText(file_list_text)
            confirm_msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm_msg.setDefaultButton(QMessageBox.No)

            # 显示确认对话框
            reply = confirm_msg.exec_()

            if reply == QMessageBox.Yes:
                # 用户确认删除
                deleted_files = []
                failed_files = []

                # 获取主窗口引用（更安全的方式）
                main_window = self.centralwidget.window()

                for file_path in existing_files:
                    try:
                        # 检查文件是否被占用
                        if os.name == 'nt':  # Windows系统
                            # 尝试重命名文件来测试是否被占用
                            temp_name = file_path + '.tmp'
                            try:
                                os.rename(file_path, temp_name)
                                os.remove(temp_name)
                            except Exception as e:
                                failed_files.append(f"{os.path.basename(file_path)} (文件可能被占用)")
                                print(f"❌ 文件被占用或无法删除: {file_path} - {e}")
                                continue
                        else:
                            # Unix/Linux系统
                            os.remove(file_path)

                        deleted_files.append(file_path)
                        print(f"✅ 已删除: {file_path}")

                    except Exception as e:
                        error_msg = str(e)
                        if "used by another process" in error_msg or "Permission denied" in error_msg:
                            failed_files.append(f"{os.path.basename(file_path)} (文件被占用，请关闭相关程序)")
                        else:
                            failed_files.append(f"{os.path.basename(file_path)} ({error_msg})")
                        print(f"❌ 删除失败: {file_path} - {e}")

                # 显示删除结果（使用 None 作为父窗口，避免引用错误）
                if failed_files:
                    result_msg = f"成功删除 {len(deleted_files)} 个文件\n\n删除失败：\n" + '\n'.join(failed_files)
                    QMessageBox.warning(
                        None,
                        "删除结果",
                        result_msg
                    )
                else:
                    result_msg = f"成功删除 {len(deleted_files)} 个文件：\n" + '\n'.join(
                        [os.path.basename(f) for f in deleted_files])
                    QMessageBox.information(
                        None,
                        "删除成功",
                        result_msg
                    )

                # 更新状态栏（安全地更新）
                try:
                    if hasattr(main_window, 'statusBar') and main_window.statusBar():
                        main_window.statusBar().showMessage(
                            f"已删除 {len(deleted_files)} 个历史数据文件", 3000
                        )
                except Exception as e:
                    print(f"⚠️ 更新状态栏失败: {e}")

                # 可选：刷新图表（如果需要）
                # 注意：删除数据文件后，刷新图表会显示示例数据
                try:
                    self.refresh_chart()
                except Exception as e:
                    print(f"⚠️ 刷新图表失败: {e}")

        except Exception as e:
            # 捕获所有未预期的异常，防止程序崩溃
            print(f"❌ 删除文件时发生严重错误: {e}")
            import traceback
            traceback.print_exc()

            QMessageBox.critical(
                None,
                "错误",
                f"删除文件时发生错误：\n{str(e)}\n\n程序将继续运行。"
            )


# ================= auto_kline 类 =================
class auto_kline:
    def __init__(self):
        self.selected_line = None  # 当前选中的折线
        self.selected_label = None  # 当前选中的折线标签名称
        self.hover_text = None  # 悬停文本标签
        self.lines = []  # 存储所有折线对象
        self.labels = []  # 存储所有折线的标签
        self.df_plot = None  # 保存用于绘图的 DataFrame，用于鼠标悬停查找

    def on_motion_notify(self, event):
        """鼠标移动事件处理，显示悬停信息"""
        if event.inaxes != self.ax_main:
            if self.hover_text:
                self.hover_text.set_visible(False)
                self.canvas.draw_idle()
            return

        # 检查是否有绘图数据
        if self.df_plot is None or self.df_plot.empty:
            return

        # X 轴是整数索引，直接四舍五入找到最近的索引
        if event.xdata is None:
            return

        nearest_idx = int(np.round(event.xdata))

        # 边界检查
        if nearest_idx < 0:
            nearest_idx = 0
        elif nearest_idx >= len(self.df_plot):
            nearest_idx = len(self.df_plot) - 1

        # 获取对应的时间
        nearest_time = self.df_plot.iloc[nearest_idx]['时间']

        # 如果是 numpy datetime64，转换一下
        if isinstance(nearest_time, np.datetime64):
            nearest_time = pd.Timestamp(nearest_time).to_pydatetime()

        # 构建显示文本
        text_lines = [f"时间: {nearest_time.strftime('%H:%M')}"]

        # 对每条折线获取对应的值
        for line, label in zip(self.lines, self.labels):
            if nearest_idx < len(line.get_ydata()):
                y_val = line.get_ydata()[nearest_idx]
                text_lines.append(f"{label}: {y_val:.2f}")

        # 更新悬停文本
        self.hover_text.set_text('\n'.join(text_lines))
        self.hover_text.set_position((0.98, 0.98))
        self.hover_text.set_visible(True)
        self.hover_text.set_va('top')
        self.hover_text.set_ha('right')

        self.canvas.draw_idle()

    def on_pick(self, event):
        """点击折线事件处理，选中/取消选中折线"""
        if event.mouseevent.button != 1:  # 只响应左键
            return

        clicked_line = event.artist

        # 如果点击的是已选中的线，取消选中
        if self.selected_line == clicked_line:
            self.selected_line.set_linewidth(1.5)
            self.selected_line.set_alpha(0.8)
            self.selected_line = None
            self.selected_label = None
        else:
            # 恢复之前选中的线
            if self.selected_line is not None:
                self.selected_line.set_linewidth(1.5)
                self.selected_line.set_alpha(0.8)

            # 选中新线
            self.selected_line = clicked_line
            # 找到对应的标签
            for line, label in zip(self.lines, self.labels):
                if line == clicked_line:
                    self.selected_label = label
                    break

            # 高亮选中线
            self.selected_line.set_linewidth(3.0)
            self.selected_line.set_alpha(1.0)

        self.canvas.draw_idle()

    def plot_emo_trend(self, csv_path='data/emo_data.csv', ax=None, selected_filters=None, canvas=None, figure=None):
        import matplotlib.pyplot as plt

        DATA_GROUPS = {
            '今天涨停表现': ['连板数', '涨停数量', '跌停数量', '炸板数量', '炸板率'],
            '昨天涨停表现': ['昨涨停平均收益', '昨涨停上涨比率', '昨涨停下跌比率', '连板晋级率'],
            '赚钱效应': ['M上涨率', 'M下跌率', 'M平盘率', '非一字涨停', '非一字跌停',
                         'ST涨停', 'ST跌停', '活跃度']
        }

        use_sample_data = False
        df = None

        if not os.path.exists(csv_path):
            print(f"⚠️ 文件不存在: {csv_path}")
            use_sample_data = True
        else:
            try:
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
                if df.empty:
                    print("⚠️ 数据为空")
                    use_sample_data = True
                elif '时间' not in df.columns:
                    print("❌ 数据中缺少 '时间' 列")
                    use_sample_data = True
            except Exception as e:
                print(f"❌ 读取文件失败: {e}")
                use_sample_data = True

        if use_sample_data:
            self._show_sample_data(ax, canvas, selected_filters, figure)
            return

        print(f"📋 CSV实际包含的列名: {list(df.columns)}")

        df['时间'] = pd.to_datetime(df['时间'])
        df = df.sort_values('时间')
        # ===== 新增：只显示最近N天的数据 =====
        days_to_show = 2 # 修改这个数字可以调整显示天数
        unique_dates = df['时间'].dt.date.unique()
        if len(unique_dates) > days_to_show:
            cutoff_date = sorted(unique_dates)[-days_to_show]
            df = df[df['时间'].dt.date >= cutoff_date]
            print(f"📊 只显示最近 {days_to_show} 天的数据")
        # ===== 新增结束 =====

        # 定义交易时间段
        start_am = pd.to_datetime("09:30").time()
        end_am = pd.to_datetime("11:30").time()
        start_pm = pd.to_datetime("13:00").time()
        end_pm = pd.to_datetime("15:00").time()

        times = df['时间'].dt.time

        # 筛选交易时间数据
        mask = (
                ((times >= start_am) & (times <= end_am)) |
                ((times >= start_pm) & (times <= end_pm))
        )

        # 关键修改：只保留交易时间的数据
        original_count = len(df)
        df = df[mask]
        filtered_count = len(df)
        print(f"✅ 数据筛选完成：保留 {filtered_count} 条交易时间记录 (原始 {original_count} 条)")

        if df.empty:
            print("⚠️ 筛选后数据为空")
            self._show_sample_data(ax, canvas, selected_filters, figure)
            return

        # 重新赋值索引，使其连续（0, 1, 2, 3...）
        df = df.reset_index(drop=True)

        # 生成连续的 X 轴索引
        x_values = np.arange(len(df))

        # 将 DataFrame 赋值给类成员，供 on_motion_notify 使用
        self.df_plot = df

        # 查找匹配的列
        def find_matching_columns(filter_name, df_columns):
            """查找匹配的列名"""
            if filter_name in df_columns:
                return [filter_name]
            base_name = filter_name.replace('', '').replace('', '')
            matching = [col for col in df_columns if
                        col.startswith(base_name) and (col.endswith('') or col.endswith(''))]
            if matching:
                return matching
            return []

        all_group_columns = []

        if selected_filters:
            for filter_name in selected_filters:
                matching_cols = find_matching_columns(filter_name, df.columns)
                for col in matching_cols:
                    all_group_columns.append(("筛选列", col))
                    print(f"✅ 匹配到列: {filter_name} -> {col}")
        else:
            for group_name, columns in DATA_GROUPS.items():
                for col in columns:
                    if col in df.columns:
                        all_group_columns.append((group_name, col))

        if not all_group_columns:
            print("⚠️ 未找到任何匹配的列，绘制所有数值型列...")
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if '时间' in numeric_cols: numeric_cols.remove('时间')
            all_group_columns = [("自动识别列", col) for col in numeric_cols]

        if not all_group_columns:
            print("❌ 数据中也没有可用的数值列")
            return

        if ax is None:
            fig = plt.figure(figsize=(18, 10))
            ax_main = plt.axes([0.05, 0.15, 0.90, 0.80])
            new_window = True
        else:
            ax_main = ax
            new_window = False

        # 设置当前绘图区域和画布
        self.ax_main = ax_main
        self.canvas = canvas
        self.figure = figure

        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        ax_main.clear()

        # 清空折线和标签列表
        self.lines = []
        self.labels = []

        color_list = plt.cm.tab10(np.linspace(0, 1, 10))
        plot_count = 0

        # 收集所有Y值用于自动调整纵坐标
        all_y_values = []

        for idx, (group_name, col) in enumerate(all_group_columns):
            y_data = df[col].ffill().bfill()
            all_y_values.extend(y_data.values)

            color = color_list[idx % len(color_list)]

            # 使用 x_values (索引) 作为 X 轴
            line = ax_main.plot(x_values, y_data,
                                label=col,
                                linewidth=1.5, alpha=0.8,
                                marker='o', markersize=2,
                                color=color,
                                picker=5)[0]
            self.lines.append(line)
            self.labels.append(col)
            plot_count += 1

        print(f"✅ 成功绘制 {plot_count} 条曲线")

        # 根据数据范围自动调整纵坐标
        if all_y_values:
            y_min, y_max = np.min(all_y_values), np.max(all_y_values)
            y_range = y_max - y_min
            if y_range > 0:
                margin = y_range * 0.1
                ax_main.set_ylim(y_min - margin, y_max + margin)
            else:
                margin = 5 if y_max > 10 else 1
                ax_main.set_ylim(y_min - margin, y_max + margin)
            print(f"📊 纵坐标范围: {y_min:.2f} ~ {y_max:.2f}")
        else:
            ax_main.set_ylim(0, 100)

        # ==========================================
        # 设置 X 轴刻度和标签 - 只显示交易时间
        # ==========================================
        tick_indices = []
        tick_labels = []
        date_change_indices = []
        half_hour_indices = []  # 【新增】30分钟位置索引
        prev_date = None

        for idx, row in df.iterrows():
            t = row['时间']
            if pd.isnull(t): continue
            current_date = t.date()
            # 检测日期变化
            if prev_date is not None and current_date != prev_date:
                date_change_indices.append(idx)

            prev_date = current_date
            # 【新增】每30分钟记录一次（09:30, 10:00, 10:30, 11:00...）
            if t.minute == 0 or t.minute == 30:
                half_hour_indices.append(idx)

            # 筛选 00分 或 30分
            if t.minute % 60 == 0:
                tick_indices.append(idx)
                tick_labels.append(t.strftime('%m-%d %H:%M'))

        # 设置刻度
        ax_main.set_xticks(tick_indices)
        ax_main.set_xticklabels(tick_labels)
        # 【新增】画每30分钟的纵向虚线（浅色细线）
        for half_hour_idx in half_hour_indices:
            ax_main.axvline(x=half_hour_idx, color='blue', linestyle=':', alpha=0.5, linewidth=0.8)

        # 在日期变化处画纵向虚线
        for change_idx in date_change_indices:
            ax_main.axvline(x=change_idx, color='gray', linestyle='--', alpha=0.5, linewidth=1)

        # 设置标签旋转，防止重叠
        plt.setp(ax_main.get_xticklabels(), rotation=45, ha='right')

        ax_main.grid(True, linestyle='--', alpha=0.5, axis='y')

        if plot_count > 0:
            # 图例位置调整到上方
            ax_main.legend(
                loc='upper center',
                bbox_to_anchor=(0.5, 1.08),
                ncol=min(6, plot_count),
                fontsize=8,
                frameon=False
            )

        # 创建悬停文本标签
        if self.hover_text is None:
            self.hover_text = ax_main.text(
                0, 0, '',
                transform=ax_main.transAxes,
                fontsize=9,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                visible=False
            )
        else:
            self.hover_text.set_visible(False)

        # 设置事件监听器（只设置一次，避免重复）
        if not hasattr(self, '_events_connected') or not self._events_connected:
            if canvas:
                canvas.mpl_connect('motion_notify_event', self.on_motion_notify)
                canvas.mpl_connect('pick_event', self.on_pick)
                self._events_connected = True

        # 调整布局以适应上方图例和悬停文本
        if not new_window and figure:
            figure.tight_layout(rect=[0, 0.03, 1, 0.95])

        if new_window:
            plt.show()
        else:
            if canvas:
                canvas.draw()

    def _show_sample_data(self, ax, canvas, selected_filters=None, figure=None):
        import matplotlib.pyplot as plt

        print("显示示例数据...")

        if ax is None:
            fig = plt.figure(figsize=(18, 10))
            ax_main = plt.axes([0.05, 0.15, 0.90, 0.80])
            new_window = True
        else:
            ax_main = ax
            new_window = False

        # 设置当前绘图区域和画布
        self.ax_main = ax_main
        self.canvas = canvas
        self.figure = figure

        ax_main.clear()

        # 清空折线和标签列表
        self.lines = []
        self.labels = []

        # 生成交易时间的时间点
        am_times = pd.date_range('09:30', '11:30', freq='15min')
        pm_times = pd.date_range('13:00', '15:00', freq='15min')
        all_times = list(am_times) + list(pm_times)

        # 生成索引作为 X 轴
        x_values = np.arange(len(all_times))
        # 保存 DataFrame 供鼠标事件使用
        self.df_plot = pd.DataFrame({'时间': all_times})

        if selected_filters:
            labels = selected_filters[:10]
        else:
            labels = ['示例指标A', '示例指标B', '示例指标C', '示例指标D']

        colors = plt.cm.tab10(np.linspace(0, 1, len(labels)))
        all_y_values = []

        for i, (color, label) in enumerate(zip(colors, labels)):
            base_value = 40 + i * 10
            values = np.random.randint(base_value - 10, base_value + 20, len(all_times))
            all_y_values.extend(values)

            # 使用 x_values (索引) 作为 X 轴
            line = ax_main.plot(x_values, values,
                                label=label,
                                linewidth=1.5, alpha=0.8,
                                color=color, marker='o', markersize=2,
                                picker=5)[0]
            self.lines.append(line)
            self.labels.append(label)

        # 根据数据范围自动调整纵坐标
        if all_y_values:
            y_min, y_max = np.min(all_y_values), np.max(all_y_values)
            y_range = y_max - y_min
            if y_range > 0:
                margin = y_range * 0.1
                ax_main.set_ylim(y_min - margin, y_max + margin)
            else:
                margin = 5 if y_max > 10 else 1
                ax_main.set_ylim(y_min - margin, y_max + margin)

        # 设置示例数据的 X 轴刻度 (只显示 HH:MM)
        tick_indices = []
        tick_labels = []
        for idx, t in enumerate(all_times):
            if t.minute % 30 == 0:
                tick_indices.append(idx)
                tick_labels.append(t.strftime('%H:%M'))

        ax_main.set_xticks(tick_indices)
        ax_main.set_xticklabels(tick_labels)
        plt.setp(ax_main.get_xticklabels(), rotation=45, ha='right')

        ax_main.set_xlabel('时间', fontsize=12)
        ax_main.set_ylabel('数值 (%)', fontsize=12)
        ax_main.grid(True, linestyle='--', alpha=0.5, axis='y')

        if len(labels) > 0:
            ax_main.legend(
                loc='upper center',
                bbox_to_anchor=(0.5, 1.08),
                ncol=min(4, len(labels)),
                fontsize=8,
                frameon=False
            )

        # 创建悬停文本标签
        if self.hover_text is None:
            self.hover_text = ax_main.text(
                0, 0, '',
                transform=ax_main.transAxes,
                fontsize=9,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                visible=False
            )
        else:
            self.hover_text.set_visible(False)

        # 设置事件监听器（只设置一次，避免重复）
        if not hasattr(self, '_events_connected') or not self._events_connected:
            if canvas:
                canvas.mpl_connect('motion_notify_event', self.on_motion_notify)
                canvas.mpl_connect('pick_event', self.on_pick)
                self._events_connected = True

        # 调整布局
        if not new_window and figure:
            figure.tight_layout(rect=[0, 0.03, 1, 0.95])

        if new_window:
            plt.show()
        else:
            if canvas:
                canvas.draw()


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import sys
    import traceback


    def handle_exception(exc_type, exc_value, exc_traceback):
        """全局异常处理"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print("=" * 60)
        print("发生未捕获的异常:")
        print(error_msg)
        print("=" * 60)

        # 尝试显示错误对话框
        try:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "程序错误",
                f"发生未捕获的异常:\n{exc_value}\n\n详细信息已输出到控制台。"
            )
        except:
            pass


    # 设置全局异常处理器
    sys.excepthook = handle_exception

    try:
        app = QtWidgets.QApplication(sys.argv)
        window = QtWidgets.QMainWindow()
        ui = MainWindow()
        ui.setupUi(window)
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"主程序启动失败: {e}")
        traceback.print_exc()
