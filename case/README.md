# CopperPilot Drone: Parametric 3D Squircle Enclosure

[![3D CAD Status](https://img.shields.io/badge/CAD-CadQuery%202.8-brightgreen.svg)](generate_case.py)
[![Collision Status](https://img.shields.io/badge/Collision-Zero%20Clashes%20%7C%2014%2F14%20Pass-brightgreen.svg)](collision.py)
[![Test Suite](https://img.shields.io/badge/Tests-18%2F18%20Passed-success.svg)](tests/test_enclosure.py)
[![3D Print Ready](https://img.shields.io/badge/Print-PETG%20%2F%20SLA%20Resin-blue.svg)](#6-3d-printing--slicing-recommendations)

A lightweight, aerodynamic, clip-on squircle enclosure engineered specifically for the CopperPilot ESP32-S3 micro quadcopter flight controller PCB. Generated entirely in Python using CadQuery and Trimesh, the enclosure automatically extracts physical board boundaries, mousebite break-away tabs, and 3D component keepouts directly from `pcb/CopperPilotDrone.kicad_pcb`.

---

## 1. System Overview & Geometry

```
pcb/CopperPilotDrone.kicad_pcb
              │
              ├──> [case/pcb_parser.py] ──> Central 45x45mm Hub, Waist Notches, Component 3D Keepouts
              │                                           │
              │                                           v
              │                               [case/generate_case.py]
              │                               - Lamé Superellipse Loft (n=4.0 -> 3.5)
              │                               - Dual-loft hollow shelling (1.4mm wall)
              │                               - Under-PCB cantilever snap hooks (waist notches)
              │                               - Port cutouts (USB-C, JST-PH, Switch, Motors, Antenna)
              │                               - Debossed "CopperPilot.ai" (Inter Bold)
              │                                           │
              │                                           ├──> case/build/case_top.stl
              │                                           ├──> case/build/case_bottom.stl
              │                                           └──> case/build/explosion_animation.gif
              │
              └──> [kicad-cli pcb export stl] ──> case/build/pcb_assembly.stl
                                                              │
                                                              v
                                                  [case/collision.py]
                                                  - Solid penetration detection (0 clashing vertices)
                                                  - Proximity & signed-distance queries (>= 0.50mm)
                                                              │
                                                              v
                                                  [case/tests/test_enclosure.py]
                                                  - Automated 18-point PyTest verification suite
```

The enclosure employs a **Lamé superellipse (squircle)** cross-section defined by the equation $|x/a|^n + |y/b|^n = 1$, transitioning smoothly from a classical squircle ($n = 4.0$) at the PCB perimeter to a softer crown ($n = 3.5$) on the top plateau.

### Physical Envelope Specifications

| Parameter | Top Canopy (`case_top.stl`) | Base Chassis (`case_bottom.stl`) | Notes |
| :--- | :--- | :--- | :--- |
| **Outer Width (X)** | 52.33 mm | 52.40 mm | Encloses 45.0 mm PCB hub with +0.30 mm clearance |
| **Outer Length (Y)** | 55.89 mm | 56.40 mm | Covers North USB-C to South ESP32 antenna |
| **Outer Height (Z)** | 11.85 mm | 6.00 mm | Clears tallest component (J3 JST-PH at 8.10 mm) |
| **Wall Thickness** | 1.40 mm (nominal) | 1.40 mm (nominal) | Exactly 3.5 passes with a 0.40 mm nozzle |
| **Displaced Volume** | 4.54 cm³ | 3.80 cm³ | Compliant with flight payload budget ($\le 15.0\text{ cm}^3$) |
| **Internal Cavity** | 29.78 cm³ | 12.50 cm³ | Expansion volume for electronics and airflow |
| **Estimated Mass** | 5.76 g (PETG @ 1.27 g/cm³) | 4.82 g (PETG) | Combined assembly mass: 10.58 g ($\le 22.0\text{ g}$ budget) |
| **Top Branding** | "CopperPilot.ai" | — | Debossed 0.40 mm into crown in Inter Bold font |

---

## 2. Post-Snap-Off PCB Integration & Snap Hooks

### Snap-Off Units on the Drone Airframe
The manufactured PCB panel integrates five sacrificial units designed to be snapped off prior to flight:
1. **Left Landing Feet (2 units)**: Located along the left tooling rail ($X < 108.4\text{ mm}$), connected via 0.50 mm mousebite perforations at $X = 99.13\text{ mm}$ and $X = 108.25\text{ mm}$.
2. **Right Landing Feet (2 units)**: Located along the right tooling rail ($X > 153.4\text{ mm}$), connected via mousebites at $X = 153.55\text{ mm}$ and $X = 162.67\text{ mm}$.
3. **Antenna Manufacturing Support Tab (1 unit)**: Located at the bottom edge ($Y > 109.0\text{ mm}$), supporting the overhanging ESP32-S3 PCB antenna during SMT assembly and soldering.

### Waist Snap Hook Landing Zones
Once the panel units are snapped off, clean bare FR-4 waist notches emerge along the left and right hub perimeters:
- **Left Waist Notch**: Continuous 22.22 mm landing edge along $X = 108.398\text{ mm}$ spanning $Y \in [75.400, 97.617]\text{ mm}$ ($Y_{3D} \in [-97.617, -75.400]\text{ mm}$). Zero copper or traces exist for $>3.5\text{ mm}$ inward.
- **Right Waist Notches**: Dual-partitioned landing zones along $X = 153.398\text{ mm}$ at $Y_{3D} \in [-77.000, -71.900]\text{ mm}$ and $Y_{3D} \in [-99.000, -93.000]\text{ mm}$, flanking the J3 battery connector port.

### Cantilever Snap-Fit Mechanics
- **Latching Depth**: Downward reach of 2.10 mm past the 1.60 mm PCB thickness.
- **Undercut Retention**: 0.45–0.50 mm positive mechanical undercut with a flat 90° retention ledge that locks against the bottom solder mask.
- **Lead-In Ramp**: 45° chamfered tip that cams over the FR-4 edge with $< 8\text{ N}$ insertion force during downward assembly.
- **Deflection Strain**: $\epsilon = \frac{3 \cdot Y \cdot h}{2 \cdot L^2} \approx 1.94\%$, safely below the 4.0% yield strain of PETG and 4.5% of ABS.

---

## 3. Port Cutouts & Mechanical Clearances

The enclosure features cutouts engineered to prevent collision with top-side SMT components while providing operational access:

```
                          [North Wall: USB-C (J1) & Power Switch (SW1)]
                       +-------------------------------------------------+
                       |     [SW1]                [J1 USB-C]    (LED1)   |
                       |   6.0x3.8mm              10.2x4.4mm    Ø2.0mm   |
                       |                                                 |
                       | (SW2 Reset)                                     |
                       |   Ø2.8mm                                        |
    [Left Waist Notch] |                                                 | [Right Waist Notch]
     Cantilever Snap   |                   [MPU-6050]                    |  Cantilever Snap
      X=108.40mm       |                 Acoustic Cavity                 |   X=153.40mm
                       |                                                 |
                       | (SW3 Boot)                               [J3]   |
                       |   Ø2.8mm                              JST-PH 1S |
                       |                                       9.5x8.0mm |
                       |            [ESP32-S3 WROOM-1]                   |
                       |            Antenna RF Window                    |
                       |                22.0x6.0mm                       |
                       +-------------------------------------------------+
                          [South Wall: Battery Cutout & Antenna Window]
```

| Subsystem / Port | Component Ref | Cutout Type | Aperture Dimensions | Clearance to Shell |
| :--- | :--- | :--- | :--- | :--- |
| **USB-C Receptacle** | `J1` | North wall rectangular collar | $10.20\text{ mm} \times 4.40\text{ mm}$ | $+2.23\text{ mm}$ margin |
| **1S LiPo Battery** | `J3` | East wall U-channel slot | $9.50\text{ mm} \times 8.00\text{ mm}$ | $+1.72\text{ mm}$ margin |
| **Power Slide Switch** | `SW1` | North wall horizontal slot | $5.50\text{ mm} \times 3.50\text{ mm}$ | $+1.50\text{ mm}$ actuator travel |
| **Reset Button** | `SW2` | Top canopy stylus pinhole | $\varnothing 2.80\text{ mm}$ through-hole | Aligned ($\Delta = 0.0\text{ mm}$) |
| **Boot Button** | `SW3` | Top canopy stylus pinhole | $\varnothing 2.80\text{ mm}$ through-hole | Aligned ($\Delta = 0.0\text{ mm}$) |
| **Motor Connectors** | `J2, J4, J5, J6` | 4 corner diagonal archways | $12.00\text{ mm} \times 8.00\text{ mm}$ | $+1.60\text{ mm}$ radial wire clearance |
| **Status LEDs** | `LED1, LED2, LED3`| Top canopy light viewports | $3\times \varnothing 2.00\text{ mm}$ cylinders | Aligned ($\le 1.0\text{ mm}$ to probe) |
| **ESP32-S3 Antenna** | `U8` | South crown RF window | $22.00\text{ mm} \times 6.00\text{ mm}$ | Zero plastic over PIFA antenna |
| **6-Axis IMU** | `U9` | Internal acoustic dome cavity | Overhead clearance $\ge 6.15\text{ mm}$ | Complete acoustic decoupling |

---

## 4. Collision Detection Engine (`collision.py`)

Verification is conducted using a pipeline that evaluates the full 3D PCB assembly directly exported from KiCad CLI against the CadQuery enclosure meshes:

1. **KiCad CLI 3D Export**: Invokes `kicad-cli pcb export stl --subst-models --include-tracks --include-pads` to produce `pcb_assembly.stl` with high-fidelity component geometry.
2. **Solid Penetration Audit**: Queries `case_mesh.contains(pcb_mesh.vertices)` to ensure exactly **0 penetrating vertices**.
3. **Signed-Distance & Clearance Audit**: Evaluates distances from the enclosure shell to bounding sample points across all 14 functional circuits, enforcing a minimum clearance threshold of $\ge 0.50\text{ mm}$.
4. **Structured JSON Diagnostics**: Emits comprehensive test logs and clearance metrics to `case/build/collision_report.json`.

---

## 5. CLI Usage & Pipeline Orchestration

### Generate 3D Enclosure Assets
```bash
# Generate STL models with default parameters into case/build/
python3 case/generate_case.py

# Generate models and render 3D rotating exploded-view assembly animation
python3 case/generate_case.py --render-animation

# Custom wall thickness and material profile
python3 case/generate_case.py --wall-thickness 1.2 --material pla --output-dir out/
```

### Run Automated Collision Verification
```bash
# Verify clearance against KiCad PCB 3D assembly STL
python3 case/collision.py \
    --case-top case/build/case_top.stl \
    --case-bottom case/build/case_bottom.stl \
    --min-clearance 0.50 \
    --json-report case/build/collision_report.json
```

### Inspect PCB Geometry & Mechanical Bounds
```bash
# Parse KiCad board outline, snap-off tabs, and component keepouts
python3 case/pcb_parser.py --pcb pcb/CopperPilotDrone.kicad_pcb
```

---

## 6. 3D Printing & Slicing Recommendations

| Parameter | Recommended Value | Notes |
| :--- | :--- | :--- |
| **Material** | **PETG** or **Tough SLA Resin** | High elastic elongation ($\ge 3.5\%$) for repeatable snap-hook cycling |
| **Nozzle Diameter** | 0.40 mm | Standard FDM brass or hardened steel nozzle |
| **Layer Height** | 0.15–0.20 mm | 0.15 mm provides smooth debossed text and snap-fit lead-in ramps |
| **Perimeters / Walls** | $\ge 3$ perimeters | Ensures solid shell density across the 1.40 mm wall |
| **Infill** | 100% rectilinear | Wall thickness is shelled; remaining ribs print 100% solid |
| **Print Orientation** | Crown face down on build plate | Minimizes support structures; ensures clean debossed "CopperPilot.ai" text |
| **Supports** | Tree / organic supports | Only required under the overhang of the cantilever snap hooks |

---

## 7. Makefile Targets

The `case/` directory integrates with both its own subfolder Makefile and the project root build system:

```bash
# Run all targets: generate CAD, run 18 pytest tests, and verify 3D collisions
make -C case all

# Individual subfolder targets
make -C case generate    # Synthesize parametric case_top.stl and case_bottom.stl
make -C case test        # Execute 18-point PyTest verification suite
make -C case collision   # Run 3D Trimesh collision & clearance verification
make -C case fmt         # Auto-format Python sources with ruff
make -C case fmt-check   # Check code formatting compliance
make -C case lint        # Run static analysis and linting with ruff
make -C case clean       # Purge build outputs and test caches

# Top-level root Makefile targets
make test                # Runs firmware (Unity) + PCB (PyTest) + Enclosure (PyTest)
make test-case           # Runs 3D enclosure test suite
make collision           # Runs 3D collision detection against PCB STL
make build-case          # Generates parametric 3D enclosure CAD models
make lint                # Full project static analysis across all languages
make fmt                 # Full project formatting
```
