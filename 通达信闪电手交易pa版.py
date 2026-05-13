# -*- coding: utf-8 -*-
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys
import base64
with open("app1.ico", "rb") as f:
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
                if line.startswith("TDX_EXE_PATH="):
                    return line.split("=", 1)[1].strip()
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
        subprocess.Popen(get_from_setup())
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

    def connect_to_tdx(self):
        """连接到已运行的通达信窗口"""
        try:
            # 查找包含关键词的窗口
            handles = findwindows.find_windows(title_re=f".*{WINDOW_TITLE_KEYWORD}.*", visible_only=True)
            if not handles:
                raise RuntimeError(f"未找到标题包含 '{WINDOW_TITLE_KEYWORD}' 的窗口")
            # 连接到第一个匹配窗口
            self.app = Application(backend="win32").connect(handle=handles[0])
            self.main_window = self.app.window(handle=handles[0])
            return True
        except Exception as e:
            print(f"❌ 连接通达信失败: {e}")
            return False

    def focus_window(self):
        """激活通达信窗口"""
        if not self.main_window:
            if not self.connect_to_tdx():
                return False
        try:
            self.main_window.set_focus()
            time.sleep(0.3)
            print("✅ 通达信窗口已激活")
            return True
        except Exception as e:
            print(f"⚠️ 激活窗口失败: {e}")
            return False

    def send_key_sequence(self, keys):
        """向通达信发送按键序列（如 '^f1' 表示 Ctrl+F1）"""
        if not self.focus_window():
            return False
        try:
            send_keys(keys, with_spaces=True, pause=0.1)
            return True
        except Exception as e:
            print(f"❌ 发送按键失败: {e}")
            return False

    # ========== 命令函数 ==========
    def cmd_f9_f1(self):
        send_keys("600000{ENTER}")
        time.sleep(0.5)
        self.send_key_sequence("{F9}")
        time.sleep(0.1)
        send_keys("10.5")
        time.sleep(0.1)
        send_keys("{ENTER}")
        time.sleep(0.1)
        send_keys("200")
        time.sleep(0.1)
        send_keys("{ENTER}{ENTER}")
        # self.send_key_sequence("{F9} ^{F1} {ENTER} {ENTER}")
        print("买入：全仓，已经提交。")

    def cmd_f9_f2(self):
        self.send_key_sequence("{F9} ^{F2} {ENTER} {ENTER}")
        print("买入：1/2 仓，已经提交。")

    def cmd_f9_f3(self):
        self.send_key_sequence("{F9} ^{F3} {ENTER} {ENTER}")
        print("买入：1/3 仓，已经提交。")

    def cmd_f9_enter(self):
        self.send_key_sequence("{F9} {ENTER} {ENTER} {ENTER}")
        print("买入：自设仓位，已经提交。")

    def cmd_yellow(self):
        self.send_key_sequence("{F11} {ENTER} {ENTER}")
        print("撤单，已经提交。")

    def cmd_f10_f1(self):
        self.send_key_sequence("{F10} ^{F1} {ENTER} {ENTER}")
        print("卖出：全部仓位，已经提交。")

    def cmd_f10_f2(self):
        self.send_key_sequence("{F10} ^{F2} {ENTER} {ENTER}")
        print("卖出：1/2仓位，已经提交。")

    def cmd_f10_f3(self):
        self.send_key_sequence("{F10} ^{F3} {ENTER} {ENTER}")
        print("卖出：1/3仓位，已经提交。")

    def cmd_f10_enter(self):
        self.send_key_sequence("{F10} {ENTER} {ENTER} {ENTER}")
        print("卖出：自设仓位，已经提交。")

    # ========== GUI 创建 ==========
    def create_gui(self):
        root = tk.Tk()
        root.title("TDX快捷交易 (pywinauto版)")
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

        self._safe_call = lambda f, u: _safe_call_wrapper(self, f, u)

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

def _safe_call_wrapper(instance, func, update_status):
    try:
        func()
    except Exception as e:
        msg = f"❌ 操作失败: {str(e)}"
        print(msg)
        update_status(msg, 5000)

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