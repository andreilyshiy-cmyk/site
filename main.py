from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import bcrypt

SQLALCHEMY_DATABASE_URL = "sqlite:///./platform.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SUPER_ADMIN_TG = "@ahahahhaaaaas"

# Модели базы данных
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String) # admin, teacher, student

class HomeworkDB(Base):
    __tablename__ = "homeworks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    subject = Column(String)

class RequestDB(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String)
    contact = Column(String)
    tariff = Column(String)
    status = Column(String, default="Новая")

class StaffDB(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    role_title = Column(String)
    photo_url = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class HomeworkCreate(BaseModel):
    title: str
    description: str
    subject: str

class RequestCreate(BaseModel):
    student_name: str
    contact: str
    tariff: str

class StaffCreate(BaseModel):
    name: str
    role_title: str
    photo_url: str

@app.post("/api/register")
def register_user(user: UserCreate, current_tg_id: str = Header(default=""), db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.add(UserDB(username=user.username, password_hash=hashed, role=user.role))
    db.commit()
    return {"status": "success", "message": "Пользователь успешно создан!"}

@app.post("/api/request")
def create_request(req: RequestCreate, db: Session = Depends(get_db)):
    db.add(RequestDB(**req.dict()))
    db.commit()
    return {"status": "success", "message": "Заявка успешно отправлена! Мы свяжемся с вами."}

@app.get("/api/requests")
def get_requests(db: Session = Depends(get_db)):
    return db.query(RequestDB).all()

@app.post("/api/homework")
def create_homework(hw: HomeworkCreate, db: Session = Depends(get_db)):
    db.add(HomeworkDB(**hw.dict()))
    db.commit()
    return {"status": "success", "message": "ДЗ опубликовано!"}

@app.get("/api/homeworks")
def get_homeworks(db: Session = Depends(get_db)):
    return db.query(HomeworkDB).all()

@app.post("/api/staff")
def add_staff(st: StaffCreate, db: Session = Depends(get_db)):
    db.add(StaffDB(**st.dict()))
    db.commit()
    return {"status": "success", "message": "Сотрудник добавлен в штаб!"}

@app.get("/api/staff")
def get_staff(db: Session = Depends(get_db)):
    return db.query(StaffDB).all()