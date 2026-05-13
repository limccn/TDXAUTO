# -*- coding: utf-8 -*-
import sys
import os
import json

import time
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QHeaderView, QVBoxLayout, QHBoxLayout, QGroupBox, QMessageBox
from PyQt5.QtGui import QIntValidator, QRegExpValidator
from PyQt5.QtCore import QRegExp

import ctypes
from ctypes import wintypes

# 全局缓存已注册的消息 ID，避免重复注册
_STOCK_MSG_ID = None
user32 = ctypes.windll.user32
HWND_BROADCAST = 0xFFFF


def txt_to_csv(input_file="data/全部股票数据.txt", output_file="data/全部股票数据.csv"):
    """
    将股票数据文本文件转换为 CSV 格式。
    只保留 '代码', '公司名称', 'AB股总市值' 三列。
    """
    import os
    import csv
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    if not os.path.exists(input_file):
        print(f"❌ 错误：输入文件 '{input_file}' 不存在！")
        return

    row_count = 0
    with open(input_file, 'r', encoding='gbk') as f_in, \
            open(output_file, 'w', newline='', encoding='utf-8') as f_out:

        writer = csv.writer(f_out)

        # === 步骤1：写入新的表头 ===
        writer.writerow(['代码', '股票名称', 'AB股总市值'])

        # === 步骤2：跳过 txt 文件的第一行（原表头） ===
        next(f_in)

        # === 步骤3：循环写入剩余的数据行 ===
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            tokens = line.split()
            if len(tokens) < 17:
                continue

            code = tokens[0]
            company_name = tokens[1]
            market_value = tokens[16]

            writer.writerow([code, company_name, market_value])
            row_count += 1

    print(f"✅ 成功生成CSV文件：{output_file} (共 {row_count} 行数据)")


def link_tdx(code: str) -> bool:

    global _STOCK_MSG_ID

    # 输入校验
    if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        print(f"❌ 无效股票代码: {code}")
        return False

    code_int = int(code)
    # wParam = code_int
    # 构造 wParam（与 Excel 宏逻辑一致）
    if code.startswith('6') or code.startswith('8') or code.startswith('5') or code.startswith('11'):
        wParam = 7000000 + code_int

    elif code.startswith('9') or code.startswith('43') :
        wParam = 4000000 + code_int
    else:
        wParam = 6000000 + code_int

    # 首次调用时注册 "Stock" 消息
    if _STOCK_MSG_ID is None:
        user32.RegisterWindowMessageA.argtypes = [wintypes.LPCSTR]
        user32.RegisterWindowMessageA.restype = wintypes.UINT
        _STOCK_MSG_ID = user32.RegisterWindowMessageA(b"Stock")
        if _STOCK_MSG_ID == 0:
            print("⚠️ 注册 'Stock' 消息失败")
            return False

    # 发送广播消息
    user32.PostMessageA.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageA.restype = wintypes.BOOL

    success = user32.PostMessageA(HWND_BROADCAST, _STOCK_MSG_ID, wParam, 0)
    if success:
        print(f"✅ 已发送股票代码 {code} 到通达信 (wParam={wParam})")
    else:
        err = ctypes.get_last_error()
        print(f"❌ 发送失败，错误码: {err}")
    return bool(success)

