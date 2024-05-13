#本計算方式基本上不考慮異常值
import csv
def calculating(weight_cal):
    weight_sum=0
    weight_max=int(weight_cal[0]) #先將最大值設成起始值
    weight_min=int(weight_cal[0]) #先將最小值設成起始值
    print(weight_cal)
    for i, element in enumerate(weight_cal):
        if int(weight_cal[i])>weight_max and int(weight_cal[i])-weight_max<500:
            weight_max=int(weight_cal[i]) #假如目前這個比前一個大，就把weight_max數值設為目前這個
        else:
            pass
        if len(weight_cal)>1:
            if int(weight_cal[i])<weight_min and int(weight_cal[i])-int(weight_cal[i-1]) > -50: #這視為無倒尿
                pass
            elif int(weight_cal[i])<weight_min and int(weight_cal[i])-int(weight_cal[i-1]) < -50: #這視為有倒尿；這是整個計算中唯一考慮到的異常值處理部分
                weight_sum=weight_sum+weight_max-weight_min #
                weight_max=int(weight_cal[i]) #重設
                weight_min=int(weight_cal[i]) #重設
        else:
            pass
    print(weight_max,weight_min)

    weight_sum=weight_sum+weight_max-weight_min
    return weight_sum

filename=str(input('輸入檔案:'))+'.csv'

with open(filename, newline='') as csvfile:
  rows = csv.reader(csvfile)
  time=[]
  weight=[]
  for row in rows:
      time.append(row[0])
      weight.append(row[1])
#以上把資料全部讀入。0是時間，1是重量



time_section=[]
weight_section=[]
for i, element in enumerate(weight):
    if time[i][-2:]!='59':
       
        time_section.append(time[i])
        weight_section.append(weight[i])
    else:
        time_section.append(time[i])
        weight_section.append(weight[i])
        weight_hour=calculating(weight_section)
        print(time[i],weight_hour)
        time_section=[]
        weight_section=[]





    
