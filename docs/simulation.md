# Simulating the Energy Node

There is **no single simulator** for the whole device — it spans an analog mains
circuit, STM32 firmware, a Wi-Fi/MQTT uplink, and the cloud pipeline, each a
different domain. This document covers the **integrated device simulation in
Proteus VSM** (STM32 firmware + sensor stimulus + virtual instruments) and how
it fits the other simulation layers.

> Since the thesis rests on **real measurement**, simulation is a *supplement*:
> it lets you develop and demonstrate the firmware before parts arrive and
> before touching mains. Present it as "firmware logic and front-end validated
> in simulation, then confirmed on real hardware against a reference meter" —
> not as a substitute for measured results.

## Simulation layers (pick what you need)

| Layer | Tool | Status |
| --- | --- | --- |
| Metrology math (Vrms/Irms/P/PF) | host unit tests | done — `make -C firmware/blackpill-node/test check` |
| Analog front-end (sensor → divider → ADC pin) | ngspice / LTspice / Falstad | optional, for a figure + 3.3 V check |
| **Integrated device (firmware + sensors + scope)** | **Proteus VSM** | this document |
| ESP-01 Wi-Fi / MQTT bridge | Wokwi + local Mosquitto | optional |
| Cloud pipeline (gateway → DB → Grafana → LSTM) | existing Docker stack + mock publisher | already runs |

---

## Proteus VSM — integrated device simulation

Proteus runs the **real compiled `.elf`** on a virtual STM32F411 and lets you
inject analog stimulus and watch the results on virtual instruments — the
closest thing to "see the device work" before hardware.

**Availability:** Proteus is commercial (Labcenter). Most Bangladeshi
universities hold a lab license — check before buying. You need a version with
the **STM32/ARM Cortex-M VSM** models.

### What it does and does *not* model

- **Does:** run your firmware, feed the ADC pins an analog waveform, show
  RMS/power on a virtual scope and the UART output on a virtual terminal, verify
  timing (TIM/ADC/DMA) and program flow.
- **Does not:** reproduce the ZMPT101B/ACS712 **modules** themselves, sensor
  non-linearity, ADC quantization noise, or transformer phase error. You inject
  an *idealized* scaled sine, so treat accuracy numbers as firmware-logic
  validation, not metrology accuracy.

### Setup steps

1. **New project** → schematic capture. Place component **STM32F411CE** (or the
   nearest F411 VSM model in the library — `Simulation > ...ARM`).
2. **Configure the part:** double-click the MCU → set **Program File** to your
   build's `blackpill-node.elf` (from STM32CubeIDE, `Debug/blackpill-node.elf`),
   and set the **crystal frequency** to match your clock (e.g. 25 MHz HSE / 96 MHz
   HCLK as in `firmware/blackpill-node/cubemx-checklist.md`).
3. **Inject the sensor signals** (stand-ins for ZMPT101B / ACS712 outputs):
   - Add two **AC voltage sources** (`Generators > SINE`).
   - Voltage channel → **PA0**: amplitude = the ADC-pin swing your front-end
     produces at nominal mains. With the ZMPT module biased at 1.65 V and tuned
     for ~1.2 V peak, set **offset 1.65 V, amplitude 1.2 V, 50 Hz**.
   - Current channel → **PA1**: model a load. For a resistive load, **same phase**
     as the voltage source; for a lagging load, add a phase (e.g. 60° → PF 0.5).
     Set **offset 1.65 V, amplitude** per your ACS712 divider (e.g. 0.5–1.0 V).
   - Keep both offsets/amplitudes so the pin stays within **0–3.3 V** — this also
     visually confirms the front-end scaling from `firmware/hardware-build.md §3`.
4. **Match calibration to the injected signal.** The `CAL_V_SCALE` / `CAL_I_SCALE`
   in `config.h` were chosen for the real sensors. For the sim, either:
   - set the generator amplitudes to what the real sensors would output (so the
     existing scales give correct volts/amps), **or**
   - temporarily set sim-specific scale factors and note it — do **not** commit
     sim-tuned constants as the hardware calibration.
5. **Watch the outputs:**
   - **Virtual Oscilloscope** on PA0/PA1 → confirm clean, in-range sines.
   - **Virtual Terminal** on **PA9 (USART1_TX)**, 115200 8N1 → you should see the
     `energy/stm32_0001/telemetry {...}` JSON lines your firmware emits
     (`esp01_publish` output) once per second.
6. **Run** (▶). Verify:
   - the JSON `voltage_v` / `current_a` / `power_w` track the injected amplitudes,
   - `power_factor`/power responds to the current-source phase,
   - timing is stable (no ADC/DMA stalls).

### The ESP-01 in Proteus

Proteus has no ESP-01 MQTT model. Two honest options:

- **Stop at the UART boundary:** the Virtual Terminal *is* the ESP-01's input.
  Seeing correct JSON lines there proves the STM32 side end-to-end. State this
  boundary explicitly in the thesis.
- **Bridge sim → real broker:** point Proteus's virtual COM port at a host serial
  port (com0com / a USB-UART) and run a tiny PC script that reads the lines and
  publishes to your local Mosquitto — exercising the *whole* pipeline with
  simulated firmware. (This is what the mock publisher in `simulator/` already
  does for pure-cloud testing.)

---

## Supporting layers

### Analog front-end (ngspice / LTspice / Falstad)

For a thesis figure and a 3.3 V-safety check, model one channel:
`sensor source → resistor divider → RC anti-alias → ADC node`, and confirm the
node stays within 0–3.3 V at maximum mains. Falstad (browser,
<https://www.falstad.com/circuit/>) is quickest for a clean diagram; LTspice for
a more rigorous DC/AC sweep. Verify the **ACS712 ~0.65× divider** (`firmware/hardware-build.md §3`)
never lets the pin exceed 3.3 V at 5 A.

### Cloud pipeline (no hardware)

The Docker stack (gateway → TimescaleDB → Grafana → LSTM) runs without any node.
Use the existing `simulator/` publisher (or a small script that replays the
Proteus UART JSON) to push telemetry into Mosquitto and watch it flow through to
Grafana — end-to-end validation of everything downstream of the node.

---

## Recommended minimum

1. **host unit tests** — metrology correctness (already passing).
2. **Proteus** — integrated firmware demo + thesis figure/video.
3. **Falstad/LTspice** — one front-end figure proving ADC-range safety.

Skip full analog+firmware+cloud co-simulation; it is not expected at undergrad
level and is a time sink. The real hardware run against a reference meter is the
result that matters.
