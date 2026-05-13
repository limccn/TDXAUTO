# 一键直达个股.py
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import pyautogui
import time
import tkinter as tk
from tkinter import messagebox
import pyautogui
import time
import win32gui
import win32con

#跳转到个股页面



class reach():
    def __init__(self, window_title="通达信"):
        self.window_title = window_title

    def focus_window_simple(self):
        """简单方法：通过alt+tab切换窗口"""
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.2)
        return True

    def open_stock(self, code):
        """打开键盘精灵并输入指定个股代码 + 回车"""
        self.focus_window_simple()
        time.sleep(0.2)

        # 输入指定代码，时间间隔
        pyautogui.write(code, interval=0.05)
        time.sleep(0.3)
        pyautogui.press('enter')
        time.sleep(0.3)



if __name__ == "__main__":
    reach().open_stock( code = '300650')