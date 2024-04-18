# On Line urine Lever urility ver 0.11d 本版是特別為了追蹤異常讀數而由b版增添了儲存原讀數的功能
# 由於如果使用maplotlib，無法使用Unihiker的A/B鍵功能，改成自己畫圖。
import time
import csv #讀寫csv檔
import numpy as np #主要數學運算用
import serial #序列埠通訊
import serial.tools.list_ports #為了自動搜尋通訊埠。如果要加速程式，而且固定使用在Unihiker的話，這個功能可以拿掉
import warnings #為了避開有的沒的警告
import sys #用來結束程式用
from unihiker import GUI   # Unihier GUI package
from sklearn.linear_model import LinearRegression #回歸用
from datetime import datetime #為了轉換時間格式方便

gui = GUI() 
startup_img = gui.draw_image(x=0, y=0,w=240, h=300,image='../upload/pict/Copyright.png')
txt=gui.draw_text(text="",x=120,y=10,font_size=12,origin="center",color="#0000FF")
message_text=gui.draw_text() #

global display_text,action, YEAR_action,MONTH_action,DAY_action,HOUR_action,MINUTE_action,Yr,Mo,D,Hr,Min,modify_time,delta_timestamp
# Initialize variables
display_text=''
action='nil'
arduinoSerial = None
period_second = [0,1,2,3,4,5,6,7,8,9,10]  #設定抓取序列埠傳入資料的時間（秒）
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

COM_PORT = 'dev/ttyACM0'
BAUD_RATES = 9600
file_name = ''

Yr=2024
Mo=6
D=15
Hr=12
Min=30

YEAR_action='nil'
MONTH_action='nil'
DAY_action='nil'
HOUR_action='nil'
MINUTE_action='nil'

modify_time='nil'

###########################################################################################   
#以下是鍵盤與顯示用函式
def INPUT():
    global B1,B2,B3,B4,B5,B6,B7,B8,B9,BB,B0,BE,txt
    global string_result,string_input
    string_input=[]
    string_result=''
    
    def btclick(data):
        string_input.append(data)
        txt.config(text=string_input)
        pass
    def btbackspace():
        del string_input[-1]
        txt.config(text=string_input)
        pass
    
    def btenter():
        global string_result
        seperator=''
        string_input.append('@')
        string_result=seperator.join(string_input)
        txt.config(text=string_result)
        pass

    B1=gui.draw_digit(x=40, y=70, text='1', origin="center", color="black", font_size=36,onclick=lambda: btclick('1'))
    B2=gui.draw_digit(x=120, y=70, text="2", origin='center',color="black", font_size=36, onclick=lambda: btclick('2'))
    B3=gui.draw_digit(x=200, y=70, text="3", origin='center',color="black", font_size=36, onclick=lambda: btclick('3'))
    B4=gui.draw_digit(x=40, y=140, text="4", origin='center',color="black", font_size=36, onclick=lambda: btclick('4'))
    B5=gui.draw_digit(x=120, y=140, text="5", origin='center',color="black", font_size=36, onclick=lambda: btclick('5'))
    B6=gui.draw_digit(x=200, y=140, text="6", origin='center',color="black", font_size=36, onclick=lambda: btclick('6'))
    B7=gui.draw_digit(x=40, y=210, text="7", origin='center',color="black", font_size=36, onclick=lambda: btclick('7'))
    B8=gui.draw_digit(x=120, y=210, text="8", origin='center',color="black", font_size=36, onclick=lambda: btclick('8'))
    B9=gui.draw_digit(x=200, y=210, text="9", origin='center',color="black", font_size=36, onclick=lambda: btclick('9'))
    BB=gui.draw_digit(x=40, y=280, text="back", origin='center',color="blue", font_size=18, onclick=lambda: btbackspace())
    B0=gui.draw_digit(x=120, y=280, text="0", origin='center',color="black", font_size=36, onclick=lambda: btclick('0'))
    BE=gui.draw_digit(x=200, y=280, text="OK", origin='center',color="red", font_size=24, onclick=lambda: btenter())
    txt=gui.draw_text(text="",x=120,y=10,font_size=16,origin="center",color="#0000FF")
               
    while True:
        gui.remove(startup_img)
        if '@' in string_input:
            gui.remove(txt)
            gui.remove(B1)
            gui.remove(B2)
            gui.remove(B3)
            gui.remove(B4)
            gui.remove(B5)
            gui.remove(B6)
            gui.remove(B7)
            gui.remove(B8)
            gui.remove(B9)
            gui.remove(BB)
            gui.remove(B0)
            gui.remove(BE)
            return(string_result[:-1])
            break
        else:
           # buttons()
            time.sleep(0.1)#增加等待，防止程序退出和卡住

