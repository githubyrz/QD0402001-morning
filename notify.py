import os
import datetime
import requests

WEBHOOK_KEY = os.getenv("WECHAT_WEBHOOK_KEY")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"  # 判断是否进入测试模式
TEST_DATE = os.getenv("TEST_DATE")  # 获取传入的测试日期

# 预留 @ 手机号（暂不启用）
MENTION_MOBILES = [
    os.getenv("MENTION_MOBILE_1"),
    os.getenv("MENTION_MOBILE_2"),
    os.getenv("MENTION_MOBILE_3"),
    os.getenv("MENTION_MOBILE_4"),
    os.getenv("MENTION_MOBILE_5"),
]

WHITE_SHIFT_BASE = datetime.date(2025, 11, 28)


def send_msg(lines):
    """发送消息（测试模式时只输出到日志）"""
    today = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    if TEST_DATE:
        # 使用测试日期
        today = datetime.datetime.strptime(TEST_DATE, "%Y-%m-%d")
    date_str = today.strftime("%Y-%m-%d")

    content = f"工作提醒 {date_str}\n\n" + "\n".join(lines)

    if TEST_MODE:
        # 测试模式下，输出到日志
        print(f"[TEST MODE] 消息内容: \n{content}")
    else:
        # 正式模式，发送到企业微信
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WEBHOOK_KEY}"
        payload = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        requests.post(url, json=payload)


def is_white_shift(dt: datetime.date) -> bool:
    """判断是否白班日"""
    diff = (dt - WHITE_SHIFT_BASE).days % 4
    return diff == 0


def is_monday(dt): 
    return dt.weekday() == 0


def is_flood_season(dt):
    return dt.month in [6, 7, 8, 9]


def closest_monday_for(target_day, dt):
    mondays = []
    for d in range(1, 32):
        try:
            t = datetime.date(dt.year, dt.month, d)
            if t.weekday() == 0:
                mondays.append(t)
        except:
            break

    best = min(mondays, key=lambda x: abs(x.day - target_day))
    return dt == best


def build_tasks(dt):
    tasks = []

    # 每天：防火巡查 + 外电源巡查
    tasks.append("防火巡查")
    tasks.append("外电源巡查")

    # 周一：周巡
    if is_monday(dt):
        tasks.append("周巡")

    # 汛期周一：防汛物资巡查
    if is_monday(dt) and is_flood_season(dt):
        tasks.append("防汛物资巡查")

    # 电气火灾巡查（最接近 14/28 的周一）
    if is_monday(dt) and (closest_monday_for(14, dt) or closest_monday_for(28, dt)):
        tasks.append("电气火灾巡查")

    # 每月 20：灭火器 &（非汛期额外）防汛物资
    if dt.day == 20:
        tasks.append("灭火器巡查")
        if not is_flood_season(dt):
            tasks.append("防汛物资巡查")

    return tasks


def in_9am_window(now):
    """判断是否处于北京时间 09:00–09:30 之间"""
    hour = now.hour
    minute = now.minute
    return (hour == 9 and minute <= 30) or (hour == 8 and minute >= 58)


if __name__ == "__main__":
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    today = now.date()

    if TEST_MODE:
        # 测试模式下，不需要考虑时间窗口，直接继续执行
        print("[TEST MODE] 正在测试...忽略时间窗口检查")
    else:
        # 非测试模式，进行时间窗口检查
        if not in_9am_window(now):
            print("Not in 9am window. Skip.")
            exit(0)

    if not is_white_shift(today):
        print("Not white shift today. No reminders.")
        exit(0)

    tasks = build_tasks(today)

    if not tasks:
        print("No tasks today.")
        exit(0)

    send_msg(tasks)
    print("Message sent.")
