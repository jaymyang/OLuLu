#按登出時的error messaga:
#Exception in thread Thread-3 (handle_client):
#Traceback (most recent call last):
#  File "D:\Lib\threading.py", line 1052, in _bootstrap_inner
#    self.run()
#  File "D:\Lib\threading.py", line 989, in run
#    self._target(*self._args, **self._kwargs)
#  File "D:\Olulu_06_96.py", line 547, in handle_client
#    message_A(message_list)
#  File "D:\Olulu_06_96.py", line 609, in message_A
#    if entry['name'] == new_name: #data字典中的name就是例如LuLu01等的ID
#       ~~~~~^^^^^^^^
#TypeError: list indices must be integers or slices, not str
#Exception in thread Thread-2 (scan_clients):
#Traceback (most recent call last):
#  File "D:\Lib\threading.py", line 1052, in _bootstrap_inner
#    self.run()
#  File "D:\Lib\threading.py", line 989, in run
#    self._target(*self._args, **self._kwargs)
#  File "D:\Olulu_06_96.py", line 413, in scan_clients
#    if pt_info_data[j]['client_IP'] !="離線" and len(data[j]['weight']) >0:# 檢查每一位帳面上有連線的病人
#                                                   ~~~~~~~^^^^^^^^^^
#TypeError: list indices must be integers or slices, not str



#現在登出以後已經可以跳回起始畫面。
#問題：
#1.假如按了按鈕，沒有輸入病歷號，不會呈現起始畫面（而是空白畫面）
#2.按了按鈕也輸入病歷號，但是client是離線的，不只不會呈現起始畫面（而是空白畫面），接下來存檔還會出現list index out of range，然後連帶其他的clients也停止收訊。最後關閉程式存檔時也會出現錯誤。


#    如果需要捕捉所有錯誤而不退出程式，可以使用 except Exception as e。
#    務必在 except 塊中加入適當的記錄或處理方式（如 print 或 logging），以便日後檢查問題。
#打算放進去的：
#    except Exception as e:
#        print(f"發生錯誤：{e}")
#以下的finally是針對連線問題的
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
from sklearn.linear_model import LinearRegression #回歸用

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
#避免重複顯示資料，以降低電腦負擔
displayed=False
#測試用來關閉程式的開關
closing=False
#暫存前一個按鈕值暫定為0
previous_selected=0
######以下是主thread 介面######################################################
#不知道為什麼，這個display info跑了8次
def display_info(button_number,displayed):
    global current_button_number

    #global displayed
    y=[]
    one_eight_selection=1
    
    try:
        # 重置先前選取的按鈕顏色
        if current_button_number is not None:
            previous_button = right_frame.winfo_children()[current_button_number]
            previous_button.config(style="TButton")  # 恢復普通樣式

        previous_selected = current_button_number #將原先的選擇值暫存為previous_selected
        current_button_number = button_number #將原先的選擇值更新為button_number
        # 設定目前選取的按鈕變色
        selected_button = right_frame.winfo_children()[button_number]
        selected_button.config(style="Selected.TButton")
        #設定為所選取的button
        info_on_button = pt_info_data[button_number]["pt_number"]

        if info_on_button == "請輸入病歷號":
            patient_id = simpledialog.askstring("輸入病歷號", f"請輸入 {pt_info_data[button_number]['Bed']} 的病歷號:")
            if patient_id: #輸入完成
                pt_info_data[button_number]["pt_number"] = patient_id#將字典的info設為所輸入的病歷號
                update_button_text(button_number)#更新按鈕
  
            else: #假如沒有輸入，將selected設回灰色，將先前的設回黃色
                selected_button = right_frame.winfo_children()[current_button_number]
                selected_button.config(style="TButton")  # 恢復普通樣式                
                current_button_number=previous_selected #假如沒有輸入病歷號而是按了cancel，就把current_button_number設回先前的值
                button_number=current_button_number
                previous_button = right_frame.winfo_children()[current_button_number]
                previous_button.config(style="Selected.TButton")  # 恢復普通樣式              
                pass
        #從pt_info_data中抓取資料
        bed = pt_info_data[button_number]["Bed"]
        client_IP = pt_info_data[button_number]["client_IP"]
        info_on_button = pt_info_data[button_number]["pt_number"]
        client_id = pt_info_data[button_number]["client_name"]

        dataDisplay_text.config(text=f"Button {button_number}\n Bed: {bed}\n client_IP: {client_IP}\n pt_number: {info_on_button}\n Client ID: {client_id}") #顯示選擇之資訊
        if data[button_number]["weight"] !=[]:
            y_data_points=one_eight_switch(one_eight_selection)[0] #切換1/8小時與準備繪圖資料（預設toggle值為1）
            bargraph(one_eight_selection,y_data_points) #以回傳資料畫圖
        else:
            pass

        #以下估計回歸
        trend_points=one_eight_switch(one_eight_selection)[1] #計算回歸用資料
        if len(trend_points)>20: #超過20個非0資料點再計算
            trend=[]
            trend=trend_prediction(trend_points) #算回歸係數
            dataDisplay_text.config(
            text=f"Button {button_number}\n Bed: {bed}\n pt_number: {info_on_button}\n 過去10分鐘重量變化: {trend[0]} \n 過去十分鐘趨勢: {trend[1]}"
        )
        displayed=True
        #previous_selected=current_button_number #假如按了cancel，因為已經是先前的值了，沒差；假如能順利跑到這，那就更新為新
        return displayed
    except Exception as e:
        print(f"line 129發生錯誤：{e}")

