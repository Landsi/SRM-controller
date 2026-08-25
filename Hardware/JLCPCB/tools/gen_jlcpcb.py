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

# LED_0805 is 270, not 90: the other 0805-family corrections are +90 because the
# imported footprints run pad1->pad2 along Y, but LD1 is polarised and JLCPCB's
# LED model faces the other way. Netlist: D8 -> R21 -> pad2 -> pad1 -> GND, so
# pad 1 is the CATHODE; the board's curved silkscreen marks sit on pad 1's side,
# the standard cathode marking. At +90 JLC's preview put '+' against that mark,
# i.e. 180 deg out. Confirmed visually, not inferred.
ROT_CORR = {'TO-220-DPAK-COMBO':90, '0805':90, '1206':90, 'LED_0805':270, 'SOT23':180, 'DIO$2F$GF1G':0}

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
    # 24 V, NOT 33 V: these FETs are 30 V parts, so a 33 V clamp sits ABOVE the
    # Vds rating and would never conduct before the FET avalanched. 24 V clears
    # a 14.4 V rail and leaves 4.4 V of margin. See README section 10.
    'D8':'24V', 'D2':'24V',
    # Both output drivers upgraded to AO3400A so J9 and J11 are interchangeable.
    # The schematic uses a 2N7002 on Q1 because it knew that load was a ~10 mA
    # button LED; at 115 mA it cannot drive even a 1.2 W dash bulb. 60 V is not
    # needed anywhere here -- the rail is 12-14.4 V and D2/D8 clamp at 25.6 V
    # worst case. Q6/Q7 were already AO3400A (SSM3K329R is SOT-23F, not the
    # standard SOT-23 this footprint expects).
    'Q1':'AO3400A', 'Q6':'AO3400A', 'Q7':'AO3400A',
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
    ('AO3400A','SOT23'):    ('AO3400A N-ch 30V 5.7A SOT-23',  'C20917','Basic'),
    ('LED','LED_0805'):     ('Red LED 0805',                  'C84256','Basic'),
    ('10n','0805'):         ('10nF 50V X7R 0805',             'C282728','Extended'),
    ('16V','SOT23'):        ('BZX84C16 16V zener SOT-23',     'C44457','Extended'),
    ('24V','SOT23'):        ('BZX84C24 24V zener SOT-23',     'C841152','Extended'),
}
ZENERS = {}   # D2/D7/D8 are "na" on the schematic -> DNP. See README section 7.
THT = {}
for r in ('D3','D4','D5','D6'): THT[r] = ('1N4007 1000V 1A DO-41','C106903','Extended')
for r in ('J5','J6','J7','J8','J9','J10','J11','J12'):
    THT[r] = ('Pin header 1x2 2.54mm','C32713268','Extended')
THT['J13'] = ('Pin header 1x4 2.54mm','C53055674','Extended')
# Schematic specifies Littelfuse RGEF800 (8 A hold), which is out of stock at
# JLCPCB in every variant. RGEF1100 is used instead: same family, and the
# datasheet gives ONE lead spacing of 5.05 mm +-0.75 for the whole RGEF250-1100
# range, so it drops into the 5.08 mm footprint exactly as the 800 would.
# Sized UP rather than down because PPTC hold current derates hard with ambient:
# at 70 C the 800 holds only 5.1 A while the 1100 still holds 6.9 A, against a
# modelled ~11.3 A average. See README section 9.
THT['F1'] = ('RGEF1100 PPTC 11A hold / 18.7A trip 5.05mm','C2760131','Extended')
# Buzzer: MUST be a PASSIVE / externally driven transducer -- the firmware makes
# the tone by toggling the pin at 2.22 kHz, so an active buzzer with a built-in
# driver is the wrong device. D12mm, 6.50mm pin pitch (measured).
THT['BZ1'] = ('Passive transducer 12mm 2.4kHz 6.5mm pitch','C252922','Extended')
# 1000uF 16V radial, 5.00mm pitch (measured) -> D10 can. The schematic DETAILS
# field says "D8, pitch 3.5", which is stale and would not fit.
for r in ('C3','C18'): THT[r] = ('1000uF 16V radial D10x16mm 5mm pitch','C88751','Extended')
# Terminal blocks: 3.81mm pitch (measured), NOT the 5.08mm the stale PHOENIX/MKDS4
# value implies. Pluggable board-side headers; mating plugs are crimped by the
# owner. Note J1 pin 1 and J2 carry ~21 A peak against an 8 A block rating -- the
# original Phoenix MC 1,5 is rated the same, so this is the design's own limit.
for r in ('J1','J3'): THT[r] = ('Terminal block 4P 3.81mm pluggable','C395697','Extended')
for r in ('J2','J4'): THT[r] = ('Terminal block 2P 3.81mm pluggable','C395685','Extended')

# --- TO-220-DPAK-COMBO: placed as flat SMD (TO-263 / D2PAK) ------------------
# JLCPCB inserts TO-220 packages UPRIGHT, but every one of these positions has a
# mounting hole 17.78 mm from the pin row, i.e. the package must lie FLAT. The
# combo footprint's DPAK lands are present in the fabricated copper (verified in
# art01.pho, 4/4 tab corners on all five), so the parts go down flat as DPAK.
#
# The SMD lands are at 2.55 / 2.60 mm spacing -- the TO-220's own 2.54 mm pin
# pitch, i.e. TO-263 / D2PAK, NOT TO-252 / DPAK's 2.286 mm. Fitting D2PAK gives
# 0.035 mm lead offset instead of 0.289 mm, and its tab covers 52% of the
# 9.9 x 14.9 mm thermal pour instead of 22%. D2PAK is simply the surface-mount
# TO-220: same die, same pinout, same pitch, gullwing leads.
#
# Body centre derived from the LEAD lands, not the oversized thermal pour:
#   lead land centres X = 0.0 / 2.55 / 5.15  -> span centre X = 2.575
#   outer lead lands end at y = -4.00, body front face just behind at -4.30,
#   TO-263 body is 8.70 mm long -> centre y = -8.65
# Cross-check: the tab starts ~1 mm behind the body front, predicting y = -5.30;
# the actual thermal land starts at exactly -5.30. Confirmed.
DPAK_LOCAL = (2.575, -8.650)
# ROTATION: +90 deg. Leads sit toward local -y, i.e. tab-above-leads in the Y-up
# CPL frame. I had assumed that was JLCPCB's 0 deg TO-263 orientation; their
# placement preview showed all five rotated 90 deg clockwise, so their library
# part has its leads along Y at 0 deg. Confirmed visually, not inferred.
# All five footprints are at KiCad rot 0, so they emit 90.
DPAK = {
    'IC4': ('LM317D2T adj. regulator TO-263',            'C91673','Extended'),
    # IRF540NS is the same die as the IRF540N TO-220, so this restores the 100 V
    # rating of the original RFP40N10 that the 40 V AOD4184A had given away.
    'Q2':  ('IRF540NS N-ch 100V 33A 44mR D2PAK',         'C23982','Extended'),
    'Q3':  ('IRF540NS N-ch 100V 33A 44mR D2PAK',         'C23982','Extended'),
    'Q5':  ('IRF540NS N-ch 100V 33A 44mR D2PAK',         'C23982','Extended'),
    'Q4':  ('IRF4905S P-ch 55V 70A 20mR D2PAK',          'C2620', 'Extended'),
}

MANUAL = {}   # nothing left to pick by hand; MOD1 is socketed by the owner
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