#######################################################################################
#以下是更改時間用函式
def DELTA_TIME():
    global YEAR_action,MONTH_action,DAY_action,HOUR_action,MINUTE_action,Yr,Mo,D,Hr,Min,modify_time
    def YEAR(action):
        global YEAR_action,Yr,Mo,D,Hr,Min
        if action=='P':
            Yr=Yr+1
        elif action=='M':
            Yr=Yr-1
        YEAR_action=1    
    def MONTH(action):
        global MONTH_action,Yr,Mo,D,Hr,Min
        if action=='P':
            Mo=Mo+1
            if Mo > 12:
                Mo=1
        elif action=='M':
            Mo=Mo-1
            if Mo <1:
                Mo=12
        MONTH_action=1
    def DAY(action):
        global DAY_action,Yr,Mo,D,Hr,Min
        if action=='P':
            D=D+1
            if Mo in [1,3,5,7,8,10,12]:
                if D>31:
                    D=1
            elif Mo in [4,6,9,11]:
                if D>30:
                    D=1
            else:
                if Yr % 4 ==0:
                    if Yr==0:
                        if D>28:
                            D=1
                    else:
                        if D > 29:
                            D=1
                else:
                    if D>28:
                        D=1
        elif action=='M':
            D=D-1
            if Mo in [1,3,5,7,8,10,12]:
                if D<1:
                    D=31
            elif Mo in [4,6,9,11]:
                if D<1:
                    D=30
            else:
                if Yr % 4 ==0:
                    if Yr==0:
                        if D<1:
                            D=28
                    else:
                        if D <1 :
                            D=29
                else:
                    if D<1:
                        D=28
        DAY_action=1
        
    def HOUR(action):
        global HOUR_action,Yr,Mo,D,Hr,Min
        if action=='P':
            Hr=Hr+1
            if Hr>23:
                Hr=0        
        elif action=='M':
            Hr=Hr-1
            if Hr <0:
                Hr=23
        HOUR_action=1
    def MINUTE(action):
        global MINUTE_action,Yr,Mo,D,Hr,Min
        if action=='P':
            Min=Min+1
            if Min>59:
                Min=0
        elif action=='M':
            Min=Min-1
            if Min<0:
                Min=59
        MINUTE_action=1
    
    def modify_ok():
        global modify_time
        modify_time='@'

