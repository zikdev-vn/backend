from fastapi import APIRouter, HTTPException, Path as FPath, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from config_database import TempEmail, get_db
import time
import requests
import random
import string
import imaplib
import email
from email.header import decode_header
from typing import Optional
import hashlib
import hmac
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from datetime import datetime
from pathlib import Path as PPath
from fastapi import Cookie


templates = Jinja2Templates(directory=str(PPath(__file__).parent))
  
templates.env.filters['datetimeformat'] = lambda value: datetime.fromtimestamp(value/1000).strftime("%Y-%m-%d %H:%M:%S")

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
load_dotenv()
API_URL = os.getenv("API_URL_TEMP")
API_TOKEN = os.getenv("API_TOKEN_TEMP")
IMAP_SERVER = os.getenv("IMAP_SERVER_TEMP")
HMAC_SECRET = os.getenv("TEMP_EMAIL_HMAC_SECRET", "ZYZZ2004@")


# ---------- UTILS ----------
def generate_random_email():
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{name}@temp.zikdev.io.vn"

def generate_random_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def decode_header_part(raw_value):
    decoded = decode_header(raw_value)
    return ''.join([
        part.decode(enc or 'utf-8') if isinstance(part, bytes) else part
        for part, enc in decoded
    ])

def sign_request_time(request_time: str) -> str:
    return hmac.new(HMAC_SECRET.encode(), request_time.encode(), hashlib.sha256).hexdigest()


# ---------- ORM DATABASE HANDLERS ----------
def get_password_from_db(db: Session, email_address: str) -> Optional[str]:
    record = db.query(TempEmail).filter(TempEmail.email == email_address).first()
    return record.password if record else None

def save_email_to_db(db: Session, email: str, password: str):
    existing = db.query(TempEmail).filter_by(email=email).first()
    if existing:
        existing.password = password
    else:
        db.add(TempEmail(email=email, password=password))
    db.commit()


