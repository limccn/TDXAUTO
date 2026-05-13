import pyautogui
import time
import os
import sys


class TDXAutomation:


    def __init__(self, window_title="通达信"):
        self.window_title = window_title

    def focus_window_simple(self):
        """简单方法：通过alt+tab切换窗口"""
        # 先按alt+tab切换到通达信
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.5)

        # 检查当前活动窗口
        try:
            # 尝试获取活动窗口
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active and self.window_title in active.title:
                print(f"已激活窗口: {active.title}")
                return True
        except:
            pass

        # print("请确保通达信窗口已打开并在后台")
        return True

    def open_keyboard_wizard(self):
        """打开键盘精灵并输入111回车"""
        # print("开始执行通达信自动化操作...")

        # 方法1：尝试激活窗口
        self.focus_window_simple()
        time.sleep(0.5)

        # 方法2：使用快捷键打开键盘精灵
        # 通达信常用快捷键：
        # Ctrl+K: 键盘精灵
        # 60: 分钟K线
        # 000: 大盘指数

        # print("按下Ctrl+K打开键盘精灵...")
        # pyautogui.hotkey('ctrl', 'k')
        # time.sleep(0.5)

        # 输入111

        """输入股票代码的函数，可供其他文件调用"""
        # print(f"输入111...")
        pyautogui.write('gkja', interval=0.2)
        time.sleep(0.2)

        # 按回车
        # print("按下回车键...")
        pyautogui.press('enter')

        # print("操作完成！")

    def alternative_methods(self):
        """备用方法集合"""
        methods = [
            self.method_direct_keys,
            self.method_alt_menu,
            self.method_coordinates
        ]

        for method in methods:
            print(f"尝试方法: {method.__name__}")
            try:
                if method():
                    return True
            except Exception as e:
                print(f"方法失败: {e}")
                time.sleep(1)

        return False

    def method_direct_keys(self):
        """直接发送按键序列"""
        # 切换到通达信
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.5)

        # 直接发送Ctrl+K, 111, Enter
        pyautogui.hotkey('ctrl', 'k')
        time.sleep(0.5)
        pyautogui.write('111')
        time.sleep(0.2)
        pyautogui.press('enter')
        return True

    def method_alt_menu(self):
        """使用Alt菜单导航"""
        # 通达信菜单快捷键通常是Alt+菜单项的首字母
        # 但需要知道具体菜单结构
        print("此方法需要手动配置快捷键")
        return False

    def method_coordinates(self):
        """使用坐标点击（需要预先录制）"""
        print("需要先录制坐标位置")
        # 示例：pyautogui.click(x=100, y=100)  # 菜单位置
        # pyautogui.write('111')
        # pyautogui.click(x=200, y=200)  # 确定按钮位置
        return False

    def setup_assistant(self):
        """设置助手，帮助用户配置"""
        # print("\n=== 通达信自动化设置助手 ===")
        # print("1. 请确保通达信软件已打开")
        # print("2. 将鼠标移动到键盘精灵按钮上")
        # print("3. 等待3秒获取坐标...")
        # input("按Enter开始获取坐标...")
        #
        # print("获取坐标倒计时：")
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)

        x, y = pyautogui.position()
        print(f"当前位置坐标: ({x}, {y})")

        # 保存配置
        config = f"""# 通达信自动化配置
keyboard_wizard_x = {x}
keyboard_wizard_y = {y}
shortcut = 'ctrl+k'
"""

        with open('tdx_config.py', 'w', encoding='utf-8') as f:
            f.write(config)

        print("配置已保存到 tdx_config.py")
        return x, y

    def run_from_config(self):
        """从配置运行"""
        try:
            # 尝试导入配置
            import tdx_config
            x = tdx_config.keyboard_wizard_x
            y = tdx_config.keyboard_wizard_y

            print(f"使用配置坐标: ({x}, {y})")

            # 点击指定位置
            pyautogui.click(x, y)
            time.sleep(0.5)
            pyautogui.write('111')
            time.sleep(0.3)
            pyautogui.press('enter')

            return True
        except:
            print("未找到配置，使用默认方法")
            return self.open_keyboard_wizard()


# 安装所需库的辅助函数
def install_requirements():
    """安装必要的库"""
    requirements = ['pyautogui', 'pygetwindow']

    print("正在安装所需库...")
    for package in requirements:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"正在安装 {package}...")
            os.system(f"{sys.executable} -m pip install {package}")

    print("安装完成！")


# 主程序
def main():
    # print("通达信自动化工具 v1.0")
    # print("=" * 30)

    # 检查并安装库
    try:
        import pyautogui
    except ImportError:
        print("缺少必要库，开始安装...")
        install_requirements()

    # 创建自动化对象
    tdx = TDXAutomation()

    # print("\n请选择操作模式：")
    # print("1. 自动执行（推荐）")
    # print("2. 设置助手（首次使用）")
    # print("3. 从配置运行")
    # print("4. 测试快捷键")

    # choice = input("请输入选择 (1-4): ").strip()
    choice = 1
    try:
        if choice == '1':
            print("\n正在执行自动化操作...")
            print("注意：请确保通达信已打开并在后台")
            input("按Enter键开始（3秒后开始操作）...")
            time.sleep(3)
            tdx.open_keyboard_wizard()

        elif choice == '2':
            tdx.setup_assistant()

        elif choice == '3':
            print("\n从配置运行...")
            input("按Enter键开始...")
            tdx.run_from_config()

        elif choice == '4':
            print("\n测试快捷键...")
            print("将测试 Ctrl+K 快捷键")
            input("按Enter测试（请观察通达信反应）...")
            pyautogui.hotkey('ctrl', 'k')
            print("如果键盘精灵打开，说明快捷键有效")

        else:
            print("使用默认模式...")
            tdx.open_keyboard_wizard()

    except Exception as e:
        print(f"执行出错: {e}")
        print("\n故障排除：")
        print("1. 确保通达信已打开")
        print("2. 尝试以管理员身份运行此脚本")
        print("3. 检查防火墙/杀毒软件设置")

    print("\n操作完成！")


if __name__ == "__main__":
    main()