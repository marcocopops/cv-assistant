# Load PG* variables from .env and pass them to every command.
include .env
export

PYTHON := .venv/bin/python

.PHONY: ingest evals check deploy history

ingest:
	$(PYTHON) cli.py ingest

evals:
	$(PYTHON) -m evals.run knowledge/evals.toml

# Re-index, then evaluate: the database can no longer drift from the files.
check: ingest evals

history:
	$(PYTHON) cli.py history 50

# Deploy only if every evaluation passes.
deploy: check
	docker compose up -d --build --wait