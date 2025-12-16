# Home Assistant (Docker on WSL2)

Minimal base repo for running Home Assistant via Docker Desktop in WSL2 with tracked configuration.

## Prerequisites
- Docker Desktop with WSL2 integration enabled
- Git installed in the WSL2 distro

## Usage
- Start stack: `docker compose up -d`
- Stop stack: `docker compose down`
- Tail HA logs: `docker compose logs -f homeassistant`

Home Assistant UI: http://localhost:8123
