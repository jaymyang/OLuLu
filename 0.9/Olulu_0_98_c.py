# -*- coding: utf-8 -*-
print('     %%%%%  %%        %%             Online Urine levering Utility   ')
print('    %%   %% %% %% %%  %% %% %%    Copyright Jay Ming-chieh Yang 2026.')   
print('    %%   %% %% %% %%  %% %% %%       Photo credit: Olulu the Poodle')
print('    %%   %% %% %% %%  %% %% %%        Theme color code is from      ') 
print('     %%%%%  %%  %%%%% %%  %%%%%       Yosun Blind Co. Ltd, 1985.     ')
print('')
print('     Kóo-tsui ê LuLu, khó-ài ê LuLu, OLuLu, OLuLu, OLuLu, OLuLu.      ')
print('         Kóo-tsui ê LuLu, khó-ài ê LuLu, LuLu LuLu LuLu, OLuLu.       ')

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import paho.mqtt.client as mqtt
import json
import datetime
import time
import queue
import math
import os
import sys
import threading
from PIL import Image, ImageTk
import random

# ================= 資源路徑設定 (相容 PyInstaller 打包) =================
def resource_path(relative_path):
    """取得資源的絕對路徑。相容開發測試環境與 PyInstaller 打包環境"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ================= 系統參數設定 =================
BROKER_IP = "192.168.50.128"        # MQTT 伺服器 IP
BROKER_PORT = 1883             # MQTT 連接埠
THEMES_FILE = "themes.csv"     # 佈景主題

DEFAULT_BED_LIST = [
    "3L01", "3L02", "3L03", "3L05", "3L06",
    "3L07", "3L08", "3L09", "3K17", "3K18"
]

# ================= 資料格式設定 (Controller 版) =================
class BedModel:
    def __init__(self, name):
        self.name = name           
        self.sensor_id = None      
        self.patient_id = None     
        self.history = []    
        self.is_online = False     
        self.is_alert = False      

    def add_data(self, timestamp, weight):
        self.history.append((timestamp, weight))
        if len(self.history) > 480:
            self.history.pop(0)
            
        if len(self.history) >= 2:
            diff = self.history[-1][1] - self.history[-2][1]
            if diff < -100: self.is_alert = True
            else: self.is_alert = False

    def clear_assignment(self):
        self.sensor_id = None  
        self.patient_id = None 
        self.is_online = False 
        self.is_alert = False  
        self.history = []

# =================  取得開機與待機圖片 =================
def get_resized_image(image_path, target_height):
    try:
        if not os.path.exists(image_path):
            return None, 0
        with Image.open(image_path) as img:
            orig_w, orig_h = img.size
            ratio = target_height / orig_h
            target_width = int(orig_w * ratio)
            resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(resized_img)
            return tk_img, target_width
    except Exception as e:
        return None, 0

# ================== 主程式 UI 控制器 ==================   
class OLuLuSystem(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.my_controller_id = f"Station_{random.randint(1000, 9999)}"
        
        self.title(f"OLuLu 遠端監控儀表板 - {self.my_controller_id}")
        window_width = int(self.winfo_screenwidth() * 0.9)
        window_height = int(self.winfo_screenheight() * 0.9)
        self.geometry(f"{window_width}x{window_height}")
        
        if os.name == 'nt':
            try: self.state('zoomed')
            except: pass
            import ctypes
            try: ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
            except: pass

        self.load_themes()
        self.configure(bg=self.theme["bg_main"])
        self.load_images()
        
        self.beds = {name: BedModel(name) for name in DEFAULT_BED_LIST}
        self.online_sensors = set()
        self.current_viewing_bed = None
        self.chart_style = "line"
        self.view_minutes = 60
        self.gui_queue = queue.Queue()
        
        self.setup_ui()
        self.log("系統初始化完成，準備連線...")
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2) 
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message        
        try:
            self.client.connect_async(BROKER_IP, BROKER_PORT, 60)
            self.client.loop_start() 
            self.log("Controller MQTT 連線機制已啟動...")
        except Exception as e:
            self.log(f"MQTT 啟動連線發生錯誤: {e}")

        self.timer_process_queue()   
        self.timer_alert_flash()     
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, message):
        """將除錯訊息送入 UI 佇列，顯示在訊息視窗中"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        self.gui_queue.put(("log", full_msg))
        print(full_msg) 

    def load_images(self): 
        screen_h = self.winfo_screenheight()
        path_startup = resource_path("copyright_1.jpg")
        self.img_startup, self.startup_w = get_resized_image(path_startup, int(screen_h * 0.40))
        path_standby = resource_path("copyright_2.jpg")
        self.img_standby, self.standby_w = get_resized_image(path_standby, int(screen_h * 0.40))

    def load_themes(self):
        import csv
        keys = ["thene_name", "bg_main", "bg_card", "primary", "alert", "text_dark", "text_light", "online", "offline", 
                "chart_line", "chart_fill", "chart_line_high", "chart_fill_high"] 
        default_themes = [
            ["default_day","#F5F7FA", "#FFFFFF", "#20B2AA", "#FF5252", "#2F3542", "#A4B0BE", "#2ECC71", "#BDC3C7", "#FF9F43", "#FFE8D1", "#7BED9F", "#E2F9EB"],
            ["default_night","#1E1E1E", "#2D2D2D", "#007ACC", "#E51400", "#FFFFFF", "#AAAAAA", "#00FF00", "#555555", "#00FFAA", "#004433", "#2ED573", "#1B5E20"]
        ]
        self.themes = []
        try:
            with open(THEMES_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader: self.themes.append(row)
        except: pass
        if not self.themes: self.themes = [dict(zip(keys, default_themes[0]))]
        self.current_theme_idx = 0                       
        self.theme = self.themes[self.current_theme_idx] 

    def cycle_theme(self, event=None):
        self.current_theme_idx = (self.current_theme_idx + 1) % len(self.themes)
        self.theme = self.themes[self.current_theme_idx]
        self.apply_theme()

    def apply_theme(self):
        t = self.theme
        self.configure(bg=t["bg_main"])
        self.bg_canvas.config(bg=t["bg_main"])
        self.main_container.config(bg=t["bg_main"])
        self.left_card.config(bg=t["bg_card"])
        self.info_frame.config(bg=t["bg_card"])
        self.info_label.config(bg=t["bg_card"], fg=t["text_dark"])
        self.conn_canvas.config(bg=t["bg_card"])
        self.canvas.config(bg=t["bg_card"])
        
        # 【更新】替底部三個子框架上色
        self.bottom_frame.config(bg=t["bg_card"])
        self.btm_left.config(bg=t["bg_card"])
        self.btm_right.config(bg=t["bg_card"])
        
        self.btn_logout.config(bg=t["bg_main"], fg=t["text_dark"])
        self.btn_toggle_time.config(bg=t["bg_main"], fg=t["text_dark"])
        corner_color = t["text_dark"] 
        self.bg_canvas.itemconfig(self.corner_tl, fill=corner_color)
        self.bg_canvas.itemconfig(self.corner_tr, fill=corner_color)
        self.bg_canvas.itemconfig(self.corner_bl, fill=corner_color)
        self.bg_canvas.itemconfig(self.corner_br, fill=corner_color)
        self.refresh_all_buttons()
        self.update_chart_display()

    def setup_ui(self):
        t = self.theme
        
        self.bg_canvas = tk.Canvas(self, bg=t["bg_main"], highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        corner_color = t["text_dark"] 
        self.corner_tl = self.bg_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=corner_color, outline="")
        self.corner_tr = self.bg_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=corner_color, outline="")
        self.corner_bl = self.bg_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=corner_color, outline="")
        self.corner_br = self.bg_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=corner_color, outline="")
        self.bg_canvas.bind("<Configure>", self.update_corners_position)

        self.main_container = tk.Frame(self, bg=t["bg_main"])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)

        self.left_card = tk.Frame(self.main_container, bg=t["bg_card"], relief="flat")
        self.left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        self.info_frame = tk.Frame(self.left_card, bg=t["bg_card"])
        self.info_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.info_label = tk.Label(self.info_frame, text="系統連線中...", font=("Microsoft JhengHei UI", 16, "bold"), 
                                   bg=t["bg_card"], fg=t["text_dark"])
        self.info_label.pack(side=tk.LEFT, padx=5)

        self.conn_canvas = tk.Canvas(self.info_frame, width=20, height=20, bg=t["bg_card"], highlightthickness=0)
        self.conn_canvas.pack(side=tk.RIGHT, padx=10)
        self.conn_light = self.conn_canvas.create_oval(2, 2, 18, 18, fill="red", outline="gray")

        # ================== 【核心排版修改】將 Log 塞入按鈕之間 ==================
        self.bottom_frame = tk.Frame(self.left_card, bg=t["bg_card"], height=100) # 給予 100 像素的高度
        self.bottom_frame.pack_propagate(False) 
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 10))
        
        # 底部左側：裝載「切換時間」按鈕 (固定寬度 200)
        self.btm_left = tk.Frame(self.bottom_frame, bg=t["bg_card"], width=200)
        self.btm_left.pack_propagate(False)
        self.btm_left.pack(side=tk.LEFT, fill=tk.Y)
        
        # 底部右側：裝載「登出」按鈕 (固定寬度 120)
        self.btm_right = tk.Frame(self.bottom_frame, bg=t["bg_card"], width=120)
        self.btm_right.pack_propagate(False)
        self.btm_right.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 底部中間：裝載「Log 訊息視窗」 (自動延展填滿剩下的空間)
        self.log_frame = tk.Frame(self.bottom_frame, bg="#1E1E1E")
        self.log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        self.log_text = tk.Text(self.log_frame, bg="#1E1E1E", fg="#00FF00", font=("Consolas", 10), state=tk.DISABLED, relief="flat")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_scroll = tk.Scrollbar(self.log_frame, command=self.log_text.yview, bg="#2D2D2D")
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=self.log_scroll.set)

        self.btn_toggle_time = tk.Button(self.btm_left, text="切換: 目前顯示 60 分鐘", 
                                         bg=t["bg_main"], fg=t["text_dark"],
                                         command=self.toggle_time_view, font=("Arial", 12))
        self.btn_logout = tk.Button(self.btm_right, text="登出此床位", 
                                    bg=t["bg_main"], fg=t["text_dark"],
                                    command=self.logout_current_bed, font=("Arial", 12))
        # =========================================================================

        self.canvas = tk.Canvas(self.left_card, bg=t["bg_card"], highlightthickness=0, cursor="hand2")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        self.canvas.bind("<Button-1>", self.cycle_theme)

        self.right_card = tk.Frame(self.main_container, bg=t["bg_card"], width=280)
        self.right_card.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_card.pack_propagate(False) 

        self.bed_buttons = {}
        for name in DEFAULT_BED_LIST:
            btn = tk.Button(self.right_card, text=name, font=("Microsoft JhengHei UI", 12, "bold"),
                            bg=t["bg_card"], relief="raised",
                            command=lambda n=name: self.on_bed_click(n))
            btn.pack(fill=tk.X, padx=5, pady=2)
            self.bed_buttons[name] = btn

        self.lbl_chart_hint = tk.Label(self.right_card, text="(點擊空白處切換圖表)", bg=t["bg_card"], fg=t["text_light"], font=("Arial", 9))
        self.lbl_chart_hint.pack(side=tk.BOTTOM, pady=10)        
        self.right_card.bind("<Button-1>", self.toggle_chart_style)
        self.lbl_chart_hint.bind("<Button-1>", self.toggle_chart_style)

        self.refresh_all_buttons()
        self.update_chart_display()

    def update_corners_position(self, event):
        w, h = self.bg_canvas.winfo_width(), self.bg_canvas.winfo_height()
        r, steps = 25, 10
        tl_pts = [0, 0, r, 0]
        for i in range(steps + 1):
            ang = math.radians(90 + (90 * i / steps))
            tl_pts.extend([r + r * math.cos(ang), r - r * math.sin(ang)])
        tl_pts.extend([0, r])
        self.bg_canvas.coords(self.corner_tl, *tl_pts)
        
        tr_pts = [w, 0, w, r]
        for i in range(steps + 1):
            ang = math.radians(0 + (90 * i / steps))
            tr_pts.extend([w - r + r * math.cos(ang), r - r * math.sin(ang)])
        tr_pts.extend([w - r, 0])
        self.bg_canvas.coords(self.corner_tr, *tr_pts)
        
        br_pts = [w, h, w - r, h]
        for i in range(steps + 1):
            ang = math.radians(270 + (90 * i / steps))
            br_pts.extend([w - r + r * math.cos(ang), h - r - r * math.sin(ang)])
        br_pts.extend([w, h - r])
        self.bg_canvas.coords(self.corner_br, *br_pts)
        
        bl_pts = [0, h, 0, h - r]
        for i in range(steps + 1):
            ang = math.radians(180 + (90 * i / steps))
            bl_pts.extend([r + r * math.cos(ang), h - r - r * math.sin(ang)])
        bl_pts.extend([r, h])
        self.bg_canvas.coords(self.corner_bl, *bl_pts)

    def on_closing(self):
        if messagebox.askyesno("確認離開", "確定要關閉 OLuLu 監控介面嗎？"):
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except: pass
            self.destroy()

    def toggle_time_view(self):
        self.view_minutes = 480 if self.view_minutes == 60 else 60
        self.btn_toggle_time.config(text=f"切換: 目前顯示 {self.view_minutes} 分鐘")
        self.update_chart_display()

    # ================== 【Controller 專用指令邏輯】 ==================
    def on_bed_click(self, bed_name):
        bed = self.beds[bed_name]
        if bed.sensor_id is None:
            self.show_login_dialog(bed_name) 
        else:
            self.current_viewing_bed = bed_name
            # 【修改】讓按鈕在左右區塊內「垂直置中」顯示
            self.btn_toggle_time.pack(expand=True)
            self.btn_logout.pack(expand=True)
            
            self.log(f"向 Broker 索取床位 {bed_name} 歷史資料...")
            self.client.publish("olulu/system/req_history", bed_name)
            self.update_chart_display()

    def show_login_dialog(self, bed_name):
        assigned_ids = [b.sensor_id for b in self.beds.values() if b.sensor_id]
        available = [sid for sid in self.online_sensors if sid not in assigned_ids]
        
        if not available:
            messagebox.showwarning("無可用設備", "目前沒有閒置的設備在線上。")
            return

        dialog = tk.Toplevel(self) 
        dialog.title(f"登錄床位 {bed_name}")
        dialog.geometry("300x400")
        dialog.grab_set()
        
        tk.Label(dialog, text="1. 選擇感測器", font=("bold")).pack(pady=5)
        lb = tk.Listbox(dialog)
        for sensor in sorted(available): lb.insert(tk.END, sensor)
        lb.pack(pady=5)
        
        tk.Label(dialog, text="2. 輸入病歷號", font=("bold")).pack(pady=5)
        entry_pid = tk.Entry(dialog) 
        entry_pid.pack(pady=5)
        
        def confirm():
            sel = lb.curselection() 
            if not sel: return
            sensor = lb.get(sel[0]) 
            pid = entry_pid.get().strip() 
            if not pid: return            
            
            payload = json.dumps({
                "bed_name": bed_name, 
                "sensor_id": sensor, 
                "patient_id": pid,
                "controller_id": self.my_controller_id
            })
            self.log(f"發送綁定請求: 床位 {bed_name} <-> 設備 {sensor}")
            self.client.publish("olulu/system/req_bind", payload)
            
            dialog.destroy() 
            
        tk.Button(dialog, text="確認綁定", command=confirm, bg=self.theme["primary"], fg="white").pack(pady=20)

    def logout_current_bed(self):
        if not self.current_viewing_bed: return
        bed = self.beds[self.current_viewing_bed]
        
        if messagebox.askyesno("確認登出", f"確定要登出 {bed.name} 嗎？"):
            self.log(f"送出登出請求: 床位 {bed.name}")
            self.client.publish("olulu/system/unbind", bed.name)
            self.current_viewing_bed = None
            self.btn_toggle_time.pack_forget() 
            self.btn_logout.pack_forget()      
            self.update_chart_display()

    # ------------------ 繪圖用 (不變) ------------------
    def toggle_chart_style(self, event=None):
        self.chart_style = "bar" if self.chart_style == "line" else "line"
        self.update_chart_display() 
        
    def update_chart_display(self):
        t = self.theme
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        if w <= 1 or h <= 1:
            self.after(50, self.update_chart_display)
            return
            
        if not self.current_viewing_bed:
            self.info_label.config(text="OLuLu 重量監控系統")
            if self.img_startup: self.canvas.create_image(w/2, h/2, image=self.img_startup, anchor=tk.CENTER)
            else: self.canvas.create_text(w/2, h/2, text="點選床位按鈕以查看資料\n\n(找不到開機圖檔 copyright_1.jpg）", fill=t["text_light"], font=("Arial", 16), justify=tk.CENTER)
            return
        
        bed = self.beds[self.current_viewing_bed]
        info_text = f"床位: {bed.name}  |  病人: {bed.patient_id}  |  設備: {bed.sensor_id}"
        if bed.history:
            last_time_str = bed.history[-1][0][:16] 
            last_time = datetime.datetime.strptime(last_time_str, "%Y-%m-%d %H:%M")
            if (datetime.datetime.now() - last_time).total_seconds() > 60:
                bed.is_online = False
                self.refresh_all_buttons() 
            
        if bed.history: 
            current_weight = bed.history[-1][1]
            info_text += f"  |  目前: {current_weight} g"            
            weights_60m = [w for t, w in bed.history[-60:]]
            weight_change = round(self.calculate_weight_changes(weights_60m),0)              
            info_text += f"  |  60分變化: {weight_change} g"          

        self.info_label.config(text=info_text)

        if not bed.history:
            if self.img_standby: self.canvas.create_image(w/2, h/2, image=self.img_standby, anchor=tk.CENTER)
            else: self.canvas.create_text(w/2, h/2, text="載入資料中...\n\n(等待 Broker 傳送歷史數據)", fill=t["text_light"], font=("Arial", 16), justify=tk.CENTER)
            return

        padding = 40 
        bottom_y = h - padding
        view_len = self.view_minutes
        now = datetime.datetime.now()
        history_dict = {t[:16]: w for t, w in bed.history} 

        valid_weights = []
        for i in range(view_len):
            target_time = now - datetime.timedelta(minutes=(view_len - 1 - i))
            target_time_str = target_time.strftime("%Y-%m-%d %H:%M")
            if target_time_str in history_dict:
                valid_weights.append(history_dict[target_time_str])

        current_max_weight = max(valid_weights) if valid_weights else 0
        min_w = -100 
        if current_max_weight > 500:
            max_w = 1000
            current_line_color = t.get("chart_line_high", "#7BED9F") 
            current_fill_color = t.get("chart_fill_high", "#E2F9EB") 
        else:
            max_w = 500
            current_line_color = t.get("chart_line", "#FF9F43") 
            current_fill_color = t.get("chart_fill", "#FFE8D1")

        zero_y = bottom_y - ((0 - min_w) / (max_w - min_w)) * (h - 2*padding)
        self.canvas.create_line(padding, bottom_y, padding, padding, width=2, fill=t["text_dark"]) 
        self.canvas.create_line(padding, zero_y, w-padding, zero_y, width=2, fill=t["text_dark"])  
        
        ticks = [max_w, max_w // 2, 0, min_w]
        for tick in ticks:
            tick_y = bottom_y - ((tick - min_w) / (max_w - min_w)) * (h - 2*padding)
            font_weight = "bold" if tick == 0 else "normal"
            self.canvas.create_text(padding-10, tick_y, text=str(tick), anchor="e", fill=t["text_dark"], font=("Arial", 10, font_weight))
            if tick != 0: 
                self.canvas.create_line(padding, tick_y, w-padding, tick_y, fill=t["text_light"], dash=(4,4))

        if self.chart_style == "bar":
            step_x = (w - 2 * padding) / max(view_len, 1)
            bar_width = step_x * 0.8 if view_len <= 120 else step_x * 0.95
            for i in range(view_len):
                target_time = now - datetime.timedelta(minutes=(view_len - 1 - i))
                target_time_str = target_time.strftime("%Y-%m-%d %H:%M")            
                x = padding + (i + 0.5) * step_x
                if target_time_str in history_dict:
                    val = history_dict[target_time_str]
                    val_clamped = max(min_w, min(max_w, val)) 
                    y = bottom_y - ((val_clamped - min_w) / (max_w - min_w)) * (h - 2*padding)
                    self.canvas.create_line(x, y, x, zero_y, width=bar_width, fill=current_line_color)
        else:
            step_x = (w - 2*padding) / max((view_len - 1), 1)
            all_line_segments, all_poly_segments = [], []
            current_line_segment, current_poly_segment = [], []
            for i in range(view_len):
                target_time = now - datetime.timedelta(minutes=(view_len - 1 - i))
                target_time_str = target_time.strftime("%Y-%m-%d %H:%M")
                x = padding + i * step_x
                if target_time_str in history_dict:
                    val = history_dict[target_time_str]
                    val_clamped = max(min_w, min(max_w, val))
                    y = bottom_y - ((val_clamped - min_w) / (max_w - min_w)) * (h - 2*padding)
                    current_line_segment.extend([x, y])
                    current_poly_segment.extend([x, y])
                    if view_len <= 120 and current_max_weight <= 500:
                        self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=current_line_color, outline="")
                else:
                    if current_line_segment:
                        all_line_segments.append(current_line_segment)
                        all_poly_segments.append(current_poly_segment)
                        current_line_segment, current_poly_segment = [], []

            if current_line_segment:
                all_line_segments.append(current_line_segment)
                all_poly_segments.append(current_poly_segment)

            for i in range(len(all_line_segments)):
                line_pts = all_line_segments[i]
                poly_pts = all_poly_segments[i]
                if len(line_pts) >= 4:
                    full_poly = [poly_pts[0], zero_y] + poly_pts + [poly_pts[-2], zero_y]
                    self.canvas.create_polygon(full_poly, fill=current_fill_color, outline="")
                    self.canvas.create_line(line_pts, fill=current_line_color, width=2, capstyle=tk.ROUND, joinstyle=tk.ROUND)

  
    # ================== MQTT 與 背景通訊 ==================
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.gui_queue.put(("conn", True))
            self.log("成功連線至 MQTT Broker。")
            
            client.subscribe("device/+/status") 
            client.subscribe("device/+/weight")
            client.subscribe("olulu/system/state_update") 
            client.subscribe("olulu/system/res_history/#")
            client.subscribe(f"olulu/system/bind_success/{self.my_controller_id}")
            client.subscribe(f"olulu/system/bind_reject/{self.my_controller_id}")
            
            self.log("向 Broker 索取最新全區狀態設定...")
            client.publish("olulu/system/req_config", "all")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.gui_queue.put(("conn", False))
        self.log("⚠️ 與 MQTT Broker 斷開連線！")

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            if msg.topic.startswith("device/"):
                parts = msg.topic.split('/')
                self.gui_queue.put(("mqtt_device", parts[1], parts[2], payload))
            elif msg.topic.startswith("olulu/system/"):
                self.gui_queue.put(("mqtt_system", msg.topic, payload))
        except: pass

    def timer_process_queue(self):
        try:
            while True:
                task = self.gui_queue.get_nowait()
                kind = task[0]
                
                if kind == "log":
                    self.log_text.config(state=tk.NORMAL)
                    self.log_text.insert(tk.END, task[1] + "\n")
                    self.log_text.see(tk.END) 
                    self.log_text.config(state=tk.DISABLED)
                
                elif kind == "conn":
                    color = "#2ECC71" if task[1] else "red"
                    self.conn_canvas.itemconfig(self.conn_light, fill=color)
                
                elif kind == "mqtt_device":
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
                                target_bed.add_data(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), float(val))
                                target_bed.is_online = True
                                if self.current_viewing_bed == target_bed.name:
                                    self.update_chart_display()
                            except: pass
                    self.refresh_all_buttons()
                
                elif kind == "mqtt_system":
                    topic, payload = task[1], task[2]
                    
                    if topic == "olulu/system/state_update":
                        config_data = json.loads(payload)
                        for bed_name, bed_info in config_data.items():
                            if bed_name in self.beds:
                                self.beds[bed_name].sensor_id = bed_info.get("sensor_id")
                                self.beds[bed_name].patient_id = bed_info.get("patient_id")
                        self.refresh_all_buttons()
                        
                    elif topic.startswith("olulu/system/res_history/"):
                        bed_name = topic.split('/')[-1]
                        history_data = json.loads(payload) 
                        if bed_name in self.beds:
                            self.beds[bed_name].history = history_data
                            self.log(f"成功接收床位 {bed_name} 歷史資料，共 {len(history_data)} 筆。")
                            if self.current_viewing_bed == bed_name:
                                self.update_chart_display()
                                
                    elif topic.startswith(f"olulu/system/bind_reject/{self.my_controller_id}"):
                        self.log(f"⚠️ 綁定遭拒絕: {payload}")
                        messagebox.showwarning("綁定失敗", payload)
                        
                    elif topic.startswith(f"olulu/system/bind_success/{self.my_controller_id}"):
                        self.log("✅ Broker 核准綁定，等待全區狀態更新...")
                        
                self.gui_queue.task_done()
        except queue.Empty: pass
        finally: 
            self.after(100, self.timer_process_queue)

    def timer_alert_flash(self):
        t = self.theme
        for name, btn in self.bed_buttons.items():
            bed = self.beds[name]
            if bed.is_alert:
                curr_bg = btn.cget("bg")
                new_bg = t["alert"] if curr_bg == t["bg_card"] else t["bg_card"]
                fg_col = "white" if new_bg == t["alert"] else t["text_dark"]
                btn.config(bg=new_bg, fg=fg_col)
            elif not bed.is_alert and bed.sensor_id:
                btn.config(bg=t["bg_card"], fg=t["online"] if bed.is_online else t["offline"])
        self.after(500, self.timer_alert_flash)

    def refresh_all_buttons(self):
        t = self.theme
        for name, bed in self.beds.items():
            btn = self.bed_buttons[name]
            if bed.sensor_id:
                txt = f"● {name}\n{bed.patient_id}"
                if not bed.is_alert:
                    btn.config(text=txt, fg=t["online"] if bed.is_online else t["offline"], bg=t["bg_card"])
            else:
                btn.config(text=f"○ {name}\n(空床)", fg=t["text_light"], bg=t["bg_main"])

    def calculate_weight_changes(self, weight_FLUID):
        weight_sum = 0
        if len(weight_FLUID) > 9:
            weight_max = weight_FLUID[0] 
            weight_min = weight_FLUID[0]     
            weight_recent = weight_FLUID[-10:] 
            small_volume = max(weight_recent) - min(weight_recent) 
            for i, element in enumerate(weight_recent):
                if weight_recent[i] > weight_max: 
                    if weight_recent[i] > (weight_max + 1500): pass
                    else: weight_max = weight_recent[i] 
                if weight_recent[i] < weight_min / 2: 
                    weight_sum = weight_sum + weight_max - weight_min 
                    weight_max = weight_recent[i] 
                    weight_min = weight_recent[i] 
                weight_sum = weight_max - weight_min
                if small_volume < 10: weight_sum = small_volume
        return weight_sum

if __name__ == "__main__":
    app = OLuLuSystem()
    app.mainloop()
