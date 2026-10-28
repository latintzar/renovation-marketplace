.PHONY: install dev build test schema-check doctor
install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt
	npx --yes pnpm@9.0.0 install --frozen-lockfile --ignore-scripts
build:
	.venv/bin/python tools/build.py
dev:
	.venv/bin/python tools/dev.py
test:
	.venv/bin/python tools/verify.py
schema-check:
	.venv/bin/python tools/schema-check.py

doctor:
	.venv/bin/python tools/doctor.py
