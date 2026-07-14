# Analog Front-End — Circuit Design & SPICE Simulation

> ⚠️ **Describes the earlier design** (SCT-013-030 current sensor, raw ZMPT101B
> transformer, Nucleo-F429ZI, 5 kHz). The current build (see `../PLAN.md`) uses
> **ACS712-5A** as the primary current sensor, the **ZMPT101B module** (onboard
> op-amp + gain pot), a **Black Pill STM32F411**, and 3.2 kHz sampling. The
> methodology below is reusable, but the specific circuit and numbers will be
> revised **after bench-testing the real modules** — simulating the modules from
> datasheets before measuring them would document fiction.

This directory covers the part of the IoT node no simulator can emulate:
the analog sensing circuit between the mains and the STM32's ADC pins.
The circuit is designed in full, simulated in **ngspice**, and its simulated
ADC waveforms are fed through the same math the firmware runs
(`blackpill-node/app/metrology.c: metrology_compute`) to verify the whole
measurement chain.

## Circuit overview (see `energy_node_schematic.svg`)

Two galvanically isolated sensor channels, both centered on a shared
1.65 V mid-rail bias (R3/R4 divider + C1) so the AC signals fit the
STM32's 0–3.3 V ADC range:

| Channel | Sensor | Transfer | ADC pin |
|---|---|---|---|
| Voltage | ZMPT101B (2 mA:2 mA voltage CT) + R1 100 kΩ limiter + R2 330 Ω burden | 230 Vrms → 0.76 Vrms | PA0 |
| Current | SCT-013-030 split-core CT (2000:1, internal burden, 1 V @ 30 A) | 10 Arms → 0.33 Vrms | PA1 |

Each channel passes through an identical 1 kΩ / 100 nF anti-aliasing RC
(fc ≈ 1.6 kHz, matched so both channels get the same phase shift — this
matters for real-power accuracy). Firmware samples at 5 kHz.

## How to read the KiCad schematic

Read the numbered blocks from top to bottom:

1. **Voltage sensing:** J1 accepts the mains sample, R1 limits current, T1
   provides isolation, R2 converts the transformer output to a voltage, and
   R5/C2 filter the signal before it reaches **PA0**.
2. **Current sensing:** J2 accepts the SCT-013-030 clamp output. Its internal
   R7 burden produces a voltage, and R6/C3 filter it before **PA1**.
3. **ADC bias:** R3/R4 create **V_BIAS = 1.65 V** and C1 stabilizes it. The
   midpoint lets the STM32 ADC represent both halves of each AC waveform.
4. **STM32 controller interface:** the Nucleo-F429ZI development board and its
   on-board **STM32F429ZIT6** MCU are shown explicitly. Matching `PA0`, `PA1`,
   `3V3`, and `GND` net labels are electrically connected even when KiCad does
   not draw a long wire between the matching names; `V_BIAS` is the separate
   shared reference net for the two sensor channels. Only the
   thesis-relevant board connections are expanded; the off-the-shelf Nucleo's
   complete 144-pin support circuitry is intentionally abstracted. The small
   power-flag symbols by J3 only tell KiCad that 3V3 and GND are supplied; they
   are not physical components.

The component prefix indicates its type: `J` = connector, `R` = resistor,
`C` = capacitor, and `T` = transformer/sensor. J1 is a mains-voltage input and
requires appropriately rated isolation, protection, clearances, and enclosure;
it is not a breadboard circuit.

## Files

- `kicad/` — proper KiCad 7 project of the same circuit
  (`energy-node.kicad_sch`, generated reproducibly by `gen_schematic.py`).
  Netlist-verified: every net matches `spice/*.cir` (PA0 ← R5/C2,
  PA1 ← R6/C3, V_BIAS ties both sensor cold ends to the R3/R4/C1 bias).
  The A4 layout includes numbered explanations for thesis readers. Export
  PDF/SVG with `kicad-cli sch export pdf energy-node.kicad_sch`,
  or open in KiCad (eeschema) to edit or continue to PCB layout.
- `schematic.py` — draws the four-block publication figure
  `energy_node_schematic.{svg,png}` using Schemdraw and MuPDF (`mutool`)
- `spice/zmpt101b_frontend.cir` — voltage channel, ngspice
- `spice/sct013_frontend.cir` — current channel, ngspice
- `spice/verify_chain.py` — closes the loop: loads the SPICE ADC-node
  waveforms, applies the firmware's bias-removal → calibration → RMS/power
  math, and compares against the true 230 V / 10 A / PF 0.95 stimulus.
  Also renders `frontend_waveforms.png` for the thesis.

## Run it

```sh
# From the repository root: regenerate the publication SVG and PNG
uv run --with schemdraw python firmware/hardware/schematic.py

# Run the circuit simulations and firmware-equivalent verifier
cd firmware/hardware/spice
ngspice -b zmpt101b_frontend.cir     # prints RMS/max/min/bias at PA0
ngspice -b sct013_frontend.cir       # same for PA1
python3 verify_chain.py              # pass/fail table + waveform figure
```

Result (design-value calibration, no per-unit trimming):

| quantity | true | recovered | error |
|---|---|---|---|
| V_rms | 230 V | 226.8 V | −1.4 % |
| I_rms | 10 A | 9.90 A | −1.0 % |
| P | 2185 W | 2131 W | −2.5 % |
| PF | 0.950 | 0.949 | −0.1 % |

The residual errors come from transformer magnetizing losses in the model —
exactly the class of error that per-device calibration constants absorb on
real hardware (the firmware's `CAL_V_SCALE`/`CAL_I_SCALE` in
`blackpill-node/config.h` would be trimmed against a reference meter).

## Design notes / lessons captured from simulation

- **Bias-referenced, not AC-coupled:** both secondaries are isolated, so
  their cold ends tie directly to the 1.65 V rail. An earlier AC-coupled
  version (series cap + resistor to bias) lost ~9 % of amplitude into the
  filter load and took seconds to settle — the SPICE run caught both.
- **Headroom:** the 330 Ω burden puts 230 Vrms at 0.58–2.72 V on PA0,
  clipping only above ~280 Vrms mains.
- **Phase realism:** a too-small magnetizing inductance in the ZMPT model
  added a 6° phase lead that corrupted the simulated power factor by 3.6 % —
  visible in the verifier, fixed in the model. The same effect exists in the
  real part (it's why ZMPT101B is specified as a *precision* transformer).

## Honesty note for the thesis

This is a circuit-level SPICE validation of the front-end design plus a
numerical replication of the firmware's sample processing. It is **not**
a co-simulation: the firmware's `metrology_compute` math and the SPICE
circuit run in separate tools, joined at the ADC-sample boundary.
Component tolerances, ADC quantization noise, and sensor non-linearity are
future hardware work.
