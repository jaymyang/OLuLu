# On Line urine Lever urility ver 0.12
#本版為0.11d版的簡化版，去掉複雜的異常值除去機制，改成利用數字偏差與取眾數，最後與上一分鐘相比

print("Olulu PC　ver. 0.12 is starting up.")

#模組
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
import signal
#-----------以下為針對不同平台帶入的各種GUI
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


import tkinter as tk
from tkinter import ttk
from threading import *


#from unihiker import GUI   # Unihiker GUI package
#gui = GUI() 
#startup_img = gui.draw_image(x=0, y=0,w=240, h=300,image='../upload/pict/Copyright-1.png')
#txt=gui.draw_text(text="",x=120,y=10,font_size=12,origin="center",color="#0000FF")
#message_text=gui.draw_text() #
#-----------------------------
# Initialize variables
fprop = fm.FontProperties(fname='NotoSansTC-VariableFont_wght.otf')
global display_text,action, YEAR_action,MONTH_action,DAY_action,HOUR_action,MINUTE_action,Yr,Mo,D,Hr,Min,modify_time,delta_timestamp
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
COM_PORT = 'COM5'
BAUD_RATES = 9600
file_name = ''

#使用者輸入目前時間所用的變數
Yr=2024
Mo=6
D=15
Hr=12
Min=30

##########################################################################################################
def threading(): 
    # Call work function 

    t2=Thread(target=main)
    t2.start()
    t1=Thread(target=DISPLAY) 
    t1.start()
# Function to plot scatter plot
##########################################################################################################
#以下是監測重量時的顯示函式
def DISPLAY(self,action_in,weight_fluid,weight_previous,message_in):
    self=tk
    self.geometry ('400x400')
    global display_text
    self.message1=weight_fluid    #用message1代替weight_FLUID，免得破壞主資料陣列
    self.message2=weight_previous #用message2代替weight_PREVIOUS，免得破壞主資料陣列
    self.message3=message_in
    if self.message2==[]: #第一輪沒有weight_PREVIOUS，所以只需要顯示weight_FLUID
        weight_plot=self.message1
    else:
        weight_plot=self.message2[-23:]+self.message1 #合併已存檔的資料（放在前，只取最後23個是因為預留空間給標籤）與新收的資料（在後）；0為最舊的資料，最後一個是最新的資料。
    weight_plot=weight_plot[-56:] #不管如何只取後55個來畫
    x_cor = np.arange(0,len(weight_plot)-1,1)
    x_cor=x_cor[::-1] #逆轉順序以供繪圖
    if np.max(weight_plot) < 350: #
        scale=1.25
        color_code='orange'
    else:
        scale=2.5
        color_code='blue'
        
    DRAW_LINE(self,weight_plot,scale,color_code,x_cor)
  

    self.mainloop()


    
#-------------------------------------------------------------
    #def DRAW_Y(scale,color_code,weight_plot):
        #for y_tick in range(300,0,-20): #座標點
        #    y_axis_label=gui.draw_text(x=10,y=y_tick, text=round(scale/2.5*(650-2.5*y_tick)), color='black', origin='center',font_size=6)
        #for x_tick in range(238,37,-40): #座標點
        #    x_axis_label=gui.draw_text(x=x_tick,y=265, text=str(int(x_tick/4-60)), color='black', origin='center',font_size=8)

    #    for i in range(0,len(weight_plot)-1,1):
    #        if weight_plot[i] < 0:#負值用黑線繪圖；照講寬度應該是要留4
    #            data_line=canvas.create_line(238-4*x_cor[i],260,238-4*x_cor[i],round(260-weight_plot[i]/scale)-1,width=3, fill="black") 
    #        else:#正值依照scale選顏色 
    #            data_line=canvas.create_line(238-4*x_cor[i],260,238-4*x_cor[i],round(260-weight_plot[i]/scale)-1,width=3, fill=color_code)
    #    canvas.pack()
    #    time.sleep(0.1)
