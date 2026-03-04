print('     %%%%%  %%        %%             Online Urine levering Utility   ')
print('    %%   %% %% %% %%  %% %% %%    Copyright Jay Ming-chieh Yang 2025.')   
print('    %%   %% %% %% %%  %% %% %%            Photo credit: Olulu        ')
print('    %%   %% %% %% %%  %% %% %%         Theme color code is from      ') 
print('     %%%%%  %%  %%%%% %%  %%%%%       Yosun Blind Co. Ltd, 1985.     ')

# ------------------ 判斷作業系統並處理Mosquitto啟動 ------------------
import subprocess
import os
import sys
# 自動判斷作業系統
if os.name == 'nt':  # Windows  Win 7/8/10/11
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
    # 代表 Linux 或 Mac 系統
    print("目前為非 Windows 系統，如為類Unix系統可假設 Mosquitto 已由系統自動啟動。")


# ------------------ 主程式套件匯入 ------------------
print('     Kóo-tsui ê LuLu, khó-ài ê LuLu, OLuLu, OLuLu, OLuLu, OLuLu.     ')
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import paho.mqtt.client as mqtt
import json
import csv
import datetime
import time
import queue
import math
from PIL import Image, ImageTk
import ctypes

# ================= 系統參數設定 =================
BROKER_IP = "localhost"        # MQTT 伺服器 IP (本機)
BROKER_PORT = 1883             # MQTT 連接埠
CONFIG_FILE = "bed_config.json"# 儲存床位綁定狀態的設定檔
THEMES_FILE = "themes.csv"     # 儲存佈景主題配色的設定檔

# 預設 10 個床位名稱列表
DEFAULT_BED_LIST = [
    "3L01", "3L02", "3L03", "3L05", "3L06",
    "3L07", "3L08", "3L09", "3K17", "3K18"
]
print('        Kóo-tsui ê LuLu, khó-ài ê LuLu, LuLu LuLu LuLu, OLuLu.     ')
# ================= 資料格式設定 =================
class BedModel:
    """代表單一床位與其綁定感測器的資料結構"""
    def __init__(self, name):
        self.name = name           # 床位名稱 (如: 3L01)
        self.sensor_id = None      # 綁定的感測器 ID (如: LuLu01)
        self.patient_id = None     # 綁定的病歷號
                
        self.history = []    # 儲存之歷史數據，格式為 list of tuple: [("YYYY-MM-DD HH:MM", 500), ...]
        
        self.is_online = False     # 感測器目前的連線狀態
        self.is_alert = False      # 是否觸發重量異常警報

    def to_dict(self):
        """將床位資料轉為字典，用於存入 JSON 檔"""
        return {"sensor_id": self.sensor_id, "patient_id": self.patient_id}

    def from_dict(self, data):
        """從字典還原床位資料，用於讀取 JSON 檔"""
        self.sensor_id = data.get("sensor_id")
        self.patient_id = data.get("patient_id")

    def add_data(self, timestamp, weight):
        """將新收到的時間與重量加入歷史紀錄，並處理存檔與警報邏輯"""
        self.history.append((timestamp, weight))
        
        # 限制記憶體內只保留最近 480 筆 (8小時) 的資料，避免記憶體爆滿
        if len(self.history) > 480:
            self.history.pop(0)
            
        # 簡單的警報觸發邏輯：若最新一筆重量比上一筆驟降 100g，視為異常 (例如尿袋破裂或被倒空)
        if len(self.history) >= 2:
            diff = self.history[-1][1] - self.history[-2][1]
            if diff < -100: self.is_alert = True
            else: self.is_alert = False
        
        # 呼叫內部函式將資料寫入獨立的 CSV 檔
        self._save_to_csv(timestamp, weight)

    def _save_to_csv(self, timestamp, weight):
        """以病歷號為檔名，儲存歷史重量資料"""
        if not self.patient_id: return
        filename = f"{self.patient_id}.csv"
        try:
            file_exists = os.path.isfile(filename)
            with open(filename, "a", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                # 若檔案不存在，先寫入標題列
                if not file_exists:
                    writer.writerow(["Time", "Weight", "SensorID"])
                writer.writerow([timestamp, weight, self.sensor_id])
        except Exception as e:
            print(f"存檔失敗: {e}")

    def clear_assignment(self):
        """登出床位，清空所有綁定與歷史資料"""
        self.sensor_id = None  # 感測器 ID
        self.patient_id = None # 病歷號
        self.is_online = False # 感測器目前的連線狀態
        self.is_alert = False  # 是否觸發重量異常警報
        self.history = []
    def load_history_from_csv(self):
        """從硬碟讀取該病歷號過去的歷史資料 (支援多種編碼與絕對路徑)"""
        if not self.patient_id: return
        
        # 取得目前 python 程式所在的資料夾路徑
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, f"{self.patient_id}.csv")
        
        if not os.path.exists(filename):
            print(f"🔍 [讀取舊檔] 找不到檔案: {filename} (新病人從零開始)")
            return

        loaded_history = []
        
        # 以三種常見的編碼來開鎖 (因應 Excel 或舊系統存檔的問題)
        encodings_to_try = ['utf-8-sig', 'big5', 'utf-8']
        
        for enc in encodings_to_try:
            try:
                with open(filename, "r", encoding=enc) as f:
                    reader = csv.reader(f)
                    for row in reader:
                        # 確保這行有資料，且沒有被空白行干擾
                        if len(row) >= 2 and row[0].strip():
                            ts_str = row[0].strip()
                            if ts_str == "Time": continue # 跳過標題列
                            
                            try:
                                weight = float(row[1])
                                loaded_history.append((ts_str, weight))
                            except ValueError:
                                pass # 遇到無法轉換的資料就跳過
                
                print(f"🔓 [讀取舊檔] 成功使用 {enc} 編碼打開了 {self.patient_id}.csv！")
                break # 如成功解讀就跳出迴圈
                
            except UnicodeDecodeError:
                continue # 這個編碼失敗，換下一個
            except Exception as e:
                print(f"❌ [讀取舊檔] 發生未知錯誤: {e}")
                return
                
        # 結算並覆蓋記憶體
        if loaded_history:
            self.history = loaded_history[-480:]
            print(f"✅ [讀取舊檔] 病歷號 {self.patient_id} 共載入 {len(self.history)} 筆資料。")
            print(f"   (最新一筆紀錄時間為：{self.history[-1][0]})")
        else:
            print(f"⚠️ [讀取舊檔] {self.patient_id}.csv 裡面是空的，或沒有格式正確的數據。")