#-----------------------------------------------------------------------------------------------------   
    Year_set=gui.draw_text(x=120,y=60, text=str(Yr)+'年', color='red', origin='center',font_size=18)
    Month_set=gui.draw_text(x=120,y=110, text=str(Mo)+'月', color='red', origin='center',font_size=18)
    Day_set=gui.draw_text(x=120,y=160, text=str(D)+'日', color='red', origin='center',font_size=18)
    Hour_set=gui.draw_text(x=120,y=210, text=str(Hr)+'時', color='red', origin='center',font_size=18)
    Minute_set=gui.draw_text(x=120,y=260, text=str(Min)+'分', color='red', origin='center',font_size=18)
    Date_Time=gui.draw_text(x=120,y=15, text=time.strftime("%Y-%m-%d, %H:%M"), color='black', origin='center',font_size=12)

    Year_p=gui.add_button(x=35, y=60, w=60, h=30, text="+", origin='center', onclick=lambda: YEAR('P')) 
    Year_m=gui.add_button(x=205, y=60, w=60, h=30, text="-", origin='center', onclick=lambda: YEAR('M')) 
    Month_p=gui.add_button(x=35, y=110, w=60, h=30, text="+", origin='center', onclick=lambda: MONTH('P')) 
    Month_m=gui.add_button(x=205, y=110, w=60, h=30, text="-", origin='center', onclick=lambda: MONTH('M')) 
    Day_p=gui.add_button(x=35, y=160, w=60, h=30, text="+", origin='center', onclick=lambda: DAY('P')) 
    Day_m=gui.add_button(x=205, y=160, w=60, h=30, text="-", origin='center', onclick=lambda: DAY('M')) 
    Hour_p=gui.add_button(x=35, y=210, w=60, h=30, text="+", origin='center', onclick=lambda: HOUR('P')) 
    Hour_m=gui.add_button(x=205, y=210, w=60, h=30, text="-", origin='center', onclick=lambda: HOUR('M')) 
    Minute_p=gui.add_button(x=35, y=260, w=60, h=30, text="+", origin='center', onclick=lambda: MINUTE('P')) 
    Minute_m=gui.add_button(x=205, y=260, w=60, h=30, text="-", origin='center', onclick=lambda: MINUTE('M')) 
    Modify_OK=gui.add_button(x=120, y=300, w=60,h=30, text="OK", origin='center', onclick=lambda: modify_ok())
                
    while True:
        if YEAR_action==1:
            YEAR_action=='nil'
            Year_set.config(text=str(Yr)+'年') 
        if MONTH_action==1:
            MONTH_action=='nil'
            Month_set.config(text=str(Mo)+'月')            
        if DAY_action==1:
            DAY_action=='nil'
            Day_set.config(text=str(D)+'日') 
        if HOUR_action==1:
            HOUR_action=='nil'
            Hour_set.config(text=str(Hr)+'時') 
        if MINUTE_action==1:
            MINUTE_action=='nil'
            Minute_set.config(text=str(Min)+'分') 
        if modify_time=='@':
            gui.remove(Year_set)
            gui.remove(Month_set)
            gui.remove(Day_set)
            gui.remove(Hour_set)
            gui.remove(Minute_set)
            gui.remove(Year_p)
            gui.remove(Month_p)
            gui.remove(Day_p)
            gui.remove(Hour_p)
            gui.remove(Minute_p)
            gui.remove(Year_m)
            gui.remove(Month_m)
            gui.remove(Day_m)
            gui.remove(Hour_m)
            gui.remove(Minute_m)
            gui.remove(Modify_OK)
            current_time=str(Hr)+':'+str(Min)+' '+str(Mo)+' '+str(D)+' '+str(Yr)
            current_time=time.mktime(time.strptime(current_time,"%H:%M %m %d %Y"))
            delta_time=float(current_time-time.time()) #這個要丟回去
            #print(str(Yr)+str(Mo)+str(D)+str(Hr)+str(Min))
            #print(delta_timestamp)
            gui.remove(Date_Time)
            return delta_time #這個很重要，會用來改變現在的時間
            break
        else:
            time.sleep(0.1)

##########################################################################################################
#以下是監測重量時的顯示函式
def DISPLAY(action,message3):
    gui.clear() #每次都先擦掉
    global weight_FLUID,weight_PREVIOUS, display_text
    message2=weight_PREVIOUS #用message2代替weight_PREVIOUS，免得破壞主資料陣列
    message1=weight_FLUID    #用message1代替weight_FLUID，免得破壞主資料陣列
