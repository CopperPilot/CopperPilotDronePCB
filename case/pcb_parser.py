#!/usr/bin/env python3
"""KiCad PCB Geometry and Mechanical Constraint Parser for Drone Enclosure.

Extracts post-snap-off fuselage boundaries, break-away mousebite tabs,
snap hook landing zones, and 3D component keepouts from CopperPilotDrone.kicad_pcb.
"""

import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

# Default path to KiCad PCB file
DEFAULT_PCB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "pcb", "CopperPilotDrone.kicad_pcb")
)


@dataclass
class ComponentKeepout:
    """3D bounding volume and alignment target for an electrical component."""

    ref: str
    val: str
    kicad_pos: list[float]  # [x, y, z_base]
    pos_3d: list[float]  # [x, y_3d = -y_kicad, z_top]
    size: list[float]  # [width_x, length_y, height_z]
    rotation: float
    description: str = ""


@dataclass
class SnapLandingZone:
    """Under-board landing zone along a waist notch for cantilever snap hooks."""

    name: str
    edge_x: float  # X coordinate of the board edge
    y_min: float  # Minimum Y along the edge
    y_max: float  # Maximum Y along the edge
    y_center: float  # Midpoint Y
    length: float  # Usable notch span
    board_thickness: float = 1.6
    clearance_inner: float = 3.5  # Copper-free setback inward from edge


@dataclass
class FuselageGeometry:
    """Post-snap-off central fuselage envelope and airframe parameters."""

    center_kicad: list[float]  # [x, y] in KiCad coordinates
    center_3d: list[float]  # [x, y] in 3D STL coordinates (y_3d = -y_kicad)
    width: float  # X span of central hub (mm)
    length: float  # Y span of central hub (mm)
    thickness: float  # PCB finished thickness (mm)
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    waist_notches: list[SnapLandingZone] = field(default_factory=list)
    components: dict[str, ComponentKeepout] = field(default_factory=dict)
    snap_off_units: list[dict[str, Any]] = field(default_factory=list)


# Component 3D height above top copper and clearance envelope database
COMPONENT_3D_SPECS: dict[str, dict[str, Any]] = {
    "J1": {
        "name": "USB_C",
        "size": [10.0, 5.0, 3.8],
        "z_offset": 1.6,
        "desc": "USB-C 16-pin receptacle",
    },
    "J3": {
        "name": "BATT_JST_PH",
        "size": [8.0, 6.5, 6.5],
        "z_offset": 1.6,
        "desc": "1S LiPo JST-PH 2.0mm SMT connector (tallest component)",
    },
    "SW1": {
        "name": "POWER_SWITCH",
        "size": [6.7, 3.0, 3.5],
        "z_offset": 1.6,
        "desc": "PCM12SMTR power slide switch",
    },
    "SW2": {
        "name": "RESET_BUTTON",
        "size": [5.1, 5.1, 2.0],
        "z_offset": 1.6,
        "desc": "TS-1187A momentary tactile reset button",
    },
    "SW3": {
        "name": "BOOT_BUTTON",
        "size": [5.1, 5.1, 2.0],
        "z_offset": 1.6,
        "desc": "TS-1187A momentary tactile boot button",
    },
    "U8": {
        "name": "ESP32_S3",
        "size": [18.0, 25.5, 3.2],
        "z_offset": 1.6,
        "desc": "ESP32-S3-WROOM-1 MCU module with PCB antenna",
    },
    "U9": {
        "name": "MPU_6050",
        "size": [4.0, 4.0, 1.0],
        "z_offset": 1.6,
        "desc": "MPU-6050 6-axis IMU sensor (acoustic isolation required)",
    },
    "LED1": {
        "name": "POW_LED",
        "size": [2.0, 2.0, 1.0],
        "z_offset": 1.6,
        "desc": "0603 Blue 3.3V Power LED",
    },
    "LED2": {
        "name": "CHG_LED",
        "size": [2.0, 2.0, 1.0],
        "z_offset": 1.6,
        "desc": "0603 Red Charging Indicator LED",
    },
    "LED3": {
        "name": "STDBY_LED",
        "size": [2.0, 2.0, 1.0],
        "z_offset": 1.6,
        "desc": "0603 Green Standby Indicator LED",
    },
    "J2": {
        "name": "MOTOR_1",
        "size": [6.0, 6.0, 4.2],
        "z_offset": 1.6,
        "desc": "JST-GH 1.25mm horizontal motor socket (Rear-Left)",
    },
    "J4": {
        "name": "MOTOR_4",
        "size": [6.0, 6.0, 4.2],
        "z_offset": 1.6,
        "desc": "JST-GH 1.25mm horizontal motor socket (Rear-Right)",
    },
    "J5": {
        "name": "MOTOR_2",
        "size": [6.0, 6.0, 4.2],
        "z_offset": 1.6,
        "desc": "JST-GH 1.25mm horizontal motor socket (Front-Left)",
    },
    "J6": {
        "name": "MOTOR_3",
        "size": [6.0, 6.0, 4.2],
        "z_offset": 1.6,
        "desc": "JST-GH 1.25mm horizontal motor socket (Front-Right)",
    },
    "IC1": {
        "name": "TP4056",
        "size": [4.9, 6.0, 1.75],
        "z_offset": 1.6,
        "desc": "TP4056 ESOP-8 LiPo linear charger",
    },
    "D1": {
        "name": "SS34_DIODE",
        "size": [5.0, 2.6, 2.25],
        "z_offset": 1.6,
        "desc": "SS34 Schottky power rectifier",
    },
}


