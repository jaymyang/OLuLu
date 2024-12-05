#待解決問題：關閉視窗時要把所有的thread關閉；整合0.2版的初估與預測功能。
#由於可能有多個地方匯出是，但不能停機，所以打算要放進很多個exception。因為打開csv時存檔失敗，接下來整個就不再接受新的資料輸入，畫不出圖來，但是帳面上還在運作。
#使用通用 Exception 捕捉錯誤：
#    如果需要捕捉所有錯誤而不退出程式，可以使用 except Exception as e。
#    務必在 except 塊中加入適當的記錄或處理方式（如 print 或 logging），以便日後檢查問題。
#打算放進去的：
#    except Exception as e:
#        print(f"發生錯誤：{e}")
#以下的finally是恩對連線問題的
#    finally:
#        client_socket.close()

#在關鍵區域添加 try-except：
#    將易於出錯的程式碼放入單獨的 try 區塊中，這樣即使發生錯誤，其他部分的程式碼也能繼續執行。

#使用 finally 保證資源釋放：

#    在結束時關閉連線或清理資源，無論是否出現錯誤。


    
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import socket
import threading
import time
import csv
import numpy as np
import statistics
from datetime import datetime, timedelta
from PIL import Image, ImageTk

formatted_time_list = []
x=[]
y=[]
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
# 所有連線的客戶端的集合
connected_clients = set()
# data：用來放置收集到的數據的串列；內以字典方式記錄各客戶端（病歷號）的資料
data = []
# current_button_number用於記錄使用者點選的按鈕號碼，用以進行資料調度與顯示
current_button_number = None
# 切換1或8小時的switch_1_8 值
switch_1_8 = 1

######以下是主thread, 介面######################################################

def display_info(button_number):
    global current_button_number

    y=[]
    one_eight_selection=1
    try:
        # 重置先前選取的按鈕顏色
        if current_button_number is not None:
            previous_button = right_frame.winfo_children()[current_button_number]
            previous_button.config(bg="SystemButtonFace", fg="black")  
        current_button_number = button_number
        # 設定目前選取的按鈕為橘底白字
        selected_button = right_frame.winfo_children()[button_number]
        selected_button.config(bg="orange", fg="white")
        #設定為所選取的button
        info_on_button = pt_info_data[button_number]["pt_number"] 

        if info_on_button == "請輸入病歷號":
            patient_id = simpledialog.askstring("輸入病歷號", f"請輸入 {pt_info_data[button_number]['Bed']} 的病歷號:")
            if patient_id:  #輸入完成
                pt_info_data[button_number]["pt_number"] = patient_id #將字典的info設為所輸入的病歷號
                update_button_text(button_number) #更新按鈕
            
    #以下是從pt_info_data中抓取資料
        bed = pt_info_data[button_number]["Bed"]
        client_IP = pt_info_data[button_number]["client_IP"]
        info_on_button = pt_info_data[button_number]["pt_number"]
        client_id = pt_info_data[button_number]["client_name"] 

        dataDisplay_text.config(text=f"Button {button_number}\n Bed: {bed}\n client_IP: {client_IP}\n pt_number: {info_on_button}\n Client ID: {client_id}",font=("Arial", 12))#這是主要有問題的地方，本來是可以不要用的，因為要直接顯示長條圖
        y_data_points=one_eight_switch(one_eight_selection) #呼叫切換與整理資料，預設值為1
        bargraph(one_eight_selection,y_data_points) #利用回傳資料，單純畫圖
    except Exception as e:
        print(f"發生錯誤：{e}")
        
