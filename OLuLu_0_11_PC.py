# On Line urine Lever urility ver 0.11 本版為0.11d版的簡化版，去掉複雜的異常值除去機制，改成利用數字偏差與取眾數，最後與上一分鐘相比

print("Olulu PC　ver. 0.11 is starting up.")

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
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import signal


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

# Function to plot scatter plot
def plot_scatter(Title):
    global weight_FLUID,weight_PREVIOUS
    weight_plot=weight_PREVIOUS+weight_FLUID
    x = np.arange(len(weight_plot))
    plt.scatter(x, weight_plot, c='g', marker='>')
    plt.title(Title)
    plt.xlim([0, 60])
    plt.show(block=False)
    plt.pause(0.1)

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
def get_weight(): #秤重
    data_temp=''
    weight_temp=''
    arduinoSerial.reset_input_buffer()
    for i in range (0,100,1): #頂多抓個100次
        data_in = arduinoSerial.readline() #得到的type為string；Arduino只傳資料頭識別碼(A)、整數、'\n'。由於舊版讀數仍有異常，決定用笨方法。
        if b'\n' in data_in:
            if str(data_in.decode('utf-8')[0])=='A':
                data_temp=str(data_in.decode('utf-8').rstrip())#解碼；用rstrip()去掉末尾
                for j in range(len(data_temp)):
                    if data_temp[j] in ['-','1','2','3','4','5','6','7','8','9','0']:
                        weight_temp=weight_temp+data_temp[j] #組合起來                   
                    else:
                        pass
                break
        else:
            time.sleep(0.1) #
            pass
            
    if weight_temp=='': #抓到了個空
        weight_temp=-999.9 #因為序列埠只回傳整數，所以故意設定為小數
    elif weight_temp=='-': #只抓到負號沒有數字
        weight_temp=-999.9
    else:
        weight_temp=int(weight_temp) #數字太離譜
        if weight_temp <-1000 or weight_temp >3000:
            weight_temp=-999.9
        else:
            pass
    print('weight_temp',weight_temp)

    return weight_temp
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
    global weight_FLUID, time_INDEX, arduinoSerial, file_name,time_stamp,weight_PREVIOUS, display_text, delta_timestamp, weight_RAW
    adjusted_time=time.time()+delta_timestamp
    time_INDEX.append(str(datetime.fromtimestamp(adjusted_time))) #改成用調整時間
    initial_weight_temp=get_weight()
    weight_FLUID.append(initial_weight_temp)
    if weight_FLUID[0]=='NaN':
        weight_FLUID[0]=0
        
    weight_RAW.append(initial_weight_temp) #為了填補數據用的暫時數據，無妨。
    print(time_INDEX[0][:16]+' 初始值:'+str(weight_FLUID[0]))
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
    one_min_abn=0

    #以下開始
    while True:                    
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複
            if action=="clean": #按下A或B的時候，停止main()的執行，進入程式結束階段。這也是為什麼在執行到這裡之前按下A/B都不會有反應。
                break
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
                if time.localtime()[5] ==11 and weight_flag==0 and len(one_min_weight)>0:
                    weight_flag==1
                    if np.max(one_min_weight)-np.min(one_min_weight) <= 5:
                        weight_FLUID.append(round(np.mean(one_min_weight)))
                    else:
                        weight_FLUID.append(statistics.median(one_min_weight))
                        pass
                    if one_min_abn <3:
                        if len(weight_FLUID) > 2: 
                            if weight_FLUID[-1]-weight_FLUID[-2]>50: #兩次相差超過50克
                                weight_FLUID[-1]=weight_FLUID[-2] #直接在這邊處理，把最新加進去的那個替換成舊值
                                one_min_abn=one_min_abn=+1
                            else:
                                pass#不然就算了
                        else:
                            if len(weight_PREVIOUS) > 0:
                                if weight_FLUID[-1]-weight_PREVIOUS[-1]>50: #兩次相差超過50克
                                    weight_FLUID[-1]=weight_PREVIOUS[-1] #直接在這邊處理，把最新加進去的那個替換成舊值
                                    one_min_abn=one_min_abn=+1
                                else:
                                    pass#不然就算了
                            else:
                                pass#不然就算了
                            
                    else:
                        one_min_abn=0
                        pass

                    weight_raw_string=",".join(str(element) for element in one_min_weight)
                    adjusted_time=time.time()+delta_timestamp
                    weight_RAW.append(weight_raw_string)
                    time_INDEX.append(str(datetime.fromtimestamp(adjusted_time))[:16])#改成用調整時間（前16個字元）加入時間記錄主串列time_INDEX
                    #print(weight_FLUID)
                    plot_scatter('繪圖中') #去畫圖
                    one_min_weight=[]


        #每5分鐘以最近十個數據，利用回歸分析判斷趨勢與估計尿量。
                if time.localtime()[4] in period_minute and len(weight_FLUID) >= 11:        #先計算最近十分鐘的總重量變化
                    five_weight_change=calculate_weight_changes(10) #呼叫。取倒數10個計算重量變化
        #利用重量變化計算趨勢與估計未來尿量
                    five_regression=calculate_regression(weight_FLUID,10)   #呼叫。以每分鐘重量差，評估趨勢（至少10個的時候才跑回歸計算趨勢）
                    if five_regression[1] < 0:
                        print("最近十分鐘尿量:"+str(round(five_weight_change))+"趨勢：減少")
                    else:
                        print("最近十分鐘尿量:"+str(round(five_weight_change))+"趨勢：穩定或增加") 

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
    COM_PORT = 'COM5'
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if port.manufacturer.startswith("Arduino"):
            COM_PORT = port.name
            print("Arduino device found on " + COM_PORT)
    arduinoSerial = serial.Serial(COM_PORT, BAUD_RATES)
    file_name = input('請輸入病歷號：') + '.csv'
    Yr=input('請輸入現在年：')
    Mo=input('請輸入現在月：')
    D=input('請輸入現在日：')
    Hr=input('請輸入現在時：')
    Min=input('請輸入現在分：')
    current_time=str(Hr)+':'+str(Min)+' '+str(Mo)+' '+str(D)+' '+str(Yr)
    delta_time=time.mktime(time.strptime(current_time,"%H:%M %m %d %Y"))
    warnings.filterwarnings('ignore', module="matplotlib")
    #warnings.filterwarnings('ignore', message='invalid value encountered in scalar divide')
    #warnings.filterwarnings('ignore', message='invalid value encountered in divide')

    main()
    signal.signal(signal.SIGINT,good_bye)
    print('Olulu ver. 0.11b. A or B Button pressed.')
    sys.exit(0)
