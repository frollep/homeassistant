# Repository Guidelines

## Project Structure & Module Organization
- `docker-compose.yml` – starts Home Assistant, InfluxDB v2, and Grafana on the same network.
- `config/` – Home Assistant configuration mounted at `/config`; keep secrets in `.env`, not here.
- `custom_components/` – Tibber Pulse phases integration; keep entity IDs stable to avoid series churn.
- `grafana/` – provisioned datasources (`provisioning/`) and JSON dashboards (`dashboards/`).
- `tools/` – utilities such as `tibber_probe.py`; `Makefile` exposes `make probe`.
- `examples/`, `docs/`, `tibber/` – reference material and sample configs.

## Build, Test, and Development Commands
- Start stack: `docker compose up -d`
- Stop stack: `docker compose down`
- Logs: `docker compose logs -f homeassistant` (or `influxdb`, `grafana`)
- Probe Tibber API: `cp .env.example .env && make probe` (needs `requests` + `websocket-client`)
- Verify InfluxDB data: `curl -G http://localhost:8086/query -H "Authorization: Token $INFLUXDB_TOKEN" --data-urlencode 'db=ha_energy' --data-urlencode 'q=SHOW MEASUREMENTS'`
- Grafana UI: http://localhost:3000 (credentials from `.env`)

## Coding Style & Naming Conventions
- YAML (Home Assistant): 2-space indent, lowercase keys, snake_case entity IDs; prefer anchors/`!include` for reuse.
- Python (tools/integrations): PEP 8, snake_case functions, type hints where helpful; keep external deps minimal.
- JSON (Grafana): format via Grafana export; no trailing commas; use readable panel titles/units.
- Docker/compose: explicit versions; keep credentials in `.env`, never hardcode tokens.

## Testing Guidelines
- Containers: `docker compose ps` should show running; restart after config changes.
- Home Assistant: check logs for integration errors; verify Tibber entities update in Developer Tools → States.
- InfluxDB: confirm bucket `ha_energy` receives points for Tibber entities via `SHOW MEASUREMENTS` or Flux `from(bucket:"ha_energy") |> range(start:-1h)`.
- Grafana: test the Influx datasource, open the `Tibber Energy & Pulse` dashboard, and confirm panels render for the last hour; widen the time range if data is sparse.

## Commit & Pull Request Guidelines
- Commits: short imperative subjects (e.g., `Add Grafana InfluxQL datasource`); include rationale in body when needed.
- PRs: describe user-facing changes, screenshots of dashboards, linked issues, and required manual steps (e.g., copy `.env`, rotate tokens).
- Keep changes focused; update docs/dashboards alongside config edits.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and replace placeholder tokens/passwords; never commit real secrets.
- Use least-privilege Influx tokens; rotate regularly. Set a strong Grafana admin password.
- Align entity names before enabling Influx export to avoid duplicate series after renames.
