#!/usr/bin/env python
"""Pretend to be sensor nodes: post readings to the running API over HTTP (for the live demo).

    python scripts/simulate_node.py mudflow --nodes ak-tash-n1,ak-tash-n2 --gap 20
    python scripts/simulate_node.py fire --nodes ak-tash-fire
    python scripts/simulate_node.py heartbeat --nodes ak-tash-n1,ak-tash-n2,ak-tash-n3

Device keys come from .demo_node_keys.json (created by `python manage.py seed_demo`).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent


def post(base, key, payload):
    r = requests.post(f"{base}/api/sensors/ingest/", json=payload, headers={"X-Device-Key": key}, timeout=15)
    if r.status_code >= 400:
        sys.exit(f"HTTP {r.status_code}: {r.text[:200]}")
    return r.json()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scenario", choices=["mudflow", "fire", "heartbeat"])
    p.add_argument("--nodes", required=True, help="Comma-separated device ids, in flow order (upstream first)")
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--keys", default=str(ROOT / ".demo_node_keys.json"))
    p.add_argument("--gap", type=float, default=20.0, help="Seconds between nodes (mudflow)")
    a = p.parse_args()

    keys = json.loads(Path(a.keys).read_text())
    nodes = [n.strip() for n in a.nodes.split(",") if n.strip()]
    missing = [n for n in nodes if n not in keys]
    if missing:
        sys.exit(f"No key for: {', '.join(missing)} (run seed_demo)")

    if a.scenario == "heartbeat":
        for n in nodes:
            print(n, post(a.base, keys[n], {"battery_v": 3.9, "water_level_cm": 80.0, "rain_mm": 0.0}))
    elif a.scenario == "fire":
        for n in nodes:
            print(n, post(a.base, keys[n], {"smoke_ppm": 850, "temperature_c": 68, "crackle_score": 0.8, "battery_v": 3.8}))
    else:
        for i, n in enumerate(nodes):
            for rms in (0.45, 0.80, 1.20):  # ground shaking builds up as the flow passes
                print(n, post(a.base, keys[n], {"vibration_rms": rms, "dominant_freq_hz": 25.0, "water_level_cm": 150 + 30 * i}))
                time.sleep(2)
            if i < len(nodes) - 1:
                print(f"... waiting {a.gap:.0f}s for the flow to reach the next node")
                time.sleep(a.gap)


if __name__ == "__main__":
    main()
