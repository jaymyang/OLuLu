import time
import csv
import numpy as np
from sklearn.linear_model import LinearRegression
import serial
import matplotlib.pyplot as plt
import winsound
import serial.tools.list_ports
import signal

# Initialize variables
arduinoSerial = None
period_second = [00,1,2,3,4,5,6,7,8,9,10]  #設定抓取序列埠傳入資料的時間（秒）
period_minute = [00,5,10,15,20,25,30,35,40,45,50,55]  #設定進行統計的時間（每5分鐘）
time_INDEX = []   #主時間戳記（每1分鐘）
weight_FLUID = [] #主重量紀錄串列
#以下為用於計算尿量與趨勢的串列與數值
analysis_wt= []
analysis_tmIn=[]
value_next=[]
weight_new=None
weight_old=None
mean=None
std_dev=None
time_stamp=time.time()

COM_PORT = 'COM5'
BAUD_RATES = 9600
file_name = ''

# Functions listed below
# Function to get weight from Arduino
def get_weight(data_flag):
    data_temp=''
    weight_temp=''
    making_sound(329, 50, 0.1, 1)
    for i in range(0,10,1):
        try:
            data_in = arduinoSerial.readline().decode('utf-8') #得到的type為string。這個要配合Aduino，只傳整數跟\n。不然就會藏一堆亂七八糟控制碼
            data_temp=int(data_in)
        except:
            data_temp=-999 #此時等01秒之後再抓一次
            i=i+1
            time.sleep(0.1)
            pass
    print('data_temp',data_temp)
    

    if data_temp < -100 and data_temp > -999: #表示可能有大減，應該要重設毛皮。
        making_sound(783,50,0.1,2) #提示音
        arduinoSerial.close()
        arduinoSerial.open() #重設serial
        weight_temp=0
        print('weight_temp<-100')
    elif data_temp ==-999: #如果跑完還是-999，表示本秒沒抓到
        making_sound(329,50, 0.1, 2)        
        pass
    else:
        weight_temp=data_temp
        making_sound(329,50, 0.1, 2)
    print('weight_temp',weight_temp)
    arduinoSerial.reset_input_buffer()
    return weight_temp,1


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
    if weight_FLUID !=[]:
        weight_max=weight_FLUID[-start_element] #先全部設成起始值
        weight_min=weight_FLUID[-start_element]
        weight_recent=weight_FLUID[-start_element:] #工作用串列
        small_volume=np.max(weight_FLUID[-start_element])-np.min(weight_FLUID[-start_element])
        for i, element in enumerate(weight_recent):
            if weight_recent[i]>weight_max: #一個一個比較
                if weight_recent[i]> (weight_max+1500): #一分鐘差1500克，可能有問題
                    pass
                else:
                    weight_max=weight_recent[i] #假如目前這個比前一個大，就把weight_max數值設為目前這個
                #print("一般情形",weight_sum)#debug追蹤程式進行用
            if weight_recent[i]<(weight_min+(weight_max-weight_min)/2): #發現突然減少（在上面那種小便很少的情形，不能一直進這個一直累加）
                weight_sum=weight_sum+weight_max-weight_min #之所以不能直接用< A_min，是考慮到有可能倒完以後的重量還是比空袋重，這樣就偵測不到了
                weight_max=weight_recent[i] #重設
                weight_min=weight_recent[i] #重設
                print("可能有突減大量",weight_sum) #提醒使用者可能有誤差                
            weight_sum=weight_max-weight_min
            if small_volume<10:#這裡是預設在一個尿量波動很小的範圍的時候，直接用最大值減最小值來估計就好。不管每5分鐘或每小時，都用10gm
                weight_Sum=small_volume
    print("小計",weight_sum)
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

# Function to plot scatter plot
def plot_scatter(Title):
    #print('weight_PREVIOUS',weight_PREVIOUS)
    plt.ion()
    #plt.show(block=False)
    plt.clf()
    weight_plot=weight_PREVIOUS+weight_FLUID #合併存檔的資料與新收的資料
    x = -np.arange(len(weight_plot))
    weight_plot.reverse() #反轉順序
    print('weight_plot',weight_plot)
    print('x axis',x)
    plt.title(Title)
    plt.xlim([-60, 0]) #最左邊是60
    #plt.ylim([-10, 1000])
    plt.scatter(x, weight_plot, c='g', marker='>')
    plt.pause(0.1)
    
    

