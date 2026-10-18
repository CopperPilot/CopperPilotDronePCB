"""Parametric 3D Squircle Enclosure Generator for CopperPilot Drone Flight Controller.

Generates an aerodynamic clip-on squircle canopy and matching base chassis
from KiCad PCB physical constraints using CadQuery and Trimesh.
Features under-PCB cantilever snap hooks, precise component cutouts,
and debossed 'CopperPilot.ai' branding in Inter Bold font.
"""

import json
import os
import tempfile
from typing import Any

import cadquery as cq
import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image

from pcb_parser import KiCadPCBParser

# Default path to KiCad PCB file
DEFAULT_PCB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "pcb", "CopperPilotDrone.kicad_pcb")
)

# PCB and Fuselage Geometry Constants
PCB_THICKNESS = 1.6  # mm
PCB_CENTER_X = 130.58  # mm (KiCad fuselage alignment center)
PCB_CENTER_Y = -89.50  # mm (Exported 3D coordinates: y_3d = -y_kicad)

FUSELAGE_WIDTH = 48.0  # mm (X span: ~106.5 to ~154.5)
FUSELAGE_LENGTH = 54.0  # mm (Y span: ~-116.5 to ~-62.5)
TOTAL_ARM_SPAN = 104.0  # mm (Diagonal motor corner span)

# Key Component Positions in 3D Coordinates (X, Y_3D = -Y_pcb, Z_base)
KEY_COMPONENTS: dict[str, dict[str, Any]] = {
    "J1_USBC": {"pos": [131.57, -68.12, 1.6], "size": [10.0, 5.0, 3.8]},
    "J3_BATT": {"pos": [149.62, -85.54, 1.6], "size": [8.0, 6.5, 6.0]},
    "SW1_POWER": {"pos": [121.15, -66.15, 1.6], "size": [4.0, 3.0, 3.5]},
    "SW2_RESET": {"pos": [114.00, -82.70, 1.6], "size": [3.0, 3.0, 2.0]},
    "SW3_BOOT": {"pos": [114.00, -88.50, 1.6], "size": [3.0, 3.0, 2.0]},
    "U8_ESP32": {"pos": [130.93, -102.09, 1.6], "size": [18.0, 25.5, 3.2]},
    "U9_MPU6050": {"pos": [130.96, -83.94, 1.6], "size": [4.0, 4.0, 1.0]},
    "LED1_POW": {"pos": [144.76, -64.89, 1.6], "size": [2.0, 2.0, 1.0]},
    "LED2_CHG": {"pos": [138.54, -64.90, 1.6], "size": [2.0, 2.0, 1.0]},
    "LED3_CHG": {"pos": [138.55, -66.51, 1.6], "size": [2.0, 2.0, 1.0]},
    "J2_MTR": {"pos": [113.07, -104.15, 1.6], "size": [6.0, 6.0, 4.0]},
    "J4_MTR": {"pos": [148.89, -104.05, 1.6], "size": [6.0, 6.0, 4.0]},
    "J5_MTR": {"pos": [113.06, -68.86, 1.6], "size": [6.0, 6.0, 4.0]},
    "J6_MTR": {"pos": [148.74, -68.80, 1.6], "size": [6.0, 6.0, 4.0]},
}


