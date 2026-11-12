#!/usr/bin/env python3
"""Create clearly labelled synthetic demonstration records for local testing."""
import io, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import settings
if settings.environment.lower() == "production":
    raise SystemExit("Local demo seeding is disabled in production; create fictional reports through the application.")
from app.database import Base, engine, SessionLocal, ensure_database_extensions
from app.models import User, UserRole, CampusZone, Listing, ListingStatus, ListingImage, TextEmbedding, ImageEmbedding
from app.security import hash_password
from app.services.embeddings import embed_text
from app.services.vision import embed_image

DEMO = ROOT / "data" / "demo" / "images"
DEMO.mkdir(parents=True, exist_ok=True)

def draw_item(kind: str, filename: str):
    image = Image.new("RGB", (512, 384), "#f4f6f8")
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((18, 18, 494, 366), radius=24, outline="#d5dce5", width=3, fill="#ffffff")
    if kind == "earbuds":
        d.rounded_rectangle((185, 120, 330, 265), radius=42, fill="#17191d", outline="#555b65", width=5)
        d.ellipse((212, 156, 254, 198), fill="#f6f7f8"); d.ellipse((260, 156, 302, 198), fill="#f6f7f8")
        d.arc((225, 190, 290, 248), 180, 350, fill="#858b95", width=4)
    elif kind == "wallet":
        d.rounded_rectangle((120, 115, 390, 270), radius=25, fill="#2563a6", outline="#153e69", width=8)
        d.line((130, 195, 380, 195), fill="#78a7d8", width=7)
        d.ellipse((325, 180, 355, 210), fill="#c5d9ef")
    elif kind == "backpack":
        d.rounded_rectangle((145, 85, 365, 300), radius=75, fill="#b83232", outline="#742020", width=9)
        d.rounded_rectangle((190, 200, 320, 290), radius=25, fill="#922929", outline="#e58c8c", width=5)
        d.arc((170, 45, 340, 180), 180, 360, fill="#762525", width=15)
    elif kind == "keys":
        d.ellipse((150, 135, 245, 230), outline="#b4a15e", width=22)
        d.line((225, 185, 365, 185), fill="#b4a15e", width=22)
        d.line((325, 185, 325, 235), fill="#b4a15e", width=16)
        d.line((360, 185, 360, 220), fill="#b4a15e", width=16)
    elif kind == "bottle":
        d.rounded_rectangle((205, 90, 310, 305), radius=30, fill="#2c8a72", outline="#145849", width=7)
        d.rectangle((228, 58, 287, 100), fill="#174e43")
        d.rounded_rectangle((218, 150, 297, 205), radius=10, fill="#d7eee8")
    image.save(filename, format="PNG")

for kind in ["earbuds", "wallet", "backpack", "keys", "bottle"]:
    draw_item(kind, DEMO / f"{kind}.png")

