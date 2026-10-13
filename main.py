import os
import csv
from io import StringIO
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select, func
from starlette.middleware.sessions import SessionMiddleware

from database import create_db_and_tables, get_session
from models import Barang
from auth import router as auth_router, require_login, NotAuthenticated

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY belum diisi di file .env")

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=60 * 60 * 24 * 7,  # login bertahan 7 hari
    same_site="lax",
)
app.include_router(auth_router)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.exception_handler(NotAuthenticated)
def not_authenticated_handler(request: Request, exc: NotAuthenticated):
    return RedirectResponse("/login?msg=Silakan login dulu", status_code=303)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="home.html",
        context={"data": {
            "judul": "Sistem Informasi Inventori",
            "kampus": "PT. XYZ",
            "deskripsi": "Aplikasi pengelolaan data barang."
        }}
    )


# ---- search + sort + total nilai stok + filter stok ----
@app.get("/barang", dependencies=[Depends(require_login)])
def barang(
    request: Request,
    q: str = "",
    sort: str = "kode",
    order: str = "asc",
    filter_stok: str = "semua",
    msg: str = "",
    session: Session = Depends(get_session)
):
    kolom_valid = {
        "kode": Barang.kode,
        "nama_barang": Barang.nama_barang,
        "harga_beli": Barang.harga_beli,
        "harga_jual": Barang.harga_jual,
        "stok": Barang.stok,
    }
    kolom_sort = kolom_valid.get(sort, Barang.kode)
    if sort not in kolom_valid:
        sort = "kode"

    statement = select(Barang)
    if q:
        statement = statement.where(Barang.nama_barang.ilike(f"%{q}%"))

    if filter_stok == "menipis":
        statement = statement.where(Barang.stok < 10)
    elif filter_stok == "aman":
        statement = statement.where(Barang.stok >= 10)

    statement = statement.order_by(kolom_sort.desc() if order == "desc" else kolom_sort.asc())
    data = session.exec(statement).all()

    total_jenis = session.exec(select(func.count(Barang.kode))).one()
    total_nilai = session.exec(
        select(func.coalesce(func.sum(Barang.harga_beli * Barang.stok), 0))
    ).one()
    stok_menipis = session.exec(
        select(func.count(Barang.kode)).where(Barang.stok < 10)
    ).one()

    return templates.TemplateResponse(
        request=request, name="barang.html",
        context={
            "barang": data,
            "q": q,
            "sort": sort,
            "order": order,
            "filter_stok": filter_stok,
            "total_nilai": total_nilai,
            "total_jenis": total_jenis,
            "stok_menipis": stok_menipis,
            "msg": msg,
        }
    )


# ---- Export CSV ----
@app.get("/barang/export", dependencies=[Depends(require_login)])
def export_csv(session: Session = Depends(get_session)):
    data = session.exec(select(Barang)).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Kode", "Nama Barang", "Harga Beli", "Harga Jual", "Stok", "Total Nilai"])

    for item in data:
        writer.writerow([
            item.kode,
            item.nama_barang,
            item.harga_beli,
            item.harga_jual,
            item.stok,
            item.harga_beli * item.stok
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data_barang.csv"}
    )


@app.get("/insert", dependencies=[Depends(require_login)])
def form_insert(request: Request):
    return templates.TemplateResponse(
        request=request, name="insert.html", context={"error": ""}
    )


# ---- validasi kode duplikat ----
@app.post("/insert", dependencies=[Depends(require_login)])
def insert(
    request: Request,
    kode: str = Form(...),
    nama_barang: str = Form(...),
    harga_beli: float = Form(...),
    harga_jual: float = Form(...),
    stok: int = Form(...),
    session: Session = Depends(get_session)
):
    existing = session.get(Barang, kode)
    if existing:
        return templates.TemplateResponse(
            request=request, name="insert.html",
            context={"error": f"Kode '{kode}' sudah dipakai, pakai kode lain."}
        )
    new_barang = Barang(
        kode=kode, nama_barang=nama_barang,
        harga_beli=harga_beli, harga_jual=harga_jual, stok=stok
    )
    session.add(new_barang)
    session.commit()
    return RedirectResponse("/barang?msg=Barang berhasil ditambahkan", status_code=303)


@app.get("/edit/{kode}", dependencies=[Depends(require_login)])
def form_edit(kode: str, request: Request, session: Session = Depends(get_session)):
    data = session.get(Barang, kode)
    if not data:
        return RedirectResponse("/barang?msg=Barang tidak ditemukan", status_code=303)
    return templates.TemplateResponse(
        request=request, name="edit.html",
        context={"barang": data}
    )


@app.post("/edit/{kode}", dependencies=[Depends(require_login)])
def edit(
    kode: str,
    nama_barang: str = Form(...),
    harga_beli: float = Form(...),
    harga_jual: float = Form(...),
    stok: int = Form(...),
    session: Session = Depends(get_session)
):
    data = session.get(Barang, kode)
    if not data:
        return RedirectResponse("/barang?msg=Barang tidak ditemukan", status_code=303)
    data.nama_barang = nama_barang
    data.harga_beli = harga_beli
    data.harga_jual = harga_jual
    data.stok = stok
    session.add(data)
    session.commit()
    return RedirectResponse("/barang?msg=Perubahan berhasil disimpan", status_code=303)


@app.post("/delete/{kode}", dependencies=[Depends(require_login)])
def delete(kode: str, session: Session = Depends(get_session)):
    data = session.get(Barang, kode)
    if data:
        session.delete(data)
        session.commit()
    return RedirectResponse("/barang?msg=Barang berhasil dihapus", status_code=303)