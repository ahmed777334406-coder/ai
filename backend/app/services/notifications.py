from sqlalchemy.orm import Session
from app.models import Notification

def notify_once(db: Session, user_id: int, kind: str, title: str, body: str, payload: dict, dedupe_key: str) -> None:
    if db.query(Notification).filter(Notification.dedupe_key == dedupe_key).first():
        return
    db.add(Notification(user_id=user_id, kind=kind, title=title, body=body, payload=payload, dedupe_key=dedupe_key))
