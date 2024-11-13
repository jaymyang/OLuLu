 #在家裡的電腦這是070。出現NameError: name 'mapping_clients' is not defined. Did you mean: 'active_clients'?

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import socket
import threading
import time
import csv
import numpy as np
import statistics
from datetime import datetime, timedelta

#----------------------------------------------------------------------------------------------#
# pt_info_data：介面工作用基本字典，如連線則於cleint_name顯示client_ID，Info為病歷號，client_ID為各個客戶端的名字，需與各客戶端的arduino code對應.
pt_info_data = {
    1: {"Bed": "Bed01", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu01'},
    2: {"Bed": "Bed02", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu02'},
    3: {"Bed": "Bed03", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu03'},
    4: {"Bed": "Bed05", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu05'},
    5: {"Bed": "Bed06", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu06'},
    6: {"Bed": "Bed07", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu07'},
    7: {"Bed": "Bed08", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu08'},
    8: {"Bed": "Bed17", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu17'},
    9: {"Bed": "Bed18", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu18'},
}
# clients：連線的客戶端字典；用來控制與客戶端的溝通
clients = {}
# data：用來放置收集到的數據的串列；內以字典方式記錄各客戶端（病歷號）的資料
data = []
# current_button_number用於記錄使用者點選的按鈕號碼，用以進行資料調度與顯示
current_button_number = None
#----------------------------------------------------------------------------------------------#

# 初始化主畫面
root = tk.Tk()
root.title("OLuLu 0.70")
root.geometry("1024x768")
##左半畫面，顯示詳細資訊區
left_frame = tk.Frame(root, width=768, height=768, bg="white")
left_frame.pack(side="left", fill="both", expand=1)
dataDisplay_text = tk.Label(left_frame, text="Click a button to see details", bg="white", font=("Arial", 14))#顯示點選的資料
dataDisplay_text.pack(pady=50)
##右半畫面，病人床位選擇區
right_frame = tk.Frame(root, width=256, height=768)
right_frame.pack(side="right", fill="both", expand=0)

# 位於右半畫面的選取床位主控面板
def display_info(button_number):
    global current_button_number
    current_button_number = button_number
    info_on_button = pt_info_data[button_number]["Info"] #設定為所選取的button
    
# pt_info_data：介面工作用基本字典，如連線則於cleint_name顯示client_ID，Info為病歷號，client_ID為各個客戶端的名字，需與各客戶端的arduino code對應.
#    1: {"Bed": "Bed01", "client_name": "離線", "Info": "請輸入病歷號", 'client_ID': 'LuLu01'},
    
    if info_on_button == "請輸入病歷號":
        patient_id = simpledialog.askstring("輸入病歷號", f"請輸入 {pt_info_data[button_number]['Bed']} 的病歷號:")
        if patient_id:  #輸入完成
            pt_info_data[button_number]["Info"] = patient_id #將字典的info設為所輸入的病歷號
            update_button_text(button_number) #更新按鈕
            
    #以下是從pt_info_data中抓取資料
    bed = pt_info_data[button_number]["Bed"]
    client_name = pt_info_data[button_number]["client_name"]
    info_on_button = pt_info_data[button_number]["Info"]
    #if pt_info_data[button_number]["client_ID"] in clients:
    client_id = pt_info_data[button_number]["client_ID"] 
    #else:
    #    pass
     #底下這個是左半的文字       
    dataDisplay_text.config(text=f"Button {button_number}\n Bed: {bed}\n client_name: {client_name}\n Info: {info_on_button}\n Client ID: {client_id}")#這是主要有問題的地方，本來是可以不要用的，因為要直接顯示長條圖
    #bar_graph() #顯示長條圖
    

# 更新按鈕所顯示內容。本來打算依照是否連線改變色，現在覺得只要更動client_name就可以
# 有輸入病歷號時，要更動button中的病歷號
# 連線時顯示client_ID，離線則顯示離線
def update_button_text(button_number):
    for widget in right_frame.winfo_children():
        #if widget.cget("text").startswith(pt_info_data[button_number]["Bed"]):
        if pt_info_data[button_number]["client_name"] in clients:
            client_id_text = pt_info_data[button_number]["client_ID"]
        else:
            client_id_text = "偵測器離線"
        widget.config(text=f"{pt_info_data[button_number]['Bed']}\n{client_id_text}")
        #break

# 回到主畫面
def return_to_main():
    dataDisplay_text.config(text="點選床位按鈕以查看資料")

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
        messagebox.showinfo("注意", "請先選擇病床再登出")


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
            #有在思考加進斷線的客戶端就顯示為離線或是按鈕換顏色，連上了又換回正常顏色
                
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 30 and not saved:
            for j, entry in enumerate(clients): #有連線的用戶
                if clients[j]['chart_no'] !='':
                    file_name=clients[j]['chart_no']+'.csv' #用戶的病歷號
                    saving_data(data[j]['time'], data[j]['weight'], file_name)
                    saved= True
        elif current_time.tm_sec == 31:
            saved = False #重設是否已存檔開關
        time.sleep(0.1) #休息一下1

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
            # 如果沒有傳入資料，目前設定以前一分鐘資料補上
            if time.localtime(time.time()).tm_sec == 29:#遍歷字典裡各病人的time，如無符合目前時間的資料，就append.list[-1]                
                for j, entry in enumerate(pt_info_data): #檢查病人名單
                    if pt_info_data[j]['client_name'] !="離線":#檢查每一位帳面上有連線的病人
                        for k, entry in enumerate(data): #檢查每一位病人的個別資料
                            if data[k]['time'][-1] != (time.strftime('%Y-%m-%d, %H:%M')): #表示為帳面上已有連線的用戶，其time欄位的最後一個是否等於目前時間，如否～
                                data[k]['time'].append(time.strftime('%Y-%m-%d, %H:%M')) #加上目前時間
                                data[k]['weight'].append(data[k]['weight'][-1])  #加上既有串列裡最後一個
                
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
