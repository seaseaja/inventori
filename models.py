from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Barang(SQLModel, table=True):
    __tablename__ = "barang"
    kode: str = Field(primary_key=True, max_length=10)
    nama_barang: str = Field(max_length=100)
    harga_beli: float
    harga_jual: float
    stok: int


class User(SQLModel, table=True):
    __tablename__ = "users"  # "user" itu reserved word di PostgreSQL
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=30, unique=True, index=True)
    email: str = Field(max_length=100, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=now_utc)