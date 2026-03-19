print('===============================================================')
print('     %%%%%  %%        %%              OLuLu Broker+Flask server    ')
print('    %%   %% %% %% %%  %% %% %%    Copyright Jay Ming-chieh Yang 2026.')   
print('    %%   %% %% %% %%  %% %% %%       [物聯網核心伺服器]  ')
print('     %%%%%  %%  %%%%% %%  %%%%%     Target OS: Windows/Linux')
print('===============================================================')

import subprocess
import os
import sys
import json
import csv
import datetime
import time
import queue
import threading
import paho.mqtt.client as mqtt

# 🟢 Flask 與密碼驗證所需套件
from flask import Flask, render_template_string, jsonify, request, Response
from functools import wraps

# ------------------ 判斷作業系統並處理 Mosquitto 啟動 ------------------
if os.name == 'nt':  # Windows 系統專用啟動邏輯
    mosquitto_path = r"C:\Program Files\mosquitto"
    mosquitto_exe = "mosquitto.exe"
    full_path = os.path.join(mosquitto_path, mosquitto_exe)
    try:
        process = subprocess.Popen([full_path])
        print(f"Windows Mosquitto broker 已於背景啟動，PID: {process.pid}")
    except FileNotFoundError:
        print(f"錯誤：找不到 Mosquitto 執行檔於 {full_path}")
    except Exception as e:
        print(f"啟動 Mosquitto 時發生錯誤： {e}")
else:
    print("目前為非 Windows 系統，假設 Mosquitto 已由系統自動啟動。")

print('      Kóo-tsui ê LuLu, khó-ài ê LuLu, OLuLu, OLuLu, OLuLu, OLuLu.      ')

# ================= 系統參數設定 =================
BROKER_IP = "localhost"        #在本機執行
BROKER_PORT = 1883             
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "bed_config.json") #讀取既有已經登錄的床位

DEFAULT_BED_LIST = ["3L01", "3L02", "3L03", "3L05", "3L06", "3L07", "3L08", "3L09", "3K17", "3K18"]

# ================= Flask 參數與密碼鎖設定 =================
app = Flask(__name__)
broker = None # 稍後在主程式初始化

# 🔒 系統管理員帳號密碼設定
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "olulu"

