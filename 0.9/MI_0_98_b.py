#2026/03/18
import os
import json
import csv
import time
import threading
import urllib.parse
import requests
import smtplib
import ssl
from datetime import datetime, timedelta 
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import paho.mqtt.client as mqtt
from PIL import Image, ImageDraw
import io
import queue

# ================= 系統與憑證設定 =================
SENDER_EMAIL = "jjsamsungcb@gmail.com"
SENDER_PASSWORD = "rlyqygxwgxejgegm"
RECEIVER_EMAIL = "jjsamsungcb@gmail.com"

# LINE API 憑證 
LINE_CHANNEL_ACCESS_TOKEN = "fb+0bW2xkpejbrEFMsKsopo4+yE71K28CxmhuEXaMzsFOdLTv61ECfALMbIodVPiM1/6HqJVuBEjd6gd/ek/AYnxz2KcGWSmtvajeYVkjJ5w5UQORJYZBv5HDC+9V2fLlG6IeLJMpPqkO1lU7pVwsgdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U32dc2a587bc124f784a0457352652624"
# Telegram API 憑證
TG_BOT_TOKEN = "8748477838:AAF4s75BTFS2e9xKSqEMIZOF6uS_AHB8eU4"
TG_CHAT_ID = "8777236897"

BROKER_IP = "localhost"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "bed_config.json")
SCHEDULE_FILE = os.path.join(BASE_DIR, "mi_schedule.json")

# 排程記憶體快取 (減少硬碟讀取)
CURRENT_SCHEDULE = {"interval": 1, "scheduled_patients": []}
# 用來接收 OLuLu 歷史資料的回傳信箱
MQTT_RESPONSE_QUEUES = {}


def generate_local_chart_bytes(pid, times_str_list, weights, interval_minutes):
    """純本地端在記憶體中繪製折線圖，X軸為絕對時間比例，Y軸固定0-500"""
    width, height = 600, 350
    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)

    if not weights:
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    max_w, min_w = 500, 0
    y_range = max_w - min_w
    pad_x, pad_y = 50, 40
    plot_w = width - pad_x * 2
    plot_h = height - pad_y * 2

    # 繪製 Y 軸的 3 條水平基準線與數字
    for y_val in [0, 250, 500]:
        y_pos = height - pad_y - ((y_val - min_w) / y_range) * plot_h
        draw.line([(pad_x, y_pos), (width - pad_x, y_pos)], fill="#EEEEEE", width=1)
        draw.text((pad_x - 30, y_pos - 5), str(y_val), fill="#888888")

    # 繪製外框底線
    draw.line([(pad_x, pad_y), (pad_x, height - pad_y)], fill="#CCCCCC", width=2)
    draw.line([(pad_x, height - pad_y), (width - pad_x, height - pad_y)], fill="#CCCCCC", width=2)

    info_text = f"Target: Last {interval_minutes} Mins | Actual Data Points: {len(weights)}"
    draw.text((pad_x + 10, pad_y + 10), info_text, fill="#555555")

    # 🚀 建立絕對時間尺規
    # 假設最右邊(終點)是「現在」，最左邊(起點)是「interval_minutes 分鐘前」
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=interval_minutes)

    points = []
    for i in range(len(weights)):
        try:
            # 將字串轉換回 datetime 物件
            t_str = times_str_list[i].replace("/", "-")
            row_time = datetime.strptime(t_str[:16], "%Y-%m-%d %H:%M")
            
            # 計算這個時間點，落在整段時間軸的百分比 (0.0 到 1.0 之間)
            time_diff_seconds = (row_time - start_time).total_seconds()
            total_seconds = interval_minutes * 60
            x_ratio = time_diff_seconds / total_seconds
            
            # 確保點不會畫到圖表外面去
            x_ratio = max(0.0, min(1.0, x_ratio))
            
            x = pad_x + (x_ratio * plot_w)
            w_capped = min(max(weights[i], 0), 500)
            y = height - pad_y - ((w_capped - min_w) / y_range) * plot_h
            points.append((x, y))
            
        except ValueError:
            continue # 時間格式無法判讀就跳過

    # 畫橘色折線與圓點
    if len(points) > 1:
        draw.line(points, fill="#FF9F43", width=2)
    for x, y in points:
        draw.ellipse([x-2, y-2, x+2, y+2], fill="#FF9F43")

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


