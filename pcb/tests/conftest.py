"""Pytest fixtures and S-expression parsers for CopperPilot Drone PCB automated tests."""

import json
import math
import os
import re
import subprocess

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def fixture(*args, **kwargs):
            return lambda fn: fn

        @staticmethod
        def fail(msg):
            raise AssertionError(msg)

    pytest = _MockPytest()

PCB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PCB_FILE = os.path.join(PCB_DIR, "CopperPilotDrone.kicad_pcb")
SCH_FILE = os.path.join(PCB_DIR, "CopperPilotDrone.kicad_sch")
PRO_FILE = os.path.join(PCB_DIR, "CopperPilotDrone.kicad_pro")


class KiCadPCB:
    """Parser for KiCad PCB S-expression format supporting KiCad 9 and 10."""

    def __init__(self, pcb_path: str):
        self.path = pcb_path
        with open(pcb_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        self._parse_nets()
        self._parse_segments()
        self._parse_vias()
        self._parse_edge_cuts()
        self._parse_footprints()

    def _parse_nets(self):
        # In KiCad 10, nets are defined as (net "NAME") or (net NUMBER "NAME")
        # We collect all distinct net names from definitions, pads, segments, and vias
        self.nets = set()
        for m in re.finditer(r'\(net\s+(?:\d+\s+)?"([^"]+)"\)', self.content):
            name = m.group(1).strip()
            if name:
                self.nets.add(name)

    def _parse_segments(self):
        self.segments = []
        # Multi-line linear segment pattern
        seg_pattern = re.finditer(
            r"\(segment\s+"
            r"\(start\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(end\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(width\s+([-\d\.]+)\)\s+"
            r'\(layer\s+"([^"]+)"\)\s+'
            r'\(net\s+(?:\d+\s+)?"?([^"\)]+)"?\)',
            self.content,
        )
        for m in seg_pattern:
            x1, y1, x2, y2, w, layer, net_name = (
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
                float(m.group(5)),
                m.group(6),
                m.group(7).strip(),
            )
            length = math.hypot(x2 - x1, y2 - y1)
            self.segments.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "width": w,
                    "layer": layer,
                    "net_name": net_name,
                    "length": length,
                }
            )

        # Multi-line arc pattern
        arc_pattern = re.finditer(
            r"\(arc\s+"
            r"\(start\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(mid\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(end\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(width\s+([-\d\.]+)\)\s+"
            r'\(layer\s+"([^"]+)"\)\s+'
            r'\(net\s+(?:\d+\s+)?"?([^"\)]+)"?\)',
            self.content,
        )
        for m in arc_pattern:
            x1, y1, _xm, _ym, x2, y2, w, layer, net_name = (
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
                float(m.group(5)),
                float(m.group(6)),
                float(m.group(7)),
                m.group(8),
                m.group(9).strip(),
            )
            chord = math.hypot(x2 - x1, y2 - y1)
            self.segments.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "width": w,
                    "layer": layer,
                    "net_name": net_name,
                    "length": chord,
                }
            )

    def _parse_vias(self):
        self.vias = []
        via_pattern = re.finditer(
            r"\(via\s+"
            r"(?:\(blind\s+yes\)\s+)?"
            r"\(at\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(size\s+([-\d\.]+)\)\s+"
            r"\(drill\s+([-\d\.]+)\)\s+"
            r"(?:[^\)]*?\)\s+)*?"
            r'\(net\s+(?:\d+\s+)?"?([^"\)]+)"?\)',
            self.content,
        )
        for m in via_pattern:
            x, y, s, d, net_name = (
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
                m.group(5).strip(),
            )
            self.vias.append(
                {
                    "x": x,
                    "y": y,
                    "size": s,
                    "drill": d,
                    "annular_ring": (s - d) / 2.0,
                    "net_name": net_name,
                }
            )

    def _parse_edge_cuts(self):
        self.edge_cuts = []
        # Multi-line gr_line pattern
        line_pat = re.finditer(
            r"\(gr_line\s+"
            r"\(start\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(end\s+([-\d\.]+)\s+([-\d\.]+)\)"
            r"[\s\S]*?"
            r'\(layer\s+"Edge\.Cuts"\)',
            self.content,
        )
        for m in line_pat:
            self.edge_cuts.append(
                {
                    "type": "line",
                    "x1": float(m.group(1)),
                    "y1": float(m.group(2)),
                    "x2": float(m.group(3)),
                    "y2": float(m.group(4)),
                }
            )

        # Multi-line gr_arc pattern
        arc_pat = re.finditer(
            r"\(gr_arc\s+"
            r"\(start\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(mid\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(end\s+([-\d\.]+)\s+([-\d\.]+)\)"
            r"[\s\S]*?"
            r'\(layer\s+"Edge\.Cuts"\)',
            self.content,
        )
        for m in arc_pat:
            self.edge_cuts.append(
                {
                    "type": "arc",
                    "x1": float(m.group(1)),
                    "y1": float(m.group(2)),
                    "xm": float(m.group(3)),
                    "ym": float(m.group(4)),
                    "x2": float(m.group(5)),
                    "y2": float(m.group(6)),
                }
            )

        # Multi-line gr_circle pattern
        circle_pat = re.finditer(
            r"\(gr_circle\s+"
            r"\(center\s+([-\d\.]+)\s+([-\d\.]+)\)\s+"
            r"\(end\s+([-\d\.]+)\s+([-\d\.]+)\)"
            r"[\s\S]*?"
            r'\(layer\s+"Edge\.Cuts"\)',
            self.content,
        )
        for m in circle_pat:
            cx, cy, ex, ey = (
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
            )
            r = math.hypot(ex - cx, ey - cy)
            self.edge_cuts.append(
                {
                    "type": "circle",
                    "cx": cx,
                    "cy": cy,
                    "radius": r,
                }
            )

    def _parse_footprints(self):
        self.footprints = {}
        # Footprint blocks
        fp_matches = list(re.finditer(r'\(footprint\s+"([^"]+)"', self.content))
        for i, m in enumerate(fp_matches):
            start_idx = m.start()
            end_idx = (
                fp_matches[i + 1].start()
                if i + 1 < len(fp_matches)
                else len(self.content)
            )
            block = self.content[start_idx:end_idx]

            ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
            if not ref_match:
                continue
            ref = ref_match.group(1)

            val_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
            val = val_match.group(1) if val_match else ""

            at_match = re.search(
                r"\(at\s+([-\d\.]+)\s+([-\d\.]+)(?:\s+([-\d\.]+))?\)", block
            )
            pos_x = float(at_match.group(1)) if at_match else 0.0
            pos_y = float(at_match.group(2)) if at_match else 0.0
            rot = float(at_match.group(3)) if at_match and at_match.group(3) else 0.0

            models = re.findall(r'\(model\s+"([^"]+)"', block)

            # Extract pads
            pads = []
            pad_pattern = re.finditer(
                r'\(pad\s+"([^"]*)"\s+(\w+)\s+(\w+)\s+'
                r"\(at\s+([-\d\.]+)\s+([-\d\.]+)(?:\s+([-\d\.]+))?\)\s+"
                r"\(size\s+([-\d\.]+)\s+([-\d\.]+)\)"
                r"[\s\S]*?"
                r'(?:\(net\s+(?:\d+\s+)?"?([^"\)\s]+)"?\))?',
                block,
            )
            for pad_m in pad_pattern:
                pad_num = pad_m.group(1)
                pad_type = pad_m.group(2)
                pad_shape = pad_m.group(3)
                px = float(pad_m.group(4))
                py = float(pad_m.group(5))
                pw = float(pad_m.group(7))
                ph = float(pad_m.group(8))
                net_name = pad_m.group(9) if pad_m.group(9) else ""

                pads.append(
                    {
                        "number": pad_num,
                        "type": pad_type,
                        "shape": pad_shape,
                        "rel_x": px,
                        "rel_y": py,
                        "width": pw,
                        "height": ph,
                        "net_name": net_name,
                    }
                )

            self.footprints[ref] = {
                "reference": ref,
                "value": val,
                "x": pos_x,
                "y": pos_y,
                "rotation": rot,
                "models": models,
                "pads": pads,
            }


