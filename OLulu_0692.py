
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
# pt_info_data：介面工作用基本字典，如連線則於cleint_name顯示client_name，pt_number為病歷號，client_name為各個客戶端的名字，需與各客戶端的arduino code對應.
pt_info_data = {
    0: {"Bed": "Bed01", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu01'},
    1: {"Bed": "Bed02", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu02'},
    2: {"Bed": "Bed03", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu03'},
    3: {"Bed": "Bed05", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu05'},
    4: {"Bed": "Bed06", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu06'},
    5: {"Bed": "Bed07", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu07'},
    6: {"Bed": "Bed08", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu08'},
    7: {"Bed": "Bed17", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu17'},
    8: {"Bed": "Bed18", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu18'},
}
# clients：連線的客戶端字典；用來控制與客戶端的溝通
clients = {}
lock = threading.Lock()
# 所有連線的客戶端的集合
connected_clients = set()

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
    info_on_button = pt_info_data[button_number]["pt_number"] #設定為所選取的button
    
# pt_info_data：介面工作用基本字典，如連線則於cleint_name顯示client_name，pt_number為病歷號，client_name為各個客戶端的名字，需與各客戶端的arduino code對應.
#    1: {"Bed": "Bed01", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu01'},
    
    if info_on_button == "請輸入病歷號":
        patient_id = simpledialog.askstring("輸入病歷號", f"請輸入 {pt_info_data[button_number]['Bed']} 的病歷號:")
        if patient_id:  #輸入完成
            pt_info_data[button_number]["pt_number"] = patient_id #將字典的info設為所輸入的病歷號
            update_button_text(button_number) #更新按鈕
            
    #以下是從pt_info_data中抓取資料
    bed = pt_info_data[button_number]["Bed"]
    client_IP = pt_info_data[button_number]["client_IP"]
    info_on_button = pt_info_data[button_number]["pt_number"]
    #if pt_info_data[button_number]["client_name"] in clients:
    client_id = pt_info_data[button_number]["client_name"] 
    #else:
    #    pass
     #底下這個是左半的文字       
    dataDisplay_text.config(text=f"Button {button_number}\n Bed: {bed}\n client_IP: {client_IP}\n pt_number: {info_on_button}\n Client ID: {client_id}")#這是主要有問題的地方，本來是可以不要用的，因為要直接顯示長條圖
    #bar_graph() #顯示長條圖
    

# 更新按鈕所顯示內容。本來打算依照是否連線改變色，現在覺得只要更動client_IP就可以
# 有輸入病歷號時，要更動button中的病歷號。連線時顯示client_IP，離線則顯示離線
def update_button_text(button_number):
    widget=right_frame.winfo_children()

    widget[button_number].config(text=f"{pt_info_data[button_number]['Bed']} \n {pt_info_data[button_number]['client_IP']} \n {pt_info_data[button_number]['pt_number']} ")
        #if widget.cget("text").startswith(pt_info_data[button_number]["Bed"]):
        #if pt_info_data[button_number]["pt_number"] == "請輸入病歷號":
        #    client_id_text = pt_info_data[button_number]["pt_number"]
        #else:
        #    client_id_text = "偵測器離線"
    

# 回到主畫面
def return_to_main():
    dataDisplay_text.config(text="點選床位按鈕以查看資料")

# 客戶端登出
def logout_client():
    if current_button_number is not None:
        bed = pt_info_data[current_button_number]["Bed"]
        info = pt_info_data[current_button_number]["pt_number"]
        response = messagebox.askyesno("確認登出", f"是否確定登出？\n{bed}\n{info}")
        
        if response:
            pt_info_data[current_button_number]["pt_number"] = "請輸入病歷號"
            pt_info_data[current_button_number]["client_name"] = "登出"
            update_button_text(current_button_number)
            return_to_main()
    else:
        messagebox.showinfo("注意", "請先選擇病床再登出")


# 0. 伺服器主程式，初始化伺服器並接受客戶端連線
def start_server():
    print('start server')
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("192.168.1.101", 8080))
    server.listen(8)
    threading.Thread(target=scan_clients, daemon=True).start()# 啟動定時發訊息
    # 持續接受新客戶端連線
    while True:
        try:
            client_socket, client_address = server.accept()
            print(f"新客戶端連線: {client_address}")
            with lock:
                client_socket.send("9".encode()) #
                print('client_socket.send("9".encode())')
                clients[client_address] = client_socket
            threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()
        except Exception as e:
            print(f"伺服器錯誤: {e}")
            break
    server.close()
    

# 1.定期向客戶端發送訊息收集資料（控時程式）

def scan_clients():
    print('scan clients')
    saved = False
    min_for_saving = [0, 10, 20, 30, 40, 50]
    while True:
        current_time = time.localtime(time.time())
        if current_time.tm_sec == 1: # 每分鐘的01秒執行掃描
            with lock:  # 確保對 clients 的操作是線程安全的
                for client_address, client_socket in list(clients.items()):
                    try:
                        client_socket.send("1".encode())
                        print(f'發送1 {client_address}')
                    except (socket.error, BrokenPipeError) as e:
                        print(f"無法向 {client_address} 發送訊息，錯誤: {e}")
                        # 移除斷開的客戶端
                        del clients[client_address]
                        client_socket.close()
                    time.sleep(1)  # 掃描頻率
#有在思考加進斷線的客戶端就顯示為離線或是按鈕換顏色，連上了又換回正常顏色
# 如果沒有傳入資料，目前設定以前一分鐘資料補上
        if time.localtime(time.time()).tm_sec == 29 and len(data)>0 :#遍歷字典裡各病人的time，如無符合目前時間的資料，就append.list[-1]
            add_missing_data()
            print('29秒',data)
                
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 35 and not saved:
            for j in pt_info_data: #所有的客戶
                if pt_info_data[j]['pt_number'] !='請輸入病歷號': #有連線的用戶
                    file_name=pt_info_data[j]['pt_number']+'.csv' #用戶的病歷號當檔名
                    print(data)
                    saving_data(data[j]['time'], data[j]['weight'], file_name) #傳過去
                    saved= True
        elif current_time.tm_sec == 37:
            saved = False #重設是否已存檔開關
        time.sleep(0.1) #休息一下1

# 1-1. 存檔函數。目前暫時不打算存入原始資料list，除非實際使用後常常出現怪異數值
def saving_data(saving_time, saving_weight, file_name):
    print('saving sata')
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

# 2. 處理個別客戶端；下面是處理socket中的東西的範例－－雖然我不懂為什麼contains前後要加底線。
#a={('192.168.1.200', 21200): "socket_name:12345686"} # Replace <socket_name:12345686> with a string
#print(a.keys())
#print(str(a.keys()).__contains__('192.168.1.200'))
def handle_client(client_socket, client_address): #client_address 是新聯上的；clients是既有列表
    
# 對新連入的客戶端。發送指令 '9' 要求回報身分編號
    #if extising_client==False:
    while True:
        try:
            print('handle_clients')
            message = client_socket.recv(1024).decode()# 接收來自客戶端的訊息
            if not message:
                break# 若無訊息則斷開連線；此點會不會就是頻繁斷線的問題所在？
            message_list = message.split(",") #將傳入字串，以逗點分成list
            if message_list[0] == "A"  and 'LuLu' in message_list[-1]:  # 確認是完整的訊息
                message_list.pop(0)  #去掉第一個（識別字元A）
                new_name =message_list[-1]
                raw_wt_list=list(map(int,message_list[1:-2]))#去頭尾
                if len(raw_wt_list)>1:
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
                    break
                print(data)
            elif message_list[0] == "R": #R字頭表回報身分編號
                print(message_list[-1],'已連線')
                client_IP=message_list[-1]
                predefined_client= False
                for i in pt_info_data:
                    if pt_info_data[i]['client_name'] == message_list[-1]:
                        pt_info_data[i]['client_IP']=str(client_address[0]) #寫入pt_info_data中
                        predefined_client= True
                        update_button_text(i) 
                    else:
                        pass
                if predefined_client== False:
                    print('非合格客戶端:',client_address[0])
                        
                print(clients)
                print(connected_clients)
     

        except (socket.timeout, socket.error) as e:
            print(f"客戶端 {client_address} 回應超時")
            client_socket.close()            
        # 嘗試清理並重新連接
            with lock:
                clients.pop(client_address, None)
            return
        #except:
        #    print(f"[斷線] {client_address} 已中斷連線")
        #    del clients[client_address]
        #    client_socket.close()
        #    time.sleep(0.1)
        #    break



def add_missing_data():
    for j in pt_info_data: #檢查病人名單
        if pt_info_data[j]['client_IP'] !="離線":#檢查每一位帳面上有連線的病人
            for k, entry in enumerate(data): #檢查每一位病人的個別資料
                if data[k]['time'][-1] != (time.strftime('%Y-%m-%d, %H:%M')): #表示為帳面上已有連線的用戶，其time欄位的最後一個是否等於目前時間，如否～
                    data[k]['time'].append(time.strftime('%Y-%m-%d, %H:%M')) #加上目前時間
                    data[k]['weight'].append(data[k]['weight'][-1])  #加上既有串列裡最後一個
                            
# 主畫面按鈕
displayok_button = tk.Button(left_frame, text="OK", command=return_to_main, font=("Arial", 12))
displayok_button.pack(side="left", padx=20, pady=10)
logout_client_button = tk.Button(left_frame, text="登出", command=logout_client, font=("Arial", 12))
logout_client_button.pack(side="right", padx=20, pady=10)

# 建立1x9的按鈕矩陣
for h in pt_info_data:
    btn = ttk.Button(right_frame, text=f"{pt_info_data[h]['Bed']}\n{pt_info_data[h]['client_IP']}\n{pt_info_data[h]['pt_number']}", command=lambda num=h: display_info(num)) #指定點選的數字
    btn.grid(row=h, column=0, pady=10)

# 啟動伺服器
lock = threading.Lock()
threading.Thread(target=start_server, daemon=True).start()

root.mainloop()
