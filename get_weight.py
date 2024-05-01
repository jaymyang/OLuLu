import sys #結束程式用
import time #時間模組
from datetime import datetime #轉換時間格式方便使用
import csv #讀寫csv檔
import numpy as np #數學運算用
import statistics
import serial #序列埠通訊
import serial.tools.list_ports #為了自動搜尋通訊埠。如果要加速程式，而且固定使用在Unihiker的話，這個功能可以拿掉
import warnings #為了避開有的沒的警告
from sklearn.linear_model import LinearRegression #回歸用
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import signal


# Initialize variables
global display_text,action, YEAR_action,MONTH_action,DAY_action,HOUR_action,MINUTE_action,Yr,Mo,D,Hr,Min,modify_time,delta_timestamp
display_text=''
action='nil'
arduinoSerial = None
period_second = [0,1,2,3,4,5,6,7,8,9,10,12,14,16,18,20,22,24,26,28,30]  #設定抓取序列埠傳入資料的時間（秒）
period_minute = [0,5,10,15,20,25,30,35,40,45,50,55]  #設定進行統計的時間（每5分鐘）
time_INDEX=[]
weight_FLUID = [] #主重量紀錄串列
weight_PREVIOUS=[]
weight_RAW=[]
#以下為用於計算尿量與趨勢的串列與數值
analysis_wt= []
analysis_tmIn=[]
value_next=[]
weight_new=None
weight_old=None
mean=None
std_dev=None
time_stamp=time.time()
delta_timestamp=0

file_name = ''
COM_PORT = 'COM4'    # 指定通訊埠名稱
BAUD_RATES = 9600    # 設定傳輸速率
arduinoSerial = serial.Serial(COM_PORT, BAUD_RATES)   # 初始化序列通訊埠

def get_data():
    data_temp=''
    weight_temp=''
    arduinoSerial.reset_input_buffer()    
    while True:
        while arduinoSerial.in_waiting:          # 若收到序列資料…
            print('getting data')
            data_in = arduinoSerial.readline() #得到的type為string；Arduino只傳資料頭識別碼(A)、整數、'\n'。由於舊版讀數仍有異常，決定用笨方法。
            #print(data_in)
            if b'\n' in data_in and str(data_in.decode('utf-8')[0]) =='A':
                data_temp=str(data_in.decode('utf-8').rstrip())#解碼；用rstrip()去掉末尾
                #print('data_temp',data_temp)
                weight_temp=int(str(data_temp)[1:])
                break
                
            else:
                time.sleep(0.1) #
                pass
        if type(weight_temp)==int:
            break
        else:
            pass
    arduinoSerial.reset_input_buffer()  
    return weight_temp
    

def get_weight(): #取Arduino
    weight_data=get_data()
    arduinoSerial.write(str(weight_data).encode(encoding='utf-8'))
    while arduinoSerial.in_waiting:
        T_F = arduinoSerial.readline()
        print(T_F.decode('utf-8').rstrip())
        if T_F.decode('utf-8').rstrip() =='T':
            break
        else:
            weight_data=999.9

      
    #if weight_temp=='': #抓到了個空
    #    weight_temp=-999.9 #因為序列埠只回傳整數，所以故意設定為小數
    #elif weight_temp=='-': #只抓到負號沒有數字
    #    weight_temp=-999.9
    #else:
    #    weight_temp=int(weight_temp) #數字太離譜
    #    if weight_temp <-1000 or weight_temp >3000:
    #        weight_temp=-999.9
    #    else:
    #        pass
    print('weight_data',weight_data)
    return weight_data



#主函式
def main():
    global weight_FLUID, time_INDEX, arduinoSerial, file_name,time_stamp,weight_PREVIOUS, display_text, delta_timestamp, weight_RAW
    
    current_minute = 61
    five_weight_change=10
    one_min_weight=-999
    #以下開始
    while True:                    
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複
            #if action=="clean": #按下A或B的時候，停止main()的執行，進入程式結束階段。這也是為什麼在執行到這裡之前按下A/B都不會有反應。
            #    break
            current_second=time.localtime()[5]
            if time.localtime()[4] != current_minute: #current_time代表以下程式區塊所執行的時間。time.localtime[4]不等於current_time時，表示是新的一分鐘
                current_minute=time.localtime()[4] #將current_minute設定為目前時間。以上兩行確保下列區塊每分鐘只執行一次
                one_min_weight=[]
                weight_flag=0

                while time.localtime()[5] in period_second:                                                          
                    if time.localtime()[5] != current_second:   #每秒只會抓一次
                        current_second=time.localtime()[5]  
                        one_sec_weight=get_weight() #抓重量，回傳的數字放在one_sec_weight
                        if one_sec_weight == -999.9 : #-999.9為異常值。重複同一分鐘上一秒的數字。
                            if len(one_min_weight)!=0:#one_min_weight必須不是空串列
                                one_min_weight.append(one_min_weight[-1]) #本秒鐘回傳為空，就重複同一分鐘內上一秒的數字。
                            else:#如果one_min_weight是空串列
                                if len(weight_FLUID)!=0:#那就用weight_FLUID的最後一個，也就是上一分鐘的最後一個。但必須要注意第一個數字有可能是0
                                    one_min_weight.append(weight_FLUID[-1])
                                else:#weight_FLUID是空的話，直接接0
                                    one_min_weight.append(0)#
                        else: #非異常值
                            one_min_weight.append(one_sec_weight)  #如非以上特例，則將傳回的數字加入本分鐘串列
                    
#收集10秒的數字以後，判斷異常。
                print('one_min_weight',one_min_weight)

 
        except Warning:
            raise
        except ZeroDivisionError:
            print('估計可能不準')
        except Exception:
            raise

        
if __name__ == '__main__':











    main()
    signal.signal(signal.SIGINT,good_bye)
    print('Olulu ver. 0.11b. A or B Button pressed.')
    sys.exit(0)
