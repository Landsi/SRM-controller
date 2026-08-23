#!/usr/bin/env python3
"""
JLCPCB package v2 for the SRM park-actuator controller: SMT + THT assembly.

Transform verified against drl01.drl (156/156 drilled points, worst residual
0.0007 mm):   X_out = X_kicad - 98.501 ;  Y_out = 150.004 - Y_kicad
"""
import re, math, csv, collections, os, sys

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srm_paths
PCB = srm_paths.kicad_pcb()
SCH = srm_paths.kicad_sch()
OUT = sys.argv[1] if len(sys.argv) > 1 else "out_v2"
OX, OY = 98.501, 150.004

def parse_sexp(text):
    tok = re.compile(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+')
    stack, cur = [], []
    for m in tok.finditer(text):
        t = m.group(0)
        if t == '(':
            new = []; cur.append(new); stack.append(cur); cur = new
        elif t == ')': cur = stack.pop()
        elif t.startswith('"'): cur.append(t[1:-1].replace('\\"','"').replace('\\\\','\\'))
        else: cur.append(t)
    return cur[0]

def kids(n, name): return [c for c in n if isinstance(c, list) and c and c[0] == name]
def kid(n, name):
    k = kids(n, name); return k[0] if k else None
def props(n):
    return {p[1]: p[2] for p in kids(n,'property')
            if len(p)>=3 and isinstance(p[1],str) and isinstance(p[2],str)}

ROT_CORR = {'TO-220-DPAK-COMBO':0, '0805':90, '1206':90, 'LED_0805':90, 'SOT23':180, 'DIO$2F$GF1G':0}

# ---- part assignment -------------------------------------------------------
# key: designator -> (comment, LCSC, library, group)
#   group: SMT = reflow, THT = wave-soldered by JLCPCB, MANUAL = pick in JLC UI
# --- Rev A3 schematic overrides ---------------------------------------------
# The KiCad project is a stale PADS->Altium->KiCad conversion and disagrees with
# the released schematic (SRM_motor_controller_A3_sch.pdf, Rev A3 / 20.10.2025)
# on 16 of 76 components. The PDF is authoritative; these are its values.
# Read off the plotted schematic, cross-checked against the netlist topology.
REV_A3 = {
    # J7 "Brake SW +12V applied" — the whole divider chain is different, and the
    # KiCad values would put ~12 V on a 5 V Nano pin with no lower leg fitted.
    'R16':'na', 'R18':'10k', 'R20':'1k', 'R22':'18k', 'C8':'2u2',
    # Q4 gate network: R5 is 47R, not 1k -> Vgs tracks the rail almost 1:1
    'R5':'47R',
    # buzzer drive
    'R36':'100R', 'C13':'470n',
    # Q1/Q8 really are 2N7002; Q6/Q7 really are SSM3K329R. KiCad has all four the same.
    'Q1':'2N7002', 'Q8':'2N7002', 'Q6':'SSM3K329R', 'Q7':'SSM3K329R',
    # the schematic names the fuse outright
    'F1':'Poly Fuse 8A RGEF800',
    # marked "na" on the schematic = deliberately unfitted, application-dependent.
    # KiCad carries "???" for these, which is not the same thing. See README §7.
    'D2':'na',
}

# --- build options chosen for THIS vehicle ----------------------------------
# The schematic leaves these positions 'na' on purpose; values are picked for a
# 12 V vehicle install with an LED park-lock button and J9 pre-wired for a relay.
# Reasoning and the numbers behind each are in README section 12.
FITTED_OPTIONS = {
    # encoder A/B noise filters. 10n = 200us rise, 3.9% of the 5.19ms half-period
    # at the firmware's 96.3 Hz encoder rate. 100n (the board's house value)
    # would eat 38% and wreck the quadrature decode, which is why it is 'na'.
    'C5':'10n', 'C6':'10n',
    # Q4 gate-source clamp. R5=47R makes Vgs track the rail ~1:1, leaving only
    # 5.7 V margin to the +-20 V limit at 14.4 V charging.
    'D7':'16V',
    # J9 spare output, prepared for an automotive 12 V relay coil:
    # Flyback clamp on Q7's drain. Clamps drain-to-GND, so it works wherever the
    # coil's other end is fed from -- this is the only change a relay needs.
    'D8':'33V',
    # R31 is deliberately NOT touched. It is the +BAT feed resistor for J9.1, a
    # convenience supply pin, not the output. Feed the coil from vehicle +12 V
    # into J9.2 instead: J9.1 keeps its 12 mA self-limiting, and +BAT is unfused
    # on this board (F1 protects only the motor path).
}

SMT_BY_VALUE = {
    ('100n','0805'):        ('100nF 50V X7R 0805',            'C49678','Basic'),
    ('10k','0805'):         ('10kR 125mW 1% 0805',            'C17414','Basic'),
    ('4k7','0805'):         ('4.7kR 125mW 1% 0805',           'C17673','Basic'),
    ('1k','0805'):          ('1kR 125mW 1% 0805',             'C17513','Basic'),
    ('240R','0805'):        ('240R 125mW 1% 0805',            'C17572','Extended'),
    ('1k33','0805'):        ('1.33kR 125mW 1% 0805',          'C17382','Extended'),
    ('18k','0805'):         ('18kR 125mW 1% 0805',            'C17506','Extended'),
    ('47R','0805'):         ('47R 125mW 1% 0805',             'C17714','Basic'),
    ('100R','0805'):        ('100R 125mW 1% 0805',            'C17408','Basic'),
    ('2u2','0805'):         ('2.2uF 25V X7R 0805',            'C19110','Extended'),
    ('470n','0805'):        ('470nF 50V X7R 0805',            'C106843','Extended'),
    ('2R2','1206'):         ('2.2R 250mW 1% 1206',            'C17947','Extended'),
    ('FB 600R','1206'):     ('Ferrite bead 600R@100MHz 1206', 'C73732','Extended'),
    ('GF1G','DIO$2F$GF1G'): ('M4 400V 1A SMA(DO-214AC)',      'C18207','Extended'),
    ('2N7002','SOT23'):     ('2N7002 N-ch 60V 115mA SOT-23',  'C8545', 'Basic'),
    ('SSM3K329R','SOT23'):  ('AO3400A N-ch 30V 5.7A SOT-23',  'C20917','Basic'),
    ('LED','LED_0805'):     ('Red LED 0805',                  'C84256','Basic'),
    ('10n','0805'):         ('10nF 50V X7R 0805',             'C282728','Extended'),
    ('16V','SOT23'):        ('BZX84C16 16V zener SOT-23',     'C44457','Extended'),
    ('33V','SOT23'):        ('BZX84C33 33V zener SOT-23',     'C22379474','Extended'),
}
ZENERS = {}   # D2/D7/D8 are "na" on the schematic -> DNP. See README section 7.
THT = {}
for r in ('D3','D4','D5','D6'): THT[r] = ('1N4007 1000V 1A DO-41','C106903','Extended')
for r in ('J5','J6','J7','J8','J9','J10','J11','J12'):
    THT[r] = ('Pin header 1x2 2.54mm','C32713268','Extended')
THT['J13'] = ('Pin header 1x4 2.54mm','C53055674','Extended')
# Schematic specifies Littelfuse RGEF800 (8 A hold). Not stocked; RGEF700 is the
# same family at 5.1 mm pitch, 7 A hold / 11.9 A trip. See README section 9.
THT['F1'] = ('RGEF700 PPTC 7A hold 5.1mm (RGEF800 specified)','C413552','Extended')

# --- TO-220-DPAK-COMBO: placed as flat SMD (TO-252 / DPAK) -------------------
# JLCPCB inserts TO-220 packages UPRIGHT, but every one of these positions has a
# mounting hole 17.78 mm from the pin row, i.e. the package must lie FLAT. The
# combo footprint's DPAK lands are present in the fabricated copper (verified in
# art01.pho, 4/4 tab corners on all five), so the parts go down flat as DPAK.
#
# Body centre derived from the LEAD lands, not the oversized thermal pour:
#   lead land centres X = 0.0 / 2.55 / 5.15  -> span centre X = 2.575
#   outer lead lands end at y = -4.00, body front face just behind at -4.30,
#   TO-252 body is 6.10 mm long -> centre y = -7.35
# Cross-check: a DPAK exposed pad starts ~1 mm behind the body front, predicting
# y = -5.30; the actual thermal land starts at exactly -5.30. Confirmed.
DPAK_LOCAL = (2.575, -7.350)
# Leads sit toward local -y = tab-above-leads in the Y-up CPL frame, which is the
# standard TO-252 0 deg orientation. All five footprints are at rot 0.
DPAK = {
    'IC4': ('LM317MDT adj. regulator TO-252',            'C3015165','Extended'),
    'Q2':  ('AOD4184A N-ch 40V 50A 7mR TO-252',          'C99124',  'Extended'),
    'Q3':  ('AOD4184A N-ch 40V 50A 7mR TO-252',          'C99124',  'Extended'),
    'Q5':  ('AOD4184A N-ch 40V 50A 7mR TO-252',          'C99124',  'Extended'),
    'Q4':  ('AOD413A P-ch 40V 30A 32mR TO-252-3L',       'C5371003','Extended'),
}

MANUAL = {
    'BZ1': 'Electromagnetic transducer, D12mm, pin pitch 6.50mm, drill 0.8mm (measured from '
           'footprint). MUST be PASSIVE / externally driven - the firmware generates the tone '
           'by toggling the pin at 2.22kHz (CYC 200), so an active buzzer with a built-in '
           'driver is wrong. GMC1209YB-42R2400 = C252922 (12mm, 2.4kHz, passive, 6.5mm pitch) '
           'matches footprint, drive method and tuned frequency.',
    'C3':  '1000uF 16V radial, pitch 5.00mm, drill 0.9mm (measured). NOTE the schematic DETAILS '
           'field says "D8, pitch 3.5" - that is stale; the CAE_5MM footprint is 5.0mm, which '
           'implies a D10 can. 16YXJ1000M10X16 = C88751 (D10x16mm). For a shorter can, '
           'C51934165 (D10x11.5mm polymer).',
    'C18': 'as C3 - 1000uF 16V, 5.00mm pitch, D10 can. C88751.',
    'J1':  'Terminal block 4P, pitch 3.81mm, drill 1.22mm (measured - NOT 5.08mm). Original is '
           'Phoenix MC 1,5/4-G-3,81. DB2EVC-3.81-4P-GN = C395697. This is the MOTOR connector: '
           'pin 1 = common (~18A peak), pins 2-4 = one phase each (~9A). That exceeds the 8A '
           'block rating, but so did the original Phoenix part - see README section 9.',
    'J3':  'Terminal block 4P, pitch 3.81mm, drill 1.22mm. Encoder / signal connector '
           '(8V, 2 signals, GND) - low current. DB2EVC-3.81-4P-GN = C395697.',
    'J2':  'Terminal block 2P, pitch 3.81mm, drill 1.22mm. MOTOR SUPPLY input, feeds F1 - '
           'carries the full motor current (~11A avg, ~18A peak). DB2EVM-3.81-2P-GN = C395685.',
    'J4':  'Terminal block 2P, pitch 3.81mm, drill 1.22mm. Controller supply (+BAT) - low '
           'current. Same part as J2: C395685.',
}
# MOD1 (Arduino Nano) -> two 1x15 female socket strips
NANO_SOCKET = ('Female header 1x15 2.54mm','C25503121','Extended')

# ---- load ------------------------------------------------------------------
pcb = parse_sexp(open(PCB).read()); sch = parse_sexp(open(SCH).read())
schprops = {}
for sym in kids(sch,'symbol'):
    pr = props(sym); r = pr.get('Reference')
    if r and not r.startswith('#'): schprops[r] = pr

def rot_local(px, py, deg):
    t = math.radians(-deg); c, s = math.cos(t), math.sin(t)
    return px*c - py*s, px*s + py*c

comps = []
nano = None
for fp in kids(pcb,'footprint'):
    at = kid(fp,'at'); fx, fy = float(at[1]), float(at[2])
    rot = float(at[3]) if len(at)>3 else 0.0
    pr = props(fp); ref = pr.get('Reference','?'); fpn = fp[1]
    pads = []
    for pad in kids(fp,'pad'):
        if len(pad)<4: continue
        sz = kid(pad,'size')
        if sz and float(sz[1])<0.01: continue
        pat = kid(pad,'at')
        pads.append((pad[1], pad[2], float(pat[1]), float(pat[2])))
    if not pads: continue
    tech = 'THT' if any(p[1]=='thru_hole' for p in pads) else 'SMD'
    xs=[p[2] for p in pads]; ys=[p[3] for p in pads]
    cxl,cyl = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    if fpn == 'TO-220-DPAK-COMBO':
        cxl, cyl = DPAK_LOCAL      # TO-252 body centre, see note above
    dx,dy = rot_local(cxl,cyl,rot)
    sp = schprops.get(ref,{})
    value = (sp.get('ALTIUM_VALUE') or pr.get('Value') or '').strip()
    value = REV_A3.get(ref, value)      # released schematic wins over the conversion
    value = FITTED_OPTIONS.get(ref, value)   # then this build's option choices
    rec = dict(ref=ref, fpname=fpn, tech=tech, value=value,
               cx=round(fx+dx-OX,4), cy=round(OY-(fy+dy),4),
               rot=round((rot+ROT_CORR.get(fpn,0))%360,2), raw_rot=round(rot%360,2))
    if fpn == 'NANO':
        nano = (fx, fy, rot, pads)
    comps.append(rec)

def refkey(r):
    m = re.match(r'([A-Za-z_]+)(\d*)', r); return (m.group(1), int(m.group(2) or 0))
comps.sort(key=lambda c: refkey(c['ref']))

# ---- classify + assign -----------------------------------------------------
rows = []          # CPL rows JLCPCB will place
bom  = collections.OrderedDict()
status = {}

def add(ref, cx, cy, rot, comment, lcsc, lib, group):
    rows.append(dict(ref=ref, cx=cx, cy=cy, rot=rot, group=group))
    bom.setdefault((comment, lcsc, lib), []).append(ref)

for c in comps:
    ref, v, fpn = c['ref'], c['value'], c['fpname']
    if fpn == 'HOLE3MM':
        status[ref] = 'mounting-hole'; continue
    if v.strip().lower() in ('na','n/a','dnp',''):
        status[ref] = 'DNP'; continue
    if ref in MANUAL:
        status[ref] = 'MANUAL'; continue
    if fpn == 'NANO':
        status[ref] = 'socketed'; continue
    if ref in DPAK:
        cm, lc, lb = DPAK[ref]; add(ref, c['cx'], c['cy'], c['rot'], cm, lc, lb, 'SMT')
        status[ref] = 'SMT'; continue
    if ref in ZENERS:
        cm, lc, lb = ZENERS[ref]; add(ref, c['cx'], c['cy'], c['rot'], cm, lc, lb, 'SMT')
        status[ref] = 'SMT'; continue
    if ref in THT:
        cm, lc, lb = THT[ref]; add(ref, c['cx'], c['cy'], c['rot'], cm, lc, lb, 'THT')
        status[ref] = 'THT'; continue
    key = (v, fpn)
    if key in SMT_BY_VALUE:
        cm, lc, lb = SMT_BY_VALUE[key]; add(ref, c['cx'], c['cy'], c['rot'], cm, lc, lb, 'SMT')
        status[ref] = 'SMT'; continue
    status[ref] = 'UNASSIGNED'

# ---- Arduino Nano ----------------------------------------------------------
# Owner fits the Nano's base by hand, so MOD1 is deliberately NOT in the CPL.
# Geometry recorded here only so the socket strips can be bought/aligned.
if nano:
    fx, fy, rot, pads = nano
    cols = collections.defaultdict(list)
    for _, _, px, py in pads:
        cols[round(px,2)].append(py)
    print("MOD1 socket strips (NOT in CPL - fitted by owner):")
    for i, (px, pys) in enumerate(sorted(cols.items()), start=1):
        cyl = (min(pys)+max(pys))/2
        dx, dy = rot_local(px, cyl, rot)
        print(f"   strip {'AB'[i-1]}: 1x{len(pys)} @ ({fx+dx-OX:.3f}, {OY-(fy+dy):.3f}) mm, "
              f"rot {(rot+90)%360:g}, pitch 2.54, rows {len(pys)}")
    print(f"   suggested part: {NANO_SOCKET[0]} = {NANO_SOCKET[1]} (x2)\n")

# ---- write -----------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)
rows.sort(key=lambda r: refkey(r['ref']))
with open(f'{OUT}/SRM_CPL_JLCPCB.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation'])
    for r in rows:
        w.writerow([r['ref'], f"{r['cx']:.4f}mm", f"{r['cy']:.4f}mm", 'Top', f"{r['rot']:g}"])
