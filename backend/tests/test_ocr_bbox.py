def test_ocr_import():
    from app.services.ocr_service import get_ocr_engine
    eng = get_ocr_engine()
    assert eng is not None
