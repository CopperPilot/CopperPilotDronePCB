#!/usr/bin/env python3
"""Convert SVG or PDF to PNG with high resolution using PyMuPDF and Pillow."""

import sys
import os
import pymupdf

def convert(input_path, output_path, dpi=600):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = pymupdf.open(input_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    pix.save(output_path)
    print(f"Rendered {input_path} -> {output_path} ({pix.width}x{pix.height})")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: svg2png.py <input.svg|pdf> <output.png> [dpi]")
        sys.exit(1)
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    convert(sys.argv[1], sys.argv[2], dpi)
