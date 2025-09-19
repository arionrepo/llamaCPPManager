.PHONY: venv install-dev test test-unit test-integration gui-test clean

PY?=python3
VENV=.venv
PIP=$(VENV)/bin/pip
PYTEST=$(VENV)/bin/pytest

venv:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install -U pip

install-dev: venv
	$(PIP) install -e . -r requirements-dev.txt

test: install-dev
	$(PYTEST) -q

test-unit: install-dev
	$(PYTEST) -q -m 'not integration'

test-integration: install-dev
	$(PYTEST) -q -m integration

gui-test:
	cd gui-macos && swift test -q

clean:
	rm -rf $(VENV) .pytest_cache .coverage dist build
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