# Function to save data
def saving_data(saving_time, saving_weight, cutting_index):
    if saving_weight:
        hour_weight_change = calculate_weight_changes(0)#從0開始算，該函式回傳數值weight_sum在此會放進hour_weight_change。
        time_marker = time.strftime("%Y-%m-%d, %H:%M")
        print(time_marker, "過去30分鐘重量變化：", hour_weight_change)#每30分的加總統計。

        saving_time_upper = [t for t in saving_time if int(t[-2:]) < 30]#表示這是00-29分的資料，放進上半
        saving_weight_upper = [w for t, w in zip(saving_time, saving_weight) if int(t[-2:]) < 30] #把兩個串列裡相同位置的元素配在一起
        saving_time_lower = [t for t in saving_time if int(t[-2:]) >= 30]#不然就是30-59分的資料，歸在下半
        saving_weight_lower = [w for t, w in zip(saving_time, saving_weight) if int(t[-2:]) >= 30]

        if cutting_index == 59:#59分的時候，保留30-59的資料，儲存00-29的資料
            file_time = saving_time_upper
            file_weight = saving_weight_upper
            saving_time = saving_time_lower
            saving_weight = saving_weight_lower
            print("59分的時候，保留30-59的資料，儲存00-29的資料")
        elif cutting_index == 29:#29分的時候，保留00-29的資料，儲存30-59的資料
            file_time = saving_time_lower
            file_weight = saving_weight_lower
            saving_time = saving_time_upper
            saving_weight = saving_weight_upper
            print("29分的時候，保留00-29的資料，儲存30-59的資料")
        with open(file_name, 'a', newline='') as csvfile:
            wt = csv.writer(csvfile)
            for save_time, save_weight in zip(file_time, file_weight):
                wt.writerow([save_time, save_weight])
            print("過去30分鐘數據存檔完成")
        return saving_time, saving_weight,file_weight

# Function to make sound#使用winsound取代print追蹤程式執行
def making_sound(frequency, duration, interrupt, repeat):
    for _ in range(repeat):
        winsound.Beep(frequency, duration)
        time.sleep(interrupt)
        
def initial_value():
    while True:
        try:
            initial_data_in = arduinoSerial.readline()
            initial_data = data_in.decode('utf-8') #得到的type為string
            initial_weight_temp=int(initial_data)
        except:
            initial_weight_temp=0
        making_sound(392,250,0.05,1)
        making_sound(392,250,0.05,1)
        making_sound(392,500,0.05,1)
        making_sound(261,250,0.05,1)
        making_sound(329,250,0.05,1)
        making_sound(392,250,0.05,1)
        return initial_weight_temp
        break
        
def good_bye(signum, frame): #按CTRLC結束
    with open(file_name, 'a', newline='') as csvfile:
        wt = csv.writer(csvfile)
        for save_time, save_weight in zip(time_INDEX,weight_FLUID):
            wt.writerow([save_time, save_weight])
    print('Data saved. Good Bye~')
    print('以下為PYTHON訊息')
    raise KeyboardInterrupt()

    

