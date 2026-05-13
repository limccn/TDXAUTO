import ctypes
import os
from ctypes import wintypes
import json
# 新增导入：用于弹窗交互
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QComboBox

# 全局缓存已注册的消息 ID，避免重复注册
_STOCK_MSG_ID = None
user32 = ctypes.windll.user32
HWND_BROADCAST = 0xFFFF


def link_tdx(code: str) -> bool:
    """发送消息给通达信"""
    global _STOCK_MSG_ID

    # 输入校验
    if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        print(f"❌ 无效股票代码: {code}")
        return False
    code_int = int(code)

    # 构造 wParam
    if code.startswith('6') or code.startswith('8') or code.startswith('5') or code.startswith('11'):
        wParam = 7000000 + code_int
    elif code.startswith('9') or code.startswith('43'):
        wParam = 4000000 + code_int
    else:
        wParam = 6000000 + code_int

    # 注册消息
    if _STOCK_MSG_ID is None:
        user32.RegisterWindowMessageA.argtypes = [wintypes.LPCSTR]
        user32.RegisterWindowMessageA.restype = wintypes.UINT
        _STOCK_MSG_ID = user32.RegisterWindowMessageA(b"Stock")
        if _STOCK_MSG_ID == 0:
            print("⚠️ 注册 'Stock' 消息失败")
            return False

    # 发送消息
    user32.PostMessageA.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageA.restype = wintypes.BOOL
    success = user32.PostMessageA(HWND_BROADCAST, _STOCK_MSG_ID, wParam, 0)

    if success:
        print(f"✅ 已发送股票代码 {code} 到通达信 (wParam={wParam})")
    else:
        err = ctypes.get_last_error()
        print(f"❌ 发送失败，错误码: {err}")
    return bool(success)


def get_tdx_path():
    """读取 setup.json 获取通达信路径"""
    config_file = 'setup.json'
    tdx_path = ""
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                tdx_path = config.get('TDX_PATH', '').strip()
                if tdx_path:
                    print(f"✅ 通达信路径已加载: {tdx_path}")
        except Exception as e:
            print(f"⚠️ 读取 setup.json 失败: {e}")
    return tdx_path


def format_stock_code_for_blk(code):
    """格式化代码为blk文件格式"""
    code = str(code).strip()
    if not code:
        return None
    prefix = '1' if code.startswith('6') else '0'
    return (prefix + code).zfill(7)


def add_codes_to_blk(tdx_path, codes, clear_before_add):
    """将代码写入blk文件 (独立函数版本)"""
    if not tdx_path:
        QMessageBox.warning(None, "错误", "未配置通达信路径，请检查 setup.json 中的 TDX_PATH")
        return

    blk_dir = os.path.join(tdx_path, 'T0002', 'blocknew')
    if not os.path.exists(blk_dir):
        QMessageBox.warning(None, "错误", f"板块目录不存在: {blk_dir}")
        return

    try:
        blk_files = [f for f in os.listdir(blk_dir) if f.endswith('.blk')]
    except Exception as e:
        QMessageBox.warning(None, "错误", f"无法读取板块目录: {e}")
        return

    if not blk_files:
        QMessageBox.information(None, "提示", "板块目录下没有 .blk 文件")
        return

    # 弹出选择框
    dialog = QInputDialog()
    dialog.setWindowTitle("选择板块")
    dialog.setLabelText("请选择目标板块文件:")
    dialog.setComboBoxItems(blk_files)
    dialog.setComboBoxEditable(False)
    dialog.resize(300, 400)

    combo_box = dialog.findChild(QComboBox)
    if combo_box:
        combo_box.setMaxVisibleItems(30)
        combo_box.setStyleSheet("QComboBox { font-size: 14px; padding: 5px; }")

    ok = dialog.exec_()
    file_name = dialog.textValue()

    if not ok or not file_name:
        return

    file_path = os.path.join(blk_dir, file_name)

    # 格式化代码
    formatted_codes = []
    for code in codes:
        f_code = format_stock_code_for_blk(code)
        if f_code:
            formatted_codes.append(f_code)
    formatted_codes = list(set(formatted_codes))

    try:
        existing_codes = set()
        if not clear_before_add and os.path.exists(file_path):
            with open(file_path, 'r', encoding='gbk') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing_codes.add(line)

        final_codes = existing_codes.union(set(formatted_codes))

        with open(file_path, 'w', encoding='gbk') as f:
            for code in final_codes:
                f.write(code + '\n')

        action_text = "清空并加入" if clear_before_add else "加入"
        print(f"✅ 已{action_text}板块 {file_name}: {formatted_codes}")
        QMessageBox.information(None, "完成", f"已{action_text} {len(formatted_codes)} 个代码到 {file_name}")

    except Exception as e:
        QMessageBox.critical(None, "错误", f"写入文件失败: {e}")


if __name__ == "__main__":
    link_tdx("002261")
