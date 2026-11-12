from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.config import settings
from app.dependencies import get_current_user
from app.models import User, Listing, ListingStatus, ListingState, TextEmbedding, Match
from app.schemas import SearchRequest, DescriptionRequest, DuplicateCheckRequest
from app.services.embeddings import embed_text, cosine_similarity
from app.services.matching import run_matching, _embedding, _image_vector
from app.services.gemini import gemini_service
from app.api.routes.listings import serialize_listing

router = APIRouter(prefix="/ai", tags=["artificial intelligence"])

@router.get("/status")
def ai_status():
    return {"gemini": gemini_service.status(), "text_embedding": {"model": "intfloat/multilingual-e5-small", "enabled": settings.enable_local_models, "status": "lazy-loaded; rule fallback if unavailable" if settings.enable_local_models else "disabled; bilingual rule/hash fallback"},
            "image_embedding": {"model": "OpenCLIP ViT-B/32", "enabled": settings.enable_local_models, "status": "lazy-loaded; HSV histogram fallback if unavailable" if settings.enable_local_models else "disabled; HSV histogram fallback"}}

@router.post("/analyze")
def analyze_text(payload: SearchRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    analysis, provider = gemini_service.analyze(payload.query)
    return {"analysis": analysis, "provider": provider, "gemini_live": provider == "google_gemini"}

@router.post("/description")
def improve_description(payload: DescriptionRequest, user: User = Depends(get_current_user)):
    result, provider = gemini_service.improve_description(payload.title, payload.description, payload.language, payload.target_language)
    return {"suggestion": result, "provider": provider, "requires_user_approval": True}

@router.post("/match/{listing_id}")
def match_listing(listing_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listing = db.query(Listing).options(joinedload(Listing.images)).filter(Listing.id == listing_id).first()
    if not listing: raise HTTPException(404, "Listing not found")
    if listing.owner_id != user.id and user.role.value != "ADMIN": raise HTTPException(403, "You can only match your own listing")
    matches = run_matching(db, listing, limit=5)
    output = []
    for match in matches:
        lost = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == match.lost_listing_id).first()
        found = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.id == match.found_listing_id).first()
        other = found if listing.status == ListingStatus.LOST else lost
        output.append({"id": match.id, "score": match.score, "score_is_probability": False,
                       "components": match.components, "methods": match.methods, "explanation": match.explanation,
                       "lost_listing": serialize_listing(lost), "found_listing": serialize_listing(found),
                       "candidate": serialize_listing(other)})
    return {"listing_id": listing_id, "count": len(output), "matches": output}

