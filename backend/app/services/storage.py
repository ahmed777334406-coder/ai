import hashlib, io, uuid
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import HTTPException, UploadFile
from app.config import settings

ALLOWED_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg", {".jpg", ".jpeg"}),
    "PNG": ("image/png", ".png", {".png"}),
    "WEBP": ("image/webp", ".webp", {".webp"}),
}
MAX_IMAGE_PIXELS = 25_000_000

async def save_upload(upload: UploadFile, private: bool = False) -> dict:
    raw = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if not raw:
        raise HTTPException(400, "Empty image upload")
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image exceeds {settings.max_upload_mb} MB")

    supplied_suffix = Path(upload.filename or "").suffix.lower()
    if supplied_suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(415, "File extension must be JPG, JPEG, PNG or WEBP")

    try:
        probe = Image.open(io.BytesIO(raw))
        actual_format = probe.format
        if actual_format not in ALLOWED_FORMATS:
            raise HTTPException(415, "Unsupported image format. Upload JPEG, PNG or WEBP.")
        mime_type, extension, valid_suffixes = ALLOWED_FORMATS[actual_format]
        if supplied_suffix not in valid_suffixes:
            raise HTTPException(415, "File extension does not match the image content")
        if probe.width * probe.height > MAX_IMAGE_PIXELS:
            raise HTTPException(413, "Image dimensions exceed the 25-megapixel safety limit")
        probe.verify()
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)
        has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
        if actual_format == "JPEG":
            image = image.convert("RGB")
        elif actual_format == "PNG":
            image = image.convert("RGBA" if has_alpha else "RGB")
        else:  # WEBP
            image = image.convert("RGBA" if has_alpha else "RGB")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise HTTPException(415, "Unsupported or invalid image. Upload a valid JPEG, PNG or WEBP file.")

    root = Path(settings.upload_dir) / ("private" if private else "public")
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    path = root / filename
    save_options = {"format": actual_format}
    if actual_format in {"JPEG", "WEBP"}:
        save_options["quality"] = 90
    if actual_format == "JPEG":
        save_options["optimize"] = True
    elif actual_format == "PNG":
        save_options["optimize"] = True
    elif actual_format == "WEBP":
        save_options["method"] = 6
    image.save(path, **save_options)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path),
        "filename": filename,
        "sha256": digest,
        "mime_type": mime_type,
        "public_url": None if private else f"/media/public/{filename}",
        "is_private": private,
    }