with open(f'{OUT}/SRM_CPL_JLCPCB_gerber-origin.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation'])
    for r in rows:
        w.writerow([r['ref'], f"{r['cx']+50:.4f}mm", f"{r['cy']+50:.4f}mm", 'Top', f"{r['rot']:g}"])
with open(f'{OUT}/SRM_BOM_JLCPCB.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['Comment','Designator','Quantity','LCSC Part #','JLC Library','Mount'])
    for (cm, lc, lb), refs in bom.items():
        refs = sorted(refs, key=refkey)
        grp = next(r['group'] for r in rows if r['ref'] == refs[0])
        w.writerow([cm, ','.join(refs), len(refs), lc, lb, grp])
with open(f'{OUT}/SRM_manual_parts.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['Designator','Value','Footprint','Why / what to pick'])
    for c in comps:
        if status.get(c['ref']) == 'MANUAL':
            w.writerow([c['ref'], c['value'], c['fpname'], MANUAL[c['ref']]])
with open(f'{OUT}/SRM_positions_all.csv','w',newline='') as f:
    w = csv.writer(f)
    w.writerow(['Designator','Status','Tech','Value','Footprint','X (mm)','Y (mm)',
                'Rotation (corrected)','Rotation (raw KiCad)'])
    for c in comps:
        w.writerow([c['ref'], status.get(c['ref'],'?'), c['tech'], c['value'], c['fpname'],
                    f"{c['cx']:.4f}", f"{c['cy']:.4f}", f"{c['rot']:g}", f"{c['raw_rot']:g}"])

# ---- report ----------------------------------------------------------------
cnt = collections.Counter(status.values())
print("footprint disposition")
for k in ('SMT','THT','socketed','MANUAL','DNP','mounting-hole','UNASSIGNED'):
    if cnt[k]: print(f"   {k:<15}{cnt[k]:>3}")
print(f"   {'TOTAL':<15}{sum(cnt.values()):>3}\n")
nsmt = sum(1 for r in rows if r['group']=='SMT')
ntht = sum(1 for r in rows if r['group']=='THT')
print(f"CPL rows placed by JLCPCB : {len(rows)}   (SMT {nsmt} reflow + THT {ntht} wave)")
print(f"BOM line items            : {len(bom)}")
print(f"Manual selection needed   : {cnt['MANUAL']}  ({', '.join(sorted(MANUAL, key=refkey))})")
un = [r for r,s in status.items() if s=='UNASSIGNED']
print(f"UNASSIGNED (bug if >0)    : {len(un)} {un}")
