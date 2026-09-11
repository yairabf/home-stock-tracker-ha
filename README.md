# Home Stock Tracker HA

A read-only Home Assistant custom integration for Home Stock Tracker. It
exposes pending groceries, tracked inventory, and actionable low-stock
recommendations as coordinator-backed sensors.

## Install with HACS

1. In Home Assistant, open HACS, select **Integrations**, then select the
   three-dot menu and **Custom repositories**.
2. Add `https://github.com/yairabf/home-stock-tracker-ha` with category
   **Integration**.
3. Download **Home Stock Tracker HA** from HACS and restart Home Assistant.
4. Open **Settings > Devices & services > Add integration**, then select
   **Home Stock Tracker**.
5. Enter the Home Stock Tracker service origin, such as
   `http://inventory.local:3000`, and its service bearer token.

The URL must be an HTTP or HTTPS origin without an API path. Do not use
`localhost` unless Home Assistant runs in the same network namespace as the
service.

## Entities

| Entity | State | Attributes |
| --- | --- | --- |
| `sensor.pending_groceries` | Pending grocery count | `items` |
| `sensor.tracked_inventory` | Current plus uncertain inventory count | `current`, `uncertain` |
| `sensor.low_stock_recommendations` | Actionable recommendation count | `recommendations` |

The integration polls the authenticated REST API every five minutes. Successful
empty responses show `0`; authentication, transport, non-success, or invalid
responses make all entities unavailable. It makes authenticated `GET` requests
only and never mutates Home Stock Tracker data or calls MCP.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m pytest -q tests
```

## Support

Report issues at <https://github.com/yairabf/home-stock-tracker-ha/issues>.

## License

Copyright 2026 Yair Abramovitch.

Licensed under the [Apache License, Version 2.0](LICENSE).
