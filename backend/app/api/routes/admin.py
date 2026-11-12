from datetime import datetime, timezone
from pathlib import Path
from fastapi.responses import FileResponse
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.config import settings
from app.dependencies import require_admin
from app.models import User, UserRole, Listing, ListingStatus, ListingState, Claim, ClaimStatus, Match, Notification, AuditLog, CampusZone
from app.schemas import ClaimReview, CampusZoneCreate, CampusZoneUpdate
from app.api.routes.claims import _claim_out
from app.api.routes.listings import serialize_listing
from app.services.notifications import notify_once

router = APIRouter(prefix="/admin", tags=["administration"])

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return {
        "users": db.query(User).count(), "listings": db.query(Listing).count(),
        "lost_open": db.query(Listing).filter(Listing.status == ListingStatus.LOST, Listing.state == ListingState.OPEN).count(),
        "found_open": db.query(Listing).filter(Listing.status == ListingStatus.FOUND, Listing.state == ListingState.OPEN).count(),
        "pending_claims": db.query(Claim).filter(Claim.status == ClaimStatus.PENDING).count(),
        "potential_matches": db.query(Match).count(),
        "recovered": db.query(Listing).filter(Listing.state == ListingState.RECOVERED).count(),
    }

@router.get("/listings")
def admin_listings(limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).order_by(Listing.created_at.desc()).limit(max(1, min(limit, 200))).all()
    return [serialize_listing(row) for row in rows]

@router.get("/claims")
def admin_claims(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(Claim).order_by(Claim.created_at.desc()).all()
    output = []
    for row in rows:
        data = _claim_out(row, include_private=True)
        listing = db.get(Listing, row.listing_id)
        data["listing_private_identifiers"] = listing.private_identifiers if listing else None
        data["evidence_received"] = bool(row.evidence_path)
        output.append(data)
    return output

@router.patch("/claims/{claim_id}")
def review_claim(claim_id: int, payload: ClaimReview, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    claim = db.query(Claim).filter(Claim.id == claim_id).with_for_update().first()
    if not claim: raise HTTPException(404, "Claim not found")
    if claim.status in {ClaimStatus.APPROVED, ClaimStatus.REJECTED}: raise HTTPException(409, "This claim has already been finalized")
    if payload.status not in {ClaimStatus.NEEDS_EVIDENCE, ClaimStatus.APPROVED, ClaimStatus.REJECTED}:
        raise HTTPException(400, "Unsupported review status")
    listing = db.query(Listing).filter(Listing.id == claim.listing_id).with_for_update().first()
    if payload.status == ClaimStatus.APPROVED and listing.state in {ListingState.RECOVERED, ListingState.CLOSED}:
        raise HTTPException(409, "This item is no longer available for approval")
    claim.status = payload.status; claim.admin_note = payload.admin_note; claim.reviewed_by = admin.id; claim.reviewed_at = datetime.now(timezone.utc)
    listing = db.get(Listing, claim.listing_id)
    if payload.status == ClaimStatus.APPROVED:
        listing.state = ListingState.RECOVERED
        notify_once(db, listing.owner_id, "ITEM_RECOVERED", "The item has been recovered", "An administrator approved an ownership claim for your found report.", {"claim_id": claim.id}, f"claim:{claim.id}:finder-recovered")
        if claim.match_id:
            match = db.get(Match, claim.match_id)
            if match:
                lost = db.get(Listing, match.lost_listing_id)
                if lost: lost.state = ListingState.RECOVERED
        notify_once(db, claim.claimant_id, "CLAIM_APPROVED", "Your recovery claim was approved", "An administrator approved your claim. Arrange the handover through the agreed campus process.", {"claim_id": claim.id}, f"claim:{claim.id}:approved")
        other_claims = db.query(Claim).filter(Claim.listing_id == listing.id, Claim.id != claim.id, Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.NEEDS_EVIDENCE])).all()
        for other in other_claims:
            other.status = ClaimStatus.REJECTED
            other.admin_note = "Another ownership claim was approved for this item."
            other.reviewed_by = admin.id; other.reviewed_at = datetime.now(timezone.utc)
            notify_once(db, other.claimant_id, "CLAIM_REJECTED", "This item has been claimed", other.admin_note, {"claim_id": other.id}, f"claim:{other.id}:rejected")
    elif payload.status == ClaimStatus.REJECTED:
        other_pending = db.query(Claim).filter(Claim.listing_id == listing.id, Claim.id != claim.id, Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.NEEDS_EVIDENCE])).count()
        listing.state = ListingState.CLAIM_PENDING if other_pending else ListingState.OPEN
        notify_once(db, claim.claimant_id, "CLAIM_REJECTED", "Your recovery claim was not approved", payload.admin_note or "The administrator could not verify the claim.", {"claim_id": claim.id}, f"claim:{claim.id}:rejected")
    else:
        notify_once(db, claim.claimant_id, "CLAIM_NEEDS_EVIDENCE", "More information is required", payload.admin_note or "Please provide additional identifying details.", {"claim_id": claim.id}, f"claim:{claim.id}:evidence")
    db.add(AuditLog(actor_id=admin.id, action="claim_reviewed", target_type="claim", target_id=str(claim.id), details={"status": payload.status.value}))
    db.commit()
    result = _claim_out(claim, include_private=True)
    result["listing_private_identifiers"] = listing.private_identifiers if listing else None
    result["evidence_received"] = bool(claim.evidence_path)
    return result

