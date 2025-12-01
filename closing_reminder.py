import os
import requests
import datetime

# 从环境变量获取 Webhook Key
WEBHOOK_KEY = os.getenv("WECHAT_WEBHOOK_KEY")
TEST_MODE = os.getenv("TEST_MODE"， "false")。lower() == "true"  # 判断是否进入测试模式
TEST_DATE = os.getenv("TEST_DATE")  # 获取传入的测试日期

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
    print(f"Message sent: {response.text}")  # 输出响应用于调试

def send_closing_reminder():
    """发送下班前工单完工确认的提醒"""
    content = "下班前记得进行工单完工确认"
    send_msg(content)

if __name__ == "__main__":
    if TEST_MODE:
        # 测试模式下，不考虑时间窗口，直接发送日志
        today = datetime.datetime.strptime(TEST_DATE, "%Y-%m-%d") if TEST_DATE else datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        date_str = today.strftime("%Y-%m-%d")
        print(f"[TEST MODE] 测试模式：今天是 {date_str}，即将发送提醒：{content}")
    else:
        # 正常模式，继续根据时间窗口发送
        today = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        date_str = today.strftime("%Y-%m-%d")
        print(f"[正式模式] 正常发送提醒：{date_str}")

    send_closing_reminder()
    print("Reminder sent successfully.")
