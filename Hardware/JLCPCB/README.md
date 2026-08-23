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
| **SMT (reflow)** | **61** | in CPL + BOM |
| **THT (wave soldered)** | **21** | in CPL + BOM |
| **Placed by JLCPCB** | **82** | — |
| Fitted by hand | 0 | — |
| Arduino Nano base | 1 | fitted by owner |
| DNP (`na`, left unfitted) | 8 | R13, R14, R16, R17, R24, R26, R27, R28 |
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
uniform shift of all 82 parts and takes one click to spot.

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

**41 of the 56 SMT parts sit on an 0805/1206-family land pattern.** Exporting
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

All 31 line items carry LCSC part numbers. 43 of 82 placements are **Basic**
parts, so only a handful of feeder setup fees apply.

| Mount | LCSC | Lib | Qty | Part |
|---|---|---|---|---|
| SMT | `C17414` | Basic | 18 | 10kR 125mW 1% 0805 |
| SMT | `C49678` | Basic | 11 | 100nF 50V X7R 0805 |
| SMT | `C17513` | Basic | 4 | 1kR 125mW 1% 0805 |
| SMT | `C20917` | Basic | 3 | AO3400A N-ch 30V 5.7A SOT-23 |
| SMT | `C99124` | Extended | 3 | AOD4184A N-ch 40V 50A 7mR TO-252 |
| SMT | `C17673` | Basic | 3 | 4.7kR 125mW 1% 0805 |
| SMT | `C282728` | Extended | 2 | 10nF 50V X7R 0805 |
| SMT | `C841152` | Extended | 2 | BZX84C24 24V zener SOT-23 |
| SMT | `C19110` | Extended | 1 | 2.2uF 25V X7R 0805 |
| SMT | `C106843` | Extended | 1 | 470nF 50V X7R 0805 |
| SMT | `C18207` | Extended | 1 | M4 400V 1A SMA(DO-214AC) |
| SMT | `C44457` | Extended | 1 | BZX84C16 16V zener SOT-23 |
| SMT | `C3015165` | Extended | 1 | LM317MDT adj. regulator TO-252 |
| SMT | `C73732` | Extended | 1 | Ferrite bead 600R@100MHz 1206 |
| SMT | `C84256` | Basic | 1 | Red LED 0805 |
| SMT | `C5371003` | Extended | 1 | AOD413A P-ch 40V 30A 32mR TO-252-3L |
| SMT | `C8545` | Basic | 1 | 2N7002 N-ch 60V 115mA SOT-23 |
| SMT | `C17714` | Basic | 1 | 47R 125mW 1% 0805 |
| SMT | `C17572` | Extended | 1 | 240R 125mW 1% 0805 |
| SMT | `C17382` | Extended | 1 | 1.33kR 125mW 1% 0805 |
| SMT | `C17947` | Extended | 1 | 2.2R 250mW 1% 1206 |
| SMT | `C17506` | Extended | 1 | 18kR 125mW 1% 0805 |
| SMT | `C17408` | Basic | 1 | 100R 125mW 1% 0805 |
| THT | `C32713268` | Extended | 8 | Pin header 1x2 2.54mm |
| THT | `C106903` | Extended | 4 | 1N4007 1000V 1A DO-41 |
| THT | `C88751` | Extended | 2 | 1000uF 16V radial D10x16mm 5mm pitch |
| THT | `C395697` | Extended | 2 | Terminal block 4P 3.81mm pluggable |
| THT | `C395685` | Extended | 2 | Terminal block 2P 3.81mm pluggable |
| THT | `C252922` | Extended | 1 | Passive transducer 12mm 2.4kHz 6.5mm pitch |
| THT | `C413552` | Extended | 1 | RGEF700 PPTC 7A hold 5.1mm (RGEF800 specified) |
| THT | `C53055674` | Extended | 1 | Pin header 1x4 2.54mm |

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

## 7. The KiCad project disagrees with the released schematic

**The KiCad conversion is stale. `SRM_motor_controller_A3_sch.pdf` (Rev A3,
20.10.2025) is authoritative and is what this BOM follows.** Comparing all 76
components gave **16 divergences**:

| Ref | KiCad conversion | Schematic Rev A3 | Why it matters |
|---|---|---|---|
| R16 | 10k | **na** | |
| R18 | na | **10k** | |
| R20 | na | **1k** | |
| R22 | 10k | **18k** | |
| C8 | 100n | **2u2** | ← all five are the J7 brake divider |
| R5 | 1k | **47R** | changes Q4's gate drive completely |
| R36 | 4k7 | **100R** | buzzer drive current |
| C13 | 100n | **470n** | buzzer coupling |
| Q1, Q8 | SSM3K329R | **2N7002** | KiCad has all four the same part |
| Q6, Q7 | SSM3K329R | **SSM3K329R** | …the schematic distinguishes them |
| D2, D7, D8 | `???` | **na** | not the same thing — see below |
| F1 | Poly Fuse 10A | **Poly Fuse 8A, Littelfuse RGEF800** | |
| BZ1, IC4 | *(blank)* | AT-1224-TWT-5V-2-R, LM317T | |

### The J7 divider is the dangerous one

J7 is labelled **"Brake SW +12V applied"** — 12 V arrives directly on the pin.
Rev A3 divides it with R22 (18k) over R18 (10k), giving the Nano
12 × 10/28 = **4.3 V**. Safe.

Build to the KiCad values instead and R18 is *not fitted at all*, so there is no
lower leg: the Nano's A2 pin sits at 12 V behind a 10k resistor, held only by its
internal clamp diode, with no pull-down when the brake is released. That is an
out-of-spec input that would read unreliably at best.

This is the clearest evidence the conversion predates Rev A3 — J6 and J8 (the
unconfigured inputs) match perfectly, and only J7, the one actually configured
for a 12 V source, differs.

### "na" means deliberately unfitted, not unknown

D2, D7 and D8 carry `???` in KiCad but **`na`** on the schematic, next to the
note *"Relay/Lamp/LED Drivers — Select part values for application"*. They are
option positions, not gaps in the documentation, so they are now **DNP**.

Earlier revisions of this package fitted derived zener values there. That was
filling in a blank the designer left open on purpose. When you would want them:

- **D2 / D8** clamp the low-side outputs on J11 and J9. Fit a zener (≈33 V, under
  the 2N7002's 60 V) only if you drive something inductive like a relay coil. For
  a lamp or LED, leave empty.
- **D7** clamps Q4's gate-source. With R5 = 47R (not the 1k the conversion
  claims), V<sub>GS</sub> tracks the supply almost 1:1 — about 11.9 V on a 12 V
  rail, but **19.8 V at the top of the schematic's stated 10–20 V input range**,
  against a ±20 V limit. On a 12 V vehicle it is unnecessary. Fit ≈15 V if you
  run the supply much above 16 V.

### Everything else checks out

The remaining 60 components match, including all four 1N4004s, the three
RFP40N10 phase switches, AOD413A for Q4 (which independently confirms §8), and
every value in the J6 and J8 input blocks.

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

## 9. Everything is in the machine order except the Nano

**MOD1 (Arduino Nano) is the only part not placed.** It is not a JLCPCB assembly
part, and you would not want it soldered down in any case. Fit two 1×15 female
sockets and plug the module in:

| | Position (CPL frame) | Rotation |
|---|---|---|
| strip A | (59.000, 68.780) mm | 270° |
| strip B | (43.760, 68.780) mm | 270° |

2.54 mm pitch, 15 ways each — `C25503121` ×2.

Earlier revisions of this package left seven more parts for hand fitting on the
grounds that "physical fit decides". Once the footprints were **measured from the
board file** rather than guessed, matching catalogue parts existed for all of
them and that reasoning no longer held:

| Ref | Measured | Part | LCSC |
|---|---|---|---|
| BZ1 | D12 mm, pitch **6.50**, drill 0.8 | passive transducer, 2.4 kHz | `C252922` |
| C3, C18 | pitch **5.00**, drill 0.9 | 1000 µF 16 V, D10×16 | `C88751` |
| J1, J3 | 4P, pitch **3.81**, drill 1.22 | DB2EVC-3.81-4P pluggable | `C395697` |
| J2, J4 | 2P, pitch **3.81**, drill 1.22 | DB2EVM-3.81-2P pluggable | `C395685` |

Three of those measurements contradicted the schematic text and would have caused
wrong parts to be bought:

- **Terminal blocks are 3.81 mm pitch, not 5.08.** All four are Phoenix **MC 1,5**
  series; the `PHOENIX/MKDS4` value on J1/J3 is stale.
- **C3/C18 are 5.00 mm pitch, not 3.5**, so a **D10** can, not the D8 the
  `DETAILS` field claims.
- **BZ1 must be a passive transducer.** The firmware makes the tone by toggling
  the pin at 2.22 kHz, so an active buzzer with a built-in driver is wrong.

### Connectors — mating plugs and the Molex question

J1–J4 are **pluggable board-side headers**; the mating plugs are crimped
separately.

**Molex Mini-Fit Jr. does not fit these footprints.** It is 4.20 mm pitch against
the board's 3.81 mm, and the error accumulates:

| | Pitch | 4-pin span | Outer pin offset | Play in a 1.22 mm hole |
|---|---|---|---|---|
| board | 3.81 mm | 11.43 mm | — | ±0.11 mm |
| Mini-Fit Jr. | 4.20 mm | 12.60 mm | **0.585 mm** | misses by ~0.49 mm |
| Micro-Fit 3.0 | 3.00 mm | 9.00 mm | 1.215 mm | hopeless |

Mini-Fit Jr. is rated **9 A per contact**, better than these 8 A blocks, so it is
worth using — as an **inline connector on a short pigtail** from the board's
terminal block, rather than on the board itself. That also puts the better
contacts on the 21 A motor conductors.

---

## 10. Build options fitted for this vehicle

The schematic leaves several positions `na` **on purpose** — they are option
positions whose right value depends on the installation, not gaps in the
documentation (§7). This build fills five of them. Each is a deliberate
deviation from the as-drawn default, recorded here so it can be undone.

### C5, C6 — encoder filters → **10 nF** (`C282728`)

The firmware fixes the encoder rate: 104 pulses over `45 × 6 × 4 ms` = **96.3 Hz**,
so a 5.19 ms half-period and **2.60 ms between the A and B edges**. R9/R11 are
10 k series, R10/R12 the 10 k pull-ups (HAL502 is open-drain), so a rising edge
sees 20 k.

| C | τ rise | % of half-period | f_c |
|---|---|---|---|
| 1 nF | 20 µs | 0.4 % | 8.0 kHz — barely filters |
| **10 nF** | **200 µs** | **3.9 %** | **796 Hz** |
| 100 nF | 2 ms | 38.5 % | 80 Hz — **breaks the quadrature decode** |

That last row is *why* the position is `na`: the board's house value of 100 n
would smear edges across 38 % of a half-period, and `enca()` samples ENCB on A's
rising edge. Both caps must be the same value so A and B are delayed equally.

Worth having because encoder A sits on **INT0** and false edges corrupt `encctr`,
which is what the over/under-travel and stall detection rely on — with ~18 A
switching centimetres away.

### D7 — Q4 gate clamp → **BZX84C16, 16 V** (`C44457`)

R5 = 47R (Rev A3, not the 1k the KiCad conversion claims), so V_GS tracks the
rail almost 1:1:

| Rail | V_GS | Margin to ±20 V |
|---|---|---|
| 12 V | 11.9 V | 8.1 V |
| 14.4 V charging | 14.3 V | **5.7 V** |
| 20 V (schematic max) | 19.8 V | 0.2 V |

16 V never conducts below a ~15.5 V rail, so it is electrically invisible in
normal use. 15 V would be wrong — its 14.25 V lower tolerance conducts at
charging voltage.

### D8 — J9 prepared for a 12 V relay

J9 and J11 are **low-side switches with a convenience supply pin**, not two-pin
outputs:

```
+BAT ──[ R31 1k ]── J9.1        <- a SOURCE pin: +BAT tapped through the resistor
                    J9.2 ── Q7 drain ── GND      <- the actual output
```

**J9.2 is the output** — open-drain to ground. J9.1 is just +BAT brought to the
same connector so a small load (an LED in a button) can sit across two adjacent
pins with no separate supply wire.

Two independent things decide what a load needs, and it is worth keeping them
apart:

| | Job | When it matters |
|---|---|---|
| **D8** | clamps the inductive kick when Q7 switches **off** | any coil, however it is wired |
| **R31** | sets the steady current when the output is **on** | only if the load is fed *through J9.1* |

So the only change a relay actually requires is **D8: BZX84C24, 24 V**
(`C841152`), cathode to Q7's drain. It clamps drain-to-ground, so it works
wherever the coil's other end comes from. Into a 0.3 H coil the clamp is ~3.4 W
for 1.8 ms — fine non-repetitive for occasional park-lock use; a continuously
cycled relay would want an SMA-package TVS instead.

**Why 24 V and not 33 V — a clamp is sized to the transistor, not the rail.**
It must sit above the rail so it never conducts, *and* below the FET's V_DS
rating so it conducts before the FET avalanches:

| Clamp | Band | vs 14.4 V rail | vs Q7 (30 V) | vs Q1 (60 V) |
|---|---|---|---|---|
| **24 V** | 22.8–25.6 | clear | **+4.4 V** ✓ | +34.4 V ✓ |
| 33 V | 31.0–35.0 | clear | **−5.0 V — above rating** | +25.0 V ✓ |

