from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
from app.config import settings
from app.services.embeddings import _device

@lru_cache(maxsize=1)
def _clip_bundle():
    if not settings.enable_local_models:
        return None
    try:
        import open_clip
        import torch
        model, _, preprocess = open_clip.create_model_and_transforms(
            settings.image_embedding_model,
            pretrained="laion2b_s34b_b79k",
            device=_device(),
        )
        model.eval()
        return model, preprocess, torch
    except Exception:
        return None

def embed_image(image_path: str) -> tuple[list[float], str]:
    bundle = _clip_bundle()
    if bundle:
        model, preprocess, torch = bundle
        image = Image.open(image_path).convert("RGB")
        tensor = preprocess(image).unsqueeze(0).to(_device())
        with torch.no_grad():
            vector = model.encode_image(tensor)
            vector = vector / vector.norm(dim=-1, keepdim=True)
        return vector[0].detach().cpu().tolist(), "openclip_vit_b32"
    # Explicitly labelled fallback: HSV colour histogram, not object-level CLIP inference.
    image = Image.open(image_path).convert("RGB").resize((128, 128))
    hsv = np.asarray(image.convert("HSV"), dtype=np.uint8)
    hist, _ = np.histogramdd(
        hsv.reshape(-1, 3), bins=(8, 8, 8), range=((0, 256), (0, 256), (0, 256))
    )
    vector = hist.astype(float).flatten()
    norm = float(np.linalg.norm(vector)) or 1.0
    return (vector / norm).tolist(), "opencv_hsv_histogram_fallback"
