#!/bin/bash
# usage: sweep.sh  (runs the trimmed EA over corners and VIN)
SP="$(cd "$(dirname "$0")" && pwd)"
export IT=6e-6 IPT=5e-6 BUF=1 BW=5 BI=2.5e-6
cd "${TMPDIR:-/tmp}"
run() { # vin vod corner temp
  out=$(python3 -I "$SP/ea_fc.py" $1 $2 $3 $4 ac 2>&1)
  iq=$(echo "$out" | grep -E '^-i\(vdd\)' | awk '{printf "%.1f", $3*1e6}')
  vo=$(echo "$out" | grep -E '^v\(out\)' | awk '{printf "%.2f", $3}')
  a0=$(echo "$out" | grep -E '^A0' | sed -E 's/A0 = ([-0-9.]+) dB.*/\1/')
  ph=$(echo "$out" | grep -E '^phase at' | sed -E 's/.*at 100 kHz = ([-0-9.]+) deg/\1/')
  echo "VIN=$1 gate=$2 $3/${4}C : Iq=${iq}uA out=${vo}V A0=${a0}dB phase@100k=${ph}deg"
}
run 3.3 2.0 tt 27
run 3.3 2.0 ss 85
run 3.3 2.0 ff 0
run 3.3 2.0 fs 27
run 3.3 2.0 sf 27
run 5.0 3.5 tt 27
run 2.5 1.0 tt 27
run 1.9 0.8 tt 27
