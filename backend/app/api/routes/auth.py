import secrets
from fastapi import Request, Response
from app.config import settings
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, bearer
from fastapi.security import HTTPAuthorizationCredentials
from hashlib import sha256
from datetime import datetime, timezone
from app.models import User, UserRole, RevokedToken
from app.schemas import UserLogin, UserOut, TokenOut
from app.security import verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/session", response_model=UserOut)
def visitor_session(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("smartfind_visitor")
    if token:
        try:
            payload = decode_access_token(token)
            user = db.get(User, int(payload["sub"]))
            if payload.get("role") == "VISITOR" and user and user.is_active and not db.get(RevokedToken, sha256(token.encode()).hexdigest()):
                return user
        except HTTPException:
            pass
    identifier = secrets.token_urlsafe(32)
    user = User(email=f"{identifier}@visitor.invalid", full_name="Anonymous visitor",
                password_hash="!anonymous-login-disabled", role=UserRole.STUDENT)
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie("smartfind_visitor", create_access_token(user.id, "VISITOR", settings.visitor_session_days * 86400),
                        httponly=True, secure=settings.environment.lower() == "production",
                        samesite="lax", path="/", max_age=settings.visitor_session_days * 86400)
    response.headers["Cache-Control"] = "no-store"
    return user

@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or user.role != UserRole.ADMIN or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "This account is disabled")
    return TokenOut(access_token=create_access_token(user.id, user.role.value), user=user)

@router.post("/logout")
def logout(request: Request, response: Response, user: User = Depends(get_current_user), credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    token = credentials.credentials if credentials else request.cookies.get("smartfind_visitor")
    payload = decode_access_token(token)
    db.merge(RevokedToken(token_hash=sha256(token.encode()).hexdigest(),
                         expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc)))
    db.commit()
    response.delete_cookie("smartfind_visitor", path="/")
    return {"success": True, "message": "Session revoked."}

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
