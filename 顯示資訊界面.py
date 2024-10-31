import tkinter as tk
from tkinter import ttk

# 字典，存入序號和IP地址
data = {
    1: {"Bed":"3L01", "IP": "192.168.1.201", "Info": "Device 1 Information"},
    2: {"Bed":"3L02", "IP": "192.168.1.202", "Info": "Device 2 Information"},
    3: {"Bed":"3L03", "IP": "192.168.1.203", "Info": "Device 3 Information"},
    5: {"Bed":"3L05", "IP": "192.168.1.205", "Info": "Device 5 Information"},
    6: {"Bed":"3L06", "IP": "192.168.1.206", "Info": "Device 6 Information"},
    7: {"Bed":"3L07", "IP": "192.168.1.207", "Info": "Device 7 Information"},
    8: {"Bed":"3L08", "IP": "192.168.1.208", "Info": "Device 8 Information"},
    9: {"Bed":"3L09", "IP": "192.168.1.209", "Info": "Device 9 Information"},
    17: {"Bed":"3K17", "IP": "192.168.1.217", "Info": "Device 17 Information"},
    18: {"Bed":"3K18", "IP": "192.168.1.218", "Info": "Device 18 Information"},
}

# 建立主畫面
root = tk.Tk()
root.title("IP Button GUI")
root.geometry("1024x768")


# 左半畫面，顯示內容
left_frame = tk.Frame(root, width=768, height=768, bg="white")
left_frame.pack(side="left", fill="both", expand=1)

# 顯示選中內容的Label
info_label = tk.Label(left_frame, text="Click a button to see details", bg="white", font=("Arial", 14))
info_label.pack(pady=50)

# 右半畫面，建立九個按鈕
right_frame = tk.Frame(root, width=256, height=768)
right_frame.pack(side="right", fill="both", expand=0)

# 建立顯示字典內容的函數
def display_info(button_number):
    bed= data[button_number]["Bed"]
    ip = data[button_number]["IP"]
    info = data[button_number]["Info"]
    info_label.config(text=f"Button {button_number}\nBed:{bed}\nIP: {ip}\nInfo: {info}")

# 建立1x9的按鈕矩陣
for i in data:
    btn = ttk.Button(right_frame, text=f"{data[i]['Bed']}\n{data[i]['IP']}", command=lambda num=i: display_info(num))
    btn.grid(row=i-1, column=0, pady=10)  # 使用i-1作為行索引，按鈕從第一行開始

# 啟動GUI主迴圈
root.mainloop()
