PYTHON ?= python3
VENV_DIR ?= .venv
PIP := $(VENV_DIR)/bin/pip
PY := $(VENV_DIR)/bin/python

.PHONY: venv install backend frontend run-backend run-frontend

venv:
	$(PYTHON) -m venv $(VENV_DIR)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt

backend:
	$(PY) backend/run.py

run-backend: backend

frontend:
	npm --prefix frontend install
	npm --prefix frontend run dev

run-frontend: frontend
