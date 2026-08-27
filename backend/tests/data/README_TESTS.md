# Test Data

- `sample_question_paper.pdf` (2 pages, 14 Q inc 11a/b) -> mimics Class_10_maths_unit_test.pdf
- `sample_answer_sheet.pdf` (4 pages) -> Q1,Q2,Q3,Q5 answered out-of-order sample, with diagrams
- `sample_question_page.png` -> single image variant
- `tmp_answer_imgs/*.jpg` -> source images

Generated via `E:\anaconda\python.exe tests/data/generate_samples.py`

To test with real files, place your PDFs in this folder and use curl:
```bash
curl -F questionPaper=@sample_question_paper.pdf -F answerSheet=@sample_answer_sheet.pdf http://localhost:8000/api/v1/sessions
curl http://localhost:8000/api/v1/sessions/{id}
curl http://localhost:8000/api/v1/sessions/{id}/file/answer/0 --output page0.jpg
```