# =================  取得開機與待機圖片 =================
def get_resized_image(image_path, target_height):
    """
    輸入圖片路徑與目標高度，回傳 (PhotoImage物件, 計算出的寬度)
    """
    try:
        if not os.path.exists(image_path):
            print(f"錯誤：找不到圖片檔案 {image_path}")
            return None, 0

        with Image.open(image_path) as img:
            orig_w, orig_h = img.size
            
            # 計算縮放比例並推算寬度
            ratio = target_height / orig_h
            target_width = int(orig_w * ratio)
            
            # 高品質縮放演算法
            resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # 轉換為 Tkinter 可用的格式
            tk_img = ImageTk.PhotoImage(resized_img)
            
            return tk_img, target_width
            
    except Exception as e:
        print(f"處理圖片時發生錯誤: {e}")
        return None, 0
# ==================主程式，以下是主要介面==================   
class OLuLuSystem(tk.Tk):
    """OLuLu 系統的主視窗與邏輯控制器"""
    #以下是全螢幕修圓角版。如果有問題，就照搬viewer的
    def __init__(self):
        super().__init__()
        
        # 以下開始為圓角版
        #===============1. 拔除系統預設標題列 (開啟無邊框模式)======
        self.overrideredirect(True)
        self.configure(bg="#F5F7FA")

        # ================== 圓角版主要修改的部分 ==================
        import os
        if os.name == 'nt':
            import ctypes
            # 宣告 RECT 結構，用來接收 Windows 回傳的座標
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long),
                            ("top", ctypes.c_long),
                            ("right", ctypes.c_long),
                            ("bottom", ctypes.c_long)]
            rect = RECT()
            # 呼叫 SystemParametersInfoW (參數 48 代表獲取工作區域 SPI_GETWORKAREA)
            ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
            
            # 算出扣除工具列之後的真實寬高與起始位置
            window_width = rect.right - rect.left
            window_height = rect.bottom - rect.top
            start_x = rect.left
            start_y = rect.top
        else:
            # 非 Windows 系統的備用方案
            window_width = self.winfo_screenwidth()
            window_height = self.winfo_screenheight() - 40 # 粗估扣除 40px 工具列
            start_x = 0
            start_y = 0

        # 將視窗精準塞入工作區域
        self.geometry(f"{window_width}x{window_height}+{start_x}+{start_y}")
        # ==================圓角版================================

        # 2. 手工打造「自訂標題列」 (記得這段一定要最先 pack，才會在最上層)
        self.title_bar = tk.Frame(self, bg="#2F3542", relief="flat", bd=0)
        self.title_bar.pack(side=tk.TOP, fill=tk.X)
        
        # 綁定滑鼠拖曳事件
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        
        # 標題列文字
        self.title_label = tk.Label(self.title_bar, text=" OLuLu 遠端監控儀表板", bg="#2F3542", fg="white", font=("Arial", 12, "bold"))
        self.title_label.pack(side=tk.LEFT, pady=8, padx=10)
        self.title_label.bind("<ButtonPress-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)

        # 3. 手工打造「自訂關閉按鈕 (X)」
        self.close_btn = tk.Button(self.title_bar, text=" ✕ ", bg="#FF5252", fg="white", font=("Arial", 12, "bold"), 
                                   relief="flat", cursor="hand2", command=self.on_closing)
        self.close_btn.pack(side=tk.RIGHT, padx=5, pady=2)

        # 4. 【強烈建議】當視窗已經是最大化時，請不要切圓角！
        # 如果切了圓角，螢幕四個角落會露出後面的桌面底色，看起來像破圖。
        self.update_idletasks()
        self.apply_rounded_corners(window_width, window_height, 20) # 20 是圓角的弧度
               
        
        # 設定預設視窗大小，並嘗試在 Windows 上最大化
        #self.geometry("1366x700")
        # ============ 防休眠 （共通）============
        if os.name == 'nt':  # 只有 Windows 才能這樣做I
            import ctypes
            try:
                # 0x80000000 (持續生效) | 0x00000002 (螢幕開啟) | 0x00000001 (系統喚醒)
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
            except Exception as e:
                print("請注意：防主機休眠機制未能啟動:", e)
        else:
            print("Linux 系統請至「系統設定 -> 電源管理」中關閉休眠與螢幕保護。")
        # ===================（原生版）=========================
        #try:
        #    self.state("zoomed")
        #except: pass
        # ==================（以下共通）==========================
        # 載入主題與背景色
        self.load_themes()
        self.configure(bg=self.theme["bg_main"])
        
        # 載入開機與待機提示圖片
        self.load_images()
        
        # 初始化 10 個床位的資料模型
        self.beds = {name: BedModel(name) for name in DEFAULT_BED_LIST}
        
        # 記錄目前在線上的感測器 ID 集合 (Set)
        self.online_sensors = set()
        
        # 記錄使用者目前點選查看的床位名稱 (如: "3L01")
        self.current_viewing_bed = None
        
        # 記錄目前的圖表顯示模式 (預設為折線圖 "line")
        self.chart_style = "line"
        
        # 記錄圖表目前的顯示模式 (預設 60 分鐘)
        self.view_minutes = 60
        
        # 讀取先前的床位綁定設定檔
        self.load_config()

        # 用於 MQTT 背景執行緒與 Tkinter 主執行緒之間安全傳遞資料的佇列
        self.gui_queue = queue.Queue()
        
        # 建立所有使用者介面元件
        self.setup_ui()

        # 設定與連接 MQTT 客戶端
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2) # 使用 VERSION2
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message        
        try:
            # 使用connect_async (非同步連線)，即使 Broker 沒開，程式也會繼續執行
            self.client.connect_async(BROKER_IP, BROKER_PORT, 60)
            
            # 啟動背景執行緒，loop_start() +connect_async會在背景不斷嘗試連線，如果斷線也會自動重連
            self.client.loop_start() 
            print("MQTT 背景連線機制已啟動，將自動嘗試連線...")
            
        except Exception as e:
            print(f"MQTT 啟動連線機制時發生錯誤: {e}")

        # 啟動三個主要定時器常駐運作
        self.timer_sync_clock()      # 定期發送廣播指令
        self.timer_process_queue()   # 持續接收 MQTT 資料並更新 UI
        self.timer_alert_flash()     # 處理警報閃爍效果
        # 攔截右上角的 X 關閉視窗按鈕
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    #def on_closing(self): #原生版
    #    """關閉視窗前的確認對話框；這是原生視窗用的"""
    #    if messagebox.askyesno("確認離開", "確定要關閉 OLuLu 系統嗎？\n(背景的連線與監控將會停止)"):
    #        self.destroy() # 使用者按「是」，關閉程式

    # ================= 視窗外觀與操作邏輯 （圓角版）=================
    def start_move(self, event):
        """記錄滑鼠點下時的座標"""
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        """計算滑鼠移動距離，並跟著移動視窗"""
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def apply_rounded_corners(self, w, h, radius):
        """呼叫 Windows 底層 API 切出完美的無黑邊圓角"""
        import os
        if os.name == 'nt':  # 確保只有在 Windows 執行
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w, h, radius, radius)
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)

    def on_closing(self):
        """自訂 X 按鈕的防呆確認框"""
        if messagebox.askyesno("確認離開", "確定要關閉 OLuLu 系統嗎？\n(背景的連線與監控將會停止)"):
            self.destroy()
            

    # ------------------ 圖片資源（共通） ------------------
    def load_images(self): #取得圖片通通在這邊
        # 取得基本路徑（與本程式在同一資料夾）
        if getattr(sys, 'frozen', False):
            BASE_DIR = os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        # 取得螢幕高度
        screen_h = self.winfo_screenheight()
        # --- 開機圖 (佔螢幕 50%) ---
        path_startup = os.path.join(BASE_DIR, "copyright_1.jpg")
        target_h_startup = int(screen_h * 0.50)
        self.img_startup, self.startup_w = get_resized_image(path_startup, target_h_startup)
        self.startup_h = target_h_startup
        # --- 待機圖 (佔螢幕 50%) ---
        path_standby = os.path.join(BASE_DIR, "copyright_2.jpg")
        target_h_standby = int(screen_h * 0.50) 
        # 呼叫工具函式計算 copyright_2 的寬度
        self.img_standby, self.standby_w = get_resized_image(path_standby, target_h_standby)
        self.standby_h = target_h_standby


    def show_splash(self): #產生獨立小視窗秀圖
        splash = tk.Toplevel()
        splash.overrideredirect(True) # 去掉邊框
        
        # 取得螢幕解析度
        sw = splash.winfo_screenwidth()
        sh = splash.winfo_screenheight()
        
        # 使用工具函式算出的尺寸來計算置中位置
        x = (sw // 2) - (self.startup_w // 2)
        y = (sh // 2) - (self.startup_h // 2)
        
        # 設定視窗幾何
        splash.geometry(f"{self.startup_w}x{self.startup_h}+{x}+{y}")
        
        # 顯示圖片
        label = tk.Label(splash, image=self.img_startup, borderwidth=0)
        label.pack()

    # ------------------ 畫面主題 ------------------
    def load_themes(self):
        # 定義顏色
        keys = ["thene_name", "bg_main", "bg_card", "primary", "alert", "text_dark", "text_light", "online", "offline", 
                "chart_line", "chart_fill", "chart_line_high", "chart_fill_high"] # high為>500時要用的顏色
                
        default_themes = [
            ["default_day","#F5F7FA", "#FFFFFF", "#20B2AA", "#FF5252", "#2F3542", "#A4B0BE", "#2ECC71", "#BDC3C7", "#FF9F43", "#FFE8D1", "#7BED9F", "#E2F9EB"],
             
            ["default_night","#1E1E1E", "#2D2D2D", "#007ACC", "#E51400", "#FFFFFF", "#AAAAAA", "#00FF00", "#555555", "#00FFAA", "#004433", "#2ED573", "#1B5E20"] #深色主題，最後為螢光綠與深墨綠
        ]
        
        self.themes = []
        if not os.path.exists(THEMES_FILE):
            try:
                with open(THEMES_FILE, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(keys)
                    writer.writerows(default_themes)
            except: pass

        try:
            with open(THEMES_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader: self.themes.append(row)
        except: pass

        if not self.themes: self.themes = [dict(zip(keys, default_themes[0]))]
        self.current_theme_idx = 0                       # 目前使用的主題索引
        self.theme = self.themes[self.current_theme_idx] # 將當前主題存入 self.theme 字典中

    def cycle_theme(self, event=None):
        """循環切換佈景主題 (由點擊畫布觸發)"""
        self.current_theme_idx = (self.current_theme_idx + 1) % len(self.themes)
        self.theme = self.themes[self.current_theme_idx]
        self.apply_theme()

    def apply_theme(self):
        """將當前選定的 self.theme 字典顏色套用到所有介面元件上"""
        t = self.theme
        self.configure(bg=t["bg_main"])
        self.bg_canvas.config(bg=t["bg_main"])
        self.main_container.config(bg=t["bg_main"])
        
        self.left_card.config(bg=t["bg_card"])
        self.info_frame.config(bg=t["bg_card"])
        self.info_label.config(bg=t["bg_card"], fg=t["text_dark"])
        self.conn_canvas.config(bg=t["bg_card"])
        self.canvas.config(bg=t["bg_card"])
        self.bottom_frame.config(bg=t["bg_card"])
        
        self.right_card.config(bg=t["bg_card"])
        self.btn_logout.config(bg=t["bg_main"], fg=t["text_dark"])
        self.btn_toggle_time.config(bg=t["bg_main"], fg=t["text_dark"])
        
        # 更新背景角落遮罩的顏色 (營造復古圓角邊框感)
        corner_color = t["text_dark"] 
        self.bg_canvas.itemconfig(self.corner_tl, fill=corner_color)
        self.bg_canvas.itemconfig(self.corner_tr, fill=corner_color)
        self.bg_canvas.itemconfig(self.corner_bl, fill=corner_color)
        self.bg_canvas.itemconfig(self.corner_br, fill=corner_color)

        self.refresh_all_buttons()
        self.update_chart_display()

    # ------------------ 介面佈局設計（共通） ------------------
    def setup_ui(self):
        """初始化並排版所有的 UI 元件"""
        t = self.theme
        
        # [底層] 用來繪製復古圓角的畫布
        self.bg_canvas = tk.Canvas(self, bg=t["bg_main"], highlightthickness=0)
        self.bg_canvas.place(x=0, y=40, relwidth=1, relheight=1)
        #self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        corner_color = t["text_dark"] 
        # 建立四個多邊形，用來當作角落遮罩 (初始坐標全為 0)
        self.corner_tl = self.bg_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=corner_color, outline="")
        self.corner_tr = self.bg_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=corner_color, outline="")
        self.corner_bl = self.bg_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=corner_color, outline="")
        self.corner_br = self.bg_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=corner_color, outline="")
        
        # 當背景畫布大小改變時，呼叫 update_corners_position 重新計算遮罩位置
        self.bg_canvas.bind("<Configure>", self.update_corners_position)

        # [主內容區] 加入 padx, pady 讓出空間給底層圓角
        self.main_container = tk.Frame(self, bg=t["bg_main"])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)

        # [左側] 資料卡片區
        self.left_card = tk.Frame(self.main_container, bg=t["bg_card"], relief="flat")
        self.left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        # 資訊標籤列，固定在最上方
        self.info_frame = tk.Frame(self.left_card, bg=t["bg_card"])
        self.info_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.info_label = tk.Label(self.info_frame, text="系統啟動中...", font=("Microsoft JhengHei UI", 16, "bold"), 
                                   bg=t["bg_card"], fg=t["text_dark"])
        self.info_label.pack(side=tk.LEFT, padx=5)

        self.conn_canvas = tk.Canvas(self.info_frame, width=20, height=20, bg=t["bg_card"], highlightthickness=0)
        self.conn_canvas.pack(side=tk.RIGHT, padx=10)
        self.conn_light = self.conn_canvas.create_oval(2, 2, 18, 18, fill="red", outline="gray")

        # 底部按鈕區，固定在最下方，高度為 40px；先不 pack 按鈕以維持淨空
        self.bottom_frame = tk.Frame(self.left_card, bg=t["bg_card"], height=40)
        self.bottom_frame.pack_propagate(False) # 強制鎖定高度，不隨內容縮放
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 10))
        
        self.btn_toggle_time = tk.Button(self.bottom_frame, text="切換: 目前顯示 60 分鐘", 
                                         bg=t["bg_main"], fg=t["text_dark"],
                                         command=self.toggle_time_view, font=("Arial", 12))
        self.btn_logout = tk.Button(self.bottom_frame, text="登出此床位", 
                                    bg=t["bg_main"], fg=t["text_dark"],
                                    command=self.logout_current_bed, font=("Arial", 12))
        # 主畫布，最後 Pack以填滿上方與下方剩下的所有空間)
        self.canvas = tk.Canvas(self.left_card, bg=t["bg_card"], highlightthickness=0, cursor="hand2")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        self.canvas.bind("<Button-1>", self.cycle_theme)

        # [右側] 床位列表卡片
        self.right_card = tk.Frame(self.main_container, bg=t["bg_card"], width=280)
        self.right_card.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_card.pack_propagate(False) # 鎖定寬度不隨內容縮放

        # 動態建立床位按鈕
        self.bed_buttons = {}
        for name in DEFAULT_BED_LIST:
            btn = tk.Button(self.right_card, text=name, font=("Microsoft JhengHei UI", 12, "bold"),
                            bg=t["bg_card"], relief="raised",
                            command=lambda n=name: self.on_bed_click(n))
            btn.pack(fill=tk.X, padx=5, pady=2)
            self.bed_buttons[name] = btn

        # 在右側底部加入淡色提示字，並將背景與提示字都綁定點擊事件
        self.lbl_chart_hint = tk.Label(self.right_card, text="(點擊空白處切換圖表)", bg=t["bg_card"], fg=t["text_light"], font=("Arial", 9))
        self.lbl_chart_hint.pack(side=tk.BOTTOM, pady=10)        
        # 綁定左鍵點擊事件 (<Button-1>) 到右側卡片與提示字上
        self.right_card.bind("<Button-1>", self.toggle_chart_style)
        self.lbl_chart_hint.bind("<Button-1>", self.toggle_chart_style)

        self.refresh_all_buttons()
        self.update_chart_display()

    # ------------------ 周邊畫圓 ------------------
    def update_corners_position(self, event):
        """利用三角函數動態計算出四個角落的反向遮罩座標"""
        w, h = self.bg_canvas.winfo_width(), self.bg_canvas.winfo_height()
        r = 25     # 圓角半徑
        steps = 10 # 弧線平滑度
        
        # 計算左上角
        tl_pts = [0, 0, r, 0]
        for i in range(steps + 1):
            ang = math.radians(90 + (90 * i / steps))
            tl_pts.extend([r + r * math.cos(ang), r - r * math.sin(ang)])
        tl_pts.extend([0, r])
        self.bg_canvas.coords(self.corner_tl, *tl_pts)
        
        # 計算右上角
        tr_pts = [w, 0, w, r]
        for i in range(steps + 1):
            ang = math.radians(0 + (90 * i / steps))
            tr_pts.extend([w - r + r * math.cos(ang), r - r * math.sin(ang)])
        tr_pts.extend([w - r, 0])
        self.bg_canvas.coords(self.corner_tr, *tr_pts)
        
        # 計算右下角
        br_pts = [w, h, w - r, h]
        for i in range(steps + 1):
            ang = math.radians(270 + (90 * i / steps))
            br_pts.extend([w - r + r * math.cos(ang), h - r - r * math.sin(ang)])
        br_pts.extend([w, h - r])
        self.bg_canvas.coords(self.corner_br, *br_pts)
        
        # 計算左下角
        bl_pts = [0, h, 0, h - r]
        for i in range(steps + 1):
            ang = math.radians(180 + (90 * i / steps))
            bl_pts.extend([r + r * math.cos(ang), h - r - r * math.sin(ang)])
        bl_pts.extend([r, h])
        self.bg_canvas.coords(self.corner_bl, *bl_pts)

    # ------------------ 介面互動 ------------------
    def toggle_time_view(self):
        """切換 60 分鐘 / 480 分鐘顯示模式"""
        self.view_minutes = 480 if self.view_minutes == 60 else 60
        self.btn_toggle_time.config(text=f"切換: 目前顯示 {self.view_minutes} 分鐘")
        self.update_chart_display()
