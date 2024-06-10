# On Line urine Lever urility ver 0.2
#版次0.2的要點
#1.簡化get_weight，每分鐘只抓一次（未來可搭配將Arduino端改減少取重頻率）版，但暫時保留舊版的作法，以備萬一；也可能改用Arduino統一發送10秒數據的方式。待試用狀況決定。
#結果發現即使是固定負重的時候，仍然發生重量飄移（上下幾公克）的狀況。考慮改為hybrid 方法，就是Arduino取數秒資料後一次送來。
#2.加上顯示8小時之內尿量趨勢的功能
#3.加上wifi ftp傳輸檔案功能（還在構思）
#覺得加上音效太麻煩，所以沒加

print("Olulu ver. 0.12 is starting up.")
#GUI功能
from unihiker import GUI   # Unihier GUI package
gui = GUI() 
startup_img = gui.draw_image(x=0, y=0,w=240, h=300,image='Copyright-1.png')
txt=gui.draw_text(text="",x=120,y=10,font_size=12,origin="center",color="#0000FF")
message_text=gui.draw_text() #
#其他模組
import sys #結束程式用
import time #時間模組
from datetime import datetime #轉換時間格式方便使用
import csv #讀寫csv檔
message_text.config(x=1,y=302, font_size=10,text="Starting up.....50% modules imported.")
import numpy as np #數學運算用
import statistics
import serial #序列埠通訊
import serial.tools.list_ports #為了自動搜尋通訊埠。如果要加速程式，而且固定使用在Unihiker的話，這個功能可以拿掉
message_text.config(x=1,y=302, font_size=10,text="Starting up.....75% modules imported.")
import warnings #為了避開有的沒的警告
from sklearn.linear_model import LinearRegression #回歸用
message_text.config(x=1,y=302, font_size=10,text="All modules imported. Finding Arduino device.")

global display_text,action, YEAR_action,MONTH_action,DAY_action,HOUR_action,MINUTE_action,Yr,Mo,D,Hr,Min,modify_time,delta_timestamp
# Initialize variables
display_text=''
action='nil'
arduinoSerial = None
period_second = [0,1,2,3,4,5,6,7,8,9,10]  #設定抓取序列埠傳入資料的時間（秒）
period_minute = [0,10,20,30,40,50]  #設定進行統計的時間（每10分鐘）
time_INDEX=[]
weight_FLUID = [] #主重量紀錄串列
weight_PREVIOUS=[]
weight_RAW=[]
#以下為用於計算尿量與趨勢的串列與數值
urine_amount=[]
analysis_wt= []
analysis_tmIn=[]
value_next=[]
weight_new=None
weight_old=None
mean=None
std_dev=None
time_stamp=time.time()
delta_timestamp=0
#Unihiker序列埠使用的變數
COM_PORT = 'dev/ttyACM0' 
BAUD_RATES = 9600
file_name = ''

#使用者輸入目前時間所用的變數
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
modify_time='nil' #因為Unihiker如不連上網路就會設定在2019年，本變數乃用於使用者輸入現在時間之校正用

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
# Function to plot scatter plot
def plot_scatter(Title):
    global weight_FLUID,weight_PREVIOUS
    weight_plot=weight_PREVIOUS+weight_FLUID
    print('weight_PLOT',weight_plot)
    x = np.arange(len(weight_plot))
    plt.scatter(x, weight_plot, c='g', marker='>')
    plt.title(Title)
    plt.xlim([0, 60])
    plt.show(block=False)
    plt.pause(0.1)
##########################################################################################################
#以下是監測重量時的顯示函式
def DISPLAY(action,message3):
    gui.clear() #每次都先擦掉
    global weight_FLUID,weight_PREVIOUS, urine_amount,display_text
    #照講下面這樣寫不是一般通用寫法，結構上不漂亮，但為了暫時可以驗證可用，先這樣寫
    message2=weight_PREVIOUS #用message2代替weight_PREVIOUS，免得破壞主資料陣列
    message1=weight_FLUID    #用message1代替weight_FLUID，免得破壞主資料陣列
