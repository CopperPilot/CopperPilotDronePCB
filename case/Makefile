# ==============================================================================
# CopperPilot Drone Case - 3D Enclosure Generation & Verification Makefile
# ==============================================================================

PYTHON        := python3
BUILD_DIR     := build
TOP_STL       := $(BUILD_DIR)/case_top.stl
BOT_STL       := $(BUILD_DIR)/case_bottom.stl
PCB_STL       := $(BUILD_DIR)/pcb_assembly.stl
REPORT_JSON   := $(BUILD_DIR)/collision_report.json

.PHONY: all help generate test collision fmt fmt-check lint clean

all: generate test collision

help:
	@echo "CopperPilot Drone Enclosure (case/) Targets:"
	@echo "  make generate  - Synthesize parametric 3D enclosure STLs (case_top.stl, case_bottom.stl)"
	@echo "  make test      - Run automated 18-point PyTest enclosure verification suite"
	@echo "  make collision - Run 3D collision detection and clearance queries against PCB STL"
	@echo "  make fmt       - Format Python source and test code with ruff"
	@echo "  make fmt-check - Non-destructive formatting compliance check"
	@echo "  make lint      - Run static analysis and linting with ruff"
	@echo "  make clean     - Remove generated meshes, build outputs, and test caches"

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

generate: $(BUILD_DIR)
	@echo "==> Synthesizing parametric 3D enclosure CAD models..."
	@$(PYTHON) generate_case.py --output-dir $(BUILD_DIR)

test:
	@echo "==> Running automated enclosure test suite with PyTest..."
	@$(PYTHON) -m pytest tests/test_enclosure.py -v

collision: $(BUILD_DIR)
	@echo "==> Running automated 3D collision and clearance verification..."
	@$(PYTHON) collision.py --case-top $(TOP_STL) --case-bottom $(BOT_STL) --json-report $(REPORT_JSON)

fmt:
	@echo "==> Formatting case Python sources..."
	@if command -v ruff > /dev/null; then \
		ruff format tests/ generator.py generate_case.py collision.py pcb_parser.py; \
	elif $(PYTHON) -m ruff --version > /dev/null 2>&1; then \
		$(PYTHON) -m ruff format tests/ generator.py generate_case.py collision.py pcb_parser.py; \
	else \
		echo "Notice: ruff not installed. Skipping Python formatting."; \
	fi

fmt-check:
	@echo "==> Checking case Python formatting compliance..."
	@if command -v ruff > /dev/null; then \
		ruff format --check tests/ generator.py generate_case.py collision.py pcb_parser.py; \
	elif $(PYTHON) -m ruff --version > /dev/null 2>&1; then \
		$(PYTHON) -m ruff format --check tests/ generator.py generate_case.py collision.py pcb_parser.py; \
	else \
		echo "Notice: ruff not installed. Skipping Python format check."; \
	fi

lint:
	@echo "==> Running case Python static analysis..."
	@if command -v ruff > /dev/null; then \
		ruff check tests/ generator.py generate_case.py collision.py pcb_parser.py; \
	elif $(PYTHON) -m ruff --version > /dev/null 2>&1; then \
		$(PYTHON) -m ruff check tests/ generator.py generate_case.py collision.py pcb_parser.py; \
	else \
		echo "Notice: ruff not installed. Skipping Python linting."; \
	fi

clean:
	@rm -rf $(BUILD_DIR) .pytest_cache tests/__pycache__ __pycache__
	@echo "Case build artifacts and test caches cleaned."
