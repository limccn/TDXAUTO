# 键盘输入.py（改进后）

import pyautogui
import time
import os
import sys

class TDXAutomation:
    def __init__(self, window_title="通达信"):
        self.window_title = window_title

    def focus_window_simple(self):
        """简单方法：通过alt+tab切换窗口"""
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.3)
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active and self.window_title in active.title:
                print(f"已激活窗口: {active.title}")
                return True
        except:
            pass
        return True

    def open_keyboard_wizard(self, code="000"):
        """打开键盘精灵并输入指定代码 + 回车"""
        self.focus_window_simple()
        time.sleep(0.3)

        # 输入指定代码，时间间隔
        pyautogui.write(code, interval=0.1)
        time.sleep(0.1)
        pyautogui.press('enter')

    # 其他方法保持不变...
    def alternative_methods(self):
        methods = [self.method_direct_keys, self.method_alt_menu, self.method_coordinates]
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
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'k')
        time.sleep(0.5)
        pyautogui.write('111')
        time.sleep(0.2)
        pyautogui.press('enter')
        return True

    def method_alt_menu(self):
        print("此方法需要手动配置快捷键")
        return False

    def method_coordinates(self):
        print("需要先录制坐标位置")
        return False

    def setup_assistant(self):
        print("\n=== 通达信自动化设置助手 ===")
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        x, y = pyautogui.position()
        print(f"当前位置坐标: ({x}, {y})")
        config = f"""# 通达信自动化配置
keyboard_wizard_x = {x}
keyboard_wizard_y = {y}
shortcut = 'ctrl+k'
"""
        with open('tdx_config.py', 'w', encoding='utf-8') as f:
            f.write(config)
        print("配置已保存到 tdx_config.py")
        return x, y

    def run_from_config(self, code="111"):
        try:
            import tdx_config
            x = tdx_config.keyboard_wizard_x
            y = tdx_config.keyboard_wizard_y
            print(f"使用配置坐标: ({x}, {y})")
            pyautogui.click(x, y)
            time.sleep(0.5)
            pyautogui.write(code)
            time.sleep(0.3)
            pyautogui.press('enter')
            return True
        except:
            print("未找到配置，使用默认方法")
            return self.open_keyboard_wizard(code)

def install_requirements():
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

def main():
    try:
        import pyautogui
    except ImportError:
        print("缺少必要库，开始安装...")
        install_requirements()

    tdx = TDXAutomation()
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