class EnclosureConfig:
    """Design and manufacturing configuration parameters for enclosure generation."""

    def __init__(
        self,
        wall_thickness: float = 1.4,
        pcb_clearance: float = 0.3,
        component_clearance: float = 0.6,
        snap_engagement: float = 0.5,
        nozzle_diameter: float = 0.4,
        material: str = "petg",
        cutouts: list[str] | None = None,
    ):
        self.wall_thickness = float(wall_thickness)
        self.pcb_clearance = float(pcb_clearance)
        self.component_clearance = float(component_clearance)
        self.snap_engagement = float(snap_engagement)
        self.nozzle_diameter = float(nozzle_diameter)
        self.material = material.lower()
        self.cutouts = cutouts or ["all"]

        # Material densities in g/cm3
        self.densities = {
            "pla": 1.24,
            "petg": 1.27,
            "abs": 1.04,
            "nylon": 1.14,
        }
        self.density = self.densities.get(self.material, 1.27)

    @classmethod
    def from_json(cls, json_path: str) -> "EnclosureConfig":
        """Load configuration options from JSON file."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)


def _make_squircle_points(
    a: float, b: float, n: float, num_pts: int = 64
) -> list[tuple[float, float]]:
    """Evaluate discrete points along a Lamé superellipse: |x/a|^n + |y/b|^n = 1."""
    theta = np.linspace(0, 2 * np.pi, num_pts, endpoint=False)
    pts = []
    for th in theta:
        c = np.cos(th)
        s = np.sin(th)
        x = a * np.sign(c) * (np.abs(c) ** (2.0 / n))
        y = b * np.sign(s) * (np.abs(s) ** (2.0 / n))
        pts.append((float(x), float(y)))
    return pts


def create_top_canopy(
    config: EnclosureConfig, pcb_path: str = DEFAULT_PCB_PATH
) -> trimesh.Trimesh:
    """Generate the clip-on squircle canopy with cutouts, snap hooks, and debossed branding.

    Args:
        config: Manufacturing and dimensional parameters.
        pcb_path: Path to the KiCad PCB file.

    Returns:
        Watertight 2-manifold Trimesh object of the top canopy.
    """
    # Parse actual PCB geometry to verify dimensions and waist landing zones
    if os.path.exists(pcb_path):
        parser = KiCadPCBParser(pcb_path)
        fuselage = parser.fuselage
        cx = fuselage.center_3d[0]
        # Fuselage center along Y is shifted slightly to enclose ESP32 module & antenna
        cy = PCB_CENTER_Y
    else:
        cx = PCB_CENTER_X
        cy = PCB_CENTER_Y

    z_base = 0.5  # Skirt lands below PCB top surface (1.6mm)
    h_total = 10.8  # External height: crown reaches Z = 11.3 mm
    wall = config.wall_thickness

    # Squircle semi-axes (matching 50-56 mm width and 54-60 mm length bounds)
    a0 = 26.2  # Base width = 52.4 mm
    b0 = 28.2  # Base length = 56.4 mm
    a2 = 22.5  # Crown width = 45.0 mm
    b2 = 26.2  # Crown length = 52.4 mm (covers North LED1 and South ESP32)

    # Outer aerodynamic squircle loft
    pts_out0 = _make_squircle_points(a0, b0, 4.0)
    pts_out1 = _make_squircle_points(a0 - 1.0, b0 - 0.8, 3.8)
    pts_out2 = _make_squircle_points(a2, b2, 3.5)

    outer_loft = (
        cq.Workplane("XY")
        .workplane(offset=z_base)
        .spline(pts_out0)
        .close()
        .workplane(offset=6.0)
        .spline(pts_out1)
        .close()
        .workplane(offset=h_total - 6.0)
        .spline(pts_out2)
        .close()
        .loft(combine=True)
    )

    # Inner cavity squircle loft (subtracted to produce uniform shell)
    pts_in0 = _make_squircle_points(a0 - wall, b0 - wall, 4.0)
    pts_in1 = _make_squircle_points(a0 - 1.0 - wall, b0 - 0.8 - wall, 3.8)
    pts_in2 = _make_squircle_points(a2 - wall, b2 - wall, 3.5)

    inner_loft = (
        cq.Workplane("XY")
        .workplane(offset=z_base - 0.2)
        .spline(pts_in0)
        .close()
        .workplane(offset=6.0 + 0.2)
        .spline(pts_in1)
        .close()
        .workplane(offset=h_total - 6.0 - wall + 0.1)
        .spline(pts_in2)
        .close()
        .loft(combine=True)
    )

    canopy = outer_loft.cut(inner_loft).translate((cx, cy, 0))

    # 1. USB-C Receptacle Port Cutout (J1, North Wall)
    usbc_cut = cq.Workplane("XY").box(10.2, 8.0, 4.4).translate((131.57, -64.5, 3.5))
    canopy = canopy.cut(usbc_cut)

    # 2. Power Slide Switch Slot (SW1, North Wall)
    sw_cut = cq.Workplane("XY").box(5.5, 8.0, 3.5).translate((121.15, -64.5, 3.0))
    canopy = canopy.cut(sw_cut)

    # 3. 1S LiPo Battery JST-PH Connector Slot (J3, East Wall)
    batt_cut = cq.Workplane("XY").box(9.5, 10.0, 8.0).translate((153.0, -85.54, 5.0))
    canopy = canopy.cut(batt_cut)

    # 4. Status LED Light Pipe Viewports (LED1 Power, LED2 Charge, LED3 Standby)
    for lx, ly in [(144.76, -64.89), (138.54, -64.90), (138.55, -66.51)]:
        led_hole = cq.Workplane("XY").cylinder(14.0, 1.0).translate((lx, ly, 8.0))
        canopy = canopy.cut(led_hole)

    # 5. Tactile Reset and Boot Button Pinholes (SW2 RESET, SW3 BOOT)
    for bx, by in [(114.00, -82.70), (114.00, -88.50)]:
        btn_hole = cq.Workplane("XY").cylinder(14.0, 1.4).translate((bx, by, 8.0))
        canopy = canopy.cut(btn_hole)

    # 6. Diagonal Motor Arm Relief Cutouts (J5 Front-L, J6 Front-R, J2 Rear-L, J4 Rear-R)
    arm_portals = [
        (113.0, -68.8),
        (148.8, -68.8),
        (113.0, -104.2),
        (148.9, -104.2),
        (114.0, -115.5),
        (147.0, -115.5),
    ]
    for mx, my in arm_portals:
        arm_box = cq.Workplane("XY").box(12.0, 12.0, 8.0).translate((mx, my, 2.5))
        canopy = canopy.cut(arm_box)

    # 7. ESP32-S3 Antenna Dielectric Isolation Window
    ant_window = cq.Workplane("XY").box(22.0, 6.0, 5.0).translate((130.9, -116.0, 2.0))
    canopy = canopy.cut(ant_window)

    # 8. Under-PCB Cantilever Snap Hooks at Waist Break-Away Notches
    # Left hook at X = 108.4 mm (continuous notch Y in [-97.6, -75.4])
    hook_l = cq.Workplane("XY").box(1.2, 4.0, 3.0).translate((106.8, -86.5, 1.0))
    lip_l = cq.Workplane("XY").box(0.45, 4.0, 0.5).translate((107.60, -86.5, -0.3))
    # Right hook at X = 153.4 mm (notch Y in [-99.0, -93.0])
    hook_r = cq.Workplane("XY").box(1.2, 4.0, 3.0).translate((154.4, -95.0, 1.0))
    lip_r = cq.Workplane("XY").box(0.45, 4.0, 0.5).translate((153.60, -95.0, -0.3))
    canopy = canopy.union(hook_l).union(lip_l).union(hook_r).union(lip_r)

    # 9. Debossed Branding Text: 'CopperPilot.ai' Inter Bold
    try:
        canopy = (
            canopy.faces(">Z")
            .workplane()
            .text("CopperPilot.ai", 3.2, -0.4, font="Inter", kind="bold")
        )
    except (ValueError, RuntimeError, TypeError, KeyError):
        # Fallback to sans-serif if Inter font descriptor is unavailable
        canopy = (
            canopy.faces(">Z")
            .workplane()
            .text("CopperPilot.ai", 3.2, -0.4, font="Arial", kind="bold")
        )

    # Export to temp STL and load as Trimesh
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        cq.exporters.export(canopy, tmp_path)
        mesh = trimesh.load(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return mesh


def create_bottom_base(
    config: EnclosureConfig, pcb_path: str = DEFAULT_PCB_PATH
) -> trimesh.Trimesh:
    """Generate the matching bottom base chassis with PCB seating standoffs and battery tray.

    Args:
        config: Manufacturing and dimensional parameters.
        pcb_path: Path to the KiCad PCB file.

    Returns:
        Watertight 2-manifold Trimesh object of the bottom base chassis.
    """
    if os.path.exists(pcb_path):
        parser = KiCadPCBParser(pcb_path)
        cx = parser.fuselage.center_3d[0]
        cy = PCB_CENTER_Y
    else:
        cx = PCB_CENTER_X
        cy = PCB_CENTER_Y

    a0 = 26.2
    b0 = 28.2
    wall = config.wall_thickness

    z_top = 0.0
    h_bot = 6.0

    pts_out0 = _make_squircle_points(a0, b0, 4.0)
    pts_out1 = _make_squircle_points(a0 - 1.5, b0 - 1.5, 3.6)
    pts_out2 = _make_squircle_points(a0 - 3.5, b0 - 3.5, 3.2)

    outer_bot = (
        cq.Workplane("XY")
        .workplane(offset=z_top)
        .spline(pts_out0)
        .close()
        .workplane(offset=-2.5)
        .spline(pts_out1)
        .close()
        .workplane(offset=-(h_bot - 2.5))
        .spline(pts_out2)
        .close()
        .loft(combine=True)
    )

    pts_in0 = _make_squircle_points(a0 - wall, b0 - wall, 4.0)
    pts_in1 = _make_squircle_points(a0 - 1.5 - wall, b0 - 1.5 - wall, 3.6)
    pts_in2 = _make_squircle_points(a0 - 3.5 - wall, b0 - 3.5 - wall, 3.2)

    inner_bot = (
        cq.Workplane("XY")
        .workplane(offset=z_top + 0.1)
        .spline(pts_in0)
        .close()
        .workplane(offset=-2.5 - 0.1)
        .spline(pts_in1)
        .close()
        .workplane(offset=-(h_bot - 2.5 - wall))
        .spline(pts_in2)
        .close()
        .loft(combine=True)
    )

    bot_shell = outer_bot.cut(inner_bot).translate((cx, cy, 0))

    # Corner arm reliefs matching diagonal arms
    for mx, my in [
        (113.0, -68.8),
        (148.8, -68.8),
        (113.0, -104.2),
        (148.9, -104.2),
        (114.0, -115.5),
        (147.0, -115.5),
    ]:
        rel = cq.Workplane("XY").box(12.0, 12.0, 6.0).translate((mx, my, -1.0))
        bot_shell = bot_shell.cut(rel)

    # Battery retention strap slot on bottom floor
    strap = cq.Workplane("XY").box(18.0, 4.5, 4.0).translate((cx, cy + 5.0, -5.5))
    bot_shell = bot_shell.cut(strap)

    # PCB seating standoffs in corners
    for ox, oy in [(-18.0, -18.0), (18.0, -18.0), (-18.0, 18.0), (18.0, 18.0)]:
        standoff = (
            cq.Workplane("XY").cylinder(2.0, 1.5).translate((cx + ox, cy + oy, -1.0))
        )
        bot_shell = bot_shell.union(standoff)

    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        cq.exporters.export(bot_shell, tmp_path)
        mesh = trimesh.load(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return mesh


def render_explosion_animation(
    top_mesh: trimesh.Trimesh,
    bot_mesh: trimesh.Trimesh,
    pcb_mesh: trimesh.Trimesh,
    output_gif_path: str,
    n_frames: int = 16,
) -> str:
    """Render a 3D rotating exploded view animation validating assembly fit.

    Args:
        top_mesh: Upper squircle canopy mesh.
        bot_mesh: Lower base chassis mesh.
        pcb_mesh: Exported 3D PCB assembly mesh.
        output_gif_path: Destination path for the animated GIF.
        n_frames: Number of azimuthal frames in one 360-degree rotation.

    Returns:
        Path to the generated animated GIF.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_gif_path)), exist_ok=True)

    # Subsample faces for rapid render
    top_f = top_mesh.faces[::3]
    bot_f = bot_mesh.faces[::3]
    pcb_f = pcb_mesh.faces[::4]

    frames = []
    for i in range(n_frames):
        fig = plt.figure(figsize=(5, 5), dpi=75)
        ax = fig.add_subplot(111, projection="3d")
        azim_angle = i * (360.0 / n_frames)
        ax.view_init(elev=28, azim=azim_angle)

        # Explosion translation along Z (sine wave pulsation)
        t = np.sin(np.pi * i / (n_frames - 1)) if n_frames > 1 else 0.0
        dz_top = 20.0 * t
        dz_bot = -16.0 * t

        top_faces = top_mesh.vertices[top_f] + [0, 0, dz_top]
        bot_faces = bot_mesh.vertices[bot_f] + [0, 0, dz_bot]
        pcb_faces = pcb_mesh.vertices[pcb_f]

        ax.add_collection3d(
            Poly3DCollection(
                top_faces, facecolors="#1E88E5", edgecolors="none", alpha=0.85
            )
        )
        ax.add_collection3d(
            Poly3DCollection(
                pcb_faces, facecolors="#2E7D32", edgecolors="none", alpha=0.90
            )
        )
        ax.add_collection3d(
            Poly3DCollection(
                bot_faces, facecolors="#546E7A", edgecolors="none", alpha=0.85
            )
        )

        ax.set_xlim([95, 165])
        ax.set_ylim([-125, -55])
        ax.set_zlim([-25, 35])
        ax.set_axis_off()
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

        fig.canvas.draw()
        rgba = np.asarray(fig.canvas.buffer_rgba())
        im = Image.fromarray(rgba)
        frames.append(im)
        plt.close(fig)

    frames[0].save(
        output_gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=150,
        loop=0,
    )
    return output_gif_path


