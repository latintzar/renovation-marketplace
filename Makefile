.PHONY: install dev build test schema-check doctor walkthrough walkthrough-build
install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt
	npx --yes pnpm@9.0.0 install --frozen-lockfile --ignore-scripts
build:
	.venv/bin/python tools/native.py build
dev:
	.venv/bin/python tools/native.py start
test:
	.venv/bin/python tools/verify.py
schema-check:
	.venv/bin/python tools/schema-check.py

doctor:
	.venv/bin/python tools/doctor.py

walkthrough-build:
	.venv/bin/python tools/build.py
walkthrough:
	.venv/bin/python tools/dev.py
