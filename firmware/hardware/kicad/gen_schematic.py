#!/usr/bin/env python3
"""Generate the energy-node KiCad 7 schematic (energy-node.kicad_sch).

The schematic mirrors spice/*.cir and energy_node_schematic.svg:
ZMPT101B voltage channel -> PA0, SCT-013-030 current channel -> PA1,
shared 1.65 V mid-rail bias, headers to the Nucleo-F429ZI.
The Nucleo block explicitly identifies its on-board STM32F429ZIT6 MCU while
keeping the off-the-shelf board circuitry as a readable abstraction.

Symbols are embedded verbatim from the system KiCad libraries, so the
file opens standalone. Run:  python3 gen_schematic.py
Then check:  kicad-cli sch export netlist energy-node.kicad_sch
"""

import argparse
import math
import re
import uuid
from pathlib import Path

LIBDIR = '/usr/share/kicad/symbols'


def grab_symbol(lib, name):
    txt = open(f'{LIBDIR}/{lib}.kicad_sym').read()
    i = txt.index(f'(symbol "{name}"')
    depth = 0
    j = i
    while True:
        if txt[j] == '(':
            depth += 1
        elif txt[j] == ')':
            depth -= 1
            if depth == 0:
                break
        j += 1
    blk = txt[i:j + 1]
    # qualify the symbol name with its library
    blk = blk.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    return blk


# symbol pin offsets in library coords (x right, y UP)
PINS = {
    'Device:R': {'1': (0, 3.81), '2': (0, -3.81)},
    'Device:C': {'1': (0, 3.81), '2': (0, -3.81)},
    'Device:C_Polarized': {'1': (0, 3.81), '2': (0, -3.81)},
    'Device:Transformer_1P_1S': {'1': (-10.16, 5.08), '2': (-10.16, -5.08),
                                 '3': (10.16, -5.08), '4': (10.16, 5.08)},
    'power:GND': {'1': (0, 0)},
    'power:+3V3': {'1': (0, 0)},
    'power:PWR_FLAG': {'1': (0, 0)},
    'Connector_Generic:Conn_01x02': {'1': (-5.08, 0), '2': (-5.08, -2.54)},
    'Connector_Generic:Conn_01x04': {'1': (-5.08, 2.54), '2': (-5.08, 0),
                                     '3': (-5.08, -2.54), '4': (-5.08, -5.08)},
}


def pin_pos(lib_id, num, x, y, rot):
    """Screen position of a pin. Schematic y grows DOWN."""
    px, py = PINS[lib_id][num]
    a = math.radians(rot)
    rx = px * math.cos(a) - py * math.sin(a)
    ry = px * math.sin(a) + py * math.cos(a)
    return (round(x + rx, 2), round(y - ry, 2))


symbols = []   # instance s-expressions
wires = []
labels = []
notes = []
graphics = []
used_libs = {}


def add(lib_id, ref, value, x, y, rot=0, ref_off=(2.54, 0), val_off=(2.54, 2.54)):
    used_libs[lib_id] = True
    u = uuid.uuid4()
    pins = ''.join(f'\n    (pin "{n}" (uuid {uuid.uuid4()}))' for n in PINS[lib_id])
    hide = ' hide' if lib_id.startswith('power:') else ''
    # counter-rotate text on rotated symbols so it stays horizontal
    prot = 90 if rot in (90, 270) else 0
    symbols.append(f'''  (symbol (lib_id "{lib_id}") (at {x} {y} {rot}) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid {u})
    (property "Reference" "{ref}" (at {x + ref_off[0]} {y + ref_off[1]} {prot})
      (effects (font (size 1.27 1.27)) (justify left){hide}))
    (property "Value" "{value}" (at {x + val_off[0]} {y + val_off[1]} {prot})
      (effects (font (size 1.27 1.27)) (justify left){hide}))
    (property "Footprint" "" (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "~" (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide)){pins}
    (instances (project "energy-node"
      (path "/00000000-0000-0000-0000-000000000000"
        (reference "{ref}") (unit 1)))))''')


def wire(p1, p2):
    wires.append(f'  (wire (pts (xy {p1[0]} {p1[1]}) (xy {p2[0]} {p2[1]}))'
                 f' (stroke (width 0) (type default)) (uuid {uuid.uuid4()}))')


def hwire(p, dx):
    p2 = (round(p[0] + dx, 2), p[1])
    wire(p, p2)
    return p2


def vwire(p, dy):
    p2 = (p[0], round(p[1] + dy, 2))
    wire(p, p2)
    return p2


def junction(p):
    labels.append(f'  (junction (at {p[0]} {p[1]}) (diameter 0) (color 0 0 0 0)'
                  f' (uuid {uuid.uuid4()}))')