#-------------------------------------------------------------  
class DRAW_LINE(ttk.Frame):
    def __init__(self, parent,weight_plot,scale,color_code,x_cor):
        super().__init__()
        self.canvas = tk.Canvas(parent, width=240, height=320)

        for yn in range(20,300,20): #畫出格線
            self.canvas.create_line(0,yn,240,yn,width=1, fill='#0a0', dash=(1,1))
        for xn in range(20,240,20):
            self.canvas.create_line(xn,0,xn,300,width=1, fill='#0a0', dash=(1,1))
        x_axis=self.canvas.create_line(20, 260, 240, 260, width=1, fill='black')#繪0參考線
        for i in range(0,len(weight_plot)-1,1):
            if weight_plot[i] < 0:#負值用黑線繪圖；照講寬度應該是要留4
                data_line=self.canvas.create_line(238-4*x_cor[i],260,238-4*x_cor[i],round(260-weight_plot[i]/scale)-1,width=3, fill="black")
            else:#正值依照scale選顏色 
                data_line=self.canvas.create_line(238-4*x_cor[i],260,238-4*x_cor[i],round(260-weight_plot[i]/scale)-1,width=3, fill=color_code)

        self.canvas.pack()
    #root.pack()
    #canvas.pack()  
    #canvas.y_grid=y_grid
    #canvas.x_grid=x_grid
    
    
    #if np.max(weight_plot) < 350: #改變Y的scale
    #    for i in range(0,len(weight_plot)-1,1):
    #        if weight_plot[i] < 0:#負值用黑線繪圖；照講寬度應該是要留4
    #            data_line=canvas.create_line(238-4*x_cor[i],260,238-4*x_cor[i],round(260-weight_plot[i]/1.25)-1,width=3, fill="black")
    #            canvas.pack()  
    #        else:#正值依照scale選顏色
    #            data_line=canvas.create_line(238-4*x_cor[i],260,238-4*x_cor[i],round(260-weight_plot[i]/1.25)-1,width=3, fill='orange')
    #            canvas.pack()  

    #else:
    #    for i in range(0,len(weight_plot)-1,1):
    #        if weight_plot[i] < 0:#負值用黑線繪圖；照講寬度應該是要留4
    #            data_line=canvas.create_line(238-4*x_cor[i],260,238-4*x_cor[i],round(260-weight_plot[i]/2.5)-1,width=3, fill="black")
    #            canvas.pack()  
    #        else:#正值依照scale選顏色 
    #            data_line=canvas.create_line(238-4*x_cor[i],260,238-4*x_cor[i],round(260-weight_plot[i]/2.5)-1,width=3, fill='blue')
    #            canvas.pack()  

     

    #if message3=='':
    #    message3=display_text #display_text是用來再現先前所顯示的內容
    #else:
    #    pass
    #message_text=gui.draw_text(x=1,y=302, font_size=10,text=message3)
    #display_text=message3
    #if action=='clean':
    #    canvas.delete('all')
    #canvas.delete('data_line')

    #time.sleep(0.1)
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
    arduinoSerial.reset_input_buffer()    
    while True:
        while arduinoSerial.in_waiting:          # 若收到序列資料…

            data_in = arduinoSerial.readline() #得到的type為string；Arduino只傳資料頭識別碼(A)、整數、'\n'。由於舊版讀數仍有異常，決定用笨方法。
            if b'\n' in data_in:
                if str(data_in.decode('utf-8')[0]) !='A':
                    pass
                else:
                    data_temp=str(data_in.decode('utf-8').rstrip())#解碼；用rstrip()去掉末尾
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
    print('weight_temp',weight_temp)    
    return weight_temp
    

def get_weight(): 
    count=0
    return_data=[]
    while True:
        if count >10:
            break
        else:
            weight_data=get_data()
            time.sleep(0.01)
            arduinoSerial.write(str(weight_data).encode(encoding='utf-8'))
            time.sleep(0.01)
            T_F = arduinoSerial.readline().decode('utf-8').rstrip()
            if T_F =='T':
                
                pass
            else:
                weight_data=999.9
            if weight_data=='': #抓到了個空
                weight_data=-999.9 #因為序列埠只回傳整數，所以故意設定為小數
            elif weight_data=='-': #只抓到負號沒有數字
                weight_data=-999.9
            elif weight_data <-1000 or weight_data >3000:
                weight_data=-999.9
            else:
                pass
        return_data.append(weight_data)
        count=count+1
    print('return_data',return_data)
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
                print("可能有突減大量:"+str(weight_sum))#提醒使用者可能有誤差                               
            weight_sum=weight_max-weight_min
            if small_volume<10:#這裡是預設在一個尿量波動很小的範圍的時候，直接用最大值減最小值來估計就好。不管每5分鐘或每小時，都用10gm
                weight_Sum=small_volume
    print("小計:"+str(weight_sum))
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
            print("30分鐘重量變化："+ str(round(hour_weight_change)) +' ；存檔完成')
            
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
    raise KeyboardInterrupt()

########################################################################################################################  
#主函式
def main():


    #以下開始
    while True:
        
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複
            #if action=="clean": #按下A或B的時候，停止main()的執行，進入程式結束階段。這也是為什麼在執行到這裡之前按下A/B都不會有反應。
            weight_FLUID=[time.localtime()[5], time.localtime()[5]+1,time.localtime()[5]+2]
            weight_PREVIOUS=[35,45,55]
            one_min_weight=[6,6,6,6,6]
            t1=threading.Thread(target=DISPLAY, args=['',weight_FLUID, weight_PREVIOUS, one_min_weight]) #去畫圖
            t1.start()
            time.sleep(0.1)

        except Warning:
            raise
        except ZeroDivisionError:
            print('估計可能不準')
        except Exception:
            raise
############################################################################################################################################

if __name__ == '__main__':
    

    t2=Thread(target=main)
    t2.start()
    signal.signal(signal.SIGINT,good_bye)
    print('Olulu ver. 0.11b. A or B Button pressed.')
    sys.exit(0)
