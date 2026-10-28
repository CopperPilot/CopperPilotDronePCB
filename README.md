# CopperPilot Drone: 2-Layer ESP32-S3 Micro Quadcopter

[![Hardware Status](https://img.shields.io/badge/KiCad-v10.0.3-brightgreen.svg)](pcb/)
[![DRC Status](https://img.shields.io/badge/DRC-Zero%20Errors%20%7C%20100%25%20Routed-brightgreen.svg)](pcb/)
[![JLCPCB Compatible](https://img.shields.io/badge/Fab-JLCPCB%202--Layer-orange.svg)](pcb/README.md)
[![Firmware](https://img.shields.io/badge/ESP--IDF-v5.1+-blue.svg)](firmware/)
[![Tests](https://img.shields.io/badge/Tests-PyTest%20%2B%20Unity%20Native-success.svg)](firmware/tests/)

An ultra-compact, high-performance, single-board Quad-X micro drone flight controller and integrated airframe built on a 2-layer FR-4 PCB. Powered by an Espressif ESP32-S3 microcontroller, the drone hosts its own standalone Wi-Fi access point and responsive web application, streaming low-latency flight commands and real-time telemetry over WebSockets to any smartphone or computer without requiring mobile apps or specialized RC transmitters.

---

## System Architecture

```
                    +----------------------------------------------------+
                    |                    Power System                    |
                    | USB-C (J1) -> MCP73833T-AMI/UN (IC1) Charger (303mA)
                    |                 |                                  |
                    | 1S LiPo (J3) -> AO3401 (U2) Power Path -> SW1 Switch
                    |                                             |      |
                    |                             TPS79633 3.3V LDO (U3) |
                    +---------------------------------------------|------+
                                                                  | +3.3V Rail
+------------------------+      I2C (400 kHz)       +-------------v------+
|        MPU-6500        |<------------------------>|     ESP32-S3       |
| 6-DOF IMU (Gyro+Accel) |  GPIO8 (SDA), GPIO9 (SCL)|  Dual-Core 240 MHz |
| GPIO10 (Data Ready INT)|------------------------->|  8MB Flash/PSRAM   |
+------------------------+                          +--+---+---+---+-----+
                                                       |   |   |   |
                                20 kHz Ultrasonic PWM: |   |   |   |
                    GPIO4 (M1), GPIO5 (M2), GPIO6 (M3), GPIO7 (M4) |
                                                       |   |   |   |
+------------------------------------------------------v---v---v---v-----+
|                          Actuation Subsystem                           |
| 4x SI2302DS N-Ch MOSFETs (T1-T4) + 1N5819WS Flyback Diodes (D2-D5)     |
| 4x 8520 Brushed Coreless Motors (J2, J5, J6, J4) in Quad-X Layout       |
+------------------------------------------------------------------------+
```

---

## Hardware Specifications

- **Chassis & Form Factor**: 100.0 mm x 100.0 mm integrated airframe with 45° diagonal arms and a 118.8 mm motor-to-motor wheelbase.
- **Motor Mounts**: 4 precision C-clamp cutouts directly in `Edge.Cuts` (8.80 mm ID) engineered to friction-fit standard 8520 (8.5 mm x 20 mm) brushed coreless DC motors.
- **Flight Controller MCU**: Espressif ESP32-S3-WROOM-1-N8R8 (dual-core 32-bit Xtensa LX7 @ 240 MHz, 512 KB SRAM, 8 MB Octal Flash, 8 MB Octal PSRAM).
- **Inertial Measurement Unit**: TDK InvenSense MPU-6500 (3x3 mm QFN-24) 6-axis gyroscope and accelerometer with on-chip hardware digital low-pass filtering (DLPF @ 42 Hz) and 500 Hz complementary AHRS attitude estimation.
- **Brushed Motor Drive**: 4 low-side SI2302CDS-T1-GE3 N-channel MOSFETs (20 V, 2.8 A, $R_{DS(on)} = 55\text{ m}\Omega$) driven by 20 kHz ultrasonic PWM to eliminate audible motor whine and prevent mechanical resonance.
- **Inductive Clamping & Filtering**: 4x 1N5819WS (PMEG4010EJ,115) 40 V 1 A Schottky flyback diodes (SOD-323) paired with series RC snubbers (22 nF 0603 ceramic capacitors `C15–C18` + 10 $\Omega$ 0603 damping resistors `R29–R32`) to suppress motor brush commutation arcing and inductive turn-off voltage spikes.
- **Power Management & Charging**:
  - Integrated Microchip MCP73833T-AMI/UN standalone linear Li-Po battery charger (MSOP-10) programmed to 303 mA charge rate via USB-C (`Rprog1 = 3.3 kΩ`, `R33 = 10 kΩ` THERM bias) with dedicated 10.1 µF `+5V` input decoupling (`C6`, `C7`).
  - AO3401A P-channel MOSFET ideal diode power-path mux automatically selects between USB `+5V` and `+BATT` battery power without dropping voltage or reverse-biasing the battery.
  - 3.3 V low-noise LDO regulator (`U3`, `TPS79633DCQR` / `ME6211C33M5G-N`) with 51 µF distributed ceramic bypass capacitance.
  - Battery voltage sensing via 100 kΩ / 100 kΩ precision resistor divider on ESP32-S3 `ADC1_CH0` (GPIO1).
- **RF Antenna Keepout**: Uninterrupted top and bottom copper isolation corridor (22.0 mm x 18.5 mm, including dedicated copper-pour keepout behind `U8` Pads 1 and 40) beneath the ESP32-S3 inverted-F PCB antenna to maximize SoftAP range and throughput.
- **Fabrication Standard**: 100% compliant with LionCircuits and JLCPCB standard 2-layer FR-4 manufacturing capabilities (0.20 mm min trace width, 0.15 mm min copper clearance, 0.68/0.35 mm signal vias, 0.80/0.40 mm power vias, 69 SMT components).

---

## Reference Design & Architectural Improvements

This flight controller builds upon the foundational architecture of the open-source **Circuit-Digest ESP-Drone** reference design, thoroughly addressing its electrical vulnerabilities, manufacturing incompatibilities, and firmware constraints through systematic hardware and software re-engineering:

| Engineering Domain | Circuit-Digest ESP-Drone Reference | CopperPilot ESP32-S3 Flight Controller |
| :--- | :--- | :--- |
| **Microcontroller Core** | ESP-WROOM-32 (Single Core App, 240 MHz) | **ESP32-S3-WROOM-1-N8R8** (Dual-Core Xtensa LX7 @ 240 MHz, 8MB Octal Flash, 8MB PSRAM) |
| **USB & Programming** | External CP2102N USB-UART bridge, dedicated crystals, and external programmer pins | **Native USB-JTAG & USB-CDC** directly on ESP32-S3 GPIO19/20; zero external bridge ICs required |
| **ESD / Transient Protection** | None (Direct USB-C D+/D- connections to IC) | **USBLC6-2SC6 TVS diode array** (< 5 mm trace length from USB-C receptacle) for full IEC 61000-4-2 compliance |
| **Motor Flyback Clamping** | Undersized 150 mA 1N4148W silicon switching diodes ($V_F \approx 1.0\text{ V}$) | **1A continuous (40V) 1N5819WS Schottky diodes** ($V_F \approx 0.45\text{ V}$) in SOD-323 package |
| **Commutation Snubbers** | None (or legacy 1.0 µF capacitors causing destructive inrush pulses) | **22 nF 0603 MLCC snubber networks** suppressing RF motor brush arcing with zero MOSFET current spike risk |
| **Schematic Integrity** | 533 legacy ERC warnings/errors (power flag conflicts, driving pins tied to GND) | **Zero ERC violations** (0 errors, 0 warnings); verified hierarchical power distribution |
| **DFM & Clearance Rules** | Disabled clearance checks; track-to-pad and via-to-via DRC violations | **Fully verified JLCPCB 2-Layer rules** (0.20 mm min trace, 0.1524 mm clearance, 0.60/0.30 mm vias) |
| **Panelization & Breakaway** | Manual depaneling with rough edges damaging ground copper | **72-hole NPTH mousebite perforation panel** (5 breakaway tabs) governed by custom `.kicad_dru` rules |
| **Flight Control Engine** | Monolithic single-threaded loop | **Dual-core deterministic 500 Hz flight loop** on Core 1 decoupled from Core 0 Wi-Fi/Web server |
| **Ground Plane & Thermal** | Broken, fragmented ground pours under high-current paths | **Continuous dual-layer ground pour** with > 120 stitching vias and 3x3 thermal relief matrix |
| **User Interface** | Dedicated mobile application / external RC controller | **Zero-install responsive Web UI** embedded in flash, streaming over WebSockets with virtual joysticks |
| **Mechanical Enclosure** | None (exposed electronics during flight) | **Parametric clip-on squircle 3D enclosure** with cantilever snap-fit hooks locking into bare FR-4 waist notches |

---

## Repository Structure

```
.
├── Makefile                        # Root build orchestrator (fmt, lint, test, coverage)
├── .clang-format                   # LLVM-based C/C++ style specification
├── .gitignore                      # Comprehensive Git exclusion rules
├── LICENSE                         # CERN Open Hardware Licence v2 - Permissive
├── README.md                       # High-level project architecture & overview
├── pcb/                            # KiCad EDA design files & automated test suite
│   ├── README.md                   # JLCPCB 2-layer stackup, DFM rules, thermal design, BOM
│   ├── Makefile                    # Hardware verification: erc, drc, test, gerbers, fab
│   ├── CopperPilotDrone.kicad_pro  # KiCad 10 project settings & netclasses
│   ├── CopperPilotDrone.kicad_sch  # 6-block schematic capture
│   ├── CopperPilotDrone.kicad_pcb  # 2-layer board layout (100% routed, 0 DRC errors)
│   ├── CopperPilotDrone.kicad_dru  # Custom DRC design rules
│   ├── sym-lib-table               # Symbol library mappings
│   ├── fp-lib-table                # Footprint library mappings
│   ├── libs/                       # Self-contained symbols, footprints, and 3D models
│   └── tests/                      # Automated 32-point pytest hardware verification suite
│       ├── conftest.py             # S-expression AST parsers & KiCad CLI fixtures
│       └── test_pcb.py             # Geometry, connectivity, DFM, and circuit parity tests
├── firmware/                       # ESP32-S3 flight control firmware
│   ├── README.md                   # Firmware architecture, pinout, PID tuning, failsafes
│   ├── Makefile                    # Targets: fmt, lint, test, coverage, build, flash
│   ├── CMakeLists.txt              # ESP-IDF project configuration
│   ├── main/                       # Application entry point & FreeRTOS dual-core tasks
│   ├── components/
│   │   ├── hal/                    # Hardware abstraction layer & native mock stubs
│   │   ├── avionics/               # MPU-6050 driver, AHRS fusion, PID, motor mixer
│   │   ├── networking/             # Wi-Fi SoftAP, HTTP web server, WebSocket telemetry
│   │   └── web_ui/                 # Responsive single-page touch joystick controller HUD
│   └── tests/                      # Native desktop unit test suite (Unity framework)
│       ├── Makefile                # Host test runner with gcov/lcov code coverage
│       ├── unity/                  # Unity C unit test framework
│       ├── test_pid.c              # PID step response, filtering, and windup tests
│       ├── test_ahrs.c             # Complementary filter angle convergence tests
│       ├── test_motor_mixer.c      # Quad-X mixing and anti-clip saturation tests
│       └── test_battery_failsafe.c # Battery ADC scaling and cutoff threshold tests
├── case/                           # Parametric 3D squircle enclosure & collision verification
│   ├── README.md                   # Mechanical specs, clearance maps, snap-fit assembly guide
│   ├── Makefile                    # Targets: generate, test, collision, fmt, lint, clean
│   ├── pcb_parser.py               # KiCad PCB geometry & snap-off tab constraint extractor
│   ├── generator.py                # CadQuery parametric squircle lofts, snap hooks & branding
│   ├── generate_case.py            # CLI generator synthesizing STL, STEP, and explosion GIF
│   ├── collision.py                # Trimesh & KiCad 3D STL collision and clearance verifier
│   └── tests/                      # Automated 18-point pytest enclosure verification suite
│       ├── conftest.py             # Enclosure mesh fixtures & test configuration
│       └── test_enclosure.py       # Manifoldness, volume, snap mechanics, cutout alignments
└── review/                         # Release audit, validation suite & JLCPCB readiness
    ├── READINESS.md                # 8-point hardware release sign-off matrix
    ├── ISSUES.md                   # Prioritized hardware issue register & remediations
    ├── DECISIONS.md                # Formal engineering waivers and trade-off records
    ├── SURVEY.md                   # Multi-disciplinary hardware audit & risk analysis
    ├── PROGRESS.md                 # Validation and remediation milestone tracking
    ├── verify.sh                   # Automated 11-point acceptance test suite runner
    ├── index.html                  # Interactive visual review report & layer diff viewer
    └── renders/                    # High-resolution layer renders, 3D views, and diff crops
```

---

## Quickstart & Commands

This project includes a unified top-level `Makefile` providing standardized verification targets across hardware design, embedded firmware, and 3D mechanical enclosure:

```bash
# Run automated code and schematic formatting checks
make fmt

# Run static analysis and linting across firmware, PCB hardware, and 3D enclosure
make lint

# Run all test suites: native firmware unit tests + PCB hardware suite + 3D enclosure suite
make test

# Run 3D collision detection and clearance queries against KiCad board STL
make collision

# Synthesize parametric 3D enclosure CAD models (case_top.stl, case_bottom.stl)
make build-case

# Generate code coverage reports (gcov/lcov for firmware, pytest-cov for PCB)
make coverage

# Cross-compile target ESP32-S3 firmware with ESP-IDF
make build-fw

# Export JLCPCB manufacturing release bundle (Gerbers, drill, CPL, BOM zip)
make build-pcb

# Clean all build outputs and temporary test artifacts
make clean
```

---

## Operating Instructions

1. **Battery Connection**: Insert a 1S 3.7V 300–600 mAh LiPo battery into the central battery compartment and plug into the JST-PH 2.0mm header (`J3`).
2. **Power On**: Slide the power switch (`SW1`) to the ON position. The blue power LED (`LED1`) will illuminate solid.
3. **Sensor Calibration**: Place the drone on a flat, level surface for 2 seconds while the flight controller boots and performs zero-rate gyroscope bias calibration.
4. **Wi-Fi Connection**: On your smartphone, tablet, or laptop, connect to the Wi-Fi network:
   - **SSID**: `CopperPilot-Drone-XXXX` (where `XXXX` matches the ESP32 MAC address)
   - **Password**: `copperpilot` (Default, configurable)
5. **Launch Controller**: Open any modern web browser and navigate to `http://192.168.4.1`.
6. **Arm & Fly**:
   - Verify that the battery gauge indicates $> 3.7\text{ V}$ and the artificial horizon is level.
   - Tap the green **ARM** button (arming requires throttle at zero and pitch/roll within $\pm 10^\circ$).
   - Use the left virtual joystick for Throttle and Yaw, and the right joystick for Pitch and Roll.
   - Tap the red **EMERGENCY STOP** button or disarm at any time to instantly kill motor power.

---

## Manufacturing & JLCPCB Order Verification

This repository includes a deterministic verification suite and interactive HTML review deliverable:

```bash
# Run 11-point automated JLCPCB acceptance test suite
./review/verify.sh

# Open interactive visual diff, before/after crops, and issue register
xdg-open review/index.html
```

- **Fabrication Release Package:** Generated by `make -C pcb fab` in `pcb/build/gerbers.zip`, `pcb/build/CopperPilotDrone-cpl.csv`, and `pcb/build/CopperPilotDrone-bom.csv`.
- **Order Specification:** See `pcb/build/ORDER_SPEC.md` for exact quoting parameters.
- **Readiness Matrix:** See `review/READINESS.md` for the full definition of done audit.

---

## License & Safety Notice

This hardware design is licensed under the CERN Open Hardware Licence Version 2 - Permissive (CERN-OHL-P v2). The accompanying firmware and software are licensed under the MIT License. Always operate radio-controlled aircraft responsibly in open spaces away from people, pets, and obstacles. Never leave charging LiPo batteries unattended.
