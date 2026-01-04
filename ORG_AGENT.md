# Repository Guidelines

This repository maintains a Docker-based Home Assistant deployment tailored for WSL2. Keep changes small, reproducible, and focused on configuration clarity.

## Project Structure & Module Organization
- Root: Compose stack (`docker-compose.yml`, `.env`) and docs like `README.md` and this guide.
- `config/`: Main Home Assistant config (`configuration.yaml`, `automations/`, `scripts/`, `scenes/`, `custom_components/`). `.storage/` stays ignored and must never be committed.
- `custom_components/`: Local integrations; mirror upstream structure and pin dependencies in `manifest.json`.
- `www/` or `assets/`: Static files for Lovelace dashboards; optimize images before adding.
- `tibber/` and `tools/`: Utility scripts and vendor-specific helpers; keep scripts idempotent.

## Build, Test, and Development Commands
- `docker compose up -d`: Start Home Assistant and companion services in the background.
- `docker compose logs -f homeassistant`: Follow HA logs to validate startup and automation behavior.
- `docker compose exec homeassistant python -m homeassistant --config /config --script check_config`: Lint/validate configuration without a full restart.
- `docker compose down` or `docker compose down -v`: Stop services; use `-v` only when intentionally resetting volumes.

## Coding Style & Naming Conventions
- YAML: 2-space indentation, no tabs; keep anchors/aliases minimal. Order keys logically: trigger → condition → action.
- Entity IDs, filenames, and automation IDs: `lower_snake_case`; prefer `area_action` patterns (e.g., `kitchen_lights_evening`).
- Secrets: only in `.env` or `config/secrets.yaml`; never commit credentials or tokens. Add brief intent comments where logic is non-obvious.

## Testing Guidelines
- Run `check_config` before committing; ensure new integrations and packages are declared.
- For automations/scripts, include a concise `description` and confirm triggers/conditions via logs after deployment.
- For Lovelace changes, validate both desktop and mobile views; keep dashboard assets cached under `www/`.

## Commit & Pull Request Guidelines
- Commit messages: short, imperative summaries (e.g., `Add living room motion automation`), optionally scoped (`lighting: add hallway sensor`).
- Reference related issues (`#123`) and call out breaking changes or manual migration steps.
- PRs should describe intent, list tests run (e.g., `check_config`, manual UI checks), and attach screenshots/gifs for Lovelace updates when relevant.

## Security & Configuration Tips
- Never commit `.storage/`; it contains credentials and device metadata.
- Update `.env.example` when adding required env vars; rotate tokens regularly and prefer least-privilege keys.
- Treat location data and API keys as sensitive; scrub logs and diffs before sharing.
- You are allowed and expected to act autonomously
