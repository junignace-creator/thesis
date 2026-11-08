# Error Amplifier Specification
**Project:** On-Chip Capacitor-Less LDO for WPT-Powered Implantable Biosensors (Tabor, UST MSEE, May 2026)
**Block:** Error amplifier (EA) of the PMOS-based capless LDO
**Process / tools:** SKY130 (sky130A), xschem + ngspice

> **How to read this document.**
> - **[Thesis]** = taken directly from your proposal (page cited).
> - **[Derived]** = my engineering derivation from the thesis architecture. These are *starting targets*. Refine them after the first closed-loop simulation.
> - **[Assumed]** = the thesis does not state it. I picked a reasonable value so you can start. Confirm with your advisor or change it.

---

## 1. Role of the EA in the architecture

The thesis uses a **three-band PSR strategy** (pp. 65-66):

| Band | Mechanism | Who provides PSR |
|---|---|---|
| < 100 kHz | Feedback loop with high DC loop gain | **Error amplifier** |
| mid-frequency | C-multiplier shunts ripple (primary job: stabilize output pole) | C-multiplier |
| up to 13.56 MHz | Current-mode feed-forward ripple cancellation (Mffrc, split pass transistor) | CFFRC |

- The EA output drives the **gate of Mmain only** (p. 72). Mffrc is strictly feed-forward, with no path from the output back to its gate (p. 68).
- Because the C-multiplier makes the **output node the dominant pole** (p. 67), the EA output pole (the gate of Mmain) must stay **non-dominant** across the 1-20 mA load range.
- The thesis says the EA is characterized for **DC gain, UGB, output impedance, and phase contribution in the low-frequency PSR region** (p. 70). Section 4 covers each one.

## 2. System-level targets the EA must support [Thesis, Table 2, p. 69]

| Parameter | Target |
|---|---|
| PSR (full spectrum up to 13.56 MHz) | >= 45 dB |
| Phase margin | >= 45 deg across the full load range |
| Load range | 1 mA - 20 mA |
| Pass device | PMOS, no charge pump |
| Process | SKY130 130 nm |
| Corners (final optimization) | TT, FF, SS, FS, SF (pp. 10, 74) |

## 3. Operating conditions

| Item | Value | Source |
|---|---|---|
| Regulated VOUT | **1.8 V** | [Your decision] |
| Supply VIN | **1.9 V nominal** (dropout target **<= 100 mV** at 20 mA) | [Your decision] The thesis test bench used 1.8 V, which cannot regulate to 1.8 V. 1.9 V stays under the ~1.95 V limit of the 1.8 V devices. |
| Pass device | `sky130_fd_pr__pfet_01v8`, **L = 0.15 um, W ~ 900 um** (5 um x 180) | [Simulated] Chosen over LVT; see section 3a. |
| Ripple test signal | 1 V AC on VIN, 1 kHz - 100 MHz sweep | [Thesis] pp. 70, 73 |
| Reference VREF | **0.9 V** | [Assumed] |
| Feedback divider ratio beta | 0.5 (VFB = 0.9 V at VOUT = 1.8 V) | [Assumed] |
| Nominal verification | TT, nominal VIN, room temperature first, then PVT sweep | [Thesis] p. 72 |
| PVT sweep (later) | VIN +/-10 %; temperature 0 / 27 / 85 C | [Assumed] |

The EA inputs sit at about 0.9 V (VREF and VFB), so an **NMOS-input pair** works. VREF was not stated in the pages I read, so confirm it.

> **Device voltage.** SKY130's 1.8 V devices (`*_01v8`) have an absolute maximum around 1.95 V. With VIN = 1.9 V the 1.8 V devices stay in range. Ripple on VIN must not push the peak above ~1.95 V, and the ripple valleys must stay above 1.8 V + dropout, or the pass device falls out of regulation.

### 3a. Pass-device comparison (ngspice, SKY130 models, script in `compare_pass.py`)

Both options were sized to deliver 20 mA at about 100 mV drop.

