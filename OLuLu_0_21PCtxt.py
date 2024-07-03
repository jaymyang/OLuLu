# On-Line urine Lever utility ver 0.2 TXT版
#1.傳輸資料改為一次全傳輸
#在Python 3.4版使用，必須配合Pyserial 2.7. (pip install pyserial==2.7)。會做出這個分枝，是因為Unihiker不支援Python 3.4版
print('         .*%%%+                                                                                     ')
print('     .%%%%%-===:%%%        %%%%%%%%%:                           .%%%%%%%%=                          ')
print('   =%%%%%%%-       %%.     %%%%%%%%%:                            %%%%%%%%=                          ')
print('  %%%%%%%%%-         %:    %%%%%%%%%:  %%%%%%%%%-   %%%%%%%%%=  .%%%%%%%%=  .%%%%%%%%-   .%%%%%%%%: ')
print(' %%%%%%%%%%-          %=   %%%%%%%%%:  %%%%%%%%%-   %%%%%%%%%=  .%%%%%%%%=   %%%%%%%%-    %%%%%%%%: ')
print(' %%%%%%%%%%-          #%=  %%%%%%%%%.  %%%%%%%%%:   %%%%%%%%%=  .%%%%%%%%=  .%%%%%%%%=   .%%%%%%%%: ')
print('-%%%%%%%%%%-           %=  %%%%%%%%%.  %%%%%%%%%.   %%%%%%%%%-  .%%%%%%%%=  .%%%%%%%%=    %%%%%%%%: ')
print('.%%%%%%%%%%-          .%=  %%%%%%%%%.  %%%%%%%%%.   %%%%%%%%%-   %%%%%%%%=  .%%%%%%%%=   .%%%%%%%%- ')
print(' %%%%%%%%%%-          %%=  %%%%%%%%#   %%%%%%%%%.   %%%%%%%%%-  .%%%%%%%%=  .%%%%%%%%=   .%%%%%%%%- ')
print('  %%%%%%%%%-         %%=   %%%%%%%%%.  %%%%%%%%%.   %%%%%%%%%-  .%%%%%%%%=   %%%%%%%%=   .%%%%%%%%- ')
print('   %%%%%%%%-        %%=    %%%%%%%%%.  %%%%%%%%%:   %%%%%%%%%-  .%%%%%%%%=   %%%%%%%%=   .%%%%%%%%- ')
print('    .%%%%%%-     +%%==     %%%%%%%%%:   %%%%%%%%*%%%%%%%%%%%%-  :%%%%%%%%=   %%%%%%%%%*%%+%%%%%%%%: ')
print('      .:%%%%%%%%%==.       %%%%%%%%%:    -%%%%%%%== %%%%%%%%%=  -%%%%%%%%=     #%%%%%%===.%%%%%%%%: ')


#模組
#GUI功能from unihiker import GUI   # Unihier GUI package
import sys #結束程式用
import time #時間模組
from datetime import datetime #轉換時間格式方便使用
import csv #讀寫csv檔
import numpy as np #數學運算用
import statistics
import serial #序列埠通訊
import serial.tools.list_ports #為了自動搜尋通訊埠。如果要加速程式，而且固定使用在Unihiker的話，這個功能可以拿掉
import warnings #為了避開有的沒的警告
#import warnings #為了避開有的沒的警告
from sklearn.linear_model import LinearRegression #回歸用
#import matplotlib.pyplot as plt
#import matplotlib.font_manager as fm
import signal
import math

# Initialize variables
#fprop = fm.FontProperties(fname='NotoSansTC-VariableFont_wght.otf')
global display_text,action, YEAR_action,MONTH_action,DAY_action,HOUR_action,MINUTE_action,Yr,Mo,D,Hr,Min,modify_time,delta_timestamp
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
def INPUT(item,range_L,range_U):
    input_data=input('請輸入現在'+item+'：')
    while True:
        if input_data.isdigit()==False:
            input_data=int(input('請輸入現在'+item+'：'))
        else:
            input_data=int(input_data)
            break
    while True:
        if int(input_data) not in range(range_L,range_U):
            input_data=int(input('請輸入現在'+item+'：'))
        else:
            break
    return input_data

##########################################################################################################