Q7 is a 30 V part — SSM3K329R as drawn, AO3400A as built — so a 33 V clamp would
sit above its breakdown and never conduct in time. That is protection that does
nothing. **D2 is a different value on purpose**: Q1 really is a 60 V 2N7002.

The two positions look identical but carry different parts because the designer
knew J11's load (a ~10 mA button LED, so a jellybean 2N7002) and did not know
J9's (hence 3.5 A of headroom). The 60 V on Q1 is incidental — it is simply what
a 2N7002 is, not something the circuit needs. **Note the coupling: these clamp
values are tied to the specific transistors. Change a FET and re-check its
clamp.**

**Wire the coil from vehicle +12 V (fused) into J9.2, leaving J9.1 unused.**
12 V and GND are already at the board, so this costs nothing in harness and
avoids the alternative below.

### Why R31 is deliberately left at 1k

Feeding the coil through J9.1 instead would require R31 → 0 R, because at 1 k a
coil sees under 3.4 V and never pulls in (85 Ω coil: 0.9 V). That buys a tidy
two-wire connection, at a real cost:

- **`+BAT` is unfused on this board.** F1 protects only the motor path, and
  closing J5 bridges +BAT to the *upstream* side of F1. At 0 R, J9.1 becomes a
  live unfused terminal and a short is limited only by the vehicle fuse, with Q7
  (5.7 A) and the 8 A connector in the path. At 1 k it self-limits to 12 mA.
- J9 could no longer drive a bare LED without an external resistor.

Normal current is a non-issue either way — 141 mA through an 0805 link and an
8 A connector is nothing. The difference is purely fault behaviour, which is why
the resistor stays at its as-drawn value.

### D2 fitted too — both channels made identical

J9 and J11 are now the same circuit with the same parts, so either can drive an
LED, a lamp or a relay without rework:

| | J11 (park indicator) | J9 (spare) |
|---|---|---|
| Driver | **AO3400A** 30 V / 5.7 A | **AO3400A** 30 V / 5.7 A |
| Clamp | **D2 = BZX84C24, 24 V** | **D8 = BZX84C24, 24 V** |
| Feed resistor | R30 = 1 k | R31 = 1 k |

Two deviations from the schematic, both deliberate:

**Q1: 2N7002 → AO3400A.** The schematic uses a jellybean 2N7002 because it knew
J11's load was a ~10 mA button LED. At **115 mA** that part cannot drive even a
1.2 W dash bulb — 100 mA steady with ~1 A cold inrush. **60 V is not needed
anywhere on this board**: the rail is 12–14.4 V and the clamps hold the drain to
25.6 V worst case, so trading it for 5.7 A costs nothing real.

The button LED is unaffected — R30 sets the current, the FET is just a switch:

| | LED current @12 V | @14.4 V | FET drop |
|---|---|---|---|
| 2N7002 (7 Ω) | 9.93 mA | 12.31 mA | 69.5 mV |
| AO3400A (30 mΩ) | 10.00 mA | 12.40 mA | 0.3 mV |

Gate drive is fine (Nano 5 V against V_GS(th) 1.45 V max, R_DS specified at
2.5 V), R39's 10 k pulldown still holds it off, and off-state leakage of ~1 µA is
three orders below the ~1 mA an LED needs to glow faintly.

**D2 fitted at 24 V.** Not needed for an LED — a diode has no inductance — but it
is free, invisible in normal operation (22.8 V lower tolerance against a 14.4 V
rail), and means J11 is ready for a relay or lamp without touching the board.

To repurpose either output now, the only change is the feed: leave R30/R31 at
1 k and put the LED across pins 1 and 2, or feed a lamp/relay coil from vehicle
+12 V into pin 2 and leave pin 1 unused.

**The clamp values remain tied to the transistors.** Both are 30 V parts, so both
clamps are 24 V. Fit a different FET and re-check its clamp.

---

## 11. Files

| File | Contents |
|---|---|
| `SRM_CPL_JLCPCB.csv` | **CPL — 82 parts (61 SMT + 21 THT), board-lower-left origin** |
| `SRM_CPL_JLCPCB_gerber-origin.csv` | same, +50/+50 to match the `.pho` frame |
| `SRM_BOM_JLCPCB.csv` | 31 line items, all with LCSC part numbers |
| `SRM_manual_parts.csv` | now empty — nothing is hand-fitted except MOD1 |
| `SRM_positions_all.csv` | all 95 footprints with status and corrected rotation |
| `tools/srm_paths.py` | resolves the design files out of the fork's zips |
| `tools/gen_jlcpcb.py` | generator |
| `tools/verify_transform.py` | 156-point drill match |
| `tools/verify_gerber_offset.py` | drill↔gerber offset correlation |

## 12. Provenance

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
