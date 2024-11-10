#有好多個threads，為了不想每次都回頭看，按照主要－次要順序由上往下排
#原計畫要由使用者輸入每個客戶端的床號與病歷號，但因可能連線不穩頻繁斷線，每次重新連線時可能就要再重新輸入一次。當然也可以用時間法（斷線超過一小時以上才需要重新輸入），但為單傳起見，計畫先以固定代號配固定床號，使用者只需要輸入病歷號，而病歷號的更改須由使用者手動更改，不會因為斷線就重新輸入。病歷號僅供存檔之用，主機與客戶端溝通以客戶端代號為依歸。如果覺得客戶端與床號的對應關係綁死在code裡面不好更改，可以把它寫成csv檔，程式啟動時讀取，要更改就用cvs檔就好了。處理

import socket
import threading
import sys #結束程式用
import time #時間模組
from datetime import datetime #轉換時間格式方便使用
import csv #讀寫csv檔
import numpy as np #數學運算用
import statistics
import serial #序列埠通訊
import serial.tools.list_ports #為了自動搜尋通訊埠。如果要加速程式，而且固定使用在Unihiker的話，這個功能可以拿掉
import warnings #為了避開有的沒的警告
#import warnings #為了避開有的沒的警告
from sklearn.linear_model import LinearRegression #回歸用
#import matplotlib.pyplot as plt
import signal
import math

# 客戶端字典和數據變量
clients = {}          #字典：已連線、欲與之交流的客戶端
scanned_clients = {}  #字典：持續掃描連線的客戶端，結果放在這裡；是否需要宣告global?
#data = [{'name':'','time':[],'weight':[]}]             #串列：存放收集的資料；用串列比較易讀，但應注意是否會拖慢執行速度
mapping_clients =[{'name':'LuLu01','bed':'Bed01','chart_no':'1234567'},{'name':'LuLu02','bed':'Bed02','chart_no':'2345678'}]   #串列：client-床位-病歷號；或許要用字典？但考慮到只有三個而已，或許用串列就好了，畢竟很容易找到想要的index。現在先設成固定式，日後可以依照連線有無顯示是否需要使用者輸入病歷號
#以後要更換字典裡的chart_no
#更改方式mapping_clients[N]['chart_no']='xxxxxxxx'
data=[]

#----------共通函數宣告完畢------------
#----------各函式----------------------
# 0.初始化伺服器並接受客戶端連線，可以視為主程式
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("192.168.1.101", 8080))  
    server.listen()
    print("[伺服器啟動] 等待客戶端連線...")

    # 啟動定時發訊息線程
    threading.Thread(target=scan_clients, daemon=True).start()

    # 持續接受新客戶端連線
    while True:
        client_socket, client_address = server.accept()
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()



# 1.定期向客戶端發送訊息（控時程式）
def scan_clients():
    saved='false'
    min_for_saving = [00,10,20,30,40,50]
    while True:
        current_time = time.localtime(time.time())
        if current_time.tm_sec == 59:  # 每分鐘的59秒執行掃描
            active_clients = list(clients.keys())
            for client_address in active_clients:
                client_socket = clients[client_address]
                try:
                    # 檢查客戶端是否仍然連線並發送訊息
                    client_socket.send("1".encode())
                    print(f"[發送訊息] 向 {client_address} 發送 '1'")
                except:
                    print(f"[移除] {client_address} 已中斷連線")
                    del clients[client_address]
                    if client_address in scanned_clients:
                        del scanned_clients[client_address]
                time.sleep(1)  # 避免連續發送，等一秒
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 30 and saved=='false':  # 每10分鐘的30秒執行存檔
            for j, entry in enumerate(mapping_clients): #活躍的用戶:
                if mapping_clients[j]['chart_no'] !='':
                    file_name=mapping_clients[j]['chart_no']+'.csv' #用戶的病歷號
                    saving_data(data[j]['time'], data[j]['weight'], file_name)
                    saved='true' #開關設成已存
                else:
                    pass
        elif current_time.tm_sec == 31:
            saved='false' #重設是否已存檔開關