#以下製造繪圖所用的資料點
def one_eight_switch(switch_1_8): #第一步：準備要畫圖的資料點
    global current_button_number
    y = []  # 清空舊資料
    trend_y=[] #用來計算回歸的
    start_time = datetime.now()
    
    #製造出顯示一小時或八小時資料時所需要的時間點陣列
    if switch_1_8==1:
        formatted_time_list = [(start_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') for i in range(60)]        
    else:
        formatted_time_list = [(start_time - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') for i in range(0,480,2)]

    # 讀取記憶體中的資料。如果是暫時登出又再連上，可在每分鐘如發現顯示陣列內資料個數不滿60筆時，就嘗試讀檔來補足顯示用資料。這部份現在還沒做好。要這樣做的話，可以把讀取資料的部分寫成函式）
    if current_button_number is not None: #當然，要有選擇到某位病人才行
        try:
            for time_point in formatted_time_list:
                if time_point in data[current_button_number]['time']:
                    index = data[current_button_number]['time'].index(time_point)
                    y.append(data[current_button_number]['weight'][index])
                    trend_y.append(data[current_button_number]['weight'][index])
                else:
                    y.append(0)                
        except Exception as e:
            canvas.delete("all")
            canvas.create_image(268, 105, image=init_image_tk, anchor="nw") #理論上在這裡應該會先清空然後顯示起始畫面
            y=one_eight_switch(switch_1_8)
            print(f"記憶體內的資料處理錯誤：{e}")
        if len(data[current_button_number]['time'])<60:
            getfiledata(y,formatted_time_list)
        else:
            pass           

    # 如果是 8 小時模式，讀取檔案資料並補上在前面被當成0的部分
    if switch_1_8 == 8:
        getfiledata(y,formatted_time_list)
    return y,trend_y

        
def getfiledata(y,formatted_time_list):
    global current_button_number
    try:
        file_name = f"{pt_info_data[current_button_number]['pt_number']}.csv"
        with open(file_name, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            csv_data = {row[0]: float(row[1]) for row in reader}  # 時間:重量
        for i, time_point in enumerate(formatted_time_list):
            # 只補上 y[i] == 0（記憶體內無資料）
            if y[i] == 0 and time_point in csv_data:
                y[i] = csv_data[time_point]
    except FileNotFoundError:
        print(f"檔案 {file_name} 不存在，無法讀取歷史資料。")
    except Exception as e:
        print(f"讀取檔案錯誤：{e}")
    return y


        
# 按鈕的事件處理
def toggle_switch():
    global switch_1_8
    # 切換 switch_1_8 的值
    switch_1_8 = 8 if switch_1_8 == 1 else 1
    print(f"切換到 {switch_1_8} 小時模式")
    try:
        # 更新資料並繪製圖表
        y_data_points=one_eight_switch(switch_1_8)[0]  # 更新 y
        #打算在切換成8小時模式時，不計算回歸
        bargraph(switch_1_8,y_data_points)         # 繪製圖表
    except Exception as e:
        print(f"切換錯誤：{e}")
        

def bargraph(switch_1_8,y):
    if not y:
        print("目前無資料可繪製圖形。") #這是為了曾經出現過的狀況，在shell關閉又開啟數次後畫不出圖來，經查仍在接收資料，但y是空的。先這樣試試看。
        #canvas.delete("all")
        canvas.create_image(268, 105, image=init_image_tk, anchor="nw")#理論上在這裡應該會先清空然後顯示起始畫面
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
        print(f"line239繪製長條圖時發生錯誤：{e}")



# 更新按鈕所顯示內容。本來打算依照是否連線改變色，現在覺得只要更動client_IP就可以
# 有輸入病歷號時，要更動button中的病歷號。連線時顯示client_IP，離線則顯示離線
# 更新按鈕文字
def update_button_text(button_number):
    button = right_frame.winfo_children()[button_number]
    bed_info = pt_info_data[button_number]
    button.config(text=f"{bed_info['Bed']} \n {bed_info['client_IP']} \n {bed_info['pt_number']}")

    
# 回到主畫面
def return_to_main():
    dataDisplay_text.config(text="點選床位按鈕以查看資料")

# 客戶端登出
def logout_client():
    #    0: {"Bed": "Bed01", "client_IP": "離線", "pt_number": "請輸入病歷號", 'client_name': 'LuLu01'},
    #button = ttk.Button(
    #    right_frame,
    #    text=f"{info['Bed']} \n {info['client_IP']} \n {info['pt_number']}",
    #    command=lambda i=i: display_info(i),
    #    style="TButton"
    global pt_info_data
    if current_button_number is not None:
        bed = pt_info_data[current_button_number]["Bed"]
        info = pt_info_data[current_button_number]["pt_number"]
        response = messagebox.askyesno("確認登出", f"是否確定登出？\n{bed}\n{info}")
        
        if response:
            logout_file_name=pt_info_data[current_button_number]['pt_number']+'.csv' #用戶的病歷號當檔名
            
            pt_info_data[current_button_number]["pt_number"] = "請輸入病歷號"
            #pt_info_data[current_button_number]["client_name"] = "登出" #這邊的用意是只有登出病人，並非要一併斷線。但問題是收進來的資料還是被存進data－－理論上登出後，就算繼續發送起始訊號，也不應該將回報資料放進data
            #應執行存檔，存檔完成清空data中本項
            #print(current_button_number)
            #print(pt_info_data[current_button_number])
            #print(data[current_button_number])
            if data!=[]:
                if data[current_button_number] !=[]:
                    remained_item_n=-(time.localtime(time.time()).tm_min % 10)
                    saving_data(data[current_button_number]['time'][remained_item_n:], data[current_button_number]['weight'][remained_item_n:], logout_file_name) #傳過去
                    data[current_button_number]=[]
                else:
                    pass
        
            update_button_text(current_button_number)
            print('已登出並存檔',data)
            canvas.delete("all")
            canvas.create_image(268, 105, image=init_image_tk, anchor="nw")
            return_to_main()
    else:
        messagebox.showinfo("注意", "請先選擇病床再登出")

def on_closing():
    response = messagebox.askyesno("確認退出", "是否存檔並退出？")
    global closing
    if response:  # 如果選擇是
        remained_item_n=-(time.localtime(time.time()).tm_min % 10)
        try:
            # 執行存檔邏輯
            for j in pt_info_data:
                if pt_info_data[j]['pt_number'] != '請輸入病歷號':
                    file_name = f"{pt_info_data[j]['pt_number']}.csv"
                    saving_data(data[j]['time'][remained_item_n:], data[j]['weight'][remained_item_n:], file_name)
            print("所有資料已存檔，感謝您的使用。")
            closing=True
        except Exception as e:
            messagebox.showerror("line309存檔錯誤", f"存檔時發生錯誤：{e}")
        finally:
            if root.winfo_exists():  # 確保 root 存在
                root.destroy()  # 確保程式退出
    else:
        print("取消關閉視窗")
        
#----------------------尚未整合進去的局部估計與趨勢預測-----------------------------------------------------
# 單次的異常值\丟棄功能，在021版已有發展，但現在尚未納入。Function to calculate weight changes#需要偵測重量突減以及異常大量
# 本版改的是只要一分鐘相差超過20公克，就視為需要重算
#注意變數名稱
def trend_prediction(weight_FLUID): #使用trend_points
    weight_sum=0
    trend=''
    start_element=-10#先計算重量變化，每十分鐘從-10開始拿來算。
    if weight_FLUID !=[]:
        weight_max=weight_FLUID[start_element] #先將最大值設成起始值
        weight_min=weight_FLUID[start_element] #先將最小值設成起始值
        weight_recent=weight_FLUID[start_element:] #工作用串列
        small_volume=np.max(weight_recent)-np.min(weight_recent) #這邊先計算是否為small volume
        print(weight_recent,small_volume)

        for i in range(1,len(weight_recent)-1,1): 
            if abs(weight_recent[i]-weight_recent[i-1])<20: #假設相差小於20克是合理的
                if weight_recent[i]>weight_max: 
                    weight_max=weight_recent[i] #假如目前這個比較大，就把weight_max數值設為目前這個
                elif weight_recent[i]<weight_max: 
                    weight_min=weight_recent[i] #假如目前這個比較小，就把weight_min數值設為目前這個
                else:
                    pass
            else:
                weight_sum=weight_sum+weight_max-weight_min #本階段結束，將本階段重量差加上原重量差，視為尿量
                weight_max=weight_recent[i] #重設
                weight_min=weight_recent[i] #重設
        weight_sum=weight_sum+weight_max-weight_min 
        if small_volume < 5:#這裡是預設在一個尿量波動很小的範圍的時候，直接用最大值減最小值來估計就好。不管每5分鐘或每小時，都用10gm
            weight_Sum=small_volume
        trend_recent=basic_regression(weight_FLUID[-10:])
        trend_ago=basic_regression(weight_FLUID[-20:-10])
        if trend_recent/trend_ago < 1:
            trend='漸減'
        else:
            trend='增加或穩定'
    
    print(weight_sum,trend)
    return str(weight_sum), trend#0是重量，1是趨勢
    
# Function to perform basic regression
def basic_regression(basic_regression_wt):#呼叫時傳來的數據放在basic_regression_wt，且已確定每次都傳來10個
    y = basic_regression_wt
    x = np.arange(1, len(basic_regression_wt) + 1).reshape((-1, 1))
    model = LinearRegression().fit(x, y)
    return model.coef_



######以下是副thread 2, 控時######################################################
#由於要持續處理連線與資料交換，必須跟介面寫在不同的thread。但是pt_info_data?
#有在思考加進斷線的客戶端就顯示為離線或是按鈕換顏色，連上了又換回正常顏色

# 2-1.資料處理的主控程式。定期向客戶端發送訊息收集資料。
def scan_clients():
    #print('scan clients')
    global current_button_number
    global data
    #global displayed
    global closing
    saved = False
    min_for_saving = [0, 10, 20, 30, 40, 50]
    while True:
        displayed=False
        current_time = time.localtime(time.time())
        if closing==True:
            break
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
        if time.localtime(time.time()).tm_sec == 25 and len(data)>0 :#遍歷字典裡各病人的time，如無符合目前時間的資料，就append.既有串列裡最後一個
            for j in range(len(pt_info_data)): #檢查病人名單
                if pt_info_data[j]['client_IP'] !="離線" and len(data[j]['weight']) >0:# 檢查每一位帳面上有連線的病人
                    #for k, entry in enumerate(data): #檢查每一位病人的個別資料
                    if data[j]['time'][-1] != (time.strftime('%Y-%m-%d %H:%M')): #表示為帳面上已有連線的用戶，其time欄位的最後一個是否等於目前時間，如否～
                        data[j]['time'].append(time.strftime('%Y-%m-%d %H:%M')) #加上目前時間
                        data[j]['weight'].append(data[j]['weight'][-1])  #加上既有串列裡最後一個
                    else:
                        pass
                else:
                    pass                

         # 每分鐘的31秒更新顯示；這個要不要寫在主線？
        if current_time.tm_sec == 31 and len(data) >0:
            if not displayed:
                displayed=display_info(current_button_number,displayed)
            else:
                time.sleep (0.1)
                pass
        elif current_time.tm_sec == 32:
            displayed=False #重設回尚未顯示

    # 每10分鐘的35秒存檔，36秒重設存檔開關             
        if current_time.tm_min in min_for_saving and current_time.tm_sec == 35 and not saved:
            for j in pt_info_data: #所有的客戶
                if pt_info_data[j]['pt_number'] !='請輸入病歷號' and pt_info_data[j]['client_IP'] !='離線': #有連線的用戶；這邊沒有考慮到有key病歷號但是離線的
                    file_name=pt_info_data[j]['pt_number']+'.csv' #用戶的病歷號當檔名
                    if data!=[]:
                        saving_data(data[j]['time'][-10:], data[j]['weight'][-10:], file_name) #把最後10項傳過去，但這要注意如果目前data未滿十項呢？
                    else:
                        pass
                else:
                    pass
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
    global closing

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("192.168.1.101", 8080))
    server.listen(8)
    threading.Thread(target=scan_clients, daemon=True).start()# 啟動定時發訊息
    # 持續接受新客戶端連線
    while True:
        if closing==True:
            break
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
    global closing
# 對新連入的客戶端。發送指令 '9' 要求回報身分編號
    #if extising_client==False:
    while True:
        if closing==True:
            break
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
#-2-2-1-----------------------------------------------------缺斷線功能
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
        print('非合格客戶端:',client_address[0])  ##應該要在這邊加入斷線
        client_socket.close()
    #print(clients)
    #print(connected_clients)

#-2-2-2-----------------------------------------------------
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
        if np.max(raw_wt_list) - np.min(raw_wt_list) <= 5: #來自02版，如果收到的資料變化不超過5，直接取平均；但這會不會是造成現行版本數字有些微波動的主因？是否直接取中位數就好？
            new_weight = round(np.mean(raw_wt_list))
        else:                                               #不然就取中位數
            new_weight = round(statistics.median(raw_wt_list))
    else: #全清空#此為異常數值
        new_weight=-9999 
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


#--------------------------------------------主畫面-----------------------------------------------#



# 初始化主畫面
root = tk.Tk()
root.title("OLuLu 0.69")
root.geometry("1024x768")

# 定義樣式
style = ttk.Style()
style.theme_use('alt')
style.configure("TButton", font=("Arial", 12), padding=5)
style.configure("Selected.TButton", background="orange", foreground="white")
#style.map("Selected.TButton", background=[('active','red')])
style.configure("TLabel", font=("Arial", 12))

# 左半畫面，顯示詳細資訊區
#left_frame = tk.Frame(root, width=768, height=768, bg="white")
#left_frame.pack(side="left", fill="both", expand=1)

# 左區畫面，顯示資料區
left_frame = ttk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
# 右側畫面，選擇區
right_frame = ttk.Frame(root)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
# 宣告Canvas 
canvas = tk.Canvas(left_frame, width=768, height=600, bg="white")
canvas.grid(column=0,row=0,columnspan=3,padx=20,pady=0)       

# 載入初始圖片
try:
    init_image = Image.open("Copyright-1.png")  #指定圖片
    init_image_tk = ImageTk.PhotoImage(init_image)
    canvas.create_image(268, 105, image=init_image_tk, anchor="nw")
except Exception as e:
    print(f"載入初始圖片時發生錯誤：{e}")
# 顯示點選的資料
dataDisplay_text = tk.Label(left_frame, text="點選右方按鈕註冊病人", bg="white", font=("Arial", 12))
dataDisplay_text.grid(column=1,row=1)
    
#按鈕
switch_button = tk.Button(left_frame, text="切換1或8小時資料", command=toggle_switch, font=("Arial", 12))
switch_button.grid(column=0,row=1)
logout_client_button = tk.Button(left_frame, text="登出病人", command=logout_client, font=("Arial", 12))
logout_client_button.grid(column=2,row=1)
# 繪製床位按鈕
for i, info in pt_info_data.items():
    button = ttk.Button(
        right_frame,
        text=f"{info['Bed']} \n {info['client_IP']} \n {info['pt_number']}",
        command=lambda i=i: display_info(i,False),
        style="TButton"
    )
    button.pack(fill=tk.X,pady=2)


# 啟動伺服器
lock = threading.Lock()
threading.Thread(target=start_server, daemon=True).start()
# 綁定關閉事件
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()

