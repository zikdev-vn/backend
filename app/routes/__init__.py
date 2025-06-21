from fastapi import FastAPI
from app.routes.security.captcha import router as captcha_api
from app.routes.auth.Login import router as Login_api
from app.routes.auth.Register import router as Register_api
from app.routes.Temp.TempMail import router as TempMail_api


def include_all_routes(app: FastAPI):
    app.include_router(Register_api, prefix="/api")
    app.include_router(Login_api, prefix="/api")
    app.include_router(TempMail_api, prefix="/api")
    app.include_router(captcha_api, prefix="/api")