#!/usr/bin/env python3
# notify.py — WeCom Notify System (robust version)
import os
import sys
import datetime
import requests
from pathlib import Path

# ---------------------- 配置 ----------------------
WEBHOOK_KEY = os.getenv("WECHAT_WEBHOOK_KEY", "").strip()
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
TEST_DATE = os.getenv("TEST_DATE", "").strip()  # YYYY-MM-DD or empty

MENTION_MOBILES = [
    os.getenv("MENTION_MOBILE_1", "").strip(),
    os.getenv("MENTION_MOBILE_2", "").strip(),
    os.getenv("MENTION_MOBILE_3", "").strip(),
    os.getenv("MENTION_MOBILE_4", "").strip(),
    os.getenv("MENTION_MOBILE_5", "").strip(),
]

# 白班基准日
WHITE_SHIFT_BASE = datetime.date(2025, 11, 28)

# 缓存目录，用于持久化“今天是否已发送”
CACHE_DIR = Path(".wecom_cache")
CACHE_DIR.mkdir(exist_ok=True)
LAST_SENT_FILE = CACHE_DIR / "last_sent_main.txt"

# 允许北京时间窗口（包含容错）
# 按你的需求：北京时间 08:50 — 09:40
WINDOW_START_BEIJING = datetime.time(8, 50)
WINDOW_END_BEIJING = datetime.time(9, 40)

# 汛期月份
FLOOD_MONTHS = {6, 7, 8, 9}

# ---------------------- 辅助函数 ----------------------
def now_utc():
    return datetime.datetime.utcnow()

def now_beijing():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)

def is_white_shift(dt_date: datetime.date) -> bool:
    # (dt_date - WHITE_SHIFT_BASE).days % 4 == 0 表示白班
    return ((dt_date - WHITE_SHIFT_BASE).days % 4) == 0

def is_monday(dt_date: datetime.date) -> bool:
    return dt_date.weekday() == 0

def is_flood_season(dt_date: datetime.date) -> bool:
    return dt_date.month in FLOOD_MONTHS

def closest_monday_for(target_day: int, dt_date: datetime.date) -> bool:
    # 找到本月所有周一，选出与 target_day 最接近的一个，判断是否等于 dt_date
    mondays = []
    year, month = dt_date.year, dt_date.month
    for d in range(1, 32):
        try:
            t = datetime.date(year, month, d)
        except ValueError:
            break
        if t.weekday() == 0:
            mondays.append(t)
    if not mondays:
        return False
    best = min(mondays, key=lambda x: abs(x.day - target_day))
    return dt_date == best

def read_last_sent_date() -> str:
    try:
        if LAST_SENT_FILE.exists():
            return LAST_SENT_FILE.read_text().strip()
    except Exception as e:
        print(f"[WARN] read_last_sent_date error: {e}")
    return ""

def write_last_sent_date(date_str: str):
    try:
        LAST_SENT_FILE.write_text(date_str)
    except Exception as e:
        print(f"[WARN] write_last_sent_date error: {e}")

def send_wecom_message(lines):
    """发送企业微信消息或在测试模式下打印"""
    # 组装内容
    beijing = now_beijing() if not TEST_DATE else datetime.datetime.strptime(TEST_DATE, "%Y-%m-%d")
    date_str = beijing.strftime("%Y-%m-%d")
    content = f"工作提醒 {date_str}\n\n" + "\n".join(lines)

    if TEST_MODE:
        print("[TEST MODE] 将不会发送到企业微信。消息内容如下：")
        print(content)
        return {"test": True, "content": content}

    if not WEBHOOK_KEY:
        print("[ERROR] WECHAT_WEBHOOK_KEY 未设置，无法发送消息。")
        return {"err": "no_key"}

    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WEBHOOK_KEY}"
    payload = {"msgtype": "text", "text": {"content": content}}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"[HTTP] POST {url} -> status {resp.status_code} response: {resp.text}")
        return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
    except Exception as e:
        print(f"[ERROR] 发送请求异常: {e}")
        return {"exception": str(e)}

