#2026/03/21 - MI 整合服務版 (Background + Web Controller)
print('===============================================================')
print('     %%%%%  %%        %%              MI Integrated Service  ')
print('    %%   %% %% %% %%  %% %% %%    Copyright Jay Ming-chieh Yang 2026.')   
print('    %%   %% %% %% %%  %% %% %%        [郵件報表整合通報系統] ver 2.0')
print('    %%   %% %% %% %%  %% %% %%')
print('     %%%%%  %%  %%%%% %%  %%%%%')
print('===============================================================')

import os
import json
import csv
import time
import threading
import urllib.parse
import requests
import smtplib
import ssl
import queue
import io
# ... 其他 import ...
from datetime import datetime, timedelta 
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import paho.mqtt.client as mqtt
from PIL import Image, ImageDraw
import logging
from flask import Flask, render_template_string, jsonify, request

# ================= 系統與憑證設定 =================
SENDER_EMAIL = "用來寄信的email信箱"
SENDER_PASSWORD = "用來寄信的密碼"
RECEIVER_EMAIL = "收信者email"

# LINE API 憑證 (暫停使用)
LINE_CHANNEL_ACCESS_TOKEN = "YOUR_LINE_TOKEN"
LINE_USER_ID = "YOUR_LINE_ID"
# Telegram API 憑證 (暫停使用)
TG_BOT_TOKEN = "YOUR_TG_TOKEN"
TG_CHAT_ID = "YOUR_TG_ID"

BROKER_IP = "localhost"
BROKER_PORT = 1883
WEB_PORT = 5001          # MI 系統網頁專用 Port 號

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "bed_config.json")
SCHEDULE_FILE = os.path.join(BASE_DIR, "mi_schedule.json")

# ================= 全域變數與快取 =================
app = Flask(__name__)

# 讓 Flask (Werkzeug) 只顯示 Error 等級的紀錄
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


def load_mi_schedule():
    """從硬碟讀取排程設定"""
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return {"interval": 1, "scheduled_patients": []}

CURRENT_SCHEDULE = load_mi_schedule()
MQTT_RESPONSE_QUEUES = {}


# 網頁端顯示用的系統狀態
system_state = {
    "beds_data": {},
    "schedule": CURRENT_SCHEDULE
}