ensure_database_extensions(); Base.metadata.create_all(engine)
db = SessionLocal()
try:
    student = db.query(User).filter(User.email == "student@example.edu").first()
    if not student:
        student = User(email="student@example.edu", full_name="Demo Student", password_hash=hash_password("StudentDemo123!"), role=UserRole.STUDENT)
        db.add(student)
    finder = db.query(User).filter(User.email == "finder@example.edu").first()
    if not finder:
        finder = User(email="finder@example.edu", full_name="Demo Finder", password_hash=hash_password("FinderDemo123!"), role=UserRole.STUDENT)
        db.add(finder)
    admin = db.query(User).filter(User.email == settings.admin_email.lower()).first()
    if not admin:
        admin = User(email=settings.admin_email.lower(), full_name="SmartFind Administrator", password_hash=hash_password(settings.admin_password or "LocalAdminDemo123!"), role=UserRole.ADMIN)
        db.add(admin)
    db.flush()

    zone_specs = [
        ("LIBRARY", "Main Library", "主图书馆", ["ENGINEERING", "CAFETERIA"]),
        ("ENGINEERING", "Engineering Building", "工程楼", ["LIBRARY", "DORM_A"]),
        ("CAFETERIA", "Student Cafeteria", "学生食堂", ["LIBRARY", "GYM"]),
        ("GYM", "Sports Hall", "体育馆", ["CAFETERIA", "DORM_A"]),
        ("DORM_A", "Residence Zone A", "A区宿舍", ["ENGINEERING", "GYM"]),
    ]
    zones = {}
    for code, en, zh, adjacent in zone_specs:
        zone = db.query(CampusZone).filter(CampusZone.code == code).first()
        if not zone:
            zone = CampusZone(code=code, name_en=en, name_zh=zh, adjacent_codes=adjacent)
            db.add(zone)
        else:
            zone.name_en, zone.name_zh, zone.adjacent_codes = en, zh, adjacent
        zones[code] = zone
    db.flush()

    records = [
        ("LOST", student, "Black wireless earbuds", "I lost a black wireless earbuds case near the main library. The case is compact and has two white earbuds inside.", "Electronics", "Black", "LIBRARY", "earbuds", 0, "The left earbud has a tiny scratch on the inner hinge."),
        ("FOUND", finder, "黑色蓝牙耳机盒", "我在主图书馆附近捡到一个黑色蓝牙耳机盒，里面有两只白色耳机。", "Electronics", "Black", "LIBRARY", "earbuds", 0, "Small scratch near the inner hinge."),
        ("LOST", student, "Blue wallet", "A blue wallet with a snap button was lost between the engineering building and the cafeteria.", "Wallets", "Blue", "ENGINEERING", "wallet", 1, "There is a faded star sticker inside."),
        ("FOUND", finder, "蓝色钱包", "在工程楼附近发现一个蓝色钱包，带有按扣。", "Wallets", "Blue", "ENGINEERING", "wallet", 1, "A faded star sticker is inside."),
        ("LOST", student, "Red backpack", "A red backpack was left near the sports hall after practice.", "Bags", "Red", "GYM", "backpack", 2, "One zipper pull is silver."),
        ("FOUND", finder, "Black backpack", "A black backpack was found near the sports hall.", "Bags", "Black", "GYM", "backpack", 2, "One zipper pull is silver."),
        ("LOST", student, "Small key ring", "I lost a small silver key ring near the residence zone.", "Keys", "Silver", "DORM_A", "keys", 3, "Three keys and a round metal ring."),
        ("FOUND", finder, "钥匙串", "在宿舍区附近捡到一串银色钥匙，有三个钥匙。", "Keys", "Silver", "DORM_A", "keys", 3, "Three keys and a round ring."),
        ("FOUND", finder, "Green water bottle", "A green reusable water bottle was found in the cafeteria.", "Water Bottles", "Green", "CAFETERIA", "bottle", 4, "A pale label is wrapped around the middle."),
    ]
    for status, owner, title, desc, category, color, zone, image_kind, day_offset, private in records:
        existing = db.query(Listing).filter(Listing.title == title, Listing.is_synthetic.is_(True)).first()
        if existing: continue
        listing = Listing(owner_id=owner.id, status=ListingStatus(status), title=title, description=desc,
                          category=category, color=color, zone_id=zones[zone].id,
                          occurred_at=datetime.now(timezone.utc) - timedelta(days=day_offset),
                          private_identifiers=private, is_synthetic=True)
        db.add(listing); db.flush()
        vector, method = embed_text(f"{title}. {desc}. {category}. {color}", "passage")
        db.add(TextEmbedding(listing_id=listing.id, vector=vector, method=method, dimensions=len(vector)))
        source_image = DEMO / f"{image_kind}.png"
        public_dir = Path(settings.upload_dir) / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        image_path = public_dir / f"demo-{image_kind}.png"
        if not image_path.exists(): image_path.write_bytes(source_image.read_bytes())
        image = ListingImage(listing_id=listing.id, storage_path=str(image_path), public_url=f"/media/public/{image_path.name}",
                             sha256=__import__("hashlib").sha256(image_path.read_bytes()).hexdigest(), mime_type="image/png")
        db.add(image); db.flush()
        image_vector, image_method = embed_image(str(image_path))
        db.add(ImageEmbedding(image_id=image.id, vector=image_vector, method=image_method, dimensions=len(image_vector)))
    db.commit()
    print("Synthetic demo data seeded.")
    print("Student: student@example.edu / StudentDemo123!")
    print("Finder:  finder@example.edu / FinderDemo123!")
    print(f"Admin:   {settings.admin_email} / value from ADMIN_PASSWORD")
finally:
    db.close()