#=============================(以下BROKER專用）===============================
    def on_bed_click(self, bed_name):
        """處理右側床位按鈕的點擊事件"""
        self.current_viewing_bed = bed_name
        bed = self.beds[bed_name]

        if bed.sensor_id is None:
            self.show_login_dialog(bed_name) # 若未綁定，彈出登錄視窗
        else:
            # 顯示底部功能按鈕
            self.btn_toggle_time.pack(side=tk.LEFT, padx=10)
            self.btn_logout.pack(side=tk.RIGHT, padx=10)
            self.update_chart_display()
#=============================(以上BROKER專用）===============================
    def show_login_dialog(self, bed_name):
        """彈出登錄病歷與選擇感測器的對話框"""
        # 篩選出目前在線上，且尚未被其他床位綁定的感測器 ID
        assigned_ids = [b.sensor_id for b in self.beds.values() if b.sensor_id]
        available = [sid for sid in self.online_sensors if sid not in assigned_ids]
        
        if not available:
            messagebox.showwarning("無可用設備", "目前沒有閒置的設備在線上。")
            return

        dialog = tk.Toplevel(self) 
        dialog.title(f"登錄床位 {bed_name}")
        dialog.geometry("300x400")
        
        # 建立感測器列表
        tk.Label(dialog, text="1. 選擇感測器", font=("bold")).pack(pady=5)
        lb = tk.Listbox(dialog)
        for sensor in sorted(available): lb.insert(tk.END, sensor)
        lb.pack(pady=5)
        
        # 建立病歷號輸入框
        tk.Label(dialog, text="2. 輸入病歷號", font=("bold")).pack(pady=5)
        entry_pid = tk.Entry(dialog) 
        entry_pid.pack(pady=5)
        
        def confirm():
            """按下確認綁定後的處理邏輯"""
            sel = lb.curselection() 
            if not sel: return
            sensor = lb.get(sel[0]) # 取得選中的感測器 ID
            pid = entry_pid.get().strip() # 取得並清理病歷號
            if not pid: return
            
            # 寫入資料用的
            self.beds[bed_name].sensor_id = sensor
            self.beds[bed_name].patient_id = pid
            self.beds[bed_name].is_online = True
            
            # 綁定病歷號後，抓出已經存檔的資料
            self.beds[bed_name].load_history_from_csv()
            
            self.save_config() # 存檔
            self.refresh_all_buttons()
            self.on_bed_click(bed_name) # 切換為顯示該床位畫面
            dialog.destroy() # 關閉對話框
            
        tk.Button(dialog, text="確認綁定", command=confirm, bg=self.theme["primary"], fg="white").pack(pady=20)

    def logout_current_bed(self):
        """處理登出床位的邏輯"""
        if not self.current_viewing_bed: return
        bed = self.beds[self.current_viewing_bed]
        
        if messagebox.askyesno("確認登出", f"確定要登出 {bed.name} 嗎？"):
            bed.clear_assignment()
            self.save_config()
            self.refresh_all_buttons()
            self.current_viewing_bed = None
            self.btn_toggle_time.pack_forget() # 隱藏按鈕
            self.btn_logout.pack_forget()      # 隱藏按鈕
            self.update_chart_display()

    # ------------------ 繪圖用  ------------------
    def toggle_chart_style(self, event=None):
        """切換折線圖與長條圖模式 (由點擊右側空白處觸發)"""
        self.chart_style = "bar" if self.chart_style == "line" else "line"
        self.update_chart_display() # 觸發重新繪圖
        
    def update_chart_display(self):
        """核心繪圖函式：負責更新上方文字資訊與繪製圖表"""
        t = self.theme
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        # 避免視窗尚未渲染完成時尺寸為 1，導致運算錯誤
        if w <= 1 or h <= 1:
            self.after(50, self.update_chart_display)
            return
            
        # 情況1：未選定任何床位，則顯示開機圖片
        if not self.current_viewing_bed:
            self.info_label.config(text="OLuLu 重量監控系統")
            if self.img_startup:
                self.canvas.create_image(w/2, h/2, image=self.img_startup, anchor=tk.CENTER)
            else:
                self.canvas.create_text(w/2, h/2, text="點選床位按鈕以查看資料\n\n(找不到開機圖檔 copyright_1.jpg）", fill=t["text_light"], font=("Arial", 16), justify=tk.CENTER)
            return
        
        #已有登錄
        # ---------------- 上方文字資訊列 ----------------
        bed = self.beds[self.current_viewing_bed]
        info_text = f"床位: {bed.name}  |  病人: {bed.patient_id}  |  設備: {bed.sensor_id}"
        # --- 逾時檢測 ---
        if bed.history:
            last_time_str = bed.history[-1][0]
            last_time = datetime.datetime.strptime(last_time_str, "%Y-%m-%d %H:%M")
            # 如果最後一筆資料距離現在超過 1 分鐘，標記為離線
            if (datetime.datetime.now() - last_time).total_seconds() > 60:
                bed.is_online = False
                self.refresh_all_buttons() # 讓右側按鈕變灰/變紅
            
        if bed.history: 
            # 1. 取得最新一筆重量
            current_weight = bed.history[-1][1]
            info_text += f"  |  目前: {current_weight} g"            
            
            # 2. 擷取過去最多 60 筆的純重量資料 (濾除時間)，組成串列
            weights_60m = [w for t, w in bed.history[-60:]]
            
            # 3. 呼叫數學分析函式計算重量變化
            weight_change = round(self.calculate_weight_changes(weights_60m),0)             
            
            # 4. 將計算結果附加到顯示字串中
            info_text += f"  |  60分變化: {weight_change} g"          

        self.info_label.config(text=info_text)

        # 情況2：已選床位但無歷史資料，則顯示待機圖片
        if not bed.history:
            if self.img_standby:
                self.canvas.create_image(w/2, h/2, image=self.img_standby, anchor=tk.CENTER)
            else:
                self.canvas.create_text(w/2, h/2, text="尚無數據傳入...\n\n(找不到待機圖檔 copyright_2.jpg)", fill=t["text_light"], font=("Arial", 16), justify=tk.CENTER)
            return

        # ================= 1. 基本變數與邊距設定 =================
        padding = 40  # 畫布邊緣留白距離 (重要：必須先定義，以免後續運算出錯)
        bottom_y = h - padding
        
        view_len = self.view_minutes
        now = datetime.datetime.now()
        
        # 建立時間對應重量的字典，方便後續用 O(1) 時間比對特定時間點是否有資料
        history_dict = {t: w for t, w in bed.history}

        # ================= 2. 依照「有效重量」，決定 Y 軸極值 =================
        valid_weights = []
        for i in range(view_len):
            # 時間格式必須與寫入資料時的 "%Y-%m-%d %H:%M" 一模一樣
            target_time = now - datetime.timedelta(minutes=(view_len - 1 - i))
            target_time_str = target_time.strftime("%Y-%m-%d %H:%M")
            if target_time_str in history_dict:
                valid_weights.append(history_dict[target_time_str])

        # 找出目前的資料最大值
        current_max_weight = max(valid_weights) if valid_weights else 0
        min_w = -100 # Y 軸底線固定為 -100
        # 判斷 Y 軸上限與對應的顏色
        if current_max_weight > 500:
            max_w = 1000
            # 從字典取得高量顏色 ；若字典沒讀到，使用預設的色
            current_line_color = t.get("chart_line_high", "#7BED9F") # 嫩綠色 (低明度，表示高量)
            current_fill_color = t.get("chart_fill_high", "#E2F9EB") # 淺嫩綠
        else:
            max_w = 500
            # 從字典取得一般量顏色
            current_line_color = t.get("chart_line", "#FF9F43") # 橘色 (高明度)
            current_fill_color = t.get("chart_fill", "#FFE8D1")# 淺橘色

        # ================= 3. 畫 X, Y 軸與刻度 =================
        # 計算數值為 0 的 Y 座標位置
        zero_y = bottom_y - ((0 - min_w) / (max_w - min_w)) * (h - 2*padding)
        
        self.canvas.create_line(padding, bottom_y, padding, padding, width=2, fill=t["text_dark"]) # 畫 Y 軸
        self.canvas.create_line(padding, zero_y, w-padding, zero_y, width=2, fill=t["text_dark"])  # 畫 X 軸 (定位於 0)
        
        # 繪製刻度數值與輔助虛線
        ticks = [max_w, max_w // 2, 0, min_w]
        for tick in ticks:
            tick_y = bottom_y - ((tick - min_w) / (max_w - min_w)) * (h - 2*padding)
            font_weight = "bold" if tick == 0 else "normal"
            self.canvas.create_text(padding-10, tick_y, text=str(tick), anchor="e", fill=t["text_dark"], font=("Arial", 10, font_weight))
            if tick != 0: # 0 的位置已經畫了實心 X 軸，故跳過不畫虛線
                self.canvas.create_line(padding, tick_y, w-padding, tick_y, fill=t["text_light"], dash=(4,4))


        # ================= 4. 繪製圖表 (長條圖/ 折線圖) =================
        if self.chart_style == "bar":
            # ---------------- 【模式 A：長條圖】 ----------------
            # 將可用寬度均分為 view_len 個「隱形格子」(注意：這裡移除了原本的 - 1)
            step_x = (w - 2 * padding) / max(view_len, 1)
            # 決定長條圖的寬度：
            bar_width = step_x * 0.8 if view_len <= 120 else step_x * 0.95
            # 以絕對時間 (now 回推) 為 X 軸基準掃描
            for i in range(view_len):
                target_time = now - datetime.timedelta(minutes=(view_len - 1 - i))
                target_time_str = target_time.strftime("%Y-%m-%d %H:%M")            
                # 中心點向右平移半個 step_x (i + 0.5)以讓最左側側邊緣貼在 Y 軸右側避免重疊
                x = padding + (i + 0.5) * step_x
                # 若該時間點有資料，才繪製該根長條 (休眠或斷線時直接留空)
                if target_time_str in history_dict:
                    val = history_dict[target_time_str]
                    val_clamped = max(min_w, min(max_w, val)) # 限制數值不超出圖表上下界
                    # 計算此數值的 Y 座標 (長條圖頂部)並畫線
                    y = bottom_y - ((val_clamped - min_w) / (max_w - min_w)) * (h - 2*padding)
                    self.canvas.create_line(x, y, x, zero_y, width=bar_width, fill=current_line_color)
            
        else:
            # ---------------- 【模式 B：折線圖與面積圖】 ----------------
            step_x = (w - 2*padding) / max((view_len - 1), 1)
            
            all_line_segments = []
            all_poly_segments = []
            current_line_segment = []
            current_poly_segment = []
            
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
                    
                    # 一般量，加畫圓點
                    if view_len <= 120 and current_max_weight <= 500:
                        self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=current_line_color, outline="")
                else:
                    if current_line_segment:
                        all_line_segments.append(current_line_segment)
                        all_poly_segments.append(current_poly_segment)
                        current_line_segment = []
                        current_poly_segment = []

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

  
    # ------------------ MQTT & 定時器背景邏輯 ------------------
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """當 MQTT 連線成功時觸發 (VERSION2 格式)"""
        if reason_code == 0:
            self.gui_queue.put(("conn", True))
            client.subscribe("device/+/status") # 訂閱所有感測器的狀態
            client.subscribe("device/+/weight") # 訂閱所有感測器的重量

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        # 發送一個 "conn False" 的訊息給 GUI 佇列
        self.gui_queue.put(("conn", False))
        print(f"斷開連線，原因碼: {reason_code}")
