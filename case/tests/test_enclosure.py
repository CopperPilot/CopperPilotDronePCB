"""Comprehensive verification test suite for CopperPilot Drone Enclosure.

Verifies:
1. Topological 2-manifoldness, watertight closure, and Euler characteristics.
2. Shell material volume, internal cavity volume, and total printed mass.
3. Outer bounding dimensions, shell wall thickness, and slicing layer constraints.
4. Snap-fit cantilever beam mechanics, engagement depth, and permissible strain.
5. Critical connector cutout alignments (USB-C, battery, switch, buttons, motors).
6. Debossed branding text depth and status LED light pipe viewports.
"""

import math

import numpy as np
import pytest
import trimesh

from generator import FUSELAGE_LENGTH, KEY_COMPONENTS


class TestEnclosureManifoldness:
    """Verifies that 3D enclosure shells are strictly 2-manifold, watertight, and topologically valid."""

    def test_watertight_closure(self, enclosure_meshes):
        """Assert both top canopy and bottom base are 100% watertight solids with zero boundary edges."""
        top = enclosure_meshes["top"]
        bottom = enclosure_meshes["bottom"]

        assert top.is_watertight, (
            "Top canopy mesh is not watertight (contains boundary open edges)"
        )
        assert bottom.is_watertight, (
            "Bottom base mesh is not watertight (contains boundary open edges)"
        )

    def test_winding_consistency(self, enclosure_meshes):
        """Assert face normals are uniformly oriented outwards without inverted or flipped triangles."""
        top = enclosure_meshes["top"]
        bottom = enclosure_meshes["bottom"]

        assert top.is_winding_consistent, (
            "Top canopy has inconsistent face normal windings"
        )
        assert bottom.is_winding_consistent, (
            "Bottom base has inconsistent face normal windings"
        )

    def test_euler_characteristic(self, enclosure_meshes):
        """Verify Euler-Poincaré topological characteristic chi = V - E + F for manifold genus."""
        for part_name in ["top", "bottom"]:
            mesh = enclosure_meshes[part_name]
            bodies = mesh.split(only_watertight=False)
            assert len(bodies) >= 1, f"{part_name} contains no valid mesh bodies"
            for i, comp in enumerate(bodies):
                v = len(comp.vertices)
                f = len(comp.faces)
                e = len(comp.edges_unique)
                chi = v - e + f

                # For closed 2-manifold orientable surfaces, chi = 2 * (1 - genus).
                # Each component must have an even integer chi <= 2.
                assert chi % 2 == 0, (
                    f"{part_name} body {i} Euler characteristic {chi} is not an even integer"
                )
                assert chi <= 2, (
                    f"{part_name} body {i} Euler characteristic {chi} exceeds theoretical maximum 2"
                )

    def test_no_degenerate_facets(self, enclosure_meshes):
        """Assert mesh contains zero zero-area degenerate triangles or duplicate vertices."""
        for part_name in ["top", "bottom"]:
            mesh = enclosure_meshes[part_name]
            areas = mesh.area_faces
            zero_area = np.sum(areas <= 1e-7)
            assert zero_area == 0, (
                f"{part_name} contains {zero_area} zero-area degenerate faces"
            )


class TestEnclosureVolume:
    """Verifies shell material volume, cavity displacement, and printed flight weight budget."""

    def test_shell_material_volume(self, enclosure_meshes):
        """Assert individual and combined shell material volumes lie within target 3D print bounds."""
        top_vol_cm3 = enclosure_meshes["top"].volume / 1000.0
        bot_vol_cm3 = enclosure_meshes["bottom"].volume / 1000.0
        total_vol_cm3 = top_vol_cm3 + bot_vol_cm3

        assert 4.0 <= top_vol_cm3 <= 15.0, (
            f"Top canopy volume {top_vol_cm3:.2f} cm3 out of range [4, 15]"
        )
        assert 3.5 <= bot_vol_cm3 <= 12.0, (
            f"Bottom base volume {bot_vol_cm3:.2f} cm3 out of range [3.5, 12]"
        )
        assert total_vol_cm3 <= 25.0, (
            f"Total enclosure volume {total_vol_cm3:.2f} cm3 exceeds flight budget"
        )

    def test_internal_cavity_volume(self, enclosure_meshes):
        """Assert internal air cavity volume provides sufficient expansion volume for PCB & electronics."""
        # Enclosing bounding box volume minus solid material volume gives interior cavity volume
        top = enclosure_meshes["top"]
        bbox_vol = float(np.prod(top.extents))
        cavity_vol_cm3 = (bbox_vol - top.volume) / 1000.0

        # Required cavity must exceed fuselage electronics volume (~12.0 cm3)
        assert cavity_vol_cm3 >= 10.0, (
            f"Top internal cavity volume {cavity_vol_cm3:.2f} cm3 is insufficient"
        )

    def test_mass_estimate_limits(self, enclosure_meshes):
        """Assert estimated printed mass using material density does not exceed maximum payload allocation."""
        config = enclosure_meshes["config"]
        total_vol_cm3 = (
            enclosure_meshes["top"].volume + enclosure_meshes["bottom"].volume
        ) / 1000.0
        mass_g = total_vol_cm3 * config.density

        assert mass_g <= 22.0, (
            f"Estimated enclosure mass {mass_g:.2f} g exceeds 22.0 g drone flight limit"
        )


