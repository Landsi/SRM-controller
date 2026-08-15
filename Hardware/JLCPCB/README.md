# SRM Park Actuator Controller — JLCPCB Fabrication Package

CPL and BOM for a JLCPCB PCB + **mixed SMT/THT assembly** order of the **Nissan
Leaf park actuator SRM controller** by *OH2NLT* (Juha Niinikoski), published by
*Romukeisari* under GPL-3.0.

- Upstream: <https://github.com/Romukeisari/SRM-controller>
- Development thread: <https://openinverter.org/forum/viewtopic.php?t=6474>
- Relevance: the ZE1 gearbox keeps an electric park-lock actuator — a 3-phase
  switched-reluctance motor with a cycloid gearbox and two hall sensors (TDK
  Micronas HAL502). It needs driving once the JB gearbox and its mechanical
  linkage are gone.

Generated 2026-08-15.

### Regenerating

Run from this directory — the tools locate the repo from their own path:

```bash
python3 tools/gen_jlcpcb.py .          # rewrite the CSVs in place
python3 tools/verify_transform.py      # 156-point drill match
python3 tools/verify_gerber_offset.py  # drill <-> gerber offset
```

`tools/srm_paths.py` unpacks `../SRM_KiCad_Designfiles.zip` and
`../SRM_gerber.zip` into a hash-keyed cache under the system temp dir, so the
tools always read exactly what the zips contain, a changed zip invalidates the
cache automatically, and the working tree stays clean. Nothing needs extracting
by hand. Set `$SRM_REPO` only if you move these tools out of the repo.

---

## 1. What gets fitted

| | Count | How |
|---|---|---|
| **SMT (reflow)** | **58** | in CPL + BOM |
| **THT (wave soldered)** | **13** | in CPL + BOM |
| **Placed by JLCPCB** | **71** | — |
| Fitted by hand | 8 | `SRM_manual_parts.csv` |
| Arduino Nano base | 1 | fitted by owner |
| DNP (`na` in schematic) | 11 | C5, C6, R13, R14, R17, R18, R20, R24, R26, R27, R28 |
| Mounting holes | 4 | HO1–HO4 |
| **Total footprints** | **95** | |

