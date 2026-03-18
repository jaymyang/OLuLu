print('===============================================================')
print('     %%%%%  %%        %%             OLuLu Broker    ')
print('    %%   %% %% %% %%  %% %% %%    Copyright Jay Ming-chieh Yang 2026.')   
print('    %%   %% %% %% %%  %% %% %%       [物聯網核心] 背景伺服器版   ')
print('     %%%%%  %%  %%%%% %%  %%%%%     Target OS: windows')
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


print('     Kóo-tsui ê LuLu, khó-ài ê LuLu, OLuLu, OLuLu, OLuLu, OLuLu.     ')


# ================= 系統參數設定 =================
BROKER_IP = "localhost"        # Broker 自己就在這台機器上
BROKER_PORT = 1883             
CONFIG_FILE = "bed_config.json"

DEFAULT_BED_LIST = ["3L01", "3L02", "3L03", "3L05", "3L06", "3L07", "3L08", "3L09", "3K17", "3K18"]

# ------------------ Linux Mosquitto 提示 ------------------
if os.name == 'nt':
    print("[系統] 偵測到 Windows 環境，請確保 Mosquitto 已經手動啟動。")
else:
    print("[系統] 偵測到 Linux/Unihiker 環境。")
    print("       請確保已透過 sudo systemctl enable mosquitto 啟動服務。")

# ================= 資料格式設定 (具備硬碟讀寫能力) =================
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

    #def _save_to_csv(self, timestamp, weight):
    #    if not self.patient_id: return
    #    base_dir = os.path.dirname(os.path.abspath(__file__))
    #    filename = os.path.join(base_dir, f"{self.patient_id}.csv")
    #    try:
    #        file_exists = os.path.isfile(filename)
    #        with open(filename, "a", newline="", encoding='utf-8') as f:
    #            writer = csv.writer(f)
    #            if not file_exists: writer.writerow(["Time", "Weight", "SensorID"])
    #            writer.writerow([timestamp, weight, self.sensor_id])
    #    except Exception as e:
    #        print(f"[錯誤] 存檔失敗 ({self.patient_id}.csv): {e}")

    def clear_assignment(self):
        self.sensor_id = None  
        self.patient_id = None 
        self.is_online = False 
        self.history = []

    def load_history_from_csv(self):
        if not self.patient_id: return
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, f"{self.patient_id}.csv")
        
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