| Result | Option 1: std, L=0.15, W=900 um | Option 2: LVT, L=0.35, W=1000 um |
|---|---|---|
| Dropout at 20 mA, TT 27 C | ~73 mV | ~82 mV |
| Dropout at 20 mA, SS 85 C | ~82 mV | ~100 mV (no margin; gate must reach 0 V) |
| Gate capacitance, 1 / 5 / 20 mA | 0.9 / 1.1 / 1.2 pF | 1.4 / 2.5 / 2.9 pF |
| Intrinsic gain gm/gds at 20 mA, 0.3 V headroom (TT / SS) | 2.8 / 2.1 | 1.3 / 1.0 |
| Intrinsic gain gm/gds at 1 mA, 0.3 V headroom (TT / SS) | 7.8 / 10.5 | 8.5 / 8.4 |
| Gate voltage needed at VIN = 1.9 V, 1 mA to 20 mA (SS 85 C) | 1.16 V down to 0.29 V | 1.42 V down to 0.00 V |

**Decision: Option 1 (standard device, minimum length).** It has more dropout margin, less than half the gate capacitance at 20 mA, and equal or better gain. The LVT option's longer channel did not buy more gain in this comparison. Caveat: DC and small-signal results only; layout wiring resistance will add to the dropout.

## 4. Specification table

| # | Parameter | Target | Notes / basis |
|---|---|---|---|
| EA-1 | **DC open-loop gain, A0** | **>= 60 dB** | [Derived] Loop DC gain = A0 x (gm,p*ro,p) x beta. This must be high enough that the feedback band delivers >= 45 dB PSR at low frequency, with margin for corners. |
| EA-2 | **Gain-bandwidth (UGB), EA alone** | **>= 5 MHz** (loaded by Mmain gate) | [Derived] Starting value. The loop must still have PM >= 45 deg once the C-multiplier sets the dominant pole. Tune from loop simulation. |
| EA-3 | **Output impedance, Rout** | As **low** as practical. Output pole `1/(2*pi*Rout*Cgate,Mmain)` must be **>= 3 x loop UGB** at 20 mA. | [Derived] Mmain is large at 20 mA, so Cgate is large. A high-Rout output makes the gate node a second dominant pole. |
| EA-4 | **Phase contribution, 1 kHz - 100 kHz** | EA phase shift **> -45 deg** inside the low-frequency PSR region (< 100 kHz); no zero/pole pair that pushes the loop below 45 deg PM | [Thesis] p. 70 asks for this characterization. The numeric target is [Derived]. |
| EA-5 | **Load capacitance (design for)** | **Cgg of Mmain = 0.9 - 1.2 pF** (900 um, L=0.15) | [Simulated] Use 1.2 pF as the EA load in simulation. |
| EA-6 | **Quiescent current** | **<= 20 uA** | [Assumed] Implant power budget. Total LDO Iq budget is not given in the pages I read. |
| EA-7 | **Input common-mode range** | Must include 0.9 V +/- 0.1 V at all corners | Follows from the VREF assumption. |
| EA-8 | **Systematic input offset** | <= 5 mV (3-sigma random offset <= 15 mV) | [Assumed] Sets DC output accuracy: dVout = dVos / beta. |
| EA-9 | **Output swing** | EA output must cover **0.2 V to 1.5 V** (low side reaches near ground; the high side is for lighter-than-1 mA loads) | [Simulated] At VIN = 1.9 V and 100 mV drop, Mmain needs a gate voltage of about 1.16 V at 1 mA and 0.29 V at 20 mA (SS, 85 C). The EA output stage must therefore be rail-to-rail on the low side. |
| EA-10 | **PSR of the EA itself** | **>= 45 dB from 1 kHz up to 100 kHz** (same as the system target) | [Your decision] Defined as 20*log10(ripple at the EA output / ripple on VIN), with the EA output gating a PMOS referenced to VIN. Because the pass-transistor gate is referenced to VIN, a gate that tracks VIN gives zero Vgs ripple; so measure the *Vgs-referred* ripple as well, which is the number that matters. Report both. |
| EA-11 | **Load range behavior** | Specs EA-1 to EA-4 hold with Mmain biased at **1, 5, 10, 20 mA** | [Thesis] p. 74 uses 4 load points. |

## 5. Suggested topology (starting point, not required by the thesis)