#-------------------------------------------------------------
    def DRAW_Y(scale,color_code,weight_plot):
        for y_tick in range(300,0,-20): #這三個數字是座標點
            y_axis_label=gui.draw_text(x=10,y=y_tick, text=round(scale/2.5*(650-2.5*y_tick)), color='black', origin='center',font_size=6)
        x_axis_label=gui.draw_text(x=120,y=301, text="-30 min", color='black', origin='center',font_size=6)
        for i in range(0,len(weight_plot)-1,1):
            if weight_plot[i] < 0:
                scatter=gui.draw_line(x0=238-4*x_cor[i], y0=260,x1=238-4*x_cor[i], y1=round(260-weight_plot[i]/scale)-1, width=3, color="black") #負值用黑線繪圖；照講寬度應該是要留4
            else:
                scatter=gui.draw_line(x0=238-4*x_cor[i], y0=260,x1=238-4*x_cor[i], y1=round(260-weight_plot[i]/scale)-1, width=3, color=color_code)#正值依照scale選顏色 
#-------------------------------------------------------------  
    if message2==[]: #第一輪沒有weight_PREVIOUS，所以只需要顯示weight_FLUID
        weight_plot=message1
    else:
        weight_plot=message2[-23:]+message1 #合併已存檔的資料（放在前，只取25個是因為畫面有預留空間給標籤）與新收的資料（在後）；0為最舊的資料，最後一個是最新的資料。
    
    for yn in range(0,301,20): #畫出格線
        x_grid=gui.draw_line(x0=20, y0=yn, x1=240, y1=yn, width=1, color=(122, 222, 44))#繪橫線，重量/2.5為座標，故一點=2.5克，上下範圍750克，每格50克，且不排斥負數
    for xn in range(20,240,20):
        y_grid=gui.draw_line(x0=xn, y0=1, x1=xn, y1=300, width=1, color=(122, 222, 44)) #繪縱線，共12線11格，每格20點，5分鐘    
    x_axis=gui.draw_line(x0=20, y0=260, x1=240, y1=260, width=1, color='black')#繪0參考線    
    x_cor = np.arange(0,len(weight_plot)-1,1) 
    x_cor=x_cor[::-1] #逆轉順序以供繪圖
    if np.max(weight_plot)<350: #改變Y的scale
        DRAW_Y(1.25,'orange',weight_plot)
    else:
        DRAW_Y(2.5,'blue',weight_plot)
        

    if message3=='':
        message3=display_text #display_text是用來再現先前所顯示的內容
    else:
        pass
    message_text=gui.draw_text(x=1,y=302, font_size=10,text=message3)
    display_text=message3
    if action=='clean':
        gui.clear()
    time.sleep(0.1)
 ##############################################################################################  
# Function to get weight from Arduino
def initial_value():
    while True:
        try:
            initial_data_in = arduinoSerial.readline()
            initial_data = data_in.decode('utf-8') #得到的type為string
            initial_weight_temp=int(initial_data)
        except:
            initial_weight_temp=0
        return initial_weight_temp
        break