#-------------------------------------------------------------
    def DRAW_Y(scale,color_code,weight_plot):
        for y_tick in range(300,0,-20): #座標點
            y_axis_label=gui.draw_text(x=10,y=y_tick, text=round(scale/2.5*(650-2.5*y_tick)), color='black', origin='center',font_size=6)
        if color_code =='yellow':
            x_axis_label=gui.draw_text(x=120,y=265, text='urine amount in past 8 hours', color='black', origin='center',font_size=8)
        else:
            for x_tick in range(238,37,-40): #座標點
                x_axis_label=gui.draw_text(x=x_tick,y=265, text=str(int(x_tick/4-60)), color='black', origin='center',font_size=8)
        for i in range(0,len(weight_plot)-1,1):
            if weight_plot[i] < 0:#負值用黑線繪圖；照講寬度應該是要留4
                scatter=gui.draw_line(x0=238-4*x_cor[i], y0=260,x1=238-4*x_cor[i], y1=round(260-weight_plot[i]/scale)-1, width=3, color="black") 
            else:#正值依照scale選顏色 
                scatter=gui.draw_line(x0=238-4*x_cor[i], y0=260,x1=238-4*x_cor[i], y1=round(260-weight_plot[i]/scale)-1, width=3, color=color_code)
#-------------------------------------------------------------  
    if message2==[]: #第一輪沒有weight_PREVIOUS，所以只需要顯示weight_FLUID
        weight_plot=message1
    else:
        weight_plot=message2[-23:]+message1 #合併已存檔的資料（放在前，只取最後23個是因為預留空間給標籤）與新收的資料（在後）；0為最舊的資料，最後一個是最新的資料。
    if action=='10min':
        weight_plot=urine_amount
    weight_plot=weight_plot[-56:] #不管如何只取後55個來畫
#以上取好了準備要繪圖的值    
    for yn in range(0,301,20): #畫出格線
        x_grid=gui.draw_line(x0=20, y0=yn, x1=240, y1=yn, width=1, color=(122, 222, 44))#繪橫線，重量/2.5為座標，故一點=2.5克，上下範圍750克，每格50克，且不排斥負數
    for xn in range(20,240,20):
        y_grid=gui.draw_line(x0=xn, y0=1, x1=xn, y1=300, width=1, color=(122, 222, 44)) #繪縱線，共12線11格，每格20點，5分鐘    
    x_axis=gui.draw_line(x0=20, y0=260, x1=240, y1=260, width=1, color='black')#繪0參考線    
    x_cor = np.arange(0,len(weight_plot)-1,1) 
    x_cor=x_cor[::-1] #逆轉順序以供繪圖
    if message3=='':
        message3=display_text #display_text是用來再現先前所顯示的內容
    else:
        pass
    message_text=gui.draw_text(x=1,y=302, font_size=10,text=message3)
    display_text=message3
  

    if action=='clean':
        gui.clear()
    elif len(weight_plot)==0: #有可能是空陣列沒得畫圖
        pass
    elif action=='10min':
        DRAW_Y(2.5,'yellow',urine_amount)         
    else:
        if np.max(weight_plot) < 350: #改變Y的scale
            DRAW_Y(1.25,'orange',weight_plot)  
        else:
            DRAW_Y(2.5,'blue',weight_plot)
        
        
    time.sleep(0.1)
 ###############################################################################

# Function to get weight from Arduino
def initial_value(): #照講這個應該一樣用get_weight()就好
    while True:
        try:
            initial_data_in = arduinoSerial.readline()
            initial_data = data_in.decode('utf-8') #得到的type為string
            initial_weight_temp=int(initial_data)
        except:
            initial_weight_temp=0
        return initial_weight_temp
        break
