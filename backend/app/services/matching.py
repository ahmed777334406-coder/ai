from datetime import datetime, timezone
from math import exp
from sqlalchemy.orm import Session
from app.models import Listing, ListingStatus, ListingState, TextEmbedding, ImageEmbedding, Match, CampusZone
from app.config import settings
from app.services.embeddings import embed_text, cosine_similarity
from app.services.gemini import gemini_service
from app.services.notifications import notify_once

def _raw_cosine(a: list[float], b: list[float]) -> float | None:
    if not a or not b or len(a) != len(b): return None
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5; nb = sum(y*y for y in b) ** 0.5
    if na == 0 or nb == 0: return None
    return max(0.0, min(1.0, dot / (na * nb)))

WEIGHTS = {
    "text": settings.match_weight_text,
    "image": settings.match_weight_image,
    "category": settings.match_weight_category,
    "color": settings.match_weight_color,
    "time": settings.match_weight_time,
    "location": settings.match_weight_location,
}

def _text_for(listing: Listing) -> str:
    return " ".join([listing.title or "", listing.description or "", listing.category or "", listing.color or ""]).strip()

def _embedding(db: Session, listing: Listing) -> tuple[list[float] | None, str | None]:
    record = db.query(TextEmbedding).filter(TextEmbedding.listing_id == listing.id).first()
    if record and record.vector:
        return record.vector, record.method
    vector, method = embed_text(_text_for(listing), "passage")
    db.add(TextEmbedding(listing_id=listing.id, vector=vector, method=method, dimensions=len(vector)))
    db.flush()
    return vector, method

def _image_vector(db: Session, listing: Listing) -> tuple[list[float] | None, str | None]:
    image_ids = [img.id for img in listing.images]
    if not image_ids: return None, None
    records = db.query(ImageEmbedding).filter(ImageEmbedding.image_id.in_(image_ids)).all()
    if not records: return None, None
    first = next((record for record in records if record.vector), None)
    return (first.vector, first.method) if first else (None, None)

def _normal(value: str | None) -> str | None:
    return value.strip().lower() if value and value.strip() else None

def _component_scores(db: Session, lost: Listing, found: Listing) -> tuple[dict, dict, list[str]]:
    values: dict[str, float | None] = {name: None for name in WEIGHTS}
    methods: dict[str, str] = {}
    missing: list[str] = []

    lv, lm = _embedding(db, lost); fv, fm = _embedding(db, found)
    if lv and fv and lm == fm:
        values["text"] = cosine_similarity(lv, fv)
        methods["text"] = lm or "unknown"
    else:
        missing.append("text similarity (embedding methods differ or unavailable)")

    liv, lim = _image_vector(db, lost); fiv, fim = _image_vector(db, found)
    if liv and fiv and lim == fim:
        values["image"] = _raw_cosine(liv, fiv) if lim == "opencv_hsv_histogram_fallback" else cosine_similarity(liv, fiv)
        methods["image"] = lim or "unknown"
    else:
        missing.append("image similarity (both reports need compatible image embeddings)")

    lc, fc = _normal(lost.category), _normal(found.category)
    if lc and fc:
        values["category"] = 1.0 if lc == fc else 0.0
        methods["category"] = "normalized_exact_category"
    else: missing.append("category")

    lcolor, fcolor = _normal(lost.color), _normal(found.color)
    if lcolor and fcolor:
        values["color"] = 1.0 if lcolor == fcolor else 0.0
        methods["color"] = "normalized_exact_color"
    else: missing.append("color")

    if lost.occurred_at and found.occurred_at:
        lost_time = lost.occurred_at.replace(tzinfo=timezone.utc) if lost.occurred_at.tzinfo is None else lost.occurred_at
        found_time = found.occurred_at.replace(tzinfo=timezone.utc) if found.occurred_at.tzinfo is None else found.occurred_at
        delta_days = abs((lost_time - found_time).total_seconds()) / 86400
        values["time"] = exp(-delta_days / max(settings.time_decay_days, 0.1))
        methods["time"] = f"exponential_{settings.time_decay_days:g}_day_decay"
    else: missing.append("time")

    if lost.zone_id and found.zone_id:
        lz, fz = db.get(CampusZone, lost.zone_id), db.get(CampusZone, found.zone_id)
        if lz and fz:
            if lz.code == fz.code: values["location"] = 1.0
            elif fz.code in (lz.adjacent_codes or []) or lz.code in (fz.adjacent_codes or []): values["location"] = 0.7
            else: values["location"] = 0.2
            methods["location"] = "configured_campus_zone_adjacency"
        else: missing.append("location (zone configuration unavailable)")
    else: missing.append("location")
    return values, methods, missing