# ---------------------- 业务逻辑 ----------------------
def build_tasks(dt_date: datetime.date):
    tasks = []
    # 每天：防火巡查 + 外电源巡查
    tasks.append("防火巡查")
    tasks.append("外电源巡查")

    # 周一：周巡
    if is_monday(dt_date):
        tasks.append("周巡")

    # 汛期周一：防汛物资巡查
    if is_monday(dt_date) and is_flood_season(dt_date):
        tasks.append("防汛物资巡查")

    # 电气火灾巡查（最接近 14/28 的周一）
    if is_monday(dt_date) and (closest_monday_for(14, dt_date) or closest_monday_for(28, dt_date)):
        tasks.append("电气火灾巡查")

    # 每月 20：灭火器 &（非汛期额外）防汛物资
    if dt_date.day == 20:
        tasks.append("灭火器巡查")
        if not is_flood_season(dt_date):
            tasks.append("防汛物资巡查")

    return tasks

def in_beijing_window(now_bj_dt: datetime.datetime) -> bool:
    t = now_bj_dt.time()
    return (WINDOW_START_BEIJING <= t <= WINDOW_END_BEIJING)

# ---------------------- 主流程 ----------------------
def main():
    utc_now = now_utc()
    bj_now = now_beijing()
    print(f"[INFO] UTC now: {utc_now.isoformat()} | Beijing now: {bj_now.isoformat()}")
    # 决定使用的“逻辑日期”：如果传了 TEST_DATE（测试模式），脚本用 TEST_DATE 作为逻辑日期
    if TEST_DATE:
        try:
            logic_dt = datetime.datetime.strptime(TEST_DATE, "%Y-%m-%d").date()
            print(f"[INFO] Using TEST_DATE as logic date: {logic_dt}")
        except Exception as e:
            print(f"[ERROR] TEST_DATE 格式错误，应为 YYYY-MM-DD: {e}")
            sys.exit(1)
    else:
        logic_dt = bj_now.date()

    # 测试模式绕过时间窗口与白班判断，但仍会构建 tasks 并输出日志（不发真实消息）
    if TEST_MODE:
        print("[TEST MODE] 已启用：忽略时间窗口与白班判断。仅输出日志（不发送真实消息）。")
        tasks = build_tasks(logic_dt)
        if not tasks:
            print("[TEST MODE] 今日无任务。")
            return
        send_wecom_message(tasks)
        print("[TEST MODE] 完成。")
        return

    # 正常模式：检查是否在北京时间窗口
    if not in_beijing_window(bj_now):
        print(f"[INFO] 不在北京时间发送窗口（{WINDOW_START_BEIJING} - {WINDOW_END_BEIJING}），跳过本次运行。当前北京时间：{bj_now.time()}")
        return

    # 正常模式：检查是否为白班
    if not is_white_shift(logic_dt):
        print(f"[INFO] 今天不是白班（{logic_dt}），不发送提醒。")
        return

    # 检查是否已经在今天发送过（使用缓存文件）
    last_sent = read_last_sent_date()
    today_str = logic_dt.strftime("%Y-%m-%d")
    if last_sent == today_str:
        print(f"[INFO] 今日（{today_str}）已发送过提醒，跳过以避免重复。")
        return

    # 构建任务并发送
    tasks = build_tasks(logic_dt)
    if not tasks:
        print("[INFO] 今日无任务，跳过发送。")
        return

    print(f"[INFO] 将发送以下任务（共 {len(tasks)} 项）：")
    for t in tasks:
        print(f" - {t}")

    result = send_wecom_message(tasks)

    # 检查发送结果：如果测试模式则早已返回；否则判断返回值是否包含 errcode==0 或类似成功指示
    success = False
    try:
        if isinstance(result, dict):
            if result.get("errcode") == 0:
                success = True
            elif result.get("test"):
                success = True
            else:
                # 某些情况返回非 JSON raw text
                success = (result.get("raw") is not None and "ok" in str(result.get("raw")).lower())
    except Exception:
        success = False

    if success:
        print(f"[OK] 发送成功，记录已发送日期：{today_str}")
        write_last_sent_date(today_str)
    else:
        print(f"[WARN] 发送未确认成功，返回：{result}")

if __name__ == "__main__":
    main()