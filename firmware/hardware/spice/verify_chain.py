#!/usr/bin/env python3
"""Close the loop between the SPICE front-end simulation and the firmware.

Reads the ADC-node waveforms dumped by ngspice (adc_v.txt, adc_i.txt),
applies the same processing the firmware performs on ADC samples
(remove mid-rail bias -> scale by calibration constant -> RMS / mean(v*i),
see blackpill-node/app/metrology.c:metrology_compute), and compares the recovered
voltage / current / power against the true values driven into the circuit.

Run after both ngspice simulations:
    ngspice -b zmpt101b_frontend.cir
    ngspice -b sct013_frontend.cir
    python3 verify_chain.py
Writes frontend_waveforms.png and prints a pass/fail table.
"""

import numpy as np

# --- ground truth driven into the SPICE circuits ---
TRUE_VRMS = 230.0        # mains
TRUE_IRMS = 10.0         # load current
PHI_DEG = 18.2           # current lag -> PF ~ 0.95
TRUE_P = TRUE_VRMS * TRUE_IRMS * np.cos(np.radians(PHI_DEG))

# --- calibration constants (design values, as the firmware would use) ---
# V channel: 230 Vrms -> 2.3 mA * 330R = 0.759 Vrms at the ADC node
V_CAL = 230.0 / 0.759            # mains volts per ADC volt
# I channel: SCT-013-030 datasheet 30 A -> 1 V
I_CAL = 30.0 / 1.0               # amps per ADC volt
BIAS = 1.65                      # mid-rail

def load(fname):
    d = np.loadtxt(fname)
    return d[:, 0], d[:, 1]

tv, v_adc = load("adc_v.txt")
ti, i_adc = load("adc_i.txt")

# Resample onto a common 5 kHz grid (the firmware's sampling rate),
# analysing the final 100 ms (5 mains cycles x ... = steady state).
t0, t1 = 0.2, 0.3
fs = 5000.0
t = np.arange(t0, t1, 1.0 / fs)
v = np.interp(t, tv, v_adc)
i = np.interp(t, ti, i_adc)

# --- firmware-equivalent processing (sensor_measure) ---
v_sig = (v - BIAS) * V_CAL
i_sig = (i - BIAS) * I_CAL
vrms = np.sqrt(np.mean(v_sig ** 2))
irms = np.sqrt(np.mean(i_sig ** 2))
p_real = np.mean(v_sig * i_sig)
pf = p_real / (vrms * irms)

rows = [
    ("V_rms [V]", TRUE_VRMS, vrms),
    ("I_rms [A]", TRUE_IRMS, irms),
    ("P [W]", TRUE_P, p_real),
    ("PF", np.cos(np.radians(PHI_DEG)), pf),
]
print(f"{'quantity':<12}{'true':>10}{'recovered':>12}{'error %':>9}")
ok = True
for name, true, got in rows:
    err = 100.0 * (got - true) / true
    ok &= abs(err) < 2.5
    print(f"{name:<12}{true:>10.3f}{got:>12.3f}{err:>8.2f}%")
print("PASS" if ok else "FAIL", "(all errors < 2.5%)" if ok else "")

# --- thesis figure ---
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
ms = (t - t0) * 1e3
axes[0].plot(ms, v, lw=1, color="tab:blue")
axes[0].axhline(BIAS, ls="--", lw=0.8, color="gray")
axes[0].axhline(3.3, ls=":", lw=0.8, color="red")
axes[0].axhline(0.0, ls=":", lw=0.8, color="red")
axes[0].set_ylabel("ADC PA0 [V]")
axes[0].set_title("Voltage channel (ZMPT101B front-end), 230 Vrms mains")
axes[1].plot(ms, i, lw=1, color="tab:orange")
axes[1].axhline(BIAS, ls="--", lw=0.8, color="gray")
axes[1].set_ylabel("ADC PA1 [V]")
axes[1].set_xlabel("time [ms]")
axes[1].set_title("Current channel (SCT-013-030 front-end), 10 Arms, PF 0.95")
axes[1].set_xlim(0, 60)
fig.tight_layout()
fig.savefig("frontend_waveforms.png", dpi=150)
print("wrote frontend_waveforms.png")