#-------------------------------------------------------------------------------     
def get_data():
    data_temp=''
    weight_temp=''
    arduinoSerial.flushInput()  
    while True:
        while arduinoSerial.inWaiting():          # 若收到序列資料…
            data_in = arduinoSerial.readline() #得到的type為string；Arduino只傳資料頭識別碼(A)、整數、'\n'。由於舊版讀數仍有異常，決定用笨方法。
            if b'\n' in data_in: #確定有取得資料尾
                if str(data_in.decode('utf-8')[0]) !='A': #沒有取到資料頭，放棄
                    pass
                else:                                     #有取得資料頭後，去尾
                    data_temp=str(data_in.decode('utf-8').rstrip()) #解碼；用rstrip()去掉末尾
                    weight_temp=int(str(data_temp)[1:])             #!!!---賦值---!!!
                    break #結束，跳出迴圈                
            else:                #沒有取得資料尾，無效
                time.sleep(0.01) 
                pass
        if type(weight_temp)==int: #再次確認是否取得整數
            break                  #結束，跳出迴圈
        else: #如非取得整數
            #arduinoSerial.flushInput() #清空
            weight_temp='' #清空
            pass    
    DISPLAY('',str(weight_temp)+str(time.localtime()[4]))
    return weight_temp
    
def get_weight(): 
    count=0
    return_data=[]
    
    while True:
        if count > 8: #由於可能需要重複取，每次重複需時將多一秒，故最多只取8次
            break
        else:
            weight_data=get_data()
            time.sleep(0.01)
            #arduinoSerial.flushInput()#再次清空，因為待會還要回送並獲取Arduino端回報結果，故清空以確保
            arduinoSerial.write(str(weight_data).encode(encoding='utf-8')) #將前述數字送去Arduino
            time.sleep(0.01)
            T_F = arduinoSerial.readline().decode('utf-8').rstrip()        #收Arduino端回覆
            if T_F =='T':           #讀取結果無誤
                if weight_data=='': #抓到了個空
                    weight_data=-999.9 #因為序列埠只回傳整數，所以故意設定為小數
                elif weight_data=='-': #只抓到負號沒有數字
                    weight_data=-999.9
                elif weight_data <-1000 or weight_data >3000: #可疑數字；這些閾值還可以改
                    weight_data=-999.9
                else:
                    pass                            
            else: #如果抓到F，照講應該不管，跳過。但就怕結果通通都是-999.9，所以在main那邊還有處理
                weight_data=-999.9
                pass
            return_data.append(weight_data)
            count=count+1
    #DISPLAY('','complete getting_weight')
    return return_data

#----------------------------------------------------------
# Function to discard outliers
def discard_outlier(wt_list): #假如信任秤，應該也可以取眾數就好  
    wt_array = np.array(wt_list) #轉換為array
    mean = np.mean(wt_array)
    std_dev = np.std(wt_array)
    outlier_wt = wt_array[(wt_array >= mean - 0.5*std_dev) & (wt_array <= mean + 0.5*std_dev)] #上下限為0.5個標準差；留下在此範圍內的元素
    return outlier_wt.tolist()

