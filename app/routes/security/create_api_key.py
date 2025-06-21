from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

import secrets
import hashlib
from datetime import datetime, timedelta
from config_database import ApiKey

def cleanup_expired_keys(db: Session):
    expired_keys = db.query(ApiKey).filter(
        ApiKey.expires_at != None,
        ApiKey.expires_at < datetime.utcnow()
    )

    count = expired_keys.count()
    expired_keys.delete(synchronize_session=False)
    db.commit()
    print(f" Đã xoá {count} API key hết hạn.")


def generate_api_key(purpose, db, usage_limit=0, expires_in_days=None):
    raw_key = secrets.token_hex(32)
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()

    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    new_key = ApiKey(
        key=hashed,
        usage_limit=usage_limit,
        expires_at=expires_at,
        purpose=purpose,
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    return raw_key
 


def verify_api_key(expected_purpose: str):
    def inner(x_api_key: str = Header(...), db: Session = Depends(get_db)):
        hashed = hashlib.sha256(x_api_key.encode()).hexdigest()
        key = db.query(ApiKey).filter(ApiKey.key == hashed).first()

        if not key or key.purpose != expected_purpose:
            raise HTTPException(status_code=403, detail="Invalid or unauthorized API key")

        if key.expires_at and key.expires_at < datetime.utcnow():
            raise HTTPException(status_code=403, detail="API key expired")

        if key.usage_limit and key.used_count >= key.usage_limit:
            raise HTTPException(status_code=429, detail="API key usage limit exceeded")

        key.used_count += 1
        db.commit()
        return True
    return inner

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from config_database import get_db
from sqlalchemy.orm import Session
import os

router = APIRouter()

# Config: mật khẩu xác thực tạo key
ADMIN_SECRET =  os.getenv("ADMIN_SECRET")

class CreateKeyRequest(BaseModel):
    secret: str
    purpose: str  # 'refresh' hoặc 'valid'
    usage_limit: int = 0
    expires_in_days: int = 0

@router.post("/create_key", tags=["API Key"])
def create_key(data: CreateKeyRequest, db: Session = Depends(get_db)):
    if data.secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if data.purpose not in ["refresh", "valid"]:
        raise HTTPException(status_code=400, detail="Invalid purpose")

    if data.purpose == "refresh" and not data.usage_limit:
        raise HTTPException(status_code=400, detail="Must set usage_limit for refresh")

    if data.purpose == "valid" and not data.expires_in_days:
        raise HTTPException(status_code=400, detail="Must set expires_in_days for valid")

    key = generate_api_key(
        purpose=data.purpose,
        db=db,
        usage_limit=data.usage_limit,
        expires_in_days=data.expires_in_days
    )
    return {"api_key": key}
