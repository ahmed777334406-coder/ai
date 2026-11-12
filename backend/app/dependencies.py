from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole, RevokedToken
from hashlib import sha256
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)

def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials if credentials else request.cookies.get("smartfind_visitor")
    if not token:
        raise HTTPException(status_code=401, detail="Visitor session required")
    payload = decode_access_token(token)
    if not credentials and payload.get("role") != "VISITOR":
        raise HTTPException(status_code=401, detail="Invalid visitor session")
    if db.get(RevokedToken, sha256(token.encode()).hexdigest()):
        raise HTTPException(status_code=401, detail="Session has been logged out")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account unavailable")
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user