class KiCadPCBParser:
    """Extracts board outlines, snap-off tabs, and component coordinates from KiCad PCB."""

    def __init__(self, pcb_path: str = DEFAULT_PCB_PATH):
        self.pcb_path = os.path.abspath(pcb_path)
        if not os.path.exists(self.pcb_path):
            raise FileNotFoundError(f"KiCad PCB file not found at: {self.pcb_path}")

        with open(self.pcb_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        self.thickness = self._parse_thickness()
        self.footprints = self._parse_footprints()
        self.mousebites = self._parse_mousebites()
        self.edge_cuts = self._parse_edge_cuts()
        self.fuselage = self._compute_fuselage_geometry()

    def _parse_thickness(self) -> float:
        """Parse finished board thickness from setup block."""
        match = re.search(r"\(thickness\s+([-\d\.]+)\)", self.content)
        return float(match.group(1)) if match else 1.6

    def _parse_footprints(self) -> dict[str, dict[str, Any]]:
        """Parse all footprint references, coordinates, values, and rotations."""
        footprints = {}
        matches = list(re.finditer(r'\(footprint\s+"([^"]+)"', self.content))
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(self.content)
            block = self.content[start:end]

            ref_m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
            if not ref_m:
                continue
            ref = ref_m.group(1)

            val_m = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
            val = val_m.group(1) if val_m else ""

            at_m = re.search(
                r"\(at\s+([-\d\.]+)\s+([-\d\.]+)(?:\s+([-\d\.]+))?\)", block
            )
            x = float(at_m.group(1)) if at_m else 0.0
            y = float(at_m.group(2)) if at_m else 0.0
            rot = float(at_m.group(3)) if (at_m and at_m.group(3)) else 0.0

            footprints[ref] = {
                "reference": ref,
                "value": val,
                "x": x,
                "y": y,
                "rotation": rot,
            }
        return footprints

    def _parse_mousebites(self) -> list[dict[str, float]]:
        """Identify mousebite perforation drill circles along break-away tabs."""
        circles = []
        pattern = re.finditer(
            r"\(gr_circle\s+\(center\s+([-\d\.]+)\s+([-\d\.]+)\)\s+\(end\s+([-\d\.]+)\s+([-\d\.]+)\)",
            self.content,
        )
        for m in pattern:
            cx, cy, ex, ey = (
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
            )
            r = math.hypot(ex - cx, ey - cy)
            # Mousebites are typically 0.5mm drill holes (radius ~0.25mm)
            if 0.15 <= r <= 0.40:
                circles.append({"x": cx, "y": cy, "radius": r})
        return circles

    def _parse_edge_cuts(self) -> list[dict[str, Any]]:
        """Extract all linear and curved line segments on Edge.Cuts."""
        elements = []
        for m in re.finditer(
            r"\(gr_line\s+\(start\s+([-\d\.]+)\s+([-\d\.]+)\)\s+\(end\s+([-\d\.]+)\s+([-\d\.]+)\)[\s\S]*?\(layer\s+\"Edge\.Cuts\"\)",
            self.content,
        ):
            elements.append(
                {
                    "type": "line",
                    "x1": float(m.group(1)),
                    "y1": float(m.group(2)),
                    "x2": float(m.group(3)),
                    "y2": float(m.group(4)),
                }
            )
        return elements

    def _compute_fuselage_geometry(self) -> FuselageGeometry:
        """Derive post-snap-off central fuselage bounds and snap-fit landing zones."""
        # Post-snap-off central hub edges:
        # Left waist notch edge at X = 108.398 mm
        # Right waist notch edge at X = 153.398 mm
        # Top front edge at Y = 64.008 mm
        # Bottom rear fuselage edge at Y = 109.008 mm
        x_min = 108.398
        x_max = 153.398
        y_min = 64.008
        y_max = 109.008

        width = x_max - x_min  # 45.000 mm
        length = y_max - y_min  # 45.000 mm
        center_x = (x_min + x_max) / 2.0  # 130.898 mm
        center_y = (y_min + y_max) / 2.0  # 86.508 mm

        # Snap hook landing zones along the break-away waist notches:
        # Left waist: continuous bare FR-4 between Y in [75.400, 97.617] mm (length 22.217 mm)
        left_zone = SnapLandingZone(
            name="LEFT_WAIST",
            edge_x=x_min,
            y_min=75.400,
            y_max=97.617,
            y_center=(75.400 + 97.617) / 2.0,  # 86.508 mm
            length=97.617 - 75.400,
            board_thickness=self.thickness,
        )

        # Right waist: upper notch Y in [71.900, 77.000] and lower notch Y in [93.000, 99.000]
        # flanking J3 battery connector at Y = 85.541
        right_zone_upper = SnapLandingZone(
            name="RIGHT_WAIST_UPPER",
            edge_x=x_max,
            y_min=71.900,
            y_max=77.000,
            y_center=(71.900 + 77.000) / 2.0,
            length=77.000 - 71.900,
            board_thickness=self.thickness,
        )
        right_zone_lower = SnapLandingZone(
            name="RIGHT_WAIST_LOWER",
            edge_x=x_max,
            y_min=93.000,
            y_max=99.000,
            y_center=(93.000 + 99.000) / 2.0,
            length=99.000 - 93.000,
            board_thickness=self.thickness,
        )

        # Build component 3D keepout map
        components = {}
        for ref, spec in COMPONENT_3D_SPECS.items():
            if ref in self.footprints:
                fp = self.footprints[ref]
                kx, ky = fp["x"], fp["y"]
                rot = fp["rotation"]
                size = spec["size"]
                z_top = self.thickness + size[2]
                components[ref] = ComponentKeepout(
                    ref=ref,
                    val=fp["value"],
                    kicad_pos=[kx, ky, self.thickness],
                    pos_3d=[kx, -ky, z_top],
                    size=size,
                    rotation=rot,
                    description=spec["desc"],
                )

        # Document snap-off units
        snap_off_units = [
            {
                "name": "LEFT_FOOT_UNITS",
                "count": 2,
                "description": "2 snap-off landing gear feet on left rail (X < 108.4 mm)",
                "mousebites_x": [99.126, 108.247],
            },
            {
                "name": "RIGHT_FOOT_UNITS",
                "count": 2,
                "description": "2 snap-off landing gear feet on right rail (X > 153.4 mm)",
                "mousebites_x": [153.548, 162.669],
            },
            {
                "name": "ANTENNA_MANUFACTURING_SUPPORT",
                "count": 1,
                "description": "Break-away panel tab supporting antenna during SMT fabrication (Y > 109.0 mm)",
                "mousebites_y": [109.209, 113.008],
            },
        ]

        return FuselageGeometry(
            center_kicad=[center_x, center_y],
            center_3d=[center_x, -center_y],
            width=width,
            length=length,
            thickness=self.thickness,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            waist_notches=[left_zone, right_zone_upper, right_zone_lower],
            components=components,
            snap_off_units=snap_off_units,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert parsed geometry and constraints to dictionary."""
        fuselage = self.fuselage
        return {
            "pcb_path": self.pcb_path,
            "board_thickness_mm": self.thickness,
            "fuselage_hub": {
                "center_kicad": fuselage.center_kicad,
                "center_3d": fuselage.center_3d,
                "width_mm": fuselage.width,
                "length_mm": fuselage.length,
                "x_range": [fuselage.x_min, fuselage.x_max],
                "y_range": [fuselage.y_min, fuselage.y_max],
            },
            "waist_notches": [asdict(w) for w in fuselage.waist_notches],
            "snap_off_units": fuselage.snap_off_units,
            "components": {k: asdict(v) for k, v in fuselage.components.items()},
        }

    def export_json(self, output_path: str) -> str:
        """Export parsed PCB geometry and constraints to JSON."""
        data = self.to_dict()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="KiCad PCB Geometry and Mechanical Parser for Drone Enclosure"
    )
    parser.add_argument(
        "--pcb",
        type=str,
        default=DEFAULT_PCB_PATH,
        help="Path to input .kicad_pcb file",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="Optional path to output JSON summary",
    )
    args = parser.parse_args()

    parser_obj = KiCadPCBParser(args.pcb)
    data = parser_obj.to_dict()

    print("======================================================================")
    print("CopperPilot Drone: KiCad PCB Mechanical Geometry Summary")
    print("======================================================================")
    print(f"PCB File:             {parser_obj.pcb_path}")
    print(f"Board Thickness:      {data['board_thickness_mm']:.2f} mm")
    print(
        f"Central Hub Center:   KiCad {data['fuselage_hub']['center_kicad']} | 3D {data['fuselage_hub']['center_3d']}"
    )
    print(
        f"Central Hub Envelope: {data['fuselage_hub']['width_mm']:.2f} x {data['fuselage_hub']['length_mm']:.2f} mm"
    )
    print(f"Waist Notches:        {len(data['waist_notches'])} landing zones detected")
    for w in data["waist_notches"]:
        print(
            f"  - {w['name']:18s}: Edge X={w['edge_x']:.2f}, Y=[{w['y_min']:.2f}, {w['y_max']:.2f}], length={w['length']:.2f} mm"
        )
    print(f"Snap-off Units:       {len(data['snap_off_units'])} units identified")
    for u in data["snap_off_units"]:
        print(f"  - {u['name']}: {u['description']}")
    print(
        f"Active Components:    {len(data['components'])} 3D keepout boundaries mapped"
    )
    print("======================================================================")

    if args.json_out:
        parser_obj.export_json(args.json_out)
        print(f"JSON summary written to: {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
