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
formatted_time_list = []
x=[]
y=[]


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

# 左半畫面，顯示詳細資訊區
left_frame = tk.Frame(root, width=768, height=768, bg="white")
left_frame.pack(side="left", fill="both", expand=1)

# 添加 Canvas 畫布
canvas = tk.Canvas(left_frame, width=640, height=600, bg="white")
canvas.pack(padx=10, pady=10)
#按鈕
displayok_button = tk.Button(left_frame, text="OK", command=return_to_main, font=("Arial", 12))
displayok_button.pack(side="left", padx=20, pady=650)
logout_client_button = tk.Button(left_frame, text="登出", command=logout_client, font=("Arial", 12))
logout_client_button.pack(side="right", padx=20, pady=650)
# 顯示點選的資料
dataDisplay_text = tk.Label(left_frame, text="Click a button to see details", bg="white", font=("Arial", 12))
dataDisplay_text.pack(pady=610)

# 右半畫面，病人床位選擇區
right_frame = tk.Frame(root, width=256, height=768)
right_frame.pack(side="right", fill="both", expand=0)


# 位於右半畫面的選取床位主控面板
# pt_info_data：介面工作用基本字典，如連線則於cleint_name顯示client_name，pt_number為病歷號，client_name為各個客戶端的名字，需與各客戶端的arduino code對應.
# 1: {"Bed": "Bed01", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu01'},

def display_info(button_number):
    global current_button_number
    y=[]
    try:
        current_button_number = button_number
        info_on_button = pt_info_data[button_number]["pt_number"] #設定為所選取的button
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

           
    #確定時間有搭上。計畫是要拿-60個資料，但可能會有疏漏。所以應該先計算data是否超過60項。
    #再來用time delta並以迴圈，以每分鐘為單位，建立串列，用來跟time[j]比較
    # 取得當前時間，格式化為指定格式
        start_time = time.strftime('%Y-%m-%d %H:%M')
    # 建立時間串列，往前推 60 分鐘
        time_list = [datetime.strptime(start_time, '%Y-%m-%d %H:%M') - timedelta(minutes=i) for i in range(60)]
    # 格式化時間串列
        formatted_time_list = [time.strftime('%Y-%m-%d %H:%M') for time in time_list]
        for j in range (-60,-1,1):
            try:
                if formatted_time_list[j] in data[button_number]['time']: #在資料中找到相對應時間
                    index=data[button_number]['time'].index(formatted_time_list[j])
                    y.append(data[button_number]['weight'][index]) #y=該時間的重量
                else:
                    y.append(0)
            except IndexError: #超出範圍
                y.append(0)
#底下這個是左半的文字
        dataDisplay_text.config(text=f"Button {button_number}\n Bed: {bed}\n client_IP: {client_IP}\n pt_number: {info_on_button}\n Client ID: {client_id}")#這是主要有問題的地方，本來是可以不要用的，因為要直接顯示長條圖

# 清除舊的長條圖
        canvas.delete("all")
        if np.max(y) >500:
            scale=2
            color_code='blue'
        else:
            scale=1
            color_code='orange'
            
    # X 軸和 Y 軸
        canvas.create_line(30, 525, 30, 0, fill="black", width=1)  # X 軸
        canvas.create_line(30, 525, 635, 525, fill="black", width=1)  # Y 軸
    # X 軸刻度
        for i in range(0, 61, 10):
            canvas.create_line(35 + i * 10, 525, 35 + i * 10, 530, fill="black")
            canvas.create_text(35 + i * 10, 530, text=i - 60, anchor=tk.N)
    # Y 軸刻度
        for j in range(0, 5):
            canvas.create_line(25, j * 100 + 25, 30, j * 100 + 25, fill="black")
            canvas.create_text(25, j * 100 + 25, text=(5 - j) * 100*scale, anchor=tk.E)
    # X 軸和 Y 軸的標籤
        canvas.create_text(615, 530, text="時間", anchor=tk.N)
        canvas.create_text(15, 45, text="公克", anchor=tk.S)
    # 繪製長條圖
        for i in range(len(y)):
            x0 = 635- i * 8
            y0 = 525
            x1 = 635- i * 8
            y1 = round(525 - y[i]/scale)
            canvas.create_line(x0, y0, x1, y1, width=8, fill=color_code)
        
    except Exception as e:
        print(f"發生錯誤：{e}")
#還沒有做到的：顯示8小時的資料
                         
    

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
    #print('scan clients')
    global current_button_number
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
        if current_time.tm_sec == 25: # 每分鐘的25
            display_info(current_button_number)
