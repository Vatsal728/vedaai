from enum import Enum

class SessionStatus(str, Enum):
    uploading = "uploading"
    extracting_questions = "extracting_questions"
    extracting_answers = "extracting_answers"
    mapping = "mapping"
    grading = "grading"
    done = "done"
    error = "error"
