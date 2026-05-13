# -*- coding: utf-8 -*-
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import win32process


# 尝试导入 pywin32
try:
    import win32gui
    import win32api
    import win32con
    import win32clipboard
except ImportError:
    print("正在安装依赖库 pywin32...")
    os.system(f"{sys.executable} -m pip install pywin32")
    import win32gui
    import win32api
    import win32con
    import win32clipboard


def check_tdx_running():
    """检测通达信是否运行，返回(是否运行, PID)"""
    for proc in subprocess.Popen("tasklist", stdout=subprocess.PIPE, shell=True).stdout.read().decode('gbk').split('\n'):
        if 'TdxW.exe' in proc or 'weituo.exe' in proc:
            try:
                pid = int(proc.split()[1])
                return True, pid
            except (ValueError, IndexError):
                continue
    return False, None


class TDXAutomation:
    def __init__(self, window_title="通达信"):
        self.window_title = window_title
        self.hwnd = None

    def find_tdx_window(self):
        """查找通达信主窗口句柄"""
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title in title:
                    windows.append(hwnd)
            return True

        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        if windows:
            self.hwnd = windows[0]
            return True
        else:
            print(f"❌ 未找到标题包含 '{self.window_title}' 的窗口")
            return False

    def focus_window_simple(self):
        """激活通达信窗口，但不改变其大小或状态"""
        if not self.find_tdx_window():
            return False
        try:
            # 仅激活窗口，不调用 ShowWindow(SW_RESTORE)，避免改变窗口状态
            # 如果窗口被最小化，SetForegroundWindow 可能无效，但这是保持原样的代价
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.2)
            print(f"✅ 已激活窗口: {win32gui.GetWindowText(self.hwnd)}")
            return True
        except Exception as e:
            print(f"⚠️ 激活窗口失败: {e}")
            return False
    def send_key(self, key_code, modifiers=None):
        """向通达信窗口发送按键（支持组合键）"""
        if not self.hwnd:
            if not self.find_tdx_window():
                return False

        # 按下修饰键（如 Ctrl）
        if modifiers:
            for mod in modifiers:
                win32api.keybd_event(mod, 0, 0, 0)

        # 按下主键
        win32api.keybd_event(key_code, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)

        # 释放修饰键
        if modifiers:
            for mod in reversed(modifiers):
                win32api.keybd_event(mod, 0, win32con.KEYEVENTF_KEYUP, 0)

        time.sleep(0.1)
        return True

    def press_enter(self, count=1):
        for _ in range(count):
            self.send_key(win32con.VK_RETURN)

    # ========== GUI 命令函数 ==========
    def cmd_f9_f1(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        time.sleep(0.2)
        self.send_key(win32con.VK_F1, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        print("买入：全仓，已经提交。")


    def cmd_f9_f2(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        time.sleep(0.2)  # 在F9和F2之间添加0.2秒延迟
        self.send_key(win32con.VK_F2, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        print("买入：1/2 仓，已经提交。")

    def cmd_f9_f3(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        time.sleep(0.2)
        self.send_key(win32con.VK_F3, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        print("买入：1/3 仓，已经提交。")

    def cmd_f9_enter(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        self.press_enter(3)
        print("买入：自设仓位，已经提交。")

    def cmd_yellow(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F11)
        self.press_enter(2)
        print("撤单，已经提交。")

    def cmd_f10_f1(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        time.sleep(0.2)
        self.send_key(win32con.VK_F1, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        print("卖出：全部仓位，已经提交。")

    def cmd_f10_f2(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        time.sleep(0.2)
        self.send_key(win32con.VK_F2, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        print("卖出：1/2仓位，已经提交。")

    def cmd_f10_f3(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        time.sleep(0.2)
        self.send_key(win32con.VK_F3, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        print("卖出：1/3仓位，已经提交。")

    def cmd_f10_enter(self):
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        self.press_enter(3)
        print("卖出：自设仓位，已经提交。")

    # ========== GUI 创建 ==========
    def create_gui(self):
        root = tk.Tk()
        root.title("TDX快捷交易 (pywin32版)")
        root.geometry("330x140")
        root.resizable(True, True)
        root.attributes('-topmost', True)

        status_label = tk.Label(root, text="", font=("宋体", 10), fg="green")
        status_label.pack(pady=5)

        def update_status(message, duration=5000):
            status_label.config(text=message)
            root.after(duration, lambda: status_label.config(text=""))

        def make_button(parent, text, bg_color, cmd):
            wrapped_cmd = lambda: self._safe_call(cmd, update_status)
            return tk.Button(
                parent, text=text, font=("宋体", 12, "bold"),
                width=5, height=2, bg=bg_color, command=wrapped_cmd
            )

        # 包装命令以捕获异常并更新状态
        def _safe_call(self, func, update_status):
            try:
                func()
                # 提取打印的最后一行作为状态（简化）
                # 实际可改进为返回消息
            except Exception as e:
                msg = f"❌ 操作失败: {str(e)}"
                print(msg)
                update_status(msg, 5000)
        # Monkey-patch for closure
        self._safe_call = lambda f, u: _safe_call(self, f, u)

        row1_frame = ttk.Frame(root)
        row1_frame.pack(fill=tk.X, padx=5, pady=5)

        btn1 = make_button(row1_frame, "买 1", "lightblue", self.cmd_f9_f1)
        btn2 = make_button(row1_frame, "买/2", "lightblue", self.cmd_f9_f2)
        btn3 = make_button(row1_frame, "买/3", "yellow", self.cmd_f9_f3)
        btn4 = make_button(row1_frame, "买\n自设", "lightblue", self.cmd_f9_enter)
        btn5 = make_button(row1_frame, "撤单", "yellow", self.cmd_yellow)

        for btn in [btn1, btn2, btn3, btn4, btn5]:
            btn.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)

        row2_frame = ttk.Frame(root)
        row2_frame.pack(fill=tk.X, padx=2, pady=2)

        btn6 = make_button(row2_frame, "卖 1", "lightcoral", self.cmd_f10_f1)
        btn7 = make_button(row2_frame, "卖/2", "red", self.cmd_f10_f2)
        btn8 = make_button(row2_frame, "卖 /3", "lightcoral", self.cmd_f10_f3)
        btn9 = make_button(row2_frame, "卖\n自设", "red", self.cmd_f10_enter)

        for btn in [btn6, btn7, btn8, btn9]:
            btn.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)

        return root


def main():
    tdx = TDXAutomation()
    gui = tdx.create_gui()

    def on_closing():
        if messagebox.askokcancel("退出", "是否关闭 TDX 快捷面板？"):
            gui.destroy()

    gui.protocol("WM_DELETE_WINDOW", on_closing)
    print("💡 GUI 面板已启动（pywin32 版），请确保通达信窗口可接收输入。")


    def get_tdx_hwnd(pid):
        """通过PID获取通达信窗口句柄"""
        hwnd_list = []

        def enum_windows_callback(hwnd, extra):
            # 获取窗口对应的进程PID
            window_pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            if window_pid == pid and win32gui.IsWindowVisible(hwnd):
                hwnd_list.append(hwnd)
            return True

        # 枚举所有窗口，筛选对应PID的可见窗口
        win32gui.EnumWindows(enum_windows_callback, None)
        return hwnd_list[0] if hwnd_list else None

    # 1. 检测通达信是否运行，未运行则启动
    is_running, tdx_pid = check_tdx_running()
    if not is_running:
        # 通达信启动路径
        tdx_exe_path = r"D:\zd_zyb\TdxW.exe"
        subprocess.Popen(tdx_exe_path)
        # 等待程序启动
        import time
        time.sleep(5)
        is_running, tdx_pid = check_tdx_running()

    # 2. 获取窗口句柄
    if tdx_pid:
        tdx_hwnd = get_tdx_hwnd(tdx_pid)
        if tdx_hwnd:
            # 3. 激活窗口并执行交互操作（示例：激活窗口）
            win32gui.SetForegroundWindow(tdx_hwnd)
            # 后续：输入股票代码、点击下单按钮等操作
            print(f"通达信窗口句柄：{tdx_hwnd}，已激活")


    gui.mainloop()


if __name__ == "__main__":
    main()