run: venv
	.venv/bin/python -m main

test: venv wasmtree/parser.py
	.venv/bin/python -m pytest -vv -s tests

repl: venv
	.venv/bin/python

wasmtree/parser.py: venv grammar.txt generate_parser.py
	.venv/bin/python generate_parser.py

venv: .venv/bin/activate

.venv/bin/activate: requirements.txt requirements-dev.txt
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -r requirements-dev.txt
	touch .venv/bin/activate
