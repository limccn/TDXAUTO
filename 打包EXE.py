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
        '--icon=app3.ico',  # 图标
        '--windowed',



        '--name=TDX一键下单pro',  # 程序名
        '--clean',  # 清理临时文件
        '--noconsole',
        'tdx_auto_trader_b.py'
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
    exe_name = 'TDX一键下单pro.exe'
    if os.path.exists(f'dist/{exe_name}'):
        print("✓ 打包成功！")
        print(f"文件位置: {os.path.abspath(f'dist/{exe_name}')}")
    else:
        print("✗ 打包失败，请查看上方的错误日志")


if __name__ == '__main__':
    build_exe()
