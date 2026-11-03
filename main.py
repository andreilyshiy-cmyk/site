from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import bcrypt

# Использование локальной базы данных SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./platform.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="guest")
    tariff = Column(String, default="Не выбран")
    status = Column(String, default="Активен")
    teacher_name = Column(String, default="Не назначен")
    lesson_link = Column(String, default="")

class RequestDB(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_name = Column(String)
    contact = Column(String)
    tariff = Column(String)
    status = Column(String, default="На рассмотрении")

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
    try:
        yield db
    finally:
        db.close()

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
    teacher_name: Optional[str] = "Не назначен"
    lesson_link: Optional[str] = ""

class RequestCreate(BaseModel):
    student_name: str
    contact: str
    tariff: str

class RequestUpdateStatus(BaseModel):
    status: str

class ScheduleCreate(BaseModel):
    day: str
    time: str
    subject: str
    teacher: str

class StaffCreate(BaseModel):
    name: str
    subject: str
    experience: Optional[str] = "Стаж 5 лет"
    bio: Optional[str] = "Преподаватель центра"
    contact_info: Optional[str] = "Telegram: @tutor_hub"
    photo_url: Optional[str] = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300"

@app.post("/api/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Логин уже занят!")
    hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    # Роль по умолчанию для всех — guest
    role = "admin" if db.query(UserDB).count() == 0 else "guest"
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
        "status_account": db_user.status,
        "teacher_name": db_user.teacher_name,
        "lesson_link": db_user.lesson_link
    }

# Все пользователи (Админ-панель)
@app.get("/api/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    return [{
        "user_id": u.id, 
        "username": u.username, 
        "role": u.role, 
        "tariff": u.tariff, 
        "status": u.status,
        "teacher_name": u.teacher_name,
        "lesson_link": u.lesson_link
    } for u in db.query(UserDB).all()]

# Запрос конкретного пользователя по ID (Логика medusa-cheat)
@app.get("/api/admin/user/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "tariff": user.tariff,
        "status": user.status,
        "teacher_name": user.teacher_name,
        "lesson_link": user.lesson_link
    }

# Сохранение/обновление профиля конкретного пользователя
@app.post("/api/admin/user/{user_id}")
def update_user_by_admin(user_id: int, data: UserUpdateAdmin, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.role = data.role
    user.tariff = data.tariff
    user.status = data.status
    user.teacher_name = data.teacher_name or "Не назначен"
    user.lesson_link = data.lesson_link or ""
    db.commit()
    return {"status": "success", "message": f"Профиль #{user_id} сохранен!"}

# Удаление пользователя
@app.delete("/api/admin/user/{user_id}")
def delete_user_by_admin(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(user)
    db.commit()
    return {"status": "success", "message": f"Пользователь #{user_id} удален"}

@app.get("/api/staff")
def get_staff(db: Session = Depends(get_db)):
    return db.query(StaffDB).all()

@app.post("/api/admin/staff")
def add_staff(item: StaffCreate, db: Session = Depends(get_db)):
    new_staff = StaffDB(
        name=item.name,
        subject=item.subject,
        experience=item.experience,
        bio=item.bio,
        contact_info=item.contact_info,
        photo_url=item.photo_url
    )
    db.add(new_staff)
    db.commit()
    return {"status": "success", "message": "Преподаватель добавлен!"}

@app.get("/api/schedules")
def get_schedules(db: Session = Depends(get_db)):
    return db.query(ScheduleDB).all()

@app.post("/api/admin/schedule")
def add_schedule(item: ScheduleCreate, db: Session = Depends(get_db)):
    db.add(ScheduleDB(**item.dict()))
    db.commit()
    return {"status": "success", "message": "Урок добавлен!"}

@app.delete("/api/admin/schedule/{sch_id}")
def delete_schedule(sch_id: int, db: Session = Depends(get_db)):
    sch = db.query(ScheduleDB).filter(ScheduleDB.id == sch_id).first()
    if not sch:
        raise HTTPException(status_code=404, detail="Урок не найден")
    db.delete(sch)
    db.commit()
    return {"status": "success", "message": "Урок удален!"}

@app.post("/api/request")
def create_request(req: RequestCreate, db: Session = Depends(get_db)):
    db.add(RequestDB(**req.dict()))
    db.commit()
    return {"status": "success", "message": "Заявка отправлена!"}

@app.get("/api/requests")
def get_requests(db: Session = Depends(get_db)):
    return db.query(RequestDB).all()

@app.post("/api/admin/request/{req_id}")
def update_request_status(req_id: int, data: RequestUpdateStatus, db: Session = Depends(get_db)):
    req = db.query(RequestDB).filter(RequestDB.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    req.status = data.status
    db.commit()
    return {"status": "success", "message": "Статус обновлен!"}
