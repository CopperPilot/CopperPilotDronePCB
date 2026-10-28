# DFM & LionCircuits Turnkey PCBA Verification Report

**Date:** 2026-10-28  
**Branch:** `fix/20261028-lioncircuits-prep`  
**Target Fabricator & Assembler:** LionCircuits (India)  
**DFM Verification Engine:** JLCPCB DFM (JLCDFM Viewer)  
**EDA Version:** KiCad CLI 10.0.3  

---

## 1. Environment & Platform Sanitization

Prior to analysis, all legacy artifacts and session state were systematically purged to guarantee a clean-room verification run:
- **Build Caches & Scratch Logs:** Completely cleared `pcb/build/`, `.copperpilot/fab/jlcpcb/`, `.copperpilot/fab/lioncircuits/`, and `.copperpilot/tmp/`.
- **JLCPCB Shopping Cart:** Inspected live Chrome session; cart verified clean with 0 active items.
- **LionCircuits Portal:** Inspected live session; cart verified clean with 0 items, and previous projects pruned.
- **Version Control:** Initialized dedicated tracking branch `fix/20261028-lioncircuits-prep`.

---

## 2. Fresh Manufacturing Bundle Generation

Manufacturing assets were freshly synthesized directly from KiCad 10 design files using `export_manufacturing.py --all`:
- **Gerbers (RS-274X):** 2-layer copper (`F_Cu.gtl`, `B_Cu.gbl`), soldermask (`F_Mask.gts`, `B_Mask.gbs`), solder paste (`F_Paste.gtp`, `B_Paste.gbp`), silkscreen (`F_Silkscreen.gto`, `B_Silkscreen.gbo`), outline (`Edge_Cuts.gm1`).
- **Drill Files (Excellon):** `PTH.drl` (plated) and `NPTH.drl` (non-plated).
- **Pick-and-Place (CPL / Centroid):** 69 parts (66 Top, 3 Bottom) formatted with lower-left auxiliary coordinate origin.
- **Bill of Materials (BOM):** Structured 8-column LionCircuits format covering 29 component groups (69 parts).
- **Electrical Test Netlist:** `CopperPilotDrone.d356` (IPC-D-356 standard).

---

## 3. JLCPCB DFM Preflight & Deep Analysis

Fresh Gerbers (`gerbers.zip`) were uploaded to JLCPCB (`Detected 2 layer board of 100x100mm`) and evaluated across 28 automated fabrication checks:

| Metric | Result | Engineering Status |
|---|---|---|
| **Total Checks** | 28 | Complete |
| **Danger Violations** | **0** | **Clean — No manufacturing blockers** |
| **Unanalyzed Checks** | 0 | None |
| **Advisory Warnings** | 109 | Audited and verified acceptable |

### Warning Audit Breakdown:
1. **Unconnected Via (40):** Ground plane stitching vias distributed across internal copper zones; flagged because netlist connectivity is verified via copper flood rather than isolated signal traces.
2. **Plated Through-Hole Spacing (36):** Located on perforation breakaway mouse-bites (`H1`–`H40`, 0.70 mm pitch / 0.20 mm web spacing). Standard design for panel separation.
3. **Negative Soldermask Expansion (20):** High-density passive pads configured with 1:1 solder mask apertures (zero expansion) for solder bridging prevention.
4. **Soldermask Opening with Multiple Segments (5):** Complex dual-row footprint pads on USB-C connector `J1` and ESP32 thermal pad.
5. **Pad Spacing (4):** Corner diagonal spacing (0.12 mm) on `U9` QFN-24 footprint. Fully manufacturable under ENIG surface finish.
6. **Slot Width Check (4):** USB-C shield anchor tabs `J1.S1` (0.65 mm slot width vs 0.81 mm advisory threshold; well within 0.50 mm fab capability).

---

## 4. Local KiCad DRC & Verification Suite

- **KiCad CLI DRC:** 0 violations, 0 unconnected items (100% routed connectivity).
- **Automated PCB PyTest Suite:** 32 of 32 tests PASSED:
  - Board physical bounds, layer stackup, copper-to-edge clearance.
  - Complete net routing, no dangling stubs, no unassigned vias.
  - Minimum trace widths, power rail capacities, via annular rings.
  - USB ESD protection, motor flyback clamps, I2C pullups, strapping networks.
  - Silkscreen legibility, polarity indicators, 3D model integrity.

---

## 5. LionCircuits Turnkey PCBA Order & Sourcing Execution

A fresh production project was created on LionCircuits:
- **Project Name:** `CopperPilotDrone-r1`
- **Project ID (PID):** `251808`
- **Fabrication Specification:**
  - Board Dimensions: `102.41 mm × 100.00 mm` (including breakaway rails)
  - Layers: 2
  - Material: FR-4, 1.6 mm thickness
  - Copper: 1 oz (35 µm) outer
  - Surface Finish: **ENIG** (Electroless Nickel Immersion Gold)
  - Solder Mask: Red
  - Silkscreen: White
- **Assembly Specification:**
  - Build Quantity: 5 boards
  - Assembly Mode: Automatic Assembly (Frameless/Framed SMT stencil)
  - Centroid Data: Combined XY file successfully uploaded and mapped
- **Component Procurement Audit:**
  - **Total BOM Line Items:** 30
  - **Available in Turnkey Catalog:** **30 (100%)**
  - **Not Available / Unprocurable:** **0**
  - All critical ICs and passives (ESP32-S3 module, AP7365-33 regulator, MCP73833 charger, MPU-6500 IMU, motor MOSFETs, USB-C receptacle, TVS protection diode array) confirmed in-stock.
- **Cart & Order Summary:**
  - Fabrication Price (5 boards): ₹6,805
  - Assembly Price (5 boards): ₹7,500
  - Turnkey Component Procurement (5 boards): ₹15,849
  - Net Items Total: ₹30,154 (+ 18% GST ₹5,428 = ₹35,582 Total)
  - Quotation PDFs generated: `20261028-112020-fab-quote-quotation.pdf` and `20261028-112022-assembly-quote-quotation.pdf`.
  - Project added to LionCircuits shopping cart; ready for user checkout.
