# Error Amplifier for a Capacitor-Less LDO (SKY130)

Error amplifier (EA) design for an on-chip capacitor-less LDO for WPT-powered implantable biosensors
(13.56 MHz ripple, 1-20 mA load, PSR >= 45 dB, phase margin >= 45 deg). Simulated with xschem + ngspice
on the SKY130 open-source PDK (installed with `ciel` in WSL Ubuntu).

## Contents

| File | What it is |
|---|---|
| `error_amplifier_spec.md` | Specification, design status, simulation results (read section 9 first) |
| `ea_fc.py` | Netlist generator + open-loop AC bench for the folded-cascode EA with class-A buffer |
| `ea_sweep.sh` | Corner and VIN sweep of the EA |
| `compare_pass.py` | Pass-transistor comparison script (1.8 V devices) |
| `ea_folded_cascode.cir`, `ea_folded_cascode_buffered.cir` | Generated ngspice netlists |
| `xschemrc`, `.spiceinit` | xschem and ngspice config that load the SKY130 PDK |

## Current status

Folded-cascode EA (5 V devices, wide-swing mirror, class-A follower buffer), about 18 uA.
Meets gain and phase targets for VIN up to 3.3 V; at VIN = 5 V the gain is up to 4 dB short.
Full-loop (C-multiplier, pass device, CFFRC) stability is not yet simulated.

## Run it (WSL Ubuntu)

The PDK location is read from the `PDK_ROOT` environment variable (default `~/.ciel`). The committed `.cir` files
are generated snapshots with a hardcoded path; regenerate them with `ea_fc.py` on a new machine.

```bash
export PDK_ROOT=~/.ciel   # or wherever ciel installed the PDK
```

```bash
IT=6e-6 IPT=5e-6 BUF=1 BW=3 BI=2.5e-6 python3 ea_fc.py 3.3 2.0 tt 27 ac
```

Arguments: VIN, DC level at the EA output, process corner, temperature, mode (`ac` or `op`).
