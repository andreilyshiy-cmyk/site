from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import bcrypt

SQLALCHEMY_DATABASE_URL = "sqlite:////data/platform.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="student")
    tariff = Column(String, default="Не выбран")
    status = Column(String, default="Активен")

class RequestDB(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_name = Column(String)
    contact = Column(String)
    tariff = Column(String)
    status = Column(String, default="Новая")

class ScheduleDB(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    day = Column(String)
    time = Column(String)
    subject = Column(String)
    teacher = Column(String)

class StaffDB(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    subject = Column(String)
    experience = Column(String)
    bio = Column(String, default="Опытный преподаватель высшей категории.")
    contact_info = Column(String, default="Telegram: @tutor_hub")
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
    try: yield db
    finally: db.close()

def seed_data():
    db = SessionLocal()
    if db.query(StaffDB).count() == 0:
        db.add_all([
            StaffDB(name="Алексей Смирнов", subject="Высшая математика", experience="Стаж 8 лет", bio="Подготовка к ЦЭ и олимпиадам.", contact_info="TG: @smirnov_math", photo_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400"),
            StaffDB(name="Екатерина Ковалева", subject="Русский язык", experience="Стаж 12 лет", bio="Эксперт по сочинениям.", contact_info="TG: @kovaleva_rus", photo_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400"),
            StaffDB(name="Дмитрий Волков", subject="Информатика & Python", experience="Стаж 5 лет", bio="Практикующий разработчик.", contact_info="TG: @volkov_code", photo_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400")
        ])
    if db.query(ScheduleDB).count() == 0:
        db.add_all([
            ScheduleDB(day="Понедельник", time="16:00 - 17:30", subject="Математика (ЦЭ)", teacher="Алексей Смирнов"),
            ScheduleDB(day="Среда", time="17:00 - 18:30", subject="Русский язык", teacher="Екатерина Ковалева")
        ])
    db.commit()
    db.close()
seed_data()

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdateAdmin(BaseModel):
    role: str
    tariff: str
    status: str

class RequestCreate(BaseModel):
    student_name: str
    contact: str
    tariff: str

class ScheduleCreate(BaseModel):
    day: str
    time: str
    subject: str
    teacher: str

@app.post("/api/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Логин уже занят!")
    hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    role = "admin" if db.query(UserDB).count() == 0 else "student"
    new_user = UserDB(username=user.username, password_hash=hashed, role=role)
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": "Регистрация успешна!"}

@app.post("/api/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if not db_user or not bcrypt.checkpw(user.password.encode('utf-8'), db_user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль!")
    return {
        "status": "success", 
        "user_id": db_user.id,
        "username": db_user.username, 
        "role": db_user.role,
        "tariff": db_user.tariff,
        "status_account": db_user.status
    }

@app.get("/api/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    return [{"user_id": u.id, "username": u.username, "role": u.role, "tariff": u.tariff, "status": u.status} for u in db.query(UserDB).all()]

@app.post("/api/admin/user/{user_id}")
def update_user_by_admin(user_id: int, data: UserUpdateAdmin, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="Не найден")
    user.role = data.role
    user.tariff = data.tariff
    user.status = data.status
    db.commit()
    return {"status": "success", "message": "Профиль обновлен!"}

@app.get("/api/staff")
def get_staff(db: Session = Depends(get_db)):
    return db.query(StaffDB).all()

@app.get("/api/schedules")
def get_schedules(db: Session = Depends(get_db)):
    return db.query(ScheduleDB).all()

@app.post("/api/admin/schedule")
def add_schedule(item: ScheduleCreate, db: Session = Depends(get_db)):
    db.add(ScheduleDB(**item.dict()))
    db.commit()
    return {"status": "success"}

@app.post("/api/request")
def create_request(req: RequestCreate, db: Session = Depends(get_db)):
    db.add(RequestDB(**req.dict()))
    db.commit()
    return {"status": "success", "message": "Заявка отправлена!"}

@app.get("/api/requests")
def get_requests(db: Session = Depends(get_db)):
    return db.query(RequestDB).all()
