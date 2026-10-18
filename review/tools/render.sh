#!/usr/bin/env bash
set -euo pipefail

# Deterministic render script for CopperPilot PCB & Schematic
# Usage:
#   review/tools/render.sh <git-ref> <out-dir>
#   review/tools/render.sh --issue <ID>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ "${1:-}" == "--issue" ]]; then
    ISSUE_ID="${2:-}"
    if [[ -z "$ISSUE_ID" ]]; then
        echo "Error: Issue ID required. Example: review/tools/render.sh --issue PCB-001"
        exit 1
    fi
    exec uv run --with pillow --with pymupdf python3 "$SCRIPT_DIR/crop_issue.py" --issue "$ISSUE_ID"
fi

if [[ $# -lt 2 ]]; then
    echo "Usage:"
    echo "  review/tools/render.sh <git-ref> <out-dir>"
    echo "  review/tools/render.sh --issue <ID>"
    exit 1
fi

GIT_REF="$1"
OUT_DIR="$2"

mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"

echo "==> Rendering design from git ref: $GIT_REF to: $OUT_DIR"

TMP_WT=$(mktemp -d -t wt-render-XXXXXX)
cleanup() {
    rm -rf "$TMP_WT" 2>/dev/null || true
    git worktree remove "$TMP_WT" --force 2>/dev/null || true
}
trap cleanup EXIT

git worktree add "$TMP_WT" "$GIT_REF" --detach >/dev/null 2>&1

cd "$TMP_WT/pcb"

echo "  -> Exporting schematic SVG & PDF..."
mkdir -p "$TMP_WT/sch_export"
kicad-cli sch export svg -o "$TMP_WT/sch_export/" CopperPilotDrone.kicad_sch >/dev/null 2>&1 || true
kicad-cli sch export pdf -o "$OUT_DIR/schematic.pdf" CopperPilotDrone.kicad_sch >/dev/null 2>&1 || true

# Convert schematic SVG to PNG
if [[ -f "$TMP_WT/sch_export/CopperPilotDrone.svg" ]]; then
    uv run --with pymupdf --with pillow python3 "$SCRIPT_DIR/svg2png.py" "$TMP_WT/sch_export/CopperPilotDrone.svg" "$OUT_DIR/schematic.png" 300
fi

echo "  -> Exporting PCB layer SVGs..."
mkdir -p "$TMP_WT/pcb_export"
kicad-cli pcb export svg \
    --mode-multi \
    --fit-page-to-board \
    --page-size-mode 2 \
    --exclude-drawing-sheet \
    --cl Edge.Cuts \
    -l "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts,F.CrtYd,B.CrtYd,F.Fab,B.Fab" \
    -o "$TMP_WT/pcb_export/" \
    CopperPilotDrone.kicad_pcb >/dev/null 2>&1 || true

# Map KiCad layer output filenames to canonical layer names
declare -A LAYER_MAP=(
    ["CopperPilotDrone-F_Cu.svg"]="F.Cu"
    ["CopperPilotDrone-B_Cu.svg"]="B.Cu"
    ["CopperPilotDrone-F_Mask.svg"]="F.Mask"
    ["CopperPilotDrone-B_Mask.svg"]="B.Mask"
    ["CopperPilotDrone-F_Silkscreen.svg"]="F.SilkS"
    ["CopperPilotDrone-B_Silkscreen.svg"]="B.SilkS"
    ["CopperPilotDrone-F_Paste.svg"]="F.Paste"
    ["CopperPilotDrone-B_Paste.svg"]="B.Paste"
    ["CopperPilotDrone-Edge_Cuts.svg"]="Edge.Cuts"
    ["CopperPilotDrone-F_Courtyard.svg"]="F.CrtYd"
    ["CopperPilotDrone-B_Courtyard.svg"]="B.CrtYd"
    ["CopperPilotDrone-F_Fab.svg"]="F.Fab"
    ["CopperPilotDrone-B_Fab.svg"]="B.Fab"
)

for SVG_NAME in "${!LAYER_MAP[@]}"; do
    CANON_NAME="${LAYER_MAP[$SVG_NAME]}"
    SVG_PATH="$TMP_WT/pcb_export/$SVG_NAME"
    if [[ -f "$SVG_PATH" ]]; then
        uv run --with pymupdf --with pillow python3 "$SCRIPT_DIR/svg2png.py" "$SVG_PATH" "$OUT_DIR/${CANON_NAME}.png" 600
        cp "$SVG_PATH" "$OUT_DIR/${CANON_NAME}.svg" 2>/dev/null || true
    fi
done

echo "  -> Generating 3D board renders..."
kicad-cli pcb render -w 1600 -h 1600 --side top -o "$OUT_DIR/3d_top.png" CopperPilotDrone.kicad_pcb >/dev/null 2>&1 || true
kicad-cli pcb render -w 1600 -h 1600 --side bottom -o "$OUT_DIR/3d_bottom.png" CopperPilotDrone.kicad_pcb >/dev/null 2>&1 || true
kicad-cli pcb render -w 1600 -h 1600 --rotate '-45,0,45' -o "$OUT_DIR/3d_isometric.png" CopperPilotDrone.kicad_pcb >/dev/null 2>&1 || true

echo "==> Renders completed successfully in: $OUT_DIR"
