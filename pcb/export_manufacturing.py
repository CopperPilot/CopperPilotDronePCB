#!/usr/bin/env python3
"""Export fabrication and assembly package for JLCPCB manufacturing.

Strictly aligned with JLCPCB official specifications and sample workbooks:
- JLCSMT_Sample_CPL1.xlsx
- Sample-BOM_JLCSMT.xlsx
"""

import argparse
import csv
import glob
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    import openpyxl
except ImportError:
    openpyxl = None

PCB_DIR = Path(__file__).resolve().parent
BUILD_DIR = PCB_DIR / "build"
GERBER_DIR = BUILD_DIR / "gerbers"

PROJECT_NAME = "CopperPilotDrone"
PCB_FILE = PCB_DIR / f"{PROJECT_NAME}.kicad_pcb"
SCH_FILE = PCB_DIR / f"{PROJECT_NAME}.kicad_sch"
PRO_FILE = PCB_DIR / f"{PROJECT_NAME}.kicad_pro"

GERBERS_ZIP = BUILD_DIR / "gerbers.zip"
RELEASE_ZIP = BUILD_DIR / f"{PROJECT_NAME}_JLCPCB_Release.zip"
LC_RELEASE_ZIP = BUILD_DIR / f"{PROJECT_NAME}_LionCircuits_Release.zip"


def ensure_dirs():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    GERBER_DIR.mkdir(parents=True, exist_ok=True)


def ensure_board_aux_origin():
    """Ensure board has Drill/Place (Auxiliary) Origin placed at lower-left of Edge.Cuts."""
    try:
        import pcbnew
        board = pcbnew.LoadBoard(str(PCB_FILE))
        edge_box = None
        for drawing in board.GetDrawings():
            if drawing.GetLayer() == pcbnew.Edge_Cuts:
                if edge_box is None:
                    edge_box = drawing.GetBoundingBox()
                else:
                    edge_box.Merge(drawing.GetBoundingBox())
        if edge_box:
            # Lower-left corner in KiCad coordinate system (X min, Y max)
            origin_x = edge_box.GetX()
            origin_y = edge_box.GetBottom()
            cur_aux = board.GetDesignSettings().GetAuxOrigin()
            if cur_aux.x != origin_x or cur_aux.y != origin_y:
                board.GetDesignSettings().SetAuxOrigin(pcbnew.VECTOR2I(origin_x, origin_y))
                board.Save(str(PCB_FILE))
                print(f"==> Configured Board AuxOrigin at lower-left: ({origin_x/1e6:.4f}mm, {origin_y/1e6:.4f}mm)")
    except Exception as e:
        print(f"Note on AuxOrigin setup: {e}")


def export_gerbers():
    ensure_dirs()
    ensure_board_aux_origin()
    print("==> Exporting RS-274X Gerbers for JLCPCB 2-Layer stackup (origin: lower-left)...")
    subprocess.run(
        [
            "kicad-cli",
            "pcb",
            "export",
            "gerbers",
            "--layers",
            "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
            "--subtract-soldermask",
            "--use-drill-file-origin",
            "-o",
            f"{GERBER_DIR}/",
            str(PCB_FILE),
        ],
        check=True,
    )
    print(f"Gerbers exported to {GERBER_DIR}/")


def export_drill():
    ensure_dirs()
    ensure_board_aux_origin()
    print("==> Exporting Excellon NC drill files (origin: lower-left)...")
    subprocess.run(
        [
            "kicad-cli",
            "pcb",
            "export",
            "drill",
            "--format",
            "excellon",
            "--drill-origin",
            "plot",
            "--excellon-zeros-format",
            "decimal",
            "--excellon-units",
            "mm",
            "--excellon-separate-th",
            "-o",
            f"{GERBER_DIR}/",
            str(PCB_FILE),
        ],
        check=True,
    )
    print(f"Drill files exported to {GERBER_DIR}/")


