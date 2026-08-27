# VedaAI Hybrid Backend (Groq + Gemini Selective Vision + OCR)

Real-world FastAPI backend for Assessment Extraction & Answer Mapping.

## Features
- Upload question paper + answer sheet (PDF/image, ≤10MB)
- OCR via RapidOCR -> exact bbox grounding (no hallucinated coords)
- Groq `openai/gpt-oss-120b` (reasoning) + `openai/gpt-oss-20b` (fast) for structuring, mapping, grading — free tier 30 RPM / 14400 day (legacy llama-3.1/3.3 retired Aug 16 2026)
- Gemini `gemini-2.0-flash` **selective** vision for low-confidence handwriting / diagrams only (avg OCR conf <0.55). Disabled when `GEMINI_API_KEY` empty — pipeline falls back to OCR.
- In-memory session store (TTL 45min), SSE progress stream, file serving for viewer
- Handles sub-parts (11a/11b), out-of-order, unanswered, orphan, multi-page

## Quick Start
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # add GROQ_API_KEY and optionally GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
# docs at http://localhost:8000/docs
```

## Env
`GROQ_API_KEY` required for LLM stages; without it fallback heuristic still works (mock data for testing).  
`GEMINI_API_KEY` optional — enables selective vision for messy handwriting. Get at https://aistudio.google.com/app/apikey (free 60 RPM).  
`ENABLE_VISION_FALLBACK=true` to activate selective vision (default true).

## API
- `POST /api/v1/sessions` multipart `questionPaper`, `answerSheet`
- `GET /api/v1/sessions/{id}` poll
- `GET /api/v1/sessions/{id}/stream` SSE
- `GET /api/v1/sessions/{id}/file/{type}/{page}`
- `DELETE /api/v1/sessions/{id}`

## Testing
```bash
python tests/data/generate_samples.py
pytest -v
```

## Folder
`D:\vedaai\backend` is self-contained. `tmp/sessions` is temp storage.

## Hybrid Design
PDF->Image (PyMuPDF 200dpi) -> OCR blocks+bboxes (RapidOCR, avg_conf tracked) -> [if low conf <0.55 and Gemini configured] Gemini selective transcription (enhances textPreview, keeps OCR BBox) -> Groq `gpt-oss-120b/20b` structures questions -> groups answers -> deterministic bbox merge -> maps -> grades.
Highlight uses OCR-derived normalized BBoxes `0-1` per page for exact frontend overlay; vision only refines text.