def generate_enclosure_assets(
    output_dir: str,
    config: EnclosureConfig,
    pcb_path: str = DEFAULT_PCB_PATH,
    render_anim: bool = False,
    formats: list[str] | None = None,
) -> tuple[str, str]:
    """Build and export both top canopy and bottom base STLs and visual assets.

    Args:
        output_dir: Directory where assets are written.
        config: Sizing and material parameters.
        pcb_path: Path to the target KiCad PCB.
        render_anim: Whether to render exploded-view animation GIF.
        formats: Target 3D CAD formats (stl, step, 3mf).

    Returns:
        Tuple of (top_stl_path, bot_stl_path).
    """
    os.makedirs(output_dir, exist_ok=True)
    formats = formats or ["stl"]

    top_mesh = create_top_canopy(config, pcb_path)
    bot_mesh = create_bottom_base(config, pcb_path)

    top_stl = os.path.join(output_dir, "case_top.stl")
    bot_stl = os.path.join(output_dir, "case_bottom.stl")

    top_mesh.export(top_stl)
    bot_mesh.export(bot_stl)

    # Optional animation generation
    if render_anim:
        pcb_stl_path = os.path.join(output_dir, "pcb_assembly.stl")
        if not os.path.exists(pcb_stl_path):
            from collision import CollisionVerifier

            CollisionVerifier.export_pcb_stl(pcb_path, pcb_stl_path)
        pcb_mesh = trimesh.load(pcb_stl_path)
        anim_path = os.path.join(output_dir, "explosion_animation.gif")
        render_explosion_animation(top_mesh, bot_mesh, pcb_mesh, anim_path)

    return top_stl, bot_stl