# Function to plot scatter plot，注意這裡是用字元顯示。
def plot_scatter(Data):
    #global weight_FLUID,weight_PREVIOUS
    #weight_plot=weight_PREVIOUS+weight_FLUID
    block_base=math.floor(int(Data)/200)
    #看看有幾個200，因為打算把每個字元代表2
    blocks_No=round((int(Data)-block_base*200)/2) #視窗開到最大。如果空間足夠，可以設得更小。
    if len(str(Data))<4:
        Data=str(Data)+' '*(4-len(str(Data))) #補空白對齊
    if block_base==0:
        print(time.localtime()[3],':',time.localtime()[4],'=',Data,'   '+'|'+chr(2593) * blocks_No)
    else:
        print(time.localtime()[3],':',time.localtime()[4],'=',Data,str(block_base*200)+'|'+chr(2593) * blocks_No)
    #x = np.arange(len(weight_plot))
    #plt.scatter(x, weight_plot, c='g', marker='>')
    #plt.title(Title)
    #plt.xlim([0, 60])
    #plt.show(block=False)
    #plt.pause(0.1)

#############################--ARDUINO--############################################
# Function to get data from Arduino
def get_weight():
	python_order='1' #1為預設啟動值，2表示需要重設
	getting_times=0
	arduinoSerial.flushInput()
    
	def check_data(original_weight):
    	abnormal_val=0
    	for i in range(0,len(original_weight),1):
        	if original_weight[i] < 0: #因為這個判斷式很重要，所以分開寫
            	abnormal_val=abnormal_val+1
        	elif original_weight[i] > 350:           	 
            	abnormal_val=abnormal_val+1
        	else:
            	pass
    	return abnormal_val
    
	def getting_data(python_order):
    	data_temp=[]
    	weight_temp=''
    	arduinoSerial.write(python_order.encode(encoding='utf-8')) #發送指令給Arduino開始抓重量
    	while True:
        	while arduinoSerial.inWaiting():      	# 若收到序列資料…
            	data_in = arduinoSerial.readline() #得到的type為string；Arduino只傳資料頭識別碼(A)、整數、'\n'。由於舊版讀數仍有異常，決定用笨方法。
            	if b'\n' in data_in: #確定有取得資料尾
                	if str(data_in.decode('utf-8',errors='ignore')[0]) !='A': #沒有取到資料頭，放棄
                    	pass
                	else:                                 	#取得資料頭後，逐字取碼不解碼
                    	for j in range(0,len(data_in),1):
                        	if data_in.decode('utf-8',errors='ignore')[j] not in [',','-','1','2','3','4','5','6','7','8','9','0']:
                            	pass                                    	#為安全起見，讀到其他字符就pass
                        	elif data_in.decode('utf-8',errors='ignore')[j] in ['-','1','2','3','4','5','6','7','8','9','0']:
                            	weight_temp=weight_temp+data_in.decode('utf-8')[j]   #理論上應可組合成數字
                        	elif data_in.decode('utf-8',errors='ignore')[j]== ',':               	#讀到逗點，就結束這個數字
                            	if weight_temp != '':                   	#如果不是空的字串
                                	data_temp.append(int(weight_temp)) #轉換為整數
                                	weight_temp=''                      	#重設
                            	else:
                                	pass
                        	else:
                            	pass
                    	break #結束，跳出迴圈           	 
            	else:     	#沒有取得資料尾，無效
                	time.sleep(0.01)
                	pass
        	if len(data_temp) > 0:         	 
            	break              	#結束，跳出迴圈
        	else:
            	weight_temp='' #清空
            	pass
    	arduinoSerial.flushOutput()
    	return data_temp

	while True:
    	while getting_times < 3:
        	original_weight=getting_data(python_order)
        	abnormal_val=check_data(original_weight)
        	if abnormal_val <=3 : #回傳的10個數字裡面只有不到3個有問題，應該可以由變異值去除機制處理
            	break
        	else:          	#回傳的數字有問題
            	python_order='2' #1為預設啟動值，2表示需要重設
            	getting_times=getting_times+1
            	print(getting_times) #追蹤用
            	pass
    	break
	return original_weight

