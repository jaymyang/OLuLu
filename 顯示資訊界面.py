import tkinter as tk
from tkinter import ttk

# 字典，存入序號和病歷號；IP地址先留著但因為主程式採浮動IP而以客戶端的ID識別，應會拿掉；Info顯示病歷號
data = {
    1: {"Bed":"Bed01", "IP": "192.168.1.201", "Info": "請輸入病歷號", client_ID='LuLu01'},
    2: {"Bed":"Bed02", "IP": "192.168.1.202", "Info": "請輸入病歷號", client_ID='LuLu02'},
    3: {"Bed":"Bed03", "IP": "192.168.1.203", "Info": "請輸入病歷號", client_ID='LuLu03'},
    5: {"Bed":"Bed05", "IP": "192.168.1.205", "Info": "請輸入病歷號", client_ID='LuLu05'},
    6: {"Bed":"Bed06", "IP": "192.168.1.206", "Info": "請輸入病歷號", client_ID='LuLu06'},
    7: {"Bed":"Bed07", "IP": "192.168.1.207", "Info": "請輸入病歷號", client_ID='LuLu07'},
    8: {"Bed":"Bed08", "IP": "192.168.1.208", "Info": "請輸入病歷號", client_ID='LuLu08'},
    9: {"Bed":"Bed09", "IP": "192.168.1.209", "Info": "請輸入病歷號", client_ID='LuLu09'},
    17: {"Bed":"Bed17", "IP": "192.168.1.217", "Info": "請輸入病歷號", client_ID='LuLu17'},
    18: {"Bed":"Bed18", "IP": "192.168.1.218", "Info": "請輸入病歷號", client_ID='LuLu18'},
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
    btn = ttk.Button(right_frame, text=f"{data[i]['Bed']}\n{data[i]['Info']}", command=lambda num=i: display_info(num))
    btn.grid(row=i-1, column=0, pady=10)  # 使用i-1作為行索引，按鈕從第一行開始

# 啟動GUI主迴圈
root.mainloop()
