import time
import pandas as pd


from mootdx import quotes


# 获取当前价格,股票名称,昨日价格
def get_current_price(code):

    symbol  = code
    current_price = quotes.StdQuotes().quotes(symbol)['price'].iloc[-1]
    return current_price
    print(current_price)


def get_stock_name(code):
    def extract_text_between_code_and_date(text):
        try:
            part1 = text.split("◇")[1]
            part2 = part1.split(" 更新日期：")[0]
            target_text = " ".join(part2.split(" ")[1:])
            return target_text
        except IndexError as e:
            print(f"字符串格式不匹配，提取失败：{e}")
            return ""

    symbol  = code
    F10 = quotes.StdQuotes().F10(symbol)['最新提示']
    stock_name = extract_text_between_code_and_date(F10)
    return stock_name
    print(stock_name)



def get_yesterday_price(code):



    yestoday_price = quotes.StdQuotes().get_k_data(code, start_date='2024-12-01', end_date='2036-01-04')['close'].iloc[-2]
    return yestoday_price
    print(yestoday_price)


if __name__ == "__main__":
    print(get_stock_name(code='300750'))
    print(get_yesterday_price(code='300750'))
    print(get_current_price(code='300750'))





