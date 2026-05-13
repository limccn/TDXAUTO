import tkinter as tk
from tkinter import simpledialog, messagebox
import pyautogui
import time
import json
import os

# 定义配置文件的名称，程序会自动在同目录下生成这个文件
CONFIG_FILE = "button_config.json"

# 定义默认的按钮数据，作为备用
DEFAULT_BUTTONS = [
    ("首页", "000"),
    ("连板", "lbtt"),
    ("数货币", "szhb"),
    ("光刻", "gkj"),
    ("商业航", "syht"),
    ("无人驾", "wrjs"),
    ("黄金", "hjgn"),
    ("核电", "hdhn"),
    ("人形", "rxjqr"),
    ("存储", "ccxp"),
    ("期货", "qhlx"),
]


class TDXAutomation:
    def __init__(self, window_title="通达信"):
        self.window_title = window_title

    def focus_window_simple(self):
        """简单方法：通过alt+tab切换窗口"""
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.3)
        return True

    def open_keyboard_wizard(self, code="000"):
        """打开键盘精灵并输入指定代码 + 回车"""
        self.focus_window_simple()
        time.sleep(0.1)

        # 输入指定代码，时间间隔
        pyautogui.write(code, interval=0.1)
        time.sleep(0.1)
        pyautogui.press('enter')


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.arrangement = "vertical"  # 默认竖列排列

        # 【修改点1】程序启动时，尝试从文件加载按钮数据
        self.buttons = self.load_buttons()

        self.button_widgets = []  # 存储按钮组件

        self.master.title("一键直达板块")
        self.master.configure(bg='#f0f0f0')
        self.master.attributes('-topmost', True)  # 窗口置顶
        self.pack(fill=tk.BOTH, expand=True)
        self.tdx = TDXAutomation()  # 创建一次实例

        # 使窗口可移动
        self.master.overrideredirect(True)  # 隐藏标题栏

        # 创建标题栏框架
        self.title_frame = tk.Frame(self, bg='#e0e0e0', height=30)
        self.title_frame.pack(fill=tk.X)
        self.title_frame.bind('<Button-1>', self.start_move)
        self.title_frame.bind('<B1-Motion>', self.on_motion)
        self.title_frame.bind('<ButtonRelease-1>', self.stop_move)

        # 添加关闭按钮
        self.close_button = tk.Button(self.title_frame, text="X", command=self.master.destroy,
                                      bg='red', fg='white', font=('Arial', 10, 'normal'),
                                      width=2, height=1)
        self.close_button.pack(side=tk.RIGHT, padx=2, pady=2)

        # 添加排列方式切换按钮
        self.arrange_button = tk.Button(self.title_frame, text="横排",
                                        command=self.toggle_arrangement,
                                        bg='#e0e0e0', fg='black', font=('Arial', 10, 'normal'),
                                        width=4, height=1, relief=tk.FLAT)
        self.arrange_button.pack(side=tk.LEFT, padx=5, pady=2)

        # 创建按钮容器
        self.button_frame = tk.Frame(self, bg='#f0f0f0')
        self.button_frame.pack(fill=tk.BOTH, expand=True)

        self.x = 0
        self.y = 0
        self.create_widgets()
        self.adjust_window_size()

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def on_motion(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.master.winfo_x() + deltax
        y = self.master.winfo_y() + deltay
        self.master.geometry(f"+{x}+{y}")

    def stop_move(self, event):
        pass

    # 【新增方法】从 JSON 文件加载按钮配置
    def load_buttons(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 简单的校验，确保数据格式正确
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        return DEFAULT_BUTTONS  # 如果文件不存在或读取失败，返回默认值

    # 【新增方法】保存按钮配置到 JSON 文件
    def save_buttons(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.buttons, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def toggle_arrangement(self):
        """切换按钮排列方式（竖列/横列）"""
        if self.arrangement == "vertical":
            self.arrangement = "horizontal"
            self.arrange_button.config(text="竖排")
        else:
            self.arrangement = "vertical"
            self.arrange_button.config(text="横排")
        self.recreate_widgets()
        self.adjust_window_size()

    def create_widgets(self):
        """创建所有按钮"""
        self.button_widgets = []
        for text, code in self.buttons:
            self.create_button(text, code)

    def recreate_widgets(self):
        """重新创建所有按钮，用于切换排列方式"""
        # 先删除现有按钮
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        self.button_widgets = []
        # 重新创建按钮
        self.create_widgets()

    def create_button(self, text, code):
        """创建单个按钮并添加到界面"""
        # 根据排列方式决定按钮文字方向
        if self.arrangement == "horizontal":
            # 横列时，将文字设置为竖直方向显示
            vertical_text = '\n'.join(list(text))
            btn = tk.Button(self.button_frame, text=vertical_text,
                            command=lambda c=code: self.execute_tdx(c),
                            bg='#343C4C', fg='white', font=('黑体', 11, 'bold'),
                            relief=tk.RAISED, bd=2, width=2, height=8)
        else:
            # 竖列时，正常显示
            btn = tk.Button(self.button_frame, text=text,
                            command=lambda c=code: self.execute_tdx(c),
                            bg='#343C4C', fg='white', font=('黑体', 11, 'bold'),
                            relief=tk.RAISED, bd=2, width=8, height=2)

        # 根据排列方式放置按钮
        if self.arrangement == "vertical":
            btn.pack(pady=5, padx=10, fill=tk.X)
        else:
            btn.pack(side=tk.LEFT, pady=5, padx=5)

        # 绑定右键菜单
        btn.bind("<Button-3>", lambda e, b=btn, t=text, c=code: self.show_context_menu(e, b, t, c))

        self.button_widgets.append(btn)
        return btn

    def show_context_menu(self, event, button, text, code):
        """显示右键菜单"""
        # 创建菜单
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="添加直达板块", command=self.add_button)
        menu.add_command(label="删除直达板块", command=lambda: self.delete_button(text, code))

        # 在鼠标位置显示菜单
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def add_button(self):
        """添加新按钮"""
        # 获取用户输入
        text = simpledialog.askstring("输入", "请添加板块名称:")
        if not text:
            return

        code = simpledialog.askstring("输入", "请输入板块对应的代码（限英文或数字）:")
        if not code:
            return

        # 添加到按钮列表
        self.buttons.append((text, code))

        # 【修改点2】添加后立即保存
        self.save_buttons()

        # 创建新按钮
        self.create_button(text, code)
        # 调整窗口大小
        self.adjust_window_size()

    def delete_button(self, text, code):
        """删除按钮"""
        # 确认删除
        if messagebox.askyesno("确认", f"请确定要删除 {text} 吗?"):
            # 从列表中移除
            self.buttons = [(t, c) for t, c in self.buttons if not (t == text and c == code)]

            # 【修改点3】删除后立即保存
            self.save_buttons()

            # 重新创建所有按钮
            self.recreate_widgets()
            # 调整窗口大小
            self.adjust_window_size()

    def adjust_window_size(self):
        """根据按钮数量和排列方式调整窗口大小"""
        # 等待所有组件更新
        self.master.update_idletasks()

        title_height = 30  # 标题栏高度
        padding = 10  # 内边距

        if self.arrangement == "vertical":
            # 竖列排列：宽度固定，高度根据所有按钮的总高度计算
            if self.button_widgets:
                total_height = 0
                for btn in self.button_widgets:
                    total_height += btn.winfo_reqheight() + 10  # 10是pady间距

                window_width = 100
                window_height = title_height + total_height + padding * 2
            else:
                window_width = 100
                window_height = title_height + 50
        else:
            # 横列排列：高度固定，宽度根据所有按钮的总宽度计算
            if self.button_widgets:
                total_width = 0
                for btn in self.button_widgets:
                    total_width += btn.winfo_reqwidth() + 8

                window_width = total_width + padding * 2
                window_height = title_height + 80
            else:
                window_width = 150
                window_height = title_height + 80

        # 获取当前位置
        current_x = self.master.winfo_x()
        current_y = self.master.winfo_y()

        # 设置窗口大小
        self.master.geometry(f"{window_width}x{window_height}+{current_x}+{current_y}")

    def execute_tdx(self, code):
        # 延迟执行避免界面卡顿
        self.after(100, lambda: self.tdx.open_keyboard_wizard(code))


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()