def label(p, text, rot=0):
    labels.append(f'  (label "{text}" (at {p[0]} {p[1]} {rot}) (fields_autoplaced)'
                  f' (effects (font (size 1.27 1.27)) (justify left bottom))'
                  f' (uuid {uuid.uuid4()}))')


def note(p, text, size=1.6, bold=False):
    """Add human-readable documentation without changing electrical nets."""
    weight = ' bold' if bold else ''
    notes.append(
        f'  (text "{text}" (at {p[0]} {p[1]} 0)'
        f' (effects (font (size {size} {size}){weight}) (justify left bottom))'
        f' (uuid {uuid.uuid4()}))'
    )


def rectangle(start, end, width=0.254):
    """Add a non-electrical outline for a documented board or subassembly."""
    graphics.append(
        f'  (rectangle (start {start[0]} {start[1]}) (end {end[0]} {end[1]})'
        f' (stroke (width {width}) (type default)) (fill (type none))'
        f' (uuid {uuid.uuid4()}))'
    )


# ============================================================
# 1. Voltage channel: 230 V AC -> isolation/scaling -> filter -> PA0
# ============================================================
note((25, 30), '1. VOLTAGE SENSING CHANNEL', size=2.54, bold=True)
note((25, 34), '230 V AC -> galvanic isolation and scaling -> anti-alias filter -> PA0 voltage ADC')

add('Connector_Generic:Conn_01x02', 'J1', 'MAINS 230V AC', 35, 55, rot=180,
    ref_off=(-8.9, -5.1), val_off=(2.5, 7.6))
j1_hot = pin_pos('Connector_Generic:Conn_01x02', '2', 35, 55, 180)
j1_cold = pin_pos('Connector_Generic:Conn_01x02', '1', 35, 55, 180)

add('Device:R', 'R1', '100k 1W', 65, 52.46, rot=90,
    ref_off=(-3.8, -3.8), val_off=(-6.4, 3.8))
wire(j1_hot, (61.19, 52.46))
add('Device:Transformer_1P_1S', 'T1', 'ZMPT101B', 100, 57.54,
    ref_off=(-2.5, -8.9), val_off=(-6.4, 10.2))
wire((68.81, 52.46), (89.84, 52.46))
wire(j1_cold, (45, 55))
wire((45, 55), (45, 62.62))
wire((45, 62.62), (89.84, 62.62))

add('Device:R', 'R2', '330 0.1%', 125, 57.54,
    ref_off=(2.5, 1.3), val_off=(2.5, 3.8))
wire((110.16, 52.46), (125, 52.46))
wire((125, 52.46), (125, 53.73))
wire((110.16, 62.62), (125, 62.62))
wire((125, 62.62), (125, 61.35))

add('Device:R', 'R5', '1k', 145, 52.46, rot=90,
    ref_off=(-3.8, -3.8), val_off=(1.3, -3.8))