#----------------------------------------        
def get_weight(): #注意：如果這段搞砸了，搬11d的回來用
    data_temp=''
    weight_temp=''
    arduinoSerial.reset_input_buffer()
    for i in range (0,100,1): #頂多抓個100次
        data_in = arduinoSerial.readline() #得到的type為string；Arduino只傳資料頭識別碼(A)、整數、'\n'。由於舊版讀數仍有異常，決定用笨方法。
        if b'\n' in data_in:
            if str(data_in.decode('utf-8')[0])=='A':
                data_temp=str(data_in.decode('utf-8').rstrip())#加上rstrip()去掉末尾
                for j in range(len(data_temp)):
                    if data_temp[j] in ['-','1','2','3','4','5','6','7','8','9','0']:
                        weight_temp=weight_temp+data_temp[j] #組合起來                   
                    else:
                        pass
                break
        else:
            time.sleep(0.01)
            pass
            
            
        #if b'\n' in data_in == False: #確定是否接收到完整數字。但如何判斷數字頭呢？
        #    time.sleep(0.01)
        #    pass
        #else: 
        #    data_temp=str(data_in.decode('utf-8').rstrip())#加上rstrip()去掉末尾
        #    if data_temp[0] =='A': #表示確定有抓到資料頭
        #        for j in range(len(data_temp)):
        #            if data_temp[j] in ['-','1','2','3','4','5','6','7','8','9','0']:
        #                weight_temp=weight_temp+data_temp[j] #組合起來                   
        #            else:
        #                pass
        #    else:
        #        time.sleep(0.01)
        #        pass
        #    break
    
    #except:
            #data_temp=-999 #此時等0.1秒之後再抓一次
            #i=i+1
            #time.sleep(0.1)
        #pass
   #負值視為異常。惟應注意實際應用上有可能導致重量暴增之情形。
   # if data_temp < -100 and data_temp > -999: #-100~-999 之間，表示可能有大減，應該要重設毛皮，且回傳0；在測試時發現，就算啥也沒動，還是可能莫名其妙進入這個範圍，所以暫時還是回傳-999
   #     arduinoSerial.close()
   #     arduinoSerial.open() #重開serial
   #     weight_temp=-999 
   #     DISPLAY('','weight_temp<-100')
   # elif data_temp ==-999: #如果跑完還是-999，表示本秒沒抓到；但是假如什麼也不做，回傳的就會是''
   #     weight_temp=-999
   #     pass
   # elif data_temp >2500: #顯然過重
   #     weight_temp=-999
   #     pass
   # elif data_temp < -999: #<-999，表示讀取的資料有問題，應該要重設毛皮，且回傳-999
   #     arduinoSerial.close()        
   #     arduinoSerial.open() #重設serial
   #     weight_temp=-999 #回傳為-999
   #     DISPLAY('','weight_temp<-100')
   # else:
   #     weight_temp=data_temp
   #       
   # arduinoSerial.reset_input_buffer()
   # #print('weight_temp',weight_temp)
    
    weight_temp=int(weight_temp)#加上一個簡單的異常數字判斷
    if weight_temp <-1000 or weight_temp >3000:
        weight_temp=-999
    else:
        pass

    return weight_temp
#----------------------------------------------------------
# Function to discard outliers
def discard_outlier(wt_list): #假如信任秤，應該也可以取眾數就好  
    wt_array = np.array(wt_list) #轉換為array
    mean = np.mean(wt_array)
    std_dev = np.std(wt_array)
    outlier_wt = wt_array[(wt_array >= mean - std_dev) & (wt_array <= mean + std_dev)] #上下限為一個標準差；留下在此範圍內的元素
    return outlier_wt.tolist()

# Function to calculate weight changes#需要偵測重量突減以及異常大量
def calculate_weight_changes(start_element):#呼叫時，要指定從串列的哪一個(start_element)開始計算。整點由0開始把全部的拿來算；每五分鐘從-10開始拿來算。
    global weight_FLUID
    weight_sum=0
    #print('calculate_weight_changes:weight_FLUID',weight_FLUID)
    if weight_FLUID !=[]:
        weight_max=weight_FLUID[-start_element] #先將最大值設成起始值
        weight_min=weight_FLUID[-start_element] #先將最小值設成起始值
        weight_recent=weight_FLUID[-start_element:] #工作用串列
        small_volume=np.max(weight_FLUID[-start_element])-np.min(weight_FLUID[-start_element])
        for i, element in enumerate(weight_recent):
            if weight_recent[i]>weight_max: #一個一個比較
                if weight_recent[i]> (weight_max+1500): #一分鐘差1500克，可能有問題
                    pass
                else:
                    weight_max=weight_recent[i] #假如目前這個比前一個大，就把weight_max數值設為目前這個