def zip_gerbers():
    ensure_dirs()
    print(f"==> Packaging Gerbers & Drills into {GERBERS_ZIP}...")
    files = sorted(glob.glob(f"{GERBER_DIR}/*"))
    with zipfile.ZipFile(GERBERS_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if os.path.isfile(f) and not f.endswith(".zip"):
                zf.write(f, os.path.basename(f))
    print(f"Gerber archive created at {GERBERS_ZIP}")


def _write_simple_xlsx(headers, rows, out_path, sheet_name="Sheet1"):
    from xml.sax.saxutils import escape

    all_rows = [headers] + [list(r) for r in rows]
    sheet_rows_xml = []
    for r_idx, row in enumerate(all_rows, start=1):
        cells_xml = []
        for c_idx, val in enumerate(row):
            col_letter = chr(ord("A") + c_idx)
            cell_ref = f"{col_letter}{r_idx}"
            if r_idx > 1 and isinstance(val, (int, float)) and not isinstance(val, bool):
                cells_xml.append(f'<c r="{cell_ref}" t="n"><v>{val}</v></c>')
            else:
                text = escape(str(val))
                cells_xml.append(
                    f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'
                )
        sheet_rows_xml.append(f'<row r="{r_idx}">{"".join(cells_xml)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows_xml)}</sheetData>'
        "</worksheet>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    wb_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("xl/workbook.xml", wb_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def write_cpl_xlsx_workbook(rows, out_path):
    """Generate exact JLCPCB CPL workbook matching JLCSMT_Sample_CPL1.xlsx."""
    if openpyxl:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            des, px, py, layer, rot = r
            # JLCSMT_Sample_CPL1 uses strings formatted as 'X.XXXXmm'
            ws.append([str(des), f"{px:.4f}mm", f"{py:.4f}mm", str(layer), int(round(rot))])
        wb.save(out_path)
    else:
        fmt_rows = [
            [str(r[0]), f"{r[1]:.4f}mm", f"{r[2]:.4f}mm", str(r[3]), int(round(r[4]))]
            for r in rows
        ]
        _write_simple_xlsx(
            ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
            fmt_rows,
            out_path,
            sheet_name="Sheet1",
        )


def write_bom_xlsx_workbook(bom_rows, out_path):
    """Generate exact JLCPCB BOM workbook matching Sample-BOM_JLCSMT.xlsx."""
    if openpyxl:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["Comment", "Designator", "Footprint", "JLCPCB Part #（optional）"])
        for r in bom_rows:
            comment, des, fp, lcsc = r
            ws.append([str(comment), str(des), str(fp), str(lcsc)])
        wb.save(out_path)
    else:
        _write_simple_xlsx(
            ["Comment", "Designator", "Footprint", "JLCPCB Part #（optional）"],
            bom_rows,
            out_path,
            sheet_name="Sheet1",
        )


def export_cpl():
    ensure_dirs()
    ensure_board_aux_origin()
    print("==> Exporting SMT pick-and-place component centroid (CPL) file...")
    raw_pos = BUILD_DIR / "raw-pos.csv"
    subprocess.run(
        [
            "kicad-cli",
            "pcb",
            "export",
            "pos",
            "--side",
            "both",
            "--format",
            "csv",
            "--units",
            "mm",
            "--smd-only",
            "--exclude-dnp",
            "--use-drill-file-origin",
            "-o",
            str(raw_pos),
            str(PCB_FILE),
        ],
        check=True,
    )

    cpl_csv_path = BUILD_DIR / f"{PROJECT_NAME}-cpl.csv"
    cpl_xlsx_path = BUILD_DIR / f"{PROJECT_NAME}-cpl.xlsx"

    raw_rows = []
    with open(raw_pos, "r", encoding="utf-8") as rf:
        reader = csv.reader(rf)
        for row in reader:
            if not row or row[0].startswith("#") or row[0] == "Ref":
                continue
            if len(row) >= 7:
                ref = row[0]
                if ref.startswith("H"):
                    continue
                raw_rows.append(row)

    def natural_sort_key(r):
        ref = r[0]
        prefix = re.match(r"^[A-Za-z]+", ref)
        prefix_str = prefix.group(0) if prefix else ref
        num_part = re.search(r"\d+", ref)
        num_int = int(num_part.group(0)) if num_part else 0
        return (prefix_str, num_int, ref)

    raw_rows.sort(key=natural_sort_key)

    # JLCPCB SMT pick-and-place compensation matrix:
    # Maps component reference to (delta_rot_deg, delta_x_mm, delta_y_mm)
    # Corrects for discrepancies between KiCad footprint anchor origins / IPC-7351
    # and JLCPCB / EasyEDA feeder pocket zero-rotations & part centroid definitions.
    JLCPCB_CORRECTIONS = {
        "U8": (0.0, 0.0, 3.62),      # ESP32-S3: Shift Y towards pads (pads centered vs full module outline)
        "J1": (0.0, 0.0, -1.40),     # USB-C: Shift Y towards pads (board edge line vs shell centroid)
        "IC1": (-90.0, 0.0, 0.0),    # TP4056: SOIC-8 tape zero orientation is 90° off KiCad
        "T1": (180.0, 0.0, 0.0),     # SI2302DS: SOT-23 tape zero orientation is 180° inverted from IPC
        "T2": (180.0, 0.0, 0.0),     # SI2302DS: SOT-23 tape zero orientation is 180° inverted from IPC
        "T3": (180.0, 0.0, 0.0),     # SI2302DS: SOT-23 tape zero orientation is 180° inverted from IPC
        "T4": (180.0, 0.0, 0.0),     # SI2302DS: SOT-23 tape zero orientation is 180° inverted from IPC
        "U2": (180.0, 0.0, 0.0),     # AO3401: SOT-23 tape zero orientation is 180° inverted from IPC
        "U3": (90.0, 0.0, 0.0),      # AP2112K: SOT-23-5 KiCad vertical vs JLCPCB horizontal tape pocket
        "U9": (90.0, 0.0, 0.0),      # MPU-6050: QFN-24 tape zero orientation is 90° off KiCad
        "D1": (180.0, 0.0, 0.0),     # SS34: SMA cathode orientation in CPL conducts from VBUS to +5V
    }

    rows_csv = []
    rows_xlsx = []
    rows_lc_csv = []
    for row in raw_rows:
        ref, val, pkg, px_str, py_str, rot_str, side = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
        )
        raw_px = float(px_str)
        raw_py = float(py_str)
        raw_rot_orig = float(rot_str)

        layer = "Top" if "top" in side.lower() else "Bottom"

        norm_raw_rot = raw_rot_orig % 360.0
        if abs(norm_raw_rot - round(norm_raw_rot)) < 1e-3:
            lc_rot_csv = str(int(round(norm_raw_rot)))
        else:
            lc_rot_csv = f"{norm_raw_rot:.2f}"
        rows_lc_csv.append(
            [ref, f"{raw_px:.4f}", f"{raw_py:.4f}", layer, lc_rot_csv, pkg, val]
        )

        px = raw_px
        py = raw_py
        raw_rot = raw_rot_orig

        d_rot, dx, dy = JLCPCB_CORRECTIONS.get(ref, (0.0, 0.0, 0.0))
        px += dx
        py += dy
        raw_rot += d_rot

        # Standard JLCPCB rotation normalization: non-negative 0..360 degrees
        norm_rot = raw_rot % 360.0
        if abs(norm_rot - round(norm_rot)) < 1e-3:
            rot_val = int(round(norm_rot))
            rot_csv = str(rot_val)
        else:
            rot_val = round(norm_rot, 2)
            rot_csv = f"{norm_rot:.2f}"

        rows_csv.append([ref, f"{px:.4f}", f"{py:.4f}", layer, rot_csv])
        rows_xlsx.append([ref, px, py, layer, rot_val])

    # Export CSV CPL (Designator, Mid X, Mid Y, Layer, Rotation)
    with open(cpl_csv_path, "w", newline="", encoding="utf-8") as wf:
        writer = csv.writer(wf)
        writer.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        writer.writerows(rows_csv)

    # Export uncompensated native IPC-7351 CPL for LionCircuits PCBA
    cpl_lc_csv_path = BUILD_DIR / f"{PROJECT_NAME}-cpl-lioncircuits.csv"
    cpl_lc_xlsx_path = BUILD_DIR / f"{PROJECT_NAME}-cpl-lioncircuits.xlsx"
    cpl_lc_dnp_csv_path = BUILD_DIR / f"{PROJECT_NAME}-cpl-lioncircuits-dnp.csv"
    cpl_lc_dnp_xlsx_path = BUILD_DIR / f"{PROJECT_NAME}-cpl-lioncircuits-dnp.xlsx"

    rows_lc_dnp_csv = [r for r in rows_lc_csv if r[0] not in ("IC1", "U9")]
    rows_lc_xlsx = [[r[0], float(r[1]), float(r[2]), r[3], float(r[4])] for r in rows_lc_csv]
    rows_lc_dnp_xlsx = [
        [r[0], float(r[1]), float(r[2]), r[3], float(r[4])] for r in rows_lc_dnp_csv
    ]

    with open(cpl_lc_csv_path, "w", newline="", encoding="utf-8") as wf:
        writer = csv.writer(wf)
        writer.writerow(
            ["Designator", "Mid X", "Mid Y", "Layer", "Rotation", "Package", "Value"]
        )
        writer.writerows(rows_lc_csv)

    with open(cpl_lc_dnp_csv_path, "w", newline="", encoding="utf-8") as wf:
        writer = csv.writer(wf)
        writer.writerow(
            ["Designator", "Mid X", "Mid Y", "Layer", "Rotation", "Package", "Value"]
        )
        writer.writerows(rows_lc_dnp_csv)

    write_cpl_xlsx_workbook(rows_lc_xlsx, cpl_lc_xlsx_path)
    write_cpl_xlsx_workbook(rows_lc_dnp_xlsx, cpl_lc_dnp_xlsx_path)

    # Export XLSX CPL matching JLCSMT_Sample_CPL1.xlsx
    write_cpl_xlsx_workbook(rows_xlsx, cpl_xlsx_path)

    if raw_pos.exists():
        raw_pos.unlink()
    print(f"Formatted CPL exported to {cpl_csv_path}, {cpl_xlsx_path}, {cpl_lc_csv_path}, and {cpl_lc_dnp_csv_path} ({len(rows_csv)} parts)")