# ================= 網頁前端 HTML 模板 =================
MI_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0"> 
    <title>MI 報表通報系統</title>
    <style>
        body { 
            font-family: 'Microsoft JhengHei UI', Arial, sans-serif; 
            margin: 0; padding: 20px; 
            background-color: #F5F7FA;
            background-image: url('/static/copyright_mi.jpg');
            background-size: contain; 
            background-repeat: no-repeat; 
            background-position: center; 
            background-attachment: fixed;
        }
        .container { 
            max-width: 800px; margin: auto; 
            background: rgba(255, 255, 255, 0.92); 
            padding: 25px; border-radius: 12px; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.15); 
            backdrop-filter: blur(5px);
        }
        h2 { color: #333; text-align: center; margin-top: 0; border-bottom: 2px solid #20B2AA; padding-bottom: 10px;}
        
        .top-bar { display: flex; align-items: center; justify-content: space-between; background: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .top-bar select { font-size: 16px; padding: 5px 10px; border-radius: 5px; }
        .btn-save { background: #4CAF50; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 5px; cursor: pointer; font-weight: bold;}
        
        .transfer-container { display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; align-items: stretch; margin-bottom: 20px;}
        .list-box { flex: 1; min-width: 250px; display: flex; flex-direction: column; }
        .list-box h3 { margin: 0 0 10px 0; font-size: 16px; color: #555; text-align: center; padding: 8px; border-radius: 5px;}
        .list-avail h3 { background: #DEFFAC; }
        .list-selected h3 { background: #F2E6E6; }
        select[multiple] { width: 100%; flex-grow: 1; min-height: 250px; font-size: 16px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-family: Consolas, monospace;}
        
        .controls { display: flex; flex-direction: column; justify-content: center; gap: 10px; min-width: 120px; }
        .controls button { background: #6c757d; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 14px;}
        .controls button:hover { background: #5a6268; }
        
        .bottom-bar { display: flex; justify-content: flex-end; padding-top: 20px; border-top: 1px solid #ddd; }
        .btn-manual { background: #FF5252; color: white; border: none; padding: 12px 25px; font-size: 16px; border-radius: 5px; cursor: pointer; font-weight: bold;}
    </style>
</head>
<body>
    <div class="container">
        <h2>📧 MI 報表通報系統 (網頁控制台)</h2>
        
        <div class="top-bar">
            <div>
                <label style="font-weight: bold; font-size: 16px;">自動寄送頻率：</label>
                <select id="intervalSelect" onchange="applySchedule()">
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="4">4</option>
                    <option value="8">8</option>
                </select>
                <label style="font-size: 16px;"> 小時</label>
            </div>
            <button class="btn-save" onclick="applySchedule()">儲存並套用</button>
        </div>

        <div class="transfer-container">
            <div class="list-box list-avail">
                <h3>目前在床病人</h3>
                <select id="availList" multiple></select>
            </div>
            
            <div class="controls">
                <button onclick="moveItems('availList', 'selectedList')">加入 &gt;</button>
                <button onclick="moveItems('selectedList', 'availList')">&lt; 移除</button>
                <button onclick="moveAll('availList', 'selectedList')">全部加入 &gt;&gt;</button>
                <button onclick="moveAll('selectedList', 'availList')">&lt;&lt; 全部移除</button>
            </div>
            
            <div class="list-box list-selected">
                <h3>已加入定時傳送名單</h3>
                <select id="selectedList" multiple></select>
            </div>
        </div>

        <div class="bottom-bar">
            <button class="btn-manual" onclick="triggerManual()">立即手動寄出 (不影響排程)</button>
        </div>
    </div>

    <script>
        let lastStateString = "";

        async function fetchState() {
            try {
                const res = await fetch('/api/state');
                const state = await res.json();
                
                const stateString = JSON.stringify(state);
                if (stateString === lastStateString) return;
                lastStateString = stateString;

                document.getElementById('intervalSelect').value = state.schedule.interval;

                let activeItems = [];
                for (const [bed, info] of Object.entries(state.beds_data)) {
                    if (info.patient_id) {
                        activeItems.push(`[${bed}] ${info.patient_id}`);
                    }
                }

                const scheduledPids = state.schedule.scheduled_patients || [];
                
                const availList = document.getElementById('availList');
                const selectedList = document.getElementById('selectedList');
                availList.innerHTML = '';
                selectedList.innerHTML = '';

                activeItems.forEach(item => {
                    const pid = item.split("] ")[1];
                    const option = document.createElement('option');
                    option.value = pid;
                    option.text = item;
                    
                    if (scheduledPids.includes(pid)) {
                        selectedList.appendChild(option);
                    } else {
                        availList.appendChild(option);
                    }
                });
            } catch (error) { console.error("無法連線至伺服器", error); }
        }

        function moveItems(sourceId, targetId) {
            const src = document.getElementById(sourceId);
            const tgt = document.getElementById(targetId);
            Array.from(src.selectedOptions).forEach(option => { tgt.appendChild(option); });
            applySchedule(true); 
        }

        function moveAll(sourceId, targetId) {
            const src = document.getElementById(sourceId);
            const tgt = document.getElementById(targetId);
            Array.from(src.options).forEach(option => { tgt.appendChild(option); });
            applySchedule(true); 
        }

        async function applySchedule(silent = false) {
            const interval = parseInt(document.getElementById('intervalSelect').value);
            const selectedList = document.getElementById('selectedList');
            const scheduledPatients = Array.from(selectedList.options).map(opt => opt.value);

            const payload = { interval: interval, scheduled_patients: scheduledPatients };
            
            try {
                await fetch('/api/schedule', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                lastStateString = ""; 
                fetchState();
                
                if (!silent) alert(`排程已更新！\\n目前設定為每 ${interval} 小時自動寄送一次。`);
            } catch (e) { alert("套用失敗，請檢查連線！"); }
        }

        async function triggerManual() {
            const selectedList = document.getElementById('selectedList');
            const scheduledPatients = Array.from(selectedList.options).map(opt => opt.value);
            
            if (scheduledPatients.length === 0) {
                alert("請先將病患加入右側名單！"); return;
            }

            if (!confirm("確定要立即收集右側名單的資料並寄出嗎？")) return;

            try {
                const response = await fetch('/api/trigger', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target_patients: scheduledPatients })
                });
                const result = await response.json();
                alert(result.message);
            } catch (e) { alert("傳送指令失敗！"); }
        }

        fetchState();
        setInterval(fetchState, 5000);
    </script>
</body>
</html>
"""

# ================= 網頁後端 API =================
@app.route('/')
def index():
    return render_template_string(MI_HTML_TEMPLATE)

@app.route('/api/state', methods=['GET'])
def get_state():
    """提供前端：目前全區床位狀態與最新 MI 排程"""
    system_state["schedule"] = CURRENT_SCHEDULE
    return jsonify(system_state)

@app.route('/api/schedule', methods=['POST'])
def set_schedule():
    """接收前端：使用者更改了排程頻率或名單"""
    global CURRENT_SCHEDULE
    data = request.json
    CURRENT_SCHEDULE = data
    system_state["schedule"] = data
    
    # 直接寫入硬碟
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    # 透過 MQTT 廣播給其他可能有監聽的服務 (保持相容性)
    mqtt_client.publish("olulu/mi/schedule_update", json.dumps(data))
    return jsonify({"status": "success"})

@app.route('/api/trigger', methods=['POST'])
def trigger_report():
    """接收前端：手動立即通報"""
    data = request.json
    target_patients = data.get("target_patients", [])
    current_interval = CURRENT_SCHEDULE.get("interval", 1)
    
    if target_patients:      # 直接呼叫背景寄信函數！
        print(f"\n [網頁觸發] 收到通報請求，名單: {target_patients}，抓取過去 {current_interval} 小時資料")
        threading.Thread(
            target=execute_combined_report, 
            args=(mqtt_client, target_patients, RECEIVER_EMAIL, current_interval),
            daemon=True
        ).start()
        
    return jsonify({"status": "success", "message": "手動通報指令已傳送至背景處理！"})

# ================= 繪圖與寄信工具 =================
def generate_local_chart_bytes(pid, times_str_list, weights, interval_minutes):
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

    for y_val in [0, 250, 500]:
        y_pos = height - pad_y - ((y_val - min_w) / y_range) * plot_h
        draw.line([(pad_x, y_pos), (width - pad_x, y_pos)], fill="#EEEEEE", width=1)
        draw.text((pad_x - 30, y_pos - 5), str(y_val), fill="#888888")

    draw.line([(pad_x, pad_y), (pad_x, height - pad_y)], fill="#CCCCCC", width=2)
    draw.line([(pad_x, height - pad_y), (width - pad_x, height - pad_y)], fill="#CCCCCC", width=2)

    info_text = f"Target: Last {interval_minutes} Mins | Actual Data Points: {len(weights)}"
    draw.text((pad_x + 10, pad_y + 10), info_text, fill="#555555")

    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=interval_minutes)

    points = []
    for i in range(len(weights)):
        try:
            t_str = times_str_list[i].replace("/", "-")
            row_time = datetime.strptime(t_str[:16], "%Y-%m-%d %H:%M")
            time_diff_seconds = (row_time - start_time).total_seconds()
            total_seconds = interval_minutes * 60
            x_ratio = time_diff_seconds / total_seconds
            x_ratio = max(0.0, min(1.0, x_ratio))
            
            x = pad_x + (x_ratio * plot_w)
            w_capped = min(max(weights[i], 0), 500)
            y = height - pad_y - ((w_capped - min_w) / y_range) * plot_h
            points.append((x, y))
        except ValueError: continue

    if len(points) > 1:
        draw.line(points, fill="#FF9F43", width=2)
    for x, y in points:
        draw.ellipse([x-2, y-2, x+2, y+2], fill="#FF9F43")

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


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
        
        html_content += f"<div style='margin-top: 30px;'><h3> 床位: {bed_name}</h3>"
        
        if not data:
            html_content += f"<p style='color: red;'>此床位於過去 {interval_minutes} 分鐘內無歷史資料。</p></div>"
            continue

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
            html_content += f"<p style='color: red;'>本地圖表繪製失敗: {e}</p></div>"

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

# ================= 資料處理核心 =================
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
                    if pid: mapping[pid] = bed_name
        except Exception: pass
    return mapping

def execute_combined_report(client_obj, patient_ids, email_address, interval_hours=1):
    collected_data = {}
    cutoff_time = datetime.now() - timedelta(hours=interval_hours)
    bed_mapping = get_pid_to_bed_mapping()
    
    for pid in patient_ids:
        bed_name = bed_mapping.get(pid)
        if not bed_name: continue
        
        final_history = []
        q = queue.Queue()
        MQTT_RESPONSE_QUEUES[bed_name] = q 
        
        # 要求 OLuLu 交出記憶體資料
        client_obj.publish("olulu/system/req_history", bed_name)
        
        try:
            memory_data = q.get(timeout=3.0)
            print(f" -> [快取成功] 零延遲取得 {bed_name} 記憶體資料 ({len(memory_data)} 筆)")
            for item in memory_data:
                time_str = item[0].replace("/", "-")
                row_time = datetime.strptime(time_str[:16], "%Y-%m-%d %H:%M")
                if row_time >= cutoff_time:
                    final_history.append((item[0], float(item[1])))
        except queue.Empty:
            print(f" ->  [快取超時] 等不到 {bed_name} 的資料，改讀硬碟 CSV。")
            memory_data = [] 
        finally:
            if bed_name in MQTT_RESPONSE_QUEUES:
                del MQTT_RESPONSE_QUEUES[bed_name]

        need_csv_fallback = False
        if not memory_data:
            need_csv_fallback = True
        else:
            oldest_time = datetime.strptime(memory_data[0][0].replace("/", "-")[:16], "%Y-%m-%d %H:%M")
            if oldest_time > cutoff_time:
                need_csv_fallback = True

        if need_csv_fallback:
            filename = os.path.join(BASE_DIR, f"{pid}.csv")
            if os.path.exists(filename):
                print(f" ->  [硬碟讀取] 正在調閱 {pid}.csv 補齊資料...")
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if len(row) >= 2 and row[0].strip() != "Time":
                                try:
                                    time_str = row[0].strip().replace("/", "-")
                                    row_time = datetime.strptime(time_str[:16], "%Y-%m-%d %H:%M")
                                    
                                    is_in_memory = any(m[0] == row[0].strip() for m in memory_data)
                                    if row_time >= cutoff_time and not is_in_memory:
                                        final_history.append((row[0].strip(), float(row[1])))
                                except ValueError: pass
                except Exception as e: print(f"讀取 CSV 失敗: {e}")
                
                final_history.sort(key=lambda x: x[0]) 

        collected_data[pid] = final_history

    print(f" -> 正在生成並寄送 HTML 圖表 Email...")
    email_success, email_reason = process_email_report(patient_ids, email_address, collected_data, interval_hours, bed_mapping) 
    print(f" -> {email_reason}")

# ================= 自動定時器 =================
def auto_timer_worker(client_obj):
    print(" [定時器] 整合版已啟動，背景監控中...")
    has_sent_this_hour = False
    
    while True:
        now = datetime.now()
        interval = CURRENT_SCHEDULE.get("interval", 1)
        scheduled_patients = CURRENT_SCHEDULE.get("scheduled_patients", [])

        if now.hour % interval == 0 and now.minute == 1:
            if not has_sent_this_hour:
                print(f"\n [排程觸發] 時間：{now.strftime('%H:%M:%S')} (頻率: {interval}H)")
                
                active_patients = get_active_patients()
                valid_targets = [p for p in scheduled_patients if p in active_patients]
                
                if valid_targets: 
                    execute_combined_report(client_obj, valid_targets, RECEIVER_EMAIL, interval_hours=interval)
                else: 
                    print(" -> 目前排程中的病患均已離線，跳過本次通報。")
                    
                has_sent_this_hour = True
                
        elif now.minute != 1:
            has_sent_this_hour = False
            
        time.sleep(30) 

# ================= MQTT 通訊 =================
def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Mi 背景通報與網頁服務已連線 MQTT Broker！")
    client.subscribe("olulu/system/res_history/+") 
    client.subscribe("olulu/system/state_update")
    # 訂閱來自 Python 獨立控制台的指令
    client.subscribe("olulu/mi/req_report")     # 手動寄信
    client.subscribe("olulu/mi/set_schedule")   # 設定排程
    client.subscribe("olulu/mi/req_schedule")   # 索取目前排程
    
    # 連線後主動索取最新的病床狀態
    client.publish("olulu/system/req_config", "all")

def on_message(client, userdata, msg):
    global CURRENT_SCHEDULE
    try:
        payload = msg.payload.decode('utf-8')
        topic = msg.topic
        
        # 1. 攔截 OLuLu 傳來的記憶體快取資料
        if topic.startswith("olulu/system/res_history/"):
            bed_name = topic.split("/")[-1]
            try:
                history_data = json.loads(payload)
                if bed_name in MQTT_RESPONSE_QUEUES:
                    MQTT_RESPONSE_QUEUES[bed_name].put(history_data)
            except Exception as e:
                print(f"解析快取資料失敗: {e}")
            return 
        
        # 2. 接收 OLuLu 主系統的床位狀態更新
        if topic == "olulu/system/state_update":
            system_state["beds_data"] = json.loads(payload)
            return
        # 3. 處理 Python 控制台的手動寄信要求
        if topic == "olulu/mi/req_report":
            data = json.loads(payload)
            target_patients = data.get("target_patients", [])
            current_interval = CURRENT_SCHEDULE.get("interval", 1)
            
            if target_patients:
                print(f"\n [MQTT觸發] 收到 Python 獨立控制台通報請求，名單: {target_patients}")
                threading.Thread(
                    target=execute_combined_report, 
                    args=(client, target_patients, RECEIVER_EMAIL, current_interval),
                    daemon=True
                ).start()
            return

        # 4. 處理 Python 控制台的排程更新設定
        if topic == "olulu/mi/set_schedule":
            data = json.loads(payload)
            CURRENT_SCHEDULE = data
            system_state["schedule"] = data
            
            # 寫入硬碟
            with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
                
            # 廣播給其他端 (讓網頁跟其他 Python 視窗同步變更)
            client.publish("olulu/mi/schedule_update", json.dumps(data))
            print(f"[MQTT觸發] 排程已更新: {data}")
            return

        # 5. 處理 Python 控制台剛啟動時的排程索取
        if topic == "olulu/mi/req_schedule":
            client.publish("olulu/mi/schedule_update", json.dumps(CURRENT_SCHEDULE))
            return

    except Exception as e: 
        print(f"❌ MQTT 處理錯誤: {e}")

# ================= 程式進入點 =================
if __name__ == "__main__":
    # 1. 建立 MQTT Client
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mi_integrated_service")
    except AttributeError:
        mqtt_client = mqtt.Client(client_id="mi_integrated_service")
        
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    # 2. 啟動背景定時器
    threading.Thread(target=auto_timer_worker, args=(mqtt_client,), daemon=True).start()
    
    # 3. 連線 MQTT (改用 loop_start 讓它在背景跑，不卡住 Flask)
    try:
        mqtt_client.connect(BROKER_IP, BROKER_PORT, 60)
        mqtt_client.loop_start() 
    except Exception as e:
        print(f"MQTT 連線失敗: {e}")

    # 4. 啟動網頁伺服器
    print("===============================================================")
    print(" MI Web 控制台已啟動！")
    print(f"請在瀏覽器輸入: http://[伺服器IP]:{WEB_PORT}")
    print("===============================================================")
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False)
