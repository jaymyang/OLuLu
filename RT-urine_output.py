import time
import csv
import numpy as np
from sklearn.linear_model import LinearRegression
import serial
import matplotlib.pyplot as plt
import winsound
import serial.tools.list_ports

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
def get_weight():
    weight_temp = 0
    if arduinoSerial.in_waiting != 0: #序列埠不為空
        making_sound(500,50,0.1,1) #提示音
        data_in = arduinoSerial.readline()
        data = data_in.decode('utf-8')
        if data.replace('-', '', 1).isdigit(): #傳來為數字時才抓
            if int(data) >= -100: #因為有可能是在已經有尿的時候掛上去 結果起始點是正值卻被當為零點。
                #不過使用者輸入病歷號的時候，機器應該已經在歸零，所以這個問題應該不大。之後需要提示「可掛上」。
                weight_temp = int(data)
            else:
                weight_temp=None
    return weight_temp

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
    x = np.arange(len(weight_FLUID))
    plt.scatter(x, weight_FLUID, c='g', marker='>')
    plt.title(Title)
    plt.xlim([0, 60])
    plt.show(block=False)
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
        return saving_time, saving_weight

# Function to make sound#使用winsound取代print追蹤程式執行
def making_sound(frequency, duration, interrupt, repeat):
    for _ in range(repeat):
        winsound.Beep(frequency, duration)
        time.sleep(interrupt)

def main():
    global weight_FLUID, time_INDEX, arduinoSerial, file_name



    # Main loop

    print('def main started')
    if time.localtime()[4] == 29 or 59:
        time.sleep(60)
    global weight_FLUID,time_INDEX,period_second,period_minute,time_stamp
    current_minute = 61
    five_weight_change=10
    one_min_weight=[]
    #以下是設定比較回歸預測準確性所需的變數，預計在這個精簡版不會使用
    prediction_selection=None
    previous_prediction_15=[0,0]
    current_second = None


    #以下開始
    while True:
        try:  #首先判定時間，以確保每分鐘只會執行一次以下程式，避免資料過多或重複

            if time.localtime()[4] != current_minute: #current_time代表以下程式區塊所執行的時間。time.localtime[4]不等於current_time時，表示是新的分鐘
                current_minute=time.localtime()[4] #將current_minute設定為目前時間
                print(weight_FLUID)
                    #開始收集資料，預設10秒'
                while time.localtime()[5] in period_second: #時間之秒為串列中之值時，將會收集資料
                    for j in range(1,21,1): #最大為21
                        #print(j)
                        if j > 19:
                            print('抓資料結束',current_minute)
                            break
                        else:
                            one_second_weight=get_weight() #呼叫。Arduino端已經設定一秒丟一個數字
                            one_min_weight.append(one_second_weight) #將該秒取得的數字加入one_min_weight
                            if None in one_min_weight:
                                one_min_weight.remove(None) #如果得到None就去掉

                        #making_sound(350,25,0.1,1)
                        time.sleep(0.6) #確保迴圈跑完需要時間超過10秒


#去除outlier。目前仍採超過一個標準差法。

                if len(one_min_weight) > 0 and None not in one_min_weight: #要確定不是空串列
                    one_weight_temp=discard_outlier(one_min_weight) #呼叫。除掉outlier，傳回資料放在one_weight_temp
                    weight_FLUID.append(np.mean(one_weight_temp))   #將已去除outlier的數字計算平均，並加入重量紀錄主串列weight_Fluid
                    time_INDEX.append(time.strftime("%Y-%m-%d %H:%M")) #將目前時間加入時間記錄主串列time_INDEX
                    if time.localtime()[4] % 3 == 0: #利用餘數判斷每三分鐘畫一次，看機器反應如何
                        plot_scatter("Weight change in recent 10 minutes:"+str(five_weight_change))
                    one_min_weight.clear()

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
                    pass
                elif time.localtime()[4]  == 29 and len(weight_FLUID) >= 1:
                    processed_data=saving_data(time_INDEX,weight_FLUID,29)
                    time_INDEX=processed_data[0]
                    weight_FLUID=processed_data[1]
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
    main()
