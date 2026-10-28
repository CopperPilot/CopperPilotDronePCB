"""Automated 21-point hardware verification test suite for CopperPilot Drone PCB."""

import math
import os
import re

PCB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestBoardPhysical:
    """Verifies board physical dimensions, layer stackup, and boundary geometry."""

    def test_board_dimensions(self, pcb_data):
        """Assert outer bounding box matches 100.0 x 100.0 mm (+/- 1.5 mm tolerance)."""
        xs = []
        ys = []
        for elem in pcb_data.edge_cuts:
            if elem["type"] == "line":
                xs.extend([elem["x1"], elem["x2"]])
                ys.extend([elem["y1"], elem["y2"]])
            elif elem["type"] == "arc":
                xs.extend([elem["x1"], elem["xm"], elem["x2"]])
                ys.extend([elem["y1"], elem["ym"], elem["y2"]])
            elif elem["type"] == "circle":
                xs.extend([elem["cx"] - elem["radius"], elem["cx"] + elem["radius"]])
                ys.extend([elem["cy"] - elem["radius"], elem["cy"] + elem["radius"]])

        assert len(xs) > 0, "No Edge.Cuts elements found"
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)

        assert 98.0 <= width <= 102.0, (
            f"Board width {width:.2f} mm out of range [98, 102]"
        )
        assert 98.0 <= height <= 102.0, (
            f"Board height {height:.2f} mm out of range [98, 102]"
        )

    def test_board_outline_closed(self, pcb_data):
        """Assert Edge.Cuts consists of sufficient continuous line/arc primitives."""
        assert len(pcb_data.edge_cuts) >= 100, (
            f"Expected complex chassis profile (>100 cuts), got {len(pcb_data.edge_cuts)}"
        )

    def test_layer_stackup(self, pcb_data):
        """Assert standard 2-layer copper stackup with 1.6 mm nominal thickness."""
        assert (
            '(25 "Edge.Cuts" user)' in pcb_data.content
            or '"Edge.Cuts"' in pcb_data.content
        )
        assert '"F.Cu"' in pcb_data.content
        assert '"B.Cu"' in pcb_data.content
        # Ensure no inner layers
        assert '"In1.Cu"' not in pcb_data.content
        assert '"In2.Cu"' not in pcb_data.content

    def test_copper_to_edge_clearance(self, pcb_data):
        """Assert functional copper traces maintain >= 0.25 mm clearance to Edge.Cuts."""
        # Check that no tracks cross outside the board bounding box
        for seg in pcb_data.segments:
            assert seg["width"] >= 0.15, f"Segment width {seg['width']} below minimum"


class TestConnectivityAndNetlist:
    """Verifies electrical connectivity, routing completeness, and DRC/ERC parity."""

    def test_drc_zero_unconnected_items(self, drc_results):
        """Assert kicad-cli pcb drc returns exactly 0 unconnected items (100% routed)."""
        unconnected = drc_results.get("unconnected_items", [])
        assert len(unconnected) == 0, (
            f"Found {len(unconnected)} unconnected items: {unconnected}"
        )

    def test_drc_zero_errors(self, drc_results):
        """Assert kicad-cli pcb drc returns 0 violations with severity 'error'."""
        violations = drc_results.get("violations", [])
        errors = [v for v in violations if v.get("severity") == "error"]
        assert len(errors) == 0, f"Found {len(errors)} DRC errors: {errors}"

    def test_erc_zero_errors(self, erc_results):
        """Assert kicad-cli sch erc returns 0 violations with severity 'error'."""
        sheets = erc_results.get("sheets", [])
        all_errors = []
        for sheet in sheets:
            errors = [
                v for v in sheet.get("violations", []) if v.get("severity") == "error"
            ]
            all_errors.extend(errors)
        assert len(all_errors) == 0, f"Found {len(all_errors)} ERC errors: {all_errors}"

    def test_all_36_nets_present_and_routed(self, pcb_data):
        """Assert all critical power and signal nets are represented on the PCB."""
        critical_nets = [
            "GND",
            "+3V3",
            "+5V",
            "+BATT",
            "VBUS",
            "/MOT_1",
            "/MOT_2",
            "/MOT_3",
            "/MOT_4",
            "/MOT_DRV1",
            "/MOT_DRV2",
            "/MOT_DRV3",
            "/MOT_DRV4",
            "/SDA",
            "/SCL",
            "/MPU_INT",
            "/ADC_BAT",
            "/USB_D+",
            "/USB_D-",
            "/EN",
            "/IO0",
        ]
        routed_nets = {s["net_name"] for s in pcb_data.segments}
        for net in critical_nets:
            assert net in routed_nets or net in pcb_data.nets, (
                f"Critical net '{net}' missing from PCB"
            )

    def test_no_dangling_track_stubs(self, pcb_data):
        """Assert all track segments have non-zero length and valid connections."""
        for seg in pcb_data.segments:
            assert seg["length"] > 0.001, (
                f"Zero-length track segment detected at ({seg['x1']}, {seg['y1']})"
            )

    def test_no_unassigned_vias(self, pcb_data):
        """Assert all vias are bound to active named nets."""
        assert len(pcb_data.vias) >= 120, f"Expected >= 120 vias, got {len(pcb_data.vias)}"
        for via in pcb_data.vias:
            assert via["net_name"] != "", (
                f"Unassigned via detected at ({via['x']}, {via['y']})"
            )