#有在思考加進斷線的客戶端就顯示為離線或是按鈕換顏色，連上了又換回正常顏色
# 如果沒有傳入資料，目前設定以前一分鐘資料補上
        if time.localtime(time.time()).tm_sec == 29 and len(data)>0 :#遍歷字典裡各病人的time，如無符合目前時間的資料，就append.list[-1]
            add_missing_data()
            #print('29秒',data)
                
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 35 and not saved:
            for j in pt_info_data: #所有的客戶
                if pt_info_data[j]['pt_number'] !='請輸入病歷號': #有連線的用戶
                    file_name=pt_info_data[j]['pt_number']+'.csv' #用戶的病歷號當檔名
                    #print(data)
                    saving_data(data[j]['time'][-10:], data[j]['weight'][-10:], file_name) #把最後10項傳過去，但這要注意如果目前data未滿十項呢？
                    #data[j]['time']=[] #先用笨一點的方法，就是每十分鐘存檔一次並清空，避免data膨脹
                    #data[j]['weight']=[] #這種方法不一定比較差，是因為下面內存10分鐘的方法，還是得開檔剩下50分鐘的資料除非我在電腦裡存60分的資料。
                    
                    #複雜的方法，保留最近十分鐘的資料，把先前（10-20分鐘）的資料送去存。但這在最後登出病人時要記得把剩下的資料存進v去
                    #這種方法幫忙不大，除非我在電腦記憶體裡存60筆，但這又會碰到就是希望10分就存檔一次以減少意外發生造成的影響。
#折衷方式：不管如何，10分鐘存檔一次。為了減少硬碟讀取，將data裡存放每個病人60分鐘的資料，但每十分鐘就將最新的資料抓去存檔。並在每小時01分將data擷取最新60分鐘資料留存在記憶體內
            saved= True #所有的都已經跑過了，saved設為True，以免在同一秒內又再來一次
        elif current_time.tm_sec == 36:
            saved = False #重設是否已存檔開關
        time.sleep(0.1) #休息一下1

# 1-1. 存檔函數。目前暫時不打算存入原始資料list，除非實際使用後常常出現怪異數值
def saving_data(saving_time, saving_weight, file_name):
    try:
        print('saving data', saving_time)
        print('saving_weight', saving_weight)
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



#-------------------------------------------------------
# 2. 處理個別客戶端；下面是處理socket中的東西的範例－－雖然我不懂為什麼contains前後要加底線。
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
            print(message_part1,message_buffer)
            

            message_list = message_part1.split(",") #將傳入字串，以逗點分成list
            print('message_list',message_list)
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
        #except:
        #    print(f"[斷線] {client_address} 已中斷連線")
        #    del clients[client_address]
        #    client_socket.close()
        #    time.sleep(0.1)
        #    break
#-------------------------------------------------------
def message_R(message_list,client_address):
    print(message_list[-1],'已連線')
    #client_IP=client_address[0]
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


def message_A(message_list):
    message_list.pop(0)  #去掉第一個（識別字元A）
    new_name =message_list[-1] #表示這資料是從哪個客戶端來的
    global data
    #print('new_name',new_name)
    raw_wt_list=list(map(int,message_list[1:-2]))#去頭尾
    new_weight=None
    if len(raw_wt_list)>0:
        if np.max(raw_wt_list) - np.min(raw_wt_list) <= 5: #來自02版，如果收到的資料變化不超過5，直接取平均；但這會不會是造成現行版本數字有些微波動的主因？是否直接取中位數就好？
            new_weight = round(np.mean(raw_wt_list))
        else:                                               #不然就取中位數
            new_weight = round(statistics.median(raw_wt_list))
                #with lock:        
    found = False
    for i, entry in enumerate(data):
        if entry['name'] == new_name: #data字典中的name就是例如LuLu01等的ID
            data[i]['time'].append(time.strftime('%Y-%m-%d %H:%M'))
            data[i]['weight'].append(new_weight)
            found = True
            break
    if not found:
        data.append({'name': new_name, 'time': [time.strftime('%Y-%m-%d %H:%M')], 'weight': [new_weight]})#就算等於離線，還是會在這邊重建一個新的資料
        #break
    print(data)


def add_missing_data():
    for j in pt_info_data: #檢查病人名單
        if pt_info_data[j]['client_IP'] !="離線":#檢查每一位帳面上有連線的病人
            for k, entry in enumerate(data): #檢查每一位病人的個別資料
                if data[k]['time'][-1] != (time.strftime('%Y-%m-%d %H:%M')): #表示為帳面上已有連線的用戶，其time欄位的最後一個是否等於目前時間，如否～
                    data[k]['time'].append(time.strftime('%Y-%m-%d %H:%M')) #加上目前時間
                    data[k]['weight'].append(data[k]['weight'][-1])  #加上既有串列裡最後一個
                            
# ----------------------------主畫面------------------------------------------


# 建立1x9的按鈕矩陣
for h in pt_info_data:
    btn = ttk.Button(right_frame, text=f"{pt_info_data[h]['Bed']}\n{pt_info_data[h]['client_IP']}\n{pt_info_data[h]['pt_number']}", command=lambda num=h: display_info(num)) #指定點選的數字
    btn.grid(row=h, column=0, pady=10)

# 啟動伺服器
lock = threading.Lock()
threading.Thread(target=start_server, daemon=True).start()

root.mainloop()
