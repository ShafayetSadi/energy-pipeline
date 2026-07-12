#!/usr/bin/env python3
"""Full energy-node schematic: analog front-end -> Nucleo-F429ZI.

Draws the complete device circuit (both sensor channels, mid-rail bias
and MCU connections) as a publication-quality figure for the thesis.
Component values match the SPICE simulation in spice/*.cir.

Run:  <venv-with-schemdraw>/python schematic.py
Writes energy_node_schematic.svg and .png next to this file.
"""

import schemdraw
import schemdraw.elements as elm

d = schemdraw.Drawing()
d.config(unit=2.0, fontsize=10)

# ================= Nucleo-F429ZI (right side) =================
mcu = elm.Ic(
    pins=[
        elm.IcPin(name='PA0 (ADC1_IN0)', side='left', slot='4/4', anchorname='PA0'),
        elm.IcPin(name='PA1 (ADC1_IN1)', side='left', slot='3/4', anchorname='PA1'),
        elm.IcPin(name='3V3', side='left', slot='2/4', anchorname='V33'),
        elm.IcPin(name='GND', side='left', slot='1/4', anchorname='GNDP'),
        elm.IcPin(name='RJ45  (ETH)', side='right', slot='2/3'),
        elm.IcPin(name='USB  (ST-LINK / VCP)', side='right', slot='1/3'),
    ],
    edgepadW=1.2, edgepadH=1.0,
).at((16, 4)).label('Nucleo-F429ZI  (STM32F429ZIT6)', loc='top', fontsize=11)
d += mcu
d += elm.Line().at(mcu.V33).left(1.0)
d += elm.Vdd().label('3V3', loc='top')
d += elm.Line().at(mcu.GNDP).left(1.8)
d += elm.Line().down(0.8)
d += elm.Ground()

# ================= Voltage channel (top) =================
d += (vsrc := elm.SourceSin().up().at((0, 8)).length(2).label('mains\n230 V\n50 Hz', loc='left'))
d += elm.Line().right(0.8).at(vsrc.end)
d += (r1 := elm.Resistor().right().label('R1\n100 kΩ 1 W', loc='bottom'))
d += (xf := elm.Transformer(t1=5, t2=5).right().anchor('p1').label('T1  ZMPT101B\n2 mA : 2 mA', loc='top', ofst=0.4))
d += elm.Line().at(xf.p2).left(0.8).tox(vsrc.start)
d += elm.Line().toy(vsrc.start)

# secondary: hot end -> anti-alias RC -> PA0 ; cold end -> bias rail
d += elm.Line().at(xf.s1).right(0.6)
d += (rb1_top := elm.Dot())
d += (r5 := elm.Resistor().right().label('R5\n1 kΩ'))
d += (c2_node := elm.Dot())
d += (c2 := elm.Capacitor().down().length(1.6).label('C2\n100 nF', loc='bottom'))
d += elm.Ground().at(c2.end)
d += elm.Line().at(c2_node.start).right(0.5).toy(mcu.PA0).tox(mcu.PA0)
d += elm.Line().to(mcu.PA0)

d += (rb1 := elm.Resistor().down().at(rb1_top.start).length(2.2).label('R2 (burden)\n330 Ω  0.1 %', loc='bottom'))
d += elm.Line().at(xf.s2).right(0.6).toy(rb1.end)
d += (biasdot_v := elm.Dot().at(rb1.end))

# ================= Current channel (middle) =================
d += (ct := elm.Transformer(t1=2, t2=6).right().at((6.2, 1.5)).label('T2  SCT-013-030\n2000 : 1, split core', loc='top'))
d += elm.Line().at(ct.p1).left(0.8).label('load line conductor\n(through core)', loc='left')
d += elm.Line().at(ct.p2).left(0.8)

d += elm.Line().at(ct.s1).right(0.6)
d += (rbi_top := elm.Dot())
d += (r6 := elm.Resistor().right().label('R6\n1 kΩ'))
d += (c3_node := elm.Dot())
d += (c3 := elm.Capacitor().down().length(1.6).label('C3\n100 nF', loc='bottom'))
d += elm.Ground().at(c3.end)
d += elm.Line().at(c3_node.start).right(0.5).toy(mcu.PA1).tox(mcu.PA1)
d += elm.Line().to(mcu.PA1)

d += (rbi := elm.Resistor().down().at(rbi_top.start).length(2.2).label('R7 (burden)*\n66.7 Ω', loc='bottom'))
d += elm.Line().at(ct.s2).right(0.6).toy(rbi.end)
d += (biasdot_i := elm.Dot().at(rbi.end))

# ================= Mid-rail bias (bottom left) =================
d += (vdd := elm.Vdd().at((1.5, -3.2)).label('3V3'))
d += (r3 := elm.Resistor().down().at(vdd.start).label('R3\n10 kΩ'))
d += (bias := elm.Dot().label('V_BIAS = 1.65 V', loc='bottom', ofst=(0.9, -0.3)))
d += (r4 := elm.Resistor().down().at(bias.start).label('R4\n10 kΩ', loc='bottom'))
d += elm.Ground().at(r4.end)
d += elm.Line().at(bias.start).left(1.8)
d += (cb := elm.Capacitor().down().length(1.9).label('C1\n10 µF', loc='left', ofst=(0.1, -0.6)))
d += elm.Ground().at(cb.end)

# bias rail to both channel cold ends
d += elm.Line().at(bias.start).tox(biasdot_v.start)
d += (jv := elm.Dot())
d += elm.Line().at(jv.start).toy(biasdot_v.start)
d += elm.Line().at(jv.start).tox(biasdot_i.start)
d += elm.Line().toy(biasdot_i.start)

# ================= annotations =================
d += elm.Label().at((11, -7.0)).label(
    '* SCT-013-030 has its internal burden; R7 shown for the bare-CT variant.\n'
    'Anti-aliasing: fc = 1/(2π·1k·100n) ≈ 1.6 kHz; firmware samples at 5 kHz.',
    fontsize=9)

d.save('energy_node_schematic.svg')
d.save('energy_node_schematic.png', dpi=150)
print('wrote energy_node_schematic.{svg,png}')