@router.patch("/listings/{listing_id}/status")
def update_listing_state(listing_id: int, state: ListingState, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    listing = db.get(Listing, listing_id)
    if not listing: raise HTTPException(404, "Listing not found")
    listing.state = state
    db.add(AuditLog(actor_id=admin.id, action="listing_state_changed", target_type="listing", target_id=str(listing.id), details={"state": state.value}))
    db.commit()
    return {"id": listing.id, "state": listing.state.value}

@router.get("/users")
def admin_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role.value, "is_active": u.is_active, "created_at": u.created_at} for u in db.query(User).order_by(User.created_at.desc()).limit(300).all()]

@router.get("/analytics")
def analytics(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    by_category = db.query(Listing.category, func.count(Listing.id)).group_by(Listing.category).all()
    by_status = db.query(Listing.status, func.count(Listing.id)).group_by(Listing.status).all()
    by_zone = db.query(Listing.zone_id, func.count(Listing.id)).group_by(Listing.zone_id).all()
    recovered = db.query(Listing).filter(Listing.state == ListingState.RECOVERED).count()
    total = db.query(Listing).count()
    return {"by_category": [{"category": k, "count": v} for k, v in by_category],
            "by_status": [{"status": k.value, "count": v} for k, v in by_status],
            "by_zone": [{"zone_id": k, "count": v} for k, v in by_zone],
            "recovered": recovered, "total_listings": total,
            "recovery_rate": round(recovered / total, 4) if total else 0.0,
            "note": "All metrics are calculated from stored records; synthetic demo records are labelled separately."}


@router.get("/claims/{claim_id}/evidence")
def download_claim_evidence(claim_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    claim = db.get(Claim, claim_id)
    if not claim or not claim.evidence_path:
        raise HTTPException(404, "Claim evidence not found")
    path = Path(claim.evidence_path).resolve()
    private_root = (Path(settings.upload_dir) / "private").resolve()
    if private_root not in path.parents or not path.is_file():
        raise HTTPException(404, "Claim evidence not found")
    return FileResponse(path, media_type="application/octet-stream", filename=f"claim-{claim.id}-evidence{path.suffix}")


@router.get("/zones")
def admin_zones(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [{"id": z.id, "code": z.code, "name_en": z.name_en, "name_zh": z.name_zh,
             "adjacent_codes": z.adjacent_codes or [], "is_active": z.is_active}
            for z in db.query(CampusZone).order_by(CampusZone.name_en).all()]

@router.post("/zones", status_code=201)
def create_zone(payload: CampusZoneCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    code = payload.code.strip().upper()
    if db.query(CampusZone).filter(CampusZone.code == code).first(): raise HTTPException(409, "Campus zone code already exists")
    adjacent = sorted({c.strip().upper() for c in payload.adjacent_codes if c.strip() and c.strip().upper() != code})
    known = {row.code for row in db.query(CampusZone).all()}
    unknown = set(adjacent) - known
    if unknown: raise HTTPException(400, f"Unknown adjacent campus zone code(s): {', '.join(sorted(unknown))}")
    zone = CampusZone(code=code, name_en=payload.name_en.strip(), name_zh=payload.name_zh.strip(),
                      adjacent_codes=adjacent, is_active=payload.is_active)
    db.add(zone); db.flush()
    db.add(AuditLog(actor_id=admin.id, action="campus_zone_created", target_type="campus_zone", target_id=str(zone.id), details={"code": code}))
    db.commit(); db.refresh(zone)
    return {"id": zone.id, "code": zone.code, "name_en": zone.name_en, "name_zh": zone.name_zh, "adjacent_codes": zone.adjacent_codes, "is_active": zone.is_active}

@router.patch("/zones/{zone_id}")
def update_zone(zone_id: int, payload: CampusZoneUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    zone = db.get(CampusZone, zone_id)
    if not zone: raise HTTPException(404, "Campus zone not found")
    changes = payload.model_dump(exclude_unset=True)
    if "adjacent_codes" in changes:
        adjacent = sorted({c.strip().upper() for c in (changes["adjacent_codes"] or []) if c.strip() and c.strip().upper() != zone.code})
        known = {row.code for row in db.query(CampusZone).all()}
        unknown = set(adjacent) - known
        if unknown: raise HTTPException(400, f"Unknown adjacent campus zone code(s): {', '.join(sorted(unknown))}")
        changes["adjacent_codes"] = adjacent
    for key, value in changes.items(): setattr(zone, key, value)
    db.add(AuditLog(actor_id=admin.id, action="campus_zone_updated", target_type="campus_zone", target_id=str(zone.id), details=changes))
    db.commit(); db.refresh(zone)
    return {"id": zone.id, "code": zone.code, "name_en": zone.name_en, "name_zh": zone.name_zh, "adjacent_codes": zone.adjacent_codes, "is_active": zone.is_active}
