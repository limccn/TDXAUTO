# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TDXAUTO (通达信自动化交易助手) is a Windows-based Chinese stock trading automation system built around the TDX (通达信) trading terminal. It consists of multiple GUI tools written in Python that automate trading, fetch market data, analyze sector heat/concept overlap, and compute real-time market sentiment indicators.

**Important context:** This codebase runs exclusively on Windows and depends on the TDX trading terminal being installed and running. Much of the automation relies on Windows API calls (win32gui, pywinauto, pyautogui) to interact with the TDX GUI.

## Common Commands

### Run the main applications

```bash
# Main strategy manager GUI (超级股票助手)
python tdx_auto.py

# Standalone trading panel (一键下单M版 / pywin32版)
python tdx_auto_trader.py

# Market sentiment analysis GUI (大盘情绪分析)
python tdx_emo.py

# Sector/concept heat analysis GUI (概念热度分析)
python hot_blk.py
```

### Data update pipeline

```bash
# Run the full daily data update (龙虎榜, 涨停股, 热榜, 基金, 板块指数, etc.)
python data_update.py
```

### Build EXEs (PyInstaller)

```bash
# Main strategy manager
python 打包成exe文件.py

# Pro trading panel
python 打包EXE.py
```

### Environment

```bash
# Install dependencies
pip install -r requirements.txt
# OR
uv pip install -r requirements.txt
```

Requires Python >= 3.11. Key dependencies: PyQt5, pywin32, pywinauto, pyautogui, pandas, akshare, mootdx, matplotlib.

## High-Level Architecture

### Module Categories

**1. Strategy & Trading Core**
- `tdx_auto.py` — Main PyQt5 GUI for managing trading strategies. Supports two modes:
  - *Single stock mode*: Individual stock strategies with conditions (price, percentage change, immediate trade, TDX alert).
  - *File mode*: Scans `.blk` files (通达信板块 files) for new stock codes and auto-imports them as running strategies.
  - Fetches real-time prices from Sina Finance (primary) and East Money (fallback) via `requests`.
  - Triggers are evaluated every ~2 seconds for running strategies.
  - On trigger, writes a command to `tdx_cmd.txt` (format: `CODE:<code>\nCMD:<cmd>\n`) and calls `link_tdx(code)` to bring up the stock in TDX.
- `tdx_auto_trader.py` — Standalone tkinter trading panel. Reads `tdx_cmd.txt` in a polling loop and executes trades by sending Windows keystrokes (win32api) to the TDX window (F9=buy, F10=sell, Ctrl+F1~F4 for position sizes).
- `tdx_order.py` — Alternative pywinauto-based trading executor with coordinate-based clicking on the TDX "闪电买入" window.
- `link_tdx.py` — Sends stock codes to TDX via Windows `PostMessageA` using a registered "Stock" window message. Also handles writing codes to `.blk` files.

**2. Strategy Configuration**
- `add_buy_st.py` / `add_sell_st.py` — PyQt5 dialogs for configuring buy/sell strategies. Support up to 4 independent batches per strategy, with stacked widgets switching between price-based and percentage-based conditions. Emit `st_saved` signal back to the main window.

**3. Data Layer (`data_update.py`)**
- A monolithic class `update` that orchestrates daily data fetching:
  - **龙虎榜 (Dragon Tiger List)**: `lhb_list()`, `lhb_stock_detail()`, `batch_lhb()` — uses `akshare` to fetch and deduplicates by `[上榜日, 代码]`.
  - **涨停股 (Limit-up stocks)**: `fetch_zt_data()`, `get_limit_up_stocks()` — scrapes from xuangubao API.
  - **热榜 (Hot rankings)**: `ths()`, `cls()`, `tdx()`, `em()` — fetches top 50 hot stocks from TongHuaShun, CaiLianShe, TDX, East Money.
  - **基金 (Funds)**: `fund_daily()`, `fund_etf_and_lof()`, `etf_jz()` — ETF/LOF net value and pricing data.
  - **板块指数 (Sector indices)**: `blk_rate()` — reads TDX daily data via `mootdx.reader.Reader`.
  - **所属概念 (Concepts)**: `update_stock_concepts()` — parses `T0002/hq_cache/infoharbor_block.dat` from TDX to extract stock-to-concept mappings.
  - **异动解析 (Anomaly parsing)**: `ztjx()` — parses downloaded HTML from 韭研公社.
- Data is persisted in `data/` as CSV files with `utf-8-sig` encoding for Excel compatibility.

