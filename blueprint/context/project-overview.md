# Home Stock Tracker HA - Project Overview

<!-- blueprint:source-hash 8e28959488600fc08aaa0dfcfe8d3dddded868aa1cd36df677401be31c7e2097 -->

> A Home Assistant custom integration for monitoring Home Stock Tracker data,
> with one deliberately narrow, confirmed grocery-addition action planned.

## Problem

Households need concise, automation-friendly signals for pending groceries,
tracked inventory, and low-stock recommendations inside Home Assistant. The
integration provides these signals from the existing service without exposing
credentials in YAML. The approved grocery-addition slice lets an explicit Home
Assistant action place a selected item on the source service's grocery list.

## Users

- **Household member** - views stock signals and explicitly adds a grocery item
  through Home Assistant.
- **Home Assistant administrator** - connects the service using a UI config
  flow with a service URL and bearer token.

## Features

1. **Read-only Home Assistant custom integration** *(completed)* - config flow,
   coordinated polling, availability-aware count sensors, HACS metadata, and
   tests.
2. **HACS release-quality readiness** *(completed)* - release policy, automated
   HACS validation, brand assets, and installation/support documentation.
3. **Write actions from Home Assistant** *(approved rollout)* - split into:
   - **3a. Confirmed grocery-list addition** - a single opt-in, duplicate-safe
     grocery-add service.
   - **3b. Explicit catalog resolution and duplicate-item decisions** - follow-up
     user decisions for unresolved products and existing pending items.
   - **3c. Purchase and inventory mutations** - later, independently approved
     stock-changing operations.

## Data model

The Home Stock Tracker service owns all records; the integration stores no
independent application data.

### Config entry

- `service_url` (`str`) - validated service origin.
- `api_token` (secret `str`) - bearer token; never logged, returned, or exposed
  in entity attributes or test output.

### Coordinator snapshot

- `groceries` (`list[Mapping[str, Any]]`) - current grocery records.
- `inventory` (`list[Mapping[str, Any]]`) - current inventory records.
- `low_stock_recommendations` (`list[Mapping[str, Any]]`) - current low-stock
  recommendations.
- Untrusted response JSON must be shape-validated before exposure; connection,
  authentication, and invalid-payload failures leave data unavailable.

### Confirmed grocery-addition contract *(load-bearing for 3a)*

- Home Assistant service input: `product_name` (`str`), `confirm` (`bool`, must
  be `true`), and optional positive `requested_quantity`, `unit`, and `note`.
- Service request: `POST /api/v1/grocery/items` with
  `unknownProductPolicy: "propose_if_missing"`, `productName`, and
  `groceryItem.ifPendingExists: "return_existing"`.
- Source outcomes: `created`, `confirmation_required`, or
  `product_resolution_required`. Only `created` changes source data; other
  outcomes must never be retried or converted into a mutation.

## Tech stack

- **Python / Home Assistant custom integration** - runtime under
  `custom_components/home_stock_tracker/`.
- **Home Assistant config entries and `DataUpdateCoordinator`** - lifecycle,
  shared polling, refresh ownership, and shared authenticated HTTP access.
- **pytest-homeassistant-custom-component** - automated integration tests.
- **HACS custom repository** - distribution at `yairabf/home-stock-tracker-ha`.

## Monetization

Not specified; the plans describe a public HACS custom repository.

## UI/UX

Home Assistant provides the UI surface: config-flow setup, three dashboard and
automation sensors, and (for 3a) an explicit service call with confirmation.

## Deployment

The integration is distributed as a public HACS custom repository. No separate
host, build command, worker, database, or deployment contract is specified.

## Open questions

> The project plan still labels all write capability a TODO, while the build
> plan now approves only 3a. Update the project plan when the approved
> exception should become the durable product boundary.
