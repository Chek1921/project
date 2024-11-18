.PHONY: seed api worker test train

seed:
	python scripts/seed_data.py

api:
	uvicorn api.main:app --reload

worker:
	python -m worker.run

test:
	pytest -q

train:
	python ml/train.py