#這個是092版以前用的，暫時留著免得新版出包
#    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
#        print(f"斷開連線，錯誤代碼: {reason_code}，嘗試重新連線...")
#        try:
#            self.client.reconnect()
#        except Exception as e:
#            print(f"重連失敗: {e}")

    def on_message(self, client, userdata, msg):
        """當收到 MQTT 訊息時觸發，將資料塞入佇列交由主執行緒處理"""
        try:
            parts = msg.topic.split('/')
            self.gui_queue.put(("mqtt", parts[1], parts[2], msg.payload.decode()))
        except: pass

    def timer_sync_clock(self):
        """定時器：每秒檢查，於每分鐘 05 秒時下令秤重，25秒繪圖，並檢測逾時連線"""
        now = datetime.datetime.now()
        sec = now.second
        # --- 05秒：向 Arduino 發出指令 ---
        if sec == 5:
            self.client.publish("olulu/all/trigger", "1")
            print(f"[{now.strftime('%H:%M:%S')}] 全體秤重指令")
        # --- 25秒：更新繪圖區 (Update UI) ---
        if sec == 25:
            if self.current_viewing_bed:
                self.update_chart_display()
            # 順便刷新右側所有按鈕的在線狀態
            self.check_device_timeout()
            self.refresh_all_buttons()
        #每秒鐘執行計時函數一次
        self.after(1000, self.timer_sync_clock)
        
    def check_device_timeout(self):
        """檢查所有床位，如果超過 1 分鐘沒資料，標記為離線"""
        now = datetime.datetime.now()
        for bed in self.beds.values():
            if bed.history:
                last_time_str = bed.history[-1][0]
                try:
                    last_time = datetime.datetime.strptime(last_time_str, "%Y-%m-%d %H:%M")
                    if (now - last_time).total_seconds() > 60: # 60秒 = 1分鐘
                        bed.is_online = False
                except:
                    pass

    def timer_process_queue(self):
        """定時器：負責從佇列取出 MQTT 資料並更新 Model 與 View (確保執行緒安全)"""
        try:
            while True:
                task = self.gui_queue.get_nowait()
                kind = task[0] # 接受到的資料種類
                
                if kind == "conn":
                    # 更新系統總連線狀態燈
                    color = "#2ECC71" if task[1] else "red"
                    self.conn_canvas.itemconfig(self.conn_light, fill=color)
                
                elif kind == "mqtt":
                    sensor_id, mtype, val = task[1], task[2], task[3]
                    
                    if mtype == "status":
                        # 處理感測器上線/離線狀態
                        if val == "online": self.online_sensors.add(sensor_id)
                        else:
                            self.online_sensors.discard(sensor_id)
                            # 同步標記綁定的床位為離線
                            for bed in self.beds.values():
                                if bed.sensor_id == sensor_id: bed.is_online = False
                    
                    elif mtype == "weight":
                        self.online_sensors.add(sensor_id) # 有傳資料代表在線上
                        
                        # 尋找是哪一張床位綁定了這個感測器
                        target_bed = next((b for b in self.beds.values() if b.sensor_id == sensor_id), None)
                        if target_bed:
                            try:
                                # 寫入資料模型 (標記精確的日期時間)
                                target_bed.add_data(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), float(val))
                                target_bed.is_online = True
                                
                                # 若更新的剛好是目前正在查看的床位，則觸發圖表刷新
                                if self.current_viewing_bed == target_bed.name:
                                    self.update_chart_display()
                            except: pass
                            
                    self.refresh_all_buttons() # 刷新右側所有按鈕狀態
                self.gui_queue.task_done()
        except queue.Empty: pass
        finally: self.after(100, self.timer_process_queue)

    def timer_alert_flash(self):
        """定時器：處理警報狀態的床位按鈕閃爍效果 (每 0.5 秒切換一次顏色)"""
        t = self.theme
        for name, btn in self.bed_buttons.items():
            bed = self.beds[name]
            if bed.is_alert:
                curr_bg = btn.cget("bg")
                new_bg = t["alert"] if curr_bg == t["bg_card"] else t["bg_card"]
                fg_col = "white" if new_bg == t["alert"] else t["text_dark"]
                btn.config(bg=new_bg, fg=fg_col)
            elif not bed.is_alert and bed.sensor_id:
                # 恢復正常顏色狀態
                btn.config(bg=t["bg_card"], fg=t["online"] if bed.is_online else t["offline"])
        self.after(500, self.timer_alert_flash)

    def refresh_all_buttons(self):
        """重新繪製右側床位清單的所有按鈕文字與顏色"""
        t = self.theme
        for name, bed in self.beds.items():
            btn = self.bed_buttons[name]
            if bed.sensor_id:
                txt = f"● {name}\n{bed.patient_id}"
                if not bed.is_alert:
                    btn.config(text=txt, fg=t["online"] if bed.is_online else t["offline"], bg=t["bg_card"])
            else:
                btn.config(text=f"○ {name}\n(空床)", fg=t["text_light"], bg=t["bg_main"])

    # ------------------ 設定檔讀寫（BROKER) ------------------
    def save_config(self):
        
        """將目前的床位綁定狀態存入 JSON 檔"""
        try:
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump({n: b.to_dict() for n, b in self.beds.items()}, f, indent=4)
        except: pass

    def load_config(self):
        """從 JSON 檔還原床位綁定狀態，並同時載入歷史資料"""
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                for name, d in json.load(f).items():
                    if name in self.beds: 
                        self.beds[name].from_dict(d)
                        # 還原病歷號綁定狀態並去硬碟把舊資料挖出來
                        if self.beds[name].patient_id:
                            self.beds[name].load_history_from_csv()
        except: pass

    # ================= 數據分析演算法 =================
    def calculate_weight_changes(self, weight_FLUID):
        """
        舊版搬移過來的分析邏輯：偵測重量突減與異常大量。
        傳入的 weight_FLUID 是一個純數值的 List。
        """
        weight_sum = 0
        if len(weight_FLUID) > 9:
            weight_max = weight_FLUID[0] # 先將最大值設成起始值
            weight_min = weight_FLUID[0] # 先將最小值設成起始值    
            weight_recent = weight_FLUID[-10:] # 取最近 10 筆資料做工作用串列
            
            # 改用原生 max 與 min，，就可以不用 numpy。REGRESSION也可自己寫
            small_volume = max(weight_recent) - min(weight_recent) 
            
            for i, element in enumerate(weight_recent):
                if weight_recent[i] > weight_max: # 逐步比較找最大值
                    if weight_recent[i] > (weight_max + 1500): 
                        # 一分鐘差1500克，視為異常可能不計入
                        pass
                    else:
                        weight_max = weight_recent[i] 

                # 發現突然減少（例如尿袋被清空）
                if weight_recent[i] < weight_min / 2: 
                    weight_sum = weight_sum + weight_max - weight_min 
                    weight_max = weight_recent[i] # 重設極值起點
                    weight_min = weight_recent[i] # 重設極值起點
                    print("可能有突減大量:" + str(weight_sum))
                                                    
                weight_sum = weight_max - weight_min
                
                # 尿量波動很小的範圍時，直接用最大減最小估計
                if small_volume < 10:
                    weight_sum = small_volume
                    
            print("小計:" + str(weight_sum))
            
        return weight_sum

# ------------------ 程式進入點 ------------------
if __name__ == "__main__":
    print('  LuLu LuLu, LuLu LuLu LuLu, LuLu LuLu LuLu OLuLu.     ')
    app = OLuLuSystem()
    app.mainloop()
