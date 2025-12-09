import os
import datetime
import requests

WEBHOOK_KEY = os.getenv("WECHAT_WEBHOOK_KEY", "").strip()  # 从环境变量中获取 Webhook Key
TEST_MODE = os.getenv("TEST_MODE"， "false").lower() == "true"  # 测试模式，不实际发送消息
FORCE_SEND = os.getenv("FORCE_SEND", "false").lower() == "true"  # 强制发送，无视时间范围

def send_msg(content):
    """发送消息到企业微信"""
    
    # 测试模式下不实际发送
    if TEST_MODE:
        print(f"[TEST MODE] 模拟发送消息: {content}")
        print(f"[TEST MODE] Webhook Key: {'已设置' if WEBHOOK_KEY else '未设置'}")
        print(f"[TEST MODE] 当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return {"errcode": 0, "errmsg": "test mode"}
    
    # 生产模式，实际发送
    if not WEBHOOK_KEY:
        print("错误: Webhook Key 未设置")
        return {"errcode": -1, "errmsg": "Webhook Key not set"}
    
    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WEBHOOK_KEY}"
    payload = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"消息发送结果: {response.text}")
        return response.json()
    except Exception as e:
        print(f"发送消息时出错: {e}")
        return {"errcode": -1， "errmsg": str(e)}


def is_within_working_hours():
    """检查是否在工作时间范围内（UTC 10:00-11:00，对应北京时间 18:00-19:00）"""
    now = datetime.datetime.now()
    current_hour = now.hour
    
    # 定义工作时间范围（UTC时间）
    work_start_hour = 10  # UTC 10:00 = 北京时间 18:00
    work_end_hour = 11    # UTC 11:00 = 北京时间 19:00
    
    return work_start_hour <= current_hour < work_end_hour


def send_closing_reminder():
    """发送下班前工单完工确认的提醒"""
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_working_hours = is_within_working_hours()
    
    # 检查是否在工作时间内或是否强制发送
    if not is_working_hours and not FORCE_SEND:
        print(f"当前时间不在工作时间内 ({current_time})，且未开启强制发送模式，跳过发送")
        print(f"工作时间范围: UTC {is_within_working_hours.__doc__.split('（')[1].split('）')[0]}")
        return
    
    # 构建消息内容
    prefix_parts = []
    if TEST_MODE:
        prefix_parts.append("[测试]")
    if FORCE_SEND and not is_working_hours:
        prefix_parts.append("[强制发送]")
    
    prefix = "".join(prefix_parts)
    content = f"{prefix}下班前记得进行工单完工确认\n时间: {current_time}"
    
    if FORCE_SEND and not is_working_hours:
        content += f"\n⚠️ 注意：当前不在工作时间范围内 ({current_time.split(' ')[1]})"
    
    result = send_msg(content)
    
    # 检查发送结果
    if result.get("errcode") == 0:
        mode_info = []
        if TEST_MODE:
            mode_info.append("测试模式")
        if FORCE_SEND:
            mode_info.append("强制发送模式")
        
        mode_str = " - ".join(mode_info) if mode_info else "生产模式"
        print(f"{mode_str} - 提醒发送成功")
    else:
        print(f"{'测试模式' if TEST_MODE else '生产模式'} - 提醒发送失败: {result.get('errmsg')}")


if __name__ == "__main__":
    print(f"开始执行{'测试' if TEST_MODE else '生产'}提醒任务")
    print(f"强制发送模式: {FORCE_SEND}")
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"当前时间: {current_time}")
    print(f"是否在工作时间内: {is_within_working_hours()}")
    
    send_closing_reminder()
    print("任务执行完成")
