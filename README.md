# CafeHub – Menu OCR (AI Prototype)

Owner uploads a photo of their menu → we return structured JSON (categories, items, prices) → owner reviews it before saving.

## Structure
```
app/
  api.py            POST /ai/menu-ocr (FastAPI router)
  menu_ocr.py       OCR (EasyOCR ar+en) + rule-based parsing
  preprocessing.py  decode, upscale, denoise, deskew, contrast
evaluation/
  evaluate.py       accuracy report on samples/  ->  evaluation/results.md
  ground_truth/     expected JSON per sample image
samples/            menu images (add real photos here + a matching ground_truth/<name>.json)
tests/              parser + evaluator tests (no OCR install needed)
```

## Setup (VS Code terminal, from the project root)
```
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
python -m pip install -r requirements.txt
```
First OCR run downloads the EasyOCR models (internet needed).

## Run
```
python -m app.menu_ocr samples/menu_en.png     # try one image
uvicorn app.api:app --reload                   # API -> http://127.0.0.1:8000/docs
python -m evaluation.evaluate                  # accuracy report
python -m tests.test_parser                    # quick tests
python -m app.preprocessing samples/menu_en.png out.png   # see what the OCR "sees"
```
Backend integration: `from app.api import router; app.include_router(router)`

## API contract
`POST /ai/menu-ocr` — multipart form, field `file` (JPG/PNG/WEBP, max 10 MB)

Response `200`:
```json
{
  "categories": [
    {
      "name": "HOT DRINKS",
      "items": [
        {
          "name": "Cappuccino",
          "price": 45.0,
          "prices": [45.0],
          "description": "Espresso with steamed milk foam",
          "confidence": 0.93,
          "needs_review": false
        }
      ]
    }
  ]
}
```
- `price`: first price on the line; `prices`: all prices (e.g. S/M/L sizes).
- `needs_review: true` when confidence < 0.5 → the review screen should highlight it.
- Errors: `400` invalid image, `413` too large, `415` unsupported type.
- Currency is not returned (prices are plain numbers).

## Adding evaluation samples
1. Put the photo in `samples/` (e.g. `cafe1.jpg`).
2. Write `evaluation/ground_truth/cafe1.json` in the same shape as the response (only `name` and `price` are required per item).
3. `python -m evaluation.evaluate`

## Git
One branch per person (`feature/ocr-parsing`, `feature/ocr-preprocessing`), PR into `main`, put the Jira key in the PR title.
