#!/usr/bin/env python3
"""
自动打包脚本
"""
import os
import subprocess
import shutil


def build_exe():
    # 清理之前的构建
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')

    # 打包命令
    cmd = [
        'pyinstaller',
        '--onefile',  # 单个exe
        '--icon=app4.ico',  # 图标
        '--windowed',

        # 1. 显式声明包含 tdx_auto_trader.py 文件
        '--add-data=tdx_auto_trader.py;.',
        '--add-data=add_buy_st.py;.',
        '--add-data=add_sell_st.py;.',
        '--add-data=get_price_from_mootdx.py;.',
        '--add-data=hot_blk.py;.',

        # 2. 【关键修复】显式声明所有自定义模块的 hidden-import
        # 因为 add_buy_st 和 add_sell_st 仅在运行时动态导入，
        # 且 tdx_auto_trader 也依赖 tkinter 和 pywin32，必须显式声明。
        '--hidden-import=tdx_auto_trader',
        '--hidden-import=add_buy_st',  # 必须：主程序依赖此模块
        '--hidden-import=add_sell_st',  # 必须：主程序依赖此模块
        '--hidden-import=get_price_from_mootdx',  # 必须：主程序依赖此自定义模块
        '--hidden-import=mootdx',  # 必须：主程序依赖此库
        '--hidden-import=tdx_auto_statics',

        # 3. 之前修复的 win32/tkinter 依赖
        '--hidden-import=tkinter',
        '--hidden-import=win32process',
        '--hidden-import=win32gui',
        '--hidden-import=win32api',
        '--hidden-import=win32con',
        '--hidden-import=pyautogui',

        # 4. 强制收集 tkinter 的所有子模块（解决 can.not import name 'ttk' 错误）
        '--collect-submodules=tkinter',
        '--collect-data=tkinter',

        # 5. 【新增】打包图片和声音文件夹（否则运行时找不到资源）
        '--add-data=image;.',
        '--add-data=sounds;.',


        '--name=TDX全自动交易-超级股票助手',  # 程序名
        '--clean',  # 清理临时文件
        '--noconsole',
        'tdx_auto.py'
    ]

    # 执行打包
    print("开始打包...")

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

    # 打印 PyInstaller 的详细日志
    print("\n=== PyInstaller 输出日志 ===")
    print(result.stdout)
    print("=== PyInstaller 错误日志 ===")
    print(result.stderr)
    print("============================\n")

    # 检查结果
    exe_name = 'TDX全自动交易-超级股票助手.exe'
    if os.path.exists(f'dist/{exe_name}'):
        print("✓ 打包成功！")
        print(f"文件位置: {os.path.abspath(f'dist/{exe_name}')}")
    else:
        print("✗ 打包失败，请查看上方的错误日志")


if __name__ == '__main__':
    build_exe()
