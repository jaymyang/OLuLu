import socket
import threading
import time

# 客戶端字典，儲存客戶端的地址與連線狀態
clients = {}

# 設置伺服器
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('192.168.1.101', 8080))
server.listen(5)
server.settimeout(1)

client_ip=['192.168.1.201','192.168.1.202','192.168.1.203']

def handle_client(client_socket, client_address):
    # 客戶端加入clients字典
    clients[client_address] = client_socket
    print(f"[連線成功] {client_address} 連接至伺服器")
    
    while True:
        try:
            # 嘗試接收來自客戶端的訊息
            message = client_socket.recv(1024).decode()
            print(message)
            if not message:
                break
        except:
            break

    # 當客戶端中斷連線時，移除客戶端
    print(f"[連線中斷] {client_address} 斷開連線")
    del clients[client_address]
    client_socket.close()
    
def send_message():
    send_port=8080
    while True:
        current_time = time.localtime(time.time())
        # 在每分鐘的59秒執行掃描
        if current_time.tm_sec == 59:
            for send_ip in client_ip:
                try:
                    # 建立一個 socket 物件
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as send:
                        # 嘗試連接到指定的 IP 和端口
                        send.connect((send_ip, send_port))
                        # 傳送訊息
                        send.sendall("B".encode())
                        print("Message sent successfully!")
                except (ConnectionRefusedError, TimeoutError, socket.error):
                    # 如果無法連接或出現其他錯誤，則略過
                    print(f"{send_ip}未連線") #可是不知道為什麼這個都會顯示
                    break
                time.sleep(0.5)
        else:
            pass

# 循環掃描客戶端
def scan_clients():
    while True:
        current_time = time.localtime(time.time())
        # 在每分鐘的59秒執行掃描
        if current_time.tm_sec == 59:
            print("[掃描中] 掃描所有連線的客戶端...")
            active_clients = list(clients.keys())
            print(active_clients)
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
threading.Thread(target=send_message).start()
threading.Thread(target=scan_clients).start()
