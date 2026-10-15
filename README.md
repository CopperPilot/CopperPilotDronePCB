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
                    | USB-C (J1) ---> TP4056 (IC1) Charger (364mA)       |
                    |                 |                                  |
                    | 1S LiPo (J3) -> AO3401 (U2) Power Path -> SW1 Switch
                    |                                             |      |
                    |                               ME6211 3.3V LDO (U3) |
                    +---------------------------------------------|------+
                                                                  | +3.3V Rail
+------------------------+      I2C (400 kHz)       +-------------v------+
|       MPU-6050         |<------------------------>|     ESP32-S3       |
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
- **Inertial Measurement Unit**: InvenSense MPU-6050 6-axis gyroscope and accelerometer with on-chip hardware digital low-pass filtering (DLPF @ 42 Hz) and 500 Hz complementary AHRS attitude estimation.
- **Brushed Motor Drive**: 4 low-side SI2302DS N-channel MOSFETs (20 V, 2.8 A, $R_{DS(on)} = 55\text{ m}\Omega$) driven by 20 kHz ultrasonic PWM to eliminate audible motor whine and prevent mechanical resonance.
- **Inductive Clamping & Filtering**: 4x 1N5819WS 40 V 1 A Schottky flyback diodes (SOD-323) paired with 22 nF 0603 ceramic snubber capacitors suppress motor brush commutation arcing and inductive turn-off voltage spikes.
- **Power Management & Charging**:
  - Integrated TP4056 linear Li-Po battery charger programmed to 364 mA charge rate via USB-C.
  - AO3401 P-channel MOSFET ideal diode power-path mux automatically selects between USB VBUS and battery power without dropping voltage or reverse-biasing the battery.
  - MicrOne ME6211C33M5G-N 3.3 V 500 mA ultra-low-noise LDO regulator with 51 µF distributed ceramic bypass capacitance.
  - Battery voltage sensing via 100 kΩ / 100 kΩ precision resistor divider on ESP32-S3 `ADC1_CH0` (GPIO1).
- **RF Antenna Keepout**: Uninterrupted top and bottom copper isolation corridor (22.0 mm x 18.5 mm) beneath the ESP32-S3 inverted-F PCB antenna to maximize SoftAP range and throughput.
- **Fabrication Standard**: 100% compliant with JLCPCB standard 2-layer FR-4 manufacturing capabilities (0.20 mm min trace width, 0.15 mm min copper clearance, 0.60/0.30 mm signal vias, 0.80/0.40 mm power vias, 100% SMT components).

---

## Repository Structure

```
~/Projects/CopperPilotDronePCB/
├── Makefile                        # Root build orchestrator (fmt, lint, test, coverage)
├── .clang-format                   # LLVM-based C/C++ style specification
├── .gitignore                      # Comprehensive Git exclusion rules
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
│   └── tests/                      # Automated 21-point pytest hardware verification suite
│       ├── conftest.py             # S-expression AST parsers & KiCad CLI fixtures
│       └── test_pcb.py             # Geometry, connectivity, DFM, and circuit parity tests
└── firmware/                       # ESP32-S3 flight control firmware
    ├── README.md                   # Firmware architecture, pinout, PID tuning, failsafes
    ├── Makefile                    # Targets: fmt, lint, test, coverage, build, flash
    ├── CMakeLists.txt              # ESP-IDF project configuration
    ├── main/                       # Application entry point & FreeRTOS dual-core tasks
    ├── components/
    │   ├── hal/                    # Hardware abstraction layer & native mock stubs
    │   ├── avionics/               # MPU-6050 driver, AHRS fusion, PID, motor mixer
    │   ├── networking/             # Wi-Fi SoftAP, HTTP web server, WebSocket telemetry
    │   └── web_ui/                 # Responsive single-page touch joystick controller HUD
    └── tests/                      # Native desktop unit test suite (Unity framework)
        ├── Makefile                # Host test runner with gcov/lcov code coverage
        ├── unity/                  # Unity C unit test framework
        ├── test_pid.c              # PID step response, filtering, and windup tests
        ├── test_ahrs.c             # Complementary filter angle convergence tests
        ├── test_motor_mixer.c      # Quad-X mixing and anti-clip saturation tests
        └── test_battery_failsafe.c # Battery ADC scaling and cutoff threshold tests
    └── case/                           # Parametric 3D squircle enclosure & collision verification
        ├── README.md                   # Mechanical specs, clearance maps, snap-fit assembly guide
        ├── Makefile                    # Targets: generate, test, collision, fmt, lint, clean
        ├── pcb_parser.py               # KiCad PCB geometry & snap-off tab constraint extractor
        ├── generator.py                # CadQuery parametric squircle lofts, snap hooks & branding
        ├── generate_case.py            # CLI generator synthesizing STL, STEP, and explosion GIF
        ├── collision.py                # Trimesh & KiCad 3D STL collision and clearance verifier
        └── tests/                      # Automated 18-point pytest enclosure verification suite
            ├── conftest.py             # Enclosure mesh fixtures & test configuration
            └── test_enclosure.py       # Manifoldness, volume, snap mechanics, cutout alignments
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

## License & Safety Notice

This hardware design and firmware are released under the MIT License. Always operate radio-controlled aircraft responsibly in open spaces away from people, pets, and obstacles. Never leave charging LiPo batteries unattended.
