#預計在字典中，將以name串列存放病歷號或床號，time串列存放時間串列（每個病人一個串列），weight串列存放重量串列（每個病人一個串列）
#是不是可以把字典改成串列？
import socket
import threading
import time
import numpy as np #數學運算用

clients = {}# 客戶端字典，儲存客戶端的地址與連線狀態
data={'name':[],'time':[],'weight':[]}# 資料字典


# 設置伺服器
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('192.168.1.101', 8080))
server.listen(5)
server.settimeout(1)

client_ip=['192.168.1.66','192.168.1.202','192.168.1.203']
def discard_outlier(wt_list): #假如信任秤，應該也可以取眾數就好  
    wt_array = np.array(wt_list) #轉換為array
    mean = np.mean(wt_array)
    std_dev = np.std(wt_array)
    outlier_wt = wt_array[(wt_array >= mean - 0.5*std_dev) & (wt_array <= mean + 0.5*std_dev)] #上下限為0.5個標準差；留下在此範圍內的元素
    return outlier_wt.tolist()

def handle_client(client_socket, client_address): #接收
    
    # 客戶端加入clients字典
    clients[client_address] = client_socket
    print(f"[連線成功] {client_address} 連接至伺服器")
    
    while True:
        try:
            # 嘗試接收來自客戶端的訊息
            message = client_socket.recv(1024).decode()
            message_list=message.split(",")

            if message_list[0]=="A" and 'LuLu' in message_list[-1]: #確認是完整的串列
                print(message_list)
                message_list.pop(0)
                new_name=message_list[-1]
                message_list.pop(-1)
                #print(message_list)
                raw_wt_list=list(map(int,message_list))
                #print("message_list",message_list)
                #print("raw_wt_list",raw_wt_list)
                if np.max(raw_wt_list)-np.min(raw_wt_list) <= 5:
                    new_weight=round(np.mean(raw_wt_list))#賦值，10秒之中取得的數字變異不大，取平均
                else:
                    new_weight=round(statistics.median(raw_wt_list))#賦值，10秒之中取得的數字變異較大，取中位數

                if new_name in data['name']:
                    #print(new_name) #追蹤各連線
                    data['time'][data['name'].index(new_name)].append(time.time())
                    data['weight'][data['name'].index(new_name)].append(new_weight)
                    print("data",data)
                else:
                    #print(new_name) #
                    data['name'].append(new_name)
                    data['time'].append(time.time())
                    data['weight'].append([new_weight])
                    print("data",data)
                        

            if not message:
                break
            message =[]
            message_list=[]
            new_name=""
        except:
            break

    # 當客戶端中斷連線時，移除客戶端
    #print(f"[連線中斷] {client_address} 斷開連線")
    #del clients[client_address]
    #client_socket.close()
    
#def send_message():#目前這個沒有在動
#    send_port=8080
#    while True:
#        current_time = time.localtime(time.time())
#        # 在每分鐘的59秒執行掃描
#        if current_time.tm_sec == 59:
#            print('client_ip',client_ip)
#            for send_ip in client_ip:
#                try:
#                    # 建立一個 socket 物件
#                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as send:
#                        # 嘗試連接到指定的 IP 和端口
#                        send.connect((send_ip, send_port))
#                        # 傳送訊息
#                        send.sendall("B".encode())
#                        print("Message sent successfully!")
#                except (ConnectionRefusedError, TimeoutError, socket.error):
#                    # 如果無法連接或出現其他錯誤，則略過
#                    print(f"{send_ip}未連線") #
#                    break
#                time.sleep(0.5)
#        else:
#            pass

# 循環掃描客戶端、但現在實際上在負責與clien溝通的是這個thread。
def scan_clients():
    while True:
        current_time = time.localtime(time.time())
        # 在每分鐘的59秒執行掃描
        if current_time.tm_sec == 59:
            print("[掃描中] 掃描所有連線的客戶端...")
            active_clients = list(clients.keys())
            print('active_clients',active_clients)
            for client_address in active_clients:
                client_socket = clients[client_address]
                try:
                    # 檢查客戶端是否仍然連線
                    client_socket.send("1".encode())
                    print(f"[發送訊息] 向 {client_address} 發送 '1'")
                except:
                    print(f"[移除] {client_address} 已中斷連線")
                    del clients[client_address]
        time.sleep(1)

# 接受客戶端連線
def accept_connections():
    while True:
        try:
            client_socket, client_address = server.accept()
            client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_handler.start()
        except socket.timeout:
            continue

# 啟動接收與掃描的執行緒
threading.Thread(target=accept_connections).start()
#threading.Thread(target=send_message).start()
threading.Thread(target=scan_clients).start()
