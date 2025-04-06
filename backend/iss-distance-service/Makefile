.DEFAULT_GOAL := help

.PHONY: install
install: venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

.PHONY: run
run: install
	.venv/bin/python app.py


.PHONY: help
help:
	@echo ""
	@echo "Available targets:"
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

.PHONY: clean
clean:
	rm -rf .venv;

venv:
	python3 -m venv .venv
