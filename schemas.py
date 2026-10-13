from sqlmodel import SQLModel, Field
from typing import Optional


class Barang(SQLModel, table=True):
    __tablename__ = "barang"

    kode: str = Field(primary_key=True, max_length=10)
    nama_barang: str = Field(max_length=100)
    harga_beli: float
    harga_jual: float
    stok: int