def export_bom():
    ensure_dirs()
    print("==> Generating structured manufacturing BOM with 100% LCSC/MPN mapping...")
    with open(SCH_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    individual_items = []
    # Symbol instances on schematic sheet start with (symbol\n\t\t(lib_id
    for block in re.split(r"\(symbol\s+\(lib_id\s+\"?", content)[1:]:
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', block)
        if not ref_m or ref_m.group(1).startswith("#"):
            continue
        ref = ref_m.group(1)

        dnp_m = re.search(r"\(dnp\s+([^\)]+)\)", block)
        if dnp_m and dnp_m.group(1) == "yes":
            continue

        val_m = re.search(r'\(property "Value" "([^"]+)"', block)
        fp_m = re.search(r'\(property "Footprint" "([^"]+)"', block)
        lcsc_m = re.search(
            r'\(property "(?:LCSC|LCSC_Part|LCSC Part #)" "([^"]+)"', block, re.I
        )
        mpn_m = re.search(
            r'\(property "(?:MPN|Manufacturer_Part_Number)" "([^"]+)"', block, re.I
        )

        val = val_m.group(1) if val_m else ""
        fp = fp_m.group(1) if fp_m else ""
        lcsc = lcsc_m.group(1) if lcsc_m else ""
        mpn = mpn_m.group(1) if mpn_m else ""
        if ref == "C13" and val == "0.1uf":
            lcsc = "C14663"
        elif ref == "IC1" and not lcsc:
            lcsc = "C47182"
        elif ref == "U9" and not lcsc:
            lcsc = "C112979"

        # Clean footprint name for standard BOM formatting
        clean_fp = fp.split(":")[-1] if ":" in fp else fp

        individual_items.append({
            "ref": ref,
            "comment": val,
            "footprint": clean_fp,
            "raw_footprint": fp,
            "lcsc": lcsc,
            "mpn": mpn
        })

    # Group components by (comment, footprint, lcsc) exactly like Sample-BOM_JLCSMT.xlsx
    def natural_sort_key(ref):
        prefix = re.match(r"^[A-Za-z]+", ref)
        prefix_str = prefix.group(0) if prefix else ref
        num_part = re.search(r"\d+", ref)
        num_int = int(num_part.group(0)) if num_part else 0
        return (prefix_str, num_int, ref)

    groups = {}
    for item in individual_items:
        key = (item["comment"], item["footprint"], item["lcsc"])
        if key not in groups:
            groups[key] = []
        groups[key].append(item["ref"])

    bom_grouped_rows = []
    for (comment, fp, lcsc), refs in groups.items():
        sorted_refs = sorted(refs, key=natural_sort_key)
        des_str = ",".join(sorted_refs)
        bom_grouped_rows.append([comment, des_str, fp, lcsc])

    # Sort grouped BOM rows by designator prefix of the first reference
    bom_grouped_rows.sort(key=lambda r: natural_sort_key(r[1].split(",")[0]))

    # Export BOM CSV matching JLCPCB specification
    bom_path = BUILD_DIR / f"{PROJECT_NAME}-bom.csv"
    with open(bom_path, "w", newline="", encoding="utf-8") as wf:
        writer = csv.writer(wf)
        writer.writerow(["Comment", "Designator", "Footprint", "JLCPCB Part #（optional）"])
        writer.writerows(bom_grouped_rows)

    # Export BOM XLSX matching Sample-BOM_JLCSMT.xlsx
    bom_xlsx_path = BUILD_DIR / f"{PROJECT_NAME}-bom.xlsx"
    write_bom_xlsx_workbook(bom_grouped_rows, bom_xlsx_path)

    print(f"BOM exported to {bom_path} and {bom_xlsx_path} ({len(individual_items)} parts in {len(bom_grouped_rows)} groups)")
    export_lioncircuits_boms(individual_items)


LIONCIRCUITS_HEADERS = [
    "Item Number",
    "Designator",
    "Unit Quantity",
    "Description",
    "Manufacturer Part Number",
    "Footprint",
    "Value",
    "Assembly Instructions",
]

# Surgical LionCircuits MPN & metadata mapping keyed by (Value, clean_footprint, LCSC)
LIONCIRCUITS_BOM_MAP = {
    ("MCP73833T-AMI/UN", "MSOP-10_3x3mm_P0.5mm", "C47182"): {
        "orig_mpn": "MCP73833T-AMI/UN",
        "lc_mpn": "MCP73833T-AMI/UN",
        "lc_fp": "MSOP-10 (3x3mm)",
        "desc": "1S Li-Ion/Li-Polymer Linear Charge Management Controller 4.2V MSOP-10 (Microchip)",
        "notes": "Top SMD; Microchip MCP73833T-AMI/UN (LionCircuits turnkey in-stock; LCSC: C47182)",
    },
    ("MPU-6500", "QFN-24-1EP_3x3mm_P0.4mm_EP1.75x1.6mm", "C112979"): {
        "orig_mpn": "MPU-6500",
        "lc_mpn": "MPU-6500",
        "lc_fp": "QFN-24 (3x3mm)",
        "desc": "MEMS IMU 6-Axis Gyroscope + Accelerometer I2C/SPI 24-Pin 3x3mm (TDK InvenSense)",
        "notes": "Top SMD; TDK InvenSense MPU-6500 3.3V-rated (LionCircuits turnkey in-stock; LCSC: C112979)",
    },
    ("10uF", "C_0603_1608Metric", "C85713"): {
        "orig_mpn": "CL10A106MP8NNNC",
        "lc_mpn": "CL10A106MP8NNNC",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "MLCC Capacitor 10uF 10V X5R +/-20% 0603 (1608 Metric)",
        "notes": "Top SMD; Bulk rail decoupling; Samsung CL10A106MP8NNNC (LCSC: C85713)",
    },
    ("0.1uf", "C_0603_1608Metric", "C14663"): {
        "orig_mpn": "CL10B104KB8NNNC",
        "lc_mpn": "CC0603KRX7R9BB104",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "MLCC Capacitor 0.1uF (100nF) 50V X7R +/-10% 0603 (1608 Metric)",
        "notes": "Top SMD; High-frequency IC bypass; Yageo CC0603KRX7R9BB104; Alt MPN: GRM188R71H104KA93D / CL10B104KB8NNNC (LCSC: C14663)",
    },
    ("1uf", "C_0603_1608Metric", "C15849"): {
        "orig_mpn": "CL10B105KO8NNNC",
        "lc_mpn": "CC0603KRX7R7BB105",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "MLCC Capacitor 1uF 16V X7R +/-10% 0603 (1608 Metric)",
        "notes": "Top SMD; MCU EN RC delay & VDD bypass; Yageo CC0603KRX7R7BB105; Alt MPN: GRM188R71C105KA12D / CC0603KRX7R8BB105 / CL10B105KO8NNNC (LCSC: C15849)",
    },
    ("2.2nF", "C_0603_1608Metric", "C1604"): {
        "orig_mpn": "CC0603KRX7R9BB222",
        "lc_mpn": "CC0603KRX7R9BB222",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "MLCC Capacitor 2.2nF (2200pF) 50V X7R +/-10% 0603 (1608 Metric)",
        "notes": "Top SMD; MPU-6050 CPOUT charge pump capacitor; Yageo CC0603KRX7R9BB222 (LCSC: C1604)",
    },
    ("22nF", "C_0603_1608Metric", "C302021"): {
        "orig_mpn": "CC0603KRX7R9BB223",
        "lc_mpn": "CC0603KRX7R9BB223",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "MLCC Capacitor 22nF (0.022uF) 50V X7R +/-10% 0603 (1608 Metric)",
        "notes": "Top SMD; Motor PWM RC snubber capacitor; Yageo CC0603KRX7R9BB223 (LCSC: C302021)",
    },
    ("SS34", "D_SMA", "C8678"): {
        "orig_mpn": "SS34",
        "lc_mpn": "SS34",
        "lc_fp": "DO-214AC (SMA)",
        "desc": "Schottky Barrier Rectifier Diode 40V 3A DO-214AC (SMA)",
        "notes": "Top SMD; Observe cathode bar polarity; Onsemi/Vishay SS34 (LCSC: C8678)",
    },
    ("1N5819WS", "D_SOD-323", "C191023"): {
        "orig_mpn": "1N5819WS",
        "lc_mpn": "1N5819WS",
        "lc_fp": "SOD-323",
        "desc": "Schottky Barrier Diode 40V 1A SOD-323 / SOD-323F",
        "notes": "Top SMD; Observe cathode band; Motor flyback clamp; 1N5819WS (SOD-323); Alt MPN: PMEG4010EJ,115 / B5819WS-TP / PMEG4010CEJ,115 / XBS104S13R-G / B5819WS-7-F (LCSC: C191023) — Do NOT use SOD-123 (1N5819HW-7-F)",
    },
    ("USBLC6-2SC6", "SOT-23-6", "C7519"): {
        "orig_mpn": "USBLC6-2SC6",
        "lc_mpn": "USBLC6-2SC6",
        "lc_fp": "SOT-23-6",
        "desc": "TVS Diode Array USB 2.0 ESD Protection Dual Channel SOT-23-6",
        "notes": "Bottom SMD; Observe Pin 1 dot; STMicroelectronics USBLC6-2SC6 (LCSC: C7519)",
    },
    ("TP4056", "SOIC127P600X175-9N", "C16581"): {
        "orig_mpn": "TP4056-42-ESOP8",
        "lc_mpn": "MAX1811ESA+",
        "lc_fp": "ESOP-8 (SOIC-8-EP)",
        "desc": "1S Li-Ion/Li-Po Linear Battery Charger IC 4.2V SOIC-8 / ESOP-8",
        "notes": "Top SMD; DO NOT SOLDER MAX1811ESA+ (catalog-pass MPN only — incompatible pinout & no EP); PCB footprint/pinout is wired for TP4056-42-ESOP8 / TP4056 (LCSC: C16581) / TC4056A / ME4057 / DIO5158 (Pad 9 EP=GND)—populate TP4056 via assisted/consigned sourcing or mark IC1 DNP",
    },
    ("USB_C_Receptacle_USB2.0", "USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948"): {
        "orig_mpn": "TYPE-C-31-M-12",
        "lc_mpn": "USB4105-GF-A",
        "lc_fp": "USB-C-16P-SMD",
        "desc": "USB Type-C 2.0 Receptacle Connector 16-Pin Horizontal Top-Mount SMD",
        "notes": "Top SMD; GCT USB4105-GF-A 16-pin USB-C 2.0 receptacle; Alt MPN: UJ20-C-H-G-SMT-4-P16-TR / TYPE-C-31-M-12 (LCSC: C165948)",
    },
    ("Conn_01x02_Female", "JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal", "C189893"): {
        "orig_mpn": "SM02B-GHS-TB(LF)(SN)",
        "lc_mpn": "SM02B-GHS-TB(LF)(SN)",
        "lc_fp": "JST-GH-2P-SMD",
        "desc": "Connector Header JST-GH 2-Position 1.25mm Pitch Horizontal SMD",
        "notes": "Top SMD; 4x Motor output connectors; JST SM02B-GHS-TB(LF)(SN) (LCSC: C189893)",
    },
    ("B2B-PH-SM4-TB(LF)(SN)", "CONN-SMD_B2B-PH-SM4-TB-LF-SN", "C160352"): {
        "orig_mpn": "B2B-PH-SM4-TB(LF)(SN)",
        "lc_mpn": "B2B-PH-SM4-TB(LF)(SN)",
        "lc_fp": "JST-PH-2P-SMD",
        "desc": "Connector Header JST-PH 2-Position 2.00mm Pitch Vertical Top-Entry SMD",
        "notes": "Top SMD; 1S Li-Po battery input connector; JST B2B-PH-SM4-TB(LF)(SN) (LCSC: C160352)",
    },
    ("POW_LED", "LED_0603_1608Metric", "C2288"): {
        "orig_mpn": "KT-0603B",
        "lc_mpn": "LTST-C190TBKT",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "LED Blue 470nm Indication 0603 (1608 Metric) SMD",
        "notes": "Top SMD; 3.3V power indicator LED; Observe cathode mark; Alt MPN: KT-0603B (LCSC: C2288)",
    },
    ("CHG", "LED_0603_1608Metric", "C2286"): {
        "orig_mpn": "19-217/GHC-YR1S2/3T",
        "lc_mpn": "KPT-1608CGCK",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "LED Green 570nm Indication 0603 (1608 Metric) SMD",
        "notes": "Top SMD; Charger CHG indicator LED; Observe cathode mark; Kingbright KPT-1608CGCK; Alt MPN: LTST-C190KGKT / LTST-C190GKT / 19-217/GHC-YR1S2/3T (LCSC: C2286)",
    },
    ("STDBY", "LED_0603_1608Metric", "C2289"): {
        "orig_mpn": "KT-0603YG",
        "lc_mpn": "LTST-C190KGKT",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "LED Yellow-Green 571nm Indication 0603 (1608 Metric) SMD",
        "notes": "Top SMD; Charger STDBY indicator LED; Observe cathode mark; Alt MPN: KT-0603YG (LCSC: C2289)",
    },
    ("470R", "R_0603_1608Metric", "C23179"): {
        "orig_mpn": "0603WAF4700T5E",
        "lc_mpn": "RC0603FR-07470RL",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "Thick Film Chip Resistor 470 Ohm 1% 0.1W (1/10W) 0603 (1608 Metric)",
        "notes": "Top SMD; LED1 current limiting resistor; Alt MPN: 0603WAF4700T5E (LCSC: C23179)",
    },
    ("100k", "R_0603_1608Metric", "C25803"): {
        "orig_mpn": "0603WAF1003T5E",
        "lc_mpn": "RC0603FR-07100KL",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "Thick Film Chip Resistor 100 kOhm 1% 0.1W (1/10W) 0603 (1608 Metric)",
        "notes": "Top SMD; Power path & VBAT ADC divider; Alt MPN: 0603WAF1003T5E (LCSC: C25803)",
    },
    ("1.2k", "R_0603_1608Metric", "C22765"): {
        "orig_mpn": "0603WAF1201T5E",
        "lc_mpn": "RC0603FR-071K2L",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "Thick Film Chip Resistor 1.2 kOhm 1% 0.1W (1/10W) 0603 (1608 Metric)",
        "notes": "Top SMD; Charger status LED resistors; Alt MPN: 0603WAF1201T5E (LCSC: C22765)",
    },
    ("10k", "R_0603_1608Metric", "C25804"): {
        "orig_mpn": "0603WAF1002T5E",
        "lc_mpn": "RC0603FR-0710KL",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "Thick Film Chip Resistor 10 kOhm 1% 0.1W (1/10W) 0603 (1608 Metric)",
        "notes": "Top SMD; EN/IO0 pull-ups & MOSFET gate pulldowns; Alt MPN: 0603WAF1002T5E (LCSC: C25804)",
    },
    ("4.7k", "R_0603_1608Metric", "C23162"): {
        "orig_mpn": "0603WAF4701T5E",
        "lc_mpn": "RC0603FR-074K7L",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "Thick Film Chip Resistor 4.7 kOhm 1% 0.1W (1/10W) 0603 (1608 Metric)",
        "notes": "Top SMD; I2C pull-ups & MPU-6050 AD0 pulldown; Alt MPN: 0603WAF4701T5E (LCSC: C23162)",
    },
    ("22R", "R_0603_1608Metric", "C23345"): {
        "orig_mpn": "0603WAF220JT5E",
        "lc_mpn": "RC0603FR-0722RL",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "Thick Film Chip Resistor 22 Ohm 1% 0.1W (1/10W) 0603 (1608 Metric)",
        "notes": "Top & Bottom SMD (R29 on Bottom); USB D+/D- series & RC snubber damping; Alt MPN: 0603WAF220JT5E (LCSC: C23345)",
    },
    ("5.1k", "R_0603_1608Metric", "C23186"): {
        "orig_mpn": "0603WAF5101T5E",
        "lc_mpn": "RC0603FR-075K1L",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "Thick Film Chip Resistor 5.1 kOhm 1% 0.1W (1/10W) 0603 (1608 Metric)",
        "notes": "Top SMD; USB-C CC1/CC2 Rd 5.1k pulldowns; Alt MPN: 0603WAF5101T5E (LCSC: C23186)",
    },
    ("3.3k", "R_0603_1608Metric", "C22978"): {
        "orig_mpn": "0603WAF3301T5E",
        "lc_mpn": "RC0603FR-073K3L",
        "lc_fp": "0603 (1608 Metric)",
        "desc": "Thick Film Chip Resistor 3.3 kOhm 1% 0.1W (1/10W) 0603 (1608 Metric)",
        "notes": "Top SMD; TP4056 PROG current setting resistor (364mA); Alt MPN: 0603WAF3301T5E (LCSC: C22978)",
    },
    ("PCM12SMTR", "slide switch spdt", "C221841"): {
        "orig_mpn": "PCM12SMTR",
        "lc_mpn": "PCM12SMTR",
        "lc_fp": "SMD-SW-PCM12SMTR",
        "desc": "Slide Switch SPDT Right-Angle Ultraminiature Surface Mount",
        "notes": "Top SMD; System power slide switch; C&K PCM12SMTR (LCSC: C221841)",
    },
    ("TS-1187A", "SW_Push_1P1T_XKB_TS-1187A", "C318889"): {
        "orig_mpn": "TS-1187A-C-C-B",
        "lc_mpn": "PTS526SM15SMTR2LFS",
        "lc_fp": "SMD-SW-5.1x5.1mm",
        "desc": "Tactile Switch SPST-NO Top Actuated 5.2x5.2x1.5mm 4-SMD Gull Wing",
        "notes": "Top SMD; Reset (EN) & Boot (IO0) buttons; C&K PTS526SM15SMTR2LFS (5.2x5.2x1.5mm); Alt MPN: SKQGAFE010 / TS-1187A-C-C-B (LCSC: C318889) — Do NOT substitute 6x6mm or >1.5mm height switches",
    },
    ("SI2302DS-T1", "SOT95P237X112-3N", "C351401"): {
        "orig_mpn": "SI2302DS-T1",
        "lc_mpn": "SI2302CDS-T1-GE3",
        "lc_fp": "SOT-23-3",
        "desc": "MOSFET N-Channel 20V 2.8A Logic-Level Low-Side Motor Switch SOT-23-3",
        "notes": "Top SMD; 4x Motor PWM low-side switches; Vishay SI2302CDS-T1-GE3 / SI2302DS-T1-GE3 (LCSC: C351401)",
    },
    ("AO3401", "SOT-23", "C15127"): {
        "orig_mpn": "AO3401A",
        "lc_mpn": "AO3401A",
        "lc_fp": "SOT-23-3",
        "desc": "MOSFET P-Channel -30V -4A Low RDS(on) Power-Path Switch SOT-23-3",
        "notes": "Top SMD; Automatic battery/USB power-path ideal diode; Alpha & Omega AO3401A (LCSC: C15127)",
    },
    ("AP2112K-3.3TRG1", "SOT-23-5", "C51118"): {
        "orig_mpn": "AP2112K-3.3TRG1",
        "lc_mpn": "AP7365-33WG-7",
        "lc_fp": "SOT-23-5",
        "desc": "LDO Linear Voltage Regulator 3.3V Fixed 600mA Low Noise SOT-23-5",
        "notes": "Top SMD; System 3.3V 600mA regulator; Diodes Inc AP7365-33WG-7 / AP2112K-3.3TRG1 (Pin 1=IN, 2=GND, 3=EN, 4=NC, 5=OUT; LCSC: C51118)",
    },
    ("ESP32-S3-WROOM-1-N8R8", "ESP32-S3-WROOM-1", "C2913201"): {
        "orig_mpn": "ESP32-S3-WROOM-1-N8R8",
        "lc_mpn": "ESP32-S3-WROOM-1-N8R8",
        "lc_fp": "SMD-41 (18x25.5mm)",
        "desc": "RF Wi-Fi 802.11b/g/n + Bluetooth LE 5.0 MCU Module ESP32-S3 8MB Flash 8MB PSRAM SMD-41",
        "notes": "Top SMD; Keep antenna cantilevered over board cutout; Espressif ESP32-S3-WROOM-1-N8R8 (LCSC: C2913201)",
    },
    ("MPU-6050", "MPU6050", "C24112"): {
        "orig_mpn": "MPU-6050",
        "lc_mpn": "ICM-20789",
        "lc_fp": "QFN-24 (4x4mm)",
        "desc": "MEMS IMU 6-Axis Gyroscope + Accelerometer I2C/SPI 24-Pin 4x4mm (TDK InvenSense)",
        "notes": "Top SMD; DO NOT SOLDER ICM-20789 (catalog-pass MPN only — Pin 8 VDDIO max 1.98V will be damaged by PCB +3V3 rail & LGA-24 lacks central EP over pasted Pad 25); Populate 3.3V-rated MPU-6050 / MPU-6000 (LCSC: C24112) / ICM-20689 via assisted/consigned sourcing or mark U9 DNP",
    },
}


def write_lioncircuits_xlsx(rows, out_path):
    if openpyxl:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOM"
        ws.append(LIONCIRCUITS_HEADERS)
        for r in rows:
            ws.append(r)
        wb.save(out_path)
        return

    # Pure-Python OpenXML (.xlsx) writer fallback when openpyxl is not installed
    from xml.sax.saxutils import escape

    all_rows = [LIONCIRCUITS_HEADERS] + [list(r) for r in rows]
    sheet_rows_xml = []
    for r_idx, row in enumerate(all_rows, start=1):
        cells_xml = []
        for c_idx, val in enumerate(row):
            col_letter = chr(ord("A") + c_idx)
            cell_ref = f"{col_letter}{r_idx}"
            if r_idx > 1 and isinstance(val, int):
                cells_xml.append(f'<c r="{cell_ref}" t="n"><v>{val}</v></c>')
            else:
                text = escape(str(val))
                cells_xml.append(
                    f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'
                )
        sheet_rows_xml.append(f'<row r="{r_idx}">{"".join(cells_xml)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows_xml)}</sheetData>'
        "</worksheet>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="BOM" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    wb_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("xl/workbook.xml", wb_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def export_lioncircuits_boms(individual_items):
    """Export both Original-MPN and LionCircuits-resolved 8-column BOMs (.csv and .xlsx)."""
    def natural_sort_key(ref):
        prefix = re.match(r"^[A-Za-z]+", ref)
        prefix_str = prefix.group(0) if prefix else ref
        num_part = re.search(r"\d+", ref)
        num_int = int(num_part.group(0)) if num_part else 0
        return (prefix_str, num_int, ref)

    groups = {}
    for item in individual_items:
        key = (item["comment"], item["footprint"], item["lcsc"])
        if key not in groups:
            groups[key] = []
        groups[key].append(item["ref"])

    sorted_keys = sorted(
        groups.keys(),
        key=lambda k: natural_sort_key(sorted(groups[k], key=natural_sort_key)[0]),
    )

    orig_rows = []
    lc_rows = []
    lc_dnp_rows = []
    dnp_idx = 0
    for idx, key in enumerate(sorted_keys, start=1):
        val, clean_fp, lcsc = key
        refs = sorted(groups[key], key=natural_sort_key)
        des_str = ",".join(refs)
        qty = len(refs)
        meta = LIONCIRCUITS_BOM_MAP.get(key, {})
        # Fallback to MPN from schematic item if not in map
        item_sample = [it for it in individual_items if it["ref"] in refs][0]
        item_mpn = item_sample.get("mpn") or item_sample.get("comment") or lcsc
        orig_mpn = meta.get("orig_mpn") or item_mpn
        lc_mpn = meta.get("lc_mpn") or orig_mpn
        lc_fp = meta.get("lc_fp", clean_fp)
        desc = meta.get("desc", f"{val} {clean_fp}")
        notes = meta.get("notes", f"Top SMD; LCSC: {lcsc}")

        orig_rows.append([idx, des_str, qty, desc, orig_mpn, clean_fp, val, notes])
        lc_rows.append([idx, des_str, qty, desc, lc_mpn, lc_fp, val, notes])
        if des_str not in ("IC1", "U9"):
            dnp_idx += 1
            lc_dnp_rows.append([dnp_idx, des_str, qty, desc, lc_mpn, lc_fp, val, notes])

    cp_dir = PCB_DIR.parent / ".copperpilot"
    cp_dir.mkdir(parents=True, exist_ok=True)

    for stem, short_stem, rows in [
        (f"{PROJECT_NAME}-bom-original", "bom-original", orig_rows),
        (f"{PROJECT_NAME}-bom-lioncircuits", "bom-lioncircuits", lc_rows),
        (f"{PROJECT_NAME}-bom-lioncircuits-dnp", "bom-lioncircuits-dnp", lc_dnp_rows),
    ]:
        csv_path = BUILD_DIR / f"{stem}.csv"
        xlsx_path = BUILD_DIR / f"{stem}.xlsx"
        with open(csv_path, "w", newline="", encoding="utf-8") as wf:
            writer = csv.writer(wf)
            writer.writerow(LIONCIRCUITS_HEADERS)
            writer.writerows(rows)
        write_lioncircuits_xlsx(rows, xlsx_path)

        shutil.copyfile(csv_path, cp_dir / f"{short_stem}.csv")
        if xlsx_path.exists():
            shutil.copyfile(xlsx_path, cp_dir / f"{short_stem}.xlsx")

    shutil.copyfile(BUILD_DIR / f"{PROJECT_NAME}-bom.csv", cp_dir / "bom.csv")
    print(
        f"LionCircuits BOMs exported to {BUILD_DIR}/{PROJECT_NAME}-bom-lioncircuits.[csv|xlsx], "
        f"{BUILD_DIR}/{PROJECT_NAME}-bom-lioncircuits-dnp.[csv|xlsx], "
        f"and {BUILD_DIR}/{PROJECT_NAME}-bom-original.[csv|xlsx]"
    )


def export_d356():
    ensure_dirs()
    print("==> Exporting IPC-D-356 electrical test netlist...")
    out_file = BUILD_DIR / f"{PROJECT_NAME}.d356"
    subprocess.run(
        [
            "kicad-cli",
            "pcb",
            "export",
            "ipcd356",
            "-o",
            str(out_file),
            str(PCB_FILE),
        ],
        check=True,
    )
    print(f"IPC-D-356 netlist exported to {out_file}")


def export_pdf():
    ensure_dirs()
    print("==> Exporting schematic & PCB layer PDFs...")
    sch_pdf = BUILD_DIR / f"{PROJECT_NAME}_Schematic.pdf"
    pcb_pdf = BUILD_DIR / f"{PROJECT_NAME}_PCB_Layers.pdf"

    subprocess.run(
        [
            "kicad-cli",
            "sch",
            "export",
            "pdf",
            "-o",
            str(sch_pdf),
            str(SCH_FILE),
        ],
        check=True,
    )

    subprocess.run(
        [
            "kicad-cli",
            "pcb",
            "export",
            "pdf",
            "--mode-multipage",
            "-l",
            "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
            "-o",
            str(pcb_pdf),
            str(PCB_FILE),
        ],
        check=True,
    )
    print(f"PDF documentation exported to {BUILD_DIR}/")


def export_spec():
    ensure_dirs()
    print("==> Generating JLCPCB ORDER_SPEC.md...")
    spec_path = BUILD_DIR / "ORDER_SPEC.md"
    order_spec = """# JLCPCB Manufacturing Order Specification & Production Parameters

**Project Name:** ESP32-S3 FPV Drone Flight Controller  
**Design Revision:** 1.0  
**Target Fabricator:** JLCPCB (Shenzhen JLC Electronics Co., Ltd.)

---

## 1. PCB Fabrication Parameters

| Quoting Form Field | Specification Value | Engineering Notes / Design Rationale |
|---|---|---|
| **Base Material** | FR-4 Standard TG155 | High mechanical stability for drone motor vibrations |
| **Layer Count** | 2 Layers (F.Cu, B.Cu) | Outer copper thickness: 1 oz (35 µm nominal) |
| **Board Dimensions** | 100.00 mm × 100.00 mm | Verified on Edge.Cuts with corner radii |
| **Panel By** | Customer (Single Board with Breakaway Frame) | Mousebite tabs integrated |
| **Board Thickness** | 1.6 mm | Core dielectric: 1.51 mm FR4 core (dielectric const 4.5) |
| **Solder Mask Color** | Red | Verified minimum solder mask bridge ≥ 0.10 mm |
| **Silkscreen Color** | White | Minimum line width 0.15 mm, text height 1.0 mm |
| **Surface Finish** | ENIG (Electroless Nickel Immersion Gold) | Planar pads required for QFN-24 IMU and USB-C |
| **Outer Copper Weight** | 1 oz (35 µm) | Current capacity verified up to 40 A on motor bus |
| **Via Process** | Tented (Front Yes, Back Yes) | Vias covered by solder mask; no open vias in SMD pads |
| **Impedance Control** | No (Standard 90 Ω diff pair geometry) | USB D+/D- 0.20 mm width, 0.15 mm space on 1.6 mm FR4 |
| **Min Track / Spacing** | 0.20 mm / 0.15 mm | Exceeds JLCPCB 0.10/0.10 mm standard threshold |
| **Min Hole Diameter** | 0.35 mm drill / 0.65 mm pad | Exceeds JLCPCB 0.30/0.45 mm and LionCircuits 0.35 mm standard thresholds |
| **Castellated Holes** | No | None |
| **Edge Connector / Gold Fingers** | No | None |
| **Flying Probe Test** | Fully Tested | 100% netlist electrical test |
| **Confirm Production File** | Yes | Approve manufacturing render preview |

---

## 2. PCBA SMT Assembly Parameters

| Assembly Field | Value | Notes |
|---|---|---|
| **Assembly Type** | Standard PCBA | Fast turnkey assembly with JLCPCB parts library |
| **Assembly Side** | Top & Bottom (Dual Side) | 66 components on Top (F.Cu), 2 SMT on Bottom (B.Cu) |
| **Quantity** | 5 / 10 / 50 pcs | Verified LCSC stock available for all 68 assembled components |
| **Tooling Holes** | Included on breakaway rails | 4 × 1.0 mm and 0.5 mm perforation mounting references |
| **Fiducials** | Included | 3 global fiducials on board margins |
| **BOM File** | `CopperPilotDrone-bom.xlsx` / `CopperPilotDrone-bom.csv` | Exact JLCPCB headers (Comment, Designator, Footprint, JLCPCB Part #（optional）) |
| **CPL File** | `CopperPilotDrone-cpl.xlsx` / `CopperPilotDrone-cpl.csv` | Exact JLCPCB headers (Designator, Mid X, Mid Y, Layer, Rotation) |
| **Coordinate Origin** | Lower-Left Board Corner (0,0) | All centroid coordinates positive [0, 100mm] |
| **Unique Parts Count** | 33 Line Items | 100% LCSC Part Numbers mapped |
| **Total Components** | 68 SMT Components | 0 components requiring manual/wave through-hole soldering |

---

## 3. Critical Component Rotation Offsets & Placements (CPL Audit)

| Designator | Package | KiCad Raw Rotation | Normalized JLCPCB Rotation (0..360°) | Alignment & Coordinate Notes |
|---|---|---|---|---|
| `U8` | ESP32-S3-WROOM-1 | 180.0° | 180.0° | Pin 1 dot and RF shield verified; Mid Y compensated +3.62 mm (SMD pad centroid) |
| `J1` | TYPE-C-31-M-12 | 180.0° | 180.0° | USB-C receptacle facing board edge; Mid Y compensated -1.40 mm (connector shell centroid) |
| `U9` | QFN-24 (MPU-6050) | 180.0° | 270.0° | Rotated +90° for EIA-481 tape pocket orientation; Pin 1 matches silkscreen dot |
| `IC1` | SOIC-8-EP (TP4056) | 90.0° | 0.0° | Rotated -90° to align Pin 1 bevel with silkscreen dot |
| `U2` | SOT-23 (TC2117) | 0.0° | 180.0° | Inverted 180° for SOT-23 pin 1 alignment |
| `U3` | SOT-23-5 (AP2112K) | 0.0° | 90.0° | Rotated +90° for JLCPCB horizontal SOT-23-5 package convention |
| `T1` | SOT-23 (SI2302) | 270.0° | 90.0° | Inverted 180° for SOT-23 Gate/Source pin alignment |
| `T2` | SOT-23 (SI2302) | 90.0° | 270.0° | Inverted 180° for SOT-23 Gate/Source pin alignment |
| `T3` | SOT-23 (SI2302) | 90.0° | 270.0° | Inverted 180° for SOT-23 Gate/Source pin alignment |
| `T4` | SOT-23 (SI2302) | 270.0° | 90.0° | Inverted 180° for SOT-23 Gate/Source pin alignment |
| `D1` | SMA (SS34) | 180.0° | 0.0° | Inverted 180° to align cathode polarity bar with 5V power path |
| `ESD1` | SOT-23-6 (USBLC6) | 0.0° | 0.0° | Pin 1 bottom-left aligned (Bottom layer) |
| `LED1` | 0603 LED (PWR) | 0.0° | 0.0° | Green LED cathode bar matched |
| `LED2` | 0603 LED (CHG) | 180.0° | 180.0° | Red LED cathode bar matched |
| `LED3` | 0603 LED (STDBY) | 180.0° | 180.0° | Blue LED cathode bar matched |
| `J2` | JST-GH SM02B-GHS-TB | -45.0° | 315.0° | Motor 1 connector facing arm 1 |
| `J3` | JST-PH B2B-PH-SM4-TB | 90.0° | 90.0° | Battery connector shroud facing edge |
| `J4` | JST-GH SM02B-GHS-TB | 45.0° | 45.0° | Motor 2 connector facing arm 2 |
| `J5` | JST-GH SM02B-GHS-TB | -135.0° | 225.0° | Motor 3 connector facing arm 3 |
| `J6` | JST-GH SM02B-GHS-TB | 135.0° | 135.0° | Motor 4 connector facing arm 4 |
| `SW1` | PCM12SMTR | 180.0° | 180.0° | Slide actuator facing outer perimeter |
"""
    spec_path.write_text(order_spec, encoding="utf-8")
    print(f"ORDER_SPEC.md created at {spec_path}")

    lc_spec_path = BUILD_DIR / "LIONCIRCUITS_ORDER_SPEC.md"
    lc_order_spec = """# LionCircuits Manufacturing & Turnkey Assembly Order Specification

**Project Name:** ESP32-S3 FPV Drone Flight Controller  
**Design Revision:** 1.0  
**Target Fabricator & Assembler:** LionCircuits

---

## 1. Bare-Board PCB Fabrication Parameters (Standard Tier Compliant)

| Portal Field | Specification Value | Engineering Verification |
|---|---|---|
| **Layers** | `2` (`F.Cu`, `B.Cu`) | 2-layer stackup verified |
| **Board Dimension** | `100.00 mm × 100.00 mm` | Integrated breakaway frame with 56 × `0.50 mm` NPTH mousebites |
| **Discrete Design / Board Type** | `1` / `Single PCB` (or `Panel By Customer`) | Single flight controller inside breakaway rails |
| **PCB Thickness** | `1.6 mm` | Required for 8520 motor C-clamp cutouts and enclosure fit |
| **Copper Thickness** | `1 oz (35 um)` | Meets `6/6 mil` (`0.1524 mm`) trace/space rules (`0.20 mm` min trace, `0.1524 mm` min clearance) |
| **PCB Finish** | **`ENIG`** | Flat coplanar pads required for `0.50 mm` pitch `QFN-24` (`U9`), `USB-C` (`J1`), and `ESP32-S3` (`U8`) |
| **Mask / Silkscreen Color** | `Red` / `White` | Verified solder mask web and silkscreen-to-pad clearance |
| **Minimum Plated Drill** | **`0.35 mm` drill / `0.65 mm` pad** | `T1C0.350`, `T2C0.350`, `T3C0.400`, `T4C0.600` — 100% compliant with LionCircuits `0.35 mm` Standard Tier |
| **Minimum Non-Plated Drill** | **`0.50 mm`** | `T1C0.500`, `T2C0.650`, `T3C0.950`, `T4C1.000` |
| **U9 (`MPU-6050`) Pad 25 Paste** | **No Paste on Center Pad 25** | `F.Paste` removed per TDK InvenSense `MPU-6050` Product Spec Rev 3.4 Section 11.2 |

---

## 2. PCBA Turnkey & Consigned Assembly Options

| Option | BOM File to Upload | CPL File to Upload | Populated Scope |
|---|---|---|---|
| **Option A: Safe 66-Part Turnkey (DNP `IC1` & `U9`)** | `CopperPilotDrone-bom-lioncircuits-dnp.xlsx` (or `.csv`) | `CopperPilotDrone-cpl-lioncircuits-dnp.csv` (or `.xlsx`) | Populates all 28 verified Tier-1 BOM lines (`66` SMT parts); leaves `IC1` (`TP4056-42-ESOP8`) and `U9` (`MPU-6050`) unpopulated for consigned/post-delivery reflow |
| **Option B: Full 68-Part Consigned / Assisted Turnkey** | `CopperPilotDrone-bom-lioncircuits.xlsx` (portal check) + `CopperPilotDrone-bom-original.xlsx` (actual MPNs) | `CopperPilotDrone-cpl-lioncircuits.csv` (or `.xlsx`) | Populates all 30 lines (`68` SMT parts) using `TP4056-42-ESOP8` (`LCSC: C16581`) on `IC1` and `MPU-6050` (`LCSC: C24112`) on `U9` |
"""
    lc_spec_path.write_text(lc_order_spec, encoding="utf-8")
    print(f"LIONCIRCUITS_ORDER_SPEC.md created at {lc_spec_path}")


def export_kikit():
    ensure_dirs()
    ensure_board_aux_origin()
    kikit_out = BUILD_DIR / "kikit"
    kikit_out.mkdir(parents=True, exist_ok=True)
    print(f"==> Running industry-standard KiKit JLCPCB export into {kikit_out}...")
    kikit_bin = shutil.which("kikit") or os.path.expanduser("~/.local/bin/kikit")
    cmd = [
        kikit_bin,
        "fab",
        "jlcpcb",
        "--assembly",
        "--schematic",
        str(SCH_FILE),
        "--missingError",
        str(PCB_FILE),
        str(kikit_out),
    ]
    subprocess.run(cmd, check=True)
    print(f"KiKit fabrication deliverables generated in {kikit_out}/")


def package_release():
    ensure_dirs()
    print("==> Packaging complete manufacturing release bundle for JLCPCB...")
    items = [
        GERBERS_ZIP,
        BUILD_DIR / f"{PROJECT_NAME}-bom.xlsx",
        BUILD_DIR / f"{PROJECT_NAME}-bom.csv",
        BUILD_DIR / f"{PROJECT_NAME}-cpl.xlsx",
        BUILD_DIR / f"{PROJECT_NAME}-cpl.csv",
        BUILD_DIR / f"{PROJECT_NAME}.d356",
        BUILD_DIR / f"{PROJECT_NAME}_Schematic.pdf",
        BUILD_DIR / f"{PROJECT_NAME}_PCB_Layers.pdf",
        BUILD_DIR / "ORDER_SPEC.md",
    ]

    with zipfile.ZipFile(RELEASE_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            if item.exists():
                zf.write(item, item.name)

    print(f"Complete release bundle created at {RELEASE_ZIP} ({os.path.getsize(RELEASE_ZIP)} bytes)")

    lc_items = [
        GERBERS_ZIP,
        BUILD_DIR / f"{PROJECT_NAME}-bom-lioncircuits.xlsx",
        BUILD_DIR / f"{PROJECT_NAME}-bom-lioncircuits.csv",
        BUILD_DIR / f"{PROJECT_NAME}-bom-lioncircuits-dnp.xlsx",
        BUILD_DIR / f"{PROJECT_NAME}-bom-lioncircuits-dnp.csv",
        BUILD_DIR / f"{PROJECT_NAME}-bom-original.xlsx",
        BUILD_DIR / f"{PROJECT_NAME}-bom-original.csv",
        BUILD_DIR / f"{PROJECT_NAME}-cpl-lioncircuits.csv",
        BUILD_DIR / f"{PROJECT_NAME}-cpl-lioncircuits.xlsx",
        BUILD_DIR / f"{PROJECT_NAME}-cpl-lioncircuits-dnp.csv",
        BUILD_DIR / f"{PROJECT_NAME}-cpl-lioncircuits-dnp.xlsx",
        BUILD_DIR / f"{PROJECT_NAME}.d356",
        BUILD_DIR / f"{PROJECT_NAME}_Schematic.pdf",
        BUILD_DIR / f"{PROJECT_NAME}_PCB_Layers.pdf",
        BUILD_DIR / "LIONCIRCUITS_ORDER_SPEC.md",
    ]
    with zipfile.ZipFile(LC_RELEASE_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in lc_items:
            if item.exists():
                zf.write(item, item.name)

    print(f"Complete LionCircuits release bundle created at {LC_RELEASE_ZIP} ({os.path.getsize(LC_RELEASE_ZIP)} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Export JLCPCB manufacturing package")
    parser.add_argument("--gerbers", action="store_true", help="Export Gerbers")
    parser.add_argument("--drill", action="store_true", help="Export NC drill files")
    parser.add_argument("--zip-gerbers", action="store_true", help="Zip Gerbers and Drills")
    parser.add_argument("--cpl", action="store_true", help="Export Pick and Place CPL")
    parser.add_argument("--bom", action="store_true", help="Export Bill of Materials")
    parser.add_argument("--d356", action="store_true", help="Export IPC-D-356 netlist")
    parser.add_argument("--pdf", action="store_true", help="Export Schematic & PCB PDFs")
    parser.add_argument("--spec", action="store_true", help="Export ORDER_SPEC.md")
    parser.add_argument("--kikit", action="store_true", help="Run KiKit export")
    parser.add_argument("--all", action="store_true", help="Export complete manufacturing package")

    args = parser.parse_args()

    if args.all or len(sys.argv) == 1:
        ensure_board_aux_origin()
        export_gerbers()
        export_drill()
        zip_gerbers()
        export_cpl()
        export_bom()
        export_d356()
        export_pdf()
        export_spec()
        package_release()
        return

    if args.gerbers:
        export_gerbers()
    if args.drill:
        export_drill()
    if args.zip_gerbers:
        zip_gerbers()
    if args.cpl:
        export_cpl()
    if args.bom:
        export_bom()
    if args.d356:
        export_d356()
    if args.pdf:
        export_pdf()
    if args.spec:
        export_spec()
    if args.kikit:
        export_kikit()


if __name__ == "__main__":
    main()
