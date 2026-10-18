# CopperPilot Drone: Hardware Validation & Review Deliverables

This directory contains the release validation deliverables, design decisions, formal engineering waivers, issue registers, visual diffs, and automated JLCPCB acceptance test framework for the **CopperPilot ESP32-S3 Drone Flight Controller**.

---

## Deliverables Index

- **[READINESS.md](READINESS.md)**: Hardware Release Readiness Sign-Off Matrix (100% Production Ready definition of done).
- **[ISSUES.md](ISSUES.md)**: Prioritized Hardware Review Issue Register (P0–P3 findings, root-cause analyses, calculations, and remediation verification).
- **[DECISIONS.md](DECISIONS.md)**: Engineering Decisions, Waivers, and Trade-Off Records (`DEC-001` through `DEC-006`).
- **[SURVEY.md](SURVEY.md)**: Comprehensive Multi-Disciplinary Hardware Survey & JLCPCB Manufacturing Audit.
- **[PROGRESS.md](PROGRESS.md)**: Validation and remediation milestone tracking and violation trend records.
- **[index.html](index.html)**: Interactive visual review dashboard with layer-by-layer visual diffs, before/after crops, and live filtering.
- **[verify.sh](verify.sh)**: Executable 11-point acceptance test suite runner (T1–T11).

---

## Running the Acceptance Verification Suite

To run the automated verification suite across all 11 criteria (ERC, DRC, JLCPCB rules, BOM completeness, fabrication outputs, issue register closure, and repo hygiene):

```bash
./review/verify.sh
```

To view the interactive visual report and layer diffs:

```bash
# Open in your default browser
xdg-open review/index.html
# or on macOS:
open review/index.html
```