class MainWindow(object):
    def __init__(self):
        super().__init__()
        # 确保 data 目录存在
        os.makedirs("data", exist_ok=True)

        # ================= 新增：数据缓存 =================
        self._cached_fund_data = None  # 缓存所有基金数据
        # self._cached_stock_data = None  # 删除或注释掉这行
        self._cached_stock_df = None
        self._cached_etf_data = None  # 缓存ETF基金数据
        self._setup_txt_path = None
        # ================================================

        # ================= 新增：初始化 fund_table 组件 =================
        self.fund_table = QtWidgets.QTableWidget()
        self.lbl_fund_title = QtWidgets.QLabel("--------")
        self.lbl_fund_title.setStyleSheet("font-weight: bold; font-size: 14px; color: rgb(0, 85, 128);")

        # ================= 新增：基金信息显示区域 =================
        self.lbl_fund_info = QtWidgets.QLabel("--------")
        self.lbl_fund_info.setFixedHeight(40)
        self.lbl_fund_info.setStyleSheet("""
            font-weight: bold;
            font-size: 13px;
            color: #005580;
            background-color: #f0f8ff;
            border: 1px solid #add8e6;
            border-radius: 4px;
            padding: 5px 10px;
        """)
        # ==================================================

        # ================= 修正：在 super 之后初始化 centralwidget =================
        # 必须在这里初始化，否则 setupUi 引用时会报错
        self.centralwidget = QtWidgets.QWidget()
        self.centralwidget.setObjectName("centralwidget")
        # ================= 修正结束 =================

        # ================= 新增：在初始化时就连接列头点击事件 =================
        # 将信号连接移到这里，确保整个程序运行期间只连接一次
        if self.fund_table.horizontalHeader() is not None:
            self.fund_table.horizontalHeader().sectionClicked.connect(self.on_fund_table_header_clicked)
            print("📡 fund_table 信号已连接（在 __init__ 中）")
        # ======================================================================
        self._sorted_column = None  # 记录当前排序的列索引
        self._sort_order = None  # 记录当前排序顺序

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        # ================= 修正：定义 centralwidget =================
        # 确保 centralwidget 存在（通常在 setupUi 开头定义）
        self.centralwidget = QtWidgets.QWidget()
        # 如果上一条报错，请确保 __init__ 中没有冲突，或者在这里重新定义
        if not hasattr(self, 'centralwidget'):
            self.centralwidget = QtWidgets.QWidget()
        self.centralwidget.setObjectName("centralwidget")
        # ================================================

        MainWindow.resize(800, 1000)

        icon = QtGui.QIcon()
        try:
            icon.addPixmap(QtGui.QPixmap("app1.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        except:
            print("未找到app1.ico图标，不影响窗口功能")
        MainWindow.setWindowIcon(icon)

        self.scrollArea = QtWidgets.QScrollArea(MainWindow)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setWidget(self.centralwidget)
        MainWindow.setCentralWidget(self.scrollArea)

        # ================= 关键修复：定义 main_layout =================
        main_layout = QVBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        # ================================================

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
                background-color: rgb(0, 170,255);
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
        self.btn_gn_update = QtWidgets.QPushButton("数据更新", self.tool_bar_widget)
        self.btn_gn_update.setObjectName("btn_gn_update")
        self.btn_gn_update.setStyleSheet(tool_btn_style)
        tool_bar_layout.addWidget(self.btn_gn_update)
        # ================= 新增：连接数据更新按钮事件 =================
        self.btn_gn_update.clicked.connect(self.on_update_data_clicked)

        # ================= 新增：基金代码输入框 =================
        # 基金代码标签
        self.lbl_fund_code = QtWidgets.QLabel("基金代码:", self.tool_bar_widget)
        self.lbl_fund_code.setStyleSheet("font-weight: bold; font-size: 12px; color: #333;")
        tool_bar_layout.addWidget(self.lbl_fund_code)

        # 基金代码输入框（16号字，加粗，蓝色，限1或5开头的6位数字）
        self.edit_fund_code = QtWidgets.QLineEdit(self.tool_bar_widget)
        self.edit_fund_code.setObjectName("edit_fund_code")
        self.edit_fund_code.setPlaceholderText("输入1或5开头的6位代码")
        self.edit_fund_code.setMaxLength(6)
        self.edit_fund_code.setFixedWidth(140)

        # 设置输入框样式：16号字，加粗，蓝色
        self.edit_fund_code.setStyleSheet("""
            QLineEdit {
                font-size: 16px;
                font-weight: bold;
                color: rgb(0, 85, 200);
                border: 2px solid #005580;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid rgb(0, 170, 255);
                background-color: #f0f8ff;
            }
        """)

        # ================= 修改：使用正则表达式验证器，只允许1或5开头的6位数字 =================
        # 正则：^(1|5)\d{5}$ 表示：以1或5开头，后面跟5个数字，共6位
        reg_exp = QRegExp("^(1|5)\\d{5}$")
        validator = QRegExpValidator(reg_exp, self.edit_fund_code)
        self.edit_fund_code.setValidator(validator)
        # ============================================================================

        # 绑定回车键事件
        self.edit_fund_code.returnPressed.connect(self.on_fund_code_query)

        tool_bar_layout.addWidget(self.edit_fund_code)

        # 基金代码查询按钮
        self.btn_fund_query = QtWidgets.QPushButton("查询", self.tool_bar_widget)
        self.btn_fund_query.setObjectName("btn_fund_query")
        self.btn_fund_query.setStyleSheet(tool_btn_style)
        self.btn_fund_query.clicked.connect(self.on_fund_code_query)
        tool_bar_layout.addWidget(self.btn_fund_query)
        # ================= 新增结束 =================

        # 更新状态标签
        tool_bar_layout.addSpacing(20)
        self.gn_update_status = QtWidgets.QLabel("就绪", self.tool_bar_widget)
        self.gn_update_status.setObjectName("gn_update_status")
        self.gn_update_status.setStyleSheet("color: gray; font-weight: normal;")
        self.gn_update_status.setFixedWidth(300)
        tool_bar_layout.addWidget(self.gn_update_status)

        tool_bar_layout.addStretch()
        main_layout.addWidget(self.tool_bar_widget)

        # ================= 新增：基金套利表格区域 =================
        fund_group = QtWidgets.QGroupBox("ETF持仓明细")
        fund_group.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #ccc; margin-top: 10px; }")
        fund_group.setFixedHeight(820)
        fund_layout = QVBoxLayout()

        # ================= 新增：基金信息显示区域 =================
        fund_layout.addWidget(self.lbl_fund_info)
        # ==================================================

        fund_layout.addWidget(self.lbl_fund_title)

        # 设置 fund_table 属性
        # 设置 fund_table 属性
        self.fund_table.setSortingEnabled(False)
        self.fund_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # 修改这里：将 Stretch 改为 Interactive，以支持设置固定列宽
        self.fund_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.fund_table.horizontalHeader().setSectionsClickable(True)
        self.fund_table.horizontalHeader().setSortIndicatorShown(True)

        self.fund_table.setObjectName("fund_table")
        # 设置选中样式
        self.fund_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #005580;
                color: white;
            }
        """)
        fund_layout.addWidget(self.fund_table)
        fund_group.setLayout(fund_layout)

        main_layout.addWidget(fund_group)  # <--- 关键：添加到主布局
        # ================= 新增结束 =================

        main_layout.addStretch()

        # ... (保持原有的菜单和状态栏设置) ...
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 23))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        # ... (setupUi 的原有代码) ...

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # ================= 修改：启动时不自动加载数据，只显示空表格 =================
        QtCore.QTimer.singleShot(100, self.init_empty_table)
        # ======================================================================
        # ================= 新增：为 fund_table 添加单击联动通达信事件 =================
        self.fund_table.cellClicked.connect(self.on_fund_table_cell_clicked)
        # =========================================================================

        # ================= 新增：连接列头点击事件（关键修复） =================
        # # 确保信号只连接一次，避免数据刷新时重复注册导致排序功能异常
        # if hasattr(self, 'fund_table') and self.fund_table.horizontalHeader() is not None:
        #     self.fund_table.horizontalHeader().sectionClicked.connect(self.on_fund_table_header_clicked)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "ETF基金持仓明细"))
        self.banner.setText(_translate("MainWindow", "ETF基金持仓明细！"))

    # ================= 新增：初始化空表格 =================
    def init_empty_table(self):
        """初始化空表格，不读取数据"""
        columns = ['代码', '股票名称', '占净值比例', '持股数', '持仓市值', '季度', 'AB股总市值', 'ETF持仓占比']

        self.fund_table.setColumnCount(len(columns))
        self.fund_table.setHorizontalHeaderLabels(columns)
        self.fund_table.setRowCount(0)

        # 设置列宽
        col_widths = [70, 90, 90, 90, 90, 150, 90, 90]
        for i, width in enumerate(col_widths):
            self.fund_table.setColumnWidth(i, width)

        self.lbl_fund_title.setText("请输入基金代码查询")
        self.lbl_fund_info.setText("等待输入基金代码...")
        self.gn_update_status.setText("就绪 - 请输入1或5开头的6位基金代码")
        print("空表格已初始化")

    # ================= 修复：读取ETF基金数据（最终修复版）=================
    def read_etf_data(self):

        if self._cached_etf_data is not None:
            return self._cached_etf_data

        etf_file = 'data/ETF基金.txt'

        try:
            if not os.path.exists(etf_file):
                print(f"警告：文件不存在 - {etf_file}")
                self._cached_etf_data = {}
                return self._cached_etf_data

            # 1. 使用 iso-8859-1 读取（避免解码错误）
            df_etf = None
            try:
                df_etf = pd.read_csv(etf_file, sep='\t', encoding='iso-8859-1')
                print(f"✅ 使用 iso-8859-1 读取文件成功")
            except Exception as e:
                print(f"❌ 读取失败: {e}")
                self._cached_etf_data = {}
                return self._cached_etf_data

            # 2. 定义编码转换函数
            def fix_encoding(x):
                """将 iso-8859-1 读取的乱码转换回 gbk"""
                # 关键：如果不是字符串或者为空，直接返回原值
                if not isinstance(x, str):
                    return x
                if not x or x.strip() == '':
                    return x
                try:
                    # 核心转换逻辑
                    return x.encode('iso-8859-1').decode('gbk')
                except Exception as e:
                    # 转换失败返回原值
                    return x

            # 3. 转换列名
            print(f"原始列名（前3个）: {list(df_etf.columns)[:3]}")
            df_etf.columns = [fix_encoding(col) for col in df_etf.columns]
            print(f"转换后列名（前3个）: {list(df_etf.columns)[:3]}")

            # 4. ================= 关键修复：全量转换所有列 =================
            print("正在全量转换数据列...")
            for col in df_etf.columns:
                # 不再判断 dtype，直接 apply（fix_encoding 内部会判断）
                df_etf[col] = df_etf[col].apply(fix_encoding)
            print(f"✅ 编码转换完成")
            # ================================================================

            # 5. 创建代码到名称和市值的映射
            etf_map = {}

            # 打印第一行数据，验证转换结果
            if len(df_etf) > 0:
                sample_row = df_etf.iloc[0]
                print(f"第一行数据样本:")
                print(f"   代码: {sample_row.get('代码', 'N/A')}")
                print(f"   名称: {sample_row.get('名称', 'N/A')}")
                print(f"   市值: {sample_row.get('AB股总市值', 'N/A')}")

            for _, row in df_etf.iterrows():
                code = str(row.get('代码', '')).strip()
                name = str(row.get('名称', '')).strip()
                market_cap = row.get('AB股总市值', '')

                if code and code != 'nan':
                    etf_map[code] = {
                        'name': name,
                        'market': str(market_cap).strip() if pd.notna(market_cap) else "未知"
                    }

            self._cached_etf_data = etf_map

            # 验证结果
            first_code = list(etf_map.keys())[0] if etf_map else None
            if first_code:
                print(f"✅ 成功加载ETF数据，共 {len(etf_map)} 只基金")
                # print(
                #     f"   示例: 代码={first_code}, 名称={etf_map[first_code]['name']}, 市值={etf_map[first_code]['market']}")
            else:
                print("⚠️ 警告：未能加载到有效的ETF数据")

            return etf_map

        except Exception as e:
            print(f"读取ETF基金数据时出错: {e}")
            import traceback
            traceback.print_exc()
            self._cached_etf_data = {}
            return self._cached_etf_data

    # ==================================================

    # ================= 新增：补充缺失的槽函数 =================

    def on_fund_table_header_clicked(self, logical_index):
        """处理表格表头点击事件，实现排序"""
        # 如果点击的是当前排序列，则切换排序顺序
        if self._sorted_column == logical_index:
            if self._sort_order == QtCore.Qt.AscendingOrder:
                self._sort_order = QtCore.Qt.DescendingOrder
            else:
                self._sort_order = QtCore.Qt.AscendingOrder
        else:
            self._sorted_column = logical_index
            self._sort_order = QtCore.Qt.AscendingOrder

        # 执行排序 (注意：这里需要表格有数据才有效果)
        self.fund_table.sortItems(logical_index, self._sort_order)

        # 更新表头显示的排序箭头
        header = self.fund_table.horizontalHeader()
        header.setSortIndicator(logical_index, self._sort_order)

    def on_update_data_clicked(self):
        """处理数据更新按钮点击事件 - 清空缓存并显示空表格"""
        print("数据更新按钮被点击")
        self.gn_update_status.setText("正在清除缓存...")

        # 清空缓存
        self._cached_fund_data = None
        self._cached_stock_data = None
        self._cached_etf_data = None
        self._setup_txt_path = None

        # 强制刷新界面
        QtWidgets.QApplication.processEvents()

        # 重新显示空表格
        self.init_empty_table()
        self.edit_fund_code.clear()  # 清空输入框

        self.gn_update_status.setText("缓存已清除，请重新输入基金代码")

    # ================= 新增：基金代码查询功能 =================
    def on_fund_code_query(self):
        """处理基金代码查询事件"""
        fund_code_input = self.edit_fund_code.text().strip()

        # 检查输入是否为空
        if not fund_code_input:
            QMessageBox.warning(self.centralwidget, "输入提示", "请输入基金代码")
            return

        # 检查输入长度
        if len(fund_code_input) != 6:
            QMessageBox.warning(self.centralwidget, "输入错误", "基金代码必须是6位数字")
            return

        # 检查是否以1或5开头
        if not fund_code_input.startswith('1') and not fund_code_input.startswith('5'):
            QMessageBox.warning(self.centralwidget, "输入错误", "基金代码必须以1或5开头")
            return

        # 统一格式化（补零或去掉前导零）
        fund_code = fund_code_input.zfill(6)

        print(f"查询基金代码: {fund_code}")
        self.gn_update_status.setText(f"正在查询基金 {fund_code}...")

        # 强制刷新界面
        QtWidgets.QApplication.processEvents()

        # 调用生成表格函数，传入基金代码进行筛选
        self.generate_fund_table(fund_code=fund_code)
        self.edit_fund_code.clear()

    # ================= 新增结束 =================



    def read_fundstk_data(self, fund_code=None):
        """
        读取基金持仓数据函数（优化版：只读取指定基金的数据）

        Args:
            fund_code: 基金代码（可选），如果指定则只读取该基金的数据

        Returns:
            如果 fund_code 为 None，返回所有基金数据列表
            如果 fund_code 指定，返回该基金的持仓数据字典，如果不存在返回 None
        """

        # ==================== 第一步：读 ====================
        # 缓存 TDX_PATH
        if self._setup_txt_path is None:
            setup_file = 'setup.json'
            tdx_path = None
            try:
                with open(setup_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    tdx_path = config.get('TDX_PATH')
                if not tdx_path:
                    print(f"错误：在{setup_file}中未找到TDX_PATH配置")
                    return None
                self._setup_txt_path = tdx_path
                print(f"读取到TDX_PATH: {tdx_path}")
            except FileNotFoundError:
                print(f"错误：找不到文件 {setup_file}")
                return None
            except Exception as e:
                print(f"读取setup.json时出错: {e}")
                return None

        tdx_path = self._setup_txt_path

        # ==================== 第二步：读取fundstk.dat文件 ====================
        fundstk_file = os.path.join(tdx_path, 'T0002', 'hq_cache', 'fundstk.dat')

        try:
            if not os.path.exists(fundstk_file):
                print(f"错误：文件不存在 - {fundstk_file}")
                return None

            with open(fundstk_file, 'r', encoding='gbk') as f:
                content = f.read()

            print(f"成功读取文件: {fundstk_file}")

        except Exception as e:
            print(f"读取fundstk.dat时出错: {e}")
            return None

        # ==================== 第三步：逐行解析数据 ====================

        # 如果指定了基金代码，只读取该基金的数据
        if fund_code is not None:
            fund_code = str(fund_code).strip()
            target_fund_data = None

            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # 按|分隔各字段
                parts = line.split('|')

                if len(parts) < 2:
                    continue

                # 检查是否是目标基金
                current_fund_code = parts[0].strip()
                if current_fund_code == fund_code:
                    # 找到目标基金，解析持仓数据
                    quarter = parts[1] if len(parts) > 1 else ""
                    holdings = []

                    # 解析持仓数据（从第3个字段开始）
                    for i in range(2, len(parts)):
                        holding_str = parts[i].strip()
                        if not holding_str:
                            continue

                        # 按,分隔持仓字段
                        holding_fields = holding_str.split(',')

                        if len(holding_fields) >= 6:
                            try:
                                market_code = int(holding_fields[0])  # 1=上海, 0=深圳
                                stock_code = holding_fields[1]  # 股票代码
                                volume = int(holding_fields[3])  # 持仓量
                                market_value = float(holding_fields[4])  # 持仓市值
                                nav_ratio = float(holding_fields[6])  # 占净值比

                                holding = {
                                    'market': '上海' if market_code == 1 else '深圳',
                                    'market_code': market_code,
                                    'stock_code': stock_code,
                                    'volume': volume,
                                    'market_value': market_value,
                                    'nav_ratio': nav_ratio
                                }
                                holdings.append(holding)

                            except (ValueError, IndexError) as e:
                                print(f"警告：行{line_num}持仓{i - 1}解析失败: {e}")
                                continue

                    # 组装基金数据
                    target_fund_data = {
                        'fund_code': fund_code,
                        'quarter': quarter,
                        'holdings': holdings
                    }

                    print(f"找到基金 {fund_code}，共 {len(holdings)} 只持仓")
                    break

            if target_fund_data is None:
                print(f"未找到基金代码: {fund_code}")

            return target_fund_data

        else:
            # 如果没有指定基金代码，读取所有基金数据（并缓存）
            fund_holdings = []
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # 按|分隔各字段
                parts = line.split('|')

                if len(parts) < 3:
                    continue  # 跳过格式不正确的行

                # 提取基本信息
                f_code = parts[0]  # 基金代码
                quarter = parts[1]  # 季度日期

                # 解析持仓数据（从第3个字段开始）
                holdings = []

                for i in range(2, len(parts)):
                    holding_str = parts[i].strip()
                    if not holding_str:
                        continue

                    # 按,分隔持仓字段
                    holding_fields = holding_str.split(',')

                    if len(holding_fields) >= 6:
                        try:
                            market_code = int(holding_fields[0])  # 1=上海, 0=深圳
                            stock_code = holding_fields[1]  # 股票代码
                            volume = int(holding_fields[3])  # 持仓量
                            market_value = float(holding_fields[4])  # 持仓市值
                            nav_ratio = float(holding_fields[6])  # 占净值比

                            holding = {
                                'market': '上海' if market_code == 1 else '深圳',
                                'market_code': market_code,
                                'stock_code': stock_code,
                                'volume': volume,
                                'market_value': market_value,
                                'nav_ratio': nav_ratio
                            }
                            holdings.append(holding)

                        except (ValueError, IndexError) as e:
                            print(f"警告：行{line_num}持仓{i - 1}解析失败: {e}")
                            continue

                # 组装完整的基金数据
                fund_data = {
                    'fund_code': f_code,
                    'quarter': quarter,
                    'holdings': holdings
                }

                fund_holdings.append(fund_data)

            # 缓存数据
            self._cached_fund_data = fund_holdings

            return fund_holdings

    def generate_fund_table(self, fund_code=None):
        try:
            csv_path = 'data\\全部股票数据.csv'

            # 检查文件是否存在
            if not os.path.exists(csv_path):
                # 尝试当前目录
                if not os.path.exists("全部股票数据.csv"):
                    QtWidgets.QMessageBox.critical(None, "文件错误",
                                                   f"找不到股票数据文件：{csv_path}\n请先运行 txt_to_csv() 生成该文件。")
                    return
                # csv_path = "全部股票数据.csv"

            # ==================== 优化：使用缓存的股票数据 ====================
            if self._cached_stock_df is None:
                print(f"正在加载股票数据（直接读取CSV）：{csv_path}")
                # 直接读取 CSV，保留所有需要的列
                df_total = pd.read_csv(
                    csv_path,
                    usecols=["代码", "股票名称", "AB股总市值"],
                    dtype={"代码": str, "股票名称": str}
                )
                print(f"✅ 成功从CSV加载 {len(df_total)} 条股票记录")
                # 缓存整个 DataFrame
                self._cached_stock_df = df_total
            else:
                print("使用缓存的股票数据")
                # 直接使用缓存的 DataFrame
                df_total = self._cached_stock_df
                print(f"从缓存读取，共 {len(df_total)} 条记录")
            # ===============================================================

            # ==================== 新增：读取ETF基金数据 ====================
            etf_data = self.read_etf_data()
            # ===============================================================

            print(f"正在获取基金 {fund_code} 的持仓数据...")

            # ==================== 优化：只读取指定基金的数据 ====================
            fund_data = self.read_fundstk_data(fund_code=fund_code)

            if fund_data is None:
                print(f"基金代码 '{fund_code}' 不存在")
                QtWidgets.QMessageBox.warning(
                    self.centralwidget,
                    "查询失败",
                    f"基金代码 '{fund_code}' 不存在！\n\n请检查基金代码是否正确。"
                )
                self.gn_update_status.setText(f"基金代码 {fund_code} 不存在")
                self.lbl_fund_info.setText(f"基金代码 {fund_code} 不存在")
                return

            print(f"成功读取基金 {fund_data['fund_code']} 的数据")
            # ======================================================================

            # ==================== 新增：显示基金信息 ====================
            fund_code_str = fund_data['fund_code']
            etf_info = etf_data.get(fund_code_str, {})
            fund_name = etf_info.get('name', '未知')
            fund_market = etf_info.get('market', '未知')

            self.lbl_fund_info.setText(
                f"基金代码: {fund_code_str}  |  "
                f"基金名称: {fund_name}  |  "
                f"基金市值: {fund_market}"
            )
            # =========================================================

            # 将数据转换为 DataFrame
            holdings_list = []

            f_code = fund_data['fund_code']
            quarter = fund_data['quarter']

            for holding in fund_data['holdings']:
                holdings_list.append({
                    '基金代码': f_code,
                    '季度': quarter,
                    '市场': holding['market'],
                    '股票代码': holding['stock_code'],
                    '持股数': holding['volume'],
                    '持仓市值': holding['market_value'],
                    '占净值比例': holding['nav_ratio']
                })

            # 创建 DataFrame
            hold_df = pd.DataFrame(holdings_list)
            print(f"共读取到 {len(hold_df)} 条持仓记录")

            # 2. 确定列名（根据文件实际列名，优先匹配代码和名称列）
            code_col_total = None
            for col in ['代码', '股票代码', 'symbol']:
                if col in df_total.columns:
                    code_col_total = col
                    print(f"   识别到代码列：{code_col_total}")
                    break

            name_col_total = None
            for col in ['名称', '股票名称', 'name']:
                if col in df_total.columns:
                    name_col_total = col
                    print(f"   识别到名称列：{name_col_total}")
                    break

            market_col_total = None
            # 增加了 "总市值(亿元)" 以兼容旧数据，首选 "AB股总市值"
            for col in ['AB股总市值']:
                if col in df_total.columns:
                    market_col_total = col
                    print(f"   识别到市值列：{market_col_total}")
                    break

            if not code_col_total or not market_col_total:
                print(f"错误：无法识别数据文件列名。")
                print(f"   代码列：{code_col_total}")
                print(f"   名称列：{name_col_total}")
                print(f"   市值列：{market_col_total}")
                print(f"   当前文件列名：{list(df_total.columns)}")
                return

            # 3. 数据清洗与匹配
            market_map = dict(zip(
                df_total[code_col_total].astype(str).str.strip(),
                df_total[market_col_total]
            ))

            # ==================== 新增：股票名称映射 ====================
            name_map = {}
            if name_col_total:
                name_map = dict(zip(
                    df_total[code_col_total].astype(str).str.strip(),
                    df_total[name_col_total]
                ))
            # ==========================================================

            display_data = []
            hold_df['股票代码'] = hold_df['股票代码'].astype(str).str.strip()

            for _, row in hold_df.iterrows():
                stock_code = row['股票代码']
                raw_market = market_map.get(stock_code, 0)
                stock_name = name_map.get(stock_code, "")  # 获取股票名称

                # --- 清洗市值数据 ---
                # 如果是字符串，且包含"亿"，转换为数值（单位：万元）
                if isinstance(raw_market, str):
                    raw_market = raw_market.replace("亿", "").replace(",", "").strip()
                    if raw_market:  # 防止空字符串
                        market_value = float(raw_market) * 10000  # 将亿转换为万元
                    else:
                        market_value = 0
                elif pd.isna(raw_market):
                    market_value = 0
                else:
                    market_value = float(raw_market)  # 假设已经是数值

                try:
                    # 计算ETF持仓占比 = 100 * 持仓市值 / (市值(万元) * 10000)
                    ratio = 100 * row['持仓市值'] / (market_value * 10000)
                except ZeroDivisionError:
                    ratio = 0

                display_data.append([
                    stock_code,
                    stock_name,  # ==================== 新增：股票名称 ====================
                    row['占净值比例'],
                    f"{round(row['持股数'] / 10000, 2)}万股",
                    row['持仓市值'],
                    row['季度'],
                    f"{market_value / 10000:.2f}亿",  # 显示时转为亿更易读
                    f"{ratio:.4f}%"  # ETF持仓占比
                ])

            # 4. 更新界面
            self.fill_ui_table(display_data, fund_code)
            print("表格更新完成")

            # 更新状态栏
            self.gn_update_status.setText(f"基金 {fund_code} 持仓明细已显示 (共 {len(display_data)} 只股票)")

        except Exception as e:
            print(f"生成基金表格时出错: {e}")
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(None, "数据加载失败", f"获取数据时发生错误：\n{str(e)}")



    def fill_ui_table(self, data_list, fund_code=None):
        """辅助函数：将处理好的数据显示在界面上

        Args:
            data_list: 数据列表
            fund_code: 基金代码（可选），用于更新标题
        """
        # 定义表头
        columns = ['代码', '股票名称', '占净值比例', '持股数', '持仓市值', '季度', 'AB股总市值']

        # 冻结表格更新（防止刷新闪烁）
        self.fund_table.setSortingEnabled(False)
        self.fund_table.setRowCount(0)  # 清空现有行

        # 设置列数和表头
        self.fund_table.setColumnCount(len(columns))
        self.fund_table.setHorizontalHeaderLabels(columns)

        # 遍历数据并插入行
        for row_data in data_list:
            row_idx = self.fund_table.rowCount()
            self.fund_table.insertRow(row_idx)

            for col_idx, item_text in enumerate(row_data):
                item = QtWidgets.QTableWidgetItem(str(item_text))

                # 设置文本对齐方式：数字右对齐
                if col_idx > 1:  # 前两列（代码、名称）左对齐，后面右对齐
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                else:
                    item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

                # ================= 新增：设置颜色 =================
                # 第2列：占净值比例
                if col_idx == 2:
                    try:
                        nav_ratio = float(item_text)
                        if nav_ratio > 10:
                            item.setForeground(QtGui.QColor(255, 0, 0))  # 红色
                        elif nav_ratio >= 5:
                            item.setForeground(QtGui.QColor(0, 0, 255))  # 蓝色
                        else:
                            item.setForeground(QtGui.QColor(0, 128, 0))  # 绿色
                    except:
                        pass  # 转换失败，使用默认颜色

                # 第6列：AB股总市值
                if col_idx == 6:
                    # 解析市值（格式可能是 "39.40亿"）
                    try:
                        # 去掉"亿"和空格
                        market_str = str(item_text).replace("亿", "").replace(" ", "").strip()
                        market_value = float(market_str)

                        if market_value > 1000:
                            item.setForeground(QtGui.QColor(28,28,28))  # 红色
                        elif market_value >= 500:
                            item.setForeground(QtGui.QColor(30,144,255))  # 蓝色
                        elif market_value >= 300:
                            item.setForeground(QtGui.QColor(255, 0, 0))  # 蓝色
                        elif market_value >= 100:
                            item.setForeground(QtGui.QColor(255, 0, 255))  # 蓝色
                        else:
                            item.setForeground(QtGui.QColor(0, 128, 0))  # 绿色
                    except:
                        pass  # 转换失败，使用默认颜色
                # ==============================================

                self.fund_table.setItem(row_idx, col_idx, item)

        # 更新标题
        if fund_code is not None:
            self.lbl_fund_title.setText(f"{fund_code} 持仓明细 (共 {len(data_list)} 只股票)")
        else:
            self.lbl_fund_title.setText(f"持仓明细 (共 {len(data_list)} 只股票)")

        # 设置列宽
        col_widths = [70, 110, 90, 90, 90, 90, 90]
        for i, width in enumerate(col_widths):
            self.fund_table.setColumnWidth(i, width)

    # ================= 新增：fund_table 单击联动通达信 =================
    def on_fund_table_cell_clicked(self, row, col):
        """
        处理 fund_table 单元格单击事件
        如果点击的是"代码"列，则联动到通达信软件
        """
        try:
            # 获取列名
            header_item = self.fund_table.horizontalHeaderItem(col)
            if not header_item:
                return

            header_text = header_item.text()

            # 只有点击代码列才触发联动
            if header_text == "代码":
                # 获取单元格内容
                item = self.fund_table.item(row, col)
                if item:
                    code = item.text().strip()
                    # 补足6位
                    code = code.zfill(6)

                    # 调用通达信联动函数
                    if link_tdx(code):
                        self.statusbar.showMessage(f"✅ 已联动通达信: {code}", 3000)
                    else:
                        QtWidgets.QMessageBox.warning(
                            None, "联动失败",
                            f"无法联动通达信，请确保通达信软件已打开。\n股票代码: {code}"
                        )
        except Exception as e:
            print(f"❌ fund_table 单击联动出错: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    txt_to_csv()

    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    ui = MainWindow()
    ui.setupUi(window)
    window.show()
    sys.exit(app.exec_())




