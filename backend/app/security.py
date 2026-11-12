import base64, hashlib, hmac, json, secrets, time
from fastapi import HTTPException, status
from app.config import settings

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return "pbkdf2_sha256$310000$%s$%s" % (base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode())

def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_b64, digest_b64 = stored.split("$")
        if algorithm != "pbkdf2_sha256": return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def create_access_token(user_id: int, role: str) -> str:
    header = _b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub":str(user_id),"role":role,"jti":secrets.token_urlsafe(24),"exp":int(time.time()) + settings.access_token_expire_minutes*60}, separators=(",", ":")).encode())
    signing = f"{header}.{payload}".encode()
    signature = _b64(hmac.new(settings.jwt_secret_key.encode(), signing, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"

def decode_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        signing = f"{header}.{payload}".encode()
        expected = _b64(hmac.new(settings.jwt_secret_key.encode(), signing, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): raise ValueError("signature")
        decoded_header = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
        if decoded_header.get("alg") != "HS256" or decoded_header.get("typ") != "JWT": raise ValueError("header")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) <= int(time.time()): raise ValueError("expired")
        if not str(data["sub"]).isdigit(): raise ValueError("subject")
        return data
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token", headers={"WWW-Authenticate":"Bearer"})
