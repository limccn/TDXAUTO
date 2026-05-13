#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通达信“沪深京日线数据完整包”自动下载与解压脚本（指定下载路径版）
流程：
  1. 用 Chrome 打开通达信页面完成 JS 挑战
  2. 强制让浏览器把 ZIP 直接下载到 {TDX_PATH}/vipdoc 目录
  3. 解压到 vipdoc
  4. 删除原 ZIP
"""

import json
import os
import sys
import time
import zipfile
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# ============ 配置 ============
SETUP_JSON = "setup.json"                             # 存 TDX_PATH 的 JSON
VIPDOC_SUBDIR = "vipdoc"
ZIP_FILENAME = "hsjday.zip"
VIPDATA_PAGE_URL = "https://www.tdx.com.cn/article/vipdata.html"  # 官方页面
HSJDAY_ZIP_URL = "https://data.tdx.com.cn/vipdoc/hsjday.zip"

# 如果你的 chromedriver 不在 PATH，可以在这里指定路径（为 None 则让 Selenium 自己找）
CHROMEDRIVER_PATH = None
# ================================


def load_tdx_path_from_json(json_path: str) -> str:
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"配置文件不存在：{json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    tdx_path = cfg.get("TDX_PATH")
    if not tdx_path or not isinstance(tdx_path, str):
        raise ValueError(f"{json_path} 中缺少 'TDX_PATH' 字段或值不是字符串")
    return tdx_path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def unzip_into(zip_path: Path, dest_dir: Path) -> None:
    if not zipfile.is_zipfile(zip_path):
        raise zipfile.BadZipFile(f"不是有效的 ZIP 文件：{zip_path}")
    print(f"[解压] 开始解压：{zip_path}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(path=dest_dir)
    print("[解压] 解压完成。")


def delete_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
        print(f"[清理] 已删除文件：{path}")
    except Exception as e:
        print(f"[清理] 删除失败（可手动删除）：{path}，原因：{e}", file=sys.stderr)


def download_hsjday_via_browser(save_dir: Path, timeout_sec: int = 120) -> Path:
    """
    用 Selenium 打开通达信官方页面完成 JS 挑战，然后下载 hsjday.zip 到指定目录
    """
    out_zip = save_dir / ZIP_FILENAME

    opts = Options()
    # opts.add_argument("--headless=new")  # 后台运行时取消注释
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # ================= 核心修改：强制指定下载路径 =================
    prefs = {
        "download.default_directory": str(save_dir.resolve()),  # 强制保存到 vipdoc
        "download.prompt_for_download": False,                  # 不弹出保存对话框
        "download.directory_upgrade": True,                     # 禁用旧版下载路径警告
        "safebrowsing.enabled": True                            # 允许下载
    }
    opts.add_experimental_option("prefs", prefs)
    # ===========================================================

    driver = None
    try:
        service = Service(executable_path=CHROMEDRIVER_PATH) if CHROMEDRIVER_PATH else Service()
        driver = webdriver.Chrome(service=service, options=opts)

        # 1. 打开官方页面完成挑战
        print("[浏览器] 正在打开个人行情数据页面，以完成 JS 挑战...")
        driver.get(VIPDATA_PAGE_URL)
        WebDriverWait(driver, timeout_sec).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '沪深京日线数据完整包')]"))
        )
        time.sleep(3)  # 确保 Cookie 写入完毕

        # 2. 跳转下载
        print(f"[浏览器] 开始下载 ZIP，将直接保存至：{save_dir}")
        driver.get(HSJDAY_ZIP_URL)

        # 3. 轮询等待文件下载完成
        wait_interval = 1.0
        elapsed = 0.0
        prev_size = -1
        stable_count = 0
        required_stable = 3

        while elapsed < timeout_sec:
            if out_zip.exists():
                curr_size = out_zip.stat().st_size
                if curr_size == prev_size and curr_size > 0:
                    stable_count += 1
                    if stable_count >= required_stable:
                        print(f"[浏览器] 下载完成（大小：{curr_size} 字节）")
                        break
                else:
                    prev_size = curr_size
                    stable_count = 0
            time.sleep(wait_interval)
            elapsed += wait_interval
        else:
            raise TimeoutError(f"下载超时（等待 {timeout_sec} 秒）：{out_zip}")

        # 4. 安全校验：是否为真正的 ZIP
        with open(out_zip, "rb") as f:
            head = f.read(4)
        if head[:2] != b"PK":
            raise RuntimeError("下载的文件不是 ZIP（头部不是 PK），可能被拦截。")

        return out_zip

    finally:
        if driver:
            driver.quit()


def main() -> None:
    try:
        # 1) 读取配置
        tdx_path = load_tdx_path_from_json(SETUP_JSON)
        print(f"[配置] TDX_PATH：{tdx_path}")

        base_dir = Path(tdx_path)
        if not base_dir.is_dir():
            raise NotADirectoryError(f"TDX_PATH 指向的目录不存在：{tdx_path}")

        # 2) 确定输出目录：{TDX_PATH}/vipdoc
        vipdoc_dir = ensure_dir(base_dir / VIPDOC_SUBDIR)

        # 3) 通过浏览器下载 ZIP（这次会直接存到 vipdoc_dir 里）
        zip_path = download_hsjday_via_browser(vipdoc_dir)

        # 4) 解压到 vipdoc
        unzip_into(zip_path, vipdoc_dir)

        # 5) 删除原 ZIP
        delete_file(zip_path)

        print("全部完成。")

    except Exception as e:
        print(f"执行失败：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
