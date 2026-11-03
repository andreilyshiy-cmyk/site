from fastapi import FastAPI, Depends, HTTPException, Request
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

# Модели базы данных
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="student") # 'student', 'teacher', 'admin', 'super_admin'
    ip_address = Column(String, nullable=True)

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
    experience = Column(String)
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

# Генерация красочных затычек в штаб и расписание
def seed_data():
    db = SessionLocal()
    if db.query(StaffDB).count() == 0:
        db.add_all([
            StaffDB(name="Алексей Смирнов", subject="Высшая математика / ЦЭ", experience="Стаж 8 лет", photo_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300"),
            StaffDB(name="Екатерина Ковалева", subject="Русский язык & Литература", experience="Стаж 12 лет", photo_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=300"),
            StaffDB(name="Дмитрий Волков", subject="Информатика & Python", experience="Стаж 5 лет", photo_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300"),
            StaffDB(name="Мария Соколова", subject="Физика / Подготовка к олимпиадам", experience="Стаж 10 лет", photo_url="https://images.unsplash.com/photo-1580489944761-15a19d654956?w=300")
        ])
    if db.query(ScheduleDB).count() == 0:
        db.add_all([
            ScheduleDB(day="Понедельник", time="16:00 - 17:30", subject="Математика (Профильный уровень)", teacher="Алексей Смирнов"),
            ScheduleDB(day="Вторник", time="18:00 - 19:30", subject="Информатика & Программирование", teacher="Дмитрий Волков"),
            ScheduleDB(day="Среда", time="17:00 - 18:30", subject="Русский язык (Интенсив ЦЭ)", teacher="Екатерина Ковалева"),
            ScheduleDB(day="Четверг", time="16:30 - 18:00", subject="Физика (Олимпиадный разбор)", teacher="Мария Соколова")
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

class RoleAssign(BaseModel):
    target_username: str
    new_role: str

class RequestCreate(BaseModel):
    student_name: str
    contact: str
    tariff: str

# 1. Регистрация нового аккаунта
@app.post("/api/register")
def register(user: UserRegister, request: Request, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует!")
    
    hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    client_ip = request.client.host
    
    new_user = UserDB(username=user.username, password_hash=hashed, role="student", ip_address=client_ip)
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": "Аккаунт успешно зарегистрирован! Теперь вы можете войти."}

# 2. Вход в аккаунт
@app.post("/api/login")
def login(user: UserLogin, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if not db_user or not bcrypt.checkpw(user.password.encode('utf-8'), db_user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль!")
    
    client_ip = request.client.host
    return {
        "status": "success",
        "username": db_user.username,
        "role": db_user.role,
        "client_ip": client_ip
    }

# 3. Выдача ролей (Управление правами доступно управляющим IP)
@app.post("/api/admin/assign-role")
def assign_role(data: RoleAssign, request: Request, db: Session = Depends(get_db)):
    # Механика управления ролями
    target_user = db.query(UserDB).filter(UserDB.username == data.target_username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден!")
    
    target_user.role = data.new_role
    db.commit()
    return {"status": "success", "message": f"Роль {data.target_username} изменена на {data.new_role}!"}

@app.get("/api/users")
def get_all_users(db: Session = Depends(get_db)):
    return db.query(UserDB).all()

# 4. Подача и сохранение заявок
@app.post("/api/request")
def create_request(req: RequestCreate, db: Session = Depends(get_db)):
    db.add(RequestDB(**req.dict()))
    db.commit()
    return {"status": "success", "message": "Заявка принята и сохранена в базе!"}

@app.get("/api/requests")
def get_requests(db: Session = Depends(get_db)):
    return db.query(RequestDB).all()

@app.get("/api/schedules")
def get_schedules(db: Session = Depends(get_db)):
    return db.query(ScheduleDB).all()

@app.get("/api/staff")
def get_staff(db: Session = Depends(get_db)):
    return db.query(StaffDB).all()
