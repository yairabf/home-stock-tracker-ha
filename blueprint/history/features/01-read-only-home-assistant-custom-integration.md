# Feature: Read-only Home Assistant custom integration

**From build-plan:** feature 1
**Status:** verified

**Migration note:** This completed feature was moved from the main Home Stock
Tracker service repository into the dedicated integration repository on
2026-09-09.

## Goal

Let a household add Home Stock Tracker to Home Assistant through a config entry
and inspect pending groceries, materialized inventory, and actionable low-stock
recommendations as authenticated, availability-aware sensors. This provides a
safe automation boundary without allowing Home Assistant to mutate household
state.

## In scope

- A repository-owned Home Assistant custom integration under
  `custom_components/home_stock_tracker/`.
- A UI config flow that accepts and validates the Home Stock Tracker base URL and
  service token, plus reauthentication when that token stops working.
- One shared coordinator that polls the existing authenticated REST read routes:
  pending grocery items, household inventory, and low-stock recommendations.
- Three sensors backed by that coordinator: pending grocery count, tracked
  inventory count, and actionable low-stock recommendation count. Their
  attributes expose the corresponding API records for Home Assistant cards and
  automations.
- Explicit unavailable state when the service cannot be reached, returns an
  invalid payload, or rejects authentication.
- Integration metadata, translations, tests, and setup documentation needed for
  a local custom-component installation.

## Out of scope

- Any Home Assistant service, automation, webhook, voice intent, or direct REST
  call that writes grocery, product, stock, purchase, or prediction-feedback
  data. Any such feature must retain the upstream service's explicit
  confirmation, optimistic-concurrency, and no-uncertain-retry rules.
- Push updates, webhooks, MQTT, Home Assistant discovery, cloud publishing,
  wider HACS publication, or changes to upstream REST/MCP contracts.
- Product-level entities, history/event entities, dashboards, or a replacement
  inventory UI.
- Recalculation, backfill, or persistence from a read. Home Assistant consumes
  only materialized service responses.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan the next unchecked step before code changes.
2. Implement only that step, including its focused tests.
3. Show the diff and evidence; wait for review before the next step.
4. Create optional checkpoints only after the relevant tests and build pass.

## Build steps

- [x] **Step 1 - Establish the custom-component and configuration boundary** - add the Home Assistant manifest, integration setup, config flow, constants, translations, and a minimal Home Assistant test harness. *Done when:* Home Assistant can discover the local integration, a user can enter a valid normalized base URL and token, duplicate configuration is rejected, invalid connection or authentication produces a safe setup error, and neither token nor authorization header appears in logs, diagnostics, or entity attributes.
- [x] **Step 2 - Add a typed, read-only coordinator client** - implement one authenticated coordinator that requests `GET /api/v1/grocery/items`, `GET /api/v1/inventory`, and `GET /api/v1/inventory/predictions/low-stock` at a documented interval and validates each response before publishing it. *Done when:* a successful refresh atomically makes all three normalized responses available, malformed or non-2xx responses do not yield partial data, 401 triggers the standard reauthentication path, transport failures leave all entities unavailable, and the client never calls a write route or MCP endpoint.
- [x] **Step 3 - Publish availability-aware household sensors** - add coordinator-backed grocery, inventory, and low-stock sensors with stable unique IDs, count states, useful structured attributes, and an `unavailable` state sourced from coordinator health. *Done when:* pending groceries expose their count and item records, inventory exposes the total tracked count plus separate `current` and `uncertain` records, low-stock exposes its recommendation count and records, empty successful responses show `0` rather than unavailable, and every entity updates from one shared successful refresh.
- [x] **Step 4 - Document installation and prove the integration boundary** - add a concise installation and configuration guide, then run the custom-component tests. *Done when:* the guide identifies the HACS custom-repository path, required base URL and service token, three entity meanings, polling behavior, unavailable behavior, and read-only limitation; fixture-driven tests cover setup, reauth, success, empty data, malformed data, and service failures; the Home Assistant test command and `git diff --check` pass.

## Files / areas

- `custom_components/home_stock_tracker/` - manifest,
  config flow, coordinator, API client, sensors, translations, and constants.
- `tests/` and `requirements-test.txt` - focused Home Assistant fixtures and
  integration behavior.
- `README.md` - HACS custom-repository installation, configuration, entity, and
  safety documentation.
- `blueprint/build-plan.md`, `blueprint/context/current-feature.md`, and
  `blueprint/.state/run.json` - durable workflow state.

## Data / contracts

- Configuration entry data is `{ base_url, api_token }`. `base_url` is normalized
  without a trailing slash; `api_token` is secret configuration and must never be
  exposed through state, attributes, diagnostics, or logs.
- Every service request sends `Authorization: Bearer <api_token>` and targets
  only the versioned REST base at `<base_url>/api/v1`. The public health route is
  not sufficient to validate credentials.
- The coordinator consumes existing response shapes without changing them:
  grocery `GroceryItem[]`, inventory `{ current: InventoryItem[],
  uncertain: InventoryItem[] }`, and low-stock recommendations from the current
  documented response. It validates required top-level collections before one
  all-or-nothing publish.
- Sensor states are non-negative counts. Attributes retain service-owned product
  names, IDs, quantities, units, inventory state/confidence, and recommendation
  reason only. They omit tokens, request headers, internal errors, event
  metadata, and any newly inferred value.
- Sensor unique IDs are deterministic per config-entry ID and sensor kind. A
  failed refresh makes all three coordinator entities unavailable, while a
  successful empty response makes the relevant count `0`.
- These contracts remain the baseline if a separately approved mutation feature
  ever reuses the authenticated client.

## Testing

- Add the Home Assistant custom-component test command and run it for every
  Python logic-bearing step. Cover config validation, duplicate entries,
  authentication/reauthentication, URL construction, authorization redaction,
  response validation, empty data, and unavailable behavior.
- Use fixture responses for the three existing REST reads. Assert there are no
  POST, PATCH, DELETE, MCP, or prediction-engine calls.
- There is no repository Browser-tests command. Verify real Home Assistant UI
  installation and entity rendering through `/check` or `/try`, not a browser
  test claim.

## Notes for the AI

- This repository is a Python Home Assistant custom integration. Keep runtime
  dependencies limited to Home Assistant-supported integration patterns.
- Reuse the documented REST read surface, not MCP. The MCP protocol and released
  agent fixtures are unrelated to Home Assistant's polling integration and must
  remain unchanged.
- Preserve the service's distinction between `current` and `uncertain`; never
  interpret omitted depleted or untracked products as proof they are absent.
- Keep polling conservative and configurable through a named constant. Do not
  invent event streaming or a second source of truth.
- Use Home Assistant's supported config-entry, coordinator, entity-availability,
  reauth, and diagnostics-redaction conventions. No client-supplied source or
  user identifier is introduced.
- Do not start implementation until the next spec is reviewed. Run
  `graphify update .` after code changes if the repository has graph output.
