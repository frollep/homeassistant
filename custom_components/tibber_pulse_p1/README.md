# Tibber Pulse P1 (Custom Integration)

Home Assistant integration that reads Tibber Pulse P1 measurements (phase-level metrics) from the Tibber Data API.

## Installation

- **HACS (custom repo):** Add this repository as a custom integration and install `Tibber Pulse P1`.
- **Manual:** Copy `custom_components/tibber_pulse_p1/` into your Home Assistant `custom_components` folder and restart Home Assistant.

## Configuration

1. In Home Assistant, go to **Settings → Devices & Services → Add Integration** and search for **Tibber Pulse P1**.
2. Enter your Tibber Data API token.
3. Select the home (if more than one) and the Pulse P1 device for that home.
4. Entities are created automatically after the first poll.

## Entities

The integration inspects the device capabilities returned by the Data API. It creates sensors for:

- Total active power (W)
- Total imported/exported energy (kWh)
- Per-phase power L1/L2/L3 (W)
- Per-phase voltage L1/L2/L3 (V)
- Per-phase current L1/L2/L3 (A)
- Power factor, grid frequency, device temperature (when available)
- Any additional numeric capabilities exposed by Tibber are added as generic sensors with the provided unit/description.

## How it works

- Polls `https://data-api.tibber.com/v1/homes/{homeId}/devices/{deviceId}` on a short interval (default 10s) using a bearer token.
- Uses Home Assistant's `DataUpdateCoordinator` for efficient updates and automatic retry handling.
- Assigns stable `unique_id` values for each capability so entities remain consistent across restarts.

## Notes

- No credentials are stored in files; the token is saved in the config entry.
- If your meter reports energy in Wh, the integration converts it to kWh for Home Assistant energy dashboards.
