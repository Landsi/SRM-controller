#!/usr/bin/env python3
"""Definitive alignment: trailing-zero-suppressed Excellon vs KiCad footprint pads."""
import re, math

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srm_paths

# ---- reuse the s-expr loader ----
import importlib.util
spec = importlib.util.spec_from_file_location("al", "align.py")

def parse_sexp(text):
    tok = re.compile(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+')
    stack, cur = [], []
    for m in tok.finditer(text):
        t = m.group(0)
        if t == '(':
            new = []; cur.append(new); stack.append(cur); cur = new
        elif t == ')':
            cur = stack.pop()
        elif t.startswith('"'):
            cur.append(t[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            cur.append(t)
    return cur[0]

def kids(n, name): return [c for c in n if isinstance(c, list) and c and c[0] == name]
def kid(n, name):
    k = kids(n, name); return k[0] if k else None

pcb = parse_sexp(open(srm_paths.kicad_pcb()).read())

def collect_kicad(sign):
    pts = []
    for fp in kids(pcb, 'footprint'):
        at = kid(fp, 'at')
        fx, fy = float(at[1]), float(at[2])
        frot = float(at[3]) if len(at) > 3 else 0.0
        for pad in kids(fp, 'pad'):
            dr = kid(pad, 'drill')
            if not dr: continue
            vals = []
            for v in dr[1:]:
                try: vals.append(float(v))
                except: pass
            if not vals: continue
            pat = kid(pad, 'at')
            px, py = float(pat[1]), float(pat[2])
            t = math.radians(frot * sign)
            c, s = math.cos(t), math.sin(t)
            pts.append((fx + px*c - py*s, fy + px*s + py*c, vals[0]))
    for via in kids(pcb, 'via'):
        at = kid(via, 'at'); dr = kid(via, 'drill')
        pts.append((float(at[1]), float(at[2]), float(dr[1])))
    return pts

# ---- Excellon with TRAILING zero suppression, 3.5 inch ----
def dec(field):
    neg = field.startswith('-')
    if neg: field = field[1:]
    v = int(field.ljust(8, '0')) / 1e5 * 25.4       # pad right -> trailing zeros
    return -v if neg else v

def collect_drill():
    sizes = {}
    for line in open(srm_paths.gerber('drl01.rep'), errors='ignore'):
        m = re.match(r'\s*(\d+)\s+([\d.]+)\s+x\s', line)
        if m: sizes[int(m.group(1))] = float(m.group(2))
    pts, tool = [], None
    for line in open(srm_paths.gerber('drl01.drl'), errors='ignore'):
        line = line.strip()
        m = re.match(r'^T(\d+)', line)
        if m: tool = int(m.group(1)); continue
        m = re.match(r'^X(-?\d+)Y(-?\d+)$', line)
        if m and tool: pts.append((dec(m.group(1)), dec(m.group(2)), sizes.get(tool, 0.0)))
    return pts

drill = collect_drill()

def evaluate(kp, ox, oy, flip, tol=0.05):
    used = [False]*len(drill); matched = 0; worst = 0.0
    for x, y, d in kp:
        tx = x + ox
        ty = (oy - y) if flip else (y + oy)
        best, bi = 1e9, -1
        for i, (gx, gy, gd) in enumerate(drill):
            if used[i] or abs(gd - d) > 0.02: continue
            e = math.hypot(gx-tx, gy-ty)
            if e < best: best, bi = e, i
        if bi >= 0 and best < tol:
            matched += 1; used[bi] = True; worst = max(worst, best)
    return matched, worst

print(f"{'sign':>5} {'flipY':>6} {'matched':>10} {'worstErr(mm)':>13}")
results = []
for sign in (1, -1):
    kp = collect_kicad(sign)
    for flip, ox, oy in ((True, -98.501, 150.004), (False, -98.501, -60.004)):
        m, w = evaluate(kp, ox, oy, flip)
        print(f"{sign:>5} {str(flip):>6} {m:>4}/{len(kp):<5} {w:>13.4f}")
        results.append((m, w, sign, flip, ox, oy))

m, w, sign, flip, ox, oy = max(results, key=lambda r: (r[0], -r[1]))
print(f"\n>>> TRANSFORM: X_out = X_kicad {ox:+.3f} ; "
      f"Y_out = {'%.3f - Y_kicad' % oy if flip else 'Y_kicad %+.3f' % oy} ; "
      f"pad-rotation sign = {sign:+d}")
print(f">>> {m}/156 drilled points matched, worst residual {w:.4f} mm")
