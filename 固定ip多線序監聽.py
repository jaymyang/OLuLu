import time
import socket
import threading
import numpy as np
import statistics

# 客戶端字典和數據變量
clients = {}
scanned_clients = {}
data = {'name': [], 'time': [], 'weight': []}

# 處理單個客戶端的函式
def handle_client(client_socket, client_address):
    # 客戶端加入clients字典
    clients[client_address] = client_socket
    print(f"[連線成功] {client_address} 連接至伺服器")
    
    while True:
        try:
            # 接收來自客戶端的訊息
            message = client_socket.recv(1024).decode()
            if not message:
                break  # 若無訊息則斷開連線
            
            message_list = message.split(",")
            print('received message:', message_list) #不知道為什麼會連續收兩個，但是反正有防呆就算了

            if message_list[0] == "A" and 'LuLu' in message_list[-1]:  # 確認是完整的訊息
                message_list.pop(0)
                new_name = message_list.pop(-1)
                raw_wt_list = list(map(int, message_list))
                
                if np.max(raw_wt_list) - np.min(raw_wt_list) <= 5:
                    new_weight = round(np.mean(raw_wt_list))
                else:
                    new_weight = round(statistics.median(raw_wt_list))

                if new_name in data['name']:
                    idx = data['name'].index(new_name)
                    data['time'][idx].append(time.time())
                    data['weight'][idx].append(new_weight)
                else:
                    data['name'].append(new_name)
                    data['time'].append([time.time()])
                    data['weight'].append([new_weight])

                print("data", data)
                
        except:
            print(f"[斷線] {client_address} 已中斷連線")
            del clients[client_address]
            client_socket.close()
            break

# 定期掃描並向客戶端發送訊息，這個是時控程式
def scan_clients():
    while True:
        current_time = time.localtime(time.time())
        if current_time.tm_sec == 59:  # 每分鐘的59秒執行掃描
            #print("[掃描中] 掃描所有連線的客戶端...")
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
            time.sleep(1)  # 避免連續發送，等一秒
            
# 初始化伺服器並接受客戶端連線，可以視為主程式
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("192.168.1.101", 8080))  
    server.listen()
    print("[伺服器啟動] 等待客戶端連線...")

    # 啟動掃描線程
    threading.Thread(target=scan_clients, daemon=True).start()

    # 持續接受新客戶端連線
    while True:
        client_socket, client_address = server.accept()
        print(f"[連線中] {client_address} 正在連接...")
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

# 啟動伺服器
start_server()
