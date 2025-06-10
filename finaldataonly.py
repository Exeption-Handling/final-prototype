from multiprocessing import Process, Manager
import data, data2, data3, data4, data5, data6, data7, data8 # 
from datetime import datetime, timedelta
from collections import Counter
from itertools import chain
import time

last_daily_run = datetime.min

#icon(아이콘) 0: 맑음, 1: 비+번개, 2: 번개 3: 눈, 4: 비, 5: 흐림, 6: 구름 많음 7: 바람
def load_data():

    now = datetime.now()
    """multiprocessing으로 데이터 수집"""
    with Manager() as manager:
        #데이터 수집 코드와 연결
        shared_list = manager.list()
        shared_list2 = manager.list()
        shared_list3 = manager.list()
        shared_list4 = manager.list()

        jobs = [
            Process(target=data.finalarr, args=(shared_list,)),
            # Process(target=data2.finalarr, args=(shared_list,)), 
            #미세먼지를 받아오는 사이트가 원인모를 이유로 작동하지 않기에(서비스 키 만료 이슈로 추정됨) 제외한 상태로 실행 (현재 단계에서는 미세먼지 서비스를 제공하고 있지 않으므로 무관하게 작동함)
            Process(target=data3.finalarr, args=(shared_list2,)),         
            Process(target=data4.finalarr, args=(shared_list,)),
            Process(target=data5.finalarr, args=(shared_list,)),
            Process(target=data6.finalarr, args=(shared_list2,)),
            Process(target=data7.finalarr, args=(shared_list3,)),
            Process(target=data8.finalarr, args=(shared_list4,)),
        ]

        for job in jobs:
            job.start()
        for job in jobs:
            job.join()

        #데이터 처리
        cleaned = []
        for item in shared_list:
            if isinstance(item, list):
                cleaned.extend(item)
            else:
                cleaned.append(item)

        merged_data = {}
        for d in cleaned:
            merged_data.update(d)
        
        organized_data = {}
        for d in shared_list2:
            for key, value in d.items():
                if key not in organized_data:
                    organized_data[key] = []
                organized_data[key].extend(value)

        #아이콘 설정(주의: data7에도 아이콘 설정 코드가 있음)
        if int(organized_data['lightning'][0][1]) > 0 and float(merged_data['rain']) > 0.0:
            s = 1
        elif int(organized_data['lightning'][0][1]) > 0 and float(merged_data['rain']) == 0.0:
            s = 2
        elif float(merged_data['rain']) > 0.0 and organized_data['sky'][0][1] in ['2', '3']:
            s = 3
        elif float(merged_data['rain']) > 0.0:
            s = 4
        elif int(merged_data['cloud']) >= 5 and int(merged_data['rainchance']) >= 50:
            s = 5
        elif int(merged_data['cloud']) >= 5:
            s = 6
        elif float(merged_data['wind']) > 8.0:
            s = 7
        else:
            s = 0
        merged_data['icon'] = s

        print(merged_data)
        #merged_data = {'temp' : value, 'rain' : value, ...}
        #temp, humidity, rain, cloud, wind, pm10Value, pm25Value, maxtemp, mintemp, rainchance

        organized_data['icon'] = []
        for i in range(len(organized_data['raintype'])): #69 81
            if i < 6:
                if int(organized_data['raintype'][i][1]) > 0 and int(organized_data['lightning'][i][1]) > 0:
                    t = 1
                elif int(organized_data['raintype'][i][1]) < 0 and int(organized_data['lightning'][i][1]) > 0:
                    t = 2
                elif organized_data['raintype'][i][1] in ['2', '3']:
                    t = 3
                elif organized_data['raintype'][i][1] in ['1', '4']:
                    t = 4
                elif int(organized_data['sky'][i][1]) == 4:
                    t = 5
                elif int(organized_data['sky'][i][1]) == 3:
                    t = 6
                elif float(organized_data['wind'][i][1]) > 8.0:
                    t = 7
                else:
                    t = 0
                organized_data['icon'].append([organized_data['temp'][i][0], t])
            else:
                if organized_data['raintype'][i][1] in ['2', '3']:
                    t = 3
                elif organized_data['raintype'][i][1] in ['1', '4']:
                    t = 4
                elif int(organized_data['sky'][i][1]) == 4:
                    t = 5
                elif int(organized_data['sky'][i][1]) == 3:
                    t = 6
                elif float(organized_data['wind'][i][1]) > 8.0:
                    t = 7
                else:
                    t = 0
                organized_data['icon'].append([organized_data['temp'][i][0], t])

        print(organized_data['mintemp'])
        #organized_data = [{'temp' : [시간, 데이터값], [시간2, 데이터값],...[시간81, 데이터값81]}, {'rain' : [시간, 데이터값],...},...]
        #temp, mintemp, maxtemp, sky(맑음, 흐림 등 하늘 상태, 숫자로), humidity, raintype(강수 형태, 비 또는 눈), wind, rain, icon(아이콘 선택, 맑음, 흐림, 비 등등) + lightning(5시간 뒤까지만)

        #일주일 날씨 설정 코드
        global last_daily_run
        now = datetime.now()
        if now - last_daily_run >= timedelta(hours=23): # and now.strftime("%H") == '00':
            d7_data1 = []
            d7_data2 = []
            d7_data = []
            temp_data = []
            for i in range(round(len(organized_data['icon'])/12)-2): #4 6
                for j in range(12):
                    temp_data.append(organized_data['icon'][i*12+j][1])
                counter = Counter(temp_data)
                freq = counter.most_common(1)[0][1]
                modes = [key for key, count in counter.items() if count == freq]
                d7_data1.append(modes[0])
                if i % 2 == 0:
                    d7_data2.append(organized_data['mintemp'][i//2][1])
                    d7_data2.append(organized_data['maxtemp'][i//2][1])
                temp_data = []
            for i in range(round(len(organized_data['icon'])/12)-2,round(len(organized_data['icon'])/12)): #4,6 6,8
                for j in range(4):
                    temp_data.append(organized_data['icon'][12*(round(len(organized_data['icon'])/12)-2)+(i-6)*4+j][1]) #48 72
                counter = Counter(temp_data)
                freq = counter.most_common(1)[0][1]
                modes = [key for key, count in counter.items() if count == freq]
                d7_data1.append(modes[0])
                try:
                    if i % 2 == 0:
                        d7_data2.append(organized_data['mintemp'][i//2][1])
                        d7_data2.append(organized_data['maxtemp'][i//2][1])
                except:
                    pass
            shared_list3 = list(chain.from_iterable(shared_list3))
            shared_list4 = list(map(float, chain.from_iterable(shared_list4)))
            d7_data1.extend(shared_list3)
            d7_data2.extend(shared_list4)
            for i in range(7):
                d7_data.append(d7_data1[i*2])
                d7_data.append(d7_data1[i*2+1])
                d7_data.append(d7_data2[i*2])
                d7_data.append(d7_data2[i*2+1])

            print(d7_data) 

    return merged_data, d7_data
        #d7_data = [1일뒤 오전 날씨 아이콘, 1일 뒤 오후 날씨 아이콘, 1일 뒤 최저기온, 1일 뒤 최고기온, ... 7일까지]

if __name__ == '__main__':
    while True:
        try:
            load_data()
            time.sleep(1800)
        except:
            pass
