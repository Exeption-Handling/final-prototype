#최고기온, 최저기온
import requests  # requests 모듈 임포트
import time
from multiprocessing import Event

# URL과 저장 경로 변수를 지정합니다.
url = f'https://apihub.kma.go.kr/api/typ01/url/kma_sfcdd.php?&stn=131&disp=0&help=1&authKey=lCL7eoqyTzGi-3qKst8xEQ'
save_path = './OpenSourceBasicProj_Ass/teamproj/output_file4.txt'
ev = Event()

try:
    with open(save_path, 'w', encoding='utf-8') as f: # 저장할 파일을 쓰기 모드로 열기
        response = requests.get(url) # 파일 URL에 GET 요청 보내기
        f.write(response.text) # 응답의 내용을 파일에 쓰기
        ev.set()
except Exception as e1:
    print("데이터 받아오기 실패[4]")

def extract_lines_in_range(file_path, linenum):
    with open(file_path, 'r', encoding='utf-8') as f:
        line = f.readlines()[linenum-1]  # 리스트 슬라이싱으로 특정 범위 라인 x`읽기
        return line.strip()

def finalarr(shared_list):
    ev.wait()
    try:
        data = extract_lines_in_range(save_path, 66)
        finalData = {'maxtemp' : data[59:63].strip(), 'mintemp' : data[70:74].strip()}

        shared_list.append(finalData)
        print('s4')
    
    except Exception as e2:
        print(f"[data4] 오류 발생: {e2}")
        shared_list.append({})
