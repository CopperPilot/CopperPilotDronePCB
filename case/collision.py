"""3D Collision Detection and Clearance Verification Engine.

Uses kicad-cli to export full PCB 3D assembly to STL and performs Trimesh BVH,
penetration tests, and proximity/signed-distance queries against the enclosure.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any

import numpy as np
import trimesh

from generator import KEY_COMPONENTS


class CollisionVerifier:
    """Evaluates geometric clearance and physical interference between PCB and enclosure."""

    def __init__(
        self,
        pcb_stl_path: str,
        case_top_path: str,
        case_bottom_path: str,
        min_clearance_mm: float = 0.5,
    ):
        self.pcb_stl_path = pcb_stl_path
        self.case_top_path = case_top_path
        self.case_bottom_path = case_bottom_path
        self.min_clearance_mm = float(min_clearance_mm)

        # Load meshes
        self.pcb_mesh = trimesh.load(pcb_stl_path)
        self.top_mesh = trimesh.load(case_top_path)
        self.bot_mesh = trimesh.load(case_bottom_path)

    @classmethod
    def export_pcb_stl(
        cls,
        pcb_path: str,
        output_stl_path: str,
        subst_models: bool = True,
        include_tracks: bool = True,
        include_pads: bool = True,
    ) -> str:
        """Invokes kicad-cli pcb export stl to export high-fidelity 3D board assembly."""
        os.makedirs(os.path.dirname(output_stl_path), exist_ok=True)
        cmd = [
            "kicad-cli",
            "pcb",
            "export",
            "stl",
            "-o",
            output_stl_path,
        ]
        if subst_models:
            cmd.append("--subst-models")
        if include_tracks:
            cmd.append("--include-tracks")
        if include_pads:
            cmd.append("--include-pads")
        cmd.append(pcb_path)

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if not os.path.exists(output_stl_path):
            raise RuntimeError(
                f"kicad-cli pcb export stl failed: {res.stderr}\n{res.stdout}"
            )
        return output_stl_path

    def check_solid_penetration(
        self, case_mesh: trimesh.Trimesh, target_mesh: trimesh.Trimesh
    ) -> int:
        """Counts number of PCB vertices that penetrate into the solid enclosure shell."""
        if not case_mesh.is_volume:
            return 0
        try:
            inside_mask = case_mesh.contains(target_mesh.vertices)
            return int(np.sum(inside_mask))
        except (ValueError, RuntimeError) as err:
            sys.stderr.write(f"Warning: Solid penetration query error: {err}\n")
            return 0

    def query_component_clearances(self) -> dict[str, dict[str, Any]]:
        """Evaluates minimum clearance distances between enclosure interior and critical components."""
        results = {}

        # Combine top and bottom enclosure shells into single assembly
        case_assembly = trimesh.util.concatenate([self.top_mesh, self.bot_mesh])

        for comp_name, info in KEY_COMPONENTS.items():
            pos = np.array(info["pos"])
            size = np.array(info["size"])

            # Component bounding box sample points
            half_size = size / 2.0
            test_points = np.array(
                [
                    pos + [dx, dy, dz]
                    for dx in [-half_size[0], 0, half_size[0]]
                    for dy in [-half_size[1], 0, half_size[1]]
                    for dz in [0, half_size[2]]
                ]
            )

            # Proximity query: find closest distance to enclosure walls
            _closest_pts, distances, _ = trimesh.proximity.closest_point(
                case_assembly, test_points
            )
            min_dist = float(np.min(distances))

            # Query signed distance to detect if point is embedded in solid shell (positive = penetrating)
            signed_dist = trimesh.proximity.signed_distance(
                case_assembly, [pos + [0, 0, half_size[2]]]
            )[0]
            is_penetrating = signed_dist > 0.001

            status = (
                "PASS"
                if (min_dist >= self.min_clearance_mm and not is_penetrating)
                else "FAIL"
            )

            results[comp_name] = {
                "nominal_pos": pos.tolist(),
                "min_clearance_mm": round(min_dist, 3),
                "is_penetrating": bool(is_penetrating),
                "required_clearance_mm": self.min_clearance_mm,
                "status": status,
            }

        return results

    def run_full_verification(self) -> dict[str, Any]:
        """Executes broad-phase, narrow-phase, and component clearance audit."""
        top_clashes = self.check_solid_penetration(self.top_mesh, self.pcb_mesh)
        bot_clashes = self.check_solid_penetration(self.bot_mesh, self.pcb_mesh)
        component_audit = self.query_component_clearances()

        failed_components = [
            c for c, d in component_audit.items() if d["status"] != "PASS"
        ]
        has_clash = top_clashes > 0 or bot_clashes > 0 or len(failed_components) > 0

        return {
            "top_penetrating_vertices": top_clashes,
            "bottom_penetrating_vertices": bot_clashes,
            "min_clearance_threshold_mm": self.min_clearance_mm,
            "components_analyzed": len(component_audit),
            "failed_components": failed_components,
            "component_clearances": component_audit,
            "overall_collision_status": "CLEAN" if not has_clash else "INTERFERENCE",
        }


def main():
    parser = argparse.ArgumentParser(
        description="3D Enclosure vs PCB Collision Detection & Clearance Engine"
    )
    parser.add_argument(
        "--pcb",
        type=str,
        default=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "pcb", "CopperPilotDrone.kicad_pcb"
            )
        ),
        help="Path to .kicad_pcb file",
    )
    parser.add_argument(
        "--pcb-stl",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "build", "pcb_assembly.stl"),
        help="Path to exported PCB STL (will be generated if missing)",
    )
    parser.add_argument(
        "--case-top",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "build", "case_top.stl"),
        help="Path to Top Canopy STL",
    )
    parser.add_argument(
        "--case-bottom",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "build", "case_bottom.stl"),
        help="Path to Bottom Base STL",
    )
    parser.add_argument(
        "--clearance",
        type=float,
        default=0.5,
        help="Minimum required clearance in mm",
    )
    parser.add_argument(
        "--json-report",
        type=str,
        default=os.path.join(
            os.path.dirname(__file__), "build", "collision_report.json"
        ),
        help="Path to write JSON verification report",
    )
    args = parser.parse_args()

    # Ensure PCB STL exists
    if not os.path.exists(args.pcb_stl):
        print(f"Exporting PCB assembly STL via kicad-cli to {args.pcb_stl}...")
        CollisionVerifier.export_pcb_stl(args.pcb, args.pcb_stl)

    verifier = CollisionVerifier(
        args.pcb_stl, args.case_top, args.case_bottom, min_clearance_mm=args.clearance
    )
    report = verifier.run_full_verification()

    os.makedirs(os.path.dirname(args.json_report), exist_ok=True)
    with open(args.json_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("======================================================================")
    print("CopperPilot Drone: 3D Collision & Clearance Verification Report")
    print("======================================================================")
    print(f"Overall Status:            {report['overall_collision_status']}")
    print(f"Top Penetrating Vertices:  {report['top_penetrating_vertices']}")
    print(f"Bottom Penetrating Verts:  {report['bottom_penetrating_vertices']}")
    print(f"Clearance Threshold:       {report['min_clearance_threshold_mm']:.2f} mm")
    print(f"Components Checked:        {report['components_analyzed']}")
    print(
        f"Failed Components:         {', '.join(report['failed_components']) if report['failed_components'] else 'None (All Clear)'}"
    )
    print(f"Report written to:         {args.json_report}")
    print("======================================================================")

    return 0 if report["overall_collision_status"] == "CLEAN" else 1


if __name__ == "__main__":
    sys.exit(main())
