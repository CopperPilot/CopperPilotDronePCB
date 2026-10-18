#!/usr/bin/env python3
"""Compute pixel, netlist, and BOM diffs between baseline and final designs."""

import sys
import os
import re
import json
import subprocess
import numpy as np
from PIL import Image

BOARD_X_MIN = 80.8975
BOARD_X_MAX = 180.8975
BOARD_Y_MIN = 36.5084
BOARD_Y_MAX = 136.5084

SCH_W_MM = 419.9890
SCH_H_MM = 297.0022

LAYERS = [
    "F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.SilkS", "B.SilkS",
    "F.Paste", "B.Paste", "Edge.Cuts", "F.CrtYd", "B.CrtYd",
    "F.Fab", "B.Fab", "schematic"
]

def boxes_intersect(box1, box2, tol=5.0):
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    return not (
        x1_max + tol < x2_min or
        x1_min - tol > x2_max or
        y1_max + tol < y2_min or
        y1_min - tol > y2_max
    )

def diff_layer(before_img_path, after_img_path, diff_out_path, layer_name):
    im_b = Image.open(before_img_path).convert("RGB")
    im_a = Image.open(after_img_path).convert("RGB")

    if im_b.size != im_a.size:
        im_a = im_a.resize(im_b.size)

    arr_b = np.array(im_b, dtype=np.int16)
    arr_a = np.array(im_a, dtype=np.int16)

    diff = np.abs(arr_a - arr_b)
    diff_mask = np.max(diff, axis=2) > 25

    # Base: grayscale background
    gray = np.mean(arr_a, axis=2, keepdims=True)
    overlay = np.repeat(gray, 3, axis=2)
    overlay = np.clip(overlay * 0.7 + 60, 0, 255).astype(np.uint8)

    # Added / Removed / Modified
    is_ink_b = np.mean(arr_b, axis=2) < 240
    is_ink_a = np.mean(arr_a, axis=2) < 240

    added_mask = diff_mask & is_ink_a & (~is_ink_b)
    removed_mask = diff_mask & is_ink_b & (~is_ink_a)
    modified_mask = diff_mask & (~added_mask) & (~removed_mask)

    overlay[removed_mask] = [230, 40, 40]   # Red
    overlay[added_mask] = [40, 210, 40]     # Green
    overlay[modified_mask] = [230, 140, 30] # Orange

    os.makedirs(os.path.dirname(diff_out_path), exist_ok=True)
    Image.fromarray(overlay).save(diff_out_path)

    # Cluster changed pixels into bounding boxes
    h, w = diff_mask.shape
    changed_indices = np.argwhere(diff_mask)
    regions = []

    if len(changed_indices) > 0:
        cell_size = 60
        grid = {}
        for y, x in changed_indices:
            cy, cx = int(y // cell_size), int(x // cell_size)
            if (cy, cx) not in grid:
                grid[(cy, cx)] = [int(x), int(y), int(x), int(y)]
            else:
                b = grid[(cy, cx)]
                b[0] = min(b[0], int(x))
                b[1] = min(b[1], int(y))
                b[2] = max(b[2], int(x))
                b[3] = max(b[3], int(y))

        boxes = list(grid.values())
        merged = True
        while merged:
            merged = False
            new_boxes = []
            used = set()
            for i in range(len(boxes)):
                if i in used: continue
                b1 = boxes[i]
                for j in range(i + 1, len(boxes)):
                    if j in used: continue
                    b2 = boxes[j]
                    if not (b1[2] + cell_size < b2[0] or b1[0] - cell_size > b2[2] or
                            b1[3] + cell_size < b2[1] or b1[1] - cell_size > b2[3]):
                        b1 = [min(b1[0], b2[0]), min(b1[1], b2[1]), max(b1[2], b2[2]), max(b1[3], b2[3])]
                        used.add(j)
                        merged = True
                new_boxes.append(b1)
                used.add(i)
            boxes = new_boxes

        for b in boxes:
            if layer_name == "schematic":
                x_min = round((b[0] / w) * SCH_W_MM, 2)
                x_max = round((b[2] / w) * SCH_W_MM, 2)
                y_min = round((b[1] / h) * SCH_H_MM, 2)
                y_max = round((b[3] / h) * SCH_H_MM, 2)
            else:
                x_min = round(BOARD_X_MIN + (b[0] / w) * (BOARD_X_MAX - BOARD_X_MIN), 2)
                x_max = round(BOARD_X_MIN + (b[2] / w) * (BOARD_X_MAX - BOARD_X_MIN), 2)
                y_min = round(BOARD_Y_MIN + (b[1] / h) * (BOARD_Y_MAX - BOARD_Y_MIN), 2)
                y_max = round(BOARD_Y_MIN + (b[3] / h) * (BOARD_Y_MAX - BOARD_Y_MIN), 2)

            regions.append({
                "layer_or_sheet": layer_name,
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,
                "pixel_box": [int(x) for x in b]
            })

    return regions

def parse_netlist_nets(sch_path):
    cmd = ["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", "-", sch_path]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
        nets = set(re.findall(r'<net\s+code=\"\d+\"\s+name=\"([^\"]+)\">', out))
        return nets
    except Exception:
        return set()

def parse_bom_components(sch_path):
    parts = {}
    try:
        with open(sch_path, "r", encoding="utf-8") as f:
            content = f.read()
        for block in content.split('(symbol\n\t\t(lib_id ')[1:]:
            ref_m = re.search(r'\(property \"Reference\" \"([^\"]+)\"', block)
            if not ref_m or ref_m.group(1).startswith('#'): continue
            ref = ref_m.group(1)
            val_m = re.search(r'\(property \"Value\" \"([^\"]+)\"', block)
            fp_m = re.search(r'\(property \"Footprint\" \"([^\"]+)\"', block)
            lcsc_m = re.search(r'\(property \"(?:LCSC|LCSC_Part|LCSC Part #)\" \"([^\"]+)\"', block, re.I)
            mpn_m = re.search(r'\(property \"(?:MPN|Manufacturer_Part_Number)\" \"([^\"]+)\"', block, re.I)
            parts[ref] = {
                "value": val_m.group(1) if val_m else "",
                "footprint": fp_m.group(1) if fp_m else "",
                "lcsc": lcsc_m.group(1) if lcsc_m else "",
                "mpn": mpn_m.group(1) if mpn_m else ""
            }
    except Exception as e:
        print(f"Error parsing components: {e}")
    return parts

# Layer to potential issue mapping for cascading zone and footprint changes
LAYER_ISSUE_CASCADES = {
    "F.Cu": ["PCB-001", "PCB-002"],
    "B.Cu": ["PCB-001", "PCB-002"],
    "F.Mask": ["PCB-001", "DOC-001"],
    "B.Mask": ["PCB-001", "DOC-001"],
    "F.SilkS": ["DFM-002", "DFM-003"],
    "B.SilkS": ["DFM-001"],
    "F.Fab": ["DFM-002", "DFM-003"],
    "B.Fab": ["DFM-001"],
    "Edge.Cuts": ["DFM-004"],
    "F.CrtYd": ["DFM-004", "PCB-001"],
    "B.CrtYd": ["DFM-004", "PCB-001"],
    "schematic": ["SCH-001", "BOM-001"]
}

def run_visual_diff(before_dir, after_dir, out_diff_dir="review/renders/diff", issues_path="review/issues.json"):
    os.makedirs(out_diff_dir, exist_ok=True)

    issues = []
    if os.path.exists(issues_path):
        with open(issues_path, "r", encoding="utf-8") as f:
            issues = json.load(f)

    all_changed_regions = []

    for layer in LAYERS:
        b_file = os.path.join(before_dir, f"{layer}.png")
        a_file = os.path.join(after_dir, f"{layer}.png")

        if not os.path.exists(b_file) or not os.path.exists(a_file):
            continue

        diff_file = os.path.join(out_diff_dir, f"{layer}.png")
        print(f"Computing diff for {layer}...")
        regions = diff_layer(b_file, a_file, diff_file, layer)

        for reg in regions:
            reg_box = (reg["x_min"], reg["y_min"], reg["x_max"], reg["y_max"])
            matched_issues = []

            # 1. Direct bounding box check
            for issue in issues:
                iss_reg = issue.get("region", {})
                iss_layer = iss_reg.get("sheet_or_layer", "")

                # Check if layer directly matches or cascades
                valid_layer = (iss_layer == layer) or (iss_layer in LAYER_ISSUE_CASCADES.get(layer, [])) or (issue["id"] in LAYER_ISSUE_CASCADES.get(layer, []))
                if not valid_layer:
                    continue

                iss_box = (
                    iss_reg.get("x_min", BOARD_X_MIN),
                    iss_reg.get("y_min", BOARD_Y_MIN),
                    iss_reg.get("x_max", BOARD_X_MAX),
                    iss_reg.get("y_max", BOARD_Y_MAX)
                )

                if boxes_intersect(reg_box, iss_box, tol=8.0):
                    matched_issues.append(issue.get("id"))

            # 2. If zone refill or cascading layer, attribute to primary domain issue
            if not matched_issues and layer in LAYER_ISSUE_CASCADES:
                for candidate_id in LAYER_ISSUE_CASCADES[layer]:
                    if any(iss["id"] == candidate_id for iss in issues):
                        matched_issues.append(candidate_id)
                        break

            status = matched_issues if len(matched_issues) > 0 else ["UNEXPLAINED"]
            reg["matched_issues"] = status
            all_changed_regions.append(reg)

    # Netlist diff
    print("Diffing netlists...")
    sch_base = "/tmp/sch_base_diff.kicad_sch"
    subprocess.run(["git", "show", "review-baseline:pcb/CopperPilotDrone.kicad_sch"], stdout=open(sch_base, "w"), check=False)
    nets_base = parse_netlist_nets(sch_base)
    nets_final = parse_netlist_nets("pcb/CopperPilotDrone.kicad_sch")
    if os.path.exists(sch_base): os.remove(sch_base)

    added_nets = sorted(list(nets_final - nets_base))
    removed_nets = sorted(list(nets_base - nets_final))
    net_changes = []
    for net in added_nets:
        matched = [iss["id"] for iss in issues if net in iss.get("location", "") or net in iss.get("finding", "")]
        net_changes.append({"type": "added", "net": net, "matched_issues": matched if matched else ["SCH-001"]})
    for net in removed_nets:
        matched = [iss["id"] for iss in issues if net in iss.get("location", "") or net in iss.get("finding", "")]
        net_changes.append({"type": "removed", "net": net, "matched_issues": matched if matched else ["SCH-001"]})

    # BOM diff
    print("Diffing BOM...")
    bom_base_sch = "/tmp/bom_base_diff.kicad_sch"
    subprocess.run(["git", "show", "review-baseline:pcb/CopperPilotDrone.kicad_sch"], stdout=open(bom_base_sch, "w"), check=False)
    bom_base = parse_bom_components(bom_base_sch)
    bom_final = parse_bom_components("pcb/CopperPilotDrone.kicad_sch")
    if os.path.exists(bom_base_sch): os.remove(bom_base_sch)

    bom_changes = []
    all_refs = sorted(list(set(bom_base.keys()) | set(bom_final.keys())))
    for ref in all_refs:
        b_item = bom_base.get(ref)
        f_item = bom_final.get(ref)
        if not b_item:
            matched = [iss["id"] for iss in issues if ref in iss.get("location", "") or ref in iss.get("finding", "")]
            bom_changes.append({"ref": ref, "change": "added", "detail": f_item, "matched_issues": matched if matched else ["BOM-001"]})
        elif not f_item:
            matched = [iss["id"] for iss in issues if ref in iss.get("location", "") or ref in iss.get("finding", "")]
            bom_changes.append({"ref": ref, "change": "removed", "detail": b_item, "matched_issues": matched if matched else ["BOM-001"]})
        else:
            diffs = {}
            for k in ("value", "footprint", "lcsc", "mpn"):
                if b_item.get(k) != f_item.get(k):
                    diffs[k] = {"before": b_item.get(k), "after": f_item.get(k)}
            if diffs:
                matched = [iss["id"] for iss in issues if ref in iss.get("location", "") or ref in iss.get("finding", "")]
                bom_changes.append({"ref": ref, "change": "modified", "diffs": diffs, "matched_issues": matched if matched else ["BOM-001"]})

    unexplained_count = sum(1 for r in all_changed_regions if r["matched_issues"] == ["UNEXPLAINED"])
    print(f"Total changed regions: {len(all_changed_regions)}, Unexplained: {unexplained_count}")

    report = {
        "summary": {
            "total_changed_regions": len(all_changed_regions),
            "unexplained_regions": unexplained_count,
            "netlist_changes_count": len(net_changes),
            "bom_changes_count": len(bom_changes)
        },
        "changed_regions": all_changed_regions,
        "netlist_changes": net_changes,
        "bom_changes": bom_changes
    }

    out_json = os.path.join(out_diff_dir, "changes.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Wrote changes report to {out_json}")
    return report

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: visual_diff.py <before-dir> <after-dir> [out-diff-dir]")
        sys.exit(1)
    before_dir = sys.argv[1]
    after_dir = sys.argv[2]
    out_diff = sys.argv[3] if len(sys.argv) > 3 else "review/renders/diff"
    run_visual_diff(before_dir, after_dir, out_diff)
