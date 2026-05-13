import os
import re
import shutil

# 指定目标目录
directory = r"D:\360MoveData\Users\Administrator\Desktop"

# 编译正则表达式模式
pattern1 = re.compile(r'^.*数.*\.xls$')
pattern2 = re.compile(r'^全部Ａ股.*\.xls$')
# pattern3 = re.compile(r'^收盘.*\.xls$')



# 遍历目录中的所有文件
for filename in os.listdir(directory):
    if pattern1.match(filename) or pattern2.match(filename):
        file_path = os.path.join(directory, filename)
        try:
            os.remove(file_path)
            print(f"已删除: {file_path}")
        except Exception as e:
            print(f"无法删除 {file_path}: {e}")


directory2 = r"D:\project2\stock\data"

# 编译正则表达式模式
pattern11 = re.compile(r'^韭研公社-\d{4}-\d{2}-\d{2}异动_files$')
pattern12 = re.compile(r'^lof型开放式基金净值查询_基金数据_同花顺金融网_files$')
pattern13 = re.compile(r'^东方财富热榜_files$')

pattern21 = re.compile(r'^韭研公社-\d{4}-\d{2}-\d{2}异动\.html$')
pattern22 = re.compile(r'^lof型开放式基金净值查询_基金数据_同花顺金融网\.html$')
pattern23 = re.compile(r'^东方财富热榜\.html$')

pattern31 = re.compile(r'^in_html_.*\.html$')



# 遍历目录中的所有文件
for filename in os.listdir(directory2):
    if pattern11.match(filename) or pattern12.match(filename) or pattern31.match(filename) or pattern13.match(filename) or pattern21.match(filename) or pattern22.match(filename) or pattern23.match(filename):
        file_path = os.path.join(directory2, filename)
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
                print(f"已删除文件夹：{file_path}")
            else:
                os.remove(file_path)
                print(f"已删除：{file_path}")
        except Exception as e:
            print(f"无法删除 {file_path}: {e}")