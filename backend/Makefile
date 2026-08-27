install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v

test-cov:
	pytest --cov=app tests/

gen-samples:
	python tests/data/generate_samples.py

docker-build:
	docker build -t vedaai-backend .

docker-run:
	docker run -p 8000:8000 --env-file .env -v ./tmp:/app/tmp vedaai-backend
