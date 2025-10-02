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

from sqlalchemy import text
from sqlalchemy.orm import Session


DATABASE_URL = "sqlite:///./database.db"
Base = declarative_base()

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}  # Chỉ cần cho SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#def drop_expense_table(db: Session):
#    db.execute(text("DROP TABLE IF EXISTS expense"))
#    db.commit()
#    print("Bảng Expense đã bị xóa.")

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

    expenses = relationship("Expense", back_populates="user")

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


class Expense(Base):
    __tablename__ = "expense"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    amount = Column(Float)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="expenses")
