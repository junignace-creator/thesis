"""Folded-cascode error amplifier (SKY130 5V devices), open-loop AC bench generator.
Usage: python3 ea_fc.py [VIN] [VOUT_DC_TARGET] [corner] [temp] [mode]
mode: op | ac
"""
import subprocess, sys, os, re, math, cmath

PDK_ROOT = os.environ.get("PDK_ROOT", os.path.expanduser("~/.ciel"))
LIB = os.path.join(PDK_ROOT, "sky130A/libs.tech/combined/sky130.lib.spice")
WORK = os.path.join(os.environ.get("TMPDIR", "/tmp"), "eafc")
os.makedirs(WORK, exist_ok=True)

VIN = float(sys.argv[1]) if len(sys.argv) > 1 else 3.3
VOD = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0     # desired DC level at EA output (gate of Mmain)
CORNER = sys.argv[3] if len(sys.argv) > 3 else "tt"
TEMP = sys.argv[4] if len(sys.argv) > 4 else "27"
MODE = sys.argv[5] if len(sys.argv) > 5 else "ac"
VREF = 1.2
CL = 1.3e-12
BUF = int(os.environ.get("BUF", "0"))
BNL = float(os.environ.get("BNL", "20"))      # length of NMOS cascode-bias diode (sets Vbnc)
BPL = float(os.environ.get("BPL", "16"))      # length of PMOS cascode-bias diode (sets Vbpc)
BW = float(os.environ.get("BW", "10"))        # follower width (um)
BI = float(os.environ.get("BI", "4e-6"))      # follower bias current

N = "sky130_fd_pr__nfet_g5v0d10v5"
P = "sky130_fd_pr__pfet_g5v0d10v5"

# (W um, L um, m)
S = dict(
    M1=(10, 1.0, 2), M2=(10, 1.0, 2),      # input pair, 20 um each
    M5=(10, 1.0, 4),                       # tail (2x mirror of Mb1 -> see Mb1)
    Mb1=(10, 1.0, 2),
    M3=(10, 1.0, 2), M4=(10, 1.0, 2), Mbp=(10, 1.0, 2),
    M6=(10, 1.0, 4), M7=(10, 1.0, 4),
    M8=(10, 1.0, 4), M9=(10, 1.0, 4),
    M10=(10, float(os.environ.get("ML", "1.0")), int(round(2 * float(os.environ.get("ML", "1.0"))))),
    M11=(10, float(os.environ.get("ML", "1.0")), int(round(2 * float(os.environ.get("ML", "1.0"))))),
)
ITAIL_REF = 1e-6      # master reference into Mb1 (mirrored up to the tail)
IP_REF = 1e-6         # master reference into Mbp (mirrored up to the top PMOS)
IT = float(os.environ.get("IT", "6e-6"))   # tail current
IPT = float(os.environ.get("IPT", "5e-6")) # each top PMOS current
CASL = float(os.environ.get("CASL", "0.8"))   # cascode length; keep W/L = 40 so the bias still centres
for _n in ("M6", "M7", "M8", "M9"):
    S[_n] = (10, CASL, int(round(4 * CASL)))
S["M5"] = (10, 1.0, int(round(2 * IT / ITAIL_REF)))
S["M3"] = (10, 1.0, int(round(2 * IPT / IP_REF)))
S["M4"] = S["M3"]


def dev(name, d, g, s, b, model):
    w, l, m = S[name]
    return f"X{name} {d} {g} {s} {b} {model} w={w} l={l} m={m}\n"