# ================== 主程式 (背景伺服器) ==================   
class HLBroker:
    def __init__(self):
        self.beds = {name: BedModel(name) for name in DEFAULT_BED_LIST}
        self.online_sensors = set()
        self.work_queue = queue.Queue()         
        self.write_buffer = queue.Queue()# 專門存放「待寫入磁碟」數據的緩衝區
        self.flush_event = threading.Event() # 用來提早喚醒寫入執行緒的事件
        self.load_config() 

        # MQTT 設定 (相容 Python 3.7+ 的寫法)
        try:
            # 嘗試使用 VERSION2 (Paho 2.0+)
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="olulu_broker_master")
        except AttributeError:
            # 如果 Unihiker 上裝的是舊版 Paho (1.6.x)，自動退回舊版寫法，確保不報錯
            self.client = mqtt.Client(client_id="olulu_broker_master")

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message        

    def start(self):
        try:
            self.client.connect(BROKER_IP, BROKER_PORT, 60) # 背景程式用阻塞式 connect 較為穩定
            self.client.loop_start() 
            print("[狀態] MQTT 核心已啟動，監聽 1883 埠...")
        except Exception as e:
            print(f"[致命錯誤] MQTT 連線失敗: {e}")
            sys.exit(1)

        # 啟動時鐘廣播執行緒
        threading.Thread(target=self.timer_sync_clock_thread, daemon=True).start()
        # 啟動工作佇列消化執行緒 (取代 Tkinter 的 self.after)
        threading.Thread(target=self.queue_worker_thread, daemon=True).start()
        # 啟動整批寫入執行緒
        threading.Thread(target=self.batch_write_worker, daemon=True).start()        
        print("[狀態] OLuLu Broker 背景服務運作中。按 Ctrl+C 終止。")
        
        # 保持主程式運行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[系統] 收到中斷訊號，開始關閉伺服器...")
            # --- 把尚未存檔的緩衝區資料寫入硬碟 ---
            if not self.write_buffer.empty():
                print(f"[系統] 正在將緩衝區剩餘的 {self.write_buffer.qsize()} 筆資料寫入硬碟，請稍候...")
                pending_data = {}
                while not self.write_buffer.empty():
                    pid, ts, weight, sid = self.write_buffer.get()
                    if pid not in pending_data:
                        pending_data[pid] = []
                    pending_data[pid].append([ts, weight, sid])
                
                for pid, rows in pending_data.items():
                    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{pid}.csv")
                    try:
                        file_exists = os.path.isfile(filename)
                        with open(filename, "a", newline="", encoding='utf-8') as f:
                            writer = csv.writer(f)
                            if not file_exists:
                                writer.writerow(["Time", "Weight", "SensorID"])
                            writer.writerows(rows)
                    except Exception as e:
                        print(f"[錯誤] 最後存檔失敗 ({pid}.csv): {e}")
            # -------------------------------------------------
            self.save_config()
            self.client.loop_stop()
            self.client.disconnect()
            print("[系統] OLuLu Broker 已安全關閉。")

    # ------------------ 設定檔讀寫 ------------------
    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump({n: b.to_dict() for n, b in self.beds.items()}, f, indent=4)
        except Exception as e: 
            print(f"[錯誤] 設定檔存檔失敗: {e}")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE): 
            print("[系統] 找不到現有設定檔，將以全新狀態啟動。")
            return
        try:
            with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                for name, d in json.load(f).items():
                    if name in self.beds: 
                        self.beds[name].from_dict(d)
                        if self.beds[name].patient_id:
                            self.beds[name].load_history_from_csv()
            print("[系統] 成功載入上一次的床位綁定設定。")
        except Exception as e: 
            print(f"[錯誤] 讀取設定檔失敗: {e}")
    # ------------------ 整批讀寫 ------------------
    def batch_write_worker(self):
        """每 30 分鐘集中處理一次所有床位的檔案寫入"""
        while True:
            # 這裡設定等待時間 (例如 1800 秒 = 30 分鐘)，但可被事件喚醒
            self.flush_event.wait(1800)
            self.flush_event.clear() # 醒來後把鬧鐘重置
            if self.write_buffer.empty():
                continue # 如果被叫醒但其實沒資料，就繼續下一輪            
            # 建立本輪寫入的資料集，減少 Open 檔案次數
            pending_data = {}
            while not self.write_buffer.empty():
                pid, ts, weight, sid = self.write_buffer.get()
                if pid not in pending_data:
                    pending_data[pid] = []
                pending_data[pid].append([ts, weight, sid])
            
            # 集中開啟各病人的檔案進行寫入
            for pid, rows in pending_data.items():
                filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{pid}.csv")
                try:
                    file_exists = os.path.isfile(filename)
                    with open(filename, "a", newline="", encoding='utf-8') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Time", "Weight", "SensorID"])
                        writer.writerows(rows) # 使用 writerows 一次寫入多筆
                except Exception as e:
                    print(f"[錯誤] 批量存檔失敗 ({pid}.csv): {e}")

    # ================== 核心業務：通訊與排程 ==================
    def timer_sync_clock_thread(self):
        """背景執行緒定時器：精確計時發送全體秤重指令"""
        last_sec = -1
        while True:
            now = datetime.datetime.now()
            sec = now.second            
            if sec != last_sec:
                last_sec = sec
                if sec == 5:
                    self.client.publish("olulu/all/trigger", "1")
                    # print(f"[{now.strftime('%H:%M:%S')}] 發送全體秤重指令") # 可取消註解以監控秒數
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
            #print(payload)
            if msg.topic.startswith("device/"):
                parts = msg.topic.split('/')
                self.work_queue.put(("mqtt_device", parts[1], parts[2], payload))
            elif msg.topic.startswith("olulu/system/"):
                self.work_queue.put(("mqtt_system", msg.topic, payload))
        except: pass

    def queue_worker_thread(self):
        """專門負責消化佇列的背景執行緒，完全不會卡住 MQTT 接收"""
        while True:
            try:
                task = self.work_queue.get() # 阻塞等待任務進來
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
                                
                                # 1. 僅更新記憶體 (因為我們剛剛拔掉了 add_data 裡的存檔功能)
                                target_bed.add_data(timestamp, weight_float)
                                target_bed.is_online = True
                                
                                # 2. 🟢 核心修改：把資料丟進寫入緩衝區 (write_buffer)
                                if target_bed.patient_id:
                                    self.write_buffer.put((target_bed.patient_id, timestamp, weight_float, sensor_id))
                                    print(f"[寫入] 成功呼叫存檔，病歷號: {target_bed.patient_id}")
                            except Exception as e: 
                                # 如果有錯應警示
                                print(f"[嚴重] 寫入 CSV 失敗: {e}")
                
                # 處理 Controller 發來的請求
                elif kind == "mqtt_system":
                    topic, payload = task[1], task[2]
                    
                    if topic == "olulu/system/req_config":
                        config_data = {n: b.to_dict() for n, b in self.beds.items()}
                        self.client.publish("olulu/system/state_update", json.dumps(config_data))

                    elif topic == "olulu/system/req_history":
                        bed_name = payload
                        if bed_name in self.beds and self.beds[bed_name].patient_id:
                            # 直接把記憶體裡的歷史紀錄轉成 JSON 發布出去
                            history_payload = json.dumps(self.beds[bed_name].history)
                            self.client.publish(f"olulu/system/res_history/{bed_name}", history_payload)
                            print(f"🚀 [快取派發] 已將 {bed_name} 記憶體資料 ({len(self.beds[bed_name].history)}筆) 秒傳給 Mi。")
                    elif topic == "olulu/system/req_bind":
                        data = json.loads(payload)
                        req_sensor = data["sensor_id"]
                        req_bed = data["bed_name"]
                        controller_id = data["controller_id"]
                        
                        is_sensor_used = any(b.sensor_id == req_sensor for b in self.beds.values())
                        
                        if is_sensor_used:
                            self.client.publish(f"olulu/system/bind_reject/{controller_id}", "此設備剛被其他護理站綁定，請選擇其他設備。")
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

                            # 🟢 背景執行緒把緩衝區的資料通通寫進硬碟
                            print(f"[系統] 準備登出 {bed_name}，正在強制觸發存檔...")
                            self.flush_event.set()
                            
                            self.beds[bed_name].clear_assignment()
                            self.save_config()
                            config_data = {n: b.to_dict() for n, b in self.beds.items()}
                            self.client.publish("olulu/system/state_update", json.dumps(config_data))
                            print(f"[成功] 床位 {bed_name} 已登出 (原病人: {patient_id})")

                    # 🟢 備用機制：強制存檔 (留著以備不時之需)
                    elif topic == "olulu/system/force_flush":
                        print("[系統] 收到強制存檔請求，正在喚醒存檔執行緒...")
                        self.flush_event.set()
                        
                self.work_queue.task_done()
            except Exception as e: 
                print(f"[錯誤] 背景佇列處理異常: {e}")

if __name__ == "__main__":
    broker = HLBroker()
    broker.start()
