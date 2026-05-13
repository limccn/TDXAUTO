# -*- coding: utf-8 -*-
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
try:
    import pyautogui
except ImportError:
    print("正在安装依赖库 pyautogui...")
    os.system(f"{sys.executable} -m pip install pyautogui")
    import pyautogui
try:
    import pygetwindow as gw
except ImportError:
    print("正在安装依赖库 pygetwindow...")
    os.system(f"{sys.executable} -m pip install pygetwindow")
    import pygetwindow as gw

class TDXAutomation:
    def __init__(self, window_title="通达信"):
        self.window_title = window_title

    def focus_window_simple(self):
        """通过 Alt+Tab 切换到通达信窗口（简单策略）"""
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.3)
        try:
            active = gw.getActiveWindow()
            if active and self.window_title in active.title:
                print(f"✅ 已激活窗口: {active.title}")
                return True
        except Exception as e:
            print(f"⚠️ 获取活动窗口失败: {e}")
        return True  # 默认继续执行，不中断流程

    # def open_keyboard_wizard(self, code="000001"):
    #     """打开键盘精灵并输入股票代码 + 回车"""
    #     self.focus_window_simple()
    #     time.sleep(0.3)
    #     pyautogui.write(code, interval=0.05)
    #     time.sleep(0.1)
    #     pyautogui.press('enter')
    #     print(f'{code}已经输入')

    def setup_assistant(self):
        """录制键盘精灵图标坐标并保存配置"""
        print("\n=== 通达信自动化设置助手 ===")
        print("请将鼠标移动到「键盘精灵」图标上（3秒后记录位置）...")
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        x, y = pyautogui.position()
        print(f"📌 当前鼠标坐标: ({x}, {y})")

        config_content = f'''# 通达信自动化配置文件
keyboard_wizard_x = {x}
keyboard_wizard_y = {y}
'''
        with open('tdx_config.py', 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("✅ 配置已保存至 tdx_config.py")

    # def run_from_config(self, code="000001"):
    #     """从配置文件读取坐标并点击"""
    #     try:
    #         import tdx_config
    #         x = tdx_config.keyboard_wizard_x
    #         y = tdx_config.keyboard_wizard_y
    #         print(f"🖱️ 使用配置坐标点击: ({x}, {y})")
    #         pyautogui.click(x, y)
    #         time.sleep(0.5)
    #         pyautogui.write(code, interval=0.05)
    #         time.sleep(0.2)
    #         pyautogui.press('enter')
    #         return True
    #     except ImportError:
    #         print("❌ 未找到 tdx_config.py，使用默认快捷键方式")
    #         self.open_keyboard_wizard(code)
    #         return True
    #     except Exception as e:
    #         print(f"⚠️ 执行配置操作时出错: {e}")
    #         return False

    def create_gui(self):
        # 创建主窗口
        root = tk.Tk()
        root.title("TDX快捷交易")
        root.geometry("480x200")
        root.resizable(True, True)
        root.attributes('-topmost', True)
        root.attributes('-alpha', 1)

        # 添加状态标签
        status_label = tk.Label(root, text="", font=("宋体", 10), fg="green")
        status_label.pack(pady=5)

        # 更新状态标签的函数
        def update_status(message, duration=5000):
            status_label.config(text=message)
            root.after(duration, lambda: status_label.config(text=""))

        # 按钮创建函数
        def make_button(parent, text, bg_color, cmd):
            return tk.Button(
                parent,
                text=text,
                font=("宋体", 12, "bold"),
                width=9,
                height=4,
                bg=bg_color,
                command=cmd
            )

        # 定义按钮命令函数
        def cmd_f9_f1():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f9')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl')
            time.sleep(0.1)
            pyautogui.hotkey('f1')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            print("买入：全仓，已经提交。")
            update_status("买入：全仓，已经提交。", 5000)
            
        def cmd_f9_f2():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f9')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl')
            time.sleep(0.1)
            pyautogui.hotkey('f2')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            print("买入：1/2 仓，已经提交。")
            update_status("买入：1/2 仓，已经提交。", 5000)
            
        def cmd_f9_f3():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f9')
            time.sleep(0.1)
            pyautogui.hotkey('f3')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            print("买入：1/3 仓，已经提交。")
            update_status("买入：1/3 仓，已经提交。", 5000)
            
        def cmd_f9_enter():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f9')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            print("买入：自设仓位，已经提交。")
            update_status("买入：自设量，已经提交。", 5000)
            
        def cmd_yellow():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f11')
            time.sleep(0.1)
            pyautogui.press('enter')
            time.sleep(0.1)
            pyautogui.press('enter')
            print("撤单，已经提交。")
            time.sleep(0.2)
            pyautogui.press('enter')
            update_status("撤单操作，已经提交。", 5000)
            
        def cmd_f10_f1():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f10')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl')
            time.sleep(0.1)
            pyautogui.hotkey('f1')

            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            print("卖出：全部仓位，已经提交。")
            update_status("卖出：全仓，已经提交。", 5000)
            
        def cmd_f10_f2():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f10')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl')
            time.sleep(0.1)
            pyautogui.hotkey('f2')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            print("卖出：1/2仓位，已经提交。")

            update_status("卖出：1/2 仓，已经提交。", 5000)
            
        def cmd_f10_f3():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f10')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl')
            time.sleep(0.1)
            pyautogui.hotkey('f3')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            print("卖出：1/3仓位，已经提交。")
            update_status("卖出：1/3 仓，已经提交。", 5000)
            
        def cmd_f10_enter():
            self.focus_window_simple()
            time.sleep(0.1)
            pyautogui.hotkey('f10')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.press('enter')
            print("卖出：自设仓位，已经提交。")
            update_status("卖出：自设量，已经提交。", 5000)

        # 创建第一排框架并放置按钮
        row1_frame = ttk.Frame(root)
        row1_frame.pack(fill=tk.X, padx=5, pady=5)

        # 创建第一排按钮
        btn1 = make_button(row1_frame, "买\n全仓", "lightblue", cmd_f9_f1)
        btn2 = make_button(row1_frame, "买\n1/2", "lightblue", cmd_f9_f2)
        btn3 = make_button(row1_frame, "买\n1/3", "yellow", cmd_f9_f3)
        btn4 = make_button(row1_frame, "买\n自设量", "lightblue", cmd_f9_enter)
        btn5 = make_button(row1_frame, "撤单", "yellow", cmd_yellow)

        # 布局第一排按钮
        btn1.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)
        btn2.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)
        btn3.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)
        btn4.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)
        btn5.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)

        # 创建第二排框架并放置按钮
        row2_frame = ttk.Frame(root)
        row2_frame.pack(fill=tk.X, padx=2, pady=2)

        # 创建第二排按钮
        btn6 = make_button(row2_frame, "卖\n全仓", "lightcoral", cmd_f10_f1)
        btn7 = make_button(row2_frame, "卖\n1/2", "red", cmd_f10_f2)
        btn8 = make_button(row2_frame, "卖\n1/3", "lightcoral", cmd_f10_f3)
        btn9 = make_button(row2_frame, "卖\n自设量", "red", cmd_f10_enter)

        # 布局第二排按钮
        btn6.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)
        btn7.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)
        btn8.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)
        btn9.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.BOTH)

        return root

def main():
    tdx = TDXAutomation()

    # 启动 GUI（非阻塞主逻辑，但实际用 mainloop 阻塞）
    gui = tdx.create_gui()

    # 在 GUI 关闭后提供命令行选项（可选）
    def on_closing():
        if messagebox.askokcancel("退出", "是否关闭 TDX 快捷面板？"):
            gui.destroy()

    gui.protocol("WM_DELETE_WINDOW", on_closing)
    print("💡 GUI 面板已启动，请在界面上操作。")

    print("📌 提示：确保通达信窗口处于可接收输入状态。")
    gui.mainloop()

    # 可选：后续扩展命令行模式（当前以 GUI 为主）
    # choice = input("\n选择功能 (1-设配, 2-运行配置): ")
    # ...


if __name__ == "__main__":
    main()