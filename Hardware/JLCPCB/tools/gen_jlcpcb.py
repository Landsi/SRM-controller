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

ROT_CORR = {'0805':90, '1206':90, 'LED_0805':90, 'SOT23':180, 'DIO$2F$GF1G':0}

# ---- part assignment -------------------------------------------------------
# key: designator -> (comment, LCSC, library, group)
#   group: SMT = reflow, THT = wave-soldered by JLCPCB, MANUAL = pick in JLC UI
SMT_BY_VALUE = {
    ('100n','0805'):        ('100nF 50V X7R 0805',            'C49678','Basic'),
    ('10k','0805'):         ('10kR 125mW 1% 0805',            'C17414','Basic'),
    ('4k7','0805'):         ('4.7kR 125mW 1% 0805',           'C17673','Basic'),
    ('1k','0805'):          ('1kR 125mW 1% 0805',             'C17513','Basic'),
    ('240R','0805'):        ('240R 125mW 1% 0805',            'C17572','Extended'),
    ('1k33','0805'):        ('1.33kR 125mW 1% 0805',          'C17382','Extended'),
    ('2R2','1206'):         ('2.2R 250mW 1% 1206',            'C17947','Extended'),
    ('FB 600R','1206'):     ('Ferrite bead 600R@100MHz 1206', 'C73732','Extended'),
    ('GF1G','DIO$2F$GF1G'): ('M4 400V 1A SMA(DO-214AC)',      'C18207','Extended'),
    ('SSM3K329R','SOT23'):  ('2N7002 N-ch 60V SOT-23',        'C8545', 'Basic'),
    ('LED','LED_0805'):     ('Red LED 0805',                  'C84256','Basic'),
}
# Zeners: values DERIVED (see README section 7), not recovered from the design.
ZENERS = {
    'D7': ('BZX84C15 15V zener SOT-23 (Q4 Vgs clamp)', 'C499792','Extended'),
    'D2': ('BZX84C33 33V zener SOT-23 (output clamp)', 'C235747','Extended'),
    'D8': ('BZX84C33 33V zener SOT-23 (output clamp)', 'C235747','Extended'),
}
THT = {}
for r in ('D3','D4','D5','D6'): THT[r] = ('1N4007 1000V 1A DO-41','C106903','Extended')
THT['IC4'] = ('LM317T adj. regulator TO-220','C3014307','Extended')
for r in ('Q2','Q3','Q5'):      THT[r] = ('IRF540N N-ch 100V 33A TO-220','C20607742','Extended')
for r in ('J5','J6','J7','J8','J9','J10','J11','J12'):
    THT[r] = ('Pin header 1x2 2.54mm','C32713268','Extended')
THT['J13'] = ('Pin header 1x4 2.54mm','C53055674','Extended')

MANUAL = {
    'BZ1': 'Magnetic buzzer 12mm THT - AT-1224-TWT-5V-2-R is C3812249 but 0 stock; pick an in-stock 12mm equivalent',
    'C3':  '1000uF 16V radial electrolytic, D8 H12 pitch 3.5mm - pick by physical fit',
    'C18': '1000uF 16V radial electrolytic, D8 H12 pitch 3.5mm - pick by physical fit',
    'F1':  'PPTC polyfuse, TE5 radial. Schematic says "Poly Fuse 10A" - confirm hold vs trip rating',
    'J1':  'Terminal block 4P 5.08mm (Phoenix MKDS4 original)',
    'J3':  'Terminal block 4P 5.08mm (Phoenix MKDS4 original)',
    'J2':  'Terminal block 2P 5.08mm (Phoenix MKDS2 original)',
    'J4':  'Terminal block 2P (Phoenix MC2 original - check pitch, MC series is 3.5/5.0mm)',
    'Q4':  'P-channel motor power switch - SEE README section 8. IRF9610 (1.8A) is undersized; '
           'intended part is AOD413A 40V DPAK = C115837 (20,740 stock)',
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
    dx,dy = rot_local(cxl,cyl,rot)
    sp = schprops.get(ref,{})
    value = (sp.get('ALTIUM_VALUE') or pr.get('Value') or '').strip()
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
