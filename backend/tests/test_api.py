from app.database import SessionLocal
from app.models import User, UserRole, CampusZone, Listing, ListingStatus, ListingState, Claim, ClaimStatus
from app.security import hash_password

def start_visitor(client, email="student@example.edu"):
    # Existing API regression cases use separately issued visitor credentials.
    client.cookies.clear()
    response = client.post("/api/v1/auth/session")
    assert response.status_code == 200, response.text
    token = client.cookies.get("smartfind_visitor")
    client.cookies.clear()
    return token

def test_health_endpoints(client):
    assert client.get("/health/live").json()["status"] == "alive"
    assert client.get("/health/ready").json()["status"] == "ready"

def test_visitor_session_and_profile(client):
    token = start_visitor(client)
    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["full_name"] == "Anonymous visitor"
    assert profile.json()["role"] == "STUDENT"


def test_registration_removed(client):
    assert client.post("/api/v1/auth/register", json={}).status_code == 404

def test_listing_create_and_private_fields_not_public(client):
    token = start_visitor(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/v1/listings", headers=headers, json={
        "status": "LOST", "title": "Black earbuds", "description": "Black wireless earbuds case lost near the library.",
        "category": "Electronics", "color": "Black", "private_identifiers": "A tiny scratch inside the hinge."
    })
    assert created.status_code == 201, created.text
    listing_id = created.json()["id"]
    assert "private_identifiers" not in created.json()
    public = client.get(f"/api/v1/listings/{listing_id}")
    assert public.status_code == 200
    assert "private_identifiers" not in public.json()

def test_opposite_status_matching_and_claim_review(client):
    student_token = start_visitor(client, "owner@example.edu")
    finder_token = start_visitor(client, "finder@example.edu")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    finder_headers = {"Authorization": f"Bearer {finder_token}"}
    lost = client.post("/api/v1/listings", headers=student_headers, json={
        "status": "LOST", "title": "Black earbuds", "description": "I lost black wireless earbuds near the main library.",
        "category": "Electronics", "color": "Black"
    }).json()
    found = client.post("/api/v1/listings", headers=finder_headers, json={
        "status": "FOUND", "title": "Black wireless earbuds", "description": "Found a black wireless earbuds case near the library.",
        "category": "Electronics", "color": "Black"
    }).json()
    matched = client.post(f"/api/v1/ai/match/{lost['id']}", headers=student_headers)
    assert matched.status_code == 200, matched.text
    assert matched.json()["count"] == 1
    match = matched.json()["matches"][0]
    assert match["lost_listing"]["status"] == "LOST"
    assert match["found_listing"]["status"] == "FOUND"
    assert match["score_is_probability"] is False
    claim = client.post("/api/v1/claims", headers=student_headers, json={
        "listing_id": found["id"], "match_id": match["id"], "verification_details": "The inside hinge has a small scratch and one earbud has a mark."
    })
    assert claim.status_code == 201, claim.text
    # Create an admin account directly in the isolated test database.
    db = next(client.app.dependency_overrides[__import__('app.database', fromlist=['get_db']).get_db]())
    try:
        admin = User(email="admin@example.edu", full_name="Admin", password_hash=hash_password("AdminPass123!"), role=UserRole.ADMIN)
        db.add(admin); db.commit(); db.refresh(admin)
        from app.security import create_access_token
        admin_token = create_access_token(admin.id, admin.role.value)
    finally:
        db.close()
    review = client.patch(f"/api/v1/admin/claims/{claim.json()['id']}", headers={"Authorization": f"Bearer {admin_token}"}, json={"status":"APPROVED","admin_note":"Details verified."})
    assert review.status_code == 200, review.text
    recovered = client.get(f"/api/v1/listings/{found['id']}")
    lost_recovered = client.get(f"/api/v1/listings/{lost['id']}")
    assert recovered.json()["state"] == "RECOVERED"
    assert lost_recovered.json()["state"] == "RECOVERED"

def test_student_cannot_access_admin(client):
    token = start_visitor(client)
    response = client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

def test_image_upload_is_reencoded_and_analysis_provider_is_honest(client):
    from PIL import Image
    import io
    token = start_visitor(client, "imageuser@example.edu")
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.post("/api/v1/listings", headers=headers, json={
        "status":"LOST", "title":"Silver key ring", "description":"A small silver key ring near the dormitory.",
        "category":"Keys", "color":"Silver"
    }).json()
    image = Image.new("RGB", (40, 40), "silver")
    buffer = io.BytesIO(); image.save(buffer, format="PNG"); buffer.seek(0)
    response = client.post(f"/api/v1/listings/{listing['id']}/images", headers=headers,
                           files={"file":("keys.png", buffer.getvalue(), "image/png")})
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["image_embedding_method"] in {"openclip_vit_b32", "opencv_hsv_histogram_fallback"}
    assert data["analysis_provider"] in {"google_gemini", "rule_fallback", "rule_fallback_after_gemini_error"}
    assert data["image_url"].startswith("/media/public/")

