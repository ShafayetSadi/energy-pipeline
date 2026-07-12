#!/usr/bin/env python3
"""Generate the energy-node KiCad 7 schematic (energy-node.kicad_sch).

The schematic mirrors spice/*.cir and energy_node_schematic.svg:
ZMPT101B voltage channel -> PA0, SCT-013-030 current channel -> PA1,
shared 1.65 V mid-rail bias, headers to the Nucleo-F429ZI.

Symbols are embedded verbatim from the system KiCad libraries, so the
file opens standalone. Run:  python3 gen_schematic.py
Then check:  kicad-cli sch erc energy-node.kicad_sch
"""

import math
import re
import uuid

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


# ============================================================
# Voltage channel: rows y=36.83 (hot) / 46.99 (cold), grid 1.27
# ============================================================
add('Connector_Generic:Conn_01x02', 'J1', 'MAINS 230V', 40, 39.37, rot=180,
    ref_off=(-8.9, -5.1), val_off=(-16.5, 7.6))
j1_hot = pin_pos('Connector_Generic:Conn_01x02', '2', 40, 39.37, 180)   # (45.08, 36.83)
j1_cold = pin_pos('Connector_Generic:Conn_01x02', '1', 40, 39.37, 180)  # (45.08, 39.37)

add('Device:R', 'R1', '100k 1W', 55.88, 36.83, rot=90, ref_off=(-3.8, -3.8), val_off=(-5.1, 3.8))
wire(j1_hot, (52.07, 36.83))
add('Device:Transformer_1P_1S', 'T1', 'ZMPT101B', 76.2, 41.91,
    ref_off=(-2.5, -8.9), val_off=(-6.4, 10.2))
wire((59.69, 36.83), (66.04, 36.83))            # R1 -> T1 primary top
wire(j1_cold, (48.26, 39.37))
wire((48.26, 39.37), (48.26, 46.99))
wire((48.26, 46.99), (66.04, 46.99))            # -> T1 primary bottom

# secondary: hot row 36.83 from pin4, cold row 46.99 from pin3
add('Device:R', 'R2', '330 0.1%', 91.44, 41.91, ref_off=(2.5, 1.3), val_off=(2.5, 3.8))
wire((86.36, 36.83), (91.44, 36.83))
wire((91.44, 36.83), (91.44, 38.1))             # stub to R2.1
wire((86.36, 46.99), (91.44, 46.99))
wire((91.44, 46.99), (91.44, 45.72))            # stub to R2.2