**4. Market Sentiment (`tdx_emo.py`, `emo_simple.py`, `ak_simple.py`)**
- `tdx_emo.py` — PyQt5 GUI with matplotlib charting. Uses `DataDownloadThread` (wraps `ak_simple.data_his`) and `EmoCalculationThread` (wraps `emo_simple.emo_doctor`) running concurrently.
- The GUI displays multi-line time-series charts of emotion indicators (涨停数量, 炸板率, M上涨率, etc.) with hover tooltips.
- Checkbox filter states are saved/restored from `tdx_emo.json`.

**5. Sector Heat Analysis (`hot_blk.py`)**
- PyQt5 GUI that loads `data/stock_gn.csv` (stock concepts) and `data/news_stat.csv` into memory.
- Auto-scans a configured `.blk` file (from `setup.json`) every 5 seconds for new stock codes and adds them to the analysis table.
- Computes concept overlap frequency across selected rows and highlights emphasized concepts (configured in `setup.json` as `yesword`).
- Double-clicking a stock code sends it to TDX via `link_tdx`.

### Key Configuration Files

| File | Purpose |
|------|---------|
| `setup.txt` / `setup.json` | TDX executable path, TDX data directory, desktop path, API keys, sector emphasis words |
| `setup.sample.json` | Template showing expected JSON structure |
| `tdx_auto.json` | Persistent strategy list for `tdx_auto.py` (stock + file strategies, last_run_date) |
| `stock_total.txt` | Valid 6-digit stock codes loaded at startup for validation |
| `gui_config.txt` | Trading panel button labels and colors |
| `set_key.txt` | Space-separated words to exclude from concept heat analysis |
| `tdx_cmd.txt` | File-based IPC between strategy manager and trading executor |
| `tdx_emo.json` | Saved checkbox filter states for sentiment GUI |
| `strategies.json` / `strategies1.json` | Strategy definitions |
| `operation_log.csv` / `strategy_total_log.csv` | Runtime logs |

### TDX Integration Patterns

There are **three distinct mechanisms** for interacting with TDX:

1. **File-based command IPC**: `tdx_auto.py` writes `tdx_cmd.txt`; `tdx_auto_trader.py` polls and reads it, renaming to `tdx_cmd_processing.txt` to avoid race conditions.
2. **Windows message broadcasting**: `link_tdx.py` registers a "Stock" message and posts `wParam = 6000000 + code_int` (or 7000000/4000000 for different markets) to `HWND_BROADCAST` to tell TDX to switch to a stock.
3. **GUI automation**: `tdx_auto_trader.py` uses `win32api.keybd_event` to send F9/F10/Ctrl+Fx keystrokes. `tdx_order.py` uses `pywinauto` and coordinate-based `pyautogui.click`. `tdx_soft.py` uses simple `pyautogui.write` + Enter.

### Data Flow

```
TDX terminal  <--Windows messages/GUI automation-->  Trading executors (tdx_auto_trader.py / tdx_order.py)
       ^
       | reads/writes .blk files
       |
Strategy manager (tdx_auto.py)  --writes--> tdx_cmd.txt
       |                                    ^
       | fetches prices                    | polls
       v                                   |
Sina/East Money APIs               Trading executor
       |
       v
data_update.py --fetches--> akshare / requests / mootdx --> data/*.csv
       |
       v
hot_blk.py / tdx_emo.py (read data/*.csv for display/analysis)
```

### Encoding Conventions

- CSV files are almost always written with `encoding='utf-8-sig'` (for Excel compatibility) or `gbk` (for TDX compatibility).
- `setup.txt` uses `utf-8`; TDX `.blk` files use `gbk`.
- Stock codes are consistently zero-padded to 6 digits as strings (`str.zfill(6)`).

### Threading Model

- `tdx_auto.py` uses `QThreadPool` + `QRunnable` for async stock price fetching (one runnable per code, timer-driven queue processing).
- `tdx_emo.py` uses `QThread` subclasses for data download and emotion calculation, communicating via `pyqtSignal`.
- `tdx_auto_trader.py` uses `tkinter.after(500, check_queue)` for polling the command file.

### Strategy State Machine

Strategies in `tdx_auto.py` have states:
- **Single stock**: `运行` (running), `暂停` (paused), `结束` (ended)
- **File mode**: `扫描` (scanning), `停止` (stopped)
- Auto-cleanup: Ended strategies are capped at 3 per stock code, older ones removed daily.
- Trigger cooldown: 300 seconds between triggers for the same strategy key.
- Command cooldown: 8 seconds minimum between consecutive trade commands to prevent over-trading.