def bargraph(switch_1_8,y):
    if not y:
        print("無法繪製圖形：資料為空") #這是為了曾經出現過的狀況，在chell關閉又開啟數次後畫不出圖來，經查仍在接收資料，但y是空的。先這樣試試看。
        y=one_eight_switch(switch_1_8)
        return
    
    if switch_1_8==1:
        scale_x=12 #60個資料點
    else:
        scale_x=3 #240個資料點，每兩分鐘一個
    if np.max(y) >500:
        scale_y=2
        color_code='blue'
    else:
        scale_y=1
        color_code='orange'
    # 清除舊的長條圖
    canvas.delete("all")
    try:
    # 繪製長條圖   
    
        for i in range(len(y)):
            x0 = 750- i*scale_x
            y0 = round(525 - y[i]/scale_y)
            x1 = 750- i*scale_x
            y1 = 525
            canvas.create_line(x0, y0, x1, y1, width=scale_x, fill=color_code)

    # X 軸和 Y 軸
        canvas.create_line(35, 525, 35, 0, fill="black", width=1)  # y 軸
        canvas.create_line(35, 525, 755, 525, fill="black", width=1)  # x 軸
    # X 軸刻度
        for i in range(0, 61, 10):
            canvas.create_line(35 + i * 12, 525, 35 + i * 12, 530, fill="black")
            if switch_1_8==1:
                canvas.create_text(35 + i * 12, 530, text=i - 60, anchor=tk.N)
            else:
                canvas.create_text(35 + i * 12, 530, text=(i - 60)*8, anchor=tk.N)
    # Y 軸刻度
        for j in range(0, 5):
            canvas.create_line(30, j * 100 + 25, 35, j * 100 + 25, fill="black")
            canvas.create_text(30, j * 100 + 25, text=(5 - j) * 100*scale_y, anchor=tk.E)
    # X 軸和 Y 軸的標籤
        canvas.create_text(395, 538, text="(min)", anchor=tk.N)
        canvas.create_text(15, 270, text="(g)", anchor=tk.S)
      
    except Exception as e:
        print(f"發生錯誤：{e}")

# 按鈕的事件處理
def toggle_switch():
    global switch_1_8
    # 切換 switch_1_8 的值
    switch_1_8 = 8 if switch_1_8 == 1 else 1
    print(f"切換到 {switch_1_8} 小時模式")
    try:
        # 更新資料並繪製圖表
        y_data_points=one_eight_switch(switch_1_8)  # 更新 y
        bargraph(switch_1_8,y_data_points)         # 繪製圖表
    except Exception as e:
        print(f"切換錯誤：{e}")
        