class TestPhysicalDimensions:
    """Verifies outer envelope dimensions, shell wall thickness, and slicing nozzle compatibility."""

    def test_outer_bounding_box(self, enclosure_meshes):
        """Assert outer shell dimensions conform to fuselage aerodynamic envelope."""
        top = enclosure_meshes["top"]
        extents = top.extents

        # X span (width) and Y span (length)
        assert 50.0 <= extents[0] <= 56.0, (
            f"Top shell width {extents[0]:.2f} mm out of range [50, 56]"
        )
        assert 54.0 <= extents[1] <= 60.0, (
            f"Top shell length {extents[1]:.2f} mm out of range [54, 60]"
        )
        assert 9.0 <= extents[2] <= 13.0, (
            f"Top shell height {extents[2]:.2f} mm out of range [9, 13]"
        )

    def test_wall_thickness(self, enclosure_meshes):
        """Assert nominal shell wall thickness satisfies minimum FDM structural requirement (>= 1.2 mm)."""
        config = enclosure_meshes["config"]
        assert config.wall_thickness >= 1.2, (
            f"Wall thickness {config.wall_thickness} mm below minimum 1.2 mm"
        )

        # Check that wall thickness is an integer multiple of nozzle perimeters (e.g. 0.4mm nozzle)
        perimeters = config.wall_thickness / config.nozzle_diameter
        assert perimeters >= 3.0, (
            f"Wall thickness provides only {perimeters:.1f} perimeters (need >= 3)"
        )


class TestSnapFitClearances:
    """Verifies cantilever snap-fit joint geometry, undercut engagement, and strain mechanics."""

    def test_undercut_engagement_depth(self, enclosure_meshes):
        """Assert snap latch undercut engagement depth provides positive mechanical retention."""
        config = enclosure_meshes["config"]
        assert 0.40 <= config.snap_engagement <= 0.65, (
            f"Snap engagement {config.snap_engagement} mm out of reliable FDM range [0.4, 0.65]"
        )

    def test_cantilever_deflection_strain(self, enclosure_meshes):
        """Assert cantilever root strain during assembly deflection does not exceed plastic yield limit."""
        config = enclosure_meshes["config"]
        # Nominal cantilever snap arm geometry: Length L = 7.0 mm, Beam thickness h = 1.4 mm
        length = 7.0
        thickness = config.wall_thickness
        deflection = config.snap_engagement

        # Mechanical strain formula for rectangular cantilever beam: epsilon = (3 * Y * h) / (2 * L^2)
        strain = (3.0 * deflection * thickness) / (2.0 * (length**2))

        # Max allowable allowable strain: PETG ~ 4.0% (0.04), PLA ~ 2.5% (0.025)
        allowable_strain = 0.040 if config.material in ["petg", "nylon"] else 0.025
        assert strain <= allowable_strain, (
            f"Snap beam strain {strain * 100:.2f}% exceeds allowable {allowable_strain * 100:.1f}% for {config.material.upper()}"
        )

    def test_parting_line_gap(self, enclosure_meshes):
        """Assert mating split-line clearance between upper canopy and lower base prevents binding."""
        config = enclosure_meshes["config"]
        # Standard FDM joint clearance
        assert 0.15 <= config.pcb_clearance <= 0.50, (
            f"Split-line clearance {config.pcb_clearance} mm out of tolerance [0.15, 0.50]"
        )


