import os
import datetime
import requests

WEBHOOK_KEY = os.getenv("WECHAT_WEBHOOK_KEY")  # 从环境变量中获取 Webhook Key

def send_msg(content):
    """发送消息到企业微信"""
    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WEBHOOK_KEY}"
    payload = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    response = requests.post(url, json=payload)
    print(f"Message sent: {response.text}")


def send_closing_reminder():
    """发送下班前工单完工确认的提醒"""
    content = "下班前记得进行工单完工确认"
    send_msg(content)


if __name__ == "__main__":
    send_closing_reminder()
    print("Reminder sent successfully.")