#1-1            
#def saving_data(saving_time, saving_weight, cutting_index,saving_raw): #位置一為time_INDEX，二是weight_FLUID，三是分鐘；由於要改用普通電腦當主機，功能較強，打算每10分鐘存檔一次，所以暫時捨棄這個複雜的方法。
#且目前暫時不打算存入原始資料list，除非實際使用後常常出現怪異數值
def saving_data(saving_time, saving_weight, file_name): #試試看由控時函式處理
    if saving_weight:
        #hour_weight_change = calculate_weight_changes(0)#從0開始算，該函式回傳數值weight_sum在此會放進hour_weight_change。
        #time_marker = time.strftime('%Y-%m-%d, %H:%M')

        file_time = saving_time
        file_weight = [w for t, w in zip(saving_time, saving_weight) ] #把兩個串列裡相同位置的元素配在一起
        with open(file_name, 'a', newline='') as csvfile:
            wt = csv.writer(csvfile)
            #print('file_weight:'+file_weight)
            for save_time, save_weight in zip(file_time, file_weight):
                wt.writerow([save_time, save_weight])#, save_raw])
            print(file_name+'存檔完成')
            
        #return saving_time, saving_weight,file_weight, saving_raw

            
# 2.處理個別客戶端的函式
def handle_client(client_socket, client_address):
    # 客戶端加入 clients 字典
    clients[client_address] = client_socket #此clients為一局域list
    #print(f"[連線成功] {client_address} 連接至伺服器")

    # 對新連入的客戶端。發送指令 '9' 要求回報身分編號
    if client_address not in scanned_clients:
        client_socket.send("9".encode())
        scanned_clients[client_address] = True
        #print(f"[連線中] {client_address} 發送身分識別要求...")
    #不知道以下是不是一直都會執行，不會被前面阻斷？
    while True:
        try:
            # 接收來自客戶端的訊息
            message = client_socket.recv(1024).decode()
            if not message:
                break  # 若無訊息則斷開連線；此點會不會就是頻繁斷線的問題所在？
            
            message_list = message.split(",")


            if message_list[0] == "A" and 'LuLu' in message_list[-1]:  # 確認是完整的訊息
                message_list.pop(0)  #去掉第一個（識別字元A）
                new_name = message_list.pop(-1) #將來要把一併傳入的身分編號，對應到病歷號
                raw_wt_list = list(map(int, message_list)) #把所得僅有重量的raw data轉換成串列
                
                if np.max(raw_wt_list) - np.min(raw_wt_list) <= 5: #來自02版，如果收到的資料變化不超過5，直接取平均；但這會不會是造成現行版本數字有些微波動的主因？是否直接取中位數就好？
                    new_weight = round(np.mean(raw_wt_list))
                else:                                               #不然就取中位數
                    new_weight = round(statistics.median(raw_wt_list))
                found = False
                for i, entry in enumerate(data):
                    if entry['name'] == new_name:
                        data[i]['time'].append(time.strftime('%Y-%m-%d, %H:%M'))
                        data[i]['weight'].append(new_weight)
                        found = True
                        break
                if not found:
                    data.append({'name': new_name, 'time': [time.time()], 'weight': [new_weight]})
            elif message_list[0] == "R": #R字頭表回報身分編號
                print(message_list[-1],'已連線')  # 目前寫這樣是確認程式可以執行到此處。接著要改成對應到另一個client-床位-病歷號的字典或串列
                
        except:
            print(f"[斷線] {client_address} 已中斷連線")
            del clients[client_address]
            if client_address in scanned_clients:
                del scanned_clients[client_address]
            client_socket.close()
            break
# 9.還不知道該放在哪裡的函式

    
# Function to plot scatter plot
def plot_scatter(Title,weight_plot):
    #global weight_FLUID,weight_PREVIOUS
    #weight_plot=weight_PREVIOUS+weight_FLUID
    print('weight_PLOT',weight_plot)
    x = np.arange(len(weight_plot))
    plt.scatter(x, weight_plot, c='g', marker='>')
    plt.title(Title)
    plt.xlim([0, 60])
    plt.show(block=False)
    plt.pause(0.1)
# 啟動伺服器
start_server()
while True:
    if time.localtime(time.time()).tm_sec ==30:
        print(data)
        plot_scatter('test',data[i]['weight'])

