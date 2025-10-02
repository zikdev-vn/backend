# routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi_jwt_auth import AuthJWT
from datetime import datetime
from config_database import User, get_db
import requests
from dotenv import load_dotenv
import os

load_dotenv() 


router = APIRouter()
GOOGLE_TOKEN_INFO_URL = os.getenv("GOOGLE_TOKEN_INFO_URL")      

# ----------- Schemas -----------

class GoogleLoginRequest(BaseModel):
    token: str
    
class LoginRequest(BaseModel):
    #email : EmailStr
    name: str
    password: str

# ----------- JWT Config (phải cấu hình riêng) -----------
class Settings(BaseModel):
    authjwt_secret_key: str = os.getenv("JWT_SECRET")
    print("secret key",authjwt_secret_key)

@AuthJWT.load_config
def get_config():
    return Settings()

# ----------- Routes -----------



def get_optional_user(
    Authorize: AuthJWT = Depends(),
    db: Session = Depends(get_db)
) -> User | None:
    try:
        Authorize.jwt_optional()  # ✅ Đúng cú pháp với version mới
        user_id = Authorize.get_jwt_subject()
        if user_id:
            return db.query(User).filter(User.id == user_id).first()
    except Exception as e:
        print("❌ Token lỗi:", str(e))

    return None


@router.post("/login" , tags=["auth"])
def login(form: LoginRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    user = db.query(User).filter_by(name=form.name).first()
    if not user or not user.check_password(form.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login_time = datetime.utcnow()
    user.last_login_ip = "client-ip-from-request"  # có thể lấy từ `Request.client.host` nếu cần
    db.commit()

    access_token = Authorize.create_access_token(subject=str(user.id))
    return {
        "access_token": access_token,
        "last_login_time": user.last_login_time.isoformat(),
        "last_login_ip": user.last_login_ip
    }
@router.get("/whoami" , tags=["auth"])
def whoami(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    user = db.query(User).get(user_id)  # <--- Sửa chỗ này, không ép int()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "username": user.username,
        "last_login_ip": user.last_login_ip,
        #"created_at": user.created_at.isoformat(),
        #"updated_at": user.updated_at.isoformat()
    }
@router.post("/google-login", tags=["auth"])
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    if not data.token:
        raise HTTPException(status_code=400, detail="Thiếu token")

    response = requests.get(GOOGLE_TOKEN_INFO_URL, params={"id_token": data.token})
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

    user_info = response.json()
    email = user_info.get("email")
    name = user_info.get("name") or email

    if not email:
        raise HTTPException(status_code=400, detail="Không lấy được email từ Google")

    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(
            name=name,
            email=email,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        user.set_password("")  # hoặc "google"
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = Authorize.create_access_token(subject=str(user.id))
    return {
        "access_token": access_token,
        "id": user.id,
        "name": user.name,
        "email": user.email
    }