# Function to calculate weight changes#需要偵測重量突減以及異常大量
# 本版改的是只要一分鐘相差超過20公克，就視為需要重算
def calculate_weight_changes(start_element):#呼叫時，要指定從串列的哪一個(start_element)開始計算。整點由0開始把全部的拿來算；每十分鐘從-10開始拿來算。
    global weight_FLUID
    weight_sum=0
    #print('calculate_weight_changes:weight_FLUID',weight_FLUID)
    if weight_FLUID !=[]:
        weight_max=weight_FLUID[-start_element] #先將最大值設成起始值
        weight_min=weight_FLUID[-start_element] #先將最小值設成起始值
        weight_recent=weight_FLUID[-start_element:] #工作用串列
        small_volume=np.max(weight_FLUID[-start_element])-np.min(weight_FLUID[-start_element]) #這邊先計算是否為small volume
        #---以下這段與01X版不同---
        for i in range(1,len(weight_recent)-1,1): 
            if abs(weight_recent[i]-weight_recent[i-1])<20: #假設相差小於20克是合理的
                if weight_recent[i]>weight_max: 
                    weight_max=weight_recent[i] #假如目前這個比較大，就把weight_max數值設為目前這個
                elif weight_recent[i]<weight_max: 
                    weight_min=weight_recent[i] #假如目前這個比較大，就把weight_max數值設為目前這個
                else:
                    pass
            else:
                weight_sum=weight_sum+weight_max-weight_min #本階段結束，將本階段重量差加上原重量差，視為尿量
                weight_max=weight_recent[i] #重設
                weight_min=weight_recent[i] #重設
                   
        if small_volume<10:#這裡是預設在一個尿量波動很小的範圍的時候，直接用最大值減最小值來估計就好。不管每5分鐘或每小時，都用10gm
            weight_Sum=small_volume
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
def saving_data(saving_time, saving_weight, cutting_index): #位置一為time_INDEX，二是weight_FLUID，三是分鐘
    if saving_weight:
        hour_weight_change = calculate_weight_changes(0)#從0開始算，該函式回傳數值weight_sum在此會放進hour_weight_change。
        time_marker = time.strftime("%Y-%m-%d, %H:%M")

        saving_time_upper = [t for t in saving_time if int(t[-2:]) < 30]#表示這是00-29分的資料，放進上半。t指time，w指weight
        saving_weight_upper = [w for t, w in zip(saving_time, saving_weight) if int(t[-2:]) < 30] #把兩個串列裡相同位置的元素配在一起
        #saving_raw_upper = [r for t, r in zip(saving_time, saving_raw) if int(t[-2:]) < 30] #把兩個串列裡相同位置的元素配在一起
        saving_time_lower = [t for t in saving_time if int(t[-2:]) >= 30]#不然就是30-59分的資料，歸在下半
        saving_weight_lower = [w for t, w in zip(saving_time, saving_weight) if int(t[-2:]) >= 30]
        #saving_raw_lower = [r for t, r in zip(saving_time, saving_raw) if int(t[-2:])  >= 30] #!!!注意其他版本的這裡

        if cutting_index == 59:#59分的時候，保留30-59的資料，儲存00-29的資料
            file_time = saving_time_upper
            file_weight = saving_weight_upper
            #file_raw = saving_raw_upper
            saving_time = saving_time_lower
            saving_weight = saving_weight_lower
            #saving_raw = saving_raw_lower
        elif cutting_index == 29:#29分的時候，保留00-29的資料，儲存30-59的資料
            file_time = saving_time_lower
            file_weight = saving_weight_lower
            #file_raw = saving_raw_lower
            saving_time = saving_time_upper
            saving_weight = saving_weight_upper
            #saving_raw = saving_raw_upper
        with open(file_name, 'a', newline='') as csvfile:
            wt = csv.writer(csvfile)
            #print("file_weight:"+file_weight)
            for save_time, save_weight in zip(file_time, file_weight):
                wt.writerow([save_time, save_weight])
            DISPLAY('',"30分鐘重量變化："+ str(round(hour_weight_change)) +' ；存檔完成')
            
        return saving_time, saving_weight,file_weight

def on_click():
    global action
    action='clean'
    
    
def good_bye(): #按A或B鍵結束    
    with open(file_name, 'a', newline='') as csvfile:
        wt = csv.writer(csvfile)
        for save_time, save_weight, save_raw in zip(time_INDEX,weight_FLUID, weight_RAW):
            wt.writerow([save_time, save_weight, save_raw])

    print('Data saved as: '+file_name+'. Good Bye~')
    raise KeyboardInterrupt()