def test_duplicate_detection_is_warning_only(client):
    token = start_visitor(client, "duplicate@example.edu")
    headers = {"Authorization": f"Bearer {token}"}
    first = client.post("/api/v1/listings", headers=headers, json={
        "status":"LOST", "title":"Black headphones", "description":"Black wireless headphones lost near the library.",
        "category":"Electronics", "color":"Black"
    }).json()
    client.post("/api/v1/listings", headers=headers, json={
        "status":"LOST", "title":"Black wireless headphones", "description":"I lost black headphones near the library.",
        "category":"Electronics", "color":"Black"
    })
    response = client.post(f"/api/v1/ai/duplicates/{first['id']}", headers=headers)
    assert response.status_code == 200, response.text
    assert "automatic_action" in response.json()["possible_duplicates"][0]
    assert response.json()["possible_duplicates"][0]["automatic_action"] == "none"

def test_claim_private_details_are_not_returned_to_student(client):
    student_token = start_visitor(client, "claimant@example.edu")
    finder_token = start_visitor(client, "ownerfound@example.edu")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    finder_headers = {"Authorization": f"Bearer {finder_token}"}
    found = client.post("/api/v1/listings", headers=finder_headers, json={
        "status":"FOUND", "title":"Blue wallet", "description":"Blue wallet found near cafeteria.",
        "category":"Wallets", "color":"Blue", "private_identifiers":"A faded star sticker inside."
    }).json()
    claim = client.post("/api/v1/claims", headers=student_headers, json={
        "listing_id":found["id"], "verification_details":"A faded star sticker is inside the wallet."
    })
    assert claim.status_code == 201
    private_view = client.get(f"/api/v1/claims/{claim.json()['id']}", headers=student_headers)
    assert private_view.status_code == 200
    assert "verification_details" not in private_view.json()

def test_english_query_retrieves_chinese_listing_in_fallback_mode(client):
    token = start_visitor(client, "crosslang@example.edu")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/v1/listings", headers=headers, json={
        "status":"FOUND", "title":"黑色蓝牙耳机盒", "description":"我在主图书馆附近捡到一个黑色蓝牙耳机盒。",
        "category":"Electronics", "color":"Black"
    })
    assert created.status_code == 201, created.text
    response = client.post("/api/v1/ai/search", headers=headers, json={"query":"black wireless earbuds case", "status":"FOUND", "limit":5})
    assert response.status_code == 200, response.text
    assert response.json()["results"]
    assert response.json()["results"][0]["listing"]["id"] == created.json()["id"]

def test_matches_endpoint_is_scoped_to_the_current_user(client):
    student_token = start_visitor(client, "matchowner@example.edu")
    finder_token = start_visitor(client, "matchfinder@example.edu")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    finder_headers = {"Authorization": f"Bearer {finder_token}"}
    lost = client.post("/api/v1/listings", headers=student_headers, json={"status":"LOST","title":"Blue wallet","description":"Blue wallet lost near library.","category":"Wallets","color":"Blue"}).json()
    found = client.post("/api/v1/listings", headers=finder_headers, json={"status":"FOUND","title":"Blue wallet found","description":"Found a blue wallet near library.","category":"Wallets","color":"Blue"}).json()
    client.post(f"/api/v1/ai/match/{lost['id']}", headers=student_headers)
    own = client.get("/api/v1/matches", headers=student_headers)
    other = client.get("/api/v1/matches", headers={"Authorization": f"Bearer {start_visitor(client, 'outsider@example.edu')}"})
    assert own.status_code == 200 and len(own.json()) >= 1
    assert other.status_code == 200 and other.json() == []

def test_pre_submission_duplicate_check_returns_warning_without_creating_record(client):
    token = start_visitor(client, "precheck@example.edu")
    headers = {"Authorization": f"Bearer {token}"}
    existing = client.post("/api/v1/listings", headers=headers, json={
        "status":"LOST", "title":"Black earbuds", "description":"Black wireless earbuds case lost by the library.",
        "category":"Electronics", "color":"Black"
    }).json()
    before = client.get("/api/v1/listings").json()["total"]
    check = client.post("/api/v1/ai/duplicates/check", headers=headers, json={
        "status":"LOST", "title":"Black wireless earbuds", "description":"I lost a black earbuds case near the library.",
        "category":"Electronics", "color":"Black"
    })
    assert check.status_code == 200, check.text
    assert check.json()["warning_only"] is True
    assert check.json()["automatic_action"] == "none"
    assert check.json()["possible_duplicates"][0]["listing_id"] == existing["id"]
    assert client.get("/api/v1/listings").json()["total"] == before

