#!/usr/bin/env python3
"""Find the translation between the Excellon drill frame and the .pho gerber frame."""
import re, collections, glob

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srm_paths

def pho_points(fn):
    """RS-274X, %FSLAX35Y35% leading-zeros-omitted, inch. Modal X/Y and modal D-code."""
    pts = []
    x = y = 0.0
    d = None
    txt = open(fn, errors='ignore').read()
    for stmt in txt.split('*'):
        stmt = stmt.strip()
        if not stmt:
            continue
        m = re.search(r'D0?([123])$', stmt)
        if m:
            d = int(m.group(1))
        hasc = False
        m = re.search(r'X(-?\d+)', stmt)
        if m: x = int(m.group(1)) / 1e5 * 25.4; hasc = True
        m = re.search(r'Y(-?\d+)', stmt)
        if m: y = int(m.group(1)) / 1e5 * 25.4; hasc = True
        if hasc and d in (1, 2, 3):
            pts.append((x, y))
    return pts

def drill_points():
    def dec(f):
        return int(f.ljust(8, '0')) / 1e5 * 25.4        # trailing-zero suppressed
    pts = []
    for line in open(srm_paths.gerber('drl01.drl'), errors='ignore'):
        m = re.match(r'^X(-?\d+)Y(-?\d+)', line.strip())
        if m: pts.append((dec(m.group(1)), dec(m.group(2))))
    return pts

dr = drill_points()
print(f"drill points: {len(dr)}")

for fn in sorted(glob.glob(os.path.join(srm_paths.gerber_dir(), '*.pho'))):
    gp = pho_points(fn)
    if not gp:
        continue
    # vote on candidate offsets at 0.05 mm resolution
    votes = collections.Counter()
    for dx0, dy0 in dr:
        for gx, gy in gp:
            ddx = gx - dx0; ddy = gy - dy0
            if not (-5 < ddx < 80 and -5 < ddy < 80):
                continue
            votes[(round(ddx * 20), round(ddy * 20))] += 1
    if not votes:
        print(f"{fn.rsplit('/',1)[1]:<14} no candidate offsets")
        continue
    (bx, by), n = votes.most_common(1)[0]
    print(f"{fn.rsplit('/',1)[1]:<14} pts={len(gp):<6} best offset = "
          f"({bx/20:+7.2f}, {by/20:+7.2f}) mm with {n} coincidences")
