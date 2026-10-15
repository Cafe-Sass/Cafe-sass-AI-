from fastapi import APIRouter, File, HTTPException, UploadFile

from menu_ocr import menu_from_image

router = APIRouter(prefix="/ai", tags=["ai"])

ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/menu-ocr")
def menu_ocr(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, "Upload a JPG, PNG or WEBP image")
    data = file.file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 10 MB)")
    try:
        result = menu_from_image(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result

try:
    from fastapi import FastAPI

    app = FastAPI(title="CafeHub AI")
    app.include_router(router)
except Exception:  
    pass