def test_ai_assistant_answers_only_from_retrieved_database_records(client):
    token = start_visitor(client, "assistant@example.edu")
    headers = {"Authorization": f"Bearer {token}"}
    empty = client.post("/api/v1/ai/assistant", headers=headers, json={"query":"blue umbrella lost yesterday"})
    assert empty.status_code == 200
    assert empty.json()["retrieved_records"] == []
    assert "could not find" in empty.json()["answer"].lower()
    client.post("/api/v1/listings", headers=headers, json={
        "status":"FOUND", "title":"Blue umbrella", "description":"A blue umbrella was found near the library.",
        "category":"Other", "color":"Blue"
    })
    found = client.post("/api/v1/ai/assistant", headers=headers, json={"query":"blue umbrella", "status":"FOUND"})
    assert found.status_code == 200
    assert found.json()["retrieved_records"]
    assert "Blue umbrella" in found.json()["answer"]

def test_student_cannot_bypass_admin_recovery_state(client):
    token = start_visitor(client, "stateowner@example.edu")
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.post("/api/v1/listings", headers=headers, json={
        "status":"LOST", "title":"Silver watch", "description":"Silver watch lost near engineering building.",
        "category":"Watches", "color":"Silver"
    }).json()
    response = client.patch(f"/api/v1/listings/{listing['id']}", headers=headers, json={"state":"RECOVERED"})
    assert response.status_code == 403

def test_admin_can_manage_configurable_campus_zone_adjacency(client):
    from app.database import get_db
    from app.security import create_access_token
    db = next(client.app.dependency_overrides[get_db]())
    try:
        admin = User(email="zones-admin@example.edu", full_name="Zone Admin", password_hash=hash_password("AdminPass123!"), role=UserRole.ADMIN)
        db.add(admin); db.commit(); db.refresh(admin)
        token = create_access_token(admin.id, admin.role.value)
    finally:
        db.close()
    headers = {"Authorization": f"Bearer {token}"}
    base = client.post("/api/v1/admin/zones", headers=headers, json={"code":"LIBRARY","name_en":"Library","name_zh":"图书馆","adjacent_codes":[]})
    assert base.status_code == 201, base.text
    zone = client.post("/api/v1/admin/zones", headers=headers, json={"code":"CAFETERIA","name_en":"Cafeteria","name_zh":"食堂","adjacent_codes":["LIBRARY"]})
    assert zone.status_code == 201, zone.text
    updated = client.patch(f"/api/v1/admin/zones/{zone.json()['id']}", headers=headers, json={"adjacent_codes":["UNKNOWN"]})
    assert updated.status_code == 400
    listed = client.get("/api/v1/admin/zones", headers=headers)
    assert len(listed.json()) == 2


def test_cosine_similarity_clamps_negative_and_orthogonal_scores_to_zero():
    from app.services.embeddings import cosine_similarity
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_missing_matching_signals_are_excluded_and_weights_renormalized(client):
    from app.database import get_db
    from app.models import Listing
    from app.services.matching import score_pair
    token_a = start_visitor(client, "missing-lost@example.edu")
    token_b = start_visitor(client, "missing-found@example.edu")
    lost = client.post("/api/v1/listings", headers={"Authorization": f"Bearer {token_a}"}, json={
        "status":"LOST", "title":"Silver key ring", "description":"A silver key ring with three keys.",
        "category":"Keys", "color":"Silver"
    }).json()
    found = client.post("/api/v1/listings", headers={"Authorization": f"Bearer {token_b}"}, json={
        "status":"FOUND", "title":"Silver keys", "description":"Found a small silver key ring.",
        "category":"Keys", "color":"Silver"
    }).json()
    db = next(client.app.dependency_overrides[get_db]())
    try:
        evidence = score_pair(db, db.get(Listing, lost["id"]), db.get(Listing, found["id"]))
        assert evidence["components"]["image"] is None
        assert evidence["components"]["time"] is None
        assert evidence["components"]["location"] is None
        assert evidence["available_weight"] == 0.52
        assert evidence["score_is_probability"] is False
        assert any("image similarity" in signal for signal in evidence["missing_signals"])
    finally:
        db.close()


def test_image_upload_rejects_mismatched_extension(client):
    from PIL import Image
    import io
    token = start_visitor(client, "mismatch-image@example.edu")
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.post("/api/v1/listings", headers=headers, json={
        "status":"LOST", "title":"Test item", "description":"A test item image for validation.",
        "category":"Other"
    }).json()
    image = Image.new("RGB", (16, 16), "white")
    buffer = io.BytesIO(); image.save(buffer, format="PNG")
    response = client.post(f"/api/v1/listings/{listing['id']}/images", headers=headers,
                           files={"file":("misleading.jpg", buffer.getvalue(), "image/jpeg")})
    assert response.status_code == 415
