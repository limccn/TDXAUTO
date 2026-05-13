import json
import os
from openai import OpenAI


def load_config():
    try:
        with open('setup.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None



def check_ai():
    print('\n' + '=' * 50)
    print('测试大模型是否正常')
    print('=' * 50)

    config = load_config()
    if not config:
        return

    api_key = config.get('OPENAI_API_KEY')
    model_name = config.get('OPENAI_MODEL')
    base_url = config.get('OPENAI_BASE_URL')

    if not api_key:
        return

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': '我正在测试所用的大模型是否正常运行，请告诉我你的模型名称。只说具体的名称和具体的版本，其它的都不需要说明。'}
            ]
        )
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"错误信息：{e}")


# ========== 入口调度逻辑 ==========
if __name__ == "__main__":
    # check()
    # #测试千问3
    check_ai()
    # 测试3.5