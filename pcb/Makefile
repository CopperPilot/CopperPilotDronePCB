# ==============================================================================
# CopperPilot Drone PCB - Hardware Verification & Fabrication Makefile
# ==============================================================================

PROJECT_NAME := CopperPilotDrone
PCB_FILE     := $(PROJECT_NAME).kicad_pcb
SCH_FILE     := $(PROJECT_NAME).kicad_sch
PRO_FILE     := $(PROJECT_NAME).kicad_pro
BUILD_DIR    := build
GERBER_DIR   := $(BUILD_DIR)/gerbers
RELEASE_ZIP  := $(BUILD_DIR)/$(PROJECT_NAME)_JLCPCB_Release.zip

PYTHON       := python3
KICAD_CLI    := kicad-cli

.PHONY: all help erc drc test netlist gerbers drill pos bom fab clean

all: test drc erc

help:
	@echo "CopperPilot Drone PCB Targets:"
	@echo "  make test      - Run automated 21-point pytest hardware verification suite"
	@echo "  make drc       - Run KiCad CLI Design Rule Check (asserts 0 errors, 0 unconnected)"
	@echo "  make erc       - Run KiCad CLI Electrical Rule Check (asserts 0 errors)"
	@echo "  make gerbers   - Export RS-274X Gerbers for JLCPCB 2-layer production"
	@echo "  make drill     - Export Excellon NC drill files (metric, plated + non-plated)"
	@echo "  make pos       - Export SMT pick-and-place component centroid file (CPL)"
	@echo "  make bom       - Export structured Bill of Materials"
	@echo "  make fab       - Generate all manufacturing outputs and package into release zip"
	@echo "  make clean     - Remove build outputs, temporary reports, and test caches"

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)
	@mkdir -p $(GERBER_DIR)

erc: $(BUILD_DIR)
	@echo "==> Running KiCad Electrical Rule Check (ERC)..."
	@$(KICAD_CLI) sch erc --format json -o $(BUILD_DIR)/erc_report.json $(SCH_FILE) > /dev/null
	@$(PYTHON) -c "import json, sys; \
		data = json.load(open('$(BUILD_DIR)/erc_report.json')); \
		errors = [v for s in data.get('sheets', []) for v in s.get('violations', []) if v.get('severity') == 'error']; \
		print(f'ERC Results: {len(errors)} errors'); \
		sys.exit(1 if errors else 0)"
	@echo "ERC Clean: 0 errors."

drc: $(BUILD_DIR)
	@echo "==> Running KiCad Design Rule Check (DRC)..."
	@$(KICAD_CLI) pcb drc --format json -o $(BUILD_DIR)/drc_report.json $(PCB_FILE) > /dev/null
	@$(PYTHON) -c "import json, sys; \
data = json.load(open('$(BUILD_DIR)/drc_report.json')); \
errors = [v for v in data.get('violations', []) if v.get('severity') == 'error']; \
unconnected = data.get('unconnected_items', []); \
print(f'DRC Results: {len(errors)} errors, {len(unconnected)} unconnected items'); \
sys.exit(1 if (errors or unconnected) else 0)"
	@echo "DRC Clean: 0 errors, 0 unconnected items (100% routed)."

test:
	@echo "==> Running automated PCB hardware test suite with PyTest..."
	@$(PYTHON) -m pytest tests/test_pcb.py -v

netlist: $(BUILD_DIR)
	@echo "==> Exporting schematic netlist..."
	@$(KICAD_CLI) sch export netlist --format kicadxml -o $(BUILD_DIR)/$(PROJECT_NAME).xml $(SCH_FILE)
	@echo "Saved netlist to $(BUILD_DIR)/$(PROJECT_NAME).xml"

gerbers: $(BUILD_DIR)
	@echo "==> Exporting RS-274X Gerbers for JLCPCB 2-Layer stackup..."
	@$(KICAD_CLI) pcb export gerbers \
		--layers "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" \
		--subtract-soldermask \
		-o $(GERBER_DIR)/ \
		$(PCB_FILE)
	@echo "Gerbers exported to $(GERBER_DIR)/"

drill: $(BUILD_DIR)
	@echo "==> Exporting Excellon NC drill files..."
	@$(KICAD_CLI) pcb export drill \
		--format excellon \
		--drill-origin absolute \
		--excellon-zeros-format decimal \
		--excellon-units mm \
		--excellon-separate-th \
		-o $(GERBER_DIR)/ \
		$(PCB_FILE)
	@echo "Drill files exported to $(GERBER_DIR)/"

pos: $(BUILD_DIR)
	@echo "==> Exporting SMT pick-and-place component centroid (CPL) file..."
	@$(KICAD_CLI) pcb export pos \
		--side front \
		--format csv \
		--units mm \
		-o $(BUILD_DIR)/$(PROJECT_NAME)-top-pos.csv \
		$(PCB_FILE)
	@echo "CPL file exported to $(BUILD_DIR)/$(PROJECT_NAME)-top-pos.csv"

bom: $(BUILD_DIR)
	@echo "==> Generating structured manufacturing BOM..."
	@$(PYTHON) -c "import csv; \
from tests.conftest import KiCadPCB; \
pcb = KiCadPCB('$(PCB_FILE)'); \
f = open('$(BUILD_DIR)/$(PROJECT_NAME)-bom.csv', 'w', newline='', encoding='utf-8'); \
writer = csv.writer(f); \
writer.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part Number']); \
[writer.writerow([pcb.footprints[r]['value'], r, '', '']) for r in sorted(pcb.footprints.keys())]; \
f.close(); \
print('BOM exported to $(BUILD_DIR)/$(PROJECT_NAME)-bom.csv')"

fab: gerbers drill pos bom
	@echo "==> Packaging manufacturing release bundle for JLCPCB..."
	@cd $(GERBER_DIR) && zip -q -r ../$(PROJECT_NAME)_Gerbers.zip *
	@cp $(BUILD_DIR)/$(PROJECT_NAME)-top-pos.csv $(BUILD_DIR)/cpl.csv
	@cp $(BUILD_DIR)/$(PROJECT_NAME)-bom.csv $(BUILD_DIR)/bom.csv
	@cd $(BUILD_DIR) && zip -q $(PROJECT_NAME)_JLCPCB_Release.zip $(PROJECT_NAME)_Gerbers.zip $(PROJECT_NAME)-top-pos.csv $(PROJECT_NAME)-bom.csv
	@echo "JLCPCB Release package created at $(RELEASE_ZIP)"

clean:
	@rm -rf $(BUILD_DIR) .pytest_cache tests/__pycache__ *.json
	@echo "PCB build directory cleaned."
