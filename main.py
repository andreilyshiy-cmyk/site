from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import bcrypt
import os

# Автоматически используем локальную БД
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

@app.post("/api/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Логин уже занят!")
    hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
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
    return {"status": "success", "message": f"Пользователь #{user_id} обновлен!"}

@app.delete("/api/admin/user/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(user)
    db.commit()
    return {"status": "success", "message": f"Пользователь #{user_id} удален"}
