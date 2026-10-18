#!/usr/bin/env python3
"""Command Line Interface for CopperPilot Drone Enclosure Generator.

Synthesizes 3D enclosure CAD files (STL, STEP, 3MF) and explosion animation
from KiCad PCB physical constraints.
"""

import argparse
import os
import sys

# Ensure local case module is accessible
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from generator import (
    DEFAULT_PCB_PATH,
    EnclosureConfig,
    generate_enclosure_assets,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="CopperPilot Drone 3D Enclosure Generator CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--pcb",
        type=str,
        default=DEFAULT_PCB_PATH,
        help="Path to input KiCad .kicad_pcb file",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Optional JSON configuration file overriding defaults",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "build"),
        help="Output directory for generated 3D meshes and assets",
    )
    parser.add_argument(
        "--wall-thickness",
        type=float,
        default=1.4,
        help="Nominal enclosure shell wall thickness in mm",
    )
    parser.add_argument(
        "--pcb-clearance",
        type=float,
        default=0.3,
        help="Radial clearance between PCB edge and interior cavity in mm",
    )
    parser.add_argument(
        "--component-clearance",
        type=float,
        default=0.6,
        help="Minimum vertical clearance above top SMT components in mm",
    )
    parser.add_argument(
        "--snap-engagement",
        type=float,
        default=0.5,
        help="Cantilever snap-fit undercut latch depth in mm",
    )
    parser.add_argument(
        "--nozzle-diameter",
        type=float,
        default=0.4,
        help="3D printer nozzle diameter for slicing feature compliance",
    )
    parser.add_argument(
        "--material",
        type=str,
        choices=["pla", "petg", "abs", "nylon"],
        default="petg",
        help="Target 3D printing filament material profile",
    )
    parser.add_argument(
        "--cutouts",
        type=str,
        default="all",
        help="Comma-separated list of cutouts to enable (all, usb, battery, switch, buttons, motors)",
    )
    parser.add_argument(
        "--render-animation",
        action="store_true",
        help="Render multi-frame rotating exploded-view GIF animation",
    )
    parser.add_argument(
        "--format",
        choices=["stl", "step", "3mf", "all"],
        default="all",
        help="Output 3D CAD serialization format",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed diagnostic logging",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all non-error output",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.config and os.path.exists(args.config):
        config = EnclosureConfig.from_json(args.config)
    else:
        cutout_list = (
            [c.strip() for c in args.cutouts.split(",")]
            if args.cutouts != "all"
            else ["all"]
        )
        config = EnclosureConfig(
            wall_thickness=args.wall_thickness,
            pcb_clearance=args.pcb_clearance,
            component_clearance=args.component_clearance,
            snap_engagement=args.snap_engagement,
            nozzle_diameter=args.nozzle_diameter,
            material=args.material,
            cutouts=cutout_list,
        )

    if not args.quiet:
        print("======================================================================")
        print("CopperPilot Drone: Parametric 3D Enclosure Generator")
        print("======================================================================")
        print(f"Target PCB:           {args.pcb}")
        print(f"Output Directory:     {args.output_dir}")
        print(f"Wall Thickness:       {config.wall_thickness:.2f} mm")
        print(f"PCB Edge Clearance:   {config.pcb_clearance:.2f} mm")
        print(f"Component Clearance:  {config.component_clearance:.2f} mm")
        print(f"Snap Latch Depth:     {config.snap_engagement:.2f} mm")
        print(
            f"Target Material:      {config.material.upper()} ({config.density} g/cm3)"
        )
        print("----------------------------------------------------------------------")

    top_stl, bot_stl = generate_enclosure_assets(
        args.output_dir,
        config,
        pcb_path=args.pcb,
        render_anim=args.render_animation,
        formats=[args.format] if args.format != "all" else ["stl", "step", "3mf"],
    )

    if not args.quiet:
        print(f"Generated Top Canopy: {top_stl}")
        print(f"Generated Base Chassis: {bot_stl}")
        if args.render_animation:
            anim_path = os.path.join(args.output_dir, "explosion_animation.gif")
            print(f"Rendered Animation:   {anim_path}")
        print("Enclosure generation completed successfully.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
