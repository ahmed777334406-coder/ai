from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserRole, Listing, Match, MatchFeedback
from app.schemas import FeedbackCreate
from app.api.routes.listings import serialize_listing

router = APIRouter(prefix="/matches", tags=["potential matches"])

def _visible(match: Match, user: User, db: Session) -> bool:
    lost, found = db.get(Listing, match.lost_listing_id), db.get(Listing, match.found_listing_id)
    return user.role == UserRole.ADMIN or bool(lost and found and (lost.owner_id == user.id or found.owner_id == user.id))

@router.get("")
def list_matches(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Match).order_by(Match.score.desc(), Match.created_at.desc())
    if user.role != UserRole.ADMIN:
        owned = db.query(Listing.id).filter(Listing.owner_id == user.id)
        query = query.filter(Match.lost_listing_id.in_(owned) | Match.found_listing_id.in_(owned))
    rows = query.limit(max(1, min(limit, 100))).all()
    output = []
    for match in rows:
        if not _visible(match, user, db): continue
        lost = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == match.lost_listing_id).first()
        found = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == match.found_listing_id).first()
        output.append({"id": match.id, "score": match.score, "score_is_probability": False, "components": match.components,
                       "methods": match.methods, "explanation": match.explanation,
                       "lost_listing": serialize_listing(lost), "found_listing": serialize_listing(found)})
    return output

@router.get("/{match_id}")
def get_match(match_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    match = db.get(Match, match_id)
    if not match: raise HTTPException(404, "Match not found")
    if not _visible(match, user, db): raise HTTPException(403, "You cannot view this match")
    lost = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == match.lost_listing_id).first()
    found = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == match.found_listing_id).first()
    return {"id": match.id, "score": match.score, "score_is_probability": False, "components": match.components,
            "methods": match.methods, "explanation": match.explanation,
            "lost_listing": serialize_listing(lost), "found_listing": serialize_listing(found)}

@router.post("/{match_id}/feedback", status_code=201)
def feedback(match_id: int, payload: FeedbackCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    match = db.get(Match, match_id)
    if not match: raise HTTPException(404, "Match not found")
    if not _visible(match, user, db): raise HTTPException(403, "You cannot review this match")
    existing = db.query(MatchFeedback).filter(MatchFeedback.match_id == match_id, MatchFeedback.user_id == user.id).first()
    if existing:
        existing.relevant = payload.relevant; existing.note = payload.note
    else:
        db.add(MatchFeedback(match_id=match_id, user_id=user.id, relevant=payload.relevant, note=payload.note))
    db.commit()
    return {"success": True, "match_id": match_id, "relevant": payload.relevant}
