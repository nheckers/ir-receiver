#!/bin/bash
DEV=/dev/lirc1
LOG=led_codes.csv
echo "code,result" > "$LOG"

for c in $(seq 0 255); do
  code=$(printf "0xeac7%02x" "$c")
  while true; do
    ir-ctl -d "$DEV" -S necx:"$code"
    read -p "$code -> what happened? (r = resend, enter = nothing): " result
    [ "$result" != "r" ] && break
  done
  [ -n "$result" ] && echo "$code,$result" >> "$LOG"
done
echo "Done. Results saved to $LOG"