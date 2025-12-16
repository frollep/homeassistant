# Tibber probe notes

Use this page to capture results from `tools/tibber_probe.py`:

- Date/time of probe
- Home ID used
- Keys observed in realtime payloads
- Whether L1/L2/L3 metrics were present
- Any anomalies (missing values, disconnects)

Command reminder:
```bash
cp .env.example .env
export TIBBER_TOKEN=...
pip install requests websocket-client
python tools/tibber_probe.py
```