def one_eight_switch(switch_1_8):
    global current_button_number
    y = []  # 清空舊資料
    start_time = datetime.now()
    if switch_1_8==1:
        formatted_time_list = [
        (start_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') 
        for i in range(60)
    ]
        
    else:
        formatted_time_list = [
        (start_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') 
        for i in range(0,480,2)
    ]
         
    
    # 讀取記憶體中的資料
    if current_button_number is not None:
        try:
            for time_point in formatted_time_list:
                if time_point in data[current_button_number]['time']:
                    index = data[current_button_number]['time'].index(time_point)
                    y.append(data[current_button_number]['weight'][index])
                else:
                    y.append(0)
        except Exception as e:
            print(f"記憶體內的data處理錯誤：{e}")

    # 如果是 8 小時模式，讀取檔案資料並補上在前面被當成0的部分
    if switch_1_8 == 8:
        try:
            file_name = f"{pt_info_data[current_button_number]['pt_number']}.csv"
            with open(file_name, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                csv_data = {row[0]: float(row[1]) for row in reader}  # 時間:重量
            for i, time_point in enumerate(formatted_time_list):
                # 只對 `y[i] == 0`（內存資料中缺失）進行補充
                if y[i] == 0 and time_point in csv_data:
                    y[i] = csv_data[time_point]
        except FileNotFoundError:
            print(f"檔案 {file_name} 不存在，無法讀取歷史資料。")
        except Exception as e:
            print(f"讀取檔案錯誤：{e}")
    return y



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
            logout_file_name=pt_info_data[current_button_number]['pt_number']+'.csv' #用戶的病歷號當檔名
            
            pt_info_data[current_button_number]["pt_number"] = "請輸入病歷號"
            pt_info_data[current_button_number]["client_name"] = "登出" #這邊的用意是只有登出病人，並非要一併斷線。但問題是收進來的資料還是被存進daa－－理論上登出後，就算繼續發送起始訊號，也不應該將回報資料放進data
            #應執行存檔，存檔完成清空data中本項
            saving_data(data[current_button_number]['time'], data[current_button_number]['weight'], logout_file_name) #傳過去
            del data[current_button_number]
            update_button_text(current_button_number)
            print('已登出並存檔',data)
            return_to_main()
    else:
        messagebox.showinfo("注意", "請先選擇病床再登出")

def on_closing():
    response = messagebox.askyesno("確認退出", "是否存檔並退出？")
    if response:  # 如果選擇是
        remained_item_n=time.localtime(time.time()).tm_min % 10
        try:
            # 執行存檔邏輯
            for j in pt_info_data:
                if pt_info_data[j]['pt_number'] != '請輸入病歷號':
                    file_name = f"{pt_info_data[j]['pt_number']}.csv"
                    saving_data(data[j]['time'][-remained_item_n:], data[j]['weight'][-remained_item_n:], file_name)
            print("所有資料已存檔，程式即將關閉。")
        except Exception as e:
            messagebox.showerror("存檔錯誤", f"存檔時發生錯誤：{e}")
        finally:
            if root.winfo_exists():  # 確保 root 存在
                root.destroy()  # 確保程式退出
    else:
        print("取消關閉視窗")






######以下是副thread 2, 控時######################################################
#由於要持續處理連線與資料交換，必須跟介面寫在不同的thread。但是pt_info_data?
#有在思考加進斷線的客戶端就顯示為離線或是按鈕換顏色，連上了又換回正常顏色

# 2-1.資料處理的主控程式。定期向客戶端發送訊息收集資料。
def scan_clients():
    #print('scan clients')
    global current_button_number
    global data
    saved = False
    min_for_saving = [0, 10, 20, 30, 40, 50]
    while True:
        current_time = time.localtime(time.time())
     # 每分鐘的01秒執行掃描    
        if current_time.tm_sec == 1: # 每分鐘的01秒執行掃描
            #with lock:  # 確保對 clients 的操作是線程安全的；這個我想保留
            for client_address, client_socket in list(clients.items()):
                try:
                    client_socket.send("1".encode())
                    print(f'發送1 {client_address}')
                except (socket.error, BrokenPipeError) as e:
                    print(f"無法向 {client_address} 發送訊息，錯誤: {e}")
                    # 移除斷開的客戶端
                    del clients[client_address]
                    client_socket.close()
                time.sleep(1)  # 每一秒鐘依次向名單中的客戶端發命令。記得要在message_R那邊加上「切斷不在名單中的客戶端」功能
               
    # 每分鐘的25秒補足資料缺口 # 如果沒有傳入資料，目前設定以前一分鐘資料補上
        if time.localtime(time.time()).tm_sec == 25:#遍歷字典裡各病人的time，如無符合目前時間的資料，就append.list[-1]
            for j in pt_info_data: #檢查病人名單
                if pt_info_data[j]['client_IP'] !="離線" and len(data) >0:# 檢查每一位帳面上有連線的病人
                    for k, entry in enumerate(data): #檢查每一位病人的個別資料
                        if data[k]['time'][-1] != (time.strftime('%Y-%m-%d %H:%M')): #表示為帳面上已有連線的用戶，其time欄位的最後一個是否等於目前時間，如否～
                            data[k]['time'].append(time.strftime('%Y-%m-%d %H:%M')) #加上目前時間
                            data[k]['weight'].append(data[k]['weight'][-1])  #加上既有串列裡最後一個

         # 每分鐘的31秒更新顯示；這個要不要寫在主線？
        if current_time.tm_sec == 31 and len(data)>0: 
            display_info(current_button_number)
            #print('29秒',data)
    # 每10分鐘的35秒存檔，36秒重設存檔開關             
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 35 and not saved:
            for j in pt_info_data: #所有的客戶
                if pt_info_data[j]['pt_number'] !='請輸入病歷號': #有連線的用戶
                    file_name=pt_info_data[j]['pt_number']+'.csv' #用戶的病歷號當檔名
                    saving_data(data[j]['time'][-10:], data[j]['weight'][-10:], file_name) #把最後10項傳過去，但這要注意如果目前data未滿十項呢？
                    #data[j]['time']=[] #先用笨一點的方法，就是每十分鐘存檔一次並清空，避免data膨脹
                    #data[j]['weight']=[] #這種方法不一定比較差，是因為下面內存10分鐘的方法，還是得開檔剩下50分鐘的資料除非我在電腦裡存60分的資料。
                    
                    #複雜的方法，保留最近十分鐘的資料，把先前（10-20分鐘）的資料送去存。但這在最後登出病人時要記得把剩下的資料存進v去
                    #這種方法幫忙不大，除非我在電腦記憶體裡存60筆，但這又會碰到就是希望10分就存檔一次以減少意外發生造成的影響。
                    #折衷方式：不管如何，10分鐘存檔一次。為了減少硬碟讀取，將data裡存放每個病人60分鐘的資料，但每十分鐘就將最新的資料抓去存檔。並在每小時01分將data擷取最新60分鐘資料留存在記憶體內
            saved= True #所有的都已經跑過了，saved設為True，以免在同一秒內又再來一次
        elif current_time.tm_sec == 36:
            saved = False #重設是否已存檔開關
     # 每整點的50秒裁減到只剩最多60個數據在記憶體中
        if time.localtime(time.time()).tm_min == 0 and time.localtime(time.time()).tm_sec == 50:
            data=data[-60:]        
        time.sleep(0.1) #休息一下0.1秒
        
# 1-1. 存檔函數。目前暫時不打算存入原始資料list，除非實際使用後常常出現怪異數值
def saving_data(saving_time, saving_weight, file_name):
    try:
        #print('saving data', saving_time)
        #print('saving_weight', saving_weight)
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

######以下是副thread 1, 連線######################################################
# 2-0. 伺服器主程式，初始化伺服器並接受客戶端連線
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
            #with lock:
            client_socket.send("9".encode()) #
            print('client_socket.send("9".encode())')
            clients[client_address] = client_socket
            threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()
        except Exception as e:
            print(f"伺服器錯誤: {e}")
            break
    server.close()
######以下是副thread 3, 資料######################################################
# 2-2. 客戶端資料處理；下面是處理socket中的東西的範例－－雖然我不懂為什麼contains前後要加底線。
#a={('192.168.1.200', 21200): "socket_name:12345686"} # Replace <socket_name:12345686> with a string
#print(a.keys())
#print(str(a.keys()).__contains__('192.168.1.200'))
def handle_client(client_socket, client_address): #client_address 是新聯上的；clients是既有列表
    message_buffer=''
    message_part1=''
# 對新連入的客戶端。發送指令 '9' 要求回報身分編號
    #if extising_client==False:
    while True:
        try:
            #print('handle_clients')
            message = client_socket.recv(1024).decode()# 接收來自客戶端的訊息
            message.strip()
            #print('message', message)
            if not message:
                break# 若無訊息則斷開連線；此點會不會就是頻繁斷線的問題所在？
            message_buffer=message_buffer+message #把新傳來的字串加上去
            message_split=message_buffer.index('LuLu')+6            #接下來要分字串
            message_part1=message_buffer[:message_split]
            message_buffer=message_buffer[message_split:]
            #print(message_part1,message_buffer)
            
            message_list = message_part1.split(",") #將傳入字串，以逗點分成list
            #print('message_list',message_list)
            if message_list[0] == "R": #R字頭表回報身分編號
                message_R(message_list,client_address)                
            elif message_list[0] == "A"  and 'LuLu' in message_list[-1]:  # 確認
                message_A(message_list)
            message_buffer=''  

        except (socket.timeout, socket.error) as e:
            print(f"客戶端 {client_address} 回應超時")
            client_socket.close()            
        # 嘗試清理並重新連接
            with lock:
                clients.pop(client_address, None)
            return
        #finally:
        #    client_socket.close()
        #    print(f"客戶端 {client_address} 連線關閉")
        #except:
        #    print(f"[斷線] {client_address} 已中斷連線")
        #    del clients[client_address]
        #    client_socket.close()
        #    time.sleep(0.1)
        #    break
#-2-2-1-----------------------------------------------------
def message_R(message_list,client_address):
    print(message_list[-1],'已連線')
    global pt_info_data
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
    #print(clients)
    #print(connected_clients)

#-2-2-2-----------------------------------------------------
def message_A(message_list):
    message_list.pop(0)  #去掉第一個（識別字元A）
    new_name =message_list[-1] #表示這資料是從哪個客戶端來的
    global data
    #print('new_name',new_name)
    raw_wt_list=list(map(int,message_list[1:-2]))#去頭尾
    new_weight=None
    if len(raw_wt_list)>0:
        raw_wt_list=discard_outlier(raw_wt_list)
    if len(raw_wt_list)>0:
        if np.max(raw_wt_list) - np.min(raw_wt_list) <= 5: #來自02版，如果收到的資料變化不超過5，直接取平均；但這會不會是造成現行版本數字有些微波動的主因？是否直接取中位數就好？
            new_weight = round(np.mean(raw_wt_list))
        else:                                               #不然就取中位數
            new_weight = round(statistics.median(raw_wt_list))
    else:
        new_weight=-9999 #此為異常數值
    found = False
    for i, entry in enumerate(data):
        if entry['name'] == new_name: #data字典中的name就是例如LuLu01等的ID
            data[i]['time'].append(time.strftime('%Y-%m-%d %H:%M'))
            if new_weight==-9999 and len(data[i]['weight'])>0: #表示有異常數值出現，不取                
                new_weight=data[i]['weight'][-1] #沿用上一個數字
            elif new_weight==-9999 and len(data[i]['weight'])==0:
                new_weight=0
            data[i]['weight'].append(new_weight)
            found = True
            break
    if not found:
        data.append({'name': new_name, 'time': [time.strftime('%Y-%m-%d %H:%M')], 'weight': [new_weight]})#就算等於離線，還是會在這邊重建一個新的資料
        #break
    #print(data)

def discard_outlier(wt_list): #假如信任秤，應該也可以取眾數就好
    for i in range(0,len(wt_list)-1):
        if wt_list[i] > 1000 or wt_list[i]<-1000:
            del wt_list[i]
    return wt_list

    #wt_array = np.array(wt_list) #轉換為array
    #mean = np.mean(wt_array)
    #std_dev = np.std(wt_array)
    #outlier_wt = wt_array[(wt_array >= mean - 0.5*std_dev) & (wt_array <= mean + 0.5*std_dev)] #上下限為0.5個標準差；留下在此範圍內的元素
    #return outlier_wt.tolist()

#--------------------------------------------主畫面-----------------------------------------------#



# 初始化主畫面
root = tk.Tk()
root.title("OLuLu 0.70")
root.geometry("1024x768")

# 左半畫面，顯示詳細資訊區
left_frame = tk.Frame(root, width=768, height=768, bg="white")
left_frame.pack(side="left", fill="both", expand=1)

# 添加 Canvas 畫布
canvas = tk.Canvas(left_frame, width=768, height=600, bg="white")
canvas.grid(column=0,row=0,columnspan=3,padx=20,pady=0)

# 載入初始圖片
try:
    init_image = Image.open("Copyright-1.png")  # 替換為你的初始圖片路徑
    init_image_tk = ImageTk.PhotoImage(init_image)
    canvas.create_image(268, 105, image=init_image_tk, anchor="nw")
except Exception as e:
    print(f"載入初始圖片時發生錯誤：{e}")
    
#按鈕
switch_button = tk.Button(left_frame, text="切換1或8小時資料", command=toggle_switch, font=("Arial", 12))
#switch_button = tk.Button(left_frame, text="OK",  font=("Arial", 12))
switch_button.grid(column=0,row=1)
logout_client_button = tk.Button(left_frame, text="登出病人", command=logout_client, font=("Arial", 12))
#logout_client_button = tk.Button(left_frame, text="登出", font=("Arial", 12))
logout_client_button.grid(column=2,row=1)
# 顯示點選的資料
dataDisplay_text = tk.Label(left_frame, text="點選右方按鈕註冊病人", bg="white", font=("Arial", 18))
dataDisplay_text.grid(column=1,row=1)


# 右半畫面，病人床位選擇區
right_frame = tk.Frame(root, width=256, height=768)
right_frame.pack(side="right", fill="both", expand=0)

# 建立1x9的按鈕矩陣
for h in pt_info_data:
    btn = tk.Button(right_frame,text=f"{pt_info_data[h]['Bed']}\n{pt_info_data[h]['client_IP']}\n{pt_info_data[h]['pt_number']}", command=lambda num=h: display_info(num)) #指定點選的數字
    btn.grid(row=h, column=0, pady=10)

# 啟動伺服器
lock = threading.Lock()
threading.Thread(target=start_server, daemon=True).start()
root.mainloop()
# 綁定關閉事件
root.protocol("WM_DELETE_WINDOW", on_closing)
