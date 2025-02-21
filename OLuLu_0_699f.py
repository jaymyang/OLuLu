import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import socket
import queue
import concurrent.futures
import threading
import time
import csv
import numpy as np
import statistics
from datetime import datetime, timedelta
from PIL import Image, ImageTk
#from sklearn.linear_model import LinearRegression #回歸用。因Windows8的Python很難裝，直接拿掉

#formatted_time_list = []
#x=[]
#y=[]
# 主控資料用，字典。如連線則於clent_name顯示感測器ID，pt_number病歷號`。
pt_info_data = {
    0: {"Bed": "3L01", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    1: {"Bed": "3L02", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    2: {"Bed": "3L03", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    3: {"Bed": "3L05", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    4: {"Bed": "3L06", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    5: {"Bed": "3L07", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    6: {"Bed": "3L08", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    7: {"Bed": "3L09", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    8: {"Bed": "3K17", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
    9: {"Bed": "3K18", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': '請選擇感測機組'},
}
#連線列表，字典，用於登錄感測器#第三個欄位（[2]）預定放置IP
client_dict={
    0:["01","grey",''],1:["02","grey",''],2:["03","grey",''],3:["05","grey",''],4:["06","grey",''],
    5:["07","grey",''],6:["08","grey",''],7:["09","grey",''],8:["17","grey",''],9:["18","grey",'']
    } 
#這個只有用來比對是不是合法客戶端
client_list=['LuLu01','LuLu02','LuLu03','LuLu05','LuLu06','LuLu07','LuLu08','LuLu09','LuLu17','LuLu18']
#主資料串列
data=[]

temporary_y=[] #暫存繪圖之Y
button_on_display = None
switch_1_8=1
#以下為如做主題變化功能時所要用的；本來想要再加一個按鈕讓使用者選擇，但是覺得太亂。所以可以做成隱藏功能，將顯示資訊，目前設為不可點選的按鈕，改成可點選，每點一次+1然後用餘數來做為選擇樣式（存在前面那兩個字典）的指令；而且因為改成可點選的隱藏版，就可以用tk就好，可以把它弄成flat使其看來不像按鈕
#0: ["blue","yellow","(12)"],
#訊息顯示處
theme_number=2 #有N種主題就設N。0為原始
t_n=0
style_info_0 = {
    0:["green","gray","(12)"],
    1:["#FFF5D9","#C1D57F"]}
style_info_1 = {
    0:["reD","white","(12)"],
    1:["#F8EBAE","#B79CC6"]}
style_info_2 = {
    0:["blue","white","(12)"],
    1:["#B79CC6","#F8EBAE"]}
#繪圖區下方按鈕
style_1_8={
    0:["black","#ECF5FF","(12)"],
    1:["#B4509A","#C1D57F"]}
#繪圖區
style_display={
    0:["orange","blue","white","#FFFAF4"],
    1:["#F8EBAE","#C1D57F","white","#FFF5D9"]} #[0:<500時顏色；1:>500時顏色；2:繪圖區背景色；3背景色]
#床位按鈕
style_bed={
    0:["black","#FBFBFF","(12)"],
    1:["#B79CC6","#F8EBAE"]} #[0前景色，1背景]
style_bed_S={
    0:["white","orange","(12)"],
    1:["#F8EBAE","#B79CC6"]}
#測試用來關閉程式的開關
closing=False
# clients：連線的客戶端字典；用來控制與客戶端的溝通，因為擔心thread競爭，加上鎖
clients = {}
#以下宣告鎖與跨線序
clients_lock = threading.Lock()
logging_out_ip_lock = threading.Lock()
pt_info_data_lock = threading.Lock()
client_dict_lock = threading.Lock()
data_lock = threading.Lock()

logging_out_ip=queue.Queue()
# 所有連線的客戶端的集合，利用集合僅能有一個相同值的特性
connected_clients = set()
thread_list=[] #開發用，用來追蹤有哪些執行緒，以免執行緒沒有中斷造成資源耗用爆炸


#####################################################################################
#                             #以下是副thread 1, 連線                               #
#####################################################################################
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                #-2-0. 伺服器主程式，初始化伺服器並接受客戶端連線                  #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
def start_server(): #    持續接受新客戶端連線
    print('Start server')
    global closing
    #global logging_out #這個變數只有LOG_OUT()可以改變。怎麼把它弄成不要用global呢？

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允許快速重用address
    #server.bind(("192.168.50.127", 8080))
    server.bind(("192.168.50.150", 8080))
    #server.bind(("192.168.1.101", 8080))
    server.listen(10) #設定最多10個連線
    t_close=threading.Thread(target=close_connection, daemon=True)
    thread_list.append(t_close)
    t_close.start()
    # 啟動時間控制程序，定時發訊息
    t_scan=threading.Thread(target=scan_clients, daemon=True)
    thread_list.append(t_scan)
    t_scan.start()
    
    # target=scan_clients: 指定執行緒要執行的函式是 scan_clients。daemon=True: 將執行緒設定為「守護執行緒 (daemon thread)」，當主程式結束時，會自動被終止。
    while True:
        if closing==True:
            break
              
        try:
            client_socket, client_address = server.accept()
            #暫停程式直到有新的客戶端連線請求，此時將返回一個包含客戶端 socket 物件和客戶端位址的元組。
            print(f"新客戶端連線: {client_address}")
            # **確保舊的連線被移除**
            with clients_lock:
                if client_address in clients:
                    print(f"發現重複的客戶端 {client_address}，刪除舊的連線")
                    clients[client_address].close()
                    del clients[client_address]


            client_socket.send("9".encode())
            print('client_socket.send("9".encode())')
            with clients_lock:
                clients[client_address] = client_socket  # 這樣確保只有一個執行緒在修改#將客戶端的 socket 物件儲存到 clients 字典中，鍵值為客戶端位址。
            #創建一個新的執行緒，並將 handle_client 函式作為執行緒的目標函式。放進thread_list以供追蹤
            t_client=threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True)
            thread_list.append(t_client)
            t_client.start()
        except Exception as e:
            print(f"伺服器錯誤: {e}")
            break
    server.close()

 #======================中斷連線======================   
def close_connection(): #
    global clients
    while True:
        closing_ip = logging_out_ip.get()  # **從 queue 取得要登出的 IP**
        print(f"嘗試關閉 IP: {closing_ip}")  # 確認 queue 內是否有正確的 IP

        if closing_ip is None:
            print("close_connection: closing_ip 為 None，跳過")
            continue

        found = False
        with clients_lock:
            print("目前 clients 內的 keys: ", clients.keys())  # 列出 clients 內的 IP
            
            for client_address, client_socket in list(clients.items()):
                print(f"檢查 client_address: {client_address}")  # 檢查目前處理的 client_address

                if str(client_address[0]) == closing_ip:  # **比對 IP 地址**
                    print(f"找到匹配的 IP: {client_address[0]}，準備關閉連線...")
                    found = True
                    try:
                        client_socket.shutdown(socket.SHUT_RDWR)
                        client_socket.close()
                        del clients[client_address]  # **從 clients 刪除**
                        print(f"已關閉 {closing_ip} 連線")
                    except Exception as e:
                        print(f"關閉 {closing_ip} 失敗: {e}")
                    break

        if not found:
            print(f"未找到對應的客戶端 {closing_ip}，可能已經斷線")

        # **清除 `pt_info_data` 內的 IP**
        with pt_info_data_lock:
            for i in pt_info_data:
                if pt_info_data[i]['client_IP'] == closing_ip:
                    pt_info_data[i]['client_IP'] = "離線"
                    print(f"感測器 {pt_info_data[i]['client_name']} IP 已重設為離線")
                    break

        logging_out_ip.task_done()  # **標記 queue 任務完成**


#####################################################################################
#           #               以下是副thread 2, 接收資料              #               #
#####################################################################################
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                        #-2-2 接收感測器訊息與訊息格式化 #                         #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
def handle_client(client_socket, client_address): #client_address 是新連上的；clients是既有列表上的
    message_buffer=''
    message_part1=''
    global closing,clients #暫時先把clients當成global
    #print("處理{client_address}",clients)
    
    while True:
        if closing==True:
            break
        try:
            message = client_socket.recv(1024).decode()# 接收來自客戶端的訊息
            message.strip()
            #print('message', message)
            if not message:#假如無訊息
                print(f"客戶端 {client_address} 發送空訊息，可能是連線異常，保持連線")
                continue  # 不要直接關閉連線，而是繼續等待訊息
            #把新傳來的字串加上去
            message_buffer=message_buffer+message 
            message_split=message_buffer.index('LuLu')+6            #接下來要分字串
            message_part1=message_buffer[:message_split]
            message_buffer=message_buffer[message_split:]
            #接著將字串轉成陣列
            message_list = message_part1.split(",") #將傳入字串，以逗點分成list，
            if message_list[0] == "R": #R字頭表回報身分編號
                message_R(message_list,client_address)                
            elif message_list[0] == "A"  and 'LuLu' in message_list[-1]:  # 確認
                message_A(message_list)
            message_buffer=''
        
        except (socket.timeout, socket.error) as e:
            print(f"客戶端 {client_address} 回應錯誤：{e}")
            with clients_lock:
                if client_address in clients:
                    del clients[client_address]
            client_socket.close()
            print(f"客戶端 {client_address} 連線中斷")
            return  # 使用 return 而不是 break 來終止該執行緒

    client_socket.close() #Gemini說，這樣就會自動關閉執行緒
    with clients_lock:  # 使用鎖來保護 clients 字典
        if client_address in clients:
            del clients[client_address]#從字典中移除
    print(f"客戶端 {client_address} 連線中斷")

#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                        #-2-2處理訊息-#                           #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#======================2-2-1處理新連線感測器======================
def message_R(message_list, client_address): 
    global client_dict,client_list, connected_clients, t_n

    client_name = message_list[-1]  # 取得感測器名稱，例如 'LuLu01'
    client_ip = client_address[0]  # 取得感測器的 IP 地址
    print(f"{client_name} 已連線，IP: {client_ip}")

    if client_name in client_list:  # 檢查是否為合法感測器
        for j in client_dict:
            if 'LuLu' + client_dict[j][0] == client_name:
                client_dict[j][1] = "blue"  # 標記為已連線
                with client_dict_lock:
                    client_dict[j][2] = client_ip  # 更新 IP
                break
        
        connected_clients.add(client_name[-2:]) #僅顯示編號
        #print(client_dict)
        dataDisplay_text.config(text=f"{'已連線的感測器：'+str(connected_clients)} \n {'請點選床位按鈕登錄感測器與病人'}", foreground=style_info_1[t_n][0],anchor=tk.CENTER)

    else:
        print(f"非合格客戶端: {client_ip} (未登錄)")
        with clients_lock:
            if client_address in clients:
                client_socket = clients.get(client_address)
                if client_socket:
                    client_socket.close()
                    del clients[client_address]


#======================2-2-2處理感測器的數據======================
def message_A(message_list):
    global data
    new_weight=None
    raw_wt_list=[]
    print(raw_wt_list)
    message_list.pop(0)  #去掉第一個（識別字元A）
    new_name =message_list[-1] #表示這資料來自於哪個客戶端
    raw_data_list=list(map(int,message_list[1:-2]))#去頭尾且轉整數
    if len(raw_data_list)>0:
        for i in range(0,len(raw_data_list)):
            if -1000<raw_data_list[i] < 1000:
                raw_wt_list.append(raw_data_list[i])
            else:
                pass
    #處理過後，如果還有東西
    if len(raw_wt_list)>0:
        if np.max(raw_wt_list) - np.min(raw_wt_list) <= 5: #沿用02版，如果收到的資料變化不超過5，直接取平均；但這會不會是造成現行版本數字有些微波動的主因？是否直接取中位數就好？
            new_weight = round(np.mean(raw_wt_list))
        else:                                               #不然就取中位數
            new_weight = round(statistics.median(raw_wt_list))
    else: #全清空#此為異常數值
        new_weight=-9999 
    found = False
    for i, entry in enumerate(data):
        if entry['name'] == new_name: #data字典中的name就是例如LuLu01等的ID
            #print(data[i])
            with data_lock:
                data[i]['time'].append(time.strftime('%Y-%m-%d %H:%M'))
            if new_weight==-9999 and len(data[i]['weight'])>1: #表示有異常數值出現，不取                
                new_weight=data[i]['weight'][-1] #沿用上一個數字
            elif new_weight==-9999 and len(data[i]['weight'])<=1:
                new_weight=0
            with data_lock:
                data[i]['weight'].append(new_weight)
            found = True
            break
    if not found and new_name in client_list: #資料格式如下，以感測ID為準存檔；但如尚無ID則應跳過
        with data_lock:
            data.append({'name': new_name, 'time': [time.strftime('%Y-%m-%d %H:%M')], 'weight': [new_weight]})#等於'離線'，在這邊重建一個新的資料
        #break
    else:
        pass
    #print(data)



###############################以下是副thread 2, 控時################################
#                 由於要持續處理連線與資料交換，必須跟介面寫在不同的thread。        #
#####################################################################################
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                            #-  時間控制（主控程式）-#                             #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
# ======================資料處理的主控程式。======================
#定期向客戶端發送訊息收集資料。
def scan_clients():
    #print('scan clients')
    global button_on_display
    global data
    global unassigned_clients
    global closing
    saved = False
    min_for_saving = [0, 10, 20, 30, 40, 50]
    to_remove = []
    displayed=False
    checked_data=False 
    while True:
        
        current_time = time.localtime(time.time())

        if closing==True:
            break

        if current_time.tm_sec == 1: # 每分鐘的01秒執行掃描
            for client_address, client_socket in list(clients.items()):# 迭代 clients
                try:
                    client_socket.send("1".encode())
                    print(f'發送1 {client_address}')
                except (socket.error, BrokenPipeError) as e:
                    print(f"無法向 {client_address} 發送訊息，錯誤: {e}")
                    # 移除斷開的客戶端；但這要注意如果又自動連上了，為免使用者麻煩，應可自動尋找本來登錄處並且逕行加入資料
                    to_remove.append(client_address)  # 收集需要刪除的 client_address
                time.sleep(1)  # 每一秒鐘依次向名單中的客戶端發命令。
            with clients_lock:
                for address in to_remove:
                    if address in clients:
                        del clients[address]
                        clients[address].close()                
             
    # 每分鐘的25秒遍歷已登錄且連線中病人的time，如無符合目前時間的資料，就append.既有串列裡最後一個補足資料缺口
        if time.localtime(time.time()).tm_sec == 25 and len(data)>0 and checked_data==False:#
            for j in range(len(data)): #檢查既有資料名單。這邊查詢的方式改變，是因為data中，只有已登錄ID的床號與病歷號，才會有資料，所以_info_data與data的數據順序不再同步
                print('追蹤是否有補足資料的j:',j)
                if len(data[j]['weight']) >0: #如某床位已有重量資料
                    for k in range(len(pt_info_data)):
                        if pt_info_data[k]['client_IP'] !="離線" and pt_info_data[k]['client_name']==data[j]['name'] : #確認帳面上仍連線
                            if data[j]['time'][-1] != (time.strftime('%Y-%m-%d %H:%M')): #表示為帳面上已有連線的用戶，其time欄位的最後一個是否等於目前時間，如否～
                                with data_lock:
                                    data[j]['time'].append(time.strftime('%Y-%m-%d %H:%M')) #加上目前時間
                                    data[j]['weight'].append(data[j]['weight'][-1])  #加上既有串列裡最後一個
                                    display_text.config(f"請檢查 {data[j]['name']}感測器狀況",anchor=tk.CENTER)
                                break #注意用break 跳出是否會發生沒有補齊的情形？
                            else:
                                pass
                        else:
                            pass
            checked_data=True
        elif current_time.tm_sec == 26:
            checked_data=False 

     # 每分鐘的31秒更新顯示
        if current_time.tm_sec == 31 and len(data) >0:
            #print('displayed',displayed)
            if not displayed:
                displayed=display_info(button_on_display,displayed)
                print('displayed',displayed)
            else:
                time.sleep (0.1)
                pass
        elif current_time.tm_sec == 32:
            displayed=False #重設回尚未顯示

    # 因為每10分鐘才一次，故未與上面25秒處合併。
    # 在35秒存檔，36秒重設存檔開關。由於登錄病人的邏輯改變，導致pt_info_data與data的indeces不一致，所以這裡隨之做出變化
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 35 and not saved and data !=[]:
            for j in range(len(data)): #檢查既有資料名單。由於data字典中是以IP為key,省略了病歷號，雖然在重新連線時可以自動把資料扔進data，但在存檔時就必須去pt_info_data取得病歷號用來存檔
                for k in range(len(pt_info_data)): #所有的感測器；由於clien_lis 也是跟這個同步，所以這回圈不一定要用_info_daa
                    if pt_info_data[k]['pt_number'] !='請輸入病歷號' and pt_info_data[j]['client_IP'] !='離線': #有連線的用戶；這邊沒有考慮到有key病歷號但是離線的
                        file_name=pt_info_data[k]['pt_number']+'.csv' #用戶的病歷號當檔名
                        saving_data(data[j]['time'][-10:], data[j]['weight'][-10:], file_name) #把最後10項傳過去，但這要注意如果目前data未滿十項呢？
                    else:
                        pass
                else:
                    pass
    #折衷方式：不管如何，10分鐘存檔一次。為了減少硬碟讀取，將data裡存放每個病人60分鐘的資料，但每十分鐘就將最新的資料抓去存檔。並在每小時01分將data擷取最新60分鐘資料留存在記憶體內
            saved= True #所有的都已經跑過了，saved設為True，以免在同一秒內又再來一次            
        elif current_time.tm_sec == 36:
            saved = False #重設是否已存檔開關
     # 每整點的50秒裁減到只剩最多60個數據在記憶體中
        if time.localtime(time.time()).tm_min == 0 and time.localtime(time.time()).tm_sec == 50:
            with data_lock:
                data=data[-60:]        
        time.sleep(0.1) #休息一下0.1秒
        
# ======================存檔函數。======================
#目前暫時不打算存入原始資料list，除非實際使用後常常出現怪異數值
def saving_data(saving_time, saving_weight, file_name):
    try:

        # 檢查是否有值
        if not saving_time or not saving_weight:
            raise ValueError("輸入的 saving_time 或 saving_weight 為空")
        # 檢查 saving_time 和 saving_weight 長度是否相同。先前是都沒有這個問題啦，但萬一有會很麻煩
        if len(saving_time) != len(saving_weight):
            raise ValueError("saving_time 和 saving_weight 項數不符")
        # 整理要寫入的資料
        file_time = saving_time
        file_weight = [w for t, w in zip(saving_time, saving_weight)]  # 把兩個串列裡相同位置的元素配在一起
        
        # 寫入檔案
        with open(file_name, 'a', newline='') as csvfile:
            wt = csv.writer(csvfile)
            for save_time, save_weight in zip(file_time, file_weight):
                wt.writerow([save_time, save_weight])
            print(f"檔案 {file_name} 存檔完成")
    
    except ValueError as ve:
        print(f"資料處理錯誤: {ve}")
   
    except IOError as ioe:
        print(f"檔案操作錯誤: {ioe}")
    
    except Exception as e:
        print(f"未知錯誤: {e}")

##################################################################################### 
#                                 登出病人與結束程式                                #
#####################################################################################
# ======================感測器連同病人一併登出======================
def logout_client():
    global pt_info_data,button_on_display,clients,data, logging_out, client_to_be_closed

    if button_on_display is not None:
        bed = pt_info_data[button_on_display]["Bed"]
        info = pt_info_data[button_on_display]["pt_number"]
        #client_id = pt_info_data[button_on_display]["client_name"]   #準備要登出的ID
        response = messagebox.askyesno("確認登出", f"是否確定登出？\n{bed}\n{info}")       
        if response:
            client_id = pt_info_data[button_on_display]["client_name"]   #準備要登出的ID
            bed = pt_info_data[button_on_display]["Bed"]
            info = pt_info_data[button_on_display]["pt_number"]
            closing_ip = pt_info_data[button_on_display]["client_IP"]  # 取出
            if closing_ip != "離線":
                with logging_out_ip_lock:
                    logging_out_ip.put(closing_ip)  # **將 IP 加入 queue，讓 close_connection() 處理**

            logout_file_name=pt_info_data[button_on_display]['pt_number']+'.csv' #用戶的病歷號當檔名。這兩個重要的資料再度設定，是為了確保最後工作的資料無誤

            pt_info_data[button_on_display]["pt_number"] = "請輸入病歷號"
            pt_info_data[button_on_display]["client_name"] = "請選擇感測機組"
            # 清除 pt_info_data 中的 IP 記錄
            with pt_info_data_lock:
                pt_info_data[button_on_display]['client_IP'] = "離線"
            update_button_text(button_on_display,2)
            
            # 遍歷 client_dict 並更新感測器選擇清單
            for i, client in client_dict.items():
                if client[2] == closing_ip:
                    with client_dict_lock:
                        client_dict[i][1] = 'grey'  # **改回未連線狀態**
                        client_dict[i][2] = ''  # **確保 IP 也被清除**
                    break
              
            #應執行存檔，存檔完成後清空data中本項
            for i, entry in enumerate(data):
                if entry['name'] == client_id: #data字典中的name就是pt_data_list中的clien_name，如LuLu01等的ID
                    data_to_be_saved=data[i]    #轉存預計存檔的資料
                    del data[i]
            # 以下是chaGPT建議的寫法**刪除 `data` 內的相關資料**
            #data[:] = [entry for entry in data if entry["name"] != client_id]
                   
            if data!=[]:
                if data_to_be_saved !=[]:
                    remained_item_n=-(time.localtime(time.time()).tm_min % 10)
                    saving_data(data_to_be_saved['time'][remained_item_n:], data_to_be_saved['weight'][remained_item_n:], logout_file_name) #傳過去
                else:
                    pass        
            
            print('已登出並存檔',data)
            canvas.delete("all")
            canvas.create_image(90, 1, image=init_image_tk, anchor="nw")
            return_to_main()
    else:
        messagebox.showinfo("注意", "請先選擇病床再登出")

#======================這個是按打叉完全退出程式======================
def on_closing(): #
    response = messagebox.askyesno("確認退出", "是否存檔並退出？")
    global closing, clients  
    if response:  # 如果選擇是
        remained_item_n=-(time.localtime(time.time()).tm_min % 10)
        try:
            # 執行存檔邏輯
            for j in range(len(data)): #檢查既有資料名單。
                for k in range(len(pt_info_data)):
                    if pt_info_data[k]['client_name']==data[j]['name']: #找到該筆data對應的病歷號
                        file_name = f"{pt_info_data[k]['pt_number']}.csv"
                        saving_data(data[j]['time'][remained_item_n:], data[j]['weight'][remained_item_n:], file_name)

            print("所有資料已存檔，感謝您的使用。")
            print(thread_list)
             # 關閉所有客戶端連線
            for client_ip, client_socket in list(clients.items()):
                try:
                    client_socket.close()
                    print(f"已關閉連線至 {client_ip}")
                except Exception as e:
                    print(f"關閉 {client_ip} 時發生錯誤: {e}")

            clients.clear()  # 清空 `clients` 字典
            closing=True
        except Exception as e:
            messagebox.showerror("存檔錯誤", f"存檔時發生錯誤：{e}")
        finally:
            if root.winfo_exists():  # 確保 root 存在
                root.destroy()  # 確保程式退出
    else:
        print("取消關閉視窗")

#####################################################################################
#MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM 主thread：介面 MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM#
#####################################################################################
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#               首先決定按下按鈕後，該進行登錄新病人或是顯示資料                    #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
def display_switch(selection):
    if pt_info_data[selection]["pt_number"]=="請輸入病歷號":#尚未登錄病人，輸入病人資料        
        assign_bed(selection,False)
    else: #已有登錄病人，顯示病人資料
        display_info(selection,False)
        
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                           #-將病人與感測器登錄到病床-#                            #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
def assign_bed(button_number,assign_bed_displayed): #button_number就是所選的按鈕編號，由0起算
    global client_list,unassigned_clients, button_on_display, data, pt_info_data, connected_clients,client_dict
    #應注意上面的諸多變數希望能改成有lock的
    if button_on_display==None:
        button_on_display=button_number
        
#-----------------次函式：更新radiobutton的標籤----------------        
    def update_label():        #用紅色顯示使用者的選擇
        selected_value = selected_option.get()
        label.config(text=f"感測器選擇：{client_dict[int(selected_value)][0]}", fg="red")
        # 更新所有 RadioButton 的顏色
        for i, radio in radio_buttons.items():
            if i == int(selected_value):
                radio.config(fg="red")
            else:
                radio.config(fg="blue")

#-----------------次函式：確認使用者的選擇----------------  
    def confirm_selection(button_number):    #按下確認後處理感測器選擇與病歷號輸入內容
        global button_on_display,t_n
        selected_value = selected_option.get()#選到的選項
        if selected_value is None or not selected_value.strip(): # 檢查 None
            messagebox.showwarning("請選擇一個感測器或直接關閉視窗")
            return
        else:
            try: # 嘗試轉換為整數，並捕捉可能的 ValueError
                chosen_client = client_dict[int(selected_value)][0]
            except (ValueError, KeyError): # 如果 selected_value 無效，顯示錯誤訊息並返回
                messagebox.showwarning("選擇的感測器無效")
                return
        patient_id = patient_id_entry.get().strip()
        if patient_id !='':#假如並非空白
            with pt_info_data_lock:
                pt_info_data[button_on_display]["client_name"] = 'LuLu' + chosen_client
                pt_info_data[button_on_display]["pt_number"] = patient_id
                pt_info_data[button_on_display]['client_IP'] = client_dict[int(selected_value)][2]
               
            with client_dict_lock:
                client_dict[int(selected_value)][1]='grey' #注意引數。改為灰色
            update_radio_buttons()                      #使其不能選取
            connected_clients.discard(chosen_client)  #移除已連線感測器名單
            dataDisplay_text.config(text=f"已連線的感測器： \n {connected_clients}",foreground=style_info_2[t_n][0],anchor=tk.CENTER) #顯示已連線的感測器
            button_number = right_frame.winfo_children()[button_number]
            button_number.config(style="Selected.TButton")
            update_button_text(button_on_display,1)
            pass  
        else: #沒有輸入東西，則不動資料，將現選按鈕改為灰色（未選），先前按鈕改為黃色即可
            selected_button = right_frame.winfo_children()[button_on_display]
            selected_button.config(style="TButton")  # 恢復普通樣式
            button_on_display=previous_selected #就把button_on_display設回先前的值
            #button_number=button_on_display
            previous_button = right_frame.winfo_children()[button_on_display]
            previous_button.config(style="Selected.TButton")  # 恢復普通樣式
            pass
    # **重置 assign_bed_displayed 避免無窮遞迴**
        global assign_bed_displayed  
        assign_bed_displayed = False

        window.destroy()  # 關閉視窗
        
#~~~~~~~~~~~~~~~~~~~次次函式：更新radiobutton是否可選~~~~~~~~~~~~~~~~~~~
    def update_radio_buttons(): #更新 RadioButton
        for i, radio in radio_buttons.items():
            state = "normal" if client_dict[i][1] == "blue" else "disabled"
            radio.config(state=state, fg=client_dict[i][1])

#======================以下為本輸入視窗的主程序======================
    try:
        if assign_bed_displayed:
            return  # 避免重複執行 assign_bed()
        assign_bed_displayed = True  # 確保只執行一次
        
        if button_on_display is not None: #假如目前有已選取的按鈕（button_on_display）...
            previous_button = right_frame.winfo_children()[button_on_display] #將已選取按鈕（舊按鈕）的資訊存到previous button中
            previous_button.config(style="TButton")  # 將舊按鈕改為普通樣式
        previous_selected = button_on_display #將已選擇值暫存為previous_selected
        button_on_display = button_number #將已選按鈕值改為新按鈕（button_number）

        # 將新已選按鈕（新按鈕，buon_number）變色
        selected_button = right_frame.winfo_children()[button_number]
        selected_button.config(style="Selected.TButton")

    # 創建新視窗
        window = tk.Toplevel(root)
        window.title("選擇感測器與輸入病歷號")
        window.geometry("300x500")
        selected_option = tk.StringVar()
        selected_option.set(None)  # 設定為 None，確保預設沒有選擇
        radio_buttons = {}
        frame = tk.Frame(window, padx=20, pady=20)
        frame.pack()

    # 建立 RadioButton
        for i in client_dict:
            state = "normal" if client_dict[i][1] == "blue" else "disabled"  # 只有藍色的選項可以點選
            radio = tk.Radiobutton(frame, text=client_dict[i][0], variable=selected_option, value=str(i),command=update_label, fg=client_dict[i][1], state=state)
            radio.pack(anchor="w")
            radio_buttons[i] = radio  # 儲存按鈕物件

    # 顯示當前選擇
        label = tk.Label(frame, text="感測器選擇：", fg="red")
        label.pack(pady=10)

    # 病歷號輸入欄位
        tk.Label(frame, text="請輸入病歷號：").pack(pady=5)
        patient_id_entry = tk.Entry(frame)  # 直接啟用輸入框，讓使用者輸入
        patient_id_entry.pack(pady=5)

    # **確認按鈕（同時負責感測器選擇與病歷號輸入）**
        confirm_button = tk.Button(window, text="確認", command=lambda:confirm_selection(button_number))
        confirm_button.pack(pady=20)
        window.wait_window()  # 等待視窗關閉
        
    except Exception as e:
        print(f"ASSIGN_BED 發生錯誤：{e}")

#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                                    #-顯示重量-#                                   #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#======================顯示重量的入口函式======================
#不知道為什麼，這個display info跑了8次。後來這個部分改為顯示重量的入口控管部
def display_info(button_number, displayed):
    global button_on_display, data, pt_info_data
    y=[]
    one_eight_selection=1
    bed_number= ''
    if displayed==True:
        time.sleep(0.1)
        return
    try:# 重置先前選取的按鈕顏色
        if button_on_display is not None: #假如目前有已選取的按鈕（button_on_display）...
            previous_button = right_frame.winfo_children()[button_on_display] #將已選取按鈕（舊按鈕）的資訊存到previous button中
            previous_button.config(style="TButton")  # 將舊按鈕改為普通樣式
        previous_selected = button_on_display #將已選擇值暫存為previous_selected
        button_on_display = button_number #將已選按鈕值改為新按鈕（button_number）
        # 將新已選按鈕（新按鈕）變色
        selected_button = right_frame.winfo_children()[button_number]
        selected_button.config(style="Selected.TButton")
        # 從新已選按鈕pt_info_data抓取資料。這部份算是有點協助除錯，將來可刪除或簡化
        bed = pt_info_data[button_number]["Bed"]
        client_i_p = pt_info_data[button_number]["client_IP"]
        info_on_button = pt_info_data[button_number]["pt_number"]
        client_id = pt_info_data[button_number]["client_name"]        
        dataDisplay_text.config(text=f"Bed:{bed}     pt_number:{info_on_button}    Client ID: {client_id} \n Button {button_number} \t  client_IP: {client_i_p}",foreground=style_info_0[t_n][0],anchor=tk.CENTER) #顯示選擇之資訊
        one_eight_switch(one_eight_selection) 
        
        #-+--+--+--+--+-以下估計回歸，但因Windows 8版的Python限制，暫時停用-+--+--+--+--+-
#        trend_points=one_eight_switch(one_eight_selection)[1] #計算回歸用資料
#        if len(trend_points)>20: #超過20個非0資料點再計算
#            trend=[]
#            trend=trend_prediction(trend_points) #算回歸係數
#            dataDisplay_text.config(text=f"Button {button_number}\n Bed: {bed}\n pt_number: {info_on_button}\n 過去10分鐘重量變化: {trend[0]} \n 過去十分鐘趨勢: {trend[1]}")
        displayed=True
        return displayed

    except Exception as e:
        print(f"DISPLAY_INFO 發生錯誤：{e}")

# ======================準備繪圖資料並呼叫繪圖函式======================
#製造繪圖所用的資料點，後來呼叫繪圖改由這邊處理
def one_eight_switch(switch_1_8): #第一步：準備要畫圖的資料點
    global button_on_display
    y = []  # 清空舊資料
    trend_y=[] #用來計算回歸的
    start_time = datetime.now()
    
    #製造出顯示一小時或八小時資料時所需要的時間點陣列
    if switch_1_8==1:
        formatted_time_list = [(start_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') for i in range(60)]        
    else:
        formatted_time_list = [(start_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') for i in range(0,480,2)]

    # 讀取記憶體中的資料。如果是暫時登出又再連上，可在每分鐘如發現顯示陣列內資料個數不滿60筆時，就嘗試讀檔來補足顯示用資料。這部份現在還沒做好。要這樣做的話，可以把讀取資料的部分寫成函式）
    #
    for i, entry in enumerate(data):    #記憶體內的資料，button_on_display為主
        if entry['name'] == pt_info_data[button_on_display]["client_name"]  : ##-*-data字典中的name就是pt_data_list中的clien_name，如LuLu01等的ID
            data_to_be_displayed=data[i] #-*-

    if data_to_be_displayed["weight"] !=[] and button_on_display is not None: #當然，要有選擇到某位病人才行
        try:
            for time_point in formatted_time_list:
                if time_point in data_to_be_displayed['time']:
                    index = data_to_be_displayed['time'].index(time_point)
                    y.append(data_to_be_displayed['weight'][index])
                    trend_y.append(data_to_be_displayed['weight'][index])
                else:
                    y.append(0)                
        except Exception as e:
            canvas.delete("all")
            canvas.create_image(90, 1, image=init_image_tk, anchor="nw") #理論上在這裡應該會先清空然後顯示起始畫面
            y=one_eight_switch(switch_1_8)
            print(f"記憶體內的資料處理錯誤：{e}")
        if len(data_to_be_displayed['time'])<60:
            getfiledata(y,formatted_time_list)
        else:
            pass           
    # 如果是 8 小時模式，讀取檔案資料並補上在前面被當成0的部分
    if switch_1_8 == 8:
        getfiledata(y,formatted_time_list) #呼叫讀檔
    bargraph(switch_1_8,y)  #-*-
        
# ======================補足資料用的讀檔函式======================
def getfiledata(y,formatted_time_list): #讀檔函式
    global en_buon_numbe
    try:
        file_name = f"{pt_info_data[button_on_display]['pt_number']}.csv" #這個還好，就是直接讀出病歷的檔案
        with open(file_name, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            csv_data = {row[0]: float(row[1]) for row in reader}  # 時間:重量
        for i, time_point in enumerate(formatted_time_list):            
            if y[i] == 0 and time_point in csv_data:# 只補上 y[i] == 0（記憶體內無資料）
                y[i] = csv_data[time_point]
    except FileNotFoundError:
        print(f"檔案 {file_name} 不存在，無法讀取歷史資料。")
    except Exception as e:
        print(f"讀取檔案錯誤：{e}")
    return y
        
#======================切換一小時與八小時按鈕的事件處理======================
def toggle_switch():
    global switch_1_8
    # 切換 switch_1_8 的值
    switch_1_8 = 8 if switch_1_8 == 1 else 1
    one_eight_switch(switch_1_8)
    print(f"切換到 {switch_1_8} 小時模式")
        
#======================繪製長條圖======================
def bargraph(switch_1_8,y):
    global t_n,temporary_y
    if not y:
        print("目前無資料可繪製圖形。") #這是為了曾經出現過的狀況，在shell關閉又開啟數次後畫不出圖來，經查仍在接收資料，但y是空的。先這樣試試看。
        canvas.create_image(90, 1, image=init_image_tk, anchor="nw")#理論上在這裡應該會先清空然後顯示起始畫面
        y=one_eight_switch(switch_1_8)
        return
    temporary_y=y
    if switch_1_8==1:
        scale_x=12 #60個資料點
    else:
        scale_x=3 #240個資料點，每兩分鐘一個
    if np.max(y) >500:
        scale_y=2
        color_code=style_display[t_n][1] #'blue'
    else:
        scale_y=1
        color_code=style_display[t_n][0] #'orange'
    # 清除舊的長條圖
    canvas.delete("all")
    try:
    # 繪製長條圖       
        for i in range(len(y)):
            x0 = 775- i*scale_x
            y0 = round(525 - y[i]/scale_y)
            x1 = 775- i*scale_x
            y1 = 525
            canvas.create_line(x0, y0, x1, y1, width=scale_x, fill=color_code)

    # X 軸和 Y 軸與參考線
        canvas.create_line(55, 525, 55, 0, fill="black", width=1)  # y 軸
        for j in range(0, 5):
            canvas.create_line(50, j * 100 + 25, 55, j * 100 + 25, fill="gray")      
        canvas.create_line(55, 525, 775, 525, fill="black", width=1)  # x 軸
        
    # X 軸刻度
        for i in range(0, 61, 10):
            canvas.create_line(55 + i * 12, 525, 55 + i * 12, 532, fill="black")
            if switch_1_8==1:
                canvas.create_text(55 + i * 12, 535, font=(12), text=i - 60, anchor=tk.N )
            else:
                canvas.create_text(55 + i * 12, 535, font=(12), text=(i - 60)*8, anchor=tk.N)
    # Y 軸刻度
        for j in range(0, 5):
            canvas.create_line(50, j * 100 + 25, 55, j * 100 + 25, fill="black")
            canvas.create_text(50, j * 100 + 25, font=(12), text=(5 - j) * 100*scale_y, anchor=tk.E)
    # X 軸和 Y 軸的標籤
        canvas.create_text(390, 550, font=(16), text="Time from now (min)", anchor=tk.N)
        y_title="Weight"
        for p in range(0,6):
            canvas.create_text(12, 200+15*p, font=(16), text=y_title[p], anchor=tk.S)
        canvas.create_text(15, 320, font=(12), text="(g)", anchor=tk.S)
      
    except Exception as e:
        print(f"繪製長條圖時發生錯誤：{e}")

#======================更新病人按鈕======================
# 或許這個可以把按鈕的文字分成左上、右上、下三區，各自用變數代表，這樣就可以依照呼叫時傳來的變數進行顯示
# -->或是將不同情況所需更新的寫成不同的buon config 內容，由呼叫時傳來的變數決定進行哪種顯示。因為現在只有兩個地方會更新按鈕，所以用這種方式集中管理
def update_button_text(button_number,action):
    button = right_frame.winfo_children()[button_number]
    bed_info = pt_info_data[button_number]
    if action==1:
        button.config(text=f"{bed_info['Bed']} \t {'['+bed_info['client_name'][-2:]+']'} \n {bed_info['pt_number']}")
    elif action==2:
        button.config(text=f"{bed_info['Bed']} \t {'離線'} \n {bed_info['pt_number']}")
        
#======================更新主題編號======================
def theme_selection():
    global theme_number,t_n,button_on_display,temporary_y
    theme_number=theme_number+1
    t_n=theme_number % 2 #除數、theme_number要依照theme的數目來調整，有n個主題就除以n
    dataDisplay_text.config(bg=style_info_1[t_n][1], fg=style_info_1[t_n][0])
    logout_client_button.config(bg=style_1_8[t_n][1])
    switch_button.config(bg=style_1_8[t_n][1])
    style.configure("TFrame", background=style_display[t_n][3])
    left_frame.config(style="TFrame")
    bargraph(switch_1_8,temporary_y) 
    right_frame.config(style="TFrame")
    #root.configure(bg=style_display[t_n][3])
    
    # **更新所有床位按鈕**
    style.configure("TButton", font=("Arial", 12), padding=5,background=style_bed[t_n][1]) #右側按鈕色
    style.configure("Selected.TButton", background=style_bed_S[t_n][1], foreground=style_bed_S[t_n][0])#右側按鈕選擇色
    for i in right_frame.winfo_children():
        if i==button_on_display:
            button.config(style="Selected.TButton")
        else:

            button.config(style="TButton")
    
# ======================回到主畫面======================
def return_to_main():
    global t_n
    connected_clients_str = ""
    for client, status in connected_clients.items():
        connected_clients_str += f"Client: {client}, Status: {status}\n"
    dataDisplay_text.config(text=f"點選床位按鈕以查看資料 \n 已連線的感測器：\n{connected_clients_str}", foreground=style_info_1[t_n][0],anchor=tk.CENTER)

#####################################################################################  
#                                       主畫面                                      #
#####################################################################################
# 初始化主畫面
root = tk.Tk()
root.title("OLuLu 0.69")
root.geometry("1024x768")

# 定義樣式
style = ttk.Style()
style.theme_use('alt')
style.configure("TFrame", background=style_display[t_n][3]) #框架背景色
style.configure("TButton", font=("Arial", 12), padding=5,background=style_bed[t_n][1]) #右側按鈕色
style.configure("Selected.TButton", background=style_bed_S[t_n][1], foreground=style_bed_S[t_n][0])#右側按鈕選擇色

#style.configure("BButton", background="#FBFBFF")#下方按鈕色，但因下方按鈕使用tk，可以直接改色，不需如此
#style.map("Selected.TButton", background=[('active','red')])
style.configure("TLabel", font=("Arial", 12))
# 將視窗背景設色
root.configure(bg=style_display[t_n][2])

# 左區畫面，顯示資料區
left_frame = ttk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
# 右側畫面，選擇區
right_frame = ttk.Frame(root)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
# 宣告Canvas 
canvas = tk.Canvas(left_frame, width=800, height=600, bg=style_display[t_n][2])
canvas.grid(column=0,row=0,columnspan=3,padx=20,pady=0)       

# 載入初始圖片
try:
    init_image = Image.open("copyright_1.jpg")  #指定圖片
    init_image_tk = ImageTk.PhotoImage(init_image)
    canvas.create_image(90, 1, image=init_image_tk, anchor="nw")
except Exception as e:
    print(f"載入開機圖片發生錯誤：{e}")
# 顯示使用者點選床位的資料
dataDisplay_text = tk.Button(left_frame, text="等待感測器連線中",width=36, height=2,bg=style_info_1[t_n][1], fg=style_info_1[t_n][0], command=theme_selection,font=("Arial", 12),relief="flat")
#dataDisplay_text = ttk.Label(left_frame, text="等待感測器連線中 \n",width=36,font=("Arial", 12), foreground=style_info_1[t_n][0],background=style_info_1[t_n][1],command=theme_selection,anchor=tk.CENTER)
dataDisplay_text.grid(column=1,row=1)

    
#功能按鈕，注意尺寸大小單位是字元
switch_button = tk.Button(left_frame, text="切換1或8小時資料", width=20, height=1,command=toggle_switch, font=("Arial", 12),bg=style_1_8[t_n][1])
switch_button.grid(column=0,row=1)
logout_client_button = tk.Button(left_frame, text="登出病人", width=20, height=1,command=logout_client, font=("Arial", 12),bg=style_1_8[t_n][1])
logout_client_button.grid(column=2,row=1)
#床位按鈕
for i, info in pt_info_data.items():
    button = ttk.Button(
        right_frame,
        width="BOLD",
        text=f"{info['Bed']} \t {info['client_IP']} \n {info['pt_number']}",
        command=lambda i=i: display_switch(i),
        style="TButton"
    )
    button.pack(fill=tk.X,pady=2)

#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                                       #-啟動-#                                    #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
# 啟動伺服器
lock = threading.Lock()
threading.Thread(target=start_server, daemon=True).start()
# 綁定關閉事件
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()

