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

url = 'http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst'
params ={'serviceKey' : '(serviceKey)', 'pageNo' : '1', 'numOfRows' : '10', 'dataType' : 'JSON', 'regId' : '11C10000', 'tmFc' : times} # (serviceKey) 부분에 직접 발급받은 키를 입력하여 사용
ev = Event()

save_path = './OpenSourceBasicProj_Ass/teamproj/output_file7.json'
try:
    with open(save_path, 'w', encoding='utf-8') as f:
        response = requests.get(url, params=params)
        json.dump(response.json(), f, indent=4, ensure_ascii=False)
        ev.set()
except Exception as e1:
    print("데이터 받아오기 실패[7]")

def finalarr(shared_list3):
    ev.wait()
    time.sleep(1)
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data['response']['body']['items']['item']
        temp_list = []
        for item in items:
            for key in item:
                if key.startswith('wf') and key.endswith('m'):
                    temp_list.append(item[key])
        
        for i in range(len(temp_list)):
            if '눈' in temp_list[i]:
                temp_list[i] = 3
            elif '비' in temp_list[i] or '소나기' in temp_list[i]:
                temp_list[i] = 4
            elif '흐' in temp_list[i]:
                temp_list[i] = 5
            elif '구' in temp_list[i]:
                temp_list[i] = 6
            else:
                temp_list[i] = 0
        
        shared_list3.append(temp_list)
        print('s7')
    except Exception as e2:
        print(f"[data7] 오류 발생: {e2}")
        shared_list3.append({})

# try:
#     with open(save_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
    
#     items = data['response']['body']['items']['item']
#     temp_list = []
#     for item in items:
#         for key in item:
#             if key.startswith('wf') and key.endswith('m'):
#                 temp_list.append(item[key])
#     for i in range(len(temp_list)):
#         if '눈' in temp_list[i]:
#             temp_list[i] = 3
#         elif '비' in temp_list[i] or '소나기' in temp_list[i]:
#             temp_list[i] = 4
#         elif '흐' in temp_list[i]:
#             temp_list[i] = 5
#         elif '구' in temp_list[i]:
#             temp_list[i] = 6
#         else:
#             temp_list[i] = 0

#     print(temp_list)
# except Exception as e2:
#     print(f"[data7] 오류 발생: {e2}")
#     #shared_list3.append({})
