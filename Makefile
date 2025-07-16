.PHONY: test run install format lint clean

# Python interpreter
PYTHON = python3
PIP = pip3

# Test configuration
PYTEST = python -m pytest -v
COVERAGE = --cov=app --cov-report=term-missing --cov-report=html

# Formatting
BLACK = black .
ISORT = isort .
FLAKE8 = flake8
MYPY = mypy .

install:
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

run:
	@echo "Starting development server..."
       FLASK_APP=run.py FLASK_DEBUG=1 $(PYTHON) -m flask run --host=0.0.0.0 --port=5015

test:
	@echo "Running tests..."
	./scripts/install_node_deps.sh
	$(PYTEST) tests/ $(COVERAGE)

format:
	@echo "Formatting code..."
	$(BLACK)
	$(ISORT)

lint:
	@echo "Linting code..."
	$(FLAKE8)
	$(MYPY)

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name "*.py,cover" -delete
	find . -type f -name ".coverage" -delete
