"""Probe Tibber API for real-time measurement fields (incl. L1/L2/L3)."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, List, Set

import requests
import websocket


API_URL = "https://api.tibber.com/v1-beta/gql"
WS_URL = "wss://api.tibber.com/v1-beta/gql"
SUBSCRIPTION_QUERY = """
subscription LiveMeasurement($homeId: ID!) {
  liveMeasurement(homeId: $homeId) {
    timestamp
    power
    powerProduction
    powerPhase1
    powerPhase2
    powerPhase3
    accumulatedConsumption
    accumulatedProduction
    accumulatedConsumptionLastHour
    accumulatedProductionLastHour
    netConsumption
    netProduction
    minPower
    maxPower
    minPowerProduction
    maxPowerProduction
    currentL1
    currentL2
    currentL3
    voltagePhase1
    voltagePhase2
    voltagePhase3
    powerFactor
    signalStrength
  }
}
"""


def fetch_homes(token: str) -> List[Dict]:
    query = """
    query ViewerHomes {
      viewer {
        homes {
          id
          appNickname
          address { address1 postalCode city }
          features { realTimeConsumptionEnabled }
        }
      }
    }
    """
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data.get("data", {}).get("viewer", {}).get("homes", []) or []


def report_home_features(homes: List[Dict]) -> None:
    print("Homes and realtime availability:")
    for home in homes:
        nickname = home.get("appNickname") or home.get("address", {}).get("address1")
        print(
            f"- {nickname} ({home.get('id')}): "
            f"realtime={home.get('features', {}).get('realTimeConsumptionEnabled')}"
        )


def run_realtime_probe(token: str, home_id: str, duration: int = 30) -> Set[str]:
    ws = websocket.create_connection(
        WS_URL,
        header=[f"Authorization: Bearer {token}"],
        timeout=10,
    )
    ws.settimeout(5)
    init_msg = {"type": "connection_init", "payload": {"token": token}}
    ws.send(json.dumps(init_msg))
    start_msg = {
        "id": "1",
        "type": "start",
        "payload": {"query": SUBSCRIPTION_QUERY, "variables": {"homeId": home_id}},
    }
    ws.send(json.dumps(start_msg))
    seen_keys: Set[str] = set()
    start = time.time()
    print(f"Listening for realtime payloads for {duration} seconds...")
    try:
        while time.time() - start < duration:
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if not raw:
                continue
            message = json.loads(raw)
            if message.get("type") != "data":
                continue
            payload = (
                message.get("payload", {})
                .get("data", {})
                .get("liveMeasurement", {})
            )
            if not payload:
                continue
            seen_keys.update(payload.keys())
            print(f"Payload keys: {sorted(payload.keys())}")
    finally:
        try:
            ws.send(json.dumps({"id": "1", "type": "stop"}))
            ws.close()
        except Exception:
            pass
    return seen_keys


def main() -> int:
    token = os.getenv("TIBBER_TOKEN")
    if not token:
        print("Set TIBBER_TOKEN in your environment (e.g., `export TIBBER_TOKEN=...`).")
        return 1
    try:
        homes = fetch_homes(token)
    except Exception as exc:  # noqa: BLE001
        print(f"Error fetching homes: {exc}")
        return 1

    if not homes:
        print("No homes returned from Tibber.")
        return 0

    report_home_features(homes)
    realtime_home = next(
        (h for h in homes if h.get("features", {}).get("realTimeConsumptionEnabled")),
        None,
    )
    if not realtime_home:
        print("No home has realtime enabled; realtime probe skipped.")
        return 0

    home_id = realtime_home["id"]
    keys = run_realtime_probe(token, home_id)
    print("\nSummary:")
    print(f"- Home {home_id} realtime fields observed ({len(keys)}): {sorted(keys)}")
    if {"voltagePhase1", "voltagePhase2", "voltagePhase3"} & keys or {
        "currentL1",
        "currentL2",
        "currentL3",
    } & keys:
        print("- Per-phase metrics detected.")
    else:
        print("- Per-phase metrics NOT detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
