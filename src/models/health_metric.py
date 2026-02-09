from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from src.database.connection import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True)
    telegram_chat_id = Column(String(100), nullable=True)
    
    tokens = relationship("OAuthToken", back_populates="user", uselist=False)
    metrics = relationship("HealthMetric", back_populates="user")

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=True)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="tokens")

class HealthMetric(Base):
    __tablename__ = "health_metrics"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    steps = Column(Integer, default=0)
    sleep_hours = Column(Float, default=0.0)
    heart_rate_avg = Column(Float, nullable=True)

    user = relationship("User", back_populates="metrics")