# ---------- EMAIL FETCH ----------
def fetch_latest_emails(email_address: str, password: str, limit: int = 5):
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(email_address, password)
    imap.select("INBOX")
    status, messages = imap.search(None, "ALL")
    mail_ids = messages[0].split()

    result = []
    for mail_id in mail_ids[-limit:]:
        status, msg_data = imap.fetch(mail_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject_raw = msg.get("Subject", "")
                subject = decode_header_part(subject_raw)

                from_raw = msg.get("From", "")
                sender = decode_header_part(from_raw)

                body = ""
                html_body = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        disposition = part.get_content_disposition()
                        charset = part.get_content_charset() or "utf-8"

                        if content_type == "text/plain" and disposition is None:
                            body = part.get_payload(decode=True).decode(charset, errors="replace")
                        elif content_type == "text/html" and disposition is None and not body:
                            html_body = part.get_payload(decode=True).decode(charset, errors="replace")
                else:
                    content_type = msg.get_content_type()
                    charset = msg.get_content_charset() or "utf-8"
                    if content_type == "text/plain":
                        body = msg.get_payload(decode=True).decode(charset, errors="replace")
                    elif content_type == "text/html":
                        html_body = msg.get_payload(decode=True).decode(charset, errors="replace")

                final_body = body if body else html_body

                result.append({
                    "from": sender,
                    "subject": subject,
                    "body": final_body[:1000],
                    "html": html_body[:10000]
                })

    imap.logout()
    return result


# ---------- ROUTES ----------
class SecureRequest(BaseModel):
    requestTime: str
    lang: Optional[str] = "en"
    signature: str 




@router.get("/gmail-new", response_class=HTMLResponse)
def create_mail_html(
    request: Request,
    lang: Optional[str] = "en",
    db: Session = Depends(get_db)
):
    # Tạo chữ ký và thời gian
    request_time = str(int(time.time() * 1000))
    signature = sign_request_time(request_time)

    email_addr = generate_random_email()
    password = generate_random_password()

    mail_payload = {
        "email": email_addr,
        "raw_password": password,
        "comment": "created via FastAPI",
        "quota_bytes": 1000000000,
        "global_admin": False,
        "enabled": True,
        "change_pw_next_login": True,
        "enable_imap": True,
        "enable_pop": True,
        "allow_spoofing": True,
        "forward_enabled": False,
        "forward_destination": [],
        "forward_keep": True,
        "reply_enabled": False,
        "reply_subject": "",
        "reply_body": "",
        "reply_startdate": "2025-01-01",
        "reply_enddate": "2025-01-10",
        "spam_threshold": 80
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }

    response = requests.post(API_URL, json=mail_payload, headers=headers, verify=False)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Email API failed: {response.text}")

    # Lưu vào DB
    save_email_to_db(db, email_addr, password)

    # Render HTML template giống /gmail-new
    expires = int(time.time() + 3600) * 1000
    html_response = templates.TemplateResponse("tempmail.html", {
        "request": request,
        "email": email_addr,
        "expires": expires
    })
    
    # Set cookie
    html_response.set_cookie(key="temp_email", value=email_addr, max_age=3600)
    html_response.headers["Content-Security-Policy"] = "frame-ancestors 'self' http://localhost:3000"

    return html_response

@router.post("/createmail", tags=["TempEmail"])
def create_mail(lang: Optional[str] = "en", db: Session = Depends(get_db)):
    # Tự tạo thời gian và chữ ký
    request_time = str(int(time.time() * 1000))
    signature = sign_request_time(request_time)

    email_addr = generate_random_email()
    password = generate_random_password()

    mail_payload = {
        "email": email_addr,
        "raw_password": password,
        "comment": "created via FastAPI",
        "quota_bytes": 1000000000,
        "global_admin": False,
        "enabled": True,
        "change_pw_next_login": True,
        "enable_imap": True,
        "enable_pop": True,
        "allow_spoofing": True,
        "forward_enabled": False,
        "forward_destination": [],
        "forward_keep": True,
        "reply_enabled": False,
        "reply_subject": "",
        "reply_body": "",
        "reply_startdate": "2025-01-01",
        "reply_enddate": "2025-01-10",
        "spam_threshold": 80
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
        
    }

    response = requests.post(API_URL, json=mail_payload, headers=headers , verify=False)
    if response.status_code == 200:
        save_email_to_db(db, email_addr, password)
        return {
            "code": 0,
            "message": "Success",
            "data": {
                "id": email_addr.split("@")[0],
                "name": email_addr,
                "expires": int(time.time() + 3600) * 1000,  # Hết hạn sau 1 giờ
                "requestTime": request_time,
                "signature": signature
            }
        }
    else:
        raise HTTPException(status_code=500, detail=f"Email API failed: {response.text}")


@router.get("/getmail/{email_address}", tags=["TempEmail"])
@limiter.limit("5/minute")
def get_mail(
    request: Request,
    email_address: str = FPath(..., description="Email muốn xem"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    password = get_password_from_db(db, email_address)
    if not password:
        raise HTTPException(status_code=404, detail="Email không tồn tại hoặc chưa được tạo")

    try:
        emails = fetch_latest_emails(email_address, password, limit)
        return {
            "code": 0,
            "message": "Success",
            "data": {
                "email": email_address,
                "count": len(emails),
                "inbox": emails
            }
        }
    except imaplib.IMAP4.error as e:
        raise HTTPException(status_code=400, detail=f"IMAP login failed: {str(e)}")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(ex)}")


@router.delete("/deletemail/{email_address}", tags=["TempEmail"])
def delete_mail(
    email_address: str = FPath(..., description="Email muốn xóa"),
    db: Session = Depends(get_db)
):
    password = get_password_from_db(db, email_address)

    url = f"{API_URL}/{email_address}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }

    response = requests.delete(url, headers=headers, verify=False)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Email không tồn tại hoặc đã bị xóa trước đó")
    elif response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Lỗi từ API mail server: {response.text}")

    db.query(TempEmail).filter(TempEmail.email == email_address).delete()
    db.commit()

    return {"code": 0, "message": "Email đã được xóa thành công"}
