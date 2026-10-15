import json
import re
import statistics
import sys

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
PRICE_RE = re.compile(
    r"\s*(\d+(?:[.,]\d+)?)\s*(?:EGP|LE|L\.E\.?|جنيه|ج\.م|جم|ج|£)?\s*", re.I
)
AR_CHAR_RE = re.compile(r"[\u0600-\u06FF]")
LOW_CONF = 0.5

_reader = None


def get_reader():
    global _reader
    if _reader is None:
        import easyocr

        _reader = easyocr.Reader(["ar", "en"], gpu=False)
    return _reader


def preprocess(image_bytes: bytes):
    import cv2
    import numpy as np

    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image file")
    h, w = img.shape[:2]
    if max(h, w) < 1600: 
        scale = 1600 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 10)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)


def run_ocr(image_bytes: bytes):
    img = preprocess(image_bytes)
    boxes = []
    for bbox, text, conf in get_reader().readtext(img):
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        boxes.append(
            {
                "text": text.strip().translate(AR_DIGITS),
                "conf": float(conf),
                "x": sum(xs) / 4,
                "y": sum(ys) / 4,
                "h": max(ys) - min(ys),
            }
        )
    return [b for b in boxes if b["text"]]


def group_rows(boxes):
    if not boxes:
        return []
    tol = 0.6 * statistics.median(b["h"] for b in boxes)
    rows, current = [], []
    for b in sorted(boxes, key=lambda b: b["y"]):
        if current and abs(b["y"] - statistics.mean(c["y"] for c in current)) > tol:
            rows.append(current)
            current = []
        current.append(b)
    if current:
        rows.append(current)
    return rows


def _to_number(text: str):
    m = PRICE_RE.fullmatch(text)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def _is_category(text: str) -> bool:
    words = text.split()
    if len(words) > 4:
        return False
    return text.isupper() or bool(AR_CHAR_RE.search(text)) or len(words) <= 2


def parse_rows(rows):
    """Turn OCR rows into {'categories': [...]} (rule-based)."""
    categories = []
    current = {"name": "Uncategorized", "items": []}
    last_item = None

    def flush():
        if current["items"]:
            categories.append(dict(current))

    for row in rows:
        prices = [(b, _to_number(b["text"])) for b in row]
        price_boxes = [b for b, v in prices if v is not None]
        name_boxes = [b for b, v in prices if v is None]
        if not name_boxes:
            continue

        text_all = " ".join(b["text"] for b in name_boxes)
        is_rtl = sum(bool(AR_CHAR_RE.search(b["text"])) for b in name_boxes) > len(name_boxes) / 2
        name_boxes.sort(key=lambda b: b["x"], reverse=is_rtl)
        name = " ".join(b["text"] for b in name_boxes)
        conf = statistics.mean(b["conf"] for b in row)

        if price_boxes:
            vals = [_to_number(b["text"]) for b in sorted(price_boxes, key=lambda b: b["x"])]
            last_item = {
                "name": name,
                "price": vals[0],
                "prices": vals,
                "description": "",
                "confidence": round(conf, 2),
                "needs_review": conf < LOW_CONF,
            }
            current["items"].append(last_item)
        elif _is_category(text_all):
            flush()
            current = {"name": text_all, "items": []}
            last_item = None
        elif last_item is not None: 
            last_item["description"] = (last_item["description"] + " " + name).strip()

    flush()
    return {"categories": categories}


def menu_from_image(image_bytes: bytes) -> dict:
    return parse_rows(group_rows(run_ocr(image_bytes)))


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        print(json.dumps(menu_from_image(f.read()), ensure_ascii=False, indent=2))