import time
import serial #序列埠通訊
import serial.tools.list_ports
weight_temp=''
data_in=''
data_temp=[]

COM_PORT = 'COM4'    # 指定通訊埠名稱
BAUD_RATES = 9600    # 設定傳輸速率
ports = list(serial.tools.list_ports.comports()) #重設輸入的方法之一，就是重新開port。因擔心真的有讀碼異常的情形，故將這一段寫成def
for port in ports:
    if port.manufacturer.startswith( "Arduino" ):
        COM_PORT = port.name
    else:
        continue
arduinoSerial = serial.Serial(COM_PORT, BAUD_RATES)   # 初始化序列通訊埠
print("Modules imported. Port: "+COM_PORT)

while True:
    letter=input('type 1 or 2: ')
    arduinoSerial.write(letter.encode(encoding='utf-8'))
    time.sleep(10)
    while arduinoSerial.in_waiting:          # 若收到序列資料…
        data_in=arduinoSerial.readline()
        if b'\n' in data_in: #確定有取得資料尾
            print("original data:",data_in)
            if str(data_in.decode('utf-8')[0]) !='A': #沒有取到資料頭，放棄
                pass
            else:                                     #取得資料頭後，逐字取碼不解碼
                for j in range(0,len(data_in),1):
                    if data_in.decode('utf-8')[j] not in [',','-','1','2','3','4','5','6','7','8','9','0']:
                        pass                                        #為安全起見，讀到其他字符就pass 
                    elif data_in.decode('utf-8')[j] in ['-','1','2','3','4','5','6','7','8','9','0']:
                        weight_temp=weight_temp+data_in.decode('utf-8')[j]   #理論上應可組合成數字
                        print('weight_temp',weight_temp)
                           
                    elif data_in.decode('utf-8')[j]== ',':                   #讀到逗點，就結束這個數字
                        if weight_temp != '':                       #如果不是空的字串
                            data_temp.append(int(weight_temp)) #轉換為整數
                            weight_temp=''                          #重設
                    else:
                        pass
                break #結束，跳出迴圈                
    print(data_in)
        #print('return '+ data_in.decode('utf-8').rstrip())
#except KeyboardInterrupt:
#    arduinoSerial.close()    # 清除序列通訊物件
#    print('再見！')
