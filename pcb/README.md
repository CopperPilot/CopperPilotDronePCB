# CopperPilot Drone Hardware: PCB Specifications & Manufacturing Guide

[![KiCad Project](https://img.shields.io/badge/KiCad-v10.0.3-brightgreen.svg)](CopperPilotDrone.kicad_pro)
[![DRC Status](https://img.shields.io/badge/DRC-Zero%20Errors%20%7C%20Zero%20Unconnected-brightgreen.svg)](CopperPilotDrone.kicad_pcb)
[![Fabricator](https://img.shields.io/badge/Target%20Fab-JLCPCB%202--Layer%20FR4-orange.svg)](https://jlcpcb.com)
[![SMT Assembly](https://img.shields.io/badge/JLCPCB%20PCBA-100%25%20SMT%20Compatible-blue.svg)](#complete-bill-of-materials-bom)

This directory contains the complete electronic design files, manufacturing rules, test suites, and component specifications for the CopperPilot 2-layer micro quadcopter flight controller and airframe.

---

## 1. Board Specifications & Geometry

| Parameter | Specification | Details / Notes |
| :--- | :--- | :--- |
| **Dimensions** | 100.64 mm x 100.00 mm | Outer bounding box including arm motor pods |
| **Layer Count** | 2 Copper Layers | Layer 1: Top (F.Cu), Layer 2: Bottom (B.Cu) |
| **Finished Thickness**| 1.60 mm $\pm 10\%$ | Standard rigid FR-4 core |
| **Copper Weight** | 1 oz finished (35 µm) | Top and bottom copper |
| **Airframe Geometry**| Quad-X Symmetrical | 45° diagonal arms, 118.79 mm motor-to-motor wheelbase |
| **Motor Mounts** | 4x Integrated C-Clamps | 8.80 mm inside diameter cutouts on `Edge.Cuts` for 8520 coreless motors |
| **Battery Bay** | 17.0 mm x 19.5 mm cutout | Sized for standard 1S 300–600 mAh LiPo pouch cells |
| **Battery Strap Slot**| 16.5 mm x 4.0 mm | Integrated slot for micro velcro or silicone retention strap |
| **RF Keepout Zone** | 22.0 mm x 18.5 mm | Zero copper on both layers beneath ESP32-S3 PCB antenna |
| **Routing Status** | 100% Routed (36/36 Nets) | 0 airwires, 0 DRC errors, 444 traces, 77 vias |

---

## 2. Fabricator Selection & JLCPCB DFM Rules

The board has been engineered from the ground up to match **JLCPCB Standard 2-Layer PCB & SMT Assembly** processes with high yield and zero manufacturing fee penalties.

### 2-Layer Stackup

```
Layer Name           Material        Thickness     Copper Weight   Dielectric Constant
--------------------------------------------------------------------------------------
Top Solder Mask      LPI Green       10 - 25 µm    -               -
Layer 1 (F.Cu)       Copper (Signal) 35 µm (1 oz)  1.0 oz/ft²      -
Dielectric Core      FR-4 Core       1.50 mm       -               εr ≈ 4.5 @ 1 MHz
Layer 2 (B.Cu)       Copper (GND/PWR)35 µm (1 oz)  1.0 oz/ft²      -
Bottom Solder Mask   LPI Green       10 - 25 µm    -               -
--------------------------------------------------------------------------------------
Total Finished Thickness: 1.60 mm ± 10%
```

### Design Rule Margins vs. JLCPCB Capabilities

| Feature | JLCPCB Standard Limit | Drone PCB Design | Safety Margin | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Min Trace Width** | 0.127 mm (5.0 mil) | **0.200 mm** (7.87 mil) | **+57%** | Verified |
| **Min Trace Spacing** | 0.127 mm (5.0 mil) | **0.1524 mm** (6.00 mil) | **+20%** | Verified |
| **Signal Via Drill** | 0.300 mm (11.8 mil) | **0.300 mm** (11.8 mil) | Standard fab limit | Verified |
| **Signal Via Diameter**| 0.500 mm (19.7 mil) | **0.600 mm** (23.6 mil) | **+20%** (0.15mm ring) | Verified |
| **Power Via Drill** | 0.300 mm | **0.400 mm** (15.7 mil) | **+33%** | Verified |
| **Power Via Diameter** | 0.500 mm | **0.800 mm** (31.5 mil) | **+60%** (0.20mm ring) | Verified |
| **Board Edge Clearance**| 0.200 mm (7.9 mil) | **0.300 mm** min functional | **+50%** (tracks >0.62mm) | Verified |
| **Solder Mask Dam** | 0.100 mm (3.9 mil) | **0.150 mm** min web | **+50%** (QFN & USB-C) | Verified |
| **Silkscreen Stroke** | 0.150 mm (5.9 mil) | **0.150 mm** min line | Compliant | Verified |
| **Silkscreen Height** | 0.800 mm (31.5 mil) | **1.000 mm** standard | **+25%** | Verified |
| **Surface Finish** | Lead-Free HASL / ENIG | **ENIG** recommended | Required for 0.5mm QFN | Selected |

---

## 3. Power Distribution & Thermal Architecture

### Motor Drive Current Regimes
Standard 8520 brushed coreless DC motors (8.5 mm x 20 mm) operate at:
- **Hover Current**: 1.0 A to 1.2 A per motor (4.0 A to 4.8 A total continuous draw).
- **Punch-Out Burst**: 2.0 A to 2.5 A per motor (8.0 A to 10.0 A total peak draw for $< 3\text{ seconds}$).
- **Locked-Rotor Stall**: Up to 3.0 A per motor (12.0 A transient).

### Battery Power Bus Routing (`+BATT`)
- Main power distribution runs along dedicated wide copper corridors (1.016 mm to 1.524 mm) on both top and bottom layers.
- Traces are stitched through **19 power vias** (0.8 mm pad / 0.4 mm drill), providing an aggregate current-carrying capacity exceeding **40 A continuous** with less than $50\text{ mV}$ DC voltage drop at full throttle.

### Low-Side Switching MOSFETs (T1–T4)
- **Component**: PUOLOP / Vishay SI2302DS-T1 N-channel MOSFET in SOT-23 ($V_{DS} = 20\text{ V}$, $I_D = 2.8\text{ A}$).
- **On-Resistance**: $R_{DS(on)} = 55\text{ to }65\text{ m}\Omega$ at $V_{GS} = 3.3\text{ V}$.
- **Thermal Dissipation**:
  - Hover ($1.0\text{ A}$): $P = I^2 \times R_{DS(on)} = 1.0^2 \times 0.056 = 56\text{ mW}$. Junction temperature rise: $\Delta T \approx 8.4^\circ\text{C}$ over ambient.
  - Full Throttle ($2.2\text{ A}$): $P = 2.2^2 \times 0.056 = 271\text{ mW}$. Junction temperature rise: $\Delta T \approx 40.6^\circ\text{C}$ over ambient, well within the $150^\circ\text{C}$ maximum junction rating.

### Inductive Flyback Protection (D2–D5) & Snubbers (C15–C18)
- Each motor channel is protected by a **1N5819WS** 40 V 1 A Schottky diode in a compact SOD-323 package, clamping inductive turn-off voltage spikes to $V_{BATT} + 0.45\text{ V} \approx 4.65\text{ V}$ (providing a 425% safety margin below the MOSFET's 20 V breakdown).
- **22 nF 0603 MLCC snubber capacitors** across each motor terminal eliminate high-frequency brush commutation arcing and RF interference without causing the destructive 52 A inrush current pulses exhibited by legacy 1.0 µF snubber values.

### Linear Regulators & Battery Charging
- **3.3V LDO (U3)**: MicrOne ME6211C33M5G-N in SOT-23-5 provides 500 mA continuous output with 51 µF of distributed ceramic decoupling (C3, C4, C9, C10, C14) to buffer 500 mA ESP32-S3 Wi-Fi calibration bursts.
- **Li-Po Charger (IC1)**: TP4056-42-ESOP8 linear charger set to 364 mA constant-current rate via $3.3\text{ k}\Omega$ $R_{prog1}$, ensuring safe $0.7\text{C}$ to $1.2\text{C}$ charging for 300–500 mAh 1S cells without thermal throttling.
- **Power Mux (U2)**: AO3401 P-channel MOSFET ideal diode circuit automatically disconnects the battery from the charging port when USB-C 5V VBUS is plugged in, preventing reverse charging into the cell.

---

## 4. Complete Bill of Materials (BOM)

All 64 components use surface-mount packages compatible with **JLCPCB SMT Assembly**. Sourcing is optimized to maximize LCSC "Basic Parts" ($0 feeder fee) to minimize assembly setup costs.

| Item | Reference | Qty | Value | Package | LCSC Part # | Description | Part Type |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| 1 | **U8** | 1 | ESP32-S3-WROOM-1-N8R8 | SMD-41 | `C2913201` | Dual-Core 240MHz MCU, 8MB Flash, 8MB PSRAM, Wi-Fi/BLE | Extended |
| 2 | **U9** | 1 | MPU-6050 | QFN-24 4x4mm | `C24112` | 6-Axis I2C Gyroscope + Accelerometer IMU Sensor | Extended |
| 3 | **IC1** | 1 | TP4056-42-ESOP8 | ESOP-8 | `C16581` | 1A Standalone Linear Li-Po Battery Charger (364mA) | Extended |
| 4 | **U2** | 1 | AO3401 | SOT-23 | `C15127` | -30V -4.2A P-Channel MOSFET Ideal Diode Power Mux | **Basic** |
| 5 | **U3** | 1 | ME6211C33M5G-N | SOT-23-5 | `C82942` | 3.3V 500mA Ultra-Low-Noise CMOS LDO Regulator | **Basic** |
| 6 | **T1..T4** | 4 | SI2302DS-T1 | SOT-23 | `C351401` | 20V 2.8A N-Channel Low-Side Motor Drive MOSFETs | **Basic** |
| 7 | **D1** | 1 | SS34 | SMA DO-214AC | `C8678` | 40V 3A Schottky Rectifier for VBUS Reverse Protection | **Basic** |
| 8 | **D2..D5** | 4 | 1N5819WS | SOD-323 | `C191023` | 40V 1A Schottky Motor Flyback Inductive Clamps | **Basic** |
| 9 | **ESD1** | 1 | USBLC6-2SC6 | SOT-23-6 | `C7519` | Low-Capacitance USB Type-C TVS ESD Diode Array | **Basic** |
| 10 | **J1** | 1 | TYPE-C-31-M-12 | USB-C 16-Pin SMT | `C165948` | USB 2.0 Type-C Receptacle (Power & Native USB D+/D-) | Extended |
| 11 | **J2,J4,J5,J6**| 4 | SM02B-GHS-TB | JST-GH 1.25mm SMT| `C189893` | 2-Pin Shrouded Motor Connectors | Extended |
| 12 | **J3** | 1 | B2B-PH-SM4-TB | JST-PH 2.0mm SMT | `C160352` | 2-Pin 1S Battery Input Connector | Extended |
| 13 | **SW1** | 1 | PCM12SMTR | SPDT SMT Slide | `C221841` | System Main Power Slide Switch (Alt: C92658) | Extended |
| 14 | **SW2,SW3** | 2 | TS-1187A-B-A-B | 5.1x5.1mm SMT | `C318884` | Momentary Tactile Switches (RESET & BOOT) | **Basic** |
| 15 | **LED1** | 1 | Blue LED | 0603 SMD | `C72041` | 3.3V System Power Indicator LED | **Basic** |
| 16 | **LED2** | 1 | Red LED | 0603 SMD | `C2286` | TP4056 Battery Charging Status Indicator | **Basic** |
| 17 | **LED3** | 1 | Green LED | 0603 SMD | `C72043` | TP4056 Full Charge / Standby Status Indicator | **Basic** |
| 18 | **R1** | 1 | 470R 1% | 0603 SMD | `C23179` | Blue Power LED Current Limiter | **Basic** |
| 19 | **R2,R26..R28**| 4 | 100k 1% | 0603 SMD | `C25803` | Power Mux Gate Pulldown & Battery ADC Divider | **Basic** |
| 20 | **R3,R4** | 2 | 1.2k 1% | 0603 SMD | `C22765` | TP4056 Status LED Current Limiters | **Basic** |
| 21 | **R10,R11,R18..R21**| 6| 10k 1% | 0603 SMD | `C25804` | EN/IO0 Pull-Ups & Motor Gate Pulldowns | **Basic** |
| 22 | **R12,R13,R14**| 3 | 4.7k 1% | 0603 SMD | `C23162` | I2C SDA/SCL Pull-Ups & MPU-6050 AD0 Address Select| **Basic** |
| 23 | **R22,R23** | 2 | 22R 5% | 0603 SMD | `C23345` | USB 2.0 Full-Speed D+/D- Series Damping Resistors | **Basic** |
| 24 | **R24,R25** | 2 | 5.1k 1% | 0603 SMD | `C23186` | USB-C Configuration Channel CC1/CC2 5.1k Pulldowns| **Basic** |
| 25 | **Rprog1** | 1 | 3.3k 1% | 0603 SMD | `C22978` | Sets TP4056 Charge Current to 364 mA | **Basic** |
| 26 | **C1,C3,C4,C5,C7,C9,C14**| 7| 10µF 10V X5R | 0603 SMD | `C19702` | Bulk Decoupling & LDO Reservoirs | **Basic** |
| 27 | **C6,C12** | 2 | 0.1µF 50V X7R | 0603 SMD | `C14663` | High-Frequency IC Power Decoupling | **Basic** |
| 28 | **C10,C11** | 2 | 1µF 50V X5R | 0603 SMD | `C15849` | EN Pin Startup RC Filter & ESP32 VDD Bypass | **Basic** |
| 29 | **C13** | 1 | 2.2nF 50V X7R | 0603 SMD | `C1604` | MPU-6050 Charge Pump Filter Capacitor | **Basic** |
| 30 | **C15..C18** | 4 | 22nF 50V X7R | 0603 SMD | `C302021` | Motor Brush RF Noise Commutation Snubbers | **Basic** |

**BOM Sourcing Metrics**:
- **Total Components**: 64
- **Unique Part Types**: 30
- **Basic Parts**: 23 lines (57 components, $0 feeder fee)
- **Extended Parts**: 7 lines (7 components, $21 feeder fee total)
- **Through-Hole Soldering**: 0 pins (100% SMT assembly)

---

## 5. JLCPCB Fabrication & Assembly Ordering Guide

When ordering PCBs and PCBA through the JLCPCB online portal:

1. **Board Settings**:
   - Dimensions: `100.64 mm x 100.00 mm`
   - Layers: `2 Layers`
   - PCB Thickness: `1.6 mm`
   - PCB Color: `Green` (or desired color)
   - Surface Finish: `ENIG` (strongly recommended due to 0.50 mm pitch QFN-24 MPU-6050 and USB-C pads; Lead-Free HASL is acceptable)
   - Copper Weight: `1 oz`
2. **Panel By JLCPCB**:
   - Because the drone chassis has irregular arm profiles and motor cutouts, select **"Panel by JLCPCB"** with **5.0 mm tooling rails on 2 sides** (stamp holes / mouse-bites) so the automated SMT pick-and-place conveyor can clamp the board.
3. **SMT Assembly**:
   - Choose **"Top Side"** SMT assembly (all 64 components are on `F.Cu`).
   - Upload the generated CPL file (`build/CopperPilotDrone-cpl.csv`) and BOM file (`build/CopperPilotDrone-bom.csv`).
   - In the JLCPCB component alignment preview, confirm orientation of the MPU-6050 (Pin 1 dot), diodes (cathodes), and polarized ICs.

---

## 6. Build, Verification & Export Commands

All PCB verification checks, rule validation, and fabrication exports are automated via `make` inside `pcb/`:

```bash
# Run automated 32-point hardware test suite (PyTest)
make test

# Run KiCad CLI Electrical Rule Check (asserts 0 errors)
make erc

# Run KiCad CLI Design Rule Check with zone refill & parity (asserts 0 errors, 0 unconnected)
make drc

# Generate complete JLCPCB manufacturing release bundle (Gerbers, Drill, CPL, BOM, PDFs, Release Zip)
make fab

# Generate individual manufacturing deliverables
make gerbers       # RS-274X Gerbers for top/bottom copper, mask, silk, and Edge.Cuts
make drill         # Excellon NC drill files (metric, PTH + NPTH)
make cpl           # SMT pick-and-place component centroid file (CPL)
make bom           # Manufacturing BOM with 100% LCSC part mappings
make pdf           # Full schematic and PCB layer documentation PDFs
make d356          # IPC-D-356 electrical test netlist

# Clean intermediate build outputs and caches
make clean
```
