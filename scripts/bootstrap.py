"""Idempotent campus setup. Admin is provisioned only with an explicit private password."""
from app.config import settings
from app.database import SessionLocal
from app.models import CampusZone, User, UserRole
from app.security import hash_password

ZONES = [
    ("LIBRARY", "University Library", "图书馆", ["TEACHING"]),
    ("TEACHING", "Teaching Buildings", "教学楼", ["LIBRARY", "CAFETERIA"]),
    ("CAFETERIA", "Campus Cafeteria", "食堂", ["TEACHING", "DORMS"]),
    ("DORMS", "Student Residences", "学生宿舍", ["CAFETERIA"]),
    ("SPORTS", "Sports Centre", "体育馆", []),
]

def main():
    with SessionLocal() as db:
        for code, en, zh, adjacent in ZONES:
            if not db.query(CampusZone).filter_by(code=code).first():
                db.add(CampusZone(code=code, name_en=en, name_zh=zh, adjacent_codes=adjacent))
        if settings.admin_password:
            if len(settings.admin_password) < 16 or settings.admin_password == 'ChangeThisAdminPassword!':
                raise RuntimeError('ADMIN_PASSWORD must be a private password of at least 16 characters')
            admin = db.query(User).filter_by(email=settings.admin_email.lower()).first()
            if admin is None:
                db.add(User(email=settings.admin_email.lower(), full_name='SmartFind Administrator', role=UserRole.ADMIN,
                            password_hash=hash_password(settings.admin_password)))
            elif admin.role != UserRole.ADMIN:
                raise RuntimeError('Refusing to promote an existing student account automatically')
        db.commit()
        print('Campus setup complete; no public demo credentials created.')

if __name__ == '__main__':
    main()
