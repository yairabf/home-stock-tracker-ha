# Home Stock Tracker HA - Project Overview

<!-- blueprint:source-hash f08e422c0dd03bb9c1e8b996be12a5b4b85853fdceb455648931f468fd58d7b9 -->

> A read-only Home Assistant custom integration for monitoring household stock
> data from the Home Stock Tracker service.

## Problem

Households need concise, automation-friendly signals for pending groceries,
tracked inventory, and low-stock recommendations inside Home Assistant. The
integration provides those signals without exposing service credentials in YAML
or allowing Home Assistant to modify the source service.

## Users

- **Household member** - views stock signals in Home Assistant dashboards and
  automations.
- **Home Assistant administrator** - connects the existing service through a
  UI config flow using a service URL and token.

## Features

1. **Read-only Home Assistant custom integration** *(completed)* - config flow,
   coordinated polling, availability-aware count sensors, HACS metadata, and
   automated tests.
2. **HACS release-quality readiness** - confirmed next direction, split into:
   - **2a. Release and versioning policy** *(completed)* - the repository's
     release contract and versioning conventions are documented.
   - **2b. Automated HACS validation** *(completed)* - automated validation of
     HACS repository requirements and Home Assistant integration metadata.
   - **2c. HACS brand assets** - supply the publication assets needed for the
     chosen HACS presentation.
   - **2d. Installation and support documentation** - document installation,
     configuration, and support expectations.
3. **Any write action from Home Assistant** *(deferred)* - requires separate
   approval and a safety design for confirmation, retries, and concurrency.

## Data model

The integration stores no independent application data and must remain
read-only. The Home Stock Tracker service owns record-level schemas.

### Config entry

- `service_url` (`str`) - Home Stock Tracker service URL, validated by the
  config flow.
- `api_token` (secret `str`) - authentication token; never logged, surfaced in
  attributes, diagnostics, or test output.

### Coordinator snapshot

- `groceries` (`list[Mapping[str, Any]]`) - current records from the grocery
  read endpoint.
- `inventory` (`list[Mapping[str, Any]]`) - current records from the inventory
  read endpoint.
- `low_stock_recommendations` (`list[Mapping[str, Any]]`) - current records
  from the low-stock read endpoint.
- Response records are untrusted external JSON and require shape validation
  before exposure. Their field-level schema is not specified in the plans.

### Home Assistant entities

- Three count sensors derive integer state from the corresponding coordinator
  record list and expose source records as attributes.
- Connection, authentication, and invalid-payload failures make data
  unavailable; stale data must not be represented as current.

## Tech stack

- **Python** - custom integration runtime under
  `custom_components/home_stock_tracker/`.
- **Home Assistant config entries and `DataUpdateCoordinator`** - lifecycle,
  shared polling, and refresh ownership.
- **`pytest-homeassistant-custom-component`** - automated integration tests.
- **HACS custom repository** - distribution at `yairabf/home-stock-tracker-ha`.

## Monetization

Not specified; the plans describe a public HACS custom repository.

## UI/UX

Home Assistant provides the UI surface:

- Config-flow UI - service URL and token setup, validation, and
  reauthentication.
- Dashboard and automation entities - three availability-aware count sensors
  for groceries, inventory, and low-stock recommendations.

## Deployment

The integration is distributed as a public HACS custom repository. No separate
application host, build command, worker, database, health check, domain, or
environment-variable deployment contract is specified.

## Open questions

> Planning gap: the project plan still describes release policy and HACS
> validation as future delivery choices, while the build plan marks Features
> 2a and 2b complete. This does not establish that a release has been published;
> brand assets and support documentation remain planned work.

> TODO: Decide whether a future write-capable integration is desired; it must
> remain outside the current read-only boundary unless separately approved.
