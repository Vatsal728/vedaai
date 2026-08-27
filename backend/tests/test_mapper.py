from app.services.mapper import fallback_map
from app.services.question_extractor import mock_questions
from app.services.answer_extractor import mock_answer_groups

def test_fallback_map_basic():
    qs = mock_questions()
    # inject id for fallback
    for q in qs:
        q["id"] = f"q_{q['label']}_{q['subLabel']}" if q.get("subLabel") else f"q_{q['label']}"
    ag = mock_answer_groups()
    mappings, orphans = fallback_map(qs, ag)
    assert len(mappings)==len(qs)
    answered = [m for m in mappings if m["status"]=="answered"]
    assert len(answered) >= 5
    # check orphan
    assert len(orphans) >= 1

def test_handle_out_of_order():
    qs = mock_questions()[:4]
    for q in qs:
        q["id"] = f"q_{q['label']}"
    # reverse order answers
    ag = [
        {"detectedLabel":"4", "blockIds":[0], "textPreview":"blood flow"},
        {"detectedLabel":"1", "blockIds":[1], "textPreview":"artery"},
        {"detectedLabel":None, "blockIds":[2], "textPreview":"orphan content xyz"},
    ]
    mappings, orphans = fallback_map(qs, ag)
    # q1 and q4 should be answered despite order
    q1 = next(m for m in mappings if m["questionId"]=="q_1")
    q4 = next(m for m in mappings if m["questionId"]=="q_4")
    assert q1["status"]=="answered"
    assert q4["status"]=="answered"
    assert len(orphans)>=1

def test_subparts_separate():
    qs = [q for q in mock_questions() if q["label"]=="11"]
    for q in qs:
        q["id"] = f"q_{q['label']}_{q['subLabel']}"
    ag = [
        {"detectedLabel":"11-a", "blockIds":[0], "textPreview":"Plant A broad green"},
        {"detectedLabel":"11-b", "blockIds":[1], "textPreview":"move to bright light"},
    ]
    mappings, _ = fallback_map(qs, ag)
    assert all(m["status"]=="answered" for m in mappings)
