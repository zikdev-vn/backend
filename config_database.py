from sqlalchemy import Text, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
DATABASE_URL = "sqlite:///./database.db"
Base = declarative_base()

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def create_tables():
    
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def generate_secure_id():
    return str(uuid.uuid4())


def add_username_column_if_missing():
    # Kiểm tra xem bảng 'user' có cột 'username' không
    inspector = inspect(engine)
    columns = [column['name'] for column in inspector.get_columns('user')]

    # Kiểm tra nếu cột 'username' chưa có trong bảng
    if 'username' not in columns:
        print("Cột 'username' không tồn tại. Đang thêm cột vào bảng 'user'...")
        
        # Thêm cột 'username' mà không có UNIQUE
        with engine.connect() as conn:
            try:
                # Thêm cột mà không có UNIQUE trước
                conn.execute(text("ALTER TABLE user ADD COLUMN username VARCHAR(120)"))
                print("Cột 'username' đã được thêm vào bảng 'user' mà không có UNIQUE.")
                
                # Sau khi thêm cột, cập nhật dữ liệu cho các bản ghi hiện tại
                conn.execute(text("UPDATE user SET username = name WHERE username IS NULL"))
                print("Cột 'username' đã được cập nhật cho các bản ghi hiện tại.")
                
                # Kiểm tra lại sự tồn tại của cột 'username' sau khi thêm
                columns = [column['name'] for column in inspector.get_columns('user')]
                if 'username' in columns:
                    print("Cột 'username' đã được thêm thành công.")
                else:
                    print("Lỗi: Cột 'username' không thể thêm vào bảng.")
                    
                # Thêm lại ràng buộc UNIQUE cho cột 'username'
                conn.execute(text("CREATE UNIQUE INDEX idx_username ON user(username)"))
                print("Ràng buộc UNIQUE đã được thêm cho cột 'username'.")
                
                # Kiểm tra lại các giá trị trong cột 'username' sau khi cập nhật
                result = conn.execute(text("SELECT username, COUNT(*) FROM user GROUP BY username HAVING COUNT(*) > 1"))
                duplicates = result.fetchall()
                if duplicates:
                    print("Cảnh báo: Có bản ghi trùng lặp trong cột 'username'.")
                    print(duplicates)
                else:
                    print("Không có bản ghi trùng lặp trong cột 'username'.")
                    
            except OperationalError as e:
                print(f"Đã xảy ra lỗi khi thêm cột 'username': {e}")
    else:
        print("Cột 'username' đã tồn tại trong bảng 'user'. Không cần thêm.")

# Gọi hàm kiểm tra và thêm cột nếu cần
add_username_column_if_missing()
# table for storing transaction history

class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True, default=generate_secure_id)
    name=Column(String(120), unique=True, nullable=False)
    username = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_time = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    transactions = relationship("TransactionHistory", back_populates="user")
    avatar_url = Column(String(255), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, index=True, nullable=False)  # SHA256 = 64 ký tự hex
    purpose = Column(String(20), nullable=False)  # Ví dụ: 'refresh' hoặc 'valid'
    usage_limit = Column(Integer, default=0)      # 0 = không giới hạn
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TransactionHistory(Base):
    __tablename__ = "transaction_history"

    id = Column(Integer, primary_key=True, index=True) # Added index for faster lookups
    user_id = Column(String, ForeignKey("user.id"), nullable=False) # Changed to String to match User.id type
    order_id = Column(String(100), index=True) # Added index
    request_id = Column(String(100))
    amount = Column(Integer)
    status = Column(String(50)) # e.g., "SUCCESS", "FAILED", "PENDING", "ERROR"
    message = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return f"<TransactionHistory {self.order_id} - {self.status}>"


class TempEmail(Base):
    __tablename__ = "temp_emails_users"

    email = Column(String, primary_key=True, index=True)
    password = Column(String)
