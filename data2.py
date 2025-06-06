#미세먼지, 초미세먼지
import requests
import json
import time
from multiprocessing import Event

url = 'http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty'
params ={'serviceKey' : 'L8/lsHDixFmS2p34yAH8Q9glQii9ughw2dcw5Hu6SH4gO0rrtNOPEevNbd3nbvW8NzCbwuPPxBHUTqs7aFzLww==', 'returnType' : 'json', 'numOfRows' : '100', 'pageNo' : '1', 'sidoName' : '충북', 'ver' : '1.0' }
ev = Event()

save_path = './OpenSourceBasicProj_Ass/teamproj/output_file2.json'
try:
    with open(save_path, 'w', encoding='utf-8') as f:
        response = requests.get(url, params=params)
        formatted_json = json.dumps(response.json(), indent=4, ensure_ascii=False)
        f.write(formatted_json)
        ev.set()
except Exception as e1:
    print("데이터 받아오기 실패[2]")

def finalarr(shared_list):
    ev.wait()
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data['response']['body']['items']

        for item in items:
            if item['stationName'] == '산남동':
                dust_data = {k: item[k] for k in ['pm10Value', 'pm25Value']}
        
        shared_list.append(dust_data)
        print('s2')
    except Exception as e2:
        print(f"[data2] 오류 발생: {e2}")
        shared_list.append({})
