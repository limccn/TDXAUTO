# -*- coding: utf-8 -*-
import os
import subprocess
import json
import sys
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QSpacerItem, QLabel, QWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QCheckBox, QPushButton, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
                             QMessageBox, QMenu, QColorDialog, QTextEdit)
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal, QTimer
import shutil


class ScriptRunner(QThread):
    """后台运行脚本并捕获输出的线程"""
    output_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(str, int)

    def __init__(self, program_name, script_path, script_dir):
        super().__init__()
        self.program_name = program_name
        self.script_path = script_path
        self.script_dir = script_dir

    def get_python_exe(self):
        """获取Python解释器路径"""
        if getattr(sys, 'frozen', False):
            python_exe = shutil.which('python')
            if python_exe:
                return python_exe
            python_exe = shutil.which('python3')
            if python_exe:
                return python_exe
            return None
        else:
            return sys.executable

    def run(self):
        try:
            python_exe = self.get_python_exe()
            if not python_exe:
                self.output_signal.emit(self.program_name, "❌ 找不到Python解释器，请确保已安装Python并添加到PATH")
                self.finished_signal.emit(self.program_name, -1)
                return
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            process = subprocess.Popen(
                [python_exe, '-u', self.script_path],
                cwd=self.script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env
            )
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.output_signal.emit(self.program_name, line.rstrip())
            process.wait()
            self.finished_signal.emit(self.program_name, process.returncode)
        except Exception as e:
            self.output_signal.emit(self.program_name, f"❌ 运行出错: {str(e)}")
            self.finished_signal.emit(self.program_name, -1)


