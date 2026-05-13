# -*- coding: utf-8 -*-
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QAction,
                             QTabWidget, QWidget, QLabel)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush

# ==================== 导入数据更新模块 ====================
import data_update
from link_tdx import link_tdx


# ==================== UI 组件 ====================
class LineTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lines = []  # 实线 (前3名)
        self.dotted_lines = []  # 点线 (稳定/上升3连)
        self.click_lines = []  # 点击线
        self.df_data = None
        self.start_col = None
        self.info_callback = None
        self.info_text = "等待操作..."  # 【新增】存储当前表格的信息文本
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def set_df_data(self, df):
        self.df_data = df

    def set_lines(self, lines):
        self.lines = lines

    def set_info_callback(self, callback):
        self.info_callback = callback

    def set_click_line(self, code):
        self.click_lines = []
        if self.df_data is None or code is None:
            self.viewport().update()
            return
        positions = []
        num_dates = len(self.df_data)
        for col_idx in range(num_dates):
            for row_idx in range(50):
                cell_code = str(self.df_data.iloc[col_idx].get(f"排名{row_idx + 1}", ""))
                if cell_code == code:
                    positions.append((row_idx, col_idx + 1))
                    break
        for i in range(len(positions) - 1):
            start_row, start_col = positions[i]
            end_row, end_col = positions[i + 1]
            self.click_lines.append((start_row, start_col, end_row, end_col, '#800020'))
        # 更新信息并保存
        msg = f"📍 单击代码 {code}，找到 {len(positions)} 个位置"
        self.info_text = msg
        if self.info_callback:
            self.info_callback(msg)
        self.viewport().update()

    def clear_click_line(self):
        self.click_lines = []
        self.viewport().update()

    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item is None:
            return
        col = item.column()
        if col < 1:
            return
        menu = QMenu(self)
        action = QAction(f"从第{col}列开始计算并画线", self)
        action.triggered.connect(lambda: self.on_calc_from_column(col))
        menu.addAction(action)
        action_clear = QAction("清除所有线条", self)
        action_clear.triggered.connect(self.clear_all_lines)
        menu.addAction(action_clear)
        menu.exec_(self.mapToGlobal(pos))

    def on_calc_from_column(self, col):
        self.start_col = col
        self.calculate_and_draw_lines()

    def clear_all_lines(self):
        self.lines = []
        self.dotted_lines = []
        self.click_lines = []
        self.start_col = None
        self.viewport().update()
        # 更新信息并保存
        msg = "🧹 已清除所有线条"
        self.info_text = msg
        if self.info_callback:
            self.info_callback(msg)

    def calculate_and_draw_lines(self):
        if self.df_data is None or self.start_col is None:
            return
        df = self.df_data
        num_dates = len(df)
        start_data_idx = self.start_col - 1
        if start_data_idx >= num_dates - 1:
            msg = "起始列是最后一列，无法计算"
            self.info_text = msg
            if self.info_callback:
                self.info_callback(msg)
            return

        # ========== 预处理数据 ==========
        col_code_maps = []
        for c_idx in range(num_dates):
            temp_map = {}
            for r_idx in range(50):
                code = str(df.iloc[c_idx].get(f"排名{r_idx + 1}", ""))
                if code:
                    temp_map[code] = r_idx
            col_code_maps.append(temp_map)

        # ========== 步骤1: 计算前3名 ==========
        code_to_row_start = col_code_maps[start_data_idx]
        code_to_row_next = col_code_maps[start_data_idx + 1]
        upward_moves = []
        for code in code_to_row_next:
            if code in code_to_row_start:
                row_start = code_to_row_start[code]
                row_next = code_to_row_next[code]
                if row_next < row_start:
                    distance = row_start - row_next
                    upward_moves.append(
                        {'code': code, 'start_row': row_start, 'end_row': row_next, 'distance': distance})
        upward_moves.sort(key=lambda x: x['distance'], reverse=True)
        top3 = upward_moves[:3]
        top3_codes = set([m['code'] for m in top3])
        colors = ['#FF0000', '#0000FF', '#00FF00']
        color_names = ['红色', '蓝色', '绿色']
        self.lines = []
        info_lines = []
        for idx, move in enumerate(top3):
            code = move['code']
            color = colors[idx]
            color_name = color_names[idx]
            positions = []
            for col_offset in range(start_data_idx, num_dates):
                if code in col_code_maps[col_offset]:
                    row_idx = col_code_maps[col_offset][code]
                    positions.append((row_idx, col_offset + 1))
            for i in range(len(positions) - 1):
                start_row, start_col_pos = positions[i]
                end_row, end_col_pos = positions[i + 1]
                self.lines.append((start_row, start_col_pos, end_row, end_col_pos, color))
            info_lines.append(f"📈 {code}: 移动{move['distance']}位, {color_name}")

        # ========== 步骤2: 计算点线 ==========
        self.dotted_lines = []
        dotted_count = 0
        for c in range(start_data_idx, num_dates - 2):
            map_c1 = col_code_maps[c]
            map_c2 = col_code_maps[c + 1]
            map_c3 = col_code_maps[c + 2]
            common_codes = set(map_c1.keys()) & set(map_c2.keys()) & set(map_c3.keys())
            for code in common_codes:
                if code in top3_codes:
                    continue
                r1 = map_c1[code]
                r2 = map_c2[code]
                r3 = map_c3[code]
                if r1 >= r2 and r2 >= r3:
                    dot_color = '#FF00FF'
                    self.dotted_lines.append((r1, c + 1, r2, c + 2, dot_color))
                    self.dotted_lines.append((r2, c + 2, r3, c + 3, dot_color))
                    dotted_count += 1

        # ========== 更新信息显示 ==========
        display_info = ""
        if info_lines:
            display_info = "\n".join(info_lines) + f"\n\n🔹 点线: {dotted_count} 个稳定趋势"
        elif dotted_count > 0:
            display_info = f"🔹 点线: {dotted_count} 个稳定趋势"
        else:
            display_info = "暂无明显趋势"
        # 【关键】保存当前信息到对象属性
        self.info_text = display_info
        if self.info_callback:
            self.info_callback(display_info)
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        self.draw_lines(self.dotted_lines, is_dotted=True)
        self.draw_lines(self.lines, is_dotted=False)
        self.draw_lines(self.click_lines, is_dotted=False)

    def draw_lines(self, lines, is_dotted=False):
        if not lines:
            return
        painter = QPainter(self.viewport())
        import math
        for line_data in lines:
            if len(line_data) != 5:
                continue
            start_row, start_col, end_row, end_col, color = line_data
            if start_row < 0 or start_col < 0 or end_row < 0 or end_col < 0:
                continue
            if start_row >= self.rowCount() or end_row >= self.rowCount():
                continue
            if start_col >= self.columnCount() or end_col >= self.columnCount():
                continue
            start_rect = self.visualRect(self.model().index(start_row, start_col))
            end_rect = self.visualRect(self.model().index(end_row, end_col))
            start_point = start_rect.center()
            end_point = end_rect.center()
            pen = QPen(QColor(color), 2 if is_dotted else 3)
            if is_dotted:
                pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(start_point, end_point)
            if not is_dotted:
                dx = end_point.x() - start_point.x()
                dy = end_point.y() - start_point.y()
                if dx != 0 or dy != 0:
                    angle = math.atan2(dy, dx)
                    arrow_size = 8
                    p1 = QPoint(int(end_point.x() - arrow_size * math.cos(angle - math.pi / 6)),
                                int(end_point.y() - arrow_size * math.sin(angle - math.pi / 6)))
                    p2 = QPoint(int(end_point.x() - arrow_size * math.cos(angle + math.pi / 6)),
                                int(end_point.y() - arrow_size * math.sin(angle + math.pi / 6)))
                    painter.drawLine(end_point, p1)
                    painter.drawLine(end_point, p2)
        painter.end()