#            if weight_recent[i]<(weight_min+(weight_max-weight_min)/2): #發現突然減少（在上面那種小便很少的情形，不能一直進這個一直累加）
            if weight_recent[i]<weight_min/2: #發現突然減少（在上面那種小便很少的情形，不能一直進這個一直累加）
                weight_sum=weight_sum+weight_max-weight_min #之所以不能直接用< A_min，是考慮到有可能倒完以後的重量還是比空袋重，這樣就偵測不到了
                weight_max=weight_recent[i] #重設
                weight_min=weight_recent[i] #重設
                DISPLAY('',"可能有突減大量:"+str(weight_sum))#提醒使用者可能有誤差                               
            weight_sum=weight_max-weight_min
            if small_volume<10:#這裡是預設在一個尿量波動很小的範圍的時候，直接用最大值減最小值來估計就好。不管每5分鐘或每小時，都用10gm
                weight_Sum=small_volume
    DISPLAY('',"小計:"+str(weight_sum))
    return weight_sum
    

# Function to perform basic regression
def basic_regression(basic_regression_wt, n_of_elements):#呼叫時傳來的數據放在basic_regression_wt，取n個來計算
    y = basic_regression_wt[-n_of_elements:]
    x = np.arange(1, n_of_elements + 1).reshape((-1, 1))
    model = LinearRegression().fit(x, y)
    return model.coef_

# Function to calculate regression
def calculate_regression(analysis_wt, n_of_elements):
    analysis_wt = analysis_wt[-n_of_elements:]
    x = np.arange(1, n_of_elements).reshape((-1, 1))
    y = np.diff(analysis_wt)
    model = LinearRegression().fit(x, y)
    return model.intercept_, model.coef_

# Function to save data
def saving_data(saving_time, saving_weight, cutting_index,saving_raw): #位置一為time_INDEX，二是weight_FLUID，三是分鐘
    if saving_weight:
        hour_weight_change = calculate_weight_changes(0)#從0開始算，該函式回傳數值weight_sum在此會放進hour_weight_change。
        time_marker = time.strftime("%Y-%m-%d, %H:%M")

        saving_time_upper = [t for t in saving_time if int(t[-2:]) < 30]#表示這是00-29分的資料，放進上半。t指time，w指weight
        saving_weight_upper = [w for t, w in zip(saving_time, saving_weight) if int(t[-2:]) < 30] #把兩個串列裡相同位置的元素配在一起
        saving_raw_upper = [r for t, r in zip(saving_time, saving_raw) if int(t[-2:]) < 30] #把兩個串列裡相同位置的元素配在一起
        saving_time_lower = [t for t in saving_time if int(t[-2:]) >= 30]#不然就是30-59分的資料，歸在下半
        saving_weight_lower = [w for t, w in zip(saving_time, saving_weight) if int(t[-2:]) >= 30]
        saving_raw_lower = [r for t, r in zip(saving_time, saving_raw) if int(t[-2:]) < 30] #把兩個串列裡相同位置的元素配在一起

        if cutting_index == 59:#59分的時候，保留30-59的資料，儲存00-29的資料
            file_time = saving_time_upper
            file_weight = saving_weight_upper
            file_raw = saving_raw_upper
            saving_time = saving_time_lower
            saving_weight = saving_weight_lower
            saving_raw = saving_raw_lower
        elif cutting_index == 29:#29分的時候，保留00-29的資料，儲存30-59的資料
            file_time = saving_time_lower
            file_weight = saving_weight_lower
            file_raw = saving_raw_lower
            saving_time = saving_time_upper
            saving_weight = saving_weight_upper
            saving_raw = saving_raw_upper
        with open(file_name, 'a', newline='') as csvfile:
            wt = csv.writer(csvfile)
            #print("file_weight:"+file_weight)
            for save_time, save_weight, save_raw in zip(file_time, file_weight, file_raw):
                wt.writerow([save_time, save_weight, save_raw])
            DISPLAY('',"30分鐘重量變化："+ str(round(hour_weight_change)) +' ；存檔完成')
            
        return saving_time, saving_weight,file_weight, saving_raw

