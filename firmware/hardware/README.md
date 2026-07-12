# Analog Front-End — Circuit Design & SPICE Simulation

This directory covers the part of the IoT node that Renode cannot emulate:
the analog sensing circuit between the mains and the STM32's ADC pins.
The circuit is designed in full, simulated in **ngspice**, and its simulated
ADC waveforms are fed through the same math the firmware runs
(`app/sensor_sim.c: sensor_measure`) to verify the whole measurement chain.

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

## Files

- `schematic.py` — draws `energy_node_schematic.{svg,png}` (schemdraw)
- `spice/zmpt101b_frontend.cir` — voltage channel, ngspice
- `spice/sct013_frontend.cir` — current channel, ngspice
- `spice/verify_chain.py` — closes the loop: loads the SPICE ADC-node
  waveforms, applies the firmware's bias-removal → calibration → RMS/power
  math, and compares against the true 230 V / 10 A / PF 0.95 stimulus.
  Also renders `frontend_waveforms.png` for the thesis.

## Run it

```sh
cd spice
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
real hardware (the firmware's `V_CAL`/`I_CAL` would be trimmed against a
reference meter).

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
a co-simulation: the compiled firmware binary (validated in Renode) and the
SPICE circuit run in separate tools, joined at the ADC-sample boundary.
Component tolerances, ADC quantization noise, and sensor non-linearity are
future hardware work.
