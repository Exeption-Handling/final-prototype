from fastapi import FastAPI, HTTPException, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import timezone, datetime, timedelta
import jwt
from pydantic import BaseModel

####################################
########### 기본 세팅 설정 ###########
SECRET_KEY = "biccharu!03"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DATABASE_URL = "mysql+pymysql://root:urie1@1.246.113.73/fast_api"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
session = Session()

api = FastAPI()

templates = Jinja2Templates(directory=".")
########### 기본 세팅 설정 ###########
####################################

###########################################
########### 데이터베이스 모델 설정 ###########
class Plant(Base):
    __tablename__ = "plants"

    Pindex = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False, unique=True)
    hp = Column(Integer, nullable=False)
    attack = Column(Integer, nullable=True)
    defense = Column(Integer, nullable=False)
    attack_speed = Column(Integer, nullable=True)
    attack_range = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.Uindex"))

    owner = relationship("User", back_populates="plants")

class User(Base):
    __tablename__ = "users"

    Uindex = Column(Integer, primary_key=True)
    Uid = Column(String(20), nullable=False, unique=True)
    Password = Column(String(20), nullable=False)
    Username = Column(String(12), nullable=False, index=True)
    plants = relationship("Plant", back_populates="owner", cascade="all, delete-orphan")

    def add_plant(self, plant):
        self.plants.append(plant)
        session.commit()

class Today(Base):
    __tablename__ = "today"

    Tindex = Column(Integer, primary_key=True)
    Time = Column(String(20), nullable=False, unique=True)
    Weather = Column(String(20), nullable=False)
    Temperature = Column(String(20), nullable=False)

class Weather(Base):
    __tablename__ = "weather"

    Windex = Column(Integer, primary_key=True)
    Date = Column(String(20), nullable=False, unique=True)
    Weather = Column(String(20), nullable=False)
    Low_temperature = Column(String(20), nullable=False)
    High_temperature = Column(String(20), nullable=False)

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(String(255), nullable=False)

class LoginRequest(BaseModel):
    user_id: str
    password: str

Base.metadata.create_all(bind=engine)
########### 데이터베이스 모델 설정 ###########
###########################################

###################################
########### DB 세션 설정 ###########
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
########### DB 세션 설정 ###########
###################################

