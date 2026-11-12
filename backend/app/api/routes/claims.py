from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pathlib import Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserRole, Listing, ListingStatus, ListingState, Claim, ClaimStatus, Match, Notification, AuditLog
from app.schemas import ClaimCreate
from app.services.notifications import notify_once
from app.services.storage import save_upload

router = APIRouter(prefix="/claims", tags=["ownership claims"])

def _claim_out(claim: Claim, include_private: bool = False) -> dict:
    data = {"id": claim.id, "listing_id": claim.listing_id, "claimant_id": claim.claimant_id,
            "match_id": claim.match_id, "status": claim.status.value, "admin_note": claim.admin_note,
            "created_at": claim.created_at, "reviewed_at": claim.reviewed_at}
    if include_private:
        data["verification_details"] = claim.verification_details
    return data

@router.post("", status_code=201)
def create_claim(payload: ClaimCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listing = db.get(Listing, payload.listing_id)
    if not listing: raise HTTPException(404, "Listing not found")
    if listing.status != ListingStatus.FOUND: raise HTTPException(400, "Claims can only be submitted for found-item reports")
    if listing.owner_id == user.id: raise HTTPException(400, "You cannot claim your own found report")
    if listing.state in {ListingState.RECOVERED, ListingState.CLOSED}: raise HTTPException(409, "This item is no longer available for claims")
    duplicate = db.query(Claim).filter(Claim.listing_id == listing.id, Claim.claimant_id == user.id, Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.NEEDS_EVIDENCE])).first()
    if duplicate: raise HTTPException(409, "You already have an active claim for this listing")
    if payload.match_id:
        match = db.get(Match, payload.match_id)
        if not match or match.found_listing_id != listing.id or match.lost_listing_id not in [row.id for row in user.listings]:
            raise HTTPException(400, "The selected match is not associated with your account")
    claim = Claim(listing_id=listing.id, claimant_id=user.id, match_id=payload.match_id, verification_details=payload.verification_details)
    db.add(claim); listing.state = ListingState.CLAIM_PENDING
    db.flush()
    notify_once(db, listing.owner_id, "CLAIM_SUBMITTED", "A recovery claim was submitted", "A student submitted a private ownership claim for your found report.", {"claim_id": claim.id}, f"claim:{claim.id}:owner")
    db.commit(); db.refresh(claim)
    return _claim_out(claim)

@router.get("")
def my_claims(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Claim).filter(Claim.claimant_id == user.id).order_by(Claim.created_at.desc()).all()
    return [_claim_out(row) for row in rows]

@router.get("/{claim_id}")
def get_claim(claim_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = db.get(Claim, claim_id)
    if not claim: raise HTTPException(404, "Claim not found")
    if user.role != UserRole.ADMIN and claim.claimant_id != user.id:
        raise HTTPException(403, "You cannot view this claim")
    return _claim_out(claim, include_private=user.role == UserRole.ADMIN)

@router.post("/{claim_id}/evidence", status_code=201)
async def upload_claim_evidence(claim_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = db.get(Claim, claim_id)
    if not claim: raise HTTPException(404, "Claim not found")
    if claim.claimant_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(403, "You cannot upload evidence to this claim")
    if claim.status in {ClaimStatus.APPROVED, ClaimStatus.REJECTED}:
        raise HTTPException(409, "Evidence cannot be changed after a claim is finalized")
    saved = await save_upload(file, private=True)
    claim.evidence_path = saved["path"]
    db.commit()
    return {"success": True, "claim_id": claim.id, "evidence_received": True, "public_url": None}