class KiCadSCH:
    """Parser for KiCad Schematic format."""

    def __init__(self, sch_path: str):
        self.path = sch_path
        with open(sch_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        self._parse_symbols()
        self._parse_wires()
        self._parse_labels()

    def _parse_symbols(self):
        self.symbols = {}
        for m in re.finditer(
            r"\(symbol\s+"
            r'\(lib_id\s+"([^"]+)"\)[\s\S]*?'
            r'\(property\s+"Reference"\s+"([^"]+)"[\s\S]*?'
            r'\(property\s+"Value"\s+"([^"]+)"',
            self.content,
        ):
            lib_id, ref, val = m.group(1), m.group(2), m.group(3)
            self.symbols[ref] = {"lib_id": lib_id, "reference": ref, "value": val}

    def _parse_wires(self):
        self.wires = []
        for m in re.finditer(
            r"\(wire\s+\(pts\s+\(xy\s+([-\d\.]+)\s+([-\d\.]+)\)\s*\(xy\s+([-\d\.]+)\s+([-\d\.]+)\)",
            self.content,
        ):
            self.wires.append(
                (
                    float(m.group(1)),
                    float(m.group(2)),
                    float(m.group(3)),
                    float(m.group(4)),
                )
            )

    def _parse_labels(self):
        self.labels = set()
        for m in re.finditer(r'\(label\s+"([^"]+)"', self.content):
            self.labels.add(m.group(1))
        for m in re.finditer(r'\(global_label\s+"([^"]+)"', self.content):
            self.labels.add(m.group(1))


@pytest.fixture(scope="session")
def pcb_data():
    return KiCadPCB(PCB_FILE)


@pytest.fixture(scope="session")
def sch_data():
    return KiCadSCH(SCH_FILE)


@pytest.fixture(scope="session")
def drc_results():
    """Run kicad-cli pcb drc and return parsed JSON."""
    report_file = os.path.join(PCB_DIR, ".drc_test_report.json")
    cmd = [
        "kicad-cli",
        "pcb",
        "drc",
        "--format",
        "json",
        "-o",
        report_file,
        PCB_FILE,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if not os.path.exists(report_file):
        pytest.fail(f"kicad-cli pcb drc failed: {res.stderr}\n{res.stdout}")

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if os.path.exists(report_file):
        os.remove(report_file)

    return data


@pytest.fixture(scope="session")
def erc_results():
    """Run kicad-cli sch erc and return parsed JSON."""
    report_file = os.path.join(PCB_DIR, ".erc_test_report.json")
    cmd = [
        "kicad-cli",
        "sch",
        "erc",
        "--format",
        "json",
        "-o",
        report_file,
        SCH_FILE,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if not os.path.exists(report_file):
        pytest.fail(f"kicad-cli sch erc failed: {res.stderr}\n{res.stdout}")

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if os.path.exists(report_file):
        os.remove(report_file)

    return data
