from datetime import datetime
from database import db
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func

class User(db.Model):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20),
                                          unique=True,
                                          nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128),
                                               nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 server_default=func.now())

    def __init__(self, username: str, password_hash: str):
        self.username = username
        self.password_hash = password_hash
