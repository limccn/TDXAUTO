import requests
import json


def send_wechat(content):
    # 替换为你自己的企业微信机器人 Webhook 地址
    webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你自己的"

    data = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }

    response = requests.post(webhook_url, data=json.dumps(data))
    print(response.json())


def send_dingtalk(content):
    # 替换为你自己的钉钉群机器人 Webhook 地址 (包含 access_token)
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=你自己的"

    # 钉钉要求声明请求头为 JSON 格式
    headers = {
        "Content-Type": "application/json"
    }

    # 钉钉发送文本消息的 JSON 格式与企业微信一致
    data = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }

    # 发送 POST 请求
    response = requests.post(webhook_url, headers=headers, data=json.dumps(data))
    print("钉钉响应结果:", response.json())
if __name__ == '__main__':
    send_wechat("交易测试")
    send_dingtalk("交易测试")