class ShellWindow(QWidget):
    """独立的 Shell 输出窗口（支持自定义背景和字体颜色）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("通达信终端")
        self.resize(700, 900)
        self.setMinimumSize(600, 300)

        # 默认颜色配置
        self.bg_color = QColor(12, 12, 12)  # 通达信经典黑
        self.text_color = QColor(255, 255, 255)  # 纯白字

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 顶部工具栏
        toolbar = QHBoxLayout()

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedHeight(28)
        self.clear_btn.setStyleSheet(self._get_toolbar_btn_style())
        self.clear_btn.clicked.connect(self.clear_content)
        toolbar.addWidget(self.clear_btn)

        self.auto_scroll_cb = QCheckBox("自动滚动")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setStyleSheet("color: #888; font-size: 12px;")
        toolbar.addWidget(self.auto_scroll_cb)

        self.font_size_label = QLabel("字号:")
        self.font_size_label.setStyleSheet("color: #888; font-size: 12px;")
        toolbar.addWidget(self.font_size_label)

        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        self.font_size_spin.setFixedHeight(28)
        self.font_size_spin.setFixedWidth(60)
        self.font_size_spin.setStyleSheet("""
            QSpinBox {
                background-color: #1a1a1a; color: #cccccc;
                border: 1px solid #444; border-radius: 3px; padding: 2px; font-size: 12px;
            }
            QSpinBox::up-button, QSpinBox::down-button { background-color: #333; border: 1px solid #444; }
        """)
        self.font_size_spin.valueChanged.connect(self.update_shell_style)
        toolbar.addWidget(self.font_size_spin)

        # 新增：设置背景色按钮
        self.bg_color_btn = QPushButton("背景色")
        self.bg_color_btn.setFixedHeight(28)
        self.bg_color_btn.setStyleSheet(self._get_toolbar_btn_style())
        self.bg_color_btn.clicked.connect(self.set_bg_color)
        toolbar.addWidget(self.bg_color_btn)

        # 新增：设置字体色按钮
        self.text_color_btn = QPushButton("字体色")
        self.text_color_btn.setFixedHeight(28)
        self.text_color_btn.setStyleSheet(self._get_toolbar_btn_style())
        self.text_color_btn.clicked.connect(self.set_text_color)
        toolbar.addWidget(self.text_color_btn)

        toolbar.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setStyleSheet("""
            QPushButton { background-color: #222; color: #888; border: 1px solid #444; border-radius: 3px; font-size: 14px; }
            QPushButton:hover { background-color: #c0392b; color: white; }
        """)
        self.close_btn.clicked.connect(self.hide)
        toolbar.addWidget(self.close_btn)

        layout.addLayout(toolbar)

        # Shell 输出区域
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.update_shell_style()  # 初始化样式
        layout.addWidget(self.text_edit)

    def _get_toolbar_btn_style(self):
        """统一工具栏按钮样式"""
        return """
            QPushButton {
                background-color: #222; color: #aaaaaa; border: 1px solid #444;
                border-radius: 3px; padding: 2px 12px; font-size: 12px;
            }
            QPushButton:hover { background-color: #333; color: #ffffff; border: 1px solid #666; }
        """

    def _get_dimmed_color(self):
        """获取比当前字体颜色稍暗的颜色（用于时间戳和程序名前缀）"""
        r = max(0, int(self.text_color.red() * 0.5))
        g = max(0, int(self.text_color.green() * 0.5))
        b = max(0, int(self.text_color.blue() * 0.5))
        return QColor(r, g, b).name()

    def update_shell_style(self):
        """统一更新输出区域的样式表"""
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.bg_color.name()};
                border: 1px solid #333;
                font-family: 'Consolas', 'Courier New', 'Microsoft YaHei';
                font-size: {self.font_size_spin.value()}pt;
                padding: 8px;
                selection-background-color: #264f78;
                selection-color: #ffffff;
            }}
        """)

    def set_bg_color(self):
        """设置背景颜色"""
        color = QColorDialog.getColor(self.bg_color, self, "选择背景色")
        if color.isValid():
            self.bg_color = color
            self.update_shell_style()

    def set_text_color(self):
        """设置字体颜色"""
        color = QColorDialog.getColor(self.text_color, self, "选择字体颜色")
        if color.isValid():
            self.text_color = color
            # 字体颜色通过 HTML span 控制，无需刷新全局样式表，但可以顺手刷一下
            self.update_shell_style()

    def append_output(self, program_name, message):
        """追加输出"""
        time_str = datetime.now().strftime("%H:%M:%S")
        prefix_color = self._get_dimmed_color()
        text_color = self.text_color.name()

        # 使用 HTML 强制指定颜色，确保历史记录和新记录颜色独立互不干扰
        prefix = f'<span style="color:{prefix_color};">[{time_str}]</span> <span style="color:{prefix_color};">[{program_name}]</span> '
        content = f'<span style="color:{text_color};">{message}</span>'

        self.text_edit.append(prefix + content)
        if self.auto_scroll_cb.isChecked():
            cursor = self.text_edit.textCursor()
            cursor.movePosition(cursor.End)
            self.text_edit.setTextCursor(cursor)

    def append_separator(self):
        """追加分隔线"""
        # 分隔线颜色取字体颜色和背景色的中间值
        sep_color = self._get_dimmed_color()
        self.text_edit.append(f'<span style="color:{sep_color};">────────────────────────────────────────</span>')

    def clear_content(self):
        """清空内容"""
        self.text_edit.clear()

    def closeEvent(self, event):
        """点击关闭按钮时隐藏而不是关闭"""
        event.ignore()
        self.hide()


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(680, 900)
        icon = QtGui.QIcon()
        try:
            icon.addPixmap(QtGui.QPixmap("app3.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        except:
            print("未找到app3.ico图标，不影响窗口功能")
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

        # --- Widget (按钮区域) ---
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.add_btn = QtWidgets.QPushButton(self.widget)
        self.add_btn.setObjectName("add_btn")
        self.add_btn.setStyleSheet("""
            QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 4px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.horizontalLayout.addWidget(self.add_btn)

        self.delete_btn = QtWidgets.QPushButton(self.widget)
        self.delete_btn.setObjectName("delete_btn")
        self.delete_btn.setStyleSheet("""
            QPushButton { background-color: #f44336; color: white; border: none; border-radius: 4px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.horizontalLayout.addWidget(self.delete_btn)

        self.shell_btn = QtWidgets.QPushButton(self.widget)
        self.shell_btn.setObjectName("shell_btn")
        self.shell_btn.setStyleSheet("""
            QPushButton { background-color: #222; color: #ffffff; border: 1px solid #444; border-radius: 4px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #333; border-color: #ffffff; }
        """)
        self.horizontalLayout.addWidget(self.shell_btn)

        self.horizontalLayout.addStretch()
        main_layout.addWidget(self.widget)

        self.py_tb = QTableWidget()
        self.py_tb.setColumnCount(5)
        self.py_tb.setHorizontalHeaderLabels(['选', '程序名', '时间', '描述', '运行'])
        header_font = QtGui.QFont()
        header_font.setFamily("SimHei")
        header_font.setPointSize(11)
        self.py_tb.horizontalHeader().setFont(header_font)
        header = self.py_tb.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.py_tb.setColumnWidth(0, 30)
        self.py_tb.setColumnWidth(1, 140)
        self.py_tb.setColumnWidth(2, 100)
        self.py_tb.setColumnWidth(4, 80)
        table_font = QtGui.QFont()
        table_font.setFamily("SimHei")
        table_font.setPointSize(11)
        self.py_tb.setFont(table_font)
        self.py_tb.verticalHeader().setDefaultSectionSize(35)
        self.py_tb.setContextMenuPolicy(Qt.CustomContextMenu)
        self.py_tb.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.py_tb)

        self.run_tb = QTableWidget()
        self.run_tb.setColumnCount(3)
        self.run_tb.setHorizontalHeaderLabels(['时间', '程序名', '运行信息'])
        self.run_tb.setStyleSheet("""
            QTableWidget { background-color: #1a1a1a; color: #00ff00; gridline-color: #333333; border: 1px solid #444444; }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section { background-color: #2d2d2d; color: #00ff00; border: 1px solid #444444; padding: 5px; font-weight: bold; }
        """)
        run_header_font = QtGui.QFont()
        run_header_font.setFamily("SimHei")
        run_header_font.setPointSize(9)
        self.run_tb.horizontalHeader().setFont(run_header_font)
        run_header = self.run_tb.horizontalHeader()
        run_header.setSectionResizeMode(0, QHeaderView.Fixed)
        run_header.setSectionResizeMode(1, QHeaderView.Fixed)
        run_header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.run_tb.setColumnWidth(0, 100)
        self.run_tb.setColumnWidth(1, 100)
        run_table_font = QtGui.QFont("Consolas", 9)
        self.run_tb.setFont(run_table_font)
        self.run_tb.setFixedHeight(250)
        self.run_tb.verticalHeader().setDefaultSectionSize(12)
        self.run_tb.verticalHeader().setVisible(False)
        main_layout.addWidget(self.run_tb)
        main_layout.addStretch()

        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 880, 23))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "程序功能大全"))
        self.add_btn.setText(_translate("MainWindow", "➕ 添加"))
        self.delete_btn.setText(_translate("MainWindow", "🗑️ 删除"))
        self.shell_btn.setText(_translate("MainWindow", "终端"))


class AddProgramDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新程序")
        self.setFixedSize(400, 220)
        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入程序名（如：hot_lbtt.py）")
        self.name_input.setMinimumHeight(30)
        layout.addRow("程序名:", self.name_input)
        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("留空表示手动运行，或输入时间如: 14:30")
        self.time_input.setMinimumHeight(30)
        layout.addRow("定时:", self.time_input)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("请输入程序描述")
        self.desc_input.setMinimumHeight(30)
        layout.addRow("描述:", self.desc_input)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Ok).setText("确定")
        button_box.button(QDialogButtonBox.Ok).setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; border: none; border-radius: 4px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background-color: #45a049; }")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.button(QDialogButtonBox.Cancel).setStyleSheet(
            "QPushButton { background-color: #9e9e9e; color: white; border: none; border-radius: 4px; padding: 8px 20px; } QPushButton:hover { background-color: #757575; }")
        layout.addRow(button_box)

    def get_data(self):
        return (self.name_input.text().strip(), self.time_input.text().strip(), self.desc_input.text().strip())


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        if getattr(sys, 'frozen', False):
            self.app_path = os.path.dirname(sys.executable)
        else:
            self.app_path = os.path.dirname(os.path.abspath(__file__))
        self.settings_file = os.path.join(self.app_path, 'aaa.json')
        self.cell_colors = {}
        self.runners = {}
        self.today_ran = set()

        self.shell_window = ShellWindow()
        self.shell_btn.clicked.connect(self.toggle_shell_window)
        self.load_table_data()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_schedule)
        self.timer.start(60000)
        QTimer.singleShot(1000, self.check_schedule)
        self.add_btn.clicked.connect(self.on_add_clicked)
        self.delete_btn.clicked.connect(self.on_delete_clicked)

    def toggle_shell_window(self):
        if self.shell_window.isVisible():
            self.shell_window.hide()
        else:
            self.shell_window.show()
            self.shell_window.raise_()

    def check_schedule(self):
        current_time = datetime.now()
        current_str = current_time.strftime("%H:%M")
        today_str = current_time.strftime("%Y-%m-%d")
        for row in range(self.py_tb.rowCount()):
            time_item = self.py_tb.item(row, 2)
            name_item = self.py_tb.item(row, 1)
            if time_item and name_item:
                scheduled_time = time_item.text().strip()
                program_name = name_item.text().strip()
                if scheduled_time and scheduled_time == current_str:
                    run_key = f"{today_str}_{program_name}"
                    if run_key not in self.today_ran:
                        self.append_log(program_name, f"⏰ 定时触发: {scheduled_time}")
                        self.on_run_clicked(row)
                        self.today_ran.add(run_key)
        if current_str == "00:00":
            self.today_ran.clear()

    def append_log(self, program_name, message):
        self.shell_window.append_output(program_name, message)
        self.run_tb.insertRow(0)
        time_str = datetime.now().strftime("%H:%M:%S")
        time_item = QTableWidgetItem(time_str)
        time_item.setTextAlignment(Qt.AlignCenter)
        self.run_tb.setItem(0, 0, time_item)
        name_item = QTableWidgetItem(program_name)
        name_item.setTextAlignment(Qt.AlignCenter)
        self.run_tb.setItem(0, 1, name_item)
        msg_item = QTableWidgetItem(message)
        msg_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.run_tb.setItem(0, 2, msg_item)
        while self.run_tb.rowCount() > 100:
            self.run_tb.removeRow(self.run_tb.rowCount() - 1)
        self.run_tb.scrollToTop()

    def on_script_finished(self, program_name, exit_code):
        self.shell_window.append_separator()
        if exit_code == 0:
            self.append_log(program_name, "✅ 运行完成")
        else:
            self.append_log(program_name, f"⚠️ 已退出 (代码: {exit_code})")
        if program_name in self.runners:
            del self.runners[program_name]

    def show_context_menu(self, position: QPoint):
        item = self.py_tb.itemAt(position)
        if not item: return
        row, col = item.row(), item.column()
        if col != 3: return
        menu = QMenu(self)
        set_color_action = menu.addAction("🎨 设置单元格颜色")
        clear_color_action = menu.addAction("🗑️ 清除单元格颜色")
        action = menu.exec_(self.py_tb.viewport().mapToGlobal(position))
        if action == set_color_action:
            self.set_cell_color(row, col)
        elif action == clear_color_action:
            self.clear_cell_color(row, col)

    def set_cell_color(self, row, col):
        current_color = self.cell_colors.get((row, col), QColor(255, 255, 255))
        color = QColorDialog.getColor(current_color, self, "选择单元格颜色")
        if color.isValid():
            item = self.py_tb.item(row, col)
            if item:
                item.setBackground(QBrush(color))
                self.cell_colors[(row, col)] = color
                self.save_table_data()

    def clear_cell_color(self, row, col):
        item = self.py_tb.item(row, col)
        if item:
            bg_color = QColor(135, 206, 250) if row % 2 == 0 else QColor(255, 255, 255)
            item.setBackground(QBrush(bg_color))
            if (row, col) in self.cell_colors: del self.cell_colors[(row, col)]
            self.save_table_data()

    def adjust_table_height(self):
        row_count = self.py_tb.rowCount()
        total_height = row_count * 35 + self.py_tb.horizontalHeader().height() + 4
        self.py_tb.setFixedHeight(total_height)

    def load_table_data(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                programs = data.get('programs', [])
                colors_data = data.get('cell_colors', {})
                self.cell_colors = {}
                for key, color_list in colors_data.items():
                    self.cell_colors[eval(key)] = QColor(*color_list)
                if programs:
                    self.refresh_table(programs)
                    return
            except Exception as e:
                print(f"⚠️ 读取配置文件失败: {e}")
        self.refresh_table([{"name": "程序A", "time": "", "desc": "这是程序A的描述说明"}])

    def save_table_data(self):
        programs = []
        for row in range(self.py_tb.rowCount()):
            name_item, time_item, desc_item = self.py_tb.item(row, 1), self.py_tb.item(row, 2), self.py_tb.item(row, 3)
            if name_item and desc_item:
                programs.append(
                    {'name': name_item.text(), 'time': time_item.text() if time_item else '', 'desc': desc_item.text()})
        colors_data = {str(k): [v.red(), v.green(), v.blue()] for k, v in self.cell_colors.items()}
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump({'programs': programs, 'cell_colors': colors_data}, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")

    def refresh_table(self, programs):
        self.py_tb.setRowCount(len(programs))
        for row, item in enumerate(programs):
            if isinstance(item, dict):
                name, time_str, desc = item.get('name', ''), item.get('time', ''), item.get('desc', '')
            else:
                name, time_str, desc = (item[0], item[1], item[2]) if len(item) >= 3 else (item[0], '', item[1])
            self.add_table_row(row, name, time_str, desc)
        self.adjust_table_height()

    def add_table_row(self, row, name, time_str, desc):
        checkbox, widget = QCheckBox(), QWidget()
        layout_h = QHBoxLayout(widget)
        layout_h.addWidget(checkbox);
        layout_h.setContentsMargins(0, 0, 0, 0);
        layout_h.setAlignment(Qt.AlignCenter)
        self.py_tb.setCellWidget(row, 0, widget)
        name_item = QTableWidgetItem(name);
        name_item.setTextAlignment(Qt.AlignCenter);
        self.py_tb.setItem(row, 1, name_item)
        time_item = QTableWidgetItem(time_str);
        time_item.setTextAlignment(Qt.AlignCenter);
        time_item.setForeground(QBrush(QColor(255, 140, 0)))
        font = time_item.font();
        font.setPointSize(18);
        time_item.setFont(font);
        self.py_tb.setItem(row, 2, time_item)
        desc_item = QTableWidgetItem(desc);
        desc_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter);
        desc_item.setFont(QFont("SimHei", 18));
        self.py_tb.setItem(row, 3, desc_item)
        run_btn = QPushButton("运行")
        run_btn.setStyleSheet(
            "QPushButton { background-color: purple; color: white; border: none; border-radius: 2px; padding: 5px 12px; font-weight: bold; } QPushButton:hover { background-color: #45a049; }")
        run_btn.clicked.connect(lambda checked, r=row: self.on_run_clicked(r))
        self.py_tb.setCellWidget(row, 4, run_btn)
        bg_color = QColor(135, 206, 250) if row % 2 == 0 else QColor(255, 255, 255)
        if (row, 3) in self.cell_colors:
            desc_item.setBackground(QBrush(self.cell_colors[(row, 3)]))
        else:
            desc_item.setBackground(QBrush(bg_color))
        name_item.setBackground(QBrush(bg_color));
        time_item.setBackground(QBrush(bg_color))

    def on_add_clicked(self):
        dialog = AddProgramDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, time_str, desc = dialog.get_data()
            if not name: QMessageBox.warning(self, "提示", "程序名不能为空！"); return
            if time_str:
                try:
                    datetime.strptime(time_str, "%H:%M")
                except ValueError:
                    QMessageBox.warning(self, "提示", "时间格式不正确！请使用 HH:MM 格式"); return
            row = self.py_tb.rowCount();
            self.py_tb.insertRow(row)
            self.add_table_row(row, name, time_str, desc);
            self.adjust_table_height();
            self.save_table_data()
            QMessageBox.information(self, "成功", f"已添加程序: {name}")

    def on_delete_clicked(self):
        rows_to_delete = [row for row in range(self.py_tb.rowCount()) if (widget := self.py_tb.cellWidget(row, 0)) and (
            cb := widget.findChild(QCheckBox)) and cb.isChecked()]
        if not rows_to_delete: QMessageBox.warning(self, "提示", "请先勾选要删除的程序！"); return
        if QMessageBox.question(self, '确认删除', f'确定要删除选中的 {len(rows_to_delete)} 个程序吗？',
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            for row in sorted(rows_to_delete, reverse=True): self.py_tb.removeRow(row)
            for key in [k for k in self.cell_colors if k[0] in rows_to_delete]: del self.cell_colors[key]
            new_cell_colors = {}
            for (old_row, col), color in self.cell_colors.items():
                new_row = old_row - sum(1 for d in sorted(rows_to_delete) if old_row > d)
                new_cell_colors[(new_row, col)] = color
            self.cell_colors = new_cell_colors
            for row in range(self.py_tb.rowCount()):
                bg_color = QColor(135, 206, 250) if row % 2 == 0 else QColor(255, 255, 255)
                for c in [1, 2]:
                    if item := self.py_tb.item(row, c): item.setBackground(QBrush(bg_color))
                if (item := self.py_tb.item(row, 3)) and (row, 3) not in self.cell_colors: item.setBackground(
                    QBrush(bg_color))
            self.adjust_table_height();
            self.save_table_data()
            QMessageBox.information(self, "成功", f"已删除 {len(rows_to_delete)} 个程序")

    def on_run_clicked(self, row):
        name_item = self.py_tb.item(row, 1)
        program_name = name_item.text() if name_item else ""
        if not program_name: QMessageBox.warning(self, "错误", "程序名无效！"); return
        if not program_name.endswith('.py'): QMessageBox.warning(self, "提示",
                                                                 f"'{program_name}' 不是Python文件！"); return
        script_path = os.path.join(self.app_path, program_name)
        if not os.path.exists(script_path):
            QMessageBox.critical(self, "错误", f"找不到程序文件:\n{script_path}")
            self.append_log(program_name, "❌ 文件不存在");
            return
        self.shell_window.show();
        self.shell_window.raise_()
        self.shell_window.append_separator()
        self.append_log(program_name, "🚀 开始运行...")
        runner = ScriptRunner(program_name, script_path, self.app_path)
        runner.output_signal.connect(self.append_log);
        runner.finished_signal.connect(self.on_script_finished)
        runner.start();
        self.runners[program_name] = runner


if __name__ == "__main__":
    import io

    if sys.stdout and hasattr(sys.stdout, 'buffer'): sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                                                                   errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'buffer'): sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8',
                                                                                   errors='replace')
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