@router.post("/search")
def semantic_search(payload: SearchRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query_vector, query_method = embed_text(payload.query, "query")
    query = db.query(Listing).options(joinedload(Listing.owner), joinedload(Listing.zone), joinedload(Listing.images)).filter(Listing.state != ListingState.CLOSED)
    if payload.status: query = query.filter(Listing.status == payload.status)
    retrieval_backend = "python_cosine_fallback"
    if db.bind and db.bind.dialect.name == "postgresql":
        # pgvector cosine-distance operator; HNSW indexes are created on the vector columns.
        from sqlalchemy import text as sql_text
        vector_literal = "[" + ",".join(str(float(value)) for value in query_vector) + "]"
        status_clause = "AND l.status = :status" if payload.status else ""
        sql = sql_text(f"""SELECT te.listing_id, GREATEST(0, 1 - (te.vector <=> CAST(:query_vector AS vector))) AS similarity
            FROM text_embeddings te JOIN listings l ON l.id = te.listing_id
            WHERE te.vector IS NOT NULL AND te.method = :method AND l.state <> 'CLOSED' {status_clause}
            ORDER BY te.vector <=> CAST(:query_vector AS vector) LIMIT :limit""")
        params = {"query_vector": vector_literal, "method": query_method, "limit": payload.limit}
        if payload.status: params["status"] = payload.status.value
        rows = db.execute(sql, params).all()
        ids = [row[0] for row in rows]
        score_map = {row[0]: float(row[1]) for row in rows}
        by_id = {row.id: row for row in query.filter(Listing.id.in_(ids)).all()} if ids else {}
        candidates = [by_id[item_id] for item_id in ids if item_id in by_id]
        ranked = [(score_map[item.id], item, query_method) for item in candidates]
        retrieval_backend = "pgvector_cosine_hnsw"
    else:
        candidates = query.order_by(Listing.created_at.desc()).limit(300).all()
        ranked = []
    if retrieval_backend == "python_cosine_fallback":
        for item in candidates:
            record = db.query(TextEmbedding).filter(TextEmbedding.listing_id == item.id).first()
            if record and record.vector and record.method == query_method:
                score = cosine_similarity(query_vector, record.vector)
                method = query_method
            else:
                # Transparent lexical fallback for records created with a different model.
                from app.services.embeddings import _canonicalize
                qset = set(_canonicalize(payload.query).split())
                tset = set(_canonicalize(item.title + " " + item.description + " " + item.category).split())
                score = len(qset & tset) / max(1, len(qset | tset))
                method = "lexical_overlap_fallback"
            ranked.append((score or 0.0, item, method))
    ranked.sort(key=lambda row: row[0], reverse=True)
    return {"query": payload.query, "method": query_method, "retrieval_backend": retrieval_backend, "results": [{"score": round(score * 100, 2), "method": method, "listing": serialize_listing(item)} for score, item, method in ranked[:payload.limit]]}

@router.post("/assistant")
def assistant(payload: SearchRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = semantic_search(payload, db, user)
    records = [{"id": r["listing"]["id"], "status": r["listing"]["status"], "title": r["listing"]["title"], "zone": r["listing"]["zone_name_en"], "score": r["score"]} for r in result["results"]]
    # The answer is grounded only in records retrieved above; no database result is fabricated.
    answer, answer_provider = gemini_service.answer_from_records(payload.query, records)
    return {"answer": answer, "answer_provider": answer_provider, "retrieved_records": records, "retrieval_method": result["method"]}

@router.post("/duplicates/check")
def check_duplicates_before_submission(payload: DuplicateCheckRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query_vector, query_method = embed_text(f"{payload.title}. {payload.description}. {payload.category}. {payload.color or ''}", "query")
    candidates = db.query(Listing).options(joinedload(Listing.images)).filter(
        Listing.status == payload.status, Listing.state != ListingState.CLOSED
    ).order_by(Listing.created_at.desc()).limit(300).all()
    warnings = []
    for candidate in candidates:
        record = db.query(TextEmbedding).filter(TextEmbedding.listing_id == candidate.id).first()
        text_score = cosine_similarity(query_vector, record.vector) if record and record.vector and record.method == query_method else None
        category_score = 1.0 if payload.category.lower() == candidate.category.lower() else 0.0
        color_score = (1.0 if payload.color and candidate.color and payload.color.lower() == candidate.color.lower() else None)
        signals = [(0.75, text_score), (0.15, category_score), (0.10, color_score)]
        available = [(weight, score) for weight, score in signals if score is not None]
        total = sum(weight for weight, _ in available)
        score = sum(weight * value for weight, value in available) / total if total else 0.0
        if score >= 0.45:
            warnings.append({"listing_id": candidate.id, "title": candidate.title, "status": candidate.status.value,
                             "similarity_score": round(score * 100, 2), "method": query_method})
    warnings.sort(key=lambda x: x["similarity_score"], reverse=True)
    return {"possible_duplicates": warnings[:5], "warning_only": True, "automatic_action": "none"}

@router.post("/duplicates/{listing_id}")
def detect_duplicates(listing_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listing = db.query(Listing).options(joinedload(Listing.images)).filter(Listing.id == listing_id).first()
    if not listing: raise HTTPException(404, "Listing not found")
    if listing.owner_id != user.id and user.role.value != "ADMIN": raise HTTPException(403, "You can only check duplicates for your own listing")
    candidates = db.query(Listing).options(joinedload(Listing.images)).filter(
        Listing.id != listing.id, Listing.status == listing.status, Listing.state != ListingState.CLOSED
    ).all()
    source_text, source_method = _embedding(db, listing)
    source_image, source_image_method = _image_vector(db, listing)
    results = []
    for candidate in candidates:
        text_vector, text_method = _embedding(db, candidate)
        image_vector, image_method = _image_vector(db, candidate)
        signals = []
        if source_text and text_vector and source_method == text_method:
            signals.append((0.55, cosine_similarity(source_text, text_vector)))
        if source_image and image_vector and source_image_method == image_method:
            signals.append((0.30, cosine_similarity(source_image, image_vector)))
        if listing.category and candidate.category:
            signals.append((0.10, 1.0 if listing.category.lower() == candidate.category.lower() else 0.0))
        if listing.color and candidate.color:
            signals.append((0.05, 1.0 if listing.color.lower() == candidate.color.lower() else 0.0))
        available = [(weight, value) for weight, value in signals if value is not None]
        denominator = sum(weight for weight, _ in available)
        score = sum(weight * value for weight, value in available) / denominator if denominator else 0
        if score >= 0.35:
            results.append({"listing": serialize_listing(candidate), "similarity_score": round(score * 100, 2),
                            "methods": {"text": text_method, "image": image_method}, "automatic_action": "none"})
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return {"listing_id": listing_id, "possible_duplicates": results[:5], "note": "Possible duplicates are warnings only; no report is automatically deleted or merged."}