# ==================== UI 主窗口 ====================
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 1350)
        icon = QtGui.QIcon()
        try:
            icon.addPixmap(QtGui.QPixmap("app4.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        except:
            pass
        MainWindow.setWindowIcon(icon)
        self.centralwidget = QtWidgets.QWidget()
        MainWindow.setCentralWidget(self.centralwidget)
        main_layout = QVBoxLayout(self.centralwidget)

        # 1. 按钮区域
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.btn_1_week = QtWidgets.QPushButton("近1周")
        self.btn_2_weeks = QtWidgets.QPushButton("近2周")
        self.btn_1_month = QtWidgets.QPushButton("近1月")
        self.btn_3_months = QtWidgets.QPushButton("近3月")
        self.horizontalLayout.addWidget(self.btn_1_week)
        self.horizontalLayout.addWidget(self.btn_2_weeks)
        self.horizontalLayout.addWidget(self.btn_1_month)
        self.horizontalLayout.addWidget(self.btn_3_months)
        font_label = QtGui.QFont()
        font_label.setFamily("SimHei")
        font_label.setPointSize(12)
        self.start_date_label = QtWidgets.QLabel("开始日期:")
        self.start_date_label.setFont(font_label)
        self.start_date_input = QtWidgets.QLineEdit()
        self.start_date_input.setText((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        self.start_date_input.setFixedWidth(100)
        self.end_date_label = QtWidgets.QLabel("结束日期:")
        self.end_date_label.setFont(font_label)
        self.end_date_input = QtWidgets.QLineEdit()
        self.end_date_input.setText(datetime.now().strftime('%Y-%m-%d'))
        self.end_date_input.setFixedWidth(100)
        self.analyze_btn = QtWidgets.QPushButton("分析连板高度")
        self.btn_toggle_display = QtWidgets.QPushButton("显示代码")
        self.btn_toggle_display.setFixedHeight(35)
        self.btn_toggle_display.setStyleSheet(
            "QPushButton { background-color: rgb(255, 140, 0); color: white; font-size: 14px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: rgb(255, 120, 0); }")
        self.update_data_btn = QtWidgets.QPushButton("数据更新")
        self.horizontalLayout.addWidget(self.start_date_label)
        self.horizontalLayout.addWidget(self.start_date_input)
        self.horizontalLayout.addWidget(self.end_date_label)
        self.horizontalLayout.addWidget(self.end_date_input)
        self.horizontalLayout.addWidget(self.analyze_btn)
        self.horizontalLayout.addWidget(self.btn_toggle_display)
        self.horizontalLayout.addWidget(self.update_data_btn)
        self.update_info_label = QtWidgets.QLabel("⏳ 等待更新...")
        self.update_info_label.setStyleSheet(
            "color: #0066cc; font-weight: bold; padding: 5px; background-color: #e6f2ff; border-radius: 3px;")
        self.horizontalLayout.addWidget(self.update_info_label)
        main_layout.addWidget(self.widget)

        # 2. 标签页和右侧信息区的容器
        self.tab_container = QWidget()
        tab_container_layout = QHBoxLayout(self.tab_container)

        # 左侧：标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 20px;
                margin-right: 2px;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #FF4D4D;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
        """)
        self.em_tb = LineTableWidget()
        self.ths_tb = LineTableWidget()
        self.tdx_tb = LineTableWidget()
        self.cls_tb = LineTableWidget()
        self.tab_widget.addTab(self.em_tb, "东方财富")
        self.tab_widget.addTab(self.ths_tb, "同花顺")
        self.tab_widget.addTab(self.tdx_tb, "通达信")
        self.tab_widget.addTab(self.cls_tb, "财联社")
        tab_container_layout.addWidget(self.tab_widget, stretch=4)

        # 右侧：画线信息区
        self.info_widget = QWidget()
        self.info_widget.setFixedWidth(160)
        self.info_widget.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 5px;")
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(10, 10, 10, 10)
        self.info_title = QLabel("📊 画线信息")
        self.info_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        info_layout.addWidget(self.info_title)
        self.info_label = QLabel("等待操作...")
        self.info_label.setStyleSheet("font-size: 12px; padding: 10px; background-color: white; border-radius: 3px;")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignTop)
        info_layout.addWidget(self.info_label, stretch=1)
        tab_container_layout.addWidget(self.info_widget, stretch=1)
        main_layout.addWidget(self.tab_container)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "热榜排行"))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.show_name_mode = True  # 默认显示名称
        self.code_name_map = {}  # 代码到名称的映射
        self.load_name_map()  # 加载名称映射

        self.table_config = {
            'em': {'table': self.em_tb, 'csv': 'data/hot_em.csv'},
            'ths': {'table': self.ths_tb, 'csv': 'data/hot_ths.csv'},
            'tdx': {'table': self.tdx_tb, 'csv': 'data/hot_tdx.csv'},
            'cls': {'table': self.cls_tb, 'csv': 'data/hot_cls.csv'},
        }
        self.analyze_btn.clicked.connect(self.on_analyze_date_clicked)
        self.update_data_btn.clicked.connect(self.on_update_data_clicked)
        self.btn_toggle_display.clicked.connect(self.toggle_display)
        self.btn_1_week.clicked.connect(lambda: self.set_date_range(days=7))
        self.btn_2_weeks.clicked.connect(lambda: self.set_date_range(days=14))
        self.btn_1_month.clicked.connect(lambda: self.set_date_range(days=30))
        self.btn_3_months.clicked.connect(lambda: self.set_date_range(days=90))
        for key in self.table_config:
            self.table_config[key]['table'].cellClicked.connect(
                lambda row, col, t=self.table_config[key]['table']: self.on_table_cell_clicked(row, col, t)
            )
            self.table_config[key]['table'].set_info_callback(self.update_info_display)
        # 【新增】连接标签页切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.load_all_data()
        # 【新增】初始化时显示第一个标签页的信息
        self.on_tab_changed(0)

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
        self.load_all_data()
        # 刷新当前标签页的信息
        self.on_tab_changed(self.tab_widget.currentIndex())

    def on_tab_changed(self, index):
        """标签页切换时，更新右侧信息显示"""
        current_table = self.tab_widget.widget(index)
        if hasattr(current_table, 'info_text'):
            self.info_label.setText(current_table.info_text)

    def update_info_display(self, info_text):
        self.info_label.setText(info_text)

    def load_table_data(self, table, csv_file):
        if not os.path.exists(csv_file):
            return
        try:
            df = pd.read_csv(csv_file, encoding="utf-8-sig")
            if df.empty:
                return
            # 只保留最近10个日期的数据
            if len(df) > 10:
                df = df.tail(10).reset_index(drop=True)
            # 预处理数据：处理空值、去掉.0后缀并补足6位
            rank_columns = [col for col in df.columns if col.startswith("排名")]
            for col in rank_columns:
                def format_code(x):
                    if pd.isna(x):
                        return ""
                    s = str(x).strip()
                    if s == '' or s.lower() == 'nan':
                        return ""
                    # 去掉.0后缀并补足6位
                    return s.split('.')[0].zfill(6)

                df[col] = df[col].apply(format_code)
            table.set_df_data(df)
            dates = df["日期"].tolist()
            table.setColumnCount(1 + len(dates))
            table.setHorizontalHeaderLabels(['排名'] + [str(d) for d in dates])
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Fixed)
            for col in range(1 + len(dates)):
                table.setColumnWidth(col, 80)
            table.setRowCount(50)
            light_blue = QColor(230, 242, 255)
            light_gray = QColor(245, 245, 245)
            for i in range(1, 51):
                row_idx = i - 1
                is_multi_5 = (i % 5 == 0)
                rank_item = QTableWidgetItem(f"排名{i}")
                rank_item.setTextAlignment(Qt.AlignCenter)
                if is_multi_5:
                    rank_item.setBackground(QBrush(light_blue))
                table.setItem(row_idx, 0, rank_item)
                for col_idx, (_, row) in enumerate(df.iterrows(), start=1):
                    code = str(row.get(f"排名{i}", ""))
                    # 根据显示模式决定显示内容
                    if self.show_name_mode:
                        display_text = self.code_name_map.get(code, code)
                    else:
                        display_text = code
                    code_item = QTableWidgetItem(display_text)
                    code_item.setTextAlignment(Qt.AlignCenter)
                    # 存储实际代码到单元格
                    code_item.setData(Qt.UserRole, code)
                    if is_multi_5:
                        code_item.setBackground(QBrush(light_blue))
                    elif col_idx % 2 == 0:
                        code_item.setBackground(QBrush(light_gray))
                    table.setItem(row_idx, col_idx, code_item)
            if len(dates) >= 2:
                table.start_col = 1
                table.calculate_and_draw_lines()
        except Exception as e:
            print(f"加载失败 {csv_file}: {e}")

    def load_all_data(self):
        for key in self.table_config:
            self.load_table_data(self.table_config[key]['table'], self.table_config[key]['csv'])

    def on_table_cell_clicked(self, row, column, table):
        if column >= 1:
            code_item = table.item(row, column)
            if code_item:
                # 从单元格获取实际代码
                code = code_item.data(Qt.UserRole)
                display_text = code_item.text()
                if code:
                    link_tdx(code)
                    table.set_click_line(code)
        elif column == 0:
            table.clear_click_line()

    def set_date_range(self, days):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        self.end_date_input.setText(end_date.strftime('%Y-%m-%d'))
        self.start_date_input.setText(start_date.strftime('%Y-%m-%d'))

    def on_analyze_date_clicked(self):
        QtWidgets.QMessageBox.information(self, "提示",
                                          f"分析日期: {self.start_date_input.text()} 至 {self.end_date_input.text()}")

    def on_update_data_clicked(self):
        """点击按钮时，直接调用 data_update 的 run 方法"""
        try:
            self.update_info_label.setText("🔄 正在全量更新数据，请稍候...")
            QtWidgets.QApplication.processEvents()
            updater = data_update.update()
            updater.run()
            self.load_all_data()
            # 更新完成后刷新当前标签页的信息
            self.on_tab_changed(self.tab_widget.currentIndex())
            self.update_info_label.setText("✅ 全部数据更新完成")
            QtWidgets.QMessageBox.information(self, "完成", "全部数据已更新！")
        except Exception as e:
            self.update_info_label.setText(f"❌ 更新失败: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "错误", f"更新失败: {e}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
