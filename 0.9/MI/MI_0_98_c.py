import tkinter as tk
from tkinter import ttk, messagebox
import json
import paho.mqtt.client as mqtt

BROKER_IP = "192.168.50.128" 
BROKER_PORT = 1883
FREQUENCY_OPTIONS = [1, 2, 4, 8]

class MiStandaloneController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MI 報表通報系統控制台")
        self.geometry("650x500")
        self.configure(bg="#F5F7FA")
        
        self.beds_data = {} 
        self.interval_hours = tk.IntVar(value=FREQUENCY_OPTIONS[0])
        
        self.setup_ui()
        self.setup_mqtt()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 10))

        # --- 頂部：排程設定 ---
        top_frame = tk.Frame(self, bg="#F5F7FA")
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=15)
        
        tk.Label(top_frame, text="自動寄送頻率：", bg="#F5F7FA", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        freq_menu = ttk.OptionMenu(top_frame, self.interval_hours, self.interval_hours.get(), *FREQUENCY_OPTIONS)
        freq_menu.pack(side=tk.LEFT, padx=5)
        tk.Label(top_frame, text="小時", bg="#F5F7FA", font=("Arial", 12)).pack(side=tk.LEFT)
        
        btn_apply = tk.Button(top_frame, text="💾 儲存並套用定時排程", command=self.apply_schedule, bg="#4CAF50", fg="white", font=("Arial", 11, "bold"))
        btn_apply.pack(side=tk.RIGHT, padx=5)

        # --- 中間：雙清單選擇器 ---
        mid_frame = tk.Frame(self, bg="#F5F7FA")
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        left_frame = tk.LabelFrame(mid_frame, text="目前在床病人", font=("Arial", 10, "bold"), bg="#DEFFAC")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_avail = tk.Listbox(left_frame, selectmode=tk.EXTENDED, font=("Consolas", 12))
        self.list_avail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        btn_frame = tk.Frame(mid_frame, bg="#F5F7FA")
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=50)
        ttk.Button(btn_frame, text="加入 >", command=self.move_to_right).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="< 移除", command=self.move_to_left).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="全部加入 >>", command=self.move_all_right).pack(fill=tk.X, pady=15)
        ttk.Button(btn_frame, text="<< 全部移除", command=self.move_all_left).pack(fill=tk.X, pady=5)
        
        right_frame = tk.LabelFrame(mid_frame, text="已加入定時傳送名單", font=("Arial", 10, "bold"), bg="#F2E6E6")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.list_selected = tk.Listbox(right_frame, selectmode=tk.EXTENDED, font=("Consolas", 12))
        self.list_selected.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 底部：傳送控制 ---
        bottom_frame = tk.Frame(self, bg="#F5F7FA")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=15)
        
        btn_refresh = tk.Button(bottom_frame, text="刷新床位", command=self.request_bed_status, bg="#20B2AA", fg="white", font=("Arial", 11))
        btn_refresh.pack(side=tk.LEFT)
        
        btn_manual = tk.Button(bottom_frame, text="立即手動寄出 (不影響排程)", command=self.trigger_email_report, bg="#FF5252", fg="white", font=("Arial", 11, "bold"))
        btn_manual.pack(side=tk.RIGHT)

    def setup_mqtt(self):
        self.client = mqtt.Client(client_id="mi_standalone_controller")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        try:
            self.client.connect(BROKER_IP, BROKER_PORT, 60)
            self.client.loop_start() 
        except Exception as e:
            messagebox.showerror("連線失敗", f"無法連線至 Broker:\n{e}")

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        self.client.subscribe("olulu/system/state_update")
        self.client.subscribe("olulu/mi/schedule_update") # 🌟 【新增】訂閱排程更新廣播
        
        # 連線成功後，同時向 Broker 索取「床位狀態」與「MI 排程狀態」
        self.request_bed_status()
        self.client.publish("olulu/mi/req_schedule", "req") 

    def on_message(self, client, userdata, msg):
        try:
            payload_data = json.loads(msg.payload.decode('utf-8'))
            
            # 收到床位更新
            if msg.topic == "olulu/system/state_update":
                self.beds_data = payload_data
                self.after(0, self.refresh_ui_list)
                
            # 🌟 【新增】收到別人(或自己)更新的 MI 排程廣播！
            elif msg.topic == "olulu/mi/schedule_update":
                self.after(0, lambda: self.sync_schedule_to_ui(payload_data))
                
        except Exception: pass

    def sync_schedule_to_ui(self, schedule_data):
        """將 Broker 傳來的最新排程，強制覆蓋到目前的 UI 上"""
        # 1. 更新頻率下拉選單
        self.interval_hours.set(schedule_data.get("interval", 1))
        
        # 2. 取得排程中的病歷號名單
        scheduled_pids = schedule_data.get("scheduled_patients", [])
        
        # 3. 重建右側清單 (將純病歷號還原成 [床位] 病歷號 的格式)
        self.list_selected.delete(0, tk.END)
        for bed_name, info in self.beds_data.items():
            pid = info.get("patient_id")
            if pid and pid in scheduled_pids:
                self.list_selected.insert(tk.END, f"[{bed_name}] {pid}")
                
        # 4. 呼叫防閃爍更新，讓左側清單自動剔除已經在右側的人
        self.refresh_ui_list()

    def request_bed_status(self):
        self.client.publish("olulu/system/req_config", "req")
        
    def refresh_ui_list(self):
        """智慧更新：先比對名單是否真的有變動，沒變動就不重畫，避免干擾使用者點選"""
        active_items = []
        for bed_name, info in self.beds_data.items():
            pid = info.get("patient_id")
            if pid: active_items.append(f"[{bed_name}] {pid}")

        # 取得目前左右兩邊現有的名單
        current_avail = list(self.list_avail.get(0, tk.END))
        current_selected = list(self.list_selected.get(0, tk.END))

        # 計算現在左邊「理應」要出現的名單
        should_be_avail = [item for item in active_items if item not in current_selected]

        # 🟢 關鍵防呆：如果左邊該顯示的人沒變，右邊選好的人也都還在床上，那就「什麼都不要做」！
        if current_avail == should_be_avail and all(item in active_items for item in current_selected):
            return

        # 只有在有人登入/登出時，才重新繪製 UI
        self.list_selected.delete(0, tk.END)
        for item in current_selected:
            if item in active_items: 
                self.list_selected.insert(tk.END, item)

        self.list_avail.delete(0, tk.END)
        for item in should_be_avail:
            self.list_avail.insert(tk.END, item)

    def move_to_right(self):
        for i in reversed(self.list_avail.curselection()):
            self.list_selected.insert(tk.END, self.list_avail.get(i))
            self.list_avail.delete(i)
        self.apply_schedule(silent=True) # 🌟 自動同步！

    def move_to_left(self):
        for i in reversed(self.list_selected.curselection()):
            self.list_avail.insert(tk.END, self.list_selected.get(i))
            self.list_selected.delete(i)
        self.apply_schedule(silent=True) # 🌟 自動同步！

    def move_all_right(self):
        for item in self.list_avail.get(0, tk.END): 
            self.list_selected.insert(tk.END, item)
        self.list_avail.delete(0, tk.END)
        self.apply_schedule(silent=True) # 🌟 自動同步！

    def move_all_left(self):
        for item in self.list_selected.get(0, tk.END): 
            self.list_avail.insert(tk.END, item)
        self.list_selected.delete(0, tk.END)
        self.apply_schedule(silent=True) # 🌟 自動同步！

    def apply_schedule(self, silent=False):
        """將設定好的頻率與名單，正式發送給背景服務儲存"""
        items_to_send = self.list_selected.get(0, tk.END)
        # 加入防呆，確保只擷取有病歷號格式的字串
        patient_ids = [item.split("] ")[1] for item in items_to_send if "] " in item]
        
        payload = {
            "interval": self.interval_hours.get(),
            "scheduled_patients": patient_ids
        }
        self.client.publish("olulu/mi/set_schedule", json.dumps(payload))
        
        # 只有在手動按下按鈕時，才跳出提示窗
        if not silent:
            messagebox.showinfo("排程已更新", f"已通知伺服器！\n目前設定為每 {self.interval_hours.get()} 小時自動寄送一次。")
    def trigger_email_report(self):
        """手動立即寄送 (拔除了清空清單的指令)"""
        items_to_send = self.list_selected.get(0, tk.END)
        if not items_to_send:
            messagebox.showinfo("提示", "請先選擇要通報的病患！")
            return
            
        patient_ids = [item.split("] ")[1] for item in items_to_send]
        payload = {
            "controller_id": "Standalone_MI_Controller",
            "target_patients": patient_ids,
            "method": "email",
            "address": "jjsamsungcb@gmail.com" 
        }
        self.client.publish("olulu/mi/req_report", json.dumps(payload))
        messagebox.showinfo("發送成功", "手動通報指令已傳送給伺服器處理！")

    def on_closing(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except: pass
        self.destroy()

if __name__ == "__main__":
    app = MiStandaloneController()
    app.mainloop()
