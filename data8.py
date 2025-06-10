import requests
import json
from datetime import datetime, timedelta
import time
from multiprocessing import Event

now = datetime.now()
times = int(now.strftime('%H'))
if 6 < times <= 18:
    times = now.strftime("%Y%m%d") + '0600'
else:
    if times < 6:
        times = str(int(now.strftime("%Y%m%d"))-1) + '1800'
    else:
        times = now.strftime("%Y%m%d") + '1800'

url = 'http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa'
params ={'serviceKey' : '(serviceKey)', 'pageNo' : '1', 'numOfRows' : '10', 'dataType' : 'JSON', 'regId' : '11C10301', 'tmFc' : times} # (serviceKey) 부분에 직접 발급받은 키를 입력하여 사용
ev = Event()

save_path = './OpenSourceBasicProj_Ass/teamproj/output_file8.json'
try:
    with open(save_path, 'w', encoding='utf-8') as f:
        response = requests.get(url, params=params)
        json.dump(response.json(), f, indent=4, ensure_ascii=False)
        ev.set()
except Exception as e1:
    print("데이터 받아오기 실패[8]")

def finalarr(shared_list4):
    ev.wait()
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data['response']['body']['items']['item']
        temp_list = []
        for item in items:
            for key in item:
                if key[-1].isdigit() and key[-1] and key[-1] not in ('8', '9', '0'):
                    temp_list.append(item[key])
        
        shared_list4.append(temp_list)
        print('s8')
    except Exception as e2:
        print(f"[data7] 오류 발생: {e2}")
        shared_list4.append({})

# with open(save_path, 'r', encoding='utf-8') as f:
#     data = json.load(f)
    
#     items = data['response']['body']['items']['item']
#     temp_list = []
#     for item in items:
#         for key in item:
#             if key[-1].isdigit() and key[-1] not in ('8', '9', '0'):
#                 temp_list.append(item[key])
#     print(temp_list)