# ================= email 通報 =================
def process_email_report(patient_ids, receiver_email, collected_data, interval_hours, bed_mapping):
    msg = MIMEMultipart('related')
    msg["from"] = SENDER_EMAIL
    msg["to"] = receiver_email
    msg["subject"] = f"🐱🐩OLuLu 系統報告 - {datetime.now().strftime('%Y/%m/%d %H:%M')}"

    interval_minutes = interval_hours * 60

    html_content = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333333; background-color: #F5F7FA; padding: 20px;">
    <div style="max-width: 700px; margin: auto; background-color: #FFFFFF; padding: 20px; border-radius: 10px;">
    <h2>🐩OLuLu 系統最新重量趨勢📊</h2>
    <p>您好，以下是過去 {interval_minutes} 分鐘內的資料：</p>
    """
    
    images_to_attach = []

    for pid in patient_ids:
        data = collected_data.get(pid, [])
        bed_name = bed_mapping.get(pid, "未知床位") 
        
        html_content += f"<div style='margin-top: 30px;'><h3>👉 床位: {bed_name}</h3>"
        
        if not data:
            html_content += f"<p style='color: red;'>此床位於過去 {interval_minutes} 分鐘內無歷史資料。</p></div>"
            continue

        # 把完整的 "YYYY-MM-DD HH:MM" 傳給畫圖函式
        times = [item[0][:16] for item in data] 
        weights = [item[1] for item in data]

        try:
            img_bytes = generate_local_chart_bytes(pid, times, weights, interval_minutes)
            img_cid = f"chart_{pid}" 
            
            html_content += f"<img src='cid:{img_cid}' style='width: 100%; max-width: 600px; border: 1px solid #ddd; border-radius: 5px;'><br></div>"
            
            img_attachment = MIMEImage(img_bytes, _subtype='png')
            img_attachment.add_header('Content-ID', f'<{img_cid}>')
            images_to_attach.append(img_attachment)
                
        except Exception as e:
            html_content += f"<p style='color: red;'>⚠️ 本地圖表繪製失敗: {e}</p></div>"

    html_content += "<p style='color: #888; font-size: 12px; margin-top: 40px;'>※ 系統自動發送信件</p></div></body></html>"
    
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_content, 'html'))

    for img in images_to_attach:
        msg.attach(img)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        return True, "Email 圖表已成功寄送！"
    except Exception as e:
        return False, f"Email 寄信失敗: {e}"


# ================= 2. LINE QuickChart 快速通報，因聯外繪圖不穩，目前停用 =================
#def process_line_report(bed_name, history_data):
#    if not history_data: return False, "無歷史資料"
#        
#    step = max(1, len(history_data) // 30)
#    sampled_data = history_data[::step]
#    
#    times = [item[0][-5:] for item in sampled_data]
#    weights = [item[1] for item in sampled_data]
#
#    chart_config = {
#        "type": "line",
#        "data": {
#            "labels": times,
#            "datasets": [{"label": "Weight (g/ml)", "data": weights, "borderColor": "rgb(54, 162, 235)", "fill": False}]
#        }
#    }
#    encoded_config = urllib.parse.quote(json.dumps(chart_config))
#    image_url = f"https://quickchart.io/chart?c={encoded_config}&w=600&h=400"
#
#    url = "https://api.line.me/v2/bot/message/push"
#    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
#    payload = {
#        "to": LINE_USER_ID,
#        "messages": [
#            {"type": "text", "text": f"🏥 OLuLu 即時通報\n床位 [{bed_name}] 最新重量趨勢："},
#        ]
#    }
#    try:
#        response = requests.post(url, headers=headers, data=json.dumps(payload))
#        if response.status_code == 200:
#            return True, "LINE 發送成功"
#        else:
#            return False, f"LINE 拒絕發送 (代碼 {response.status_code}): {response.text}"
#    except Exception as e: 
#        return False, f"LINE 連線錯誤: {e}"


# ================= 3. Telegram ASCII 通報，因暫時無法解決機器人發訊問題，停用中 =================
#def process_telegram_report(bed_name, history_data):
#    if not history_data: return False, "無歷史資料"

#    step = max(1, len(history_data) // 15)
#    sampled_data = history_data[::step][-15:] 
    
#    weights = [item[1] for item in sampled_data]
#    max_w = max(weights) if weights else 1
#    if max_w == 0: max_w = 1 
    
#    max_bars = 15 
#    ascii_lines = []
#    for t, w in sampled_data:
#        time_str = t[-5:] 
#        bar_len = int((w / max_w) * max_bars) if w > 0 else 0
#        bar_str = "█" * bar_len
#        ascii_lines.append(f"{time_str} | {bar_str:<{max_bars}} {w}g")

#    ascii_chart = "\n".join(ascii_lines)
#    message_text = f"🚨 OLuLu 即時通報\n床位 [{bed_name}] 最新重量趨勢：\n<pre>{ascii_chart}</pre>"

#    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
#    payload = {
#        "chat_id": TG_CHAT_ID,
#        "text": message_text,
#        "parse_mode": "HTML" 
#    }

#    try:
#        response = requests.post(url, json=payload, timeout=10)
#        return response.status_code == 200, "Telegram 發送成功"
#    except Exception as e: 
#        return False, f"Telegram 發送失敗: {e}"
    

# ================= 核心：資料讀取與通報中樞 =================
# 🟢 記得加上 mqtt_client 參數
def execute_combined_report(mqtt_client, patient_ids, email_address, interval_hours=1):
    collected_data = {}
    cutoff_time = datetime.now() - timedelta(hours=interval_hours)
    bed_mapping = get_pid_to_bed_mapping()
    
    for pid in patient_ids:
        bed_name = bed_mapping.get(pid)
        if not bed_name: continue
        
        final_history = []
        
        # ==========================================
        # 1. 建立專屬信箱，並發出 req_history 請求
        # ==========================================
        q = queue.Queue()
        MQTT_RESPONSE_QUEUES[bed_name] = q 
        
        # 🟢 核心動作：要求 OLuLu 交出記憶體資料
        mqtt_client.publish("olulu/system/req_history", bed_name)
        
        try:
            # 原地等待，最多等 3 秒
            memory_data = q.get(timeout=3.0)
            print(f" -> ⚡ [快取成功] 零延遲取得 {bed_name} 記憶體資料 ({len(memory_data)} 筆)")
            
            # 篩選我們需要的時間範圍
            for item in memory_data:
                time_str = item[0].replace("/", "-")
                row_time = datetime.strptime(time_str[:16], "%Y-%m-%d %H:%M")
                if row_time >= cutoff_time:
                    final_history.append((item[0], float(item[1])))
                    
        except queue.Empty:
            print(f" -> ⚠️ [快取超時] 等不到 {bed_name} 的資料，改讀硬碟 CSV。")
            memory_data = [] 
            
        finally:
            # 用完就把信箱拆了
            if bed_name in MQTT_RESPONSE_QUEUES:
                del MQTT_RESPONSE_QUEUES[bed_name]

        # ==========================================
        # 2. 如果快取不夠或失敗，備援去讀 CSV
        # ==========================================
        need_csv_fallback = False
        if not memory_data:
            need_csv_fallback = True
        else:
            # 檢查快取中最舊的那筆資料，是不是還比我們要求的時間新？
            # 如果是，代表快取長度不夠，必須去 CSV 找更舊的資料
            oldest_time = datetime.strptime(memory_data[0][0].replace("/", "-")[:16], "%Y-%m-%d %H:%M")
            if oldest_time > cutoff_time:
                need_csv_fallback = True

        if need_csv_fallback:
            filename = os.path.join(BASE_DIR, f"{pid}.csv")
            if os.path.exists(filename):
                print(f" -> 💽 [硬碟讀取] 正在調閱 {pid}.csv 補齊資料...")
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if len(row) >= 2 and row[0].strip() != "Time":
                                try:
                                    time_str = row[0].strip().replace("/", "-")
                                    row_time = datetime.strptime(time_str[:16], "%Y-%m-%d %H:%M")
                                    
                                    # 🟢 確保不要把已經在快取裡的資料重複加進來
                                    is_in_memory = any(m[0] == row[0].strip() for m in memory_data)
                                    if row_time >= cutoff_time and not is_in_memory:
                                        final_history.append((row[0].strip(), float(row[1])))
                                except ValueError: pass
                except Exception as e: print(f"讀取 CSV 失敗: {e}")
                
                final_history.sort(key=lambda x: x[0]) # 重新照時間排序

        collected_data[pid] = final_history

    # ==========================================
    # 3. 執行原本的畫圖與寄信
    # ==========================================
    print(f" -> 正在生成並寄送 HTML 圖表 Email...")
    email_success, email_reason = process_email_report(patient_ids, email_address, collected_data, interval_hours, bed_mapping) 
    print(f" -> {email_reason}")
    
    #for pid in patient_ids: #如上，暫時停用
    #    bed_name = bed_mapping.get(pid, "未知床位") 
    #    line_success, line_reason = process_line_report(bed_name, collected_data[pid])
    #    print(f" -> [LINE] 床位 {bed_name}: {line_reason}") 
    #    
    #    tg_success, tg_reason = process_telegram_report(bed_name, collected_data[pid])
    #    print(f" -> [Telegram] 床位 {bed_name}: {tg_reason}")


# ================= 獲取病床與病人基本資料=================
def get_active_patients():
    active_pids = []
    if not os.path.exists(CONFIG_FILE): return active_pids
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for bed_name, info in data.items():
                pid = info.get("patient_id")
                if pid: active_pids.append(pid)
    except Exception: pass
    return active_pids

def get_pid_to_bed_mapping():
    mapping = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for bed_name, info in data.items():
                    pid = info.get("patient_id")
                    if pid:
                        mapping[pid] = bed_name
        except Exception: pass
    return mapping


# ================= 自動定時器與 MQTT 監聽 =================
def load_mi_schedule():
    """從硬碟讀取排程設定 (僅啟動時呼叫一次)"""
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return {"interval": 1, "scheduled_patients": []}


def auto_timer_worker():
    """優化後的定時器：使用 Flag 控制與記憶體快取"""
    global CURRENT_SCHEDULE
    CURRENT_SCHEDULE = load_mi_schedule()
    has_sent_this_hour = False
    
    print("⏳ [定時器] 優化版啟動，背景監控中...")
    
    while True:
        now = datetime.now()
        interval = CURRENT_SCHEDULE.get("interval", 1)
        scheduled_patients = CURRENT_SCHEDULE.get("scheduled_patients", [])

        # 條件：小時能整除、分鐘為 01
        if now.hour % interval == 0 and now.minute == 1:
            if not has_sent_this_hour:
                print(f"\n⏰ [排程觸發] 時間：{now.strftime('%H:%M:%S')} (頻率: {interval}H)")
                
                active_patients = get_active_patients()
                valid_targets = [p for p in scheduled_patients if p in active_patients]
                
                if valid_targets: 
                    execute_combined_report(mqtt_client,valid_targets, RECEIVER_EMAIL, interval_hours=interval)
                else: 
                    print(" -> 目前排程中的病患均已離線，跳過本次通報。")
                    
                has_sent_this_hour = True # 上鎖，避免本分鐘內重複執行
                
        # 過了 01 分，把鎖解開，準備下一次觸發
        elif now.minute != 1:
            has_sent_this_hour = False
            
        time.sleep(30) # 保持 30 秒迴圈即可，沒有硬碟 I/O 負擔極輕


def on_connect(client, userdata, flags, reason_code, properties=None):
    print("✅ MI 背景通報服務已連線，等待手動指令...")
    client.subscribe("olulu/mi/req_report")
    client.subscribe("olulu/mi/set_schedule")
    client.subscribe("olulu/mi/req_schedule")
    client.subscribe("olulu/system/res_history/+")#訂閱 OLuLu 傳回來的歷史資料頻道 (+ 代表接收所有床位)

    
def on_message(client, userdata, msg):
    global CURRENT_SCHEDULE
    try:
        payload = msg.payload.decode('utf-8')
        # 🟢 新增：攔截 OLuLu 傳來的記憶體快取資料
        if msg.topic.startswith("olulu/system/res_history/"):
            bed_name = msg.topic.split("/")[-1]
            try:
                history_data = json.loads(payload) # OLuLu 傳來的是 JSON
                # 看看有沒有人正在等這個床位的資料，有的話就丟進信箱
                if bed_name in MQTT_RESPONSE_QUEUES:
                    MQTT_RESPONSE_QUEUES[bed_name].put(history_data)
            except Exception as e:
                print(f"❌ 解析快取資料失敗: {e}")
            return # 處理完就結束，不要往下跑
        
        # 處理前端發來的「設定排程」指令
        elif msg.topic == "olulu/mi/set_schedule":
            schedule_data = json.loads(payload)
            CURRENT_SCHEDULE = schedule_data # 🌟 同步更新記憶體快取
            
            with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(schedule_data, f)
            print(f"📝 已更新排程設定：每 {schedule_data.get('interval')} 小時寄送，名單: {schedule_data.get('scheduled_patients')}")
            
            client.publish("olulu/mi/schedule_update", json.dumps(schedule_data))

        # 處理前端剛開機時，主動來要排程的請求
        elif msg.topic == "olulu/mi/req_schedule":
            # 直接從記憶體快取回傳
            client.publish("olulu/mi/schedule_update", json.dumps(CURRENT_SCHEDULE))

        # 處理前端發來的「手動立即寄出」指令
        elif msg.topic == "olulu/mi/req_report":
            req_data = json.loads(payload)
            patients = req_data.get("target_patients", [])
            address = req_data.get("address", RECEIVER_EMAIL)
            
            # 直接讀取記憶體快取中的真實頻率
            current_interval = CURRENT_SCHEDULE.get("interval", 1)
            
            print(f"\n📥 [手動觸發] 收到通報請求，名單: {patients}，抓取過去 {current_interval} 小時資料")
            
            if patients:
                # 將耗時且需要等待的寄信任務，丟給獨立的背景執行緒，以免卡住 MQTT 的接收通道了
                threading.Thread(
                    target=execute_combined_report, 
                    args=(client, patients, address, current_interval),
                    daemon=True
                ).start()                
    except Exception as e: 
        print(f"❌ 處理錯誤: {e}")


if __name__ == "__main__":
    threading.Thread(target=auto_timer_worker, daemon=True).start()
    
    client = mqtt.Client(client_id="olulu_mi_background_service")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER_IP, 1883, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n⛔ MI 背景服務手動關閉")
        client.disconnect()