- Single-stage **telescopic or folded-cascode OTA** with a **source-follower or class-A buffer** to drive the Mmain gate, **or** a **two-stage** (5T OTA + common-source stage) if A0 >= 60 dB is not reachable in one stage on 1.8 V.
- Devices: `sky130_fd_pr__nfet_01v8` (input pair, tail), `sky130_fd_pr__pfet_01v8` (loads / mirrors). Minimum L = 0.15 um; use L >= 0.5 um in the input pair and mirrors for gain/matching.
- Cap-less on the EA: no Miller capacitor unless EA-4 fails. The C-multiplier is the compensation strategy of the system.

## 6. Test benches to build (xschem, folder `~/error_amplifier`)

1. **TB1: Open-loop AC of the EA alone.** VREF = 0.9 V DC, VFB = 0.9 V DC + 1 V AC. Load = Cgate of Mmain (EA-5). Report A0, UGB, phase at UGB, Rout (current-probe or AC test source at the output).
2. **TB2: Systematic offset and input CM range.** DC sweep of VFB, find the offset and the range where gain stays within 3 dB of A0.
3. **TB3: Loop gain with Mmain.** EA + Mmain (+ Mffrc off) + divider + 1-20 mA load, loop broken at the feedback node. Report DC loop gain, UGB, PM at 1 / 5 / 10 / 20 mA.
4. **TB4: EA PSR.** 1 V AC on VIN, report EA output ripple vs frequency from 1 kHz to 100 kHz, plus the Vgs-referred ripple of Mmain (EA-10). Pass if >= 45 dB across the band.
5. **TB5: Corners.** Repeat TB1 and TB3 at TT, FF, SS, FS, SF (`.lib ... sky130.lib.spice <corner>`).

## 7. Pass/fail checklist

- [ ] A0 >= 60 dB (TT, then all corners)
- [ ] EA UGB >= 5 MHz at all four load points
- [ ] Output pole >= 3 x loop UGB at 20 mA
- [ ] Phase contribution OK below 100 kHz
- [ ] Iq <= 20 uA
- [ ] Loop PM >= 45 deg at 1 / 5 / 10 / 20 mA (TB3)
- [ ] Offset <= 5 mV systematic
- [ ] EA PSR >= 45 dB, 1 kHz - 100 kHz (EA-10)

## 8. Open questions to confirm with your advisor

1. Is VIN = 1.9 V (100 mV dropout) available from the rectifier, and how much 13.56 MHz ripple rides on it? The ripple valleys eat the 100 mV headroom.
2. Reference voltage source: ideal VREF source, or a bandgap block to be designed later?
3. Total LDO quiescent current budget (I assumed EA <= 20 uA).
4. Temperature range for the PVT sweep (an implant stays near 37 C).
5. Whether A0 = 60 dB and UGB = 5 MHz are acceptable starting points, or if the thesis has stricter numbers elsewhere.

---

## 9. Design status (current EA: folded cascode + class-A follower buffer)

> **Supersedes** the 1.8 V-device / VIN = 1.9 V assumptions in sections 3 and 3a. The design now targets **VIN up to 5 V with 5 V devices** (`sky130_fd_pr__*_g5v0d10v5`), VREF = 1.2 V (assumed), VOUT = 1.8 V. The pass-device sizing for the lowest VIN is still undecided. Sections 3/3a/EA-9 will be refreshed once it is.

**Topology** (`ea_folded_cascode_buffered.cir`, generator `ea_fc.py`): NMOS input pair, PMOS top current sources, PMOS cascodes, NMOS cascode mirror, then a complementary class-A source-follower buffer (PMOS follower then NMOS follower, shifts cancel) driving 1.3 pF (Mmain gate). Currents: tail 6 uA, top PMOS 5 uA each, follower 2.5 uA each, master references 1 uA + 1 uA. Biasing of the cascode gates is **ideal** (not yet a real bias circuit).

**Results** (ngspice, open loop, 1.3 pF load):

| Condition | Iq | A0 | Phase at 100 kHz |
|---|---|---|---|
| VIN 3.3 V, TT 27 C | 16.0 uA | 63.7 dB | -20 deg |
| VIN 3.3 V, SS 85 C | 16.2 uA | 63.2 dB | -22 deg |
| VIN 3.3 V, FF 0 C | 15.9 uA | 63.8 dB | -19 deg |
| VIN 3.3 V, FS 27 C | 14.2 uA | **56.6 dB** | -24 deg |
| VIN 3.3 V, SF 27 C | 15.7 uA | 63.6 dB | -20 deg |
| VIN 5.0 V, TT 27 C | 16.0 uA | 62.5 dB | -17 deg |
| VIN 2.5 V, TT 27 C | 16.0 uA | 62.8 dB | -22 deg |
| VIN 1.9 V, TT 27 C | 16.0 uA | **52.8 dB** | -17 deg |

