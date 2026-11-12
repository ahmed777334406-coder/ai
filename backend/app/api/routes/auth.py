from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, bearer
from fastapi.security import HTTPAuthorizationCredentials
from hashlib import sha256
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from app.models import User, UserRole, RevokedToken
from app.schemas import UserCreate, UserLogin, UserOut, TokenOut
from app.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password),
                role=UserRole.STUDENT, preferred_language=payload.preferred_language if payload.preferred_language in {"en", "zh"} else "en")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists")
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id, user.role.value), user=user)

@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "This account is disabled")
    return TokenOut(access_token=create_access_token(user.id, user.role.value), user=user)

@router.post("/logout")
def logout(user: User = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    payload = decode_access_token(credentials.credentials)
    db.merge(RevokedToken(token_hash=sha256(credentials.credentials.encode()).hexdigest(),
                         expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc)))
    db.commit()
    return {"success": True, "message": "Session revoked. Discard the access token on this device."}

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

from app.schemas import ProfileUpdate

@router.patch("/me", response_model=UserOut)
def update_profile(payload: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