################################
########### JWT 설정 ###########
def create_jwt_token(data : dict, expires_delta : timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp" : expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_jwt_token(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="로그인 후 이용할 수 있는 기능입니다.")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="잘못된 토큰입니다.")
########### JWT 설정 ###########
################################

########### 메인 페이지 ###########
@api.get("/", response_class=HTMLResponse)
def title(request : Request):
    return templates.TemplateResponse("title.html", {"request" : request})
########### 메인 페이지 ###########

########### 지구마당 더보기 ###########
@api.get("/WW/", response_class=HTMLResponse)
def WW(request : Request):
    token = request.cookies.get("access_token")
    return templates.TemplateResponse("WW.html", {"request" : request, "token":token})

########### 회원가입 ###########
@api.get("/WW/sign_up/", response_class=HTMLResponse) # 회원가입 페이지
def sign_up(request : Request):
    return templates.TemplateResponse("signup.html", {"request" : request})
########### 회원가입 ###########

########### 회원가입 요청 전달 ###########
@api.post("/WW/sign_up/process/", response_class=HTMLResponse) # 회원가입 요청
def process_signing_up(request:Request, Uid:str=Form(...), username:str=Form(...), password:str=Form(...), db:Session=Depends(get_db)):
    new_user = User(Uid=Uid, Username=username, Password=password)
    scan_user = db.query(User).filter(User.Uid == Uid).first()
    if scan_user is None:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return templates.TemplateResponse("WW.html", {"request" : request, "signup_success" : f"{username}님, 성공적으로 회원가입이 완료되었습니다."})
    else: return templates.TemplateResponse("signup.html", {"request" : request, "error_message" : "이미 존재하는 Uid입니다. 다른 Uid를 입력해주세요!"})
########### 회원가입 요청 전달 ###########

########### 로그인 ###########
@api.get("/WW/login/", response_class=HTMLResponse) # 로그인 페이지
def login(request : Request):
    return templates.TemplateResponse("login.html", {"request" : request})
########### 로그인 ###########

########### 로그인 요청 전달 ###########
@api.post("/WW/login/process/", response_class=HTMLResponse) # 로그인 요청
def login(request: Request, user_id: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.Uid == user_id).first()

    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error_message": "ID를 찾을 수 없습니다."})
    elif not user.Password == password:
        return templates.TemplateResponse("login.html", {"request": request, "error_message": "PW가 일치하지 않습니다."})

    token = create_jwt_token({"sub": user.Uid}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    response = RedirectResponse(url="/WW/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)

    return response
########### 로그인 요청 전달 ###########

########### 로그아웃 ###########
@api.get("/WW/logout/") # 로그아웃
def logout():
    response = RedirectResponse(url="/WW/", status_code=303)
    response.delete_cookie(key="access_token")
    return response
########### 로그인 ###########

########### 마이페이지 ###########
@api.get("/WW/mypage/", response_class=HTMLResponse) # 마이페이지
def mypage(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("WW.html", {"request":request, "no_permission":"로그인 후 사용할 수 있는 기능입니다."})
    
    return templates.TemplateResponse("mypage.html", {"request":request})

########### 나만의 정원 ###########
@api.get("/WW/mypage/garden/", response_class=HTMLResponse) # 정원
def garden(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("mypage.html", {"request":request, "no_permission":"로그인 후 사용할 수 있는 기능입니다."})
    
    user = verify_jwt_token(request)
    user_id = user.get("sub")
    plants = db.query(Plant).filter(Plant.user_id == user_id).all()
    
    return templates.TemplateResponse("garden.html", {"request":request, "plants":plants})
########### 나만의 정원 ###########

########### 식물 vs 좀비 게임 ###########
@api.get("/WW/mypage/game/") # 게임
def game(request: Request):
    pass
########### 식물 vs 좀비 게임 ###########
########### 마이페이지 ###########

########### 지구 토론 게시판 ###########
@api.get("/WW/board/", response_class=HTMLResponse) # 게시판
def board(request : Request, db : Session = Depends(get_db)):
    posts = db.query(Post).all()
    return templates.TemplateResponse("posts.html", {"request":request, "posts":posts})

########### 글 쓰기 ###########
@api.get("/WW/board/create/", response_class=HTMLResponse) # 게시물 작성 페이지
def creating_post(request:Request, db : Session = Depends(get_db)):
    posts = db.query(Post).all()
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("posts.html", {"request":request, "posts" : posts, "no_permission":"로그인 후 사용할 수 있는 기능입니다."})
    return templates.TemplateResponse("creatingpost.html", {"request": request})
########### 글 쓰기 ###########

########### 글 쓰기 요청 전달 ###########
@api.post("/WW/board/create/process/", response_class=HTMLResponse) # 게시물 작성 요청
def create_post(request:Request, title:str=Form(...), content:str=Form(...), db: Session = Depends(get_db)):
    new_post = Post(title=title, content=content)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    return templates.TemplateResponse("post.html", {"request":request, "post":new_post})
########### 글 쓰기 요청 전달 ###########

########### 게시물 상세 페이지 ###########
@api.get("/WW/board/{post_id}/", response_class=HTMLResponse) # 게시물 상세 페이지
def read_post(post_id : int, request : Request, db : Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("post.html", {"request":request, "post":post})
########### 게시물 상세 페이지 ###########

########### 게시물 삭제 ###########
@api.post("/WW/board/delete/{post_id}/", response_class=HTMLResponse) # 게시물 수정 및 삭제
async def delete_post(post_id : int, request : Request, db : Session=Depends(get_db)):
    form_data = await request.form()
    method = form_data.get("_method","").lower()

    if method == "delete":
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            db.delete(post)
            db.commit()
            return RedirectResponse("/WW/board/", status_code=303)
        raise HTTPException(status_code=404, detail="Post not found")
    raise HTTPException(status_code=405, detail="Method not allowed")
########### 게시물 삭제 ###########

########### 게시물 수정 ###########
@api.get("/WW/board/modify/{post_id}/", response_class=HTMLResponse) # 게시물 수정 페이지
def modifying_post(post_id : int, request : Request, db : Session=Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("modify.html", {"request":request, "post":post})
########### 게시물 수정 ###########

########### 게시물 수정 요청 전달 ###########
@api.post("/WW/board/modify/process/{post_id}/", response_class=HTMLResponse) # 게시물 수정 요청
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
            return RedirectResponse("/WW/board/", status_code=303)
        raise HTTPException(status_code=404, detail="Post not found")
    raise HTTPException(status_code=405, detail="Method not allowed")
########### 게시물 수정 요청 전달 ###########
########### 지구 토론 게시판 ###########

########### 체크리스트 ###########
@api.get("/WW/mypage/checklist/", response_class=HTMLResponse) # 체크리스트
def checklist(request : Request):
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("WW.html", {"request":request, "no_permission":"로그인 후 사용할 수 있는 기능입니다."})
    return templates.TemplateResponse("checklist.html", {"request":request})
########### 체크리스트 ###########

########### 체크리스트 결과 전달 요청 ###########
@api.post("/WW/mypage/checklist/process/", response_class=HTMLResponse) # 체크리스트 요청
def submit_checklist(request : Request, db : Session = Depends(get_db)):
    pass
########### 체크리스트 결과 전달 요청 ###########
########### 지구마당 더보기 ###########

########### 워밍워닝 더보기 ###########
@api.get("/moreww/", response_class=HTMLResponse) # 워밍워닝 더보기
def moreww(request : Request):
    return templates.TemplateResponse("moreww.html", {"request" : request})

########### 워밍워닝이란? ###########
@api.get("/moreww/aboutww/", response_class=HTMLResponse) # 워밍워닝이란?
def aboutww(request : Request):
    return templates.TemplateResponse("aboutww.html", {"request" : request})
########### 워밍워닝이란? ###########

########### 지구 숨 지수란? ###########
@api.get("/moreww/aboutwp/", response_class=HTMLResponse) # 지구 숨 지수란?
def aboutwp(request : Request):
    return templates.TemplateResponse("aboutwp.html", {"request" : request})
########### 지구 숨 지수란? ###########

########### 정보 출처 ###########
@api.get("/moreww/source/", response_class=HTMLResponse) # 정보 출처
def source(request : Request):
    return templates.TemplateResponse("source.html", {"request" : request})
########### 정보 출처 ###########
########### 워밍워닝 더보기 ###########
