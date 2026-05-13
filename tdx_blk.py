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
import chardet  # 【新增】添加缺失的导入
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QHeaderView, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QCheckBox, QPushButton, \
    QFrame, QLabel, QComboBox, QGroupBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer  # 【新增】导入 QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import matplotlib

matplotlib.use('Qt5Agg')


class ouput_block_codes:
    def detect_file_encoding(file_path):
        """
        检测文件编码

        Args:
            file_path (str): 文件路径

        Returns:
            str: 检测到的编码格式
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # 读取前10000字节进行检测
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']
                print(f"📝 检测到文件编码: {encoding} (置信度: {confidence:.2%})")
                return encoding
        except Exception as e:
            print(f"⚠️ 编码检测失败: {str(e)}")
            return 'gbk'  # 默认编码

    def extract_block_codes_to_file(input_file='板块指数.txt', output_file='data\\blk.txt', exclude_codes=None):
        """
        从板块指数文件中提取代码列，每行一个代码保存到指定文件
        支持自动检测文件编码

        Args:
            input_file (str): 输入的板块指数文件路径
            output_file (str): 输出的代码文件路径
            exclude_codes (list): 需要排除的代码列表，例如 ['880001', '880002']

        Returns:
            list: 提取的代码列表（已排除指定代码）
        """
        exclude_codes = [
            '880505',  # 稀缺资源
            '880586',  # 土地流转
            '880594',  # 一带一路
            '880741',  # 代糖概念
            '880642',  # 供销社
            '880671',  # 中特估
            '880923',  # 赛马概念
            '880575',  # 地热能
            '880501',  # 含H股
            '880727',  # 盐湖提锂
            '880584',  # 石墨烯
            '880634',  # 含GDR
            '880502',  # 含B股
            '880564',  # 白酒概念
            '880515',  # 通达信88
            '880955',  # 乡村振兴
            '880971',  # 降解塑料
            '880568',  # 生物质能
            '880972',  # 雅江水电概念
            '880911',  # 雄安新区
            '880635',  # 先进封装
            '880637',  # EDA概念
            '880650',  # 血氧仪
            '880519',  # 碳中和
            '880610',  # 中俄贸易
            '880940',  # PPP概念
            '880524',  # 含可转债
            '880662',  # 时空大数据
            '880558',  # 节能环保
            '880529',  # 次新股
            '880967',  # 数字货币
            '880591',  # 上海自贸
            '880572',  # 新零售
            '880739',  # 边缘计算
            '880919',  # 粤港澳
            '880926',  # 垃圾分类
            '880614',  # 绿色建筑
            '880961',  # 小米概念
            '880954',  # 大数据
            '880540',  # 创投概念
            '880946',  # 区块链
            '880720',  # 抖音概念
            '880621',  # NFT概念
            '880525',  # 高铁
            '880762',  # 信创
            '880939',  # 无人机
            '880516',  # ST板块
            '880574',  # 苹果概念
            '880921',  # 阿里概念
            '880951',  # 新能源车
            '880696',  # 小米汽车概念
            '880748',  # 元宇宙概念
            '880560',  # 高端装备
            '880569',  # 3D打印
            '880577',  # 安防服务
            '880956',  # 腾讯概念
            '880711',  # 操作系统
            '880791',  # 网红经济
            '880530',  # 合成生物
            '880555',  # 财税数字化
            '880704',  # 工业大麻
            '880605',  # 装配式建筑
            '880977',  # BIPV概念
            '880902',  # 特斯拉概念
            '880643',  # Web3概念
            '880598',  # 博彩概念
            '880795',  # 口罩防护
            '880950',  # 军民融合
            '880647',  # 数据确权
            '880962',  # 百度概念
            '880718',  # 小红书概念
            '880616',  # 大飞机
        ]

        # 尝试的编码列表
        encodings_to_try = ['gbk', 'gb18030', 'gb2312', 'utf-8', 'utf-8-sig']

        # 首先尝试自动检测编码
        detected_encoding = self.detect_file_encoding(input_file)
        if detected_encoding and detected_encoding.lower() not in [enc.lower() for enc in encodings_to_try]:
            encodings_to_try.insert(0, detected_encoding)

        df = None
        used_encoding = None

        # 尝试不同编码读取文件
        for encoding in encodings_to_try:
            try:
                print(f"🔄 尝试使用编码: {encoding}")
                df = pd.read_csv(input_file, sep='\t', encoding=encoding)
                used_encoding = encoding
                print(f"✅ 成功使用 {encoding} 编码读取文件")
                break
            except UnicodeDecodeError:
                print(f"❌ {encoding} 编码失败，继续尝试...")
                continue
            except Exception as e:
                print(f"⚠️ 使用 {encoding} 编码时出错: {str(e)}")
                continue

        if df is None:
            print(f"❌ 所有编码尝试失败，无法读取文件")
            return []

        try:
            # 打印列名以便调试
            print(f"📋 文件列名: {list(df.columns)}")

            # 提取代码列（第一列）
            if '代码' in df.columns:
                codes = df['代码'].tolist()
            elif len(df.columns) > 0:
                # 如果没有'代码'列名，取第一列
                codes = df.iloc[:, 0].tolist()
            else:
                print(f"❌ 文件没有可用的列")
                return []

            # 过滤空值和非数值代码
            codes = [str(code).strip() for code in codes if
                     pd.notna(code) and str(code).strip() and str(code).strip() != '代码']

            # 过滤可能的标题行
            codes = [code for code in codes if code.isdigit() or (code.startswith('8') and len(code) == 6)]

            # ================= 新增：排除功能开始 =================
            if exclude_codes:
                # 将排除列表中的代码统一转为字符串并去除空格
                exclude_list = [str(code).strip() for code in exclude_codes]
                # 计算排除前的数量
                before_count = len(codes)
                # 执行过滤
                codes = [code for code in codes if code not in exclude_list]
                after_count = len(codes)
                print(f"🚫 已排除 {before_count - after_count} 个指定代码: {exclude_list}")
            # ================= 新增：排除功能结束 =================

            if not codes:
                print(f"⚠️ 未找到有效的板块代码")
                return []

            # 给每个代码添加 .SH 后缀
            codes = [f"{code}.SH" for code in codes]

            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # 写入文件，每行一个代码
            with open(output_file, 'w', encoding='utf-8') as f:
                for code in codes:
                    f.write(f"{code}\n")

            print(f"✅ 成功提取 {len(codes)} 个板块代码到 {output_file}")
            print(f"📝 使用的文件编码: {used_encoding}")

            return codes

        except Exception as e:
            print(f"❌ 提取代码时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []


# ================= 新增结束 =================


class MainWindow(object):

    # ================= 新增：自动刷新控制逻辑 =================
    def on_auto_refresh_toggled(self, checked):
        """
        自动刷新复选框状态改变

        Args:
            checked: 是否选中
        """
        if checked:
            # 启动自动刷新
            self.auto_refresh_timer.start(30000)  # 30秒 = 30000毫秒
            self.lbl_auto_refresh_status.setText("开启")
            self.lbl_auto_refresh_status.setStyleSheet("color: green; font-weight: bold;")
            print("✅ 自动刷新已开启 (每30秒)")
            # 立即刷新一次
            self.refresh_chart()
        else:
            # 停止自动刷新
            self.auto_refresh_timer.stop()
            self.lbl_auto_refresh_status.setText("关闭")
            self.lbl_auto_refresh_status.setStyleSheet("color: gray; font-weight: normal;")
            print("⏸️ 自动刷新已停止")

        # 保存自动刷新状态
        self.save_auto_refresh_state()

    def save_auto_refresh_state(self):
        """保存自动刷新状态到配置文件"""
        try:
            config_file = 'filter_config.json'
            data = {}
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            data['auto_refresh_enabled'] = self.chk_auto_refresh.isChecked()

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️ 保存自动刷新状态失败: {e}")

    def load_auto_refresh_state(self):
        """加载自动刷新状态"""
        try:
            config_file = 'filter_config.json'
            if not os.path.exists(config_file):
                # 默认开启自动刷新
                self.chk_auto_refresh.setChecked(True)
                self.on_auto_refresh_toggled(True)
                return

            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            auto_refresh_enabled = data.get('auto_refresh_enabled', True)
            self.chk_auto_refresh.setChecked(auto_refresh_enabled)
            self.on_auto_refresh_toggled(auto_refresh_enabled)
        except Exception as e:
            print(f"⚠️ 加载自动刷新状态失败: {e}")
            # 默认开启自动刷新
            self.chk_auto_refresh.setChecked(True)
            self.on_auto_refresh_toggled(True)

    # ================= 新增：上午/下午切换逻辑 =================
    def on_morning_clicked(self):
        """点击上午按钮"""
        self.btn_morning.setStyleSheet("""
            QPushButton {
                background-color: rgb(0, 170, 255);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: rgb(0, 140, 220);
            }
            QPushButton:pressed {
                background-color: rgb(0, 120, 200);
            }
        """)
        self.btn_afternoon.setStyleSheet("""
            QPushButton {
                background-color: rgb(200, 200, 200);
                color: black;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: rgb(180, 180, 180);
            }
            QPushButton:pressed {
                background-color: rgb(160, 160, 160);
            }
        """)
        self.kline.time_period = 'morning'
        self.refresh_chart()

    def on_afternoon_clicked(self):
        """点击下午按钮"""
        self.btn_morning.setStyleSheet("""
            QPushButton {
                background-color: rgb(200, 200, 200);
                color: black;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: rgb(180, 180, 180);
            }
            QPushButton:pressed {
                background-color: rgb(160, 160, 160);
            }
        """)
        self.btn_afternoon.setStyleSheet("""
            QPushButton {
                background-color: rgb(0, 170, 255);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: rgb(0, 140, 220);
            }
            QPushButton:pressed {
                background-color: rgb(0, 120, 200);
            }
        """)
        self.kline.time_period = 'afternoon'
        self.refresh_chart()

    # ================= 新增结束 =================

    # ================= 图表刷新方法 =================
    def refresh_chart(self):
        """根据当前时间段刷新图表 - 显示所有板块的涨幅折线图"""
        # 防止在加载配置时触发重复刷新
        print("🔄 刷新图表...")

        # 显示所有板块的涨幅趋势
        self.kline.plot_board_change_trend(
            csv_path='data\\板块今日价.csv',
            ax=self.ax_main,
            canvas=self.canvas,
            figure=self.figure,
            selected_codes=None  # None表示显示所有板块
        )

    # ================= 新增：图表刷新方法 =================
    def refresh_chart_mode(self):
        """刷新图表显示"""
        print("🔄 刷新板块涨幅折线图...")
        self.refresh_chart()

    # ================= 新增结束 =================

    # ================= 数据下载相关方法 =================
    def on_down(self):
        """执行板块代码提取"""
        print("🔄 开始提取板块代码...")

        # 更新UI状态
        self.btn_gn_update.setText("正在更新...")
        self.btn_gn_update.setStyleSheet("""
            QPushButton {
                background-color: rgb(255, 165, 0);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgb(255, 145, 0);
            }
            QPushButton:pressed {
                background-color: rgb(255, 125, 0);
            }
        """)
        self.gn_update_status.setText("正在提取板块代码...")
        self.gn_update_status.setStyleSheet("color: blue; font-weight: bold;")

        # 使用 window() 获取主窗口
        main_window = self.centralwidget.window()
        main_window.statusBar().showMessage("正在提取板块代码...", 2000)

        try:
            # 调用板块代码提取函数
            codes = ouput_block_codes.extract_block_codes_to_file()

            # 恢复按钮状态
            self.btn_gn_update.setText("板块概念更新")
            self.btn_gn_update.setStyleSheet("""
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

            if codes:
                self.gn_update_status.setText(f"✅ 成功提取 {len(codes)} 个板块代码")
                self.gn_update_status.setStyleSheet("color: green; font-weight: bold;")
                main_window.statusBar().showMessage(f"板块代码提取完成，共 {len(codes)} 个代码", 3000)

                # 刷新图表
                self.refresh_chart()
            else:
                self.gn_update_status.setText("❌ 提取失败，请检查文件")
                self.gn_update_status.setStyleSheet("color: red; font-weight: bold;")
                main_window.statusBar().showMessage("板块代码提取失败", 3000)

        except Exception as e:
            print(f"❌ 提取板块代码时出错: {e}")
            self.btn_gn_update.setText("板块概念更新")
            self.btn_gn_update.setStyleSheet("""
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
            self.gn_update_status.setText("❌ 提取出错")
            self.gn_update_status.setStyleSheet("color: red; font-weight: bold;")

    def on_update_log(self, message):
        """处理下载日志"""
        # 更新状态标签（只显示最后一条消息）
        self.gn_update_status.setText(message)

        # 根据消息内容设置颜色
        if "❌" in message or "错误" in message or "失败" in message:
            self.gn_update_status.setStyleSheet("color: red; font-weight: bold;")
        elif "✅" in message or "成功" in message:
            self.gn_update_status.setStyleSheet("color: green; font-weight: bold;")
        elif "🚀" in message or "正在" in message:
            self.gn_update_status.setStyleSheet("color: blue; font-weight: bold;")
        else:
            self.gn_update_status.setStyleSheet("color: black; font-weight: normal;")

        # 同时打印到控制台
        print(f"[下载日志] {message}")

    def on_update_finished(self):
        """下载完成"""
        print("✅ 数据下载线程已结束")

        # 更新UI状态
        self.btn_gn_update.setText("自动下载")
        self.btn_gn_update.setStyleSheet("""
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
        self.gn_update_status.setText("已停止")
        self.gn_update_status.setStyleSheet("color: gray; font-weight: normal;")

        # 使用 window() 获取主窗口
        main_window = self.centralwidget.window()
        main_window.statusBar().showMessage("数据下载已停止", 3000)

    # ================= 新增结束 =================

    # ================= 图表刷新方法结束 =================

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

        # 板块概念更新按钮
        self.btn_gn_update = QtWidgets.QPushButton("板块概念更新", self.tool_bar_widget)
        self.btn_gn_update.setObjectName("btn_gn_update")
        self.btn_gn_update.setStyleSheet(tool_btn_style)
        tool_bar_layout.addWidget(self.btn_gn_update)

        # 更新状态标签
        tool_bar_layout.addSpacing(20)
        self.gn_update_status = QtWidgets.QLabel("就绪", self.tool_bar_widget)
        self.gn_update_status.setObjectName("gn_update_status")
        self.gn_update_status.setStyleSheet("color: gray; font-weight: normal;")
        self.gn_update_status.setFixedWidth(300)
        tool_bar_layout.addWidget(self.gn_update_status)

        # ================= 新增：上午/下午选择按钮 =================
        tool_bar_layout.addSpacing(20)

        # 上午按钮（默认选中）
        self.btn_morning = QtWidgets.QPushButton("上午", self.tool_bar_widget)
        self.btn_morning.setObjectName("btn_morning")
        self.btn_morning.setStyleSheet("""
            QPushButton {
                background-color: rgb(0, 170, 255);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: rgb(0, 140, 220);
            }
            QPushButton:pressed {
                background-color: rgb(0, 120, 200);
            }
        """)
        tool_bar_layout.addWidget(self.btn_morning)

        # 下午按钮
        self.btn_afternoon = QtWidgets.QPushButton("下午", self.tool_bar_widget)
        self.btn_afternoon.setObjectName("btn_afternoon")
        self.btn_afternoon.setStyleSheet("""
            QPushButton {
                background-color: rgb(200, 200, 200);
                color: black;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: rgb(180, 180, 180);
            }
            QPushButton:pressed {
                background-color: rgb(160, 160, 160);
            }
        """)
        tool_bar_layout.addWidget(self.btn_afternoon)
        # ================= 新增结束 =================

        # ================= 新增：自动刷新控制 =================
        tool_bar_layout.addSpacing(20)
        self.chk_auto_refresh = QCheckBox("自动刷新", self.tool_bar_widget)
        self.chk_auto_refresh.setObjectName("chk_auto_refresh")
        self.chk_auto_refresh.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                font-weight: bold;
                color: black;
            }
        """)
        tool_bar_layout.addWidget(self.chk_auto_refresh)

        # 自动刷新状态标签
        self.lbl_auto_refresh_status = QtWidgets.QLabel("关闭", self.tool_bar_widget)
        self.lbl_auto_refresh_status.setObjectName("lbl_auto_refresh_status")
        self.lbl_auto_refresh_status.setStyleSheet("color: gray; font-weight: normal;")
        self.lbl_auto_refresh_status.setFixedWidth(60)
        tool_bar_layout.addWidget(self.lbl_auto_refresh_status)
        # ================= 新增结束 =================

        # ================= 新增：图表模式切换按钮 =================
        tool_bar_layout.addSpacing(20)
        self.btn_toggle_chart = QtWidgets.QPushButton("刷新图表", self.tool_bar_widget)

        self.btn_toggle_chart.setObjectName("btn_toggle_chart")
        self.btn_toggle_chart.setStyleSheet("""
            QPushButton {
                background-color: rgb(100, 150, 200);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgb(80, 130, 180);
            }
            QPushButton:pressed {
                background-color: rgb(60, 110, 160);
            }
        """)
        tool_bar_layout.addWidget(self.btn_toggle_chart)
        # ================= 新增结束 =================

        tool_bar_layout.addSpacing(100)
        self.btn_del_history = QtWidgets.QPushButton("删除历史数据", self.tool_bar_widget)
        self.btn_del_history.setObjectName("btn_del_history")
        self.btn_del_history.setStyleSheet(tool_btn_style)
        tool_bar_layout.addWidget(self.btn_del_history)

        tool_bar_layout.addStretch()
        main_layout.addWidget(self.tool_bar_widget)

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

        # 【修改】初始化 kline，确保在加载配置之前
        self.kline = auto_kline()

        # 【修改】初始化下载线程为 None
        self.update_thread = None
        # 【修改】初始化计算线程为 None
        self.calc_thread = None

        # ================= 新增：创建自动刷新定时器 =================
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.setInterval(30000)  # 30秒 = 半分钟
        self.auto_refresh_timer.timeout.connect(self.refresh_chart)
        print("✅ 自动刷新定时器已创建 (每30秒)")
        # ================= 新增结束 =================

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # ================= 事件连接 =================
        self.btn_gn_update.clicked.connect(self.on_down)
        self.btn_del_history.clicked.connect(self.on_del)
        # 【新增】连接新按钮
        self.btn_toggle_chart.clicked.connect(self.refresh_chart_mode)
        # 【新增】连接上午/下午按钮
        self.btn_morning.clicked.connect(self.on_morning_clicked)
        self.btn_afternoon.clicked.connect(self.on_afternoon_clicked)
        # 【新增】连接自动刷新复选框
        self.chk_auto_refresh.toggled.connect(self.on_auto_refresh_toggled)

        # ================= 连接结束 =================

        # ================= 新增：窗口关闭事件 =================
        # 确保定时器在窗口关闭时停止
        def closeEvent_override(event):
            if hasattr(self, 'auto_refresh_timer'):
                self.auto_refresh_timer.stop()
                print("✅ 自动刷新定时器已停止")
            event.accept()

        MainWindow.closeEvent = closeEvent_override
        # ================= 新增结束 =================

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "板块涨幅趋势"))
        self.banner.setText(_translate("MainWindow", "精准把握板块涨幅趋势，第一时间上车！"))

        self.init_chart()

    def init_chart(self):
        """初始化图表"""
        print("初始化图表...")
        # 默认使用上午时段
        self.kline.time_period = 'morning'
        # 加载自动刷新状态并启动
        self.load_auto_refresh_state()
        self.refresh_chart()

    # ================= 情绪计算相关方法 =================
    def on_cal(self):
        """启动/停止情绪计算"""
        if self.calc_thread is None or not self.calc_thread.isRunning():
            # 启动计算
            self.start_calc()
        else:
            # 停止计算
            self.stop_calc()

    def start_calc(self):
        """启动情绪计算"""
        print("🚀 启动自动计算...")
        # 这里需要实现计算逻辑
        pass

    def stop_calc(self):
        """停止情绪计算"""
        print("🛑 停止情绪计算...")
        # 这里需要实现停止逻辑
        pass

    def on_calc_log(self, message):
        """处理计算日志"""
        print(f"[计算日志] {message}")
        if "计算完成并保存" in message:
            self.refresh_chart()

    def on_calc_finished(self):
        """计算完成或线程结束"""
        print("✅ 情绪计算线程已结束")
        self.calc_thread = None

    # ================= 新增结束 =================

    def on_del(self):
        """删除历史数据文件"""
        import os
        from PyQt5.QtWidgets import QMessageBox
        from PyQt5.QtCore import QProcess

        try:
            # 定义要删除的文件列表
            files_to_delete = [
                'data/板块今日价.csv'
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
                    "没有找到需要删除的文件！\n\n板块今日价.csv"
                )
                return

            # 创建确认消息
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
                                failed_files.append(f"{os.path.basename(file_path)} (文件可能被占用）")
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
        self.selected_line = None
        self.selected_label = None
        self.hover_text = None
        self.lines = []
        self.labels = []
        self.df_plot = None
        self.ax_main = None # ✅ 新增：初始化属性
        self.canvas = None # ✅ 新增：初始化属性
        self.figure = None # ✅ 新增：初始化属性
        self.chart_mode = 'change'
        self.time_period = 'morning' # 新增：时间时段，morning或afternoon
        self._events_connected = False
        self.code_name_map = {} # ✅ 新增：代码名称映射字典

    def load_code_name_mapping(self, file_path):
        """ 从板块指数文件中加载代码和名称的映射关系 """
        # 检测文件编码
        encoding = self.detect_file_encoding(file_path)
        try:
            df = pd.read_csv(file_path, sep='\t', encoding=encoding)
            # 创建代码到名称的映射字典
            code_name_map = {}
            if '代码' in df.columns and '名称' in df.columns:
                for index, row in df.iterrows():
                    code = str(row['代码']).strip()
                    name = str(row['名称']).strip()
                    if code and name and code not in ['代码', '名称']:
                        self.code_name_map[code] = self.code_name_map.get(code, name)
            print(f"✅ 成功加载 {len(self.code_name_map)} 个板块代码名称映射")
            return True
        except Exception as e:
            print(f"❌ 加载代码名称映射失败: {e}")
            return False

    def detect_file_encoding(self, file_path):
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)
            result = chardet.detect(raw_data)
            return result['encoding']
        except Exception as e:
            print(f"❌ 编码检测失败: {e}")
            return 'gbk' # 默认编码

    def on_motion_notify(self, event):
        """鼠标移动事件处理，显示悬停信息 - 只显示涨幅"""
        # ✅ 新增：防御性检查，避免属性未初始化
        if self.ax_main is None:
            return
        if self.canvas is None:
            return
        if event.inaxes != self.ax_main:
            if self.hover_text:
                self.hover_text.set_visible(False)
                self.canvas.draw_idle()
            return

        if self.df_plot is None or self.df_plot.empty:
            return

        # X轴是整数索引，直接四舍五入找到最近的索引
        if event.xdata is None:
            return
        nearest_idx = int(np.round(event.xdata))

        # 边界检查
        if nearest_idx < 0:
            nearest_idx = 0
        elif nearest_idx >= len(self.df_plot):
            nearest_idx = len(self.df_plot) - 1

        # 获取对应的时间
        all_times = self.df_plot['时间'].unique()
        all_times_sorted = sorted(all_times)
        if nearest_idx >= len(all_times_sorted):
            return
        nearest_time = pd.Timestamp(all_times_sorted[nearest_idx])

        # 构建显示文本
        text_lines = [f"时间: {nearest_time.strftime('%H:%M')}"]
        # 对每条折线获取对应的涨幅值
        for line, label in zip(self.lines, self.labels):
            if nearest_idx < len(line.get_ydata()):
                y_val = line.get_ydata()[nearest_idx]
                text_lines.append(f"{label}: {y_val:.2f}%")

        # 更新悬停文本
        self.hover_text.set_text('\n'.join(text_lines))
        self.hover_text.set_position((0.98, 0.98))
        self.hover_text.set_visible(True)
        self.hover_text.set_va('top')
        self.hover_text.set_ha('right')
        self.canvas.draw_idle()

    # ======== 补充缺失的方法 _plot_example_chart ========
    def _plot_example_chart(self, ax):
        """绘制示例图表，当数据加载失败时显示"""
        ax.clear()
        ax.text(0.5, 0.5, '无有效数据\nNo Valid Data', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, fontsize=14)
        ax.set_title('板块涨幅趋势 (无数据)', fontsize=12, fontweight='bold')
        ax.set_xlabel('时间', fontsize=10)
        ax.set_ylabel('涨幅 (%)', fontsize=10)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        print("ℹ️ 显示示例图表")
    # ======== 补充结束 ========

    def plot_board_change_trend(self, csv_path, ax, canvas, figure, selected_codes=None):
        """ 绘制板块涨幅趋势折线图
        Args:
            csv_path (str): CSV文件路径
            ax: matplotlib轴对象
            canvas: canvas对象
            figure: figure对象
            selected_codes (list): 选中的代码列表，None表示显示所有
        """
        self.ax_main = ax
        self.canvas = canvas
        self.figure = figure

        # 清除之前的图表
        ax.clear()
        self.lines = []
        self.labels = []

        # 读取CSV文件
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception as e:
            print(f"❌ 读取CSV文件失败: {e}")
            self._plot_example_chart(ax) # 调用补充的方法
            canvas.draw()
            return

        if df.empty:
            print("⚠️ CSV文件为空")
            self._plot_example_chart(ax) # 调用补充的方法
            canvas.draw()
            return

        self.df_plot = df

        # 确定时间范围
        if self.time_period == 'morning':
            # 上午：09:30-11:30
            start_hour, start_minute = 9, 30
            end_hour, end_minute = 11, 30
            x_label = "时间 (上午)"
        else:
            # 下午：13:00-15:00
            start_hour, start_minute = 13, 0
            end_hour, end_minute = 15, 0
            x_label = "时间 (下午)"

        # 获取时间列（第一列）
        time_col = df.columns[0]

        # 解析时间并转换为分钟数
        # 【核心修复】使用 format='mixed' 自动推断时间格式
        # 解析时间并转换为分钟数
        # 【核心修复 + 优化】使用 format='mixed' 并避免 DataFrame 碎片化
        try:
            # 尝试解析时间，format='mixed' 能自动处理 'YYYY-MM-DD HH:MM:SS' 和 'HH:MM' 等多种格式
            time_obj_series = pd.to_datetime(df[time_col], format='mixed', errors='coerce')
            # 如果解析失败（产生 NaT），则整个列可能无效
            if time_obj_series.isna().all():
                raise ValueError("所有时间数据都无法解析")

            # 创建一个包含新列的字典
            new_columns = {
                'time_obj': time_obj_series,
                'time_minutes': time_obj_series.dt.hour * 60 + time_obj_series.dt.minute
            }
            # 使用 pd.concat 一次性添加所有新列，避免碎片化
            df = pd.concat([df, pd.DataFrame(new_columns)], axis=1)

        except Exception as e:
            print(f"❌ 时间解析失败: {e}")
            self._plot_example_chart(ax)  # 调用补充的方法
            canvas.draw()
            return

        # 过滤时间段数据
        try:
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            df_filtered = df[(df['time_minutes'] >= start_minutes) & (df['time_minutes'] <= end_minutes)]
        except Exception as e:
            print(f"❌ 时间过滤失败: {e}")
            self._plot_example_chart(ax) # 调用补充的方法
            canvas.draw()
            return

        if df_filtered.empty:
            print(f"⚠️ {self.time_period} 时段没有数据")
            self._plot_example_chart(ax) # 调用补充的方法
            canvas.draw()
            return

        # 获取要绘制的列
        columns_to_plot = []
        for col in df_filtered.columns:
            if col not in [time_col, 'time_obj', 'time_minutes']:
                columns_to_plot.append(col)

        print(f"📊 准备绘制 {len(columns_to_plot)} 条折线")

        # 绘制每列的折线
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
        for idx, col in enumerate(columns_to_plot):
            if selected_codes is not None and col not in selected_codes:
                continue
            try:
                x_data = df_filtered['time_minutes'].values
                y_data = df_filtered[col].values

                # 移除NaN值
                mask = ~np.isnan(y_data)
                x_data = x_data[mask]
                y_data = y_data[mask]

                if len(x_data) > 0:
                    line, = ax.plot(x_data, y_data, color=colors[idx % len(colors)], linewidth=1.0, alpha=0.7, label=col)
                    self.lines.append(line)
                    self.labels.append(col)
            except Exception as e:
                print(f"❌ 绘制列 {col} 失败: {e}")

        # 设置x轴刻度
        self._set_xtick_labels(ax, df_filtered, start_minutes, end_minutes)

        # 设置y轴范围（-7到1）
        ax.set_ylim(1, 7)

        # 添加零线
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)

        # 设置标题和标签
        period_name = "上午" if self.time_period == 'morning' else "下午"
        ax.set_title(f"板块涨幅趋势 ({period_name})", fontsize=12, fontweight='bold')
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel("涨幅 (%)", fontsize=10)

        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')

        # 启用鼠标交互
        # 启用鼠标交互
        if not self._events_connected:
            self.canvas.mpl_connect('motion_notify_event', self.on_motion_notify)
            self._events_connected = True

        # 创建或更新悬停文本对象
        if self.hover_text is None:
            # 在右上角创建一个初始为空、不可见的文本框
            self.hover_text = ax.text(0.98, 0.98, '', transform=ax.transAxes,
                                      verticalalignment='top', horizontalalignment='right',
                                      bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5),
                                      fontsize=9)
        else:
            # 如果已存在，确保它是可见的（虽然初始内容为空）
            self.hover_text.set_visible(True)

        canvas.draw()
        print(f"✅ 图表绘制完成，共 {len(self.lines)} 条折线")

    def _set_xtick_labels(self, ax, df_filtered, start_minutes, end_minutes):
        """设置X轴的刻度和标签"""
        # 计算主要刻度（每30分钟一个）
        major_ticks = np.arange(start_minutes, end_minutes + 1, 30)
        major_labels = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in major_ticks]
        ax.set_xticks(major_ticks)
        ax.set_xticklabels(major_labels, rotation=45, ha='right')

        # 如果数据点很多，可以考虑只显示主要刻度
        # 如果数据点较少，可以显示所有数据点的时间
        if len(df_filtered) <= 10:
            all_ticks = df_filtered['time_minutes'].unique()
            all_labels = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in all_ticks]
            ax.set_xticks(all_ticks)
            ax.set_xticklabels(all_labels, rotation=45, ha='right')
if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    ui = MainWindow()
    ui.setupUi(window)
    window.show()
    sys.exit(app.exec_())
