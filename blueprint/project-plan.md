# Project plan: Home Stock Tracker HA

## Purpose

Home Stock Tracker HA lets a household monitor its Home Stock Tracker service
from Home Assistant. It provides a safe, read-only automation boundary for
pending groceries, tracked inventory, and actionable low-stock recommendations.

## Users and value

- A household member can see concise stock signals in Home Assistant dashboards
  and automations.
- A Home Assistant administrator can connect the service through a UI config
  flow without placing credentials in YAML.

## Product boundary

The integration authenticates to existing read endpoints only. It must not
create, change, or delete grocery, product, purchase, stock, or prediction
feedback data unless a separately approved feature changes that boundary.

## Shipped foundation

- Config-entry setup with URL and token validation, including reauthentication.
- A shared polling coordinator for the service's grocery, inventory, and
  low-stock read models.
- Three availability-aware sensors with counts as state and source records as
  attributes.
- Localized config-flow strings, integration metadata, HACS custom-repository
  metadata, documentation, and a Home Assistant pytest suite.

## Technical shape

- Python custom integration under `custom_components/home_stock_tracker/`.
- Home Assistant config entries and `DataUpdateCoordinator` for lifecycle and
  refresh management.
- HACS custom repository hosted at `yairabf/home-stock-tracker-ha`.
- Tests use `pytest-homeassistant-custom-component`.

## Delivery and support

The repository is public so it can be added in HACS as a custom integration
repository. Releases, HACS validation automation, and wider HACS discoverability
are future delivery choices rather than current guarantees.

## Next decisions to confirm

> TODO (confirm): Decide whether the next feature is HACS release-quality
> automation (validation workflow, release process, and branding) or improved
> dashboard/diagnostic presentation for the existing sensors.

> TODO (confirm): Decide whether a future write-capable integration is desired.
> It would require an explicit safety design and must not be bundled into the
> read-only integration by default.