add('Device:R', 'R5', '1k', 99.06, 36.83, rot=90, ref_off=(-3.8, -3.8), val_off=(1.3, -3.8))
wire((91.44, 36.83), (95.25, 36.83))
add('Device:C', 'C2', '100n', 107.95, 43.18, ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire((102.87, 36.83), (107.95, 36.83))
wire((107.95, 36.83), (114.3, 36.83))
label((114.3, 36.83), 'PA0')
junction((107.95, 36.83))
wire((107.95, 36.83), (107.95, 39.37))          # down to C2.1
add('power:GND', '#PWR01', 'GND', 107.95, 49.53)
wire((107.95, 46.99), (107.95, 49.53))

p = vwire((91.44, 46.99), 3.81)
label(p, 'V_BIAS', rot=270)

# ============================================================
# Current channel: rows y=64.77 (hot) / 74.93 (cold)
# ============================================================
add('Connector_Generic:Conn_01x02', 'J2', 'SCT-013-030 jack', 40, 67.31, rot=180,
    ref_off=(-8.9, -5.1), val_off=(-8.9, 7.6))
j2_hot = pin_pos('Connector_Generic:Conn_01x02', '2', 40, 67.31, 180)   # (45.08, 64.77)
j2_cold = pin_pos('Connector_Generic:Conn_01x02', '1', 40, 67.31, 180)  # (45.08, 67.31)

add('Device:R', 'R7', '66.7 (internal)', 76.2, 69.85, ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire(j2_hot, (76.2, 64.77))
wire((76.2, 64.77), (76.2, 66.04))              # stub to R7.1
wire(j2_cold, (48.26, 67.31))
wire((48.26, 67.31), (48.26, 74.93))
wire((48.26, 74.93), (76.2, 74.93))
wire((76.2, 74.93), (76.2, 73.66))              # stub to R7.2

add('Device:R', 'R6', '1k', 86.36, 64.77, rot=90, ref_off=(-3.8, -3.8), val_off=(1.3, -3.8))
wire((76.2, 64.77), (82.55, 64.77))
add('Device:C', 'C3', '100n', 95.25, 71.12, ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire((90.17, 64.77), (95.25, 64.77))
wire((95.25, 64.77), (101.6, 64.77))
label((101.6, 64.77), 'PA1')
junction((95.25, 64.77))
wire((95.25, 64.77), (95.25, 67.31))            # down to C3.1
add('power:GND', '#PWR02', 'GND', 95.25, 77.47)
wire((95.25, 74.93), (95.25, 77.47))

p = hwire((76.2, 74.93), 3.81)
label(p, 'V_BIAS')

# ============================================================
# Bias generator
# ============================================================
add('power:+3V3', '#PWR03', '+3V3', 40, 106.68)
add('Device:R', 'R3', '10k', 40, 110.49, ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire((40, 114.3), (40, 116.84))
add('Device:R', 'R4', '10k', 40, 120.65, ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
add('power:GND', '#PWR04', 'GND', 40, 127)
wire((40, 124.46), (40, 127))
add('Device:C_Polarized', 'C1', '10u', 52.07, 120.65, ref_off=(2.5, -1.3), val_off=(2.5, 1.3))
wire((40, 116.84), (52.07, 116.84))
add('power:GND', '#PWR05', 'GND', 52.07, 127)
wire((52.07, 124.46), (52.07, 127))
p = hwire((52.07, 116.84), 7.62)
label(p, 'V_BIAS')

# ============================================================
# Nucleo header + power flags
# ============================================================
add('Connector_Generic:Conn_01x04', 'J3', 'to Nucleo-F429ZI CN9/CN8', 130, 110, rot=180,
    ref_off=(-8.9, -8.9), val_off=(-26.7, 11.4))
j3 = {n: pin_pos('Connector_Generic:Conn_01x04', n, 130, 110, 180) for n in '1234'}
p = hwire(j3['1'], 7.62); label(p, 'PA0')
p = hwire(j3['2'], 7.62); label(p, 'PA1')
p = hwire(j3['3'], 12.7)
add('power:+3V3', '#PWR06', '+3V3', p[0], p[1])
add('power:PWR_FLAG', '#FLG01', 'PWR_FLAG', p[0] - 6.35, p[1])
p = hwire(j3['4'], 12.7)
add('power:GND', '#PWR07', 'GND', p[0], p[1])
add('power:PWR_FLAG', '#FLG02', 'PWR_FLAG', p[0] - 6.35, p[1])

# ============================================================
# emit file
# ============================================================
libblocks = '\n'.join(grab_symbol(*lib_id.split(':')) for lib_id in used_libs)

out = f'''(kicad_sch (version 20230121) (generator gen_schematic.py)
  (uuid 00000000-0000-0000-0000-000000000000)
  (paper "A4")
  (title_block (title "Energy node - analog front-end") (date "2026-07-12")
    (rev "1") (company "BSc thesis")
    (comment 1 "Matches spice/*.cir; ZMPT101B->PA0, SCT-013-030->PA1"))
  (lib_symbols
{libblocks}
  )
{chr(10).join(wires)}
{chr(10).join(labels)}
{chr(10).join(symbols)}
  (sheet_instances (path "/" (page "1")))
)
'''
open('energy-node.kicad_sch', 'w').write(out)
print('wrote energy-node.kicad_sch')