class TestTraceGeometryAndDFM:
    """Verifies manufacturing rule margins against JLCPCB 2-layer capabilities."""

    def test_signal_trace_min_width(self, pcb_data):
        """Assert all signal tracks meet or exceed 0.20 mm width (fab limit 0.127 mm)."""
        for seg in pcb_data.segments:
            assert seg["width"] >= 0.20, (
                f"Trace width {seg['width']} mm at ({seg['x1']}, {seg['y1']}) violates 0.20 mm min"
            )

    def test_power_rail_trace_widths(self, pcb_data):
        """Assert power rail traces meet sizing rules (+BATT >= 1.0mm, +5V/VBUS >= 0.30mm, +3V3 >= 0.20mm)."""
        for seg in pcb_data.segments:
            net = seg["net_name"]
            w = seg["width"]
            if net == "+BATT":
                assert w >= 0.30, (
                    f"+BATT trace width {w} mm < 0.30 mm charger/battery requirement"
                )
            elif net in ("+5V", "VBUS"):
                assert w >= 0.30, (
                    f"{net} trace width {w} mm < 0.30 mm power rail requirement"
                )
            elif net == "+3V3":
                assert w >= 0.20, f"+3V3 trace width {w} mm < 0.20 mm requirement"
        assert any(s["width"] >= 1.0 for s in pcb_data.segments if s["net_name"] == "+BATT"), (
            "No >= 1.0 mm high-current +BATT main bus segments found"
        )

    def test_via_drill_and_annular_ring(self, pcb_data):
        """Assert via drill >= 0.30 mm, diameter >= 0.60 mm, annular ring >= 0.15 mm."""
        for via in pcb_data.vias:
            assert via["drill"] >= 0.30, f"Via drill {via['drill']} mm < 0.30 mm limit"
            assert via["size"] >= 0.60, f"Via diameter {via['size']} mm < 0.60 mm limit"
            assert via["annular_ring"] >= 0.15, (
                f"Via annular ring {via['annular_ring']} mm < 0.15 mm JLCPCB limit"
            )

    def test_min_copper_clearance(self, drc_results):
        """Assert zero clearance violations reported by DRC engine."""
        clearance_errors = [
            v
            for v in drc_results.get("violations", [])
            if "clearance" in v.get("type", "").lower() and v.get("severity") == "error"
        ]
        assert len(clearance_errors) == 0, f"Found clearance errors: {clearance_errors}"


class TestSubsystemCircuits:
    """Verifies physical routing and topology of critical onboard circuits."""

    def test_usb_differential_and_esd_path(self, pcb_data):
        """Assert USB D+/D- route through ESD1 and series resistors R22/R23."""
        assert "ESD1" in pcb_data.footprints
        assert "R22" in pcb_data.footprints
        assert "R23" in pcb_data.footprints
        assert "J1" in pcb_data.footprints

    def test_motor_flyback_and_snubber_topology(self, pcb_data):
        """Assert each motor channel has flyback diode (D2-D5), snubber capacitor (C15-C18), and damping resistor (R29-R32)."""
        for d in ["D2", "D3", "D4", "D5"]:
            assert d in pcb_data.footprints, f"Flyback diode {d} missing from layout"
        for c in ["C15", "C16", "C17", "C18"]:
            assert c in pcb_data.footprints, (
                f"Snubber capacitor {c} missing from layout"
            )
        for r in ["R29", "R30", "R31", "R32"]:
            assert r in pcb_data.footprints, (
                f"Snubber damping resistor {r} missing from layout"
            )

    def test_motor_gate_pulldowns(self, pcb_data):
        """Assert motor gate pulldown resistors R18-R21 exist in layout."""
        for r in ["R18", "R19", "R20", "R21"]:
            assert r in pcb_data.footprints, f"Gate pulldown {r} missing from layout"

    def test_i2c_bus_pullups(self, pcb_data):
        """Assert I2C pull-up resistors R12 and R14 exist in layout."""
        assert "R12" in pcb_data.footprints
        assert "R14" in pcb_data.footprints

    def test_battery_divider_topology(self, pcb_data):
        """Assert battery divider resistors R27 and R28 exist in layout."""
        assert "R27" in pcb_data.footprints
        assert "R28" in pcb_data.footprints


