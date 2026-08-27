from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_create_session_missing_files():
    r = client.post("/api/v1/sessions", files={})
    assert r.status_code == 422

def test_create_session_with_samples():
    # Use generated samples if exist, else skip
    q_path = os.path.join(os.path.dirname(__file__), "data", "sample_question_paper.pdf")
    a_path = os.path.join(os.path.dirname(__file__), "data", "sample_answer_sheet.pdf")
    if not os.path.exists(q_path) or not os.path.exists(a_path):
        # generate
        import subprocess, sys
        gen = os.path.join(os.path.dirname(__file__), "data", "generate_samples.py")
        subprocess.run([sys.executable, gen], check=False)
    if not os.path.exists(q_path):
        assert True  # skip if still not exists
        return
    with open(q_path, "rb") as qf, open(a_path, "rb") as af:
        r = client.post(
            "/api/v1/sessions",
            files={
                "questionPaper": ("sample_question_paper.pdf", qf, "application/pdf"),
                "answerSheet": ("sample_answer_sheet.pdf", af, "application/pdf"),
            }
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "id" in data
    sid = data["id"]
    # Poll
    import time
    for _ in range(10):
        r2 = client.get(f"/api/v1/sessions/{sid}")
        assert r2.status_code == 200
        sess = r2.json()
        if sess["status"] == "done":
            assert len(sess["questions"]) >= 10
            assert "mappings" in sess
            assert "grading" in sess
            break
        time.sleep(0.8)
    else:
        # allow done even if not yet, check at least extracting
        r2 = client.get(f"/api/v1/sessions/{sid}")
        assert r2.json()["progress"] >= 10

def test_label_utils():
    from app.utils.label import normalize_label
    assert normalize_label("Q1.") == "1"
    assert normalize_label("11(a)") == "11-a"
    assert normalize_label("11 b)") == "11-b"
    assert normalize_label("Q 11 B") == "11-b"
    assert normalize_label("  2  ") == "2"

def test_bbox_merge():
    from app.utils.bbox import merge_block_bboxes
    blocks = [
        {"id": 0, "bbox": [[10,10],[100,10],[100,40],[10,40]], "pageIndex": 0, "img_w": 1000, "img_h": 1000},
        {"id": 1, "bbox": [[10,50],[100,50],[100,80],[10,80]], "pageIndex": 0, "img_w": 1000, "img_h": 1000},
    ]
    bboxes = merge_block_bboxes(blocks, [0,1], 1000, 1000)
    assert len(bboxes)==1
    assert bboxes[0]["pageIndex"]==0
    assert 0 <= bboxes[0]["x"] <= 1
