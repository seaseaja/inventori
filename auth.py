import hashlib
import hmac
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import get_session
from models import User

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
router = APIRouter()

ITERATIONS = 260_000
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NotAuthenticated(Exception):
    pass


# ---------- password helper ----------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ---------- dependency buat proteksi halaman ----------
def require_login(request: Request):
    if not request.session.get("user_id"):
        raise NotAuthenticated()


# ---------- routes ----------
@router.get("/login")
def form_login(request: Request, msg: str = ""):
    if request.session.get("user_id"):
        return RedirectResponse("/barang", status_code=303)
    return templates.TemplateResponse(
        request=request, name="login.html",
        context={"error": "", "msg": msg, "username": ""}
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    uname = username.strip().lower()
    user = session.exec(select(User).where(User.username == uname)).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request, name="login.html",
            context={"error": "Username atau password salah.", "msg": "", "username": username},
            status_code=401,
        )

    request.session.clear()  # cegah session fixation
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return RedirectResponse("/barang?msg=Selamat datang, " + user.username, status_code=303)


@router.get("/register")
def form_register(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/barang", status_code=303)
    return templates.TemplateResponse(
        request=request, name="register.html",
        context={"error": "", "username": "", "email": ""}
    )


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    konfirmasi: str = Form(...),
    session: Session = Depends(get_session),
):
    uname = username.strip().lower()
    mail = email.strip().lower()

    def balik(error: str):
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": error, "username": username, "email": email},
            status_code=400,
        )

    if not USERNAME_RE.match(uname):
        return balik("Username 3-30 karakter, hanya huruf, angka, dan underscore.")
    if not EMAIL_RE.match(mail):
        return balik("Format email tidak valid.")
    if len(password) < 8:
        return balik("Password minimal 8 karakter.")
    if password != konfirmasi:
        return balik("Konfirmasi password tidak cocok.")

    if session.exec(select(User).where(User.username == uname)).first():
        return balik("Username sudah dipakai.")
    if session.exec(select(User).where(User.email == mail)).first():
        return balik("Email sudah terdaftar.")

    session.add(User(username=uname, email=mail, password_hash=hash_password(password)))
    session.commit()
    return RedirectResponse("/login?msg=Registrasi berhasil, silakan login", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login?msg=Kamu sudah logout", status_code=303)