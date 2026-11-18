#!/bin/bash
# sweep.sh
# Sends every possible NEC command byte (0x00 to 0xFF) one at a time and
# asks what the LED strip did, logging anything that had an effect.
#
# Usage:
#   sudo ./sweep.sh          start from 0x00
#   sudo ./sweep.sh 0x47     resume from a specific code

ADDRESS="0xeac7"       # Roku address (the LED strip ignores it)
RESET="0xeac71c"       # sets the strip to solid white before each test
LOG="led_codes.csv"
START="${1:-0}"

# ---------- Find the transmitter ----------
# lirc device numbers can change between boots, so ask each one if it can send.
DEV=""
for d in /dev/lirc*; do
  if ir-ctl -f -d "$d" 2>/dev/null | grep -q "Device can send"; then
    DEV="$d"
    break
  fi
done

if [ -z "$DEV" ]; then
  echo "No IR transmitter found. Check the gpio-ir-tx overlay and wiring."
  exit 1
fi
echo "Using transmitter: $DEV"

# ---------- Log file ----------
# Only write the header if the log doesn't exist yet, so resuming never wipes results.
[ -f "$LOG" ] || echo "code,result" > "$LOG"

send() {
  ir-ctl -d "$DEV" -S necx:"$1"
}

# ---------- Sweep ----------
for c in $(seq $((START)) 255); do
  code=$(printf "%s%02x" "$ADDRESS" "$c")

  while true; do
    send "$RESET"      # put the strip in a known state first
    sleep 1
    send "$code"
    read -p "$code -> what happened? (r = resend, q = quit, enter = nothing): " result
    [ "$result" != "r" ] && break
  done

  if [ "$result" = "q" ]; then
    echo "Stopped at $code. Resume with: sudo $0 $(printf "0x%02x" "$c")"
    exit 0
  fi

  [ -n "$result" ] && echo "$code,$result" >> "$LOG"
done

echo "Done. Results saved to $LOG"
