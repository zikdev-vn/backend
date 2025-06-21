# routes/register.py
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel , EmailStr
from sqlalchemy.orm import Session
from config_database import User
from config_database import SessionLocal
import redis.asyncio as redis
#from fastapi_limiter.depends import RateLimiter
#from fastapi_limiter import FastAPILimiter
import traceback 

router = APIRouter()

# Schema cho dữ liệu gửi lên
class CreateregisterRequest(BaseModel):
    username:str
    name: str
    password: str
    email : EmailStr

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoint đăng ký
@router.post("/register", tags=["auth"])
async def register(request: Request, form: CreateregisterRequest, db: Session = Depends(get_db)):
    ip = request.client.host or "unknown-ip"
    user_agent = request.headers.get("User-Agent", "unknown-ua")

    try:
        print(" Payload received:", await request.json())

        if db.query(User).filter_by(name=form.name).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        
        if db.query(User).filter_by(email=form.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(name=form.name, email=form.email)
        user.set_password(form.password)
        db.add(user)
        db.commit()
        db.refresh(user)

        print("✅ User created:", user)

        return {
            "msg": "Registered successfully",
            "user": {
                "id": user.id,
                "username":user.username,
                "name": user.name,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat()
            }
        }

    except Exception as e:
        print("error register:")
        traceback.print_exc()  # in stacktrace chi tiết
        raise e  
