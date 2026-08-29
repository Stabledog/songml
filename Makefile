# Makefile for songml (dev repo)
SHELL=/bin/bash
.ONESHELL:
.SUFFIXES:
.SHELLFLAGS = -uec
MAKEFLAGS += --no-builtin-rules --no-print-directory

absdir := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))

PkgDir := $(absdir)songml-utils
VersionFile := $(PkgDir)/src/songml_utils/__init__.py

FORCE:

help: FORCE
	@echo "Targets:"
	@echo "  test           Run the songml-utils test suite"
	@echo "  lint           Run ruff checks"
	@echo "  bump-version   Bump the patch version in $(VersionFile)"
	@echo "  release        Bump version, commit+push, reinstall to this host"
	@echo "  reinstall      Pull ~/.local/bin and reinstall the songml dotkit"
	@echo "  serve-start    Start songml-serve (this dev tree's code) on :8080"
	@echo "  serve-stop     Stop whatever's serving on :8080"
	@echo "  serve-bounce   Replace whatever's on :8080 with this dev tree's code"
	@echo "  serve-status   Show whether :8080 is up and who's serving it"

test: FORCE
	cd $(PkgDir)
	uv run --extra dev pytest

lint: FORCE
	cd $(PkgDir)
	uv run --extra dev ruff check src/ tests/

bump-version: FORCE
	@
	current=$$(grep -oE '"[0-9]+\.[0-9]+\.[0-9]+"' $(VersionFile) | tr -d '"')
	IFS=. read -r major minor patch <<<"$$current"
	next="$$major.$$minor.$$((patch + 1))"
	sed -i "s/__version__ = \"$$current\"/__version__ = \"$$next\"/" $(VersionFile)
	echo "Bumped version: $$current -> $$next"

release: FORCE bump-version
	@
	cd $(absdir)
	version=$$(grep -oE '"[0-9]+\.[0-9]+\.[0-9]+"' $(VersionFile) | tr -d '"')
	git add $(VersionFile)
	git commit -m "Bump songml-utils version to $$version"
	git push origin main
	$(MAKE) reinstall

reinstall: FORCE
	git -C ~/.local/bin pull
	setup.sh songml

serve-start: FORCE
	$(absdir)bin/test-serve.sh start

serve-stop: FORCE
	$(absdir)bin/test-serve.sh stop

serve-bounce: FORCE
	$(absdir)bin/test-serve.sh bounce

serve-status: FORCE
	$(absdir)bin/test-serve.sh status