def main():
    global weight_FLUID, time_INDEX, arduinoSerial, file_name,time_stamp,weight_PREVIOUS
    time_INDEX.append(time.strftime("%Y-%m-%d %H:%M"))
    initial_weight_temp=initial_value()
    weight_FLUID.append(initial_weight_temp)
    print('初始值',weight_FLUID,time_INDEX)    
    
    if time.localtime()[4] == 29 or 59:
        time.sleep(60)

    current_minute = 61
    five_weight_change=10
    one_min_weight=-999
    #以下是設定比較回歸預測準確性所需的變數，預計在這個精簡版不會使用
    prediction_selection=None
    previous_prediction_15=[0,0]
    current_second = None
    weight_PREVIOUS=[]

    #以下開始
    while True:
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複
            if time.localtime()[4] != current_minute: #current_time代表以下程式區塊所執行的時間。time.localtime[4]不等於current_time時，表示是新的分鐘
                current_minute=time.localtime()[4] #將current_minute設定為目前時間。以上兩行確保下列區塊每分鐘只執行一次
                weight_flag=0
                one_min_weight=[]
                if time.localtime()[5] in period_second: #左述時間之秒，收集資料
                    one_sec_weight=get_weight(weight_flag)
                    weight_flag=one_sec_weight[1]
                    making_sound(392,50,0.1,1)
                
                    if one_sec_weight[0] == -999 or None: #要確定不是空串列
                        one_min_weight.append(one_min_weight[-1]) #本秒鐘回傳為空，就重複上一秒的數字。                        
                    else:
                        one_min_weight.append(one_sec_weight[0])  #加入本分鐘串列
#去除outlier。目前仍採超過一個標準差法。
                if len(one_min_weight) > 0 and None not in one_min_weight: #確定不是空串列
                    one_weight_temp=discard_outlier(one_min_weight) #呼叫。除掉outlier，傳回資料放在one_weight_temp
                    weight_FLUID.append(np.mean(one_weight_temp))   #將已去除outlier的數字計算平均，並加入重量紀錄主串列weight_Fluid
                    time_INDEX.append(time.strftime("%Y-%m-%d %H:%M")) #將目前時間加入時間記錄主串列time_INDEX
                    print('weight_FLUID',weight_FLUID)
                    print('time_INDEX',time_INDEX)
                    plot_scatter("weight change :"+str(five_weight_change))  #注意，這邊並沒有計算。要等到下一段才有
                    one_min_weight=[]
                else:
                    pass #空串列的話就啥都不做

#每5分鐘以最近十個數據，利用回歸分析判斷趨勢與估計尿量。
                if time.localtime()[4] in period_minute and len(weight_FLUID) >= 11:
        #先計算最近十分鐘的總重量變化
                    five_weight_change=calculate_weight_changes(10) #呼叫。取倒數10個計算重量變化
                    making_sound(350,25,0.1,2)
                    print("最近十分鐘尿量",five_weight_change)
        #利用重量變化計算趨勢與估計未來尿量
                    five_regression=calculate_regression(weight_FLUID,10)   #呼叫。以每分鐘重量差，評估趨勢（至少10個的時候才跑回歸計算趨勢）
                    if five_regression[1] < 0:
                        print("趨勢：減少")
                    else:
                        print("趨勢：穩定或增加")

#每59分或29分紀錄總尿量。不管len(weight_FLUID) >=1，也不指定秒數，只要電腦有空就去做

                if time.localtime()[4]  == 59 and len(weight_FLUID) >= 1:
                    processed_data=saving_data(time_INDEX,weight_FLUID,59) #呼叫。存檔
                    print(processed_data[0],processed_data[1])
                    time_INDEX=processed_data[0] #留下縮減過的資料串列
                    weight_FLUID=processed_data[1]#留下縮減過的資料串列
                    weight_PREVIOUS=processed_data[2]
                    print('回傳之weight_PREVIOUS',weight_PREVIOUS)
                    pass
                elif time.localtime()[4]  == 29 and len(weight_FLUID) >= 1:
                    processed_data=saving_data(time_INDEX,weight_FLUID,29)
                    time_INDEX=processed_data[0]
                    weight_FLUID=processed_data[1]
                    weight_PREVIOUS=processed_data[2]
                    print('回傳之weight_PREVIOUS',weight_PREVIOUS)
                    pass

            else:
                pass




        except Warning:
            raise
        except ZeroDivisionError:
            print('估計可能不準')
        except Exception:
            raise

        
if __name__ == '__main__':
        # Arduino setup
    COM_PORT = 'COM5'
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if port.manufacturer.startswith("Arduino"):
            COM_PORT = port.name
            print("Arduino device found on " + COM_PORT)
    arduinoSerial = serial.Serial(COM_PORT, BAUD_RATES)
    file_name = input('請輸入病歷號：') + '.csv'
    signal.signal(signal.SIGINT,good_bye)
    
    main()
