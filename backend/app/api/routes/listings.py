from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserRole, Listing, ListingStatus, ListingState, ListingImage, ListingAIAnalysis, TextEmbedding, ImageEmbedding, CampusZone
from app.schemas import ListingCreate, ListingUpdate
from app.services.embeddings import embed_text
from app.services.vision import embed_image
from app.services.gemini import gemini_service
from app.services.storage import save_upload

router = APIRouter(prefix="/listings", tags=["listings"])

def serialize_listing(item: Listing) -> dict:
    return {
        "id": item.id, "owner_id": item.owner_id, "owner_name": "Campus student",
        "status": item.status.value, "state": item.state.value, "title": item.title, "description": item.description,
        "category": item.category, "color": item.color, "zone_id": item.zone_id,
        "zone_name_en": item.zone.name_en if item.zone else None, "zone_name_zh": item.zone.name_zh if item.zone else None,
        "occurred_at": item.occurred_at, "image_urls": [image.public_url for image in item.images if image.public_url and not image.is_private],
        "is_synthetic": item.is_synthetic, "created_at": item.created_at,
    }

def _can_edit(item: Listing, user: User) -> bool:
    return item.owner_id == user.id or user.role == UserRole.ADMIN

@router.get("")
def list_listings(status: ListingStatus | None = None, category: str | None = None, zone_id: int | None = None,
                  q: str | None = None, color: str | None = None, limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 50)); offset = max(0, offset)
    query = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone)).filter(Listing.state != ListingState.CLOSED)
    if status: query = query.filter(Listing.status == status)
    if category: query = query.filter(Listing.category.ilike(f"%{category}%"))
    if color: query = query.filter(Listing.color.ilike(f"%{color}%"))
    if zone_id: query = query.filter(Listing.zone_id == zone_id)
    if q: query = query.filter((Listing.title.ilike(f"%{q}%")) | (Listing.description.ilike(f"%{q}%")))
    total = query.count()
    rows = query.order_by(Listing.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [serialize_listing(row) for row in rows], "total": total, "limit": limit, "offset": offset}

@router.post("", status_code=201)
def create_listing(payload: ListingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.client_request_id:
        existing = db.query(Listing).filter(Listing.owner_id == user.id, Listing.client_request_id == payload.client_request_id).first()
        if existing: return serialize_listing(existing)
    if payload.zone_id and not db.get(CampusZone, payload.zone_id):
        raise HTTPException(400, "Unknown campus zone")
    item = Listing(owner_id=user.id, client_request_id=payload.client_request_id, status=payload.status, title=payload.title.strip(), description=payload.description.strip(),
                   category=payload.category.strip(), color=payload.color, zone_id=payload.zone_id,
                   occurred_at=payload.occurred_at, private_identifiers=payload.private_identifiers)
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(Listing).filter(Listing.owner_id == user.id, Listing.client_request_id == payload.client_request_id).first() if payload.client_request_id else None
        if existing: return serialize_listing(existing)
        raise
    vector, method = embed_text(f"{item.title}. {item.description}. {item.category}. {item.color or ''}", "passage")
    db.add(TextEmbedding(listing_id=item.id, vector=vector, method=method, dimensions=len(vector)))
    db.commit()
    # Automatically inspect opposite-status reports when a new listing is submitted.
    try:
        from app.services.matching import run_matching
        run_matching(db, item, limit=5)
    except Exception:
        db.rollback()  # The listing itself is already committed and remains available.
    item = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == item.id).first()
    return serialize_listing(item)

@router.get("/zones/list")
def list_zones(db: Session = Depends(get_db)):
    return [{"id": z.id, "code": z.code, "name_en": z.name_en, "name_zh": z.name_zh} for z in db.query(CampusZone).filter(CampusZone.is_active.is_(True)).order_by(CampusZone.name_en).all()]

@router.get("/mine")
def my_listings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.owner_id == user.id).order_by(Listing.created_at.desc()).all()
    return [serialize_listing(row) for row in rows]

@router.get("/{listing_id}")
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    item = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == listing_id).first()
    if not item: raise HTTPException(404, "Listing not found")
    return serialize_listing(item)

@router.patch("/{listing_id}")
def update_listing(listing_id: int, payload: ListingUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Listing, listing_id)
    if not item: raise HTTPException(404, "Listing not found")
    if not _can_edit(item, user): raise HTTPException(403, "You cannot edit this listing")
    changes = payload.model_dump(exclude_unset=True)
    if "state" in changes and user.role != UserRole.ADMIN:
        raise HTTPException(403, "Only administrators can change listing workflow state")
    if changes.get("zone_id") and not db.get(CampusZone, changes["zone_id"]):
        raise HTTPException(400, "Unknown campus zone")
    for key, value in changes.items():
        setattr(item, key, value)
    vector, method = embed_text(f"{item.title}. {item.description}. {item.category}. {item.color or ''}", "passage")
    record = db.query(TextEmbedding).filter(TextEmbedding.listing_id == item.id).first()
    if record: record.vector, record.method, record.dimensions = vector, method, len(vector)
    else: db.add(TextEmbedding(listing_id=item.id, vector=vector, method=method, dimensions=len(vector)))
    db.commit()
    try:
        from app.services.matching import run_matching
        run_matching(db, item, limit=5)
    except Exception:
        db.rollback()
    item = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == item.id).first()
    return serialize_listing(item)

@router.delete("/{listing_id}")
def close_listing(listing_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Listing, listing_id)
    if not item: raise HTTPException(404, "Listing not found")
    if not _can_edit(item, user): raise HTTPException(403, "You cannot close this listing")
    item.state = ListingState.CLOSED
    db.commit()
    return {"success": True, "state": item.state.value}

@router.post("/{listing_id}/images", status_code=201)
async def upload_listing_image(listing_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Listing, listing_id)
    if not item: raise HTTPException(404, "Listing not found")
    if not _can_edit(item, user): raise HTTPException(403, "You cannot upload images to this listing")
    saved = await save_upload(file, private=False)
    image = ListingImage(listing_id=item.id, storage_path=saved["path"], public_url=saved["public_url"],
                         sha256=saved["sha256"], mime_type=saved["mime_type"], is_private=False)
    db.add(image); db.flush()
    vector, method = embed_image(saved["path"])
    db.add(ImageEmbedding(image_id=image.id, vector=vector, method=method, dimensions=len(vector)))
    analysis, provider = gemini_service.analyze(item.description, Path(saved["path"]).read_bytes(), saved["mime_type"])
    db.add(ListingAIAnalysis(listing_id=item.id, provider=provider, model=gemini_service.status()["model"] if provider == "google_gemini" else None,
                             attributes=analysis, confidence=analysis.get("confidence")))
    db.commit()
    try:
        from app.services.matching import run_matching
        run_matching(db, item, limit=5)
    except Exception:
        db.rollback()
    return {"image_id": image.id, "image_url": image.public_url, "image_embedding_method": method,
            "analysis_provider": provider, "analysis": analysis}

