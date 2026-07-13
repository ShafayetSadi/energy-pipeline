#!/usr/bin/env python3
"""Render the energy-node analog front-end as a thesis-ready schematic.

The figure mirrors the KiCad schematic and the two SPICE models:

- voltage channel: J1/R1/T1/R2/R5/C2 -> PA0
- current channel: SCT-013-030/J2/R7/R6/C3 -> PA1
- shared midpoint: R3/R4/C1 -> V_BIAS
- controller connection: PA0/PA1/3V3/GND -> Nucleo-F429ZI with
  STM32F429ZIT6 MCU shown explicitly

Run from any directory with:
    uv run --with schemdraw python firmware/hardware/schematic.py

Writes energy_node_schematic.svg and energy_node_schematic.png beside this file.
"""

from pathlib import Path
import shutil
import subprocess

import schemdraw
import schemdraw.elements as elm


OUTDIR = Path(__file__).resolve().parent

SECTION = '#1f4e79'
MUTED = '#475569'
BORDER = '#94a3b8'
PANEL = '#f8fafc'
SAFETY = '#b91c1c'

d = schemdraw.Drawing()
d.config(unit=1.7, fontsize=10, lw=1.5)


def text(x, y, value, *, size=10, color='black'):
    """Place left-aligned explanatory text at an absolute coordinate."""
    d.add(
        elm.Label()
        .at((x, y))
        .label(value, fontsize=size, color=color, halign='left', valign='center')
    )


def panel(x, y, width, height, title, subtitle):
    """Draw a lightly bounded functional block with a plain-language heading."""
    d.add(
        elm.Rect((0, 0), (width, height), fill=PANEL, lw=1)
        .at((x, y))
        .color(BORDER)
    )
    text(x + 0.35, y + height - 0.38, title, size=13, color=SECTION)
    text(x + 0.35, y + height - 0.78, subtitle, size=9, color=MUTED)


# ================= functional blocks =================
panel(
    0,
    6.85,
    18,
    4.35,
    '1. Voltage sensing channel',
    '230 V AC -> current limiting -> galvanic isolation and scaling -> low-pass filter -> PA0',
)
panel(
    0,
    2.25,
    18,
    4.15,
    '2. Current sensing channel',
    'Load conductor -> SCT-013-030 clamp and internal burden -> low-pass filter -> PA1',
)
panel(
    0,
    -2.6,
    8.55,
    4.4,
    '3. Shared ADC bias',
    '3.3 V divider creates the 1.65 V midpoint used by both channels',
)
panel(
    8.95,
    -2.6,
    9.05,
    4.4,
    '4. STM32 controller interface',
    'Nucleo-F429ZI development board with STM32F429ZIT6 MCU',
)


# ================= voltage channel =================
d += (
    vsrc := elm.SourceSin()
    .up()
    .at((1.0, 7.75))
    .length(1.75)
)
text(0.35, 9.82, 'J1: 230 V AC, 50 Hz', size=8)
d += elm.Line().right(0.45).at(vsrc.end)
d += elm.Resistor().right().length(1.7).label('R1\n100 kΩ, 1 W', loc='bottom', fontsize=7)
d += elm.Line().right(0.35)
d += (
    xf := elm.Transformer(t1=5, t2=5, core=True)
    .right()
    .anchor('p1')
)
text(3.1, 10.02, 'T1  ZMPT101B\n2 mA : 2 mA isolated', size=8)
d += elm.Line().at(xf.p2).left(0.45).tox(vsrc.start)
d += elm.Line().toy(vsrc.start)

# T1 secondary: R2 is the burden; R5/C2 filter the PA0 signal.
d += elm.Line().at(xf.s1).right(0.8)
d += (v_burden_top := elm.Dot())
d += elm.Resistor().right().length(1.65).label('R5  1 kΩ', loc='top', fontsize=9)
d += elm.Line().right(0.35)
d += (pa0_node := elm.Dot())
d += (
    c2 := elm.Capacitor()
    .down()
    .at(pa0_node.start)
    .length(1.15)
    .label('C2\n100 nF', loc='right', fontsize=9)
)
d += elm.Ground().at(c2.end)
d += elm.Line().at(pa0_node.start).right(0.45)
d += elm.Tag(width=2.25).right().label('PA0  voltage ADC', fontsize=9, color=SECTION)

d += (
    r2 := elm.Resistor()
    .down()
    .at(v_burden_top.start)
    .length(1.65)
    .label('R2 burden\n330 Ω, 0.1%', loc='left', fontsize=7)
)
d += elm.Line().at(xf.s2).right(0.8).toy(r2.end)
d += elm.Line().at(r2.end).right(2.2)
d += elm.Tag(width=1.45).right().label('V_BIAS', fontsize=9, color=SECTION)

text(12.1, 8.2, 'R5 + C2\nAnti-alias low-pass\nfc ≈ 1.6 kHz', size=8, color=MUTED)
text(
    12.1,
    9.7,
    'SAFETY: J1 is mains voltage.\nUse rated isolation, protection,\nclearances, and enclosure.',
    size=8,
    color=SAFETY,
)


# ================= current channel =================
d += (
    ct := elm.Transformer(t1=2, t2=6, core=True)
    .right()
    .at((3.1, 3.35))
)
text(0.35, 4.7, 'J2 — two-pin SCT sensor jack', size=8)
d += elm.Line().at(ct.p1).left(1.15).label('load conductor\nthrough clamp', loc='left', fontsize=9)
d += elm.Line().at(ct.p2).left(1.15)