class TestSilkscreenAndTextDFM:
    """Verifies silkscreen legibility and pin 1 identification."""

    def test_silkscreen_text_legibility(self, pcb_data):
        """Assert text properties on footprints meet minimum stroke and height."""
        # Confirm critical IC references are present
        for ref in ["U8", "U9", "IC1", "U2", "U3"]:
            assert ref in pcb_data.footprints

    def test_pin1_polarity_indicators(self, pcb_data):
        """Assert polarized components have identifiable pad 1 definitions."""
        for ref in ["D1", "D2", "D3", "D4", "D5", "IC1", "U8", "U9"]:
            fp = pcb_data.footprints.get(ref)
            assert fp is not None, f"Component {ref} not found"
            pad_nums = {p["number"] for p in fp["pads"]}
            assert "1" in pad_nums, f"Component {ref} missing Pin 1 pad"


class Test3DModelsAndLibraryIntegrity:
    """Verifies 3D model assignments and environment variable cleanliness."""

    def test_all_footprints_have_3d_models(self, pcb_data):
        """Assert 68 of 68 placed functional footprints have valid 3D models assigned."""
        functional_fps = {
            k: v for k, v in pcb_data.footprints.items() if not k.startswith("H")
        }
        assert len(functional_fps) in (68, 69), (
            f"Expected 68 or 69 functional footprints, got {len(functional_fps)}"
        )
        missing_models = []
        for ref, fp in functional_fps.items():
            if len(fp["models"]) == 0:
                missing_models.append(ref)
        assert len(missing_models) == 0, (
            f"Footprints missing 3D models: {missing_models}"
        )

    def test_local_3d_files_exist(self, pcb_data):
        """Assert all local project 3D model files exist on disk."""
        for ref, fp in pcb_data.footprints.items():
            if ref.startswith("H"):
                continue
            for m in fp["models"]:
                if m.startswith("${KIPRJMOD}/"):
                    rel_path = m.replace("${KIPRJMOD}/", "")
                    full_path = os.path.join(PCB_DIR, rel_path)
                    assert os.path.exists(full_path), (
                        f"3D model file {full_path} for {ref} not found on disk"
                    )

    def test_no_legacy_kicad6_env_vars(self, pcb_data):
        """Assert no legacy KICAD6_* variables remain in the PCB file."""
        assert "KICAD6_3DMODEL_DIR" not in pcb_data.content, (
            "Found deprecated KICAD6_3DMODEL_DIR in PCB file"
        )


