import requests
import json
from collections import defaultdict
from datetime import datetime, timedelta
import time
from multiprocessing import Event

now = datetime.now()
date = now.strftime("%Y%m%d")
times = int(now.strftime("%H"))
if 2 < times <= 5:
    times = '0200'
elif 5 < times <= 8:
    times = '0500'
elif 8 < times <= 11:
    times = '0800'
elif 11 < times <= 14:
    times = '1100'
elif 14 < times <= 17:
    times = '1400'
elif 17 < times <= 20:
    times = '1700'
elif 20 < times <= 23:
    times = '2000'
else:
    if times <= 2:
        date = str(int(date)-1)
    times = '2300'

url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst'
params ={'serviceKey' : '(serviceKey)', 'pageNo' : '1', 'numOfRows' : '1000', 'dataType' : 'JSON', 'base_date' : date, 'base_time' : times, 'nx' : '68', 'ny' : '107' } # (serviceKey)부분에 자신이 발급받은 키를 입력하여 사용
ev = Event()

save_path = './OpenSourceBasicProj_Ass/teamproj/output_file3.json'
try:
    with open(save_path, 'w', encoding='utf-8') as f:
        response = requests.get(url, params=params)
        formatted_json = json.dumps(response.json(), indent=4, ensure_ascii=False)
        f.write(formatted_json)
        ev.set()
except Exception as e1:
    print("데이터 받아오기 실패[3]")

def finalarr(shared_list2):
    ev.wait()
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
            items = data['response']['body']['items']['item']
            grouped = defaultdict(list)
            for item in items:
                if item['category'] == 'TMP':
                    grouped['temp'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
                elif item['category'] == 'TMN':
                    grouped['mintemp'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
                elif item['category'] == 'TMX':
                    grouped['maxtemp'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
                elif item['category'] == 'SKY':
                    grouped['sky'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
                elif item['category'] == 'REH':
                    grouped['humidity'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
                elif item['category'] == 'PTY':
                    grouped['raintype'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
                elif item['category'] == 'WSD':
                    grouped['wind'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
                elif item['category'] == 'PCP':
                    if item['fcstValue'] == '강수없음':
                        item['fcstValue'] = 0.0
                    elif item['fcstValue'] == '1mm 미만':
                        item['fcstValue'] = 0.5
                    elif item['fcstValue'] == '30.0~50.0mm':
                        item['fcstValue'] = 40.0
                    elif item['fcstValue'].endswith('mm'):
                        item['fcstValue'] = float(item['fcstValue'].replace('mm', ''))
                    else:
                        item['fcstValue'] == 50.0
                    grouped['rain'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
            shared_list2.append(grouped)
            print('s3')
    except Exception as e2:
        print(f"[data3] 오류 발생: {e2}")
        shared_list2.append({})

# shared_list2 = []
# with open(save_path, 'r', encoding='utf-8') as f:
#     data = json.load(f)

#     items = data['response']['body']['items']['item']
#     grouped = defaultdict(list)
#     for item in items:
#         if item['category'] == 'TMP':
#             grouped['temp'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
#         elif item['category'] == 'TMN':
#             grouped['mintemp'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
#         elif item['category'] == 'TMX':
#             grouped['maxtemp'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
#         elif item['category'] == 'SKY':
#             grouped['sky'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
#         elif item['category'] == 'REH':
#             grouped['humidity'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
#         elif item['category'] == 'PTY':
#             grouped['raintype'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
#         elif item['category'] == 'WSD':
#             grouped['wind'].append([item['fcstDate']+item['fcstTime'], item['fcstValue']])
#     shared_list2.append(grouped)
#     print(shared_list2)