d += elm.Line().at(ct.s1).right(0.8)
d += (i_burden_top := elm.Dot())
d += elm.Resistor().right().length(1.65).label('R6  1 kΩ', loc='top', fontsize=9)
d += elm.Line().right(0.35)
d += (pa1_node := elm.Dot())
d += (
    c3 := elm.Capacitor()
    .down()
    .at(pa1_node.start)
    .length(1.15)
    .label('C3\n100 nF', loc='right', fontsize=9)
)
d += elm.Ground().at(c3.end)
d += elm.Line().at(pa1_node.start).right(0.45)
d += elm.Tag(width=2.25).right().label('PA1  current ADC', fontsize=9, color=SECTION)

d += (
    r7 := elm.Resistor()
    .down()
    .at(i_burden_top.start)
    .length(1.65)
    .label('R7 internal\n66.7 Ω', loc='left', fontsize=7)
)
d += elm.Line().at(ct.s2).right(0.8).toy(r7.end)
d += elm.Line().at(r7.end).right(2.2)
d += elm.Tag(width=1.45).right().label('V_BIAS', fontsize=9, color=SECTION)

text(11.7, 5.05, 'SCT-013-030 external clamp\n2000 : 1; 1 V output at 30 A', size=8, color=MUTED)
text(11.7, 4.15, 'R7 is the internal 66.7 Ω burden.\nDo not add a second external burden.', size=8, color=MUTED)
text(11.7, 3.15, 'R6 + C3 match the voltage-channel\nfilter to preserve phase alignment.', size=8, color=MUTED)


# ================= midpoint bias =================
d += (vdd := elm.Vdd().at((1.5, 0.5)).label('3V3', fontsize=9))
d += elm.Resistor().down().at(vdd.start).length(0.9)
d += (bias := elm.Dot())
d += elm.Resistor().down().at(bias.start).length(0.9)
d += elm.Ground()
text(0.35, 0.05, 'R3  10 kΩ', size=7)
text(0.35, -0.85, 'R4  10 kΩ', size=7)

d += elm.Line().at(bias.start).right(1.1)
d += (
    c1 := elm.Capacitor(polar=True)
    .down()
    .length(0.95)
    .label('C1\n10 µF', loc='right', fontsize=8)
)
d += elm.Ground().at(c1.end)
d += elm.Line().at(bias.start).right(3.25)
d += elm.Tag(width=1.75).right().label('V_BIAS  1.65 V', fontsize=9, color=SECTION)

text(4.35, -1.8, 'V_BIAS shifts bipolar AC waveforms\ninto the STM32 ADC\'s 0-3.3 V range.', size=7, color=MUTED)


# ================= Nucleo-F429ZI / STM32F429ZIT6 =================
mcu = (
    elm.Ic(
        size=(4.8, 2.2),
        pins=[
            elm.IcPin(name='PA0 (ADC1_IN0)', side='left', slot='4/4', anchorname='PA0', lblsize=7),
            elm.IcPin(name='PA1 (ADC1_IN1)', side='left', slot='3/4', anchorname='PA1', lblsize=7),
            elm.IcPin(name='3V3', side='left', slot='2/4', anchorname='V33', lblsize=7),
            elm.IcPin(name='GND', side='left', slot='1/4', anchorname='GNDP', lblsize=7),
        ],
        edgepadW=0.8,
        edgepadH=0.6,
    )
    .at((11.75, -1.35))
)
d += mcu

# Show the controller explicitly while keeping the Nucleo board as the
# implemented hardware boundary.  The full 144-pin Nucleo circuitry is an
# off-the-shelf development board and would obscure the sensing front end.
d.add(
    elm.Rect((0, 0), (2.15, 0.95), fill='white', lw=1)
    .at((13.62, -0.82))
    .color(SECTION)
)
text(13.8, -0.36, 'U1  STM32F429ZIT6\nArm Cortex-M4 MCU', size=7, color=SECTION)
text(12.15, 0.58, 'Nucleo-F429ZI development board', size=7, color=MUTED)

d += elm.Line().at(mcu.PA0).left(0.35)
d += elm.Tag(width=1.1).left().label('PA0', fontsize=8, color=SECTION)
d += elm.Line().at(mcu.PA1).left(0.35)
d += elm.Tag(width=1.1).left().label('PA1', fontsize=8, color=SECTION)
d += elm.Line().at(mcu.V33).left(0.35)
d += elm.Tag(width=1.1).left().label('3V3', fontsize=8, color=SECTION)
d += elm.Line().at(mcu.GNDP).left(0.55)
d += elm.Ground()

text(
    9.3,
    -2.25,
    'Board-level abstraction: only thesis-relevant STM32 connections are shown.',
    size=8,
    color=MUTED,
)


# ================= output =================
svg_path = OUTDIR / 'energy_node_schematic.svg'
png_path = OUTDIR / 'energy_node_schematic.png'
d.save(str(svg_path))
mutool = shutil.which('mutool')
if mutool is None:
    raise RuntimeError('mutool is required to rasterize the generated SVG as PNG')
subprocess.run(
    [mutool, 'draw', '-r', '180', '-o', str(png_path), str(svg_path)],
    check=True,
)
print(f'wrote {svg_path.name} and {png_path.name}')