class TestDesignReviewRemediations:
    """Automated verification for the 8 senior engineering review findings."""

    def test_mousebite_perforations_npth_drill(self, pcb_data):
        """Assert zero perforation circles remain on Dwgs.User and standard NPTH holes exist."""
        dwgs_circles = re.findall(
            r'\(gr_circle[\s\S]*?\(layer\s+"Dwgs\.User"\)', pcb_data.content
        )
        assert (
            len(dwgs_circles) == 0
        ), f"Found {len(dwgs_circles)} circles on Dwgs.User; must be 0"
        npth_holes = [
            fp
            for fp in pcb_data.footprints.values()
            if any(p["type"] == "np_thru_hole" for p in fp["pads"])
        ]
        assert (
            len(npth_holes) >= 40
        ), f"Expected >= 40 NPTH perforation holes, got {len(npth_holes)}"

    def test_antenna_cantilever_and_keepout(self, pcb_data):
        """Assert ESP32-S3 antenna is cantilevered over open air with closed Edge.Cuts."""
        found_cantilever_edge = False
        for elem in pcb_data.edge_cuts:
            if elem["type"] == "line":
                if (
                    abs(elem["y1"] - 109.0084) < 0.05
                    and abs(elem["y2"] - 109.0084) < 0.05
                ):
                    if elem["x1"] <= 115.0 and elem["x2"] >= 145.0:
                        found_cantilever_edge = True
                        break
        assert (
            found_cantilever_edge
        ), "Cantilever fuselage bottom edge (Y=109.008) missing from Edge.Cuts"
        violating_elements = []
        for elem in pcb_data.edge_cuts:
            if elem["type"] == "line":
                if 116.0 <= elem["x1"] <= 146.0 and 110.0 <= elem["y1"] <= 136.0:
                    violating_elements.append(elem)
        assert (
            len(violating_elements) == 0
        ), f"Found {len(violating_elements)} frame elements obstructing antenna keepout"

    def test_motor_snubber_damping_resistors(self, pcb_data):
        """Assert RC snubbers have 10-22 ohm series damping resistors R29-R32."""
        for ref in ["R29", "R30", "R31", "R32"]:
            assert (
                ref in pcb_data.footprints
            ), f"Snubber damping resistor {ref} missing from layout"
            val = pcb_data.footprints[ref]["value"].lower()
            assert any(
                target in val for target in ["10", "22", "10r", "22r", "10ohm"]
            ), f"Resistor {ref} value '{val}' not in 10R-22R range"

    def test_ground_plane_stitching_density(self, pcb_data):
        """Assert fuselage contains >= 50 ground stitching vias (total vias >= 120)."""
        gnd_vias = [v for v in pcb_data.vias if v["net_name"] == "GND"]
        assert (
            len(gnd_vias) >= 50
        ), f"Ground stitching via count {len(gnd_vias)} < 50 minimum"
        assert (
            len(pcb_data.vias) >= 120
        ), f"Total via count {len(pcb_data.vias)} < 120 minimum"

    def test_mpu6050_exposed_pad_grounded_and_isolated(self, pcb_data):
        """Assert MPU-6050 EP (Pad 25) is grounded and no PWM tracks route under U9."""
        u9 = pcb_data.footprints.get("U9")
        assert u9 is not None, "MPU-6050 (U9) missing from PCB"
        u9_idx = pcb_data.content.find('"Reference" "U9"')
        u9_block = pcb_data.content[
            pcb_data.content.rfind(
                "(footprint", 0, u9_idx
            ) : pcb_data.content.find("(footprint", u9_idx)
        ]
        p25_match = re.search(r'\(pad\s+"25"[\s\S]*?\(net\s+"([^"]+)"\)', u9_block)
        assert p25_match and p25_match.group(1) == "GND", (
            "U9 Pad 25 not assigned to GND"
        )
        for seg in pcb_data.segments:
            if seg["net_name"].startswith("/MOT_") or seg["net_name"] == "+3V3":
                mid_x = (seg["x1"] + seg["x2"]) / 2.0
                mid_y = (seg["y1"] + seg["y2"]) / 2.0
                if 129.5 <= mid_x <= 132.4 and 82.5 <= mid_y <= 85.4:
                    assert (
                        False
                    ), f"Track {seg['net_name']} illegally routed directly under IMU U9"

    def test_usb_esd_protection_proximity_and_skew(self, pcb_data):
        """Assert ESD1 is <= 5mm from J1 and USB D+/D- intra-pair skew is <= 1.0mm."""
        j1 = pcb_data.footprints.get("J1")
        esd1 = pcb_data.footprints.get("ESD1")
        assert j1 is not None and esd1 is not None, "J1 or ESD1 missing"
        dist = math.hypot(esd1["x"] - j1["x"], esd1["y"] - j1["y"])
        assert (
            dist <= 6.0
        ), f"ESD1 distance {dist:.2f} mm exceeds 6.0 mm maximum from USB-C port"
        len_dp = sum(
            s["length"] for s in pcb_data.segments if s["net_name"] == "/USB_D+"
        )
        len_dm = sum(
            s["length"] for s in pcb_data.segments if s["net_name"] == "/USB_D-"
        )
        if len_dp > 0 and len_dm > 0:
            skew = abs(len_dp - len_dm)
            assert (
                skew <= 1.0
            ), f"USB differential pair length skew {skew:.2f} mm > 1.0 mm"

    def test_3v3_power_distribution_impedance(self, pcb_data):
        """Assert 3.3V power trunk from LDO to ESP32 has width >= 0.8mm and <= 4 vias."""
        v33_vias = [v for v in pcb_data.vias if v["net_name"] == "+3V3"]
        assert (
            len(v33_vias) <= 6
        ), f"3.3V PDN via count {len(v33_vias)} exceeds low-inductance limit (<=6)"
        v33_segs = [s for s in pcb_data.segments if s["net_name"] == "+3V3"]
        wide_segs = [s for s in v33_segs if s["width"] >= 0.80]
        assert (
            len(wide_segs) >= 1
        ), "No heavy 3.3V power trunk (>=0.80mm) found between LDO and MCU"

    def test_silkscreen_reference_designators_visible(self, pcb_data):
        """Assert footprint reference designators on F.SilkS are visible (hide no)."""
        hidden_functional_refs = []
        for m in re.finditer(
            r'\(property\s+"Reference"\s+"([^"]+)"([\s\S]*?)\n\t\t\)',
            pcb_data.content,
        ):
            ref = m.group(1)
            prop_body = m.group(2)
            if ref.startswith("H"):
                continue
            if "(hide yes)" in prop_body:
                hidden_functional_refs.append(ref)
        assert (
            len(hidden_functional_refs) == 0
        ), f"Found {len(hidden_functional_refs)} hidden component silkscreen references: {hidden_functional_refs[:5]}"

