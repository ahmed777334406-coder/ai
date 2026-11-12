from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
def list_notifications(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(max(1, min(limit, 100))).all()
    return [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "payload": n.payload, "is_read": n.is_read, "created_at": n.created_at} for n in rows]

@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not row: raise HTTPException(404, "Notification not found")
    row.is_read = True; db.commit()
    return {"success": True, "id": row.id, "is_read": row.is_read}