def netlist(ac=True):
    n = f"folded cascode EA, VIN={VIN}\n.lib {LIB} {CORNER}\n.temp {TEMP}\n"
    n += f"Vdd vdd 0 {VIN}\n"
    n += f"Vref vp 0 {VREF} ac {1 if ac else 0}\n"
    # bias
    n += f"Ib1 vdd vbt 0\n"  # placeholder replaced below
    n = n.replace("Ib1 vdd vbt 0\n", "")
    n += f"Iref1 vdd vbt {ITAIL_REF}\n"
    n += dev("Mb1", "vbt", "vbt", "0", "0", N)
    n += dev("M5", "tail", "vbt", "0", "0", N)
    n += dev("Mbp", "vbp", "vbp", "vdd", "vdd", P)
    n += f"Iref2 vbp 0 {IP_REF}\n"
    # real cascode bias (wide-swing): diode-connected devices at 1/4 W/L carrying the 1 uA copy currents
    # Vbnc = Vth + 2*Vov (NMOS), Vbpc = VIN - (Vth + 2*Vov) (PMOS); both track corner/temp/VIN
    n += f"Xmbp2 vbnc vbp vdd vdd {P} w=10 l=1.0 m=2\n"          # 1 uA copy of Mbp
    n += f"XmbN vbnc vbnc 0 0 {N} w=10 l={BNL} m=1\n"
    n += f"Xmb4n vbpc vbt 0 0 {N} w=10 l=1.0 m=2\n"              # 1 uA copy of Mb1
    n += f"XmbP4 vbpc vbpc vdd vdd {P} w=10 l={BPL} m=1\n"
    # core
    n += dev("M1", "f1", "vp", "tail", "0", N)
    n += dev("M2", "f2", "vfb", "tail", "0", N)
    n += dev("M3", "f1", "vbp", "vdd", "vdd", P)
    n += dev("M4", "f2", "vbp", "vdd", "vdd", P)
    n += dev("M6", "n1", "vbpc", "f1", "vdd", P)
    n += dev("M7", "eo" if BUF else "out", "vbpc", "f2", "vdd", P)
    n += dev("M8", "n1", "vbnc", "m1", "0", N)
    n += dev("M9", "eo" if BUF else "out", "vbnc", "m2", "0", N)
    n += dev("M10", "m1", "n1", "0", "0", N)     # wide-swing cascode mirror: gates tied to n1
    n += dev("M11", "m2", "n1", "0", "0", N)
    n += f"Cl out 0 {CL}\n"
    if BUF:
        # complementary class-A follower pair: PMOS follower (+Vsg) then NMOS follower (-Vgs)
        n += f"Xmpf 0 eo x1 x1 {P} w={BW} l=0.5 m=1\n"
        n += f"Ibp vdd x1 {BI}\n"
        n += f"Xmnf vdd x1 out 0 {N} w={BW} l=0.5 m=1\n"
        n += f"Ibn out 0 {BI}\n"
    # DC feedback with level shift so out sits at VOD, open for AC
    n += f"Lfb out xfb 1e12\n"
    n += f"Vos vfb xfb {{-({VOD}-{VREF})}}\n"
    n += "Cfb vfb 0 1e3\n"
    return n


def run(net, name):
    p = f"{WORK}/{name}.cir"
    open(p, "w").write(net)
    r = subprocess.run(["ngspice", "-b", p], capture_output=True, text=True)
    return r.stdout + r.stderr


if MODE == "op":
    net = netlist(ac=False) + """.control
set ngbehavior=hsa
op
print v(out) v(vfb) v(tail) v(f1) v(f2) v(n1) v(m1) v(m2) v(vbt) v(vbp)
print -i(Vdd)
.endc
.end
"""
    print(run(net, "op")[-2500:])
    sys.exit()

net = netlist(ac=True) + f""".control
set ngbehavior=hsa
op
print -i(Vdd)
print v(out) v(eo) v(f1) v(f2) v(m1) v(m2) v(n1) v(tail)
ac dec 20 1 1G
wrdata {WORK}/ac.txt v(out)
.endc
.end
"""
out = run(net, "ac")
for line in out.splitlines():
    if line.strip().startswith(("-i(", "v(", "i(", "Error", "error")) or "fatal" in line.lower():
        print(line)

f, H = [], []
for line in open(f"{WORK}/ac.txt"):
    a = line.split()
    f.append(float(a[0])); H.append(complex(float(a[1]), float(a[2])))
mag = [20 * math.log10(abs(h)) for h in H]
ph = [math.degrees(cmath.phase(h)) for h in H]
# unwrap
for i in range(1, len(ph)):
    while ph[i] - ph[i - 1] > 180: ph[i] -= 360
    while ph[i] - ph[i - 1] < -180: ph[i] += 360
a0 = mag[0]
ugb = None
for i in range(len(f) - 1):
    if mag[i] >= 0 > mag[i + 1]:
        t = mag[i] / (mag[i] - mag[i + 1])
        ugb = f[i] * (f[i + 1] / f[i]) ** t
        ph_ugb = ph[i] + t * (ph[i + 1] - ph[i])
        break
# -3 dB point
f3 = next((f[i] for i in range(len(f)) if mag[i] < a0 - 3), None)
print(f"A0 = {a0:.1f} dB   f(-3dB) = {f3}   UGB = {ugb}   phase@UGB = {ph_ugb if ugb else None}")
print(f"phase at 1 kHz = {ph[min(range(len(f)), key=lambda i: abs(f[i]-1e3))]:.1f} deg, at 100 kHz = {ph[min(range(len(f)), key=lambda i: abs(f[i]-1e5))]:.1f} deg")
