# On Line urine Lever urility ver 0.12
#本版為0.11d版的簡化版，去掉複雜的異常值除去機制，改成利用數字偏差與取眾數，最後與上一分鐘相比

print("Olulu PC　ver. 0.12 is starting up.")

#模組
import sys #結束程式用
import time #時間模組
from datetime import datetime #轉換時間格式方便使用


import numpy as np #數學運算用


import signal
#-----------以下為針對不同平台帶入的各種GUI



import tkinter as tk
from tkinter import ttk
import threading
from threading import *
from queue import Queue

#from unihiker import GUI   # Unihiker GUI package
#gui = GUI() 
#startup_img = gui.draw_image(x=0, y=0,w=240, h=300,image='../upload/pict/Copyright-1.png')
#txt=gui.draw_text(text="",x=120,y=10,font_size=12,origin="center",color="#0000FF")
#message_text=gui.draw_text() #
#-----------------------------
# Initialize variables


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

# Function to plot scatter plot
##########################################################################################################
#以下是監測重量時的顯示函式
class DISPLAY(tk.Tk):
    def __init__(self,action,weight_fluid,weight_previous,message_in):
        self=tk.Tk()
        self.title('test')
        self.geometry ('240x320')
        global display_text
        self.message1=weight_fluid    #用message1代替weight_FLUID，免得破壞主資料陣列
        self.message2=weight_previous #用message2代替weight_PREVIOUS，免得破壞主資料陣列
        self.message3=message_in
        #self.mainloop()
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
        print(action)
        if action > 0:
            self.destroy()
        else:
            pass
        self.canvas = tk.Canvas(width=240, height=320)
        x_axis=self.canvas.create_line(20, 260, 240, 260, width=1, fill='black')
        self.canvas.pack()
     

        self.mainloop()



    

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
        time.sleep(1)
        self.canvas.destroy()
        
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
    

#-------------------------------------------------------------------------------     

    
def good_bye(): #按A或B鍵結束    


    print('Data saved as: '+file_name+'. Good Bye~')
    raise KeyboardInterrupt()

def main_1():
    weight_FLUID=[time.localtime()[5], time.localtime()[5]+1,time.localtime()[5]+2]
    weight_PREVIOUS=[35,45,55]
    one_min_weight=[6,6,6,6,6]
    Queue().put(weight_FLUID,weight_PREVIOUS,one_min_weight)
    print('thread2')

########################################################################################################################  
#主函式
def main():
    current_second=0
    count_display=1


    #以下開始
    while True:        
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複
            if time.localtime()[5]!=current_second:
                current_second=time.localtime()[5]
                count_display=count_display+1
                t2=threading.Thread(target=main_1)
                t2.start()
                #if action=="clean": #按下A或B的時候，停止main()的執行，進入程式結束階段。這也是為什麼在執行到這裡之前按下A/B都不會有反應。
                print('thread1')
                queue_temp=Queue().get()
                print(queue_temp)
                weight_fluid=Queue().get()[0]
                weight_previous=t2[1]
                one_min_weight=t2[2]
                DISPLAY(count_display,weight_fluid, weight_previous, one_min_weight)

                #t1=threading.Thread(target=DISPLAY,args=[count_display,weight_FLUID, weight_PREVIOUS, one_min_weight])
                #t1.start() #去畫圖
            
            time.sleep(0.1)

        except Warning:
            raise
        except ZeroDivisionError:
            print('估計可能不準')
        except Exception:
            raise
############################################################################################################################################

if __name__ == '__main__':
    main()
    

    #signal.signal(signal.SIGINT,good_bye)
    print('Olulu ver. 0.11b. A or B Button pressed.')
    sys.exit(0)
