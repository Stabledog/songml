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
