# Assuming this is in your main.py or a new file like routes/expenses.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi_jwt_auth import AuthJWT
from datetime import datetime
from typing import List, Optional

# Import models và schemas của bạn
# from . import models, schemas
# from .database import get_db

# Thay thế bằng import thực tế của bạn
import sys
import os

# Để import từ thư mục cha nếu bạn đang ở trong thư mục con (ví dụ: routes)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import User, Expense # Đảm bảo đường dẫn đúng
from schemas import LoginRequest, ExpenseCreate, ExpenseResponse, UserResponse
from database import get_db, Base, engine # Đảm bảo đường dẫn đúng

# Tạo bảng trong database nếu chưa có (chỉ gọi một lần khi khởi động ứng dụng)
# Base.metadata.create_all(bind=engine)

router = APIRouter(tags=["expenses"]) # Router mới cho các API chi tiêu

# --- API để thêm một khoản chi tiêu mới ---
@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    Authorize.jwt_required() # Yêu cầu người dùng phải đăng nhập
    current_user_id = Authorize.get_jwt_subject()

    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db_expense = Expense(
        description=expense_data.description,
        amount=expense_data.amount,
        date=expense_data.date if expense_data.date else datetime.utcnow(), # Sử dụng ngày người dùng nhập hoặc ngày hiện tại
        user_id=current_user_id
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

# --- API để lấy tất cả chi tiêu của người dùng hiện tại ---
@router.get("/expenses", response_model=List[ExpenseResponse])
def get_user_expenses(
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    Authorize.jwt_required()
    current_user_id = Authorize.get_jwt_subject()

    expenses = db.query(Expense).filter(Expense.user_id == current_user_id).all()
    return expenses

# --- API để lấy một chi tiêu cụ thể theo ID ---
@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense_by_id(
    expense_id: str,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    Authorize.jwt_required()
    current_user_id = Authorize.get_jwt_subject()

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user_id # Đảm bảo chỉ lấy chi tiêu của người dùng hiện tại
    ).first()

    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found or you don't have access")
    return expense

# --- API để cập nhật một khoản chi tiêu ---
@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: str,
    expense_data: ExpenseCreate, # Có thể dùng lại schema Create hoặc tạo schema riêng cho Update nếu có trường Optional
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    Authorize.jwt_required()
    current_user_id = Authorize.get_jwt_subject()

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user_id
    ).first()

    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found or you don't have access")

    # Cập nhật các trường
    expense.description = expense_data.description
    expense.amount = expense_data.amount
    expense.date = expense_data.date if expense_data.date else expense.date # Giữ lại ngày cũ nếu không gửi ngày mới
    expense.updated_at = datetime.utcnow() # Tự động cập nhật thời gian cập nhật

    db.commit()
    db.refresh(expense)
    return expense

# --- API để xóa một khoản chi tiêu ---
@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: str,
    db: Session = Depends(get_db),
    Authorize: AuthJWT = Depends()
):
    Authorize.jwt_required()
    current_user_id = Authorize.get_jwt_subject()

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user_id
    ).first()

    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found or you don't have access")

    db.delete(expense)
    db.commit()
    return {"detail": "Expense deleted successfully"}


# Đăng ký router này vào ứng dụng FastAPI chính của bạn
# Ví dụ trong main.py:
# from fastapi import FastAPI
# from .routes import auth, expenses # Nếu bạn đặt các router trong thư mục routes
# app = FastAPI()
# app.include_router(auth.router)
# app.include_router(expenses.router)

# Hoặc nếu bạn muốn đặt tất cả trong một file:
# app = FastAPI()
# # Thêm các API Auth vào app (ví dụ như đoạn code login/whoami của bạn)
# @app.post("/login" , tags=["auth"])
# ...
# @app.get("/whoami" , tags=["auth"])
# ...
# # Thêm các API Expense vào app
# app.include_router(router)