############################--STATISTICS--#####################################
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
                #print('可能有突減大量:'+str(weight_sum))#提醒使用者可能有誤差                               
            weight_sum=weight_max-weight_min
            if small_volume<10:#這裡是預設在一個尿量波動很小的範圍的時候，直接用最大值減最小值來估計就好。不管每5分鐘或每小時，都用10gm
                weight_Sum=small_volume
    print('小計:'+str(weight_sum))
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
        time_marker = time.strftime('%Y-%m-%d, %H:%M')

        saving_time_upper = [t for t in saving_time if int(t[-2:]) < 30]#表示這是00-29分的資料，放進上半。t指time，w指weight
        saving_weight_upper = [w for t, w in zip(saving_time, saving_weight) if int(t[-2:]) < 30] #把兩個串列裡相同位置的元素配在一起
        saving_raw_upper = [r for t, r in zip(saving_time, saving_raw) if int(t[-2:]) < 30] #把兩個串列裡相同位置的元素配在一起
        saving_time_lower = [t for t in saving_time if int(t[-2:]) >= 30]#不然就是30-59分的資料，歸在下半
        saving_weight_lower = [w for t, w in zip(saving_time, saving_weight) if int(t[-2:]) >= 30]
        saving_raw_lower = [r for t, r in zip(saving_time, saving_raw) if int(t[-2:]) >= 30] #把兩個串列裡相同位置的元素配在一起

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
            #print('file_weight:'+file_weight)
            for save_time, save_weight, save_raw in zip(file_time, file_weight, file_raw):
                wt.writerow([save_time, save_weight, save_raw])
            print('30分鐘重量變化：'+ str(round(hour_weight_change)) +' ；存檔完成')
            
        return saving_time, saving_weight,file_weight, saving_raw

#def on_click(): #所有的PC版用不到這個
#    global action
#    action='clean'
    
def good_bye(): #按ctrl-C結束    
    with open(file_name, 'a', newline='') as csvfile:
        wt = csv.writer(csvfile)
        for save_time, save_weight, save_raw in zip(time_INDEX,weight_FLUID, weight_RAW):
            wt.writerow([save_time, save_weight, save_raw])

    print('Data saved as: '+file_name+'. Good Bye~')
    sys.exit(0)
    #raise KeyboardInterrupt()


####################主函式####################
def main():
    global weight_FLUID, time_INDEX, arduinoSerial, file_name,time_stamp,weight_PREVIOUS, display_text, delta_timestamp, weight_RAW, urine_amount
    adjusted_time=time.time()+delta_timestamp
    initial_weight_temp=get_weight() #這個跟下一行刪掉，也無妨
    print(str(datetime.fromtimestamp(adjusted_time))[:16]+' 初始值:'+str(initial_weight_temp))
    #改用調整時間，判斷如果是29分或59分的時候，等一分鐘以後再開始
    if datetime.fromtimestamp(adjusted_time).minute== 29 or 59: #剛好這兩個時間點的時候，寧可等一分鐘再開始，以免存個空陣列
        time.sleep(60)
    current_minute = 61
    five_weight_change=0
    current_second = None
    weight_PREVIOUS=[]
    one_min_abn=0
#**********開始*********#
    while True:
        if action=="clean": #按下A或B的時候，停止main()的執行，進入程式結束階段。
            break        
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複
            if time.localtime()[4] != current_minute: #time.localtime[4]不等於current_minute時，表示是新的一分鐘
                current_minute=time.localtime()[4] #將current_minute設定為目前時間。以上兩行確保下列區塊每分鐘只執行一次
                getting_weight=get_weight()
                if len(getting_weight)>0: #有抓到的話
                    if np.max(getting_weight)-np.min(getting_weight) <= 5:
                        weight_FLUID.append(round(np.mean(getting_weight)))#賦值，10秒之中取得的數字變異不大，取平均
                    else:
                        weight_FLUID.append(round(statistics.median(getting_weight)))#賦值，10秒之中取得的數字變異較大，取中位數
