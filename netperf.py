#!/usr/bin/python3

import subprocess
import time

interface = "enx2800af245ce4"
interval = 1  # seconds

def get_rx_bytes():
    cmd = f"ip -s link show {interface} | head -4 | tail -1 | awk '{{print $1}}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return int(result.stdout.strip())
    return 0

print(f"Monitoring RX on {interface} using shell... (Ctrl+C to stop)")
while True:
    rx1 = get_rx_bytes()
    time.sleep(interval)
    rx2 = get_rx_bytes()

    rx_bps = (rx2 - rx1) / interval / 100000
    print(f"RX: {rx_bps:.2f} bps")
