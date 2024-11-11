import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import socket
import threading
import time
import csv
import numpy as np
import statistics

# 字典，存入序號和病歷號
pt_info_data = {
    1: {"Bed": "Bed01", "IP": "", "Info": "請輸入病歷號", 'client_ID': 'LuLu01'},
    2: {"Bed": "Bed02", "IP": "", "Info": "請輸入病歷號", 'client_ID': 'LuLu02'},
    3: {"Bed": "Bed03", "IP": "", "Info": "請輸入病歷號", 'client_ID': 'LuLu03'},
    # 其他床位可照此添加
}
clients = {}          # 已連線的客戶端
data = []             # 收集數據的串列
current_button_number = None  # 記錄當前顯示的按鈕號碼

# 初始化主畫面
root = tk.Tk()
root.title("IP Button GUI")
root.geometry("1024x768")
left_frame = tk.Frame(root, width=768, height=768, bg="white")
left_frame.pack(side="left", fill="both", expand=1)
info_label = tk.Label(left_frame, text="Click a button to see details", bg="white", font=("Arial", 14))
info_label.pack(pady=50)
right_frame = tk.Frame(root, width=256, height=768)
right_frame.pack(side="right", fill="both", expand=0)

# 顯示選中內容的函數
def display_info(button_number):
    global current_button_number
    current_button_number = button_number
    info = pt_info_data[button_number]["Info"]
    
    if info == "請輸入病歷號":
        patient_id = simpledialog.askstring("輸入病歷號", f"請輸入 {pt_info_data[button_number]['Bed']} 的病歷號:")
        if patient_id:
            pt_info_data[button_number]["Info"] = patient_id
            update_button_text(button_number)
            
    bed = pt_info_data[button_number]["Bed"]
    ip = pt_info_data[button_number]["IP"]
    info = pt_info_data[button_number]["Info"]
    client_id = pt_info_data[button_number]["client_ID"] if (pt_info_data[button_number]["client_ID"] in clients) else "離線"
    info_label.config(text=f"Button {button_number}\nBed: {bed}\nIP: {ip}\nInfo: {info}\nClient ID: {client_id}")

# 更新按鈕上的文本
def update_button_text(button_number):
    for widget in right_frame.winfo_children():
        if widget.cget("text").startswith(pt_info_data[button_number]["Bed"]):
            client_id_text = pt_info_data[button_number]["client_ID"] if (pt_info_data[button_number]["client_ID"] in clients) else "離線"
            widget.config(text=f"{pt_info_data[button_number]['Bed']}\n{client_id_text}")
            break

# 回到主畫面
def return_to_main():
    info_label.config(text="Click a button to see details")

# 登出函數
def logout_client():
    if current_button_number is not None:
        bed = pt_info_data[current_button_number]["Bed"]
        info = pt_info_data[current_button_number]["Info"]
        response = messagebox.askyesno("確認登出", f"是否確定登出？\n{bed}\n{info}")
        
        if response:
            pt_info_data[current_button_number]["Info"] = "請輸入病歷號"
            pt_info_data[current_button_number]["client_ID"] = "請輸入病歷號"
            update_button_text(current_button_number)
            return_to_main()
    else:
        messagebox.showinfo("提示", "請先選擇病床再登出")

# OK 按鈕
displayok_button = tk.Button(left_frame, text="OK", command=return_to_main, font=("Arial", 12))
displayok_button.pack(side="left", padx=20, pady=10)
logout_client_button = tk.Button(left_frame, text="登出", command=logout_client, font=("Arial", 12))
logout_client_button.pack(side="right", padx=20, pady=10)

# 建立1x9的按鈕矩陣
for h in pt_info_data:
    btn = ttk.Button(right_frame, text=f"{pt_info_data[h]['Bed']}\n{pt_info_data[h]['Info']}", command=lambda num=h: display_info(num))
    btn.grid(row=h-1, column=0, pady=10)

# 啟動伺服器
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("192.168.1.101", 8080))
    server.listen()
    threading.Thread(target=scan_clients, daemon=True).start()
    while True:
        client_socket, client_address = server.accept()
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

# 定期掃描客戶端並存檔
def scan_clients():
    saved = False
    min_for_saving = [0, 10, 20, 30, 40, 50]
    while True:
        current_time = time.localtime(time.time())
        if current_time.tm_sec == 59:
            active_clients = list(clients.keys())
            for client_address in active_clients:
                client_socket = clients[client_address]
                try:
                    client_socket.send("1".encode())
                except:
                    del clients[client_address]
                time.sleep(1)
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 30 and not saved:
            for client in clients:
                file_name = pt_info_data[client]["client_ID"] + '.csv'
                saving_data(data, file_name)
            saved = True
        elif current_time.tm_sec == 31:
            saved = False

# 存檔函數
def saving_data(data, file_name):
    with open(file_name, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for entry in data:
            writer.writerow(entry)
        print(file_name + ' 存檔完成')

# 客戶端處理
def handle_client(client_socket, client_address):
    clients[client_address] = client_socket
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break
            message_list = message.split(",")
            if message_list[0] == "A":
                raw_wt_list = list(map(int, message_list[1:]))
                new_weight = round(np.mean(raw_wt_list)) if np.max(raw_wt_list) - np.min(raw_wt_list) <= 5 else round(statistics.median(raw_wt_list))
                data.append([time.strftime('%Y-%m-%d, %H:%M'), new_weight])
        except:
            del clients[client_address]
            client_socket.close()
            break

# 啟動伺服器
threading.Thread(target=start_server, daemon=True).start()
root.mainloop()
