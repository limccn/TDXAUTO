# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, QGroupBox,
                             QLabel, QLineEdit, QPushButton, QComboBox, QRadioButton,
                             QTimeEdit, QHBoxLayout, QSpacerItem, QSizePolicy, QFileDialog, QMessageBox,
                             QVBoxLayout, QStackedWidget)  # 新增 QVBoxLayout, QStackedWidget
from PyQt5.QtGui import QPixmap, QFont, QIcon, QDoubleValidator
from PyQt5.QtCore import Qt, pyqtSlot, QRegExp, QTime, pyqtSignal
from PyQt5.QtGui import QRegExpValidator


class AddBuyStWindow(QMainWindow):
    # 定义信号（用于通知主窗口保存完成）
    st_saved = pyqtSignal(list, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 初始化声音下拉框列表
        self.alarm_sound_list = []
        self.file_alarm_sound_list = []

        # 存储各批次全仓单选按钮和策略Tab索引
        self.stock_full_radios = []
        self.file_full_radios = []

        # 初始化策略数据
        self.add_buy_st_stock_list = []
        self.add_buy_st_file_list = []

        # 新增：存储各批次控件引用
        self.stock_price_widgets = []
        self.stock_alarm_widgets = []

        self.file_price_widgets = []
        self.file_alarm_widgets = []


        # 新增：存储单选按钮引用
        self.stock_price_radio_groups = []
        self.stock_alarm_radio_groups = []
        self.file_alarm_radio_groups = []

        # 新增：用于管理价格条件切换的 QStackedWidget 列表
        self.price_stacked_widgets = []

        self.init_ui()
        self.init_signals()
        self.current_batch = 1
        self.file_current_batch = 1
        self.init_sound_combo_boxes()
        self.init_batch_visibility()
        self.on_stock_st_changed()
        self.on_file_st_changed()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("添加买入策略（多批次独立配置，最多4批）")
        self.setWindowIcon(QIcon("image/app4.ico"))
        self.resize(754, 558)

        # 居中显示
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

        # 创建主TabWidget并设置为中心部件（替代原绝对定位）
        self.tabWidget = QTabWidget()
        self.setCentralWidget(self.tabWidget)

        # 创建界面
        self.create_stock_single_tab()
        self.create_stock_folder_tab()
        self.tabWidget.setCurrentIndex(0)

    def init_batch_visibility(self):
        """初始化批次显隐"""
        for i in range(4):
            if i != 0:
                self.st_tab.setTabVisible(i, False)
        for i in range(4):
            if i != 0:
                self.file_st_tab.setTabVisible(i, False)

    def create_stock_single_tab(self):
        """创建单支股票设置Tab - 使用布局管理"""
        self.stock_single_widget = QWidget()
        main_layout = QVBoxLayout(self.stock_single_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === 步骤1 ===
        step1_layout = QHBoxLayout()
        step1_layout.setSpacing(10)

        self.step1_logo = QLabel()
        self.step1_logo.setPixmap(QPixmap("image/1.png"))
        self.step1_logo.setFixedSize(54, 61)

        self.buy_icon_label = QLabel()
        pixmap = QPixmap("image/buy.png")
        if pixmap.isNull():
            self.buy_icon_label.setText("")
            self.buy_icon_label.setAlignment(Qt.AlignCenter)
        else:
            self.buy_icon_label.setPixmap(pixmap.scaled(81, 91, Qt.KeepAspectRatio))
        self.buy_icon_label.setFixedSize(81, 91)

        self.step1_group = QGroupBox("第一步：基础设置")
        font = QFont("黑体", 10)
        self.step1_group.setFont(font)
        step1_inner_layout = QHBoxLayout()

        self.stock_code_label = QLabel("股票代码：")
        self.stock_code_label.setStyleSheet("color: rgb(85, 170, 0); font: 12pt '阿里巴巴普惠体 M'")

        self.stock_code_input = QLineEdit()
        self.stock_code_input.setPlaceholderText("代码")
        font_code = QFont("阿里巴巴普惠体 M", 16, QFont.Bold)
        self.stock_code_input.setFont(font_code)
        reg_exp = QRegExp(r'^\d{6}$')
        validator = QRegExpValidator(reg_exp, self.stock_code_input)
        self.stock_code_input.setValidator(validator)

        step1_inner_layout.addWidget(self.stock_code_label)
        step1_inner_layout.addWidget(self.stock_code_input)
        step1_inner_layout.addStretch()
        self.step1_group.setLayout(step1_inner_layout)

        step1_layout.addWidget(self.step1_logo)
        step1_layout.addWidget(self.step1_group)
        step1_layout.addStretch()
        step1_layout.addWidget(self.buy_icon_label)
        main_layout.addLayout(step1_layout)

        # === 步骤2 ===
        step2_layout = QHBoxLayout()
        step2_layout.setSpacing(10)

        self.step2_logo = QLabel()
        self.step2_logo.setPixmap(QPixmap("image/2.png"))
        self.step2_logo.setFixedSize(51, 61)

        self.step2_group = QGroupBox("第二步：策略分类")
        step2_inner_layout = QHBoxLayout()

        self.st_radio_price = QRadioButton("按股价")
        self.st_radio_rate = QRadioButton("按涨幅")
        self.st_radio_rate.setChecked(True)

        self.st_radio_immediate = QRadioButton("立即交易")

        step2_inner_layout.addWidget(self.st_radio_price)
        step2_inner_layout.addWidget(self.st_radio_rate)

        step2_inner_layout.addWidget(self.st_radio_immediate)
        step2_inner_layout.addStretch()
        self.step2_group.setLayout(step2_inner_layout)

        step2_layout.addWidget(self.step2_logo)
        step2_layout.addWidget(self.step2_group)
        main_layout.addLayout(step2_layout)

        # === 步骤3 ===
        step3_layout = QHBoxLayout()
        step3_layout.setSpacing(10)

        self.step3_logo = QLabel()
        self.step3_logo.setPixmap(QPixmap("image/3.png"))
        self.step3_logo.setFixedSize(54, 51)

        self.step3_group = QGroupBox("第三步：策略参数")
        step3_inner_layout = QVBoxLayout()

        self.st_tab = QTabWidget()
        self.st_tab.setTabPosition(QTabWidget.South)

        step3_inner_layout.addWidget(self.st_tab)
        self.step3_group.setLayout(step3_inner_layout)

        step3_layout.addWidget(self.step3_logo)
        step3_layout.addWidget(self.step3_group)
        main_layout.addLayout(step3_layout)

        # === 底部按钮 ===
        self.btn_layout = QHBoxLayout()

        self.add_batch_btn = QPushButton("增加第二批策略")
        self.add_batch_btn.setStyleSheet(
            "color: rgb(255, 255, 255); background-color: rgb(85, 0, 127); font: 16pt '阿里巴巴普惠体 M'")

        self.save_btn = QPushButton("保存策略")
        self.save_btn.setStyleSheet(
            "font: 20pt '阿里巴巴普惠体 M'; color: rgb(255, 255, 255); background-color: rgb(85, 170, 0)")

        spacer = QSpacerItem(100, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.btn_layout.addWidget(self.add_batch_btn)
        self.btn_layout.addItem(spacer)
        self.btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(self.btn_layout)

        self.tabWidget.addTab(self.stock_single_widget, "单支股票设置")

        # 创建批次Tab内容
        self.create_st_batch_tabs()

    def create_stock_folder_tab(self):
        """创建文件批量设置Tab - 使用布局管理"""
        self.stock_folder_widget = QWidget()
        main_layout = QVBoxLayout(self.stock_folder_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === 步骤1 ===
        step1_layout = QHBoxLayout()
        step1_layout.setSpacing(10)

        self.file_step1_logo = QLabel()
        self.file_step1_logo.setPixmap(QPixmap("image/1.png"))
        self.file_step1_logo.setFixedSize(54, 61)

        self.file_buy_icon_label = QLabel()
        pixmap = QPixmap("image/buy.png")
        if pixmap.isNull():
            self.file_buy_icon_label.setText("")
            self.file_buy_icon_label.setAlignment(Qt.AlignCenter)
        else:
            self.file_buy_icon_label.setPixmap(pixmap.scaled(81, 91, Qt.KeepAspectRatio))
        self.file_buy_icon_label.setFixedSize(81, 91)

        self.file_step1_group = QGroupBox("第一步：基础设置")
        font = QFont("黑体", 10)
        self.file_step1_group.setFont(font)
        step1_inner_layout = QHBoxLayout()

        self.folder_label = QLabel("TDX板块")
        self.folder_label.setStyleSheet("color: rgb(85, 170, 0); font: 12pt '阿里巴巴普惠体 M'")

        self.blk_name = QLineEdit()
        self.blk_name.setPlaceholderText(r"简要说明这个板块是什么内容")

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText(r"板块地址例如：T0002/blocknew/my_stocks.blk")

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")

        step1_inner_layout.addWidget(self.folder_label)
        step1_inner_layout.addWidget(self.blk_name)
        step1_inner_layout.addWidget(self.folder_input)
        step1_inner_layout.addWidget(self.browse_btn)
        self.file_step1_group.setLayout(step1_inner_layout)

        step1_layout.addWidget(self.file_step1_logo)
        step1_layout.addWidget(self.file_step1_group)
        step1_layout.addStretch()
        step1_layout.addWidget(self.file_buy_icon_label)
        main_layout.addLayout(step1_layout)

        # === 步骤2 ===
        step2_layout = QHBoxLayout()
        step2_layout.setSpacing(10)

        self.file_step2_logo = QLabel()
        self.file_step2_logo.setPixmap(QPixmap("image/2.png"))
        self.file_step2_logo.setFixedSize(51, 61)

        self.file_step2_group = QGroupBox("第二步：策略分类")
        step2_inner_layout = QHBoxLayout()

        self.file_radio_price = QRadioButton("按涨幅")
        self.file_radio_price.setChecked(True)


        self.file_radio_immediate = QRadioButton("立即交易")

        step2_inner_layout.addWidget(self.file_radio_price)


        step2_inner_layout.addWidget(self.file_radio_immediate)
        step2_inner_layout.addStretch()
        self.file_step2_group.setLayout(step2_inner_layout)

        step2_layout.addWidget(self.file_step2_logo)
        step2_layout.addWidget(self.file_step2_group)
        main_layout.addLayout(step2_layout)

        # === 步骤3 ===
        step3_layout = QHBoxLayout()
        step3_layout.setSpacing(10)

        self.file_step3_logo = QLabel()
        self.file_step3_logo.setPixmap(QPixmap("image/3.png"))
        self.file_step3_logo.setFixedSize(54, 51)

        self.file_step3_group = QGroupBox("第三步：策略参数")
        step3_inner_layout = QVBoxLayout()

        self.file_st_tab = QTabWidget()
        self.file_st_tab.setTabPosition(QTabWidget.South)

        step3_inner_layout.addWidget(self.file_st_tab)
        self.file_step3_group.setLayout(step3_inner_layout)

        step3_layout.addWidget(self.file_step3_logo)
        step3_layout.addWidget(self.file_step3_group)
        main_layout.addLayout(step3_layout)

        # === 底部按钮 ===
        self.file_btn_layout = QHBoxLayout()

        self.file_add_batch_btn = QPushButton("增加第二批策略")
        self.file_add_batch_btn.setStyleSheet(
            "color: rgb(255, 255, 255); background-color: rgb(85, 0, 127); font: 16pt '阿里巴巴普惠体 M'")

        self.file_save_btn = QPushButton("保存策略")
        self.file_save_btn.setStyleSheet(
            "font: 20pt '阿里巴巴普惠体 M'; color: rgb(255, 255, 255); background-color: rgb(85, 170, 0)")

        file_spacer = QSpacerItem(80, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.file_btn_layout.addWidget(self.file_add_batch_btn)
        self.file_btn_layout.addItem(file_spacer)
        self.file_btn_layout.addWidget(self.file_save_btn)

        main_layout.addLayout(self.file_btn_layout)

        self.tabWidget.addTab(self.stock_folder_widget, "按文件设置")

        self.create_file_st_batch_tabs()

    def init_sound_combo_boxes(self):
        """初始化声音下拉框"""
        sound_dir = "sounds"
        if not os.path.exists(sound_dir):
            os.makedirs(sound_dir)
            mp3_files = ["无报警音"]
        else:
            mp3_files = [f for f in os.listdir(sound_dir) if f.lower().endswith(".wav")]
            if not mp3_files:
                mp3_files = ["无报警音"]

        for combo in self.alarm_sound_list:
            combo.clear()
            combo.addItems(mp3_files)
            combo.setCurrentIndex(0)

        for combo in self.file_alarm_sound_list:
            combo.clear()
            combo.addItems(mp3_files)
            combo.setCurrentIndex(0)

    def create_st_batch_tabs(self):
        """创建单支股票的4个批次策略界面 - 使用布局管理"""
        self.price_rate_inputs = []
        self.alarm_rate_inputs = []
        self.price_compare_list = []
        self.alarm_compare_list = []
        self.target_price_inputs = []
        self.alarm_price_inputs = []

        self.stock_position_radios = []

        self.alarm_sound_list.clear()
        self.stock_full_radios.clear()
        self.stock_price_widgets.clear()
        self.stock_alarm_widgets.clear()

        self.stock_price_radio_groups.clear()
        self.stock_alarm_radio_groups.clear()
        self.price_stacked_widgets.clear()  # 清空堆栈列表

        for i in range(4):
            batch_widget = QWidget()
            batch_name = f"第{i + 1}批策略参数"

            # 使用垂直布局管理批次内部控件
            batch_layout = QVBoxLayout(batch_widget)
            batch_layout.setContentsMargins(5, 5, 5, 5)
            batch_layout.setSpacing(5)

            # === 价格条件区域：使用 QStackedWidget 切换显示 ===
            stacked_widget = QStackedWidget()

            # 页面0: 按股价
            price_by_value_widget = QWidget()
            price_by_value_layout = QHBoxLayout()
            price_by_value_label = QLabel("价格条件：")
            price_by_value_label.setStyleSheet("color: rgb(85, 170, 0); font: 12pt '阿里巴巴普惠体 M'")
            price_compare_A = QComboBox()
            price_compare_A.addItems([">=", "<="])
            target_price_input = QLineEdit()
            target_price_input.setPlaceholderText("请输入目标价")
            validator = QDoubleValidator(0.99, 1999.99, 2)
            validator.setNotation(QDoubleValidator.StandardNotation)
            target_price_input.setValidator(validator)
            self.target_price_inputs.append(target_price_input)

            price_by_value_layout.addWidget(price_by_value_label)
            price_by_value_layout.addWidget(price_compare_A)
            price_by_value_layout.addWidget(target_price_input)
            price_by_value_layout.addStretch()
            price_by_value_widget.setLayout(price_by_value_layout)

            # 页面1: 按涨幅
            price_by_rate_widget = QWidget()
            price_by_rate_layout = QHBoxLayout()
            price_by_rate_label = QLabel("价格条件：")
            price_by_rate_label.setStyleSheet("color: rgb(85, 170, 0); font: 12pt '阿里巴巴普惠体 M'")
            price_compare_B = QComboBox()
            price_compare_B.addItems([">=", "<="])
            radio_rate_input = QLineEdit()
            radio_rate_input.setPlaceholderText("涨幅")
            validator = QDoubleValidator(-20.0, 20.0, 2)
            validator.setNotation(QDoubleValidator.StandardNotation)
            radio_rate_input.setValidator(validator)
            self.price_rate_inputs.append(radio_rate_input)
            percent_label = QLabel("%")
            percent_label.setFont(QFont("Arial", 16))

            price_by_rate_layout.addWidget(price_by_rate_label)
            price_by_rate_layout.addWidget(price_compare_B)
            price_by_rate_layout.addWidget(radio_rate_input)
            price_by_rate_layout.addWidget(percent_label)
            price_by_rate_layout.addStretch()
            price_by_rate_widget.setLayout(price_by_rate_layout)

            # 将两个页面添加到堆栈窗体
            stacked_widget.addWidget(price_by_value_widget)  # Index 0
            stacked_widget.addWidget(price_by_rate_widget)  # Index 1

            self.price_compare_list.append((price_compare_A, price_compare_B))
            self.price_stacked_widgets.append(stacked_widget)

            # 临时存储旧数据结构引用以兼容旧代码
            self.stock_price_widgets.append((price_by_value_widget, price_by_rate_widget))

            batch_layout.addWidget(stacked_widget)

            # === 语音报警布局 ===
            alarm_layout = QHBoxLayout()
            alarm_label = QLabel("语音报警：")
            alarm_label.setStyleSheet("color: rgb(0, 170, 0); font: 12pt '黑体'")
            alarm_sound_label = QLabel("声音")
            alarm_sound_label.setFont(QFont("阿里巴巴普惠体 M", 10))
            alarm_sound = QComboBox()
            alarm_sound.setFont(QFont("Arial", 10))
            self.alarm_sound_list.append(alarm_sound)
            alarm_spacer = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

            alarm_layout.addWidget(alarm_label)
            alarm_layout.addWidget(alarm_sound_label)
            alarm_layout.addWidget(alarm_sound)
            alarm_layout.addItem(alarm_spacer)

            alarm_widget = QWidget()
            alarm_widget.setLayout(alarm_layout)
            batch_layout.addWidget(alarm_widget)
            self.stock_alarm_widgets.append(alarm_widget)


            # === 仓位布局 ===
            position_layout = QHBoxLayout()
            position_radio_group = []
            position_label = QLabel("仓位：")
            position_label.setStyleSheet("color: rgb(0, 170, 0); font: 12pt '黑体'")

            radio_full = QRadioButton("全仓")
            radio_full.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            self.stock_full_radios.append(radio_full)
            position_radio_group.append(radio_full)
            radio_full.toggled.connect(lambda checked, batch_idx=i: self.update_stock_st_tabs(checked, batch_idx))

            radio_half = QRadioButton("1/2")
            radio_half.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            position_radio_group.append(radio_half)

            radio_third = QRadioButton("1/3")
            radio_third.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            radio_third.setChecked(True)
            position_radio_group.append(radio_third)

            radio_quarter = QRadioButton("1/4")
            radio_quarter.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            position_radio_group.append(radio_quarter)

            radio_custom = QRadioButton("自设量")
            radio_custom.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            position_radio_group.append(radio_custom)

            radio_none = QRadioButton("不交易")
            radio_none.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            position_radio_group.append(radio_none)

            self.stock_position_radios.append(position_radio_group)

            position_layout.addWidget(position_label)
            for radio in position_radio_group:
                position_layout.addWidget(radio)

            position_widget = QWidget()
            position_widget.setLayout(position_layout)
            batch_layout.addWidget(position_widget)

            self.st_tab.addTab(batch_widget, batch_name)

    def create_file_st_batch_tabs(self):
        """创建文件模式的4个批次策略界面 - 使用布局管理"""
        self.file_price_rate_inputs = []
        self.file_alarm_rate_inputs = []
        self.file_price_compare_list = []
        self.file_alarm_compare_list = []

        self.file_position_radios = []

        self.file_alarm_sound_list.clear()
        self.file_full_radios.clear()
        self.file_price_widgets.clear()
        self.file_alarm_widgets.clear()

        self.file_alarm_radio_groups.clear()

        for i in range(4):
            batch_widget = QWidget()
            batch_name = f"第{i + 1}批策略参数"

            batch_layout = QVBoxLayout(batch_widget)
            batch_layout.setContentsMargins(5, 5, 5, 5)
            batch_layout.setSpacing(5)

            # === 价格条件布局 ===
            price_layout = QHBoxLayout()
            price_label = QLabel("价格条件：")
            price_label.setStyleSheet("color: rgb(85, 170, 0); font: 12pt '阿里巴巴普惠体 M'")
            file_price_compare = QComboBox()
            file_price_compare.addItems([">=", "<="])
            self.file_price_compare_list.append(file_price_compare)

            file_radio_price_rate = QRadioButton("涨幅：")
            file_radio_price_rate.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            file_radio_price_rate.setChecked(True)

            price_rate_label = QLabel("%")
            price_rate_label.setFont(QFont("Arial", 16))

            file_price_rate_input = QLineEdit()
            file_price_rate_input.setPlaceholderText("涨幅")
            validator = QDoubleValidator(-20.0, 20.0, 2)
            validator.setNotation(QDoubleValidator.StandardNotation)
            file_price_rate_input.setValidator(validator)
            self.file_price_rate_inputs.append(file_price_rate_input)

            price_spacer = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

            price_layout.addWidget(price_label)
            price_layout.addWidget(file_price_compare)
            price_layout.addWidget(file_radio_price_rate)
            price_layout.addWidget(price_rate_label)
            price_layout.addWidget(file_price_rate_input)
            price_layout.addItem(price_spacer)

            price_widget = QWidget()
            price_widget.setLayout(price_layout)
            batch_layout.addWidget(price_widget)
            self.file_price_widgets.append(price_widget)

            # === 语音报警布局 ===
            alarm_layout = QHBoxLayout()
            alarm_label = QLabel("语音报警：")
            alarm_label.setStyleSheet("color: rgb(0, 170, 0); font: 12pt '黑体'")
            alarm_spacer1 = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
            alarm_sound_label = QLabel("声音")
            alarm_sound_label.setFont(QFont("阿里巴巴普惠体 M", 10))
            file_alarm_sound = QComboBox()
            file_alarm_sound.setFont(QFont("Arial", 10))
            self.file_alarm_sound_list.append(file_alarm_sound)
            alarm_spacer2 = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

            alarm_layout.addWidget(alarm_label)
            alarm_layout.addItem(alarm_spacer1)
            alarm_layout.addWidget(alarm_sound_label)
            alarm_layout.addWidget(file_alarm_sound)
            alarm_layout.addItem(alarm_spacer2)

            alarm_widget = QWidget()
            alarm_widget.setLayout(alarm_layout)
            batch_layout.addWidget(alarm_widget)
            self.file_alarm_widgets.append(alarm_widget)



            # === 仓位布局 ===
            position_layout = QHBoxLayout()
            position_radio_group = []
            position_label = QLabel("仓位：")
            position_label.setStyleSheet("color: rgb(0, 170, 0); font: 12pt '黑体'")

            file_radio_full = QRadioButton("全仓")
            file_radio_full.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            self.file_full_radios.append(file_radio_full)
            position_radio_group.append(file_radio_full)
            file_radio_full.toggled.connect(lambda checked, batch_idx=i: self.update_file_st_tabs(checked, batch_idx))

            file_radio_half = QRadioButton("1/2")
            file_radio_half.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            position_radio_group.append(file_radio_half)

            file_radio_third = QRadioButton("1/3")
            file_radio_third.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            file_radio_third.setChecked(True)
            position_radio_group.append(file_radio_third)

            file_radio_quarter = QRadioButton("1/4")
            file_radio_quarter.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            position_radio_group.append(file_radio_quarter)

            file_radio_custom = QRadioButton("自设量")
            file_radio_custom.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            position_radio_group.append(file_radio_custom)

            file_radio_none = QRadioButton("不交易")
            file_radio_none.setStyleSheet("font: 10pt '阿里巴巴普惠体 M'")
            position_radio_group.append(file_radio_none)

            self.file_position_radios.append(position_radio_group)

            position_layout.addWidget(position_label)
            for radio in position_radio_group:
                position_layout.addWidget(radio)

            position_widget = QWidget()
            position_widget.setLayout(position_layout)
            batch_layout.addWidget(position_widget)

            self.file_st_tab.addTab(batch_widget, batch_name)

    def init_signals(self):
        """初始化信号与槽连接"""
        self.browse_btn.clicked.connect(self.select_blk_file)
        self.add_batch_btn.clicked.connect(self.add_stock_batch)
        self.file_add_batch_btn.clicked.connect(self.add_file_batch)
        self.save_btn.clicked.connect(self.save_stock_st)
        self.file_save_btn.clicked.connect(self.save_file_st)
        self.stock_code_input.textChanged.connect(self.update_rate_validators)

        # 单选按钮互斥连接
        self.st_radio_price.clicked.connect(
            lambda: self.set_radio_group([self.st_radio_rate, self.st_radio_immediate]))
        self.st_radio_rate.clicked.connect(
            lambda: self.set_radio_group([self.st_radio_price,  self.st_radio_immediate]))

        self.st_radio_immediate.clicked.connect(
            lambda: self.set_radio_group([self.st_radio_price, self.st_radio_rate]))

        self.file_radio_price.clicked.connect(lambda: self.set_radio_group(
            [self.file_radio_price, self.file_radio_immediate]))


        self.file_radio_immediate.clicked.connect(lambda: self.set_radio_group(
            [self.file_radio_price,  self.file_radio_immediate]))

        self.st_radio_price.toggled.connect(self.on_stock_st_changed)
        self.st_radio_rate.toggled.connect(self.on_stock_st_changed)

        self.st_radio_immediate.toggled.connect(self.on_stock_st_changed)

        self.file_radio_price.toggled.connect(self.on_file_st_changed)

        self.file_radio_immediate.toggled.connect(self.on_file_st_changed)

        self.tabWidget.currentChanged.connect(self.on_tab_changed)

    def on_stock_st_changed(self):
        """单支股票模式：根据策略分类更新第三步显示"""

        is_immediate = self.st_radio_immediate.isChecked()
        is_price_st = self.st_radio_price.isChecked()
        is_rate_st = self.st_radio_rate.isChecked()

        for i in range(4):
            if not self.st_tab.isTabVisible(i):
                continue

            # 使用 QStackedWidget 进行页面切换
            stacked = self.price_stacked_widgets[i]

            if is_price_st:
                stacked.setCurrentIndex(0)  # 显示按股价
                stacked.setVisible(True)
            elif is_rate_st:
                stacked.setCurrentIndex(1)  # 显示按涨幅
                stacked.setVisible(True)
            else:
                stacked.setVisible(False)  # 隐藏价格区域


            self.stock_alarm_widgets[i].setVisible(True)

    def on_file_st_changed(self):
        """文件模式：根据策略分类更新第三步显示"""

        is_price_st = self.file_radio_price.isChecked()

        for i in range(4):
            if not self.file_st_tab.isTabVisible(i):
                continue
            self.file_price_widgets[i].setVisible(is_price_st)

            self.file_alarm_widgets[i].setVisible(True)

    def on_tab_changed(self, index):
        """切换主Tab时重置另一页面"""
        if index == 0:
            self.reset_file_tab()
        else:
            self.reset_stock_tab()

    def reset_stock_tab(self):
        """重置单支股票设置页面"""
        self.stock_code_input.clear()
        self.st_radio_price.setChecked(True)
        self.current_batch = 1
        self.init_batch_visibility()
        for i in range(4):
            self.reset_single_stock_batch(i)
        self.add_batch_btn.setText("增加第二批策略")
        self.add_batch_btn.setEnabled(True)
        self.add_buy_st_stock_list.clear()

    def reset_file_tab(self):
        """重置文件设置页面"""
        self.blk_name.clear()
        self.folder_input.clear()
        self.file_radio_price.setChecked(True)
        self.file_current_batch = 1
        self.init_batch_visibility()
        for i in range(4):
            self.reset_single_file_batch(i)
        self.file_add_batch_btn.setText("增加第二批策略")
        self.file_add_batch_btn.setEnabled(True)
        self.add_buy_st_file_list.clear()

    def reset_single_stock_batch(self, batch_idx):
        """单支股票模式：清零单个批次的所有参数"""
        if batch_idx < 0 or batch_idx >= 4:
            return

        self.price_rate_inputs[batch_idx].clear()
        self.target_price_inputs[batch_idx].clear()

        compare_tuple = self.price_compare_list[batch_idx]
        if isinstance(compare_tuple, tuple):
            compare_tuple[0].setCurrentIndex(0)
            compare_tuple[1].setCurrentIndex(0)
        else:
            compare_tuple.setCurrentIndex(0)

        self.alarm_sound_list[batch_idx].setCurrentIndex(0)


        for radio in self.stock_position_radios[batch_idx]:
            radio.setChecked(radio.text() == "1/3")
        self.stock_full_radios[batch_idx].setChecked(False)

    def reset_single_file_batch(self, batch_idx):
        """文件模式：清零单个批次的所有参数"""
        if batch_idx < 0 or batch_idx >= 4:
            return
        self.file_price_rate_inputs[batch_idx].clear()
        self.file_price_compare_list[batch_idx].setCurrentIndex(0)
        self.file_alarm_sound_list[batch_idx].setCurrentIndex(0)

        for radio in self.file_position_radios[batch_idx]:
            radio.setChecked(radio.text() == "1/3")
        self.file_full_radios[batch_idx].setChecked(False)

    def update_rate_validators(self):
        """根据股票代码更新涨幅输入框的验证器"""
        stock_code = self.stock_code_input.text().strip()
        max_rate = 10
        if len(stock_code) >= 2:
            prefix = stock_code[:2]
            if prefix in ["30", "68"] or stock_code.startswith("1"):
                max_rate = 20
            elif prefix in ["00", "60"]:
                max_rate = 10
        for input_box in self.price_rate_inputs:
            validator = QDoubleValidator(-max_rate, max_rate, 2, self)
            validator.setNotation(QDoubleValidator.StandardNotation)
            input_box.setValidator(validator)

    def validate_stock_prev_batch(self, prev_batch_idx):
        """校验单支股票模式的上一批策略是否完整"""
        stock_code = self.stock_code_input.text().strip()
        if len(stock_code) != 6 or not stock_code.isdigit():
            QMessageBox.warning(self, "校验失败", "请先填写有效的6位股票代码！")
            return False
        price_rate = self.price_rate_inputs[prev_batch_idx].text().strip()
        target_price = self.target_price_inputs[prev_batch_idx].text().strip()
        if not price_rate and not target_price:
            QMessageBox.warning(self, "校验失败", f"第{prev_batch_idx + 1}批策略：价格涨幅和目标价至少填写一项！")
            return False
        if price_rate:
            try:
                float(price_rate)
            except ValueError:
                QMessageBox.warning(self, "校验失败", f"第{prev_batch_idx + 1}批策略：价格涨幅必须是有效数字！")
                return False
        if target_price:
            try:
                float(target_price)
            except ValueError:
                QMessageBox.warning(self, "校验失败", f"第{prev_batch_idx + 1}批策略：目标价必须是有效数字！")
                return False
        position_checked = any(radio.isChecked() for radio in self.stock_position_radios[prev_batch_idx])
        if not position_checked:
            QMessageBox.warning(self, "校验失败", f"第{prev_batch_idx + 1}批策略：请选择仓位类型！")
            return False
        return True

    def validate_file_prev_batch(self, prev_batch_idx):
        """校验文件模式的上一批策略是否完整"""
        file_path = self.folder_input.text().strip()
        if not file_path:
            QMessageBox.warning(self, "校验失败", "请先选择.blk文件路径！")
            return False
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "校验失败", "所选文件不存在，请重新选择！")
            return False
        if not file_path.endswith(".blk"):
            QMessageBox.warning(self, "校验失败", "请选择.blk格式的通达信板块文件！")
            return False
        if self.file_radio_price.isChecked():
            price_rate = self.file_price_rate_inputs[prev_batch_idx].text().strip()
            if not price_rate:
                QMessageBox.warning(self, "校验失败", f"第{prev_batch_idx + 1}批策略：请填写价格涨幅！")
                return False
            try:
                float(price_rate)
            except ValueError:
                QMessageBox.warning(self, "校验失败", f"第{prev_batch_idx + 1}批策略：价格涨幅必须是有效数字！")
                return False
        position_checked = any(radio.isChecked() for radio in self.file_position_radios[prev_batch_idx])
        if not position_checked:
            QMessageBox.warning(self, "校验失败", f"第{prev_batch_idx + 1}批策略：请选择仓位类型！")
            return False
        return True

    @pyqtSlot()
    def add_stock_batch(self):
        """增加单支股票策略批次"""
        if self.current_batch >= 4:
            QMessageBox.information(self, "提示", "已达最大4批策略，无法继续增加！")
            return
        prev_batch_idx = self.current_batch - 1
        if not self.validate_stock_prev_batch(prev_batch_idx):
            return
        new_batch_idx = self.current_batch
        self.reset_single_stock_batch(new_batch_idx)
        self.st_tab.setTabVisible(new_batch_idx, True)
        self.st_tab.setCurrentIndex(new_batch_idx)
        self.current_batch += 1
        if self.current_batch < 4:
            self.add_batch_btn.setText(f"增加第{self.current_batch + 1}批策略")
        else:
            self.add_batch_btn.setText("已达最大批次")
            self.add_batch_btn.setEnabled(False)
        self.on_stock_st_changed()

    @pyqtSlot()
    def add_file_batch(self):
        """增加文件策略批次"""
        if self.file_current_batch >= 4:
            QMessageBox.information(self, "提示", "已达最大4批策略，无法继续增加！")
            return
        prev_batch_idx = self.file_current_batch - 1
        if not self.validate_file_prev_batch(prev_batch_idx):
            return
        new_batch_idx = self.file_current_batch
        self.reset_single_file_batch(new_batch_idx)
        self.file_st_tab.setTabVisible(new_batch_idx, True)
        self.file_st_tab.setCurrentIndex(new_batch_idx)
        self.file_current_batch += 1
        if self.file_current_batch < 4:
            self.file_add_batch_btn.setText(f"增加第{self.file_current_batch + 1}批策略")
        else:
            self.file_add_batch_btn.setText("已达最大批次")
            self.file_add_batch_btn.setEnabled(False)
        self.on_file_st_changed()

    @pyqtSlot(bool, int)
    def update_stock_st_tabs(self, checked, batch_idx):
        """单支股票模式：根据批次全仓状态，控制后续Tab显隐"""
        if checked:
            for i in range(batch_idx + 1, 4):
                self.st_tab.setTabVisible(i, False)
            self.add_batch_btn.setText("已选全仓，无需后续批次")
            self.add_batch_btn.setEnabled(False)
        else:
            all_unchecked = all(not radio.isChecked() for radio in self.stock_full_radios)
            if all_unchecked:
                for i in range(self.current_batch):
                    self.st_tab.setTabVisible(i, True)
                for i in range(self.current_batch, 4):
                    self.st_tab.setTabVisible(i, False)
                self.add_batch_btn.setEnabled(True)
                if self.current_batch < 4:
                    self.add_batch_btn.setText(f"增加第{self.current_batch + 1}批策略")
                else:
                    self.add_batch_btn.setText("已达最大批次")

    @pyqtSlot(bool, int)
    def update_file_st_tabs(self, checked, batch_idx):
        """文件模式：根据批次全仓状态，控制后续Tab显隐"""
        if checked:
            for i in range(batch_idx + 1, 4):
                self.file_st_tab.setTabVisible(i, False)
            self.file_add_batch_btn.setText("已选全仓，无需后续批次")
            self.file_add_batch_btn.setEnabled(False)
        else:
            all_unchecked = all(not radio.isChecked() for radio in self.file_full_radios)
            if all_unchecked:
                for i in range(self.file_current_batch):
                    self.file_st_tab.setTabVisible(i, True)
                for i in range(self.file_current_batch, 4):
                    self.file_st_tab.setTabVisible(i, False)
                self.file_add_batch_btn.setEnabled(True)
                if self.file_current_batch < 4:
                    self.file_add_batch_btn.setText(f"增加第{self.file_current_batch + 1}批策略")
                else:
                    self.file_add_batch_btn.setText("已达最大批次")

    @pyqtSlot()
    def select_blk_file(self):
        """选择.blk格式文件"""
        try:
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择通达信板块文件",
                "",
                "通达信板块文件 (*.blk);;所有文件 (*)",
                options=options
            )
            if file_path:
                if not file_path.endswith(".blk"):
                    QMessageBox.warning(self, "格式错误", "请选择.blk格式的文件！")
                    return
                self.folder_input.setText(file_path)
        except Exception as e:
            print(f"打开文件对话框出错: {e}")
            QMessageBox.critical(self, "错误", f"打开文件选择失败：{str(e)}")

    @pyqtSlot()
    def save_stock_st(self):
        """保存单支股票策略"""
        if self.tabWidget.currentIndex() != 0:
            return
        stock_code = self.stock_code_input.text().strip()
        if len(stock_code) != 6 or not stock_code.isdigit():
            QMessageBox.warning(self, "输入错误", "请输入有效的6位股票代码！")
            return

        for i in range(4):
            if not self.st_tab.isTabVisible(i):
                continue
            if self.st_radio_rate.isChecked():
                price_rate_text = self.price_rate_inputs[i].text().strip()
                if price_rate_text:
                    try:
                        value = float(price_rate_text)
                        max_rate = 10
                        prefix = stock_code[:2]
                        if prefix in ["30", "68"] or stock_code.startswith("1"):
                            max_rate = 20
                        if value < -max_rate or value > max_rate:
                            QMessageBox.warning(self, "输入错误",
                                                f"第{i + 1}批设置中本股所允许的涨幅必须在±{max_rate}之间！")
                            return
                    except ValueError:
                        QMessageBox.warning(self, "输入错误", f"第{i + 1}批涨幅必须是有效的数字！")
                        return

        self.add_buy_st_stock_list.clear()
        for batch_idx in range(4):
            if not self.st_tab.isTabVisible(batch_idx):
                continue
            if self.st_radio_price.isChecked():
                st_type = "按股价"
            elif self.st_radio_rate.isChecked():
                st_type = "按涨幅"

            else:
                st_type = "立即交易"

            price_condition = ""
            if self.st_radio_price.isChecked():
                price_compare = self.price_compare_list[batch_idx][0].currentText()
                target_price = self.target_price_inputs[batch_idx].text().strip() or ""
                price_condition = f"{price_compare}{target_price}"
            elif self.st_radio_rate.isChecked():
                price_compare = self.price_compare_list[batch_idx][1].currentText()
                price_rate = self.price_rate_inputs[batch_idx].text().strip() or ""
                price_condition = f"{price_compare}{price_rate}%"

            sound_file = self.alarm_sound_list[batch_idx].currentText() or "无报警音"


            position_text = "无"
            for radio in self.stock_position_radios[batch_idx]:
                if radio.isChecked():
                    position_text = radio.text()
                    break

            batch_st = {
                "添加时间": '',
                "状态": '暂停',
                "方向": '买入',
                "股票代码": stock_code,
                "股票名称": '',
                "现价": '',
                "昨日价": '',
                "策略分类": st_type,
                "价格条件": price_condition,
                "仓位": position_text,
                "声音文件": sound_file,

            }
            self.add_buy_st_stock_list.append(batch_st)

        QMessageBox.information(self, "保存成功", "策略已经保存，请按需要进行运行")
        self.st_saved.emit(self.add_buy_st_stock_list, [])
        self.close()

    @pyqtSlot()
    def save_file_st(self):
        """保存文件模式策略"""
        if self.tabWidget.currentIndex() != 1:
            return
        blk_name = self.blk_name.text().strip()
        file_path = self.folder_input.text().strip()

        if not file_path:
            QMessageBox.warning(self, "输入错误", "请选择.blk文件路径！")
            return
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "文件不存在", f"所选文件不存在：{file_path}")
            return
        if not file_path.endswith(".blk"):
            QMessageBox.warning(self, "格式错误", "请选择.blk格式的文件！")
            return

        if self.file_radio_price.isChecked():
            for i in range(4):
                if not self.file_st_tab.isTabVisible(i):
                    continue
                price_text = self.file_price_rate_inputs[i].text().strip()
                if price_text:
                    try:
                        float(price_text)
                    except ValueError:
                        QMessageBox.warning(self, "输入错误", f"第{i + 1}批涨幅必须是有效的数字！")
                        return

        self.add_buy_st_file_list.clear()
        for batch_idx in range(4):
            if not self.file_st_tab.isTabVisible(batch_idx):
                continue
            if self.file_radio_price.isChecked():
                file_st_type = "按涨幅"


            else:
                file_st_type = "立即交易"

            file_price_compare = self.file_price_compare_list[batch_idx].currentText()
            file_price_rate = self.file_price_rate_inputs[batch_idx].text().strip() or ""
            if self.file_radio_price.isChecked():
                file_price_condition = f"{file_price_compare}{file_price_rate}%"
            else:
                file_price_condition = ""

            file_sound_file = self.file_alarm_sound_list[batch_idx].currentText() or "无报警音"


            file_position_text = "无"
            for radio in self.file_position_radios[batch_idx]:
                if radio.isChecked():
                    file_position_text = radio.text()
                    break

            batch_st = {
                "状态": '停止',
                "方向": '买入',
                "板块简介": blk_name,
                "文件地址": file_path,
                "策略分类": file_st_type,
                "价格条件": file_price_condition,
                "仓位": file_position_text,
                "声音文件": file_sound_file,

            }
            self.add_buy_st_file_list.append(batch_st)

        QMessageBox.information(self, "保存成功", "策略已经保存，请按需要进行运行")
        self.st_saved.emit([], self.add_buy_st_file_list)
        self.close()

    def set_radio_group(self, radio_list):
        """设置单选按钮组互斥"""
        for radio in radio_list:
            radio.setChecked(False)
        self.sender().setChecked(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("阿里巴巴普惠体 M", 10)
    app.setFont(font)
    window = AddBuyStWindow()
    window.show()
    sys.exit(app.exec_())
