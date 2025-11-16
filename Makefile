.PHONY: install test lint format check

install:
	pip install -e .[dev]

test:
	pytest -v --cov=src --cov-report=term-missing

lint:
	black --check src tests
	isort --check-only src tests
	flake8 src tests
	mypy src

format:
	black src tests
	isort src tests

check: lint test