[JLCPCB assembles through-hole parts](https://jlcpcb.com/capabilities/pcb-assembly-capabilities)
by wave soldering, mixed with SMD reflow in a single order, so the axial diodes
and the pin headers go in the machine order alongside the SMD parts. The five
combo positions go in too, but as flat **DPAK** parts rather than upright
TO-220s — that is §8.

### Upload

| Slot | File |
|---|---|
| Gerber | upstream `SRM_gerber.zip`, **unmodified** |
| BOM | `SRM_BOM_JLCPCB.csv` |
| CPL | `SRM_CPL_JLCPCB.csv` |

Upstream states *"SRM_gerber.zip made with original design on Pads. PCB can be
ordered with this"*, so the PADS gerbers are the tested fab data and are used
as-is. The KiCad project supplies placement data only — it is an
Altium→KiCad conversion the author explicitly caveats.

---

## 2. Why the CPL had to be derived

The upstream `SRM_BOM.xlsx` is **empty** — `<dimension ref="A1"/>`,
`<sheetData/>`, zero rows. The gerbers are legacy RS-274X (`.pho`, PADS), not
Gerber X3, so they carry **no component layer**. Neither input could supply a
CPL or a BOM.

Placement comes from `SRM_Converted.kicad_pcb` (KiCad 9.0, 95 footprints); part
values come from the schematic's `ALTIUM_VALUE` / `RATING` / `MANUFACTURER`
fields. All 95 components matched a schematic symbol.

The gerbers carry an internal job name `Suzuki_meter_cluster.pc` — a stale PADS
database name, not a different board (see §3).

---

## 3. Coordinate frames — verified, not assumed

Every drilled point in the KiCad design (102 through-hole pads + 54 vias = 156)
was matched against `drl01.drl`:

```
X_cpl = X_kicad −  98.501
Y_cpl = 150.004 − Y_kicad     (Y-up, origin = board outline lower-left)
```

> **156 / 156 points matched, worst residual 0.0007 mm.**

Corroborated independently by the drill tool table — all ten tools agree with
the KiCad drill sizes exactly (0.4×54, 0.8×32, 0.813×2, 0.9×4, 0.914×20,
1.016×8, 1.041×15, 1.219×12, 3.048×9). The gerbers *are* this board.

Two traps found on the way:

1. **`drl01.drl` uses trailing-zero suppression**, not the leading-zero
   suppression its `%FSLAX35Y35%` header implies. `X0028559` is 72.540 mm, not
   7.254 mm. Decoding it the header's way corrupts about one hole in ten.
2. **The `.pho` layers sit +50.00 / +50.00 mm from the drill frame** — a PADS
   plot origin, measured by drill/copper correlation (286 coincidences at
   exactly 50.00/50.00). Board outline is 0–100 × 0–90 in the drill frame but
   50–150 × 50–140 in the gerber frame.

Because of (2) the CPL origin is genuinely ambiguous, so both are provided:

| File | Origin | Use when |
|---|---|---|
| `SRM_CPL_JLCPCB.csv` | board lower-left | **default** — the standard convention |
| `SRM_CPL_JLCPCB_gerber-origin.csv` | +50/+50 | if JLC's preview shows every part uniformly shifted |

**Check the placement preview before paying.** A wrong origin appears as a
uniform shift of all 71 parts and takes one click to spot.

---

## 4. Rotation corrections — the part that would have failed silently

The Altium-imported footprints do not follow IPC/JLCPCB orientation:

| Footprint | Correction | Qty | Why |
|---|---|---|---|
| `0805` | **+90°** | 42 | pad 1→2 runs along **Y**; IPC standard is along X |
| `1206` | **+90°** | 2 | same |
| `LED_0805` | **+90°** | 1 | same |
| `SOT23` | **+180°** | 7 | geometry matches KiCad's standard SOT-23 |
| `DIO$2F$GF1G` | 0° | 1 | already along X |
| `TO-220-DPAK-COMBO` | 0° | 5 | DPAK leads point −y = standard TO-252 |

**45 of the 58 SMT parts sit on an 0805/1206-family land pattern.** Exporting
rotation naively would have placed every resistor and capacitor 90° out —
bridged across its pads instead of along them. No standard rotation-correction
database catches this, because those databases key on KiCad's *standard*
footprint names (`R_0805_2012Metric`), which correctly need no correction; this
board's imported footprints are named plain `0805`.

The SOT-23 value is not inference — it matches the published JLCPCB table
(`bennymeg/Fabrication-Toolkit`, `plugins/transformations.csv`:
`"^SOT-23",180,0,0`).

### Confirm polarity visually

Rotation fixes the axis, not which end is pin 1. Check in JLC's part preview:
**LD1** (LED), **D1** (M4 SMA cathode band), **Q1/Q6/Q7/Q8** (2N7002), and the
three zeners **D2/D7/D8**. The other 45 SMT parts are non-polarised and carry no
polarity risk.

---

## 5. Circuit roles, from the firmware

`src/SRM_drive_v10/SRM_drive_v10.ino` pin defines, cross-referenced against the
netlist, identify every transistor:

| Part | Nano pin | Firmware role | Drives |
|---|---|---|---|
| Q2, Q3, Q5 (DPAK) | D10/D11/D12 | `U_SW`/`V_SW`/`W_SW` | the three SRM phases |
| Q6 → Q4 | D9 | `A_SW` motor power | Q4 = high-side motor switch |
| Q1 | D5 | `BTNLED` | park-lock button LED, via J11 |
| Q7 | D6 | *unused in v1.0* — spare output | J9 |
| Q8 | D13 | `BUZZ` | BZ1 buzzer |

Motor data from the upstream README and the forum thread: **1.35 Ω/phase**,
inductance **1.6–4.4 mH** with rotor position, ~**11 Nm** at the output, ~155
encoder pulses end-to-end, ~30–35° travel, runs on **12 V**.

---

## 6. BOM

All 19 line items carry LCSC part numbers. 45 of 71 placements are **Basic**
parts, so only a handful of feeder setup fees apply.

| Mount | LCSC | Lib | Qty | Part |
|---|---|---|---|---|
| SMT | C49678 | Basic | 13 | 100nF 50V X7R 0805 |
| SMT | C17414 | Basic | 19 | 10 kΩ 1% 0805 |
| SMT | C17673 | Basic | 4 | 4.7 kΩ 1% 0805 |
| SMT | C17513 | Basic | 4 | 1 kΩ 1% 0805 |
| SMT | C8545 | Basic | 4 | 2N7002 SOT-23 |
| SMT | C84256 | Basic | 1 | Red LED 0805 |
| SMT | C17572 | Extended | 1 | 240 Ω 1% 0805 |
| SMT | C17382 | Extended | 1 | 1.33 kΩ 1% 0805 |
| SMT | C17947 | Extended | 1 | 2.2 Ω 1% 1206 |
| SMT | C73732 | Extended | 1 | Ferrite bead 600 Ω@100 MHz 1206 |
| SMT | C18207 | Extended | 1 | M4 400 V 1 A SMA |
| SMT | C3015165 | Extended | 1 | LM317MDT TO-252 (flat) |
| SMT | C99124 | Extended | 3 | AOD4184A N-ch 40 V TO-252 (flat) |
| SMT | C5371003 | Extended | 1 | AOD413A P-ch 40 V TO-252-3L (flat) |
| SMT | C499792 | Extended | 1 | BZX84C15 15 V zener — **derived, see §7** |
| SMT | C235747 | Extended | 2 | BZX84C33 33 V zener — **derived, see §7** |
| THT | C106903 | Extended | 4 | 1N4007 DO-41 |
| THT | C32713268 | Extended | 8 | Pin header 1×2 2.54 mm |
| THT | C53055674 | Extended | 1 | Pin header 1×4 2.54 mm |

Substitutions:

- **Q1/Q6/Q7/Q8**: schematic `ALTIUM_VALUE` is `SSM3K329R` (SOT-23**F**,
  Extended, ~4 k stock); the PCB `Value` field says **2N7002**, a Basic part
  with 1.9 M stock. 2N7002 used. Fine at 115 mA gate-drive duty.
- **Q2/Q3/Q5**: `RFP40N10` → **IRF540N** (100 V, 33 A). The PCB value BUZ11 is
  50 V/30 A, so this is equal or better on both counts.
- **D1**: `GF1G` → **M4** — identical ratings (400 V, 1 A, SMA/DO-214AC).

Stock was live on 2026-08-15 and moves. Re-check **C17382** (1.33 kΩ, ~4.6 k
stock) and the zeners (~600–1,800 each) before ordering.

---

## 7. Zener values — derived, not measured

`ALTIUM_VALUE` is literally `???` for D2, D7 and D8 in both the schematic and
the board, and the schematic PDF has no extractable text. **The openinverter
thread contains no output-voltage measurements either** — it covers the
actuator's internals (cycloid gearbox, HAL502 hall sensors, dyno torque), not
the controller's clamp levels. The "10F" SOT-23 discussed there is a Renesas
NNCD10F on the *motor's* flex PCB protecting the hall sensors, not on this
board.

So these values are calculated from the circuit, and should be confirmed with
OH2NLT before a production run:

**D7 — Q4 gate-source clamp → 15 V.** R4 (4k7) pulls Q4's gate to the rail, R5
(1k) pulls it down, so V<sub>GS</sub> = V<sub>rail</sub> × 4.7/5.7 = **9.9 V at
12 V, 13.2 V at 16 V**. IRF9610 and AOD413A are both ±20 V V<sub>GS(max)</sub>.
15 V clears the working point and stays under the limit. This one is
well-constrained.

**D2 / D8 — output clamps → 33 V.** Low-side 2N7002 drains (60 V V<sub>DS</sub>)
on the "two configurable outputs for relay / lamp / led". The clamp must sit
above a 16 V rail and below 60 V; 33 V is the conventional pick and is safe for
either a lamp or a relay coil. Less tightly constrained than D7 — it depends on
what you hang on J9/J11.

Phase flyback does **not** pass through these: at 1.35 Ω the phase current is
~8.9 A, so ½LI² ≈ 174 mJ — far beyond a 350 mW SOT-23. That energy goes through
D3–D6 (1N4007), consistent with the design.

---

## 8. The five combo positions — placed flat as DPAK

IC4, Q2, Q3, Q4 and Q5 sit on `TO-220-DPAK-COMBO`, a hybrid land pattern taking
either a TO-220 through-hole part or a DPAK surface-mount one. **All five are
placed as DPAK, lying flat.**

### Why not TO-220

Every one has a 5.08 mm mounting hole exactly **17.78 mm** from the pin row —
that hole only makes sense with the package lying flat and its tab bolted down.
JLCPCB's THT process inserts TO-220 packages **upright**: it will not form leads
90° or fit a screw. Ordering them that way gives parts standing ~15 mm proud
with no heatsink path, unbendable once wave-soldered. JLC's board preview shows
this plainly, and is worth trusting — it renders what they will actually build.

### The DPAK lands are real

Checked against the fabricated data, **all five DPAK thermal-tab lands are
present in the top copper** (`art01.pho`, 4/4 corners each). The lands survived
the Altium→KiCad import only as unnamed, netless pads — a KiCad artifact, not a
board one.

### Where the body goes — derived, then cross-checked

The thermal pour is 9.9 × 14.9 mm, far larger than the ~6.5 mm package, because
it doubles as the bolt-down area for a TO-220 tab. So it is useless as a
placement reference. The **lead lands** are the reliable datum:

```
lead land centres, footprint-local X = 0.00 / 2.55 / 5.15  ->  span centre 2.575
outer lead lands end at            y = -4.00
TO-252 body front face just behind y = -4.30
body is 6.10 mm long               ->  centre y = -7.35
```

Independent cross-check: a DPAK's exposed pad starts ~1 mm behind the body front
face, predicting the thermal land should begin at **y = −5.30**. It begins at
**exactly −5.30**. The land pattern really was drawn around a true TO-252, so the
body position is confirmed by geometry rather than assumed.

Verified after generation — every centroid sits inside its own thermal land, and
the 6.6 × 6.1 mm body clears the lead lands by 1.8 mm.

**Rotation is 0°.** Leads sit toward local −y, i.e. tab-above-leads in the Y-up
CPL frame, which is the standard TO-252 orientation. All five footprints are at
rot 0.

### Parts

| Ref | Part | LCSC | Note |
|---|---|---|---|
| IC4 | LM317MDT, TO-252 | `C3015165` | supplies ~8 V rail + hall sensors, well under 100 mA |
| Q2, Q3, Q5 | AOD4184A N-ch, 40 V, 50 A, 7 mΩ | `C99124` | phase switches, ~8.9 A each → ~0.55 W |
| Q4 | AOD413A P-ch, 40 V, 30 A, 32 mΩ | `C5371003` | motor power switch, carries the lot |

Two things to weigh, neither blocking:

- **Lead pitch is 2.55 / 2.60 mm on these lands, against 2.286 mm on a real
  TO-252.** The combo footprint compromised toward the TO-220's 2.54 mm holes.
  Outer leads therefore sit ~0.15–0.3 mm off their land centres — still well
  inside 2.1 mm-wide lands, but it is not a textbook DPAK pattern.
- **40 V parts replace 50 V (BUZ11) / 100 V (RFP40N10) originals.** Phase flyback
  is clamped to the rail by D3–D6, so working V<sub>DS</sub> is ~13–17 V and 40 V
  is over 2× that. But the 1N4007s are slow rectifiers, so a brief spike before
  they conduct is plausible. If you want the original margin back, keep Q2/Q3/Q5
  as bolted TO-220s and hand-fit just those three.

**Q4's part number was separately contested** and this settles it: the PCB value
`IRF9610` is 1.8 A, hopeless against ~8.9 A, while `ALTIUM_VALUE`, `RATING` (40V)
and `DETAILS` (SMD) all point at AOD413A. Three fields against one, and the DPAK
land confirms the package. The 30 A / 32 mΩ variant is specified rather than the
12 A one, because Q4 sees the full ~18 A peak.

---

## 9. Parts fitted by hand (8)

`SRM_manual_parts.csv` — none of these is a judgement call any more; every
dimension is measured from the board file, so they are ordinary catalogue
lookups. Only F1 has a genuine open question.

| Ref | Measured footprint | Part | LCSC |
|---|---|---|---|
| BZ1 | D12 mm, pin pitch **6.50 mm**, drill 0.8 | Electromagnetic transducer, **passive** — see below | `C252922` |
| C3, C18 | pitch **5.00 mm**, drill 0.9 | 1000 µF 16 V radial, D10 can | `C88751` |
| J1, J3 | 4P, pitch **3.81 mm**, drill 1.22 | Terminal block, DB2EVC-3.81-4P | `C395697` |
| J2, J4 | 2P, pitch **3.81 mm**, drill 1.22 | Terminal block, DB2EVM-3.81-2P | `C395685` |
| F1 | TE5, pitch **5.08 mm**, drill 0.81 | see below — the one open question | — |

Three corrections fall out of measuring rather than trusting the schematic text:

- **The terminal blocks are 3.81 mm pitch, not 5.08 mm.** All four are Phoenix
  **MC 1,5** series, matching the `PHOENIX/MC2` and `MC4` values — the
  `PHOENIX/MKDS4` value on J1/J3 is stale.
- **C3/C18 are 5.00 mm pitch, not 3.5 mm.** The schematic `DETAILS` field says
  "H12, D8, Pitch 3.5", but the footprint is `CAE_5MM` at 5.00 mm — which implies
  a **D10** can, not D8. Buying to the schematic text would not fit.
- **BZ1 must be a passive transducer, not an active buzzer.** The firmware
  generates the tone itself by toggling the pin at 2.22 kHz (`CYC 200`), so a
  buzzer with a built-in driver is the wrong device. `C252922`
  (GMC1209YB-42R2400) matches footprint pitch, drive method and the tuned
  frequency together.

### F1 — what current does it actually see?

The schematic says "Poly Fuse 10A" without stating whether that is a **hold** or
an **interrupt** rating, and the two readings give completely different parts.
The measured motor data plus the firmware timing settle it.

F1 sits upstream of Q4, so it carries the whole motor current. The firmware
alternates **two** phases on and **one** phase on, 4 ms each, six steps per loop:

| Step | R | Steady-state I | Reached after 4 ms (τ = 1.2–3.3 ms) |
|---|---|---|---|
| UV / VW / WU (2 phases) | 0.675 Ω | 17.8 A | 12.6–17.2 A |
| V / W / U (1 phase) | 1.350 Ω | 8.9 A | 6.3–8.6 A |

- duty-weighted average ≈ **11.3 A**
- worst-case peak ≈ **17.8 A**
- duration per park/unpark = 45 × 6 × 4 ms + start = **1.14 s**

A PPTC with a ~1 A hold current would therefore trip on every single operation.
**"10 A" can only mean the hold/continuous rating.** Question resolved.

The awkward part is that **no ~10 A-hold PPTC fits a 5.08 mm pitch**: RUEF900
(9 A hold) needs 10.2 mm, and MF-R1100 (11 A) is out of stock. Physics is against
it — that hold current needs a large disc and wide leads. So either:

- fit a **10 A TE5 cartridge fuse**, which matches the footprint exactly and is
  correctly rated for 11 A over 1.14 s (fuses tolerate mild overload for
  seconds), but is not resettable; or
- fit **RUEF900** and form its leads from 10.2 mm down to 5.08 mm.

### Connector current ratings — worth knowing

From the netlist, **J1 is the motor connector** (pin 1 = common, pins 2–4 = the
three phases) and **J2 is the motor supply input** feeding F1. With the currents
below that means J1 pin 1 and J2 both see **~18 A peak**, against an **8 A**
rating on 3.81 mm blocks.

That is not a substitution error — the original Phoenix MC 1,5 series is also
rated 8 A, so the design always ran these connectors over their continuous
rating. It is workable because conduction is only 1.14 s at a time, but it is
the tightest-rated part in the motor path and worth watching if anything runs
hot. J3 (encoder/signals) and J4 (controller supply) carry very little.

**MOD1 (Arduino Nano)** is fitted by the owner. Geometry if you want sockets:
two 1×15 strips, 2.54 mm pitch, at **(59.000, 68.780)** and **(43.760,
68.780)** mm, rotation 270°. A suitable part is `C25503121` (1×15 female
header) ×2.

---

## 10. Files

| File | Contents |
|---|---|
| `SRM_CPL_JLCPCB.csv` | **CPL — 71 parts (58 SMT + 13 THT), board-lower-left origin** |
| `SRM_CPL_JLCPCB_gerber-origin.csv` | same, +50/+50 to match the `.pho` frame |
| `SRM_BOM_JLCPCB.csv` | 19 line items, all with LCSC part numbers |
| `SRM_manual_parts.csv` | the 8 parts fitted by hand |
| `SRM_positions_all.csv` | all 95 footprints with status and corrected rotation |
| `tools/srm_paths.py` | resolves the design files out of the fork's zips |
| `tools/gen_jlcpcb.py` | generator |
| `tools/verify_transform.py` | 156-point drill match |
| `tools/verify_gerber_offset.py` | drill↔gerber offset correlation |

## 11. Provenance

This directory lives in <https://github.com/Landsi/SRM-controller>, a fork of
`Romukeisari/SRM-controller` (GPL-3.0, HW and SW by OH2NLT). An `upstream`
remote is configured, so `git fetch upstream && git merge upstream/main` pulls
the author's changes. As of 2026-08-15 the fork was level with upstream
(0 ahead, 0 behind) at `cc59940`.

Everything here is *generated* — derived from `../SRM_KiCad_Designfiles.zip` and
checked against `../SRM_gerber.zip`. The upstream hardware files are untouched.

**If upstream revises the hardware, re-run the two verify scripts before
trusting the CPL again** — the transform is specific to this board revision, and
a silent origin or rotation change is exactly the failure this package exists to
prevent.

Used by the Clio Leaf conversion (`project-clio-leaf`) to drive the ZE1
gearbox's park-lock actuator.
