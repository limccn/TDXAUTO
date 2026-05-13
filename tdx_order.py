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
# from pywin32 import win32gui, win32api, win32con, win32process
import win32api
import win32con
import win32process
import threading
import pyautogui
import tdx_soft
import base64
import pygetwindow as gw
#这是pyautogui版本的闪电手下单程序
# 读取.ico文件，转为base64编码
with open("app4.ico", "rb") as f:
    ico_base64 = base64.b64encode(f.read()).decode("utf-8")

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
                if line.startswith("TDX_PATH="):
                    return line.split("=", 1)[1].strip()


TDX_EXE_PATH = get_from_setup()
WINDOW_TITLE_KEYWORD = "通达信"  # 用于匹配窗口标题
TRADING_WINDOW_TITLE = "闪电买入"

# 2. 控件相对窗口的坐标（严格取自200.txt，无需修改）
# 买入价格输入框（EDIT控件）：x=53, y=93, 宽40, 高13
PRICE_INPUT_RELATIVE = (53, 93)
# 买入数量输入框（EDIT控件）：x=53, y=130, 宽64, 高13
QTY_INPUT_RELATIVE = (53, 130)
# 买入按钮（BUTTON控件）：x=13, y=155, 宽49, 高15
BUY_BUTTON_RELATIVE = (13, 155)

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
        tdx_soft.reach().open_stock(code='')
        time.sleep(0.02)  # 等待代码输入生效
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
    def auto_trade_buy(self, target_price, target_qty):
        """自动完成：定位窗口→输入价格→输入数量→点击买入"""
        try:
            self.send_key_sequence("{F9}")
            time.sleep(0.25)
            print("正在定位交易窗口...")
            trading_window = gw.getWindowsWithTitle(TRADING_WINDOW_TITLE)[0]
            if not trading_window.isActive:
                trading_window.activate()
            if trading_window.isMinimized:
                trading_window.restore()
            time.sleep(0.2)  # 延时等待窗口激活（真实软件响应需要时间）
            # 步骤2：获取窗口左上角绝对坐标（转换相对坐标为屏幕绝对坐标）
            window_left, window_top = trading_window.topleft
            print(f"交易窗口定位成功，左上角坐标：({window_left}, {window_top})")
            # 步骤3：计算控件绝对坐标
            # 价格输入框坐标（取输入框中心，提高点击准确率）
            price_x = window_left + PRICE_INPUT_RELATIVE[0] + 20  # +20（输入框宽度的一半）
            price_y = window_top + PRICE_INPUT_RELATIVE[1] + 6  # +6（输入框高度的一半）            # 数量输入框坐标
            qty_x = window_left + QTY_INPUT_RELATIVE[0] + 32  # +32（输入框宽度的一半）
            qty_y = window_top + QTY_INPUT_RELATIVE[1] + 6  # +6（输入框高度的一半）
            # 买入按钮坐标
            buy_btn_x = window_left + BUY_BUTTON_RELATIVE[0] + 24  # +24（按钮宽度的一半）
            buy_btn_y = window_top + BUY_BUTTON_RELATIVE[1] + 7  # +7（按钮高度的一半）
            # 步骤4：输入买入价格（先点击激活→清空原有内容→输入新价格）
            print("正在输入买入价格...")
            time.sleep(0.2)
            pyautogui.click(price_x, price_y, clicks=1, interval=0.1)

            pyautogui.press("backspace")  # 清空
            pyautogui.typewrite(target_price, interval=0.05)  # 慢速输入，适配真实软件
            time.sleep(0.35)

            # 步骤5：输入买入数量（同价格输入逻辑，确保无残留内容）
            send_keys("{ENTER}")
            time.sleep(0.20)
            print("正在输入买入数量...")
            pyautogui.click(qty_x, qty_y, clicks=1, interval=0.1)

            pyautogui.press("backspace")
            pyautogui.typewrite(target_qty, interval=0.05)
            time.sleep(0.35)

            # 步骤6：点击买入按钮，完成交易操作
            print("正在点击买入按钮...")

            send_keys("{ENTER}")
            time.sleep(0.1)
            send_keys("{ENTER}")

            print("自动化操作完成！")

        except IndexError:
            print(f"错误：未找到标题为「{TRADING_WINDOW_TITLE}」的窗口，请确认窗口已打开且标题一致。")
        except Exception as e:
            print(f"错误：自动化操作失败，详情：{str(e)}")

# ========== 命令函数 ==========
    def cmd_f9_f1(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.25)

            send_keys("{ENTER}")
            time.sleep(0.25)

            # 数量框
            send_keys("{F1}")
            time.sleep(0.1)
            # 买入按键
            send_keys("{ENTER}")
            time.sleep(0.1)
            send_keys("{ENTER}")
            print("买入：全仓，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f9_f2(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.25)

            send_keys("{ENTER}")
            time.sleep(0.25)

            # 数量框
            send_keys("{F2}")
            time.sleep(0.1)
            # 买入按键
            send_keys("{ENTER}")
            time.sleep(0.1)
            send_keys("{ENTER}")
            print("买入：1/2仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f9_f3(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.25)

            send_keys("{ENTER}")
            time.sleep(0.25)

            # 数量框
            send_keys("{F3}")
            time.sleep(0.1)
            # 买入按键
            send_keys("{ENTER}")
            time.sleep(0.1)
            send_keys("{ENTER}")
            print("买入：1/3仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f9_enter(self):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.25)

            send_keys("{ENTER}")
            time.sleep(0.25)

            # 数量框
            send_keys("{ENTER}")
            time.sleep(0.1)
            # 买入按键
            send_keys("{ENTER}")
            time.sleep(0.1)
            send_keys("{ENTER}")

            print("买入：自设仓位，已经提交。")

        self._input_stock_and_proceed(action)

    def cmd_f9_btn5(self, target_price, target_qty):
        def action():
            self.send_key_sequence("{F9}")
            time.sleep(0.25)


            pyautogui.typewrite(target_price,interval=0.1)  # 保留两位小数
            print(f"修改买入价格: {target_price}")
            time.sleep(0.3)
            send_keys("{ENTER}")
            time.sleep(0.2)

            # 数量框
            pyautogui.typewrite(target_qty, interval=0.1)
            time.sleep(0.35)
            # 买入按键
            print(f"买入：{target_qty}，已经提交。")
            send_keys("{ENTER}")
            time.sleep(0.1)
            send_keys("{ENTER}")



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