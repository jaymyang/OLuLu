import serial #序列埠通訊
import serial.tools.list_ports
import time

ports = list(serial.tools.list_ports.comports()) #重設輸入的方法之一，就是重新開port。因擔心真的有讀碼異常的情形，故將這一段寫成def
for port in ports:
    if port.manufacturer.startswith( "Arduino" ):
        COM_PORT = port.name
    else:
        continue    
print("Modules imported. Port: "+COM_PORT)
arduinoSerial = serial.Serial(COM_PORT, 9600) #開啟port
arduinoSerial.flushInput() 
while True:
    letter=input('type something: ')
    arduinoSerial.write(letter.encode(encoding='utf-8'))
    data=arduinoSerial.readline()
    print(data)
    print('return '+ data.decode('utf-8').rstrip())
    
