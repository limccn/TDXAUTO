# -*- coding: utf-8 -*-
import sys
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
        self.banner.setText(_translate("MainWindow", "LOF场外场内套利！"))

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
        sortable_columns = ['场内最新价', '单位净值', '成交额', '溢价']

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
                        if num_val > 10000:
                            # 橙色加粗
                            item.setForeground(QtGui.QColor(218, 49, 220))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        elif 1000 <= num_val <= 10000:
                            # 红色加粗
                            item.setForeground(QtGui.QColor(255, 0, 70))
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
        """生成 fund_table.csv：合并场内价格与单位净值，计算溢价"""
        try:
            etf_path = "data/fund_lof.csv"
            day_path = "data/fund_day.csv"

            # 1. 读取数据
            df_etf = pd.read_csv(etf_path, encoding='utf-8-sig')
            df_day = pd.read_csv(day_path, encoding='utf-8-sig')

            fund_table = pd.DataFrame(columns=[
                '代码', '名称', '场内最新价', '成交额', '溢价',
                '基金代码', '基金名称', '单位净值'
            ])

            # 2. 填充基础数据
            min_len = min(len(df_etf), len(df_day))

            df = df_etf['代码'].iloc[:min_len]
            fund_table['代码'] = df_etf['代码'].iloc[:min_len]
            fund_table['名称'] = df_etf['名称'].iloc[:min_len]
            fund_table['场内最新价'] = df_etf['最新价'].iloc[:min_len]
            fund_table['成交额'] = round(df_etf['成交额'].iloc[:min_len] / 10000, 2)

            # 3. 映射填充数据
            fund_table['代码'] = fund_table['代码'].astype(str)
            df_day['代码'] = df_day['代码'].astype(str)
            lookup_df = df_day.set_index('代码')

            fund_table['单位净值'] = fund_table['代码'].map(lookup_df.iloc[:, 1])
            if '基金名称' in df_day.columns:
                fund_table['基金名称'] = fund_table['代码'].map(lookup_df['基金名称'])

            fund_table['基金代码'] = fund_table['代码']

            # 4. 数据类型转换与计算
            fund_table['单位净值'] = pd.to_numeric(fund_table['单位净值'], errors='coerce')
            fund_table['场内最新价'] = pd.to_numeric(fund_table['场内最新价'], errors='coerce')

            # ================= 新增：过滤单位净值为空值的行 =================
            # dropna(subset=['单位净值']) 会检查 '单位净值' 列，删除该列值为 NaN 的行
            # inplace=True 表示直接在原 DataFrame 上修改
            fund_table.dropna(subset=['单位净值'], inplace=True)
            # ========================================================

            fund_table['溢价'] = 100 * (fund_table['场内最新价'] - fund_table['单位净值']) / fund_table['单位净值']
            fund_table['溢价'] = fund_table['溢价'].round(2)

            # ================= 新增：保存原始数据用于恢复无排序状态 =================
            self.df_fund_display = fund_table.copy()
            # =======================================================================

            # 5. 显示数据（调用提取出的显示方法）
            self.display_fund_data(fund_table)
            self.fund_table.horizontalHeader().setSortIndicator(-1, QtCore.Qt.AscendingOrder)
            self.df_fund_display = fund_table.copy()
            print(f"✅ fund_table 已更新，共 {len(fund_table)} 条记录")

            self._sorted_column = None
            self._sort_order = None

        except Exception as e:
            import traceback
            print(f"❌ 生成失败: {e}")
            traceback.print_exc()

            self.fund_table.setRowCount(1)
            self.fund_table.setColumnCount(1)
            self.fund_table.setHorizontalHeaderLabels(['错误'])
            self.fund_table.setItem(0, 0, QtWidgets.QTableWidgetItem(f"生成失败：{str(e)}"))

    # ================= 修改：列头点击事件处理（增加循环逻辑） =================
    def on_fund_table_header_clicked(self, logical_index):
        column_name = self.fund_table.horizontalHeaderItem(logical_index).text()
        sortable_columns = ['场内最新价', '单位净值', '成交额', '溢价']
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
            etf_path = 'data/fund_lof.csv'

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