def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
    '請輸入正確的帳號密碼進入 OLuLu 系統管理。', 401,
    {'WWW-Authenticate': 'Basic realm="OLuLu Admin Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# ================= 網頁前端 HTML 模板 =================

# 1. 訪客看圖專用首頁
MAIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0"> 
    <title>OLuLu 遠端即時監控</title>
    <script src="/static/chart.js"></script>
    <style>
        body { font-family: 'Microsoft JhengHei UI', Arial, sans-serif; background-color: #F5F7FA; margin: 0; padding: 15px; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h2 { color: #333; text-align: center; margin-top: 0; }
        select { width: 100%; padding: 12px; font-size: 18px; border-radius: 8px; border: 1px solid #ccc; margin-bottom: 20px; }
        .chart-container { position: relative; height: 40vh; width: 100%; }
        .status { text-align: center; color: #888; font-size: 14px; margin-top: 15px; }
        .btn-admin { display: block; width: 100%; text-align: center; margin-top: 25px; padding: 12px; background: #6c757d; color: white; text-decoration: none; border-radius: 8px; font-weight: bold;}
    </style>
</head>
<body>
    <div class="container">
        <h2>🏥 OLuLu 即時重量監控</h2>
        
        <label for="bedSelect" style="font-weight: bold; color: #555;">請選擇床位：</label>
        <select id="bedSelect" onchange="updateChart()"></select>
        
        <div class="chart-container">
            <canvas id="weightChart"></canvas>
        </div>
        
        <div class="status" id="lastUpdated">載入中...</div>
        
        <hr style="margin: 30px 0; border: 0; border-top: 1px solid #eee;">
        <a href="/admin" class="btn-admin">⚙️ 進入系統管理</a>
    </div>

    <script>
        let chartInstance = null;
        let globalData = {};

        async function fetchData() {
            try {
                const response = await fetch('/api/data');
                globalData = await response.json();
                
                const select = document.getElementById('bedSelect');
                const currentSelection = select.value;
                
                select.innerHTML = '<option value="">-- 請選擇病床 --</option>';
                for (const bedName in globalData) {
                    const option = document.createElement('option');
                    option.value = bedName;
                    option.textContent = `[${bedName}] 病歷號: ${globalData[bedName].patient_id}`;
                    select.appendChild(option);
                }
                
                if (currentSelection && globalData[currentSelection]) {
                    select.value = currentSelection;
                }
                
                updateChart();
                document.getElementById('lastUpdated').textContent = `最後更新時間: ${new Date().toLocaleTimeString()}`;
            } catch (error) {
                document.getElementById('lastUpdated').textContent = '⚠️ 無法連線至伺服器';
            }
        }

        function updateChart() {
            const selectedBed = document.getElementById('bedSelect').value;
            const ctx = document.getElementById('weightChart').getContext('2d');
            
            if (!selectedBed || !globalData[selectedBed]) {
                if (chartInstance) chartInstance.destroy();
                return;
            }

            const bedData = globalData[selectedBed];
            if (chartInstance) chartInstance.destroy();
            
            chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: bedData.times,
                    datasets: [{
                        label: '重量 (g/ml)',
                        data: bedData.weights,
                        borderColor: '#FF9F43',
                        backgroundColor: 'rgba(255, 159, 67, 0.2)',
                        borderWidth: 2,
                        pointRadius: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true, suggestedMax: 500 } },
                    animation: { duration: 0 } 
                }
            });
        }

        fetchData();
        setInterval(fetchData, 60000);
    </script>
</body>
</html>
"""

# 2. 系統管理員專用 (需密碼)
ADMIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0"> 
    <title>OLuLu 系統管理後台</title>
    <style>
        body { font-family: 'Microsoft JhengHei UI', Arial, sans-serif; background-color: #ECEFF1; margin: 0; padding: 15px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h2 { color: #333; text-align: center; margin-top: 0; }
        input { width: 100%; padding: 12px; margin: 8px 0 15px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; box-sizing: border-box;}
        .btn { width: 100%; padding: 14px; color: white; border: none; border-radius: 5px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 5px;}
        .btn-bind { background: #20B2AA; }
        .btn-danger { background: #d9534f; }
        .btn-back { display: block; text-align: center; margin-top: 25px; color: #007BFF; text-decoration: none; font-size: 16px;}
        label { font-weight: bold; color: #555; }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚙️ OLuLu 系統管理後台</h2>
        
        <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ddd;">
            <h3 style="margin-top: 0; color: #333;">📝 登錄新病人</h3>
            <label>病床號碼</label>
            <input type="text" id="bindBed" placeholder="例如: 3L01">
            <label>設備 MAC / ID</label>
            <input type="text" id="bindSensor" placeholder="輸入 HX711 設備 ID">
            <label>病歷號</label>
            <input type="text" id="bindPatient" placeholder="輸入病患病歷號">
            <button class="btn btn-bind" onclick="submitBind()">送出登錄</button>
        </div>

        <div style="background: #fdf0ef; padding: 20px; border-radius: 8px; border: 1px solid #f5c6cb;">
            <h3 style="color: #d9534f; margin-top: 0;">⚠️ 伺服器電源控制</h3>
            <p style="color: #666; font-size: 14px; line-height: 1.5;">點擊下方按鈕將強制存檔所有未寫入的資料，並安全關閉伺服器。關閉後必須在主機端重新啟動程式。</p>
            <button class="btn btn-danger" onclick="systemShutdown()">安全關機 (儲存所有資料)</button>
        </div>

        <a href="/" class="btn-back">⬅️ 返回重量圖表首頁</a>
    </div>

    <script>
        async function submitBind() {
            const bed = document.getElementById('bindBed').value;
            const sensor = document.getElementById('bindSensor').value;
            const patient = document.getElementById('bindPatient').value;
            
            if (!bed || !sensor || !patient) { 
                alert("請填寫完整資訊！"); return; 
            }
            
            try {
                const response = await fetch('/api/bind', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bed_name: bed, sensor_id: sensor, patient_id: patient })
                });
                const result = await response.json();
                alert(result.message);
                if (result.status === "success") {
                    document.getElementById('bindSensor').value = '';
                    document.getElementById('bindPatient').value = '';
                }
            } catch (error) { alert("連線錯誤，請確認伺服器狀態。"); }
        }

        async function systemShutdown() {
            if (!confirm("⚠️ 警告：確定要關閉伺服器嗎？\\n系統將停止收集重量資料。")) return;
            try {
                const response = await fetch('/api/shutdown', { method: 'POST' });
                const result = await response.json();
                alert(result.message);
                document.body.innerHTML = '<h2 style="color: #d9534f; text-align: center; margin-top: 50px;">伺服器已安全關閉<br>您可以關閉此網頁頁面。</h2>';
            } catch (error) { alert("連線錯誤，請檢查伺服器是否開啟。"); }
        }
    </script>
</body>
</html>
"""

# ================= 網頁後端 API 邏輯 =================
@app.route('/')
def index():
    """首頁：開放所有人觀看圖表"""
    return render_template_string(MAIN_HTML_TEMPLATE)

@app.route('/admin')
@requires_auth  # 🔒 加上密碼鎖
def admin_page():
    """後台：需輸入密碼才能進行登錄與關機操作"""
    return render_template_string(ADMIN_HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    """圖表 API：直接從記憶體撈取歷史資料，不讀硬碟"""
    try:
        response_data = {}
        for bed_name, bed_model in broker.beds.items():
            pid = bed_model.patient_id            
            # 防呆：確保病歷號不是 None 也不是空字串 ("")
            if pid and str(pid).strip() != "":
                recent_history = bed_model.history[-60:]                
                # 確保就算沒有歷史紀錄 (空陣列) 也不會當機
                times = [item[0][-5:] for item in recent_history] if recent_history else []
                weights = [item[1] for item in recent_history] if recent_history else []
                
                response_data[bed_name] = {
                    "patient_id": pid,
                    "times": times,
                    "weights": weights
                }
        return jsonify(response_data)        
    except Exception as e:
        print(f"❌ [網頁 API 錯誤] 產生圖表資料時發生異常: {e}")
        return jsonify({}), 500
@app.route('/api/bind', methods=['POST'])
def bind_patient():
    """登錄 API：接收前端表單轉發給 MQTT"""
    data = request.json
    payload = {
        "bed_name": data.get("bed_name"),
        "sensor_id": data.get("sensor_id"),
        "patient_id": data.get("patient_id"),
        "controller_id": "Web_Admin"
    }
    broker.client.publish("olulu/system/req_bind", json.dumps(payload))
    return jsonify({"status": "success", "message": f"綁定指令已送出！床位: {data.get('bed_name')}"})

@app.route('/api/shutdown', methods=['POST'])
def shutdown_server():
    """關機 API：觸發完美存檔與程序終止"""
    print("\n[系統] ⚠️ 收到網頁端安全關機指令...")
    def shutdown_task():
        time.sleep(1.5) 
        broker.shutdown() 
        print("[系統] 網頁端觸發關機完成，程序即將結束。")
        os._exit(0) 

    threading.Thread(target=shutdown_task, daemon=True).start()
    return jsonify({"status": "success", "message": "資料已安全存檔，伺服器準備關閉，可以關閉此網頁。"})

# ================= 資料格式設定 =================
class BedModel:
    def __init__(self, name):
        self.name = name           
        self.sensor_id = None      
        self.patient_id = None     
        self.history = []    
        self.is_online = False     

    def to_dict(self):
        return {"sensor_id": self.sensor_id, "patient_id": self.patient_id}

    def from_dict(self, data):
        self.sensor_id = data.get("sensor_id")
        self.patient_id = data.get("patient_id")

    def add_data(self, timestamp, weight):
        self.history.append((timestamp, weight))
        if len(self.history) > 480: 
            self.history.pop(0)

    def clear_assignment(self):
        self.sensor_id = None  
        self.patient_id = None 
        self.is_online = False 
        self.history = []

    def load_history_from_csv(self):
        if not self.patient_id: return
        filename = os.path.join(BASE_DIR, f"{self.patient_id}.csv")
        if not os.path.exists(filename): return
        
        loaded_history = []
        encodings_to_try = ['utf-8-sig', 'big5', 'utf-8']
        for enc in encodings_to_try:
            try:
                with open(filename, "r", encoding=enc) as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2 and row[0].strip():
                            ts_str = row[0].strip()
                            if ts_str == "Time": continue 
                            try: loaded_history.append((ts_str, float(row[1])))
                            except ValueError: pass
                break 
            except UnicodeDecodeError: continue
            except Exception: return
                
        if loaded_history: 
            self.history = loaded_history[-480:]
            print(f"[資料] 成功載入 {self.patient_id}.csv，共 {len(self.history)} 筆歷史紀錄。")

# ================== 主程式 (背景線序伺服器) ==================    
class HLBroker:
    def __init__(self):
        self.beds = {name: BedModel(name) for name in DEFAULT_BED_LIST}
        self.online_sensors = set()
        self.work_queue = queue.Queue()         
        self.write_buffer = queue.Queue()
        self.flush_event = threading.Event() 
        self.load_config() 

        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="olulu_broker_master")
        except AttributeError:
            self.client = mqtt.Client(client_id="olulu_broker_master")

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message        

    def start(self):
        try:
            self.client.connect(BROKER_IP, BROKER_PORT, 60) 
            self.client.loop_start() 
            print("[狀態] MQTT 核心已啟動，監聽 1883 埠...")
        except Exception as e:
            print(f"[重大問題] MQTT 連線失敗: {e}")
            sys.exit(1)

        threading.Thread(target=self.timer_sync_clock_thread, daemon=True).start()
        threading.Thread(target=self.queue_worker_thread, daemon=True).start()
        threading.Thread(target=self.batch_write_worker, daemon=True).start()        
        print("[狀態] OLuLu 背景存檔與通訊服務運作中。")

    def shutdown(self):
        """將尚未存檔的緩衝區資料寫入硬碟，並安全關閉"""
        print("\n[系統] 收到中斷訊號，開始關閉伺服器...")
        if not self.write_buffer.empty():
            print(f"[系統] 正在將緩衝區剩餘的 {self.write_buffer.qsize()} 筆資料寫入硬碟，請稍候...")
            pending_data = {}
            while not self.write_buffer.empty():
                pid, ts, weight, sid = self.write_buffer.get()
                if pid not in pending_data:
                    pending_data[pid] = []
                pending_data[pid].append([ts, weight, sid])
            
            for pid, rows in pending_data.items():
                filename = os.path.join(BASE_DIR, f"{pid}.csv")
                try:
                    file_exists = os.path.isfile(filename)
                    with open(filename, "a", newline="", encoding='utf-8') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Time", "Weight", "SensorID"])
                        writer.writerows(rows)
                except Exception as e:
                    print(f"[存檔錯誤] 最後存檔失敗 ({pid}.csv): {e}")
                    
        self.save_config()
        self.client.loop_stop()
        self.client.disconnect()
        print("[系統] OLuLu Broker 已存檔並安全關閉。")

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump({n: b.to_dict() for n, b in self.beds.items()}, f, indent=4)
        except Exception as e: 
            print(f"[錯誤] 設定檔存檔失敗: {e}")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE): 
            print("[系統] 找不到現有設定檔，以全新狀態啟動。")
            return
        # 準備多種編碼，相容舊版 Windows (Big5) 與新版網頁 (UTF-8)
        encodings_to_try = ['utf-8', 'big5', 'utf-8-sig', 'cp950']
        loaded_success = False        
        for enc in encodings_to_try:
            try:
                with open(CONFIG_FILE, "r", encoding=enc) as f:
                    data = json.load(f)
                    for name, d in data.items():
                        if name in self.beds: 
                            self.beds[name].from_dict(d)
                            # 確保 patient_id 存在且不為空字串
                            if self.beds[name].patient_id and str(self.beds[name].patient_id).strip():
                                self.beds[name].load_history_from_csv()
                print(f"[系統] 成功載入上一次的床位綁定設定 (偵測為 {enc} 編碼)。")
                loaded_success = True
                break # 成功就跳出迴圈
            except UnicodeDecodeError:
                continue # 編碼錯誤，換下一個編碼試試看
            except Exception as e: 
                print(f"[警告] 嘗試以 {enc} 讀取設定檔時發生異常: {e}")
                continue
                
        if not loaded_success:
            print("[錯誤] 無法讀取 bed_config.json，可能檔案格式已損毀，或裡面有無法辨識的字元。")

    def batch_write_worker(self):
        while True:
            self.flush_event.wait(1800)
            self.flush_event.clear() 
            if self.write_buffer.empty():
                continue             
            
            pending_data = {}
            while not self.write_buffer.empty():
                pid, ts, weight, sid = self.write_buffer.get()
                if pid not in pending_data:
                    pending_data[pid] = []
                pending_data[pid].append([ts, weight, sid])
            
            for pid, rows in pending_data.items():
                filename = os.path.join(BASE_DIR, f"{pid}.csv")
                try:
                    file_exists = os.path.isfile(filename)
                    with open(filename, "a", newline="", encoding='utf-8') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Time", "Weight", "SensorID"])
                        writer.writerows(rows) 
                except Exception as e:
                    print(f"[錯誤] 時間與重量存檔失敗 ({pid}.csv): {e}")

    def timer_sync_clock_thread(self):
        last_sec = -1
        while True:
            now = datetime.datetime.now()
            sec = now.second            
            if sec != last_sec:
                last_sec = sec
                if sec == 5:
                    self.client.publish("olulu/all/trigger", "1")
            time.sleep(0.2)

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        print("[連線] 已成功連線至 MQTT Broker。")
        client.subscribe("device/+/status") 
        client.subscribe("device/+/weight")
        client.subscribe("olulu/system/#")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code=None, properties=None):
        print(f"[警告] 與 MQTT Broker 斷開連線！")

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            if msg.topic.startswith("device/"):
                parts = msg.topic.split('/')
                self.work_queue.put(("mqtt_device", parts[1], parts[2], payload))
            elif msg.topic.startswith("olulu/system/"):
                self.work_queue.put(("mqtt_system", msg.topic, payload))
        except: pass

    def queue_worker_thread(self):
        while True:
            try:
                task = self.work_queue.get() 
                kind = task[0]
                
                if kind == "mqtt_device":
                    sensor_id, mtype, val = task[1], task[2], task[3]
                    if mtype == "status":
                        if val == "online": self.online_sensors.add(sensor_id)
                        else:
                            self.online_sensors.discard(sensor_id)
                            for bed in self.beds.values():
                                if bed.sensor_id == sensor_id: bed.is_online = False
                    elif mtype == "weight":
                        self.online_sensors.add(sensor_id) 
                        target_bed = next((b for b in self.beds.values() if b.sensor_id == sensor_id), None)
                     
                        if target_bed:
                            try:
                                weight_float = float(val)
                                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                                
                                target_bed.add_data(timestamp, weight_float)
                                target_bed.is_online = True
                                
                                if target_bed.patient_id:
                                    self.write_buffer.put((target_bed.patient_id, timestamp, weight_float, sensor_id))
                                    # print(f"[寫入] 成功呼叫存檔，病歷號: {target_bed.patient_id}")
                            except Exception as e: 
                                print(f"[錯誤] 處理重量數據失敗: {e}")
                
                elif kind == "mqtt_system":
                    topic, payload = task[1], task[2]
                    
                    if topic == "olulu/system/req_config":
                        config_data = {n: b.to_dict() for n, b in self.beds.items()}
                        self.client.publish("olulu/system/state_update", json.dumps(config_data))

                    elif topic == "olulu/system/req_history":
                        bed_name = payload
                        if bed_name in self.beds and self.beds[bed_name].patient_id:
                            history_payload = json.dumps(self.beds[bed_name].history)
                            self.client.publish(f"olulu/system/res_history/{bed_name}", history_payload)
                            print(f"🚀 已將 {bed_name} 記憶體資料 ({len(self.beds[bed_name].history)}筆) 秒傳給 Mi。")

                    elif topic == "olulu/system/req_bind":
                        data = json.loads(payload)
                        req_sensor = data["sensor_id"]
                        req_bed = data["bed_name"]
                        controller_id = data["controller_id"]
                        
                        is_sensor_used = any(b.sensor_id == req_sensor for b in self.beds.values())
                        
                        if is_sensor_used:
                            self.client.publish(f"olulu/system/bind_reject/{controller_id}", "此設備已被登錄，請選擇其他設備。")
                            print(f"[拒絕] {controller_id} 嘗試綁定 {req_bed} 與 {req_sensor}，但設備已被佔用。")
                        else:
                            self.beds[req_bed].sensor_id = req_sensor
                            self.beds[req_bed].patient_id = data["patient_id"]
                            self.beds[req_bed].load_history_from_csv()
                            self.save_config()
                            
                            self.client.publish(f"olulu/system/bind_success/{controller_id}", "OK")
                            config_data = {n: b.to_dict() for n, b in self.beds.items()}
                            self.client.publish("olulu/system/state_update", json.dumps(config_data))
                            print(f"[成功] 床位 {req_bed} 成功綁定病人 {data['patient_id']} (設備: {req_sensor})")

                    elif topic == "olulu/system/unbind":
                        bed_name = payload
                        if bed_name in self.beds:
                            patient_id = self.beds[bed_name].patient_id
                            print(f"[系統] 準備登出 {bed_name}，正在強制存檔...")
                            self.flush_event.set()
                            
                            self.beds[bed_name].clear_assignment()
                            self.save_config()
                            config_data = {n: b.to_dict() for n, b in self.beds.items()}
                            self.client.publish("olulu/system/state_update", json.dumps(config_data))
                            print(f"[成功] 床位 {bed_name} 已登出 (原病人: {patient_id})")

                    elif topic == "olulu/system/force_flush":
                        print("[系統] 收到強制存檔請求，正在喚醒存檔執行緒...")
                        self.flush_event.set()
                        
                self.work_queue.task_done()
            except Exception as e: 
                print(f"[錯誤] 背景佇列處理異常: {e}")


if __name__ == "__main__":
    # 1. 初始化並啟動 MQTT Broker 背景服務
    broker = HLBroker()
    broker.start() 
    
    # 2. 啟動 Flask 網頁伺服器 (接管主執行緒)
    print("🌐 OLuLu Web Server 已同步啟動！")
    print("👉 看圖首頁: http://[伺服器IP]:5000")
    print("⚙️ 管理後台: http://[伺服器IP]:5000/admin (帳號: admin, 密碼: olulu)")
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    finally:
        # 3. 捕捉 Ctrl+C 或任何中斷，執行安全關機
        broker.shutdown()
