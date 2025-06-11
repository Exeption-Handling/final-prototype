from fastapi import FastAPI, HTTPException, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import sessionmaker, Session
from datetime import timezone, datetime, timedelta
import jwt, uuid, json
from pydantic import BaseModel
import subprocess
from random import *
import finaldataonly

####################################
########### 기본 세팅 설정 ###########
SECRET_KEY = "(secret_key)" # 직접 secret_key를 설정하여 사용.
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

DATABASE_URL = "mysql+pymysql://{username}:{password}@{host}/{database}" # 개인 데이터베이스 정보 입력 후 사용

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
session = SessionLocal()

api = FastAPI() 

templates = Jinja2Templates(directory=".")

api.mount("/images", StaticFiles(directory="./weather_simple_icon/"), name="static")
########### 기본 세팅 설정 ###########
####################################

########### DB 세션 설정 ###########
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
########### DB 세션 설정 ###########

###########################################
########### 데이터베이스 모델 설정 ###########
class User(Base):
    __tablename__ = "users"

    Uindex = Column(Integer, primary_key=True)
    Uid = Column(String(20), nullable=False, unique=True)
    Password = Column(String(20), nullable=False)
    Username = Column(String(12), nullable=False, index=True)
    Uscore = Column(Integer, nullable=False, default=0)
    plants = Column(MutableList.as_mutable(JSON), nullable=True)

    def list_append(self, plant, db : Session = Depends(get_db)):
        current_plants = self.plants if self.plants else []

        if plant not in current_plants:
            current_plants.append(plant)
            db.commit()
            return True
        
        return False

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class LoginRequest(BaseModel):
    user_id: str
    password: str

class ScoreData(BaseModel):
    total_score : int

Base.metadata.create_all(bind=engine)
########### 데이터베이스 모델 설정 ###########
###########################################

###################################
###################################

################################
########### JWT 설정 ###########
def create_jwt_token(data : dict, expires_delta : timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp" : expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_jwt_token(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return (0, None)  # 로그인되지 않은 경우 None 반환
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        user = db.query(User).filter(User.Uid == user_id).first()
        if user:
            return (1, user)
        else:
            return (2, None)
    except jwt.ExpiredSignatureError:
        return (3, None)
    except jwt.InvalidTokenError:
        return (2, None)


########### JWT 설정 ###########
################################

########### 메인 페이지 ###########
@api.get("/", response_class=HTMLResponse)
def title(request : Request, db : Session = Depends(get_db)):
    data_today, icon_7days, weather_7days = finaldataonly.load_data()
    token, user = verify_jwt_token(request, db)
    return templates.TemplateResponse("title.html", {"request" : request, "token" : token, "user" : user, "today" : data_today, "d7" : icon_7days, "d7_w" : weather_7days})
########### 메인 페이지 ###########

@api.get("/weekly_weather/", response_class=HTMLResponse)
def weekly_weather(request : Request, db : Session = Depends(get_db)):
    weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    dates = [(datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(7)]
    data_today, icon_7days, weather_7days = finaldataonly.load_data()
    return templates.TemplateResponse("weekly_weather.html", {"request" : request, "d7" : icon_7days, "d7_w" : weather_7days, "weekday_names" : weekday_names, "dates" : dates})

########### 회원가입 ###########
@api.get("/sign_up/", response_class=HTMLResponse) # 회원가입 페이지
def sign_up(request : Request):
    return templates.TemplateResponse("signup.html", {"request" : request})
########### 회원가입 ###########

########### 회원가입 요청 전달 ###########
@api.post("/sign_up/process/", response_class=HTMLResponse) # 회원가입 요청
def process_signing_up(request:Request, Uid:str=Form(...), username:str=Form(...), password:str=Form(...), db:Session=Depends(get_db)):
    new_user = User(Uid=Uid, Username=username, Password=password)
    scan_user = db.query(User).filter(User.Uid == Uid).first()
    data_today, icon_7days, weather_7days = finaldataonly.load_data()
    if scan_user is None:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return templates.TemplateResponse("title.html", {"request" : request, "today" : data_today, "d7" : icon_7days, "d7_w" : weather_7days, "signup_success" : f"{username}님, 성공적으로 회원가입이 완료되었습니다."})
    else: return templates.TemplateResponse("signup.html", {"request" : request, "error_message" : "이미 존재하는 Uid입니다. 다른 Uid를 입력해주세요!"})
########### 회원가입 요청 전달 ###########

@api.get("/login/", response_class=HTMLResponse)
def login_page(request : Request):
    return templates.TemplateResponse("login.html", {"request" : request})

########### 로그인 요청 전달 ###########
@api.post("/login/process/", response_class=HTMLResponse) # 로그인 요청
def login(request: Request, user_id: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.Uid == user_id).first()

    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "token" : 0, "error_message": "ID를 찾을 수 없습니다."})
    elif not user.Password == password:
        return templates.TemplateResponse("login.html", {"request": request, "token" : 0, "error_message": "PW가 일치하지 않습니다."})

    token = create_jwt_token({"sub": user.Uid}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)

    return response