########################################################################################################################  
#主函式
def main():
    global weight_FLUID, time_INDEX, arduinoSerial, file_name,time_stamp,weight_PREVIOUS, display_text, delta_timestamp, weight_RAW, urine_amount
    adjusted_time=time.time()+delta_timestamp
    #time_INDEX.append(str(datetime.fromtimestamp(adjusted_time))[:16])#改成用調整時間（前16個字元）加入時間記錄主串列time_INDEX
    print(str(datetime.fromtimestamp(adjusted_time)))
    initial_weight_temp=initial_value()
    #weight_FLUID.append(round(np.mean(initial_weight_temp)))
    #if weight_FLUID[0]=='NaN':
    #    weight_FLUID[0]=0
        
    #weight_RAW.append(initial_weight_temp) #為了填補數據用的暫時數據，無妨。
    DISPLAY('',str(datetime.fromtimestamp(adjusted_time))[:16]+' 初始值:'+str(initial_weight_temp))
    #改用調整時間，判斷如果是29分或59分的時候，等一分鐘以後再開始
    if datetime.fromtimestamp(adjusted_time).minute== 29 or 59: #剛好這兩個時間點的時候，寧可等一分鐘再開始，以免存個空陣列
        time.sleep(60)
    current_minute = 61
    five_weight_change=10
    one_min_weight=-999
    
    #以下是設定比較回歸預測準確性所需的變數，預計在這個精簡版不會使用
    prediction_selection=None
    previous_prediction_15=[0,0]
    current_second = None
    weight_PREVIOUS=[] #忘記先前為什麼改設空
    one_min_abn=0
    
    #以下開始
    while True:
        if action=="clean": #按下A或B的時候，停止main()的執行，進入程式結束階段。
            break        
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複

            #current_second=time.localtime()[5]
            if time.localtime()[4] != current_minute: #time.localtime[4]不等於current_minute時，表示是新的一分鐘       
                DISPLAY('',time.localtime()[4])
                current_minute=time.localtime()[4] #將current_minute設定為目前時間。以上兩行確保下列區塊每分鐘只執行一次
                one_min_weight=''  
                one_min_weight=get_data()   #抓重量，因發現get_data基本上已經可以取得可用數字，試試看只抓一次
                if one_min_weight !='': #有抓到的話  
                    weight_FLUID.append(one_min_weight)
                #    for i in range(0,len(one_min_weight),1):
                #        if one_min_weight[i]==-999.9:
                #            del one_min_weight[i]
                #        else:
                #            pass
                #    if np.max(one_min_weight)-np.min(one_min_weight) <= 5:
                #        weight_FLUID.append(round(np.mean(one_min_weight)))#賦值
                #    else:
                #        weight_FLUID.append(round(statistics.median(one_min_weight)))#賦值
   #接著判斷是否有異常
                    if one_min_abn <3:
                        if len(weight_FLUID) > 2:        #已有兩分鐘以上的數字
                            if weight_FLUID[-1]-weight_FLUID[-2]>50:     #兩次一分鐘重量相差超過50克
                                weight_FLUID[-1]=weight_FLUID[-2]        #把最新加進去的那個替換成舊值
                                one_min_abn = one_min_abn + 1
                            else:
                                pass
                        else:                            #目前這30分鐘區間僅有1~2個數字
                            if len(weight_PREVIOUS) > 0: #看看前一個30分鐘區間有沒有數字
                                if weight_FLUID[-1]-weight_PREVIOUS[-1]>50: #兩次相差超過50克
                                    weight_FLUID[-1]=weight_PREVIOUS[-1]     #把最新加進去的那個替換成舊值
                                    one_min_abn = one_min_abn + 1
                                else:
                                    pass
                            else:
                                pass
                    else: #if one_min_abn == 3: #當異常數字已經三次時
                        one_min_abn=0 #歸零，並認定本if區塊一開始的賦值結果
                        pass                    
                else: #if len(one_min_weight)==0: #沒有數值
                    if len(weight_FLUID)>0:
                        weight_FLUID.append(weight_FLUID[-1]) #直接帶入上一個分鐘的
                    elif len(weight_FLUID)==0 and len(weight_PREVIOUS)>0:
                        weight_FLUID.append(weight_PREVIOUS[-1]) #直接帶入上一個分鐘的
                    else:
                        weight_FLUID.append(0) #都非上面情況，則加0

