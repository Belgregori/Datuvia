from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: UUID  # <-- Cambiado de int a UUID
    email: str


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    domain = normalized.split("@")[-1] if "@" in normalized else ""
    if "@" not in normalized or "." not in domain:
        raise HTTPException(status_code=400, detail="Email inválido")
    return normalized


def _check_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña tiene que tener al menos 8 caracteres")
    if len(password.encode()) > 72:
        raise HTTPException(status_code=400, detail="La contraseña es demasiado larga")


@router.post("/register", response_model=UserRead, status_code=201)
def register(body: AuthRequest, session: Session = Depends(get_session)) -> User:
    email = _normalize_email(body.email)
    _check_password(body.password)
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ese email ya está registrado")

    user = User(email=email, hashed_password=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# <-- Acá cambiamos AuthRequest por OAuth2PasswordRequestForm
@router.post("/login", response_model=TokenResponse)
def login(body: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)) -> TokenResponse:
    # FastAPI usa 'username' en sus formularios de login por defecto
    email = _normalize_email(body.username) 
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user