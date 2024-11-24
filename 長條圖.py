from datetime import datetime, timedelta
import tkinter as tk
import time

# 起始時間
start_time = datetime(2024, 11, 8, 12, 50)
y = []

# 建立時間串列
time_list = [start_time + timedelta(minutes=i) for i in range(20)]
formatted_time_list = [time.strftime("%Y/%m/%d %H:%M") for time in time_list]

# 範例資料（其中 12:54 的資料遺失）
data = [{'time': ['2024/11/08 12:50', '2024/11/08 12:51', '2024/11/08 12:52', 
                  '2024/11/08 12:53', '2024/11/08 12:55', '2024/11/08 12:56', 
                  '2024/11/08 12:57', '2024/11/08 12:58', '2024/11/08 12:59', 
                  '2024/11/08 13:00', '2024/11/08 13:01', '2024/11/08 13:02', 
                  '2024/11/08 13:03', '2024/11/08 13:04', '2024/11/08 13:05', 
                  '2024/11/08 13:06', '2024/11/08 13:07', '2024/11/08 13:08', 
                  '2024/11/08 13:09'],
         'weight': [0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]}]

temp_time = data[0]['time']
temp_weight = data[0]['weight']
#確定時間有搭上。計畫是要拿-60個資料，但可能會有疏漏。所以應該先計算data是否超過60項。
#再來用time delta並以迴圈，以每分鐘為單位，建立串列，用來跟time[j]比較
#start_time = time.strftime('%Y-%m-%d, %H:%M')
#應該是這個time_list = [datetime.strptime(start_time, '%Y-%m-%d %H:%M') + timedelta(minutes=-i) for i in range(60)]（往前推60個）
#for i in time_list:
#  formatted_time_list[i]=time_list[i].strftime('%Y-%m-%d %H:%M') #建立符合格式的參考時間串列
#接著要有60組X跟Y的數據；在這之前要判斷data[i]是否有超過60組數據。
#for i in range(-1,-61,-1):
#  if data[i]['time']==formatted_time_list[i]:
#    y.append(data[i]['weight'])
#  else:
#    y.append(0)


#如少於60項，-60分至有資料的時間，x軸用空白，y軸用0
#如超過60項，由-60開始，確認時間參考陣列質是否=time[j]。如否，y用0。如是，y用weight[j]

for i in range(19):
    if formatted_time_list[i] in temp_time:
        y.append(temp_weight[temp_time.index(formatted_time_list[i])])
    else:
        y.append(0)

# 建立視窗
root = tk.Tk()
root.title("長條圖")

# 設定畫布尺寸
canvas = tk.Canvas(root, width=650, height= 550, bg="white")
canvas.pack()


# 繪製長條圖；為簡單起見直接寫成固定值
for i in range(len(y)):
    x0 = 25+i*10
    y0 = 525-y[i]*10
    x1 = 25+i*10
    y1 = 525
    canvas.create_line(x0, y0, x1, y1,width=10, fill="orange")    

# 繪製 X 軸和 Y 軸
canvas.create_line(30,525,30, 0, fill="black", width=1) #x軸
canvas.create_line(30,525,635,525, fill="black", width=1)#y軸

# X軸刻度
for i in range(0,61,10):
    canvas.create_line(35+i*10,525,35+i*10,530, fill="black")
    canvas.create_text(35+i*10,530, text=i-60, anchor=tk.N)

# Y軸，乾脆用固定值比較容易看出變化。但應注意將來要設定如OluLu02版一樣，過重時更動刻度的機制
#for j in range(min(y), max(y) + 1):
for j in range(0,5):
    canvas.create_line(25,j*100+25,30,j*100+25, fill="black")
    canvas.create_text(25,j*100+25,text= (5-j)*100, anchor=tk.E)

# X 軸和 Y 軸的標籤
canvas.create_text(615,530, text="時間", anchor=tk.N)
canvas.create_text(15,45, text="公克", anchor=tk.S)

# 顯示視窗
root.mainloop()