#********處理異常值********#
                    if one_min_abn <3: #就是沒什麼異常值的時候
                        if len(weight_FLUID) > 2: #但這樣的作法，有可能在剛開始使用時，原先為0然後掛上尿袋，卻因為大於50克被hold住，到了連續三次以後才被寫入，但外表看來就是從零跳到一兩百
                            if weight_FLUID[-1]-weight_FLUID[-2]>50: #一分鐘重量相差超過50克
                                weight_FLUID[-1]=weight_FLUID[-2] #直接在這邊處理，把最新加進去的那個替換成舊值
                                one_min_abn = one_min_abn + 1
                            else:#沒有過大差距
                                pass
                        else: #每30分鐘區段開始的時候
                            if len(weight_PREVIOUS) > 0:
                                if weight_FLUID[-1]-weight_PREVIOUS[-1]>50: #兩次相差超過50克
                                    weight_FLUID[-1]=weight_PREVIOUS[-1] #直接在這邊處理，把最新加進去的那個替換成舊值
                                    one_min_abn = one_min_abn + 1
                                else:#沒有過大差距
                                    pass 
                            else:#沒有舊值
                                pass #這種情形是沒有舊值且現在也只有一兩個，就是最初剛開始。pass就是不替換，直接把數字放進去
                    elif one_min_abn == 3: #
                        one_min_abn=0
                        pass
                else: #if len(one_min_weight)==0: #沒有數值
                    if len(weight_FLUID)>0:
                        weight_FLUID.append(weight_FLUID[-1]) #直接帶入上一個分鐘的
                    elif len(weight_FLUID)==0 and len(weight_PREVIOUS)>0:
                        weight_FLUID.append(weight_PREVIOUS[-1]) #直接帶入上一個分鐘的
                    else:
                        weight_FLUID.append(0) #都非上面情況，則加0

#*****處理存檔資料*****#
                weight_raw_string= getting_weight #原始資料，用於開發用
                adjusted_time=time.time()+delta_timestamp
                weight_RAW.append(weight_raw_string)
                time_INDEX.append(str(datetime.fromtimestamp(adjusted_time))[:16])#改成用調整時間（前16個字元）加入時間記錄主串列time_INDEX
                #print('weight_RAW',weight_raw_string)
                #print("最近十分鐘尿量:"+str(round(five_weight_change))) #去畫圖
                #time.sleep(5)              #圖顯示5秒        
                #DISPLAY('',getting_weight) #去畫圖 
                plot_scatter(weight_FLUID[-1]) #去畫圖
#考慮到PC版的顯示美觀問題，將來或許取消下面的資料顯示
        #每10分鐘以最近十個數據，利用回歸分析判斷趨勢與估計尿量。
                if time.localtime()[4] in period_minute and len(weight_FLUID) >= 11:        #先計算最近十分鐘的總重量變化
                    five_weight_change=calculate_weight_changes(10) #呼叫。取倒數10個計算重量變化
        #利用重量變化計算趨勢與估計未來尿量
                    #urine_amount.append(urine_amount[-1]+five_weight_change) #其他繪圖版本使用
                    five_regression=calculate_regression(weight_FLUID,10)   #呼叫。以每分鐘重量差，評估趨勢（至少10個的時候才跑回歸計算趨勢）
                    if five_regression[1] < 0:
                        print('最近十分鐘尿量:'+str(round(five_weight_change))+'趨勢：減少')
                    else:
                        print('最近十分鐘尿量:'+str(round(five_weight_change))+'趨勢：穩定或增加') 

#每59分或29分紀錄總尿量。為了簡化，有考慮一小時存一次即可
                if time.localtime()[4]  == 59 and len(weight_FLUID) >= 1:
                    processed_data=saving_data(time_INDEX,weight_FLUID,59,weight_RAW) #~存檔~
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
#本分鐘應做的事情全做完                
#                time.sleep(1.5) #等1.5秒（這樣下一秒絕對不會是00）
                #pass
                #current_minute=time.localtime()[4] #將current_minute設定為目前時間。以上兩行確保下列區塊每分鐘只執行一次
            else:
                time.sleep(0.5)
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
    COM_PORT = 'COM5'

    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if port.manufacturer.startswith('Arduino'):
            COM_PORT = port.name
            print('Arduino device found on ' + COM_PORT)
    arduinoSerial = serial.Serial(COM_PORT, BAUD_RATES)
    

    file_name = input('請輸入病歷號：') + '.csv'
    Yr=input('請輸入現在年：')
    Mo=input('請輸入現在月：')
    D=input('請輸入現在日：')
    Hr=input('請輸入現在時：')
    Min=input('請輸入現在分：')
    current_time=str(Hr)+':'+str(Min)+' '+str(Mo)+' '+str(D)+' '+str(Yr)
    delta_time=time.mktime(time.strptime(current_time,'%H:%M %m %d %Y'))
    #warnings.filterwarnings('ignore', module='matplotlib')
    #warnings.filterwarnings('ignore', message='invalid value encountered in scalar divide')
    #warnings.filterwarnings('ignore', message='invalid value encountered in divide')

    main()
    signal.signal(signal.SIGINT,good_bye)
    print('Olulu ver. 0.20. Ctrl-C pressed.')
    sys.exit(0)
