import requests
import json
from collections import defaultdict
from datetime import datetime
import time
from multiprocessing import Event

now = datetime.now()
date = now.strftime("%Y%m%d")
if int(now.strftime("%H"))-1 < 10:
    times = '0' + str(int(now.strftime("%H"))-1) + '00'
else:
    times = str(int(now.strftime("%H"))-1) + '00'

url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst'
params ={'serviceKey' : 'L8/lsHDixFmS2p34yAH8Q9glQii9ughw2dcw5Hu6SH4gO0rrtNOPEevNbd3nbvW8NzCbwuPPxBHUTqs7aFzLww==', 'pageNo' : '1', 'numOfRows' : '1000', 'dataType' : 'JSON', 'base_date' : date, 'base_time' : times, 'nx' : '68', 'ny' : '107' }
ev = Event()

save_path = './OpenSourceBasicProj_Ass/teamproj/output_file6.json'
try:
    with open(save_path, 'w', encoding='utf-8') as f:
        response = requests.get(url, params=params)
        formatted_json = json.dumps(response.json(), indent=4, ensure_ascii=False)
        f.write(formatted_json)
        ev.set()
except Exception as e1:
    print("데이터 받아오기 실패[6]")

def finalarr(shared_list2):
    ev.wait()
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data['response']['body']['items']['item']
        grouped = defaultdict(list)
        for item in items:
            if item['category'] == 'LGT':
                grouped['lightning'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])

        shared_list2.append(grouped)
        print('s6')
    except Exception as e2:
        print(f"[data6] 오류 발생: {e2}")
        shared_list2.append({})

# shared_list2=[]
# with open(save_path, 'r', encoding='utf-8') as f:
#     data = json.load(f)
    
#     items = data['response']['body']['items']['item']
#     grouped = defaultdict(list)
#     for item in items:
#         if item['category'] == 'LGT':
#             grouped['lightning'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
#     shared_list2.append(grouped)
#     print(shared_list2[0]['lightning'])