# Makefile for managing a Python virtual environment and dependencies.

VENV         := .venv
PYTHON       := python3
BIN          := $(VENV)/bin
REQUIREMENTS := requirements.txt
STAMP        := $(VENV)/.install-stamp

.DEFAULT_GOAL := help

## help: Show this help message
.PHONY: help
help:
	@echo "Available targets:"
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'

## venv: Create the virtualenv (if missing) and install requirements
.PHONY: venv
venv: $(STAMP)

# Create the virtualenv only if it doesn't already exist.
$(BIN)/python:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip

# Reinstall whenever requirements.txt changes (tracked via a stamp file).
$(STAMP): $(BIN)/python $(REQUIREMENTS)
	$(BIN)/pip install -r $(REQUIREMENTS)
	@touch $(STAMP)

## install: Alias for venv — install/sync dependencies
.PHONY: install
install: venv

## freeze: Write currently installed packages to requirements.lock.txt
.PHONY: freeze
freeze: venv
	$(BIN)/pip freeze > requirements.lock.txt
	@echo "Wrote requirements.lock.txt"

## shell: Print the command to activate the virtualenv
.PHONY: shell
shell:
	@echo "Run: source $(BIN)/activate"

## clean: Remove the virtualenv
.PHONY: clean
clean:
	rm -rf $(VENV)

## rebuild: Remove and recreate the virtualenv from scratch
.PHONY: rebuild
rebuild: clean venv