def score_pair(db: Session, lost: Listing, found: Listing) -> dict:
    if lost.status != ListingStatus.LOST or found.status != ListingStatus.FOUND:
        raise ValueError("Matching requires one LOST listing and one FOUND listing")
    values, methods, missing = _component_scores(db, lost, found)
    available = [(name, value, WEIGHTS[name]) for name, value in values.items() if value is not None]
    denominator = sum(weight for _, _, weight in available)
    score = (sum(value * weight for _, value, weight in available) / denominator * 100) if denominator else 0.0
    return {
        "score": round(score, 2),
        "components": values,
        "weighted_components": {name: round(value * 100, 2) if value is not None else None for name, value in values.items()},
        "methods": methods,
        "missing_signals": missing,
        "available_weight": round(denominator, 3),
        "score_is_probability": False,
    }

def run_matching(db: Session, listing: Listing, limit: int = 5) -> list[Match]:
    if listing.state not in {ListingState.OPEN, ListingState.CLAIM_PENDING}:
        return []
    if listing.status == ListingStatus.LOST:
        candidates = db.query(Listing).filter(Listing.status == ListingStatus.FOUND, Listing.state.in_([ListingState.OPEN, ListingState.CLAIM_PENDING])).all()
    else:
        candidates = db.query(Listing).filter(Listing.status == ListingStatus.LOST, Listing.state.in_([ListingState.OPEN, ListingState.CLAIM_PENDING])).all()
    results = []
    for candidate in candidates:
        if listing.status == ListingStatus.LOST: lost, found = listing, candidate
        else: lost, found = candidate, listing
        if lost.id == found.id: continue
        evidence = score_pair(db, lost, found)
        if evidence["available_weight"] <= 0: continue
        existing = db.query(Match).filter(Match.lost_listing_id == lost.id, Match.found_listing_id == found.id).first()
        deterministic_explanation = gemini_service._deterministic_explanation(evidence)
        methods = {**evidence["methods"], "missing_signals": evidence["missing_signals"],
                   "available_weight": evidence["available_weight"], "explanation": "deterministic_evidence_fallback"}
        if existing:
            existing.score = evidence["score"]; existing.components = evidence["components"]
            existing.methods = methods; existing.explanation = deterministic_explanation
            match = existing
        else:
            match = Match(lost_listing_id=lost.id, found_listing_id=found.id, score=evidence["score"],
                          components=evidence["components"], methods=methods, explanation=deterministic_explanation)
            db.add(match); db.flush()
        if evidence["score"] >= 35:
            notify_once(db, lost.owner_id, "POTENTIAL_MATCH", "A potential match was found", f"A found report may match: {lost.title}", {"match_id": match.id}, f"match:{match.id}:lost")
            notify_once(db, found.owner_id, "POTENTIAL_MATCH", "A potential match was found", f"A lost report may match: {found.title}", {"match_id": match.id}, f"match:{match.id}:found")
        results.append(match)
    ranked = sorted(results, key=lambda item: item.score, reverse=True)[:limit]
    # Only the returned top candidates incur generative explanation calls.
    for match in ranked:
        evidence = {"components": match.components, "missing_signals": match.methods.get("missing_signals", [])}
        explanation, provider = gemini_service.explain_match(evidence)
        match.explanation = explanation
        match.methods = {**match.methods, "explanation": provider}
    db.commit()
    return ranked

