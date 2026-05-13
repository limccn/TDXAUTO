# -*- coding: utf-8 -*-
import os
import sys
if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(sys.executable))
    if hasattr(sys, '_MEIPASS'):
        sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(sys.executable))
    if hasattr(sys, '_MEIPASS'):
        sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import json
import datetime
import csv
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QHeaderView,
    QWidget, QHBoxLayout, QLabel, QPushButton, QTableWidget, QVBoxLayout,
    QInputDialog, QDialog, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QEvent, QTimer, QObject, pyqtSignal, QRunnable, QThreadPool
from PyQt5.QtGui import QFont, QPixmap, QCursor, QColor
from PyQt5 import QtCore, QtGui, QtWidgets
import time
import winsound
from tdx_auto_trader import TDX_CMD_FILE
import requests
import matplotlib
matplotlib.use('Qt5Agg')
from link_tdx import link_tdx


def get_price_em(secid: str):
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {"invt": 2, "fltt": 2, "fields": "f58,f107,f57,f43,f59,f169,f170", "secid": secid}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json().get("data")
        code = data['f57']
        name = data['f58']
        current = data['f43']
        change_rate = data.get('f170', 0)
        if change_rate is not None:
            prev = current / (1 + change_rate / 100)
        else:
            prev = None
        return {'name': name, 'price': current, 'prev_close': prev}
    except Exception as e:
        print(f"{secid}: 请求失败 - {e}")
        return None


def get_price_sina(code):
    if code.startswith(('60', '68')):
        sina_code = f"sh{code}"
    else:
        sina_code = f"sz{code}"
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'referer': 'https://finance.sina.com.cn/',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    url = f"https://hq.sinajs.cn/list={sina_code}"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'gbk'
        text = response.text.strip()
        if not text:
            return None
        match = re.search(r'"(.+)"', text)
        if not match:
            return None
        data_str = match.group(1)
        parts = data_str.split(',')
        if len(parts) < 6:
            return None
        name = parts[0]
        prev_close = float(parts[2])
        current = float(parts[3])
        return {'name': name, 'price': current, 'prev_close': prev_close}
    except Exception as e:
        print(f"{code}: 新浪请求失败 - {e}")
        return None


class CombinedDataWorker(QObject):
    data_ready = pyqtSignal(str, dict)
    data_error = pyqtSignal(str, str)

    def run_fetch(self, code):
        result = get_price_sina(code)
        if result:
            self.data_ready.emit(code, result)
            return
        try:
            if code.startswith(('60', '68')):
                secid = f"1.{code}"
            else:
                secid = f"0.{code}"
            result = get_price_em(secid)
            if result:
                self.data_ready.emit(code, result)
                return
        except Exception as e:
            print(f"东财备选也失败 [{code}]: {e}")
        self.data_error.emit(code, "获取数据失败")


class CombinedFetchRunnable(QRunnable):
    def __init__(self, worker, code):
        super().__init__()
        self.worker = worker
        self.code = code

    def run(self):
        self.worker.run_fetch(self.code)


try:
    from add_buy_st import AddBuyStWindow
    from add_sell_st import AddSellStWindow
except ImportError as e:
    print(f"导入失败：{e}")
    print("请确保add_buy_st.py, add_sell_st.py和main.py在同一目录下")
    sys.exit(1)

LOG_CSV_FILE = "strategy_total_log.csv"
DATA_FILE = "tdx_auto.json"


def add_strategy_log(strategy_dict, event_type, extra_info=""):
    if "logs" not in strategy_dict:
        strategy_dict["logs"] = []
    log_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event_type,
        "extra": str(extra_info)
    }
    strategy_dict["logs"].append(log_entry)
    if len(strategy_dict["logs"]) > 50:
        strategy_dict["logs"].pop(0)


def save_total_log_to_csv(all_strategies):
    total_logs = []
    for st in all_strategies:
        identifier = st.get("股票代码") or st.get("文件地址", "unknown")
        st_type = "stock" if "股票代码" in st else "file"
        for log in st.get("logs", []):
            total_logs.append({
                "identifier": identifier, "type": st_type,
                "timestamp": log["timestamp"], "event": log["event"], "extra": log["extra"]
            })
    total_logs.sort(key=lambda x: x["timestamp"])
    try:
        with open(LOG_CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=["identifier", "type", "timestamp", "event", "extra"])
            writer.writeheader()
            writer.writerows(total_logs)
    except Exception as e:
        print(f"保存总日志 CSV 失败: {e}")


def load_stock_total():
    stock_file = "stock_total.txt"
    if not os.path.exists(stock_file):
        return set()
    valid_codes = set()
    encodings = ['utf-8', 'gbk', 'gb2312']
    for encoding in encodings:
        try:
            with open(stock_file, 'r', encoding=encoding) as f:
                for line in f:
                    line = line.strip()
                    if line and line.isdigit() and len(line) == 6:
                        valid_codes.add(line)
                    elif line:
                        parts = line.split(',')
                        for part in reversed(parts):
                            part = part.strip()
                            if part.isdigit() and len(part) == 6:
                                valid_codes.add(part)
                                break
                return valid_codes
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"加载 stock_total.txt 失败: {e}")
            return set()
    print("警告: 无法识别 stock_total.txt 的文件编码，请确保文件内容正确。")
    return set()


def extract_condition(s):
    if not isinstance(s, str) or not s.strip():
        return ""
    pos = s.find('%')
    if pos == -1:
        return s
    after = s[pos + 1:]
    if re.search(r'\d', after):
        return s[:pos] + after
    return s


def load_from_json():
    if not os.path.exists(DATA_FILE):
        return [], [], ""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("stock", []), data.get("file", []), data.get("last_run_date", "")
    except Exception as e:
        print(f"加载JSON失败: {e}")
        return [], [], ""


def save_to_json(stock_list, file_list, last_run_date):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "stock": stock_list,
                "file": file_list,
                "last_run_date": last_run_date
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存JSON失败: {e}")


