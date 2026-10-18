#!/usr/bin/env python3
"""Crop issue region before, after, and diff images for evidence review."""

import sys
import os
import json
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageChops

BOARD_X_MIN = 80.8975
BOARD_X_MAX = 180.8975
BOARD_Y_MIN = 36.5084
BOARD_Y_MAX = 136.5084

SCH_W_MM = 419.9890
SCH_H_MM = 297.0022

def get_font():
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        return ImageFont.load_default()

def mm_to_px(x_mm, y_mm, domain, w_px, h_px):
    if domain in ("SCH", "schematic"):
        px = int((x_mm / SCH_W_MM) * w_px)
        py = int((y_mm / SCH_H_MM) * h_px)
    else:
        px = int(((x_mm - BOARD_X_MIN) / (BOARD_X_MAX - BOARD_X_MIN)) * w_px)
        py = int(((y_mm - BOARD_Y_MIN) / (BOARD_Y_MAX - BOARD_Y_MIN)) * h_px)
    return px, py

def crop_for_issue(issue_id, issues_path="review/issues.json", baseline_dir="review/renders/baseline", final_dir="review/renders/final", out_base="review/renders/issues"):
    if not os.path.exists(issues_path):
        print(f"Error: {issues_path} not found.")
        return False

    with open(issues_path, "r", encoding="utf-8") as f:
        issues = json.load(f)

    issue = next((item for item in issues if item.get("id") == issue_id), None)
    if not issue:
        print(f"Issue {issue_id} not found in {issues_path}.")
        return False

    region = issue.get("region", {})
    layer_or_sheet = region.get("sheet_or_layer", "F.Cu")
    domain = issue.get("domain", "PCB")

    x_min = region.get("x_min", BOARD_X_MIN)
    y_min = region.get("y_min", BOARD_Y_MIN)
    x_max = region.get("x_max", BOARD_X_MAX)
    y_max = region.get("y_max", BOARD_Y_MAX)

    # Add 2.0 mm margin
    margin = 2.0
    x_min_m = max(BOARD_X_MIN if domain != "SCH" else 0.0, x_min - margin)
    y_min_m = max(BOARD_Y_MIN if domain != "SCH" else 0.0, y_min - margin)
    x_max_m = min(BOARD_X_MAX if domain != "SCH" else SCH_W_MM, x_max + margin)
    y_max_m = min(BOARD_Y_MAX if domain != "SCH" else SCH_H_MM, y_max + margin)

    # Determine file names
    if domain == "SCH" or layer_or_sheet in ("SCH", "schematic"):
        img_name = "schematic.png"
    else:
        # Layer filename mapping
        layer_clean = layer_or_sheet.replace(".", "_")
        img_name = f"{layer_or_sheet}.png"
        if not os.path.exists(os.path.join(baseline_dir, img_name)):
            img_name = f"CopperPilotDrone-{layer_clean}.png"
            if not os.path.exists(os.path.join(baseline_dir, img_name)):
                img_name = f"{layer_or_sheet}.png"

    before_path = os.path.join(baseline_dir, img_name)
    after_path = os.path.join(final_dir, img_name)

    if not os.path.exists(before_path) or not os.path.exists(after_path):
        print(f"Warning: Image missing ({before_path} or {after_path}). Searching fallback...")
        # fallback search
        for f in os.listdir(baseline_dir):
            if layer_or_sheet.replace(".", "_") in f or layer_or_sheet in f:
                before_path = os.path.join(baseline_dir, f)
                break
        for f in os.listdir(final_dir):
            if layer_or_sheet.replace(".", "_") in f or layer_or_sheet in f:
                after_path = os.path.join(final_dir, f)
                break

    if not os.path.exists(before_path) or not os.path.exists(after_path):
        print(f"Error: Could not resolve before/after images for layer {layer_or_sheet}.")
        return False

    im_before = Image.open(before_path).convert("RGBA")
    im_after = Image.open(after_path).convert("RGBA")

    w_px, h_px = im_before.size
    px_x1, px_y1 = mm_to_px(x_min_m, y_min_m, domain, w_px, h_px)
    px_x2, px_y2 = mm_to_px(x_max_m, y_max_m, domain, w_px, h_px)

    px_x1, px_x2 = min(px_x1, px_x2), max(px_x1, px_x2)
    px_y1, px_y2 = min(px_y1, px_y2), max(px_y1, px_y2)

    # Box coordinates without margin (for bounding box outline)
    box_x1, box_y1 = mm_to_px(x_min, y_min, domain, w_px, h_px)
    box_x2, box_y2 = mm_to_px(x_max, y_max, domain, w_px, h_px)
    box_x1, box_x2 = min(box_x1, box_x2), max(box_x1, box_x2)
    box_y1, box_y2 = min(box_y1, box_y2), max(box_y1, box_y2)

    crop_before = im_before.crop((px_x1, px_y1, px_x2, px_y2))
    crop_after = im_after.crop((px_x1, px_y1, px_x2, px_y2))

    # Compute diff crop
    diff = ImageChops.difference(crop_before.convert("RGB"), crop_after.convert("RGB"))
    diff_overlay = crop_after.copy()
    diff_draw = ImageDraw.Draw(diff_overlay)

    font = get_font()

    # Draw bounding box and label on crops
    for cr, label in [(crop_before, "BEFORE"), (crop_after, "AFTER"), (diff_overlay, f"DIFF {issue_id}")]:
        draw = ImageDraw.Draw(cr)
        # Relative coordinates in cropped image
        rx1 = box_x1 - px_x1
        ry1 = box_y1 - px_y1
        rx2 = box_x2 - px_x1
        ry2 = box_y2 - px_y1
        draw.rectangle([rx1, ry1, rx2, ry2], outline="red", width=3)
        draw.text((rx1 + 4, max(0, ry1 - 24)), f"{issue_id} ({label})", fill="red", font=font)

    issue_dir = os.path.join(out_base, issue_id)
    os.makedirs(issue_dir, exist_ok=True)

    crop_before.save(os.path.join(issue_dir, "before.png"))
    crop_after.save(os.path.join(issue_dir, "after.png"))
    diff_overlay.save(os.path.join(issue_dir, "diff.png"))

    print(f"Generated issue crops for {issue_id} in {issue_dir}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", required=True, help="Issue ID (e.g. PCB-001)")
    args = parser.parse_args()
    success = crop_for_issue(args.issue)
    sys.exit(0 if success else 1)