#處理要存的資料
                #weight_raw_string=",".join(str(element) for element in one_min_weight)
                adjusted_time=time.time()+delta_timestamp
                #weight_RAW.append(weight_raw_string)
                time_INDEX.append(str(datetime.fromtimestamp(adjusted_time))[:16])#改成用調整時間（前16個字元）加入時間記錄主串列time_INDEX
                DISPLAY('10min',"最近十分鐘尿量:"+str(round(five_weight_change))) #去畫圖
                time.sleep(5)
                DISPLAY('',one_min_weight) #去畫圖
            #plot_scatter(weight_FLUID[-1]) #去畫圖
                one_min_weight=[]
#留35秒時間

    
#每10分鐘以最近十個數據，利用回歸分析判斷趨勢與估計尿量。
                if time.localtime()[4] in period_minute and len(weight_FLUID) >= 11:        #先計算最近十分鐘的總重量變化
                    five_weight_change=calculate_weight_changes(10) #呼叫。取倒數10個計算重量變化 
                    urine_amount.append(five_weight_change)                    
                    five_regression=calculate_regression(weight_FLUID,10)   #利用重量變化計算趨勢與估計未來尿量，評估趨勢（至少10個的時候才跑回歸計算趨勢）
                    if five_regression[1] < 0:
                        DISPLAY('',"最近十分鐘尿量:"+str(round(five_weight_change))+"趨勢：減少")
                    else:
                        DISPLAY('',"最近十分鐘尿量:"+str(round(five_weight_change))+"趨勢：穩定或增加") 
                else:
                    pass

#每59分或29分紀錄總尿量。為了簡化，有考慮一小時存一次即可
                if time.localtime()[4]  == 59 and len(weight_FLUID) >= 1:
                    processed_data=saving_data(time_INDEX,weight_FLUID,59) #~存檔~
                    time_INDEX=processed_data[0]      #留下縮減過的資料串列
                    weight_FLUID=processed_data[1]    #留下縮減過的資料串列
                    weight_PREVIOUS=processed_data[2] #已經存入的資料串列
                    #weight_RAW=processed_data[3]
                    pass
                elif time.localtime()[4]  == 29 and len(weight_FLUID) >= 1:
                    processed_data=saving_data(time_INDEX,weight_FLUID,29)
                    time_INDEX=processed_data[0]
                    weight_FLUID=processed_data[1]
                    weight_PREVIOUS=processed_data[2]
                    #weight_RAW=processed_data[3]
                    pass
                else:
                    pass
#本分鐘應做的事情全做完                
#                time.sleep(1.5) #等1.5秒（這樣下一秒絕對不會是00）
                pass
               
            else:
                time.sleep(0.1)
                pass
#.............................................................#
        #except Warning:
            #raise
        except ZeroDivisionError:
            print('估計可能不準')
        #except Exception:
            #raise
############################################################################################################################################

if __name__ == '__main__':
    #OPEN_SERIAL() #開啟序列埠，本來想寫成def，但後面flush 的地方發生錯誤
    ports = list(serial.tools.list_ports.comports()) #重設輸入的方法之一，就是重新開port。因擔心真的有讀碼異常的情形，故將這一段寫成def
    for port in ports:
        if port.manufacturer.startswith( "Arduino" ):
            COM_PORT = '/dev/'+port.name
        else:
            continue    
    message_text.config(x=1,y=302, font_size=10,text="Modules imported. Port: "+COM_PORT)
    arduinoSerial = serial.Serial(COM_PORT, BAUD_RATES) #開啟port

    start_time=time.localtime()
    time.sleep(0.1)
    RESULT=INPUT()  #輸入病歷號
    file_name=RESULT+'.csv'
    message_text.config(x=1,y=302, font_size=10,text='file:'+file_name)
    delta_timestamp=DELTA_TIME() #輸入現在時間
    
    #warnings.filterwarnings('ignore', module="numpy")
    #warnings.filterwarnings('ignore', message='invalid value encountered in scalar divide')
    #warnings.filterwarnings('ignore', message='invalid value encountered in divide')
    gui.on_key_click('a',on_click)#按A鍵結束
    gui.on_key_click('b',on_click)


    main()
    gui.clear
    good_bye()
    print('Olulu ver. 0.11b. A or B Button pressed.')
    sys.exit(0)