########### 로그인 요청 전달 ###########

########### 로그아웃 ###########
@api.get("/logout/") # 로그아웃
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response
########### 로그인 ###########

########### 마이페이지 ###########
@api.get("/mypage/", response_class=HTMLResponse) # 마이페이지
def mypage(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        data_today, icon_7days, weather_7days = finaldataonly.load_data()
        return templates.TemplateResponse("title.html", {"request":request, "token" : 0, "no_permission":"로그인 후 사용할 수 있는 기능입니다.", "today" : data_today, "d7" : icon_7days, "d7_w" : weather_7days})
    
    return templates.TemplateResponse("mypage.html", {"request":request})

########### 나만의 정원 ###########
@api.get("/mypage/garden/", response_class=HTMLResponse) # 정원
def garden(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("mypage.html", {"request":request, "no_permission":"로그인 후 사용할 수 있는 기능입니다."})
    
    token, user = verify_jwt_token(request, db)
    if user.plants is None:
        user.plants = []
    return templates.TemplateResponse("garden.html", {"request":request, "user" : user, "len" : len(user.plants)})
########### 나만의 정원 ###########

########### 식물 vs 좀비 게임 ###########
@api.get("/mypage/game/") # 게임
def game(request: Request, db: Session = Depends(get_db)):
    token, user = verify_jwt_token(request, db)
    if user.plants is None:
        return templates.TemplateResponse("mypage.html", {"request" : request, "no_plants" : "식물이 존재하지 않아 게임을 시작할 수 없습니다."})
    try:
        # 유저의 식물 데이터를 임시 JSON 파일로 저장
        session_id = str(uuid.uuid4())  # 고유 세션 ID
        json_path = f"session_{session_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"plants": user.plants}, f)

        # 게임 실행 시 경로 인자로 전달
        subprocess.Popen(
            ["python", "game.py", json_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        return templates.TemplateResponse("mypage.html", {"request": request, "game_started": "게임이 시작되었습니다."})
    except Exception as e:
        return templates.TemplateResponse("mypage.html", {"request": request, "game_error": f"게임을 시작하는데 실패했습니다: {str(e)}"})
    # threading.Thread(target=).start()
    # pass
########### 식물 vs 좀비 게임 ###########
########### 마이페이지 ###########

########### 지구 토론 게시판 ###########
@api.get("/board/", response_class=HTMLResponse) # 게시판
def board(request : Request, db : Session = Depends(get_db)):
    posts = db.query(Post).all()
    return templates.TemplateResponse("posts.html", {"request":request, "posts":posts})

########### 글 쓰기 ###########
@api.get("/board/create/", response_class=HTMLResponse) # 게시물 작성 페이지
def creating_post(request:Request, db : Session = Depends(get_db)):
    posts = db.query(Post).all()
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("posts.html", {"request":request, "posts" : posts, "no_permission":"로그인 후 사용할 수 있는 기능입니다."})
    return templates.TemplateResponse("creatingpost.html", {"request": request})
########### 글 쓰기 ###########

########### 글 쓰기 요청 전달 ###########
@api.post("/board/create/process/", response_class=HTMLResponse) # 게시물 작성 요청
def create_post(request:Request, title:str=Form(...), content:str=Form(...), db: Session = Depends(get_db)):
    token, user = verify_jwt_token(request, db)
    if token != 1 or not user:
        return templates.TemplateResponse("posts.html", {"request" : request, "no_permission" : "로그인 후 사용할 수 있는 기능입니다."})
    new_post = Post(title=title, content=content, author=user.Username)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    return templates.TemplateResponse("post.html", {"request":request, "post":new_post})
########### 글 쓰기 요청 전달 ###########

########### 게시물 상세 페이지 ###########
@api.get("/board/{post_id}/", response_class=HTMLResponse) # 게시물 상세 페이지
def read_post(post_id : int, request : Request, db : Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("post.html", {"request":request, "post":post})
########### 게시물 상세 페이지 ###########

########### 게시물 삭제 ###########
@api.post("/board/delete/{post_id}/", response_class=HTMLResponse) # 게시물 수정 및 삭제
async def delete_post(post_id : int, request : Request, db : Session=Depends(get_db)):
    form_data = await request.form()
    method = form_data.get("_method","").lower()

    if method == "delete":
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            db.delete(post)
            db.commit()
            return RedirectResponse("/board/", status_code=303)
        raise HTTPException(status_code=404, detail="Post not found")
    raise HTTPException(status_code=405, detail="Method not allowed")
########### 게시물 삭제 ###########

########### 게시물 수정 ###########
@api.get("/board/modify/{post_id}/", response_class=HTMLResponse) # 게시물 수정 페이지
def modifying_post(post_id : int, request : Request, db : Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("modify.html", {"request":request, "post":post})
########### 게시물 수정 ###########

########### 게시물 수정 요청 전달 ###########
@api.post("/board/modify/process/{post_id}/", response_class=HTMLResponse) # 게시물 수정 요청
async def modify_post(post_id : int, request:Request, title:Optional[str]=Form(None), content:Optional[str]=Form(None), db:Session=Depends(get_db)):
    form_data = await request.form()
    method = form_data.get("_method","").lower()

    if method == "modify":
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.title = title or post.title
            post.content = content or post.content
            db.commit()
            db.refresh(post)
            return RedirectResponse("/board/", status_code=303)
        raise HTTPException(status_code=404, detail="Post not found")
    raise HTTPException(status_code=405, detail="Method not allowed")
########### 게시물 수정 요청 전달 ###########
########### 지구 토론 게시판 ###########

########### 체크리스트 ###########
@api.get("/mypage/checklist/", response_class=HTMLResponse) # 체크리스트
def checklist(request : Request, db : Session = Depends(get_db)):
    token, user = verify_jwt_token(request, db)
    if not token:
        return templates.TemplateResponse("mypage.html", {"request":request, "no_permission":"로그인 후 사용할 수 있는 기능입니다."})
    
    if request.cookies.get("checklist_submitted") == "true":
        return templates.TemplateResponse("mypage.html", {
            "request": request,
            "user": user,
            "already_done": "오늘은 이미 체크리스트를 완료하셨습니다."
        })
    
    return templates.TemplateResponse("checklist.html", {"request" : request, "user" : user, "token" : token})
########### 체크리스트 ###########

########### 체크리스트 결과 전달 요청 ###########
@api.post("/mypage/checklist/process/", response_class=HTMLResponse) # 체크리스트 요청
def submit_checklist(request : Request, total_score : int = Form(...), db : Session = Depends(get_db)):
    levelup = 0
    value = None
    appended = None
    token, current_user = verify_jwt_token(request, db)
    if token != 1 or not current_user:
        return templates.TemplateResponse("checklist.html", {"request":request, "no_permission":"로그인 후 사용할 수 있는 기능입니다."})
    
    if current_user.Uscore is None:
        current_user.Uscore = 0

    plants = {0 : "ranged", 1 : "melee", 2 : "shield"}
    current_user.Uscore += total_score
    if current_user.Uscore > 100:
        value = randint(0, 2)
        current_user.Uscore -= 100
        levelup = 1
        appended = current_user.list_append(plants[value], db)
    plant = plants[value] if value is not None else None
    db.commit()
    db.refresh(current_user)

    response = templates.TemplateResponse("score_result.html", {"request": request, "user": current_user, "score": total_score, "levelup" : levelup, "plant" : plant, "append" : appended})
    expire_time = datetime.utcnow() + timedelta(days=1)
    response.set_cookie(key="checklist_submitted", value="true", expires=expire_time.strftime("%a, %d-%b-%Y %H:%M:%S GMT"))
    return response
########### 체크리스트 결과 전달 요청 ###########
