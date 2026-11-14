import hashlib, math, re
from functools import lru_cache
from pathlib import Path
from app.config import settings

SYNONYMS = {
    "耳机": "earbuds headphones", "蓝牙耳机": "wireless earbuds headphones", "耳机盒": "earbuds case",
    "钱包": "wallet purse", "学生卡": "student id card", "校园卡": "student id card",
    "钥匙": "keys key", "背包": "backpack bag", "书包": "backpack bag", "水杯": "water bottle",
    "水瓶": "water bottle", "手表": "watch", "手机": "phone smartphone", "笔记本电脑": "laptop",
    "黑色": "black", "白色": "white", "蓝色": "blue", "红色": "red", "银色": "silver",
    "图书馆": "library", "食堂": "cafeteria canteen", "教学楼": "classroom building",
    "体育馆": "gymnasium sports hall", "宿舍": "dormitory residence hall",
}

@lru_cache(maxsize=1)
def _e5_model():
    if not settings.enable_local_models:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(settings.text_embedding_model, device=_device(), cache_folder=settings.model_cache_dir)
    except Exception:
        return None

def _device() -> str:
    if settings.ai_device != "auto": return settings.ai_device
    try:
        import torch
        if torch.cuda.is_available(): return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available(): return "mps"
    except Exception:
        pass
    return "cpu"

def _canonicalize(text: str) -> str:
    normalized = (text or "").lower()
    for source in sorted(SYNONYMS, key=len, reverse=True):
        normalized = normalized.replace(source, f" {SYNONYMS[source]} ")
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalized)
    return " ".join(tokens)

def _fallback_vector(text: str, dimensions: int = 384) -> list[float]:
    canonical = _canonicalize(text)
    tokens = canonical.split()
    features = tokens + [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens)-1)]
    vector = [0.0] * dimensions
    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(x*x for x in vector)) or 1.0
    return [x / norm for x in vector]

def embed_text(text: str, role: str = "passage") -> tuple[list[float], str]:
    model = _e5_model()
    if model is not None:
        prefix = "query: " if role == "query" else "passage: "
        vector = model.encode(prefix + text, normalize_embeddings=True).tolist()
        if len(vector) == 384:
            method = "multilingual_e5_small" if settings.text_embedding_model == "intfloat/multilingual-e5-small" else "e5:" + settings.text_embedding_model
            return vector, method
    return _fallback_vector(text), "bilingual_rule_hash_fallback"

def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b or len(a) != len(b): return None
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0: return None
    return max(0.0, min(1.0, dot / (na * nb)))
