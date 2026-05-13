# -*- coding: utf-8 -*-
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import win32process
import pyautogui
import csv  # 新增：用于CSV处理
import datetime  # 新增：用于时间戳

TDX_PATH = ""  # 默认为空，将由 get_from_setup 填充

# 日志文件配置
LOG_FILE = "operation_log.csv"
TDX_CMD_FILE = "tdx_cmd.txt"


# 定义日志记录函数
def add_log(message, level="INFO"):

    try:
        # 获取当前时间，精确到毫秒
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        # 准备新的一行数据
        new_row = [timestamp, level, message]

        # 读取现有日志tdx_auto_trader.py
        logs = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.reader(f)
                    logs = list(reader)
            except Exception as e:
                print(f"读取日志文件失败: {e}")

        # 添加新日志
        logs.append(new_row)

        # 如果总行数超过500，保留最新的500条（删除前面的）
        if len(logs) > 500:
            logs = logs[-500:]

        # 写回文件
        with open(LOG_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(logs)
    except Exception as e:
        # 防止日志记录本身导致程序崩溃
        print(f"日志写入异常: {e}")


# 尝试导入 pywin32
try:
    import win32gui
    import win32api
    import win32con
except ImportError:
    print("正在安装依赖库 pywin32...")
    os.system(f"{sys.executable} -m pip install pywin32")
    import win32gui
    import win32api
    import win32con


def get_from_setup():
    """从setup.txt文件中读取TDX路径"""
    setup_file = "setup.txt"
    if os.path.exists(setup_file):
        with open(setup_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("TDX_PATH="):
                    path = line.split("=", 1)[1].strip()
                    add_log(f"读取通达信路径成功: {path}")
                    return path
    add_log("未找到setup.txt或未配置TDX_PATH", "WARN")
    return None


# 修正：原代码此处逻辑可能有误，若get_from_setup返回None，f-string会报错，这里做简单容错
_setup_path = get_from_setup()
TDX_PATH = f'{_setup_path}\\TdxW.exe' if _setup_path else 'TdxW.exe'

WINDOW_TITLE_KEYWORD = "通达信"  # 用于匹配窗口标题


def check_tdx_running():
    """检测通达信是否运行，返回(是否运行, PID)"""
    add_log("检查通达信运行状态...")
    try:
        for proc in subprocess.Popen("tasklist", stdout=subprocess.PIPE, shell=True).stdout.read().decode('gbk').split(
                '\n'):
            if 'TdxW.exe' in proc or 'weituo.exe' in proc:
                try:
                    pid = int(proc.split()[1])
                    add_log(f"通达信正在运行, PID: {pid}")
                    return True, pid
                except (ValueError, IndexError):
                    continue
        add_log("通达信未运行", "INFO")
        return False, None
    except Exception as e:
        add_log(f"检查通达信状态出错: {e}", "ERROR")
        return False, None


class TDXAutomation:
    def __init__(self, window_title="通达信"):
        self.window_title = window_title
        self.hwnd = None
        self.is_monitoring = False  # 新增：监控状态标志
        add_log("TDXAutomation 实例初始化")

    def find_tdx_window(self):
        """查找通达信主窗口句柄"""
        add_log(f"正在查找标题包含 '{self.window_title}' 的窗口...")

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
            add_log(f"成功找到窗口, 句柄: {self.hwnd}")
            return True
        else:
            add_log(f"未找到标题包含 '{self.window_title}' 的窗口", "WARN")
            return False

    def focus_window_simple(self):
        """激活通达信窗口，但不改变其大小或状态"""
        if not self.find_tdx_window():
            return False
        try:
            # 仅激活窗口，不调用 ShowWindow(SW_RESTORE)，避免改变窗口状态
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.2)
            title = win32gui.GetWindowText(self.hwnd)
            add_log(f"窗口已激活: {title}")
            return True
        except Exception as e:
            add_log(f"激活窗口失败: {e}", "ERROR")
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
        time.sleep(0.1)
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)

        # 释放修饰键
        if modifiers:
            for mod in reversed(modifiers):
                win32api.keybd_event(mod, 0, win32con.KEYEVENTF_KEYUP, 0)

        time.sleep(0.1)
        # 记录按键日志（如果不需要太详细的记录可以注释掉下面这行）
        # add_log(f"发送按键: Key={key_code}, Modifiers={modifiers}")
        return True

    def press_enter(self, count=1):
        for _ in range(count):
            self.send_key(win32con.VK_RETURN)

    # ... (其他代码保持不变) ...

    def process_command_file(self):
        """
        读取指令文件并执行。
        【修复】通过重命名文件来解决并发冲突，防止新指令被误删。
        """
        # 如果指令文件不存在，直接返回
        if not os.path.exists(TDX_CMD_FILE):
            return

        # --- 修复点1：文件加锁机制 ---
        # 立即将文件重命名，防止新的指令文件覆盖当前处理
        temp_cmd_file = "tdx_cmd_processing.txt"

        # 如果存在上次遗留的临时文件（比如程序异常退出），先清理
        if os.path.exists(temp_cmd_file):
            try:
                os.remove(temp_cmd_file)
            except:
                pass

        try:
            os.rename(TDX_CMD_FILE, temp_cmd_file)
        except OSError as e:
            # 如果重命名失败（可能文件正在被写入），跳过本次处理
            add_log(f"文件锁定失败，跳过本次: {e}", "WARN")
            return

        add_log("检测到新的指令文件，开始处理...")
        try:
            # --- 1. 读取临时文件内容 ---
            with open(temp_cmd_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # --- 2. 解析 CODE 和 CMD ---
            code = None
            cmd = None
            for line in content.split('\n'):
                if line.startswith("CODE:"):
                    code = line.split(":")[1].strip()
                elif line.startswith("CMD:"):
                    cmd = line.split(":")[1].strip()

            add_log(f"解析指令内容 -> CODE: {code}, CMD: {cmd}")

            # 简单校验
            if not code or not cmd:
                add_log("指令文件格式错误，缺少 CODE 或 CMD", "ERROR")
                return

            # --- 3. 第一步：打开股票 (输入代码) ---
            add_log(f"正在执行: 打开股票 {code}")
            self.open_stock(code)
            # 稍微等待，确保通达信界面已经切换到该股票并加载完毕
            time.sleep(0.5)

            # --- 4. 第二步：执行具体的交易命令 ---
            # 检查指令对应的方法是否存在
            if hasattr(self, cmd):
                method_to_call = getattr(self, cmd)
                if callable(method_to_call):
                    add_log(f"开始执行交易命令: {cmd}")
                    method_to_call()
                    add_log(f"交易命令执行完毕: {cmd}")
                else:
                    add_log(f"方法 '{cmd}' 不可调用", "ERROR")
            else:
                add_log(f"TDXAutomation 类中没有找到名为 '{cmd}' 的方法", "ERROR")

        except Exception as e:
            add_log(f"读取/执行指令文件出错: {e}", "ERROR")
        finally:
            # --- 5. 清理：删除临时文件 ---
            try:
                if os.path.exists(temp_cmd_file):
                    # 【修复点2】不再需要 sleep 2秒，因为我们操作的是临时文件，不会阻塞新文件的写入
                    os.remove(temp_cmd_file)
                add_log("指令文件处理完成")
            except Exception as e:
                add_log(f"删除临时文件失败: {e}", "ERROR")



    # ========== GUI 命令函数 ==========

    def cmd_f9_f1(self):
        add_log("操作: 买入 全仓")
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        time.sleep(0.3)
        self.press_enter(1)
        time.sleep(0.3)
        self.send_key(win32con.VK_F1, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        msg = "买入：全仓"
        print(msg)
        return msg

    def cmd_f9_f2(self):
        add_log("操作: 买入 1/2仓")
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        time.sleep(0.3)
        self.press_enter(1)
        time.sleep(0.3)
        self.send_key(win32con.VK_F2, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        msg = "买入：1/2仓"
        print(msg)
        return msg

    def cmd_f9_f3(self):
        add_log("操作: 买入 1/3仓")
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        time.sleep(0.3)
        self.press_enter(1)
        time.sleep(0.3)
        self.send_key(win32con.VK_F3, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        msg = "买入：1/3仓"
        print(msg)
        return msg

    def cmd_f9_f4(self):
        add_log("操作: 买入 1/4仓")
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        time.sleep(0.3)
        self.press_enter(1)
        time.sleep(0.3)
        self.send_key(win32con.VK_F4, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        msg = "买入：1/4仓"
        print(msg)
        return msg

    def cmd_f9_enter(self):
        add_log("操作: 买入 自设仓位")
        self.focus_window_simple()
        self.send_key(win32con.VK_F9)
        self.press_enter(3)
        msg = "买入：自设量"
        print(msg)
        return msg

    def cmd_yellow(self):
        add_log("操作: 撤单")
        self.focus_window_simple()
        self.send_key(win32con.VK_F11)
        self.press_enter(2)
        msg = "撤单"
        print(msg)
        return msg

    def cmd_f10_f1(self):
        add_log("操作: 卖出 全仓")
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        time.sleep(0.3)
        self.press_enter(1)
        time.sleep(0.3)
        self.send_key(win32con.VK_F1, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        msg = "卖出：全仓"
        print(msg)
        return msg

    def cmd_f10_f2(self):
        add_log("操作: 卖出 1/2仓位")
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        time.sleep(0.3)
        self.press_enter(1)
        time.sleep(0.3)
        self.send_key(win32con.VK_F2, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        msg = "卖出：1/2仓"
        print(msg)
        return msg

    def cmd_f10_f3(self):
        add_log("操作: 卖出 1/3仓位")
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        time.sleep(0.3)
        self.press_enter(1)
        time.sleep(0.3)
        self.send_key(win32con.VK_F3, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        msg = "卖出：1/3仓"
        print(msg)
        return msg

    def cmd_f10_f4(self):
        add_log("操作: 卖出 1/4仓位")
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        time.sleep(0.3)
        self.press_enter(1)
        time.sleep(0.3)
        self.send_key(win32con.VK_F4, modifiers=[win32con.VK_CONTROL])
        self.press_enter(2)
        msg = "卖出：1/4仓"
        print(msg)
        return msg

    def cmd_f10_enter(self):
        add_log("操作: 卖出 自设仓位")
        self.focus_window_simple()
        self.send_key(win32con.VK_F10)
        self.press_enter(3)
        msg = "卖出：自设量"
        print(msg)
        return msg

    def cmd_scan(self):
        """监控/触发 - 根据当前状态执行操作"""
        if self.is_monitoring:
            add_log("操作: 停止监控")
            # 这里可以添加实际停止监控的逻辑，例如停止某个后台任务
            print("监控：已停止")
        else:
            add_log("操作: 开始监控")
            self.focus_window_simple()
            time.sleep(0.2)
            # pyautogui.press('f12') # 假设F12是键盘精灵的快捷键
            print("监控：已触发自动买入")

    def open_stock(self, code):



        """打开键盘精灵并输入指定个股代码 + 回车"""
        add_log(f"正在打开股票代码: {code}")
        self.focus_window_simple()
        time.sleep(0.3)
        # 输入指定代码，时间间隔
        pyautogui.write(code, interval=0.1)
        time.sleep(0.3)
        pyautogui.press('enter')

    # ========== GUI 创建 ==========

    def animate_button(self, button, angle=0):
        """动画函数：旋转按钮文本"""
        if not hasattr(button, 'is_monitoring') or not button.is_monitoring:
            button.animation_id = None
            return  # 如果未监控，停止动画

        # 简单的旋转动画，通过改变按钮文本实现（实际项目中可以更复杂）
        symbols = ['监控中', '|', '//', '--', '\\']
        button.config(text=symbols[angle % len(symbols)])
        # 每200毫秒更新一次
        button.animation_id = button.after(200, lambda: self.animate_button(button, angle + 1))

    def toggle_monitoring(self, button):
        """切换监控状态并更新按钮"""
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            button.config(text="监控中", bg="orange", relief="sunken")
            # 启动动画
            if hasattr(button, 'animation_id') and button.animation_id:
                button.after_cancel(button.animation_id)
            button.is_monitoring = True
            self.animate_button(button)
            print("监控：已启动")

            # --- 修改点1：按下监控按钮时，立即执行一次指令文件处理 ---
            self.process_command_file()

        else:
            button.config(text="监控", bg="lightgreen", relief="raised")
            # 停止动画
            button.is_monitoring = False
            if hasattr(button, 'animation_id') and button.animation_id:
                button.after_cancel(button.animation_id)
                button.animation_id = None
            # 恢复初始文本
            button.config(text="监控")
            print("监控：已停止")

        # 执行核心监控/停止逻辑
        # self.cmd_scan()

    def create_gui(self):
        root = tk.Tk()
        root.title("TDX一键下单 带自动交易监控")

        # --- 修复 1：图标设置 ---
        try:
            root.iconbitmap('app1.ico')
        except Exception:
            print("未找到app1.ico图标，不影响窗口功能")

        root.geometry("280x140")
        root.resizable(True, True)
        root.attributes('-topmost', True)

        # 状态标签初始化
        status_label = tk.Label(root, text="系统就绪", font=("宋体", 10), fg="green")  # 建议给个初始文字方便调试

        for i in range(6):
            root.grid_columnconfigure(i, weight=1)

        def update_status(message, duration=5000):
            status_label.config(text=message)
            root.after(duration, lambda: status_label.config(text="系统就绪"))  # 恢复默认文字或清空

        def make_button(parent, text, bg_color, cmd):
            wrapped_cmd = lambda: self._safe_call(cmd, update_status)
            button = tk.Button(
                parent, text=text, font=("宋体", 12, "bold"),
                width=5, height=2, bg=bg_color, command=wrapped_cmd
            )
            return button

        # 包装命令以捕获异常并更新状态
        def _safe_call(self, func, update_status):
            try:
                result = func()  # 执行函数并获取返回值

                # 如果函数返回了字符串，更新状态标签
                if isinstance(result, str):
                    update_status(result, 5000)  # 显示消息5秒

            except Exception as e:
                msg = f"❌ 操作失败: {str(e)}"
                add_log(msg, "ERROR")
                print(msg)
                update_status(msg, 5000)

        # Monkey-patch for closure
        self._safe_call = lambda f, u: _safe_call(self, f, u)

        # 创建按钮
        btn_scan = tk.Button(
            root, text="监控", font=("宋体", 12, "bold"),
            width=5, height=2, bg="lightgreen",
            command=lambda: self.toggle_monitoring(btn_scan)
        )
        btn_scan.is_monitoring = False
        btn_scan.animation_id = None

        btn1 = make_button(root, "买 1", "lightblue", self.cmd_f9_f1)
        btn2 = make_button(root, "买/2", "lightblue", self.cmd_f9_f2)
        btn3 = make_button(root, "买/3", "yellow", self.cmd_f9_f3)
        btn4 = make_button(root, "买\n自设", "lightblue", self.cmd_f9_enter)
        btn5 = make_button(root, "撤单", "yellow", self.cmd_yellow)
        btn6 = make_button(root, "卖 1", "lightcoral", self.cmd_f10_f1)
        btn7 = make_button(root, "卖/2", "red", self.cmd_f10_f2)
        btn8 = make_button(root, "卖 /3", "lightcoral", self.cmd_f10_f3)
        btn9 = make_button(root, "卖\n自设", "red", self.cmd_f10_enter)

        # 监控在第1列
        btn_scan.grid(row=1, column=1, sticky="nsew", padx=(5, 1), pady=1)

        # 状态标签放在中间 (column=2)，并跨2列 (columnspan=2)，这样视觉上更居中
        status_label.grid(row=1, column=2, columnspan=2, sticky="nsew", padx=(5, 1), pady=1)

        # 由于 label 占了 col 2 和 3，这里把撤单放在 col 4
        btn5.grid(row=1, column=4, sticky="nsew", padx=(5, 5), pady=1)

        # 第二行 (row=2)
        btn1.grid(row=2, column=1, sticky="nsew", padx=1, pady=1)
        btn2.grid(row=2, column=2, sticky="nsew", padx=1, pady=1)
        btn3.grid(row=2, column=3, sticky="nsew", padx=1, pady=1)
        btn4.grid(row=2, column=4, sticky="nsew", padx=1, pady=1)

        # 第三行 (row=3)
        btn6.grid(row=3, column=1, sticky="nsew", padx=1, pady=1)
        btn7.grid(row=3, column=2, sticky="nsew", padx=1, pady=1)
        btn8.grid(row=3, column=3, sticky="nsew", padx=1, pady=1)
        btn9.grid(row=3, column=4, sticky="nsew", padx=1, pady=1)

        return root


def main():
    add_log("程序启动")
    tdx = TDXAutomation()
    gui = tdx.create_gui()

    def check_queue():
        if tdx.is_monitoring:
            tdx.process_command_file()

        gui.after(500, check_queue)  # 启动轮询循环

    check_queue()

    def on_closing():
        if messagebox.askokcancel("退出", "是否关闭 TDX一键下单 带自动交易监控？"):
            add_log("程序退出")
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
        add_log(f"通达信未运行，尝试启动: {TDX_PATH}")
        subprocess.Popen(TDX_PATH)
        # 等待程序启动
        import time
        time.sleep(5)
        is_running, tdx_pid = check_tdx_running()
        if is_running:
            add_log(f"通达信启动成功, PID: {tdx_pid}")
        else:
            add_log("通达信启动失败或超时", "ERROR")

    # 2. 获取窗口句柄
    if tdx_pid:
        tdx_hwnd = get_tdx_hwnd(tdx_pid)
        if tdx_hwnd:
            # 3. 激活窗口并执行交互操作（示例：激活窗口）
            win32gui.SetForegroundWindow(tdx_hwnd)
            # 后续：输入股票代码、点击下单按钮等操作
            add_log(f"通达信窗口句柄：{tdx_hwnd}，已激活")

    gui.mainloop()


if __name__ == "__main__":
    main()
