import os
import json
import csv
import time
import threading
import urllib.parse
import requests
import io
import smtplib
import ssl
from datetime import datetime
from datetime import datetime, timedelta 
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import paho.mqtt.client as mqtt
from PIL import Image, ImageDraw
import io


# ================= 系統與憑證設定 (保持不變) =================
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
# --- 記錄 MI 排程的專屬檔案 ---
SCHEDULE_FILE = os.path.join(BASE_DIR, "mi_schedule.json")



def generate_local_chart_bytes(pid, times, weights, interval_minutes):
    """純本地端在記憶體中繪製折線圖 (Y軸固定0-500)"""
    width, height = 600, 350
    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)

    if not weights:
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    # 單純一點固定 Y 軸最大值為 500，最小值為 0
    max_w = 500
    min_w = 0
    y_range = max_w - min_w

    pad_x, pad_y = 50, 40
    plot_w = width - pad_x * 2
    plot_h = height - pad_y * 2

    # 繪製 Y 軸的 3 條水平基準線 (0, 250, 500) 與刻度數字
    for y_val in [0, 250, 500]:
        y_pos = height - pad_y - ((y_val - min_w) / y_range) * plot_h
        draw.line([(pad_x, y_pos), (width - pad_x, y_pos)], fill="#EEEEEE", width=1)
        # 在旁邊印出數字 (使用 PIL 內建安全字型)
        draw.text((pad_x - 30, y_pos - 5), str(y_val), fill="#888888")

    # 繪製外框底線
    draw.line([(pad_x, pad_y), (pad_x, height - pad_y)], fill="#CCCCCC", width=2)
    draw.line([(pad_x, height - pad_y), (width - pad_x, height - pad_y)], fill="#CCCCCC", width=2)

    # 🚀 需求達成：在圖表左上角加註時間長度與資料筆數 (使用英文防亂碼)
    info_text = f"Target: Last {interval_minutes} Mins | Actual Data Points: {len(weights)}"
    draw.text((pad_x + 10, pad_y + 10), info_text, fill="#555555")

    # 計算所有資料點的 X, Y 座標
    points = []
    n = len(weights)
    for i in range(n):
        x = pad_x + (i / max(1, n - 1)) * plot_w
        
        # 防呆機制：萬一重量超過 500，把它壓回 500，避免畫到圖表外面去
        w_capped = min(max(weights[i], 0), 500)
        
        y = height - pad_y - ((w_capped - min_w) / y_range) * plot_h
        points.append((x, y))

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
    """將 PIL 繪製的圖片放入迴圈，確保每位病患都能產生圖表"""
    msg = MIMEMultipart('related')
    msg["from"] = SENDER_EMAIL
    msg["to"] = receiver_email
    msg["subject"] = f"🏥 OLuLu 系統定時報告 - {datetime.now().strftime('%Y/%m/%d %H:%M')}"

    # 換算分鐘數
    interval_minutes = interval_hours * 60

    html_content = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333333; background-color: #F5F7FA; padding: 20px;">
    <div style="max-width: 700px; margin: auto; background-color: #FFFFFF; padding: 20px; border-radius: 10px;">
    <h2>📊 OLuLu 系統最新重量趨勢</h2>
    <p>您好，以下是本次通報的病患即時數據 (擷取過去 {interval_minutes} 分鐘內的資料)：</p>
    """
    
    images_to_attach = []

    # 🔄 開始逐一處理每位病患
    for pid in patient_ids:
        data = collected_data.get(pid, [])
        # 🌟 透過翻譯字典查出床號，查不到就顯示「未知床位」
        bed_name = bed_mapping.get(pid, "未知床位") 
        
        # 🌟 把原本的 {pid} 換成 {bed_name}
        html_content += f"<div style='margin-top: 30px;'><h3>👉 床位: {bed_name}</h3>"
        
        if not data:
            html_content += f"<p style='color: red;'>此床位於過去 {interval_minutes} 分鐘內無歷史資料。</p></div>"
            continue

        times = [item[0][-8:-3] for item in data] 
        weights = [item[1] for item in data]

        try:
            # 呼叫 PIL 畫圖，把分鐘數傳進去
            img_bytes = generate_local_chart_bytes(pid, times, weights, interval_minutes)
            img_cid = f"chart_{pid}" # 為這張圖建立專屬 ID
            
            # 寫入 HTML
            html_content += f"<img src='cid:{img_cid}' style='width: 100%; max-width: 600px; border: 1px solid #ddd; border-radius: 5px;'><br></div>"
            
            # 打包這張圖片進名單中
            img_attachment = MIMEImage(img_bytes, _subtype='png')
            img_attachment.add_header('Content-ID', f'<{img_cid}>')
            images_to_attach.append(img_attachment)
                
        except Exception as e:
            html_content += f"<p style='color: red;'>⚠️ 本地圖表繪製失敗: {e}</p></div>"

    html_content += "<p style='color: #888; font-size: 12px; margin-top: 40px;'>※ 系統自動發送信件</p></div></body></html>"
    
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_content, 'html'))

    # 把剛剛收集到的所有圖片貼到信
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

# ================= 2. LINE QuickChart 快速通報 =================
def process_line_report(bed_name, history_data):
    if not history_data: return False, "無歷史資料"
        
    # 🚀 移除 [-30:] 切片，改用「均勻抽樣」來適應 LINE 的小螢幕
    # 例如 8 小時有 480 筆，我們均勻抽出約 30 筆來畫圖，才不會擠成一團
    step = max(1, len(history_data) // 30)
    sampled_data = history_data[::step]
    
    times = [item[0][-5:] for item in sampled_data]
    weights = [item[1] for item in sampled_data]

    chart_config = {
        "type": "line",
        "data": {
            "labels": times,
            "datasets": [{"label": "Weight (g/ml)", "data": weights, "borderColor": "rgb(54, 162, 235)", "fill": False}]
        }
    }
    encoded_config = urllib.parse.quote(json.dumps(chart_config))
    image_url = f"https://quickchart.io/chart?c={encoded_config}&w=600&h=400"

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {"type": "text", "text": f"🏥 OLuLu 即時通報\n床位 [{bed_name}] 最新重量趨勢："},
        ]
#            {"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url}
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return True, "LINE 發送成功"
        else:
            # 把 LINE 伺服器真正的退貨原因印出來
            return False, f"LINE 拒絕發送 (代碼 {response.status_code}): {response.text}"
    except Exception as e: 
        return False, f"LINE 連線錯誤: {e}"


# ================= 3. Telegram ASCII 極速通報 =================
def process_telegram_report(bed_name, history_data):
    if not history_data: return False, "無歷史資料"

    # 🚀 移除 [-10:] 切片，為了保持 ASCII 圖不換行，均勻抽出 15 筆涵蓋整個時段
    step = max(1, len(history_data) // 15)
    sampled_data = history_data[::step][-15:] 
    
    weights = [item[1] for item in sampled_data]
    max_w = max(weights) if weights else 1
    if max_w == 0: max_w = 1 
    
    max_bars = 15 
    ascii_lines = []
    for t, w in sampled_data:
        time_str = t[-5:] 
        bar_len = int((w / max_w) * max_bars) if w > 0 else 0
        bar_str = "█" * bar_len
        ascii_lines.append(f"{time_str} | {bar_str:<{max_bars}} {w}g")

    # 把所有行組合起來
    ascii_chart = "\n".join(ascii_lines)
    # 組合 Telegram 訊息，使用 <pre> 標籤強制等寬字體顯示
    message_text = f"🚨 OLuLu 即時通報\n床位 [{bed_name}] 最新重量趨勢：\n<pre>{ascii_chart}</pre>"

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML" # 必須開啟 HTML 解析，<pre> 標籤才會生效
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200, "Telegram 發送成功"
    except Exception as e: 
        return False, f"Telegram 發送失敗: {e}"
    
# ================= 核心：資料讀取與通報中樞 =================
def execute_combined_report(patient_ids, email_address, interval_hours=1):
    """加入 interval_hours 參數，負責精準回推時間來過濾資料"""
    collected_data = {}
        # 算出「截止時間」與叫出床號
    cutoff_time = datetime.now() - timedelta(hours=interval_hours)
    bed_mapping = get_pid_to_bed_mapping()
    
    for pid in patient_ids:
        filename = os.path.join(BASE_DIR, f"{pid}.csv")
        history = []
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2 and row[0].strip() != "Time":
                            try:
                                # 解析 OLuLu 的時間格式 
                                time_str = row[0].strip().replace("/", "-")
                                row_time = datetime.strptime(time_str[:16], "%Y-%m-%d %H:%M")
                                
                                # 只抓取大於「截止時間」的資料
                                if row_time >= cutoff_time:
                                    history.append((row[0].strip(), float(row[1])))
                            except ValueError: pass
            except Exception as e: print(f"讀取 {pid} 失敗: {e}")
            
        collected_data[pid] = history

    print(f" -> 正在生成並寄送 HTML 圖表 Email...")
    # 
    email_success, email_reason = process_email_report(patient_ids, email_address, collected_data, interval_hours, bed_mapping) 
    print(f" -> {email_reason}")
    
    for pid in patient_ids:
        # 🌟 床號
        bed_name = bed_mapping.get(pid, "未知床位") 
        
        # 🌟 把原本傳 pid 的地方，通通改成傳 bed_name 給 LINE 和 Telegram！
        line_success, line_reason = process_line_report(bed_name, collected_data[pid])
        print(f" -> [LINE] 床位 {bed_name}: {line_reason}") 
        
        tg_success, tg_reason = process_telegram_report(bed_name, collected_data[pid])
        print(f" -> [Telegram] 床位 {bed_name}: {tg_reason}")

# ================= 獲取病床與病人基本資料=================
def get_active_patients():
    """從硬碟讀取目前真的有在床上的病患"""
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
    """讀取設定檔，建立『病歷號 -> 床號』的翻譯字典"""
    mapping = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for bed_name, info in data.items():
                    pid = info.get("patient_id")
                    if pid:
                        mapping[pid] = bed_name # 建立對應關係，例如 {"1234567": "3L01"}
        except Exception: pass
    return mapping
        # ================= 自動定時器與 MQTT 監聽 =================
def load_mi_schedule():
    """從硬碟讀取排程設定"""
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    # 預設值
    return {"interval": 1, "scheduled_patients": []}

def auto_timer_worker():
    """自動定時器：動態讀取頻率並判斷是否觸發"""
    last_sent_hour = -1
    print("⏳ [定時器] 啟動成功，背景監控中...")
    
    while True:
        now = datetime.now()
        schedule = load_mi_schedule()
        interval = schedule.get("interval", 1)
        scheduled_patients = schedule.get("scheduled_patients", [])

        # 條件：小時能整除、分鐘為 01 (或 00)、且這個小時還沒寄過
        if now.hour % interval == 0 and now.minute == 1 and last_sent_hour != now.hour:
            print(f"\n⏰ [排程觸發] 時間：{now.strftime('%H:%M:%S')} (頻率: {interval}H)")
            
            active_patients = get_active_patients()
            valid_targets = [p for p in scheduled_patients if p in active_patients]
            
            if valid_targets: 
                # 🚀把 interval 傳遞進去
                execute_combined_report(valid_targets, RECEIVER_EMAIL, interval_hours=interval)
            else: 
                print(" -> 目前排程中的病患均已離線，跳過本次通報。")
                
            last_sent_hour = now.hour
            
        time.sleep(30)# 每 30 秒檢查一次

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("✅ MI 背景通報服務已連線，等待手動指令...")
    client.subscribe("olulu/mi/req_report")
    client.subscribe("olulu/mi/set_schedule") # --- 新增訂閱排程頻道 ---

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        
        # 1. 處理前端發來的「設定排程」指令
        if msg.topic == "olulu/mi/set_schedule":
            schedule_data = json.loads(payload)
            with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(schedule_data, f)
            print(f"📝 已更新排程設定：每 {schedule_data.get('interval')} 小時寄送，名單: {schedule_data.get('scheduled_patients')}")
            
            # 儲存完畢後，立刻把最新名單廣播給所有 Controller！
            client.publish("olulu/mi/schedule_update", json.dumps(schedule_data))

        # 2.處理前端剛開機時，主動來要排程的請求
        elif msg.topic == "olulu/mi/req_schedule":
            schedule_data = load_mi_schedule()
            client.publish("olulu/mi/schedule_update", json.dumps(schedule_data))

        # 3. 處理前端發來的「手動立即寄出」指令
        elif msg.topic == "olulu/mi/req_report":
            
            # 🌟 關鍵修復：把純文字 payload 轉換成字典 req_data
            req_data = json.loads(payload)
            
            # 🌟 接著從字典 (req_data) 裡面用 .get() 抓資料
            patients = req_data.get("target_patients", [])
            address = req_data.get("address", RECEIVER_EMAIL)
            
            # 去讀取目前系統中設定的真實頻率
            current_schedule = load_mi_schedule()
            current_interval = current_schedule.get("interval", 1)
            
            print(f"\n📥 [手動觸發] 收到通報請求，名單: {patients}，抓取過去 {current_interval} 小時資料")
            
            if patients: 
                # 把它傳遞給畫圖中樞
                execute_combined_report(patients, address, interval_hours=current_interval)                
    except Exception as e: 
        print(f"❌ 處理錯誤: {e}")

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("✅ MI 背景通報服務已連線，等待手動指令...")
    client.subscribe("olulu/mi/req_report")
    client.subscribe("olulu/mi/set_schedule")
    client.subscribe("olulu/mi/req_schedule") # 🌟 【新增】訂閱索取排程的頻道

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
