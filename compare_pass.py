import subprocess, re, math, os, sys

LIB = "/home/johni/.ciel/sky130A/libs.tech/combined/sky130.lib.spice"
WORK = "/tmp/passcmp"
os.makedirs(WORK, exist_ok=True)

OPTS = {
    "1: std  L=0.15 W=900um": ("sky130_fd_pr__pfet_01v8", 0.15, 180),      # 5um x 180
    "2: LVT  L=0.35 W=1000um": ("sky130_fd_pr__pfet_01v8_lvt", 0.35, 200),  # 5um x 200
}
CORNERS = [("tt", 27), ("ss", 85)]
LOADS_MA = [1, 5, 20]
VIN, VOUT = (float(sys.argv[1]) if len(sys.argv) > 1 else 1.9), 1.8


def run(netlist, name):
    p = os.path.join(WORK, name + ".cir")
    open(p, "w").write(netlist)
    r = subprocess.run(["ngspice", "-b", p], capture_output=True, text=True)
    return r.stdout + r.stderr


def dc_sweep(dev, L, m, corner, temp):
    net = f"""dc
.lib {LIB} {corner}
.temp {temp}
Xm d g s s {dev} w=5 l={L} m={m}
Vs s 0 {VIN}
Vg g 0 0
Vd d 0 {VOUT}
.control
set ngbehavior=hsa
dc Vg 0 {VIN} 0.01
wrdata {WORK}/dc.txt i(Vd)
.endc
.end
"""
    run(net, "dc")
    xs, ys = [], []
    for line in open(f"{WORK}/dc.txt"):
        a = line.split()
        xs.append(float(a[0])); ys.append(float(a[1]))
    return xs, ys


def find_vg(xs, ys, target):
    # current falls as Vg rises; find crossing
    for i in range(len(xs) - 1):
        if (ys[i] - target) * (ys[i + 1] - target) <= 0 and ys[i] != ys[i + 1]:
            f = (target - ys[i]) / (ys[i + 1] - ys[i])
            return xs[i] + f * (xs[i + 1] - xs[i])
    return None


def ac_point(dev, L, m, corner, temp, vg):
    net = f"""ac
.lib {LIB} {corner}
.temp {temp}
Xm d g s s {dev} w=5 l={L} m={m}
Vs s 0 {VIN}
Vg g 0 {vg} ac 1
Vd d 0 {VOUT} ac 0
.control
set ngbehavior=hsa
op
ac lin 1 1k 1k
let gm = mag(i(Vd))
print gm
alter Vg ac = 0
alter Vd ac = 1
ac lin 1 1k 1k
let gds = mag(i(Vd))
print gds
alter Vg ac = 1
alter Vd ac = 0
ac lin 1 10Meg 10Meg
let cgg = mag(i(Vg))/(2*pi*10e6)
print cgg
.endc
.end
"""
    out = run(net, "ac")
    res = {}
    for k in ("gm", "gds", "cgg"):
        mm = re.search(rf"^{k}\s*=\s*([-\d.e+]+)", out, re.M)
        res[k] = float(mm.group(1)) if mm else float("nan")
    return res


print(f"VIN={VIN} V  VOUT={VOUT} V  (Vsd = {VIN-VOUT:.2f} V)\n")
for oname, (dev, L, m) in OPTS.items():
    print("=" * 78)
    print("OPTION", oname)
    for corner, temp in CORNERS:
        xs, ys = dc_sweep(dev, L, m, corner, temp)
        imax = ys[0]
        print(f"  [{corner.upper()} {temp}C]  max current (Vg=0, Vsd=0.1V) = {imax*1e3:.1f} mA"
              f"  -> dropout at 20 mA ~ {100*20/(imax*1e3):.0f} mV" if imax else "")
        print(f"   {'Iload':>6} {'Vg(V)':>7} {'gm(mS)':>8} {'gds(mS)':>8} {'gm/gds':>7} {'Cgg(pF)':>8}")
        for ma in LOADS_MA:
            vg = find_vg(xs, ys, ma * 1e-3)
            if vg is None:
                print(f"   {ma:>4}mA  cannot reach this current (max {imax*1e3:.1f} mA)")
                continue
            r = ac_point(dev, L, m, corner, temp, vg)
            ga = r["gm"] / r["gds"] if r["gds"] else float("nan")
            print(f"   {ma:>4}mA {vg:7.3f} {r['gm']*1e3:8.2f} {r['gds']*1e3:8.2f} {ga:7.1f} {r['cgg']*1e12:8.2f}")
    print()