def on_click():
    global action
    action='clean'
    
def good_bye(): #按A或B鍵結束    
    with open(file_name, 'a', newline='') as csvfile:
        wt = csv.writer(csvfile)
        for save_time, save_weight, save_raw in zip(time_INDEX,weight_FLUID, weight_RAW):
            wt.writerow([save_time, save_weight, save_raw])

    print('Data saved as: '+file_name+'. Good Bye~')



########################################################################################################################  
#主函式
def main():
    global weight_FLUID, time_INDEX, arduinoSerial, file_name,time_stamp,weight_PREVIOUS, display_text, delta_timestamp, weight_RAW
    adjusted_time=time.time()+delta_timestamp
    time_INDEX.append(str(datetime.fromtimestamp(adjusted_time))) #改成用調整時間
    initial_weight_temp=initial_value()
    weight_FLUID.append(initial_weight_temp)
    weight_RAE.append(initial_weight_temp) #為了填補數據用的暫時數據，無妨。
    DISPLAY('','初始值:'+str(weight_FLUID[0])+'; '+time_INDEX[0])
    #改用調整時間，判斷如果是29分或59分的時候，等一分鐘以後再開始
    adjusted_time=time.time()+delta_timestamp
    if datetime.fromtimestamp(adjusted_time).minute== 29 or 59:
    #if time.localtime()[4] == 29 or 59: #剛好這兩個時間點的時候，寧可等一分鐘再開始，以免存個空陣列
        time.sleep(60)

    current_minute = 61
    five_weight_change=10
    one_min_weight=-999
    #以下是設定比較回歸預測準確性所需的變數，預計在這個精簡版不會使用
    prediction_selection=None
    previous_prediction_15=[0,0]
    current_second = None
    weight_PREVIOUS=[] #忘記先前為什麼改設空

    #以下開始
    while True:                    
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複
            if action=="clean": #按下A或B的時候，停止main()的執行，進入程式結束階段。這也是為什麼在執行到這裡之前按下A/B都不會有反應。
                break

            if time.localtime()[4] != current_minute: #current_time代表以下程式區塊所執行的時間。time.localtime[4]不等於current_time時，表示是新的一分鐘
                current_minute=time.localtime()[4] #將current_minute設定為目前時間。以上兩行確保下列區塊每分鐘只執行一次
                #weight_flag=0
                one_min_weight=[]

                while time.localtime()[5] in period_second:
                    current_second=time.localtime()[5]
                    if time.localtime()[4] != current_second:
                        one_sec_weight=get_weight()
                        if one_sec_weight == -999 : #要確定不是空串列
                            if len(one_min_weight)>1:#one_min_weight不能為空啊~
                                one_min_weight.append(one_min_weight[-1]) #本秒鐘回傳為空，就重複同一分鐘內上一秒的數字。
                            else:
                                one_min_weight.append(0)#如果真的是空，就當作0吧          
                        elif one_sec_weight-weight_FLUID[-1]>100: #不大可能一秒鐘比上一分鐘的重量多100克
                            pass
                        else:
                            one_min_weight.append(one_sec_weight)  #如非以上特例，則將傳回的數字加入本分鐘串列

        #這一分鐘裡面，前面的10秒收集完以後，去除outlier。目前仍採超過一個標準差法。                
                if len(one_min_weight) > 0 : #要送去跑的話，應該全部是數字，所以這裡判斷不只是空串列，還必須全是數字。如果還是很麻煩，不如不要搞什麼outlier，就是呆呆地每分鐘的00秒接收一次就好。
                    DISPLAY('',one_min_weight) #去畫圖
                    weight_raw_string=",".join(str(element) for element in one_min_weight)
                    one_weight_temp=discard_outlier(one_min_weight) #呼叫。除掉outlier，傳回資料放在one_weight_temp
                    weight_FLUID.append(np.mean(one_weight_temp))   #將已去除outlier的數字計算平均，並加入重量紀錄主串列weight_Fluid
                    weight_RAW.append(weight_raw_string)
                    adjusted_time=time.time()+delta_timestamp
                    time_INDEX.append(str(datetime.fromtimestamp(adjusted_time))[:16])#改成用調整時間（前16個字元）加入時間記錄主串列time_INDEX
                    DISPLAY('',one_min_weight) #去畫圖
                    one_min_weight=[]
                else:
                    weight_FLUID.append(weight_FLUID[-1]) #等於上一分的數字 
                    DISPLAY('',one_min_weight) #去畫圖
                    pass 

        #每5分鐘以最近十個數據，利用回歸分析判斷趨勢與估計尿量。
                if time.localtime()[4] in period_minute and len(weight_FLUID) >= 11:        #先計算最近十分鐘的總重量變化
                    five_weight_change=calculate_weight_changes(10) #呼叫。取倒數10個計算重量變化
                    #MAIN_DISPLAY('print',"最近十分鐘尿量:"+str(five_weight_change),'')
        #利用重量變化計算趨勢與估計未來尿量
                    five_regression=calculate_regression(weight_FLUID,10)   #呼叫。以每分鐘重量差，評估趨勢（至少10個的時候才跑回歸計算趨勢）
                    if five_regression[1] < 0:
                        DISPLAY('',"最近十分鐘尿量:"+str(round(five_weight_change))+"趨勢：減少")
                    else:
                        DISPLAY('',"最近十分鐘尿量:"+str(round(five_weight_change))+"趨勢：穩定或增加") 

        #每59分或29分紀錄總尿量。為了簡化，有考慮一小時存一次即可
                if time.localtime()[4]  == 59 and len(weight_FLUID) >= 1:
                    processed_data=saving_data(time_INDEX,weight_FLUID,59,weight_RAW) #呼叫存檔函式
                    time_INDEX=processed_data[0]      #留下縮減過的資料串列
                    weight_FLUID=processed_data[1]    #留下縮減過的資料串列
                    weight_PREVIOUS=processed_data[2] #已經存入的資料串列
                    weight_RAW=processed_data[3]
                    pass
                elif time.localtime()[4]  == 29 and len(weight_FLUID) >= 1:
                    processed_data=saving_data(time_INDEX,weight_FLUID,29,weight_RAW)
                    time_INDEX=processed_data[0]
                    weight_FLUID=processed_data[1]
                    weight_PREVIOUS=processed_data[2]
                    weight_RAW=processed_data[3]
                    pass
                else:
                    pass
            
            time.sleep(0.1)

        except Warning:
            raise
        except ZeroDivisionError:
            print('估計可能不準')
        except Exception:
            raise
############################################################################################################################################

if __name__ == '__main__':  
    ports = list( serial.tools.list_ports.comports() )
    for port in ports:
        if port.manufacturer.startswith( "Arduino" ):
            COM_PORT = '/dev/'+port.name
        else:
            continue    
    message_text.config(x=1,y=302, font_size=10,text="Port:"+COM_PORT)
    arduinoSerial = serial.Serial(COM_PORT, BAUD_RATES) #開啟port
    start_time=time.localtime()
    time.sleep(5)
    RESULT=INPUT()  #輸入病歷號
    file_name=RESULT+'.csv'
    message_text.config(x=1,y=302, font_size=10,text='file:'+file_name)
    delta_timestamp=DELTA_TIME() #輸入現在時間
    warnings.filterwarnings('ignore', module="numpy")
    warnings.filterwarnings('ignore', message='invalid value encountered in scalar divide')
    warnings.filterwarnings('ignore', message='invalid value encountered in divide')
    gui.on_key_click('a',on_click)#按A鍵結束
    gui.on_key_click('b',on_click)
    
    main()
    gui.clear
    good_bye()
    print('Olulu ver. 0.11b. A or B Button pressed.')
    sys.exit(0)