Status vs spec: EA-1 (A0 >= 60 dB) met except **FS corner and VIN = 1.9 V**; EA-2 (UGB >= 5 MHz) met (about 40 MHz); EA-4 (phase > -45 deg below 100 kHz) met; EA-6 (Iq <= 20 uA) met at 16 uA. EA-3 (output pole about 300 kHz) depends on the loop UGB, still to be measured. EA-10 (EA PSR) not yet measured; needs a real bias circuit.

### 9.1 Update: wide-swing mirror and real cascode bias

The two weak cases above had one cause: the bottom mirror's diode-connected device wasted 0.76 V of headroom and the cascode gate voltages were fixed numbers. At VIN = 1.9 V the output sat 28 mV above the mirror node, so the NMOS cascode fell out of saturation; at the FS corner a top-PMOS node floated up to VIN. Fix: a **wide-swing cascode mirror** (mirror gates tied to the cascode drain node) with the cascode biases **generated by diode-connected devices at 1/4 W/L** carrying 1 uA copy currents, so they track corner, temperature and VIN (no ideal voltage sources remain in the bias path; the reference currents are still ideal). Cascode devices are 0.8 um long (W/L = 40); bias diodes are 20 um (NMOS) and 16 um (PMOS) long. Supply current is now **~18 uA** (budget 20 uA).

**Gain vs pole is a fixed trade.** A0 x (EA pole) is about 265 MHz, set by the high-impedance node's capacitance (about 35 fF, mostly device parasitics, not the follower). A0 >= 60 dB and < 45 deg lag at 100 kHz therefore only fit together for A0 between about 60 dB and 68 dB. Cascode length 0.75 to 0.8 um lands inside that window; 0.9 um gives 68-70 dB but 46-54 deg of lag at 100 kHz (fails EA-4), and 1.0 um gives 74 dB with 60-69 deg of lag.

| Condition | A0 | EA pole | Phase at 100 kHz |
|---|---|---|---|
| VIN 3.3 V TT 27 C | 66.0 dB | - | -32 deg |
| VIN 3.3 V SS 85 C | 65.2 dB | - | -34 deg |
| VIN 3.3 V FF 0 C | 66.4 dB | - | -32 deg |
| VIN 3.3 V FS | 64.5 dB | - | -28 deg |
| VIN 3.3 V SF | 67.2 dB | - | -35 deg |
| VIN 2.5 V TT | 65.6 dB | - | -33 deg |
| VIN 1.9 V TT | 63.8 dB | 200 kHz | -29 deg |
| VIN 1.9 V SS 85 C | 62.8 dB | 200 kHz | -30 deg |
| VIN 1.9 V FF 0 C | 64.3 dB | 200 kHz | -28 deg |
| VIN 1.9 V FS | 62.3 dB | 251 kHz | -25 deg |
| VIN 1.9 V SF | 64.5 dB | 178 kHz | -31 deg |
| VIN 5.0 V TT | **59.8 dB** | 251 kHz | -17 deg |
| VIN 5.0 V SS 85 C | **56.2 dB** | 501 kHz | -13 deg |
| VIN 5.0 V FF 0 C | 60.8 dB | 355 kHz | -17 deg |
| VIN 5.0 V FS | **55.9 dB** | 631 kHz | -11 deg |
| VIN 5.0 V SF | 63.3 dB | 251 kHz | -23 deg |

**Open item:** at **VIN = 5 V** the gain is 0.2 dB (TT), 3.8 dB (SS) and 4.1 dB (FS) below the 60 dB target. Lengthening the mirror devices did not help (+0.2 dB), so the limit is elsewhere (suspects: the high 3.4 V drain-source voltage across the NMOS cascode, or the PMOS side). Phase lag at 5 V is small (11-23 deg), so there is room to raise the gain there. All conditions at VIN <= 3.3 V meet EA-1, EA-4 and EA-6.
