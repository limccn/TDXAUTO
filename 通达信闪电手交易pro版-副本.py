# -*- coding: utf-8 -*-
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys
import ctypes
from ctypes import wintypes
import win32gui
import win32api
import win32con
import win32process
import threading
import pyautogui
import tdx_soft
import base64

# 读取.ico文件，转为base64编码
# with open("app1.ico", "rb") as f:
#     ico_base64 = base64.b64encode(f.read()).decode("utf-8")

# 自动安装 pywinauto（可选）
try:
    from pywinauto import Application
except ImportError:
    print("正在安装依赖库 pywinauto...")
    os.system(f"{sys.executable} -m pip install pywinauto")
    from pywinauto import Application


def get_from_setup():
    """从setup.txt文件中读取TDX路径"""
    setup_file = "setup.txt"
    if os.path.exists(setup_file):
        with open(setup_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("TDX_EXE_PATH="):


                    return line.split("=", 1)[1].strip()


TDX_EXE_PATH = f'{get_from_setup}TdxW.exe'
WINDOW_TITLE_KEYWORD = "通达信"  # 用于匹配窗口标题


def is_tdx_running():
    """检查通达信是否在运行，返回 (bool, pid 或 None)"""
    try:
        pids = []
        for w in findwindows.find_elements():
            if w.process_id and w.visible and WINDOW_TITLE_KEYWORD in (w.name or ""):
                pids.append(w.process_id)
        if pids:
            return True, pids[0]
        return False, None
    except Exception:
        return False, None


def start_tdx_if_needed():
    """如果未运行，则启动通达信并等待窗口出现"""
    running, pid = is_tdx_running()
    if not running:
        print("启动通达信...")
        subprocess.Popen(TDX_EXE_PATH)
        time.sleep(6)  # 等待启动
        for _ in range(10):
            running, pid = is_tdx_running()
            if running:
                break
            time.sleep(1)
        else:
            raise RuntimeError("通达信启动超时，请检查路径或手动启动。")
    return pid


class TDXAutomation:
    def __init__(self):
        self.app = None
        self.main_window = None
        self.stock_code_entry = None  # 将在 GUI 创建时绑定
        self.window_var = None  # 窗口选择变量
        self.price_entry = None  # 价格输入框
        self.qty_entry = None  # 数量输入框
        # 模式变量
        self.order_mode = None  # 统一的模式变量

        # 按钮实例变量
        self.btn1 = self.btn2 = self.btn3 = self.btn4 = self.btn5 = None
        self.btn6 = self.btn7 = self.btn8 = self.btn9 = self.btn10 = None

        # Windows API 相关组件
        self.HKL = wintypes.HANDLE
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def connect_to_tdx(self):
        """连接到已运行的通达信窗口，并记录原始窗口位置和大小"""
        try:
            handles = findwindows.find_windows(title_re=f".*{WINDOW_TITLE_KEYWORD}.*", visible_only=True)
            if not handles:
                raise RuntimeError(f"未找到标题包含 '{WINDOW_TITLE_KEYWORD}' 的窗口")
            self.app = Application(backend="win32").connect(handle=handles[0])
            self.main_window = self.app.window(handle=handles[0])
            # 记录原始窗口矩形 (left, top, right, bottom)
            rect = self.main_window.rectangle()
            self._original_rect = (rect.left, rect.top, rect.right, rect.bottom)
            return True
        except Exception as e:
            print(f"❌ 连接通达信失败: {e}")
            return False

    def focus_window(self):
        if not self.main_window:
            if not self.connect_to_tdx():
                return False

        try:
            hwnd = self.main_window.handle

            # 恢复原始窗口位置和大小
            if hasattr(self, '_original_rect'):
                left, top, right, bottom = self._original_rect
                width = right - left
                height = bottom - top
                # SWP_NOZORDER | SWP_NOACTIVATE = 0x0004 | 0x0010 = 0x0014
                self.user32.SetWindowPos(hwnd, 0, left, top, width, height, 0x0014)

            # 激活窗口（前台显示）
            self.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            self.user32.SetForegroundWindow(hwnd)
            self.user32.SetActiveWindow(hwnd)
            self.user32.SetFocus(hwnd)

            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"⚠️ 激活或恢复窗口失败: {e}")
            return False

    def send_key_sequence(self, keys):
        if not self.focus_window():
            return False
        try:
            send_keys(keys, with_spaces=True, pause=0.1)
            return True
        except Exception as e:
            print(f"❌ 发送按键失败: {e}")
            return False

    # ========== 命令函数辅助方法 ==========
    def _input_stock_and_proceed(self, after_input_func):
        """输入股票代码（如果选择）并执行后续操作"""
        if self.window_var.get() == "stock_code":
            stock_code = self.stock_code_entry.get().strip()
            if not stock_code or len(stock_code) != 6 or not stock_code.isdigit():
                messagebox.showerror("输入错误", "请输入6位数字的股票代码")
                return

            # 跳转到指定股票代码的页面
            tdx_soft.reach.open_stock(self, code=f'{stock_code}')
            time.sleep(0.5)  # 等待页面跳转完成

            # 发送股票代码
            if not self.send_key_sequence(stock_code):
                return
            time.sleep(0.3)  # 等待代码输入生效
        # 执行后续操作
        after_input_func()

    def get_window_handle(self, window_title_keyword):
        """根据窗口标题关键词查找通达信窗口句柄"""
        hwnd = 0

        def callback(handle, extra):
            nonlocal hwnd
            window_title = win32gui.GetWindowText(handle)
            if window_title_keyword in window_title and win32gui.IsWindowVisible(handle):
                hwnd = handle
                return False
            return True

        win32gui.EnumWindows(callback, None)
        return hwnd

    # ========== 价格获取方法（改进版） ==========

    # ========== 命令函数 ==========
    def cmd_f9_f1(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "自设价模式":
                # 获取当前买入价格
                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改买入价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 发送确认和数量
            elif current_mode == "抢单模式":
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            send_keys("{F1}")
            time.sleep(0.3)
            # 买入按键
            send_keys("{ENTER}{ENTER}")
            print("买入：全仓，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f9_f2(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "自设价模式":
                # 获取当前买入价格
                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改买入价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 发送确认和数量
            elif current_mode == "抢单模式":
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            send_keys("{F2}")
            time.sleep(0.3)
            # 买入按键
            send_keys("{ENTER}{ENTER}")
            print("买入：1/2仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f9_f3(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "自设价模式":
                # 获取当前买入价格
                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改买入价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 发送确认和数量
            elif current_mode == "抢单模式":
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            send_keys("{F3}")
            time.sleep(0.3)
            # 买入按键
            send_keys("{ENTER}{ENTER}")
            print("买入：1/3仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f9_enter(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "自设价模式":
                # 获取当前买入价格
                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改买入价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 发送确认和数量
            elif current_mode == "抢单模式":
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            send_keys("{ENTER}")
            time.sleep(0.3)
            # 买入按键
            send_keys("{ENTER}{ENTER}")

            print("买入：自设仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f9_btn5(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "价量自定模式":
                # 获取当前买入价格

                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改买入价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            qty = self.qty_entry.get().strip()
            if not qty or not qty.isdigit():
                messagebox.showerror("输入错误", "请输入有效的股数")
                return

            pyautogui.typewrite(qty)
            time.sleep(0.3)
            # 买入按键
            send_keys("{ENTER}{ENTER}")

            print(f"买入：{qty}，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_yellow(self):
        # 撤单不需要股票代码
        self.send_key_sequence("{F11} {ENTER} {ENTER}")
        print("撤单，已经提交。")

    def cmd_f10_f1(self):
        def action():
            self.send_key_sequence("{F10}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "自设价模式":
                # 获取当前卖出价格

                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改卖出价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 发送确认和数量
            elif current_mode == "抢单模式":
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            send_keys("{F1}")
            time.sleep(0.3)
            # 卖出按键
            send_keys("{ENTER}{ENTER}")

            print("卖出：全部仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f10_f2(self):
        def action():
            self.send_key_sequence("{F10}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "自设价模式":
                # 获取当前卖出价格

                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改卖出价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 发送确认和数量
            elif current_mode == "抢单模式":
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            send_keys("{F2}")
            time.sleep(0.3)
            # 卖出按键
            send_keys("{ENTER}{ENTER}")

            print("卖出：1/2仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f10_f3(self):
        def action():
            self.send_key_sequence("{F10}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "自设价模式":
                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改卖出价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 发送确认和数量
            elif current_mode == "抢单模式":
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            send_keys("{F3}")
            time.sleep(0.3)
            # 卖出按键
            send_keys("{ENTER}{ENTER}")

            print("卖出：1/3仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f10_enter(self):
        def action():
            self.send_key_sequence("{F10}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "自设价模式":
                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改卖出价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 发送确认和数量
            elif current_mode == "抢单模式":
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            send_keys("{ENTER}")
            time.sleep(0.3)
            # 卖出按键
            send_keys("{ENTER}{ENTER}")

            print("卖出：自定数量仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f10_btn10(self):
        def action():
            self.send_key_sequence("{F10}")
            time.sleep(0.3)

            current_mode = self.order_mode.get()
            if current_mode == "价量自定模式":
                # 获取当前卖出价格

                new_price = float(self.price_entry.get().strip())
                pyautogui.typewrite(f"{new_price:.2f}")  # 保留两位小数
                print(f"修改卖出价格: {new_price:.2f}")
                time.sleep(0.3)
                send_keys("{ENTER}")
                time.sleep(0.3)

            # 数量框
            qty = self.qty_entry.get().strip()
            if not qty or not qty.isdigit():
                messagebox.showerror("输入错误", "请输入有效的股数")
                return

            pyautogui.typewrite(qty)
            time.sleep(0.3)
            # 卖出按键
            send_keys("{ENTER}{ENTER}")

            print(f"卖出：{qty}，已经提交。")

        self._input_stock_and_proceed(action)

    def order_mode_show(self):
        """根据选择的交易模式显示/隐藏相应按钮"""
        current_mode = self.order_mode.get()
        if current_mode == "价量自定模式":
            # 隐藏不需要的按钮
            self.btn1.pack_forget()  # 买 1
            self.btn2.pack_forget()  # 买/2
            self.btn3.pack_forget()  # 买/3
            self.btn4.pack_forget()  # 量自设
            self.btn6.pack_forget()  # 卖 1
            self.btn7.pack_forget()  # 卖/2
            self.btn8.pack_forget()  # 卖 /3
            self.btn9.pack_forget()  # 卖自设
            # 显示需要的按钮

            self.btn5.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 价+量自定（买）
            self.btn10.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 价+量自定（卖）
        elif current_mode == "自设价模式":

            # 隐藏价量自定按钮
            self.btn5.pack_forget()  # 价+量自定（买）
            self.btn10.pack_forget()  # 价+量自定（卖）
            # 显示其他按钮

            self.btn1.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 买 1
            self.btn2.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 买/2
            self.btn3.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 买/3
            self.btn4.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 量自设
            self.btn6.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 卖 1
            self.btn7.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 卖/2
            self.btn8.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 卖 /3
            self.btn9.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 卖自设
        elif current_mode == "抢单模式":

            # 隐藏价量自定按钮
            self.btn5.pack_forget()  # 价+量自定（买）
            self.btn10.pack_forget()  # 价+量自定（卖）
            # 显示其他按钮
            self.btn1.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 买 1
            self.btn2.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 买/2
            self.btn3.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 买/3
            self.btn4.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 量自设
            self.btn6.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 卖 1
            self.btn7.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 卖/2
            self.btn8.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 卖 /3
            self.btn9.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)  # 卖自设

    # ========== GUI 创建 ==========
    def create_gui(self):
        root = tk.Tk()
        root.title("TDX快捷交易 (pywinauto版)")
        root.geometry("380x250")  # 增加高度容纳状态栏
        root.resizable(True, True)
        root.attributes('-topmost', True)


        # 操作信息状态栏
        status_label = tk.Label(root, text="", font=("宋体", 10), fg="green")
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        def update_status(message, duration=5000):
            status_label.config(text=message)
            root.after(duration, lambda: status_label.config(text=""))

        # 第一排：窗口选择和交易模式选择
        top_frame = ttk.Frame(root)
        top_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # 左侧：当前窗口选择
        window_frame = ttk.Frame(top_frame)
        window_frame.pack(side=tk.LEFT)
        self.window_var = tk.StringVar(value="current_window")
        window_radio = tk.Radiobutton(
            window_frame,
            text="当前窗口",
            variable=self.window_var,
            value="current_window"
        )
        window_radio.pack(side=tk.LEFT, anchor=tk.W)

        # 中间：股票代码输入
        # code_frame = ttk.Frame(top_frame)
        # code_frame.pack(side=tk.LEFT, padx=10)
        # code_radio = tk.Radiobutton(
        #     code_frame,
        #     text="股票代码",
        #     variable=self.window_var,
        #     value="stock_code"
        # )
        # code_radio.pack(side=tk.LEFT, anchor=tk.W)
        # self.stock_code_entry = tk.Entry(code_frame, font=("Consolas", 12), width=6, validate="key")
        # # 验证输入只允许数字且最多6位
        # vcmd = (root.register(lambda s: s.isdigit() and len(s) <= 6), '%P')
        # self.stock_code_entry.config(validate="key", validatecommand=vcmd)
        # self.stock_code_entry.pack(side=tk.LEFT, anchor=tk.W, padx=5)
        # self.stock_code_entry.insert(0, "")  # 默认值

        # 右侧：交易模式选择
        mode_frame = ttk.Frame(top_frame)
        mode_frame.pack(side=tk.RIGHT)
        tk.Label(mode_frame, text="模式:", font=("宋体", 10)).pack(side=tk.LEFT)

        self.order_mode = tk.StringVar(value="抢单模式")

        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.order_mode,
            values=["抢单模式", "自设价模式", "价量自定模式"],
            state="readonly",
            width=10
        )
        mode_combo.set("抢单模式")
        mode_combo.pack(side=tk.LEFT)

        # 第二排：价格和数量输入，以及撤单按钮
        middle_frame = ttk.Frame(root)
        middle_frame.pack(fill=tk.X, padx=10, pady=5)

        # 左侧：价格和数量输入
        price_qty_frame = ttk.Frame(middle_frame)
        price_qty_frame.pack(side=tk.LEFT)

        # 股价输入
        tk.Label(price_qty_frame, text="股价:", font=("宋体", 11)).pack(side=tk.LEFT)
        self.price_entry = tk.Entry(price_qty_frame, font=("Consolas", 11), width=10)
        self.price_entry.pack(side=tk.LEFT, padx=5)
        self.price_entry.insert(0, "6.85")  # 默认价格

        # 股数输入
        tk.Label(price_qty_frame, text="股数:", font=("宋体", 11)).pack(side=tk.LEFT)
        self.qty_entry = tk.Entry(price_qty_frame, font=("Consolas", 11), width=10)
        self.qty_entry.pack(side=tk.LEFT, padx=5)
        self.qty_entry.insert(0, "200")  # 默认股数

        # 右侧：撤单按钮
        cancel_frame = ttk.Frame(middle_frame)
        cancel_frame.pack(side=tk.RIGHT)
        cancel_btn = tk.Button(
            cancel_frame,
            text="撤单",
            font=("宋体", 12, "bold"),
            width=5,
            height=2,
            bg="yellow",
            command=lambda: self._safe_call(self.cmd_yellow, update_status)
        )
        cancel_btn.pack()

        # 按钮辅助函数
        def make_button(parent, text, bg_color, cmd):
            wrapped_cmd = lambda: self._safe_call(cmd, update_status)
            return tk.Button(
                parent, text=text, font=("宋体", 12, "bold"),
                width=5, height=2, bg=bg_color, command=wrapped_cmd
            )

        # 买入按钮行
        row1_frame = ttk.Frame(root)
        row1_frame.pack(fill=tk.X, padx=5, pady=5)
        self.btn1 = make_button(row1_frame, "买 1", "lightblue", self.cmd_f9_f1)
        self.btn2 = make_button(row1_frame, "买/2", "lightblue", self.cmd_f9_f2)
        self.btn3 = make_button(row1_frame, "买/3", "yellow", self.cmd_f9_f3)
        self.btn4 = make_button(row1_frame, "量\n自设", "lightblue", self.cmd_f9_enter)
        self.btn5 = make_button(row1_frame, "价+量\n自定", "lightblue", self.cmd_f9_btn5)
        for btn in [self.btn1, self.btn2, self.btn3, self.btn4, self.btn5]:
            btn.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)

        # 卖出按钮行
        row2_frame = ttk.Frame(root)
        row2_frame.pack(fill=tk.X, padx=2, pady=2)
        self.btn6 = make_button(row2_frame, "卖 1", "lightcoral", self.cmd_f10_f1)
        self.btn7 = make_button(row2_frame, "卖/2", "red", self.cmd_f10_f2)
        self.btn8 = make_button(row2_frame, "卖 /3", "lightcoral", self.cmd_f10_f3)
        self.btn9 = make_button(row2_frame, "卖\n自设", "red", self.cmd_f10_enter)
        self.btn10 = make_button(row2_frame, "价+量\n自定", "red", self.cmd_f10_btn10)
        for btn in [self.btn6, self.btn7, self.btn8, self.btn9, self.btn10]:
            btn.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)

        # 绑定模式选择事件，当模式改变时更新按钮显示
        mode_combo.bind('<<ComboboxSelected>>', lambda event: self.order_mode_show())

        # 初始显示按钮（根据默认模式）
        self.order_mode_show()

        return root

    @staticmethod
    def _safe_call(func, update_status):
        """安全调用交易命令，并捕获异常显示到状态栏"""
        try:
            func()
            update_status("✅ 操作已发送", 2000)
        except Exception as e:
            error_msg = f"❌ 错误: {str(e)}"
            print(error_msg)
            update_status(error_msg, 4000)


def main():
    # 启动通达信（如未运行）
    try:
        start_tdx_if_needed()
    except Exception as e:
        messagebox.showerror("启动错误", f"无法启动通达信：{e}")
        return

    tdx = TDXAutomation()
    gui = tdx.create_gui()

    def on_closing():
        if messagebox.askokcancel("退出", "是否关闭 TDX 快捷面板？"):
            gui.destroy()

    gui.protocol("WM_DELETE_WINDOW", on_closing)
    print("💡 GUI 面板已启动（pywinauto 版），请确保通达信窗口可接收输入。")
    gui.mainloop()


if __name__ == "__main__":
    main()