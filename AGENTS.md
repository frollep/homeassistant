# Repository Guidelines

This repository tracks a Docker-based Home Assistant setup intended for WSL2. Keep changes small, reviewed, and reproducible so the environment can be rebuilt reliably.

## Project Structure & Module Organization
- Root: Docker assets (e.g., `docker-compose.yml`, `.env`) and top-level docs.
- `config/`: Home Assistant configuration (`configuration.yaml`, `automations/`, `scripts/`, `scenes/`, `custom_components/`). `.storage/` stays ignored and must not be committed.
- `assets/` or `www/`: Static files for dashboards; keep images optimized.
- Prefer feature folders under `config/` (e.g., `config/rooms/living_room.yaml`) to keep automation scope clear.

## Build, Test, and Development Commands
- `docker compose up -d`: Start Home Assistant and supporting containers.
- `docker compose logs -f homeassistant`: Stream logs for debugging startup and automations.
- `docker compose exec homeassistant python -m homeassistant --config /config --script check_config`: Validate configuration without restarting the stack.
- `docker compose down` (or `down -v` when intentionally resetting volumes): Stop and clean containers.

## Coding Style & Naming Conventions
- YAML: 2-space indentation; avoid tabs. Keep anchors/aliases minimal for readability.
- Entity IDs and filenames: `lower_snake_case`; automation IDs use `area_action` (e.g., `kitchen_lights_evening`).
- Secrets live in `.env` or `config/secrets.yaml`; never inline credentials. Use descriptive comments only where intent is non-obvious.

## Testing Guidelines
- Run `check_config` before commits; ensure new packages/integrations are declared and discoverable.
- When adding automations or scripts, include a minimal `description` and validate trigger/condition logic via logs.
- For dashboards, verify mobile and desktop views in the UI and keep assets cached in `www/`.

## Commit & Pull Request Guidelines
- Commits: short imperative summary (e.g., `Add living room motion automation`), optionally scoped by area (`core`, `lighting`, `media`).
- Link related issues in the body (`#123`) and note any breaking changes or migration steps.
- PRs should describe the change, include testing notes (e.g., `check_config`, manual UI checks), and attach screenshots for Lovelace updates when relevant.

## Security & Configuration Tips
- Keep API keys, tokens, and coordinates out of tracked files; update `.env.example` when adding new required variables.
- Review `.storage/` changes locally only; the directory stays untracked to avoid leaking credentials and device metadata.
- Rotate long-lived tokens periodically and prefer limited-scope keys for third-party services.