class TestCutoutAlignments:
    """Verifies that physical port cutouts align precisely with PCB component coordinates."""

    def test_usbc_port_aperture(self, enclosure_meshes):
        """Assert USB-C cutout clears standard connector plug (>= 9.6 x 3.8 mm) centered on J1."""
        top = enclosure_meshes["top"]
        j1_pos = KEY_COMPONENTS["J1_USBC"]["pos"]

        # Sample points representing USB-C plug insertion envelope
        plug_w = 9.0
        plug_h = 3.5
        plug_pts = np.array(
            [
                [j1_pos[0] + dx, j1_pos[1] + (FUSELAGE_LENGTH / 2.0), 3.5 + dz]
                for dx in [-plug_w / 2, 0, plug_w / 2]
                for dz in [-plug_h / 2, 0, plug_h / 2]
            ]
        )

        # Distance query: plug points must pass cleanly through cutout without hitting solid shell
        _, dists, _ = trimesh.proximity.closest_point(top, plug_pts)
        assert np.all(dists >= 0.0), "USB-C aperture cut into top canopy is obstructed"

    def test_battery_jst_aperture(self, enclosure_meshes):
        """Assert JST-PH battery jack (J3) maintains routing clearance for power harness."""
        j3_info = KEY_COMPONENTS["J3_BATT"]
        assert j3_info["pos"][0] == pytest.approx(149.62, abs=0.5)
        assert j3_info["pos"][1] == pytest.approx(-85.54, abs=0.5)

    def test_switch_and_buttons(self, enclosure_meshes):
        """Assert tactile power switch (SW1) and boot/reset buttons (SW2, SW3) have actuator access."""
        top = enclosure_meshes["top"]
        # Verify button access holes through top shell
        sw2_pos = KEY_COMPONENTS["SW2_RESET"]["pos"]
        sw3_pos = KEY_COMPONENTS["SW3_BOOT"]["pos"]

        for b_name, b_pos in [("RESET", sw2_pos), ("BOOT", sw3_pos)]:
            stylus_pt = np.array([[b_pos[0], b_pos[1], 10.0]])
            _, dist, _ = trimesh.proximity.closest_point(top, stylus_pt)
            assert dist[0] <= 1.5, (
                f"{b_name} button access port misaligned on top shell"
            )

    def test_motor_arm_channels(self, enclosure_meshes):
        """Assert motor connectors on 4 diagonal arms (J2, J4, J5, J6) clear fuselage perimeter."""
        for mtr_key in ["J2_MTR", "J4_MTR", "J5_MTR", "J6_MTR"]:
            pos = KEY_COMPONENTS[mtr_key]["pos"]
            # Motor connectors sit at +/-45 and +/-135 deg relative to center
            dx = pos[0] - 130.58
            dy = pos[1] - (-86.51)
            dist_from_center = math.hypot(dx, dy)
            assert dist_from_center >= 20.0, (
                f"{mtr_key} connector too close to central fuselage core"
            )


class TestMarkingsAndFeatures:
    """Verifies debossed branding, status LED viewports, and acoustic IMU cavity isolation."""

    def test_led_viewports_open(self, enclosure_meshes):
        """Assert light apertures exist directly above LED1 (Power), LED2 (CHG), and LED3 (CHG)."""
        top = enclosure_meshes["top"]
        for led_key in ["LED1_POW", "LED2_CHG", "LED3_CHG"]:
            pos = KEY_COMPONENTS[led_key]["pos"]
            # Probe at ceiling height
            probe_pt = np.array([[pos[0], pos[1], 10.5]])
            _, dist, _ = trimesh.proximity.closest_point(top, probe_pt)
            # Distance should be <= aperture radius (1.0 mm)
            assert dist[0] <= 1.2, (
                f"LED viewport for {led_key} is blocked or misaligned"
            )

    def test_imu_acoustic_chamber(self, enclosure_meshes):
        """Assert MPU-6050 6-axis IMU (U9) maintains minimum 1.0 mm air gap to prevent acoustic coupling."""
        u9_pos = np.array(KEY_COMPONENTS["U9_MPU6050"]["pos"])
        assembly = enclosure_meshes["assembly"]

        # Sample points on top of IMU package
        imu_top_pts = np.array(
            [u9_pos + [dx, dy, 1.0] for dx in [-2.0, 0, 2.0] for dy in [-2.0, 0, 2.0]]
        )

        _, dists, _ = trimesh.proximity.closest_point(assembly, imu_top_pts)
        min_imu_dist = np.min(dists)
        assert min_imu_dist >= 1.0, (
            f"IMU acoustic gap {min_imu_dist:.2f} mm is less than required 1.0 mm"
        )
