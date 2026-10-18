# CopperPilot Drone Firmware: ESP32-S3 Flight Controller

[![Platform](https://img.shields.io/badge/Platform-ESP32--S3%20Xtensa%20LX7-red.svg)](https://www.espressif.com)
[![Framework](https://img.shields.io/badge/Framework-ESP--IDF%20v5.1+-blue.svg)](https://docs.espressif.com/projects/esp-idf/)
[![Flight Loop](https://img.shields.io/badge/Flight%20Loop-500%20Hz%20(2.0%20ms)-brightgreen.svg)](#avionics-stabilization-loop-core-1)
[![PWM Frequency](https://img.shields.io/badge/Motor%20PWM-20%20kHz%20Ultrasonic-orange.svg)](#quad-x-motor-mixing--actuation)
[![Native Unit Tests](https://img.shields.io/badge/Tests-Unity%20Native-success.svg)](tests/)
[![Avionics Coverage](https://img.shields.io/badge/Coverage->90%25%20Avionics-brightgreen.svg)](tests/)

High-performance, low-latency flight control firmware engineered for the 2-layer ESP32-S3 CopperPilot micro drone. The firmware utilizes the dual-core 240 MHz Xtensa LX7 processor to decouple hard real-time avionics stabilization from wireless communication, hosting an autonomous Wi-Fi SoftAP and responsive single-page browser flight controller.

---

## 1. Dual-Core Real-Time Architecture

The firmware assigns dedicated FreeRTOS tasks to each CPU core to guarantee zero timing jitter in the flight stabilization loop regardless of Wi-Fi traffic or WebSocket packet processing.

```
+-------------------------------------------------------------------------+
|                              ESP32-S3                                   |
|                                                                         |
|  +--------------------------------+   +-------------------------------+ |
|  |     Core 1: Avionics Loop      |   |   Core 0: Networking & System | |
|  |     (Priority 5, 500 Hz)       |   |      (Priority 2, 50 Hz)      | |
|  +--------------------------------+   +-------------------------------+ |
|  | - MPU-6050 400kHz I2C Burst    |   | - 802.11n Wi-Fi SoftAP        | |
|  | - 180° PCB Mounting Remap      |   | - Asynchronous HTTP Server    | |
|  | - 500 Hz Complementary AHRS    |   | - 50 Hz WebSocket Streaming   | |
|  | - Cascaded Angle/Rate PID      |   | - Battery ADC Oversampling    | |
|  | - Quad-X Mixer + Anti-Clip     |   | - Watchdog Failsafe Monitor   | |
|  | - 20 kHz Ultrasonic LEDC PWM   |   | - Gzipped Web UI Asset Server | |
|  +--------------------------------+   +-------------------------------+ |
+-------------------------------------------------------------------------+
```

---

## 2. Hardware Pin Allocation & Schematic Parity

Every GPIO pin used by the flight controller matches the KiCad schematic (`CopperPilotDrone.kicad_sch`):

| Function | Pin Name | ESP32-S3 GPIO | Electrical Interface & Hardware Topology |
| :--- | :--- | :---: | :--- |
| **Battery Voltage Sense** | `/ADC_BAT` | **GPIO1** | `ADC1_CH0` via 100k/100k precision resistor divider ($V_{batt} = 2.0 \times V_{pin}$). |
| **Motor 1 (Rear-Left / SW)**| `/MOT_1` | **GPIO4** | Gate of T1 (SI2302DS, SOT-23), 10k pulldown R18, D2 (1N5819WS), C15 (22nF), J2. CCW. |
| **Motor 2 (Front-Left / NW)**| `/MOT_2` | **GPIO5** | Gate of T2 (SI2302DS, SOT-23), 10k pulldown R19, D4 (1N5819WS), C17 (22nF), J5. CW. |
| **Motor 3 (Front-Right / NE)**|`/MOT_3` | **GPIO6** | Gate of T3 (SI2302DS, SOT-23), 10k pulldown R20, D5 (1N5819WS), C18 (22nF), J6. CCW. |
| **Motor 4 (Rear-Right / SE)**| `/MOT_4` | **GPIO7** | Gate of T4 (SI2302DS, SOT-23), 10k pulldown R21, D3 (1N5819WS), C16 (22nF), J4. CW. |
| **IMU I2C Data** | `/SDA` | **GPIO8** | MPU-6050 SDA (Pin 24), 4.7k pull-up resistor R12 to +3.3V. |
| **IMU I2C Clock** | `/SCL` | **GPIO9** | MPU-6050 SCL (Pin 23), 4.7k pull-up resistor R14 to +3.3V. |
| **IMU Interrupt** | `/MPU_INT` | **GPIO10**| MPU-6050 Data Ready interrupt (Pin 12), push-pull active-high. |
| **IMU Address Select** | `/MPU_AD0` | Hardware GND | MPU-6050 AD0 (Pin 9) tied to GND via 4.7k pull-down R13 $\implies$ 7-bit Address `0x68`. |
| **Boot Mode Switch** | `/IO0` | **GPIO0** | 10k pull-up R11 to +3.3V, momentary switch SW3 to GND. High = Boot, Low = Flash. |
| **Hardware Reset** | `/EN` | **CHIP_PU** | 10k pull-up R10, 1.0 µF capacitor C11 (2.87 ms RC startup delay), switch SW2. |

---

## 3. Sensor Fusion & Attitude Estimation (AHRS)

### MPU-6050 Configuration & I2C Burst Read
- **I2C Bus**: Fast-Mode 400 kHz on GPIO8 (SDA) and GPIO9 (SCL).
- **Digital Low-Pass Filter (DLPF)**: Configured to 42 Hz bandwidth (`CONFIG = 0x03`) to reject high-frequency motor commutator vibration harmonics.
- **Full Scale Ranges**: Gyroscope set to $\pm 2000^\circ/\text{s}$ (16.4 LSB/dps), Accelerometer set to $\pm 8\text{g}$ (4096 LSB/g).
- **Burst Transaction**: 14 consecutive registers read from `0x3B` (`ACCEL_XOUT_H`) through `0x48` (`GYRO_ZOUT_L`) in a single DMA transaction taking $\approx 360\text{ µs}$.

### Coordinate Remapping for 180° PCB Mounting
Because the MPU-6050 is rotated 180° on the PCB relative to standard forward heading, raw sensor readings are transformed into the standard aerospace right-handed body frame (Forward = $+X$, Right = $+Y$, Down = $+Z$):

$$\begin{aligned}
a_{x\_body} &= -a_{y\_raw} \\
a_{y\_body} &= -a_{x\_raw} \\
a_{z\_body} &= +a_{z\_raw} \\
\omega_{roll} &= -\omega_{x\_raw} - \text{bias}_x \\
\omega_{pitch} &= -\omega_{y\_raw} - \text{bias}_y \\
\omega_{yaw} &= +\omega_{z\_raw} - \text{bias}_z
\end{aligned}$$

### Complementary Filter
A 500 Hz complementary filter ($\Delta t = 0.002\text{ s}$, $\alpha = 0.98$) fuses integrated gyroscope angular rates with tilt angles derived from the gravity vector:

$$\theta_{accel} = \text{atan2}\left(-a_x, \sqrt{a_y^2 + a_z^2}\right), \quad \phi_{accel} = \text{atan2}(a_y, a_z)$$
$$\text{angle}_{k} = \alpha \left(\text{angle}_{k-1} + \omega \cdot \Delta t\right) + (1 - \alpha) \text{angle}_{accel}$$

---

## 4. Cascaded Dual-Loop PID Control

Flight stabilization uses a cascaded dual-loop architecture separating attitude angle tracking from angular rate damping:

```
Target Angle (Web UI)
        |
        v
+------------------+  Desired Rate   +------------------+  Torque Command   +-------------+
| Outer Angle Loop |---------------->| Inner Rate Loop  |------------------>| Quad-X      |
|     (250 Hz)     |   (±180 deg/s)  |     (500 Hz)     |   (Duty Counts)   | Motor Mixer |
+------------------+                 +------------------+                   +-------------+
        ^                                     ^
        | Measured Angle                      | Measured Rate
     (AHRS)                                (Gyroscope)
```

- **Outer Angle Loop (250 Hz)**: Proportional controller converts attitude error into target angular rate, clamped to $\pm 180^\circ/\text{s}$.
- **Inner Rate Loop (500 Hz)**: Full PID controller with anti-windup integrator clamping and a first-order 30 Hz low-pass filter on the derivative term to eliminate motor vibration amplification.
- **Default PID Gains**:
  - Roll Axis: Angle $K_p = 4.5$; Rate $K_p = 1.2$, $K_i = 0.05$, $K_d = 0.015$, $I_{max} = 200$.
  - Pitch Axis: Angle $K_p = 4.5$; Rate $K_p = 1.2$, $K_i = 0.05$, $K_d = 0.015$, $I_{max} = 200$.
  - Yaw Axis: Rate $K_p = 2.0$, $K_i = 0.10$, $K_d = 0.0$, $I_{max} = 150$.

---

## 5. Quad-X Motor Mixing & Actuation

The four 8520 brushed motors are driven by 20 kHz ultrasonic PWM via the ESP32-S3 LEDC peripheral with 10-bit resolution ($0\text{ to }1023$ counts). The 20 kHz frequency sits well above the human audible spectrum, eliminating motor whine and preventing coreless motor mechanical resonance.

### Mixing Equations
For normalized throttle $T \in [0, 1000]$ and torque commands $U_R$ (roll), $U_P$ (pitch), $U_Y$ (yaw):

$$\begin{aligned}
\text{PWM}_1 (\text{Rear-Left, CCW, Pin 4}) &= T + U_P + U_R + U_Y \\
\text{PWM}_2 (\text{Front-Left, CW, Pin 5}) &= T - U_P + U_R - U_Y \\
\text{PWM}_3 (\text{Front-Right, CCW, Pin 6}) &= T - U_P - U_R + U_Y \\
\text{PWM}_4 (\text{Rear-Right, CW, Pin 7}) &= T + U_P - U_R - U_Y
\end{aligned}$$

### Anti-Clip Protection (Throttle Prioritization)
If stabilization torque commands push any motor duty cycle above the 1000 count ceiling ($\max(\text{PWM}_i) > 1000$), the excess $\Delta = \max(\text{PWM}_i) - 1000$ is subtracted from all four motors equally. This maintains full roll and pitch stabilization authority even at 100% throttle.

### Battery Sag Voltage Compensation
Because coreless motor thrust scales with $V^2$, battery voltage sag ($4.2\text{ V} \to 3.5\text{ V}$) diminishes throttle response. The mixer applies an active voltage compensation factor:

$$k_v = \left(\frac{V_{nominal}}{V_{battery}}\right)^2 = \left(\frac{4.0\text{ V}}{V_{battery}}\right)^2 \quad (\text{clamped between } 1.0\text{ and } 1.35)$$

---

## 6. Multi-Tier Safety Failsafes

The flight controller implements five layers of automated safety interlocks:

1. **Arming Safety Interlock**: Arming is rejected unless throttle is $< 5\%$, roll and pitch tilt are within $\pm 10^\circ$ of level, and gyro zero-rate bias calibration has completed.
2. **Wi-Fi Loss Auto-Descent (300 ms)**: If no valid control packet is received over WebSockets for $> 300\text{ ms}$, the flight controller enters auto-descent, holding level attitude with 15% throttle.
3. **Wi-Fi Loss Emergency Kill (500 ms)**: If packet loss exceeds $500\text{ ms}$, the drone immediately disarms and kills all motor PWM to 0%.
4. **Crash / Inversion Kill**: If roll or pitch angle exceeds $\pm 60^\circ$ (e.g. wall collision or flip), the drone disarms within $< 2\text{ ms}$.
5. **Low-Voltage Cutoff (LVC)**: If battery voltage drops below $3.30\text{ V}$ for $> 2.0\text{ seconds}$, motors are disarmed to prevent destructive LiPo pouch cell over-discharge.

---

## 7. Responsive Web Controller & Telemetry

The flight controller hosts an embedded single-page application directly out of ESP32-S3 Flash (< 14 KB):
- **SoftAP Wi-Fi**: SSID `CopperPilot-Drone-XXXX` (where `XXXX` is the lower 2 bytes of the MAC address), password `copperpilot`.
- **IP Address**: `http://192.168.4.1`.
- **Dual Virtual Joysticks**:
  - Left Stick: Throttle (springless vertical) and Yaw (auto-centering horizontal).
  - Right Stick: Pitch (auto-centering vertical) and Roll (auto-centering horizontal).
- **Real-Time HUD**: Artificial horizon Canvas rendering roll and pitch, color-coded battery gauge, per-motor PWM duty bar graphs, and large red emergency stop button.
- **WebSocket Protocol**: 50 Hz bidirectional JSON/binary streaming over `/ws`.

---

## 8. Development, Testing & Build Commands

```bash
# Run native desktop unit tests (no hardware or ESP-IDF required)
make test

# Generate code coverage report using gcov
make coverage

# Check C formatting compliance (clang-format)
make fmt-check

# Format all C sources in-place
make fmt

# Static analysis and syntax linting (clang / cppcheck)
make lint

# Cross-compile target firmware for ESP32-S3 with ESP-IDF
make build

# Flash firmware over native USB-CDC (GPIO19/GPIO20)
make flash

# Open serial debug monitor
make monitor

# Clean build and test outputs
make clean
```
