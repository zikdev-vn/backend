import fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Body
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
import uvicorn
import os
from app.routes import include_all_routes
from dotenv import load_dotenv
from config_database import create_tables
from starlette.middleware.trustedhost import TrustedHostMiddleware

load_dotenv()

create_tables()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    #TrustedHostMiddleware,
    allow_origins=["*"],  # Có thể chỉnh theo domain cụ thể khi deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

include_all_routes(app)


#submit_form()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

