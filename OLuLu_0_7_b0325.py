import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import paho.mqtt.client as mqtt
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
    0: {"Bed": "3L01", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    1: {"Bed": "3L02", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    2: {"Bed": "3L03", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    3: {"Bed": "3L05", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    4: {"Bed": "3L06", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    5: {"Bed": "3L07", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    6: {"Bed": "3L08", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    7: {"Bed": "3L09", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    8: {"Bed": "3K17", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
    9: {"Bed": "3K18", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_number': '請選擇感測機組'},
}
#連線列表，字典，用於登錄感測器#第三個欄位（[2]）預定放置IP
client_dict={
    0:["01","grey",''],1:["02","grey",''],2:["03","grey",''],3:["05","grey",''],4:["06","grey",''],
    5:["07","grey",''],6:["08","grey",''],7:["09","grey",''],8:["17","grey",''],9:["18","grey",'']
    } 
#這個只有用來比對是不是合法客戶端
client_list=['LuLu01','LuLu02','LuLu03','LuLu05','LuLu06','LuLu07','LuLu08','LuLu09','LuLu17','LuLu18']
#主資料串列，但元素為字典；格式為{'client_number': new_ID, 'pt_number': 病歷號, 'time': [time.strftime('%Y-%m-%d %H:%M')], 'weight': [new_weight]}
data=[]


temporary_y=[] #暫存繪圖點之Y值
button_on_display = None
switch_1_8=1
#訊息顯示區，第一區可點選（使用tk，弄成flat使其看來不像按鈕），每點一次+1然後用餘數來做為選擇樣式的指令
#第二區原來單純顯示，但發現這樣跟第一區邊界不齊，所以改成一樣的格式。
#0: ["blue","yellow","(12)"],
#訊息顯示處
theme_number=0 #有N種主題就設N。0為原始
theme_total=1
t_n=0

#配色皆以字典儲存
style_info_0 = {0:["green","#FBFBFF"]} #下方中央資訊按鈕配色1，此配色也用於按鈕警示色，故背景需與style_bed相同。
style_info_1 = {0:["blue","white"]}#下方中央資訊按鈕配色2（一般）
style_info_2 = {0:["red","white"]}#下方中央資訊按鈕配色3（警示）
style_1_8={0:["black","#ECF5FF"]}#下方兩側按鈕
style_display={0:["orange","blue","white","#FFFAF4"]}#繪圖區[0:<500時顏色；1:>500時顏色；2:繪圖區背景色；3背景色]
style_bed={0:["black","#FBFBFF"]}#床位按鈕[0前景色，1背景]
style_bed_S={0:["white","orange"]}#選中床位按鈕[0前景色，1背景]
# 讀取CSV檔案
with open('olulu_theme.csv', 'r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    headers = next(csv_reader)  # 讀取標題行
# 處理每一行數據
    for i, row in enumerate(csv_reader):
        style_info_0[i+1] = [row[0], row[1]]
        style_info_1[i+1] = [row[2], row[3]]
        style_info_2[i+1] = [row[4], row[6]]
        style_1_8[i+1] = [row[6], row[7]]
        style_display[i+1] = [row[8], row[9], row[10], row[11]]
        style_bed[i+1] = [row[12], row[13]]
        style_bed_S[i+1] = [row[14], row[15]]
    theme_total = i + 2  # i+1 從1開始，所以總行數是 i + 1，內建有一組所以+2
    print(style_bed)

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
new_connected_clients = set()
thread_list=[] #開發用，用來追蹤有哪些執行緒，以免執行緒沒有中斷造成資源耗用爆炸
#MQTT連線用變數
#mqtt_server = "192.168.50.127"  # MQTT Broker 的 IP 位址，如果是筆電改150
mqtt_server = "192.168.50.150"  
mqtt_port = 1883
topic_sub="olulu/response"  #這個主題為接收訊息用
topic_pub="olulu/command"  #這個主題為廣播訊息用

#####################################################################################
#                             #以下是副thread 1, 連線                               #
#####################################################################################

#PC連接到 MQTT Broker 時，會呼叫此函數。rc 變數表示連線結果，rc == 0 表示連線成功。

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
        client.subscribe(topic_sub)
        print(f"Subscribed to {topic_sub}")
        client.publish(topic_pub, "9")  # 嘗試發送命令9
        print("Sent command: 9")
    else:
        print(f"Failed to connect, return code {rc}")

#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                        #-2-2 接收感測器訊息與訊息格式化 #                         #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#

#當 PC 端收到來自 MQTT Broker 的訊息時，此函數會被呼叫。
def on_message(client, userdata, msg):    
    message_buffer=''
    message_part1=''
    global closing,clients
    message = msg.payload.decode() #將接收到的訊息解碼為字串#在這裡名為payload，實際上就是感測器傳來的東西
    message.strip()
    #把新傳來的字串加上去
    message_buffer=message_buffer+message
    if "LuLu" in message_buffer:
        message_split = message_buffer.find("LuLu") + 6
        message_part1 = message_buffer[:message_split]
        message_buffer = message_buffer[message_split:]
    else:
        print("Invalid message received:", message_buffer)
        message_buffer = ""

    #接著將字串轉成list
    message_list = message_part1.split(",") #將傳入字串，以逗點分成list
    # 確保 `message_list` 至少有 2 個元素，避免錯誤
    if len(message_list) < 2:
        print(f"錯誤：無效的訊息格式 {message_list}")
        return
    print(message_list)
    if 'LuLu' in message_list[-1]: #確認為有效資料
        if message_list[0] == "R": #R字頭表回報身分編號
            message_R(message_list[-1]) #理論上這應該就是感測器的ID
        elif message_list[0] == "A":  #A表示回報數據
            message_A(message_list)
    message_buffer=''

#======================處理有新感測器連接======================

#現在留下處理選單的功能    
def message_R(device_id): 
    global client_dict,client_list,new_connected_clients,t_n,pt_info_data
    new_device=False    
    if device_id in client_list:
        for j in range(len(pt_info_data)):
            if device_id == pt_info_data[j]['client_number']: #表示是既有的
                new_device=False
                print('message_R',new_device)
                break
            else:
                new_device=True
        if new_device==True:
            for k in range(len(client_dict)):
                if client_dict[k][0]== device_id[-2:]:
                    client_dict[k][1] = "blue"  # 標記為已連線且尚未登錄
                    new_connected_clients.add(device_id[-2:]) #僅顯示編號。找一下logou那邊是不是登出時沒有delete掉？
                    print(f"{device_id} 已連線")
                else:
                    pass
        
        Display_text.config(text=f"請點選床位按鈕，選擇感測器：{new_connected_clients}登錄病人", foreground=style_info_1[t_n][0],anchor=tk.CENTER)
    else:
        print(f"非合格客戶端: {client_ip} (未登錄)")


#======================處理感測器的數據======================
def message_A(message_list):
    global data
    new_weight=None
    raw_wt_list=[]
    message_list.pop(0)  #去掉第一個（識別字元A）
    message_ID =message_list[-1] #表示這資料來自於哪個客戶端
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
    for i in range(len(data)): #這邊直接加入資料
        if data[i]['client_number'] == message_ID and data[i]['pt_number'] != '請輸入病歷號:':  #比對資料的ID（例如LuLu01等），且確定已有登錄
            #print(data[i])                
            if new_weight==-9999 and len(data[i]['weight'])>1: #表示有異常數值出現，不取                
                new_weight=data[i]['weight'][-1] #沿用上一個數字
            elif new_weight==-9999 and len(data[i]['weight'])<=1:
                new_weight=0
            with data_lock:
                data[i]['time'].append(time.strftime('%Y-%m-%d %H:%M')) #加入目前時間
                data[i]['weight'].append(new_weight)                    #加入目前數值
            found = True
            break
        else:
            pass
    if not found and message_ID in client_list: #新登錄的「合法」感測器，以ID為準（client_number）存檔
        for j in pt_info_data:
            if message_ID == pt_info_data[j]['client_number']: #在pt_info_data已有ID者表示已經登錄；如尚無病歷號則應跳過
                with data_lock:#這時建立該感測器與病人資料
                    data.append({'client_number': message_ID, 'pt_number': pt_info_data[j]['pt_number'], 'time': [time.strftime('%Y-%m-%d %H:%M')], 'weight': [new_weight]})
            else:
                pass
    else:
        pass
    #print(data)


#======================中斷連線（現在似乎改用登出即可，還沒重寫）======================   
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
                    print(f"感測器 {pt_info_data[i]['client_number']} IP 已重設為離線")
                    break

        logging_out_ip.task_done()  # **標記 queue 任務完成**


#####################################################################################
#           #               以下是副thread 2, 接收資料              #               #
#####################################################################################
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                        #-2-2處理訊息-#                           #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#======================2-2-1處理新連線感測器======================
def start_server():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message  
    try:
        client.connect(mqtt_server, mqtt_port, 60)
        client.loop_start()
        time.sleep(5)  # 等待 5 秒確認訊息
        client.publish(topic_pub, "9")  # 測試發送 '9'
        print("Sent test command: 9")
        time.sleep(5)  # 等待 5 秒確認訊息
        # 啟動時間控制程序，定時發訊息給感應器
        scan_clients(client)

    except socket.error as e:
        print(f"Socket error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
###############################以下是副thread 2, 控時################################
#                 由於要持續處理連線與資料交換，必須跟介面寫在不同的thread。        #
#####################################################################################
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
#                            #-  時間控制（主控程式）-#                             #
#-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--+-+--+--+--+--#
# ======================資料處理的主控程式。======================
#定期向客戶端發送訊息收集資料。
def scan_clients(client):
    global button_on_display
    global data,client_list
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
        if current_time.tm_sec %30 == 0: # 每分鐘的00,30秒執行掃描，送出9確認連線狀況
            print("scan_clients: 開始檢查連線狀態")
            if len(new_connected_clients) == 0:  # 只在沒有感測器回應時發送9
                client.publish(topic_pub, "9")
            time.sleep(1.5)
        if current_time.tm_sec == 5: # 每分鐘的05秒發送指令
            for device_id in client_list:
                topic = f"command/{device_id}"  # 每個設備有獨立的指令主題
                client.publish(topic, "1")
                print(f"Sent command 1 to {device_id}")
                time.sleep(0.1)  # 延遲 0.1 秒
        if time.localtime(time.time()).tm_sec == 25 and len(data)>0 and checked_data==False:#
            for j in range(len(data)): #檢查既有資料名單（已經有資料的才需要補齊）
                print('追蹤是否有補足資料的j:',j)
                if len(data[j]['weight']) >0 and data[j]['time'][-1] != (time.strftime('%Y-%m-%d %H:%M')): ##如某床位已有重量資料且其time欄位的最後一個時間並非目前時間
                    print('有缺漏')
                    with data_lock:
                        print(f"開始補數據, 當前 data: {data}")
                        print(f"當前 j: {j}, data[j]: {data[j]}")
                        print(f"當前 data[{j}]['weight']: {data[j]['weight']}, 類型: {type(data[j]['weight'])}, 長度: {len(data[j]['weight'])}")
                        if len(data[j]['weight']) == 0:
                            print(f"警告！data[{j}]['weight'] 為空列表，無法取 `-1`！")
                        else:
                            last_weight = data[j]['weight'][-1]  # 確保這行不會出錯
                            print(f"最後一個 weight: {last_weight}")
                            data[j]['weight'].append(last_weight)
                            print(f"補上一個重量後: {data[j]['weight']}")
                            data[j]['time'].append(time.strftime('%Y-%m-%d %H:%M')) #加上目前時間
                            print('補時間')
                            Display_text.config(text=f"請檢查 {data[j]['client_number']}感測器狀況",anchor=tk.CENTER)
                            #break #注意用break 跳出是否會發生沒有補齊的情形？
                else:
                    pass
            checked_data=True
            time.sleep(1)
        elif current_time.tm_sec == 26: #由於補資料很快，一定可以在一秒內完成，所以這邊設定到26秒的時候再改
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
            decreasing=[] #存入斜率漸減的clients
    # 因為每10分鐘才一次，故未與上面25秒處合併。
    # 折衷方式：不管如何，10分鐘存檔一次。為了減少硬碟讀取，將data裡存放每個病人60分鐘的資料，但每十分鐘就將最新的資料抓去存檔。並在每小時01分將data擷取最新60分鐘資料留存在記憶體內
    # 在35秒存檔，36秒重設存檔開關。由於登錄病人的邏輯改變，導致pt_info_data與data的indeces不一致，所以這裡隨之做出變化
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 35 and not saved and data !=[]:
            for k in range(len(pt_info_data)): #遍歷所有的床號
                if pt_info_data[k]['pt_number'] !='請輸入病歷號': #有登錄的
                    for j in range(len(data)): #找尋資料相符的
                        if data[j]['pt_number']== pt_info_data[k]['pt_number']: #找到相符的資料
                            file_name=pt_info_data[k]['pt_number']+'.csv' #用戶的病歷號當檔名
                            saving_data(data[j]['time'][-10:], data[j]['weight'][-10:], file_name) #把最後10項傳過去存檔
                            decreasing=data_analysis(data[j]['weight'][-10:],pt_info_data[k]['Bed'],k,decreasing) #資料分析；如果趨勢下降，添加
                saved= True #提早將saved設為True，以免在同一秒內又再來一次
#            for j in range(len(data)): #只檢查已經有資料的。由於data字典中是以IP為key,省略了病歷號，雖然在重新連線時可以自動把資料扔進data，但在存檔時就必須去pt_info_data取得病歷號用來存檔
#                for k in range(len(pt_info_data)): #接著遍歷所有的床號
#                    if pt_info_data[k]['pt_number'] !='請輸入病歷號': #有登錄的                    
#                        file_name=pt_info_data[k]['pt_number']+'.csv' #用戶的病歷號當檔名
#                        saving_data(data[j]['time'][-10:], data[j]['weight'][-10:], file_name) #把最後10項傳過去，但這要注意如果目前data未滿十項呢？先前沒有出狀況，應該是因為剛好我的資料是按順序存入
#                        decreasing=data_analysis(data[j]['weight'][-10:],pt_info_data[k]['Bed'],k,decreasing) #把可能要進行的資料分析在這時順便呼叫。如果趨勢下降，添加
#                    else: #無登錄的床號直接跳過
#                        pass
                
            Analysis_text.config(text=f"漸減：{decreasing}") #顯示顯示漸減的clients。如果將來資料太多電腦跑不完，那就將時間推遲。名稱為Analysis_text
            #time.sleep(1) #確定上面的事情做完時已經超過35秒了
        if current_time.tm_sec == 36:
            saved = False
            #---------開發中功能，在此偷渡一下計算目前顯示的病人的重量-----------
            turn_point_1=0
            difference=0
            diff_weight=0
            new_diff=0
            cal_weight=[]
            for i in range(len(data)):    #記憶體內的資料，button_on_display為主
                if data[i]['pt_number'] == pt_info_data[button_on_display]["pt_number"]  :
                    if len(data[i]["weight"]) < 10:
                        print("未滿10分鐘")
                        break
                    else:
                        cal_weight=data[i]["weight"][-10:]    #用最近10分鐘資料這個串列來計算
            if len(cal_weight)>0:
                slope,intercept=linear_regression(cal_weight) #取得回歸直線的常數項與斜率
                for j in range(0,len(cal_weight)-1,1):  #找出轉折點
                    new_diff= cal_weight[j+1]-cal_weight[j]
                    if new_diff < difference:
                        difference=new_diff
                        turn_point_1=j
                turn_point_2=turn_point_1+1 #下一點
                if turn_point_2>9: #轉折點在最後；理論上這不可能發生
                    diff_weight=np.max(cal_weight)-np.min(cal_weight)
                elif turn_point_1==0: #表示一路增加或穩定
                    diff_weight=np.max(cal_weight)-np.min(cal_weight)
                else:
                    point_1=cal_weight[turn_point_1]-(intercept+turn_point_1*slope)
                    point_2=cal_weight[turn_point_2]-(intercept+turn_point_2*slope)
                    if point_1 * point_2 <0 and abs(point_2-point_1) >10: #相鄰兩點在回歸線的兩邊，且差異大於10
                        cal_weight_1=data[:turn_point_1+1]
                        cal_weight_2=data[turn_point_1+1:]
                        diff_weight=np.max(cal_weight_1)-np.min(cal_weight_1)+np.max(cal_weight_2)-np.min(cal_weight_2)
            print('turn_point',turn_point_1)
            print('試算10分鐘重量變化',diff_weight)

                                
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
# ======================資料分析。======================
#~~~~~~~~~~~~~~~~~~分析入口~~~~~~~~~~~~~~~~~~
def data_analysis(weight,bed_no,k,decreasing):
    global button_on_display,pt_info_data
    
    style.configure("Decreasing.TButton", 
                    background=style_info_0[t_n][1],  # 背景色
                    foreground=style_info_0[t_n][0])  # 前景色
    style.configure("not_Decreasing.TButton", 
                    background=style_bed[t_n][1],  # 背景色
                    foreground=style_bed[t_n][0])  # 前景色
    
    if len(weight) < 10:
        return
    else:
        slope_10_5,intercept_10_5 =linear_regression(weight[-10:-5]) #最近的6-10分鐘數字
        slope_5_0,intercept_5_0 =linear_regression(weight[-5:]) #最近的五分鐘
        if slope_5_0 > slope_10_5: #最近的斜率較大
            #不管decreasing，因為這個只是用來顯示，而且先前在36秒已經重設為空
            #但是必須重設床位按鈕的文字顏色
            for i, button in enumerate(right_frame.winfo_children()):
                if i == k:
                    button.configure(style="not_Decreasing.TButton")
                    break
                else:
                    pass
        else: #最近的斜率較小，表示漸減
            decreasing.append(bed_no)
            if bed_no==pt_info_data[button_on_display]['Bed']:
                pass
            else:
            #床位按鈕的文字顏色設定為警告色
                for i, button in enumerate(right_frame.winfo_children()):
                    if i == k:
                        button.configure(style="Decreasing.TButton")
                        break
                    else:
                        pass
        print(decreasing)
        return decreasing

    
#~~~~~~~~~~~~~~~~~~線性回歸~~~~~~~~~~~~~~~~~~
def linear_regression(y):
    x = list(range(1, len(y) + 1))
    
    #計算線性回歸的斜率 (m) 和截距 (b)，為了簡單起見，一律只取五個數據點
    #參數: x: 獨立變數數據點， y: 依賴變數數據點，都是list
    #return:m: 斜率 b: 截距
    
    n = len(x)
    if n != len(y) or n == 0:
        raise ValueError("x 和 y 的長度必須相等且不為空")

    # 計算所需的中間值
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x_squared = sum(xi * xi for xi in x)

    # 計算斜率 m
    numerator = n * sum_xy - sum_x * sum_y
    denominator = n * sum_x_squared - sum_x * sum_x
    if denominator == 0:
        raise ValueError("除數為零，無法計算斜率")
    m = numerator / denominator

    # 計算截距 b
    b = (sum_y - m * sum_x) / n

    return m, b

##################################################################################### 
#                                 登出病人與結束程式                                #
#####################################################################################
# ======================感測器連同病人一併登出======================
def logout_client():
    global pt_info_data,button_on_display,clients,data, logging_out, client_to_be_closed,client_dict
    if button_on_display is not None:
        bed = pt_info_data[button_on_display]["Bed"]
        info = pt_info_data[button_on_display]["pt_number"]
        response = messagebox.askyesno("確認登出", f"是否確定登出？\n{bed}\n{info}")       
        if response:
            client_id = pt_info_data[button_on_display]["client_number"]   #準備要登出的ID
            bed = pt_info_data[button_on_display]["Bed"]
            info = pt_info_data[button_on_display]["pt_number"]
            #以下這段理論上是可以不用，但是先留著看看會怎樣
            closing_ip = pt_info_data[button_on_display]["client_IP"]  # 取出
            #if closing_ip != "離線":
            #    with logging_out_ip_lock:
            #        logging_out_ip.put(closing_ip)  # **將 IP 加入 queue，讓 close_connection() 處理**
            logout_file_name=pt_info_data[button_on_display]['pt_number']+'.csv' #用戶的病歷號當檔名。這兩個重要的資料再度設定，是為了確保最後工作的資料無誤
            pt_info_data[button_on_display]["pt_number"] = "請輸入病歷號"
            pt_info_data[button_on_display]["client_number"] = "請選擇感測機組"
            # 清除 pt_info_data 中的 IP 記錄；在MQTT版有可能不需要
            with pt_info_data_lock:
                pt_info_data[button_on_display]['client_IP'] = "離線"
            update_button_text(button_on_display,2)
            # 遍歷 client_dict 並更新感測器選擇清單
            for i in client_dict:
                print(i)
                with client_dict_lock:
                    print(client_dict[i][0])
                    if 'LuLu'+ client_dict[i][0] == client_id:                    
                        client_dict[i][1] = 'blue'  # 在MQTT版本，直接改回可以登錄狀態**
                        client_dict[i][2] = ''  # **確保 IP 也被清除**
                        break
            #應執行存檔，存檔完成後清空data中本項。注意是否確實存到非整點、非半點的資料
            for i in range(len(data)):
                if data[i]['client_number'] == client_id: #data字典中的client_number就是pt_data_list中的clien_number，如LuLu01等的ID
                    data_to_be_saved=data[i]    #轉存預計存檔的資料
                    del data[i]

                    if data_to_be_saved !=[]:
                        remained_item_n=-(time.localtime(time.time()).tm_min % 10)
                        saving_data(data_to_be_saved['time'][remained_item_n:], data_to_be_saved['weight'][remained_item_n:], logout_file_name) #傳過去
                else:
                    pass        
            
            print('已登出並存檔',data)
            left_canvas.delete("all")
            left_canvas.create_image(125, 1, image=init_image_tk, anchor="nw")
            return
            #return_to_main()
    else:
        messagebox.showinfo("注意", "請先選擇病床再登出")

#======================這個是按打叉完全退出程式======================
def on_closing(): #
    response = messagebox.askyesno("確認退出", "是否退出並將所有資料存檔？")
    global closing, clients  
    if response:  # 如果選擇是
        remained_item_n=-(time.localtime(time.time()).tm_min % 10) #因為十分鐘存檔一次
        try:
            # 執行存檔邏輯
            for j in range(len(data)): #檢查既有資料名單。
                for k in range(len(pt_info_data)):
                    if pt_info_data[k]['client_number']==data[j]['client_number']: #找到該筆data對應的病歷號
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
    global client_list,unassigned_clients, button_on_display, data, pt_info_data, new_connected_clients,client_dict
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
        global button_on_display,t_n,new_connected_clients
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
                pt_info_data[button_on_display]["client_number"] = 'LuLu' + chosen_client
                pt_info_data[button_on_display]["pt_number"] = patient_id
                pt_info_data[button_on_display]['client_IP'] = client_dict[int(selected_value)][2]
               
            with client_dict_lock:
                client_dict[int(selected_value)][1]='grey' #注意引數。改為灰色
            update_radio_buttons()                      #使其不能選取
            new_connected_clients.discard(chosen_client)  #移除已連線感測器名單
            Display_text.config(text=f"已連線的感測器： {new_connected_clients}",foreground=style_info_2[t_n][0],anchor=tk.CENTER) #顯示已連線的感測器
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

        # 將新已選按鈕（新按鈕，button_number）變色
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
#後來這個部分改為顯示重量的入口控管部
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
        client_id = pt_info_data[button_number]["client_number"]
        #由於顯示空間不夠，改用縮寫並在註記所顯示的資訊：第一行：床位、病歷號，第二行為協助偵錯，依次顯示按鈕編號、感測器編號、IP
        Display_text.config(text=f"Bed:{bed} \t Patient No.:{info_on_button} \t ID: {client_id}" ,foreground=style_info_0[t_n][0],anchor=tk.CENTER) #顯示選擇之資訊
        #print(text=f"IP: {client_i_p} Button:{button_number}")
        print(f"IP: {client_i_p} Button:{button_number}")
        one_eight_switch(one_eight_selection) 

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
    data_to_be_displayed = []  # 初始化變數
    # 取得 left_canvas 的寬度和高度
    canvas_width = left_canvas.winfo_width()
    canvas_height = left_canvas.winfo_height()
    # 計算置中位置
    center_x = canvas_width / 2
    center_y = canvas_height / 2


    
    #製造出顯示一小時或八小時資料時所需要的時間點陣列
    if switch_1_8==1:
        formatted_time_list = [(start_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') for i in range(60)]        
    else:
        formatted_time_list = [(start_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') for i in range(0,480,2)]

    # 讀取記憶體中的資料。如果是暫時登出又再連上，可在每分鐘如發現顯示陣列內資料個數不滿60筆時，就嘗試讀檔來補足顯示用資料。這部份現在還沒做好。要這樣做的話，可以把讀取資料的部分寫成函式）
    #
    for i in range(len(data)):    #記憶體內的資料，button_on_display為主
        if data[i]['pt_number'] == pt_info_data[button_on_display]["pt_number"]  : #本用感測器ID，但因MQTT版導入data也有pt_number，改用之
            data_to_be_displayed=data[i] #-*-
    if data_to_be_displayed!=[]:
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
                left_canvas.delete("all")
                # 使用計算出的置中位置和 anchor=tk.CENTER
                init_image_item = left_canvas.create_image(center_x, center_y, image=init_image_tk, anchor=tk.CENTER, tags="init_image")
                y=one_eight_switch(switch_1_8)
                print(f"記憶體內的資料處理錯誤：{e}")
            if len(data_to_be_displayed['time'])<60:
                getfiledata(y,formatted_time_list)
            else:
                pass
    else:
        Display_text.config(text=f"尚無資料可供繪圖")
        #顯示起始圖
        left_canvas.delete("all")
        #使用計算出的置中位置和 anchor=tk.CENTER
        init_image_item = left_canvas.create_image(center_x, center_y, image=init_image_tk, anchor=tk.CENTER, tags="init_image")
        return
        
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
    if button_on_display is None:
        print("請先選擇一個床位按鈕")
        return
    
    switch_1_8 = 8 if switch_1_8 == 1 else 1 # 切換 switch_1_8 的值
    one_eight_switch(switch_1_8)
    print(f"切換到 {switch_1_8} 小時模式")
        
#======================繪製長條圖======================
def bargraph(switch_1_8,y):
    global t_n,temporary_y
    if not y:
        print("目前無資料可繪製圖形。") #這是為了曾經出現過的狀況，在shell關閉又開啟數次後畫不出圖來，經查仍在接收資料，但y是空的。先這樣試試看。
        left_canvas.create_image(125, 1, image=init_image_tk, anchor="nw")#理論上在這裡應該會先清空然後顯示起始畫面
        y=one_eight_switch(switch_1_8)
        return
    temporary_y=y
    left_canvas.config(bg=style_display[t_n][2])
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
    left_canvas.delete("all")
    try:
    # 繪製長條圖       
        for i in range(len(y)):
            x0 = 775- i*scale_x
            y0 = round(525 - y[i]/scale_y)
            x1 = 775- i*scale_x
            y1 = 525
            left_canvas.create_line(x0, y0, x1, y1, width=scale_x, fill=color_code)

    # X 軸和 Y 軸與參考線；有了參考線以後，軸加粗
        left_canvas.create_line(55, 525, 55, 0, fill="black", width=2)  # y 軸
        for j in range(0, 5):
            left_canvas.create_line(55, j * 100 + 25, 775, j * 100 + 25, fill="gray",width=1)      
        left_canvas.create_line(55, 525, 780, 525, fill="black", width=2)  # x 軸
        
    # X 軸刻度
        for i in range(0, 61, 10):
            left_canvas.create_line(55 + i * 12, 525, 55 + i * 12, 532, fill="black") #刻度線
            if switch_1_8==1: #數字
                left_canvas.create_text(55 + i * 12, 535, font=(12), text=i - 60, anchor=tk.N )
            else:
                left_canvas.create_text(55 + i * 12, 535, font=(12), text=(i - 60)*8, anchor=tk.N)
    # Y 軸刻度
        for j in range(0, 5):
            left_canvas.create_line(50, j * 100 + 25, 55, j * 100 + 25, fill="black")
            left_canvas.create_text(50, j * 100 + 25, font=(12), text=(5 - j) * 100*scale_y, anchor=tk.E)
            
    # X 軸和 Y 軸的標籤
        left_canvas.create_text(398, 550, font=(16), text="Time from now (min)", anchor=tk.N)
        y_title="Weight"
        for p in range(0,6):
            left_canvas.create_text(15, 200+15*p, font=(16), text=y_title[p], anchor=tk.S)
        left_canvas.create_text(15, 300, font=(12), text="(g)", anchor=tk.S)
        #補畫Y軸原點
        left_canvas.create_line(50, 525, 55, 525, fill="black")
        left_canvas.create_text(50, 520, font=(12), text=(0), anchor=tk.E)
      
    except Exception as e:
        print(f"繪製長條圖時發生錯誤：{e}")

#======================更新病人按鈕======================
# 或許這個可以把按鈕的文字分成左上、右上、下三區，各自用變數代表，這樣就可以依照呼叫時傳來的變數進行顯示
# -->或是將不同情況所需更新的寫成不同的buon config 內容，由呼叫時傳來的變數決定進行哪種顯示。因為現在只有兩個地方會更新按鈕，所以用這種方式集中管理
def update_button_text(button_number,action):
    button = right_frame.winfo_children()[button_number]
    bed_info = pt_info_data[button_number]
    if action==1:
        button.config(text=f"{bed_info['Bed']} \t {'['+bed_info['client_number'][-2:]+']'} \n {bed_info['pt_number']}")
    elif action==2:
        button.config(text=f"{bed_info['Bed']} \t {'離線'} \n {bed_info['pt_number']}")
        
#======================更新主題編號======================
def theme_selection(): #0：前景色（文字色），1：背景色
    global theme_number,t_n,button_on_display,temporary_y,theme_total   
    theme_number=theme_number+1
    t_n=(theme_number) % theme_total #t_n為現在所選到的主題編號。
    Display_text.config(bg=style_info_1[t_n][1], fg=style_info_1[t_n][0])
    Analysis_text.config(bg=style_info_1[t_n][1], fg=style_info_1[t_n][0])
    logout_client_button.config(bg=style_1_8[t_n][1])
    switch_button.config(bg=style_1_8[t_n][1])
    style.configure("TFrame", background=style_display[t_n][3])
    left_frame.config(style="TFrame")
    bargraph(switch_1_8,temporary_y) 
    right_frame.config(style="TFrame")
    root.configure(bg=style_display[t_n][3]) #2/22打開這個看看，如果沒有什麼意義就再關掉
    
# 更新 TButton 和 Selected.TButton 的樣式定義
    style.configure("TButton", 
                    font=("Arial", 12), 
                    padding=5, 
                    background=style_bed[t_n][1],  # 背景色
                    foreground=style_bed[t_n][0])  # 前景色
    style.configure("Selected.TButton", 
                    background=style_bed_S[t_n][1],  # 選中背景色
                    foreground=style_bed_S[t_n][0])  # 選中前景色
    

    for i, button in enumerate(right_frame.winfo_children()):
        if i == button_on_display:
            button.configure(style="Selected.TButton")
        else:
            button.configure(style="TButton")
    root.update()  # 強制刷新 UI
    
# ======================回到主畫面======================
def return_to_main():    
    global t_n
    new_connected_clients_str = ""
    for client, status in new_connected_clients.items():
        new_connected_clients_str += f"Client: {client}, Status: {status}\n"
    Display_text.config(text=f"點選床位按鈕以查看資料 \t 已連線的感測器：{new_connected_clients_str}", foreground=style_info_1[t_n][0],anchor=tk.CENTER)



#####################################################################################  
#                                       主畫面                                      #
#####################################################################################
# 初始化主畫面
root = tk.Tk()
root.title("OLuLu 0.70MQTT")
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
# 左區畫面，顯示資料區
left_frame = ttk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=10)  #改變padx可以改變其與其他元件的距離
# 右側畫面，選擇區
right_frame = ttk.Frame(root)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
# 宣告 Canvas (放置在 root 視窗上)
root_canvas = tk.Canvas(root, bg="#f0f0f0", highlightthickness=0)  # 假設的背景顏色
root_canvas.place(x=0, y=0, relwidth=1, relheight=1)  # 讓 Canvas 填滿整個 root 視窗
# 載入角落圖片
try:
    corner_image = Image.open("corner.png")  #指定角落圖片
    corner_image_tk = ImageTk.PhotoImage(corner_image)
    # 旋轉圖片
    rotated_90 = ImageTk.PhotoImage(corner_image.rotate(90))  # 右上角 90 度
    rotated_180 = ImageTk.PhotoImage(corner_image.rotate(180))  # 右下角 180 度
    rotated_270 = ImageTk.PhotoImage(corner_image.rotate(270))  # 左下角 270 度
except Exception as e:
    print(f"載入角落圖片發生錯誤：{e}")
# 放置圖片於視窗的四個角落
left_top_image = root_canvas.create_image(0, 0, anchor=tk.NW, image=corner_image_tk)
right_top_image = root_canvas.create_image(root.winfo_width(), 0, anchor=tk.NE, image=rotated_270)
left_bottom_image = root_canvas.create_image(0, root.winfo_height(), anchor=tk.SW, image=rotated_90)
right_bottom_image = root_canvas.create_image(root.winfo_width(), root.winfo_height(), anchor=tk.SE, image=rotated_180)

# 保持圖片引用
root_canvas.photo_images = [corner_image_tk, rotated_90, rotated_180, rotated_270] # 保持圖片引用
# 視窗大小改變時更新圖片位置
def update_image_positions(event):
    canvas_width = root.winfo_width()
    canvas_height = root.winfo_height()
    root_canvas.coords(left_top_image, 0, 0)
    root_canvas.coords(right_top_image, canvas_width, 0)
    root_canvas.coords(left_bottom_image, 0, canvas_height)
    root_canvas.coords(right_bottom_image, canvas_width, canvas_height)
root.bind("<Configure>", update_image_positions)

# 將 left_frame 和 right_frame 提升到 root_canvas 的上方
left_frame.lift()
right_frame.lift()

# 宣告 Canvas (左側框架)
left_canvas = tk.Canvas(left_frame, width=802, height=596) # bg="#e0f0ff"
left_canvas.grid(column=0, row=0, columnspan=3, padx=20, pady=0)

   
# 載入初始圖片
try:
    init_image = Image.open("copyright_1.jpg")  #指定圖片
    init_image_tk = ImageTk.PhotoImage(init_image)
    # 取得 left_canvas 的寬度和高度
    canvas_width = left_canvas.winfo_width()
    canvas_height = left_canvas.winfo_height()
    # 計算置中位置
    center_x = canvas_width / 2
    center_y = canvas_height / 2
    # 使用計算出的置中位置和 anchor=tk.CENTER
    init_image_item = left_canvas.create_image(center_x, center_y, image=init_image_tk, anchor=tk.CENTER, tags="init_image")
    # 在 left_canvas 大小改變時重新計算置中位置
    def update_init_image_position(event):
        canvas_width = left_canvas.winfo_width()
        canvas_height = left_canvas.winfo_height()
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        left_canvas.coords(init_image_item, center_x, center_y)

    left_canvas.bind("<Configure>", update_init_image_position)
except Exception as e:
    print(f"載入開機圖片發生錯誤：{e}")
    

# 顯示使用者所點選床位的資訊，height=2為兩行
Display_text = tk.Button(left_frame, text="等待感測器連線中",width=36, height=1,bg=style_info_1[t_n][1], fg=style_info_1[t_n][0], command=theme_selection,font=("Arial", 12),relief="flat")
Display_text.grid(column=1,row=1,sticky=tk.W+tk.E)
#顯示分析資料。本來因為單純顯示，所以只用label，但發現跟上面的大小不搭，試看看sticky=tk.W+tk.E。並且跟上面的一樣做成平面的按鈕，以免使用者混淆。
Analysis_text = tk.Button(left_frame, text="",width=36,bg=style_info_1[t_n][1], fg=style_info_1[t_n][0], command=theme_selection,font=("Arial", 12),anchor=tk.CENTER,relief="flat")
Analysis_text.grid(column=1,row=2,sticky=tk.W+tk.E)    
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