class MainWindow(QMainWindow):
    TDX_CMD_FILE = "tdx_cmd.txt"

    def __init__(self):
        super().__init__()
        self.last_trigger_time = {}
        self._skip_restore_check_state = False
        self.thread_pool = QThreadPool()
        self.combined_worker = CombinedDataWorker()
        self.combined_worker.data_ready.connect(self.on_stock_data_received)
        self.combined_worker.data_error.connect(self.on_stock_data_error)
        self.stock_data_cache = {}
        self.last_cmd_time = 0
        self.dependency_error_shown = False
        self.fetch_code_list = []
        self.fetch_index = 0
        self.fetch_timer = QTimer(self)
        self.fetch_timer.timeout.connect(self._process_fetch_queue)
        self.fetch_timer.setInterval(2000)
        self.manual_stock_strategies = []
        self.save_file_st = []
        self.last_run_date = ""
        self.seen_file_stocks = set()
        self.current_stock_filter = None
        self.current_file_filter = None
        self.valid_stock_codes = load_stock_total()
        if not self.valid_stock_codes:
            print("警告: stock_total.txt 文件不存在或为空，将不进行代码验证")
        self.manual_stock_strategies, self.save_file_st, self.last_run_date = load_from_json()
        self._next_day_cleanup()
        self.setupUi(self)
        self.bind_events()
        self.init_tables()
        self.all_table()
        self.check_dependencies()
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.process_running_file_strategies)
        self.monitor_timer.start(5000)
        self.file_scan_timer = QTimer(self)
        self.file_scan_timer.timeout.connect(self.rebuild_temp_stocks_from_running_files)
        self.file_scan_timer.setInterval(5000)
        self.file_scan_timer.start()
        self.rebuild_temp_stocks_from_running_files()

    def _next_day_cleanup(self):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if self.last_run_date == today:
            return
        self.manual_stock_strategies = [st for st in self.manual_stock_strategies if st.get("状态") != "结束"]
        for st in self.manual_stock_strategies:
            if st.get("状态") == "运行":
                st["状态"] = "暂停"
        for st in self.save_file_st:
            if st.get("状态") == "扫描":
                st["状态"] = "停止"
        self.last_run_date = today
        save_to_json(self.manual_stock_strategies, self.save_file_st, self.last_run_date)

    def _mark_dirty_and_save(self):
        """保存内存数据到JSON文件，内存数据始终是唯一数据源"""
        save_to_json(self.manual_stock_strategies, self.save_file_st, self.last_run_date)
        all_strategies = self.manual_stock_strategies + self.save_file_st
        save_total_log_to_csv(all_strategies)

    def check_dependencies(self):
        try:
            import requests
            if not hasattr(requests, 'get'):
                raise ImportError("requests 模块结构不完整")
        except ImportError as e:
            QMessageBox.critical(self, "严重错误",
                                 f"检测到关键模块缺失或错误！\n\n错误详情: {str(e)}\n\n"
                                 f"原因分析：\n1. 缺少文件 'requests'。\n2. 打包时该文件未被包含进 EXE。\n\n"
                                 f"解决方案：\n请确保 'requests' 模块已安装，\n"
                                 f"或者联系开发者获取完整版软件包。\n\n当前软件将无法获取股票实时数据。")
            self.dependency_error_shown = True
        except Exception as e:
            QMessageBox.warning(self, "警告", f"模块加载异常: {str(e)}\n数据获取功能可能不稳定。")

    def on_stock_data_error(self, code, error_msg):
        is_missing_module = "No module named 'requests'" in str(error_msg) or "ModuleNotFoundError: No module named 'requests'" in str(error_msg)
        if is_missing_module:
            if not self.dependency_error_shown:
                self.dependency_error_shown = True
                QMessageBox.critical(self, "严重错误",
                                     f"数据获取失败：缺少关键模块！\n\n错误信息: {error_msg}\n\n"
                                     f"无法获取股票名称、现价、昨日价。请检查软件完整性。")
            else:
                print(f"[{code}] 数据获取失败(模块缺失): {error_msg}")
        else:
            print(f"[{code}] 数据获取失败: {error_msg}")
            self.statusbar.showMessage(f"[{code}] 数据获取失败: {error_msg}", 5000)

    def is_weekday(self):
        return datetime.datetime.now().weekday() < 5

    def is_trading_time(self):
        if not self.is_weekday():
            return False
        now = datetime.datetime.now().time()
        if datetime.time(9, 30) <= now <= datetime.time(11, 30):
            return True
        if datetime.time(13, 0) <= now <= datetime.time(15, 0):
            return True
        return False

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1060, 1200)
        icon = QtGui.QIcon()
        try:
            icon.addPixmap(QtGui.QPixmap("app4.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        except:
            print("未找到app4.ico图标，不影响窗口功能")
        MainWindow.setWindowIcon(icon)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        main_layout = QtWidgets.QVBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
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
        self.add_st = QtWidgets.QGroupBox(self.centralwidget)
        self.add_st.setFixedHeight(110)
        font = QtGui.QFont()
        font.setFamily("黑体")
        font.setPointSize(12)
        self.add_st.setFont(font)
        self.add_st.setObjectName("add_st")
        add_st_layout = QtWidgets.QHBoxLayout(self.add_st)
        add_st_layout.addStretch()
        self.add_buy_st = QtWidgets.QLabel(self.add_st)
        self.add_buy_st.setText("")
        try:
            self.add_buy_st.setPixmap(QtGui.QPixmap("image/buy.png"))
        except:
            self.add_buy_st.setText("买入")
        self.add_buy_st.setAlignment(Qt.AlignCenter)
        self.add_buy_st.setObjectName("add_buy_st")
        add_st_layout.addWidget(self.add_buy_st)
        self.add_kkk = QtWidgets.QLabel(self.add_st)
        self.add_kkk.setText("")
        try:
            self.add_kkk.setPixmap(QtGui.QPixmap("image/kkk.png"))
        except:
            self.add_kkk.setText("")
        self.add_kkk.setAlignment(Qt.AlignCenter)
        self.add_kkk.setObjectName("add_kkk")
        add_st_layout.addWidget(self.add_kkk)
        self.add_sell_st = QtWidgets.QLabel(self.add_st)
        self.add_sell_st.setText("")
        try:
            self.add_sell_st.setPixmap(QtGui.QPixmap("image/sell.png"))
        except:
            self.add_sell_st.setText("卖出")
        self.add_sell_st.setAlignment(Qt.AlignCenter)
        self.add_sell_st.setObjectName("add_sell_st")
        add_st_layout.addWidget(self.add_sell_st)
        self.add_kkk = QtWidgets.QLabel(self.add_st)
        self.add_kkk.setText("")
        try:
            self.add_kkk.setPixmap(QtGui.QPixmap("image/kkk.png"))
        except:
            self.add_kkk.setText("")
        self.add_kkk.setAlignment(Qt.AlignCenter)
        self.add_kkk.setObjectName("add_kkk")
        add_st_layout.addWidget(self.add_kkk)
        add_st_layout.addStretch()
        main_layout.addWidget(self.add_st)
        self.stock_tb_label = QLabel(self.centralwidget)
        self.stock_tb_label.setText("单支股票策略列表")
        self.stock_tb_label.setFont(QFont("黑体", 12))
        main_layout.addWidget(self.stock_tb_label)
        self.stock_button_widget = QWidget(self.centralwidget)
        self.stock_button_layout = QHBoxLayout()
        self.stock_button_widget.setLayout(self.stock_button_layout)
        main_layout.addWidget(self.stock_button_widget)
        self.stock_st_table = QTableWidget(self.centralwidget)
        sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(2)
        self.stock_st_table.setSizePolicy(sp)
        main_layout.addWidget(self.stock_st_table)
        self.file_tb_label = QLabel(self.centralwidget)
        self.file_tb_label.setText("文件模式策略列表")
        self.file_tb_label.setFont(QFont("黑体", 12))
        main_layout.addWidget(self.file_tb_label)
        self.file_button_widget = QWidget(self.centralwidget)
        self.file_button_layout = QHBoxLayout()
        self.file_button_widget.setLayout(self.file_button_layout)
        main_layout.addWidget(self.file_button_widget)
        self.file_st_table = QTableWidget(self.centralwidget)
        sp_file = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sp_file.setHorizontalStretch(0)
        sp_file.setVerticalStretch(2)
        self.file_st_table.setSizePolicy(sp_file)
        main_layout.addWidget(self.file_st_table)
        self.stock_select_all_btn = QPushButton("全选")
        self.stock_select_none_btn = QPushButton("反选")
        self.stock_run_btn = QPushButton("运行")
        self.stock_pause_btn = QPushButton("暂停")
        self.stock_status_filter_btn = QPushButton("状态分类")
        self.stock_direction_filter_btn = QPushButton("方向分类")
        self.stock_strategy_filter_btn = QPushButton("策略分类")
        self.stock_delete_btn = QPushButton("删除")
        self.sort_stock_btn = QPushButton("排序")
        self.sort_stock_btn.clicked.connect(self.sort_stock_strategies)
        button_style = "QPushButton {padding: 5px 10px; margin: 0 5px;}"
        for btn in [self.stock_select_all_btn, self.stock_select_none_btn, self.stock_run_btn,
                    self.stock_pause_btn, self.stock_status_filter_btn, self.stock_direction_filter_btn,
                    self.stock_strategy_filter_btn]:
            btn.setStyleSheet(button_style)
        self.stock_delete_btn.setStyleSheet(button_style + "background-color: #ff4444; color: white;")
        for btn in [self.stock_select_all_btn, self.stock_select_none_btn, self.stock_run_btn,
                    self.stock_pause_btn, self.stock_status_filter_btn, self.stock_direction_filter_btn,
                    self.stock_strategy_filter_btn, self.stock_delete_btn]:
            self.stock_button_layout.addWidget(btn)
        self.file_select_all_btn = QPushButton("全选")
        self.file_select_none_btn = QPushButton("反选")
        self.file_run_btn = QPushButton("扫描")
        self.file_pause_btn = QPushButton("停止")
        self.file_status_filter_btn = QPushButton("表2状态")
        self.file_direction_filter_btn = QPushButton("方向分类")
        self.file_strategy_filter_btn = QPushButton("策略分类")
        self.file_delete_btn = QPushButton("删除")
        for btn in [self.file_select_all_btn, self.file_select_none_btn, self.file_run_btn,
                    self.file_pause_btn, self.file_status_filter_btn, self.file_direction_filter_btn,
                    self.file_strategy_filter_btn]:
            btn.setStyleSheet(button_style)
        self.file_delete_btn.setStyleSheet(button_style + "background-color: #ff4444; color: white;")
        for btn in [self.file_select_all_btn, self.file_select_none_btn, self.file_run_btn,
                    self.file_pause_btn, self.file_status_filter_btn, self.file_direction_filter_btn,
                    self.file_strategy_filter_btn, self.file_delete_btn]:
            self.file_button_layout.addWidget(btn)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "超级股票助手"))
        self.banner.setText(_translate("MainWindow", "超级助手，助力您做股票越来越轻松！"))
        self.add_st.setTitle(_translate("MainWindow", "添加策略"))

    def init_tables(self):
        font = QtGui.QFont()
        font.setPointSize(10)
        self.stock_st_table.setFont(font)
        self.file_st_table.setFont(font)
        self.file_st_table.setColumnCount(9)
        self.file_st_table.setHorizontalHeaderLabels(
            ["选择", "表2状态", "方向", "板块简介", "文件地址", "策略分类", "价格条件", "仓位", "声音文件"])
        file_column_widths = [30, 55, 50, 150, 285, 80, 95, 40, 120]
        for col, width in enumerate(file_column_widths):
            self.file_st_table.setColumnWidth(col, width)
        self.file_st_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.stock_st_table.setColumnCount(12)
        self.stock_st_table.setHorizontalHeaderLabels(
            ["选择", "添加时间", "状态", "方向", "股票代码", "股票名称", "现价", "昨日价", "策略分类", "价格条件", "仓位", "声音文件"])
        stock_column_widths = [40, 120, 60, 60, 80, 80, 60, 60, 120, 120, 60, 120]
        for col, width in enumerate(stock_column_widths):
            self.stock_st_table.setColumnWidth(col, width)
        self.stock_st_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

    def bind_events(self):
        self.add_buy_st.setCursor(QCursor(Qt.PointingHandCursor))
        self.add_buy_st.installEventFilter(self)
        self.add_sell_st.setCursor(QCursor(Qt.PointingHandCursor))
        self.add_sell_st.installEventFilter(self)
        self.stock_select_all_btn.clicked.connect(lambda: self.select_all(self.stock_st_table))
        self.stock_select_none_btn.clicked.connect(lambda: self.select_inverse(self.stock_st_table))
        self.stock_run_btn.clicked.connect(lambda: self.set_status(self.stock_st_table, "运行"))
        self.stock_pause_btn.clicked.connect(lambda: self.set_status(self.stock_st_table, "暂停"))
        self.stock_status_filter_btn.clicked.connect(lambda: self.filter_by_status(self.stock_st_table))
        self.stock_direction_filter_btn.clicked.connect(lambda: self.filter_by_direction(self.stock_st_table))
        self.stock_strategy_filter_btn.clicked.connect(lambda: self.filter_by_strategy(self.stock_st_table))
        self.stock_delete_btn.clicked.connect(lambda: self.delete_selected(self.stock_st_table))
        self.file_select_all_btn.clicked.connect(lambda: self.select_all(self.file_st_table))
        self.file_select_none_btn.clicked.connect(lambda: self.select_inverse(self.file_st_table))
        self.file_run_btn.clicked.connect(lambda: self.set_status(self.file_st_table, "扫描"))
        self.file_pause_btn.clicked.connect(lambda: self.set_status(self.file_st_table, "停止"))
        self.file_status_filter_btn.clicked.connect(lambda: self.filter_by_status(self.file_st_table))
        self.file_direction_filter_btn.clicked.connect(lambda: self.filter_by_direction(self.file_st_table))
        self.file_strategy_filter_btn.clicked.connect(lambda: self.filter_by_strategy(self.file_st_table))
        self.file_delete_btn.clicked.connect(lambda: self.delete_selected(self.file_st_table))
        self.stock_st_table.cellClicked.connect(self.on_stock_table_cell_clicked)
        self.stock_st_table.cellDoubleClicked.connect(self.show_stock_log)
        self.file_st_table.cellDoubleClicked.connect(self.show_file_log)

    def on_stock_table_cell_clicked(self, row, col):
        if col != 4:
            return
        item = self.stock_st_table.item(row, col)
        if not item:
            return
        code = item.text().strip()
        if code and code.isdigit() and len(code) == 6:
            link_tdx(code)

    def eventFilter(self, obj, event):
        if obj == self.add_buy_st and event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.open_add_buy_st()
            return True
        elif obj == self.add_sell_st and event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.open_add_sell_st()
            return True
        return super().eventFilter(obj, event)

    def open_add_buy_st(self):
        try:
            self.add_buy_window = AddBuyStWindow(self)
            self.add_buy_window.st_saved.connect(self.update_st_tables)
            parent_geometry = self.geometry()
            child_geometry = self.add_buy_window.frameGeometry()
            x = parent_geometry.x() + (parent_geometry.width() - child_geometry.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - child_geometry.height()) // 2
            self.add_buy_window.move(x, y)
            self.add_buy_window.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开买入策略窗口失败：{str(e)}")

    def open_add_sell_st(self):
        try:
            self.add_sell_window = AddSellStWindow(self)
            self.add_sell_window.st_saved.connect(self.update_st_tables)
            parent_geometry = self.geometry()
            child_geometry = self.add_sell_window.frameGeometry()
            x = parent_geometry.x() + (parent_geometry.width() - child_geometry.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - child_geometry.height()) // 2
            self.add_sell_window.move(x, y)
            self.add_sell_window.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开卖出策略窗口失败：{str(e)}")

    def update_st_tables(self, stock_strategies, file_strategies):
        if stock_strategies:
            valid_stocks = []
            for st in stock_strategies:
                stock_code = st.get("股票代码", "")
                if stock_code and self.valid_stock_codes:
                    if stock_code not in self.valid_stock_codes:
                        QMessageBox.warning(self, "无效股票代码",
                                            f"股票代码 '{stock_code}' 不在 stock_total.txt 中！\n该代码不存在，无法添加。")
                        continue
                st_type = st.get("策略分类", "")
                price_cond = st.get("价格条件", "")
                if not self._is_price_condition_valid(st_type, price_cond):
                    QMessageBox.warning(self, "无效数据",
                                        f"股票策略：\n策略分类为'{st_type}'时，价格条件'{price_cond}'无效（必须包含数字）。\n添加不成功。")
                    continue
                if "添加时间" not in st:
                    st["添加时间"] = datetime.datetime.now().strftime("%H:%M:%S")
                add_strategy_log(st, "新建")
                valid_stocks.append(st)
            if valid_stocks:
                self.merge_into_stock_strategies(valid_stocks)
                self._mark_dirty_and_save()
                self.all_table()
        if file_strategies:
            valid_files = []
            for st in file_strategies:
                st_type = st.get("策略分类", "")
                price_cond = st.get("价格条件", "")
                if not self._is_price_condition_valid(st_type, price_cond):
                    QMessageBox.warning(self, "无效数据",
                                        f"文件策略：\n策略分类为'{st_type}'时，价格条件'{price_cond}'无效（必须包含数字）。\n添加不成功。")
                    continue
                if self._is_duplicate_file_strategy(st):
                    dup_info = (f"方向: {st.get('方向')}\n"
                                f"文件: {st.get('文件地址')}\n"
                                f"策略: {st.get('策略分类')}")
                    QMessageBox.information(self, "重复数据",
                                            f'该策略已存在于表2（状态为"扫描"或"停止"）：\n{dup_info}\n将跳过添加。')
                    continue
                add_strategy_log(st, "新建")
                valid_files.append(st)
            if valid_files:
                self.save_file_st.extend(valid_files)
                self._mark_dirty_and_save()
                self.all_table()

    def all_table(self):
        self.stock_tb()
        self.file_tb()

    def _get_strategy_key(self, st):
        fields = ["股票代码", "方向", "策略分类", "价格条件", "仓位"]
        key_parts = [str(st.get(f, "")) for f in fields]
        return "|".join(key_parts)

    def file_tb(self):
        display_strategies = self.save_file_st.copy()
        if self.current_file_filter:
            filter_type, filter_value = self.current_file_filter
            if filter_type == "status":
                if filter_value != "全部状态":
                    display_strategies = [st for st in display_strategies if st.get("状态", "停止") == filter_value]
            elif filter_type == "direction":
                if filter_value != "全部方向":
                    display_strategies = [st for st in display_strategies if st.get("方向", "买入") == filter_value]
            elif filter_type == "strategy":
                if filter_value != "全部策略":
                    display_strategies = [st for st in display_strategies if st.get("策略分类", "") == filter_value]
        self.file_st_table.setRowCount(len(display_strategies))
        for row, st in enumerate(display_strategies):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            check_item.setTextAlignment(Qt.AlignCenter)
            self.file_st_table.setItem(row, 0, check_item)
            status = st.get("状态", "停止")
            item1 = QTableWidgetItem(status)
            item1.setTextAlignment(Qt.AlignCenter)
            font = QFont(); font.setBold(True); font.setPointSize(10)
            item1.setFont(font)
            item1.setForeground(QColor("#00AA00") if status == "扫描" else QColor("#888888"))
            item1.setFlags(item1.flags() & ~Qt.ItemIsEditable)
            self.file_st_table.setItem(row, 1, item1)
            item2 = QTableWidgetItem(st.get("方向", "买入"))
            item2.setTextAlignment(Qt.AlignCenter)
            item2.setFlags(item2.flags() & ~Qt.ItemIsEditable)
            self.file_st_table.setItem(row, 2, item2)
            item3 = QTableWidgetItem(st.get("板块简介", ""))
            item3.setTextAlignment(Qt.AlignCenter)
            item3.setFlags(item3.flags() & ~Qt.ItemIsEditable)
            self.file_st_table.setItem(row, 3, item3)
            fields = ["文件地址", "策略分类", "价格条件", "仓位", "声音文件"]
            for col_offset, field in enumerate(fields, start=4):
                raw_value = st.get(field, "")
                display_value = extract_condition(raw_value) if field == "价格条件" else raw_value
                item = QTableWidgetItem(display_value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.file_st_table.setItem(row, col_offset, item)

    def rebuild_temp_stocks_from_running_files(self):
        new_temp_stocks = []
        files_to_clear = set()
        for row_idx, file_st in enumerate(self.save_file_st):
            if file_st.get("状态") != "扫描":
                continue
            file_path = file_st.get("文件地址", "").strip()
            if not file_path or not os.path.isfile(file_path):
                continue
            found_new = False
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
            except Exception as e:
                print(f"读取文件失败 {file_path}: {e}")
                continue
            for line_num, line in enumerate(lines):
                line = line.strip()
                if len(line) < 6:
                    continue
                stock_code = line[-6:]
                if not stock_code.isdigit():
                    continue
                unique_key = (stock_code, file_path)
                if unique_key in self.seen_file_stocks:
                    continue
                self.seen_file_stocks.add(unique_key)
                found_new = True
                price_cond = file_st.get("价格条件", "")
                st_type = file_st.get("策略分类", "")
                if not self._is_price_condition_valid(st_type, price_cond):
                    print(f"[扫描跳过] 文件: {os.path.basename(file_path)}, 代码: {stock_code}, 策略: {st_type}, 价格条件无效")
                    continue
                stock_st = {
                    "状态": "运行", "方向": file_st.get("方向", "买入"),
                    "股票代码": stock_code, "股票名称": "--", "现价": "--", "昨日价": "--",
                    "策略分类": st_type, "价格条件": price_cond, "仓位": file_st.get("仓位", ""),
                    "声音文件": file_st.get("声音文件", ""), "来源": "file_import",
                    "_source_file_path": file_path, "_line_number": line_num,
                    "添加时间": datetime.datetime.now().strftime("%H:%M:%S")
                }
                new_temp_stocks.append(stock_st)
            if found_new:
                files_to_clear.add(file_path)
        all_current_file_paths = {st.get("文件地址", "") for st in self.save_file_st if st.get("状态") == "扫描"}
        self.seen_file_stocks = {(code, path) for (code, path) in self.seen_file_stocks
                                 if path in all_current_file_paths and os.path.isfile(path)}
        for fp in files_to_clear:
            try:
                with open(fp, 'w', encoding='utf-8') as f:
                    pass
                self.seen_file_stocks = {(c, p) for (c, p) in self.seen_file_stocks if p != fp}
                print(f"[文件扫描] 已读取新数据并清空: {fp}")
            except Exception as e:
                print(f"清空文件失败 {fp}: {e}")
        if new_temp_stocks:
            self.merge_into_stock_strategies(new_temp_stocks)
            self._mark_dirty_and_save()
            self.stock_tb()

    def merge_into_stock_strategies(self, new_strategies: list):
        skipped_list = []
        to_add = []
        active_strategies = [st for st in self.manual_stock_strategies if st.get("状态") in ("运行", "暂停")]
        ended_by_code = {}
        remaining_manual = []
        for st in self.manual_stock_strategies:
            code = st.get("股票代码", "")
            if st.get("状态") == "结束":
                ended_by_code.setdefault(code, []).append(st)
            else:
                remaining_manual.append(st)
        for new_st in new_strategies:
            stock_code = new_st.get("股票代码", "")
            is_duplicate = False
            for active in active_strategies:
                if self._is_same_strategy(new_st, active):
                    is_duplicate = True
                    skipped_list.append(stock_code)
                    break
            if is_duplicate:
                continue
            if new_st.get("状态") == "结束":
                ended_by_code.setdefault(stock_code, []).append(new_st)
            else:
                to_add.append(new_st)
        cleaned_ended = []
        for code, ended_list in ended_by_code.items():
            def get_last_log_time(st):
                logs = st.get("logs", [])
                if logs:
                    try:
                        return datetime.datetime.strptime(logs[-1]["timestamp"], "%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                return datetime.datetime.now()
            ended_list.sort(key=get_last_log_time, reverse=True)
            kept = ended_list[:3]
            cleaned_ended.extend(kept)
            if len(ended_list) > 3:
                discarded = ended_list[3:]
                for d in discarded:
                    add_strategy_log(d, "自动清理", "超过3条结束策略，被移除")
        self.manual_stock_strategies = remaining_manual + to_add + cleaned_ended
        if skipped_list:
            unique_skipped = list(set(skipped_list))
            msg = "以下股票因存在运行/暂停中的相同策略，已跳过添加：\n" + "\n".join(unique_skipped)
            QMessageBox.information(self, "重复策略跳过", msg)

    def stock_tb(self):
        table = self.stock_st_table
        current_check_states = {}
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                current_check_states[row] = item.checkState()
        display_strategies = self._get_displayed_stock_strategies()
        self.fetch_stock_data_async(display_strategies)
        table.setRowCount(len(display_strategies))
        self._last_stock_strategies_for_check = display_strategies
        fields = ["方向", "股票代码", "股票名称", "现价", "昨日价", "策略分类", "价格条件", "仓位", "声音文件"]
        for row, st in enumerate(display_strategies):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setTextAlignment(Qt.AlignCenter)
            if row in current_check_states:
                check_item.setCheckState(current_check_states[row])
            else:
                check_item.setCheckState(Qt.Unchecked)
            table.setItem(row, 0, check_item)
            raw_add_time = st.get("添加时间")
            if not raw_add_time:
                logs = st.get("logs", [])
                if logs:
                    raw_add_time = logs[0].get("timestamp", "--")
                else:
                    raw_add_time = "--"
            if raw_add_time and raw_add_time != "--":
                str_time = str(raw_add_time)
                if " " in str_time:
                    display_time = str_time.split(" ")[-1]
                else:
                    display_time = str_time
            else:
                display_time = "--"
            time_item = QTableWidgetItem(display_time)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 1, time_item)
            status = st.get("状态", "暂停")
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            status_item.setFont(font)
            if status == "运行":
                status_item.setForeground(QColor("#00AA00"))
            elif status == "暂停":
                status_item.setForeground(QColor("#FF0000"))
            else:
                status_item.setForeground(QColor("#888888"))
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 2, status_item)
            code = st.get("股票代码")
            cached = self.stock_data_cache.get(code, {})
            display_name = cached.get('name', "--")
            display_price = f"{cached.get('price', 0):.2f}" if 'price' in cached else "--"
            display_prev = f"{cached.get('prev_close', 0):.2f}" if 'prev_close' in cached else "--"
            for col_offset, field in enumerate(fields, start=3):
                raw_value = ""
                if field == "股票名称":
                    raw_value = display_name
                elif field == "现价":
                    raw_value = display_price
                elif field == "昨日价":
                    raw_value = display_prev
                else:
                    raw_value = st.get(field, "")
                if field in ("价格条件",):
                    display_value = extract_condition(raw_value)
                else:
                    display_value = str(raw_value) if raw_value != "" else "--"
                item = QTableWidgetItem(display_value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col_offset, item)

    def _is_price_condition_valid(self, st_type, price_cond):
        if st_type in ["按股价", "按涨幅"]:
            if not price_cond or not re.search(r'\d', str(price_cond)):
                return False
        return True

    def _is_duplicate_file_strategy(self, new_st):
        existing_strategies = [s for s in self.save_file_st if s.get("状态") in ["扫描", "停止"]]
        for st in existing_strategies:
            if (st.get("方向") == new_st.get("方向")
                    and st.get("文件地址") == new_st.get("文件地址")
                    and st.get("策略分类") == new_st.get("策略分类")
                    and st.get("价格条件") == new_st.get("价格条件")
                    and st.get("仓位") == new_st.get("仓位")
                    and st.get("声音文件") == new_st.get("声音文件")):
                return True
        return False

    def fetch_stock_data_async(self, display_strategies):
        existing_set = set(self.fetch_code_list)
        new_codes = []
        running = [s for s in display_strategies if s.get("状态") == "运行"]
        for st in running:
            code = st.get("股票代码", "").strip()
            if code and code.isdigit() and code not in existing_set:
                new_codes.append(code)
        if new_codes:
            self.fetch_code_list = new_codes + [c for c in self.fetch_code_list if c not in set(new_codes)]
            self.fetch_index = 0
        if self.fetch_code_list and not self.fetch_timer.isActive():
            self.fetch_timer.start()

    def _process_fetch_queue(self):
        if not self.fetch_code_list:
            self.fetch_timer.stop()
            return
        code = self.fetch_code_list[self.fetch_index]
        self.fetch_index = (self.fetch_index + 1) % len(self.fetch_code_list)
        task = CombinedFetchRunnable(self.combined_worker, code)
        self.thread_pool.start(task)

    def on_stock_data_received(self, code, data):
        if not data:
            return
        if code not in self.stock_data_cache:
            self.stock_data_cache[code] = {}
        cache = self.stock_data_cache[code]
        current_timestamp = time.time()
        if 'name' in data:
            cache['name'] = data['name']
        if 'price' in data:
            cache['price'] = data['price']
        if 'prev_close' in data:
            cache['prev_close'] = data['prev_close']
        cache['last_full_fetch_time'] = current_timestamp
        display_strategies = self._get_displayed_stock_strategies()
        table = self.stock_st_table
        for row, st in enumerate(display_strategies):
            if st.get("股票代码") == code and row < table.rowCount():
                if 'name' in data:
                    name = data['name']
                    st["股票名称"] = name
                    item = table.item(row, 5)
                    if item:
                        item.setText(name)
                if 'prev_close' in data:
                    prev = data['prev_close']
                    st["昨日价"] = f"{prev:.2f}" if isinstance(prev, (int, float)) else "--"
                    item = table.item(row, 7)
                    if item:
                        item.setText(st["昨日价"])
                if 'price' in data:
                    price = data['price']
                    st["现价"] = f"{price:.2f}" if isinstance(price, (int, float)) else "--"
                    item = table.item(row, 6)
                    if item:
                        item.setText(st["现价"])
        QTimer.singleShot(500, lambda c=code: self._delayed_trigger_check(c))

    def _delayed_trigger_check(self, code):
        display_strategies = self._get_displayed_stock_strategies()
        cached = self.stock_data_cache.get(code, {})
        price = cached.get('price')
        prev_price = cached.get('prev_close')
        if not isinstance(price, (int, float)) or not isinstance(prev_price, (int, float)):
            return
        for st in display_strategies:
            if st.get("股票代码") == code:
                if st.get("状态") == "结束":
                    continue
                if st.get("状态") != "运行":
                    continue
                if self.check_trigger_condition(st, price, prev_price):
                    key = self._get_strategy_key(st)
                    now_time = time.time()
                    if key not in self.last_trigger_time or now_time - self.last_trigger_time[key] >= 300:
                        self._handle_trigger(st)
                        self.last_trigger_time[key] = now_time

    def _schedule_voice(self, sound_file, remain_times, interval_ms):
        if remain_times <= 0:
            return
        if os.path.isfile(sound_file):
            winsound.PlaySound(sound_file, winsound.SND_ASYNC)
        else:
            winsound.Beep(1000, 300)
        next_count = remain_times - 1
        QTimer.singleShot(interval_ms, lambda f=sound_file, c=next_count: self._schedule_voice(f, c, interval_ms))

    def _eval_op(self, op, val, target):
        if op == '>=': return val >= target
        if op == '<=': return val <= target
        if op == '>':  return val > target
        if op == '<':  return val < target
        if op == '==': return abs(val - target) < 1e-5
        if op == '!=': return abs(val - target) >= 1e-5
        return False

    def check_trigger_condition(self, st, current_price, yesterday_price):
        st_type = st.get("策略分类", "")
        price_cond_str = st.get("价格条件", "").strip()
        if st_type in ["通达信预警", "立即交易"]:
            return True
        if st_type in ["按股价", "按涨幅"]:
            try:
                curr = float(current_price)
                prev = float(yesterday_price)
            except (ValueError, TypeError):
                return False
            if st_type == "按涨幅":
                try:
                    prev = float(yesterday_price)
                    if prev == 0:
                        return False
                except (ValueError, TypeError):
                    return False
            else:
                try:
                    prev = float(yesterday_price)
                except:
                    pass
            match = re.match(r'^([<>=!]+)\s*([+-]?\d*\.?\d+)\s*(%?)$', price_cond_str)
            if not match:
                return False
            op = match.group(1)
            val = float(match.group(2))
            if st_type == "按股价":
                return self._eval_op(op, curr, val)
            elif st_type == "按涨幅":
                change_pct = (curr - prev) / prev * 100
                return self._eval_op(op, change_pct, val)
            return False
        return False

    def _update_table_status_cell(self, st):
        """在表格中找到策略对应的行，立即更新状态列显示"""
        code = st.get("股票代码", "")
        status = st.get("状态", "")
        table = self.stock_st_table
        display_strategies = self._get_displayed_stock_strategies()
        for row, ds in enumerate(display_strategies):
            if ds is st and row < table.rowCount():
                status_item = table.item(row, 2)
                if status_item:
                    status_item.setText(status)
                    font = QFont()
                    font.setBold(True)
                    font.setPointSize(10)
                    status_item.setFont(font)
                    if status == "运行":
                        status_item.setForeground(QColor("#00AA00"))
                    elif status == "暂停":
                        status_item.setForeground(QColor("#FF0000"))
                    else:
                        status_item.setForeground(QColor("#888888"))
                break

    def _handle_trigger(self, st):
        add_strategy_log(st, "触发条件满足", "检测到满足交易条件")
        sound_file = st.get("声音文件", "")
        sound_played = False
        if sound_file:
            if not os.path.isabs(sound_file) and not sound_file.startswith("sounds"):
                sound_path = os.path.join("sounds", sound_file)
            else:
                sound_path = sound_file
            if os.path.exists(sound_path):
                try:
                    self._schedule_voice(sound_path, 3, 1000)
                    sound_played = True
                except Exception as e:
                    print(f"播放声音出错: {e}")
            else:
                print(f"声音文件未找到: {sound_path}")
        if not sound_played:
            try:
                winsound.Beep(1000, 300)
            except Exception:
                pass
        position = st.get("仓位", "")
        direction = st.get("方向", "--")
        stock_code = st.get("股票代码", "--")
        if position and position not in ["全仓", "自设量", "不交易"] and "仓" not in position:
            position = position + "仓"
        if position == "不交易":
            add_strategy_log(st, "触发不交易", f"仓位为'不交易'，仅播放声音，未发送交易指令。")
            st["状态"] = "结束"
            self._mark_dirty_and_save()
            self._update_table_status_cell(st)
            return
        cmd_map = {
            ("买入", "全仓"): "cmd_f9_f1", ("买入", "1/2仓"): "cmd_f9_f2",
            ("买入", "1/3仓"): "cmd_f9_f3", ("买入", "1/4仓"): "cmd_f9_f4",
            ("买入", "自设量"): "cmd_f9_enter", ("买入", "不交易"): "",
            ("卖出", "全仓"): "cmd_f10_f1", ("卖出", "1/2仓"): "cmd_f10_f2",
            ("卖出", "1/3仓"): "cmd_f10_f3", ("卖出", "1/4仓"): "cmd_f10_f4",
            ("卖出", "自设量"): "cmd_f10_enter", ("卖出", "不交易"): "",
        }
        key = (direction, position)
        cmd = cmd_map.get(key)
        add_strategy_log(st, "发送指令成功", extra_info=f" {direction} {position}")
        if not cmd:
            print(f"[触发失败] 无法识别的操作类型: 方向={direction}, 仓位={position}")
            add_strategy_log(st, "发送指令失败", f"未知操作类型: {direction} {position}")
            st["状态"] = "结束"
            self._mark_dirty_and_save()
            self._update_table_status_cell(st)
            return
        now = time.time()
        if now - self.last_cmd_time < 8:
            wait_time = 8 - (now - self.last_cmd_time)
            add_strategy_log(st, "排队等待", f"距离上次指令不足8秒，等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
        try:
            file_content = f"CODE:{stock_code}\nCMD:{cmd}\n"
            with open(TDX_CMD_FILE, 'w', encoding='utf-8') as f:
                f.write(file_content)
            print(f"[发送指令] {cmd} -> {stock_code}")
            add_strategy_log(st, "指令已发送", f"发送至TDX小助手: {cmd} 代码:{stock_code}")
            self.last_cmd_time = time.time()
            link_tdx(stock_code)
        except Exception as e:
            print(f"写入指令文件失败: {e}")
            add_strategy_log(st, "发送指令失败", f"写入文件异常: {e}")
            self.last_cmd_time = time.time()
        st["状态"] = "结束"
        self._mark_dirty_and_save()
        self._update_table_status_cell(st)

    def process_running_file_strategies(self):
        self.rebuild_temp_stocks_from_running_files()

    def select_all(self, table):
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def select_inverse(self, table):
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)

    def set_status(self, table, status):
        if table == self.stock_st_table:
            rows_to_update = []
            for i in range(table.rowCount()):
                item = table.item(i, 0)
                if item and item.flags() & Qt.ItemIsUserCheckable and item.checkState() == Qt.Checked:
                    rows_to_update.append(i)
            if not rows_to_update:
                QMessageBox.warning(self, "提示", "请先勾选要操作的策略行！")
                return
            display_strategies = self._get_displayed_stock_strategies()
            strategies_to_update = []
            for row in rows_to_update:
                if row < len(display_strategies):
                    strategies_to_update.append(display_strategies[row])
            for target_st in strategies_to_update:
                for st in self.manual_stock_strategies:
                    if self._is_same_strategy(st, target_st):
                        old_status = st.get("状态", "暂停")
                        st["状态"] = status
                        add_strategy_log(st, "状态变更", f"{old_status} -> {status}")
                        if status == "运行":
                            st_type = st.get("策略分类", "")
                            if st_type in ["通达信预警", "立即交易"]:
                                QTimer.singleShot(100, lambda s=st: self._execute_immediate_trigger(s))
                        break
            self._mark_dirty_and_save()
            self._skip_restore_check_state = True
            self.stock_tb()
            self._skip_restore_check_state = False
        elif table == self.file_st_table:
            rows_to_update = []
            for i in range(table.rowCount()):
                item = table.item(i, 0)
                if item and item.flags() & Qt.ItemIsUserCheckable and item.checkState() == Qt.Checked:
                    rows_to_update.append(i)
            if not rows_to_update:
                QMessageBox.warning(self, "提示", "请先勾选要操作的策略行！")
                return
            display_strategies = self.save_file_st.copy()
            if self.current_file_filter:
                filter_type, filter_value = self.current_file_filter
                if filter_type == "status" and filter_value != "全部状态":
                    display_strategies = [st for st in display_strategies if st.get("状态", "停止") == filter_value]
                elif filter_type == "direction" and filter_value != "全部方向":
                    display_strategies = [st for st in display_strategies if st.get("方向", "买入") == filter_value]
                elif filter_type == "strategy" and filter_value != "全部策略":
                    display_strategies = [st for st in display_strategies if st.get("策略分类", "") == filter_value]
            for row in rows_to_update:
                if row < len(display_strategies):
                    st = display_strategies[row]
                    old_status = st.get("状态", "停止")
                    st["状态"] = status
                    add_strategy_log(st, "状态变更", f"{old_status} -> {status}")
            self._mark_dirty_and_save()
            self.file_tb()

    def _execute_immediate_trigger(self, st):
        if st.get("状态") != "运行":
            return
        key = self._get_strategy_key(st)
        now_time = time.time()
        if key not in self.last_trigger_time or now_time - self.last_trigger_time[key] >= 300:
            if self.check_trigger_condition(st, None, None):
                self._handle_trigger(st)
                self.last_trigger_time[key] = now_time

    def _get_displayed_stock_strategies(self):
        all_stocks = self.manual_stock_strategies
        if self.current_stock_filter:
            filter_type, filter_value = self.current_stock_filter
            if filter_type == "status" and filter_value != "全部状态":
                all_stocks = [st for st in all_stocks if st.get("状态", "暂停") == filter_value]
            elif filter_type == "direction" and filter_value != "全部方向":
                all_stocks = [st for st in all_stocks if st.get("方向", "买入") == filter_value]
            elif filter_type == "strategy" and filter_value != "全部策略":
                all_stocks = [st for st in all_stocks if st.get("策略分类", "") == filter_value]

        def get_add_time(x):
            t = x.get("添加时间")
            if t:
                return t
            logs = x.get("logs", [])
            if logs:
                return logs[0].get("timestamp", "00:00:00")
            return "00:00:00"

        all_stocks.sort(key=lambda x: get_add_time(x), reverse=True)
        return all_stocks

    def filter_by_status(self, table):
        if table == self.stock_st_table:
            status_list = ["全部状态", "运行", "暂停", "结束"]
            selected_status, ok = QInputDialog.getItem(self, "选择状态", "请选择要显示的个股状态:", status_list, 0, False)
            if not ok:
                return
            self.current_stock_filter = ("status", selected_status)
            self.stock_tb()
        elif table == self.file_st_table:
            status_list = ["全部状态", "扫描", "停止"]
            selected_status, ok = QInputDialog.getItem(self, "选择状态", "请选择要显示文件表格的状态:", status_list, 0, False)
            if not ok:
                return
            self.current_file_filter = ("status", selected_status)
            self.file_tb()

    def filter_by_direction(self, table):
        if table == self.stock_st_table:
            direction_list = ["全部方向", "买入", "卖出"]
            selected_direction, ok = QInputDialog.getItem(self, "选择方向", "请选择要显示的个股买卖方向:", direction_list, 0, False)
            if not ok:
                return
            self.current_stock_filter = ("direction", selected_direction)
            self.stock_tb()
        elif table == self.file_st_table:
            direction_list = ["全部方向", "买入", "卖出"]
            selected_direction, ok = QInputDialog.getItem(self, "选择方向", "请选择要显示的文件表格买卖方向:", direction_list, 0, False)
            if not ok:
                return
            self.current_file_filter = ("direction", selected_direction)
            self.file_tb()

    def filter_by_strategy(self, table):
        if table == self.stock_st_table:
            strategy_list = ["全部策略", "按股价", "按涨幅", "立即交易", "通达信预警"]
            selected_strategy, ok = QInputDialog.getItem(self, "选择策略", "请选择要显示的个股策略:", strategy_list, 0, False)
            if not ok:
                return
            self.current_stock_filter = ("strategy", selected_strategy)
            self.stock_tb()
        elif table == self.file_st_table:
            strategy_list = ["全部策略", "按涨幅", "立即交易", "通达信预警"]
            selected_strategy, ok = QInputDialog.getItem(self, "选择策略", "请选择要显示的文件表格策略:", strategy_list, 0, False)
            if not ok:
                return
            self.current_file_filter = ("strategy", selected_strategy)
            self.file_tb()

    def delete_selected(self, table):
        if table == self.stock_st_table:
            rows_to_delete = []
            for i in range(table.rowCount()):
                item = table.item(i, 0)
                if item and item.checkState() == Qt.Checked:
                    rows_to_delete.append(i)
            if not rows_to_delete:
                QMessageBox.warning(self, "提示", "请先勾选要删除的策略行！")
                return
            reply = QMessageBox.question(self, "确认删除", "确定要删除选中的策略吗？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            displayed_strategies = self._get_displayed_stock_strategies()
            strategies_to_delete = []
            for row in rows_to_delete:
                if row < len(displayed_strategies):
                    strategies_to_delete.append(displayed_strategies[row])
            for st_to_delete in strategies_to_delete:
                for i in range(len(self.manual_stock_strategies) - 1, -1, -1):
                    if self._is_same_strategy(self.manual_stock_strategies[i], st_to_delete):
                        add_strategy_log(self.manual_stock_strategies[i], "删除")
                        del self.manual_stock_strategies[i]
                        break
            self._mark_dirty_and_save()
            self._skip_restore_check_state = True
            self.stock_tb()
            self._skip_restore_check_state = False
        elif table == self.file_st_table:
            rows_to_delete = []
            for i in range(table.rowCount()):
                item = table.item(i, 0)
                if item and item.checkState() == Qt.Checked:
                    rows_to_delete.append(i)
            if not rows_to_delete:
                QMessageBox.warning(self, "提示", "请先勾选要删除的策略行！")
                return
            reply = QMessageBox.question(self, "确认删除", "确定要删除选中的策略吗？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            display_strategies = self.save_file_st.copy()
            if self.current_file_filter:
                filter_type, filter_value = self.current_file_filter
                if filter_type == "status" and filter_value != "全部状态":
                    display_strategies = [st for st in display_strategies if st.get("状态", "停止") == filter_value]
                elif filter_type == "direction" and filter_value != "全部方向":
                    display_strategies = [st for st in display_strategies if st.get("方向", "买入") == filter_value]
                elif filter_type == "strategy" and filter_value != "全部策略":
                    display_strategies = [st for st in display_strategies if st.get("策略分类", "") == filter_value]
            strategies_to_delete = []
            for row in sorted(rows_to_delete, reverse=True):
                if row < len(display_strategies):
                    strategies_to_delete.append(display_strategies[row])
            for st_to_delete in strategies_to_delete:
                for i, st in enumerate(self.save_file_st):
                    if self._is_same_strategy(st, st_to_delete):
                        add_strategy_log(st, "删除")
                        del self.save_file_st[i]
                        break
            self._mark_dirty_and_save()
            self.file_tb()

    def sort_stock_strategies(self):
        self._skip_restore_check_state = True
        self.stock_tb()
        self._skip_restore_check_state = False

    def _is_same_strategy(self, st1, st2):
        keys_to_compare = ["股票代码", "方向", "策略分类", "价格条件", "仓位", "文件地址"]
        for key in keys_to_compare:
            if key in st1 and key in st2:
                if st1[key] != st2[key]:
                    return False
            elif (key in st1) != (key in st2):
                return False
        return True

    def show_stock_log(self, row, col):
        all_stocks = self._get_displayed_stock_strategies()
        if row < len(all_stocks):
            strategy = all_stocks[row]
            self._show_log_window(strategy)

    def show_file_log(self, row, col):
        display_strategies = self.save_file_st.copy()
        if self.current_file_filter:
            filter_type, filter_value = self.current_file_filter
            if filter_type == "status" and filter_value != "全部状态":
                display_strategies = [st for st in display_strategies if st.get("状态", "停止") == filter_value]
            elif filter_type == "direction" and filter_value != "全部方向":
                display_strategies = [st for st in display_strategies if st.get("方向", "买入") == filter_value]
            elif filter_type == "strategy" and filter_value != "全部策略":
                display_strategies = [st for st in display_strategies if st.get("策略分类", "") == filter_value]
        if row < len(display_strategies):
            strategy = display_strategies[row]
            self._show_log_window(strategy)

    def _show_log_window(self, strategy):
        log_viewer = LogViewerWindow(strategy, self)
        log_viewer.exec_()

    def show_menu_info(self, title, content):
        QMessageBox.information(self, title, content, QMessageBox.Ok)


class LogViewerWindow(QDialog):
    def __init__(self, strategy, parent=None):
        super().__init__(parent)
        self.setWindowTitle("策略日志详情")
        self.resize(600, 400)
        layout = QVBoxLayout()
        identifier = strategy.get("股票代码") or strategy.get("文件地址", "未知策略")
        st_type = "股票" if "股票代码" in strategy else "文件"
        title_label = QLabel(f"<h3>【{st_type}】{identifier}</h3>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(["时间", "事件", "详情"])
        self.log_table.horizontalHeader().setStretchLastSection(True)
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        logs = strategy.get("logs", [])
        self.log_table.setRowCount(len(logs))
        for i, log in enumerate(reversed(logs)):
            self.log_table.setItem(i, 0, QTableWidgetItem(log.get("timestamp", "")))
            self.log_table.setItem(i, 1, QTableWidgetItem(log.get("event", "")))
            self.log_table.setItem(i, 2, QTableWidgetItem(log.get("extra", "")))
        layout.addWidget(self.log_table)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
