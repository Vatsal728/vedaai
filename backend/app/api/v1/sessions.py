import os
import uuid
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from loguru import logger
from app.store.memory_store import get_store
from app.services.file_service import save_and_process, ensure_session_dir, cleanup_session
from app.services.pipeline import run_pipeline
from app.models.enums import SessionStatus
import json

router = APIRouter()

@router.post("", status_code=201)
async def create_session(
    background_tasks: BackgroundTasks,
    questionPaper: UploadFile = File(..., description="Question paper PDF or image"),
    answerSheet: UploadFile = File(..., description="Answer sheet PDF or image"),
):
    # Validate at least both files
    if not questionPaper or not answerSheet:
        raise HTTPException(status_code=422, detail="Both questionPaper and answerSheet files required")

    session_id = str(uuid.uuid4())
    session_dir = ensure_session_dir(session_id)
    created = datetime.utcnow()

    # Initial session entry
    store = get_store()
    base_session = {
        "id": session_id,
        "status": SessionStatus.uploading,
        "progress": 5,
        "createdAt": created,
        "updatedAt": created,
        "files": {
            "questionPaper": {"name": questionPaper.filename, "pages": 0, "size": 0, "mime": questionPaper.content_type, "images": []},
            "answerSheet": {"name": answerSheet.filename, "pages": 0, "size": 0, "mime": answerSheet.content_type, "images": []},
        },
        "questions": [],
        "answers": [],
        "mappings": [],
        "grading": [],
        "summary": None,
        "orphans": [],
        "error": None,
    }
    store.create(session_id, base_session)
    logger.info(f"Create session {session_id} files: {questionPaper.filename}, {answerSheet.filename}")

    try:
        # Save and process files
        q_saved, q_images, q_info = await save_and_process(questionPaper, session_dir, "question")
        a_saved, a_images, a_info = await save_and_process(answerSheet, session_dir, "answer")

        # Update files info with imagesUrl for frontend
        def images_url(images, prefix):
            return [f"/api/v1/sessions/{session_id}/file/{prefix}/{i}" for i in range(len(images))]

        store.update(session_id, {
            "status": SessionStatus.extracting_questions,
            "progress": 10,
            "updatedAt": datetime.utcnow(),
            "files": {
                "questionPaper": {
                    "name": q_info["name"],
                    "pages": q_info["pages"],
                    "size": q_info["size"],
                    "mime": q_info["mime"],
                    "saved_path": q_info["saved_path"],
                    "images": q_images,
                    "imagesUrl": images_url(q_images, "question"),
                },
                "answerSheet": {
                    "name": a_info["name"],
                    "pages": a_info["pages"],
                    "size": a_info["size"],
                    "mime": a_info["mime"],
                    "saved_path": a_info["saved_path"],
                    "images": a_images,
                    "imagesUrl": images_url(a_images, "answer"),
                },
            },
        })

        # Launch pipeline in background
        background_tasks.add_task(run_pipeline, session_id, q_images, a_images)

        return {
            "id": session_id,
            "status": SessionStatus.extracting_questions,
            "progress": 10,
            "message": "Session created, processing started",
            "files": store.get(session_id)["files"]
        }

    except Exception as e:
        logger.exception(f"Session {session_id} create failed: {e}")
        # mark error
        store.update(session_id, {"status": SessionStatus.error, "progress": 100, "error": str(e), "updatedAt": datetime.utcnow()})
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{session_id}")
async def get_session(session_id: str):
    store = get_store()
    sess = store.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    # Convert datetimes to iso
    out = dict(sess)
    # Ensure json serializable
    for k in ["createdAt", "updatedAt"]:
        if k in out and hasattr(out[k], "isoformat"):
            out[k] = out[k].isoformat()
    # Strip internal paths for response
    # Keep imagesUrl but hide absolute paths
    return out

@router.get("/{session_id}/stream")
async def stream_session(session_id: str, request: Request):
    """
    SSE stream for progress. Falls back to polling if client prefers.
    """
    store = get_store()
    if not store.get(session_id):
        raise HTTPException(404, "Session not found")

    async def event_gen():
        last_progress = -1
        while True:
            if await request.is_disconnected():
                break
            sess = store.get(session_id)
            if not sess:
                yield f"event: error\ndata: {json.dumps({'error': 'not found'})}\n\n"
                break
            status = sess.get("status")
            progress = sess.get("progress", 0)
            if progress != last_progress:
                data = json.dumps({"status": status, "progress": progress, "updatedAt": sess.get("updatedAt").isoformat() if hasattr(sess.get("updatedAt"), "isoformat") else str(sess.get("updatedAt"))})
                yield f"data: {data}\n\n"
                last_progress = progress
            if status in [SessionStatus.done, SessionStatus.error]:
                # send final full session
                final = json.dumps({"status": status, "progress": progress, "done": True})
                yield f"event: done\ndata: {final}\n\n"
                break
            await asyncio.sleep(1.0)

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@router.get("/{session_id}/file/{file_type}/{page_idx}")
async def get_page_image(session_id: str, file_type: str, page_idx: int):
    if file_type not in ["question", "answer"]:
        raise HTTPException(400, "file_type must be question or answer")
    store = get_store()
    sess = store.get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    files = sess.get("files", {})
    key = "questionPaper" if file_type == "question" else "answerSheet"
    info = files.get(key)
    if not info:
        raise HTTPException(404, "File not found")
    images = info.get("images", [])
    if page_idx < 0 or page_idx >= len(images):
        raise HTTPException(404, f"Page {page_idx} not found, max {len(images)-1}")
    path = images[page_idx]
    if not os.path.exists(path):
        raise HTTPException(404, "Image file missing")
    return FileResponse(path, media_type="image/jpeg", filename=f"{file_type}_{page_idx}.jpg")

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    store = get_store()
    sess = store.get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    cleanup_session(session_id)
    store.delete(session_id)
    return {"ok": True, "deleted": session_id}

@router.get("/{session_id}/questions")
async def get_questions(session_id: str):
    store = get_store()
    sess = store.get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return {"questions": sess.get("questions", [])}

@router.get("/{session_id}/mappings")
async def get_mappings(session_id: str):
    store = get_store()
    sess = store.get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return {
        "mappings": sess.get("mappings", []),
        "answers": sess.get("answers", []),
        "grading": sess.get("grading", []),
        "summary": sess.get("summary")
    }
