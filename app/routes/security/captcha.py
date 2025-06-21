from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import os
router = APIRouter()

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
VERIFY_URL = os.getenv("TURNSTILE_VERIFY_URL")

class TurnstileToken(BaseModel):
    token: str

@router.post("/verify-turnstile", tags=["captcha"])
def verify_turnstile(data: TurnstileToken):
    if not data.token:
        raise HTTPException(status_code=400, detail="Thiếu token")

    payload = {
        "secret": TURNSTILE_SECRET_KEY,
        "response": data.token
    }

    try:
        response = requests.post(VERIFY_URL, data=payload)
        result = response.json()

        if result.get("success"):
            return {"success": True}
        else:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "message": "Token không hợp lệ", "data": result}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"success": False, "message": "Lỗi hệ thống", "error": str(e)})

