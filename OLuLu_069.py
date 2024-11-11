 在家裡的電腦這是070。出現NameError: name 'mapping_clients' is not defined. Did you mean: 'active_clients'?

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
    1: {"Bed": "Bed01", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu01'},
    2: {"Bed": "Bed02", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu02'},
    3: {"Bed": "Bed03", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu03'},
    # 其他床位可照此添加
}
clients = {}          # 已連線的客戶端
data = []             # 收集數據的串列
scanned_clients = {} 
current_button_number = None  # 記錄當前顯示的按鈕號碼，來源為客戶，輸出為病歷號

# 初始化主畫面
root = tk.Tk()
root.title("OLuLu version GUI")
root.geometry("1024x768")
left_frame = tk.Frame(root, width=768, height=768, bg="white")
left_frame.pack(side="left", fill="both", expand=1)
info_label = tk.Label(left_frame, text="Click a button to see details", bg="white", font=("Arial", 14))
info_label.pack(pady=50)
right_frame = tk.Frame(root, width=256, height=768)
right_frame.pack(side="right", fill="both", expand=0)

# 選取床位（主控面板）
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

# 更新按鈕
def update_button_text(button_number):
    for widget in right_frame.winfo_children():
        if widget.cget("text").startswith(pt_info_data[button_number]["Bed"]):
            client_id_text = pt_info_data[button_number]["client_ID"] if (pt_info_data[button_number]["client_ID"] in clients) else "離線"
            widget.config(text=f"{pt_info_data[button_number]['Bed']}\n{client_id_text}")
            break

# 回到主畫面
def return_to_main():
    info_label.config(text="Click a button to see details")

# 客戶端登出
def logout_client():
    if current_button_number is not None:
        bed = pt_info_data[current_button_number]["Bed"]
        info = pt_info_data[current_button_number]["Info"]
        response = messagebox.askyesno("確認登出", f"是否確定登出？\n{bed}\n{info}")
        
        if response:
            pt_info_data[current_button_number]["Info"] = "請輸入病歷號"
            pt_info_data[current_button_number]["client_ID"] = "登出"
            update_button_text(current_button_number)
            return_to_main()
    else:
        messagebox.showinfo("提示", "請先選擇病床再登出")


# 0. 伺服器主程式，初始化伺服器並接受客戶端連線
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("192.168.1.101", 8080))
    server.listen()
    threading.Thread(target=scan_clients, daemon=True).start()# 啟動定時發訊息線程
    # 持續接受新客戶端連線
    while True:
        client_socket, client_address = server.accept()
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

# 1.定期向客戶端發送訊息收集資料（控時程式）
def scan_clients():
    saved = False
    min_for_saving = [0, 10, 20, 30, 40, 50]
    while True:
        current_time = time.localtime(time.time())
        if current_time.tm_sec == 59: # 每分鐘的59秒執行掃描
            active_clients = list(clients.keys())
            for client_address in active_clients:
                client_socket = clients[client_address]
                try:# 檢查客戶端是否仍然連線並發送訊息
                    client_socket.send("1".encode())
                except:
                    del clients[client_address]
                    #if client_address in scanned_clients:
                    #    del scanned_clients[client_address]
                time.sleep(1)# 避免連續發送，等一秒
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 30 and not saved:
            for j, entry in enumerate(clients): #活躍的用戶:掃描完畢是放在哪裡？
                if clients[j]['chart_no'] !='':
                    file_name=clients[j]['chart_no']+'.csv' #用戶的病歷號
                    saving_data(data[j]['time'], data[j]['weight'], file_name)
                    saved= True
        elif current_time.tm_sec == 31:
            saved = False #重設是否已存檔開關

# 1-1. 存檔函數。目前暫時不打算存入原始資料list，除非實際使用後常常出現怪異數值
def saving_data(saving_time, saving_weight, file_name):
    #if saving_weight:
        #hour_weight_change = calculate_weight_changes(0)#從0開始算，該函式回傳數值weight_sum在此會放進hour_weight_change。
        #time_marker = time.strftime('%Y-%m-%d, %H:%M')

    file_time = saving_time
    file_weight = [w for t, w in zip(saving_time, saving_weight) ] #把兩個串列裡相同位置的元素配在一起
    with open(file_name, 'a', newline='') as csvfile:
        wt = csv.writer(csvfile)
        #print('file_weight:'+file_weight)
        for save_time, save_weight in zip(file_time, file_weight):
            wt.writerow([save_time, save_weight])#, save_raw])
        #print(file_name+'存檔完成')

# 2. 處理個別客戶端
def handle_client(client_socket, client_address):
    clients[client_address] = client_socket# 客戶端加入 clients 字典
        # 對新連入的客戶端。發送指令 '9' 要求回報身分編號
    if client_address not in clients:
        client_socket.send("9".encode())
        #clients[client_address] = True
        #print(f"[連線中] {client_address} 發送身分識別要求...")
    while True:
        try:
            message = client_socket.recv(1024).decode()# 接收來自客戶端的訊息
            if not message:
                break# 若無訊息則斷開連線；此點會不會就是頻繁斷線的問題所在？
            message_list = message.split(",")
            if message_list[0] == "A"  and 'LuLu' in message_list[-1]:  # 確認是完整的訊息
                message_list.pop(0)  #去掉第一個（識別字元A）
                new_name = message_list.pop(-1)
                if np.max(raw_wt_list) - np.min(raw_wt_list) <= 5: #來自02版，如果收到的資料變化不超過5，直接取平均；但這會不會是造成現行版本數字有些微波動的主因？是否直接取中位數就好？
                    new_weight = round(np.mean(raw_wt_list))
                else:                                               #不然就取中位數
                    new_weight = round(statistics.median(raw_wt_list))
                found = False
                for i, entry in enumerate(data):
                    if entry['name'] == new_name: #data字典中的name就是例如LuLu01等的ID
                        data[i]['time'].append(time.strftime('%Y-%m-%d, %H:%M'))
                        data[i]['weight'].append(new_weight)
                        found = True
                        break
                if not found:
                    data.append({'name': new_name, 'time': [time.time()], 'weight': [new_weight]})
            elif message_list[0] == "R": #R字頭表回報身分編號
                print(message_list[-1],'已連線')
                client_name=message_list[-1]
                for i, entry in enumerate(pt_info_data):                    
                    if entry['client_ID'] == client_name:
                        data[i]['client_name']=client_name

                  # 目前寫這樣是確認程式可以執行到此處。接著要改成對應到另一個client-床位-病歷號的字典或串列
        except:
            print(f"[斷線] {client_address} 已中斷連線")
            del clients[client_address]
            #if client_address in scanned_clients:
            #    del scanned_clients[client_address]
            client_socket.close()
            break

# 主畫面按鈕
displayok_button = tk.Button(left_frame, text="OK", command=return_to_main, font=("Arial", 12))
displayok_button.pack(side="left", padx=20, pady=10)
logout_client_button = tk.Button(left_frame, text="登出", command=logout_client, font=("Arial", 12))
logout_client_button.pack(side="right", padx=20, pady=10)

# 建立1x9的按鈕矩陣
for h in pt_info_data:
    btn = ttk.Button(right_frame, text=f"{pt_info_data[h]['Bed']}\n{pt_info_data[h]['Info']}", command=lambda num=h: display_info(num))
    btn.grid(row=h-1, column=0, pady=10)



# 啟動伺服器
threading.Thread(target=start_server, daemon=True).start()
root.mainloop()
