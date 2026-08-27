# VedaAI — Assessment Extraction & Answer Mapping

Hybrid AI pipeline for teachers: upload **Question Paper (PDF/image)** + **Student Answer Sheet (PDF/image)** → extract questions in printed order, transcribe answers, map each answer to its question (with exact highlight), grade and give feedback.

> Figma reference: [VedaAI Hiring Assignment](https://www.figma.com/design/GEjt1rt1s7AXvkcr4t8muE/VedaAI-Hiring-Assignment?node-id=0-1&t=Dv2LriEPmTjljAqe-1) — Upload (empty/filled) → Extracting → Q-A Mapping

## Demo
- **Frontend:** Next.js 14 + Tailwind — pixel Figma (`Upload → Extracting → Mapping` split `Questions | Answer Sheet` with green `Q2` highlight, `2/2` pills, `AI Feedback`)
- **Backend:** FastAPI — `POST /api/v1/sessions` (multipart `questionPaper`, `answerSheet` ≤10MB) → `GET /sessions/{id}` poll/SSE → `GET /file/{question|answer}/{page}`. In-memory TTL 45min.

## Quick Start
### Backend (Python 3.11)
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # add keys below
uvicorn app.main:app --reload --port 8000
# docs at http://localhost:8000/docs
```
### Frontend
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev  # http://localhost:3000
npm run build # production
```

## Env
`backend/.env.example`:
```
GROQ_API_KEY=gsk_...              # free 30 RPM / 14400 day — https://console.groq.com/keys
GROQ_MODEL_Q=openai/gpt-oss-120b  # reasoning (Q extract, grading) — replaces retired llama-3.3-70b (Aug 16 2026)
GROQ_MODEL_FAST=openai/gpt-oss-20b # fast (answer grouping, mapping) — replaces llama-3.1-8b
GEMINI_API_KEY=                   # optional selective vision — https://aistudio.google.com/app/apikey (free 60 RPM)
GEMINI_VISION_MODEL=gemini-2.0-flash
ENABLE_VISION_FALLBACK=true       # low-conf handwriting / diagrams only
```
Without keys, fallback heuristic still runs (mock 14 Q for demo, proves flow).

## API
- `POST /api/v1/sessions` → `{id, status, progress}`
- `GET /api/v1/sessions/{id}` → `{status, progress 0-100, questions, answers{ bboxes[] 0-1 }, mappings, grading, summary}`
- `GET /api/v1/sessions/{id}/stream` → SSE `data: {status, progress}`
- `GET /api/v1/sessions/{id}/file/{question|answer}/{pageIdx}` → `image/jpeg`
- `DELETE /api/v1/sessions/{id}`

## Architecture
```
PDF → Image (PyMuPDF 200dpi)
  → OCR blocks+bboxes + avg_conf (RapidOCR)
  → [if avg_conf<0.55 && GEMINI_API_KEY] Gemini selective transcription (keeps OCR BBox, refines text)
  → Groq gpt-oss-120b structures Questions (preserve 11a/11b, order)
  → Groq gpt-oss-20b groups Answers (blockIds)
  → merge_block_bboxes → AnswerRegion {bboxes: [{pageIndex,x,y,w,h}]}
  → Groq mapping (label-norm + semantic, handles out-of-order, orphan)
  → Groq grading (score/max + 2-sentence feedback)
  → Summary
```
Highlight: frontend `left=x*100% top=y*100% width=w*100%` green `border-2 bg-green-500/10` over `answer` image.

## AI Model / Approach
- **OCR:** `rapidocr-onnxruntime` for deterministic grounding; `PyMuPDF` render.
- **Text LLM:** `openai/gpt-oss-120b` (high reasoning) + `openai/gpt-oss-20b` (fast) via Groq API. No credit card free tier.
- **Vision (optional):** `gemini-2.0-flash` only for low-confidence pages (`avg_conf` tracking in `ocr_service.py`), not full replacement — keeps exact BBox, refines transcription for messy cursive/diagrams. `llava-v1.6-34b` kept as pure-Groq fallback but not used by default.
- Prompts in `backend/app/prompts/*.txt` — JSON-only, sub-parts separate, printed order, orphan handling.

## Assumptions & Limitations
- In-memory store (no DB) — sessions expire 45min, not persistent.
- `Max 10MB` per file (Figma); no auth.
- Printed question OCR fallback mocks 14 Q if heuristic fails; real Groq extracts verbatim.
- Handwriting `RapidOCR` conf shown; selective Gemini improves low-conf but still lenient grading for illegible.
- Multi-page answers grouped by `blockIds` → `bboxes[]` per `pageIndex`; highlight jumps to first page.
- Out-of-order handled via `normalize_label`, semantic fallback `overlap >0.12`.

## Tests
```bash
cd backend
python tests/data/generate_samples.py
pytest -v  # 9 passed — health, upload, label, bbox, mapper (11a/b, out-of-order, orphan)
```

## Folder
```
vedaai/
  backend/  # FastAPI + Groq/Gemini/OCR
  frontend/ # Next.js App Router + Tailwind
  *.png     # Figma design refs
```

## Deployment
- Backend: `Dockerfile` → Render/Fly/Cloud Run `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Frontend: Vercel `NEXT_PUBLIC_API_URL=https://<backend>`

## Submission
Live URL + this repo + approach above.
