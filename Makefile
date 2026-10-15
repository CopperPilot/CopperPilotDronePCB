# ==============================================================================
# CopperPilot Drone PCB & Firmware - Unified Root Build & Verification Makefile
# ==============================================================================

PYTHON ?= python3

.PHONY: all help fmt fmt-check lint test test-fw test-pcb test-case collision coverage coverage-fw coverage-pcb \
        build-fw build-pcb build-case drc erc clean distclean

# Default target runs complete verification across hardware, firmware, and mechanical enclosure
all: test lint

help:
	@echo "======================================================================"
	@echo "CopperPilot Drone: Unified Multi-Language Build & Verification System"
	@echo "======================================================================"
	@echo "Top-Level Targets:"
	@echo "  make fmt          - In-place formatting across firmware, PCB tests, and enclosure suites"
	@echo "  make fmt-check    - Non-destructive code formatting compliance check"
	@echo "  make lint         - Static analysis (C/C++ clang/cppcheck, PCB ERC, Python ruff)"
	@echo "  make test         - Run full test suite: firmware + PCB hardware + 3D enclosure"
	@echo "  make test-fw      - Run native desktop firmware unit tests (Unity framework)"
	@echo "  make test-pcb     - Run 21-point automated PCB hardware verification suite (PyTest)"
	@echo "  make test-case    - Run 18-point automated 3D enclosure verification suite (PyTest)"
	@echo "  make collision    - Run 3D collision detection and clearance queries (Trimesh vs KiCad STL)"
	@echo "  make coverage     - Generate statement coverage reports (gcov for C, pytest-cov for PCB)"
	@echo "  make drc          - Run KiCad CLI Design Rule Check on PCB layout (0 errors, 100% routed)"
	@echo "  make erc          - Run KiCad CLI Electrical Rule Check on schematic (0 errors)"
	@echo "  make build-fw     - Cross-compile target ESP32-S3 firmware using ESP-IDF"
	@echo "  make build-pcb    - Generate JLCPCB manufacturing release bundle (Gerbers, drill, CPL, BOM)"
	@echo "  make build-case   - Synthesize parametric 3D enclosure CAD models (case_top.stl, case_bottom.stl)"
	@echo "  make clean        - Clean intermediate build and test outputs in all subdirectories"
	@echo "  make distclean    - Deep clean removing caches, virtual environments, and artifacts"

# ------------------------------------------------------------------------------
# Formatting
# ------------------------------------------------------------------------------
fmt:
	@echo ">>> [1/3] Formatting Firmware Source Code..."
	@$(MAKE) -C firmware fmt
	@echo ">>> [2/3] Formatting PCB Python Test Suites..."
	@if command -v ruff > /dev/null; then \
		ruff format pcb/tests; \
	elif $(PYTHON) -m ruff --version > /dev/null 2>&1; then \
		$(PYTHON) -m ruff format pcb/tests; \
	else \
		echo "Notice: ruff not installed. Skipping Python formatting."; \
	fi
	@echo ">>> [3/3] Formatting Case Python Suite..."
	@$(MAKE) -C case fmt
	@echo "All formatting complete."

fmt-check:
	@echo ">>> [1/3] Checking Firmware Formatting..."
	@$(MAKE) -C firmware fmt-check
	@echo ">>> [2/3] Checking PCB Python Test Formatting..."
	@if command -v ruff > /dev/null; then \
		ruff format --check pcb/tests; \
	elif $(PYTHON) -m ruff --version > /dev/null 2>&1; then \
		$(PYTHON) -m ruff format --check pcb/tests; \
	else \
		echo "Notice: ruff not installed. Skipping Python format check."; \
	fi
	@echo ">>> [3/3] Checking Case Python Formatting..."
	@$(MAKE) -C case fmt-check
	@echo "All format checks passed."

# ------------------------------------------------------------------------------
# Linting & Static Analysis
# ------------------------------------------------------------------------------
lint:
	@echo ">>> [1/4] Running Firmware Static Analysis..."
	@$(MAKE) -C firmware lint
	@echo ">>> [2/4] Running KiCad Schematic Electrical Rule Check (ERC)..."
	@$(MAKE) -C pcb erc
	@echo ">>> [3/4] Running PCB Python Test Suite Linting..."
	@if command -v ruff > /dev/null; then \
		ruff check pcb/tests; \
	elif $(PYTHON) -m ruff --version > /dev/null 2>&1; then \
		$(PYTHON) -m ruff check pcb/tests; \
	else \
		echo "Notice: ruff not installed. Skipping Python linting."; \
	fi
	@echo ">>> [4/4] Running Case Python Suite Linting..."
	@$(MAKE) -C case lint
	@echo "All linting and static analysis passed cleanly."

# ------------------------------------------------------------------------------
# Testing
# ------------------------------------------------------------------------------
test: test-fw test-pcb test-case
	@echo "======================================================================"
	@echo "SUCCESS: All firmware, PCB hardware, and 3D enclosure tests passed!"
	@echo "======================================================================"

test-fw:
	@echo ">>> Running Native Firmware Desktop Unit Tests (Unity Framework)..."
	@$(MAKE) -C firmware test

test-pcb:
	@echo ">>> Running Automated PCB Hardware Verification Suite (PyTest)..."
	@$(MAKE) -C pcb test

test-case:
	@echo ">>> Running Automated 3D Enclosure Verification Suite (PyTest)..."
	@$(MAKE) -C case test

collision:
	@echo ">>> Running Automated 3D Collision Detection & Clearance Queries..."
	@$(MAKE) -C case collision

# ------------------------------------------------------------------------------
# Code Coverage
# ------------------------------------------------------------------------------
coverage: coverage-fw coverage-pcb

coverage-fw:
	@echo ">>> Generating Firmware Statement Coverage Report (gcov)..."
	@$(MAKE) -C firmware coverage

coverage-pcb:
	@echo ">>> Generating PCB Automated Test Coverage Report (pytest-cov)..."
	@cd pcb && $(PYTHON) -m pytest tests/test_pcb.py --cov=tests --cov-report=term-missing

# ------------------------------------------------------------------------------
# Hardware DRC / ERC
# ------------------------------------------------------------------------------
drc:
	@$(MAKE) -C pcb drc

erc:
	@$(MAKE) -C pcb erc

# ------------------------------------------------------------------------------
# Cross-Compilation & Manufacturing Builds
# ------------------------------------------------------------------------------
build-fw:
	@$(MAKE) -C firmware build

build-pcb:
	@$(MAKE) -C pcb fab

build-case:
	@echo ">>> Synthesizing 3D Enclosure CAD Models..."
	@$(MAKE) -C case generate

# ------------------------------------------------------------------------------
# Cleaning
# ------------------------------------------------------------------------------
clean:
	@$(MAKE) -C firmware clean
	@$(MAKE) -C pcb clean
	@$(MAKE) -C case clean
	@echo "Root workspace cleaned."

distclean: clean
	@rm -rf .pytest_cache pcb/.pytest_cache firmware/.pytest_cache case/.pytest_cache case/build
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.py[cod]" -delete 2>/dev/null || true
	@find . -type d -name "*.dSYM" -exec rm -rf {} + 2>/dev/null || true
	@echo "Distclean complete: all caches, temporaries, and debug symbols removed."
