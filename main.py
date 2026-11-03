from fastapi import FastAPI, Depends, HTTPException, Request, Header
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

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="student") # 'student', 'teacher', 'admin'
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

def seed_data():
    db = SessionLocal()
    if db.query(StaffDB).count() == 0:
        db.add_all([
            StaffDB(name="Алексей Смирнов", subject="Высшая математика", experience="Стаж 8 лет", photo_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300"),
            StaffDB(name="Екатерина Ковалева", subject="Русский язык", experience="Стаж 12 лет", photo_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=300"),
            StaffDB(name="Дмитрий Волков", subject="Информатика & Python", experience="Стаж 5 лет", photo_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300")
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

class RoleAssign(BaseModel):
    target_username: str
    new_role: str

class RequestCreate(BaseModel):
    student_name: str
    contact: str
    tariff: str

class ScheduleCreate(BaseModel):
    day: str
    time: str
    subject: str
    teacher: str

class StaffCreate(BaseModel):
    name: str
    subject: str
    experience: str
    photo_url: str

@app.post("/api/register")
def register(user: UserRegister, request: Request, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Логин уже занят!")
    hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Первый зарегистрированный пользователь или с вашего ПК получает права админа
    role = "admin" if db.query(UserDB).count() == 0 else "student"
    new_user = UserDB(username=user.username, password_hash=hashed, role=role, ip_address=request.client.host)
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": "Регистрация успешна!"}

@app.post("/api/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if not db_user or not bcrypt.checkpw(user.password.encode('utf-8'), db_user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль!")
    return {"status": "success", "username": db_user.username, "role": db_user.role}

@app.post("/api/admin/assign-role")
def assign_role(data: RoleAssign, db: Session = Depends(get_db)):
    target = db.query(UserDB).filter(UserDB.username == data.target_username).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    target.role = data.new_role
    db.commit()
    return {"status": "success", "message": "Роль обновлена!"}

@app.post("/api/admin/schedule")
def add_schedule(item: ScheduleCreate, db: Session = Depends(get_db)):
    db.add(ScheduleDB(**item.dict()))
    db.commit()
    return {"status": "success"}

@app.post("/api/admin/staff")
def add_staff(item: StaffCreate, db: Session = Depends(get_db)):
    db.add(StaffDB(**item.dict()))
    db.commit()
    return {"status": "success"}

@app.post("/api/request")
def create_request(req: RequestCreate, db: Session = Depends(get_db)):
    db.add(RequestDB(**req.dict()))
    db.commit()
    return {"status": "success", "message": "Заявка успешно отправлена!"}

@app.get("/api/requests")
def get_requests(db: Session = Depends(get_db)):
    return db.query(RequestDB).all()

@app.get("/api/schedules")
def get_schedules(db: Session = Depends(get_db)):
    return db.query(ScheduleDB).all()

@app.get("/api/staff")
def get_staff(db: Session = Depends(get_db)):
    return db.query(StaffDB).all()
