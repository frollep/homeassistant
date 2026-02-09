# Home Assistant (Docker on WSL2)

Minimal base repo for running Home Assistant via Docker Desktop in WSL2 with tracked configuration.

## Prerequisites
- Docker Desktop with WSL2 integration enabled
- Git installed in the WSL2 distro
- Python 3 (for Tibber probe tooling)

## Usage
- Start stack: `docker compose up -d`
- Stop stack: `docker compose down`
- Tail HA logs: `docker compose logs -f homeassistant`

Home Assistant UI: http://localhost:8123

## Backup (recommended)
Git only tracks the config files in this repo. For a full restore after reinstall,
also back up secrets and Home Assistant storage/state.

Backup command:
```bash
tar -czf ha_backup_$(date +%Y%m%d).tar.gz \
  .env config/.storage config/secrets.yaml config/home-assistant_v2.db
```

Restore:
1) Clone the repo and restore `.env`
2) Extract the backup in the repo root
3) Start: `docker compose up -d`

## Tibber Pulse probe (fields & per-phase check)
- Install deps (one-time): `pip install requests websocket-client`
- Copy env template: `cp .env.example .env` and set `TIBBER_TOKEN`.
- Run: `make probe` (or `python tools/tibber_probe.py`).
- Expected output: homes with realtime flag plus live payload keys printed for ~30s; note whether `powerPhase1/2/3`, `currentL1..3`, `voltagePhase1..3` appear.

### Probe report template
- Fields observed: `<paste keys from probe>`
- Per-phase present: `<yes/no>`
- Recommendation: `<proceed with HA integration / consider alternate metering>`

## Custom integration: tibber_pulse_phases
- Copy `custom_components/tibber_pulse_phases/` into your HA `config/custom_components/`.
- Restart HA, add integration **Tibber Pulse Phases**, paste Tibber token, select home.
- Sensors created when fields are available: `power_total`, `energy_total`, `power_l1..3`, `current_l1..3`, `voltage_l1..3`.
- Example Lovelace graph card:
  ```yaml
  type: history-graph
  entities:
    - sensor.<your_home>_power_l1
    - sensor.<your_home>_power_l2
    - sensor.<your_home>_power_l3
  ```
