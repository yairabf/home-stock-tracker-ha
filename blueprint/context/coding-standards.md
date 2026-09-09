# Coding standards

## Home Assistant integration conventions

- Keep runtime code in `custom_components/home_stock_tracker/`; use the domain
  constant rather than repeating literal identifiers.
- Follow Home Assistant config-entry lifecycle patterns: setup, unload,
  coordinator ownership, and explicit `ConfigEntryAuthFailed` or
  `UpdateFailed` errors as appropriate.
- Put shared HTTP access in the coordinator. Sensors should present coordinator
  data rather than perform their own requests.
- Use Home Assistant's async APIs and a framework-provided aiohttp session.
- Treat network responses as untrusted: validate expected JSON shapes before
  exposing data to entities.

## Security and behavior

- The API token is a secret. Never log it, return it from diagnostics, or expose
  it in entity attributes.
- Keep the integration read-only unless an approved current feature says
  otherwise.
- Connection, invalid-payload, and authorization failures must surface as
  unavailable data rather than stale data presented as current.

## Testing

- Add or update focused pytest coverage for config flow, coordinator failures,
  and entity state/attributes when changing those areas.
- Run `.venv/bin/python -m pytest -q tests` when the repository virtual
  environment exists; otherwise use a prepared Python environment with
  `requirements-test.txt` installed.
