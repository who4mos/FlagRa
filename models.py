from datetime import datetime
from database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, DateTime, func

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

    histories: Mapped[list["History"]] = relationship(back_populates="user")

    def __init__(self, username: str, password_hash: str):
        self.username = username
        self.password_hash = password_hash


class History(db.Model):
    __tablename__ = "history"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)    # alternatives or fill in
    corrects: Mapped[int] = mapped_column(nullable=False)
    played_at: Mapped[datetime] = mapped_column(DateTime,
                                                server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="histories")

    def __init__(self, user_id, region, mode, corrects):
        self.user_id = user_id
        self.region = region
        self.mode = mode
        self.corrects = corrects

