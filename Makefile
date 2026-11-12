.PHONY: install dev test seed migrate evaluation build count clean
install:
	python3 -m venv .venv || true
	. .venv/bin/activate && pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	bash scripts/dev.sh

test:
	PYTHONPATH=backend pytest -q backend/tests

seed:
	PYTHONPATH=backend python scripts/seed_demo.py

migrate:
	PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head

evaluation:
	PYTHONPATH=backend python scripts/evaluate.py

build:
	python3 -m compileall -q backend/app backend/tests
	cd frontend && npm run build

count:
	python scripts/count_source_lines.py

clean:
	rm -rf frontend/.next frontend/node_modules backend/__pycache__ backend/app/__pycache__ .pytest_cache
