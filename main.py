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

# ВАШ TELEGRAM ID ДЛЯ ВЫДАЧИ АДМИНОК
SUPER_ADMIN_TG = "@ahahahhaaaaas"

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String) # 'admin', 'teacher', 'student'
    tg_id = Column(String, nullable=True)

class RequestDB(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String)
    contact = Column(String)
    tariff = Column(String)
    status = Column(String, default="Новая")

class ScheduleDB(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    day = Column(String)
    time = Column(String)
    subject = Column(String)
    teacher = Column(String)

class StaffDB(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    subject = Column(String)
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

# Заполняем стартовыми данными (заглушки) при запуске
def init_seed_data():
    db = SessionLocal()
    if db.query(StaffDB).count() == 0:
        db.add_all([
            StaffDB(name="Алексей Смирнов", subject="Математика / Физика", photo_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300"),
            StaffDB(name="Елена Ковалева", subject="Русский язык / Литература", photo_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=300"),
            StaffDB(name="Дмитрий Волков", subject="Информатика / Python", photo_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300")
        ])
    if db.query(ScheduleDB).count() == 0:
        db.add_all([
            ScheduleDB(day="Понедельник", time="16:00", subject="Математика (ЦЭ/ЕГЭ)", teacher="Алексей Смирнов"),
            ScheduleDB(day="Среда", time="17:30", subject="Русский язык", teacher="Елена Ковалева"),
            ScheduleDB(day="Пятница", time="18:00", subject="Программирование Python", teacher="Дмитрий Волков")
        ])
    db.commit()
    db.close()

init_seed_data()

class RequestCreate(BaseModel):
    student_name: str
    contact: str
    tariff: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    tg_id: str | None = None

class UserLogin(BaseModel):
    username: str
    password: str

# Подача заявки учеником
@app.post("/api/request")
def create_request(req: RequestCreate, db: Session = Depends(get_db)):
    new_req = RequestDB(**req.dict())
    db.add(new_req)
    db.commit()
    return {"status": "success", "message": "Заявка успешно отправлена и сохранена!"}

# Просмотр всех заявок (для учителя / админа)
@app.get("/api/requests")
def get_requests(db: Session = Depends(get_db)):
    return db.query(RequestDB).all()

# Назначение учителей / админов (доступно только Супер-админу @ahahahhaaaaas)
@app.post("/api/register")
def register_user(user: UserCreate, current_tg_id: str = Header(default=""), db: Session = Depends(get_db)):
    if current_tg_id != SUPER_ADMIN_TG:
        raise HTTPException(status_code=403, detail="Только супер-администратор может назначать роли!")
    
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует!")

    hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = UserDB(username=user.username, password_hash=hashed, role=user.role, tg_id=user.tg_id)
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": f"Пользователь {user.username} создан с ролью {user.role}!"}

@app.post("/api/login")
def login_user(creds: UserLogin, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == creds.username).first()
    if not user or not bcrypt.checkpw(creds.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль!")
    return {"status": "success", "role": user.role, "username": user.username}

@app.get("/api/schedules")
def get_schedules(db: Session = Depends(get_db)):
    return db.query(ScheduleDB).all()

@app.get("/api/staff")
def get_staff(db: Session = Depends(get_db)):
    return db.query(StaffDB).all()
