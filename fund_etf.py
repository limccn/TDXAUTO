# -*- coding: utf-8 -*-
import json
import os
import time
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QHeaderView, QVBoxLayout, QHBoxLayout, QGroupBox
import data_update





# ================= 新增结束 =================


class MainWindow(object):
    def __init__(self):
        super().__init__()
        # 确保 data 目录存在
        os.makedirs("data", exist_ok=True)

        # ================= 新增：初始化 fund_table 组件 =================
        self.fund_table = QtWidgets.QTableWidget()
        self.lbl_fund_title = QtWidgets.QLabel("--------")
        self.lbl_fund_title.setStyleSheet("font-weight: bold; font-size: 14px; color: rgb(0, 85, 128);")

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
            icon.addPixmap(QtGui.QPixmap("app4.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        except:
            print("未找到app4.ico图标，不影响窗口功能")
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
        fund_group = QtWidgets.QGroupBox("基金套利分析")
        fund_group.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #ccc; margin-top: 10px; }")
        fund_group.setFixedHeight(820)
        fund_layout = QVBoxLayout()
        fund_layout.addWidget(self.lbl_fund_title)

        # 设置 fund_table 属性
        self.fund_table.setSortingEnabled(False)  # 允许排序
        self.fund_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)  # 整行选择
        self.fund_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
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

        # ================= 新增：连接列头点击事件（关键修复） =================
        # # 确保信号只连接一次，避免数据刷新时重复注册导致排序功能异常
        # if hasattr(self, 'fund_table') and self.fund_table.horizontalHeader() is not None:
        #     self.fund_table.horizontalHeader().sectionClicked.connect(self.on_fund_table_header_clicked)


        # �保定时器在窗口关闭时停止
        def closeEvent_override(event):
            if hasattr(self, 'auto_refresh_timer'):
                self.auto_refresh_timer.stop()
                print("✅ 自动刷新定时器已停止")
            event.accept()

        MainWindow.closeEvent = closeEvent_override
        # ================= 新增结束 =================

        # ================= 新增：自动生成表格 =================
        # 使用定时器在界面初始化后自动填充表格
        QtCore.QTimer.singleShot(500, self.generate_fund_table)
        # ================= 新增结束 =================

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "基金套利"))
        self.banner.setText(_translate("MainWindow", "ETF场内基金套利！"))

    def display_fund_data(self, df_data):
        """
        将 DataFrame 数据显示到 fund_table 中，并处理颜色和字体
        【修改】数值列格式修改为 3 位小数
        """
        if df_data is None or df_data.empty:
            return

        # 清空或设置行列
        self.fund_table.setRowCount(len(df_data))
        self.fund_table.setColumnCount(len(df_data.columns))
        self.fund_table.setHorizontalHeaderLabels(df_data.columns.tolist())

        # 定义需要按数值排序的列
        sortable_columns = ['场内最新价', '单位净值', '成交额', '溢价', '基金市值']

        # ================= 为可排序列设置列头属性 =================
        for col_idx, col_name in enumerate(df_data.columns):
            header_item = self.fund_table.horizontalHeaderItem(col_idx)
            if header_item and col_name in sortable_columns:
                header_item.setToolTip(f"点击按 '{col_name}' 排序")
        # ===================================================================

        # ================= 填充表格并设置颜色 =================
        for row_idx in range(len(df_data)):
            for col_idx, col_name in enumerate(df_data.columns):
                val = df_data.iloc[row_idx][col_name]
                item = None

                # === 1. 处理数值列（修改为保留 3 位小数） ===
                if col_name in sortable_columns:
                    if pd.isna(val):
                        # 空值处理
                        display_val = ""  # 界面显示为空
                        sort_val = 0.0  # 排序时视为 0
                        num_val = 0.0  # 用于颜色判断
                    elif isinstance(val, (int, float)):
                        # 正常数值：修改这里，将 .2f 改为 .3f
                        display_val = f"{val:.3f}"
                        sort_val = float(val)
                        num_val = float(val)
                    else:
                        # 容错处理（如果数据不是数字）
                        display_val = str(val)
                        sort_val = 0.0
                        num_val = 0.0

                    # 创建单元格项
                    item = QtWidgets.QTableWidgetItem(display_val)

                    # 设置 EditRole 为数值，确保排序正确
                    item.setData(QtCore.Qt.EditRole, sort_val)

                    # === 2. 处理溢价列的颜色和加粗 ===
                    if col_name == '溢价':
                        if num_val > 5:
                            # 橙色加粗
                            item.setForeground(QtGui.QColor(218, 49, 220))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        elif 0 <= num_val <= 5:
                            # 红色加粗
                            item.setForeground(QtGui.QColor(255, 0, 0))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        elif num_val < 0:
                            # 绿色加粗
                            item.setForeground(QtGui.QColor(108, 196, 70))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)

                    # === 3列的颜色和加粗 ===
                    if col_name == '成交额':
                        if num_val >= 10000:
                            # 橙色加粗
                            item.setForeground(QtGui.QColor(218, 49, 220))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        elif 5000 <= num_val < 10000:
                            # 红色加粗
                            item.setForeground(QtGui.QColor(255, 0, 70))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        elif 1000 <= num_val < 5000:
                            # 红色加粗
                            item.setForeground(QtGui.QColor(0,191,255))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)

                # === 3. 处理非数值列（代码、名称等） ===
                else:
                    if pd.isna(val):
                        display_val = ""
                    else:
                        display_val = str(val)
                    item = QtWidgets.QTableWidgetItem(display_val)

                self.fund_table.setItem(row_idx, col_idx, item)

        # 自适应列宽
        self.fund_table.resizeColumnsToContents()
        # self.fund_table.horizontalHeader().setSortIndicator(-1, QtCore.Qt.AscendingOrder)

    def generate_fund_table(self):
        """生成 fund_table：合并场内价格与持仓数据（净值、市值）"""
        try:
            etf_path = "data/fund_etf.csv"

            # 1. 读取场内ETF数据
            if not os.path.exists(etf_path):
                print(f"❌ 未找到文件: {etf_path}")
                self.show_error_in_table(f"未找到文件: {etf_path}\n请先点击'数据更新'")
                return

            df_etf = pd.read_csv(etf_path, encoding='utf-8-sig')

            # ================= 核心修改：读取 specjjdata.txt 获取净值和市值 =================
            nav_map = {}  # 代码 -> 单位净值
            mv_map = {}  # 代码 -> 基金市值

            tdx_path = None
            setup_file = "setup.json"  # 读取通达信路径
            if os.path.exists(setup_file):
                try:
                    with open(setup_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        tdx_path = config.get('TDX_PATH')
                except Exception as e:
                    print(f"读取 setup.json 失败: {e}")
            if tdx_path:
                spec_file = os.path.join(tdx_path, 'T0002', 'hq_cache', 'specjjdata.txt')
                if os.path.exists(spec_file):
                    print(f"📂 正在读取持仓文件: {spec_file}")
                    # 使用 GBK 编码读取通达信文件
                    with open(spec_file, 'r', encoding='gbk', errors='ignore') as f:
                        for line in f:
                            parts = line.strip().split(',')
                            # 格式: 159141,0,,20260212,102906.07,1.1230
                            # 索引: 0(代码), 4(份额), 5(净值)
                            if len(parts) >= 6:
                                code = parts[0].strip()
                                try:
                                    share = float(parts[4])
                                    nav = float(parts[5])
                                    nav_map[code] = nav
                                    mv_map[code] = round(share * nav, 2)
                                except ValueError:
                                    continue
                    print(f"✅ 成功解析 {len(nav_map)} 条持仓数据")
                else:
                    print(f"⚠️ 未找到持仓文件: {spec_file}")
            else:
                print("⚠️ 未配置 TDX_PATH，无法获取净值和市值数据")
                self.show_error_in_table("未配置通达信路径(setup.json)，无法获取净值数据")
                return
            # =============================================================================

            # 2. 填充基础数据
            fund_table = pd.DataFrame()

            # 处理代码格式（去除 sh/sz 前缀，补齐6位）
            fund_table['代码'] = df_etf['代码'].astype(str).str.replace(r'^(sh|sz)', '', regex=True).str.zfill(6)
            fund_table['名称'] = df_etf['名称']
            fund_table['场内最新价'] = df_etf['最新价']

            # 成交额处理（假设原数据为元，转为万元）
            fund_table['成交额'] = pd.to_numeric(df_etf['成交额'], errors='coerce').fillna(0) / 10000
            fund_table['成交额'] = fund_table['成交额'].round(2)

            # 3. 映射净值和市值（核心修改）
            fund_table['单位净值'] = fund_table['代码'].map(nav_map).round(3)
            fund_table['基金市值'] = (fund_table['代码'].map(mv_map) / 10000).round(2)

            # 4. 数据清洗与计算
            # 过滤掉没有净值的行（即未持仓或未匹配的基金）
            fund_table.dropna(subset=['单位净值'], inplace=True)

            # 计算溢价
            fund_table['溢价'] = 100 * (fund_table['场内最新价'] - fund_table['单位净值']) / fund_table['单位净值']
            fund_table['溢价'] = fund_table['溢价'].round(2)

            # 5. 调整列顺序（根据需求：删除基金代码，基金名称改为基金市值）
            # 现在列名为：名称（场内简称），基金市值（计算得出），单位净值（从文件读取）
            final_cols = ['代码', '名称', '场内最新价', '成交额', '溢价', '基金市值', '单位净值']
            fund_table = fund_table[final_cols].copy()

            # 保存显示数据
            self.df_fund_display = fund_table.copy()

            # 6. 显示数据
            self.display_fund_data(fund_table)
            self.fund_table.horizontalHeader().setSortIndicator(-1, QtCore.Qt.AscendingOrder)

            print(f"✅ fund_table 已更新，共 {len(fund_table)} 条记录")

        except Exception as e:
            import traceback
            print(f"❌ 生成失败: {e}")
            traceback.print_exc()
            self.show_error_in_table(f"生成失败：{str(e)}")

    def show_error_in_table(self, msg):
        """辅助方法：在表格中显示错误信息"""
        self.fund_table.setRowCount(1)
        self.fund_table.setColumnCount(1)
        self.fund_table.setHorizontalHeaderLabels(['错误'])
        self.fund_table.setItem(0, 0, QtWidgets.QTableWidgetItem(msg))

    # ================= 修改：列头点击事件处理（增加循环逻辑） =================
    def on_fund_table_header_clicked(self, logical_index):
        column_name = self.fund_table.horizontalHeaderItem(logical_index).text()
        sortable_columns = ['场内最新价', '单位净值', '成交额', '溢价', '基金市值']
        if column_name not in sortable_columns:
            return

        if self._sorted_column != logical_index:
            # 新列：升序
            self.fund_table.sortItems(logical_index, QtCore.Qt.AscendingOrder)
            self._sorted_column = logical_index
            self._sort_order = QtCore.Qt.AscendingOrder
            print(f"✅ 已按 '{column_name}' 升序排序")
        elif self._sort_order == QtCore.Qt.AscendingOrder:
            # 升序 → 降序
            self.fund_table.sortItems(logical_index, QtCore.Qt.DescendingOrder)
            self._sort_order = QtCore.Qt.DescendingOrder
            print(f"✅ 已按 '{column_name}' 降序排序")
        else:
            # 降序 → 升序 (修改这里：不再恢复原始顺序，而是循环回升序)
            self.fund_table.sortItems(logical_index, QtCore.Qt.AscendingOrder)
            self._sort_order = QtCore.Qt.AscendingOrder
            print(f"✅ 已按 '{column_name}' 升序排序")
    def on_update_data_clicked(self):
        """
        数据更新按钮点击事件
        1. 删除旧文件
        2. 下载新数据（fund_daily 和 fund_etf_and_lof）
        3. 更新状态显示
        """
        try:
            # ================= 第一步：删除旧数据文件 =================
            day_path = 'data/fund_day.csv'
            etf_path = 'data/fund_etf.csv'

            files_to_delete = []
            if os.path.exists(day_path):
                files_to_delete.append(day_path)
            if os.path.exists(etf_path):
                files_to_delete.append(etf_path)

            if files_to_delete:
                # 显示正在删除的状态
                self.gn_update_status.setText("正在删除旧数据...")
                QtWidgets.QApplication.processEvents()  # 刷新界面，让状态显示出来
                time.sleep(0.3)  # 短暂延迟，让用户能看到"正在删除"

                for file_path in files_to_delete:
                    try:
                        os.remove(file_path)
                        print(f"✅ 已删除文件: {file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除文件失败: {file_path}, 错误: {e}")

                self.gn_update_status.setText("✅ 旧数据已删除")
            else:
                print("⚠️ 未找到需要删除的旧数据文件")
                self.gn_update_status.setText("⚠️ 未找到旧数据文件")

            QtWidgets.QApplication.processEvents()  # 刷新界面
            # ============================================================

            # ================= 第二步：下载新数据 =================
            self.gn_update_status.setText("🔄 正在更新数据（龙虎榜 + 基金）...")
            QtWidgets.QApplication.processEvents()

            # 创建 update 实例并执行 run 方法
            updater = data_update.update()
            updater.run()

            print("✅ update.run() 执行完成")

            # ================= 第三步：更新完成并刷新表格 =================
            self.gn_update_status.setText("✅ 数据更新完成！")
            self.gn_update_status.setStyleSheet("color: green; font-weight: bold;")

            # 刷新界面显示
            QtWidgets.QApplication.processEvents()

            # ================= 第四步：自动重新生成表格 =================
            self.gn_update_status.setText("🔄 正在生成表格...")
            QtWidgets.QApplication.processEvents()

            # 调用生成表格的方法
            self.generate_fund_table()

            # ================= 第五步：恢复默认样式 =================
            # 延时恢复为默认样式
            def restore_status():
                self.gn_update_status.setText("就绪")
                self.gn_update_status.setStyleSheet("color: gray; font-weight: normal;")

            QtCore.QTimer.singleShot(2000, restore_status)
            # ============================================================

        except Exception as e:
            import traceback
            print(f"❌ 数据更新失败: {e}")
            traceback.print_exc()

            self.gn_update_status.setText(f"❌ 更新失败：{str(e)}")
            self.gn_update_status.setStyleSheet("color: red; font-weight: bold;")




if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    ui = MainWindow()
    ui.setupUi(window)
    window.show()
    sys.exit(app.exec_())

    # fd = fund_data()
    # fd.fund_daily()
    # print("获取所有基金历史净值成功，数据已经保存")
    #
    # print("----正在获取ETF基数现价")
    # fd.fund_etf_and_lof()
    # print("------获取ETF现价成功，数据已经保存")
