import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.gemini_service import transcribe_handwriting_image, get_gemini_configured
def test_gemini_vision_transcription():
    c = get_gemini_configured()
    p = os.path.join(os.path.dirname(__file__), 'data', 'sample_question_page.png')
    t = transcribe_handwriting_image(p)
    if c:
        assert t is not None
    else:
        assert t is None