wire((125, 52.46), (141.19, 52.46))
add('Device:C', 'C2', '100n', 165, 58.81,
    ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire((148.81, 52.46), (165, 52.46))
wire((165, 52.46), (185, 52.46))
label((185, 52.46), 'PA0')
junction((165, 52.46))
wire((165, 52.46), (165, 55))
add('power:GND', '#PWR01', 'GND', 165, 68.97)
wire((165, 62.62), (165, 68.97))

p = vwire((125, 62.62), 5.08)
label(p, 'V_BIAS', rot=270)

note((105, 69), 'R2 converts the isolated transformer current into a measurable voltage.', size=1.35)
note((105, 72), 'R5 + C2 form a 1.6 kHz low-pass filter before the STM32 ADC.', size=1.35)
note((25, 80), 'SAFETY: J1 is mains voltage; use rated isolation, protection, and enclosure.',
     size=1.35, bold=True)

# ============================================================
# 2. Current channel: clamp output -> burden -> filter -> PA1
# ============================================================
note((25, 87), '2. CURRENT SENSING CHANNEL', size=2.54, bold=True)
note((25, 91), 'SCT-013-030 clamp output -> internal burden -> anti-alias filter -> PA1 current ADC')

add('Connector_Generic:Conn_01x02', 'J2', 'SCT-013-030 JACK', 35, 105, rot=180,
    ref_off=(-8.9, -5.1), val_off=(2.5, 7.6))
j2_hot = pin_pos('Connector_Generic:Conn_01x02', '2', 35, 105, 180)
j2_cold = pin_pos('Connector_Generic:Conn_01x02', '1', 35, 105, 180)

add('Device:R', 'R7', '66.7 internal', 105, 107.54,
    ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire(j2_hot, (105, 102.46))
wire((105, 102.46), (105, 103.73))
wire(j2_cold, (45, 105))
wire((45, 105), (45, 112.62))
wire((45, 112.62), (105, 112.62))
wire((105, 112.62), (105, 111.35))

add('Device:R', 'R6', '1k', 145, 102.46, rot=90,
    ref_off=(-3.8, -3.8), val_off=(1.3, -3.8))
wire((105, 102.46), (141.19, 102.46))
add('Device:C', 'C3', '100n', 165, 108.81,
    ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire((148.81, 102.46), (165, 102.46))
wire((165, 102.46), (185, 102.46))
label((185, 102.46), 'PA1')
junction((165, 102.46))
wire((165, 102.46), (165, 105))
add('power:GND', '#PWR02', 'GND', 165, 118.97)
wire((165, 112.62), (165, 118.97))

p = hwire((105, 112.62), 10.16)
label(p, 'V_BIAS')

note((105, 123), "R7 is the sensor's internal 66.7 ohm burden; do not add a second burden.", size=1.35)
note((105, 126), 'R6 + C3 match the voltage-channel filter so phase error stays aligned.', size=1.35)

# ============================================================
# 3. Shared 1.65 V ADC midpoint bias
# ============================================================
note((25, 137), '3. SHARED ADC BIAS (MIDPOINT)', size=2.54, bold=True)
note((25, 141), 'R3 and R4 make 1.65 V; C1 stabilizes it. This shifts both AC waveforms into the 0-3.3 V ADC range.',
     size=1.5)

add('power:+3V3', '#PWR03', '+3V3', 65, 148)
add('Device:R', 'R3', '10k', 65, 151.81,
    ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire((65, 155.62), (65, 158.16))
add('Device:R', 'R4', '10k', 65, 161.97,
    ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
add('power:GND', '#PWR04', 'GND', 65, 168.32)
wire((65, 165.78), (65, 168.32))
add('Device:C_Polarized', 'C1', '10u', 90, 161.97,
    ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire((65, 158.16), (90, 158.16))
add('power:GND', '#PWR05', 'GND', 90, 168.32)
wire((90, 165.78), (90, 168.32))
p = hwire((90, 158.16), 20)
label(p, 'V_BIAS')
note((105, 163), 'V_BIAS = 1.65 V reference for both sensor channels', size=1.35, bold=True)

# ============================================================
# 4. Nucleo-F429ZI board and its STM32F429ZIT6 MCU
# ============================================================
note((195, 132), 'Power-flag symbols are KiCad checks for supplied 3V3/GND; they are not physical parts.', size=1.25)
note((195, 137), '4. STM32 CONTROLLER INTERFACE', size=2.54, bold=True)
note((195, 141), 'NUCLEO-F429ZI development board with on-board STM32F429ZIT6 MCU', size=1.5, bold=True)
note((195, 145), 'Board-level abstraction: PA0 = voltage ADC; PA1 = current ADC.', size=1.25)

rectangle((192, 147), (270, 162), width=0.5)
rectangle((196, 150), (216, 160), width=0.4)
note((198, 153.5), 'U1  STM32F429ZIT6', size=1.5, bold=True)
note((198, 157), 'Arm Cortex-M4 MCU', size=1.25)
note((198, 159.5), 'on Nucleo-F429ZI board', size=1.1)

add('Connector_Generic:Conn_01x04', 'J3', 'ADC/POWER HEADER', 235, 157, rot=180,
    ref_off=(-8.9, -8.9), val_off=(-7.6, -6.35))
j3 = {n: pin_pos('Connector_Generic:Conn_01x04', n, 235, 157, 180) for n in '1234'}
p = hwire(j3['1'], 10.16); label(p, 'PA0')
p = hwire(j3['2'], 10.16); label(p, 'PA1')
p = hwire(j3['3'], 17.78)
add('power:+3V3', '#PWR06', '+3V3', p[0], p[1])
add('power:PWR_FLAG', '#FLG01', 'PWR_FLAG', p[0] - 7.62, p[1])
p = hwire(j3['4'], 17.78)
add('power:GND', '#PWR07', 'GND', p[0], p[1])
add('power:PWR_FLAG', '#FLG02', 'PWR_FLAG', p[0] - 7.62, p[1])

# ============================================================
# emit file
# ============================================================
libblocks = '\n'.join(grab_symbol(*lib_id.split(':')) for lib_id in used_libs)

out = f'''(kicad_sch (version 20230121) (generator gen_schematic.py)
  (uuid 00000000-0000-0000-0000-000000000000)
  (paper "A4")
  (title_block (title "Energy node - analog front-end") (date "2026-07-13")
    (rev "1") (company "BSc thesis")
    (comment 1 "SPICE-verified analog front-end"))
  (lib_symbols
{libblocks}
  )
{chr(10).join(wires)}
{chr(10).join(labels)}
{chr(10).join(graphics)}
{chr(10).join(notes)}
{chr(10).join(symbols)}
  (sheet_instances (path "/" (page "1")))
)
'''
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', default='energy-node.kicad_sch', help='output schematic path')
args = parser.parse_args()
output = Path(args.output)
output.write_text(out)
print(f'wrote {output}')
